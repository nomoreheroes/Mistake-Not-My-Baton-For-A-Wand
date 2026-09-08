# K0b-01 Alpha Foundation Planning Package v1.1

| Field | Value |
|---|---|
| Work item | `K0b-01` |
| Version | `1.1.0` |
| Status | `review_candidate`; planning authority only |
| Scope | Alpha forward migration, registry/routing and resource-budget compilers, remaining minimal Alpha events |
| Runtime model calls | `0/0` |
| Plan-review model calls | `2 nominal / 4 worst-case`, manual VSCode UI only, not dispatched by this plan |

## 1. Revision contract and authority boundary

This file is the v1.1 normative revision overlay for `new pipeline/architecture/k0b-01-planning-package-v1.md` at complete-file SHA-256 `028aa3e3667ff55f92a732d3b2424c704bdb0eaa81268a49c7505cfaa9a2e85f`. All non-conflicting v1 requirements remain incorporated by that exact hash. This v1.1 file supersedes v1 only for the decisions made explicit below: the four-table migration rebuild closure, 21 separate event schemas, two compiler receipts plus an aggregate manifest, independent reference vectors/oracle, the two-stream review topology, and treatment of the unapproved engineering draft.

Authority is limited to planning and preparation of two review inputs. It does not authorize implementation, execution or import of draft code, database mutation, runtime activation, physical model calls, review dispatch, provider API use, checkpoint/projection publication, or a readiness claim.

Exact controlling records are:

- final K0b-00 disposition: `new pipeline/decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml`, SHA-256 `544a6160fc27be348794179f44b44080b87bf3f53c0dd1b66baf9c7d1a40fe9d`;
- v1.1 owner direction: `new pipeline/decisions/k0b-01-plan-v1.1-owner-direction-v1.yaml`, SHA-256 `4ce0f4dd6b776cf55c238a8b6268e89143e49173d5da926c0d2cd1ca6c555c39`;
- frozen-draft record: `new pipeline/evidence/k0b-01-unapproved-engineering-draft-freeze-v1.yaml`, SHA-256 `7f29f002e794bfc61e4f6daa610a32c0b5f4219d18291c63df400a9706b01f66`;
- review-budget supplement: `new pipeline/evidence/k0b-01-plan-v1.1-review-budget-supplement-v1.yaml`, SHA-256 `b79adb397cedccf5a72ea6d78e2d4a3c87cab977cf9b1c53c64c97470a02f217`.

The 18 frozen files listed in the freeze record are preserved as non-authoritative engineering history. They are not plan outputs, conformance evidence, review truth, or an implementation starting point until a later explicit implementation authority independently revalidates every byte against the reviewed plan.

## 2. Exact scope and boundaries

After a separate implementation disposition, K0b-01 may implement only:

1. The exact schema-v3 to schema-v4 forward migration with the four-table dependency closure in section 3.
2. Closed contracts and registry inputs for exactly 21 minimal Alpha event types.
3. A deterministic registry/routing compiler and its typed receipt.
4. A deterministic resource-budget compiler, fail-closed binary-budget validator, and typed receipt.
5. One aggregate compiled-output manifest binding both receipts and all eight output families.
6. Temporary-database and synthetic-record tests, including a test oracle independent from production compiler helpers.
7. Deterministic validation evidence without runtime or readiness claims.

K0b-02 retains projection outbox, YAML/Markdown pair rendering, tracked checkpoint publication, replay materialization, phase-seal persistence/execution, and crash reconciliation. K0b-03/K0b-04 retain execution, prompts, model dispatch, provider interaction, and runtime activation. No K0a or K0b-00 hash-bound byte may be edited.

The canonical fixture, `research/old-swarm`, and `projects/swarm` are prohibited inputs and targets. Tests must generate disposable databases and synthetic records from allowed migration/contract bytes only.

## 3. Forward migration: selected full dependency closure

