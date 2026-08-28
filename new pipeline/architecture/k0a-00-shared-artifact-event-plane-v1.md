# K0a-00 Shared Artifact/Event Plane Architecture Plan

| Field | Value |
|---|---|
| Plan ID | `k0a-00-shared-artifact-event-plane` |
| Version | `1.1.0` |
| Status | `review_candidate` |
| Work item / phase | `K0a-00` / `K0a` (`2.0a`) |
| Architecture owner | `W1 Kernel / shared artifact-event plane` |
| Complexity tier | `shared_plane`, at most 800 non-empty full-file lines |
| Exact hash binding | complete-file SHA-256 is recorded outside these bytes in review/evidence records to avoid self-reference |

## Scope envelope

This is one shared-plane plan. It is bound to `k0a-00-bootstrap-f00-scope-v1` (`new pipeline/architecture/k0a-00-scope-envelope-v1.yaml`, version `1.0.0`, SHA-256 `0ecfb4009935e362a39c5e037abd1b8692da1c82ffc142b6bb2426e2022cd216`). It neither combines nor approves the shared control plane or S.

| Required field | Bound value |
|---|---|
| Phase/package | `K0a-00`; architecture planning for `K0a/2.0a-bootstrap-kernel` |
| Profiles/scenarios | disposable synthetic fixture; `F00` only |
| Current producers | deterministic harness acting on validated proposals from S0, synthetic Layer0, and fixture worker |
| Current route | five F00 events and one textual artifact version ending at fixture `bootstrap_sink` plus CLI readback |
| Current artifact/event types | `bootstrap.synthetic_result`; `command.received`, `run.started`, `artifact.version_created`, `handoff.ready`, `run.completed` |
| Downstream boundary | terminal fixture sink/readback only; no project projection, product consumer, or readiness claim |

Explicit exclusions: operational K0b hardening; checkpoint publisher/clone-only recovery; full Alpha event profile; production/project effects; legacy research import; full P/R/E/G/A/H/T/I/Q/M contracts; K0a-01/K0a-02 implementation during K0a-00; projection outbox; crash reconciliation/resume/abort; leases/general retries; side-effect intents; full replay; binary payload; and release/Alpha-0/product claims.

Deferred interfaces are versioned artifact/event schema bindings, `artifact_version_id`, causation/correlation, validated atomic-publication requests, subscriber snapshots, delivery terminal result, and replay-point references. Only an explicit hash-bound owner approval of all three reviewed plans may activate their narrow K0a implementation scope.

## 1. Purpose, boundaries, non-goals, and applicability

This plane owns the canonical F00 artifact/event data model and deterministic persistence semantics in the disposable fixture active SQLite DB. It validates and stores immutable artifact versions, public events, subscriber snapshots/delivery results, lineage, and the atomic publication unit that prevents an artifact without its events or an event pointing to a missing artifact.

It does not own run scheduling, model calls, semantic routing, prompt content, product files, key-decision projections, checkpoint publication, or production schemas. It applies only to F00 on the D0-06 fixture binding and cannot be generalized to Alpha or product routes without K0b/later delta approval.

The plan itself performs no migration/schema/contract implementation. After owner approval, it bounds only the artifact/event portions of K0a-01/K0a-02 and F00 evidence in K0a-03.

## 2. Dispatcher, deterministic harness, and worker boundary

Reasoning actors never write this plane. S0 and synthetic Layer0 may return route proposals containing existing refs; the fixture worker may return a textual artifact proposal plus allowed event proposals. The control harness checks invocation identity and submits a typed publication request.

The artifact/event harness alone validates schema/version/hash profile, ownership, causation, input freshness, idempotency key, state revision, terminal policy, and transaction invariants. It writes SQLite through a short local transaction and returns IDs/status. The bootstrap sink is deterministic and may acknowledge only `handoff.ready` for the exact F00 profile.

No worker can choose a schema, event type, subscriber, delivery state, artifact owner, hash profile, or storage encoding. Any extra field interpreted as such is untrusted output and causes validation failure.

