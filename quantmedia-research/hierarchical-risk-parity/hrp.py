"""
Hierarchical Risk Parity (HRP)
==============================
Reference implementation for the QuantMedia research paper:
https://quantmedia.io/paper-hierarchical-risk-parity.html

Follows López de Prado (2016), "Building Diversified Portfolios that Outperform
Out of Sample", Journal of Portfolio Management 42(4).

Why it exists
-------------
Mean-variance optimisation solves for weights using the INVERSE covariance
matrix. Sample covariance matrices are close to singular when assets are
correlated - which they are, especially in stress - and inverting a
near-singular matrix amplifies estimation noise enormously. The symptoms are
well documented: extreme weights, concentration in a handful of names, and
portfolios that reshuffle completely on one extra month of data.

HRP never inverts anything. It clusters assets by correlation, reorders the
covariance matrix so related assets sit adjacent, then splits risk down the
resulting tree. It also needs no expected-return vector, which sidesteps the
hardest quantity in finance to estimate.

The three steps
---------------
1. TREE CLUSTERING       correlation -> distance -> hierarchical linkage
2. QUASI-DIAGONALISATION reorder so similar assets are adjacent
3. RECURSIVE BISECTION   split risk top-down, inversely to cluster variance

Requires: numpy, pandas, scipy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform

__all__ = ['correlation_distance', 'quasi_diagonalise', 'inverse_variance_weights',
           'cluster_variance', 'recursive_bisection', 'hrp_weights',
           'min_variance_weights', 'portfolio_stats']


# ---------------------------------------------------------------------------
# 1. Correlation distance
# ---------------------------------------------------------------------------
def correlation_distance(corr: pd.DataFrame) -> pd.DataFrame:
    """Convert a correlation matrix to a proper distance metric.

        d(i,j) = sqrt( 0.5 * (1 - rho(i,j)) )

    This satisfies the triangle inequality, which raw (1 - rho) does not, so
    the hierarchical clustering below is operating on a genuine metric space.
    Perfectly correlated assets are at distance 0, perfectly anti-correlated
    at distance 1.
    """
    # Build from a fresh array: pandas 3.x hands back read-only views, so
    # fill_diagonal on .values raises there while working on pandas 2.x.
    vals = np.sqrt(np.clip(0.5 * (1.0 - np.asarray(corr, dtype=float)), 0.0, 1.0))
    vals = np.array(vals, copy=True)
    np.fill_diagonal(vals, 0.0)
    vals = 0.5 * (vals + vals.T)        # enforce exact symmetry for squareform
    return pd.DataFrame(vals, index=corr.index, columns=corr.columns)


# ---------------------------------------------------------------------------
# 2. Quasi-diagonalisation
# ---------------------------------------------------------------------------
def quasi_diagonalise(link: np.ndarray) -> list[int]:
    """Return original asset indices ordered so correlated assets sit adjacent.

    Walks the scipy linkage matrix, repeatedly replacing each cluster id with
    its two children until only original leaves remain.
    """
    link = link.astype(int)
    n_items = link[-1, 3]                       # total leaves in the last merge
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])

    while sort_ix.max() >= n_items:             # while clusters remain
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)   # make space
        df0 = sort_ix[sort_ix >= n_items]                   # find clusters
        i, j = df0.index, df0.values - n_items
        sort_ix[i] = link[j, 0]                             # left child
        df1 = pd.Series(link[j, 1], index=i + 1)            # right child
        sort_ix = pd.concat([sort_ix, df1]).sort_index()
        sort_ix.index = range(sort_ix.shape[0])

    return sort_ix.tolist()


# ---------------------------------------------------------------------------
# 3. Recursive bisection
# ---------------------------------------------------------------------------
def inverse_variance_weights(cov: pd.DataFrame) -> np.ndarray:
    """Inverse-variance portfolio using only the diagonal - no inversion."""
    ivp = 1.0 / np.diag(cov.values)
    return ivp / ivp.sum()


def cluster_variance(cov: pd.DataFrame, items: list) -> float:
    """Variance of a sub-cluster weighted by inverse variance."""
    sub = cov.loc[items, items]
    w = inverse_variance_weights(sub).reshape(-1, 1)
    return float((w.T @ sub.values @ w)[0, 0])


def recursive_bisection(cov: pd.DataFrame, sorted_items: list) -> pd.Series:
    """Allocate top-down, splitting each pair of sub-clusters inversely to
    their variance:

        alpha = 1 - Var(left) / ( Var(left) + Var(right) )

    The riskier side gets less. Weights are positive by construction and sum
    to 1, so HRP as specified is long-only.
    """
    w = pd.Series(1.0, index=sorted_items, dtype=float)
    clusters = [sorted_items]

    while clusters:
        # Bisect every cluster with more than one member.
        clusters = [c[k:l] for c in clusters
                    for k, l in ((0, len(c) // 2), (len(c) // 2, len(c)))
                    if len(c) > 1]
        for i in range(0, len(clusters), 2):
            left, right = clusters[i], clusters[i + 1]
            v_left = cluster_variance(cov, left)
            v_right = cluster_variance(cov, right)
            alpha = 1.0 - v_left / (v_left + v_right)
            w[left] *= alpha
            w[right] *= 1.0 - alpha
    return w


def hrp_weights(returns: pd.DataFrame,
                method: str = 'single') -> pd.Series:
    """Full HRP pipeline: returns -> weights.

    Parameters
    ----------
    returns : DataFrame of periodic returns, one column per asset.
    method  : scipy linkage method. 'single' is the original paper's choice.
              'average' and 'ward' give different trees and therefore
              different weights - this is a modelling choice, not a detail.

    Returns a Series of weights indexed by asset, summing to 1.
    """
    if returns.shape[1] < 2:
        raise ValueError('need at least 2 assets')
    if returns.isna().any().any():
        raise ValueError('returns contain NaN; clean or fill before calling')

    cov = returns.cov()
    corr = returns.corr()

    dist = correlation_distance(corr)
    link = linkage(squareform(dist.values, checks=False), method=method)

    order = quasi_diagonalise(link)
    sorted_items = [corr.index[i] for i in order]

    w = recursive_bisection(cov, sorted_items)
    return w.reindex(returns.columns).astype(float)


# ---------------------------------------------------------------------------
# Comparison baseline
# ---------------------------------------------------------------------------
def min_variance_weights(returns: pd.DataFrame,
                         long_only: bool = False,
                         shrinkage: float = 0.0) -> pd.Series:
    """Classical minimum-variance portfolio: w = (S^-1 1) / (1' S^-1 1).

    This is the textbook mean-variance solution with no return forecast, so it
    isolates exactly the property HRP targets: sensitivity to inverting a
    noisy covariance matrix.

    ``shrinkage`` blends the sample covariance toward a diagonal target
    (a simple stand-in for Ledoit-Wolf), because comparing HRP against a
    completely un-regularised optimiser overstates the case for HRP.
    ``long_only`` clips negatives and renormalises - crude, but it shows how
    much of the raw solution was short.
    """
    cov = returns.cov()
    if shrinkage > 0:
        target = np.diag(np.diag(cov.values))
        cov = pd.DataFrame((1 - shrinkage) * cov.values + shrinkage * target,
                           index=cov.index, columns=cov.columns)

    inv = np.linalg.pinv(cov.values)            # pinv: survives singularity
    ones = np.ones(len(cov))
    w = inv @ ones
    w = w / w.sum()

    if long_only:
        w = np.clip(w, 0, None)
        w = w / w.sum() if w.sum() > 0 else np.full(len(w), 1 / len(w))

    return pd.Series(w, index=returns.columns)


def portfolio_stats(weights: pd.Series, returns: pd.DataFrame,
                    periods_per_year: int = 252) -> dict:
    """Realised statistics for a fixed weight vector over ``returns``."""
    w = weights.reindex(returns.columns).fillna(0.0).values
    port = returns.values @ w
    vol = float(np.std(port, ddof=1) * np.sqrt(periods_per_year))
    mean = float(np.mean(port) * periods_per_year)

    equity = np.cumprod(1.0 + port)
    drawdown = float((equity / np.maximum.accumulate(equity) - 1.0).min())

    active = w[np.abs(w) > 1e-10]
    return {
        'annual_return': mean,
        'annual_vol': vol,
        'sharpe': mean / vol if vol > 0 else float('nan'),
        'max_drawdown': drawdown,
        'max_weight': float(np.max(w)),
        'min_weight': float(np.min(w)),
        'short_weight': float(np.sum(w[w < 0])),
        'n_effective': float(1.0 / np.sum(w ** 2)) if np.sum(w ** 2) > 0 else 0.0,
        'herfindahl': float(np.sum(w ** 2)),
        'n_active': int(len(active)),
    }
