"""Pivot, step 3: make the pipeline, validator and generator match the site.

Retired pages lose their injection anchors. Without these edits the nightly run
would log a stage error for every missing anchor (turning every run PARTIAL),
the corruption gate would fail on pages that no longer exist as products, and
build_pages would keep emitting the report pages without their verification
record. Everything here is guarded by exact-string matches and asserts, so a
drifted upstream fails loudly instead of half-applying.

Idempotent.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
done = []


def patch(rel, old, new, label):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    if new in s:
        done.append(f'  [  -] {label}')
        return
    assert old in s, f'{rel}: anchor not found for {label!r}'
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
    done.append(f'  [chg] {label}')


# ---------------------------------------------------------------------------
# daily_update.py: renderers tolerate a retired page (anchor absent -> skip,
# quietly, as a print rather than a stage_error).
# ---------------------------------------------------------------------------
patch('scripts/daily_update.py',
      'def inject(html, marker, inner_html):\n    """Replace content between QM:MARKER comment anchors."""',
      'def has_anchor(html, marker):\n'
      '    return f"<!-- QM:{marker}:START -->" in html\n\n\n'
      'def inject(html, marker, inner_html):\n    """Replace content between QM:MARKER comment anchors."""',
      'daily_update: has_anchor helper')

patch('scripts/daily_update.py',
      "        html = read_file('news.html')\n        html = inject(html, 'NEWS_SNAP',",
      "        html = read_file('news.html')\n"
      "        if not has_anchor(html, 'NEWS_SNAP'):\n"
      "            print('  news.html retired - no render')\n"
      "            return\n"
      "        html = inject(html, 'NEWS_SNAP',",
      'daily_update: news render skips a retired page')

patch('scripts/daily_update.py',
      "        page = read_file(\"index.html\")\n        page = inject(page, \"HOME_BAR\", bar_html)\n        page = inject(page, \"HOME_SESSION\", block)",
      "        page = read_file(\"index.html\")\n"
      "        if has_anchor(page, \"HOME_BAR\"):\n"
      "            page = inject(page, \"HOME_BAR\", bar_html)\n"
      "        page = inject(page, \"HOME_SESSION\", block)",
      'daily_update: homepage market bar optional')

# markets.html render: find the function and guard it
p = ROOT / 'scripts' / 'daily_update.py'
s = p.read_text(encoding='utf-8')
# Guard the one place markets.html is read for rendering, whatever the
# enclosing function's signature turns out to be.
if 'markets.html retired' not in s:
    line = re.search(r"^([ \t]+)html = read_file\('markets\.html'\)[ \t]*$", s, re.M)
    assert line, "read_file('markets.html') line not found"
    ind = line.group(1)
    guarded = (line.group(0) + "\n"
               + ind + "if not has_anchor(html, 'FOREX'):\n"
               + ind + "    print('  markets.html retired - no render')\n"
               + ind + "    return")
    s = s[:line.start()] + guarded + s[line.end():]
    p.write_text(s, encoding='utf-8')
    done.append('  [chg] daily_update: markets render skips a retired page')
else:
    done.append('  [  -] daily_update: markets render skips a retired page')

patch('scripts/daily_update.py',
      "DATA_DRIVEN = ('/quantum-signals.html', '/markets.html', '/news.html',",
      "DATA_DRIVEN = ('/quantum-signals.html',",
      'daily_update: DATA_DRIVEN drops retired pages')

# ---------------------------------------------------------------------------
# qm_config.py: retired pages are no longer required to be large.
# ---------------------------------------------------------------------------
patch('scripts/qm_config.py',
      "    'markets.html':          25_000,\n    'news.html':             25_000,\n    'stocks.html':           25_000,\n",
      "    'reports/index.html':    12_000,\n",
      'qm_config: REQUIRED_FILES swaps retired pages for the reports hub')

# ---------------------------------------------------------------------------
# validate_site.py: retired pages are skipped by every content check, and the
# blank-data check no longer demands anchors on pages that have none.
# ---------------------------------------------------------------------------
patch('scripts/validate_site.py',
      "def html_files():\n    \"\"\"Every published page, discovered rather than listed.",
      "RETIRED_MARK = '<!-- qm-retired -->'\n\n\n"
      "def is_retired(rel):\n"
      "    \"\"\"A retired page keeps its file (noindex + refresh to a live page) but is\n"
      "    no longer a product. Content checks skip it; the sitemap check still\n"
      "    guarantees it is not listed.\"\"\"\n"
      "    try:\n"
      "        return RETIRED_MARK in read(rel)\n"
      "    except Exception:\n"
      "        return False\n\n\n"
      "def html_files():\n    \"\"\"Every published page, discovered rather than listed.",
      'validate_site: is_retired helper')

patch('scripts/validate_site.py',
      "            rel = f if rel_dir == '.' else os.path.join(rel_dir, f).replace(os.sep, '/')\n            out.append(rel)\n    return sorted(out)",
      "            rel = f if rel_dir == '.' else os.path.join(rel_dir, f).replace(os.sep, '/')\n"
      "            if is_retired(rel):\n                continue\n"
      "            out.append(rel)\n    return sorted(out)",
      'validate_site: html_files excludes retired pages')

patch('scripts/validate_site.py',
      "def check_blank_data_regression():\n    for name in ('markets.html', 'news.html'):\n        path = os.path.join(ROOT, name)\n        if not os.path.exists(path):\n            continue",
      "def check_blank_data_regression():\n    for name in ('markets.html', 'news.html'):\n        path = os.path.join(ROOT, name)\n        if not os.path.exists(path) or is_retired(name):\n            continue",
      'validate_site: blank-data check skips retired pages')

# The consistency check reads quantum-signals.html and index.html directly;
# both remain live, nothing to change. The placeholder check iterates
# html_files(), which now excludes retired pages.

# ---------------------------------------------------------------------------
# build_pages.py: compose the verification record into the report pages, and
# retitle them so the URL keeps working while the page says what it now is.
# ---------------------------------------------------------------------------
patch('scripts/build_pages.py',
      'import page_content_examples as PCE',
      'import page_content_examples as PCE\nimport page_content_reports as PCR   # verification layer, composed below',
      'build_pages: import verification fragments')

patch('scripts/build_pages.py',
      "for slug, title, description, body in [\n    ('index.html',",
      "# Compose: verdict + dated record on top, worked example in the middle,\n"
      "# defects / limitations / reproduce at the end. Same URLs as before.\n"
      "PCE.INDEX_BODY = PCR.INDEX_BODY\n"
      "PCE.VPIN_BODY = PCR.VPIN_VERDICT + PCE.VPIN_BODY + PCR.VPIN_VERIFICATION\n"
      "PCE.HRP_BODY = PCR.HRP_VERDICT + PCE.HRP_BODY + PCR.HRP_VERIFICATION\n"
      "PCE.PSR_BODY = PCR.PSR_VERDICT + PCE.PSR_BODY + PCR.PSR_VERIFICATION\n\n"
      "for slug, title, description, body in [\n    ('index.html',",
      'build_pages: compose verification into report bodies')

p = ROOT / 'scripts' / 'build_pages.py'
s = p.read_text(encoding='utf-8')
RETITLE = [
    ("'Free Quantitative Finance Worked Examples'", "'Verification Reports: Quant Finance Code Checked Against Ground Truth'"),
    ("'VPIN Example: One Tape, Two Classifiers'", "'VPIN Verification Report: One Tape, Two Classifiers, One Defect Fixed'"),
    ("'HRP Example: Compare Six Portfolio Allocators'", "'HRP Verification Report: Six Allocators, Two Defects Fixed'"),
    ("'Probabilistic Sharpe Ratio: A Worked Calculation'", "'PSR Verification Report: A Published Example, Corrected'"),
]
changed = False
for old, new in RETITLE:
    if old in s:
        s = s.replace(old, new, 1)
        changed = True
if changed:
    p.write_text(s, encoding='utf-8')
    done.append('  [chg] build_pages: report titles say verification')
else:
    done.append('  [  -] build_pages: report titles say verification')

print('\n'.join(done))
