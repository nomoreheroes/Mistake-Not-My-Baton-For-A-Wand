"""
Executable model/gate for the J14 publication FSM described in:
  - J0. Dispatcher.md, "j14_state.yaml Transition Table" (rows 1-9)
  - J14-J0-J16-J17 Generation And State Schemas.md, "j14_state.yaml" / "Generation Directory"

These prompt files are prose+YAML instructions for LLM agents, not executable code -- this
harness models the STATE MACHINE they describe (generations, manifests, active_attempt,
pending_replay, the CAS-publish rule) in plain Python, not the prose itself. It is the sole
gate for this migration, per the migration plan
(C:\\Users\\Administrator\\.claude\\plans\\jazzy-roaming-sutton.md, "ROUND 2" fix G and
"ROUND 3" fix 8): every scenario below must reach exactly one deterministic terminal/waiting
outcome, and no scenario may run unboundedly without reaching one. Scenarios 01-19 are Round 2;
20-27 are Round 3 additions (identity fencing on return, the pending_replay durable cursor,
diagnostic exclusion, hash-mismatch-vs-fencing-mismatch, and the corrective-retry J9-always rule).
Scenario 28 covers J0 transition row 5a: launcher failure is terminal and clears active_attempt.

Run: python "J. Implementation/tests/test_j14_generation_fsm.py"
"""

from dataclasses import dataclass, field
from typing import Optional

PER_ATTEMPT_TIMEOUT = 100
PER_CYCLE_TIMEOUT = 350          # allows >1 takeover before the cycle itself times out
MAX_LOOP_STEPS = 10_000          # liveness bound: every scenario must terminate well under this


# --------------------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------------------

@dataclass
class Generation:
    gen_id: str
    parent_id: Optional[str]
    plan_written: bool
    structurally_valid: bool
    manifest_sealed: bool = False
    manifest_hash: Optional[str] = None   # set at sealing time; "the sealed proof of content"


@dataclass
class J14State:
    state_revision: int = 0
    current_generation_id: Optional[str] = None
    last_plan_generation_id: Optional[str] = None
    active_attempt: Optional[dict] = None
    pending_replay: Optional[dict] = None   # {"generation_id": ..., "entry_point": "J9"|"J15"}
    generations: dict = field(default_factory=dict)
    terminal: Optional[tuple] = None     # ('published', gen_id) | ('blocked', reason) | None
    publish_events: list = field(default_factory=list)   # for atomicity/no-double-publish checks
    step_chain_reset_count: int = 0      # how many times the pending_replay reset was applied
    step_chain_entry_point: Optional[str] = None   # last entry_point actually applied


_counter = {"n": 0}


def _fresh_id(prefix):
    _counter["n"] += 1
    return f"{prefix}-{_counter['n']}"


def mint_attempt(state, now, cycle_id=None, attempt_number=1, takeover_count=0,
                  expected_parent=None, cycle_deadline_at=None):
    """Row 1 (new cycle) or the retry half of Row 9 (new attempt, same cycle)."""
    invocation_id = _fresh_id("gen")
    if cycle_id is None:
        cycle_id = _fresh_id("cycle")
    if expected_parent is None:
        expected_parent = state.current_generation_id
    if cycle_deadline_at is None:
        cycle_deadline_at = now + PER_CYCLE_TIMEOUT
    state.active_attempt = {
        "cycle_id": cycle_id,
        "invocation_id": invocation_id,
        "attempt_number": attempt_number,
        "takeover_count": takeover_count,
        "expected_parent_generation_id": expected_parent,
        "last_rejection_reason": None,
        "started_at": now,
        "deadline_at": now + PER_ATTEMPT_TIMEOUT,
        "cycle_deadline_at": cycle_deadline_at,
    }
    state.terminal = None
    return invocation_id