## 3. State machine, invariants, and terminal states

Artifact proposal states are `proposed -> validated -> persisted`. Validation failure is terminal `rejected`; transaction failure is terminal `rolled_back` after proving no row from the unit is visible. Persisted versions are immutable.

Event states are `proposed -> validated -> appended -> terminal_or_delivered`. F00 has no retry/dead-letter loop. Delivery states are `pending -> accepted_terminal` for the fixture sink or `rejected_terminal` on schema/profile/ref mismatch. `run.completed` may be appended only after accepted terminal handoff and successful consistency checks.

Invariants:

- every artifact has a stable artifact identity and immutable unique version ID;
- every external reference uses artifact version ID; digest is verification metadata, not identity;
- worker publication creates the artifact version, `artifact.version_created`, `handoff.ready`, and their subscriber snapshots in one transaction;
- event causation and referenced rows exist before commit;
- all five event types are pinned to the F00 schema/profile and cannot be extended at runtime;
- terminal sink acceptance is fixture/profile-specific and cannot be reused outside F00;
- no mutable current pointer can conceal version history.

## 4. Input events, guards, routing, fan-out, barriers, and fast paths

Inputs are validated control-plane requests, not arbitrary SQL or agent text.

| Event/request | Guards | Route |
|---|---|---|
| `command.received` append | pinned run/contract; normalized command; unique idempotency key | subscriber snapshot names S0 control delivery |
| `run.started` append | command exists; run binding complete; state `created` | terminal audit/readback policy for F00 |
| worker publication request | valid current invocation/result; textual artifact schema; expected state revision | atomic artifact version + two events |
| `artifact.version_created` | exact new version ID/owner/hash/lineage | terminal `bootstrap_readback` |
| `handoff.ready` | exact same artifact version and causation chain | one subscriber: `bootstrap_sink` |
| `run.completed` append | sink accepted; all refs/deliveries consistent; no failure | terminal `bootstrap_readback` |

There is no fan-out, quorum, retry, dead-letter, cross-layer route, or semantic fast path. The deterministic sink/readback paths are not dispatcher fast paths and make no model call. Unknown event types/subscribers/guards fail before transaction.

Routing section sub-budget: at most 85 non-empty lines.

## 5. Output events, subscribers, terminal policy, and cross-layer contracts

The exact F00 catalog and terminal behavior are:

| Event | Semantic initiator | Subscriber or terminal policy | Required result |
|---|---|---|---|
| `command.received` | CLI/operator command | S0 through control harness | validated route attempt or typed run failure |
| `run.started` | control harness | `bootstrap_readback` terminal | visible in inspect output |
| `artifact.version_created` | fixture worker proposal | `bootstrap_readback` terminal | exact version visible and hash-valid |
| `handoff.ready` | fixture worker proposal | `bootstrap_sink` terminal | accepted only for exact fixture F00 profile |
| `run.completed` | control harness after sink acceptance | `bootstrap_readback` terminal | completed graph visible in inspect output |

`bootstrap_readback` is a terminal evidence policy, not a production subscriber. `bootstrap_sink` does not transform content or publish another artifact. No emitted event is dangling.

Cross-layer contracts are N/A in current scope. Synthetic Layer0 is not a production layer and the terminal handoff cannot escape the fixture. Later event subscribers require forward-only registry versions and delta review.

## 6. Artifact types, ownership, versioning, lineage, and key decisions

The sole content type is `bootstrap.synthetic_result`, encoded as NFC UTF-8 `application/json` or `text/plain` under a pinned textual schema; exact selection is fixed by K0a-02 contract, not model output. Its exact logical owner identifier is `fixture.bootstrap_worker`. The invoked fixture worker is the semantic producer acting for that owner, while the artifact/event harness is persistence authority. Neither S0 nor Layer0 owns or edits content, and neither the model nor publication caller can replace the owner identifier.

