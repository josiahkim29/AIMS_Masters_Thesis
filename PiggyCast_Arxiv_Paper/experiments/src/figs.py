"""Paper figures for PiggyCast (static PDF, AMS two-column widths: 19pc single, 39pc double)."""
import sys, json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import cartopy.crs as ccrs

S, OUT = sys.argv[1], sys.argv[2]
R = f"{S}/res"
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#52514e", "axes.linewidth": 0.6,
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.5,
    "lines.linewidth": 1.4, "lines.markersize": 3.5, "savefig.bbox": "tight", "pdf.fonttype": 42,
})
SINGLE, DOUBLE = 19 / 6, 39 / 6  # inches (1pc = 1/6 in)
LEADS = np.arange(24, 241, 24)

# Fixed encodings: base models in graded grays with fixed markers; combiners in categorical slots 1-4.
BASE = {"neuralgcm": ("NeuralGCM", "#3b3a37", "o"), "graphcast": ("GraphCast", "#6d6c68", "s"),
        "ifshres": ("IFS HRES", "#9a9993", "^"), "pangu": ("Pangu-Weather", "#bdbcb6", "D")}
COMB = {"mmm": ("Multi-model mean", "#2a78d6", "o"), "lin_clim": ("PiggyCast-Lin", "#eb6834", "s"),
        "xgb_resid": ("PiggyCast-XGB-R", "#1baf7a", "^"), "xgb_orig": ("PiggyCast-XGB (thesis)", "#eda100", "D")}

res = pd.read_csv(f"{R}/results.csv")
safe = res[res.gap == "gapsafe"]
piv = lambda col: safe.pivot(index="lead", columns="method", values=col)

# ---------------- Figure: headline skill vs lead ---------------------------------------
rm, acc, act = piv("rmse_foldmean"), piv("acc"), piv("activity")
best = rm[list(BASE)].min(axis=1)
fig, axs = plt.subplots(1, 3, figsize=(DOUBLE, 2.15))
for k, (lab, col, mk) in BASE.items():
    axs[0].plot(LEADS, 100 * (rm[k] / best - 1), color=col, marker=mk, lw=1.0, label=lab)
    axs[1].plot(LEADS, acc[k], color=col, marker=mk, lw=1.0, label=lab)
    axs[2].plot(LEADS, act[k], color=col, marker=mk, lw=1.0, label=lab)
for k, (lab, col, mk) in COMB.items():
    axs[0].plot(LEADS, 100 * (rm[k] / best - 1), color=col, marker=mk, label=lab)
    axs[1].plot(LEADS, acc[k], color=col, marker=mk, label=lab)
    axs[2].plot(LEADS, act[k], color=col, marker=mk, label=lab)
axs[0].axhline(0, color="#0b0b0b", lw=0.6)
axs[0].set_ylabel("RMSE change vs. best\nsingle model (%)")
axs[0].set_ylim(-20, 15)
axs[0].text(30, 13.2, "\u2191 +39%", fontsize=6, color="#52514e")
axs[1].set_ylabel("Anomaly correlation (ACC)")
axs[1].set_ylim(0.5, 1.0)
axs[2].set_ylabel("Activity ratio (forecast/ERA5\nanomaly amplitude)")
axs[2].axhline(1, color="#0b0b0b", lw=0.6)
for a, t in zip(axs, "abc"):
    a.set_xlabel("Lead time (h)"); a.set_xticks(LEADS[::2])
    a.set_title(f"({t})", loc="left", fontweight="bold")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.12))
fig.tight_layout(w_pad=1.2)
fig.savefig(f"{OUT}/fig_skill_vs_lead.pdf")
plt.close(fig)

