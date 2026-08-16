# Hierarchical Risk Parity (HRP)

Runnable reference implementation for the QuantMedia research paper
[Hierarchical Risk Parity](https://quantmedia.io/paper-hierarchical-risk-parity.html).
Plain-language comparison:
[HRP vs mean-variance](https://quantmedia.io/learn/hrp-vs-mean-variance.html)

---

## What problem does HRP solve?

Mean-variance optimisation solves for weights using the **inverse** covariance
matrix. Sample covariance matrices are close to singular when assets are
correlated — which they are, especially in stress — and inverting a
near-singular matrix amplifies estimation noise. The symptoms are well
documented: extreme weights, concentration in a few names, and portfolios that
reshuffle completely given one extra month of data.

HRP never inverts anything, and needs no expected-return vector — which
sidesteps the hardest quantity in finance to estimate.

## Method implemented

**1. Tree clustering.** Correlations become a proper distance metric:

```
d(i,j) = sqrt( 0.5 * (1 - rho(i,j)) )
```

This satisfies the triangle inequality (raw `1 - rho` does not), so clustering
operates on a genuine metric space. Then `scipy.cluster.hierarchy.linkage`.

**2. Quasi-diagonalisation.** Walk the linkage tree, replacing each cluster id
with its children until only leaves remain. Correlated assets end up adjacent
and large covariance entries move toward the diagonal.

**3. Recursive bisection.** Walk the tree top-down. At each split, allocate
between the two sub-clusters inversely to their variance:

```
alpha = 1 - Var(left) / ( Var(left) + Var(right) )
```

The riskier side gets less. Weights are positive by construction and sum to 1,
so HRP as specified is **long-only**.

## Installation

```bash
cd quantmedia-research/hierarchical-risk-parity
pip install -r requirements.txt
```

Python 3.9+, numpy, pandas, scipy. No network access, no API key.

## Input schema

A `pandas.DataFrame` of periodic returns — one column per asset, one row per
period, no NaNs. Decimal returns (`0.012` = 1.2%), not percentages.

## Usage

```python
import pandas as pd
from hrp import hrp_weights, min_variance_weights, portfolio_stats

returns = pd.read_csv('sample_returns.csv', index_col=0, parse_dates=True)

w = hrp_weights(returns, method='single')
print(w.sort_values(ascending=False).head())
print('sum:', w.sum())                      # 1.0

print(portfolio_stats(w, returns))
```

Building blocks are exported individually: `correlation_distance`,
`quasi_diagonalise`, `inverse_variance_weights`, `cluster_variance`,
`recursive_bisection`.

## Example

```bash
python compare_mvo.py
```

Fits every allocator on a 120-period in-sample window, then measures the
**fixed** weights on 400 unseen periods. In-sample comparison would be
meaningless: mean-variance is optimal in sample by construction.

### Expected output

Reproducible from seed `20260808`:

```
assets           : 20
in-sample        : 120 periods
out-of-sample    : 400 periods
mean |corr|      : 0.240

        allocator  vol_in  vol_out  vol_drift_pct  sharpe_out  max_weight  short_weight  n_effective
     HRP (single)  0.1401   0.1419            1.3      -0.015      0.1059        0.0000        16.29
       HRP (ward)  0.1419   0.1425            0.4      -0.029      0.1097        0.0000        16.73
           MinVar  0.1311   0.1489           13.6      -0.341      0.2287       -0.1115         7.37
 MinVar long-only  0.1325   0.1460           10.2      -0.256      0.2058        0.0000         9.54
MinVar shrunk 0.3  0.1330   0.1432            7.7      -0.244      0.1689       -0.0193        11.78
     Equal weight  0.1474   0.1443           -2.1      -0.224      0.0500        0.0000        20.00
```

**How to read this.**

- MinVar achieves the lowest **in-sample** volatility (0.1311). It is supposed
  to — that is what it solves for.
- Out of sample its volatility rises **13.6%**, while HRP's rises **1.3%**.
  That gap is the estimation-error cost, and it is the whole point.
- MinVar concentrates: max weight 22.9%, an 11.2% short book, and an effective
  breadth of 7.4 names out of 20. HRP holds 16.3 effective names with no
  shorts.
- **Shrinkage closes much of the gap** (drift 7.7%, effective N 11.8). A
  regularised mean-variance portfolio is a far stronger opponent than the
  textbook version, and any comparison omitting that row is unfair to MVO.
- Every out-of-sample Sharpe is negative because the synthetic panel has no
  drift by construction. This example is about **risk control**, not returns.

Writes `outputs/comparison.csv`, `outputs/weights.csv` and `sample_returns.csv`.

## About the sample data

> **The return panel is synthetic.** Generated from a fixed seed with a
> deliberate four-block correlation structure so the clustering step has
> something to find. It is **not** real market data and no conclusion about
> real assets follows from it.

## Limitations

- **HRP is not universally better.** It is sub-optimal in sample *by
  construction*. The claim supported here is narrower: lower out-of-sample
  volatility drift and lower concentration on correlated universes where the
  covariance matrix is poorly estimated.
- **One panel, one seed.** The example illustrates a mechanism; it is not
  evidence. Vary the seed, the block structure and the window before drawing
  conclusions.
- **Linkage method is a free parameter.** `single` (the paper's choice) and
  `ward` give different trees and different weights — both are shown above so
  the sensitivity is visible rather than hidden.
- **No return objective.** HRP allocates risk. If you have genuine return
  forecasts, discarding them is a real cost.
- **Correlations converge in crises**, flattening the tree exactly when
  diversification matters most.

## Tests

```bash
cd quantmedia-research
python tests/test_hrp.py
```

Covers: weights sum to 1, no negatives, deterministic output on a fixed seed,
distance-metric properties, quasi-diagonalisation ordering, recursive
allocation, and input validation.

## Research reference

**QuantMedia (2026).** *Hierarchical Risk Parity: Portfolio Construction
Without Matrix Inversion.*
https://quantmedia.io/paper-hierarchical-risk-parity.html

Primary sources:

- López de Prado, M. (2016). "Building Diversified Portfolios that Outperform
  Out of Sample." *Journal of Portfolio Management* 42(4), 59–69.
- Markowitz, H. (1952). "Portfolio Selection." *Journal of Finance* 7(1), 77–91.
- Michaud, R. (1989). "The Markowitz Optimization Enigma: Is Optimized
  Optimal?" *Financial Analysts Journal* 45(1), 31–42.
- Ledoit, O. & Wolf, M. (2004). "A Well-Conditioned Estimator for
  Large-Dimensional Covariance Matrices." *Journal of Multivariate Analysis*
  88(2), 365–411.

## Licence

Free to use and cite with attribution to QuantMedia.
