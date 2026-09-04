#!/usr/bin/env python3
"""
Page bodies for the generated /indices/, /learn/ and /tools/ pages.
===================================================================
Content lives here, assembly lives in build_pages.py. Every figure that
describes the signal engine is interpolated from qm_config.ENGINE so these
pages cannot drift from production the way the old copy did.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qm_config as C   # noqa: E402

E = C.ENGINE
UNI = E['universe_count']
NSIG = E['n_signals']
THR = E['confluence_min']
MINS = E['min_sessions']


# ===========================================================================
# /indices/ - proprietary metrics that originate on QuantMedia
# ===========================================================================
# Chart script kept OUT of the f-string: it is full of JS braces, which an
# f-string would try to interpret as replacement fields.
_BREADTH_CHART_JS = """
  <script>
  (function(){
    var box=document.getElementById('qm-breadth-history');
    if(!box) return;
    fetch('/data/breadth_history.json',{cache:'no-cache'})
      .then(function(r){ if(!r.ok) throw 0; return r.json(); })
      .then(function(d){
        var s=(d&&d.series)||[]; if(!s.length) throw 0;
        var thr=d.threshold||22, n=s.length;
        var rows=s.slice().reverse().map(function(r){
          return '<tr><td class="qm-num">'+r.market_date+'</td>'+
                 '<td class="qm-num">'+r.breadth_pct.toFixed(1)+'%</td>'+
                 '<td class="qm-num">'+r.buy_signals+'/'+r.scored+'</td>'+
                 '<td class="qm-num">'+r.median_score+'</td>'+
                 '<td class="qm-num">'+(r.mean_score!=null?r.mean_score.toFixed(2):'--')+'</td></tr>';
        }).join('');
        var table='<div class="qm-tablewrap"><table class="qm-kv"><thead><tr>'+
          '<th>Market date</th><th>Breadth</th><th>BUY / scored</th>'+
          '<th>Median</th><th>Mean</th></tr></thead><tbody>'+rows+
          '</tbody></table></div>';
        var head='', chart='';
        if(n<10){
          head='<p class="qm-note"><strong>'+n+' observation'+(n===1?'':'s')+
               ' so far.</strong> A chart appears once at least 10 sessions have '+
               'accumulated; until then the table below is the complete series.</p>';
        }else{
          // Lightweight inline SVG - no charting library.
          var W=720,H=200,P=32, vals=s.map(function(r){return r.breadth_pct;});
          var lo=Math.max(0,Math.min.apply(null,vals)-5),
              hi=Math.min(100,Math.max.apply(null,vals)+5);
          var x=function(i){return P+i*(W-2*P)/Math.max(1,n-1);},
              y=function(v){return H-P-(v-lo)*(H-2*P)/Math.max(1e-9,hi-lo);};
          var pts=vals.map(function(v,i){return x(i).toFixed(1)+','+y(v).toFixed(1);}).join(' ');
          chart='<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="200" '+
            'role="img" aria-label="QuantMedia Signal Breadth over the last '+n+
            ' sessions. Values are listed in the table below.">'+
            '<line x1="'+P+'" y1="'+y(50).toFixed(1)+'" x2="'+(W-P)+'" y2="'+y(50).toFixed(1)+
            '" stroke="currentColor" stroke-opacity=".25" stroke-dasharray="4 4"/>'+
            '<polyline fill="none" stroke="#00a651" stroke-width="2" points="'+pts+'"/>'+
            '<text x="'+P+'" y="16" font-size="11" fill="currentColor" opacity=".65">'+
            'Signal breadth %, last '+n+' sessions (dashed = 50%)</text></svg>';
        }
        box.innerHTML=head+chart+table+
          '<p class="qm-note">Full series: '+
          '<a href="/data/breadth_history.json">/data/breadth_history.json</a></p>';
      })
      .catch(function(){
        box.innerHTML='<p class="qm-note">History is still accumulating &mdash; '+
          'the first records publish with the next post-close scans. The series '+
          'will be available at <a href="/data/breadth_history.json">'+
          '/data/breadth_history.json</a>.</p>';
      });
  })();
  </script>
"""


BREADTH_BODY = f"""
  <p class="qm-lede">Signal Breadth is a QuantMedia metric. It measures how much
  of the scan universe currently qualifies as a BUY, which is a different
  question from whether any individual stock looks attractive: it describes
  <em>participation</em>. The reading below is regenerated after every US close
  from the same scan that produces the <a href="/quantum-signals.html">daily
  signal dashboard</a>.</p>

  <div class="qm-answer">
    <span class="qm-answer-label">Definition</span>
    <p><strong>QuantMedia Signal Breadth</strong> is the share of successfully
    scored US equities whose confluence score reached the BUY threshold on a
    given market date. With a universe of {UNI} liquid US-listed equities scored
    against {NSIG} binary technical signals and a threshold of {THR}, a breadth
    of 40% means 40% of the stocks scored that day had at least {THR} of {NSIG}
    signals simultaneously bullish.</p>
  </div>

  <h2>Current reading</h2>
  <!-- QM:BREADTH:START -->
  <p class="qm-note">The current reading publishes after the next post-close scan.</p>
  <!-- QM:BREADTH:END -->

  <h2>Formula</h2>
  <div class="qm-formula">breadth_pct = 100 x (BUY decisions / successfully scored stocks)

where  BUY  &lt;=&gt;  confluence_score &gt;= {THR}
       confluence_score = count of active bullish signals, 0..{NSIG}</div>
  <p>The denominator is <em>scored</em> stocks, not the full universe. A ticker
  that fails the data-completeness gate on a given day &mdash; fewer than {MINS}
  clean sessions in the trailing year, a halt, a failed download &mdash; is
  excluded from both numerator and denominator rather than counted as a
  non-signal. Counting it as a miss would depress breadth for a data reason
  rather than a market reason.</p>

  <h2>How to read it</h2>
  <table class="qm-kv">
    <thead><tr><th>Breadth</th><th>Label</th><th>What it implies</th></tr></thead>
    <tbody>
      <tr><td class="qm-num">&ge; 60%</td><td>Broad participation</td><td>Most of the universe is in a confirmed uptrend. The BUY flag is at its least selective, and the score column carries more information than the flag.</td></tr>
      <tr><td class="qm-num">40&ndash;60%</td><td>Mixed</td><td>Roughly half qualifies. Sector dispersion usually matters more than the aggregate.</td></tr>
      <tr><td class="qm-num">20&ndash;40%</td><td>Narrow</td><td>Setups concentrate in fewer names and sectors.</td></tr>
      <tr><td class="qm-num">&lt; 20%</td><td>Few qualifying setups</td><td>The engine goes quiet by design rather than forcing low-conviction output.</td></tr>
    </tbody>
  </table>
  <p>These bands are a vocabulary, not a model. They are a descriptive split of
  one number, published so the wording stays consistent between updates and so
  anyone can disagree with where the lines sit.</p>

  <h2>Limitations</h2>
  <ul>
    <li><strong>It is not a forecast.</strong> Breadth describes the state of the
    scan on a completed session. Nothing here is evidence that high or low
    breadth predicts subsequent returns, and QuantMedia publishes no study
    claiming it does.</li>
    <li><strong>The universe is fixed and curated.</strong> {UNI} liquid
    US-listed names, not an index. Breadth measured on a different universe
    would produce a different number, and the two are not comparable.</li>
    <li><strong>Trend-following bias.</strong> The underlying signals are
    momentum- and trend-weighted, so breadth mechanically rises in sustained
    advances and collapses at turning points. It lags inflections.</li>
    <li><strong>Short history.</strong> The series starts when it was first
    published and is not backfilled, because the scan was not run historically
    under this methodology. Backfilling it would be inventing data.</li>
    <li><strong>Threshold sensitivity.</strong> Breadth is defined against a
    fixed threshold of {THR}. When the median score sits near the threshold,
    small score shifts move breadth sharply.</li>
  </ul>

  <h2>History</h2>
  <p>One record per completed US trading session. The series starts on the day
  it was first published and is <strong>not backfilled</strong> &mdash; the scan
  was not run historically under this methodology, so earlier values do not
  exist and inventing them would be fabrication. Duplicate dates are impossible
  by construction: an existing record for a market date is replaced, never
  appended alongside.</p>
  <div id="qm-breadth-history">
    <p class="qm-note">History loads from
    <a href="/data/breadth_history.json">/data/breadth_history.json</a>. The
    full series is always available there as JSON even when the table below is
    still short.</p>
  </div>
""" + _BREADTH_CHART_JS + f"""

  <h2>Data and refresh</h2>
  <table class="qm-kv"><tbody>
    <tr><th>Source</th><td>QuantMedia post-close signal scan (end-of-day OHLCV via Yahoo Finance / yfinance)</td></tr>
    <tr><th>Methodology version</th><td>2.0 (effective 2026-04-14) &mdash; stamped into every record</td></tr>
    <tr><th>Cadence</th><td>Every US trading day, published after 23:30 UTC</td></tr>
    <tr><th>Machine-readable</th><td><a href="/data/signal_breadth.json">/data/signal_breadth.json</a> &middot; <a href="/data/breadth_history.json">/data/breadth_history.json</a></td></tr>
    <tr><th>Methodology config</th><td><a href="/data/signal_config.json">/data/signal_config.json</a></td></tr>
    <tr><th>Citation</th><td>Free to cite with attribution to QuantMedia and the market date</td></tr>
  </tbody></table>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/indices/sector-confluence.html">QuantMedia Sector Confluence</a><span>The same scan broken down by sector, ranked by mean score</span></li>
    <li><a href="/learn/what-is-market-breadth.html">What is market breadth?</a><span>How this measure compares to advance/decline and percent-above-MA</span></li>
    <li><a href="/learn/what-is-signal-confluence.html">What is signal confluence?</a><span>How the underlying score is built</span></li>
    <li><a href="/quantum-signals.html">Daily US stock signals</a><span>The per-stock table this metric aggregates</span></li>
    <li><a href="/methodology.html#signal-engine">Signal engine methodology</a><span>Full parameter documentation</span></li>
  </ul>
