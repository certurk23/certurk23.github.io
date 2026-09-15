"""Degenerate inputs: what the VPIN, HRP and PSR implementations return on
the edge cases that expose sign, convention and division-by-zero errors.

SYNTHETIC DATA by construction; these inputs are chosen for the answer
being obvious, not for realism. For each case the expected behaviour is
written down before the run and the observed output is recorded next to it.
Where the two disagree, that is a finding, not an assertion failure; the
tests in tests/test_degenerate_inputs.py pin the cases whose answer is
settled.

Run:  python experiment.py    (writes outputs/cases.csv, outputs/summary.json)
"""
from __future__ import annotations

import csv
import json
import os
import sys
from math import erfc, sqrt

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'vpin-order-flow-toxicity'))
sys.path.insert(0, os.path.join(HERE, '..', 'hierarchical-risk-parity'))
import vpin as V   # noqa: E402
import hrp as H    # noqa: E402

OUT = os.path.join(HERE, 'outputs')
SEED = 20260915


def tape(prices, volumes=None):
    prices = np.asarray(prices, dtype=float)
    volumes = np.full(len(prices), 100.0) if volumes is None else np.asarray(volumes, dtype=float)
    return pd.DataFrame({'price': prices, 'volume': volumes})


def vpin_mean(trades, bucket_size, window, method):
    out = V.vpin_from_trades(trades, bucket_size=bucket_size, window=window, method=method)
    v = out['vpin'].dropna()
    return (float(v.mean()) if len(v) else float('nan')), int(len(out))


def psr(sr, sr_star, n, g1, g2):
    d2 = 1.0 - g1 * sr + (g2 - 1.0) / 4.0 * sr * sr
    return float('nan') if d2 <= 0 else 0.5 * erfc(-((sr - sr_star) * sqrt(n - 1) / sqrt(d2)) / sqrt(2))


def vpin_cases(rng):
    n = 2000
    cases = []
    up = tape(100 + 0.01 * np.arange(n))
    down = tape(120 - 0.01 * np.arange(n))
    flat = tape(np.full(n, 100.0))
    alt = tape(100 + 0.01 * (np.arange(n) % 2))                 # up, down, up, down
    rw = tape(100 + np.cumsum(rng.normal(0, 0.01, n)))
    for name, t, expect in [
        ('monotone up (every trade higher)', up, 'VPIN ~ 1: every bucket entirely buy'),
        ('monotone down', down, 'VPIN ~ 1: every bucket entirely sell'),
        ('flat (price never moves)', flat, 'VPIN 0: no information; 50/50 split is the defensible answer'),
        ('alternating +/- one tick', alt, 'BVC: bucket close-to-close change 0 or one tick, small; tick rule: signs cancel'),
        ('random walk, no drift', rw, 'noise floor: BVC ~ 0.45, tick ~ sqrt(2/pi)/sqrt(k)'),
    ]:
        for method in ('bvc', 'tick'):
            m, nb = vpin_mean(t, bucket_size=2000.0, window=10, method=method)   # 20 trades per bucket
            cases.append({'method': 'VPIN', 'case': name, 'variant': method, 'expected': expect, 'observed': f'{m:.4f} over {nb} buckets'})
    # Volume edge cases
    one_giant = tape([100, 101, 102], volumes=[100, 5000, 100])
    m, nb = vpin_mean(one_giant, bucket_size=1000.0, window=1, method='tick')
    cases.append({'method': 'VPIN', 'case': 'one trade larger than five buckets', 'variant': 'tick',
                  'expected': 'the trade is split across buckets; volume conserved; ~5 complete buckets',
                  'observed': f'{m:.4f} over {nb} buckets'})
    m, nb = vpin_mean(rw.iloc[:100], bucket_size=2000.0, window=10, method='bvc')   # 5 buckets, window 10
    cases.append({'method': 'VPIN', 'case': 'fewer buckets than the window', 'variant': 'bvc',
                  'expected': 'no VPIN value (NaN), not a partial-window number',
                  'observed': f'{"nan" if np.isnan(m) else m} over {nb} buckets'})
    try:
        vpin_mean(rw.iloc[:15], bucket_size=2000.0, window=10, method='bvc')     # 1,500 volume < one bucket
        obs = 'returned a value'
    except Exception as e:
        obs = f'raises {type(e).__name__}: {str(e)[:60]}'
    cases.append({'method': 'VPIN', 'case': 'total volume below one bucket', 'variant': 'bvc',
                  'expected': 'refuses (ValueError), rather than returning a number from zero buckets', 'observed': obs})
    return cases


