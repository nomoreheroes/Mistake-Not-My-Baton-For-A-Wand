# K0b-00 Shared Artifact/Event Plane Operational Delta Plan

| Field | Value |
|---|---|
| Plan ID | `k0b-00-shared-artifact-event-plane-delta` |
| Version | `1.0.0` |
| Status | `review_candidate`; implementation forbidden pending independent review, budget reconciliation, and owner approval |
| Work item / phase | `K0b-00` / `K0b` (`2.0b`) |
| Architecture owner | `W1 Kernel / shared artifact-event plane` |
| Baseline | `k0a-00-shared-artifact-event-plane` v`1.1.0`, SHA-256 `671b238c2dfd76f2b37d4ba3ff9db3a5b67ce5e4295483e0d202e060f57e5860` |
| Complexity tier | `shared_plane`, at most 800 non-empty full-file lines |
| Sub-budgets | routing `<=105`; roster `<=55`; failure/recovery `<=105` non-empty lines |
| Exact hash binding | recorded outside these bytes in author/review/approval records to avoid self-reference |

## Scope envelope

This is a delta only to the approved K0a shared artifact/event plane. All unchanged K0a invariants remain binding by the baseline hash. The common authority is `k0b-00-operational-alpha0-delta-scope-v1` (`new pipeline/architecture/k0b-00-scope-envelope-v1.yaml`, v`1.0.0`, SHA-256 `fe63742498a8192c7f67c5d430eb8c466d3621d873e3486115102510e7ca779a`). The entry evidence is commit `a031ee56a36cf794646643b67270c6e0f7092e08` with corrected external rereview verdict `approve`.

| Required field | Bound K0b value |
|---|---|
| Package | `K0b-00`; one shared-plane architecture delta only |
| Runtime profile after approval | operational Alpha-0 in a new committed fixture clone with a coordination worktree; never the canonical fixture worktree |
| Scenarios | `F01-F05`, `F07`, `F09`, `F10`, `F13a`, `F15` |
| Current deterministic components | schema/profile validator, transaction writer, subscription materializer, projection outbox/projector, checkpoint publisher, replay/reconciliation materializer, compatibility/backup reader |
| Current routes | validated request to atomic artifact/event publication; immutable delivery snapshot; key-decision projection pair; bounded checkpoint publication; clean-clone replay/reconciliation |
| Artifact types | retained `bootstrap.synthetic_result`; added fixture-only `alpha0.key_decision`; internal records are not content artifacts |
| Event profile | the five retained F00 events plus the exact sixteen K0b additions in the common scope envelope |
| Downstream boundary | committed IDs/results to shared control; compiled semantic route bindings from S/control; projection pair and checkpoint only in fixture project Git |

K0b-00 may create only plans, exact review inputs, review/disposition records, ledger entries, and approval requests/receipts. It creates no SQL migration, registry, contract, prompt, fixture run, checkpoint, projection, or runtime behavior. Later implementation is limited to this plane's portions of `K0b-01..05` and remains blocked until all three deltas are reviewed and owner-approved.

Explicit non-goals are a `projects/swarm` or other real-product run; any research read/import; canonical fixture mutation; product/release readiness; N1 contracts; dialogue, distributed leases, general retry/dead-letter, budget optimizer/escalation FSM, cache/scale/RAG, CAS/LFS/external checkpoint backend, destructive in-place restore, or direct provider/API authority.

## 1. Purpose, responsibility, non-goals, and applicability

The delta promotes the F00-only immutable store into the operational fixture persistence plane. It owns canonical artifact/event schemas, versioned registry inputs, atomic versions/events/deliveries, projection outbox and hashes, SQLite snapshot bytes, checkpoint publication records, replay materialization evidence, and persistence reconciliation.

It does not own semantic route choice, run state, invocation scheduling, checkpoint timing policy, S route-freeze decisions, model execution, product source, or owner approval. Shared control validates and orders requests; S owns semantic routing; this plane validates and durably realizes only the exact requested persistence effect.

Applicability is the assigned K0b scenarios on an isolated fixture clone after the complete K0b-00 gate. Alpha-0 is a fixture-only recovery/safety claim after K0b-04, not product readiness. Unknown profile, project identity, schema, compiler output, or owner binding fails before mutation.

## 2. Dispatcher, deterministic harness, S, Layer0, worker, and compiler boundary

