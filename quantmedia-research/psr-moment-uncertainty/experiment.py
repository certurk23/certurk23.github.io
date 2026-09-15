"""How uncertain is a Probabilistic Sharpe Ratio at n = 24?

SYNTHETIC DATA. Nothing here is a market return.

The PSR closed form (Bailey & Lopez de Prado, 2012) plugs point estimates of
the Sharpe ratio, skewness and kurtosis into

    z = (SR - SR*) * sqrt(n - 1) / sqrt(1 - g1*SR + (g2 - 1)/4 * SR^2)

as if they were known. At n = 24 they are not. This script measures how far
the inputs and the resulting PSR move across samples of 24 observations,
using a distribution whose population moments are set to the site's worked
example (SR 1.50, skewness -1.20, Pearson kurtosis 7.00, SR* 0), so the true
PSR is known and every estimate can be compared with it.

Part A  Sampling variability of g1 and g2 at n = 24 under normality
        (Monte Carlo against the finite-sample formulas).
Part B  Plug-in PSR across 20,000 samples of n = 24 from the calibrated
        mixture, and a stationary bootstrap interval for one representative
        sample.

Run:  python experiment.py      (writes outputs/summary.csv, outputs/psr_draws.csv)
"""
from __future__ import annotations

import csv
import json
import os
from math import erfc, sqrt

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import kurtosis, skew

SEED = 20260915
N = 24
SR_TRUE, G1_TRUE, G2_TRUE, SR_STAR = 1.50, -1.20, 7.00, 0.0
REPS = 20_000
BOOT = 5_000
MEAN_BLOCK = 3.0
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'outputs')


def phi(z: float) -> float:
    return 0.5 * erfc(-z / sqrt(2.0))


def psr(sr: float, g1: float, g2: float, n: int, sr_star: float = SR_STAR) -> float:
    """Closed-form PSR. g2 is Pearson (non-excess) kurtosis; a normal has 3."""
    d2 = 1.0 - g1 * sr + (g2 - 1.0) / 4.0 * sr * sr
    if d2 <= 0:
        return float('nan')
    return phi((sr - sr_star) * sqrt(n - 1) / sqrt(d2))


def moments(x: np.ndarray) -> tuple[float, float, float]:
    """SR = mean/std (ddof=1); skewness and Pearson kurtosis with the biased
    (population) estimators, i.e. what scipy.stats.skew/kurtosis return by
    default. State the estimator; it matters at n = 24."""
    sd = x.std(ddof=1)
    return x.mean() / sd, float(skew(x)), float(kurtosis(x, fisher=False))


# --------------------------------------------------------------------------
# A. Sampling variability of the inputs under normality
# --------------------------------------------------------------------------
def part_a(rng: np.random.Generator) -> dict:
    x = rng.standard_normal((REPS, N))
    g1 = skew(x, axis=1)
    g2 = kurtosis(x, axis=1, fisher=False)  # Pearson
    sr = x.mean(axis=1) / x.std(axis=1, ddof=1)
    n = N
    # Exact finite-sample variances of the biased estimators under normality.
    var_g1 = 6.0 * (n - 2) / ((n + 1) * (n + 3))
    var_g2 = 24.0 * n * (n - 2) * (n - 3) / ((n + 1) ** 2 * (n + 3) * (n + 5))
    return {
        'g1_sd_mc': float(g1.std()), 'g1_sd_exact': sqrt(var_g1),
        'g2_sd_mc': float(g2.std()), 'g2_sd_exact': sqrt(var_g2),
        'g2_sd_asymptotic': sqrt(24.0 / n),
        'g2_mean_mc': float(g2.mean()),
        'g2_p05': float(np.percentile(g2, 5)), 'g2_p95': float(np.percentile(g2, 95)),
        'sr_sd_mc_at_sr0': float(sr.std()),
        'sr_se_naive': 1.0 / sqrt(n),
    }


