"""Verification layer for the /reports/ pages.

These fragments are COMPOSED into the existing report pages (built from
page_content_examples.py) rather than published as parallel URLs. The report
URLs that already exist - /reports/, vpin-example, hrp-example,
psr-worked-example - are the canonical ones; a second set would be exactly the
duplicated-intent problem the site was rejected for.

Each method gets two fragments:

  *_VERDICT        prepended: the one-paragraph verdict and the dated record
  *_VERIFICATION   appended: defects found, limitations of the check, reproduce

EVERY NUMBER IS CONSOLE OUTPUT FROM THE SHIPPED CODE, OR ARITHMETIC THE READER
CAN REPEAT. The three defects documented were all found by executing the code
against known ground truth - which is the whole practice in one sentence.
"""

REPO = 'https://github.com/certurk23/certurk23.github.io'
CODE = REPO + '/tree/main/quantmedia-research'

# ---------------------------------------------------------------------------
INDEX_BODY = f'''
<p class="qm-lede">A verification report is evidence that an implementation of
a quantitative method does what the paper says &mdash; produced by running the
code against inputs whose correct answer is known in advance, and recording
what it got right, what it got wrong, and what was fixed.</p>

<div class="qm-answer"><span class="qm-answer-label">Why this exists</span>
<p>Language models now produce a plausible implementation of almost any finance
paper in seconds. What they cannot do is tell you whether it is correct. The
first report below documents a VPIN implementation that returned <em>zero</em>
toxicity for a perfectly one-sided tape &mdash; the opposite of the right
answer &mdash; and looked fine until it was tested. As generating code becomes
free, proving it correct is the part that keeps its value.</p></div>

<h2>Reports</h2>
<div class="qm-tablewrap"><table class="qm-kv">
<thead><tr><th>Method</th><th>Record</th><th>Verdict</th><th>Defects found</th></tr></thead>
<tbody>
<tr><td><a href="/reports/vpin-example.html">VPIN &mdash; order-flow toxicity</a></td>
    <td class="qm-num">v1.0 &middot; 2026-08</td><td>Passes after one fix</td><td class="qm-num">1 &mdash; degenerate tape</td></tr>
<tr><td><a href="/reports/hrp-example.html">Hierarchical Risk Parity</a></td>
    <td class="qm-num">v1.0 &middot; 2026-08</td><td>Passes after two fixes</td><td class="qm-num">2 &mdash; pandas 3 view; symmetry</td></tr>
<tr><td><a href="/reports/psr-worked-example.html">Probabilistic Sharpe Ratio</a></td>
    <td class="qm-num">v1.0 &middot; 2026-08</td><td>Published example was wrong; corrected</td><td class="qm-num">1 &mdash; kurtosis term</td></tr>
</tbody></table></div>

<h2>What a report contains</h2>
<ul>
<li><strong>Ground truth.</strong> How an input with a known correct answer was
constructed &mdash; usually synthetic, from a fixed seed, because real market
data never tells you what the right answer was.</li>
<li><strong>What was run.</strong> The exact commands, versions and seed.</li>
<li><strong>Results.</strong> The numbers the code produced, unedited.</li>
<li><strong>Defects.</strong> What was wrong, how it was detected, how it was
fixed, and the regression test that now guards it.</li>
<li><strong>Limitations.</strong> What the verification does <em>not</em>
establish. Passing on synthetic data proves the mechanism, not the market.</li>
<li><strong>Reproduce.</strong> Enough to get the same output on your machine.</li>
</ul>

<h2>Check it yourself, in one command</h2>
<p><code>python quantmedia-research/verify_examples.py</code> re-runs both
packages in a clean temporary directory and asserts that every shipped output
file matches to nine decimal places. If it passes on your machine, you hold the
same evidence this page describes. The runner and both packages are in the
<a href="{CODE}" rel="noopener" target="_blank">public repository</a>.</p>

<h2>Verify your own implementation</h2>
<p>If you have written or generated your own VPIN, HRP or PSR code, point it at
the synthetic inputs described in each report and compare. If you would like a
report written against <em>your</em> implementation &mdash; the same ground
truth, the same discipline, a dated document you can cite &mdash;
<a href="/contact.html">get in touch</a>. That is the service this site is being
built around.</p>

<div class="qm-related">
  <a href="/reproducibility.html">Implementations &amp; tests</a>
  <a href="/editorial-policy.html">Corrections policy</a>
  <a href="/author/cemil-erturk.html">Who verifies</a>
</div>
'''

