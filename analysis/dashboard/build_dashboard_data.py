import json
import numpy as np
import pandas as pd

A = r"..\data"
C = r"..\..\cleaning"
OUT = r"."


def clean(v, nd):
    return None if pd.isna(v) else round(float(v), nd)


# ---- monthly totals ----
m = pd.read_csv(rf"{A}\master_monthly.csv", parse_dates=["month"])
val_yoy = m["val_cr"].pct_change(12)
master = [{
    "month": r.month.strftime("%Y-%m-%d"),
    "banks_live": int(r.banks_live),
    "vol_bn": clean(r.vol_mn / 1000, 2),
    "val_lc": clean(r.val_cr / 1e5, 2),
    "avg_ticket": clean(r.avg_ticket, 0),
    "vol_yoy_pct": clean(r.vol_yoy * 100, 1),
    "val_yoy_pct": clean(val_yoy[i] * 100, 1),
    "p2m_vol_pct": clean(r.p2m_vol_share * 100, 1),
    "p2m_val_pct": clean(r.p2m_val_share * 100, 1),
} for i, r in enumerate(m.itertuples())]

# ---- brand shares, NPCI basis: share of headline UPI volume ----
a = pd.read_csv(rf"{C}\apps_clean.csv", parse_dates=["month"])
a["v"] = a["vol_settled_mn"]
head = m.set_index("month")["vol_mn"]
b = a.groupby(["month", "brand"])["v"].sum().unstack()
keep = ["PhonePe", "Google Pay", "Paytm", "Navi", "super.money", "WhatsApp"]
rows = []
for mon, r in b.iterrows():
    tot = head[mon]
    listed = 0.0
    for k in keep:
        s = float(r.get(k, 0) if pd.notna(r.get(k, np.nan)) else 0)
        listed += s
        rows.append({"month": mon.strftime("%Y-%m-%d"), "brand": k, "share_pct": round(s / tot * 100, 2)})
    rows.append({"month": mon.strftime("%Y-%m-%d"), "brand": "All other", "share_pct": round((1 - listed / tot) * 100, 2)})

# ---- forecast ----
f = pd.read_csv(rf"{A}\forecast_12m.csv", parse_dates=["month"])
# forecast_12m.csv stores vol_yoy rounded to whole percent, so recompute it from the forecast and the actuals a year earlier
head_vol = m.set_index("month")["vol_mn"]
f["vol_yoy"] = [r.vol_mn / head_vol[r.month - pd.DateOffset(years=1)] - 1 for r in f.itertuples()]
forecast = [{
    "month": r.month.strftime("%Y-%m-%d"),
    "vol_bn": clean(r.vol_mn / 1000, 1), "vol_bn_lo80": clean(r.vol_mn_p10 / 1000, 1), "vol_bn_hi80": clean(r.vol_mn_p90 / 1000, 1),
    "vol_bn_lo95": clean(r.vol_mn_p2_5 / 1000, 1), "vol_bn_hi95": clean(r.vol_mn_p97_5 / 1000, 1),
    "ticket": clean(r.ticket, 0), "val_lc": clean(r.val_cr / 1e5, 1), "yoy_pct": clean(r.vol_yoy * 100, 1),
} for r in f.itertuples()]

# ---- backtest (volume) ----
bt = pd.read_csv(rf"{A}\forecast_backtest.csv")
bt = bt[bt.series == "volume per day"]
backtest = [{"model": r.model, "h": int(r.h), "mape_pct": clean(r.mape, 1), "bias_pct": clean(r.bias, 1), "mase": clean(r.mase, 2),
             "cover80_pct": clean(r.cover80 * 100, 0) if pd.notna(r.cover80) else None, "origins": int(r.n)} for r in bt.itertuples()]

# ---- events (sources: NPCI notes, news reports found by web search; see FINDINGS.md section 6) ----
events = [
    {"tag": "A", "month": "2020-11-01", "title": "30% app cap proposed; WhatsApp Pay approved", "detail": "NPCI proposed a 30% volume cap on third-party apps and approved a limited WhatsApp Pay rollout.", "status": "reported", "on_chart": False},
    {"tag": "B", "month": "2020-12-01", "title": "B2C and B2B credited to the PSP bank", "detail": "Definition change in NPCI's app table. Bank-app volumes (for example Axis Bank, 5 mn to 92 mn) are not comparable before and after.", "status": "confirmed", "on_chart": False},
    {"tag": "C", "month": "2022-12-01", "title": "Flipkart completes separation from PhonePe", "detail": "Reported by trade press.", "status": "reported", "on_chart": False},
    {"tag": "D", "month": "2023-08-01", "title": "Navi starts UPI payments", "detail": "First appears in NPCI data in September 2023; passes Amazon Pay in August 2024 and Axis Bank in September 2024.", "status": "confirmed", "on_chart": True},
    {"tag": "E", "month": "2024-01-01", "title": "RBI restricts Paytm Payments Bank", "detail": "Announced 31 January; deadline moved to 15 March. Paytm's share falls from 11.9% (Jan) to 8.2% (May 2024).", "status": "confirmed", "on_chart": True},
    {"tag": "F", "month": "2024-06-01", "title": "super.money (Flipkart) launches in beta", "detail": "Open to all Android users in August 2024. Plateaus near 1.3% share through late 2025.", "status": "confirmed", "on_chart": True},
    {"tag": "G", "month": "2024-12-01", "title": "Cap deadline moved to Dec 2026; WhatsApp limit removed", "detail": "NPCI extended the 30% cap compliance date to 31 December 2026 and lifted WhatsApp's onboarding limit on 31 December. No significant WhatsApp step in the data.", "status": "confirmed", "on_chart": True},
    {"tag": "H", "month": "2026-04-01", "title": "RBI cancels Paytm Payments Bank licence", "detail": "Effective 24 April 2026 under the Banking Regulation Act. Paytm says its UPI service continues.", "status": "confirmed", "on_chart": True},
    {"tag": "I", "month": "2026-10-01", "title": "0.4% merchant fee on UPI payments above Rs 2,000", "detail": "Effective 15 October 2026, capped at Rs 300, paid by the merchant; P2P and small merchants exempt. Reported by many outlets; the primary circular was not seen. Too early to see in the data.", "status": "reported", "on_chart": True},
]

for name, obj in (("master", master), ("brand_share", rows), ("forecast", forecast), ("backtest", backtest), ("events", events)):
    with open(rf"{OUT}\{name}.json", "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)
    print(name, len(obj))
