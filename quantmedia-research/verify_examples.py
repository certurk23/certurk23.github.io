"""Re-run both examples in isolation and compare all shipped CSV output.

Run from any directory: python quantmedia-research/verify_examples.py
The source tree and its sample files are never modified by this check.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parent


class ReproductionTests(unittest.TestCase):
    def reproduce(self, package, entry, files):
        with tempfile.TemporaryDirectory(prefix='qm-example-') as temp:
            target = Path(temp) / package
            shutil.copytree(ROOT / package, target,
                            ignore=shutil.ignore_patterns('__pycache__'))
            # Also works with embedded Python distributions without cwd on sys.path.
            result = subprocess.run(
                [sys.executable, '-B', '-c',
                 'import os,runpy,sys;sys.path.insert(0,os.getcwd());'
                 'runpy.run_path(sys.argv[1],run_name="__main__")', entry],
                cwd=target, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout)
            for file in files:
                expected = pd.read_csv(ROOT / package / file)
                actual = pd.read_csv(target / file)
                with self.subTest(output=file):
                    pd.testing.assert_frame_equal(
                        actual, expected, check_exact=False, rtol=1e-9, atol=1e-9)

    def test_vpin_matches_published_output(self):
        self.reproduce('vpin-order-flow-toxicity', 'example.py',
                       ['outputs/example_output.csv', 'sample_data/sample_trades.csv'])

    def test_hrp_matches_published_output(self):
        self.reproduce('hierarchical-risk-parity', 'compare_mvo.py',
                       ['outputs/comparison.csv', 'outputs/weights.csv', 'sample_returns.csv'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
