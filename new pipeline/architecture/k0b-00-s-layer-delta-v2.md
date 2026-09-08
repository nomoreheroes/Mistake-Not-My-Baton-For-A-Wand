# K0b-00 S Layer D03 Successor Delta Plan

| Field | Value |
|---|---|
| Plan ID | `k0b-00-s-layer-delta-v2` |
| Version | `2.0.0` |
| Status | `review_candidate`; no implementation or runtime authority |
| Work item / parent phase | `K0b-00` / `K0b` (`2.0b`) |
| Architecture owner | `S semantic routing` |
| K0a baseline | S v`1.2.0`, SHA-256 `9daf44b49451f5261d618ca183cb50d6c793b608e03caeca2c07788068d55a77` |
| Passing predecessor | K0b S v`1.1.0`, SHA-256 `c1e9eb94c639cb2e54e0d1b922b1e541557fc83370449578142a112f47381fd0`; review SHA-256 `605b7ccbe1f35da880c6cc6cfde79b8534a7c018d5970668c8ce6057276922b7` |
| Reviewed siblings | control v2 SHA-256 `ce8c8a3160f52dae4f49d753f60ac2df202496c40697bca1d1cc5775908b17e3`; artifact/event v2.2 SHA-256 `9586c4536144b612be58d6d01cc13f6437d31898c9bb40fb1c518602086a26ce` |
| Author input | `new pipeline/evidence/k0b-00-s-d03-v2-author-input.yaml`, SHA-256 `dfc0c885b5b5cd0f2780e7c3baa6e6d55d50ba4bdc1cabd047fc11d300ff8bf7` |
| Return budget authority | SHA-256 `d4fb22d5c980ccf9dd7b946cf60af6e3f9e9e3c0a07ae06303c123ca68978ba0` |
| Complexity tier | `narrow`; at most 500 non-empty lines; routing `<=95`, roster `<=45`, failure/recovery `<=95` |

## Bound scope and D03 authority

This is a new successor, not an edit of passing S v1.1. Every v1.1 semantic contract remains binding unless this plan explicitly adds a D03 phase-fence guard or records an already approved owner disposition. Exact cross-cutting authorities are policy overlay SHA-256 `ed224c7473810be838c2c22129d567c337bd16fd13532efb893074e684367ce8`, scope v2 SHA-256 `e839396d9199fa85e5474b3a45a852e7b6b59d81d6910ae67897f7dffe627cde`, forecast v3 SHA-256 `ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a`, reconciliation v3 SHA-256 `d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb`, and addendum v2 SHA-256 `838fbec03184c587286dd37bc757a0fe7717d68c70454aef34650f51ba7db46c`.

S owns semantic route meaning only. It consumes a control-owned phase admission/fence as a guard but cannot create, rename, classify, activate, seal or measure a phase; allocate a call; mint a trigger; publish a checkpoint; or start a new top-level run. The public event profile stays exactly 21 types. Only architecture/evidence/review/ledger records are permitted now; contracts, registries, prompts, migrations, code, fixture work, model calls, projections and checkpoints remain forbidden.

## 1. Purpose, responsibility, non-goals, and applicability

S defines closed route classes and applicability, ambiguity/block meaning, permitted fallback semantics, F04 reviewer/barrier meaning, F05 revision-owner resolution and abort/reconciliation freeze behavior. Exactly one S0 semantic dispatcher and zero S workers remain current.

S is not a compiler, scheduler, persistence plane, subscriber registry, tool broker, executor/model selector, budget/phase/trigger authority, projector, checkpoint publisher, recovery executor or approval source. Applicability is only the isolated fixture K0b scenarios F01-F05, F07, F09, F10, F13a and F15. Real projects, research, N1, M, general routing/retries/dialogue and release are out of scope.

## 2. Dispatcher, compiler, control, artifact/event, Layer0, and operator boundaries

| Owner | Exclusive responsibility | S exclusion |
|---|---|---|
| S plan/S0 | semantic source profiles and one bounded raw route/revision proposal when scheduled | no compile, schedule, DB/Git, direct handoff, tool, model or phase decision |
| Shared control | compile route/event/resource/phase outputs; admit/schedule/fence calls; enforce budgets, triggers and seals | cannot invent semantic route meaning or persist artifact/event bytes |
| Artifact/event | canonical schemas, immutable proposal/event/delivery/outbox/checkpoint/phase/seal persistence and publication | cannot choose routes, calls, phases, triggers or models |
| Layer0/workers | typed proposal/result for one exact control envelope | cannot widen target/capability/event/root/model authority |
| Human operator | gates and manual VS Code model/extension selection receipts | cannot turn UI text into S route or approval |

