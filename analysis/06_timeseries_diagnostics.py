import warnings
warnings.filterwarnings("ignore")
import itertools
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller, kpss

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25, "font.size": 9})
m = pd.read_csv(r".\data\master_monthly.csv", parse_dates=["month"]).set_index("month")
m.index.freq = "MS"
CH = r".\charts"

lv = np.log(m["vol_per_day"]).rename("log_vol")
samples = {"full (2019-04 ->)": lv, "post-COVID (2021-06 ->)": lv["2021-06-01":]}
out = []

# ---------- 1. stationarity: ADF and KPSS read together ----------
def verdict(adf_p, kpss_p):
    if adf_p < .05 and kpss_p >= .05:
        return "stationary"
    if adf_p >= .05 and kpss_p < .05:
        return "NON-stationary"
    if adf_p < .05 and kpss_p < .05:
        return "conflict (trend/break?)"
    return "inconclusive (low power)"

print("1. STATIONARITY. ADF H0 = unit root; KPSS H0 = stationary. Read together.\n")
for sname, s in samples.items():
    print(f"  sample: {sname} (n={len(s)})")
    for tname, x, kreg in [("log level", s, "ct"), ("d log (growth)", s.diff().dropna(), "c"),
                           ("d log, seasonally differenced (12)", s.diff().diff(12).dropna(), "c")]:
        a = adfuller(x, autolag="AIC")[1]
        k = kpss(x, regression=kreg, nlags="auto")[1]
        v = verdict(a, k)
        print(f"    {tname:36s} ADF p={a:.3f} | KPSS({kreg}) p={min(max(k, .01), .1):.2f} -> {v}")
        out.append({"sample": sname, "series": "log volume/day", "transform": tname, "adf_p": a, "kpss_p": k, "verdict": v})

# ---------- 2. ACF / PACF of growth ----------
fig, ax = plt.subplots(2, 2, figsize=(11, 6))
for j, (sname, s) in enumerate(samples.items()):
    g = s.diff().dropna()
    plot_acf(g, lags=24, ax=ax[0, j], title=f"ACF of monthly log growth: {sname}")
    plot_pacf(g, lags=24, ax=ax[1, j], method="ywm", title=f"PACF: {sname}")
fig.tight_layout(); fig.savefig(rf"{CH}\11_acf_pacf.png"); plt.close(fig)

print("\n2. AUTOCORRELATION OF MONTHLY GROWTH (significant lags at ~95%)")
for sname, s in samples.items():
    g = s.diff().dropna()
    from statsmodels.tsa.stattools import acf, pacf
    a_ = acf(g, nlags=24); p_ = pacf(g, nlags=24, method="ywm")
    band = 1.96 / np.sqrt(len(g))
    sig_a = [i for i in range(1, 25) if abs(a_[i]) > band]
    sig_p = [i for i in range(1, 25) if abs(p_[i]) > band]
    print(f"  {sname}: ACF sig lags {sig_a} | PACF sig lags {sig_p} | lag-1 ACF {a_[1]:.2f} | lag-12 ACF {a_[12]:.2f} (band +-{band:.2f})")

