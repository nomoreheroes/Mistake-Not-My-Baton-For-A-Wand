# K0b-00 Shared Control Plane D03 Successor Delta Plan

| Field | Value |
|---|---|
| Plan ID | `k0b-00-shared-control-plane-delta-v2` |
| Version | `2.0.0` |
| Status | `review_candidate`; no implementation or runtime authority |
| Work item / parent phase | `K0b-00` / `K0b` (`2.0b`) |
| Architecture owner | `W1 Kernel / shared control plane` |
| K0a baseline | `k0a-00-shared-control-plane` v`1.2.0`, SHA-256 `8ba07c56d850b85c2dac8c24a5fa8f18e3a677a45c90b496b86e057921f4a93f` |
| Passing predecessor | K0b control v`1.2.0`, SHA-256 `8048df9a4b7726f1ad021ef569e02cd938e3fff47883664652185cade3c651af`; review SHA-256 `f9725905ee763dff666511d3197d7c0ca341c9274ed57ed803852146e46a8635` |
| Revision authority | `new pipeline/decisions/k0b-00-d03-policy-scope-plan-revision-owner-disposition-v1.yaml`, SHA-256 `0725cc34cf660ab821fc2cb08fd748df7a17e63c51c6d14844cc2c56671af6f7` |
| Author input | `new pipeline/evidence/k0b-00-shared-control-d03-v2-author-input.yaml`, SHA-256 `fa7965ed72984b39cce118bd1cc283be7970122c78386787720b1cfe340de595` |
| Complexity tier | `shared_plane`; at most 800 non-empty full-file lines; routing `<=95`, roster `<=55`, failure/recovery `<=95` |

## Bound scope and D03 authority

This is a forward successor, not an edit of the passing v1.2 plan. All v1.2 contracts remain binding unless this document explicitly changes them for D03. Exact cross-cutting authorities are scope v2 SHA-256 `e839396d9199fa85e5474b3a45a852e7b6b59d81d6910ae67897f7dffe627cde`, K0b policy overlay SHA-256 `ed224c7473810be838c2c22129d567c337bd16fd13532efb893074e684367ce8`, forecast v3 SHA-256 `ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a`, reconciliation v3 SHA-256 `d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb`, and partition addendum v2 SHA-256 `838fbec03184c587286dd37bc757a0fe7717d68c70454aef34650f51ba7db46c`.

The overlay adopts the base checkpoint thresholds and semantics for K0b only and defines exactly two real budget phases within parent K0b: `K0b-runtime-operational` followed by `K0b-F15-exact-measurement`. They are chronological, contiguous, non-overlapping, exhaustive, immutable before activation, and share one fixture project chain. This does not split the product program phase, reset cumulative chain accounting, create arbitrary batches, increase a threshold, or grant storage/runtime authority.

The fixed-hybrid executor profile is bound by SHA-256 `125a1e30e4ca69ab812280a40ff57302a5211cd1b888b23a3e6d9a8620c3898d`, passing review `3d1de40087201a4bc32c41e962e8f4b5392ada11466dc53d413b5988d11c85b8`, and accepted manual-UI risk `7c5c2504656f96387afb20232c184121f83364e8a369419cdf3a25566850c0e3`. Transport is `manual_VSCode_UI`; the operator selects the model manually for each physical dispatch and supplies the required receipt. No static model ID is inferred by architecture.

Only architecture, evidence, review, decision, and ledger records may be produced now. Runtime code, schemas, contracts, migrations, prompts, executor adapters, model calls, fixture mutations, checkpoints, and projections remain forbidden pending all three v2 reviews and exact owner approval.

## 1. Purpose, responsibility, non-goals, and applicability

The shared control plane deterministically compiles and enforces run, route, invocation, phase, checkpoint-admission, recovery, abort, and compatibility state. This successor makes the D03 budget partition executable as architecture without weakening K0a or the passing K0b v1.2 plan.

It applies only to the isolated committed fixture route `K0b-01..05` and scenarios `F01-F05`, `F07`, `F09`, `F10`, `F13a`, and `F15`. It does not authorize a real-project run, `projects/swarm`, legacy research, N1, full M, distributed scheduling, general retries/dead letters, external checkpoint storage, destructive restore, release, or production claims.

