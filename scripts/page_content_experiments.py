"""Bodies for experiment notes: articles built on a runnable experiment in
quantmedia-research/, with every number taken from its committed output.

PSR_UNCERTAINTY_BODY: numbers from
quantmedia-research/psr-moment-uncertainty/outputs/summary.csv, run 15
September 2026 with numpy 2.5.2 / scipy 1.18.1, seed 20260915, 20,000
samples per scenario, 5,000 bootstrap resamples.
"""

PSR_UNCERTAINTY_BODY = """
<div class="qm-answer">
<span class="qm-answer-label">Short answer</span>
<p>A lot. At n = 24 the sample kurtosis that the Probabilistic Sharpe Ratio
plugs into its denominator has a standard deviation of about 0.74 even when
returns are normal, and on a fat-tailed distribution it typically reads 4 when
the truth is 7. For a strong edge (per-period SR 1.5) none of this matters:
the PSR is saturated near 1 whatever the inputs do. For a marginal edge (SR
0.5, true PSR 0.956) the plug-in PSR ranges from 0.70 to 1.00 across samples
of the same process, and a stationary bootstrap of one typical sample spans
0.86 to 0.9996. The closed form is exact arithmetic on inputs that are not
exact.</p>
</div>

<h2>Why this experiment exists</h2>
<p>The <a href="/reports/psr-worked-example.html">PSR verification report</a>
checks the closed-form arithmetic: denominator, z-statistic, probability. A
reader on r/quant pointed out the second-order problem hiding in the same
example: at n = 24 the kurtosis estimate itself is very noisy, so treating
&gamma;&#8322; = 7.00 as known treats the noisiest input as exact. The report
now says so in its limits. This note measures it, with a distribution whose
true moments are set to the worked example, so every estimate can be compared
with a known answer. Everything below is synthetic; nothing is a market
return.</p>

<h2>What the closed form assumes</h2>
<div class="qm-formula">z = (SR &minus; SR*) &middot; &radic;(n &minus; 1) / &radic;(1 &minus; &gamma;&#8321;&middot;SR + (&gamma;&#8322; &minus; 1)/4 &middot; SR&sup2;)<br>PSR = &Phi;(z)</div>
<p>SR, &gamma;&#8321; (skewness) and &gamma;&#8322; (Pearson kurtosis; a normal
distribution has 3, not 0) enter as point estimates. The formula is an
asymptotic approximation from Bailey and L&oacute;pez de Prado (2012); it says
nothing about how far those estimates sit from the population values at a
given n. Two different questions follow.</p>

<h2>Part A: how much the inputs move under normality</h2>
<p>20,000 samples of 24 standard-normal draws. The estimators are the biased
(population) skewness and kurtosis that <code>scipy.stats.skew</code> and
<code>kurtosis(fisher=False)</code> return by default; the choice matters at
this n and is stated for that reason.</p>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>Quantity at n = 24, normal returns</th><th>Monte Carlo</th><th>Finite-sample formula</th><th>Asymptotic</th></tr></thead>
<tbody>
<tr><td>SD of sample skewness &gamma;&#8321;</td><td class="qm-num">0.443</td><td class="qm-num">0.442</td><td class="qm-num">&radic;(6/n) = 0.500</td></tr>
<tr><td>SD of sample kurtosis &gamma;&#8322;</td><td class="qm-num">0.746</td><td class="qm-num">0.737</td><td class="qm-num">&radic;(24/n) = 1.000</td></tr>
<tr><td>5th&ndash;95th percentile of &gamma;&#8322; (true value 3)</td><td class="qm-num">1.90 &ndash; 4.16</td><td>&mdash;</td><td>&mdash;</td></tr>
<tr><td>SD of sample SR when the true SR is 0</td><td class="qm-num">0.215</td><td>&mdash;</td><td class="qm-num">1/&radic;n = 0.204</td></tr>
</tbody></table></div>
<p>The finite-sample formulas are the exact variances of the biased estimators
under normality, 6(n&minus;2)/((n+1)(n+3)) and 24n(n&minus;2)(n&minus;3)/((n+1)&sup2;(n+3)(n+5)).
The often-quoted &radic;(24/n) overstates the n = 24 spread by about a third,
and the direction of the reader's remark holds either way: a kurtosis reading
anywhere between roughly 2 and 4 is consistent with a normal distribution at
this sample size.</p>

<h2>Part B: a process with the worked example's moments</h2>
<p>To compare estimates with a known PSR the population must have SR 1.50,
skewness &minus;1.20 and kurtosis 7.00. A two-component normal mixture does
it: with probability 0.10 a &ldquo;bad regime&rdquo; N(0.145, 1.706&sup2;),
otherwise N(1.651, 0.749&sup2;), in units where the standard deviation is 1.
The four parameters are solved from the four moment equations; the solver's
residuals are below 10<sup>&minus;8</sup>. A second scenario shifts both
component means by &minus;1.0, which leaves variance, skewness and kurtosis
untouched and sets the true SR to 0.50: a marginal edge. Each scenario draws
20,000 samples of n = 24 and computes the plug-in PSR against SR* = 0.</p>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>n = 24, 20,000 samples</th><th>True SR 1.50 (worked example)</th><th>True SR 0.50 (marginal edge)</th></tr></thead>
<tbody>
<tr><td>True PSR (population moments)</td><td class="qm-num">0.9981</td><td class="qm-num">0.9560</td></tr>
<tr><td>Sample SR: mean, SD</td><td class="qm-num">1.660, 0.528</td><td class="qm-num">0.570, 0.300</td></tr>
<tr><td>Lo (2002) normal-theory SE of SR</td><td class="qm-num">0.298</td><td class="qm-num">0.217</td></tr>
<tr><td>Sample skewness: mean (true &minus;1.20)</td><td class="qm-num">&minus;0.67</td><td class="qm-num">&minus;0.68</td></tr>
<tr><td>Sample kurtosis: mean, SD (true 7.00)</td><td class="qm-num">4.22, 2.16</td><td class="qm-num">4.23, 2.15</td></tr>
<tr><td>Sample kurtosis: 5th&ndash;95th percentile</td><td class="qm-num">2.08 &ndash; 8.71</td><td class="qm-num">2.08 &ndash; 8.70</td></tr>
<tr><td>Plug-in PSR: median</td><td class="qm-num">1.0000</td><td class="qm-num">0.9806</td></tr>
<tr><td>Plug-in PSR: 5th&ndash;95th percentile</td><td class="qm-num">0.9850 &ndash; 1.0000</td><td class="qm-num">0.7038 &ndash; 1.0000</td></tr>
<tr><td>Samples with plug-in PSR below 0.90</td><td class="qm-num">0.0%</td><td class="qm-num">22.4%</td></tr>
<tr><td>Samples with plug-in PSR above the true PSR</td><td class="qm-num">76.9%</td><td class="qm-num">62.5%</td></tr>
<tr><td>Normal-only PSR (skew 0, kurtosis 3 assumed): median</td><td class="qm-num">1.0000</td><td class="qm-num">0.9927</td></tr>
</tbody></table></div>

<h2>What the table says</h2>
<ul>
<li><strong>The kurtosis estimate cannot see the tails.</strong> With 24
observations from a process whose kurtosis is 7, the sample kurtosis averages
4.2 and lands below 3 in a fifth of samples. The 10% bad regime simply does
not show up often enough in 24 draws. The closed form's correction for fat
tails is therefore systematically too small, which is one reason more than
half the plug-in values sit above the true PSR.</li>
<li><strong>The SR estimate is wider than normal theory says.</strong> Lo's
SE, &radic;((1 + SR&sup2;/2)/n), gives 0.298 at SR 1.5; the observed SD is
0.528. Fat tails widen the sampling distribution of SR itself, before any
PSR arithmetic. The naive 1/&radic;n = 0.204, which drops the SR&sup2;/2
term, is wrong by a factor of 2.6 here.</li>
<li><strong>At SR 1.5 the input noise is irrelevant.</strong> Every one of
the 20,000 samples gives a plug-in PSR above 0.985. The verification report's
example is a strong edge; its PSR of 0.9981 would survive any plausible error
in the moments.</li>
<li><strong>At SR 0.5 the point estimate is mostly noise.</strong> The same
process, 24 observations, gives PSR anywhere from 0.70 to 1.00. In 22% of
samples the analyst reports &ldquo;below 0.90&rdquo;; in most of the rest,
&ldquo;above 0.95&rdquo;. The same edge is called insignificant or near-certain
depending on which 24 months happened to be drawn.</li>
<li><strong>Ignoring skew and kurtosis makes it worse, but not by much at
this n.</strong> The normal-only median is 0.9927 against 0.9806 with the
estimated moments. The estimated moments are so noisy that they only partially
do their job.</li>
</ul>

<h2>One sample, bootstrapped</h2>
<p>Take the marginal-edge sample whose plug-in PSR sits at the median: SR
0.538, skewness &minus;0.64, kurtosis 3.97, PSR 0.9806. A stationary bootstrap
(Politis and Romano, 1994; 5,000 resamples, mean block length 3) recomputes
SR, skewness, kurtosis and PSR on each resample. The 5th, 50th and 95th
percentiles are <strong>0.859, 0.981 and 0.9996</strong>. The interval runs
from &ldquo;not significant at 10%&rdquo; to &ldquo;essentially certain&rdquo;.
That is the honest statement of what 24 observations of a marginal, fat-tailed
strategy support, and it is not what the single number 0.9806 suggests.</p>
<p>The block length does not matter here because the process is independent
across periods; it is included because a real return series is not, and the
same code applies to one.</p>

<h2>What this does not establish</h2>
<ul>
<li>One synthetic process, one seed, one n. Real return series are
autocorrelated, heteroskedastic and not stationary; all of that adds
uncertainty this experiment does not model.</li>
<li>The mixture is a device for hitting three target moments, not a model of
returns. Other distributions with the same moments would give different
sampling behaviour for the estimators.</li>
<li>The per-period SR of 1.5 in the worked example is far above anything
plausible at monthly frequency; it was kept because it is the published
example's input, and the second scenario exists to show a realistic
regime.</li>
<li>Bias-corrected estimators of skewness and kurtosis would change the
numbers in Part A and the kurtosis rows in Part B; the biased ones were used
because they are what the common libraries return by default.</li>
</ul>

<h2>Reproduce</h2>
<div class="qm-formula">cd quantmedia-research/psr-moment-uncertainty<br>python experiment.py<br>python ../tests/test_psr_uncertainty.py&nbsp;&nbsp;# expected: 6 passed</div>
<p>The script writes <code>outputs/summary.csv</code>, <code>summary.json</code>
and the 20,000 plug-in PSR draws per scenario. Runtime about six seconds.
Because NumPy does not promise bit-identical random streams across minor
versions, the tests pin the claims above with tolerances rather than every
decimal; the committed output was produced with numpy 2.5.2 and scipy 1.18.1.
<a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research/psr-moment-uncertainty">Code and output on GitHub</a>.</p>

<h2>References</h2>
<ul>
<li>Bailey, D. H. and L&oacute;pez de Prado, M. (2012). The Sharpe Ratio Efficient Frontier. <em>Journal of Risk</em>, 15(2).</li>
<li>Lo, A. W. (2002). The Statistics of Sharpe Ratios. <em>Financial Analysts Journal</em>, 58(4), 36&ndash;52.</li>
<li>Politis, D. N. and Romano, J. P. (1994). The Stationary Bootstrap. <em>Journal of the American Statistical Association</em>, 89(428), 1303&ndash;1313.</li>
<li>Joanes, D. N. and Gill, C. A. (1998). Comparing measures of sample skewness and kurtosis. <em>The Statistician</em>, 47(1), 183&ndash;189 (finite-sample variances of the estimators).</li>
</ul>
"""

