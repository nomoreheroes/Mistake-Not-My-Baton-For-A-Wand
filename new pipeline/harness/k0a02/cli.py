"""Basic K0a-02 CLI with the exact grammar: initialize | run | inspect."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable, Sequence, TextIO

from .adapters import ScriptedAdapter
from .contract import PinnedContractPackage, load_contract_package
from .orchestrator import K0a02Harness


HarnessFactory = Callable[[PinnedContractPackage], K0a02Harness]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline-v2-k0a02", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("initialize", "run", "inspect"):
        commands.add_parser(name, allow_abbrev=False)
    return parser


def _default_harness(package: PinnedContractPackage) -> K0a02Harness:
    return K0a02Harness(ScriptedAdapter.nominal(package), package=package)


def main(
    argv: Sequence[str] | None = None,
    *,
    cwd: Path | None = None,
    harness_factory: HarnessFactory = _default_harness,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    arguments = _parser().parse_args(argv)
    runtime_root = cwd if cwd is not None else Path.cwd()
    runtime_root = runtime_root.absolute()
    try:
        package = load_contract_package()
        harness = harness_factory(package)
        if arguments.command == "initialize":
            binding = harness.initialize(runtime_root)
            result = {
                "command": "initialize",
                "contract_package_sha256": package.complete_file_sha256,
                "database": str(binding.database_path),
                "fixture_commit": binding.guard_proof.runtime_fixture.commit,
                "pipeline_commit": binding.guard_proof.pipeline.commit,
                "status": "initialized",
            }
        elif arguments.command == "run":
            run = harness.run(
                runtime_root,
                {
                    "command": "bootstrap",
                    "fixture_spec_sha256": package.fixture_binding["fixture_spec_sha256"],
                    "profile": "F00",
                    "type": "normalized_f00_command",
                },
            )
            result = {
                "artifact_version_id": run.artifact_version_id,
                "command": "run",
                "network_calls": run.network_calls,
                "readback_gate_id": run.readback_gate_id,
                "run_id": run.run_id,
                "runtime_model_invocations": run.runtime_model_invocations,
                "sink_acceptance_id": run.sink_acceptance_id,
                "state": run.inspect["run"]["state"],
            }
        else:
            result = harness.inspect(runtime_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")), file=stdout)
        return 0
    except Exception as exc:  # exact boundary: concise typed CLI rejection, no traceback
        print(f"pipeline-v2-k0a02: {exc}", file=stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
