"""
Datu ielāde un sagatavošana NHL lietotnei (bez Streamlit atkarības, lai kodu var testēt atsevišķi).

Datu avoti (mapē "sezonas" blakus šim failam, ko raksta nhl_dati.py; iepriekšējās sezonas – sezonas/vesture/<sezona>/):
  speles.csv, speletaji.csv, vartsargi.csv, varti.csv
Kalendārs: sezonas/nhl_kalendars.csv (ko raksta kalendars.py).
Ja speles.csv vēl nav, tiek izmantots vecais nhl_sezona.csv.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
# Aktīvās sezonas faili: sezonas/ (pārejas laikā, ja tur vēl nav speles.csv, tiek lasīta vecā mape dati/)
DATU_MAPE = BASE / "sezonas" if (BASE / "sezonas" / "speles.csv").exists() or not (BASE / "dati").exists() else BASE / "dati"
VESTURES_MAPE = BASE / "sezonas" / "vesture"         # iepriekšējās sezonas: sezonas/vesture/<sezona>/ (piem., 20252026), tie paši CSV
LV_TZ = ZoneInfo("Europe/Riga")

KOMANDAS = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes", "CHI": "Chicago Blackhawks",
    "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montreal Canadiens",
    "NSH": "Nashville Predators", "NJD": "New Jersey Devils", "NYI": "New York Islanders",
    "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks", "SEA": "Seattle Kraken",
    "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Mammoth", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
    "WSH": "Washington Capitals", "WPG": "Winnipeg Jets",
}
DIENAS = {0: "Pirmdiena", 1: "Otrdiena", 2: "Trešdiena", 3: "Ceturtdiena",
          4: "Piektdiena", 5: "Sestdiena", 6: "Svētdiena"}

TEKSTA_KOL = {"datums", "home_team", "away_team", "sakums_utc", "arena",
              "spele_beidzas", "uzvaretajs", "star1", "star2", "star3"}
PAPILDU_SKAITLI = {
    "speletaji": ("numurs", "goals", "assists", "points", "plusMinus", "pim", "hits", "powerPlayGoals",
                  "sog", "faceoffWinningPctg", "blockedShots", "shifts", "giveaways", "takeaways"),
    "vartsargi": ("numurs", "shotsAgainst", "saves", "goalsAgainst", "savePctg", "pim"),
    "varti": (),
    "tiesnesi": ("pen_home", "pen_away", "pen_total", "pim_home", "pim_away"),
}


# ----------------------------------------------------------------------------
# PALĪGFUNKCIJAS
# ----------------------------------------------------------------------------
def pilns_nosaukums(kods):
    return KOMANDAS.get(str(kods).upper(), str(kods).upper())


def logo_url(kods):
    return f"https://assets.nhle.com/logos/nhl/svg/{str(kods).upper()}_light.svg"


def sodien_lv():
    return datetime.now(LV_TZ).date()


def beigu_etikete(beigas):
    return {"OT": "OT", "SO": "SO", "OT/SO": "OT/SO"}.get(str(beigas), "")


def datu_versija():
    """Faila izmaiņu laiki (kešatmiņas atslēga: kad fails mainās, dati tiek pārlasīti)."""
    celi = [DATU_MAPE / n for n in ("speles.csv", "speletaji.csv", "vartsargi.csv", "varti.csv", "pedeja_atjaunosana.json",
                                    "tiesnesi.csv", "tiesnesi_pagajusa.csv", "referees_lastseason.csv", "tiesnesi_planotie.csv")]
    celi += [DATU_MAPE / "nhl_kalendars.csv", VESTURES_MAPE / "referees_lastseason.csv",
             BASE / "nhl_sezona.csv", BASE / "nhl_kalendars.csv", BASE / "referees_lastseason.csv"]
    return tuple(c.stat().st_mtime if c.exists() else 0 for c in celi)


def _lv_laiks(df, utc_kol, datuma_kol):
    """Atgriež (sākuma laiks Rīgas laikā, datums pēc Rīgas laika). Bez UTC laika: ASV datums + 1 diena."""
    if utc_kol in df.columns:
        sakums = pd.to_datetime(df[utc_kol], utc=True, errors="coerce").dt.tz_convert(LV_TZ)
    else:
        sakums = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]").dt.tz_convert(LV_TZ)
    datums_lv = sakums.dt.normalize().dt.tz_localize(None)
    rezerve = pd.to_datetime(df[datuma_kol], errors="coerce") + pd.Timedelta(days=1)
    return sakums, datums_lv.fillna(rezerve)


# ----------------------------------------------------------------------------
# IELĀDE
# ----------------------------------------------------------------------------
TIPS_RS, TIPS_PO = "RS", "PO"       # regulārā sezona / play-off (statistika vienmēr tiek skaitīta atsevišķi)


def ielasit_speles():
    """Viena rinda uz spēli; pievieno 'sakums_lv' un 'datums_lv' (Rīgas laiks)."""
    fails = next((c for c in (DATU_MAPE / "speles.csv", BASE / "nhl_sezona.csv") if c.exists()), None)
    if fails is None:
        return None
    df = pd.read_csv(fails)
    if df.empty or "datums" not in df.columns:
        return None
    for c in df.columns:
        if c not in TEKSTA_KOL:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["datums"] = pd.to_datetime(df["datums"], errors="coerce")
    df = df.dropna(subset=["datums"]).copy()
    df["sakums_lv"], df["datums_lv"] = _lv_laiks(df, "sakums_utc", "datums")

    if "spele_beidzas" not in df.columns:   # vecais formāts: secinām no vārtiem
        def reg(p):
            return df[[f"{p}_p1", f"{p}_p2", f"{p}_p3"]].fillna(0).sum(axis=1)
        ot = ((df["home_ot"].fillna(0) + df["away_ot"].fillna(0)) > 0) | \
             (df["home_total"] != reg("home")) | (df["away_total"] != reg("away"))
        df["spele_beidzas"] = np.where(ot, "OT/SO", "REG")
    df["spele_beidzas"] = df["spele_beidzas"].fillna("REG")
    # sezona un spēles tips: NHL gameType 2 = regulārā sezona (RS), 3 = play-off (PO); trūkstošās vērtības – RS un pēc datuma aprēķināta sezona
    gads = df["datums"].dt.year
    sez_pec_datuma = np.where(df["datums"].dt.month >= 7, gads * 10000 + gads + 1, (gads - 1) * 10000 + gads)
    df["sezona"] = pd.to_numeric(df["sezona"], errors="coerce").fillna(pd.Series(sez_pec_datuma, index=df.index)).astype(int) \
        if "sezona" in df.columns else sez_pec_datuma
    tips_kods = pd.to_numeric(df["speles_tips"], errors="coerce") if "speles_tips" in df.columns else pd.Series(np.nan, index=df.index)
    df["tips"] = np.where(tips_kods == 3, TIPS_PO, TIPS_RS)
    return df.sort_values(["datums_lv", "sakums_lv", "game_id"]).reset_index(drop=True)


def ielasit_kalendaru():
    c = next((c for c in (DATU_MAPE / "nhl_kalendars.csv", BASE / "nhl_kalendars.csv") if c.exists()), None)
    if c is None:
        return None
    df = pd.read_csv(c)
    if df.empty:
        return None
    df["sakums_lv"], df["datums_lv"] = _lv_laiks(df, "sakuma_laiks_utc", "datums")
    return df.sort_values(["sakums_lv", "game_id"]).reset_index(drop=True)


def ielasit_tabulu(nos):
    """Papildu tabulas (speletaji, vartsargi, varti); None, ja faila vēl nav."""
    c = DATU_MAPE / f"{nos}.csv"
    if not c.exists():
        return None
    df = pd.read_csv(c)
    if df.empty:
        return None
    for k in PAPILDU_SKAITLI.get(nos, ()):
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce")
    return df


def nakamas_speles(kal, n=7, komanda=None):
    if kal is None or kal.empty:
        return pd.DataFrame()
    x = kal[kal["datums_lv"].dt.date >= sodien_lv()]
    if komanda:
        x = x[(x["majas_komanda"] == komanda) | (x["viesu_komanda"] == komanda)]
    return x.head(n)


# ----------------------------------------------------------------------------
# KOMANDU TABULA (viena rinda = komanda vienā spēlē)
# ----------------------------------------------------------------------------
def _kol(df, nos):
    return df[nos] if nos in df.columns else pd.Series(np.nan, index=df.index)


def _komandas_puse(df, puse, pret):
    def p(nos):
        return _kol(df, f"{puse}_{nos}")

    def q(nos):
        return _kol(df, f"{pret}_{nos}")

    d = pd.DataFrame({
        "datums": df["datums_lv"], "sakums": df["sakums_lv"], "game_id": df["game_id"],
        "komanda": df[f"{puse}_team"], "pretinieks": df[f"{pret}_team"],
        "majas": 1 if puse == "home" else 0,
        "beigas": df["spele_beidzas"],
        "tips": _kol(df, "tips").fillna(TIPS_RS), "sezona": _kol(df, "sezona"),
        "g_tot": p("total"), "z_tot": q("total"),
        "sog_tot": p("sog_total"), "sog_pret": q("sog_total"),
        "ppg": p("ppg"), "pp_sog": p("pp_sog"), "pp_opp": p("pp_opp"),
        "pim_tot": p("pim_total"), "pen_count": p("pen_count"), "pen_draw": q("pen_count"),
        "draw_pim_tot": q("pim_total"),
        "hits": p("hits"), "blocked": p("blocked_shots"),
        "giveaways": p("giveaways"), "takeaways": p("takeaways"), "fo_pct": p("faceoff_pct"),
    })
    for n in (1, 2, 3):
        d[f"g_p{n}"] = p(f"p{n}")
        d[f"z_p{n}"] = q(f"p{n}")
        d[f"sog_p{n}"] = p(f"sog_p{n}")
        d[f"sog_pret_p{n}"] = q(f"sog_p{n}")
        d[f"pim_p{n}"] = p(f"pim_p{n}")
        d[f"pen_p{n}"] = p(f"pen_p{n}")            # sodu skaits periodā (jaunajos datos)
        d[f"draw_pim_p{n}"] = q(f"pim_p{n}")       # pretinieka sodu minūtes periodā
        d[f"draw_p{n}"] = q(f"pen_p{n}")           # pretinieka sodu skaits periodā
    return d


def sagatavot_vienoto_tabulu(df):
    if df is None or df.empty:
        return pd.DataFrame()
    c = pd.concat([_komandas_puse(df, "home", "away"), _komandas_puse(df, "away", "home")], ignore_index=True)

    for n in (1, 2, 3):
        c[f"diff_p{n}"] = c[f"g_p{n}"] - c[f"z_p{n}"]
    c["g_reg"] = c[["g_p1", "g_p2", "g_p3"]].sum(axis=1)
    c["z_reg"] = c[["z_p1", "z_p2", "z_p3"]].sum(axis=1)
    c["tot_reg_goals"] = c["g_reg"] + c["z_reg"]
    c["sog_reg"] = c[["sog_p1", "sog_p2", "sog_p3"]].sum(axis=1)
    c["pim_reg"] = c[["pim_p1", "pim_p2", "pim_p3"]].sum(axis=1)

    # Statistikā tiek lietots tikai pamatlaiks (1.-3. periods); papildlaiks tiek tikai saglabāts vizuālai attēlošanai.
    # noraidījumu skaits pa periodiem: precīzs no jaunajiem datiem, citādi sodu minūtes / 2 (vecais formāts)
    for n in (1, 2, 3):
        c[f"pen_p{n}"] = c[f"pen_p{n}"].where(c[f"pen_p{n}"].notna(), (c[f"pim_p{n}"] / 2).round())
        c[f"draw_p{n}"] = c[f"draw_p{n}"].where(c[f"draw_p{n}"].notna(), (c[f"draw_pim_p{n}"] / 2).round())
    c["pim_count"] = c[["pen_p1", "pen_p2", "pen_p3"]].sum(axis=1).fillna(0).astype(int)      # sodu skaits pamatlaikā
    c["draw_pim_reg"] = c[["draw_pim_p1", "draw_pim_p2", "draw_pim_p3"]].sum(axis=1)        # pretinieka sodu minūtes pamatlaikā
    c["sog_pret_reg"] = c[["sog_pret_p1", "sog_pret_p2", "sog_pret_p3"]].sum(axis=1)        # pretinieka metieni pamatlaikā

    pret_sk = c[["game_id", "komanda", "pim_count"]].rename(columns={"komanda": "pretinieks", "pim_count": "_pret_sk"})
    c = c.merge(pret_sk, on=["game_id", "pretinieks"], how="left")
    c["pen_draw"] = c["_pret_sk"]          # izcīnītie noraidījumi = pretinieka noraidījumi pamatlaikā
    c = c.drop(columns="_pret_sk")

    uzvara = c["g_tot"] > c["z_tot"]
    papildl = c["beigas"].isin(["OT", "SO", "OT/SO"]) & (c["tips"] != TIPS_PO)        # play-off nav OT loss: zaudējums ir zaudējums
    c["rez"] = np.where(uzvara, "W", np.where(papildl, "OTL", "L"))
    c["pts"] = c["rez"].map({"W": 2, "OTL": 1, "L": 0})

    pret = c[["game_id", "komanda", "ppg", "pp_opp"]].rename(
        columns={"komanda": "pretinieks", "ppg": "ppg_allowed", "pp_opp": "pp_opp_pret"})
    c = c.merge(pret, on=["game_id", "pretinieks"], how="left")
    c["pilns_nosaukums"] = c["komanda"].map(pilns_nosaukums)
    return c.sort_values(["komanda", "datums", "game_id"]).reset_index(drop=True)


def filtret(df, scope="Visas", n=None):
    """scope: Visas / Mājās / Izbraukumā; n: pēdējās n spēles katrai komandai (pēc scope filtra)."""
    sub = df
    if scope == "Mājās":
        sub = sub[sub["majas"] == 1]
    elif scope == "Izbraukumā":
        sub = sub[sub["majas"] == 0]
    if n:
        sub = sub.groupby("komanda").tail(n)
    return sub


def _dala(a, b):
    return a / b.where(b > 0) * 100


def kopsavilkums(df, scope="Visas", n=None):
    """Komandu kopsavilkums (indekss = komanda). Visi rādītāji ir pamatlaika (1.-3. periods), bez papildlaika (OT/SO)."""
    sub = filtret(df, scope, n)
    if sub.empty:
        return pd.DataFrame()
    s = sub.assign(
        w=(sub["rez"] == "W").astype(int), l=(sub["rez"] == "L").astype(int),
        otl=(sub["rez"] == "OTL").astype(int), over65=(sub["tot_reg_goals"] > 6.5).astype(int),
        over55=(sub["tot_reg_goals"] > 5.5).astype(int))
    g = s.groupby("komanda")
    out = pd.DataFrame({
        "GP": g.size(),
        "W": g["w"].sum(), "L": g["l"].sum(), "OTL": g["otl"].sum(), "PTS": g["pts"].sum(),
        "G": g["g_reg"].sum(), "Z": g["z_reg"].sum(),
        "G_sp": g["g_reg"].mean(), "Z_sp": g["z_reg"].mean(),
        "SOG_sp": g["sog_reg"].mean(), "SA_sp": g["sog_pret_reg"].mean(),
        "PPG": g["ppg"].sum(), "PP_opp": g["pp_opp"].sum(min_count=1), "PP_sog": g["pp_sog"].sum(),
        "PPG_pret": g["ppg_allowed"].sum(), "PP_opp_pret": g["pp_opp_pret"].sum(min_count=1),
        "PEN_sp": g["pim_count"].mean(), "PIM_sp": g["pim_reg"].mean(), "DRAW_sp": g["pen_draw"].mean(),
        "Over65": g["over65"].mean() * 100,
        "Over55": g["over55"].mean() * 100,
    })
    for p in (1, 2, 3):
        out[f"G_p{p}"] = g[f"g_p{p}"].mean()
        out[f"Z_p{p}"] = g[f"z_p{p}"].mean()
    out["Starpiba"] = out["G"] - out["Z"]
    out["PTS_pct"] = out["PTS"] / (2 * out["GP"]) * 100
    sog_s, sa_s = g["sog_reg"].sum(), g["sog_pret_reg"].sum()
    out["SOG_dala"] = sog_s / (sog_s + sa_s).where((sog_s + sa_s) > 0) * 100
    out["PP_pct"] = _dala(out["PPG"], out["PP_opp"])
    out["PK_pct"] = 100 - _dala(out["PPG_pret"], out["PP_opp_pret"])
    out["PEN_starpiba"] = out["DRAW_sp"] - out["PEN_sp"]
    return out


def _nor_kolonna(metrika, veids, perioda):
    """Bāzes tabulas kolonna: metrika 'skaits'/'minutes', veids 'sanemtie'/'izcinitie', perioda 'kopa'/1/2/3."""
    i = 0 if metrika == "skaits" else 1
    sanemtie = {"kopa": ("pim_count", "pim_reg"), 1: ("pen_p1", "pim_p1"), 2: ("pen_p2", "pim_p2"), 3: ("pen_p3", "pim_p3")}
    izcinitie = {"kopa": ("pen_draw", "draw_pim_reg"), 1: ("draw_p1", "draw_pim_p1"),
                 2: ("draw_p2", "draw_pim_p2"), 3: ("draw_p3", "draw_pim_p3")}
    return (sanemtie if veids == "sanemtie" else izcinitie)[perioda][i]


def noraidijumu_tabula(df, scope="Visas", n=None, metrika="skaits", videji=True):
    """
    Noraidījumi pa periodiem (indekss = komanda). Katram periodam (kopa, 1, 2, 3) kolonnas:
      s_<p> = saņemtie (paša komandas), i_<p> = izcīnītie (pretinieka noraidījumi), r_<p> = izcīnītie - saņemtie.
    metrika: 'skaits' (sodu skaits) vai 'minutes' (sodu minūtes); videji: vidēji spēlē (True) vai kopsumma (False).
    """
    sub = filtret(df, scope, n)
    if sub.empty:
        return pd.DataFrame()
    g = sub.groupby("komanda")
    out = pd.DataFrame({"GP": g.size()})
    for p in ("kopa", 1, 2, 3):
        for kods, veids in (("s", "sanemtie"), ("i", "izcinitie")):
            kol = _nor_kolonna(metrika, veids, p)
            out[f"{kods}_{p}"] = g[kol].mean() if videji else g[kol].sum()
        out[f"r_{p}"] = out[f"i_{p}"] - out[f"s_{p}"]
    return out


def periodu_tabula(df, p, scope="Visas", n=None):
    sub = filtret(df, scope, n)
    if sub.empty:
        return pd.DataFrame()
    g = sub.groupby("komanda")
    out = pd.DataFrame({
        "GP": g.size(),
        "G": g[f"g_p{p}"].sum(), "Z": g[f"z_p{p}"].sum(),
        "G_sp": g[f"g_p{p}"].mean(), "Z_sp": g[f"z_p{p}"].mean(),
        "SOG_sp": g[f"sog_p{p}"].mean(), "SA_sp": g[f"sog_pret_p{p}"].mean(),
    })
    out["Starpiba"] = out["G"] - out["Z"]
    return out


def over_under(df, linija=6.5, scope="Visas", n=10):
    sub = filtret(df, scope, n)
    if sub.empty:
        return pd.DataFrame()
    s = sub.assign(over=(sub["tot_reg_goals"] > linija).astype(int),
                   under=(sub["tot_reg_goals"] < linija).astype(int))
    g = s.groupby("komanda")
    out = pd.DataFrame({
        "GP": g.size(), "Over": g["over"].sum(), "Under": g["under"].sum(),
        "Vid_kopa": g["tot_reg_goals"].mean(),
    })
    out["Over_pct"] = out["Over"] / out["GP"] * 100
    out["Under_pct"] = out["Under"] / out["GP"] * 100
    return out


# ----------------------------------------------------------------------------
# SPĒLĒTĀJI
# ----------------------------------------------------------------------------
def toi_minutes(x):
    try:
        m, s = str(x).split(":")
        return int(m) + int(s) / 60
    except (ValueError, AttributeError):
        return np.nan


def speletaju_lideri(sk):
    if sk is None or sk.empty:
        return pd.DataFrame()
    x = sk.assign(toi_min=sk["toi"].map(toi_minutes))
    out = x.groupby("playerId").agg(
        Speletajs=("vards", "last"), Komanda=("team", "last"), Poz=("pozicija", "last"),
        GP=("game_id", "nunique"), G=("goals", "sum"), A=("assists", "sum"), P=("points", "sum"),
        PM=("plusMinus", "sum"), PIM=("pim", "sum"), SOG=("sog", "sum"), HIT=("hits", "sum"),
        BLK=("blockedShots", "sum"), PPG=("powerPlayGoals", "sum"), TOI=("toi_min", "mean"))
    out["P_sp"] = out["P"] / out["GP"]
    return out.reset_index()


def vartsargu_lideri(vg):
    if vg is None or vg.empty:
        return pd.DataFrame()
    x = vg.assign(
        toi_min=vg["toi"].map(toi_minutes),
        sak=vg["starter"].astype(str).str.lower().eq("true").astype(int),
        uzv=vg["decision"].astype(str).eq("W").astype(int))
    x = x[x["toi_min"] > 0]                  # rezerves vārtsargi, kas bija pieteikti, bet nespēlēja (TOI 00:00), netiek skaitīti kā aizvadīta spēle
    if x.empty:
        return pd.DataFrame()
    out = x.groupby("playerId").agg(
        Vartsargs=("vards", "last"), Komanda=("team", "last"),
        GP=("game_id", "nunique"), GS=("sak", "sum"), W=("uzv", "sum"),
        SA=("shotsAgainst", "sum"), SV=("saves", "sum"), GA=("goalsAgainst", "sum"),
        TOI=("toi_min", "sum"))
    out["SVpct"] = out["SV"] / out["SA"].where(out["SA"] > 0) * 100
    out["GAA"] = out["GA"] * 60 / out["TOI"].where(out["TOI"] > 0)
    return out.reset_index()


# ----------------------------------------------------------------------------
# TIESNEŠI
# ----------------------------------------------------------------------------
# Pagājušās sezonas fails: sezonas/vesture/referees_lastseason.csv (vai sezonas/referees_lastseason.csv, vai tas pats fails saknē)
TIESNESU_METRIKAS = ("kopa", "majas", "viesi", "p1", "p2", "p3")   # noraidījumi spēlē: kopā, mājas, viesu komanda, pa periodiem

_ALIASI = {
    "vards": ("vards", "name", "referee", "official", "tiesnesis", "tiesnesa_vards"),
    "speles": ("speles", "gp", "games", "games_count", "games_officiated"),
    "liga": ("league_avg_default", "league_avg", "liga_vid"),
}
# metrika: (kolonnas ar kopsummu / vērtību spēlē, kolonnas ar vidējo spēlē)
_METR_ALIASI = {
    "kopa": (("noraid_kopa", "penalties", "total_penalties", "pen_total", "noraidijumi_kopa"),
             ("noraid_sp", "pen_per_game", "penalties_per_game", "noraidijumi_spele", "avg_pen_per_game")),
    "majas": (("noraid_majas", "home_penalties", "pen_home"), ("home_avg", "avg_home_pen")),
    "viesi": (("noraid_viesi", "away_penalties", "pen_away"), ("away_avg", "avg_away_pen")),
    "p1": (("pen_p1",), ("p1_avg", "avg_p1")),
    "p2": (("pen_p2",), ("p2_avg", "avg_p2")),
    "p3": (("pen_p3",), ("p3_avg", "avg_p3")),
}


def _pagajusie_faili():
    return (VESTURES_MAPE / "referees_lastseason.csv", DATU_MAPE / "referees_lastseason.csv", DATU_MAPE / "tiesnesi_pagajusa.csv",
            BASE / "referees_lastseason.csv")


def atslega(vards):
    """Vārda atslēga salīdzināšanai: pirmais burts + uzvārds ('Wes McCauley' = 'W. McCauley')."""
    s = unicodedata.normalize("NFKD", str(vards)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z\s]", " ", s.replace("'", ""))          # defise kā atstarpe: 'Samuels-Thomas' = 'Samuels Thomas'; apostrofi tiek izmesti
    dalas = [d for d in s.split() if d not in ("jr", "sr", "ii", "iii")]
    return f"{dalas[0][0]} {dalas[-1]}" if dalas else ""


def ielasit_pagajuso_tiesnesus():
    """
    Pagājušās sezonas tiesnešu dati. Atgriež (DataFrame vai None, paziņojums).
    DataFrame kolonnas: key, vards, GP, kopa, majas, viesi, p1, p2, p3, liga_kopa
    (noraidījumi spēlē vidēji; kolonnas, kuru failā nav, ir NaN).
    Formāts A (viena rinda uz tiesnesi): referee, games_count, avg_pen_per_game, p1_avg, p2_avg, p3_avg, league_avg_default
    Formāts B (viena rinda uz spēli un tiesnesi): vards, game_id, pen_total [, pen_home, pen_away, pen_p1..3]
    """
    fails = next((c for c in _pagajusie_faili() if c.exists()), None)
    if fails is None:
        return None, ""
    df = pd.read_csv(fails)
    df.columns = [str(c).strip().lower() for c in df.columns]

    def kol(aliasi):
        return next((c for c in df.columns if c in aliasi), None)

    sagaidamas = "referee, games_count, avg_pen_per_game (neobligāti p1_avg, p2_avg, p3_avg, league_avg_default)"
    k_vards, k_speles, k_liga = kol(_ALIASI["vards"]), kol(_ALIASI["speles"]), kol(_ALIASI["liga"])
    if k_vards is None:
        return None, f"Pagājušās sezonas failā ({fails.name}) nav kolonnas ar tiesneša vārdu. Sagaidāmās kolonnas: {sagaidamas}."
    par_spele = "game_id" in df.columns
    if not par_spele and k_speles is None:
        return None, f"Pagājušās sezonas failā ({fails.name}) nav spēļu skaita kolonnas. Sagaidāmās kolonnas: {sagaidamas}."

    df["key"] = df[k_vards].map(atslega)
    df = df[df["key"] != ""].copy()
    gp = pd.to_numeric(df[k_speles], errors="coerce") if k_speles else pd.Series(np.nan, index=df.index)
    vert = {}
    for m, (summ, vid) in _METR_ALIASI.items():
        c_sum, c_vid = kol(summ), kol(vid)
        if c_sum:
            vert[m] = pd.to_numeric(df[c_sum], errors="coerce")
        elif c_vid and not par_spele:
            vert[m] = pd.to_numeric(df[c_vid], errors="coerce") * gp      # vidējais × spēles = kopsumma
    if "kopa" not in vert:
        return None, f"Pagājušās sezonas failā ({fails.name}) nav noraidījumu kolonnas. Sagaidāmās kolonnas: {sagaidamas}."

    d = pd.DataFrame({"key": df["key"], "vards": df[k_vards], **vert})
    if par_spele:                                    # formāts B
        d["game_id"] = df["game_id"]
        g = d.groupby("key")
        out = pd.DataFrame({"vards": g["vards"].last(), "GP": g["game_id"].nunique()})
        for m in TIESNESU_METRIKAS:
            out[m] = g[m].mean() if m in vert else np.nan
    else:                                            # formāts A
        d["GP"] = gp
        d = d[d["GP"] > 0]
        g = d.groupby("key")
        out = pd.DataFrame({"vards": g["vards"].last(), "GP": g["GP"].sum()})
        for m in TIESNESU_METRIKAS:
            out[m] = g[m].sum(min_count=1) / out["GP"] if m in vert else np.nan
    liga = pd.to_numeric(df[k_liga], errors="coerce").dropna() if k_liga else pd.Series(dtype=float)
    out["liga_kopa"] = float(liga.iloc[0]) if not liga.empty else np.nan
    return out.reset_index(), ""


def _kol(df, nos):
    return df[nos] if nos in df.columns else pd.Series(np.nan, index=df.index)


_TEK_KOL = {"kopa": "pen_total", "majas": "pen_home", "viesi": "pen_away", "p1": "pen_p1", "p2": "pen_p2", "p3": "pen_p3"}


def _tiesnesu_tek_agregats(cur):
    r = cur[cur["loma"] == "referee"] if "loma" in cur.columns else cur
    r = r.assign(key=r["vards"].map(atslega))
    g = r.groupby("key")
    out = pd.DataFrame({"vards": g["vards"].last(), "GP": g["game_id"].nunique()})
    for m, c in _TEK_KOL.items():
        out[m] = g[c].mean() if c in r.columns else np.nan
    return out


def _liga_tek(cur):
    r = cur[cur["loma"] == "referee"] if "loma" in cur.columns else cur
    spele = r.drop_duplicates("game_id")
    return {m: (spele[c].mean() if c in spele.columns else np.nan) for m, c in _TEK_KOL.items()}


def _liga_prev(prev):
    out = {}
    for m in TIESNESU_METRIKAS:
        ok = prev[m].notna()
        out[m] = float((prev.loc[ok, m] * prev.loc[ok, "GP"]).sum() / prev.loc[ok, "GP"].sum()) if ok.any() else np.nan
    if "liga_kopa" in prev.columns and prev["liga_kopa"].notna().any():      # failā norādītais līgas vidējais
        out["kopa"] = float(prev["liga_kopa"].dropna().iloc[0])
    return out


def _shrink(n, avg, liga, k):
    """Pievelk tiesneša vidējo pie līgas vidējā: maz spēļu -> tuvāk līgai, daudz spēļu -> tuvāk paša vidējam."""
    n = n.where(avg.notna(), 0)
    return (n * avg.fillna(0) + k * liga) / (n + k) if (k > 0) else avg.fillna(liga)


def tiesnesu_apkopojums(cur, prev, w_prev=0.6, k=10):
    """
    Kombinētais noraidījumu rādītājs katram tiesnesim (kopā, mājas/viesu komandai, pa periodiem):
        kombinets = w_prev * pagājušā_sezona + (1 - w_prev) * šosezona,
    kur katra sezonas komponente ir pievilkta pie līgas vidējā ar K "papildu spēlēm"
    (jaunam tiesnesim vai ar maz spēlēm komponente ≈ līgas vidējais).
    Atgriež (tabula ar indeksu key, {"t": līga šosezon, "p": līga pagājušā, "blend": līga kombinētā}).
    """
    tuks = pd.DataFrame(columns=["vards", "GP", *TIESNESU_METRIKAS]).astype({"GP": float})
    t = _tiesnesu_tek_agregats(cur) if cur is not None and not cur.empty else tuks
    p = prev.set_index("key") if prev is not None and not prev.empty else tuks
    nan = {m: np.nan for m in TIESNESU_METRIKAS}
    liga_t = _liga_tek(cur) if cur is not None and not cur.empty else dict(nan)
    liga_p = _liga_prev(p.reset_index()) if not p.empty else dict(nan)
    for m in TIESNESU_METRIKAS:        # ja vienas sezonas nav, izmanto otras līgas vidējo
        if pd.isna(liga_t[m]):
            liga_t[m] = liga_p[m]
        if pd.isna(liga_p[m]):
            liga_p[m] = liga_t[m]

    keys = t.index.union(p.index)
    tab = pd.DataFrame(index=keys)
    tab["vards"] = t["vards"].reindex(keys).fillna(p["vards"].reindex(keys))
    gp_t = t["GP"].reindex(keys).fillna(0).astype(float)
    gp_p = p["GP"].reindex(keys).fillna(0).astype(float)
    tab["GP_t"], tab["GP_p"] = gp_t.astype(int), gp_p.astype(int)
    liga_bl = {}
    for m in TIESNESU_METRIKAS:
        avg_t, avg_p = t[m].reindex(keys).astype(float), p[m].reindex(keys).astype(float)
        w = w_prev if (not p.empty and p[m].notna().any()) else 0.0
        tab[f"{m}_t"], tab[f"{m}_p"] = avg_t, avg_p
        tab[m] = w * _shrink(gp_p, avg_p, liga_p[m], k) + (1 - w) * _shrink(gp_t, avg_t, liga_t[m], k)
        liga_bl[m] = w * liga_p[m] + (1 - w) * liga_t[m]
    tab["kopa_vs_liga"] = tab["kopa"] - liga_bl["kopa"]
    kopa_sp = tab["GP_t"] + tab["GP_p"]
    tab["dati"] = np.where(kopa_sp >= 20, "Pietiekami", np.where(kopa_sp >= 8, "Vidēji", "Maz datu"))
    return tab, {"t": liga_t, "p": liga_p, "blend": liga_bl}


def tiesnesu_prognoze(tab, liga, vardi):
    """Gaidāmie noraidījumi spēlē konkrētiem tiesnešiem (parasti 2); nezināmiem tiesnešiem - līgas vidējais."""
    out = {}
    for m in TIESNESU_METRIKAS:
        vert = []
        for v in vardi:
            k = atslega(v)
            ok = k in tab.index and pd.notna(tab.at[k, m])
            vert.append(float(tab.at[k, m]) if ok else float(liga["blend"][m]))
        out[m] = float(np.mean(vert)) if vert else float(liga["blend"][m])
    return out


def tiesnesu_speles(cur, vards):
    """Konkrēta tiesneša spēles šosezon (no tiesnesi.csv)."""
    if cur is None or cur.empty:
        return pd.DataFrame()
    r = cur[(cur["loma"] == "referee") & (cur["vards"].map(atslega) == atslega(vards))]
    return r.sort_values("datums", ascending=False)


def ielasit_planotos_tiesnesus():
    """Pirms spēlēm paziņotie tiesneši (sezonas/tiesnesi_planotie.csv, ko raksta tiesnesi_planotie.py)."""
    c = DATU_MAPE / "tiesnesi_planotie.csv"
    if not c.exists():
        return None
    df = pd.read_csv(c)
    return None if df.empty else df


def planotie_vardi(plan, game_id):
    """Spēles galveno tiesnešu vārdi no plānoto tiesnešu tabulas (tukšs saraksts, ja vēl nav paziņoti)."""
    if plan is None or plan.empty:
        return []
    r = plan[(plan["game_id"] == game_id) & (plan["loma"] == "referee")]
    return r["vards"].tolist()


# ----------------------------------------------------------------------------
# KARSTIE SPĒLĒTĀJI
# ----------------------------------------------------------------------------
KARSTUMA_METRIKAS = {"punkti": "points", "vardi": "goals", "piespeles": "assists"}   # points = vārti + piespēles
VIETAS_SERIJAS_SLIEKSNIS = 4      # tik mājas (vai izbraukuma) spēles pēc kārtas ar rādītāju: spēlētājs tiek iekļauts sarakstā arī bez augsta indeksa


def _trailing_serija(vertibas):
    """Cik spēles pēc kārtas (skaitot no jaunākās) rādītājs ir vismaz 1."""
    n = 0
    for v in vertibas[::-1]:
        if v >= 1:
            n += 1
        else:
            break
    return n


def karstie_speletaji(sk, metrika="punkti", logs=5, min_speles=3, k=10, min_speles_ar_raditaju=2, vietas_serija=VIETAS_SERIJAS_SLIEKSNIS):
    """
    Spēlētāju "karstuma" novērtējums pēc pēdējo `logs` spēļu rezultātiem (no speletaji.csv).

    Loģika (vienkārša, izskaidrojama):
      1. Gaidāmais rādītājs logā E = spēlētāja iepriekšējo spēļu vidējais (pievilkts pie līgas vidējā savā pozīcijā ar K spēlēm)
         × spēļu skaits logā. Spēlētājam bez vēstures E ir pozīcijas (uzbrucēju/aizsargu) līgas vidējais.
      2. Karstuma indekss z = (faktiskais - E) / sqrt(max(E, 0.5)): tas ņem vērā izlases lielumu, tāpēc 1-2 spēles nevar dot
         augstu indeksu, ja nav pietiekami daudz atkārtojumu.
      3. Prasības: vismaz `min_speles` spēles logā un rādītājs vismaz `min_speles_ar_raditaju` dažādās spēlēs
         (viena "uzspridzināta" spēle netiek uzskatīta par karstumu).
      4. Papildu signāli: sērija (spēles pēc kārtas ar rādītāju), metienu skaits un šaušanas % (vai rezultāts ir pamatots
         ar metieniem vai veiksmi), laiks laukumā (vai loma ir augusi).
      5. Gaidāmais rādītājs nākamajā spēlē = 75% sezonas vidējais (pievilkts pie līgas) + 25% loga vidējais (pievilkts).
         Hokejā "karstumam" ir neliela noturība, tāpēc svars ir mazs.
      6. Papildu atlase: spēlētājs tiek iekļauts arī tad, ja viņš negūst rādītāju katrā spēlē, bet gūst to vismaz `vietas_serija` mājas
         (vai izbraukuma) spēlēs pēc kārtas (skaitot tikai attiecīgās vietas spēles, piem., 4 mājas spēles pēc kārtas). Kolonna tr_serija.
    Atgriež DataFrame (viena rinda uz spēlētāju), kārtotu pēc karstuma indeksa (dilstoši).
    """
    if sk is None or sk.empty:
        return pd.DataFrame()
    col = KARSTUMA_METRIKAS[metrika]
    x = sk.copy()
    x["toi_min"] = x["toi"].map(toi_minutes)
    x["_dat"] = pd.to_datetime(x["datums"], errors="coerce")
    x = x.sort_values(["playerId", "_dat", "game_id"]).reset_index(drop=True)
    x["_no_gala"] = x.groupby("playerId").cumcount(ascending=False)       # 0 = jaunākā spēle
    x["grupa"] = np.where(x["pozicija"] == "D", "D", "F")
    liga = x.groupby("grupa")[col].mean()

    g = x.groupby("playerId")
    out = pd.DataFrame({
        "Speletajs": g["vards"].last(), "Komanda": g["team"].last(), "Poz": g["pozicija"].last(),
        "grupa": g["grupa"].last(), "GP": g.size(),
        "G_sez": g["goals"].sum(), "A_sez": g["assists"].sum(), "P_sez": g["points"].sum(), "SOG_sez": g["sog"].sum(),
        "m_sez": g[col].sum(), "toi_sez": g["toi_min"].mean(),
        "serija": g[col].agg(lambda s: _trailing_serija(s.fillna(0).values)),
    })
    w = x[x["_no_gala"] < logs].groupby("playerId")
    pr = x[x["_no_gala"] >= logs].groupby("playerId")
    out["n_w"] = w.size().reindex(out.index).fillna(0).astype(int)
    for nos, c in (("G_w", "goals"), ("A_w", "assists"), ("P_w", "points"), ("SOG_w", "sog"), ("m_w", col)):
        out[nos] = w[c].sum().reindex(out.index).fillna(0)
    out["toi_w"] = w["toi_min"].mean().reindex(out.index)
    out["spel_ar"] = w[col].agg(lambda s: int((s.fillna(0) >= 1).sum())).reindex(out.index).fillna(0).astype(int)
    out["n_p"] = pr.size().reindex(out.index).fillna(0)
    out["m_p"] = pr[col].sum().reindex(out.index).fillna(0)

    liga_s = out["grupa"].map(liga)
    pirms = (out["m_p"] + k * liga_s) / (out["n_p"] + k)                      # iepriekšējo spēļu vidējais (pievilkts)
    out["gaidamais_logaa"] = pirms * out["n_w"]
    out["z"] = (out["m_w"] - out["gaidamais_logaa"]) / np.sqrt(np.maximum(out["gaidamais_logaa"], 0.5))
    sezona_s = (out["m_sez"] + k * liga_s) / (out["GP"] + k)
    loga_s = (out["m_w"] + 5 * liga_s) / (out["n_w"] + 5)
    out["gaidamie_nakamaja"] = 0.75 * sezona_s + 0.25 * loga_s
    out["vid_sez"] = out["m_sez"] / out["GP"]
    out["vid_w"] = out["m_w"] / out["n_w"].where(out["n_w"] > 0)

    # sērijas pēc vietas: tikai mājas vai tikai izbraukuma spēles (hronoloģiskā secībā), cik pēdējās pēc kārtas ar rādītāju
    for nos, vieta in (("ser_majas", "home"), ("ser_viesos", "away")):
        xv = x[x["home_away"] == vieta]
        out[nos] = xv.groupby("playerId")[col].agg(lambda s: _trailing_serija(s.fillna(0).values)).reindex(out.index).fillna(0).astype(int)
    out["tr_serija"] = (out["ser_majas"] >= vietas_serija) | (out["ser_viesos"] >= vietas_serija)

    derigi = (out["n_w"] >= min_speles) & (out["spel_ar"] >= min_speles_ar_raditaju)
    out["z"] = out["z"].where(derigi)                                           # nederīgiem indekss nav aprēķināts
    out = out[(out["n_w"] >= min_speles) | out["tr_serija"]].copy()
    out["_serija_maks"] = out[["ser_majas", "ser_viesos"]].max(axis=1)
    return out.sort_values(["z", "_serija_maks"], ascending=[False, False], na_position="last")


def karstuma_teksts(r, metrika="punkti"):
    """Īss paskaidrojums, kāpēc spēlētājs tiek uzskatīts par karstu (viena rinda no karstie_speletaji)."""
    nos = {"punkti": "punkti", "vardi": "vārti", "piespeles": "piespēles"}[metrika]
    daudz = f"{int(r['m_w'])} {nos} {int(r['n_w'])} spēlēs ({r['vid_w']:.2f} spēlē; sezonā {r['vid_sez']:.2f})"
    daļas = [daudz]
    if r["spel_ar"] >= 2:
        daļas.append(f"rādītājs {int(r['spel_ar'])} no {int(r['n_w'])} spēlēm")
    if r["serija"] >= 3:
        daļas.append(f"sērija {int(r['serija'])} spēles pēc kārtas")
    for nos, vieta in (("ser_majas", "mājas"), ("ser_viesos", "viesu")):
        if int(r.get(nos, 0) or 0) >= VIETAS_SERIJAS_SLIEKSNIS and int(r["serija"]) < int(r.get(nos, 0)):
            daļas.append(f"{int(r[nos])} {vieta} spēles pēc kārtas ar rādītāju (tikai {vieta} spēļu secībā)")
    if r["n_w"] > 0 and r["GP"] > r["n_w"]:
        sog_w, sog_s = r["SOG_w"] / r["n_w"], r["SOG_sez"] / r["GP"]
        if metrika in ("punkti", "vardi"):
            if sog_s > 0 and sog_w >= sog_s * 1.15:
                daļas.append(f"metienu skaits audzis ({sog_w:.1f} pret {sog_s:.1f} spēlē), tāpēc rezultāts pamatots")
            elif r["SOG_w"] > 0 and r["G_w"] / r["SOG_w"] > max(0.25, 1.8 * r["G_sez"] / max(r["SOG_sez"], 1)):
                daļas.append("šaušanas % ļoti augsts, daļa var būt veiksme")
        if pd.notna(r["toi_w"]) and pd.notna(r["toi_sez"]) and r["toi_w"] - r["toi_sez"] >= 1.0:
            daļas.append(f"laiks laukumā +{r['toi_w'] - r['toi_sez']:.1f} min")
    return "; ".join(daļas)


def speletaju_speles(sk, raw, logs=5):
    """
    Katra spēlētāja pēdējās `logs` spēles (jaunākā pirmā), lai varētu redzēt, vai spēle bija mājās vai izbraukumā un ko viņš tajā guva.
    Atgriež DataFrame: playerId, game_id, datums (Rīgas), vieta ('Mājās'/'Izbraukumā'), pretinieks (kods), goals, assists, points.
    """
    if sk is None or sk.empty:
        return pd.DataFrame()
    x = sk.merge(raw[["game_id", "datums_lv", "home_team", "away_team"]], on="game_id", how="left")
    x["pretinieks"] = np.where(x["home_away"] == "home", x["away_team"], x["home_team"])
    x["vieta"] = np.where(x["home_away"] == "home", "Mājās", "Izbraukumā")
    x = x.sort_values(["playerId", "datums_lv", "game_id"], ascending=[True, False, False])
    x = x.groupby("playerId").head(logs)
    return x[["playerId", "game_id", "datums_lv", "vieta", "pretinieks", "goals", "assists", "points"]].rename(columns={"datums_lv": "datums"})
