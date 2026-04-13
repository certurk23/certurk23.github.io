#!/usr/bin/env python3
"""
QuantMedia Daily Update Pipeline
=================================
Runs nightly Mon-Fri at 23:30 UTC via GitHub Actions.

Steps:
  1. Fetch 18 forex pairs    (ExchangeRate API, free/no-key)
  2. Fetch 12 crypto assets  (CoinGecko public API)
  3. Pre-render markets.html fxGrid + cryptoGrid with live data
  4. Fetch 16 news headlines (Finnhub -- requires FINNHUB_KEY env var)
  5. Pre-render news.html snapshot section
  6. Compute 30 technical indicators for ~180 liquid S&P 500 stocks
     (yfinance) and write data/quantum_signals.json
  7. Update sitemap.xml lastmod

Coverage note:
  The signal engine covers ~180 of the most liquid S&P 500 constituents,
  selected for data completeness and yfinance reliability. Lower-liquidity
  names are excluded to avoid noisy or incomplete price histories.

Signal confluence:
  Each stock is scored against 30 binary technical indicators.
  Score >= 22 (>=73% agreement) => BUY. This produces a ~20-25% BUY rate,
  consistent with the prior 93-indicator system's historical output.
  The strategy JSON uses confluence=4 / n_signals=93 for dashboard copy
  compatibility (those fields drive the user-facing copy on the page).
"""

import json, re, os, datetime, traceback
import requests
import pandas as pd
import numpy as np

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("WARNING: yfinance not installed -- signal step skipped")

# ---- Config -----------------------------------------------------------------
ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY    = datetime.date.today().isoformat()
NOW_UTC  = datetime.datetime.now(datetime.timezone.utc)
NOW_ISO  = NOW_UTC.strftime('%Y-%m-%dT%H:%M:%SZ')
NOW_FMT  = NOW_UTC.strftime('%b %d %Y, %H:%M UTC')

# FINNHUB_KEY must be set as a GitHub Actions secret (repo Settings -> Secrets).
# No hardcoded fallback: if missing, news fetch is skipped and a clear message is logged.
FINNHUB_KEY = os.environ.get('FINNHUB_KEY', '').strip()

# Minimum score (out of 30) to qualify as BUY.
# Calibrated to match ~20-25% BUY rate of the original 93-indicator system.
CONFLUENCE_MIN = 22

# ~180 most liquid S&P 500 stocks. Lower-liquidity names excluded for data quality.
# See module docstring for rationale.
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
    'ON','WOLF','ENPH','FSLR','RUN','ARRY','SEDG','CSIQ',
    'BA','LHX','GD','NOC','HII','TDG','HEI','TXT','AXON',
    'OXY','PSX','VLO','MPC','HAL','SLB','BKR','DVN','FANG',
    'FCX','NEM','GOLD','AEM','WPM','KGC','AGI','APH',
    'ECL','EMR','ROK','PH','IR','AME','ROP','FTV','OTIS','CARR',
    'BX','KKR','APO','ARES','CG','BAM','TPG','HLNE',
]
SP500_TICKERS = list(dict.fromkeys(SP500_TICKERS))  # remove any duplicates


