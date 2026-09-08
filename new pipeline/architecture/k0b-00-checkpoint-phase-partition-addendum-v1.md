# K0b-00 checkpoint phase-partition addendum v1.0.0

Status: `review_candidate`; architecture-only D03 owner-route specialization; no runtime, migration, contract, fixture, checkpoint, or physical-call authority.

Author invocation: `k0b-00-author-d03-checkpoint-phase-partition-v1` using exact input manifest `new pipeline/evidence/k0b-00-d03-checkpoint-phase-partition-author-input-v1.yaml`, SHA-256 `a78dedb2f0216094f798819ac8114088c03582621492ebf99785a9249da1da83`.

Exact authority: scope envelope `fe63742498a8192c7f67c5d430eb8c466d3621d873e3486115102510e7ca779a`; checkpoint policy v1 `8e9696916c939c6d9fa337c7bddc8b022c7657a2c105c0e51773b4c6ba1a67f3`; D03 owner disposition `ddb37be73c667be61e893b5063c2f35aac27a5284cfa064d44dcab3826930732`; forecast v2 `8122405a989aca205633917d692202733be02378acb4f1d74d90ebac0071c89d`; reconciliation v2 `92fc9a0ebebe999590769ab2a60dda86731100e1f6fc0961167d01271c02c35f`.

Reviewed sibling authority remains byte-identical: shared control v1.2.0 `8048df9a4b7726f1ad021ef569e02cd938e3fff47883664652185cade3c651af`; shared artifact/event v1.1.0 `750d0bc8124faf59559bde60d320b6bc694dafe0755514312b57004172408240`; S v1.1.0 `c1e9eb94c639cb2e54e0d1b922b1e541557fc83370449578142a112f47381fd0`. Their final independent reviews remain `f9725905ee763dff666511d3197d7c0ca341c9274ed57ed803852146e46a8635`, `616506ba0535b88dd5039c4e819f3b2d4a7258db47ebd5227e66fb09d828eb0b`, and `605b7ccbe1f35da880c6cc6cfde79b8534a7c018d5970668c8ce6057276922b7` respectively.

## 1. Purpose, boundaries, non-goals, and applicability

This addendum materializes the registered `narrow_or_checkpoint_batching` route as an explicit non-overlapping checkpoint-phase partition inside K0b. It resolves the v1 single-phase planning worst of `2,055,208,960` bytes by assigning publications to `K0b-runtime-operational` or `K0b-F15-exact-measurement` before effect and applying the unchanged `1,073,741,824`-byte pack hard limit independently to each phase, as required by the policy's per-phase formula.

It is not a fourth layer plan, a new work item, a new product phase, a second project chain, a threshold increase, measured delta credit, storage migration, or permission to implement. The same fixture checkpoint chain remains cumulative and visible. If this specialization conflicts with an existing reviewed plan rather than filling its external D03 owner-route boundary, review must block and request explicit plan-revision authority.

## 2. Control, deterministic compiler, artifact/event, S, and operator ownership

Shared control owns phase-policy compilation, membership validation, the single-active-phase guard, budget counters, seal/abort requests, hard-stop decisions, and successor admission. The shared artifact/event plane alone persists bindings, intents, results, outbox rows, SQLite snapshots, projections, Project-Git commits, phase seals, and measured pack facts. S owns no checkpoint phase, publication, byte, or budget decision. The operator may approve only already-typed owner gates and may not reclassify a record or grant credit.

The future compiler emits immutable `compiled_checkpoint_phase_partition_v1` and `compiled_checkpoint_publication_budget_v2`. The first contains `project_chain_id`, two ordered `checkpoint_phase_id` values, exact package/record membership predicates, predecessor/seal rules, allowed trigger classes, policy/forecast/addendum hashes, and a partition digest. The second contains per-phase invocation, replay-point, minute, trigger, publication, batch, checkpoint-byte, pack-byte, warning, hard, and margin bounds. Unknown fields, overlapping predicates, missing members, a cycle, or a non-terminal predecessor fail compilation.

## 3. Phase state machine, invariants, and terminal states

Each phase uses the closed states `planned`, `active`, `sealing`, `sealed`, `blocked`, and `aborted`. Declared edges are `planned -> active`, `active -> sealing`, `sealing -> sealed`, `planned|active|sealing -> blocked`, and `planned|active|sealing -> aborted`. `sealed`, `blocked`, and `aborted` are terminal; every other edge is rejected.

