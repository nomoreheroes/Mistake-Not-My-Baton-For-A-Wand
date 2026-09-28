from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RENDERER_PATH = ROOT / "new pipeline/state/renderer/k0b03_v7/renderer.py"
PROFILE_PATH = ROOT / "new pipeline/state/renderer/k0b03_v7/projection-profile-v7.yaml"
SOURCE_PATH = ROOT / "new pipeline/state/state.yaml"
PROJECTION_PATH = ROOT / "new pipeline/state/STATE.md"

SPEC = importlib.util.spec_from_file_location("pipeline_v2_renderer_v7", RENDERER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("renderer_import_spec")
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class RendererV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.source = renderer.read_json(SOURCE_PATH, "test_source")
        (
            cls.profile,
            cls.profile_sha,
            cls.allowed,
            cls.base_profile,
        ) = renderer.load_profile(PROFILE_PATH, ROOT)

    def render(self):
        return renderer.render_bytes(
            source_path=SOURCE_PATH,
            profile_path=PROFILE_PATH,
            repository_root=ROOT,
        )

    def validate_mutation(self, mutation) -> None:
        candidate = copy.deepcopy(self.source)
        mutation(candidate)
        renderer.validate_transition(
            candidate, self.profile, self.profile_sha, self.base_profile
        )

    def test_valid_candidate_and_complete_projection(self) -> None:
        output, summary = self.render()
        self.assertTrue(output.startswith(b"# Pipeline v2 state projection\n"))
        self.assertEqual(summary["open_gate_count"], 6)
        self.assertEqual(summary["closed_gate_count"], 11)
        self.assertEqual(output, PROJECTION_PATH.read_bytes())

    def test_repeated_render_is_deterministic(self) -> None:
        self.assertEqual(self.render(), self.render())

    def test_check_mode_is_read_only(self) -> None:
        before = PROJECTION_PATH.read_bytes()
        renderer.check_projection(
            source_path=SOURCE_PATH,
            profile_path=PROFILE_PATH,
            projection_path=PROJECTION_PATH,
            repository_root=ROOT,
        )
        self.assertEqual(before, PROJECTION_PATH.read_bytes())

    def test_foreign_gate_mutation_rejected(self) -> None:
        def mutate(candidate):
            candidate["open_gates"][1]["status"] = "closed"

        with self.assertRaisesRegex(renderer.RendererError, "outside_delta_whitelist"):
            self.validate_mutation(mutate)

    def test_untrusted_shapes_mutation_rejected(self) -> None:
        def mutate(candidate):
            candidate["open_gates"][0]["status"] = "closed"

        with self.assertRaisesRegex(renderer.RendererError, "untrusted_shapes"):
            self.validate_mutation(mutate)

    def test_untrusted_shapes_closure_rejected(self) -> None:
        def mutate(candidate):
            candidate["open_gates"].pop(0)
            candidate["work_items"][12]["open_gate_ids"] = []

        with self.assertRaisesRegex(renderer.RendererError, "source:K0b03"):
            self.validate_mutation(mutate)

    def test_K0b03_status_escalation_rejected(self) -> None:
        def mutate(candidate):
            candidate["work_items"][12]["status"] = "prerequisites_complete"

        with self.assertRaisesRegex(renderer.RendererError, "source:K0b03"):
            self.validate_mutation(mutate)

    def test_authority_evidence_mismatch_rejected(self) -> None:
        def mutate(candidate):
            candidate["active_authority"]["K0b_03_predecessor_gate_transition"][
                "sha256"
            ] = "0" * 64

        with self.assertRaisesRegex(renderer.RendererError, "active_authority"):
            self.validate_mutation(mutate)

    def test_closed_record_mismatch_rejected(self) -> None:
        def mutate(candidate):
            candidate["closed_gates"][-1]["closed_by"] = "automatic"

        with self.assertRaisesRegex(renderer.RendererError, "closed_record"):
            self.validate_mutation(mutate)

    def test_duplicate_and_overlapping_gate_rejected(self) -> None:
        duplicate = copy.deepcopy(self.source)
        duplicate["open_gates"].append(copy.deepcopy(duplicate["open_gates"][0]))
        with self.assertRaisesRegex(renderer.RendererError, "open_gate_duplicate"):
            renderer.validate_transition(
                duplicate, self.profile, self.profile_sha, self.base_profile
            )

        overlap = copy.deepcopy(self.source)
        overlap["open_gates"][0]["gate_id"] = "G-K0B03-K0B01-COMPLETE"
        with self.assertRaisesRegex(renderer.RendererError, "gate_overlap"):
            renderer.validate_transition(
                overlap, self.profile, self.profile_sha, self.base_profile
            )

    def test_extra_source_field_rejected(self) -> None:
        def mutate(candidate):
            candidate["unexpected"] = True

        with self.assertRaisesRegex(renderer.RendererError, "outside_delta_whitelist"):
            self.validate_mutation(mutate)

    def test_profile_binding_drift_rejected(self) -> None:
        with self.assertRaisesRegex(renderer.RendererError, "profile_binding"):
            renderer.validate_transition(
                self.source, self.profile, "0" * 64, self.base_profile
            )

    def test_absolute_escape_and_hash_mismatch_rejected(self) -> None:
        with self.assertRaisesRegex(renderer.RendererError, "reference_scope"):
            renderer.reference("C:/outside", "0" * 64, ROOT, self.allowed)
        with self.assertRaisesRegex(renderer.RendererError, "source_reference:hash"):
            renderer.reference(
                "new pipeline/PIPELINE_V2_DEVELOPMENT_PLAN.md",
                "0" * 64,
                ROOT,
                self.allowed,
            )

    def test_projection_drift_rejected_without_rewrite(self) -> None:
        before = SOURCE_PATH.read_bytes()
        with self.assertRaisesRegex(renderer.RendererError, "byte_mismatch"):
            renderer.check_projection(
                source_path=SOURCE_PATH,
                profile_path=PROFILE_PATH,
                projection_path=SOURCE_PATH,
                repository_root=ROOT,
            )
        self.assertEqual(before, SOURCE_PATH.read_bytes())


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RendererV7Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        {
            "result": "pass" if result.wasSuccessful() else "fail",
            "tests": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
        }
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
