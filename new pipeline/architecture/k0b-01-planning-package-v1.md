# K0b-01 Alpha Foundation Implementation Planning Package

| Field | Value |
|---|---|
| Plan ID | `k0b-01-alpha-foundation-planning-package-v1` |
| Version | `1.0.0` |
| Status | `planning_candidate`; plan only, not implementation or runtime authority |
| Work item | `K0b-01` |
| Exact scope | Alpha forward migration, registry/routing/resource-budget compilers, and the remaining minimal Alpha events |
| Checkpoint budget phase | `K0b-runtime-operational` only |
| Physical model calls | `0` nominal, `0` worst-case |
| Base Git commit/tree | `a031ee56a36cf794646643b67270c6e0f7092e08` / `fbda92274880ea684bebacc6bb58e12a40084d07` |
| Approval rule | A later owner disposition must bind the complete-file SHA-256 of this plan and an exact implementation write set before any planned file is created |

## 1. Authority, interpretation, and session boundary

The sole entry authority for this planning session is `new pipeline/decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml`, complete-file SHA-256 `544a6160fc27be348794179f44b44080b87bf3f53c0dd1b66baf9c7d1a40fe9d`. That disposition closes K0b-00 architecture and permits only a separate K0b-01 planning session. It grants no K0b-01 implementation authority.

This is a work-item implementation plan, not a fourth layer architecture plan and not a revision of any approved K0b-00 byte. The approved control, artifact/event, and S plans remain the architectural owners. This plan decomposes only their already approved K0b-01 intersection. It cannot revise an owner disposition, threshold, event set, role partition, call allocation, checkpoint phase, or cross-plane owner.

The planning result is this Markdown file only. This session does not create or change runtime code, SQL, contracts, registries, fixtures, prompts, checkpoints, projections, receipts, reviews, or design-invocation ledger entries. It launches no physical model call or independent review and uses no provider API.

## 2. Exact immutable inputs

Implementation planning is valid only while every binding below has the listed complete-file SHA-256.

| Role | Path | SHA-256 |
|---|---|---|
| Final K0b-00 disposition | `new pipeline/decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml` | `544a6160fc27be348794179f44b44080b87bf3f53c0dd1b66baf9c7d1a40fe9d` |
| Architecture baseline | `new pipeline/PIPELINE_V2_ARCHITECTURE_PLAN.md` | `f5877a07daabbb2ad5d846890587fcb033f58fc0dba49b36668ae476294447b9` |
| Development baseline | `new pipeline/PIPELINE_V2_DEVELOPMENT_PLAN.md` | `679a0bfa08d5c249968fe03ce91d85f9205bab6851c2f09aa9efada3f687382d` |
| K0b scope | `new pipeline/architecture/k0b-00-scope-envelope-v2.yaml` | `e839396d9199fa85e5474b3a45a852e7b6b59d81d6910ae67897f7dffe627cde` |
| K0b phase policy | `new pipeline/registry/checkpoint-budget-policy/k0b-phase-partition-v1.yaml` | `ed224c7473810be838c2c22129d567c337bd16fd13532efb893074e684367ce8` |
| K0b forecast | `new pipeline/evidence/k0b-00-updated-forecast-v3.yaml` | `ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a` |
| K0b binary reconciliation | `new pipeline/evidence/k0b-00-forecast-binary-reconciliation-v3.yaml` | `d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb` |
| K0b phase addendum | `new pipeline/architecture/k0b-00-checkpoint-phase-partition-addendum-v2.md` | `838fbec03184c587286dd37bc757a0fe7717d68c70454aef34650f51ba7db46c` |
| Shared control plan | `new pipeline/architecture/k0b-00-shared-control-plane-delta-v2.md` | `ce8c8a3160f52dae4f49d753f60ac2df202496c40697bca1d1cc5775908b17e3` |
| Artifact/event plan | `new pipeline/architecture/k0b-00-shared-artifact-event-plane-delta-v2.md` | `9586c4536144b612be58d6d01cc13f6437d31898c9bb40fb1c518602086a26ce` |
| S plan | `new pipeline/architecture/k0b-00-s-layer-delta-v2.md` | `e40b57493262d40c1eb48157de9dca216702b063cf3ffd5649238cfefe1e8be3` |
| Executor profile | `new pipeline/architecture/k0b-00-fixed-hybrid-manual-vscode-executor-profile-v1.yaml` | `125a1e30e4ca69ab812280a40ff57302a5211cd1b888b23a3e6d9a8620c3898d` |
| D0 layer gate | `new pipeline/decisions/d0-02-layer-architecture-gate.yaml` | `1bf92c755912a95ecf46e691454512f22a48fe97b59a5f7a676ac07e054478c4` |
| D0 forecast | `new pipeline/decisions/d0-01-full-route-forecast.yaml` | `7e8a8da36c982b21bc25e1bbd1b1dd495f36f92446e7afbef4c6ce8cc8683840` |
| Base checkpoint policy | `new pipeline/registry/checkpoint-budget-policy/v1.yaml` | `8e9696916c939c6d9fa337c7bddc8b022c7657a2c105c0e51773b4c6ba1a67f3` |
| K0a budget reference | `new pipeline/worksheets/k0a-00-budget-reference-v1.yaml` | `eab713455e593d556ee4c52668fe202649f969d79a6ebfa17ad10b237b4503f9` |

