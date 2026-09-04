# QuantMedia — verified quantitative finance code

**quantmedia.io** publishes implementations of quantitative finance methods
together with the evidence that they are correct: a synthetic input whose
right answer is known in advance, the unedited output the code produced, the
defects found along the way, and the tests that now guard them.

Language models generate a plausible implementation of almost any finance
paper in seconds. They cannot tell you whether it is right. This repository is
built around the part that keeps its value as generation becomes free:
**verification**.

Everything here is free to read, run and cite. There is no paywall and no
registration.

## What is verified

| Method | Package | Tests | Report |
|---|---|---|---|
| VPIN — order-flow toxicity (Easley, López de Prado, O'Hara) | `quantmedia-research/vpin-order-flow-toxicity/` | 15 | [Verification report](https://quantmedia.io/reports/vpin-example.html) |
| Hierarchical Risk Parity (López de Prado) | `quantmedia-research/hierarchical-risk-parity/` | 13 | [Verification report](https://quantmedia.io/reports/hrp-example.html) |
| Probabilistic Sharpe Ratio (Bailey, López de Prado) | client-side calculator + `scripts/test_psr.js` | — | [Verification report](https://quantmedia.io/reports/psr-worked-example.html) |

Three defects were found by running this code against known ground truth, and
all three are documented on the report pages rather than quietly patched:

- **VPIN** returned zero toxicity for a perfectly one-sided tape — the opposite
  of the correct answer — because the degenerate branch split volume 50/50.
- **HRP** raised under pandas 3 (read-only view) and produced a distance matrix
  `squareform` rejected as asymmetric.
- **PSR** — the worked example published on the site itself was arithmetically
  wrong; the kurtosis term does not vanish at γ₂ = 3.

## Reproduce every published number in one command

```bash
pip install -r quantmedia-research/requirements-verified.txt
python quantmedia-research/verify_examples.py
```

This re-runs both packages in a clean temporary directory and asserts that
every shipped output file matches the committed one to nine decimal places.
Then:

```bash
cd quantmedia-research
python tests/test_vpin.py     # expected: 15 passed
python tests/test_hrp.py      # expected: 13 passed
```

Example data is **synthetic, from fixed seeds**, and says so in the README,
the module docstring and the console output. Synthetic data proves the
mechanism behaves as specified; it proves nothing about live markets, and no
trading result is implied anywhere.

## Live pipeline

A GitHub Actions job runs after each US close (`.github/workflows/daily-update.yml`)
and publishes two metrics computed from a 30-signal scan of 180 liquid US
equities, with their freshness state and no backfilling:

- [Signal Breadth Index](https://quantmedia.io/indices/signal-breadth.html) — `data/signal_breadth.json`
- [Sector Confluence Index](https://quantmedia.io/indices/sector-confluence.json) — `data/sector_confluence.json`

The pipeline is fail-safe by design: each source degrades independently to its
last known good value, `data/status.json` states what is fresh and what is
not, and `scripts/validate_site.py` refuses to commit a build that contradicts
its own data. The scan is a demonstration of that discipline. It has no
forward-tested track record and is not a signal service.

## Repository layout

```
quantmedia-research/     verified implementations, tests, verify_examples.py
scripts/daily_update.py  the post-close pipeline
scripts/validate_site.py the corruption gate that runs before every commit
scripts/test_pipeline.py 43 reliability tests, stdlib only
scripts/build_pages.py   generator for /reports, /learn, /indices, /tools
reports/                 dated verification reports
data/                    machine-readable outputs (JSON)
```

## Verification for your own code

If you have written or generated an implementation of one of these methods,
point it at the synthetic inputs described in the matching report and compare.
If you would like a report written against your implementation — same ground
truth, same discipline, a dated document you can cite — contact
contact@quantmedia.io.

## Author and policy

Written and operated by [Cemil Ertürk](https://quantmedia.io/author/cemil-erturk.html).
Independent; not peer reviewed; no affiliation with any fund, broker or
exchange. How research is produced, corrected and funded is set out in the
[editorial policy](https://quantmedia.io/editorial-policy.html). Corrections
are recorded, not silently absorbed.

Educational and informational only. Nothing here is investment advice.
