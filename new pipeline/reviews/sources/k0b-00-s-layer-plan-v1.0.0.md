# K0b-00 S Layer Operational Delta Plan

- Plan ID: `k0b-00-s-layer-delta`
- Version: `1.0.0`
- Status: `review_candidate_not_approved`
- Baseline: `new pipeline/architecture/k0a-00-s-layer-v1.md`, version `1.2.0`, SHA-256 `9daf44b49451f5261d618ca183cb50d6c793b608e03caeca2c07788068d55a77`
- Common scope: `new pipeline/architecture/k0b-00-scope-envelope-v1.yaml`, version `1.0.0`, SHA-256 `fe63742498a8192c7f67c5d430eb8c466d3621d873e3486115102510e7ca779a`
- Author input: `new pipeline/evidence/k0b-00-s-author-input-v1.yaml`, version `1.0.0`, SHA-256 `9e9f348d0b9f162f998abd7e861d34d66b56ac370e01b1d8afd87503a1c7d9d2`
- Entry commit/tree: `a031ee56a36cf794646643b67270c6e0f7092e08` / `fbda92274880ea684bebacc6bb58e12a40084d07`
- Complexity tier: `narrow`; full-file cap `<=500` non-empty lines; routing `<=95`; roster `<=45`; failure/recovery `<=95`.

This document is a delta. Every unchanged K0a S v1.2.0 rule, especially the approved F00 disposition, remains binding. Sibling K0b deltas are provisional compatibility inputs, not owner-approved authority.

## Scope envelope

| Dimension | K0b S delta |
|---|---|
| Applies to | semantic routing for the Alpha-0 fixture scenarios `F01`, `F02`, `F03`, `F04`, `F05`, `F07`, `F09`, `F10`, `F13a`, `F15` |
| Runtime location | a future committed independent fixture clone, never the canonical fixture worktree |
| Current S roster | exactly one S0 semantic dispatcher and zero S workers |
| Added semantics | compiled nominal applicability; fail-closed ambiguity; Layer0 fallback declaration; bounded F04 fan-out; F05 revision ownership; abort/reconciliation route freeze |
| Retained semantics | F00 always makes one real S0 call, returns only raw `s0_route_proposal`, and relies on deterministic harness validation/persistence |
| Downstream ownership | shared control compiles and executes; shared artifact/event persists and publishes; S owns neither |
| Readiness claim | fixture-only operational Alpha-0 after K0b-04; no real-project or product-readiness claim |

This author invocation creates only this plan, its exact input manifest, and one design-ledger entry. It creates no contracts, registries, prompts, migrations, runtime code, fixture changes, projection/checkpoint output, model call, review, or approval.

## 1. Purpose, responsibility, non-goals, and applicability

S is the semantic routing authority. It defines route classes, applicability predicates, ambiguity and blocker meaning, permitted fallback class, revision-owner resolution, and route-freeze/unfreeze semantics. S0 remains the only S reasoning actor.

S is not a scheduler, compiler, persistence layer, subscriber registry, tool broker, checkpoint publisher, projection renderer, budget allocator, or recovery executor. It cannot turn a proposal into authority, widen a compiled capability/event/root set, or call another actor directly.

The delta applies only after all three exact K0b plans are independently reviewed and owner-approved. `K0b-D01`, `K0b-D02`, `K0b-D04`, the activated `K0b-D03`, and binary-forecast reconciliation remain unresolved; affected implementation and all physical K0b calls remain blocked.

## 2. Dispatcher, deterministic harness, compiler, and plane boundaries

| Boundary owner | S-supplied or consumed meaning | Explicit exclusion |
|---|---|---|
| S plan/S0 | semantic source profiles and bounded raw route/revision proposals | no compile, schedule, persistence, tool, DB, Git, or direct handoff |
| Shared control | validate semantic source; compile closed tables/graphs/forecasts; schedule and fence effects | cannot invent route meaning or persist events/artifacts |
| Shared artifact/event | persist compiled snapshot, proposals, decisions, events, deliveries, outbox and checkpoints | cannot choose routes, revisions, freeze state, or invocations |
| Layer0/fixture actors | return only typed proposal/result for an exact scheduled envelope | cannot select owner, route, subscriber, capability, or side effect |

