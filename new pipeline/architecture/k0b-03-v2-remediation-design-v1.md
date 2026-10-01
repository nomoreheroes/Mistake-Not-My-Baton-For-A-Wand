# K0b-03 v2 remediation design v1

## 1. Status and authority boundary

This document freezes an append-only remediation design for `K0B03-IA-R2-F01` through `K0B03-IA-R2-F08`. All eight findings remain open, high-severity, and blocking. This document does not implement the design, close a finding, authorize a capability experiment, adopt K0b-03 v2, change canonical state, close `G-K0B03-UNTRUSTED-SHAPES`, or grant runtime authority.

The selected architecture is:

`full_append_only_K0b03_v2_replacement_candidate_with_separate_capability_qualification_independent_re_review_owner_closure_and_canonical_adoption_gate_transaction`

The historical 47-path K0b-03 v1 implementation package and its independent-audit record remain immutable. Before a later adoption transaction, v2 is only a candidate successor and has no runtime authority. The scanner remains heuristic hygiene only.

## 2. Architecture choice

Three alternatives were assessed.

1. A single versioned successor without an explicit adoption boundary was rejected because it could be mistaken for effective authority immediately after materialization.
2. Ordered partial successors for contracts, scanner, launcher, lifecycle, and compatibility were rejected because the eight findings share profiles, typed digests, registry bindings, persistence, and validation coverage. Intermediate commits would create split or misleading truth.
3. A complete v2 candidate in one atomic all-new implementation commit, followed by independent review, owner closure, and a separate canonical adoption/gate transaction was selected.

The complete ordered transaction is therefore:

1. this design-freeze documentation commit;
2. a separately authorized Windows enforcement capability qualification and security-focused review;
3. one atomic 70-path candidate implementation and validation commit;
4. fresh-context read-only non-author independent re-review;
5. separate owner closure of all eight findings;
6. separate renderer/profile/state/STATE adoption and `G-K0B03-UNTRUSTED-SHAPES` transition;
7. independent audit of the canonical transition.

## 3. Finding-to-remediation matrix

| Finding | Confirmed gap | Owner and single source | Exact successor components | Required proof | Dependencies |
|---|---|---|---|---|---|
| `F01` | Scanner embeds private-key patterns, lengths, alphabets, thresholds, and Unicode case behavior. | Shared control/W1 scanner. `detector-profile-v2.json` is the only authored detector source. | Detector profile, scanner, compiler. | Positive, negative, exact-boundary and profile-mutation cases; ASCII-only casing; absence of parallel detector literals. | F02, F04 |
| `F02` | Existing schemas are incomplete or open and cannot represent invalid submitted UTF-8 bytes with original-byte offsets. | Shared control schema validator and artifact/event contract owner. Closed v2 schemas are authority. | Closed schemas, typed transient submitted bytes, stdlib offline validator. | Valid/invalid instance pairs, nested unknown fields, strict base64 and UTF-8, sanitized evidence, byte-offset cases. | F08 |
| `F03` | Policy is descriptive; caller supplies allowlists; launcher bypasses admission and does not apply limits or egress isolation. | Shared control tool boundary. `repository-tool-policy-v2.json` is the only authored policy. | Repository guard, tool guard, Job Object backend, AppContainer backend, enforcing launcher. | Exact repo/tool identity, applied limits, owned-tree cancellation, egress denial, canary and no-write-through cases. | F05, F08, `CP-K0B03-V2-WINDOWS-ENFORCEMENT` |
| `F04` | Per-field truncation can hide the global 65th finding; split spans, overlap and tie-breaking are wrong. | Shared control/W1 scanner. Profile v2 plus closed finding/result schemas. | Scanner, finding schema, result schema. | Global multi-field overflow, exact split subspans, CR/LF/CRLF, set-aware overlap/dedup and detector-ID ordering. | F01, F02 |
| `F05` | Lifecycle logic is not persisted and lacks CAS, replay, freeze, reconciliation and late-result fencing. | Shared control abort coordinator/run FSM. Existing `runs.state/state_revision` remains canonical. | Lifecycle, store, migration 0008, registry-derived event routes. | Duplicate/stale abort, non-cancellable/ambiguous effects, late result, crash/partial effect and resume tests. | F03, F06, F08 |
| `F06` | Validation skips the populated migration chain; backup, newer-schema, FK, CAS quarantine, restore and HITL controls are incomplete. | Artifact/event plane owns evidence; shared control owns admission. Immutable 0001–0007 plus additive 0008. | Migration, compatibility, store, restore authorization boundary. | Populated chain and preservation, verified backup, pre/post integrity/FK, crash boundaries, newer-write block, guarded restore. | F05, F08 |
| `F07` | 128 successful cases do not cover the mandatory contracts. | K0b-03 validation/evidence owner. `coverage-map-v2.json` is the sole coverage mapping. | Six case families, coverage map, validation evidence. | Exactly 256 cases in each of two environments, no skips, identical results and outputs; coverage sufficiency distinct from count. | All other findings |
| `F08` | Hashes lack object/profile typing; registry-v2 and event schemas are not bound; route policy is duplicated; attestation boundary is missing. | Registry authority and shared artifact/event plane. Existing registry-v2/event schemas plus v2 hash registry and attestation boundary. | Hash registry, registry binding compiler, compiled bindings, attestation schema/profile. | Cross-profile substitution, replacement, pin conflicts, shadow-route and attestation conflict/reduced-guarantee tests. | F02, F03, F05, F06 |

