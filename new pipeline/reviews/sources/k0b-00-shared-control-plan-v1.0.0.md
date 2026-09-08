# K0b-00 Shared Control Plane Operational Delta Plan

| Field | Value |
|---|---|
| Plan ID | `k0b-00-shared-control-plane-delta` |
| Version | `1.0.0` |
| Status | `review_candidate`; implementation forbidden pending independent review and owner approval |
| Work item / phase | `K0b-00` / `K0b` (`2.0b`) |
| Architecture owner | `W1 Kernel / shared control plane` |
| Baseline | `k0a-00-shared-control-plane` v`1.2.0`, SHA-256 `8ba07c56d850b85c2dac8c24a5fa8f18e3a677a45c90b496b86e057921f4a93f` |
| Complexity tier | `shared_plane`, at most 800 non-empty full-file lines |
| Sub-budgets | routing `<=95`; roster `<=55`; failure/recovery `<=95` non-empty lines |
| Exact hash binding | recorded outside these bytes in author/review/approval records to avoid self-reference |

## Scope envelope

This delta changes only the shared control plane. Unchanged K0a responsibilities and invariants remain binding by the baseline hash; this file does not restate or silently replace them. The common authority is `k0b-00-operational-alpha0-delta-scope-v1` (`new pipeline/architecture/k0b-00-scope-envelope-v1.yaml`, v`1.0.0`, SHA-256 `fe63742498a8192c7f67c5d430eb8c466d3621d873e3486115102510e7ca779a`). The entry evidence is the externally approved K0a-03 commit `a031ee56a36cf794646643b67270c6e0f7092e08`.

| Required field | Bound K0b value |
|---|---|
| Package | `K0b-00`; architecture delta only |
| Runtime target after approval | operational Alpha-0 on a new committed clone of the fixture, never the canonical fixture worktree |
| Scenarios | `F01-F05`, `F07`, `F09`, `F10`, `F13a`, `F15` |
| Current control components | CLI/guard, compiler engine, run controller, reconciliation/abort controller, replay materializer, checkpoint-policy coordinator, model-executor boundary |
| Routes | deterministic compiled nominal path; validated real-LLM Layer0 fallback for non-nominal state; bounded fan-out/barrier; revision/minimal replay; no direct handoff |
| Owned records | run/invocation/delivery/transition/recovery/abort/compatibility/budget-forecast control records and requests; no content artifact or binary payload ownership |
| Downstream boundary | typed requests to the shared artifact/event plane and semantic routing contracts owned by S; fixture-only terminal human/W5 policies |

K0b-00 may create only plans, review inputs, review/disposition records, ledger entries, and a hash-bound approval request. SQL migrations, registries, contracts, prompts, executors, fixture runtime, checkpoint publication, projections, and physical model calls remain forbidden until all three K0b-00 plans pass independent review and owner approval.

Explicit non-goals are a real `projects/swarm` run; reading legacy research; production or release claims; N1 layer contracts; full M; distributed leases or a project fleet scheduler; general retry/dead-letter/budget-escalation families; cache/scale/RAG; CAS/LFS/external checkpoint storage; destructive restore; and treating K0a's manual-extension decision as K0b executor authority.

## 1. Purpose, responsibility, non-goals, and applicability

The delta turns the proven single-run bootstrap controller into the deterministic operational coordinator needed to test recovery, abort, compatibility, compiled routing, repository guards, checkpoint policy, and forensic replay on a committed fixture. It owns control state and ordering, not artifact/event persistence, semantic route policy, projection rendering, checkpoint bytes, or project content.

It applies only to K0b fixture work items after the full K0b-00 architecture gate. Alpha-0 means the assigned fixture scenarios and storage/security thresholds pass; it does not mean product readiness. Any use on a real project, research import, additional layer, or unapproved executor is inapplicable and fails closed.

Implementation authority, if later approved, is limited to shared-control portions of `K0b-01` through `K0b-05`. Each work item retains its own tests and exit gate; K0b-00 approval does not authorize skipping those barriers.

## 2. Dispatcher, deterministic harness, S, Layer0, and worker boundary