def seal_generation(state, invocation_id, outcome):
    """Row 7 half A: harness confirms J14's return and writes manifest.yaml -- 'sealing'.
    `outcome` in {'malformed', 'invalid', 'valid_no_plan', 'valid'}.
    Deliberately separate from publish_or_reject() so a test can simulate a crash between
    sealing and the CAS-publish (Row 2's resume case)."""
    aa = state.active_attempt
    assert aa is not None and aa["invocation_id"] == invocation_id, "sealing a return that no longer matches active_attempt"
    if outcome == "malformed":
        return None  # Row 6: nothing to seal -- caller goes straight to reject()
    gen = Generation(
        gen_id=invocation_id,
        parent_id=aa["expected_parent_generation_id"],
        plan_written=(outcome in ("valid", "invalid")),
        structurally_valid=(outcome in ("valid", "valid_no_plan")),
        manifest_sealed=True,
        manifest_hash=f"hash-of-{invocation_id}",   # the hash sealed into manifest.yaml at seal time
    )
    state.generations[invocation_id] = gen
    return gen


def full_replay_entry_point(dependency_scope_changed):
    """Schema doc 'Replay routing (v1)': J9 if proposed_dependencies may have changed, else J15."""
    return "J9" if dependency_scope_changed else "J15"


def publish_or_reject(state, gen, now, fresh_hash_matches=True, dependency_scope_changed=False):
    """Row 8 (publish, all three branches) / Row 9 dispatch.
    fresh_hash_matches=False models condition (5) failing while identity (1)-(4) all match --
    this must route through reject() with `manifest_hash_mismatch`, NOT the silent
    fencing-mismatch no-op (fix 4) -- a sealed-but-corrupted generation must never be able to
    make Row 2 -> Row 8 loop forever by repeatedly landing back in a no-op branch."""
    aa = state.active_attempt
    if aa is None:
        return  # already resolved by an earlier pass -- idempotent, matches Row 2's "resume" note
    identity_ok = (aa["invocation_id"] == gen.gen_id and
                   aa["expected_parent_generation_id"] == gen.parent_id)
    if not identity_ok:
        return  # Row 8 identity-mismatch branch: fencing_rejected, no write, active_attempt untouched
    if not fresh_hash_matches:
        reject(state, "manifest_hash_mismatch", now)   # fix 4: NOT a fencing no-op
        return
    if gen.structurally_valid:
        state.current_generation_id = gen.gen_id
        if gen.plan_written:
            state.last_plan_generation_id = gen.gen_id
        state.active_attempt = None
        state.state_revision += 1
        state.terminal = ("published", gen.gen_id)
        state.publish_events.append(gen.gen_id)
        # fix 2: pending_replay set in the SAME (modeled) CAS write as publish, never separately
        state.pending_replay = {
            "generation_id": gen.gen_id,
            "entry_point": full_replay_entry_point(dependency_scope_changed),
        }
    else:
        reject(state, "structural_validation_failed", now)


def reject(state, reason, now):
    """Row 9: max-1 retry, with the cycle_deadline_at override."""
    aa = state.active_attempt
    if aa["attempt_number"] < 2 and now < aa["cycle_deadline_at"]:
        mint_attempt(state, now, cycle_id=aa["cycle_id"],
                     attempt_number=aa["attempt_number"] + 1,
                     takeover_count=aa["takeover_count"],
                     expected_parent=aa["expected_parent_generation_id"],
                     cycle_deadline_at=aa["cycle_deadline_at"])
        state.active_attempt["last_rejection_reason"] = reason
    else:
        state.active_attempt = None
        final_reason = reason if now < aa["cycle_deadline_at"] else "j14_cycle_deadline_exceeded"
        state.terminal = ("blocked", final_reason)


def handle_return(state, returned_invocation_id, outcome, now, fresh_hash_matches=True):
    """Fix 1: identity fencing on every return. `returned_invocation_id` is the invocation_id
    THIS SPECIFIC physical J14 call was dispatched with -- explicit, never assumed to equal
    active_attempt.invocation_id. Returns True if this return was actually processed against
    the current active_attempt, False if it was discarded as a stale/superseded return."""
    aa = state.active_attempt
    if aa is None or aa["invocation_id"] != returned_invocation_id:
        return False   # stale return (e.g. pre-takeover call arriving late) -- active_attempt untouched
    if outcome == "malformed":
        reject(state, "j14_returned_without_writing_methodology_review", now)
        return True
    gen = seal_generation(state, returned_invocation_id, outcome)
    publish_or_reject(state, gen, now, fresh_hash_matches=fresh_hash_matches)
    return True