Exactly one phase is active or sealing. `K0b-F15-exact-measurement` cannot enter `active` until the operational phase has a durable, reconciled `sealed` record and its terminal checkpoint/result hashes agree. A seal is immutable. Reopening, relabelling, deleting, or charging a later publication to a sealed phase is forbidden.

All 16/30 non-F15 physical model calls must complete in the operational phase before its seal. After F15 activation, K0b-04 measurement closure and K0b-05 disposition are deterministic and may add zero physical model calls. Any contrary need invalidates this forecast and blocks before the call.

## 4. Inputs, guards, membership routing, batching, and fast paths

Inputs are hash-bound scope, policy, owner disposition, v2 forecast/reconciliation, three reviewed plans, compiled K0b work graph, invocation package, scenario/attempt identity, replay-point counts, publisher minutes, trigger type, cumulative checkpoint bytes, and prior phase seal. Every invocation, trigger, checkpoint, publication, and evidence record maps to exactly one phase by compiled type and lineage, never by mutable labels or content supplied by a model.

Operational membership is every non-F15 physical model invocation and its evidence plus pre-F15 K0b-01 through K0b-04 activity. F15 membership is exactly 36 F15 attempts, their direct request/response/validation/measurement evidence, and deterministic post-F15 K0b-04/K0b-05 closure. Unclassified or multiple membership, a non-F15 model call after the seal, more than four F15 boundary triggers, or more than 29 F15 publications blocks.

Within a phase the publisher compiles batches of at most 12 publications. Batch boundaries limit a single published pack batch but never reset phase counters, create byte credit, or weaken the phase hard stop. A deterministic no-op duplicate returns its original result; there is no model-selected routing or fast path around validation.

## 5. Output records, subscribers, terminal policy, and cross-plane handoffs

Planned records are `checkpoint_phase_binding_v1`, `checkpoint_publication_budget_v2`, `checkpoint_phase_transition_v1`, `checkpoint_phase_seal_intent_v1`, `checkpoint_phase_seal_result_v1`, and phase fields added to the existing checkpoint publication request/result envelope. Every record carries the exact chain, phase, partition digest, policy, forecast, addendum, causation, idempotency, checkpoint, outbox, and prior-seal references applicable to it.

Control consumes artifact/event results and advances only the matching compiled state. Artifact/event consumes typed control requests and never derives membership. The checkpoint publisher consumes only committed outbox rows in per-chain sequence. Human/W5 receives only terminal blocker, hard-stop, security incident, or post-F15 disposition evidence.

## 6. Schemas, artifacts, versioning, lineage, phase seals, and migration boundary

All planned schemas are forward-versioned additions after K0b approval; no schema or migration is created here. `checkpoint_phase_binding_v1` has a unique `(project_chain_id, checkpoint_phase_id, partition_digest)`. Publication uniqueness is `(project_chain_id, checkpoint_phase_id, trigger_id, checkpoint_id)`. A phase seal names the terminal cumulative checkpoint, projection pair, Git commit/tree, highest publication sequence, measured counters, and predecessor seal.

Checkpoint contents remain cumulative across the fixture chain; phase attribution applies to publications and per-phase pack-growth accounting, not to deleting history. Hashes provide integrity and lineage, never logical identity. No BLOB, artifact version, event, outbox row, or Git object may be silently copied between phases to alter a budget.

## 7. Context/query allowlists, trust, provenance, and injection controls

The compiler and publisher may query only typed K0b control/artifact/event records for the exact fixture chain, current work graph, two phase IDs, declared packages, policy, forecast, prior seal, and outbox sequence. Model output, transcript text, artifact body, path text, or external metadata is untrusted and cannot select a phase, trigger, counter, threshold, or repository destination.

Every derived count retains producer, schema/version, causation, and complete-file authority hashes. Missing provenance, stale policy/addendum/forecast, prompt-injected phase labels, or data-dependent query widening blocks without fallback.

## 8. Current roster, inputs, outputs, capabilities, and stop conditions

No new actor is added. Shared control compiles/guards, artifact/event persists/publishes, the harness validates, and the existing operator owns explicit gates. The F15 actor roster and fixed-hybrid manual VS Code executor profile are unchanged. This addendum grants no actor tool, shell, filesystem, database, Git, network, model, or storage capability.

