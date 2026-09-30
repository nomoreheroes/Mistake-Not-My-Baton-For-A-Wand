from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RENDERER_PATH = ROOT / "new pipeline/state/renderer/k0b03_v8/renderer.py"
PROFILE_PATH = ROOT / "new pipeline/state/renderer/k0b03_v8/projection-profile-v8.yaml"
SOURCE_PATH = ROOT / "new pipeline/state/state.yaml"
PROJECTION_PATH = ROOT / "new pipeline/state/STATE.md"
REQUEST_PATH = ROOT / (
    "new pipeline/requests/"
    "development-plan-v0-14-adoption-approval-request-v1.yaml"
)
EXPECTED_ENV_ROOTS = {
    Path(
        "C:/Users/Administrator/AppData/Local/Temp/2/"
        "pipeline-v2-development-plan-v014-adoption-v8-A"
    ).absolute(),
    Path(
        "C:/Users/Administrator/AppData/Local/Temp/2/"
        "pipeline-v2-development-plan-v014-adoption-v8-B"
    ).absolute(),
}
FIXTURE_LEAVES = {
    "real/source/state.yaml",
    "links/source-file.yaml",
    "real/source-parent/state.yaml",
    "links/source-parent",
    "real/profile/profile.yaml",
    "links/profile-file.yaml",
    "real/profile-parent/profile.yaml",
    "links/profile-parent",
    "real/repository/payload.bin",
    "links/repository-root",
    "repository-surface/real-segment/payload.bin",
    "repository-surface/link-segment",
    "real/projection/STATE.md",
    "links/projection-file.md",
    "real/projection-parent/STATE.md",
    "links/projection-parent",
    "real/output-existing/canary.md",
    "links/output-file.md",
    "real/output-parent",
    "links/output-parent",
    "real/regular-output/STATE.md",
    "cases/overlap-profile.yaml",
    "cases/duplicate-key.yaml",
    "cases/crlf.yaml",
}


SPEC = importlib.util.spec_from_file_location("pipeline_v2_renderer_v8", RENDERER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("renderer_import_spec")
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def allowed_fixture_paths() -> set[str]:
    allowed = set(FIXTURE_LEAVES)
    for value in tuple(FIXTURE_LEAVES):
        parent = Path(value).parent
        while str(parent) != ".":
            allowed.add(parent.as_posix())
            parent = parent.parent
    return allowed


class SyntheticReparsePath:
    def absolute(self):
        return self

    @property
    def parents(self):
        return ()

    def lstat(self):
        return types.SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=renderer.REPARSE_ATTRIBUTE,
        )


