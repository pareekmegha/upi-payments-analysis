import itertools
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import grangercausalitytests

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
m = pd.read_csv(r".\data\master_monthly.csv", parse_dates=["month"]).set_index("month")
CH = r".\charts"

d = pd.DataFrame(index=m.index)
d["vol_growth"] = np.log(m["vol_per_day"]).diff()
d["val_growth"] = np.log(m["val_cr"] / m["days_in_month"]).diff()
d["banks_growth"] = np.log(m["banks_live"]).diff()
d["p2m_share_chg"] = m["p2m_vol_share"].diff() * 100            # percentage points
d["top2_share_chg"] = m["top2_share"].diff() * 100
d["hhi_chg"] = m["hhi"].diff()
d["tpap_share_chg"] = m["tpap_vol_share"].diff() * 100
d["brands_chg"] = m["n_brands"].diff()
# ticket growth is val_growth - vol_growth by identity, so it is excluded from the pairwise matrix on purpose
d["ticket_growth"] = np.log(m["avg_ticket"]).diff()

vars_ = [c for c in d.columns if c != "ticket_growth"]
rows = []
for a, b in itertools.combinations(vars_, 2):
    x = d[[a, b]].dropna()
    if len(x) < 24:
        continue
    r, p = stats.spearmanr(x[a], x[b])
    rows.append({"a": a, "b": b, "n": len(x), "spearman": r, "p": p})
res = pd.DataFrame(rows)
res["p_fdr"] = multipletests(res["p"], method="fdr_bh")[1]
res["significant_fdr05"] = res["p_fdr"] < .05
res = res.sort_values("spearman", key=abs, ascending=False)
res.round(4).to_csv(r".\data\corr_growth_pairs.csv", index=False)
print(f"GROWTH-RATE CORRELATIONS (Spearman, {len(res)} pairs, BH-FDR corrected)\n")
print(res.head(12).round(3).to_string(index=False))
print("\nsignificant after FDR:", int(res.significant_fdr05.sum()), "of", len(res))

# heatmap
M = pd.DataFrame(np.nan, index=vars_, columns=vars_)
for _, r in res.iterrows():
    M.loc[r.a, r.b] = M.loc[r.b, r.a] = r.spearman
np.fill_diagonal(M.values, 1)
fig, ax = plt.subplots(figsize=(7.2, 6))
im = ax.imshow(M.values.astype(float), cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(vars_))); ax.set_xticklabels(vars_, rotation=45, ha="right"); ax.set_yticks(range(len(vars_))); ax.set_yticklabels(vars_)
for i in range(len(vars_)):
    for j in range(len(vars_)):
        v = M.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7)
ax.set_title("Spearman correlation of monthly changes"); fig.colorbar(im, shrink=.8)
fig.tight_layout(); fig.savefig(rf"{CH}\09_corr_heatmap.png"); plt.close(fig)

# ---------- why levels mislead ----------
pairs = [("vol_mn", "val_cr"), ("banks_live", "vol_mn"), ("p2m_vol_share", "avg_ticket"), ("hhi", "vol_mn"), ("top2_share", "vol_mn")]
lev = []
for a, b in pairs:
    x = m[[a, b]].dropna()
    ga, gb = {"vol_mn": "vol_growth", "val_cr": "val_growth", "banks_live": "banks_growth", "p2m_vol_share": "p2m_share_chg",
              "avg_ticket": "ticket_growth", "hhi": "hhi_chg", "top2_share": "top2_share_chg"}[a], \
             {"vol_mn": "vol_growth", "val_cr": "val_growth", "banks_live": "banks_growth", "p2m_vol_share": "p2m_share_chg",
              "avg_ticket": "ticket_growth", "hhi": "hhi_chg", "top2_share": "top2_share_chg"}[b]
    y = d[[ga, gb]].dropna()
    lev.append({"pair": f"{a} vs {b}", "levels_pearson": stats.pearsonr(x[a], x[b])[0], "changes_spearman": stats.spearmanr(y[ga], y[gb])[0]})
lev = pd.DataFrame(lev)
print("\nLEVELS vs CHANGES (levels are inflated by the shared trend)\n", lev.round(3).to_string(index=False))
lev.round(3).to_csv(r".\data\corr_levels_vs_changes.csv", index=False)

# ---------- lead/lag ----------
def xcorr(x, y, maxlag=6):
    out = []
    for k in range(-maxlag, maxlag + 1):
        z = pd.concat([x, y.shift(-k)], axis=1).dropna()       # k>0: x leads y by k months
        out.append((k, stats.spearmanr(z.iloc[:, 0], z.iloc[:, 1])[0], len(z)))
    return pd.DataFrame(out, columns=["lag_x_leads", "spearman", "n"])

for a, b, label in [("p2m_share_chg", "ticket_growth", "P2M share change -> ticket growth"),
                    ("banks_growth", "vol_growth", "banks live growth -> volume growth"),
                    ("tpap_share_chg", "vol_growth", "TPAP share change -> volume growth")]:
    xc = xcorr(d[a], d[b])
    band = 2 / np.sqrt(xc["n"].min())
    top = xc.loc[xc.spearman.abs().idxmax()]
    print(f"\nLEAD/LAG: {label} | strongest at lag {int(top.lag_x_leads)} (r={top.spearman:.2f}) | ~95% noise band +-{band:.2f}")
    print("  ", {int(r.lag_x_leads): round(r.spearman, 2) for r in xc.itertuples()})

# ---------- Granger (low power: ~75 points, report as suggestive only) ----------
print("\nGRANGER (suggestive only, ~75 obs) -- min p over lags 1-3")
for cause, effect in [("p2m_share_chg", "ticket_growth"), ("ticket_growth", "p2m_share_chg"), ("banks_growth", "vol_growth"), ("vol_growth", "banks_growth")]:
    z = d[[effect, cause]].dropna()
    g = grangercausalitytests(z, maxlag=3, verbose=False)
    ps = {k: round(g[k][0]["ssr_ftest"][1], 3) for k in g}
    print(f"  {cause} -> {effect}: p by lag {ps}")
