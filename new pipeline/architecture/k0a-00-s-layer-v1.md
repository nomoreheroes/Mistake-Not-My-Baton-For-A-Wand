# K0a-00 S Layer Architecture Plan

| Field | Value |
|---|---|
| Plan ID | `k0a-00-s-layer` |
| Version | `1.2.0` |
| Status | `review_candidate` |
| Work item / phase | `K0a-00` / `K0a` (`2.0a`) |
| Layer owner | `S / S0` |
| Complexity tier | `narrow`, at most 500 non-empty full-file lines |
| Exact hash binding | complete-file SHA-256 is recorded outside these bytes in review/evidence records to avoid self-reference |

## Scope envelope

This is the exact phase-scoped plan for S only. It binds `k0a-00-bootstrap-f00-scope-v1` (`new pipeline/architecture/k0a-00-scope-envelope-v1.yaml`, version `1.0.0`, SHA-256 `0ecfb4009935e362a39c5e037abd1b8692da1c82ffc142b6bb2426e2022cd216`) and does not approve either shared plane or the synthetic layer.

| Required field | Bound value |
|---|---|
| Phase/package | `K0a-00`; architecture planning for `K0a/2.0a-bootstrap-kernel` |
| Profiles/scenarios | disposable synthetic fixture; `F00` only |
| Current S roster | one `S0`; no S workers |
| Current S route | consume `command.received`, choose the only pinned synthetic Layer0 route, return a validated route proposal to the harness |
| Current S artifact/event types | owns no artifact or public event; reads event/ref metadata and returns a control proposal |
| Downstream boundary | harness invokes synthetic Layer0; S0 never directly calls it and never reaches a production layer/project |

Explicit exclusions are operational K0b S hardening; project lease and multi-run scheduling; budget/escalation FSM; checkpoint publisher/clone-only recovery; full Alpha events; product/project effects; research import; full P/R/E/G/A/H/T/I/Q/M contracts; K0a-01/K0a-02 implementation during this planning package; cross-layer invalidation; HITL/dialogue; crash resume/abort; and all release/Alpha-0/product claims.

The only deferred stable output is `validated_route_proposal` for the harness. K0b may delta-approve non-nominal routing and operational recovery after F00. No S implementation begins before explicit owner approval of all three exact plan versions/hashes and requested scope.

## 1. Purpose, boundaries, non-goals, and applicability

S0 is the sole command-facing reasoning dispatcher. In F00 it proves only that a real LLM can recognize one pinned synthetic command/profile and select one permitted synthetic Layer0 route without changing policy. It does not create product content, choose product architecture, persist records, run tools, or coordinate real layers.

The plan applies only to the D0-06 disposable fixture and F00. It is not a target S architecture: cross-layer queues, project leases, HITL, resume/reconciliation, applicability, budgets, invalidation, parallelism, product aliases, and operational guards remain deferred.

This document authorizes no implementation. Once owner-approved, it bounds the S0 portion of K0a-02 and its F00 evidence in K0a-03.

## 2. Dispatcher, deterministic harness, and worker boundary

S0 receives a harness-rendered envelope for one `command.received` delivery. Its sole raw schema type is `s0_route_proposal`, which must name exactly the pinned synthetic Layer0 contract. Semantic blockers, abstentions, and alternate outcomes are not valid outputs in F00; the harness rejects them as `failed_validation`. After schema/semantic validation, the harness persists the canonical `validated_route_proposal`. The logical success state is `route_selected`; it is a state name, not a second output type. S0 cannot invoke Layer0, open SQLite, read files, run tools, mutate Git, select provider/model/capabilities, or add an event/subscriber.

The deterministic harness owns command parsing, roots/pins, context assembly, schema validation, invocation creation, model call, identity echo, state transition, and subsequent Layer0 invocation. Synthetic Layer0 and fixture worker are downstream actors owned by their future fixture contract, not S workers. Their free-form outputs are never included in S0 context.

