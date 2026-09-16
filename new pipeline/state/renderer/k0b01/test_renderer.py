from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

import renderer


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[3]
PROFILE = HERE / "projection-profile-v2.yaml"
GOLDEN_SOURCE = HERE / "fixtures" / "golden" / "state-v1.yaml"
GOLDEN_PROJECTION = HERE / "fixtures" / "golden" / "STATE-v1.md"
NEGATIVE_CASES = HERE / "fixtures" / "negative" / "cases-v1.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, *, round_trip: bool = False) -> dict[str, Any]:
    yaml = YAML() if round_trip else YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    document = yaml.load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _write_yaml(path: Path, document: dict[str, Any]) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 4096
    stream = StringIO()
    yaml.dump(document, stream)
    text = stream.getvalue().replace("\r\n", "\n")
    assert text.endswith("\n") and not text.endswith("\n\n")
    path.write_text(text, encoding="utf-8", newline="\n")


def _render() -> tuple[bytes, dict[str, str]]:
    return renderer.render_bytes(
        source_path=GOLDEN_SOURCE,
        profile_path=PROFILE,
        repository_root=REPOSITORY_ROOT,
    )


def _cases() -> list[dict[str, str]]:
    document = _load(NEGATIVE_CASES)
    cases = document["cases"]
    assert isinstance(cases, list) and len(cases) == 20
    return cases


def test_profile_contract_loads() -> None:
    profile, digest = renderer.load_profile(PROFILE)
    assert profile["projection_version"] == "2.0.0"
    assert len(profile["source_contract"]["allowed_shape_sha256"]) == 3
    assert digest == _sha256(PROFILE)


def test_golden_render_matches() -> None:
    output, _ = _render()
    assert output == GOLDEN_PROJECTION.read_bytes()


def test_golden_check_passes() -> None:
    summary = renderer.check_projection(
        source_path=GOLDEN_SOURCE,
        profile_path=PROFILE,
        projection_path=GOLDEN_PROJECTION,
        repository_root=REPOSITORY_ROOT,
    )
    assert summary["projection_sha256"] == _sha256(GOLDEN_PROJECTION)


def test_repeated_render_is_byte_identical() -> None:
    first, first_summary = _render()
    second, second_summary = _render()
    assert first == second
    assert first_summary == second_summary


def test_render_does_not_mutate_source() -> None:
    before = _sha256(GOLDEN_SOURCE)
    _render()
    assert _sha256(GOLDEN_SOURCE) == before


def test_check_does_not_mutate_inputs() -> None:
    before = (_sha256(GOLDEN_SOURCE), _sha256(GOLDEN_PROJECTION), _sha256(PROFILE))
    renderer.check_projection(
        source_path=GOLDEN_SOURCE,
        profile_path=PROFILE,
        projection_path=GOLDEN_PROJECTION,
        repository_root=REPOSITORY_ROOT,
    )
    after = (_sha256(GOLDEN_SOURCE), _sha256(GOLDEN_PROJECTION), _sha256(PROFILE))
    assert after == before


def test_render_byte_profile() -> None:
    output, _ = _render()
    assert not output.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in output
    assert output.endswith(b"\n") and not output.endswith(b"\n\n")


def test_semantic_body_round_trip() -> None:
    output, summary = _render()
    source_text = GOLDEN_SOURCE.read_text(encoding="utf-8")
    assert source_text.encode("utf-8") in output
    assert summary["source_sha256"] == _sha256(GOLDEN_SOURCE)