## 2. Dispatcher, compiler, artifact/event, S, Layer0, and operator boundaries

| Owner | Exclusive responsibility | Forbidden crossing |
|---|---|---|
| Shared control | compile exact registries, route graph, call allocation and budget phases; schedule/fence calls; enforce FSMs, guards, counters, barriers, seals, recovery and abort | no semantic route invention, event/artifact persistence, projection rendering, SQLite snapshot or Git publication |
| Shared artifact/event plane | canonical persistence, transactional outbox, checkpoint snapshots, projections, publication, readback and reconciliation evidence | no invocation scheduling, semantic decisions, threshold changes, or phase reclassification |
| S | semantic route classes, fallback/block/revision meaning and applicability | no control transition, persistence, effect, phase membership, trigger or call-budget decision |
| Layer0/workers | typed result for one exact envelope | no route, subscriber, tool, checkpoint, model, or successor selection |
| Human operator | explicit gates and manual VS Code dispatch/model selection receipts | no policy/schema mutation, forged receipt, retroactive reclassification, or threshold override |

No reasoning actor calls another directly. Every physical invocation crosses the pinned harness boundary after a committed before-call replay point and returns a receipt/result for validation before state transition. Fixed hybrid means deterministic compilation on the nominal path and a pinned real-LLM Layer0 envelope only for registered non-nominal cases; `manual_VSCode_UI` is transport, not an API or semantic decision maker.

## 3. State machines, invariants, terminal states, and phase chronology

The exhaustive run states remain `created`, `running`, `waiting`, `completing`, `reconciliation_required`, `reconciling`, `aborting`, `completed`, `aborted`, `blocked`, and `blocked_over_limit`. Valid edges are those in passing v1.2: `created -> running`; `running -> waiting|completing|reconciliation_required|aborting|blocked|blocked_over_limit`; `waiting -> running|reconciliation_required|aborting|blocked|blocked_over_limit`; `completing -> completed|reconciliation_required|blocked|blocked_over_limit`; `aborting -> aborted|reconciliation_required|blocked|blocked_over_limit`; `reconciliation_required -> reconciling|blocked`; `reconciling` returns only to the fenced prior semantic branch or a terminal block. `completed|aborted|blocked|blocked_over_limit` are terminal.

The budget-phase FSM is closed: `planned -> active -> sealing -> sealed`, with any nonterminal able to enter terminal `blocked|aborted`. Exactly one phase is `active|sealing`. A successor cannot activate until the predecessor seal, projection pair, outbox range, Project-Git identity, counters, measured bytes, and authority hashes reconcile.

Chronology is mandatory: all K0b-01/02/03 work and all 16 nominal/30 worst-case non-F15 physical-call capacity occur in pre-F15 K0b-04 under `K0b-runtime-operational`; all such calls are terminal and reconciled before its seal and the first F15 submit. `K0b-F15-exact-measurement` then contains exactly 36 F15 calls plus deterministic post-F15 K0b-04 closure and K0b-05 forecast/owner disposition, in the same top-level run segment, with zero post-F15 model calls. Any reordered, unclassified, overlapping, repeated, or extra-call path blocks and requires a new forecast.

## 4. Inputs, guards, routing, fan-out, barriers, triggers, and fast paths

Inputs are authenticated closed CLI requests or persisted resume/abort/replay requests; exact Pipeline/fixture commit and tree, root/worktree, scope/policy/forecast/plan/compiler/executor pins; run/work-item/scenario/attempt/call identities; expected revisions; capability and context allowlists; phase, checkpoint, trigger, outbox and predecessor-seal facts. Unknown or stale input fails closed before effect.

The compiler assigns deterministic exact nominal cases directly, registered ambiguous/non-nominal cases to the pinned Layer0 fallback, F04 to its immutable bounded reviewer fan-out and compiled barrier, and accepted revisions to only invalidated descendants. Missing nodes, dangling terminal policies, route ambiguity outside the registered fallback, direct handoff, or capability widening blocks.

