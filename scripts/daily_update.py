#!/usr/bin/env python3
"""
QuantMedia Daily Update Pipeline
=================================
Runs nightly via GitHub Actions (Mon-Fri, 23:30 UTC).
1. Fetches forex rates  -> pre-renders markets.html fxGrid
2. Fetches crypto prices -> pre-renders markets.html cryptoGrid
3. Fetches financial news -> pre-renders news.html snapshot
4. Computes technical signals for ~200 S&P 500 stocks -> data/quantum_signals.json
5. Updates sitemap.xml lastmod
"""

import json, re, os, sys, datetime, time, traceback
import requests
import pandas as pd
import numpy as np

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("WARNING: yfinance not available, skipping signal computation")

# ─── Config ──────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date.today().isoformat()
NOW_ISO = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
FINNHUB_KEY = os.environ.get('FINNHUB_KEY', 'd6o5n7hr01qu09ci6v60d6o5n7hr01qu09ci6v6g')

# S&P 500 large-cap universe (200 most liquid)
SP500_TICKERS = [
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
    'ON','WOLF','ENPH','FSLR','RUN','ARRY','SEDG','CSIQ','BA','LHX','GD','NOC','HII','TDG','HEI','TXT','AXON',
    'OXY','PSX','VLO','MPC','HAL','SLB','BKR','DVN','FANG',
    'FCX','NEM','GOLD','AEM','WPM','KGC','AGI','OR','PG','APH',
    'ECL','EMR','ROK','PH','IR','AME','ROP','FTV','OTIS','CARR',
    'BX','KKR','APO','ARES','CG','BAM','TPG','HLNE','GS','MS',
]
SP500_TICKERS = list(dict.fromkeys(SP500_TICKERS))  # deduplicate


# ─── Helpers ─────────────────────────────────────────────────────────────────
def fmtprice(v, decimals=4):
    if v is None or np.isnan(v): return '—'
    if v >= 10000: return f'{v:,.0f}'
    if v >= 1000:  return f'{v:,.2f}'
    if v >= 10:    return f'{v:.4f}'
    return f'{v:.4f}'

def fmtchg(v):
    if v is None or np.isnan(v): return ('—', 'nt')
    sign = '+' if v >= 0 else ''
    cls = 'pos' if v >= 0 else 'neg'
    return (f'{sign}{v:.2f}%', cls)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def inject(html, marker, inner_html):
    """Replace content between <!-- QM:MARKER:START --> and <!-- QM:MARKER:END -->"""
    pattern = rf'(<!-- QM:{marker}:START -->).*?(<!-- QM:{marker}:END -->)'
    replacement = rf'\1\n{inner_html}\n\2'
    new_html, n = re.subn(pattern, replacement, html, flags=re.DOTALL)
    if n == 0:
        print(f"  WARNING: marker QM:{marker} not found in HTML")
    return new_html


# ─── 1. Forex ────────────────────────────────────────────────────────────────
FOREX_PAIRS = [
    # (symbol, name, base_curr, quote_curr)
    ('EUR/USD', 'Euro / Dollar',    'EUR', 'USD', 'majors'),
    ('GBP/USD', 'Sterling / Dollar','GBP', 'USD', 'majors'),
    ('USD/JPY', 'Dollar / Yen',     'USD', 'JPY', 'majors'),
    ('USD/CHF', 'Dollar / Franc',   'USD', 'CHF', 'majors'),
    ('AUD/USD', 'Aussie / Dollar',  'AUD', 'USD', 'majors'),
    ('USD/CAD', 'Dollar / Loonie',  'USD', 'CAD', 'majors'),
    ('USD/MXN', 'Dollar / Peso',    'USD', 'MXN', 'crosses'),
    ('USD/BRL', 'Dollar / Real',    'USD', 'BRL', 'crosses'),
    ('USD/CNY', 'Dollar / Yuan',    'USD', 'CNY', 'crosses'),
    ('USD/INR', 'Dollar / Rupee',   'USD', 'INR', 'crosses'),
    ('USD/KRW', 'Dollar / Won',     'USD', 'KRW', 'crosses'),
    ('USD/SGD', 'Dollar / S$',      'USD', 'SGD', 'crosses'),
    ('EUR/GBP', 'Euro / Sterling',  'EUR', 'GBP', 'other'),
    ('EUR/JPY', 'Euro / Yen',       'EUR', 'JPY', 'other'),
    ('EUR/CHF', 'Euro / Franc',     'EUR', 'CHF', 'other'),
    ('GBP/JPY', 'Sterling / Yen',   'GBP', 'JPY', 'other'),
    ('NZD/USD', 'Kiwi / Dollar',    'NZD', 'USD', 'other'),
    ('USD/SEK', 'Dollar / Krona',   'USD', 'SEK', 'other'),
]

