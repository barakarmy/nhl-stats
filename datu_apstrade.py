"""
Datu ielāde un sagatavošana NHL lietotnei (bez Streamlit atkarības, lai kodu var testēt atsevišķi).

Datu avoti (mapē "dati" blakus šim failam, ko raksta nhl_dati.py):
  speles.csv, speletaji.csv, vartsargi.csv, varti.csv
Kalendārs: nhl_kalendars.csv (ko raksta kalendars.py).
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
DATU_MAPE = BASE / "dati"
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
FORMAS_EMOJI = {"W": "🟩", "OTL": "🟨", "L": "🟥"}

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
    celi = [DATU_MAPE / n for n in ("speles.csv", "speletaji.csv", "vartsargi.csv", "varti.csv",
                                    "tiesnesi.csv", "tiesnesi_pagajusa.csv", "referees_lastseason.csv")]
    celi += [BASE / "nhl_sezona.csv", BASE / "nhl_kalendars.csv", BASE / "referees_lastseason.csv"]
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
    return df.sort_values(["datums_lv", "sakums_lv", "game_id"]).reset_index(drop=True)


def ielasit_kalendaru():
    c = next((c for c in (BASE / "nhl_kalendars.csv", DATU_MAPE / "nhl_kalendars.csv") if c.exists()), None)
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
        "g_tot": p("total"), "z_tot": q("total"),
        "sog_tot": p("sog_total"), "sog_pret": q("sog_total"),
        "ppg": p("ppg"), "pp_sog": p("pp_sog"), "pp_opp": p("pp_opp"),
        "pim_tot": p("pim_total"), "pen_count": p("pen_count"), "pen_draw": q("pen_count"),
        "hits": p("hits"), "blocked": p("blocked_shots"),
        "giveaways": p("giveaways"), "takeaways": p("takeaways"), "fo_pct": p("faceoff_pct"),
    })
    for n in (1, 2, 3):
        d[f"g_p{n}"] = p(f"p{n}")
        d[f"z_p{n}"] = q(f"p{n}")
        d[f"sog_p{n}"] = p(f"sog_p{n}")
        d[f"sog_pret_p{n}"] = q(f"sog_p{n}")
        d[f"pim_p{n}"] = p(f"pim_p{n}")
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

    # noraidījumu skaits: precīzs no jaunajiem datiem, citādi minūtes / 2 (vecais formāts)
    c["pim_count"] = c["pen_count"].where(c["pen_count"].notna(), (c["pim_tot"] / 2).round())
    c["pim_count"] = c["pim_count"].fillna(0).astype(int)

    uzvara = c["g_tot"] > c["z_tot"]
    c["rez"] = np.where(uzvara, "W", np.where(c["beigas"].isin(["OT", "SO", "OT/SO"]), "OTL", "L"))
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
    """Komandu kopsavilkums (indekss = komanda). Vārtu rādītāji ir pamatlaika (bez OT/SO)."""
    sub = filtret(df, scope, n)
    if sub.empty:
        return pd.DataFrame()
    s = sub.assign(
        w=(sub["rez"] == "W").astype(int), l=(sub["rez"] == "L").astype(int),
        otl=(sub["rez"] == "OTL").astype(int), over65=(sub["tot_reg_goals"] > 6.5).astype(int))
    g = s.groupby("komanda")
    out = pd.DataFrame({
        "GP": g.size(),
        "W": g["w"].sum(), "L": g["l"].sum(), "OTL": g["otl"].sum(), "PTS": g["pts"].sum(),
        "G": g["g_reg"].sum(), "Z": g["z_reg"].sum(),
        "G_sp": g["g_reg"].mean(), "Z_sp": g["z_reg"].mean(),
        "SOG_sp": g["sog_tot"].mean(), "SA_sp": g["sog_pret"].mean(),
        "PPG": g["ppg"].sum(), "PP_opp": g["pp_opp"].sum(min_count=1), "PP_sog": g["pp_sog"].sum(),
        "PPG_pret": g["ppg_allowed"].sum(), "PP_opp_pret": g["pp_opp_pret"].sum(min_count=1),
        "PEN_sp": g["pim_count"].mean(), "PIM_sp": g["pim_tot"].mean(), "DRAW_sp": g["pen_draw"].mean(),
        "Over65": g["over65"].mean() * 100,
    })
    for p in (1, 2, 3):
        out[f"G_p{p}"] = g[f"g_p{p}"].mean()
        out[f"Z_p{p}"] = g[f"z_p{p}"].mean()
    out["Starpiba"] = out["G"] - out["Z"]
    out["PTS_pct"] = out["PTS"] / (2 * out["GP"]) * 100
    sog_s, sa_s = g["sog_tot"].sum(), g["sog_pret"].sum()
    out["SOG_dala"] = sog_s / (sog_s + sa_s).where((sog_s + sa_s) > 0) * 100
    out["PP_pct"] = _dala(out["PPG"], out["PP_opp"])
    out["PK_pct"] = 100 - _dala(out["PPG_pret"], out["PP_opp_pret"])
    out["PEN_starpiba"] = out["DRAW_sp"] - out["PEN_sp"]
    return out


def forma(df, n=5):
    """Pēdējo n spēļu rezultāti kā emoji virkne (vecākā → jaunākā)."""
    return df.groupby("komanda")["rez"].agg(lambda s: "".join(FORMAS_EMOJI.get(x, "⬜") for x in s.tail(n)))


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
# Pagājušās sezonas fails: dati/referees_lastseason.csv (vai dati/tiesnesi_pagajusa.csv, vai tas pats fails saknē)
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
    return (DATU_MAPE / "referees_lastseason.csv", DATU_MAPE / "tiesnesi_pagajusa.csv", BASE / "referees_lastseason.csv")


def atslega(vards):
    """Vārda atslēga salīdzināšanai: pirmais burts + uzvārds ('Wes McCauley' = 'W. McCauley')."""
    s = unicodedata.normalize("NFKD", str(vards)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z\s-]", " ", s.replace("'", ""))
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