Identity fields are stable artifact ID plus immutable artifact-version ID. Each version records logical owner `fixture.bootstrap_worker`, producer invocation, parent input refs, media type/encoding, schema identity/hash, complete content SHA-256/profile, created event, and causation/correlation. F00 creates one version and no supersession/invalidation edge. The K0a-02 positive contract fixes this owner value; a missing, alternate, S0, Layer0, harness, or model-selected owner fails the wrong-owner test before transaction.

Lineage is `fixture input version -> command/run -> S0/Layer0/worker invocations -> bootstrap.synthetic_result version -> artifact.version_created/handoff.ready -> sink delivery -> run.completed`. CLI readback must traverse this exact graph.

Key-decision projections are N/A: the artifact is synthetic, not an owner decision; projection request/written/failed events and YAML+Markdown outbox are K0b scope.

## 7. Context/query allowlists, trust, provenance, and prompt injection

Reasoning-context assembly is owned by the control plane; this plane exposes only bounded queries by exact run/invocation/event/artifact-version ID. No free SQL, full-table dump, path-based implicit artifact lookup, or hash-as-identity query is available to an agent.

Persisted artifact content and model output are untrusted data. They cannot declare executable commands, event types, subscribers, capabilities, roots, schema IDs, media types, or approvals. The publication request carries those trusted values from pinned contracts, and the validator compares rather than accepts model-supplied authority.

Provenance includes fixture spec/commit/tree, input artifact version, producing invocation, exact context/result refs, contract/schema/hash profile, causation, and timestamps. Secret/PII scan must pass before persistence; because F00 has no secret scope, a match blocks the whole publication.

## 8. Current roster, inputs, outputs, capabilities, and stop conditions

There are no artifact/event-plane LLM workers. Current deterministic components are:

| Component | Input | Output | Capability | Stop condition |
|---|---|---|---|---|
| schema/ownership validator | typed request and pinned schemas | validated request or finding | read registry; no DB write | unknown/malformed/unauthorized value |
| transaction writer | validated request and expected DB revision | committed IDs or rolled-back error | one short active-fixture SQLite write | stale state, constraint/I/O failure |
| subscription resolver | pinned F00 registry and event | immutable subscriber snapshot | deterministic registry read | zero/multiple unexpected routes |
| bootstrap sink | exact `handoff.ready` delivery | accepted terminal delivery | read referenced textual version | wrong profile/type/ref/hash |
| inspect reader | exact run ID | bounded lifecycle/telemetry readback | read-only DB query | missing/inconsistent graph |

Deferred stable interfaces only: Alpha subscription compiler, delivery retry/dead-letter, invalidation/supersession, projection outbox, side-effect records, BLOB/incremental I/O, checkpoint publisher, and recovery/reconciliation.

Roster section sub-budget: at most 45 non-empty lines.

## 9. Failure, revision ownership, invalidation, replay, recovery, and abort

| Failure | Deterministic outcome / owner |
|---|---|
| schema/media/owner/ref violation | reject before write; W1 contract/schema finding |
| unregistered event/subscriber/terminal policy | reject before write; W1 registry finding |
| stale revision or duplicate idempotency conflict | no new rows; return existing exact result or fail inconsistency |
| constraint/disk/transaction failure | rollback entire publication; `failed_persistence` to control plane |
| sink hash/content/profile mismatch | `rejected_terminal`; block completion; artifact/event owner finding |
| CLI readback graph mismatch | block completion/evidence; W3 verification finding |

F00 has no artifact revision/supersession/invalidation route. A defect in synthetic output is a failed run; a fixed prompt/contract uses a new Pipeline commit and new disposable run. No row is edited to repair evidence.

Minimal replay is read-only traversal of recorded version/event/delivery/context/result refs in the same active DB. The plane provides enough exact records for later forensic semantics but K0a does not restore, re-dispatch, reconcile a crash, or claim clone-only replay.

Operational recovery/abort are N/A by explicit K0a exclusion. On interruption or uncertain commit, no blind retry is allowed: SQLite atomic visibility is inspected; if outcome cannot be proven, preserve the disposable DB as evidence and start a fresh materialization/run. K0b adds reconciliation and public abort events.

