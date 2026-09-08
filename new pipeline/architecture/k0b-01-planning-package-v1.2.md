# K0b-01 Alpha Foundation Planning Package v1.2

| Field | Value |
|---|---|
| Work item | `K0b-01` |
| Version | `1.2.0` |
| Status | `r1_review_candidate`; planning only |
| Revision purpose | Close all five migration and three compiler/budget r0 blocking findings |
| Implementation/runtime authority | None |
| Remaining review budget | Exactly two r1 calls on `gpt-5.6-sol`; zero calls afterward |

## 1. Revision, authorities, and unchanged scope

This is the normative v1.2 overlay on v1.1 SHA-256 `14449871269f237cc90fb61a6946a7f92c6f7a93635fd49b8652ce3311319429`, which itself incorporates v1 SHA-256 `028aa3e3667ff55f92a732d3b2424c704bdb0eaa81268a49c7505cfaa9a2e85f`. Non-conflicting requirements remain binding. This revision supersedes only the ambiguous or incomplete details identified by the two r0 reviews.

Exact revision authority is `new pipeline/decisions/k0b-01-plan-v1.2-owner-continuation-v1.yaml`, SHA-256 `e1d7c0d60150e1098d065dc5fba915a2db002e4f5dee69469a5bb18c93c293bc`. The controlling final K0b-00 disposition remains SHA-256 `544a6160fc27be348794179f44b44080b87bf3f53c0dd1b66baf9c7d1a40fe9d`. Migration r0 is SHA-256 `7446b15de247d14ee6c717f709ca46e3e7904ebd9ded77dc3dc63e53db5fdad2`; normalized compiler/budget r0 is SHA-256 `a57b85f422fc5b2002b2f814c4f21eca7d79a69855d1de7b2d6004d4845c096c`. Review execution/evidence qualifications remain bound by reconciliation SHA-256 `4544812b3f632bcdad469c5672947beaa467dd64f1c89913e435308595b4ecdd`.

The v2 review budget supplement is `new pipeline/evidence/k0b-01-plan-v1.2-review-budget-supplement-v2.yaml`, SHA-256 `19a8603578bdf93f2572fcd994ad8012ec34f0be87f9f7aa84f973b08cd70d34`. The exact validation platform observation is `new pipeline/evidence/k0b-01-migration-validation-platform-v1.yaml`, SHA-256 `509abcbea93182aa641cd048815cee0ffbae4d9a818264e162cb458d35d71f76`.

No runtime code, contract, schema, registry, migration, prompt, projection, checkpoint, fixture, or frozen draft byte is created or authorized here. The canonical fixture, `research/old-swarm`, and `projects/swarm` remain prohibited. The frozen 18-file engineering draft remains unavailable as authority or review input.

## 2. Exact SQLite validation matrix and connection contract

The mandatory conformance row is Windows Server 2022 `10.0.20348` AMD64, CPython `3.12.7` Anaconda, Python sqlite module `2.6.0`, SQLite library `3.45.3`. An unlisted OS, architecture, Python, or SQLite version is unsupported until separately hash-bound conformance evidence exists; portability is never inferred.

The future migration adapter must assert, in order and before source mutation:

1. no active transaction and no second migration writer;
2. `PRAGMA busy_timeout=5000`, `recursive_triggers=ON`, `legacy_alter_table=OFF`, `journal_mode=WAL`, and `synchronous=FULL`, each read back exactly;
3. `PRAGMA wal_checkpoint(TRUNCATE)` completes with zero busy frames;
4. `PRAGMA foreign_keys=OFF` is set and read back before `BEGIN IMMEDIATE` because changing it inside a transaction is ineffective;
5. source v3 preflight, backup, and a second pre-mutation source digest all agree;
6. one `BEGIN IMMEDIATE` encloses every DDL/DML rebuild mutation through all pre-commit checks;
7. after commit, `PRAGMA foreign_keys=ON` is set/read back and both integrity checks run again.

Only the exact row above must pass process-loss validation. Other rows fail the compatibility gate without touching the database.