| Owner | Added K0b responsibility | Boundary |
|---|---|---|
| Shared control plane | compile pinned registries and route/budget graphs; enforce state, identity, timing, window, guard, recovery, and abort policy | cannot invent semantic routes, persist artifacts/events/checkpoints, or render projections |
| S plan | define semantic route classes, fast-path applicability, fallback/blocker/revision meaning, and route-freeze behavior | cannot write control state, execute Git/SQLite, or call Layer0 directly |
| Layer0/worker contracts | return typed proposals/results for the exact scheduled invocation | cannot select capabilities, subscribers, checkpoint policy, or side effects |
| Shared artifact/event plane | persist events/artifacts/deliveries/outbox/checkpoints and perform allowed project-Git publication | cannot schedule invocations or decide semantic routes |

The compiler engine is deterministic infrastructure. It compiles only versioned, hash-bound registries/contracts into a closed route table, event reachability graph, and resource forecast. The control plane executes that table. A compiled result is not an S-authored artifact; it records the S profile/version whose semantics were compiled.

No reasoning actor calls another. Every physical invocation crosses one harness boundary with a committed before-replay point, executor binding, capability set, exact input bound, and durable dispatch. The K0a manual-extension transport remains historical F00 evidence only until owner decision `K0b-D01` pins a K0b executor.

## 3. State machine, invariants, and terminal states

K0a's immutable run/invocation evidence remains valid. K0b adds operational run states `waiting`, `reconciliation_required`, `reconciling`, `aborting`, `aborted`, `blocked`, and `blocked_over_limit`. Normal state paths are:

```text
created -> running -> waiting -> running -> completing -> completed
running|waiting -> reconciliation_required -> reconciling -> running|waiting|blocked
running|waiting -> abort_requested -> aborting -> aborted|blocked
running|waiting -> blocked|blocked_over_limit
```

`waiting` is durable and resumable from a new process/session; it is not an in-memory pause. Recovery status is explicit and never inferred from file presence alone. `blocked` requires a typed reason and terminal human/W5 queue route. `blocked_over_limit` permits only the one terminal checkpoint for the current unpublished range plus recovery/migration/owner-disposition evidence.

Operational invariants:

- one project-scoped local writer lock and one active K0b run; no distributed lease claim;
- every mutation uses expected state revision, idempotency identity, and an immutable transition record;
- an active run cannot load a different Pipeline/schema/registry/executor binding;
- every nondeterministic boundary has committed before/after replay points;
- recovery reconciles DB authority, sidecar/Git state, and any intent/result before retrying an effect;
- abort freezes new deliveries, fences late results, preserves partial evidence, and never deletes the worktree/DB;
- completion requires reachable terminal policies, no pending outbox/checkpoint obligation, and a gate-bearing readback;
- a hard budget crossing blocks the next product/external action even if the current DB transaction succeeded.

## 4. Inputs, guards, routing branches, fan-out, barriers, and fast paths

Inputs are exact CLI commands or persisted resume/abort/replay requests. The closed K0b grammar may add `resume`, `abort`, and forensic replay/checkpoint operations only through future reviewed contracts; arbitrary paths/providers/models/SQL/tool arguments remain forbidden.

| Condition | Decision | Control action |
|---|---|---|
| exact registered nominal case with all guards satisfied | `compiled_route_decision` | schedule the compiled delivery without an S0/Layer0 dispatcher model call |
| registered non-nominal/ambiguous case with approved fallback | `fallback_required` | schedule the pinned real-LLM Layer0 envelope; validate result before transition |
| missing/unknown/stale/incomplete graph or registry | `blocked_input` | no invocation or effect |
| forbidden capability/event/transition or malformed proposal | `blocked_policy` or `failed_validation` | persist terminal policy; no side effect |
| declared parallel review route | immutable fan-out snapshot | schedule exact members; close only under the compiled barrier policy |
| accepted downstream revision | `revision_requested` | route through S to the owning upstream zero and replay only invalidated descendants |

The nominal fast path is deterministic only when the compiled branch has one exact outcome and all applicability predicates are machine-known. Unknown or semantically material ambiguity never guesses. A fallback result cannot widen the compiled event/capability/root set. Direct worker-to-worker or layer-to-layer handoff has no executable route.

