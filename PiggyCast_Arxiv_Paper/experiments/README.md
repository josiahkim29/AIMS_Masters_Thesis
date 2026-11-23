# PiggyCast paper experiments

Reproduces every number, table and figure in `../master_document.tex`.

```bash
cd experiments
uv sync            # creates .venv from pyproject.toml / uv.lock
./run_all.sh       # downloads ~260 MB from the public WeatherBench 2 bucket, then runs everything (~10 min, CPU only)
```

| Script | Produces |
|---|---|
| `src/download.py` | Z500 forecasts (4 models, 24–240 h), ERA5, ERA5 1990–2019 climatology → `data/` |
| `src/exp.py` | All combiners × 10 leads × 10 folds × {5-day gap, leakage-safe gap} → `res/results.csv` (Table 2, Appendix A), per-time errors, RMSE maps |
| `src/analysis.py` | Block-bootstrap CIs (Table 3), base-model error correlations |
| `src/extra.py` | Linear stacking weights, SHAP, training-length sensitivity, pairwise RMSE + MDS |
| `src/casestudy.py` | Case-study polar maps (Fig. 5) |
| `src/figs.py` | All other figures → `../figures/` |
| `src/lin_vs_base.py` | PiggyCast-Lin vs each base model, days 1–10: skill curves and RMSE-ratio maps |
| `src/download_multiyear.py` | Multi-year forecasts (IFS HRES 2017–22, Pangu HRES-init 2020–22, Pangu and GraphCast ERA5-init) and ERA5, ~1.3 GB |
| `src/multiyear.py` | Appendix E: two-model (A) and three-model (B) stacks trained on up to two years, tested on 2022 |
| `src/multiyear_fig.py` | Fig. E1 from `res/multiyear_A.csv` and `res/multiyear_B.csv` |
| `src/tune.py` | Table E1: nested hyperparameter tuning of PiggyCast-XGB and -XGB-R on Experiment A |

Key protocol choices (see paper Sect. 3c): valid-time indexing; common valid window
2020-01-11T00 – 2021-01-01T12 for all leads; 10 folds of 30-day tests / 60-day training;
gap = 5 days + lead time so training targets are verified before test forecasts are issued.

## Results notebook (for review)

`notebooks/PiggyCast_results.ipynb` walks through every result in the paper, with tables, figures, per-fold and per-latitude breakdowns, a case-study explorer and open questions for co-authors. It is committed with its outputs, so it can be read on GitHub without running anything. To run it yourself:

```bash
uv sync --group notebook
uv run --group notebook jupyter lab notebooks/PiggyCast_results.ipynb
```

Sections 1–9 read only the precomputed results in `res/` (committed, about 3 MB). The case-study explorer (section 10) also needs `data/`; run `./run_all.sh` first.
