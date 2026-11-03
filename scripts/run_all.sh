#!/usr/bin/env bash
# One-command reproduction (Git Bash on Windows, or any Unix shell).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONUTF8=1
export HF_HOME="$PWD/.cache/hf"

if [ ! -d .venv ]; then python -m venv .venv; fi
if [ -f .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe; else PY=.venv/bin/python; fi
$PY -m pip install -q -r requirements.txt

$PY scripts/fetch_assets.py          # FLORES-200 tarball + Noto fonts
$PY src/data.py --per-lang 50000     # Sangraha training corpus (streamed)
$PY src/train_tokenizers.py          # standard / akshara-atomic BPE + Unigram
$PY src/metrics.py --workers 4       # FLORES metrics for every tokenizer
$PY src/stats.py                     # bootstrap CIs + Wilcoxon tests
$PY src/vocab_analysis.py            # vocabulary composition + lineage
$PY src/metadata.py                  # results/run_metadata.json
$PY src/plots.py                     # figures/
$PY -m pytest -q