K0b supports only the fan-out/barrier needed by `F04`; the S delta must name the exact fixture reviewer roles and one of the canonical barrier policies. General scheduling, quorum optimization, distributed leases, and dynamic roster discovery are deferred.

`F15` uses the predeclared `HYP-DISPATCH-01` matrix: 12 nominal/ambiguous/non-nominal cases times three attempts, 36/36 without forbidden transition/capability/event, at least 34/36 oracle-matching initial choices, and at least 2/3 correct per case. Thresholds and oracle labels are pinned before execution and cannot be edited after results.

Routing section sub-budget: `<=95` non-empty lines.

## 5. Output events, subscribers, terminal policies, and cross-plane requests

The control plane is semantic producer of run lifecycle, approval/gate, revision, and typed error requests; the artifact/event plane is the only persistence/subscription authority. Retained F00 events remain unchanged. K0b adds requests for `run.blocked`, `run.abort_requested`, `run.aborted`, `revision.requested`, `gate.passed`, approval events, the three Alpha error events, and `meta.incident_detected`.

Before M1, schema/tool/security errors terminate at `block_run_and_enqueue_human`; `meta.incident_detected` terminates at `persist_incident_and_enqueue_W5`. These policies must create a durable queue item and cannot be dangling hooks. `handoff.ready/bootstrap_sink` remains executable only for the exact F00 profile.

Control-to-artifact/event requests include run and expected revision, causation/correlation, idempotency key, registry/schema versions, semantic producer, required terminal policy, and exact allowed result. Control consumes committed event/delivery IDs; it never accepts an agent statement as delivery proof.

Checkpoint policy produces `checkpoint_publish_request` with a contiguous replay-point range, DB sequence, product-state commit/tree and dirty/untracked snapshot refs, trigger, threshold status, and allowlisted paths. Projection policy similarly produces one normalized `projection_intent`; rendering and pair persistence stay outside this plane.

## 6. Artifacts, ownership, versioning, lineage, and key decisions

This plane still owns no content artifact or binary bytes. Added immutable control records are compiled profile identity, route/budget forecast, run lock, recovery/abort requests and results, checkpoint publication request/result references, replay-materialization request/result references, compatibility decisions, and gate evaluations.

Lineage extends K0a with `compiled profile -> route decision/fallback -> delivery graph -> replay range -> projection/checkpoint intents -> publication result -> gate evaluation`. Every external reference uses a stable ID plus verification profile/hash; hashes do not become identity.

Owner decisions remain canonical DB decision versions when runtime exists. YAML+Markdown are derived projections owned by the artifact/event plane. An approval must reference the exact decision/projection version and hash; generated files alone are not approvals.

## 7. Context/query allowlists, trust classes, provenance, and injection controls

The harness constructs contexts from exact-ID queries and compiled allowlists. Agent-visible input may include only the assigned artifact/control fragments, route schema, permitted result values, bounded provenance, and capability summary. Full DB dumps, checkpoint bytes, Git history, arbitrary repository files, other raw agent transcripts, and hidden security policy are excluded.

Product/fixture text, projection text, prior model output, replayed responses, tool output, and Git metadata not produced by the guard are untrusted data. They cannot select a route, executable, root, event, subscriber, approval, model, or checkpoint path. Prompt-injection/secret scan and executor/tool guards run before every physical call or tool effect; F10 failure blocks K0b and later research capability.

Forensic replay injects a recorded response as labelled evidence and does not present it as a fresh model call. Stochastic rerun receives the exact original envelope; unavailable executor/model/tool profile creates a typed reproducibility gap, never an implicit substitute.

## 8. Current roster, inputs, outputs, capabilities, and stops

