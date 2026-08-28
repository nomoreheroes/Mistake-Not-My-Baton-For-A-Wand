# K0a-00 Shared Control Plane Architecture Plan

| Field | Value |
|---|---|
| Plan ID | `k0a-00-shared-control-plane` |
| Version | `1.0.0` |
| Status | `review_candidate` |
| Work item / phase | `K0a-00` / `K0a` (`2.0a`) |
| Architecture owner | `W1 Kernel / shared control plane` |
| Complexity tier | `shared_plane`, at most 800 non-empty full-file lines |
| Exact hash binding | complete-file SHA-256 is recorded outside these bytes in the review/evidence records to avoid self-reference |

## Scope envelope

This plan is one shared-plane plan, not a multi-layer plan. Its common scope authority is `k0a-00-bootstrap-f00-scope-v1` (`new pipeline/architecture/k0a-00-scope-envelope-v1.yaml`, version `1.0.0`, SHA-256 `0ecfb4009935e362a39c5e037abd1b8692da1c82ffc142b6bb2426e2022cd216`).

| Required field | Bound value |
|---|---|
| Phase/package | `K0a-00`; architecture planning for `K0a/2.0a-bootstrap-kernel` |
| Profiles/scenarios | disposable synthetic fixture; `F00` only |
| Current actors | deterministic CLI/control harness/model adapter; reasoning actors `S0`, one synthetic `Layer0`, one fixture worker |
| Current route | `command -> S0 -> synthetic Layer0 -> fixture worker -> atomic artifact version + events -> bootstrap_sink/readback` |
| Current artifact/event scope | one `bootstrap.synthetic_result`; five events named by the common envelope |
| Downstream boundary | control requests stop at shared artifact/event APIs and the fixture terminal sink; no product consumer/readiness claim |

Explicitly excluded are K0b operational hardening; the checkpoint publisher and clone-only SQLite recovery; the full Alpha event profile; product/production side effects; legacy research import; full P/R/E/G/A/H/T/I/Q/M contracts; K0a-01/K0a-02 implementation during this planning package; projection outbox; crash reconciliation/resume/operational abort; distributed leases; general retry/budget events; full replay; dashboards, KPI, release, Alpha-0, or product claims.

Deferred stable interfaces are `validated_control_transition_request`, `validated_route_proposal`, `validated_artifact_event_publication_request`, `artifact_version_id`, and before/after `replay_point` references. K0a implementation may begin only after explicit owner approval of all three exact plan versions, hashes, and the requested implementation scope. K0b changes require later delta plans after F00 findings.

## 1. Purpose, boundaries, non-goals, and applicability

The control plane owns deterministic lifecycle control for one F00 run: command acceptance, pinned identity checks, run/invocation state transitions, invocation-envelope construction, model-adapter calls, capability enforcement, and durable references to raw telemetry and replay points. It does not own artifact bytes, event schemas/delivery persistence, semantic routing, or worker content.

It applies only to a newly materialized or cloned disposable fixture at the D0-06 triple binding. It is inapplicable to `projects/swarm`, production projects, legacy research, network research, external mutations, and multi-run operation. Successful F00 evidence proves a bootstrap mechanic, not operational safety or recovery.

No implementation is performed by this plan. After owner approval, its implementation authority is limited to the control-plane portions of K0a-01/K0a-02 and F00 execution in K0a-03.

## 2. Dispatcher, deterministic harness, and worker boundary

