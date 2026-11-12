import numpy as np
import pandas as pd

C = r"..\cleaning"
product = pd.read_csv(rf"{C}\product_clean.csv", parse_dates=["month"])
p2p = pd.read_csv(rf"{C}\p2p_p2m_clean.csv", parse_dates=["month"])
apps = pd.read_csv(rf"{C}\apps_clean.csv", parse_dates=["month"])
apps["vol_mn"] = apps["vol_settled_mn"]   # headline-consistent volume (excludes on-us); see clean_apps.py

# --- app-level aggregates, at brand level (Paytm Payments Bank + Paytm rolled up) ---
named = apps[~apps["is_other"]]
brand = named.groupby(["month", "brand"], as_index=False)["vol_mn"].sum()
app_total = apps.groupby("month")["vol_mn"].sum().rename("apps_vol_sum")

def share_table(b, total):
    b = b.merge(total, on="month")
    b["share"] = b["vol_mn"] / b["apps_vol_sum"]
    return b

brand = share_table(brand, app_total.reset_index())
agg = brand.groupby("month").agg(
    n_brands=("brand", "size"),
    hhi=("share", lambda s: float((s ** 2).sum() * 10000)),
).join(app_total)
ranked = brand.sort_values(["month", "share"], ascending=[True, False])
ranked["rank"] = ranked.groupby("month").cumcount() + 1
for n in (1, 2, 3):
    agg[f"top{n}_share"] = ranked[ranked["rank"] <= n].groupby("month")["share"].sum()
for b, col in (("PhonePe", "phonepe_share"), ("Google Pay", "gpay_share"), ("Paytm", "paytm_share"), ("WhatsApp", "whatsapp_share")):
    agg[col] = brand[brand["brand"] == b].set_index("month")["share"]
agg["tpap_vol_share"] = apps[apps["is_tpap"]].groupby("month")["vol_mn"].sum() / app_total
agg["others_share"] = apps[apps["is_other"]].groupby("month")["vol_mn"].sum() / app_total
agg = agg.reset_index()

# --- master ---
m = product.merge(p2p.drop(columns=["total_vol_mn", "total_val_cr"]), on="month", how="outer").merge(agg, on="month", how="outer")
m = m.sort_values("month").reset_index(drop=True)
m["year"] = m["month"].dt.year
m["month_num"] = m["month"].dt.month
m["fy"] = np.where(m["month_num"] >= 4, m["year"], m["year"] - 1)
m["fy"] = m["fy"].astype(str) + "-" + (m["fy"] + 1).astype(str).str[-2:]
m["avg_ticket"] = m["val_cr"] * 10 / m["vol_mn"]
m["vol_yoy"] = m["vol_mn"].pct_change(12)
m["val_yoy"] = m["val_cr"].pct_change(12)
m["vol_mom"] = m["vol_mn"].pct_change()
m["val_mom"] = m["val_cr"].pct_change()
m["ticket_mom"] = m["avg_ticket"].pct_change()
m["days_in_month"] = m["month"].dt.days_in_month
m["vol_per_day"] = m["vol_mn"] / m["days_in_month"]

m.to_csv(r".\data\master_monthly.csv", index=False)
print("master:", m.shape, "|", m["month"].min().date(), "->", m["month"].max().date())
print("non-null months per column:\n", m.notna().sum().to_string())