# Numbers from quantmedia-research/vpin-classifier-sensitivity/outputs/,
# run 15 September 2026 (numpy 2.5.2, pandas 3.0.5). The 250-bucket /
# window-50 cells reproduce the VPIN verification report exactly.
VPIN_NOISE_FLOOR_BODY = """
<div class="qm-answer">
<span class="qm-answer-label">Short answer</span>
<p>On the same 20,000-trade synthetic tape, VPIN averages 0.4410 with bulk
volume classification (BVC) and 0.1779 with the tick rule. Neither number
measures toxicity on its own: each classifier has a noise floor, the VPIN it
reports when there is nothing to detect, and the floors differ by
construction. BVC maps every bucket's net price change through a CDF, so on
pure noise it reads about 0.45 (exactly 0.50 with a normal CDF). The tick
rule sums roughly 80 trade signs per bucket that mostly cancel, so its floor
is &radic;(2/&pi;)/&radic;k &asymp; 0.13. Both predictions land within 0.01 of the
control tape. Bucket size moves the tick rule's level and barely touches
BVC's; BVC's t-distribution setting moves its level and barely touches its
detection ratio. A VPIN threshold quoted without classifier, bucket size and
window is not a number.</p>
</div>

<h2>The question the verification report left open</h2>
<p>The <a href="/reports/vpin-example.html">VPIN verification report</a>
showed the estimator responding to a planted informed episode and noted, as a
limit, that the two classifiers give 0.4410 and 0.1779 on identical data. It
suggested varying bucket size and window as the next experiment. This note
does that, and first explains the gap, with the same tape, the same
implementation and a control tape that has the planted drift removed.
Everything is synthetic.</p>

<h2>Setup</h2>
<p>The tape is the report's: 20,000 trades, Gaussian price steps with
&sigma; = 0.01, lognormal sizes, a persistent upward drift of 0.004 per
trade on trades 8,000&ndash;11,999. The control tape subtracts the cumulative
drift from the price path and keeps every step and every volume, so the two
tapes differ only in the informed episode. The published setting is 250
equal-volume buckets of 21,376 shares (80 trades per bucket on average) and
a 50-bucket window. &ldquo;Quiet&rdquo; is the mean VPIN over buckets
15&ndash;35% of the way through the tape, &ldquo;active&rdquo; over
42&ndash;62%, as in the report.</p>

<h2>Part A: where the gap comes from</h2>
<p>VPIN over a window of equal-volume buckets is the average per-bucket
imbalance ratio |V<sub>buy</sub> &minus; V<sub>sell</sub>| / V. The two
classifiers produce that ratio in different ways.</p>
<ul>
<li><strong>BVC</strong> assigns each bucket a buy fraction T(&Delta;P /
&sigma;<sub>&Delta;P</sub>) using a Student-t CDF, so the imbalance ratio is
|2T(z) &minus; 1| for one standardised price change z per bucket. If z were
standard normal and T the normal CDF, T(z) would be uniform on [0, 1] and the
expected ratio would be exactly 0.5, regardless of bucket size, tape or
anything else. With the t-distribution at 3 degrees of freedom the Monte
Carlo expectation is 0.449.</li>
<li><strong>The tick rule</strong> signs each trade by its price change and
sums signed volume within the bucket. With k independent fair signs the
expected absolute sum is &radic;(2/&pi;)&middot;&radic;(&sum;v<sub>i</sub>&sup2;),
which divided by bucket volume gives the floor. Computed on the actual bucketed
volumes of this tape, that is 0.131.</li>
</ul>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>250 buckets, window 50</th><th>BVC (dof 3)</th><th>Tick rule</th></tr></thead>
<tbody>
<tr><td>Control tape (no informed episode): mean VPIN</td><td class="qm-num">0.4579</td><td class="qm-num">0.1358</td></tr>
<tr><td>Predicted noise floor</td><td class="qm-num">0.449</td><td class="qm-num">0.131</td></tr>
<tr><td>Informed tape: mean VPIN</td><td class="qm-num">0.4410</td><td class="qm-num">0.1779</td></tr>
<tr><td>Informed tape: quiet / active</td><td class="qm-num">0.3292 / 0.6376</td><td class="qm-num">0.1386 / 0.2259</td></tr>
<tr><td>Detection ratio (active / quiet)</td><td class="qm-num">1.94&times;</td><td class="qm-num">1.63&times;</td></tr>
<tr><td>Per-bucket imbalance ratio, informed tape: median / 90th pct</td><td class="qm-num">0.37 / 0.86</td><td class="qm-num">0.14 / 0.33</td></tr>
</tbody></table></div>
<p>Two things follow. First, the difference between 0.44 and 0.18 is almost
entirely the difference between the two floors, 0.45 and 0.13; the informed
episode adds a comparable amount to each. Second, BVC's quiet reading on the
informed tape (0.3292) is <em>below</em> its own floor (0.4579). That is not a
paradox: BVC standardises by the dispersion of price changes across the whole
tape, and the informed episode inflates that dispersion from 0.0872 to 0.1492.
Quiet buckets are then divided by a larger &sigma;, their z shrinks, and their
imbalance reads lower. The level of BVC in one part of a tape depends on what
happened elsewhere on it.</p>

<h2>Part B: bucket size and window</h2>
<p>Bucket counts 50, 100, 250, 500 and 1,000 (400 down to 20 trades per
bucket) crossed with windows 10, 25, 50 and 100 buckets, on the informed
tape. Cells where the window is longer than the quiet segment have no quiet
mean and are omitted.</p>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>Buckets (trades each)</th><th>Window</th><th>BVC mean</th><th>BVC quiet / active</th><th>BVC ratio</th><th>Tick mean</th><th>Tick quiet / active</th><th>Tick ratio</th></tr></thead>
<tbody>
<tr><td>50 (400)</td><td class="qm-num">10</td><td class="qm-num">0.3507</td><td class="qm-num">0.178 / 0.603</td><td class="qm-num">3.39</td><td class="qm-num">0.1161</td><td class="qm-num">0.075 / 0.202</td><td class="qm-num">2.69</td></tr>
<tr><td>100 (200)</td><td class="qm-num">10</td><td class="qm-num">0.3760</td><td class="qm-num">0.240 / 0.797</td><td class="qm-num">3.33</td><td class="qm-num">0.1301</td><td class="qm-num">0.095 / 0.254</td><td class="qm-num">2.69</td></tr>
<tr><td>100 (200)</td><td class="qm-num">25</td><td class="qm-num">0.4079</td><td class="qm-num">0.242 / 0.578</td><td class="qm-num">2.39</td><td class="qm-num">0.1372</td><td class="qm-num">0.096 / 0.181</td><td class="qm-num">1.89</td></tr>
<tr><td>250 (80)</td><td class="qm-num">10</td><td class="qm-num">0.4125</td><td class="qm-num">0.325 / 0.793</td><td class="qm-num">2.44</td><td class="qm-num">0.1696</td><td class="qm-num">0.146 / 0.283</td><td class="qm-num">1.94</td></tr>
<tr><td>250 (80)</td><td class="qm-num">50</td><td class="qm-num">0.4410</td><td class="qm-num">0.329 / 0.638</td><td class="qm-num">1.94</td><td class="qm-num">0.1779</td><td class="qm-num">0.139 / 0.226</td><td class="qm-num">1.63</td></tr>
<tr><td>500 (40)</td><td class="qm-num">50</td><td class="qm-num">0.4512</td><td class="qm-num">0.366 / 0.704</td><td class="qm-num">1.92</td><td class="qm-num">0.2128</td><td class="qm-num">0.176 / 0.291</td><td class="qm-num">1.65</td></tr>
<tr><td>1,000 (20)</td><td class="qm-num">50</td><td class="qm-num">0.4487</td><td class="qm-num">0.386 / 0.641</td><td class="qm-num">1.66</td><td class="qm-num">0.2773</td><td class="qm-num">0.246 / 0.349</td><td class="qm-num">1.42</td></tr>
<tr><td>1,000 (20)</td><td class="qm-num">100</td><td class="qm-num">0.4536</td><td class="qm-num">0.392 / 0.623</td><td class="qm-num">1.59</td><td class="qm-num">0.2781</td><td class="qm-num">0.246 / 0.335</td><td class="qm-num">1.36</td></tr>
</tbody></table></div>
<p>The full 34-cell grid is in <code>outputs/grid.csv</code>. Reading it:</p>
<ul>
<li><strong>The tick rule's level is a function of trades per bucket.</strong>
From 200 trades per bucket to 20 its mean rises from 0.13 to 0.28, because
fewer signs cancel. Its floor scales like 1/&radic;k. Any tick-rule VPIN
threshold therefore only means something for one bucket size.</li>
<li><strong>BVC's level barely moves</strong> (0.35 to 0.45 across the same
range, 0.41 to 0.45 for windows of 25 or more). One z per bucket is one draw
from roughly the same distribution whatever the bucket size; the floor does
not depend on k.</li>
<li><strong>Detection favours few, large buckets and short windows.</strong>
The best active/quiet ratio in the grid is 3.39&times; (BVC, 50 buckets,
window 10); the published 250/50 setting gives 1.94&times;; 1,000 buckets
with a 100-bucket window gives 1.59&times;. Small buckets dilute the episode
across more readings and long windows average it away. The price of the
sharpest setting is 10 readings per window on a 50-bucket tape, which is not
a series anyone would trade on.</li>
<li><strong>BVC beats the tick rule on detection in every cell</strong> of this
tape, by 0.2&ndash;0.7 in ratio terms. On this tape; the informed episode is
a smooth drift, which is the case BVC is designed for.</li>
</ul>

<h2>Part C: BVC's degrees of freedom</h2>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>Student-t dof</th><th>Informed tape: mean</th><th>Quiet / active</th><th>Ratio</th><th>Control tape: mean</th><th>Predicted floor</th></tr></thead>
<tbody>
<tr><td class="qm-num">1</td><td class="qm-num">0.3664</td><td class="qm-num">0.275 / 0.528</td><td class="qm-num">1.92</td><td class="qm-num">0.3785</td><td class="qm-num">0.372</td></tr>
<tr><td class="qm-num">3 (published)</td><td class="qm-num">0.4410</td><td class="qm-num">0.329 / 0.638</td><td class="qm-num">1.94</td><td class="qm-num">0.4579</td><td class="qm-num">0.449</td></tr>
<tr><td class="qm-num">30 (&asymp; normal)</td><td class="qm-num">0.4822</td><td class="qm-num">0.361 / 0.695</td><td class="qm-num">1.93</td><td class="qm-num">0.5042</td><td class="qm-num">0.494</td></tr>
</tbody></table></div>
<p>The degrees-of-freedom setting shifts the level by 0.12 end to end and
leaves the detection ratio at 1.92&ndash;1.94. Heavier tails in the CDF
compress |2T(z) &minus; 1| for moderate z, lowering the floor, without changing
how much the informed episode stands out relative to it. Papers that quote a
VPIN &ldquo;alert level&rdquo; rarely state the dof; it is worth 0.12 here.</p>

<h2>What this does not establish</h2>
<ul>
<li>One synthetic tape with one shape of informed episode (a steady drift).
Informed flow that arrives as bursts, or as volume without a price trend,
would change which classifier detects it and by how much.</li>
<li>Nothing here says whether VPIN forecasts volatility in real markets, the
question Andersen and Bondarenko (2014) raised; a synthetic tape cannot
address it.</li>
<li>The tick-rule floor prediction assumes independent signs. Real tick-rule
signs are autocorrelated (unchanged prices inherit the previous sign); on
this tape the observed floor is 0.136 against 0.131 predicted, so the effect
is small here and could be larger elsewhere.</li>
<li>Level is not detectability. Every table reports both, and the practical
use of VPIN depends on the second.</li>
</ul>

<h2>Reproduce</h2>
<div class="qm-formula">cd quantmedia-research/vpin-classifier-sensitivity<br>python experiment.py<br>python ../tests/test_vpin_sensitivity.py&nbsp;&nbsp;# expected: 6 passed</div>
<p>Runtime about two seconds. The 250-bucket, window-50 cells must reproduce
the verification report's 0.4410 / 0.1779 / 0.3292 / 0.6376 exactly; the
first test checks that. <a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research/vpin-classifier-sensitivity">Code and output on GitHub</a>.</p>

<h2>References</h2>
<ul>
<li>Easley, D., L&oacute;pez de Prado, M. and O&rsquo;Hara, M. (2012). Flow Toxicity and Liquidity in a High-Frequency World. <em>Review of Financial Studies</em>, 25(5), 1457&ndash;1493.</li>
<li>Easley, D., L&oacute;pez de Prado, M. and O&rsquo;Hara, M. (2016). Discerning Information from Trade Data. <em>Journal of Financial Economics</em>, 120(2), 269&ndash;285 (bulk volume classification).</li>
<li>Andersen, T. G. and Bondarenko, O. (2014). VPIN and the Flash Crash. <em>Journal of Financial Markets</em>, 17, 1&ndash;46.</li>
<li>Lee, C. M. C. and Ready, M. J. (1991). Inferring Trade Direction from Intraday Data. <em>Journal of Finance</em>, 46(2), 733&ndash;746 (the tick rule).</li>
</ul>
"""