The later pre-implementation verifier must stop on the first absent or mismatched binding. Stale status fields in immutable K0b-00 inputs remain semantically superseded by the final disposition and must not be rewritten.

## 3. Scope envelope

### In scope after separate implementation approval

1. One forward-only schema step from the exact K0a schema-v3 chain to the K0b-01 Alpha foundation schema.
2. Canonical, closed source contracts and registry inputs for the exact 21-event minimal Alpha profile, subscription/terminal snapshots, the five approved S route classes, fan-out/barrier facts, and resource/checkpoint budget facts.
3. A deterministic registry/routing compiler that produces closed, hash-bound reachability, subscription, route, fan-out, checkpoint-phase, and publication-budget outputs.
4. A deterministic resource-budget compiler that computes invocation, human-attention, binary, checkpoint-publication, checkpoint-size, and phase-pack budgets and proves reference equivalence.
5. A fail-closed layer-plan `binary_payload_budget` validator implementing the full D0-02 required-field contract and N/A proof rule.
6. Deterministic migration, contract, structural, reference-equivalence, and negative tests using generated temporary databases and synthetic records only.
7. A K0b-01 validation record containing exact hashes, commands, exit codes, test counts, and limitations, without a readiness or runtime claim.

### Explicitly out of scope

- K0b-02 projection outbox, YAML/Markdown pair renderer, tracked checkpoint publisher, replay materializer, phase seal persistence/execution, and crash reconciliation.
- K0b-03 repository/worktree/path/symlink/tool/egress/secret/process enforcement and operational abort/compatibility implementation.
- K0b-04 scenario execution, synthetic BLOB/page-churn measurement, F15, any manual VS Code dispatch, and any physical model call.
- K0b-05 feasibility forecast, `continue_to_N1 | pause_program`, N1, real product work, release, deployment, or readiness claims.
- Prompts, model adapters, provider credentials, direct REST/SDK/Responses API, plugins/connectors, dynamic provider or model fallback, and inferred/static model identity.
- Threshold increase, storage migration, CAS/LFS/external backend, a third checkpoint-budget phase, arbitrary batch-as-phase, or any call/byte/publication credit.
- Reading, writing, executing, or importing the canonical fixture, `projects/swarm`, or `research/old-swarm`.
- Editing any K0a migration/contract byte or any K0b-00 hash-bound input.

## 4. Planned write set for a later implementation session

The paths below are candidates to be made exact by the later owner implementation disposition. No path is authorized by this plan alone.