# ---------------- Figure: error structure (correlation + MDS) --------------------------
names = json.load(open(f"{R}/pairwise_names.json"))
D = np.load(f"{R}/pairwise_rmse.npy")
X = np.load(f"{R}/mds_coords.npy")
iu = np.triu_indices_from(D, 1)
dh = np.sqrt(((X[:, None] - X[None]) ** 2).sum(-1))
stress1 = np.sqrt(((D[iu] - dh[iu]) ** 2).sum() / (D[iu] ** 2).sum())
X = X - X[names.index("era5")]
# orient so that the trajectories leave ERA5 towards +x
th = np.arctan2(*X[names.index("neuralgcm_240")][::-1])
Rm = np.array([[np.cos(-th), -np.sin(-th)], [np.sin(-th), np.cos(-th)]])
X = X @ Rm.T
fig = plt.figure(figsize=(DOUBLE, 2.2))
gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.2], wspace=0.55)
order = ["neuralgcm", "graphcast", "ifshres", "pangu"]
labs = [BASE[m][0].replace("-Weather", "") for m in order]
for j, L in enumerate([72, 240]):
    ax = fig.add_subplot(gs[0, j])
    C = np.load(f"{R}/errcorr_{L}.npy")  # order: neuralgcm, graphcast, ifshres, pangu
    Cm = np.where(np.eye(4, dtype=bool), np.nan, C)
    im = ax.imshow(Cm, cmap="Blues", vmin=0, vmax=1)
    for a in range(4):
        for b in range(4):
            if a != b:
                ax.text(b, a, f"{C[a, b]:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if C[a, b] > 0.6 else "#0b0b0b")
    ax.set_xticks(range(4)); ax.set_yticks(range(4))
    ax.set_xticklabels(labs, rotation=45, ha="right"); ax.set_yticklabels(labs if j == 0 else [])
    ax.grid(False)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title(f"({'ab'[j]}) Error corr., {L} h", loc="left", fontweight="bold")
ax = fig.add_subplot(gs[0, 2])
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import squareform
sel = [names.index(f"{m}_72") for m in order] + [names.index("era5")]
D72 = D[np.ix_(sel, sel)]
Z = linkage(squareform(D72, checks=False), method="average")
dendrogram(Z, labels=labs + ["ERA5"], ax=ax, color_threshold=0, above_threshold_color="#3b3a37", leaf_font_size=7, leaf_rotation=45)
ax.set_ylabel("UPGMA distance (m$^2$ s$^{-2}$)")
ax.grid(False); ax.spines["bottom"].set_visible(False)
ax.set_title("(c) Hierarchical clustering, 72 h", loc="left", fontweight="bold")
fig.savefig(f"{OUT}/fig_error_structure.pdf")
plt.close(fig)
print("MDS stress-1", round(stress1, 3))

# ---------------- Figure: what the stack learns (weights + SHAP) -----------------------
co = pd.read_csv(f"{R}/lin_clim_coefs.csv").groupby("lead").agg(["mean", "std"])
sh = pd.read_csv(f"{R}/shap_xgb_orig.csv").groupby("lead").mean()
fig, axs = plt.subplots(1, 2, figsize=(DOUBLE * 0.8, 2.1))
for m in order:
    lab, col, mk = BASE[m]
    axs[0].errorbar(LEADS, co[(m, "mean")], yerr=co[(m, "std")], color=col, marker=mk, lw=1.0, capsize=1.5, label=lab)
    axs[1].plot(LEADS, sh[m], color=col, marker=mk, lw=1.0, label=lab)
axs[0].errorbar(LEADS, co[("clim", "mean")], yerr=co[("clim", "std")], color="#e34948", marker="x", lw=1.4, ls="--", capsize=1.5, label="Climatology")
axs[1].plot(LEADS, sh["latitude"], color="#e34948", marker="x", ls="--", label="Latitude")
axs[1].plot(LEADS, sh["longitude"], color="#e34948", marker="+", ls=":", label="Longitude")
axs[0].axhline(0, color="#0b0b0b", lw=0.6)
axs[0].set_ylabel("Regression weight"); axs[1].set_ylabel("Mean |SHAP| (m$^2$ s$^{-2}$)")
axs[0].set_title("(a) PiggyCast-Lin weights", loc="left", fontweight="bold")
axs[1].set_title("(b) PiggyCast-XGB feature attribution", loc="left", fontweight="bold")
for a in axs: a.set_xlabel("Lead time (h)"); a.set_xticks(LEADS[::2])
h0, l0 = axs[0].get_legend_handles_labels(); h1, l1 = axs[1].get_legend_handles_labels()
fig.tight_layout()
fig.legend(h0 + h1[-2:], l0 + l1[-2:], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.16))
fig.savefig(f"{OUT}/fig_weights_shap.pdf")
plt.close(fig)

