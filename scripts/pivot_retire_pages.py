"""Pivot, step 1: retire the off-thesis pages and re-cut the site chrome.

THE DECISION THIS IMPLEMENTS
----------------------------
QuantMedia stops being a financial media site (news digest, market dashboards,
a screener, a dozen loosely related papers) and becomes a verification practice
for quantitative finance code: verified reference implementations, dated
verification reports, and the tooling to check your own implementation
against known ground truth.

Google's "Low value content" verdict, three times over, was a reviewer saying
"I cannot tell what this site is for." Six of eleven papers, the news feed, the
forex/crypto/equity dashboards and the screener-as-product were the reason.

RETIREMENT IS REVERSIBLE BY DESIGN
----------------------------------
Nothing is deleted and nothing 404s. A retired page keeps its file and its
body, and gains:

  - robots noindex,follow          (leaves the index; keeps passing link equity)
  - canonical -> the nearest on-thesis page
  - meta refresh -> the same page  (GitHub Pages has no server redirects)
  - a visible one-line notice      (for anyone whose UA ignores the refresh)
  - a <!-- qm-retired --> marker   (validator and pipeline skip it)

and is dropped from the sitemap, the nav and both footer variants. Undoing it
is deleting four lines from the <head>.

KEPT AND DEMOTED, NOT RETIRED
-----------------------------
quantum-signals.html and both /indices/ pages stay indexed. They are the live
demonstration of the pipeline discipline (honest freshness, no backfill, one
payload driving every page), which is itself part of the verification story.
They leave the nav and the homepage hero; they remain in the footer.

Idempotent.
"""
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARK = '<!-- qm-retired -->'

# page -> nearest on-thesis destination
RETIRE = {
    'news.html':                                 '/',
    'markets.html':                              '/indices/signal-breadth.html',
    'stocks.html':                               '/indices/signal-breadth.html',
    'claude-ai-trading.html':                    '/reproducibility.html',
    'sector-rotation-guide.html':                '/indices/sector-confluence.html',
    'infrastructure.html':                       '/reproducibility.html',
    'research.html':                             '/paper-vpin-order-flow-toxicity.html',
    'paper-sovereign-ai-local-llms.html':        '/papers.html',
    'paper-bist-sentiment-analysis.html':        '/papers.html',
    'paper-genetic-algorithm-alpha.html':        '/papers.html',
    'paper-gpu-cpu-trading-infrastructure.html': '/papers.html',
    'paper-hf-analytical-operations.html':       '/papers.html',
    'paper-alternative-data-quant-finance.html': '/papers.html',
}

NAV = [
    ('/', 'Home'),
    ('/reproducibility.html', 'Verified Methods'),
    ('/reports/', 'Reports'),
    ('/papers.html', 'Papers'),
    ('/methodology.html', 'Methodology'),
    ('/about.html', 'About'),
]

FT_COLS = [
    ('Verified methods', [
        ('/reproducibility.html', 'Implementations &amp; tests'),
        ('/reports/', 'Verification reports'),
        ('/tools/probabilistic-sharpe-ratio-calculator.html', 'PSR calculator'),
        ('/learn/deflated-sharpe-ratio.html', 'Deflated Sharpe explainer'),
    ]),
    ('Research', [
        ('/paper-vpin-order-flow-toxicity.html', 'VPIN &amp; flow toxicity'),
        ('/paper-hierarchical-risk-parity.html', 'Hierarchical Risk Parity'),
        ('/paper-probabilistic-sharpe-ratio.html', 'Probabilistic Sharpe'),
        ('/paper-slippage-latency-modeling.html', 'Slippage modelling'),
        ('/papers.html', 'All papers'),
    ]),
    ('Live pipeline', [
        ('/indices/signal-breadth.html', 'Signal Breadth Index'),
        ('/indices/sector-confluence.html', 'Sector Confluence'),
        ('/quantum-signals.html', 'Daily scan (demo)'),
        ('/methodology.html', 'Methodology'),
    ]),
    ('QuantMedia', [
        ('/about.html', 'About'),
        ('/author/cemil-erturk.html', 'Author'),
        ('/editorial-policy.html', 'Editorial policy'),
        ('/contact.html', 'Contact'),
        ('/privacy.html', 'Privacy'),
    ]),
]

stats = {'retired': 0, 'nav': 0, 'footer': 0, 'cards': 0, 'sitemap': 0}


def rel_of(f):
    return f.relative_to(ROOT).as_posix()


