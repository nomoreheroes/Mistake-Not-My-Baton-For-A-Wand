from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from canonical import canonical_bytes, load_strict
from compiler import compile_package, output_manifest
from scanner import scan_request


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="k0b03-v1")
    sub = result.add_subparsers(dest="command", required=True)
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("--repository-root", required=True)
    compile_parser.add_argument("--output-root", required=True)
    scan_parser = sub.add_parser("scan")
    scan_parser.add_argument("--profile", required=True)
    scan_parser.add_argument("--request", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "compile":
        output_root = Path(args.output_root)
        compile_package(Path(args.repository_root), output_root)
        sys.stdout.buffer.write(canonical_bytes({"result":"compiled_not_authorized","outputs":output_manifest(output_root),"runtime_authority":"none"}))
        return 0
    profile = load_strict(Path(args.profile))
    request = load_strict(Path(args.request))
    sys.stdout.buffer.write(canonical_bytes(scan_request(request, profile)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
