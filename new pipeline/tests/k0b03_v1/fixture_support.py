from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HARNESS_ROOT = REPOSITORY_ROOT / "new pipeline/harness/k0b03_v1"
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from canonical import CanonicalError, canonical_bytes, canonical_sha256, load_strict, loads_strict, sha256_file
from compatibility import CompatibilityError, apply_migration, backup_database, database_integrity, older_harness_disposition, restore_to_new_target, schema_version
from compiler import OUTPUT_NAMES, compile_package, output_manifest
from contract import ContractError, validate_detector_profile, validate_scan_request
from guards import GuardError, file_sha256, guarded_repository_path, stat_is_reparse, validate_invocation
from lifecycle import Intent, LifecycleError, admit_resume, reconcile_abort, request_abort, security_policy_route
from scanner import scan_bytes, scan_request
from store import EvidenceStore, StoreError


PROFILE_PATH = REPOSITORY_ROOT / "new pipeline/registry/k0b03/detector-profile-v1.json"
POLICY_PATH = REPOSITORY_ROOT / "new pipeline/registry/k0b03/repository-tool-policy-v1.json"
MIGRATION_PATH = REPOSITORY_ROOT / "new pipeline/harness/migrations/0007_k0b03_compatibility_evidence_v1.sql"
PROFILE = load_strict(PROFILE_PATH)
POLICY = load_strict(POLICY_PATH)


def environment_root() -> Path:
    value = os.environ.get("K0B03_ENV_ROOT")
    if not value:
        raise RuntimeError("K0B03_ENV_ROOT is required")
    return Path(value)


def load_cases(filename: str, group: str | None = None) -> list[dict[str, Any]]:
    data = load_strict(Path(__file__).parent / "fixtures" / filename)
    cases = data["cases"]
    return [case for case in cases if group is None or case.get("group") == group]


def attach_cases(cls: type, cases: list[dict[str, Any]], handler: Callable[[Any, dict[str, Any]], None]) -> None:
    for case in cases:
        def test(self: Any, current: dict[str, Any] = case) -> None:
            handler(self, current)
        test.__name__ = f"test_{case['id']}_{case['kind']}"
        setattr(cls, test.__name__, test)


def _scan(text: str | bytes, cap: int = 1048576) -> dict[str, Any]:
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    return scan_bytes(data, "fixture/source", "fixture-binding", cap, PROFILE)


def _categories(result: dict[str, Any]) -> list[str]:
    return [item["detector_category"] for item in result["findings"]]