| Owner | K0b responsibility | Forbidden overlap |
|---|---|---|
| S | semantic route classes, fallback/blocker/revision meaning, route freeze/unfreeze | no DB/Git write, schema invention, publication, or projector call |
| Shared control | compile and execute route/resource graph; validate state/ordering; issue typed transition, projection, checkpoint, and replay requests | no content/event/checkpoint persistence or projection rendering |
| Layer0/workers | propose typed semantic results for the scheduled invocation | no event/subscriber/schema/owner/path/capability selection |
| Shared artifact/event plane | own canonical data schemas and registries; validate/persist immutable effects; publish projections/checkpoints | no semantic routing, invocation scheduling, or executor selection |

The future K0b compiler consumes hash-bound S semantics, control policy, artifact/event registries, schemas, projection profile, and checkpoint policy. The compiler engine and its execution belong to shared control. This plane owns the data-definition inputs and independently validates the compiled output hash before using it.

Required compiler outputs are `compiled_artifact_event_profile`, `compiled_event_reachability_graph`, `compiled_subscription_terminal_snapshot`, `compiled_projection_checkpoint_profile`, and `compiled_resource_forecast`. Each contains compiler/version/input hashes, deterministic ordering, profile/scenario scope, and one aggregate digest. Unknown nodes, dangling subscribers, conflicting schema versions, incomplete terminal policies, unbounded payload values, or a forecast mismatch reject compilation; runtime cannot patch output bytes.

The plane persists an immutable compiled-profile snapshot on run binding and copies the exact applicable subscriber/barrier/terminal entries into each delivery transaction. It never interprets an S or model proposal as a compiler output. The provisional sibling control delta is a compatibility input only; the approved K0a baselines and common scope remain authoritative until owner decision `K0b-D02`.

## 3. Canonical schemas, forward migrations, state machines, and invariants

After approval, `K0b-01` may create one canonical artifact/event contract package and registries for the exact Alpha-0 profile. Planned schema identities are:

| Canonical schema | Version | Purpose / authority |
|---|---:|---|
| `pipeline-v2.artifact-publication-request` | 2 | additive operational request with expected revision, idempotency identity, lineage, owner, schema/profile and optional projection intent |
| `pipeline-v2.artifact-version-record` | 2 | immutable textual or explicitly budgeted binary version metadata; stable version ID remains canonical identity |
| `pipeline-v2.event-envelope` | 2 | immutable event ID/type version, producer, causation/correlation, trust, payload schema/hash and artifact/evidence refs |
| `pipeline-v2.event-delivery-snapshot` | 2 | exact compiled subscriber, guard result, fan-out group/barrier, terminal policy and delivery result |
| `pipeline-v2.key-decision-record` | 1 | normalized fixture-only decision version from which YAML+Markdown are rendered |
| `pipeline-v2.projection-outbox-item` | 1 | source version, pair target, renderer/schema hashes, expected content hashes and idempotency key |
| `pipeline-v2.checkpoint-publication-record` | 1 | DB identity/sequence/range, trigger, snapshot hash, Git intent/result and threshold statuses |
| `pipeline-v2.replay-materialization-record` | 1 | source checkpoint/replay point, target identities, verification gaps and deterministic result |

The physical contract/registry paths and migration sequence are assigned only after all three plans are approved. Logical forward-migration IDs are `k0b01.artifact_event.operational_v1`, `k0b02.artifact_event.publication_replay_v1`, and `k0b03.artifact_event.compatibility_evidence_v1`; no file with those migrations exists in this authoring step.

`k0b01` preserves all K0a IDs/rows and replaces the closed F00-only event constraint through a verified SQLite table-rebuild or equivalent registry-FK migration, never an in-place edit of prior migration files. It adds the Alpha event/type/profile tables and compiled snapshot bindings. `k0b02` adds outbox/result, checkpoint publication, replay materialization, and reconciliation history. `k0b03` adds compatibility, backup/restore, quarantine, and recovery evidence owned by this plane. Shared-control tables and transitions remain outside these migrations.

Every migration requires a consistent pre-upgrade backup, integrity/foreign-key checks before and after, exact schema/pipeline compatibility pins, transactional apply where SQLite permits, and an immutable migration result. Crash before commit leaves the old schema; crash after commit is detected by migration identity/hash. A newer DB is read-only diagnostic to an older harness; downgrade or destructive overwrite is forbidden.

State machines are:

```text
artifact/event request: proposed -> validated -> committed | rejected | rolled_back
delivery: pending -> accepted_terminal | delivered | rejected_terminal | blocked
projection: pending -> materializing -> pair_ready -> recorded | reconcile_required | failed
checkpoint: requested -> snapshot_validated -> git_intent -> committed -> recorded | reconcile_required | failed | over_limit
replay materialization: requested -> verified -> materialized -> reconciled | blocked
```

Persisted artifacts/events, lineage, subscriber snapshots, outbox intents/results, checkpoint intents/results, and transition history are immutable. Mutable convenience pointers may be rebuilt and cannot conceal history. One local writer lock, expected DB revision, stable IDs, exact schema/profile hashes, and unique idempotency keys guard every mutation.

## 4. Input events, guards, persistence routes, fan-out, barriers, and fast paths

All inputs are typed shared-control requests or internal reconciliation facts; no agent receives SQL, filesystem, or Git capability.

| Input / condition | Guards | Deterministic persistence route |
|---|---|---|
| validated artifact publication | run/profile, producer invocation, owner, schema, lineage, content hash, size, expected revision | atomic artifact version + required events + subscriber snapshots + optional projection intent |
| validated event append | known event/schema/producer, causation, terminal policy, idempotency key | append once and materialize exact delivery snapshot |
| compiled fan-out event | exact immutable members and barrier policy from compiled profile | create all deliveries in one transaction; barrier result remains control-owned |
| projection intent | exact committed `alpha0.key_decision`, paired paths/profile/renderer, no pending conflicting source version | append outbox row and `projection.requested` atomically with decision version |
| checkpoint publish request | contiguous replay range, DB sequence, trigger, threshold status, root/worktree allowlist, no unresolved projection | snapshot/verify, materialize ready pair, create allowlisted Git commit, record result |
| replay materialization request | exact checkpoint/replay point, clean target, compatible reader, complete refs | restore to a new runtime path and verify state/tree/delta/envelope |
| abort/reconciliation request | route frozen by control; exact outstanding intent set | finish or classify begun persistence only; start no unrelated delivery |

The only fast paths are pure schema/hash validation, duplicate-result lookup, exact subscriber snapshot lookup, and read-only inspection. They make no LLM call and no semantic choice. Unknown or ambiguous schema/type/subscriber/owner/path never falls back to a permissive write.

`F04` fan-out is limited to the exact compiled fixture reviewer set. This plane snapshots members and the canonical barrier identifier; shared control decides scheduling and barrier satisfaction. `F05` revision persists the new request and invalidation edges but S identifies the semantic owner and control computes the minimal executable subgraph.

Routing section sub-budget: `<=105` non-empty lines.

## 5. Output events, subscribers, terminal policy, and cross-plane handoffs

The exact K0b profile retains `command.received`, `run.started`, `artifact.version_created`, `handoff.ready`, and `run.completed`, and adds only:

`run.blocked`, `run.abort_requested`, `run.aborted`, `artifact.published`, `projection.requested`, `projection.written`, `projection.failed`, `revision.requested`, `gate.passed`, `approval.requested`, `approval.granted`, `approval.rejected`, `error.schema_mismatch`, `error.tool_failure`, `error.security_policy`, and `meta.incident_detected`.

| Family | Semantic producer / persistence owner | Required subscriber or terminal policy |
|---|---|---|
| run lifecycle and abort | shared control / artifact-event plane | control readback; abort terminal only after reconciliation |
| artifact and handoff | worker proposal validated by control / artifact-event plane | compiled subscriber snapshot; `bootstrap_sink` only for exact F00 |
| projection | request policy by control, outbox/projector result by artifact-event plane | control/gate consumes exact pair hashes or failure |
| revision and gate | S/downstream meaning through control / artifact-event plane | exact upstream owner or gate consumer from compiled profile |
| approval | authenticated human request/result through control / artifact-event plane | exact requesting gate; text/model claims cannot grant approval |
| schema/tool/security errors | detecting deterministic component / artifact-event plane | `block_run_and_enqueue_human` before M1 |
| meta incident | detecting component / artifact-event plane | `persist_incident_and_enqueue_W5` before M1 |

`projection.written` is emitted only after both files validate and their hashes are recorded. `projection.failed` is terminal for the current intent and blocks the gate; crash reconciliation may prove an already completed pair without creating a second logical request. `artifact.published` means the exact artifact version has a completed declared publication result, not merely a DB row.

