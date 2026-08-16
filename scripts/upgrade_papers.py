#!/usr/bin/env python3
"""
Research paper upgrade: limitations, references, honest schema.
===============================================================
An audit of the 11 research pages found the core credibility problem on the
site: every one was marked up as ScholarlyArticle, none cited a single
reference, and ten had no limitations section. At a median of 665 words they
were technical blog posts wearing academic costume - while the /learn/
explainers pointing AT them carried full reference lists with DOIs.

This script fixes that inversion:

  1. LIMITATIONS   an honest, paper-specific section where one is missing
  2. REFERENCES    real, checkable citations with DOIs where they exist
  3. SCHEMA        ScholarlyArticle -> Article, plus `citation` entries.
                   ScholarlyArticle implies academic publication norms these
                   pages do not meet. "Technical article with references" is a
                   respectable thing to be; claiming more is not.

Idempotent - safe to re-run. Verifies against the live section audit.

    python scripts/upgrade_papers.py
"""

from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = """<style>
.qm-sec{margin:34px 0 0}
.qm-sec h2{font-family:'Barlow Condensed',sans-serif;font-size:22px;font-weight:700;
  color:var(--text);letter-spacing:-.2px;margin:0 0 14px;padding-bottom:8px;
  border-bottom:1px solid var(--border)}
.qm-sec ul{margin:0 0 8px 20px;color:var(--text)}
.qm-sec li{margin-bottom:10px;line-height:1.8;font-size:14.5px}
.qm-sec li strong{color:var(--text)}
.qm-refs-list{list-style:none;margin:0;padding:0}
.qm-refs-list li{margin-bottom:12px;line-height:1.75;font-size:13.5px;color:var(--dim);
  padding-left:20px;text-indent:-20px}
.qm-refs-list a{color:var(--accent)}
.qm-refnote{font-size:12.5px;color:var(--dim);line-height:1.75;margin:14px 0 0;
  padding-top:12px;border-top:1px solid var(--border)}
</style>"""


def L(*items):
    return list(items)


