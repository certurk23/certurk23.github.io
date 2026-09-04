# QuantMedia

Free quantitative finance tools, worked examples and research at
[quantmedia.io](https://quantmedia.io). The site is a static GitHub Pages project.

| Start here | What you can do |
| --- | --- |
| [PSR calculator](https://quantmedia.io/tools/probabilistic-sharpe-ratio-calculator.html) | Examine how sample length and return moments affect a Sharpe estimate. |
| [Worked examples](https://quantmedia.io/reports/) | Follow the inputs, calculations, results and limitations for VPIN, HRP and PSR. |
| [Python research packages](quantmedia-research/) | Run two implementations, 28 tests and fixed-seed examples without a market-data subscription. |
| [Implementation index](https://quantmedia.io/reproducibility.html) | See which research has runnable code and which remains explanatory. |

Access is free. Advertising through AdSense is the intended funding model;
see the [editorial policy](https://quantmedia.io/editorial-policy.html) for the
published funding status and disclosures.

## Run the research

```text
git clone https://github.com/certurk23/certurk23.github.io.git
cd certurk23.github.io
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` in PowerShell or
`source .venv/bin/activate` in macOS/Linux. For the environment used by the
worked examples, use Python 3.11 and then:

```text
python -m pip install -r quantmedia-research/requirements-verified.txt
python quantmedia-research/tests/test_vpin.py
python quantmedia-research/tests/test_hrp.py
python quantmedia-research/verify_examples.py
```

The final command runs both examples in temporary directories and compares all
five CSV files with the shipped results. It does not overwrite the source tree.
See the [research README](quantmedia-research/README.md) to run or modify an
individual experiment. After installation, the examples run offline.

All example data is **synthetic**. Passing tests and reproducing the examples
does not establish real-market forecasting ability or profitable trading.

## Preview and edit the site

```text
python -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/`. Root HTML pages are edited directly. Generated
learning pages, tools, reports and identity pages are defined in
`scripts/build_pages.py` and its `page_content*.py` modules. Run
`python scripts/build_pages.py` after changing those sources. It preserves
daily readings inside the `QM` markers. Do not edit a generated page alone;
the next build will replace it.

## Verify changes

```text
python scripts/validate_site.py
python scripts/test_pipeline.py
node scripts/test_psr.js
```

The research workflow additionally checks that generated HTML agrees with its
source, runs the two research test suites and reproduces their CSV output.
Node is needed only for the calculator checks, not to serve the static site.

## Daily data

The existing daily workflow updates post-close snapshots and preserves the
last known good source when an upstream feed fails. Methodology lives in
`scripts/qm_config.py`; data timestamps and source states are exposed in
`data/status.json`. Synthetic research examples are separate from these market
snapshots. No credentials are needed to read the site or run the research.
