"""Tests for dsr-trials/experiment.py.
Run: python tests/test_dsr_trials.py   (about 45 s: Monte Carlo parts run at
reduced size here)
"""
import os
import sys
from math import sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'dsr-trials'))

import numpy as np  # noqa: E402
import experiment as X  # noqa: E402

X.REPS = 800   # smaller Monte Carlo for the test run; tolerances are set for it
passed = 0


def test(name, fn):
    global passed
    fn()
    passed += 1
    print('  [ ok ]', name)


def t_explainer_table():
    a = X.part_a()
    assert abs(a['denominator'] - 2.2389) < 5e-4
    rows = {r['N']: r for r in a['rows']}
    for N, em, d in ((10, 0.7873, 0.9997), (100, 1.2653, 0.8736), (1000, 1.6276, 0.2671)):
        assert abs(rows[N]['expected_max_sr'] - em) < 5e-4, (N, rows[N])
        assert abs(rows[N]['dsr'] - d) < 5e-4, (N, rows[N])
    assert rows[1]['expected_max_sr'] == 0.0 and abs(rows[1]['dsr'] - a['psr_zero']) < 1e-12


def t_closed_form_matches_monte_carlo():
    b = X.part_b(np.random.default_rng(3))
    for r in b:
        assert abs(r['max_sr_mc'] - r['max_sr_formula']) < 0.02, r
        assert abs(r['sd_sr_across_trials'] - sqrt(1 / X.N_PERIODS)) < 0.01, r


def t_false_positives_and_power():
    c = {r['N']: r for r in X.part_c(np.random.default_rng(5))}
    assert abs(c[1]['naive_psr_fp'] - 0.05) < 0.03            # a single trial: nominal size
    assert c[100]['naive_psr_fp'] > 0.9 and c[1000]['naive_psr_fp'] > 0.95
    assert all(c[N]['dsr_fp'] < 0.03 for N in (10, 100, 1000))
    assert c[10]['dsr_power'] < c[10]['naive_psr_power']       # the price of the correction
    assert c[1]['edge_picked'] == 1.0


def t_correlated_trials():
    d = X.part_d(np.random.default_rng(9))
    sds = [r['sd_sr_across_trials'] for r in d]
    assert sds == sorted(sds, reverse=True)                     # more correlation, less spread
    for r in d:
        assert abs(r['max_sr_mc'] - r['max_sr_formula_nominalN']) < 0.02, r
        assert 60 < r['n_effective'] < 160, r


def t_deterministic():
    assert X.part_b(np.random.default_rng(1)) == X.part_b(np.random.default_rng(1))


if __name__ == '__main__':
    for name, fn in [('explainer table reproduces to four decimals', t_explainer_table),
                     ('closed-form E[max SR] matches Monte Carlo under the null', t_closed_form_matches_monte_carlo),
                     ('naive PSR false positives explode with N; DSR stays small; power drops', t_false_positives_and_power),
                     ('correlated trials: sd(SR) shrinks and the formula still matches', t_correlated_trials),
                     ('same seed, same numbers', t_deterministic)]:
        test(name, fn)
    print(f'{passed} passed')