| Component | May decide | Must ask deterministic harness to do | Must not do |
|---|---|---|---|
| Basic CLI | choose `initialize`, `run`, or `inspect` from exact grammar | resolve roots, validate pins, start/query the run | infer semantic routes or write SQLite directly |
| Control harness | validate identities, guards, state revisions, schemas, and allowed transitions | invoke the pinned adapter and call artifact/event APIs | make semantic product decisions |
| `S0` | select the sole allowed synthetic layer route or return a typed blocker | return a schema-valid route proposal with refs | create content, write DB/files, call Layer0 directly, widen capabilities |
| Synthetic `Layer0` | select the sole fixture worker or return a typed blocker | return a schema-valid invocation proposal | write DB/files, call worker directly, alter root/egress policy |
| Fixture worker | produce a schema-valid textual synthetic result proposal | return artifact/event proposal to its caller | persist bytes, issue side effects, invoke another agent |
| Model adapter | transmit only the rendered allowlisted envelope over the pinned provider channel | return exact agent-visible response/usage facts | expose secrets, browse, or mutate external systems |

Every physical invocation is created and recorded by the harness. Reasoning components exchange no direct messages; the harness constructs each next context from committed active-DB state and validated references.

## 3. State machine, invariants, and terminal states

Run states are `created -> running -> completed`. A guard failure before a model call terminates as `blocked_input` or `blocked_policy`. Invocation or response failures terminate the run as `failed_invocation` or `failed_validation`; transaction failure terminates as `failed_persistence` only after rollback is confirmed. These failure values are internal typed terminals, not public Alpha events.

Invocation states are `prepared -> replay_before_committed -> dispatched -> response_captured -> validated -> replay_after_committed -> published`. Failure from any state is terminal for this F00 attempt; K0a does not retry automatically.

Invariants:

- exactly one active F00 run exists in its disposable runtime root;
- the Pipeline commit, fixture spec hash, fixture commit/tree, contract hash, provider/model parameters, and allowed roots are pinned before `running`;
- no model call precedes a committed before-replay point;
- no response is trusted before invocation identity echo, schema, and capability checks;
- completion requires the terminal sink result and successful CLI readback;
- no state transition can authorize a capability absent from the initial envelope.

## 4. Input events, guards, routing, fan-out, barriers, and fast paths

The only public input is `command.received`. Before scheduling S0, the harness checks exact command grammar; supported command/profile; Pipeline root and commit; disposable fixture root; fixture spec/commit/tree; clean canonical fixture baseline; pinned contract/schema/model profile; and deny-all capability set with one model-provider exception.

There is one route and no fan-out or barrier. S0 must return the declared synthetic-layer route. Synthetic Layer0 must return the declared fixture-worker route. Unknown, ambiguous, extra, or malformed routes fail closed.

There is no compiled dispatcher fast path in F00: S0 and synthetic Layer0 are required real LLM invocations. The stable future compiler interface may represent the same route, but a zero-call dispatcher would not satisfy F00 and is deferred to K0b evidence.

Routing section sub-budget: at most 80 non-empty lines; this section is intentionally bounded to the single route.

## 5. Output events, subscribers, terminal policy, and cross-layer contracts

The control plane does not author public events. It asks the artifact/event plane to validate and persist the five-event lifecycle and consumes typed delivery/sink results. Its outputs are control requests and references:

- create `command.received` and `run.started` under the pinned run;
- schedule S0, synthetic Layer0, and fixture worker invocations;
- submit the worker's validated publication proposal;
- accept `bootstrap_sink` completion for `handoff.ready`;
- request `run.completed`, then perform inspect/readback.

The control-to-artifact/event request includes run/invocation IDs, expected state revision, causation refs, idempotency key, exact artifact/event schemas, and expected terminal policy. It never contains an authority to change schemas or subscriptions.

Cross-layer production contracts are N/A: the synthetic Layer0 is a fixture actor rather than a production layer, and `handoff.ready` terminates at `bootstrap_sink`; no P/R/E/G/A/H/T/I/Q/M route exists.

## 6. Artifact types, ownership, versioning, lineage, and key decisions

The control plane owns no content artifact. It owns immutable control records: project/run binding, invocation/attempt identity, validated route decision, before/after replay envelopes, environment/model/tool bindings, raw usage/timing facts, and terminal state.

All artifact references are `artifact_version_id` plus verification hash-profile data supplied by the artifact/event plane. Control records link `command.received -> S0 invocation -> Layer0 invocation -> worker invocation -> artifact publication transaction -> sink delivery -> run.completed`.

