#!/usr/bin/env python3
"""
QuantMedia Daily Update Pipeline
=================================
Runs Mon-Fri at 23:30 UTC via GitHub Actions (.github/workflows/daily-update.yml).

What it produces
----------------
  data/markets.json          FX + crypto snapshot (keyless public APIs)
  data/news.json             Categorised headline snapshot (Finnhub, needs FINNHUB_KEY)
  data/quantum_signals.json  Post-close technical signal scan
  data/status.json           Per-feed freshness ledger consumed by every page
  data/signal_config.json    Published methodology config (from ENGINE)
  markets.html / news.html   Server-rendered snapshots injected at QM: markers
  sitemap.xml                lastmod bumped for DATA-DRIVEN pages only

Design rules (do not regress these)
-----------------------------------
1. NO API KEY IS EVER WRITTEN INTO HTML OR JSON. Keys stay in env vars.
   The browser reads pre-rendered snapshots from data/*.json instead.
2. A failed fetch NEVER blanks a section. Last-known-good is preserved and
   re-published with its ORIGINAL timestamp, so the page can honestly say
   how old the data is instead of showing empty cells or a false "live" badge.
3. Every feed carries its own `fetched_utc`. The frontend derives the
   freshness label from that timestamp - the word "live" is never hardcoded.
4. Stage failures are isolated. One dead upstream must not stop the others.
   main() collects errors and exits non-zero at the end so CI fails loudly
   while still publishing whatever did succeed.

Signal engine (the single source of truth for all site copy)
------------------------------------------------------------
  Universe    180 liquid US-listed equities (curated large/mid-cap list;
              includes non-S&P-500 names such as COIN, HOOD, NU, AEM, BAM).
              NOT "500+" and NOT "all S&P 500 constituents".
  Eligibility >= 60 completed daily OHLCV sessions inside the trailing 1-year
              download. Names that fail to download, are halted/delisted, or
              return short histories are skipped - that is the ONLY reason the
              scored count can land below the universe size.
  Signals     30 binary technical checks per ticker (see score_ticker).
  Decision    score >= 22  (>= 73% agreement)  -> BUY, otherwise WATCH.
  Levels      Reference stop  = close - 2.0 x ATR(14)
              Reference target = close + 1.5 x ATR(14)
              These are ATR-derived, NOT fixed percentages.
"""

import datetime
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qm_config as C

# Heavy dependencies are optional at import time so the module can be imported
# by the test harness (and by any stdlib-only tooling) without them installed.
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# ---- Config -----------------------------------------------------------------
ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
NOW_UTC  = datetime.datetime.now(datetime.timezone.utc)
NOW_ISO  = NOW_UTC.strftime('%Y-%m-%dT%H:%M:%SZ')

# Identifies this specific run end-to-end. In CI it is the Actions run id, so
# a deployment can be traced back to the exact workflow execution; locally it
# falls back to a timestamp-derived value.
RUN_ID = (os.environ.get('GITHUB_RUN_ID')
          or NOW_UTC.strftime('local-%Y%m%dT%H%M%SZ'))

# The most recent US session that has actually finished. NEVER use the calendar
# date: a Saturday run would otherwise stamp signals with a Saturday.
SESSION_DATE = C.last_completed_session(NOW_UTC)

# FINNHUB_KEY must be supplied as a GitHub Actions secret (Settings -> Secrets).
# There is deliberately no fallback: a missing key skips news, it never leaks.
FINNHUB_KEY = os.environ.get('FINNHUB_KEY', '').strip()

# Engine parameters come from the single source of truth.
CONFLUENCE_MIN = C.ENGINE['confluence_min']
N_SIGNALS      = C.ENGINE['n_signals']
MIN_SESSIONS   = C.ENGINE['min_sessions']
HOLD_DAYS      = C.ENGINE['hold_days']
STOP_ATR       = C.ENGINE['stop_atr']
TARGET_ATR     = C.ENGINE['target_atr']

ERRORS = []      # human-readable stage failures, surfaced in status.json
STATUS = {}      # per-source outcome: fresh | preserved | unavailable


def stage_error(stage, exc):
    msg = f"{stage}: {exc}"
    ERRORS.append(msg)
    print(f"  ERROR  {msg}")


class FetchError(Exception):
    """Raised when a payload is missing, malformed, or fails validation.
    Always caught per-source: one bad upstream must never abort the run."""


# 180 liquid US-listed equities. Curated for data completeness and continuous
# quotation, not index membership - several names are not S&P 500 constituents.
TICKERS = [
    'AAPL','MSFT','NVDA','AMZN','META','GOOGL','GOOG','BRK-B','LLY','JPM',
    'V','XOM','UNH','TSLA','MA','JNJ','PG','AVGO','HD','MRK',
    'COST','ABBV','CVX','BAC','ORCL','CRM','AMD','KO','PEP','WMT',
    'MCD','CSCO','TMO','ACN','ABT','IBM','MS','WFC','ADBE','NFLX',
    'GS','INTC','QCOM','DHR','UPS','CAT','LMT','SYK','AMGN','SPGI',
    'RTX','NEE','HON','BLK','T','VZ','DE','AXP','TJX','INTU',
    'PFE','BKNG','MDT','CB','GILD','C','MMM','USB','MO','AON',
    'CL','DUK','NSC','ITW','CME','APD','SHW','SO','GM','F',
    'ELV','CI','HUM','CVS','MCK','AIG','PNC','TGT','NKE','LOW',
    'SBUX','FDX','GE','ETN','ZTS','NOW','REGN','ISRG','VRTX',
    'PANW','SNPS','CDNS','KLAC','LRCX','AMAT','MU','MRVL','ADI','TXN',
    'PYPL','COIN','HOOD','SOFI','NU','AFRM','UPST','MDB','NET',
    'ZS','OKTA','CRWD','S','DDOG','SNOW','PLTR','AI','GTLB','CFLT',
    'ON','WOLF','ENPH','FSLR','RUN','ARRY','SEDG','CSIQ',
    'BA','LHX','GD','NOC','HII','TDG','HEI','TXT','AXON',
    'OXY','PSX','VLO','MPC','HAL','SLB','BKR','DVN','FANG',
    'FCX','NEM','GOLD','AEM','WPM','KGC','AGI','APH',
    'ECL','EMR','ROK','PH','IR','AME','ROP','FTV','OTIS','CARR',
    'BX','KKR','APO','ARES','CG','BAM','TPG','HLNE',
]
TICKERS = list(dict.fromkeys(TICKERS))
UNIVERSE_N = len(TICKERS)


# ---- I/O helpers ------------------------------------------------------------
def read_file(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def write_file(rel, content):
    with open(os.path.join(ROOT, rel), 'w', encoding='utf-8') as f:
        f.write(content)


def read_json(rel, default=None):
    """Load a previously published snapshot (last-known-good)."""
    path = os.path.join(ROOT, rel)
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def write_json(rel, payload):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, separators=(',', ':'), ensure_ascii=False)


MAX_ATTEMPTS = 3          # bounded on purpose: never retry indefinitely
BASE_BACKOFF = 4          # seconds; doubles each attempt, plus jitter
MAX_BACKOFF  = 45


def _sleep_for(attempt, retry_after=None):
    """Exponential backoff with jitter, honouring Retry-After when supplied."""
    if retry_after:
        try:
            return min(float(retry_after), MAX_BACKOFF)
        except (TypeError, ValueError):
            pass
    delay = min(BASE_BACKOFF * (2 ** (attempt - 1)), MAX_BACKOFF)
    return delay + random.uniform(0, delay * 0.25)