"""


SECTOR_BODY = f"""
  <p class="qm-lede">Sector Confluence is a QuantMedia metric. It takes the same
  post-close scan behind the <a href="/quantum-signals.html">daily signal
  dashboard</a> and groups it by sector, so you can see <em>where</em> technical
  agreement is concentrated rather than only how much of it exists in
  aggregate.</p>

  <div class="qm-answer">
    <span class="qm-answer-label">Definition</span>
    <p><strong>QuantMedia Sector Confluence</strong> is the mean confluence score
    and BUY breadth of each sector within the {UNI}-name scan universe, computed
    from one post-close run and ranked by mean score. A sector mean of 24 out of
    {NSIG} means the average stock in that sector had 24 signals simultaneously
    bullish &mdash; comfortably above the {THR} threshold.</p>
  </div>

  <h2>Current reading</h2>
  <!-- QM:SECTORS:START -->
  <p class="qm-note">The current reading publishes after the next post-close scan.</p>
  <!-- QM:SECTORS:END -->

  <h2>Method</h2>
  <div class="qm-formula">for each sector S:
    mean_score   = mean(confluence_score of scored members of S)
    median_score = median(confluence_score of scored members of S)
    breadth_pct  = 100 x (BUY members of S / scored members of S)
    rank         = position when sorted by mean_score desc, breadth as tiebreak

sectors with fewer than {C.MIN_SECTOR_SIZE} scored members are omitted</div>
  <p>Ranking uses the mean rather than breadth because breadth saturates: once
  most of a sector clears the threshold, breadth stops distinguishing between a
  sector averaging {THR} and one averaging 27. The mean keeps separating them.
  Both are shown so you can see when they disagree &mdash; a high mean with low
  breadth means a few very strong names carrying an otherwise flat sector.</p>

  <h2>Sector grouping</h2>
  <p>The grouping is hand-maintained by QuantMedia and approximates GICS without
  being it. Most assignments are uncontroversial. The exception is a small
  clean-energy cohort of solar manufacturers and residential installers, which
  GICS splits across Information Technology, Industrials and Utilities; these
  are grouped together here because they trade as a cohort, and separating them
  would leave buckets too small to average. Calling the mapping GICS would claim
  an accuracy it does not have.</p>
  <p>Sector membership is fixed to the scan universe, so a sector's constituent
  count reflects QuantMedia's liquidity list rather than the sector's true size
  in the market. Utilities, for example, has three members here and is reported
  only because it clears the minimum &mdash; it is not a representative sample
  of US utilities.</p>

  <h2>Limitations</h2>
  <ul>
    <li><strong>Small samples.</strong> Several sectors have fewer than ten
    scored members. A single stock moves the mean materially. Constituent counts
    are shown for exactly this reason.</li>
    <li><strong>Not sector allocation advice.</strong> A top rank means recent
    technical agreement, and nothing about valuation, fundamentals or forward
    return.</li>
    <li><strong>Same trend bias as the underlying signals.</strong> Sectors that
    have already run tend to rank highest, which is a property of momentum
    scoring rather than a discovery.</li>
    <li><strong>Universe-dependent.</strong> Computed on {UNI} liquid names, not
    on sector ETFs or full sector membership. Readings are not comparable to
    XLK/XLF-style ETF performance.</li>
  </ul>

  <h2>Data and refresh</h2>
  <table class="qm-kv"><tbody>
    <tr><th>Source</th><td>QuantMedia post-close signal scan</td></tr>
    <tr><th>Cadence</th><td>Every US trading day, published after 23:30 UTC</td></tr>
    <tr><th>Machine-readable</th><td><a href="/data/sector_confluence.json">/data/sector_confluence.json</a></td></tr>
    <tr><th>Citation</th><td>Free to cite with attribution to QuantMedia and the market date</td></tr>
  </tbody></table>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/indices/signal-breadth.html">QuantMedia Signal Breadth</a><span>The aggregate this metric decomposes</span></li>
    <li><a href="/sector-rotation-guide.html">Sector rotation guide</a><span>How capital moves between S&amp;P 500 sectors</span></li>
    <li><a href="/learn/what-is-signal-confluence.html">What is signal confluence?</a><span>The score being averaged here</span></li>
    <li><a href="/stocks.html">US equities screener</a><span>Sector ETF context</span></li>
  </ul>
"""


# ===========================================================================
# /learn/ - answer pages built around questions people actually ask
# ===========================================================================

VPIN_BODY = """
  <div class="qm-answer">
    <span class="qm-answer-label">Short answer</span>
    <p>VPIN (Volume-Synchronized Probability of Informed Trading) estimates how
    <em>toxic</em> order flow is &mdash; that is, how likely it is that the
    counterparties trading against a market maker are better informed. It works
    by splitting trading activity into equal-volume buckets rather than equal
    time intervals, classifying each bucket's volume as buy- or sell-initiated,
    and averaging the absolute imbalance. Readings near 1 indicate heavily
    one-sided, likely informed flow; readings near 0 indicate balanced flow.</p>
  </div>

  <h2>Why time buckets fail and volume buckets do not</h2>
  <p>The idea VPIN replaced was PIN, which estimated informed trading from daily
  buy and sell counts using a maximum-likelihood fit. That approach struggles
  once trading becomes fast and uneven: in modern markets, a single minute at
  the open can carry more volume than an hour at midday, so a clock-based window
  mixes a frantic period and a quiet one into the same observation.</p>
  <p>VPIN's central move is to stop using the clock. Volume is accumulated until
  a fixed bucket size is reached, and only then is the bucket closed. Every
  bucket therefore represents the same amount of economic activity, which makes
  buckets comparable to one another regardless of how long each took in wall
  time. In an active period buckets close quickly; in a quiet one they take
  longer. This is what &ldquo;volume-synchronized&rdquo; means.</p>

  <h2>Formula</h2>
  <div class="qm-formula">Split the tape into n buckets of equal volume V.

For bucket i, classify volume into buy-initiated (Vb) and sell-initiated (Vs),
so that  Vb_i + Vs_i = V.

                 1     n
    VPIN  =  ------- * SUM  | Vb_i - Vs_i |
              n * V   i = 1

VPIN is bounded in [0, 1]:
    0  ->  every bucket perfectly balanced
    1  ->  every bucket entirely one-sided</div>

  <h2>Worked example</h2>
  <p>Take a bucket size of V = 100,000 shares and four completed buckets:</p>
  <table class="qm-kv">
    <thead><tr><th>Bucket</th><th>Buy volume</th><th>Sell volume</th><th>|Imbalance|</th></tr></thead>
    <tbody>
      <tr><td class="qm-num">1</td><td class="qm-num">55,000</td><td class="qm-num">45,000</td><td class="qm-num">10,000</td></tr>
      <tr><td class="qm-num">2</td><td class="qm-num">80,000</td><td class="qm-num">20,000</td><td class="qm-num">60,000</td></tr>
      <tr><td class="qm-num">3</td><td class="qm-num">48,000</td><td class="qm-num">52,000</td><td class="qm-num">4,000</td></tr>
      <tr><td class="qm-num">4</td><td class="qm-num">90,000</td><td class="qm-num">10,000</td><td class="qm-num">80,000</td></tr>
    </tbody>
  </table>
  <div class="qm-formula">VPIN = (10,000 + 60,000 + 4,000 + 80,000) / (4 x 100,000)
     = 154,000 / 400,000
     = 0.385</div>
  <p>0.385 means that, on average, about 38.5% of each bucket's volume was
  unmatched directional pressure. Two of the four buckets (2 and 4) are doing
  almost all the work &mdash; which is typical, and a reason to look at the
  distribution of bucket imbalances rather than the average alone.</p>

  <h2>Where the buy/sell split comes from</h2>
  <p>Exchange tapes do not label trades as buyer- or seller-initiated, so the
  split has to be inferred. Two common approaches:</p>
  <ul>
    <li><strong>Tick rule / Lee-Ready:</strong> compare the trade price to the
    prevailing quote midpoint or to the previous trade. Simple, but degrades
    when quotes move faster than trades are reported.</li>
    <li><strong>Bulk volume classification (BVC):</strong> the method used in
    the original VPIN work. Rather than classifying each trade, it assigns a
    <em>fraction</em> of each bar's volume to buys using the standardised price
    change, typically via a Student-t or normal CDF. This is more robust to
    timestamp noise and is why VPIN is usually computed on bars rather than
    individual prints.</li>
  </ul>
  <p>The choice matters: published VPIN levels are not comparable across studies
  unless the classification method, bucket size and sample window all match.</p>

  <h2>What a high reading actually means</h2>
  <p>A high VPIN says order flow has been persistently one-sided. For a liquidity
  provider that is a warning about adverse selection: the probability of being
  filled by someone who knows more rises, so quoting the same spread becomes
  more expensive. The documented response is to widen spreads or withdraw, which
  is the mechanism connecting toxicity to liquidity deterioration.</p>
  <p>What it does <strong>not</strong> say is which direction price will go.
  VPIN uses the absolute imbalance, so a heavily bought and a heavily sold
  bucket produce the same contribution. It is a measure of one-sidedness, not
  of direction.</p>

  <h2>Limitations</h2>
  <ul>
    <li><strong>Contested predictive value.</strong> VPIN's role in the 2010
    Flash Crash has been actively disputed in the literature, notably by Andersen
    and Bondarenko, who argue much of its apparent forecasting power reflects
    volume-volatility mechanics rather than information. Treat it as a
    descriptive microstructure statistic, not an established early-warning
    indicator.</li>
    <li><strong>Highly parameter-dependent.</strong> Bucket size, the number of
    buckets in the moving window and the classification method all move the
    level. Absolute values are close to meaningless without those parameters.</li>
    <li><strong>Needs real tick or bar data.</strong> VPIN cannot be computed
    from end-of-day OHLCV. <em>QuantMedia does not publish a live VPIN reading
    for this reason</em> &mdash; the data pipeline collects daily bars, not
    order flow, and estimating it anyway would be fabrication.</li>
    <li><strong>Relative, not absolute.</strong> A reading is interpretable
    against that instrument's own recent history, not against a universal
    threshold.</li>
  </ul>

  <h2>References</h2>
  <ul class="qm-refs">
    <li>Easley, D., L&oacute;pez de Prado, M. &amp; O'Hara, M. (2012).
    &ldquo;Flow Toxicity and Liquidity in a High-Frequency World.&rdquo;
    <em>Review of Financial Studies</em> 25(5), 1457&ndash;1493.
    <a href="https://doi.org/10.1093/rfs/hhs053" rel="noopener" target="_blank">doi:10.1093/rfs/hhs053</a></li>
    <li>Easley, D., L&oacute;pez de Prado, M. &amp; O'Hara, M. (2011).
    &ldquo;The Microstructure of the Flash Crash.&rdquo;
    <em>Journal of Portfolio Management</em> 37(2), 118&ndash;128.</li>
    <li>Andersen, T. &amp; Bondarenko, O. (2014). &ldquo;VPIN and the Flash
    Crash.&rdquo; <em>Journal of Financial Markets</em> 17, 1&ndash;46.
    <a href="https://doi.org/10.1016/j.finmar.2013.05.005" rel="noopener" target="_blank">doi:10.1016/j.finmar.2013.05.005</a></li>
    <li>Lee, C. &amp; Ready, M. (1991). &ldquo;Inferring Trade Direction from
    Intraday Data.&rdquo; <em>Journal of Finance</em> 46(2), 733&ndash;746.</li>
  </ul>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/paper-vpin-order-flow-toxicity.html">VPIN &amp; Order Flow Toxicity</a><span>The full QuantMedia research paper</span></li>
    <li><a href="/paper-bid-ask-spread-dynamics.html">Bid-Ask Spread Dynamics</a><span>How adverse selection widens quoted spreads</span></li>
    <li><a href="/learn/how-to-model-slippage-in-backtests.html">How to model slippage in backtests</a><span>What toxicity costs in execution terms</span></li>
    <li><a href="/methodology.html">Methodology &amp; data sources</a><span>What QuantMedia does and does not collect</span></li>
  </ul>
