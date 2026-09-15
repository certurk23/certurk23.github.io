"""Tests for hrp-drift-anatomy/experiment.py.
Run: python tests/test_hrp_drift.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'hrp-drift-anatomy'))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import experiment as X  # noqa: E402

passed = 0


def test(name, fn):
    global passed
    fn()
    passed += 1
    print('  [ ok ]', name)


def t_replica_panel_is_identical():
    panel, cov = X.make_panel_with_truth(520, X.SEED)
    ref = X.CM.make_synthetic_returns()
    assert panel.shape == ref.shape and list(panel.columns) == list(ref.columns)
    assert np.allclose(panel.to_numpy(), ref.to_numpy())
    # The true covariance is symmetric positive definite and its diagonal
    # matches the sample variance to within sampling error.
    c = cov.to_numpy()
    assert np.allclose(c, c.T) and np.linalg.eigvalsh(c).min() > 0
    ratio = panel.var().to_numpy() / np.diag(c)
    assert 0.7 < ratio.min() and ratio.max() < 1.3, ratio


def t_reproduces_published_numbers():
    rows, oracle, extra = X.part_a()
    r = {x['allocator']: x for x in rows}
    assert abs(r['HRP (single)']['vol_in'] - 0.1401) < 5e-4 and abs(r['HRP (single)']['vol_out'] - 0.1419) < 5e-4
    assert abs(r['MinVar']['vol_in'] - 0.1311) < 5e-4 and abs(r['MinVar']['vol_out'] - 0.1489) < 5e-4
    assert abs(r['HRP (single)']['drift_pct'] - 1.3) < 0.1 and abs(r['MinVar']['drift_pct'] - 13.6) < 0.1
    # Decomposition identity: (1 + optimism)(1 + luck) = 1 + drift.
    for x in rows:
        lhs = (1 + x['optimism_pct'] / 100) * (1 + x['luck_pct'] / 100)
        assert abs(lhs - (1 + x['drift_pct'] / 100)) < 1e-9
    # MinVar's drift is optimism; HRP's optimism is small.
    assert r['MinVar']['optimism_pct'] > 12 and abs(r['MinVar']['luck_pct']) < 1
    assert r['HRP (single)']['optimism_pct'] < 4
    # The oracle (true covariance) has lower true vol than every sample allocator.
    assert all(oracle['vol_true'] < x['vol_true'] for x in rows)


def t_optimism_falls_with_training_length():
    b = pd.DataFrame(X.part_b())
    mv = b[b.allocator == 'MinVar'].set_index('train_len')
    assert mv.loc[60, 'optimism_pct'] > 30 and mv.loc[2000, 'optimism_pct'] < 5
    assert mv.loc[60, 'dist_to_oracle'] > mv.loc[500, 'dist_to_oracle'] > mv.loc[2000, 'dist_to_oracle']


def t_seeds():
    c = pd.DataFrame(X.part_c())
    med = c.groupby('allocator')['drift_pct'].median()
    assert med['HRP (single)'] < 5 and med['MinVar'] > 15
    hrp = c[c.allocator == 'HRP (single)'].set_index('seed'); mv = c[c.allocator == 'MinVar'].set_index('seed')
    assert (hrp['drift_pct'] < mv['drift_pct']).mean() > 0.95
    # Drift is not realised volatility: MinVar's out-of-sample vol is often lower.
    share = (hrp['vol_out'] < mv['vol_out']).mean()
    assert 0.2 < share < 0.8, share


def t_shrinkage_monotone():
    d = pd.DataFrame(X.part_d())
    drift = d['drift_pct'].to_list()
    assert drift == sorted(drift, reverse=True), drift
    assert d.iloc[-1]['short_weight'] == 0.0   # full shrinkage = inverse variance, long only


def t_deterministic():
    a1, _, _ = X.part_a(); a2, _, _ = X.part_a()
    assert a1 == a2


if __name__ == '__main__':
    for name, fn in [('replica panel is identical to compare_mvo and the true covariance is sane', t_replica_panel_is_identical),
                     ('published split reproduces the report; drift = optimism x luck', t_reproduces_published_numbers),
                     ('MinVar optimism falls with training length', t_optimism_falls_with_training_length),
                     ('50 seeds: HRP drifts less in nearly all, but is not always lower-vol', t_seeds),
                     ('shrinkage lowers drift monotonically', t_shrinkage_monotone),
                     ('same inputs, same numbers', t_deterministic)]:
        test(name, fn)
    print(f'{passed} passed')
