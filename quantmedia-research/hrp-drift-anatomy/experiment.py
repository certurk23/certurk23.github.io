"""Where minimum-variance's out-of-sample volatility drift comes from, and
how much training length, shrinkage and the random seed change it.

SYNTHETIC DATA. Nothing here is a market return.

The HRP verification report fits six allocators on 120 periods of a 20-asset
block-correlated panel and holds the weights fixed over the next 400: HRP's
volatility drifts +1.3%, unconstrained minimum-variance +13.6%. This script
asks why, using the fact that the panel is generated from a known factor
model, so the TRUE covariance is available and every allocator's realised
volatility can be split into two parts:

    optimism = vol_true / vol_in  - 1   (in-sample estimate below the truth:
                                         the optimiser fitted the noise)
    luck     = vol_out / vol_true - 1   (the test window's own sampling noise)
    drift    = vol_out / vol_in   - 1   = (1 + optimism)(1 + luck) - 1

Part A  Decomposition at the published split (train 120, test 400), plus the
        oracle: minimum variance computed from the true covariance.
Part B  Training length 60 ... 2,000 periods with a fixed 400-period test.
Part C  50 seeds at the published split: distribution of drift per allocator.
Part D  Shrinkage intensity 0 ... 1 for minimum variance at the published split.

Run:  python experiment.py     (writes outputs/*.csv, outputs/summary.json)
"""
from __future__ import annotations

import csv
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
HRP_DIR = os.path.join(HERE, '..', 'hierarchical-risk-parity')
sys.path.insert(0, HRP_DIR)
import compare_mvo as CM  # noqa: E402  (the published panel and split)
import hrp as H           # noqa: E402  (the implementation under test)

OUT = os.path.join(HERE, 'outputs')
SEED = CM.SEED
SPLIT = 120
TEST = 400
BLOCKS = {'TECH': 6, 'FIN': 5, 'ENERGY': 4, 'STAPLE': 5}
TRAIN_LENGTHS = (60, 120, 250, 500, 1000, 2000)
N_SEEDS = 50
SHRINKAGES = (0.0, 0.1, 0.3, 0.5, 0.7, 1.0)
PPY = 252


def make_panel_with_truth(n_periods: int, seed: int):
    """Mirror compare_mvo.make_synthetic_returns call for call, so the panel
    is identical, and additionally return the true covariance implied by the
    factor loadings and idiosyncratic volatilities that were drawn."""
    rng = np.random.default_rng(seed)
    market = rng.normal(0, 0.008, n_periods)
    cols, data = [], []
    beta_m, beta_b, sig_i, block_of = [], [], [], []
    for b, (block, count) in enumerate(BLOCKS.items()):
        factor = rng.normal(0, 0.010, n_periods)
        for i in range(count):
            bm = rng.uniform(0.6, 1.3)
            bb = rng.uniform(0.7, 1.2)
            s = rng.uniform(0.006, 0.018)
            idio = rng.normal(0, s, n_periods)
            data.append(bm * market + bb * factor + idio)
            cols.append(f'{block}_{i + 1}')
            beta_m.append(bm); beta_b.append(bb); sig_i.append(s); block_of.append(b)
    panel = pd.DataFrame(np.array(data).T, columns=cols,
                         index=pd.date_range('2022-01-03', periods=n_periods, freq='B'))
    bm = np.array(beta_m); bb = np.array(beta_b); si = np.array(sig_i); bl = np.array(block_of)
    same_block = (bl[:, None] == bl[None, :]).astype(float)
    cov = (0.008 ** 2) * np.outer(bm, bm) + (0.010 ** 2) * same_block * np.outer(bb, bb) + np.diag(si ** 2)
    return panel, pd.DataFrame(cov, index=cols, columns=cols)


def allocators():
    return {
        'HRP (single)': lambda d: H.hrp_weights(d, method='single'),
        'HRP (ward)': lambda d: H.hrp_weights(d, method='ward'),
        'MinVar': lambda d: H.min_variance_weights(d),
        'MinVar long-only': lambda d: H.min_variance_weights(d, long_only=True),
        'MinVar shrunk 0.3': lambda d: H.min_variance_weights(d, shrinkage=0.3),
        'Equal weight': lambda d: pd.Series(1 / d.shape[1], index=d.columns),
    }


def ann_vol_true(w: pd.Series, cov_true: pd.DataFrame) -> float:
    v = w.reindex(cov_true.index).fillna(0.0).to_numpy()
    return float(np.sqrt(v @ cov_true.to_numpy() @ v) * np.sqrt(PPY))


