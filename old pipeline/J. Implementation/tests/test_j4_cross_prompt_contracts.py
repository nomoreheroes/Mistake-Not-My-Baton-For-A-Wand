"""Static regression checks for the J4-centered implementation prompt contracts."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class J4CrossPromptContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.j0 = read("J0. Dispatcher.md")
        cls.j4 = read("J4. Methodologist.md")
        cls.j5 = read("J5. Test Writer.md")
        cls.j6 = read("J6. Coder.md")
        cls.j7 = read("J7. Test Runner.md")
        cls.j8 = read("J8. Static Analyzer.md")
        cls.j9 = read("J9. Dependency Auditor.md")
        cls.j10 = read("J10. Code Analyst.md")
        cls.j12 = read("J12. Container & Deploy.md")
        cls.j13 = read("J13. HITL UI.md")
        cls.j20 = read("J20. Migration Dry Run.md")
        cls.shared = read("J4-J0 Core Generation And Invocation Envelope.md")

    def test_j4_may_write_every_artifact_its_role_requires(self):
        constraint = next(
            line
            for line in self.j4.splitlines()
            if line.startswith("- J4 создаёт `{resolved_output_dir}/methodology_review.yaml`")
        )
        self.assertIn("conditional plan-файлы", constraint)
        for name in (
            "deployment_execution_plan.yaml",
            "ui_review_plan.yaml",
            "migration_execution_plan.yaml",
        ):
            self.assertIn(
                f"j4_generations/{{run_id}}/{name}",
                self.shared,
            )

    def test_j4_methodology_and_execution_plans_are_input_bound(self):
        self.assertIn(
            'task_spec_hash: "sha256:<must equal j_acceptance_index.yaml#task_spec_hash',
            self.j4,
        )
        for plan_heading in (
            "## Deployment Execution Plan (triggers_module_complete)",
            "## Migration Execution Plan (`migration`)",
        ):
            plan = self.j4.split(plan_heading, 1)[1]
            self.assertIn("agent: J4", plan)
            self.assertIn("task_spec_hash:", plan)
            self.assertIn("methodology_review_hash:", plan)
        self.assertIn("**Canonical J4 generation and input-binding gate.**", self.j0)

    def test_law_j_testable_fail_contract_is_consistent_through_j6(self):
        for text in (self.j4, self.j5, self.j6):
            self.assertIn("expected_typed_outcome", text)
        self.assertIn("This exception never applies to `config`", self.j6)
        self.assertIn("Для `config` любой applicable `fail` блокирует approval", self.j4)
        self.assertIn("`status != not_applicable`", self.j5)
        self.assertNotIn("explicit `applicable: true`", self.j5)

    def test_config_acceptance_is_not_optional_in_j6(self):
        self.assertIn(
            "`acceptance_checks` are absent or empty. J0 Task Preflight and J4 require",
            self.j6,
        )
        self.assertNotIn("For `config` chain, `acceptance_checks` may be absent", self.j6)

    def test_deploy_observability_and_atomicity_have_structured_plan_fields(self):
        for text in (self.j4, self.j12):
            self.assertIn("observability_policy:", text)
            self.assertIn("partial_execution_classification:", text)
            self.assertIn("methodology_review_hash:", text)

    def test_j12_retry_and_dependency_status_vocabulary_is_canonical(self):
        self.assertIn("retry_context.attempt_number > 2", self.j12)
        self.assertNotIn("retry_context.j12_attempt_number", self.j12)
        self.assertIn(
            "status: approved | partially_approved | no_new_dependencies | rejected | blocked | not_applicable",
            self.j12,
        )
        self.assertIn("normative override of the legacy `j12_attempt_number`", self.j0)

    def test_j10_can_assign_j4_as_finding_owner(self):
        self.assertIn("owner: J4 | J6 | J5", self.j10)
        self.assertIn("tied to owner (`J4`, `J6`", self.j10)

    def test_j9_and_j20_results_are_fenced_by_j0(self):
        self.assertIn("**Canonical J9 invocation envelope", self.j0)
        self.assertIn("exact equality of all three `context` values", self.j0)
        self.assertIn("**Canonical J20 current-run gate.**", self.j0)
        self.assertGreaterEqual(self.j20.count('run_id: "<UUID echoed verbatim'), 2)
        self.assertIn("current_attempt_runtime_step: complete_after_immediate_run_id_gate", self.j0)
        self.assertIn("structured `env[].env_var_name`", self.j20)

    def test_launcher_failure_vocabulary_covers_reviewed_agents(self):
        launcher_line = next(
            line for line in self.j0.splitlines() if line.startswith("- **`LAUNCHER_FAILURE`**")
        )
        for agent in ("J4", "J5", "J6", "J8", "J9", "J10", "J12", "J13", "J20"):
            self.assertIn(agent, launcher_line)
        for text in (self.j5, self.j6, self.j9, self.j10, self.j12, self.j20):
            self.assertIn("LAUNCHER_FAILURE", text)

    def test_j5_contract_has_minimum_identity_envelope(self):
        self.assertGreaterEqual(self.j5.count('schema_version: "1.2"'), 2)
        self.assertGreaterEqual(self.j5.count("agent: J5"), 2)
        self.assertGreaterEqual(self.j5.count('task_id: "<task_id>"'), 2)
        self.assertIn("**Canonical J5 artifact identity and acceptance-index gate.**", self.j0)
        self.assertIn("acceptance_index_hash:", self.j5)
        self.assertIn("check_id: \"AC-001\"", self.j5)
        self.assertNotIn("J5 never emits `check_id`", self.j10)

    def test_j4_is_published_as_an_immutable_cas_generation(self):
        self.assertIn("## J4 Immutable Generation Paths", self.shared)
        self.assertIn("j4_state.yaml", self.shared)
        self.assertIn("active_attempt.parent_generation_id == current_generation_id", self.shared)
        self.assertIn("J4 never writes or edits it", self.shared)
        self.assertIn("## Failure and recovery transitions", self.shared)
        self.assertIn("CAS-clears `active_attempt` only if its run id still matches", self.shared)
        self.assertIn('schema_version: "2.0"', self.j4)
        self.assertIn("{resolved_output_dir}/methodology_review.yaml", self.j4)
        self.assertIn("j4_generations/<run_id>/manifest.yaml", self.j0)

    def test_common_invocation_envelope_fences_every_target_agent(self):
        for text in (self.j4, self.j5, self.j10, self.j12):
            self.assertIn("invocation_envelope", text)
            self.assertIn("acceptance_index_hash", text)
        self.assertIn("For every physical J4, J5, J10, or J12 call", self.j0)
        self.assertIn('schema_version: "1.1"', self.j10)
        self.assertIn('schema_version: "1.1"', self.j12)

    def test_j4_handoff_is_just_in_time_and_ui_plan_can_be_deferred(self):
        self.assertIn("## Just-In-Time Handoff", self.shared)
        self.assertIn("j8_can_proceed", self.j4)
        self.assertIn("ui_review_plan: complete | deferred | not_applicable", self.j4)
        self.assertIn("approved methodology is not rejected", self.j4)
        self.assertIn("J0 checks only the readiness flag", self.j0)

    def test_all_j4_consumers_use_the_sealed_generation(self):
        consumers = (
            self.j5,
            self.j6,
            self.j8,
            self.j9,
            self.j10,
            self.j12,
            self.j13,
            self.j20,
        )
        for text in consumers:
            self.assertIn("j4_generation", text)
            self.assertIn("J4-J0 Core Generation And Invocation Envelope.md", text)

    def test_j5_no_change_required_is_a_complete_evidence_result(self):
        self.assertIn("status: success | partial_success | no_change_required", self.j5)
        self.assertIn("evidence_origin: existing_test", self.j5)
        self.assertIn("no_change_has_complete_existing_coverage", self.j5)
        self.assertIn("status: no_change_required", self.j0)
        self.assertIn("Canonical J5 No-Change Consumption", self.j7)

    def test_j10_binds_review_to_full_worktree_digest(self):
        self.assertIn("reviewed_worktree_diff_digest", self.j10)
        self.assertIn("exact J8 Canonical Worktree Diff Digest algorithm", self.shared)
        self.assertIn("j10_worktree_changed_after_review", self.j0)


if __name__ == "__main__":
    unittest.main()
