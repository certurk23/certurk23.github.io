#!/usr/bin/env python3
"""
Static page generator for /indices/, /learn/ and /tools/.
=========================================================
One-shot tool, not part of the CI run. It assembles new pages from the shared
site shell (lifted from methodology.html) plus per-page content, so the nav,
styling and footer stay identical across the site instead of drifting.

    python scripts/build_pages.py

Re-run it after editing PAGES or the shell. The output is committed as plain
static HTML: the whole point of these pages is that a crawler or an assistant
sees the content in the markup without executing JavaScript.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import qm_config as C   # noqa: E402

E = C.ENGINE
SITE = 'https://quantmedia.io'

# One canonical font request for the whole site. Barlow 300 is requested
# nowhere in the CSS and Barlow Condensed 500 is used 21 times site-wide across
# all families combined, so both are dropped: 12 font files becomes 10.
# Loaded via preload+onload rather than a plain stylesheet link, because a
# stylesheet link to fonts.googleapis.com blocks first paint on a third-party
# round trip. The <noscript> copy keeps the fonts for scripting-disabled agents.
FONT_HREF = ('https://fonts.googleapis.com/css2?family=Barlow:ital,wght@0,400;0,500;0,600;0,700;1,400'
             '&family=Barlow+Condensed:wght@400;600;700'
             '&family=JetBrains+Mono:wght@400;500&display=swap')


# ---------------------------------------------------------------------------
# Shared shell, lifted from methodology.html so styling cannot drift
# ---------------------------------------------------------------------------
def shell_parts():
    src = open(os.path.join(ROOT, 'methodology.html'), encoding='utf-8').read()
    style = re.search(r'<style>.*?</style>', src, re.DOTALL).group(0)
    header = re.search(r'<header class="site-header">.*?</header>',
                       src, re.DOTALL).group(0)
    footer = re.search(r'<footer>.*?</footer>', src, re.DOTALL).group(0)
    # Pages live one directory down, so relative links need a root prefix.
    def rootify(html):
        html = re.sub(r'href="(?!https?://|/|#|mailto:)', 'href="/', html)
        html = re.sub(r'src="(?!https?://|/|data:)', 'src="/', html)
        return html.replace('href="/./"', 'href="/"')
    return style, rootify(header), rootify(footer)


EXTRA_CSS = """
<style>
.qm-lede{font-size:15px;line-height:1.85;color:var(--text);margin:0 0 20px}
.qm-answer{background:rgba(0,166,81,.07);border:1px solid rgba(0,166,81,.28);
  border-left:3px solid var(--accent);border-radius:0 4px 4px 0;padding:16px 20px;margin:0 0 24px}
.qm-answer p{margin:0;font-size:14.5px;line-height:1.8;color:var(--text)}
.qm-answer .qm-answer-label{font-family:'Barlow Condensed',sans-serif;font-size:10px;
  font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--accent);
  display:block;margin-bottom:8px}
.qm-def{border:1px solid var(--border);background:var(--bg2);border-radius:4px;
  padding:16px 20px;margin:20px 0}
.qm-def dt{font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;
  letter-spacing:1.1px;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
.qm-def dd{margin:0 0 14px;font-size:14px;line-height:1.8;color:var(--text)}
.qm-def dd:last-child{margin-bottom:0}
.qm-formula{font-family:'JetBrains Mono',monospace;font-size:13px;line-height:1.9;
  background:var(--bg3);border:1px solid var(--border2);border-radius:4px;
  padding:14px 16px;margin:16px 0;overflow-x:auto;white-space:pre;color:var(--text)}
.qm-kv{width:100%;border-collapse:collapse;border:1px solid var(--border);margin:14px 0;font-size:13.5px}
.qm-kv th,.qm-kv td{padding:8px 12px;border-bottom:1px solid var(--border);text-align:left}
.qm-kv thead th{background:var(--bg3);font-family:'Barlow Condensed',sans-serif;
  font-size:11px;letter-spacing:.6px;text-transform:uppercase;color:var(--accent)}
.qm-kv th{color:var(--dim);font-weight:600;width:38%}
.qm-kv td{color:var(--text)}
.qm-num{font-family:'JetBrains Mono',monospace}
.qm-rank{font-family:'JetBrains Mono',monospace;color:var(--accent);font-weight:600;width:36px}
.qm-sector{font-weight:600}
.qm-tablewrap{overflow-x:auto}
.qm-reading{font-size:15px;line-height:1.8;margin:0 0 14px;color:var(--text)}
.qm-note{font-size:12.5px;line-height:1.75;color:var(--dim);margin:10px 0 0}
.qm-refs{font-size:13px;line-height:1.85;color:var(--dim);margin:0;padding-left:18px}
.qm-refs li{margin-bottom:8px}
.qm-crumb{font-size:11px;color:var(--dim);margin-bottom:14px;
  font-family:'Barlow Condensed',sans-serif;letter-spacing:.6px;text-transform:uppercase}
.qm-crumb a{color:var(--accent)}
.qm-related{list-style:none;padding:0;margin:0}
.qm-related li{padding:9px 0;border-bottom:1px solid var(--border);font-size:14px}
.qm-related a{color:var(--accent);font-weight:600}
.qm-related span{color:var(--dim);display:block;font-size:12.5px;margin-top:3px}
.calc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}
.calc-field label{display:block;font-size:11px;font-family:'Barlow Condensed',sans-serif;
  letter-spacing:.7px;text-transform:uppercase;color:var(--dim);margin-bottom:5px}
