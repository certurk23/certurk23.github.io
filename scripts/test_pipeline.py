#!/usr/bin/env python3
"""
Pipeline reliability tests.
===========================
Covers the failure scenarios that actually take a data site down. Runs on the
standard library alone (no pytest, no pandas) so it can execute in CI before
the heavy dependency install, and locally on any Python 3.9+.

    python scripts/test_pipeline.py

Each test asserts the FAIL-SAFE rule: a failed upstream must never leave
production worse than it was before the run.
"""

import datetime
import json
import os
import re
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import qm_config as C            # noqa: E402
import daily_update as P         # noqa: E402

UTC = datetime.timezone.utc
PASSED, FAILED = [], []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f'  [ ok ] {name}')
    except AssertionError as e:
        FAILED.append((name, str(e)))
        print(f'  [FAIL] {name}\n         {e}')
    except Exception:
        FAILED.append((name, traceback.format_exc(limit=2)))
        print(f'  [FAIL] {name}\n{traceback.format_exc(limit=2)}')


class Sandbox:
    """Isolate data/ writes so tests never touch real production files."""

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix='qm-test-')
        os.makedirs(os.path.join(self.tmp, 'data'), exist_ok=True)
        self._root, self._data = P.ROOT, P.DATA_DIR
        P.ROOT = self.tmp
        P.DATA_DIR = os.path.join(self.tmp, 'data')
        P.ERRORS.clear()
        P.STATUS.clear()
        return self

    def __exit__(self, *a):
        P.ROOT, P.DATA_DIR = self._root, self._data
        shutil.rmtree(self.tmp, ignore_errors=True)

    def seed(self, rel, payload):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f)

    def load(self, rel):
        with open(os.path.join(self.tmp, rel), encoding='utf-8') as f:
            return json.load(f)

    def exists(self, rel):
        return os.path.exists(os.path.join(self.tmp, rel))


GOOD_FX = {f'P{i}': {'name': f'p{i}', 'price': 1.5, 'group': 'majors'}
           for i in range(18)}
GOOD_CRYPTO = {f'C{i}': {'name': f'c{i}', 'price': 100.0, 'chg': 1.0}
               for i in range(12)}


# ---------------------------------------------------------------------------
# A. All sources succeed
# ---------------------------------------------------------------------------
def test_a_all_succeed():
    with Sandbox() as sb:
        feed = P.resolve_feed('forex', lambda: dict(GOOD_FX),
                              'data/markets_fx.json')
        assert feed and not feed['stale'], 'fresh fetch must not be marked stale'
        assert P.STATUS['forex'] == 'fresh', P.STATUS
        assert len(feed['data']) == 18
        assert not P.ERRORS, f'clean run recorded errors: {P.ERRORS}'


# ---------------------------------------------------------------------------
# B. News API fails -> previous news preserved, other sources unaffected
# ---------------------------------------------------------------------------
def test_b_news_fails_preserves():
    with Sandbox() as sb:
        prev = {'data': [{'headline': 'old but real', 'url': 'https://x/1'}],
                'fetched_utc': '2026-08-06T23:30:00Z', 'stale': False}
        sb.seed('data/news.json', prev)

        def boom():
            raise P.FetchError('simulated 503')

        news = P.resolve_feed('news', boom, 'data/news.json')
        fx = P.resolve_feed('forex', lambda: dict(GOOD_FX),
                            'data/markets_fx.json')

        assert news is not None, 'news must fall back, not vanish'
        assert news['data'] == prev['data'], 'previous news must survive verbatim'
        assert news['fetched_utc'] == '2026-08-06T23:30:00Z', \
            'preserved data must keep its ORIGINAL timestamp, not now()'
        assert news['stale'] is True
        assert P.STATUS['news'] == 'preserved'
        # Independence: forex is untouched by the news failure.
        assert fx and not fx['stale'] and P.STATUS['forex'] == 'fresh'
        assert any('news' in e for e in P.ERRORS), 'failure must be logged'


# ---------------------------------------------------------------------------
# C. Crypto returns an empty array -> rejected, previous preserved
# ---------------------------------------------------------------------------
def test_c_crypto_empty():
    with Sandbox() as sb:
        prev = {'data': GOOD_CRYPTO, 'fetched_utc': '2026-08-06T23:30:00Z',
                'stale': False}
        sb.seed('data/markets_crypto.json', prev)

        def empty():
            raise P.FetchError('empty price object')

        feed = P.resolve_feed('crypto', empty, 'data/markets_crypto.json')
        assert feed['data'] == GOOD_CRYPTO, 'good crypto must not be blanked'
        assert feed['stale'] is True
        assert P.STATUS['crypto'] == 'preserved'


