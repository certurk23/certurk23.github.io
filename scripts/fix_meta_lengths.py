#!/usr/bin/env python3
"""Bring hand-maintained pages' meta descriptions under 160 characters and
keep the og:/twitter: copies identical to the primary description.

Generated pages get theirs from build_pages.py (edited alongside this).
Idempotent. Fails loudly if any target text is over length.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DESC = {
    'index.html': ('Verified VPIN, Hierarchical Risk Parity and Probabilistic Sharpe '
                   'Ratio code: runnable Python, synthetic ground truth, dated defect '
                   'reports. Free.'),
    'quantum-signals.html': ('180 liquid US equities scored against 30 technical signals '
                             'after every close. 22 or more bullish signals flags a BUY. '
                             'Free, rules-based, research use only.'),
    'contact.html': ('Contact QuantMedia for research collaboration, corrections, or '
                     'feedback. Independent quant research covering market '
                     'microstructure and algorithmic trading.'),
}

META = [
    re.compile(r'(<meta name="description" content=")[^"]*(")'),
    re.compile(r'(<meta property="og:description" content=")[^"]*(")'),
    re.compile(r'(<meta name="twitter:description" content=")[^"]*(")'),
]


def main():
    bad = {k: len(v) for k, v in DESC.items() if not 70 <= len(v) <= 155}
    if bad:
        sys.exit(f'description length out of range: {bad}')
    for name, desc in DESC.items():
        p = os.path.join(ROOT, name)
        with open(p, encoding='utf-8', newline='') as fh:
            s = fh.read()
        s2 = s
        for rx in META:
            s2 = rx.sub(lambda m: m.group(1) + desc + m.group(2), s2, count=1)
        if s2 != s:
            with open(p, 'w', encoding='utf-8', newline='') as fh:
                fh.write(s2)
            print(f'  {name}: description set ({len(desc)} chars)')
        else:
            print(f'  {name}: already current')

    # pivot_homepage.py rewrites the homepage description when re-run; keep
    # it in step so a re-run cannot restore the 202-character original.
    ph = os.path.join(ROOT, 'scripts', 'pivot_homepage.py')
    with open(ph, encoding='utf-8', newline='') as fh:
        src = fh.read()
    src2 = re.sub(r'(<meta name="description" content=")[^"]*(">)',
                  lambda m: m.group(1) + DESC['index.html'] + m.group(2), src, count=1)
    if src2 != src:
        with open(ph, 'w', encoding='utf-8', newline='') as fh:
            fh.write(src2)
        print('  scripts/pivot_homepage.py: description synced')


if __name__ == '__main__':
    main()