The only F15 boundary trigger identities are exactly one each of `k0b.f15.boundary.entry_gate`, `k0b.f15.boundary.program_owner_wait_or_exit`, `k0b.f15.boundary.exit_gate`, and `k0b.f15.boundary.top_level_run_end`. A fifth trigger, a duplicate with conflicting payload, or a separate K0b-05 run blocks before publication. Publication batches contain at most 12 windows and never reset phase totals. Identical idempotent duplicates return the original disposition.

F15 remains the pinned `HYP-DISPATCH-01` matrix: 12 cases by three attempts, exactly 36/36, at least 34 oracle-matching initial choices, at least two correct attempts per case, and zero forbidden transition/capability/event. Labels and thresholds freeze before dispatch.

## 5. Output events, subscribers, terminal policies, and cross-plane requests

Control semantically produces typed requests for run lifecycle, approvals/gates, revision, invocation, delivery, replay, phase transition/seal, projection and checkpoint publication. Artifact/event alone persists and delivers them. K0b error events remain `error.schema_mismatch`, `error.tool_failure`, `error.security_policy`, and `meta.incident_detected`; the first three terminate at `block_run_and_enqueue_human`, and incident terminates at `persist_incident_and_enqueue_W5`.

Each request carries run and expected revision, project chain, phase and partition digest where applicable, causation/correlation, idempotency identity, schema/registry/compiler/executor pins, semantic producer, terminal policy, allowed result enum and before-call replay point. Control consumes only committed IDs and verified results.

`checkpoint_phase_seal_intent` and `checkpoint_publish_request` name a contiguous sequence/window, trigger, checkpoint, cumulative counters/bytes, dirty/untracked allowlist snapshot, projection DB sequence, and predecessor seal. No downstream success is inferred from a file or model statement.

## 6. Canonical schemas, compiler outputs, artifacts, ownership, versioning, lineage, and migration

No schema is created here. Future forward-only contracts must cover `compiled_checkpoint_phase_partition_v1`, `compiled_checkpoint_publication_budget_v2`, `checkpoint_phase_binding_v1`, `checkpoint_phase_transition_v1`, `checkpoint_phase_seal_intent_v1`, `checkpoint_phase_seal_result_v1`, and phase fields on publication intent/result. Version mismatch is explicit; silent coercion or down-migration is forbidden.

Compiler outputs bind all authority hashes, ordered intervals, exact work-item/call allocation, four-trigger allowlist, thresholds, publication limits, predecessor seal, projected counts/bytes, and a canonical partition digest. They are immutable for a run. Unknown, duplicate, overlapping, cyclic, incomplete, stale, or arithmetically inconsistent output blocks activation.

Binding uniqueness is `(project_chain_id, checkpoint_phase_id, partition_digest)`; publication uniqueness is `(project_chain_id, checkpoint_phase_id, trigger_id, checkpoint_id)`. Lineage is `compiled profile -> route/call -> transition/delivery -> replay range -> projection/checkpoint intent -> publication -> phase seal -> successor/gate`. The control plane stores only bounded control records and references, never artifact or checkpoint bytes.

## 7. Context/query allowlists, trust, provenance, and injection controls

Contexts use exact-ID queries and compiled allowlists. Agent-visible material is limited to the assigned bounded artifact/control fragments, result schema, permitted enums, provenance and capabilities. Full DB dumps, checkpoint bytes, Git history, arbitrary repository files, other raw transcripts, credentials, and hidden policy are excluded.

Fixture text, prior model output, projection text, replayed responses, tool output, and unguarded Git metadata are untrusted data. They cannot select roots, routes, events, tools, models, approvals, phases, triggers, checkpoints, or successors. Injection/secret/tool guards run before every physical call or effect. Forensic replay labels a recorded response; stochastic replay requires the exact envelope and a new identity.

## 8. Current roster, inputs, outputs, capabilities, and stops

