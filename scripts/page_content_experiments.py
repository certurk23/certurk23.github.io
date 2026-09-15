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
