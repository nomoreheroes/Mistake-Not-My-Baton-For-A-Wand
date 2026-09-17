# K0b-02 bounded planning package

Plan ID: `k0b-02-planning-package-v1`; version `1.0.0`.
Status: `draft_non_authorizing_requires_separate_exact_scope_implementation_approval`.
Owner: `W1 Kernel / shared artifact-event plane`. Prepared by the primary workspace agent.
Recorded at UTC: `2026-09-17T14:15:32.0524978Z`; recording time is not an inferred owner-message timestamp.
Complexity tier for this draft: `narrow`, at most 500 non-empty lines; routing at most 95, roster at most 55, failure/recovery at most 95.

This draft specifies fixture-only projection outbox, checkpoint publication, replay materialization and crash reconciliation requirements. It creates no runtime, code, migration, fixture, checkpoint or state-transition authority.

## Bound inputs and precedence

| Input | Complete-file SHA-256 | Bytes |
|---|---|---:|
| `new pipeline/requests/k0b-02-completion-prerequisites-and-bounded-planning-approval-request-v1.yaml` | `a3e6a2710ed7e3d895fb2599c92bd48f7ee23f1add48d37ffe7df5742729ae8c` | 35951 |
| `new pipeline/decisions/k0b-02-transition-and-planning-owner-disposition-v1.yaml` | `10282c45f01518fe96d2f01c6044b445a141f53a039a7368031d5aefc37f9f28` | 27337 |
| `new pipeline/receipts/k0b-01-implementation-completion-v1.yaml` | `c0f24a7c09cbd5d190073510de1f9fe159af8e086bd5f344fe0ffc8ffde243d1` | 15226 |
| `new pipeline/evidence/k0b-02-prerequisite-gate-closure-proposal-v1.yaml` | `219f94076b582d52c94b041f389e3e236b04fccdfe53d607000c3a790ae83a8d` | 8370 |
| `new pipeline/PIPELINE_V2_DEVELOPMENT_PLAN.md` | `679a0bfa08d5c249968fe03ce91d85f9205bab6851c2f09aa9efada3f687382d` | 97569 |
| `new pipeline/decisions/k0b-01-final-implementation-owner-disposition-v2.yaml` | `474d49857a91fd1177560e0ba8ac46f90d56a79de5f41e373febc1440371ccb2` | 42360 |
| `new pipeline/registry/alpha0/alpha0-routing-contract-v1.json` | `38f0ad9652fde5b26268be476347e119be864110f3d4b2fbcc0d4682187f232f` | 37286 |
| `new pipeline/decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml` | `544a6160fc27be348794179f44b44080b87bf3f53c0dd1b66baf9c7d1a40fe9d` | 15509 |
| `new pipeline/architecture/k0b-00-shared-artifact-event-plane-delta-v2.md` | `9586c4536144b612be58d6d01cc13f6437d31898c9bb40fb1c518602086a26ce` | 28613 |
| `new pipeline/reviews/k0b-01-human-only-review-v1.yaml` | `522c3b0e5227f5a6620668ec78c4870b2370faa5d95d8c5132f5a6a7e4fd5140` | 8659 |

The new owner disposition authorizes this documentation package. The final K0b-01 disposition governs the implemented static registry and selected B02 budget inputs. The K0b-00 final owner disposition gives effective authority to its hash-bound artifact/event plan despite that plan's historical review-candidate wording. Root development-plan wording applies with those successors.
No transitive document read or implementation activation is inferred from a reference in this draft.

## Entry conditions and remaining transition blockers

The final K0b-01 completion receipt exists and distinguishes historical document results, observed commit B and owner-reported final-tail results. It discloses the accepted host Python/ruamel procedural deviation.
The owner has explicitly confirmed the single source and projection owners through the exact-hash full documentation-scope confirmation recorded in the new disposition.
The two closure conditions have documentary support. The closure proposal is `conditions_satisfied_closure_proposed_not_materialized_in_state`.
Actual K0b-02 state remains `blocked`; state and all gates remain unchanged.
Renderer v3 has a closed gate-record allowlist without either K0b-02 gate. A separately approved renderer successor and actual state transition are required before materialized closure. Direct MD editing and patches to the existing v3 artifacts are excluded.
The compiler-interface mapping described below also requires an explicit disposition before implementation or activation.

