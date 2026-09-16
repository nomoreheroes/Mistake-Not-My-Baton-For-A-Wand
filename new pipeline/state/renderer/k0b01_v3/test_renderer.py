from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROFILE = HERE / "projection-profile-v3.yaml"
GOLDEN = HERE / "fixtures/golden/state-v1.yaml"
PROJECTION = HERE / "fixtures/golden/STATE-v1.md"
REQUEST = (
    REPO
    / "new pipeline/requests/k0b-01-final-implementation-disposition-and-bounded-implementation-approval-request-v1.yaml"
)
spec = importlib.util.spec_from_file_location(
    "state_renderer_v3_tests", HERE / "renderer.py"
)
assert spec and spec.loader
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def load(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    value = yaml.load(path.read_bytes())
    assert isinstance(value, dict)
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    yaml = YAML()
    yaml.width = 120
    yaml.representer.ignore_aliases = lambda *args: True
    stream = StringIO()
    yaml.dump(value, stream)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stream.getvalue().encode("utf-8"))


def ref(path: str) -> dict[str, str]:
    return {"path": path, "sha256": "0" * 64}


def phase_a() -> dict[str, Any]:
    source = load(REPO / "new pipeline/state/state.yaml")
    request = load(REQUEST)
    source["projection_version"] = "3.0.0"
    profile = "new pipeline/state/renderer/k0b01_v3/projection-profile-v3.yaml"
    source["projection_profile"] = ref(profile)
    nav = {
        "K0b_01_final_implementation_approval_request": str(
            REQUEST.relative_to(REPO).as_posix()
        ),
        "K0b_01_final_implementation_disposition": request["phase_A_contract"][
            "owner_disposition"
        ]["path"],
        "K0b_01_implementation_session_allocation": request["phase_A_contract"][
            "session_allocation"
        ]["path"],
        "K0b_01_renderer_v3_profile": profile,
        "K0b_01_renderer_v3_validation": "new pipeline/evidence/k0b-01-final-disposition-renderer-v3-validation-v1.yaml",
        "K0b_01_final_implementation_gate_closure": request["phase_A_contract"][
            "closure"
        ]["path"],
        "K0b_01_active_ledger_index": "new pipeline/ledger/k0b01/index-v1.yaml",
    }
    for key, path in nav.items():
        source["active_authority"][key] = ref(path)
    source["open_gates"] = [
        g
        for g in source["open_gates"]
        if g["gate_id"] != "G-K0B01-IMPLEMENTATION-DISPOSITION"
    ]
    for gate in source["closed_gates"]:
        if gate["gate_id"] == "G-K0B01-STATE-RENDERER":
            gate["closure_evidence"]["ledger_registration"]["index"]["path"] = request[
                "historical_index_preservation"
            ]["snapshot_0"]["path"]
    if not any(
        g["gate_id"] == "G-K0B01-IMPLEMENTATION-DISPOSITION"
        for g in source["closed_gates"]
    ):
        source["closed_gates"].append(
            {
                "gate_id": "G-K0B01-IMPLEMENTATION-DISPOSITION",
                "status": "closed",
                "closure_evidence": {
                    "approval_request": ref(
                        nav["K0b_01_final_implementation_approval_request"]
                    ),
                    "owner_disposition": ref(
                        nav["K0b_01_final_implementation_disposition"]
                    ),
                    "session_allocation": ref(
                        nav["K0b_01_implementation_session_allocation"]
                    ),
                    "renderer_v3_validation": ref(nav["K0b_01_renderer_v3_validation"]),
                    "ledger_entry": {
                        "authorized_event": ref(
                            request["phase_A_contract"]["ledger_entry"]["exact_events"][
                                1
                            ]
                        ),
                        "index": ref(
                            request["historical_index_preservation"]["snapshot_1"][
                                "path"
                            ]
                        ),
                        "event_count": 32,
                    },
                    "gate_closure": ref(
                        nav["K0b_01_final_implementation_gate_closure"]
                    ),
                    "projection_profile": ref(profile),
                },
            }
        )
    for item in source["work_items"]:
        if item["work_item_id"] == "K0b-01":
            item["status"] = "implementation_authorized_not_started"
            item["authority_path"] = nav["K0b_01_final_implementation_disposition"]
            item["authority_sha256"] = "0" * 64
            item["open_gate_ids"] = []
    source["scope"]["implementation_authority"] = (
        "bounded_K0b_01_exact_phase_B_scope_only"
    )
    source["scope"]["K0b_01_remaining_open_prerequisites"] = 0
    source["scope"]["K0b_01_implementation_session_budget"] = 1
    source["scope"]["K0b_01_implementation_session_id"] = request["budget"][
        "implementation_session_id"
    ]
    source["scope"]["K0b_01_implementation_status"] = "authorized_not_started"
    return source


