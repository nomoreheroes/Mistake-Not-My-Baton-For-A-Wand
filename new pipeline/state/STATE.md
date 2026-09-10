# Pipeline v2 state projection

Machine source: [state.yaml](state.yaml) `f345b46b9011`

Projection profile: [state-projection-profile-v1.yaml](state-projection-profile-v1.yaml) `7032748afe3e`

Program status: `K0b_01_planning_approved_with_open_implementation_prerequisites`. D0-05, K0b-B02, the canonical-payload verifier gate, K0b-01 human-only planning signoff, and the K0b-01 toolchain gate are closed. Three K0b-01 implementation prerequisites remain open; runtime and implementation authority remain absent.

## Active authority

- Final K0b-00 disposition: [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27`
- K0b-01 governance direction: [k0b-01-governance-remediation-owner-direction-v1.yaml](../decisions/k0b-01-governance-remediation-owner-direction-v1.yaml) `364a6941a216`
- Governance-hardening request: [pipeline-v2-governance-hardening-approval-request-v1.yaml](../requests/pipeline-v2-governance-hardening-approval-request-v1.yaml) `1569b1ff1588`
- Governance-hardening owner disposition: [pipeline-v2-governance-hardening-owner-disposition-v1.yaml](../decisions/pipeline-v2-governance-hardening-owner-disposition-v1.yaml) `06fdeda5f0cf`
- Two-step authority-confirmation profile: [v1.yaml](../registry/authority-confirmation/v1.yaml) `b597423cb206`
- Canonical hash-profile remediation gate: [d0-canonical-hash-profile-remediation-gate-v1.yaml](../decisions/d0-canonical-hash-profile-remediation-gate-v1.yaml) `ad24abd94653`
- Canonical YAML verifier owner disposition: [d0-canonical-yaml-v1-verifier-owner-disposition-v1.yaml](../decisions/d0-canonical-yaml-v1-verifier-owner-disposition-v1.yaml) `b00d66e41d50`
- Canonical YAML verifier contract: [canonical-yaml-v1-verifier-contract-v1.yaml](../registry/hash-profiles/canonical-yaml-v1-verifier-contract-v1.yaml) `e091a9efb5d8`
- Canonical YAML verifier toolchain: [canonical-yaml-v1-verifier-toolchain-v1.yaml](../registry/hash-profiles/canonical-yaml-v1-verifier-toolchain-v1.yaml) `43f2778ebd28`
- Canonical YAML effective-status successor: [canonical-yaml-v1-status-v2.yaml](../registry/hash-profiles/canonical-yaml-v1-status-v2.yaml) `88881da22308`
- Canonical YAML validation: [d0-canonical-yaml-v1-validation-v1.yaml](../evidence/d0-canonical-yaml-v1-validation-v1.yaml) `4a4798989fef`
- Canonical claim reconciliation: [d0-canonical-payload-claim-reconciliation-v1.yaml](../evidence/d0-canonical-payload-claim-reconciliation-v1.yaml) `1e80b1f3dbd4`
- Canonical verifier gate closure: [d0-canonical-yaml-v1-gate-closure-v1.yaml](../evidence/d0-canonical-yaml-v1-gate-closure-v1.yaml) `cc88ba85a81b`
- D0-02 external-approval backlink: [d0-02-external-approval-backlink-v1.yaml](../evidence/d0-02-external-approval-backlink-v1.yaml) `d0d2a81dff49`
- Prospective design-review independence profile: [v2.yaml](../registry/design-review-independence/v2.yaml) `8e9910688190`
- K0b-01 plan: [k0b-01-planning-package-v1.3.md](../architecture/k0b-01-planning-package-v1.3.md) `4a039d27d13b`
- K0b-B02 owner selection: [k0b-01-b02-binary-budget-owner-disposition-v1.yaml](../decisions/k0b-01-b02-binary-budget-owner-disposition-v1.yaml) `349997f22c6f`
- K0b-B02 recalculation: [k0b-01-b02-binary-size-recalculation-v1.yaml](../evidence/k0b-01-b02-binary-size-recalculation-v1.yaml) `5ebc6ba23898`
- K0b-01 toolchain authority: [k0b-01-toolchain-completeness-remediation-and-gate-closure-approval-request-v1.yaml](../requests/k0b-01-toolchain-completeness-remediation-and-gate-closure-approval-request-v1.yaml) `ce0b19cb99f1`
- K0b-01 toolchain/CI prerequisite manifest: [toolchain-lock-v1.json](../toolchain/k0b01/toolchain-lock-v1.json) `3ba58d66cb33`; this does not claim that CI exists or has run.
- K0b-01 toolchain validation v2: [k0b-01-toolchain-validation-v2.yaml](../evidence/k0b-01-toolchain-validation-v2.yaml) `cf48abf5b24c`
- K0b-01 toolchain gate closure: [k0b-01-toolchain-gate-closure-v1.yaml](../evidence/k0b-01-toolchain-gate-closure-v1.yaml) `060fc2f7dc8e`
- Frozen-draft reuse triage: [k0b-01-frozen-draft-reuse-triage-v1.yaml](../evidence/k0b-01-frozen-draft-reuse-triage-v1.yaml) `3976909ee305`
- Frozen-draft triage clarification: [k0b-01-frozen-draft-reuse-triage-clarification-v1.yaml](../evidence/k0b-01-frozen-draft-reuse-triage-clarification-v1.yaml) `2956de3d9485`

Supporting review evidence: [r1 dispatch reconciliation](../evidence/k0b-01-r1-review-dispatch-reconciliation-v1.yaml) `c1438f246cb3` and [r1 ledger append](../evidence/k0b-01-r1-review-ledger-append-v1.yaml) `e2eb12a33f72` preserve two approvals with zero open findings for the exact v1.2 hash. [Human-only review](../reviews/k0b-01-human-only-review-v1.yaml) `522c3b0e5227` approves exact v1.3 and selected K0b-B02-A with zero blocking and five non-blocking findings carried forward. Remaining review calls: `0`.

## Root-plan status

- [PIPELINE_V2_ARCHITECTURE_PLAN.md](../PIPELINE_V2_ARCHITECTURE_PLAN.md) `f5877a07daab` remains the active hash-bound baseline with superseding K0b deltas. Its section 18.3 launch-method statement is superseded by [k0b-00-fixed-hybrid-manual-vscode-executor-profile-v1.yaml](../architecture/k0b-00-fixed-hybrid-manual-vscode-executor-profile-v1.yaml) `125a1e30e4ca`.
- [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` remains the active hash-bound baseline with successor work-item authorities. Its missing manual-VS-Code wording is superseded by the final K0b-00 disposition `544a6160fc27`.

## Work items

| sequence | work item | status | authority | open gates |
|---:|---|---|---|---|
| 1 | D0-01 | complete | [d0-01-decision-baseline-approval.yaml](../receipts/d0-01-decision-baseline-approval.yaml) `3cff717a14ab` | none |
| 2 | D0-02 | complete | [d0-02-layer-architecture-gate.yaml](../decisions/d0-02-layer-architecture-gate.yaml) `1bf92c755912` | none |
| 3 | D0-03_D0-04 | complete | [d0-04-legacy-relocation.yaml](../receipts/d0-04-legacy-relocation.yaml) `87d259ff0ccd` | none |
| 4 | D0-05 | complete | [k0b-01-governance-remediation-owner-direction-v1.yaml](../decisions/k0b-01-governance-remediation-owner-direction-v1.yaml) `364a6941a216` | none |
| 5 | D0-06 | complete | [d0-06-fixture-reproducibility-v1.yaml](../receipts/d0-06-fixture-reproducibility-v1.yaml) `dc3d9dead0e9` | none |
| 6 | K0a-00 | architecture_complete | [k0a-00-layer-architecture-approval-v1.yaml](../receipts/k0a-00-layer-architecture-approval-v1.yaml) `98411d2a98eb` | none |
| 7 | K0a-01 | implemented_validated | [k0a-01-corrective-validation-v2.yaml](../evidence/k0a-01-corrective-validation-v2.yaml) `4fe090ec2ed4` | none |
| 8 | K0a-02 | implemented_validated | [k0a-02-validation-v1.yaml](../evidence/k0a-02-validation-v1.yaml) `3c2385d28e38` | none |
| 9 | K0a-03 | implemented_validated | [k0a-03-manual-extension-owner-disposition-v1.yaml](../decisions/k0a-03-manual-extension-owner-disposition-v1.yaml) `870979d78a26` | none |
| 10 | K0b-00 | architecture_complete | [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27` | none |
| 11 | K0b-01 | planning_approved_implementation_blocked | [k0b-01-planning-package-v1.3.md](../architecture/k0b-01-planning-package-v1.3.md) `4a039d27d13b` | G-K0B01-IMPLEMENTATION-DISPOSITION, G-K0B01-IMPLEMENTATION-LEDGER, G-K0B01-STATE-RENDERER |
| 12 | K0b-02 | blocked | [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` | G-K0B02-K0B01-COMPLETE, G-K0B02-SINGLE-SOURCE-CONFIRMATION |
| 13 | K0b-03 | blocked | [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` | G-K0B03-K0B01-COMPLETE, G-K0B03-UNTRUSTED-SHAPES |
| 14 | K0b-04 | blocked | [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27` | G-K0B04-F15-ATTESTATION-LIMIT, G-K0B04-PREREQUISITES |
| 15 | K0b-05 | blocked | [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27` | G-K0B05-F15-COMPLETE |
| 16 | N1 | blocked | [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` | G-N1-K0B-COMPLETE, G-N1-POLICY-LIMITS |

## Open gates

| gate | owner | status | blocks | closure condition |
|---|---|---|---|---|
| G-K0B01-IMPLEMENTATION-DISPOSITION | workspace_owner | open_blocking | K0b-01_implementation | later_exact_hash_bound_owner_disposition_defines_new_write_and_validation_sets |
| G-K0B01-IMPLEMENTATION-LEDGER | Pipeline_governance | open_blocking | K0b-01_implementation | separate_implementation_invocation_schema_ledger_budget_and_historical_incident_record_exist |
| G-K0B01-STATE-RENDERER | Pipeline_governance | open_blocking | K0b-01_implementation | deterministic_renderer_and_projection_equivalence_check_exist |
| G-K0B02-K0B01-COMPLETE | K0b-01 | blocked_by_predecessor | K0b-02 | K0b_01_completion_receipt_exists |
| G-K0B02-SINGLE-SOURCE-CONFIRMATION | workspace_owner | future_open | K0b-02 | confirm_single_JSON_registry_and_projection_ownership_before_K0b_02 |
| G-K0B03-K0B01-COMPLETE | K0b-01 | blocked_by_predecessor | K0b-03 | K0b_01_completion_receipt_exists |
| G-K0B03-UNTRUSTED-SHAPES | K0b-03 | future_open | K0b-03_F10 | shape_entropy_JWT_Bearer_provider_token_base64_and_split_line_detectors_exist_and_scanner_is_documented_as_hygiene |
| G-K0B04-F15-ATTESTATION-LIMIT | K0b-04 | future_open | K0b-04_F15_conclusion | F15_conclusion_states_the_manual_transcript_and_model_attestation_limit |
| G-K0B04-PREREQUISITES | K0b-04 | blocked_by_predecessors | K0b-04 | K0b_01_K0b_02_and_K0b_03_required_gates_are_complete |
| G-K0B05-F15-COMPLETE | K0b-05 | blocked_by_predecessor | K0b-05 | exact_F15_phase_and_post_F15_closure_are_complete |
| G-N1-K0B-COMPLETE | N1 | blocked_by_predecessor | N1 | K0b_completion_and_owner_continue_or_pause_decision_exist |
| G-N1-POLICY-LIMITS | Pipeline_governance | future_open | N1 | context_and_failure_receipt_limits_are_versioned_policy_values_not_function_defaults |

## Closed gates

- `G-K0B01-HUMAN-SIGNOFF`: closed by [human-only review](../reviews/k0b-01-human-only-review-v1.yaml) `522c3b0e5227` and [closure evidence](../evidence/k0b-01-human-signoff-gate-closure-v1.yaml) `34354f8dc56f`. Verdict: `APPROVE`; blocking findings: `0`; non-blocking findings carried forward: `5`.
- `G-K0B01-TOOLCHAIN`: closed by the exact [toolchain/CI prerequisite manifest](../toolchain/k0b01/toolchain-lock-v1.json) `3ba58d66cb33`, [two-environment validation v2](../evidence/k0b-01-toolchain-validation-v2.yaml) `cf48abf5b24c`, and [closure evidence](../evidence/k0b-01-toolchain-gate-closure-v1.yaml) `060fc2f7dc8e`. Python, SQLite, Ruff lint/format, import-root strategy, and one validation entry point are pinned; CI existence or execution is not claimed.
- `G-D0-CANONICAL-HASH-PROFILE-VERIFIER`: closed through the authorized implement-and-validate route. The fixed 27-vector suite and 10 test methods pass; all 6 primary claims and 4 derivative occurrences match with zero discrepancies.
- `G-D005-CONTAINING-COMMIT`: closed by commit `45536507a469403b4878d273b661fe3a1d2c9573`, tree `00fa73a15dc6b402b00af0426d54f02c7f8c0b64`.
- `G-K0B01-BINARY-SIZE`: closed by K0b-B02-A. The selected runtime-phase pack is `1,033,895,936` bytes with `39,845,888` bytes of margin under the unchanged `1 GiB` phase limit.

## Superseded and frozen records

- [canonical-yaml-v1.yaml](../registry/hash-profiles/canonical-yaml-v1.yaml) `46597d916fdc` remains byte-unchanged with embedded status `proposed_for_owner_approval`; [canonical-yaml-v1-status-v2.yaml](../registry/hash-profiles/canonical-yaml-v1-status-v2.yaml) `88881da22308` makes its effective status `active_machine_verified`. Existing complete-file hashes are unaffected. All 6 known primary claims and 4 derivative occurrences were machine-verified without rewriting historical sources.
- [k0b-01-implementation-owner-disposition-v1.yaml](../decisions/k0b-01-implementation-owner-disposition-v1.yaml) `cdb87a83b5bc` is non-authoritative.
- [k0b-01-validation-v1.yaml](../evidence/k0b-01-validation-v1.yaml) `8a0485b0821b` is non-authoritative superseded draft evidence.
- [k0b-01-planning-package-v1.2.md](../architecture/k0b-01-planning-package-v1.2.md) `f6c297a11134` remains the exact subject of two valid r1 approvals but is superseded by v1.3 for future implementation.
- The 18-artifact frozen set is read-only. The clarification records that additive migration was conditionally permitted by plan v1.0 and became unambiguously obsolete under v1.2; reuse triage still permits no whole-file reuse: 2 records are provenance-only and 16 artifacts require re-authoring from current authority.

## Effective scope

K0b-B02, D0 canonical-payload verifier remediation, human-only K0b-01 planning signoff, and the K0b-01 toolchain prerequisite are complete. The five non-blocking human findings remain mandatory carry-forward inputs: publication count `34` is reforecast-sensitive; F15 needs an authoritative worst-case object count; future budget evidence must expose all three §6 quantities and mean size; forecast-v3/reconciliation-v3 hard-budget inputs need exact hash provenance; and the later implementation disposition must give the state-renderer gate authoritative support while enumerating all five gates present at review time. Three K0b-01 prerequisites remain open. There is no K0b-01 runtime or implementation authority. Remaining design-review model calls: `0`. Access to forbidden roots and push, PR, deploy, or release operations are not authorized.
