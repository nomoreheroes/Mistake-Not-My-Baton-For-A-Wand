# Pipeline v2 state projection

Machine source: [state.yaml](state.yaml) `8f8f3a966b5a`

Projection profile: [state-projection-profile-v1.yaml](state-projection-profile-v1.yaml) `7032748afe3e`

Program status: `governance_remediation_ready_for_containing_commit`. D0-05 becomes complete when this projection and its complete hash-reachable governance graph are tracked by the same validated commit. The commit SHA is intentionally not embedded in this projection.

## Active authority

- Final K0b-00 disposition: [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27`
- K0b-01 governance direction: [k0b-01-governance-remediation-owner-direction-v1.yaml](../decisions/k0b-01-governance-remediation-owner-direction-v1.yaml) `364a6941a216`
- K0b-01 plan: [k0b-01-planning-package-v1.3.md](../architecture/k0b-01-planning-package-v1.3.md) `4a039d27d13b`
- Frozen-draft reuse triage: [k0b-01-frozen-draft-reuse-triage-v1.yaml](../evidence/k0b-01-frozen-draft-reuse-triage-v1.yaml) `3976909ee305`

Supporting review evidence: [r1 dispatch reconciliation](../evidence/k0b-01-r1-review-dispatch-reconciliation-v1.yaml) `c1438f246cb3` and [r1 ledger append](../evidence/k0b-01-r1-review-ledger-append-v1.yaml) `e2eb12a33f72`. They preserve two approvals with zero open findings for the exact v1.2 hash; they do not approve v1.3. Remaining review calls: `0`.

## Root-plan status

- [PIPELINE_V2_ARCHITECTURE_PLAN.md](../PIPELINE_V2_ARCHITECTURE_PLAN.md) `f5877a07daab` remains the active hash-bound baseline with superseding K0b deltas. Its section 18.3 launch-method statement is superseded by [k0b-00-fixed-hybrid-manual-vscode-executor-profile-v1.yaml](../architecture/k0b-00-fixed-hybrid-manual-vscode-executor-profile-v1.yaml) `125a1e30e4ca`.
- [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` remains the active hash-bound baseline with successor work-item authorities. Its missing manual-VS-Code wording is superseded by the final K0b-00 disposition `544a6160fc27`.

## Work items

| sequence | work item | status | authority | open gates |
|---:|---|---|---|---|
| 1 | D0-01 | complete | [d0-01-decision-baseline-approval.yaml](../receipts/d0-01-decision-baseline-approval.yaml) `3cff717a14ab` | none |
| 2 | D0-02 | complete | [d0-02-layer-architecture-gate.yaml](../decisions/d0-02-layer-architecture-gate.yaml) `1bf92c755912` | none |
| 3 | D0-03_D0-04 | complete | [d0-04-legacy-relocation.yaml](../receipts/d0-04-legacy-relocation.yaml) `87d259ff0ccd` | none |
| 4 | D0-05 | complete_on_containing_commit | [k0b-01-governance-remediation-owner-direction-v1.yaml](../decisions/k0b-01-governance-remediation-owner-direction-v1.yaml) `364a6941a216` | G-D005-CONTAINING-COMMIT |
| 5 | D0-06 | complete | [d0-06-fixture-reproducibility-v1.yaml](../receipts/d0-06-fixture-reproducibility-v1.yaml) `dc3d9dead0e9` | none |
| 6 | K0a-00 | architecture_complete | [k0a-00-layer-architecture-approval-v1.yaml](../receipts/k0a-00-layer-architecture-approval-v1.yaml) `98411d2a98eb` | none |
| 7 | K0a-01 | implemented_validated | [k0a-01-corrective-validation-v2.yaml](../evidence/k0a-01-corrective-validation-v2.yaml) `4fe090ec2ed4` | none |
| 8 | K0a-02 | implemented_validated | [k0a-02-validation-v1.yaml](../evidence/k0a-02-validation-v1.yaml) `3c2385d28e38` | none |
| 9 | K0a-03 | implemented_validated | [k0a-03-manual-extension-owner-disposition-v1.yaml](../decisions/k0a-03-manual-extension-owner-disposition-v1.yaml) `870979d78a26` | none |
| 10 | K0b-00 | architecture_complete | [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27` | none |
| 11 | K0b-01 | planning_remediation | [k0b-01-planning-package-v1.3.md](../architecture/k0b-01-planning-package-v1.3.md) `4a039d27d13b` | G-D005-CONTAINING-COMMIT, G-K0B01-BINARY-SIZE, G-K0B01-HUMAN-SIGNOFF, G-K0B01-IMPLEMENTATION-DISPOSITION, G-K0B01-IMPLEMENTATION-LEDGER, G-K0B01-STATE-RENDERER, G-K0B01-TOOLCHAIN |
| 12 | K0b-02 | blocked | [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` | G-K0B02-K0B01-COMPLETE, G-K0B02-SINGLE-SOURCE-CONFIRMATION |
| 13 | K0b-03 | blocked | [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` | G-K0B03-K0B01-COMPLETE, G-K0B03-UNTRUSTED-SHAPES |
| 14 | K0b-04 | blocked | [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27` | G-K0B04-F15-ATTESTATION-LIMIT, G-K0B04-PREREQUISITES |
| 15 | K0b-05 | blocked | [k0b-00-final-architecture-package-owner-disposition-v1.yaml](../decisions/k0b-00-final-architecture-package-owner-disposition-v1.yaml) `544a6160fc27` | G-K0B05-F15-COMPLETE |
| 16 | N1 | blocked | [PIPELINE_V2_DEVELOPMENT_PLAN.md](../PIPELINE_V2_DEVELOPMENT_PLAN.md) `679a0bfa08d5` | G-N1-K0B-COMPLETE, G-N1-POLICY-LIMITS |

## Open gates

| gate | owner | status | blocks | closure condition |
|---|---|---|---|---|
| G-D005-CONTAINING-COMMIT | workspace_owner | ready | D0-05, K0b-01 | this_state_and_the_complete_hash_reachable_governance_graph_are_in_the_same_validated_commit |
| G-K0B01-BINARY-SIZE | workspace_owner | open_blocking | K0b-01_implementation | select_K0b_B02_and_recalculate_the_size_stressed_reference_without_threshold_storage_credit_or_third_phase_change |
| G-K0B01-HUMAN-SIGNOFF | workspace_owner | open_blocking | K0b-01_implementation | human_only_review_approves_exact_plan_v1_3_and_selected_K0b_B02_with_identity_and_capacity |
| G-K0B01-IMPLEMENTATION-DISPOSITION | workspace_owner | open_blocking | K0b-01_implementation | later_exact_hash_bound_owner_disposition_defines_new_write_and_validation_sets |
| G-K0B01-IMPLEMENTATION-LEDGER | Pipeline_governance | open_blocking | K0b-01_implementation | separate_implementation_invocation_schema_ledger_budget_and_historical_incident_record_exist |
| G-K0B01-STATE-RENDERER | Pipeline_governance | open_blocking | K0b-01_implementation | deterministic_renderer_and_projection_equivalence_check_exist |
| G-K0B01-TOOLCHAIN | Pipeline_governance | open_blocking | K0b-01_implementation | toolchain_and_CI_manifest_pins_Python_SQLite_lint_format_import_root_and_one_validation_entry_point |
| G-K0B02-K0B01-COMPLETE | K0b-01 | blocked_by_predecessor | K0b-02 | K0b_01_completion_receipt_exists |
| G-K0B02-SINGLE-SOURCE-CONFIRMATION | workspace_owner | future_open | K0b-02 | confirm_single_JSON_registry_and_projection_ownership_before_K0b_02 |
| G-K0B03-K0B01-COMPLETE | K0b-01 | blocked_by_predecessor | K0b-03 | K0b_01_completion_receipt_exists |
| G-K0B03-UNTRUSTED-SHAPES | K0b-03 | future_open | K0b-03_F10 | shape_entropy_JWT_Bearer_provider_token_base64_and_split_line_detectors_exist_and_scanner_is_documented_as_hygiene |
| G-K0B04-F15-ATTESTATION-LIMIT | K0b-04 | future_open | K0b-04_F15_conclusion | F15_conclusion_states_the_manual_transcript_and_model_attestation_limit |
| G-K0B04-PREREQUISITES | K0b-04 | blocked_by_predecessors | K0b-04 | K0b_01_K0b_02_and_K0b_03_required_gates_are_complete |
| G-K0B05-F15-COMPLETE | K0b-05 | blocked_by_predecessor | K0b-05 | exact_F15_phase_and_post_F15_closure_are_complete |
| G-N1-K0B-COMPLETE | N1 | blocked_by_predecessor | N1 | K0b_completion_and_owner_continue_or_pause_decision_exist |
| G-N1-POLICY-LIMITS | Pipeline_governance | future_open | N1 | context_and_failure_receipt_limits_are_versioned_policy_values_not_function_defaults |

## Superseded and frozen records

- [k0b-01-implementation-owner-disposition-v1.yaml](../decisions/k0b-01-implementation-owner-disposition-v1.yaml) `cdb87a83b5bc` is non-authoritative.
- [k0b-01-validation-v1.yaml](../evidence/k0b-01-validation-v1.yaml) `8a0485b0821b` is non-authoritative superseded draft evidence.
- [k0b-01-planning-package-v1.2.md](../architecture/k0b-01-planning-package-v1.2.md) `f6c297a11134` remains the exact subject of two valid r1 approvals but is superseded by v1.3 for future implementation.
- The 18-artifact frozen set is read-only. Reuse triage permits no whole-file reuse: 2 records are provenance-only and 16 artifacts require re-authoring from current authority.

## Effective scope

There is no runtime or implementation authority. Remaining design-review model calls: `0`. Access to forbidden roots and push, PR, deploy, or release operations are not authorized.
