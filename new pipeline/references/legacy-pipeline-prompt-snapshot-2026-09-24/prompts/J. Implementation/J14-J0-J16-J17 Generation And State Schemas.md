# PROMPT — J14/J0/J16/J17: Generation And State Schemas

## Purpose

This document is the single canonical definition for the generation-based publication
architecture shared by J0, J14, J16 and J17 for `infra_code`: the immutable generation
directory + manifest, the single mutable `j14_state.yaml` pointer/retry-state file, the six
named consumer projections recorded for future selective replay routing (in v1 they are
computed and stored but do NOT yet drive routing — see "Replay routing (v1)" below for what
actually decides replay today), and the uniform J16/J17 report envelope. J0 and J14 reference these definitions rather than restating them — a restated
copy is exactly what caused the recurring drift bugs (`j17_assertion_ref`,
`test_version_command_ref`, `declared_gaps[blocks_before:J17]`) across rounds 32–36 of this
pipeline's hardening history. Any change to a projection's field list happens here, once,
and is immediately authoritative for every consumer without a second edit anywhere else.

This replaces the entire candidate/intent/marker ordered-commit protocol and the
`Three independent counters`/`Amendment Impact` revision-counter cascade previously
documented in `J0. Dispatcher.md` and `J14. Infra Methodologist.md`. See those files'
"J14 Candidate Validation And Promotion" (J0) and "Выходной Артефакт" (J14) sections for how
this is actually driven; this document only defines shapes and the projection/replay rule.

---

## Generation Directory

`{artifact_root}/{task_id}/j14_generations/{generation_id}/` — `generation_id` is a fresh
UUID minted by J0 for each J14 invocation (see `j14_state.yaml#active_attempt.invocation_id`
below — the invocation's own id becomes the generation's id 1:1, there is no separate
minting step). Contents, all immutable once `manifest.yaml` exists:

- `methodology_review.yaml` — written by J14. Same content/shape as before this migration
  (see `J14. Infra Methodologist.md`, "Инфраструктурная Методология" and the surrounding
  schema) — this migration changes *where and how it is published*, not what it contains.
- `deployment_execution_plan.yaml` — written by J14 whenever `status: approved` and the
  operational plan is either fully resolved or tier-2 partial with structured `declared_gaps`
  (see `J14. Infra Methodologist.md`, "Blockers vs Partial Plan vs Deferred Without A File").
  It is absent only for tier-3 deferred-without-a-file or when the methodology itself is
  `status: blocked`. `manifest.yaml#plan_present` records the actual outcome; no overloaded
  "tier-1" label is used here.
