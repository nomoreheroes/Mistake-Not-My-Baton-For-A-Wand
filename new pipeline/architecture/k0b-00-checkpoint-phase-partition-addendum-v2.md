# K0b-00 checkpoint budget phase-partition addendum v2.0.0

Status: `review_candidate`; revision authority `0725cc34cf660ab821fc2cb08fd748df7a17e63c51c6d14844cc2c56671af6f7`; author input `fa7965ed72984b39cce118bd1cc283be7970122c78386787720b1cfe340de595`. This architecture record grants no runtime, contract, migration, fixture, checkpoint, model-call, or approval authority.

Exact cross-cutting authority: base policy `8e9696916c939c6d9fa337c7bddc8b022c7657a2c105c0e51773b4c6ba1a67f3`; K0b policy overlay `ed224c7473810be838c2c22129d567c337bd16fd13532efb893074e684367ce8`; scope v2 `e839396d9199fa85e5474b3a45a852e7b6b59d81d6910ae67897f7dffe627cde`; forecast v3 `ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a`; reconciliation v3 `d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb`. It supersedes rejected addendum v1 `ca472f20201363e088d51d8e4b45c4f91b675d9346d8226189266d39d69e8896` only for D03 successor architecture.

## 1. Purpose, boundaries, non-goals, and applicability

This addendum applies the unchanged checkpoint hard limits to two owner-approved real chronological `checkpoint_budget_phase` intervals within the K0b program phase and one fixture project chain. Unlike v1, its threshold unit is expressly defined by a versioned K0b policy overlay and scope v2. The exact order is `K0b-runtime-operational` then `K0b-F15-exact-measurement`; the intervals are contiguous, non-overlapping, exhaustive, immutable before effect, and capped at two.

It is neither arbitrary batch renaming nor a new product phase. Cumulative chain bytes remain visible and subject to clone/performance gates. Thresholds, storage, 16/30 operational calls, exact 36 F15 calls, B01 seeds, and factor 1.0 are unchanged. Three separately authored/reviewed v2 layer plans are required; this addendum alone closes nothing.

## 2. Dispatcher, compiler, artifact/event, S, and operator boundaries

Shared control owns phase-policy compilation, exact call/trigger membership, counters, admission, hard stops, seal/abort requests, and successor activation. Artifact/event exclusively persists bindings, intents/results, outbox rows, cumulative SQLite snapshots, projections, Project-Git publications, measurements, and seals. S owns semantic route meaning only and cannot choose phase, checkpoint, trigger, call allocation, or byte credit. The operator owns only explicit gates and cannot reclassify evidence.

Compiler outputs are immutable `compiled_checkpoint_phase_partition_v1` and `compiled_checkpoint_publication_budget_v2`, binding policy/scope/forecast/addendum/three-plan hashes, ordered intervals, work-item and call allocation, stable trigger allowlist, predecessor seal, byte/count limits, and partition digest. Unknown, overlapping, missing, cyclic, or stale output blocks.

## 3. State machine, invariants, terminal states, and chronology

Closed states are `planned`, `active`, `sealing`, `sealed`, `blocked`, `aborted`; edges are `planned -> active`, `active -> sealing`, `sealing -> sealed`, and any nonterminal to `blocked|aborted`. Terminal states never reopen. Exactly one phase is active or sealing.

Operational contains all K0b-01/02/03 and pre-F15 K0b-04 checkpointed activity plus all 16/30 non-F15 physical-call capacity. Every such call must be terminal and its outbox reconciled before the operational seal and first F15 submit. F15 contains exactly 36 calls, direct measurement evidence, deterministic post-F15 K0b-04 closure, and deterministic K0b-05 forecast/owner disposition in the same top-level run segment with zero model calls. Any different chronology blocks and reforecasts.

## 4. Inputs, guards, membership, routing, batching, and fast paths

Inputs are exact chain, program/phase/work-item/scenario/attempt/call/trigger/checkpoint/outbox/seal identities and bound authority hashes. Membership comes only from the compiled work graph: K0b-01/02/03 are zero-call operational; all non-F15 capacity is pre-F15 K0b-04 operational; exact F15 is F15 phase; post-F15 K0b-04/K0b-05 is deterministic F15 phase. Unclassified or multiple membership blocks.