def test_cli_render(tmp_path: Path) -> None:
    output = tmp_path / "rendered.md"
    result = _run_cli(
        "render",
        "--output",
        str(output),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["result"] == "pass"
    assert output.read_bytes() == GOLDEN_PROJECTION.read_bytes()


def test_cli_check() -> None:
    result = _run_cli(
        "check",
        "--projection",
        str(GOLDEN_PROJECTION),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["result"] == "pass"


def _run_cli(command: str, *extra: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            str(HERE / "renderer.py"),
            command,
            "--profile",
            str(PROFILE),
            "--source",
            str(GOLDEN_SOURCE),
            "--repository-root",
            str(REPOSITORY_ROOT),
            *extra,
        ],
        check=False,
        capture_output=True,
        cwd=HERE,
        env=environment,
        text=True,
    )


def _mutated_profile(case_id: str, path: Path) -> None:
    document = _load(PROFILE, round_trip=True)
    if case_id == "unsupported-profile-schema":
        document["schema_version"] = 2
    elif case_id == "unknown-profile-field":
        document["unexpected"] = True
    else:
        raise AssertionError(case_id)
    _write_yaml(path, document)


def _mutated_source(case_id: str, path: Path) -> None:
    document = _load(GOLDEN_SOURCE, round_trip=True)
    if case_id == "unsupported-source-schema":
        document["schema_version"] = 2
    elif case_id == "unknown-source-field":
        document["unexpected"] = True
    elif case_id == "missing-source-field":
        document.pop("status")
    elif case_id == "duplicate-work-item-id":
        document["work_items"][1]["work_item_id"] = document["work_items"][0][
            "work_item_id"
        ]
    elif case_id == "unsorted-work-item-sequence":
        document["work_items"].reverse()
    elif case_id == "duplicate-open-gate-id":
        document["open_gates"].append(copy.deepcopy(document["open_gates"][0]))
    elif case_id == "open-closed-gate-overlap":
        document["closed_gates"][0]["gate_id"] = document["open_gates"][0]["gate_id"]
    elif case_id == "work-item-missing-global-gate":
        document["work_items"][0]["open_gate_ids"] = ["G-MISSING"]
    elif case_id == "invalid-open-gate-status":
        document["open_gates"][0]["status"] = "invalid"
    elif case_id == "invalid-closed-gate-status":
        document["closed_gates"][0]["status"] = "open"
    elif case_id == "broken-repository-reference":
        document["active_authority"]["fixture_profile"]["path"] = (
            "new pipeline/state/renderer/k0b01/missing.yaml"
        )
    elif case_id == "repository-reference-hash-mismatch":
        document["active_authority"]["fixture_profile"]["sha256"] = "f" * 64
    elif case_id == "unknown-work-item-field":
        document["work_items"][0]["unexpected"] = True
    elif case_id == "missing-work-item-field":
        document["work_items"][0].pop("authority_sha256")
    elif case_id == "source-only-change":
        document["status"] = "fixture_only_changed_but_structurally_valid"
    else:
        raise AssertionError(case_id)
    _write_yaml(path, document)


def _mutated_projection(case_id: str, path: Path) -> None:
    data = GOLDEN_PROJECTION.read_bytes()
    if case_id == "projection-only-change":
        data = data.replace(b"Fixture-02", b"Fixture-X2", 1)
    elif case_id == "extra-normative-claim":
        data = data[:-4] + b"extra normative claim\n```\n"
    elif case_id == "malformed-projection-fence":
        data = data[:-4] + b"``x\n"
    else:
        raise AssertionError(case_id)
    path.write_bytes(data)


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["case_id"])
def test_fail_closed_cases(case: dict[str, str], tmp_path: Path) -> None:
    case_id = case["case_id"]
    group = case["group"]
    expected = case["expected_error"]
    source = GOLDEN_SOURCE
    profile = PROFILE
    projection = GOLDEN_PROJECTION

    if group == "profile":
        profile = tmp_path / "profile.yaml"
        _mutated_profile(case_id, profile)
    elif group == "source":
        source = tmp_path / "state.yaml"
        _mutated_source(case_id, source)
    elif group == "projection":
        if case_id == "source-only-change":
            source = tmp_path / "state.yaml"
            _mutated_source(case_id, source)
        else:
            projection = tmp_path / "STATE.md"
            _mutated_projection(case_id, projection)
    else:
        raise AssertionError(group)

    with pytest.raises(renderer.RendererError, match=f"^{re.escape(expected)}$"):
        if group == "projection":
            renderer.check_projection(
                source_path=source,
                profile_path=profile,
                projection_path=projection,
                repository_root=REPOSITORY_ROOT,
            )
        else:
            renderer.render_bytes(
                source_path=source,
                profile_path=profile,
                repository_root=REPOSITORY_ROOT,
            )
