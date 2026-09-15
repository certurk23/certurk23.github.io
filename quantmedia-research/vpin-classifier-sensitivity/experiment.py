"""Why BVC and the tick rule give different VPIN levels on the same tape, and
how much bucket size, window and BVC's t-distribution setting move them.

SYNTHETIC DATA. Nothing here is a market return.

Reuses the tape from vpin-order-flow-toxicity/example.py (seed 20260808,
20,000 trades, informed buying planted in trades 8,000-11,999) and the
implementation in vpin-order-flow-toxicity/vpin.py. A control tape with the
planted drift removed (same random steps, same volumes) isolates each
classifier's noise floor: what VPIN reads when there is nothing to detect.

Part A  Decomposition at the published setting (250 buckets, window 50):
        per-bucket imbalance ratios, and each classifier's noise floor on
        the control tape against a closed-form prediction.
Part B  Grid: buckets in {50, 100, 250, 500, 1000} x window in {10, 25, 50, 100}
        x classifier, on the informed tape: level in the balanced and
        informed segments and their ratio.
Part C  BVC degrees of freedom in {1, 3, 30} at the published setting.

Run:  python experiment.py     (writes outputs/*.csv and outputs/summary.json)
"""
from __future__ import annotations

import csv
import json
import os
import sys
from math import pi, sqrt

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

HERE = os.path.dirname(os.path.abspath(__file__))
VPIN_DIR = os.path.join(HERE, '..', 'vpin-order-flow-toxicity')
sys.path.insert(0, VPIN_DIR)
import example as EX  # noqa: E402  (the published tape)
import vpin as V      # noqa: E402  (the implementation under test)

OUT = os.path.join(HERE, 'outputs')
BUCKET_COUNTS = (50, 100, 250, 500, 1000)
WINDOWS = (10, 25, 50, 100)
DOFS = (1, 3, 30)
QUIET, ACTIVE = (0.15, 0.35), (0.42, 0.62)   # bucket-index fractions, as in example.py


def informed_tape() -> pd.DataFrame:
    return EX.make_synthetic_trades()


def control_tape() -> pd.DataFrame:
    """The same tape with the planted drift removed. example.py builds
    price = 100 + cumsum(N(0, 0.01) + drift) with drift = 0.004 on trades
    8,000-11,999; subtracting cumsum(drift) recovers the driftless path with
    the identical noise and volumes."""
    t = informed_tape().copy()
    n = len(t)
    drift = np.zeros(n)
    drift[8_000:12_000] = 0.0040
    price = t['price'].to_numpy(dtype=float) - np.cumsum(drift)
    t['price'] = np.round(price, 4)
    return t


def segment_means(v: pd.Series):
    n = len(v)
    q = v.iloc[int(n * QUIET[0]):int(n * QUIET[1])].mean()
    a = v.iloc[int(n * ACTIVE[0]):int(n * ACTIVE[1])].mean()
    return float(q), float(a)


def run(trades: pd.DataFrame, n_buckets: int, window: int, method: str, dof: int = 3) -> pd.DataFrame:
    bucket_size = int(trades['volume'].sum() / n_buckets)
    return V.vpin_from_trades(trades, bucket_size=bucket_size, window=window, method=method, dof=dof)


# --------------------------------------------------------------------------
# A. Decomposition and noise floors
# --------------------------------------------------------------------------
def tick_floor_prediction(trades: pd.DataFrame, bucket_size: float) -> float:
    """If trade signs were independent fair coins, the expected absolute
    signed volume of a bucket is sqrt(2/pi) * sqrt(sum v_i^2). Divided by the
    bucket volume that is the tick rule's noise floor for VPIN. Uses the
    actual volumes bucketed exactly as vpin.py buckets them (a straddling
    trade is split), so only the sign assumption is idealised."""
    b = V.build_volume_buckets(trades, bucket_size)
    # Recover per-bucket sum of squared volumes by re-walking the tape.
    sums, cur, cur_vol = [], 0.0, 0.0
    for vol in trades['volume'].to_numpy(dtype=float):
        remaining = vol
        while remaining > 0:
            take = min(remaining, bucket_size - cur_vol)
            cur += take * take
            cur_vol += take
            remaining -= take
            if cur_vol >= bucket_size - 1e-9:
                sums.append(cur); cur, cur_vol = 0.0, 0.0
    sums = np.array(sums[:len(b)])
    return float(np.mean(sqrt(2 / pi) * np.sqrt(sums) / b['volume'].to_numpy()[:len(sums)]))


def bvc_floor_prediction(dof: int, n: int = 200_000, seed: int = 1) -> float:
    """BVC maps each bucket's standardised price change z to a buy fraction
    T_dof(z); the imbalance ratio is |2 T(z) - 1|. If z were exactly N(0, 1)
    the expected ratio is E|2 T_dof(Z) - 1|, which for the normal CDF is 0.5
    exactly (Phi(Z) is uniform). Monte Carlo for the Student-t CDF."""
    z = np.random.default_rng(seed).standard_normal(n)
    return float(np.mean(np.abs(2 * student_t.cdf(z, df=dof) - 1)))