def _synthetic_suffix(length: int, alphabet: str | None = None) -> str:
    if alphabet == "uppercase_alphanumeric":
        return ("A1B2C3D4E5F6G7H8" * ((length + 15) // 16))[:length]
    if alphabet == "ascii_alphanumeric_underscore_hyphen":
        return ("Ab3_Cd4-Ef5_Gh6-" * ((length + 15) // 16))[:length]
    return ("Ab3_Cd4-Ef5.Gh6/" * ((length + 16) // 17))[:length]


def run_detector_case(testcase: Any, case: dict[str, Any]) -> None:
    kind = case["kind"]
    if kind == "label_positive":
        result = _scan(case["variant"] + "=" + "Synth" + "Value123")
        testcase.assertIn("labelled_secret", _categories(result))
    elif kind == "private_header":
        middle = "PRIVATE KEY" if case["variant"] == "GENERIC" else case["variant"] + " PRIVATE KEY"
        testcase.assertIn("private_key", _categories(_scan("-----BEGIN " + middle + "-----")))
    elif kind == "label_short_clean":
        testcase.assertNotIn("labelled_secret", _categories(_scan("password=short")))
    elif kind == "label_hyphen_positive":
        testcase.assertIn("labelled_secret", _categories(_scan("client-secret=" + "Synthetic" + "Value")))
    elif kind in {"jwt_positive", "jwt_no_authenticity_claim"}:
        testcase.assertIn("jwt", _categories(_scan("ab.cd.ef")))
    elif kind == "jwt_empty_signature":
        testcase.assertIn("jwt", _categories(_scan("ab.cd.")))
    elif kind == "jwt_short_clean":
        testcase.assertNotIn("jwt", _categories(_scan("a.b.c")))
    elif kind == "authorization_bearer":
        testcase.assertIn("authorization_bearer", _categories(_scan("Authorization: Bearer " + "Synthetic" + "Token")))
    elif kind == "standalone_bearer":
        testcase.assertIn("standalone_bearer", _categories(_scan("Bearer " + "Synthetic" + "Token")))
    elif kind == "bearer_word_clean":
        testcase.assertNotIn("standalone_bearer", _categories(_scan("Bearer")))
    elif kind == "bearer_short_clean":
        testcase.assertNotIn("standalone_bearer", _categories(_scan("Bearer short")))
    elif kind == "provider_positive":
        spec = PROFILE["provider_tokens"][case["variant"]]
        value = spec["prefix"] + _synthetic_suffix(spec["suffix_minimum"], spec.get("suffix_alphabet"))
        testcase.assertIn("provider_token", _categories(_scan(value)))
    elif kind == "provider_short_clean":
        testcase.assertNotIn("provider_token", _categories(_scan("sk-" + "ShortValue")))
    elif kind == "aws_lowercase_clean":
        testcase.assertNotIn("provider_token", _categories(_scan("AKIA" + "abcdefghijklmnop")))
    elif kind == "entropy_positive":
        value = "".join(["Ab3_", "Cd4-", "Ef5.", "Gh6/", "Ij7+", "Kl8="])
        testcase.assertIn("high_entropy", _categories(_scan(value)))
    elif kind == "entropy_low_clean":
        testcase.assertNotIn("high_entropy", _categories(_scan("a" * 32)))
    elif kind == "hex40_clean":
        testcase.assertNotIn("high_entropy", _categories(_scan("a1" * 20)))
    elif kind == "hex64_clean":
        testcase.assertNotIn("high_entropy", _categories(_scan("a1" * 32)))
    elif kind == "labelled_hex40_positive":
        testcase.assertIn("labelled_secret", _categories(_scan("secret=" + "a1" * 20)))
    elif kind == "base64_valid":
        encoded = base64.b64encode(b"plain synthetic fixture text").decode("ascii")
        testcase.assertIn("base64", _categories(_scan(encoded)))
    elif kind == "base64_decoded_secret":
        decoded = "password=" + "Synthetic" + "DecodedValue"
        encoded = base64.b64encode(decoded.encode()).decode()
        result = _scan(encoded)
        testcase.assertIn("base64", _categories(result))
        testcase.assertTrue(any(x["representation_kind"] == "base64_decoded" and x["detector_category"] == "labelled_secret" for x in result["findings"]))
    elif kind == "base64_invalid_clean":
        testcase.assertNotIn("base64", _categories(_scan("A" * 23 + "!")))
    elif kind == "base64_non_recursive":
        inner = base64.b64encode(("secret=" + "Synthetic" + "NestedValue").encode())
        outer = base64.b64encode(inner).decode()
        result = _scan(outer)
        testcase.assertFalse(any(x["representation_kind"] == "base64_decoded" and x["detector_category"] == "labelled_secret" for x in result["findings"]))
    elif kind == "split_label_two_lines":
        result = _scan("password=Syn\n  theticValue")
        testcase.assertTrue(any(x["representation_kind"] == "split_line" and x["detector_category"] == "labelled_secret" for x in result["findings"]))
    elif kind == "split_provider_four_lines":
        result = _scan("sk-proj-AB3_\nCD4-EF5.\nGH6/IJ7_\nKL8-MN9.")
        testcase.assertTrue(any(x["representation_kind"] == "split_line" and x["detector_category"] == "provider_token" for x in result["findings"]))
    elif kind == "split_five_line_limit":
        result = _scan("password=\nA\nB\nC\nDEFGHIJK")
        testcase.assertFalse(any(x["representation_kind"] == "split_line" and x["detector_category"] == "labelled_secret" for x in result["findings"]))
    elif kind == "invalid_utf8_block":
        result = _scan(b"\xff\xfe")
        testcase.assertEqual(result["result"], "blocked")
        testcase.assertEqual(result["findings"], [])
    elif kind == "byte_cap_block":
        result = _scan("ordinary text", cap=4)
        testcase.assertEqual(result["result"], "blocked")
    elif kind == "bom_is_content":
        result = _scan("\ufeffordinary text")
        testcase.assertEqual(result["result"], "no_shape_finding_observed")
    elif kind == "deterministic_order":
        text = "Bearer SyntheticToken password=SyntheticValue123"
        first = _scan(text)
        second = _scan(text)
        testcase.assertEqual(first, second)
        starts = [x["original_byte_spans"][0][0] for x in first["findings"]]
        testcase.assertEqual(starts, sorted(starts))
    elif kind == "exact_dedup":
        result = _scan("password=SyntheticValue123")
        keys = [(x["detector_category"], x["representation_kind"], tuple(map(tuple, x["original_byte_spans"]))) for x in result["findings"]]
        testcase.assertEqual(len(keys), len(set(keys)))
    elif kind == "finding_overflow":
        text = " ".join("password=Synth%04dValue" % index for index in range(65))
        result = _scan(text)
        testcase.assertEqual(len(result["findings"]), 64)
        testcase.assertTrue(result["overflow"])
        testcase.assertEqual(result["result"], "blocked")
    elif kind == "redaction_shape":
        result = _scan("secret=" + "Synthetic" + "Value123")
        allowed = set(PROFILE["finding"]["allowed_fields"])
        testcase.assertTrue(result["findings"])
        testcase.assertEqual(set(result["findings"][0]), allowed)
    elif kind == "crlf_split_mapping":
        result = _scan("password=Syn\r\n\ttheticValue")
        finding = next(x for x in result["findings"] if x["representation_kind"] == "split_line" and x["detector_category"] == "labelled_secret")
        testcase.assertEqual(len(finding["original_byte_spans"]), 2)
    else:
        raise AssertionError(f"unknown detector case {kind}")


def _guard_fixture_paths(name: str, directory: bool = False) -> tuple[Path, Path]:
    root = environment_root()
    target = root / "fixture-repos" / (name + "-target")
    link = root / "reparse-fixtures" / (name + "-link")
    if link.exists() or link.is_symlink():
        link.unlink()
    if directory:
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("canary", encoding="utf-8")
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        raise AssertionError(f"real symlink fixture unavailable: {exc.winerror if hasattr(exc, 'winerror') else exc}") from exc
    info = link.lstat()
    if not link.is_symlink() or not stat_is_reparse(info):
        link.unlink(missing_ok=True)
        raise AssertionError("fixture lacks symlink/reparse identity")
    return target, link


def _remove_link(link: Path) -> None:
    if link.is_symlink():
        link.unlink()


def _valid_envelope() -> tuple[dict[str, Any], set[str], set[str], dict[str, dict[str, str]], set[str]]:
    executable = Path(sys.executable)
    env_root = environment_root()
    working_directory = env_root / "work"
    working_directory.mkdir(parents=True, exist_ok=True)
    executable_sha256 = file_sha256(executable)
    envelope = {
        "schema_version": "1.0.0",
        "effect_id": "fixture-effect-001",
        "executable": executable.as_posix(),
        "executable_sha256": executable_sha256,
        "executable_version": platform.python_version(),
        "arguments": ["-B"],
        "working_directory": working_directory.as_posix(),
        "environment": {"K0B03_ENV_ROOT": env_root.as_posix()},
        "timeout_seconds": 30,
        "cpu_seconds_maximum": 15,
        "memory_bytes_maximum": 134217728,
        "process_count_maximum": 2,
        "output_bytes_maximum": 4096,
        "owned_process_tree": True,
        "cancellable": True,
        "expected_result": "exit_0",
    }
    admitted_executables = {
        os.path.normcase(os.path.abspath(os.fspath(executable))): {
            "sha256": executable_sha256,
            "version": platform.python_version(),
        }
    }
    return envelope, {"K0B03_ENV_ROOT"}, {"-B"}, admitted_executables, {working_directory.as_posix()}


def _validate_fixture_invocation(envelope: dict[str, Any], env_names: set[str], args: set[str], admitted: dict[str, dict[str, str]], working: set[str], policy: dict[str, Any] = POLICY) -> dict[str, Any]:
    return validate_invocation(envelope, policy, env_names, args, admitted, working)


def run_guard_case(testcase: Any, case: dict[str, Any]) -> None:
    kind = case["kind"]
    root = environment_root() / "fixture-repos" / "guard-repository"
    root.mkdir(parents=True, exist_ok=True)
    (root / "ordinary.txt").write_text("ordinary", encoding="utf-8")
    if kind == "repository_path_valid":
        testcase.assertEqual(guarded_repository_path(root, "ordinary.txt"), root / "ordinary.txt")
    elif kind == "absolute_path_rejected":
        with testcase.assertRaises(GuardError): guarded_repository_path(root, Path(sys.executable).as_posix())
    elif kind == "traversal_rejected":
        with testcase.assertRaises(GuardError): guarded_repository_path(root, "../escape")
    elif kind == "missing_output_parent_valid":
        testcase.assertEqual(guarded_repository_path(root, "new/file.json", output=True), root / "new/file.json")
    elif kind == "output_directory_rejected":
        (root / "directory").mkdir(exist_ok=True)
        with testcase.assertRaises(GuardError): guarded_repository_path(root, "directory", output=True)
    elif kind in {"file_symlink_rejected", "output_symlink_rejected"}:
        _, link = _guard_fixture_paths(case["id"], False)
        try:
            relative = os.path.relpath(link, root)
            with testcase.assertRaises(GuardError): guarded_repository_path(root, relative, output=kind.startswith("output"))
        finally:
            _remove_link(link)
    elif kind == "repository_root_symlink_rejected":
        _, link = _guard_fixture_paths(case["id"], True)
        try:
            with testcase.assertRaises(GuardError): guarded_repository_path(link, "ordinary.txt")
        finally:
            _remove_link(link)
    elif kind in {"intermediate_symlink_rejected", "output_parent_symlink_rejected"}:
        target, link = _guard_fixture_paths(case["id"], True)
        (target / "child.txt").write_text("canary", encoding="utf-8")
        try:
            relative = os.path.relpath(link / "child.txt", root)
            with testcase.assertRaises(GuardError): guarded_repository_path(root, relative, output=kind.startswith("output"))
        finally:
            _remove_link(link)
    elif kind == "synthetic_reparse_detected":
        testcase.assertTrue(stat_is_reparse(SimpleNamespace(st_file_attributes=0x400)))
    elif kind == "synthetic_normal_not_reparse":
        testcase.assertFalse(stat_is_reparse(SimpleNamespace(st_file_attributes=0)))
    elif kind == "invocation_valid_not_authorized":
        envelope, env_names, args, admitted, working = _valid_envelope()
        result = _validate_fixture_invocation(envelope, env_names, args, admitted, working)
        testcase.assertFalse(result["authorized"])
        unadmitted = dict(envelope); unadmitted["executable"] = Path(os.environ["WINDIR"], "System32", "where.exe").as_posix()
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(unadmitted, env_names, args, admitted, working)
        wrong_version = dict(envelope); wrong_version["executable_version"] = "0.0.0"
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(wrong_version, env_names, args, admitted, working)
        wrong_working = dict(envelope); wrong_working["working_directory"] = environment_root().as_posix()
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(wrong_working, env_names, args, admitted, working)
        for field, value in {
            "timeout_seconds": POLICY["process"]["timeout_seconds_maximum"] + 1,
            "cpu_seconds_maximum": POLICY["process"]["cpu_seconds_maximum"] + 1,
            "memory_bytes_maximum": POLICY["process"]["memory_bytes_maximum"] + 1,
            "process_count_maximum": POLICY["process"]["process_count_maximum"] + 1,
            "output_bytes_maximum": POLICY["process"]["output_bytes_maximum"] + 1,
        }.items():
            over_limit = dict(envelope); over_limit[field] = value
            with testcase.assertRaises(GuardError): _validate_fixture_invocation(over_limit, env_names, args, admitted, working)
        unowned = dict(envelope); unowned["owned_process_tree"] = False
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(unowned, env_names, args, admitted, working)
        wrong_result = dict(envelope); wrong_result["expected_result"] = "unknown"
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(wrong_result, env_names, args, admitted, working)
    elif kind == "executable_hash_rejected":
        envelope, env_names, args, admitted, working = _valid_envelope(); envelope["executable_sha256"] = "0" * 64
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(envelope, env_names, args, admitted, working)
    elif kind == "argument_rejected":
        envelope, env_names, args, admitted, working = _valid_envelope(); envelope["arguments"] = ["--unknown"]
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(envelope, env_names, args, admitted, working)
    elif kind == "environment_extra_rejected":
        envelope, env_names, args, admitted, working = _valid_envelope(); envelope["environment"]["EXTRA"] = "value"
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(envelope, env_names, args, admitted, working)
    elif kind == "credential_environment_rejected":
        envelope, _, args, admitted, working = _valid_envelope(); envelope["environment"] = {"API_TOKEN": "opaque"}
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(envelope, {"API_TOKEN"}, args, admitted, working)
    elif kind == "egress_nonempty_rejected":
        envelope, env_names, args, admitted, working = _valid_envelope(); policy = json.loads(json.dumps(POLICY)); policy["egress"]["allowed_hosts"] = ["example.invalid"]
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(envelope, env_names, args, admitted, working, policy)
    elif kind in {"unsafe_effect_id_rejected", "zero_timeout_rejected", "zero_output_cap_rejected"}:
        envelope, env_names, args, admitted, working = _valid_envelope()
        if kind == "unsafe_effect_id_rejected": envelope["effect_id"] = "unsafe effect"
        if kind == "zero_timeout_rejected": envelope["timeout_seconds"] = 0
        if kind == "zero_output_cap_rejected": envelope["output_bytes_maximum"] = 0
        with testcase.assertRaises(GuardError): _validate_fixture_invocation(envelope, env_names, args, admitted, working)
        if kind == "zero_output_cap_rejected":
            for field in ("cpu_seconds_maximum", "memory_bytes_maximum", "process_count_maximum"):
                zero_limit, _, _, _, _ = _valid_envelope(); zero_limit[field] = 0
                with testcase.assertRaises(GuardError): _validate_fixture_invocation(zero_limit, env_names, args, admitted, working)
    elif kind == "missing_executable_rejected":
        envelope, env_names, args, admitted, working = _valid_envelope(); envelope["executable"] = (environment_root() / "work/missing.exe").as_posix()
        with testcase.assertRaises((GuardError, FileNotFoundError)): _validate_fixture_invocation(envelope, env_names, args, admitted, working)
    elif kind == "owned_process_tree_policy": testcase.assertTrue(POLICY["process"]["owned_declared_tree_only"])
    elif kind == "remote_effects_forbidden": testcase.assertFalse(POLICY["egress"]["remote_effects"])
    elif kind == "plugins_forbidden": testcase.assertFalse(POLICY["tool"]["hooks_plugins_and_credential_helpers"])
    elif kind == "ambient_path_forbidden": testcase.assertFalse(POLICY["tool"]["ambient_PATH_substitution"])
    elif kind == "stable_effect_identity_required": testcase.assertTrue(POLICY["process"]["stable_effect_identity"])
    elif kind == "canary_unchanged":
        target, link = _guard_fixture_paths(case["id"], False)
        before = target.read_bytes()
        try:
            relative = os.path.relpath(link, root)
            with testcase.assertRaises(GuardError): guarded_repository_path(root, relative, output=True)
            testcase.assertEqual(target.read_bytes(), before)
        finally:
            _remove_link(link)
    else: raise AssertionError(f"unknown guard case {kind}")


def run_lifecycle_case(testcase: Any, case: dict[str, Any]) -> None:
    kind = case["kind"]
    if kind == "abort_running": testcase.assertEqual(request_abort("running", True), "aborting")
    elif kind == "abort_waiting": testcase.assertEqual(request_abort("waiting", True), "aborting")
    elif kind == "abort_completed_rejected":
        with testcase.assertRaises(LifecycleError): request_abort("completed", True)
    elif kind == "abort_stale_rejected":
        with testcase.assertRaises(LifecycleError): request_abort("running", False)
    elif kind == "reconcile_completed": testcase.assertEqual(reconcile_abort([Intent("e1", "completed", False, True)])["terminal_state"], "aborted")
    elif kind == "reconcile_cancellable": testcase.assertEqual(reconcile_abort([Intent("e1", "started", True, False)])["cancel_effect_ids"], ["e1"])
    elif kind == "reconcile_unknown_blocks": testcase.assertEqual(reconcile_abort([Intent("e1", "started", False, False)])["terminal_state"], "blocked")
    elif kind == "unknown_no_retry": testcase.assertFalse(reconcile_abort([Intent("e1", "unknown", False, False)])["retry"])
    elif kind == "security_route": testcase.assertEqual(security_policy_route(False)["terminal_policy"], "block_run_and_enqueue_human")
    elif kind == "leak_route_freezes": testcase.assertTrue(security_policy_route(True)["publisher_frozen"])
    elif kind == "raw_material_not_persisted": testcase.assertFalse(security_policy_route(True)["raw_material_persisted"])
    elif kind == "resume_pass_not_authorized": testcase.assertFalse(admit_resume(True, True, False)["authorized"])
    elif kind == "resume_pin_mismatch": testcase.assertEqual(admit_resume(False, True, False)["result"], "blocked")
    elif kind == "resume_unknown_effect": testcase.assertEqual(admit_resume(True, True, True)["result"], "blocked")
    else: raise AssertionError(f"unknown lifecycle case {kind}")


def _fresh_database(name: str) -> Path:
    path = environment_root() / "db" / f"{name}.sqlite3"
    path.unlink(missing_ok=True)
    apply_migration(path, MIGRATION_PATH)
    return path


def run_compatibility_case(testcase: Any, case: dict[str, Any]) -> None:
    kind = case["kind"]
    database = _fresh_database(case["id"])
    if kind == "apply_migration_version": testcase.assertEqual(schema_version(database), 7)
    elif kind == "migration_tables":
        with sqlite3.connect(database) as connection:
            names={x[0] for x in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        testcase.assertTrue({"k0b03_compatibility_evidence","k0b03_effect_intents","k0b03_quarantine"} <= names)
    elif kind == "backup_new_target":
        target=environment_root()/"backups"/f"{case['id']}.sqlite3"; target.unlink(missing_ok=True); testcase.assertEqual(len(backup_database(database,target)),64)
    elif kind == "backup_existing_rejected":
        target=environment_root()/"backups"/f"{case['id']}.sqlite3"; target.parent.mkdir(exist_ok=True); target.write_bytes(b"exists")
        with testcase.assertRaises(CompatibilityError): backup_database(database,target)
    elif kind == "restore_new_target":
        backup=environment_root()/"backups"/f"{case['id']}.sqlite3"; backup.unlink(missing_ok=True); backup_database(database,backup)
        target=environment_root()/"restore"/f"{case['id']}.sqlite3"; target.unlink(missing_ok=True); testcase.assertEqual(len(restore_to_new_target(backup,target)),64)
    elif kind == "restore_existing_rejected":
        backup=environment_root()/"backups"/f"{case['id']}.sqlite3"; backup.unlink(missing_ok=True); backup_database(database,backup)
        target=environment_root()/"restore"/f"{case['id']}.sqlite3"; target.parent.mkdir(exist_ok=True); target.write_bytes(b"exists")
        with testcase.assertRaises(CompatibilityError): restore_to_new_target(backup,target)
    elif kind == "integrity_check": testcase.assertEqual(database_integrity(database),"ok")
    elif kind == "foreign_key_check":
        with sqlite3.connect(database) as connection: testcase.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(),[])
    elif kind == "older_harness_read_only": testcase.assertEqual(older_harness_disposition(database,6),"read_only_diagnostic")
    elif kind == "supported_version_compatible": testcase.assertEqual(older_harness_disposition(database,7),"compatible")
    elif kind in {"store_record_intent","store_stale_transition","store_quarantine","store_unresolved_order"}:
        store=EvidenceStore(database); stamp="2026-10-01T00:00:00Z"; digest="0"*64
        store.record_intent("effect-b","run-1","fixture",digest,stamp)
        if kind == "store_record_intent": testcase.assertEqual(store.unresolved("run-1"),[("effect-b","prepared")])
        elif kind == "store_stale_transition":
            with testcase.assertRaises(StoreError): store.transition_intent("effect-b","started","completed",stamp,digest)
        elif kind == "store_quarantine":
            store.quarantine("q1","effect-b","UNKNOWN",digest,stamp); testcase.assertEqual(store.unresolved("run-1"),[])
        else:
            store.record_intent("effect-a","run-1","fixture",digest,stamp); testcase.assertEqual(store.unresolved("run-1"),[("effect-a","prepared"),("effect-b","prepared")])
    else: raise AssertionError(f"unknown compatibility case {kind}")


def run_compiler_case(testcase: Any, case: dict[str, Any]) -> None:
    kind=case["kind"]; work=environment_root()/"work"/case["id"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True,exist_ok=True)
    if kind == "canonical_sort_hash": testcase.assertEqual(canonical_bytes({"b":1,"a":2}),b'{"a":2,"b":1}\n')
    elif kind == "duplicate_key_rejected":
        with testcase.assertRaises(CanonicalError): loads_strict(b'{"a":1,"a":2}\n')
    elif kind == "profile_contract": testcase.assertEqual(validate_detector_profile(PROFILE)["classification"],"heuristic_hygiene_only")
    elif kind == "compile_four_outputs":
        output=work/"compiled"; compile_package(REPOSITORY_ROOT,output); testcase.assertEqual([x["name"] for x in output_manifest(output)],OUTPUT_NAMES)
    elif kind == "second_compile_identical":
        first=work/"first"; second=work/"second"; compile_package(REPOSITORY_ROOT,first); compile_package(REPOSITORY_ROOT,second)
        testcase.assertEqual([x.read_bytes() for x in sorted(first.iterdir())],[x.read_bytes() for x in sorted(second.iterdir())])
    elif kind == "scan_request_closed":
        request={"schema_version":"1.0.0","authenticated":True,"profile_sha256":canonical_sha256(PROFILE),"caller_byte_cap":1024,"fields":[{"field_type":"untrusted_text","source_id":"fixture","safe_source_binding":"binding","text_utf8":"ordinary"}],"extra":True}
        with testcase.assertRaises(ContractError): validate_scan_request(request)
    elif kind == "cli_scan_not_authorized":
        request={"schema_version":"1.0.0","authenticated":True,"profile_sha256":canonical_sha256(PROFILE),"caller_byte_cap":1024,"fields":[{"field_type":"untrusted_text","source_id":"fixture","safe_source_binding":"binding","text_utf8":"ordinary"}]}
        testcase.assertFalse(scan_request(request,PROFILE)["authorized"])
    elif kind == "toolchain_stdlib_pins":
        lock=load_strict(REPOSITORY_ROOT/"new pipeline/toolchain/k0b03/toolchain-lock-v1.json")
        testcase.assertEqual(lock["dependencies"],[]); testcase.assertEqual(lock["runtime_authority"],"none")
    else: raise AssertionError(f"unknown compiler case {kind}")