Closure evidence for every finding must include the input manifest, compiler receipt, compiled-output manifest, coverage map, two-environment validation evidence, implementation document check, completion receipt, independent re-review, and separate owner closure. No successful test count alone closes a finding.

## 4. Ownership and single-source boundaries

- Alpha0 registry v2 remains the only authored source for event types, producers, subscribers, routes, fences, and terminal policies.
- Existing event schemas remain the only authored event payload shapes.
- `detector-profile-v2.json` owns all detector IDs, signatures, alphabets, thresholds, limits, normalization, precedence, and finding-cap semantics.
- `repository-tool-policy-v2.json` owns repository identity, permitted changes, tool grammar, environment, process, resource, and egress requirements.
- `hash-profile-registry-v2.json` owns object-to-hash-profile mappings. Every digest carries object type, profile ID/version, SHA-256, and size.
- Closed schemas own data shapes. Python validation code enforces but does not re-author them.
- Existing `runs.state` and `runs.state_revision` remain canonical run state. New tables journal intents, transitions, fences, reconciliation, and compatibility evidence; they do not create another run-state truth.
- `state.yaml` remains canonical governance state and `STATE.md` remains its one-way projection. Neither belongs to the implementation commit.

## 5. Detector-profile-driven scanner

The scanner compiler accepts only the closed detector profile. Implementation code may contain generic parsing, finite-state, entropy, base64, source-map, ordering, and overlap algorithms, but it may not contain a second signature, provider-prefix, label, alphabet, threshold, padding, precedence, or cap table.

Required semantics include:

- stable detector IDs and ordinal ordering;
- ASCII-only case folding where the profile declares it; Unicode case folding cannot expand the admitted alphabet;
- exact inclusive minimum and maximum bounds and explicit alphabets;
- profile-defined JWT terminal padding and empty-signature handling;
- exact entropy threshold, character classes, and Git/SHA pure-hex exclusions;
- a single strict base64 decode and no recursive decode;
- split-line joins across at most the profile count with no internal character removal;
- exact character-to-original-byte span sets for LF, CRLF, and CR;
- set-aware overlap and exact deduplication across all spans;
- one global finding cap across every request field; the 65th finding produces typed overflow and blocks without silent truncation;
- deterministic tie-breaking by original first byte, complete span set, precedence, stable detector ID, representation and source ordinal.

The input JSON boundary carries submitted bytes as strict base64 only transiently, with an explicit encoding claim. It is decoded once and strict UTF-8 is validated before scanning. Raw, base64, matched, decoded, preview, substring-hash, or otherwise reversible secret material is never persisted or logged.

