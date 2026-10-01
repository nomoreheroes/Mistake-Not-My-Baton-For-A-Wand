import unittest

from fixture_support import attach_cases, load_cases, run_compatibility_case


class CompatibilityCases(unittest.TestCase):
    pass


attach_cases(CompatibilityCases, load_cases("lifecycle-recovery-vectors-v1.json", "compatibility"), run_compatibility_case)


if __name__ == "__main__":
    unittest.main()