def fetch_forex():
    try:
        r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=12)
        r.raise_for_status()
        rates = r.json().get('rates', {})
        result = {}
        for sym, name, base, quote, group in FOREX_PAIRS:
            try:
                if base == 'USD':
                    price = rates[quote]
                elif quote == 'USD':
                    price = 1.0 / rates[base]
                else:
                    price = rates[quote] / rates[base]
                result[sym] = {'price': round(price, 5), 'name': name, 'group': group}
            except (KeyError, ZeroDivisionError):
                result[sym] = {'price': None, 'name': name, 'group': group}
        print(f"  Forex: fetched {len([v for v in result.values() if v['price']])} pairs")
        return result
    except Exception as e:
        print(f"  Forex fetch failed: {e}")
        return {}

def render_forex_html(forex):
    def drow(sym, name, price):
        p = fmtprice(price, 4) if price else '—'
        cls = 'nt'
        return (f'<div class="drow"><div><div class="dsym">{sym}</div>'
                f'<div class="dfull">{name}</div></div>'
                f'<div class="dmono">{p}</div>'
                f'<div style="text-align:right"><span class="badge {cls}">live</span></div></div>')

    groups = {'majors': [], 'crosses': [], 'other': []}
    for sym, name, base, quote, group in FOREX_PAIRS:
        d = forex.get(sym, {})
        groups[group].append(drow(sym, name, d.get('price')))

    ts = datetime.datetime.utcnow().strftime('%H:%M UTC')
    html = (
        f'<div class="grid-3" id="fxGrid">'
        f'<div class="panel"><div class="panel-head">Majors</div>{"".join(groups["majors"])}</div>'
        f'<div class="panel"><div class="panel-head">USD Crosses</div>{"".join(groups["crosses"])}</div>'
        f'<div class="panel"><div class="panel-head">Other Pairs</div>{"".join(groups["other"])}</div>'
        f'</div>'
    )
    return html


# ─── 2. Crypto ───────────────────────────────────────────────────────────────
CRYPTO_ASSETS = [
    ('BTC',  'Bitcoin',    'bitcoin'),
    ('ETH',  'Ethereum',   'ethereum'),
    ('SOL',  'Solana',     'solana'),
    ('BNB',  'BNB',        'binancecoin'),
    ('XRP',  'XRP',        'ripple'),
    ('ADA',  'Cardano',    'cardano'),
    ('AVAX', 'Avalanche',  'avalanche-2'),
    ('LINK', 'Chainlink',  'chainlink'),
    ('DOT',  'Polkadot',   'polkadot'),
    ('UNI',  'Uniswap',    'uniswap'),
    ('LTC',  'Litecoin',   'litecoin'),
    ('BCH',  'Bitcoin Cash','bitcoin-cash'),
]

def fetch_crypto():
    ids = ','.join(a[2] for a in CRYPTO_ASSETS)
    try:
        try:
            r = requests.get(
                f'https://api.coingecko.com/api/v3/simple/price'
                f'?ids={ids}&vs_currencies=usd&include_24hr_change=true',
                timeout=15
            )
        except Exception:
            r = requests.get(
                f'https://api.coingecko.com/api/v3/simple/price'
                f'?ids={ids}&vs_currencies=usd&include_24hr_change=true',
                timeout=15, verify=False
            )
        r.raise_for_status()
        data = r.json()
        result = {}
        for sym, name, cg_id in CRYPTO_ASSETS:
            d = data.get(cg_id, {})
            result[sym] = {
                'name': name,
                'price': d.get('usd'),
                'chg': d.get('usd_24h_change'),
            }
        print(f"  Crypto: fetched {len([v for v in result.values() if v['price']])} assets")
        return result
    except Exception as e:
        print(f"  Crypto fetch failed: {e}")
        return {}