def get_json(url, timeout=15, tries=MAX_ATTEMPTS, label=''):
    """GET returning parsed JSON, with a bounded retry policy.

    Retries: 429 (honouring Retry-After), 5xx, timeouts, connection errors.
    Does NOT retry: 4xx other than 429 - a bad key or bad URL will not fix
    itself, and retrying just burns quota.
    Raises FetchError on final failure so callers treat it as a soft failure.
    """
    if not HAS_REQUESTS:
        raise FetchError('requests not installed')

    last = 'unknown error'
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(
                url, timeout=timeout,
                headers={'User-Agent': 'QuantMedia-DailyUpdate/1.0',
                         'Accept': 'application/json'})

            if r.status_code == 429:
                last = 'rate limited (429)'
                if attempt < tries:
                    wait = _sleep_for(attempt, r.headers.get('Retry-After'))
                    print(f"    {label} 429, retry {attempt}/{tries - 1} "
                          f"in {wait:.0f}s")
                    time.sleep(wait)
                    continue
                raise FetchError(last)

            if 500 <= r.status_code < 600:
                last = f'upstream {r.status_code}'
                if attempt < tries:
                    wait = _sleep_for(attempt)
                    print(f"    {label} {r.status_code}, retry "
                          f"{attempt}/{tries - 1} in {wait:.0f}s")
                    time.sleep(wait)
                    continue
                raise FetchError(last)

            if r.status_code >= 400:
                # Client error: not transient, do not waste further attempts.
                raise FetchError(f'HTTP {r.status_code} (not retryable)')

            ctype = (r.headers.get('Content-Type') or '').lower()
            if 'json' not in ctype:
                # An HTML error/captcha page returned with 200 is a classic
                # silent-corruption source. Reject before it reaches parsing.
                raise FetchError(
                    f'unexpected Content-Type {ctype!r} (expected JSON)')

            try:
                return r.json()
            except ValueError as e:
                raise FetchError(f'malformed JSON payload ({e})')

        except FetchError:
            raise
        except Exception as e:      # timeout / connection / DNS -> retryable
            last = f'{type(e).__name__}: {e}'
            if attempt < tries:
                wait = _sleep_for(attempt)
                print(f"    {label} {last}, retry {attempt}/{tries - 1} "
                      f"in {wait:.0f}s")
                time.sleep(wait)
                continue
    raise FetchError(last)


def yf_download(tickers, **kw):
    """yfinance wrapper that survives signature drift between major versions.

    yfinance tracks an undocumented endpoint and its own API moves too; an
    unexpected keyword should degrade to a plain call rather than take the
    whole scan down.
    """
    try:
        return yf.download(tickers, **kw)
    except TypeError as e:
        print(f"    yfinance rejected a kwarg ({e}); retrying minimally")
        minimal = {k: v for k, v in kw.items() if k in ('period', 'auto_adjust')}
        return yf.download(tickers, **minimal)


def frame_for(raw, sym):
    """Extract one ticker's OHLCV frame from a multi-ticker download.

    Column layout differs by version and by single/multi ticker: it may be a
    MultiIndex with the ticker on level 1 (Price, Ticker) or level 0, or a
    plain frame for a single ticker. Try each rather than assuming.
    """
    if not isinstance(raw.columns, pd.MultiIndex):
        return raw
    for level in (1, 0):
        try:
            if sym in raw.columns.get_level_values(level):
                return raw.xs(sym, level=level, axis=1)
        except (KeyError, IndexError):
            continue
    raise KeyError(sym)