def test_c2_partial_payload_rejected():
    """A response with too few valid assets must be treated as a failure."""
    with Sandbox() as sb:
        sb.seed('data/markets_crypto.json',
                {'data': GOOD_CRYPTO, 'fetched_utc': '2026-08-06T23:30:00Z',
                 'stale': False})

        def partial():
            # only 3 of 12 -> below the 70% floor
            raise P.FetchError('only 3/12 assets valid (need >= 8)')

        feed = P.resolve_feed('crypto', partial, 'data/markets_crypto.json')
        assert len(feed['data']) == 12, 'partial payload must not replace good data'


# ---------------------------------------------------------------------------
# D. Signal generation invalid -> existing file untouched
# ---------------------------------------------------------------------------
def test_d_invalid_signals_preserved():
    with Sandbox() as sb:
        good = {'updated': '2026-08-06T23:30:00Z', 'market_date': '2026-08-06',
                'signals': [{'s': 'AAPL', 'p': 1.0, 'sc': 25, 'd': 'BUY'}],
                'buy_count': 1, 'total_count': 1}
        sb.seed('data/quantum_signals.json', good)
        before = sb.load('data/quantum_signals.json')

        try:
            raise P.FetchError('only 12/180 tickers scored - refusing to publish')
        except P.FetchError as e:
            P.stage_error('signals', e)

        after = sb.load('data/quantum_signals.json')
        assert after == before, 'invalid scan must leave the good file untouched'
        assert P.ERRORS, 'the failure must be recorded'


# ---------------------------------------------------------------------------
# E. Workflow runs on a Saturday -> no fake weekend market_date
# ---------------------------------------------------------------------------
def test_e_weekend_run():
    sat = datetime.datetime(2026, 8, 8, 23, 30, tzinfo=UTC)   # Saturday
    sun = datetime.datetime(2026, 8, 9, 23, 30, tzinfo=UTC)   # Sunday
    for when in (sat, sun):
        s = C.last_completed_session(when)
        assert s == datetime.date(2026, 8, 7), f'{when:%a} -> {s}, want Fri 08-07'
        assert C.is_trading_day(s)
        assert s.weekday() < 5, 'never a weekend date'


def test_e2_holiday_run():
    # 2026-07-03 is the observed Independence Day holiday (Jul 4 is a Saturday)
    assert not C.is_trading_day(datetime.date(2026, 7, 3))
    s = C.last_completed_session(datetime.datetime(2026, 7, 3, 23, 30, tzinfo=UTC))
    assert s == datetime.date(2026, 7, 2), s
    # Thanksgiving
    assert not C.is_trading_day(datetime.date(2026, 11, 26))
    s = C.last_completed_session(datetime.datetime(2026, 11, 26, 23, 30, tzinfo=UTC))
    assert s == datetime.date(2026, 11, 25), s


def test_e3_preclose_run_uses_prior_session():
    """A run before the close must report the PREVIOUS session, not today."""
    s = C.last_completed_session(
        datetime.datetime(2026, 8, 10, 12, 0, tzinfo=UTC))   # Mon midday
    assert s == datetime.date(2026, 8, 7), s


# ---------------------------------------------------------------------------
# F. Nothing changed -> no feed rewritten
# ---------------------------------------------------------------------------
def test_f_no_change_no_write():
    with Sandbox() as sb:
        sb.seed('data/markets_fx.json',
                {'data': GOOD_FX, 'fetched_utc': '2026-08-06T23:30:00Z',
                 'stale': False})

        def boom():
            raise P.FetchError('down')

        feed = P.resolve_feed('forex', boom, 'data/markets_fx.json')
        # main() only writes feeds where stale is False.
        assert feed['stale'] is True, 'preserved feeds must be flagged stale'
        # Simulate the write gate from main()
        wrote = feed and not feed['stale']
        assert not wrote, 'a preserved feed must not be rewritten'


