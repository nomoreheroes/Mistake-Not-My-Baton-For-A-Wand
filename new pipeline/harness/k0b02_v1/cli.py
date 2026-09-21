from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

if __package__ in (None, ""):
    spec = importlib.util.spec_from_file_location(
        "k0b02_v1",
        Path(__file__).with_name("__init__.py"),
        submodule_search_locations=[str(Path(__file__).parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("closed package loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    __package__ = spec.name

from .budget_compiler import compile_b, integrated_manifest
from .canonical import ContractError, json_bytes, require, sha256
from .contract import InputContext
from .registry_compiler import FAMILIES as A_FAMILIES, compile_a
from .budget_compiler import FAMILIES as B_FAMILIES
from .store import K0b02Store


FILENAMES = {
    "compiled_artifact_event_profile": "compiled_artifact_event_profile.json",
    "compiled_event_reachability_graph": "compiled_event_reachability_graph.json",
    "compiled_subscription_terminal_snapshot": "compiled_subscription_terminal_snapshot.json",
    "compiled_s_route_table_v2": "compiled_s_route_table_v2.json",
    "compiled_fanout_barrier_profile": "compiled_fanout_barrier_profile.json",
    "compiled_projection_checkpoint_profile": "compiled_projection_checkpoint_profile.json",
    "compiled_resource_forecast": "compiled_resource_forecast.json",
    "compiled_checkpoint_phase_partition_v1": "compiled_checkpoint_phase_partition_v1.json",
    "compiled_checkpoint_publication_budget_v2": "compiled_checkpoint_publication_budget_v2.json",
}
ROOTS = {
    "environment_A": Path(
        "C:/Users/Administrator/AppData/Local/Temp/2/pipeline-v2-k0b02-artifact-event-implementation-v1-a"
    ),
    "environment_B": Path(
        "C:/Users/Administrator/AppData/Local/Temp/2/pipeline-v2-k0b02-artifact-event-implementation-v1-b"
    ),
}


def _path(path: Path, root: Path, exists: bool = False) -> Path:
    require(path.is_absolute() and path != root, "CLI:absolute_child")
    require(path.resolve().is_relative_to(root.resolve()), "CLI:escape")
    if exists:
        require(path.is_file(), "CLI:missing")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        require(not path.exists() and not path.is_symlink(), "CLI:existing_output")
    return path


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument(
        "mode", choices=("validate-inputs", "compile-all", "init-db", "audit-db")
    )
    p.add_argument("--repository-root", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--runtime-root", type=Path, required=True)
    p.add_argument("--environment", choices=tuple(ROOTS), required=True)
    p.add_argument("--output-dir", type=Path)
    p.add_argument("--database", type=Path)
    p.add_argument("--target-version", type=int, default=6)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        require(
            args.repository_root.is_absolute() and args.runtime_root.is_absolute(),
            "CLI:absolute",
        )
        require(
            args.runtime_root.resolve() == ROOTS[args.environment].resolve(),
            "CLI:denied_root",
        )
        context = InputContext(args.repository_root, args.manifest)
        store = K0b02Store(context, args.runtime_root, args.runtime_root)
        if args.mode == "validate-inputs":
            value = {
                "result": "pass",
                "effective_input_count": len(context.pins),
                "frozen_HASH_ONLY_count": len(context.hash_only),
                "manifest_sha256": context.manifest_sha256,
                "runtime_enabled": False,
            }
        elif args.mode == "compile-all":
            require(
                args.output_dir is not None
                and args.output_dir.is_absolute()
                and args.output_dir.resolve() != args.runtime_root.resolve()
                and args.output_dir.resolve().is_relative_to(
                    args.runtime_root.resolve()
                ),
                "CLI:output_dir",
            )
            args.output_dir.mkdir(parents=True, exist_ok=True)
            a, receipt_a = compile_a(context)
            for name in A_FAMILIES:
                (args.output_dir / FILENAMES[name]).write_bytes(a[name])
            a_path = (
                args.output_dir / "k0b-02-registry-routing-compiler-receipt-v3.yaml"
            )
            a_path.write_bytes(receipt_a)
            b, receipt_b = compile_b(context, receipt_a)
            for name in B_FAMILIES:
                (args.output_dir / FILENAMES[name]).write_bytes(b[name])
            b_path = args.output_dir / "k0b-02-resource-budget-compiler-receipt-v3.yaml"
            b_path.write_bytes(receipt_b)
            manifest = integrated_manifest(context, receipt_a, receipt_b, {**a, **b})
            m_path = args.output_dir / "k0b-02-compiled-output-manifest-v3.yaml"
            m_path.write_bytes(manifest)
            value = {
                "result": "pass",
                "output_count": 9,
                "receipt_A_sha256": sha256(receipt_a),
                "receipt_B_sha256": sha256(receipt_b),
                "integrated_manifest_sha256": sha256(manifest),
                "runtime_enabled": False,
            }
        else:
            require(args.database is not None, "CLI:database")
            database = _path(
                args.database, args.runtime_root, exists=args.mode == "audit-db"
            )
            value = (
                store.initialize_to_version(database, args.target_version)
                if args.mode == "init-db"
                else store.audit(database)
            )
        print(json_bytes(value).decode("utf-8"), end="")
        return 0
    except (ContractError, OSError, KeyError, TypeError, ValueError) as exc:
        print(
            json_bytes(
                {"result": "fail", "error": str(exc), "runtime_enabled": False}
            ).decode("utf-8"),
            end="",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
