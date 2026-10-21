"""
shorts.py – vertikāli YouTube Shorts video (1080×1920, MP4) no lietotnes datiem: "xG LUCK REPORT" + atskati.

JAUNS VIDEO (--veids):
  speletaji  – 3 spēlētāji ar vārtiem krietni VIRS xG (veiksme → atdzisīs) un 3 krietni ZEM xG (gaidāmi vārti)
  komandas   – 3 komandas ar augstāko PDO (veicas → kritīsies) un 3 ar zemāko (neveicas → uzlabosies)
  vartsargi  – 3 vārtsargi ar labāko GSAx (karsti → atdzisīs) un 3 ar sliktāko (atkopsies)
  Katram jaunam video blakus MP4 tiek saglabāts .json ar parādīto sarakstu un datu periodu.

TREŠDIENAS VIDEO (--veids fantasy): "3 fantasy pickups nākamajai nedēļai" – nākamās nedēļas grafiks (komandas ar 4 un 2
  spēlēm) un 3 spēlētāji, kuri ESPN līgās paņemti ≤ 40 % (--max-rostered), ar labāko formu pēdējās 14 dienās
  (punkti, metieni, ixG, laiks uz ledus, punkti vairākumā) + nākamās nedēļas spēļu skaits un pretinieku aizsardzība.
  Vajag sezonas/fantasy_espn.csv (fantasy_espn.py, ikdienas darbplūsmā). Komanda: python shorts.py --veids fantasy

ATSKATS (--atskats <json>): ņem tieši to sarakstu, kas tika parādīts video, un rāda, kas notika PĒC tā datuma
  (vārti pret xG / PDO / GSAx spēlē) ar ✓ (prognoze piepildījās) vai ✗ (nepiepildījās). Spēlētājs, kurš pēc tam
  nav spēlējis, rezultātā netiek skaitīts.

Katrā kadrā augšā redzams datu datums: jaunam video "STATS THROUGH <datums>", atskatam "FLAGGED <datums> · RESULTS <no – līdz>".

Ieteicamais grafiks: pirmdienās jauns video (speletaji → komandas → vartsargi → ...), ceturtdienās atskats par
video, kas publicēts pirms ~2,5 nedēļām. Lai dati starp viena veida video nepārklātos, lieto --dienas 21.

Palaišana (repozitorija mapē):
    pip install pandas numpy pillow edge-tts     (+ ffmpeg: Windows – winget install ffmpeg, tad jauns terminālis)
    python shorts.py --veids speletaji --dienas 21 --kanals @tavskanals
    python shorts.py --veids komandas  --dienas 21
    python shorts.py --veids vartsargi --dienas 21
    python shorts.py --atskats video/2026-10-26_speletaji        (mape, ko izveidoja jaunais video)
    python shorts.py --gaida                                     → kuriem video vēl jātaisa atskats un kad
    citi parametri: --top 3  --min-metieni 15  --balss en-US-GuyNeural  --bez-balss
                    --lidz 2026-10-25   (izmantot datus tikai līdz šim datumam; noder pārbaudei / atkārtošanai)
Rezultāts: katrai ģenerācijai sava mape video/<šodienas datums>_<veids>/ (piem. video/2026-10-26_speletaji/):
  .mp4 video, .txt (virsraksts, apraksts, runa), .json (tikai xG video – atskatam) un INFO.txt (kad ģenerēts, kādi dati,
  ar kādu komandu, un vai/kad jātaisa atskats + gatava komanda). Atskata mape: video/<datums>_atskats_<veids>/;
  izveidojot atskatu, oriģinālās mapes INFO.txt tiek atzīmēts "ATSKATS IZVEIDOTS".
.txt failā: virsraksts, apraksts ar tēmturiem, datu periods un runas teksts.
"""
import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import timedelta

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import xg as xgm  # noqa: E402

W, H, FPS = 1080, 1920, 30
BG_TOP, BG_BOT = (10, 15, 28), (22, 32, 58)
BALTS, PELEKS, TUMSS, MELNS = (245, 247, 250), (148, 163, 184), (30, 41, 59), (8, 15, 30)
ZALS, SARKANS, ZILS, DZELTENS = (34, 197, 94), (239, 68, 68), (56, 189, 248), (250, 204, 21)
NEITRALS = (100, 116, 139)

KOMANDAS = {
    "ANA": ("Anaheim", "Ducks", (252, 76, 2)), "BOS": ("Boston", "Bruins", (252, 181, 20)),
    "BUF": ("Buffalo", "Sabres", (0, 48, 135)), "CGY": ("Calgary", "Flames", (200, 16, 46)),
    "CAR": ("Carolina", "Hurricanes", (206, 17, 38)), "CHI": ("Chicago", "Blackhawks", (207, 10, 44)),
    "COL": ("Colorado", "Avalanche", (111, 38, 61)), "CBJ": ("Columbus", "Blue Jackets", (0, 38, 84)),
    "DAL": ("Dallas", "Stars", (0, 104, 71)), "DET": ("Detroit", "Red Wings", (206, 17, 38)),
    "EDM": ("Edmonton", "Oilers", (252, 76, 0)), "FLA": ("Florida", "Panthers", (200, 16, 46)),
    "LAK": ("Los Angeles", "Kings", (162, 170, 173)), "MIN": ("Minnesota", "Wild", (21, 71, 52)),
    "MTL": ("Montreal", "Canadiens", (175, 30, 45)), "NSH": ("Nashville", "Predators", (255, 184, 28)),
    "NJD": ("New Jersey", "Devils", (206, 17, 38)), "NYI": ("New York", "Islanders", (0, 83, 155)),
    "NYR": ("New York", "Rangers", (0, 56, 168)), "OTT": ("Ottawa", "Senators", (218, 26, 50)),
    "PHI": ("Philadelphia", "Flyers", (247, 73, 2)), "PIT": ("Pittsburgh", "Penguins", (252, 181, 20)),
    "SJS": ("San Jose", "Sharks", (0, 109, 117)), "SEA": ("Seattle", "Kraken", (153, 217, 217)),
    "STL": ("St. Louis", "Blues", (0, 47, 135)), "TBL": ("Tampa Bay", "Lightning", (0, 40, 104)),
    "TOR": ("Toronto", "Maple Leafs", (0, 32, 91)), "UTA": ("Utah", "Mammoth", (113, 175, 229)),
    "VAN": ("Vancouver", "Canucks", (0, 32, 91)), "VGK": ("Vegas", "Golden Knights", (185, 151, 91)),
    "WSH": ("Washington", "Capitals", (200, 16, 46)), "WPG": ("Winnipeg", "Jets", (4, 30, 66)),
}


def uz_fona(bg):
    """Teksta krāsa, kas labi redzama uz dotā fona (gaišām komandu krāsām – tumšs teksts)."""
    r, g, b = bg[:3]
    return MELNS if 0.299 * r + 0.587 * g + 0.114 * b > 150 else BALTS


def kkrasa(kom):
    return KOMANDAS.get(str(kom), ("", str(kom), NEITRALS))[2]


def kom_nos(kom):
    return KOMANDAS.get(str(kom), ("", str(kom)))[1]


FONTU_MAPES = ["/usr/share/fonts/opentype/inter", "C:/Windows/Fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental",
               "/usr/share/fonts/truetype/dejavu"]