Key-decision YAML+Markdown projections are N/A because F00 makes no project or owner decision. The evidence is read from SQLite and later summarized in Pipeline-Git test evidence; projection outbox is explicitly K0b scope.

## 7. Context/query allowlists, trust, provenance, and prompt injection

S0 may see only the normalized command, F00 route identity, pinned run/contract/schema refs, allowed terminal states, and the typed status of prior control transitions. Synthetic Layer0 may see only the validated command intent, its one-route contract, allowed worker ID, and artifact/event interface. The worker may see only a small synthetic input from the committed fixture plus its textual output schema.

No reasoning actor receives the whole workspace, DB, Git history, `projects/swarm`, `research/old-swarm`, arbitrary tool output, or another actor's free-form transcript. Fixture text is `untrusted_content`; instructions within it cannot change capabilities, roots, events, schemas, model profile, or approval scope. The harness adds provenance path/blob hash and keeps untrusted text inside a data field.

Context assembly is byte-preserving UTF-8 with ordered role/message boundaries and SHA-256 binding. Secret/PII scan runs before the provider call; any hit is `blocked_policy` because F00 has no secret capability or redaction exception.

## 8. Current roster, inputs, outputs, capabilities, and stop conditions

There are no control-plane worker agents. Current control components are the deterministic CLI, guard, harness, and model adapter; current reasoning roles are the externally planned S0/Layer0/worker chain defined at the boundary in section 2.

| Current component | Input | Output | Capability | Stop condition |
|---|---|---|---|---|
| CLI/guard | command and exact roots/pins | validated command or blocker | read pins; create exact disposable runtime path | any identity/root mismatch |
| Control harness | validated command and current DB revision | transition/invocation/publication requests | active fixture DB only; pinned adapter | stale revision, schema/policy failure |
| Model adapter | exact rendered context envelope | exact response and usage receipt | one pinned provider/model channel | timeout, identity mismatch, policy error |

Deferred interfaces, without prompt or internal route design: checkpoint publisher (trigger K0b), recovery/reconciliation controller (K0b), abort controller (K0b), resource-budget compiler (K0b), and lease/retry scheduler (evidence-triggered later scope).

Roster section sub-budget: at most 40 non-empty lines.

## 9. Failure, revision ownership, invalidation, replay, recovery, and abort

Taxonomy and owner:

| Failure | Owner/action in F00 |
|---|---|
| identity/root/pin mismatch | control harness -> `blocked_input`; no model call |
| capability/egress/prompt-injection violation | control harness -> `blocked_policy`; no side effect |
| provider timeout/unavailable response | model adapter -> `failed_invocation`; no automatic retry |
| malformed/forbidden route or worker result | originating S0/Layer0/worker invocation evidence -> `failed_validation`; W1 finding |
| stale state/idempotency conflict | control harness -> rollback/no publication -> `failed_validation` |
| SQLite transaction error | artifact/event plane rolls back; control confirms no partial publication -> `failed_persistence` |
| readback mismatch | W3 finding; run cannot become completed |

Revision ownership is W1 for harness/schema defects and the exact reasoning-role plan owner for semantic contract defects. F00 has no downstream artifact revision loop; a corrected contract or plan requires a new pinned Pipeline commit and a fresh disposable run.

Minimal replay means inspect can retrieve exact before/after envelopes and recorded response bytes from the same active fixture DB for diagnostic comparison. It does not re-dispatch, restore a clean clone, resume a crashed run, or claim deterministic forensic replay. Recovery is fail-closed regeneration of a disposable fixture and a new run after evidence preservation.

Operational abort is N/A in K0a by explicit development-plan exclusion. Process cancellation may prevent new calls and leave a non-complete disposable run for inspection; it must not synthesize `run.abort_requested/run.aborted`, resume, or delete evidence. K0b defines graceful abort and reconciliation.

