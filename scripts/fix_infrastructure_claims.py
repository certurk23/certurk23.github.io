"""Stop two pages presenting fabricated live readings as measurements.

WHAT WAS THERE
--------------
research.html shipped a dashboard of VPIN values for named real securities:

    VPIN (AAPL) 0.312  OBI Score -0.041  Hurst (SPY) 0.587
    Latency P99 740 ns  Toxicity MODERATE
    AAPL 0.312 / NVDA 0.389 / SPY 0.198 / QQQ 0.224 / MSFT 0.271
    "VPIN on NASDAQ Composite crosses 0.31 threshold - elevated toxicity
     regime detected in AAPL, NVDA order flow"

VPIN cannot be computed from end-of-day bars. It needs trade-level data, which
this site does not have and says it does not have. So these are invented market
readings attributed to real, tradeable securities - and the page contradicted
three things at once: /editorial-policy.html, the VPIN paper, and a paragraph
further down the same page which now correctly states "QuantMedia has not
replicated it."

infrastructure.html shipped a panel headed "System Status - NY4 / LIVE" with
P99 740 ns, P50 720 ns, a NIC drop rate and a TLB miss rate. The page describes
itself as "a reference architecture", which is legitimate and interesting; a
LIVE status readout from co-located hardware is not, because there is none.

WHAT REPLACES IT
----------------
research.html gets the numbers QuantMedia genuinely produces - the daily scan
and the two published indices - plus the synthetic-data VPIN demonstration
whose figures are reproducible from the shipped package.

infrastructure.html keeps every technical section. The status panel becomes a
clearly-labelled DESIGN BUDGET, and the page states in its own first screen
that nothing on it is a measurement of hardware operated by QuantMedia.

Idempotent.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
RESEARCH_STRIP_OLD = '''    <div class="market-strip">
      <div class="mkt-cell"><div class="label">VPIN (AAPL)</div><div class="val">0.312</div><div class="chg up">▲ +0.024</div></div>
      <div class="mkt-cell"><div class="label">OBI Score</div><div class="val">−0.041</div><div class="chg dn">▼ −0.007</div></div>
      <div class="mkt-cell"><div class="label">Hurst (SPY)</div><div class="val">0.587</div><div class="chg up">▲ +0.012</div></div>
      <div class="mkt-cell"><div class="label">Latency P99</div><div class="val">740 ns</div><div class="chg up">▼ −18 ns</div></div>
      <div class="mkt-cell"><div class="label">Toxicity</div><div class="val" style="color:var(--gold)">MODERATE</div><div class="chg" style="color:var(--gold)">● Active</div></div>
    </div>'''

RESEARCH_STRIP_NEW = '''    <div class="qm-note" style="margin:0 0 22px">
      <strong>What this page is.</strong> A written review of the microstructure
      literature QuantMedia works from &mdash; order-flow toxicity, adverse
      selection and venue fragmentation. It reports no live measurement of any
      security. VPIN requires trade-and-quote data; this site collects
      end-of-day bars, as the
      <a href="/editorial-policy.html">editorial policy</a> states. The metrics
      QuantMedia does compute daily are the
      <a href="/indices/signal-breadth.html">Signal Breadth Index</a> and
      <a href="/indices/sector-confluence.html">Sector Confluence Index</a>.
    </div>'''

RESEARCH_TABLE_OLD = '''      <div class="widget-header"><span class="widget-title">VPIN Snapshot</span></div>
      <table class="data-table">
        <thead><tr><th>Symbol</th><th>VPIN</th><th>Δ</th></tr></thead>
        <tbody>
          <tr><td class="tname">AAPL</td><td>0.312</td><td class="up">+0.024</td></tr>
          <tr><td class="tname">NVDA</td><td>0.389</td><td class="dn">−0.011</td></tr>
          <tr><td class="tname">SPY</td><td>0.198</td><td class="up">+0.003</td></tr>
          <tr><td class="tname">QQQ</td><td>0.224</td><td class="up">+0.008</td></tr>
          <tr><td class="tname">MSFT</td><td>0.271</td><td class="dn">−0.005</td></tr>
        </tbody>
      </table>'''

RESEARCH_TABLE_NEW = '''      <div class="widget-header"><span class="widget-title">VPIN, measured</span></div>
      <table class="data-table">
        <thead><tr><th>Synthetic tape</th><th>Mean VPIN</th></tr></thead>
        <tbody>
          <tr><td class="tname">Balanced segment</td><td>0.3292</td></tr>
          <tr><td class="tname">Informed segment</td><td>0.6376</td></tr>
          <tr><td class="tname">Ratio</td><td>1.94&times;</td></tr>
          <tr><td class="tname">BVC vs tick rule</td><td>0.4410 / 0.1779</td></tr>
        </tbody>
      </table>
      <p style="font-size:11.5px;color:var(--dim);line-height:1.7;padding:10px 14px;margin:0">
        Output of the <a href="/reproducibility.html">published implementation</a>
        on a synthetic tape with a planted informed episode, from a fixed seed.
        Synthetic because the ground truth is knowable; not a reading on any real
        security.
      </p>'''

RESEARCH_BANNER_OLD = ('<span class="breaking-text">VPIN on NASDAQ Composite crosses 0.31 '
                       'threshold — elevated toxicity regime detected in AAPL, NVDA order '
                       'flow</span>')
RESEARCH_BANNER_NEW = ('<span class="breaking-text">Order-flow toxicity, adverse selection '
                       'and venue fragmentation &mdash; methodology, published code and '
                       'stated limitations</span>')

RESEARCH_LABEL_OLD = '<span class="breaking-label">Research Note</span>'
RESEARCH_LABEL_NEW = '<span class="breaking-label">Research</span>'

RESEARCH_REGIME_OLD = '''        <span class="stack-key">Toxicity Regime</span>
        <span class="stack-val" style="color:var(--gold)">MODERATE</span>'''
RESEARCH_REGIME_NEW = '''        <span class="stack-key">Live toxicity index</span>
        <span class="stack-val" style="color:var(--dim)">not published</span>'''

# ---------------------------------------------------------------------------
INFRA_STATUS_OLD = '''      <div class="widget-header">
        <span class="widget-title">System Status</span>
        <span style="font-size:10px;color:var(--dim);font-family:'Barlow Condensed',sans-serif">NY4 / LIVE</span>
      </div>
      <div class="status-grid">
        <div class="status-cell"><div class="sc-label">Latency P99</div><div class="sc-val up">740 ns</div><div class="sc-sub">Within budget</div></div>
        <div class="status-cell"><div class="sc-label">Latency P50</div><div class="sc-val up">720 ns</div><div class="sc-sub">Target &lt;800 ns</div></div>
        <div class="status-cell"><div class="sc-label">NIC Queue</div><div class="sc-val up">0.0%</div><div class="sc-sub">Drop rate</div></div>
        <div class="status-cell"><div class="sc-label">TLB Misses</div><div class="sc-val up">0.04%</div><div class="sc-sub">2MB hugepages</div></div>
      </div>'''

INFRA_STATUS_NEW = '''      <div class="widget-header">
        <span class="widget-title">Design Budget</span>
        <span style="font-size:10px;color:var(--dim);font-family:'Barlow Condensed',sans-serif">TARGET, NOT MEASURED</span>
      </div>
      <div class="status-grid">
        <div class="status-cell"><div class="sc-label">Latency P99</div><div class="sc-val">&lt;800 ns</div><div class="sc-sub">Design target</div></div>
        <div class="status-cell"><div class="sc-label">DMA stage</div><div class="sc-val">120 ns</div><div class="sc-sub">Budget allocation</div></div>
        <div class="status-cell"><div class="sc-label">Cross-NUMA</div><div class="sc-val">~80 ns</div><div class="sc-sub">Published penalty</div></div>
        <div class="status-cell"><div class="sc-label">TLB miss</div><div class="sc-val">~100 ns</div><div class="sc-sub">Page-table walk</div></div>
      </div>
      <p style="font-size:11px;color:var(--dim);line-height:1.65;padding:10px 14px;margin:0;border-top:1px solid var(--border)">
        Budget allocations for the architecture described here, drawn from
        vendor and published figures. QuantMedia operates no co-located
        hardware and has measured none of this.
      </p>'''

INFRA_DESC_OLD = ('<div class="page-desc">A reference architecture for sub-microsecond '
                  'order flow analysis:')
INFRA_DESC_NEW = ('<div class="page-desc"><strong>A design study, not a system in '
                  'operation.</strong> QuantMedia runs no co-located hardware, holds no '
                  'exchange feed and has taken no latency measurement; every figure below '
                  'is a design target or a published vendor number, and the site\'s actual '
                  'data pipeline is described in the '
                  '<a href="/editorial-policy.html" style="color:var(--accent)">editorial '
                  'policy</a>. With that said &mdash; a reference architecture for '
                  'sub-microsecond order flow analysis:')

EDITS = [
    ('research.html', RESEARCH_STRIP_OLD, RESEARCH_STRIP_NEW),
    ('research.html', RESEARCH_TABLE_OLD, RESEARCH_TABLE_NEW),
    ('research.html', RESEARCH_BANNER_OLD, RESEARCH_BANNER_NEW),
    ('research.html', RESEARCH_LABEL_OLD, RESEARCH_LABEL_NEW),
    ('research.html', RESEARCH_REGIME_OLD, RESEARCH_REGIME_NEW),
    ('infrastructure.html', INFRA_STATUS_OLD, INFRA_STATUS_NEW),
    ('infrastructure.html', INFRA_DESC_OLD, INFRA_DESC_NEW),
]

# No page may present these as current measurements again.
BANNED = [
    ('research.html', 'VPIN (AAPL)'),
    ('research.html', 'toxicity regime detected'),
    ('research.html', '>0.312<'),
    ('research.html', '>0.389<'),
    ('infrastructure.html', 'NY4 / LIVE'),
]


# A second "Live Metrics" panel and a scrolling ticker carried the same
# invented numbers. "UPDATED 14:32:07" on a hardcoded value is the worst of it:
# a timestamp is a claim of recency, and this one was frozen in the markup.
RESEARCH_LIVE_OLD = """        <span class="widget-title">Live Metrics</span>
        <span style="font-size:10px;color:var(--dim);font-family:'Barlow Condensed',sans-serif">UPDATED 14:32:07</span>
      </div>
      <div class="status-grid">
        <div class="status-cell"><div class="sc-label">VPIN</div><div class="sc-val up">0.312</div><div class="sc-sub">AAPL / ▲ +0.024</div></div>
        <div class="status-cell"><div class="sc-label">OBI Score</div><div class="sc-val dn">−0.041</div><div class="sc-sub">▼ −0.007</div></div>
        <div class="status-cell"><div class="sc-label">Hurst</div><div class="sc-val" style="color:var(--blue)">0.587</div><div class="sc-sub">SPY / Persistent</div></div>
        <div class="status-cell"><div class="sc-label">Latency P99</div><div class="sc-val">740 ns</div><div class="sc-sub">NY4 co-lo</div></div>
      </div>"""

RESEARCH_LIVE_NEW = """        <span class="widget-title">What QuantMedia measures</span>
        <span style="font-size:10px;color:var(--dim);font-family:'Barlow Condensed',sans-serif">DAILY, POST-CLOSE</span>
      </div>
      <div class="status-grid">
        <div class="status-cell"><div class="sc-label">Universe</div><div class="sc-val">180</div><div class="sc-sub">Liquid US equities</div></div>
        <div class="status-cell"><div class="sc-label">Signals</div><div class="sc-val">30</div><div class="sc-sub">Per stock, per close</div></div>
        <div class="status-cell"><div class="sc-label">Threshold</div><div class="sc-val">22/30</div><div class="sc-sub">BUY qualification</div></div>
        <div class="status-cell"><div class="sc-label">Published</div><div class="sc-val">2</div><div class="sc-sub">Daily indices</div></div>
      </div>"""

RESEARCH_TICKS_OLD = """const ticks=[
  {name:'VPIN AAPL',val:'0.312',chg:'+0.024',up:true},
  {name:'OBI SPY',val:'−0.041',chg:'−0.007',up:false},
  {name:'HURST SPY',val:'0.587',chg:'+0.012',up:true},
  {name:'LATENCY',val:'740 ns',chg:'−18 ns',up:true},
  {name:'NVDA VPIN',val:'0.389',chg:'−0.011',up:false},
  {name:'QQQ VPIN',val:'0.224',chg:'+0.008',up:true},
  {name:'MSFT VPIN',val:'0.271',chg:'−0.005',up:false},
  {name:'TOXICITY',val:'MODERATE',chg:'●',up:true},
];"""

RESEARCH_TICKS_NEW = """/* The ticker previously scrolled invented VPIN readings for AAPL, NVDA, SPY,
   QQQ and MSFT. Those cannot be computed from end-of-day bars. It now carries
   the engine's published, checkable parameters instead. */
