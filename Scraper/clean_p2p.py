import pandas as pd

SRC = r"..\Raw data\upi_p2p_p2m_monthly.csv"
OUT = r"..\cleaning\p2p_p2m_clean.csv"

d = pd.read_csv(SRC, parse_dates=["month"]).sort_values("month").reset_index(drop=True)

parts = d["month_value"].str.extract(r"^([A-Za-z]{3})[A-Za-z]*['\-](\d{2})$")
label = pd.to_datetime(parts[0] + " 20" + parts[1], format="%b %Y", errors="coerce")
print("month_value label mismatches vs month:", int((label != d["month"]).sum()))
d = d.drop(columns="month_value")

cols = ["total_vol_mn", "total_val_cr", "p2p_vol_mn", "p2p_val_cr", "p2m_vol_mn", "p2m_val_cr"]
expected = pd.date_range(d["month"].min(), d["month"].max(), freq="MS")
print("months:", len(d), "|", d["month"].min().date(), "->", d["month"].max().date(),
      "| missing:", [m.strftime("%Y-%m") for m in expected if m not in set(d["month"])],
      "| dup:", int(d["month"].duplicated().sum()))
print("nulls:", int(d[cols].isna().sum().sum()), "| non-positive:", int((d[cols] <= 0).sum().sum()))

for k, (a, b, c) in {"volume": ("p2p_vol_mn", "p2m_vol_mn", "total_vol_mn"), "value": ("p2p_val_cr", "p2m_val_cr", "total_val_cr")}.items():
    gap = (d[a] + d[b] - d[c]).abs() / d[c]
    d[f"{k[:3]}_gap"] = gap
    print(f"{k}: p2p+p2m vs total max gap {gap.max():.4%} | months >0.1%:", d.loc[gap > .001, "month"].dt.strftime("%Y-%m").tolist())

d["p2m_vol_share"] = d["p2m_vol_mn"] / d["total_vol_mn"]
d["p2m_val_share"] = d["p2m_val_cr"] / d["total_val_cr"]
d["p2p_avg_ticket"] = d["p2p_val_cr"] * 10 / d["p2p_vol_mn"]      # cr / mn = Rs 10 per unit -> Rs
d["p2m_avg_ticket"] = d["p2m_val_cr"] * 10 / d["p2m_vol_mn"]
d["avg_ticket"] = d["total_val_cr"] * 10 / d["total_vol_mn"]

for c in ("total_vol_mn", "total_val_cr", "p2p_vol_mn", "p2m_vol_mn"):
    d[f"{c}_mom"] = d[c].pct_change()
jumps = d[(d[["total_vol_mn_mom", "total_val_cr_mom"]].abs() > .15).any(axis=1)]
print("\nMoM jumps >15% (review, not removed):\n", jumps[["month", "total_vol_mn", "total_val_cr", "total_vol_mn_mom", "total_val_cr_mom"]].to_string())
print("\nP2M volume share range: %.1f%% -> %.1f%%" % (d.p2m_vol_share.min() * 100, d.p2m_vol_share.max() * 100))
print("ticket size (Rs) min/max:", round(d.avg_ticket.min()), round(d.avg_ticket.max()))

ps = pd.read_csv(r"..\Raw data\upi_product_monthly.csv", parse_dates=["month"])
m = d.merge(ps, on="month", suffixes=("", "_hl"))
vg = (m["total_vol_mn"] - m["vol_mn"]).abs() / m["vol_mn"]
lg = (m["total_val_cr"] - m["val_cr"]).abs() / m["val_cr"]
print("\nvs product headline: months compared", len(m), "| vol gap max %.3f%% | val gap max %.3f%%" % (vg.max() * 100, lg.max() * 100))
print("off by >0.5%:", m.loc[(vg > .005) | (lg > .005), "month"].dt.strftime("%Y-%m").tolist())

out = d.drop(columns=["vol_gap", "val_gap"] + [c for c in d.columns if c.endswith("_mom")])
out.to_csv(OUT, index=False)
print("\nsaved", OUT, out.shape)