Future semantic schema identities remain `pipeline-v2.s-route-profile` v1, `pipeline-v2.s-route-proposal` v2, `pipeline-v2.s-revision-owner-proposal` v1 and `pipeline-v2.s-route-freeze-policy` v1. D03 adds fields to the source profile only: allowed phase class, phase-admission requirement, call class, predecessor-seal requirement and post-F15 prohibition. No schema file or migration is created here.

S inputs feed control-owned `compiled_s_route_table_v2`, `compiled_event_reachability_graph`, `compiled_fanout_barrier_profile`, and `compiled_resource_forecast`; S consumes but does not author `compiled_checkpoint_phase_partition_v1` and `compiled_checkpoint_publication_budget_v2`. Outputs bind exact source/schema/compiler/scope/policy hashes, ordered predicates, targets, capabilities/events/roots, F04 membership/barrier, F05 owner rule, phase/fence requirements and one digest. Unknown, open, stale, cyclic, incomplete, overlapping or inconsistent output blocks; runtime cannot patch compiled bytes.

## 3. Semantic state machine, invariants, terminal states, and phase fence

The semantic FSM remains `route_requested -> compiled_nominal|dispatcher_required|blocked_input`; `compiled_nominal -> scheduled|route_frozen`; `dispatcher_required -> proposal_received -> validated_route|failed_validation|blocked_semantic`; `validated_route -> scheduled|route_frozen`; `revision_requested -> owner_resolved -> replay_scope_requested|blocked_revision`; `route_frozen -> resume_eligible|aborted|blocked_reconciliation`.

These are dispositions, not durable run or phase states. Control validates the freeze and D03 phase guard before `scheduled`; artifact/event persists the resulting record. `failed_validation`, `blocked_input`, `blocked_semantic`, `blocked_revision`, `aborted` and `blocked_reconciliation` schedule no actor. S0 cannot advance run/phase state or mint terminal events.

One command/event identity binds one compiled profile. An accepted proposal names one exact route/target and cannot widen authority. Phase admission requires exact `project_chain_id`, `checkpoint_phase_id`, `partition_digest`, call class and predecessor seal from control. A stale/missing/multiple phase, non-F15 call after operational seal, F15 call before seal, post-F15 S invocation, fifth boundary trigger or separate K0b-05 run maps to `route_frozen` or a typed block before dispatch.

## 4. Input events, guards, routing, fan-out, barriers, F15, and fast paths

S consumes bounded views of `command.received`, compiled-profile and phase-admission status, validated outcomes, `revision.requested`, abort/reconciliation status and F04 barrier status. Inputs are IDs, enums, hashes, versions, deterministic guard results and bounded non-secret intent fields—not DB/checkpoint/projection bytes or arbitrary repository content.

| Route ID | Exact guard and semantic disposition |
|---|---|
| `s.alpha0.compiled_nominal.v1` | one machine-known outcome, all compiled/freeze/phase guards true; control schedules with no S0/Layer0 dispatcher call |
| `s.alpha0.layer0_fallback.v1` | registered ambiguous/non-nominal case plus admitted executor/phase; control schedules exact Layer0 envelope and validates result |
| `s.alpha0.f04.parallel_review.v1` | exact compatible reviewer snapshot; two external members under `all_required` |
| `s.alpha0.f05.revision.v1` | accepted existing version/consumer; resolve `fixture.alpha0.upstream_zero`; producer invocation remains lineage only |
| `s.alpha0.blocked.v1` | missing, stale, conflicting, forbidden, incompatible or phase-fenced input; no invocation/effect |

F04 members remain exactly `fixture.alpha0.primary_reviewer` and `fixture.alpha0.adversarial_reviewer`, external to S and mutually hidden before barrier. One deduplicated valid terminal result from each satisfies `all_required`; quorum, first-success, substitution and dynamic membership are forbidden.

For F05, `revision_owner_zero_role_id` and `producer_invocation_id` are distinct. Control validates producer lineage and the exact compiled mapping, schedules only the zero role, and computes the minimal invalidated descendant subgraph. S never selects a worker/replay point or mutates lineage.

F00 remains the immutable historical exception: its one-route profile made one required real S0 call and admitted only raw `s0_route_proposal` before deterministic validation. K0b compiled nominal does not reinterpret F00. All K0b non-F15 physical calls, including any registered Layer0 fallback, occur in pre-F15 K0b-04 and are terminal before the operational seal.

