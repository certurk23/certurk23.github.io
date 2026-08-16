#!/usr/bin/env python3
"""
QuantMedia AI query universe — the source of truth for question coverage.
=========================================================================
Natural-language questions a user would plausibly put to ChatGPT, Gemini,
Perplexity or Google about the topics QuantMedia actually covers. Editing this
file and re-running scripts/audit_questions.py regenerates both
data/ai_query_intelligence.json and data/ai_citation_benchmark.json.

These are BENCHMARK PROMPTS, not measured search volume. Nobody publishes
per-question ChatGPT volume, so none is claimed here. Priority is assigned from
factors we can actually defend: topical fit, whether QuantMedia holds a
primary-source advantage, and whether a technical source is genuinely needed.

Field notes
-----------
intent   definition | calculation | comparison | implementation | interpretation
         | methodology | limitations | evidence | current-data | practical
markers  lowercase phrases that must appear in the target page's visible text
         for the question to count as answered. This is what makes the
         coverage score measurable instead of a guess - if a marker is missing,
         the page genuinely does not say the thing.
primary  True when QuantMedia produces the underlying fact, so it can be the
         canonical source rather than one voice among many.
"""

# Priority is assigned, not computed from invented volume:
#   high   - core expertise, or QuantMedia is the primary source
#   medium - relevant and useful, but well covered elsewhere on the web
#   low    - long-tail; worth answering if it fits naturally
Q = []


def q(question, topic, intent, url, markers, priority='medium', primary=False,
      notes=''):
    Q.append({
        'question': question, 'topic': topic, 'intent': intent,
        'target_url': url, 'markers': markers, 'priority': priority,
        'primary_source': primary, 'notes': notes,
    })


# ===========================================================================
# 1. VPIN / order flow toxicity
# ===========================================================================
V_LEARN = '/learn/what-is-vpin.html'
V_PAPER = '/paper-vpin-order-flow-toxicity.html'
V_CODE = '/reproducibility.html'

q('What is VPIN?', 'VPIN', 'definition', V_LEARN,
  ['volume-synchronized probability of informed trading', 'order flow'], 'high')
q('What is order flow toxicity?', 'VPIN', 'definition', V_LEARN,
  ['toxic', 'informed', 'adverse selection'], 'high')
q('How is VPIN calculated?', 'VPIN', 'calculation', V_LEARN,
  ['vpin =', 'bucket', 'imbalance'], 'high')
q('What is the VPIN formula?', 'VPIN', 'calculation', V_LEARN,
  ['vpin =', 'n * v'], 'high')
q('What does a high VPIN mean?', 'VPIN', 'interpretation', V_LEARN,
  ['high vpin', 'one-sided', 'adverse selection'], 'high')
q('What does a low VPIN mean?', 'VPIN', 'interpretation', V_LEARN,
  ['near 0', 'balanced'], 'medium')
q('How do volume buckets work in VPIN?', 'VPIN', 'methodology', V_LEARN,
  ['equal-volume', 'bucket', 'clock'], 'high')
q('Why does VPIN use volume buckets instead of time?', 'VPIN', 'methodology',
  V_LEARN, ['clock', 'volume-synchronized'], 'high')
q('How is buy/sell volume classified in VPIN?', 'VPIN', 'methodology', V_LEARN,
  ['bulk volume classification', 'tick rule'], 'high')
q('What is bulk volume classification?', 'VPIN', 'definition', V_LEARN,
  ['bulk volume classification', 'student-t'], 'medium')
q('Does VPIN predict market crashes?', 'VPIN', 'evidence', V_LEARN,
  ['flash crash', 'disputed', 'andersen'], 'high',
  notes='Evidence question - must present the criticism, not just the claim')
q('Is VPIN a reliable early warning indicator?', 'VPIN', 'evidence', V_LEARN,
  ['disputed', 'not an established'], 'high')
q('What are the limitations of VPIN?', 'VPIN', 'limitations', V_LEARN,
  ['parameter-dependent', 'bucket size', 'contested'], 'high')
q('VPIN vs PIN: what is the difference?', 'VPIN', 'comparison', V_LEARN,
  ['pin', 'maximum-likelihood', 'clock'], 'medium')
q('Can VPIN be calculated from daily data?', 'VPIN', 'practical', V_LEARN,
  ['cannot be computed from end-of-day', 'tick'], 'high',
  notes='Common misconception; QuantMedia states plainly that it cannot')