"""


PSR_BODY = """
  <div class="qm-answer">
    <span class="qm-answer-label">Short answer</span>
    <p>The Probabilistic Sharpe Ratio (PSR) is the probability that a strategy's
    <em>true</em> Sharpe ratio exceeds a chosen benchmark, given the Sharpe you
    observed, the length of the track record, and the skewness and kurtosis of
    the returns. It converts a point estimate into a confidence statement. A
    Sharpe of 1.5 over 24 months with negatively skewed, fat-tailed returns can
    easily carry a PSR below 0.90, meaning the evidence does not support the
    claim at conventional confidence.</p>
  </div>

  <h2>The problem it solves</h2>
  <p>A Sharpe ratio is an estimate from a sample, so it carries estimation error.
  Two strategies both reporting 1.5 are not equally credible if one has three
  years of history and the other has three months. Worse, the standard error of
  the Sharpe estimator depends on the <em>shape</em> of the return distribution:
  negative skew and excess kurtosis &mdash; exactly what option-selling and
  carry strategies produce &mdash; inflate it. Those strategies look best
  precisely where the metric is least reliable.</p>
  <p>PSR, introduced by Bailey and L&oacute;pez de Prado, restates the question:
  instead of &ldquo;what is the Sharpe?&rdquo; it asks &ldquo;what is the
  probability the true Sharpe beats a threshold?&rdquo;</p>

  <h2>Formula</h2>
  <div class="qm-formula">                  ( SR_hat - SR* ) * sqrt( n - 1 )
PSR(SR*) = Z [ ---------------------------------------------------- ]
                sqrt( 1 - g1*SR_hat + ((g2 - 1)/4)*SR_hat^2 )

  Z        standard normal CDF
  SR_hat   observed Sharpe ratio (same frequency as the returns)
  SR*      benchmark Sharpe being tested against (often 0)
  n        number of return observations
  g1       skewness of returns
  g2       kurtosis of returns (normal = 3)</div>
  <p>Read the denominator carefully, because that is where the intuition lives.
  Negative skew (g1 &lt; 0) makes the term <code>-g1*SR_hat</code> positive,
  which enlarges the denominator, shrinks the statistic and lowers PSR. Excess
  kurtosis (g2 &gt; 3) does the same. Longer track records raise
  <code>sqrt(n-1)</code> and push PSR up.</p>

  <h2>Worked example</h2>
  <p>Two years of monthly returns, n = 24, both strategies reporting the same
  headline Sharpe of 1.50:</p>
  <table class="qm-kv">
    <thead><tr><th>Input</th><th>Strategy A</th><th>Strategy B</th></tr></thead>
    <tbody>
      <tr><th>Observed Sharpe</th><td class="qm-num">1.50</td><td class="qm-num">1.50</td></tr>
      <tr><th>Skewness &gamma;&#8321;</th><td class="qm-num">0.00</td><td class="qm-num">&minus;1.20</td></tr>
      <tr><th>Kurtosis &gamma;&#8322;</th><td class="qm-num">3.0</td><td class="qm-num">7.0</td></tr>
      <tr><th>Denominator</th><td class="qm-num">1.4577</td><td class="qm-num">2.4850</td></tr>
      <tr><th>z, against SR* = 0</th><td class="qm-num">4.935</td><td class="qm-num">2.895</td></tr>
      <tr><th>PSR, against SR* = 0</th><td class="qm-num">1.0000</td><td class="qm-num">0.9981</td></tr>
      <tr><th>z, against SR* = 1.0</th><td class="qm-num">1.645</td><td class="qm-num">0.965</td></tr>
      <tr><th>PSR, against SR* = 1.0</th><td class="qm-num">0.9500</td><td class="qm-num">0.8327</td></tr>
    </tbody>
  </table>
  <p>Working strategy A's denominator explicitly, because the kurtosis term
  catches people out &mdash; it does <em>not</em> vanish at &gamma;&#8322; = 3:</p>
  <div class="qm-formula">den = sqrt( 1 - 0.00*1.50 + ((3.0 - 1)/4)*1.50^2 )
    = sqrt( 1 + 0.5*2.25 )
    = sqrt( 2.125 )
    = 1.4577</div>
  <p>Against a zero benchmark both look fine. Raise the benchmark to a Sharpe
  of 1.0 &mdash; the question an allocator with a passive alternative actually
  asks &mdash; and they separate sharply: A lands exactly on the 0.95 bar,
  while B falls to 0.83 and fails it. Identical headline Sharpe, materially
  different evidence. That is the entire point of the measure.</p>
  <p>Note the annualisation trap in this example: if SR_hat is annualised, n
  must still be the number of <em>observations</em> (24 months), and SR_hat and
  SR* must be expressed at the same frequency. Mixing an annualised Sharpe with
  a monthly observation count is the single most common implementation error.</p>

  <h2>How to use it</h2>
  <ul>
    <li><strong>0.95 is the conventional bar.</strong> Below it, the track record
    does not support the claim at 95% confidence &mdash; which is a statement
    about evidence, not about the strategy being bad.</li>
    <li><strong>Set SR* to something meaningful.</strong> Testing against zero is
    a weak hurdle. Testing against the Sharpe of a passive alternative is the
    question an allocator actually cares about.</li>
    <li><strong>Use it to size track-record requirements.</strong> Inverting the
    formula gives the minimum track record length needed for a given observed
    Sharpe to clear 0.95 &mdash; often far longer than practitioners expect.</li>
  </ul>

  <h2>Limitations</h2>
  <ul>
    <li><strong>It does not correct for selection bias.</strong> PSR evaluates
    one track record. If you tested 200 strategies and are reporting the best,
    PSR is the wrong tool &mdash; the <a href="/learn/deflated-sharpe-ratio.html" style="color:var(--accent)">Deflated Sharpe Ratio</a> extends it to
    account for the number of trials.</li>
    <li><strong>It assumes IID returns.</strong> Serial correlation, common in
    illiquid or smoothed portfolios, inflates the apparent Sharpe and is not
    handled by the standard formulation.</li>
    <li><strong>Higher moments are themselves estimated.</strong> Skewness and
    kurtosis from short samples are noisy, and the correction is only as good as
    those estimates.</li>
    <li><strong>Backtest Sharpe is not live Sharpe.</strong> PSR says nothing
    about costs, capacity, or whether the strategy was fitted to the sample.</li>
  </ul>

  <h2>References</h2>
  <ul class="qm-refs">
    <li>Bailey, D. &amp; L&oacute;pez de Prado, M. (2012). &ldquo;The Sharpe
    Ratio Efficient Frontier.&rdquo; <em>Journal of Risk</em> 15(2), 3&ndash;44.</li>
    <li>Bailey, D. &amp; L&oacute;pez de Prado, M. (2014). &ldquo;The Deflated
    Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and
    Non-Normality.&rdquo; <em>Journal of Portfolio Management</em> 40(5),
    94&ndash;107.</li>
    <li>Lo, A. (2002). &ldquo;The Statistics of Sharpe Ratios.&rdquo;
    <em>Financial Analysts Journal</em> 58(4), 36&ndash;52.</li>
  </ul>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/tools/probabilistic-sharpe-ratio-calculator.html">PSR calculator</a><span>Compute PSR from your own inputs</span></li>
    <li><a href="/learn/deflated-sharpe-ratio.html">What is the Deflated Sharpe Ratio?</a><span>The correction to use when the strategy is the best of many you tested</span></li>
    <li><a href="/paper-probabilistic-sharpe-ratio.html">Probabilistic Sharpe Ratio</a><span>The full QuantMedia research paper</span></li>
    <li><a href="/learn/hrp-vs-mean-variance.html">HRP vs mean-variance</a><span>Another case where estimation error dominates</span></li>
  </ul>
