"""The Deflated Sharpe Ratio in practice: how large the luck benchmark is,
whether the closed form for it holds, what it does to false positives, and
what correlated trials do to the trial count.

SYNTHETIC DATA. Nothing here is a market return.

DSR (Bailey & Lopez de Prado, 2014) is the Probabilistic Sharpe Ratio with
the benchmark raised to the Sharpe the best of N independent no-skill trials
is expected to show:

    SR*_0 = sd(SR) * [ (1 - g) Phi^-1(1 - 1/N) + g Phi^-1(1 - 1/(N e)) ],  g = 0.5772...

Part A  Recompute the site's explainer table (SR 1.50, n 120, skew -0.8,
        kurtosis 6.0, sd(SR) 0.50) so every published number is checked.
Part B  Monte Carlo under the null (N iid-normal strategies, n = 120):
        the empirical max Sharpe against the closed form, with sd(SR) taken
        from the trials themselves, as the method requires.
Part C  False positives: share of best-of-N winners with PSR(0) > 0.95
        versus DSR > 0.95, N = 1 ... 1,000; then power with one true edge.
Part D  Correlated trials: strategies sharing a common factor at rho in
        {0, 0.5, 0.9}; the effective number of independent trials implied by
        the observed maximum.

Run:  python experiment.py    (writes outputs/*.csv, outputs/summary.json)
"""
from __future__ import annotations

import csv
import json
import os
from math import e, erfc, sqrt

import numpy as np
from scipy.stats import kurtosis, norm, skew

SEED = 20260915
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
GAMMA = 0.5772156649015329
N_PERIODS = 120
REPS = 5_000
TRIALS = (1, 10, 100, 1000)
RHOS = (0.0, 0.5, 0.9)


def phi(z: float) -> float:
    return 0.5 * erfc(-z / sqrt(2.0))


def psr(sr, sr_star, n, g1, g2):
    d2 = 1.0 - g1 * sr + (g2 - 1.0) / 4.0 * sr * sr
    return float('nan') if d2 <= 0 else phi((sr - sr_star) * sqrt(n - 1) / sqrt(d2))


def expected_max_sr(sd_sr: float, n_trials: int) -> float:
    """Closed form for E[max of N iid draws] with sd sd_sr (Bailey & LdP 2014)."""
    if n_trials < 2:
        return 0.0
    return sd_sr * ((1 - GAMMA) * norm.ppf(1 - 1 / n_trials) + GAMMA * norm.ppf(1 - 1 / (n_trials * e)))


def dsr(sr, n, g1, g2, sd_sr, n_trials):
    return psr(sr, expected_max_sr(sd_sr, n_trials), n, g1, g2)


def sample_sr(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=-1) / x.std(axis=-1, ddof=1)


# --------------------------------------------------------------------------
def part_a():
    sr, n, g1, g2, sd = 1.50, 120, -0.8, 6.0, 0.50
    den = sqrt(1 - g1 * sr + (g2 - 1) / 4 * sr * sr)
    rows = []
    for N in TRIALS:
        rows.append({'N': N, 'expected_max_sr': expected_max_sr(sd, N), 'dsr': dsr(sr, n, g1, g2, sd, N)})
    return {'denominator': den, 'psr_zero': psr(sr, 0.0, n, g1, g2), 'rows': rows}


def part_b(rng):
    rows = []
    for N in TRIALS:
        if N == 1:
            continue
        maxes, sds = [], []
        for _ in range(REPS):
            x = rng.standard_normal((N, N_PERIODS))
            s = sample_sr(x)
            maxes.append(s.max()); sds.append(s.std(ddof=1))
        sd_emp = float(np.mean(sds))
        rows.append({'N': N, 'sd_sr_across_trials': sd_emp, 'sd_sr_theory': sqrt(1 / N_PERIODS),
                     'max_sr_mc': float(np.mean(maxes)), 'max_sr_formula': expected_max_sr(sd_emp, N),
                     'max_sr_formula_sd050': expected_max_sr(0.50, N)})
    return rows


