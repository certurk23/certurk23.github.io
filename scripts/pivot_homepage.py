"""Pivot, step 2: one hero, one purpose, on the homepage.

After the previous commit the homepage carried TWO heroes: a new
"Understand the method. Run the numbers." section, and below it the old
"US Markets - Daily Quantitative Research & Signal Analysis" hero whose S&P /
Nasdaq / VIX cards are filled only by JavaScript and ship as "-". Two heroes
saying different things is the "unclear purpose" verdict rendered in HTML.

This keeps the new section as the sole hero, removes the old one and the
post-close market bar, leads the "What originates here" block with the
verification reports, and fixes the WebSite schema, whose author was a Person
named "QuantMedia Research".

The QM:HOME_SESSION anchor stays: it is the pipeline's live, server-rendered
demonstration of honest freshness, and the validator cross-checks it against
data/quantum_signals.json. It is relabelled from a market headline to what it
is - a demo of the discipline.

Idempotent.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
p = ROOT / 'index.html'
s = o = p.read_text(encoding='utf-8')

# 1. old hero (with JS-only "-" cards) -> gone. Keep the new start-here section.
m = re.search(r'\n<section class="hero-section">.*?</section>\n', s, re.S)
if m:
    s = s[:m.start()] + '\n' + s[m.end():]

# 2. post-close market bar -> gone (its render is made anchor-tolerant in
#    pivot_pipeline.py, so the daily run stays SUCCESS without it).
m = re.search(r'\n<!-- MARKET BAR -->.*?<!-- QM:HOME_BAR:END --></div>\s*</div>\n', s, re.S)
if m:
    s = s[:m.start()] + '\n' + s[m.end():]

# 3. "What originates here" -> lead with verification, keep the data + code.
OLD_LEDE = re.search(r'<p style="font-size:14\.5px;line-height:1\.8;color:var\(--text3\);margin:0 0 20px;max-width:760px">\s*Most of what you can read.*?</p>', s, re.S)
NEW_LEDE = ('<p style="font-size:14.5px;line-height:1.8;color:var(--text3);margin:0 0 20px;max-width:760px">\n'
            '      QuantMedia verifies quantitative finance code. Each method here has a\n'
            '      runnable implementation, a synthetic input whose correct answer is known\n'
            '      in advance, a dated report of what the code got right and wrong, and\n'
            '      tests that guard the fixes. Two daily metrics are computed from the same\n'
            '      pipeline discipline and published with their freshness state.\n'
            '    </p>')
if OLD_LEDE:
    s = s[:OLD_LEDE.start()] + NEW_LEDE + s[OLD_LEDE.end():]
s = s.replace('>What originates here<', '>Verified here<', 1)

# The first card becomes the reports; the indices keep their two cards.
CARD_OLD = re.search(r'<div>\s*<a href="/reproducibility.html"[^>]*>Reproducible code &rarr;</a>.*?</div>\s*', s, re.S)
CARD_NEW = ('<div>\n'
            '        <a href="/reports/" style="font-family:\'Barlow Condensed\',sans-serif;font-size:16px;font-weight:700;color:var(--green);letter-spacing:.2px">Verification reports &rarr;</a>\n'
            '        <p style="font-size:13px;line-height:1.7;color:var(--text3);margin:6px 0 0">VPIN, HRP and PSR run against known ground truth. Three defects found by testing, all documented and fixed; one command reproduces every published number.</p>\n'
            '      </div>\n      ')
if CARD_OLD:
    s = s[:CARD_OLD.start()] + CARD_NEW + s[CARD_OLD.end():]

# 4. HOME_SESSION label: it is a demo of pipeline honesty, not a headline.
s = s.replace('Latest session snapshot</div>', 'Live pipeline &mdash; today&rsquo;s scan, server-rendered</div>')

# 5. WebSite schema author was a Person called "QuantMedia Research".
s = s.replace('"author":{"@type":"Person","name":"QuantMedia Research","url":"https://quantmedia.io/about.html"}',
              '"author":{"@type":"Person","name":"Cemil Ertürk","url":"https://quantmedia.io/author/cemil-erturk.html"}')

# 6. Title/description: verification-first, still free.
s = re.sub(r'<title>[^<]*</title>',
           '<title>QuantMedia — Verified Quantitative Finance Code, Free</title>', s, count=1)
s = re.sub(r'<meta name="description" content="[^"]*">',
           '<meta name="description" content="Verified implementations of VPIN, Hierarchical Risk Parity and the Probabilistic Sharpe Ratio: runnable code, synthetic ground truth, dated reports of defects found and fixed, and a free PSR calculator.">',
           s, count=1)

if s != o:
    p.write_text(s, encoding='utf-8')

checks = {
    'single hero (start-here only)': s.count('<section class="hero-section">') == 0 and s.count('class="start-here"') == 1,
    'no JS-only market cards': 'id="heroSPY"' not in s,
    'market bar removed': 'QM:HOME_BAR' not in s,
    'HOME_SESSION kept': s.count('QM:HOME_SESSION:START') == 1,
    'reports card present': '/reports/' in s,
    'schema author fixed': '"name":"Cemil Ertürk"' in s,
    'div balance': s.count('<div') == s.count('</div>'),
}
for k, v in checks.items():
    print(f'  [{"ok" if v else "FAIL"}] {k}')
sys.exit(0 if all(checks.values()) else 1)
