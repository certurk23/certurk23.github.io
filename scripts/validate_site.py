#!/usr/bin/env python3
"""
Pre-commit production validator.
=================================
Runs in CI immediately before `git commit`. If it exits non-zero, nothing is
committed and nothing is deployed - the live site keeps whatever it had, which
is always better than shipping a broken or contradictory build.

Pure standard library: this must be able to run before pandas/numpy/yfinance
are installed, and must never itself be the reason a build fails.

Usage
-----
    python scripts/validate_site.py            # full check, exit 1 on ERROR
    python scripts/validate_site.py --warn-only
"""

import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qm_config as C   # noqa: E402

# Overridable so the test-suite can point the validator at a corrupted copy of
# the site and prove that it actually fails. A validator that has only ever
# been seen to pass is an untested validator.
ROOT = os.environ.get('QM_ROOT') or \
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ERRORS, WARNINGS = [], []


def _reset():
    del ERRORS[:]
    del WARNINGS[:]


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace') as f:
        return f.read()


# Directories that hold build inputs or vendored code, not published pages.
NON_PAGE_DIRS = {'.git', '.github', 'node_modules', 'scripts', 'data',
                 'docs', 'quantmedia-research', '__pycache__'}


def html_files():
    """Every published page, discovered rather than listed.

    This used to hard-code ('indices', 'learn', 'tools'). When /author/ was
    added it was silently excluded, so EVERY check in this file - forbidden
    strings, fabricated attribution, placeholder text, schema shape - skipped
    the author page entirely. The bug was invisible because the validator kept
    printing "ok". Walking the tree and excluding known non-page directories
    fails safe in the other direction: a new directory is checked by default.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in NON_PAGE_DIRS]
        rel_dir = os.path.relpath(dirpath, ROOT)
        for f in filenames:
            if not f.endswith('.html') or f.startswith('google'):
                continue
            rel = f if rel_dir == '.' else os.path.join(rel_dir, f).replace(os.sep, '/')
            out.append(rel)
    return sorted(out)


# ---------------------------------------------------------------------------
# 1. Required files exist and are not truncated
# ---------------------------------------------------------------------------
def check_required_files():
    for rel, min_size in C.REQUIRED_FILES.items():
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            err(f'{rel}: MISSING')
            continue
        size = os.path.getsize(path)
        if size < min_size:
            err(f'{rel}: only {size:,} bytes (expected >= {min_size:,}) '
                '- looks truncated')


# ---------------------------------------------------------------------------
# 2. No forbidden / legacy / dangerous strings anywhere in the HTML
# ---------------------------------------------------------------------------
def check_forbidden_strings():
    for name in html_files():
        text = read(name)
        for pattern, why in C.FORBIDDEN:
            m = pattern.search(text)
            if m:
                snippet = text[max(0, m.start() - 40):m.end() + 40]
                snippet = ' '.join(snippet.split())
                err(f'{name}: {why} -> "...{snippet}..."')


# ---------------------------------------------------------------------------
# 3. Signal methodology copy agrees with ENGINE
# ---------------------------------------------------------------------------
def check_signal_config():
    """The published config must match ENGINE exactly - it is what external
    readers and the site copy are validated against."""
    rel = 'data/signal_config.json'
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        err(f'{rel}: MISSING (single source of truth for methodology)')
        return
    try:
        d = json.loads(read(rel))
    except Exception as e:
        err(f'{rel}: does not parse ({e})')
        return
    expect = C.signal_config()
    for k, v in expect.items():
        if k.startswith('_'):
            continue
        if d.get(k) != v:
            err(f'{rel}: {k}={d.get(k)!r} but ENGINE says {v!r} '
                '- regenerate via the pipeline')


# Hardcoded month/year in visible copy is how the homepage ended up telling
# visitors it was April months later. Publication dates are legitimate; a
# dated label on a "current" widget is not.
STALE_DATE_COPY = re.compile(
    r'>\s*(?:This Week|Today|Latest)\s*<[^>]*>[^<]*'
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}', re.I)
DATED_EVENT_ROW = re.compile(
    r'class="cal-time">\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
    r'[a-z]*\s+\d{1,2}', re.I)
FAKE_RELATIVE_TIME = re.compile(r'class="nc-time">\s*\d+\s*h ago\s*<', re.I)


def check_stale_homepage_copy():
    """Catches the specific regressions the homepage actually shipped."""
    for name in ('index.html',):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        text = read(name)
        if DATED_EVENT_ROW.search(text):
            err(f'{name}: macro calendar contains hardcoded dated events '
                '- they expire and then read as current')
        if FAKE_RELATIVE_TIME.search(text):
            err(f'{name}: hardcoded relative timestamps ("Nh ago") in static '
                'markup - these never update and always claim to be recent')
        if STALE_DATE_COPY.search(text):
            err(f'{name}: a "current" label sits next to a hardcoded date')


# Static markup must never impersonate a publisher. The homepage previously
# shipped seven invented stories bylined to real newsrooms.
PUBLISHERS = ('CNBC', 'Financial Times', 'Wall Street Journal', 'Bloomberg',
              'Reuters', 'Institutional Investor')


QM_REGION = re.compile(r'<!-- QM:[A-Z_]+:START -->.*?<!-- QM:[A-Z_]+:END -->',
                       re.DOTALL)
LINKED_ITEM = re.compile(r'<a\b[^>]*href="https?://[^"]+"[^>]*>.*?</a>', re.DOTALL)


def check_no_fabricated_attribution():
    """Flag publisher bylines that are NOT backed by a link to the article.

    The distinction matters and the first version of this check got it wrong:
    it flagged the pipeline's own news snapshot, which carries genuine Reuters
    and CNBC bylines pulled from the feed, and blocked a deploy that contained
    perfectly good data. Legitimate attribution always sits inside an anchor
    pointing at the original article; the fabricated cards had no link at all.

    So: strip pipeline-injected regions and every external link, then anything
    still claiming a publisher is invented.
    """
    for name in html_files():
        text = QM_REGION.sub('', read(name))     # pipeline-generated: exempt
        text = LINKED_ITEM.sub('', text)         # linked to source: legitimate
        for pub in PUBLISHERS:
            if re.search(rf'class="nc-src">\s*{re.escape(pub)}\s*<', text):
                err(f'{name}: bylines content to {pub} with no link to the '
                    'original article - fabricated attribution, remove it')


def check_methodology_consistency():
    uni = str(C.ENGINE['universe_count'])
    nsig = str(C.ENGINE['n_signals'])
    thr = str(C.ENGINE['confluence_min'])
    for name in C.METHODOLOGY_PAGES:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            err(f'{name}: MISSING (methodology page)')
            continue
        text = read(name)
        for value, label in ((uni, 'universe count'),
                             (nsig, 'signal count'),
                             (thr, 'confluence threshold')):
            if not re.search(rf'\b{value}\b', text):
                err(f'{name}: does not state the {label} ({value}) '
                    'from ENGINE - copy and code disagree')


# ---------------------------------------------------------------------------
# 4. HTML structural sanity (the bugs that actually shipped)
# ---------------------------------------------------------------------------
def check_html_structure():
    for name in html_files():
        text = read(name)

        # A missing opening <script> tag once caused ~100 lines of raw JS to
        # render as visible text on markets.html and killed every script.
        opens = len(re.findall(r'<script[\s>]', text))
        closes = len(re.findall(r'</script>', text))
        if opens != closes:
            err(f'{name}: unbalanced script tags ({opens} open / {closes} close)')

        d_open = len(re.findall(r'<div[\s>]', text))
        d_close = len(re.findall(r'</div>', text))
        if d_open != d_close:
            err(f'{name}: unbalanced div tags ({d_open} open / {d_close} close)')

        # <main> is the accessibility landmark; three pages shipped it unclosed.
        m_open = len(re.findall(r'<main[\s>]', text))
        m_close = len(re.findall(r'</main>', text))
        if m_open != m_close:
            err(f'{name}: unbalanced main tags ({m_open} open / {m_close} close)')

        # Every JSON-LD block must parse or rich results silently break.
        for i, m in enumerate(re.finditer(
                r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                text, re.DOTALL)):
            try:
                json.loads(m.group(1))
            except Exception as e:
                err(f'{name}: JSON-LD block #{i} does not parse ({e})')

        if '<title>' not in text:
            err(f'{name}: no <title>')
        if name != '404.html' and 'rel="canonical"' not in text:
            warn(f'{name}: no canonical link')


# ---------------------------------------------------------------------------
# 5. Catastrophic blank-table / placeholder regression
# ---------------------------------------------------------------------------
DASH_ROW = re.compile(r'<div class="dmono"[^>]*>\s*(?:&mdash;|—|--)\s*</div>')


def check_blank_data_regression():
    for name in ('markets.html', 'news.html'):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        text = read(name)
        dashes = len(DASH_ROW.findall(text))
        if dashes >= 5:
            err(f'{name}: {dashes} placeholder "—" data rows - '
                'this is the blank-grid regression, do not ship it')

        # Injection anchors must survive, or the pipeline silently no-ops.
        for marker in (('FOREX', 'CRYPTO') if name == 'markets.html'
                       else ('NEWS_SNAP',)):
            if text.count(f'<!-- QM:{marker}:START -->') != 1 or \
               text.count(f'<!-- QM:{marker}:END -->') != 1:
                err(f'{name}: QM:{marker} injection anchors missing/duplicated')

    # The index pages are the most original content on the site, and until this
    # existed nothing checked them. Re-running build_pages.py overwrote a real
    # reading with the empty template and the validator still said PASSED,
    # because this function only ever looked at markets.html and news.html.
    for rel, marker in (('indices/signal-breadth.html', 'BREADTH'),
                        ('indices/sector-confluence.html', 'SECTORS')):
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        text = read(rel)
        m = re.search(r'<!-- QM:' + marker + r':START -->(.*?)<!-- QM:'
                      + marker + r':END -->', text, re.DOTALL)
        if not m:
            err(rel + ': QM:' + marker + ' injection anchor missing - the '
                'pipeline cannot publish a reading into this page')
            continue
        # A real reading is a rendered table; the placeholder is one sentence.
        if '<table' not in m.group(1):
            err(rel + ': QM:' + marker + ' contains no rendered reading ('
                + str(len(m.group(1).strip())) + ' bytes) - a rebuild has '
                'blanked a page that had live data. Do not ship it.')


# ---------------------------------------------------------------------------
# 6. Data payloads
# ---------------------------------------------------------------------------
def _iso(ts):
    try:
        datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ')
        return True
    except Exception:
        return False


def check_signals():
    rel = 'data/quantum_signals.json'
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        err(f'{rel}: MISSING')
        return
    try:
        d = json.loads(read(rel))
    except Exception as e:
        err(f'{rel}: does not parse ({e})')
        return

    if not _iso(d.get('updated', '')):
        err(f'{rel}: "updated" is not ISO-8601 Z ({d.get("updated")!r})')

    md = d.get('market_date', '')
    try:
        md_date = datetime.date.fromisoformat(md)
    except Exception:
        err(f'{rel}: market_date invalid ({md!r})')
        return

    if not C.is_trading_day(md_date):
        err(f'{rel}: market_date {md} is not a US trading day '
            f'({md_date.strftime("%A")}) - trading-calendar logic regressed')

    if md_date > datetime.date.today():
        err(f'{rel}: market_date {md} is in the future')

    # Staleness is deliberately a WARNING here, never an error.
    #
    # This validator's job is to block CORRUPTION - output that would make the
    # live site wrong. Stale-but-valid data is not corruption: the site is
    # built to disclose it, and data/status.json is the very file that drives
    # the "updates are paused" banner. Blocking the commit on staleness would
    # withhold that disclosure from production AND strand any sibling source
    # that did refresh, making the site strictly worse than not running at
    # all. That is exactly the fail-safe rule this pipeline exists to honour.
    #
    # The loud signal lives in the workflow's final step, which fails the run
    # AFTER the push, so CI goes red without holding the truth hostage.
    behind = C.sessions_behind(md_date)
    if behind >= 3:
        warn(f'{rel}: market_date {md} is {behind} sessions behind the '
             f'latest completed session ({C.last_completed_session()}) '
             '- signal stage is stalled (reported post-deploy, not blocking)')

    rows = d.get('signals') or []
    if not rows:
        err(f'{rel}: zero signal rows')
        return
    if len(rows) < C.ENGINE['universe_count'] * 0.5:
        err(f'{rel}: only {len(rows)} rows scored of '
            f'{C.ENGINE["universe_count"]} universe')

    eng = d.get('engine') or {}
    for key in ('n_signals', 'confluence_min'):
        if eng.get(key) != C.ENGINE[key]:
            err(f'{rel}: engine.{key}={eng.get(key)} but ENGINE says '
                f'{C.ENGINE[key]} - payload and config disagree')

    lo, hi = C.BOUNDS['equity_price']
    rlo, rhi = C.BOUNDS['rsi']
    for row in rows:
        for field in ('s', 'p', 'sc', 'd'):
            if field not in row:
                err(f'{rel}: row {row.get("s", "?")} missing "{field}"')
                return
        if not (lo <= row['p'] <= hi):
            err(f'{rel}: {row["s"]} price {row["p"]} outside sane bounds')
            return
        if not (0 <= row['sc'] <= C.ENGINE['n_signals']):
            err(f'{rel}: {row["s"]} score {row["sc"]} outside 0..'
                f'{C.ENGINE["n_signals"]}')
            return
        if row['d'] not in ('BUY', 'WATCH'):
            err(f'{rel}: {row["s"]} decision {row["d"]!r} invalid')
            return
        if row.get('r') is not None and not (rlo <= row['r'] <= rhi):
            err(f'{rel}: {row["s"]} RSI {row["r"]} outside 0..100')
            return

    # The BUY set must be exactly what the threshold implies.
    thr = C.ENGINE['confluence_min']
    mismatched = [r['s'] for r in rows
                  if (r['sc'] >= thr) != (r['d'] == 'BUY')]
    if mismatched:
        err(f'{rel}: decision/threshold mismatch for {mismatched[:5]} '
            f'(threshold {thr})')
    declared = d.get('buy_count')
    actual = sum(1 for r in rows if r['d'] == 'BUY')
    if declared is not None and declared != actual:
        err(f'{rel}: buy_count={declared} but {actual} rows are BUY')


def check_feed(rel, expect_key):
    """Validate an optional last-known-good feed envelope."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return                                  # not yet published: fine
    try:
        d = json.loads(read(rel))
    except Exception as e:
        err(f'{rel}: does not parse ({e})')
        return
    if not _iso(d.get('fetched_utc', '')):
        err(f'{rel}: fetched_utc not ISO-8601 Z ({d.get("fetched_utc")!r})')
    data = d.get('data')
    if data is None or (hasattr(data, '__len__') and len(data) == 0):
        err(f'{rel}: published with an empty payload - '
            'last-known-good protection failed')
        return
    exp = C.EXPECTED.get(expect_key)
    if exp and hasattr(data, '__len__'):
        floor = exp.get('min_items') or int(exp['total'] * exp['min_ratio'])
        if len(data) < floor:
            err(f'{rel}: only {len(data)} items (floor {floor})')