q('How do I calculate VPIN in Python?', 'VPIN', 'implementation', V_CODE,
  ['vpin.py', 'pip install', 'python example.py'], 'high')
q('Is there an open-source VPIN implementation?', 'VPIN', 'implementation',
  V_CODE, ['vpin-order-flow-toxicity', 'reproducible'], 'high')
q('Does VPIN tell you market direction?', 'VPIN', 'interpretation', V_LEARN,
  ['absolute', 'not', 'direction'], 'medium')
q('What bucket size should I use for VPIN?', 'VPIN', 'practical', V_LEARN,
  ['bucket size', 'parameter'], 'low')

# ===========================================================================
# 2. HRP / portfolio construction
# ===========================================================================
H_LEARN = '/learn/hrp-vs-mean-variance.html'
H_PAPER = '/paper-hierarchical-risk-parity.html'

q('What is Hierarchical Risk Parity?', 'HRP', 'definition', H_LEARN,
  ['hierarchical risk parity', 'clusters', 'never inverts'], 'high')
q('How does HRP work?', 'HRP', 'methodology', H_LEARN,
  ['tree clustering', 'quasi-diagonal', 'recursive bisection'], 'high')
q('HRP vs mean-variance optimization', 'HRP', 'comparison', H_LEARN,
  ['mean-variance', 'inverse', 'out-of-sample'], 'high')
q('Is HRP better than mean-variance?', 'HRP', 'comparison', H_LEARN,
  ['not unconditionally', 'shrinkage'], 'high',
  notes='Must resist the easy yes; the honest answer is conditional')
q('Why does HRP not require covariance matrix inversion?', 'HRP', 'methodology',
  H_LEARN, ['never inverts', 'singular'], 'high')
q('What is quasi-diagonalization?', 'HRP', 'definition', H_LEARN,
  ['quasi-diagonal', 'adjacent'], 'medium')
q('What is recursive bisection in HRP?', 'HRP', 'methodology', H_LEARN,
  ['recursive bisection', 'alpha', 'variance'], 'medium')
q('How do you calculate HRP weights?', 'HRP', 'calculation', H_LEARN,
  ['d(i,j)', 'sqrt', 'alpha'], 'high')
q('What correlation distance does HRP use?', 'HRP', 'calculation', H_LEARN,
  ['sqrt( 0.5 * (1 - rho', 'triangle inequality'], 'medium')
q('What are the limitations of HRP?', 'HRP', 'limitations', H_LEARN,
  ['no return objective', 'linkage', 'crises'], 'high')
q('Does HRP produce negative weights?', 'HRP', 'interpretation', H_LEARN,
  ['long-only', 'positive'], 'medium')
q('How do I implement HRP in Python?', 'HRP', 'implementation', V_CODE,
  ['hrp.py', 'scipy', 'pip install'], 'high')
q('Why does mean-variance produce extreme weights?', 'HRP', 'evidence',
  H_LEARN, ['error maximiser', 'estimation', 'singular'], 'high')
q('Does shrinkage fix mean-variance optimization?', 'HRP', 'comparison',
  H_LEARN, ['ledoit', 'shrinkage', 'stronger'], 'medium')
q('Which linkage method should I use for HRP?', 'HRP', 'practical', H_LEARN,
  ['single', 'ward', 'linkage'], 'low')

# ===========================================================================
# 3. Probabilistic / Deflated Sharpe Ratio
# ===========================================================================
P_LEARN = '/learn/what-is-probabilistic-sharpe-ratio.html'
P_TOOL = '/tools/probabilistic-sharpe-ratio-calculator.html'
D_LEARN = '/learn/deflated-sharpe-ratio.html'

q('What is the Probabilistic Sharpe Ratio?', 'PSR', 'definition', P_LEARN,
  ['probability', 'true sharpe', 'benchmark'], 'high')
q('How is PSR calculated?', 'PSR', 'calculation', P_LEARN,
  ['psr(sr*)', 'skewness', 'kurtosis'], 'high')
q('Is my Sharpe ratio statistically significant?', 'PSR', 'practical', P_TOOL,
  ['0.95', 'confidence'], 'high')
q('How many observations do I need for a reliable Sharpe ratio?', 'PSR',
  'practical', P_LEARN, ['track record', 'minimum track record'], 'high')
