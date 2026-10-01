import unittest

from fixture_support import attach_cases, load_cases, run_compiler_case


class ContractCases(unittest.TestCase):
    pass


attach_cases(ContractCases, load_cases("lifecycle-recovery-vectors-v1.json", "compiler")[:4], run_compiler_case)


if __name__ == "__main__":
    unittest.main()
