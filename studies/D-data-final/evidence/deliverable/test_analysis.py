"""Tests: run with `python3 -m unittest` from the workspace."""
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "analysis.py")
RESULTS = os.path.join(HERE, "results.txt")
REPORT = os.path.join(HERE, "report.md")


def run_script(out):
    p = subprocess.run([sys.executable, SCRIPT, "--out", out],
                       capture_output=True, text=True, check=True)
    return p.stdout


class AnalysisTests(unittest.TestCase):
    def test_deterministic(self):
        scratch = os.path.join(HERE, "scratch")
        os.makedirs(scratch, exist_ok=True)
        a = run_script(os.path.join(scratch, "a.txt"))
        b = run_script(os.path.join(scratch, "b.txt"))
        self.assertEqual(a, b)
        with open(os.path.join(scratch, "a.txt"), encoding="utf-8") as f1, \
                open(os.path.join(scratch, "b.txt"), encoding="utf-8") as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_results_file_matches_stdout(self):
        out = run_script(RESULTS)
        with open(RESULTS, encoding="utf-8") as fh:
            self.assertEqual(out, fh.read())

    def test_report_figures_in_results(self):
        run_script(RESULTS)
        with open(RESULTS, encoding="utf-8") as fh:
            results = fh.read()
        with open(REPORT, encoding="utf-8") as fh:
            report = fh.read()
        result_tokens = set(re.findall(r"\d+(?:\.\d+)?%?", results))
        # Remove list numbering ("1. ") and the year/filename, which are not figures.
        body = re.sub(r"(?m)^\s*\d+\.\s", "", report)
        body = body.replace("orders_2025.csv", "").replace("2025", "")
        # Digits inside "100 and over" style labels are real figures from results.
        missing = []
        for tok in re.findall(r"\d+(?:\.\d+)?%?", body):
            if tok not in result_tokens:
                missing.append(tok)
        self.assertEqual(missing, [], "figures in report not in results: %s" % missing)

    def test_report_word_limit(self):
        with open(REPORT, encoding="utf-8") as fh:
            self.assertLessEqual(len(fh.read().split()), 1000)

    def test_key_numbers(self):
        run_script(RESULTS)
        with open(RESULTS, encoding="utf-8") as fh:
            results = fh.read()
        for needle in ["Overall return rate: 7.2%", "Home Textiles sold on marketplace",
                       "30.3%"]:
            self.assertIn(needle, results)


if __name__ == "__main__":
    unittest.main()
