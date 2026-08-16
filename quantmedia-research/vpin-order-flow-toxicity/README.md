# VPIN — Volume-Synchronized Probability of Informed Trading

Runnable reference implementation for the QuantMedia research paper
[VPIN & Order Flow Toxicity](https://quantmedia.io/paper-vpin-order-flow-toxicity.html).
Plain-language explainer: [What is VPIN?](https://quantmedia.io/learn/what-is-vpin.html)

---

## What is VPIN?

VPIN estimates how **toxic** order flow is — how likely it is that the
counterparties trading against a liquidity provider are better informed. It
splits trading into equal-*volume* buckets rather than equal-*time* intervals,
classifies each bucket's volume as buy- or sell-initiated, and averages the
absolute imbalance over a rolling window.

Readings near 1 mean persistently one-sided flow. Readings near 0 mean
balanced flow. VPIN uses the **absolute** imbalance, so it says nothing about
direction — a heavily bought and a heavily sold bucket contribute identically.

## Method implemented

**1. Equal-volume buckets.** Trades accumulate until a fixed volume `V` is
reached, then the bucket closes. Clock-based windows mix a frantic minute at
the open with a quiet hour at midday; volume buckets make every observation
represent the same economic activity. A trade straddling a boundary is split
proportionally, so no volume is lost.

**2. Buy/sell classification.** Exchange tapes do not label trades as buyer- or
seller-initiated, so the split is inferred. Two methods:

- **Bulk Volume Classification (default)** — what the original paper uses.
  Assigns a *fraction* of each bucket to buys via a Student-t CDF of the
  standardised price change:
  `Vb_i = V * T((P_i − P_{i−1}) / σ_ΔP ; dof)`. Robust to timestamp noise and
  out-of-sequence prints.
- **Tick rule** — classifies each trade by price against the previous trade.
  Simpler, but degrades when quotes move faster than trades are reported.

**3. VPIN.**

```
VPIN_t  =   Σ |Vb_i − Vs_i|  over the last n buckets
            ────────────────────────────────────────
                  Σ V_i      over the same buckets
```

Bounded in `[0, 1]`.

## Installation

```bash
cd quantmedia-research/vpin-order-flow-toxicity
pip install -r requirements.txt
```

Requires Python 3.9+, numpy, pandas, scipy. No network access, no API key.

## Input schema

A `pandas.DataFrame` ordered by time:

| column      | type            | required | notes                                  |
|-------------|-----------------|----------|----------------------------------------|
| `price`     | float           | yes      | trade price                            |
| `volume`    | float / int     | yes      | trade size, non-negative               |
| `timestamp` | datetime        | no       | carried through to bucket start/end    |
| `sign`      | float (+1 / −1) | no       | only for the tick-rule path            |

## Usage

```python
import pandas as pd
from vpin import vpin_from_trades

trades = pd.read_csv('sample_data/sample_trades.csv', parse_dates=['timestamp'])

out = vpin_from_trades(
    trades,
    bucket_size=21_376,   # volume per bucket
    window=50,            # buckets in the rolling window
    method='bvc',         # or 'tick'
    dof=3,                # Student-t degrees of freedom (BVC only)
)

print(out[['bucket_id', 'close_price', 'buy_volume', 'sell_volume', 'vpin']].tail())
```

Lower-level building blocks are exported too: `build_volume_buckets`,
`classify_bvc`, `classify_tick_rule`, `sign_trades_tick_rule`, `compute_vpin`.

## Example

```bash
python example.py
```

### Expected output

Reproducible from seed `20260808`:

```
====================================================================
VPIN example  --  SYNTHETIC DATA, NOT REAL MARKET DATA
====================================================================
trades          : 20,000
total volume    : 5,344,047
bucket size     : 21,376
rolling window  : 50 buckets
price range     : 99.87 - 115.20

[BVC ] buckets=250  VPIN mean=0.4410  min=0.2805  max=0.8257
[TICK] buckets=250  VPIN mean=0.1779  min=0.1247  max=0.2918

volume in buckets : 5,344,000 (100.0% of tape; remainder is the incomplete
                    final bucket, discarded by design)

mean VPIN, balanced regime : 0.3292
mean VPIN, informed regime : 0.6376
ratio                      : 1.94x
```

The synthetic tape plants a one-sided buying episode between trades 8,000 and
12,000. VPIN roughly doubles through it and decays afterwards, which is the
behaviour the measure is supposed to exhibit.

Note the two methods produce very different **levels** (0.44 vs 0.18 mean) on
identical data. That is not a bug — it is the single most important practical
caveat about VPIN, and the reason absolute readings are meaningless without
stating the classification method, bucket size and window.

Writes `outputs/example_output.csv` (per-bucket results) and
`sample_data/sample_trades.csv` (first 2,000 rows of the tape).

## About the sample data

> **The sample data is synthetic.** It is generated from a fixed random seed by
> `make_synthetic_trades()` in `example.py`. It is **not** real market data, not
> a recording of any actual instrument, and no conclusion about any real
> security can be drawn from it. It exists so the implementation can be run and
> verified end-to-end without a paid tick-data subscription.

## Limitations

- **Contested predictive value.** VPIN's role in the 2010 Flash Crash is
  actively disputed — see Andersen & Bondarenko (2014), who argue much of its
  apparent forecasting power reflects volume–volatility mechanics rather than
  information. Treat it as a descriptive microstructure statistic, not an
  established early-warning indicator.
- **Highly parameter-dependent.** Bucket size, window length, classification
  method and `dof` all move the level, as the example above shows directly.
- **Needs tick or bar data.** VPIN cannot be computed from end-of-day OHLCV.
  **QuantMedia does not publish a live VPIN reading** for exactly this reason:
  the production pipeline collects daily bars, not order flow, and estimating
  it anyway would be fabrication.
- **Relative, not absolute.** A reading is interpretable against the same
  instrument's own recent history, not against a universal threshold.
- **Degenerate tapes.** A tape with zero price-change dispersion is handled
  explicitly: a flat tape splits 50/50, while a perfectly steady drift is
  classified fully one-sided. (An earlier revision split both evenly, which
  returned VPIN = 0 for a monotonically rising tape — the opposite of correct.
  `tests/test_vpin.py::test_monotone_tape_is_fully_one_sided` guards it.)

## Tests

```bash
cd quantmedia-research
python tests/test_vpin.py
```

Covers bucket construction and volume conservation, boundary splitting, both
classification methods, VPIN bounds, the degenerate-tape cases and input
validation.

## Research reference

**QuantMedia (2026).** *VPIN & Order Flow Toxicity: A Practical Microstructure
Signal.* https://quantmedia.io/paper-vpin-order-flow-toxicity.html

Primary sources:

- Easley, D., López de Prado, M. & O'Hara, M. (2012). "Flow Toxicity and
  Liquidity in a High-Frequency World." *Review of Financial Studies* 25(5),
  1457–1493. [doi:10.1093/rfs/hhs053](https://doi.org/10.1093/rfs/hhs053)
- Easley, D., López de Prado, M. & O'Hara, M. (2011). "The Microstructure of
  the Flash Crash." *Journal of Portfolio Management* 37(2), 118–128.
- Andersen, T. & Bondarenko, O. (2014). "VPIN and the Flash Crash."
  *Journal of Financial Markets* 17, 1–46.
  [doi:10.1016/j.finmar.2013.05.005](https://doi.org/10.1016/j.finmar.2013.05.005)
- Lee, C. & Ready, M. (1991). "Inferring Trade Direction from Intraday Data."
  *Journal of Finance* 46(2), 733–746.

## Licence

Free to use and cite with attribution to QuantMedia.