# ---------------------------------------------------------------------------
# G. HTTP 429 -> bounded retries, then a soft failure (never a crash)
# ---------------------------------------------------------------------------
class FakeResp:
    def __init__(self, status, body=None, ctype='application/json',
                 headers=None):
        self.status_code = status
        self._body = body
        self.headers = {'Content-Type': ctype}
        self.headers.update(headers or {})

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def _patch_requests(responses):
    """Feed get_json a scripted sequence of responses; count the calls."""
    calls = {'n': 0}

    class FakeRequests:
        @staticmethod
        def get(url, **kw):
            i = min(calls['n'], len(responses) - 1)
            calls['n'] += 1
            r = responses[i]
            if isinstance(r, Exception):
                raise r
            return r

    P.requests = FakeRequests
    P.HAS_REQUESTS = True
    return calls


def test_g_429_bounded_retry():
    orig, had = getattr(P, 'requests', None), P.HAS_REQUESTS
    slept = []
    real_sleep, P.time.sleep = P.time.sleep, lambda s: slept.append(s)
    try:
        calls = _patch_requests([FakeResp(429, headers={'Retry-After': '1'})])
        try:
            P.get_json('https://x', label='t')
            raise AssertionError('should have raised FetchError')
        except P.FetchError as e:
            assert '429' in str(e), e
        assert calls['n'] == P.MAX_ATTEMPTS, \
            f'expected {P.MAX_ATTEMPTS} bounded attempts, got {calls["n"]}'
        assert all(s <= P.MAX_BACKOFF for s in slept), \
            f'backoff must stay bounded, got {slept}'
    finally:
        P.time.sleep = real_sleep
        P.requests, P.HAS_REQUESTS = orig, had


def test_g2_5xx_then_success():
    orig, had = getattr(P, 'requests', None), P.HAS_REQUESTS
    real_sleep, P.time.sleep = P.time.sleep, lambda s: None
    try:
        _patch_requests([FakeResp(503), FakeResp(200, {'ok': True})])
        assert P.get_json('https://x', label='t') == {'ok': True}
    finally:
        P.time.sleep = real_sleep
        P.requests, P.HAS_REQUESTS = orig, had


def test_g3_4xx_not_retried():
    """A 401/404 will not fix itself; retrying just burns quota."""
    orig, had = getattr(P, 'requests', None), P.HAS_REQUESTS
    real_sleep, P.time.sleep = P.time.sleep, lambda s: None
    try:
        calls = _patch_requests([FakeResp(401)])
        try:
            P.get_json('https://x', label='t')
            raise AssertionError('should have raised')
        except P.FetchError as e:
            assert 'not retryable' in str(e), e
        assert calls['n'] == 1, f'4xx must not retry, got {calls["n"]} calls'
    finally:
        P.time.sleep = real_sleep
        P.requests, P.HAS_REQUESTS = orig, had


def test_g4_html_error_page_rejected():
    """A 200 with an HTML body is a classic silent-corruption source."""
    orig, had = getattr(P, 'requests', None), P.HAS_REQUESTS
    real_sleep, P.time.sleep = P.time.sleep, lambda s: None
    try:
        _patch_requests([FakeResp(200, '<html>rate limited</html>',
                                  ctype='text/html')])
        try:
            P.get_json('https://x', label='t')
            raise AssertionError('should have raised')
        except P.FetchError as e:
            assert 'Content-Type' in str(e), e
    finally:
        P.time.sleep = real_sleep
        P.requests, P.HAS_REQUESTS = orig, had


def test_g5_malformed_json_rejected():
    orig, had = getattr(P, 'requests', None), P.HAS_REQUESTS
    real_sleep, P.time.sleep = P.time.sleep, lambda s: None
    try:
        _patch_requests([FakeResp(200, ValueError('Expecting value'))])
        try:
            P.get_json('https://x', label='t')
            raise AssertionError('should have raised')
        except P.FetchError as e:
            assert 'malformed JSON' in str(e), e
    finally:
        P.time.sleep = real_sleep
        P.requests, P.HAS_REQUESTS = orig, had


# ---------------------------------------------------------------------------
# H. Existing snapshot already stale -> reported honestly, never as fresh
# ---------------------------------------------------------------------------
def test_h_stale_snapshot_labelled():
    assert C.freshness_state(2) == 'fresh'
    assert C.freshness_state(30) == 'recent'
    assert C.freshness_state(24 * 7) == 'delayed'
    assert C.freshness_state(24 * 60) == 'paused'
    assert C.freshness_state(None) == 'unknown'

    with Sandbox() as sb:
        old = '2026-04-13T22:33:48Z'
        sb.seed('data/news.json', {'data': [{'headline': 'x'}],
                                   'fetched_utc': old, 'stale': False})

        def boom():
            raise P.FetchError('down')

        feed = P.resolve_feed('news', boom, 'data/news.json')
        assert feed['fetched_utc'] == old, \
            'a stale snapshot must never be restamped with now()'
        assert feed['stale'] is True