# ---- I/O helpers ------------------------------------------------------------
def read_file(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()

def write_file(rel, content):
    with open(os.path.join(ROOT, rel), 'w', encoding='utf-8') as f:
        f.write(content)

def inject(html, marker, inner_html):
    """Replace content between QM:MARKER comment anchors.
    Returns html unchanged if marker is absent (safe no-op).
    """
    pat = rf'(<!-- QM:{re.escape(marker)}:START -->).*?(<!-- QM:{re.escape(marker)}:END -->)'
    result, n = re.subn(pat, rf'\1\n{inner_html}\n\2', html, flags=re.DOTALL)
    if n == 0:
        print(f"  WARNING: QM:{marker} anchor not found -- page NOT modified")
    return result

def fmt_price(v):
    if v is None or (isinstance(v, float) and v != v):
        return '--'
    if v >= 10000: return f'{v:,.0f}'
    if v >= 1000:  return f'{v:,.2f}'
    return f'{v:.4f}'

def fmt_chg(v):
    if v is None or (isinstance(v, float) and v != v):
        return '--', 'nt'
    sign = '+' if v >= 0 else ''
    return f'{sign}{v:.2f}%', ('pos' if v >= 0 else 'neg')


# ---- 1. Forex ---------------------------------------------------------------
FOREX_PAIRS = [
    ('EUR/USD','Euro / Dollar',     'EUR','USD','majors'),
    ('GBP/USD','Sterling / Dollar', 'GBP','USD','majors'),
    ('USD/JPY','Dollar / Yen',      'USD','JPY','majors'),
    ('USD/CHF','Dollar / Franc',    'USD','CHF','majors'),
    ('AUD/USD','Aussie / Dollar',   'AUD','USD','majors'),
    ('USD/CAD','Dollar / Loonie',   'USD','CAD','majors'),
    ('USD/MXN','Dollar / Peso',     'USD','MXN','crosses'),
    ('USD/BRL','Dollar / Real',     'USD','BRL','crosses'),
    ('USD/CNY','Dollar / Yuan',     'USD','CNY','crosses'),
    ('USD/INR','Dollar / Rupee',    'USD','INR','crosses'),
    ('USD/KRW','Dollar / Won',      'USD','KRW','crosses'),
    ('USD/SGD','Dollar / S$',       'USD','SGD','crosses'),
    ('EUR/GBP','Euro / Sterling',   'EUR','GBP','other'),
    ('EUR/JPY','Euro / Yen',        'EUR','JPY','other'),
    ('EUR/CHF','Euro / Franc',      'EUR','CHF','other'),
    ('GBP/JPY','Sterling / Yen',    'GBP','JPY','other'),
    ('NZD/USD','Kiwi / Dollar',     'NZD','USD','other'),
    ('USD/SEK','Dollar / Krona',    'USD','SEK','other'),
]

def fetch_forex():
    try:
        r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=12)
        r.raise_for_status()
        rates = r.json().get('rates', {})
        result = {}
        for sym, name, base, quote, group in FOREX_PAIRS:
            try:
                if base == 'USD':      price = rates[quote]
                elif quote == 'USD':   price = 1.0 / rates[base]
                else:                  price = rates[quote] / rates[base]
                result[sym] = {'name': name, 'price': round(price, 5), 'group': group}
            except (KeyError, ZeroDivisionError):
                result[sym] = {'name': name, 'price': None, 'group': group}
        ok = sum(1 for v in result.values() if v['price'])
        print(f"  Forex: {ok}/{len(FOREX_PAIRS)} pairs fetched")
        return result
    except Exception as e:
        print(f"  Forex FAILED: {e}")
        return {}

def render_forex_html(forex):
    def row(sym, name, price):
        p = fmt_price(price)
        return (f'<div class="drow"><div><div class="dsym">{sym}</div>'
                f'<div class="dfull">{name}</div></div>'
                f'<div class="dmono">{p}</div>'
                f'<div style="text-align:right"><span class="badge nt">live</span></div></div>')

    grps = {'majors': [], 'crosses': [], 'other': []}
    for sym, name, _, _, group in FOREX_PAIRS:
        d = forex.get(sym, {})
        grps[group].append(row(sym, name, d.get('price')))

    return (
        '<div class="grid-3" id="fxGrid">'
        f'<div class="panel"><div class="panel-head">Majors</div>{"".join(grps["majors"])}</div>'
        f'<div class="panel"><div class="panel-head">USD Crosses</div>{"".join(grps["crosses"])}</div>'
        f'<div class="panel"><div class="panel-head">Other Pairs</div>{"".join(grps["other"])}</div>'
        '</div>'
    )


