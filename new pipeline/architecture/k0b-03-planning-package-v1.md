# K0b-03 prerequisite and bounded planning package

Plan ID: `pipeline-v2.k0b-03-planning-package-v1`; version `1.0.0`.

Status: `bounded_non_authorizing_requires_separate_transition_and_implementation_authorities`.

Owner boundaries: workspace owner, shared control/W1 Kernel, shared artifact/event plane, S, artifact/event publisher, and the separately approved governance state renderer.

This package prepares K0b-03 repository, worktree, path, tool, egress, secret, and process guards together with graceful abort and compatibility requirements. It does not implement them, run repository code or tests, create a migration or detector profile, change state or a gate, activate Alpha0/F10/F15, or grant runtime authority.

## 1. Bound authority and inputs

| Input | Complete-file SHA-256 | Bytes |
|---|---|---:|
| `new pipeline/requests/k0b-03-prerequisite-and-bounded-planning-approval-request-v1.yaml` | `296cf14c033e87d6f6c1ce1f0e1b6da51f424f6e3a7df1623765d85168427a7d` | 34654 |
| `new pipeline/decisions/k0b-03-transition-and-planning-owner-disposition-v1.yaml` | `9f19dc88c3d265ae8f8073f840ae3d84afd6f8ef87db69e650e782fd8ea8ff77` | 9317 |
| `new pipeline/evidence/k0b-03-predecessor-gate-closure-proposal-v1.yaml` | `f314d65b9ae5b3b0578792dc1a319e89cb3d122af118294b7a1f38402e12f0f2` | 5887 |
| `new pipeline/state/state.yaml` | `f94bbac7cede9d5da2b069a84ce3669dd3a1d66e45d1c71e2c365644f42cf269` | 84926 |
| `new pipeline/PIPELINE_V2_DEVELOPMENT_PLAN.md` | `679a0bfa08d5c249968fe03ce91d85f9205bab6851c2f09aa9efada3f687382d` | 97569 |
| `new pipeline/PIPELINE_V2_ARCHITECTURE_PLAN.md` | `f5877a07daabbb2ad5d846890587fcb033f58fc0dba49b36668ae476294447b9` | 246369 |
| `new pipeline/architecture/k0b-00-scope-envelope-v2.yaml` | `e839396d9199fa85e5474b3a45a852e7b6b59d81d6910ae67897f7dffe627cde` | 11872 |
| `new pipeline/architecture/k0b-00-shared-control-plane-delta-v1.md` | `8048df9a4b7726f1ad021ef569e02cd938e3fff47883664652185cade3c651af` | 31108 |
| `new pipeline/architecture/k0b-00-shared-control-plane-delta-v2.md` | `ce8c8a3160f52dae4f49d753f60ac2df202496c40697bca1d1cc5775908b17e3` | 26784 |
| `new pipeline/architecture/k0b-00-shared-artifact-event-plane-delta-v1.md` | `750d0bc8124faf59559bde60d320b6bc694dafe0755514312b57004172408240` | 39798 |
| `new pipeline/architecture/k0b-00-shared-artifact-event-plane-delta-v2.md` | `9586c4536144b612be58d6d01cc13f6437d31898c9bb40fb1c518602086a26ce` | 28613 |
| `new pipeline/architecture/k0b-00-s-layer-delta-v2.md` | `e40b57493262d40c1eb48157de9dca216702b063cf3ffd5649238cfefe1e8be3` | 24481 |
| `new pipeline/architecture/k0b-01-planning-package-v1.3.md` | `4a039d27d13b52553d3ec860f9c1bfdef489f95c43490d8763ca069656b874e4` | 15415 |
| `new pipeline/architecture/k0b-02-planning-package-v1.2.md` | `5f1c4be08a989f677affca71ec5b992453e302da7c24e5e034891f6bbd987cd6` | 4967 |
| `new pipeline/registry/alpha0/alpha0-routing-contract-v2.json` | `e6216a0eb36a7d90693d2e0d2251318d00d0bf38ef546a71fa6a586b9ed81dce` | 86209 |
| `new pipeline/receipts/k0b-01-implementation-completion-v1.yaml` | `c0f24a7c09cbd5d190073510de1f9fe159af8e086bd5f344fe0ffc8ffde243d1` | 15226 |

