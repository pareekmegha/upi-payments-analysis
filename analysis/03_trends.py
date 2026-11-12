import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.seasonal import STL

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "font.size": 9})
m = pd.read_csv(r".\data\master_monthly.csv", parse_dates=["month"]).set_index("month")
CH = r".\charts"

# ---------- CAGR ----------
def cagr(s, a, b):
    yrs = (b - a).days / 365.25
    return (s[b] / s[a]) ** (1 / yrs) - 1

end = m.index.max()
print("CAGR (point to point, month level)")
rows = []
for label, a in [("full (2019-04 ->)", m.index.min()), ("last 5y", end - pd.DateOffset(years=5)),
                 ("last 3y", end - pd.DateOffset(years=3)), ("last 2y", end - pd.DateOffset(years=2)), ("last 1y", end - pd.DateOffset(years=1))]:
    rows.append({"window": label, "from": a.date(), "vol_cagr": cagr(m["vol_mn"], a, end), "val_cagr": cagr(m["val_cr"], a, end),
                 "ticket_cagr": cagr(m["avg_ticket"], a, end)})
cg = pd.DataFrame(rows)
print(cg.round(3).to_string(index=False))
cg.to_csv(r".\data\trend_cagr.csv", index=False)

# ---------- growth deceleration ----------
y = m["vol_yoy"].dropna()
t = np.arange(len(y))
X = sm.add_constant(t)
fit = sm.OLS(np.log1p(y.values), X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
print(f"\nYoY volume growth:{y.iloc[0]:.1%} ({y.index[0]:%Y-%m}) -> {y.iloc[-1]:.1%} ({y.index[-1]:%Y-%m})")
print(f"log(1+YoY) trend, all months: slope {fit.params[1]:.4f}/month  95% CI [{fit.conf_int()[1][0]:.4f}, {fit.conf_int()[1][1]:.4f}] (HAC)")
post = y[y.index >= "2022-04-01"]          # after the COVID base-effect spike
fit2 = sm.OLS(np.log1p(post.values), sm.add_constant(np.arange(len(post))), ).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
print(f"log(1+YoY) trend, from 2022-04 only: slope {fit2.params[1]:.4f}/month  95% CI [{fit2.conf_int()[1][0]:.4f}, {fit2.conf_int()[1][1]:.4f}] -> the growth factor (1+YoY) shrinks ~{(1 - np.exp(12 * fit2.params[1])) * 100:.0f}% per year (e.g. 50% YoY -> ~35%)")
print("YoY at checkpoints:", {f"{d:%Y-%m}": round(float(y[d]), 3) for d in y.index[[0, 12, 24, 36, 48, 60, -1]]})

fig, ax = plt.subplots(figsize=(9, 3.6))
ax.plot(m.index, m["vol_yoy"] * 100, label="volume YoY"); ax.plot(m.index, m["val_yoy"] * 100, label="value YoY")
ax.set_title("Year-over-year growth (%)"); ax.legend(); fig.tight_layout(); fig.savefig(rf"{CH}\06_yoy_growth.png"); plt.close(fig)

# ---------- seasonality (STL on log per-day series, so month length is not mistaken for seasonality) ----------
def seasonal_profile(series, name):
    ls = np.log(series.dropna())
    ls.index = pd.DatetimeIndex(ls.index, freq="MS")
    res = STL(ls, period=12, robust=True).fit()
    dt = (ls - res.trend)
    strength = max(0, 1 - res.resid.var() / (res.seasonal + res.resid).var())
    g = dt.groupby(dt.index.month)
    prof = pd.DataFrame({"effect_pct": (np.exp(g.mean()) - 1) * 100, "n_years": g.size()})
    se = g.std() / np.sqrt(g.size())
    tcrit = stats.t.ppf(.975, g.size() - 1)
    prof["ci_lo"] = (np.exp(g.mean() - tcrit * se) - 1) * 100
    prof["ci_hi"] = (np.exp(g.mean() + tcrit * se) - 1) * 100
    prof["significant"] = (prof.ci_lo > 0) | (prof.ci_hi < 0)
    print(f"\nSEASONALITY: {name} | seasonal strength {strength:.2f} (0-1)")
    print(prof.round(2).to_string())
    prof.round(3).to_csv(rf".\data\trend_seasonality_{name}.csv")
    return res, prof

m["val_per_day"] = m["val_cr"] / m["days_in_month"]
res_v, prof_v = seasonal_profile(m["vol_per_day"], "volume")
res_t, prof_t = seasonal_profile(m["avg_ticket"], "ticket")

fig, ax = plt.subplots(1, 2, figsize=(11, 3.6), sharey=False)
for a, prof, ttl in ((ax[0], prof_v, "Volume per day: month effect vs trend (%)"), (ax[1], prof_t, "Avg ticket: month effect vs trend (%)")):
    a.bar(prof.index, prof.effect_pct, color=np.where(prof.significant, "#1f77b4", "#c7c7c7"))
    a.errorbar(prof.index, prof.effect_pct, yerr=[prof.effect_pct - prof.ci_lo, prof.ci_hi - prof.effect_pct], fmt="none", ecolor="k", lw=.8)
    a.set_xticks(range(1, 13)); a.set_title(ttl); a.axhline(0, c="k", lw=.6)
fig.tight_layout(); fig.savefig(rf"{CH}\07_seasonality.png"); plt.close(fig)

fig = res_v.plot(); fig.set_size_inches(9, 6); fig.tight_layout(); fig.savefig(rf"{CH}\08_stl_volume.png"); plt.close(fig)

# ---------- level shifts in growth (single unknown break in mean MoM growth, sup-F) ----------
g = np.log(m["vol_per_day"]).diff().dropna()
# remove seasonality so a festive month is not read as a break
g = g - (g.groupby(g.index.month).transform("mean") - g.mean())
n = len(g); lo, hi = int(.15 * n), int(.85 * n)
rss0 = ((g - g.mean()) ** 2).sum()
best = max(((rss0 - (((g.iloc[:k] - g.iloc[:k].mean()) ** 2).sum() + ((g.iloc[k:] - g.iloc[k:].mean()) ** 2).sum())) /
            ((((g.iloc[:k] - g.iloc[:k].mean()) ** 2).sum() + ((g.iloc[k:] - g.iloc[k:].mean()) ** 2).sum()) / (n - 2)), k)
           for k in range(lo, hi))
supf, k = best
print(f"\nBREAK IN MEAN MoM GROWTH: best break before {g.index[k]:%Y-%m} | sup-F = {supf:.1f} (Andrews 5% critical value ~8.9 for 15% trimming)")
print(f"  mean MoM growth before {g.iloc[:k].mean():.2%} -> after {g.iloc[k:].mean():.2%}")
print("  NOTE: growth is decaying smoothly, so a 'break' here mostly reflects deceleration, not a discrete shock.")