## 3. Complete four-table dependency and schema-object inventory

The selected rebuild set remains exactly `runs`, `run_state_transitions`, `events`, and `event_deliveries`. These external child foreign keys must retain byte-identical `sqlite_schema.sql` before and after migration:

| Parent | External child foreign keys |
|---|---|
| `runs` | `actor_proposal_consumptions.run_id`; `actor_proposals.run_id`; `artifact_version_lineage.run_id`; `artifact_versions.run_id`; `artifacts.run_id`; `deliveries.run_id`; `manual_dispatches.run_id`; `publication_transactions.run_id`; `readback_gates.run_id`; `replay_points.run_id`; `sink_acceptances.run_id` |
| `events` | `deliveries(triggering_event_id,run_id)`; `publication_transactions(handoff_event_id,run_id)`; `publication_transactions(version_created_event_id,run_id)`; four `readback_gates(*_event_id,run_id)` constraints; `sink_acceptances(handoff_event_id,run_id)` |
| `event_deliveries` | `sink_acceptances.event_delivery_id` |
| `run_state_transitions` | none |

Internal closure edges are `run_state_transitions.run_id -> runs`, `events.run_id -> runs`, `events(caused_by_event_id,run_id) -> events(event_id,run_id)`, and `event_deliveries.event_id -> events`. Existing outbound composite event edges to `physical_invocations(invocation_id,run_id)` and `artifact_versions(artifact_version_id,run_id)` remain exact.

The v3 schema owns one explicit index, `events_run_type_idx`, and exactly these eleven triggers on rebuilt tables: `event_deliveries_immutable_delete`, `event_delivery_snapshot_immutable`, `event_delivery_state_transition_is_exact`, `events_immutable_delete`, `events_immutable_update`, `run_completed_event_requires_gate`, `run_identity_immutable`, `run_state_transitions_immutable_delete`, `run_state_transitions_immutable_update`, `runs_k0a02_blocks_completed_insert`, and `runs_k0a02_requires_completion_gate`. PRIMARY KEY and UNIQUE auto-index semantics are recreated by exact v4 table constraints, never by copied `sqlite_autoindex_*` names.

The migration may replace a listed trigger only with an explicitly named v4 trigger that has an exact F00-preservation branch plus an independently enumerated Alpha branch. All external tables, indexes, triggers, and views remain byte-identical. “Same or stricter” is removed: historical F00 DDL and behavior must be exact except these enumerated CHECK vocabulary widenings only: `runs.profile`, `runs.state`, `run_state_transitions.from_state/to_state`, `events.event_type/event_version`, and `event_deliveries.subscriber_id/terminal_policy/state`.

## 4. Single-valued create-copy-drop-rename-recreate algorithm

All staging tables use suffix `__k0b01_new`, are `STRICT`, contain the final v4 constraints, and write foreign-key target names as the final names (`runs`, `events`, and other unchanged parents), never staging names. With foreign keys already disabled and one immediate transaction active, the exact mutation order is:

1. Create `runs__k0b01_new`, `events__k0b01_new`, `run_state_transitions__k0b01_new`, `event_deliveries__k0b01_new` in that order. Create no triggers or secondary indexes yet.
2. Copy explicit named columns without casts, defaults, normalization, or `SELECT *`, in this order: `runs`, `events`, `run_state_transitions`, `event_deliveries`. Compare row count and canonical historical row digest immediately after each copy.
3. Drop only the four old tables, child first: `event_deliveries`, `run_state_transitions`, `events`, `runs`. Old table names are never renamed, preventing SQLite from retargeting external child FK SQL to temporary names.
4. Rename staged parents to final names in this exact order: `runs__k0b01_new -> runs`, `events__k0b01_new -> events`, `run_state_transitions__k0b01_new -> run_state_transitions`, `event_deliveries__k0b01_new -> event_deliveries`.
5. Recreate `events_run_type_idx`, the eleven exact v4 triggers, and all newly authorized Alpha indexes/triggers from explicit statements. Reject duplicate, missing, extra, or reordered schema-object identities.
6. Compare every external `sqlite_schema` row byte-for-byte, validate the exact final v4 schema fingerprint, compare historical content, then insert one v4 migration record and set `user_version=4`.
7. Run `integrity_check`, `foreign_key_check`, row/digest/readback checks inside the transaction and commit only if every result passes. Re-enable foreign keys and repeat both checks after commit.