The request contains the complete finite 45-file read scope. A citation here does not authorize a new transitive semantic read. The owner confirmation is exact-hash-bound to the request and authorizes only this five-file documentation package and one local commit.

## 2. Entry state and prerequisite disposition

The verified Git baseline is HEAD `1c7294ca2d3386e9eb07c2fbb507d239e5c09aeb`, parent `c4b8b627cf32f43093b2b1da27c3a41a5788d4a8`, tree `dccb7b3f9fce715c9d0cfd00a28c9fb9f791b61f`.

K0b-02 is `implemented_validated_externally_audited_runtime_not_authorized`. K0b-03 remains `blocked`. Runtime authority is `none`.

The development-plan dependencies for K0b-03 are K0b-00 and K0b-01. The current HEAD also contains the preserved K0b-02 artifact/event and registry-v2 interfaces, but this does not reclassify K0b-02 as a formal predecessor.

`G-K0B03-K0B01-COMPLETE` has closure condition `K0b_01_completion_receipt_exists`. The final K0b-01 completion receipt exists at its pinned bytes, documents K0b-01 as implemented and validated with runtime not authorized, addresses the exact closure condition, and expressly does not perform an automatic gate or state transition. Therefore the condition is satisfied and closure is proposed, but the canonical gate remains `blocked_by_predecessor` until a later separate renderer/state authority materializes it.

`G-K0B03-UNTRUSTED-SHAPES` remains `future_open`. This package neither claims its condition is satisfied nor proposes its closure.

## 3. Scope and exclusions

The future implementation scope to be separately authorized is exactly:

- repository and worktree identity;
- canonical path, symlink, junction, and reparse-point handling;
- tool executable, argument, current-directory, environment, resource, and output guards;
- deny-by-default egress and provider boundaries;
- secret and untrusted-shape scanning;
- owned-process admission, cancellation, and result fencing;
- graceful abort and reconciliation;
- forward compatibility, backup, restore, quarantine, and recovery evidence.

K0b-03 has zero physical model/provider calls in its scope envelope. It does not execute F10 or F15. It does not import research, run Alpha0, publish a runtime checkpoint, modify a product repository, or create a remote effect.

General scheduling, production adapters, research-import capability, M automation, release actions, destructive history repair, and K0b-04/K0b-05/N1 work are out of scope.

## 4. Single sources and exclusive ownership

`new pipeline/registry/alpha0/alpha0-routing-contract-v2.json` is the sole current authored source for Alpha0 events, semantic producers, subscribers, terminal policies, S routes, and phase fences. Registry v1 remains immutable historical K0b-01 input and is not the current source.

The existing event schemas remain the canonical payload-shape sources. Compiler outputs, Python tables, tests, SQLite projections, evidence summaries, and Markdown do not become parallel authored registry truth.

The future K0b-03 implementation must introduce exactly one versioned authored detector profile for detector signatures, thresholds, limits, normalization rules, and profile identity. Its exact path and full implementation write inventory must be frozen by a later request. Python code may compile and enforce that profile but may not embed a divergent parallel pattern or threshold table.

Canonical runtime process state and immutable compatibility/recovery evidence belong in SQLite when runtime is separately authorized. `state.yaml` remains canonical governance state; `STATE.md` is its one-way renderer projection.

| Owner | Exclusive responsibility | Must not own |
|---|---|---|
| Workspace owner | exact-scope authority, incompatible migration, restore, risk acceptance, continuation | automated runtime decisions |
| Shared control / W1 Kernel | admission, guard result, scanner decision, run/abort/compatibility FSM, fencing | artifact/checkpoint bytes, semantic route invention |
| Shared artifact/event plane | event persistence, additive migration, compatibility/backup/restore/quarantine/recovery evidence | scheduling, semantic routing, tool selection |
| S | semantic route/fallback and monotonic route freeze/unfreeze | processes, filesystem paths, tools, persistence |
| Artifact/event publisher | enforce publication freeze from committed typed control result | secret classification or scope approval |
| Governance state renderer | one-way governance projection under separate authority | runtime activation or manual policy invention |