## Single source and exclusive owners

`new pipeline/registry/alpha0/alpha0-routing-contract-v1.json` is the sole authored Alpha-0 registry for events, subscriptions, terminal policies and S routes. Event schemas and resource-budget policy retain their separate roles; canonical process artifacts and decisions belong in SQLite.
Compiled payloads, receipts, snapshots, YAML/MD pairs and Python code do not become parallel authored registry sources.

| Owner | Responsibility |
|---|---|
| `workspace_owner` | Human decisions, approvals and exact scope/ownership confirmation |
| `W1 Kernel / shared artifact-event plane` | Canonical persistence definitions, outbox/projector, checkpoint publisher and replay materialization |
| `artifact_event.transaction_writer` | Atomic decision version, projection intent and outbox admission |
| `artifact_event.projector` | Deterministic pair rendering, verification, readiness and pair hashes |
| Shared control | Admission, scheduling, route/phase/trigger/budget FSM and reconciliation |
| `control.projection_reconciliation` | Consume projection results under control |
| Approved governance state renderer | One-way program-state projection under its separately approved source schema |

Shared control schedules typed requests and owns compiler execution. The artifact/event plane realizes admitted persistence and publication; it does not choose semantic routes, model profiles, call budgets, trigger timing or thresholds.
S/Layer0/workers cannot select publication paths, schemas, phase membership or Git effects. All planned runtime event interfaces remain inactive until separate authority.

## Typed requests, outputs and consumer proof

| Request / source | Planned admission and output | Consumer proof |
|---|---|---|
| Projection intent from admitted control decision | Decision version, outbox intent and `projection.requested` in one DB transaction | Exact decision/outbox IDs, DB sequence, profile and compiler hashes |
| Ordered outbox claim | Verified YAML+MD pair, hashes and immutable result; `projection.written` only when both peers match | `control.projection_reconciliation` records exact pair fields read and disposition |
| Failed projection | Preserved failure evidence and typed `projection.failed` | Existing `block_run_and_enqueue_human` terminal policy |
| Phase-bound checkpoint intent | Verified snapshot and allowlisted Project-Git publication result | Snapshot, contiguous range, commit/tree, DB sequence and consumer receipt |
| Exact replay point | Isolated new-path restore/readback or reproducibility-gap blocker | Pinned invocation envelope, state/tree/delta and artifact/event identities |
| Seal/reconciliation intent | Existing effect reconciled once or typed block | Outbox high-water mark, checkpoint/Git result, counters and predecessor seal |

Every request binds run/project chain, work item, phase/partition, expected revision, causation/correlation, stable identity, canonical request hash, idempotency key, admitted path/root, schema/profile/compiler and count/byte facts.
Stable IDs identify records; hashes verify them. Stored rows, files or commits alone do not establish actual consumer proof.
Preserve the 21-event catalog and existing subscriber/terminal snapshots; phase/seal records are internal persistence records.

## Work units and forward migration interfaces

| Unit | Planned requirements | Exit evidence required by a future implementation scope |
|---|---|---|
| Publication/replay forward migration | New additive outbox, pair, publication and replay records; existing rows/IDs/lineage remain readable | Independent row/count/hash and FK/integrity readback; verified backup/restore |
| Checkpoint-phase forward migration | Ordered binding/transition/seal records and cumulative counters; no third phase | Partition/predecessor/seal invariants and compatibility proof |
| Outbox and projector | Short single-writer DB transactions, ordered claims, deterministic pairs and pair readiness | Duplicate/conflict, partial pair, drift and crash-boundary outcomes |
| Publisher | Durable intent/result, SQLite Backup API, verified clean snapshot, exact allowlisted Git diff | Snapshot identity/integrity, unrelated dirty-path exclusion, exact publication/footer/tree and result reconciliation |
| Replay and reconciliation | New-path restore, exact envelope/readback, begun-intent reconciliation | Clone-only forensic restore and typed block on ambiguous or unavailable effects |

Preserve logical migration order: implemented K0b-01 operational foundation, then `k0b02.artifact_event.publication_replay_v1`, then `k0b02.artifact_event.checkpoint_phase_partition_v1`. Concrete migration filenames and DDL require later exact-scope review against the existing implementation.
Never modify an existing migration. Any required table rebuild must be a separately approved transaction with independent preservation and compatibility checks.

