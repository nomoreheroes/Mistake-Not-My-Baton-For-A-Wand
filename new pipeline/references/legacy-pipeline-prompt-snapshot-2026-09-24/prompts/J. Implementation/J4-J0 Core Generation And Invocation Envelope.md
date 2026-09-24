# J4–J0 Core Generation And Invocation Envelope

This document is the normative shared contract for:

- J4 immutable publication on `server_code | client_code | ui_code | migration | config`;
- J0 just-in-time consumption of J4 handoff readiness;
- the common per-physical-call invocation envelope used by J4, J5, J10 and J12.

If a legacy bare-path or attempt-only statement in J0/J4/J5/J10/J12 conflicts with this document, this document wins.

---

## Common Invocation Envelope

Before every physical call to J4, J5, J10 or J12, J0 mints a fresh UUID `run_id`. It is never reused, including a retry with unchanged task/coding attempt counters.

```yaml
invocation_envelope:
  run_id: "<fresh UUID from J0>"
  attempt_number: 1             # positive, agent-specific physical-call attempt
  task_spec_hash: "sha256:<j_acceptance_index.yaml#task_spec_hash>"
  acceptance_index_hash: "sha256:<fresh canonical-object hash of j_acceptance_index.yaml>"
```

Every produced artifact covered by this contract echoes the object byte-for-byte under `context.invocation_envelope`. J0 validates the echo before reading `status`, findings, readiness, routing or any other semantic field and durably records the accepted `run_id` in that runtime step. Any later consumer of a mutable non-J4 report (notably J7 reading J5) rechecks that its envelope still equals the accepted step envelope. Missing/mismatched envelope means stale output (`invalid artifact`/`missing artifact`), never the result of the current call.

For J4, `invocation_envelope.run_id` is also the generation id. For J10, `attempt_number` is independent from `context.task_attempt`: the former distinguishes physical J10 calls, the latter binds the report to the coding unit. For J12, `attempt_number` is `1` for the first deploy call and `2` for its only automatic retry.

J5, J10 and J12 publish their single canonical result through a same-directory temporary file, schema validation, flush where supported, and atomic replace. J0 reads only after physical return and validates the exact envelope. A later overwrite by an obsolete invocation is detected by every downstream reread against the envelope durably accepted for the runtime step.

---

## J4 Immutable Generation Paths

J4 outputs exist only below:

```text
{artifact_root}/{task_id}/j4_generations/{run_id}/methodology_review.yaml
{artifact_root}/{task_id}/j4_generations/{run_id}/deployment_execution_plan.yaml
{artifact_root}/{task_id}/j4_generations/{run_id}/ui_review_plan.yaml
{artifact_root}/{task_id}/j4_generations/{run_id}/migration_execution_plan.yaml
{artifact_root}/{task_id}/j4_generations/{run_id}/manifest.yaml
```

`methodology_review.yaml` is mandatory for every sealed generation. The three plan files are conditional. There are no mutable bare-path J4 outputs under `{artifact_root}/{task_id}/`.

J4 may create/write only the first four files in its own generation directory. J0 alone writes `manifest.yaml` and `{artifact_root}/{task_id}/j4_state.yaml`. A consumer never discovers the current generation by directory ordering, mtime or filename guessing; it reads `j4_state.yaml`.

---

## `j4_state.yaml`

J0 owns this file and updates it with temp-file + atomic replace under the per-task lease and `state_revision` CAS discipline.

```yaml
schema_version: "1.0"
agent: J0
task_id: "<task_id>"
state_revision: 0
current_generation_id: null
active_attempt: null
# active_attempt, when non-null:
#   run_id: "<UUID>"
#   parent_generation_id: "<UUID|null>"
#   attempt_number: 1
#   task_spec_hash: "sha256:<hex>"
#   acceptance_index_hash: "sha256:<hex>"
#   started_at: "<ISO-8601>"
#   deadline_at: "<ISO-8601>"
```

