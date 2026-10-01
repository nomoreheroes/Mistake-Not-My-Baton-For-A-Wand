import unittest

from fixture_support import attach_cases, load_cases, run_lifecycle_case


class LifecycleCases(unittest.TestCase):
    pass


attach_cases(LifecycleCases, load_cases("lifecycle-recovery-vectors-v1.json", "lifecycle"), run_lifecycle_case)


if __name__ == "__main__":
    unittest.main()