const ticks=[
  {name:'UNIVERSE',val:'180',chg:'US equities',up:true},
  {name:'SIGNALS',val:'30',chg:'per stock',up:true},
  {name:'THRESHOLD',val:'22/30',chg:'BUY',up:true},
  {name:'CADENCE',val:'POST-CLOSE',chg:'Mon-Fri',up:true},
  {name:'METHODOLOGY',val:'v2.0',chg:'published',up:true},
  {name:'TESTS',val:'28',chg:'research code',up:true},
];"""

EDITS.append(('research.html', RESEARCH_LIVE_OLD, RESEARCH_LIVE_NEW))
EDITS.append(('research.html', RESEARCH_TICKS_OLD, RESEARCH_TICKS_NEW))
BANNED.append(('research.html', 'UPDATED 14:32:07'))
BANNED.append(('research.html', 'NY4 co-lo'))
BANNED.append(('research.html', "0.271"))



def main():
    changed = missing = 0
    for rel, old, new in EDITS:
        p = ROOT / rel
        s = p.read_text(encoding='utf-8')
        if new in s:
            print(f'  [  -] {rel}: already applied')
            continue
        if old not in s:
            print(f'  [MISS] {rel}: {" ".join(old.split())[:66]}...')
            missing += 1
            continue
        p.write_text(s.replace(old, new, 1), encoding='utf-8')
        changed += 1
        print(f'  [chg] {rel}: {" ".join(old.split())[:62]}...')

    print(f'\n{changed} applied, {missing} not matched')

    fail = False
    for rel, needle in BANNED:
        if needle in (ROOT / rel).read_text(encoding='utf-8'):
            print(f'  STILL PRESENT  {rel}: {needle!r}')
            fail = True
    for rel in ('research.html', 'infrastructure.html'):
        s = (ROOT / rel).read_text(encoding='utf-8')
        if s.count('<div') != s.count('</div>'):
            print(f'  UNBALANCED div in {rel}: {s.count("<div")}/{s.count("</div>")}')
            fail = True
    print('verified: no fabricated live reading remains, div tags balanced'
          if not fail else 'FAILED')
    sys.exit(1 if (fail or missing) else 0)


if __name__ == '__main__':
    main()