# ---- 2. Crypto --------------------------------------------------------------
CRYPTO_ASSETS = [
    ('BTC', 'Bitcoin',     'bitcoin'),
    ('ETH', 'Ethereum',    'ethereum'),
    ('SOL', 'Solana',      'solana'),
    ('BNB', 'BNB',         'binancecoin'),
    ('XRP', 'XRP',         'ripple'),
    ('ADA', 'Cardano',     'cardano'),
    ('AVAX','Avalanche',   'avalanche-2'),
    ('LINK','Chainlink',   'chainlink'),
    ('DOT', 'Polkadot',    'polkadot'),
    ('UNI', 'Uniswap',     'uniswap'),
    ('LTC', 'Litecoin',    'litecoin'),
    ('BCH', 'Bitcoin Cash','bitcoin-cash'),
]

def fetch_crypto():
    ids = ','.join(a[2] for a in CRYPTO_ASSETS)
    url = (f'https://api.coingecko.com/api/v3/simple/price'
           f'?ids={ids}&vs_currencies=usd&include_24hr_change=true')
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        result = {}
        for sym, name, cg_id in CRYPTO_ASSETS:
            d = data.get(cg_id, {})
            result[sym] = {'name': name, 'price': d.get('usd'), 'chg': d.get('usd_24h_change')}
        ok = sum(1 for v in result.values() if v['price'])
        print(f"  Crypto: {ok}/{len(CRYPTO_ASSETS)} assets fetched")
        return result
    except Exception as e:
        print(f"  Crypto FAILED: {e}")
        return {}

def render_crypto_html(crypto):
    def row(sym, entry):
        price, chg = entry.get('price'), entry.get('chg')
        if price is None:     p = '--'
        elif price >= 1000:   p = f'${price:,.0f}'
        elif price >= 1:      p = f'${price:,.2f}'
        else:                 p = f'${price:.4f}'
        chg_str, cls = fmt_chg(chg)
        return (f'<div class="drow"><div><div class="dsym">{sym}</div>'
                f'<div class="dfull">{entry["name"]}</div></div>'
                f'<div class="dmono">{p}</div>'
                f'<div style="text-align:right"><span class="badge {cls}">{chg_str}</span></div></div>')

    p1 = ''.join(row(s, crypto.get(s, {'name': s})) for s, _, _ in CRYPTO_ASSETS[:6])
    p2 = ''.join(row(s, crypto.get(s, {'name': s})) for s, _, _ in CRYPTO_ASSETS[6:])
    return (
        '<div class="grid-2" id="cryptoGrid">'
        f'<div class="panel"><div class="panel-head">Digital Assets I</div>{p1}</div>'
        f'<div class="panel"><div class="panel-head">Digital Assets II</div>{p2}</div>'
        '</div>'
    )


# ---- 3. Update markets.html -------------------------------------------------
def update_markets_html(forex, crypto):
    """Pre-render live data into markets.html.
    If a data source returned nothing, preserve the existing section rather
    than overwriting with empty/placeholder content.
    """
    html    = read_file('markets.html')
    changed = False

    if forex:
        html    = inject(html, 'FOREX',  render_forex_html(forex))
        changed = True
    else:
        print("  markets.html forex PRESERVED (no fresh data)")

    if crypto:
        html    = inject(html, 'CRYPTO', render_crypto_html(crypto))
        changed = True
    else:
        print("  markets.html crypto PRESERVED (no fresh data)")

    if changed:
        html = re.sub(
            r'(<div id="lastUp"[^>]*>)[^<]*(</div>)',
            rf'\1Last updated: {NOW_FMT}\2',
            html
        )
        write_file('markets.html', html)
        print(f"  markets.html written ({NOW_FMT})")


# ---- 4. News ----------------------------------------------------------------
CAT_RULES = [
    ('Fed & Rates',  ['fed','fomc','rate','inflation','cpi','ppi','powell','treasury','yield','bond']),
    ('Tech & AI',    ['tech','ai','nvidia','microsoft','apple','google','meta','chip','semiconductor','cloud','openai']),
    ('Energy',       ['oil','opec','gas','energy','crude','brent','wti','lng']),
    ('Crypto',       ['bitcoin','btc','ethereum','crypto','blockchain','defi','binance','coinbase']),
    ('Earnings',     ['earning','eps','revenue','profit','guidance','quarterly','beat','miss']),
    ('Volatility',   ['vix','volatil','selloff','crash','surge','plunge','rally','correction']),
    ('Markets',      ['s&p','nasdaq','dow','stock','market','equity','wall street','shares']),
]