| Area | Candidate new path(s) | Purpose |
|---|---|---|
| Contract package | `new pipeline/contracts/k0b01/alpha0-kernel-contract-package-v1.json` | Closed schemas and identities for events, profiles, compiler inputs/outputs, and validation receipts; no prompt text |
| Event registry | `new pipeline/registry/alpha0/event-profile-v1.yaml` | Exact 21 event types, versions, producers, consumers or terminal policies, and activation gates |
| Subscription registry | `new pipeline/registry/alpha0/subscription-terminal-profile-v1.yaml` | Immutable subscriber and terminal-policy snapshots with no dangling route |
| S routing registry | `new pipeline/registry/alpha0/s-routing-profile-v1.yaml` | Exact five route IDs, applicability, targets, F04 barrier, F05 owner rule, and phase fences |
| Budget policy | `new pipeline/registry/resource-budget-policy/v1.yaml` | Machine-readable counting rules, tier limits, required completeness, and hard-stop semantics |
| Reference cases | `new pipeline/registry/resource-budget-policy/reference-cases-v1.yaml` | Independent input graphs and expected outputs bound to the K0a worksheet, D0 forecast, and K0b forecast/reconciliation |
| Forward migration | `new pipeline/harness/migrations/0004_k0b01.sql` | Exact schema-v3 to schema-v4 forward transition; earlier migration bytes remain untouched |
| Deterministic harness | `new pipeline/harness/k0b01/` | Store upgrade adapter, strict contract/registry loaders, compilers, canonical hashing, and validators only |
| Migration tests | `new pipeline/tests/foundation/test_k0b01_migration.py` | Upgrade, preservation, backup/restore, old-reader rejection, integrity, idempotency, and failure atomicity |
| Contract/compiler tests | `new pipeline/tests/contracts/test_k0b01_contracts.py`, `test_k0b01_routing_compiler.py`, `test_k0b01_resource_budget.py` | Exact profile, reachability, deterministic digests, equivalence, and fail-closed negatives |
| Validation evidence | `new pipeline/evidence/k0b-01-validation-v1.yaml` | Deterministic evidence only; not an independent review or owner approval |

No CLI capable of dispatch, model execution, checkpoint publication, projection write, product effect, or network egress belongs in this work item. Compiled outputs used by tests are temporary outputs; they are not runtime activation records or Git checkpoint publications.

## 5. Forward migration design

The later migration must recognize only the exact historical chain:

- schema v1 / `0001_k0a01` / SHA-256 `9901b21aa733611a36191f07cb139b7a79b5d73fd0184e6347792b091adf4dc3`;
- schema v2 / `0002_k0a02` / SHA-256 `7539ab85afaddac2b520f806787177d78106a934e05f5e2a2229c3ef13c8456b`;
- schema v3 / `0003_k0a03` / SHA-256 `0e0b59b111e53406158c6d58ce533ab5b4676e90a6f1f9261583f1b73a79557b`.

The upgrade boundary is fail-closed:

1. Require an explicit source DB and an explicit new backup path; neither may be a canonical fixture path, a product path, or a tracked checkpoint path.
2. Verify source `user_version`, ordered migration rows and hashes, schema fingerprint, `integrity_check`, and `foreign_key_check` before mutation.
3. Create the backup with the SQLite Backup API, verify its byte hash and integrity, and record its locator/hash in temporary validation evidence. K0b-01 does not publish or commit it.
4. Apply the v4 migration in one immediate transaction. Existing CHECK-constrained F00 tables may be transactionally rebuilt only where necessary to support versioned Alpha bindings; all historical IDs, values, lineage, counts, and immutable rows must survive exact readback.
5. Insert exactly one immutable v4 migration record, set `user_version = 4`, then verify the complete v1+v2+v3+v4 schema fingerprint, integrity, foreign keys, row counts, content digests, and exact F00 graph readback.
6. On any failure, roll back the live DB and prove the verified backup restores into a different new path. There is no down migration and no destructive in-place restore.