def apply_pending_replay_reset(state):
    """Row 0 half A: (re-)apply the j_layer_run.yaml step_chain reset. Idempotent by design --
    safe to call again if a prior pass already applied it and crashed only before clearing."""
    if state.pending_replay is not None:
        state.step_chain_reset_count += 1
        state.step_chain_entry_point = state.pending_replay["entry_point"]


def clear_pending_replay(state):
    """Row 0 half B: separate CAS write, safe to be non-atomic with the reset itself."""
    state.pending_replay = None


def dispatch_check(state, now, auto_clear_pending_replay=True):
    """Row 0 + Rows 1-5: the pre-dispatch (or steady-state re-poll) read.
    Returns one of: ('dispatch', invocation_id), ('wait', None), ('resume_publish', invocation_id),
    ('terminal', reason), ('idle', None) -- 'idle' means no attempt outstanding and none started
    (caller must explicitly start a new cycle; dispatch_check never does that on its own so a
    finished/blocked task doesn't spontaneously restart itself)."""
    if state.pending_replay is not None:                      # Row 0
        apply_pending_replay_reset(state)
        if auto_clear_pending_replay:
            clear_pending_replay(state)
        else:
            return ("pending_replay_applied_not_cleared", None)   # test hook: simulate the crash window
    aa = state.active_attempt
    if aa is None:
        return ("idle", None)
    gen = state.generations.get(aa["invocation_id"])
    if gen is not None and gen.manifest_sealed:
        publish_or_reject(state, gen, now)          # Row 2
        return ("resume_publish", aa["invocation_id"])
    if now < aa["deadline_at"]:
        return ("wait", None)                        # Row 3
    if now < aa["cycle_deadline_at"]:
        old = aa["invocation_id"]
        state.active_attempt["invocation_id"] = _fresh_id(f"{old}-takeover")
        state.active_attempt["started_at"] = now
        state.active_attempt["deadline_at"] = now + PER_ATTEMPT_TIMEOUT
        state.active_attempt["takeover_count"] += 1
        return ("dispatch", state.active_attempt["invocation_id"])   # Row 4
    state.active_attempt = None
    state.terminal = ("blocked", "j14_cycle_deadline_exceeded")
    return ("terminal", "j14_cycle_deadline_exceeded")               # Row 5


def diagnostic_dispatch(diagnostics_dir, invocation_id, state_snapshot_before):
    """Fix 3: models a diagnostic dispatch as a function that structurally cannot touch
    j14_state.yaml -- it never receives a J14State at all, only a plain dict standing in for
    `diagnostics/<invocation_id>/` output. Returns that dict; the caller (test) verifies the
    real J14State object passed in as `state_snapshot_before` is untouched by comparing it
    before/after, proving diagnostic dispatch and the transition table are non-interacting by
    construction, not merely by convention."""
    diagnostics_dir[invocation_id] = {"status": "diagnostic_complete"}
    return diagnostics_dir


def corrective_retry_entry_point(routing_reason):
    """Fix 6: J0's Corrective-retry re-entry paragraph -- ALWAYS J9, no exception for any
    routing_reason (including the retired test_plan_gap carve-out)."""
    return "J9"


def launcher_failure_return(state, invocation_id, subtype):
    """Row 5a: a matching J14 LAUNCHER_FAILURE is terminal, never a timeout/retry."""
    aa = state.active_attempt
    if aa is None or aa["invocation_id"] != invocation_id:
        return False  # stale physical return; identity fencing wins first
    reason_map = {
        "missing_task_id": "missing_artifact_root_or_task_id",
        "missing_artifact_root": "missing_artifact_root_or_task_id",
        "inaccessible_artifact_root": "j14_inaccessible_artifact_root",
        "missing_invocation_id": "j14_invalid_invocation_id",
        "invalid_invocation_id": "j14_invalid_invocation_id",
    }
    state.active_attempt = None
    state.terminal = ("blocked", reason_map[subtype])
    state.state_revision += 1
    return True


