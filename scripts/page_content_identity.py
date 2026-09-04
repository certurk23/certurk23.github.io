"""Content for the author profile and the editorial policy page.

EVERY factual claim below is either supplied by the site owner or already
verifiable inside this repository. Deliberately absent, because they would be
inventions: university, employer, job title, professional licence, years of
experience, prior roles, awards, client list, team size, peer review, journal
publication, and any traffic or performance figure.

Where the honest answer is "no", the page says no - there is no peer review,
there is no institutional backing, the track record has not been forward
tested. A trust page that admits its gaps is worth more than one that implies
credentials it cannot support.
"""

AUTHOR_NAME = 'Cemil Ertürk'
GITHUB = 'https://github.com/certurk23'
XPROFILE = 'https://x.com/certurk23'
REPO = 'https://github.com/certurk23/certurk23.github.io'
EMAIL = 'contact@quantmedia.io'

AUTHOR_BODY = f'''
<p class="qm-lede">{AUTHOR_NAME} is the researcher and engineer behind QuantMedia.
He writes the research, builds the data pipeline that produces the site's
proprietary metrics, and maintains the open implementations that accompany the
papers.</p>

<div class="qm-note">
<strong>Stated plainly, because it matters more than a biography.</strong>
QuantMedia is an independent, one-person research project. It is not affiliated
with any university, fund, broker or financial institution, and nothing on this
site is peer reviewed. No professional licence or institutional credential is
claimed anywhere on this site, and none should be inferred. The research is
published so that it can be checked, not because an institution vouches for it.
</div>

<h2>Research areas</h2>
<p>These are the areas the published work actually covers, each linked to the
research itself rather than asserted:</p>
<ul>
  <li><strong>Market microstructure</strong> &mdash; order-flow toxicity and
      adverse selection (<a href="/paper-vpin-order-flow-toxicity.html">VPIN</a>),
      and the components of the quoted spread
      (<a href="/paper-bid-ask-spread-dynamics.html">spread dynamics</a>).</li>
  <li><strong>Portfolio construction</strong> &mdash; allocation methods that
      avoid inverting an unstable covariance matrix
      (<a href="/paper-hierarchical-risk-parity.html">Hierarchical Risk Parity</a>).</li>
  <li><strong>Performance evaluation under multiple testing</strong> &mdash;
      whether a Sharpe ratio survives its own track-record length and the
      number of trials that produced it
      (<a href="/paper-probabilistic-sharpe-ratio.html">PSR</a>,
       <a href="/learn/deflated-sharpe-ratio.html">DSR</a>).</li>
  <li><strong>Execution and transaction costs</strong> &mdash; spread, market
      impact and delay cost as separate terms rather than one flat assumption
      (<a href="/paper-slippage-latency-modeling.html">slippage and latency</a>).</li>
  <li><strong>Systematic signal research</strong> &mdash; the
      <a href="/methodology.html">confluence engine</a> behind the daily scan and
      the two indices derived from it.</li>
</ul>

<h2>How the research is approached</h2>
<p>Four working rules, each of which is enforced by something in the codebase
rather than being a statement of intent:</p>
<ul>
  <li><strong>Published code beats a published claim.</strong> Where an
      implementation exists it is
      <a href="/reproducibility.html">shipped with example data and tests</a>.
      Writing the VPIN package found a real bug in the degenerate case &mdash; a
      perfectly one-sided tape returned zero toxicity, the opposite of correct.
      That is the argument for running code rather than describing it.</li>
  <li><strong>State the limitations.</strong> Every paper carries a limitations
      section covering what it does <em>not</em> establish. Two proposed
      metrics &mdash; a VPIN toxicity index and a slippage stress index &mdash;
      were deliberately not built, because the pipeline collects end-of-day
      bars and neither can be computed honestly without tick data.</li>
  <li><strong>Never present stale data as live.</strong> The pipeline publishes
      its own freshness at <a href="/data/status.json">/data/status.json</a> and
      the site reports a paused feed rather than quietly showing an old number.</li>
  <li><strong>No backfilling.</strong> Index history accumulates one record per
      completed session, going forward only. Reconstructing history that was
      never observed would make the series look older and more validated than
      it is.</li>
</ul>

<h2>Built and maintained</h2>
<div class="qm-tablewrap">
<table>
<thead><tr><th>Component</th><th>What it is</th></tr></thead>
<tbody>
<tr><td><a href="/methodology.html">Daily confluence scan</a></td>
    <td>A 30-signal technical engine scored across a fixed 180-name liquid US universe, run after every close.</td></tr>
<tr><td><a href="/indices/signal-breadth.html">Signal Breadth Index</a></td>
    <td>Share of the universe clearing the 22-of-30 threshold, with published formula, JSON and history.</td></tr>
<tr><td><a href="/indices/sector-confluence.html">Sector Confluence Index</a></td>
    <td>The same scan grouped and ranked by sector.</td></tr>
<tr><td><a href="/reproducibility.html">VPIN implementation</a></td>
    <td>Equal-volume bucketing, bulk volume classification and the tick rule. 15 tests.</td></tr>
<tr><td><a href="/reproducibility.html">HRP implementation</a></td>
    <td>Correlation distance, linkage, quasi-diagonalisation and recursive bisection, with baselines. 13 tests.</td></tr>
<tr><td><a href="/tools/probabilistic-sharpe-ratio-calculator.html">PSR calculator</a></td>
    <td>Client-side calculator showing every intermediate value so the result can be checked by hand.</td></tr>
</tbody>
</table>
</div>

<h2>Selected research</h2>
<ul>
  <li><a href="/paper-vpin-order-flow-toxicity.html">VPIN and Order Flow Toxicity</a> &mdash; with runnable code</li>
  <li><a href="/paper-hierarchical-risk-parity.html">Hierarchical Risk Parity</a> &mdash; with runnable code</li>
  <li><a href="/paper-probabilistic-sharpe-ratio.html">The Probabilistic Sharpe Ratio</a> &mdash; with calculator</li>
  <li><a href="/paper-slippage-latency-modeling.html">Slippage and Latency Modelling</a></li>
  <li><a href="/paper-bid-ask-spread-dynamics.html">Bid-Ask Spread Dynamics</a></li>
  <li><a href="/papers.html">All research papers &rarr;</a></li>
</ul>

<h2>Verifiable profiles</h2>
<p>Only accounts that genuinely exist are listed here. There is no ORCID or
Google Scholar profile, because no peer-reviewed publication record exists to
attach one to.</p>
<ul>
  <li><a href="{GITHUB}" rel="me noopener" target="_blank">GitHub &mdash; certurk23</a>
      &middot; the <a href="{REPO}" rel="noopener" target="_blank">repository behind this site</a>,
      including the research packages and the data pipeline</li>
  <li><a href="{XPROFILE}" rel="me noopener" target="_blank">X &mdash; @certurk23</a></li>
  <li><a href="mailto:{EMAIL}">{EMAIL}</a></li>
</ul>

<h2>Corrections</h2>
<p>Errors get corrected in place and the change is recorded rather than quietly
overwritten &mdash; the <a href="/editorial-policy.html">editorial policy</a>
sets out how. A published worked example for the Probabilistic Sharpe Ratio was
found to be arithmetically wrong and was corrected against
<code>scipy</code>; that correction is disclosed on the paper itself. If you
find a mistake, <a href="mailto:{EMAIL}">say so</a>.</p>

<div class="qm-related">
  <a href="/editorial-policy.html">Editorial policy</a>
  <a href="/methodology.html">Research methodology</a>
  <a href="/reproducibility.html">Reproducibility</a>
  <a href="/about.html">About QuantMedia</a>
</div>
'''