Every committed response to control contains stable IDs, DB sequence/revision, schema/profile/compiler digests, idempotency disposition, and exact delivery/outbox/checkpoint result refs. No direct layer-to-layer or worker-to-worker handoff exists.

## 6. Artifact types, ownership, versioning, lineage, projections, and publication

`bootstrap.synthetic_result` remains byte-for-byte governed by its approved F00 schema. K0b adds only `alpha0.key_decision`, a fixture-only normalized structured textual record used to prove F07 projection recovery. Its logical owner is the authenticated fixture owner decision; a worker, S, control, projector, or model cannot replace that owner.

Every content version records stable artifact and immutable version IDs, logical owner, producer invocation/request, parent version/evidence refs, schema/profile/hash/canonicalization, media/encoding, trust/confidentiality, DB sequence, causation/correlation, and supersession/invalidation edges. External references use `artifact_version_id`; content hash is verification metadata, never identity.

Projection ownership is strict: the DB decision version is canonical; YAML and Markdown are derived peers with one stem. The outbox/projector and pair hashes belong to this plane. Shared control owns request ordering and checkpoint policy; S may request a semantic decision revision but never edits a projection. Manual file drift is rejected or captured as an untrusted proposal for a new owner-owned version.

Projection protocol:

1. One DB transaction commits the decision version, outbox intent, expected pair paths/hashes, and `projection.requested`.
2. The projector claims the exact intent under the local lock, renders canonical YAML and deterministic Markdown into same-directory temporary files, validates both, and fsyncs where supported.
3. It atomically renames each file. Because the pair cannot be filesystem-atomic, readiness remains blocked until both final files exist and hash-match the same source version.
4. A short DB transaction records both hashes/result and emits `projection.written`; a known rendering/path/security error records `projection.failed`.
5. A checkpoint request may include only `recorded` pairs at or before its DB sequence. The Git change allowlist contains the checkpoint plus those exact ready pairs and nothing else.

Checkpoint publication first records a durable intent, snapshots the active DB through SQLite Backup API to a temporary file, runs identity/integrity/foreign-key checks, atomically replaces only the tracked checkpoint in the fixture coordination worktree, verifies the exact Git diff, and creates one project-Git commit. The commit footer binds checkpoint ID, DB sequence, replay-point range, snapshot SHA-256, and product-state commit/tree; the DB does not contain the hash of the commit that contains itself. The active DB records the Git result afterward, and the next checkpoint carries that prior result.

## 7. Context/query allowlists, trust classes, provenance, and prompt injection

Queries are bounded by exact run, event, delivery, artifact-version, outbox, checkpoint, replay-point, or compiled-profile ID. Agents cannot request full-table dumps, raw checkpoint bytes, arbitrary paths, or direct SQL. Q primary worktree excludes all `.pipeline/**`; required evidence is delivered as a typed secondary bundle, never by indexing the checkpoint.

Fixture/product content, model output, projection drift, replayed response, tool output, and imported metadata are untrusted. They cannot declare schema/type/subscriber/owner/approval/root/path/executable/capability or change compiler outputs. Trusted authority comes only from hash-bound registries, authenticated owner inputs, deterministic guards, and exact control requests.

Provenance binds Pipeline/fixture Git identities, DB instance/schema/sequence, compiler inputs/output digest, producer and invocation/result, context/replay point, artifact parents, event causation/correlation, schema/hash profile, target root/worktree, renderer/tool versions, and result hashes. Secret/PII findings block persistence/publication and trigger quarantine; secrets are never valid replay payload.

## 8. Current roster, inputs, outputs, capabilities, and stop conditions

| Deterministic component | Input | Output | Capability | Stop condition |
|---|---|---|---|---|
| schema/profile validator | typed request plus canonical schemas/compiled digest | validated request or typed rejection | registry/schema reads only | unknown, stale, oversized, or unauthorized field |
| transaction writer | validated request and expected revision | immutable IDs/result | short active-DB write | lock/revision/constraint/integrity failure |
| subscription materializer | event plus compiled profile | immutable delivery snapshot | compiled-profile read and DB write | dangling/conflicting subscriber or terminal policy |
| projection outbox/projector | committed decision intent | validated YAML+MD pair and hashes | exact temp/final decision paths | drift, partial pair, renderer/schema/path failure |
| checkpoint publisher | exact publish request and ready projections | verified snapshot/Git result | SQLite backup and allowlisted coordination-worktree Git write | threshold/root/diff/integrity/publication conflict |
| replay/reconciliation materializer | durable intents, checkpoint and replay refs | verified new runtime state or blocker | isolated fixture restore/readback | incomplete/incompatible/ambiguous state |
| compatibility/backup reader | DB/Pipeline/schema pins | diagnostic, backup/upgrade/restore evidence | read-only diagnosis and new-path backup/restore | newer DB, failed integrity, absent HITL |

