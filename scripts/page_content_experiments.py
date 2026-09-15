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
