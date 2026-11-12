import glob
import pandas as pd

files = sorted(glob.glob(r"..\Product-Statistics-UPI-Product-statistics-upi\*.xlsx"))
print("files:", len(files))

parts = []
for f in files:
    x = pd.read_excel(f, dtype=str)
    x = x.iloc[:, :4]
    x.columns = ["month_raw", "banks_live", "vol_mn", "val_cr"]   # by position
    x["src"] = f.split("\\")[-1]
    parts.append(x)
ps = pd.concat(parts, ignore_index=True).dropna(subset=["month_raw"])

ps["month"] = pd.to_datetime(ps["month_raw"].str.strip(), format="%B-%Y", errors="coerce")
for c in ["banks_live", "vol_mn", "val_cr"]:
    ps[c] = pd.to_numeric(ps[c].str.replace(",", "", regex=False), errors="coerce")

print("unparsed months:", ps[ps["month"].isna()]["month_raw"].tolist())
ps = ps.dropna(subset=["month"]).sort_values("month").reset_index(drop=True)

expected = pd.date_range("2019-04-01", "2026-10-01", freq="MS")
print("months:", len(ps), "(expect 91) | missing:", [m.strftime("%Y-%m") for m in expected if m not in set(ps["month"])])
print("duplicates:", ps["month"].duplicated().sum(), "| nulls:", ps[["banks_live", "vol_mn", "val_cr"]].isna().sum().to_dict())

# MoM jumps >15% worth a manual look
ps["vol_mom"] = ps["vol_mn"].pct_change()
ps["val_mom"] = ps["val_cr"].pct_change()
print("\nMoM jumps over 15%:\n", ps.loc[(ps["vol_mom"].abs() > .15) | (ps["val_mom"].abs() > .15), ["month", "vol_mn", "val_cr", "vol_mom", "val_mom"]])
print("\nApr 2026:", ps.loc[ps["month"] == "2026-04-01", ["vol_mn", "val_cr"]].values.tolist())

# reconcile against P2P/P2M and apps
p = pd.read_csv("upi_p2p_p2m_monthly.csv", parse_dates=["month"])
m = ps.merge(p[["month", "total_vol_mn", "total_val_cr"]], on="month", how="inner")
m["vol_gap"] = (m["vol_mn"] - m["total_vol_mn"]).abs() / m["vol_mn"]
m["val_gap"] = (m["val_cr"] - m["total_val_cr"]).abs() / m["val_cr"]
print("\nvs P2P/P2M total: months compared", len(m), "| off by >0.5%:",
      m.loc[(m["vol_gap"] > .005) | (m["val_gap"] > .005), "month"].dt.strftime("%Y-%m").tolist())

a = pd.read_csv("upi_apps_monthly.csv", parse_dates=["month"]).groupby("month")[["vol_mn", "val_cr"]].sum().reset_index()
r = ps.merge(a, on="month", suffixes=("", "_apps"))
r["vol_ratio"] = r["vol_mn_apps"] / r["vol_mn"]
print("\napps sum / headline volume: min %.3f | max %.3f" % (r["vol_ratio"].min(), r["vol_ratio"].max()))
print(r[["month", "vol_ratio"]].iloc[[0, 6, 12, -13, -1]].to_string(index=False))

ps[["month", "banks_live", "vol_mn", "val_cr"]].to_csv("upi_product_monthly.csv", index=False)
print("\nsaved upi_product_monthly.csv", ps.shape)