The later `0004_k0b01.sql` design must rebuild exactly these existing CHECK-constrained tables as one coordinated closure: `runs`, `run_state_transitions`, `events`, and `event_deliveries`. It must not merely add definitions while leaving Alpha rows impossible, and it must not introduce parallel Alpha-only event tables.

The migration sequence is fail closed:

1. Require an explicit schema-v3 source database and an explicit new backup path. Reject canonical fixture, product, tracked checkpoint, existing-target, symlink/reparse escape, or in-place restore paths.
2. Before mutation, verify ordered v1-v3 migration identities and hashes, `user_version = 3`, expected schema fingerprint, `integrity_check`, `foreign_key_check`, and a canonical content digest covering every table, row, column, value, and ordered relationship.
3. Produce the backup at the verified new path; verify its byte/content identity and prove it can be opened independently before entering the rebuild transaction.
4. Begin one immediate transaction. Create v4 forms of the four tables with explicit final names staged safely; copy all historical rows without coercion or default substitution; preserve every F00 ID, profile, state, event type/version, subscriber, terminal policy, lineage link, revision, payload byte string, digest, timestamp, uniqueness relation, and row count.
5. Swap the closure without temporarily accepting invalid references. Recreate all indexes, UNIQUE constraints, CHECK constraints, self-references, and foreign keys with the same or stricter historical semantics plus only the approved Alpha vocabulary. No dependent table outside the selected closure may be silently rewritten.
6. Insert exactly one immutable v4 migration record, set `user_version = 4`, and verify final schema fingerprint, both SQLite integrity checks, per-table row counts, pre/post historical content digest, and exact F00 graph readback before commit.
7. Commit only after every verification passes. A second initialization must be a no-op after verifying the exact v4 migration identity/hash; changed, missing, extra, or reordered migration records block.

The rebuild must accommodate the Alpha profile and run-state vocabulary needed by the exact approved event graph while retaining byte-compatible F00 behavior. The K0b-01 reader upgrades exact v3 and accepts exact v4. Every K0a reader must reject v4 as newer/unsupported; no historical migration or K0a contract is edited to imitate backward compatibility.

Fault injection is mandatory at: before backup creation, after backup verification, before and after each of the four table-copy/swap boundaries, before the v4 migration-row insert, after that insert, and immediately before commit. Each fault must prove the live database is exactly pre-migration v3 or complete v4, never partial. Restore is tested only from the verified backup into a distinct new path; there is no down migration or destructive in-place restore.

The migration adds no emitter, consumer, dispatcher, prompt, checkpoint writer, projection writer, phase transition effect, or provider integration. Static Alpha records remain activation-gated.

## 4. Exactly 21 self-contained event schemas

The later implementation write set contains exactly one self-contained JSON Schema per event under `new pipeline/contracts/k0b01/events/`:

1. `command.received-v1.schema.json`
2. `run.started-v1.schema.json`
3. `artifact.version_created-v1.schema.json`
4. `handoff.ready-v1.schema.json`
5. `run.completed-v1.schema.json`
6. `run.blocked-v1.schema.json`
7. `run.abort_requested-v1.schema.json`
8. `run.aborted-v1.schema.json`
9. `artifact.published-v1.schema.json`
10. `projection.requested-v1.schema.json`
11. `projection.written-v1.schema.json`
12. `projection.failed-v1.schema.json`
13. `revision.requested-v1.schema.json`
14. `gate.passed-v1.schema.json`
15. `approval.requested-v1.schema.json`
16. `approval.granted-v1.schema.json`
17. `approval.rejected-v1.schema.json`
18. `error.schema_mismatch-v1.schema.json`
19. `error.tool_failure-v1.schema.json`
20. `error.security_policy-v1.schema.json`
21. `meta.incident_detected-v1.schema.json`