No `ALTER TABLE ... RENAME` is applied to an old parent. No external child table is rebuilt or edited. Any SQLite behavior that rewrites an external child definition, even semantically equivalently, blocks and rolls back.

## 5. Canonical historical content digest v1

Historical preservation uses `pipeline-v2.sqlite-content-digest-v1`, not SQL text rendering or JSON coercion. SHA-256 consumes this binary stream:

1. ASCII header `pipeline-v2.sqlite-content-digest-v1` followed by byte `00`.
2. Tables sorted by UTF-8 table-name bytes. Each name is framed as unsigned 64-bit big-endian byte length plus raw UTF-8 bytes.
3. Columns use `PRAGMA table_info` `cid` order and are name-framed the same way.
4. Every table must have a declared primary key. Rows are sorted in memory by the lexicographic binary encoding of the complete declared primary-key tuple; database collation, insertion order, and query plan are irrelevant.
5. Each row starts with byte `52`, an unsigned 64-bit big-endian column count, then each cell as a one-byte storage-class tag and unsigned 64-bit big-endian payload length: NULL `4e`/zero bytes; INTEGER `69`/signed 64-bit two’s-complement big-endian; REAL `72`/IEEE-754 binary64 big-endian with NaN forbidden; TEXT `74`/exact UTF-8 bytes returned by SQLite with invalid encoding blocking; BLOB `62`/raw bytes.
6. Each table ends with byte `45` and unsigned 64-bit big-endian row count.

Before migration, retain per-table and per-row digests plus the aggregate. After migration, compare the historical projection: every pre-existing table and column; versions 1-3 only in `schema_migrations`; every pre-existing row in the four rebuilt tables; and all rows in untouched tables. New v4 rows/columns/tables are excluded only by an explicit manifest, never by discovery.

For every historical event, additionally compare `length(CAST(payload_json AS BLOB))` and `hex(CAST(payload_json AS BLOB))`; for every historical delivery compare the same pair for `fields_read_json`. Text value equality alone is insufficient. Row counts, PK sets, UNIQUE-key sets, FK edge tuples, state revisions, and F00 graph readback must also match.

## 6. Backup identity and restore

The source v3 database and backup are never required to have identical file bytes. The adapter records independently:

- source logical schema fingerprint and historical content digest immediately before backup;
- backup artifact’s own complete-file SHA-256 after the Backup API destination closes;
- backup logical schema fingerprint and historical content digest after independent reopen;
- a second live-source fingerprint/digest immediately before `BEGIN IMMEDIATE` mutation.

Backup is valid only when its logical schema/content values match the source and its own artifact hash remains stable on reread. Source-file SHA-256, if observed, is diagnostic only because WAL/checkpoint/layout differences make physical equality non-normative. Restore copies only the verified backup into a distinct verified new path, reopens it, and reproduces the recorded backup artifact hash or the same logical schema/content digest as appropriate to the copy method. There is no down migration or in-place restore.

## 7. Exact fault and process-loss boundaries

Deterministic exception injection names are: `B00.before_wal_checkpoint`, `B01.after_wal_checkpoint`, `B02.before_backup`, `B03.after_backup_close`, `B04.after_backup_verify`, `T00.before_begin_immediate`, `T01.after_begin_immediate`; `C.<table>.before` and `C.<table>.after` for each copy in the exact section 4 order; `D.<table>.before` and `D.<table>.after` for each drop; `R.<table>.before` and `R.<table>.after` for each rename; `S00.before_schema_objects`, `S01.after_schema_objects`, `M00.before_migration_row`, `M01.after_migration_row`, `M02.after_user_version`, `V00.before_integrity_checks`, `V01.after_integrity_checks`, and `T99.immediately_before_commit`.

