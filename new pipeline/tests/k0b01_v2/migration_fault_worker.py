from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import threading
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-pins", required=True, type=Path)
    parser.add_argument(
        "--environment", required=True, choices=("environment_A", "environment_B")
    )
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--marker", required=True, type=Path)
    parser.add_argument("--fault", required=True)
    args = parser.parse_args()
    product = args.repository_root / "new pipeline/harness/k0b01_v2"
    spec = importlib.util.spec_from_file_location(
        "k0b01_v2", product / "__init__.py", submodule_search_locations=[str(product)]
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("closed loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    from k0b01_v2.canonical import json_bytes, load_json, require
    from k0b01_v2.contract import InputContext
    from k0b01_v2.store import AlphaStore

    require(
        args.source_pins.is_relative_to(args.runtime_root.parent), "worker:pins_scope"
    )
    context = InputContext(
        args.repository_root, args.manifest, load_json(args.source_pins.read_bytes())
    )
    store = AlphaStore(context, args.runtime_root, args.environment)
    marker = store.root.file(args.marker, must_exist=False)
    require(
        args.fault in store.metadata["process_loss_faults"], "worker:mandatory_boundary"
    )

    def observer(boundary: str) -> None:
        if boundary == args.fault:
            with marker.open("xb") as stream:
                stream.write(
                    json_bytes(
                        {
                            "pid": os.getpid(),
                            "parent_pid": os.getppid(),
                            "boundary": boundary,
                            "database": str(args.database),
                            "synthetic_only": True,
                        }
                    )
                )
                stream.flush()
                os.fsync(stream.fileno())
            print(
                json.dumps({"durable_boundary": boundary, "pid": os.getpid()}),
                flush=True,
            )
            ready = store.root.file(marker.with_suffix(".ready"), must_exist=False)
            with ready.open("xb") as stream:
                stream.write(b"durable marker closed\n")
                stream.flush()
                os.fsync(stream.fileno())
            threading.Event().wait()

    store.initialize(args.database, args.backup, observer=observer)
    raise RuntimeError("mandatory boundary was not paused")


if __name__ == "__main__":
    main()
