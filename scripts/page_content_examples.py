"""Free worked examples backed by the runnable research packages."""

REPO = 'https://github.com/certurk23/certurk23.github.io'
CODE = REPO + '/tree/70ae45c/quantmedia-research'


def record(path):
    return f'''
<div class="qm-def"><dl>
<dt>Reproduction record</dt><dd>Checked 4 September 2026. Seed: <code>20260808</code>.</dd>
<dt>Source</dt><dd><a href="{CODE}/{path}">{path}</a> at revision <code>70ae45c</code>.</dd>
<dt>Environment used</dt><dd>Python 3.11.9, NumPy 2.4.6, pandas 3.0.5, SciPy 1.17.1.</dd>
<dt>Data</dt><dd>Synthetic. These examples test the implementation and illustrate the method; they do not measure trading performance on real securities.</dd>
</dl></div>'''


INDEX_BODY = f'''
<p class="qm-lede">Follow a quantitative result from its inputs to its output.
These free examples pair the explanation with runnable code, expected results
and the limitations that matter when interpreting them.</p>
<div class="qm-answer"><span class="qm-answer-label">Choose a question</span>
<p>Use PSR to examine a Sharpe estimate, VPIN to explore trade classification,
or HRP to compare portfolio allocations. The examples require no account or
paid data feed.</p></div>
<ul class="qm-related">
<li><a href="/reports/psr-worked-example.html">PSR: check every step of the calculation</a>
<span>Why skewness, kurtosis and the benchmark change the answer. Try the same inputs in the free calculator.</span></li>
<li><a href="/reports/vpin-example.html">VPIN: one tape, two different readings</a>
<span>Bulk volume classification and the tick rule on the same 20,000 synthetic trades. Includes 15 tests.</span></li>
<li><a href="/reports/hrp-example.html">HRP: compare six allocation methods</a>
<span>In-sample and out-of-sample volatility on a 20-asset synthetic panel. Includes 13 tests.</span></li>
</ul>
<h2>Run the examples</h2>
<p>The <a href="{REPO}/tree/main/quantmedia-research">GitHub research directory</a>
contains the code, sample data and expected CSV output. Start with the
<a href="/reproducibility.html">installation instructions and implementation index</a>.
After installing the dependencies, the Python examples run offline.</p>
<h2>What these checks establish</h2>
<p>Known inputs help expose implementation errors: lost volume in a bucket,
weights that fail to sum to one, or a missing term in a formula. A passing test
supports the behavior it checks. It does not establish that a method predicts
future prices, survives transaction costs or generalizes beyond the example.</p>
<p>All examples and tools are freely accessible. For background, browse the
<a href="/papers.html">research library</a>; for data coverage and corrections,
read the <a href="/editorial-policy.html">editorial policy</a>.</p>
'''

VPIN_BODY = '''
<p class="qm-lede">On the same synthetic tape, mean VPIN is 0.4410 with bulk
volume classification and 0.1779 with the tick rule. The classifier changes
the reading substantially, so a VPIN threshold needs more context than a number.</p>
''' + record('vpin-order-flow-toxicity') + f'''
<h2>Set up the experiment</h2>
<p>The generator creates 20,000 trades with total volume 5,344,047. A segment
with one-sided flow is inserted into an otherwise balanced tape. Both classifiers
receive the same trades, bucket size of 21,376 and rolling window of 50 buckets.</p>
<div class="qm-formula">cd quantmedia-research/vpin-order-flow-toxicity
python example.py</div>
<h2>Compare the output</h2>
<div class="qm-tablewrap"><table class="qm-kv">
<thead><tr><th>Measure</th><th>Bulk volume classification</th><th>Tick rule</th></tr></thead>
<tbody>
<tr><td>Complete buckets</td><td>250</td><td>250</td></tr>
<tr><td>Mean VPIN</td><td>0.4410</td><td>0.1779</td></tr>
<tr><td>Minimum</td><td>0.2805</td><td>0.1247</td></tr>
<tr><td>Maximum</td><td>0.8257</td><td>0.2918</td></tr>
</tbody></table></div>
<p>For bulk volume classification, the mean in the balanced segment is
<strong>0.3292</strong>, compared with <strong>0.6376</strong> in the planted
one-sided segment: a ratio of <strong>1.94</strong>. This describes the two
segments in this tape, not a forecast accuracy or trading return.</p>
<p>The buckets account for 5,344,000 volume units. The remaining <strong>47</strong>
units are in an incomplete final bucket and are excluded by design. The console
rounds this coverage to 100.0%; it is not exactly 100%.</p>
<h2>What to inspect in the code</h2>
<p>Bulk volume classification estimates buy and sell volume from standardized
bucket price changes. The tick rule uses trade-to-trade price direction. Neither
method observes the true identity or intent of a trader. Their difference here
shows why changing the classification rule can change an apparent toxicity signal.</p>
<p>The tests also cover a special case: constant positive price changes have
zero dispersion. The implementation handles that case by price-change sign,
so a uniformly rising tape does not incorrectly receive a balanced 50/50 split.
Flat changes receive an even split.</p>
<div class="qm-formula"># From the repository root:
python quantmedia-research/tests/test_vpin.py
# Expected: 15 passed</div>
<h2>Limits and a useful next experiment</h2>
<p>This is one seed and one constructed tape. It does not verify that VPIN
predicts volatility in a real market. Try a different bucket size or window,
keeping the trade tape fixed, to separate estimator sensitivity from changes
in the underlying inputs. Such variants are experiments, not results reported here.</p>
<p>Download the <a href="{REPO}/blob/main/quantmedia-research/vpin-order-flow-toxicity/outputs/example_output.csv">expected bucket output</a>
or inspect the <a href="{CODE}/tests/test_vpin.py">tests at the checked revision</a>.</p>
<ul class="qm-related">
<li><a href="/learn/what-is-vpin.html">What is VPIN?</a><span>Definitions and a small numerical example</span></li>
<li><a href="/paper-vpin-order-flow-toxicity.html">VPIN research note</a><span>Method, literature and limitations</span></li>
<li><a href="/reports/">All worked examples</a></li>
</ul>
'''

