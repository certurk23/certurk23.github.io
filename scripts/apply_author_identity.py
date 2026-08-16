"""Attach a real, named author to the research, and make each paper citable.

WHY
---
The site published eleven research papers with no human attached to any of
them. Schema said author = Organization "QuantMedia"; the visible byline said
"QuantMedia Research". For quantitative market analysis that reads as an
accountability gap: nobody is answerable for the claims, and there is no
person for a reader, a reviewer or a language model to evaluate.

Everything written here is supplied by the site owner or already verifiable in
this repository. Specifically NOT claimed anywhere: university affiliation,
employer, professional licence, peer review, journal publication, years of
experience, or any prior role. Those would all be inventions.

WHAT IT DOES
------------
1. meta author, visible byline and Article schema all name the same person and
   point at the same author URL. One identity, stated three ways consistently.

2. dateModified is corrected. All eleven papers were materially revised (they
   gained limitations and references) while dateModified still equalled
   datePublished, which is simply false.

3. Adds a "Research record" block: version, publication date, last material
   revision, author, and a citation the reader can copy - plain text and
   BibTeX. Entry type is @misc, not @article, because these are not journal
   articles and labelling them as such would be a lie encoded in a citation.

Idempotent.
"""
import datetime as dt
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = 'https://quantmedia.io'

AUTHOR_NAME = 'Cemil Ertürk'
AUTHOR_URL = f'{SITE}/author/cemil-erturk.html'
AUTHOR_ROLE = 'QuantMedia Research'
# LaTeX needs the diacritic escaped or the citation renders as "Ertrk".
AUTHOR_BIBTEX = 'Ert{\\"u}rk, Cemil'

# The date the papers were materially revised (limitations + references added).
REVISED = '2026-08-16'
REVISED_HUMAN = 'August 16, 2026'
RESEARCH_VERSION = '1.1'

MARKER = 'qm-record'

CSS = """
.qm-record{border:1px solid var(--border,#242424);border-radius:6px;background:var(--bg2,#111);
  padding:20px 22px;margin:32px 0}
.qm-record h3{font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:700;
  letter-spacing:1.2px;text-transform:uppercase;color:var(--accent,#00a651);margin:0 0 14px}
.qm-record dl{display:grid;grid-template-columns:auto 1fr;gap:6px 18px;margin:0 0 16px;font-size:13.5px}
.qm-record dt{color:var(--dimmer,#888);white-space:nowrap}
.qm-record dd{margin:0;color:var(--text2,#c4c4c4)}
.qm-cite{margin-top:14px}
.qm-cite h4{font-size:12px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;
  color:var(--dimmer,#888);margin:14px 0 6px}
.qm-cite pre{background:var(--bg3,#181818);border:1px solid var(--border,#242424);border-radius:4px;
  padding:12px 14px;margin:0;overflow-x:auto;font-family:'JetBrains Mono',monospace;
  font-size:12px;line-height:1.65;color:var(--text2,#c4c4c4);white-space:pre;tab-size:2}
.qm-cite .plain{white-space:pre-wrap;word-break:break-word}
.qm-copy{font:inherit;font-size:11px;letter-spacing:.5px;text-transform:uppercase;
  background:none;border:1px solid var(--border2,#2e2e2e);color:var(--dimmer,#888);
  border-radius:3px;padding:4px 10px;cursor:pointer;margin-left:8px}
.qm-copy:hover{color:var(--text,#e8e8e8);border-color:var(--accent,#00a651)}
@media(pointer:coarse){.qm-copy{min-height:44px;min-width:64px;padding:0 14px}}
@media(max-width:600px){.qm-record dl{grid-template-columns:1fr;gap:2px 0}
  .qm-record dt{margin-top:8px}}
"""

COPY_JS = """
<script>
document.addEventListener('click',function(e){
  var b=e.target.closest('.qm-copy'); if(!b) return;
  var pre=document.getElementById(b.dataset.target); if(!pre) return;
  navigator.clipboard.writeText(pre.innerText).then(function(){
    var o=b.textContent; b.textContent='Copied'; setTimeout(function(){b.textContent=o;},1400);
  });
});
</script>
"""


