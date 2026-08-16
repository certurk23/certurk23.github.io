"""
Tests for the VPIN implementation.

    cd quantmedia-research && python tests/test_vpin.py

No pytest dependency: this must be runnable by anyone who cloned the repo and
installed only requirements.txt.
"""

from __future__ import annotations

import os
import sys
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'vpin-order-flow-toxicity'))

from vpin import (build_volume_buckets, classify_bvc, classify_tick_rule,  # noqa: E402
                  compute_vpin, sign_trades_tick_rule, vpin_from_trades)

PASSED, FAILED = [], []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f'  [ ok ] {name}')
    except Exception as e:
        FAILED.append((name, str(e)))
        print(f'  [FAIL] {name}\n         {e}')
        if not isinstance(e, AssertionError):
            print(traceback.format_exc(limit=2))


def tape(prices, volumes=None):
    volumes = volumes if volumes is not None else [100] * len(prices)
    return pd.DataFrame({'price': list(map(float, prices)), 'volume': volumes})


# ---------------------------------------------------------------------------
# Bucket construction
# ---------------------------------------------------------------------------
def test_bucket_volume_is_exact():
    """Every completed bucket must hold exactly bucket_size volume."""
    b = build_volume_buckets(tape([100] * 100), bucket_size=250)
    assert len(b) == 40, len(b)
    assert (b['volume'] == 250).all(), b['volume'].unique()


def test_bucket_splits_trades_across_boundaries():
    """A trade larger than the bucket must be split, not dropped or duplicated."""
    b = build_volume_buckets(tape([100], [1000]), bucket_size=250)
    assert len(b) == 4, f'one 1000-lot trade at size 250 -> 4 buckets, got {len(b)}'
    assert b['volume'].sum() == 1000


def test_bucket_conserves_volume():
    rng = np.random.default_rng(7)
    vols = rng.integers(1, 500, 500)
    t = tape(100 + rng.normal(0, 1, 500), vols.tolist())
    b = build_volume_buckets(t, bucket_size=1000)
    consumed = b['volume'].sum()
    assert consumed <= vols.sum(), 'buckets cannot hold more than the tape'
    assert vols.sum() - consumed < 1000, 'at most one partial bucket discarded'


def test_partial_final_bucket_discarded():
    """999 of 1000 volume: no complete bucket, so no rows."""
    b = build_volume_buckets(tape([100] * 9, [111] * 9), bucket_size=1000)
    assert b.empty, f'expected no complete bucket, got {len(b)}'


def test_rejects_bad_input():
    for bad, why in (
        (lambda: build_volume_buckets(tape([100]), 0), 'zero bucket_size'),
        (lambda: build_volume_buckets(tape([100]), -5), 'negative bucket_size'),
        (lambda: build_volume_buckets(pd.DataFrame({'price': [1]}), 10),
         'missing volume column'),
        (lambda: build_volume_buckets(tape([100], [-5]), 10), 'negative volume'),
    ):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError(f'should have raised for {why}')


# ---------------------------------------------------------------------------
# Classification and VPIN
# ---------------------------------------------------------------------------
def test_monotone_tape_is_fully_one_sided():
    """REGRESSION. A steadily rising tape has zero dispersion in its price
    changes. An earlier revision took that as 'no information' and split
    volume 50/50, returning VPIN = 0 for a perfectly one-sided tape."""
    r = vpin_from_trades(tape(np.arange(1, 501) * 1.0), bucket_size=1000,
                         window=10)
    last = r['vpin'].iloc[-1]
    assert last > 0.99, f'monotone tape should give VPIN ~1, got {last}'


def test_flat_tape_is_balanced():
    r = vpin_from_trades(tape([100.0] * 500), bucket_size=1000, window=10)
    assert r['vpin'].iloc[-1] == 0.0, r['vpin'].iloc[-1]


