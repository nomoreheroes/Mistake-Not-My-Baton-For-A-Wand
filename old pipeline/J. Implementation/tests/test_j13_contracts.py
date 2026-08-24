"""Regression checks for the prose contracts shared by J0/J4/J6/J7/J8/J10/J13.

Run:
    python "J. Implementation/tests/test_j13_contracts.py"

The checks pin mechanically testable cross-prompt invariants. They do not simulate a human
review or validate the semantic quality of a generated UI plan/result.
"""

from pathlib import Path
import unittest


J_DIR = Path(__file__).resolve().parents[1]


def read_prompt(name: str) -> str:
    return (J_DIR / name).read_text(encoding="utf-8")


class HitlUiPromptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.j0 = read_prompt("J0. Dispatcher.md")
        cls.j4 = read_prompt("J4. Methodologist.md")
        cls.j6 = read_prompt("J6. Coder.md")
        cls.j7 = read_prompt("J7. Test Runner.md")
        cls.j8 = read_prompt("J8. Static Analyzer.md")
        cls.j10 = read_prompt("J10. Code Analyst.md")
        cls.j13 = read_prompt("J13. HITL UI.md")
        cls.matrix = read_prompt("J13 HITL UI Protocol - Regression Matrix.md")

    def test_result_blocker_phase_excludes_launch(self):
        self.assertIn("phase: preflight | review_execution", self.j13)
        self.assertNotIn("phase: launch | preflight | review_execution", self.j13)
        self.assertIn("A result never contains a", self.j13)

    def test_invocation_id_failure_uses_launch_blocked_artifact(self):
        self.assertIn(
            "the already-validated `launch_blocked_token` lets J13 report this failure through",
            self.j13,
        )
        self.assertIn("whose filename does not contain `hitl_ui_invocation_id`", self.j13)
        self.assertNotIn("missing_context-reporting result", self.j13)

    def test_bundle_authorization_and_timestamp_are_structurally_closed(self):
        self.assertIn(
            "`participant_authorization_artifact_hash` is non-null and conforms exactly to "
            "`sha256:[0-9a-f]{64}`",
            self.j13,
        )
        self.assertIn("`decided_at` is a non-null, parseable ISO-8601 timestamp", self.j13)
        self.assertIn("REQUIRED non-null `sha256:` + 64 lowercase hex chars", self.j13)

    def test_fixture_ack_list_is_required_and_canonical_when_empty(self):
        self.assertIn(
            "`fixture_irreversible_acknowledgments: []`",
            self.j13,
        )
        self.assertIn("**required list on every invocation**", self.j13)
        self.assertIn("Omitting the field is `missing_context`", self.j13)
        self.assertNotIn("optional, one entry per **`(check_id, point_id)` pair**", self.j13)

    def test_internal_applicability_bug_is_not_routed_to_j4(self):
        expected = (
            "`reason: orchestration_state_mismatch`, `subreason: null`, `next_owner: J0` "
            "(biconditional (v))"
        )
        self.assertIn(expected, self.j13)
        self.assertIn(expected, self.matrix)
        self.assertNotIn(
            "`reason: spec_conflict`, `subreason: invalid_applicability_contract` "
            "(biconditional (v))",
            self.matrix,
        )

    def test_launcher_failure_distinguishes_missing_and_invalid_bootstrap(self):
        for subtype in (
            "inaccessible_artifact_root",
            "invalid_invocation_timestamp",
            "invalid_launch_blocked_token",
            "unsafe_task_id",
        ):
            self.assertIn(subtype, self.j13)
            self.assertIn(subtype, self.j0)
        self.assertIn("j13_inaccessible_artifact_root", self.j0)

    def test_atomic_write_collision_routing_depends_on_target_kind(self):
        for prompt in (self.j0, self.matrix):
            self.assertIn("j13_invocation_candidate_collision", prompt)
            self.assertIn("launch_blocked", prompt)
            self.assertIn("launch_blocked_token", prompt)

    def test_j0_enforces_full_ui_plan_validation_before_both_consumers(self):
        self.assertIn("J10 или J13", self.j0)
        self.assertIn("полный `validate_ui_review_plan_v1`", self.j0)
        self.assertIn("sealed `j4_generations/<run_id>/manifest.yaml`", self.j0)
        self.assertIn("J10 additionally requires a complete UI plan", self.j0)
        self.assertIn("Publication contract for approved `ui_code`", self.j4)

    def test_hybrid_ui_routing_waits_for_automated_component(self):
        self.assertIn("routing is discriminated by mode", self.j10)
        self.assertIn("`components.human_ui.status` remains `not_yet_opened`", self.j10)
        self.assertIn("hybrid_human_ui_opened_only_after_automated_satisfied: true", self.j10)

    def test_j7_deferral_does_not_dispatch_j13(self):
        self.assertIn("provisional evidence-deferral annotation", self.j7)
        self.assertIn("J13 is NOT the next physical step", self.j7)
        self.assertIn("J0 never jumps directly from this recommendation to J13", self.j7)

    def test_zero_diff_contract_is_shared_by_j6_j8_and_j0(self):
        self.assertIn("Legitimate task-level no-op", self.j6)
        self.assertIn("Legitimate task-level no-op", self.j0)
        self.assertIn("zero_diff_expected: true", self.j8)

    def test_j8_uses_generation_scoped_infra_plan_path(self):
        expected = (
            "`{task_id}/j14_generations/{context.plan_generation_id}/"
            "deployment_execution_plan.yaml`"
        )
        self.assertIn(expected, self.j8)


if __name__ == "__main__":
    unittest.main()
