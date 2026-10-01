import unittest

from fixture_support import attach_cases, load_cases, run_detector_case


class ScannerCases(unittest.TestCase):
    pass


attach_cases(ScannerCases, load_cases("detector-vector-recipes-v1.json"), run_detector_case)


if __name__ == "__main__":
    unittest.main()