Future K0b-01 contracts, if separately authorized, use these canonical semantic schema identities: `pipeline-v2.s-route-profile` v1, `pipeline-v2.s-route-proposal` v2, `pipeline-v2.s-revision-owner-proposal` v1, and `pipeline-v2.s-route-freeze-policy` v1. This plan defines their required meaning but does not create schema files.

The route-profile source must bind `profile_id/version/hash`, applicable event/profile/schema versions, machine-known predicates, route class, target contract, allowed capability/event/root sets, proposal schema, fallback class, reviewer membership and barrier where applicable, revision-owner rule, freeze behavior, and compatibility range. Unknown or open-world fields fail compilation.

Shared control deterministically produces a closed route table, event reachability graph, fan-out/barrier profile, and resource forecast. Each output records the exact S profile version/hash. A compiler output is control-owned derived authority, not an S-authored decision or model result. The artifact/event plane persists only the exact compiled snapshot selected by control.

## 3. Semantic state machine, invariants, and terminal states

S-facing semantic states are:

```text
route_requested -> compiled_nominal | dispatcher_required | blocked_input
dispatcher_required -> proposal_received -> validated_route | failed_validation | blocked_semantic
validated_route -> scheduled | route_frozen
revision_requested -> owner_resolved -> replay_scope_requested | blocked_revision
route_frozen -> resume_eligible | aborted | blocked_reconciliation
```

These are semantic dispositions. Shared control owns durable run/invocation state and validates every transition; shared artifact/event owns persistence. S0 cannot write or advance either state machine.

Invariants: one command/event identity has one active compiled profile; every accepted proposal names one exact compiled route and target contract; no proposal widens compiled authority; unknown/stale/incompatible semantics block; route freeze prevents new deliveries but never deletes evidence; unfreeze requires a control-owned reconciled state with the same pinned profile or a separately approved compatibility migration.

`failed_validation`, `blocked_input`, `blocked_semantic`, `blocked_revision`, `aborted`, and `blocked_reconciliation` schedule no new reasoning actor. Terminal events and human/W5 routing follow the shared event profile; S does not mint a parallel terminal schema.

## 4. Input events, guards, routing, fan-out, barriers, and fast paths

S consumes bounded semantic views of `command.received`, compiled-profile status, validated downstream outcomes, `revision.requested`, abort/reconciliation status, and F04 barrier status. It receives IDs, enums, hashes, versions, guard results, and bounded non-secret intent fields, never raw DB/checkpoint/projection or repository contents.

Canonical K0b route identities are:

| Route ID | Guard | Semantic disposition |
|---|---|---|
| `s.alpha0.compiled_nominal.v1` | one exact machine-known outcome and every compiled guard true | control schedules without S0 or Layer0 dispatcher call |
| `s.alpha0.layer0_fallback.v1` | registered ambiguous/non-nominal case and owner-approved executor binding | control schedules the exact real-LLM Layer0 proposal envelope; validates before use |
| `s.alpha0.f04.parallel_review.v1` | exact F04 review profile and both reviewer contracts compatible | immutable two-member fan-out under `all_required` |
| `s.alpha0.f05.revision.v1` | accepted revision names an existing artifact/version and causal consumer | resolve producing upstream zero; request minimal descendant replay |
| `s.alpha0.blocked.v1` | missing, stale, conflicting, unknown, forbidden, or incompatible input | no dispatcher invocation or side effect |

F04 reviewer role IDs are exactly `fixture.alpha0.primary_reviewer` and `fixture.alpha0.adversarial_reviewer`; both are required external fixture actors, not S workers. The barrier is exactly canonical policy `all_required`: control may pass it only after one valid terminal result from each member of the immutable compiled snapshot. No quorum, first-success, dynamic membership, substitution, or reviewer-to-reviewer visibility is allowed.

For F05, S resolves semantic ownership to the producer invocation of the invalidated artifact version. Shared control validates existence/authority and computes the minimal executable invalidation subgraph; the artifact/event plane persists revision and invalidation edges. S cannot choose replay points or mutate lineage.

