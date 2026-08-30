"""Exact, fixture-only contract package loader for K0a-02.

This is intentionally not a registry or schema-compiler framework.  It loads
one pinned JSON package and implements only the finite validation vocabulary
used by that package.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping


PINNED_PACKAGE_ID = "pipeline-v2.k0a02.f00-contract-package"
PINNED_PACKAGE_VERSION = "1.0.0"
PINNED_PACKAGE_SHA256 = "5b8b677aa98416d85db29a12bb0369e98369dcdfae98249dfaf813eeb08a19c6"
PINNED_PROFILE = "F00"
PINNED_ROLES = ("S0", "synthetic_Layer0", "fixture_worker")
PINNED_ROUTE = (
    "command",
    "S0",
    "synthetic_Layer0",
    "fixture_worker",
    "bootstrap_sink",
    "bootstrap_readback",
)
PINNED_EVENTS = (
    "command.received",
    "run.started",
    "artifact.version_created",
    "handoff.ready",
    "run.completed",
)
PINNED_OWNER = "fixture.bootstrap_worker"
PINNED_MEDIA_TYPE = "text/plain"
PINNED_ARTIFACT_TYPE = "bootstrap.synthetic_result"
PINNED_MODEL_CHANNEL = "future:f00-primary-v1"
PACKAGE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "k0a02"
    / "f00-contract-package-v1.json"
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
_PACKAGE_LOAD_TOKEN = object()


class ContractError(RuntimeError):
    """The only K0a-02 contract is absent, stale, widened, or malformed."""


class ContractHashMismatch(ContractError):
    """A package, contract, prompt, or schema hash is not exact."""


class ContractValidationError(ContractError):
    """A value does not satisfy the one pinned contract package."""


@dataclass(frozen=True)
class Identity:
    id: str
    version: str
    sha256: str


@dataclass(frozen=True)
class ResponseIdentity:
    invocation_id: str
    run_id: str
    triggering_event_id: str


def sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8", errors="strict")).hexdigest()


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ContractValidationError("value is not canonical JSON-compatible") from exc


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ContractValidationError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ContractValidationError(f"{label} fields differ: missing={missing}, extra={extra}")
    return value


def _text(value: Any, label: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise ContractValidationError(f"{label} must be non-empty text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ContractValidationError(f"{label} must be strict UTF-8 text") from exc
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ContractValidationError(f"{label} must be lowercase SHA-256")
    return value


class PinnedContractPackage:
    """Validated immutable view of the sole F00 package."""

    def __init__(
        self,
        data: Mapping[str, Any],
        complete_file_sha256: str,
        *,
        _load_token: object | None = None,
    ):
        if _load_token is not _PACKAGE_LOAD_TOKEN:
            raise ContractValidationError(
                "PinnedContractPackage must be created by the exact-byte package loader"
            )
        if complete_file_sha256 != PINNED_PACKAGE_SHA256:
            raise ContractHashMismatch("constructed package hash is not the pinned complete-file hash")
        data = _validate_package(data)
        # Retain no caller-owned mutable mappings.  Accessors decode a fresh
        # view so a consumer cannot widen a live contract/schema after load.
        self.__data_json = json.dumps(
            data,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        self.__complete_file_sha256 = complete_file_sha256

    def _data(self) -> Mapping[str, Any]:
        value = json.loads(self.__data_json)
        assert isinstance(value, dict)
        return value

    @property
    def complete_file_sha256(self) -> str:
        return self.__complete_file_sha256

    @property
    def package_identity(self) -> Identity:
        return Identity(PINNED_PACKAGE_ID, PINNED_PACKAGE_VERSION, self.complete_file_sha256)

    @property
    def fixture_binding(self) -> Mapping[str, Any]:
        return self._data()["fixture_binding"]

    @property
    def artifact_profile(self) -> Mapping[str, Any]:
        return self._data()["artifact_profile"]

    @property
    def capability_profile(self) -> Mapping[str, Any]:
        return self._data()["capability_profile"]

    @property
    def model_profile(self) -> Mapping[str, Any]:
        return self._data()["model_profile"]

    @property
    def event_profile(self) -> Mapping[str, Any]:
        return self._data()["event_profile"]

    def actor(self, role: str) -> Mapping[str, Any]:
        if role not in PINNED_ROLES:
            raise ContractValidationError(f"unknown or forbidden role {role!r}")
        return self._data()["actors"][role]

    def actor_contract_identity(self, role: str) -> Identity:
        actor = self.actor(role)
        return Identity(actor["contract_id"], actor["contract_version"], actor["contract_sha256"])

    def prompt(self, role: str) -> Mapping[str, Any]:
        actor = self.actor(role)
        return self._data()["prompts"][actor["prompt_ref"]]

    def prompt_identity(self, role: str) -> Identity:
        prompt = self.prompt(role)
        return Identity(prompt["id"], prompt["version"], prompt["sha256"])

    def schema(self, ref: str) -> Mapping[str, Any]:
        schemas = self._data()["schemas"]
        if ref not in schemas:
            raise ContractValidationError(f"unknown or forbidden schema ref {ref!r}")
        return schemas[ref]

    def schema_identity(self, ref: str) -> Identity:
        schema = self.schema(ref)
        return Identity(schema["id"], schema["version"], schema["sha256"])

    def result_schema_identity(self, role: str) -> Identity:
        return self.schema_identity(self.actor(role)["result_schema_ref"])

    def require_package_identity(self, identity: Identity) -> None:
        if identity != self.package_identity:
            raise ContractHashMismatch("contract package ID/version/hash is not the pinned identity")

    def require_prompt_identity(self, role: str, identity: Identity) -> None:
        if identity != self.prompt_identity(role):
            raise ContractHashMismatch(f"{role} prompt ID/version/hash is not pinned")

    def require_result_schema_identity(self, role: str, identity: Identity) -> None:
        if identity != self.result_schema_identity(role):
            raise ContractHashMismatch(f"{role} result schema ID/version/hash is not pinned")

    def validate(self, schema_ref: str, value: Any) -> Any:
        _validate_schema(value, self.schema(schema_ref)["schema"], schema_ref)
        return value

    def validate_normalized_command(self, value: Any) -> Mapping[str, Any]:
        result = self.validate("normalized_f00_command", value)
        assert isinstance(result, dict)
        if result["fixture_spec_sha256"] != self.fixture_binding["fixture_spec_sha256"]:
            raise ContractValidationError("normalized command fixture spec is stale or foreign")
        return result

    def validate_actor_input(self, role: str, value: Any) -> Mapping[str, Any]:
        actor = self.actor(role)
        result = self.validate(actor["allowed_input_schema_ref"], value)
        assert isinstance(result, dict)
        if role == "fixture_worker" and sha256_text(
            result["fixture_input"]["content_text"]
        ) != result["fixture_input"]["content_sha256"]:
            raise ContractValidationError("fixture worker input content hash is wrong")
        return result

    def validate_response(
        self,
        role: str,
        response_text: str,
        identity: ResponseIdentity,
    ) -> Mapping[str, Any]:
        _text(response_text, "actor response", nonempty=False)
        try:
            value = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"{role} response is not JSON") from exc
        actor = self.actor(role)
        self.validate(actor["result_schema_ref"], value)
        assert isinstance(value, dict)
        if (
            value["invocation_id"] != identity.invocation_id
            or value["run_id"] != identity.run_id
            or value["triggering_event_id"] != identity.triggering_event_id
        ):
            raise ContractValidationError(f"{role} response identity echo is wrong")
        if value["type"] != actor["allowed_output_type"]:
            raise ContractValidationError(f"{role} output type is not allowed")
        if value["action"] != actor["allowed_action"]:
            raise ContractValidationError(f"{role} action is not allowed")
        if role in {"S0", "synthetic_Layer0"} and value["route"] != actor["allowed_route"]:
            raise ContractValidationError(f"{role} route is not allowed")
        if role == "fixture_worker":
            artifact = self.artifact_profile
            result_schema = self.schema_identity(artifact["schema_ref"])
            expected = {
                "artifact_type": artifact["artifact_type"],
                "logical_owner": artifact["logical_owner"],
                "media_type": artifact["media_type"],
                "result_schema_id": result_schema.id,
                "result_schema_version": result_schema.version,
                "result_schema_sha256": result_schema.sha256,
            }
            if any(value[name] != expected_value for name, expected_value in expected.items()):
                raise ContractValidationError("fixture worker widened artifact owner/media/schema")
            if sha256_text(value["content_text"]) != value["content_sha256"]:
                raise ContractValidationError("fixture worker content hash does not match exact text")
        return value


def _validate_schema(value: Any, schema: Any, label: str) -> None:
    if not isinstance(schema, dict) or "type" not in schema:
        raise ContractValidationError(f"{label} schema is outside the finite validator vocabulary")
    expected_type = schema["type"]
    if expected_type == "object":
        if not isinstance(value, dict):
            raise ContractValidationError(f"{label} must be an object")
        properties = schema.get("properties")
        required = schema.get("required")
        if properties is None:
            return
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise ContractValidationError(f"{label} object schema is malformed")
        if schema.get("additionalProperties") is not False:
            raise ContractValidationError(f"{label} must fail closed on additional properties")
        if set(value) != set(required) or set(required) != set(properties):
            missing = sorted(set(required) - set(value))
            extra = sorted(set(value) - set(required))
            raise ContractValidationError(f"{label} fields differ: missing={missing}, extra={extra}")
        for name, child_schema in properties.items():
            _validate_schema(value[name], child_schema, f"{label}.{name}")
        return
    if expected_type == "string":
        text = _text(value, label, nonempty=False)
        if "const" in schema and text != schema["const"]:
            raise ContractValidationError(f"{label} is not the pinned constant")
        if len(text) < schema.get("minLength", 0) or len(text) > schema.get("maxLength", len(text)):
            raise ContractValidationError(f"{label} length is outside the pinned bound")
        pattern = schema.get("pattern")
        if pattern is not None and re.fullmatch(pattern, text) is None:
            raise ContractValidationError(f"{label} does not match the pinned pattern")
        return
    if expected_type == "boolean":
        if type(value) is not bool:
            raise ContractValidationError(f"{label} must be a boolean")
        if "const" in schema and value is not schema["const"]:
            raise ContractValidationError(f"{label} is not the pinned constant")
        return
    if expected_type == "array":
        if not isinstance(value, list):
            raise ContractValidationError(f"{label} must be an array")
        return
    raise ContractValidationError(f"{label} uses an unsupported schema type {expected_type!r}")


def _validate_package(data: Any) -> Mapping[str, Any]:
    top = _exact_keys(
        data,
        {
            "actors",
            "artifact_profile",
            "capability_profile",
            "event_profile",
            "fixture_binding",
            "model_profile",
            "package_id",
            "package_version",
            "profile",
            "prompts",
            "route",
            "schemas",
        },
        "contract package",
    )
    if (
        top["package_id"] != PINNED_PACKAGE_ID
        or top["package_version"] != PINNED_PACKAGE_VERSION
        or top["profile"] != PINNED_PROFILE
        or tuple(top["route"]) != PINNED_ROUTE
    ):
        raise ContractValidationError("contract package identity/profile/route is stale or widened")

    actors = _exact_keys(top["actors"], set(PINNED_ROLES), "actors")
    actor_keys = {
        "allowed_action",
        "allowed_input_schema_ref",
        "allowed_output_type",
        "allowed_route",
        "contract_id",
        "contract_sha256",
        "contract_version",
        "prompt_ref",
        "result_schema_ref",
        "role",
    }
    for role in PINNED_ROLES:
        actor = _exact_keys(actors[role], actor_keys, f"actor {role}")
        if actor["role"] != role or actor["contract_version"] != "1.0.0":
            raise ContractValidationError(f"actor {role} identity is stale")
        declared_hash = _hash(actor["contract_sha256"], f"actor {role} contract hash")
        payload = {key: value for key, value in actor.items() if key != "contract_sha256"}
        if sha256_text(canonical_json(payload)) != declared_hash:
            raise ContractHashMismatch(f"actor {role} contract hash mismatch")

    prompts = _exact_keys(top["prompts"], {"s0", "synthetic_layer0", "fixture_worker"}, "prompts")
    prompt_keys = {"id", "version", "sha256", "text"}
    for ref, prompt_value in prompts.items():
        prompt = _exact_keys(prompt_value, prompt_keys, f"prompt {ref}")
        if prompt["version"] != "1.0.0":
            raise ContractValidationError(f"prompt {ref} version is stale")
        if sha256_text(_text(prompt["text"], f"prompt {ref}")) != _hash(
            prompt["sha256"], f"prompt {ref} hash"
        ):
            raise ContractHashMismatch(f"prompt {ref} hash mismatch")

    if not isinstance(top["schemas"], dict) or not top["schemas"]:
        raise ContractValidationError("schemas must be a non-empty exact object")
    schema_keys = {"id", "version", "sha256", "schema"}
    for ref, schema_value in top["schemas"].items():
        schema = _exact_keys(schema_value, schema_keys, f"schema {ref}")
        if schema["version"] != "1.0.0":
            raise ContractValidationError(f"schema {ref} version is stale")
        declared_hash = _hash(schema["sha256"], f"schema {ref} hash")
        if sha256_text(canonical_json(schema["schema"])) != declared_hash:
            raise ContractHashMismatch(f"schema {ref} hash mismatch")

    for role in PINNED_ROLES:
        actor = actors[role]
        if actor["prompt_ref"] not in prompts:
            raise ContractValidationError(f"actor {role} prompt ref is unknown")
        for ref_name in ("allowed_input_schema_ref", "result_schema_ref"):
            if actor[ref_name] not in top["schemas"]:
                raise ContractValidationError(f"actor {role} schema ref is unknown")

    events = _exact_keys(top["event_profile"], set(PINNED_EVENTS), "event profile")
    event_keys = {"payload_schema_ref", "subscriber", "terminal_policy"}
    for event_type, event_value in events.items():
        event = _exact_keys(event_value, event_keys, f"event {event_type}")
        if event["payload_schema_ref"] not in top["schemas"]:
            raise ContractValidationError(f"event {event_type} schema ref is unknown")
    expected_events = {
        "command.received": ("s0_control_delivery", "control_delivery"),
        "run.started": ("bootstrap_readback", "observational_terminal"),
        "artifact.version_created": ("bootstrap_readback", "observational_terminal"),
        "handoff.ready": ("bootstrap_sink", "fixture_terminal"),
        "run.completed": ("bootstrap_readback", "observational_terminal"),
    }
    if any(
        (events[name]["subscriber"], events[name]["terminal_policy"]) != expected
        for name, expected in expected_events.items()
    ):
        raise ContractValidationError("event profile subscriber/terminal policy was widened")

    artifact = _exact_keys(
        top["artifact_profile"],
        {"artifact_type", "encoding", "hash_profile_id", "logical_owner", "media_type", "schema_ref"},
        "artifact profile",
    )
    if (
        artifact["artifact_type"] != PINNED_ARTIFACT_TYPE
        or artifact["logical_owner"] != PINNED_OWNER
        or artifact["media_type"] != PINNED_MEDIA_TYPE
        or artifact["encoding"] != "utf-8"
        or artifact["hash_profile_id"] != "sha256-utf8-v1"
        or artifact["schema_ref"] not in top["schemas"]
    ):
        raise ContractValidationError("artifact profile owner/media/schema is stale or widened")

    capabilities = _exact_keys(
        top["capability_profile"],
        {
            "filesystem_roots",
            "model_channel",
            "policy_version",
            "product_external_side_effects",
            "runtime_enabled",
            "tools",
        },
        "capability profile",
    )
    if (
        capabilities["filesystem_roots"] != []
        or capabilities["tools"] != []
        or capabilities["model_channel"] != PINNED_MODEL_CHANNEL
        or capabilities["product_external_side_effects"] is not False
        or capabilities["runtime_enabled"] is not False
    ):
        raise ContractValidationError("capability profile is not deny-all/scripted-only")

    model = _exact_keys(
        top["model_profile"],
        {
            "context_limit_tokens",
            "execution_mode",
            "model_identifier",
            "model_profile",
            "parameters",
            "provider",
        },
        "model profile",
    )
    if (
        model["provider"] != PINNED_MODEL_CHANNEL
        or model["execution_mode"] != "scripted_fixture_only"
        or model["model_profile"] != "k0a02-scripted-no-network-v1"
        or model["model_identifier"] != "scripted-response-v1"
        or model["parameters"] != {"temperature": 0, "top_p": 1}
        or model["context_limit_tokens"] != 4096
    ):
        raise ContractValidationError("model profile is stale, unknown, or widened")

    fixture = _exact_keys(
        top["fixture_binding"],
        {"canonical_fixture_commit", "canonical_fixture_tree", "fixture_spec_sha256", "fixture_version"},
        "fixture binding",
    )
    if fixture != {
        "canonical_fixture_commit": "192a5b1e9e312b78c310184cde0fc3377c51ab1b",
        "canonical_fixture_tree": "93a9b120c6284bb4b094ab1efd3784582597452d",
        "fixture_spec_sha256": "6b188e11fa1ea35dbd8b487956e82e0d2ad05d06f5121b1c330b56cd6b3f4a8a",
        "fixture_version": "1.0.0",
    }:
        raise ContractValidationError("fixture binding is stale or foreign")
    return top


def load_contract_package(path: str | Path | None = None) -> PinnedContractPackage:
    package_path = PACKAGE_PATH if path is None else Path(path)
    try:
        payload = package_path.read_bytes()
    except OSError as exc:
        raise ContractError("pinned K0a-02 contract package is unavailable") from exc
    if payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload:
        raise ContractValidationError("contract package must be UTF-8 without BOM and LF-only")
    complete_hash = sha256(payload).hexdigest()
    if complete_hash != PINNED_PACKAGE_SHA256:
        raise ContractHashMismatch(
            f"contract package hash mismatch: expected {PINNED_PACKAGE_SHA256}, got {complete_hash}"
        )
    try:
        text = payload.decode("utf-8", errors="strict")
        data = json.loads(text)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractValidationError("contract package is not strict UTF-8 JSON") from exc
    return PinnedContractPackage(data, complete_hash, _load_token=_PACKAGE_LOAD_TOKEN)
