"""Case-study maps: one 240-h forecast of Z500 anomalies from ERA5, NeuralGCM, the multi-model
mean and PiggyCast-Lin (leakage-safe fold), Northern Hemisphere polar stereographic."""
import os, sys
S, OUT = sys.argv[1], sys.argv[2]
sys.argv = ["exp.py", f"{S}/data", f"{S}/res"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.util import add_cyclic_point
import exp

plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.titlesize": 8, "pdf.fonttype": 42})
LEAD = int(os.environ.get("LEAD", 240))
F, y, c = exp.build(LEAD)
stack = np.stack([F[m] for m in exp.MODELS], -1)
mmm = stack.mean(-1)
gap = exp.GAP0 + LEAD // 24 * exp.STEPS_PER_DAY
lin = np.full_like(y, np.nan)
for tr, te in exp.folds(gap):
    X = np.column_stack([stack[tr].reshape(-1, 4), np.ones(len(tr) * exp.NPIX), c[tr].ravel()])
    coef = exp.wls(X, y[tr].ravel(), np.tile(exp.w, len(tr)))
    Xt = np.column_stack([stack[te].reshape(-1, 4), np.ones(len(te) * exp.NPIX), c[te].ravel()])
    lin[te] = (Xt @ coef).reshape(len(te), exp.NPIX)
test = ~np.isnan(lin[:, 0])
# pick the test case with the largest Northern-Hemisphere extratropical ERA5 anomaly in Nov-Dec
lat2 = exp.LAT; wnh = exp.w * (lat2 > 30)
anom = y - c
score = np.sqrt((anom ** 2 * wnh).sum(1) / wnh.sum())
months = exp.VALID.month.values
cand = np.where(test & np.isin(months, [11, 12]))[0]
t = int(os.environ.get("TIDX", cand[np.argmax(score[cand])]))
when = exp.VALID[t]
print("case", when, "init", when - pd.Timedelta(hours=LEAD))

def rmse_nh(p):
    return np.sqrt((((p - y[t]) ** 2) * wnh).sum() / wnh.sum())

fields = [("ERA5 (truth)", y[t]), ("NeuralGCM", F["neuralgcm"][t]), ("Multi-model mean", mmm[t]), ("PiggyCast-Lin", lin[t])]
lon = np.arange(0, 360, 5.625); lat = exp.lat
proj = ccrs.NorthPolarStereo(central_longitude=0)
fig, axs = plt.subplots(1, 4, figsize=(39 / 6, 2.15), subplot_kw=dict(projection=proj))
lev = np.arange(-2400, 2401, 300)
for ax, (name, f) in zip(axs, fields):
    a = (f - c[t]).reshape(len(lat), len(lon))
    full = f.reshape(len(lat), len(lon))
    ac, lonc = add_cyclic_point(a, coord=lon)
    fc_, _ = add_cyclic_point(full, coord=lon)
    ax.set_extent([-180, 180, 25, 90], ccrs.PlateCarree())
    cf = ax.contourf(lonc, lat, ac, levels=lev, cmap="RdBu_r", extend="both", transform=ccrs.PlateCarree())
    ax.contour(lonc, lat, fc_, levels=np.arange(48000, 60001, 1000), colors="#2b2b2b", linewidths=0.4, transform=ccrs.PlateCarree())
    ax.coastlines(lw=0.3, color="#52514e")
    sub = "" if name.startswith("ERA5") else f"\nNH RMSE {rmse_nh(f):.0f} m$^2$ s$^{{-2}}$"
    ax.set_title(name + sub, fontsize=7)
cb = fig.colorbar(cf, ax=axs, orientation="horizontal", fraction=0.06, pad=0.04, aspect=50)
cb.set_label("Z500 anomaly from 1990–2019 climatology (m$^2$ s$^{-2}$); contours: Z500 every 1000 m$^2$ s$^{-2}$")
fig.suptitle(f"{LEAD}-h forecasts valid {when:%H} UTC {when:%-d %b %Y}", y=1.04, fontsize=8)
fig.savefig(f"{OUT}/fig_case_study.pdf", bbox_inches="tight")
with open(f"{S}/res/case_study.txt", "w") as fh:
    fh.write(f"{when} init {when - pd.Timedelta(hours=LEAD)}\n")
    for name, f in fields[1:]:
        fh.write(f"{name}: NH RMSE {rmse_nh(f):.1f}, anomaly rms {np.sqrt((((f - c[t]) ** 2) * wnh).sum() / wnh.sum()):.1f}\n")
    fh.write(f"ERA5 anomaly rms {score[t]:.1f}\n")
print(open(f"{S}/res/case_study.txt").read())
