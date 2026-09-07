#!/usr/bin/env python3
"""Bring the copy that still described the pre-pivot site into line with
what QuantMedia now is: a verification practice for quantitative finance
code. Found by the 7 Sep 2026 read-only audit.

  1. Homepage site-search index listed 12 retired pages.
  2. Homepage About / What We Research / Platform Tools paragraphs described
     retired products (news digest, market data, GPU infrastructure) and one
     paragraph had empty subjects where retired links were stripped.
  3. about.html: "11 research papers" (five are live), an Infrastructure tab
     with no section, kernel-bypass / Equinix / latency-benchmark prose,
     research cards for work that is not on the site.
  4. Footer description on every page: "high-frequency infrastructure".
  5. "NASDAQ / NYSE Arca" footer badge implied a relationship.
  6. Duplicate "Editorial policy" / "Editorial Policy" footer links.
  7. "Scores 180 equities" vs the panel's "179 scored": say why.
  papers.html "11 Papers" and the methodology.html Equinix sentence too.

Idempotent. Retired pages are not touched.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', '.github', 'scripts', 'data', 'quantmedia-research', 'node_modules'}
RETIRED = '<!-- qm-retired -->'

FOOTER_DESC = ('Verified implementations of quantitative finance methods: runnable code, '
               'synthetic ground truth and dated verification reports. Educational use '
               'only; not financial advice.')

SEARCH_INDEX = """const SEARCH_INDEX = [
  {t:'page', title:'Home', sub:'Verified quantitative finance code, free', url:'index.html', kw:'home homepage ana sayfa'},
  {t:'page', title:'Verification Reports', sub:'VPIN, HRP and PSR checked against known answers', url:'reports/', kw:'reports verification examples worked do\\u011frulama'},
  {t:'page', title:'VPIN Verification Report', sub:'One tape, two classifiers, one defect fixed', url:'reports/vpin-example.html', kw:'vpin report bulk volume tick rule'},
  {t:'page', title:'HRP Verification Report', sub:'Six allocators, two defects fixed', url:'reports/hrp-example.html', kw:'hrp report allocators minimum variance shrinkage'},
  {t:'page', title:'PSR Verification Report', sub:'A published example, corrected', url:'reports/psr-worked-example.html', kw:'psr report worked example'},
  {t:'page', title:'Verified Methods', sub:'Runnable Python, tests and GitHub source', url:'reproducibility.html', kw:'github code python tools vpin hrp reproducibility'},
  {t:'page', title:'Free PSR Calculator', sub:'Probabilistic Sharpe Ratio in your browser', url:'tools/probabilistic-sharpe-ratio-calculator.html', kw:'psr calculator sharpe tool hesaplay\\u0131c\\u0131'},
  {t:'page', title:'Daily Signals', sub:'Post-close scan of a 180-name US universe', url:'quantum-signals.html', kw:'signals scan buy confluence stocks hisse'},
  {t:'page', title:'Signal Breadth Index', sub:'Share of the universe clearing the 22-of-30 threshold', url:'indices/signal-breadth.html', kw:'breadth index market breadth'},
  {t:'page', title:'Sector Confluence Index', sub:'Confluence score and BUY breadth per sector', url:'indices/sector-confluence.html', kw:'sector confluence rotation'},
  {t:'page', title:'Research Notes', sub:'Five notes on microstructure, portfolios and execution', url:'papers.html', kw:'papers research notes makaleler ara\\u015ft\\u0131rma'},
  {t:'paper', title:'VPIN & Order Flow Toxicity', sub:'Research note \\u2014 Microstructure', url:'paper-vpin-order-flow-toxicity.html', kw:'vpin order flow toxicity microstructure'},
  {t:'paper', title:'Hierarchical Risk Parity (HRP)', sub:'Research note \\u2014 Portfolio', url:'paper-hierarchical-risk-parity.html', kw:'hrp risk parity portfolio clustering'},
  {t:'paper', title:'Probabilistic Sharpe Ratio', sub:'Research note \\u2014 Statistics', url:'paper-probabilistic-sharpe-ratio.html', kw:'psr sharpe ratio backtest overfitting'},
  {t:'paper', title:'Bid-Ask Spread Dynamics', sub:'Research note \\u2014 Microstructure', url:'paper-bid-ask-spread-dynamics.html', kw:'spread bid ask microstructure execution'},
  {t:'paper', title:'Slippage & Latency Modeling', sub:'Research note \\u2014 Execution', url:'paper-slippage-latency-modeling.html', kw:'slippage latency backtest execution market impact'},
  {t:'topic', title:'What is VPIN?', sub:'Explainer', url:'learn/what-is-vpin.html', kw:'vpin explainer definition'},
  {t:'topic', title:'What is the Probabilistic Sharpe Ratio?', sub:'Explainer', url:'learn/what-is-probabilistic-sharpe-ratio.html', kw:'psr explainer'},
  {t:'topic', title:'Deflated Sharpe Ratio', sub:'Explainer', url:'learn/deflated-sharpe-ratio.html', kw:'dsr deflated sharpe overfitting trials'},
  {t:'topic', title:'HRP vs Mean-Variance', sub:'Explainer', url:'learn/hrp-vs-mean-variance.html', kw:'hrp mean variance markowitz'},
  {t:'topic', title:'Modelling Slippage in Backtests', sub:'Explainer', url:'learn/how-to-model-slippage-in-backtests.html', kw:'slippage backtest impact'},
  {t:'topic', title:'What is Signal Confluence?', sub:'Explainer', url:'learn/what-is-signal-confluence.html', kw:'confluence signals threshold'},
  {t:'topic', title:'What is Market Breadth?', sub:'Explainer', url:'learn/what-is-market-breadth.html', kw:'breadth advance decline'},
  {t:'page', title:'Methodology', sub:'Data sources, editorial standards, disclosures', url:'methodology.html', kw:'methodology metodoloji data sources kaynaklar'},
  {t:'page', title:'About', sub:'What QuantMedia is and who writes it', url:'about.html', kw:'about hakk\\u0131nda quantmedia'},
  {t:'page', title:'Cemil Ert\\u00fcrk', sub:'Author page', url:'author/cemil-erturk.html', kw:'author cemil erturk yazar'},
  {t:'page', title:'Editorial Policy', sub:'Corrections, funding, AI-tool disclosure', url:'editorial-policy.html', kw:'editorial policy corrections disclosure'},
  {t:'page', title:'Contact', sub:'Questions, corrections, verification requests', url:'contact.html', kw:'contact ileti\\u015fim email'},
];"""

HOME_ABOUT = ('QuantMedia verifies quantitative finance code. Each method published here &mdash; VPIN, '
              'Hierarchical Risk Parity and the Probabilistic Sharpe Ratio &mdash; ships as runnable Python '
              'with a synthetic input whose correct answer is known in advance, tests that guard the fixes, '
              'and a dated verification report of what the code got wrong before it was corrected. '
              'Everything is free to read and free to run.')
HOME_RESEARCH = ('Research notes cover VPIN order-flow toxicity, Hierarchical Risk Parity portfolio '
                 'construction, the Probabilistic Sharpe Ratio for backtest validation, bid-ask spread '
                 'dynamics, and slippage and latency modelling. Seven short explainers and a free PSR '
                 'calculator accompany them. Research, examples and tools are freely accessible for '
                 'educational use. Advertising is the intended funding model; see our '
                 '<a href="/editorial-policy.html" style="color:var(--accent)">editorial policy</a>.')
HOME_TOOLS = ('The <a href="quantum-signals.html" style="color:var(--accent)">Quantum Signals dashboard</a> '
              'scores a fixed 180-name universe of liquid US equities against 30 technical signals after '
              'each market close, flagging the stocks where at least 22 of the 30 are simultaneously bullish. '
              'A name is skipped on any day its data window is incomplete, so the scored count can sit '
              'just below 180. Two indices derived from the same scan, '
              '<a href="/indices/signal-breadth.html" style="color:var(--accent)">Signal Breadth</a> and '
              '<a href="/indices/sector-confluence.html" style="color:var(--accent)">Sector Confluence</a>, '
              'are published with an explicit freshness state.')

ABOUT_OVERVIEW = """
      <p><strong>QuantMedia</strong> is an independent quantitative research site written and operated by <a href="/author/cemil-erturk.html">Cemil Ert&uuml;rk</a>. Its subject is whether published quantitative finance methods work as described once they are implemented: each method here ships as runnable Python with a synthetic input whose correct answer is known in advance, tests that guard the fixes, and a dated verification report of what the code got wrong before it was corrected.</p>

      <p>Two methods, <strong>VPIN</strong> and <strong>Hierarchical Risk Parity</strong>, have runnable implementations with example data and 28 tests. The <strong>Probabilistic Sharpe Ratio</strong> is covered by a worked calculation, checked step by step, and a free calculator. The remaining research notes are analytical and are not presented as validated backtests.</p>

      <p>A daily pipeline scores a fixed 180-name US equity universe after each close and publishes two indices derived from that scan, Signal Breadth and Sector Confluence, together with their freshness state. Nothing on this site is investment advice.</p>
    """

ABOUT_CARDS = """<div class="research-grid">
        <div class="research-card">
          <div class="rc-icon">&#128202;</div>
          <div class="rc-title">Order Flow Toxicity</div>
          <div class="rc-desc">A <a href="/reproducibility.html">runnable VPIN estimator</a> covering equal-volume bucketing, bulk volume classification and the tick rule, with 15 tests and a <a href="/reports/vpin-example.html">verification report</a>. The example data is synthetic and states its own limits.</div>
          <div class="rc-tags"><span class="rc-tag">VPIN</span><span class="rc-tag">Python</span><span class="rc-tag">15 tests</span></div>
        </div>
        <div class="research-card">
          <div class="rc-icon">&#129513;</div>
          <div class="rc-title">Portfolio Construction</div>
          <div class="rc-desc">A runnable <a href="/reproducibility.html">Hierarchical Risk Parity allocator</a> compared with minimum variance, shrinkage and equal weight on a synthetic panel, with 13 tests and a <a href="/reports/hrp-example.html">verification report</a>.</div>
          <div class="rc-tags"><span class="rc-tag">HRP</span><span class="rc-tag">Python</span><span class="rc-tag">13 tests</span></div>
        </div>
        <div class="research-card">
          <div class="rc-icon">&#128208;</div>
          <div class="rc-title">Backtest Statistics</div>
          <div class="rc-desc">The Probabilistic and Deflated Sharpe Ratios: a <a href="/reports/psr-worked-example.html">worked calculation</a> checked step by step, a <a href="/tools/probabilistic-sharpe-ratio-calculator.html">free calculator</a>, and explainers on track-record length, skewness and kurtosis.</div>
          <div class="rc-tags"><span class="rc-tag">PSR</span><span class="rc-tag">DSR</span><span class="rc-tag">Calculator</span></div>
        </div>
        <div class="research-card">
          <div class="rc-icon">&#128177;</div>
          <div class="rc-title">Execution Costs</div>
          <div class="rc-desc"><a href="/paper-bid-ask-spread-dynamics.html">Bid-ask spread dynamics</a> and <a href="/learn/how-to-model-slippage-in-backtests.html">slippage</a> modelled as spread, square-root impact and delay cost, with a worked example of what turnover does to a strategy net of costs.</div>
          <div class="rc-tags"><span class="rc-tag">Spread</span><span class="rc-tag">Slippage</span><span class="rc-tag">Impact</span></div>
        </div>
        <div class="research-card">
          <div class="rc-icon">&#128225;</div>
          <div class="rc-title">Daily Signal Pipeline</div>
          <div class="rc-desc">A post-close scan of a fixed 180-name US universe against 30 technical signals, publishing <a href="/indices/signal-breadth.html">Signal Breadth</a> and <a href="/indices/sector-confluence.html">Sector Confluence</a> with an explicit freshness state and a fail-safe that never labels stale data as live.</div>
          <div class="rc-tags"><span class="rc-tag">Breadth</span><span class="rc-tag">Confluence</span><span class="rc-tag">Pipeline</span></div>
        </div>
      </div>
    </div>

    """

SKIP_NOTE = (' A name whose data window is incomplete on a given day is skipped, so the '
             'scored count can be slightly below 180.')


def live_pages():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in sorted(fn):
            if f.endswith('.html'):
                p = os.path.join(dp, f)
                with open(p, encoding='utf-8', newline='') as fh:
                    s = fh.read()
                if RETIRED not in s:
                    yield p, s


def sub_para(s, heading, body):
    """Replace the first <p> after an <h2>heading</h2>, keeping the <p> tag."""
    rx = re.compile(r'(<h2[^>]*>' + re.escape(heading) + r'</h2>\s*<p[^>]*>)(?:(?!</p>).)*(</p>)', re.S)
    m = rx.search(s)
    assert m, heading
    return s[:m.start()] + m.group(1) + body + m.group(2) + s[m.end():]


def fix_index(s):
    s = re.sub(r'const SEARCH_INDEX = \[\r?\n.*?\r?\n\];', lambda m: SEARCH_INDEX, s, count=1, flags=re.S)
    s = sub_para(s, 'About QuantMedia', HOME_ABOUT)
    s = sub_para(s, 'What We Research', HOME_RESEARCH)
    s = sub_para(s, 'Platform Tools', HOME_TOOLS)
    return s


def fix_about(s):
    s = s.replace('<span class="profile-tag">11 research papers</span>',
                  '<span class="profile-tag">5 research notes</span>')
    s = re.sub(r'\r?\n[ \t]*<div class="profile-tab">Infrastructure</div>', '', s)
    s = s.replace('<h2>Lab Overview</h2>', '<h2>Overview</h2>')
    s = s.replace('<span class="toc-num">01</span>Lab Overview', '<span class="toc-num">01</span>Overview')
    rx = re.compile(r'(<div class="section-header" id="overview"><h2>Overview</h2></div>\s*<div class="article-card">)(.*?)(</div>)', re.S)
    m = rx.search(s)
    assert m, 'overview card'
    s = s[:m.start()] + m.group(1) + ABOUT_OVERVIEW + m.group(3) + s[m.end():]
    a = s.index('<div class="research-grid">')
    b = s.index('<div class="section-header" id="timeline">')
    s = s[:a] + ABOUT_CARDS + s[b:]
    s = s.replace('all 11 research papers', 'all five research notes')
    s = s.replace('Research papers</a></span><span class="skill-pct">11</span>',
                  'Research notes</a></span><span class="skill-pct">5</span>')
    s = s.replace('<span class="skill-name">Signals scored each close</span><span class="skill-pct">180</span>',
                  '<span class="skill-name">Signal universe (names)</span><span class="skill-pct">180</span>')
    # The timeline's "eleven papers" is history and stays; say what happened next.
    if 'were retired' not in s:
        s = s.replace('Each carries primary references and an explicit limitations section.',
                      'Each carries primary references and an explicit limitations section. Six were '
                      'retired in September 2026 when the site narrowed to verified methods; five remain.')
    return s


RETIRED_PAPERS = re.compile(r'paper-(?:alternative|bist|genetic|gpu|hf-|sovereign)')


def fix_papers(s):
    s = s.replace('<div class="hero-stat-val">11</div><div class="hero-stat-label">Papers</div>',
                  '<div class="hero-stat-val">5</div><div class="hero-stat-label">Research notes</div>')
    s = s.replace('<span class="stack-key">Papers</span><span class="stack-val">11</span>',
                  '<span class="stack-key">Research notes</span><span class="stack-val">5</span>')

    # The ItemList schema still enumerated all eleven papers, six of them retired.
    def trim(m):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            return m.group(0)
        changed = False
        nodes = d.get('@graph') if isinstance(d.get('@graph'), list) else [d]
        for node in nodes:
            items = node.get('itemListElement')
            if isinstance(items, list):
                keep = [i for i in items if not RETIRED_PAPERS.search(str(i.get('url', '')))]
                if len(keep) != len(items):
                    for n, i in enumerate(keep, 1):
                        i['position'] = n
                    node['itemListElement'] = keep
                    if 'numberOfItems' in node:
                        node['numberOfItems'] = len(keep)
                    changed = True
            if node.get('@type') == 'CollectionPage' and str(node.get('description', '')).startswith('11 open-access'):
                node['description'] = ('Five research notes on market microstructure, portfolio construction, '
                                       'backtest statistics and execution costs, each with primary references '
                                       'and a stated limitations section.')
                changed = True
        if not changed:
            return m.group(0)
        return '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False) + '</script>'
    return re.sub(r'<script type="application/ld\+json">(.*?)</script>', trim, s, flags=re.S)


def fix_methodology(s):
    return re.sub(r'References to exchanges, data centers \(Equinix NY4/NY5\), or specific technologies '
                  r'describe the author\'s research interests and do not imply any commercial relationship\.',
                  'References to exchanges or specific technologies describe research subjects and do not '
                  'imply any commercial relationship.', s)


def fix_signals(s):
    if 'is skipped' not in s:
        s = s.replace('spanning every major sector.', 'spanning every major sector.' + SKIP_NOTE)
    return s


def fix_footer(s):
    s = re.sub(r'(<div class="(?:ft-desc|footer-desc)">)(?:(?!</div>).)*(</div>)',
               lambda m: m.group(1) + FOOTER_DESC + m.group(2), s, flags=re.S)
    if '>Editorial policy<' in s:
        s = re.sub(r'\r?\n[ \t]*<a href="/editorial-policy\.html">Editorial Policy</a>', '', s)
    s = re.sub(r'\r?\n[ \t]*<span class="fbadge">NASDAQ / NYSE Arca</span>', '', s)
    return s


SPECIAL = {
    'index.html': fix_index,
    'about.html': fix_about,
    'papers.html': fix_papers,
    'methodology.html': fix_methodology,
    'quantum-signals.html': fix_signals,
}


def main():
    changed = 0
    for p, s in live_pages():
        rel = os.path.relpath(p, ROOT).replace('\\', '/')
        s2 = fix_footer(s)
        if rel in SPECIAL:
            s2 = SPECIAL[rel](s2)
        if s2 != s:
            with open(p, 'w', encoding='utf-8', newline='') as fh:
                fh.write(s2)
            changed += 1
            print(f'  {rel}')
    print(f'{changed} files changed')


if __name__ == '__main__':
    main()