## Projection, checkpoint and replay invariants

1. Projection decision version, intent and expected pair are admitted atomically in SQLite.
2. Render peers deterministically to admitted same-directory temporary paths; validate and fsync, then rename each peer. No partial pair is ready.
3. Record pair readiness and hashes only after both peers match the same canonical decision version.
4. Publisher consumes committed intents, ready pairs and contiguous DB sequence ranges. Active DB/WAL and migration backups remain runtime-only.
5. Use SQLite Backup API and independently verify identity/integrity/FKs. The tracked checkpoint relative path remains `.pipeline/history/pipeline-checkpoint.sqlite3`.
6. Coordination-Git publication includes only the checkpoint and ready YAML/MD peers of the same sequence. Reject unrelated changes and binary merge.
7. Persist intent before external effects and result afterward. The next checkpoint carries the preceding Git result to avoid containing-commit recursion.
8. Phase seal binds terminal checkpoint, ready pair set, outbox high-water mark, counters, authorities and predecessor/successor eligibility. A terminal seal never reopens.
9. F13a acceptance must restore from a clean committed clone into a new runtime path without access to the producer's active DB.
10. Forensic replay uses captured original identities and envelope. Stochastic rerun is a separate action; unavailable model/tool evidence creates a typed reproducibility gap.

These are future implementation acceptance requirements. No fixture clone, runtime path, temporary peer, SQLite database, Git publisher or replay effect is created by this package.

## Failure, crash and duplicate matrix

| Boundary / failure | Required future outcome |
|---|---|
| Invalid schema/profile/owner/phase/trigger/path or stale digest | Reject before mutation or external effect |
| Before DB commit | No visible unit; same request may be revalidated |
| DB commit before response | Return exact committed IDs under the same stable key |
| One projection peer renamed | Pair remains unready; regenerate from canonical DB or block on drift |
| Backup/snapshot replacement interrupted | Reconcile exact durable intent and snapshot identity or block |
| Git index/commit before DB result | Recover exact committed footer/tree/snapshot once or block; no duplicate publication |
| Checkpoint/result before phase seal | Reconcile pending range and intent; keep successor inactive |
| Conflicting duplicate or wrong expected revision | Typed conflict before effect; no identity reinterpretation |
| Corrupt/incompatible checkpoint or missing envelope | Exact-scope read-only diagnosis and verified new-path restore, otherwise block |
| Abort or unknown external effect | Freeze new work, preserve evidence and reconcile begun intents under control |
| Budget hard crossing or fifth F15 trigger | Block the next snapshot/Git effect and preserve terminal evidence |

Fault coverage must exercise each boundary named by the eventual implementation rather than substitute self-report or trivial mocks. Case counts are to be declared by the later approved implementation scope; this draft invents no executed cases.

## Compiler-interface disposition required

The K0b-00 artifact/event architecture names `compiled_projection_checkpoint_profile`. The active Alpha-0 registry lists eight output families and does not include that name.
The current eight are five registry/routing outputs (`compiled_artifact_event_profile`, `compiled_event_reachability_graph`, `compiled_subscription_terminal_snapshot`, `compiled_s_route_table_v2`, `compiled_fanout_barrier_profile`) and three resource/budget outputs (`compiled_resource_forecast`, `compiled_checkpoint_phase_partition_v1`, `compiled_checkpoint_publication_budget_v2`).
Before implementation, produce a concrete owner disposition mapping the projection/checkpoint requirement onto versioned existing interfaces or approving an explicitly bounded successor output/registry scope. Demonstrate provenance and consumer fields for the chosen mapping.
This draft chooses neither branch, adds no ninth output and modifies no registry, schema or compiler.

## Budget, chronology and carry-forward