def phase_b() -> dict[str, Any]:
    source = phase_a()
    for item in source["work_items"]:
        if item["work_item_id"] == "K0b-01":
            item["status"] = "implemented_validated_runtime_not_authorized"
    source["scope"]["K0b_01_implementation_status"] = (
        "implemented_validated_runtime_not_authorized"
    )
    nav = {
        "K0b_01_implementation_input_manifest": "new pipeline/evidence/k0b-01-implementation-input-manifest-v2.yaml",
        "K0b_01_implementation_session_entry": "new pipeline/evidence/k0b-01-implementation-session-entry-v1.yaml",
        "K0b_01_implementation_session_completion": "new pipeline/evidence/k0b-01-implementation-session-completion-v1.yaml",
        "K0b_01_registry_routing_compiler_receipt": "new pipeline/evidence/k0b-01-registry-routing-compiler-receipt-v2.yaml",
        "K0b_01_resource_budget_compiler_receipt": "new pipeline/evidence/k0b-01-resource-budget-compiler-receipt-v2.yaml",
        "K0b_01_compiled_output_manifest": "new pipeline/evidence/k0b-01-compiled-output-manifest-v2.yaml",
        "K0b_01_implementation_validation": "new pipeline/evidence/k0b-01-implementation-validation-v2.yaml",
    }
    for key, path in nav.items():
        source["supporting_review_evidence"][key] = ref(path)
    return source