## 5. Repository, worktree, and path guards

Every filesystem or Git operation must admit a closed invocation envelope containing the exact Pipeline root, fixture root, repository role, top-level, branch/worktree identity, commit and tree, expected baseline, target allowlist, and permitted change set.

The guard resolves and compares canonical paths with `OrdinalIgnoreCase` Windows semantics where applicable. It rejects symlink, junction, mount/reparse, alias, relative traversal, case-alias, alternate Git-dir, and ancestor escape before any effect.

Pipeline Git and the canonical fixture are read-only. Future fixture writes are confined to a new independent coordination clone and its exact runtime paths. No shared checkout reset is allowed.

Task worktrees must physically exclude checkpoint history, runtime files, backups, WAL, and SHM. Q primary worktree and index must exclude all `/.pipeline/**`. A sparse-checkout or alternate-index bypass blocks admission.

Wrong root, wrong repository role, wrong top-level, wrong commit/tree, unapproved dirty or untracked path, changed allowlist, detached unexpected worktree, or target collision fails closed before mutation. File presence alone never proves identity or state.

Content-derived paths and commands, broad `.pipeline` ignores, attached SQLite databases, extension loading, untrusted triggers/PRAGMAs, shared-checkout reset, binary merge, and direct edits of a tracked checkpoint are forbidden.

## 6. Tool, environment, egress, and process guards

Each executable effect requires exact executable path, full-file hash and version, a closed argument grammar, admitted working directory, environment allowlist, timeout, CPU/memory/process limits, output-byte limit, and expected result enum.

Unknown switches, open-ended arguments, content-derived command fragments, shell interpolation, response files, ambient `PATH` substitution, implicit `PYTHONPATH`, package hooks, Git hooks, plugins, credential helpers, arbitrary configuration discovery, and direct SQL supplied by untrusted content are denied.

The runtime environment is constructed from an allowlist. Credential material is represented only by opaque approved references at a future executor boundary; raw secrets are never inserted into an invocation envelope, log, tracked evidence, or projection.

Egress is deny-by-default. K0b-03 validation itself requires no model/provider or arbitrary network access. Any later dependency acquisition would require an explicit hash-pinned host/file authority separate from harness execution; no such authority exists in this package.

Only a declared owned process tree can be started, observed, or cancelled. Cancellation is permitted only for an operation declared cancellable in its immutable envelope. The harness must not kill an arbitrary PID or assume that process disappearance means an external effect did not occur.

Started effects have durable intents and stable identities. Unknown, ambiguous, or unverifiable external state freezes further effects, preserves evidence, and yields a typed block rather than retry or fabricated success.

## 7. Detector profile and scanner semantics

The scanner accepts strict UTF-8 text only. Invalid UTF-8, input beyond the smaller of the caller-declared cap and 1,048,576 bytes, or more than 64 findings in one source blocks without truncation-and-pass. Comparisons and ordering are ordinal and locale-independent.

The authored detector profile must contain all of the following families.

### 7.1 Secret shape

Retain labelled-value detection for `api_key`, `access_token`, `auth_token`, `password`, `passwd`, `secret`, `authorization`, `private_key`, `client_secret`, and `aws_access_key_id`, accepting hyphen/underscore variants and a value length of 8 through 4096 admitted ASCII token characters. Retain PEM RSA, EC, OpenSSH, and generic private-key headers. Existing PII checks may remain but do not substitute for any K0b-03 family.

### 7.2 JWT

Detect a bounded compact three-segment base64url shape. The first and second segments contain 2 through 8192 base64url characters; the third contains 0 through 8192. Terminal padding may be tolerated only as defined by the profile. Total candidate length is at most 16384.

Decodable header/payload JSON strengthens classification but is not required to block a structurally valid three-segment candidate. Detection makes no assertion about signature validity, token authenticity, authorization, expiry, or issuer.

### 7.3 Bearer

Detect ASCII case-insensitive `Authorization` followed by optional horizontal whitespace, `:`, optional horizontal whitespace, `Bearer`, and a token. Also detect a bounded standalone `Bearer <token>` form. A token is 8 through 16384 non-whitespace token characters. The word `Bearer` alone is not a finding.

