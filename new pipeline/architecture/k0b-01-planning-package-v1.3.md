# K0b-01 Alpha Foundation Planning Package v1.3

| Field | Value |
|---|---|
| Work item | `K0b-01` |
| Version | `1.3.0` |
| Status | owner-directed governance remediation; implementation blocked |
| Base | v1.2 SHA-256 `f6c297a111346a017cf12925d8d3f4fe8d0a168b0a8e34737f93a43edb4775ff` |
| New implementation/runtime authority | none |
| Remaining independent-review model budget | zero |

## 1. Authority, supersession, and claim boundary

This is the normative v1.3 overlay on v1.2. Every non-conflicting v1.2 requirement remains binding, including the exact four-table migration algorithm, canonical typed preservation profile, exact SQLite platform row, 21-event matrix, five/three receipt ownership split, two checkpoint-budget phases, and all runtime prerequisites. This document supersedes v1.2 only where the 2026-09-08 human audit identified a governance or future-implementation defect.

The exact owner direction is `new pipeline/decisions/k0b-01-governance-remediation-owner-direction-v1.yaml`, SHA-256 `364a6941a216a6f285a63b03f44d218895bf9944a7254eeca5758da649f698d1`. The audit source has SHA-256 `8c796d6fd4e0f6f0d2763940c54cc31f8d7b50f8f905ac2a441d2a00e5b42eb8`. The read-only frozen-draft triage is `new pipeline/evidence/k0b-01-frozen-draft-reuse-triage-v1.yaml`, SHA-256 `3976909ee3058cc02c993ddf7cf24cfb737f52b7dc566f212e80b82d1a924d5e`.

The two r1 approvals remain valid evidence that v1.2 closed the eight r0 design blockers; they did not review the later human findings and are not approval of v1.3. No r2 or replacement model review is available under the exhausted four-call package. A future human-only review must evaluate this exact v1.3 hash and every open decision below before any implementation disposition.

Claims must name their layer. The former phrase `closed_21_event_Alpha0_definition` is forbidden without qualification. Before persistence it may be claimed only as `registry_level_closed_21_event_Alpha0_definition`; database, runtime, security, and end-to-end claims remain separately gated.

## 2. Governance baseline and status projection

D0-05 is a current prerequisite, not historical decoration. The exact hash-reachable governance graph, including immutable reviews, dispositions, ledgers, evidence, this plan, and frozen bytes referenced by the freeze manifest, must be committed without dangling path/hash edges. The containing governance commit supplies the baseline commit identity; no file self-embeds that commit SHA.

The commit set must exclude caches, temporary files, external attachments, product workspaces, canonical fixture content, `research/old-swarm`, `projects/swarm`, and unrelated user changes. Frozen artifacts are included unchanged only because the authoritative freeze and triage records hash-reference them. Inclusion preserves provenance and does not activate or approve them.

`new pipeline/state/state.yaml` is the machine-readable current-state projection and `new pipeline/state/STATE.md` is its human projection. Each row supplies work item, status, exact authority path/hash, supersession facts, and open gates. A stale immutable source status is never silently rewritten: the state projection names its effective successor. Root-plan v0.16/v0.13 bytes remain unchanged because K0b-00 binds their complete-file hashes; the state projection must mark their internal `DRAFT` labels and architecture §18.3 automatic-adapter wording as superseded by the final K0b-00 disposition and fixed-hybrid manual VS Code profile.

The frozen `k0b-01-validation-v1.yaml` must appear as `non_authoritative_superseded_draft_evidence`, never as the current K0b-01 status. State projections are governance navigation aids; authority remains the cited complete-file hashes.

## 3. Frozen-draft reuse boundary

The 18 frozen artifacts remain byte-preserved. The triage found zero complete files eligible for reuse, two provenance-only records, and sixteen required rewrites. Future implementation may reuse only concepts explicitly listed in the triage, rederived against this plan and a later exact owner disposition.

No future author may import a frozen module, patch it in place, copy a frozen file wholesale, retain its invalid authority hashes, or cite its earlier passing tests as evidence. The authoritative implementation must use a new exact write set and new hashes. Provenance paths may remain in Git but must never be placed on an executable/import search path by an authorized K0b-01 entry point.

## 4. One source of truth and honest file formats

The future authoritative registry source is one strict-JSON document named with `.json`, provisionally `registry/alpha0/alpha0-routing-contract-v1.json`. It owns the normative 21 event rows, F00/Alpha branches, delivery/terminal tuples, fields read, activation, replay/idempotency facts, five S routes, F04 barrier, F05 revision-owner rule, phase fences, and the exact eight output-family vocabulary.

