"""Tests for vpin-classifier-sensitivity/experiment.py.
Run: python tests/test_vpin_sensitivity.py
"""
import os
import sys
from math import pi, sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'vpin-classifier-sensitivity'))

import numpy as np  # noqa: E402
import experiment as X  # noqa: E402

passed = 0


def test(name, fn):
    global passed
    fn()
    passed += 1
    print('  [ ok ]', name)


def t_reproduces_published_setting():
    """250 buckets, window 50 must give the report's numbers exactly."""
    inf = X.informed_tape()
    bvc = X.run(inf, 250, 50, 'bvc')
    tick = X.run(inf, 250, 50, 'tick')
    assert abs(bvc['vpin'].mean() - 0.4410) < 5e-4, bvc['vpin'].mean()
    assert abs(tick['vpin'].mean() - 0.1779) < 5e-4, tick['vpin'].mean()
    q, a = X.segment_means(bvc['vpin'])
    assert abs(q - 0.3292) < 5e-4 and abs(a - 0.6376) < 5e-4
    assert abs(a / q - 1.94) < 0.01


def t_control_tape_has_no_drift():
    inf, ctl = X.informed_tape(), X.control_tape()
    assert (inf['volume'].to_numpy() == ctl['volume'].to_numpy()).all()
    # Removing cumsum(drift) lowers every price at and after trade 8,000 and
    # leaves the first 8,000 untouched.
    d = inf['price'].to_numpy() - ctl['price'].to_numpy()
    assert np.allclose(d[:8000], 0.0, atol=1e-9)
    assert abs(d[-1] - 4000 * 0.004) < 1e-6


def t_noise_floors_match_predictions():
    a = X.part_a()
    assert abs(a['control_tick']['vpin_mean'] - a['tick_floor_predicted']) < 0.02
    assert abs(a['control_bvc']['vpin_mean'] - a['bvc_floor_predicted_dof3']) < 0.02
    # With the normal CDF the floor is exactly 0.5: Phi(Z) is uniform.
    assert abs(X.bvc_floor_prediction(30) - 0.5) < 0.01
    # Tick floor scales like 1/sqrt(trades per bucket): 80 trades -> ~0.13.
    assert 0.10 < a['tick_floor_predicted'] < 0.16


def t_grid_directions():
    rows = X.part_b()
    at50 = {(r['buckets'], r['method']): r for r in rows if r['window'] == 50 or (r['window'] == 25 and r['buckets'] == 50)}
    tick_levels = [at50[(nb, 'tick')]['vpin_mean'] for nb in (100, 250, 500, 1000)]
    assert tick_levels == sorted(tick_levels), tick_levels  # smaller buckets, higher tick level
    bvc_levels = [at50[(nb, 'bvc')]['vpin_mean'] for nb in (100, 250, 500, 1000)]
    assert max(bvc_levels) - min(bvc_levels) < 0.06, bvc_levels  # BVC level roughly flat
    # BVC sits above the tick rule in every cell.
    for r in rows:
        if r['method'] == 'bvc':
            twin = next(x for x in rows if x['buckets'] == r['buckets'] and x['window'] == r['window'] and x['method'] == 'tick')
            assert r['vpin_mean'] > twin['vpin_mean']


def t_dof_moves_level_not_ratio():
    rows = X.part_c()
    levels = [r['vpin_mean_informed'] for r in rows]
    assert levels == sorted(levels)               # dof 1 < 3 < 30
    ratios = [r['ratio'] for r in rows]
    assert max(ratios) - min(ratios) < 0.05, ratios
    for r in rows:
        assert abs(r['vpin_mean_control'] - r['floor_predicted']) < 0.02


def t_deterministic():
    assert X.part_c() == X.part_c()


if __name__ == '__main__':
    for name, fn in [('250 buckets / window 50 reproduces the published numbers', t_reproduces_published_setting),
                     ('control tape = same tape minus the planted drift', t_control_tape_has_no_drift),
                     ('noise floors match the closed-form predictions', t_noise_floors_match_predictions),
                     ('grid: tick level rises with smaller buckets, BVC stays flat and above', t_grid_directions),
                     ('BVC dof shifts the level, not the detection ratio', t_dof_moves_level_not_ratio),
                     ('same inputs, same numbers', t_deterministic)]:
        test(name, fn)
    print(f'{passed} passed')