def article_schema(h):
    """Return (raw_json_text, parsed) for the page's Article node."""
    for m in re.finditer(r'(?s)<script type="application/ld\+json">(.*?)</script>', h):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        if d.get('@type') in ('Article', 'ScholarlyArticle', 'BlogPosting'):
            return m.group(1), d
    return None, None


def bib_key(slug, year):
    tail = re.sub(r'[^a-z]', '', slug.replace('paper-', '').split('-')[0])
    return f'erturk{year}{tail}'


def record_block(slug, title, published, category, has_code):
    year = published[:4]
    url = f'{SITE}/{slug}'
    # %-d is POSIX-only and raises on Windows; strip the zero manually.
    try:
        d = dt.date.fromisoformat(published)
        pub_human = f'{d.strftime("%B")} {d.day}, {d.year}'
    except ValueError:
        pub_human = published

    plain = f'{AUTHOR_NAME}. "{title}." QuantMedia, {year}. {url}'
    bib = (f'@misc{{{bib_key(slug, year)},\n'
           f'  author       = {{{AUTHOR_BIBTEX}}},\n'
           f'  title        = {{{title}}},\n'
           f'  year         = {{{year}}},\n'
           f'  howpublished = {{QuantMedia}},\n'
           f'  url          = {{{url}}},\n'
           f'  note         = {{Accessed: <date>}}\n'
           f'}}')

    code_row = ''
    if has_code:
        code_row = ('<dt>Code</dt><dd><a href="/reproducibility.html">Runnable implementation '
                    'with tests</a></dd>')

    pid = 'cite-' + re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    return f'''<div class="qm-sec {MARKER}" id="research-record">
  <h3>Research record</h3>
  <dl>
    <dt>Author</dt><dd><a href="/author/cemil-erturk.html">{html.escape(AUTHOR_NAME)}</a> &middot; {AUTHOR_ROLE}</dd>
    <dt>Published</dt><dd>{pub_human}</dd>
    <dt>Last material revision</dt><dd>{REVISED_HUMAN}</dd>
    <dt>Research version</dt><dd>{RESEARCH_VERSION}</dd>
    <dt>Topic</dt><dd>{html.escape(category)}</dd>
    {code_row}
    <dt>Review status</dt><dd>Independent research. Not peer reviewed.</dd>
  </dl>
  <div class="qm-cite">
    <h4>How to cite this research
      <button class="qm-copy" data-target="{pid}-p" type="button">Copy</button></h4>
    <pre class="plain" id="{pid}-p">{html.escape(plain)}</pre>
    <h4>BibTeX
      <button class="qm-copy" data-target="{pid}-b" type="button">Copy</button></h4>
    <pre id="{pid}-b">{html.escape(bib)}</pre>
  </div>
</div>'''