def check_status():
    rel = 'data/status.json'
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        warn(f'{rel}: missing (generated on first pipeline run)')
        return
    try:
        d = json.loads(read(rel))
    except Exception as e:
        err(f'{rel}: does not parse ({e})')
        return
    if not _iso(d.get('last_pipeline_run', '')):
        err(f'{rel}: last_pipeline_run not ISO-8601 Z')
    for k in ('markets_status', 'news_status', 'signals_status'):
        if d.get(k) not in ('fresh', 'recent', 'delayed', 'paused',
                            'unknown', 'unavailable'):
            err(f'{rel}: {k}={d.get(k)!r} is not a known freshness state')


def check_sitemap():
    rel = 'sitemap.xml'
    try:
        root = ET.fromstring(read(rel))
    except Exception as e:
        err(f'{rel}: XML does not parse ({e})')
        return
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locs = root.findall('.//s:url', ns) or root.findall('.//url')
    if len(locs) < 10:
        err(f'{rel}: only {len(locs)} <url> entries')
    today = datetime.date.today()
    for url in locs:
        loc = url.find('s:loc', ns) if url.find('s:loc', ns) is not None \
            else url.find('loc')
        lm = url.find('s:lastmod', ns) if url.find('s:lastmod', ns) is not None \
            else url.find('lastmod')
        if loc is None:
            err(f'{rel}: <url> without <loc>')
            continue
        target = loc.text.replace('https://quantmedia.io/', '') or 'index.html'
        if target and not target.startswith('http'):
            if not os.path.exists(os.path.join(ROOT, target)):
                err(f'{rel}: {loc.text} has no corresponding file')
        if lm is not None:
            try:
                d = datetime.date.fromisoformat(lm.text)
                if d > today:
                    err(f'{rel}: {loc.text} lastmod {lm.text} is in the future')
            except Exception:
                err(f'{rel}: {loc.text} lastmod {lm.text!r} is not a date')


