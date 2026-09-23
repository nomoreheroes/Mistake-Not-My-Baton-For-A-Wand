from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO: Path
CANDIDATE: Path
SCRATCH: Path
PROFILE_REL = "new pipeline/state/renderer/k0b02_v6/projection-profile-v6.yaml"
RENDERER_REL = "new pipeline/state/renderer/k0b02_v6/renderer.py"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RendererV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location(
            "approved_renderer_v6", REPO / RENDERER_REL
        )
        assert spec is not None and spec.loader is not None
        cls.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.renderer)
        cls.profile_path = REPO / PROFILE_REL
        cls.profile = json.loads(cls.profile_path.read_bytes())
        cls.candidate = json.loads(CANDIDATE.read_bytes())

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="renderer-v6-", dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source(self, value: dict) -> Path:
        path = self.root / "state.yaml"
        path.write_bytes(
            (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
        )
        return path

    def render(self, value: dict | None = None):
        return self.renderer.render_bytes(
            source_path=self.source(self.candidate if value is None else value),
            profile_path=self.profile_path,
            repository_root=REPO,
        )

    def rejected(self, value: dict) -> None:
        with self.assertRaises(self.renderer.RendererError):
            self.render(value)

    def test_valid_complete_projection_and_read_only_check(self) -> None:
        output, summary = self.render()
        self.assertIn(b"Projection version: `6.0.0`", output)
        self.assertIn(self.source(self.candidate).read_bytes(), output)
        peer = self.root / "STATE.md"
        source = self.source(self.candidate)
        peer.write_bytes(output)
        before = peer.read_bytes()
        checked = self.renderer.check_projection(
            source_path=source,
            profile_path=self.profile_path,
            projection_path=peer,
            repository_root=REPO,
        )
        self.assertEqual(summary, checked)
        self.assertEqual(before, peer.read_bytes())

    def test_deterministic_render(self) -> None:
        self.assertEqual(self.render(), self.render())

    def test_all_twenty_whitelist_entries_are_the_only_delta(self) -> None:
        self.assertEqual(len(self.profile["delta_contract"]["delta_whitelist"]), 20)
        mutations = [
            ("baseline", lambda x: x["baseline"].update({"commit": "0" * 40})),
            (
                "foreign_work",
                lambda x: next(
                    w for w in x["work_items"] if w["work_item_id"] == "K0b-03"
                ).update(status="complete"),
            ),
            ("open_gate", lambda x: x["open_gates"][0].update(status="closed")),
            ("closed_gate", lambda x: x["closed_gates"][0].update(status="open")),
            ("runtime", lambda x: x["scope"].update(runtime_authority="approved")),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name):
                value = copy.deepcopy(self.candidate)
                mutate(value)
                self.rejected(value)

    def test_k0b02_final_audit_authority_and_evidence_required(self) -> None:
        for dotted in (
            "active_authority.K0b_02_final_audit_transition",
            "supporting_review_evidence.K0b_02_post_audit_remediation_validation",
            "supporting_review_evidence.K0b_02_post_audit_remediation_completion",
            "supporting_review_evidence.K0b_02_post_audit_remediation_materialization",
            "supporting_review_evidence.K0b_02_root_comparator_correction",
            "supporting_review_evidence.K0b_02_root_comparator_validation",
            "supporting_review_evidence.K0b_02_audit_correction_completion",
            "supporting_review_evidence.K0b_02_audit_correction_materialization",
            "supporting_review_evidence.K0b_02_final_external_audit",
        ):
            with self.subTest(path=dotted):
                value = copy.deepcopy(self.candidate)
                first, second = dotted.split(".")
                value[first][second]["sha256"] = "0" * 64
                self.rejected(value)

    def test_profile_binding_and_time_rejected(self) -> None:
        for mode in ("profile", "time"):
            value = copy.deepcopy(self.candidate)
            if mode == "profile":
                value["projection_profile"]["sha256"] = "0" * 64
            else:
                value["generated_at"] = "not-a-time"
            with self.subTest(mode=mode):
                self.rejected(value)

    def test_gate_inventory_unchanged(self) -> None:
        self.assertEqual(
            (len(self.candidate["open_gates"]), len(self.candidate["closed_gates"])),
            (7, 10),
        )

    def test_root_reference_exception_is_literal(self) -> None:
        with self.assertRaisesRegex(
            self.renderer.RendererError, "source:reference_scope"
        ):
            self.renderer.reference("other-root-file", "0" * 64, REPO, self.profile)
        pin = next(
            x
            for x in self.profile["reference_contract"]["pins"]
            if x["path"] == ".gitattributes"
        )
        self.renderer.reference(pin["path"], pin["sha256"], REPO, self.profile)

    def test_drift_check_does_not_write(self) -> None:
        output, _ = self.render()
        peer = self.root / "STATE.md"
        source = self.source(self.candidate)
        peer.write_bytes(output + b"drift\n")
        before = peer.read_bytes()
        with self.assertRaisesRegex(
            self.renderer.RendererError, "projection:byte_mismatch"
        ):
            self.renderer.check_projection(
                source_path=source,
                profile_path=self.profile_path,
                projection_path=peer,
                repository_root=REPO,
            )
        self.assertEqual(before, peer.read_bytes())

    def test_cli_collision_preserves_source(self) -> None:
        source = self.source(self.candidate)
        before = source.read_bytes()
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(REPO / RENDERER_REL),
                "render",
                "--source",
                str(source),
                "--profile",
                str(self.profile_path),
                "--repository-root",
                str(REPO),
                "--output",
                str(source),
            ],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"output:input_collision", result.stderr)
        self.assertEqual(before, source.read_bytes())


def main() -> int:
    global REPO, CANDIDATE, SCRATCH
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    REPO, CANDIDATE, SCRATCH = (
        args.repository_root.absolute(),
        args.candidate.absolute(),
        args.scratch.absolute(),
    )
    expected = Path(sys.executable).parent.parent.absolute()
    if SCRATCH != expected / "renderer-v6-tests" or not CANDIDATE.is_relative_to(
        expected
    ):
        parser.error(
            "Candidate and scratch must be confined to this exact locked environment"
        )
    SCRATCH.mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RendererV6Tests)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    print(
        json.dumps(
            {
                "result": "pass" if result.wasSuccessful() else "fail",
                "tests": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
            },
            sort_keys=True,
        )
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