| Deterministic component | Input / output | Capability | Stop |
|---|---|---|---|
| CLI/identity guard | closed request / validated identity | bounded roots and runtime paths | root, pin, symlink, argument mismatch |
| registry/resource compiler | exact authorities / compiled route, phase and forecast | read pinned Pipeline records | incomplete graph, stale hash, overlap or arithmetic error |
| run controller | request and revision / transitions and deliveries | short active-DB transactions | stale state, pending obligation, incompatible binding |
| phase-budget coordinator | compiled membership and counters / admission, seal or hard stop | request-only artifact/event interface | wrong chronology, extra call/trigger, limit crossing |
| reconciliation/abort controller | intents/results/observed state / reconciled or blocked outcome | bounded inspection/cancellation | unknown effect or unsafe cancellation |
| replay materializer coordinator | replay point and snapshot refs / materialization refs | isolated fixture paths only | incomplete tree, delta, envelope or environment |
| model-executor boundary | exact envelope and manual receipt / typed transcript result | approved VS Code UI channel only | missing model/extension/tool receipt or policy violation |

There are seven deterministic control components and zero control-plane LLM workers. S0, Layer0, workers and reviewers are interface actors owned elsewhere. Distributed leases, dynamic roster discovery, general retry/dead-letter service, cache/RAG, research importer, production adapters and full M remain deferred.

## 9. Failure taxonomy, invalidation, replay, reconciliation, crash consistency, abort, and duplicate suppression

| Failure | Required fail-closed outcome |
|---|---|
| root/worktree/symlink/tool/egress mismatch | pre-effect security error and human route |
| unknown route/event/subscriber/phase/trigger or incomplete compiler graph | no activation or dispatch |
| schema/proposal/manual-receipt mismatch | preserve evidence; no transition/effect |
| crash before DB commit | absent transaction; reconcile any sidecar/intent; repeat only idempotent preparation |
| commit before outbox/projection/checkpoint result | recover committed intent by identity; inspect external/result state; complete once or block |
| mandatory boundary has pending outbox/checkpoint | block next effect, successor and exit until exact terminal result |
| incompatible Pipeline/schema/executor/partition | read-only diagnosis; explicit forward migration/backup or blocked resume |
| uncertain external effect or cancellation | fence late result, preserve evidence and block; never fabricate success/abort |
| phase count/byte hard crossing or fifth F15 trigger | no next publication/effect; terminal permitted evidence only |

Every mutation uses expected revision and a stable idempotency key in the same transaction as its outbox row. Publisher checkpointing and projection results are reconciled by committed sequence and external Git/tree identity. Identical retries return the original outcome; conflicting reuse is evidence and blocks. Duplicate suppression never drops a semantically distinct attempt, trigger, phase or result.

Minimal replay creates new invocation/artifact/event identities for invalidated descendants and never rewrites history. Clean-target materialization verifies the recorded commit/tree plus dirty/untracked delta. Graceful abort persists request, freezes delivery, fences prepared work, cancels only declared cancellable effects, reconciles every begun intent/result, preserves worktree/DB and emits `run.aborted` only from a consistent graph. Abort is not rollback; terminal states and sealed phases never reopen.

## 10. HITL, autonomy, approvals, dialogue, and compatibility semantics

Automatic authority is limited to deterministic reads, compilation, validation, DB transitions, reconciliation and already run-authorized reversible fixture effects. Explicit human action is required for architecture/runtime approval, each manual UI dispatch/model receipt, destructive restore, migration, threshold/policy change, unresolved external effect, risk acceptance and program continuation.

Resume requires the same Pipeline/schema/registry/compiler/partition/executor pins and no unresolved obligation. A compatible additive schema version follows an approved forward migration with verified backup/readback; unknown, older, lossy or substituted versions block. `resume`, abort text, or a UI selection cannot approve scope, migrate state, change model policy, or reclassify a budget phase. Creative dialogue and M automation are N/A.

## 11. Tools, side effects, security, egress, and repository boundaries

Later runtime, if approved, uses a new independent committed fixture clone. Pipeline Git and the canonical fixture are read-only. Q task worktrees exclude `.pipeline/**`; only the fixture coordination worktree may materialize an allowlisted checkpoint. `projects/swarm` and `research/old-swarm` remain outside every capability.