- `manifest.yaml` — **written by J0 acting as the harness layer, never by J14**, via the same
  atomic temp-write-then-rename primitive used for every other durable write in this pipeline
  (temp file, fsync, rename onto the canonical path, fsync the containing directory) — a crash
  mid-write leaves no partial `manifest.yaml` on disk, only the unambiguous absence this
  document's "no manifest ⟺ never completed" rule already relies on. Written as
  the absolute last action of processing a J14 invocation that returned normally (not
  `LAUNCHER_FAILURE`), only after confirming the expected file(s) above actually exist on
  disk:
  ```yaml
  generation_id: "<uuid>"                     # equals this directory's own name
  parent_generation_id: "<uuid|null>"         # j14_state.yaml#current_generation_id at the
                                               # moment this invocation was dispatched — the
                                               # exact value J0 passed as context.parent_generation_id
  plan_present: true | false
  methodology_review_hash: "sha256:<hex>"     # real hash-tool invocation over the raw file
                                               # bytes, computed by J0/harness — the same
                                               # discipline J16 already uses for
                                               # deployment_contract_digest, never typed out
                                               # as if computed mentally by an LLM
  deployment_execution_plan_hash: "sha256:<hex>|null"   # null iff plan_present: false
  consumer_projections:                       # see "Consumer Projections" below — every
    J9: "sha256:<hex>"                        # value computed fresh by J0/harness from the
    J15: "sha256:<hex>"                       # sealed files, never echoed from J14
    J8: "sha256:<hex>"
    J16: "sha256:<hex>|null"                  # null iff plan_present: false — J16's projection
                                               # is sourced ENTIRELY from deployment_execution_plan.yaml
                                               # (see "Consumer Projections" table), which does not
                                               # exist for this generation in that case; a scalar
                                               # null, not an "all-null object" or an absent key —
                                               # the key `J16` is always present in this map
    J17: "sha256:<hex>"                       # NEVER null — J17's projection has a methodology-
                                               # sourced half that exists regardless of plan_present
                                               # (see "Consumer Projections" table); only the
                                               # deployment_execution_plan.yaml-sourced half of the
                                               # projected object is omitted when plan_present: false,
                                               # which still yields a real, computable hash
    J11: "sha256:<hex>"
  sealed_at: "<ISO-8601>"
  ```
  **No `manifest.yaml` ⟺ this generation never completed** — J14 crashed mid-write, or is
  still running under this `invocation_id`. This is what makes "still in flight" and "tier-2/
  tier-3, no plan by design" structurally distinguishable: both leave `methodology_review.yaml`
  on disk without a plan file next to it, but only a genuinely-finished invocation ever gets
  a manifest, and the manifest itself carries `plan_present` as an explicit, sealed fact
  rather than something inferred from file presence.

**Generations are never deleted, moved, or edited by any correctness-relevant logic.** An
unpublished (never reached `current_generation_id`/`last_plan_generation_id`) generation
directory is ordinary garbage, eligible for GC by out-of-band housekeeping (not defined here —
it is explicitly outside the correctness path) at any time. A generation that WAS published —
at any point in the task's history, even if a later generation has since superseded it as
`current_generation_id` — is under a **GC moratorium: not eligible for deletion until the
owning task itself reaches a terminal state** (`complete`/`blocked`/`superseded` at the
`j_layer_run.yaml` task level, not the generation level). This is deliberately simpler than a
real reachability-set computation (walking every consumer's still-referenced generation via
`consumer_projections`/report `context.generation_id` echoes) — GC is already explicitly
out-of-band housekeeping, not correctness-path logic, so there is no need to compute the
precise reachable set as long as the coarser task-terminal moratorium is cheap to check and
never wrong: nothing outside the owning task can hold a live reference to one of its
generations, so once the task is terminal, no future correctness-path read of any of its
generations can occur, full stop. Real reachability-based GC (deleting a superseded-but-still-
task-active generation the moment nothing references it) is deferred, not designed here — it
is unneeded complexity while the task is still running, and the moratorium alone is sufficient
for correctness. No recovery algorithm ever needs to inspect, resume, or clean up a generation
directory — this is the direct structural payoff of immutability: there is no partial state to
recover *from*.

---

## `j14_state.yaml`

`{artifact_root}/{task_id}/j14_state.yaml` — the only mutable file in this subsystem, one per
task. Every write is a CAS on `state_revision` (same atomic-replace primitive already used
throughout this pipeline for `j_layer_run.yaml`/`j0_task_lease.yaml` — read, verify
`state_revision` unchanged, write with `state_revision + 1`, all as one harness-atomic
operation; a concurrent writer's mismatched `state_revision` at write time means this write
is rejected, re-read and retry).

