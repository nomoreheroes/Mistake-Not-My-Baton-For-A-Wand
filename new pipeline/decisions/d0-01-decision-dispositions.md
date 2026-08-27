# D0-01 — Proposed dispositions V2-D01…V2-D39

**Status:** revision 2 plus accepted non-return findings N-01…N-12; all 39 decisions ready for owner disposition  
**Owner:** human owner  
**Architecture source:** `PIPELINE_V2_ARCHITECTURE_PLAN.md` v0.16, §23

All 39 decisions remain proposed as `accepted`; none is silently deferred. This is not yet an owner approval. The second independent review returned `approve_with_changes`; the listed changes passed mechanical validation, so the former blocked set V2-D01/D04/D22/D33/D38 now joins the other 34 for owner disposition. The later N-01…N-12 source is treated as an owner-disposition input, not a prohibited third review-return; its consistency corrections do not change the meaning of any decision. Deferred runtime capabilities remain scoped inside accepted rollout decisions and retain explicit activation triggers.

| ID | Proposed disposition | Rationale / condition |
|---|---|---|
| V2-D01 | accepted | Ten layer owners plus S0 remain distinct; the independently reviewed forecast treats them as a staged program with K0-b/N1 continuation gates. |
| V2-D02 | accepted | One SQLite per project provides transactional process memory and queryable lineage without a premature distributed store. |
| V2-D03 | accepted | Key decisions get YAML+MD projections; working history stays canonical in SQLite and its governed checkpoint. |
| V2-D04 | accepted | Forensic replay requires logical replay points and a tracked clean checkpoint; exact per-project-chain limits are canonical in `registry/checkpoint-budget-policy/v1.yaml`. |
| V2-D05 | accepted | All handoff is event-driven and observable; direct agent transfer is forbidden. |
| V2-D06 | accepted | Only deterministic harness code writes runtime state; LLMs return validated proposals. |
| V2-D07 | accepted | Python CLI/library fits SQLite/Git tooling, Windows and Visual Studio. |
| V2-D08 | accepted | Safe reversible work is autonomous; risky side effects and owner decisions remain HITL. |
| V2-D09 | accepted | Adoption/usability are operational requirements for internal software. |
| V2-D10 | accepted | Q reconstructs from primary sources and independent evidence, not I self-report. |
| V2-D11 | accepted | Meta changes require separate approval to implement and to publish. |
| V2-D12 | accepted | Root Pipeline Git ignores `/projects/`; each product owns its own Git. |
| V2-D13 | accepted | Normal runs require a committed Pipeline pin; dirty mode records an exact diff hash. |
| V2-D14 | accepted | Registry/migrations are executable authority; plans do not duplicate schemas. |
| V2-D15 | accepted | Elm is the default direction for applicable stateful UI; exact registry predicates and evidence thresholds require owner disposition at S1-00. |
| V2-D16 | accepted | G creative and structural contexts remain isolated until explicit mapping. |
| V2-D17 | accepted | P1–P20 become enforceable language profiles; P8/P20 remain blocking. |
| V2-D18 | accepted | Inventory, honest sampling and lossless sharding prevent claims about unread scope. |
| V2-D19 | accepted | Tools are pinned, bounded and deny-by-default for hooks/network. |
| V2-D20 | accepted | Product/research content is data and cannot grant capabilities or impersonate approval. |
| V2-D21 | accepted | Pre-context egress/secret controls are required because replay data inherits Git retention. |
| V2-D22 | accepted | Artifact identity uses version IDs; relations stay relational and binary payload stays in SQLite for alpha only while V2-D04 remains viable. A storage migration automatically reopens this decision. |
| V2-D23 | accepted | Harness/registry fixes use an explicit M5h red→green track. |
| V2-D24 | accepted | This accepts the rollout shape; continuation beyond K0-b and N1 remains separately gated by K0b-05, N1-03 and V2-D39. |
| V2-D25 | accepted | Exact nominal routing is compiled; ambiguity activates the owning Layer0. |
| V2-D26 | accepted | External worktrees isolate changes and only coordination materializes the checkpoint. |
| V2-D27 | accepted | Pipeline/schema binding and forward migrations make DB evolution recoverable. |
| V2-D28 | accepted | New Swarm is greenfield; legacy content is untrusted research evidence only. |
| V2-D29 | accepted | Pipeline/DB rollback and product rollback remain separate domains and tests. |
| V2-D30 | accepted | Alpha implements only events with an executable subscriber or terminal policy. |
| V2-D31 | accepted | Readiness requires exact downstream consumption and defect→revision evidence. |
| V2-D32 | accepted | Physical legacy relocation and product hygiene are complete; capability enforcement remains a Foundation test. |
| V2-D33 | accepted | Individual just-in-time plans, finite review, design-invocation ledger and binary budgets balance depth with time-to-runtime; the revised gate contract passed focused review with mechanically validated changes. |
| V2-D34 | accepted | V1 failure revises owners, honestly narrows scope or pauses; downstream work cannot hide it. |
| V2-D35 | accepted | P supplies facts, A1 evaluates policy, A0 routes and A8 alone grants exceptions; exact registry predicates and evidence thresholds require owner disposition at S1-00. |
| V2-D36 | accepted | Owner-first creative triads improve elicitation without silently promoting agent proposals. |
| V2-D37 | accepted | Irrecoverable raw telemetry must start in K0-a; this decision may not be deferred. |
| V2-D38 | accepted | Pre-run model/human budgets include plan-production and runtime packages; every concrete high-attention package needs an exact capacity receipt, while the phase label is informational. |
| V2-D39 | accepted | Full, proven Core-6 or pause are honest post-N1 routes; reduced scope is not full success. |

## Exact V2-D04 parameters

The machine-readable authority is `new pipeline/registry/checkpoint-budget-policy/v1.yaml`; the numbers below are a human-readable projection, not a second source of truth.

- `max_checkpoint_bytes`: 104,857,600 (100 MiB)
- `max_projected_pack_growth_per_phase`: 1,073,741,824 (1 GiB)
- `max_publications_per_run`: 12
- `max_publication_p95_seconds`: 10
- `max_clean_clone_restore_seconds`: 120
- warning/hard ratios: 0.5 / 1.0
- unpublished window: 10 replay points / 5 minutes / 32 MiB
- last cheap migration gate: V1-00 before V1-01

These limits preserve SQLite-in-Git as the current hypothesis. They do not authorize automatic CAS/LFS migration. K0-b measurement and G/Q binary-budget reconciliation remain blocking inputs to any threshold change or migration route. If the owner selects `migrate_checkpoint_storage`, V2-D22 is automatically reopened.

## Existing implementation evidence

- V2-D12: root `/projects/` ignore exists.
- V2-D32: physical relocation and product-tree hygiene are recorded in `receipts/d0-04-legacy-relocation.{yaml,md}`; runtime access enforcement is still pending K0-b.
- V2-D33: the proposed reviewer/gate contract is recorded in `d0-02-layer-architecture-gate.{yaml,md}`.

## Approval required

The owner must approve the exact finalized record/projection hashes for all 39 decisions through the external approval envelope or return modified decision IDs with replacement dispositions and rationale. The envelope validator requires the exact V2-D01…D39 ID set plus forecast, gate-contract and checkpoint-policy records. Until then `owner_approved = 0`, and K0-a remains blocked by the Decision baseline.