def render_crypto_html(crypto):
    def drow(sym, name, price, chg):
        if price and price >= 1000:
            p = f'${price:,.0f}'
        elif price and price >= 1:
            p = f'${price:,.2f}'
        elif price:
            p = f'${price:.4f}'
        else:
            p = '—'
        chg_str, cls = fmtchg(chg)
        return (f'<div class="drow"><div><div class="dsym">{sym}</div>'
                f'<div class="dfull">{name}</div></div>'
                f'<div class="dmono">{p}</div>'
                f'<div style="text-align:right"><span class="badge {cls}">{chg_str}</span></div></div>')

    panel1 = ''.join(drow(s, crypto.get(s,{}).get('name',s),
                          crypto.get(s,{}).get('price'), crypto.get(s,{}).get('chg'))
                     for s, _, _ in CRYPTO_ASSETS[:6])
    panel2 = ''.join(drow(s, crypto.get(s,{}).get('name',s),
                          crypto.get(s,{}).get('price'), crypto.get(s,{}).get('chg'))
                     for s, _, _ in CRYPTO_ASSETS[6:])

    return (
        f'<div class="grid-2" id="cryptoGrid">'
        f'<div class="panel"><div class="panel-head">Digital Assets I</div>{panel1}</div>'
        f'<div class="panel"><div class="panel-head">Digital Assets II</div>{panel2}</div>'
        f'</div>'
    )


# ─── 3. Markets HTML update ───────────────────────────────────────────────────
def update_markets_html(forex, crypto):
    path = os.path.join(ROOT, 'markets.html')
    html = read_file(path)

    if forex:
        new_fx = render_forex_html(forex)
        html = inject(html, 'FOREX', new_fx)

    if crypto:
        new_cr = render_crypto_html(crypto)
        html = inject(html, 'CRYPTO', new_cr)

    # Update lastUp timestamp
    ts = datetime.datetime.utcnow().strftime('%b %d %Y, %H:%M UTC')
    html = re.sub(
        r'(<div id="lastUp"[^>]*>).*?(</div>)',
        rf'\1Last updated: {ts}\2',
        html
    )

    write_file(path, html)
    print(f"  markets.html updated")


# ─── 4. News ──────────────────────────────────────────────────────────────────
CAT_RULES = [
    ('Fed · Rates',  ['fed', 'fomc', 'rate', 'inflation', 'cpi', 'ppi', 'powell', 'treasury', 'yield', 'bond', 'monetary']),
    ('Tech · AI',    ['tech', 'ai', 'nvidia', 'microsoft', 'apple', 'google', 'meta', 'chip', 'semiconductor', 'cloud', 'openai']),
    ('Energy',       ['oil', 'opec', 'gas', 'energy', 'crude', 'brent', 'wti', 'lng', 'pipeline', 'refin']),
    ('Crypto',       ['bitcoin', 'btc', 'ethereum', 'crypto', 'blockchain', 'defi', 'nft', 'binance', 'coinbase']),
    ('Earnings',     ['earning', 'eps', 'revenue', 'profit', 'guidance', 'quarterly', 'beat', 'miss', 'outlook']),
    ('Volatility',   ['vix', 'volatil', 'selloff', 'crash', 'surge', 'plunge', 'rally', 'fear', 'panic', 'correction']),
    ('Markets',      ['s&p', 'nasdaq', 'dow', 'stock', 'market', 'equity', 'index', 'wall street', 'shares', 'trade']),
]

def categorize(title, summary=''):
    text = (title + ' ' + summary).lower()
    for cat, kws in CAT_RULES:
        if any(k in text for k in kws):
            return cat
    return 'Markets'