class RendererV8AdoptionTests(unittest.TestCase):
    rejection_codes: dict[str, str] = {}

    @classmethod
    def setUpClass(cls) -> None:
        value = os.environ.get("K0B03_REPARSE_ENV_ROOT")
        if value is None:
            raise RuntimeError("fixture_environment_root_missing")
        cls.environment_root = Path(value).absolute()
        if cls.environment_root not in EXPECTED_ENV_ROOTS:
            raise RuntimeError("fixture_environment_root_out_of_scope")
        info = cls.environment_root.lstat()
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & renderer.REPARSE_ATTRIBUTE
        ):
            raise RuntimeError("fixture_environment_root_reparse")
        cls.fixture_root = cls.environment_root / "reparse-fixtures"
        if os.path.lexists(cls.fixture_root):
            raise RuntimeError("fixture_root_exists")
        cls.links: list[Path] = []
        cls.real_snapshots: dict[Path, bytes] = {}
        try:
            cls._create_fixture()
        except BaseException:
            cls._cleanup_fixture(best_effort=True)
            raise

    @classmethod
    def _write(cls, relative: str, data: bytes) -> Path:
        path = cls.fixture_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        cls.real_snapshots[path] = data
        return path

    @classmethod
    def _make_link(cls, relative: str, target: Path, *, directory: bool) -> Path:
        link = cls.fixture_root / relative
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=directory)
        info = link.lstat()
        if not stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"fixture_not_symlink:{relative}")
        if not (
            getattr(info, "st_file_attributes", 0) & renderer.REPARSE_ATTRIBUTE
        ):
            raise RuntimeError(f"fixture_not_Windows_reparse:{relative}")
        cls.links.append(link)
        return link

    @classmethod
    def _create_fixture(cls) -> None:
        source = cls._write("real/source/state.yaml", SOURCE_PATH.read_bytes())
        source_parent_file = cls._write(
            "real/source-parent/state.yaml", SOURCE_PATH.read_bytes()
        )
        profile = cls._write("real/profile/profile.yaml", PROFILE_PATH.read_bytes())
        profile_parent_file = cls._write(
            "real/profile-parent/profile.yaml", PROFILE_PATH.read_bytes()
        )
        payload = cls._write("real/repository/payload.bin", b"fixture-payload\n")
        segment_payload = cls._write(
            "repository-surface/real-segment/payload.bin", b"segment-payload\n"
        )
        projection = cls._write(
            "real/projection/STATE.md", PROJECTION_PATH.read_bytes()
        )
        projection_parent_file = cls._write(
            "real/projection-parent/STATE.md", PROJECTION_PATH.read_bytes()
        )
        canary = cls._write(
            "real/output-existing/canary.md", b"canary-must-remain\n"
        )
        output_parent = cls.fixture_root / "real/output-parent"
        output_parent.mkdir(parents=True, exist_ok=True)
        regular_output_parent = cls.fixture_root / "real/regular-output"
        regular_output_parent.mkdir(parents=True, exist_ok=True)

        cls.source_file_link = cls._make_link(
            "links/source-file.yaml", source, directory=False
        )
        cls.source_parent_link = cls._make_link(
            "links/source-parent", source_parent_file.parent, directory=True
        )
        cls.profile_file_link = cls._make_link(
            "links/profile-file.yaml", profile, directory=False
        )
        cls.profile_parent_link = cls._make_link(
            "links/profile-parent", profile_parent_file.parent, directory=True
        )
        cls.repository_root_link = cls._make_link(
            "links/repository-root", payload.parent, directory=True
        )
        cls.repository_segment_link = cls._make_link(
            "repository-surface/link-segment", segment_payload.parent, directory=True
        )
        cls.projection_file_link = cls._make_link(
            "links/projection-file.md", projection, directory=False
        )
        cls.projection_parent_link = cls._make_link(
            "links/projection-parent", projection_parent_file.parent, directory=True
        )
        cls.output_file_link = cls._make_link(
            "links/output-file.md", canary, directory=False
        )
        cls.output_parent_link = cls._make_link(
            "links/output-parent", output_parent, directory=True
        )
        cls.regular_output = regular_output_parent / "STATE.md"
        cls.segment_payload = segment_payload
        cls.payload = payload
        cls.canary = canary
        cls.output_parent = output_parent
        cls._assert_inventory()

    @classmethod
    def _current_inventory(cls) -> set[str]:
        result: set[str] = set()
        for parent, directories, files in os.walk(cls.fixture_root, followlinks=False):
            base = Path(parent)
            for name in [*directories, *files]:
                result.add((base / name).relative_to(cls.fixture_root).as_posix())
        return result

    @classmethod
    def _assert_inventory(cls) -> None:
        unexpected = cls._current_inventory() - allowed_fixture_paths()
        if unexpected:
            raise AssertionError(f"unexpected_fixture_paths:{sorted(unexpected)}")

    @classmethod
    def _cleanup_fixture(cls, *, best_effort: bool = False) -> None:
        errors: list[str] = []
        for link in reversed(getattr(cls, "links", [])):
            try:
                info = link.lstat()
                if not stat.S_ISLNK(info.st_mode) or not (
                    getattr(info, "st_file_attributes", 0)
                    & renderer.REPARSE_ATTRIBUTE
                ):
                    raise RuntimeError(f"cleanup_link_identity:{link}")
                link.unlink()
                if os.path.lexists(link):
                    raise RuntimeError(f"cleanup_link_remains:{link}")
            except FileNotFoundError:
                continue
            except BaseException as exc:
                errors.append(str(exc))
        root = getattr(cls, "fixture_root", None)
        if root is not None and root.exists():
            try:
                shutil.rmtree(root)
            except BaseException as exc:
                errors.append(str(exc))
        if root is not None and os.path.lexists(root):
            errors.append(f"cleanup_fixture_root_remains:{root}")
        if errors and not best_effort:
            raise AssertionError(";".join(errors))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cleanup_fixture()

    def assert_canaries_and_inventory(self) -> None:
        for path, expected in self.real_snapshots.items():
            self.assertEqual(path.read_bytes(), expected, str(path))
        self._assert_inventory()

    def assert_rejection(self, case_id: str, code: str, operation) -> None:
        with self.assertRaises(renderer.RendererError) as raised:
            operation()
        self.assertEqual(str(raised.exception), code)
        type(self).rejection_codes[case_id] = code
        self.assert_canaries_and_inventory()

    def test_01_canonical_render_reproduces_committed_STATE_bytes(self) -> None:
        output, summary = renderer.render_bytes(
            source_path=SOURCE_PATH,
            profile_path=PROFILE_PATH,
            repository_root=ROOT,
        )
        self.assertEqual(renderer.RENDERER_VERSION, "8.0.0")
        self.assertEqual(output, PROJECTION_PATH.read_bytes())
        self.assertEqual(summary["projection_sha256"], sha256(output))
        self.assertEqual(len(output), len(PROJECTION_PATH.read_bytes()))

    def test_02_canonical_check_is_read_only(self) -> None:
        before = PROJECTION_PATH.read_bytes()
        renderer.check_projection(
            source_path=SOURCE_PATH,
            profile_path=PROFILE_PATH,
            projection_path=PROJECTION_PATH,
            repository_root=ROOT,
        )
        self.assertEqual(PROJECTION_PATH.read_bytes(), before)

    def test_03_regular_output_has_exact_projection_bytes(self) -> None:
        output, _ = renderer.render_bytes(
            source_path=SOURCE_PATH,
            profile_path=PROFILE_PATH,
            repository_root=ROOT,
        )
        renderer.write_projection(self.regular_output, output)
        self.assertEqual(self.regular_output.read_bytes(), PROJECTION_PATH.read_bytes())
        self.real_snapshots[self.regular_output] = output
        self._assert_inventory()

    def test_04_regular_repository_file_passes(self) -> None:
        expected = self.payload.read_bytes()
        actual = renderer.repository_file(
            self.payload.parent,
            self.payload.name,
            sha256(expected),
            len(expected),
            "regular_repository_file",
        )
        self.assertEqual(actual, expected)

    def test_05_source_file_symlink_rejected(self) -> None:
        self.assert_rejection(
            "R8-N01",
            "source:reparse",
            lambda: renderer.read_json(self.source_file_link, "source"),
        )

    def test_06_source_parent_symlink_rejected(self) -> None:
        self.assert_rejection(
            "R8-N02",
            "source:reparse",
            lambda: renderer.read_json(self.source_parent_link / "state.yaml", "source"),
        )

    def test_07_profile_file_symlink_rejected(self) -> None:
        self.assert_rejection(
            "R8-N03",
            "profile:reparse",
            lambda: renderer.load_profile(self.profile_file_link, ROOT),
        )

    def test_08_profile_parent_symlink_rejected(self) -> None:
        self.assert_rejection(
            "R8-N04",
            "profile:reparse",
            lambda: renderer.load_profile(
                self.profile_parent_link / "profile.yaml", ROOT
            ),
        )

    def test_09_repository_root_symlink_rejected_before_resolve(self) -> None:
        expected = self.payload.read_bytes()
        self.assert_rejection(
            "R8-N05",
            "repository_root:reparse",
            lambda: renderer.repository_file(
                self.repository_root_link,
                "payload.bin",
                sha256(expected),
                len(expected),
                "source_reference",
            ),
        )

    def test_10_transition_pin_intermediate_symlink_rejected(self) -> None:
        expected = self.segment_payload.read_bytes()
        self.assert_rejection(
            "R8-N06",
            "transition_pin:reparse",
            lambda: renderer.repository_file(
                self.fixture_root / "repository-surface",
                "link-segment/payload.bin",
                sha256(expected),
                len(expected),
                "transition_pin",
            ),
        )

    def test_11_state_reference_intermediate_symlink_rejected(self) -> None:
        expected = self.segment_payload.read_bytes()
        self.assert_rejection(
            "R8-N07",
            "source_reference:reparse",
            lambda: renderer.repository_file(
                self.fixture_root / "repository-surface",
                "link-segment/payload.bin",
                sha256(expected),
                len(expected),
                "source_reference",
            ),
        )

    def test_12_check_projection_file_symlink_rejected(self) -> None:
        self.assert_rejection(
            "R8-N08",
            "projection:reparse",
            lambda: renderer.check_projection(
                source_path=SOURCE_PATH,
                profile_path=PROFILE_PATH,
                projection_path=self.projection_file_link,
                repository_root=ROOT,
            ),
        )

    def test_13_check_projection_parent_symlink_rejected(self) -> None:
        self.assert_rejection(
            "R8-N09",
            "projection:reparse",
            lambda: renderer.check_projection(
                source_path=SOURCE_PATH,
                profile_path=PROFILE_PATH,
                projection_path=self.projection_parent_link / "STATE.md",
                repository_root=ROOT,
            ),
        )

    def test_14_render_existing_output_symlink_rejected(self) -> None:
        self.assert_rejection(
            "R8-N10",
            "output:reparse",
            lambda: renderer.write_projection(self.output_file_link, b"replacement\n"),
        )

    def test_15_render_output_parent_symlink_rejected(self) -> None:
        target = self.output_parent / "STATE.md"
        self.assertFalse(target.exists())
        self.assert_rejection(
            "R8-N11",
            "output:reparse",
            lambda: renderer.write_projection(
                self.output_parent_link / "STATE.md", b"replacement\n"
            ),
        )
        self.assertFalse(target.exists())

    def test_16_synthetic_non_symlink_reparse_rejected(self) -> None:
        self.assert_rejection(
            "R8-N12",
            "synthetic:reparse",
            lambda: renderer.reject_reparse(SyntheticReparsePath(), "synthetic"),
        )


    def _transition_values(self):
        source = json.loads(SOURCE_PATH.read_bytes())
        profile, profile_sha, _ = renderer.load_profile(PROFILE_PATH, ROOT)
        return source, profile, profile_sha

    def test_17_foreign_selector_rejected(self) -> None:
        source, profile, profile_sha = self._transition_values()
        source["scope"]["v8_test_foreign_selector"] = True
        with self.assertRaises(renderer.RendererError) as raised:
            renderer.validate_transition(source, profile, profile_sha)
        self.assertEqual(str(raised.exception), "source:outside_delta_whitelist")

    def test_18_development_plan_hash_rejected(self) -> None:
        source, profile, profile_sha = self._transition_values()
        source["root_plan_status"]["development_plan"]["sha256"] = "0" * 64
        with self.assertRaises(renderer.RendererError) as raised:
            renderer.validate_transition(source, profile, profile_sha)
        self.assertEqual(str(raised.exception), "source:development_plan_sha256")

    def test_19_development_plan_path_rejected(self) -> None:
        source, profile, profile_sha = self._transition_values()
        source["root_plan_status"]["development_plan"]["path"] = (
            "new pipeline/PIPELINE_V2_DEVELOPMENT_PLAN.md"
        )
        with self.assertRaises(renderer.RendererError) as raised:
            renderer.validate_transition(source, profile, profile_sha)
        self.assertEqual(str(raised.exception), "source:development_plan_path")

    def test_20_duplicate_gate_rejected(self) -> None:
        source, profile, profile_sha = self._transition_values()
        source["open_gates"].append(copy.deepcopy(source["open_gates"][0]))
        with self.assertRaises(renderer.RendererError) as raised:
            renderer.validate_transition(source, profile, profile_sha)
        self.assertEqual(str(raised.exception), "source:gate_inventory")

    def test_21_base_allowlist_overlap_rejected(self) -> None:
        profile = json.loads(PROFILE_PATH.read_bytes())
        additions = profile["reference_contract"]["allowed_path_additions"]
        additions[0] = ".gitattributes"
        additions.sort()
        invalid = self._write(
            "cases/overlap-profile.yaml",
            (json.dumps(profile, indent=2) + "\n").encode("utf-8"),
        )
        with self.assertRaises(renderer.RendererError) as raised:
            renderer.load_profile(invalid, ROOT)
        self.assertEqual(str(raised.exception), "profile:allowed_additions")

    def test_22_duplicate_JSON_key_rejected(self) -> None:
        invalid = self._write("cases/duplicate-key.yaml", b'{"a":1,"a":2}\n')
        with self.assertRaises(renderer.RendererError) as raised:
            renderer.read_json(invalid, "duplicate")
        self.assertEqual(str(raised.exception), "duplicate:JSON")

    def test_23_CRLF_rejected(self) -> None:
        invalid = self._write("cases/crlf.yaml", b'{"a":1}\r\n')
        with self.assertRaises(renderer.RendererError) as raised:
            renderer.read_json(invalid, "crlf")
        self.assertEqual(str(raised.exception), "crlf:canonical_text")

    def test_24_candidate_entry_reference_projection_is_exactly_100(self) -> None:
        request = json.loads(REQUEST_PATH.read_bytes())
        entries = request["entry_state_reference_manifest"]["entries"]
        paths = {item["path"] for item in entries}
        self.assertEqual(len(paths), 98)
        paths.remove("new pipeline/PIPELINE_V2_DEVELOPMENT_PLAN.md")
        paths.remove(
            "new pipeline/state/renderer/k0b03_v7/projection-profile-v7.yaml"
        )
        paths.update(
            {
                "new pipeline/PIPELINE_V2_DEVELOPMENT_PLAN-v0.14.md",
                "new pipeline/decisions/development-plan-v0-14-adoption-owner-disposition-v1.yaml",
                "new pipeline/evidence/development-plan-v0-14-adoption-v1.yaml",
                "new pipeline/state/renderer/k0b03_v8/projection-profile-v8.yaml",
            }
        )
        self.assertEqual(len(paths), 100)
        source = json.loads(SOURCE_PATH.read_bytes())
        self.assertEqual(
            source["active_authority"]["development_plan_v0_14_adoption"]["path"],
            "new pipeline/decisions/development-plan-v0-14-adoption-owner-disposition-v1.yaml",
        )
        self.assertEqual(
            source["supporting_review_evidence"]["development_plan_v0_14_adoption"]["path"],
            "new pipeline/evidence/development-plan-v0-14-adoption-v1.yaml",
        )


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RendererV8AdoptionTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    canonical_projection = PROJECTION_PATH.read_bytes()
    print(
        json.dumps(
            {
                "result": "pass" if result.wasSuccessful() else "fail",
                "renderer_version": renderer.RENDERER_VERSION,
                "tests": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "canonical_projection_sha256": sha256(canonical_projection),
                "canonical_projection_bytes": len(canonical_projection),
                "rejection_codes": RendererV8AdoptionTests.rejection_codes,
                "fixture_root_absent_after_cleanup": not os.path.lexists(
                    getattr(RendererV8AdoptionTests, "fixture_root", Path("."))
                ),
            },
            sort_keys=True,
        )
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