def check_no_visible_loading_placeholder():
    """No page may serve a JS loading placeholder as its crawlable text.

    news.html and quantum-signals.html each shipped an element whose contents
    were only ever filled by JavaScript, so every crawler - and every reader
    with JS blocked - saw "Loading latest snapshot..." under the H1 and
    "loading..." where the session date belongs. Both now render server-side
    from the pipeline; this stops them regressing to a placeholder.

    Only text a crawler actually reads is inspected: <script>, <style> and
    <template> contents are stripped first, so the JS that legitimately sets a
    loading state at runtime is not flagged.
    """
    pat = re.compile(r'(?i)>[^<]{0,30}\b(loading|please wait|fetching\b|coming soon|'
                     r'no data available)\b[^<]{0,30}<')
    for rel in html_files():
        try:
            html = read(rel)
        except Exception:
            continue
        visible = re.sub(r'(?is)<(script|style|template|noscript).*?</\1>', ' ', html)
        for m in pat.findall(visible):
            err(f'{rel}: serves a JavaScript placeholder ("{m}") as crawlable '
                f'text - render it server-side instead')


def check_profilepage_schema():
    """ProfilePage must follow Google's profile spec, not the Article spec.

    Search Console raised three warnings on /author/cemil-erturk.html because
    page() emitted the same Article-shaped node for every schema type:

        "dateModified" invalid datetime  - a bare date; the profile spec wants
                                           a full ISO 8601 datetime
        "mainEntityOfPage" unrecognised  - not part of the profile spec
        "author" unrecognised            - the person belongs in mainEntity,
                                           which was missing entirely

    All three are the same root cause, so this checks the shape rather than the
    three symptoms.
    """
    iso_dt = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$')
    for rel in html_files():
        try:
            html = read(rel)
        except Exception:
            continue
        for raw in re.findall(
                r'(?s)<script type="application/ld\+json">(.*?)</script>', html):
            try:
                node = json.loads(raw)
            except Exception:
                err(f'{rel}: JSON-LD block does not parse')
                continue
            if not isinstance(node, dict) or node.get('@type') != 'ProfilePage':
                continue
            me = node.get('mainEntity')
            if not isinstance(me, dict) or not me.get('name'):
                err(f'{rel}: ProfilePage is missing mainEntity with a name '
                    '- that is the one property the profile spec requires')
            for field in ('author', 'mainEntityOfPage', 'headline', 'publisher'):
                if field in node:
                    err(f'{rel}: ProfilePage carries "{field}", which the '
                        'Google profile spec does not recognise - describe the '
                        'person in mainEntity instead')
            for field in ('dateCreated', 'dateModified'):
                v = node.get(field)
                if v and not iso_dt.match(str(v)):
                    err(f'{rel}: ProfilePage {field}={v!r} is not a full ISO 8601 '
                        'datetime - a bare date is reported as invalid')


