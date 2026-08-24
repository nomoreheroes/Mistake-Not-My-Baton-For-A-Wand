"""Executable regression model for the non-infra J4 generation/CAS contract."""

from dataclasses import dataclass, field
from typing import Optional
import unittest


@dataclass
class Generation:
    run_id: str
    parent_id: Optional[str]
    core_hash: str
    artifact_hashes_valid: bool = True
    manifest_written: bool = False


@dataclass
class State:
    revision: int = 0
    current: Optional[str] = None
    active: Optional[dict] = None
    generations: dict[str, Generation] = field(default_factory=dict)


def register(state: State, run_id: str, attempt: int) -> None:
    assert state.active is None
    assert run_id not in state.generations
    state.active = {
        "run_id": run_id,
        "attempt": attempt,
        "parent": state.current,
        "lease_revision": state.revision + 1,
    }
    state.revision += 1


def clear_failed(state: State, run_id: str) -> bool:
    if state.active is None or state.active["run_id"] != run_id:
        return False
    state.active = None
    state.revision += 1
    return True


def seal_and_publish(state: State, generation: Generation) -> bool:
    active = state.active
    if active is None or active["run_id"] != generation.run_id:
        return False
    if active["lease_revision"] != state.revision:
        return False
    if active["parent"] != state.current or generation.parent_id != state.current:
        return False
    if not generation.artifact_hashes_valid:
        clear_failed(state, generation.run_id)
        return False
    generation.manifest_written = True  # J0-owned last write before pointer CAS
    state.generations[generation.run_id] = generation
    state.current = generation.run_id
    state.active = None
    state.revision += 1
    return True


def replace_timed_out(state: State, old_run_id: str, new_run_id: str, attempt: int) -> bool:
    if state.active is None or state.active["run_id"] != old_run_id:
        return False
    parent = state.current
    state.active = None
    state.revision += 1
    register(state, new_run_id, attempt)
    assert state.active["parent"] == parent
    return True


def can_run(readiness: dict[str, bool], unit: str) -> bool:
    """JIT gate: only the unit's own flag matters."""
    return readiness[unit]


def reuse_prior_work(parent_core_hash: str, child_core_hash: str) -> bool:
    return parent_core_hash == child_core_hash


class J4GenerationFSM(unittest.TestCase):
    def test_publish_requires_matching_active_run_and_parent(self):
        state = State(current="g0")
        register(state, "g1", 1)
        self.assertFalse(seal_and_publish(state, Generation("other", "g0", "core")))
        self.assertFalse(seal_and_publish(state, Generation("g1", "other", "core")))
        self.assertEqual(state.current, "g0")
        self.assertFalse(state.generations)

    def test_manifest_is_written_before_pointer_moves(self):
        state = State()
        register(state, "g1", 1)
        generation = Generation("g1", None, "core")
        self.assertTrue(seal_and_publish(state, generation))
        self.assertTrue(generation.manifest_written)
        self.assertEqual(state.current, "g1")
        self.assertIsNone(state.active)

    def test_late_timed_out_writer_cannot_publish(self):
        state = State(current="g0")
        register(state, "slow", 1)
        self.assertTrue(replace_timed_out(state, "slow", "fresh", 2))
        self.assertFalse(seal_and_publish(state, Generation("slow", "g0", "old")))
        self.assertTrue(seal_and_publish(state, Generation("fresh", "g0", "new")))
        self.assertEqual(state.current, "fresh")

    def test_revision_cas_rejects_concurrent_state_change(self):
        state = State(current="g0")
        register(state, "g1", 1)
        state.revision += 1  # models another accepted state transition
        self.assertFalse(seal_and_publish(state, Generation("g1", "g0", "core")))
        self.assertEqual(state.current, "g0")

    def test_failure_clears_only_matching_attempt(self):
        state = State()
        register(state, "g1", 1)
        self.assertFalse(clear_failed(state, "stale"))
        self.assertEqual(state.active["run_id"], "g1")
        self.assertTrue(clear_failed(state, "g1"))
        self.assertIsNone(state.active)

    def test_invalid_hashes_never_create_a_current_generation(self):
        state = State(current="g0")
        register(state, "g1", 1)
        generation = Generation("g1", "g0", "core", artifact_hashes_valid=False)
        self.assertFalse(seal_and_publish(state, generation))
        self.assertFalse(generation.manifest_written)
        self.assertEqual(state.current, "g0")
        self.assertIsNone(state.active)

    def test_readiness_is_checked_just_in_time(self):
        readiness = {"J5": True, "J6": True, "J10": False}
        self.assertTrue(can_run(readiness, "J5"))
        self.assertTrue(can_run(readiness, "J6"))
        self.assertFalse(can_run(readiness, "J10"))

    def test_plan_only_corrective_generation_reuses_work_only_for_same_core(self):
        self.assertTrue(reuse_prior_work("sha256:core", "sha256:core"))
        self.assertFalse(reuse_prior_work("sha256:old", "sha256:new"))


if __name__ == "__main__":
    unittest.main()
