"""
HRP vs mean-variance: an out-of-sample comparison.

    python compare_mvo.py

Builds a SYNTHETIC correlated return panel (see the warning below), fits both
allocators on an in-sample window, then measures how the resulting FIXED
weights behave out of sample. Writes outputs/comparison.csv and
outputs/weights.csv, and saves the panel to sample_returns.csv.

=============================================================================
THE RETURN DATA IS SYNTHETIC, generated from a fixed seed. It is NOT real
market data. It has a deliberate block-correlation structure so the clustering
step has something to find. No conclusion about real assets follows from it.
=============================================================================

Why out of sample. Mean-variance is optimal IN sample by construction - it
solves for exactly that. Any in-sample comparison is therefore rigged in its
favour and tells you nothing. The interesting question is what happens to
those weights on data the optimiser never saw.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from hrp import hrp_weights, min_variance_weights, portfolio_stats

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260808


def make_synthetic_returns(n_periods: int = 520, seed: int = SEED) -> pd.DataFrame:
    """Synthetic daily returns with block correlation.

    Four sector-like blocks. Within a block, assets share a common factor and
    are strongly correlated; across blocks they are nearly independent. This
    is the structure hierarchical clustering is designed to exploit, and the
    structure that makes a sample covariance matrix ill-conditioned.
    """
    rng = np.random.default_rng(seed)

    blocks = {'TECH': 6, 'FIN': 5, 'ENERGY': 4, 'STAPLE': 5}
    market = rng.normal(0, 0.008, n_periods)        # common market factor

    cols, data = [], []
    for block, count in blocks.items():
        factor = rng.normal(0, 0.010, n_periods)    # block factor
        for i in range(count):
            beta_m = rng.uniform(0.6, 1.3)
            beta_b = rng.uniform(0.7, 1.2)
            idio = rng.normal(0, rng.uniform(0.006, 0.018), n_periods)
            data.append(beta_m * market + beta_b * factor + idio)
            cols.append(f'{block}_{i + 1}')

    return pd.DataFrame(np.array(data).T, columns=cols,
                        index=pd.date_range('2022-01-03', periods=n_periods,
                                            freq='B'))


def main() -> int:
    rets = make_synthetic_returns()
    split = 120          # ~6 months: n_periods only 6x n_assets
    in_s, out_s = rets.iloc[:split], rets.iloc[split:]

    print('=' * 74)
    print('HRP vs mean-variance  --  SYNTHETIC DATA, NOT REAL MARKET DATA')
    print('=' * 74)
    print(f'assets           : {rets.shape[1]}')
    print(f'in-sample        : {len(in_s)} periods  ({in_s.index[0].date()} -> {in_s.index[-1].date()})')
    print(f'out-of-sample    : {len(out_s)} periods  ({out_s.index[0].date()} -> {out_s.index[-1].date()})')

    corr = in_s.corr().values
    off = corr[~np.eye(len(corr), dtype=bool)]
    cond = np.linalg.cond(in_s.cov().values)
    print(f'mean |corr|      : {np.abs(off).mean():.3f}')
    print(f'cov condition no : {cond:,.0f}   (high = inversion is unstable)')
    print()

    allocators = {
        'HRP (single)':       lambda d: hrp_weights(d, method='single'),
        'HRP (ward)':         lambda d: hrp_weights(d, method='ward'),
        'MinVar':             lambda d: min_variance_weights(d),
        'MinVar long-only':   lambda d: min_variance_weights(d, long_only=True),
        'MinVar shrunk 0.3':  lambda d: min_variance_weights(d, shrinkage=0.3),
        'Equal weight':       lambda d: pd.Series(1 / d.shape[1], index=d.columns),
    }

    weights, rows = {}, []
    for name, fn in allocators.items():
        w = fn(in_s)
        weights[name] = w
        s_in = portfolio_stats(w, in_s)
        s_out = portfolio_stats(w, out_s)
        rows.append({
            'allocator':      name,
            'vol_in':         round(s_in['annual_vol'], 4),
            'vol_out':        round(s_out['annual_vol'], 4),
            'vol_drift_pct':  round(100 * (s_out['annual_vol'] / s_in['annual_vol'] - 1), 1),
            'sharpe_out':     round(s_out['sharpe'], 3),
            'maxdd_out':      round(s_out['max_drawdown'], 4),
            'max_weight':     round(s_in['max_weight'], 4),
            'short_weight':   round(s_in['short_weight'], 4),
            'herfindahl':     round(s_in['herfindahl'], 4),
            'n_effective':    round(s_in['n_effective'], 2),
        })

    df = pd.DataFrame(rows)
    print('Fixed weights fitted in sample, measured out of sample:')
    print(df.to_string(index=False))

    print('\nConcentration (in-sample weights):')
    print(f"  {'allocator':<20}{'max w':>9}{'short':>9}{'eff. N':>9}")
    for r in rows:
        print(f"  {r['allocator']:<20}{r['max_weight']:>9.3f}"
              f"{r['short_weight']:>9.3f}{r['n_effective']:>9.2f}")

    hrp_row = next(r for r in rows if r['allocator'] == 'HRP (single)')
    mv_row = next(r for r in rows if r['allocator'] == 'MinVar')
    print(f"\nOut-of-sample volatility: HRP {hrp_row['vol_out']:.4f} "
          f"vs MinVar {mv_row['vol_out']:.4f}")
    print(f"Volatility drift in->out: HRP {hrp_row['vol_drift_pct']:+.1f}% "
          f"vs MinVar {mv_row['vol_drift_pct']:+.1f}%")
    print('\nThis is ONE synthetic panel and one seed. It illustrates the '
          'estimation-error\nmechanism; it is not evidence that HRP beats '
          'mean-variance in general.')

    os.makedirs(os.path.join(HERE, 'outputs'), exist_ok=True)
    df.to_csv(os.path.join(HERE, 'outputs', 'comparison.csv'), index=False)
    pd.DataFrame(weights).round(5).to_csv(
        os.path.join(HERE, 'outputs', 'weights.csv'))
    rets.round(6).to_csv(os.path.join(HERE, 'sample_returns.csv'))
    print(f"\nwrote outputs/comparison.csv, outputs/weights.csv, "
          f"sample_returns.csv")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
