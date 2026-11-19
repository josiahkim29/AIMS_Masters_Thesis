"""More-data side experiment: does the XGBoost stack catch up with years of training data?

Experiment A (two models, three contiguous years, same sources as the paper):
  IFS HRES + Pangu-Weather (HRES-initialised), valid times 2020-01-11 .. 2022-12-31.
  Test: the 12 calendar months of 2022 (one fold each). Training: the N days that end
  (5 days + lead) before the test month starts, N in TRAIN_DAYS (15 .. 700 days).
Experiment B (three models, ERA5-initialised Pangu and GraphCast, non-contiguous years):
  IFS HRES + Pangu (ERA5-init) + GraphCast v2 (ERA5-init); data in 2018, 2020 and 2022.
  Test: Mar..Dec 2022 (10 monthly folds). Training sets: "60d" (paper protocol),
  "prior" (all of 2018 and 2020, fixed), "prior+60d" (prior years plus the 60-day window).

Writes res/multiyear_A.csv and res/multiyear_B.csv (one row per lead x training set x method,
with fold-mean RMSE, ACC, activity and per-fold RMSEs).
Usage: python src/multiyear.py <experiments dir> A|B [leads]
"""
import os, sys, json, time, warnings
import numpy as np, pandas as pd, xarray as xr, xgboost as xgb

warnings.filterwarnings("ignore")
S, EXP = sys.argv[1], sys.argv[2]
LEADS = [int(a) for a in sys.argv[3].split(",")] if len(sys.argv) > 3 else [24, 72, 120, 168, 240]
D = 2  # steps per day

fc = xr.open_dataset(f"{S}/data/multiyear_z500.nc")
era = xr.open_dataset(f"{S}/data/era5_z500_multiyear.nc")["era5"]
clim = xr.open_dataset(f"{S}/data/clim_z500.nc")["clim"]
lat = fc.latitude.values
w2d = np.broadcast_to(np.cos(np.deg2rad(lat))[:, None], (len(lat), len(fc.longitude))).astype(np.float64)
w = w2d.ravel()
ws = w / w.sum()
LON, LAT = [a.ravel() for a in np.meshgrid(fc.longitude.values, lat)]
NPIX = w.size

if EXP == "A":
    MODELS = ["ifshres", "pangu_hres"]
    VALID = pd.date_range("2020-01-11T00", "2022-12-31T12", freq="12h")
    TEST_MONTHS = list(range(1, 13))
    TRAIN_SETS = [15, 30, 60, 120, 240, 365, 700]
else:
    MODELS = ["ifshres", "pangu_era5", "gc_era5"]
    VALID = pd.date_range("2018-01-11T00", "2022-12-31T12", freq="12h")
    TEST_MONTHS = list(range(3, 13))
    TRAIN_SETS = ["60d", "prior", "prior+60d"]
BIG = dict(n_estimators=500, max_depth=8, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8)


def build(lead):
    init = VALID - pd.Timedelta(hours=lead)
    F = []
    for m in MODELS:
        a = fc[m].sel(prediction_timedelta=np.timedelta64(lead, "h")).reindex(time=init.values)
        F.append(a.transpose("time", "latitude", "longitude").values.reshape(len(VALID), -1).astype(np.float64))
    stack = np.stack(F, -1)
    y = era.sel(time=VALID.values).transpose("time", "latitude", "longitude").values.reshape(len(VALID), -1).astype(np.float64)
    doy = xr.DataArray(VALID.dayofyear.values, dims="t")
    hr = xr.DataArray(VALID.hour.values, dims="t")
    c = clim.sel(dayofyear=doy, hour=hr).transpose("t", "latitude", "longitude").values.reshape(len(VALID), -1).astype(np.float64)
    ok = np.isfinite(stack).all((1, 2))
    return stack, y, c, ok


def wls(X, yv, wv):
    sw = np.sqrt(wv)[:, None]
    return np.linalg.lstsq(X * sw, yv * sw[:, 0], rcond=None)[0]


def xgbfit(X, yv, wv, params):
    m = xgb.XGBRegressor(random_state=42, n_jobs=12, tree_method="hist", **params)
    return m.fit(X, yv, sample_weight=wv)


