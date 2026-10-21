"""
fantasy_adv.py – padziļinātā fantasy statistika visiem laukuma spēlētājiem → sezonas/fantasy_advanced.csv

Viens fails Google Sheets tabulai (caur nhl-feed: https://barakarmy.github.io/nhl-feed/advanced.csv).
Katram spēlētājam trīs periodi: visa sezona (s_), pēdējās 30 dienas (l30_) un 14 dienas (l14_):
  SKAITĪTĀJI: gp, g, a, pts, ppp (punkti vairākumā), sog, hit, blk
  INDIVIDUĀLIE (visas situācijas, bez metieniem tukšos vārtos):
    toi_gp (min), sog60, iff60 (neblokētie mēģinājumi), icf60 (visi mēģinājumi = Corsi),
    ixg60, iscf60 (iespējas, xG ≥ 0.045), ihdcf60 (bīstamās iespējas, xG ≥ 0.09), g_ixg (vārti − ixG = "veiksme")
  ON-ICE 5v5 (no maiņu datiem, sezonas/onice.csv):
    toi5_gp, cf60, ca60, cf_pct, xgf60, xga60, xgf_pct, scf60, sca60, hdcf60, hdca60, pdo (vārtu realizācija + atvairītie)
  ESPN: rostered (% līgu), rostered_7d (izmaiņa 7 dienās), status (ACTIVE / DAY_TO_DAY / OUT / INJURY_RESERVE)

Palaiž ikdienas darbplūsma (pēc onice.py un fantasy_espn.py). Ar roku: python fantasy_adv.py
"""
import os
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import xg as xgm  # noqa: E402

MAPE = os.path.join(BASE, "sezonas")
IZVADE = os.path.join(MAPE, "fantasy_advanced.csv")
IESPEJA, BISTAMS = 0.045, 0.09
PERIODI = (("s_", None), ("l30_", 30), ("l14_", 14))


def _lasit(nos):
    p = os.path.join(MAPE, nos)
    return pd.read_csv(p, encoding="utf-8-sig", low_memory=False) if os.path.exists(p) else None


def _toi(t):
    try:
        m, s = str(t).split(":")
        return int(m) + int(s) / 60
    except ValueError:
        return np.nan


def _r(v, n=2):
    return np.round(v, n)


def periods(sp, m, bl, oi, va, no, lidz, pfx):
    """Viena perioda rādītāji (indekss: playerId)."""
    s = sp[(sp["datums"] >= no) & (sp["datums"] <= lidz)]
    g = s.groupby("playerId").agg(gp=("game_id", "nunique"), G=("goals", "sum"), A=("assists", "sum"), P=("points", "sum"),
                                  SOG=("sog", "sum"), HIT=("hits", "sum"), BLK=("blockedShots", "sum"), TOI=("toi_m", "sum"))
    if va is not None:
        v = va[(va["datums"] >= no) & (va["datums"] <= lidz) & (va["strength"].astype(str).str.lower() == "pp")]
        pp = pd.concat([pd.to_numeric(v[c], errors="coerce") for c in ("scorer_id", "assist1_id", "assist2_id")]).dropna().astype(int).value_counts()
        g["PPP"] = pp.reindex(g.index).fillna(0).astype(int)
    else:
        g["PPP"] = np.nan
    mm = m[(m["datums"] >= no) & (m["datums"] <= lidz)]
    mg = mm.groupby("metejs")
    g["iFF"] = mg.size().reindex(g.index).fillna(0)
    g["ixG"] = mg["xg"].sum().reindex(g.index).fillna(0)
    g["iSC"] = mm[mm["xg"] >= IESPEJA].groupby("metejs").size().reindex(g.index).fillna(0)
    g["iHD"] = mm[mm["xg"] >= BISTAMS].groupby("metejs").size().reindex(g.index).fillna(0)
    if bl is not None:
        b = bl[(bl["datums"] >= no) & (bl["datums"] <= lidz)]
        g["iCF"] = g["iFF"] + b.groupby("metejs").size().reindex(g.index).fillna(0)
    else:
        g["iCF"] = np.nan
    h = (g["TOI"] / 60).where(g["TOI"] > 0)
    out = pd.DataFrame(index=g.index)
    out["gp"] = g["gp"]
    for k in ("G", "A", "P", "PPP", "SOG", "HIT", "BLK"):
        out[k.lower() if k != "P" else "pts"] = g[k]
    out["toi_gp"] = _r(g["TOI"] / g["gp"])
    for k, n in (("SOG", "sog60"), ("iFF", "iff60"), ("iCF", "icf60"), ("ixG", "ixg60"), ("iSC", "iscf60"), ("iHD", "ihdcf60")):
        out[n] = _r(g[k] / h, 3 if n == "ixg60" else 2)
    out["g_ixg"] = _r(g["G"] - g["ixG"])
    if oi is not None:
        o = oi[(oi["datums"] >= no) & (oi["datums"] <= lidz) & (oi["sit"] == "5v5")]
        a = o.groupby("playerId")[["toi", "CF", "CA", "xGF", "xGA", "SCF", "SCA", "HDCF", "HDCA", "GF", "GA", "SF", "SA"]].sum()
        a["gp5"] = o.groupby("playerId")["game_id"].nunique()
        h5 = (a["toi"] / 60).where(a["toi"] > 0)
        a2 = pd.DataFrame(index=a.index)
        a2["toi5_gp"] = _r(a["toi"] / a["gp5"])
        for k, n in (("CF", "cf60"), ("CA", "ca60"), ("xGF", "xgf60"), ("xGA", "xga60"), ("SCF", "scf60"), ("SCA", "sca60"),
                     ("HDCF", "hdcf60"), ("HDCA", "hdca60")):
            a2[n] = _r(a[k] / h5)
        a2["cf_pct"] = _r(a["CF"] / (a["CF"] + a["CA"]).where(a["CF"] + a["CA"] > 0) * 100, 1)
        a2["xgf_pct"] = _r(a["xGF"] / (a["xGF"] + a["xGA"]).where(a["xGF"] + a["xGA"] > 0) * 100, 1)
        sh = a["GF"] / a["SF"].where(a["SF"] > 0)
        sv = 1 - a["GA"] / a["SA"].where(a["SA"] > 0)
        a2["pdo"] = _r((sh + sv) * 100, 1)
        out = out.join(a2)
    return out.add_prefix(pfx)