Separate event, subscription, and S-route files may exist only as compiler outputs. Production Python must not contain `EXACT_EVENT_METADATA`, copied event rows, copied route tables, copied authority hashes, or another hand-maintained truth set. It receives a hash-bound input manifest, validates generic schemas and closed counts, and compiles from the single registry source.

Files containing strict JSON use `.json`. A `.yaml` suffix is reserved for YAML parsed by the agreed YAML parser/profile. The phrase “JSON-compatible YAML” does not justify a misleading extension.

Complete-file source hashes live in an immutable input manifest or receipt, not in reusable Python constants. Test-only independent expected outputs live outside the production source graph. Production compilers, helpers, receipt builders, and output builders cannot import, read, or derive from those expected outputs.

## 5. Compiler boundary retained and strengthened

Receipt A `registry_and_routing` remains sole owner of the five v1.2 registry/routing families. It consumes the single JSON registry, generic schemas, exact authority manifest, and its own compiler hash. Receipt A contains all five output hashes and a diagnostic result.

Receipt B `resource_and_budget` remains sole owner of the three budget families. It consumes the accepted complete-file hash of receipt A and all five A-family hashes. Receipt B never reconstructs registry facts from Python constants. The aggregate manifest rejects overlap, omission, extra families, owner mismatch, missing or wrong B-to-A binding, reverse dependency, cycle, stale input/compiler/schema/authority hashes, or any non-pass diagnostic.

The future implementation uses two compiler modules or two entry boundaries with disjoint output constructors. A convenience aggregate API may call A and then B but cannot make either receipt optional or merge their ownership.

## 6. Binary size-stress correction and open K0b-B02 gate

For every applicable binary budget, three independent quantities are mandatory:

1. nominal expected bytes = `nominal_object_count × assumed_mean_object_bytes`;
2. forecast worst-by-count bytes = `worst_case_object_count × assumed_mean_object_bytes`, retained only for comparison with the approved historical forecast;
3. size-stressed bytes = `worst_case_object_count × hard_per_object_bytes`.

The compiler validates every actual object against `hard_per_object_bytes`, the cumulative actual bytes against `runtime_aggregate_limit_bytes`, and size-stressed bytes against both the policy maximum and runtime aggregate limit. It then substitutes size-stressed bytes into a separate worst-size checkpoint/phase-pack calculation. Passing the mean-based forecast cannot offset or suppress a failing size-stress calculation.

The current K0b case has non-binary worst components `22,020,096` bytes, `12` objects, and a `1,048,576`-byte object hard limit. Size-stressed binary bytes are therefore `12,582,912`; the resulting checkpoint is exactly `34,603,008` bytes (`33 MiB`). At `34` publications the runtime phase pack is `1,176,502,272` bytes, exceeding the unchanged `1,073,741,824`-byte hard limit by `102,760,448` bytes. The authoritative compiler must report `above_hard`; implementation cannot proceed on the old values.

Open owner decision `K0b-B02` must select a correction without credit, threshold increase, storage migration, or third phase. The recommended candidate retains 12 objects and 34 publications but reduces `hard_per_object_bytes` to `655,360` (`640 KiB`): size-stressed binary bytes become `7,864,320`, the rounded checkpoint becomes `30,408,704` bytes (`29 MiB`), and the phase pack becomes `1,033,895,936` bytes, leaving `39,845,888` bytes (`38 MiB`) below the hard limit. Alternatives are reducing the worst object count to at most 8 at the 1 MiB hard size, or separately reducing publication amplification under a newly reviewed policy. No candidate is selected by this plan.

Reference inputs and literal expected-output oracle bytes must be separate files. New negative cases include: every object at the hard size; one object above hard; cumulative actual bytes above runtime aggregate; size-stress above phase hard while mean forecast passes; rounding across the 30/31 MiB boundary; and exactly-at versus one-byte-over aggregate semantics.

## 7. Migration I/O, root allowlist, and schema construction

All v1.2 migration requirements remain mandatory. In addition, both source database and backup destination must resolve inside one exact owner-approved temporary runtime root. The guard rejects paths equal to or outside that root, symlink/junction/reparse escapes, missing verified parents, source/backup identity, and any root identity mismatch. A denylist or substring test is forbidden. The canonical fixture and product/research roots are unreachable by construction rather than enumerated as an incomplete blacklist.

