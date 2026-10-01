import unittest

from fixture_support import attach_cases, load_cases, run_guard_case


class GuardCases(unittest.TestCase):
    pass


attach_cases(GuardCases, load_cases("guard-vectors-v1.json"), run_guard_case)


if __name__ == "__main__":
    unittest.main()
