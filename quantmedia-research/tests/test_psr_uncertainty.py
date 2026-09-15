"""Tests for psr-moment-uncertainty/experiment.py.

Tolerance-based on purpose: the experiment is Monte Carlo, and NumPy does not
promise bit-identical Generator streams across minor releases, so the checks
pin what the article claims rather than every decimal of the CSV.
Run: python tests/test_psr_uncertainty.py
"""
import os
import sys
from math import sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'psr-moment-uncertainty'))

import numpy as np  # noqa: E402
import experiment as X  # noqa: E402

passed = 0


def test(name, fn):
    global passed
    fn()
    passed += 1
    print('  [ ok ]', name)


def t_psr_closed_form():
    # The site's worked example, both cases, against independent arithmetic.
    assert abs(X.psr(1.5, 0.0, 3.0, 24) - 0.9999996) < 1e-6
    assert abs(X.psr(1.5, -1.2, 7.0, 24) - 0.9981037) < 1e-6
    # z for the skewed case is 2.8949, not 2.8955 (pinned after a reader caught it).
    z = 1.5 * sqrt(23) / sqrt(1 + 1.8 + 1.5 * 2.25)
    assert abs(z - 2.894921) < 1e-5
    assert np.isnan(X.psr(1.5, 3.0, 3.0, 24))  # non-positive variance


def t_calibration_hits_targets():
    p, m1, s1, m2, s2 = X.calibrate()
    mu, var, g1, g2 = X.mixture_moments(p, m1, s1, m2, s2)
    assert abs(mu - 1.5) < 1e-8 and abs(var - 1.0) < 1e-8
    assert abs(g1 + 1.2) < 1e-6 and abs(g2 - 7.0) < 1e-6
    # Shifting the mean must leave shape alone.
    q = X.shift((p, m1, s1, m2, s2), 0.5)
    mu2, var2, g1b, g2b = X.mixture_moments(*q)
    assert abs(mu2 - 0.5) < 1e-8 and abs(var2 - 1.0) < 1e-8
    assert abs(g1b + 1.2) < 1e-6 and abs(g2b - 7.0) < 1e-6


def t_normal_input_variability():
    a = X.part_a(np.random.default_rng(1))
    # Finite-sample SDs of the biased estimators at n = 24 under normality.
    assert abs(a['g2_sd_exact'] - 0.737) < 0.001
    assert abs(a['g1_sd_exact'] - 0.442) < 0.001
    assert abs(a['g2_sd_mc'] - a['g2_sd_exact']) < 0.05
    assert abs(a['g1_sd_mc'] - a['g1_sd_exact']) < 0.03
    # The asymptotic sqrt(24/n) overstates the finite-sample SD by about a third.
    assert a['g2_sd_asymptotic'] > 1.3 * a['g2_sd_exact']


def t_scenarios_direction():
    rng = np.random.default_rng(7)
    base = X.calibrate()
    b15, _, _ = X.part_b(rng, base, 1.5)
    b05, _, _ = X.part_b(rng, X.shift(base, 0.5), 0.5)
    # Sample kurtosis at n = 24 cannot see the tails: biased well below 7.
    assert 3.5 < b15['g2_mean'] < 5.0 and 3.5 < b05['g2_mean'] < 5.0
    # SR dispersion exceeds Lo's normal-theory SE once tails are fat.
    assert b15['sr_sd'] > b15['sr_se_lo2002'] and b05['sr_sd'] > b05['sr_se_lo2002']
    # At SR 1.5 the PSR is saturated; at SR 0.5 it is not.
    assert b15['plugin_p05'] > 0.97
    assert b05['plugin_p05'] < 0.80 and b05['plugin_share_below_0.90'] > 0.15
    assert abs(b05['true_psr'] - 0.9560) < 0.001


def t_stationary_bootstrap_shape():
    rng = np.random.default_rng(3)
    x = np.arange(24, dtype=float)
    b = X.stationary_bootstrap(rng, x, 200, 3.0)
    assert b.shape == (200, 24)
    # Every value is an element of x (resampling, not perturbation).
    assert set(np.unique(b)).issubset(set(x))


def t_deterministic():
    r1 = X.part_a(np.random.default_rng(X.SEED))
    r2 = X.part_a(np.random.default_rng(X.SEED))
    assert r1 == r2


if __name__ == '__main__':
    for name, fn in [('PSR closed form matches the worked example', t_psr_closed_form),
                     ('mixture calibration hits SR 1.5 / skew -1.2 / kurtosis 7', t_calibration_hits_targets),
                     ('input variability under normality matches finite-sample theory', t_normal_input_variability),
                     ('scenarios: kurtosis biased down, SR wider than Lo, marginal PSR spreads', t_scenarios_direction),
                     ('stationary bootstrap resamples the series', t_stationary_bootstrap_shape),
                     ('same seed, same numbers', t_deterministic)]:
        test(name, fn)
    print(f'{passed} passed')
