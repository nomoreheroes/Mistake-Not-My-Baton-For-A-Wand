"""Regression checks for the prose contracts shared by J0/J1/J2/J3.

Run:
    python "J. Implementation/tests/test_j1_j3_contracts.py"

These checks intentionally cover only mechanically testable cross-prompt invariants. They do
not attempt to validate the semantic quality of a generated spike result.
"""

from pathlib import Path
import re
import unittest


J_DIR = Path(__file__).resolve().parents[1]


def read_prompt(name: str) -> str:
    return (J_DIR / name).read_text(encoding="utf-8")


class ResearchSpikePromptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.j0 = read_prompt("J0. Dispatcher.md")
        cls.j1 = read_prompt("J1. Spike Executor.md")
        cls.j2 = read_prompt("J2. Spike Documenter.md")
        cls.j3 = read_prompt("J3. Spike Resolver.md")
        cls.plan = read_prompt("J Layer - Architecture Plan.md")

    def test_j0_uses_canonical_i21_research_identity_paths(self):
        self.assertIn("spike_id: <task_spec.provenance.spike_id>", self.j0)
        self.assertIn("open_question_id: <task_spec.provenance.open_question_id>", self.j0)
        self.assertIn("open_questions[question_id", self.j0)

    def test_open_question_record_field_is_question_id(self):
        for prompt in (self.j1, self.j2, self.j3):
            self.assertIn("open_question.question_id", prompt)
        self.assertNotIn("не содержит `open_question_id` / question text", self.j3)

    def test_freshness_hashes_cross_every_handoff(self):
        binding_names = (
            "task_spec_hash",
            "frozen_snapshot_hash",
            "j_acceptance_index_hash",
            "spike_findings_hash",
            "spike_report_hash",
        )
        for name in binding_names[:3]:
            self.assertIn(name, self.j1)
        for name in binding_names[:4]:
            self.assertIn(name, self.j2)
        for name in binding_names:
            self.assertIn(name, self.j0)
            self.assertGreaterEqual(self.j3.count(name), 3, name)

    def test_acceptance_identity_is_shared_across_all_agents(self):
        for prompt in (self.j0, self.j1, self.j2, self.j3):
            self.assertIn("j_acceptance_index", prompt)
            self.assertIn("check_id", prompt)
        for prompt in (self.j1, self.j2, self.j3):
            self.assertIn("source_index", prompt)
            self.assertIn("source_text", prompt)

    def test_j1_has_closed_gate_catalog(self):
        ids = re.findall(r"`(J1-GATE-\d{3})`", self.j1)
        self.assertEqual(ids[:9], [f"J1-GATE-{n:03d}" for n in range(1, 10)])
        self.assertIn("Ровно девять rows J1-GATE-001..009", self.j1)

    def test_assumptions_have_one_structured_home(self):
        match = re.search(
            r"\nfindings:\n(?P<body>.*?)\nproposed_assumptions:\n",
            self.j1,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        findings_schema = match.group("body")
        self.assertNotIn("claim_type: fact | assumption", findings_schema)
        self.assertNotIn("conservative_assumption", findings_schema)
        self.assertIn("assumptions допустимы только в `proposed_assumptions[]`", self.j3)

    def test_retry_archives_previous_attempt_before_reset(self):
        self.assertIn("### Research Spike Retry Archive", self.j0)
        self.assertIn("spike_attempts/attempt-<N+1>/manifest.yaml", self.j0)
        self.assertIn("rerun_allowed: false", self.j0)
        self.assertIn("unsafe_rerun_context", self.j3)

    def test_research_only_resolution_is_batch_local(self):
        self.assertIn("record_spike_resolved_for_batch", self.j3)
        self.assertIn("Research-only Spike Batch Policy", self.j0)
        self.assertIn("remaining eligible research tasks", self.plan)

    def test_research_artifact_schema_versions_are_current(self):
        self.assertIn('schema_version: "1.1"', self.j1)
        self.assertIn('spike_findings.yaml#schema_version != "1.1"', self.j2)
        self.assertIn('spike_findings.yaml#schema_version != "1.1"', self.j3)
        self.assertIn('schema_version: "1.1"', self.j3)
        self.assertIn('schema_version: "1.1"', self.j0)


if __name__ == "__main__":
    unittest.main()
