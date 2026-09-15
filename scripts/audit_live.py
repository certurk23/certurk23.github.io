#!/usr/bin/env python3
"""Read-only live audit: every sitemap URL is fetched and checked for status,
title/description length, canonical, single H1, JSON-LD validity, word
count, and internal links resolving (against the live site). Prints one
line per problem and a summary. Kept in the repo so it survives temp-dir
cleanups; makes no changes.

Run: python scripts/audit_live.py
"""
import concurrent.futures as cf
import gzip
import json
import re
import urllib.request

SITE = 'https://quantmedia.io'
UA = {'User-Agent': 'Mozilla/5.0 qm-audit', 'Accept-Encoding': 'gzip'}


def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30)
    b = r.read()
    if r.headers.get('Content-Encoding') == 'gzip':
        b = gzip.decompress(b)
    return r.status, b.decode('utf-8', 'replace')


def head_ok(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, method='HEAD', headers=UA), timeout=20)
        return r.status
    except Exception as e:
        return getattr(e, 'code', str(e)[:30])


def audit(u):
    st, h = get(u)
    t = re.search(r'<title>(.*?)</title>', h, re.S)
    t = re.sub(r'\s+', ' ', t.group(1)).strip() if t else ''
    d = re.search(r'<meta\s+name="description"\s+content="(.*?)"', h, re.S)
    d = d.group(1).strip() if d else ''
    can = re.search(r'<link\s+rel="canonical"\s+href="(.*?)"', h)
    can = can.group(1) if can else ''
    h1 = len(re.findall(r'<h1[\s>]', h))
    ld_ok = True
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            json.loads(m.group(1))
        except ValueError:
            ld_ok = False
    words = len(re.sub(r'(?is)<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', h).split())
    noindex = 'noindex' in h[:5000]
    links = set(re.findall(r'href="(/[^"#?]+)"', h))
    issues = []
    if st != 200: issues.append(f'status {st}')
    if not 30 <= len(t) <= 65: issues.append(f'title {len(t)}ch')
    if not 70 <= len(d) <= 160: issues.append(f'desc {len(d)}ch')
    if can.rstrip('/') != u.rstrip('/'): issues.append(f'canonical {can}')
    if h1 != 1: issues.append(f'h1={h1}')
    if not ld_ok: issues.append('bad JSON-LD')
    if noindex: issues.append('NOINDEX')
    if words < 300: issues.append(f'thin {words}w')
    return u, words, issues, links


def main():
    _, sm = get(f'{SITE}/sitemap.xml')
    urls = re.findall(r'<loc>(.*?)</loc>', sm)
    print(f'{len(urls)} URLs in sitemap')
    all_links = set()
    clean = 0
    with cf.ThreadPoolExecutor(6) as ex:
        for u, words, issues, links in ex.map(audit, urls):
            all_links |= {l for l in links if not l.startswith('/data/')}
            if issues:
                print(f'  {words:5d}w {u.replace(SITE, "")}  {", ".join(issues)}')
            else:
                clean += 1
    print(f'clean: {clean}/{len(urls)}')
    targets = sorted(all_links)
    with cf.ThreadPoolExecutor(8) as ex:
        bad = [(l, s) for l, s in zip(targets, ex.map(lambda l: head_ok(SITE + l), targets)) if s != 200]
    print(f'internal link targets: {len(targets)}, broken: {len(bad)}')
    for l, s in bad:
        print('  ', s, l)


if __name__ == '__main__':
    main()
