"""Tests for degenerate-inputs/experiment.py: the cases whose answer is settled.
Run: python tests/test_degenerate_inputs.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'degenerate-inputs'))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import experiment as X  # noqa: E402

passed = 0


def test(name, fn):
    global passed
    fn()
    passed += 1
    print('  [ ok ]', name)


def t_monotone_tapes_read_one():
    n = 2000
    for prices in (100 + 0.01 * np.arange(n), 120 - 0.01 * np.arange(n)):
        for method in ('bvc', 'tick'):
            m, nb = X.vpin_mean(X.tape(prices), 2000.0, 10, method)
            assert m > 0.99, (method, m)


def t_flat_tape_reads_zero_both_ways():
    flat = X.tape(np.full(2000, 100.0))
    for method in ('bvc', 'tick'):
        m, _ = X.vpin_mean(flat, 2000.0, 10, method)
        assert abs(m) < 1e-12, (method, m)


def t_window_and_volume_edges():
    rng = np.random.default_rng(1)
    rw = X.tape(100 + np.cumsum(rng.normal(0, 0.01, 100)))
    m, nb = X.vpin_mean(rw, 2000.0, 10, 'bvc')          # 5 buckets < window 10
    assert np.isnan(m) and nb == 5
    try:
        X.vpin_mean(rw.iloc[:15], 2000.0, 10, 'bvc')      # 1,500 volume < one bucket
        raise AssertionError('should have raised')
    except ValueError:
        pass
    m, nb = X.vpin_mean(X.tape([100, 101, 102], [100, 5000, 100]), 1000.0, 1, 'tick')
    assert nb == 5                                        # one giant trade split over five buckets


def t_hrp_refusals_and_invariances():
    rng = np.random.default_rng(2)
    f = rng.normal(0, 0.01, 250)
    base = pd.DataFrame({'A': f + rng.normal(0, 0.005, 250), 'B': -f + rng.normal(0, 0.005, 250),
                         'C': rng.normal(0, 0.02, 250), 'D': rng.normal(0, 0.008, 250)})
    for bad in (base[['A']], base.assign(Z=0.0)):
        try:
            X.H.hrp_weights(bad); raise AssertionError('should have raised')
        except ValueError as e:
            assert 'assets' in str(e) or 'zero-variance' in str(e), str(e)
    with_nan = base.copy(); with_nan.iloc[10, 0] = np.nan
    try:
        X.H.hrp_weights(with_nan); raise AssertionError('should have raised')
    except ValueError as e:
        assert 'NaN' in str(e)
    w = X.H.hrp_weights(pd.DataFrame({'A': base['A'], 'A2': base['A']}))
    assert abs(w['A'] - 0.5) < 1e-9 and abs(w['A2'] - 0.5) < 1e-9
    w1, w2 = X.H.hrp_weights(base), X.H.hrp_weights(base + 1.0)
    assert np.allclose(w1.to_numpy(), w2.to_numpy())      # shift-invariant
    assert abs(w1.sum() - 1) < 1e-9 and (w1 >= 0).all()
    rank1 = pd.DataFrame({f'X{i}': (0.5 + 0.25 * i) * f for i in range(4)})
    w = X.H.hrp_weights(rank1)
    assert abs(w.sum() - 1) < 1e-9 and np.isfinite(w).all()


def t_psr_edges():
    assert X.psr(1.0, 1.0, 24, 0.0, 3.0) == 0.5
    assert abs(X.psr(1.5, 0.0, 2, 0.0, 3.0) - 0.8483) < 5e-4
    assert np.isnan(X.psr(1.5, 0.0, 24, 3.0, 3.0))
    assert abs(X.psr(-0.5, 0.0, 24, 0.0, 3.0) + X.psr(0.5, 0.0, 24, 0.0, 3.0) - 1.0) < 1e-12


if __name__ == '__main__':
    for name, fn in [('monotone tapes read VPIN ~ 1 under both classifiers', t_monotone_tapes_read_one),
                     ('a flat tape reads VPIN 0 under both classifiers', t_flat_tape_reads_zero_both_ways),
                     ('window longer than the tape gives NaN; sub-bucket volume is refused; giant trades split', t_window_and_volume_edges),
                     ('HRP refuses one asset, NaN and zero variance; identical assets split 0.5; shift-invariant', t_hrp_refusals_and_invariances),
                     ('PSR closed-form edges: equality 0.5, n = 2, non-positive variance NaN, sign symmetry', t_psr_edges)]:
        test(name, fn)
    print(f'{passed} passed')
