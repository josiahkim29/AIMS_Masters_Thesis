"""Figure for the multi-year side experiment (res/multiyear_A.csv, res/multiyear_B.csv).

  ../figures/fig_multiyear.pdf
    (a,b) Experiment A, RMSE relative to the multi-model mean against training length, 24 h and 240 h
    (c)   Experiment B, RMSE relative to PiggyCast-Lin by lead, 60-day vs multi-year training
Usage: python src/multiyear_fig.py <experiments dir> <figures dir>
"""
import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

S, OUT = sys.argv[1], sys.argv[2]
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 6.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#52514e", "axes.linewidth": 0.6, "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.5,
    "lines.linewidth": 1.4, "lines.markersize": 3.5, "savefig.bbox": "tight", "pdf.fonttype": 42,
})
COMB = {"lin_clim": ("PiggyCast-Lin", "#eb6834", "s"), "xgb_resid": ("PiggyCast-XGB-R", "#1baf7a", "^"),
        "xgb_orig": ("PiggyCast-XGB", "#eda100", "D")}
A = pd.read_csv(f"{S}/res/multiyear_A.csv")
B = pd.read_csv(f"{S}/res/multiyear_B.csv")

fig, axs = plt.subplots(1, 3, figsize=(39 / 6, 2.2))
for ax, L in zip(axs[:2], [24, 240]):
    d = A[A.lead == L]
    ref = d[d.method == "mmm"].rmse_foldmean.iloc[0]
    for m, (lab, col, mk) in COMB.items():
        e = d[d.method == m].assign(train=lambda x: x.train.astype(int)).sort_values("train")
        ax.plot(e.train, 100 * (e.rmse_foldmean / ref - 1), color=col, marker=mk, label=lab)
    big = d[d.method == "xgb_big"].rmse_foldmean.iloc[0]
    ax.plot([700], [100 * (big / ref - 1)], ls="none", marker="D", mfc="none", mec="#9a6a00", ms=6, label="PiggyCast-XGB, 500 deeper trees")
    best = d[d.method.isin(["ifshres", "pangu_hres"])].rmse_foldmean.min()
    ax.axhline(100 * (best / ref - 1), color="#6d6c68", lw=0.8, ls="-.", label="Best single model")
    ax.axhline(0, color="#2a78d6", lw=0.9, ls="--", label="Multi-model mean")
    ax.set_xscale("log"); ax.set_xticks([15, 30, 60, 120, 365, 700]); ax.set_xticklabels(["15", "30", "60", "120", "365", "700"])
    ax.minorticks_off()
    ax.set_xlabel("Training window (days)")
    ax.set_title(f"({'ab'[L == 240]}) Two models, {L} h", loc="left", fontweight="bold")
axs[0].set_ylabel("RMSE relative to MMM (%)")
for m in ["xgb_orig", "xgb_resid"]:
    lab, col, mk = COMB[m]
    for T, ls in [("60d", ":"), ("prior+60d", "-")]:
        e = B[(B.method == m) & (B.train == T)].set_index("lead").rmse_foldmean
        r = B[(B.method == "lin_clim") & (B.train == T)].set_index("lead").rmse_foldmean
        axs[2].plot(e.index / 24, 100 * (e / r - 1), color=col, marker=mk, ls=ls, mfc=col if ls == "-" else "white")
axs[2].axhline(0, color=COMB["lin_clim"][1], lw=0.9)
axs[2].set_xlabel("Lead time (days)"); axs[2].set_xticks([1, 3, 5, 7, 10])
axs[2].set_ylabel("RMSE relative to PiggyCast-Lin (%)")
axs[2].set_yscale("symlog", linthresh=10); axs[2].set_yticks([-5, 0, 5, 10, 20, 40]); axs[2].set_yticklabels(["−5", "0", "5", "10", "20", "40"])
axs[2].minorticks_off()
axs[2].set_title("(c) Three models, 2022", loc="left", fontweight="bold")
axs[2].plot([], [], color="#52514e", ls=":", label="60-day training")
axs[2].plot([], [], color="#52514e", ls="-", label="2 yr + 60 days")
axs[2].legend(loc="upper right", frameon=False, bbox_to_anchor=(1.02, 1.0), handlelength=1.6)
h, l = axs[1].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 1.1))
fig.tight_layout(w_pad=1.0)
fig.savefig(f"{OUT}/fig_multiyear.pdf")