"""


HRP_BODY = """
  <div class="qm-answer">
    <span class="qm-answer-label">Short answer</span>
    <p>Mean-variance optimisation finds mathematically optimal weights for the
    inputs you give it, but it requires inverting a covariance matrix, which
    makes it extremely sensitive to estimation error &mdash; small changes in
    expected returns produce wildly different, highly concentrated portfolios.
    Hierarchical Risk Parity (HRP) avoids matrix inversion entirely: it clusters
    assets by correlation, then allocates risk down the resulting tree. HRP is
    usually more stable out of sample; mean-variance is usually better in
    sample. Neither is universally better.</p>
  </div>

  <h2>Why mean-variance misbehaves</h2>
  <p>Markowitz optimisation solves for weights using the inverse covariance
  matrix. That inversion is the problem. Covariance matrices estimated from
  finite samples are close to singular when assets are highly correlated &mdash;
  which they are, especially in stress &mdash; and inverting a near-singular
  matrix amplifies estimation noise enormously.</p>
  <p>The practical symptoms are well documented: extreme long-short weights,
  concentration in a handful of assets, and instability where re-estimating on
  one extra month of data reshuffles the whole portfolio. Michaud's description
  of the optimiser as an &ldquo;error maximiser&rdquo; captures it: the assets
  with the most overstated returns and understated risk get the largest weights,
  precisely because their estimates are wrong.</p>

  <h2>What HRP does instead</h2>
  <p>HRP, introduced by L&oacute;pez de Prado, replaces optimisation with three
  deterministic steps. It <strong>never inverts</strong> a matrix at any point,
  and it requires no expected-return vector &mdash; which removes the two
  inputs that cause most of the trouble above.</p>
  <div class="qm-formula">1. TREE CLUSTERING
   Convert the correlation matrix to a distance metric
       d(i,j) = sqrt( 0.5 * (1 - rho(i,j)) )
   and build a hierarchical clustering tree.

2. QUASI-DIAGONALISATION
   Reorder the covariance matrix so that similar assets sit adjacent.
   Large values move toward the diagonal; the structure becomes visible.

3. RECURSIVE BISECTION
   Walk the tree top-down. At each split, allocate between the two
   sub-clusters inversely to their variance:

       alpha = 1 - Var(L) / ( Var(L) + Var(R) )

   Recurse until every leaf holds a single asset.</div>
  <p>The distance transform matters more than it looks. Raw <code>1 &minus;
  rho</code> is not a metric &mdash; it violates the <strong>triangle
  inequality</strong>, so clustering on it can produce trees that contradict
  themselves. The square-root form above is a proper metric, which is what
  makes the hierarchy well defined.</p>

  <h3>Does HRP produce negative weights?</h3>
  <p>No. HRP as specified is <strong>long-only</strong>: recursive bisection
  multiplies positive fractions down the tree, so every weight is
  <strong>positive</strong> and they sum to 1 by construction. There is no
  short book to constrain away. Unconstrained mean-variance, by contrast,
  routinely returns large offsetting long and short positions &mdash; in the
  comparison below it produced an 11% short book on a long-only universe.</p>

  <h2>Direct comparison</h2>
  <table class="qm-kv">
    <thead><tr><th></th><th>Mean-variance</th><th>HRP</th></tr></thead>
    <tbody>
      <tr><th>Requires expected returns</th><td>Yes</td><td>No</td></tr>
      <tr><th>Inverts covariance matrix</th><td>Yes</td><td>No</td></tr>
      <tr><th>Behaviour with correlated assets</th><td>Degrades sharply</td><td>Handles via clustering</td></tr>
      <tr><th>Typical concentration</th><td>High</td><td>Lower</td></tr>
      <tr><th>Turnover on re-estimation</th><td>High</td><td>Lower</td></tr>
      <tr><th>In-sample efficiency</th><td>Optimal by construction</td><td>Sub-optimal by construction</td></tr>
      <tr><th>Out-of-sample variance</th><td>Often worse</td><td>Often better</td></tr>
      <tr><th>Guaranteed better live?</th><td colspan="2">No. Depends on the universe, estimation window and rebalancing rule.</td></tr>
    </tbody>
  </table>

  <h2>So is HRP better?</h2>
  <p>Not unconditionally, and claims that it is should be treated sceptically.
  What the evidence supports is narrower and more useful: HRP tends to produce
  <em>lower out-of-sample variance and lower turnover</em> than unconstrained
  mean-variance on correlated, realistically sized universes. That advantage
  comes from not needing the inputs that are hardest to estimate, not from any
  claim to superior returns.</p>
  <p>Two honest caveats. First, much of mean-variance's practical failure is
  addressed by constraints, shrinkage estimators such as Ledoit-Wolf, or
  resampling &mdash; a well-regularised mean-variance portfolio is a much
  stronger opponent than the textbook version. Second, HRP has free parameters
  of its own: the linkage method and distance metric change the tree, and
  therefore the weights.</p>

  <h2>Limitations</h2>
  <ul>
    <li><strong>No return objective.</strong> HRP allocates risk. If you have
    genuine return forecasts, discarding them is a real cost.</li>
    <li><strong>Clustering is a modelling choice.</strong> Single, average and
    ward linkage give different trees and different portfolios.</li>
    <li><strong>Correlation instability.</strong> Correlations converge in
    crises, which flattens the tree exactly when diversification matters most.</li>
    <li><strong>Sub-optimal in sample, always.</strong> Any comparison run in
    sample will favour mean-variance by construction. Only out-of-sample
    comparisons are informative.</li>
  </ul>

  <h2>References</h2>
  <ul class="qm-refs">
    <li>L&oacute;pez de Prado, M. (2016). &ldquo;Building Diversified Portfolios
    that Outperform Out of Sample.&rdquo; <em>Journal of Portfolio Management</em>
    42(4), 59&ndash;69.</li>
    <li>Markowitz, H. (1952). &ldquo;Portfolio Selection.&rdquo;
    <em>Journal of Finance</em> 7(1), 77&ndash;91.</li>
    <li>Michaud, R. (1989). &ldquo;The Markowitz Optimization Enigma: Is
    Optimized Optimal?&rdquo; <em>Financial Analysts Journal</em> 45(1), 31&ndash;42.</li>
    <li>Ledoit, O. &amp; Wolf, M. (2004). &ldquo;A Well-Conditioned Estimator for
    Large-Dimensional Covariance Matrices.&rdquo; <em>Journal of Multivariate
    Analysis</em> 88(2), 365&ndash;411.</li>
  </ul>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/paper-hierarchical-risk-parity.html">Hierarchical Risk Parity</a><span>The full QuantMedia research paper</span></li>
    <li><a href="/learn/what-is-probabilistic-sharpe-ratio.html">What is the Probabilistic Sharpe Ratio?</a><span>Judging whether a performance difference is real</span></li>
  </ul>
"""


SLIPPAGE_BODY = """
  <div class="qm-answer">
    <span class="qm-answer-label">Short answer</span>
    <p>Model slippage as three separate components rather than one flat number:
    the spread you cross, the market impact your own order causes, and the delay
    cost from latency between signal and fill. A single &ldquo;5 basis
    points&rdquo; assumption is the most common way backtests overstate returns,
    because impact scales with the square root of participation rate &mdash; so
    costs grow non-linearly as size increases, exactly where a naive constant
    assumption says nothing changes.</p>
  </div>

  <h2>Decompose before you estimate</h2>
  <table class="qm-kv">
    <thead><tr><th>Component</th><th>What causes it</th><th>Scales with</th></tr></thead>
    <tbody>
      <tr><td><strong>Spread cost</strong></td><td>Crossing from mid to the far touch</td><td>Half-spread, roughly constant per trade</td></tr>
      <tr><td><strong>Market impact</strong></td><td>Your order consuming book depth</td><td>~ sqrt(order size / ADV)</td></tr>
      <tr><td><strong>Delay cost</strong></td><td>Price drift between decision and fill</td><td>Volatility x sqrt(latency)</td></tr>
      <tr><td><strong>Opportunity cost</strong></td><td>Unfilled portion of the order</td><td>Fill rate and subsequent drift</td></tr>
    </tbody>
  </table>

  <h2>A workable model</h2>
  <div class="qm-formula">total_cost_bps = half_spread_bps
                 + k * sigma * sqrt( Q / ADV ) * 10000
                 + sigma * sqrt( latency_seconds / 23400 ) * 10000

  Q        order quantity (shares)
  ADV      average daily volume (shares)
  sigma    daily volatility, decimal (0.02 = 2%)
  k        impact coefficient, empirically ~0.5-1.0 for US large caps
  23400    seconds in a 6.5-hour session</div>
  <p>The square-root impact law is the part worth internalising. It has held up
  across markets and decades of研究 and is the reason capacity is a real
  constraint: doubling order size does not double impact, it multiplies it by
  about 1.41 &mdash; but that still means impact per share rises with size.</p>

  <h2>Worked example</h2>
  <p>Buying 50,000 shares of a stock with 5,000,000 ADV, 2% daily volatility,
  a 2 bp half-spread, k = 0.7, and 250 ms from signal to fill:</p>
  <div class="qm-formula">participation = 50,000 / 5,000,000 = 0.01  (1% of ADV)

spread  = 2.0 bp
impact  = 0.7 * 0.02 * sqrt(0.01) * 10000 = 14.0 bp
delay   = 0.02 * sqrt(0.25 / 23400) * 10000 = 0.65 bp