# Numbers from quantmedia-research/hrp-drift-anatomy/outputs/, run 15
# September 2026 (numpy 2.5.2, pandas 3.0.5). The published-split rows
# reproduce the HRP verification report exactly.
HRP_DRIFT_BODY = """
<div class="qm-answer">
<span class="qm-answer-label">Short answer</span>
<p>Because the panel is generated from a known factor model, its true
covariance is available, and every allocator's out-of-sample volatility drift
can be split into <em>optimism</em> (the in-sample estimate sits below the true
volatility of the chosen weights) and <em>luck</em> (the test window's own
noise). Minimum variance's +13.6% is +13.5% optimism and +0.1% luck: the
optimiser fitted the estimation error in a 120-period sample covariance and
reported a volatility it could never have. HRP's +1.3% is +2.8% optimism and
&minus;1.5% luck. Across 50 seeds HRP drifts less than minimum variance every
time, but its realised volatility is <em>lower</em> than minimum variance's in
only 40% of them, and a 0.3-shrunk minimum variance ends lowest in 64%. Drift
measures honesty, not performance.</p>
</div>

<h2>The question the verification report left open</h2>
<p>The <a href="/reports/hrp-example.html">HRP verification report</a> fits
six allocators on 120 periods of a 20-asset panel, holds the weights fixed for
400 more, and finds HRP's volatility drifting +1.3% against minimum variance's
+13.6%. It suggested varying the training length as the next experiment. This
note does that, and first explains the drift, with one instrument the report
did not use: the panel's true covariance. Everything is synthetic.</p>

<h2>Setup</h2>
<p>The report's generator draws a market factor (&sigma; 0.008), four block
factors (&sigma; 0.010) and, per asset, a market beta in [0.6, 1.3], a block
beta in [0.7, 1.2] and an idiosyncratic &sigma; in [0.006, 0.018]. Mirroring it
call for call gives the identical 520&times;20 panel (the tests assert this)
and the true covariance &Sigma; = &sigma;<sub>m</sub>&sup2;&beta;<sub>m</sub>&beta;<sub>m</sub>&prime;
+ &sigma;<sub>b</sub>&sup2;(block mask)&beta;<sub>b</sub>&beta;<sub>b</sub>&prime;
+ diag(&sigma;<sub>i</sub>&sup2;). For a weight vector w, vol<sub>true</sub> =
&radic;(w&prime;&Sigma;w)&middot;&radic;252 is what those weights would deliver
on average. Then</p>
<div class="qm-formula">optimism = vol<sub>true</sub> / vol<sub>in</sub> &minus; 1<br>luck = vol<sub>out</sub> / vol<sub>true</sub> &minus; 1<br>(1 + optimism)(1 + luck) = 1 + drift</div>
<p>The oracle is minimum variance computed from &Sigma; itself: the best any
covariance-based allocator could do with perfect information.</p>

<h2>Part A: the published split, decomposed</h2>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>Train 120, test 400</th><th>vol in</th><th>vol true</th><th>vol out</th><th>Optimism</th><th>Luck</th><th>Drift</th><th>Max weight</th><th>Short</th><th>N effective</th></tr></thead>
<tbody>
<tr><td>HRP (single)</td><td class="qm-num">0.1401</td><td class="qm-num">0.1440</td><td class="qm-num">0.1419</td><td class="qm-num">+2.8%</td><td class="qm-num">&minus;1.5%</td><td class="qm-num">+1.3%</td><td class="qm-num">0.106</td><td class="qm-num">0</td><td class="qm-num">16.3</td></tr>
<tr><td>HRP (Ward)</td><td class="qm-num">0.1419</td><td class="qm-num">0.1439</td><td class="qm-num">0.1425</td><td class="qm-num">+1.5%</td><td class="qm-num">&minus;1.0%</td><td class="qm-num">+0.4%</td><td class="qm-num">0.110</td><td class="qm-num">0</td><td class="qm-num">16.7</td></tr>
<tr><td>Minimum variance</td><td class="qm-num">0.1311</td><td class="qm-num">0.1489</td><td class="qm-num">0.1489</td><td class="qm-num">+13.5%</td><td class="qm-num">+0.1%</td><td class="qm-num">+13.6%</td><td class="qm-num">0.229</td><td class="qm-num">&minus;0.112</td><td class="qm-num">7.4</td></tr>
<tr><td>Minimum variance, long-only</td><td class="qm-num">0.1325</td><td class="qm-num">0.1450</td><td class="qm-num">0.1460</td><td class="qm-num">+9.4%</td><td class="qm-num">+0.7%</td><td class="qm-num">+10.2%</td><td class="qm-num">0.206</td><td class="qm-num">0</td><td class="qm-num">9.5</td></tr>
<tr><td>Minimum variance, shrinkage 0.3</td><td class="qm-num">0.1330</td><td class="qm-num">0.1444</td><td class="qm-num">0.1432</td><td class="qm-num">+8.6%</td><td class="qm-num">&minus;0.8%</td><td class="qm-num">+7.7%</td><td class="qm-num">0.169</td><td class="qm-num">&minus;0.019</td><td class="qm-num">11.8</td></tr>
<tr><td>Equal weight</td><td class="qm-num">0.1474</td><td class="qm-num">0.1464</td><td class="qm-num">0.1443</td><td class="qm-num">&minus;0.7%</td><td class="qm-num">&minus;1.4%</td><td class="qm-num">&minus;2.1%</td><td class="qm-num">0.050</td><td class="qm-num">0</td><td class="qm-num">20.0</td></tr>
<tr><td>Oracle: minimum variance from &Sigma;</td><td class="qm-num">0.1412</td><td class="qm-num">0.1388</td><td class="qm-num">0.1377</td><td>&mdash;</td><td>&mdash;</td><td>&mdash;</td><td class="qm-num">0.129</td><td class="qm-num">&minus;0.056</td><td class="qm-num">10.2</td></tr>
</tbody></table></div>
<p>Three readings. First, minimum variance's drift is not bad luck in the
test window: luck is +0.1%. Its in-sample 0.1311 was an artefact of fitting
20 assets to 120 observations (sample covariance condition number 43 against
35 for the truth), and the weights it chose have a true volatility of 0.1489,
higher than HRP's 0.1440 and higher than the oracle's 0.1388. Second, HRP is
not free of optimism (+2.8%) but nearly so, because it never inverts the
covariance: its weights are ratios of cluster variances, which the sample
estimates reasonably even at n = 120. Third, the oracle shows what the sample
optimiser was aiming for and missed: a 0.1388 portfolio with a 5.6% short
position and 10 effective names. The sample version doubled the short
position and halved the effective names.</p>

<h2>Part B: training length</h2>
<p>A longer panel (seed + 1, 2,400 periods) with a fixed 400-period test
window; training uses the T periods immediately before it.</p>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>T</th><th>HRP drift (optimism / luck)</th><th>MinVar drift (optimism / luck)</th><th>MinVar |w &minus; w<sub>oracle</sub>|</th><th>Shrunk 0.3 drift</th><th>HRP vol out</th><th>MinVar vol out</th></tr></thead>
<tbody>
<tr><td class="qm-num">60</td><td class="qm-num">+10.0% (+6.3 / +3.5)</td><td class="qm-num">+49.7% (+39.7 / +7.2)</td><td class="qm-num">1.66</td><td class="qm-num">+26.4%</td><td class="qm-num">0.1655</td><td class="qm-num">0.1924</td></tr>
<tr><td class="qm-num">120</td><td class="qm-num">+18.7% (+14.7 / +3.5)</td><td class="qm-num">+29.3% (+22.0 / +5.9)</td><td class="qm-num">0.98</td><td class="qm-num">+25.1%</td><td class="qm-num">0.1641</td><td class="qm-num">0.1658</td></tr>
<tr><td class="qm-num">250</td><td class="qm-num">+8.4% (+5.3 / +3.0)</td><td class="qm-num">+17.8% (+11.7 / +5.5)</td><td class="qm-num">0.71</td><td class="qm-num">+15.0%</td><td class="qm-num">0.1630</td><td class="qm-num">0.1616</td></tr>
<tr><td class="qm-num">500</td><td class="qm-num">+3.7% (+0.4 / +3.3)</td><td class="qm-num">+8.4% (+2.4 / +5.9)</td><td class="qm-num">0.59</td><td class="qm-num">+6.4%</td><td class="qm-num">0.1665</td><td class="qm-num">0.1602</td></tr>
<tr><td class="qm-num">1,000</td><td class="qm-num">+3.8% (+0.4 / +3.4)</td><td class="qm-num">+6.6% (+1.0 / +5.5)</td><td class="qm-num">0.40</td><td class="qm-num">+5.5%</td><td class="qm-num">0.1660</td><td class="qm-num">0.1579</td></tr>
<tr><td class="qm-num">2,000</td><td class="qm-num">+5.9% (+2.5 / +3.3)</td><td class="qm-num">+7.2% (+2.5 / +4.6)</td><td class="qm-num">0.21</td><td class="qm-num">+6.8%</td><td class="qm-num">0.1642</td><td class="qm-num">0.1552</td></tr>
</tbody></table></div>
<p>On this seed the test window is a high-volatility stretch, so every
allocator carries a positive luck term of 2&ndash;7%; that is the part no
training length can remove. Minimum variance's optimism falls from +39.7% at
T = 60 to about +1&ndash;2.5% from T = 500 on, and its distance from the
oracle weights shrinks eightfold. HRP's optimism is small from T = 250 on but
is +14.7% at T = 120 on this seed: the clustering step is also estimated
from the sample and can also be wrong. And once T is 250 or more, minimum
variance's realised volatility is <em>below</em> HRP's on this panel,
because with enough data the optimiser finds the diversification that HRP's
tree structure cannot express.</p>

<h2>Part C: 50 seeds at the published split</h2>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>Train 120, test 400, 50 panels</th><th>Drift median [p25, p75]</th><th>Optimism median</th><th>Vol out median</th><th>Lowest vol out in</th></tr></thead>
<tbody>
<tr><td>HRP (single)</td><td class="qm-num">+2.3% [&minus;1.6, +7.6]</td><td class="qm-num">+1.4%</td><td class="qm-num">0.1456</td><td class="qm-num">2% of seeds</td></tr>
<tr><td>HRP (Ward)</td><td class="qm-num">+2.1% [&minus;1.8, +6.9]</td><td class="qm-num">+1.6%</td><td class="qm-num">0.1458</td><td class="qm-num">4%</td></tr>
<tr><td>Minimum variance</td><td class="qm-num">+20.4% [+12.9, +24.4]</td><td class="qm-num">+19.6%</td><td class="qm-num">0.1427</td><td class="qm-num">4%</td></tr>
<tr><td>Minimum variance, long-only</td><td class="qm-num">+8.8% [+2.8, +13.6]</td><td class="qm-num">+7.5%</td><td class="qm-num">0.1406</td><td class="qm-num">26%</td></tr>
<tr><td>Minimum variance, shrinkage 0.3</td><td class="qm-num">+11.5% [+6.3, +14.7]</td><td class="qm-num">+10.7%</td><td class="qm-num">0.1389</td><td class="qm-num">64%</td></tr>
<tr><td>Equal weight</td><td class="qm-num">+0.9% [&minus;4.2, +4.6]</td><td class="qm-num">+0.1%</td><td class="qm-num">0.1494</td><td class="qm-num">0%</td></tr>
</tbody></table></div>
<p>HRP drifts less than minimum variance in 50 of 50 seeds. It also ends with
lower realised volatility than minimum variance in only 20 of 50, has lower
<em>true</em> volatility in 17 of 50, and is the lowest-volatility allocator in
one seed. Shrunk minimum variance takes that title in 32. The verification
report's claim, that HRP &ldquo;drifts far less&rdquo;, holds without
exception; the stronger claim people tend to make, that HRP therefore builds
lower-risk portfolios, does not hold on this panel.</p>

<h2>Part D: shrinkage</h2>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>Shrinkage toward diagonal</th><th>vol in</th><th>vol out</th><th>Drift</th><th>Optimism</th><th>Short</th><th>N effective</th></tr></thead>
<tbody>
<tr><td class="qm-num">0.0</td><td class="qm-num">0.1311</td><td class="qm-num">0.1489</td><td class="qm-num">+13.6%</td><td class="qm-num">+13.5%</td><td class="qm-num">&minus;0.112</td><td class="qm-num">7.4</td></tr>
<tr><td class="qm-num">0.1</td><td class="qm-num">0.1315</td><td class="qm-num">0.1462</td><td class="qm-num">+11.2%</td><td class="qm-num">+11.5%</td><td class="qm-num">&minus;0.054</td><td class="qm-num">9.0</td></tr>
<tr><td class="qm-num">0.3</td><td class="qm-num">0.1330</td><td class="qm-num">0.1432</td><td class="qm-num">+7.7%</td><td class="qm-num">+8.6%</td><td class="qm-num">&minus;0.019</td><td class="qm-num">11.8</td></tr>
<tr><td class="qm-num">0.5</td><td class="qm-num">0.1352</td><td class="qm-num">0.1419</td><td class="qm-num">+4.9%</td><td class="qm-num">+6.0%</td><td class="qm-num">0</td><td class="qm-num">14.3</td></tr>
<tr><td class="qm-num">0.7</td><td class="qm-num">0.1382</td><td class="qm-num">0.1416</td><td class="qm-num">+2.5%</td><td class="qm-num">+3.6%</td><td class="qm-num">0</td><td class="qm-num">16.5</td></tr>
<tr><td class="qm-num">1.0 (inverse variance)</td><td class="qm-num">0.1457</td><td class="qm-num">0.1437</td><td class="qm-num">&minus;1.3%</td><td class="qm-num">&minus;0.5%</td><td class="qm-num">0</td><td class="qm-num">18.6</td></tr>
</tbody></table></div>
<p>Drift falls monotonically with shrinkage and crosses zero at full
shrinkage, where the allocator is plain inverse variance. Realised volatility
bottoms out around 0.5&ndash;0.7 (0.1416&ndash;0.1419), level with HRP's
0.1419 on the same split. The crude diagonal target used here is a stand-in
for Ledoit&ndash;Wolf; a proper shrinkage estimator would pick its own
intensity from the data.</p>

<h2>What this does not establish</h2>
<ul>
<li>A factor-model panel with four clean blocks is the structure HRP was
designed for and the structure that makes a sample covariance
ill-conditioned; real markets are neither this clean nor stationary.</li>
<li>No transaction costs and no rebalancing anywhere; fixed weights flatter
every allocator and the least stable one most.</li>
<li>&ldquo;Optimism&rdquo; and &ldquo;luck&rdquo; are defined for volatility
only. Returns are not modelled (the panel has zero drift by construction),
so nothing here speaks to Sharpe ratios.</li>
<li>50 seeds of one generator. The ordering of allocators by realised
volatility could change with different block sizes, betas or idiosyncratic
noise.</li>
</ul>

<h2>Reproduce</h2>
<div class="qm-formula">cd quantmedia-research/hrp-drift-anatomy<br>python experiment.py<br>python ../tests/test_hrp_drift.py&nbsp;&nbsp;# expected: 6 passed</div>
<p>Runtime about four seconds. The first test asserts that the mirrored panel
is identical to the report's; the second that the published split
reproduces 0.1401 / 0.1419 / 0.1311 / 0.1489 and that optimism and luck
multiply to the drift exactly.
<a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research/hrp-drift-anatomy">Code and output on GitHub</a>.</p>

<h2>References</h2>
<ul>
<li>L&oacute;pez de Prado, M. (2016). Building Diversified Portfolios that Outperform Out of Sample. <em>Journal of Portfolio Management</em>, 42(4), 59&ndash;69.</li>
<li>Michaud, R. O. (1989). The Markowitz Optimization Enigma: Is &lsquo;Optimized&rsquo; Optimal? <em>Financial Analysts Journal</em>, 45(1), 31&ndash;42.</li>
<li>Ledoit, O. and Wolf, M. (2004). A well-conditioned estimator for large-dimensional covariance matrices. <em>Journal of Multivariate Analysis</em>, 88(2), 365&ndash;411.</li>
<li>DeMiguel, V., Garlappi, L. and Uppal, R. (2009). Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy? <em>Review of Financial Studies</em>, 22(5), 1915&ndash;1953.</li>
</ul>
"""