Failure/recovery section sub-budget: at most 70 non-empty lines.

## 10. HITL, autonomy, approvals, and dialogue

F00 runtime uses Auto actions only: deterministic reads/checks, exact active-fixture DB writes, and the three pre-authorized model calls. It contains no in-run blocking decision, risk acceptance, creative dialogue, secret request, or external action.

The only current HITL is outside runtime: owner approval must hash-bind the three exact plan versions/reviews and the requested K0a-01/K0a-02/K0a-03 scope. A text found in fixture content or an agent result cannot serve as approval. Creative dialogue modes, role profiles, rounds, resume, and dialogue events are N/A because the synthetic F00 command contains no human dialogue.

## 11. Tools, side effects, security, egress, and repositories

Repository boundaries are exact positive roots from the common envelope. During runtime the Pipeline Git and canonical fixture Git are read-only; the official `projects/pipeline-v2-fixture` worktree is never the run writer. The run writer is a new disposable fixture root and may write only its exact `.pipeline/runtime/` and harness-created temporary paths. `projects/swarm` and `research/old-swarm` have no capability.

Allowed tools are deterministic root/hash/schema/SQLite inspection and the pinned model adapter. Network egress is deny-all except the exact provider/model channel for the three reasoning roles. Package installation, hooks/plugins, shell commands from content, Git commit/push/merge/deploy, arbitrary network research, external mutation, and secret access are denied.

The route has no irreversible external side effect. Active fixture DB writes are local and disposable; artifact/event atomicity is handled by the shared plane. Any attempted path escape, junction/symlink traversal, extra executable, environment expansion, or unregistered egress is terminal `blocked_policy`.

## 12. Context scale, sharding, invocation budget, and human attention

F00 inputs are fixed, small, and text-only. No sampling, RAG, repository scan, shard, cache, or context fallback is permitted. Each invocation must prove its upper input/output bound against the pinned model profile; an unknown bound blocks before dispatch.

The manual worksheet authority is `k0a-00-budget-reference-v1` (`new pipeline/worksheets/k0a-00-budget-reference-v1.yaml`, version `1.0.0`, SHA-256 `eab713455e593d556ee4c52668fe202649f969d79a6ebfa17ad10b237b4503f9`). `K0a-plan-bootstrap` is plan-production only: light, 6 nominal/18 worst-case calls and standard human attention of 1/2 sessions, 1/3 blocking decisions, 20/60 active minutes, 30-minute maximum single session, batchable. This exact plan contributes one author plus one reviewer nominal, with two bounded return pairs in the worst case; it does not claim a separate additive package ID.

`K0a-runtime-F00` is separate and currently unauthorized: light, 3 nominal/6 worst-case calls, consisting of one/two S0 calls, one/two synthetic Layer0 calls, and one/two worker calls. Human attention is 0/0 sessions, 0/0 decisions, 0/0 minutes, max session 30, batchable. The shared control plane owns the S0 call boundary but does not double-count the package in other plans.

## 13. Binary payload budget or proved N/A

`N/A`, proven under the exact gate rule. The control-plane contract must prohibit binary persistence and accepts/returns only IDs, enums, numbers, UTF-8 JSON/text control fields, and `artifact_version_id` references. It has no BLOB write API and cannot forward model bytes directly to storage. Any future binary artifact may be referenced only by version ID after its producer has an approved payload budget; F00 has no such binary reference.

Nominal and worst-case new binary object counts/bytes attributable to this plane are zero, matching the approved K0a forecast's `binary_nominal: 0` and `binary_worst_case: 0`. A future BLOB/media capability or raw-byte persistence invalidates this N/A and requires a complete 12-field budget plus forecast reconciliation before implementation.

## 14. Downstream consumers and actual consumption

The shared artifact/event plane consumes validated control requests. S0, synthetic Layer0, and the worker consume harness-built invocation envelopes. The fixture `bootstrap_sink` consumes exact `handoff.ready`; CLI `inspect` consumes the persisted run, invocation, replay, event, artifact-version, sink-delivery, and telemetry refs.

