from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical import canonical_bytes, load_strict, sha256_file, write_new_canonical
from contract import validate_detector_profile


OUTPUT_NAMES = [
    "compiled-detector-profile.json",
    "compiled-hash-profile-map.json",
    "compiled-repository-tool-policy.json",
    "compiled-contract-manifest.json",
]


def _binding(repository_root: Path, relative_path: str) -> dict[str, Any]:
    path = repository_root / relative_path
    return {"path": relative_path, "sha256": sha256_file(path), "bytes": path.stat().st_size}


def compile_package(repository_root: Path, output_root: Path) -> dict[str, dict[str, Any]]:
    detector_path = repository_root / "new pipeline/registry/k0b03/detector-profile-v1.json"
    hash_path = repository_root / "new pipeline/registry/k0b03/hash-profile-registry-v1.json"
    policy_path = repository_root / "new pipeline/registry/k0b03/repository-tool-policy-v1.json"
    package_path = repository_root / "new pipeline/contracts/k0b03/k0b03-contract-package-v1.json"
    detector = validate_detector_profile(load_strict(detector_path))
    hash_profiles = load_strict(hash_path)
    policy = load_strict(policy_path)
    package = load_strict(package_path)
    schemas = [_binding(repository_root, path) for path in sorted(package["schemas"])]
    migration = _binding(repository_root, package["migration"])
    outputs: dict[str, dict[str, Any]] = {
        OUTPUT_NAMES[0]: {"compiled_profile_version":"1.0.0","source":_binding(repository_root, detector_path.relative_to(repository_root).as_posix()),"profile":detector},
        OUTPUT_NAMES[1]: {"compiled_profile_version":"1.0.0","source":_binding(repository_root, hash_path.relative_to(repository_root).as_posix()),"profiles":hash_profiles["profiles"]},
        OUTPUT_NAMES[2]: {"compiled_profile_version":"1.0.0","source":_binding(repository_root, policy_path.relative_to(repository_root).as_posix()),"policy":policy},
        OUTPUT_NAMES[3]: {"compiled_profile_version":"1.0.0","package":_binding(repository_root, package_path.relative_to(repository_root).as_posix()),"schemas":schemas,"migration":migration},
    }
    output_root.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_NAMES:
        write_new_canonical(output_root / name, outputs[name])
    return outputs


def output_manifest(output_root: Path) -> list[dict[str, Any]]:
    rows = []
    for name in OUTPUT_NAMES:
        data = (output_root / name).read_bytes()
        rows.append({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return rows