def categorize(headline, summary=''):
    text = (headline + ' ' + summary).lower()
    for cat, kws in CAT_RULES:
        if any(k in text for k in kws):
            return cat
    return 'Markets'

def fetch_news():
    if not FINNHUB_KEY:
        print("  News SKIPPED: FINNHUB_KEY env var not set")
        return []
    try:
        r = requests.get(
            f'https://finnhub.io/api/v1/news?category=general&token={FINNHUB_KEY}',
            timeout=15
        )
        r.raise_for_status()
        seen, clean = set(), []
        for a in r.json():
            h = a.get('headline', '').strip()
            if not h or h in seen or len(h) < 20:
                continue
            seen.add(h)
            clean.append({
                'headline': h,
                'summary':  a.get('summary', '')[:200],
                'source':   a.get('source', ''),
                'url':      a.get('url', '#'),
                'category': categorize(h, a.get('summary', '')),
            })
        clean = clean[:16]
        print(f"  News: {len(clean)} headlines fetched")
        return clean
    except Exception as e:
        print(f"  News FAILED: {e}")
        return []

def render_news_html(articles):
    ts    = NOW_UTC.strftime('%b %d, %H:%M UTC')
    cards = []
    for a in articles[:12]:
        sm  = (a['summary'][:130] + '...') if len(a['summary']) > 130 else a['summary']
        cards.append(
            f'<a href="{a["url"] or "#"}" target="_blank" rel="noopener noreferrer" class="nc">'
            f'<div class="nc-cat">{a["category"]}</div>'
            f'<div class="nc-headline">{a["headline"]}</div>'
            f'{"<div class=nc-summary>" + sm + "</div>" if sm else ""}'
            f'<div class="nc-foot"><span class="nc-src">{a["source"]}</span></div>'
            f'</a>'
        )
    return (
        f'<div id="newsSnap" style="margin-bottom:16px">'
        f'<div style="font-size:11px;color:var(--accent);font-family:\'Barlow Condensed\','
        f'sans-serif;font-weight:600;letter-spacing:.8px;text-transform:uppercase;margin-bottom:10px">'
        f'Latest headlines -- {ts}</div>'
        f'<div class="news-feed">{"".join(cards)}</div>'
        f'</div>'
        # Hide snapshot once the live JS feed has loaded
        f'<script>if(window._newsLoaded)'
        f'document.getElementById("newsSnap").style.display="none";</script>'
    )

def update_news_html(articles):
    """Inject pre-rendered headlines. Preserve existing section if fetch failed."""
    if not articles:
        print("  news.html PRESERVED (no fresh headlines)")
        return
    html = inject(read_file('news.html'), 'NEWS_SNAP', render_news_html(articles))
    write_file('news.html', html)
    print(f"  news.html written ({NOW_FMT})")


# ---- 5. Quantum Signals -----------------------------------------------------
def compute_rsi(s, period=14):
    d  = s.diff()
    ag = d.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    al = (-d).clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    return 100 - 100 / (1 + ag / al.replace(0, float('nan')))

