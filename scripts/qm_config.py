#!/usr/bin/env python3
"""
QuantMedia pipeline configuration - THE single source of truth.
===============================================================
Pure standard library on purpose. This module is imported by the pre-commit
validator, which must run in CI before (and independently of) pandas/numpy/
yfinance being installed. Do not add third-party imports here.

Everything that both the production code AND the user-facing site copy must
agree on lives in ENGINE below. If you change the signal engine, change it
here: validate_site.py will fail the build when the HTML still quotes the old
numbers, which is what stopped the site drifting into claiming "93 signals /
4+ bullish" while the code actually ran 30 signals with a threshold of 22.
"""

import datetime
import re

# ---------------------------------------------------------------------------
# Signal engine - single source of truth
# ---------------------------------------------------------------------------
ENGINE = {
    'universe_count':   180,
    'universe_label':   '180 liquid US-listed equities',
    'universe_note':    ('A fixed liquidity list, not an index. Includes large-cap '
                         'S&P 500 names alongside high-volume tickers that are not '
                         'index constituents.'),
    'n_signals':        30,
    'confluence_min':   22,
    'min_sessions':     60,      # eligibility gate: completed daily bars required
    'hold_days':        60,      # forward window for the up-rate statistic
    'stop_atr':         2.0,     # reference stop  = close - stop_atr   x ATR(14)
    'target_atr':       1.5,     # reference target= close + target_atr x ATR(14)
    'cadence':          'Mon-Fri, 23:30 UTC (after the 16:00 ET US close)',
    'data_source':      'Yahoo Finance via yfinance (end-of-day OHLCV)',
}
# Methodology version. Bump this when the production engine changes so that
# historical records stay attributable to the logic that produced them.
# Historical papers keep their own methodology and are NOT rewritten.
METHODOLOGY_VERSION = '2.0'
METHODOLOGY_EFFECTIVE = '2026-04-14'   # date the 30-signal / 22-threshold engine went live

ENGINE['agreement_pct'] = round(
    100.0 * ENGINE['confluence_min'] / ENGINE['n_signals'])   # 73


def signal_config():
    """Public, machine-readable projection of ENGINE, published at
    /data/signal_config.json. Anything consuming the methodology (site copy,
    validator, external readers) reads this rather than hardcoding numbers."""
    return {
        '_comment': ('Generated from ENGINE in scripts/qm_config.py by '
                     'scripts/daily_update.py. Do not hand-edit: '
                     'scripts/validate_site.py fails the build when site copy '
                     'stops matching these values.'),
        'eligible_universe_label': ENGINE['universe_label'],
        'universe_count':          ENGINE['universe_count'],
        'universe_note':           ENGINE['universe_note'],
        'signal_count':            ENGINE['n_signals'],
        'buy_threshold':           ENGINE['confluence_min'],
        'agreement_pct':           ENGINE['agreement_pct'],
        'min_sessions':            ENGINE['min_sessions'],
        'hold_days':               ENGINE['hold_days'],
        'stop_atr':                ENGINE['stop_atr'],
        'target_atr':              ENGINE['target_atr'],
        'update_cadence':          'post-close',
        'schedule_utc':            'Mon-Fri 23:30 UTC',
        'data_source':             ENGINE['data_source'],
        'methodology_version':     METHODOLOGY_VERSION,
        'methodology_effective':   METHODOLOGY_EFFECTIVE,
    }

