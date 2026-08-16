"""Surface the site's original work from the homepage and the site chrome.

WHY THIS EXISTS
---------------
An audit of inbound internal links found that these pages had exactly ZERO
links pointing at them from anywhere in the navigation, the homepage or the
footer:

    /indices/signal-breadth.html        (daily proprietary metric)
    /indices/sector-confluence.html     (daily proprietary metric)
    /reproducibility.html               (runnable research code)
    /tools/probabilistic-sharpe-ratio-calculator.html
    /learn/*.html                       (seven explainers)

Every one of those is original work that exists nowhere else, and none of it
was reachable without typing the URL. Publishing original material and then
hiding it is worse than not publishing it: it costs the crawl budget of an
orphan page and returns nothing.

Three separate defects are fixed here.

1. HOMEPAGE has no entry point to any of it. A "What originates here" section
   is inserted immediately before the main content well.

2. NAV LABELS "Analysis" (papers.html) and "Research" (research.html) are
   near-synonyms pointing at genuinely different pages. Measured vocabulary
   overlap between the two is 10%, so these are NOT duplicates and both stay -
   but the labels made them indistinguishable. Renamed to "Papers" and
   "Microstructure", which is what each page's own <h1> already says.

3. FOOTER "Markets" column linked stocks.html three times under three
   different labels. Duplicate hrefs inflate the internal link count without
   adding a single crawlable destination. Those slots now carry the two index
   pages.

Idempotent: safe to run repeatedly, and safe to run against a tree whose data/
directory is newer than the one this was written against, because it only ever
edits navigation chrome and never touches data or the pipeline's QM: anchors.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

MARKER = 'What originates here'

HOMEPAGE_SECTION = """<!-- ORIGINAL WORK
     Everything below originates on QuantMedia rather than being aggregated
     from a data vendor. It sat unreachable from the homepage and the main nav
     until this section existed, which meant the site's only real
     differentiators were invisible to a first-time visitor. -->
<div class="page-wrap" style="padding-bottom:0">
  <div style="border:1px solid var(--bd);border-radius:6px;background:var(--bg2);padding:26px 26px 20px;margin-bottom:28px">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:var(--green);margin-bottom:8px">What originates here</div>
    <p style="font-size:14.5px;line-height:1.8;color:var(--text3);margin:0 0 20px;max-width:760px">
      Most of what you can read about quantitative finance online is a summary of
      someone else's paper. These four things are produced by QuantMedia: two
      daily metrics computed from our own scan, research code you can run, and
      calculators that show their working.
    </p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px">
      <div>
        <a href="/indices/signal-breadth.html" style="font-family:'Barlow Condensed',sans-serif;font-size:16px;font-weight:700;color:var(--green);letter-spacing:.2px">Signal Breadth Index &rarr;</a>
        <p style="font-size:13px;line-height:1.7;color:var(--text3);margin:6px 0 0">How much of a 180-stock US universe clears a 22-of-30 technical threshold, recomputed after every close. Formula, history and JSON published.</p>
      </div>
      <div>
        <a href="/indices/sector-confluence.html" style="font-family:'Barlow Condensed',sans-serif;font-size:16px;font-weight:700;color:var(--green);letter-spacing:.2px">Sector Confluence &rarr;</a>
        <p style="font-size:13px;line-height:1.7;color:var(--text3);margin:6px 0 0">The same scan grouped by sector and ranked by mean score, so you can see where technical agreement is concentrated rather than only how much exists.</p>
      </div>
      <div>
        <a href="/reproducibility.html" style="font-family:'Barlow Condensed',sans-serif;font-size:16px;font-weight:700;color:var(--green);letter-spacing:.2px">Reproducible code &rarr;</a>
        <p style="font-size:13px;line-height:1.7;color:var(--text3);margin:6px 0 0">Runnable VPIN and Hierarchical Risk Parity implementations with example data, expected output and 28 tests. Papers without code are labelled as such.</p>
      </div>
      <div>
        <a href="/tools/probabilistic-sharpe-ratio-calculator.html" style="font-family:'Barlow Condensed',sans-serif;font-size:16px;font-weight:700;color:var(--green);letter-spacing:.2px">PSR calculator &rarr;</a>
        <p style="font-size:13px;line-height:1.7;color:var(--text3);margin:6px 0 0">Test whether a Sharpe ratio survives its own track-record length, skew and kurtosis. Every intermediate value is shown so you can check it.</p>
      </div>
    </div>
    <p style="font-size:12.5px;line-height:1.7;color:var(--text3);margin:20px 0 0;padding-top:16px;border-top:1px solid var(--bd)">
      Short explainers with worked examples:
      <a href="/learn/what-is-vpin.html" style="color:var(--green)">VPIN</a> &middot;
      <a href="/learn/hrp-vs-mean-variance.html" style="color:var(--green)">HRP vs mean-variance</a> &middot;
      <a href="/learn/what-is-probabilistic-sharpe-ratio.html" style="color:var(--green)">Probabilistic Sharpe Ratio</a> &middot;
      <a href="/learn/deflated-sharpe-ratio.html" style="color:var(--green)">Deflated Sharpe Ratio</a> &middot;
      <a href="/learn/how-to-model-slippage-in-backtests.html" style="color:var(--green)">slippage modelling</a>
    </p>
  </div>