# ---------- 3. candidate ARIMA fits + residual diagnostics ----------
print("\n3. ARIMA(p,1,q)+drift on log volume/day: best by AIC and residual checks (Ljung-Box lag 12 and 24, ARCH, Jarque-Bera, residual lag-12 ACF)")
fig, ax = plt.subplots(2, 2, figsize=(11, 5.6))
for j, (sname, s) in enumerate(samples.items()):
    best = None
    for p, q in itertools.product(range(3), range(3)):
        try:
            r = SARIMAX(s, order=(p, 1, q), trend="c").fit(disp=False)
        except Exception:
            continue
        if best is None or r.aic < best[0].aic:
            best = (r, p, q)
    r, p, q = best
    e = r.resid.iloc[1:]
    lb12 = acorr_ljungbox(e, lags=[12], return_df=True)["lb_pvalue"].iloc[0]
    lb24 = acorr_ljungbox(e, lags=[24], return_df=True)["lb_pvalue"].iloc[0] if len(e) > 40 else np.nan
    arch = het_arch(e, nlags=6)[1]
    jb = stats.jarque_bera(e)[1]
    a12 = acf(e, nlags=12)[12]
    first, second = e.iloc[:len(e) // 2], e.iloc[len(e) // 2:]
    var_ratio = first.var() / second.var()
    print(f"  {sname}: best ARIMA({p},1,{q}) AIC={r.aic:.1f} | LB12 p={lb12:.3f} LB24 p={lb24:.3f} | ARCH p={arch:.3f} | JB p={jb:.3f} | resid lag-12 ACF {a12:.2f} | var(1st half)/var(2nd half) {var_ratio:.1f}")
    out.append({"sample": sname, "series": "log volume/day", "transform": f"ARIMA({p},1,{q})", "lb12_p": lb12, "lb24_p": lb24, "arch_p": arch, "jb_p": jb, "resid_lag12_acf": a12, "var_ratio_halves": var_ratio})
    ax[0, j].plot(e.index, e.values); ax[0, j].axhline(0, c="k", lw=.6); ax[0, j].set_title(f"Residuals ARIMA({p},1,{q}): {sname}")
    stats.probplot(e, dist="norm", plot=ax[1, j]); ax[1, j].set_title("Normal Q-Q")
fig.tight_layout(); fig.savefig(rf"{CH}\12_residual_diag.png"); plt.close(fig)

# ---------- 4. STL on other series ----------
def strengths(x):
    x = x.dropna()
    x.index = pd.DatetimeIndex(x.index, freq="MS")
    res = STL(x, period=12, robust=True).fit()
    fs = max(0, 1 - res.resid.var() / (res.seasonal + res.resid).var())
    ft = max(0, 1 - res.resid.var() / (res.trend + res.resid).var())
    return res, fs, ft

print("\n4. STL STRENGTHS (0 = none, 1 = fully determined by that component)")
cands = {"log volume/day": lv, "log value/day": np.log(m["val_cr"] / m["days_in_month"]), "avg ticket": m["avg_ticket"],
         "P2M vol share": m["p2m_vol_share"], "top-2 share": m["top2_share"], "log banks live": np.log(m["banks_live"])}
fig, ax = plt.subplots(len(cands), 1, figsize=(9, 11), sharex=True)
for i, (name, x) in enumerate(cands.items()):
    res, fs, ft = strengths(x)
    print(f"  {name:16s} trend strength {ft:.2f} | seasonal strength {fs:.2f}")
    out.append({"sample": "full", "series": name, "transform": "STL", "trend_strength": ft, "seasonal_strength": fs})
    ax[i].plot(res.trend.index, res.trend, label="trend"); ax[i].plot(res.seasonal.index, res.seasonal + res.trend.mean() * 0, label="seasonal", alpha=.6)
    ax[i].set_title(f"{name}: trend {ft:.2f}, seasonal {fs:.2f}", fontsize=8)
fig.tight_layout(); fig.savefig(rf"{CH}\13_stl_all_series.png"); plt.close(fig)

# ---------- 5. is growth predictable at all? ----------
print("\n5. PREDICTABILITY OF GROWTH (post-COVID): does last month's growth help?")
g = lv["2021-06-01":].diff().dropna()
ar1 = np.corrcoef(g.iloc[1:], g.shift(1).dropna())[0, 1]
detr = g - g.rolling(12, center=True, min_periods=6).mean()
print(f"  lag-1 autocorrelation of growth: {ar1:.2f} | growth std {g.std():.3%} vs mean {g.mean():.3%} (signal/noise {g.mean() / g.std():.2f})")
print(f"  std of growth first half {g.iloc[:len(g) // 2].std():.3%} -> second half {g.iloc[len(g) // 2:].std():.3%}")

pd.DataFrame(out).to_csv(r".\data\ts_diagnostics.csv", index=False)
print("\nsaved data/ts_diagnostics.csv")