There are seven deterministic components and zero artifact/event-plane LLM workers. S0, Layer0, fixture workers, model reviewers, and the compiler engine are external interface actors/components owned by their respective plans.

Deferred interfaces are real-project artifact catalogs, domain layer events, dialogue, leases/general retries/dead letters, full invalidation families, external side effects, G/Q binary payloads, CAS/LFS/external storage, distributed publication, cache/scale/RAG, and M subscribers. They gain internals only at their just-in-time gate.

Roster section sub-budget: `<=55` non-empty lines.

## 9. Failure taxonomy, invalidation, replay, recovery, abort, and duplicate suppression

| Failure | Deterministic outcome / owner |
|---|---|
| schema/type/owner/ref/profile mismatch | reject before write; artifact/event owner finding and `error.schema_mismatch` request |
| unknown/dangling subscriber or terminal policy | compiler/runtime validation rejection; no event append |
| idempotency key reused with different canonical request hash | immutable conflict, block run; never return the first result as success |
| crash before DB transaction commit | no visible unit; same request may be revalidated and applied |
| crash after DB commit before response | unique key returns the exact committed IDs/result; no duplicate rows/events |
| crash after one projection rename | reconcile source/version/hashes; regenerate the whole pair from DB or block on unsafe drift |
| crash after pair rename before DB result | verify both exact hashes, record the one result, emit one `projection.written` |
| crash before checkpoint Git commit | verify/remove only the known temp state and repeat snapshot/publication under the same intent |
| crash after Git commit before DB result | locate exact footer/tree/snapshot hash, record existing commit; never create a duplicate commit |
| divergent checkpoint history or unrelated dirty path | fail closed; preserve evidence and route owner/recovery, never merge binary DB |
| incompatible/corrupt checkpoint or DB | read-only diagnosis; verified backup/forward migration or blocked restore to new path |
| abort with pending persistence | freeze new work, reconcile begun intent/result, preserve partial evidence; no blind rollback |

Append-once event ID plus unique `(run_id, event_type_version, idempotency_key)` suppresses duplicate event requests. Artifact publication uses `(run_id, producer_invocation_id, request_key)` plus canonical request hash. Deliveries use `(event_id, compiled_subscriber_snapshot_id)`. Projection uses `(source_decision_version_id, projection_profile_hash, pair_stem)`. Checkpoint publication uses `(db_instance_id, sequence, replay_range, trigger)` and verifies snapshot/Git hashes. A matching duplicate returns the original result; a non-matching duplicate is a blocker.

Reconciliation never guesses from filename presence. It compares durable intent, DB sequence, content/snapshot hashes, projection pair, Git index/tree/commit footer, and result history. Every state advance is idempotent and recorded; general retry/dead-letter machinery remains deferred.

Minimal replay preserves existing versions. A downstream revision creates a new revision request, invalidation edges, invocation IDs, artifact versions, and events only for the control-computed affected subgraph. Forensic replay restores the tracked checkpoint to a new runtime path, reconstructs the selected product tree/delta/envelope, injects labelled recorded responses, and must reproduce route/artifact/event identities as defined by the replay contract. Stochastic re-execution creates new attempt/output identities and compares only pinned semantic/safety properties.

Abort is not rollback. After control freezes routing, this plane accepts no new unrelated publication, records `run.abort_requested`, reconciles committed/pending artifact, projection, and checkpoint intents, preserves worktree/DB/evidence, and persists `run.aborted` only when no effect is unknown. Unknown external or Git state yields `run.blocked`, not fabricated completion.

Failure/recovery section sub-budget: `<=105` non-empty lines.

## 10. HITL, autonomy, approvals, compatibility, and dialogue