| Deterministic component | Input | Output | Capability | Stop condition |
|---|---|---|---|---|
| CLI/identity guard | closed command and exact roots/pins | validated request | read identities; create bounded runtime paths | any mismatch or open argument |
| registry/resource compiler | exact registries and complete route graph | compiled profile and forecast | read pinned Pipeline records | unknown node/edge/budget or reference mismatch |
| run controller | validated request and DB revision | transitions/deliveries | short active-DB transactions | stale revision, pending obligation, incompatible binding |
| reconciliation/abort controller | durable intents/results and observed state | reconciled or blocked result | bounded inspection/cancellation protocol | unknown external state or unsafe cancellation |
| replay materializer coordinator | selected replay point and snapshot refs | materialization request/result refs | isolated fixture paths only | incomplete envelope, tree, delta, or tool/environment snapshot |
| checkpoint-policy coordinator | replay window and threshold facts | publish request or hard block | no Git write; artifact/event API only | publisher unavailable, limit crossed, dirty allowlist mismatch |
| model-executor boundary | exact invocation envelope and owner-pinned binding | transcript/usage receipt | only approved executor channel | missing pin, tool/egress violation, incomplete transcript |

There are seven deterministic components and zero control-plane LLM workers. S0, Layer0, fixture workers, and reviewers are interface actors owned by their respective plans/contracts, not this roster.

Deferred components are distributed lease/scheduler, general retry/dead-letter service, cache/scale/RAG, product alias discovery, research importer, production side-effect adapters, and full M. Only names/triggers and stable interfaces may appear before their just-in-time plans.

Roster section sub-budget: `<=55` non-empty lines.

## 9. Failure taxonomy, invalidation, replay, recovery, and abort

| Failure | Required outcome / owner |
|---|---|
| root/worktree/path/symlink mismatch | pre-effect `error.security_policy`; control blocks; W1 finding |
| unknown event/route/subscriber or incomplete graph | compiler rejection; no run activation |
| schema or proposal mismatch | `error.schema_mismatch`; no transition/effect |
| tool/executor/egress/secret violation | `error.tool_failure` or `error.security_policy`; freeze route and enqueue human |
| crash before DB commit | transaction absent; reconcile sidecars/intents and repeat only idempotent preparation |
| crash after DB commit before external/projection/checkpoint result | inspect durable intent and external/result identity; complete or block, never blind retry |
| checkpoint/outbox pending at mandatory boundary | block next effect/exit until exact result or terminal failure is persisted |
| incompatible Pipeline/schema | read-only diagnosis; backup and explicit forward upgrade or blocked resume |
| abort with unknown external effect | preserve state and terminal `blocked`; no fabricated `run.aborted` |
| late/fenced result | preserve rejected evidence; no state or artifact transition |

Minimal replay selects an exact dependency subgraph. It never rewrites prior versions; it creates new invocation/artifact/event identities for stochastic execution. Recorded-response forensic replay is deterministic evidence reconstruction. Product tree materialization uses a clean target plus the recorded commit/tree and exact dirty/untracked delta; source and target identities are checked before writes.

Graceful abort first persists `run.abort_requested`, stops new deliveries, fences prepared work, requests cancellation only for declared cancellable operations, reconciles begun intents/results, preserves partial artifacts and worktree/DB, then emits `run.aborted` only when the graph is consistent. Abort is not rollback.

Recovery is idempotent at every boundary and keeps an immutable transition history. Destructive overwrite of an active DB is forbidden; restore requires verified backup, new target path, compatibility check, and explicit human authorization.

Failure/recovery section sub-budget: `<=95` non-empty lines.

## 10. HITL, autonomy, approvals, and dialogue

Auto actions are deterministic reads, compilers, validations, DB transitions, and read-only reconciliation. Run-authorized actions are bounded fixture writes/tests and approved checkpoint publication inside the isolated fixture coordination worktree. Explicit HITL is required for architecture approval, executor binding, destructive restore/migration, threshold changes, risk acceptance, and program continuation.

`resume` may continue an already authorized run only if all pins and obligations still match. It cannot silently approve a new executor, migration, side effect, or scope. Abort requests are authenticated control inputs, not agent text.

Creative dialogue is N/A in K0b. Human/W5 terminal queue entries are safety endpoints, not dialogue sessions or M automation.

## 11. Tools, side effects, security, egress, and repository boundaries