# ---------------------------------------------------------------------------
def _record(path):
    return f'''
<div class="qm-def"><dl>
<dt>Verification record</dt><dd>v1.0 &middot; first run 16 August 2026 &middot; published as a report 4 September 2026</dd>
<dt>Implementation under test</dt><dd><code>{path}</code>, in the public repository</dd>
<dt>Environment</dt><dd>Python 3.11.9; numpy 2.4.6; pandas 3.0.5; scipy 1.17.1 &mdash; all newer than the package pins, so this doubles as a forward-compatibility check</dd>
<dt>Verifier</dt><dd><a href="/author/cemil-erturk.html">Cemil Ert&uuml;rk</a></dd>
<dt>Status</dt><dd>Independent. Not peer reviewed. Synthetic data only; no claim about any real security.</dd>
</dl></div>
'''

VPIN_VERDICT = '''
<div class="qm-answer"><span class="qm-answer-label">Verdict</span>
<p>The implementation reproduces the defining property of VPIN &mdash; a
rising reading under informed flow &mdash; on a tape where the informed
episode is known in advance: 0.3292 in the balanced segment against 0.6376 in
the informed segment, a ratio of 1.94&times;. It did so only after a defect in
its degenerate-case handling was found and fixed.</p></div>
''' + _record('quantmedia-research/vpin-order-flow-toxicity/vpin.py')

VPIN_VERIFICATION = '''
<h2>Defect found during verification</h2>
<div class="qm-answer"><span class="qm-answer-label">Degenerate tape returned the wrong sign</span>
<p>Bulk volume classification standardises each bucket&rsquo;s price change by
the dispersion of price changes. On a <em>monotone</em> tape &mdash; every trade
at a higher price than the last &mdash; that dispersion is zero, and the
original branch handled the division by splitting volume 50/50. So a perfectly
one-sided tape, the most toxic input imaginable, returned VPIN = 0. Exactly
backwards.</p>
<p><strong>Detection:</strong> a test constructing a monotone tape and asserting
VPIN &gt; 0.9. <strong>Fix:</strong> in the degenerate branch, classify by the
sign of the price change (up &rarr; buy, down &rarr; sell, flat &rarr; 50/50).
<strong>Guard:</strong> the test is one of 15 in <code>tests/test_vpin.py</code>.</p></div>

<h2>What this verification does not establish</h2>
<ul>
<li>It proves the estimator <em>responds</em> to imbalance as designed. It
proves nothing about whether VPIN forecasts volatility in real markets; that
is contested (Andersen &amp; Bondarenko, 2014) and outside what synthetic data
can settle.</li>
<li>The absolute level is method-dependent: BVC and the tick rule give 0.4410
and 0.1779 on identical data. No threshold such as &ldquo;toxic above 0.4&rdquo;
means anything without stating classifier, bucket size and window.</li>
<li>One seed, one tape. The direction of the result is robust to the seed; the
magnitudes are not claimed to be.</li>
</ul>

<h2>Reproduce</h2>
<p><code>python quantmedia-research/verify_examples.py</code> re-runs this
example in a clean directory and asserts the shipped CSV matches to nine
decimal places. Then <code>python tests/test_vpin.py</code> from
<code>quantmedia-research/</code>: expected 15 passed.</p>
'''

# ---------------------------------------------------------------------------
HRP_VERDICT = '''
<div class="qm-answer"><span class="qm-answer-label">Verdict</span>
<p>The allocator produces weights that sum to one, contain no shorts, and drift
far less out of sample than an unconstrained minimum-variance optimiser on the
same panel (+1.3% against +13.6%). Two defects were found and fixed before it
did, and one over-specified test was corrected rather than the code.</p></div>
''' + _record('quantmedia-research/hierarchical-risk-parity/hrp.py')

