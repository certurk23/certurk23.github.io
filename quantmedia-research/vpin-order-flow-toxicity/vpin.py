"""
VPIN — Volume-Synchronized Probability of Informed Trading
===========================================================
Reference implementation for the QuantMedia research paper:
https://quantmedia.io/paper-vpin-order-flow-toxicity.html

Implements the measure as described in Easley, Lopez de Prado & O'Hara (2012),
"Flow Toxicity and Liquidity in a High-Frequency World", RFS 25(5).

The three steps, and why each exists
------------------------------------
1. EQUAL-VOLUME BUCKETS. Trades are accumulated until a fixed volume V is
   reached, then the bucket closes. Buckets are *not* time-based: in modern
   markets a minute at the open can carry more volume than an hour at midday,
   so clock windows mix frantic and quiet periods into one observation. Volume
   buckets make every observation represent the same economic activity. A trade
   straddling a boundary is split across buckets so no volume is lost.

2. BUY/SELL CLASSIFICATION. Exchange tapes do not label trades as buyer- or
   seller-initiated, so the split must be inferred. Two methods are provided:

     - BULK VOLUME CLASSIFICATION (default, and what the original paper uses).
       Rather than classifying each print, it assigns a *fraction* of each
       bucket's volume to buys using the standardised price change through a
       Student-t CDF. Robust to timestamp noise and to trades reported out of
       sequence.

     - TICK RULE. Classifies each trade by comparing its price to the previous
       trade. Simpler and more intuitive, but degrades when quotes move faster
       than trades are reported.

3. VPIN. The average absolute order imbalance across a rolling window of
   buckets, normalised by bucket size, so the result lies in [0, 1].

           VPIN = (1 / (n*V)) * sum over n buckets of |Vb_i - Vs_i|

Requires: numpy, pandas. No network access, no API keys.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

__all__ = ['build_volume_buckets', 'classify_bvc', 'classify_tick_rule',
           'compute_vpin', 'vpin_from_trades']


# ---------------------------------------------------------------------------
# 1. Equal-volume bucket construction
# ---------------------------------------------------------------------------
def build_volume_buckets(trades: pd.DataFrame, bucket_size: float) -> pd.DataFrame:
    """Split a trade tape into equal-volume buckets.

    Parameters
    ----------
    trades : DataFrame with columns ``price`` and ``volume``, ordered by time.
             A ``timestamp`` column is carried through if present.
    bucket_size : volume per bucket, in the same units as ``volume``.

    Returns
    -------
    DataFrame, one row per COMPLETED bucket, with columns:
        bucket_id, open_price, close_price, volume, n_trades,
        signed_volume (only when the input carries a tick-rule ``sign``),
        start_time / end_time when timestamps were supplied.

    A trade that straddles a boundary is split proportionally, so the sum of
    bucket volumes equals the consumed input volume exactly. Any residual
    volume after the last complete bucket is discarded: a partial bucket is
    not comparable to a full one and including it would bias VPIN.
    """
    if bucket_size <= 0:
        raise ValueError('bucket_size must be positive')
    for col in ('price', 'volume'):
        if col not in trades.columns:
            raise ValueError(f'trades is missing required column {col!r}')
    if (trades['volume'] < 0).any():
        raise ValueError('negative volume in trades')

    has_time = 'timestamp' in trades.columns
    has_sign = 'sign' in trades.columns

    buckets: list[dict] = []
    cur_vol = 0.0
    cur_signed = 0.0
    cur_trades = 0
    cur_open = None
    cur_start = None
    last_price = None

    for row in trades.itertuples(index=False):
        remaining = float(row.volume)
        price = float(row.price)
        sign = float(getattr(row, 'sign', 0.0)) if has_sign else 0.0
        ts = getattr(row, 'timestamp', None) if has_time else None

        while remaining > 0:
            if cur_open is None:
                cur_open, cur_start = price, ts
            take = min(remaining, bucket_size - cur_vol)
            cur_vol += take
            cur_signed += sign * take
            remaining -= take
            last_price = price
            # Count a trade once, against the bucket it starts in.
            if take > 0 and remaining + take == float(row.volume):
                cur_trades += 1

            if cur_vol >= bucket_size - 1e-9:      # bucket complete
                rec = {
                    'bucket_id': len(buckets),
                    'open_price': cur_open,
                    'close_price': last_price,
                    'volume': cur_vol,
                    'n_trades': cur_trades,
                }
                if has_sign:
                    rec['signed_volume'] = cur_signed
                if has_time:
                    rec['start_time'], rec['end_time'] = cur_start, ts
                buckets.append(rec)
                cur_vol = cur_signed = 0.0
                cur_trades = 0
                cur_open = cur_start = None

    return pd.DataFrame(buckets)


# ---------------------------------------------------------------------------
# 2. Buy/sell volume classification
# ---------------------------------------------------------------------------
def classify_bvc(buckets: pd.DataFrame, dof: int = 3) -> pd.DataFrame:
    """Bulk Volume Classification.

    Assigns a fraction of each bucket's volume to buys:

        Vb_i = V_i * T( (P_i - P_{i-1}) / sigma_dP ;  dof )
        Vs_i = V_i - Vb_i

    where T is the Student-t CDF. Fat tails are the point: large price moves
    should not saturate the classification the way a normal CDF does.

    ``dof`` is the degrees-of-freedom parameter; the original paper uses a
    small value (0.25 in some variants, 3 is a common practical choice).
    Published VPIN levels are NOT comparable across studies unless this,
    the bucket size and the window all match.
    """
    out = buckets.copy()
    dp = out['close_price'].diff()
    sigma = dp.std(ddof=1)

    if not np.isfinite(sigma) or sigma == 0:
        # Degenerate case: price changes have zero dispersion. That covers two
        # very different tapes and they must NOT be treated the same way.
        #   * dp == 0 everywhere (flat tape): genuinely no information, 50/50.
        #   * dp constant and non-zero (perfectly steady drift): every bucket
        #     is entirely one-sided, so the fraction is 1 or 0.
        # Splitting the second case evenly returned VPIN = 0 for a monotone
        # tape, which is exactly backwards.
        frac = pd.Series(np.where(dp > 0, 1.0, np.where(dp < 0, 0.0, 0.5)),
                         index=out.index)
    else:
        frac = pd.Series(student_t.cdf(dp / sigma, df=dof), index=out.index)
    frac.iloc[0] = 0.5          # no prior price for the first bucket

    out['buy_volume'] = out['volume'] * frac
    out['sell_volume'] = out['volume'] - out['buy_volume']
    out['order_imbalance'] = (out['buy_volume'] - out['sell_volume']).abs()
    return out


def classify_tick_rule(buckets: pd.DataFrame) -> pd.DataFrame:
    """Tick-rule classification, using signed volume accumulated per bucket.

    Requires the input trades to have carried a ``sign`` column (+1 buyer-
    initiated, -1 seller-initiated), which ``sign_trades_tick_rule`` produces.
    """
    if 'signed_volume' not in buckets.columns:
        raise ValueError('buckets lack signed_volume; pass trades with a '
                         '"sign" column (see sign_trades_tick_rule)')
    out = buckets.copy()
    # signed = Vb - Vs  and  Vb + Vs = V  ->  Vb = (V + signed)/2
    out['buy_volume'] = (out['volume'] + out['signed_volume']) / 2.0
    out['sell_volume'] = out['volume'] - out['buy_volume']
    out['order_imbalance'] = out['signed_volume'].abs()
    return out


def sign_trades_tick_rule(trades: pd.DataFrame) -> pd.DataFrame:
    """Label each trade +1/-1 by the tick rule (price vs previous price).

    Unchanged prices inherit the previous sign, which is the standard
    convention. The first trade is treated as buyer-initiated.
    """
    out = trades.copy()
    diff = out['price'].diff()
    sign = np.sign(diff).replace(0, np.nan).ffill().fillna(1.0)
    out['sign'] = sign.astype(float)
    return out


# ---------------------------------------------------------------------------
# 3. VPIN
# ---------------------------------------------------------------------------
def compute_vpin(classified: pd.DataFrame, window: int = 50) -> pd.Series:
    """Rolling VPIN over ``window`` buckets.

        VPIN_t = sum(|Vb - Vs|) over the last n buckets
                 -------------------------------------
                          sum(V) over the same buckets

    Returns a Series indexed like ``classified``; the first ``window - 1``
    entries are NaN because the window is not yet full. Bounded in [0, 1].
    """
    if window < 1:
        raise ValueError('window must be >= 1')
    if len(classified) < window:
        return pd.Series(np.nan, index=classified.index, name='vpin')

    imb = classified['order_imbalance'].rolling(window).sum()
    vol = classified['volume'].rolling(window).sum()
    vpin = (imb / vol).rename('vpin')
    return vpin.clip(0.0, 1.0)


def vpin_from_trades(trades: pd.DataFrame, bucket_size: float,
                     window: int = 50, method: str = 'bvc',
                     dof: int = 3) -> pd.DataFrame:
    """End-to-end convenience wrapper: trades -> buckets -> VPIN.

    Parameters
    ----------
    trades      : DataFrame with ``price`` and ``volume`` (``timestamp`` optional)
    bucket_size : volume per bucket
    window      : number of buckets in the rolling VPIN window
    method      : 'bvc' (default) or 'tick'
    dof         : Student-t degrees of freedom, BVC only

    Returns the bucket table with buy/sell volumes and a ``vpin`` column.
    """
    if method not in ('bvc', 'tick'):
        raise ValueError("method must be 'bvc' or 'tick'")

    if method == 'tick':
        trades = sign_trades_tick_rule(trades)

    buckets = build_volume_buckets(trades, bucket_size)
    if buckets.empty:
        raise ValueError(f'no complete buckets: total volume is below '
                         f'bucket_size={bucket_size}')

    classified = (classify_bvc(buckets, dof=dof) if method == 'bvc'
                  else classify_tick_rule(buckets))
    classified['vpin'] = compute_vpin(classified, window=window)
    return classified