Runtime uses a new independent committed fixture clone. The canonical fixture and Pipeline Git are read-only. Only the fixture coordination worktree may materialize the tracked checkpoint; task worktrees sparse-exclude history/runtime/backups, and Q primary worktree excludes all `.pipeline/**`. `projects/swarm` and `research/old-swarm` remain outside capabilities.

Every Git operation checks canonical root, repository role, top-level, expected branch/worktree and baseline, symlink/junction ancestry, and actual change set, then uses `git -C <exact-root>`. Shared user checkout is never reset or used as rollback. The checkpoint publisher may commit only the allowlisted checkpoint and ready projections of one DB sequence; unrelated dirty files block publication.

Tool/executable identity, arguments, cwd, environment allowlist, timeout, process/resource limits, egress destination, and expected outputs are pinned before intent. Content-derived shell, package hooks/plugins, arbitrary provider/network, credential discovery, and direct SQL are forbidden. The exact model transport remains blocked until owner decision `K0b-D01`.

K0b scenarios use synthetic/reversible effects only. No product/external mutation, research import, push, merge, deploy, or release is authorized.

## 12. Context/scale policy, invocation and human-attention budgets

The delta supports only bounded fixture graphs. Repository-wide inventory, dynamic sharding, RAG, cache, and scale fallbacks are deferred. Every invocation proves `effective_limit = min(configured_gate, model_limit - reserved_output - safety_margin)` before dispatch; unknown bounds block.

Plan-production authority is the single package `K0b-plan-deltas`: light, six nominal/twelve worst-case design calls. Nominal is three separate authors plus three fresh-context reviewers. One bounded author/reviewer return pair per plan consumes the six-call margin; a second return requires owner/budget disposition despite the global two-return ceiling. Human attention is one session nominal/worst, one/two blocking decisions, 30/30 active minutes, 30-minute maximum, batchable.

This file consumes one author call. It creates no runtime calls and does not duplicate the package in the other two plans. Later operational authority is `K0b-runtime-operational`, standard, 16 nominal/30 worst-case calls across `K0b-01..05`; exact per-scenario allocation must be compiled and approved before execution. `F15`'s 36 attempts are a separately predeclared hypothesis measurement and must be reconciled with that package before physical calls; if the forecast cannot contain it, scope/budget must be revised rather than hidden.

## 13. Binary payload budget or proved N/A

`N/A` for this plane. Its reviewed contract must forbid binary persistence and expose only IDs, enums, numbers, bounded UTF-8 canonical JSON/text, hashes, and version references. Checkpoint/BLOB bytes are created and first persisted only by the shared artifact/event plane under its complete binary budget; control carries `checkpoint_id` and result refs, never the bytes.

Nominal/worst-case new binary objects and bytes attributable to this plane are zero. Any raw checkpoint, archive, trace, media, opaque tool bytes, or BLOB write API invalidates this N/A and blocks implementation until a complete machine-readable budget and D0 reconciliation are approved.

## 14. Downstream consumers and actual consumption

The artifact/event plane consumes validated transition, event, outbox, and checkpoint requests. S consumes compiled route/fallback/revision status and freezes/unfreezes routing on abort/reconciliation. Layer0/workers consume exact invocation envelopes. CLI/owner gates consume bounded readbacks and evidence.

Actual consumption requires durable delivery/result or gate records with exact producer/consumer contract versions, IDs, semantic fields read, and disposition. A compiler output is consumed only when it gates a run or delivery; a checkpoint request only when a matching publisher result and project-Git identity are reconciled; replay only when the materialized envelope/tree/delta is validated. Self-report is insufficient.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: closed state/event/route graph; every blocker and terminal has an owner/route; no dangling subscriber; one local writer lock.
- Contract: exact compiler reference cases; incomplete route/fan-out/retry/dialogue graph fails; undeclared event/transition/capability fails.
- Foundation: forward migration/backup compatibility, idempotent recovery at every transaction/outbox/checkpoint boundary, graceful abort, hard-limit block, root/worktree/tool guards.
- Behavioral: deterministic nominal route, real-LLM non-nominal fallback, `F15` k/n and forbidden-transition criteria, bounded fan-out/barrier and revision replay.
- Replay: clean clone without runtime DB restores tracked checkpoint to a new path, materializes selected tree/delta/envelope, and separates forensic response injection from stochastic rerun.
- Adversarial: `F09` wrong root and `F10` injection/secret/tool attempt block before effect; late/fenced result and malformed proposal remain evidence only.
- Fixture E2E: control-owned portions of `F01-F05`, `F07`, `F09`, `F10`, `F13a`, and `F15` on an independent committed fixture clone.
- Real project: N/A and forbidden before K0b-05/N1 gates.