Stops include missing seal, stale digest, wrong chain/worktree, dirty unrelated state, publication gap, duplicate conflict, phase overlap, unclassified trigger, count/byte overrun, post-seal non-F15 model call, fifth F15 boundary trigger, thirtieth F15 publication, checkpoint at least 100 MiB, phase pack at least 1 GiB, or any need for unmeasured credit.

## 9. Failure, replay, reconciliation, crash recovery, abort, and duplicates

Same-phase replay retains its original phase and creates no new logical publication for an identical trigger/checkpoint result. Conflicting identity reuse blocks with incident evidence. Cross-phase replay may read immutable predecessor artifacts, but its new request/result is charged to the active phase. A replay that would mutate a sealed phase, exceed an active bound, or require a new non-F15 call after F15 starts freezes the successor and requires a new forecast/owner route.

Seal and publication use durable intent/result records. Crash before effect reconciles the same intent; crash after unknown filesystem/Git effect inspects exact hashes and sequence before retry; blind retry is forbidden. Crash between operational seal and F15 activation leaves no active phase and resumes only from the same seal/digests. Late results for a sealed, aborted, blocked, stale, or wrong phase are preserved as rejected evidence and advance nothing.

Abort before publication fences the intent. Abort after an uncertain effect reconciles and may use the policy's one terminal checkpoint for the current unpublished range, but cannot admit F15 or claim a passing phase. Aborting or blocking the operational phase prevents F15 activation; aborting or blocking F15 prevents K0b-05 completion.

## 10. HITL, autonomy, approvals, and compatibility

No dialogue or autonomous budget escalation is introduced. The one F15 human wait/exit trigger represents the already-required post-measurement owner disposition; two asserted gate triggers bind entry and exit. More owner waits or gates exceed the compiled four-boundary budget unless a new forecast passes before effect.

Compatibility is exact on Pipeline/fixture commit and tree, scope, three plans/reviews, policy, owner disposition, author input, forecast, reconciliation, addendum, compiler, schemas, executor profile, phase partition, trigger allocation, and predecessor seal. Any change makes the binding stale and requires deterministic compatibility/reforecast evidence; silent reuse is forbidden.

## 11. Tools, side effects, security, egress, and repository boundaries

Future writes remain harness-only in the coordination worktree of a new committed fixture clone. The canonical fixture stays immutable; task worktrees exclude history/runtime/backups; `projects/swarm` and `research/old-swarm` remain prohibited. Symlink/junction escape, wrong root, content-derived path, broad ignore, secret/PII, SQLite attach/extension, forged seal/approval, or direct provider API fails before effect.

Only artifact/event may write SQLite, projection, snapshot, outbox, or Project Git. Phase partitioning creates no second publisher and no egress. Security failures freeze both successor admission and publication while preserving bounded evidence without secrets.

## 12. Invocation, publication, storage, and human-attention budgets

Design authority is the owner-extended K0b cap of 24 calls; 16 precede this author, this author is 17, and one fresh review is 18, leaving 6. Design calls are not checkpointed. Physical budgets remain operational `16/30` and F15 exact `36/36`, non-overlapping; the effective K0b invocation worst is 90 only because the design cap is 24, while checkpointed physical worst remains 66.

Operational uses 14/34 publications in 2/3 batches. F15 uses 8/22 mandatory windows plus exactly four conservative boundary triggers, totaling 12/26 publications in 1/3 batches. No overlap, compression, delta, deduplication, cross-phase, retry, or hidden call credit is used. Human attention and model selection remain governed by existing decisions.

## 13. Binary/checkpoint budget and exact D03 reconciliation

| Checkpoint phase | Checkpoint bytes nominal/worst | Publications nominal/worst | No-delta pack nominal/worst | Worst hard margin |
|---|---:|---:|---:|---:|
| `K0b-runtime-operational` | `9,437,184 / 27,262,976` | `14 / 34` | `132,120,576 / 926,941,184` | `146,800,640` |
| `K0b-F15-exact-measurement` | `10,485,760 / 36,700,160` | `12 / 26` | `125,829,120 / 954,204,160` | `119,537,664` |