```yaml
state_revision: 12
current_generation_id: "<uuid|null>"       # null only before the task's first-ever publish
last_plan_generation_id: "<uuid|null>"     # the most recent generation with plan_present:
                                            # true — may differ from current_generation_id
                                            # only across tier-3 no-file generations; tier 2 has a partial plan
active_attempt: null | {
  cycle_id: "<uuid>",                      # constant across every attempt within one max-1
                                            # retry cycle; fresh on a brand-new cycle
  invocation_id: "<uuid>",                 # THE PHYSICAL CALL IDENTITY — fresh, unique, never
                                            # reused for any reason, on every single physical
                                            # dispatch of J14, including every retry attempt AND
                                            # every takeover within the same cycle_id. Becomes
                                            # this attempt's generation_id 1:1 if it ever
                                            # completes. Overwritten in place (same CAS write
                                            # that updates started_at/deadline_at) on a
                                            # deadline-exceeded takeover — there is no separate
                                            # persisted "the old one is now dead" marker; a late
                                            # return under a since-overwritten invocation_id
                                            # simply never matches this field again and cannot
                                            # publish (see "j14_state.yaml Transition Table" in
                                            # J0. Dispatcher.md) — this is why no `state` field
                                            # exists on this object: every transition either
                                            # updates invocation_id in place (takeover) or
                                            # clears active_attempt entirely (publish/terminal),
                                            # never a two-step "mark dead, then mint successor"
                                            # that could be interrupted mid-way and leave an
                                            # unhandled intermediate value on disk.
  attempt_number: 1,                       # 1 or 2 — max-1 retry means attempt_number never
                                            # exceeds 2. Advances only on a structural-validation
                                            # failure or a missing-output defect (see Transition
                                            # Table rows 5/6) — never on a deadline-exceeded
                                            # takeover, which is a liveness concern, not a defect
                                            # in what J14 produced.
  takeover_count: 0,                       # increments by 1 on every deadline-exceeded takeover
                                            # within this cycle_id (Transition Table row 4);
                                            # reset only when a brand-new cycle_id is minted.
                                            # Exists so a persistently-slow/hanging J14 converges
                                            # to a terminal failure via cycle_deadline_at below,
                                            # instead of taking over forever.
  expected_parent_generation_id: "<uuid|null>",  # current_generation_id at the moment this
                                            # attempt was minted — carried through unchanged
                                            # across a retry/takeover within the same cycle (the
                                            # parent doesn't move just because a candidate was
                                            # rejected or an invocation timed out)
  last_rejection_reason: "<string|null>",  # null on attempt 1 of a cycle. Set by J0 as part
                                            # of the SAME CAS write that mints attempt 2, from
                                            # the specific defect of attempt 1 — a structural-
                                            # validation failure (task_id mismatch, task_spec_hash
                                            # mismatch, pairing mismatch) or a missing-output
                                            # defect (see J0.md Transition Table rows 5/6). J0
                                            # passes this verbatim in attempt 2's invocation
                                            # context so J14 corrects the actual defect instead
                                            # of guessing — see J14.md, "Входные Артефакты".
                                            # Durable: a crash between minting attempt 2 and
                                            # actually dispatching it never loses the reason,
                                            # since it lives in the same state_revision-guarded
                                            # write as attempt_number itself, not a side channel
                                            # that could go stale.
  started_at: "<ISO-8601>",                # reset on every takeover (row 4); NOT reset on a
                                            # retry (rows 5/6), where it stays at attempt 1's
                                            # original value — only cycle_deadline_at (below)
                                            # bounds the whole cycle end-to-end.
  deadline_at: "<ISO-8601>",               # started_at + a fixed per-attempt timeout; see
                                            # J0. Dispatcher.md, Transition Table
  cycle_deadline_at: "<ISO-8601>",         # set once, when cycle_id is minted (row 1); NEVER
                                            # updated by a takeover — bounds the entire cycle
                                            # (all attempts and all takeovers combined), so a
                                            # J14 that reliably exceeds its per-attempt deadline
                                            # (or returns normally without ever producing a
                                            # sealable file — see row 6) still converges to a
                                            # terminal j_task_failure_report.yaml instead of
                                            # taking over indefinitely (row 5).
}
pending_replay: null | {
  generation_id: "<uuid>",                 # the generation this replay obligation was produced
                                            # by — matches current_generation_id at the moment
                                            # this field was set
  entry_point: "J9" | "J15",               # where J0 must (re-)start the downstream step_chain
                                            # — see the full-replay rule in "Replay Routing (v1)"
                                            # below and J0. Dispatcher.md, "Corrective-retry
                                            # re-entry"
}
```