Every boundary runs an ordinary raised-exception test. Every post-mutation `*.after` boundary from `T01` through `T99` also runs a separate child-process termination test on the exact supported platform. The child emits a durable boundary marker outside the database, is forcibly terminated, and the parent reopens using SQLite recovery without blind retry. Under `WAL`, `synchronous=FULL`, and one immediate transaction, the reopened source must be exact v3 after every pre-commit termination; the success control is complete v4. `user_version`, migration rows, schema fingerprint, content digest, FK graph, `integrity_check`, `foreign_key_check`, WAL/SHM disposition, and backup restore are checked for every case.

Boundary IDs are constants in the future adapter and tests; a missing, duplicate, reordered, unreachable, or untested ID fails validation.

## 8. Exact K0a reader rejection set

The universal-reader claim is narrowed to these three exact implementations and entry points:

| Reader | Complete-file SHA-256 | Entry point | Required v4 result |
|---|---|---|---|
| `new pipeline/harness/k0a01/store.py` | `06a7eb07c17244f1078e6178f91ba2fdb75027703c2ca351ca8d77d17a72c925` | `K0a01Store.initialize()` | raise `MigrationError("unsupported schema version 4")` |
| `new pipeline/harness/k0a02/store.py` | `4b14f84388e6b2a603da900eca798ea2341e81b1d0a76b9c116e38d0501daa55` | `K0a02Store.initialize()` | raise `MigrationError("unsupported schema version 4")` |
| `new pipeline/harness/k0a03/store.py` | `bd030c0983de68201919b32a59a77299b3098ecdaca42a57eabb2fc01af45bb7` | `K0a03Store.initialize()` | raise `MigrationError("unsupported schema version 4")` |

Tests create a synthetic exact v4 database in a temporary path, call each pinned reader, assert the exact exception type/message, and prove pre/post schema/content digests and file set are unchanged. Package `__init__`, CLI, and orchestrator paths are not separate database readers; any later-discovered entry point is out of claim until enumerated and hashed. No K0a byte is edited.

## 9. Normative 21-event Alpha matrix

All rows are schema version 1 and immutable. `producer` is the semantic request owner; Artifact/Event remains the sole persister. `delivery` is a fixed compiled subscriber/policy/state tuple. The five retained rows preserve the exact F00 delivery before the semicolon and define a distinct Alpha delivery after it. `activation` names the only future work item allowed to emit the Alpha form; K0b-01 only compiles it.