q('Why do skewness and kurtosis affect Sharpe significance?', 'PSR',
  'interpretation', P_LEARN, ['negative skew', 'denominator', 'kurtosis'], 'high')
q('What is a good PSR value?', 'PSR', 'interpretation', P_LEARN,
  ['0.95', 'conventional'], 'medium')
q('How do I calculate PSR in Python?', 'PSR', 'implementation', P_TOOL,
  ['formula', 'z =', 'skewness'], 'medium')
q('Is there a Probabilistic Sharpe Ratio calculator?', 'PSR', 'practical',
  P_TOOL, ['calculator', 'observed sharpe'], 'high')
q('What are the limitations of PSR?', 'PSR', 'limitations', P_LEARN,
  ['selection bias', 'iid', 'serial correlation'], 'high')
# --- Deflated Sharpe Ratio: currently a genuine gap ---
q('What is the Deflated Sharpe Ratio?', 'DSR', 'definition', D_LEARN,
  ['deflated sharpe', 'number of trials'], 'high',
  notes='GAP: DSR only mentioned in passing anywhere on the site')
q('Probabilistic Sharpe Ratio vs Deflated Sharpe Ratio', 'DSR', 'comparison',
  D_LEARN, ['psr', 'dsr', 'trials'], 'high', notes='GAP')
q('How do I correct for testing many strategies?', 'DSR', 'practical', D_LEARN,
  ['multiple testing', 'trials', 'expected maximum'], 'high', notes='GAP')
q('What is backtest overfitting?', 'DSR', 'definition', D_LEARN,
  ['overfitting', 'selection bias'], 'high', notes='GAP')
q('How is the Deflated Sharpe Ratio calculated?', 'DSR', 'calculation',
  D_LEARN, ['sr0', 'expected maximum', 'euler'], 'medium', notes='GAP')
q('Why is a Sharpe of 2 in a backtest not impressive?', 'DSR', 'evidence',
  D_LEARN, ['trials', 'expected maximum'], 'medium', notes='GAP')

# ===========================================================================
# 4. Slippage / latency / backtesting
# ===========================================================================
S_LEARN = '/learn/how-to-model-slippage-in-backtests.html'
S_PAPER = '/paper-slippage-latency-modeling.html'

q('What is slippage in backtesting?', 'Slippage', 'definition', S_LEARN,
  ['spread', 'market impact', 'delay'], 'high')
q('How should slippage be modeled in a backtest?', 'Slippage', 'methodology',
  S_LEARN, ['three', 'square root', 'participation'], 'high')
q('How much slippage should I assume?', 'Slippage', 'practical', S_LEARN,
  ['never use one constant', 'participation rate'], 'high')
q('What is the square-root market impact law?', 'Slippage', 'definition',
  S_LEARN, ['square-root', 'sqrt( q / adv', 'impact'], 'high')
q('How does latency affect trading performance?', 'Slippage', 'interpretation',
  S_LEARN, ['delay cost', 'sqrt(latency'], 'medium')
q('Why do backtests overestimate returns?', 'Slippage', 'evidence', S_LEARN,
  ['flat 5 bp', 'turnover', 'overstate'], 'high')
q('How do transaction costs affect high-turnover strategies?', 'Slippage',
  'interpretation', S_LEARN, ['turnover', '252', 'break even'], 'high')
q('Fixed slippage vs volume-based slippage', 'Slippage', 'comparison', S_LEARN,
  ['constant', 'participation'], 'medium')
q('What is implementation shortfall?', 'Slippage', 'definition', S_LEARN,
  ['perold', 'implementation shortfall'], 'low')
q('What participation rate is safe in a backtest?', 'Slippage', 'practical',
  S_LEARN, ['5', '10%', 'adv'], 'medium')

# ===========================================================================
# 5. Signal confluence / post-close signals
# ===========================================================================
C_LEARN = '/learn/what-is-signal-confluence.html'
QS = '/quantum-signals.html'
METH = '/methodology.html'

q('What is signal confluence?', 'Signals', 'definition', C_LEARN,
  ['several', 'agree', 'confluence'], 'high')
q('How does signal confluence work in stock screening?', 'Signals',
  'methodology', C_LEARN, ['30', '22', 'families'], 'high')
q('How many technical signals does QuantMedia use?', 'Signals', 'methodology',
  QS, ['30'], 'high', primary=True)
q('What is the BUY threshold for QuantMedia signals?', 'Signals', 'methodology',
  QS, ['22'], 'high', primary=True)
