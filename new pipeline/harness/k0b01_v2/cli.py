from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


if __package__ in (None, ""):
    spec = importlib.util.spec_from_file_location(
        "k0b01_v2",
        Path(__file__).with_name("__init__.py"),
        submodule_search_locations=[str(Path(__file__).parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("closed package loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    __package__ = spec.name

from .binary_budget import validate_actual, validate_definition
from .budget_compiler import compile_budget
from .canonical import ContractError, json_bytes, load_json, no_reparse, require, sha256
from .contract import InputContext
from .registry_compiler import aggregate, compile_registry
from .store import AlphaStore


def temp_file(path: Path, target: Path, *, exists: bool) -> Path:
    require(
        path.is_absolute()
        and path.is_relative_to(target / ".tmp")
        and path != target / ".tmp",
        "CLI:exact_temp_output",
    )
    no_reparse(target)
    no_reparse(path.parent)
    require(
        path.parent.resolve().is_relative_to(target / ".tmp"), "CLI:temp_parent_escape"
    )
    if exists:
        no_reparse(path)
        require(path.is_file(), "CLI:temp_input_file")
    else:
        require(not path.exists() and not path.is_symlink(), "CLI:existing_output")
    return path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Closed K0b-01 static compilation and synthetic migration only"
    )
    result.add_argument(
        "mode",
        choices=(
            "validate-inputs",
            "compile-registry",
            "compile-budget",
            "validate-binary",
            "verify-schema",
            "migrate-synthetic",
        ),
    )
    result.add_argument("--repository-root", type=Path, required=True)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--source-pins", type=Path, required=True)
    result.add_argument(
        "--environment", choices=("environment_A", "environment_B"), required=True
    )
    result.add_argument("--temp-target", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--receipt-a", type=Path)
    result.add_argument("--accepted-a-sha256")
    result.add_argument("--aggregate-output", type=Path)
    result.add_argument("--definition", type=Path)
    result.add_argument("--actual-objects", type=Path)
    result.add_argument("--database", type=Path)
    result.add_argument("--backup", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        require(
            args.temp_target.is_absolute()
            and args.temp_target
            == Path(
                "C:/Users/Administrator/AppData/Local/Temp/2/pipeline-v2-k0b01-final-disposition-implementation-v1-"
                + ("a" if args.environment == "environment_A" else "b"),
            ),
            "CLI:target_identity",
        )
        output = temp_file(args.output, args.temp_target, exists=False)
        pins_path = temp_file(args.source_pins, args.temp_target, exists=True)
        context = InputContext(
            args.repository_root, args.manifest, load_json(pins_path.read_bytes())
        )
        approved_root = Path(context.manifest["runtime_roots"][args.environment])
        require(
            approved_root == args.temp_target / ".tmp/runtime", "CLI:approved_target"
        )
        if args.mode == "validate-inputs":
            raw = json_bytes(
                {
                    "result": "pass",
                    "source_count": len(context.source_pins),
                    "existing_count": 193,
                    "frozen_hash_only_count": 18,
                    "input_manifest_sha256": context.manifest_sha256,
                    "runtime_enabled": False,
                }
            )
        elif args.mode == "compile-registry":
            raw = compile_registry(context)
        elif args.mode == "compile-budget":
            require(
                args.receipt_a is not None
                and args.accepted_a_sha256 is not None
                and args.aggregate_output is not None,
                "CLI:accepted_A_and_aggregate_required",
            )
            receipt_a = temp_file(
                args.receipt_a, args.temp_target, exists=True
            ).read_bytes()
            aggregate_path = temp_file(
                args.aggregate_output, args.temp_target, exists=False
            )
            raw = compile_budget(context, receipt_a, args.accepted_a_sha256)
            aggregate_raw = aggregate(
                context, receipt_a, args.accepted_a_sha256, raw, sha256(raw)
            )
            aggregate_path.write_bytes(aggregate_raw)
        elif args.mode == "validate-binary":
            require(args.definition is not None, "CLI:definition_required")
            definition = load_json(
                temp_file(args.definition, args.temp_target, exists=True).read_bytes()
            )
            result = validate_definition(definition)
            if args.actual_objects is not None:
                objects = load_json(
                    temp_file(
                        args.actual_objects, args.temp_target, exists=True
                    ).read_bytes()
                )
                require(
                    isinstance(objects, list)
                    and all(isinstance(p, str) for p in objects),
                    "CLI:actual_object_paths",
                )
                result["actual"] = validate_actual(
                    [
                        temp_file(Path(p), args.temp_target, exists=True).read_bytes()
                        for p in objects
                    ],
                    definition,
                )
            raw = json_bytes(
                {"result": "pass", "binary": result, "runtime_enabled": False}
            )
        else:
            require(args.database is not None, "CLI:database_required")
            store = AlphaStore(context, approved_root, args.environment)
            if args.mode == "verify-schema":
                result = store.audit(args.database)
            else:
                require(args.backup is not None, "CLI:backup_required")
                result = store.initialize(args.database, args.backup)
            raw = json_bytes(
                {"result": "pass", "migration": result, "runtime_enabled": False}
            )
        output.write_bytes(raw)
        print(
            json_bytes(
                {
                    "result": "pass",
                    "mode": args.mode,
                    "output_sha256": sha256(raw),
                    "output_bytes": len(raw),
                    "runtime_enabled": False,
                }
            ).decode("utf-8"),
            end="",
        )
        return 0
    except (ContractError, OSError, KeyError, TypeError) as exc:
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