There is no S worker roster in K0a. Adding a planner, status summarizer, approval broker, recovery agent, or any other S role requires a new plan version.

## 3. State machine, invariants, and terminal states

Before S0 exists, the harness moves the delivery through `pending_preflight -> preflight_passed | rejected_pre_invocation`. A rejected preflight is emitted and persisted only by the harness as run terminal `blocked_input` or `blocked_policy`; no S0 invocation/state/result exists. After preflight passes, delivery-level S0 states are `not_invoked -> evaluating_attempt_1 -> route_selected | retry_pending | failed_validation | failed_invocation`; the sole retry path is `retry_pending -> evaluating_attempt_2 -> route_selected | failed_validation | failed_invocation`. The harness alone owns these transitions. A malformed/forbidden raw response becomes `failed_validation`; a non-retriable provider failure or exhausted transient retry becomes `failed_invocation`. An attempt-1 failure is evidence but is not run-terminal when the exact `retry_pending` transition is taken.

Guards precede the model call. A valid result must echo invocation/run/trigger identities, name the exact one allowed route, cite the command event, contain no additional action, and satisfy the result schema. Once accepted, the route decision is immutable for that attempt.

Invariants:

- one delivered command produces at most one accepted semantic result and one accepted route proposal, with at most two physical S0 invocation attempts carrying distinct invocation/attempt IDs;
- S0 cannot change pins, roots, provider/model, context, schema, event catalog, capability, or terminal policy;
- S0 cannot manufacture an approval or claim that F00/product/Alpha has passed;
- ambiguous/unknown input does not fall back to a guessed route;
- a failed S0 attempt never schedules Layer0.

## 4. Input events, guards, routing, fan-out, barriers, and fast paths

The only input event is `command.received`. Its allowed semantic form is a normalized F00 bootstrap command carrying exact fixture/run/contract refs. Required guards are: exact event/profile/schema; current run state; D0-06 fixture binding; accepted root/capability proof; context size bound; one declared route; and no prior accepted S0 route for the delivery.

Routing table:

| Condition | S0 result | Harness action |
|---|---|---|
| exact F00 command/profile and one allowed route | model call exists; S0 returns `s0_route_proposal` | validate into `validated_route_proposal`, persist, create Layer0 invocation |
| missing/stale/malformed identity or prerequisite | no model call and no S0 state/result | harness persists `rejected_pre_invocation` / `blocked_input` |
| preflight capability/root/event/schema conflict | no model call and no S0 state/result | harness persists `rejected_pre_invocation` / `blocked_policy` |
| unknown/ambiguous/extra route/action, semantic blocker/abstention, or malformed S0 result | model call exists but raw result is rejected | harness persists `failed_validation`; no fallback/retry |
| transient provider failure before an accepted response | first model call exists; no S0 semantic result | one bounded same-run adapter retry under section 9, otherwise `failed_invocation` |

Fan-out and barriers are N/A because exactly one Layer0 route exists. Compiled fast path is forbidden for F00: the real S0 invocation is mandatory. K0b may later prove an exact compiled nominal route but cannot rewrite F00 evidence.

Routing section sub-budget: at most 75 non-empty lines.

## 5. Output events, subscribers, terminal policy, and cross-layer contracts

S0 emits no public event in K0a. Its sole raw output type is `s0_route_proposal`. Only a valid route outcome becomes exactly one persisted `validated_route_proposal`, after which the harness schedules synthetic Layer0 under the original command causation. Every other raw outcome is rejected and schedules nothing. `route_selected` names the logical S0 state reached after route persistence; implementation must not create competing success/blocker schemas.

Because there is no S-authored event, subscriber/terminal-policy ownership for the five F00 events belongs to the shared artifact/event plan. S0 consumes only `command.received`; `handoff.ready` terminates at the fixture sink and never returns to S0 as a product handoff.

Production cross-layer contracts are N/A: synthetic Layer0 is fixture-only, and no P/R/E/G/A/H/T/I/Q/M dispatcher exists in this scope. The stable future boundary is a harness-validated route proposal containing contract ID/version/hash and triggering event/ref IDs.