# --------------------------------------------------------------------------
# B. A distribution with the worked example's population moments
# --------------------------------------------------------------------------
def mixture_moments(p: float, m1: float, s1: float, m2: float, s2: float):
    """Population mean, variance, skewness, Pearson kurtosis of a two-component
    normal mixture, from raw moments."""
    def raw(m, s, k):
        # E[X^k] for X ~ N(m, s^2), k <= 4
        return {1: m, 2: m * m + s * s, 3: m ** 3 + 3 * m * s * s,
                4: m ** 4 + 6 * m * m * s * s + 3 * s ** 4}[k]
    E = {k: p * raw(m1, s1, k) + (1 - p) * raw(m2, s2, k) for k in (1, 2, 3, 4)}
    mu = E[1]
    var = E[2] - mu * mu
    mu3 = E[3] - 3 * mu * E[2] + 2 * mu ** 3
    mu4 = E[4] - 4 * mu * E[3] + 6 * mu * mu * E[2] - 3 * mu ** 4
    return mu, var, mu3 / var ** 1.5, mu4 / var ** 2


def calibrate(p: float = 0.10):
    """Solve for (m1, s1, m2, s2) so that mean/sd = SR_TRUE with sd = 1,
    skewness = G1_TRUE and Pearson kurtosis = G2_TRUE. The mixing weight p is
    fixed (a 10% 'bad regime'); four equations, four unknowns."""
    def resid(v):
        m1, s1, m2, s2 = v
        mu, var, g1, g2 = mixture_moments(p, m1, abs(s1), m2, abs(s2))
        return [mu - SR_TRUE, var - 1.0, g1 - G1_TRUE, g2 - G2_TRUE]
    sol = least_squares(resid, x0=[1.8, 0.6, -1.2, 1.6], xtol=1e-14, ftol=1e-14, gtol=1e-14)
    m1, s1, m2, s2 = sol.x
    s1, s2 = abs(s1), abs(s2)
    mu, var, g1, g2 = mixture_moments(p, m1, s1, m2, s2)
    assert abs(mu - SR_TRUE) < 1e-8 and abs(var - 1) < 1e-8, sol
    assert abs(g1 - G1_TRUE) < 1e-6 and abs(g2 - G2_TRUE) < 1e-6, (g1, g2)
    return p, m1, s1, m2, s2


def draw_mixture(rng, params, size):
    p, m1, s1, m2, s2 = params
    comp = rng.random(size) < p
    return np.where(comp, rng.normal(m1, s1, size), rng.normal(m2, s2, size))


def stationary_bootstrap(rng, x: np.ndarray, reps: int, mean_block: float) -> np.ndarray:
    """Politis & Romano (1994): blocks of geometric length, wrapped circularly."""
    n = len(x)
    q = 1.0 / mean_block
    out = np.empty((reps, n))
    for r in range(reps):
        idx = np.empty(n, dtype=int)
        i = rng.integers(n)
        for t in range(n):
            if t and rng.random() < q:
                i = rng.integers(n)
            idx[t] = i
            i = (i + 1) % n
        out[r] = x[idx]
    return out


def shift(params, new_sr: float):
    """Same shape (variance, skewness, kurtosis), different mean: shifting both
    component means by the same amount leaves every central moment unchanged."""
    p, m1, s1, m2, s2 = params
    d = new_sr - SR_TRUE
    return p, m1 + d, s1, m2 + d, s2