# ---------------- Figure: maps of RMSE ratios ---------------------------------------
lat = np.linspace(-87.1875, 87.1875, 32); lon = np.arange(0, 360, 5.625)
lon_e = np.append(lon, 360) - 5.625 / 2; lat_e = np.linspace(-90, 90, 33)
panels = [(72, "lin_clim", "neuralgcm", "Lin \u00f7 NeuralGCM, 72 h"),
          (240, "lin_clim", "neuralgcm", "Lin \u00f7 NeuralGCM, 240 h"),
          (240, "xgb_orig", "mmm", "XGB (thesis) \u00f7 MMM, 240 h")]
# lin_clim maps are not stored; recompute from stored ones where available
fig, axs = plt.subplots(1, 3, figsize=(DOUBLE, 1.65), subplot_kw=dict(projection=ccrs.Robinson(central_longitude=0)))
norm = TwoSlopeNorm(vmin=0.6, vcenter=1.0, vmax=1.4)
for ax, (L, a, b, title), t in zip(axs, panels, "abc"):
    mp = np.load(f"{R}/rmse_maps_gapsafe_{L}.npz")
    num = mp[a] if a in mp else mp["lin_pix"]
    ratio = num / mp[b]
    pc = ax.pcolormesh(lon_e, lat_e, ratio, cmap="RdBu_r", norm=norm, transform=ccrs.PlateCarree(), shading="flat")
    ax.coastlines(lw=0.3, color="#3b3a37")
    ax.set_global()
    ax.set_title(f"({t}) {title}", fontsize=7, loc="left", fontweight="bold")
cb = fig.colorbar(pc, ax=axs, orientation="horizontal", fraction=0.06, pad=0.06, aspect=50, extend="both")
cb.set_label("RMSE ratio (< 1: numerator better)")
fig.savefig(f"{OUT}/fig_maps.pdf")
plt.close(fig)

# ---------------- Figure: training-length sensitivity ---------------------------------
tl = pd.read_csv(f"{R}/trainlen.csv")
fig, axs = plt.subplots(1, 3, figsize=(DOUBLE, 1.9))
for ax, L, t in zip(axs, [48, 120, 240], "abc"):
    d = tl[tl.lead == L]
    ref = d[d.method == "mmm"].rmse_foldmean.iloc[0]
    for k in ["lin_clim", "xgb_resid", "xgb_orig"]:
        lab, col, mk = COMB[k]
        e = d[d.method == k].sort_values("train_days")
        ax.plot(e.train_days, 100 * (e.rmse_foldmean / ref - 1), color=col, marker=mk, label=lab)
    e = d[d.method == "lin_pix"].sort_values("train_days")
    ax.plot(e.train_days, 100 * (e.rmse_foldmean / ref - 1), color="#6250d6", marker="v", label="Per-grid-point linear")
    ax.axhline(0, color="#2a78d6", lw=1.0, ls="--", label="Multi-model mean")
    ax.set_xscale("log"); ax.set_xticks([15, 30, 60, 120]); ax.set_xticklabels(["15", "30", "60", "120"])
    ax.minorticks_off()
    ax.set_xlabel("Training window (days)"); ax.set_title(f"({t}) {L} h", loc="left", fontweight="bold")
axs[0].set_ylabel("RMSE change vs.\nmulti-model mean (%)")
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.1))
fig.tight_layout()
fig.savefig(f"{OUT}/fig_trainlen.pdf")
plt.close(fig)
print("done")
