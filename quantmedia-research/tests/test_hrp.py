"""
Tests for the HRP implementation.

    cd quantmedia-research && python tests/test_hrp.py
"""

from __future__ import annotations

import os
import sys
import traceback

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'hierarchical-risk-parity'))

from hrp import (correlation_distance, hrp_weights, inverse_variance_weights,  # noqa: E402
                 min_variance_weights, portfolio_stats, quasi_diagonalise,
                 recursive_bisection)

PASSED, FAILED = [], []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f'  [ ok ] {name}')
    except Exception as e:
        FAILED.append((name, str(e)))
        print(f'  [FAIL] {name}\n         {e}')
        if not isinstance(e, AssertionError):
            print(traceback.format_exc(limit=2))


def panel(n_assets=8, n_periods=300, seed=1):
    """Small block-correlated panel."""
    rng = np.random.default_rng(seed)
    f1 = rng.normal(0, 0.01, n_periods)
    f2 = rng.normal(0, 0.01, n_periods)
    cols, data = [], []
    for i in range(n_assets):
        f = f1 if i < n_assets // 2 else f2
        data.append(f * rng.uniform(0.8, 1.2)
                    + rng.normal(0, rng.uniform(0.005, 0.015), n_periods))
        cols.append(f'A{i}')
    return pd.DataFrame(np.array(data).T, columns=cols)


# ---------------------------------------------------------------------------
def test_weights_sum_to_one():
    w = hrp_weights(panel())
    assert abs(w.sum() - 1.0) < 1e-9, f'sum={w.sum()}'


def test_no_negative_weights():
    """HRP as specified is long-only: recursive bisection multiplies positive
    fractions, so a negative weight means the allocation logic broke."""
    for seed in range(6):
        w = hrp_weights(panel(seed=seed))
        assert (w >= 0).all(), f'seed {seed}: negative weight\n{w[w < 0]}'


def test_all_assets_receive_weight():
    w = hrp_weights(panel(n_assets=10))
    assert len(w) == 10 and w.index.tolist() == [f'A{i}' for i in range(10)]
    assert (w > 0).all(), 'every asset should get a positive allocation'


def test_deterministic():
    p = panel(seed=99)
    pd.testing.assert_series_equal(hrp_weights(p), hrp_weights(p))


def test_known_two_asset_result():
    """With two uncorrelated assets, recursive bisection reduces to inverse
    variance. Asset B has 4x the variance (2x the sd), so it should receive
    1/4 the weight: 0.8 / 0.2."""
    rng = np.random.default_rng(5)
    n = 20000
    df = pd.DataFrame({'A': rng.normal(0, 0.01, n),
                       'B': rng.normal(0, 0.02, n)})
    w = hrp_weights(df)
    assert abs(w['A'] - 0.8) < 0.02, f"A={w['A']:.4f}, expected ~0.80"
    assert abs(w['B'] - 0.2) < 0.02, f"B={w['B']:.4f}, expected ~0.20"


def test_correlation_distance_properties():
    p = panel()
    d = correlation_distance(p.corr())
    assert np.allclose(np.diag(d.values), 0.0), 'diagonal must be zero'
    assert np.allclose(d.values, d.values.T), 'must be symmetric'
    assert (d.values >= -1e-12).all() and (d.values <= 1 + 1e-12).all(), \
        'distance must lie in [0,1]'
    # Perfectly correlated -> distance 0
    same = pd.DataFrame({'X': [1.0, 2, 3, 4], 'Y': [2.0, 4, 6, 8]})
    assert correlation_distance(same.corr()).loc['X', 'Y'] < 1e-9


def test_inverse_variance_weights():
    cov = pd.DataFrame(np.diag([0.01, 0.04]), index=['A', 'B'],
                       columns=['A', 'B'])
    w = inverse_variance_weights(cov)
    assert abs(w[0] - 0.8) < 1e-9 and abs(w[1] - 0.2) < 1e-9, w