| Event | Producer | Delivery or terminal | Exact fields read | Activation | Replay and idempotency |
|---|---|---|---|---|---|
| `command.received` | `control.authenticated_ingress` | F00 and Alpha: `s0_control_delivery/control_delivery/pending` | `run_id,profile,command` | F00 retained; Alpha `K0b-04` | root preserved; key `(run_id,v1,command_id)` |
| `run.started` | `shared_control.run_fsm` | F00 `bootstrap_readback/observational_terminal/observed_terminal`; Alpha `control.run_lifecycle/control_delivery/pending` | `run_id,state` | F00 retained; Alpha `K0b-04` | once per transition revision; key `(run_id,v1,to_revision)` |
| `artifact.version_created` | `artifact_event.transaction_writer` | F00 `bootstrap_readback/observational_terminal/observed_terminal`; Alpha `control.artifact_lifecycle/artifact_delivery/pending` | `artifact_version_id,artifact_type,content_sha256` | F00 retained; Alpha `K0b-04` | historical version reused; key `(run_id,v1,artifact_version_id)` |
| `handoff.ready` | `artifact_event.transaction_writer` | F00 `bootstrap_sink/fixture_terminal/pending`; Alpha `control.handoff_delivery/control_delivery/pending` | `artifact_version_id,profile,route_id` | F00 retained; Alpha `K0b-04` | new descendant only after invalidation; key `(run_id,v1,artifact_version_id,route_id)` |
| `run.completed` | `shared_control.run_fsm` | F00 `bootstrap_readback/observational_terminal/observed_terminal`; Alpha `alpha_observation/observational_terminal/observed_terminal` | `run_id,state,completion_gate_id` | F00 retained; Alpha `K0b-04` | terminal never replayed into same run; key `(run_id,v1,terminal_revision)` |
| `run.blocked` | `shared_control.run_fsm` | `human_blocker_queue/block_run_and_enqueue_human/accepted_terminal` | `run_id,state,block_code,evidence_ref` | `K0b-04` | preserve blocker; key `(run_id,v1,state_revision,block_code)` |
| `run.abort_requested` | `shared_control.abort_coordinator` | `control.abort_coordinator/control_delivery/pending` | `run_id,abort_request_id,reason_code` | `K0b-03` | duplicate returns same fence; key `(run_id,v1,abort_request_id)` |
| `run.aborted` | `shared_control.abort_coordinator` | `alpha_observation/observational_terminal/observed_terminal` | `run_id,state,reconciliation_ref` | `K0b-03` | terminal never reopens; key `(run_id,v1,terminal_revision)` |
| `artifact.published` | `artifact_event.publication_writer` | `control.artifact_lifecycle/artifact_delivery/pending` | `artifact_version_id,publication_transaction_id,content_sha256` | `K0b-02` | same publication returned; key `(run_id,v1,publication_transaction_id)` |
| `projection.requested` | `artifact_event.transaction_writer` | `artifact_event.projector/projection_delivery/pending` | `decision_version_id,projection_profile_sha256,pair_stem` | `K0b-02` | same outbox intent returned; key `(run_id,v1,decision_version_id,projection_profile_sha256)` |
| `projection.written` | `artifact_event.projector` | `control.projection_reconciliation/control_delivery/pending` | `projection_id,yaml_sha256,markdown_sha256` | `K0b-02` | same verified pair returned; key `(run_id,v1,projection_id)` |
| `projection.failed` | `artifact_event.projector` | `human_blocker_queue/block_run_and_enqueue_human/accepted_terminal` | `projection_id,failure_code,evidence_ref` | `K0b-02` | failure preserved; key `(run_id,v1,projection_id,failure_code)` |
| `revision.requested` | `shared_control.revision_coordinator` | `s.revision_coordinator/s_revision_delivery/pending` | `artifact_version_id,revision_owner_zero_role_id,reason_code` | `K0b-04` | creates invalidated descendants only; key `(run_id,v1,artifact_version_id,request_revision)` |
| `gate.passed` | `shared_control.gate_coordinator` | `control.gate_delivery/gate_delivery/pending` | `gate_id,run_id,state_revision` | `K0b-04` | same gate result returned; key `(run_id,v1,gate_id,state_revision)` |
| `approval.requested` | `shared_control.approval_coordinator` | `human_approval_queue/human_approval_wait/pending` | `approval_id,subject_ref,required_role` | `K0b-04` | same pending request returned; key `(run_id,v1,approval_id)` |
| `approval.granted` | `control.authenticated_approval_adapter` | `control.approval_coordinator/approval_delivery/pending` | `approval_id,decision_version_id,actor_id` | `K0b-04` | immutable decision returned; key `(run_id,v1,approval_id,decision_version_id)` |
| `approval.rejected` | `control.authenticated_approval_adapter` | `control.approval_coordinator/approval_delivery/pending` | `approval_id,decision_version_id,reason_code` | `K0b-04` | immutable decision returned; key `(run_id,v1,approval_id,decision_version_id)` |
| `error.schema_mismatch` | `shared_control.schema_validator` | `human_blocker_queue/block_run_and_enqueue_human/accepted_terminal` | `run_id,error_code,evidence_ref` | `K0b-04` | error evidence preserved; key `(run_id,v1,source_request_sha256,error_code)` |
| `error.tool_failure` | `shared_control.tool_boundary` | `human_blocker_queue/block_run_and_enqueue_human/accepted_terminal` | `run_id,error_code,evidence_ref` | `K0b-03` | failure preserved, retry gets new attempt; key `(run_id,v1,invocation_id,attempt,error_code)` |
| `error.security_policy` | `shared_control.security_monitor` | `human_blocker_queue/block_run_and_enqueue_human/accepted_terminal` | `run_id,error_code,evidence_ref` | `K0b-03` | frozen evidence never suppressed; key `(run_id,v1,incident_source_id,error_code)` |
| `meta.incident_detected` | `shared_control.security_monitor` | `w5_incident_queue/persist_incident_and_enqueue_W5/accepted_terminal` | `run_id,incident_id,evidence_ref` | `K0b-03` | incident preserved; key `(run_id,v1,incident_id)` |