</div>

<!-- MAIN CONTENT -->
<div class="page-wrap">"""

ANCHOR = '<!-- MAIN CONTENT -->\n<div class="page-wrap">'

# Nav blocks only. Renaming every occurrence of the word "Research" across the
# site would rewrite body prose, which is not the defect being fixed.
NAV_RE = re.compile(
    r'(<nav class="main-nav">.*?</nav>|<div class="mobile-nav"[^>]*>.*?</div>)', re.S)

MARKETS_COL_RE = re.compile(
    r'(<h4>Markets</h4>\s*\n)((?:[ \t]*<a [^>]*>[^<]*</a>[ \t]*\n)+)')
LINK_RE = re.compile(r'^(\s*)<a href="([^"]+)"[^>]*>([^<]*)</a>\s*$')

LAB_OLD = '      <h4>Lab</h4>\n      <a href="research.html">Research Home</a>'
LAB_NEW = ('      <h4>Lab</h4>\n'
           '      <a href="/reproducibility.html">Reproducible Code</a>\n'
           '      <a href="/tools/probabilistic-sharpe-ratio-calculator.html">PSR Calculator</a>\n'
           '      <a href="research.html">Microstructure Research</a>')

INDEX_LINKS = [
    ('/indices/signal-breadth.html', 'Signal Breadth Index'),
    ('/indices/sector-confluence.html', 'Sector Confluence'),
]

# ---------------------------------------------------------------------------
# Second pass: the site has TWO footer structures, not one.
#
# 22 pages use `.ft-col` (the methodology.html shell, which build_pages.py
# lifts for every generated page) and 19 use `.footer-col`. The first pass only
# knew about `.footer-col`, so every generated page - including the learn
# explainers and the reproducibility hub - still had no route to the indices.
# Fixing the shell fixes all of them, but only if build_pages.py is re-run
# afterwards, since it copies this footer at build time.
# ---------------------------------------------------------------------------
FTCOL_ANCHOR = '''    <div class="ft-col">
      <h4>Lab</h4>'''

FTCOL_NEW = '''    <div class="ft-col">
      <h4>Data &amp; Code</h4>
      <a href="/indices/signal-breadth.html">Signal Breadth Index</a>
      <a href="/indices/sector-confluence.html">Sector Confluence</a>
      <a href="/reproducibility.html">Reproducible Code</a>
      <a href="/tools/probabilistic-sharpe-ratio-calculator.html">PSR Calculator</a>
    </div>
    <div class="ft-col">
      <h4>Lab</h4>'''

# Identity links belong in every footer variant, not just the homepage one.
IDENTITY_LINKS = [
    ('about.html', '<a href="/author/cemil-erturk.html">Author</a>'),
    ('privacy.html', '<a href="/editorial-policy.html">Editorial Policy</a>'),
]

# "Non-Commercial" is not true of a site funded by AdSense, and it directly
# contradicts the funding disclosure on /editorial-policy.html. A trust badge
# that conflicts with the trust page is worse than no badge.
BADGE_FIXES = [
    ('<span class="fbadge">Non-Commercial</span>',
     '<span class="fbadge">Independent</span>'),
]

stats = {'homepage': 0, 'nav': 0, 'markets': 0, 'lab': 0, 'dupes': 0,
         'ftcol': 0, 'identity': 0, 'badge': 0}


def rename_nav(block):
    block = re.sub(r'(<a href="/?papers\.html"[^>]*>)Analysis(</a>)', r'\1Papers\2', block)
    block = re.sub(r'(<a href="/?research\.html"[^>]*>)Research(</a>)',
                   r'\1Microstructure\2', block)
    return block


def rebuild_markets(m):
    head, body = m.group(1), m.group(2)
    kept, seen, indent = [], set(), '      '
    for ln in body.split('\n'):
        if not ln.strip():
            continue
        mm = LINK_RE.match(ln)
        if not mm:
            kept.append(ln)
            continue
        indent, href = mm.group(1), mm.group(2)
        if href in seen:                      # same destination, different label
            stats['dupes'] += 1
            continue
        seen.add(href)
        kept.append(ln)
    for href, label in INDEX_LINKS:
        if href not in seen:
            kept.append(f'{indent}<a href="{href}">{label}</a>')
            seen.add(href)
    return head + '\n'.join(kept) + '\n'


for f in sorted(ROOT.rglob('*.html')):
    if any(p in ('node_modules', '.git') for p in f.parts):
        continue
    src = out = f.read_text(encoding='utf-8')

    if f.name == 'index.html' and f.parent == ROOT and MARKER not in out:
        if ANCHOR not in out:
            print(f'ERROR: homepage anchor not found in {f}', file=sys.stderr)
            sys.exit(1)
        out = out.replace(ANCHOR, HOMEPAGE_SECTION, 1)
        stats['homepage'] += 1

    before = out
    out = NAV_RE.sub(lambda m: rename_nav(m.group(0)), out)
    # 404.html carries a bare nav with no .main-nav class.
    out = rename_nav(out) if f.name == '404.html' else out
    if out != before:
        stats['nav'] += 1

    before = out
    out = MARKETS_COL_RE.sub(rebuild_markets, out)
    if out != before:
        stats['markets'] += 1

    before = out
    out = out.replace(LAB_OLD, LAB_NEW)
    if out != before:
        stats['lab'] += 1

    # --- second footer variant ---
    if 'Data &amp; Code' not in out and FTCOL_ANCHOR in out:
        out = out.replace(FTCOL_ANCHOR, FTCOL_NEW, 1)
        stats['ftcol'] += 1

    before = out
    for after_href, link in IDENTITY_LINKS:
        if link in out:
            continue
        m = re.search(r'([ \t]*)<a href="/?' + re.escape(after_href) + r'"[^>]*>[^<]*</a>\n', out)
        if m:
            out = out[:m.end()] + m.group(1) + link + '\n' + out[m.end():]
    if out != before:
        stats['identity'] += 1

    before = out
    for old, new in BADGE_FIXES:
        out = out.replace(old, new)
    if out != before:
        stats['badge'] += 1

    if out != src:
        f.write_text(out, encoding='utf-8')

for k, v in stats.items():
    print(f'  {k:10} {v}')

# Prove the orphans are gone rather than assuming the edits landed.
print('\ninbound internal links:')
failed = False
for target in ('/indices/signal-breadth.html', '/indices/sector-confluence.html',
               '/reproducibility.html', '/tools/probabilistic-sharpe-ratio-calculator.html',
               '/learn/what-is-vpin.html', '/author/cemil-erturk.html',
               '/editorial-policy.html'):
    n = sum(1 for f in ROOT.rglob('*.html')
            if '.git' not in f.parts and target in f.read_text(encoding='utf-8'))
    flag = 'ok ' if n else 'ORPHAN'
    if not n:
        failed = True
    print(f'  [{flag}] {target:52} {n}')

if re.search(r'>Analysis</a>', (ROOT / 'index.html').read_text(encoding='utf-8')):
    print('ERROR: ambiguous "Analysis" nav label still present', file=sys.stderr)
    failed = True

sys.exit(1 if failed else 0)