F00 is an explicit exception to the K0b compiled fast path: the historical one-route profile still makes its required real S0 call, admits only raw `s0_route_proposal`, and schedules nothing until deterministic validation persists `validated_route_proposal`. K0b cannot reinterpret or replace its evidence.

F15 uses the predeclared 12-case nominal/ambiguous/non-nominal oracle, three attempts per case. It requires 36/36 free of forbidden transition/capability/event, at least 34/36 oracle-matching initial choices, and at least 2/3 correct per case. Oracle labels, routes, prompts, model profile, and thresholds are pinned before any attempt. `K0b-D01` and `K0b-D04` block execution now.

Routing-section budget: `45` non-empty lines maximum for this section, within the `95`-line gate cap.

## 5. Output events, subscribers, terminal policy, and cross-plane handoffs

S0 emits no public event. It can return only a raw proposal admitted by its exact scheduled contract. Shared control validates it, owns `compiled_route_decision` and scheduling, and requests persistence of `validated_route_proposal`; shared artifact/event is the only persistence and subscriber authority.

S semantically classifies only routes, revision ownership, and freeze status. The minimal Alpha event profile remains exactly the 21 types in the common scope: five retained K0a types and sixteen K0b additions. S cannot add a type, subscriber, delivery, retry, error family, or terminal policy.

Errors terminate as `block_run_and_enqueue_human`; `meta.incident_detected` terminates as `persist_incident_and_enqueue_W5`. These are control/event-plane behaviors. S receives only the resulting bounded status and must not continue routing from a terminal event.

The only cross-plane semantic fields authored by S are profile identity, route class/ID, applicability disposition, exact target/reviewer/barrier references, revision-owner proposal, and freeze-policy reference. Correlation, idempotency, scheduling, event records, delivery snapshots, and acknowledgements are owned by the shared planes.

## 6. Artifacts, ownership, versioning, lineage, and key decisions

S owns no content artifact, event row, outbox item, checkpoint, projection, Git path, or binary object. Semantic profiles are versioned registry inputs only after K0b-01 authorization; raw and validated proposals are evidence records persisted by the artifact/event plane.

Lineage is `semantic profile -> compiled profile -> route request -> raw proposal when required -> validated decision -> invocation/delivery graph`. Revision lineage adds `consumer revision request -> invalidated artifact version -> producing upstream owner -> minimal replay subgraph`. Every edge uses stable IDs plus version/hash; hash is not identity.

Owner decisions remain external, durable decision versions. S can classify a route as blocked by `K0b-D01..D04` but cannot select an option, infer approval from prose/Git, or treat a review recommendation as approval.

Projection outbox, checkpoint publisher, replay materializer, crash reconciliation, canonical artifact/event schemas, and forward migrations belong to the artifact/event delta. S participates only through bounded route freeze and revision-owner semantics; it cannot read or write their payloads.

## 7. Context/query allowlists, trust, provenance, and prompt injection

The S0 input allowlist is: normalized bounded intent; event/run/invocation IDs; S profile and compiled-profile IDs/hashes; exact candidate route enums; machine guard results; target contract/version/hash; allowed capability summary; bounded prior disposition; and revision/abort/reconciliation status when applicable.

Untrusted fields include command text, artifact-derived summaries, model outputs, error text, and any external label. They are data, never registry names, code, paths, SQL, tool arguments, capability grants, subscriber IDs, or owner approval. The harness renders a typed envelope and validates exact echo/enum/schema fields.

Provenance binds source event, causal chain, producer, schema/profile/compiler/executor versions, hashes, and trust class. Missing or conflicting provenance blocks before a physical invocation. S receives no conversation transcript, arbitrary repository file, secret, raw peer output, research content, or product project content.

## 8. Current roster, inputs, outputs, capabilities, and stop conditions

