import json, os
import pandas as pd

d = json.load(open("npci_p2p_raw.json"))
if os.path.exists("npci_p2p_2025-11.json"):
    d.update(json.load(open("npci_p2p_2025-11.json")))
d.pop("_failed", None)

rows = []
for key, resp in sorted(d.items()):
    res = (resp or {}).get("data", {}).get("results", [])
    if len(res) != 1:
        continue                      # months with no data (e.g. 2020-03)
    r = res[0]
    row = {"month": key}
    row.update({k: v for k, v in r.items()
                if k not in {"id", "created_at", "updated_at", "published_at",
                             "created_by_id", "updated_by_id", "product_name",
                             "tab_name", "year", "month", "locale"}})
    rows.append(row)

df = pd.DataFrame(rows)
df["month"] = pd.to_datetime(df["month"] + "-01")

rename = {
    "total_volume_mn": "total_vol_mn", "total_value_cr": "total_val_cr",
    "p_2_p_volume_mn": "p2p_vol_mn",   "p_2_p_value_cr": "p2p_val_cr",
    "p_2_m_volume_mn": "p2m_vol_mn",   "p_2_m_value_cr": "p2m_val_cr",
}
df = df.rename(columns=rename)
for c in rename.values():
    df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False), errors="coerce")

print("months:", len(df), "| first:", df["month"].min().date(), "| last:", df["month"].max().date())
print("null counts:\n", df.isna().sum())

for a, b, c, label in [("p2p_vol_mn", "p2m_vol_mn", "total_vol_mn", "volume"),
                       ("p2p_val_cr", "p2m_val_cr", "total_val_cr", "value")]:
    ok = df[[a, b, c]].notna().all(axis=1)
    gap = (df[a] + df[b] - df[c]).abs() / df[c]
    print(f"{label}: compared {ok.sum()} of {len(df)} months | off by >0.1%:",
          df.loc[ok & (gap > 0.001), "month"].dt.strftime("%Y-%m").tolist())

expected = pd.date_range(df["month"].min(), df["month"].max(), freq="MS")
print("missing months in range:", [m.strftime("%Y-%m") for m in expected if m not in set(df["month"])])

df.to_csv("upi_p2p_p2m_monthly.csv", index=False)
print("saved", df.shape)