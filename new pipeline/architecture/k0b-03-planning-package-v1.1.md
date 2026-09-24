# K0b-03 prerequisite and bounded planning package — legacy applicability overlay v1.1

Plan ID: `pipeline-v2.k0b-03-planning-package-v1.1`; version `1.1.0`.

Recorded: 2026-09-24.

Status: `bounded_non_authorizing_overlay_requires_independent_review_transition_and_implementation_authorities`.

This document is an immutable overlay on `k0b-03-planning-package-v1.md` v1.0.0. The effective planning input is v1 plus this file; v1 is not rewritten. If the two conflict, this overlay may narrow or make a guard fail closed, but it may not add runtime authority, a legacy runtime dependency, a state transition, or K0b-04/N1 execution.

## 1. Bound authority and inputs

| Input | SHA-256 | Bytes | Role |
|---|---|---:|---|
| `architecture/k0b-03-planning-package-v1.md` | `0ef7d61150cce6b407a8719b819589c180e3efc6fde55538d50f0d8ef94ca147` | 26523 | immutable base plan |
| `requests/legacy-pipeline-successor-and-plan-revision-approval-request-v1.yaml` | `1c664576325fafb0d2a7eb3f4eb8d6e1d5492c05666f64709a76c9c50f08e191` | 38427 | exact documentation authority request |
| `decisions/legacy-pipeline-successor-and-plan-revision-owner-disposition-v1.yaml` | `4288640e6dd2cd8573bd9d3c59790bcb62a0745ac6b84feb59b0613a38f290f5` | 8381 | owner scope disposition |
| `references/legacy-pipeline-successor-2026-09-23/manifest-v1.yaml` | `37a18ca9935948511eaf757660f4485bf11ea9f06a59158f42293f985fdee880` | 178435 | provenance and exclusion binding |
| `evidence/legacy-pipeline-successor-applicability-v1.yaml` | `a5f210453868836c7ad7c977bcac3ed421e56c71eade7a04bcf0b622acb3ef4c` | 17797 | sole 21-path applicability disposition |
| `architecture/legacy-pipeline-successor-applicability-addendum-v1.md` | `7422498e34f803116d04b95061b066dd200a7aa68393ecccf74c2978af02bd2b` | 11398 | source precedence and phase boundary |
| `PIPELINE_V2_DEVELOPMENT_PLAN-v0.14.md` | `7756786f7bfa141114c33daed510167607f248de753591d10191e889d11015f5` | 101354 | program sequence successor |

This overlay accepts two changed-path dispositions as primary K0b-03 planning inputs: `J4. Methodologist.md` and `J8. Static Analyzer.md`. It accepts cross-cutting attestation observations only as compatibility constraints on future guard evidence. The eight K0b-04 rows and eight N1 rows do not become K0b-03 implementation scope.

The applicability evidence must be independently reviewed before a future K0b-03 implementation scope is frozen. Presence of this plan or its containing commit is not that review receipt.

## 2. External source and overlay isolation

`C:/Projects/software_workflow`, `old pipeline/**`, and `references/legacy-pipeline-successor-2026-09-23/overlay/**` are forbidden runtime imports. No future K0b-03 package may:

- enumerate or read the external source during harness execution;
- open an overlay file to select a route, pattern, command, argument, policy, threshold, schema, or status;
- derive a tool allowlist, detector table, environment variable, egress target, process action, or hash profile from legacy prose;
- install the overlay as prompts or copy its agent roster into the active registry;
- treat an excluded backup, cache, database, executable, script, node module, editor directory, test workspace, or runtime artifact as semantic input.

The manifest and overlay are design provenance. A future implementation input manifest may cite their reviewed applicability receipt, not import their bytes into runtime. A need for runtime access is scope expansion and stops the package.

## 3. Typed hash-profile guard

The v1 requirement for exact file and artifact identity is tightened: every hash-bearing field must name an admitted `hash_profile_id` and object type. Profiles are not interchangeable.