### 7.4 Provider token

The minimum v1 finite prefix table is:

- OpenAI: `sk-`, including the more specific `sk-proj-` and `sk-svcacct-`, with a suffix of at least 16 admitted token characters;
- Anthropic: `sk-ant-` with a suffix of at least 16 admitted token characters;
- GitHub: `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_`, or `github_pat_`, followed by 20 through 255 admitted characters;
- Slack: `xoxb-`, `xoxa-`, `xoxp-`, `xoxr-`, or `xoxs-`, followed by 10 through 255 admitted characters;
- AWS access-key ID: exactly `AKIA` or `ASIA` plus 16 uppercase alphanumeric characters;
- Google API key: `AIza` plus 35 ASCII alphanumeric, underscore, or hyphen characters.

Adding, removing, or weakening a signature requires a versioned profile successor. A match is a shape finding, not proof that the credential is live.

### 7.5 High entropy

Evaluate ASCII candidates 24 through 4096 characters long over the profile's admitted token alphabet. A candidate requires Shannon entropy of at least 4.0 bits per character and representation from at least three of lowercase, uppercase, digit, and non-alphanumeric token classes.

Unlabelled pure hexadecimal strings of exactly 40 or 64 characters are excluded so ordinary Git object IDs and SHA-256 pins do not block governance documents. This exclusion does not apply when a secret label or provider signature anchors the value.

### 7.6 Base64 and base64url

Detect base64/base64url candidates 24 through 16384 characters long with canonical padding or a permitted unpadded terminal form. Decode strictly and cap decoded bytes at 12288. A decoded strict-UTF-8 payload is scanned once for secret shape, JWT, Bearer, provider token, and high entropy.

Recursive decode is forbidden. Invalid encoding does not produce a decoded result. The encoded candidate remains independently eligible for high-entropy classification.

### 7.7 Split-line reconstruction

Maintain a bounded source map across at most four adjacent physical lines. Construct a candidate by removing only the line break and horizontal whitespace at the joined boundaries; do not remove internal characters. The combined candidate is at most 16384 characters.

Reconstruction is attempted only when the fragments collectively complete one of the named detector families: labelled secret/value, JWT, Bearer, provider token, high entropy, or base64/base64url. A finding maps back to the original byte spans and line boundaries. Whole-document whitespace stripping or arbitrary concatenation is forbidden.

### 7.8 Findings and redaction

Raw matched bytes, decoded secret material, token previews, and reversible encodings are never persisted or logged. A sanitized finding contains only detector category/version, source ID, original byte span or span set, match length, scanner-profile hash, safe source binding, and the typed block disposition.

Any finding blocks admission before model context, tool arguments/environment, DB/outbox content, projection/checkpoint publication, or log/evidence publication. The scanner can block but can never authorize a path, tool, capability, model/provider, egress target, approval, or publication.

The control result uses sanitized `error.security_policy` with terminal policy `block_run_and_enqueue_human`. A confirmed leakage incident additionally freezes the publisher and uses `meta.incident_detected` with `persist_incident_and_enqueue_W5`. Raw secret bytes are not copied into the incident record.

### 7.9 Mandatory hygiene boundary

> Scanner is heuristic hygiene only. It does not prove absence of secrets, prompt-injection safety, JWT/token authenticity, provenance, capability safety, or tool/egress compliance, and it does not satisfy F10 by itself.

F10 remains a separate K0b-04 adversarial proof of prompt-injection handling, secret boundaries, tool policy, and capability non-escalation before research-import capability. No F10 result may be inferred from scanner tests.

## 8. Scan and guard ordering

The future deterministic order is:

1. validate the authenticated closed request and exact authority/profile pins;
2. validate repository, worktree, canonical path, and permitted change set;
3. validate tool, executable, arguments, current directory, environment, resources, process, and egress policy;
4. admit only bounded strict-UTF-8 untrusted fields and run raw, split-line, entropy, token, JWT/Bearer, and base64 detectors;
5. compile an invocation or persistence request containing only typed allowed fields;
6. recheck the scanner immediately before a physical call/effect and before persistence/publication when the bytes have changed representation;
7. persist only sanitized guard/scanner results and stable evidence references;
8. stop on any stale pin, mismatch, finding, incompatible version, or unknown effect.