| Actor/interface | Count | Input | Output | Capabilities and stop |
|---|---:|---|---|---|
| S0 semantic dispatcher | 1 | one exact typed route envelope | one raw route or revision-owner proposal | no tools/DB/Git/network/subagents; stop after one proposal |
| S workers | 0 | N/A | N/A | absent; adding one requires a new plan |
| fixture Layer0 fallback | external 1 per scheduled case | exact control envelope | typed proposal | not S roster; no authority widening |
| F04 fixture reviewers | external 2 | same immutable review snapshot | independent typed results | not S roster; no peer output before barrier |
| shared control/artifact planes | external deterministic | profiles/proposals/status | compiled/persisted evidence | ownership fixed in sibling plans |

S0 has no general dispatcher loop, memory, dialogue, retries, alternate-model selection, or dynamic roster discovery. It stops on accepted proposal, validation failure, ambiguity without approved fallback, incompatible profile, budget/security blocker, freeze, abort, or terminal run state.

Roster-section budget: `12` non-empty lines maximum for this section, within the `45`-line gate cap.

## 9. Failure taxonomy, revision, replay, recovery, abort, and duplicates

| Failure | Required semantic response |
|---|---|
| missing/stale/uncompiled profile or unknown route | `blocked_input`; no call or schedule |
| material ambiguity without exact fallback or executor | `blocked_semantic`; no guess |
| malformed, extra-field, wrong-target, or authority-widening proposal | `failed_validation`; no retry |
| F04 missing/duplicate/incompatible reviewer result | keep `all_required` unsatisfied and block completion |
| F05 owner absent or lineage ambiguous | `blocked_revision`; no broad replay |
| abort requested or crash reconciliation pending | freeze all new S-owned routes and fence late proposals |
| profile/schema/compiler/executor compatibility mismatch | block resume; require approved compatibility path |
| duplicate proposal with same identity and bytes | return original validated disposition; no new route |
| duplicate identity with different bytes or causation | security/schema blocker and incident evidence |

Shared control assigns idempotency identities and fences attempts; shared artifact/event enforces durable uniqueness and returns the original result for an identical duplicate. S never implements retry or duplicate storage. A failed validation cannot be resubmitted under the same identity, and a late result cannot unfreeze or revive a run.

Revision replay is minimal: S names only the semantic owner; control computes descendants and before/after replay points; artifact/event materializes persisted inputs and immutable invalidation edges. Unaffected ancestors and parallel branches are reused only after hash/compatibility proof. General retry, dead-letter, speculative replay, and recursive self-repair are deferred.

Abort is monotonic from S's perspective. On `abort_requested`, S freezes route issuance; after control/event reconciliation, terminal `aborted` remains frozen. Resume is allowed only from non-terminal recovery state with matching pinned bindings and an explicit control-owned `resume_eligible`; S never infers safety from missing work or files.

Crash consistency is proved outside S by atomic state/event/outbox transitions and intent/result reconciliation. S acceptance requires evidence that a crash before/after proposal validation produces at most one scheduled route, no lost accepted proposal, no duplicate F04 member, and no route while frozen.

Failure/recovery-section budget: `32` non-empty lines maximum for this section, within the `95`-line gate cap.

## 10. HITL, autonomy, approvals, compatibility, and dialogue

There is no dialogue protocol. S0 performs one bounded autonomous classification per scheduled envelope; it cannot ask the user, negotiate scope, or self-approve. Human/W5 receives only typed blocker/incident evidence through the shared terminal policy.

Owner action is required for `K0b-D01` executor binding, `K0b-D02` exact three-plan hashes/scope, activated `K0b-D03` checkpoint route, `K0b-D04` F15 call-budget reconciliation, and the D0 binary-forecast variance. This plan chooses none.

Compatibility is exact and fail-closed. A run binds Pipeline commit/tree, S profile, compiled outputs, schemas, executor, fixture, and event profile. Resume under any changed binding requires a reviewed compatibility declaration and deterministic migration/restore evidence from the owning planes; otherwise it blocks.

## 11. Tools, side effects, security, egress, and repository boundaries

S0 and S have no tools, shell, filesystem, database, Git, network, provider-selection, credential, plugin, package, process, worktree, checkpoint, or projection capability. A future physical model call crosses only the control-owned executor boundary selected by `K0b-D01`.