def check_signal_consistency():
    """One scan, one set of numbers, everywhere it is published.

    data/quantum_signals.json is the source of truth. Before this existed the
    site actively contradicted itself: with buy_count = 67, the Signal Breadth
    index correctly said "67 of 179 reached the 22/30 threshold" while
    quantum-signals.html shipped the sentence "No BUY signals today" in its
    static markup. Crawlers read hidden text, so the site's core product page
    told every crawler the opposite of the truth.

    Checks, in order of how badly each would mislead a reader:
      1. no page states there are no BUY signals when there are
      2. the BUY table actually contains the rows the JSON claims
      3. the breadth index quotes the same two numbers
      4. the homepage quotes the same two numbers
    """
    rel = 'data/quantum_signals.json'
    if not os.path.exists(os.path.join(ROOT, rel)):
        return
    try:
        sig = json.loads(read(rel))
    except Exception as e:
        err(rel + ': does not parse (' + str(e) + ')')
        return

    rows = sig.get('signals') or []
    if not rows:
        return
    actual_buys = sum(1 for r in rows
                      if str(r.get('d', '')).upper() == 'BUY')
    claimed = sig.get('buy_count')
    scored = sig.get('total_count') or len(rows)
    md = sig.get('market_date') or ''

    if claimed is not None and claimed != actual_buys:
        err(rel + ': buy_count=' + str(claimed) + ' but ' + str(actual_buys)
            + ' rows are marked BUY - the payload contradicts itself')

    n_buy = actual_buys
    qs = 'quantum-signals.html'
    if os.path.exists(os.path.join(ROOT, qs)):
        text = read(qs)

        # 1. The false-negative that started this. Crawlers read hidden text,
        #    so display:none is no defence - the notice must be absent.
        m = re.search(r'id="noBuyMsg" style="display:(\w+)', text)
        if n_buy and m and m.group(1) != 'none':
            err(qs + ': the "No BUY signals today" notice is displayed while '
                + str(n_buy) + ' BUY signals exist')
        # display:none is not enough. Crawlers and language models read hidden
        # text, which is how the original contradiction reached production in
        # the first place, so the words must be absent from the markup.
        visible = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', text)
        if n_buy and re.search(r'(?i)no BUY signals', visible):
            err(qs + ': the phrase "no BUY signals" is in the crawlable markup '
                'while ' + str(n_buy) + ' BUY signals exist - hiding it with '
                'display:none does not stop a crawler reading it')
        m = re.search(r'id="signalTableWrap" style="display:(\w+)', text)
        if n_buy and m and m.group(1) != 'block':
            err(qs + ': the BUY table is hidden while ' + str(n_buy)
                + ' BUY signals exist')

        # 2. The rendered table must carry the rows, not a spinner.
        m = re.search(r'<!-- QM:SIGNALS_ROWS:START -->(.*?)'
                      r'<!-- QM:SIGNALS_ROWS:END -->', text, re.DOTALL)
        if not m:
            err(qs + ': QM:SIGNALS_ROWS anchor missing - the BUY table cannot '
                'be server-rendered and crawlers will see an empty table')
        else:
            rendered = m.group(1).count('<tr>')
            if rendered != n_buy:
                err(qs + ': renders ' + str(rendered) + ' BUY rows but the '
                    'payload has ' + str(n_buy))

        # 3. The summary must quote the payload, not a stale copy.
        m = re.search(r'<!-- QM:SIGNALS_SUMMARY:START -->(.*?)'
                      r'<!-- QM:SIGNALS_SUMMARY:END -->', text, re.DOTALL)
        if m and md and md not in m.group(1):
            err(qs + ': summary does not state the payload market_date ' + md)

    # 4. Signal Breadth and the homepage must agree with the same payload.
    pair = str(n_buy) + ' of ' + str(scored)
    for other in ('indices/signal-breadth.html', 'index.html'):
        path = os.path.join(ROOT, other)
        if not os.path.exists(path):
            continue
        text = read(other)
        inner = ''.join(m.group(1) for m in re.finditer(
            r'<!-- QM:[A-Z_]+:START -->(.*?)<!-- QM:[A-Z_]+:END -->',
            text, re.DOTALL))
        if not inner:
            continue
        flat = ' '.join(re.sub(r'<[^>]+>', ' ', inner).split())
        if pair not in flat:
            err(other + ': server-rendered region does not state "' + pair
                + '" - it has drifted from data/quantum_signals.json')