def part_c(rng, edge_sr: float = 0.30):
    rows = []
    for N in TRIALS:
        naive_fp = dsr_fp = 0
        naive_pow = dsr_pow = picked = 0
        for _ in range(REPS):
            # Null: no strategy has edge.
            x = rng.standard_normal((N, N_PERIODS))
            s = sample_sr(x)
            j = int(np.argmax(s))
            g1, g2 = float(skew(x[j])), float(kurtosis(x[j], fisher=False))
            sd = float(s.std(ddof=1)) if N > 1 else 0.0
            if psr(s[j], 0.0, N_PERIODS, g1, g2) > 0.95:
                naive_fp += 1
            if dsr(s[j], N_PERIODS, g1, g2, sd, N) > 0.95:
                dsr_fp += 1
            # One true edge among N: strategy 0 has mean edge_sr per period.
            x[0] += edge_sr
            s = sample_sr(x)
            j = int(np.argmax(s))
            g1, g2 = float(skew(x[j])), float(kurtosis(x[j], fisher=False))
            sd = float(s.std(ddof=1)) if N > 1 else 0.0
            if j == 0:
                picked += 1
                if psr(s[j], 0.0, N_PERIODS, g1, g2) > 0.95:
                    naive_pow += 1
                if dsr(s[j], N_PERIODS, g1, g2, sd, N) > 0.95:
                    dsr_pow += 1
        rows.append({'N': N, 'naive_psr_fp': naive_fp / REPS, 'dsr_fp': dsr_fp / REPS,
                     'edge_picked': picked / REPS, 'naive_psr_power': naive_pow / REPS, 'dsr_power': dsr_pow / REPS})
    return rows


def part_d(rng, N: int = 100):
    rows = []
    for rho in RHOS:
        maxes, sds = [], []
        for _ in range(REPS):
            common = rng.standard_normal(N_PERIODS)
            idio = rng.standard_normal((N, N_PERIODS))
            x = sqrt(rho) * common + sqrt(1 - rho) * idio
            s = sample_sr(x)
            maxes.append(s.max()); sds.append(s.std(ddof=1))
        m, sd = float(np.mean(maxes)), float(np.mean(sds))
        # Effective N: the trial count whose closed-form E[max] matches the observed one.
        grid = np.arange(2, 20_000)
        em = np.array([expected_max_sr(sd, k) for k in grid])
        n_eff = int(grid[np.argmin(np.abs(em - m))])
        rows.append({'rho': rho, 'sd_sr_across_trials': sd, 'max_sr_mc': m,
                     'max_sr_formula_nominalN': expected_max_sr(sd, N), 'n_effective': n_eff})
    return rows


def write_csv(name, rows):
    with open(os.path.join(OUT, name), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def main():
    rng = np.random.default_rng(SEED)
    a = part_a(); b = part_b(rng); c = part_c(rng); d = part_d(rng)
    os.makedirs(OUT, exist_ok=True)
    write_csv('explainer_table.csv', a['rows']); write_csv('max_sr_null.csv', b)
    write_csv('false_positives.csv', c); write_csv('correlated_trials.csv', d)
    with open(os.path.join(OUT, 'summary.json'), 'w') as fh:
        json.dump({'A': a, 'B': b, 'C': c, 'D': d, 'seed': SEED, 'n_periods': N_PERIODS, 'reps': REPS,
                   'numpy': np.__version__}, fh, indent=1)
    print('=' * 70); print('Deflated Sharpe Ratio  --  SYNTHETIC DATA'); print('=' * 70)
    print(f"A. explainer table: denominator {a['denominator']:.4f}, PSR(0) {a['psr_zero']:.4f}")
    for r in a['rows']:
        print(f"   N={r['N']:5d}  E[max SR] {r['expected_max_sr']:.4f}  DSR {r['dsr']:.4f}")
    print(f"B. null, n={N_PERIODS}, {REPS:,} reps: sd(SR) across trials vs theory sqrt(1/n)={sqrt(1/N_PERIODS):.4f}")
    for r in b:
        print(f"   N={r['N']:5d}  sd(SR) {r['sd_sr_across_trials']:.4f}  max SR: MC {r['max_sr_mc']:.4f}  formula {r['max_sr_formula']:.4f}  (formula with sd 0.50: {r['max_sr_formula_sd050']:.4f})")
    print(f"C. false positives at 0.95 (null) and power with one true edge (SR {0.30} per period)")
    for r in c:
        print(f"   N={r['N']:5d}  naive PSR FP {r['naive_psr_fp']:.1%}  DSR FP {r['dsr_fp']:.1%} | edge picked {r['edge_picked']:.1%}  naive power {r['naive_psr_power']:.1%}  DSR power {r['dsr_power']:.1%}")
    print('D. correlated trials, N=100')
    for r in d:
        print(f"   rho={r['rho']:.1f}  sd(SR) {r['sd_sr_across_trials']:.4f}  max SR MC {r['max_sr_mc']:.4f}  formula(N=100) {r['max_sr_formula_nominalN']:.4f}  effective N {r['n_effective']}")
    print(f"wrote {OUT}")


if __name__ == '__main__':
    main()