Before dispatch, J0 rereads state, mints `run_id`, and CAS-writes `active_attempt`. It passes `parent_generation_id = current_generation_id` and the common invocation envelope to J4. A non-null active attempt that has not expired is waiting, not permission to start another writer. A timed-out attempt may be replaced with a fresh `run_id`; the old writer can only finish in its now-unpublishable directory.

The fresh generation directory must not already exist at registration time. J4 creates each artifact via same-directory temp file plus atomic rename and performs no further write after returning control. A collision is invalid launcher state, never permission to reuse/overwrite the directory.

---

## J4 Output Envelope

Every J4-produced file begins with its normal schema/agent/task/chain fields and:

```yaml
context:
  invocation_envelope:
    run_id: "<same as generation directory>"
    attempt_number: "<positive physical-call attempt>"
    task_spec_hash: "sha256:<hex>"
    acceptance_index_hash: "sha256:<hex>"
  parent_generation_id: "<UUID|null>"
```

`task_spec_hash`/`acceptance_index_hash` legacy top-level plan fields, where retained for consumer convenience, must equal the envelope values. A mismatch within one file is invalid output.

---

## Sealing And CAS Publication

On physical return from J4, J0 performs these steps in order:

1. Reread `j4_state.yaml`; reject the return unless `active_attempt.run_id` equals this physical call's `run_id`.
2. Require the generation directory name and every artifact envelope `run_id` to match.
3. Validate methodology schema/status/task/chain/hash binding and all declared conditional plan schemas.
4. Enforce output-presence invariants from `methodology_review.yaml#output_publication`.
5. Compute canonical-object SHA-256 for every present artifact and `methodology_core_hash` as defined below.
6. Write `manifest.yaml` as the last file in the generation directory using temp + atomic rename. J4 never writes or edits it.
7. Reread state and hashes. Publish only if the lease, `state_revision`, `active_attempt.run_id`, and `active_attempt.parent_generation_id == current_generation_id` still match.
8. One CAS write sets `current_generation_id = run_id`, clears `active_attempt`, and increments `state_revision`.

No consumer may read a generation until its manifest exists and `j4_state.current_generation_id` names it. A late writer can create files only in an unreferenced directory and can never move the pointer.

### Failure and recovery transitions

- If dispatch cannot start after `active_attempt` was registered, J0 CAS-clears that same active attempt; current generation is unchanged.
- On `LAUNCHER_FAILURE`, malformed output, invalid envelope/schema/hash/presence, or manifest-sealing failure, J0 CAS-clears `active_attempt` only if its run id still matches. A permitted corrective retry registers a fresh run id and a new positive attempt number; it never repairs or reuses the failed directory.
- If the call times out, J0 does not trust a later return. Once `deadline_at` has passed, it CAS-replaces the active attempt with a fresh run id (or clears it when no retry is allowed). The timed-out run can never publish even if it later finishes successfully.
- A CAS mismatch at sealing/publication means this return lost ownership. J0 leaves the newer state untouched and treats the directory as orphaned, never as current output.
- Unreferenced/failed generation directories are audit/GC candidates only. Correctness logic never promotes, merges, or edits them.

```yaml
# j4_generations/<run_id>/manifest.yaml — J0-owned, immutable after publication
schema_version: "1.0"
agent: J0
task_id: "<task_id>"
generation_id: "<run_id>"
parent_generation_id: "<UUID|null>"
execution_chain: server_code | client_code | ui_code | migration | config
task_spec_hash: "sha256:<hex>"
acceptance_index_hash: "sha256:<hex>"
methodology_core_hash: "sha256:<hex>"
artifacts:
  methodology_review: {present: true, path: "methodology_review.yaml", sha256: "sha256:<hex>"}
  deployment_execution_plan: {present: false, path: null, sha256: null}
  ui_review_plan: {present: false, path: null, sha256: null}
  migration_execution_plan: {present: false, path: null, sha256: null}
sealed_at: "<ISO-8601>"
```

`methodology_core_hash` is the canonical-object hash of `methodology_review.yaml` after removing only these volatile/JIT fields:

- `created_at`;
- `context.invocation_envelope`;
- `context.parent_generation_id`;
- `retry_context`;
- `unspecified_decisions`;
- `handoff_readiness`;
- `output_publication`;
- `self_audit` plan-publication/readiness fields.

Nothing else is excluded.

---

## Consumer Resolution

For non-infra J4 chains, every phrase such as `{task_id}/methodology_review.yaml`, `deployment_execution_plan.yaml`, `ui_review_plan.yaml` or `migration_execution_plan.yaml` in a consumer prompt is a logical artifact name. J0 passes:

```yaml
j4_generation:
  generation_id: "<j4_state.current_generation_id>"
  generation_dir: "<absolute artifact_root/task_id/j4_generations/generation_id>"
  manifest_ref: "<generation_dir>/manifest.yaml"
```

J5/J6/J8/J9/J10/J12/J20 resolve J4 logical artifacts only inside that directory. They validate state→manifest→artifact hashes before semantic use. J13, whose contract prohibits shell/filesystem-discovery and hashing commands, instead requires J0's verified manifest/hash attestation, compares the supplied generation id with `quality_report.yaml#context.j4_generation_id` and `request_basis`, and reads only the exact supplied plan path. No consumer falls back to a legacy bare path, another generation or the newest directory by mtime.

---

## Output Publication States

`methodology_review.yaml` contains:

```yaml
output_publication:
  deployment_execution_plan: complete | deferred | not_applicable
  ui_review_plan: complete | deferred | not_applicable
  migration_execution_plan: complete | deferred | not_applicable
```

Invariants:

- `complete` means the corresponding file is present in this generation and valid.
- `deferred` means it is absent, exactly one or more unresolved decisions target its consumer (`J10`, `J12` or `J20`), and that consumer's readiness flag is false.
- `not_applicable` means the file is absent and the chain/trigger does not require it.
- `status: blocked` has all three states `not_applicable` and publishes only methodology.

For `ui_code`, an unclassifiable acceptance check no longer creates a malformed partial plan. J4 publishes methodology with `ui_review_plan: deferred`, leaves the plan absent, sets `j10_can_proceed: false`/`j13_acceptance_points_prepared: false`, and may still set earlier-unit flags true.

---

## Just-In-Time Handoff

J0 does not evaluate all J4 readiness flags when the generation is published. It checks exactly one flag immediately before the unit it governs:

| Unit about to run | Required flag |
|---|---|
| J9 | `j9_can_proceed` (`not_applicable` only when J9 is legitimately absent) |
| J5 | `j5_can_proceed` |
| J6 | `j6_can_proceed` |
| J8 | `j8_can_proceed` |
| J7 | `j7_can_proceed` |
| J10 | `j10_can_proceed` and, for `ui_code`, `output_publication.ui_review_plan == complete` |
| J12 | `j12_can_proceed` and deployment plan complete |
| J20 | `j20_can_proceed` and migration plan complete |
| config validation | `config_validation_can_proceed` |

A false flag pauses only before that unit (`waiting.kind: blocked_until_j0_budget_decision`). It never prevents earlier true units from running.

When a deferred decision is resolved, J0 dispatches a new J4 generation with the current generation as parent. If the new `methodology_core_hash` equals the parent's, completed earlier units remain valid. If it differs, J0 must replay from the earliest consumer whose input projection changed; if J0 cannot determine that boundary deterministically, replay from J9 when present, otherwise J5/J6 as appropriate. It never silently keeps code/tests produced under a changed core methodology.

---

## J10 Reviewed Worktree Digest

J10 computes `context.reviewed_worktree_diff_digest` using the exact J8 Canonical Worktree Diff Digest algorithm, substituting J10's `diff_base_ref` for J8's baseline. The digest includes committed changes since the base plus staged, unstaged and untracked content.

J0 recomputes the digest immediately after J10 returns and before trusting `quality_report.yaml#status`. It must equal the report and the report's common invocation envelope must match the physical call. A mismatch reruns J10 once with a fresh `run_id`; a second mismatch in the same coding attempt blocks with `j10_worktree_changed_after_review`.
