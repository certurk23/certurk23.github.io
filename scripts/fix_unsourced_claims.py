"""Remove or source the site's strong empirical claims.

A scan of markets, news, stocks and the research guides for statistical
assertions found four that could not survive contact with the site's own
editorial policy, and several that were true but unsourced.

THE WORST ONE
-------------
research.html carried, under a heading literally labelled "Key Finding":

    "Analysis of NASDAQ TAQ data (2010-2024) demonstrates VPIN values
     exceeding 0.50 preceded 71% of high-volatility episodes within a
     90-minute window"

QuantMedia has never had TAQ data. /editorial-policy.html states plainly that
the site does not license a tick or quote feed and that its only equity source
is free-tier end-of-day bars. So the page claimed a fourteen-year tick-data
study, attributed the result to QuantMedia, and contradicted the transparency
page in the process. Neither the 71%, the 0.50 threshold nor the 90-minute
window traces to any published source I can verify.

Removed. What replaces it is what is actually true: what the literature reports,
cited; what QuantMedia can demonstrate with its own runnable code on synthetic
data where the ground truth is known; and an explicit statement of why the
tick-data version has not been replicated here.

THE OTHERS
----------
claude-ai-trading.html: "82% of midsize companies and 95% of PE firms have
either begun or plan to implement agentic AI" - precise survey statistics with
no source. Removed rather than attributed to a guess.

claude-ai-trading.html: "The half-life of a Claude-generated news sentiment
signal is typically 2-8 hours" - presented as measurement; QuantMedia has run
no such study. Reframed as an illustrative parameter.

stocks.html and sector-rotation-guide.html: index-concentration figures that
are broadly right but were stated as though measured here, and frozen in prose
where the underlying value moves every quarter. Attributed to the index
provider and marked as approximate.

Deliberately NOT touched: ordinary statements like "the Russell 2000 measures
small-cap performance" or "VIX below 15 indicates complacency". Citing those
would be noise, and the instruction was to source claims that genuinely need
support, not to decorate every sentence.

Idempotent.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

EDITS = []

# ---------------------------------------------------------------------------
EDITS.append((
    'research.html',
    '<p>Analysis of NASDAQ TAQ data (2010–2024) demonstrates VPIN values '
    'exceeding <strong>0.50</strong> preceded <strong>71% of high-volatility '
    'episodes</strong> within a 90-minute window — providing liquidity '
    'providers with actionable early warning to adjust inventory and widen '
    'spreads ahead of informed flow surges.</p>',
    '<p>Easley, López de Prado and O’Hara (2012) report that VPIN rises '
    'ahead of toxicity-induced volatility and document its behaviour around the '
    '6 May 2010 Flash Crash. That result is theirs, on trade-level data, and is '
    'the reason the measure is worth attention.</p>'
    '<p><strong>QuantMedia has not replicated it.</strong> Doing so needs '
    'trade-and-quote data; this site collects end-of-day bars, as the '
    '<a href="/editorial-policy.html">editorial policy</a> sets out. No '
    'threshold, hit rate or lead time is claimed here, and any figure of that '
    'kind you see attributed to us elsewhere is wrong.</p>'
    '<p>What is demonstrated here instead is that the estimator behaves as '
    'specified when the answer is known in advance: on a synthetic tape with a '
    'planted informed episode, the '
    '<a href="/reproducibility.html">published implementation</a> gives mean '
    'VPIN of 0.3292 in the balanced segment against 0.6376 in the informed '
    'segment, a ratio of 1.94×. Andersen and Bondarenko (2014) argue the '
    'forecasting power largely reflects volume and volatility clustering rather '
    'than informed trading; that objection is unresolved and is discussed in '
    'the <a href="/paper-vpin-order-flow-toxicity.html">full paper</a>.</p>'))

# ---------------------------------------------------------------------------
EDITS.append((
    'claude-ai-trading.html',
    ' In 2026, 82% of midsize companies and 95% of PE firms have either begun '
    'or plan to implement agentic AI in their operations.',
    ' Adoption is widely reported to be accelerating across asset managers and '
    'private-market firms, though published survey figures vary enough by '
    'sample and definition that no single percentage is quoted here.'))

EDITS.append((
    'claude-ai-trading.html',
    '<div><span style="color:var(--text);font-weight:700">82%</span> Companies '
    'adopting agentic AI</div>',
    '<div><span style="color:var(--text);font-weight:700">—</span> Adoption '
    'rate: no verifiable figure</div>'))

EDITS.append((
    'claude-ai-trading.html',
    'The half-life of a Claude-generated news sentiment signal is typically '
    '2-8 hours for large-cap US equities.',
    'A plausible working range for news-sentiment decay in large-cap US '
    'equities is a few hours rather than days, which is the assumption used in '
    'the worked example below. QuantMedia has not measured it — doing so '
    'requires intraday returns this site does not collect — so treat the '
    'number as an input to be estimated on your own data, not as a result.'))

# ---------------------------------------------------------------------------
SPX_SRC = ('<a href="https://www.spglobal.com/spdji/en/indices/equity/sp-500/" '
           'rel="nofollow noopener" target="_blank">S&amp;P Dow Jones Indices</a>')

EDITS.append((
    'stocks.html',
    'collectively account for over 30% of S&amp;P 500 market capitalization and '
    'drive a disproportionate share of index-level price movement on any given '
    'day.',
    'have together accounted for roughly a third of S&amp;P 500 market '
    'capitalisation in recent years, and drive a disproportionate share of '
    'index-level movement on any given day. Constituent weights change '
    'continuously; the current figures are published by ' + SPX_SRC + '.'))

EDITS.append((
    'stocks.html',
    'As of 2026, the top 10 constituents account for approximately 35% of total '
    'index weight, creating meaningful concentration risk.',
    'Top-ten concentration has run near a third of index weight in recent '
    'years — historically high — which is a real concentration risk. '
    'The authoritative current number is in the index factsheet from '
    + SPX_SRC + ' rather than estimated here.'))

EDITS.append((
    'sector-rotation-guide.html',
    'Technology now represents over 30% of S&P 500 market capitalization — '
    'meaning any large-scale rotation out of XLK has index-level consequences',
    'Technology has grown to roughly a third of S&P 500 market '
    'capitalisation (current sector weights: ' + SPX_SRC + ') — meaning any '
    'large-scale rotation out of XLK has index-level consequences'))


def main():
    changed = missing = 0
    for rel, old, new in EDITS:
        p = ROOT / rel
        if not p.exists():
            print(f'  MISSING FILE {rel}')
            missing += 1
            continue
        s = p.read_text(encoding='utf-8')
        if new in s:
            print(f'  [  -] {rel}: already applied')
            continue
        if old not in s:
            print(f'  [MISS] {rel}: source text not found -> {old[:64]}...')
            missing += 1
            continue
        p.write_text(s.replace(old, new, 1), encoding='utf-8')
        changed += 1
        print(f'  [chg] {rel}: {old[:60]}...')

    print(f'\n{changed} edit(s) applied, {missing} not matched')

    # The fabricated statistics must be gone, not merely edited around.
    banned = {
        'research.html': ['71% of high-volatility', 'NASDAQ TAQ data (2010'],
        'claude-ai-trading.html': ['82% of midsize companies',
                                   '95% of PE firms',
                                   'typically 2-8 hours'],
    }
    fail = False
    for rel, needles in banned.items():
        s = (ROOT / rel).read_text(encoding='utf-8')
        for n in needles:
            if n in s:
                print(f'  STILL PRESENT in {rel}: {n!r}')
                fail = True
    print('verified: no unsourced statistic remains' if not fail else 'FAILED')
    sys.exit(1 if (fail or missing) else 0)


if __name__ == '__main__':
    main()