# Numbers from quantmedia-research/dsr-trials/outputs/, run 15 September
# 2026 (numpy 2.5.2 / scipy 1.18.1), seed 20260915, 5,000 Monte Carlo
# repetitions per cell. Part A reproduces the DSR explainer's table exactly.
DSR_TRIALS_BODY = """
<div class="qm-answer">
<span class="qm-answer-label">Short answer</span>
<p>Pick the best of N no-skill strategies by Sharpe ratio and test the
winner with an ordinary Probabilistic Sharpe Ratio at 0.95: it passes 40% of
the time at N = 10, 99% at N = 100, always at N = 1,000. Test it with the
Deflated Sharpe Ratio instead and it passes 0.1% of the time. The closed form
for the luck benchmark, the expected best Sharpe among N trials, matches Monte
Carlo to within 0.005 when the dispersion term is measured across the actual
trials, and keeps matching when the trials are correlated, because that
dispersion shrinks with the correlation. The price: with one genuine edge
among ten no-skill trials, DSR at 0.95 detects it 19% of the time where the
naive PSR detects it 92%. DSR is a conservative test, and this note
measures how conservative.</p>
</div>

<h2>What is being checked</h2>
<p>The <a href="/learn/deflated-sharpe-ratio.html">DSR explainer</a> gives
the formula and a worked table: a strategy with Sharpe 1.50 over 120 monthly
observations, skewness &minus;0.8, kurtosis 6.0, and a dispersion of Sharpe
ratios across trials of 0.50, falls from DSR 0.9997 at N = 10 to 0.2671 at
N = 1,000. Four questions follow. Is the table right? Does the closed form
for the expected maximum hold? What does the correction do to false
positives and to power? And what happens when the N trials are not
independent, as parameter sweeps never are? Everything below is synthetic.</p>

<h2>The benchmark</h2>
<div class="qm-formula">SR*<sub>0</sub> = sd(SR) &middot; [ (1 &minus; &gamma;) &Phi;<sup>&minus;1</sup>(1 &minus; 1/N) + &gamma; &Phi;<sup>&minus;1</sup>(1 &minus; 1/(N&middot;e)) ]<br>DSR = PSR evaluated against SR*<sub>0</sub> instead of 0, with the winner's own n, skewness and kurtosis</div>
<p>&gamma; is the Euler&ndash;Mascheroni constant 0.5772. sd(SR) is the
standard deviation of the Sharpe ratios <em>across the N trials</em>, which
means the trials have to have been kept.</p>

<h2>Part A: the explainer's table, recomputed</h2>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>N</th><th>Expected max Sharpe SR*<sub>0</sub></th><th>DSR</th></tr></thead>
<tbody>
<tr><td class="qm-num">1</td><td class="qm-num">&mdash;</td><td class="qm-num">1.0000 (= PSR)</td></tr>
<tr><td class="qm-num">10</td><td class="qm-num">0.7873</td><td class="qm-num">0.9997</td></tr>
<tr><td class="qm-num">100</td><td class="qm-num">1.2653</td><td class="qm-num">0.8736</td></tr>
<tr><td class="qm-num">1,000</td><td class="qm-num">1.6276</td><td class="qm-num">0.2671</td></tr>
</tbody></table></div>
<p>Denominator 2.2389, every cell to four decimals. The published table
holds. One thing the table does not say: sd(SR) = 0.50 is a large dispersion.
Under a pure null with 120 observations, Sharpe ratios of independent
no-skill strategies scatter with a standard deviation of only
&radic;(1/n) = 0.091. A dispersion of 0.50 describes a family of genuinely
different strategies, some with edge, not a parameter sweep of one; the
example is illustrative of the arithmetic, not of what a sweep produces.</p>

<h2>Part B: does the closed form hold?</h2>
<p>N independent strategies with iid standard-normal returns over 120
periods, 5,000 repetitions. sd(SR) is taken from the trials in each
repetition, as the method prescribes.</p>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>N</th><th>sd(SR) across trials</th><th>Max SR, Monte Carlo</th><th>Max SR, closed form</th><th>Closed form with sd 0.50</th></tr></thead>
<tbody>
<tr><td class="qm-num">10</td><td class="qm-num">0.0900</td><td class="qm-num">0.1424</td><td class="qm-num">0.1417</td><td class="qm-num">0.7873</td></tr>
<tr><td class="qm-num">100</td><td class="qm-num">0.0918</td><td class="qm-num">0.2322</td><td class="qm-num">0.2324</td><td class="qm-num">1.2653</td></tr>
<tr><td class="qm-num">1,000</td><td class="qm-num">0.0920</td><td class="qm-num">0.3039</td><td class="qm-num">0.2995</td><td class="qm-num">1.6276</td></tr>
</tbody></table></div>
<p>The formula is accurate to within 0.005 at N = 10 and 100 and within
0.005 at N = 1,000, where the extreme-value approximation is at its
weakest. The last column is what the explainer's sd of 0.50 implies; it is
5.5 times the null dispersion, and the benchmark scales with it linearly.
Feeding DSR a dispersion that was not measured on the trials is where the
number stops meaning anything.</p>

<h2>Part C: false positives and power</h2>
<p>Under the null (no strategy has edge), the best of N by in-sample Sharpe
is tested at 0.95 both ways. With one true edge planted (mean 0.30 per
period, PSR against zero about 0.94 on its own), the same is done and
&ldquo;power&rdquo; counts the repetitions where the edge was both selected and
passed.</p>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>N</th><th>Naive PSR &gt; 0.95, null</th><th>DSR &gt; 0.95, null</th><th>True edge selected</th><th>Naive PSR power</th><th>DSR power</th></tr></thead>
<tbody>
<tr><td class="qm-num">1</td><td class="qm-num">4.7%</td><td class="qm-num">4.7%</td><td class="qm-num">100%</td><td class="qm-num">94.4%</td><td class="qm-num">94.4%</td></tr>
<tr><td class="qm-num">10</td><td class="qm-num">40.1%</td><td class="qm-num">0.0%</td><td class="qm-num">93.4%</td><td class="qm-num">91.5%</td><td class="qm-num">18.9%</td></tr>
<tr><td class="qm-num">100</td><td class="qm-num">99.2%</td><td class="qm-num">0.1%</td><td class="qm-num">75.1%</td><td class="qm-num">75.1%</td><td class="qm-num">13.1%</td></tr>
<tr><td class="qm-num">1,000</td><td class="qm-num">100%</td><td class="qm-num">0.1%</td><td class="qm-num">49.4%</td><td class="qm-num">49.4%</td><td class="qm-num">5.4%</td></tr>
</tbody></table></div>
<ul>
<li><strong>The naive PSR is useless on a mined winner.</strong> Its
false-positive rate is 40% after ten tries and 99% after a hundred. The 4.7%
at N = 1 is the nominal 5%, which is the only case where PSR is the right
test.</li>
<li><strong>DSR over-corrects.</strong> Its false-positive rate is not 5% but
0.0&ndash;0.1%. The benchmark is the <em>expected</em> maximum, and the winner
has to clear it with 95% confidence; under the null the winner sits at the
expected maximum on average, so it almost never clears with margin.</li>
<li><strong>Power is the cost.</strong> A strategy with a real per-period
Sharpe of 0.30 is found by the naive test 91% of the time among ten
no-skill rivals and by DSR 19%; among a thousand rivals it is not even
selected half the time, and DSR confirms it in 5%. Conditional on being
selected, DSR's detection rate is 20%, 17% and 11%.</li>
</ul>
<p>Read together: DSR at 0.95 is a filter that rarely lets luck through and
often keeps skill out. That is a defensible trade for a research process
where the cost of a false strategy is high; it is not a neutral
measurement.</p>

<h2>Part D: correlated trials</h2>
<p>A parameter sweep produces trials that share most of their returns. Here
N = 100 strategies are built as &radic;&rho;&middot;common + &radic;(1&minus;&rho;)&middot;own
noise, so pairwise correlation is &rho;.</p>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>&rho;</th><th>sd(SR) across trials</th><th>Max SR, Monte Carlo</th><th>Closed form with nominal N = 100</th><th>Effective N implied</th></tr></thead>
<tbody>
<tr><td class="qm-num">0.0</td><td class="qm-num">0.0920</td><td class="qm-num">0.2330</td><td class="qm-num">0.2328</td><td class="qm-num">101</td></tr>
<tr><td class="qm-num">0.5</td><td class="qm-num">0.0651</td><td class="qm-num">0.1656</td><td class="qm-num">0.1646</td><td class="qm-num">104</td></tr>
<tr><td class="qm-num">0.9</td><td class="qm-num">0.0291</td><td class="qm-num">0.0741</td><td class="qm-num">0.0735</td><td class="qm-num">106</td></tr>
</tbody></table></div>
<p>Correlation does not break the formula; it shrinks sd(SR). Ninety
percent common variance leaves the hundred trials with a Sharpe dispersion of
0.029 instead of 0.092, the expected maximum falls from 0.23 to 0.07, and the
closed form with the nominal N = 100 still lands within 0.001 of the Monte
Carlo. The trials are not independent, but the dispersion measured across
them already carries that information, so the &ldquo;effective number of
independent trials&rdquo; implied by the maximum stays near 100. The
practical rule is the one the explainer already gives: measure sd(SR) on the
trials you actually ran. Substituting a dispersion from elsewhere, or a
nominal &ldquo;independent&rdquo; N smaller than the count, double-corrects.</p>

<h2>What this does not establish</h2>
<ul>
<li>Normal returns throughout. Fat tails widen the null dispersion of
Sharpe ratios and would raise every benchmark; the explainer's skew and
kurtosis inputs enter DSR's denominator, not its benchmark.</li>
<li>The equicorrelated design is one structure. A sweep that produces a few
clusters of near-identical strategies plus some outliers is different, and
Bailey and L&oacute;pez de Prado's own recommendation, to cluster trials
first, is not tested here.</li>
<li>&ldquo;Power&rdquo; is defined for one edge size and one n. A larger
edge or a longer record changes the numbers, not the direction.</li>
<li>N is self-reported everywhere in this method; no experiment can make an
understated trial count honest.</li>
</ul>

<h2>Reproduce</h2>
<div class="qm-formula">cd quantmedia-research/dsr-trials<br>python experiment.py&nbsp;&nbsp;# about 45 s<br>python ../tests/test_dsr_trials.py&nbsp;&nbsp;# expected: 5 passed</div>
<p>The first test recomputes the explainer table to four decimals; the
others run the Monte Carlo at reduced size with matching tolerances.
<a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research/dsr-trials">Code and output on GitHub</a>.</p>

<h2>References</h2>
<ul>
<li>Bailey, D. H. and L&oacute;pez de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. <em>Journal of Portfolio Management</em>, 40(5), 94&ndash;107.</li>
<li>Bailey, D. H. and L&oacute;pez de Prado, M. (2012). The Sharpe Ratio Efficient Frontier. <em>Journal of Risk</em>, 15(2).</li>
<li>Harvey, C. R. and Liu, Y. (2015). Backtesting. <em>Journal of Portfolio Management</em>, 42(1), 13&ndash;28.</li>
<li>White, H. (2000). A Reality Check for Data Snooping. <em>Econometrica</em>, 68(5), 1097&ndash;1126.</li>
</ul>
"""

