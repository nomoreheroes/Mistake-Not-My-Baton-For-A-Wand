import unittest

from fixture_support import attach_cases, load_cases, run_compiler_case


class ToolchainCases(unittest.TestCase):
    pass


attach_cases(ToolchainCases, load_cases("lifecycle-recovery-vectors-v1.json", "compiler")[6:8], run_compiler_case)


if __name__ == "__main__":
    unittest.main()