## 16. Evidence package and readiness criteria

Evidence binds Pipeline/fixture commits and trees; all three plan/review/approval hashes; schema/registry/compiler/executor versions; run/invocation/delivery/transition IDs; before/after replay envelopes; root/worktree/tool/egress proofs; fan-out/barrier and revision graph; recovery/abort intents/results; projection/checkpoint requests/results; threshold status; compatibility backup/restore refs; F15 matrix/oracle/attempts; exact commands/results; and finding dispositions.

Architecture readiness requires independent review of this exact hash, ledger-resolved author/reviewer calls, consistency with the other two deltas, closed `K0b-D01`/`K0b-D02`, approved complexity/binary dispositions, and no implementation files. Fixture readiness later requires all assigned scenarios, clean-clone F13a, zero forbidden transitions/effects, and storage thresholds below hard stop or an owner route.

Complexity evidence records full non-empty lines plus routing/roster/failure counts against `800/95/55/95`. Claims are falsifiable by compiled graph/reference cases and fault injection, not prose equivalence.

## 17. Migration note from K0a and old pipeline

The authoritative source is the approved K0a shared-control plan and F00 evidence. Retained are deterministic harness ownership, immutable transitions, exact replay envelopes, one bounded attempt policy, root/pin guards, and the separation of semantic proposals from execution.

Rewritten for K0b are disposable-run regeneration into idempotent reconciliation/resume; the one-route mandatory LLM dispatcher into compiled nominal plus validated non-nominal fallback; inspect-only replay into clean-clone forensic materialization; cancellation into graceful abort; and static worksheet checks into a registry/resource compiler.

No new old-pipeline content was read or imported for this delta. K0a records and migrations remain immutable; K0b uses forward-only migrations and compatibility/backup tests. Retired behavior includes filesystem truth, direct handoff, blind effect retry, shared-checkout reset, unguarded Git, and human text as approval.

## 18. Risks, open decisions, and deferred capabilities

| Item | Status / control |
|---|---|
| K0a transport might be assumed valid for K0b | blocker `K0b-D01`; owner must hash-bind manual extension, separate adapter, or narrow/pause before physical F15 |
| F15's 36 attempts may exceed the current operational package interpretation | resource compiler must reconcile exact package allocation before calls; no hidden budget credit |
| Compiler could encode S semantics and blur ownership | S owns semantic profile; control owns generic compile/execute engine; cross-plan tests compare hashes and outputs |
| Recovery could repeat an uncertain effect | durable intent/result plus external-state reconciliation; unknown outcome blocks |
| Checkpoint coordinator could become a second publisher | control creates policy request only; artifact/event plane exclusively writes snapshot/outbox/Git |
| Binary N/A could become stale through replay/checkpoint convenience | bytes forbidden at control API; only version/result refs cross the boundary |
| Fixture Alpha-0 could be mislabeled product-ready | explicit fixture-only readiness and no product/research capabilities |

Open owner decisions are `K0b-D01` (runtime executor binding), `K0b-D02` (exact three-plan scope), and `K0b-D04` (the impossible current `36 F15 attempts > 30 worst-case K0b calls` budget conflict). `K0b-D03` activates only if forecast/measurement crosses checkpoint warning or hard thresholds. Any unresolved blocker keeps the plan at `review_candidate` and prevents K0b-01.

Deferred capabilities remain real project aliases/runs, research import, N1 layer contracts, distributed leases, general retries/dead letters, budget escalation FSM, cache/scale/RAG, CAS/LFS/external storage, release, and full M. No implementation or readiness claim is created by this document.
