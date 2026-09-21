#!/usr/bin/env python3
"""Fixes from the 21 September 2026 pre-AdSense live audit. Idempotent.

  1. about.html: a market bar that never rendered ("Market data updates when
     available") sat under the header; an empty widget on the About page.
     Removed with its JS call.
  2. methodology.html: still documented the TradingView ticker (removed 14
     Sep) as the site's "one real-time exception", and a News page that no
     longer exists. Row, sentence and section corrected.
  3. privacy.html section 6 claimed the browser retrieves live data from
     third-party APIs that may log the visitor's IP. Data is fetched
     server-side by the pipeline; the browser only loads quantmedia.io JSON.
     Rewritten truthfully; TradingView dropped.
  4. papers.html: hero copy listed six retired topics and one sentence had an
     empty subject ("the  covers") left by link stripping.
  5. manifest.json: "live market data" -> what the site is.
  6. Heading order: papers used <h4>/<h3> for "Key Takeaways" directly under
     the H1 and <h4> in related cards; quantum-signals used <h4>Contents</h4>
     under an H2. Tags and their tag-based CSS selectors moved together.
  7. build_pages.py EXTRA_CSS: .qm-table-wrap had no overflow rule, so the
     experiment notes' wide tables overflowed the viewport at 320px.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rw(rel, fn):
    p = os.path.join(ROOT, rel)
    with open(p, encoding='utf-8', newline='') as fh:
        raw = fh.read()
    nl = '\r\n' if '\r\n' in raw else '\n'
    s = raw.replace('\r\n', '\n')
    s2 = fn(s)
    if s2 != s:
        with open(p, 'w', encoding='utf-8', newline='') as fh:
            fh.write(s2.replace('\n', nl))
        print('  patched', rel)
    else:
        print('  unchanged', rel)


def about(s):
    s = re.sub(r'\n<!-- MARKET BAR -->\n<div class="market-bar">.*?</div>\n</div>\n', '\n', s, count=1, flags=re.S)
    s = re.sub(r"/\* Market bar reads data/markets_bar\.json via qm-data\.js\..*?\*/\nQM\.marketBar\('mbarItems','mbarLabel'\);\n", '', s, count=1, flags=re.S)
    # A dead fabricated ticker ('VPIN AAPL 0.312', 'LATENCY P99 740 ns', ...)
    # targeting an element that no longer exists. The statement threw, which
    # also killed the hamburger menu and theme toggle defined below it.
    s = re.sub(r"const ticks=\[\n.*?\];\nconst t=document\.getElementById\('ticker'\);\nconst d=\[\.\.\.ticks,\.\.\.ticks\];\nt\.innerHTML=d\.map\([^\n]*\n", '', s, count=1, flags=re.S)
    # TradingView ticker host and its deferred loader: third-party content on the About page.
    s = re.sub(r'\n[^\n]*<div id="tickerWrap"[^\n]*\n', '\n', s, count=1)
    s = re.sub(r"<script>window\.addEventListener\('load',function\(\)\{setTimeout\(function\(\)\{var w=document\.getElementById\('tickerWrap'\);.*?</script>\n?", '', s, count=1, flags=re.S)
    return s


def methodology(s):
    s = re.sub(r'\s*<tr><td><strong>TradingView</strong></td>.*?</tr>', '', s, count=1, flags=re.S)
    s = re.sub(r'<tr><td><strong>Finnhub</strong></td><td>News headlines</td><td>General market newswire</td><td>[^<]*</td></tr>',
               '<tr><td><strong>Finnhub</strong></td><td>News headlines</td><td>General market newswire</td>'
               '<td>Captured server-side once per weekday as a pipeline health signal; headlines are not currently displayed on any page. '
               'The API key is held as a repository secret and is never sent to the browser.</td></tr>', s, count=1)
    s = s.replace('<p>With one exception, <strong>nothing on this site is real-time</strong>.', '<p><strong>Nothing on this site is real-time</strong>.')
    s = s.replace(' The single exception is the embedded TradingView widget, which streams its own data independently.', '')
    # Remove the News Classification section (the News page was retired on 4 Sep and deleted on 14 Sep).
    s = re.sub(r'\n  <!-- NEWS METHODOLOGY -->\n  <div class="section-header" id="news-methodology">.*?(?=\n  <div class="section-header" id="signal-engine">)', '\n', s, count=1, flags=re.S)
    return s


def privacy(s):
    old = re.search(r'    <h2>6\. Third-Party Market Data</h2>.*?<p>We do not control the data practices of these third-party services\.</p>', s, re.S)
    if not old:
        return s
    new = ('    <h2>6. Third-Party Market Data</h2>\n'
           '    <p>Market data on this Site is end-of-day, not live. It is collected once per weekday by an automated pipeline running on '
           'QuantMedia\'s own infrastructure (GitHub Actions) and published as static JSON files on quantmedia.io. Your browser loads those '
           'files from quantmedia.io only; it does not contact the upstream providers, and they do not see your visit. The upstream sources are:</p>\n'
           '    <ul>\n'
           '      <li><strong>Yahoo Finance</strong> (via the <code>yfinance</code> library) &mdash; end-of-day equity, index and futures prices</li>\n'
           '      <li><strong>CoinGecko</strong> &mdash; cryptocurrency reference prices (<a href="https://www.coingecko.com/en/privacy" target="_blank" rel="noopener">Privacy Policy</a>)</li>\n'
           '      <li><strong>Open Exchange Rates API (open.er-api.com)</strong> &mdash; foreign exchange reference rates</li>\n'
           '      <li><strong>Finnhub</strong> &mdash; market headlines, captured for pipeline monitoring and not displayed (<a href="https://finnhub.io/privacy-policy" target="_blank" rel="noopener">Privacy Policy</a>)</li>\n'
           '    </ul>\n'
           '    <p>We do not control the data practices of these providers; the links above lead to their own policies.</p>')
    return s[:old.start()] + new + s[old.end():]


def papers(s):
    s = s.replace('Independent, open-access research covering market microstructure, portfolio construction, execution analytics, GPU trading infrastructure, and machine learning in finance. Each paper includes a full written analysis and Python implementation examples',
                  'Five independent research notes on market microstructure, portfolio construction and execution costs. Each note carries primary references, a stated limitations section and, where the method has been implemented here, runnable Python with tests')
    s = s.replace('Topics span VPIN order flow toxicity, Hierarchical Risk Parity, the Probabilistic Sharpe Ratio, slippage and latency modeling, genetic algorithm alpha discovery, alternative data integration, sovereign AI for investment research, and high-frequency analytical operations. All research is non-commercial and provided for educational purposes.',
                  'Topics: VPIN order flow toxicity, Hierarchical Risk Parity, the Probabilistic Sharpe Ratio, bid-ask spread dynamics, and slippage and latency modelling. All research is non-commercial and provided for educational purposes; none of it is peer reviewed.')
    s = s.replace('dashboard puts multi-factor confluence to work on 180 liquid US equities, the  covers how capital moves between S&amp;P 500 sectors, and',
                  'dashboard applies multi-factor confluence to a fixed 180-name US universe, the <a href="indices/sector-confluence.html" style="color:var(--accent)">Sector Confluence index</a> breaks that scan down by sector, and')
    return s


def manifest(s):
    return s.replace('"description": "Independent quantitative research: market microstructure, live market data, and financial analysis."',
                     '"description": "Verified implementations of quantitative finance methods: runnable code, synthetic ground truth and dated verification reports."')


def paper_headings(s):
    # Key Takeaways sits directly under the H1: it is an H2.
    s = re.sub(r'\.key-takeaways h[34]\{', '.key-takeaways h2{', s)
    s = re.sub(r'<h[34]>Key Takeaways</h[34]>', '<h2>Key Takeaways</h2>', s)
    # Related cards sit under an H2: their headings are H3s.
    s = s.replace('.related-card h4{', '.related-card h3{')
    s = re.sub(r'(<a href="[^"]+" class="related-card">\s*)<h4>(.*?)</h4>', r'\1<h3>\2</h3>', s)
    return s


def signals_headings(s):
    s = s.replace('.toc-widget h4{', '.toc-widget h3{').replace('<h4>Contents</h4>', '<h3>Contents</h3>')
    return s


def build_pages(s):
    if '.qm-table-wrap{' in s:
        return s
    return s.replace('.qm-tablewrap{overflow-x:auto}', '.qm-tablewrap{overflow-x:auto}\n.qm-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:14px 0}', 1)


def main():
    rw('about.html', about)
    rw('methodology.html', methodology)
    rw('privacy.html', privacy)
    rw('papers.html', papers)
    rw('manifest.json', manifest)
    for f in ('paper-vpin-order-flow-toxicity.html', 'paper-hierarchical-risk-parity.html', 'paper-probabilistic-sharpe-ratio.html',
              'paper-bid-ask-spread-dynamics.html', 'paper-slippage-latency-modeling.html'):
        rw(f, paper_headings)
    rw('quantum-signals.html', signals_headings)
    rw('scripts/build_pages.py', build_pages)


if __name__ == '__main__':
    main()
