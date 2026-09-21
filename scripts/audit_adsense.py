#!/usr/bin/env python3
"""Pre-AdSense audit of the LIVE site. Read-only. Fetches every sitemap URL
plus robots/ads.txt/manifest/data, and reports per page: crawler-visible
word count (no JS), title/H1/description, canonical, JSON-LD validity and
author/publisher, heading order, placeholder text, strong claims, AdSense
wording, third-party brand mentions, references/limitations sections,
dates. Also: www/http/index.html handling, retired URLs, data consistency.

Run: python scripts/audit_adsense.py [--save DIR]
"""
import concurrent.futures as cf
import gzip
import json
import os
import re
import sys
import urllib.request
import urllib.error

SITE = 'https://quantmedia.io'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; qm-audit/1.0)', 'Accept-Encoding': 'gzip'}
SAVE = None
if '--save' in sys.argv:
    SAVE = sys.argv[sys.argv.index('--save') + 1]
    os.makedirs(SAVE, exist_ok=True)

CLAIMS = ['institutional-grade', 'institutional grade', 'NY4', 'NY5', 'co-location', 'colocation', 'ITCH',
          'nanosecond', 'real-time', 'realtime', 'real time', 'registered', 'professional infrastructure',
          'peer reviewed', 'peer-reviewed', 'our team', 'research lab', 'outperform', 'guaranteed',
          'proprietary', 'live ', 'LIVE', 'alpha', 'award', 'trusted by', 'clients']
ADS = ['AdSense', 'adsense', 'Google Ads', 'ad revenue', 'advertising', 'sponsored', 'affiliate']
BRANDS = ['TradingView', 'Reuters', 'CNBC', 'Yahoo', 'Finnhub', 'CoinGecko', 'Bloomberg', 'OpenAI', 'ChatGPT',
          'Claude', 'Anthropic', 'FMP', 'Financial Modeling Prep', 'Alpha Vantage', 'Polygon', 'Stooq', 'Frankfurter']
PLACEHOLDER = re.compile(r'(?i)>[^<]{0,40}\b(loading|please wait|fetching|coming soon|no data available|placeholder|lorem|TODO|TBD)\b[^<]{0,40}<')


def get(u, method='GET'):
    req = urllib.request.Request(u, headers=UA, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=40)
        b = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            b = gzip.decompress(b)
        return r.status, r.geturl(), dict(r.headers), b.decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.geturl() if hasattr(e, 'geturl') else u, dict(e.headers or {}), ''
    except Exception as e:
        return str(e)[:40], u, {}, ''


def visible(html):
    s = re.sub(r'(?is)<(script|style|template|noscript).*?</\1>', ' ', html)
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'&[a-z#0-9]+;', ' ', s)


def audit_page(u):
    st, final, hdr, h = get(u)
    rel = u.replace(SITE, '') or '/'
    if SAVE:
        with open(os.path.join(SAVE, re.sub(r'[^a-zA-Z0-9]+', '_', rel).strip('_') or 'index') + '.html', 'w', encoding='utf-8') as fh:
            fh.write(h)
    r = {'url': rel, 'status': st}
    if st != 200:
        return r
    v = visible(h)
    r['words'] = len(v.split())
    t = re.search(r'<title>(.*?)</title>', h, re.S); r['title'] = re.sub(r'\s+', ' ', t.group(1)).strip() if t else ''
    d = re.search(r'<meta\s+name="description"\s+content="(.*?)"', h, re.S); r['desc'] = d.group(1) if d else ''
    c = re.search(r'<link\s+rel="canonical"\s+href="(.*?)"', h); r['canonical'] = c.group(1) if c else ''
    r['h1'] = [re.sub(r'<[^>]+>|\s+', ' ', x).strip() for x in re.findall(r'<h1[^>]*>(.*?)</h1>', h, re.S)]
    heads = [int(m.group(1)) for m in re.finditer(r'<h([1-6])[\s>]', h)]
    r['heading_jumps'] = sum(1 for a, b in zip(heads, heads[1:]) if b > a + 1)
    r['noindex'] = bool(re.search(r'name="robots"[^>]*noindex', h))
    r['viewport'] = 'name="viewport"' in h
    lds = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            lds.append(json.loads(m.group(1)))
        except ValueError:
            lds.append('INVALID')
    r['ld_invalid'] = sum(1 for x in lds if x == 'INVALID')
    types, author, publisher = [], set(), set()
    def walk(o):
        if isinstance(o, dict):
            if '@type' in o: types.append(o['@type'] if isinstance(o['@type'], str) else ','.join(o['@type']))
            a = o.get('author')
            if isinstance(a, dict): author.add(a.get('name', '?'))
            elif isinstance(a, list): [author.add(x.get('name', '?')) for x in a if isinstance(x, dict)]
            p = o.get('publisher')
            if isinstance(p, dict): publisher.add(p.get('name', '?'))
            for vv in o.values(): walk(vv)
        elif isinstance(o, list):
            for vv in o: walk(vv)
    walk(lds)
    r['ld_types'] = sorted(set(types)); r['ld_author'] = sorted(author); r['ld_publisher'] = sorted(publisher)
    r['placeholders'] = [m.group(0)[:60] for m in PLACEHOLDER.finditer(re.sub(r'(?is)<(script|style|template|noscript).*?</\1>', ' ', h))]
    r['claims'] = sorted({k for k in CLAIMS if re.search(r'(?<![A-Za-z])' + re.escape(k) + r'(?![A-Za-z])', v)})
    r['ads_words'] = sorted({k for k in ADS if k in v})
    r['brands'] = sorted({k for k in BRANDS if re.search(r'(?<![A-Za-z])' + re.escape(k) + r'(?![A-Za-z])', v)})
    low = v.lower()
    r['has_references'] = bool(re.search(r'references|bibliography', low))
    r['has_limits'] = bool(re.search(r'limitation|does not establish|what this does not|limits', low))
    r['has_author_visible'] = 'Cemil' in v
    r['dates'] = sorted(set(re.findall(r'\b(20\d\d-\d\d-\d\d)\b', v)))[:6]
    r['links'] = sorted(set(re.findall(r'href="(/[^"#?]*)"', h)))
    r['imgs'] = re.findall(r'<img[^>]+src="([^"]+)"', h)
    r['ext_scripts'] = sorted(set(re.findall(r'<script[^>]+src="(https?://[^"]+)"', h)))
    r['fetches'] = sorted(set(re.findall(r"""['"](/?data/[^'"]+\.json)['"]""", h)))
    return r


