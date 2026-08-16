"""Stop the web font blocking first paint, and make authorship consistent.

PERFORMANCE
-----------
Measured before this ran: 34 of 37 pages loaded the Google Fonts stylesheet
with a plain <link rel="stylesheet">. That is a render-blocking request to a
third-party origin - the browser will not paint until it resolves DNS,
connects, fetches the CSS, and then fetches the font files it names. Two pages
already used the preload+onload pattern, so the fix is to apply the pattern the
codebase had already settled on, not to invent one.

Three different font URLs were also in use, requesting 12, 10 and 6 font files
respectively. They are unified on one request for 10 files. Barlow 300 was
requested by 34 pages and used by none; `font-weight:300` appears nowhere in
any stylesheet on the site.

Deliberately NOT done: switching MathJax from tex-mml-chtml to tex-chtml. I
measured both - 1,145 KB against 1,133 KB - so the saving is 1% and the risk of
breaking MathML rendering is not worth it. It is already async and therefore
not render-blocking.

IDENTITY
--------
<meta name="author"> said "QuantMedia" (an organisation) on every page. The
research now has a named human author, and the meta tag should agree with the
byline and the schema rather than contradicting them.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

FONT_HREF = ('https://fonts.googleapis.com/css2?family=Barlow:ital,wght@0,400;0,500;0,600;0,700;1,400'
             '&family=Barlow+Condensed:wght@400;600;700'
             '&family=JetBrains+Mono:wght@400;500&display=swap')

NONBLOCKING = (f'<link rel="preload" as="style" href="{FONT_HREF}" '
               f'onload="this.onload=null;this.rel=\'stylesheet\'">\n'
               f'<noscript><link rel="stylesheet" href="{FONT_HREF}"></noscript>')

# Any plain stylesheet link to Google Fonts, whatever families it names.
BLOCKING_RE = re.compile(
    r'<link\s+href="https://fonts\.googleapis\.com/css2\?[^"]*"\s+rel="stylesheet"\s*/?>')
# An already-converted preload, so the URL can still be normalised.
# Leading indentation and the trailing newline are part of the match: without
# them the strip-and-re-add cycle leaves a stray blank line behind on every
# run, which accumulates and makes the script non-idempotent. Caught by hashing
# the tree across three consecutive runs rather than by reading the code.
PRELOAD_RE = re.compile(
    r'[ \t]*<link rel="preload" as="style" href="https://fonts\.googleapis\.com/css2\?[^"]*"'
    r' onload="[^"]*">[ \t]*\n?'
    r'(?:[ \t]*<noscript><link rel="stylesheet"'
    r' href="https://fonts\.googleapis\.com/css2\?[^"]*"></noscript>[ \t]*\n?)?')
NOSCRIPT_RE = re.compile(
    r'[ \t]*<noscript><link rel="stylesheet" '
    r'href="https://fonts\.googleapis\.com/css2\?[^"]*"></noscript>[ \t]*\n?')

AUTHOR = 'Cemil Ertürk'

stats = {'font_unblocked': 0, 'font_normalised': 0, 'meta_author': 0}

for f in sorted(ROOT.rglob('*.html')):
    if any(p in ('.git', 'node_modules') for p in f.parts):
        continue
    src = out = f.read_text(encoding='utf-8')

    # Two pages carried BOTH a preload and a blocking link. Converting the
    # blocking one in isolation left a duplicate preload behind, so strip every
    # font link first and re-add exactly one. Collapse, then emit.
    if BLOCKING_RE.search(out) or PRELOAD_RE.search(out):
        had_blocking = bool(BLOCKING_RE.search(out))
        before = out
        out = BLOCKING_RE.sub('', out)
        out = PRELOAD_RE.sub('', out)
        out = NOSCRIPT_RE.sub('', out)
        out = out.replace('</head>', NONBLOCKING + '\n</head>', 1)
        if had_blocking:
            stats['font_unblocked'] += 1
        elif out != before:
            stats['font_normalised'] += 1

    before = out
    out = re.sub(r'<meta name="author" content="[^"]*">',
                 f'<meta name="author" content="{AUTHOR}">', out)
    if out != before:
        stats['meta_author'] += 1

    if out != src:
        f.write_text(out, encoding='utf-8')

for k, v in stats.items():
    print(f'  {k:18} {v}')

# --- verify -----------------------------------------------------------------
blocking, urls, authors = [], set(), set()
for f in ROOT.rglob('*.html'):
    if '.git' in f.parts:
        continue
    h = f.read_text(encoding='utf-8')
    if BLOCKING_RE.search(h):
        blocking.append(f.name)
    urls.update(re.findall(r'https://fonts\.googleapis\.com/css2\?[^"]*', h))
    authors.update(re.findall(r'<meta name="author" content="([^"]*)">', h))

print(f'\n  render-blocking font links remaining : {len(blocking)} {blocking[:5]}')
print(f'  distinct font URLs in use            : {len(urls)}')
print(f'  distinct meta author values          : {sorted(authors)}')
sys.exit(1 if blocking or len(urls) > 1 or len(authors) > 1 else 0)