HRP_BODY = '''
<p class="qm-lede">On this synthetic panel, HRP with single linkage has
out-of-sample volatility of 0.1419, compared with 0.1489 for unconstrained
minimum variance. Other baselines narrow that difference. The comparison is
useful precisely because all six results are visible.</p>
''' + record('hierarchical-risk-parity') + f'''
<h2>Set up the experiment</h2>
<p>The panel contains 20 assets. The first 120 periods fit the weights; the
next 400 evaluate them without refitting. The in-sample mean absolute correlation
is 0.240 and the covariance condition number is about 43.</p>
<div class="qm-formula">cd quantmedia-research/hierarchical-risk-parity
python compare_mvo.py</div>
<h2>Compare the output</h2>
<p>Volatility is annualized in the example using 252 periods per year. Drift is
100 &times; (out-of-sample volatility / in-sample volatility &minus; 1), calculated
before the displayed volatility figures are rounded.</p>
<div class="qm-tablewrap"><table class="qm-kv">
<thead><tr><th>Allocator</th><th>Volatility in</th><th>Volatility out</th><th>Drift</th></tr></thead>
<tbody>
<tr><td>HRP (single)</td><td>0.1401</td><td>0.1419</td><td>+1.3%</td></tr>
<tr><td>HRP (Ward)</td><td>0.1419</td><td>0.1425</td><td>+0.4%</td></tr>
<tr><td>Minimum variance</td><td>0.1311</td><td>0.1489</td><td>+13.6%</td></tr>
<tr><td>Minimum variance, clipped to long-only</td><td>0.1325</td><td>0.1460</td><td>+10.2%</td></tr>
<tr><td>Minimum variance, shrinkage 0.3</td><td>0.1330</td><td>0.1432</td><td>+7.7%</td></tr>
<tr><td>Equal weight</td><td>0.1474</td><td>0.1443</td><td>&minus;2.1%</td></tr>
</tbody></table></div>
<p>The long-only baseline clips negative weights and renormalizes the result.
It is a simple comparison, <strong>not a constrained optimization solver</strong>.
The full <a href="{REPO}/blob/main/quantmedia-research/hierarchical-risk-parity/outputs/comparison.csv">comparison CSV</a>
also includes concentration, short exposure, drawdown and Sharpe. Out-of-sample
Sharpe is negative for every allocator in this example.</p>
<h2>Read the result carefully</h2>
<p>Minimum variance has the lowest fitted volatility and the largest increase
outside the fitted sample. Shrinkage reduces that increase. Equal weight has a
small decrease; a negative drift is possible and is not an implementation error.</p>
<p>A small drift means the two volatility estimates are similar. It does not
by itself imply the highest return, the lowest risk or the best portfolio.
HRP single and Ward illustrate that even the linkage choice changes the result.</p>
<h2>Check the implementation</h2>
<p>The 13 tests include weights summing to one, nonnegative HRP weights,
distance-matrix properties, and a two-asset case with a known 80/20 allocation.
The implementation copies the correlation array before modifying it and
symmetrizes the distance matrix to handle floating-point noise.</p>
<div class="qm-formula"># From the repository root:
python quantmedia-research/tests/test_hrp.py
# Expected: 13 passed</div>
<h2>Limits and a useful next experiment</h2>
<p>This is one fixed-seed panel with no transaction costs and no weight refitting.
It does not establish which allocator wins across assets or market regimes.
Vary the training length while retaining a separate evaluation sample to explore
how much each method depends on its covariance estimate.</p>
<ul class="qm-related">
<li><a href="/learn/hrp-vs-mean-variance.html">HRP vs mean-variance</a><span>How the allocation methods differ</span></li>
<li><a href="/paper-hierarchical-risk-parity.html">HRP research note</a><span>Algorithm, references and assumptions</span></li>
<li><a href="/reports/">All worked examples</a></li>
</ul>
'''