# Method note. Every example cited is a defect or check that exists in this
# repository's reports, tests or experiment notes; nothing is hypothetical.
VERIFY_METHOD_BODY = """
<div class="qm-answer">
<span class="qm-answer-label">Short answer</span>
<p>Run the implementation on an input whose correct answer you already know,
and on the ugliest inputs you can construct, before you run it on data whose
answer you do not know. Every defect this site has found and fixed was found
that way, none by reading the code and none by running it on real returns:
a VPIN estimator that returned 0 on a perfectly one-sided tape, a distance
matrix that scipy rejected as asymmetric, a worked example whose
&ldquo;normal&rdquo; case dropped the kurtosis term, a table cell that carried
2.8955 where the arithmetic gives 2.8949. The method is eight steps; the
rest of this note is what each one caught.</p>
</div>

<h2>Why reading the code is not enough</h2>
<p>Quantitative finance methods are usually implemented from a paper, and a
paper is prose plus formulas. Prose is where conventions hide: whether
kurtosis means Pearson's 3-at-normal or the excess 0-at-normal, whether a
division by zero in a degenerate case should give 0.5 or should follow the
sign, whether the last incomplete bucket belongs in the average. Code that
reads correctly against the prose can still be wrong against the maths, and
real data cannot tell you, because on real data the right answer is unknown.
So the test has to be an input where it is known.</p>

<h2>The eight steps</h2>
<div class="qm-table-wrap"><table class="qm-table">
<thead><tr><th>Step</th><th>What it means</th><th>What it caught here</th></tr></thead>
<tbody>
<tr><td>1. Build a synthetic input with a planted answer</td><td>Generate data from a fixed seed with the property the method is supposed to detect placed where you know it is.</td><td>A 20,000-trade tape with informed buying in trades 8,000&ndash;11,999; VPIN rose from 0.3292 to 0.6376 across it, a 1.94&times; ratio the estimator had to show before anything else was believed.</td></tr>
<tr><td>2. Feed it the degenerate cases</td><td>Zero variance, constant inputs, a single asset, the smallest n the formula admits, a monotone series. Decide the correct output <em>before</em> running.</td><td>A monotone tape: every trade higher than the last, dispersion of price changes zero. The original branch split volume 50/50 and returned VPIN 0 on the most toxic input possible. Fixed by classifying on the sign of the change; now one of 15 tests.</td></tr>
<tr><td>3. Reproduce a published number</td><td>If the paper, a textbook or your own site gives a worked example, recompute it independently (scipy, a spreadsheet, by hand) and compare every intermediate, not just the final figure.</td><td>The PSR worked example: denominators of 1.000 and 2.318 as published, 1.4577 and 2.4850 when computed. Months later a reader recomputed the z-statistic on the corrected page and found 2.8949 where the table still said 2.8955.</td></tr>
<tr><td>4. Run it in a clean environment with current libraries</td><td>Dependencies move. Install the pinned versions in a fresh directory, then the newest, and run both.</td><td>HRP under pandas 3: <code>np.fill_diagonal</code> on <code>DataFrame.values</code> raised because the view is read-only. Under pandas 2 the same code had run for a year.</td></tr>
<tr><td>5. Check what the library rejects</td><td>Floating-point noise breaks exact properties (symmetry, positive definiteness, sums to one). Test the properties, not just the values.</td><td>The correlation-distance matrix was asymmetric at the 10<sup>&minus;16</sup> level and <code>scipy.spatial.distance.squareform</code> refused it. Fixed by symmetrising explicitly, 0.5(D + D&prime;).</td></tr>
<tr><td>6. Fix the test when the test is wrong, and say so</td><td>An over-specified assertion is a defect in the test, not in the code. The distinction has to be written down, because silently loosening tests is how real gaps get hidden.</td><td>An HRP test asserted that single and Ward linkage must produce different weights; on one seed they coincided. The methods were confirmed to differ on other seeds and the test was corrected, with the reason recorded in the report.</td></tr>
<tr><td>7. Pin every intermediate the reader could check</td><td>Publish the denominator, the z, the bucket size, the seed, the version numbers. A final figure alone cannot be audited; a chain of intermediates can, and will be.</td><td>The 2.8955 catch above happened only because the intermediate was on the page. It would have been invisible behind &ldquo;PSR = 99.81%&rdquo;.</td></tr>
<tr><td>8. Write down what the check does not establish</td><td>A synthetic test proves the implementation matches the method. It says nothing about whether the method works on markets.</td><td>Every report on this site ends with that section: VPIN's forecasting power is contested in the literature and untested here; HRP's lower drift does not mean lower realised volatility, and on 50 synthetic panels it usually does not.</td></tr>
</tbody></table></div>

<h2>What makes a good planted answer</h2>
<p>The input should be simple enough that the right output is obvious and
strong enough that a wrong implementation cannot get it by accident. The
monotone tape is the model: any correct classifier must call it entirely
one-sided, so the expected VPIN is 1 to within the window's edge effects,
and a test asserting VPIN &gt; 0.9 has no false positives worth worrying
about. The informed-episode tape is the weaker kind: it tests direction,
not level, because the level depends on the classifier, the bucket size and
the window, as the <a href="/learn/vpin-classifier-noise-floor.html">noise-floor
note</a> measures. A good suite has both: one input with an exact answer, one
with a qualitative one, and the qualitative one is not allowed to be the only
evidence.</p>
<p>For a formula rather than an algorithm, the planted answer is a second,
independent computation. The PSR calculator now computes the normal CDF
rather than quoting a value, and its tests pin the normal case (denominator
1.4577, z 4.935) and the skewed case (2.4850, 2.895) against scipy. Two
implementations that agree can both be wrong in the same way if they share a
convention; the convention itself (here, that &gamma;&#8322; is non-excess
kurtosis) has to be stated in the text so a reader can disagree with it.</p>

<h2>What makes a good degenerate case</h2>
<p>Ask what each denominator can do. Zero dispersion of price changes, zero
variance of returns, a covariance matrix of rank one, n = 2 in a formula
with &radic;(n &minus; 1), a kurtosis that makes 1 &minus; &gamma;&#8321;SR +
(&gamma;&#8322; &minus; 1)SR&sup2;/4 negative. Then ask what each branch that
handles those cases assumes. The VPIN defect lived in the branch that
handled zero dispersion; the branch existed, so the author had thought about
the case, and still got its sign wrong, because &ldquo;split 50/50&rdquo; was the
right answer for a flat tape and the wrong one for a steadily rising tape,
and the branch did not distinguish them. The test that caught it constructs
the rising tape explicitly. The calculator's tests likewise refuse to display
a result when the variance term is non-positive rather than printing a
number that means nothing.</p>

<h2>What a verification report has to contain</h2>
<ul>
<li>The implementation under test, at a named revision.</li>
<li>The environment: language and library versions actually used.</li>
<li>The input: how it was generated, its seed, what was planted.</li>
<li>The expected answer and where it comes from.</li>
<li>What the code returned, before and after any fix.</li>
<li>Each defect: how it was detected, what the fix was, which test now guards it.</li>
<li>A reproduce block: the commands that regenerate every number on the page.</li>
<li>The limits: what this establishes and what it does not.</li>
</ul>
<p>The three reports on this site (<a href="/reports/vpin-example.html">VPIN</a>,
<a href="/reports/hrp-example.html">HRP</a>, <a href="/reports/psr-worked-example.html">PSR</a>)
follow this outline, and <code>quantmedia-research/verify_examples.py</code>
re-runs the first two in a clean directory and asserts that the committed
CSVs match to nine decimals. The experiment notes that followed them use
tolerance tests instead, because Monte Carlo output is not bit-stable across
NumPy versions; the note says which kind of test it is.</p>

<h2>What this does not establish</h2>
<ul>
<li>Passing every step proves the implementation matches the method as
stated. It does not prove the method is useful, and a verification report
should never be read as an endorsement of the method.</li>
<li>The steps were distilled from three methods and about thirty tests.
Other kinds of code (optimisers with numerical tolerances, anything
stochastic by design) need additional steps this note does not cover.</li>
<li>Independent recomputation catches convention and arithmetic errors; it
does not catch a misreading shared by both computations. Publishing the
convention is the only defence, and it depends on a reader.</li>
</ul>

<h2>Reproduce</h2>
<div class="qm-formula">python quantmedia-research/tests/test_vpin.py&nbsp;&nbsp;&nbsp;# 15<br>python quantmedia-research/tests/test_hrp.py&nbsp;&nbsp;&nbsp;&nbsp;# 13<br>node scripts/test_psr.js&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 12<br>python quantmedia-research/verify_examples.py</div>
<p>Every defect cited above is in the repository's history and the test
that guards it is in the suites listed.
<a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research">Code on GitHub</a>.</p>
"""
