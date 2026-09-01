"""Closed K0a-03 CLI: fixed runtime cwd and no provider/model/path/SQL options."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Callable, Sequence, TextIO

from .orchestrator import K0a03Harness


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline-k0a03", allow_abbrev=False)
    parser.add_argument("command", choices=("initialize", "run", "inspect"))
    return parser


def _emit(stream: TextIO, value: object) -> None:
    stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")


def main(
    argv: Sequence[str] | None = None,
    *,
    cwd: Path | None = None,
    harness_factory: Callable[[], K0a03Harness] = K0a03Harness,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    arguments = _parser().parse_args(argv)
    runtime = (cwd or Path.cwd()).absolute()
    harness = harness_factory()
    try:
        if arguments.command == "initialize":
            binding = harness.initialize(runtime)
            _emit(
                stdout,
                {
                    "database_path": str(binding.database_path),
                    "fixture_commit": binding.guard_proof.runtime_fixture.commit,
                    "pipeline_commit": binding.guard_proof.pipeline.commit,
                    "status": "initialized",
                    "type": "k0a03_initialize_result",
                },
            )
        elif arguments.command == "run":
            result = harness.run(runtime)
            _emit(
                stdout,
                {
                    "invocation_id": result.invocation_id,
                    "physical_model_invocations": result.physical_model_invocations,
                    "pipeline_network_calls": result.pipeline_network_calls,
                    "request_path": None if result.request_path is None else str(result.request_path),
                    "role": result.role,
                    "run_id": result.run_id,
                    "status": result.status,
                    "successful_model_invocations": result.successful_model_invocations,
                    "type": "k0a03_run_progress",
                },
            )
        else:
            _emit(stdout, harness.inspect(runtime))
    except Exception as exc:
        _emit(stderr, {"error": str(exc), "status": "failed_closed", "type": "k0a03_error"})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