The v4 logical schema must support versioned contract/profile bindings, immutable source and compiled profile identities, compiler input/output hashes, the Alpha event/delivery snapshots, and terminal human/W5 queue records needed by the approved terminal policies. Checkpoint publication, projection outbox, replay materialization, phase-transition/seal execution, Git effects, and their K0b-02 persistence tables remain absent from K0b-01; only their stable interface and compiler-output schema identities may be referenced. They cannot become operational through K0b-01.

K0a compatibility is asymmetric by design: the K0b-01 store reads and upgrades the exact v3 database, while K0a stores must reject schema v4 as newer/unsupported. No historical migration or K0a contract is edited to simulate compatibility.

## 6. Minimal Alpha event and terminal profile

The compiled public catalog is exactly 21 event types.

Retained byte-compatible K0a types are:

`command.received`, `run.started`, `artifact.version_created`, `handoff.ready`, `run.completed`.

The exact K0b-01 additions are:

`run.blocked`, `run.abort_requested`, `run.aborted`, `artifact.published`, `projection.requested`, `projection.written`, `projection.failed`, `revision.requested`, `gate.passed`, `approval.requested`, `approval.granted`, `approval.rejected`, `error.schema_mismatch`, `error.tool_failure`, `error.security_policy`, `meta.incident_detected`.

Each registry entry must contain an exact type/version, payload-schema identity/hash, semantic producer owner, allowed subscriber set or terminal policy, fields consumed, activation work item, replay/idempotency semantics, and terminal disposition. Unknown types and unknown fields fail closed. The retained F00 `handoff.ready -> bootstrap_sink` route remains valid only under the exact F00 package and is forbidden for Alpha routes.

The K0b-01 contract subset plans the approved identities `artifact-publication-request` v2, `artifact-version-record` v2, `event-envelope` v2, `event-delivery-snapshot` v2, `key-decision-record` v1, and `model-execution-receipt-ref` v1, together with `pipeline-v2.s-route-profile` v1, `pipeline-v2.s-route-proposal` v2, `pipeline-v2.s-revision-owner-proposal` v1, and `pipeline-v2.s-route-freeze-policy` v1. Projection-outbox, checkpoint-publication, replay-materialization, phase-transition, and phase-seal persistence stays with K0b-02 even where K0b-01 defines a stable input/output interface needed for compilation.

The three error types have terminal policy `block_run_and_enqueue_human`. `meta.incident_detected` has terminal policy `persist_incident_and_enqueue_W5`. Those policies create durable typed queue evidence without pretending that full M is active. Events owned by K0b-02 or K0b-03 interfaces may compile in the static Alpha graph, but their emission and consumption remain activation-gated until the owning implementation/evidence exists. A declared future interface is not a runtime receipt or readiness claim.

The compiler must prove that all 21 events have a producer/bootstrap source and a subscriber/terminal outcome, that every consumed field has an owner, and that no event, decision, evidence, route, or coverage edge is dangling. Adding dialogue, lease/retry/dead-letter, budget-escalation, cache/scale, deferred, full replay, or layer-domain event families fails this plan's scope check.

## 7. Registry and routing compiler

The registry compiler is deterministic and has no LLM, tool broker, provider, filesystem-effect, or runtime scheduling authority. It consumes only exact hash-bound source documents and returns canonical outputs plus hashes.

Required output families are:

- `compiled_artifact_event_profile`;
- `compiled_event_reachability_graph`;
- `compiled_subscription_terminal_snapshot`;
- `compiled_s_route_table_v2`;
- `compiled_fanout_barrier_profile`;
- `compiled_resource_forecast`;
- `compiled_checkpoint_phase_partition_v1`;
- `compiled_checkpoint_publication_budget_v2`.