def part_b(rng: np.random.Generator, params, sr_true: float) -> tuple[dict, np.ndarray, dict]:
    true_psr = psr(sr_true, G1_TRUE, G2_TRUE, N)
    x = draw_mixture(rng, params, (REPS, N))
    sr = x.mean(axis=1) / x.std(axis=1, ddof=1)
    g1 = skew(x, axis=1)
    g2 = kurtosis(x, axis=1, fisher=False)
    plug = np.array([psr(a, b, c, N) for a, b, c in zip(sr, g1, g2)])
    ok = ~np.isnan(plug)
    # Reference: what an analyst who ignored skew and kurtosis would report.
    normal_only = np.array([psr(a, 0.0, 3.0, N) for a in sr])
    summary = {
        'mixture_p': params[0], 'mixture_m1': params[1], 'mixture_s1': params[2],
        'mixture_m2': params[3], 'mixture_s2': params[4],
        'true_psr': true_psr,
        'sr_true': sr_true,
        'sr_mean': float(sr.mean()), 'sr_sd': float(sr.std()),
        'sr_se_lo2002': sqrt((1 + sr_true ** 2 / 2) / N), 'sr_se_naive': 1 / sqrt(N),
        'g1_mean': float(g1.mean()), 'g1_sd': float(g1.std()), 'g1_p05': float(np.percentile(g1, 5)), 'g1_p95': float(np.percentile(g1, 95)),
        'g2_mean': float(g2.mean()), 'g2_sd': float(g2.std()), 'g2_p05': float(np.percentile(g2, 5)), 'g2_p95': float(np.percentile(g2, 95)),
        'plugin_nan_share': float(1 - ok.mean()),
        'plugin_median': float(np.median(plug[ok])), 'plugin_mean': float(plug[ok].mean()),
        'plugin_p05': float(np.percentile(plug[ok], 5)), 'plugin_p25': float(np.percentile(plug[ok], 25)),
        'plugin_p75': float(np.percentile(plug[ok], 75)), 'plugin_p95': float(np.percentile(plug[ok], 95)),
        'plugin_share_below_0.95': float((plug[ok] < 0.95).mean()),
        'plugin_share_below_0.90': float((plug[ok] < 0.90).mean()),
        'plugin_share_above_0.95': float((plug[ok] > 0.95).mean()),
        'plugin_share_above_true': float((plug[ok] > true_psr).mean()),
        'normal_only_median': float(np.median(normal_only)),
        'normal_only_share_above_0.95': float((normal_only > 0.95).mean()),
        'normal_only_share_above_true': float((normal_only > true_psr).mean()),
    }
    # One representative sample: the draw whose plug-in PSR is closest to the median.
    j = int(np.argmin(np.abs(plug - summary['plugin_median'])))
    sample = x[j]
    s_sr, s_g1, s_g2 = moments(sample)
    b = stationary_bootstrap(rng, sample, BOOT, MEAN_BLOCK)
    b_psr = np.array([psr(*moments(row), N) for row in b])
    b_ok = ~np.isnan(b_psr)
    rep = {
        'sample_index': j, 'sample_sr': s_sr, 'sample_g1': s_g1, 'sample_g2': s_g2,
        'sample_plugin_psr': psr(s_sr, s_g1, s_g2, N),
        'boot_reps': BOOT, 'boot_mean_block': MEAN_BLOCK, 'boot_nan_share': float(1 - b_ok.mean()),
        'boot_p05': float(np.percentile(b_psr[b_ok], 5)), 'boot_p50': float(np.percentile(b_psr[b_ok], 50)),
        'boot_p95': float(np.percentile(b_psr[b_ok], 95)),
        'boot_share_below_0.95': float((b_psr[b_ok] < 0.95).mean()),
    }
    return summary, plug, rep


SCENARIOS = ((1.50, '15', 'the worked example'), (0.50, '05', 'a marginal edge'))