Automatic operations are schema/hash validation, short SQLite transactions, projection rendering, duplicate lookup, integrity checks, and read-only reconciliation. Run-authorized fixture operations are exact projection/checkpoint writes in the coordination worktree. HITL is required for the three-plan approval, executor binding, incompatible schema upgrade, destructive restore/history migration, threshold route, risk acceptance, and K0b-05 continuation.

`resume` preserves the original scope, schema/compiler/executor pins and authorization. A changed binding creates a new decision; a projection file or model response is never human approval. Restore targets a new path after verified backup and explicit authorization. In-place downgrade and overwrite are forbidden.

Creative dialogue is `N/A`: the K0b fixture decision input is predeclared/authenticated and tests projection mechanics only. Human/W5 terminal queues are safety endpoints, not dialogue or M automation.

## 11. Tools, side effects, security, egress, and repository boundaries

The active DB/WAL/SHM, temporary snapshots, and backups remain runtime-only. The only tracked binary is `.pipeline/history/pipeline-checkpoint.sqlite3` in the new fixture clone. Only the harness in the fixture coordination worktree writes it. Task worktrees exclude history/runtime/backups; Q primary worktree excludes all `.pipeline/**`. Pipeline Git and the canonical fixture are read-only. `projects/swarm` and `research/old-swarm` are outside capabilities.

Every filesystem/Git operation resolves and compares canonical repository root, repository role, top-level, branch/worktree/baseline, symlink/junction ancestry, target allowlist, and actual change set, then uses exact-root invocation. Broad `.pipeline` ignore, attached SQLite databases, extension loading, untrusted triggers/PRAGMAs, content-derived paths/commands, package hooks, push/merge/deploy, shared-checkout reset, and binary merge are forbidden.

The plane has no network or model egress. It persists only exact harness-visible response bytes already admitted by control; owner decision `K0b-D01` must bind the K0b executor before any physical call can create such bytes. Secret scanning precedes DB/checkpoint publication; a confirmed leak freezes the publisher and starts quarantine, rotation, history-rewrite, and clone invalidation evidence.

## 12. Context/scale policy, invocation and human-attention budgets

K0b operates on bounded fixture graphs and exact-ID queries. Repository-wide inventory, sampling, RAG, dynamic sharding, cache, and scale fallbacks are deferred. Size/event/query limits are compiled; unknown limits reject writes.

Plan production is the single package `K0b-plan-deltas`, light, six nominal/twelve worst-case calls: three separate authors plus three fresh-context reviewers, with at most one bounded author/reviewer return pair per plan inside the margin. Human attention is light: sessions `1/1`, blocking decisions `1/2`, active minutes `30/30`, maximum single session 30 minutes, batchable. This file consumes the second author call; it creates no reviewer call.

The distinct future package `K0b-runtime-operational` is standard at `16/30` calls, human standard at sessions `1/3`, decisions `2/4`, active minutes `30/120`, maximum 60 minutes, not batchable. This plane has zero LLM workers; runtime calls remain attributed once to S0/Layer0/workers/reviewers. Owner decision `K0b-D04` must reconcile F15's exact 36 physical attempts with the 30-call worst-case package before any call.

## 13. Binary payload budget and D0 reconciliation

This plane creates/first persists binary bytes, so `N/A` is forbidden. The candidate budget is bound to `d0-01-full-route-forecast` v2, SHA-256 `7e8a8da36c982b21bc25e1bbd1b1dd495f36f92446e7afbef4c6ce8cc8683840`, K0b row, and checkpoint policy v1, SHA-256 `8e9696916c939c6d9fa337c7bddc8b022c7657a2c105c0e51773b4c6ba1a67f3`.

| Required field | Candidate exact value |
|---|---|
| payload classes/media types | tracked SQLite checkpoint `application/vnd.sqlite3`; fixture-only generated page-churn/BLOB measurement seeds `application/octet-stream` |
| nominal/worst object count | checkpoints `14/34`; logical measurement seeds `6/12` |
| assumed mean object bytes | checkpoint `7,340,032/22,020,096`; seed `372,736/372,736` |
| hard per-object bytes | checkpoint `104,857,600`; seed `1,048,576` |
| nominal aggregate new bytes | checkpoint publication aggregate `102,760,448`; seeds `2,236,416`, included inside rather than added again to checkpoint snapshots |
| worst aggregate new bytes | checkpoint publication aggregate `748,683,264`; seeds `4,472,832`, included inside rather than added again to checkpoint snapshots |
| policy-permitted maximum aggregate | `1,073,741,824` phase pack bytes |
| fail-closed runtime aggregate limit | `1,073,741,824` phase pack and `104,857,600` per checkpoint, enforced independently |
| checkpoint publication count | `14/34` per K0b phase; at most `12` per run |
| pessimistic pack amplification | delta factor `1.0`; `7,340,032*14=102,760,448`, `22,020,096*34=748,683,264` |
| threshold status | nominal checkpoint/pack `below_warning/below_warning`; worst `below_warning/above_warning` |
| exact forecast binding | K0b fixture chain in the named D0 forecast; no cross-project byte carry |