EDITORIAL_BODY = f'''
<p class="qm-lede">How QuantMedia research is produced, funded, corrected and
disclosed. The purpose of this page is to let a reader judge the work without
having to take anything on trust.</p>

<h2>Independence</h2>
<p>QuantMedia is independently operated by {AUTHOR_NAME} and is not sponsored
by, affiliated with, or paid by any fund, broker, exchange, data vendor or
issuer. No paid placements, sponsored posts, affiliate links or gifted
subscriptions appear anywhere on this site. No third party reviews or approves
research before publication.</p>
<p>If that changes, it will be disclosed on this page and on the affected page
before publication, not afterwards.</p>

<h2>How this site is funded</h2>
<p><strong>QuantMedia currently generates no revenue.</strong> There are no sponsorships, no paid placements, no affiliate links and no paid subscriptions, and nothing on this site has ever been written for payment.</p>
<p>An application to Google AdSense has been submitted and is pending. If it is approved, advertising may appear on this site in future, and this page will be updated to say so plainly. No other form of monetisation is planned at present.</p>
<p>Whatever funding arrives later, the rule is fixed in advance: advertisers get no input into research topics, conclusions or publication timing, they are never shown content ahead of readers, and no revenue arrangement will depend on reaching any particular conclusion. Any change to this will be disclosed here before it takes effect, not after.</p>

<h2>No investment advice, and no positions disclosed as recommendations</h2>
<p>Everything here is published for informational and educational purposes.
It is not investment advice, not a recommendation, and not an offer or
solicitation to buy or sell any security. {AUTHOR_NAME} is not a licensed
investment adviser or broker-dealer in any jurisdiction. The signals published
by the daily scan are the mechanical output of a documented rule set, not a
view on what any reader should do.</p>

<h2>Data sources</h2>
<div class="qm-tablewrap">
<table>
<thead><tr><th>Data</th><th>Upstream source</th><th>Nature</th></tr></thead>
<tbody>
<tr><td>US equity OHLCV, signals, indices</td><td>Yahoo Finance, via the <code>yfinance</code> library</td><td>End-of-day bars</td></tr>
<tr><td>Market news</td><td>Finnhub</td><td>Third-party headlines, attributed to their publisher</td></tr>
<tr><td>Foreign exchange</td><td>open.er-api.com</td><td>Reference rates</td></tr>
<tr><td>Crypto</td><td>CoinGecko</td><td>Reference prices</td></tr>
</tbody>
</table>
</div>
<p>QuantMedia does not own or license a professional market-data feed. All
upstream data is free-tier and carries the accuracy limitations of that tier,
including occasional gaps, late revisions and unadjusted corporate actions.
Anything computed by QuantMedia from that data &mdash; the confluence scan, the
Signal Breadth and Sector Confluence indices &mdash; is original to this site,
and is labelled as such.</p>
<p>News headlines are third-party content and are always attributed to the
publisher that produced them. QuantMedia does not rewrite, re-report or claim
authorship of them.</p>

<h2>Live versus snapshot</h2>
<p>Nothing on this site is labelled live unless the pipeline actually refreshed
it. The machine-readable state is published at
<a href="/data/status.json">/data/status.json</a> and each source reports
independently, so one failing feed cannot silently stale the others. When a
source has not refreshed, the site says the feed is delayed or paused and shows
the timestamp of the data it is displaying. A failed update never removes data
that was already published &mdash; the last known good value is preserved and
disclosed as such.</p>

<h2>Methodology versioning</h2>
<p>The production signal methodology carries an explicit version and effective
date, published in
<a href="/data/signal_config.json">/data/signal_config.json</a> and stamped into
every scan output. The current engine is <strong>version 2.0</strong>, effective
<strong>14 April 2026</strong>.</p>
<p>Research pages carry their own research version, publication date and last
material revision date. The version is incremented only when the substance
changes &mdash; a new limitation, a corrected calculation, a changed conclusion.
Typography and layout fixes do not bump it, because a version number that moves
for trivial reasons tells the reader nothing.</p>

<h2>Corrections policy</h2>
<p>Mistakes are corrected in place. The correction is recorded rather than
silently absorbed, so that the history of a claim stays legible.</p>
<ul>
  <li><strong>Material errors</strong> &mdash; a wrong number, formula, or
      conclusion. The page is corrected, the last-material-revision date is
      updated, and the correction is described on the page itself.</li>
  <li><strong>Non-material fixes</strong> &mdash; typography, broken links,
      clarified wording. Fixed without ceremony and without a version bump.</li>
  <li><strong>Withdrawal</strong> &mdash; if a piece of research cannot be
      supported, it is marked as withdrawn with the reason, rather than
      deleted. Removing the evidence of a mistake is worse than the mistake.</li>
</ul>
<p>Two corrections have been published so far, both found by running the code
rather than reading it: an arithmetically wrong worked example in the
Probabilistic Sharpe Ratio paper, and a VPIN degenerate case that returned zero
toxicity for a perfectly one-sided tape. Both are disclosed on the affected
pages.</p>
<p>To report an error, email <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>

<h2>Reproducibility standards</h2>
<p>Where an implementation exists it is published with example data, expected
output and tests, and the <a href="/reproducibility.html">reproducibility
index</a> states honestly which papers have code and which do not. Papers
without an implementation are labelled research-only rather than left to
imply otherwise.</p>
<p>Example datasets shipped with the packages are <strong>synthetic and
generated from fixed seeds</strong>. This is stated in the README, the module
docstring and the console output. Synthetic data demonstrates that code runs
and is deterministic; it does not validate a strategy, and no result computed
on it should be read as evidence about live markets.</p>

<h2>What has not been validated</h2>
<p>The published signals have <strong>no forward-tested track record</strong>.
The methodology is documented and the outputs are published daily, but no
out-of-sample performance record has accumulated yet, and none is claimed.
Backfilling one would be fabrication. Any performance figure appearing on this
site is explicitly labelled as in-sample, illustrative, or computed on
synthetic data.</p>

<h2>Use of AI tools</h2>
<p>AI coding and writing assistants are used materially in building this site:
in drafting and editing prose, in writing and refactoring code, and in auditing
pages for errors and inconsistencies. This is disclosed because it is true and
because readers are entitled to know how content they are asked to trust was
produced.</p>
<p>What that does not change: every factual claim, formula, reference and
numeric result is the author's responsibility. Formulas are checked against
their primary sources, numeric examples are computed with
<code>numpy</code>/<code>scipy</code> rather than asserted, and the code is
covered by tests that run in continuous integration. Where an AI-assisted draft
produced something wrong &mdash; as with the PSR worked example &mdash; it was
caught by executing the calculation, and the correction was published.</p>
<p>No page on this site is auto-generated and published without review, and no
AI system is presented as an author.</p>

<h2>Privacy and analytics</h2>
<p>QuantMedia uses Google Analytics 4 for aggregate traffic measurement. Google AdSense code is present because an application is pending; should it be approved, advertising cookies would apply as described in the <a href="/privacy.html">privacy policy</a>. No accounts, logins or personal profiles are collected by this site.</p>

<div class="qm-related">
  <a href="/author/cemil-erturk.html">About the author</a>
  <a href="/methodology.html">Research methodology</a>
  <a href="/reproducibility.html">Reproducibility</a>
  <a href="/privacy.html">Privacy policy</a>
</div>
'''
