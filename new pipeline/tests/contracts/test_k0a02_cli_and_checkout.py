from __future__ import annotations

from pathlib import Path
import shutil
from types import SimpleNamespace
import io
import os
import subprocess
import sys
import tempfile
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a02.cli import _parser, main  # noqa: E402


class FakeHarness:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def initialize(self, runtime_root: Path):
        self.calls.append(("initialize", runtime_root))
        repository = SimpleNamespace(commit="a" * 40)
        return SimpleNamespace(
            database_path=runtime_root / ".pipeline" / "runtime" / "pipeline.sqlite3",
            guard_proof=SimpleNamespace(pipeline=repository, runtime_fixture=repository),
        )

    def run(self, runtime_root: Path, command):
        self.calls.append(("run", (runtime_root, command)))
        return SimpleNamespace(
            artifact_version_id="artifact-version",
            network_calls=0,
            readback_gate_id="readback-gate",
            run_id="run",
            runtime_model_invocations=0,
            sink_acceptance_id="sink-acceptance",
            inspect={"run": {"state": "completed"}},
        )

    def inspect(self, runtime_root: Path):
        self.calls.append(("inspect", runtime_root))
        return {"run": {"state": "completed"}, "type": "inspect_readback"}


class K0a02CliAndCheckoutTests(unittest.TestCase):
    def test_cli_grammar_is_exactly_initialize_run_inspect_without_free_parameters(self) -> None:
        parser = _parser()
        for command in ("initialize", "run", "inspect"):
            self.assertEqual(parser.parse_args([command]).command, command)
        forbidden = (
            [],
            ["unknown"],
            ["run", "C:/arbitrary"],
            ["run", "--provider", "foreign"],
            ["run", "--model", "foreign"],
            ["run", "--schema", "foreign"],
            ["run", "--route", "foreign"],
            ["run", "--capability", "shell"],
            ["inspect", "--sql", "select * from runs"],
            ["initialize", "--runtime-root", "C:/foreign"],
        )
        for argv in forbidden:
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                parser.parse_args(argv)

    def test_cli_delegates_all_three_commands_to_harness_api(self) -> None:
        with tempfile.TemporaryDirectory(prefix="k0a02-cli-") as temporary:
            runtime = Path(temporary).resolve()
            for command in ("initialize", "run", "inspect"):
                fake = FakeHarness()
                output = io.StringIO()
                errors = io.StringIO()
                code = main(
                    [command],
                    cwd=runtime,
                    harness_factory=lambda _package, current=fake: current,
                    stdout=output,
                    stderr=errors,
                )
                self.assertEqual(code, 0, errors.getvalue())
                self.assertEqual(fake.calls[0][0], command)
                self.assertTrue(output.getvalue().endswith("\n"))
                self.assertEqual(errors.getvalue(), "")
                if command == "run":
                    submitted = fake.calls[0][1][1]
                    self.assertEqual(
                        set(submitted),
                        {"command", "fixture_spec_sha256", "profile", "type"},
                    )
                    self.assertNotIn("provider", submitted)
                    self.assertNotIn("model", submitted)
                    self.assertNotIn("path", submitted)

    def test_cli_source_has_no_direct_sqlite_or_free_sql_surface(self) -> None:
        source = (PIPELINE_DIR / "harness" / "k0a02" / "cli.py").read_text(encoding="utf-8")
        self.assertNotIn("import sqlite3", source)
        self.assertNotIn("execute(", source)
        self.assertNotIn("--sql", source)
        self.assertNotIn("K0a02Store", source)

    def test_k0a02_text_survives_clean_checkout_with_core_autocrlf_true(self) -> None:
        relative_files = [
            Path(".gitattributes"),
            Path("new pipeline/contracts/k0a02/f00-contract-package-v1.json"),
            Path("new pipeline/harness/migrations/0001_k0a01.sql"),
            Path("new pipeline/harness/migrations/0002_k0a02.sql"),
            Path("new pipeline/harness/k0a02/__init__.py"),
            Path("new pipeline/harness/k0a02/adapters.py"),
            Path("new pipeline/harness/k0a02/cli.py"),
            Path("new pipeline/harness/k0a02/contract.py"),
            Path("new pipeline/harness/k0a02/guards.py"),
            Path("new pipeline/harness/k0a02/orchestrator.py"),
            Path("new pipeline/harness/k0a02/security.py"),
            Path("new pipeline/harness/k0a02/store.py"),
        ]
        with tempfile.TemporaryDirectory(prefix="k0a02-autocrlf-") as temporary:
            base = Path(temporary)
            source = base / "source"
            checkout = base / "checkout"
            source.mkdir()
            for relative in relative_files:
                destination = source / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            environment = os.environ.copy()
            environment.update(
                {
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "LC_ALL": "C",
                }
            )

            def git(repository: Path, *arguments: str) -> None:
                subprocess.run(
                    ["git", "-C", str(repository), *arguments],
                    check=True,
                    capture_output=True,
                    env=environment,
                )

            subprocess.run(
                ["git", "init", "--quiet", str(source)],
                check=True,
                capture_output=True,
                env=environment,
            )
            git(source, "config", "user.name", "K0a02 Test")
            git(source, "config", "user.email", "k0a02@example.invalid")
            git(source, "config", "core.autocrlf", "false")
            git(source, "add", "--all")
            git(source, "commit", "--quiet", "-m", "fixture")
            subprocess.run(
                ["git", "clone", "--quiet", "--no-checkout", str(source), str(checkout)],
                check=True,
                capture_output=True,
                env=environment,
            )
            git(checkout, "config", "core.autocrlf", "true")
            git(checkout, "checkout", "--quiet", "--force")
            for relative in relative_files:
                with self.subTest(relative=relative):
                    expected = (source / relative).read_bytes()
                    actual = (checkout / relative).read_bytes()
                    self.assertEqual(actual, expected)
                    self.assertFalse(actual.startswith(b"\xef\xbb\xbf"))
                    self.assertNotIn(b"\r", actual)


if __name__ == "__main__":
    unittest.main()
