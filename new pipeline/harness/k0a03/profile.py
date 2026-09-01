"""Pinned K0a-03 manual VS Code extension execution profile."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from harness.k0a02.contract import ContractHashMismatch, ContractValidationError, load_contract_package


PROFILE_PATH = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "k0a03"
    / "manual-extension-profile-v1.json"
)
PINNED_PROFILE_SHA256 = "2e2bc83038a1985ae8b5e1471737ed24534dac848aa67475fd153cdc486dd56b"
PINNED_EXECUTORS = ("chatgpt_gpt_5_6_sol", "claude_opus_4_6")


@dataclass(frozen=True)
class ExecutorBinding:
    key: str
    extension_id: str
    extension_version: str
    provider: str
    model_profile: str
    model_identifier: str
    parameters: Mapping[str, Any]
    context_limit_tokens: int
    tool_enforcement: str
    capture_completeness: str
    gap_code: str | None


class ManualExecutionProfile:
    def __init__(self, data: Mapping[str, Any], complete_file_sha256: str) -> None:
        self._data = json.loads(json.dumps(data, separators=(",", ":")))
        self.complete_file_sha256 = complete_file_sha256

    @property
    def policy_version(self) -> str:
        return self._data["policy_version"]

    @property
    def execution_mode(self) -> str:
        return self._data["execution_mode"]

    @property
    def physical_invocation_budget(self) -> Mapping[str, int]:
        return dict(self._data["physical_invocation_budget"])

    def executor(self, key: str) -> ExecutorBinding:
        if key not in PINNED_EXECUTORS:
            raise ContractValidationError("executor is not in the pinned K0a-03 allowlist")
        value = self._data["executors"][key]
        return ExecutorBinding(key=key, **value)


def _validate(data: Any) -> Mapping[str, Any]:
    expected = {
        "base_contract_package_sha256",
        "execution_mode",
        "executors",
        "physical_invocation_budget",
        "policy_version",
        "profile",
        "profile_id",
        "profile_version",
        "roles",
        "switch_policy",
    }
    if not isinstance(data, dict) or set(data) != expected:
        raise ContractValidationError("K0a-03 profile fields are incomplete or widened")
    base = load_contract_package()
    if data["base_contract_package_sha256"] != base.complete_file_sha256:
        raise ContractHashMismatch("K0a-03 base contract package binding is stale")
    if (
        data["profile_id"] != "pipeline-v2.k0a03.manual-extension-profile"
        or data["profile_version"] != "1.0.0"
        or data["profile"] != "F00"
        or data["execution_mode"] != "manual_extension_handoff_v1"
        or data["policy_version"] != "k0a03-f00-manual-extension-deny-all-v1"
        or data["roles"] != ["S0", "synthetic_Layer0", "fixture_worker"]
        or data["switch_policy"]
        != "only_after_accepted_after_replay_before_next_prepare"
        or data["physical_invocation_budget"] != {"nominal": 3, "worst_case": 6}
    ):
        raise ContractValidationError("K0a-03 profile identity, route, or budget is stale")
    if not isinstance(data["executors"], dict) or tuple(data["executors"]) != PINNED_EXECUTORS:
        raise ContractValidationError("K0a-03 executor allowlist differs")
    expected_keys = {
        "capture_completeness",
        "context_limit_tokens",
        "extension_id",
        "extension_version",
        "gap_code",
        "model_identifier",
        "model_profile",
        "parameters",
        "provider",
        "tool_enforcement",
    }
    exact = {
        "chatgpt_gpt_5_6_sol": {
            "capture_completeness": "typed_gap",
            "context_limit_tokens": 32768,
            "extension_id": "openai.chatgpt",
            "extension_version": "26.825.51511",
            "gap_code": "chatgpt_tools_contract_forbidden_not_machine_disabled",
            "model_identifier": "gpt-5.6-sol",
            "model_profile": "chatgpt-gpt-5.6-sol-read-only-v1",
            "parameters": {},
            "provider": "openai.chatgpt-vscode-extension",
            "tool_enforcement": "contract_forbidden_audited_zero_calls",
        },
        "claude_opus_4_6": {
            "capture_completeness": "complete_harness_visible",
            "context_limit_tokens": 32768,
            "extension_id": "anthropic.claude-code",
            "extension_version": "2.1.251",
            "gap_code": None,
            "model_identifier": "claude-opus-4-6",
            "model_profile": "claude-opus-4.6-tools-disabled-v1",
            "parameters": {},
            "provider": "anthropic.claude-code-vscode-extension",
            "tool_enforcement": "process_flag_disable_all",
        },
    }
    for key in PINNED_EXECUTORS:
        value = data["executors"][key]
        if not isinstance(value, dict) or set(value) != expected_keys or value != exact[key]:
            raise ContractValidationError(f"K0a-03 executor {key} is stale or widened")
    return data


def load_execution_profile(path: str | Path | None = None) -> ManualExecutionProfile:
    profile_path = PROFILE_PATH if path is None else Path(path)
    try:
        payload = profile_path.read_bytes()
    except OSError as exc:
        raise ContractValidationError("pinned K0a-03 execution profile is unavailable") from exc
    if payload.startswith(b"\xef\xbb\xbf") or b"\r" in payload:
        raise ContractValidationError("K0a-03 profile must be strict UTF-8, BOM-free, LF-only")
    digest = sha256(payload).hexdigest()
    if digest != PINNED_PROFILE_SHA256:
        raise ContractHashMismatch(
            f"K0a-03 profile hash mismatch: expected {PINNED_PROFILE_SHA256}, got {digest}"
        )
    try:
        data = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractValidationError("K0a-03 profile is not strict JSON") from exc
    return ManualExecutionProfile(_validate(data), digest)