def oracle_minvar(cov_true: pd.DataFrame) -> pd.Series:
    inv = np.linalg.inv(cov_true.to_numpy())
    w = inv @ np.ones(len(inv)); w = w / w.sum()
    return pd.Series(w, index=cov_true.index)


def evaluate(train: pd.DataFrame, test: pd.DataFrame, cov_true: pd.DataFrame, allocs: dict) -> list[dict]:
    rows = []
    w_oracle = oracle_minvar(cov_true)
    for name, fn in allocs.items():
        w = fn(train)
        s_in = H.portfolio_stats(w, train)
        s_out = H.portfolio_stats(w, test)
        vt = ann_vol_true(w, cov_true)
        rows.append({
            'allocator': name,
            'vol_in': s_in['annual_vol'], 'vol_true': vt, 'vol_out': s_out['annual_vol'],
            'optimism_pct': 100 * (vt / s_in['annual_vol'] - 1),
            'luck_pct': 100 * (s_out['annual_vol'] / vt - 1),
            'drift_pct': 100 * (s_out['annual_vol'] / s_in['annual_vol'] - 1),
            'dist_to_oracle': float(np.abs(w.reindex(w_oracle.index).to_numpy() - w_oracle.to_numpy()).sum()),
            'max_weight': s_in['max_weight'], 'short_weight': s_in['short_weight'],
            'n_effective': s_in['n_effective'],
        })
    return rows


# --------------------------------------------------------------------------
def part_a():
    panel, cov_true = make_panel_with_truth(520, SEED)
    check = CM.make_synthetic_returns()
    assert np.allclose(panel.to_numpy(), check.to_numpy()), 'replica panel differs from compare_mvo'
    train, test = panel.iloc[:SPLIT], panel.iloc[SPLIT:]
    rows = evaluate(train, test, cov_true, allocators())
    w_or = oracle_minvar(cov_true)
    oracle = {
        'vol_true': ann_vol_true(w_or, cov_true),
        'vol_out': H.portfolio_stats(w_or, test)['annual_vol'],
        'vol_in': H.portfolio_stats(w_or, train)['annual_vol'],
        'max_weight': float(w_or.max()), 'short_weight': float(w_or[w_or < 0].sum()),
        'n_effective': float(1 / (w_or ** 2).sum()),
    }
    extra = {
        'cond_sample_cov': float(np.linalg.cond(train.cov().to_numpy())),
        'cond_true_cov': float(np.linalg.cond(cov_true.to_numpy())),
        'mean_abs_corr_sample': float(np.abs(train.corr().to_numpy()[~np.eye(20, dtype=bool)]).mean()),
    }
    return rows, oracle, extra


def part_b():
    n = max(TRAIN_LENGTHS) + TEST
    panel, cov_true = make_panel_with_truth(n, SEED + 1)
    test = panel.iloc[-TEST:]
    rows = []
    for T in TRAIN_LENGTHS:
        train = panel.iloc[-TEST - T:-TEST]
        for r in evaluate(train, test, cov_true, allocators()):
            r['train_len'] = T
            rows.append(r)
    return rows


def part_c():
    rows = []
    for k in range(N_SEEDS):
        panel, cov_true = make_panel_with_truth(520, SEED + 100 + k)
        for r in evaluate(panel.iloc[:SPLIT], panel.iloc[SPLIT:], cov_true, allocators()):
            r['seed'] = SEED + 100 + k
            rows.append(r)
    return rows


def part_d():
    panel, cov_true = make_panel_with_truth(520, SEED)
    train, test = panel.iloc[:SPLIT], panel.iloc[SPLIT:]
    allocs = {f'MinVar shrunk {s:.1f}': (lambda s: (lambda d: H.min_variance_weights(d, shrinkage=s)))(s) for s in SHRINKAGES}
    rows = evaluate(train, test, cov_true, allocs)
    for r, s in zip(rows, SHRINKAGES):
        r['shrinkage'] = s
    return rows


def write_csv(name, rows, digits=4):
    with open(os.path.join(OUT, name), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, digits) if isinstance(v, float) else v) for k, v in r.items()})