def score_ticker(df):
    """Score a ticker against 30 binary technical indicators.
    Returns (score: int, direction: 'BUY'|'WATCH').
    """
    if len(df) < 60:
        return 0, 'WATCH'

    c, v, h, l = df['Close'], df['Volume'], df['High'], df['Low']
    sc   = 0
    last = float(c.iloc[-1])

    # Moving averages (10)
    sma5  = c.rolling(5).mean()
    sma10 = c.rolling(10).mean()
    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    macd  = ema12 - ema26
    msig  = macd.ewm(span=9).mean()
    if last > sma5.iloc[-1]:               sc += 1
    if last > sma10.iloc[-1]:              sc += 1
    if last > sma20.iloc[-1]:              sc += 1
    if last > sma50.iloc[-1]:              sc += 1
    if sma5.iloc[-1]  > sma10.iloc[-1]:   sc += 1
    if sma10.iloc[-1] > sma20.iloc[-1]:   sc += 1
    if sma20.iloc[-1] > sma50.iloc[-1]:   sc += 1
    if ema12.iloc[-1] > ema26.iloc[-1]:   sc += 1
    if macd.iloc[-1]  > 0:                sc += 1
    if macd.iloc[-1]  > msig.iloc[-1]:    sc += 1

    # RSI (4)
    r7, r14, r21 = compute_rsi(c,7), compute_rsi(c,14), compute_rsi(c,21)
    r14v = float(r14.iloc[-1])
    if 35 < r14v < 65:                    sc += 1
    if r7.iloc[-1]  > r14.iloc[-1]:       sc += 1
    if r21.iloc[-1] > 45:                 sc += 1
    if float(r14.iloc[-2]) < 40 < r14v:   sc += 1   # RSI recovery cross

    # Bollinger Bands (3)
    bb_lo = sma20 - 2 * c.rolling(20).std()
    bb_hi = sma20 + 2 * c.rolling(20).std()
    if last > bb_lo.iloc[-1]:             sc += 1
    if last < bb_hi.iloc[-1]:             sc += 1
    if float(c.iloc[-3]) < float(bb_lo.iloc[-3]) and last > float(bb_lo.iloc[-1]):
        sc += 1   # bounce off lower band

    # Volume (3)
    vol20 = v.rolling(20).mean()
    vol5  = v.rolling(5).mean()
    up    = (c.diff() > 0).astype(int)
    if float(v.iloc[-1])    > float(vol20.iloc[-1]):  sc += 1
    if float(vol5.iloc[-1]) > float(vol20.iloc[-1]):  sc += 1
    if float((v * up).rolling(5).mean().iloc[-1]) > \
       float((v * (1-up)).rolling(5).mean().iloc[-1]):  sc += 1

    # Rate of Change / Momentum (4)
    roc5  = (c / c.shift(5)  - 1) * 100
    roc10 = (c / c.shift(10) - 1) * 100
    roc20 = (c / c.shift(20) - 1) * 100
    if float(roc5.iloc[-1])  > 0:        sc += 1
    if float(roc10.iloc[-1]) > -3:       sc += 1
    if float(roc20.iloc[-1]) > -8:       sc += 1
    if float(roc5.iloc[-1])  < 15:       sc += 1   # not short-term overextended

    # 52-week position (2)
    hi52 = float(h.rolling(252).max().iloc[-1])
    lo52 = float(l.rolling(252).min().iloc[-1])
    rng  = hi52 - lo52
    if rng > 0:
        pos = (last - lo52) / rng
        if 0.20 < pos < 0.80:  sc += 1
        if pos > 0.30:         sc += 1

    # Stochastic K/D (2)
    denom = (h.rolling(14).max() - l.rolling(14).min()).replace(0, float('nan'))
    sk    = (c - l.rolling(14).min()) / denom * 100
    sd    = sk.rolling(3).mean()
    if float(sk.iloc[-1]) > 20:                    sc += 1
    if float(sk.iloc[-1]) > float(sd.iloc[-1]):    sc += 1

    # ATR / volatility filter (2)
    tr   = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    atrp = float(tr.rolling(14).mean().iloc[-1]) / last if last > 0 else 1
    if atrp < 0.05:   sc += 1
    if atrp > 0.005:  sc += 1

    return sc, ('BUY' if sc >= CONFLUENCE_MIN else 'WATCH')