## 6. Artifact types, ownership, versioning, lineage, and key decisions

S owns no content artifact, artifact version, event row, or key-decision projection. S0 reads only reference metadata and returns a route proposal stored by the control plane as an immutable route-decision record.

Lineage is `command.received -> S0 invocation -> validated route proposal -> synthetic Layer0 invocation`. Downstream worker artifact lineage continues under the shared artifact/event plan but is outside S ownership. Digest never replaces an artifact/invocation/event identity.

Key-decision YAML+Markdown projections are N/A because route selection is predetermined by the approved fixture contract and contains no owner/product decision.

## 7. Context/query allowlists, trust, provenance, and prompt injection

S0 context allowlist is limited to: normalized command intent; event/run/invocation IDs; F00 profile; exact fixture binding status; one allowed Layer0 contract identity/hash; allowed route/result enums and schema; and non-secret capability summary. It receives no repository files, artifact payload, arbitrary SQL query, other agent output, tool response, conversation transcript, Swarm/research content, or hidden author/reviewer context.

The command's user-controlled text is untrusted data after normalization. Embedded instructions cannot add routes, agents, events, tools, roots, network, approvals, or output fields. S0 must treat policy/contract blocks as authority and the command payload as data. The harness rejects any result that echoes an untrusted instruction as authority.

Provenance binds exact command bytes/hash, fixture/run/contract/prompt/model refs, ordered rendered context, and S0 response. Unknown or over-budget context blocks before invocation.

## 8. Current roster, inputs, outputs, capabilities, and stop conditions

| Role | Input | Output | Capability | Stop condition |
|---|---|---|---|---|
| `S0` | one validated `command.received` envelope | exact route proposal only | reasoning only; no tools/subagents/DB/files/network beyond harness-mediated model call | any ambiguity, blocker/abstention, policy conflict, schema mismatch, unknown route, or extra action |

S has zero workers. Synthetic Layer0 and fixture worker are downstream interface actors and are not counted as S roster. Current S roster count is one dispatcher, zero workers.

Deferred interfaces only: project alias resolver, status presenter, cross-layer queue/barriers, applicability/HITL broker, invalidation/replay coordinator, abort/recovery coordinator, project lease/scheduler, and budget escalation. Their prompts, state machines, and internal routes are intentionally not designed here.

Roster section sub-budget: at most 30 non-empty lines.

## 9. Failure, revision ownership, invalidation, replay, recovery, and abort

| Failure | F00 outcome / owner |
|---|---|
| missing/stale command or ref found preflight | harness emits/persists `rejected_pre_invocation` / `blocked_input`; no S0 invocation exists |
| policy/capability widening | result rejected; W1/S security finding; no downstream invocation |
| ambiguous/unknown/forbidden route | `failed_validation`; S plan/contract owner disposition required before rerun |
| malformed identity echo/schema | `failed_validation`; prompt/adapter evidence retained |
| transient provider failure before accepted response | harness records attempt failure; at most one pre-authorized adapter retry with new physical identity and same run/delivery/context/pins; after it, `failed_invocation` |
| later Layer0/worker/persistence failure | outside S ownership; run fails under owning plan and is not rerouted by S0 |

There is no artifact invalidation or revision loop in S scope. If S routing is defective, a new plan/contract/Pipeline version and fresh fixture run are required; the prior route record remains immutable.

The only retry trigger is adapter-classified `transient_unavailable_before_dispatch_ack` or `timeout_before_accepted_response`; validation, policy, blocker/abstention, partial-response ambiguity, and downstream failure never retry. When that trigger is recorded and no response was accepted, the deterministic harness automatically takes the single `retry_pending` transition; no new command or human trigger is required. Attempt 2 stays in the same run and command delivery, reuses byte-identical context/pins, has a new physical invocation/attempt ID, fences any late attempt-1 result, preserves attempt-1 evidence, and consumes the second S0 call already included in `K0a-runtime-F00` worst case. It needs no human decision, so runtime human attention remains zero.

