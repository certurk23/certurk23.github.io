"""Make the site usable on a phone. Two separate defects, both measured.

DEFECT 1 - horizontal overflow
------------------------------
Measured in a real browser at a 375px viewport before this ran:

    quantum-signals.html    549px of horizontal overflow
    claude-ai-trading.html  441px
    methodology.html         86px
    stocks.html              16px (at 320px)

Root cause is not the obvious one. `.page-grid` is a CSS grid whose mobile rule
already sets `grid-template-columns:1fr`, which looks correct. But `1fr` is
shorthand for `minmax(auto, 1fr)`, and an `auto` minimum refuses to shrink below
the content's min-content width. One wide table or code block therefore drags
the whole track past the viewport, and the page scrolls sideways.

`minmax(0, 1fr)` lets the track shrink, and the wide child is then made to
scroll inside its own box instead of pushing the page. Verified in-browser
before being written to any file: 549 -> 0, 441 -> 0, 86 -> 0.

DEFECT 2 - no mobile navigation
-------------------------------
14 pages - including all 11 research papers - render the desktop nav on
phones with no hamburger and no mobile menu. `.main-nav` has `overflow:hidden`,
so the links past the fold are clipped and simply unreachable: on a phone you
could open a paper and have no way to navigate anywhere else. The pattern
applied here is the one already working on the other 23 pages, not a new one.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

MOBILE_CSS = """
/* --- mobile hardening ---------------------------------------------------
   `1fr` means `minmax(auto,1fr)`, and an auto minimum cannot shrink below the
   content's min-content width, so a single wide table pushed the whole grid
   track past the viewport. minmax(0,1fr) lets it shrink; wide children then
   scroll inside their own box rather than scrolling the page. */
@media(max-width:900px){
  .page-grid{grid-template-columns:minmax(0,1fr)}
  .article-content,.article-wrap,.page-wrap,main{min-width:0}
  .profile-hero-inner,.profile-info{min-width:0;max-width:100%;flex-wrap:wrap}
  table{display:block;width:100%;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
  pre,code{max-width:100%;overflow-x:auto}
  img,svg,iframe{max-width:100%;height:auto}
}
"""

HAMBURGER = ('<button class="hamburger" id="hamburger" onclick="toggleMenu()" title="Menu" '
             'aria-label="Toggle navigation" aria-expanded="false" aria-controls="mobileNav">'
             '<span></span><span></span><span></span></button>')

MOBILE_NAV = """
<!-- MOBILE NAV -->
<div class="mobile-nav" id="mobileNav">
  <a href="/">Home</a>
  <a href="/markets.html">Live Data</a>
  <a href="/news.html">News</a>
  <a href="/stocks.html">Equities</a>
  <a href="/quantum-signals.html">Quantum</a>
  <a href="/papers.html">Papers</a>
  <a href="/research.html">Microstructure</a>
  <a href="/about.html">About</a>
</div>
"""

NAV_CSS = """
.hamburger{display:none;flex-direction:column;justify-content:center;gap:5px;width:32px;height:32px;background:transparent;border:1px solid var(--border2);border-radius:4px;padding:7px;cursor:pointer;flex-shrink:0}
.hamburger span{display:block;height:1.5px;background:var(--text);border-radius:2px;transition:all .2s ease;transform-origin:center}
.hamburger.open span:nth-child(1){transform:translateY(6.5px) rotate(45deg)}
.hamburger.open span:nth-child(2){opacity:0}
.hamburger.open span:nth-child(3){transform:translateY(-6.5px) rotate(-45deg)}
.mobile-nav{display:none;position:fixed;top:var(--nav-h);left:0;right:0;background:var(--bg2);border-bottom:2px solid var(--accent);z-index:148;box-shadow:0 8px 32px rgba(0,0,0,.6)}
.mobile-nav.open{display:block}
.mobile-nav a{display:block;padding:13px 24px;font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:600;letter-spacing:.8px;text-transform:uppercase;color:var(--dim);border-left:3px solid transparent;transition:color .14s,border-color .14s}
.mobile-nav a:hover,.mobile-nav a.active{color:var(--text);border-left-color:var(--accent);background:var(--bg3)}
@media(max-width:900px){.site-header .main-nav,.main-nav{display:none}.btn-subscribe{display:none}.hamburger{display:flex}}
"""

NAV_JS = """
<script>
function toggleMenu(){var h=document.getElementById('hamburger'),m=document.getElementById('mobileNav');
 var open=m.classList.toggle('open');h.classList.toggle('open');
 h.setAttribute('aria-expanded',open?'true':'false');document.body.style.overflow=open?'hidden':'';}
document.querySelectorAll('.mobile-nav a').forEach(function(a){a.addEventListener('click',function(){
 document.getElementById('hamburger').classList.remove('open');
 document.getElementById('mobileNav').classList.remove('open');
 document.getElementById('hamburger').setAttribute('aria-expanded','false');
 document.body.style.overflow='';});});
</script>
"""

stats = {'overflow_css': 0, 'nav_added': 0, 'skipped_no_anchor': []}

for f in sorted(ROOT.rglob('*.html')):
    if any(p in ('.git', 'node_modules') for p in f.parts):
        continue
    src = out = f.read_text(encoding='utf-8')
    if '<html' not in out:
        continue

    # ---- 1. overflow hardening, every page ----
    if 'mobile hardening' not in out and '</head>' in out:
        out = out.replace('</head>', f'<style>{MOBILE_CSS}</style>\n</head>', 1)
        stats['overflow_css'] += 1

    # ---- 2. mobile nav, only where it is missing ----
    # All 14 affected pages carry <div class="header-right"> as the button
    # cluster, so the hamburger goes in as its first child - same position it
    # already occupies on the 23 pages where the pattern works.
    if 'class="main-nav"' in out and 'hamburger' not in out:
        anchor = '<div class="header-right">'
        if anchor not in out:
            stats['skipped_no_anchor'].append(f.name)
        else:
            out = out.replace(anchor, anchor + HAMBURGER, 1)
            out = out.replace('</header>', '</header>\n' + MOBILE_NAV, 1)
            out = out.replace('</head>', f'<style>{NAV_CSS}</style>\n</head>', 1)
            out = out.replace('</body>', NAV_JS + '</body>', 1)
            stats['nav_added'] += 1

    if out != src:
        f.write_text(out, encoding='utf-8')

print(f"  overflow CSS added : {stats['overflow_css']}")
print(f"  mobile nav added   : {stats['nav_added']}")
if stats['skipped_no_anchor']:
    print(f"  NO ANCHOR (skipped): {stats['skipped_no_anchor']}")

missing = [f.as_posix().lstrip('./') for f in ROOT.rglob('*.html')
           if '.git' not in f.parts
           and 'class="main-nav"' in f.read_text(encoding='utf-8')
           and 'hamburger' not in f.read_text(encoding='utf-8')]
print(f"  pages still lacking a mobile nav: {missing or 'none'}")
sys.exit(1 if missing else 0)