The future guard must distinguish at least:

| Object | Required profile |
|---|---|
| executable, source file, task-spec file, lockfile, manifest file | SHA-256 over complete raw bytes |
| authored registry object where its canonical contract explicitly requires canonical JSON | the pinned canonical-object profile and version |
| artifact/version payload | the canonical artifact hash profile already owned by the artifact/event plane |
| tool invocation envelope | deterministic compiler profile over the typed envelope, not raw command prose |
| evidence bundle | ordered manifest profile naming every member identity and byte hash |

A consumer expecting one profile must reject a digest produced under another even if the hex length matches. Missing profile identity, unknown profile version, ambiguous text normalization, file replacement after hashing, mismatch between resolved and declared path, or disagreement between raw bytes and a compiled envelope blocks before execution or persistence.

The legacy J4 correction establishes only that its task-spec identity was raw bytes. It does not globally convert canonical-object identities to raw bytes. The future implementation must add positive and negative cross-profile substitution cases without changing the existing canonical hash authority.

## 4. Declared repository and tool-policy source

Repository/build-root policy must come from one pinned native v2 source declared by the future implementation contract. It may be a versioned toolchain manifest or a contract-owned equivalent, but it cannot be inferred from one `Cargo.toml`, `package.json`, `cabal.project`, build script, test name, or observed command.

The admitted policy input must name:

- repository role, root and canonical top-level;
- manifest and lockfile paths with complete-file hashes;
- exact executable identity, version and full-file hash;
- allowed target/discovery grammar and whether a task may add a target;
- allowed working directories and repository path classes;
- closed argument grammar, environment allowlist and output policy;
- owner and compatibility/version of the policy source.

Absent, stale, multiply active, case-aliased, path-escaped, or internally contradictory policy blocks. The guard must not repair or choose between sources. Updating the source requires a versioned successor and a separately authorized implementation input.

## 5. Reachability is not execution authority

A preflight may prove only that the declared tool identity resolves to the admitted path/hash/version under the constructed environment. It must not run the task validation command, install a dependency, query a provider, contact a registry, access an ambient credential, or infer that a command is safe because a binary exists.

Reachability, scanner result, hash match, schema validity, and attestation validity are independent necessary predicates. No one predicate can authorize another. The effect is admitted only when all applicable repository, path, tool, argument, CWD, environment, resource, egress, process, scanner, authority, and phase fences pass at the same pinned revision.

Content-derived commands, response files, shell interpolation, hooks, plugins, credential helpers, implicit configuration discovery, package-manager bootstrap, and ambient `PATH` substitution remain denied by v1.

## 6. Egress and oracle boundary

An acceptance or validation command may name an oracle; it never grants egress. An oracle or tool target is admissible only when its producer/owner, exact artifact or endpoint identity, terminal policy, evidence shape, and separately approved capability are resolvable from native v2 sources.

Unknown or unreachable oracle state blocks without executing a fallback. A missing binary is not permission to download it. A provider CLI `validate`, `plan`, `dry-run`, or read-only label is not proof of no external effect; its admitted egress and mutation semantics must be pinned by the future native contract and tested later.

The complete acceptance-oracle compiler and dispatcher preflight belong to K0b-04 disposition. K0b-03 owns only the guard interface that can reject an unresolved or unauthorized effect. This overlay does not create the oracle schema or run an oracle.

## 7. Attestation compatibility interface

Future K0b-03 guard evidence must not collapse reduced guarantees into a boolean `safe`. If an invocation contract later permits a reduced guarantee, the attestation must provide:

- exact schema/profile identity and hash;
- an exhaustive, non-overlapping partition of fields by guarantee level;
- the mode and rule that permits every reduction;
- non-reducible fields for any credentialed or externally meaningful effect;
- observed executable, environment, path, process and egress identities;
- a typed block for unknown, omitted, duplicated, or contradictory partition membership.

