"""PiggyCast experiment suite.

Reproduces the thesis setup (Z500, 5.625 deg, valid-time indexed, 10-fold
TimeSeriesSplit with 60-day train / 30-day test / 5-day gap) and adds:
  * a leakage-safe gap (5 days + lead time) with identical test windows,
  * simple stacking baselines (multi-model mean, linear stacking, per-gridpoint
    linear stacking a la Krishnamurti superensemble),
  * PiggyCast variants (original, residual target, no lat/lon),
  * metrics beyond RMSE: ACC, bias, activity ratio (smoothing diagnostic),
  * per-time squared errors for paired block-bootstrap significance tests.
"""
import os, sys, json, time, warnings
import numpy as np, pandas as pd, xarray as xr, xgboost as xgb

warnings.filterwarnings("ignore")
DATA, OUT = sys.argv[1], sys.argv[2]
LEADS = [int(a) for a in sys.argv[3].split(",")] if len(sys.argv) > 3 else [24 * k for k in range(1, 11)]
MODELS = ["graphcast", "pangu", "neuralgcm", "ifshres"]
STEPS_PER_DAY = 2
N_SPLITS, TRAIN, TEST, GAP0 = 10, 60 * STEPS_PER_DAY, 30 * STEPS_PER_DAY, 5 * STEPS_PER_DAY

fc = xr.open_dataset(f"{DATA}/forecasts_z500_2020.nc")
era = xr.open_dataset(f"{DATA}/era5_z500.nc")["era5"]
clim = xr.open_dataset(f"{DATA}/clim_z500.nc")["clim"]
lat = fc.latitude.values
w2d = np.broadcast_to(np.cos(np.deg2rad(lat))[:, None], (len(lat), len(fc.longitude))).astype(np.float64)
w = w2d.ravel()
LON, LAT = np.meshgrid(fc.longitude.values, lat)
LON, LAT = LON.ravel(), LAT.ravel()
NPIX = w.size

# Common valid-time window available at every lead (inits 2020-01-01T00..2020-12-31T12,
# leads 24..240 h) so that all lead times are verified on identical days.
VALID = pd.date_range(os.environ.get("VSTART", "2020-01-11T00"), os.environ.get("VEND", "2021-01-01T12"), freq="12h")


def build(lead):
    """Return arrays indexed [time, pixel] for valid times VALID."""
    init = VALID - pd.Timedelta(hours=lead)
    F = {}
    for m in MODELS:
        a = fc[m].sel(prediction_timedelta=np.timedelta64(lead, "h")).sel(time=init.values)
        F[m] = a.transpose("time", "latitude", "longitude").values.reshape(len(VALID), -1).astype(np.float64)
    y = era.sel(time=VALID.values).transpose("time", "latitude", "longitude").values.reshape(len(VALID), -1).astype(np.float64)
    doy = xr.DataArray(VALID.dayofyear.values, dims="t")
    hr = xr.DataArray(VALID.hour.values, dims="t")
    c = clim.sel(dayofyear=doy, hour=hr).transpose("t", "latitude", "longitude").values.reshape(len(VALID), -1).astype(np.float64)
    return F, y, c


def folds(gap):
    n = len(VALID)
    out = []
    for i in range(N_SPLITS):
        ts = n - (N_SPLITS - i) * TEST
        te = ts + TEST
        tr_end = ts - gap
        tr_start = max(0, tr_end - TRAIN)
        out.append((np.arange(tr_start, tr_end), np.arange(ts, te)))
    return out


def wls(Xm, yv, wv):
    sw = np.sqrt(wv)[:, None]
    coef, *_ = np.linalg.lstsq(Xm * sw, yv * sw[:, 0], rcond=None)
    return coef


def per_time_stats(pred, y, c):
    """Per-valid-time area-weighted stats. pred,y,c: [T, P]."""
    ws = w / w.sum()
    err = pred - y
    mse = (err ** 2 * ws).sum(1)
    bias = (err * ws).sum(1)
    fa, oa = pred - c, y - c
    # WB2-style ACC (uncentred anomalies, area-weighted)
    acc = (fa * oa * ws).sum(1) / np.sqrt((fa ** 2 * ws).sum(1) * (oa ** 2 * ws).sum(1))
    # activity: area-weighted std of anomaly field relative to truth
    act = np.sqrt((fa ** 2 * ws).sum(1)) / np.sqrt((oa ** 2 * ws).sum(1))
    return mse, bias, acc, act


def fit_xgb(X, yv, wv, params):
    m = xgb.XGBRegressor(random_state=42, n_jobs=12, tree_method="hist", **params)
    m.fit(X, yv, sample_weight=wv)
    return m