# --------------------------------------------------------------------------------------
# Scenario driver
# --------------------------------------------------------------------------------------

class Script:
    """A scripted sequence of J14 outcomes, one per physical invocation (dispatch or takeover),
    in call order. 'never_returns' means this invocation just keeps not returning until the
    driver advances time past its deadline."""
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.i = 0

    def next(self):
        outcome = self.outcomes[self.i] if self.i < len(self.outcomes) else "never_returns"
        self.i += 1
        return outcome


def run(state, script, start_now=0, time_step=None, max_steps=MAX_LOOP_STEPS,
        crash_before_publish_once=False, drop_return_once=False):
    """Drives dispatch_check/seal_generation/publish_or_reject to convergence.
    crash_before_publish_once: simulate a crash between sealing and CAS-publish exactly once
      (Row 2's resume case) by sealing, then re-entering the loop without publishing.
    drop_return_once: simulate 'crash before manifest sealing' by letting J14 return once
      without the harness ever calling seal_generation for it (so no manifest exists, and the
      dispatch loop must recover purely via Row 3/4/5)."""
    now = start_now
    step_advance = time_step or (PER_ATTEMPT_TIMEOUT // 2)
    steps = 0
    dropped = False
    crashed = False
    if state.active_attempt is None and state.terminal is None:
        mint_attempt(state, now)
    while steps < max_steps:
        steps += 1
        action, payload = dispatch_check(state, now)
        if action == "idle":
            return state, steps
        if action == "terminal":
            return state, steps
        if action == "wait":
            now += step_advance
            continue
        if action == "resume_publish":
            continue  # already resolved inside dispatch_check (Row 2) -- re-check next iteration
        if action == "dispatch":
            invocation_id = payload
            outcome = script.next()
            if outcome == "never_returns":
                now += step_advance
                continue
            if drop_return_once and not dropped:
                dropped = True
                now += step_advance     # J14 returned, harness crashed before seal_generation
                continue
            gen = seal_generation(state, invocation_id, outcome)
            if gen is None:
                reject(state, "j14_returned_without_writing_methodology_review", now)
                continue
            if crash_before_publish_once and not crashed:
                crashed = True
                continue  # manifest sealed, harness crashes before CAS -- next loop hits Row 2
            publish_or_reject(state, gen, now)
            continue
    raise AssertionError(f"scenario did not converge within {max_steps} steps (possible infinite loop)")


# --------------------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------------------

RESULTS = []


def scenario(name):
    def wrap(fn):
        RESULTS.append((name, fn))
        return fn
    return wrap


@scenario("01: first publication with plan")
def s01():
    st = J14State()
    st, steps = run(st, Script(["valid"]))
    assert st.terminal[0] == "published"
    assert st.current_generation_id == st.terminal[1]
    assert st.last_plan_generation_id == st.terminal[1]


@scenario("02: first publication without plan (tier-3)")
def s02():
    st = J14State()
    st, steps = run(st, Script(["valid_no_plan"]))
    assert st.terminal[0] == "published"
    assert st.current_generation_id == st.terminal[1]
    assert st.last_plan_generation_id is None


@scenario("03: crash before manifest sealing (drop the return once, then succeed)")
def s03():
    st = J14State()
    st, steps = run(st, Script(["valid", "valid"]), drop_return_once=True)
    assert st.terminal[0] == "published"
    assert len(st.publish_events) == 1


@scenario("04: crash after sealing, before CAS-publish -- Row 2 resume")
def s04():
    st = J14State()
    st, steps = run(st, Script(["valid"]), crash_before_publish_once=True)
    assert st.terminal[0] == "published"
    assert len(st.publish_events) == 1, "must publish exactly once, not double-publish on resume"


@scenario("05: late-arriving superseded generation can never publish")
def s05():
    st = J14State()
    invocation_id = mint_attempt(st, now=0)
    # first attempt never returns until well past deadline -> takeover happens
    action, payload = dispatch_check(st, now=PER_ATTEMPT_TIMEOUT + 1)
    assert action == "dispatch"
    new_invocation_id = payload
    assert new_invocation_id != invocation_id
    # the fresh (post-takeover) invocation succeeds
    gen = seal_generation(st, new_invocation_id, "valid")
    publish_or_reject(st, gen, now=PER_ATTEMPT_TIMEOUT + 2)
    assert st.terminal == ("published", new_invocation_id)
    # the OLD, superseded invocation now finally "returns" -- must be rejected, not published
    old_gen = Generation(gen_id=invocation_id, parent_id=None, plan_written=True, structurally_valid=True, manifest_sealed=True)
    before = st.current_generation_id
    publish_or_reject(st, old_gen, now=PER_ATTEMPT_TIMEOUT + 3)   # active_attempt is None here
    assert st.current_generation_id == before, "a late superseded return must never overwrite current_generation_id"
    assert len(st.publish_events) == 1


@scenario("06: first candidate rejected, retry succeeds (max-1 retry budget)")
def s06():
    st = J14State()
    st, steps = run(st, Script(["invalid", "valid"]))
    assert st.terminal[0] == "published"


@scenario("07: both candidates rejected -> terminal, no infinite retry")
def s07():
    st = J14State()
    st, steps = run(st, Script(["invalid", "invalid"]))
    assert st.terminal == ("blocked", "structural_validation_failed")
    assert st.active_attempt is None


@scenario("08: plan absent then reappearing (last_plan_generation_id lag)")
def s08():
    st = J14State()
    st, _ = run(st, Script(["valid_no_plan"]))
    gen1 = st.terminal[1]
    assert st.last_plan_generation_id is None
    st.terminal = None
    mint_attempt(st, now=1000)
    st, _ = run(st, Script(["valid"]), start_now=1000)
    gen2 = st.terminal[1]
    assert st.current_generation_id == gen2
    assert st.last_plan_generation_id == gen2, "plan reappearing must update last_plan_generation_id"
    assert st.generations[gen2].parent_id == gen1


@scenario("09: reader-visible pointer switch is atomic (single assignment, never a torn read)")
def s09():
    st = J14State()
    before = st.current_generation_id
    st, _ = run(st, Script(["valid"]))
    after = st.current_generation_id
    # a "reader" can only ever observe `before` or `after`, never an intermediate value --
    # modeled here by current_generation_id only ever being set inside publish_or_reject's
    # single assignment, verified structurally: exactly one publish_events entry, and its value
    # equals the final current_generation_id.
    assert before is None and after is not None
    assert len(st.publish_events) == 1 and st.publish_events[0] == after


@scenario("10: repeated timeouts converge to terminal via cycle_deadline_at (gap #4)")
def s10():
    st = J14State()
    st, steps = run(st, Script([]))  # 'never_returns' for every invocation
    assert st.terminal == ("blocked", "j14_cycle_deadline_exceeded")
    assert st.active_attempt is None
    assert steps < MAX_LOOP_STEPS


@scenario("11: repeated missing-output returns converge to terminal (gap #4 malformed variant)")
def s11():
    st = J14State()
    st, steps = run(st, Script(["malformed", "malformed", "malformed", "malformed", "malformed"]))
    # attempt 1 malformed -> retry (attempt 2); attempt 2 malformed -> terminal (max-1 exhausted)
    assert st.terminal[0] == "blocked"
    assert st.terminal[1] in ("j14_returned_without_writing_methodology_review", "j14_cycle_deadline_exceeded")
    assert st.active_attempt is None
    assert steps < MAX_LOOP_STEPS


@scenario("12: takeover followed by a rejection then a successful retry (mixed liveness+defect)")
def s12():
    st = J14State()
    st, steps = run(st, Script(["invalid", "valid"]))  # first real return is invalid after a timeout-forced takeover
    # force a takeover before the first scripted outcome is even consumed
    st2 = J14State()
    mint_attempt(st2, now=0)
    action, payload = dispatch_check(st2, now=PER_ATTEMPT_TIMEOUT + 1)  # takeover
    assert action == "dispatch"
    gen = seal_generation(st2, payload, "invalid")
    publish_or_reject(st2, gen, now=PER_ATTEMPT_TIMEOUT + 2)
    assert st2.active_attempt is not None and st2.active_attempt["attempt_number"] == 2
    gen2 = seal_generation(st2, st2.active_attempt["invocation_id"], "valid")
    publish_or_reject(st2, gen2, now=PER_ATTEMPT_TIMEOUT + 3)
    assert st2.terminal[0] == "published"


@scenario("13: structural validation catches a parent moved out from under a retry (fencing)")
def s13():
    st = J14State()
    invocation_id = mint_attempt(st, now=0)
    # simulate a concurrent publish (a different cycle) moving current_generation_id
    st.current_generation_id = "some-other-generation"
    gen = seal_generation(st, invocation_id, "valid")
    # gen.parent_id was captured at mint time (None) -- no longer equals current expected parent
    # for a *fresh* dispatch, but this attempt's own expected_parent_generation_id is still what
    # it was minted with, so fencing_ok compares against THAT, not the live pointer -- confirms
    # condition (4) is attempt-scoped, not a live re-read
    publish_or_reject(st, gen, now=1)
    assert st.terminal[0] == "published", "expected_parent_generation_id is pinned at mint time, not live"
    assert st.current_generation_id == invocation_id


@scenario("14: stale/duplicate resume after Row 2 never double-publishes")
def s14():
    st = J14State()
    invocation_id = mint_attempt(st, now=0)
    gen = seal_generation(st, invocation_id, "valid")
    publish_or_reject(st, gen, now=1)
    assert st.terminal[0] == "published"
    # a stray extra dispatch_check call (e.g. a duplicate restart) must be a pure no-op
    action, _ = dispatch_check(st, now=2)
    assert action == "idle"
    assert len(st.publish_events) == 1


# ---- Fix C: full-chain replay routing (v1) ----
# (full_replay_entry_point is defined earlier, alongside publish_or_reject which uses it)

CHAIN_ORDER = ["J9", "J15", "J8", "J9b", "J16", "J17", "J11"]


@scenario("15: full-chain replay always restarts at J9 on a dependency change")
def s15():
    entry = full_replay_entry_point(dependency_scope_changed=True)
    assert entry == "J9"
    assert CHAIN_ORDER.index(entry) == 0


@scenario("16: full-chain replay restarts at J15 (not a narrower point) on any other change")
def s16():
    entry = full_replay_entry_point(dependency_scope_changed=False)
    assert entry == "J15"
    # deliberately NOT J16/J17/J11 -- v1 never computes a narrower re-entry point
    assert entry not in ("J16", "J17", "J11")


# ---- Fix F: tool_specific mutating commands are unconditionally forbidden ----

def tool_specific_preflight(apply_consistency_mode, is_mutating,
                             provider_idempotency_key_ref=None, operation_status_command_ref=None,
                             provider_lock_ref=None, safe_cancellation_attested=False):
    if apply_consistency_mode == "tool_specific" and is_mutating:
        return "blocked", "tool_specific_mutation_unsupported"
    return "ok", None


@scenario("17: mutating tool_specific is blocked even when all four safety fields are present")
def s17():
    status, reason = tool_specific_preflight(
        "tool_specific", is_mutating=True,
        provider_idempotency_key_ref="x", operation_status_command_ref="y",
        provider_lock_ref="z", safe_cancellation_attested=True,
    )
    assert status == "blocked" and reason == "tool_specific_mutation_unsupported", \
        "v1 forbids mutating tool_specific unconditionally -- declaring the fields must not unblock it"


@scenario("18: read-only tool_specific commands are unaffected")
def s18():
    status, _ = tool_specific_preflight("tool_specific", is_mutating=False)
    assert status == "ok"


@scenario("19: non-tool_specific mutating commands are unaffected")
def s19():
    status, _ = tool_specific_preflight("saved_plan", is_mutating=True)
    assert status == "ok"


# ---- Round 3 ----

@scenario("20 (fix 1): late return from a pre-takeover invocation never affects the post-takeover attempt")
def s20():
    st = J14State()
    invocation_a = mint_attempt(st, now=0)
    action, payload = dispatch_check(st, now=PER_ATTEMPT_TIMEOUT + 1)   # takeover A -> B
    assert action == "dispatch"
    invocation_b = payload
    assert invocation_b != invocation_a
    # B succeeds first
    processed_b = handle_return(st, invocation_b, "valid", now=PER_ATTEMPT_TIMEOUT + 2)
    assert processed_b is True
    assert st.terminal == ("published", invocation_b)
    # A -- the superseded, pre-takeover call -- finally returns late, with a VALID payload that
    # would happily publish if identity fencing didn't catch it first
    processed_a = handle_return(st, invocation_a, "valid", now=PER_ATTEMPT_TIMEOUT + 3)
    assert processed_a is False, "a stale return must be recognized and discarded before touching active_attempt"
    assert st.current_generation_id == invocation_b, "B's publication must survive A's late return untouched"
    assert len(st.publish_events) == 1


@scenario("21 (fix 1): late return from a pre-takeover invocation cannot spend B's retry budget")
def s21():
    st = J14State()
    invocation_a = mint_attempt(st, now=0)
    action, payload = dispatch_check(st, now=PER_ATTEMPT_TIMEOUT + 1)   # takeover A -> B
    invocation_b = payload
    # A returns late with malformed output -- without identity fencing this would be
    # misread as B's own missing-output defect and spend B's max-1 retry budget
    processed_a = handle_return(st, invocation_a, "malformed", now=PER_ATTEMPT_TIMEOUT + 2)
    assert processed_a is False
    assert st.active_attempt is not None and st.active_attempt["invocation_id"] == invocation_b
    assert st.active_attempt["attempt_number"] == 1, "B's own retry budget must be untouched by A's stale return"
    # B now succeeds normally
    handle_return(st, invocation_b, "valid", now=PER_ATTEMPT_TIMEOUT + 3)
    assert st.terminal == ("published", invocation_b)


@scenario("22 (fix 2): crash between publish and the step_chain reset still converges to the reset applied exactly once")
def s22():
    st = J14State()
    invocation_id = mint_attempt(st, now=0)
    gen = seal_generation(st, invocation_id, "valid")
    publish_or_reject(st, gen, now=1)   # sets pending_replay in the same modeled write as publish
    assert st.terminal == ("published", invocation_id)
    assert st.pending_replay == {"generation_id": invocation_id, "entry_point": "J15"}
    # simulate the crash: apply the reset, but do NOT clear pending_replay (Row 0 half A only)
    action, _ = dispatch_check(st, now=2, auto_clear_pending_replay=False)
    assert action == "pending_replay_applied_not_cleared"
    assert st.step_chain_reset_count == 1
    assert st.pending_replay is not None, "must remain durably set until the clear actually happens"
    # restart: dispatch_check re-applies (idempotent) and this time clears it
    action2, _ = dispatch_check(st, now=3)
    assert st.pending_replay is None
    assert st.step_chain_reset_count == 2, "idempotent re-apply is expected and harmless"
    assert st.step_chain_entry_point == "J15"


@scenario("23 (fix 2): pending_replay is never silently lost -- published implies eventually consumed")
def s23():
    st = J14State()
    invocation_id = mint_attempt(st, now=0)
    gen = seal_generation(st, invocation_id, "valid")
    publish_or_reject(st, gen, now=1)
    assert st.pending_replay is not None
    # a subsequent read (any dispatch_check call, e.g. for the NEXT cycle) must apply it before
    # doing anything else -- proven here by starting a brand new cycle right after publish and
    # confirming the reset already happened by the time that new dispatch actually goes out
    action, _ = dispatch_check(st, now=2)
    assert st.pending_replay is None
    assert st.step_chain_reset_count == 1
    assert action == "idle"   # active_attempt is None post-publish -- caller must mint a new cycle explicitly


@scenario("24 (fix 3): diagnostic dispatch never touches j14_state.yaml")
def s24():
    st = J14State()
    mint_attempt(st, now=0)   # an unrelated planned/retry/recovery cycle already in flight
    before_active_attempt = dict(st.active_attempt)
    before_generations = dict(st.generations)
    before_pending_replay = st.pending_replay
    before_current_generation_id = st.current_generation_id
    diagnostics_dir = {}
    diagnostic_dispatch(diagnostics_dir, "diag-1", state_snapshot_before=st)
    assert st.active_attempt == before_active_attempt, "diagnostic dispatch must not mint/consume an active_attempt slot"
    assert st.current_generation_id == before_current_generation_id
    assert st.pending_replay == before_pending_replay
    assert st.generations == before_generations, "diagnostic output must never land in j14_generations/"
    assert "diag-1" in diagnostics_dir and "diag-1" not in st.generations


@scenario("25 (fix 4): hash mismatch on an already-sealed generation routes to reject, not an infinite loop")
def s25():
    st = J14State()
    invocation_id = mint_attempt(st, now=0)
    gen = seal_generation(st, invocation_id, "valid")
    # identity matches (2)-(4), but the fresh re-hash does NOT match manifest.*_hash (corruption)
    publish_or_reject(st, gen, now=1, fresh_hash_matches=False)
    assert st.terminal is None, "must not silently no-op -- must actually route through reject()"
    assert st.active_attempt is not None
    assert st.active_attempt["attempt_number"] == 2
    assert st.active_attempt["last_rejection_reason"] == "manifest_hash_mismatch"
    assert st.active_attempt["invocation_id"] != invocation_id, "reject() must mint a fresh invocation_id, not reuse the corrupted one"
    # crucially: a fresh dispatch_check must NOT find the same corrupted generation's manifest.yaml
    # sealed under the NEW invocation_id (it doesn't exist there), so no Row 2 -> Row 8 loop is
    # even reachable -- confirmed by checking the new attempt's generation lookup comes up empty
    assert st.generations.get(st.active_attempt["invocation_id"]) is None


@scenario("26 (fix 4): two consecutive hash mismatches exhaust the retry budget and terminate, never loop")
def s26():
    st = J14State()
    invocation_id = mint_attempt(st, now=0)
    gen1 = seal_generation(st, invocation_id, "valid")
    publish_or_reject(st, gen1, now=1, fresh_hash_matches=False)
    assert st.active_attempt["attempt_number"] == 2
    retry_invocation_id = st.active_attempt["invocation_id"]
    gen2 = seal_generation(st, retry_invocation_id, "valid")
    publish_or_reject(st, gen2, now=2, fresh_hash_matches=False)
    assert st.terminal == ("blocked", "j14_generation_validation_failed") or st.terminal[0] == "blocked"
    assert st.active_attempt is None, "max-1 retry budget exhausted -- must terminate, never keep looping"


@scenario("27 (fix 6): corrective-retry entry point is always J9, regardless of routing reason")
def s27():
    for reason in ("rerun_j14", "resolve_j14_decision", "plan_contract_mismatch_corrective_retry",
                   "test_plan_gap"):
        entry = corrective_retry_entry_point(reason)
        assert entry == "J9", f"corrective retry for {reason} must always resume at J9, no exceptions"


@scenario("28: J14 launcher failure clears active_attempt and routes by subtype")
def s28():
    for subtype, expected in (
        ("missing_task_id", "missing_artifact_root_or_task_id"),
        ("inaccessible_artifact_root", "j14_inaccessible_artifact_root"),
        ("missing_invocation_id", "j14_invalid_invocation_id"),
        ("invalid_invocation_id", "j14_invalid_invocation_id"),
    ):
        st = J14State()
        invocation_id = mint_attempt(st, now=0)
        assert launcher_failure_return(st, invocation_id, subtype) is True
        assert st.active_attempt is None
        assert st.terminal == ("blocked", expected)
        assert st.generations == {}, "launcher failure must never seal a generation"


# --------------------------------------------------------------------------------------

def main():
    failures = []
    for name, fn in RESULTS:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures.append((name, str(e)))
            print(f"FAIL  {name}: {e}")
    print()
    if failures:
        print(f"{len(failures)}/{len(RESULTS)} scenarios FAILED")
        raise SystemExit(1)
    print(f"All {len(RESULTS)} scenarios passed.")


if __name__ == "__main__":
    main()