Each schema has its own stable `$id`, exact event type/version, required envelope and payload fields, field types/formats/enums, `additionalProperties: false` at every closed object boundary, and a complete-file SHA-256 registry pin. A file must validate independently without a shared local schema or external/network `$ref`; a dangling or path-sensitive reference blocks compilation. The five retained F00 types remain semantically and byte compatible for F00 records.

Every event registry entry binds the schema ID/hash, producer/bootstrap owner, allowed subscribers or exact terminal policy, fields read by each subscriber, activation owner/work item, replay rule, idempotency rule, and terminal disposition. The three error events terminate as `block_run_and_enqueue_human`; `meta.incident_detected` terminates as `persist_incident_and_enqueue_W5`. Static projection/checkpoint/abort interface declarations do not activate their later owners.

The event catalog rejects a twenty-second type, unknown field, undeclared producer/subscriber, missing field owner, dangling edge, dynamic subscription, direct actor-to-actor handoff, and any dialogue, lease/retry/dead-letter, budget-escalation, cache/scale, deferred, full-replay, or layer-domain expansion.

## 5. Compiler split, receipts, and aggregate manifest

The registry/routing compiler consumes only exact pinned schema and registry bytes. It verifies all 21 events, subscription/terminal reachability, the five S route classes, fixed F04 all-required fan-out, distinct F05 revision ownership, activation barriers, and checkpoint-phase membership. Its typed receipt binds input hashes, compiler identity/version/complete-file hash, canonicalization profile, output-family hashes, diagnostics, and pass/block result.

The resource-budget compiler independently consumes complete route/fan-out/retry/dialogue facts, per-role call classes, package identities, human-attention facts, replay/tool/side-effect facts, binary budgets, the base checkpoint policy, and the exact two-phase overlay. Missing data is not zero: absence requires an explicit bounded-zero proof. Its typed receipt binds the same provenance fields plus independently calculated calls, human attention, binary limits, publications, checkpoint bytes, phase packs, margins, and reference-equivalence results.

The later evidence paths are:

- `new pipeline/evidence/k0b-01-registry-routing-compiler-receipt-v1.yaml`;
- `new pipeline/evidence/k0b-01-resource-budget-compiler-receipt-v1.yaml`;
- `new pipeline/evidence/k0b-01-compiled-output-manifest-v1.yaml`.

The aggregate manifest binds both receipt hashes, both compiler hashes/versions, every source hash, the exact authorities in section 1, and exactly these eight output families:

1. `compiled_artifact_event_profile`
2. `compiled_event_reachability_graph`
3. `compiled_subscription_terminal_snapshot`
4. `compiled_s_route_table_v2`
5. `compiled_fanout_barrier_profile`
6. `compiled_resource_forecast`
7. `compiled_checkpoint_phase_partition_v1`
8. `compiled_checkpoint_publication_budget_v2`

All outputs use specified canonical ordering for maps, sets, nodes, edges, roles, phases, triggers, and packages. Identical input bytes produce byte-identical receipts, outputs, aggregate manifest, and digests regardless of time, locale, working directory, absolute path, or map insertion order. Runtime patching of compiled bytes is forbidden.

## 6. Independent vectors and oracle

Reference-equivalence uses versioned cases with two disjoint sections: complete input graphs and literal expected outputs. Production compiler code may consume only the input graph and must never read, import, copy, derive from, or select behavior using expected values.

Tests implement an independent oracle in a separate test-only module. It may parse the case format but must not import production calculation helpers, constants assembled by those helpers, production receipt builders, or production canonical-output builders. The oracle independently implements integer arithmetic, ceiling, MiB rounding, strict-bound comparisons, phase classification, and graph completeness, then compares both its result and the production result to the stored expected vector.

Cases cover at least the K0a worksheet, D0/K0b package rows, both K0b checkpoint phases, control and S binary N/A proofs, artifact/event seed count and bytes, incomplete/unknown facts, false N/A, stale hashes, phase gaps/overlaps/reorder/third phase, fifth trigger, publication 27-30 boundaries, binary per-object/aggregate overflow, and zero-credit constraints. Any extra, missing, coerced, approximately equal, or differently rounded output fails.