`active_attempt: null` means no J14 invocation is currently outstanding for this task — the
task is either freshly created, or the previous cycle already resolved (published or
terminally failed).

`pending_replay` is set by the SAME CAS write as Publication's match branch (Transition Table
row 8) — never a separate write — and is what makes "generation published, but the downstream
full-chain replay this migration's Fix C requires was never actually applied" structurally
unobservable: `current_generation_id` advancing and `pending_replay` being non-null are set
together, atomically, so a crash between publishing and actually resetting
`j_layer_run.yaml#step_chain`/`current_step_index` always leaves a durable, checkable trace
(`pending_replay != null`) rather than a state indistinguishable from "already fully handled."
J0 clears it (a second, independent CAS write, safe to be non-atomic with the actual
`j_layer_run.yaml` reset — see "j14_state.yaml Transition Table", Row 0) only after that reset
has actually been applied. Terminal failure (Transition Table row 9's terminal branch) has no
equivalent field — `j_task_failure_report.yaml`'s own presence/absence is already the durable
signal J0's outer routing checks, with no analogous "was this consumed" ambiguity.

---

## Lineage

Because generations are immutable and permanently addressable by `generation_id` (until GC,
which never runs mid-correctness-decision), lineage is a direct pointer walk, never a search:

- **Methodology lineage**: `parent_generation_id` on any generation's manifest names the
  generation whose `methodology_review.yaml` it was written against. Walking
  `parent_generation_id` repeatedly reconstructs the full methodology history.
- **Plan lineage**: `j14_state.yaml#last_plan_generation_id` always names the most recent
  generation that actually had `plan_present: true`, independent of how many plan-absent
  tier-3 generations have published since (tier 2 is never plan-absent). When J0 dispatches J14 for a task whose
  `last_plan_generation_id` is non-null but not equal to `current_generation_id` (a plan
  existed before, was skipped for one or more cycles, and might reappear now), J0 passes
  **both** `context.parent_generation_id` (methodology continuity) **and**
  `context.last_plan_generation_id` (plan continuity) — J14 reads the latter's
  `deployment_execution_plan.yaml` directly from its own immutable directory as the basis for
  a reappearing plan. There is no "search for the archive with the highest revision number"
  step anywhere in this design — the pointer already names the exact right generation.

---

## Consumer Projections

Six named projections, one per `infra_code` downstream consumer. Each is defined once, here,
as an explicit positive include-list (never an exclusion list — an exclusion list silently
makes every future field relevant by default, the same reasoning that already applies to
"Deploy Contract Digest" style projections elsewhere in this pipeline). J0/harness computes
all six via real hash-tool invocations at sealing time, over the canonicalized projected
content (algorithm below) — J14 never computes any of them.

**Canonicalization algorithm (shared by all six)**: identical to the pre-migration "Deploy
Contract Digest" algorithm — (1) the filtered projection, an object containing exactly the
listed keys/sub-keys, interpreted as a JSON value; (2) serialized as canonical JSON (object
keys sorted by Unicode code point, no insignificant whitespace, arrays keep declared order,
minimal-form numbers, explicit `null`); (3) UTF-8 bytes, no BOM, no trailing newline;
(4) `"sha256:" + lowercase-hex(SHA-256(bytes))`.

| Consumer | Source file | Included fields |
|---|---|---|
| **J9** | `methodology_review.yaml` | `proposed_dependencies` (the full list) |
| **J15** | `methodology_review.yaml` | `handoff_to_j15.amendment_triggers` in full (the actual schema is a list of `{condition, package_hint, reason}` records, not booleans; any record/content change is IaC-identity-relevant) |
| **J8** | `methodology_review.yaml` | `validation_strategy.j8_static_checks`, `static_review_guidance` |
| **J16** | `deployment_execution_plan.yaml` | **Exactly the deploy projection already defined in `J14. Infra Methodologist.md`, "Deploy Contract Digest"** (`include` list + filters + canonicalization algorithm) — not restated here as a second copy. This is intentional, not an oversight: the SAME field list serves two purposes — J16's own apply-time `deployment_contract_digest` (staleness vs J17, computed by J16 itself) and this replay-routing projection (computed by J0/harness at sealing time) — one canonical definition, two consumers, avoiding the exact kind of drift-prone duplicate list that caused several rounds of this pipeline's hardening history. **`null` (a scalar, not an absent key or a special "all-null object") when `plan_present: false`** — there is no `deployment_execution_plan.yaml` for this generation to project, see the `manifest.yaml` schema above. |
| **J17** | `methodology_review.yaml` + `deployment_execution_plan.yaml` | From `deployment_execution_plan.yaml`: `infra_tests` in full (`commands`/`tests`/`steps`/`assertions`), `credentials` referenced by ≥1 `infra_tests.commands[]` entry (via `credential_refs`) — **including an entry shared with `commands.*`**, not only entries exclusive to `infra_tests.commands`, since J17 legitimately reads and depends on a shared credential the same way it would a J17-only one (see `J17. Infra Tester.md`, "Credential Reuse" — "never a credential scoped only for J16" implies the converse is fine), `toolchain` entries with `scope: test` or `scope: both` **in full** (`tool_id`/`executable_ref`/`version_match`/`expected_version`/`version_extract_pattern`/`test_version_command_ref` — every field J17 itself reads, not merely `test_version_command_ref` plucked off an otherwise-excluded `scope: both` entry), `placeholder_bindings` referenced by ≥1 `infra_tests.commands[]` entry (same shared-vs-exclusive correction as `credentials` above), `declared_gaps` filtered to `blocks_before: J17` only. `runtime_environment.isolated_tool_state_dirs` (feeds the env-var collision check every `step_output_bindings[].to_env_var` is validated against — see `J14. Infra Methodologist.md`, "Environment Composition Contract"), `commands.apply` (specifically its emptiness — governs the `target_ref_kind: literal`-only exception for a validation-only unit, see `J17. Infra Tester.md` Preflight row 15), `task_id`/`agent`/`task_spec_hash` (the pairing-proof fields Preflight row 22 checks). From `methodology_review.yaml`: `validation_command_coverage[].j17_assertion_ref` (load-bearing oracle pointer — see `J17. Infra Tester.md`, "Источник Истины" #5), `validation_strategy.acceptance_mapping` (gates `status: passed` via the `A` predicate in "Status Rollup Rule", and Preflight row 24), `status`/`handoff_readiness.j17_can_proceed_after_j16`/`unspecified_decisions.items[]` entries with `required_before: J17` (gate Preflight rows 7–9), `context.task_spec_hash` (the methodology half of the same row-22 pairing proof). **This list is broader than the two originally-scoped bullets above precisely because J17's actual read-set is broader than "the commands/tests it executes" — it also reads the gating/pairing metadata that governs WHETHER it may execute them at all.** It is still not a claim of perfect completeness — see the note below on why exhaustive accuracy is not yet load-bearing. Absent the `deployment_execution_plan.yaml`-sourced half when `plan_present: false` — the resulting hash is still a real, non-null value (see `manifest.yaml` schema above), computed over the reduced (methodology-only) object. |
| **J11** | `methodology_review.yaml` | `documentation_handoff` |

**Replay routing (v1) — full chain, no selective diffing.** `required_replay_from` and the
per-consumer diff rule described in earlier drafts of this section are **not implemented in
v1**. Any generation change (a new `current_generation_id`, or a new `last_plan_generation_id`
when the plan specifically changed) triggers the full downstream chain from its earliest
structural entry point: `J15 → J8 → J9b → J16 → J17 → J11` for any methodology or plan content
change; starting from `J9` specifically when `proposed_dependencies` changed. This is
deliberately coarser than diff-based selective replay — it costs extra reruns of steps whose
actual read-set didn't change — but it is unconditionally safe, which selective replay
currently is not: auditing each of the six projections in the table above against what its
consumer *actually* reads (not just what a first-pass field list guessed) is exactly the kind
of hand-maintained, easy-to-under-scope enumeration this whole redesign exists to eliminate one
level down — J15's `handoff_to_j15.amendment_triggers`-only projection is a concrete example
that shipped too narrow relative to J15's real read-set (see the migration's round-2 notes).
This J9-vs-J15 branch is a real content comparison (J9's entire read-set is, by design, exactly
`proposed_dependencies` — see `J9. Dependency Auditor.md`, "Source Of Truth" — so diffing that
one field between parent and child generation is exact, not a guessed field list), which is why
it is kept here even though selective per-consumer routing generally is not. **Corrective
retries specifically use a stricter, unconditional `J9`-always rule instead of this branch** —
see `J0. Dispatcher.md`, "Corrective-retry re-entry" — because an earlier revision carved out
one routing reason (`test_plan_gap`) as skippable based on what *triggered* the retry rather
than on an actual content diff of the resulting generation, which was found unsound (round-3
notes); the stricter rule applies there specifically, not as a general replacement for the
content-based branch described here.

The six `consumer_projections` hashes are still computed and stored at sealing time (cheap, and
already useful for the report envelope's staleness checks and future re-introduction of
selective replay) but are **not currently read for routing purposes** — `required_replay_from`
is not computed or written anywhere. Re-introducing per-consumer selective replay is deferred
until each projection's field list has a machine-checked read-set test proving it is a superset
of what that consumer's own prose actually depends on (see the executable test suite gate in the
migration plan) — a one-time audit is not sufficient, since the same drift that under-scoped
the field list once can silently reintroduce it on any future edit to a consumer's own Source Of
Truth without touching this table.

