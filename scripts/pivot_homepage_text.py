#!/usr/bin/env python3
"""Homepage, step two: remove every third-party and widget block so the page
is QuantMedia's own writing, not an aggregator.

AdSense rejected the site twice for "low value content" (last on 6 Sep 2026,
resubmission blocked until 20 Sep). The homepage a reviewer lands on was half
syndicated material: a Reuters/CNBC headline grid with publisher images, a
TradingView ticker tape, a "breaking" bar, top-movers and release-schedule
widgets and a market-snapshot sidebar. AdSense's policy names "content
aggregated from other sources" as the first example of low value.

What goes: breaking bar, TradingView ticker, Market News grid, Data Panels
(movers + release schedule), Market Snapshot sidebar widget, and the
JavaScript that fed them (barRows/loadMarketBar/loadSnapshot/loadMovers/
showMovers/init, the whole news feed, the TradingView loader). Leaving the JS
behind would recreate the loadHero console error we removed on 6 Sep.

What stays: hero, three start-here cards, About / What We Research / Platform
Tools, the server-rendered session snapshot (QM:HOME_SESSION), "Verified
here" and report cards, Research & Analysis cards, newsletter, footer, search.

Idempotent: every cut is guarded by an anchor that vanishes with the cut.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'index.html')


def cut(s, start, end, label, include_end=True):
    """Remove s[start_marker : end_marker(+end)] once; no-op if start is gone."""
    a = s.find(start)
    if a < 0:
        return s, False
    b = s.find(end, a + len(start))
    if b < 0:
        sys.exit(f'{label}: end marker not found')
    b = b + len(end) if include_end else b
    return s[:a] + s[b:], True


def main():
    with open(PATH, encoding='utf-8', newline='') as fh:
        raw = fh.read()
    nl = '\r\n' if '\r\n' in raw else '\n'
    s = raw.replace('\r\n', '\n')
    orig = s
    done = []

    # 1. Breaking bar + TradingView ticker host.
    s, k = cut(s, '<!-- BREAKING ALERT -->', '<span class="breaking-close">&times;</span>\n</div>\n', 'breaking'); done += ['breaking'] * k
    s, k = cut(s, '<!-- TICKER (deferred', 'contain:layout style"></div>\n', 'ticker'); done += ['ticker'] * k

    # 2. Market News grid (third-party headlines and images).
    s, k = cut(s, '<!-- MARKET NEWS -->', '</div><!-- /newsGrid -->\n</div>\n', 'news'); done += ['news'] * k

    # 3. Data panels: top movers + release schedule.
    s, k = cut(s, '  <!-- DATA PANELS -->', '  <!-- CONTENT LAYOUT', 'panels', include_end=False); done += ['panels'] * k

    # 4. Market snapshot sidebar widget (newsletter stays in the aside).
    s, k = cut(s, '      <!-- Market Snapshot -->', '      <!-- Newsletter -->', 'snapshot', include_end=False); done += ['snapshot'] * k

    # 5. JavaScript that fed the removed blocks.
    s, k = cut(s, '/* --- Market data: one snapshot read', 'init();\n', 'js-market'); done += ['js-market'] * k
    s, k = cut(s, '/* ============================================================\n   NEWS FEED', 'loadNews();\n', 'js-news'); done += ['js-news'] * k
    s, k = cut(s, '/* Deferred TradingView ticker', '  }, 2000);\n});\n', 'js-ticker'); done += ['js-ticker'] * k

    # 6. The helper block that only the removed code used.
    s, k = cut(s, "const pct  = v =>", "const now  = () => new Date().toLocaleTimeString('en-US', {hour12:false, hour:'2-digit', minute:'2-digit'});\n", 'js-helpers'); done += ['js-helpers'] * k

    # Self-checks: nothing left references the removed ids or functions.
    js = ' '.join(re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*ld\+json)[^>]*>(.*?)</script>', s, re.S))
    for ident in ('newsGrid', 'snapRows', 'moversPanel', 'tabGain', 'marketBar', 'tickerWrap',
                  'loadNews', 'loadSnapshot', 'loadMovers', 'barRows', 'nAgo(', 'breakingBar'):
        if ident in js:
            sys.exit(f'self-check: {ident} still referenced in inline JS')
    for ident in ('id="newsGrid"', 'id="dataPanels"', 'id="snapRows"', 'id="tickerWrap"', 'id="breakingBar"'):
        if ident in s:
            sys.exit(f'self-check: {ident} still in markup')
    if s.count('<div') != s.count('</div>'):
        sys.exit(f'self-check: div balance {s.count("<div")} vs {s.count("</div>")}')
    for must in ('<!-- QM:HOME_SESSION:START -->', 'id="newsletter"', 'class="story-grid"', 'const SEARCH_INDEX', '<script src="qm-data.js">'):
        if must not in s:
            sys.exit(f'self-check: expected block missing: {must}')

    if s != orig:
        with open(PATH, 'w', encoding='utf-8', newline='') as fh:
            fh.write(s.replace('\n', nl))
    print('index.html:', ', '.join(done) if done else 'no change', f'({len(orig) - len(s):,} chars removed)')


if __name__ == '__main__':
    main()
