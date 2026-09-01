from __future__ import annotations

from pathlib import Path
import sys
import unittest


PIPELINE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_DIR))

from harness.k0a03 import PINNED_EXECUTORS, load_execution_profile  # noqa: E402
from harness.k0a03.cli import _parser  # noqa: E402


class K0a03ProfileAndCliTests(unittest.TestCase):
    def test_profile_pins_both_extensions_without_role_partition(self) -> None:
        profile = load_execution_profile()
        self.assertEqual(PINNED_EXECUTORS, ("chatgpt_gpt_5_6_sol", "claude_opus_4_6"))
        for key in PINNED_EXECUTORS:
            executor = profile.executor(key)
            self.assertTrue(executor.extension_id)
            self.assertTrue(executor.model_identifier)
        self.assertEqual(profile.physical_invocation_budget, {"nominal": 3, "worst_case": 6})

    def test_cli_has_only_fixed_commands_and_no_free_options(self) -> None:
        parser = _parser()
        for command in ("initialize", "run", "inspect"):
            self.assertEqual(parser.parse_args([command]).command, command)
        for arguments in (
            [],
            ["submit"],
            ["run", "--provider", "foreign"],
            ["run", "--model", "foreign"],
            ["run", "--tools", "shell"],
            ["inspect", "--sql", "select 1"],
            ["initialize", "C:/foreign"],
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
