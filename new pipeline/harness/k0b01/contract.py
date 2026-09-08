"""Strict K0b-01 contract and JSON-compatible YAML registry loading."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping


PIPELINE_DIR = Path(__file__).resolve().parents[2]
PACKAGE_PATH = (
    PIPELINE_DIR / "contracts" / "k0b01" / "alpha0-kernel-contract-package-v1.json"
)
EVENT_PROFILE_PATH = PIPELINE_DIR / "registry" / "alpha0" / "event-profile-v1.yaml"
SUBSCRIPTION_PROFILE_PATH = (
    PIPELINE_DIR / "registry" / "alpha0" / "subscription-terminal-profile-v1.yaml"
)
ROUTING_PROFILE_PATH = (
    PIPELINE_DIR / "registry" / "alpha0" / "s-routing-profile-v1.yaml"
)
RESOURCE_POLICY_PATH = PIPELINE_DIR / "registry" / "resource-budget-policy" / "v1.yaml"
REFERENCE_CASES_PATH = (
    PIPELINE_DIR / "registry" / "resource-budget-policy" / "reference-cases-v1.yaml"
)

PINNED_PACKAGE_SHA256 = (
    "fb5c078dc8c10d166ea6b62aeb32183be4197b47dd9fec4df37511d5ef7cc654"
)
PINNED_EVENT_PROFILE_SHA256 = (
    "ae6c93462ecef5e39655103004f7e9b6777f9b8aff9c2dc8488348ede2d987d2"
)
PINNED_SUBSCRIPTION_PROFILE_SHA256 = (
    "62806ad950e1a9a0c17b9d6f885f4af553395db58be9b14634b28e28fca34fab"
)
PINNED_ROUTING_PROFILE_SHA256 = (
    "0d2002f2d09253a04ee7e494b3681e90728850f5e8c1fe8afe762970d9b8cfbf"
)
PINNED_RESOURCE_POLICY_SHA256 = (
    "3db06dce46de067e2fde5bdbbf184fda0da3e7a131a3211d48ba31d8eb8790f9"
)
PINNED_REFERENCE_CASES_SHA256 = (
    "f576d2b25aa9ab934ce8c45b30e3bb0e86cca82743c057f7045cab092c0fdbd1"
)

PINNED_PACKAGE_ID = "pipeline-v2.k0b01.alpha0-kernel-contract-package"
PINNED_PACKAGE_VERSION = "1.0.0"
PINNED_PROFILE = "Alpha0"
EXACT_EVENT_TYPES = (
    "command.received",
    "run.started",
    "artifact.version_created",
    "handoff.ready",
    "run.completed",
    "run.blocked",
    "run.abort_requested",
    "run.aborted",
    "artifact.published",
    "projection.requested",
    "projection.written",
    "projection.failed",
    "revision.requested",
    "gate.passed",
    "approval.requested",
    "approval.granted",
    "approval.rejected",
    "error.schema_mismatch",
    "error.tool_failure",
    "error.security_policy",
    "meta.incident_detected",
)
RETAINED_F00_EVENTS = EXACT_EVENT_TYPES[:5]
EXACT_ROUTE_IDS = (
    "s.alpha0.compiled_nominal.v1",
    "s.alpha0.layer0_fallback.v1",
    "s.alpha0.f04.parallel_review.v1",
    "s.alpha0.f05.revision.v1",
    "s.alpha0.blocked.v1",
)
REQUIRED_OUTPUT_FAMILIES = (
    "compiled_artifact_event_profile",
    "compiled_event_reachability_graph",
    "compiled_subscription_terminal_snapshot",
    "compiled_s_route_table_v2",
    "compiled_fanout_barrier_profile",
    "compiled_resource_forecast",
    "compiled_checkpoint_phase_partition_v1",
    "compiled_checkpoint_publication_budget_v2",
)
CHECKPOINT_PHASE_ORDER = ("K0b-runtime-operational", "K0b-F15-exact-measurement")
F15_TRIGGER_IDS = (
    "k0b.f15.boundary.entry_gate",
    "k0b.f15.boundary.program_owner_wait_or_exit",
    "k0b.f15.boundary.exit_gate",
    "k0b.f15.boundary.top_level_run_end",
)
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class ContractError(RuntimeError):
    """The K0b-01 contract bundle is absent, malformed, stale, or widened."""


class ContractHashMismatch(ContractError):
    """A complete-file or declared content hash differs from its pin."""


class ContractValidationError(ContractError):
    """A contract or registry value is outside the closed K0b-01 vocabulary."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractValidationError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ContractValidationError(
            f"{label} keys must be exactly {sorted(expected)!r}, got {actual!r}"
        )
    return value


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ContractValidationError(f"{label} must be non-empty trimmed text")
    return value