---

## Report Envelope (J16 + J17)

Every J16 report (`deployment_report.yaml`, `deployment_cleanup_report.yaml`,
`deployment_diagnostic_report.yaml`) and every J17 report (`infra_test_report.yaml`) carries
this four-field envelope as a top-level `context` sub-object, with exactly these names, types
and top-level placement — no schema-specific variation on the envelope itself (a flat vs.
nested placement mismatch across report types was itself a bug found in round 36; the uniform
shape below is what closes that class of bug structurally). This is a floor, not a closed
shape: each report's own schema in `J16. Infra Deployer.md`/`J17. Infra Tester.md` legitimately
adds further report-specific fields inside the same `context` object (e.g. J16's
`deployment_execution_plan_generation_id_used`/`deployment_contract_digest`, J17's
`previous_report_sha256`) — those additions do not violate "exactly this shape," which governs
only the four fields below; a consumer checking envelope conformance checks that these four are
present with the right names/types/placement, never that `context` contains nothing else:

```yaml
context:
  run_id: "<uuid>"                    # fresh per physical invocation, including every retry
  attempt_number: 1
  generation_id: "<uuid>"             # the j14_generations/ methodology generation this run
                                       # was built against — equals j14_state.yaml#current_
                                       # generation_id at the moment this invocation started.
                                       # Plan-dependent content is a SEPARATE concern: J16/J17
                                       # each also carry their own context.plan_generation_id
                                       # (echoing j14_state.yaml#last_plan_generation_id at
                                       # dispatch), which can legitimately differ from
                                       # generation_id only across tier-3 no-file generations
                                       # above. Never conflate the two: a plan-dependent field
                                       # is bound to plan_generation_id, never to generation_id.
  task_spec_hash: "sha256:<hex>"      # echoed from j_acceptance_index.yaml#task_spec_hash,
                                       # same Input-hash binding principle used elsewhere
```

