import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25, "font.size": 9})
m = pd.read_csv(r".\data\master_monthly.csv", parse_dates=["month"]).set_index("month")
apps = pd.read_csv(r"..\cleaning\apps_clean.csv", parse_dates=["month"])
apps["vol_mn"] = apps["vol_settled_mn"]   # headline-consistent volume (excludes on-us); see clean_apps.py
CH = r".\charts"
rng = np.random.default_rng(7)

# ---------- 1. stationarity: why we model changes, not levels ----------
print("1. ADF (p<0.05 => reject unit root). c = constant only, ct = constant + linear trend")
series = {"log volume": np.log(m["vol_per_day"]), "log value": np.log(m["val_cr"] / m["days_in_month"]), "avg ticket": m["avg_ticket"],
          "top2 share": m["top2_share"], "P2M vol share": m["p2m_vol_share"]}
for name, s in series.items():
    s = s.dropna()
    pc = adfuller(s, regression="c", autolag="AIC")[1]
    pct = adfuller(s, regression="ct", autolag="AIC")[1]
    dc = adfuller(s.diff().dropna(), regression="c", autolag="AIC")[1]
    print(f"   {name:15s} level p(c)={pc:.3f} p(ct)={pct:.3f} | first difference p(c)={dc:.3f}")
print("   Caveat: growth is decaying and COVID is a break near the start, so ADF is unreliable here.")
print("   Treat the change-based correlations as descriptive, not inferential.")

# ---------- 2. outlier months in growth ----------
print("\n2. OUTLIER MONTHS (robust z of seasonally-adjusted log growth, |z|>3.5; small-n so treat as candidates)")
for name, col in [("volume", "vol_per_day"), ("ticket", "avg_ticket")]:
    g = np.log(m[col]).diff().dropna()
    g = g - (g.groupby(g.index.month).transform("mean") - g.mean())
    # compare each month with its local neighbourhood so the decaying growth trend is not flagged
    loc = g.rolling(13, center=True, min_periods=7).median()
    dev = g - loc
    z = .6745 * (dev - dev.median()) / (dev - dev.median()).abs().median()
    hit = z[z.abs() > 3.5]
    print(f"   {name}: {len(hit)} flagged ->", {f"{d:%Y-%m}": round(float(v), 1) for d, v in hit.items()})