FONTI = {"black": ["Inter-Black.otf", "ariblk.ttf", "Arial Black.ttf", "DejaVuSans-Bold.ttf"],
         "bold": ["Inter-ExtraBold.otf", "Inter-Bold.otf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
         "semi": ["Inter-SemiBold.otf", "seguisb.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
         "reg": ["Inter-Medium.otf", "Inter-Regular.otf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]}
_fcache = {}


def fonts(veids, izm):
    k = (veids, izm)
    if k not in _fcache:
        for nos in FONTI[veids]:
            p = next((os.path.join(m, nos) for m in FONTU_MAPES if os.path.exists(os.path.join(m, nos))), None)
            if p:
                _fcache[k] = ImageFont.truetype(p, izm)
                break
        else:
            _fcache[k] = ImageFont.load_default(izm)
    return _fcache[k]


def dat(d, gads=False):
    """'Oct 19' vai 'Oct 19, 2026' (strādā arī Windows)."""
    d = pd.Timestamp(d)
    return f"{d:%b} {d.day}" + (f", {d.year}" if gads else "")


def periods_txt(no, lidz):
    no, lidz = pd.Timestamp(no), pd.Timestamp(lidz)
    if no.year != lidz.year:
        return f"{dat(no, True)} – {dat(lidz, True)}"
    return f"{dat(no)} – {dat(lidz, True)}"


def spelu(n):
    return f"{n} game" + ("" if n == 1 else "s")


def minus(s):
    return s.replace("-", "−")


def sk(v):
    """numpy → python skaitlis JSON failam."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else round(float(v), 4)
    return v


# ================================================================ dati

def ielasit(lidz=None):
    m = pd.read_csv(os.path.join(BASE, "sezonas", "metieni.csv"), low_memory=False)
    if lidz:
        m = m[m["datums"] <= lidz]
    mod = xgm.ielasit_modeli()
    if mod is None:
        raise SystemExit("Nav xG modeļa (sezonas/vesture/xg_modelis.json).")
    m["xg"] = xgm.xg_varbutibas(m, mod)
    m = m[m["xg"].notna()].copy()                                   # bez tukšajiem vārtiem un metienu sērijas
    m["varti"] = pd.to_numeric(m["varti"], errors="coerce").fillna(0)
    m["metejs"] = pd.to_numeric(m["metejs"], errors="coerce")
    m["vartsargs"] = pd.to_numeric(m["vartsargs"], errors="coerce")
    m["uz_v"] = m["tips"].astype(str).isin(["sog", "goal"]).astype(int)
    return m


def logs(m, dienas=None):
    if dienas:
        sak = (pd.Timestamp(m["datums"].max()) - timedelta(days=dienas - 1)).strftime("%Y-%m-%d")
        m = m[m["datums"] >= sak]
    return m


def speletaju_vardi():
    sp = pd.read_csv(os.path.join(BASE, "sezonas", "speletaji.csv"), encoding="utf-8-sig", low_memory=False)
    sp = sp.sort_values("datums").drop_duplicates("playerId", keep="last")
    sp["playerId"] = pd.to_numeric(sp["playerId"], errors="coerce")
    return sp.set_index("playerId")[["vards", "team", "pozicija", "numurs"]]


def speletaju_tabula(m, min_metieni=0):
    g = m.groupby("metejs").agg(G=("varti", "sum"), xG=("xg", "sum"), met=("xg", "size"), sog=("uz_v", "sum"),
                                sp=("game_id", "nunique"))
    g = g[g["met"] >= min_metieni].copy()
    g["d"] = g["G"] - g["xG"]
    return g


def komandu_tabula(m):
    gf = m.groupby("komanda").agg(GF=("varti", "sum"), xGF=("xg", "sum"), SF=("uz_v", "sum"))
    ga = m.groupby("pretinieks").agg(GA=("varti", "sum"), xGA=("xg", "sum"), SA=("uz_v", "sum"))
    gp = pd.concat([m[["game_id", "komanda"]], m[["game_id", "pretinieks"]].rename(columns={"pretinieks": "komanda"})]) \
        .drop_duplicates().groupby("komanda").size().rename("GP")
    t = gf.join(ga, how="outer").join(gp, how="outer").fillna(0)
    t["sh"] = (t["GF"] / t["SF"].where(t["SF"] > 0)) * 100
    t["sv"] = (1 - t["GA"] / t["SA"].where(t["SA"] > 0)) * 100
    t["PDO"] = t["sh"] + t["sv"]
    t["GD"], t["xGD"] = t["GF"] - t["GA"], t["xGF"] - t["xGA"]
    return t


def vartsargu_tabula(m):
    x = m[m["vartsargs"].notna()]
    g = x.groupby("vartsargs").agg(kom=("pretinieks", "last"), met=("xg", "size"), SA=("uz_v", "sum"), GA=("varti", "sum"),
                                   xGA=("xg", "sum"), GP=("game_id", "nunique"))
    g["GSAx"] = g["xGA"] - g["GA"]
    g["sv"] = (1 - g["GA"] / g["SA"].where(g["SA"] > 0)) * 100
    g["GSAx_sp"] = g["GSAx"] / g["GP"]
    return g


def bilance(no=None, lidz=None):
    """Komandu W-L-OTL un punkti no sezonas/speles.csv (regulārā sezona, pēc izvēles – datumu intervālā)."""
    s = pd.read_csv(os.path.join(BASE, "sezonas", "speles.csv"), encoding="utf-8-sig", low_memory=False)
    s = s[s["home_total"].notna() & (s["speles_tips"].astype(str) == "2")]
    if no:
        s = s[s["datums"] >= no]
    if lidz:
        s = s[s["datums"] <= lidz]
    r = {}
    for x in s.itertuples(index=False):
        ot = str(x.spele_beidzas) != "REG"
        for k in (x.home_team, x.away_team):
            b = r.setdefault(k, [0, 0, 0])
            if x.uzvaretajs == k:
                b[0] += 1
            elif ot:
                b[2] += 1
            else:
                b[1] += 1
    return {k: (v[0], v[1], v[2], 2 * v[0] + v[2]) for k, v in r.items()}


def zimogs_jauns(no, lidz, dienas):
    return f"STATS THROUGH {dat(lidz, True).upper()}  ·  " + (f"LAST {dienas} DAYS" if dienas else "SEASON TO DATE")


# ================================================================ jauni video

def veids_speletaji(m, a):
    mm = logs(m, a.dienas)
    g = speletaju_tabula(mm, a.min_metieni).join(speletaju_vardi())
    g = g[g["vards"].notna()]
    laim = g.sort_values(["d", "G"], ascending=[False, False]).head(a.top)
    nelaim = g[g["xG"] >= 1.5].sort_values(["d", "xG"], ascending=[True, False]).head(a.top)
    if laim.empty or nelaim.empty:
        return None
    no, lidz = mm["datums"].min(), mm["datums"].max()

    def karte(pid, r, nr, lucky):
        v = str(r["vards"]).split(" ", 1)
        poz = {"C": "Center", "L": "Left wing", "R": "Right wing", "D": "Defense"}.get(str(r["pozicija"]), str(r["pozicija"]))
        num = "" if pd.isna(r["numurs"]) else f"#{int(r['numurs'])}  ·  "
        sh = r["G"] / r["sog"] * 100 if r["sog"] else 0
        return {"nr": nr, "akc": ZALS if lucky else SARKANS,
                "augsa": "LUCKY  ·  EXPECT A COOLDOWN" if lucky else "UNLUCKY  ·  DUE FOR GOALS",
                "v1": v[0] if len(v) > 1 else "", "v2": v[-1], "badge": str(r["team"]), "bkr": kkrasa(r["team"]),
                "info": f"{num}{poz}  ·  {int(r['sp'])} GP",
                "bars": [("GOALS", r["G"], BALTS, "{:.0f}"), ("EXPECTED (xG)", r["xG"], ZILS, "{:.1f}")],
                "liels": minus(f"{r['G'] - r['xG']:+.1f}"),
                "apaksa": f"goals vs expected  ·  {sh:.0f}% shooting on {int(r['sog'])} SOG"}
    kartes = [karte(p, r, i, True) for i, (p, r) in enumerate(laim.iterrows(), 1)]
    kartes += [karte(p, r, i, False) for i, (p, r) in enumerate(nelaim.iterrows(), 1)]
    runa = [f"Which NHL scorers are running on luck? Goals versus expected goals, {dat(no)} to {dat(lidz)}."]
    b1, b2 = ["Expect a cooldown.", "That pace won't last.", "Regression is coming."], ["He's due.", "The goals will come.", "Buy low."]
    for i, (_, r) in enumerate(laim.iterrows()):
        runa.append(f"{r['vards']} has {int(r['G'])} goals on just {r['xG']:.1f} expected. {b1[i % 3]}")
    for i, (_, r) in enumerate(nelaim.iterrows()):
        g_ = int(r["G"])
        runa.append(f"{r['vards']}: {g_} goal{'' if g_ == 1 else 's'}, but {r['xG']:.1f} expected. {b2[i % 3]}")
    runa.append("Luck runs out. Expected goals don't. We'll check back in two weeks. Follow for weekly NHL stats.")
    rinda = lambda r: {"vards": r["vards"], "team": r["team"], "G": sk(r["G"]), "xG": sk(r["xG"]), "sog": sk(r["sog"]), "sp": sk(r["sp"])}  # noqa: E731
    return {
        "intro": {"tag": "NHL  ·  xG LUCK REPORT", "rindas": [("WHO'S", BALTS), ("RUNNING", BALTS), ("ON LUCK?", DZELTENS)],
                  "apaksa": ["Goals vs expected goals (xG)", periods_txt(no, lidz)],
                  "legenda": [("LUCKY  →  cooldown", ZALS, MELNS), ("UNLUCKY  →  due for goals", SARKANS, BALTS)]},
        "kartes": kartes,
        "outro": {"rindas": [("LUCK RUNS OUT.", BALTS), ("xG DOESN'T.", DZELTENS)],
                  "info": [f"Own xG model · {len(mm):,} unblocked shots".replace(",", " "), "We'll check back in 2 weeks"]},
        "zimogs": zimogs_jauns(no, lidz, a.dienas), "runa": runa, "lidz": lidz, "periods": periods_txt(no, lidz),
        "thumb": {"tag": "NHL  ·  xG LUCK REPORT", "hook": ["RUNNING", "ON LUCK?"], "vards": str(laim.iloc[0]["vards"]).split(" ")[-1],
                  "badge": str(laim.iloc[0]["team"]), "skaitlis": minus(f"{laim.iloc[0]['G'] - laim.iloc[0]['xG']:+.1f}"), "kr": ZALS,
                  "apaksa": "goals above expected", "datums": lidz},
        "virsraksts": f"{laim.iloc[0]['vards']} is running HOT… but xG says it won't last 🏒",
        "saraksts": [f"{r['vards']} ({r['team']}): {int(r['G'])} G vs {r['xG']:.1f} xG" for _, r in pd.concat([laim, nelaim]).iterrows()],
        "apraksts": "Goals vs expected goals (xG) – who's lucky and who's due.",
        "momentuzn": {"laim": {str(int(p)): rinda(r) for p, r in laim.iterrows()},
                      "nelaim": {str(int(p)): rinda(r) for p, r in nelaim.iterrows()}},
    }


def veids_komandas(m, a):
    mm = logs(m, a.dienas)
    t = komandu_tabula(mm)
    t = t[t["GP"] >= 3]
    if len(t) < 2 * a.top:
        return None
    laim = t.sort_values("PDO", ascending=False).head(a.top)
    nelaim = t.sort_values("PDO").head(a.top)
    no, lidz = mm["datums"].min(), mm["datums"].max()
    bil = bilance(lidz=lidz)

    def karte(kom, r, nr, lucky):
        pils, nos, kr = KOMANDAS.get(kom, ("", kom, NEITRALS))
        w, l_, o, p = bil.get(kom, (0, 0, 0, 0))
        return {"nr": nr, "akc": ZALS if lucky else SARKANS,
                "augsa": "RIDING LUCK  ·  EXPECT A DROP" if lucky else "UNLUCKY  ·  BETTER THAN RECORD",
                "v1": pils, "v2": nos, "badge": kom, "bkr": kr, "info": f"Season record {w}-{l_}-{o}  ·  {p} PTS",
                "bars": [("GOAL DIFFERENCE", r["GD"], BALTS, "{:+.0f}"), ("EXPECTED (xG DIFF)", r["xGD"], ZILS, "{:+.1f}")],
                "diverg": True, "liels": f"PDO {r['PDO']:.1f}",
                "apaksa": f"{r['sh']:.1f} SH% + {r['sv']:.1f} SV%  ·  avg ≈ 100"}
    kartes = [karte(k, r, i, True) for i, (k, r) in enumerate(laim.iterrows(), 1)]
    kartes += [karte(k, r, i, False) for i, (k, r) in enumerate(nelaim.iterrows(), 1)]
    zime = lambda v: ("plus " if v >= 0 else "minus ") + f"{abs(v):.0f}"   # noqa: E731
    runa = ["Which NHL teams are living on luck? PDO adds shooting and save percentage. Average is one hundred."]
    for k, r in laim.iterrows():
        runa.append(f"The {kom_nos(k)}: PDO {r['PDO']:.0f}. Goal difference {zime(r['GD'])}, but expected only {zime(r['xGD'])}.")
    for k, r in nelaim.iterrows():
        runa.append(f"The {kom_nos(k)}: PDO {r['PDO']:.0f}. They're playing better than the scoreboard says.")
    runa.append("PDO always comes back to one hundred. We'll check back in two weeks. Follow for weekly NHL stats.")
    rinda = lambda r: {k_: sk(r[k_]) for k_ in ("PDO", "sh", "sv", "GD", "xGD", "GP")}   # noqa: E731
    return {
        "intro": {"tag": "NHL  ·  TEAM LUCK REPORT", "rindas": [("WHICH TEAMS", BALTS), ("ARE LIVING", BALTS), ("ON LUCK?", DZELTENS)],
                  "apaksa": ["PDO = shooting % + save %  ·  avg ≈ 100", periods_txt(no, lidz)],
                  "legenda": [("HIGH PDO  →  expect a drop", ZALS, MELNS), ("LOW PDO  →  better days ahead", SARKANS, BALTS)]},
        "kartes": kartes,
        "outro": {"rindas": [("PDO ALWAYS", BALTS), ("COMES BACK.", DZELTENS)],
                  "info": ["All situations, empty-net goals excluded", "We'll check back in 2 weeks"]},
        "zimogs": zimogs_jauns(no, lidz, a.dienas), "runa": runa, "lidz": lidz, "periods": periods_txt(no, lidz),
        "thumb": {"tag": "NHL  ·  TEAM LUCK REPORT", "hook": ["LIVING", "ON LUCK?"], "vards": kom_nos(laim.index[0]),
                  "badge": laim.index[0], "skaitlis": f"PDO {laim.iloc[0]['PDO']:.1f}", "kr": ZALS,
                  "apaksa": "league average ≈ 100", "datums": lidz},
        "virsraksts": f"The {kom_nos(laim.index[0])} are winning on LUCK – here's the proof 🏒",
        "saraksts": [f"{' '.join(KOMANDAS.get(k, ('', k))[:2]).strip()}: PDO {r['PDO']:.1f}, GD {r['GD']:+.0f} vs xGD {r['xGD']:+.1f}"
                     for k, r in pd.concat([laim, nelaim]).iterrows()],
        "apraksts": "PDO (shooting % + save %) and goal difference vs expected goal difference.",
        "momentuzn": {"laim": {k: rinda(r) for k, r in laim.iterrows()}, "nelaim": {k: rinda(r) for k, r in nelaim.iterrows()}},
    }


def veids_vartsargi(m, a):
    mm = logs(m, a.dienas)
    g = vartsargu_tabula(mm)
    g = g[(g["GP"] >= 3) & (g["met"] >= max(60, a.min_metieni * 4))].copy()
    if len(g) < 2 * a.top:
        return None
    vg = pd.read_csv(os.path.join(BASE, "sezonas", "vartsargi.csv"), encoding="utf-8-sig", low_memory=False)
    vg["playerId"] = pd.to_numeric(vg["playerId"], errors="coerce")
    vg = vg.sort_values("datums").drop_duplicates("playerId", keep="last").set_index("playerId")
    g = g.join(vg[["vards", "numurs"]])
    g = g[g["vards"].notna()]
    labie = g.sort_values("GSAx", ascending=False).head(a.top)
    sliktie = g.sort_values("GSAx").head(a.top)
    no, lidz = mm["datums"].min(), mm["datums"].max()

    def karte(r, nr, labs):
        v = str(r["vards"]).split(" ", 1)
        num = "" if pd.isna(r["numurs"]) else f"#{int(r['numurs'])}  ·  "
        return {"nr": nr, "akc": ZALS if labs else SARKANS,
                "augsa": "RED HOT  ·  STEALING GAMES" if labs else "ICE COLD  ·  COSTING GAMES",
                "v1": v[0] if len(v) > 1 else "", "v2": v[-1], "badge": str(r["kom"]), "bkr": kkrasa(r["kom"]),
                "info": f"{num}Goalie  ·  {int(r['GP'])} GP",
                "bars": [("GOALS ALLOWED", r["GA"], BALTS, "{:.0f}"), ("EXPECTED (xGA)", r["xGA"], ZILS, "{:.1f}")],
                "liels": minus(f"{r['GSAx']:+.1f}"),
                "apaksa": f"saved above expected  ·  .{round(r['sv'] * 10):03d} SV%  ·  {int(r['SA'])} shots"}
    kartes = [karte(r, i, True) for i, (_, r) in enumerate(labie.iterrows(), 1)]
    kartes += [karte(r, i, False) for i, (_, r) in enumerate(sliktie.iterrows(), 1)]
    runa = ["Which NHL goalies are stealing games, and which are costing them? Goals saved above expected."]
    for _, r in labie.iterrows():
        runa.append(f"{r['vards']}: {r['GSAx']:.1f} goals saved above expected. {int(r['GA'])} allowed on {r['xGA']:.1f} expected.")
    for _, r in sliktie.iterrows():
        runa.append(f"{r['vards']}: {abs(r['GSAx']):.1f} goals worse than expected. {int(r['GA'])} allowed on {r['xGA']:.1f} expected.")
    runa.append("Hot streaks cool, cold streaks thaw. We'll check back in two weeks. Follow for weekly NHL stats.")
    rinda = lambda r: {"vards": r["vards"], "kom": r["kom"], **{k_: sk(r[k_]) for k_ in ("GSAx", "GSAx_sp", "GA", "xGA", "SA", "sv", "GP")}}  # noqa: E731
    return {
        "intro": {"tag": "NHL  ·  GOALIE REPORT", "rindas": [("WHO'S", BALTS), ("STEALING", BALTS), ("GAMES?", DZELTENS)],
                  "apaksa": ["Goals saved above expected (GSAx)", periods_txt(no, lidz)],
                  "legenda": [("+  saves more than expected", ZALS, MELNS), ("−  lets in more than expected", SARKANS, BALTS)]},
        "kartes": kartes,
        "outro": {"rindas": [("SAVE % LIES.", BALTS), ("GSAx DOESN'T.", DZELTENS)],
                  "info": ["GSAx = expected goals against − goals allowed", "We'll check back in 2 weeks"]},
        "zimogs": zimogs_jauns(no, lidz, a.dienas), "runa": runa, "lidz": lidz, "periods": periods_txt(no, lidz),
        "thumb": {"tag": "NHL  ·  GOALIE REPORT", "hook": ["STEALING", "GAMES"], "vards": str(labie.iloc[0]["vards"]).split(" ")[-1],
                  "badge": str(labie.iloc[0]["kom"]), "skaitlis": minus(f"{labie.iloc[0]['GSAx']:+.1f}"), "kr": ZALS,
                  "apaksa": "goals saved above expected", "datums": lidz},
        "virsraksts": f"{labie.iloc[0]['vards']} is STEALING games – the numbers 🥅",
        "saraksts": [f"{r['vards']} ({r['kom']}): GSAx {r['GSAx']:+.1f}, {int(r['GA'])} GA vs {r['xGA']:.1f} xGA"
                     for _, r in pd.concat([labie, sliktie]).iterrows()],
        "apraksts": "Goals saved above expected (GSAx) – which goalies steal games and which cost them.",
        "momentuzn": {"laim": {str(int(p)): rinda(r) for p, r in labie.iterrows()},
                      "nelaim": {str(int(p)): rinda(r) for p, r in sliktie.iterrows()}},
    }


VEIDI = {"speletaji": veids_speletaji, "komandas": veids_komandas, "vartsargi": veids_vartsargi}


# ================================================================ atskats

def atskats(fails, m, a):
    with open(fails, encoding="utf-8") as f:
        j = json.load(f)
    veids, lidz0 = j["veids"], j["lidz"]
    pec = m[m["datums"] > lidz0]
    if pec.empty:
        print(f"Pēc {lidz0} vēl nav aizvadītu spēļu – atskatam vēl par agru.")
        return None
    no2, lidz2 = pec["datums"].min(), pec["datums"].max()
    neitr = "DIDN'T PLAY"
    kartes, runa_k, saraksts, ok_skaits, vert_skaits = [], [], [], 0, 0

    if veids == "speletaji":
        t = speletaju_tabula(pec)
        for grupa, lucky in (("laim", True), ("nelaim", False)):
            for nr, (pid, r) in enumerate(j["momentuzn"][grupa].items(), 1):
                x = t.loc[float(pid)] if float(pid) in t.index else None
                G2, xG2, sp2 = (0, 0.0, 0) if x is None else (int(x["G"]), float(x["xG"]), int(x["sp"]))
                if sp2 < 2:
                    ok, verd = None, (neitr if sp2 == 0 else "TOO FEW GAMES")
                elif lucky:
                    ok = (G2 - xG2) <= 0.5
                    verd = "COOLED OFF ✓" if ok else "STILL HOT ✗"
                else:
                    ok = (G2 - xG2) >= -0.5 or G2 >= 2
                    verd = "GOALS CAME ✓" if ok else "STILL WAITING ✗"
                v = str(r["vards"]).split(" ", 1)
                kartes.append({"nr": nr, "akc": NEITRALS if ok is None else (ZALS if ok else SARKANS),
                               "augsa": "WE SAID: COOLDOWN" if lucky else "WE SAID: DUE FOR GOALS",
                               "v1": v[0] if len(v) > 1 else "", "v2": v[-1], "badge": r["team"], "bkr": kkrasa(r["team"]),
                               "info": f"On {dat(lidz0)}: {int(r['G'])} G on {r['xG']:.1f} xG",
                               "bars": [("GOALS SINCE", G2, BALTS, "{:.0f}"), ("EXPECTED (xG) SINCE", xG2, ZILS, "{:.1f}")],
                               "liels": verd, "liels_izm": 120,
                               "apaksa": f"{spelu(sp2)}  ·  {dat(no2)} – {dat(lidz2)}"})
                tail = ("Too few games to judge." if ok is None else ("Cooled off." if ok else "Still hot. Miss.") if lucky
                        else ("The goals came." if ok else "Still waiting. Miss."))
                runa_k.append(f"{r['vards']} {'was running hot' if lucky else 'was due'}. Since then: {G2} goals on {xG2:.1f} expected. {tail}")
                saraksts.append(f"{r['vards']} ({r['team']}): {int(r['G'])} G / {r['xG']:.1f} xG → {G2} G / {xG2:.1f} xG  {verd}")
                if ok is not None:
                    vert_skaits += 1
                    ok_skaits += int(ok)
        tag, rindas = "NHL  ·  xG FOLLOW-UP", [("DID xG", BALTS), ("CALL IT?", DZELTENS)]
        temats, vards_k = "players", "scorers"
        outro_info = "Goals vs xG after the video date"

    elif veids == "komandas":
        t = komandu_tabula(pec)
        bil = bilance(no=no2, lidz=lidz2)
        for grupa, lucky in (("laim", True), ("nelaim", False)):
            for nr, (kom, r) in enumerate(j["momentuzn"][grupa].items(), 1):
                x = t.loc[kom] if kom in t.index else None
                if x is None or x["GP"] < 2 or not np.isfinite(x["PDO"]):
                    ok, verd, p2 = None, "NOT ENOUGH GAMES", np.nan
                else:
                    p2 = float(x["PDO"])
                    ok = p2 <= r["PDO"] - 2 if lucky else p2 >= r["PDO"] + 2
                    verd = ("PDO DROPPED ✓" if ok else "STILL LUCKY ✗") if lucky else ("PDO ROSE ✓" if ok else "STILL UNLUCKY ✗")
                pils, nos, kr = KOMANDAS.get(kom, ("", kom, NEITRALS))
                w, l_, o, _ = bil.get(kom, (0, 0, 0, 0))
                bars = [("PDO BEFORE", r["PDO"] - 100, BALTS, "{:.1f}", 100)]
                if np.isfinite(p2):
                    bars.append(("PDO SINCE", p2 - 100, ZILS, "{:.1f}", 100))
                gd_txt = ""
                if x is not None:
                    gd_s, xgd_s = minus(format(x["GD"], "+.0f")), minus(format(x["xGD"], "+.1f"))
                    gd_txt = f"GD {gd_s} vs xGD {xgd_s}  ·  "
                kartes.append({"nr": nr, "akc": NEITRALS if ok is None else (ZALS if ok else SARKANS),
                               "augsa": "WE SAID: PDO WILL DROP" if lucky else "WE SAID: PDO WILL RISE",
                               "v1": pils, "v2": nos, "badge": kom, "bkr": kr,
                               "info": f"Record since {dat(lidz0)}: {w}-{l_}-{o}",
                               "bars": bars, "diverg": True, "nulle": "100",
                               "liels": verd, "liels_izm": 120,
                               "apaksa": f"{gd_txt}{dat(no2)} – {dat(lidz2)}"})
                tail = ("Not enough games." if ok is None else ("Luck ran out." if ok else "Still lucky. Miss.") if lucky
                        else ("Better days came." if ok else "Still unlucky. Miss."))
                p2_txt = "n/a" if not np.isfinite(p2) else f"{p2:.0f}"
                runa_k.append(f"The {nos}: PDO was {r['PDO']:.0f}. Since then: {p2_txt}. {tail}")
                saraksts.append(f"{pils} {nos}: PDO {r['PDO']:.1f} → {p2_txt}  {verd}")
                if ok is not None:
                    vert_skaits += 1
                    ok_skaits += int(ok)
        tag, rindas = "NHL  ·  TEAM LUCK FOLLOW-UP", [("DID THE LUCK", BALTS), ("RUN OUT?", DZELTENS)]
        temats, vards_k = "teams", "teams"
        outro_info = "PDO after the video date, all situations"

    elif veids == "vartsargi":
        t = vartsargu_tabula(pec)
        for grupa, labs in (("laim", True), ("nelaim", False)):
            for nr, (pid, r) in enumerate(j["momentuzn"][grupa].items(), 1):
                x = t.loc[float(pid)] if float(pid) in t.index else None
                r1 = r["GSAx_sp"]
                if x is None or x["GP"] < 2:
                    ok, verd = None, (neitr if x is None else "TOO FEW GAMES")
                    r2, gp2 = np.nan, (0 if x is None else int(x["GP"]))
                else:
                    r2, gp2 = float(x["GSAx_sp"]), int(x["GP"])
                    ok = r2 < r1 * 0.5 if labs else r2 > r1 * 0.5
                    verd = ("CAME BACK DOWN ✓" if ok else "STILL STEALING ✗") if labs else ("BOUNCED BACK ✓" if ok else "STILL STRUGGLING ✗")
                v = str(r["vards"]).split(" ", 1)
                gsax0 = minus(format(r["GSAx"], "+.1f"))
                bars = [("GSAx PER GAME BEFORE", r1, BALTS, "{:+.2f}")]
                if np.isfinite(r2):
                    bars.append(("GSAx PER GAME SINCE", r2, ZILS, "{:+.2f}"))
                sv_txt = "" if x is None or not np.isfinite(x["sv"]) else f".{round(x['sv'] * 10):03d} SV%  ·  "
                kartes.append({"nr": nr, "akc": NEITRALS if ok is None else (ZALS if ok else SARKANS),
                               "augsa": "WAS STEALING GAMES" if labs else "WAS COSTING GAMES",
                               "v1": v[0] if len(v) > 1 else "", "v2": v[-1], "badge": r["kom"], "bkr": kkrasa(r["kom"]),
                               "info": f"On {dat(lidz0)}: GSAx {gsax0} in {int(r['GP'])} GP",
                               "bars": bars, "diverg": True,
                               "liels": verd, "liels_izm": 120,
                               "apaksa": f"{sv_txt}{spelu(gp2)}  ·  {dat(no2)} – {dat(lidz2)}"})
                tail = ("Too few games to judge." if ok is None else ("Came back to earth." if ok else "Still stealing. Miss.") if labs
                        else ("Bounced back." if ok else "Still struggling. Miss."))
                r2_txt = "n/a" if not np.isfinite(r2) else f"{r2:+.2f}"
                r2_runa = r2_txt.replace("+", "plus ").replace("-", "minus ")
                stav = "was red hot" if labs else "was ice cold"
                runa_k.append(f"{r['vards']} {stav}. Since then: {r2_runa} goals saved above expected per game. {tail}")
                saraksts.append(f"{r['vards']} ({r['kom']}): GSAx/GP {r1:+.2f} → {r2_txt}  {verd}")
                if ok is not None:
                    vert_skaits += 1
                    ok_skaits += int(ok)
        tag, rindas = "NHL  ·  GOALIE FOLLOW-UP", [("DID THE STREAKS", BALTS), ("LAST?", DZELTENS)]
        temats, vards_k = "goalies", "goalies"
        outro_info = "GSAx per game after the video date"
    else:
        raise SystemExit(f"Nezināms veids JSON failā: {veids}")

    rez = f"{ok_skaits}/{vert_skaits}"
    zimogs = f"FLAGGED {dat(lidz0, True).upper()}  ·  RESULTS {dat(no2).upper()} – {dat(lidz2).upper()}"
    runa = [f"On {dat(lidz0)}, we flagged {len(kartes)} NHL {vards_k} as lucky or unlucky. Here's what happened next."] + runa_k
    runa.append(f"The call went {ok_skaits} for {vert_skaits}. No hiding misses. Follow for weekly NHL stats.")
    return {
        "intro": {"tag": tag, "rindas": rindas,
                  "apaksa": [f"Our list from {dat(lidz0, True)}", f"Results: {dat(no2)} – {dat(lidz2, True)}"],
                  "legenda": [("✓  prediction held", ZALS, MELNS), ("✗  prediction missed", SARKANS, BALTS)]},
        "kartes": kartes,
        "outro": {"rindas": [(f"WENT {rez}.", BALTS), ("NO HIDING MISSES.", DZELTENS)],
                  "info": [outro_info, f"{dat(no2)} – {dat(lidz2, True)}"]},
        "zimogs": zimogs, "runa": runa, "lidz": lidz2, "periods": f"flagged {dat(lidz0, True)}, results {dat(no2)} – {dat(lidz2, True)}",
        "thumb": {"tag": tag, "hook": ["DID xG", "CALL IT?"], "vards": {"players": "PLAYERS", "teams": "TEAMS", "goalies": "GOALIES"}[temats],
                  "badge": "", "skaitlis": f"{rez} ✓", "kr": ZALS if vert_skaits and ok_skaits / vert_skaits >= 0.5 else SARKANS,
                  "apaksa": f"flagged {dat(lidz0)} · results to {dat(lidz2)}", "datums": lidz2},
        "virsraksts": f"We called these NHL {temats} lucky. Were we right? ({rez}) 🏒",
        "saraksts": saraksts, "apraksts": f"Follow-up on our xG luck list from {dat(lidz0, True)}: what happened next.",
        "nosaukums": f"xg_atskats_{veids}_{lidz0}_{lidz2}",
    }


# ================================================================ zīmēšana

def ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def fons():
    a = np.linspace(0, 1, H)[:, None, None]
    img = (np.array(BG_TOP) * (1 - a) + np.array(BG_BOT) * a).repeat(W, axis=1).astype(np.uint8)
    im = Image.fromarray(img, "RGB")
    d = ImageDraw.Draw(im, "RGBA")
    d.line([(0, 1250), (W, 1250)], fill=(220, 38, 38, 40), width=6)
    d.ellipse([W / 2 - 330, 1250 - 330, W / 2 + 330, 1250 + 330], outline=(56, 189, 248, 28), width=6)
    for y in (420, 1700):
        d.line([(0, y), (W, y)], fill=(56, 189, 248, 30), width=8)
    return im


def platums(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f)
    return b[2] - b[0]


def teksts_c(d, y, txt, f, krasa=BALTS):
    d.text(((W - platums(d, txt, f)) / 2, y), txt, font=f, fill=krasa)


def ietilpinat(d, txt, veids, izm, max_w):
    while izm > 30 and platums(d, txt, fonts(veids, izm)) > max_w:
        izm -= 4
    return fonts(veids, izm)


def pill(d, x, y, txt, f, bg, fg=BALTS, pad=(26, 12), center=False):
    b = d.textbbox((0, 0), txt, font=f)
    w, h = b[2] - b[0] + 2 * pad[0], b[3] - b[1] + 2 * pad[1]
    if center:
        x = (W - w) / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
    d.text((x + pad[0] - b[0], y + pad[1] - b[1]), txt, font=f, fill=fg)
    return w, h


def ar_alfa(kr, a):
    return tuple(kr[:3]) + (int(a),)


def slide(t, ilgums, t_in=0.28, t_out=0.22):
    if t < t_in:
        k = ease(t / t_in)
        return (1 - k) * 140, k
    if t > ilgums - t_out:
        k = ease((t - (ilgums - t_out)) / t_out)
        return -k * 140, 1 - k
    return 0, 1


def aina_intro(t, s):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = ease(t / 0.5)
    pill(d, 0, 300, s["tag"], fonts("semi", 40), ZILS, MELNS, center=True)
    y = 470 if len(s["rindas"]) == 3 else 560
    for i, (rinda, kr) in enumerate(s["rindas"]):
        kk = ease((t - 0.12 * i) / 0.45)
        f = ietilpinat(d, rinda, "black", 150, W - 120)
        d.text(((W - platums(d, rinda, f)) / 2 + (1 - kk) * 200, y), rinda, font=f, fill=ar_alfa(kr, 255 * kk))
        y += 175
    for i, r in enumerate(s["apaksa"]):
        teksts_c(d, 1080 + i * 66, r, ietilpinat(d, r, "reg", 46, W - 120), ar_alfa(PELEKS, 255 * k))
    a = 255 * ease((t - 0.6) / 0.4)
    for i, (txt, bg, fg) in enumerate(s["legenda"]):
        pill(d, 0, 1300 + i * 100, txt, fonts("semi", 40), ar_alfa(bg, a), ar_alfa(fg, a), center=True)
    return im


def aina_karte(t, c):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    akc = c["akc"]
    pill(d, 0, 250, c["augsa"], fonts("semi", 40), akc, MELNS if akc == ZALS else BALTS, center=True)
    x0, y0, x1, y1 = 70, 380, W - 70, 1640
    d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=(15, 23, 42, 235), outline=(255, 255, 255, 30), width=3)
    d.rounded_rectangle([x0, y0, x1, y0 + 22], radius=11, fill=c["bkr"])
    d.text((x0 + 50, y0 + 60), f"#{c['nr']}", font=fonts("black", 92), fill=akc)
    fb = fonts("bold", 48)
    pill(d, x1 - 50 - platums(d, c["badge"], fb) - 68, y0 + 80, c["badge"], fb, c["bkr"], uz_fona(c["bkr"]), pad=(34, 14))
    d.text((x0 + 50, y0 + 210), c["v1"].upper(), font=fonts("semi", 54), fill=PELEKS)
    f2 = ietilpinat(d, c["v2"].upper(), "black", 120, x1 - x0 - 100)
    d.text((x0 + 50, y0 + 275), c["v2"].upper(), font=f2, fill=BALTS)
    d.text((x0 + 50, y0 + 425), c["info"], font=ietilpinat(d, c["info"], "reg", 44, x1 - x0 - 100), fill=PELEKS)
    # stabiņi
    k = ease((t - 0.35) / 0.9)
    yb = y0 + 560
    bx0, bx1 = x0 + 50, x1 - 50
    div = c.get("diverg", False)
    mx = max([abs(b[1]) for b in c["bars"]] + [1]) * (1.25 if div else 1.08)
    for i, bar in enumerate(c["bars"]):
        nos, v, kr, fmt = bar[:4]
        baze = bar[4] if len(bar) > 4 else 0
        y = yb + i * 190
        d.text((bx0, y), nos, font=fonts("semi", 40), fill=PELEKS)
        d.rounded_rectangle([bx0, y + 62, bx1, y + 142], radius=40, fill=TUMSS)
        vv = v * k
        txt = fmt.format(baze + vv)
        txt = minus(txt) if "+" in fmt or baze + vv < 0 else txt
        if div and c.get("nulle") and i == 0:
            fz = fonts("semi", 32)
            d.text(((bx0 + bx1) / 2 - platums(d, c["nulle"], fz) / 2, y + 8), c["nulle"], font=fz, fill=PELEKS)
        fv = fonts("black", 64)
        tw = platums(d, txt, fv)
        if div:
            cx = (bx0 + bx1) / 2
            d.line([(cx, y + 50), (cx, y + 154)], fill=(255, 255, 255, 90), width=4)
            w = (bx1 - bx0) / 2 * (abs(vv) / mx)
            if w > 6:
                xa, xb = (cx, cx + w) if vv >= 0 else (cx - w, cx)
                d.rounded_rectangle([xa, y + 62, xb, y + 142], radius=min(40, w / 2), fill=kr)
            arpus = (cx + w + 20 + tw <= bx1 - 10) if vv >= 0 else (cx - w - 20 - tw >= bx0 + 10)
            if arpus:
                tx, krt = (cx + w + 20 if vv >= 0 else cx - w - 20 - tw), BALTS
            else:                                                     # neietilpst ārpusē → stabiņa iekšpusē
                tx, krt = (cx + w - tw - 28 if vv >= 0 else cx - w + 28), MELNS
            d.text((tx, y + 64), txt, font=fv, fill=krt)
        else:
            w = (bx1 - bx0) * (max(vv, 0) / mx)
            if w > 80:
                d.rounded_rectangle([bx0, y + 62, bx0 + w, y + 142], radius=40, fill=kr)
            ieksa = w + tw + 60 >= bx1 - bx0
            tx = bx0 + w - tw - 30 if ieksa else bx0 + max(w, 0) + 20
            d.text((tx, y + 64), txt, font=fv, fill=MELNS if ieksa else BALTS)
    k2 = ease((t - 1.2) / 0.45)
    if k2 > 0:
        f = ietilpinat(d, c["liels"], "black", int(c.get("liels_izm", 200) * (0.7 + 0.3 * k2)), x1 - x0 - 80)
        teksts_c(d, yb + 410, c["liels"], f, ar_alfa(akc, 255 * k2))
        teksts_c(d, yb + 640, c["apaksa"], ietilpinat(d, c["apaksa"], "reg", 42, x1 - x0 - 80), ar_alfa(PELEKS, 255 * k2))
    return im


def aina_outro(t, s, kanals):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    a = 255 * ease(t / 0.4)
    for i, (r, kr) in enumerate(s["rindas"]):
        teksts_c(d, 560 + i * 140, r, ietilpinat(d, r, "black", 104, W - 100), ar_alfa(kr, a))
    for i, r in enumerate(s["info"]):
        teksts_c(d, 900 + i * 64, r, ietilpinat(d, r, "reg", 44, W - 120), ar_alfa(PELEKS, a))
    a2 = 255 * ease((t - 0.5) / 0.4)
    pill(d, 0, 1180, "FOLLOW FOR WEEKLY NHL STATS", fonts("bold", 50), ar_alfa(ZILS, a2), ar_alfa(MELNS, a2), pad=(44, 24), center=True)
    if kanals:
        teksts_c(d, 1330, kanals, fonts("semi", 52), ar_alfa(BALTS, a2))
    cta = s.get("cta")
    if cta:
        a3 = 255 * ease((t - 0.9) / 0.4)
        x0, y0, x1, y1 = 90, 1420, W - 90, 1670
        d.rounded_rectangle([x0, y0, x1, y1], radius=32, fill=ar_alfa((15, 23, 42), 235 * a3 / 255),
                            outline=ar_alfa(DZELTENS, a3), width=4)
        teksts_c(d, y0 + 30, cta[0], ietilpinat(d, cta[0], "black", 52, x1 - x0 - 60), ar_alfa(DZELTENS, a3))
        for i, rinda in enumerate(cta[1:]):
            teksts_c(d, y0 + 112 + i * 58, rinda, ietilpinat(d, rinda, "semi", 40, x1 - x0 - 60), ar_alfa(BALTS, a3))
    return im


# ================================================================ trešdienas video: fantasy pickups

DIENAS_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _toi_min(s):
    try:
        mm, ss = str(s).split(":")
        return int(mm) + int(ss) / 60
    except (ValueError, AttributeError):
        return np.nan


def _mmss(v):
    v = abs(v)
    return f"{int(v)}:{int(round((v - int(v)) * 60)):02d}"


def nakama_nedela(a, lidz):
    """Nākamās fantasy nedēļas pirmdiena (pēc šodienas; ar --nedela var norādīt pašam)."""
    if a.nedela:
        return pd.Timestamp(a.nedela).normalize()
    sod = pd.Timestamp(a.lidz) + timedelta(days=1) if a.lidz else pd.Timestamp.now().normalize()
    return sod + timedelta(days=(7 - sod.weekday()) % 7 or 7)


def espn_dati():
    """sezonas/fantasy_espn.csv (+ izmaiņa 7 dienās no vēstures) → DataFrame pēc NHL playerId, vai None."""
    p = os.path.join(BASE, "sezonas", "fantasy_espn.csv")
    if not os.path.exists(p):
        return None, None
    e = pd.read_csv(p)
    e = e[pd.to_numeric(e["playerId"], errors="coerce").notna()].copy()
    e["playerId"] = e["playerId"].astype(int)
    e["delta7"] = np.nan
    pv = os.path.join(BASE, "sezonas", "fantasy_espn_vesture.csv")
    if os.path.exists(pv):
        v = pd.read_csv(pv)
        mer = (pd.Timestamp(e["datums"].max()) - timedelta(days=7)).strftime("%Y-%m-%d")
        vecs = v[v["datums"] <= mer].sort_values("datums").drop_duplicates("espn_id", keep="last").set_index("espn_id")["rostered"]
        if len(vecs):
            e["delta7"] = e["rostered"] - e["espn_id"].map(vecs).fillna(0)
    return e.drop_duplicates("playerId").set_index("playerId"), e["datums"].max()


def veids_fantasy(m, a):
    dienas = a.dienas or 14
    sp = pd.read_csv(os.path.join(BASE, "sezonas", "speletaji.csv"), encoding="utf-8-sig", low_memory=False)
    sp["playerId"] = pd.to_numeric(sp["playerId"], errors="coerce")
    sp["toi_m"] = sp["toi"].map(_toi_min)
    if a.lidz:
        sp = sp[sp["datums"] <= a.lidz]
    lidz = sp["datums"].max()
    no = (pd.Timestamp(lidz) - timedelta(days=dienas - 1)).strftime("%Y-%m-%d")
    nesen = sp[sp["datums"] >= no]
    vec = sp[sp["datums"] < no]
    g = nesen.groupby("playerId").agg(GP=("game_id", "nunique"), G=("goals", "sum"), A=("assists", "sum"), P=("points", "sum"),
                                      SOG=("sog", "sum"), TOI=("toi_m", "mean"), pedeja=("datums", "max"),
                                      vards=("vards", "last"), team=("team", "last"), poz=("pozicija", "last"), numurs=("numurs", "last"))
    g = g[(g["poz"] != "G") & (g["GP"] >= 4) & (g["pedeja"] >= (pd.Timestamp(lidz) - timedelta(days=7)).strftime("%Y-%m-%d"))].copy()
    g["TOI_vec"] = vec.groupby("playerId")["toi_m"].mean().reindex(g.index)
    g["TOI_d"] = (g["TOI"] - g["TOI_vec"]).fillna(0)
    # ixG (pēdējās N dienas, visas situācijas)
    mm = m[(m["datums"] >= no) & (m["datums"] <= lidz)]
    g["ixG"] = mm.groupby("metejs")["xg"].sum().reindex(g.index).fillna(0)
    # punkti vairākumā (vārti + piespēles ar strength == pp)
    v = pd.read_csv(os.path.join(BASE, "sezonas", "varti.csv"), encoding="utf-8-sig", low_memory=False)
    v = v[(v["datums"] >= no) & (v["datums"] <= lidz) & (v["strength"].astype(str).str.lower() == "pp")]
    pp = pd.concat([pd.to_numeric(v[c], errors="coerce") for c in ("scorer_id", "assist1_id", "assist2_id")]).dropna().astype(int).value_counts()
    g["PPP"] = pp.reindex(g.index).fillna(0)
    for k in ("P", "SOG", "ixG", "PPP"):
        g[k + "_gp"] = g[k] / g["GP"]
    # nākamās nedēļas grafiks
    start = nakama_nedela(a, lidz)
    beigas = start + timedelta(days=6)
    kal = pd.read_csv(os.path.join(BASE, "sezonas", "nhl_kalendars.csv"), encoding="utf-8-sig")
    kal = kal[(kal["datums"] >= start.strftime("%Y-%m-%d")) & (kal["datums"] <= beigas.strftime("%Y-%m-%d"))]
    if kal.empty:
        print(f"Kalendārā nav spēļu nedēļai {start:%Y-%m-%d} – {beigas:%Y-%m-%d}.")
        return None
    grafiks = {}
    for r in kal.itertuples(index=False):
        d = DIENAS_EN[pd.Timestamp(r.datums).weekday()]
        grafiks.setdefault(r.majas_komanda, []).append((r.datums, d, r.viesu_komanda, "vs"))
        grafiks.setdefault(r.viesu_komanda, []).append((r.datums, d, r.majas_komanda, "@"))
    for k in grafiks:
        grafiks[k].sort()
    # pretinieku aizsardzība: xG pret spēlē visā sezonā (augstāks = vājāka aizsardzība = labāka spēle uzbrucējiem)
    kt = komandu_tabula(m[m["datums"] <= lidz])
    xga = (kt["xGA"] / kt["GP"]).sort_values(ascending=False)
    vajas, stipras = set(xga.index[:10]), set(xga.index[-10:])
    g["sp_nak"] = g["team"].map(lambda k: len(grafiks.get(k, [])))
    g["vajie"] = g["team"].map(lambda k: sum(o in vajas for _, _, o, _ in grafiks.get(k, [])))
    g = g[g["sp_nak"] >= 1]
    g["stipras"] = g["team"].map(lambda k: sum(o in stipras for _, _, o, _ in grafiks.get(k, [])))
    # ESPN % rostered
    e, e_dat = espn_dati()
    if e is not None:
        g = g.join(e[["rostered", "delta7"]], how="left")
        rost_txt = f"under {a.max_rostered:.0f}% rostered on ESPN"
    else:
        print("BRĪDINĀJUMS: nav sezonas/fantasy_espn.csv (palaid python fantasy_espn.py) – izslēdzu sezonas top 60 pēc punktiem; drop netiek rādīti.")
        g["rostered"], g["delta7"] = np.nan, np.nan
        rost_txt = "outside the top 60 scorers"

    def z(s_):
        sd = s_.std()
        return (s_ - s_.mean()) / sd if sd and np.isfinite(sd) else s_ * 0
    # forma tiek vērtēta pret VISIEM spēlētājiem (ne tikai brīvajiem), aizsargi – atsevišķi no uzbrucējiem
    g["grupa"] = np.where(g["poz"] == "D", "D", "F")

    def forma_grupai(x):
        return (0.30 * z(x["P_gp"]) + 0.25 * z(x["ixG_gp"]) + 0.15 * z(x["SOG_gp"]) + 0.10 * z(x["TOI_d"].clip(-4, 4))
                + 0.10 * z(x["PPP_gp"]))
    g["forma"] = pd.concat([forma_grupai(x) for _, x in g.groupby("grupa")])
    if e is not None:
        brivi = g[g["rostered"].notna() & (g["rostered"] <= a.max_rostered)].copy()
        nometami = g[g["rostered"].notna() & (g["rostered"] >= a.drop_min_rostered) & (g["rostered"] <= a.drop_max_rostered)].copy()
    else:
        top = sp.groupby("playerId")["points"].sum().sort_values(ascending=False).index[:60]
        brivi, nometami = g[~g.index.isin(top)].copy(), g.iloc[0:0].copy()
    if len(brivi) < a.top:
        return None
    brivi["score"] = brivi["forma"] + 0.40 * (brivi["sp_nak"] - 3.5) + 0.05 * brivi["vajie"] + 0.10 * z(brivi["delta7"].fillna(0))
    def ar_limitu(df, kol, n):
        """Top n pēc kol, bet ne vairāk kā 1 aizsargs (fantasy līgās vairāk vajag uzbrucējus) un 1 spēlētājs no komandas."""
        out, d_, kom_ = [], 0, set()
        for pid_, r_ in df.sort_values(kol, ascending=False).iterrows():
            if (r_["grupa"] == "D" and d_ >= 1) or r_["team"] in kom_:
                continue
            out.append(pid_)
            d_ += r_["grupa"] == "D"
            kom_.add(r_["team"])
            if len(out) >= n:
                break
        return df.loc[out]
    izv = ar_limitu(brivi, "score", a.top)
    # drop: daudzās līgās paņemts, bet vāja forma un/vai mazs/grūts nākamās nedēļas grafiks
    nometami["dscore"] = -nometami["forma"] + 0.40 * (3.5 - nometami["sp_nak"]) + 0.05 * nometami["stipras"] - 0.10 * z(nometami["delta7"].fillna(0))
    drop = ar_limitu(nometami[nometami["forma"] < 0], "dscore", a.drop) if a.drop > 0 else nometami.iloc[0:0]
    drop_veids = {pid_: ("BENCH" if r_["forma"] > -0.4 and r_["sp_nak"] <= 2 else "DROP") for pid_, r_ in drop.iterrows()}

    lidz_ts = pd.Timestamp(lidz)

    def iemesls(r):
        if r["TOI_d"] >= 1.5:
            return f"Bigger role: +{_mmss(r['TOI_d'])} ice time per game"
        if r["PPP"] >= 2:
            return f"Power-play role: {int(r['PPP'])} PP points in {int(r['GP'])} games"
        if r["ixG_gp"] >= g["ixG_gp"].quantile(0.8):
            return f"Real chances: {r['ixG_gp']:.2f} expected goals per game"
        if r["sp_nak"] >= 4:
            return f"{int(r['sp_nak'])} games next week" + (f", {int(r['vajie'])} vs weak defenses" if r["vajie"] else "")
        return f"{r['SOG_gp']:.1f} shots per game – volume drives fantasy points"

    def iemesls_drop(r):
        dalas = []
        if r["TOI_d"] <= -1.5:
            dalas.append(f"−{_mmss(r['TOI_d'])} ice time per game")
        if r["P"] == 0:
            dalas.append(f"no points in {int(r['GP'])} games")
        elif r["P_gp"] < 0.35:
            dalas.append(f"{int(r['P'])} point{'' if r['P'] == 1 else 's'} in {int(r['GP'])} games")
        if r["poz"] != "D" and r["ixG_gp"] <= g.loc[g["grupa"] == "F", "ixG_gp"].quantile(0.3):
            dalas.append(f"only {r['ixG_gp']:.2f} xG per game")
        if r["sp_nak"] <= 2:
            dalas.append(f"only {int(r['sp_nak'])} games next week")
        elif r["stipras"] >= 2:
            dalas.append(f"{int(r['stipras'])} tough matchups next week")
        t_ = ", ".join(dalas[:2]) or "cold form and a tough week ahead"
        return t_[0].upper() + t_[1:]

    poz_nos = {"C": "Center", "L": "Left wing", "R": "Right wing", "D": "Defense"}

    def karte(nr, r, veids):
        vv = str(r["vards"]).split(" ", 1)
        rost = "" if not np.isfinite(r["rostered"]) else f"{r['rostered']:.0f}% ROSTERED (ESPN)"
        delta = r["delta7"]
        d_txt = "" if not np.isfinite(delta) or abs(delta) < 0.5 else (f"▲ {delta:.1f}% this week" if delta > 0 else f"▼ {abs(delta):.1f}% this week")
        toi_sub = "" if abs(r["TOI_d"]) < 0.5 else (("▲ " if r["TOI_d"] > 0 else "▼ ") + _mmss(r["TOI_d"]))
        pretinieki = []
        for _, d, o, kur in grafiks.get(r["team"], []):
            kr = ZALS if o in vajas else (SARKANS if o in stipras else NEITRALS)
            pretinieki.append((d, f"{'' if kur == 'vs' else '@'}{o}", kr))
        akc = {"ADD": ZALS, "STREAM": DZELTENS, "DROP": SARKANS, "BENCH": (249, 115, 22)}[veids]
        virs = f"PICKUP #{nr}" if veids in ("ADD", "STREAM") else f"DROP CANDIDATE #{nr}"
        return {
            "tips": "fantasy", "nr": nr, "akc": akc, "augsa": virs + (f"  ·  {rost}" if rost else ""),
            "v1": vv[0] if len(vv) > 1 else "", "v2": vv[-1], "badge": str(r["team"]), "bkr": kkrasa(r["team"]),
            "info": f"{poz_nos.get(str(r['poz']), str(r['poz']))}  ·  last {dienas} days: {int(r['GP'])} GP" + (f"  ·  {d_txt}" if d_txt else ""),
            "flizes": [("PTS", f"{int(r['P'])}", f"{int(r['G'])}G {int(r['A'])}A"),
                       ("SOG / GP", f"{r['SOG_gp']:.1f}", ""),
                       ("xG / GP", f"{r['ixG_gp']:.2f}", ""),
                       ("TOI / GP", _mmss(r["TOI"]), toi_sub),
                       ("PP PTS", f"{int(r['PPP'])}", ""),
                       ("NEXT WEEK", f"{int(r['sp_nak'])} GP", "")],
            "pretinieki": pretinieki, "liels": veids,
            "apaksa": iemesls(r) if veids in ("ADD", "STREAM") else iemesls_drop(r)}

    kartes = []
    cetri = sorted([k for k, v in grafiks.items() if len(v) >= 4])
    divi = sorted([k for k, v in grafiks.items() if len(v) <= 2])
    kartes.append({"tips": "grafiks", "cetri": cetri, "divi": divi,
                   "nedela": f"{dat(start).upper()} – {dat(beigas).upper()}"})
    n_drop = len(drop)
    runa = [f"Three fantasy hockey pickups for next week, all {rost_txt}" + (f", plus {n_drop} player{'' if n_drop == 1 else 's'} to drop or bench." if n_drop else "."),
            f"First, the schedule. {len(cetri)} teams play four games next week" + (f", {len(divi)} play only two." if divi else ".")]
    for nr, (pid, r) in enumerate(izv.iterrows(), 1):
        veids = "STREAM" if r["forma"] < 0.4 and r["sp_nak"] >= 4 else "ADD"
        kartes.append(karte(nr, r, veids))
        ros = "" if not np.isfinite(r["rostered"]) else f" Rostered in only {r['rostered']:.0f} percent of leagues."
        runa.append(f"{r['vards']}, {kom_nos(r['team'])}. {int(r['P'])} points in his last {int(r['GP'])} games, "
                    f"{r['SOG_gp']:.1f} shots a game, and {int(r['sp_nak'])} games next week.{ros} "
                    + ("Stream him." if veids == "STREAM" else "Add him."))
    for nr, (pid, r) in enumerate(drop.iterrows(), 1):
        veids = drop_veids[pid]
        kartes.append(karte(nr, r, veids))
        sakums = ("Now, players to drop or bench. " if n_drop > 1 else "Now, one player to drop or bench. ") if nr == 1 else ""
        runa.append(f"{sakums}{r['vards']}, {kom_nos(r['team'])}. Rostered in {r['rostered']:.0f} percent of leagues, but "
                    f"{iemesls_drop(r)[0].lower() + iemesls_drop(r)[1:]}. " + ("Bench him this week." if veids == "BENCH" else "Time to drop him."))
    runa.append("Green matchups are the weakest defenses by expected goals against. Follow for weekly fantasy hockey tips.")
    zimogs = f"STATS THROUGH {dat(lidz_ts, True).upper()}" + (f"  ·  ESPN ROSTERED % {dat(e_dat).upper()}" if e is not None else "")
    legenda = [("ADD  →  keep him", ZALS, MELNS), ("STREAM  →  ride the schedule", DZELTENS, MELNS)]
    if n_drop:
        legenda.append(("DROP / BENCH  →  cut or sit", SARKANS, BALTS))
    saraksts = [f"ADD {r['vards']} ({r['team']}): {int(r['P'])} P in {int(r['GP'])} GP, {r['SOG_gp']:.1f} SOG/GP, "
                f"{r['ixG_gp']:.2f} xG/GP, {int(r['sp_nak'])} games next week"
                + ("" if not np.isfinite(r["rostered"]) else f", {r['rostered']:.1f}% rostered") for _, r in izv.iterrows()]
    saraksts += [f"{drop_veids[pid_]} {r['vards']} ({r['team']}): {r['rostered']:.0f}% rostered – {iemesls_drop(r)}" for pid_, r in drop.iterrows()]
    return {
        "intro": {"tag": "NHL  ·  FANTASY WAIVER WIRE", "rindas": [("3 PICKUPS", BALTS), (f"+ {n_drop} DROP{'' if n_drop == 1 else 'S'}" if n_drop else "FOR NEXT", BALTS),
                                                                  ("NEXT WEEK" if n_drop else "WEEK", DZELTENS)],
                  "apaksa": [f"Week of {dat(start)} – {dat(beigas, True)}", "Pickups " + rost_txt],
                  "legenda": legenda},
        "kartes": kartes,
        "outro": {"rindas": [("GRAB THEM", BALTS), ("BEFORE THEY'RE GONE.", DZELTENS)],
                  "info": ["Rostered % from ESPN  ·  stats from NHL", "Green = soft matchup (high xG against)"]},
        "zimogs": zimogs, "runa": runa, "lidz": lidz, "periods": f"{dat(no)} – {dat(lidz, True)}; week of {dat(start)} – {dat(beigas, True)}",
        "thumb": {"tag": "NHL  ·  FANTASY WAIVER WIRE", "hook": ["3 PICKUPS", f"+ {n_drop} DROP{'' if n_drop == 1 else 'S'}" if n_drop else "NEXT WEEK"],
                  "vards": str(izv.iloc[0]["vards"]).split(" ")[-1], "badge": str(izv.iloc[0]["team"]),
                  "skaitlis": (f"{izv.iloc[0]['rostered']:.0f}%" if np.isfinite(izv.iloc[0]["rostered"]) else f"{int(izv.iloc[0]['P'])} PTS"),
                  "kr": ZALS, "apaksa": ("rostered on ESPN" if np.isfinite(izv.iloc[0]["rostered"]) else f"in {int(izv.iloc[0]['GP'])} games"),
                  "datums": None, "nedela": f"WEEK OF {dat(start).upper()}"},
        "virsraksts": f"3 fantasy hockey pickups" + (f" & {n_drop} drop{'' if n_drop == 1 else 's'}" if n_drop else "") + f" for next week – {izv.iloc[0]['vards']} is a must-add 🏒",
        "saraksts": saraksts,
        "apraksts": f"Fantasy hockey waiver wire for the week of {dat(start)} – {dat(beigas, True)}.",
        "nosaukums": f"fantasy_{start:%Y-%m-%d}",
    }


VEIDI["fantasy"] = veids_fantasy


def aina_grafiks(t, c):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pill(d, 0, 250, "NEXT WEEK'S SCHEDULE", fonts("semi", 40), ZILS, MELNS, center=True)
    teksts_c(d, 360, c["nedela"], fonts("black", 92), BALTS)
    y = 540
    for nos, saraksts, kr in (("4 GAMES  →  TARGET THEIR PLAYERS", c["cetri"], ZALS), ("2 GAMES  →  BENCH OR DROP", c["divi"], SARKANS)):
        if not saraksts:
            continue
        teksts_c(d, y, nos, ietilpinat(d, nos, "bold", 48, W - 120), kr)
        y += 90
        f = fonts("bold", 46)
        rinda, pw, gap = 5, 176, 18
        for i, kom in enumerate(saraksts):
            k = ease((t - 0.25 - 0.05 * i) / 0.35)
            if k <= 0:
                continue
            ri, ci = divmod(i, rinda)
            n_rinda = min(rinda, len(saraksts) - ri * rinda)
            x0 = (W - (n_rinda * pw + (n_rinda - 1) * gap)) / 2 + ci * (pw + gap)
            yy = y + ri * 108 + (1 - k) * 30
            d.rounded_rectangle([x0, yy, x0 + pw, yy + 88], radius=44, fill=ar_alfa(kkrasa(kom), 255 * k))
            d.text((x0 + (pw - platums(d, kom, f)) / 2, yy + 14), kom, font=f, fill=ar_alfa(uz_fona(kkrasa(kom)), 255 * k))
        y += ((len(saraksts) - 1) // rinda + 1) * 108 + 70
    teksts_c(d, max(y, 1500), "Everyone else plays 3", fonts("reg", 42), PELEKS)
    return im


def aina_fantasy(t, c):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    akc = c["akc"]
    pill(d, 0, 250, c["augsa"], ietilpinat(d, c["augsa"], "semi", 40, W - 160), akc, MELNS, center=True)
    x0, y0, x1, y1 = 70, 380, W - 70, 1640
    d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=(15, 23, 42, 235), outline=(255, 255, 255, 30), width=3)
    d.rounded_rectangle([x0, y0, x1, y0 + 22], radius=11, fill=c["bkr"])
    d.text((x0 + 50, y0 + 60), f"#{c['nr']}", font=fonts("black", 92), fill=akc)
    fb = fonts("bold", 48)
    pill(d, x1 - 50 - platums(d, c["badge"], fb) - 68, y0 + 80, c["badge"], fb, c["bkr"], uz_fona(c["bkr"]), pad=(34, 14))
    d.text((x0 + 50, y0 + 200), c["v1"].upper(), font=fonts("semi", 50), fill=PELEKS)
    d.text((x0 + 50, y0 + 258), c["v2"].upper(), font=ietilpinat(d, c["v2"].upper(), "black", 112, x1 - x0 - 100), fill=BALTS)
    d.text((x0 + 50, y0 + 400), c["info"], font=ietilpinat(d, c["info"], "reg", 40, x1 - x0 - 100), fill=PELEKS)
    # statistikas flīzes 3 × 2
    tw_, th_, gap = (x1 - x0 - 100 - 2 * 22) / 3, 150, 22
    for i, (lab, val, sub) in enumerate(c["flizes"]):
        k = ease((t - 0.3 - 0.08 * i) / 0.35)
        if k <= 0:
            continue
        ri, ci = divmod(i, 3)
        fx, fy = x0 + 50 + ci * (tw_ + gap), y0 + 480 + ri * (th_ + gap) + (1 - k) * 24
        d.rounded_rectangle([fx, fy, fx + tw_, fy + th_], radius=24, fill=ar_alfa(TUMSS, 255 * k))
        d.text((fx + 22, fy + 16), lab, font=fonts("semi", 28), fill=ar_alfa(PELEKS, 255 * k))
        d.text((fx + 22, fy + 52), val, font=ietilpinat(d, val, "black", 62, tw_ - 40), fill=ar_alfa(BALTS, 255 * k))
        if sub:
            krs = ZALS if sub.startswith("▲") else (SARKANS if sub.startswith("▼") else PELEKS)
            fs = fonts("semi", 26)
            d.text((fx + tw_ - 18 - platums(d, sub, fs), fy + 18), sub, font=fs, fill=ar_alfa(krs, 255 * k))
    # nākamās nedēļas pretinieki
    yg = y0 + 850
    d.text((x0 + 50, yg), "NEXT WEEK", font=fonts("semi", 36), fill=PELEKS)
    pr = c["pretinieki"]
    if pr:
        n = len(pr)
        pw = min(200, (x1 - x0 - 100 - (n - 1) * 16) / n)
        for i, (dn, o, kr) in enumerate(pr):
            k = ease((t - 0.8 - 0.07 * i) / 0.3)
            if k <= 0:
                continue
            px = x0 + 50 + i * (pw + 16)
            d.rounded_rectangle([px, yg + 52, px + pw, yg + 172], radius=22, fill=ar_alfa(kr, 200 * k))
            fd, fo = fonts("semi", 28), ietilpinat(d, o, "black", 44, pw - 20)
            d.text((px + (pw - platums(d, dn, fd)) / 2, yg + 64), dn, font=fd, fill=ar_alfa(BALTS, 230 * k))
            d.text((px + (pw - platums(d, o, fo)) / 2, yg + 102), o, font=fo, fill=ar_alfa(BALTS, 255 * k))
    k2 = ease((t - 1.3) / 0.4)
    if k2 > 0:
        teksts_c(d, y0 + 1040, c["liels"], fonts("black", int(150 * (0.75 + 0.25 * k2))), ar_alfa(akc, 255 * k2))
        teksts_c(d, y0 + 1200, c["apaksa"], ietilpinat(d, c["apaksa"], "reg", 40, x1 - x0 - 80), ar_alfa(PELEKS, 255 * k2))
    return im


def zimet_thumbnail(th, fails):
    """YouTube Shorts / TikTok vāks 1080×1920. Viss svarīgais – centrā (y 420–1500), jo dažās vietās attēls tiek apgriezts."""
    im = fons().convert("RGBA")
    d = ImageDraw.Draw(im)
    bk = kkrasa(th["badge"]) if th.get("badge") else ZILS
    # komandas krāsas "mirdzums" aiz skaitļa
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W / 2 - 420, 900, W / 2 + 420, 1440], fill=ar_alfa(bk, 70))
    from PIL import ImageFilter
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(im)
    pill(d, 0, 300, th["tag"], fonts("semi", 40), ZILS, MELNS, center=True)
    y = 430
    for i, r in enumerate(th["hook"]):
        teksts_c(d, y, r, ietilpinat(d, r, "black", 140, W - 100), DZELTENS if i == len(th["hook"]) - 1 else BALTS)
        y += 158
    if th.get("badge"):
        pill(d, 0, y + 36, th["badge"], fonts("bold", 60), bk, uz_fona(bk), pad=(40, 14), center=True)
        y += 130
    else:
        y += 40
    v = str(th["vards"]).upper()
    teksts_c(d, y, v, ietilpinat(d, v, "black", 150, W - 100), BALTS)
    y += 200
    teksts_c(d, y, th["skaitlis"], ietilpinat(d, th["skaitlis"], "black", 260, W - 100), th["kr"])
    y += 300
    teksts_c(d, y, th["apaksa"], ietilpinat(d, th["apaksa"], "semi", 54, W - 120), PELEKS)
    apaksa2 = th.get("nedela") or (f"STATS THROUGH {dat(th['datums'], True).upper()}" if th.get("datums") else "")
    if apaksa2:
        teksts_c(d, 1640, apaksa2, fonts("semi", 40), ar_alfa(PELEKS, 220))
    im.convert("RGB").save(fails, "PNG")


# ================================================================ balss un video

def ierunat(teksti, balss, mape):
    try:
        import edge_tts
    except ImportError:
        print("BALSS: nav edge-tts šim Python → palaid:  python -m pip install edge-tts   (video tiks bez skaņas)")
        return None
    if not shutil.which("ffprobe"):
        print("BALSS: nav ffprobe (nāk kopā ar ffmpeg) – pārinstalē ffmpeg (video tiks bez skaņas)")
        return None

    async def viens(txt, fails):
        await edge_tts.Communicate(txt, balss, rate="+8%").save(fails)
    out = []
    for i, txt in enumerate(teksti):
        f = os.path.join(mape, f"a{i}.mp3")
        try:
            asyncio.run(viens(txt, f))
        except Exception as ex:                                       # noqa: BLE001
            print(f"BALSS neizdevās: {type(ex).__name__}: {ex} – video bez skaņas (vai ir interneta savienojums?)")
            return None
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                             capture_output=True, text=True).stdout.strip()
        out.append((f, float(dur or 0)))
    return out


def renderet(s, izvade, kanals="", balss=None):
    if not shutil.which("ffmpeg"):
        raise SystemExit("Nav ffmpeg (Windows: winget install ffmpeg, tad jauns terminālis).")
    ainas = [("intro", None, 3.2)] + [("karte", c, 3.6) for c in s["kartes"]] + [("outro", None, 4.5 if s["outro"].get("cta") else 3.2)]
    tmp = tempfile.mkdtemp(prefix="shorts_")
    audio = ierunat(s["runa"], balss, tmp) if balss else None
    if audio and len(audio) == len(ainas) and all(dur > 0 for _, dur in audio):
        ainas = [(v, c, max(ilg, dur + 0.45)) for (v, c, ilg), (_, dur) in zip(ainas, audio)]
    else:
        if audio:
            print("BALSS: audio faili tukši vai nepilnīgi – video bez skaņas.")
        audio = None
    kopa = sum(a[2] for a in ainas)
    bg = fons()
    video_tmp = os.path.join(tmp, "v.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          video_tmp], stdin=subprocess.PIPE)
    t0 = 0.0
    for veids, c, ilg in ainas:
        for fr in range(int(round(ilg * FPS))):
            t = fr / FPS
            if veids == "intro":
                sl, (dx, alfa) = aina_intro(t, s["intro"]), (0, min(1, t / 0.25))
            elif veids == "outro":
                sl, (dx, alfa) = aina_outro(t, s["outro"], kanals), (0, min(1, t / 0.25))
            else:
                fn = {"fantasy": aina_fantasy, "grafiks": aina_grafiks}.get(c.get("tips"), aina_karte)
                sl, (dx, alfa) = fn(t, c), slide(t, ilg)
            kadrs = bg.copy()
            if alfa < 1:
                sl.putalpha(sl.getchannel("A").point(lambda v: int(v * alfa)))
            kadrs.paste(sl, (int(dx), 0), sl)
            dd = ImageDraw.Draw(kadrs, "RGBA")
            fz = ietilpinat(dd, s["zimogs"], "semi", 34, W - 100)
            teksts_c(dd, 170, s["zimogs"], fz, ar_alfa(PELEKS, 235))
            dd.rectangle([0, 0, W, 10], fill=(255, 255, 255, 30))
            dd.rectangle([0, 0, W * min(1, (t0 + t) / kopa), 10], fill=DZELTENS)
            p.stdin.write(kadrs.tobytes())
        t0 += ilg
    p.stdin.close()
    p.wait()
    if audio:
        ievades, filtri, sak = [], [], 0.0
        for i, ((f, _), a) in enumerate(zip(audio, ainas)):
            ievades += ["-i", f]
            ms = int((sak + 0.15) * 1000)
            filtri.append(f"[{i + 1}:a]adelay={ms}|{ms}[a{i}]")
            sak += a[2]
        filtri.append("".join(f"[a{i}]" for i in range(len(audio))) + f"amix=inputs={len(audio)}:normalize=0[aout]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_tmp, *ievades, "-filter_complex", ";".join(filtri),
                        "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", izvade], check=True)
    else:
        shutil.move(video_tmp, izvade)
    shutil.rmtree(tmp, ignore_errors=True)
    return kopa, bool(audio)


def cta_apraksts(kontakts):
    kam = f"DM {kontakts}" if kontakts else "Send me a message"
    return ("\n📊 WANT THE FULL FANTASY SHEET?\n"
            "Google Sheets planner with every skater's form, shots, xG, ice time, power-play points, next week's schedule "
            "and ESPN rostered % – updated automatically every day.\n"
            f"{kam} or comment \"SHEET\" below for access & pricing.\n\n")


def cta_komentars(kontakts):
    kam = f"DM {kontakts}" if kontakts else "send me a message"
    return (f"📊 Want the full fantasy hockey sheet (Google Sheets, updated daily)? Comment \"SHEET\" or {kam} "
            "for access & pricing!")


def gaidosie_atskati(mape):
    """Saraksts ar video mapēm, kurām INFO.txt prasa atskatu, bet tas vēl nav izveidots."""
    sod = pd.Timestamp.now().normalize()
    rindas = []
    for d in sorted(os.listdir(mape)) if os.path.isdir(mape) else []:
        p = os.path.join(mape, d, "INFO.txt")
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8").read()
        if "ATSKATS:      vajadzīgs" not in t or "ATSKATS IZVEIDOTS" in t:
            continue
        ieteic = next((r.split(":", 1)[1].strip()[:10] for r in t.splitlines() if r.strip().startswith("ieteicamais")), "")
        agr = next((r.split(":", 1)[1].strip()[:10] for r in t.splitlines() if r.strip().startswith("agrākais")), "")
        if agr and sod < pd.Timestamp(agr):
            stav = f"vēl par agru (no {agr})"
        elif ieteic and sod <= pd.Timestamp(ieteic):
            stav = f"var taisīt – ieteicams {ieteic}"
        else:
            stav = f"JĀTAISA (ieteicamais datums {ieteic} pagājis)"
        rindas.append(f"  {d:<34} {stav}\n      python shorts.py --atskats {os.path.relpath(os.path.join(mape, d), BASE)}")
    print("Gaidošie atskati:" if rindas else "Gaidošu atskatu nav.")
    print("\n".join(rindas))
    return 0


def main():
    ap = argparse.ArgumentParser(description="NHL xG Shorts → MP4")
    ap.add_argument("--veids", choices=list(VEIDI), default="speletaji")
    ap.add_argument("--atskats", default=None, help="atskats par agrāk izveidotu video: tā mape (video/2026-10-26_speletaji) vai .json fails")
    ap.add_argument("--dienas", type=int, default=None, help="tikai pēdējās N dienas (noklusējums: visa sezona)")
    ap.add_argument("--lidz", default=None, help="izmantot datus tikai līdz šim datumam (YYYY-MM-DD)")
    ap.add_argument("--nedela", default=None, help="fantasy: nedēļas pirmdiena YYYY-MM-DD (noklusējums: nākamā pirmdiena)")
    ap.add_argument("--max-rostered", type=float, default=40, help="fantasy: maks. %% rostered ESPN (noklusējums 40)")
    ap.add_argument("--drop", type=int, default=2, help="fantasy: cik 'drop' spēlētājus rādīt (0 = nerādīt)")
    ap.add_argument("--drop-min-rostered", type=float, default=50, help="fantasy drop: min. %% rostered (noklusējums 50)")
    ap.add_argument("--drop-max-rostered", type=float, default=90, help="fantasy drop: maks. %% rostered – zvaigznes neiesakām mest ārā (90)")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--min-metieni", type=int, default=15)
    ap.add_argument("--balss", default="en-US-AndrewNeural", help="edge-tts balss (piem. en-US-GuyNeural)")
    ap.add_argument("--bez-balss", action="store_true")
    ap.add_argument("--kanals", default="", help="kanāla nosaukums beigu kadram, piem. @nhlxg")
    ap.add_argument("--mape", default=os.path.join(BASE, "video"))
    ap.add_argument("--kontakts", default="", help="kur rakstīt, lai saņemtu Google Sheets tabulu (piem. @nhlxg vai e-pasts); "
                                                    "noklusējums – --kanals")
    ap.add_argument("--cta", action="store_true", help="piedāvājums par Google Sheets tabulu arī xG video (fantasy video – vienmēr)")
    ap.add_argument("--bez-cta", action="store_true", help="bez piedāvājuma par Google Sheets tabulu")
    ap.add_argument("--gaida", action="store_true", help="parādīt video, kuriem vēl jāizveido atskats (un kad)")
    a = ap.parse_args()
    if a.gaida:
        return gaidosie_atskati(a.mape)
    if a.atskats and os.path.isdir(a.atskats):                     # var norādīt arī mapi – tad ņem tās .json failu
        js = sorted(f for f in os.listdir(a.atskats) if f.endswith(".json"))
        if not js:
            print(f"Mapē {a.atskats} nav .json faila (atskats iespējams tikai speletaji / komandas / vartsargi video).")
            return 1
        a.atskats = os.path.join(a.atskats, js[0])
    if a.atskats and not os.path.exists(a.atskats):
        print(f"Nav faila {a.atskats}")
        return 1
    m = ielasit(a.lidz)
    if a.atskats:
        s = atskats(a.atskats, m, a)
        with open(a.atskats, encoding="utf-8") as f:
            veids_txt = "atskats_" + json.load(f)["veids"]
    else:
        s = VEIDI[a.veids](m, a)
        veids_txt = a.veids
    if s is None:
        print("Nepietiek datu (samazini --min-metieni, palielini --dienas vai pagaidi vēl dažas spēles).")
        return 1
    kontakts = a.kontakts or a.kanals
    ar_cta = not a.bez_cta and (a.veids == "fantasy" and not a.atskats or a.cta)
    if ar_cta:
        kam = f"DM {kontakts}" if kontakts else "Message me"
        s["outro"]["cta"] = ("WANT THE FULL FANTASY SHEET?", "Google Sheets · updated daily", f"{kam} for access & pricing")
        s["runa"][-1] += " Want the full fantasy sheet, updated every day? Message me for access and pricing."

    # katrai ģenerācijai sava mape: video/<šodienas datums>_<veids>/ (ja jau ir – _2, _3 ...)
    tagad = pd.Timestamp.now()
    mape = os.path.join(a.mape, f"{tagad:%Y-%m-%d}_{veids_txt}")
    n = 2
    while os.path.exists(mape):
        mape = os.path.join(a.mape, f"{tagad:%Y-%m-%d}_{veids_txt}_{n}")
        n += 1
    os.makedirs(mape)
    izv = os.path.join(mape, (s.get("nosaukums") or f"xg_{a.veids}_{s['lidz']}") + ".mp4")
    kopa, ar_balsi = renderet(s, izv, a.kanals, None if a.bez_balss else a.balss)
    if s.get("thumb"):
        zimet_thumbnail(s["thumb"], os.path.join(mape, "thumbnail.png"))
    with open(izv[:-4] + ".txt", "w", encoding="utf-8") as f:
        f.write(f"VIRSRAKSTS:\n{s['virsraksts']} #NHL #Shorts\n\nAPRAKSTS:\n{s['apraksts']}\nData: {s['periods']}\n"
                + "\n".join(s["saraksts"])
                + "\nxG from our own model (unblocked shots, empty-net goals excluded).\n"
                + (cta_apraksts(kontakts) if ar_cta else "")
                + "#NHL #hockey #NHLstats #xG #fantasyhockey #Shorts\n\n"
                + (f"PIESPRAUŽAMAIS KOMENTĀRS:\n{cta_komentars(kontakts)}\n\n" if ar_cta else "")
                + "RUNAS TEKSTS (pa ainām):\n"
                + "\n".join(f"{i}. {t}" for i, t in enumerate(s["runa"])) + "\n")
    json_fails = None
    if "momentuzn" in s:
        json_fails = izv[:-4] + ".json"
        with open(json_fails, "w", encoding="utf-8") as f:
            json.dump({"veids": a.veids, "lidz": s["lidz"], "dienas": a.dienas, "periods": s["periods"],
                       "izveidots": tagad.strftime("%Y-%m-%d %H:%M"), "momentuzn": s["momentuzn"]},
                      f, ensure_ascii=False, indent=1)

    # INFO.txt: kad un kā ģenerēts, kādi dati, vai un kad jātaisa atskats
    komanda = "python shorts.py " + " ".join(sys.argv[1:])
    info = [f"VEIDS:        {veids_txt}",
            f"ĢENERĒTS:     {tagad:%Y-%m-%d %H:%M} ({['pirmdiena', 'otrdiena', 'trešdiena', 'ceturtdiena', 'piektdiena', 'sestdiena', 'svētdiena'][tagad.weekday()]})",
            f"DATI:         {s['periods']}",
            f"VIDEO:        {os.path.basename(izv)} ({kopa:.0f} s, {'ar balsi' if ar_balsi else 'bez skaņas'})",
            "SĪKTĒLS:      thumbnail.png (YouTube: Shorts → Edit → Thumbnail; TikTok: Edit cover → Upload)",
            f"KOMANDA:      {komanda}", ""]
    if json_fails:
        agrakais = tagad.normalize() + timedelta(days=14)
        ieteicamais = agrakais + timedelta(days=(3 - agrakais.weekday()) % 7)        # pirmā ceturtdiena pēc 14 dienām
        info += ["ATSKATS:      vajadzīgs",
                 f"  agrākais:    {agrakais:%Y-%m-%d} (pēc 14 dienām)",
                 f"  ieteicamais: {ieteicamais:%Y-%m-%d} (ceturtdiena pēc grafika)",
                 f"  komanda:     python shorts.py --atskats {os.path.relpath(mape, BASE)} --kanals {a.kanals or '@tavskanals'}"]
    elif a.atskats:
        orig = os.path.dirname(os.path.abspath(a.atskats))
        info += [f"ATSKATS PAR:  {os.path.relpath(orig, BASE)}", "Šis ir atskats – jauns atskats nav vajadzīgs."]
        # oriģinālajā INFO.txt atzīmē, ka atskats ir izveidots
        oi = os.path.join(orig, "INFO.txt")
        if os.path.exists(oi):
            with open(oi, "a", encoding="utf-8") as f:
                f.write(f"\nATSKATS IZVEIDOTS: {tagad:%Y-%m-%d %H:%M} → {os.path.relpath(mape, BASE)}\n")
    else:
        info += ["ATSKATS:      nav vajadzīgs (fantasy ieteikumi ir par vienu konkrētu nedēļu)"]
    with open(os.path.join(mape, "INFO.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(info) + "\n")
    print(f"Gatavs: {os.path.relpath(mape, BASE)}/ ({kopa:.0f} s, {'ar balsi' if ar_balsi else 'bez skaņas'})")
    for r in info[7:]:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