Failure/recovery section sub-budget: at most 75 non-empty lines.

## 10. HITL, autonomy, approvals, and dialogue

All plane actions in F00 are deterministic Auto operations under the approved run. There is no human dialogue, approval event, risk acceptance, or in-run decision. The plane cannot parse a model/text/file assertion as human authorization.

Owner approval of this exact architecture package occurs before implementation and is stored later in Pipeline Git, not the fixture DB by this planning step. Creative Dialogue is N/A because no human-facing content is elicited or synthesized.

## 11. Tools, side effects, security, egress, and repositories

The writer opens only the active SQLite DB below a newly created disposable F00 run root. The canonical fixture checkout is read-only and is never modified. Pipeline Git is read-only during runtime. Swarm and legacy research capabilities are absent.

No network egress is performed by this plane. SQLite/library calls use pinned harness code; agents receive no database connection or filesystem tool. The actual change set is bounded to the exact disposable runtime/temp paths. Symlink/junction escape, attached databases, extension loading, triggers from untrusted SQL, arbitrary pragmas, and content-derived file paths are denied.

The only side effect is reversible/disposable local DB persistence. Git commit/push, projection files, checkpoint replacement, external mutation, package hooks, shell execution, and secrets are out of scope.

## 12. Context scale, sharding, invocation budget, and human attention

F00 contains one small textual artifact and five events. Queries are exact-ID bounded; no sharding, RAG, sampling, cache, large repository inventory, or fallback profile applies. Object/event/context size limits must be fixed by the future K0a contract before write; unknown size is fail-closed.

Budget authority: `k0a-00-budget-reference-v1`, SHA-256 `eab713455e593d556ee4c52668fe202649f969d79a6ebfa17ad10b237b4503f9`. The shared plan-production package `K0a-plan-bootstrap` is light at 6 nominal/18 worst-case calls and has standard human attention 1/2 sessions, 1/3 decisions, 20/60 active minutes, 30-minute maximum, batchable. This plan contributes one author/reviewer pair nominal and up to two bounded revision pairs; it does not create a duplicate package.

The separate, not-yet-authorized `K0a-runtime-F00` package is light at 3/6 calls and zero human sessions/decisions/minutes. This plane has zero LLM calls: its validator, writer, resolver, sink, and inspect reader are deterministic. Runtime calls remain attributed once to S0, synthetic Layer0, and the fixture worker.

## 13. Binary payload budget or proved N/A

`N/A`, after a non-automatic applicability check. This plane is capable of persistence generally, so the K0a contract must make the proof executable: accepted F00 media types are textual UTF-8 only; content must decode strictly and pass its textual schema; SQLite BLOB storage, non-UTF8 bytes, image/audio/video/archive/font/executable media, opaque tool output, and existing binary artifact refs are all rejected before transaction.

Thus it creates or first persists zero binary objects and zero binary bytes nominal/worst-case, exactly matching the approved K0a forecast. Any future BLOB column use, opaque byte field, non-text media class, or reference to binary payload invalidates this N/A. If a later plan merely references producer-budgeted binary content, it may use only `artifact_version_id` and must bind that producer budget; current F00 has no such reference.

## 14. Downstream consumers and actual consumption

`artifact.version_created` is consumed by bounded CLI readback; `handoff.ready` is consumed by the deterministic fixture bootstrap sink; `run.started` and `run.completed` are terminal readback evidence. The control plane consumes the sink result and exact persisted refs to decide completion.

Actual consumption requires a delivery/readback record naming run, consumer policy, exact artifact version/event IDs, fields read, validation outcome, and evidence refs. A stored artifact alone or worker self-report is insufficient. No real downstream layer or product consumer exists in K0a.

## 15. Structural, contract, behavioral, fixture, and real-project scenarios