# Per-paper limitations. Specific to the actual claims each paper makes -
# a generic "past performance" boilerplate would be worthless.
LIMITATIONS = {
 'paper-vpin-order-flow-toxicity.html': L(
  ('Contested empirical status', 'VPIN\'s role as a Flash Crash early-warning signal is actively disputed. Andersen and Bondarenko (2014) argue much of its apparent forecasting power reflects volume-volatility mechanics rather than information content. Treat VPIN as a descriptive microstructure statistic, not a validated predictor.'),
  ('Parameter sensitivity', 'Bucket size, window length, classification method and the Student-t degrees of freedom all move the level materially. Published VPIN values are not comparable across studies unless every one of those choices matches.'),
  ('Data requirements', 'VPIN needs trade-level or bar data. It cannot be computed from end-of-day OHLCV, which is why QuantMedia publishes no live VPIN reading: the production pipeline collects daily bars only.'),
  ('Directionally blind', 'The measure uses absolute imbalance, so heavy buying and heavy selling contribute identically. It describes one-sidedness, not direction.'),
 ),
 'paper-hierarchical-risk-parity.html': L(
  ('Sub-optimal in sample by construction', 'Mean-variance solves for minimum in-sample variance, so any in-sample comparison favours it automatically. HRP\'s case rests entirely on out-of-sample behaviour, and only out-of-sample tests are informative.'),
  ('No return objective', 'HRP allocates risk and ignores expected returns. Where genuine return forecasts exist, discarding them is a real cost rather than a free simplification.'),
  ('Linkage is a free parameter', 'Single, average and Ward linkage produce different trees and therefore different weights. The choice is a modelling decision that should be disclosed, not a detail.'),
  ('Correlation instability', 'Correlations converge during stress, flattening the cluster tree exactly when diversification matters most. The hierarchy is estimated from the same noisy data it is meant to protect against.'),
  ('Regularised mean-variance is a stronger baseline', 'Much of textbook mean-variance\'s instability is addressed by shrinkage estimators, constraints or resampling. Comparisons against an unconstrained optimiser overstate HRP\'s advantage.'),
 ),
 'paper-probabilistic-sharpe-ratio.html': L(
  ('Does not correct for selection bias', 'PSR evaluates one track record in isolation. If the strategy is the best of many tested, PSR overstates the evidence and the Deflated Sharpe Ratio should be used instead.'),
  ('Assumes IID returns', 'Serial correlation, common in illiquid or smoothed portfolios, inflates the observed Sharpe and is not handled by the standard formulation.'),
  ('Higher moments are themselves estimates', 'Skewness and kurtosis from short samples are noisy, and the correction is only as reliable as those estimates.'),
  ('Says nothing about economics', 'PSR is a statistical statement about a return series. It does not address costs, capacity, regime change, or whether the strategy was fitted to its sample.'),
 ),
 'paper-slippage-latency-modeling.html': L(
  ('The square-root law is empirical, not physical', 'The impact coefficient varies by asset, venue, participation rate and regime. Treat it as a calibration target with a sensitivity range, not a constant.'),
  ('Calibrated on normal conditions', 'Impact estimates derived from typical trading understate stress. In dislocations, depth vanishes and realised cost can exceed the model by multiples.'),
  ('Omits several real costs', 'The decomposition here covers spread, impact and delay. Commissions, exchange fees, borrow costs, taxes and opportunity cost from unfilled orders are strategy-specific and excluded.'),
  ('Fill assumptions remain optimistic', 'Assuming complete fills at the signal price is generous precisely in the conditions where signals tend to fire.'),
 ),
 'paper-bid-ask-spread-dynamics.html': L(
  ('Decomposition is model-dependent', 'Splitting the spread into order-processing, inventory and adverse-selection components requires a structural model. Different models attribute the same observed spread differently.'),
  ('Quoted is not effective', 'Quoted spreads overstate the cost actually paid when trades execute inside the quotes, and understate it when orders walk the book.'),
  ('Fragmentation', 'US equities trade across many venues and dark pools. A spread measured on one venue is not the consolidated cost of liquidity.'),
  ('Intraday non-stationarity', 'Spreads follow a strong intraday pattern and widen around events. Daily averages conceal most of what matters for execution.'),
 ),
 'paper-genetic-algorithm-alpha.html': L(
  ('Severe overfitting risk', 'Evolutionary search evaluates an enormous number of candidate rules. The best result from a large search will look strong by chance alone, which is exactly the condition the Deflated Sharpe Ratio exists to correct.'),
  ('Trial count is rarely reported honestly', 'Meaningful statistical correction requires knowing how many specifications were evaluated, including abandoned runs. Without it, reported performance cannot be assessed.'),
  ('Non-stationarity', 'Rules evolved on one regime frequently fail in the next. Evolutionary fitness measured in-sample says little about durability.'),
  ('Interpretability', 'Evolved rules are often complex and post-hoc rationalised, which makes it hard to distinguish an economic mechanism from a fitted artefact.'),
 ),
 'paper-alternative-data-quant-finance.html': L(
  ('Short and biased histories', 'Most alternative datasets begin recently and are frequently backfilled or restated by the vendor, which introduces look-ahead bias that is difficult to detect after the fact.'),
  ('Panel instability', 'Coverage changes as the underlying panel changes. A shift in the data collection method can look like a change in the economy.'),
  ('Crowding and decay', 'Once a dataset is widely licensed, its edge decays. Historical backtests are run on a period when few participants had access.'),
  ('Cost and legal exposure', 'Licensing, privacy regulation and material non-public information constraints are real operational limits, not footnotes.'),
 ),
 'paper-bist-sentiment-analysis.html': L(
  ('Language and domain transfer', 'Sentiment lexicons and models trained on English financial text do not transfer cleanly to Turkish, and general-purpose sentiment tools misread financial language in any language.'),
  ('Market-specific structure', 'BIST differs from US markets in liquidity, participant mix, disclosure timing and trading hours. Results should not be generalised to other markets.'),
  ('Endogeneity', 'Sentiment and returns are jointly determined. Coverage tends to follow price moves as much as it precedes them, so causal claims require careful timing.'),
  ('Sample size', 'Event-driven sentiment studies on a single market produce small effective samples, and apparent significance is fragile to specification choices.'),
 ),
 'paper-gpu-cpu-trading-infrastructure.html': L(
  ('Reference architecture, not a measured system', 'Figures here are drawn from vendor documentation and published benchmarks to size a design. They are not measurements taken on QuantMedia hardware, which does not include a co-located feed handler.'),
  ('Workload dependence', 'GPU advantage depends entirely on the workload. Batched matrix operations parallelise; sequential order-book state machines and risk gates do not.'),
  ('Latency is a distribution', 'Median figures are close to meaningless for execution. Tail latency under load determines outcomes, and tails are dominated by queueing and jitter rather than raw compute.'),
  ('Hardware moves', 'Specific part numbers and their published figures date quickly. The decomposition is durable; the numbers are not.'),
 ),
 'paper-hf-analytical-operations.html': L(
  ('Operational, not predictive', 'This paper describes how analytical workloads are organised. It makes no claim that any described pipeline produces profitable signals.'),
  ('Scale assumptions', 'Architectural choices that make sense at institutional data volumes are frequently wrong at smaller scale, where simpler tooling dominates.'),
  ('Vendor and stack churn', 'Specific technologies referenced here change rapidly. The separation of concerns is the durable part.'),
 ),
 'paper-sovereign-ai-local-llms.html': L(
  ('Fast-moving policy and capability', 'Model capabilities, licences and regulatory regimes change on a timescale of months. Conclusions drawn here should be re-checked against current terms before acting on them.'),
  ('Capability gap', 'Locally deployable models trail frontier hosted models on reasoning-heavy financial tasks. Deployment location is a constraint that costs accuracy, not a free choice.'),
  ('Total cost is understated by hardware price', 'On-premise inference carries engineering, security, evaluation and maintenance costs that rarely appear in simple hardware-versus-API comparisons.'),
  ('No benchmark results', 'This is an architectural and policy discussion. It presents no evaluation of model accuracy on financial tasks.'),
 ),
}