The only F15 boundary trigger IDs are `k0b.f15.boundary.entry_gate`, `k0b.f15.boundary.program_owner_wait_or_exit`, `k0b.f15.boundary.exit_gate`, and `k0b.f15.boundary.top_level_run_end`, cardinality one each. K0b-05 cannot create another run. Any fifth identity blocks before publication. Batches contain at most 12 and never reset phase totals. Identical duplicates return the original result; conflicts block.

## 5. Output events, subscribers, terminal policy, and handoffs

Planned records are `checkpoint_phase_binding_v1`, `checkpoint_publication_budget_v2`, `checkpoint_phase_transition_v1`, `checkpoint_phase_seal_intent_v1`, `checkpoint_phase_seal_result_v1`, and phase fields on existing publication requests/results. They carry exact chain, phase, partition, policy, scope, forecast, plan, trigger, causation, idempotency, sequence, checkpoint, outbox, and seal references.

Control consumes persisted results; artifact/event consumes only typed requests; publisher consumes committed outbox sequence; replay/abort consume terminal/seal state; human/W5 consumes typed hard-stop, incident, or program-disposition evidence. No direct handoff exists.

## 6. Schemas, artifacts, ownership, versioning, lineage, and seals

Future schemas are forward additions only after approval; none is created here. Binding uniqueness is `(project_chain_id, checkpoint_phase_id, partition_digest)`; publication uniqueness is `(project_chain_id, checkpoint_phase_id, trigger_id, checkpoint_id)`. Seal lineage includes predecessor, terminal cumulative checkpoint, projection pair, Git commit/tree, highest sequence, counters, measured bytes, and exact authority hashes.

Checkpoint contents remain cumulative. Phase attribution partitions chronological publications, not stored history. Hashes prove integrity but are never logical identity. No artifact/BLOB/event/outbox/Git object moves phases for budget advantage.

## 7. Context, query allowlists, trust, provenance, and injection

Queries are restricted to typed records for the exact fixture chain, two phases, compiled work graph, packages, policy, scope, forecast, current outbox, and predecessor seal. Model text, transcript, artifact body, external metadata, and content-derived paths cannot select membership, triggers, counters, thresholds, or destinations. Missing provenance, injected labels, or stale authority blocks.

## 8. Current roster, inputs, outputs, capabilities, and stops

No actor or capability is added. Existing control, artifact/event, S, harness, operator, and fixed-hybrid executor boundaries remain. Stops include stale digest, wrong root/worktree, publication gap, conflicting duplicate, missing seal, phase overlap/gap, post-seal non-F15 call, fifth boundary trigger, F15 publication 30, checkpoint at least 100 MiB, phase pack at least 1 GiB, or any threshold/storage/credit/third-phase request.

## 9. Failure, invalidation, replay, recovery, crash, abort, and duplicates

Same-phase replay keeps phase identity. Cross-phase replay may read immutable predecessor artifacts but charges new records to the active phase. Any repair that would mutate a seal, add a post-F15 non-F15 call, or exceed a bound freezes the successor and requires reforecast. Identical duplicates do not add logical attempts/publications; conflicting reuse emits incident evidence and blocks.

Publication and seal use durable intent/result. Crash before effect resumes the same intent; unknown filesystem/Git outcome reconciles exact hashes/sequence before retry; blind retry is forbidden. Crash between seal and F15 leaves no active phase. Abort fences pending effects; one policy-permitted terminal over-limit checkpoint never marks a phase passing or admits a successor. Late/stale/wrong-phase results remain rejected evidence.

## 10. HITL, autonomy, approvals, dialogue, and compatibility

There is no dialogue or automatic escalation. The one owner wait trigger is the K0b-05 program disposition inside the same post-F15 segment. Entry/exit gates and one terminal run end complete the exhaustive four-trigger map. More waits, gates, or runs block.

Compatibility binds commits/trees, base/overlay policy, scope v2, three v2 plans/reviews, forecast/reconciliation/addendum, compiler/schemas/executor, partition/trigger digests, predecessor seal, and call allocation. Any change is stale and requires reviewed compatibility/reforecast evidence.

## 11. Tools, side effects, security, egress, and repository boundaries