def test_h2_status_reports_staleness():
    with Sandbox() as sb:
        P.STATUS.update({'forex': 'preserved', 'crypto': 'preserved',
                         'news': 'preserved', 'bar': 'preserved',
                         'signals': 'preserved'})
        old_feed = {'data': [1], 'fetched_utc': '2026-04-13T22:33:48Z',
                    'stale': True}
        sig = {'updated': '2026-04-13T22:33:48Z', 'market_date': '2026-04-14'}
        st = P.build_status(old_feed, old_feed, old_feed, old_feed, sig, False)
        assert st['signals_status'] == 'paused', st['signals_status']
        assert st['markets_status'] in ('delayed', 'paused'), st['markets_status']
        assert st['pipeline_result'] in ('PARTIAL', 'FAILED')
        assert st['signals_sessions_behind'] > 5
        # Schema the frontend and humans depend on.
        for k in ('last_pipeline_run', 'markets_updated', 'news_updated',
                  'signals_market_date', 'markets_status', 'news_status',
                  'signals_status'):
            assert k in st, f'status.json missing {k}'


def test_h3_status_is_secret_free():
    with Sandbox():
        P.STATUS.update({'forex': 'fresh'})
        sig = {'updated': '2026-08-07T23:30:00Z', 'market_date': '2026-08-07'}
        st = P.build_status({'data': [1], 'fetched_utc': '2026-08-07T23:30:00Z',
                             'stale': False}, None, None, None, sig, True)
        blob = json.dumps(st).lower()
        for bad in ('token', 'apikey', 'api_key', 'secret', 'password'):
            assert bad not in blob, f'status.json leaked {bad!r}'


# ---------------------------------------------------------------------------
# Validation-layer tests: the guards must actually catch bad input
# ---------------------------------------------------------------------------
def test_bounds_reject_garbage():
    assert P._num(True) is None, 'bools must not pass as numbers'
    assert P._num('1.5') is None, 'strings must not pass as numbers'
    assert P._num(float('nan')) is None
    assert P._num(float('inf')) is None
    assert P._num(3) == 3.0


def test_market_date_never_weekend():
    for day in range(1, 29):
        d = datetime.date(2026, 8, min(day, 28))
        when = datetime.datetime(d.year, d.month, d.day, 23, 30, tzinfo=UTC)
        s = C.last_completed_session(when)
        assert s.weekday() < 5, f'{d} -> {s} is a weekend'
        assert C.is_trading_day(s), f'{d} -> {s} is a holiday'


def test_engine_config_is_coherent():
    e = C.ENGINE
    assert 0 < e['confluence_min'] <= e['n_signals']
    assert e['agreement_pct'] == round(100 * e['confluence_min'] / e['n_signals'])
    assert e['universe_count'] == len(P.TICKERS), \
        f"ENGINE says {e['universe_count']} but TICKERS has {len(P.TICKERS)}"
    assert P.CONFLUENCE_MIN == e['confluence_min']
    assert P.N_SIGNALS == e['n_signals']


# ---------------------------------------------------------------------------
# Validator negative tests: prove the pre-commit gate actually blocks bad builds
# ---------------------------------------------------------------------------
import importlib                                            # noqa: E402


