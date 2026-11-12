import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "font.size": 9})
m = pd.read_csv(r".\data\master_monthly.csv", parse_dates=["month"])
apps = pd.read_csv(r"..\cleaning\apps_clean.csv", parse_dates=["month"])
apps["vol_mn"] = apps["vol_settled_mn"]   # headline-consistent volume (excludes on-us); see clean_apps.py
CH = r".\charts"

# ---------- summary stats ----------
cols = ["banks_live", "vol_mn", "val_cr", "avg_ticket", "p2m_vol_share", "p2m_val_share", "top2_share", "hhi", "tpap_vol_share", "n_brands"]
s = m[cols].describe().T
s["cv"] = s["std"] / s["mean"]
s["skew"] = m[cols].skew()
s.round(3).to_csv(r".\data\eda_summary.csv")
print("SUMMARY\n", s[["count", "min", "mean", "max", "cv", "skew"]].round(3).to_string())

first, last = m.iloc[0], m.iloc[-1]
print(f"\nvolume {first.vol_mn:,.0f} -> {last.vol_mn:,.0f} mn ({last.vol_mn / first.vol_mn:.1f}x) | "
      f"value {first.val_cr:,.0f} -> {last.val_cr:,.0f} cr ({last.val_cr / first.val_cr:.1f}x)")
print(f"avg ticket Rs {first.avg_ticket:,.0f} -> {last.avg_ticket:,.0f} | peak Rs {m.avg_ticket.max():,.0f} on {m.loc[m.avg_ticket.idxmax(), 'month']:%Y-%m}")

fy = m.groupby("fy").agg(months=("month", "size"), vol_mn=("vol_mn", "sum"), val_cr=("val_cr", "sum"), banks_live_end=("banks_live", "last"))
fy["vol_growth"] = fy["vol_mn"].pct_change()
fy["val_growth"] = fy["val_cr"].pct_change()
part = fy.index[-1]
n = int(fy.loc[part, "months"])
if n < 12:
    # partial year: compare the same n months of the prior FY, otherwise growth is meaningless
    prev = m[m["fy"] == fy.index[-2]].head(n)
    fy.loc[part, "vol_growth"] = fy.loc[part, "vol_mn"] / prev["vol_mn"].sum() - 1
    fy.loc[part, "val_growth"] = fy.loc[part, "val_cr"] / prev["val_cr"].sum() - 1
print("\nFISCAL YEARS (FY26-27 is partial)\n", fy.round(3).to_string())
fy.to_csv(r".\data\eda_fiscal_years.csv")

# ---------- charts ----------
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
ax[0].plot(m.month, m.vol_mn / 1000, color="#1f77b4"); ax[0].set_title("Monthly volume (billion txns)")
ax[1].plot(m.month, m.val_cr / 1e5, color="#d62728"); ax[1].set_title("Monthly value (Rs lakh crore)")
fig.tight_layout(); fig.savefig(rf"{CH}\01_volume_value.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
ax[0].plot(m.month, m.avg_ticket, color="#2ca02c"); ax[0].set_title("Average ticket size (Rs)")
ax[1].plot(m.month, m.p2m_vol_share * 100, label="volume", color="#9467bd")
ax[1].plot(m.month, m.p2m_val_share * 100, label="value", color="#ff7f0e")
ax[1].set_title("P2M share of UPI (%)"); ax[1].legend()
fig.tight_layout(); fig.savefig(rf"{CH}\02_ticket_p2m_share.png"); plt.close(fig)

# brand shares
named = apps.groupby(["month", "brand"])["vol_mn"].sum().reset_index()
tot = apps.groupby("month")["vol_mn"].sum().rename("tot")
named = named.merge(tot, on="month"); named["share"] = named["vol_mn"] / named["tot"]
topb = named.groupby("brand")["vol_mn"].sum().nlargest(6).index.tolist()
pv = named[named["brand"].isin(topb)].pivot(index="month", columns="brand", values="share")[topb].fillna(0)
pv["All other"] = 1 - pv.sum(axis=1)
fig, ax = plt.subplots(figsize=(10, 4.2))
ax.stackplot(pv.index, (pv * 100).T.values, labels=pv.columns, alpha=.9)
ax.set_title("Share of app volume by brand (%)"); ax.legend(loc="upper center", bbox_to_anchor=(.5, -.08), ncol=7, fontsize=8, frameon=False); ax.set_ylim(0, 100)
fig.tight_layout(); fig.savefig(rf"{CH}\03_brand_share.png"); plt.close(fig)

a = m.dropna(subset=["hhi"])
fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
ax[0].plot(a.month, a.top2_share * 100, color="#8c564b"); ax[0].set_title("Top-2 brand share of app volume (%)")
ax[1].plot(a.month, a.hhi, color="#e377c2"); ax[1].axhline(2500, ls="--", c="grey", lw=.8); ax[1].set_title("HHI (2,500 = highly concentrated)")
ax[2].plot(a.month, a.tpap_vol_share * 100, color="#17becf"); ax[2].set_title("TPAP share of volume (%)")
fig.tight_layout(); fig.savefig(rf"{CH}\04_concentration.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
ax[0].plot(m.month, m.banks_live, color="#7f7f7f"); ax[0].set_title("Banks live on UPI")
ax[1].plot(a.month, a.n_brands, color="#bcbd22"); ax[1].set_title("Named app brands reporting")
fig.tight_layout(); fig.savefig(rf"{CH}\05_banks_apps_count.png"); plt.close(fig)

# ---------- app landscape ----------
life = named[named["brand"] != "Others"].groupby("brand").agg(first=("month", "min"), last=("month", "max"), months=("month", "size"), total_vol=("vol_mn", "sum"))
latest = m.month.max() if False else apps.month.max()
life["active_now"] = life["last"] == latest
life = life.sort_values("total_vol", ascending=False)
life.round(1).to_csv(r".\data\eda_brand_lifecycle.csv")
print("\nTOP 12 BRANDS BY CUMULATIVE VOLUME\n", life.head(12).round(0).to_string())
print(f"\nbrands total: {len(life)} | still reporting in {latest:%Y-%m}: {int(life.active_now.sum())} | dropped out: {int((~life.active_now).sum())}")
print("entries by year:", life["first"].dt.year.value_counts().sort_index().to_dict())

lat = named[named.month == latest].sort_values("share", ascending=False).head(8)[["brand", "vol_mn", "share"]]
print(f"\nLATEST ({latest:%Y-%m}) TOP 8\n", lat.round(3).to_string(index=False))

kind = apps.assign(kind=np.where(apps.is_other, "Others", np.where(apps.is_tpap, "TPAP", "Bank/other app"))) \
           .groupby(["month", "kind"])["vol_mn"].sum().unstack().fillna(0)
ks = kind.div(kind.sum(axis=1), axis=0)
print("\nVOLUME MIX BY APP TYPE (first / last month)\n", ks.iloc[[0, -1]].round(3).to_string())