# ---------------------------------------------------------------------------
def main():
    warn_only = '--warn-only' in sys.argv
    print('=' * 66)
    print('QuantMedia pre-commit production validation')
    print('=' * 66)

    checks = [
        ('required files',          check_required_files),
        ('forbidden strings',       check_forbidden_strings),
        ('signal config',           check_signal_config),
        ('methodology consistency', check_methodology_consistency),
        ('stale homepage copy',     check_stale_homepage_copy),
        ('fabricated attribution',  check_no_fabricated_attribution),
        ('html structure',          check_html_structure),
        ('blank-data regression',   check_blank_data_regression),
        ('signal payload',          check_signals),
        ('status ledger',           check_status),
        ('sitemap',                 check_sitemap),
        ('js-only placeholders',    check_no_visible_loading_placeholder),
        ('profilepage schema',      check_profilepage_schema),
        ('signal consistency',      check_signal_consistency),
    ]
    for label, fn in checks:
        before = len(ERRORS)
        try:
            fn()
        except Exception as e:                  # a validator bug must not
            warn(f'{label}: validator raised {e!r}')   # block a good deploy
        status = 'FAIL' if len(ERRORS) > before else 'ok'
        print(f'  [{status:>4}] {label}')

    for rel, key in (('data/markets_fx.json', 'forex'),
                     ('data/markets_crypto.json', 'crypto'),
                     ('data/news.json', 'news'),
                     ('data/markets_bar.json', 'bar')):
        check_feed(rel, key)

    print()
    if WARNINGS:
        print(f'{len(WARNINGS)} warning(s):')
        for w in WARNINGS:
            print(f'  WARN  {w}')
        print()
    if ERRORS:
        print(f'{len(ERRORS)} error(s):')
        for e in ERRORS:
            print(f'  ERROR {e}')
            if os.environ.get('GITHUB_ACTIONS'):
                print(f'::error::{e}')
        print()
        if warn_only:
            print('RESULT: FAILED (--warn-only, not blocking)')
            return 0
        print('RESULT: FAILED - refusing to commit/deploy this build')
        return 1

    print('RESULT: PASSED - safe to commit and deploy')
    return 0


if __name__ == '__main__':
    sys.exit(main())