HRP_VERIFICATION = '''
<h2>Defects found during verification</h2>
<div class="qm-answer"><span class="qm-answer-label">1. Read-only array under pandas 3</span>
<p>The distance matrix was built by calling <code>np.fill_diagonal</code> on
<code>DataFrame.values</code>. pandas 3 returns a read-only view, so the call
raised. <strong>Fix:</strong> copy first. This is the kind of defect a
&ldquo;works on my machine&rdquo; implementation carries for years.</p></div>
<div class="qm-answer"><span class="qm-answer-label">2. Asymmetric distance matrix</span>
<p>Floating-point noise left the correlation-distance matrix very slightly
asymmetric, and <code>scipy.spatial.distance.squareform</code> rejects that.
<strong>Fix:</strong> symmetrise explicitly with <code>0.5&middot;(D + D&#x1D40;)</code>.</p></div>
<p>A third item was a test, not the code: an assertion that linkage methods
must differ was over-specified for one unlucky seed, on which single and Ward
linkage happened to agree. The methods were confirmed to differ on other seeds,
and the test was fixed rather than the implementation. Adjusting a bad test is
legitimate; adjusting a test to hide a real gap is not.</p>

<h2>What this verification does not establish</h2>
<ul>
<li>One synthetic panel, one seed. It illustrates the estimation-error
mechanism; it is not evidence that HRP beats mean-variance in general.</li>
<li>No transaction costs anywhere in the comparison. Weights are held fixed,
which flatters every allocator and the least stable one most.</li>
<li>Out-of-sample Sharpe was negative for every allocator on this panel, which
is why none is reported as a performance figure.</li>
</ul>

<h2>Reproduce</h2>
<p><code>python quantmedia-research/verify_examples.py</code> asserts
<code>outputs/comparison.csv</code> and <code>outputs/weights.csv</code> match
the committed files. Then <code>python tests/test_hrp.py</code>: expected 13
passed.</p>
'''

# ---------------------------------------------------------------------------
PSR_VERDICT = '''
<div class="qm-answer"><span class="qm-answer-label">Verdict</span>
<p>The worked example previously published on this site was arithmetically
wrong, for months. It was found by computing it rather than reading it,
corrected against <code>scipy</code>, and every intermediate value is now
shown so it can be checked by hand.</p></div>
''' + _record('tools/probabilistic-sharpe-ratio-calculator.html and the worked example on the paper')

PSR_VERIFICATION = '''
<h2>Defect found during verification</h2>
<div class="qm-tablewrap"><table class="qm-kv">
<thead><tr><th>Quantity (SR 1.50, SR* 0, n 24)</th><th>As originally published</th><th>Correct</th></tr></thead>
<tbody>
<tr><td>Denominator, &gamma;&#8321; = 0, &gamma;&#8322; = 3</td><td class="qm-num">1.000</td><td class="qm-num">1.4577</td></tr>
<tr><td>Denominator, &gamma;&#8321; = &minus;1.20, &gamma;&#8322; = 7.00</td><td class="qm-num">2.318</td><td class="qm-num">2.4850</td></tr>
<tr><td>z-statistic (skewed, fat-tailed case)</td><td class="qm-num">&mdash;</td><td class="qm-num">2.8955</td></tr>
<tr><td>PSR (skewed, fat-tailed case)</td><td class="qm-num">&mdash;</td><td class="qm-num">0.9981</td></tr>
</tbody></table></div>
<div class="qm-answer"><span class="qm-answer-label">The kurtosis term does not vanish at &gamma;&#8322; = 3</span>
<p>The original example treated the &ldquo;normal&rdquo; case as having a
denominator of exactly 1, as though zero excess kurtosis removed the term. It
does not: the formula uses (&gamma;&#8322; &minus; 1)/4, which at
&gamma;&#8322; = 3 is 0.5, so the denominator is
&radic;(1 + 0.5&middot;1.5&sup2;) = &radic;2.125 = <strong>1.4577</strong>. The same
slip propagated to the skewed case: &radic;(1 + 1.80 + 1.5&middot;2.25) =
&radic;6.175 = <strong>2.4850</strong>, not 2.318.</p>
<p><strong>Detection:</strong> evaluating the formula in <code>scipy</code>
instead of trusting the prose. <strong>Fix:</strong> paper, explainer and
calculator now agree and show every intermediate. <strong>Guard:</strong> the
calculator computes rather than quotes, and <code>scripts/test_psr.js</code>
exercises it.</p></div>

<h2>Why it matters</h2>
<p>PSR is a test people use to decide whether a backtest is trustworthy. An
implementation that understates the denominator overstates the z-statistic and
reports more confidence than the data supports &mdash; in the direction that
makes bad strategies look good.</p>

<h2>What this verification does not establish</h2>
<ul>
<li>This verifies arithmetic, not statistical assumptions. PSR assumes
serially independent returns; on smoothed or illiquid marks it over-reports.</li>
<li>It says nothing about how many strategy variants were tried &mdash; that is
the <a href="/learn/deflated-sharpe-ratio.html">Deflated Sharpe Ratio</a>&rsquo;s job.</li>
</ul>

<h2>Reproduce</h2>
<p><code>from scipy.stats import norm; norm.cdf(1.5*23**0.5/2.4850)</code>
&rarr; 0.9981. Or open the
<a href="/tools/probabilistic-sharpe-ratio-calculator.html">calculator</a> with
SR 1.50, SR* 0, n 24, skew &minus;1.20, kurtosis 7.00.</p>
'''