Content cannot form paths, arguments, registry keys, subscriber lists, reviewer identities, capabilities, or event types. Unknown fields and prompt attempts to override roles/authority are rejected. Raw provider/tool bytes are never exposed to S persistence.

Runtime, if later approved, occurs only in a new committed independent fixture clone. Pipeline Git is read-only; canonical fixture is immutable; scenario coordination owns its worktree; task worktrees exclude history/runtime/backups; Q excludes `.pipeline`; `projects/swarm`, `research/old-swarm`, real products, push/merge/deploy/release and arbitrary egress are forbidden.

## 12. Context scale, invocation budget, and human attention

S context is one bounded event/route envelope. Repository scans, RAG, sharding, caching, batch reasoning, peer transcripts, alternate-model fallback, and unbounded history are N/A. Overflow blocks without truncating authority fields.

`K0b-plan-deltas` is one light package at `6/12` design calls: three separate authors plus three fresh-context reviewers nominal, with at most one bounded return pair per plan in the worst-case margin. Human attention is light at `1/1` sessions, `1/2` blocking decisions, `30/30` active minutes, 30-minute maximum, batchable. This file is the third initial author call; the five earlier artifact/control author/review calls plus this call make six ledgered design invocations, with no duplicate package.

Future `K0b-runtime-operational` is standard at `16/30` physical calls across K0b-01..05. S owns no independent additive package and may allocate no call. F15 requires 36 attempts, so `K0b-D04` must revise or separately authorize the package before execution; hidden/post-hoc credit is forbidden.

## 13. Binary payload budget or proved N/A

`N/A` is executable for S: schema contracts must admit only IDs, enums, booleans, bounded numbers, hashes, version references, and bounded canonical UTF-8 JSON/text. They must reject BLOB fields, base64/opaque byte envelopes, media/archive/checkpoint/projection bodies, raw tool/provider streams, and filesystem handles.

S-attributable binary objects and bytes are exactly zero nominal and worst-case. Checkpoint/BLOB measurement inputs are first persisted only by the artifact/event plane under its seed-inclusive budget. Any S binary field or persistence API invalidates N/A and blocks implementation pending a full machine-readable budget and D0 reconciliation.

## 14. Downstream consumers and proof of actual consumption

Shared control consumes the S semantic profile only by compiling it into exact route/reachability/fan-out/resource outputs, and consumes a raw proposal only by recording deterministic validation and scheduling the matching compiled target. Shared artifact/event consumes accepted records only through exact persistence requests; Layer0/reviewers/workers consume only control-created invocation envelopes.

Actual consumption evidence names producer/consumer IDs, contract/profile/compiler versions and hashes, fields read, decision/delivery ID, and accepted/rejected disposition. A stored profile, model self-report, or generated file without a control decision is not consumption.

For F04, consumption requires two member deliveries and one `all_required` barrier evaluation over the immutable reviewer snapshot. For F05, it requires an owner-resolution record that control uses to compile the minimal replay subgraph. Freeze consumption requires evidence that control created no new delivery until reconciled unfreeze.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: one S plan, one S0, zero S workers; all 18 sections; exact ownership; line budgets; no implementation files.
- Contract: closed semantic schema identities/versions; unknown field/route/reviewer/barrier/capability fails; F00 v1 behavior remains valid.
- Behavioral: compiled nominal route; ambiguous/non-nominal fallback; fail-closed blocker; F04 independent fan-out plus `all_required`; F05 owner/minimal replay; freeze/abort/reconcile; duplicate/late-result fencing.
- Fixture: S-owned portions of `F01`, `F02`, `F03`, `F04`, `F05`, `F07`, `F09`, `F10`, `F13a`, and the pinned F15 matrix in a new committed clone.
- Real project: N/A and forbidden; no product consumer or readiness claim exists.
- Negative: canonical fixture mutation, forbidden roots, direct handoff, dynamic roster, public S event, binary payload, hidden call, stale compatibility, and owner-decision inference all fail closed.

## 16. Evidence, observability, acceptance, and readiness criteria