def report_scenario(tag, b, rep):
    print(f"B{tag}. {b['label']}: true SR {b['sr_true']:.2f}, mixture p={b['mixture_p']:.2f}: "
          f"N({b['mixture_m1']:.3f},{b['mixture_s1']:.3f}) / N({b['mixture_m2']:.3f},{b['mixture_s2']:.3f})")
    print(f"   true PSR {b['true_psr']:.4f}")
    print(f"   SR: mean {b['sr_mean']:.3f} sd {b['sr_sd']:.3f}  (Lo 2002 SE {b['sr_se_lo2002']:.3f}, naive {b['sr_se_naive']:.3f})")
    print(f"   g1: mean {b['g1_mean']:.2f} sd {b['g1_sd']:.2f}  5-95%: {b['g1_p05']:.2f} .. {b['g1_p95']:.2f}   (true -1.20)")
    print(f"   g2: mean {b['g2_mean']:.2f} sd {b['g2_sd']:.2f}  5-95%: {b['g2_p05']:.2f} .. {b['g2_p95']:.2f}   (true 7.00)")
    print(f"   plug-in PSR: median {b['plugin_median']:.4f}  5-95%: {b['plugin_p05']:.4f} .. {b['plugin_p95']:.4f}  nan {b['plugin_nan_share']:.2%}")
    print(f"   share below 0.90: {b['plugin_share_below_0.90']:.1%}  below 0.95: {b['plugin_share_below_0.95']:.1%}  "
          f"above 0.95: {b['plugin_share_above_0.95']:.1%}  above true: {b['plugin_share_above_true']:.1%}")
    print(f"   normal-only PSR median {b['normal_only_median']:.4f}, above 0.95 {b['normal_only_share_above_0.95']:.1%}, above true {b['normal_only_share_above_true']:.1%}")
    print(f"   representative sample #{rep['sample_index']}: SR {rep['sample_sr']:.3f} g1 {rep['sample_g1']:.2f} g2 {rep['sample_g2']:.2f} plug-in PSR {rep['sample_plugin_psr']:.4f}")
    print(f"   stationary bootstrap ({BOOT:,}, mean block {MEAN_BLOCK:.0f}): 5-50-95%: {rep['boot_p05']:.4f} / {rep['boot_p50']:.4f} / {rep['boot_p95']:.4f}  nan {rep['boot_nan_share']:.2%}")


def main():
    rng = np.random.default_rng(SEED)
    a = part_a(rng)
    base = calibrate()
    results = {}
    for sr_true, tag, label in SCENARIOS:
        b, plug, rep = part_b(rng, shift(base, sr_true), sr_true)
        b['label'] = label
        results[tag] = (b, plug, rep)
    os.makedirs(OUT, exist_ok=True)
    rows = [('A_' + k, v) for k, v in a.items()]
    for tag, (b, plug, rep) in results.items():
        rows += [(f'B{tag}_' + k, v) for k, v in b.items()] + [(f'R{tag}_' + k, v) for k, v in rep.items()]
        np.savetxt(os.path.join(OUT, f'psr_draws_sr{tag}.csv'), plug, fmt='%.6f', header='plugin_psr', comments='')
    with open(os.path.join(OUT, 'summary.csv'), 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['quantity', 'value'])
        for k, v in rows:
            w.writerow([k, f'{v:.6f}' if isinstance(v, float) else v])
    with open(os.path.join(OUT, 'summary.json'), 'w') as fh:
        json.dump({'A': a, **{f'B{t}': r[0] for t, r in results.items()}, **{f'R{t}': r[2] for t, r in results.items()},
                   'seed': SEED, 'n': N, 'reps': REPS, 'numpy': np.__version__}, fh, indent=1)
    print('=' * 68)
    print('PSR at n = 24  --  SYNTHETIC DATA')
    print('=' * 68)
    print(f"A. normality, n={N}, {REPS:,} draws")
    print(f"   sd(g1): MC {a['g1_sd_mc']:.3f}  exact {a['g1_sd_exact']:.3f}")
    print(f"   sd(g2): MC {a['g2_sd_mc']:.3f}  exact {a['g2_sd_exact']:.3f}  asymptotic sqrt(24/n) {a['g2_sd_asymptotic']:.3f}")
    print(f"   g2 5th-95th pct: {a['g2_p05']:.2f} - {a['g2_p95']:.2f}  (population value 3)")
    print(f"   sd(SR) at SR=0: MC {a['sr_sd_mc_at_sr0']:.3f}  naive 1/sqrt(n) {a['sr_se_naive']:.3f}")
    for tag, (b, plug, rep) in results.items():
        report_scenario(tag, b, rep)
    print(f"wrote {OUT}")


if __name__ == '__main__':
    main()