def _hash(value: Any, label: str) -> str:
    text = _nonempty_text(value, label)
    if SHA256_RE.fullmatch(text) is None:
        raise ContractValidationError(f"{label} must be a lowercase SHA-256")
    return text


def load_exact_json(path: Path, expected_sha256: str, label: str) -> Mapping[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ContractError(f"cannot read {label}: {path}") from exc
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ContractValidationError(f"{label} must be UTF-8 without BOM and LF-only")
    actual = sha256_bytes(raw)
    if actual != expected_sha256:
        raise ContractHashMismatch(
            f"{label} complete-file SHA-256 mismatch: expected {expected_sha256}, got {actual}"
        )
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractValidationError(
            f"{label} is not strict JSON-compatible YAML"
        ) from exc
    if not isinstance(value, dict):
        raise ContractValidationError(f"{label} top level must be an object")
    return value


@dataclass(frozen=True)
class ContractBundle:
    package: Mapping[str, Any]
    event_profile: Mapping[str, Any]
    subscription_profile: Mapping[str, Any]
    routing_profile: Mapping[str, Any]
    resource_policy: Mapping[str, Any]
    reference_cases: Mapping[str, Any]
    source_hashes: Mapping[str, str]


def validate_contract_package(package: Mapping[str, Any]) -> None:
    top = _exact_keys(
        package,
        {
            "package_id",
            "package_version",
            "profile",
            "authority",
            "source_registries",
            "schema_contracts",
            "exact_event_types",
            "retained_f00_event_types",
            "exact_s_route_ids",
            "required_compiler_outputs",
            "checkpoint_phase_order",
            "f15_boundary_trigger_ids",
            "capability_policy",
        },
        "contract package",
    )
    if (
        top["package_id"] != PINNED_PACKAGE_ID
        or top["package_version"] != PINNED_PACKAGE_VERSION
        or top["profile"] != PINNED_PROFILE
    ):
        raise ContractValidationError("contract package identity is stale or widened")
    authority = _exact_keys(
        top["authority"],
        {
            "implementation_disposition_sha256",
            "k0b01_plan_sha256",
            "final_k0b00_disposition_sha256",
            "scope_sha256",
            "phase_policy_sha256",
            "forecast_sha256",
            "reconciliation_sha256",
            "executor_profile_sha256",
        },
        "contract authority",
    )
    for name, value in authority.items():
        _hash(value, f"contract authority {name}")
    expected_authority = {
        "implementation_disposition_sha256": "cdb87a83b5bc91ca343a76103252183669dc5da6d03ab9222abb1b81b68fe4dc",
        "k0b01_plan_sha256": "028aa3e3667ff55f92a732d3b2424c704bdb0eaa81268a49c7505cfaa9a2e85f",
        "final_k0b00_disposition_sha256": "544a6160fc27be348794179f44b44080b87bf3f53c0dd1b66baf9c7d1a40fe9d",
        "scope_sha256": "e839396d9199fa85e5474b3a45a852e7b6b59d81d6910ae67897f7dffe627cde",
        "phase_policy_sha256": "ed224c7473810be838c2c22129d567c337bd16fd13532efb893074e684367ce8",
        "forecast_sha256": "ed65d6e3c046c81c2e1e10efd4ac152bba5cd2cc1783b4d6b2102c788accdc8a",
        "reconciliation_sha256": "d3f9bd18ba15c2d7e791a8dc277011711cc8b7ef6788eb4c0ccdfecdfd2f71cb",
        "executor_profile_sha256": "125a1e30e4ca69ab812280a40ff57302a5211cd1b888b23a3e6d9a8620c3898d",
    }
    if dict(authority) != expected_authority:
        raise ContractHashMismatch(
            "contract authority hashes differ from the approved package"
        )
    expected_registry_keys = {
        "event_profile",
        "subscription_terminal_profile",
        "s_routing_profile",
        "resource_budget_policy",
        "resource_budget_reference_cases",
    }
    registries = _exact_keys(
        top["source_registries"], expected_registry_keys, "source registries"
    )
    for name, value in registries.items():
        _nonempty_text(value, f"source registry {name}")
    if tuple(top["exact_event_types"]) != EXACT_EVENT_TYPES:
        raise ContractValidationError("minimal Alpha event set or order differs")
    if tuple(top["retained_f00_event_types"]) != RETAINED_F00_EVENTS:
        raise ContractValidationError("retained F00 event set differs")
    if tuple(top["exact_s_route_ids"]) != EXACT_ROUTE_IDS:
        raise ContractValidationError("S route set or order differs")
    if tuple(top["required_compiler_outputs"]) != REQUIRED_OUTPUT_FAMILIES:
        raise ContractValidationError("compiler output families differ")
    if tuple(top["checkpoint_phase_order"]) != CHECKPOINT_PHASE_ORDER:
        raise ContractValidationError("checkpoint phase order differs")
    if tuple(top["f15_boundary_trigger_ids"]) != F15_TRIGGER_IDS:
        raise ContractValidationError("F15 trigger allowlist differs")
    if (
        len(set(top["exact_event_types"])) != 21
        or len(set(top["f15_boundary_trigger_ids"])) != 4
    ):
        raise ContractValidationError("event or trigger identity is duplicated")
    capability = _exact_keys(
        top["capability_policy"],
        {
            "physical_model_calls",
            "tools",
            "network",
            "runtime_phase_activation",
            "checkpoint_publication",
            "projection_write",
            "allowed_payload_encoding",
        },
        "capability policy",
    )
    if capability != {
        "physical_model_calls": 0,
        "tools": [],
        "network": False,
        "runtime_phase_activation": False,
        "checkpoint_publication": False,
        "projection_write": False,
        "allowed_payload_encoding": "canonical-json-utf8-v1",
    }:
        raise ContractValidationError("K0b-01 capability policy was widened")
    schemas = top["schema_contracts"]
    if not isinstance(schemas, dict) or not schemas:
        raise ContractValidationError("schema contracts must be a non-empty object")


def load_contract_bundle(
    *,
    package_path: Path = PACKAGE_PATH,
    event_profile_path: Path = EVENT_PROFILE_PATH,
    subscription_profile_path: Path = SUBSCRIPTION_PROFILE_PATH,
    routing_profile_path: Path = ROUTING_PROFILE_PATH,
    resource_policy_path: Path = RESOURCE_POLICY_PATH,
    reference_cases_path: Path = REFERENCE_CASES_PATH,
) -> ContractBundle:
    package = load_exact_json(
        package_path, PINNED_PACKAGE_SHA256, "K0b-01 contract package"
    )
    validate_contract_package(package)
    source_specs = (
        ("event_profile", event_profile_path, PINNED_EVENT_PROFILE_SHA256),
        (
            "subscription_profile",
            subscription_profile_path,
            PINNED_SUBSCRIPTION_PROFILE_SHA256,
        ),
        ("routing_profile", routing_profile_path, PINNED_ROUTING_PROFILE_SHA256),
        ("resource_policy", resource_policy_path, PINNED_RESOURCE_POLICY_SHA256),
        ("reference_cases", reference_cases_path, PINNED_REFERENCE_CASES_SHA256),
    )
    documents: dict[str, Mapping[str, Any]] = {}
    hashes: dict[str, str] = {"contract_package": PINNED_PACKAGE_SHA256}
    for name, path, expected_hash in source_specs:
        documents[name] = load_exact_json(path, expected_hash, name.replace("_", " "))
        hashes[name] = expected_hash
    return ContractBundle(package=package, source_hashes=hashes, **documents)
