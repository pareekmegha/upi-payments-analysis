import re
import numpy as np
import pandas as pd

SRC = r"..\Raw data\upi_apps_monthly.csv"
OUT = r"..\cleaning\apps_clean.csv"
MAP_OUT = r"..\cleaning\apps_name_map.csv"

# key = lowercase name with '#', '*', trailing " app(s)" removed. value = canonical name.
# Brand-continuity merges (e.g. Paytm Payments Bank -> Paytm) are deliberate: the series is the brand, not the legal entity.
ALIAS = {
    "whatsapp": "WhatsApp", "omnicard": "OmniCard", "union bank of india": "Union Bank of India",
    "amazonpay": "Amazon Pay", "cred": "Cred", "whatsapp pay": "WhatsApp",
    "paytm payment bank": "Paytm Payments Bank", "paytm payments bank": "Paytm Payments Bank",
    "paytmwallet": "Paytm Payments Bank", "paytm (ocl)": "Paytm",
    "fam": "FamPay", "famapp by trio": "FamPay", "fam app by trio": "FamPay", "fam pay by trio": "FamPay",
    "fampay by trio": "FamPay", "fampay ppi": "FamPay", "fampay": "FamPay",
    "mobikwik ppi": "Mobikwik", "mbk": "Mobikwik",
    "bajaj finserv ppi": "Bajaj Finserv", "bajaj pay wallet": "Bajaj Finserv", "bpaywallet": "Bajaj Finserv",
    "bajaj markets": "Bajaj Finserv", "finserv markets": "Bajaj Finserv",
    "au small finance bank": "AU Small Finance Bank",
    "aditya birla capital digital limited": "Aditya Birla Capital Digital",
    "akudo & muvin (livquik)": "LivQuik", "livquik": "LivQuik", "livquick ppi": "LivQuik",
    "jupiter": "Jupiter", "jupiter money": "Jupiter", "jupiter edge": "Jupiter",
    "jupiter edge (livquick ppi)": "Jupiter", "jupiter edge (livquick ppi app)": "Jupiter",
    "andhra bank one": "Andhra Bank", "dbs bank": "DBS Digibank", "deustche bank": "Deutsche Bank",
    "equitas small": "Equitas Small Finance Bank", "fedral bank": "Federal Bank", "fifederal": "Fi Money",
    "idfc bank": "IDFC First Bank", "idfc first bank": "IDFC First Bank",
    "indie": "Indie (IndusInd)", "indie - indus ind": "Indie (IndusInd)",
    "janta sahakari bank": "Janata Sahakari Bank", "kiwi": "Kiwi", "go kiwi": "Kiwi", "gokiwi": "Kiwi",
    "kredit pe": "Kredit.Pe", "freo money": "Freo", "go niyo": "Niyo", "goniyo ppi": "Niyo", "niyo global": "Niyo",
    "makemy trip": "MakeMyTrip", "omni": "OmniCard", "omni card": "OmniCard", "omnicard ppi": "OmniCard",
    "punjab and sind bank": "Punjab & Sind Bank", "punjab sind bank": "Punjab & Sind Bank",
    "punjab sindh bank": "Punjab & Sind Bank", "rapi pay": "Rapipay", "rblbank": "RBL Bank",
    "sbi bank": "State Bank of India", "shriram": "Shriram One", "shri ram one": "Shriram One",
    "slice small finance bank": "Slice", "slice ppi": "Slice",
    "suryoday": "Suryoday Small Finance Bank", "suryoday bank": "Suryoday Small Finance Bank",
    "tataneu": "Tata Neu", "union bank": "Union Bank of India", "vijya bank": "Vijaya Bank",
    "naviaxis": "Navi", "dhani ppi": "Dhani", "digikhata ppi": "Digikhata", "transerv ppi": "Transerv",
    "flipkart upi": "Flipkart", "lxme upi": "LXME", "cbdc": "CBDC",
    "hsbc bank": "HSBC", "standard chartered bank": "Standard Chartered", "citi bank": "Citi Bank",
    "other": "Others", "other apps": "Others", "other bank apps": "Others",
    "pinelabs": "Pine Labs", "eroute": "Eroute", "obopay": "Obopay",
}

JUNK = re.compile("[#*�]")


def key(name):
    s = JUNK.sub("", name)
    s = re.sub(r"\s+", " ", s).strip().casefold()
    s = re.sub(r"\s+\)", ")", s)
    return re.sub(r"\s+apps?$", "", s)


