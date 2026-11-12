import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import norm
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.statespace.sarimax import SARIMAX

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25, "font.size": 9})
m = pd.read_csv(r".\data\master_monthly.csv", parse_dates=["month"]).set_index("month")
m.index.freq = "MS"
CH = r".\charts"
START = "2021-06-01"          # post-COVID training window (see FINDINGS section 7)
HS = (1, 3, 6, 12)
H_FINAL = 12


# ---------------- models: each returns (point forecast, sd of forecast error or None), all on the log scale ----------------
def m_naive(y, h):
    return np.repeat(y.iloc[-1], h), None

def m_drift12(y, h):
    d = y.diff().iloc[-12:].mean()
    return y.iloc[-1] + d * np.arange(1, h + 1), None

def m_snaive_growth(y, h):
    # same month last year, plus the latest year-over-year growth: strong baseline for a trending monthly series
    yo = y.iloc[-1] - y.iloc[-13]
    return np.array([y.iloc[-12 + ((k - 1) % 12)] + yo * (1 + (k - 1) // 12) for k in range(1, h + 1)]), None

def _ets(y, h, seasonal):
    kw = dict(error="add", trend="add", damped_trend=True)
    if seasonal:
        kw.update(seasonal="add", seasonal_periods=12)
    r = ETSModel(y, **kw).fit(disp=False, maxiter=2000)
    pf = r.get_prediction(start=len(y), end=len(y) + h - 1).summary_frame(alpha=.2)
    sd = (pf["pi_upper"].values - pf["mean"].values) / norm.ppf(.9)
    return pf["mean"].values, sd

def m_ets_damped(y, h):
    return _ets(y, h, False)

def m_ets_damped_seas(y, h):
    return _ets(y, h, True)

def m_arima_d2(y, h):
    r = SARIMAX(y, order=(1, 2, 1)).fit(disp=False)
    f = r.get_forecast(h)
    return f.predicted_mean.values, np.sqrt(f.var_pred_mean.values)

def m_decay(y, h):
    # monthly log growth g_t = c + a*exp(-b*t), integrated forward; error accumulates as a random walk
    g = y.diff().dropna().values
    t = np.arange(len(g), dtype=float)
    try:
        (c, a, b), _ = curve_fit(lambda t, c, a, b: c + a * np.exp(-b * t), t, g, p0=[g[-6:].mean(), g[:6].mean() - g[-6:].mean(), .03],
                                 bounds=([-.01, 0, 1e-4], [.05, .5, .5]), maxfev=20000)
        resid = g - (c + a * np.exp(-b * t))
        tf = np.arange(len(g), len(g) + h, dtype=float)
        gf = c + a * np.exp(-b * tf)
    except Exception:
        resid = g - g.mean(); gf = np.repeat(g[-12:].mean(), h)
    return y.iloc[-1] + np.cumsum(gf), resid.std(ddof=1) * np.sqrt(np.arange(1, h + 1))

def m_ensemble(y, h):
    fs = [f(y, h)[0] for f in (m_ets_damped, m_arima_d2, m_decay)]
    return np.mean(fs, axis=0), None

MODELS = {"naive": m_naive, "drift (12m)": m_drift12, "seasonal naive + YoY": m_snaive_growth,
          "ETS damped": m_ets_damped, "ETS damped + seasonal": m_ets_damped_seas, "ARIMA(1,2,1)": m_arima_d2,
          "decaying growth": m_decay, "ensemble (ETS, ARIMA, decay)": m_ensemble}


# ---------------- backtest ----------------
def backtest(y, n0=36):
    rows = []
    N = len(y)
    for T in range(n0, N - 1):
        train = y.iloc[:T]; train.index.freq = "MS"
        scale = np.abs(np.diff(np.exp(train.values))).mean()
        for name, fn in MODELS.items():
            try:
                f, sd = fn(train, max(HS))
            except Exception:
                continue
            for h in HS:
                if T + h - 1 >= N:
                    continue
                act = y.iloc[T + h - 1]
                e = np.exp(f[h - 1]) - np.exp(act)
                row = {"model": name, "h": h, "origin": y.index[T - 1], "pct_err": e / np.exp(act), "abs_scaled": abs(e) / scale}
                if sd is not None:
                    row["covered80"] = abs(act - f[h - 1]) <= norm.ppf(.9) * sd[h - 1]
                rows.append(row)
    return pd.DataFrame(rows)


def summarize(bt):
    bt = bt.assign(covered80=bt["covered80"].astype(float))     # object dtype (bool + NaN) otherwise averages wrongly
    g = bt.groupby(["model", "h"])
    s = g.agg(mape=("pct_err", lambda x: x.abs().mean() * 100), bias=("pct_err", lambda x: x.mean() * 100),
              mase=("abs_scaled", "mean"), n=("pct_err", "size"), cover80=("covered80", "mean")).reset_index()
    return s


def run_series(name, y):
    bt = backtest(y)
    s = summarize(bt)
    print(f"\n=== BACKTEST: {name} | {y.index[0]:%Y-%m} to {y.index[-1]:%Y-%m}, first origin after 36 months, expanding window ===")
    for h in HS:
        t = s[s.h == h].sort_values("mase")
        print(f"\n h={h} (origins n={int(t.n.iloc[0])})")
        print(t[["model", "mape", "bias", "mase", "cover80"]].round(2).to_string(index=False))
    s["series"] = name
    return s, bt


# ---------------- run ----------------
res = {}
y_vol = np.log(m["vol_per_day"][START:])
y_tkt = np.log(m["avg_ticket"][START:])
sv, btv = run_series("volume per day", y_vol)
st, btt = run_series("average ticket", y_tkt)
pd.concat([sv, st]).round(4).to_csv(r".\data\forecast_backtest.csv", index=False)


def pick(s):
    t = s[s.h.isin([3, 6, 12])].groupby("model")["mase"].mean().sort_values()
    base = {"naive", "drift (12m)", "seasonal naive + YoY"}
    best_base = t[[i for i in t.index if i in base]].min()
    cand = t[[i for i in t.index if i not in base]]
    return t, cand.index[0], cand.iloc[0], best_base

for nm, s in (("volume", sv), ("ticket", st)):
    t, best, v, bb = pick(s)
    print(f"\n{nm.upper()}: mean MASE over h=3,6,12 ->", {k: round(x, 2) for k, x in t.items()})
    print(f"  best non-baseline: {best} ({v:.2f}) vs best baseline ({bb:.2f}) -> {'beats' if v < bb else 'DOES NOT beat'} baselines")
    res[nm] = best


# =============== final 12-month forecast ===============
def sim_paths(y, seasonal, n=4000, seed=11):
    kw = dict(error="add", trend="add", damped_trend=True)
    if seasonal:
        kw.update(seasonal="add", seasonal_periods=12)
    r = ETSModel(y, **kw).fit(disp=False, maxiter=2000)
    s = r.simulate(nsimulations=H_FINAL, repetitions=n, anchor="end", random_state=seed)
    return np.asarray(s), r

idx = pd.date_range(m.index.max() + pd.DateOffset(months=1), periods=H_FINAL, freq="MS")
vol_paths, rv = sim_paths(y_vol, seasonal=True)          # log volume per day
tkt_paths, rt = sim_paths(y_tkt, seasonal=False)         # log ticket (non-seasonal: seasonal variant is overconfident)
days = idx.days_in_month.values[:, None]
vol_mn = np.exp(vol_paths) * days
ticket = np.exp(tkt_paths)
value_cr = vol_mn * ticket / 10                            # ticket = value*10/volume
print("\nETS parameters: volume damping phi=%.3f | ticket damping phi=%.3f" % (rv.params[rv.param_names.index("damping_trend")], rt.params[rt.param_names.index("damping_trend")]))

# does independence between volume and ticket errors hold? (backtest error correlation, h=6)
cv = btv[(btv.model == "ETS damped + seasonal") & (btv.h == 6)].set_index("origin")["pct_err"]
ct = btt[(btt.model == "ETS damped") & (btt.h == 6)].set_index("origin")["pct_err"]
rho = cv.corr(ct)
print(f"backtest correlation of volume and ticket errors (h=6): {rho:.2f}  -> value intervals assume 0")

def q(a, p):
    return np.percentile(a, p, axis=1)

fc = pd.DataFrame({"month": idx})
for nm, a in (("vol_mn", vol_mn), ("ticket", ticket), ("val_cr", value_cr)):
    fc[nm] = q(a, 50)
    fc[f"{nm}_p10"], fc[f"{nm}_p90"] = q(a, 10), q(a, 90)
    fc[f"{nm}_p2_5"], fc[f"{nm}_p97_5"] = q(a, 2.5), q(a, 97.5)
last_year = m["vol_mn"].reindex(idx - pd.DateOffset(years=1)).values
fc["vol_yoy"] = fc["vol_mn"] / last_year - 1
fc.round(4).to_csv(r".\data\forecast_12m.csv", index=False)
print("\n12-MONTH FORECAST (median; 80% interval)")
show = fc.assign(vol=lambda d: d.vol_mn.round(0).astype(int), vol_80=lambda d: d.vol_mn_p10.round(0).astype(int).astype(str) + "-" + d.vol_mn_p90.round(0).astype(int).astype(str),
                 tkt=lambda d: d.ticket.round(0).astype(int), val_lakh_cr=lambda d: (d.val_cr / 1e5).round(2), yoy=lambda d: (d.vol_yoy * 100).round(1))
print(show[["month", "vol", "vol_80", "tkt", "val_lakh_cr", "yoy"]].to_string(index=False))

# fiscal year totals: FY2026-27 = actual Apr-Oct 2026 + forecast Nov-Mar
fy_idx = [d for d in idx if d <= pd.Timestamp("2027-03-01")]
k = len(fy_idx)
actual = m.loc["2026-04-01":"2026-10-01"]
for nm, col, a in (("volume (mn)", "vol_mn", vol_mn), ("value (Rs cr)", "val_cr", value_cr)):
    tot = actual[col].sum() + a[:k].sum(axis=0)
    prev = m.loc["2025-04-01":"2026-03-01", col].sum()
    g = tot / prev - 1
    print(f"FY2026-27 {nm}: {np.median(tot):,.0f} (80%: {np.percentile(tot, 10):,.0f} to {np.percentile(tot, 90):,.0f}) | growth vs FY2025-26: {np.median(g):.1%} (80%: {np.percentile(g, 10):.1%} to {np.percentile(g, 90):.1%})")

# ---------- charts ----------
sv_ = sv.copy()
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
for mod, grp in sv_.groupby("model"):
    ax[0].plot(grp.h, grp.mase, marker="o", label=mod, lw=1.5 if mod in ("ETS damped + seasonal",) else .9)
ax[0].set_title("Volume: backtest MASE by horizon (lower is better)"); ax[0].set_xlabel("months ahead"); ax[0].legend(fontsize=6.5)
b12 = sv_[sv_.h == 12].set_index("model")["bias"].sort_values()
ax[1].barh(b12.index, b12.values, color=np.where(b12 > 0, "#d62728", "#1f77b4")); ax[1].axvline(0, c="k", lw=.6)
ax[1].set_title("Bias at 12 months ahead (%): red = over-forecast")
fig.tight_layout(); fig.savefig(rf"{CH}\14_backtest.png"); plt.close(fig)

hist = m.loc["2023-10-01":]
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(hist.index, hist.vol_mn / 1000, color="#1f77b4", label="actual")
ax.plot(fc.month, fc.vol_mn / 1000, color="#d62728", label="forecast (median)")
ax.fill_between(fc.month, fc.vol_mn_p10 / 1000, fc.vol_mn_p90 / 1000, color="#d62728", alpha=.25, label="80%")
ax.fill_between(fc.month, fc.vol_mn_p2_5 / 1000, fc.vol_mn_p97_5 / 1000, color="#d62728", alpha=.12, label="95%")
ax.set_title("UPI monthly volume: 12-month forecast (billion transactions)"); ax.legend(); fig.tight_layout(); fig.savefig(rf"{CH}\15_forecast_volume.png"); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
for a_, col, ttl, sc in ((ax[0], "ticket", "Average ticket (Rs)", 1), (ax[1], "val_cr", "Monthly value (Rs lakh crore)", 1e5)):
    a_.plot(hist.index, (hist["avg_ticket"] if col == "ticket" else hist["val_cr"]) / sc, color="#1f77b4")
    a_.plot(fc.month, fc[col] / sc, color="#d62728")
    a_.fill_between(fc.month, fc[f"{col}_p10"] / sc, fc[f"{col}_p90"] / sc, color="#d62728", alpha=.25)
    a_.fill_between(fc.month, fc[f"{col}_p2_5"] / sc, fc[f"{col}_p97_5"] / sc, color="#d62728", alpha=.12)
    a_.set_title(ttl)
fig.tight_layout(); fig.savefig(rf"{CH}\16_forecast_value_ticket.png"); plt.close(fig)
print("\nsaved charts 14-16, data/forecast_12m.csv, data/forecast_backtest.csv")