Future writes remain harness-only in a coordination worktree of a new committed fixture clone. Canonical fixture is immutable; task worktrees exclude runtime/history/backups; forbidden roots stay unread/unmodified. Wrong root, path escape, symlink/junction, dirty unrelated state, secret/PII, SQLite attach/extension, forged seal/approval, model-selected phase, or direct API blocks before effect. Only artifact/event writes DB/projection/Git; partition adds no publisher or egress.

## 12. Context scale, invocation, publication, and human budgets

Design is 24-call owner cap: ordinals 19/20 control, 21/22 artifact/event, 23/24 S, leaving zero return margin. Physical budgets remain operational 16/30 before F15 and exact F15 36/36; design is not checkpointed. F15 uses 8/22 window publications plus four boundary IDs = 12/26; operational remains 14/34. No call, trigger, retry, overlap, compression, delta, dedup, cross-phase, or batch-reset credit exists.

## 13. Binary/checkpoint budget and D03 arithmetic

| Phase | Checkpoint nominal/worst | Publications nominal/worst | Pack nominal/worst | Worst margin |
|---|---:|---:|---:|---:|
| operational | `9,437,184 / 27,262,976` | `14 / 34` | `132,120,576 / 926,941,184` | `146,800,640` |
| F15 | `10,485,760 / 36,700,160` | `12 / 26` | `125,829,120 / 954,204,160` | `119,537,664` |

Each checkpoint is below `104,857,600`; each phase pack below `1,073,741,824`; worst 12-publication batches `327,155,712/440,401,920` are below warning `536,870,912`. B01 seeds `6/12` and `2,236,416/4,472,832` remain. Observable chain sum `257,949,696/1,881,145,344` remains mandatory scale evidence, not threshold credit.

## 14. Downstream consumers and actual consumption

Control admission consumes compiler outputs; artifact/event uniqueness/outbox and publisher consume phase/trigger/sequence; replay/abort consume seals; storage gate consumes measured bytes and counters; K0b-05 consumes sealed F15 evidence. Tests must prove every consumer rejects wrong, stale, missing, overlapping, over-count, or over-byte data.

## 15. Structural, contract, behavioral, fixture, and real-project tests

Tests cover two ordered intervals, exhaustive work-item/call/trigger mapping, closed FSM, one publisher, exact formulas, four stable IDs, 12-batch and 26/29 boundaries, seal-before-F15, 36 F15 calls, zero post-F15 calls, same/cross-phase replay, identical/conflicting duplicate, crash at each intent/effect/seal edge, abort/late fencing, and hard edges. A fifth trigger, second K0b-05 run, post-seal call, overlap, third phase, or credit fails. Fixture execution waits for approval in a new clone; real project is forbidden.

## 16. Evidence, observability, acceptance, and readiness

Evidence records exact identities/hashes, state/phase/member/trigger, counts, windows, bytes, margins, outbox/checkpoint/seal, replay/crash/abort/duplicate, p95, clone, cumulative chain/object metrics, and actor without secrets or fabricated measurements. Architecture requires all 18 categories, exact hash graph, three separate authors/reviews with zero blockers, compatible ownership, arithmetic tests, and no implementation. D03 closes only after all v2 reviews and exact owner approval. Runtime later requires compiler equivalence, measured bounds, publication p95 under 10 seconds, clone restore under 120 seconds, and all negative scenarios.

## 17. Migration and supersession

This is planning supersession, not database migration. Policy overlay and scope v2 make the denominator explicit; forecast/reconciliation v3 supersede D03 parts of v2 while retaining history, B01, D04, thresholds, storage, and calls. v1 plans remain immutable evidence; new v2 plans must replace them in final authority.

## 18. Risks, remaining blockers, deferred capabilities, and non-authorizations

Risks are denominator gaming, hidden post-F15 work, missing triggers, and cumulative Git growth; fixed controls are two milestone phases only, full allocation, four stable IDs, zero credit, immutable seals, chain observability, and hard stops. Any v2 review failure pauses because no design-call margin remains. Exact manual model receipts remain pre-dispatch and final K0b approval remains separate. Runtime, schemas/contracts/migrations, fixtures/checkpoints, physical calls, threshold/storage changes, third phase, product/research work, canonical fixture edits, commit, push, merge, deploy, and release remain unauthorized.