F15 remains 12 pinned nominal/ambiguous/non-nominal cases times three attempts: exact 36/36, at least 34 oracle-matching initial choices, at least two correct attempts per case and zero forbidden transition/capability/event. It begins only after the verified operational seal. Post-F15 K0b-04 and K0b-05 are deterministic with zero S0/Layer0/model calls in the same run segment. The four control-owned IDs are exactly `k0b.f15.boundary.entry_gate`, `k0b.f15.boundary.program_owner_wait_or_exit`, `k0b.f15.boundary.exit_gate` and `k0b.f15.boundary.top_level_run_end`; they cannot route to S. Pure compiled nominal classification and exact duplicate lookup are the only fast paths.

## 5. Output events, subscribers, terminal policy, and cross-plane handoffs

S0 emits no public event; it returns one raw proposal under the exact scheduled contract. Control validates and schedules, artifact/event persists. S semantically authors only profile ID/version/hash, route class/ID, applicability, exact target/reviewer/barrier refs, revision-owner proposal and freeze-policy ref.

The event catalog remains exactly the 21 types in passing v1.1 and artifact/event v2.2. S cannot add a type, subscriber, delivery, retry, error or terminal family. Schema/tool/security errors terminate at `block_run_and_enqueue_human`; incidents terminate at `persist_incident_and_enqueue_W5`. S receives bounded terminal status and never routes onward from it.

Correlation, idempotency, state revision, phase binding, trigger, model receipt, event/delivery/outbox/checkpoint/seal records and acknowledgements belong to the shared planes. No direct actor-to-actor handoff exists.

## 6. Artifacts, ownership, versioning, lineage, projections, checkpoints, and migrations

S owns no content artifact, event row, binary, projection, outbox, checkpoint, phase/seal row or Git path. Semantic profiles are versioned registry inputs only after later authority; proposals are evidence persisted elsewhere. Stable IDs plus version/hash bind lineage; hash is verification, not identity.

Lineage is `semantic profile -> compiled profile -> phase-admitted route request -> raw proposal when required -> validated decision -> invocation/delivery graph`. Revision adds `consumer request -> invalidated version -> producer evidence -> revision_owner_zero_role_id -> minimal replay graph`. Phase/checkpoint/seal lineage is consumed only as a guard and never rewritten by S.

Canonical artifact/event schemas, forward migrations, projection outbox, publisher, replay materializer and crash reconciliation belong exclusively to artifact/event. S has no migration. Changed bindings require a new compatible profile/compiler result and owning-plane forward migration; historical records stay immutable.

## 7. Context/query allowlists, trust, provenance, and prompt injection

The S0 allowlist is bounded intent; event/run/invocation IDs; semantic and compiled profile IDs/hashes; candidate route enums; machine guard and phase-admission facts; target contract/version/hash; capability summary; bounded prior disposition; and revision/abort/reconciliation status.

Command/artifact text, model output, error text, receipt labels and external metadata are untrusted. They cannot form registry names, paths, SQL, tool arguments, model/provider selection, capabilities, subscribers, phase/trigger identities or approval. The harness renders a typed envelope and exact echo/enum/schema validation.

Provenance binds source event/causation, producer, schema/profile/compiler/partition/executor/extension/manual-model-receipt versions and hashes and trust class. S receives receipt validity only, not authority to alter it. Missing/conflicting provenance blocks before a physical invocation.

## 8. Current roster, inputs, outputs, capabilities, and stops

| Actor/interface | Count | Input / output | Capability and stop |
|---|---:|---|---|
| S0 semantic dispatcher | 1 | exact typed envelope / one raw route or owner proposal | no tools/DB/Git/network/subagents; stop after one proposal |
| S workers | 0 | N/A | absent; adding one requires a new gate |
| fixture Layer0 fallback | external, one per admitted case | exact envelope / typed proposal | not S roster; no widening; phase/model receipt required by control |
| F04 fixture reviewers | external 2 | immutable snapshot / independent results | no peer visibility; one result each |
| shared planes | deterministic external | profiles/proposals/fence / compiled and persisted evidence | ownership fixed by reviewed sibling plans |

S0 has no loop, memory, dialogue, retry, alternate-model selection or dynamic roster discovery. It stops on proposal, validation failure, ambiguity without fallback, incompatible binding, budget/security/phase block, freeze, abort or terminal run state.

## 9. Failure, revision, replay, recovery, crash, abort, and duplicates