J0 checks all four fields **before** reading `status` on every row that consumes one of these
four report types: `run_id` against the UUID it minted for this physical dispatch,
`attempt_number` against the dispatched attempt, `generation_id` against the
`j14_state.yaml#current_generation_id` read immediately before dispatch, and `task_spec_hash`
against a fresh `j_acceptance_index.yaml#task_spec_hash` — see `J0. Dispatcher.md`, the
uniform envelope gate immediately before the J16/J17 rows in "Step Result Contract". An
absence/type error/mismatch in any field means the report does not belong to the invocation
J0 is currently evaluating — treat as
`missing artifact`, never as this invocation's own `status`, regardless of what `status`
literally says inside the file.

The four-field envelope binds the invocation and methodology generation; the plan identity is a
required companion check, not a fifth uniform field with schema-specific aliases. J0 also checks
`context.deployment_execution_plan_generation_id_used` against the dispatched `plan_generation_id`
for main/diagnostic J16, `context.plan_generation_id` against it for J17, and the cleanup report's
`context.deployment_execution_plan_generation_id_used` against the original accepted deploy report's
value. See the "Plan-generation companion gate" in `J0. Dispatcher.md`. A mismatch is stale/foreign
output even when all four uniform envelope fields match.

---

## Harness Attestation (J16 + J17)

