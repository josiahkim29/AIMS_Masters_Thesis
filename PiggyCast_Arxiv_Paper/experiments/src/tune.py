"""Nested hyperparameter tuning of the XGBoost stacks (Experiment A data, see multiyear.py).

Protocol (no test data is used for tuning):
  * For each lead and training length N (60 or 700 days), hyperparameters are chosen ONCE on the
    training window of the first test fold (January 2022), i.e. on data before the test year.
    That window is split in time: the last 20% of its days is the validation block, and the inner
    training block ends one leakage-safe gap (5 days + lead) before it. The inner training rows are
    randomly subsampled to at most 600k for speed.
  * Grid: max_depth {4, 8} x min_child_weight {1, 100} x reg_lambda {1, 50}, learning rate 0.05,
    subsample 0.8, colsample_bytree 0.8, up to 2000 trees with early stopping (50 rounds) on the
    validation block. The selected setting and its best number of trees are then frozen.
  * Each of the 12 monthly folds of 2022 is refit with the frozen setting on its full N-day window.
Writes res/tuning_A.csv (per lead x N x method: tuned fold-mean RMSE, default and PiggyCast-Lin
RMSE from res/multiyear_A.csv, chosen parameters, per-fold RMSEs).
Usage: python src/tune.py <experiments dir> [leads]
"""
import os, sys, json, time, itertools
S = sys.argv[1]
LEADS = [int(a) for a in sys.argv[2].split(",")] if len(sys.argv) > 2 else [24, 120, 240]
sys.argv = ["multiyear.py", S, "A"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, xgboost as xgb
import multiyear as my

GRID = [dict(max_depth=d, min_child_weight=m, reg_lambda=l) for d, m, l in itertools.product([4, 8], [1, 100], [1, 50])]
FIXED = dict(learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, tree_method="hist", n_jobs=12, random_state=42)
CAP = 600_000
rng = np.random.default_rng(0)
NPIX, M = my.NPIX, len(my.MODELS)


def features(stack, c, idx, resid):
    mmm = stack[idx].mean(-1)
    if resid:
        cols = [(stack[idx] - mmm[..., None]).reshape(-1, M), (mmm - c[idx]).ravel()[:, None]]
    else:
        cols = [stack[idx].reshape(-1, M)]
    cols += [np.tile(my.LON, len(idx))[:, None], np.tile(my.LAT, len(idx))[:, None]]
    return np.hstack(cols), mmm.ravel()


def target(y, idx, mmm, resid):
    return y[idx].ravel() - mmm if resid else y[idx].ravel()


def window(tr_end, days, ok):
    return np.where((my.VALID < tr_end) & (my.VALID >= tr_end - pd.Timedelta(days=days)) & ok)[0]


ref = pd.read_csv(f"{S}/res/multiyear_A.csv")
rows = []
for L in LEADS:
    stack, y, c, ok = my.build(L)
    gap = pd.Timedelta(days=5 + L // 24)
    for N in [60, 700]:
        for method, resid in [("xgb_orig", False), ("xgb_resid", True)]:
            t0 = time.time()
            # ---- tune once on the January-2022 training window
            tr_end = pd.Timestamp(2022, 1, 1) - gap
            tr = window(tr_end, N, ok)
            v_start = my.VALID[tr[0]] + 0.8 * (my.VALID[tr[-1]] - my.VALID[tr[0]])
            va = tr[my.VALID[tr] >= v_start]
            it = tr[my.VALID[tr] < v_start - gap]
            Xi, mi = features(stack, c, it, resid); yi = target(y, it, mi, resid); wi = np.tile(my.w, len(it))
            Xv, mv = features(stack, c, va, resid); yv = target(y, va, mv, resid); wv = np.tile(my.w, len(va))
            if len(yi) > CAP:
                k = rng.choice(len(yi), CAP, replace=False); Xi, yi, wi = Xi[k], yi[k], wi[k]
            best = None
            for g in GRID:
                m = xgb.XGBRegressor(n_estimators=2000, early_stopping_rounds=50, eval_metric="rmse", **FIXED, **g)
                m.fit(Xi, yi, sample_weight=wi, eval_set=[(Xv, yv)], sample_weight_eval_set=[wv], verbose=False)
                score = m.best_score
                if best is None or score < best[0]:
                    best = (score, g, m.best_iteration + 1)
            score, g, ntree = best
            # ---- frozen refit per monthly fold
            fr = []
            for mo in range(1, 13):
                ts = pd.Timestamp(2022, mo, 1)
                te = np.where((my.VALID >= ts) & (my.VALID < ts + pd.offsets.MonthBegin(1)) & ok)[0]
                trk = window(ts - gap, N, ok)
                Xa, ma = features(stack, c, trk, resid)
                Xb, mb = features(stack, c, te, resid)
                m = xgb.XGBRegressor(n_estimators=ntree, **FIXED, **g).fit(Xa, target(y, trk, ma, resid), sample_weight=np.tile(my.w, len(trk)))
                p = m.predict(Xb) + (mb if resid else 0)
                fr.append(float(np.sqrt(my.stats(p.reshape(len(te), NPIX), y[te], c[te])[0].mean())))
            r = ref[(ref.lead == L) & (ref.train.astype(str) == str(N))].set_index("method").rmse_foldmean
            rows.append(dict(lead=L, train=N, method=method, rmse_tuned=float(np.mean(fr)), rmse_default=float(r[method]),
                             rmse_lin=float(r["lin_clim"]), rmse_mmm=float(r["mmm"]), n_trees=int(ntree), val_rmse=float(score),
                             **g, fold_rmse=json.dumps([round(v, 3) for v in fr])))
            d = rows[-1]
            print(L, N, method, g, ntree, f"tuned {d['rmse_tuned']:.1f} default {d['rmse_default']:.1f} lin {d['rmse_lin']:.1f}",
                  f"{time.time() - t0:.0f}s", flush=True)
            pd.DataFrame(rows).to_csv(f"{S}/res/tuning_A.csv", index=False)
print("done")