def test_vpin_is_bounded():
    rng = np.random.default_rng(11)
    t = tape(100 + np.cumsum(rng.normal(0, 0.05, 3000)),
             rng.integers(50, 500, 3000).tolist())
    for method in ('bvc', 'tick'):
        v = vpin_from_trades(t, bucket_size=5000, window=20,
                             method=method)['vpin'].dropna()
        assert (v >= 0).all() and (v <= 1).all(), f'{method} out of [0,1]'


def test_buy_and_sell_volume_sum_to_bucket():
    rng = np.random.default_rng(3)
    t = tape(100 + np.cumsum(rng.normal(0, 0.05, 2000)))
    for classify, prep in ((classify_bvc, lambda x: x),
                           (classify_tick_rule, sign_trades_tick_rule)):
        b = build_volume_buckets(prep(t), bucket_size=2000)
        c = classify(b)
        diff = (c['buy_volume'] + c['sell_volume'] - c['volume']).abs().max()
        assert diff < 1e-6, f'{classify.__name__}: buy+sell != volume ({diff})'
        assert (c['buy_volume'] >= -1e-9).all(), 'negative buy volume'
        assert (c['sell_volume'] >= -1e-9).all(), 'negative sell volume'


def test_tick_rule_signs():
    signed = sign_trades_tick_rule(tape([100, 101, 102, 101, 101, 100]))
    assert list(signed['sign']) == [1.0, 1.0, 1.0, -1.0, -1.0, -1.0], \
        list(signed['sign'])


def test_window_longer_than_data_returns_nan():
    b = build_volume_buckets(tape([100] * 50), bucket_size=1000)
    v = compute_vpin(classify_bvc(b), window=999)
    assert v.isna().all(), 'insufficient buckets must yield NaN, not a value'


def test_window_must_be_positive():
    b = classify_bvc(build_volume_buckets(tape([100] * 100), 1000))
    try:
        compute_vpin(b, window=0)
    except ValueError:
        return
    raise AssertionError('window=0 should raise')


def test_no_complete_buckets_raises():
    try:
        vpin_from_trades(tape([100], [5]), bucket_size=1_000_000)
    except ValueError as e:
        assert 'bucket' in str(e).lower()
        return
    raise AssertionError('should raise when no bucket completes')


def test_deterministic():
    """Same input, same output - a reproducibility package must be exact."""
    rng = np.random.default_rng(42)
    t = tape(100 + np.cumsum(rng.normal(0, 0.05, 2000)))
    a = vpin_from_trades(t, bucket_size=5000, window=10)['vpin']
    b = vpin_from_trades(t, bucket_size=5000, window=10)['vpin']
    pd.testing.assert_series_equal(a, b)


def test_unknown_method_rejected():
    try:
        vpin_from_trades(tape([100] * 100), 1000, method='magic')
    except ValueError:
        return
    raise AssertionError("unknown method should raise")


def main():
    print('=' * 62)
    print('VPIN implementation tests')
    print('=' * 62)
    for name, fn in [
        ('bucket volume is exact',            test_bucket_volume_is_exact),
        ('trades split across boundaries',    test_bucket_splits_trades_across_boundaries),
        ('bucket conserves volume',           test_bucket_conserves_volume),
        ('partial final bucket discarded',    test_partial_final_bucket_discarded),
        ('rejects bad input',                 test_rejects_bad_input),
        ('monotone tape fully one-sided',     test_monotone_tape_is_fully_one_sided),
        ('flat tape balanced',                test_flat_tape_is_balanced),
        ('VPIN bounded in [0,1]',             test_vpin_is_bounded),
        ('buy+sell == bucket volume',         test_buy_and_sell_volume_sum_to_bucket),
        ('tick rule signs',                   test_tick_rule_signs),
        ('window > data -> NaN',              test_window_longer_than_data_returns_nan),
        ('window must be positive',           test_window_must_be_positive),
        ('no complete buckets raises',        test_no_complete_buckets_raises),
        ('deterministic',                     test_deterministic),
        ('unknown method rejected',           test_unknown_method_rejected),
    ]:
        check(name, fn)
    print(f'\n{len(PASSED)} passed, {len(FAILED)} failed')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