Both checkpoints are below `104,857,600`; both phase packs are strictly below `1,073,741,824`. Largest worst batches are `327,155,712` and `440,401,920`, both below the `536,870,912` warning threshold. The observable chain sum is `257,949,696 / 1,881,145,344`; it remains recorded for clone/scale evidence but is not silently substituted for the policy's per-phase denominator.

B01 seed counts `6/12` and bytes `2,236,416/4,472,832`, delta factor `1.0`, and cumulative checkpoints remain unchanged. F15 can tolerate no more than 29 worst publications at 36,700,160 bytes; the compiled cap of 26 leaves three, not reusable credit.

## 14. Downstream consumers and proof of actual consumption

The control scheduler consumes partition/budget compiler outputs to admit invocations and triggers. The artifact/event transaction layer consumes phase identity in uniqueness and outbox rows. The publisher consumes counters and seal order. Replay/abort controllers consume phase terminal state. The acceptance gate consumes exact arithmetic, measured checkpoint/pack facts, and clean-clone results. K0b-05 consumes only sealed F15 evidence and its typed owner disposition.

Evidence must show each consumer rejected wrong, stale, missing, overlapping, or over-budget phase data; mere schema existence is insufficient.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

Structural tests require two ordered phases, one chain, one publisher, closed states, unique ownership, and no dangling member. Contract tests cover schema/version/hash, membership exhaustiveness, one-phase uniqueness, trigger caps, state edges, predecessor seal, idempotency conflict, and exact arithmetic.

Behavioral tests cover operational seal before F15, 36 attempts only in F15, deterministic post-F15 closure, 12-publication batches, 26/29 boundary, checkpoint/pack hard edges, identical/conflicting duplicate, same/cross-phase replay, crash at every intent/effect/seal boundary, abort before/after effect, and late result fencing. Negative tests prove that one post-F15 non-F15 model call, a fifth boundary trigger, publication 30, overlapping membership, or credit claim blocks. Fixture execution waits for approval and occurs only in a new clone. Real-project testing is N/A and forbidden.

## 16. Evidence, observability, acceptance, and readiness

Observability records chain/phase/partition IDs, state transitions, member/trigger class, invocation/replay/publication/checkpoint/outbox/seal IDs, cumulative and per-phase bytes, window derivation, batch and phase counters, margins, duplicate/reconcile/abort disposition, policy/forecast/compiler/addendum hashes, publisher/clone timings, and actor identity. It never fabricates measured delta or records secrets/unbounded content.

Architecture acceptance requires exact authority hashes, forecast/reconciliation arithmetic, 18 scoped categories, full-file and sub-budget compliance, one author and fresh reviewer ledger entries, reviewer `approve` with zero blocking findings, byte-identical sibling plans, no silent scope reinterpretation, and no implementation file. D03 closes only for this exact addendum hash after review. Operational acceptance later requires compiled membership equivalence, measured counters within bounds, publication p95 below 10 seconds, clean-clone restore below 120 seconds, cumulative chain/object metrics, zero forbidden effects, and all crash/replay/abort negatives.

## 17. Migration and supersession from v1 forecast

Forecast v2 supersedes v1 only for D03 phase attribution, publication counts, pack arithmetic/status, derived pack totals, and the already-approved design cap. Reconciliation v2 preserves B01 and D04. No database migration occurs. Future implementation would add forward schemas beside prior evidence; historical v1 forecast and single-phase failed route remain immutable provenance.

The three reviewed deltas and scope envelope are unchanged because they deliberately leave D03 to an external owner route. If independent review finds that this addendum changes their semantic ownership or work-item boundary, it must recommend `revise` and no approval may rely on this compatibility claim.

## 18. Risks, remaining blockers, deferred capabilities, and non-authorizations

The partition could hide post-F15 work; therefore zero post-F15 non-F15 model calls and four boundary triggers are hard contracts. Phase boundaries could game repository growth; therefore cumulative chain bytes, object count, clone restore, and both per-phase packs remain observable. A final checkpoint may grow beyond forecast; any hard crossing stops before the next action under existing policy. The three-publication F15 margin is not call or trigger credit.

After a successful review, D03 arithmetic and architecture route may close. Exact manual model-selection receipts remain required before their physical slots dispatch, and an exact hash-bound K0b approval remains separate. CAS/LFS/external storage, threshold changes, new runtime calls, new actors, product execution, canonical fixture changes, implementation, migration, commit, push, merge, deploy, and release remain unauthorized.
