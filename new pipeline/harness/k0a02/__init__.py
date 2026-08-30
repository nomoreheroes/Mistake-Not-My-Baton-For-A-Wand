"""Public fixture-only K0a-02 surface."""

from .adapters import AdapterError, AdapterRequest, AdapterReceipt, ModelAdapter, ScriptedAdapter
from .contract import (
    ContractError,
    ContractHashMismatch,
    ContractValidationError,
    Identity,
    PINNED_PACKAGE_SHA256,
    ResponseIdentity,
    canonical_json,
    load_contract_package,
    sha256_text,
)
from .guards import GuardError, GuardProof, RepositoryIdentity, RootGuard
from .orchestrator import BootstrapSink, K0a02Harness, OrchestrationError, RunResult, RuntimeBinding
from .security import SensitiveDataError, scan_untrusted_text
from .store import K0a02Store, ReadbackGate, SinkAcceptance

__all__ = [
    "AdapterError",
    "AdapterReceipt",
    "AdapterRequest",
    "BootstrapSink",
    "ContractError",
    "ContractHashMismatch",
    "ContractValidationError",
    "GuardError",
    "GuardProof",
    "Identity",
    "K0a02Harness",
    "K0a02Store",
    "ModelAdapter",
    "OrchestrationError",
    "PINNED_PACKAGE_SHA256",
    "ReadbackGate",
    "RepositoryIdentity",
    "ResponseIdentity",
    "RootGuard",
    "RunResult",
    "RuntimeBinding",
    "ScriptedAdapter",
    "SensitiveDataError",
    "SinkAcceptance",
    "canonical_json",
    "load_contract_package",
    "scan_untrusted_text",
    "sha256_text",
]