total   = 16.7 bp per side
round trip = 33.4 bp</div>
  <p>Now scale the order to 500,000 shares (10% of ADV) and impact becomes
  <code>0.7 * 0.02 * sqrt(0.10) * 10000 = 44.3 bp</code>. Ten times the size
  produced a bit over three times the impact per share &mdash; but total cost
  in dollars rose more than thirtyfold. A backtest using a flat 5 bp would have
  charged the same rate for both.</p>

  <h2>What this does to a strategy</h2>
  <p>Cost compounds with turnover, which is where plausible-looking edges die:</p>
  <table class="qm-kv">
    <thead><tr><th>Annual turnover</th><th>Round trips</th><th>At 33 bp/round trip</th></tr></thead>
    <tbody>
      <tr><td class="qm-num">1x</td><td class="qm-num">1</td><td class="qm-num">-0.33%</td></tr>
      <tr><td class="qm-num">12x</td><td class="qm-num">12</td><td class="qm-num">-4.0%</td></tr>
      <tr><td class="qm-num">52x</td><td class="qm-num">52</td><td class="qm-num">-17.4%</td></tr>
      <tr><td class="qm-num">252x</td><td class="qm-num">252</td><td class="qm-num">-83.2%</td></tr>
    </tbody>
  </table>
  <p>A daily-rebalanced strategy needs to gross more than 80% annually just to
  break even on execution at this cost level. This is why turnover, not signal
  quality, is usually the binding constraint on high-frequency approaches.</p>

  <h2>Practical rules</h2>
  <ul>
    <li><strong>Never use one constant.</strong> At minimum, make cost a function
    of participation rate.</li>
    <li><strong>Cap participation in the backtest.</strong> If a fill needs more
    than 5&ndash;10% of ADV, the backtest should reject or split it, not assume
    it filled at the close.</li>
    <li><strong>Charge the spread you would actually pay.</strong> Quoted spreads
    at the open and close differ by multiples from midday.</li>
    <li><strong>Test sensitivity, not a point estimate.</strong> Re-run at k =
    0.5, 1.0 and 1.5. If the edge disappears, it was never robust.</li>
    <li><strong>Model partial fills.</strong> Assuming complete fills at the
    signal price is optimistic in exactly the conditions where signals fire.</li>
  </ul>

  <h2>Limitations</h2>
  <ul>
    <li>The square-root law is an empirical regularity, not a physical constant;
    k varies by asset, venue and regime.</li>
    <li>It describes typical conditions. In stress, impact is materially higher
    and liquidity can vanish, so tail scenarios need separate treatment.</li>
    <li>The model above ignores fees, borrow costs and taxes, all of which are
    real and strategy-specific.</li>
  </ul>

  <h2>References</h2>
  <ul class="qm-refs">
    <li>Almgren, R. &amp; Chriss, N. (2001). &ldquo;Optimal Execution of Portfolio
    Transactions.&rdquo; <em>Journal of Risk</em> 3(2), 5&ndash;40.</li>
    <li>Almgren, R., Thum, C., Hauptmann, E. &amp; Li, H. (2005). &ldquo;Direct
    Estimation of Equity Market Impact.&rdquo; <em>Risk</em> 18(7), 58&ndash;62.</li>
    <li>Kyle, A. (1985). &ldquo;Continuous Auctions and Insider Trading.&rdquo;
    <em>Econometrica</em> 53(6), 1315&ndash;1335.</li>
    <li>Perold, A. (1988). &ldquo;The Implementation Shortfall: Paper versus
    Reality.&rdquo; <em>Journal of Portfolio Management</em> 14(3), 4&ndash;9.</li>
  </ul>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/paper-slippage-latency-modeling.html">Slippage &amp; Latency Modeling</a><span>The full QuantMedia research paper</span></li>
    <li><a href="/paper-bid-ask-spread-dynamics.html">Bid-Ask Spread Dynamics</a><span>Where the spread component comes from</span></li>
    <li><a href="/learn/what-is-vpin.html">What is VPIN?</a><span>Why spreads widen when flow turns toxic</span></li>
  </ul>
"""


CONFLUENCE_BODY = f"""
  <div class="qm-answer">
    <span class="qm-answer-label">Short answer</span>
    <p>Signal confluence means requiring several independent technical
    conditions to agree before acting, instead of trusting any one indicator.
    QuantMedia's engine scores each stock against {NSIG} binary checks &mdash;
    trend, momentum, volume, volatility and 52-week position &mdash; and flags
    a BUY only when at least {THR} are simultaneously bullish, roughly
    {E['agreement_pct']}% agreement. The purpose is to filter noise, and the
    cost is that confluence systems are structurally late at turning points.</p>
  </div>

  <h2>The reasoning</h2>
  <p>Any single technical indicator produces frequent false positives. RSI drops
  below 30 often in a downtrend that continues; moving-average crossovers whipsaw
  in ranges. Requiring agreement across indicator <em>families</em> that respond
  to different market properties raises the bar for a signal to fire.</p>
  <p>The important caveat is that confluence is not statistical independence.
  Technical indicators computed from the same price series are heavily
  correlated: if price is above its 5-, 10-, 20- and 50-day averages, those four
  checks pass together almost by construction. So a score of {THR} out of {NSIG}
  does <strong>not</strong> represent {THR} independent confirmations. It
  represents broad agreement among overlapping measurements &mdash; useful, but
  a weaker claim than the raw count suggests.</p>

  <h2>How the score is built</h2>
  <table class="qm-kv">
    <thead><tr><th>Family</th><th>Checks</th><th>What it tests</th></tr></thead>
    <tbody>
      <tr><td>Trend / moving averages</td><td class="qm-num">10</td><td>Price vs SMA(5/10/20/50), MA ordering, EMA(12) vs EMA(26), MACD level and signal cross</td></tr>
      <tr><td>Momentum oscillators</td><td class="qm-num">4</td><td>RSI(14) in the neutral band, RSI(7) vs RSI(14), RSI(21) level, RSI recovery cross</td></tr>
      <tr><td>Rate of change</td><td class="qm-num">4</td><td>5/10/20-day returns, plus a check that short-term momentum is not overextended</td></tr>
      <tr><td>Bollinger Bands</td><td class="qm-num">3</td><td>Position inside the bands and a bounce off the lower band</td></tr>
      <tr><td>Volume</td><td class="qm-num">3</td><td>Current vs 20-day average, 5-day vs 20-day, up-volume vs down-volume</td></tr>
      <tr><td>Stochastic</td><td class="qm-num">2</td><td>%K level and %K vs %D</td></tr>
      <tr><td>52-week position</td><td class="qm-num">2</td><td>Position within the 52-week range</td></tr>
      <tr><td>Volatility regime</td><td class="qm-num">2</td><td>ATR as a share of price, inside a workable band</td></tr>
      <tr><th>Total</th><th class="qm-num">{NSIG}</th><th>BUY at &ge; {THR}</th></tr>
    </tbody>
  </table>
  <p>Each check returns 1 or 0. There is no weighting, no optimisation of the
  threshold against past returns, and no discretionary override. That keeps the
  system un-fitted to any particular period &mdash; and equally means the
  threshold carries no claim of being optimal.</p>

  <h2>Why {THR}, and what that choice costs</h2>
  <p>{THR} of {NSIG} is about {E['agreement_pct']}% agreement. Requiring roughly
  three-quarters of checks to align means a stock generally has to be in a
  broad, confirmed uptrend to qualify. The direct consequences are worth stating
  plainly:</p>
  <ul>
    <li>Signals cluster in rising markets and thin out in falling ones. That is
    the design working, not a malfunction.</li>
    <li>The engine is structurally late at inflections. It cannot flag a bottom,
    because at a bottom almost no trend check passes.</li>
    <li>When the median score sits near {THR}, the BUY flag stops discriminating
    &mdash; half the universe qualifies. On those days the score itself carries
    more information than the flag. <a href="/indices/signal-breadth.html">Signal
    Breadth</a> exists to make that visible.</li>
  </ul>

  <h2>Limitations</h2>
  <ul>
    <li><strong>Correlated inputs.</strong> As above, {THR} checks are not {THR}
    independent pieces of evidence.</li>
    <li><strong>Purely technical.</strong> No earnings, guidance, litigation or
    index-change awareness. A stock can score {NSIG}/{NSIG} the day before a
    profit warning.</li>
    <li><strong>No published track record.</strong> QuantMedia does not publish
    live or audited performance for this engine, because no verified
    out-of-sample record exists to report.</li>
    <li><strong>End-of-day only.</strong> Signals reflect the prior close and can
    be invalidated by overnight news or a gap.</li>
  </ul>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/quantum-signals.html">Daily US stock signals</a><span>The live dashboard this describes</span></li>
    <li><a href="/indices/signal-breadth.html">QuantMedia Signal Breadth</a><span>How much of the universe currently qualifies</span></li>
    <li><a href="/indices/sector-confluence.html">QuantMedia Sector Confluence</a><span>Where the agreement is concentrated</span></li>
    <li><a href="/methodology.html#signal-engine">Signal engine methodology</a><span>Full parameter table</span></li>
  </ul>
