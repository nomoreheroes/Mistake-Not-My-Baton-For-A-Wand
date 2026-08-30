from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a02 import contract as contract_module  # noqa: E402
from harness.k0a02.contract import (  # noqa: E402
    ContractHashMismatch,
    ContractValidationError,
    Identity,
    PACKAGE_PATH,
    PINNED_EVENTS,
    PINNED_PACKAGE_SHA256,
    PINNED_ROLES,
    ResponseIdentity,
    canonical_json,
    load_contract_package,
    sha256_text,
)


class K0a02ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.package = load_contract_package()
        cls.document = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    def test_exact_positive_contract_load(self) -> None:
        self.assertEqual(self.package.complete_file_sha256, PINNED_PACKAGE_SHA256)
        self.assertEqual(self.package.package_identity.id, "pipeline-v2.k0a02.f00-contract-package")
        self.assertEqual(self.package.package_identity.version, "1.0.0")
        self.assertEqual(tuple(self.package.event_profile), PINNED_EVENTS)
        for role in PINNED_ROLES:
            self.assertEqual(self.package.actor(role)["role"], role)
            self.assertEqual(len(self.package.actor_contract_identity(role).sha256), 64)
            self.assertEqual(len(self.package.prompt_identity(role).sha256), 64)
            self.assertEqual(len(self.package.result_schema_identity(role).sha256), 64)

    def test_complete_package_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="k0a02-contract-") as temporary:
            changed = Path(temporary) / "changed.json"
            changed.write_bytes(PACKAGE_PATH.read_bytes().replace(b'"profile": "F00"', b'"profile": "F01"', 1))
            with self.assertRaises(ContractHashMismatch):
                load_contract_package(changed)

    def test_contract_prompt_and_schema_hash_mismatches_are_distinctly_rejected(self) -> None:
        mutations = []
        actor = deepcopy(self.document)
        actor["actors"]["S0"]["allowed_route"] = "foreign"
        mutations.append(actor)
        prompt = deepcopy(self.document)
        prompt["prompts"]["s0"]["text"] += " widened"
        mutations.append(prompt)
        schema = deepcopy(self.document)
        schema["schemas"]["s0_route_proposal"]["schema"]["properties"]["route"]["const"] = "foreign"
        mutations.append(schema)
        for mutation in mutations:
            with self.subTest(kind=mutations.index(mutation)):
                with self.assertRaises(ContractHashMismatch):
                    contract_module._validate_package(mutation)

    def test_unknown_extra_stale_route_event_and_capability_values_fail_closed(self) -> None:
        mutations: list[dict[str, object]] = []
        extra = deepcopy(self.document)
        extra["unexpected"] = True
        mutations.append(extra)
        stale = deepcopy(self.document)
        stale["package_version"] = "0.9.0"
        mutations.append(stale)
        route = deepcopy(self.document)
        route["route"].append("foreign_worker")
        mutations.append(route)
        event = deepcopy(self.document)
        event["event_profile"]["foreign.event"] = deepcopy(event["event_profile"]["run.started"])
        mutations.append(event)
        tools = deepcopy(self.document)
        tools["capability_profile"]["tools"] = ["shell"]
        mutations.append(tools)
        roots = deepcopy(self.document)
        roots["capability_profile"]["filesystem_roots"] = ["C:/foreign"]
        mutations.append(roots)
        provider = deepcopy(self.document)
        provider["model_profile"]["provider"] = "foreign-provider"
        mutations.append(provider)
        model = deepcopy(self.document)
        model["model_profile"]["model_profile"] = "foreign-model"
        mutations.append(model)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ContractValidationError):
                    contract_module._validate_package(mutation)

    def test_exact_identity_guards_reject_stale_contract_prompt_and_schema(self) -> None:
        with self.assertRaises(ContractHashMismatch):
            self.package.require_package_identity(
                Identity(self.package.package_identity.id, "0.9.0", self.package.complete_file_sha256)
            )
        for method, current in (
            (self.package.require_prompt_identity, self.package.prompt_identity("S0")),
            (self.package.require_result_schema_identity, self.package.result_schema_identity("S0")),
        ):
            with self.subTest(method=method.__name__):
                with self.assertRaises(ContractHashMismatch):
                    method("S0", Identity(current.id, current.version, "0" * 64))

    def test_loaded_package_accessors_cannot_mutate_pinned_contract_or_schema(self) -> None:
        actor = self.package.actor("S0")
        schema = self.package.schema("s0_route_proposal")
        actor["allowed_route"] = "foreign_Layer0"
        schema["schema"]["properties"]["route"]["const"] = "foreign_Layer0"
        foreign = {
            "action": "invoke",
            "invocation_id": "inv-s0",
            "route": "foreign_Layer0",
            "run_id": "run-1",
            "triggering_event_id": "event-command",
            "type": "s0_route_proposal",
        }
        with self.assertRaises(ContractValidationError):
            self.package.validate_response(
                "S0",
                canonical_json(foreign),
                ResponseIdentity("inv-s0", "run-1", "event-command"),
            )
        self.assertEqual(self.package.actor("S0")["allowed_route"], "synthetic_Layer0")
        self.assertEqual(
            self.package.schema("s0_route_proposal")["schema"]["properties"]["route"]["const"],
            "synthetic_Layer0",
        )

    def test_direct_package_construction_cannot_bypass_exact_byte_loader(self) -> None:
        foreign = deepcopy(self.document)
        foreign["actors"]["S0"]["allowed_route"] = "foreign_Layer0"
        foreign["schemas"]["s0_route_proposal"]["schema"]["properties"]["route"][
            "const"
        ] = "foreign_Layer0"
        with self.assertRaises(ContractValidationError):
            contract_module.PinnedContractPackage(foreign, PINNED_PACKAGE_SHA256)

    def test_s0_response_rejects_extra_unknown_route_action_and_wrong_identity_echo(self) -> None:
        identity = ResponseIdentity("inv-s0", "run-1", "event-command")
        valid = {
            "action": "invoke",
            "invocation_id": identity.invocation_id,
            "route": "synthetic_Layer0",
            "run_id": identity.run_id,
            "triggering_event_id": identity.triggering_event_id,
            "type": "s0_route_proposal",
        }
        self.assertEqual(
            self.package.validate_response("S0", canonical_json(valid), identity), valid
        )
        mutations = []
        for key, value in (
            ("extra", True),
            ("route", "foreign"),
            ("action", "call_tool"),
            ("invocation_id", "wrong"),
            ("run_id", "wrong"),
            ("triggering_event_id", "wrong"),
            ("type", "abstention"),
        ):
            changed = dict(valid)
            changed[key] = value
            mutations.append(changed)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(ContractValidationError):
                    self.package.validate_response("S0", canonical_json(value), identity)
        for malformed in ("not-json", "[]", '{"type":"semantic_blocker"}'):
            with self.assertRaises(ContractValidationError):
                self.package.validate_response("S0", malformed, identity)

    def test_worker_rejects_wrong_artifact_owner_media_schema_hash_and_content_hash(self) -> None:
        identity = ResponseIdentity("inv-worker", "run-1", "event-started")
        schema = self.package.schema_identity("bootstrap_synthetic_result")
        content = "synthetic"
        valid = {
            "action": "publish",
            "artifact_type": "bootstrap.synthetic_result",
            "content_sha256": sha256_text(content),
            "content_text": content,
            "invocation_id": identity.invocation_id,
            "logical_owner": "fixture.bootstrap_worker",
            "media_type": "text/plain",
            "parent_ref": "fixture:seed:request.yaml",
            "result_schema_id": schema.id,
            "result_schema_sha256": schema.sha256,
            "result_schema_version": schema.version,
            "run_id": identity.run_id,
            "triggering_event_id": identity.triggering_event_id,
            "type": "fixture_worker_publication_proposal",
        }
        self.package.validate_response("fixture_worker", canonical_json(valid), identity)
        for key, value in (
            ("logical_owner", "S0"),
            ("media_type", "application/octet-stream"),
            ("result_schema_id", "foreign"),
            ("result_schema_version", "2"),
            ("result_schema_sha256", "0" * 64),
            ("content_sha256", "f" * 64),
        ):
            changed = dict(valid)
            changed[key] = value
            with self.subTest(key=key):
                with self.assertRaises(ContractValidationError):
                    self.package.validate_response("fixture_worker", canonical_json(changed), identity)

    def test_fixture_worker_input_schema_matches_exact_envelope_and_content_hash(self) -> None:
        layer0 = {
            "action": "invoke",
            "invocation_id": "inv-layer0",
            "route": "fixture_worker",
            "run_id": "run-1",
            "triggering_event_id": "event-command",
            "type": "synthetic_layer0_invocation_proposal",
        }
        content = "request_id: fixture-request-001\n"
        worker_input = {
            "fixture_input": {
                "content_sha256": sha256_text(content),
                "content_text": content,
                "ref": "fixture:seed:request.yaml",
            },
            "layer0_proposal": layer0,
        }
        self.assertEqual(
            self.package.validate_actor_input("fixture_worker", worker_input), worker_input
        )
        for changed in (
            layer0,
            {**worker_input, "extra": True},
            {
                **worker_input,
                "fixture_input": {**worker_input["fixture_input"], "content_sha256": "0" * 64},
            },
        ):
            with self.assertRaises(ContractValidationError):
                self.package.validate_actor_input("fixture_worker", changed)

    def test_normalized_command_and_unknown_schema_fail_closed(self) -> None:
        command = {
            "command": "bootstrap",
            "fixture_spec_sha256": self.package.fixture_binding["fixture_spec_sha256"],
            "profile": "F00",
            "type": "normalized_f00_command",
        }
        self.package.validate_normalized_command(command)
        for changed in (
            {**command, "profile": "F01"},
            {**command, "fixture_spec_sha256": "0" * 64},
            {**command, "provider": "foreign"},
        ):
            with self.assertRaises(ContractValidationError):
                self.package.validate_normalized_command(changed)
        with self.assertRaises(ContractValidationError):
            self.package.schema("unknown")


if __name__ == "__main__":
    unittest.main()
