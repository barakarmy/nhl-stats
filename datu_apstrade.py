"""
Datu ielāde un sagatavošana NHL lietotnei (bez Streamlit atkarības, lai kodu var testēt atsevišķi).

Datu avoti (mapē "dati" blakus šim failam, ko raksta nhl_dati.py):
  speles.csv, speletaji.csv, vartsargi.csv, varti.csv
Kalendārs: nhl_kalendars.csv (ko raksta kalendars.py).
Ja speles.csv vēl nav, tiek izmantots vecais nhl_sezona.csv.
"""
from __future__ import annotations

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
    celi = [DATU_MAPE / n for n in ("speles.csv", "speletaji.csv", "vartsargi.csv", "varti.csv")]
    celi += [BASE / "nhl_sezona.csv", BASE / "nhl_kalendars.csv"]
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