PSR_BODY = '''
<p class="qm-lede">With an observed Sharpe of 1.50, 24 observations, skewness
of &minus;1.20 and kurtosis of 7.00, the Probabilistic Sharpe Ratio against
a zero benchmark is <strong>99.81%</strong>. Here is the arithmetic behind
that result, including the denominator that is easy to miscalculate.</p>
<div class="qm-answer"><span class="qm-answer-label">Use consistent units</span>
<p>Sharpe and the benchmark must be expressed at the observation frequency.
For monthly observations, use monthly Sharpe values; do not enter an annualized
Sharpe alongside a count of monthly returns. Kurtosis here is ordinary kurtosis,
where a normal distribution has value 3, not excess kurtosis.</p></div>
<h2>Inputs</h2>
<table class="qm-kv"><tbody>
<tr><th>Observed Sharpe SR</th><td>1.50 per observation period</td></tr>
<tr><th>Benchmark SR*</th><td>0.00 per observation period</td></tr>
<tr><th>Observations n</th><td>24</td></tr>
<tr><th>Skewness g1</th><td>&minus;1.20</td></tr>
<tr><th>Kurtosis g2</th><td>7.00</td></tr>
</tbody></table>
<h2>Calculate without intermediate rounding</h2>
<div class="qm-formula">denominator = sqrt(1 - g1*SR + ((g2 - 1)/4)*SR^2)
            = sqrt(1 + 1.80 + 1.5*2.25)
            = sqrt(6.175)
            = 2.484954727958

z = (SR - SR*) * sqrt(n - 1) / denominator
  = 1.5 * sqrt(23) / sqrt(6.175)
  = 2.8949208628

PSR = standard_normal_cdf(z)
    = 0.9981037293
    = 99.81% (rounded)</div>
<p>The normal-return case still has a kurtosis term. Setting skewness to zero
and kurtosis to 3 gives sqrt(1 + 0.5 &times; 1.50&sup2;) = <strong>1.4577</strong>,
not 1. Zero excess kurtosis does not remove (g2 &minus; 1)/4 from this formula.</p>
<h2>Change the question</h2>
<p>Raise the benchmark from 0 to 1 while keeping the other inputs fixed. The
z-statistic becomes 0.9650 and PSR falls to <strong>83.27%</strong>, below a
95% threshold. The observed record is the same; the claim being tested is stronger.</p>
<p><a href="/tools/probabilistic-sharpe-ratio-calculator.html">Open the free calculator with these default inputs</a>.
It calculates locally in your browser and displays both the denominator and z.</p>
<h2>Reproduce with Python</h2>
<div class="qm-formula">from math import erf, sqrt

sr, benchmark, n, skew, kurtosis = 1.5, 0.0, 24, -1.2, 7.0
den = sqrt(1 - skew*sr + ((kurtosis - 1)/4)*sr**2)
z = (sr - benchmark)*sqrt(n - 1)/den
psr = (1 + erf(z/sqrt(2)))/2
print(f"den={den:.10f}, z={z:.10f}, PSR={psr:.10f}")</div>
<p>This check uses Python's standard library. The browser calculator uses an
error-function approximation, so compare at the displayed precision rather
than requiring identical last digits.</p>
<h2>What the percentage does not mean</h2>
<p>PSR is not the probability of a profitable next trade. Its interpretation
depends on the statistical assumptions, including independent returns and
reliable moment estimates. It does not account for costs or the number of
strategy variants tried. Selection across many backtests needs a separate
correction such as the Deflated Sharpe Ratio.</p>
<p class="qm-note">Arithmetic checked 4 September 2026. The earlier worked
example printed z = 2.8955; the correct value rounded to four decimals is
2.8949. This correction leaves the displayed PSR of 99.81% unchanged.</p>
<ul class="qm-related">
<li><a href="/learn/what-is-probabilistic-sharpe-ratio.html">PSR explained</a></li>
<li><a href="/learn/deflated-sharpe-ratio.html">Deflated Sharpe Ratio</a><span>Accounting for multiple strategy trials</span></li>
<li><a href="/paper-probabilistic-sharpe-ratio.html">PSR research note and references</a></li>
<li><a href="/reports/">All worked examples</a></li>
</ul>
'''