| Failure | Semantic outcome |
|---|---|
| missing/stale/uncompiled profile or phase admission | `blocked_input`; no call/schedule |
| ambiguity without exact fallback/executor receipt path | `blocked_semantic`; no guess |
| malformed/extra/wrong-target/widening proposal | `failed_validation`; no retry under same identity |
| F04 missing/incompatible member | barrier remains unsatisfied |
| F04 identical member result redelivery | original logical terminal result; no second count |
| F04 conflicting identity/bytes/causation | block plus incident evidence |
| F05 invalid producer/zero-role mapping | `blocked_revision`; schedule neither producer nor broad replay |
| phase chronology/call/trigger violation | freeze/block before physical call or publication |
| abort/reconciliation pending or late proposal | monotonic route freeze; evidence preserved, no revival |
| profile/schema/compiler/partition/executor incompatibility | block resume pending approved compatibility path |

Control assigns attempt/idempotency and fences results; artifact/event durably enforces uniqueness and returns original results. S consumes only deduplicated logical dispositions and implements neither storage nor retry. Identical replay cannot add an F04 count; conflicting replay never succeeds.

Revision replay stays minimal and immutable: S names only the exact zero owner; control computes descendants and replay points; artifact/event materializes inputs/edges. Forensic recorded-response replay and stochastic re-execution remain distinct. Abort is not rollback: S freezes new routes, terminal aborted remains frozen, and resume requires a nonterminal control-owned `resume_eligible` with the same pins.

Crash acceptance requires committed before/after proposal boundaries to produce at most one scheduled route, no lost accepted proposal, exact duplicate behavior and no routing while fenced. S infers nothing from file absence or external/UI text.

## 10. HITL, autonomy, approvals, compatibility, and dialogue

S0 performs one bounded autonomous classification only when control schedules it. It cannot ask the user, negotiate scope, choose a model, retry, self-approve or accept UI prose as approval. Human/W5 receives typed blocker/incident evidence through shared terminal policy.

Resume requires exact Pipeline, semantic/compiler/partition/schema/executor/fixture/event-profile pins. Compatible change requires reviewed declaration plus owning-plane migration/restore evidence; unknown, stale or lossy binding blocks. D01/D02/D03/D04/B01 choices are recorded owner authority, but final K0b-00 approval and per-dispatch manual receipts remain external. There is no dialogue protocol.

## 11. Tools, side effects, security, egress, and repository boundaries

S0/S have no shell, filesystem, DB, Git, network, provider/model/extension selection, credentials, plugins, processes, worktrees, checkpoints or projections. Any later physical model call crosses only the control-owned fixed-hybrid `manual_VSCode_UI` boundary with exact operator-selected model/extension receipts persisted by artifact/event.

Content cannot choose paths, commands, routes, event types, reviewers, capabilities, phase/trigger or models. Unknown fields and injection attempts are rejected. Runtime, if separately approved, uses only a new fixture clone; Pipeline and canonical fixture are read-only; task worktrees exclude runtime/history, Q excludes `.pipeline`; `projects/swarm`, `research/old-swarm`, real-product effects, push/merge/deploy/release and arbitrary egress are forbidden.

## 12. Context scale, invocation, call, and human budgets

S context is one bounded route envelope. Repository scans, RAG, sharding, caching, peer transcripts, alternate-model fallback and unbounded history are N/A; overflow blocks without truncating authority fields.

This S author/review is design ordinals 27/28 under effective cap 30. Ordinals 29/30 are one conditional author/fresh-review pair only if ordinal 28 returns a typed non-approve; otherwise they expire at package disposition. No design call becomes runtime credit.

Runtime allocation remains 16 nominal/30 worst non-F15 calls, all before operational seal, plus the separate exact 36-call F15 measurement. S owns no additive package and cannot allocate a call. Post-F15 calls are zero. Human attention, checkpoint batches and binary bytes cannot be converted into model-call credit.

## 13. Binary payload budget or proved N/A

`N/A` is mandatory for S: future semantic contracts admit only IDs, enums, booleans, bounded numbers, hashes, versions and bounded canonical UTF-8 JSON/text. BLOB/base64/opaque bytes, media/archive/checkpoint/projection bodies, raw provider/tool streams and filesystem handles are rejected.

S-attributable binary objects and bytes are zero nominal and worst. Checkpoint/measurement bytes are first persisted only by artifact/event under its reviewed phase budgets. Any S binary field or persistence API invalidates N/A and blocks implementation pending a full budget and reconciliation.

## 14. Downstream consumers and proof of actual consumption

Control consumes S profiles by compiling exact routes/reachability/fan-out/resource output and consumes raw proposals only through deterministic validation and the matching scheduled target. Artifact/event consumes accepted records only through control requests; Layer0/reviewers/workers consume only exact control-created envelopes.