The mandatory boundary is: scanner output is heuristic hygiene only. A finding blocks admission, but a clean result never authorizes a repository, path, tool, process, egress target, model/provider, persistence action, publication, capability, approval, or F10 result.

## 6. Closed schemas and offline validation

All v2 schemas use Draft 2020-12 and a closed project-supported vocabulary. Every object, including nested findings and sanitized evidence, rejects unknown members. Local `$ref` resolution is bounded to the pinned contract package; remote resolution is forbidden.

The stdlib-only validator implements exactly the frozen vocabulary used by these schemas and rejects an unknown keyword rather than ignoring it. It validates schemas during compilation and validates every runtime instance. It does not become authored shape truth: the schemas remain the source. Positive and negative vectors cover every keyword and every schema, including additional and unevaluated members, integer/string bounds, patterns, enums, constants, arrays, local references, and combinators actually used by the package.

No pip, wheel, external schema fetch, network resolver, ambient package, plugin, or cache is permitted.

## 7. Repository, tool, process, and egress enforcement

The policy must bind the exact repository root, repository role, admitted top-level, Git branch/worktree identity, commit, tree, expected baseline, permitted path allowlist, and permitted change set. Root and every existing path component are checked without following a symlink, junction, mount-like alias, or any Windows reparse point. Absolute, escaping, content-derived, case-colliding, duplicate, and unapproved paths block.

Git and every other tool are admitted only by exact executable path, full-file SHA-256, version, closed argument grammar, exact CWD, and an allowlisted environment constructed from scratch. Response files, shell interpolation, ambient PATH substitution, implicit PYTHONPATH, hooks, plugins, credential helpers, provider/model calls, dependency acquisition, and remote effects are forbidden.

An effect envelope binds a stable effect ID, typed hashes, repository and authority revision, time/CPU/memory/process/output caps, cancellability, expected result, and attestation compatibility record. The launcher must call the guards itself; caller-supplied allowlists are forbidden.

The Windows backend design uses suspended process creation, Job Object assignment before resume, kill-on-close, active-process and memory limits, CPU accounting, wall timeout, bounded stdout/stderr pipes, stable handle ownership, and cancellation only for a declared owned tree. No process disappearance is treated as proof that an external effect did not happen. Unknown state blocks, preserves evidence, and is not retried automatically.

Job Objects do not provide egress isolation. Therefore actual implementation authority is blocked by `CP-K0B03-V2-WINDOWS-ENFORCEMENT`. The candidate is AppContainer with no network capabilities, combined with the Job Object. This is a design, not a proven host capability.

## 8. Persisted abort and reconciliation FSM

An authenticated current-revision abort request maps only `running|waiting` to `aborting` using CAS. Its stable request ID and original disposition are durable; an identical replay returns that disposition without another transition. A stale request or any other source state rejects without mutation.

Abort processing freezes publications and semantic routes, enumerates every begun filesystem, Git, database, checkpoint, provider, and tool intent, requests cancellation only for declared cancellable owned effects, and persists reconciliation obligations. A known completed result is reconciled; a non-cancellable unresolved or ambiguous effect blocks. Late results are fenced and cannot publish.

A crash in `aborting` or `completing` transitions through `reconciliation_required` and `reconciling`. It can return only to the fenced prior semantic branch when all obligations are known, or to a terminal block. `run.aborted` is emitted only when the graph is consistent and no effect is unknown. Abort is not rollback and does not delete worktrees, databases, evidence, or history.

Registry-v2 supplies the event producer, subscriber, route, fence, and terminal disposition. The lifecycle implementation consumes compiled bindings and cannot define a second route table.

## 9. Migration, backup, restore, quarantine, and compatibility

Migration `0008_k0b03_v2_remediation.sql` is an additive forward successor. Files 0001 through 0007 remain byte-immutable. The validated sequence is the complete pinned populated chain through 0008, including existing same-phase migration ordering.

Before migration, the harness creates a consistent verified backup at a new admitted target and records database, pipeline, schema, registry, compiler, partition, executor, migration and authority pins. Integrity and foreign-key checks run before and after. All connections enable foreign keys before any statement.