def fetch_news():
    try:
        r = requests.get(
            f'https://finnhub.io/api/v1/news?category=general&token={FINNHUB_KEY}',
            timeout=15
        )
        r.raise_for_status()
        articles = r.json()
        seen = set()
        clean = []
        for a in articles:
            h = a.get('headline', '').strip()
            if not h or h in seen or len(h) < 20:
                continue
            seen.add(h)
            clean.append({
                'headline': h,
                'summary': a.get('summary', '')[:200],
                'source': a.get('source', ''),
                'url': a.get('url', '#'),
                'datetime': a.get('datetime', 0),
                'category': categorize(h, a.get('summary', '')),
            })
        clean = clean[:16]
        print(f"  News: fetched {len(clean)} headlines")
        return clean
    except Exception as e:
        print(f"  News fetch failed: {e}")
        return []

def render_news_html(articles):
    if not articles:
        return ''
    ts = datetime.datetime.utcnow().strftime('%b %d, %H:%M UTC')
    cards = []
    for a in articles[:12]:
        src = a['source']
        cat = a['category']
        url = a['url'] or '#'
        h = a['headline']
        sm = a['summary'][:130] + '…' if len(a['summary']) > 130 else a['summary']
        cards.append(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="nc">'
            f'<div class="nc-cat">{cat}</div>'
            f'<div class="nc-headline">{h}</div>'
            f'{"<div class=nc-summary>"+sm+"</div>" if sm else ""}'
            f'<div class="nc-foot"><span class="nc-src">{src}</span></div>'
            f'</a>'
        )
    grid = f'<div class="news-feed">{"".join(cards)}</div>'
    snap = (
        f'<div id="newsSnap" style="margin-bottom:16px">'
        f'<div style="font-size:11px;color:var(--accent);font-family:\'Barlow Condensed\',sans-serif;'
        f'font-weight:600;letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px">'
        f'Latest headlines — {ts}</div>'
        f'{grid}'
        f'</div>'
        f'<script>if(window._newsLoaded)document.getElementById("newsSnap").style.display="none";</script>'
    )
    return snap

def update_news_html(articles):
    path = os.path.join(ROOT, 'news.html')
    html = read_file(path)
    if articles:
        snap_html = render_news_html(articles)
        html = inject(html, 'NEWS_SNAP', snap_html)
    write_file(path, html)
    print(f"  news.html updated")


