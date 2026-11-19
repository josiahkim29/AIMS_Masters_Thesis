#!/usr/bin/env bash
# Reproduce every experiment, table number and figure in the PiggyCast paper.
#   cd PiggyCast_Arxiv_Paper/experiments && uv sync && ./run_all.sh
# Downloads ~270 MB of public WeatherBench 2 data (anonymous GCS access); ~10 min end to end on a laptop.
set -euo pipefail
cd "$(dirname "$0")"
PY=".venv/bin/python -I"
HERE="$(pwd)"; FIGS="$HERE/../figures"
mkdir -p data res "$FIGS"
[ -f data/forecasts_z500_2020.nc ] || $PY src/download.py "$HERE/data"
$PY src/exp.py "$HERE/data" "$HERE/res"                         # main results (Table 2, appendix A)
$PY src/analysis.py "$HERE"                                      # bootstrap CIs (Table 3), error correlations
WHAT=coef,shap,trainlen,mds $PY src/extra.py "$HERE"             # weights, SHAP, training length, MDS
$PY src/casestudy.py "$HERE" "$FIGS"                             # case-study maps
$PY src/figs.py "$HERE" "$FIGS"                                  # all other figures
$PY src/lin_vs_base.py "$HERE" "$FIGS"                           # PiggyCast-Lin vs each base model (curves + maps)
# Multi-year side experiment (appendix E): ~1.3 GB extra download, ~25 min. Skip with SKIP_MULTIYEAR=1.
if [ -z "${SKIP_MULTIYEAR:-}" ]; then
  [ -f data/multiyear_z500.nc ] || $PY src/download_multiyear.py "$HERE/data"
  $PY src/multiyear.py "$HERE" A && $PY src/multiyear.py "$HERE" B
  $PY src/multiyear_fig.py "$HERE" "$FIGS"                       # Fig. E1
  $PY src/tune.py "$HERE"                                        # Table E1: nested XGBoost tuning (~10 min)
fi
