"""Static regression checks for the J14-centered infra prompt contract."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class InfraPromptContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.j0 = read("J0. Dispatcher.md")
        cls.j8 = read("J8. Static Analyzer.md")
        cls.j9 = read("J9. Dependency Auditor.md")
        cls.j9b = read("J9b. Lockfile Verifier.md")
        cls.j11 = read("J11. Documenter.md")
        cls.j14 = read("J14. Infra Methodologist.md")
        cls.j15 = read("J15. Infra Coder.md")
        cls.j16 = read("J16. Infra Deployer.md")
        cls.j17 = read("J17. Infra Tester.md")
        cls.shared = read("J14-J0-J16-J17 Generation And State Schemas.md")
        cls.architecture = read("J Layer - Architecture Plan.md")

    def test_manual_validation_binding_is_structured_and_versioned(self):
        self.assertIn('schema_version: "2.2"', self.j14)
        self.assertIn('invocation_id: "<UUID echoed verbatim from J0', self.j14)
        self.assertIn("manual_decision_ref:", self.j14)
        self.assertNotIn("disposition: j8_static | j16_smoke | j17_test | rejected_unsafe", self.j14)
        self.assertIn("unsafe command is not a fifth output disposition", self.j14)
        self.assertIn("validation_command_coverage[].manual_decision_ref", self.j0)
        self.assertIn("J0 never parses `decision_id` out of `manual_check_description`", self.j0)

    def test_j14_launcher_failure_has_a_terminal_fsm_branch(self):
        self.assertIn("missing_invocation_id | invalid_invocation_id", self.j14)
        self.assertIn("| 5a |", self.j0)
        self.assertIn("j14_invalid_invocation_id", self.j0)

    def test_plan_lag_vocabulary_does_not_claim_tier_2_is_planless(self):
        for text in (self.j0, self.j14, self.j16, self.j17, self.shared):
            self.assertNotIn("tier-2/3", text)
            self.assertNotIn("tier-2/tier-3", text)
        self.assertIn("tier 2 is never plan-absent", self.shared)

    def test_reversible_delete_does_not_require_fabricated_risk_acceptance(self):
        self.assertIn("reversible/stateless delete or replacement may use `null`", self.j15)
        self.assertIn("genuinely irreversible/data-loss-bearing", self.j15)
        self.assertIn("unaccepted_destructive_change", self.j16)
        self.assertIn("destructive_risk_and_rollback_contract_checked: true", self.j16)

    def test_acceptance_mapping_is_checked_before_and_during_execution(self):
        self.assertIn("J14 acceptance-mapping structural gate", self.j0)
        self.assertIn("exact bijection", self.j17)
        self.assertIn("acceptance_checks_mapped", self.j14)

    def test_resource_lock_exception_uses_scope_and_state_not_four_empty_lists(self):
        self.assertIn("late-discovered methodology blocker", self.j14)
        self.assertIn("state.model: repository_only", self.j16)
        self.assertIn("Empty `plan`/`apply`/`rollback`/`cleanup` lists alone are not proof", self.j16)

    def test_consumer_path_and_output_enums_are_consistent(self):
        self.assertIn("chain-resolved `methodology_review.yaml` path", self.j8)
        self.assertIn(
            "`source_ref: {task_id}/j14_generations/{current_generation_id}/methodology_review.yaml`",
            self.j0,
        )
        self.assertNotIn("status: passed | failed | blocked | skipped | not_applicable", self.j17)
        self.assertIn("For `infra_code`, never document this task as a production deployment", self.j11)

    def test_harness_attestation_is_not_assigned_to_j14(self):
        self.assertIn("J14 receives no harness attestation", self.shared)
        self.assertNotIn("J14/J16 invocation bundle", self.shared)

    def test_j15_fences_every_disk_artifact_and_verifies_lineage(self):
        self.assertIn("all three fencing fields", self.j15)
        self.assertIn("`j15_no_change_confirmation.yaml`", self.j15)
        self.assertIn("acceptance_index_and_j14_state_binding_fresh", self.j15)
        self.assertIn("j14_state.yaml#last_plan_generation_id", self.j15)
        self.assertNotIn("`coding_blocker.yaml`, `dependency_amendment_request.yaml`, and the Финальный Ответ", self.j15)

    def test_j15_retry_modes_are_bound_to_current_inputs(self):
        self.assertIn('`schema_version == "1.1"`', self.j15)
        self.assertIn("`context.plan_generation_id` match this dispatch", self.j15)
        self.assertIn('`schema_version == "1.0"`, `agent == J9b`', self.j15)
        self.assertIn("The encoded id is a useful cross-check", self.j15)

    def test_dependency_audit_is_explicit_for_every_infra_pass(self):
        self.assertIn("`dependency_audit.yaml` is missing. J9 runs for every `infra_code` chain", self.j15)
        self.assertIn("For `execution_chain: infra_code`, `dependency_audit.yaml` is missing", self.j8)
        self.assertIn("It is mandatory for `infra_code`", self.j9b)
        self.assertIn("canonical `no_new_dependencies` audit", self.j0)

    def test_support_steps_and_test_bindings_are_closed_contracts(self):
        self.assertIn("`resource_targets: []` is legal only", self.j15)
        self.assertIn("non-resource support step", self.j14)
        self.assertIn("infra_test_target_ref_or_output_binding_changed", self.j14)
        self.assertIn("`#infra_tests.commands.*.cwd`/`argv`/`target_ref`", self.j8)

    def test_amendment_sequence_is_durable_and_crash_safe(self):
        self.assertIn("next_sequence = current + 1", self.j15)
        self.assertIn("request_id` is not exactly `DAR-<task_id>-A<coding_unit_attempt_count>-S<amendment_sequence_in_attempt>", self.j9)
        self.assertIn("request с `sequence == current + 1`", self.j0)
        self.assertIn("invalid_amendment_sequence", self.j0)

    def test_j8_digest_is_a_mandatory_precommit_fence(self):
        self.assertIn("## Canonical Worktree Diff Digest", self.j8)
        self.assertIn("J0 MUST recompute a passed report", self.j8)
        self.assertIn("Canonical J8 worktree-digest gate", self.j0)
        self.assertIn("j8_worktree_changed_after_review", self.j0)

    def test_registry_metadata_is_not_confused_with_materialization(self):
        self.assertIn("J9 may use read-only official registry/advisory/documentation metadata", self.j15)
        self.assertNotIn("No agent in `infra_code` (J14, J9, J15, J16, J17) has live network/registry access", self.j15)

    def test_ambiguous_mode_is_not_budget_escalation(self):
        self.assertIn("Ambiguous J0/J15 mode context", self.j0)
        self.assertIn("orchestration error, не как budget escalation", self.j0)

    def test_j17_report_schema_version_is_consistent_at_producer_and_consumers(self):
        self.assertIn('schema_version: "3.1"', self.j17)
        self.assertIn('`schema_version: "3.1"` on `infra_test_report.yaml`', self.j0)
        self.assertIn('J17 `infra_test_report.yaml#schema_version: "3.1"`', self.shared)
        self.assertNotIn('infra_test_report.yaml#schema_version: "1.0"', self.shared)

    def test_blocked_tests_always_have_a_retry_cause_and_owner(self):
        self.assertIn(
            "safety_incident | finalization_blocker | failed_test | blocked_test | execution_blocker | preflight_blocker",
            self.j17,
        )
        self.assertIn("For a `blocked_test` with no refuted assertion", self.j17)
        self.assertIn("For an `execution_blocker` tied to a test", self.j17)
        self.assertIn("failure_owner: test_declaration | deployment_plan | deployment_report", self.j17)
        self.assertIn("J17 must not relabel it transient", self.j17)
        self.assertIn("Any disagreement in `route_to`, `allowed`, or `reason`", self.j17)

    def test_deployed_target_resolution_selects_a_unique_scalar(self):
        output_selector = "outputs_captured_without_secrets[name=<target_ref>].value_ref"
        logical_selector = "deployed_resource_refs[logical_id=<target_ref>].address_or_ref"
        for text in (self.j14, self.j17):
            self.assertIn(output_selector, text)
            self.assertIn(logical_selector, text)
        self.assertIn("the scalar consumed by J17", self.j16)
        self.assertNotIn("outputs_captured_without_secrets[<name>]", self.j14)

    def test_preflight_version_probe_is_the_only_executable_exception(self):
        self.assertIn("The sole executable preflight exception is a declared `test_version_command_ref`", self.j17)
        self.assertIn("no functional test/probe command runs", self.j17)
        self.assertIn("its launches are still recorded in `command_executions[]`", self.j17)

    def test_j0_checks_plan_identity_and_j17_claimed_success_internally(self):
        self.assertIn("Plan-generation companion gate", self.j0)
        self.assertIn("J17 claimed-success consistency gate", self.j0)
        self.assertIn("J17 retry-cause integrity gate", self.j0)
        self.assertIn("`context.plan_generation_id == plan_generation_id`", self.j0)
        self.assertIn("retry == {allowed: false, route_to: null, reason: not_applicable, causes: []}", self.j0)
        self.assertIn("required companion check", self.shared)

    def test_validation_coverage_lookup_is_field_matched_not_positional(self):
        self.assertIn("field-match lookup", self.j17)
        self.assertIn("It is never an array-position subscript", self.j0)

    def test_command_ids_are_unique_across_deploy_and_test_spaces(self):
        self.assertIn("globally unique across the combined deploy-side `commands.*[]` and test-side `infra_tests.commands[]`", self.j14)
        self.assertIn("cross-namespace collision", self.j16)

    def test_architecture_overview_tracks_cleanup_and_canonical_skip_reason(self):
        self.assertIn("conditional cleanup-only pass", self.architecture)
        self.assertIn("deployment_cleanup_report.yaml", self.architecture)
        self.assertNotIn("skip_reason: no_lockfile_delta", self.architecture)


if __name__ == "__main__":
    unittest.main()