"""


BREADTH_LEARN_BODY = f"""
  <div class="qm-answer">
    <span class="qm-answer-label">Short answer</span>
    <p>Market breadth measures how <em>many</em> stocks participate in a move,
    rather than how far an index travelled. An index can rise while breadth
    falls, which means a handful of large constituents are carrying it.
    QuantMedia publishes its own breadth measure &mdash;
    <a href="/indices/signal-breadth.html">Signal Breadth</a> &mdash; defined as
    the share of scored equities meeting a fixed {THR}-of-{NSIG} technical
    threshold, updated after every US close.</p>
  </div>

  <h2>Why breadth and price can disagree</h2>
  <p>A capitalisation-weighted index reflects the largest members
  disproportionately. If five mega-caps rise 5% while 300 smaller members fall
  1%, the index still prints a gain. Breadth measures catch that divergence,
  which is why they are used as a check on the durability of a move rather than
  as a directional signal.</p>

  <h2>Common breadth measures</h2>
  <table class="qm-kv">
    <thead><tr><th>Measure</th><th>Definition</th><th>Notes</th></tr></thead>
    <tbody>
      <tr><td>Advance/decline line</td><td>Cumulative advancers minus decliners</td><td>The classic; sensitive to universe composition</td></tr>
      <tr><td>% above 200-day MA</td><td>Share of members above their long MA</td><td>Slow, widely quoted</td></tr>
      <tr><td>New highs &minus; new lows</td><td>52-week highs minus lows</td><td>Sharp at extremes, quiet otherwise</td></tr>
      <tr><td><strong>QuantMedia Signal Breadth</strong></td><td>Share of scored stocks at &ge; {THR}/{NSIG} signals</td><td>Multi-factor rather than single-condition; fixed universe of {UNI}</td></tr>
    </tbody>
  </table>
  <p>The difference in the last row is that the underlying condition is a
  multi-factor score spanning trend, momentum, volume and volatility, not a
  single moving-average comparison. That makes it a stricter test of
  participation &mdash; a stock can sit above its 200-day average while failing
  most of the other checks.</p>

  <h2>Reading it honestly</h2>
  <ul>
    <li><strong>It is descriptive.</strong> QuantMedia publishes no evidence that
    its breadth reading predicts returns, and does not claim it does.</li>
    <li><strong>Universe matters more than people expect.</strong> Breadth on
    {UNI} liquid large- and mid-caps behaves differently from breadth on 3,000
    listed names. Readings from different universes are not comparable.</li>
    <li><strong>Near-threshold effects.</strong> When the median score sits close
    to {THR}, breadth becomes volatile for reasons that have little to do with
    the market.</li>
    <li><strong>It lags turns.</strong> Trend-weighted inputs mean breadth
    confirms moves rather than anticipating them.</li>
  </ul>

  <h2>Current reading and data</h2>
  <p>The live figure, its distribution and the historical series are published
  on the <a href="/indices/signal-breadth.html">Signal Breadth index page</a>,
  with machine-readable copies at
  <a href="/data/signal_breadth.json">/data/signal_breadth.json</a> and
  <a href="/data/breadth_history.json">/data/breadth_history.json</a>. Both are
  free to cite with attribution to QuantMedia and the market date.</p>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/indices/signal-breadth.html">QuantMedia Signal Breadth</a><span>Current reading, formula and history</span></li>
    <li><a href="/indices/sector-confluence.html">QuantMedia Sector Confluence</a><span>Breadth decomposed by sector</span></li>
    <li><a href="/learn/what-is-signal-confluence.html">What is signal confluence?</a><span>The underlying per-stock score</span></li>
    <li><a href="/sector-rotation-guide.html">Sector rotation guide</a><span>Reading participation across sectors</span></li>
  </ul>
