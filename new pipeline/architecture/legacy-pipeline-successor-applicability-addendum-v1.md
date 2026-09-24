# Legacy Pipeline successor applicability addendum

Addendum ID: `pipeline-v2.legacy-pipeline-successor-applicability-addendum-v1`; version `1.0.0`.

Recorded: 2026-09-24.

Status: `owner-approved documentation addendum; independent review, implementation, state transition, and runtime authority remain separate`.

This addendum explains how the pinned legacy Pipeline delta may inform Pipeline v2. It does not replace `PIPELINE_V2_ARCHITECTURE_PLAN.md` v0.16, edit any existing plan, activate a legacy prompt, implement K0b-03, perform K0b-04 or N1 work, change state or a gate, or grant runtime authority.

## 1. Bound inputs

| Input | SHA-256 | Bytes | Role |
|---|---|---:|---|
| `requests/legacy-pipeline-successor-and-plan-revision-approval-request-v1.yaml` | `1c664576325fafb0d2a7eb3f4eb8d6e1d5492c05666f64709a76c9c50f08e191` | 38427 | exact-scope request |
| `decisions/legacy-pipeline-successor-and-plan-revision-owner-disposition-v1.yaml` | `4288640e6dd2cd8573bd9d3c59790bcb62a0745ac6b84feb59b0613a38f290f5` | 8381 | owner scope and boundary disposition |
| `references/legacy-pipeline-successor-2026-09-23/manifest-v1.yaml` | `37a18ca9935948511eaf757660f4485bf11ea9f06a59158f42293f985fdee880` | 178435 | complete 170-path base/successor/exclusion binding |
| `evidence/legacy-pipeline-successor-applicability-v1.yaml` | `a5f210453868836c7ad7c977bcac3ed421e56c71eade7a04bcf0b622acb3ef4c` | 17797 | sole 21-row path-level applicability disposition |
| `PIPELINE_V2_DEVELOPMENT_PLAN-v0.14.md` | `7756786f7bfa141114c33daed510167607f248de753591d10191e889d11015f5` | 101354 | program-order successor |
| `PIPELINE_V2_ARCHITECTURE_PLAN.md` | `f5877a07daabbb2ad5d846890587fcb033f58fc0dba49b36668ae476294447b9` | 246369 | unchanged architecture base |

The Git baseline for this package is HEAD `84b390ef281a31caa119023c5dee61fceaa25439`, parent `1c7294ca2d3386e9eb07c2fbb507d239e5c09aeb`, tree `4f44ada7d7c1e1c3a273445a69f3236bccefca27`.

## 2. Source and precedence model

`old pipeline/**` is the immutable repository base snapshot. `C:/Projects/software_workflow` is an external read-only provenance source. The 21 overlay files preserve the changed active source bytes after the declared line-ending normalization. The manifest binds all 170 base and successor paths, all 21 overlay bytes, all 149 unchanged paths, 33 backup exclusions, four `.pytest_cache` exclusions, and 21 top-level recursive exclusion closures.

None of those three surfaces is a mutable Pipeline v2 authority. Their permitted flow is one-way:

```text
immutable base + pinned external raw bytes
  -> complete manifest and LF-normalized reference overlay
  -> one 21-row applicability disposition
  -> native Pipeline v2 plan/contract/profile/schema proposal
  -> independent review and separate exact-scope authority
  -> later implementation and evidence, if approved
```

The reverse flow is forbidden. Runtime code must not import the overlay, inspect the external source, choose a legacy prompt by path, or treat a legacy artifact name as an active registry entry. Copying prose into code or tests does not make it authoritative.

When inputs disagree, precedence is:

1. exact owner authority and canonical governance state for allowed effects;
2. approved Pipeline v2 architecture, registry, schema, migration, and profile sources for semantics;
3. the v0.14 development sequence and an approved phase/layer plan for scheduling;
4. the applicability evidence for destination and review routing;
5. the manifest and overlay as provenance evidence only.

A conflict at levels 1–3 is not resolved by selecting legacy wording. It blocks adoption until a new owner disposition and a native v2 successor resolve the conflict.

## 3. Single-source boundaries

`registry/alpha0/alpha0-routing-contract-v2.json` remains the sole current authored Alpha-0 event, producer, subscriber, terminal-policy, route, and phase-fence source. The overlay cannot add a route, event, status, agent, tool, transition, or terminal policy.

The complete base/successor/exclusion facts have one source: `manifest-v1.yaml`. The 21 primary applicability categories have one source: `legacy-pipeline-successor-applicability-v1.yaml`. Summaries in Markdown are non-authoritative projections and must not drift into alternative tables.

The current detector profile is still future K0b-03 work under a separate authority. Legacy secret, token, command, or attestation text cannot become a shadow detector/profile source. Existing event schemas, migrations 0001–0006, state, renderer, and K0b-02 artifacts remain immutable.

## 4. Applicability decisions

The evidence assigns exactly one primary destination to each changed path:

| Category | Paths | Meaning |
|---|---:|---|
| `already_covered_by_v2` | 3 | current v2 invariants already express the applicable safety property; later review verifies non-regression, not a new implementation claim |
| `required_for_K0b03` | 2 | only repository/tool/hash guard implications enter the K0b-03 planning delta |
| `required_for_K0b04` | 8 | dispatcher, toolchain, oracle, security, plan-only/read-only, and attestation findings require future K0b-04 disposition and evidence |
| `required_for_N1` | 8 | I/J layer contract changes require a native N1-00 migration matrix and approved layer plans |
| `deferred_to_later_layer` | 0 | no current row is silently parked without a named phase |
| `not_applicable` | 0 | no changed active source path was discarded without a disposition |