# ---------- 3. duopoly share ----------
print("\n3. SHARE TRENDS (brand share of app volume; HAC 95% CI on linear slope)")
sh = {"PhonePe": "phonepe_share", "Google Pay": "gpay_share", "Paytm": "paytm_share", "top-2": "top2_share", "TPAP total": "tpap_vol_share"}
fig, ax = plt.subplots(figsize=(9, 3.8))
for lab, col in sh.items():
    s = m[col].dropna() * 100
    X = sm.add_constant((s.index - s.index[0]).days / 365.25)
    f = sm.OLS(s.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    lo, hi = f.conf_int()[1]
    f12 = s.iloc[:12].mean(); l12 = s.iloc[-12:].mean()
    tau, tp = stats.kendalltau(np.arange(len(s)), s.values)
    print(f"   {lab:11s} first-12m avg {f12:5.1f}% -> last-12m avg {l12:5.1f}% | slope {f.params[1]:+.2f} pp/yr [{lo:+.2f}, {hi:+.2f}] | Kendall tau {tau:+.2f}")
    if lab in ("PhonePe", "Google Pay", "Paytm"):
        ax.plot(s.index, s, label=lab)
ax.set_title("Brand share of app volume (%)"); ax.legend(); fig.tight_layout(); fig.savefig(rf"{CH}\10_share_trends.png"); plt.close(fig)

# ---------- 4. event studies ----------
brand = apps.groupby(["month", "brand"])["vol_mn"].sum().unstack()
tot = apps.groupby("month")["vol_mn"].sum()
bshare = brand.div(tot, axis=0)

def boot_diff(a, b, n=5000):
    d = [rng.choice(b, len(b)).mean() - rng.choice(a, len(a)).mean() for _ in range(n)]
    return np.percentile(d, [2.5, 97.5])

print("\n4a. PAYTM: PPBL action (Jan-Mar 2024). Share of app volume, 6m before (2023-07..12) vs 6m after (2024-04..09)")
pre = bshare.loc["2023-07":"2023-12", "Paytm"] * 100
post = bshare.loc["2024-04":"2024-09", "Paytm"] * 100
lo, hi = boot_diff(pre.values, post.values)
print(f"   Paytm share {pre.mean():.1f}% -> {post.mean():.1f}% | diff {post.mean() - pre.mean():+.1f} pp, bootstrap 95% CI [{lo:+.1f}, {hi:+.1f}]")
tr = bshare.loc["2023-01":"2023-12", "Paytm"] * 100
sl, ic = np.polyfit(np.arange(len(tr)), tr.values, 1)
cf = ic + sl * (len(tr) + np.arange(6, 12))
print(f"   pre-trend (2023) extrapolated to 2024-04..09 would be {cf.mean():.1f}% vs actual {post.mean():.1f}%")
gain = (bshare.loc["2024-04":"2024-09"].fillna(0).mean() - bshare.loc["2023-07":"2023-12"].fillna(0).mean()).mul(100).sort_values()
print("   biggest share movers (pp):", {k: round(v, 1) for k, v in pd.concat([gain.head(3), gain.tail(4)]).items()})
print("   Paytm volume (mn): ", {f"{d:%Y-%m}": round(float(v)) for d, v in brand["Paytm"].loc["2023-11":"2024-05"].items()})

print("\n4b. WHATSAPP: onboarding cap removed 2024-12-31. MoM log growth of WhatsApp volume, 9m before vs 9m after")
w = np.log(brand["WhatsApp"]).diff()
before = w.loc["2024-04":"2024-12"].dropna(); after = w.loc["2025-01":"2025-09"].dropna()
t, tp = stats.ttest_ind(after, before, equal_var=False); u, up = stats.mannwhitneyu(after, before)
lo, hi = boot_diff(before.values, after.values)
print(f"   mean MoM growth {before.mean():.1%} -> {after.mean():.1%} | diff {after.mean() - before.mean():+.1%} bootstrap CI [{lo:+.1%}, {hi:+.1%}] | Welch p={tp:.3f}, Mann-Whitney p={up:.3f}")
print("   WhatsApp volume (mn):", {f"{d:%Y-%m}": round(float(v), 1) for d, v in brand["WhatsApp"].loc["2024-10":"2025-04"].items()})

# ---------- 5. rename detector (validates the alias map) ----------
print("\n5. RENAME DETECTOR: a brand ends in month t-1 while another starts in month t with similar volume")
named = apps[~apps.is_other].groupby(["month", "app"])["vol_mn"].sum().reset_index()
life = named.groupby("app").agg(first=("month", "min"), last=("month", "max"))
vol = named.set_index(["app", "month"])["vol_mn"]
end_m = apps["month"].max(); start_m = apps["month"].min()
rows = []
for a_, r in life[life["last"] < end_m].iterrows():
    nxt = r["last"] + pd.DateOffset(months=1)
    va = vol[(a_, r["last"])]
    if va < 0.3:
        continue
    for b_, rb in life[(life["first"] == nxt) | (life["first"] == nxt + pd.DateOffset(months=1))].iterrows():
        vb = vol[(b_, rb["first"])]
        ratio = vb / va
        if .5 <= ratio <= 2:
            rows.append({"ended": a_, "last_month": r["last"].strftime("%Y-%m"), "last_vol": round(va, 2), "started": b_, "first_month": rb["first"].strftime("%Y-%m"), "first_vol": round(vb, 2), "ratio": round(ratio, 2)})
cand = pd.DataFrame(rows).sort_values("last_vol", ascending=False)
cand.to_csv(r".\data\stats_rename_candidates.csv", index=False)
print(cand.head(15).to_string(index=False) if len(cand) else "   none")
print(f"   {len(cand)} candidate pairs saved to data/stats_rename_candidates.csv (review manually, these are leads, not proof)")

# brands with implausible single-month jumps (possible mapping or scrape errors)
bm = np.log(brand.where(brand >= 0.5)).diff()
jumps = bm.stack()
jumps = jumps[(jumps.abs() > 1.2)]
print(f"\n   brand-month jumps > 3.3x or < 0.3x on volume >=0.5mn: {len(jumps)} (top 10 by size)")
for (d_, b_), v in jumps.reindex(jumps.abs().sort_values(ascending=False).index).head(10).items():
    print(f"     {d_:%Y-%m} {b_:30s} x{np.exp(v):.2f}")
