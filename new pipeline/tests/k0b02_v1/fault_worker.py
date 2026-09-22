from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time


def durable_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--repository", type=Path)
    parser.add_argument(
        "--operation",
        choices=("migration", "decision", "projector", "publisher", "seal"),
        required=True,
    )
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--ready", type=Path, required=True)
    args = parser.parse_args()

    root = args.repository_root.resolve()
    runtime = args.runtime_root.resolve()
    for path in (args.database, args.payload, args.marker, args.ready):
        if not path.resolve().is_relative_to(runtime):
            parser.error("worker path escaped the admitted runtime root")
    harness = root / "new pipeline/harness"
    sys.path.insert(0, str(harness))
    from k0b02_v1.contract import InputContext
    from k0b02_v1.phase import seal
    from k0b02_v1.projector import project
    from k0b02_v1.publisher import publish
    from k0b02_v1.store import K0b02Store
    from k0b02_v1.transaction_writer import admit

    context = InputContext(
        root,
        root / "new pipeline/evidence/k0b-02-implementation-input-manifest-v2.yaml",
    )
    store = K0b02Store(context, runtime, runtime)
    payload = json.loads(args.payload.read_bytes())

    def observer(actual: str) -> None:
        if actual != args.boundary:
            return
        record = {
            "boundary": actual,
            "database": str(args.database),
            "launcher_pid": os.getppid(),
            "pid": os.getpid(),
        }
        durable_write(args.marker, (json.dumps(record, sort_keys=True) + "\n").encode())
        durable_write(args.ready, b"durable marker closed\n")
        print(actual, flush=True)
        while True:
            time.sleep(0.1)

    if args.operation == "migration":
        store.initialize_to_version(args.database, payload["target_version"], observer)
    elif args.operation == "decision":
        admit(args.database, payload, observer)
    elif args.operation == "projector":
        assert args.repository is not None
        project(args.database, payload["outbox_id"], args.repository, observer)
    elif args.operation == "publisher":
        assert args.repository is not None
        publish(store, args.database, args.repository, payload, observer)
    else:
        seal(args.database, payload, observer)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