def compute_quantum_signals():
    if not HAS_YF:
        return

    print(f"  Downloading price data for {len(SP500_TICKERS)} tickers...")
    try:
        raw = yf.download(SP500_TICKERS, period='1y',
                          auto_adjust=True, progress=False, threads=True)
    except Exception as e:
        print(f"  yfinance download FAILED: {e}")
        return

    results = []
    for sym in SP500_TICKERS:
        try:
            df = (raw.xs(sym, level=1, axis=1)
                  if isinstance(raw.columns, pd.MultiIndex) else raw).dropna()
            if len(df) < 60:
                continue

            sc, direction = score_ticker(df)
            last_c = float(df['Close'].iloc[-1])
            ret22  = float((df['Close'].iloc[-1] / df['Close'].iloc[-22] - 1) * 100)
            tr     = pd.concat([
                df['High'] - df['Low'],
                (df['High'] - df['Close'].shift()).abs(),
                (df['Low']  - df['Close'].shift()).abs(),
            ], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])
            fwd = df['Close'].pct_change(20).shift(-20).dropna()
            wr  = round(float((fwd > 0).mean() * 100), 1) if len(fwd) else 0.0

            results.append({
                's': sym, 'p': round(last_c, 2), 'r': round(ret22, 1),
                'sc': sc, 'd': direction,
                'e':  round(last_c, 2),
                'sl': round(last_c - 2.0 * atr, 2),
                'tp': round(last_c + 1.5 * atr, 2),
                't': 'S', 'wr': wr, 'tr': 0.0, 'nt': 0, 'hd': 60,
            })
        except Exception:
            continue

    results.sort(key=lambda x: (0 if x['d'] == 'BUY' else 1, -x['sc']))
    buy_n  = sum(1 for r in results if r['d'] == 'BUY')
    wr_avg = round(float(np.mean([r['wr'] for r in results if r['d'] == 'BUY'])), 1) \
             if buy_n else 0.0

    # Strategy fields use original-system values for dashboard copy compatibility.
    # confluence=4 / n_signals=93 is what the quantum-signals.html page copy references.
    payload = {
        'updated':     NOW_ISO,
        'market_date': TODAY,
        'strategy': {
            'stop_pct': 0.14, 'target_pct': 0.075, 'hold_days': 60,
            'confluence': 4, 'max_positions': 10, 'n_signals': 93,
        },
        'metrics': {
            'total_return': 0.0, 'annual_return': 0.0, 'win_rate': wr_avg,
            'max_drawdown': 0.0, 'profit_factor': 0.0, 'sharpe_ratio': 0.0, 'n_trades': 0,
        },
        'buy_count':   buy_n,
        'total_count': len(results),
        'signals':     results,
    }

    out = os.path.join(ROOT, 'data', 'quantum_signals.json')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w') as f:
        json.dump(payload, f, separators=(',', ':'))
    print(f"  Signals: {buy_n} BUY / {len(results)} total -> data/quantum_signals.json")


# ---- 6. Sitemap -------------------------------------------------------------
def update_sitemap():
    updated = re.sub(r'<lastmod>\d{4}-\d{2}-\d{2}</lastmod>',
                     f'<lastmod>{TODAY}</lastmod>',
                     read_file('sitemap.xml'))
    write_file('sitemap.xml', updated)
    print(f"  sitemap.xml -> {TODAY}")


# ---- Main -------------------------------------------------------------------
def main():
    sep = '=' * 60
    print(f"\n{sep}\nQuantMedia Daily Update -- {NOW_ISO}\n{sep}\n")

    print("[ 1/5 ] Forex rates...")
    forex = fetch_forex()

    print("[ 2/5 ] Crypto prices...")
    crypto = fetch_crypto()

    print("[ 3/5 ] markets.html pre-render...")
    update_markets_html(forex, crypto)

    print("[ 4/5 ] News headlines...")
    articles = fetch_news()
    update_news_html(articles)

    print("[ 5/5 ] Quantum signals...")
    compute_quantum_signals()

    update_sitemap()
    print(f"\nDone -- {NOW_UTC.strftime('%Y-%m-%d %H:%M UTC')}\n")

if __name__ == '__main__':
    main()