Preservation proof covers rows, IDs, typed values, hashes, event/version lineage, phase seals, publication identities, and schema history. A required table successor copies transactionally with row/count/hash readback and freezes the former v1 table as historical input rather than parallel current truth.

Crash before commit leaves the previous schema. Crash after commit is recognized through immutable migration identity and is not ambiguously re-applied. A harness facing a newer schema may perform only bounded read-only diagnosis; writes, downgrade, overwrite, attached-database migration, and extension loading block.

Quarantine transitions use expected state/revision CAS and row-count confirmation. Restore requires a verified backup, a new admitted non-reparse target, complete compatibility readback, and an explicit closed owner/HITL authorization token bound to source, destination, hashes, authority revision, expiry and nonce. It never overwrites an active target.

## 10. Registry-v2, event schemas, typed hashes, and attestations

Every hash field is a typed digest with object type, admitted hash-profile ID and version, digest, and byte size. Raw-file bytes, canonical JSON, canonical YAML, artifact payloads, invocation envelopes, and evidence manifests are distinct object/profile bindings. Equal-looking hexadecimal values under a different profile are rejected.

The contract package pins Alpha0 registry v2 and every consumed event schema. The compiler derives the exact event producer, subscriber, route, fence, and terminal policy into `compiled-registry-event-bindings.json`; Python and SQLite do not author competing values.

The attestation boundary is closed and separates observed identity from guarantee. It records exact schema/profile, issuer/owner, scope, revision, time/expiry, nonce, observed executable/environment/path/process/egress identities, guarantee level, missing guarantees, failed probes and evidence digest. A missing, stale, substituted, conflicting, or reduced attestation blocks any effect that requires a stronger guarantee. Attestation validity, scanner cleanliness, reachability, hash match, schema validity, and authority are independent predicates. K0b-04 retains ownership of the actual attestation-limit decision.

## 11. Exact validation matrix

Each of the two fresh locked environments must execute exactly 256 cases with 256 passed, zero failures, zero errors, and zero skips:

| Group | Cases | Mandatory coverage |
|---|---:|---|
| Detector/scanner | 96 | Every family, every provider prefix, min/max±1, ASCII/Unicode negatives, invalid UTF-8, BOM, byte cap, global 65th finding, exact spans, overlap, dedup, ordering, profile mutation |
| Contracts/registry/hash/attestation/compiler | 40 | Every closed schema, typed submitted bytes and digests, cross-profile substitution, registry/event pins, route derivation, attestation conflicts, deterministic compilation |
| Repository/tool/launcher/enforcement | 48 | Root/role/top-level/Git identity, permitted changes, path/reparse cases, executable/grammar/CWD/env, actual caps, owned tree, cancellation, egress and canaries |
| Persisted lifecycle FSM | 32 | CAS, duplicate/stale abort, freeze, non-cancellable and unknown effects, late results, crash/partial effects, reconciliation, resume |
| Migration/backup/restore/compatibility | 32 | Populated 0001→0008, preservation, backup, FK/integrity, crash boundaries, newer-schema denial, quarantine CAS, restore token and target guards |
| CLI/toolchain/determinism | 8 | Closed modes, pinned executables, no dependencies/network, A/B identity, rerender identity, cleanup and residue checks |

The exact case-to-requirement mapping is an authored coverage map. A passed count is execution evidence but is not by itself coverage evidence.

The future environments are:

- `C:/Users/Administrator/AppData/Local/Temp/2/pipeline-v2-k0b03-v2-remediation-A`
- `C:/Users/Administrator/AppData/Local/Temp/2/pipeline-v2-k0b03-v2-remediation-B`

They use pinned CPython 3.12.7, `-B -m venv --without-pip`, no system site packages, dependency set `[]`, network-host set `[]`, disabled bytecode, empty PYTHONPATH, and no ambient caches, plugins, hooks, credentials, signing, or config. All temp data, scratch repositories, databases, backups, restores, canaries, workers, pipes, processes, AppContainer identities and environments must be removed by exact identity before staging. Cleanup must not follow a reparse point.