def retire(f, target):
    s = f.read_text(encoding='utf-8')
    if MARK in s:
        return False
    head_add = (f'{MARK}\n'
                f'<meta http-equiv="refresh" content="0;url={target}">\n')
    s = re.sub(r'<meta name="robots" content="[^"]*">',
               '<meta name="robots" content="noindex,follow">', s, count=1)
    if 'name="robots"' not in s:
        head_add += '<meta name="robots" content="noindex,follow">\n'
    s = re.sub(r'<link rel="canonical" href="[^"]*">',
               f'<link rel="canonical" href="https://quantmedia.io{target}">', s, count=1)
    s = s.replace('</head>', head_add + '</head>', 1)
    notice = (f'<div style="background:#1a1a1a;color:#e8e8e8;border-bottom:2px solid #00a651;'
              f'padding:12px 20px;font:14px/1.6 sans-serif;text-align:center">This page has '
              f'been retired as part of QuantMedia\'s refocus on verified quantitative '
              f'methods. <a href="{target}" style="color:#00a651">Continue to the current '
              f'page &rarr;</a></div>\n')
    s = re.sub(r'(<body[^>]*>)', r'\1\n' + notice.replace('\\', '\\\\'), s, count=1)
    f.write_text(s, encoding='utf-8')
    return True


def nav_html(active_rel, indent, mobile=False):
    out = []
    for href, label in NAV:
        cur = (href == '/' and active_rel == 'index.html') or href.lstrip('/') == active_rel
        cls = ' class="active"' if cur else ''
        out.append(f'{indent}<a href="{href}"{cls}>{label}</a>')
    return '\n'.join(out)


def recut_nav(f, s):
    rel = rel_of(f)
    n = 0
    m = re.search(r'(<nav class="main-nav">)(.*?)(</nav>)', s, re.S)
    if m:
        s = s[:m.start()] + m.group(1) + '\n' + nav_html(rel, '      ') + '\n    ' + m.group(3) + s[m.end():]
        n += 1
    m = re.search(r'(<div class="mobile-nav"[^>]*>)(.*?)(</div>)', s, re.S)
    if m:
        s = s[:m.start()] + m.group(1) + '\n' + nav_html(rel, '  ', True) + '\n' + m.group(3) + s[m.end():]
        n += 1
    # 404.html carries a bare list of links
    if rel == '404.html':
        s = re.sub(r'<a href="/?(news|markets|stocks|research|infrastructure|quantum-signals)\.html">[^<]*</a>\s*', '', s)
    return s, n


def recut_footer(s):
    changed = False
    # variant A: .ft-col blocks inside <div class="footer-top">
    m = re.search(r'(<div class="footer-top">.*?<div class="ft-col">)(.*?)(</div>\s*</div>\s*<div class="footer-bottom">)', s, re.S)
    if m:
        cols = ''.join(
            f'    <div class="ft-col">\n      <h4>{h}</h4>\n' +
            ''.join(f'      <a href="{u}">{t}</a>\n' for u, t in links) + '    </div>\n'
            for h, links in FT_COLS)
        head = re.search(r'<div class="footer-top">.*?(?=<div class="ft-col">)', s, re.S).group(0)
        # head ends in the indentation of the first column; the columns carry
        # their own. Without the rstrip, four spaces accumulate on every run
        # and the tree is never byte-stable.
        head = head.rstrip(' \t')
        tail = s[m.end(2):]
        s = s[:m.start()] + head + cols + '  </div>\n  <div class="footer-bottom">' + tail[len(m.group(3)):]
        changed = True
    # variant B: flat .footer-col blocks (h4 + anchors, no nested divs) ahead of
    # <div class="footer-bottom">. Structure-agnostic: delete every such block,
    # then insert the new columns once, just before footer-bottom. The earlier
    # single-regex version silently matched nothing on the paper pages.
    # Test the MARKUP, not the substring: the shared stylesheet declares .ft-col
    # on every page, so `'ft-col' not in s` was False everywhere and this branch
    # never ran. That is why three columns of "Analysis | Markets | Lab" kept
    # surviving on the hand-written pages.
    if 'class="ft-col"' not in s and 'class="footer-col"' in s:
        # Structural, not pattern-matched: everything from the first column to
        # the close of .footer-inner is replaced. Column innards vary (the
        # link-strip pass leaves blank lines) and a content pattern kept
        # silently failing to match, which is how "Author" ended up in the nav.
        inner = s.find('<div class="footer-inner">')
        first = s.find('<div class="footer-col">', inner)
        close = re.compile(r'\s*</div>\s*<div class="footer-bottom">').search(s, first)
        if inner != -1 and first != -1 and close:
            cols = ''.join(
                f'\n    <div class="footer-col">\n      <h4>{h}</h4>\n' +
                ''.join(f'      <a href="{u}">{t}</a>\n' for u, t in links) + '    </div>'
                for h, links in FT_COLS)
            new = s[:first].rstrip(' \t') + cols.lstrip('\n') + '\n  </div>\n  <div class="footer-bottom">' \
                + s[close.end():]
            if new != s:
                s = new
                changed = True
    return s, changed


