"""Extra analyses: linear stacking weights, SHAP, training-length sensitivity, MDS."""
import sys, os, json
S = sys.argv[1]
sys.argv = ["exp.py", f"{S}/data", f"{S}/res"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import exp
from exp import *  # noqa
import shap
from sklearn.manifold import MDS

what = os.environ.get("WHAT", "coef,shap,trainlen,mds").split(",")

if "coef" in what:
    rows = []
    for L in exp.LEADS:
        F, y, c = exp.build(L)
        stack = np.stack([F[m] for m in exp.MODELS], -1)
        gap = exp.GAP0 + L // 24 * exp.STEPS_PER_DAY
        for k, (tr, te) in enumerate(exp.folds(gap)):
            X = np.column_stack([stack[tr].reshape(-1, 4), np.ones(len(tr) * exp.NPIX), c[tr].ravel()])
            coef = exp.wls(X, y[tr].ravel(), np.tile(exp.w, len(tr)))
            rows.append(dict(lead=L, fold=k, **{m: coef[i] for i, m in enumerate(exp.MODELS)}, intercept=coef[4], clim=coef[5]))
    df = pd.DataFrame(rows); df.to_csv(f"{S}/res/lin_clim_coefs.csv", index=False)
    print(df.groupby("lead")[exp.MODELS + ["clim"]].mean().round(3).to_string())

if "shap" in what:
    rows = []
    rng = np.random.default_rng(0)
    for L in exp.LEADS:
        F, y, c = exp.build(L)
        stack = np.stack([F[m] for m in exp.MODELS], -1)
        gap = exp.GAP0 + L // 24 * exp.STEPS_PER_DAY
        for k, (tr, te) in enumerate(exp.folds(gap)):
            if k not in (0, 4, 9):
                continue
            def feats(idx):
                return np.column_stack([stack[idx, :, j].ravel() for j in range(4)] + [np.tile(exp.LON, len(idx)), np.tile(exp.LAT, len(idx))])
            m = exp.fit_xgb(feats(tr), y[tr].ravel(), np.tile(exp.w, len(tr)), {})
            Xte = feats(te)
            sub = rng.choice(len(Xte), 20000, replace=False)
            sv = shap.TreeExplainer(m).shap_values(Xte[sub])
            wt = np.tile(exp.w, len(te))[sub]
            imp = (np.abs(sv) * wt[:, None]).sum(0) / wt.sum()
            rows.append(dict(lead=L, fold=k, **dict(zip(exp.MODELS + ["longitude", "latitude"], imp))))
        print(L, flush=True)
    df = pd.DataFrame(rows); df.to_csv(f"{S}/res/shap_xgb_orig.csv", index=False)
    print(df.groupby("lead").mean().drop(columns="fold").round(1).to_string())

if "trainlen" in what:
    allrows = []
    for days in [15, 30, 60, 120]:
        exp.TRAIN = days * exp.STEPS_PER_DAY
        out = f"{S}/res_train{days}"; os.makedirs(out, exist_ok=True); exp.OUT = out
        for L in [48, 120, 240]:
            rows = exp.run_lead(L, "gapsafe")
            for r in rows: r["train_days"] = days
            allrows += rows
            print(days, L, {r["method"]: round(r["rmse_foldmean"], 1) for r in rows if r["method"] in ("mmm", "lin", "lin_clim", "lin_pix", "xgb_orig", "xgb_resid")}, flush=True)
    pd.DataFrame(allrows).to_csv(f"{S}/res/trainlen.csv", index=False)

if "mds" in what:
    # pairwise area-weighted RMSE between ERA5 and each model at each lead (common window)
    names, fields = [], []
    y = None
    for L in exp.LEADS:
        F, y, c = exp.build(L)
        for m in exp.MODELS:
            names.append(f"{m}_{L}"); fields.append(F[m])
    names.append("era5"); fields.append(y)
    n = len(fields); D = np.zeros((n, n))
    ws = exp.w / exp.w.sum()
    for i in range(n):
        for j in range(i + 1, n):
            D[i, j] = D[j, i] = np.sqrt((((fields[i] - fields[j]) ** 2) * ws).sum(1).mean())
    np.save(f"{S}/res/pairwise_rmse.npy", D)
    json.dump(names, open(f"{S}/res/pairwise_names.json", "w"))
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=0, n_init=8, max_iter=1000, eps=1e-9, normalized_stress="auto")
    X = mds.fit_transform(D)
    np.save(f"{S}/res/mds_coords.npy", X)
    print("stress", mds.stress_)