def main():
    sp = _lasit("speletaji.csv")
    m = _lasit("metieni.csv")
    if sp is None or m is None:
        print("Nav speletaji.csv vai metieni.csv")
        return 1
    sp = sp[sp["pozicija"] != "G"].copy()
    sp["playerId"] = pd.to_numeric(sp["playerId"], errors="coerce")
    sp["toi_m"] = sp["toi"].map(_toi)
    mod = xgm.ielasit_modeli()
    m["xg"] = xgm.xg_varbutibas(m, mod)
    m = m[m["xg"].notna()].copy()                                    # bez tukšajiem vārtiem un metienu sērijas
    m["metejs"] = pd.to_numeric(m["metejs"], errors="coerce")
    bl = _lasit("bloketi.csv")
    if bl is not None:
        bl = bl[pd.to_numeric(bl["tuksi"], errors="coerce").fillna(0) == 0].copy()
        bl["metejs"] = pd.to_numeric(bl["metejs"], errors="coerce")
    va = _lasit("varti.csv")
    oi = _lasit("onice.csv")
    if oi is not None and "SCF" not in oi:
        oi["SCF"], oi["SCA"] = np.nan, np.nan
    lidz = sp["datums"].max()
    pamats = sp.sort_values("datums").groupby("playerId").agg(name=("vards", "last"), team=("team", "last"), pos=("pozicija", "last"))
    dfs = [pamats]
    for pfx, dienas in PERIODI:
        no = sp["datums"].min() if dienas is None else (pd.Timestamp(lidz) - timedelta(days=dienas - 1)).strftime("%Y-%m-%d")
        dfs.append(periods(sp, m, bl, oi, va, no, lidz, pfx))
    t = pd.concat(dfs, axis=1)
    t["rostered"], t["rostered_7d"], t["status"] = np.nan, np.nan, ""
    e = _lasit("fantasy_espn.csv")
    if e is not None:
        e = e[pd.to_numeric(e["playerId"], errors="coerce").notna()].copy()
        e["playerId"] = e["playerId"].astype(int)
        e = e.drop_duplicates("playerId").set_index("playerId")
        t["rostered"] = e["rostered"].reindex(t.index)
        t["status"] = e["trauma"].reindex(t.index) if "trauma" in e else ""
        v = _lasit("fantasy_espn_vesture.csv")
        if v is not None and len(v):
            mer = (pd.Timestamp(e["datums"].max()) - timedelta(days=7)).strftime("%Y-%m-%d")
            vec = v[v["datums"] <= mer].sort_values("datums").drop_duplicates("espn_id", keep="last").set_index("espn_id")["rostered"]
            t["rostered_7d"] = _r(t["rostered"] - e["espn_id"].reindex(t.index).map(vec), 2) if len(vec) else np.nan
    t.index.name = "player_id"
    t = t[t["s_gp"].fillna(0) > 0].reset_index()
    t.insert(4, "stats_through", lidz)
    t = t.sort_values(["rostered", "s_toi_gp"], ascending=False, na_position="last")
    t.to_csv(IZVADE, index=False, encoding="utf-8")
    print(f"fantasy_advanced.csv: {len(t)} spēlētāji, {len(t.columns)} kolonnas, dati līdz {lidz}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