## 7. Budget and exact two-phase invariants

The supplemental plan-review package is design-time, non-checkpointed, and separate from K0b runtime: `2 nominal / 4 worst-case` calls. Nominal is one initial review per stream. Worst case allows exactly one r1 per stream and only after an r0 blocking finding. It contributes zero credit to runtime, F15, another package, checkpoint bytes, or publications. Combined forecast arithmetic is `58 + 2 = 60` nominal and `90 + 4 = 94` effective worst-case; K0b-01 implementation/runtime remains `0/0` model calls.

The runtime compiler still emits exactly two chronological, contiguous, non-overlapping, exhaustive checkpoint-budget phases in order: `K0b-runtime-operational`, then `K0b-F15-exact-measurement`. It must preserve operational `16/30` calls, checkpoint bytes `9437184/27262976`, publications `14/34`, and packs `132120576/926941184`; F15 exact `36/36` calls, checkpoint bytes `10485760/36700160`, publications `12/26`, and packs `125829120/954204160`; seed count `6/12`, seed bytes `2236416/4472832`, and observable pack sum `257949696/1881145344` without credit.

Limits remain strict: checkpoint `< 104857600`, phase pack `< 1073741824`, warning `536870912`, batch at most 12 publications, publication p95 below 10 seconds, and clean-clone restore below 120 seconds. Factor remains `1.0`; overlap, compression, delta, dedup, cross-phase, retry, or batch-reset credit remains zero. Unclassified/multiply classified membership, a gap/reopen/reorder, third phase, stale predecessor seal, fifth F15 trigger, separate K0b-05 run, post-seal non-F15 call, post-F15 call, or publication count at least 30 blocks. Counts above 26 require pre-effect reforecast.

## 8. Review sequence and implementation entry gate

Two independent plan reviews are prepared, not executed by this plan:

1. Migration review: four-table dependency closure, SQLite FK/swap feasibility, historical-byte preservation, backup/restore, old-reader rejection, idempotency, and injected-failure atomicity.
2. Compiler/budget review: 21-schema closure, route/reachability/barriers, two receipts and aggregate manifest, oracle independence, reference equivalence, binary fail-closed behavior, and exact budget/phase arithmetic.

Each dispatch must use manual VSCode UI and a fresh ledger-compliant invocation ID plus an exact pre-dispatch receipt containing the manually selected model and model ID. API/REST/SDK/Responses API, managed credentials, inferred/static model IDs, provider/model fallback, and reuse of expired K0b-00 ordinals 29/30 are forbidden. No r1 is allowed unless the corresponding r0 contains a blocking finding.

After both model-review streams have terminal outputs, a human-only review/signoff stage follows. Its reviewer identity and capacity assignment remain pending; no signoff is inferred from the option selection itself.

Implementation remains blocked until both independent streams recommend approval with zero open blocking findings, the exact human-only signoff exists, and a new exact-hash-bound implementation owner disposition binds this plan, the reviews, the human record, and an allowed write/validation set. None of the frozen draft files satisfies an entry gate.

## 9. Stop conditions and handoff

Stop on any stale hash, missing authority, ambiguous FK-preserving rebuild, historical content variance, extra event/schema/output family, dangling graph edge, production/oracle coupling, budget variance, third phase, threshold/storage change, need for a forbidden input, API/provider fallback, physical call without dispatch prerequisites, or write beyond planning/review preparation.

This planning handoff consists only of this v1.1 plan, its owner direction, its budget supplement, the frozen-draft record, and two exact review-input packages. It creates no review result, implementation evidence, owner implementation approval, runtime phase, model receipt, ledger entry, checkpoint, projection, commit, push, or PR.