Consumption evidence names producer/consumer IDs, contract/profile/compiler/partition versions/hashes, fields read, decision/delivery, phase admission and disposition. Stored profiles, files or model self-report are insufficient. F04 requires two deduplicated member results and one `all_required` evaluation. F05 requires separate zero-role and producer fields plus minimal graph. Freeze evidence proves no new delivery until reconciled unfreeze.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: one S0, zero S workers, 18 sections, exact boundaries and budgets, no implementation files.
- Contract: closed schemas/routes/events/phase-guard fields; unknown field/route/reviewer/barrier/capability/phase fails; retained F00 valid.
- Behavioral: compiled nominal scheduled/frozen, exact fallback, F04 independent deduplicated `all_required`, F05 zero owner/producer split and minimal replay, abort/freeze/late/duplicate fencing.
- D03: all non-F15 calls before seal; exact 36 F15 after seal; zero post-F15 S/model calls; four control triggers never route to S; fifth/separate run blocks.
- Fixture: S-owned F01-F05/F07/F09/F10/F13a/F15 cases on a new clone with manual receipt validity guards and exact oracle thresholds.
- Security negative: forbidden roots, canonical mutation, direct handoff, injection, dynamic roster, public S event, binary payload, hidden call, stale compatibility and inferred owner/model all fail closed.
- Real project: N/A and forbidden.

## 16. Evidence, observability, acceptance, and readiness

Evidence binds entry commit/tree; scope/policy/forecast/reconciliation/addendum; baseline/predecessor/review and both sibling v2/reviews; author/reviewer ledger entries; semantic profiles/compiler outputs; schemas/executor/fixture/event profile; proposals/routes/guards/phase admission; F04 snapshot/results/barrier; F05 lineage/replay; freeze/abort/reconciliation; compatibility; F15 oracle/attempts; manual receipt validity; commands/results/usage and findings.

Observability records route/reason, guard/phase disposition, compiled digest, validator result, scheduled target, reviewer/barrier state, revision owner/replay digest, freeze cause, duplicate/late fence, exact physical-call provider/model/parameters/token usage receipts when later present, and terminal blocker. It records no secret, raw binary, unrestricted prompt or fabricated KPI.

Architecture acceptance requires independent review of this exact hash at ordinal 28, ledger resolution, all 18 categories, passing sibling hashes, closed D03 cross-plan findings, exact route/event/roster/compiler ownership, budgets, binary N/A, security and final owner approval. Operational acceptance later requires assigned fixture cases, clean-clone F13a, exact F15 thresholds/call authority, zero forbidden effects, exact F04 barrier, F05 minimal replay, freeze/crash/duplicate proofs, both phase seals and no product claim. This candidate grants none.

## 17. Migration and supersession from K0a/K0b v1

K0a F00 evidence and its one S0 call remain immutable. Passing K0b S v1.1 remains historical authority for every unchanged semantic contract. D03 adds only source-profile phase guard fields and call chronology; it does not relabel prior routes or create a migration.

Future schema change is forward-only under K0b-01 after approval. Compatibility must read retained records, compile new profiles deterministically, reject mixed/stale bindings and preserve evidence through owning-plane backup/restore. Old-pipeline/research content is not read or imported; implicit handoff, free-form output, actor-selected tools/routes/models and file presence as state stay retired.

## 18. Risks, owner decisions, deferred capabilities, and non-authorizations

| Item | Disposition / mitigation |
|---|---|
| D01 | fixed-hybrid manual VS Code binding approved; exact operator-selected model/extension receipt still required per physical dispatch |
| D02 | three separate planes approved in scope; exact reviewed hashes still need final owner approval |
| D03 | real two-phase policy/scope and control/artifact successors reviewed; S review and final approval remain |
| D04 | exact separate 36-call F15 package approved; no operational credit |
| B01 | seed candidate accepted/reconciled; S binary remains zero |
| Compiled nominal could bypass historical F00 call | profile-level F00 exclusion and regression evidence |
| F04 actor/count confusion | external exact roles, zero S workers, immutable snapshot and duplicate rules |
| Phase fence could become S policy | S consumes only control-signed admission; cannot author membership/trigger/seal |
| Manual UI could imply model authority | S sees receipt validity only; operator selection cannot change semantic route |
| Final return margin | 29/30 usable only for a typed ordinal-28 finding; otherwise expires |

Remaining blockers are S fresh review, ledger/hash reconciliation, exact final K0b-00 owner approval and future per-dispatch receipts/runtime gates. Deferred capabilities are general multilayer routing, dynamic roster/subscribers, quorum/first-success, dialogue, distributed leases/scheduling, retries/dead letters/budget escalation, cache/RAG, N1+, product aliases, research, real projects, automatic self-change and release. No runtime code, contract, registry, migration, prompt, fixture change, projection, checkpoint, physical call or approval is created here.