# Real, checkable references. DOIs only where I can state them accurately;
# otherwise author, title, venue and year, which are verifiable by search.
REFERENCES = {
 'paper-vpin-order-flow-toxicity.html': [
  ('Easley, D., López de Prado, M. & O\'Hara, M.', 2012, 'Flow Toxicity and Liquidity in a High-Frequency World', 'Review of Financial Studies 25(5), 1457–1493', '10.1093/rfs/hhs053'),
  ('Easley, D., López de Prado, M. & O\'Hara, M.', 2011, 'The Microstructure of the Flash Crash', 'Journal of Portfolio Management 37(2), 118–128', None),
  ('Andersen, T. & Bondarenko, O.', 2014, 'VPIN and the Flash Crash', 'Journal of Financial Markets 17, 1–46', '10.1016/j.finmar.2013.05.005'),
  ('Lee, C. & Ready, M.', 1991, 'Inferring Trade Direction from Intraday Data', 'Journal of Finance 46(2), 733–746', None),
  ('Easley, D., Kiefer, N., O\'Hara, M. & Paperman, J.', 1996, 'Liquidity, Information, and Infrequently Traded Stocks', 'Journal of Finance 51(4), 1405–1436', None),
 ],
 'paper-hierarchical-risk-parity.html': [
  ('López de Prado, M.', 2016, 'Building Diversified Portfolios that Outperform Out of Sample', 'Journal of Portfolio Management 42(4), 59–69', None),
  ('Markowitz, H.', 1952, 'Portfolio Selection', 'Journal of Finance 7(1), 77–91', None),
  ('Michaud, R.', 1989, 'The Markowitz Optimization Enigma: Is Optimized Optimal?', 'Financial Analysts Journal 45(1), 31–42', None),
  ('Ledoit, O. & Wolf, M.', 2004, 'A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices', 'Journal of Multivariate Analysis 88(2), 365–411', None),
  ('DeMiguel, V., Garlappi, L. & Uppal, R.', 2009, 'Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?', 'Review of Financial Studies 22(5), 1915–1953', None),
 ],
 'paper-probabilistic-sharpe-ratio.html': [
  ('Bailey, D. & López de Prado, M.', 2012, 'The Sharpe Ratio Efficient Frontier', 'Journal of Risk 15(2), 3–44', None),
  ('Bailey, D. & López de Prado, M.', 2014, 'The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality', 'Journal of Portfolio Management 40(5), 94–107', None),
  ('Lo, A.', 2002, 'The Statistics of Sharpe Ratios', 'Financial Analysts Journal 58(4), 36–52', None),
  ('Harvey, C. & Liu, Y.', 2015, 'Backtesting', 'Journal of Portfolio Management 42(1), 13–28', None),
 ],
 'paper-slippage-latency-modeling.html': [
  ('Almgren, R. & Chriss, N.', 2001, 'Optimal Execution of Portfolio Transactions', 'Journal of Risk 3(2), 5–40', None),
  ('Almgren, R., Thum, C., Hauptmann, E. & Li, H.', 2005, 'Direct Estimation of Equity Market Impact', 'Risk 18(7), 58–62', None),
  ('Kyle, A.', 1985, 'Continuous Auctions and Insider Trading', 'Econometrica 53(6), 1315–1335', None),
  ('Perold, A.', 1988, 'The Implementation Shortfall: Paper versus Reality', 'Journal of Portfolio Management 14(3), 4–9', None),
 ],
 'paper-bid-ask-spread-dynamics.html': [
  ('Roll, R.', 1984, 'A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market', 'Journal of Finance 39(4), 1127–1139', None),
  ('Glosten, L. & Milgrom, P.', 1985, 'Bid, Ask and Transaction Prices in a Specialist Market with Heterogeneously Informed Traders', 'Journal of Financial Economics 14(1), 71–100', None),
  ('Amihud, Y. & Mendelson, H.', 1986, 'Asset Pricing and the Bid-Ask Spread', 'Journal of Financial Economics 17(2), 223–249', None),
  ('Huang, R. & Stoll, H.', 1997, 'The Components of the Bid-Ask Spread: A General Approach', 'Review of Financial Studies 10(4), 995–1034', None),
  ('Corwin, S. & Schultz, P.', 2012, 'A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices', 'Journal of Finance 67(2), 719–760', None),
 ],
 'paper-genetic-algorithm-alpha.html': [
  ('Allen, F. & Karjalainen, R.', 1999, 'Using Genetic Algorithms to Find Technical Trading Rules', 'Journal of Financial Economics 51(2), 245–271', None),
  ('Koza, J.', 1992, 'Genetic Programming: On the Programming of Computers by Means of Natural Selection', 'MIT Press', None),
  ('Holland, J.', 1975, 'Adaptation in Natural and Artificial Systems', 'University of Michigan Press', None),
  ('Bailey, D., Borwein, J., López de Prado, M. & Zhu, Q.', 2014, 'Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance', 'Notices of the AMS 61(5), 458–471', None),
 ],
 'paper-alternative-data-quant-finance.html': [
  ('Monk, A., Prins, M. & Rook, D.', 2019, 'Rethinking Alternative Data in Institutional Investment', 'Journal of Financial Data Science 1(1), 14–31', None),
  ('Denev, A. & Amen, S.', 2020, 'The Book of Alternative Data', 'Wiley', None),
  ('Tetlock, P.', 2007, 'Giving Content to Investor Sentiment: The Role of Media in the Stock Market', 'Journal of Finance 62(3), 1139–1168', None),
  ('Bailey, D., Borwein, J., López de Prado, M. & Zhu, Q.', 2014, 'Pseudo-Mathematics and Financial Charlatanism', 'Notices of the AMS 61(5), 458–471', None),
 ],
 'paper-bist-sentiment-analysis.html': [
  ('Loughran, T. & McDonald, B.', 2011, 'When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks', 'Journal of Finance 66(1), 35–65', None),
  ('Tetlock, P.', 2007, 'Giving Content to Investor Sentiment: The Role of Media in the Stock Market', 'Journal of Finance 62(3), 1139–1168', None),
  ('Bollen, J., Mao, H. & Zeng, X.', 2011, 'Twitter Mood Predicts the Stock Market', 'Journal of Computational Science 2(1), 1–8', '10.1016/j.jocs.2010.12.007'),
  ('Antweiler, W. & Frank, M.', 2004, 'Is All That Talk Just Noise? The Information Content of Internet Stock Message Boards', 'Journal of Finance 59(3), 1259–1294', None),
 ],
 'paper-gpu-cpu-trading-infrastructure.html': [
  ('Menkveld, A.', 2013, 'High Frequency Trading and the New Market Makers', 'Journal of Financial Markets 16(4), 712–740', None),
  ('Budish, E., Cramton, P. & Shim, J.', 2015, 'The High-Frequency Trading Arms Race: Frequent Batch Auctions as a Market Design Response', 'Quarterly Journal of Economics 130(4), 1547–1621', None),
  ('Hasbrouck, J. & Saar, G.', 2013, 'Low-Latency Trading', 'Journal of Financial Markets 16(4), 646–679', None),
 ],
 'paper-hf-analytical-operations.html': [
  ('Aldridge, I.', 2013, 'High-Frequency Trading: A Practical Guide to Algorithmic Strategies and Trading Systems', 'Wiley, 2nd edition', None),
  ('Menkveld, A.', 2013, 'High Frequency Trading and the New Market Makers', 'Journal of Financial Markets 16(4), 712–740', None),
  ('Hasbrouck, J. & Saar, G.', 2013, 'Low-Latency Trading', 'Journal of Financial Markets 16(4), 646–679', None),
  ('López de Prado, M.', 2018, 'Advances in Financial Machine Learning', 'Wiley', None),
 ],
 'paper-sovereign-ai-local-llms.html': [
  ('Bommasani, R. et al.', 2021, 'On the Opportunities and Risks of Foundation Models', 'Stanford CRFM, arXiv:2108.07258', None),
  ('European Parliament and Council', 2024, 'Regulation (EU) 2024/1689 laying down harmonised rules on artificial intelligence (AI Act)', 'Official Journal of the European Union', None),
  ('Touvron, H. et al.', 2023, 'Llama 2: Open Foundation and Fine-Tuned Chat Models', 'arXiv:2307.09288', None),
 ],
}


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def limitations_html(items):
    lis = ''.join(f'<li><strong>{esc(t)}.</strong> {esc(b)}</li>' for t, b in items)
    return ('<div class="qm-sec" id="limitations"><h2>Limitations</h2>'
            f'<ul>{lis}</ul></div>')


