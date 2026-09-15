"""What twenty observations of the Signal Breadth Index can and cannot say.

Reads the site's own published series (data/breadth_history.json, written
nightly by the pipeline, never backfilled) and computes the descriptive
statistics the note quotes, plus the sample sizes that would be needed
before any predictive claim could be tested. Nothing here is a forecast.

Run:  python summarize.py     (writes outputs/summary.json, outputs/series.csv)
"""
from __future__ import annotations

import csv
import json
import os
from math import sqrt, atanh, tanh

import numpy as np
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '..', 'data', 'breadth_history.json')
OUT = os.path.join(HERE, 'outputs')


def load(path: str = SRC):
    d = json.load(open(path, encoding='utf-8'))
    s = sorted(d['series'], key=lambda r: r['market_date'])
    return d, s


def lag1_autocorr(x: np.ndarray) -> float:
    x = x - x.mean()
    return float((x[:-1] * x[1:]).sum() / (x * x).sum())


def n_for_correlation(r: float, power: float = 0.8, alpha: float = 0.05) -> int:
    """Observations needed to detect a true correlation r at two-sided alpha
    with the given power, via Fisher's z (n = ((z_a + z_b)/atanh(r))^2 + 3)."""
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    return int(np.ceil(((za + zb) / atanh(r)) ** 2 + 3))


def summarize(d, s):
    b = np.array([r['breadth_pct'] for r in s], dtype=float)
    med = np.array([r['median_score'] for r in s], dtype=float)
    mean_sc = np.array([r['mean_score'] for r in s], dtype=float)
    buys = np.array([r['buy_signals'] for r in s], dtype=float)
    scored = np.array([r['scored'] for r in s], dtype=float)
    n = len(b)
    r1 = lag1_autocorr(b)
    # Standard error of a sample autocorrelation under the white-noise null: 1/sqrt(n).
    se_r = 1 / sqrt(n)
    # Correlation between breadth and the median score across days (mechanical, same scan).
    r_bm = float(np.corrcoef(b, med)[0, 1])
    r_bmean = float(np.corrcoef(b, mean_sc)[0, 1])
    daily_change = np.diff(b)
    out = {
        'observations': n, 'first_date': s[0]['market_date'], 'last_date': s[-1]['market_date'],
        'threshold': d['threshold'], 'signal_count': d['signal_count'], 'methodology_version': d['methodology_version'],
        'scored_min': int(scored.min()), 'scored_max': int(scored.max()),
        'breadth_min': float(b.min()), 'breadth_max': float(b.max()), 'breadth_median': float(np.median(b)),
        'breadth_mean': float(b.mean()), 'breadth_sd': float(b.std(ddof=1)),
        'breadth_first': float(b[0]), 'breadth_last': float(b[-1]),
        'date_of_max': s[int(b.argmax())]['market_date'], 'date_of_min': s[int(b.argmin())]['market_date'],
        'buys_min': int(buys.min()), 'buys_max': int(buys.max()),
        'median_score_min': int(med.min()), 'median_score_max': int(med.max()),
        'daily_change_mean_abs': float(np.abs(daily_change).mean()), 'daily_change_max_abs': float(np.abs(daily_change).max()),
        'days_up': int((daily_change > 0).sum()), 'days_down': int((daily_change < 0).sum()), 'days_flat': int((daily_change == 0).sum()),
        'lag1_autocorr': r1, 'lag1_se_white_noise': se_r, 'lag1_t': r1 / se_r,
        'corr_breadth_median_score': r_bm, 'corr_breadth_mean_score': r_bmean,
        'n_needed_r03': n_for_correlation(0.3), 'n_needed_r02': n_for_correlation(0.2), 'n_needed_r01': n_for_correlation(0.1),
        'trading_days_to_r03': None,
    }
    out['trading_days_to_r03'] = out['n_needed_r03'] - n
    return out


def main():
    d, s = load()
    out = summarize(d, s)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'summary.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=1)
    with open(os.path.join(OUT, 'series.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(s[0].keys())); w.writeheader(); w.writerows(s)
    print('=' * 70); print('Signal Breadth: twenty observations'); print('=' * 70)
    for k, v in out.items():
        print(f'  {k:28s} {v}')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