def part_a() -> dict:
    inf, ctl = informed_tape(), control_tape()
    bucket_size = int(inf['volume'].sum() / 250)
    out = {'bucket_size': bucket_size, 'n_trades_per_bucket': None}
    res = {}
    for label, tape in (('informed', inf), ('control', ctl)):
        for method in ('bvc', 'tick'):
            df = run(tape, 250, 50, method)
            ratio = (df['order_imbalance'] / df['volume'])
            q, a = segment_means(df['vpin'])
            res[f'{label}_{method}'] = {
                'buckets': int(len(df)),
                'vpin_mean': float(df['vpin'].mean()),
                'vpin_quiet': q, 'vpin_active': a, 'ratio': a / q if q else float('nan'),
                'imb_ratio_mean': float(ratio.mean()),
                'imb_ratio_median': float(ratio.median()),
                'imb_ratio_p90': float(ratio.quantile(0.9)),
            }
            if label == 'informed' and method == 'bvc':
                out['n_trades_per_bucket'] = float(df['n_trades'].mean())
                # How much the informed drift inflates the standardisation sigma.
                dp = df['close_price'].diff()
                out['sigma_dp_informed'] = float(dp.std(ddof=1))
    dpc = run(ctl, 250, 50, 'bvc')['close_price'].diff()
    out['sigma_dp_control'] = float(dpc.std(ddof=1))
    out['tick_floor_predicted'] = tick_floor_prediction(ctl, bucket_size)
    out['bvc_floor_predicted_dof3'] = bvc_floor_prediction(3)
    out['bvc_floor_predicted_normal'] = 0.5
    out.update(res)
    return out


# --------------------------------------------------------------------------
# B. Grid
# --------------------------------------------------------------------------
def part_b() -> list[dict]:
    inf = informed_tape()
    rows = []
    for nb in BUCKET_COUNTS:
        for w in WINDOWS:
            if w >= nb:
                continue
            for method in ('bvc', 'tick'):
                df = run(inf, nb, w, method)
                q, a = segment_means(df['vpin'])
                rows.append({'buckets': nb, 'window': w, 'method': method,
                             'trades_per_bucket': round(float(df['n_trades'].mean()), 1),
                             'vpin_mean': round(float(df['vpin'].mean()), 4),
                             'vpin_quiet': round(q, 4), 'vpin_active': round(a, 4),
                             'ratio': round(a / q, 2) if q else float('nan')})
    return rows


# --------------------------------------------------------------------------
# C. BVC degrees of freedom
# --------------------------------------------------------------------------
def part_c() -> list[dict]:
    inf, ctl = informed_tape(), control_tape()
    rows = []
    for dof in DOFS:
        d_inf = run(inf, 250, 50, 'bvc', dof)
        d_ctl = run(ctl, 250, 50, 'bvc', dof)
        q, a = segment_means(d_inf['vpin'])
        rows.append({'dof': dof, 'vpin_mean_informed': round(float(d_inf['vpin'].mean()), 4),
                     'vpin_quiet': round(q, 4), 'vpin_active': round(a, 4), 'ratio': round(a / q, 2),
                     'vpin_mean_control': round(float(d_ctl['vpin'].mean()), 4),
                     'floor_predicted': round(bvc_floor_prediction(dof), 4)})
    return rows


def main():
    a, b, c = part_a(), part_b(), part_c()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'grid.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(b[0].keys())); w.writeheader(); w.writerows(b)
    with open(os.path.join(OUT, 'dof.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(c[0].keys())); w.writeheader(); w.writerows(c)
    with open(os.path.join(OUT, 'summary.json'), 'w') as fh:
        json.dump({'A': a, 'C': c, 'numpy': np.__version__, 'pandas': pd.__version__}, fh, indent=1)
    print('=' * 70)
    print('VPIN classifier and setting sensitivity  --  SYNTHETIC DATA')
    print('=' * 70)
    print(f"A. published setting: bucket {a['bucket_size']:,}, window 50, {a['n_trades_per_bucket']:.1f} trades/bucket")
    print(f"   sigma(dP) across buckets: informed tape {a['sigma_dp_informed']:.4f}, control tape {a['sigma_dp_control']:.4f}")
    for k in ('informed_bvc', 'informed_tick', 'control_bvc', 'control_tick'):
        r = a[k]
        print(f"   {k:14s} VPIN mean {r['vpin_mean']:.4f}  quiet {r['vpin_quiet']:.4f}  active {r['vpin_active']:.4f}  ratio {r['ratio']:.2f}x"
              f"  | per-bucket imbalance mean {r['imb_ratio_mean']:.4f} median {r['imb_ratio_median']:.4f} p90 {r['imb_ratio_p90']:.4f}")
    print(f"   noise floors on the control tape: tick predicted {a['tick_floor_predicted']:.4f} vs observed {a['control_tick']['vpin_mean']:.4f};"
          f" BVC(dof 3) predicted {a['bvc_floor_predicted_dof3']:.4f} vs observed {a['control_bvc']['vpin_mean']:.4f}")
    print('B. grid (informed tape)')
    print('   buckets window method trades/bucket  mean   quiet  active ratio')
    for r in b:
        print(f"   {r['buckets']:7d} {r['window']:6d} {r['method']:6s} {r['trades_per_bucket']:12.1f}  {r['vpin_mean']:.4f} {r['vpin_quiet']:.4f} {r['vpin_active']:.4f} {r['ratio']:5.2f}")
    print('C. BVC degrees of freedom (250 buckets, window 50)')
    for r in c:
        print(f"   dof {r['dof']:3d}: informed mean {r['vpin_mean_informed']:.4f} quiet {r['vpin_quiet']:.4f} active {r['vpin_active']:.4f} ratio {r['ratio']:.2f}"
              f" | control mean {r['vpin_mean_control']:.4f} floor predicted {r['floor_predicted']:.4f}")
    print(f"wrote {OUT}")


if __name__ == '__main__':
    main()