The compiler rejects any row/field/producer/subscriber/policy/state/activation/replay/key difference, a missing profile branch for a retained event, unknown subscriber, second delivery unless explicitly listed here, or a twenty-second event. Terminal rows have no downstream semantic routing after the recorded queue/observation disposition.

## 10. Disjoint compiler receipt ownership

Receipt A, `registry_and_routing`, is the sole producer of exactly five families: `compiled_artifact_event_profile`, `compiled_event_reachability_graph`, `compiled_subscription_terminal_snapshot`, `compiled_s_route_table_v2`, and `compiled_fanout_barrier_profile`.

Receipt B, `resource_and_budget`, is the sole producer of exactly three families: `compiled_resource_forecast`, `compiled_checkpoint_phase_partition_v1`, and `compiled_checkpoint_publication_budget_v2`. B consumes the complete-file hash of accepted receipt A and the five A-family hashes as immutable graph facts; A never consumes B. This gives one directed edge `A -> B` and forbids a cycle.

The aggregate manifest consumes A and B only after both pass. It rejects any family produced by both, any omitted/extra family, owner mismatch, B receipt that does not bind the exact A hash/families, reverse dependency, cycle, stale authority/compiler/schema hash, or diagnostic result other than pass. Its family set equality is exact: five plus three equals the eight v1.1 families.

## 11. Complete review-package human-attention budget

Package `K0b01-plan-v1.1-independent-reviews` retains light model-call budget `2 nominal / 4 worst-case`, non-checkpointed. Its human-attention profile is `standard`: sessions `1/2`, blocking decisions `1/3`, active minutes `30/90`, maximum single session `60`, `batchable_requests=true`. Nominal covers one owner batch over both r0 outputs; worst case covers the revision decision and both r1 output checks. Future human-only final signoff is excluded and still needs its own identity/capacity record.

Against the K0b baseline, combined human totals are sessions `2+1=3` nominal and `4+2=6` worst; blocking decisions `3+1=4` and `6+3=9`; active minutes `60+30=90` and `150+90=240`; maximum session remains 60; envelope remains `high_attention`. Model totals remain `58+2=60` nominal and `90+4=94` effective worst. Runtime calls, two checkpoint phases, publications, binary/checkpoint bytes, thresholds, and every no-credit rule remain unchanged.

## 12. r0 closure, r1 acceptance, and stop

Sections 2-8 close migration findings `K0B01-MIG-R0-001..005`. Section 9 closes `K0B01-CB-R0-F01`; section 10 closes `F02`; section 11 and budget supplement v2 close `F03`.

Exactly two fresh-context r1 agents may review this exact hash: migration and compiler/budget, each `gpt-5.6-sol`, one call, no subagents, no API, and one output file. The four-call worst-case review budget is exhausted after those two calls; there is no correction/return/model-call reserve.

Implementation remains blocked unless both r1 reviews recommend `approve` with zero open blocking findings, exact hashes and ledger entries reconcile, a separate human-only review/signoff exists, and a later exact owner disposition explicitly authorizes an implementation write/validation set. Any residual finding, unsupported platform, ambiguous migration rule, event-matrix inconsistency, budget variance, need for a forbidden input, or review evidence defect stops at owner-facing planning evidence. No runtime, implementation, commit, push, PR, deploy, or release follows automatically.