def process(path):
    h = original = path.read_text(encoding='utf-8')
    slug = path.relative_to(ROOT).as_posix()

    raw, art = article_schema(h)
    if not art:
        return False, 'no Article schema'

    # ---- 1. schema author: Organization -> Person, with a resolvable URL ----
    art['author'] = {'@type': 'Person', 'name': AUTHOR_NAME, 'url': AUTHOR_URL}
    art['publisher'] = {'@type': 'Organization', 'name': 'QuantMedia', 'url': SITE}
    if art.get('dateModified') == art.get('datePublished'):
        art['dateModified'] = REVISED
    h = h.replace(raw, '\n' + json.dumps(art, indent=2, ensure_ascii=False) + '\n', 1)

    # ---- 2. meta author ----
    h = re.sub(r'<meta name="author" content="[^"]*">',
               f'<meta name="author" content="{AUTHOR_NAME}">', h)

    # ---- 3. visible byline ----
    upd = f'<span>&middot;</span><span>Updated {REVISED_HUMAN}</span>'

    def fix_byline(m):
        inner = m.group(1)
        # Drop any previously-placed "Updated" span so ordering can be redone.
        inner = inner.replace(upd, '')
        inner = inner.replace(
            '<span class="byline-author">QuantMedia Research</span>',
            f'<span class="byline-author"><a href="/author/cemil-erturk.html" '
            f'style="color:inherit">{AUTHOR_NAME}</a></span>')
        # "Updated" belongs immediately after the publication date, not before
        # it - author, published, updated, topic reads in chronological order.
        inner, n = re.subn(r'(<span>[A-Z][a-z]+ \d{1,2}, \d{4}</span>)',
                           r'\1' + upd, inner, count=1)
        if not n:
            inner += upd
        return f'<div class="article-byline">{inner}</div>'

    h = re.sub(r'(?s)<div class="article-byline">(.*?)</div>', fix_byline, h, count=1)

    # ---- 4. research record + citation ----
    if MARKER not in h:
        title = art.get('headline') or ''
        # Prefer the on-page H1: the schema headline is SEO-shaped, the H1 is
        # what a citing reader actually sees as the title of the work.
        mh1 = re.search(r'<h1 class="article-h1">(.*?)</h1>', h, re.S)
        if mh1:
            title = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', mh1.group(1))).strip()
        title = html.unescape(title)
        mcat = re.search(r'(?s)<div class="article-byline">.*?<span>([^<]+)</span>\s*</div>', h)
        category = html.unescape(mcat.group(1).strip()) if mcat else 'Research'
        has_code = 'qm-repro' in h
        block = record_block(slug, title, art.get('datePublished', '2026'), category, has_code)

        # Place it after references when present, else before the footer.
        anchor = None
        for cand in ('<div class="qm-sec" id="references">', '<div class="qm-repro">'):
            if cand in h:
                idx = h.index(cand)
                depth, i = 0, idx
                while i < len(h):                       # walk to the matching </div>
                    if h.startswith('<div', i):
                        depth += 1
                    elif h.startswith('</div>', i):
                        depth -= 1
                        if depth == 0:
                            anchor = i + len('</div>')
                            break
                    i += 1
                if anchor:
                    break
        if anchor is None:
            return False, 'no anchor for record block'
        h = h[:anchor] + '\n' + block + '\n' + h[anchor:]

    # ---- 5. styles + copy handler, once ----
    if '.qm-record{' not in h:
        h = h.replace('</head>', f'<style>{CSS}</style>\n</head>', 1)
    if 'qm-copy' in h and 'closest(\'.qm-copy\')' not in h:
        h = h.replace('</body>', COPY_JS + '</body>', 1)

    if h != original:
        path.write_text(h, encoding='utf-8')
        return True, 'updated'
    return False, 'already current'


def main():
    targets = sorted(ROOT.glob('paper-*.html'))
    changed = 0
    for p in targets:
        ok, msg = process(p)
        changed += ok
        print(f'  [{"chg" if ok else "  -"}] {p.name:44} {msg}')
    print(f'\n{changed}/{len(targets)} paper(s) updated')

    # Verify rather than assume.
    bad = []
    for p in targets:
        h = p.read_text(encoding='utf-8')
        _, art = article_schema(h)
        checks = {
            'schema Person': (art or {}).get('author', {}).get('@type') == 'Person',
            'schema url': (art or {}).get('author', {}).get('url') == AUTHOR_URL,
            'dateModified': (art or {}).get('dateModified') != (art or {}).get('datePublished'),
            'meta author': f'content="{AUTHOR_NAME}"' in h,
            'visible byline': 'author/cemil-erturk.html' in h,
            'record block': MARKER in h,
            'bibtex @misc': '@misc{' in h,
            'no @article': '@article{' not in h,
        }
        fails = [k for k, v in checks.items() if not v]
        if fails:
            bad.append((p.name, fails))
    if bad:
        for n, f in bad:
            print(f'  FAIL {n}: {f}')
        sys.exit(1)
    print(f'verified: {len(targets)}/{len(targets)} papers carry a consistent named author')


if __name__ == '__main__':
    main()