`agent_best_effort` cannot satisfy an OS-enforced requirement. A `plan_only`, `dry_run`, or `read_only` label does not reduce `isolated_home` or `inherit_environment` when any declared command can use credentials or observe a protected live target. Unknown effect state remains blocking.

The actual attestation-limit decision and its F10/F15 evidence belong to K0b-04 and `G-K0B04-F15-ATTESTATION-LIMIT`. This section only prevents the K0b-03 guard/evidence interface from making that future proof impossible or from treating a reduced guarantee as full enforcement.

## 8. Future implementation input requirements

In addition to v1 section 11, a later exact-scope implementation request must pin:

1. the independent review receipt for the manifest, applicability matrix, v0.14, addendum, and this overlay;
2. the native repository/tool-policy source and its complete-file hash;
3. the admitted hash-profile registry identities for every K0b-03 object type;
4. the exact compiler output fields that bind object type, profile, path, tool and authority revision;
5. the attestation compatibility schema boundary, while leaving K0b-04-only guarantee decisions unresolved;
6. negative tests proving external source and overlay paths cannot be runtime inputs;
7. the unchanged registry-v2, event-schema, migration, state, and renderer pins.

The request must still freeze every write path, read pin, locked environment, dependency, offline source, temp target, command, check, stop condition, and one-commit scope. This document supplies none of those implementation authorities.

## 9. Future validation delta

The later K0b-03 validation must add, without executing F10 or F15:

- raw-byte versus canonical-object cross-profile substitution is rejected;
- a hash computed before a file/path replacement cannot authorize the replacement;
- missing or conflicting tool-policy sources block before command compilation;
- a single manifest/build file cannot be used to infer undeclared target policy;
- tool reachability does not execute the tool or authorize dependency/network access;
- legacy external and overlay paths are denied as runtime inputs;
- clean scanner, valid hash or valid attestation alone cannot bypass any other guard;
- malformed guarantee partitions and unapproved reduced guarantees block;
- sanitized evidence contains profile and source bindings but no raw secret or excluded legacy content.

These tests require the same two fresh independent locked environments and zero provider/model/network/runtime publication effects required by v1. They are future requirements, not checks performed by this documentation package.

## 10. Gate and phase order

1. Commit this documentation/reference package with state and all gates unchanged.
2. Independently review the applicability package under separate authority.
3. If approved, prepare any separate renderer/state transition request on the then-current baseline; this package does not close `G-K0B03-K0B01-COMPLETE`.
4. Freeze and authorize K0b-03 implementation separately, then validate and audit it.
5. Keep `G-K0B03-UNTRUSTED-SHAPES` open until detector implementation, two-environment validation, explicit hygiene documentation, external audit, and a separate state transition are complete.
6. Route dispatcher/toolchain/oracle/attestation findings to K0b-04 only after K0b-03 prerequisites; do not run F10/F15 here.
7. Do not create the N1 migration matrix until K0b-05 authorizes continuation to N1.

## 11. Stop conditions

In addition to v1 section 14, stop on any mismatch in the 170-path manifest, 21 overlays, exclusions, applicability row count/category/owner, v0.14, addendum, or this overlay. Stop if a future change needs an excluded artifact, direct legacy runtime read, new semantic category, shadow registry/profile, existing-file edit, unapproved dependency, network access, temp target, repository code/test execution, state/gate mutation, model/provider call, runtime publication, or remote effect.

## 12. Retained non-authorizations

- no K0b-03 code, profile, migration, fixture, toolchain, locked environment, temp target, test execution, validation, completion, or audit claim;
- no F10, F15, Alpha-0, model, provider, network, dependency, runtime publication, or remote effect;
- no state, STATE.md, renderer, projection profile, status, or gate change;
- no legacy prompt, registry, agent roster, command, tool, environment, egress target, or runtime import activation;
- no K0b-04, K0b-05, or N1 progress;
- runtime authority remains `none`.