# Body copy on live pages ("See also" strips, sidebar widgets, research-only
# lists) links retired pages by name. Pointing "Market News" at the homepage
# would mislabel it, so the anchor is removed together with its separator or
# its list item.
# Anchor text may carry inline markup (<strong>, an icon <span>), so the body
# is "anything up to the closing tag", not "no tags".
RETIRED_HREF = re.compile(
    r'<a href="/?(?:' + '|'.join(re.escape(p) for p in RETIRE) + r')(?:#[a-z]*)?"[^>]*>'
    r'(?:(?!</a>).)*</a>', re.S)


def strip_body_links(s):
    n = 0
    # <li> wrapping only the retired link
    s, k = re.subn(r'\s*<li[^>]*>\s*' + RETIRED_HREF.pattern + r'(?:\s*<[^>]+>[^<]*</[^>]+>)?\s*</li>', '', s, flags=re.S)
    n += k
    # inline "a · b · c" strips: drop the link and one adjacent separator
    s, k = re.subn(r'(?:\s*(?:&middot;|·|\|)\s*)?' + RETIRED_HREF.pattern + r'(?:\s*(?:&middot;|·|\|))?', '', s)
    n += k
    # anything left standing alone
    s, k = RETIRED_HREF.subn('', s)
    n += k
    return s, n


def trim_paper_cards(s):
    n = 0
    for page in RETIRE:
        if not page.startswith('paper-'):
            continue
        pat = re.compile(r'\s*<!--[^>]*-->\s*<a href="' + re.escape(page) +
                         r'" class="paper-card">.*?</a>', re.S)
        s, k = pat.subn('', s)
        n += k
    return s, n


def main():
    for f in sorted(ROOT.rglob('*.html')):
        if any(p in ('.git', 'node_modules') for p in f.parts):
            continue
        rel = rel_of(f)
        if rel in RETIRE and retire(f, RETIRE[rel]):
            stats['retired'] += 1
            print(f'  [retire] {rel} -> {RETIRE[rel]}')
        s = o = f.read_text(encoding='utf-8')
        s, n = recut_nav(f, s)
        stats['nav'] += n
        s, ch = recut_footer(s)
        stats['footer'] += ch
        if rel not in RETIRE:
            s, k = strip_body_links(s)
            stats['body'] = stats.get('body', 0) + k
        if rel == 'papers.html':
            s, k = trim_paper_cards(s)
            stats['cards'] += k
        if s != o:
            f.write_text(s, encoding='utf-8')

    # sitemap: drop retired, add reports
    sm = ROOT / 'sitemap.xml'
    xml = sm.read_text(encoding='utf-8')
    for page in RETIRE:
        xml, k = re.subn(r'\s*<url>\s*<loc>https://quantmedia\.io/' + re.escape(page) +
                         r'</loc>.*?</url>', '', xml, flags=re.S)
        stats['sitemap'] += k
    # The report URLs already exist (reports/, vpin-example, hrp-example,
    # psr-worked-example) and are the canonical ones. Adding a second set
    # would be the "duplicated intent" Google flagged. Nothing is added here.
    sm.write_text(xml, encoding='utf-8')

    for k, v in stats.items():
        print(f'  {k:8} {v}')

    bad = []
    for page in RETIRE:
        s = (ROOT / page).read_text(encoding='utf-8')
        if MARK not in s or 'noindex' not in s or 'http-equiv="refresh"' not in s:
            bad.append(page)
        if f'/{page}' in xml:
            bad.append(f'{page} still in sitemap')
    for f in ROOT.rglob('*.html'):
        if '.git' in f.parts:
            continue
        s = f.read_text(encoding='utf-8')
        if MARK in s:
            continue
        for page in ('news.html', 'markets.html', 'stocks.html', 'research.html', 'infrastructure.html'):
            if re.search(r'<a href="/?' + re.escape(page) + '"', s):
                bad.append(f'{rel_of(f)} still links {page}')
                break
    if bad:
        print('  PROBLEMS:'); [print('   -', b) for b in bad[:12]]
        sys.exit(1)
    print('verified: retired pages marked, out of sitemap, no live page links to them')


if __name__ == '__main__':
    main()
