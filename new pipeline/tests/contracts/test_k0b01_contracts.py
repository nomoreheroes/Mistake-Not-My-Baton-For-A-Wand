from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0b01.compiler import ReachabilityError, compile_registry_bundle  # noqa: E402
from harness.k0b01.contract import (  # noqa: E402
    EXACT_EVENT_TYPES,
    F15_TRIGGER_IDS,
    PACKAGE_PATH,
    PINNED_EVENT_PROFILE_SHA256,
    PINNED_PACKAGE_SHA256,
    ContractHashMismatch,
    ContractValidationError,
    load_contract_bundle,
    load_exact_json,
    sha256_json,
)


class K0b01ContractTests(unittest.TestCase):
    def test_exact_contract_and_registry_bundle_loads(self) -> None:
        bundle = load_contract_bundle()
        self.assertEqual(
            sha256(PACKAGE_PATH.read_bytes()).hexdigest(), PINNED_PACKAGE_SHA256
        )
        self.assertEqual(
            bundle.source_hashes["event_profile"], PINNED_EVENT_PROFILE_SHA256
        )
        self.assertEqual(tuple(bundle.package["exact_event_types"]), EXACT_EVENT_TYPES)
        self.assertEqual(len(EXACT_EVENT_TYPES), 21)
        self.assertEqual(len(F15_TRIGGER_IDS), 4)
        self.assertNotIn("prompts", bundle.package)
        self.assertEqual(bundle.package["capability_policy"]["physical_model_calls"], 0)
        self.assertEqual(bundle.package["capability_policy"]["tools"], [])
        self.assertFalse(bundle.package["capability_policy"]["network"])
        for event in bundle.event_profile["events"]:
            schema_identity = {
                "additional_properties": False,
                "id": event["payload_schema_id"],
                "required_fields": event["fields_consumed"],
                "version": event["payload_schema_version"],
            }
            self.assertEqual(
                event["payload_schema_sha256"], sha256_json(schema_identity)
            )
            self.assertTrue(event["fields_consumed"])

    def test_complete_file_hash_mismatch_blocks_before_parse_or_compile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-contract-hash-") as temporary:
            changed = Path(temporary) / "changed.json"
            changed.write_bytes(
                PACKAGE_PATH.read_bytes().replace(b'"Alpha0"', b'"Alpha1"', 1)
            )
            with self.assertRaises(ContractHashMismatch):
                load_contract_bundle(package_path=changed)

    def test_duplicate_json_key_is_rejected_even_with_matching_complete_hash(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="k0b01-duplicate-key-") as temporary:
            path = Path(temporary) / "duplicate.yaml"
            path.write_bytes(b'{"id":1,"id":2}\n')
            with self.assertRaisesRegex(
                ContractValidationError, "duplicate JSON object key"
            ):
                load_exact_json(
                    path, sha256(path.read_bytes()).hexdigest(), "duplicate source"
                )

    def test_unknown_event_and_dangling_route_fail_closed(self) -> None:
        bundle = load_contract_bundle()
        changed_event = deepcopy(bundle.event_profile)
        changed_event["events"][0]["event_type"] = "unknown.event"
        with self.assertRaisesRegex(ReachabilityError, "21-event catalog"):
            compile_registry_bundle(replace(bundle, event_profile=changed_event))
        changed_route = deepcopy(bundle.event_profile)
        changed_route["events"][0]["route_ref"] = "missing.route"
        with self.assertRaisesRegex(ReachabilityError, "missing or unused routes"):
            compile_registry_bundle(replace(bundle, event_profile=changed_route))

    def test_payload_hash_field_ownership_and_producer_drift_fail_closed(self) -> None:
        bundle = load_contract_bundle()
        changed_hash = deepcopy(bundle.event_profile)
        changed_hash["events"][0]["payload_schema_sha256"] = "0" * 64
        with self.assertRaisesRegex(ReachabilityError, "payload schema hash differs"):
            compile_registry_bundle(replace(bundle, event_profile=changed_hash))
        changed_field = deepcopy(bundle.event_profile)
        changed_field["events"][0]["fields_consumed"][0] = "unknown_field"
        schema_identity = {
            "additional_properties": False,
            "id": changed_field["events"][0]["payload_schema_id"],
            "required_fields": changed_field["events"][0]["fields_consumed"],
            "version": changed_field["events"][0]["payload_schema_version"],
        }
        changed_field["events"][0]["payload_schema_sha256"] = sha256_json(
            schema_identity
        )
        with self.assertRaisesRegex(ReachabilityError, "consumed fields differ"):
            compile_registry_bundle(replace(bundle, event_profile=changed_field))
        changed_producer = deepcopy(bundle.event_profile)
        changed_producer["events"][0]["producer_owner"] = "unknown_owner"
        with self.assertRaisesRegex(ReachabilityError, "producer owner differs"):
            compile_registry_bundle(replace(bundle, event_profile=changed_producer))

    def test_error_and_incident_terminal_policies_are_exact(self) -> None:
        bundle = load_contract_bundle()
        changed = deepcopy(bundle.subscription_profile)
        route = next(
            item
            for item in changed["routes"]
            if item["route_id"] == "alpha0.terminal.error_human"
        )
        route["terminal_policy"] = "retry_silently"
        with self.assertRaisesRegex(ReachabilityError, "terminal policy differs"):
            compile_registry_bundle(replace(bundle, subscription_profile=changed))
        compiled = compile_registry_bundle(bundle).document
        routes = compiled["outputs"]["compiled_subscription_terminal_snapshot"][
            "routes"
        ]
        policies = {route["route_id"]: route["terminal_policy"] for route in routes}
        self.assertEqual(
            policies["alpha0.terminal.error_human"], "block_run_and_enqueue_human"
        )
        self.assertEqual(
            policies["alpha0.terminal.incident_w5"], "persist_incident_and_enqueue_W5"
        )

    def test_f00_sink_is_bound_only_to_the_exact_retained_contract(self) -> None:
        bundle = load_contract_bundle()
        exception = bundle.subscription_profile["f00_exception"]
        self.assertEqual(exception["event_type"], "handoff.ready")
        self.assertEqual(exception["subscriber"], "bootstrap_sink")
        self.assertEqual(
            exception["allowed_only_under_contract_sha256"],
            "5b8b677aa98416d85db29a12bb0369e98369dcdfae98249dfaf813eeb08a19c6",
        )
        changed = deepcopy(bundle.subscription_profile)
        changed["f00_exception"]["allowed_only_under_contract_sha256"] = "0" * 64
        with self.assertRaisesRegex(ReachabilityError, "F00 bootstrap-sink exception"):
            compile_registry_bundle(replace(bundle, subscription_profile=changed))


if __name__ == "__main__":
    unittest.main()