Both `J16. Infra Deployer.md` and `J17. Infra Tester.md` require a `harness_attestation` object
from J0 (see each file's own "Execution Harness Requirements") as an external input confirming
execution-environment guarantees the model cannot self-certify. **J16 requires
`schema_version: "1.1"`, while J17 requires `schema_version: "1.0"`; each value versions that
agent's own envelope and is not a promise of an identical field set** — J16
and J17 attest to different guarantees because they do materially different things (J16 runs
stateful mutating phases under lease fencing and a durable journal; J17 runs read-only tests and
never mutates infrastructure), so their attestation objects are two separate schemas that happen
to have independently versioned schemas, the same way J16 report `schema_version: "1.2"` and
J17 `infra_test_report.yaml#schema_version: "3.1"` do not imply those two report schemas
are otherwise identical. Do not infer one agent's required field list from the other's, and do
not pass one agent's attestation object to the other.

The canonical field list for each lives in exactly one place — the same anti-drift principle
already applied above to Consumer Projections and the Report Envelope:

- **J16's fields**: `J16. Infra Deployer.md`, "Execution Harness Requirements" — `schema_version`,
  `read_only_worktree_mount`, `isolated_home`, `inherit_environment`, `env_allowlist`,
  `argv_no_shell_default`, `bounded_termination`, `pre_context_redaction`,
  `atomic_schema_validated_write`, `durable_fsync_journal_append`,
  `atomic_append_if_absent_external_state_resolved`, `atomic_fenced_command_spawn`,
  `atomic_fenced_external_state_resolution`, `atomic_fenced_report_commit`,
  `output_capture_policy_supported`, `attestation_source`.
- **J17's fields**: `J17. Infra Tester.md`, "Execution Harness Requirements" — `schema_version`,
  `read_only_worktree_mount`, `isolated_home`, `inherit_environment`, `env_allowlist`,
  `argv_no_shell_default`, `bounded_termination`, `pre_context_redaction`,
  `atomic_schema_validated_write`, `step_output_bindings_supported`,
  `output_capture_policy_supported`, `attestation_source`.

`J0. Dispatcher.md` passes each executor its own object, by name (`harness_attestation` in the
J16 invocation bundle vs. `harness_attestation` in the J17 invocation bundle — J14 receives no harness attestation; see "Запуск
агентов"), sourced from the actual execution harness at dispatch time, never invented or copied
across agents. If a future edit adds/removes a field for one agent, update only that agent's own
"Execution Harness Requirements" section and this list — never the other agent's schema, and
never assume the two lists stay in sync by default.