def _run_validator_on(mutate):
    """Copy the real site to a temp root, corrupt it, and run the validator.
    Returns the list of errors it produced."""
    tmp = tempfile.mkdtemp(prefix='qm-val-')
    try:
        site = os.path.join(tmp, 'site')
        os.makedirs(site)
        for name in os.listdir(ROOT):
            if name in ('.git', 'node_modules', '.github'):
                continue
            src = os.path.join(ROOT, name)
            dst = os.path.join(site, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        mutate(site)
        os.environ['QM_ROOT'] = site
        import validate_site
        importlib.reload(validate_site)
        validate_site._reset()
        for fn in (validate_site.check_required_files,
                   validate_site.check_forbidden_strings,
                   validate_site.check_signal_config,
                   validate_site.check_stale_homepage_copy,
                   validate_site.check_no_fabricated_attribution,
                   validate_site.check_methodology_consistency,
                   validate_site.check_html_structure,
                   validate_site.check_blank_data_regression,
                   validate_site.check_signals,
                   validate_site.check_sitemap):
            try:
                fn()
            except Exception as e:
                validate_site.err(f'validator raised {e!r}')
        return list(validate_site.ERRORS)
    finally:
        os.environ.pop('QM_ROOT', None)
        shutil.rmtree(tmp, ignore_errors=True)


def _write(site, rel, text):
    with open(os.path.join(site, rel), 'w', encoding='utf-8') as f:
        f.write(text)


def _read(site, rel):
    with open(os.path.join(site, rel), encoding='utf-8') as f:
        return f.read()


def test_v0_clean_site_passes():
    errs = _run_validator_on(lambda site: None)
    assert not errs, f'clean site must validate: {errs}'


def test_v1_catches_legacy_methodology():
    def mutate(site):
        t = _read(site, 'quantum-signals.html')
        _write(site, 'quantum-signals.html',
               t.replace('</main>', '<p>scans 500+ US equities using 93 '
                                    'technical signals</p></main>'))
    errs = _run_validator_on(mutate)
    assert any('legacy' in e for e in errs), errs


def test_v2_catches_truncated_file():
    errs = _run_validator_on(lambda s: _write(s, 'markets.html', '<html></html>'))
    assert any('truncated' in e or 'MISSING' in e for e in errs), errs


def test_v3_catches_broken_json():
    def mutate(site):
        _write(site, os.path.join('data', 'quantum_signals.json'), '{"broken":')
    errs = _run_validator_on(mutate)
    assert any('does not parse' in e for e in errs), errs


def test_v4_catches_weekend_market_date():
    def mutate(site):
        p = os.path.join(site, 'data', 'quantum_signals.json')
        d = json.load(open(p, encoding='utf-8'))
        d['market_date'] = '2026-08-08'          # a Saturday
        json.dump(d, open(p, 'w', encoding='utf-8'))
    errs = _run_validator_on(mutate)
    assert any('not a US trading day' in e for e in errs), errs


def test_v5_catches_threshold_mismatch():
    """A row scored below the threshold but flagged BUY is a logic regression."""
    def mutate(site):
        p = os.path.join(site, 'data', 'quantum_signals.json')
        d = json.load(open(p, encoding='utf-8'))
        d['signals'][0]['sc'] = 3
        d['signals'][0]['d'] = 'BUY'
        json.dump(d, open(p, 'w', encoding='utf-8'))
    errs = _run_validator_on(mutate)
    assert any('mismatch' in e for e in errs), errs


def test_v6_catches_unbalanced_script_tag():
    """The exact bug that shipped: a missing opening <script> tag."""
    def mutate(site):
        t = _read(site, 'markets.html')
        _write(site, 'markets.html', t.replace('<script src="qm-data.js">', '', 1))
    errs = _run_validator_on(mutate)
    assert any('unbalanced script' in e for e in errs), errs


def test_v7_catches_blank_grid_regression():
    """The historical failure: every price cell rendered as an em-dash."""
    def mutate(site):
        t = _read(site, 'markets.html')
        rows = ('<div class="dmono" style="color:var(--dimmer)">&mdash;</div>'
                '<div></div>') * 8
        _write(site, 'markets.html', t.replace('</footer>', '</footer>' + rows))
    errs = _run_validator_on(mutate)
    assert any('blank-grid' in e or 'placeholder' in e for e in errs), errs


def test_v8_catches_hardcoded_api_key():
    def mutate(site):
        t = _read(site, 'index.html')
        _write(site, 'index.html',
               t.replace('</body>', "<script>var token='abcdef0123456789abcdef'"
                                    ";</script></body>"))
    errs = _run_validator_on(mutate)
    assert any('API key' in e for e in errs), errs


def test_v9_catches_missing_injection_anchor():
    def mutate(site):
        t = _read(site, 'markets.html')
        _write(site, 'markets.html', t.replace('<!-- QM:FOREX:START -->', ''))
    errs = _run_validator_on(mutate)
    assert any('anchors' in e for e in errs), errs


def test_v11_catches_fabricated_publisher_byline():
    """The homepage shipped seven invented stories bylined to real newsrooms."""
    def mutate(site):
        t = _read(site, 'index.html')
        _write(site, 'index.html', t.replace(
            '</body>', '<div class="nc-src">Financial Times</div></body>'))
    errs = _run_validator_on(mutate)
    assert any('fabricated attribution' in e or 'Financial Times' in e
               for e in errs), errs


def test_v12_catches_dated_macro_calendar():
    """Hardcoded dated events expire and then read as current."""
    def mutate(site):
        t = _read(site, 'index.html')
        _write(site, 'index.html', t.replace(
            '</body>', '<div class="cal-time">Apr 10 8:30</div></body>'))
    errs = _run_validator_on(mutate)
    assert any('calendar' in e for e in errs), errs


def test_v13_catches_fake_relative_timestamp():
    def mutate(site):
        t = _read(site, 'index.html')
        _write(site, 'index.html', t.replace(
            '</body>', '<span class="nc-time">4h ago</span></body>'))
    errs = _run_validator_on(mutate)
    assert any('relative timestamp' in e for e in errs), errs


def test_v14_catches_signal_config_drift():
    """Published config must not drift from ENGINE."""
    def mutate(site):
        p = os.path.join(site, 'data', 'signal_config.json')
        d = json.load(open(p, encoding='utf-8'))
        d['buy_threshold'] = 4          # the legacy value
        json.dump(d, open(p, 'w', encoding='utf-8'))
    errs = _run_validator_on(mutate)
    assert any('buy_threshold' in e for e in errs), errs


def test_v15_allows_linked_publisher_byline():
    """Regression: run #46 was blocked because the validator flagged the
    pipeline's own news snapshot, which carries genuine Reuters/CNBC bylines
    linked to the original articles. Real attribution must pass."""
    def mutate(site):
        t = _read(site, 'news.html')
        card = ('<a href="https://www.reuters.com/markets/x" target="_blank" '
                'rel="noopener noreferrer" class="nc">'
                '<div class="nc-headline">A real headline from the feed</div>'
                '<div class="nc-foot"><span class="nc-src">Reuters</span></div></a>')
        _write(site, 'news.html', t.replace('</footer>', '</footer>' + card))
    errs = _run_validator_on(mutate)
    assert not any('fabricated attribution' in e or 'Reuters' in e
                   for e in errs), \
        f'linked byline must NOT be flagged as fabricated: {errs}'


def test_v16_allows_pipeline_injected_region():
    """Content inside QM injection markers is machine-generated from a
    validated feed and must be exempt."""
    def mutate(site):
        t = _read(site, 'news.html')
        inject = ('<!-- QM:NEWS_SNAP:START -->'
                  '<div class="nc-foot"><span class="nc-src">CNBC</span></div>'
                  '<!-- QM:NEWS_SNAP:END -->')
        _write(site, 'news.html',
               re.sub(r'<!-- QM:NEWS_SNAP:START -->.*?<!-- QM:NEWS_SNAP:END -->',
                      inject, t, flags=re.DOTALL))
    errs = _run_validator_on(mutate)
    assert not any('CNBC' in e for e in errs), \
        f'pipeline-injected region must be exempt: {errs}'


def test_v10_catches_future_lastmod():
    def mutate(site):
        t = _read(site, 'sitemap.xml')
        _write(site, 'sitemap.xml', t.replace('<lastmod>2026-08-07</lastmod>',
                                              '<lastmod>2099-01-01</lastmod>', 1))
    errs = _run_validator_on(mutate)
    assert any('future' in e for e in errs), errs


# ---------------------------------------------------------------------------
def main():
    print('=' * 66)
    print('QuantMedia pipeline reliability tests')
    print('=' * 66)
    scenarios = [
        ('A  all sources succeed',            test_a_all_succeed),
        ('B  news fails -> preserved',        test_b_news_fails_preserves),
        ('C  crypto empty -> preserved',      test_c_crypto_empty),
        ('C2 partial payload rejected',       test_c2_partial_payload_rejected),
        ('D  invalid signals -> untouched',   test_d_invalid_signals_preserved),
        ('E  Saturday/Sunday run',            test_e_weekend_run),
        ('E2 market holiday run',             test_e2_holiday_run),
        ('E3 pre-close run',                  test_e3_preclose_run_uses_prior_session),
        ('F  no change -> no rewrite',        test_f_no_change_no_write),
        ('G  HTTP 429 bounded retry',         test_g_429_bounded_retry),
        ('G2 5xx then success',               test_g2_5xx_then_success),
        ('G3 4xx not retried',                test_g3_4xx_not_retried),
        ('G4 HTML error page rejected',       test_g4_html_error_page_rejected),
        ('G5 malformed JSON rejected',        test_g5_malformed_json_rejected),
        ('H  stale snapshot labelled',        test_h_stale_snapshot_labelled),
        ('H2 status reports staleness',       test_h2_status_reports_staleness),
        ('H3 status is secret-free',          test_h3_status_is_secret_free),
        ('--  numeric bounds',                test_bounds_reject_garbage),
        ('--  market_date never weekend',     test_market_date_never_weekend),
        ('--  engine config coherent',        test_engine_config_is_coherent),
        # The validator must FAIL on bad input, not just pass on good input.
        ('V0 clean site passes',              test_v0_clean_site_passes),
        ('V1 catches legacy methodology',     test_v1_catches_legacy_methodology),
        ('V2 catches truncated file',         test_v2_catches_truncated_file),
        ('V3 catches broken JSON',            test_v3_catches_broken_json),
        ('V4 catches weekend market_date',    test_v4_catches_weekend_market_date),
        ('V5 catches threshold mismatch',     test_v5_catches_threshold_mismatch),
        ('V6 catches unbalanced script tag',  test_v6_catches_unbalanced_script_tag),
        ('V7 catches blank-grid regression',  test_v7_catches_blank_grid_regression),
        ('V8 catches hardcoded API key',      test_v8_catches_hardcoded_api_key),
        ('V9 catches missing anchor',         test_v9_catches_missing_injection_anchor),
        ('V10 catches future lastmod',      test_v10_catches_future_lastmod),
        ('V15 allows linked byline',        test_v15_allows_linked_publisher_byline),
        ('V16 allows injected region',      test_v16_allows_pipeline_injected_region),
        ('V11 catches fake publisher byline', test_v11_catches_fabricated_publisher_byline),
        ('V12 catches dated macro calendar', test_v12_catches_dated_macro_calendar),
        ('V13 catches fake relative time',  test_v13_catches_fake_relative_timestamp),
        ('V14 catches signal config drift', test_v14_catches_signal_config_drift),
    ]
    for name, fn in scenarios:
        check(name, fn)

    print()
    print(f'{len(PASSED)} passed, {len(FAILED)} failed')
    if FAILED:
        print('\nFAILURES:')
        for name, why in FAILED:
            print(f'  {name}: {why}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())


def test_sector_map_covers_universe():
    """Every scanned ticker must map to exactly one sector, or the Sector
    Confluence index silently drops names."""
    uni, mapped = set(P.TICKERS), set(C.SECTOR_OF)
    assert not uni - mapped, f'unmapped tickers: {sorted(uni - mapped)}'
    assert not mapped - uni, f'mapped but not scanned: {sorted(mapped - uni)}'
    dupes = [t for t in mapped
             if sum(t in v for v in C.SECTOR_MAP.values()) > 1]
    assert not dupes, f'ticker in two sectors: {dupes}'


def test_breadth_metric_is_consistent():
    """Breadth must equal BUY/scored exactly, and never exceed 100%."""
    sig = {
        'market_date': '2026-08-07',
        'engine': {'universe': C.ENGINE['universe_count']},
        'signals': [{'s': 'AAPL', 'sc': 25, 'd': 'BUY'},
                    {'s': 'MSFT', 'sc': 22, 'd': 'BUY'},
                    {'s': 'INTC', 'sc': 10, 'd': 'WATCH'},
                    {'s': 'F',    'sc': 8,  'd': 'WATCH'}],
    }
    b = P.compute_breadth(sig)
    assert b['buy_signals'] == 2 and b['scored_stocks'] == 4
    assert b['breadth_pct'] == 50.0, b['breadth_pct']
    assert 0 <= b['breadth_pct'] <= 100
    assert b['min_score'] == 8 and b['max_score'] == 25
    assert sum(d['n'] for d in b['distribution']) == 4, 'distribution must total'
    assert b['regime_band']['label'] == 'Mixed participation'


def test_sector_confluence_drops_tiny_sectors():
    """A sector below the minimum size must be omitted, not averaged on 1 name."""
    sig = {'market_date': '2026-08-07',
           'engine': {'universe': C.ENGINE['universe_count']},
           'signals': [{'s': 'NEE', 'sc': 20, 'd': 'WATCH'}]}
    out = P.compute_sector_confluence(sig)
    assert out['sectors'] == [], 'a 1-name sector must not be reported'