.calc-field input{width:100%;padding:9px 11px;background:var(--bg);color:var(--text);
  border:1px solid var(--border2);border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:13px}
.calc-out{background:var(--bg3);border:1px solid var(--border2);border-radius:4px;
  padding:16px 18px;margin-top:14px}
.calc-out .big{font-family:'JetBrains Mono',monospace;font-size:30px;color:var(--accent);font-weight:600}
</style>
"""


def page(slug, title, description, h1, crumb, body,
         schema_type='Article', published='2026-08-08', modified='2026-08-08',
         extra_schema=''):
    style, header, footer = shell_parts()
    url = f'{SITE}/{slug}'
    ld = f'''<script type="application/ld+json">{{
  "@context":"https://schema.org",
  "@type":"{schema_type}",
  "headline":{title.split(" | ")[0]!r},
  "description":{description!r},
  "author":{{"@type":"Person","name":"Cemil Ertürk","url":"{SITE}/author/cemil-erturk.html"}},
  "publisher":{{"@type":"Organization","name":"QuantMedia","url":"{SITE}"}},
  "datePublished":"{published}",
  "dateModified":"{modified}",
  "mainEntityOfPage":"{url}",
  "isAccessibleForFree":true
}}</script>
<script type="application/ld+json">{{
  "@context":"https://schema.org",
  "@type":"BreadcrumbList",
  "itemListElement":[
    {{"@type":"ListItem","position":1,"name":"Home","item":"{SITE}/"}},
    {{"@type":"ListItem","position":2,"name":{crumb[0]!r},"item":"{SITE}/{crumb[1]}"}},
    {{"@type":"ListItem","position":3,"name":{h1!r},"item":"{url}"}}
  ]
}}</script>'''.replace("'", '"')

    return f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<script>try{{var _t=localStorage.getItem('qm-theme');if(_t)document.documentElement.setAttribute('data-theme',_t);}}catch(e){{}}</script>
<meta charset="UTF-8">
<meta name="google-adsense-account" content="ca-pub-7635577322319251">
<meta name="theme-color" content="#00a651">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta name="author" content="Cemil Ertürk">
<meta property="og:type" content="article">
<meta property="og:title" content="{title.split(' | ')[0]}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="QuantMedia">
<meta property="og:image" content="{SITE}/og-card.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title.split(' | ')[0]}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{SITE}/og-card.png">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-QX7WEBS0LK"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-QX7WEBS0LK');</script>
{ld}{extra_schema}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="{FONT_HREF}" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="{FONT_HREF}"></noscript>
{style}
{EXTRA_CSS}
</head>
{header}
<main>
<div class="page-wrap">
  <div class="qm-crumb"><a href="/">Home</a> &rsaquo; <a href="/{crumb[1]}">{crumb[0]}</a> &rsaquo; {h1}</div>
  <h1 style="font-family:'Barlow Condensed',sans-serif;font-size:30px;font-weight:800;letter-spacing:.3px;color:var(--text);margin:0 0 16px;line-height:1.2">{h1}</h1>
{body}
</div>
</main>
{footer}
<script>
function toggleTheme(){{var c=document.documentElement.getAttribute('data-theme');var n=c==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',n);try{{localStorage.setItem('qm-theme',n);}}catch(e){{}}}}
</script>
</body>
</html>
'''


def write(slug, html):
    path = os.path.join(ROOT, slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  wrote {slug}  ({len(html):,} bytes)')


import page_content as PC
import page_content_identity as PCI   # noqa: E402

# knowsAbout lists only subjects with published work behind them on this site.
# No affiliation, credential, job title or award appears here, because none can
# be verified - and an unverifiable claim in structured data is still a claim.
PERSON_SCHEMA = '''
<script type="application/ld+json">{
  "@context":"https://schema.org",
  "@type":"Person",
  "name":"Cemil Ertürk",
  "url":"https://quantmedia.io/author/cemil-erturk.html",
  "email":"mailto:contact@quantmedia.io",
  "description":"Independent quantitative researcher and engineer. Writes the research and builds the data pipeline behind QuantMedia.",
  "knowsAbout":["Market microstructure","Order flow toxicity","VPIN","Hierarchical Risk Parity","Portfolio construction","Probabilistic Sharpe Ratio","Backtest overfitting","Transaction cost analysis","Slippage modelling","Systematic trading signals"],
  "sameAs":["https://github.com/certurk23","https://x.com/certurk23"],
  "worksFor":{"@type":"Organization","name":"QuantMedia","url":"https://quantmedia.io"},
  "mainEntityOfPage":"https://quantmedia.io/author/cemil-erturk.html"
}</script>'''

PAGES = [
    dict(slug='indices/signal-breadth.html',
         title='QuantMedia Signal Breadth Index | QuantMedia',
         description=('QuantMedia Signal Breadth: the share of scored US equities '
                      'meeting the ' + str(E['confluence_min']) + '-of-' + str(E['n_signals'])
                      + ' technical threshold, updated after every US close. Formula, '
                        'current reading, history and limitations.'),
         h1='QuantMedia Signal Breadth Index',
         crumb=('Indices', 'indices/signal-breadth.html'),
         body=PC.BREADTH_BODY, schema_type='Article'),

    dict(slug='indices/sector-confluence.html',
         title='QuantMedia Sector Confluence Index | QuantMedia',
         description=('QuantMedia Sector Confluence: mean technical confluence score '
                      'and BUY breadth per US sector, ranked and updated after every '
                      'US close. Method, current reading and limitations.'),
         h1='QuantMedia Sector Confluence Index',
         crumb=('Indices', 'indices/sector-confluence.html'),
         body=PC.SECTOR_BODY, schema_type='Article'),

    dict(slug='learn/what-is-vpin.html',
         title='What Is VPIN? Order Flow Toxicity Explained | QuantMedia',
         description=('VPIN measures order-flow toxicity using equal-volume buckets. '
                      'Definition, formula, a worked numeric example, what a high '
                      'reading means, and the documented criticism of it.'),
         h1='What is VPIN?',
         crumb=('Learn', 'learn/what-is-vpin.html'),
         body=PC.VPIN_BODY),

    dict(slug='learn/what-is-probabilistic-sharpe-ratio.html',
         title='What Is the Probabilistic Sharpe Ratio? | QuantMedia',
         description=('The Probabilistic Sharpe Ratio gives the probability a true '
                      'Sharpe exceeds a benchmark, adjusting for track-record length, '
                      'skewness and kurtosis. Formula, worked example, limitations.'),
         h1='What is the Probabilistic Sharpe Ratio?',
         crumb=('Learn', 'learn/what-is-probabilistic-sharpe-ratio.html'),
         body=PC.PSR_BODY),

    dict(slug='learn/hrp-vs-mean-variance.html',
         title='HRP vs Mean-Variance Optimisation Compared | QuantMedia',
         description=('Hierarchical Risk Parity avoids inverting the covariance matrix; '
                      'mean-variance does not. Side-by-side comparison of stability, '
                      'concentration, turnover and out-of-sample behaviour.'),
         h1='HRP vs mean-variance optimisation',
         crumb=('Learn', 'learn/hrp-vs-mean-variance.html'),
         body=PC.HRP_BODY),

    dict(slug='learn/how-to-model-slippage-in-backtests.html',
         title='How to Model Slippage in Backtests | QuantMedia',
         description=('Model slippage as spread, square-root market impact and delay '
                      'cost rather than one flat number. Formula, worked example, and '
                      'what turnover does to a strategy net of costs.'),
         h1='How to model slippage in backtests',
         crumb=('Learn', 'learn/how-to-model-slippage-in-backtests.html'),
         body=PC.SLIPPAGE_BODY),

    dict(slug='learn/deflated-sharpe-ratio.html',
         title='Deflated Sharpe Ratio: Correcting for Backtest Overfitting | QuantMedia',
         description=('The Deflated Sharpe Ratio raises the benchmark to the Sharpe '
                      'you would expect from luck alone after N trials. Formula, '
                      'worked example, and how it differs from PSR.'),
         h1='What is the Deflated Sharpe Ratio?',
         crumb=('Learn', 'learn/deflated-sharpe-ratio.html'),
         body=PC.DSR_BODY),

    dict(slug='learn/what-is-signal-confluence.html',
         title='What Is Signal Confluence in Stock Screening? | QuantMedia',
         description=('Signal confluence requires several technical conditions to agree '
                      'before acting. How QuantMedia scores ' + str(E['n_signals'])
                      + ' checks per stock, why the threshold is '
                      + str(E['confluence_min']) + ', and what that choice costs.'),
         h1='What is signal confluence?',
         crumb=('Learn', 'learn/what-is-signal-confluence.html'),
         body=PC.CONFLUENCE_BODY),

    dict(slug='learn/what-is-market-breadth.html',
         title='What Is Market Breadth? Measures Compared | QuantMedia',
         description=('Market breadth measures how many stocks participate in a move. '
                      'Advance/decline, percent above the 200-day, new highs minus lows, '
                      'and QuantMedia Signal Breadth compared.'),
         h1='What is market breadth?',
         crumb=('Learn', 'learn/what-is-market-breadth.html'),
         body=PC.BREADTH_LEARN_BODY),

    dict(slug='reproducibility.html',
         title='Research Reproducibility: Code, Data and Tools | QuantMedia',
         description=('Runnable implementations behind QuantMedia research: VPIN '
                      'order-flow toxicity and Hierarchical Risk Parity, with '
                      'example data, expected output and tests. Plus which papers '
                      'are research-only.'),
         h1='Research reproducibility',
         crumb=('Research', 'papers.html'),
         body=PC.REPRO_BODY),

    dict(slug='tools/probabilistic-sharpe-ratio-calculator.html',
         title='Probabilistic Sharpe Ratio Calculator | QuantMedia',
         description=('Free PSR calculator. Enter observed Sharpe, benchmark, '
                      'observations, skewness and kurtosis to get the probability the '
                      'true Sharpe exceeds your benchmark. Runs in your browser.'),
         h1='Probabilistic Sharpe Ratio calculator',
         crumb=('Tools', 'tools/probabilistic-sharpe-ratio-calculator.html'),
         body=PC.PSR_TOOL_BODY, schema_type='WebApplication'),

    # The author page carries Person + ProfilePage rather than Article: it is
    # an identity page, and mislabelling it as an article would be the same
    # class of error as the ScholarlyArticle claim that was removed earlier.
    dict(slug='author/cemil-erturk.html',
         title='Cemil Ertürk - Quantitative Researcher | QuantMedia',
         description=('Cemil Ertürk is the researcher behind QuantMedia, covering market '
                      'microstructure, portfolio construction, execution costs and '
                      'systematic signals. Independent research, published with code.'),
         h1='Cemil Ertürk',
         crumb=('About', 'about.html'),
         body=PCI.AUTHOR_BODY, schema_type='ProfilePage',
         extra_schema=PERSON_SCHEMA),

    dict(slug='editorial-policy.html',
         title='Editorial Policy, Corrections and Disclosures | QuantMedia',
         description=('How QuantMedia research is produced, funded, versioned and '
                      'corrected. Data sources, independence, AI-tool disclosure, '
                      'corrections policy and what has not been validated.'),
         h1='Editorial policy',
         crumb=('About', 'about.html'),
         body=PCI.EDITORIAL_BODY),
]


def main():
    print('Building generated pages')
    for spec in PAGES:
        write(spec['slug'], page(**spec))
    print(f'\n{len(PAGES)} pages written')
    return 0


if __name__ == '__main__':
    sys.exit(main())