Evidence binds entry commit/tree; scope/baseline/author-input/plan/review hashes; semantic profiles and compiler outputs; schemas/executor/fixture/event profile; raw and validated proposals; route/guard/decision/invocation/delivery identities; F04 snapshot/results/barrier; F05 lineage/replay subgraph; freeze/abort/reconciliation records; compatibility and owner-decision versions; F15 oracle/attempts; exact commands/results; usage; and finding dispositions.

Observability records route class and reason code, guard disposition, compiled-profile digest, proposal validator result, scheduled target, reviewer/barrier state, revision owner and replay-scope digest, freeze/unfreeze cause, duplicate/late-result fence, provider/model/parameters/token usage for physical calls, and terminal blocker. It records no secret, raw binary, unrestricted prompt context, or fabricated KPI.

Architecture acceptance requires: exact author manifest and ledger resolution; all 18 categories; an independent fresh-context review of this exact hash in a later invocation; no unresolved review blocker; consistent ownership with exact reviewed sibling hashes; owner closure of `K0b-D01..D04` and binary forecast; compiler reference tests for every route/negative case; route/roster/failure/full-file budgets within caps; binary N/A enforcement; and no runtime/contracts/migrations/fixture changes.

Operational acceptance later requires every assigned fixture scenario, F13a clean-clone replay, F15 thresholds and reconciled call authority, zero forbidden transitions/effects, exact two-reviewer barrier, deterministic minimal revision replay, freeze/crash/duplicate proofs, threshold route closure, and no product claim.

## 17. Migration note from K0a and old pipeline

K0a F00 evidence and its one real S0 call are immutable. K0b adds new versioned semantic profiles beside the retained F00 profile; it does not mutate historical proposal, event, route, invocation, or approval records.

Any future schema change is forward-only and owned by K0b-01 after approval. Compatibility tests must read retained K0a records unchanged, compile the new K0b profiles deterministically, reject mixed/stale bindings, and prove rollback/restore without deleting evidence. This plan creates no migration.

Old-pipeline content is not read or imported. Implicit handoff, free-form dispatcher output, agents selecting tools/routes, dynamic peer visibility, and file presence as state are retired concepts only; they are not compatibility inputs.

## 18. Risks, open decisions, blockers, and deferred capabilities

| Risk/blocker | Required disposition or mitigation |
|---|---|
| K0a manual transport assumed valid for K0b | `K0b-D01`; owner hash-binds one allowed executor route or pauses |
| three plans disagree on exact scope/ownership | `K0b-D02`; owner approves, narrows, or rejects exact reviewed hashes |
| planning-worst checkpoint phase pack is already above warning | `K0b-D03` is activated now; owner selects a storage/batching/threshold/pause route |
| F15 36 attempts exceed 30-call worst-case package | `K0b-D04`; revise matrix/package or pause before any call |
| D0 says K0b binary zero while artifact plan persists measurement BLOBs | corrected forecast plus reconciliation receipt and owner route required |
| compiled nominal path bypasses required F00 call | profile-level F00 exclusion plus regression proof |
| fallback proposal widens authority | closed compiled target/capability/event/root validation |
| F04 reviewers are miscounted as S workers or see peers early | exact external roles, zero S workers, immutable snapshot, `all_required` |
| revision selects a broad or wrong owner | producer-lineage proof; block ambiguity; control computes minimal subgraph |
| crash/abort permits a late or duplicate route | monotonic freeze, idempotency identity, durable fence/reconciliation proof |
| sibling control delta retains conditional wording for `K0b-D03` | cross-plan inconsistency must be corrected or dispositioned in a separate control-plan review/revision before approval |

Deferred: general multi-layer routing, dynamic roster/subscribers, quorum/first-success barriers, dialogue/HITL broker, leases/distributed scheduling, general retry/dead-letter, budget optimizer/escalation FSM, cache/scale/RAG, N1+ contracts, product aliases, research import, real-project execution, and automatic pipeline self-change.

The author makes no owner decision. Independent review is intentionally excluded from this author invocation. Until the exact reviewed plan and sibling set receive owner approval and every affected blocker is closed, K0b-01 implementation and all physical K0b calls remain forbidden.
