import json
import pandas as pd

META = {"id", "created_at", "updated_at", "published_at", "created_by_id",
        "updated_by_id", "product_name", "tab_name", "year", "month", "locale"}

def load(path, extra=None):
    d = json.load(open(path))
    if extra:
        d.update(json.load(open(extra)))
    failed = d.pop("_failed", None)
    return d, failed

def to_numeric_where_possible(df, skip):
    for c in df.columns:
        if c in skip:
            continue
        conv = pd.to_numeric(df[c], errors="coerce")        # "-" becomes NaN
        if conv.notna().sum() >= 0.5 * df[c].notna().sum() > 0:
            df[c] = conv
    return df

# ---------- 1. UPI apps ----------
apps, _ = load("npci_upi-apps.json", "npci_upi-apps_missing.json")
rows = []
for key, recs in apps.items():
    for r in recs:
        name = r.get("application_name") or r.get("upi_application_name")
        vol  = r.get("total_volume_mn")   or r.get("upi_volume_mn")
        val  = r.get("total_value_cr")    or r.get("upi_value_cr")
        rows.append({
            "month": key, "app_raw": name,
            "vol_mn": vol, "val_cr": val,
            "ci_vol_mn": r.get("customer_initiated_transactions_volume_mn"),
            "ci_val_cr": r.get("customer_initiated_transactions_value_cr"),
            "b2c_vol_mn": r.get("b_2_c_transactions_volume_mn"),
            "b2c_val_cr": r.get("b_2_c_transactions_value_cr"),
            "b2b_vol_mn": r.get("b_2_b_transactions_volume_mn"),
            "b2b_val_cr": r.get("b_2_b_transactions_value_cr"),
            "onus_vol_mn": r.get("onus_transactions_volume_mn"),
            "onus_val_cr": r.get("onus_transactions_value_cr"),
        })
df = pd.DataFrame(rows)
print("rows with no app name after fallback:", df["app_raw"].isna().sum())
df = df.dropna(subset=["app_raw"])
df["month"] = pd.to_datetime(df["month"] + "-01")
df["has_hash"] = df["app_raw"].str.strip().str.endswith("#")
df["app"] = df["app_raw"].str.strip().str.rstrip("#").str.strip()
for c in df.columns:
    if c.endswith(("_mn", "_cr")):
        df[c] = pd.to_numeric(df[c].astype("string").str.replace(",", "", regex=False).str.strip(), errors="coerce")
df = df.sort_values(["month", "vol_mn"], ascending=[True, False]).reset_index(drop=True)
df.to_csv("upi_apps_monthly.csv", index=False)

expected = pd.date_range("2020-06-01", "2026-09-01", freq="MS")
have = set(df["month"].unique())
print("APPS:", df.shape, "| months:", df["month"].nunique(),
      "| missing:", [d.strftime("%Y-%m") for d in expected if d not in have])
print("duplicate (month, app):", df.duplicated(["month", "app"]).sum())
g = df.groupby("month").agg(n_apps=("app", "size"), vol_sum=("vol_mn", "sum"))
print(g.tail(3))

