"""PiggyCast-Lin (the best combiner) against each raw base model, days 1-10.

Writes res/lin_vs_base.csv (per-lead RMSE/ACC for the four models and PiggyCast-Lin) and
res/rmse_maps_lin_vs_base.npz (grid-point RMSE maps of all five at every lead), then draws
  ../figures/fig_lin_vs_base.pdf       skill against lead time
  ../figures/fig_lin_vs_base_maps.pdf  RMSE-ratio maps, PiggyCast-Lin / each model, days 1, 5, 10
Usage: python src/lin_vs_base.py <experiments dir> <figures dir>
"""
import os, sys
S, OUT = sys.argv[1], sys.argv[2]
sys.argv = ["exp.py", f"{S}/data", f"{S}/res"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import cartopy.crs as ccrs
import exp

R = f"{S}/res"
BASE = {"neuralgcm": ("NeuralGCM", "#3b3a37", "o"), "graphcast": ("GraphCast", "#6d6c68", "s"),
        "ifshres": ("IFS HRES", "#9a9993", "^"), "pangu": ("Pangu-Weather", "#bdbcb6", "D")}
LIN = ("PiggyCast-Lin", "#eb6834", "s")

# ---------------------------------------------------------------- compute
rows, maps = [], {}
for L in exp.LEADS:
    F, y, c = exp.build(L)
    stack = np.stack([F[m] for m in exp.MODELS], -1)
    lin = np.full_like(y, np.nan)
    fold = np.full(len(y), -1)
    for k, (tr, te) in enumerate(exp.folds(exp.GAP0 + L // 24 * exp.STEPS_PER_DAY)):
        X = np.column_stack([stack[tr].reshape(-1, 4), np.ones(len(tr) * exp.NPIX), c[tr].ravel()])
        coef = exp.wls(X, y[tr].ravel(), np.tile(exp.w, len(tr)))
        Xt = np.column_stack([stack[te].reshape(-1, 4), np.ones(len(te) * exp.NPIX), c[te].ravel()])
        lin[te] = (Xt @ coef).reshape(len(te), exp.NPIX)
        fold[te] = k
    test = fold >= 0
    preds = {**{m: F[m] for m in exp.MODELS}, "lin_clim": lin}
    for name, p in preds.items():
        mse, bias, acc, act = exp.per_time_stats(p[test], y[test], c[test])
        rmse = np.mean([np.sqrt(mse[fold[test] == k].mean()) for k in range(exp.N_SPLITS)])
        rows.append(dict(lead=L, method=name, rmse_foldmean=rmse, acc=acc.mean(), activity=act.mean()))
        maps[f"{name}_{L}"] = np.sqrt(((p[test] - y[test]) ** 2).mean(0)).reshape(exp.w2d.shape)
    print(L, flush=True)
df = pd.DataFrame(rows)
df.to_csv(f"{R}/lin_vs_base.csv", index=False)
np.savez_compressed(f"{R}/rmse_maps_lin_vs_base.npz", **maps)

# ---------------------------------------------------------------- figures
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#52514e", "axes.linewidth": 0.6, "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.5,
    "lines.linewidth": 1.4, "lines.markersize": 3.5, "savefig.bbox": "tight", "pdf.fonttype": 42,
})
DOUBLE = 39 / 6
days = np.array(exp.LEADS) / 24
rm = df.pivot(index="lead", columns="method", values="rmse_foldmean")
acc = df.pivot(index="lead", columns="method", values="acc")

fig, axs = plt.subplots(1, 3, figsize=(DOUBLE, 2.15))
for m, (lab, col, mk) in BASE.items():
    axs[0].plot(days, rm[m], color=col, marker=mk, lw=1.0, label=lab)
    axs[1].plot(days, 100 * (1 - rm["lin_clim"] / rm[m]), color=col, marker=mk, lw=1.0, label=lab)
    axs[2].plot(days, acc[m], color=col, marker=mk, lw=1.0, label=lab)
axs[0].plot(days, rm["lin_clim"], color=LIN[1], marker=LIN[2], lw=1.8, label=LIN[0])
axs[2].plot(days, acc["lin_clim"], color=LIN[1], marker=LIN[2], lw=1.8, label=LIN[0])
axs[0].set_ylabel("RMSE (m$^2$ s$^{-2}$)")
axs[1].set_ylabel("RMSE reduction by\nPiggyCast-Lin (%)")
axs[1].set_ylim(0, None)
axs[2].set_ylabel("Anomaly correlation (ACC)")
axs[2].axhline(0.6, color="#0b0b0b", lw=0.6, ls=":")
axs[2].text(1.2, 0.575, "0.6 (useful-skill threshold)", fontsize=6, color="#52514e")
for a, t in zip(axs, "abc"):
    a.set_xlabel("Lead time (days)"); a.set_xticks(np.arange(1, 11))
    a.set_title(f"({t})", loc="left", fontweight="bold")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.1))
fig.tight_layout(w_pad=1.2)
fig.savefig(f"{OUT}/fig_lin_vs_base.pdf")
plt.close(fig)

lat_e = np.linspace(-90, 90, 33); lon_e = np.append(np.arange(0, 360, 5.625), 360) - 5.625 / 2
wlat = exp.w2d
SHOW = [24, 120, 240]
fig, axs = plt.subplots(len(SHOW), 4, figsize=(DOUBLE, 3.5), subplot_kw=dict(projection=ccrs.Robinson()))
norm = TwoSlopeNorm(vmin=0.6, vcenter=1.0, vmax=1.4)
for i, L in enumerate(SHOW):
    for j, m in enumerate(BASE):
        ax = axs[i, j]
        r = maps[f"lin_clim_{L}"] / maps[f"{m}_{L}"]
        pc = ax.pcolormesh(lon_e, lat_e, r, cmap="RdBu_r", norm=norm, transform=ccrs.PlateCarree(), shading="flat", antialiased=False, linewidth=0, rasterized=True)
        ax.coastlines(lw=0.3, color="#3b3a37"); ax.set_global()
        better = 100 * (wlat * (r < 1)).sum() / wlat.sum()
        ax.text(0.5, -0.1, f"{better:.1f}% of area better", transform=ax.transAxes, ha="center", va="top", fontsize=6, color="#3b3a37")
        if i == 0:
            ax.set_title(f"÷ {BASE[m][0]}", fontsize=7.5, fontweight="bold")
        if j == 0:
            ax.text(-0.08, 0.5, f"Day {L // 24}", transform=ax.transAxes, rotation=90, ha="right", va="center", fontsize=7.5, fontweight="bold")
cb = fig.colorbar(pc, ax=axs, orientation="horizontal", fraction=0.035, pad=0.09, aspect=50, extend="both")
cb.set_label("RMSE ratio, PiggyCast-Lin ÷ base model (< 1: PiggyCast-Lin better)")
fig.savefig(f"{OUT}/fig_lin_vs_base_maps.pdf", dpi=300)
plt.close(fig)

summ = pd.DataFrame({m: 100 * (1 - rm["lin_clim"] / rm[m]) for m in BASE}).round(1)
summ.index = [f"day {d}" for d in (rm.index // 24)]
print("RMSE reduction by PiggyCast-Lin (%)\n", summ.to_string())
print("area better (%)", {f"{m}_{L}": round(float(100 * (wlat * (maps[f'lin_clim_{L}'] / maps[f'{m}_{L}'] < 1)).sum() / wlat.sum()), 1) for L in exp.LEADS for m in BASE})