The seed matrix is fixed before implementation: sizes `{4,096; 65,536; 1,048,576}` bytes times `{compressible; deterministic pseudorandom}` gives six nominal objects; the worst case repeats the six after page-rewrite/VACUUM, yielding twelve. Seeds are fixture-only, contain no imported/product bytes, are not artifact versions, and are not separate Git objects; their bytes are included in measured DB/checkpoint size to avoid double counting.

Two gate facts remain unresolved. First, the D0 K0b row classifies `binary_nominal/binary_worst_case` as zero while this scope explicitly first persists measurement BLOBs; that assumption variance requires an updated forecast/reconciliation and owner route before `K0b-01/02`. Second, the pinned planning-worst phase pack is already `above_warning`; `K0b-D03` therefore becomes applicable when the compiler confirms this scope and must choose narrow/batching, evidence-backed threshold change, storage migration, or pause. This plan selects none of those routes.

## 14. Downstream consumers and proof of actual consumption

Shared control consumes committed event/delivery, artifact, outbox, checkpoint, replay, and compatibility result IDs. S consumes revision/freeze/reconciliation status through control, never raw DB writes. The fixture CLI/acceptance gate consumes bounded lifecycle and lineage readbacks. Project Git/clean clone consumes only a verified checkpoint and ready projection pair. Human/W5 queues consume terminal error/incident records.

Actual consumption requires a durable record naming producer/consumer contract versions, exact event/artifact/result IDs, fields read, compiler/profile digest, validation outcome, DB sequence, and evidence ref. A stored row, generated file, Git commit, worker self-report, or event with no delivery/terminal result is insufficient. F13a must prove a clean clone consumes the tracked checkpoint without access to the source runtime DB.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: exact 21-event Alpha-0 catalog, schemas/producers/subscribers/terminal policies closed; compiled reachability has no dangling node; migration chain is forward-only.
- Contract: accept retained F00 bytes unchanged; reject unknown event/type/schema/owner, hash-as-identity, stale compiler digest, incomplete projection pair, unbudgeted binary, and conflicting idempotency reuse.
- Behavioral: atomic artifact/events/deliveries/outbox; bounded F04 snapshot/barrier; F05 immutable revision/invalidation; checkpoint allowlist and duplicate suppression.
- Crash: fault injection at every DB commit, projection rename/result, SQLite snapshot/replace, Git index/commit/result, migration, backup, and restore boundary; prove deterministic reconcile or typed block.
- Fixture: plane-owned portions of `F01-F05`, `F07`, `F09`, `F10`, `F13a`, and persistence/replay evidence for `F15` in a new committed clone.
- Security: wrong root/worktree, symlink/junction, dirty unrelated file, broad ignore, SQLite attach/extension/untrusted pragma, content-derived path, secret/PII, injection and forged approval all fail before forbidden effect.
- Storage: exact synthetic matrix measures checkpoint size/page churn/compressibility, snapshot/commit p95, pack delta factor, clone restore and threshold axes without silently changing policy.
- Real project: `N/A` and forbidden; no product source or external capability is present before later owner/program gates.

## 16. Evidence package and acceptance/readiness criteria

Architecture evidence binds this plan/baseline/scope/gate/forecast/policy hashes; exact author/reviewer ledger refs; all three delta hashes; typed findings/dispositions; complexity and complete binary counts; compiler input/output definitions; schema/migration identities; and unresolved owner decisions. No implementation file may exist at K0b-00 approval.

Later implementation evidence binds migration/contract/registry/compiler hashes; reference-equivalence results; DB and fixture Git identities; every artifact/event/delivery/outbox/checkpoint/replay ID and hash; idempotency duplicates/conflicts; fault-injection before/after proofs; projection pairs; checkpoint footer/tree; clean-clone restore; security negatives; storage matrix raw facts; exact commands/results; and owner dispositions.