Each Git/tool action verifies canonical root, repository role, top-level, baseline, branch/worktree, symlink/junction ancestry, exact change set, executable identity, argv, cwd, environment allowlist, timeout, resources, egress and expected outputs. Checkpoint publication may commit only one reconciled DB sequence's allowlisted checkpoint and ready projections. Arbitrary provider/network, credential discovery, package hooks/plugins, direct SQL, content-derived shell, push/merge/deploy/release and shared-checkout reset are forbidden.

## 12. Context scale, invocation, publication, and human-attention budgets

Design authority is capped at 24 calls. This control v2 author is ordinal 19; its fresh independent review is ordinal 20. Artifact v2 author/review are 21/22 and S v2 author/review are 23/24. There is no return margin; any non-approve outcome pauses for new owner budget authority.

Operational allocation is unchanged: 16 nominal/30 worst-case non-F15 calls, all before the operational seal, plus separately approved exact F15 measurement of 36 calls. Post-F15 K0b-04 closure and K0b-05 are deterministic with zero model calls. No unused, duplicate, forensic, failed-transport or manual-UI attempt is silently credited; exact accounting follows the approved policy and receipts.

The forecast remains bounded fixture scale. Dynamic sharding, repository-wide inventory, cache/RAG and scale fallback are deferred. Every dispatch proves its effective context limit. Human attention follows the approved gate/decision packages and cannot be converted into model-call credit.

## 13. Binary/checkpoint payload budget and D03 arithmetic

The control-plane binary budget is `N/A`: zero binary objects and bytes. Its interfaces contain IDs, enums, integers, bounded canonical UTF-8, hashes and version refs only. Binary input/output, BLOB storage, archives, media or raw checkpoint bytes invalidate N/A and block implementation.

Artifact/event owns the exact D03 pack budget. Operational worst pack is `926,941,184` bytes (`9` checkpoints at `26 MiB`, `14` publications at `34 MiB`, plus fixed `132,120,576`); F15 worst pack is `954,204,160` bytes (`10` checkpoints at `35 MiB`, `12` publications at `26 MiB`, plus fixed `125,829,120`). Each is below the unchanged `1 GiB` hard limit. Combined cumulative observability is `1,881,145,344` bytes and remains visible to full-route clone/performance gates; it is not compared as one phase pack after the explicit K0b overlay.

Forecast arithmetic, count cardinalities and byte units must be compiled and read back. A measured or forecast phase hard crossing blocks before the next effect. The `29` F15 publication hard-count boundary is not credit for a fifth trigger or an unplanned publication.

## 14. Downstream consumers and actual consumption

Artifact/event consumes typed transition, outbox, projection, phase seal and checkpoint requests. S consumes compiled route/fallback/revision and phase-fence status. Layer0/workers consume exact envelopes. Publisher consumes committed outbox order. Replay/abort consume terminal and seal state. CLI/owner gates consume bounded verified readbacks.

Actual consumption requires a durable delivery/result/gate record with producer/consumer contract versions, identities, fields read and disposition. A compiler output counts only when it gates activation/delivery; publication only when matching outbox, projection pair, checkpoint, Git commit/tree and seal reconcile. Self-report, file existence and transcript prose are not consumption evidence.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: exhaustive run and phase enums/edges; closed event/route/subscriber graph; exactly two ordered phases; exact call/work-item membership; exactly four stable boundary triggers; no dangling terminal.
- Contract: compiler golden and negative vectors; uniqueness/idempotency/conflict behavior; schema/version/partition mismatch; validated run, phase, abort and seal edges; no binary crossing.
- Crash/recovery: fault injection before/after DB commit, outbox append, projection publication, checkpoint Git effect and phase seal; each completes once or blocks with immutable evidence.
- Routing: deterministic nominal, pinned non-nominal Layer0, F04 bounded fan-out/barrier, minimal revision replay, direct-handoff rejection and exact F15 oracle thresholds.
- D03: all non-F15 calls terminal before operational seal; F15 cannot start early; four triggers have cardinality one; fifth trigger and separate K0b-05 run fail; both phase worst packs compile below hard; cumulative bytes remain visible.
- Security/adversarial: F09 wrong root and F10 injection/secret/tool attempt stop before effect; missing manual model/extension receipt, late result and conflicting duplicate cannot mutate state.
- Fixture E2E: control-owned portions of F01-F05, F07, F09, F10, F13a and F15 on a new committed clone, including clean-clone replay and compatible forward migration/backup.
- Real project: N/A and forbidden before later gates.