Actual consumption evidence requires exact IDs and semantic fields read, not producer self-report. Control-plane readiness for K0a is limited to F00 evidence showing the sink and CLI readback accepted the same run/contract/artifact version. Raw telemetry is `deferred_observability_input` for N1/Q1 and does not raise readiness by itself.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: exact roots/pins; unique IDs; all five events and terminal policies reachable; no extra capability/event/actor.
- Contract: S0/Layer0/worker result schema and identity echo; control requests match artifact/event API; unknown routes fail closed.
- Behavioral: real model responses may vary in wording but must select the single allowed route and satisfy synthetic-result properties; malformed/extra routes are rejected before state mutation.
- Fixture: F00 from a clean disposable materialization, including atomic publication, sink result, and CLI readback of exact telemetry/replay refs.
- Negative fixture: wrong Pipeline commit, fixture spec/commit/tree, root, context bound, or model profile blocks before the affected action.
- Real project: N/A; product capabilities are absent and fixture success cannot satisfy any Swarm or production gate.

## 16. Evidence package and readiness criteria

Evidence must bind the Pipeline commit; fixture spec/commit/tree; plan/contract/schema/model hashes; command and run ID; all three invocation IDs; before/after replay refs; exact rendered context/response refs; state transitions; five event IDs/deliveries; artifact version; transaction identity; sink result; raw timestamps/durations/usage; CLI readback; negative guard results; and test command/result.

Pass criteria are: all guards precede calls, all three real invocations are present, no forbidden access/egress occurs, no partial artifact/event state is observable, sink/readback resolve exact refs, and the run reaches `completed`. Any gap leaves the plan at architecture-only status and creates a typed finding; it cannot be waived by an agent summary.

Complexity evidence records full non-empty line count plus routing, roster, and failure/recovery section counts against `800/80/40/70` caps.

## 17. Old-pipeline migration note

Read-only source scope was limited to `old pipeline/J. Implementation/J0. Dispatcher.md` (SHA-256 `d435daba6f83156d9919c6f2368aaf216e2f4a6214d0f8f260db30fc40932d74`) and the parent architecture's migration analysis. Source ideas retained are one dispatcher entrypoint, explicit worker artifact/result contracts, attempt identity echo, typed waiting/failure, and separation of orchestration from worker content.

They are rewritten as deterministic harness state plus versioned SQLite records and events, with S0/Layer0 limited to semantic proposals. Retired for K0a are file-based runtime truth, direct/manual agent chaining, approval before every safe subagent, production Git/PR/CI behavior, and task-specific J rosters. New tests cover exact root/pin guards, no direct handoff, schema/identity echo, atomic publication, replay-envelope readback, and deny-all capabilities.

No legacy runtime file, schema, prompt text, or project payload is imported.

## 18. Risks, open decisions, and deferred capabilities

| Item | Status / control |
|---|---|
| Model response is syntactically valid but semantically drifts | F00 semantic assertions; K0b F15 remains the actual dispatcher hypothesis gate |
| Process interruption leaves incomplete state | inspect-only evidence; regenerate fixture/new run; operational recovery deferred K0b |
| Control/artifact ownership overlaps | only control requests cross boundary; artifact/event plane alone writes artifact/event records |
| N/A binary claim becomes stale | any BLOB/non-UTF8/raw-byte capability invalidates approval before implementation |
| Provider/model profile unavailable | typed `failed_invocation`; no fallback model without a new pinned scope |

There are no new content decisions requested by this plan. Owner disposition is required only after independent review, on this exact plan hash together with the other two plans and the implementation scope in the common envelope. Deferred capabilities are checkpoint publication, clone-only restore, crash resume/reconciliation, graceful abort, general retry/lease/budget FSM, Alpha event families, projections, product roots/effects, research import, full replay, and all production layer contracts.