The primary category is routing, not a claim that every paragraph of the source belongs to that phase. Each future owner must select the smallest native invariant, name incompatible legacy behavior, and produce the evidence route recorded in the matrix.

## 5. K0b-03 boundary

Only two path-level deltas are routed primarily to K0b-03: object-specific raw-byte hash binding from J4 and declared repository/build-root policy boundaries from J8. Their admissible architectural consequences are limited to:

- select and persist the declared hash profile per object type; never substitute canonical-object hashing for a raw-byte identity or vice versa;
- bind every trusted repository/tool policy input by source identity and complete-file hash;
- treat tool presence or reachability as preflight evidence only, never as execution authority;
- reject an inferred build-root policy when the declared pinned source is absent or stale;
- keep path, tool, environment, egress, process, scanner, and authority guards independently conjunctive.

This does not add legacy J0, J4, or J8 prompts to the K0b-03 runtime. It does not add a toolchain manifest, acceptance-oracle compiler, F10 scenario, F15 call, provider adapter, or new repository read. Exact implementation paths, schemas, tests, locked environments, and temp targets still require a later request.

## 6. K0b-04 boundary

K0b-04 receives eight primary dispositions and the cross-cutting findings they represent. Before Alpha-0 evidence can rely on them, a later K0b-04 package must explicitly decide and test:

1. dispatcher preflight occurs before any agent or command cost;
2. toolchain reachability is measured over the whole declared scope, not a known example;
3. every acceptance oracle has a machine-resolvable owner and production path;
4. task-spec, manifest, command, expected-result, and committed-source hashes use named non-interchangeable profiles;
5. plan-only and live-read-only modes cannot report applied/deployed success;
6. reduced attestation guarantees form a complete non-overlapping partition and are allowed only by an explicit mode contract;
7. credentialed probes retain isolated-home and non-inherited-environment guarantees and record observed identity;
8. unknown rollout binding, tool state, external effect, or oracle state blocks rather than passes or retries without a bound budget.

These are review inputs, not results. This package executes neither F10 nor F15, produces no Alpha-0 disposition, and does not close `G-K0B04-F15-ATTESTATION-LIMIT` or any other gate.

## 7. N1-00 boundary

Before any affected P/R/A/T/I/Q-Alpha layer plan is approved, N1-00 must create a 21-row migration matrix keyed by the applicability evidence. Each row must include:

- legacy relative path and overlay SHA-256;
- applicability category and native v2 target contract;
- exclusive owner and registered consumer;
- explicit compatibility, replacement, rejection, or already-covered rationale;
- planned verification and approval receipt reference.

The matrix is a planning artifact, not an importer. It must not activate legacy agents or use legacy file names as runtime identities. Missing owner, consumer, native target, compatibility disposition, or verification route blocks the applicable layer-plan approval.

## 8. Ownership

| Owner | Owns | Does not own |
|---|---|---|
| Workspace owner | exact scope, conflict disposition, risk acceptance, phase continuation | automated route or runtime success |
| W0/program governance | v0.14 sequencing and review barriers | runtime registry semantics |
| Shared control/W1 | future K0b-03 admission, hash-profile selection, repository/tool/egress/process decisions | legacy prompt semantics or artifact bytes |
| Shared artifact/event plane | versioned evidence and future additive persistence | scheduling or applicability classification |
| K0b-04 proof owner | dispatcher/security/toolchain/oracle/attestation test disposition | K0b-03 implementation or N1 layer design |
| N1-00 layer-plan owners | native layer migration matrix and plans | rewriting completed Foundation evidence |
| Governance state renderer | later one-way state projection under separate authority | deriving a transition from this addendum |

## 9. Compatibility and abort rules

Completed K0a, K0b-01, and K0b-02 evidence remains valid at its pinned bytes. A newly discovered conflict is a forward finding; it cannot silently relabel historical evidence or mutate its scope.

Adoption stops on a manifest, overlay, source, category, owner, consumer, profile, plan, registry, schema, or evidence mismatch. It also stops if an excluded artifact is needed semantically, if external source bytes must be read at runtime, or if a proposed native requirement expands beyond the phase named by the applicability row.

Unknown applicability is not `not_applicable`. It is a blocking review outcome. A rejected legacy rule remains visible in the migration matrix with rationale; it is not removed from provenance.

## 10. Review and transition order

1. Commit this documentation/reference package without changing existing files, state, or gates.
2. Independently review the manifest, 21-row classification, v0.14 sequence, this addendum, and K0b-03 v1.1.
3. Under a later exact-hash authority, adopt any reviewed plan authorities and separately materialize any permitted predecessor gate transition.
4. Freeze K0b-03 implementation paths and inputs only after the review disposition; implement and validate under another authority.
5. Route the eight K0b-04 findings only after K0b-03 prerequisites are actually satisfied; do not run Alpha-0/F10/F15 from this package.
6. Create the N1-00 migration matrix only after K0b-05 permits continuation to N1.

`G-K0B03-UNTRUSTED-SHAPES` remains open. K0b-03 remains blocked in canonical state. K0b-04, K0b-05, and N1 do not progress. Runtime authority remains `none`.