def test_quasi_diagonalisation_returns_permutation():
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform
    p = panel(n_assets=8)
    d = correlation_distance(p.corr())
    order = quasi_diagonalise(linkage(squareform(d.values, checks=False),
                                      method='single'))
    assert sorted(order) == list(range(8)), \
        f'must be a permutation of all leaves, got {sorted(order)}'


def test_recursive_bisection_splits_risk():
    """The higher-variance branch must receive less weight."""
    cov = pd.DataFrame(np.diag([0.0001, 0.0001, 0.01, 0.01]),
                       index=list('ABCD'), columns=list('ABCD'))
    w = recursive_bisection(cov, list('ABCD'))
    assert abs(w.sum() - 1.0) < 1e-9
    assert w['A'] + w['B'] > w['C'] + w['D'], \
        'low-variance pair should get the larger allocation'


def test_rejects_bad_input():
    try:
        hrp_weights(pd.DataFrame({'A': [0.1, 0.2]}))
    except ValueError:
        pass
    else:
        raise AssertionError('single asset should raise')

    bad = panel()
    bad.iloc[0, 0] = np.nan
    try:
        hrp_weights(bad)
    except ValueError:
        return
    raise AssertionError('NaN input should raise')


def test_linkage_method_changes_weights():
    """The linkage method is a real modelling choice, not a detail - the README
    says so, and this pins it.

    Note the two methods DO coincide on some panels (a clean, well-separated
    two-block structure can produce the same tree either way). Seed 2 at 10
    assets is one where they diverge by ~8 percentage points on a single
    weight, which is the point being demonstrated.
    """
    p = panel(n_assets=10, seed=2)
    a, b = hrp_weights(p, method='single'), hrp_weights(p, method='ward')
    gap = np.abs(a.values - b.values).max()
    assert gap > 0.01, (
        f'expected the linkage choice to move weights on this panel, '
        f'max difference was only {gap:.6f}')
    # Both must still be valid allocations.
    for w in (a, b):
        assert abs(w.sum() - 1.0) < 1e-9 and (w >= 0).all()


def test_minvar_baseline_runs():
    p = panel()
    w = min_variance_weights(p)
    assert abs(w.sum() - 1.0) < 1e-9
    wl = min_variance_weights(p, long_only=True)
    assert (wl >= -1e-12).all() and abs(wl.sum() - 1.0) < 1e-9


def test_portfolio_stats_shape():
    p = panel()
    s = portfolio_stats(hrp_weights(p), p)
    for k in ('annual_return', 'annual_vol', 'sharpe', 'max_drawdown',
              'max_weight', 'n_effective', 'herfindahl'):
        assert k in s, f'missing {k}'
    assert s['annual_vol'] > 0
    assert s['max_drawdown'] <= 0
    assert 1 <= s['n_effective'] <= len(p.columns) + 1e-9


def main():
    print('=' * 62)
    print('HRP implementation tests')
    print('=' * 62)
    for name, fn in [
        ('weights sum to 1',              test_weights_sum_to_one),
        ('no negative weights',           test_no_negative_weights),
        ('all assets allocated',          test_all_assets_receive_weight),
        ('deterministic',                 test_deterministic),
        ('known 2-asset result (80/20)',  test_known_two_asset_result),
        ('correlation distance metric',   test_correlation_distance_properties),
        ('inverse variance weights',      test_inverse_variance_weights),
        ('quasi-diagonalisation perm',    test_quasi_diagonalisation_returns_permutation),
        ('recursive bisection splits',    test_recursive_bisection_splits_risk),
        ('rejects bad input',             test_rejects_bad_input),
        ('linkage method matters',        test_linkage_method_changes_weights),
        ('minvar baseline runs',          test_minvar_baseline_runs),
        ('portfolio stats shape',         test_portfolio_stats_shape),
    ]:
        check(name, fn)
    print(f'\n{len(PASSED)} passed, {len(FAILED)} failed')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