def synthetic(source: dict[str, Any], base: Path) -> tuple[Path, Path]:
    source = copy.deepcopy(source)
    scope = next(p for p in base.parents if p.name == ".tmp")
    assert scope.parent.name.startswith(
        "pipeline-v2-k0b01-final-disposition-implementation-v1-"
    )
    root = scope / "r" / hashlib.sha256(str(base).encode()).hexdigest()[:12]
    root.mkdir(parents=True)
    hashes: dict[str, str] = {}

    def materialize(path: str) -> str:
        if path not in hashes:
            candidate = root / path
            candidate.parent.mkdir(parents=True, exist_ok=True)
            data = (
                PROFILE.read_bytes()
                if path
                == "new pipeline/state/renderer/k0b01_v3/projection-profile-v3.yaml"
                else ("synthetic reference only: " + path + "\n").encode()
            )
            candidate.write_bytes(data)
            hashes[path] = hashlib.sha256(data).hexdigest()
        return hashes[path]

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if "path" in value and "sha256" in value:
                value["sha256"] = materialize(value["path"])
            if "authority_path" in value and "authority_sha256" in value:
                value["authority_sha256"] = materialize(value["authority_path"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(source)
    path = base / "state.yaml"
    write(path, source)
    return path, root


def render(source: Path = GOLDEN, root: Path = REPO) -> tuple[bytes, dict[str, str]]:
    return renderer.render_bytes(
        source_path=source, profile_path=PROFILE, repository_root=root
    )


def check(source: Path, root: Path, projection: Path) -> dict[str, str]:
    return renderer.check_projection(
        source_path=source,
        profile_path=PROFILE,
        repository_root=root,
        projection_path=projection,
    )


def cli(
    source: Path, root: Path, output: Path, *, cwd: Path, locale: str = "C"
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["LC_ALL"] = locale
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            str(HERE / "renderer.py"),
            "render",
            "--profile",
            str(PROFILE),
            "--source",
            str(source),
            "--repository-root",
            str(root),
            "--output",
            str(output),
        ],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_complete_golden_roundtrip() -> None:
    output, _ = render()
    assert output == PROJECTION.read_bytes()
    assert (
        check(GOLDEN, REPO, PROJECTION)["projection_sha256"]
        == hashlib.sha256(output).hexdigest()
    )


def test_phase_A_transition_schema_and_byte_equivalence(tmp_path: Path) -> None:
    source, root = synthetic(phase_a(), tmp_path)
    first, summary = render(source, root)
    second, second_summary = render(source, root)
    assert first == second and summary == second_summary
    projection = tmp_path / "STATE.md"
    projection.write_bytes(first)
    assert check(source, root, projection) == summary


def test_phase_B_transition_schema_and_byte_equivalence(tmp_path: Path) -> None:
    source, root = synthetic(phase_b(), tmp_path)
    output, summary = render(source, root)
    assert b"implemented_validated_runtime_not_authorized" in output
    projection = tmp_path / "STATE.md"
    projection.write_bytes(output)
    assert check(source, root, projection) == summary


def test_closed_gates_with_immutable_index_snapshots(tmp_path: Path) -> None:
    source, root = synthetic(phase_a(), tmp_path)
    output, _ = render(source, root)
    assert b"history/state-renderer-index-at-97a742a0-v1.yaml" in output
    assert b"history/final-disposition-entry-index-v1.yaml" in output
    before = source.read_bytes()
    render(source, root)
    assert source.read_bytes() == before


def test_hash_preamble_and_complete_embedded_source() -> None:
    output, summary = render()
    assert GOLDEN.read_bytes() in output
    assert summary["source_sha256"].encode() in output
    assert summary["profile_sha256"].encode() in output
    assert b"Source:" in output and output.endswith(b"```\n")


def test_caller_cwd_independence(tmp_path: Path) -> None:
    a = cli(GOLDEN, REPO, tmp_path / "a.md", cwd=tmp_path)
    b = cli(GOLDEN, REPO, tmp_path / "b.md", cwd=HERE)
    assert a.returncode == b.returncode == 0, (a.stderr, b.stderr)
    assert (tmp_path / "a.md").read_bytes() == (tmp_path / "b.md").read_bytes()


def test_locale_independence(tmp_path: Path) -> None:
    a = cli(GOLDEN, REPO, tmp_path / "a.md", cwd=tmp_path, locale="C")
    b = cli(GOLDEN, REPO, tmp_path / "b.md", cwd=tmp_path, locale="ru_RU.UTF-8")
    assert a.returncode == b.returncode == 0, (a.stderr, b.stderr)
    assert json.loads(a.stdout) == json.loads(b.stdout)
    assert (tmp_path / "a.md").read_bytes() == (tmp_path / "b.md").read_bytes()


def test_source_timestamp_only_output(tmp_path: Path) -> None:
    source = load(GOLDEN)
    source["generated_at"] = "2001-02-03T04:05:06+00:00"
    path, root = synthetic(source, tmp_path)
    output, _ = render(path, root)
    assert source["generated_at"].encode() in output
    assert path.read_bytes() in output
    assert str(tmp_path).encode() not in output


def test_variable_record_counts_within_closed_typed_schema(tmp_path: Path) -> None:
    source = load(GOLDEN)
    item = copy.deepcopy(source["work_items"][-1])
    item["sequence"] = 3
    item["work_item_id"] = "Fixture-03"
    source["work_items"].append(item)
    path, root = synthetic(source, tmp_path)
    output, _ = render(path, root)
    assert b"Fixture-03" in output


def test_read_only_check_and_explicit_render_output(tmp_path: Path) -> None:
    before = (GOLDEN.read_bytes(), PROFILE.read_bytes(), PROJECTION.read_bytes())
    check(GOLDEN, REPO, PROJECTION)
    assert before == (
        GOLDEN.read_bytes(),
        PROFILE.read_bytes(),
        PROJECTION.read_bytes(),
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            str(HERE / "renderer.py"),
            "render",
            "--profile",
            str(PROFILE),
            "--source",
            str(GOLDEN),
            "--repository-root",
            str(REPO),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2


CASES = load(HERE / "fixtures/negative/cases-v1.yaml")["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda v: v["case_id"])
def test_fail_closed(case: dict[str, str], tmp_path: Path) -> None:
    case_id = case["case_id"]
    source = phase_a() if case_id == "K0b_01_gate_inventory_mismatch" else load(GOLDEN)
    path, root = synthetic(source, tmp_path)
    doc = load(path)
    if case_id == "duplicate_YAML_keys":
        path.write_bytes(path.read_bytes() + b"state_id: duplicate\n")
    elif case_id == "unknown_top_level_field":
        doc["unknown"] = True
    elif case_id == "unknown_nested_record_field":
        doc["work_items"][0]["unknown"] = True
    elif case_id == "wrong_schema_version":
        doc["schema_version"] = 2
    elif case_id == "wrong_scalar_type":
        doc["schema_version"] = True
    elif case_id == "duplicate_work_item_id":
        doc["work_items"][1]["work_item_id"] = doc["work_items"][0]["work_item_id"]
    elif case_id == "duplicate_sequence":
        doc["work_items"][1]["sequence"] = doc["work_items"][0]["sequence"]
    elif case_id == "reordered_sequence":
        doc["work_items"].reverse()
    elif case_id == "duplicate_open_gate_id":
        doc["open_gates"].append(copy.deepcopy(doc["open_gates"][0]))
    elif case_id == "duplicate_closed_gate_id":
        doc["closed_gates"].append(copy.deepcopy(doc["closed_gates"][0]))
    elif case_id == "open_closed_gate_overlap":
        doc["closed_gates"][0]["gate_id"] = doc["open_gates"][0]["gate_id"]
    elif case_id == "missing_work_item_gate":
        doc["work_items"][0]["open_gate_ids"] = ["G-MISSING"]
    elif case_id == "K0b_01_gate_inventory_mismatch":
        next(w for w in doc["work_items"] if w["work_item_id"] == "K0b-01")[
            "open_gate_ids"
        ] = [doc["open_gates"][0]["gate_id"]]
    elif case_id == "invalid_gate_status":
        doc["open_gates"][0]["status"] = "closed"
    elif case_id == "malformed_SHA_scalar":
        doc["active_authority"]["fixture_profile"]["sha256"] = "invalid"
    elif case_id == "missing_reference_file":
        doc["active_authority"]["fixture_profile"]["path"] = (
            "new pipeline/contracts/k0b01/events/error.tool_failure-v1.schema.json"
        )
    elif case_id == "reference_hash_mismatch":
        doc["active_authority"]["fixture_profile"]["sha256"] = "f" * 64
    elif case_id == "absolute_or_escaping_reference_path":
        for index, bad in enumerate(
            ("C:/unapproved/file.yaml", "../escape.yaml", "new pipeline/unlisted.yaml")
        ):
            bad_doc = copy.deepcopy(doc)
            bad_doc["active_authority"]["fixture_profile"]["path"] = bad
            bad_path = tmp_path / (str(index) + ".yaml")
            write(bad_path, bad_doc)
            with pytest.raises(renderer.RendererError):
                render(bad_path, root)
        return
    elif case_id == "invalid_UTF8_BOM_CRLF_or_final_LF":
        data = path.read_bytes()
        for index, bad in enumerate(
            (
                b"\xff\n",
                b"\xef\xbb\xbf" + data,
                data.replace(b"\n", b"\r\n"),
                data[:-1],
                data + b"\n",
            )
        ):
            bad_path = tmp_path / (str(index) + ".yaml")
            bad_path.write_bytes(bad)
            with pytest.raises(renderer.RendererError):
                render(bad_path, root)
        return
    elif case_id == "projection_byte_or_embedded_source_mismatch":
        output, _ = render(path, root)
        bad = tmp_path / "bad.md"
        bad.write_bytes(output + b"extra claim\n")
        with pytest.raises(renderer.RendererError):
            check(path, root, bad)
        return
    else:
        raise AssertionError(case_id)
    if case_id != "duplicate_YAML_keys":
        write(path, doc)
    with pytest.raises(renderer.RendererError):
        render(path, root)
