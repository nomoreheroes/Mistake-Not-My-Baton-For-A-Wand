from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = None
CANDIDATE = None
SCRATCH = None
PROFILE_REL = "new pipeline/state/renderer/k0b02_v4/projection-profile-v4.yaml"
RENDERER_REL = "new pipeline/state/renderer/k0b02_v4/renderer.py"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


class RendererV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "approved_renderer_v4", REPO / RENDERER_REL
        )
        cls.renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.renderer)
        cls.profile_path = REPO / PROFILE_REL
        cls.profile = json.loads(cls.profile_path.read_bytes())
        cls.candidate = json.loads(CANDIDATE.read_bytes())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="renderer-v4-", dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.fixture = Path(self.temp.name)
        self.source = self.fixture / "state.yaml"

    def source_for(self, value):
        self.source.write_bytes(
            (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
        return self.source

    def render(self, value=None, profile=None):
        return self.renderer.render_bytes(
            source_path=self.source_for(self.candidate if value is None else value),
            profile_path=self.profile_path if profile is None else profile,
            repository_root=REPO,
        )

    def rejected(self, value):
        with self.assertRaises(self.renderer.RendererError):
            self.render(value)

    def test_valid_candidate_and_complete_source_projection(self):
        output, summary = self.render()
        self.assertIn(b"Projection version:", output)
        self.assertIn(b"4.0.0", output)
        self.assertIn(
            bytes([96]) * 3
            + b"yaml\n"
            + self.source.read_bytes()
            + bytes([96]) * 3
            + b"\n",
            output,
        )
        self.assertEqual(summary["source_sha256"], sha(self.source.read_bytes()))
        self.assertEqual(summary["projection_sha256"], sha(output))
        self.assertEqual(len(self.candidate["open_gates"]), 7)
        self.assertEqual(len(self.candidate["closed_gates"]), 10)
        peer = self.fixture / "STATE.md"
        peer.write_bytes(output)
        original = {p: p.read_bytes() for p in (self.source, peer, self.profile_path)}
        checked = self.renderer.check_projection(
            source_path=self.source,
            profile_path=self.profile_path,
            projection_path=peer,
            repository_root=REPO,
        )
        self.assertEqual(checked, summary)
        self.assertEqual(original, {p: p.read_bytes() for p in original})

    def test_repeated_render_is_deterministic(self):
        self.assertEqual(self.render(), self.render())

    def test_foreign_gate_changes_rejected(self):
        for name in ("status", "owner", "closure_condition"):
            with self.subTest(field=name):
                value = copy.deepcopy(self.candidate)
                value["open_gates"][0][name] = "forged"
                self.rejected(value)

    def test_foreign_work_item_changes_rejected(self):
        value = copy.deepcopy(self.candidate)
        next(w for w in value["work_items"] if w["work_item_id"] == "K0b-03")[
            "status"
        ] = "complete"
        self.rejected(value)

    def test_duplicate_unknown_and_overlapping_gates_rejected(self):
        for mode in ("duplicate", "unknown", "overlap"):
            with self.subTest(mode=mode):
                value = copy.deepcopy(self.candidate)
                if mode == "duplicate":
                    value["closed_gates"].append(
                        copy.deepcopy(value["closed_gates"][-1])
                    )
                elif mode == "unknown":
                    value["closed_gates"][-1]["gate_id"] = "G-K0B03-UNTRUSTED-SHAPES"
                else:
                    value["closed_gates"][-1]["gate_id"] = value["open_gates"][0][
                        "gate_id"
                    ]
                self.rejected(value)

    def test_each_required_closure_must_exist(self):
        for index in (-1, -2):
            with self.subTest(index=index):
                value = copy.deepcopy(self.candidate)
                del value["closed_gates"][index]
                self.rejected(value)

    def test_work_item_gate_lists_must_match(self):
        value = copy.deepcopy(self.candidate)
        next(w for w in value["work_items"] if w["work_item_id"] == "K0b-02")[
            "open_gate_ids"
        ] = ["G-K0B02-K0B01-COMPLETE"]
        self.rejected(value)

    def test_runtime_and_implementation_escalation_rejected(self):
        for name in (
            "runtime_authority",
            "K0b_02_implementation_authority",
            "K0b_02_runtime_authority",
        ):
            with self.subTest(field=name):
                value = copy.deepcopy(self.candidate)
                value["scope"][name] = "approved"
                self.rejected(value)

    def test_forged_disposition_rejected(self):
        value = copy.deepcopy(self.candidate)
        value["active_authority"]["K0b_02_prerequisite_transition"]["sha256"] = "0" * 64
        self.rejected(value)

    def test_missing_and_mismatched_gate_evidence_rejected(self):
        for name in self.profile["transition_contract"]["bindings"]:
            for mode in ("missing", "mismatch"):
                with self.subTest(field=name, mode=mode):
                    value = copy.deepcopy(self.candidate)
                    if mode == "missing":
                        del value["closed_gates"][-1]["evidence"][name]
                    else:
                        value["closed_gates"][-1]["evidence"][name]["sha256"] = "0" * 64
                    self.rejected(value)

    def test_profile_binding_drift_rejected(self):
        value = copy.deepcopy(self.candidate)
        value["projection_profile"]["sha256"] = "0" * 64
        self.rejected(value)

    def test_schema_unknown_field_and_boolean_integer_rejected(self):
        for mode in ("unknown", "boolean"):
            with self.subTest(mode=mode):
                value = copy.deepcopy(self.candidate)
                if mode == "unknown":
                    value["scope"]["unapproved_field"] = "none"
                else:
                    value["scope"]["K0b_01_remaining_open_prerequisites"] = False
                self.rejected(value)

    def test_preserved_historical_evidence_and_closed_records(self):
        for field in ("supporting_review_evidence", "closed_gates"):
            with self.subTest(field=field):
                value = copy.deepcopy(self.candidate)
                if field == "closed_gates":
                    value[field][0]["status"] = "open"
                else:
                    value[field].clear()
                self.rejected(value)

    def test_drift_check_does_not_write(self):
        output, _ = self.render()
        peer = self.fixture / "STATE.md"
        peer.write_bytes(output + b"drift\n")
        before = peer.read_bytes()
        with self.assertRaisesRegex(
            self.renderer.RendererError, "projection:byte_mismatch"
        ):
            self.renderer.check_projection(
                source_path=self.source,
                profile_path=self.profile_path,
                projection_path=peer,
                repository_root=REPO,
            )
        self.assertEqual(peer.read_bytes(), before)

    def test_finite_reference_allowlist(self):
        with self.assertRaisesRegex(
            self.renderer.RendererError, "source:reference_scope"
        ):
            self.renderer.reference(
                "new pipeline/evidence/unapproved.yaml", "0" * 64, REPO, self.profile
            )

    def test_reference_missing_and_actual_hash_mismatch(self):
        root = self.fixture / "root"
        root.mkdir()
        relative = "new pipeline/receipts/k0b-01-implementation-completion-v1.yaml"
        with self.assertRaisesRegex(
            self.renderer.RendererError, "source:reference_missing"
        ):
            self.renderer.reference(relative, "0" * 64, root, self.profile)
        target = root / relative
        target.parent.mkdir(parents=True)
        target.write_bytes(b"bounded test fixture\n")
        with self.assertRaisesRegex(
            self.renderer.RendererError, "source:reference_hash"
        ):
            self.renderer.reference(relative, "0" * 64, root, self.profile)
        self.renderer.reference(relative, sha(target.read_bytes()), root, self.profile)

    def test_outside_root_path_is_rejected_before_read(self):
        root = self.fixture / "root"
        root.mkdir()
        outside = self.fixture / "outside"
        outside.write_bytes(b"outside fixture\n")
        profile = copy.deepcopy(self.profile)
        profile["reference_contract"]["allowed_repository_paths"].append("../outside")
        with self.assertRaisesRegex(self.renderer.RendererError, "source:path_escape"):
            self.renderer.reference(
                "../outside", sha(outside.read_bytes()), root, profile
            )
        self.assertEqual(outside.read_bytes(), b"outside fixture\n")

    def test_actual_windows_junction_and_root_rejected(self):
        self.assertEqual(os.name, "nt", "This approved lock is Windows-only")
        root = self.fixture / "root"
        (root / "new pipeline").mkdir(parents=True)
        target = self.fixture / "target"
        target.mkdir()
        leaf = target / "k0b-01-implementation-completion-v1.yaml"
        leaf.write_bytes(b"junction test fixture\n")
        link = root / "new pipeline/receipts"
        command = (
            "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path "
            + ps_quote(link)
            + " -Target "
            + ps_quote(target)
            + " | Out-Null"
        )
        created = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
        )
        self.assertEqual(created.returncode, 0, created.stderr.decode(errors="replace"))
        try:
            with self.assertRaisesRegex(self.renderer.RendererError, "reparse"):
                self.renderer.reference(
                    "new pipeline/receipts/k0b-01-implementation-completion-v1.yaml",
                    sha(leaf.read_bytes()),
                    root,
                    self.profile,
                )
            with self.assertRaisesRegex(self.renderer.RendererError, "reparse"):
                self.renderer.reference(
                    "new pipeline/receipts/k0b-01-implementation-completion-v1.yaml",
                    sha(leaf.read_bytes()),
                    link,
                    self.profile,
                )
        finally:
            removed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "[IO.Directory]::Delete(" + ps_quote(link) + ")",
                ],
                capture_output=True,
            )
            self.assertEqual(
                removed.returncode, 0, removed.stderr.decode(errors="replace")
            )
        self.assertTrue(
            leaf.is_file(), "Removing the junction must preserve its target"
        )

    def test_forged_profile_owner_binding_rejected(self):
        profile = copy.deepcopy(self.profile)
        profile["transition_contract"]["bindings"]["owner_disposition"]["sha256"] = (
            "0" * 64
        )
        path = self.fixture / "profile.yaml"
        path.write_bytes((json.dumps(profile, indent=2) + "\n").encode("utf-8"))
        with self.assertRaisesRegex(self.renderer.RendererError, "profile:authority"):
            self.renderer.load_profile(path)

    def test_cli_input_collision_preserves_source(self):
        source = self.source_for(self.candidate)
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
        self.assertEqual(source.read_bytes(), before)


def main():
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
    if SCRATCH != expected / "renderer-v4-tests" or not CANDIDATE.is_relative_to(
        expected
    ):
        parser.error(
            "Candidate and scratch must be confined to this exact locked environment"
        )
    SCRATCH.mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RendererV4Tests)
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