Minimal replay is read-only retrieval of S0's exact before/after replay envelope and recorded response for diagnostic route comparison. S0 has no replay command and cannot re-invoke itself. Crash recovery/resume and operational abort are N/A by explicit K0a exclusion; an interrupted run remains non-complete for inspection and a new disposable run starts after evidence preservation. Such a new run is recovery evidence, not the budgeted same-run transient retry.

Failure/recovery section sub-budget: at most 60 non-empty lines.

## 10. HITL, autonomy, approvals, and dialogue

S0 performs one Auto reasoning action within the pre-approved F00 run. It does not request human input, choose risk/scope, interpret approval, access secrets, or authorize side effects. The runtime human-attention budget is zero.

Owner approval of this exact architecture package is a pre-implementation W0 action outside S runtime. Creative dialogue, factual elicitation, decision approval, session/round budgets, resume rules, and dialogue provenance are N/A because no human turn exists in F00.

## 11. Tools, side effects, security, egress, and repositories

S0 receives no tool capability, filesystem root, DB handle, shell, Git, network research, external mutation, secret, or subagent-dispatch tool. The harness mediates its sole egress through the exact pinned provider/model channel and supplies only the bounded context.

Pipeline and canonical fixture roots are read-only to the harness; the disposable runtime root is not exposed to S0. `projects/swarm` and `research/old-swarm` are inaccessible. S0 output cannot select paths or commands. No side-effect intent exists.

Any output suggesting a tool call, file path, new capability, direct Layer0 contact, alternate provider, product action, or legacy import is a forbidden extra action and blocks before downstream dispatch.

## 12. Context scale, sharding, invocation budget, and human attention

S0 context is a fixed small envelope for one event and one route. Sharding, RAG, sampling, caching, repository scans, dialogue fan-out, and alternate-model fallback profiles are N/A. The harness proves input/output token bounds against the pinned model; overflow does not truncate authority fields and instead blocks.

Budget authority is `k0a-00-budget-reference-v1`, SHA-256 `eab713455e593d556ee4c52668fe202649f969d79a6ebfa17ad10b237b4503f9`. Shared plan-production package `K0a-plan-bootstrap` remains one unique light package at 6 nominal/18 worst-case calls and standard human attention 1/2 sessions, 1/3 decisions, 20/60 minutes, 30-minute max, batchable. This exact plan accounts for one author/reviewer pair nominal and up to two bounded return pairs without inventing another package.

Separate unauthorized runtime package `K0a-runtime-F00` is light at 3/6 calls and zero human sessions/decisions/minutes. S contributes one nominal S0 call and at most two worst-case S0 physical calls: attempt 2 is allowed only by the section 9 transient-provider rule. Layer0 and worker calls are counted once/twice at their own equivalent boundaries. Any other S role, retry trigger, third attempt, new run presented as an in-run retry, or owner-mediated continuation exceeds the approved route and blocks.

## 13. Binary payload budget or proved N/A

`N/A`, proven under the exact gate rule. S0 has no persistence or payload API and its contract must prohibit binary fields. It receives and returns only bounded UTF-8 JSON control values and immutable IDs/refs. It cannot create, first persist, copy, embed, or transform artifact bytes.

If a future S route needs an existing binary artifact, the only permitted interface is `artifact_version_id` referring to a producer with an approved binary budget; F00 references none. Therefore S creates zero binary objects/bytes nominal and worst-case, matching the approved K0a forecast. Any binary field or raw-byte capability invalidates the N/A and the plan approval.

## 14. Downstream consumers and actual consumption

The deterministic control harness is the sole consumer of raw `s0_route_proposal`. It validates exact contract/run/event/route fields and records `accepted | rejected`; accepted output becomes `validated_route_proposal`. That record is actually consumed only when the harness creates the matching synthetic Layer0 invocation; both records must share the causation and contract hashes.