## 12. Windows capability prerequisite

`CP-K0B03-V2-WINDOWS-ENFORCEMENT` is `open_blocking_implementation_authority`.

The separately authorized qualification must prove, on the pinned host, AppContainer creation with no network capabilities, suspended launch, Job assignment before resume, temporary-root-only ACLs, loopback-only denial, timeout/CPU/memory/process/output enforcement, owned-tree cancellation, canary preservation, and complete process/profile/ACL/root cleanup. The capability result needs a security-focused independent review.

If the proof fails or is inconclusive, F03 remains blocking, the implementation authority is not issued, and no requirement is relabelled as merely declarative. No external isolation product, firewall mutation, network access, or persistent OS policy may be inferred as authorized.

## 13. Exact 70-path candidate implementation inventory

The later implementation commit, if separately authorized after successful capability qualification, is exactly the following all-new inventory:

1. `new pipeline/requests/k0b-03-v2-remediation-and-validation-approval-request-v1.yaml`
2. `new pipeline/decisions/k0b-03-v2-remediation-and-validation-owner-disposition-v1.yaml`
3. `new pipeline/evidence/k0b-03-v2-remediation-input-manifest-v1.yaml`
4. `new pipeline/evidence/k0b-03-v2-remediation-session-entry-v1.yaml`
5. `new pipeline/evidence/k0b-03-v2-contract-compiler-receipt-v1.yaml`
6. `new pipeline/evidence/k0b-03-v2-compiled-output-manifest-v1.yaml`
7. `new pipeline/evidence/k0b-03-v2-requirement-to-test-coverage-v1.yaml`
8. `new pipeline/evidence/k0b-03-v2-remediation-validation-v1.yaml`
9. `new pipeline/evidence/k0b-03-v2-remediation-document-check-v1.yaml`
10. `new pipeline/receipts/k0b-03-v2-remediation-completion-v1.yaml`
11. `new pipeline/registry/k0b03_v2/detector-profile-v2.json`
12. `new pipeline/registry/k0b03_v2/hash-profile-registry-v2.json`
13. `new pipeline/registry/k0b03_v2/repository-tool-policy-v2.json`
14. `new pipeline/registry/k0b03_v2/attestation-compatibility-profile-v1.json`
15. `new pipeline/contracts/k0b03_v2/detector-profile-v2.schema.json`
16. `new pipeline/contracts/k0b03_v2/hash-profile-registry-v2.schema.json`
17. `new pipeline/contracts/k0b03_v2/repository-tool-policy-v2.schema.json`
18. `new pipeline/contracts/k0b03_v2/scan-request-v2.schema.json`
19. `new pipeline/contracts/k0b03_v2/finding-v2.schema.json`
20. `new pipeline/contracts/k0b03_v2/scan-result-v2.schema.json`
21. `new pipeline/contracts/k0b03_v2/invocation-envelope-v2.schema.json`
22. `new pipeline/contracts/k0b03_v2/guard-result-v2.schema.json`
23. `new pipeline/contracts/k0b03_v2/lifecycle-command-v2.schema.json`
24. `new pipeline/contracts/k0b03_v2/lifecycle-result-v2.schema.json`
25. `new pipeline/contracts/k0b03_v2/compatibility-evidence-v2.schema.json`
26. `new pipeline/contracts/k0b03_v2/attestation-compatibility-v1.schema.json`
27. `new pipeline/contracts/k0b03_v2/k0b03-contract-package-v2.json`
28. `new pipeline/harness/k0b03_v2/__init__.py`
29. `new pipeline/harness/k0b03_v2/canonical.py`
30. `new pipeline/harness/k0b03_v2/schema_validator.py`
31. `new pipeline/harness/k0b03_v2/registry_binding.py`
32. `new pipeline/harness/k0b03_v2/compiler.py`
33. `new pipeline/harness/k0b03_v2/scanner.py`
34. `new pipeline/harness/k0b03_v2/repository_guard.py`
35. `new pipeline/harness/k0b03_v2/tool_guard.py`
36. `new pipeline/harness/k0b03_v2/windows_job.py`
37. `new pipeline/harness/k0b03_v2/windows_appcontainer.py`
38. `new pipeline/harness/k0b03_v2/launcher.py`
39. `new pipeline/harness/k0b03_v2/lifecycle.py`
40. `new pipeline/harness/k0b03_v2/store.py`
41. `new pipeline/harness/k0b03_v2/compatibility.py`
42. `new pipeline/harness/k0b03_v2/attestations.py`
43. `new pipeline/harness/k0b03_v2/cli.py`
44. `new pipeline/harness/migrations/0008_k0b03_v2_remediation.sql`
45. `new pipeline/tests/k0b03_v2/fixture_support.py`
46. `new pipeline/tests/k0b03_v2/fixtures/coverage-map-v2.json`
47. `new pipeline/tests/k0b03_v2/fixtures/detector-vector-recipes-v2.json`
48. `new pipeline/tests/k0b03_v2/fixtures/contract-registry-attestation-vectors-v2.json`
49. `new pipeline/tests/k0b03_v2/fixtures/repository-tool-launcher-vectors-v2.json`
50. `new pipeline/tests/k0b03_v2/fixtures/lifecycle-recovery-vectors-v2.json`
51. `new pipeline/tests/k0b03_v2/fixtures/compatibility-migration-vectors-v2.json`
52. `new pipeline/tests/k0b03_v2/fixtures/toolchain-vectors-v2.json`
53. `new pipeline/tests/k0b03_v2/fixtures/compiled-output-expectations-v2.json`
54. `new pipeline/tests/k0b03_v2/fixtures/migration-preservation-seed-v2.json`
55. `new pipeline/tests/k0b03_v2/workers/controlled_effect_worker.py`
56. `new pipeline/tests/k0b03_v2/test_scanner.py`
57. `new pipeline/tests/k0b03_v2/test_contracts_registry_attestations.py`
58. `new pipeline/tests/k0b03_v2/test_repository_tool_launcher.py`
59. `new pipeline/tests/k0b03_v2/test_lifecycle.py`
60. `new pipeline/tests/k0b03_v2/test_migration_compatibility.py`
61. `new pipeline/tests/k0b03_v2/test_cli_toolchain.py`
62. `new pipeline/toolchain/k0b03_v2/invoke-v2.ps1`
63. `new pipeline/toolchain/k0b03_v2/toolchain-lock-v2.json`
64. `new pipeline/compiled/k0b03_v2/compiled-contract-manifest.json`
65. `new pipeline/compiled/k0b03_v2/compiled-detector-profile.json`
66. `new pipeline/compiled/k0b03_v2/compiled-hash-profile-map.json`
67. `new pipeline/compiled/k0b03_v2/compiled-repository-tool-policy.json`
68. `new pipeline/compiled/k0b03_v2/compiled-registry-event-bindings.json`
69. `new pipeline/compiled/k0b03_v2/compiled-attestation-boundary.json`
70. `new pipeline/compiled/k0b03_v2/compiled-coverage-map.json`

No existing path, state file, renderer, projection profile, status, or gate belongs to this candidate implementation inventory.

## 14. Checks, stop conditions, and later audit

The future implementation must stop on any baseline or finite-read pin mismatch, capability proof mismatch, existing target, hidden dependency, schema keyword outside the frozen validator vocabulary, scanner semantic outside the profile, registry or route shadowing, AppContainer or Job control failure, privilege mismatch, reparse ambiguity, canary mutation, outbound network or DNS attempt, test skip, A/B result difference, raw or reversible secret evidence, unresolved effect, cleanup failure, residue, or scope expansion.

After the complete implementation and validation, a fresh-context read-only non-author reviewer must independently inspect the exact implementation inventory, authored/compiled boundaries, 256-case coverage, evidence-bound dynamic claims, migration and enforcement proof. Reviewer approval is not owner closure. Only a later owner disposition may close the eight findings, and only a still later canonical transaction may adopt v2 and close the gate.

Runtime authority remains `none` throughout this design freeze.