if __name__ == "__main__":
    d = pd.read_csv(SRC, parse_dates=["month"], encoding="utf-8")
    d["key"] = d["app_raw"].map(key)
    shown = d["app_raw"].map(lambda s: JUNK.sub("", s).strip())
    top = (d.assign(w=d["vol_mn"].fillna(0), shown=shown).groupby(["key", "shown"])["w"].sum()
             .reset_index().sort_values(["key", "w"], ascending=[True, False]).drop_duplicates("key").set_index("key")["shown"])
    default = top.str.replace(r"\s+Apps?$", "", regex=True)
    d["app_clean"] = d["key"].map(lambda k: ALIAS.get(k, default[k]))

    names = pd.Series(d["app_clean"].unique())
    squashed = names.map(lambda n: re.sub(r"[^a-z0-9]", "", n.casefold()))
    assert not squashed.duplicated().any(), names[squashed.duplicated(keep=False)].tolist()

    name_map = d[["app_raw", "app_clean"]].drop_duplicates().sort_values(["app_clean", "app_raw"])
    try:
        name_map.to_csv(MAP_OUT, index=False)
    except PermissionError:
        MAP_OUT = MAP_OUT.replace(".csv", ".new.csv")
        name_map.to_csv(MAP_OUT, index=False)
        print("WARNING: apps_name_map.csv is locked (open in Excel?); wrote", MAP_OUT)

    flows = [c for c in d.columns if c.endswith(("_mn", "_cr"))]
    g = d.groupby(["month", "app_clean"], as_index=False).agg(
        **{c: (c, lambda x: x.sum(min_count=1)) for c in flows},
        is_tpap_reported=("has_hash", "max"), n_source_rows=("app_raw", "size"))
    print("rows:", len(d), "->", len(g), "| names:", d["app_raw"].nunique(), "raw ->", g["app_clean"].nunique(), "clean")
    print("month+app collisions summed:", int((g["n_source_rows"] > 1).sum()))

    # NPCI only started marking '#' in 2024-02; apps flagged then were TPAPs earlier too.
    flagged = set(g.loc[g["is_tpap_reported"], "app_clean"])
    g["is_tpap"] = g["is_tpap_reported"] | g["app_clean"].isin(flagged)
    g["is_other"] = g["app_clean"].eq("Others")
    # Paytm Payments Bank (PPBL, to 2024-01) and Paytm (One97/OCL TPAP, from 2024-02) are different entities;
    # `brand` lets you roll them up when you want brand-level trends.
    g["brand"] = g["app_clean"].replace({"Paytm Payments Bank": "Paytm"})
    g = g.rename(columns={"app_clean": "app"}).sort_values(["month", "vol_mn"], ascending=[True, False]).reset_index(drop=True)

    # Source publishes the literal string "NaN" as total for some rows. With no B2C/B2B/on-us components,
    # total == customer-initiated. (The component-sum identity does not hold after mid-2025, so no wider fill.)
    for t in ("vol_mn", "val_cr"):
        no_parts = g[[f"b2c_{t}", f"b2b_{t}", f"onus_{t}"]].isna().all(axis=1)
        fill = g[t].isna() & g[f"ci_{t}"].notna() & no_parts
        g[f"{t}_imputed"] = fill
        g.loc[fill, t] = g.loc[fill, f"ci_{t}"]
        print(f"imputed {t} from customer-initiated:", int(fill.sum()))

    # Headline UPI volume excludes on-us; NPCI's app "total" includes it. ci + b2c + b2b reconciles to the headline
    # (ratio 1.000 for 2020-12..2023), so market shares should use this column, not vol_mn.
    g["vol_settled_mn"] = np.where(g["ci_vol_mn"].notna(),
                                   g["ci_vol_mn"] + g["b2c_vol_mn"].fillna(0) + g["b2b_vol_mn"].fillna(0), g["vol_mn"])

    print("\nnulls:\n", g[flows].isna().sum().to_string())
    print("\nnull vol/val rows:\n", g[g["vol_mn"].isna() | g["val_cr"].isna()][["month", "app", "vol_mn", "val_cr"]].to_string())
    print("\nnegative values:", int((g[flows] < 0).sum().sum()))

    ps = pd.read_csv(r"..\Raw data\upi_product_monthly.csv", parse_dates=["month"])
    r = g.groupby("month")[["vol_mn", "val_cr"]].sum().reset_index().merge(ps, on="month", suffixes=("_apps", ""))
    r["vol_ratio"] = r["vol_mn_apps"] / r["vol_mn"]
    r["val_ratio"] = r["val_cr_apps"] / r["val_cr"]
    print("\napps sum / headline: vol %.3f-%.3f | val %.3f-%.3f" % (r.vol_ratio.min(), r.vol_ratio.max(), r.val_ratio.min(), r.val_ratio.max()))
    print(r.loc[((r.vol_ratio - 1).abs() > .02) | ((r.val_ratio - 1).abs() > .02), ["month", "vol_ratio", "val_ratio"]].to_string())

    rs = g.groupby("month")["vol_settled_mn"].sum().reset_index().merge(ps, on="month", suffixes=("_s", ""))
    rs["ratio"] = rs["vol_settled_mn"] / rs["vol_mn"]
    print("settled volume / headline: min %.3f max %.3f | months within 2%%: %d of %d" % (rs.ratio.min(), rs.ratio.max(), ((rs.ratio - 1).abs() <= .02).sum(), len(rs)))

    g.drop(columns=["is_tpap_reported", "n_source_rows"]).to_csv(OUT, index=False)
    print("\nsaved", OUT, g.shape)
