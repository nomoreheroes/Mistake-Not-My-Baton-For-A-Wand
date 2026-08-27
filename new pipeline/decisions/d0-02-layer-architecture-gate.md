# D0-02 — Layer Architecture Gate and reviewer contract

**Source YAML:** `new pipeline/decisions/d0-02-layer-architecture-gate.yaml`  
**Record ID:** `d0-02-layer-architecture-gate`  
**Status:** revision 2 validated; non-return findings N-01…N-12 applied as owner-disposition inputs; ready for owner disposition

## Gate invariant

No production prompt, contract or layer-specific runtime behavior may be implemented before the exact plan version and scope are approved. Only read-only old-Pipeline analysis and explicitly disposable spikes outside the baseline are exempt.

Plans are individual and just-in-time. A combined multi-layer plan does not satisfy the gate. Expansion requires a new plan version; unchanged sections retain their prior hashes in delta review.

## Required plan content

All 18 development-plan §4.2 categories must physically exist. An inapplicable section contains `N/A`, a reason and evidence; omission never means not applicable.

The plan includes scope/applicability, dispatcher/harness/worker boundaries, state/routing/artifact/event ownership, security, replay/recovery, current/deferred roster, downstream consumption, tests/evidence, migration notes and all applicable budgets.

## Budget scope and bootstrap enforcement

Complexity and call tiers bind a package or exact layer-plan scope, not an aggregate phase row:

| Invocation tier | Nominal | Worst case |
|---|---:|---:|
| light | 12 | 20 |
| standard | 30 | 50 |
| deep | exact owner-authorized values | exact owner-authorized values |

Both nominal and worst-case values must fit the tier. Every budget has a unique `package_id`; backlog IDs are only `covers_work_items`. Phase forecasts may aggregate several separately valid packages and therefore do not inherit one package label.

Counting is split explicitly:

- plan-production package: initial author, mandatory fresh-context reviewer and bounded author/reviewer revision-return calls, using the D0 `new_plan_call_model` or `delta_plan_call_model`;
- runtime package: S0/Layer0, workers, independent runtime reviewers, dialogue roles, retries and fallbacks.

Design calls occur before project DB runtime, so they are recorded in the Pipeline-Git ledger `new pipeline/ledgers/design-invocations.yaml`. A layer-plan receipt is invalid unless author and reviewer invocation refs resolve there; missing historical metadata is recorded as a gap and never invented.

Human tiers also bind both nominal and worst case. Every package declares its own profile, sessions, blocking decisions and active minutes in nominal/worst variants, plus `max_single_session_minutes` and `batchable_requests`:

| Human tier | Sessions | Blocking decisions | Active minutes | Max one session |
|---|---:|---:|---:|---:|
| light | 1 | 2 | 30 | 30 min |
| standard | 3 | 6 | 120 | 60 min |
| high-attention | exact owner-authorized values | exact | exact | default 90 min |

The pre-compiler cycle is explicitly broken:

- D0/K0-a use a versioned manual/reference worksheet;
- K0-b implements the compiler and proves equivalence with reference cases;
- from N1, a machine-generated forecast is mandatory.

This rule applies independently to invocation and human-attention budgets. A phase profile is only an informational envelope label derived from its unique packages. It does not itself create a capacity receipt. Each concrete `high_attention` package requires an exact owner-capacity receipt before execution; V1 has two such runtime packages.

## Binary-payload budget

G, Q runtime evidence and any scope creating or first persisting binary bytes declare object/media classes, nominal/worst counts, assumed mean and hard per-object size, planning aggregate, policy-permitted maximum aggregate, fail-closed runtime aggregate limit, publication amplification and an exact forecast binding. Per-object and aggregate caps are enforced independently.

Any changed number or assumption blocks the gate pending an owner route: narrow/batching, evidence-backed threshold increase, checkpoint-storage migration, or pause. A migration route reopens V2-D22. G closes the route before V1-01; Q closes it before implementing corresponding runtime evidence.

`N/A` is valid only when the contract prohibits binary persistence and references payload already budgeted by its producer.

## Independent reviewer

W0 appoints a reviewer who has not authored any prior or current version of the plan. The reviewer runs in a fresh read-only invocation/session without inherited author transcript or hidden summary, records identity/model/provider/profile/conflicts, and may emit findings and proposed dispositions only.

The reviewer cannot edit the plan, implement the layer or issue owner approval. Initial review may return the plan at most twice. A third autonomous loop is forbidden; unresolved disagreement goes to the owner.

The current D0-02 package has consumed revision-return round 2, the maximum. The second review verdict is `approve_with_changes`; those changes passed mechanical validation, a third autonomous return is forbidden and any remaining disagreement goes to the owner.

## Machine checks versus reviewer judgment

The deterministic validator is authoritative only for machine-checkable predicates, including:

- exact plan/parent/gate/registry/forecast hashes;
- presence of all 18 sections or explicit `N/A` reasons;
- distinct reviewer identity and review receipt;
- route/owner declarations;
- budget completeness and numeric caps/escalations;
- reconciled binary budget;
- no more than two returns;
- exact owner approval envelope and allowed scope.

Human/reviewer judgment remains explicit for:

- whether ownership overlap is actually safe;
- whether the roster is minimal and deferral honest;
- whether tests can falsify the architecture;
- whether scope is unambiguous and sufficient;
- whether security/replay/failure routes are coherent.

Each judgment produces either a typed finding or explicit pass. Deterministic code may not silently synthesize it.

## Approval receipt and staleness

Every receipt binds the exact plan, parent architecture, D0-02 gate contract, registries, forecast, review, budgets and implementation scope. It records the presence/`N/A` state of all plan sections.

Mandatory stale inputs are:

- plan SHA-256;
- parent-architecture SHA-256;
- gate-contract SHA-256;
- referenced registry versions/hashes;
- bound forecast SHA-256;
- complexity tier;
- approved phase/package/profiles.

The receipt uses version 1 of `registry/hash-profiles/canonical-yaml-v1.yaml`: restricted YAML 1.2 Core is normalized to NFC and serialized as RFC 8785 canonical JSON before SHA-256, excluding only `receipt_sha256`. The external approval envelope additionally records the complete-file SHA-256, avoiding an impossible self-referential hash.

The approval envelope schema lives in `new pipeline/registry/approval-envelope/v1.schema.yaml` and records actor, authority, timestamp, exact record/projection hashes, decision overrides and scope. For a D0 baseline, deterministic validation requires the exact ID set V2-D01…V2-D39 and exactly one record role each for dispositions, forecast, gate contract and checkpoint policy; object-level `uniqueItems` alone is not treated as sufficient.

## Gate status

Revision 0 was returned by the first independent review. The focused second review returned `approve_with_changes`; its required local changes are represented in revision 2 and passed mechanical verification. The later `d0-01-d0-02-owner-disposition-input-03.txt` is recorded as non-return findings N-01…N-12 because a third autonomous return is forbidden; accepted consistency corrections are applied here. This document does not self-approve—owner disposition remains the next authority step.