Retain exactly `K0b-runtime-operational` followed by `K0b-F15-exact-measurement`; chronological, contiguous, non-overlapping and exhaustive. Preserve cumulative chain growth, predecessor seal and zero credit.
Current selected K0b-01 operational values remain inherited inputs: assumed mean object bytes `372736`, nominal/worst counts `6/12`, hard per object `655360`, nominal expected `2236416`, forecast worst-by-count `4472832`, size-stressed object bytes `7864320`, non-binary worst bytes `22020096`, rounded size-stressed checkpoint `30408704` and `34` operational publications.
Provenance for these values is the bound previous K0b-01 request's `phase_B_contract.budget_inputs` and final K0b-01 disposition. This draft records inputs without performing a new budget calculation or asserting new phase completion.
Checkpoint hard remains `104857600`; phase-pack warning/hard remain `536870912/1073741824`; planning factor `1.0_exact`; publication batch cap `12`. Checkpoint and phase-pack values must be strictly below hard.
F15 remains a separate exact measurement package with its four existing boundary trigger identities, exact 36 physical calls under later authority and zero post-F15 model calls. This package allocates or executes no such calls.

| Carry-forward ID | Required obligation |
|---|---|
| `K0B01-HR-NB01` | Preserve 34 as exact and reforecast-sensitive; any input change needs a new bound calculation |
| `K0B01-HR-NB02` | Authoritative F15 worst-case object count before F15 size-stress or second-phase completion claims |
| `K0B01-HR-NB03` | Include assumed mean and all three budget quantities in future inputs/evidence |
| `K0B01-HR-NB04` | Exact forecast-v3/reconciliation-v3 provenance paths and hashes in later authority graph |
| `K0B01-HR-NB05` | Preserve existing authoritative renderer record and five K0b-01 gate inventory |

No finding is reclassified or closed by this draft. No thresholds, storage model, publication counts, phase boundaries or call credits change.

## Later exact scope inventory and acceptance

The current write scope is the six documentation paths in the bound request; existing-file modifications are zero.
Before implementation, separately enumerate concrete new/modified harness, migration, schema, registry, test, fixture and evidence paths; exact existing read pins; locked dependencies; admitted network hosts if necessary; exact new temporary/clone/database targets and cleanup; local Git effects; freeze order and native final checks.
Candidate code reads requiring later separate authorization include `new pipeline/contracts/k0b01/alpha0-kernel-contract-package-v2.json`, `new pipeline/harness/k0b01_v2/store.py`, `new pipeline/harness/k0b01_v2/contract.py`, `new pipeline/harness/k0b01_v2/registry_compiler.py`, `new pipeline/harness/k0b01_v2/budget_compiler.py`, `new pipeline/harness/migrations/0004_k0b01_v2.sql`, `new pipeline/registry/resource-budget-policy/k0b01-policy-v2.json` and `new pipeline/registry/resource-budget-policy/k0b01-reference-inputs-v2.json`.
These candidate paths have not been semantically read by this documentation package and confer no present read/write permission.
Resolve the renderer/state transition and compiler-interface decisions first. Preserve security/egress/abort interfaces owned by K0b-03; do not claim those gates are complete.
Later evidence must bind immutable IDs, schema/migration/profile/compiler inputs, DB sequence, pair/snapshot/Git lineage, fault outcomes, exact consumer receipts, counts/bytes and actual commands/exits. Unknown identities/costs remain unknown.

## Freeze order, stops and owner interaction rule

Current DAG: request -> owner disposition -> final K0b-01 receipt -> two-gate closure proposal -> this draft -> precommit document-check evidence -> new documentation commit.
This draft binds frozen predecessors only, never its own hash, future check/state hashes or its containing commit. Post-freeze staging/commit checks belong in the final handoff.
Stop affected actions on hash/baseline mismatch, unrelated changes, contradictory or insufficient evidence, missing ownership confirmation, unknown effects or any required scope expansion. Report the minimum actual delta without automatic fixes, assumed closure or repeated K0b-01 validation.
When owner confirmation is required, immediately provide ready wording with exact scope and the complete hash once computed. Do not first request permission merely to ask for confirmation.
Mechanical technical retries within unchanged approved scope need no new approval. New paths, dependencies, network/temp targets, authority or materially changed actions need separate agreement.

## Non-authorizations

No K0b-02 implementation, renderer successor, state/gate mutation, manual STATE.md edit, prior evidence rewrite, frozen semantic access, old pipeline/projects/research/external attachment access, network/bootstrap/temp-target restoration, host Python/ruamel, repeated Ruff/pytest/ledger/index/budget/renderer runs, model/provider/API/subagent/review dispatch, threshold/storage/phase/credit change, F15 completion/readiness claim or remote action.
K0b-02 implementation authority remains `none`; runtime authority remains `none`.
