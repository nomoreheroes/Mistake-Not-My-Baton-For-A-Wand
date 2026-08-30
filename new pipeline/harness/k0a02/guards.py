"""Exact Pipeline, fixture, runtime-root, and capability guards for K0a-02."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import subprocess
from typing import Mapping

from .contract import PinnedContractPackage


PIPELINE_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_FIXTURE_ROOT = PIPELINE_ROOT / "projects" / "pipeline-v2-fixture"
SWARM_ROOT = PIPELINE_ROOT / "projects" / "swarm"
LEGACY_RESEARCH_ROOT = PIPELINE_ROOT / "research" / "old-swarm"
FIXTURE_SPEC_PATH = PIPELINE_ROOT / "new pipeline" / "tests" / "fixtures" / "canonical-v1" / "fixture-spec.json"


class GuardError(RuntimeError):
    """An exact root, Git identity, clean-state, or capability guard failed."""


@dataclass(frozen=True)
class RepositoryIdentity:
    root: Path
    commit: str
    tree: str
    git_dir: Path
    clean: bool


@dataclass(frozen=True)
class GuardProof:
    pipeline: RepositoryIdentity
    canonical_fixture: RepositoryIdentity
    runtime_fixture: RepositoryIdentity
    fixture_spec_sha256: str
    forbidden_roots: tuple[Path, Path]
    capabilities: Mapping[str, object]


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _inside(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


class GitProbe:
    """Small fixed-command Git reader; it never mutates a repository."""

    def __init__(self) -> None:
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "LC_ALL": "C",
            }
        )

    def _git(self, root: Path, *arguments: str) -> str:
        command = [
            "git",
            "-c",
            f"safe.directory={root}",
            "-C",
            str(root),
            *arguments,
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                env=self.environment,
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise GuardError(f"Git identity check failed for {root}") from exc
        try:
            return completed.stdout.decode("utf-8", errors="strict").strip()
        except UnicodeError as exc:
            raise GuardError("Git returned non-UTF-8 identity output") from exc

    def identity(self, root: Path) -> RepositoryIdentity:
        top = Path(self._git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if not _same_path(top, root):
            raise GuardError("Git top-level differs from the exact requested root")
        commit = self._git(root, "rev-parse", "HEAD")
        tree = self._git(root, "rev-parse", "HEAD^{tree}")
        status = self._git(root, "status", "--porcelain=v1", "--untracked-files=all")
        git_dir_raw = Path(self._git(root, "rev-parse", "--absolute-git-dir"))
        git_dir = git_dir_raw.resolve(strict=True)
        return RepositoryIdentity(root, commit, tree, git_dir, not status)


class RootGuard:
    """Validates only the three exact repositories and one disposable run root."""

    def __init__(
        self,
        package: PinnedContractPackage,
        *,
        expected_pipeline_root: Path = PIPELINE_ROOT,
        canonical_fixture_root: Path = CANONICAL_FIXTURE_ROOT,
        swarm_root: Path = SWARM_ROOT,
        legacy_research_root: Path = LEGACY_RESEARCH_ROOT,
        fixture_spec_path: Path = FIXTURE_SPEC_PATH,
        git: GitProbe | None = None,
    ) -> None:
        self.package = package
        self.expected_pipeline_root = expected_pipeline_root.resolve(strict=True)
        self.canonical_fixture_root = canonical_fixture_root.resolve(strict=True)
        # Forbidden roots may be intentionally absent in a clean Pipeline
        # checkout.  Resolve existing aliases without requiring or creating a
        # missing final path, so overlap checks also cover junction targets.
        self.swarm_root = swarm_root.resolve(strict=False)
        self.legacy_research_root = legacy_research_root.resolve(strict=False)
        self.fixture_spec_path = fixture_spec_path.resolve(strict=True)
        self.git = git or GitProbe()

    @staticmethod
    def _exact_directory(path: Path, label: str) -> Path:
        if not path.is_absolute():
            raise GuardError(f"{label} must be an absolute path")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise GuardError(f"{label} does not exist") from exc
        if not resolved.is_dir() or not _same_path(path, resolved):
            raise GuardError(f"{label} is not an exact real directory (symlink/junction rejected)")
        return resolved

    def validate(
        self,
        *,
        pipeline_root: Path,
        canonical_fixture_root: Path,
        runtime_root: Path,
        expected_pipeline_commit: str | None = None,
    ) -> GuardProof:
        pipeline = self._exact_directory(pipeline_root, "Pipeline root")
        canonical = self._exact_directory(canonical_fixture_root, "canonical fixture root")
        runtime = self._exact_directory(runtime_root, "disposable runtime root")
        if not _same_path(pipeline, self.expected_pipeline_root):
            raise GuardError("foreign Pipeline root")
        if not _same_path(canonical, self.canonical_fixture_root):
            raise GuardError("foreign canonical fixture root")
        if _same_path(runtime, canonical) or _inside(runtime, pipeline):
            raise GuardError("runtime root must be a separate disposable fixture outside Pipeline root")
        if any(
            _same_path(runtime, forbidden) or _inside(runtime, forbidden)
            for forbidden in (self.swarm_root, self.legacy_research_root)
        ):
            raise GuardError("runtime root overlaps a forbidden product/research root")

        pipeline_identity = self.git.identity(pipeline)
        canonical_identity = self.git.identity(canonical)
        runtime_identity = self.git.identity(runtime)
        if expected_pipeline_commit is not None and pipeline_identity.commit != expected_pipeline_commit:
            raise GuardError("Pipeline HEAD differs from the expected current commit")
        if not pipeline_identity.clean:
            raise GuardError("Pipeline worktree/index is not clean")
        binding = self.package.fixture_binding
        if (
            canonical_identity.commit != binding["canonical_fixture_commit"]
            or canonical_identity.tree != binding["canonical_fixture_tree"]
            or not canonical_identity.clean
        ):
            raise GuardError("canonical fixture commit/tree/clean baseline is not pinned")
        if (
            runtime_identity.commit != binding["canonical_fixture_commit"]
            or runtime_identity.tree != binding["canonical_fixture_tree"]
            or not runtime_identity.clean
            or _same_path(runtime_identity.git_dir, canonical_identity.git_dir)
        ):
            raise GuardError("runtime root is not a clean independent clone/materialization of the fixture")
        spec_hash = sha256(self.fixture_spec_path.read_bytes()).hexdigest()
        if spec_hash != binding["fixture_spec_sha256"]:
            raise GuardError("fixture spec hash mismatch")
        capabilities = self.package.capability_profile
        if (
            capabilities["filesystem_roots"] != []
            or capabilities["tools"] != []
            or capabilities["runtime_enabled"] is not False
            or capabilities["product_external_side_effects"] is not False
        ):
            raise GuardError("reasoning capability profile was widened")
        return GuardProof(
            pipeline_identity,
            canonical_identity,
            runtime_identity,
            spec_hash,
            (self.swarm_root, self.legacy_research_root),
            capabilities,
        )