S K0a readiness requires that exact consumption evidence plus the downstream F00 terminal sink/readback. S0 self-report, a valid-looking route string, or a scheduled-but-not-created invocation is insufficient. No product layer consumes an S artifact because S creates none.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: one S0, zero S workers, one input event, one route schema, no public S output event, exact boundary refs.
- Contract: accept only raw type `s0_route_proposal` with the pinned Layer0 contract/route and required identity echo; persist success only as `validated_route_proposal`; reject missing/extra/unknown route/action/capability.
- Behavioral: real S0 selects the allowed route for the synthetic command; adversarial command instructions cannot widen authority; ambiguity fails closed.
- Fixture F00: accepted S0 proposal is consumed by creation of the exact Layer0 invocation and participates in terminal artifact/sink/readback evidence.
- Negative fixture: wrong profile/pin/root status and stale command prove pre-invocation harness rejection with no S0 state; over-bound context, alternate route, tool request, and forged approval all block before Layer0; transient pre-ack/response timeout permits exactly one byte-identical same-run retry while validation/policy/partial-response cases permit none.
- Real project: N/A; S0 has no product root or production route and F00 cannot establish real-project readiness.

## 16. Evidence package and readiness criteria

Evidence binds the exact S plan/contract/prompt/Pipeline hashes; fixture identity; command event; preflight state/result and proof that rejected preflight created no S0 state; run/S0 physical invocation/attempt IDs; before/after replay refs; ordered context/result refs; provider/model/parameters/usage; raw S0 result with its accepted/rejected validation disposition; accepted `validated_route_proposal` where present; created Layer0 invocation; retry trigger, byte-identical inputs, new identity, late-result fence, and attempt count where applicable; negative cases; and downstream terminal F00 refs.

Architecture readiness means the independent plan review passes and the owner later approves this exact hash/scope. Fixture readiness later requires a real S0 call, valid route consumption, no forbidden action, full raw telemetry, and successful whole F00. It does not grant Alpha-0/product status.

Complexity evidence records full non-empty lines and routing/roster/failure counts against `500/75/30/60` caps.

## 17. Old-pipeline migration note

Read-only migration input was restricted to the parent architecture and `old pipeline/J. Implementation/J0. Dispatcher.md` (SHA-256 `d435daba6f83156d9919c6f2368aaf216e2f4a6214d0f8f260db30fc40932d74`). Retained ideas are a single dispatcher entrypoint, explicit next-step selection, typed worker result contract, identity/attempt echo, and a dispatcher that does not author worker content.

They are rewritten so S0 proposes only semantic routing while deterministic harness owns state, invocation, DB, validation, and delivery. Retired are J-specific task/worker chains, filesystem runtime authority, direct subagent orchestration, per-subagent blanket human approval, Git/PR/CI duties, and manual resume as normal routing. New tests cover the one-route guard, no direct handoff/tool access, forged approval rejection, route consumption, and exact replay-envelope evidence.

No legacy prompt body, J task schema, runtime file, product code, or research payload is imported.

## 18. Risks, open decisions, and deferred capabilities

| Item | Status / control |
|---|---|
| One-route F00 may overstate general dispatcher quality | explicit smoke-only claim; HYP-DISPATCH-01/F15 remains K0b gate |
| S0 may add persuasive but forbidden actions | closed result schema and reject-extra-fields/semantic assertions |
| Retry could silently inflate budget | exactly one automatic deterministic adapter retry is allowed only for the two named pre-acceptance triggers, inside the predeclared runtime worst case and with a new invocation identity |
| S/control ownership may blur | S0 only proposes semantic route; harness alone persists/schedules |
| Future product alias could expose wrong root | product alias/root resolution excluded and requires K0b/later delta plan |

There is no new substantive owner decision beyond approving or changing the exact reviewed plan/scope. Deferred capabilities are multi-route/cross-layer scheduling, fan-out/barriers, applicability, HITL/dialogue, leases, budget ledger/escalation, invalidation/replay coordination, recovery/abort, status UX, product aliases/roots, research import, Alpha events, and every production layer contract.
