from __future__ import annotations

import ast
import base64
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


PIPELINE_ROOT = Path(__file__).resolve().parents[2]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from harness.governance import canonical_yaml  # noqa: E402
from harness.governance.canonical_yaml import (  # noqa: E402
    CanonicalYamlError,
    calculate_canonical_payload_sha256,
    canonicalize_validated_value,
    parse_validate_and_normalize_yaml_bytes,
    verify_declared_canonical_payload_sha256,
)


VECTOR_PATH = Path(__file__).with_name("canonical_yaml_v1_vectors.json")
FORBIDDEN_IMPORT_ROOTS = {
    "http",
    "requests",
    "socket",
    "sqlite3",
    "subprocess",
    "urllib",
}
FORBIDDEN_WRITE_CALLS = {
    "open",
    "write",
    "write_bytes",
    "write_text",
    "touch",
    "mkdir",
    "rename",
    "unlink",
}


class CanonicalYamlV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vector_document = json.loads(VECTOR_PATH.read_text(encoding="utf-8"))
        cls.vectors = cls.vector_document["vectors"]

    def test_vector_schema_and_oracle_separation(self) -> None:
        self.assertEqual(self.vector_document["profile_id"], "canonical-yaml-v1")
        self.assertEqual(self.vector_document["vector_schema_version"], 1)
        self.assertEqual(
            self.vector_document["oracle"],
            "fixed_test_only_values_not_generated_by_production_verifier",
        )
        self.assertEqual(len(self.vectors), 27)
        self.assertEqual(len({item["vector_id"] for item in self.vectors}), 27)
        source = Path(canonical_yaml.__file__).read_text(encoding="utf-8")
        self.assertNotIn(VECTOR_PATH.name, source)
        for vector in self.vectors:
            expected_hash = vector["expected_SHA_256_or_null"]
            if expected_hash is not None:
                self.assertNotIn(expected_hash, source)

    def test_all_fixed_vectors(self) -> None:
        positive = 0
        negative = 0
        for vector in self.vectors:
            with self.subTest(vector=vector["vector_id"]):
                data = base64.b64decode(
                    vector["input_UTF_8_bytes_as_base64"], validate=True
                )
                error_code = vector["expected_error_code_or_null"]
                if error_code is not None:
                    negative += 1
                    with self.assertRaises(CanonicalYamlError) as raised:
                        calculate_canonical_payload_sha256(
                            data, vector["excluded_field_path"]
                        )
                    self.assertEqual(raised.exception.code, error_code)
                    self.assertIsNone(
                        vector["expected_canonical_UTF_8_bytes_as_base64_or_null"]
                    )
                    self.assertIsNone(vector["expected_SHA_256_or_null"])
                    continue

                positive += 1
                normalized = parse_validate_and_normalize_yaml_bytes(
                    data, vector["excluded_field_path"]
                )
                canonical = canonicalize_validated_value(normalized)
                expected_canonical = base64.b64decode(
                    vector["expected_canonical_UTF_8_bytes_as_base64_or_null"],
                    validate=True,
                )
                self.assertEqual(canonical, expected_canonical)
                self.assertEqual(
                    sha256(canonical).hexdigest(),
                    vector["expected_SHA_256_or_null"],
                )
                self.assertEqual(
                    calculate_canonical_payload_sha256(
                        data, vector["excluded_field_path"]
                    ),
                    vector["expected_SHA_256_or_null"],
                )
        self.assertEqual(positive, 8)
        self.assertEqual(negative, 19)

    def test_equivalent_block_flow_and_newline_inputs_have_same_hash(self) -> None:
        by_id = {item["vector_id"]: item for item in self.vectors}
        self.assertEqual(
            by_id["map_order_block"]["expected_SHA_256_or_null"],
            by_id["map_order_flow"]["expected_SHA_256_or_null"],
        )

    def test_direct_value_validation_is_non_mutating(self) -> None:
        original = {"e\u0301": ["A\u030a", -0.0, True, None]}
        canonical = canonicalize_validated_value(original)
        self.assertEqual(canonical, '{"é":["Å",0,true,null]}'.encode())
        self.assertEqual(original, {"e\u0301": ["A\u030a", -0.0, True, None]})

    def test_quoted_merge_spelling_is_a_plain_string_key(self) -> None:
        data = ('"<<": value\nreceipt_sha256: "' + ("0" * 64) + '"\n').encode()
        normalized = parse_validate_and_normalize_yaml_bytes(data, "receipt_sha256")
        self.assertEqual(canonicalize_validated_value(normalized), b'{"<<":"value"}')

    def test_direct_value_fail_closed_errors(self) -> None:
        cases = [
            ({"bad": float("nan")}, "NON_FINITE_NUMBER"),
            ({"bad": 9_007_199_254_740_992}, "INTEGER_RANGE"),
            ({1: "bad"}, "NON_STRING_KEY"),
            ({"bad": ("tuple",)}, "NON_JSON_VALUE"),
            ({"bad": "\ud800"}, "UNICODE_SURROGATE"),
            ({"é": 1, "e\u0301": 2}, "NORMALIZED_KEY_COLLISION"),
        ]
        for value, error_code in cases:
            with self.subTest(error_code=error_code):
                with self.assertRaises(CanonicalYamlError) as raised:
                    canonicalize_validated_value(value)
                self.assertEqual(raised.exception.code, error_code)

    def test_declared_hash_verification_and_format(self) -> None:
        vector = self.vectors[0]
        data = base64.b64decode(vector["input_UTF_8_bytes_as_base64"])
        expected = vector["expected_SHA_256_or_null"]
        matching = verify_declared_canonical_payload_sha256(
            data, vector["excluded_field_path"], expected
        )
        self.assertTrue(matching.matches)
        self.assertEqual(matching.computed_sha256, expected)
        mismatch = verify_declared_canonical_payload_sha256(
            data, vector["excluded_field_path"], "f" * 64
        )
        self.assertFalse(mismatch.matches)
        with self.assertRaises(CanonicalYamlError) as raised:
            verify_declared_canonical_payload_sha256(
                data, vector["excluded_field_path"], "A" * 64
            )
        self.assertEqual(raised.exception.code, "DECLARED_HASH_FORMAT")

    def test_cli_match_mismatch_and_validation_error(self) -> None:
        vector = self.vectors[0]
        data = base64.b64decode(vector["input_UTF_8_bytes_as_base64"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "input.yaml")
            path.write_bytes(data)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = canonical_yaml.main(
                    [
                        str(path),
                        "--exclude",
                        vector["excluded_field_path"],
                        "--expected",
                        vector["expected_SHA_256_or_null"],
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["matches"])
            self.assertEqual(payload["profile"], "canonical-yaml-v1")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = canonical_yaml.main(
                    [
                        str(path),
                        "--exclude",
                        vector["excluded_field_path"],
                        "--expected",
                        "f" * 64,
                    ]
                )
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(stdout.getvalue())["matches"])

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = canonical_yaml.main(
                    [
                        str(path),
                        "--exclude",
                        "bad..path",
                        "--expected",
                        vector["expected_SHA_256_or_null"],
                    ]
                )
            self.assertEqual(code, 2)
            self.assertEqual(
                json.loads(stderr.getvalue())["error_code"], "EXCLUDED_PATH_SYNTAX"
            )

    def test_toolchain_versions_are_exact(self) -> None:
        self.assertEqual(sys.version_info[:3], (3, 12, 7))
        self.assertEqual(importlib.metadata.version("ruamel.yaml"), "0.18.6")
        self.assertEqual(importlib.metadata.version("ruamel.yaml.clib"), "0.2.8")

    def test_production_module_has_no_forbidden_capability(self) -> None:
        source = Path(canonical_yaml.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        called_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_names.add(node.func.attr)
        self.assertFalse(imported_roots & FORBIDDEN_IMPORT_ROOTS)
        self.assertFalse(called_names & FORBIDDEN_WRITE_CALLS)


if __name__ == "__main__":
    unittest.main()