def run_lead(lead, gap_mode):
    F, y, c = build(lead)
    stack = np.stack([F[m] for m in MODELS], -1)  # T,P,4
    mmm = stack.mean(-1)
    gap = GAP0 if gap_mode == "gap5d" else GAP0 + lead // 24 * STEPS_PER_DAY
    T = len(VALID)
    preds = {k: np.full((T, NPIX), np.nan) for k in
             ["clim", "mmm", "lin", "lin_clim", "lin_pix", "xgb_orig", "xgb_resid", "xgb_nolatlon"]}
    for m in MODELS:
        preds[m] = F[m]
    preds["clim"] = c
    preds["mmm"] = mmm
    fold_id = np.full(T, -1)
    for k, (tr, te) in enumerate(folds(gap)):
        fold_id[te] = k
        wtr = np.tile(w, len(tr))
        # global linear stacking (area-weighted)
        Xtr = np.column_stack([stack[tr].reshape(-1, 4), np.ones(len(tr) * NPIX)])
        Xte = np.column_stack([stack[te].reshape(-1, 4), np.ones(len(te) * NPIX)])
        coef = wls(Xtr, y[tr].ravel(), wtr)
        preds["lin"][te] = (Xte @ coef).reshape(len(te), NPIX)
        # linear stacking with climatology as an extra regressor (allows damping)
        Xtr2 = np.column_stack([Xtr, c[tr].ravel()])
        Xte2 = np.column_stack([Xte, c[te].ravel()])
        coef2 = wls(Xtr2, y[tr].ravel(), wtr)
        preds["lin_clim"][te] = (Xte2 @ coef2).reshape(len(te), NPIX)
        # per-gridpoint linear stacking on anomalies (superensemble), ridge-regularised
        A = stack[tr] - c[tr][..., None]           # t,P,4
        b = y[tr] - c[tr]                           # t,P
        A1 = np.concatenate([A, np.ones(A.shape[:2] + (1,))], -1).transpose(1, 0, 2)  # P,t,5
        b1 = b.T                                                                          # P,t
        lam = 1e-3 * np.einsum("ptk,ptk->p", A1, A1)[:, None, None] / 5 * np.eye(5)[None]
        lam[:, 4, 4] = 0
        G = np.einsum("ptk,ptj->pkj", A1, A1) + lam
        r = np.einsum("ptk,pt->pk", A1, b1)
        beta = np.linalg.solve(G, r[..., None])[..., 0]                                   # P,5
        At = np.concatenate([stack[te] - c[te][..., None], np.ones((len(te), NPIX, 1))], -1)
        preds["lin_pix"][te] = c[te] + np.einsum("tpk,pk->tp", At, beta)
        # XGBoost variants
        def feats(idx, latlon=True):
            cols = [stack[idx, :, j].ravel() for j in range(4)]
            if latlon:
                cols += [np.tile(LON, len(idx)), np.tile(LAT, len(idx))]
            return np.column_stack(cols)
        Xa, Xb = feats(tr), feats(te)
        m = fit_xgb(Xa, y[tr].ravel(), wtr, {})
        preds["xgb_orig"][te] = m.predict(Xb).reshape(len(te), NPIX)
        Xa0, Xb0 = feats(tr, False), feats(te, False)
        m = fit_xgb(Xa0, y[tr].ravel(), wtr, {})
        preds["xgb_nolatlon"][te] = m.predict(Xb0).reshape(len(te), NPIX)
        # residual PiggyCast: learn correction to the multi-model mean, anomaly features
        def rfeats(idx):
            cols = [(stack[idx, :, j] - mmm[idx]).ravel() for j in range(4)]
            cols += [(mmm[idx] - c[idx]).ravel(), np.tile(LON, len(idx)), np.tile(LAT, len(idx))]
            return np.column_stack(cols)
        m = fit_xgb(rfeats(tr), (y[tr] - mmm[tr]).ravel(), wtr, {})
        preds["xgb_resid"][te] = mmm[te] + m.predict(rfeats(te)).reshape(len(te), NPIX)
    test = fold_id >= 0
    rows, series = [], {}
    for name, p in preds.items():
        mse, bias, acc, act = per_time_stats(p[test], y[test], c[test])
        series[name] = mse
        fid = fold_id[test]
        fold_rmse = [np.sqrt(mse[fid == k].mean()) for k in range(N_SPLITS)]
        rows.append(dict(lead=lead, gap=gap_mode, method=name,
                         rmse_foldmean=float(np.mean(fold_rmse)),
                         rmse_pooled=float(np.sqrt(mse.mean())),
                         rmse_timemean=float(np.sqrt(mse).mean()),
                         acc=float(acc.mean()), bias=float(bias.mean()), activity=float(act.mean()),
                         fold_rmse=json.dumps([round(v, 3) for v in fold_rmse])))
    np.savez_compressed(f"{OUT}/mse_series_{gap_mode}_{lead}.npz", times=VALID[test].values.astype("datetime64[s]").astype(str), **series)
    # spatial RMSE maps for the key methods (for figures)
    maps = {k: np.sqrt(((preds[k][test] - y[test]) ** 2).mean(0)).reshape(w2d.shape)
            for k in ["neuralgcm", "graphcast", "mmm", "lin_clim", "lin_pix", "xgb_orig", "xgb_resid"]}
    np.savez_compressed(f"{OUT}/rmse_maps_{gap_mode}_{lead}.npz", **maps)
    return rows


if __name__ == "__main__":
    allrows = []
    for gm in ["gap5d", "gapsafe"]:
        for L in LEADS:
            t0 = time.time()
            rows = run_lead(L, gm)
            allrows += rows
            d = {r["method"]: r["rmse_foldmean"] for r in rows}
            print(gm, L, f"{time.time()-t0:.0f}s", {k: round(v, 1) for k, v in d.items()}, flush=True)
            pd.DataFrame(allrows).to_csv(f"{OUT}/results.csv", index=False)