## 16. Evidence, observability, acceptance, and readiness

Evidence binds Pipeline/fixture commits and trees; scope/policy/forecast/reconciliation/addendum and all three v2 plan/review/approval hashes; compiler output and partition digest; schema/registry/executor/extension and manually selected model receipts; run/work-item/scenario/attempt/call/phase/trigger/checkpoint/outbox/projection/seal identities; FSM transitions; route/barrier/revision graph; before/after replay; fault-injection and duplicate cases; security/root/tool/egress checks; byte/count arithmetic; Project-Git readback; commands, exits, timings and finding dispositions.

Metrics/logs are bounded, canonical and secret-scanned: active phase, admitted/terminal calls, publication/checkpoint counts and bytes, outbox lag, highest committed/published sequence, projection pair, seal latency, retries suppressed, conflicts, reconciliation/abort state, hard-stop reason and manual receipt completeness. IDs join traces without raw prompts, credentials or checkpoint payloads.

Architecture acceptance requires this exact hash to pass fresh independent review, ordinals 19/20 to reconcile, artifact and S v2 to pass at 21..24, cross-plan ownership/schema/event/hash consistency, all D03 r0 findings resolved, line budgets and validation green, and exact owner approval. Runtime acceptance later requires compiled/read-back authority, both seals, zero forbidden effects/transitions, exact 36 F15 calls and thresholds, clean-clone replay, crash/idempotency tests, reconciled projections/outbox/Git and storage below hard limits. This review candidate alone authorizes none of those actions.

## 17. Migration and supersession from K0a/K0b v1

K0a records remain immutable. Retained are deterministic harness ownership, immutable transitions, exact replay envelopes, root/pin guards, separation of semantic proposal from execution, and forward-only compatibility. Passing K0b control v1.2 remains historical authority for every unaffected contract.

For D03 only, scope v2 and the K0b overlay replace the ambiguous one-phase denominator with two real budget phases and exact chronology. Runtime adoption, if later approved, is forward-only: validate backup and compatibility; compile the partition; write binding before activation; seal operational; activate F15 from its predecessor; never relabel old evidence or reopen a seal. Rejected addendum v1 and forecast/reconciliation v2 remain immutable superseded evidence.

## 18. Risks, owner decisions, deferred capabilities, and non-authorizations

| Item | Current disposition / control |
|---|---|
| D01 executor ambiguity | resolved as separately pinned fixed-hybrid `manual_VSCode_UI`; model and extension evidence are manual per dispatch |
| D02 exact three-plan scope | approved; control, artifact/event and S remain separate authors/reviews |
| D03 denominator and trigger ambiguity | owner selected real phase partition; policy/scope and all three plans require successor reviews; no arbitrary batching |
| D04 F15 conflict | exact separate 36-call measurement package approved with updated forecast; no hidden operational credit |
| B01 candidate | accepted with forecast reconciliation; no runtime authority follows |
| No review return margin | any non-approve at ordinals 20/22/24 pauses for owner budget action |
| Manual UI receipt may be incomplete | accepted residual risk, but missing exact per-dispatch evidence blocks that dispatch |
| Phase split could hide cumulative growth | cumulative bytes and full-route clone/performance gates remain mandatory |
| Recovery could duplicate an effect | transactional intent/outbox, stable key, external readback and conflict block |
| Control could become publisher or semantic owner | request/reference-only interfaces and cross-plan contract tests enforce boundaries |

Remaining architecture blockers are the fresh control, artifact/event and S v2 reviews, ledger/hash reconciliation, and exact final K0b-00 owner approval. Deferred capabilities remain real projects, research import, N1, full M, distributed leases, general retry/dead-letter/budget escalation, cache/RAG, CAS/LFS/external storage, production effects and release. Nothing in this plan creates runtime code, migrations, contracts, prompts, physical calls, checkpoints, fixture changes, or final approval.