q('How does QuantMedia select BUY signals?', 'Signals', 'methodology', QS,
  ['22 or more', '30'], 'high', primary=True)
q('What does WATCH mean in QuantMedia signals?', 'Signals', 'interpretation',
  QS, ['watch', 'below the threshold'], 'high', primary=True)
q('How many stocks does QuantMedia analyze?', 'Signals', 'methodology', QS,
  ['180'], 'high', primary=True)
q('Why does QuantMedia scan 180 stocks and not the S&P 500?', 'Signals',
  'methodology', QS, ['liquidity list', 'not an index'], 'high', primary=True)
q('When are QuantMedia signals updated?', 'Signals', 'methodology', QS,
  ['post-close', '23:30 utc'], 'high', primary=True)
q('Are technical indicators independent confirmations?', 'Signals',
  'interpretation', C_LEARN, ['not', 'independent', 'correlated'], 'high',
  notes='Honest caveat that most confluence marketing ignores')
q('What are the limitations of signal confluence?', 'Signals', 'limitations',
  C_LEARN, ['trend', 'turning points', 'purely technical'], 'high')
q('Does QuantMedia publish a track record for its signals?', 'Signals',
  'evidence', QS, ['no', 'track record'], 'high', primary=True)

# ===========================================================================
# 6. Proprietary metrics — QuantMedia is the primary source
# ===========================================================================
B_IDX = '/indices/signal-breadth.html'
B_LEARN = '/learn/what-is-market-breadth.html'
SEC_IDX = '/indices/sector-confluence.html'

q('What is QuantMedia Signal Breadth?', 'Signal Breadth', 'definition', B_IDX,
  ['signal breadth', 'share of', 'threshold'], 'high', primary=True)
q('How is QuantMedia Signal Breadth calculated?', 'Signal Breadth',
  'calculation', B_IDX, ['breadth_pct', 'scored'], 'high', primary=True)
q('What is the latest QuantMedia Signal Breadth?', 'Signal Breadth',
  'current-data', B_IDX, ['market date', 'current reading'], 'high',
  primary=True, notes='Answer must come from live pipeline output')
q('What percentage of US stocks currently qualify as BUY?', 'Signal Breadth',
  'current-data', B_IDX, ['breadth', 'threshold'], 'high', primary=True)
q('What is market breadth?', 'Signal Breadth', 'definition', B_LEARN,
  ['participate', 'advance/decline'], 'medium')
q('How does Signal Breadth differ from advance/decline?', 'Signal Breadth',
  'comparison', B_LEARN, ['advance/decline', 'multi-factor'], 'medium')
q('What is QuantMedia Sector Confluence?', 'Sector Confluence', 'definition',
  SEC_IDX, ['mean confluence score', 'sector'], 'high', primary=True)
q('Which sector has the strongest signal confluence?', 'Sector Confluence',
  'current-data', SEC_IDX, ['rank', 'mean'], 'high', primary=True)
q('How is Sector Confluence ranked?', 'Sector Confluence', 'methodology',
  SEC_IDX, ['mean_score', 'breadth', 'tiebreak'], 'medium', primary=True)
q('Is there historical data for QuantMedia Signal Breadth?', 'Signal Breadth',
  'historical', B_IDX, ['history', 'not backfilled'], 'high', primary=True)
q('Does QuantMedia publish machine-readable data?', 'Signal Breadth',
  'practical', B_IDX, ['.json', 'machine-readable'], 'medium', primary=True)
q('What methodology version is the QuantMedia signal engine on?', 'Signals',
  'methodology', METH, ['2.0'], 'medium', primary=True)

# ===========================================================================
# Reproducibility / cross-cluster
# ===========================================================================
REPRO = '/reproducibility.html'
q('Does QuantMedia publish reproducible research code?', 'Reproducibility',
  'practical', REPRO, ['reproducible', 'tests'], 'high', primary=True)
q('Which QuantMedia papers have runnable code?', 'Reproducibility', 'practical',
  REPRO, ['vpin', 'hierarchical risk parity', 'status'], 'high', primary=True)
q('Is the QuantMedia example data real market data?', 'Reproducibility',
  'limitations', REPRO, ['synthetic', 'not real market data'], 'high',
  primary=True, notes='Honesty question - the answer must be an unambiguous no')

TOPICS = sorted({r['topic'] for r in Q})