Historical content hashing implements `pipeline-v2.sqlite-content-digest-v1` incrementally. Each table is queried in the plan-defined complete primary-key order and consumed in a bounded batch, provisionally at most 512 rows. Each encoded cell and row frame is fed directly to SHA-256; the adapter retains only current batch bytes, rolling hash state, row count, PK/UNIQUE/FK summaries, and required per-row digests. It never constructs or JSON-sorts a whole table in memory. Query-plan, collation, invalid-text, NaN, missing-PK, and duplicate-key ambiguity fail closed.

The expected v3/v4 schema fingerprint is computed once per process for the tuple `(SQLite library version, migration 0001 hash, 0002 hash, 0003 hash, 0004 hash)`. A bounded immutable process-local cache may reuse only an exact tuple match. It holds schema metadata, not database payload. Cross-process or on-disk cache reuse is forbidden unless separately designed and hash-bound. Every initialize still verifies live schema, migration identities, platform, connection settings, and content; caching cannot bypass a check.

The new migration and its tests must implement the exact four-table create-copy-drop-rename-recreate sequence, full FK/schema-object inventory, exact supported-platform WAL/FULL recovery matrix, all named exception/process-loss boundaries, backup identity separation, streaming digest, and all three pinned K0a reader rejection checks. The frozen additive migration and five-point exception-only tests are ineligible.

## 8. Implementation invocation accounting

Before any implementation session, governance must define `implementation_invocations` separately from design invocations and runtime physical model calls. Each record minimally contains invocation ID, human/agent actor, model if any, purpose, exact input authority hashes, exact allowed write set, start/end timestamps, model/API/tool counts, output hashes, and validation evidence.

The frozen unapproved implementation session is recorded retrospectively only as an explicitly unauthorised historical incident with unknown fields left unknown; no model, timestamp, or cost is invented. It receives no design or runtime budget credit. A future implementation disposition must allocate an explicit implementation-session budget and require its ledger entry before claiming completion.

## 9. Security and later-work-item dispositions

The K0b-01 path/root correction is an implementation prerequisite here. Secret-shape, JWT/Bearer, provider-token, high-entropy, base64, and split-line detectors belong to K0b-03 and must be added before F10; the scanner is hygiene, not proof of prompt-injection safety.

The F15 conclusion must state that HYP-DISPATCH-01 evidence is only as strong as manual transcript/model attestation. The accepted manual transport risk is not converted into cryptographic provenance.

Before K0b-02, owner must confirm the single-source registry decision and projection ownership. Before N1, policy-valued context/failure-receipt limits must move out of function defaults into a versioned policy registry. Removal of the separate review-copy directory under `projects/` is a cleanup task and is not performed by this plan or governance commit.

## 10. Root plans, tooling, and review-process follow-up

The current root plans remain hash-bound historical baselines. Their stale labels and automatic-adapter wording are made visible in state governance rather than edited in place. A later separately authorized root-plan successor may consolidate K0b decisions and transition to an active baseline.

Before K0b-01 implementation, a toolchain/CI manifest must pin Python, SQLite, formatter/linter, import-root strategy, and one supported validation entry point. This is a prerequisite, not evidence that CI exists now.

For future review packages, r0 receives a fixed completeness checklist and must enumerate every blocking finding it can identify. A genuinely new r1 issue not caused by the revision is normally non-blocking unless it identifies safety, authority, data-loss, or hard-budget violation. Review tracks sharing one authority graph should use one consolidated reviewer unless independence or expertise requirements justify a split. This prospective policy does not rewrite the completed K0b-01 r0/r1 records.

## 11. Entry gates and stop conditions

Governance remediation is complete only when the exact graph is committed and the containing commit has no dangling hash reference. This does not open implementation.

K0b-01 implementation remains blocked on all of the following:

- D0-05 hash-reachable governance baseline commit;
- this exact v1.3 plan and state projections committed;
- explicit `K0b-B02` binary-budget owner decision and recalculated reference case;
- toolchain/CI manifest and one supported validation entry point;
- implementation-invocation ledger schema and budget;
- separate human-only review/signoff of v1.3 and the selected K0b-B02 outcome;
- later exact hash-bound implementation owner disposition with a new write/validation set.

Any frozen-byte change, forbidden-root access, unreviewed threshold/storage/phase change, unresolved size-stress hard stop, missing root confinement, non-streaming whole-table preservation path, production-to-oracle dependency, registry/Python double-entry truth, or dangling governance hash stops before implementation.

No runtime code, contract, schema, registry, migration, prompt, fixture, projection, checkpoint, physical model call, API call, push, PR, deploy, or release is authorized by v1.3.
