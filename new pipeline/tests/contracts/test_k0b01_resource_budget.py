from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0b01 import (  # noqa: E402
    BinaryPayloadBudgetError,
    BudgetError,
    BudgetLimitExceeded,
    IncompleteGraph,
    ReferenceMismatch,
    compile_resource_budget,
    load_contract_bundle,
    prove_reference_equivalence,
)


class K0b01ResourceBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load_contract_bundle()
        cls.cases = {
            case["case_id"]: case for case in cls.bundle.reference_cases["cases"]
        }

    def test_all_reference_cases_match_exact_fields_and_values(self) -> None:
        compiled = prove_reference_equivalence(
            self.bundle.reference_cases, self.bundle.resource_policy
        )
        self.assertEqual(
            tuple(item.case_id for item in compiled),
            ("k0a-bootstrap-reference-v1", "k0b-approved-two-phase-reference-v1"),
        )
        k0b = compiled[1].result
        self.assertEqual(k0b["total_calls"], {"nominal": 58, "worst_case": 90})
        self.assertEqual(
            k0b["binary_payload"],
            {"nominal_new_bytes": 2236416, "worst_case_new_bytes": 4472832},
        )
        self.assertEqual(
            k0b["checkpoint_phases"]["K0b-runtime-operational"]["phase_pack_bytes"],
            {"nominal": 132120576, "worst_case": 926941184},
        )
        self.assertEqual(
            k0b["checkpoint_phases"]["K0b-F15-exact-measurement"]["phase_pack_bytes"],
            {"nominal": 125829120, "worst_case": 954204160},
        )
        self.assertEqual(
            k0b["cumulative_observable_phase_pack_bytes"],
            {"nominal": 257949696, "worst_case": 1881145344},
        )

    def test_incomplete_graph_duplicate_package_and_hidden_deterministic_call_fail(
        self,
    ) -> None:
        base = self.cases["k0a-bootstrap-reference-v1"]
        incomplete = deepcopy(base)
        incomplete["graph_completeness"]["dialogue"] = False
        with self.assertRaises(IncompleteGraph):
            compile_resource_budget(incomplete, self.bundle.resource_policy)
        duplicate = deepcopy(base)
        duplicate["packages"].append(deepcopy(duplicate["packages"][0]))
        with self.assertRaises(IncompleteGraph):
            compile_resource_budget(duplicate, self.bundle.resource_policy)
        hidden = deepcopy(base)
        hidden["packages"][1]["call_nodes"][0]["call_class"] = "deterministic"
        with self.assertRaisesRegex(BudgetError, "cannot hide a model call"):
            compile_resource_budget(hidden, self.bundle.resource_policy)

    def test_tier_overrun_requires_exact_escalation_authority(self) -> None:
        base = deepcopy(self.cases["k0a-bootstrap-reference-v1"])
        base["packages"][1]["call_nodes"][0]["worst_case"] = 21
        with self.assertRaises(BudgetLimitExceeded):
            compile_resource_budget(base, self.bundle.resource_policy)
        base["packages"][1]["budget_escalation_authority"] = "owner-budget-receipt-v1"
        result = compile_resource_budget(base, self.bundle.resource_policy)
        self.assertEqual(result["package_calls"]["K0a-runtime-F00"]["worst_case"], 25)

    def test_false_na_missing_binary_field_and_aggregate_overflow_fail(self) -> None:
        base = self.cases["k0b-approved-two-phase-reference-v1"]
        false_na = deepcopy(base)
        false_na["binary_payload_budgets"][0][
            "contract_prohibits_binary_persistence"
        ] = False
        with self.assertRaises(BinaryPayloadBudgetError):
            compile_resource_budget(false_na, self.bundle.resource_policy)
        missing = deepcopy(base)
        del missing["binary_payload_budgets"][2]["runtime_aggregate_limit_bytes"]
        with self.assertRaises(BinaryPayloadBudgetError):
            compile_resource_budget(missing, self.bundle.resource_policy)
        overflow = deepcopy(base)
        overflow["binary_payload_budgets"][2]["runtime_aggregate_limit_bytes"] = 1
        with self.assertRaises(BinaryPayloadBudgetError):
            compile_resource_budget(overflow, self.bundle.resource_policy)
        stale_count = deepcopy(base)
        stale_count["binary_payload_budgets"][2]["checkpoint_publication_count"] = 59
        with self.assertRaisesRegex(
            BinaryPayloadBudgetError, "publication count differs"
        ):
            compile_resource_budget(stale_count, self.bundle.resource_policy)
        hidden_amplification = deepcopy(base)
        hidden_amplification["binary_payload_budgets"][2][
            "pessimistic_pack_amplification"
        ] = 0
        with self.assertRaisesRegex(
            BinaryPayloadBudgetError, "pack amplification differs"
        ):
            compile_resource_budget(hidden_amplification, self.bundle.resource_policy)

    def test_policy_authority_threshold_and_credit_drift_fail_closed(self) -> None:
        base = self.cases["k0a-bootstrap-reference-v1"]
        mutations = []
        authority = deepcopy(self.bundle.resource_policy)
        authority["authority"]["d0_gate_sha256"] = "0" * 64
        mutations.append(authority)
        threshold = deepcopy(self.bundle.resource_policy)
        threshold["checkpoint"]["max_checkpoint_bytes"] += 1
        mutations.append(threshold)
        credit = deepcopy(self.bundle.resource_policy)
        credit["checkpoint"]["all_credit"] = 1
        mutations.append(credit)
        call_class = deepcopy(self.bundle.resource_policy)
        call_class["call_classes"]["deterministic"]["counts_as_model_call"] = True
        mutations.append(call_class)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(BudgetError):
                compile_resource_budget(base, mutation)

    def test_phase_reorder_overlap_third_phase_and_call_reclassification_fail(
        self,
    ) -> None:
        base = self.cases["k0b-approved-two-phase-reference-v1"]
        reordered = deepcopy(base)
        reordered["checkpoint_phases"].reverse()
        with self.assertRaises(IncompleteGraph):
            compile_resource_budget(reordered, self.bundle.resource_policy)
        overlap = deepcopy(base)
        overlap["checkpoint_phases"][1]["members"].append("K0b-01")
        with self.assertRaises(IncompleteGraph):
            compile_resource_budget(overlap, self.bundle.resource_policy)
        third = deepcopy(base)
        extra = deepcopy(third["checkpoint_phases"][1])
        extra["phase_id"] = "third-phase"
        extra["members"] = ["other"]
        third["checkpoint_phases"].append(extra)
        with self.assertRaises(IncompleteGraph):
            compile_resource_budget(third, self.bundle.resource_policy)
        call = deepcopy(base)
        call["packages"][1]["call_nodes"][0]["call_class"] = "model"
        call["packages"][1]["call_nodes"][0]["nominal"] = 1
        call["packages"][1]["call_nodes"][0]["worst_case"] = 1
        with self.assertRaisesRegex(BudgetError, "call allocation differs for K0b-01"):
            compile_resource_budget(call, self.bundle.resource_policy)

    def test_checkpoint_warning_and_exact_hard_boundary_are_fail_closed(self) -> None:
        base = self.cases["k0a-bootstrap-reference-v1"]
        warning = deepcopy(base)
        warning["checkpoint_phases"][0]["checkpoint_components_bytes"]["nominal"] = [
            50 * 1048576
        ]
        warning["checkpoint_phases"][0]["checkpoint_components_bytes"]["worst_case"] = [
            50 * 1048576
        ]
        result = compile_resource_budget(warning, self.bundle.resource_policy)
        self.assertEqual(
            result["checkpoint_phases"]["K0a"]["checkpoint_status"],
            {"nominal": "above_warning", "worst_case": "above_warning"},
        )
        hard = deepcopy(base)
        hard["checkpoint_phases"][0]["checkpoint_components_bytes"]["nominal"] = [
            100 * 1048576
        ]
        hard["checkpoint_phases"][0]["checkpoint_components_bytes"]["worst_case"] = [
            100 * 1048576
        ]
        with self.assertRaises(BudgetLimitExceeded):
            compile_resource_budget(hard, self.bundle.resource_policy)

    def test_f15_thirtieth_publication_blocks_unconditionally(self) -> None:
        base = deepcopy(self.cases["k0b-approved-two-phase-reference-v1"])
        f15 = base["checkpoint_phases"][1]
        f15["fixed_trigger_counts"] = {"nominal": 8, "worst_case": 8}
        with self.assertRaisesRegex(BudgetLimitExceeded, "publication count blocks"):
            compile_resource_budget(base, self.bundle.resource_policy)

    def test_reference_expected_output_is_not_used_as_compiler_input(self) -> None:
        changed = deepcopy(self.bundle.reference_cases)
        changed["cases"][0]["expected_reference_result"]["total_calls"][
            "worst_case"
        ] = 999
        with self.assertRaises(ReferenceMismatch):
            prove_reference_equivalence(changed, self.bundle.resource_policy)


if __name__ == "__main__":
    unittest.main()