Observability is raw, append-only evidence rather than a new KPI system: timestamps/durations for validation, transaction, projection, snapshot, Git commit and restore; DB/checkpoint/object bytes; publication count and pack delta; outbox age/state; duplicate/conflict counts; reconciliation path/result; integrity outcomes; and event/delivery terminal state. Records carry run/component/intent IDs and exact clock/source semantics. No dashboard, SLO, success threshold, sampling, or automated optimization is authorized beyond the pinned checkpoint policy; missing telemetry blocks the affected acceptance claim instead of being inferred.

Acceptance requires: all 18 categories; independent fresh-context review of this exact hash in a later invocation; author/reviewer ledger resolution; cross-plan owner consistency; zero unresolved review blocker; closed `K0b-D01`, `K0b-D02`, `K0b-D04`, binary forecast reconciliation, and any activated `K0b-D03`; full-file/routing/roster/failure budgets within caps; exact 21-event reachability; no partial projection/publication; deterministic crash/duplicate reconciliation; F13a clone-only replay; zero forbidden effects; and thresholds below stop or owner-routed.

`fixture_verified` is available only after K0b-04 evidence passes. `real_project_verified` is `N/A` and forbidden. Complexity evidence records full non-empty lines and routing/roster/failure counts against `800/105/55/105`; readiness statements without machine evidence are rejected.

## 17. Migration note from K0a and old pipeline

The approved K0a artifact/event plan, receipt, and F00 evidence are the source baseline. Retained are stable artifact-version identity, immutable versions/events/lineage, atomic publication, exact subscriber snapshot, textual F00 restrictions, untrusted-content treatment, and bounded readback.

Rewritten for K0b are F00-only checks into versioned registry/FK validation; terminal-only sink into compiled subscriptions; inspect-only replay into clone-only materialization; disposable interruption into intent/result reconciliation; no projections/checkpoints into outbox plus tracked snapshot publisher; and schema refusal into forward compatibility/backup evidence.

Retired behavior is filesystem truth, mutable history repair, implicit handoff, blind retry, binary merge, shared-checkout reset, manual projection synchronization, hash-as-identity, and model-selected schema/subscriber/owner. New tests cover migration preservation, event reachability, outbox pair crash recovery, checkpoint/Git uncertain-result reconciliation, duplicate suppression, binary limits, compatibility and F13a.

No old-pipeline or research source was read for this delta. No legacy schema, runtime file, prompt, product payload, or unapproved observation is imported.

## 18. Risks, open decisions, blockers, and deferred capabilities

| Item | Status / control |
|---|---|
| Executor bytes could be persisted under stale K0a authority | blocker `K0b-D01`; no physical K0b call or transcript until exact binding is owner-approved |
| Three plans could disagree on request/result ownership | blocker `K0b-D02`; owner approves/narrows/rejects only exact reviewed hashes and work-item boundaries |
| F15 has 36 required attempts but runtime package caps at 30 worst-case calls | blocker `K0b-D04`; revise/authorize a separate exact package or pause before calls |
| Binary seed classification differs from D0's zero-binary K0b row | forecast-variance blocker; updated forecast plus reconciliation and owner route required before first seed/checkpoint implementation |
| Planning-worst K0b phase pack is `above_warning` | conditional `K0b-D03` route becomes required when compiler confirms the crossing; no option chosen here |
| Filesystem/DB/Git cannot share one transaction | durable intent/result, exact hashes/footer, idempotent reconciliation and blocked readiness |
| Snapshot may leak secrets into Git history | pre-publication scan plus freeze/quarantine/rotation/history-rewrite/clone-invalidation runbook |
| Full SQLite checkpoints may scale poorly | measure in K0b; CAS/LFS/external storage remains forbidden without later owner architecture route |

The author makes no owner decision. Unresolved `K0b-D01`, `K0b-D02`, and `K0b-D04` block their affected implementation; `K0b-D03` follows its declared threshold activation. Independent review is intentionally not performed in this invocation.

Deferred capabilities remain real-product artifacts/events, research ingestion, N1 layer contracts, dialogue, leases/retries/dead letters, full domain event catalog, G/Q payloads, external effects, distributed publishers, CAS/LFS/external storage, scale/cache/RAG, release and M automation. This plan creates no implementation or readiness claim.
