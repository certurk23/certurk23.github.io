# QuantMedia Research — reproducible implementations

Runnable code behind the research published at
[quantmedia.io](https://quantmedia.io). Index of everything, with status:
[quantmedia.io/reproducibility.html](https://quantmedia.io/reproducibility.html)

Each package implements the methodology described in its corresponding paper,
ships example data and expected output, and is covered by tests. Nothing here
requires an API key or a paid data feed. After downloading the code and
installing dependencies, the examples run offline.

## Worked examples and reproducibility checks

Read the [free worked examples](https://quantmedia.io/reports/) for the inputs,
output and limitations. The examples were checked using Python 3.11.9 and the
versions in [`requirements-verified.txt`](requirements-verified.txt).

From the repository root, run:

```text
python -m pip install -r quantmedia-research/requirements-verified.txt
python quantmedia-research/verify_examples.py
```

This reruns both examples in temporary directories and compares all five
generated CSV files with the committed versions. The Research and Site Checks
workflow runs it alongside the implementation tests and calculator checks.

## Packages

| Package | Paper | Status | Tests |
|---|---|---|---|
| [`vpin-order-flow-toxicity/`](vpin-order-flow-toxicity/) | [VPIN & Order Flow Toxicity](https://quantmedia.io/paper-vpin-order-flow-toxicity.html) | Reproducible | 15 |
| [`hierarchical-risk-parity/`](hierarchical-risk-parity/) | [Hierarchical Risk Parity](https://quantmedia.io/paper-hierarchical-risk-parity.html) | Reproducible | 13 |

The Probabilistic Sharpe Ratio is published as an
[interactive calculator](https://quantmedia.io/tools/probabilistic-sharpe-ratio-calculator.html)
rather than a package: the formula is a single expression and the tool exposes
every intermediate term.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate

cd vpin-order-flow-toxicity
pip install -r requirements.txt
python example.py

cd ../hierarchical-risk-parity
pip install -r requirements.txt
python compare_mvo.py

cd ..
python tests/test_vpin.py     # 15 tests
python tests/test_hrp.py      # 13 tests
```

Python 3.9+. Dependencies: numpy, pandas, scipy.

## A note on the sample data

> Both packages ship **synthetic** example data generated from fixed seeds.
> It is **not** real market data, not a recording of any actual instrument, and
> no conclusion about any real security can be drawn from it. It exists so the
> implementations can be run and verified end-to-end without a paid tick-data
> subscription. Each package repeats this in its README, its module docstring
> and its console output.

Synthetic data is used deliberately rather than shipping a redistributed
vendor sample, which would create a licensing problem and would not be
reproducible for anyone without the same subscription.

## What is deliberately not here

- **A live VPIN feed.** The VPIN code is complete and runnable, but QuantMedia's
  production pipeline collects end-of-day OHLCV, not tick or quote data. VPIN
  cannot be computed from daily bars, so no live reading is published.
- **Production signal-engine code.** The daily scan that powers
  [quantmedia.io/quantum-signals.html](https://quantmedia.io/quantum-signals.html)
  lives in the site repository. Its parameters are published as
  [signal_config.json](https://quantmedia.io/data/signal_config.json) and
  documented in full at
  [methodology.html](https://quantmedia.io/methodology.html#signal-engine).
- **Any API key, credential or private dataset.**

## Citation

```
QuantMedia (2026). VPIN & Order Flow Toxicity: A Practical Microstructure Signal.
https://quantmedia.io/paper-vpin-order-flow-toxicity.html

QuantMedia (2026). Hierarchical Risk Parity: Portfolio Construction Without
Matrix Inversion.
https://quantmedia.io/paper-hierarchical-risk-parity.html
```

Free to use and cite with attribution.

## Licence

MIT for the code. Research text on quantmedia.io is free to quote with
attribution.