- Structural: one artifact type/five events; unique IDs; declared schema, producer, subscriber/terminal policy, owner, causation, and no dangling route.
- Contract: accept only logical owner `fixture.bootstrap_worker`; reject missing/alternate/model-selected owner, hash-as-identity, wrong media/schema/profile, missing consumer, extra event/subscriber, and non-text/BLOB payload.
- Behavioral: atomic all-or-none worker publication; idempotent repeated request returns the same outcome or explicit conflict; sink cannot alter content.
- Fixture F00: one textual version, its two publication events, sink acceptance, completion, and CLI traversal of the full lineage.
- Fault injection: fail between validation/write/commit and prove no partial rows; corrupt ref/hash and prove completion blocked.
- Security negatives: secret/PII match, write to canonical fixture or another forbidden root, `..` path traversal, symlink/junction escape, SQLite `ATTACH`, extension loading, untrusted trigger/pragma, and a content-derived path each fail with `blocked_policy` or `rejected` from the named validator/transaction writer before forbidden or partial write.
- Real project: N/A because capabilities and consumers are fixture-only and no product readiness claim is allowed.

## 16. Evidence package and readiness criteria

Evidence binds plan/contract/schema/hash-profile/Pipeline and fixture identities; DB migration hash; exact SQL transaction result; logical owner `fixture.bootstrap_worker` and positive/wrong-owner results; artifact/version/content hash/media; five event IDs and payload hashes; subscriber snapshots/delivery terminal results; causation lineage; idempotency/state revision; negative BLOB/event/subscriber cases; sink acceptance; and CLI readback query/result. Security evidence separately names the enforcing validator or transaction writer, expected typed failure, resolved canonical target, and before/after DB/filesystem proof of zero forbidden or partial writes for secret/PII, forbidden-root, traversal, symlink/junction, `ATTACH`, extension, trigger/pragma, and content-derived-path attempts.

Readiness for K0a requires atomicity, immutability, exact version references, complete reachability, textual-only enforcement, terminal sink/readback, and no forbidden paths/effects. Failure evidence is preserved and classified; it cannot be replaced by prose.

Complexity evidence records the full non-empty line count and routing/roster/failure counts against `800/85/45/75` caps.

## 17. Old-pipeline migration note

Minimal read-only sources were the parent architecture migration analysis and `old pipeline/J. Implementation/J0. Dispatcher.md` (SHA-256 `d435daba6f83156d9919c6f2368aaf216e2f4a6214d0f8f260db30fc40932d74`). Retained ideas are immutable attempt/result identities, explicit artifact contracts, evidence before completion, and dispatcher ownership of orchestration rather than worker self-certification.

They are rewritten from many file artifacts and manually synchronized status into normalized SQLite versions/events/deliveries with atomic constraints and version-ID lineage. Retired are `task_results` path conventions, filesystem files as runtime authority, implicit handoff, PR/CI/product evidence, and J-specific task schemas. New tests cover atomic artifact+events, consumer reachability, identity/hash separation, textual-only persistence, and sink/readback consistency.

No old schema, runtime file, prompt, task artifact, or legacy product payload is imported.

## 18. Risks, open decisions, and deferred capabilities

| Item | Status / control |
|---|---|
| Text/binary ambiguity could invalidate N/A | strict UTF-8 textual media allowlist plus BLOB/non-text negative tests |
| Event terminal policy could be mistaken for real consumption | fixture-only profile marker and forbidden reuse outside F00 |
| Atomicity could omit delivery snapshot | transaction contract includes artifact, two events, and subscriber snapshots |
| Duplicate request could fork identity | exact idempotency/state-revision rules and conflict evidence |
| Schema design could overfit Alpha target | only F00 fields implemented; forward-only delta in K0b |

No new substantive owner decision is introduced. After independent review, owner approval is requested on the exact plan hash and common implementation scope only. Deferred capabilities include binary storage, projections/outbox, checkpoint/recovery, abort/retry/dead-letter, leases, side-effect records, Alpha/domain events, artifact revision/invalidation, product roots, and real consumers.
