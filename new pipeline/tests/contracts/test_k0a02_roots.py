from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a02 import (  # noqa: E402
    GuardError,
    K0a02Harness,
    RepositoryIdentity,
    RootGuard,
    ScriptedAdapter,
    load_contract_package,
)


class FakeGitProbe:
    def __init__(self, identities: dict[Path, RepositoryIdentity]):
        self.identities = identities

    def identity(self, root: Path) -> RepositoryIdentity:
        try:
            return self.identities[root]
        except KeyError as exc:
            raise GuardError("foreign repository") from exc


class K0a02RootGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="k0a02-roots-")
        base = Path(self.temporary.name).resolve()
        self.base = base
        self.pipeline = base / "pipeline"
        self.fixture = self.pipeline / "projects" / "pipeline-v2-fixture"
        self.swarm = self.pipeline / "projects" / "swarm"
        self.research = self.pipeline / "research" / "old-swarm"
        self.runtime = base / "runtime-fixture"
        self.foreign = base / "foreign"
        for path in (
            self.fixture,
            self.swarm,
            self.research,
            self.runtime,
            self.foreign,
            self.pipeline / ".git",
            self.fixture / ".git",
            self.runtime / ".git",
            self.foreign / ".git",
        ):
            path.mkdir(parents=True, exist_ok=True)
        self.spec = self.pipeline / "fixture-spec.json"
        self.spec.write_bytes(
            (ROOT / "new pipeline" / "tests" / "fixtures" / "canonical-v1" / "fixture-spec.json").read_bytes()
        )
        package = load_contract_package()
        self.package = package
        binding = package.fixture_binding
        self.pipeline_identity = RepositoryIdentity(
            self.pipeline,
            "a" * 40,
            "b" * 40,
            (self.pipeline / ".git").resolve(),
            True,
        )
        self.fixture_identity = RepositoryIdentity(
            self.fixture,
            binding["canonical_fixture_commit"],
            binding["canonical_fixture_tree"],
            (self.fixture / ".git").resolve(),
            True,
        )
        self.runtime_identity = RepositoryIdentity(
            self.runtime,
            binding["canonical_fixture_commit"],
            binding["canonical_fixture_tree"],
            (self.runtime / ".git").resolve(),
            True,
        )
        self.identities = {
            self.pipeline: self.pipeline_identity,
            self.fixture: self.fixture_identity,
            self.runtime: self.runtime_identity,
        }
        self.guard = RootGuard(
            package,
            expected_pipeline_root=self.pipeline,
            canonical_fixture_root=self.fixture,
            swarm_root=self.swarm,
            legacy_research_root=self.research,
            fixture_spec_path=self.spec,
            git=FakeGitProbe(self.identities),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self):
        return self.guard.validate(
            pipeline_root=self.pipeline,
            canonical_fixture_root=self.fixture,
            runtime_root=self.runtime,
            expected_pipeline_commit=self.pipeline_identity.commit,
        )

    def test_exact_pipeline_fixture_runtime_and_forbidden_root_proof(self) -> None:
        proof = self.validate()
        self.assertEqual(proof.pipeline.commit, "a" * 40)
        self.assertEqual(proof.canonical_fixture.commit, proof.runtime_fixture.commit)
        self.assertNotEqual(proof.canonical_fixture.git_dir, proof.runtime_fixture.git_dir)
        self.assertEqual(proof.forbidden_roots, (self.swarm, self.research))
        self.assertEqual(proof.capabilities["filesystem_roots"], [])
        self.assertEqual(proof.capabilities["tools"], [])

    def test_foreign_pipeline_fixture_and_runtime_roots_are_rejected(self) -> None:
        cases = (
            {"pipeline_root": self.foreign, "canonical_fixture_root": self.fixture, "runtime_root": self.runtime},
            {"pipeline_root": self.pipeline, "canonical_fixture_root": self.foreign, "runtime_root": self.runtime},
            {"pipeline_root": self.pipeline, "canonical_fixture_root": self.fixture, "runtime_root": self.fixture},
            {"pipeline_root": self.pipeline, "canonical_fixture_root": self.fixture, "runtime_root": self.swarm},
            {"pipeline_root": self.pipeline, "canonical_fixture_root": self.fixture, "runtime_root": self.research},
        )
        for values in cases:
            with self.subTest(values=values):
                with self.assertRaises(GuardError):
                    self.guard.validate(**values)

    def test_dirty_or_wrong_pinned_canonical_fixture_fails_closed(self) -> None:
        variants = (
            replace(self.fixture_identity, clean=False),
            replace(self.fixture_identity, commit="0" * 40),
            replace(self.fixture_identity, tree="0" * 40),
        )
        for identity in variants:
            with self.subTest(identity=identity):
                self.identities[self.fixture] = identity
                with self.assertRaises(GuardError):
                    self.validate()
        self.identities[self.fixture] = self.fixture_identity

    def test_dirty_wrong_or_nonindependent_runtime_fixture_fails_closed(self) -> None:
        variants = (
            replace(self.runtime_identity, clean=False),
            replace(self.runtime_identity, commit="0" * 40),
            replace(self.runtime_identity, tree="0" * 40),
            replace(self.runtime_identity, git_dir=self.fixture_identity.git_dir),
        )
        for identity in variants:
            with self.subTest(identity=identity):
                self.identities[self.runtime] = identity
                with self.assertRaises(GuardError):
                    self.validate()
        self.identities[self.runtime] = self.runtime_identity

    def test_pipeline_commit_and_clean_state_are_exact(self) -> None:
        with self.assertRaises(GuardError):
            self.guard.validate(
                pipeline_root=self.pipeline,
                canonical_fixture_root=self.fixture,
                runtime_root=self.runtime,
                expected_pipeline_commit="0" * 40,
            )
        self.identities[self.pipeline] = replace(self.pipeline_identity, clean=False)
        with self.assertRaises(GuardError):
            self.validate()

    def test_fixture_spec_hash_mismatch_is_rejected(self) -> None:
        self.spec.write_bytes(self.spec.read_bytes() + b"\n")
        with self.assertRaises(GuardError):
            self.validate()

    def test_absent_forbidden_roots_are_bound_without_creation_in_clean_clone(self) -> None:
        absent_swarm = self.pipeline / "absent-projects" / "swarm"
        absent_research = self.pipeline / "absent-research" / "old-swarm"
        guard = RootGuard(
            self.package,
            expected_pipeline_root=self.pipeline,
            canonical_fixture_root=self.fixture,
            swarm_root=absent_swarm,
            legacy_research_root=absent_research,
            fixture_spec_path=self.spec,
            git=FakeGitProbe(self.identities),
        )
        proof = guard.validate(
            pipeline_root=self.pipeline,
            canonical_fixture_root=self.fixture,
            runtime_root=self.runtime,
            expected_pipeline_commit=self.pipeline_identity.commit,
        )
        self.assertEqual(proof.forbidden_roots, (absent_swarm, absent_research))
        self.assertFalse(absent_swarm.exists())
        self.assertFalse(absent_research.exists())

    def test_existing_forbidden_root_junction_binds_target_and_rejects_runtime_alias(self) -> None:
        forbidden_junction = self.pipeline / "forbidden-runtime-junction"
        try:
            if os.name == "nt":
                subprocess.run(
                    [
                        "cmd.exe",
                        "/d",
                        "/c",
                        "mklink",
                        "/J",
                        str(forbidden_junction),
                        str(self.runtime),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            else:
                forbidden_junction.symlink_to(self.runtime, target_is_directory=True)
            guard = RootGuard(
                self.package,
                expected_pipeline_root=self.pipeline,
                canonical_fixture_root=self.fixture,
                swarm_root=forbidden_junction,
                legacy_research_root=self.research,
                fixture_spec_path=self.spec,
                git=FakeGitProbe(self.identities),
            )
            with self.assertRaises(GuardError):
                guard.validate(
                    pipeline_root=self.pipeline,
                    canonical_fixture_root=self.fixture,
                    runtime_root=self.runtime,
                    expected_pipeline_commit=self.pipeline_identity.commit,
                )
        finally:
            if forbidden_junction.exists() or forbidden_junction.is_symlink():
                os.rmdir(forbidden_junction)

    def test_whole_runtime_root_symlink_or_junction_is_rejected_before_resolution(self) -> None:
        junction = self.base / "runtime-junction"
        adapter = ScriptedAdapter.nominal(self.package)
        harness = K0a02Harness(
            adapter,
            package=self.package,
            guard=self.guard,
            pipeline_root=self.pipeline,
            canonical_fixture_root=self.fixture,
        )
        try:
            if os.name == "nt":
                subprocess.run(
                    ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(self.runtime)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            else:
                junction.symlink_to(self.runtime, target_is_directory=True)
            with self.assertRaises(GuardError):
                self.guard.validate(
                    pipeline_root=self.pipeline,
                    canonical_fixture_root=self.fixture,
                    runtime_root=junction,
                    expected_pipeline_commit=self.pipeline_identity.commit,
                )
            with self.assertRaises(GuardError):
                harness.initialize(
                    junction, expected_pipeline_commit=self.pipeline_identity.commit
                )
            self.assertFalse(
                (self.runtime / ".pipeline" / "runtime" / "pipeline.sqlite3").exists()
            )
            harness.initialize(
                self.runtime, expected_pipeline_commit=self.pipeline_identity.commit
            )
            with self.assertRaises(GuardError):
                harness.inspect(
                    junction, expected_pipeline_commit=self.pipeline_identity.commit
                )
            with self.assertRaises(GuardError):
                harness.run(
                    junction,
                    {
                        "command": "bootstrap",
                        "fixture_spec_sha256": self.package.fixture_binding[
                            "fixture_spec_sha256"
                        ],
                        "profile": "F00",
                        "type": "normalized_f00_command",
                    },
                    expected_pipeline_commit=self.pipeline_identity.commit,
                )
            self.assertEqual(adapter.requests, [])
        finally:
            if junction.exists() or junction.is_symlink():
                os.rmdir(junction)


if __name__ == "__main__":
    unittest.main()