A clean scanner result does not bypass any other guard. A guard denial cannot be downgraded by model output, fixture content, projection text, replayed response, tool output, or Git metadata not produced by the trusted guard.

## 9. Abort and reconciliation

The exhaustive run states remain `created`, `running`, `waiting`, `completing`, `reconciliation_required`, `reconciling`, `aborting`, `completed`, `aborted`, `blocked`, and `blocked_over_limit`. `run.abort_requested` is an event, not a state.

An authenticated request at the current expected revision maps only `running|waiting -> aborting`. An identical replay returns the original disposition. A stale request or a request in any other state is rejected without mutation.

Abort processing must:

1. persist the request and expected revision;
2. freeze new deliveries and S routes;
3. fence prepared work and late results;
4. request cancellation only for declared cancellable owned operations;
5. reconcile every begun persistence, filesystem, Git, checkpoint, provider, or tool intent/result;
6. preserve partial artifacts, worktree, DB, transition history, and sanitized evidence;
7. emit `run.aborted` only when the graph is consistent and no effect is unknown.

Abort is not rollback. It does not delete the worktree or DB, rewrite history, reopen a sealed phase, or assume cancellation succeeded. An unknown effect yields typed terminal `run.blocked` and a human/W5 route, never fabricated `run.aborted` or ordinary retry.

A crash in `aborting` or `completing` transitions through `reconciliation_required -> reconciling` and may return only to the fenced prior semantic branch or a terminal block. It cannot silently resume ordinary delivery.

## 10. Compatibility, migration, backup, and restore

The logical K0b-03 migration is `k0b03.artifact_event.compatibility_evidence_v1`; the expected future file is `new pipeline/harness/migrations/0007_k0b03_compatibility_evidence_v1.sql`. Creation of that file is not authorized here.

Migrations 0001 through 0006 are immutable. The successor must be forward-only and additive, preserving existing rows, IDs, typed values, content hashes, event/version lineage, phase seals, publication identities, and schema history. A required table rebuild must use transactional copy plus row/count/hash, integrity, and foreign-key readback.

Before migration, create a consistent verified backup and record exact Pipeline, schema, registry, compiler, partition, executor, database, and migration pins. Integrity and foreign-key checks run before and after. Crash before commit leaves the prior schema; crash after commit is recognized by immutable migration identity/hash and reconciled without reapplying an ambiguous effect.

An older harness may open a newer DB only for bounded read-only diagnosis. Unknown, older, lossy, mixed, or substituted bindings block. In-place downgrade, destructive overwrite, attached-database migration, extension loading, and restore over an active path are forbidden.

Restore uses a verified backup, a new admitted target path, compatibility readback, and explicit human authorization. Resume requires the same Pipeline/schema/registry/compiler/partition/executor and authority pins and no unresolved security, publication, abort, migration, or recovery obligation.

Compatibility, backup/restore, quarantine, and recovery evidence belongs to the shared artifact/event plane. Shared control owns the admission decision and state transition, not evidence bytes.

## 11. Future artifacts and implementation authority boundary

A later implementation request must freeze exact paths, hashes or creation roles for:

- one versioned detector/security profile and contract package;
- one K0b-03 harness package for guards, scanner, abort, and compatibility control;
- the additive 0007 migration and its schema contract;
- compatibility, backup/restore, quarantine, and recovery evidence storage;
- one K0b-03 toolchain entry point;
- exact security/recovery tests and synthetic non-secret fixtures;
- implementation input manifest, session entry, compiler/validation receipts, completion and audit/materialization evidence;
- a separate renderer/state successor for actual gate and status transitions.

This plan does not assign the remaining implementation paths, create them, select a temp root, or authorize a dependency. Registry v2, current compiled outputs, migrations 0001–0006, K0b-02 code/evidence, state, STATE.md, and renderer v6 remain immutable inputs.

## 12. Future validation requirements

The separately authorized implementation must cover at least:

- positive and negative cases for every detector family;
- exact minimum/maximum lengths, entropy threshold, padding, invalid UTF-8, over-limit, finding-cap, chunk, line-boundary, four-line, and fifth-line rejection cases;
- JWT empty-signature shape, Bearer casing/whitespace, every provider prefix, Git/SHA false-positive exclusions, base64 single-decode, recursive-decode rejection, and original-offset mapping;
- proof that raw matches and decoded secrets do not enter logs, SQLite evidence, projections, checkpoints, exceptions, or test artifacts;
- wrong root, repository role, top-level, commit/tree, worktree, Git-dir, dirty/untracked set, sparse exclusion, symlink/junction/reparse escape, and target-collision cases;
- executable/hash/version, argument, CWD, environment, hook/plugin, resource, output, process ownership, cancellation, and egress denials;
- duplicate and stale abort, late result, crash in `aborting`/`completing`, known result reconciliation, ambiguous/unknown effect block, and preservation of worktree/DB/evidence;
- old-to-new migration, pre/post integrity and foreign-key checks, backup verification, crash before/after migration commit, old-reader no-write, newer-schema block, no downgrade, and new-path restore;
- exact registry-v2/event-schema bindings and absence of shadow authored truth;
- zero actual provider/model calls, zero real credentials, zero network effects during tests, zero remote Git effects, and zero runtime publications.

The implementation validation must run without skips in two fresh independent locked environments using `new pipeline/toolchain/k0b01/toolchain-lock-v1.json` or a separately approved versioned successor. It must pin host executable and packages, use an offline wheelhouse after any separately authorized acquisition, disable ambient caches/plugins/PYTHONPATH, and produce byte-identical deterministic compiler outputs. This package authorizes neither those environments nor wheel acquisition or temp targets.

F10 and real Alpha0/F15 scenarios are explicitly excluded from K0b-03 validation.

## 13. Gate-transition order

1. This documentation package records the satisfied predecessor condition and planning contract; canonical state and all gates remain unchanged.
2. A later exact-hash renderer/state authority may close only `G-K0B03-K0B01-COMPLETE`. `G-K0B03-UNTRUSTED-SHAPES` remains open and K0b-03 remains non-runtime.
3. A later exact-scope implementation authority may create the frozen K0b-03 source, contract, migration, tests, toolchain, and evidence paths and run the two locked validations.
4. Completion and external audit must confirm the detector/profile/wiring, explicit hygiene statement, guards, abort, compatibility, zero forbidden effects, and zero blocking findings.
5. Only another separate renderer/state authority may close `G-K0B03-UNTRUSTED-SHAPES` and materialize the final K0b-03 status.
6. K0b-04, K0b-05, and N1 remain unchanged throughout this sequence.

No evidence document, owner disposition, test result, or file existence closes a gate by itself.

## 14. Stop conditions

Stop before additional effect on any baseline, complete-file hash, size, authority, source-of-truth, root, worktree, path, environment, or scope mismatch.

Stop if implementation requires a new semantic input outside the approved finite read set, an existing-file edit not explicitly listed by its future authority, a shadow registry/profile truth, a migration rewrite, state/renderer change, unapproved dependency, network access, temp target, model/provider call, runtime publication, or remote Git effect.

Stop and preserve evidence on an active hook, signing requirement, executable/config drift, target collision, unrelated index/worktree change, unknown external effect, ambiguous migration/publication result, raw-secret exposure, or inability to retain the immutable predecessor chain.

Technical retry is permitted only inside a separately authorized unchanged exact scope after the prior attempt is proven to have no unknown effect.

## 15. Retained non-authorizations

- no K0b-03 implementation, repository code execution, or tests;
- no detector profile, contract, migration, toolchain, fixture, runtime, or temp-target creation;
- no state, STATE.md, renderer, profile, status, or gate mutation;
- no closure of either K0b-03 gate by this package;
- no K0b-04, K0b-05, or N1 progress;
- no Alpha0, F10, F15, real model/provider execution, runtime publication, or external side effect;
- no network, dependency acquisition, push, fetch, PR, merge, deploy, or release;
- runtime authority remains `none`.
