"""Add assumptions, measured results, robustness and cost notes to the five
flagship papers.

WHY
---
A section audit of the flagship papers found:

    Limitations   5/5     Assumptions        0/5
    References    5/5     Results            0/5
    Author block  5/5     Robustness         0/5
                          Transaction costs  1/5

The first column is what earlier passes added. The second column is what
separates a summary of somebody else's paper from research someone can act on,
and it is precisely where the better independent quant sites are strong.

EVERY NUMBER BELOW WAS PRODUCED BY RUNNING THE SHIPPED CODE
-----------------------------------------------------------
The HRP table is the console output of
`quantmedia-research/hierarchical-risk-parity/compare_mvo.py`, and the VPIN
figures are the output of `quantmedia-research/vpin-order-flow-toxicity/
example.py`. Both run on synthetic data from a fixed seed, which is stated in
the text every time a number appears - synthetic data proves the estimator
behaves as claimed when the ground truth is known, and proves nothing about
live markets.

Nothing here is a backtest of a tradeable strategy, and no performance claim is
made for any QuantMedia signal. Papers with no implementation get assumptions,
robustness and cost discussion only - no invented results table.

Idempotent.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MARKER = 'qm-deepen'


def sec(anchor_id, title, body):
    return (f'<div class="qm-sec {MARKER}" id="{anchor_id}"><h2>{title}</h2>'
            f'{body}</div>')


# ---------------------------------------------------------------------------
VPIN = sec('assumptions', 'Assumptions', '''
<p>The estimator rests on four assumptions, each of which can fail
independently:</p>
<ul>
<li><strong>The volume clock is the right clock.</strong> Buckets are equal in
volume, not in time, so a quiet hour and a frantic minute can occupy the same
bucket. This is deliberate &mdash; information arrives with volume, not with
the wall clock &mdash; but it means bucket boundaries move with activity and
two runs over different bucket sizes are not directly comparable.</li>
<li><strong>Bulk volume classification approximates signing.</strong> BVC
infers buy volume from the standardised price change across a bucket rather
than from the true aggressor side. Where genuine trade-direction flags exist,
they are better; BVC exists because that data is expensive.</li>
<li><strong>Price changes are approximately Student-t.</strong> BVC uses a
Student-t CDF with a chosen degrees-of-freedom parameter. Fatter tails than
assumed push classifications toward 0 or 1 and inflate the measured imbalance.</li>
<li><strong>The bucket count in the rolling window is stationary enough.</strong>
VPIN is a rolling mean over the last <em>n</em> buckets. Regime changes inside
that window are averaged away.</li>
</ul>''') + sec('results', 'What the implementation actually produces', '''
<p>The numbers below are the console output of <code>example.py</code> in the
published package, on a 20,000-trade synthetic tape generated from a fixed
seed. The tape is constructed with a known balanced segment and a known
informed segment, so the estimator can be checked against a ground truth that
real market data never provides.</p>
<div class="qm-tablewrap"><table class="qm-kv">
<thead><tr><th>Measure</th><th>Bulk volume classification</th><th>Tick rule</th></tr></thead>
<tbody>
<tr><td>Buckets</td><td class="qm-num">250</td><td class="qm-num">250</td></tr>
<tr><td>Mean VPIN</td><td class="qm-num">0.4410</td><td class="qm-num">0.1779</td></tr>
<tr><td>Minimum</td><td class="qm-num">0.2805</td><td class="qm-num">0.1247</td></tr>
<tr><td>Maximum</td><td class="qm-num">0.8257</td><td class="qm-num">0.2918</td></tr>
</tbody></table></div>
<p>Against the known regimes, mean VPIN was <strong>0.3292</strong> in the
balanced segment and <strong>0.6376</strong> in the informed segment &mdash; a
ratio of <strong>1.94&times;</strong>. That is the property the measure is
supposed to have, demonstrated rather than asserted.</p>
<p class="qm-note">Synthetic data from a fixed seed. This shows the estimator
responds to order-flow imbalance as designed; it is not evidence about any real
security, and no trading result is implied.</p>''') + sec(
    'robustness', 'Robustness: what would change the conclusion', '''
<p><strong>The absolute level is method-dependent and should not be compared
across implementations.</strong> On the same tape, BVC gives a mean of 0.4410
and the tick rule 0.1779 &mdash; a factor of 2.5. Any threshold such as
&ldquo;VPIN above 0.4 is toxic&rdquo; is therefore meaningless without stating
the classification method, the bucket size and the window length. Only the
movement of the series against its own history carries information.</p>
<p><strong>The published criticism is substantive, not a footnote.</strong>
Andersen and Bondarenko (2014) argue that VPIN's forecasting power largely
reflects volume and volatility clustering rather than informed trading, and
that the 2010 Flash Crash result is sensitive to specification. Their objection
is not resolved here, and a reader should treat VPIN as a conditioning variable
rather than a signal.</p>
<p><strong>QuantMedia does not compute VPIN on live data.</strong> The pipeline
behind this site collects end-of-day bars, and VPIN needs trade-level data. No
VPIN index is published here, and the
<a href="/reproducibility.html">reproducibility index</a> says so explicitly
rather than leaving the absence to inference.</p>''') + sec(
    'costs', 'Relevance to transaction costs', '''
<p>VPIN is most useful read as an adverse-selection cost estimate rather than a
directional signal. When flow is one-sided, a passive order that gets filled is
disproportionately likely to have been filled by someone better informed, so
the effective cost of resting on the book rises even though the quoted spread
has not moved.</p>
<p>Practically that argues for shifting toward liquidity-taking or pausing
execution when the measure is elevated relative to its own recent range, and it
connects directly to the
<a href="/paper-slippage-latency-modeling.html">slippage model</a>: adverse
selection is the component that a spread-plus-impact cost model systematically
understates.</p>''')

# ---------------------------------------------------------------------------
HRP = sec('assumptions', 'Assumptions', '''
<ul>
<li><strong>Correlation carries the structure worth using.</strong> HRP builds
its tree from a correlation distance and never estimates expected returns. If
you hold genuine return forecasts, discarding them is a real cost, not a free
simplification.</li>
<li><strong>The hierarchy is stable enough to be worth respecting.</strong> The
tree is estimated from the same noisy sample it is meant to protect against.</li>
<li><strong>Weights are held fixed out of sample.</strong> The comparison below
fits weights in sample and does not rebalance, which isolates estimation error
from rebalancing effects.</li>
<li><strong>Long-only by construction.</strong> Recursive bisection splits a
positive budget, so HRP cannot short. Mean-variance can, and does.</li>
</ul>''') + sec('results', 'Measured out-of-sample behaviour', '''
<p>Output of <code>compare_mvo.py</code> in the published package: 20 assets,
120 in-sample periods, 400 out-of-sample periods, synthetic data from a fixed
seed. Mean absolute correlation 0.240; covariance condition number 43, high
enough that inversion is visibly unstable.</p>
<div class="qm-tablewrap"><table class="qm-kv">
<thead><tr><th>Allocator</th><th>Vol in</th><th>Vol out</th><th>Drift %</th>
<th>Max weight</th><th>Short</th><th>Effective N</th></tr></thead>
<tbody>
<tr><td>HRP (single)</td><td class="qm-num">0.1401</td><td class="qm-num">0.1419</td><td class="qm-num">+1.3</td><td class="qm-num">0.106</td><td class="qm-num">0.000</td><td class="qm-num">16.29</td></tr>
<tr><td>HRP (ward)</td><td class="qm-num">0.1419</td><td class="qm-num">0.1425</td><td class="qm-num">+0.4</td><td class="qm-num">0.110</td><td class="qm-num">0.000</td><td class="qm-num">16.73</td></tr>
<tr><td>MinVar</td><td class="qm-num">0.1311</td><td class="qm-num">0.1489</td><td class="qm-num">+13.6</td><td class="qm-num">0.229</td><td class="qm-num">-0.112</td><td class="qm-num">7.37</td></tr>
<tr><td>MinVar long-only</td><td class="qm-num">0.1325</td><td class="qm-num">0.1460</td><td class="qm-num">+10.2</td><td class="qm-num">0.206</td><td class="qm-num">0.000</td><td class="qm-num">9.54</td></tr>
<tr><td>MinVar shrunk 0.3</td><td class="qm-num">0.1330</td><td class="qm-num">0.1432</td><td class="qm-num">+7.7</td><td class="qm-num">0.169</td><td class="qm-num">-0.019</td><td class="qm-num">11.78</td></tr>
<tr><td>Equal weight</td><td class="qm-num">0.1474</td><td class="qm-num">0.1443</td><td class="qm-num">-2.1</td><td class="qm-num">0.050</td><td class="qm-num">0.000</td><td class="qm-num">20.00</td></tr>
</tbody></table></div>
<p>The finding is <em>drift</em>, not outperformance. Minimum variance achieves
the lowest in-sample volatility &mdash; it is solving for exactly that &mdash;
and then gives most of it back: +13.6% out of sample against HRP's +1.3%. The
in-sample number is a promise the out-of-sample number does not keep.</p>
<p class="qm-note">One synthetic panel, one seed. Out-of-sample Sharpe was
negative for every allocator on this panel, which is why none is quoted as a
performance result. This illustrates an estimation-error mechanism; it is not
evidence that HRP beats mean-variance in general.</p>''') + sec(
    'robustness', 'Robustness: what would change the conclusion', '''
<p><strong>Shrinkage closes most of the gap.</strong> A Ledoit-Wolf-style
shrunk covariance takes minimum variance from +13.6% drift to +7.7%. Comparing
HRP against an unconstrained, unshrunk optimiser overstates its advantage, and
the shrunk row is included here for exactly that reason.</p>
<p><strong>Equal weight is not embarrassed.</strong> The 1/N portfolio drifts
<em>-2.1%</em> and is the most diversified allocator in the table. DeMiguel,
Garlappi and Uppal (2009) is the standing warning that sophistication has to
earn its place against it.</p>
<p><strong>Linkage is a modelling choice.</strong> Single and Ward linkage
produce different trees and different weights (+1.3% vs +0.4% here). The choice
should be disclosed with the result.</p>
<p><strong>One seed is one seed.</strong> These numbers come from a single
synthetic panel. Change the seed, the asset count or the correlation structure
and the magnitudes move; the direction is the part supported by the wider
literature, not this table.</p>''') + sec(
    'costs', 'Turnover and transaction costs', '''
<p>Concentration is a cost story as much as a risk story. Minimum variance puts
22.9% in a single asset and holds &minus;11.2% short, with an effective breadth
of 7.4 names out of 20; HRP holds a 10.6% maximum, no shorts, and an effective
16.3 names. A concentrated, unstable weight vector is the one that generates
large rebalancing trades exactly when correlations move.</p>
<p>The comparison above deliberately holds weights fixed out of sample, so
<strong>no rebalancing cost is included in any figure in this paper</strong>.
That flatters every allocator, and it flatters the least stable one most. A
realistic assessment would apply the
<a href="/paper-slippage-latency-modeling.html">spread plus square-root impact
model</a> to the turnover each method generates &mdash; work this package does
not yet do, and the reason no net-of-cost claim appears here.</p>''')

# ---------------------------------------------------------------------------
PSR = sec('assumptions', 'Assumptions', '''
<ul>
<li><strong>Returns are independent.</strong> PSR corrects for skewness and
kurtosis but assumes serial independence. Autocorrelated returns &mdash; which
is what smoothed or illiquid marks produce &mdash; understate the true standard
error and inflate PSR.</li>
<li><strong>The benchmark is chosen before looking.</strong> PSR asks whether
the true Sharpe exceeds SR*. Setting SR* to zero after seeing the result is the
most common way the statistic is abused.</li>
<li><strong>The track record is the whole track record.</strong> The formula
takes <em>n</em> at face value. If the sample begins after a bad year was
dropped, no correction can recover it.</li>
<li><strong>One strategy, one test.</strong> PSR says nothing about how many
variants were tried. That is what the
<a href="/learn/deflated-sharpe-ratio.html">Deflated Sharpe Ratio</a>
addresses.</li>
</ul>''') + sec('robustness', 'Robustness: what would change the conclusion', '''
<p><strong>Trial count dominates everything else.</strong> The same Sharpe of
1.50 gives PSR 1.0000 against a zero benchmark, DSR 0.8736 after 100 trials,
and DSR 0.2671 after 1,000. Nothing about the strategy changes between those
numbers &mdash; only the honesty of the accounting. A PSR quoted without a
trial count is close to meaningless.</p>
<p><strong>Kurtosis matters more than intuition suggests.</strong> The kurtosis
term does not vanish at the normal value of 3. A published worked example on
this page previously got that wrong, giving denominators of 1.000 and 2.318
against the correct 1.4577 and 2.4850; the correction is disclosed rather than
silently patched. Every intermediate value is now shown so the arithmetic can
be checked by hand or against <code>scipy</code>.</p>
<p><strong>Short records cannot be rescued.</strong> The
<span class="qm-num">&radic;(n&minus;1)</span> factor means a high Sharpe over
a few dozen observations stays statistically weak no matter how attractive the
point estimate is.</p>''') + sec(
    'costs', 'Gross versus net Sharpe', '''
<p>PSR is a statement about the return series you feed it, and nothing more. A
gross-of-cost series produces a gross-of-cost PSR, and the gap between the two
widens with turnover: a high-frequency strategy can carry a comfortable gross
PSR and a negative net Sharpe.</p>
<p>Before computing PSR, subtract realistic costs &mdash; spread, market impact
and delay &mdash; using something like the
<a href="/paper-slippage-latency-modeling.html">square-root impact model</a>.
Applying a statistical significance test to a return stream that could not have
been captured is precision applied to the wrong quantity.</p>''')

# ---------------------------------------------------------------------------
SLIPPAGE = sec('assumptions', 'Assumptions', '''
<ul>
<li><strong>Impact scales with the square root of participation.</strong> The
model treats impact as proportional to volatility times the square root of
order size over daily volume. It is an empirical regularity across venues and
decades, not a law, and it fits large institutional orders better than small
ones.</li>
<li><strong>Volume is forecastable enough to plan against.</strong>
Participation rate is computed against expected daily volume. On a news day the
denominator is wrong in the direction that flatters the estimate.</li>
<li><strong>Spread is paid on entry and exit.</strong> Half-spread each way is
the floor for a liquidity-taking strategy, before any impact.</li>
<li><strong>Delay cost is proportional to signal decay.</strong> The cost of
waiting is only estimable if you know how fast the alpha decays, which most
backtests never measure.</li>
</ul>''') + sec('robustness', 'Robustness: what would change the conclusion', '''
<p><strong>A single flat cost assumption is the most consequential modelling
error in most backtests.</strong> Using a fixed number of basis points makes
cost independent of size, volatility and liquidity &mdash; the three things it
actually depends on &mdash; and the error grows with turnover, so it punishes
exactly the strategies that look best gross.</p>
<p><strong>Impact coefficients are regime-dependent.</strong> The constant in
front of the square-root term is fitted, not universal. It widens in stress and
differs by venue, sector and market-cap band.</p>
<p><strong>Adverse selection sits outside this model.</strong> Spread plus
impact plus delay does not capture the cost of being filled by better-informed
flow. That component is what
<a href="/paper-vpin-order-flow-toxicity.html">VPIN</a> attempts to measure, and
ignoring it biases cost estimates downward for passive strategies specifically.</p>
<p><strong>QuantMedia has not validated these coefficients on its own
executions.</strong> This site runs no execution and holds no fill data, so
nothing here is calibrated against realised trading. The model is presented as
the standard framework with its parameters exposed, not as a fitted result.</p>''')

# ---------------------------------------------------------------------------
SPREAD = sec('assumptions', 'Assumptions', '''
<ul>
<li><strong>The Roll estimator assumes an efficient price plus bid-ask
bounce.</strong> Serial covariance of price changes is negative only because
trades alternate between bid and ask. Any genuine short-horizon momentum or
mean reversion in the efficient price contaminates the estimate.</li>
<li><strong>Trades are equally likely at bid and ask.</strong> Systematically
one-sided flow breaks the symmetry the estimator depends on.</li>
<li><strong>The spread is constant over the estimation window.</strong> It is
not, particularly around the open, the close and scheduled news.</li>
<li><strong>Quoted is not effective.</strong> Quoted spread is an upper bound;
executions inside the quote make the effective spread smaller, and the gap
between them is itself informative.</li>
</ul>''') + sec('robustness', 'Robustness: what would change the conclusion', '''
<p><strong>The estimator fails loudly and often.</strong> When the sample
covariance of consecutive price changes is positive, the Roll formula requires
the square root of a negative number and returns nothing. Published
implementations differ in how they handle it &mdash; discarding the window,
flooring at zero, or substituting a different estimator &mdash; and the choice
materially changes any average computed across many windows.</p>
<p><strong>Decomposition is model-dependent.</strong> Splitting the spread into
order-processing, inventory-holding and adverse-selection components requires a
structural model. Different models attribute the same observed spread quite
differently, so component shares should be read as model output, not
measurement.</p>
<p><strong>Tick-size regimes are not comparable.</strong> Spread series that
straddle a tick-size change, a decimalisation event or a venue-structure change
are measuring different things before and after.</p>''')

PAPERS = {
    'paper-vpin-order-flow-toxicity.html': VPIN,
    'paper-hierarchical-risk-parity.html': HRP,
    'paper-probabilistic-sharpe-ratio.html': PSR,
    'paper-slippage-latency-modeling.html': SLIPPAGE,
    'paper-bid-ask-spread-dynamics.html': SPREAD,
}


def main():
    changed = 0
    for name, block in PAPERS.items():
        p = ROOT / name
        if not p.exists():
            print(f'  MISSING {name}')
            continue
        h = p.read_text(encoding='utf-8')
        if MARKER in h:
            print(f'  [  -] {name}  already deepened')
            continue
        # Insert before the limitations section, so the page reads
        # assumptions -> results -> robustness -> costs -> limitations ->
        # references -> research record.
        anchor = '<div class="qm-sec" id="limitations">'
        if anchor not in h:
            print(f'  FAIL {name}: no limitations anchor')
            continue
        h = h.replace(anchor, block + anchor, 1)
        p.write_text(h, encoding='utf-8')
        changed += 1
        print(f'  [chg] {name}')

    print(f'\n{changed} paper(s) deepened')

    bad = []
    for name in PAPERS:
        p = ROOT / name
        if not p.exists():
            continue
        h = p.read_text(encoding='utf-8')
        if h.count('<div') != h.count('</div>'):
            bad.append(f'{name}: unbalanced div ({h.count("<div")}/{h.count("</div>")})')
        for need in ('id="assumptions"', 'id="robustness"'):
            if need not in h:
                bad.append(f'{name}: missing {need}')
    if bad:
        print('\n'.join('  ' + b for b in bad))
        sys.exit(1)
    print('verified: assumptions + robustness present, div tags balanced')


if __name__ == '__main__':
    main()