The exact S route IDs are `s.alpha0.compiled_nominal.v1`, `s.alpha0.layer0_fallback.v1`, `s.alpha0.f04.parallel_review.v1`, `s.alpha0.f05.revision.v1`, and `s.alpha0.blocked.v1`. F04 contains exactly `fixture.alpha0.primary_reviewer` and `fixture.alpha0.adversarial_reviewer` with `all_required`. F05 keeps `revision_owner_zero_role_id` distinct from `producer_invocation_id` and resolves the owner to `fixture.alpha0.upstream_zero`. Direct actor-to-actor handoff, dynamic membership, quorum/first-success substitution, and actor-selected route/capability/event/model are rejected.

Canonical output ordering must be defined for maps, sets, graph nodes, graph edges, roles, phases, triggers, and budget packages. The aggregate digest binds every source file hash, compiler version/hash, contract/schema versions, output-family hash, and the exact authority hashes in section 2. Repeated compilation from the same bytes must produce byte-identical canonical output and digest, independent of working directory, locale, time, map insertion order, or absolute path.

Negative compilation must reject missing nodes or terminal policies, duplicate identities, unknown owners, cycles where acyclicity is required, incomplete fan-out/barriers, undeclared retry/dialogue graphs, overlapping routes, stale schema/profile/compiler hashes, unknown capabilities, and any runtime patch of compiled bytes.

## 8. Resource-budget and binary-budget compilers

The resource compiler takes a complete route/fan-out/retry/dialogue graph, per-role call class, package identity, human-attention facts, replay/tool/side-effect facts, binary budgets, checkpoint policy, and the two-phase overlay. Absence must be an explicit bounded zero with proof; omitted/unknown data is not zero and blocks compilation.

Invocation rules are exact: compiled deterministic fast paths cost zero model calls; S0/Layer0, workers, runtime reviewers, dialogue roles, bounded retries, and non-nominal fallbacks count. `light` is at most `12/20`, `standard` at most `30/50`, and `deep` requires an exact nominal/worst count and owner authority. Package IDs are unique; plan-production and runtime calls never credit one another.

Human-attention output includes package-scoped profile, nominal/worst sessions, blocking decisions and active minutes, maximum single-session minutes, and `batchable_requests`. A phase label never substitutes for package facts, and a high-attention package requires its own future capacity receipt.

The layer-plan binary validator implements all D0-02 fields: payload classes/media types, nominal/worst object count, assumed mean object bytes, hard per-object bytes, nominal/worst aggregate new bytes, policy-permitted maximum aggregate, runtime aggregate limit, checkpoint-publication count, pessimistic pack amplification, and exact forecast ref/hash. N/A is accepted only when the contract prohibits binary persistence and uses version references to already budgeted producer payloads. Per-object and aggregate bounds both fail closed.

Checkpoint arithmetic uses integer bytes and the owner-approved formulas:

- window publications = `max(ceil(replay_points / 10), ceil(publisher_eligible_minutes / 5), ceil(new_db_bytes / 33554432))`;
- checkpoint bytes are rounded up to a whole MiB;
- phase pack = rounded cumulative checkpoint bytes times publications owned by that checkpoint-budget phase times factor;
- factor is `1.0` until replaced by separately approved measurement;
- overlap, compression, delta, dedup, cross-phase, retry, or batch-reset credit is `0`.

Reference-equivalence is not allowed to feed an expected output back as the calculation. Versioned cases must contain independent input graphs and expected outputs. At minimum they cover the K0a worksheet, the D0/K0b package rows, both K0b phase forecasts, control and S binary N/A proofs, and the artifact/event seed budget. Every selected field and value must match exactly; extra, missing, coerced, rounded differently, or merely approximately equal output fails.

## 9. Exact two-phase and dispatch invariants

The compiler always emits exactly two chronological, contiguous, non-overlapping, exhaustive K0b checkpoint-budget phases in this order:

1. `K0b-runtime-operational`;
2. `K0b-F15-exact-measurement`.

