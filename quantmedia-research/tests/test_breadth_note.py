"""Tests for breadth-history-note/summarize.py. The series grows nightly, so
these pin invariants and formulas, not the values of a particular day.
Run: python tests/test_breadth_note.py
"""
import os
import sys
from math import sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'breadth-history-note'))

import numpy as np  # noqa: E402
import summarize as X  # noqa: E402

passed = 0


def test(name, fn):
    global passed
    fn()
    passed += 1
    print('  [ ok ]', name)


def t_series_integrity():
    d, s = X.load()
    dates = [r['market_date'] for r in s]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    assert d['observations'] == len(s)
    for r in s:
        assert r['scored'] > 0 and 0 <= r['breadth_pct'] <= 100
        assert abs(r['breadth_pct'] - round(100 * r['buy_signals'] / r['scored'], 1)) < 0.051, r
        assert 0 <= r['median_score'] <= d['signal_count']
    assert 'not backfilled' in d['note']


def t_summary_consistent_with_series():
    d, s = X.load()
    out = X.summarize(d, s)
    b = [r['breadth_pct'] for r in s]
    assert out['breadth_min'] == min(b) and out['breadth_max'] == max(b)
    assert out['days_up'] + out['days_down'] + out['days_flat'] == len(s) - 1
    assert -1 <= out['lag1_autocorr'] <= 1
    assert abs(out['lag1_se_white_noise'] - 1 / sqrt(len(s))) < 1e-12


def t_formulas():
    # Lag-1 autocorrelation of a perfectly persistent and of an alternating series.
    assert abs(X.lag1_autocorr(np.array([1., 2, 3, 4, 5, 6])) - 0.5) < 1e-12
    assert X.lag1_autocorr(np.array([1., -1, 1, -1, 1, -1])) < -0.8
    # Fisher-z sample sizes for 80% power at two-sided 5%.
    assert X.n_for_correlation(0.3) == 85
    assert X.n_for_correlation(0.2) == 194
    assert X.n_for_correlation(0.1) == 783


def t_deterministic():
    d, s = X.load()
    assert X.summarize(d, s) == X.summarize(d, s)


if __name__ == '__main__':
    for name, fn in [('series is sorted, unique, internally consistent, not backfilled', t_series_integrity),
                     ('summary agrees with the series it was computed from', t_summary_consistent_with_series),
                     ('autocorrelation and Fisher-z sample-size formulas', t_formulas),
                     ('same inputs, same numbers', t_deterministic)]:
        test(name, fn)
    print(f'{passed} passed')