def _num(v):
    """Strict finite-number coercion. Rejects bools, NaN, inf, and strings."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v in (float('inf'), float('-inf')):
        return None
    return float(v)


def inject(html, marker, inner_html):
    """Replace content between QM:MARKER comment anchors."""
    pat = rf'(<!-- QM:{re.escape(marker)}:START -->).*?(<!-- QM:{re.escape(marker)}:END -->)'
    result, n = re.subn(pat, lambda m: f"{m.group(1)}\n{inner_html}\n{m.group(2)}",
                        html, flags=re.DOTALL)
    if n == 0:
        stage_error('inject', f'QM:{marker} anchor missing -- page NOT modified')
    return result


def disp(iso):
    """ISO8601 Z -> 'Aug 07 2026, 23:30 UTC' for display."""
    try:
        dt = datetime.datetime.strptime(iso, '%Y-%m-%dT%H:%M:%SZ')
        return dt.strftime('%b %d %Y, %H:%M UTC')
    except Exception:
        return 'unknown'


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


# ---- 1. Forex ---------------------------------------------------------------
FOREX_PAIRS = [
    ('EUR/USD', 'Euro / Dollar',     'EUR', 'USD', 'majors'),
    ('GBP/USD', 'Sterling / Dollar', 'GBP', 'USD', 'majors'),
    ('USD/JPY', 'Dollar / Yen',      'USD', 'JPY', 'majors'),
    ('USD/CHF', 'Dollar / Franc',    'USD', 'CHF', 'majors'),
    ('AUD/USD', 'Aussie / Dollar',   'AUD', 'USD', 'majors'),
    ('USD/CAD', 'Dollar / Loonie',   'USD', 'CAD', 'majors'),
    ('USD/MXN', 'Dollar / Peso',     'USD', 'MXN', 'crosses'),
    ('USD/BRL', 'Dollar / Real',     'USD', 'BRL', 'crosses'),
    ('USD/CNY', 'Dollar / Yuan',     'USD', 'CNY', 'crosses'),
    ('USD/INR', 'Dollar / Rupee',    'USD', 'INR', 'crosses'),
    ('USD/KRW', 'Dollar / Won',      'USD', 'KRW', 'crosses'),
    ('USD/SGD', 'Dollar / S$',       'USD', 'SGD', 'crosses'),
    ('EUR/GBP', 'Euro / Sterling',   'EUR', 'GBP', 'other'),
    ('EUR/JPY', 'Euro / Yen',        'EUR', 'JPY', 'other'),
    ('EUR/CHF', 'Euro / Franc',      'EUR', 'CHF', 'other'),
    ('GBP/JPY', 'Sterling / Yen',    'GBP', 'JPY', 'other'),
    ('NZD/USD', 'Kiwi / Dollar',     'NZD', 'USD', 'other'),
    ('USD/SEK', 'Dollar / Krona',    'USD', 'SEK', 'other'),
]
FX_GROUPS = [('majors', 'Majors'), ('crosses', 'USD Crosses'), ('other', 'Other Pairs')]


def fetch_forex():
    """Returns {sym: {...}}. Raises FetchError rather than returning a partial
    or empty set, so the caller preserves the previous good snapshot."""
    payload = get_json('https://open.er-api.com/v6/latest/USD', label='forex')
    if not isinstance(payload, dict):
        raise FetchError(f'expected object, got {type(payload).__name__}')
    rates = payload.get('rates')
    if not isinstance(rates, dict) or not rates:
        raise FetchError('empty or missing "rates" object')

    lo, hi = C.BOUNDS['fx_price']
    out = {}
    for sym, name, base, quote, group in FOREX_PAIRS:
        try:
            if base == 'USD':
                num, den = _num(rates[quote]), 1.0
            elif quote == 'USD':
                num, den = 1.0, _num(rates[base])
            else:
                num, den = _num(rates[quote]), _num(rates[base])
            if num is None or den is None or den == 0:
                continue
            price = num / den
        except KeyError:
            continue
        if not (lo <= price <= hi):        # impossible rate -> drop the pair
            continue
        out[sym] = {'name': name, 'price': round(price, 5), 'group': group}

    exp = C.EXPECTED['forex']
    floor = int(exp['total'] * exp['min_ratio'])
    if len(out) < floor:
        raise FetchError(f'only {len(out)}/{exp["total"]} pairs valid '
                         f'(need >= {floor})')
    print(f"  Forex: {len(out)}/{exp['total']} pairs valid")
    return out


def render_forex_html(forex, fetched_iso):
    """Only renders pairs that actually have a price -- no placeholder dashes."""
    def row(sym, entry):
        price = entry['price']
        p = (f'{price:,.0f}' if price >= 10000
             else f'{price:,.2f}' if price >= 1000 else f'{price:.4f}')
        return (f'<div class="drow"><div><div class="dsym">{esc(sym)}</div>'
                f'<div class="dfull">{esc(entry["name"])}</div></div>'
                f'<div class="dmono">{p}</div>'
                f'<div style="text-align:right"><span class="badge nt">close</span></div></div>')

    panels = []
    for key, label in FX_GROUPS:
        rows = [row(s, forex[s]) for s, _, _, _, g in FOREX_PAIRS
                if g == key and s in forex]
        if rows:
            panels.append(f'<div class="panel"><div class="panel-head">{label}</div>'
                          f'{"".join(rows)}</div>')
    return (f'<div class="grid-3" id="fxGrid" data-snapshot="{fetched_iso}">'
            f'{"".join(panels)}</div>')


# ---- 2. Crypto --------------------------------------------------------------
CRYPTO_ASSETS = [
    ('BTC',  'Bitcoin',      'bitcoin'),
    ('ETH',  'Ethereum',     'ethereum'),
    ('SOL',  'Solana',       'solana'),
    ('BNB',  'BNB',          'binancecoin'),
    ('XRP',  'XRP',          'ripple'),
    ('ADA',  'Cardano',      'cardano'),
    ('AVAX', 'Avalanche',    'avalanche-2'),
    ('LINK', 'Chainlink',    'chainlink'),
    ('DOT',  'Polkadot',     'polkadot'),
    ('UNI',  'Uniswap',      'uniswap'),
    ('LTC',  'Litecoin',     'litecoin'),
    ('BCH',  'Bitcoin Cash', 'bitcoin-cash'),
]


def fetch_crypto():
    ids = ','.join(a[2] for a in CRYPTO_ASSETS)
    url = ('https://api.coingecko.com/api/v3/simple/price'
           f'?ids={ids}&vs_currencies=usd&include_24hr_change=true')
    data = get_json(url, label='crypto')
    # CoinGecko returns {} (not an error) when it throttles or ids miss.
    if not isinstance(data, dict) or not data:
        raise FetchError('empty price object')

    lo, hi = C.BOUNDS['crypto_price']
    clo, chi = C.BOUNDS['crypto_chg_pct']
    out = {}
    for sym, name, cg_id in CRYPTO_ASSETS:
        d = data.get(cg_id)
        if not isinstance(d, dict):
            continue
        price = _num(d.get('usd'))
        if price is None or not (lo <= price <= hi):
            continue
        chg = _num(d.get('usd_24h_change'))
        if chg is None or not (clo <= chg <= chi):
            chg = 0.0
        out[sym] = {'name': name, 'price': price, 'chg': round(chg, 2)}

    exp = C.EXPECTED['crypto']
    floor = int(exp['total'] * exp['min_ratio'])
    if len(out) < floor:
        raise FetchError(f'only {len(out)}/{exp["total"]} assets valid '
                         f'(need >= {floor})')
    print(f"  Crypto: {len(out)}/{exp['total']} assets valid")
    return out


def render_crypto_html(crypto, fetched_iso):
    def row(sym, entry):
        price, chg = entry['price'], entry.get('chg', 0.0)
        p = (f'${price:,.0f}' if price >= 1000
             else f'${price:,.2f}' if price >= 1 else f'${price:.4f}')
        cls = 'pos' if chg >= 0 else 'neg'
        sign = '+' if chg >= 0 else ''
        return (f'<div class="drow"><div><div class="dsym">{esc(sym)}</div>'
                f'<div class="dfull">{esc(entry["name"])}</div></div>'
                f'<div class="dmono">{p}</div>'
                f'<div style="text-align:right">'
                f'<span class="badge {cls}">{sign}{chg:.2f}%</span></div></div>')

    live = [(s, crypto[s]) for s, _, _ in CRYPTO_ASSETS if s in crypto]
    half = (len(live) + 1) // 2
    p1 = ''.join(row(s, e) for s, e in live[:half])
    p2 = ''.join(row(s, e) for s, e in live[half:])
    panels = f'<div class="panel"><div class="panel-head">Digital Assets I</div>{p1}</div>'
    if p2:
        panels += f'<div class="panel"><div class="panel-head">Digital Assets II</div>{p2}</div>'
    return f'<div class="grid-2" id="cryptoGrid" data-snapshot="{fetched_iso}">{panels}</div>'


# ---- 3. markets.html --------------------------------------------------------
def update_markets_html(fx_feed, cx_feed):
    """Inject whichever feeds we have. A stale feed keeps its own timestamp."""
    try:
        html = read_file('markets.html')
    except Exception as e:
        stage_error('markets.html read', e)
        return

    if fx_feed and fx_feed.get('data'):
        html = inject(html, 'FOREX',
                      render_forex_html(fx_feed['data'], fx_feed['fetched_utc']))
    if cx_feed and cx_feed.get('data'):
        html = inject(html, 'CRYPTO',
                      render_crypto_html(cx_feed['data'], cx_feed['fetched_utc']))

    stamps = [f['fetched_utc'] for f in (fx_feed, cx_feed) if f and f.get('fetched_utc')]
    if not stamps:
        # Nothing resolved and nothing on disk. Do NOT stamp "now" onto a page
        # that is still showing placeholders - that is exactly the false-live
        # claim this rewrite exists to remove.
        print("  markets.html untouched (no forex or crypto data available)")
        return

    newest = max(stamps)
    html = re.sub(r'(<div id="lastUp"[^>]*data-snapshot=")[^"]*(")',
                  rf'\g<1>{newest}\g<2>', html)
    html = re.sub(r'(<div id="lastUp"[^>]*>).*?(</div>)',
                  lambda m: f'{m.group(1)}Data snapshot: {disp(newest)}{m.group(2)}',
                  html, flags=re.DOTALL)
    write_file('markets.html', html)
    print(f"  markets.html rendered (snapshot {disp(newest)})")


# ---- 4. News ----------------------------------------------------------------
# Categories MUST match the filter tabs in news.html exactly (middot separator).
CAT_RULES = [
    ('Fed · Rates', r'\b(fed|fomc|federal reserve|rate cut|rate hike|interest rates?|'
                         r'inflation|cpi|ppi|powell|treasury|treasuries|yields?|bonds?)\b'),
    ('Tech · AI',   r'\b(ai|a\.i\.|artificial intelligence|nvidia|nvda|microsoft|apple|'
                         r'google|alphabet|meta|openai|anthropic|chips?|semiconductors?|'
                         r'cloud|software|datacenters?)\b'),
    ('Energy',           r'\b(oil|opec|crude|brent|wti|natural gas|lng|refinery|energy)\b'),
    ('Crypto',           r'\b(bitcoin|btc|ethereum|eth|crypto|blockchain|defi|stablecoins?|'
                         r'binance|coinbase)\b'),
    ('Earnings',         r'\b(earnings?|eps|revenue|profits?|guidance|quarterly|'
                         r'beats?|misses|forecasts?)\b'),
    ('Volatility',       r'\b(vix|volatility|selloff|sell-off|crash|plunges?|slumps?|'
                         r'corrections?|rout)\b'),
    ('Markets',          r'\b(s&p|nasdaq|dow|stocks?|equities|markets?|shares?|'
                         r'wall street|indexe?s)\b'),
]
CAT_RULES = [(name, re.compile(pat, re.I)) for name, pat in CAT_RULES]


def categorize(headline, summary=''):
    """Word-boundary matching. Substring matching mis-filed 'gain'/'against'
    as Tech-AI because they contain the letters 'ai'."""
    text = f'{headline} {summary}'
    for cat, rx in CAT_RULES:
        if rx.search(text):
            return cat
    return 'Markets'


def fetch_news():
    if not FINNHUB_KEY:
        raise FetchError('FINNHUB_KEY not set')

    raw = get_json('https://finnhub.io/api/v1/news?category=general'
                   f'&token={FINNHUB_KEY}', label='news')
    if not isinstance(raw, list):
        raise FetchError(f'expected a list, got {type(raw).__name__}')
    if not raw:
        raise FetchError('zero articles returned')

    cutoff = (NOW_UTC - datetime.timedelta(days=7)).timestamp()
    seen, clean = set(), []
    for a in raw:
        if not isinstance(a, dict):
            continue
        h = (a.get('headline') or '').strip()
        url = (a.get('url') or '').strip()
        # Required fields: a headline we can show and a link we can attribute.
        if len(h) < 20 or not url.startswith(('http://', 'https://')):
            continue
        # Near-duplicate collapse: alphanumeric-only prefix as the identity.
        key = re.sub(r'[^a-z0-9]+', '', h.lower())[:60]
        if key in seen:
            continue
        seen.add(key)

        ts = a.get('datetime')
        ts = int(ts) if isinstance(ts, (int, float)) and ts > 0 else 0
        # Drop anything implausibly old; a stale-article flood is a bad feed.
        if ts and ts < cutoff:
            continue

        clean.append({
            'headline': h,
            'summary':  (a.get('summary') or '').strip()[:220],
            'source':   (a.get('source') or '').strip(),
            'url':      url,
            'image':    (a.get('image') or '').strip(),
            'datetime': ts,
            'category': categorize(h, a.get('summary') or ''),
        })

    clean = clean[:C.EXPECTED['news']['total']]
    floor = C.EXPECTED['news']['min_items']
    if len(clean) < floor:
        raise FetchError(f'only {len(clean)} usable headlines (need >= {floor})')
    print(f"  News: {len(clean)} headlines after de-duplication")
    return clean


def render_news_html(articles, fetched_iso):
    cards = []
    for a in articles[:12]:
        sm = a['summary']
        sm = (sm[:130] + '…') if len(sm) > 130 else sm
        summary_html = f'<div class="nc-summary">{esc(sm)}</div>' if sm else ''
        src_html = (f'<div class="nc-foot"><span class="nc-src">{esc(a["source"])}</span></div>'
                    if a['source'] else '')
        cards.append(
            f'<a href="{esc(a["url"])}" target="_blank" rel="noopener noreferrer" class="nc">'
            f'<div class="nc-cat">{esc(a["category"])}</div>'
            f'<div class="nc-headline">{esc(a["headline"])}</div>'
            f'{summary_html}{src_html}</a>'
        )
    return (f'<div id="newsSnap" data-snapshot="{fetched_iso}" style="margin-bottom:16px">'
            f'<div class="snap-stamp">Headline snapshot &middot; {disp(fetched_iso)}</div>'
            f'<div class="news-feed">{"".join(cards)}</div></div>')


def update_signals_html():
    """Server-render the scan date on quantum-signals.html.

    The page was previously written entirely client-side, so the largest
    content page on the site served the literal string "loading..." to every
    crawler where the session date belongs. Reads the JSON already on disk -
    including a preserved last-known-good one - so the date shown always
    matches the signals actually being displayed.
    """
    sig = read_json('data/quantum_signals.json') or {}
    md = sig.get('market_date')
    if not md:
        print("  quantum-signals.html PRESERVED (no market_date)")
        return
    try:
        page = read_file('quantum-signals.html')
        page = inject(page, 'SCAN_DATE',
                      f'<span id="scanTime" style="color:var(--accent);'
                      f'font-weight:600">{esc(md)}</span>')
        write_file('quantum-signals.html', page)
        print(f"  quantum-signals.html rendered (session {md})")
    except Exception as e:
        stage_error('quantum-signals.html write', e)


def update_news_html(feed):
    if not feed or not feed.get('data'):
        print("  news.html PRESERVED (no fresh headlines)")
        return
    try:
        html = read_file('news.html')
        html = inject(html, 'NEWS_SNAP',
                      render_news_html(feed['data'], feed['fetched_utc']))
        # The status line used to be filled only by JavaScript, so every
        # crawler - and every reader with JS blocked - saw the literal string
        # "Loading latest snapshot..." directly under the H1.
        #
        # What is rendered here is a TIMESTAMP FACT, not a freshness claim.
        # "Headline snapshot: <when>" stays true forever; "Live" would become a
        # lie the moment the pipeline stalls, and static HTML cannot know how
        # long it has been sitting there. QM.stamp() upgrades this to the
        # derived freshness state on load, so JS users still see live/paused.
        html = inject(html, 'NEWS_STATUS',
                      f'<div id="newsStatus" class="qm-fresh" style="font-size:11px;'
                      f'font-family:\'Barlow Condensed\',sans-serif;font-weight:600;'
                      f'letter-spacing:.8px;text-transform:uppercase;margin-bottom:12px">'
                      f'Headline snapshot: {disp(feed["fetched_utc"])} &middot; '
                      f'{len(feed["data"])} headlines captured</div>')
        write_file('news.html', html)
        print(f"  news.html rendered (snapshot {disp(feed['fetched_utc'])})")
    except Exception as e:
        stage_error('news.html write', e)


# ---- 5. Quantum Signals -----------------------------------------------------
def compute_rsi(s, period=14):
    d = s.diff()
    ag = d.clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    al = (-d).clip(lower=0).ewm(com=period - 1, min_periods=period).mean()
    return 100 - 100 / (1 + ag / al.replace(0, float('nan')))


def score_ticker(df):
    """Score against 30 binary technical checks -> (score, 'BUY'|'WATCH')."""
    c, v, h, l = df['Close'], df['Volume'], df['High'], df['Low']
    sc = 0
    last = float(c.iloc[-1])

    # Trend / moving averages (10)
    sma5, sma10 = c.rolling(5).mean(), c.rolling(10).mean()
    sma20, sma50 = c.rolling(20).mean(), c.rolling(50).mean()
    ema12, ema26 = c.ewm(span=12).mean(), c.ewm(span=26).mean()
    macd = ema12 - ema26
    msig = macd.ewm(span=9).mean()
    if last > sma5.iloc[-1]:             sc += 1
    if last > sma10.iloc[-1]:            sc += 1
    if last > sma20.iloc[-1]:            sc += 1
    if last > sma50.iloc[-1]:            sc += 1
    if sma5.iloc[-1] > sma10.iloc[-1]:   sc += 1
    if sma10.iloc[-1] > sma20.iloc[-1]:  sc += 1
    if sma20.iloc[-1] > sma50.iloc[-1]:  sc += 1
    if ema12.iloc[-1] > ema26.iloc[-1]:  sc += 1
    if macd.iloc[-1] > 0:                sc += 1
    if macd.iloc[-1] > msig.iloc[-1]:    sc += 1

    # Momentum oscillators (4)
    r7, r14, r21 = compute_rsi(c, 7), compute_rsi(c, 14), compute_rsi(c, 21)
    r14v = float(r14.iloc[-1])
    if 35 < r14v < 65:                   sc += 1
    if r7.iloc[-1] > r14.iloc[-1]:       sc += 1
    if r21.iloc[-1] > 45:                sc += 1
    if float(r14.iloc[-2]) < 40 < r14v:  sc += 1

    # Bollinger Bands (3)
    sd20 = c.rolling(20).std()
    bb_lo, bb_hi = sma20 - 2 * sd20, sma20 + 2 * sd20
    if last > bb_lo.iloc[-1]:            sc += 1
    if last < bb_hi.iloc[-1]:            sc += 1
    if float(c.iloc[-3]) < float(bb_lo.iloc[-3]) and last > float(bb_lo.iloc[-1]):
        sc += 1

    # Volume (3)
    vol20, vol5 = v.rolling(20).mean(), v.rolling(5).mean()
    up = (c.diff() > 0).astype(int)
    if float(v.iloc[-1]) > float(vol20.iloc[-1]):     sc += 1
    if float(vol5.iloc[-1]) > float(vol20.iloc[-1]):  sc += 1
    if float((v * up).rolling(5).mean().iloc[-1]) > \
       float((v * (1 - up)).rolling(5).mean().iloc[-1]):
        sc += 1

    # Rate of change (4)
    roc5 = float((c.iloc[-1] / c.iloc[-6] - 1) * 100)
    roc10 = float((c.iloc[-1] / c.iloc[-11] - 1) * 100)
    roc20 = float((c.iloc[-1] / c.iloc[-21] - 1) * 100)
    if roc5 > 0:    sc += 1
    if roc10 > -3:  sc += 1
    if roc20 > -8:  sc += 1
    if roc5 < 15:   sc += 1

    # 52-week position (2)
    win = min(252, len(df))
    hi52 = float(h.rolling(win).max().iloc[-1])
    lo52 = float(l.rolling(win).min().iloc[-1])
    rng = hi52 - lo52
    if rng > 0:
        pos = (last - lo52) / rng
        if 0.20 < pos < 0.80:  sc += 1
        if pos > 0.30:         sc += 1

    # Stochastic (2)
    denom = (h.rolling(14).max() - l.rolling(14).min()).replace(0, float('nan'))
    sk = (c - l.rolling(14).min()) / denom * 100
    sd = sk.rolling(3).mean()
    if float(sk.iloc[-1]) > 20:                 sc += 1
    if float(sk.iloc[-1]) > float(sd.iloc[-1]): sc += 1

    # Volatility regime (2)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atrp = float(tr.rolling(14).mean().iloc[-1]) / last if last > 0 else 1
    if atrp < 0.05:   sc += 1
    if atrp > 0.005:  sc += 1

    return sc, ('BUY' if sc >= CONFLUENCE_MIN else 'WATCH')


def compute_quantum_signals():
    """Returns the signal payload. Raises FetchError if the scan cannot run,
    so the caller preserves the previous scan rather than publishing nothing."""
    if not HAS_YF:
        raise FetchError('yfinance/pandas not installed')

    print(f"  Downloading {UNIVERSE_N} tickers...")
    raw = None
    last_err = 'no data'
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = yf_download(TICKERS, period='1y', auto_adjust=True,                              progress=False, threads=True)
            if raw is not None and len(raw):
                break
            last_err = 'empty frame'
        except Exception as e:
            last_err = f'{type(e).__name__}: {e}'
        if attempt < MAX_ATTEMPTS:
            wait = _sleep_for(attempt)
            print(f"    signals {last_err}, retry {attempt}/"
                  f"{MAX_ATTEMPTS - 1} in {wait:.0f}s")
            time.sleep(wait)
    if raw is None or not len(raw):
        raise FetchError(f'yfinance returned no data ({last_err})')

    results, skipped = [], []
    for sym in TICKERS:
        try:
            df = frame_for(raw, sym).dropna()
            if len(df) < MIN_SESSIONS:
                skipped.append(sym)
                continue

            sc, direction = score_ticker(df)
            close = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-2])
            chg = round((close / prev - 1) * 100, 2) if prev > 0 else 0.0

            rsi14 = float(compute_rsi(df['Close'], 14).iloc[-1])
            ret22 = float((close / float(df['Close'].iloc[-22]) - 1) * 100) \
                if len(df) > 22 else 0.0

            tr = pd.concat([
                df['High'] - df['Low'],
                (df['High'] - df['Close'].shift()).abs(),
                (df['Low'] - df['Close'].shift()).abs(),
            ], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])

            # Share of overlapping 20-session forward windows in the sampled
            # history that closed higher. A base-rate for the name, NOT a
            # strategy win rate and NOT a backtest of these signals.
            fwd = df['Close'].pct_change(20).shift(-20).dropna()
            up20 = round(float((fwd > 0).mean() * 100), 1) if len(fwd) else None

            results.append({
                's': sym,
                'p': round(close, 2),
                'chg': chg,                                          # 1-session % change
                'r': round(rsi14, 1) if rsi14 == rsi14 else None,   # real RSI(14)
                'r22': round(ret22, 1),
                'sc': sc,
                'd': direction,
                'e': round(close, 2),
                'sl': round(close - STOP_ATR * atr, 2),
                'tp': round(close + TARGET_ATR * atr, 2),
                'up20': up20,
            })
        except Exception:
            skipped.append(sym)
            continue

    if len(results) < UNIVERSE_N * 0.5:
        raise FetchError(f'only {len(results)}/{UNIVERSE_N} tickers scored '
                         f'({len(skipped)} skipped) - refusing to publish')

    results.sort(key=lambda x: (0 if x['d'] == 'BUY' else 1, -x['sc']))
    buys = [r for r in results if r['d'] == 'BUY']
    scores = [r['sc'] for r in results]

    # market_date is the session the DATA belongs to, taken from the frame's
    # own last index. Never the calendar date - a Saturday run must not stamp
    # a Saturday. Cross-check against the calendar and refuse if it is not a
    # real trading day or is implausibly far from the expected session.
    try:
        market_date = raw.index[-1].date()
    except Exception as e:
        raise FetchError(f'cannot read last session date from frame ({e})')

    if not C.is_trading_day(market_date):
        raise FetchError(f'frame last index {market_date} '
                         f'({market_date.strftime("%A")}) is not a trading day')

    behind = C.sessions_behind(market_date, NOW_UTC)
    if behind > 3:
        raise FetchError(
            f'data is {behind} sessions stale (frame ends {market_date}, '
            f'latest completed session is {SESSION_DATE}) - upstream is behind')
    if behind:
        print(f"  NOTE: frame ends {market_date}, {behind} session(s) behind "
              f"{SESSION_DATE} (upstream lag)")
    market_date = str(market_date)

    payload = {
        'updated': NOW_ISO,
        # Stamps the output with the engine version that produced it, so a
        # future methodology change cannot silently reinterpret old records.
        'methodology_version': C.METHODOLOGY_VERSION,
        'market_date': market_date,
        'engine': {
            'universe': UNIVERSE_N,
            'scored': len(results),
            'skipped': len(skipped),
            'n_signals': N_SIGNALS,
            'confluence_min': CONFLUENCE_MIN,
            'min_sessions': MIN_SESSIONS,
            'hold_days': HOLD_DAYS,
            'stop_atr': STOP_ATR,
            'target_atr': TARGET_ATR,
        },
        # legacy key retained so an older cached page never breaks
        'strategy': {'confluence': CONFLUENCE_MIN, 'n_signals': N_SIGNALS,
                     'hold_days': HOLD_DAYS},
        'buy_count': len(buys),
        'total_count': len(results),
        'median_score': int(np.median(scores)) if scores else 0,
        'max_score': int(max(scores)) if scores else 0,
        'signals': results,
    }
    print(f"  Signals: {len(buys)} BUY / {len(results)} scored "
          f"({len(skipped)} skipped) median score {payload['median_score']}")
    return payload


# ---- 5c. Proprietary metrics ------------------------------------------------
# Derived entirely from the scan the pipeline just produced. These are the only
# figures on the site that originate here rather than being sourced from a data
# vendor, so they are computed once, published as JSON, and rendered into the
# index pages as static HTML.
#
# Deliberately NOT built: an order-flow toxicity (VPIN) index and a slippage
# stress index. Both need tick/quote data the pipeline does not collect. There
# is no defensible way to compute them from end-of-day OHLCV, so they are
# absent rather than approximated.

# Descriptive bands on breadth. This is a restatement of one number, not a
# forecast and not a validated regime model - the labels exist so a reader has
# a consistent vocabulary, and the thresholds are published so anyone can
# disagree with them.
BREADTH_BANDS = [
    (60.0, 'Broad participation',
     'A majority of the universe clears the threshold. Trend-following '
     'signals are least selective in this state.'),
    (40.0, 'Mixed participation',
     'Roughly half the universe qualifies. Signal count discriminates less '
     'than usual; the score column matters more than the BUY flag.'),
    (20.0, 'Narrow participation',
     'A minority qualifies. Setups are concentrated in fewer names and '
     'sectors.'),
    (0.0,  'Few qualifying setups',
     'Very little of the universe clears the threshold. The engine is '
     'designed to go quiet here rather than force low-conviction output.'),
]


def _band(breadth_pct):
    for floor, label, note in BREADTH_BANDS:
        if breadth_pct >= floor:
            return {'label': label, 'note': note, 'floor_pct': floor}
    return {'label': 'unknown', 'note': '', 'floor_pct': 0.0}


def compute_breadth(sig):
    """QuantMedia Signal Breadth Index.

        breadth = BUY decisions / successfully scored stocks

    Everything here comes from the scan payload; nothing is estimated.
    """
    rows = sig['signals']
    scores = sorted(r['sc'] for r in rows)
    n = len(scores)
    buys = sum(1 for r in rows if r['d'] == 'BUY')
    breadth = round(100.0 * buys / n, 1) if n else 0.0
    mean = sum(scores) / n if n else 0.0
    var = sum((x - mean) ** 2 for x in scores) / n if n else 0.0

    dist = []
    for lo in range(0, N_SIGNALS + 1, 5):
        hi = min(lo + 4, N_SIGNALS)
        dist.append({'band': f'{lo}-{hi}',
                     'n': sum(1 for s in scores if lo <= s <= hi)})

    return {
        'metric':          'QuantMedia Signal Breadth',
        'market_date':     sig['market_date'],
        'updated_at':      NOW_ISO,
        'eligible_stocks': sig['engine']['universe'],
        'scored_stocks':   n,
        'buy_signals':     buys,
        'breadth_pct':     breadth,
        'median_score':    scores[n // 2] if n else 0,
        'mean_score':      round(mean, 2),
        'score_stdev':     round(var ** 0.5, 2),
        'min_score':       scores[0] if n else 0,
        'max_score':       scores[-1] if n else 0,
        'threshold':       CONFLUENCE_MIN,
        'signal_count':    N_SIGNALS,
        'distribution':    dist,
        'regime_band':     _band(breadth),
        'definition':      ('Share of successfully scored equities whose '
                            'confluence score reached the BUY threshold on '
                            'the stated market date.'),
    }


def compute_sector_confluence(sig):
    """QuantMedia Sector Confluence Index - the same scan, grouped by sector."""
    by_sector = {}
    for r in sig['signals']:
        sec = C.SECTOR_OF.get(r['s'])
        if sec:
            by_sector.setdefault(sec, []).append(r)

    out = []
    for sec, rows in by_sector.items():
        if len(rows) < C.MIN_SECTOR_SIZE:
            continue                      # too few names for an average
        scores = sorted(r['sc'] for r in rows)
        n = len(scores)
        buys = sum(1 for r in rows if r['d'] == 'BUY')
        out.append({
            'sector':        sec,
            'constituents':  len(C.SECTOR_MAP[sec]),
            'scored':        n,
            'buy_signals':   buys,
            'breadth_pct':   round(100.0 * buys / n, 1),
            'mean_score':    round(sum(scores) / n, 2),
            'median_score':  scores[n // 2],
            'top_symbol':    max(rows, key=lambda r: r['sc'])['s'],
            'top_score':     max(r['sc'] for r in rows),
        })

    # Rank on mean score; breadth breaks ties.
    out.sort(key=lambda s: (-s['mean_score'], -s['breadth_pct']))
    for i, s in enumerate(out, 1):
        s['rank'] = i

    return {
        'metric':      'QuantMedia Sector Confluence',
        'market_date': sig['market_date'],
        'updated_at':  NOW_ISO,
        'threshold':   CONFLUENCE_MIN,
        'signal_count': N_SIGNALS,
        'sector_basis': ('Hand-maintained QuantMedia sector grouping, '
                         'approximating GICS. Not an official classification.'),
        'definition':  ('Mean confluence score and BUY breadth per sector, '
                        'computed from the same post-close scan.'),
        'sectors':     out,
    }


def render_index_pages(breadth, sectors):
    """Write the current readings into the index pages as STATIC HTML.

    This is the point of the whole exercise: a crawler or an assistant that
    fetches the page must see the numbers in the markup, not a spinner that
    resolves after JavaScript. The QM: anchors keep the surrounding editorial
    content untouched.
    """
    b = breadth
    band = b['regime_band']
    rows = ''.join(
        f'<tr><td class="qm-rank">{s["rank"]}</td>'
        f'<td class="qm-sector">{esc(s["sector"])}</td>'
        f'<td class="qm-num">{s["mean_score"]:.2f}</td>'
        f'<td class="qm-num">{s["median_score"]}</td>'
        f'<td class="qm-num">{s["buy_signals"]}/{s["scored"]}</td>'
        f'<td class="qm-num">{s["breadth_pct"]:.1f}%</td>'
        f'<td class="qm-num">{esc(s["top_symbol"])} ({s["top_score"]})</td></tr>'
        for s in sectors['sectors'])

    dist = ''.join(
        f'<tr><td class="qm-num">{esc(d["band"])}</td>'
        f'<td class="qm-num">{d["n"]}</td></tr>'
        for d in b['distribution'] if d['n'])

    breadth_html = (
        f'<p class="qm-reading"><strong>{b["buy_signals"]} of '
        f'{b["scored_stocks"]}</strong> successfully scored equities reached '
        f'the {b["threshold"]}/{b["signal_count"]} threshold on '
        f'<strong>{b["market_date"]}</strong>.</p>'
        f'<table class="qm-kv"><tbody>'
        f'<tr><th>Signal breadth</th><td><strong>{b["breadth_pct"]:.1f}%</strong></td></tr>'
        f'<tr><th>Median score</th><td>{b["median_score"]}/{b["signal_count"]}</td></tr>'
        f'<tr><th>Mean score</th><td>{b["mean_score"]:.2f}</td></tr>'
        f'<tr><th>Score dispersion (SD)</th><td>{b["score_stdev"]:.2f}</td></tr>'
        f'<tr><th>Score range</th><td>{b["min_score"]}&ndash;{b["max_score"]}</td></tr>'
        f'<tr><th>Universe / scored</th><td>{b["eligible_stocks"]} / {b["scored_stocks"]}</td></tr>'
        f'<tr><th>Reading</th><td>{esc(band["label"])}</td></tr>'
        f'<tr><th>Market date</th><td>{b["market_date"]}</td></tr>'
        f'<tr><th>Generated</th><td>{b["updated_at"]}</td></tr>'
        f'</tbody></table>'
        f'<p class="qm-note">{esc(band["note"])}</p>'
        f'<h3>Score distribution</h3>'
        f'<table class="qm-kv"><thead><tr><th>Signals active</th>'
        f'<th>Stocks</th></tr></thead><tbody>{dist}</tbody></table>')

    sector_html = (
        f'<p class="qm-reading">Sector readings for '
        f'<strong>{sectors["market_date"]}</strong>, ranked by mean confluence '
        f'score across {sum(s["scored"] for s in sectors["sectors"])} scored '
        f'equities.</p>'
        f'<div class="qm-tablewrap"><table class="qm-kv"><thead><tr>'
        f'<th>#</th><th>Sector</th><th>Mean</th><th>Median</th>'
        f'<th>BUY</th><th>Breadth</th><th>Strongest</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
        f'<p class="qm-note">Generated {sectors["updated_at"]}. '
        f'{esc(sectors["sector_basis"])}</p>')

    for rel, marker, html in (
            ('indices/signal-breadth.html', 'BREADTH', breadth_html),
            ('indices/sector-confluence.html', 'SECTORS', sector_html)):
        try:
            page = read_file(rel)
        except FileNotFoundError:
            print(f"  WARNING: {rel} missing - skipped")
            continue
        write_file(rel, inject(page, marker, html))
        print(f"  {rel} rendered")


HISTORY_CAP = 750        # ~3 years of sessions; keeps the file small


def append_history(rel, row, metric_name):
    """Append one row per market date to a history series.

    Rules, enforced here rather than trusted to the caller:
      * exactly one entry per market_date - an existing row for the same date
        is replaced, never duplicated
      * the series is only ever extended from real production output; there is
        NO backfill, because the scan was not run historically under this
        methodology and inventing the values would be fabrication
      * capped at HISTORY_CAP rows so the file stays small enough to serve
    """
    hist = read_json(rel) or {}
    series = [r for r in hist.get('series', [])
              if r.get('market_date') != row['market_date']]
    series.append(row)
    series.sort(key=lambda r: r['market_date'])
    return {
        'metric':          f'{metric_name} - history',
        'methodology_version': C.METHODOLOGY_VERSION,
        'updated_at':      NOW_ISO,
        'threshold':       CONFLUENCE_MIN,
        'signal_count':    N_SIGNALS,
        'observations':    len(series[-HISTORY_CAP:]),
        'note':            ('History begins when this series was first '
                            'published and is not backfilled: the scan was not '
                            'run historically under the current methodology, '
                            'so earlier values do not exist.'),
        'series':          series[-HISTORY_CAP:],
    }


# ---- 5b. Market bar ---------------------------------------------------------
# Sourced from yfinance so the values are the real instruments. The previous
# client-side version proxied gold with the PAX-Gold token and WTI with a
# CoinGecko id, which are not those markets.
BAR_SYMBOLS = [
    ('^GSPC',     'S&P 500'),
    ('^IXIC',     'Nasdaq'),
    ('^DJI',      'Dow'),
    ('^VIX',      'VIX'),
    ('GC=F',      'Gold'),
    ('CL=F',      'WTI'),
    ('DX-Y.NYB',  'DXY'),
    ('EURUSD=X',  'EUR/USD'),
    ('BTC-USD',   'BTC'),
]


def fetch_market_bar():
    if not HAS_YF:
        raise FetchError('yfinance not installed')

    syms = [s for s, _ in BAR_SYMBOLS]
    raw = yf_download(syms, period='5d', auto_adjust=False,
                      progress=False, threads=True)
    if raw is None or not len(raw):
        raise FetchError('yfinance returned no rows')

    clo, chi = C.BOUNDS['bar_chg_pct']
    out = []
    for sym, label in BAR_SYMBOLS:
        try:
            close = frame_for(raw, sym)['Close'].dropna() if isinstance(raw.columns, pd.MultiIndex) else raw['Close'].dropna()
            if len(close) < 2:
                continue
            last, prev = float(close.iloc[-1]), float(close.iloc[-2])
            if last <= 0 or prev <= 0:
                continue
            chg = (last / prev - 1) * 100
            if not (clo <= chg <= chi):
                continue
            out.append({'s': sym, 'l': label, 'p': round(last, 4),
                        'c': round(chg, 2)})
        except Exception:
            continue

    floor = C.EXPECTED['bar']['min_items']
    if len(out) < floor:
        raise FetchError(f'only {len(out)}/{len(BAR_SYMBOLS)} bar symbols '
                         f'valid (need >= {floor})')
    print(f"  Market bar: {len(out)}/{len(BAR_SYMBOLS)} symbols valid")
    return out


# ---- 6. Sitemap -------------------------------------------------------------
# Only these URLs are genuinely regenerated every run. Editorial pages keep
# their real lastmod so <lastmod> stays a truthful modification signal.
DATA_DRIVEN = ('/quantum-signals.html', '/markets.html', '/news.html',
               '/stocks.html', '/')


def update_sitemap(data_date):
    try:
        xml = read_file('sitemap.xml')

        def bump(m):
            block = m.group(0)
            loc = re.search(r'<loc>([^<]+)</loc>', block)
            if not loc:
                return block
            path = loc.group(1).replace('https://quantmedia.io', '') or '/'
            if path in DATA_DRIVEN:
                return re.sub(r'<lastmod>[^<]*</lastmod>',
                              f'<lastmod>{data_date}</lastmod>', block)
            return block

        write_file('sitemap.xml', re.sub(r'<url>.*?</url>', bump, xml, flags=re.DOTALL))
        print(f"  sitemap.xml: data-driven URLs -> {data_date}")
    except Exception as e:
        stage_error('sitemap', e)


# ---- 7. Feed orchestration --------------------------------------------------
def resolve_feed(name, fetcher, rel_path):
    """The last-known-good contract, applied identically to every source.

        fresh + valid   -> publish it                        (status: fresh)
        fetch failed    -> re-publish previous snapshot       (status: preserved)
                           VERBATIM, keeping its original timestamp so the
                           site can say how old it is instead of implying it
                           is current
        no previous     -> return None; the page renders its own explicit
                           non-live fallback                  (status: unavailable)

    A failure here can only ever leave production exactly as it was. It can
    never blank a section or overwrite good data with placeholders.
    """
    try:
        fresh = fetcher()
        if fresh:
            STATUS[name] = 'fresh'
            return {'data': fresh, 'fetched_utc': NOW_ISO, 'stale': False}
        reason = 'fetcher returned nothing'
    except FetchError as e:
        reason = str(e)
    except Exception as e:                      # never let one source abort
        reason = f'{type(e).__name__}: {e}'

    stage_error(name, reason)

    prev = read_json(rel_path)
    if prev and prev.get('data'):
        prev_ts = prev.get('fetched_utc', NOW_ISO)
        age = (NOW_UTC - datetime.datetime.strptime(
            prev_ts, '%Y-%m-%dT%H:%M:%SZ').replace(
                tzinfo=datetime.timezone.utc)).total_seconds() / 3600 \
            if _iso_ok(prev_ts) else None
        print(f"  {name}: PRESERVED previous snapshot from {prev_ts} "
              f"({C.freshness_state(age)})")
        STATUS[name] = 'preserved'
        return {'data': prev['data'], 'fetched_utc': prev_ts, 'stale': True}

    print(f"  {name}: UNAVAILABLE - no fresh data and no snapshot on disk")
    STATUS[name] = 'unavailable'
    return None


def _iso_ok(ts):
    try:
        datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ')
        return True
    except Exception:
        return False


def feed_age_hours(feed):
    if not feed or not _iso_ok(feed.get('fetched_utc', '')):
        return None
    ts = datetime.datetime.strptime(
        feed['fetched_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(
            tzinfo=datetime.timezone.utc)
    return (NOW_UTC - ts).total_seconds() / 3600


# Payload validation now lives in two places, both closer to where it matters:
#   * each fetch_*() raises FetchError before a bad payload is ever accepted,
#     so last-known-good kicks in automatically;
#   * scripts/validate_site.py re-checks everything on disk before the commit.
# There is deliberately no third copy here to drift out of sync.


# ---- Status ledger ----------------------------------------------------------
def build_status(fx, cx, nx, bar, sig_on_disk, signals_fresh):
    """Public, secret-free freshness ledger served at /data/status.json.

    The frontend reads this to decide whether it may say "latest snapshot" or
    must downgrade to "delayed"/"paused". Humans read it to debug a stall
    without opening the Actions log.
    """
    markets_ages = [a for a in (feed_age_hours(fx), feed_age_hours(cx),
                                feed_age_hours(bar)) if a is not None]
    markets_age = max(markets_ages) if markets_ages else None
    news_age = feed_age_hours(nx)

    sig_updated = sig_on_disk.get('updated')
    sig_age = None
    if _iso_ok(sig_updated or ''):
        sig_age = (NOW_UTC - datetime.datetime.strptime(
            sig_updated, '%Y-%m-%dT%H:%M:%SZ').replace(
                tzinfo=datetime.timezone.utc)).total_seconds() / 3600

    md = sig_on_disk.get('market_date')
    behind = None
    if md:
        try:
            behind = C.sessions_behind(md, NOW_UTC)
        except Exception:
            behind = None

    # Signal freshness is measured in SESSIONS, not hours: a Friday scan read
    # on Sunday is current, not two days stale.
    if behind is None:
        sig_state = 'unknown'
    elif behind == 0:
        sig_state = 'fresh'
    elif behind == 1:
        sig_state = 'recent'
    elif behind <= 5:
        sig_state = 'delayed'
    else:
        sig_state = 'paused'

    def state(feed, age):
        if not feed:
            return 'unavailable'
        return C.freshness_state(age)

    overall = 'SUCCESS'
    if STATUS.get('signals') == 'unavailable' or sig_state == 'paused':
        overall = 'FAILED'
    elif any(v in ('preserved', 'unavailable') for v in STATUS.values()) or ERRORS:
        overall = 'PARTIAL'

    return {
        # A unique id per run. The deploy check polls the live file for THIS
        # value, so an HTTP 200 serving a cached older copy cannot be mistaken
        # for a successful deployment.
        'pipeline_run_id':      RUN_ID,
        'generated_at':         NOW_ISO,
        'last_pipeline_run':    NOW_ISO,     # retained: older pages read this
        'pipeline_result':      overall,
        'latest_us_session':    str(SESSION_DATE),

        'markets_updated':      (fx or cx or bar or {}).get('fetched_utc'),
        'news_updated':         (nx or {}).get('fetched_utc'),
        'signals_updated':      sig_updated,
        'signals_market_date':  md,
        'signals_sessions_behind': behind,

        'markets_status':       state(fx or cx or bar, markets_age),
        'news_status':          state(nx, news_age),
        'signals_status':       sig_state,

        'sources': {
            'forex':   STATUS.get('forex', 'unknown'),
            'crypto':  STATUS.get('crypto', 'unknown'),
            'news':    STATUS.get('news', 'unknown'),
            'bar':     STATUS.get('bar', 'unknown'),
            'signals': STATUS.get('signals', 'unknown'),
        },
        'errors': ERRORS,
    }


def print_health_summary(status, changed_hint=None):
    bar = '=' * 62
    label = {'fresh': 'fresh', 'preserved': 'preserved previous',
             'unavailable': 'UNAVAILABLE', 'unknown': 'unknown'}
    print(f"\n{bar}\nPIPELINE HEALTH SUMMARY\n{bar}")
    print(f"  Pipeline run:         {status['pipeline_result']}")
    for src in ('forex', 'crypto', 'news', 'bar', 'signals'):
        print(f"  {src.capitalize():<21} {label.get(status['sources'][src], '?')}")
    print(f"  Signals market date:  {status['signals_market_date']} "
          f"({status['signals_sessions_behind']} session(s) behind)")
    print(f"  Latest US session:    {status['latest_us_session']}")
    print(f"  Markets status:       {status['markets_status']}")
    print(f"  News status:          {status['news_status']}")
    print(f"  Signals status:       {status['signals_status']}")
    if changed_hint is not None:
        print(f"  Files written:        {changed_hint}")
    print(f"  Errors:               {len(status['errors'])}")
    for e in status['errors']:
        print(f"    - {e}")
    print(bar)

    if os.environ.get('GITHUB_ACTIONS'):
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            try:
                with open(summary, 'a', encoding='utf-8') as f:
                    f.write(f"### Pipeline: {status['pipeline_result']}\n\n")
                    f.write('| Source | Result |\n|---|---|\n')
                    for src in ('forex', 'crypto', 'news', 'bar', 'signals'):
                        f.write(f"| {src} | {status['sources'][src]} |\n")
                    f.write(f"\n- Signals market date: "
                            f"`{status['signals_market_date']}` "
                            f"({status['signals_sessions_behind']} behind)\n")
                    f.write(f"- Latest US session: "
                            f"`{status['latest_us_session']}`\n")
                    for e in status['errors']:
                        f.write(f"- :warning: {e}\n")
            except Exception:
                pass


# ---- Main -------------------------------------------------------------------
def main():
    sep = '=' * 62
    print(f"\n{sep}\nQuantMedia Daily Update -- {NOW_ISO}")
    print(f"Latest completed US session: {SESSION_DATE} "
          f"({SESSION_DATE.strftime('%A')})\n{sep}\n")
    os.makedirs(DATA_DIR, exist_ok=True)

    # Each source is resolved independently. A failure in any one of them
    # cannot affect the others - that is the whole point of resolve_feed.
    print("[1/6] Forex...")
    fx = resolve_feed('forex', fetch_forex, 'data/markets_fx.json')
    print("[2/6] Crypto...")
    cx = resolve_feed('crypto', fetch_crypto, 'data/markets_crypto.json')
    print("[3/6] News...")
    nx = resolve_feed('news', fetch_news, 'data/news.json')
    print("[4/6] Market bar...")
    bar = resolve_feed('bar', fetch_market_bar, 'data/markets_bar.json')

    print("[5/6] Signals...")
    signals = None
    try:
        signals = compute_quantum_signals()
        STATUS['signals'] = 'fresh'
    except FetchError as e:
        stage_error('signals', e)
    except Exception as e:
        stage_error('signals', f'{type(e).__name__}: {e}')
    if signals is None:
        prev = read_json('data/quantum_signals.json')
        if prev and prev.get('signals'):
            print(f"  signals: PRESERVED previous scan "
                  f"(market_date {prev.get('market_date')})")
            STATUS['signals'] = 'preserved'
        else:
            print("  signals: UNAVAILABLE - no previous scan on disk")
            STATUS['signals'] = 'unavailable'

    print("[6/6] Publish...")
    written = []
    # Only feeds that resolved get written. A None feed leaves the existing
    # file untouched - never truncated, never emptied.
    for rel, feed in (('data/markets_fx.json', fx),
                      ('data/markets_crypto.json', cx),
                      ('data/news.json', nx),
                      ('data/markets_bar.json', bar)):
        if feed and not feed['stale']:
            write_json(rel, feed)
            written.append(rel)
    if signals:
        write_json('data/quantum_signals.json', signals)
        written.append('data/quantum_signals.json')

    update_markets_html(fx, cx)
    update_news_html(nx)
    update_signals_html()

    # Republish the methodology config so the site copy, the validator and any
    # external reader all resolve to the same numbers.
    write_json('data/signal_config.json', C.signal_config())
    written.append('data/signal_config.json')

    # Proprietary metrics, derived from the scan on disk (fresh or preserved).
    sig_now = read_json('data/quantum_signals.json')
    if sig_now and sig_now.get('signals'):
        try:
            breadth = compute_breadth(sig_now)
            sectors = compute_sector_confluence(sig_now)
            write_json('data/signal_breadth.json', breadth)
            write_json('data/sector_confluence.json', sectors)
            written += ['data/signal_breadth.json', 'data/sector_confluence.json']
            # Only extend the series when the scan is genuinely fresh, or a
            # preserved payload would re-append the same session every run.
            if signals:
                write_json('data/breadth_history.json', append_history(
                    'data/breadth_history.json',
                    {'market_date': breadth['market_date'],
                     'breadth_pct': breadth['breadth_pct'],
                     'buy_signals': breadth['buy_signals'],
                     'scored': breadth['scored_stocks'],
                     'median_score': breadth['median_score'],
                     'mean_score': breadth['mean_score']},
                    'QuantMedia Signal Breadth'))
                write_json('data/sector_confluence_history.json', append_history(
                    'data/sector_confluence_history.json',
                    {'market_date': sectors['market_date'],
                     'sectors': [{'sector': s['sector'], 'mean_score': s['mean_score'],
                                  'median_score': s['median_score'], 'buy_pct': s['breadth_pct'],
                                  'rank': s['rank']} for s in sectors['sectors']]},
                    'QuantMedia Sector Confluence'))
                written += ['data/breadth_history.json',
                            'data/sector_confluence_history.json']
            render_index_pages(breadth, sectors)
            print(f"  Metrics: breadth {breadth['breadth_pct']}% "
                  f"({breadth['buy_signals']}/{breadth['scored_stocks']}), "
                  f"{len(sectors['sectors'])} sectors ranked")
        except Exception as e:
            stage_error('metrics', f'{type(e).__name__}: {e}')

    sig_on_disk = read_json('data/quantum_signals.json') or {}
    status = build_status(fx, cx, nx, bar, sig_on_disk, signals is not None)
    write_json('data/status.json', status)
    written.append('data/status.json')

    # lastmod tracks the session the data belongs to, not "today".
    if signals:
        update_sitemap(sig_on_disk.get('market_date') or str(SESSION_DATE))
    else:
        print("  sitemap.xml: unchanged (no fresh signal data)")

    print_health_summary(status, changed_hint=len(written))

    # Exit 0 even on partial failure: whatever succeeded must still deploy.
    # The workflow turns the run red AFTER the push, so CI stays loud without
    # holding good data hostage to one dead upstream.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