K0b-01, K0b-02, and K0b-03 have zero physical model calls and belong only to `K0b-runtime-operational`. All `16/30` non-F15 physical-call capacity belongs to pre-F15 K0b-04 and must be terminal before the operational seal. The second phase starts only from that verified seal, contains exactly `36/36` F15 calls, deterministic post-F15 K0b-04 closure and deterministic K0b-05 in the same top-level run segment, and permits zero non-F15 or post-F15 model calls.

The F15 boundary allowlist is exactly one of each:

- `k0b.f15.boundary.entry_gate`;
- `k0b.f15.boundary.program_owner_wait_or_exit`;
- `k0b.f15.boundary.exit_gate`;
- `k0b.f15.boundary.top_level_run_end`.

The compiler must preserve the unchanged hard limits: checkpoint `< 104857600` bytes, phase pack `< 1073741824` bytes, warning at `536870912` bytes, publication batch at most `12`, publication p95 below `10` seconds, and clean-clone restore below `120` seconds. It must reproduce operational `9437184/27262976` checkpoint bytes, `14/34` publications, and `132120576/926941184` pack bytes; F15 `10485760/36700160`, `12/26`, and `125829120/954204160`; seed count `6/12` and seed bytes `2236416/4472832`; and cumulative observable pack sum `257949696/1881145344` without treating the sum as phase credit.

An unclassified or multiply classified member, phase gap/overlap/reorder/reopen, third phase, stale/missing predecessor seal, fifth trigger, separate K0b-05 run, post-seal non-F15 call, post-F15 call, or checkpoint/phase pack at or above hard produces a blocking result. F15 publication count above the forecasted `26` requires pre-effect reforecast; `29` is the maximum count strictly below the hard byte bound at the approved worst checkpoint, and `30` or more blocks unconditionally. K0b-01 compiles and tests these rules but does not activate a phase, write a seal, publish a checkpoint, or dispatch a call.

## 10. Verification plan for the later implementation

### Migration and compatibility

- Build schema v1 through v4 from exact migration bytes and match a deterministic schema fingerprint.
- Upgrade a generated v3 database containing representative K0a F00 rows; prove stable IDs, byte-equivalent content, lineage, delivery snapshots, manual receipts, counts, and hashes.
- Prove repeated v4 initialization is idempotent and changed/missing/extra/reordered migration records fail.
- Inject failure before backup, after backup, during table copy, before migration-row insert, and before commit; prove either exact v3 or exact v4, never a partial schema.
- Prove a v3 backup restores to a distinct new path and both old K0a store classes reject v4 without mutating it.

### Contracts, events, and reachability

- Accept exactly the 5 retained plus 16 added event types and reject an undeclared twenty-second type.
- Prove F00 identities and its fixture-only sink are unchanged and cannot be reused by Alpha.
- Prove each event's producer, subscriber/terminal snapshot, consumed fields, idempotency, replay semantics, and activation gate are complete.
- Prove error and incident terminal policies create typed human/W5 queue evidence and cannot claim M readiness.
- Prove projection/checkpoint/abort interfaces remain inactive until their owning later work-item evidence is bound.

### Routing and deterministic compilation

- Compile the same inputs under varied ordering, locale, cwd, and temporary root and compare exact canonical bytes and digest.
- Exercise all five route classes, F04 exact membership/barrier, F05 owner/producer distinction, phase fences, and nominal zero-call fast path.
- Reject unknown/overlapping/cyclic routes, direct handoff, dynamic reviewer membership, incomplete barriers, capability widening, stale pins, and content-selected policy.

### Resource and checkpoint budgets

- Prove exact field/value equivalence for every approved reference vector and independently recompute every formula.
- Reject incomplete route/fan-out/retry/dialogue graphs, duplicate package IDs, unknown tier/count, overflow, non-integer/coerced values, and hidden calls.
- Reject incomplete binary budgets, false N/A, per-object or aggregate overflow, stale forecast binding, changed seed assumptions, and unreconciled variance.
- Prove the exact two-phase ordering, work/call membership, four trigger IDs, 12-publication batches, strict hard comparisons, and zero-credit arithmetic.
- Include boundary vectors at warning, one byte below hard, exactly hard, and one byte above hard; exactly-hard is blocking.