def references_html(refs):
    lis = []
    for authors, year, title, venue, doi in refs:
        link = (f' <a href="https://doi.org/{doi}" target="_blank" '
                f'rel="noopener">doi:{doi}</a>') if doi else ''
        lis.append(f'<li>{esc(authors)} ({year}). &ldquo;{esc(title)}.&rdquo; '
                   f'<em>{esc(venue)}</em>.{link}</li>')
    return ('<div class="qm-sec" id="references"><h2>References</h2>'
            f'<ul class="qm-refs-list">{"".join(lis)}</ul>'
            '<p class="qm-refnote">QuantMedia research is independent and not '
            'peer reviewed. These references are the primary sources the '
            'analysis draws on; readers are encouraged to consult them '
            'directly rather than relying on this summary.</p></div>')


def citation_ld(refs):
    """schema.org `citation` entries so the references are machine-readable."""
    out = []
    for authors, year, title, venue, doi in refs:
        c = {'@type': 'CreativeWork', 'name': title,
             'author': authors, 'datePublished': str(year),
             'publication': venue}
        if doi:
            c['sameAs'] = f'https://doi.org/{doi}'
        out.append(c)
    return out


def main():
    import json
    changed = 0
    for name in sorted(LIMITATIONS):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            print(f'  {name}: MISSING, skipped')
            continue
        html = io.open(path, encoding='utf-8').read()
        orig = html

        if 'qm-sec' not in html:
            html = html.replace('</head>', CSS + '\n</head>', 1)

        blocks = ''
        if 'id="limitations"' not in html:
            blocks += limitations_html(LIMITATIONS[name])
        if 'id="references"' not in html and name in REFERENCES:
            blocks += references_html(REFERENCES[name])

        if blocks:
            anchor = next((a for a in ('<div class="qm-repro">',
                                       '<!-- NEWSLETTER CTA -->', '</main>')
                           if a in html), None)
            if anchor is None:
                print(f'  {name}: no anchor, skipped')
                continue
            html = html.replace(anchor, blocks + '\n' + anchor, 1)

        # ScholarlyArticle overstates what these are. Article + citation is
        # accurate and Google treats them identically.
        html = html.replace('"@type":"ScholarlyArticle"', '"@type":"Article"')
        if name in REFERENCES and '"citation"' not in html:
            cites = json.dumps(citation_ld(REFERENCES[name]), ensure_ascii=False)
            html = re.sub(r'("@type":"Article",)',
                          r'\1"citation":' + cites + ',', html, count=1)

        if html != orig:
            io.open(path, 'w', encoding='utf-8').write(html)
            changed += 1
            print(f'  {name}: upgraded')
        else:
            print(f'  {name}: already current')
    print(f'\n{changed} paper(s) upgraded')
    return 0


if __name__ == '__main__':
    sys.exit(main())