def main():
    st, _, _, sm = get(f'{SITE}/sitemap.xml')
    urls = re.findall(r'<loc>(.*?)</loc>', sm)
    print(f'sitemap: {len(urls)} URLs')
    with cf.ThreadPoolExecutor(6) as ex:
        pages = list(ex.map(audit_page, urls))
    # --- housekeeping endpoints
    print('\n== endpoints ==')
    for p in ('/robots.txt', '/ads.txt', '/manifest.json', '/site.webmanifest', '/favicon.ico', '/data/status.json',
              '/data/quantum_signals.json', '/data/signal_breadth.json', '/data/sector_confluence.json', '/data/news.json',
              '/data/markets_bar.json', '/llms.txt', '/404-does-not-exist'):
        s, f, h, b = get(SITE + p)
        print(f'  {s:>4} {p}  {len(b):>7}B')
    print('\n== host handling ==')
    for u in ('http://quantmedia.io/', 'https://www.quantmedia.io/', 'https://quantmedia.io/index.html', 'https://quantmedia.io/reports', 'https://quantmedia.io/reports/index.html'):
        s, f, h, b = get(u)
        print(f'  {s:>4} {u} -> {f}')
    print('\n== retired URLs ==')
    for p in ('news.html', 'markets.html', 'stocks.html', 'research.html', 'infrastructure.html', 'claude-ai-trading.html', 'sector-rotation-guide.html',
              'paper-alternative-data-quant-finance.html', 'paper-bist-sentiment-analysis.html', 'paper-genetic-algorithm-alpha.html',
              'paper-gpu-cpu-trading-infrastructure.html', 'paper-hf-analytical-operations.html', 'paper-sovereign-ai-local-llms.html'):
        s, *_ = get(f'{SITE}/{p}', 'HEAD')
        linked = [pg['url'] for pg in pages if pg.get('links') and any(l.rstrip('/').endswith(p) for l in pg['links'])]
        print(f'  {s:>4} {p}  linked_from={linked}')
    # --- per-page table
    print('\n== pages ==')
    print(f"{'url':48s} {'words':>5} h1 jmp ld  auth  pub  refs lim  auth_vis  flags")
    titles = {}
    for pg in pages:
        if pg['status'] != 200:
            print(f"  {pg['url']:46s} STATUS {pg['status']}"); continue
        titles.setdefault(pg['title'], []).append(pg['url'])
        flags = []
        if pg['words'] < 500: flags.append(f'THIN')
        if pg['noindex']: flags.append('NOINDEX')
        if pg['ld_invalid']: flags.append('LD-INVALID')
        if not pg['ld_author']: flags.append('no-ld-author')
        if pg['placeholders']: flags.append('PLACEHOLDER:' + '|'.join(pg['placeholders'])[:60])
        if pg['claims']: flags.append('claims:' + ','.join(pg['claims']))
        if pg['ads_words']: flags.append('ads:' + ','.join(pg['ads_words']))
        if pg['brands']: flags.append('brands:' + ','.join(pg['brands']))
        if pg['canonical'].rstrip('/') != (SITE + pg['url']).rstrip('/'): flags.append('CANON:' + pg['canonical'])
        if not pg['viewport']: flags.append('NO-VIEWPORT')
        print(f"  {pg['url']:46s} {pg['words']:5d} {len(pg['h1']):2d} {pg['heading_jumps']:3d} {len(pg['ld_types']):2d}  {('|'.join(pg['ld_author']) or '-')[:12]:12s} {('|'.join(pg['ld_publisher']) or '-')[:10]:10s} {'y' if pg['has_references'] else '-'}    {'y' if pg['has_limits'] else '-'}    {'y' if pg['has_author_visible'] else '-'}     {' '.join(flags)}")
    dup = {t: u for t, u in titles.items() if len(u) > 1}
    print('\n== duplicate titles ==', dup or 'none')
    # --- internal link targets
    targets = set()
    for pg in pages:
        for l in pg.get('links', []): targets.add(l)
        for i in pg.get('imgs', []):
            if i.startswith('/'): targets.add(i)
        for f in pg.get('fetches', []): targets.add('/' + f.lstrip('/'))
    targets = sorted(t for t in targets if not t.startswith('//'))
    with cf.ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(lambda t: get(SITE + t, 'HEAD')[0], targets))
    bad = [(t, c) for t, c in zip(targets, codes) if c != 200]
    print(f'\n== internal targets: {len(targets)}, broken: {len(bad)} ==')
    for t, c in bad: print('  ', c, t)
    ext = sorted({s for pg in pages for s in pg.get('ext_scripts', [])})
    print('\n== external scripts ==', ext)
    if SAVE:
        with open(os.path.join(SAVE, '_audit.json'), 'w', encoding='utf-8') as fh:
            json.dump(pages, fh, indent=1)


if __name__ == '__main__':
    main()