def hrp_cases(rng):
    cases = []
    n = 250
    f = rng.normal(0, 0.01, n)
    base = pd.DataFrame({'A': f + rng.normal(0, 0.005, n), 'B': -f + rng.normal(0, 0.005, n),
                         'C': rng.normal(0, 0.02, n), 'D': rng.normal(0, 0.008, n)})

    def try_case(name, df, expect, fn=lambda d: H.hrp_weights(d)):
        try:
            w = fn(df)
            obs = ', '.join(f'{k}={v:.3f}' for k, v in w.items()) + f' (sum {w.sum():.3f})'
        except Exception as e:
            obs = f'raises {type(e).__name__}: {str(e)[:70]}'
        cases.append({'method': 'HRP', 'case': name, 'variant': 'hrp_weights', 'expected': expect, 'observed': obs})

    try_case('single asset', base[['A']], 'raises ValueError (needs >= 2 assets)')
    try_case('two identical assets', pd.DataFrame({'A': base['A'], 'A2': base['A']}),
             'correlation 1, distance 0: equal split 0.5 / 0.5')
    try_case('one zero-variance asset', base.assign(Z=0.0),
             'refuses with a message that names the column (before 15 Sep 2026: an opaque scipy error about finite values)')
    try_case('perfectly anti-correlated pair plus two', base,
             'weights sum to 1, no shorts; A and B are NOT clustered: distance sqrt((1-rho)/2) puts rho=-1 at the maximum, HRP as specified does not see a hedge')
    try_case('rank-one panel (all assets = beta x one factor)',
             pd.DataFrame({f'X{i}': (0.5 + 0.25 * i) * f for i in range(4)}),
             'sample covariance singular; HRP should still return weights (no inversion)')
    with_nan = base.copy(); with_nan.iloc[10, 0] = np.nan
    try_case('NaN in returns', with_nan, 'raises ValueError (refuses NaN)')
    try_case('constant-shift panel (all returns + 1)', base + 1.0, 'identical weights to base: covariance is shift-invariant')
    # min-variance on the singular panel, for contrast
    try_case('rank-one panel, min-variance', pd.DataFrame({f'X{i}': (0.5 + 0.25 * i) * f for i in range(4)}),
             'pinv survives singularity; the solution is one of many; weights may be extreme',
             fn=lambda d: H.min_variance_weights(d))
    return cases


def psr_cases():
    cases = []
    for name, args, expect in [
        ('SR equals benchmark', (1.0, 1.0, 24, 0.0, 3.0), 'exactly 0.5'),
        ('n = 2 (smallest admissible)', (1.5, 0.0, 2, 0.0, 3.0), 'sqrt(n-1) = 1: z = 1.5/1.4577 = 1.029, PSR 0.848'),
        ('n = 1', (1.5, 0.0, 1, 0.0, 3.0), 'sqrt(0) = 0: z = 0, PSR 0.5 regardless of SR (should be refused upstream)'),
        ('variance term non-positive (skew 3, kurtosis 3, SR 1.5)', (1.5, 0.0, 24, 3.0, 3.0), 'NaN: the formula has no answer'),
        ('kurtosis below 1 (impossible for a real distribution)', (1.5, 0.0, 24, 0.0, 0.5), 'denominator sqrt(1 - 0.28) = 0.85: PSR computes but the input is invalid'),
        ('huge n', (0.05, 0.0, 1_000_000, 0.0, 3.0), 'saturates at 1: any positive SR is "certain" with enough data'),
        ('negative SR', (-0.5, 0.0, 24, 0.0, 3.0), 'below 0.5: 1 - PSR(+0.5)'),
    ]:
        v = psr(*args)
        cases.append({'method': 'PSR', 'case': name, 'variant': 'closed form', 'expected': expect, 'observed': 'nan' if np.isnan(v) else f'{v:.4f}'})
    return cases


def main():
    rng = np.random.default_rng(SEED)
    cases = vpin_cases(rng) + hrp_cases(rng) + psr_cases()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'cases.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(cases[0].keys())); w.writeheader(); w.writerows(cases)
    with open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8') as fh:
        json.dump({'cases': cases, 'seed': SEED, 'numpy': np.__version__, 'pandas': pd.__version__}, fh, indent=1)
    print('=' * 78); print('Degenerate inputs  --  SYNTHETIC'); print('=' * 78)
    for c in cases:
        print(f"[{c['method']:4s}] {c['case']} ({c['variant']})\n       expect: {c['expected']}\n       got:    {c['observed']}")
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
