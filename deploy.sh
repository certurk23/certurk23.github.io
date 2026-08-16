#!/usr/bin/env bash
#
# QuantMedia deploy helper
# ========================
# This working folder is a ZIP snapshot, not a git clone, so it cannot push on
# its own. This script clones the real repository into a temp directory, copies
# the changed files across, validates the result, shows you the diff, and only
# then asks whether to commit and push.
#
# It never force-pushes and never touches anything outside the repo it clones.
#
#   bash deploy.sh                 # review only, then prompts before pushing
#   bash deploy.sh --dry-run       # review only, never prompts
#
set -euo pipefail

REPO="${QM_REPO:-https://github.com/certurk23/certurk23.github.io.git}"
BRANCH="${QM_BRANCH:-main}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# Everything this change set touches. Anything not listed is left alone, so a
# stale local copy can never revert unrelated work in the repo.
FILES=(
  index.html markets.html news.html stocks.html quantum-signals.html
  papers.html methodology.html research.html about.html infrastructure.html
  sector-rotation-guide.html claude-ai-trading.html
  paper-alternative-data-quant-finance.html paper-bid-ask-spread-dynamics.html
  paper-bist-sentiment-analysis.html paper-genetic-algorithm-alpha.html
  paper-gpu-cpu-trading-infrastructure.html paper-hf-analytical-operations.html
  paper-hierarchical-risk-parity.html paper-probabilistic-sharpe-ratio.html
  paper-slippage-latency-modeling.html paper-sovereign-ai-local-llms.html
  paper-vpin-order-flow-toxicity.html
  qm-data.js sitemap.xml
  data/quantum_signals.json data/status.json
  scripts/daily_update.py scripts/qm_config.py
  scripts/validate_site.py scripts/test_pipeline.py
  .github/workflows/daily-update.yml
)

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo "==> Cloning $REPO ($BRANCH)"
git clone --quiet --branch "$BRANCH" --depth 20 "$REPO" "$WORK/repo"
cd "$WORK/repo"

echo "==> Copying ${#FILES[@]} files"
for f in "${FILES[@]}"; do
  if [[ ! -f "$SRC/$f" ]]; then
    echo "    !! missing locally, skipped: $f"
    continue
  fi
  mkdir -p "$(dirname "$f")"
  cp "$SRC/$f" "$f"
done

# The old ledger was superseded by data/status.json.
[[ -f data/site_status.json ]] && git rm --quiet --ignore-unmatch data/site_status.json

# Find a real interpreter. On Windows, bare `python` is often the Microsoft
# Store stub, which prints an error and exits non-zero instead of running.
PY=""
for cand in python3 python py; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import sys" >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done

if [[ -z "$PY" ]]; then
  echo
  echo "!! No working Python found on this machine."
  echo "   The test suite and production validator cannot run locally."
  echo "   Both still run in GitHub Actions on every scheduled run, so this"
  echo "   only means you are deploying without a local pre-flight check."
  echo
  read -r -p "   Continue without local validation? [y/N] " skip
  [[ "$skip" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
else
  echo
  echo "==> Reliability tests ($PY)"
  "$PY" scripts/test_pipeline.py || { echo "TESTS FAILED - aborting"; exit 1; }

  echo
  echo "==> Production validation"
  "$PY" scripts/validate_site.py || { echo "VALIDATION FAILED - aborting"; exit 1; }
fi

echo
echo "==> Changes to be pushed"
git add -A
git diff --staged --stat

if git diff --staged --quiet; then
  echo "Nothing to deploy - the repo already matches."
  exit 0
fi

if $DRY_RUN; then
  echo
  echo "--dry-run: stopping here. Nothing was committed or pushed."
  exit 0
fi

echo
read -r -p "Commit and push these changes to $BRANCH? [y/N] " reply
if [[ ! "$reply" =~ ^[Yy]$ ]]; then
  echo "Aborted. Nothing was pushed."
  exit 0
fi

git -c user.name="${GIT_AUTHOR_NAME:-QuantMedia}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-contact@quantmedia.io}" \
    commit --quiet -m "Fix data pipeline reliability and site consistency

- restore missing <script> tag on markets.html (raw JS was rendering as text
  and no script on the page ran)
- replace the placeholder-dash crypto grid with real snapshot rendering
- stop labelling stale snapshots as live data
- remove hardcoded Finnhub/FMP keys from client-side source
- unify signal methodology on 180 equities / 30 signals / 22 threshold
- add trading-day aware market_date, last-known-good preservation,
  bounded retries, pre-commit validation and data/status.json"

git push origin "HEAD:$BRANCH"

echo
echo "==> Pushed. GitHub Pages usually serves the change within ~1-2 minutes."
echo "    Verify:  curl -s https://quantmedia.io/data/status.json"
echo "    Then run the workflow once: Actions > Daily Market Update > Run workflow"