def main():
    a_rows, oracle, extra = part_a()
    b_rows, c_rows, d_rows = part_b(), part_c(), part_d()
    os.makedirs(OUT, exist_ok=True)
    write_csv('decomposition.csv', a_rows); write_csv('train_length.csv', b_rows)
    write_csv('seeds.csv', c_rows); write_csv('shrinkage.csv', d_rows)
    c = pd.DataFrame(c_rows)
    seed_summary = {}
    for name, g in c.groupby('allocator', sort=False):
        seed_summary[name] = {'drift_median': float(g['drift_pct'].median()),
                              'drift_p25': float(g['drift_pct'].quantile(.25)), 'drift_p75': float(g['drift_pct'].quantile(.75)),
                              'optimism_median': float(g['optimism_pct'].median()), 'luck_median': float(g['luck_pct'].median()),
                              'vol_out_median': float(g['vol_out'].median())}
    hrp = c[c.allocator == 'HRP (single)'].set_index('seed'); mv = c[c.allocator == 'MinVar'].set_index('seed')
    seed_summary['share_hrp_drift_below_minvar'] = float((hrp['drift_pct'] < mv['drift_pct']).mean())
    seed_summary['share_hrp_vol_out_below_minvar'] = float((hrp['vol_out'] < mv['vol_out']).mean())
    with open(os.path.join(OUT, 'summary.json'), 'w') as fh:
        json.dump({'A': a_rows, 'oracle': oracle, 'extra': extra, 'B': b_rows, 'C': seed_summary, 'D': d_rows,
                   'numpy': np.__version__, 'pandas': pd.__version__}, fh, indent=1)
    print('=' * 78)
    print('HRP drift anatomy  --  SYNTHETIC DATA')
    print('=' * 78)
    print(f"A. published split (train {SPLIT}, test {TEST}); sample cov condition {extra['cond_sample_cov']:,.0f}, true {extra['cond_true_cov']:,.0f}")
    print('   allocator            vol_in  vol_true vol_out  optimism   luck   drift  |w-oracle| maxw  short  n_eff')
    for r in a_rows:
        print(f"   {r['allocator']:20s} {r['vol_in']:.4f}  {r['vol_true']:.4f}  {r['vol_out']:.4f}  {r['optimism_pct']:+6.1f}% {r['luck_pct']:+6.1f}% {r['drift_pct']:+6.1f}%   {r['dist_to_oracle']:.3f}   {r['max_weight']:.3f} {r['short_weight']:+.3f} {r['n_effective']:5.2f}")
    print(f"   oracle MinVar (true cov): vol_true {oracle['vol_true']:.4f} vol_in {oracle['vol_in']:.4f} vol_out {oracle['vol_out']:.4f} maxw {oracle['max_weight']:.3f} short {oracle['short_weight']:+.3f} n_eff {oracle['n_effective']:.2f}")
    print('B. training length (fixed 400-period test, seed+1)')
    print('   T      HRP drift  MinVar drift  MinVar optimism  MinVar |w-oracle|  shrunk drift  EW drift')
    b = pd.DataFrame(b_rows)
    for T in TRAIN_LENGTHS:
        g = b[b.train_len == T].set_index('allocator')
        print(f"   {T:5d}  {g.loc['HRP (single)','drift_pct']:+7.1f}%  {g.loc['MinVar','drift_pct']:+9.1f}%  {g.loc['MinVar','optimism_pct']:+11.1f}%  {g.loc['MinVar','dist_to_oracle']:14.3f}  {g.loc['MinVar shrunk 0.3','drift_pct']:+9.1f}%  {g.loc['Equal weight','drift_pct']:+7.1f}%")
    print(f"C. {N_SEEDS} seeds at the published split: drift median [p25, p75]; optimism / luck medians")
    for name, s in seed_summary.items():
        if isinstance(s, dict):
            print(f"   {name:20s} {s['drift_median']:+6.1f}% [{s['drift_p25']:+6.1f}, {s['drift_p75']:+6.1f}]   {s['optimism_median']:+6.1f}% / {s['luck_median']:+6.1f}%   vol_out {s['vol_out_median']:.4f}")
    print(f"   HRP drift below MinVar in {seed_summary['share_hrp_drift_below_minvar']:.0%} of seeds; HRP vol_out below MinVar in {seed_summary['share_hrp_vol_out_below_minvar']:.0%}")
    print('D. shrinkage (published split)')
    for r in d_rows:
        print(f"   shrink {r['shrinkage']:.1f}: vol_in {r['vol_in']:.4f} vol_out {r['vol_out']:.4f} drift {r['drift_pct']:+6.1f}% optimism {r['optimism_pct']:+6.1f}% short {r['short_weight']:+.3f} n_eff {r['n_effective']:.2f}")
    print(f"wrote {OUT}")


if __name__ == '__main__':
    main()
