#!/usr/bin/env python3
"""Raise small-text contrast to WCAG AA and clear the two axe findings that
every page shared (footer <h4> breaking heading order; in-text links told
apart from prose by colour alone).

Lighthouse 12, 6 Sep 2026, homepage mobile: accessibility 89 with
color-contrast (82 nodes), heading-order and link-in-text-block failing.
Root causes, all in the per-page inline <style>:

  dark  --dimmer #444    on #000/#111/#181818  ->  2.0:1   (footer, badges)
  dark  --muted  #606060 on #111/#181818       ->  3.0:1   (widget captions)
  dark  --red    #e5322d on #111               ->  4.3:1   (negative changes)
  light --dimmer #888888, --muted #999999 on white -> 3.5:1 / 2.8:1
  .ft-col a / .footer-col a  hard-coded #555   ->  2.8:1
  white on --accent #00a651 buttons            ->  3.2:1
  white on --red breaking bar                  ->  4.35:1

Idempotent: run it twice and the second pass changes nothing. Retired
pages (qm-retired marker) are left alone.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', '.github', 'scripts', 'data', 'quantmedia-research', 'node_modules'}
RETIRED = '<!-- qm-retired -->'
LINK_MARK = '/* qm-a11y-links */'
LINK_RULE = (LINK_MARK + 'main p a:not([class]),main li a:not([class]),main dd a:not([class]),'
             'main td a:not([class]),.page-wrap p a:not([class]),.page-wrap li a:not([class]),'
             '.page-wrap dd a:not([class]),.page-wrap td a:not([class]),.qm-crumb a,'
             '.widget a:not([class]),.nl-pad a:not([class])'
             '{text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:2px}\n')
LINK_RX = re.compile(re.escape(LINK_MARK) + r'[^\n]*\n')

# Palette tokens. Ratios quoted against the darkest background each token
# sits on (#181818 for dark widgets, #ebebea for the light footer).
PALETTE = [
    (re.compile(r'--dimmer:\s*#444(?![0-9a-fA-F])'), '--dimmer:#858585'),   # 2.0 -> 4.9
    (re.compile(r'--muted:\s*#606060'), '--muted:#8a8a8a'),                 # 2.8 -> 5.2
    (re.compile(r'--red:\s*#e5322d'), '--red:#f04a45'),                     # 4.3 -> 4.9
    (re.compile(r'--dimmer:\s*#888888'), '--dimmer:#666666'),               # 3.5 -> 4.8
    (re.compile(r'--muted:\s*#999999'), '--muted:#666666'),                 # 2.8 -> 4.8
    (re.compile(r'--ink:\s*#404040'), '--ink:#8a8a8a'),                     # 2.0 -> 5.9 (footer badges)
]

RULES = [
    (re.compile(r'(\.ft-col a\{[^}]*?)color:#555;'), r'\1color:var(--dim);'),
    (re.compile(r'(\.footer-col a\{[^}]*?)color:#555;'), r'\1color:var(--dim);'),
    (re.compile(r'\.ft-col h4\{'), '.ft-col .ft-h{'),
    (re.compile(r'\.footer-col h4\{'), '.footer-col .ft-h{'),
    # White text needs the darker green: #007a3d gives 5.5:1, #00a651 3.2:1.
    (re.compile(r'(\.btn-subscribe\{[^}]*?)background:var\(--(?:accent|green)\);'), r'\1background:#007a3d;'),
    (re.compile(r'(\.nl-btn\{[^}]*?)background:var\(--green\);'), r'\1background:#007a3d;'),
    # Breaking bar: white on #b3221e is 6.6:1; the pill goes darker, not lighter.
    (re.compile(r'(\.breaking-bar\{\s*)background:var\(--red\);'), r'\1background:#b3221e;'),
    (re.compile(r'(\.breaking-pill\{[^}]*?)background:rgba\(255,255,255,\.22\);'), r'\1background:rgba(0,0,0,.3);'),
    (re.compile(r'\.breaking-close\{color:rgba\(255,255,255,\.6\);'), '.breaking-close{color:rgba(255,255,255,.9);'),
]

FOOTER_RX = re.compile(r'<footer\b.*?</footer>', re.S)


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


def fix(s):
    n = 0
    for rx, rep in PALETTE + RULES:
        s, k = rx.subn(rep, s)
        n += k

    # Footer column headings are labels, not document headings.
    def defoot(m):
        nonlocal n
        f = m.group(0)
        n += f.count('<h4>')
        return f.replace('<h4>', '<div class="ft-h">').replace('</h4>', '</div>')
    s = FOOTER_RX.sub(defoot, s)

    if LINK_MARK in s:
        s2 = LINK_RX.sub(LINK_RULE, s, count=1)
        if s2 != s:
            s, n = s2, n + 1
    elif '</style>' in s:
        s = s.replace('</style>', LINK_RULE + '</style>', 1)
        n += 1
    return s, n


def main():
    changed = 0
    for p, s in live_pages():
        s2, n = fix(s)
        if s2 != s:
            with open(p, 'w', encoding='utf-8', newline='') as fh:
                fh.write(s2)
            changed += 1
            print(f'  {os.path.relpath(p, ROOT):55s} {n:3d} edits')
    print(f'{changed} files changed')


if __name__ == '__main__':
    main()