# ─── 5. Quantum Signals ──────────────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_signals_for_ticker(df):
    """
    Compute signal score for a single ticker.
    Returns score (int) and direction ('BUY'/'WATCH').
    Indicators (30 total):
    """
    if len(df) < 60:
        return 0, 'WATCH'

    c = df['Close']
    v = df['Volume']
    h = df['High']
    l = df['Low']

    score = 0

    # ── Moving Averages (10 signals) ──────────────────────────────────────
    sma5   = c.rolling(5).mean()
    sma10  = c.rolling(10).mean()
    sma20  = c.rolling(20).mean()
    sma50  = c.rolling(50).mean()
    ema12  = c.ewm(span=12).mean()
    ema26  = c.ewm(span=26).mean()

    last = c.iloc[-1]
    if last > sma5.iloc[-1]:   score += 1   # 1
    if last > sma10.iloc[-1]:  score += 1   # 2
    if last > sma20.iloc[-1]:  score += 1   # 3
    if last > sma50.iloc[-1]:  score += 1   # 4
    if sma5.iloc[-1] > sma10.iloc[-1]: score += 1  # 5
    if sma10.iloc[-1] > sma20.iloc[-1]: score += 1 # 6
    if sma20.iloc[-1] > sma50.iloc[-1]: score += 1 # 7
    if ema12.iloc[-1] > ema26.iloc[-1]: score += 1 # 8

    # MACD
    macd = ema12 - ema26
    signal_line = macd.ewm(span=9).mean()
    if macd.iloc[-1] > 0:               score += 1  # 9
    if macd.iloc[-1] > signal_line.iloc[-1]: score += 1  # 10

    # ── RSI (4 signals) ──────────────────────────────────────────────────
    rsi7  = compute_rsi(c, 7)
    rsi14 = compute_rsi(c, 14)
    rsi21 = compute_rsi(c, 21)

    r14 = rsi14.iloc[-1]
    if 35 < r14 < 65:  score += 1   # 11  neutral-healthy zone
    if rsi7.iloc[-1] > rsi14.iloc[-1]: score += 1  # 12  short RSI > mid RSI (momentum)
    if rsi21.iloc[-1] > 45:  score += 1  # 13  long-term not oversold
    if rsi14.iloc[-2] < 40 and r14 > 40:  score += 1  # 14  RSI recovery cross

    # ── Bollinger Bands (3 signals) ───────────────────────────────────────
    bb_mid  = sma20
    bb_std  = c.rolling(20).std()
    bb_up   = bb_mid + 2 * bb_std
    bb_low  = bb_mid - 2 * bb_std

    if last > bb_low.iloc[-1]:  score += 1  # 15  above lower band
    if last < bb_up.iloc[-1]:   score += 1  # 16  below upper band (not overbought)
    # Price crossed above lower band recently
    if c.iloc[-3] < bb_low.iloc[-3] and last > bb_low.iloc[-1]: score += 1  # 17

    # ── Volume (3 signals) ────────────────────────────────────────────────
    vol_avg20 = v.rolling(20).mean()
    vol_avg5  = v.rolling(5).mean()

    if v.iloc[-1] > vol_avg20.iloc[-1]:        score += 1  # 18  high volume today
    if vol_avg5.iloc[-1] > vol_avg20.iloc[-1]: score += 1  # 19  recent vol > avg
    # Volume expanding on up days
    up_days = (c.diff() > 0).astype(int)
    vol_up  = (v * up_days).rolling(5).mean()
    vol_dn  = (v * (1 - up_days)).rolling(5).mean()
    if vol_up.iloc[-1] > vol_dn.iloc[-1]:      score += 1  # 20  more vol on up days

    # ── Momentum / Rate of Change (4 signals) ─────────────────────────────
    roc5  = (c / c.shift(5)  - 1) * 100
    roc10 = (c / c.shift(10) - 1) * 100
    roc20 = (c / c.shift(20) - 1) * 100

    if roc5.iloc[-1]  > 0:   score += 1  # 21
    if roc10.iloc[-1] > -3:  score += 1  # 22  not deeply negative
    if roc20.iloc[-1] > -8:  score += 1  # 23
    if roc5.iloc[-1]  < 15:  score += 1  # 24  not overextended short-term

    # ── 52-week position (2 signals) ──────────────────────────────────────
    high52 = h.rolling(252).max().iloc[-1]
    low52  = l.rolling(252).min().iloc[-1]
    rng = high52 - low52

    if rng > 0:
        pos = (last - low52) / rng
        if 0.20 < pos < 0.80:  score += 1  # 25  mid-range (not at extremes)
        if pos > 0.30:          score += 1  # 26  above lower 30%

    # ── Stochastic (2 signals) ────────────────────────────────────────────
    low14  = l.rolling(14).min()
    high14 = h.rolling(14).max()
    denom  = (high14 - low14).replace(0, np.nan)
    stoch_k = ((c - low14) / denom * 100)
    stoch_d = stoch_k.rolling(3).mean()

    if stoch_k.iloc[-1] > 20:                             score += 1  # 27  not oversold
    if stoch_k.iloc[-1] > stoch_d.iloc[-1]:               score += 1  # 28  K > D momentum

    # ── ATR / volatility filter (2 signals) ──────────────────────────────
    tr = pd.concat([
        h - l,
        (h - c.shift()).abs(),
        (l - c.shift()).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    atr_pct = atr14.iloc[-1] / last if last > 0 else 1

    if atr_pct < 0.05:  score += 1  # 29  reasonable volatility
    if atr_pct > 0.005: score += 1  # 30  enough movement to trade

    direction = 'BUY' if score >= 22 else 'WATCH'
    return score, direction

def compute_quantum_signals():
    if not HAS_YF:
        return False

    print(f"  Fetching price data for {len(SP500_TICKERS)} tickers...")
    try:
        raw = yf.download(
            SP500_TICKERS,
            period='1y',
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        print(f"  yfinance download failed: {e}")
        return False

    results = []
    buy_count = 0

    for sym in SP500_TICKERS:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                df = raw.xs(sym, level=1, axis=1).dropna()
            else:
                df = raw.dropna()

            if len(df) < 60:
                continue

            score, direction = compute_signals_for_ticker(df)
            last_close = float(df['Close'].iloc[-1])
            last_r = float(((df['Close'].iloc[-1] / df['Close'].iloc[-22]) - 1) * 100)

            # Simple SL/TP based on ATR
            tr = pd.concat([
                df['High'] - df['Low'],
                (df['High'] - df['Close'].shift()).abs(),
                (df['Low']  - df['Close'].shift()).abs(),
            ], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])

            sl = round(last_close - 2.0 * atr, 2)
            tp = round(last_close + 1.5 * atr, 2)

            # Historical win rate proxy: pct of 20-day windows with positive return
            fwd = df['Close'].pct_change(20).shift(-20).dropna()
            wr = round(float((fwd > 0).mean() * 100), 1) if len(fwd) > 0 else 0.0

            results.append({
                's': sym,
                'p': round(last_close, 2),
                'r': round(last_r, 1),
                'sc': score,
                'd': direction,
                'e': round(last_close, 2),
                'sl': sl,
                'tp': tp,
                't': 'S',
                'wr': wr,
                'tr': 0.0,
                'nt': 0,
                'hd': 60,
            })

            if direction == 'BUY':
                buy_count += 1

        except Exception:
            continue

    # Sort: BUY first by score desc, then WATCH by score desc
    results.sort(key=lambda x: (0 if x['d'] == 'BUY' else 1, -x['sc']))

    # Compute aggregate metrics
    wr_list = [r['wr'] for r in results if r['d'] == 'BUY']
    avg_wr = round(float(np.mean(wr_list)), 1) if wr_list else 0.0

    payload = {
        'updated': NOW_ISO,
        'market_date': TODAY,
        'strategy': {
            'stop_pct': 0.14,
            'target_pct': 0.075,
            'hold_days': 60,
            'confluence': 22,
            'max_positions': 10,
            'n_signals': 30,
        },
        'metrics': {
            'total_return': 0.0,
            'annual_return': 0.0,
            'win_rate': avg_wr,
            'max_drawdown': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'n_trades': 0,
        },
        'buy_count': buy_count,
        'total_count': len(results),
        'signals': results,
    }

    out_path = os.path.join(ROOT, 'data', 'quantum_signals.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(payload, f, separators=(',', ':'))

    print(f"  Signals: {buy_count} BUY / {len(results)} total -> data/quantum_signals.json")
    return True


# ─── 6. Sitemap ───────────────────────────────────────────────────────────────
def update_sitemap():
    path = os.path.join(ROOT, 'sitemap.xml')
    content = read_file(path)
    content = re.sub(r'<lastmod>\d{4}-\d{2}-\d{2}</lastmod>', f'<lastmod>{TODAY}</lastmod>', content)
    write_file(path, content)
    print(f"  sitemap.xml -> lastmod {TODAY}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f"QuantMedia Daily Update — {NOW_ISO}")
    print(f"{'='*60}\n")

    print("[ 1/5 ] Fetching forex rates...")
    forex = fetch_forex()

    print("[ 2/5 ] Fetching crypto prices...")
    crypto = fetch_crypto()

    print("[ 3/5 ] Updating markets.html...")
    update_markets_html(forex, crypto)

    print("[ 4/5 ] Fetching news & updating news.html...")
    articles = fetch_news()
    update_news_html(articles)

    print("[ 5/5 ] Computing quantum signals...")
    compute_quantum_signals()

    update_sitemap()

    print(f"\nDone — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")

if __name__ == '__main__':
    main()