Tests use only temporary generated databases and synthetic records. They do not copy, open, execute, or mutate the canonical fixture or either forbidden legacy/product directory. They perform no network access, provider call, manual UI dispatch, Git commit, or checkpoint publication.

## 11. Runtime-prerequisite matrix

| Final K0b-00 prerequisite | K0b-01 responsibility | Later owner |
|---|---|---|
| Separate hash-bound K0b-01 plan and scope authority | This file supplies the plan candidate; a future owner disposition must bind its complete-file hash and exact write set | Owner before implementation |
| Forward migrations, compilers, minimal Alpha events | Implement and verify only after that disposition | K0b-01 |
| Compiler reference equivalence and fail-closed layer-plan binary validator | Full responsibility and exit-gate evidence | K0b-01 |
| Exact manual model/model-ID receipt before every dispatch | Preserve as a compiler/executor binding; create no receipt or dispatch | K0b-04 pre-dispatch |
| Fixed role partition, extension version/profile, UI evidence, visible transcript controls | Bind exact approved profile hash and reject stale/missing future inputs; no adapter here | K0b-03/K0b-04 runtime |
| Phase membership, predecessor seals, four-trigger allowlist, publication caps, no-credit arithmetic | Compile and test immutable membership/budget outputs; no persistence/effect | K0b-01 compile, K0b-02 persistence, K0b-04 execution |
| Contract/harness/security/replay/crash/abort/clean-clone conformance | Migration/contract/compiler subset only | K0b-02/K0b-03/K0b-04 for remaining proof |
| No calls until later package and all pre-dispatch gates | Hard-coded zero-call K0b-01 scope and negative tests | All later work items |

## 12. Entry, exit, handoff, and stop conditions

### Entry gate for a future K0b-01 implementation session

All of the following are mandatory before the first implementation write:

1. HEAD remains the authorized K0a baseline unless a separate owner record explicitly changes it; every section-2 hash matches.
2. A new owner disposition binds this plan's complete-file SHA-256, exact allowed write set, implementation session, and zero-call scope.
3. Any requested independent review has separate explicit necessity and budget authority. No expired K0b-00 design ordinal `29` or `30` is reused or reallocated.
4. The implementation session reconfirms no canonical-fixture, `projects/swarm`, or `research/old-swarm` access and no API/model-call authority.
5. Existing user changes are inventoried and preserved; no hash-bound K0b-00 or K0a byte is edited.

### K0b-01 exit gate

K0b-01 may be reported complete only when the separately authorized write set exists and:

- the exact forward migration, preservation, backup/restore, integrity, old-reader rejection, and failure-atomicity tests pass;
- the 21-event contract and all subscriber/terminal reachability tests pass with zero dangling edge;
- routing outputs are byte-deterministic and every positive/negative route vector passes;
- resource, human, binary, checkpoint, and two-phase outputs exactly match all bound reference cases;
- the binary-budget validator rejects every missing, false-N/A, over-limit, stale, or unreconciled case;
- source-to-compiled hashes, schema/migration hashes, commands, exits, and test counts are recorded in deterministic evidence;
- no runtime phase is activated, no checkpoint/projection is written, no physical/model/API/network call occurs, and no readiness claim is made;
- HEAD and every immutable authority hash remain unchanged.

Passing K0b-01 authorizes only consideration of K0b-02 and K0b-03 under their own scope authority. It does not authorize K0b-04, F15, a manual model receipt, N1, a real project, commit/push/PR, or release.

Stop immediately on a stale hash, scope overlap with K0b-02/03, ambiguous migration preservation, incomplete graph/budget, any phase or threshold variance, need to access a forbidden root/fixture, need for a physical call/API, or an unapproved write path. The only permitted response is read-only diagnosis and an owner-facing scope/budget/authority request; no silent narrowing, widening, fallback, or credit is allowed.