# ---------------------------------------------------------------------------
# Sector grouping for the scan universe.
#
# Deliberately called a "QuantMedia sector grouping", not GICS. It approximates
# the GICS sectors but is hand-maintained, and a handful of names (notably the
# solar/clean-energy cohort, which GICS splits across Information Technology,
# Industrials and Utilities) are grouped by how they actually trade rather than
# by official classification. Saying "GICS" would be claiming an accuracy this
# map does not have. Every ticker in TICKERS must appear here exactly once -
# test_pipeline.py enforces that.
# ---------------------------------------------------------------------------
SECTOR_MAP = {
    'Technology': [
        'AAPL', 'MSFT', 'NVDA', 'AVGO', 'ORCL', 'CRM', 'AMD', 'CSCO', 'ACN',
        'IBM', 'ADBE', 'INTC', 'QCOM', 'INTU', 'TXN', 'ADI', 'MU', 'MRVL',
        'PANW', 'SNPS', 'CDNS', 'KLAC', 'LRCX', 'AMAT', 'NOW', 'APH', 'ON',
        'WOLF', 'ZS', 'OKTA', 'CRWD', 'S', 'DDOG', 'SNOW', 'PLTR', 'AI',
        'GTLB', 'CFLT', 'NET', 'MDB',
    ],
    'Communication Services': ['GOOGL', 'GOOG', 'META', 'NFLX', 'T', 'VZ'],
    'Consumer Discretionary': [
        'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX', 'BKNG',
        'GM', 'F',
    ],
    'Consumer Staples': ['PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'MO', 'TGT'],
    'Health Care': [
        'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'TMO', 'ABT', 'DHR', 'SYK',
        'AMGN', 'PFE', 'MDT', 'GILD', 'ELV', 'CI', 'HUM', 'CVS', 'MCK',
        'ZTS', 'REGN', 'ISRG', 'VRTX',
    ],
    'Financials': [
        'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'MS', 'WFC', 'GS', 'BLK', 'AXP',
        'CB', 'C', 'USB', 'AON', 'PNC', 'AIG', 'SPGI', 'CME', 'PYPL', 'COIN',
        'HOOD', 'SOFI', 'NU', 'AFRM', 'UPST', 'BX', 'KKR', 'APO', 'ARES',
        'CG', 'BAM', 'TPG', 'HLNE',
    ],
    'Energy': [
        'XOM', 'CVX', 'OXY', 'PSX', 'VLO', 'MPC', 'HAL', 'SLB', 'BKR',
        'DVN', 'FANG',
    ],
    'Industrials': [
        'UPS', 'CAT', 'LMT', 'RTX', 'HON', 'DE', 'FDX', 'GE', 'ETN', 'BA',
        'LHX', 'GD', 'NOC', 'HII', 'TDG', 'HEI', 'TXT', 'AXON', 'EMR', 'ROK',
        'PH', 'IR', 'AME', 'ROP', 'FTV', 'OTIS', 'CARR', 'ITW', 'MMM', 'NSC',
    ],
    'Materials': [
        'APD', 'SHW', 'ECL', 'FCX', 'NEM', 'GOLD', 'AEM', 'WPM', 'KGC', 'AGI',
    ],
    'Utilities': ['NEE', 'DUK', 'SO'],
    'Clean Energy': ['ENPH', 'FSLR', 'SEDG', 'CSIQ', 'ARRY', 'RUN'],
}

# Flattened ticker -> sector lookup.
SECTOR_OF = {t: sec for sec, names in SECTOR_MAP.items() for t in names}

# A sector needs enough constituents for an average to mean anything.
MIN_SECTOR_SIZE = 3


# ---------------------------------------------------------------------------
# Per-source validation thresholds. A fetch that cannot clear these is treated
# as a failure and the previous good snapshot is preserved instead.
# ---------------------------------------------------------------------------
EXPECTED = {
    'forex':  {'total': 18, 'min_ratio': 0.70},   # >= 13 of 18 pairs
    'crypto': {'total': 12, 'min_ratio': 0.70},   # >=  9 of 12 assets
    'news':   {'total': 16, 'min_items': 6},
    'bar':    {'total':  9, 'min_items': 5},
}

# Sanity bounds. Anything outside these is a bad payload, not a market move.
BOUNDS = {
    'fx_price':      (1e-6, 1e7),
    'crypto_price':  (1e-8, 1e8),
    'crypto_chg_pct': (-95.0, 500.0),
    'equity_price':  (0.01, 1e6),
    'rsi':           (0.0, 100.0),
    'bar_chg_pct':   (-99.0, 200.0),
}

# ---------------------------------------------------------------------------
# Freshness. Thresholds are shared with the frontend (qm-data.js mirrors them).
# ---------------------------------------------------------------------------
FRESHNESS_HOURS = {
    'fresh':   20,      # < 20h  -> "fresh"
    'recent':  96,      # < 96h  -> "recent"   (covers a long weekend)
    'delayed': 24 * 14, # < 14d  -> "delayed"  (warn)
}                       # beyond -> "paused"   (do not imply currency)


def freshness_state(age_hours):
    """Mirror of QM.freshness() in qm-data.js. Keep the two in step."""
    if age_hours is None:
        return 'unknown'
    if age_hours < FRESHNESS_HOURS['fresh']:
        return 'fresh'
    if age_hours < FRESHNESS_HOURS['recent']:
        return 'recent'
    if age_hours < FRESHNESS_HOURS['delayed']:
        return 'delayed'
    return 'paused'


# ---------------------------------------------------------------------------
# US equity market trading calendar (NYSE/Nasdaq).
# Rule-derived rather than a hardcoded list so it does not silently expire.
# ---------------------------------------------------------------------------
def _easter(year):
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return datetime.date(year, month, day + 1)


def _nth_weekday(year, month, weekday, n):
    """n-th `weekday` (Mon=0) of month; n=-1 for the last one."""
    if n > 0:
        d = datetime.date(year, month, 1)
        offset = (weekday - d.weekday()) % 7
        return d + datetime.timedelta(days=offset + 7 * (n - 1))
    last = datetime.date(year, month, 28)
    while (last + datetime.timedelta(days=7)).month == month:
        last += datetime.timedelta(days=7)
    return last - datetime.timedelta(days=(last.weekday() - weekday) % 7)


def _observed(d, is_new_year=False):
    """NYSE observation: Saturday -> preceding Friday, Sunday -> next Monday.
    Exception: a Saturday New Year's Day is NOT observed on Dec 31."""
    if d.weekday() == 5:                       # Saturday
        return None if is_new_year else d - datetime.timedelta(days=1)
    if d.weekday() == 6:                       # Sunday
        return d + datetime.timedelta(days=1)
    return d


def market_holidays(year):
    """Full-day NYSE closures for `year`. Half-days are ignored: the market
    still closes and produces a valid session, which is all we need."""
    out = set()
    for d, is_ny in (
        (_observed(datetime.date(year, 1, 1), is_new_year=True), True),
        (_nth_weekday(year, 1, 0, 3),  False),   # MLK Day
        (_nth_weekday(year, 2, 0, 3),  False),   # Washington's Birthday
        (_easter(year) - datetime.timedelta(days=2), False),   # Good Friday
        (_nth_weekday(year, 5, 0, -1), False),   # Memorial Day
        (_observed(datetime.date(year, 6, 19)),  False),       # Juneteenth
        (_observed(datetime.date(year, 7, 4)),   False),       # Independence Day
        (_nth_weekday(year, 9, 0, 1),  False),   # Labor Day
        (_nth_weekday(year, 11, 3, 4), False),   # Thanksgiving
        (_observed(datetime.date(year, 12, 25)), False),       # Christmas
    ):
        if d is not None:
            out.add(d)
    return out


def is_trading_day(d):
    return d.weekday() < 5 and d not in market_holidays(d.year)


def last_completed_session(now_utc=None, close_hour_utc=21):
    """Most recent US trading session that has finished.

    The 16:00 ET close is 20:00 UTC in EDT and 21:00 UTC in EST. Using 21:00
    is the conservative choice: on a summer afternoon between 20:00 and 21:00
    UTC we report the previous session rather than a session whose official
    close may not be settled yet.

    This is what `market_date` must reflect. Never use the calendar date - a
    Saturday run would otherwise stamp signals with a Saturday.
    """
    now = now_utc or datetime.datetime.now(datetime.timezone.utc)
    d = now.date()
    # If today's close has not happened yet, start looking from yesterday.
    if now.hour < close_hour_utc:
        d -= datetime.timedelta(days=1)
    for _ in range(14):                        # covers the longest holiday run
        if is_trading_day(d):
            return d
        d -= datetime.timedelta(days=1)
    raise RuntimeError('no trading day found in the last 14 days')


def sessions_behind(market_date, now_utc=None):
    """How many completed sessions old `market_date` is. 0 == current."""
    if isinstance(market_date, str):
        market_date = datetime.date.fromisoformat(market_date)
    target = last_completed_session(now_utc)
    if market_date >= target:
        return 0
    n, d = 0, target
    while d > market_date and n < 60:
        d -= datetime.timedelta(days=1)
        if is_trading_day(d):
            n += 1
    return n


# ---------------------------------------------------------------------------
# Pre-commit production guards (used by validate_site.py)
# ---------------------------------------------------------------------------
# Strings that must never reach production again. Each entry is
# (compiled pattern, human explanation).
FORBIDDEN = [
    (re.compile(r'\b500\+\s*(US|S&P|equities|stocks)', re.I),
     'legacy universe claim ("500+")'),
    (re.compile(r'\b509\b\s*(stocks|equities)', re.I),
     'legacy universe count (509)'),
    (re.compile(r'\b93\s*(technical|signals?|rules|indicators?)\b', re.I),
     'legacy signal count (93)'),
    (re.compile(r'\b4\+\s*bullish\b', re.I),
     'legacy confluence threshold (4+)'),
    (re.compile(r'(fewer than|at least)\s+4\s+(active|bullish)', re.I),
     'legacy confluence threshold (4)'),
    (re.compile(r'Sharpe\s*(ratio)?\s*(of\s*)?2\.199', re.I),
     'unsupported performance claim (Sharpe 2.199)'),
    (re.compile(r'67\.3%\s*win', re.I),
     'unsupported performance claim (67.3% win rate)'),
    (re.compile(r'Fetching live data', re.I),
     'placeholder loading copy left in production'),
    (re.compile(r'Finnhub API\s*[-—]\s*Live Feed', re.I),
     'raw provider label exposed in UI'),
    (re.compile(r'updated every (60 seconds|2 minutes|two minutes)', re.I),
     'false refresh-rate claim'),
    (re.compile(r'\bLive rates\b'),
     'false "live" label on snapshot data'),
    (re.compile(r'(token|apikey|api_key)["\']?\s*[=:]\s*["\'][A-Za-z0-9]{16,}', re.I),
     'possible hardcoded API key'),
]

# Files that must exist and never collapse below a sane size.
REQUIRED_FILES = {
    'index.html':            60_000,
    'quantum-signals.html':  40_000,
    'reports/index.html':    12_000,
    'papers.html':           25_000,
    'methodology.html':      15_000,
    'sitemap.xml':            1_000,
    'robots.txt':                50,
    'qm-data.js':             1_000,
    'llms.txt':                 800,
    'indices/signal-breadth.html':    12_000,
    'indices/sector-confluence.html': 12_000,
    'reproducibility.html':     15_000,
    'learn/deflated-sharpe-ratio.html': 12_000,
    'data/ai_query_intelligence.json':  10_000,
    'data/ai_citation_benchmark.json':   8_000,
    'data/signal_config.json':  200,
}

# Pages whose copy must quote the live engine numbers.
METHODOLOGY_PAGES = ['quantum-signals.html', 'methodology.html']