"""


PSR_TOOL_BODY = """
  <p class="qm-lede">This calculator returns the Probabilistic Sharpe Ratio: the
  probability that a strategy's true Sharpe ratio exceeds a chosen benchmark,
  given the observed Sharpe, the track-record length, and the skewness and
  kurtosis of the returns. It runs entirely in your browser &mdash; nothing is
  uploaded or stored.</p>

  <div class="qm-answer">
    <span class="qm-answer-label">What it answers</span>
    <p>A Sharpe ratio is an estimate from a sample. PSR asks the question that
    actually matters to an allocator: <em>given this much data and this return
    shape, how confident can I be that the true Sharpe beats my benchmark?</em>
    A PSR of 0.95 is the conventional bar &mdash; below it, the record does not
    support the claim at 95% confidence.</p>
  </div>

  <h2>Calculator</h2>
  <p class="qm-note">Use Sharpe and benchmark values at the observation frequency,
  not annualized values with a count of daily or monthly observations.
  <a href="/reports/psr-worked-example.html">Follow the worked calculation</a>.</p>
  <div class="calc-grid">
    <div class="calc-field">
      <label for="psr-sr">Observed Sharpe (SR&#770;)</label>
      <input type="number" id="psr-sr" value="1.5" step="0.01">
    </div>
    <div class="calc-field">
      <label for="psr-bm">Benchmark Sharpe (SR*)</label>
      <input type="number" id="psr-bm" value="0" step="0.01">
    </div>
    <div class="calc-field">
      <label for="psr-n">Observations (n)</label>
      <input type="number" id="psr-n" value="24" step="1" min="2">
    </div>
    <div class="calc-field">
      <label for="psr-skew">Skewness (&gamma;&#8321;)</label>
      <input type="number" id="psr-skew" value="-1.2" step="0.1">
    </div>
    <div class="calc-field">
      <label for="psr-kurt">Kurtosis (&gamma;&#8322;, normal = 3)</label>
      <input type="number" id="psr-kurt" value="7" step="0.1">
    </div>
  </div>
  <div class="calc-out">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--dim);margin-bottom:6px">Probabilistic Sharpe Ratio</div>
    <div class="big" id="psr-value">&mdash;</div>
    <div id="psr-verdict" style="font-size:13.5px;line-height:1.7;color:var(--text);margin-top:8px"></div>
    <div id="psr-detail" style="font-size:12px;line-height:1.7;color:var(--dim);margin-top:8px;font-family:'JetBrains Mono',monospace"></div>
  </div>
  <p class="qm-note"><strong>Frequency consistency matters.</strong> SR&#770;,
  SR* and n must describe the same sampling frequency. If you enter an
  annualised Sharpe, n is still the number of observations (24 monthly returns
  = 24, not 2). Mixing them is the most common error with this formula.</p>

  <h2>Formula</h2>
  <div class="qm-formula">                  ( SR_hat - SR* ) * sqrt( n - 1 )
PSR(SR*) = Z [ ---------------------------------------------------- ]
                sqrt( 1 - g1*SR_hat + ((g2 - 1)/4)*SR_hat^2 )

  Z   standard normal CDF      g1  skewness
  n   number of observations   g2  kurtosis (normal = 3)</div>
  <p>Negative skew makes <code>-g1*SR_hat</code> positive, enlarging the
  denominator and lowering PSR. Excess kurtosis does the same. Both encode the
  fact that fat-tailed, negatively skewed returns make a Sharpe estimate less
  trustworthy &mdash; which is precisely the profile of strategies that look
  best on headline numbers.</p>

  <h2>Example calculation</h2>
  <p>The values the calculator loads by default, so you can verify it against
  an independent implementation before trusting it on your own numbers:</p>
  <table class="qm-kv">
    <thead><tr><th>Input</th><th>Value</th></tr></thead>
    <tbody>
      <tr><th>Observed Sharpe SR&#770;</th><td class="qm-num">1.50</td></tr>
      <tr><th>Benchmark SR*</th><td class="qm-num">0.00</td></tr>
      <tr><th>Observations n</th><td class="qm-num">24</td></tr>
      <tr><th>Skewness &gamma;&#8321;</th><td class="qm-num">&minus;1.20</td></tr>
      <tr><th>Kurtosis &gamma;&#8322;</th><td class="qm-num">7.00</td></tr>
    </tbody>
  </table>
  <div class="qm-formula">den = sqrt( 1 - (-1.20)(1.50) + ((7.00 - 1)/4)(1.50)^2 )
    = sqrt( 1 + 1.80 + 1.5 * 2.25 )
    = sqrt( 6.175 )
    = 2.4850

z   = (1.50 - 0.00) * sqrt(24 - 1) / 2.4850
    = 1.50 * 4.7958 / 2.4850
    = 2.8949

PSR = Z(2.8949) = 0.9981  ->  99.81%</div>
  <p>Change the benchmark to 1.00 and the same track record gives z = 0.965 and
  PSR = 0.8327, which fails the 0.95 bar. Same strategy, different question.</p>

  <h2>Assumptions</h2>
  <ul>
    <li>Returns are independent and identically distributed. Serial correlation
    &mdash; common in illiquid or smoothed portfolios &mdash; inflates the
    apparent Sharpe and is not corrected here.</li>
    <li>Skewness and kurtosis are known. In practice they are estimated from the
    same short sample, so they carry their own error.</li>
    <li>The test evaluates <em>one</em> track record. If it is the best of many
    strategies you tested, use the Deflated Sharpe Ratio instead, which adjusts
    for the number of trials.</li>
    <li>Nothing here accounts for costs, capacity or backtest overfitting.</li>
  </ul>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/learn/what-is-probabilistic-sharpe-ratio.html">What is the Probabilistic Sharpe Ratio?</a><span>Worked explanation with examples</span></li>
    <li><a href="/learn/deflated-sharpe-ratio.html">What is the Deflated Sharpe Ratio?</a><span>The correction to use when the strategy is the best of many you tested</span></li>
    <li><a href="/paper-probabilistic-sharpe-ratio.html">Probabilistic Sharpe Ratio</a><span>The full QuantMedia research paper</span></li>
    <li><a href="/learn/how-to-model-slippage-in-backtests.html">How to model slippage in backtests</a><span>The cost side of an apparent edge</span></li>
  </ul>

<script>
(function(){
  var ids=['psr-sr','psr-bm','psr-n','psr-skew','psr-kurt'];
  // Abramowitz & Stegun 7.1.26 error-function approximation; |error| < 1.5e-7.
  function erf(x){
    var s=x<0?-1:1; x=Math.abs(x);
    var a1=0.254829592,a2=-0.284496736,a3=1.421413741,a4=-1.453152027,a5=1.061405429,p=0.3275911;
    var t=1/(1+p*x);
    var y=1-(((((a5*t+a4)*t)+a3)*t+a2)*t+a1)*t*Math.exp(-x*x);
    return s*y;
  }
  var ncdf=function(z){return 0.5*(1+erf(z/Math.SQRT2));};

  function calc(){
    var sr=parseFloat(document.getElementById('psr-sr').value);
    var bm=parseFloat(document.getElementById('psr-bm').value);
    var n=parseFloat(document.getElementById('psr-n').value);
    var g1=parseFloat(document.getElementById('psr-skew').value);
    var g2=parseFloat(document.getElementById('psr-kurt').value);
    var out=document.getElementById('psr-value');
    var verdict=document.getElementById('psr-verdict');
    var detail=document.getElementById('psr-detail');

    if([sr,bm,n,g1,g2].some(function(v){return !Number.isFinite(v);})||n<2||!Number.isInteger(n)){
      out.textContent='—';
      verdict.textContent='Enter all five inputs. Use finite numbers and a whole-number observation count of at least 2.';
      detail.textContent='';
      return;
    }
    var denomSq=1-g1*sr+((g2-1)/4)*sr*sr;
    if(!Number.isFinite(denomSq)||denomSq<=0){
      out.textContent='—';
      verdict.textContent='These inputs do not give a finite, positive variance term. Check the Sharpe, skewness and kurtosis inputs.';
      detail.textContent='1 - g1*SR + ((g2-1)/4)*SR^2 = '+denomSq.toFixed(4);
      return;
    }
    var z=((sr-bm)*Math.sqrt(n-1))/Math.sqrt(denomSq);
    var psr=ncdf(z);
    out.textContent=(psr*100).toFixed(2)+'%';
    detail.textContent='denominator = '+Math.sqrt(denomSq).toFixed(4)+'   z = '+z.toFixed(3);
    if(psr>=0.95){
      verdict.innerHTML='<strong style="color:var(--accent)">Clears the 95% bar.</strong> The record supports a true Sharpe above '+bm+' at conventional confidence.';
    }else if(psr>=0.90){
      verdict.innerHTML='<strong style="color:var(--gold)">Short of 95%.</strong> Suggestive but not conclusive at the usual threshold — the result remains below the chosen confidence threshold.';
    }else{
      verdict.innerHTML='<strong style="color:var(--red)">Does not support the claim.</strong> Given this track length and return shape, the evidence for a true Sharpe above '+bm+' is weak.';
    }
  }
  ids.forEach(function(id){
    var el=document.getElementById(id);
    if(el){el.addEventListener('input',calc);}
  });
  calc();
})();
</script>
"""


# ===========================================================================
# /reproducibility.html — index of implementations and tools
# ===========================================================================
REPRO_BODY = """
  <p class="qm-lede">Every QuantMedia research claim that can reasonably be
  reproduced should be. This page indexes the implementations, example data and
  tools that back the research &mdash; and is equally explicit about which
  papers are currently <em>research only</em>, with no runnable material behind
  them.</p>

  <div class="qm-answer">
    <span class="qm-answer-label">Status definitions</span>
    <p><strong>Reproducible</strong> &mdash; runnable code, example data,
    expected output and tests exist, and the implementation follows the
    methodology in the paper. <strong>Interactive tool</strong> &mdash; a
    working calculator with a published formula. <strong>Research only</strong>
    &mdash; the paper stands on its own; no code has been released yet. Nothing
    is labelled reproducible on the strength of an intention.</p>
  </div>

  <div class="qm-answer"><span class="qm-answer-label">Start here</span>
    <p><a href="/tools/probabilistic-sharpe-ratio-calculator.html">Use the free PSR calculator</a>,
    <a href="/reports/">read the worked examples</a>, or
    <a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research">get the Python code on GitHub</a>.
    All tools and examples are freely accessible.</p></div>
  <h2>Available implementations</h2>

  <h3>VPIN &mdash; order flow toxicity</h3>
  <table class="qm-kv"><tbody>
    <tr><th>Research question</th><td>Can order-flow toxicity be estimated from a trade tape without quote data, and how sensitive is the answer to the classification method?</td></tr>
    <tr><th>Paper</th><td><a href="/paper-vpin-order-flow-toxicity.html">VPIN &amp; Order Flow Toxicity</a></td></tr>
    <tr><th>Explainer</th><td><a href="/learn/what-is-vpin.html">What is VPIN?</a></td></tr>
    <tr><th>Code</th><td><a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research/vpin-order-flow-toxicity">GitHub: vpin-order-flow-toxicity</a> &mdash; <code>vpin.py</code>, <code>example.py</code></td></tr>
    <tr><th>Implements</th><td>Equal-volume bucketing with boundary splitting; Bulk Volume Classification (Student-t) and the tick rule; rolling VPIN</td></tr>
    <tr><th>Example data</th><td>Synthetic tape, fixed seed <code>20260808</code>, with a planted one-sided episode</td></tr>
    <tr><th>Expected output</th><td>VPIN rises ~1.94x through the planted episode; BVC and tick-rule means differ (0.44 vs 0.18) on identical data</td></tr>
    <tr><th>Tests</th><td>15, covering bucket construction, volume conservation, both classifiers, bounds, degenerate tapes and validation</td></tr>
    <tr><th>Status</th><td><strong>Reproducible</strong></td></tr>
  </tbody></table>

  <h3>Hierarchical Risk Parity</h3>
  <table class="qm-kv"><tbody>
    <tr><th>Research question</th><td>Does avoiding covariance-matrix inversion produce more stable out-of-sample allocations than mean-variance on correlated universes?</td></tr>
    <tr><th>Paper</th><td><a href="/paper-hierarchical-risk-parity.html">Hierarchical Risk Parity</a></td></tr>
    <tr><th>Explainer</th><td><a href="/learn/hrp-vs-mean-variance.html">HRP vs mean-variance</a></td></tr>
    <tr><th>Code</th><td><a href="https://github.com/certurk23/certurk23.github.io/tree/main/quantmedia-research/hierarchical-risk-parity">GitHub: hierarchical-risk-parity</a> &mdash; <code>hrp.py</code>, <code>compare_mvo.py</code></td></tr>
    <tr><th>Implements</th><td>Correlation distance, hierarchical linkage, quasi-diagonalisation, recursive bisection; min-variance and shrinkage baselines</td></tr>
    <tr><th>Example data</th><td>Synthetic 20-asset block-correlated panel, fixed seed <code>20260808</code></td></tr>
    <tr><th>Expected output</th><td>Out-of-sample volatility drift: HRP +1.3% vs MinVar +13.6%; shrinkage narrows it to +7.7%</td></tr>
    <tr><th>Tests</th><td>13, including weights summing to 1, no negatives, a known 80/20 two-asset result and distance-metric properties</td></tr>
    <tr><th>Status</th><td><strong>Reproducible</strong></td></tr>
  </tbody></table>

  <h3>Probabilistic Sharpe Ratio</h3>
  <table class="qm-kv"><tbody>
    <tr><th>Research question</th><td>Given a track record's length and return shape, how confident can you be that the true Sharpe beats a benchmark?</td></tr>
    <tr><th>Paper</th><td><a href="/paper-probabilistic-sharpe-ratio.html">Probabilistic Sharpe Ratio</a></td></tr>
    <tr><th>Explainer</th><td><a href="/learn/what-is-probabilistic-sharpe-ratio.html">What is the Probabilistic Sharpe Ratio?</a></td></tr>
    <tr><th>Tool</th><td><a href="/tools/probabilistic-sharpe-ratio-calculator.html">PSR calculator</a> &mdash; runs in the browser, no data leaves the page</td></tr>
    <tr><th>Verification</th><td>Worked example published with every intermediate value, so the tool can be checked against an independent implementation</td></tr>
    <tr><th>Status</th><td><strong>Interactive tool</strong></td></tr>
  </tbody></table>

  <h2>Research only</h2>
  <p>These papers have no released implementation. They are listed so the
  absence is explicit rather than inferred:</p>
  <ul class="qm-related">
    <li><a href="/paper-slippage-latency-modeling.html">Slippage &amp; Latency Modeling</a><span>Formulas and a worked example appear in <a href="/learn/how-to-model-slippage-in-backtests.html">the explainer</a>; no package yet</span></li>
    <li><a href="/paper-bid-ask-spread-dynamics.html">Bid-Ask Spread Dynamics</a><span>Research only</span></li>
    <li><a href="/paper-genetic-algorithm-alpha.html">Genetic Algorithm Alpha</a><span>Research only</span></li>
    <li><a href="/paper-alternative-data-quant-finance.html">Alternative Data in Quantitative Finance</a><span>Research only</span></li>
    <li><a href="/papers.html">Full research library</a><span>All 11 open-access papers</span></li>
  </ul>

  <h2>Running the code</h2>
  <div class="qm-formula">git clone https://github.com/certurk23/certurk23.github.io.git
cd certurk23.github.io
python -m venv .venv
# Activate: source .venv/bin/activate (macOS/Linux)
# PowerShell: .venv\\Scripts\\Activate.ps1

cd quantmedia-research/vpin-order-flow-toxicity
pip install -r requirements.txt
python example.py

cd ../hierarchical-risk-parity
pip install -r requirements.txt
python compare_mvo.py

cd ..
python tests/test_vpin.py     # 15 tests
python tests/test_hrp.py      # 13 tests</div>
  <p>Python 3.9 or later. Dependencies are numpy, pandas and scipy. No API key,
  no paid data subscription is required. Downloading the code and installing dependencies needs internet access; the examples then run offline.</p>

  <div class="qm-answer">
    <span class="qm-answer-label">On the sample data</span>
    <p>Both packages ship <strong>synthetic</strong> example data generated from
    fixed seeds. It is not real market data and no conclusion about any real
    security follows from it. It exists so the implementations can be run and
    verified end-to-end without a tick-data subscription. Each package states
    this in its README, its module docstring and its console output.</p>
  </div>

  <h2>Daily market metrics and data</h2>
  <p>Separately from the research code, QuantMedia publishes two metrics
  computed from its own daily scan, with machine-readable history:</p>
  <ul class="qm-related">
    <li><a href="/indices/signal-breadth.html">QuantMedia Signal Breadth</a><span>Share of scored equities clearing the BUY threshold &middot; <a href="/data/signal_breadth.json">JSON</a> &middot; <a href="/data/breadth_history.json">history</a></span></li>
    <li><a href="/indices/sector-confluence.html">QuantMedia Sector Confluence</a><span>Mean score and breadth per sector &middot; <a href="/data/sector_confluence.json">JSON</a> &middot; <a href="/data/sector_confluence_history.json">history</a></span></li>
    <li><a href="/data/signal_config.json">Signal engine configuration</a><span>Canonical methodology parameters, version <strong>2.0</strong></span></li>
  </ul>

  <h2>Not implemented, and why</h2>
  <p>Three things that would fit this site are deliberately absent:</p>
  <ul>
    <li><strong>Live VPIN / order-flow toxicity index.</strong> Requires tick or
    quote data. The production pipeline collects end-of-day OHLCV only. The VPIN
    code above is fully runnable, but there is no honest way to compute a live
    reading from daily bars, so none is published.</li>
    <li><strong>Slippage stress index.</strong> Same reason &mdash; it needs
    spread and depth data the pipeline does not collect.</li>
    <li><strong>Market regime score.</strong> Not implemented: insufficient
    validated inputs. A composite of breadth and score dispersion would restate
    numbers already on the Signal Breadth page while adding a label that implies
    validation nobody has done.</li>
  </ul>

  <h2>Methodology versioning</h2>
  <p>The signal engine carries a version number, currently <strong>2.0</strong>
  (effective 2026-04-14), stamped into every scan output and history record.
  When production logic changes the version increments; historical records keep
  the version that produced them and are never retroactively rewritten. Papers
  describing earlier methodology are preserved as published rather than edited
  to match current production.</p>
"""


# ===========================================================================
# /learn/deflated-sharpe-ratio.html
# ===========================================================================
DSR_BODY = """
  <div class="qm-answer">
    <span class="qm-answer-label">Short answer</span>
    <p>The Deflated Sharpe Ratio (DSR) is the Probabilistic Sharpe Ratio with
    the benchmark raised to the Sharpe you would <em>expect to see by luck
    alone</em> after testing many strategies. If you try enough variations, the
    best one will look good whether or not it has any edge. DSR asks whether
    your winner beats that luck threshold. A strategy with PSR near 1.00
    against a zero benchmark can fall below 0.30 once 1,000 trials are
    accounted for.</p>
  </div>

  <h2>What problem does it solve?</h2>
  <p>The <a href="/learn/what-is-probabilistic-sharpe-ratio.html">Probabilistic
  Sharpe Ratio</a> corrects for track-record length and return shape, but it
  evaluates <strong>one</strong> track record in isolation. That is the wrong
  question if the strategy in front of you is the survivor of a search.</p>
  <p>Suppose you test 1,000 parameter combinations on the same data. Even if
  none has genuine edge, the sample Sharpe ratios will scatter around zero, and
  the best of the 1,000 will be well above zero purely from sampling variation.
  Reporting that winner as though it were the only thing you tried is selection
  bias, and it is the single most common way backtests mislead.</p>
  <p>Statisticians call this the <strong>multiple testing</strong> problem, and
  it is the same issue that produces false positives in clinical trials and
  particle physics. Finance arrived at it late and still under-corrects for it.</p>
  <p>Bailey and L&oacute;pez de Prado's fix is direct: instead of testing
  against zero, test against the Sharpe you would <em>expect</em> the best of
  N trials to produce under the null hypothesis of no skill.</p>

  <h2>Formula</h2>
  <p>DSR is PSR evaluated at a deflated benchmark:</p>
  <div class="qm-formula">DSR = PSR(SR*_0)

where the expected maximum Sharpe across N independent trials is

                   [                                           1        ]
SR*_0 = sd(SR) * [ (1 - g) * Z^-1( 1 - 1/N )  +  g * Z^-1( 1 - --- ) ]
                   [                                          N*e       ]

  sd(SR)  standard deviation of Sharpe ratios ACROSS the trials
  N       number of independent trials actually performed
  g       Euler-Mascheroni constant, 0.5772...
  Z^-1    inverse standard normal CDF
  e       Euler's number</div>
  <p>Two inputs deserve attention because they are where the method is easiest
  to abuse. <code>N</code> is the number of trials you <em>really</em> ran,
  including the ones you abandoned early and the ones you would rather forget;
  understating it inflates DSR. <code>sd(SR)</code> is the dispersion of Sharpe
  ratios across those trials, which requires you to have kept them.</p>

  <h2>Worked example</h2>
  <p>A strategy with an observed Sharpe of 1.50 over 120 monthly observations,
  skewness &minus;0.8 and kurtosis 6.0. Sharpe ratios across the trials had a
  standard deviation of 0.50. The denominator term is the same as for PSR:</p>
  <div class="qm-formula">den = sqrt( 1 - (-0.80)(1.50) + ((6.0 - 1)/4)(1.50)^2 )
    = sqrt( 1 + 1.20 + 1.25 * 2.25 )
    = sqrt( 5.0125 )
    = 2.2389</div>
  <p>Now watch what the trial count does to the same strategy:</p>
  <table class="qm-kv">
    <thead><tr><th>Trials (N)</th><th>Expected max Sharpe SR*&#8320;</th><th>DSR</th><th>Verdict at 0.95</th></tr></thead>
    <tbody>
      <tr><td class="qm-num">1</td><td class="qm-num">&mdash;</td><td class="qm-num">1.0000</td><td>Passes (no selection to correct)</td></tr>
      <tr><td class="qm-num">10</td><td class="qm-num">0.7873</td><td class="qm-num">0.9997</td><td>Passes</td></tr>
      <tr><td class="qm-num">100</td><td class="qm-num">1.2653</td><td class="qm-num">0.8736</td><td><strong>Fails</strong></td></tr>
      <tr><td class="qm-num">1000</td><td class="qm-num">1.6276</td><td class="qm-num">0.2671</td><td><strong>Fails badly</strong></td></tr>
    </tbody>
  </table>
  <p>Nothing about the strategy changed between those rows. Only the honesty of
  the accounting did. Against a zero benchmark this track record gives a PSR of
  essentially 1.0000 &mdash; which is why a naive PSR on a mined strategy is
  close to meaningless.</p>
  <p>The N = 1 row is a genuine degenerate case: with a single trial there is no
  selection bias, the expected maximum is undefined, and DSR collapses back to
  ordinary PSR. That is correct behaviour, not a gap.</p>

  <h2>PSR vs DSR: which do I need?</h2>
  <table class="qm-kv">
    <thead><tr><th></th><th>PSR</th><th>DSR</th></tr></thead>
    <tbody>
      <tr><th>Question answered</th><td>Is this Sharpe distinguishable from the benchmark?</td><td>Is this Sharpe distinguishable from the best of N lucky tries?</td></tr>
      <tr><th>Benchmark</th><td>Chosen by you (often 0)</td><td>Expected maximum under the null</td></tr>
      <tr><th>Corrects for track length</th><td>Yes</td><td>Yes</td></tr>
      <tr><th>Corrects for skew/kurtosis</th><td>Yes</td><td>Yes</td></tr>
      <tr><th>Corrects for selection bias</th><td><strong>No</strong></td><td><strong>Yes</strong></td></tr>
      <tr><th>Needs a trial count</th><td>No</td><td>Yes &mdash; and an honest one</td></tr>
      <tr><th>Use when</th><td>You have one strategy, designed in advance</td><td>You searched, optimised or selected</td></tr>
    </tbody>
  </table>
  <p>The practical rule: if you can honestly say you tested exactly one
  specification and are reporting it whatever the result, PSR is enough.
  The moment you swept a parameter, PSR overstates your evidence.</p>

  <h2>Limitations</h2>
  <ul>
    <li><strong>N is self-reported and unverifiable.</strong> The correction is
    only as honest as the trial count you feed it. There is no way for a reader
    to audit it, which is why the number should be disclosed alongside the
    result rather than folded silently into a score.</li>
    <li><strong>Trials are assumed independent.</strong> Sweeping one parameter
    produces highly correlated strategies, so the <em>effective</em> number of
    independent trials is smaller than the raw count. Using the raw count is
    conservative; treating correlated variants as independent overstates the
    penalty.</li>
    <li><strong>It inherits every PSR assumption.</strong> IID returns, known
    higher moments, and no account of costs, capacity or regime change.</li>
    <li><strong>It does not rescue a bad process.</strong> DSR quantifies the
    damage from searching; it does not undo it. The stronger discipline is to
    pre-register the specification.</li>
  </ul>

  <h2>References</h2>
  <ul class="qm-refs">
    <li>Bailey, D. &amp; L&oacute;pez de Prado, M. (2014). &ldquo;The Deflated
    Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and
    Non-Normality.&rdquo; <em>Journal of Portfolio Management</em> 40(5),
    94&ndash;107.</li>
    <li>Bailey, D. &amp; L&oacute;pez de Prado, M. (2012). &ldquo;The Sharpe
    Ratio Efficient Frontier.&rdquo; <em>Journal of Risk</em> 15(2), 3&ndash;44.</li>
    <li>Bailey, D., Borwein, J., L&oacute;pez de Prado, M. &amp; Zhu, Q. (2014).
    &ldquo;Pseudo-Mathematics and Financial Charlatanism: The Effects of
    Backtest Overfitting on Out-of-Sample Performance.&rdquo;
    <em>Notices of the AMS</em> 61(5), 458&ndash;471.</li>
    <li>Harvey, C. &amp; Liu, Y. (2015). &ldquo;Backtesting.&rdquo;
    <em>Journal of Portfolio Management</em> 42(1), 13&ndash;28.</li>
  </ul>

  <h2>Related</h2>
  <ul class="qm-related">
    <li><a href="/learn/what-is-probabilistic-sharpe-ratio.html">What is the Probabilistic Sharpe Ratio?</a><span>The measure DSR extends</span></li>
    <li><a href="/tools/probabilistic-sharpe-ratio-calculator.html">PSR calculator</a><span>Enter SR*&#8320; as the benchmark to compute DSR directly</span></li>
    <li><a href="/learn/deflated-sharpe-ratio.html">What is the Deflated Sharpe Ratio?</a><span>The correction to use when the strategy is the best of many you tested</span></li>
    <li><a href="/paper-probabilistic-sharpe-ratio.html">Probabilistic Sharpe Ratio</a><span>The full QuantMedia research paper</span></li>
    <li><a href="/learn/how-to-model-slippage-in-backtests.html">How to model slippage in backtests</a><span>The other way backtests overstate results</span></li>
  </ul>
"""
