from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import locale
import os
from pathlib import Path
import sys
import tempfile
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0b01 import (  # noqa: E402
    CHECKPOINT_PHASE_ORDER,
    EXACT_ROUTE_IDS,
    F15_TRIGGER_IDS,
    CompilerError,
    RoutingError,
    compile_registry_bundle,
    compile_registry_bytes,
    load_contract_bundle,
)


def _reverse_mapping_insertion_order(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _reverse_mapping_insertion_order(item)
            for key, item in reversed(tuple(value.items()))
        }
    if isinstance(value, list):
        return [_reverse_mapping_insertion_order(item) for item in value]
    return value


class K0b01RoutingCompilerTests(unittest.TestCase):
    def test_compilation_is_byte_deterministic_across_cwd_and_repetition(self) -> None:
        first = compile_registry_bytes()
        second = compile_registry_bytes()
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory(prefix="k0b01-cwd-") as temporary:
            original = Path.cwd()
            try:
                os.chdir(temporary)
                third = compile_registry_bytes()
            finally:
                os.chdir(original)
        self.assertEqual(first, third)
        original_locale = locale.setlocale(locale.LC_ALL)
        try:
            locale.setlocale(locale.LC_ALL, "C")
            fourth = compile_registry_bytes()
        finally:
            locale.setlocale(locale.LC_ALL, original_locale)
        self.assertEqual(first, fourth)
        bundle = load_contract_bundle()
        reordered = replace(
            bundle,
            package=_reverse_mapping_insertion_order(bundle.package),
            event_profile=_reverse_mapping_insertion_order(bundle.event_profile),
            subscription_profile=_reverse_mapping_insertion_order(
                bundle.subscription_profile
            ),
            routing_profile=_reverse_mapping_insertion_order(bundle.routing_profile),
            resource_policy=_reverse_mapping_insertion_order(bundle.resource_policy),
            reference_cases=_reverse_mapping_insertion_order(bundle.reference_cases),
            source_hashes=_reverse_mapping_insertion_order(bundle.source_hashes),
        )
        self.assertEqual(first, compile_registry_bytes(reordered))

    def test_compiled_outputs_are_closed_and_hash_bound(self) -> None:
        compiled = compile_registry_bundle().document
        self.assertEqual(
            tuple(compiled["outputs"]),
            (
                "compiled_artifact_event_profile",
                "compiled_event_reachability_graph",
                "compiled_subscription_terminal_snapshot",
                "compiled_s_route_table_v2",
                "compiled_fanout_barrier_profile",
                "compiled_resource_forecast",
                "compiled_checkpoint_phase_partition_v1",
                "compiled_checkpoint_publication_budget_v2",
            ),
        )
        self.assertEqual(len(compiled["source_hashes"]), 6)
        self.assertEqual(len(compiled["output_hashes"]), 8)
        self.assertEqual(
            compiled["compiler_hashes"],
            {
                "registry_routing_sha256": sha256(
                    (PIPELINE_DIR / "harness" / "k0b01" / "compiler.py").read_bytes()
                ).hexdigest(),
                "resource_budget_sha256": sha256(
                    (PIPELINE_DIR / "harness" / "k0b01" / "budget.py").read_bytes()
                ).hexdigest(),
            },
        )
        self.assertEqual(len(compiled["aggregate_digest"]), 64)
        self.assertEqual(
            compiled["outputs"]["compiled_artifact_event_profile"]["event_count"], 21
        )
        reachability = compiled["outputs"]["compiled_event_reachability_graph"]
        expected_field_count = sum(
            len(event["fields_consumed"])
            for event in compiled["outputs"]["compiled_artifact_event_profile"][
                "events"
            ]
        )
        self.assertEqual(
            len(reachability["consumed_field_owners"]), expected_field_count
        )
        self.assertTrue(
            all(
                len(owner["owner_schema_sha256"]) == 64
                for owner in reachability["consumed_field_owners"]
            )
        )

    def test_exact_routes_barrier_revision_owner_and_zero_call_fence(self) -> None:
        compiled = compile_registry_bundle().document["outputs"]
        routes = compiled["compiled_s_route_table_v2"]["routes"]
        self.assertEqual(tuple(route["route_id"] for route in routes), EXACT_ROUTE_IDS)
        self.assertFalse(
            compiled["compiled_s_route_table_v2"]["physical_dispatch_authorized"]
        )
        barrier = compiled["compiled_fanout_barrier_profile"]["barriers"][0]
        self.assertEqual(barrier["policy"], "all_required")
        self.assertEqual(
            barrier["members"],
            ["fixture.alpha0.primary_reviewer", "fixture.alpha0.adversarial_reviewer"],
        )
        self.assertFalse(barrier["dynamic_membership"])
        revision = compiled["compiled_fanout_barrier_profile"]["revision_owner_rule"]
        self.assertEqual(
            revision["revision_owner_zero_role_id"], "fixture.alpha0.upstream_zero"
        )
        self.assertEqual(
            revision["producer_invocation_id"], "distinct_required_runtime_value"
        )

    def test_two_phase_partition_and_four_triggers_are_exact_and_inactive(self) -> None:
        output = compile_registry_bundle().document["outputs"]
        partition = output["compiled_checkpoint_phase_partition_v1"]
        self.assertEqual(tuple(partition["order"]), CHECKPOINT_PHASE_ORDER)
        self.assertTrue(partition["chronological"])
        self.assertTrue(partition["contiguous"])
        self.assertTrue(partition["non_overlapping"])
        self.assertTrue(partition["exhaustive"])
        self.assertEqual(tuple(partition["f15_boundary_trigger_ids"]), F15_TRIGGER_IDS)
        self.assertEqual(
            partition["call_allocation"]["K0b-01"], {"nominal": 0, "worst_case": 0}
        )
        publication = output["compiled_checkpoint_publication_budget_v2"]
        self.assertFalse(publication["runtime_phase_activation"])
        self.assertEqual(publication["checkpoint_policy"]["all_credit"], 0)

    def test_direct_handoff_dynamic_member_phase_widening_and_target_drift_fail(
        self,
    ) -> None:
        bundle = load_contract_bundle()
        mutations = []
        direct = deepcopy(bundle.routing_profile)
        direct["routes"][0]["target"] = "another_actor_directly"
        mutations.append(direct)
        dynamic = deepcopy(bundle.routing_profile)
        dynamic["barriers"][0]["dynamic_membership"] = True
        mutations.append(dynamic)
        phase = deepcopy(bundle.routing_profile)
        phase["routes"][0]["allowed_checkpoint_phase"] = "third-phase"
        mutations.append(phase)
        target = deepcopy(bundle.routing_profile)
        target["routes"][3]["target"] = "producer_invocation"
        mutations.append(target)
        for mutation in mutations:
            with self.subTest(index=mutations.index(mutation)):
                with self.assertRaises(RoutingError):
                    compile_registry_bundle(replace(bundle, routing_profile=mutation))

    def test_reference_failure_blocks_registry_compilation(self) -> None:
        bundle = load_contract_bundle()
        changed = deepcopy(bundle.reference_cases)
        changed["cases"][0]["expected_reference_result"]["total_calls"]["nominal"] += 1
        with self.assertRaisesRegex(CompilerError, "differs from reference case"):
            compile_registry_bundle(replace(bundle, reference_cases=changed))


if __name__ == "__main__":
    unittest.main()