def stats(p, y, c):
    err = p - y
    mse = (err ** 2 * ws).sum(1)
    fa, oa = p - c, y - c
    acc = (fa * oa * ws).sum(1) / np.sqrt((fa ** 2 * ws).sum(1) * (oa ** 2 * ws).sum(1))
    act = np.sqrt((fa ** 2 * ws).sum(1) / (oa ** 2 * ws).sum(1))
    return mse, acc, act


def fit_predict(stack, y, c, tr, te, big):
    M = stack.shape[-1]
    mmm = stack.mean(-1)
    wtr = np.tile(w, len(tr))
    out = {m: stack[te, :, j] for j, m in enumerate(MODELS)}
    out["mmm"] = mmm[te]
    X = lambda idx: np.column_stack([stack[idx].reshape(-1, M), np.ones(len(idx) * NPIX), c[idx].ravel()])
    coef = wls(X(tr), y[tr].ravel(), wtr)
    out["lin_clim"] = (X(te) @ coef).reshape(len(te), NPIX)
    fx = lambda idx: np.column_stack([stack[idx].reshape(-1, M), np.tile(LON, len(idx)), np.tile(LAT, len(idx))])
    Xa, Xb = fx(tr), fx(te)
    out["xgb_orig"] = xgbfit(Xa, y[tr].ravel(), wtr, {}).predict(Xb).reshape(len(te), NPIX)
    if big:
        out["xgb_big"] = xgbfit(Xa, y[tr].ravel(), wtr, BIG).predict(Xb).reshape(len(te), NPIX)
    rx = lambda idx: np.column_stack([(stack[idx] - mmm[idx][..., None]).reshape(-1, M), (mmm[idx] - c[idx]).ravel(),
                                      np.tile(LON, len(idx)), np.tile(LAT, len(idx))])
    out["xgb_resid"] = mmm[te] + xgbfit(rx(tr), (y[tr] - mmm[tr]).ravel(), wtr, {}).predict(rx(te)).reshape(len(te), NPIX)
    return out


if __name__ == "__main__":
    rows = []
    for L in LEADS:
        stack, y, c, ok = build(L)
        gap = pd.Timedelta(days=5 + L // 24)
        res = {}  # (train_set, method) -> list of per-fold (mse array, acc, act)
        t0 = time.time()
        for mo in TEST_MONTHS:
            ts = pd.Timestamp(2022, mo, 1)
            te = np.where((VALID >= ts) & (VALID < ts + pd.offsets.MonthBegin(1)) & ok)[0]
            tr_end = ts - gap
            for T in TRAIN_SETS:
                if EXP == "A":
                    sel = (VALID < tr_end) & (VALID >= tr_end - pd.Timedelta(days=T))
                else:
                    recent = (VALID < tr_end) & (VALID >= tr_end - pd.Timedelta(days=60))
                    prior = np.isin(VALID.year, [2018, 2020]) & (VALID < "2021-01-01")
                    sel = {"60d": recent, "prior": prior, "prior+60d": recent | prior}[T]
                tr = np.where(sel & ok)[0]
                big = (EXP == "A" and T == max(TRAIN_SETS)) or (EXP == "B" and T == "prior+60d")
                for name, p in fit_predict(stack, y, c, tr, te, big).items():
                    res.setdefault((T, name), []).append((stats(p, y[te], c[te]), len(tr)))
            print(EXP, L, mo, f"{time.time() - t0:.0f}s", flush=True)
        for (T, name), folds in res.items():
            fr = [float(np.sqrt(s[0].mean())) for s, _ in folds]
            rows.append(dict(lead=L, train=T, method=name, rmse_foldmean=float(np.mean(fr)),
                             acc=float(np.mean(np.concatenate([s[1] for s, _ in folds]))),
                             activity=float(np.mean(np.concatenate([s[2] for s, _ in folds]))),
                             n_train_days=float(np.mean([n for _, n in folds])) / D,
                             fold_rmse=json.dumps([round(v, 3) for v in fr])))
        pd.DataFrame(rows).to_csv(f"{S}/res/multiyear_{EXP}.csv", index=False)
    print("done")
