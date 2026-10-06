"""
NHL dienas statistika no oficiālajiem NHL serveriem (api-web.nhle.com un api.nhle.com).

Katrai pabeigtai spēlei tiek ielasīti: landing, boxscore, play-by-play un maiņu dati,
un ierakstīti vairākās CSV tabulās mapē DATU_MAPE:

  speles.csv     - viena rinda uz spēli (rezultāts, periodi, metieni, sodi, vairākums, komandu statistika)
  speletaji.csv  - laukuma spēlētāju statistika no boxscore (viena rinda uz spēlētāju uz spēli)
  vartsargi.csv  - vārtsargu statistika (arī pa spēka situācijām)
  varti.csv      - katri gūtie vārti (autors, piespēles, spēka situācija, laiks)
  notikumi.csv   - pilns play-by-play (katrs notikums ar koordinātām, spēlētāju ID, situāciju)
  sastavi.csv    - spēles sastāvi (playerId -> vārds, numurs, pozīcija)
  mainas.csv     - maiņu dati (kurš spēlētājs kad bija laukumā)
  tiesnesi.csv   - spēles tiesneši un līnijtiesneši + spēlē piešķirtie noraidījumi (tiesnešu statistikai)

SVARĪGI: statistikā tiek lietots tikai pamatlaiks (1.-3. periods). Papildlaiks (OT) un pēcspēles metieni (SO)
tiek tikai saglabāti kolonnās *_ot un kopsummās vizuālai attēlošanai (piem., home_ot, home_sog_ot, home_pen_ot).
Sodu skaits un sodu minūtes (pim_total) ir tikai minor sodi (dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem;
oficiālās kopējās sodu minūtes ir pim_official), vairākuma rādītāji un tukšo vārtu/mazākuma vārti ir pamatlaika; sog_total ir oficiālā
kopsumma (arī papildlaiks), tāpēc statistikā jālieto sog_p1..p3.

Lietošana:
  python nhl_dati.py                        # pēdējās 3 dienas (pēc ASV austrumu laika), jau esošās spēles tiek izlaistas
  python nhl_dati.py 2026-10-01             # konkrēta diena
  python nhl_dati.py 2026-10-01 2026-10-07  # datumu intervāls (vēstures aizpildīšanai)
  python nhl_dati.py --raw                  # papildus saglabā neapstrādātos JSON mapē raw\\
  python nhl_dati.py --vieglais             # bez lielajām tabulām notikumi.csv un mainas.csv (GitHub Actions)
  python nhl_dati.py 2026-09-29 2026-10-02 --atjaunot   # pārraksta jau esošās spēles (piem., lai papildinātu trūkstošos laukus)

Nepieciešams:  pip install requests tzdata
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

# ----------------------------------------------------------------------------
# IESTATĪJUMI
# ----------------------------------------------------------------------------
DATU_MAPE = os.environ.get("NHL_DATU_MAPE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dati")   # pēc noklusējuma: mape "dati" blakus skriptam
API_WEB = "https://api-web.nhle.com/v1"
API_STATS = "https://api.nhle.com/stats/rest/en"

# 1 = pirmssezona, 2 = regulārā sezona, 3 = izslēgšanas spēles
SPELU_TIPI = (2, 3)
VIEGLAIS = "--vieglais" in sys.argv   # GitHub Actions: bez lielajām tabulām (notikumi, mainas)
ATJAUNOT = "--atjaunot" in sys.argv   # pārlasa un pārraksta arī jau esošās spēles norādītajā intervālā
# --pedejas-stundas=N: tikai spēles, kas beigušās pēdējo N stundu laikā (tās vienmēr tiek pārlasītas), datumi aprēķināti automātiski
PEDEJAS_STUNDAS = next((float(a.split("=", 1)[1]) for a in sys.argv if a.startswith("--pedejas-stundas=") and a.split("=", 1)[1]), None)
SPELES_ILGUMS_H = 3.5   # spēle (ar pārtraukumiem un papildlaiku) beidzas ne vēlāk kā ~3,5 h pēc sākuma
IEGUT_MAINAS = not VIEGLAIS      # maiņu dati (liela tabula)
LIELAS_TABULAS = ("notikumi", "mainas")
KAVESANAS = 0.25         # pauze starp pieprasījumiem (sekundes)
ATPAKAL_DIENAS = 3       # cik dienas atpakaļ pārbaudīt, ja datumi nav norādīti (jau esošās spēles tiek izlaistas)
RAW = "--raw" in sys.argv

ET = ZoneInfo("America/New_York")   # NHL spēļu datumi ir pēc ASV austrumu laika
PERIODI = ("p1", "p2", "p3", "ot")
REG_PERIODI = ("p1", "p2", "p3")   # statistikā tiek lietots tikai pamatlaiks; papildlaiks (ot) tiek tikai saglabāts

# ----------------------------------------------------------------------------
# KOLONNAS
# ----------------------------------------------------------------------------


def pari(prefikss, sufiksi):
    """home_X, away_X pāri katram sufiksam."""
    out = []
    for s in sufiksi:
        out += [f"home_{prefikss}{s}", f"away_{prefikss}{s}"]
    return out


SPELES_KOL = (
    ["datums", "game_id", "sezona", "speles_tips", "sakums_utc", "arena",
     "spele_beidzas", "uzvaretajs", "home_team", "away_team", "home_total", "away_total"]
    + pari("", PERIODI)                         # vārti pa periodiem
    + pari("pim_", ("total",) + PERIODI)        # minor sodu minūtes (bez major, 10 min disciplinārajiem un kautiņiem)
    + pari("pen_", PERIODI)                     # minor sodu skaits pa periodiem (dubultais minor = 2)
    + pari("sog_", ("total",) + PERIODI)        # metieni vārtos
    + ["home_ppg", "away_ppg", "home_pp_sog", "away_pp_sog"]
    + pari("", ("pp_opp", "pen_count", "sh_goals", "en_goals", "missed_shots", "pim_official",
                "hits", "blocked_shots", "giveaways", "takeaways", "faceoff_pct"))
    + ["star1", "star2", "star3"]
)

SKATER_STAT = ["goals", "assists", "points", "plusMinus", "pim", "hits", "powerPlayGoals", "sog",
               "faceoffWinningPctg", "toi", "blockedShots", "shifts", "giveaways", "takeaways"]
GOALIE_STAT = ["starter", "decision", "toi", "shotsAgainst", "saves", "goalsAgainst", "savePctg",
               "evenStrengthShotsAgainst", "powerPlayShotsAgainst", "shorthandedShotsAgainst",
               "saveShotsAgainst", "evenStrengthGoalsAgainst", "powerPlayGoalsAgainst",
               "shorthandedGoalsAgainst", "pim"]
SPELETAJA_PAMATS = ["datums", "game_id", "team", "home_away", "playerId", "vards", "numurs", "pozicija"]

DETAIL_LAUKI = [
    "eventOwnerTeamId", "xCoord", "yCoord", "zoneCode", "shotType", "shootingPlayerId", "goalieInNetId",
    "scoringPlayerId", "assist1PlayerId", "assist2PlayerId", "awayScore", "homeScore", "awaySOG", "homeSOG",
    "reason", "secondaryReason", "blockingPlayerId", "hittingPlayerId", "hitteePlayerId",
    "winningPlayerId", "losingPlayerId", "playerId",
    "typeCode", "descKey", "duration", "committedByPlayerId", "drawnByPlayerId", "servedByPlayerId",
]
NOTIKUMU_KOL = (
    ["datums", "game_id", "event_id", "sort_order", "period", "period_type", "laiks_periodaa", "laiks_atlicis",
     "situacijas_kods", "away_vratsargs", "away_laukumaa", "home_laukumaa", "home_vratsargs",
     "home_aizsargaja_puse", "tips_kods", "tips", "komanda"]
    + DETAIL_LAUKI + ["citi_dati"]
)
VARTU_KOL = ["datums", "game_id", "period", "period_type", "laiks", "komanda", "strength", "goal_modifier",
             "shot_type", "situacijas_kods", "scorer_id", "scorer", "assist1_id", "assist1",
             "assist2_id", "assist2", "home_score", "away_score"]
TIESNESU_KOL = ["datums", "game_id", "sezona", "loma", "vards", "home_team", "away_team",
               "pen_home", "pen_away", "pen_total", "pen_p1", "pen_p2", "pen_p3", "pim_home", "pim_away"]
MAINU_KOL = ["datums", "game_id", "team", "playerId", "vards", "period", "shiftNumber",
             "startTime", "endTime", "duration"]

TABULAS = {
    "speletaji": ("speletaji.csv", SPELETAJA_PAMATS + SKATER_STAT + ["noraid"]),      # noraid = minor noraidījumi pamatlaikā
    "vartsargi": ("vartsargi.csv", SPELETAJA_PAMATS + GOALIE_STAT),
    "varti": ("varti.csv", VARTU_KOL),
    "notikumi": ("notikumi.csv", NOTIKUMU_KOL),
    "sastavi": ("sastavi.csv", SPELETAJA_PAMATS),
    "mainas": ("mainas.csv", MAINU_KOL),
    "tiesnesi": ("tiesnesi.csv", TIESNESU_KOL),
    "speles": ("speles.csv", SPELES_KOL),   # pēdējā: spēle ir "gatava" tikai tad, kad tā ierakstīta šeit
}

# ----------------------------------------------------------------------------
# PALĪGFUNKCIJAS
# ----------------------------------------------------------------------------
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})
kludu_skaits = 0


def get_json(url, meginajumi=3):
    """Pieprasījums ar timeout un atkārtošanu. Atgriež None, ja neizdodas."""
    for i in range(1, meginajumi + 1):
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200:
                return r.json()
            print(f"  Kļūda {r.status_code}: {url} (mēģinājums {i}/{meginajumi})")
        except (requests.RequestException, ValueError) as e:
            print(f"  Savienojuma kļūda: {e} (mēģinājums {i}/{meginajumi})")
        time.sleep(2 * i)
    return None


def teksts(x):
    if isinstance(x, dict):
        return x.get("default") or ""
    return "" if x is None else str(x)


def atrast_sarakstu(obj, atslega):
    """Meklē pirmo sarakstu ar doto atslēgu jebkurā JSON dziļumā (neatkarīgi no precīza ceļa)."""
    if isinstance(obj, dict):
        v = obj.get(atslega)
        if isinstance(v, list):
            return v
        for x in obj.values():
            r = atrast_sarakstu(x, atslega)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for x in obj:
            r = atrast_sarakstu(x, atslega)
            if r is not None:
                return r
    return None


def amatpersonas_vards(x):
    """Tiesneša vārds no dažādiem iespējamiem formātiem: 'Vārds', {'default': 'Vārds'}, {'firstName':..,'lastName':..}."""
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        v = teksts(x.get("default")) or teksts(x.get("name")) or teksts(x.get("fullName"))
        if v:
            return v.strip()
        return f"{teksts(x.get('firstName'))} {teksts(x.get('lastName'))}".strip()
    return ""


def sadalit_dalu(x):
    """'6/8' -> (6, 8); ja nevar nolasīt -> (None, None)."""
    try:
        a, b = str(x).split("/")
        return int(a), int(b)
    except (ValueError, AttributeError):
        return None, None


def minor_sodu_skaits(det):
    """
    Cik minor sodu (2 min) ir šajā sodu notikumā: minor un komandas (bench) minor = 1, dubultais minor (4 min) = 2.
    0: major (5 min), 10 min disciplinārais (misconduct), spēles disciplinārais (game misconduct), match, kautiņi, soda metiens.
    Statistikā "noraidījumi" ir tikai minor sodi, jo tieši tie dod pretiniekam vairākumu.
    """
    kods = str(det.get("typeCode") or "").upper()
    desc = str(det.get("descKey") or "").lower()
    ilgums = det.get("duration") or 0
    if "misconduct" in desc or "fight" in desc or "match" in desc or kods in ("MAJ", "MIS", "GMIS", "GAM", "MAT", "MATCH", "PS"):
        return 0
    if ilgums == 2:
        return 1
    if ilgums == 4:
        return 2
    return 0


def perioda_atslega(pd):
    """'p1' / 'p2' / 'p3' / 'ot' vai None (pēcspēles metieni / nezināms)."""
    tips = pd.get("periodType")
    num = pd.get("number")
    if tips == "SO":
        return None
    if tips == "OT":
        return "ot"
    if num in (1, 2, 3):
        return f"p{num}"
    if isinstance(num, int) and num > 3:
        return "ot"
    return None


def situacija(kods):
    """situationCode: [away vārtsargs][away laukumā][home laukumā][home vārtsargs]."""
    k = str(kods or "")
    if len(k) == 4 and k.isdigit():
        return k[0], k[1], k[2], k[3]
    return "", "", "", ""


def noklusejuma_intervals():
    ta = datetime.now(ET).date()
    return (ta - timedelta(days=ATPAKAL_DIENAS)).isoformat(), (ta - timedelta(days=1)).isoformat()


def datumu_saraksts(no, lidz):
    d = datetime.strptime(no, "%Y-%m-%d").date()
    e = datetime.strptime(lidz, "%Y-%m-%d").date()
    while d <= e:
        yield d.isoformat()
        d += timedelta(days=1)


def saglabat_raw(gid, nosaukums, dati):
    if not RAW or dati is None:
        return
    mape = os.path.join(DATU_MAPE, "raw")
    os.makedirs(mape, exist_ok=True)
    with open(os.path.join(mape, f"{gid}_{nosaukums}.json"), "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False)


# ----------------------------------------------------------------------------
# CSV DARBS
# ----------------------------------------------------------------------------
ID_KESS = {}


def cels(nos):
    return os.path.join(DATU_MAPE, TABULAS[nos][0])


def sagatavot_failus():
    """Ja esošā CSV galvene neatbilst: pievienotas kolonnas tiek papildinātas vietā, citādi vecais fails tiek pārsaukts."""
    os.makedirs(DATU_MAPE, exist_ok=True)
    for nos, (_, kol) in TABULAS.items():
        c = cels(nos)
        if not os.path.isfile(c):
            continue
        with open(c, newline="", encoding="utf-8-sig") as f:
            galvene = next(csv.reader(f), None)
        if galvene != kol and galvene and set(galvene) <= set(kol):
            # tikai pievienotas jaunas kolonnas: fails tiek papildināts vietā, vecie ieraksti paliek (jaunās kolonnas tukšas)
            with open(c, newline="", encoding="utf-8-sig") as f:
                rindas = list(csv.DictReader(f))
            with open(c, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=kol, extrasaction="ignore")
                w.writeheader()
                w.writerows(rindas)
            print(f"Piezīme: {os.path.basename(c)} papildināts ar jaunām kolonnām: {[x for x in kol if x not in galvene][:6]}...")
        elif galvene != kol:
            jauns = c[:-4] + "_vecs_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
            os.replace(c, jauns)
            print(f"Brīdinājums: {os.path.basename(c)} galvene neatbilda, vecais fails pārsaukts par {os.path.basename(jauns)}")


def ielasit_id(nos):
    if nos in ID_KESS:
        return ID_KESS[nos]
    ids = set()
    c = cels(nos)
    if os.path.isfile(c):
        with open(c, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                ids.add(str(r.get("game_id")))
    ID_KESS[nos] = ids
    return ids


def dzest_spelu_rindas(nos, ids):
    """Izdzēš no tabulas visas rindas ar norādītajiem game_id (lai tās varētu ierakstīt no jauna)."""
    c = cels(nos)
    if not ids or not os.path.isfile(c):
        return
    with open(c, newline="", encoding="utf-8-sig") as f:
        rindas = list(csv.DictReader(f))
    atlikt = [r for r in rindas if str(r.get("game_id")) not in ids]
    if len(atlikt) != len(rindas):
        with open(c, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=TABULAS[nos][1], extrasaction="ignore")
            w.writeheader()
            w.writerows(atlikt)
    ID_KESS.pop(nos, None)


def pievienot(nos, rindas):
    """Pievieno rindas; spēles, kas jau ir šajā failā, tiek izlaistas (nav dublikātu)."""
    if not rindas:
        return 0
    esosie = ielasit_id(nos)
    jaunas = [r for r in rindas if str(r.get("game_id")) not in esosie]
    if not jaunas:
        return 0
    c = cels(nos)
    jauns_fails = not os.path.isfile(c)
    with open(c, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=TABULAS[nos][1], extrasaction="ignore")
        if jauns_fails:
            w.writeheader()
        w.writerows(jaunas)
    esosie.update(str(r.get("game_id")) for r in jaunas)
    return len(jaunas)


# ----------------------------------------------------------------------------
# VIENAS SPĒLES APSTRĀDE
# ----------------------------------------------------------------------------
def apstradat_spele(spele, datums):
    gid = spele.get("id")
    land = get_json(f"{API_WEB}/gamecenter/{gid}/landing")
    time.sleep(KAVESANAS)
    box = get_json(f"{API_WEB}/gamecenter/{gid}/boxscore")
    time.sleep(KAVESANAS)
    pbp = get_json(f"{API_WEB}/gamecenter/{gid}/play-by-play")
    if not (land and box and pbp):
        print("  Trūkst datu no API, spēle izlaista (tiks mēģināta nākamreiz).")
        return None

    time.sleep(KAVESANAS)
    rr = get_json(f"{API_WEB}/gamecenter/{gid}/right-rail", meginajumi=2)   # tiesneši atrodas šeit (gameInfo)

    maina = None
    if IEGUT_MAINAS:
        time.sleep(KAVESANAS)
        maina = get_json(f"{API_STATS}/shiftcharts?cayenneExp=gameId={gid}", meginajumi=2)
    for nos, dati in (("landing", land), ("boxscore", box), ("pbp", pbp), ("rightrail", rr), ("shifts", maina)):
        saglabat_raw(gid, nos, dati)

    home = land.get("homeTeam") or spele.get("homeTeam") or {}
    away = land.get("awayTeam") or spele.get("awayTeam") or {}
    home_ab, away_ab = teksts(home.get("abbrev")), teksts(away.get("abbrev"))
    home_id, away_id = home.get("id"), away.get("id")
    id2ab = {home_id: home_ab, away_id: away_ab}
    summary = land.get("summary") or {}
    plays = pbp.get("plays") or []

    # ---- pamatinformācija ----
    r = dict.fromkeys(SPELES_KOL, 0)
    tipi = {(p.get("periodDescriptor") or {}).get("periodType") for p in plays}
    beigas = (land.get("gameOutcome") or {}).get("lastPeriodType") or (
        "SO" if "SO" in tipi else "OT" if "OT" in tipi else "REG")
    r.update({
        "datums": datums, "game_id": gid,
        "sezona": land.get("season"), "speles_tips": land.get("gameType"),
        "sakums_utc": land.get("startTimeUTC"), "arena": teksts(land.get("venue")),
        "spele_beidzas": beigas,
        "home_team": home_ab, "away_team": away_ab,
        "home_total": home.get("score", 0), "away_total": away.get("score", 0),
        "star1": "", "star2": "", "star3": "",
    })
    if r["home_total"] != r["away_total"]:
        r["uzvaretajs"] = home_ab if r["home_total"] > r["away_total"] else away_ab
    else:
        r["uzvaretajs"] = ""

    for zv in summary.get("threeStars") or []:
        n = zv.get("star")
        if n in (1, 2, 3):
            r[f"star{n}"] = f"{teksts(zv.get('name'))} ({teksts(zv.get('teamAbbrev'))})"

    # ---- vārti (landing kopsavilkums) ----
    vartu_rindas = []
    pasvarti = set()                           # (perioda numurs, laiks) paštrāpījumiem: NHL tos neieskaita komandas metienos vārtos
    ppg_ot = {"home": 0, "away": 0}           # vārti vairākumā papildlaikā (netiek ieskaitīti statistikā)
    for pd_ in summary.get("scoring") or []:
        pdesc = pd_.get("periodDescriptor") or {}
        pk = perioda_atslega(pdesc)
        for g in pd_.get("goals") or []:
            kom = teksts(g.get("teamAbbrev"))
            puse = "home" if kom == home_ab else "away" if kom == away_ab else None
            if puse is None:
                continue
            if pk:
                r[f"{puse}_{pk}"] += 1
            stipr = g.get("strength")
            if pk in REG_PERIODI:                  # vairākuma / mazākuma / tukšo vārtu statistika: tikai pamatlaiks
                if stipr == "pp":
                    r[f"{puse}_ppg"] += 1
                elif stipr == "sh":
                    r[f"{puse}_sh_goals"] += 1
                if g.get("goalModifier") == "empty-net":
                    r[f"{puse}_en_goals"] += 1
            elif pk == "ot" and stipr == "pp":
                ppg_ot[puse] += 1
            ass = g.get("assists") or []
            a1 = ass[0] if len(ass) > 0 else {}
            a2 = ass[1] if len(ass) > 1 else {}
            if g.get("goalModifier") == "own-goal":
                pasvarti.add((pdesc.get("number"), g.get("timeInPeriod")))
            vartu_rindas.append({
                "datums": datums, "game_id": gid,
                "period": pdesc.get("number"), "period_type": pdesc.get("periodType"),
                "laiks": g.get("timeInPeriod"), "komanda": kom,
                "strength": stipr, "goal_modifier": g.get("goalModifier"),
                "shot_type": g.get("shotType"), "situacijas_kods": g.get("situationCode"),
                "scorer_id": g.get("playerId"),
                "scorer": teksts(g.get("name")) or f"{teksts(g.get('firstName'))} {teksts(g.get('lastName'))}".strip(),
                "assist1_id": a1.get("playerId"), "assist1": teksts(a1.get("name")),
                "assist2_id": a2.get("playerId"), "assist2": teksts(a2.get("name")),
                "home_score": g.get("homeScore"), "away_score": g.get("awayScore"),
            })

    # ---- play-by-play: notikumi, metieni, sodi ----
    notikumu_rindas = []
    kautinu_pim = {"home": 0, "away": 0}
    spel_noraid = {}                           # spēlētāja minor sodu skaits pamatlaikā (playerId → skaits; dubultais minor = 2)
    citi_pim = {"home": 0, "away": 0}          # sodi, kas nav minor (major, 10 min disciplinārie, spēles disciplinārie, match): netiek skaitīti
    pen_per = {"p1": 0, "p2": 0, "p3": 0}      # abu komandu sodu skaits pa periodiem (tiesnešu statistikai)
    ot_pp_sog = {"home": 0, "away": 0}         # metieni vairākumā papildlaikā (tiek atņemti no PP metieniem)
    for p in plays:
        det = p.get("details") or {}
        pdesc = p.get("periodDescriptor") or {}
        pk = perioda_atslega(pdesc)
        tips = p.get("typeDescKey")
        team_id = det.get("eventOwnerTeamId")
        puse = "home" if team_id == home_id else "away" if team_id == away_id else None
        sit = situacija(p.get("situationCode"))

        rinda = {
            "datums": datums, "game_id": gid,
            "event_id": p.get("eventId"), "sort_order": p.get("sortOrder"),
            "period": pdesc.get("number"), "period_type": pdesc.get("periodType"),
            "laiks_periodaa": p.get("timeInPeriod"), "laiks_atlicis": p.get("timeRemaining"),
            "situacijas_kods": p.get("situationCode"),
            "away_vratsargs": sit[0], "away_laukumaa": sit[1], "home_laukumaa": sit[2], "home_vratsargs": sit[3],
            "home_aizsargaja_puse": p.get("homeTeamDefendingSide"),
            "tips_kods": p.get("typeCode"), "tips": tips,
            "komanda": id2ab.get(team_id, ""),
        }
        for k in DETAIL_LAUKI:
            rinda[k] = det.get(k)
        citi = {k: v for k, v in det.items() if k not in DETAIL_LAUKI}
        rinda["citi_dati"] = json.dumps(citi, ensure_ascii=False) if citi else ""
        notikumu_rindas.append(rinda)

        if puse is None:
            continue
        if tips == "penalty":
            ilgums = det.get("duration", 0) or 0
            minori = minor_sodu_skaits(det)
            if "fight" in str(det.get("descKey", "")).lower():
                kautinu_pim[puse] += ilgums
            elif minori == 0:
                citi_pim[puse] += ilgums                  # major / 10 min disciplinārais / spēles disciplinārais: nav noraidījums statistikā
            elif pk:
                r[f"{puse}_pim_{pk}"] += 2 * minori       # minor sodu minūtes (arī papildlaiks pim_ot, tikai vizuālai attēlošanai)
                if pk in REG_PERIODI:
                    r[f"{puse}_pim_total"] += 2 * minori  # kopā = tikai pamatlaiks
                    r[f"{puse}_pen_count"] += minori      # minor sodu skaits pamatlaikā (dubultais minor = 2)
                    pid_ = det.get("committedByPlayerId")
                    if pid_:                              # komandas (bench) sodam spēlētāja nav
                        spel_noraid[pid_] = spel_noraid.get(pid_, 0) + minori
                r[f"{puse}_pen_{pk}"] += minori           # minor sodu skaits pa periodiem (arī pen_ot)
                if pk in pen_per:
                    pen_per[pk] += minori
        elif not pk:
            continue  # pēcspēles metieni netiek skaitīti periodos
        elif tips in ("shot-on-goal", "goal"):
            if tips == "goal" and ((pdesc.get("number"), p.get("timeInPeriod")) in pasvarti or str(det.get("goalModifier", "")) == "own-goal"):
                continue                               # paštrāpījums: vārti skaitās, bet NHL to neieskaita metienos vārtos
            r[f"{puse}_sog_{pk}"] += 1
            if pk == "ot" and len(sit) == 4 and all(x.isdigit() for x in sit) and sit[0] == "1" and sit[3] == "1":
                # papildlaika metiens vairākumā (komandai laukumā vairāk spēlētāju, abi vārtsargi laukumā)
                sk_savi, sk_pret = (int(sit[2]), int(sit[1])) if puse == "home" else (int(sit[1]), int(sit[2]))
                if sk_savi > sk_pret:
                    ot_pp_sog[puse] += 1
        elif tips == "missed-shot" and pk in REG_PERIODI:
            r[f"{puse}_missed_shots"] += 1

    # ---- komandu statistika (teamGameStats: right-rail vai landing kopsavilkums) ----
    tgs_saraksts = atrast_sarakstu(rr, "teamGameStats") or summary.get("teamGameStats") or []
    tgs = {it.get("category"): it for it in tgs_saraksts if isinstance(it, dict)}
    gaiditie = ("sog", "faceoffWinningPctg", "powerPlay", "pim", "hits", "blockedShots", "giveaways", "takeaways")
    if not tgs:
        print("  Piezīme: teamGameStats nav atrasts (right-rail / landing), komandu statistika (PP, hits u.c.) būs tukša.")
    elif any(k not in tgs for k in gaiditie):
        print("  Piezīme: teamGameStats trūkst kategoriju:", [k for k in gaiditie if k not in tgs],
              "| atrastās:", sorted(k for k in tgs if k))

    def tv(kat, puse):
        return (tgs.get(kat) or {}).get(f"{puse}Value")

    def procenti(x):
        """Iemetienu procenti vienmēr 0-100 (ja API atdod daļskaitli 0-1, tiek pārrēķināts)."""
        try:
            x = float(x)
        except (TypeError, ValueError):
            return None
        return round(x * 100, 1) if 0 <= x <= 1 else x

    for puse in ("home", "away"):
        r[f"{puse}_pim_official"] = tv("pim", puse)
        r[f"{puse}_hits"] = tv("hits", puse)
        r[f"{puse}_blocked_shots"] = tv("blockedShots", puse)
        r[f"{puse}_giveaways"] = tv("giveaways", puse)
        r[f"{puse}_takeaways"] = tv("takeaways", puse)
        r[f"{puse}_faceoff_pct"] = procenti(tv("faceoffWinningPctg", puse))
        pp_g, pp_o = sadalit_dalu(tv("powerPlay", puse))
        pret_puse = "away" if puse == "home" else "home"
        if pp_o is not None:                       # papildlaika vairākuma iespējas (pretinieka sodi papildlaikā) netiek ieskaitītas
            pp_o = max(pp_o - r[f"{pret_puse}_pen_ot"], 0)
        r[f"{puse}_pp_opp"] = pp_o
        if pp_o is None and "powerPlay" in tgs:
            print("  Piezīme: 'powerPlay' atrasts, bet formātu nevar nolasīt. Paraugs:", tgs["powerPlay"])
        if pp_g is not None and pp_g - ppg_ot[puse] != r[f"{puse}_ppg"]:
            print(f"  Brīdinājums: {puse} vairākuma vārti {r[f'{puse}_ppg']} != oficiālie pamatlaikā {pp_g - ppg_ot[puse]}")

        summa = sum(r[f"{puse}_sog_{k}"] for k in PERIODI)
        oficial = home.get("sog") if puse == "home" else away.get("sog")
        r[f"{puse}_sog_total"] = oficial if oficial is not None else summa
        if oficial is not None and oficial != summa:
            print(f"  Brīdinājums: {puse} metienu summa pa periodiem ({summa}) != kopējie ({oficial})")

        off_pim = r[f"{puse}_pim_official"]
        if isinstance(off_pim, (int, float)) and r[f"{puse}_pim_total"] + r[f"{puse}_pim_ot"] + kautinu_pim[puse] + citi_pim[puse] != off_pim:
            print(f"  Brīdinājums: {puse} PIM minor {r[f'{puse}_pim_total'] + r[f'{puse}_pim_ot']} + kautiņi {kautinu_pim[puse]} "
                  f"+ citi {citi_pim[puse]} != oficiālie {off_pim}")

    # ---- vārtu pārbaude (SO uzvarētāja vārti nav periodu summā) ----
    starp = {p: r[f"{p}_total"] - sum(r[f"{p}_{k}"] for k in PERIODI) for p in ("home", "away")}
    if min(starp.values()) < 0 or sum(starp.values()) != (1 if beigas == "SO" else 0):
        print(f"  Brīdinājums: vārti pa periodiem nesakrīt ar rezultātu (starpība {starp}, beigas {beigas})")

    # ---- sastāvi ----
    vardnica = {}
    sastavu_rindas = []
    for rs in pbp.get("rosterSpots") or []:
        tid = rs.get("teamId")
        vards = f"{teksts(rs.get('firstName'))} {teksts(rs.get('lastName'))}".strip()
        vardnica[rs.get("playerId")] = vards
        sastavu_rindas.append({
            "datums": datums, "game_id": gid, "team": id2ab.get(tid, ""),
            "home_away": "home" if tid == home_id else "away" if tid == away_id else "",
            "playerId": rs.get("playerId"), "vards": vards,
            "numurs": rs.get("sweaterNumber"), "pozicija": rs.get("positionCode"),
        })

    # ---- spēlētāji un vārtsargi (boxscore) ----
    speletaju_rindas, vartsargu_rindas = [], []
    pbgs = box.get("playerByGameStats") or {}
    for puse, ab in (("home", home_ab), ("away", away_ab)):
        t = pbgs.get(f"{puse}Team") or {}

        def pamats(pl):
            pid = pl.get("playerId")
            return {
                "datums": datums, "game_id": gid, "team": ab, "home_away": puse,
                "playerId": pid, "vards": vardnica.get(pid) or teksts(pl.get("name")),
                "numurs": pl.get("sweaterNumber"), "pozicija": pl.get("position"),
            }

        for grupa in ("forwards", "defense"):
            for pl in t.get(grupa) or []:
                rinda = pamats(pl)
                for k in SKATER_STAT:
                    rinda[k] = pl.get(k)
                rinda["noraid"] = spel_noraid.get(pl.get("playerId"), 0)     # minor noraidījumi pamatlaikā (no play-by-play)
                speletaju_rindas.append(rinda)

        pret = "away" if puse == "home" else "home"   # metieni pret šīs komandas vārtsargu = pretinieka metieni
        for pl in t.get("goalies") or []:
            rinda = pamats(pl)
            for k in GOALIE_STAT:
                rinda[k] = pl.get(k)
            vartsargu_rindas.append(rinda)
            _, pp_sa = sadalit_dalu(pl.get("powerPlayShotsAgainst"))
            if pp_sa:
                r[f"{pret}_pp_sog"] += pp_sa

    for puse in ("home", "away"):                   # vairākuma metieni: tikai pamatlaiks
        r[f"{puse}_pp_sog"] = max(r[f"{puse}_pp_sog"] - ot_pp_sog[puse], 0)

    # ---- maiņas ----
    mainu_rindas = []
    if isinstance(maina, dict):
        for s in maina.get("data") or []:
            if s.get("typeCode") not in (None, 517):   # 517 = parasta maiņa
                continue
            mainu_rindas.append({
                "datums": datums, "game_id": gid, "team": s.get("teamAbbrev"),
                "playerId": s.get("playerId"),
                "vards": f"{s.get('firstName') or ''} {s.get('lastName') or ''}".strip(),
                "period": s.get("period"), "shiftNumber": s.get("shiftNumber"),
                "startTime": s.get("startTime"), "endTime": s.get("endTime"), "duration": s.get("duration"),
            })
    if IEGUT_MAINAS and not mainu_rindas:
        print("  Piezīme: maiņu dati šai spēlei vēl nav pieejami.")

    # ---- tiesneši (right-rail; atslēga 'referees' tiek meklēta jebkurā dziļumā) ----
    tiesnesu_rindas = []
    atrasts = {}
    for loma, atsl in (("referee", "referees"), ("linesman", "linesmen")):
        atrasts[atsl] = atrast_sarakstu(rr, atsl)
        for x in atrasts[atsl] or []:
            vards = amatpersonas_vards(x)
            if vards:
                tiesnesu_rindas.append({
                    "datums": datums, "game_id": gid, "sezona": land.get("season"), "loma": loma, "vards": vards,
                    "home_team": home_ab, "away_team": away_ab,
                    "pen_home": r["home_pen_count"], "pen_away": r["away_pen_count"],
                    "pen_total": r["home_pen_count"] + r["away_pen_count"],
                    "pen_p1": pen_per["p1"], "pen_p2": pen_per["p2"], "pen_p3": pen_per["p3"],
                    "pim_home": r["home_pim_total"], "pim_away": r["away_pim_total"],
                })
    if not any(t["loma"] == "referee" for t in tiesnesu_rindas):
        if rr is None:
            print("  Piezīme: right-rail pieprasījums neizdevās, tiesneši nav ielasīti.")
        elif atrasts["referees"]:
            print("  Piezīme: 'referees' atrasts, bet vārdus nevar nolasīt. Paraugs:",
                  json.dumps(atrasts["referees"][:2], ensure_ascii=False)[:250])
        else:
            print("  Piezīme: right-rail atbildē nav 'referees'. Augšējās atslēgas:", list(rr)[:15],
                  "| gameInfo:", json.dumps(rr.get("gameInfo"), ensure_ascii=False)[:300])

    return {
        "tiesnesi": tiesnesu_rindas,
        "speles": [r], "varti": vartu_rindas, "notikumi": notikumu_rindas,
        "sastavi": sastavu_rindas, "speletaji": speletaju_rindas,
        "vartsargi": vartsargu_rindas, "mainas": mainu_rindas,
    }


# ----------------------------------------------------------------------------
# GALVENĀ PROGRAMMA
# ----------------------------------------------------------------------------
def main():
    global kludu_skaits
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    robeza_utc = None
    if PEDEJAS_STUNDAS:
        tagad = datetime.now(timezone.utc)
        robeza_utc = tagad - timedelta(hours=PEDEJAS_STUNDAS + SPELES_ILGUMS_H)     # spēles, kas sākās pēc šī brīža, varēja beigties pēdējo N h laikā
        no, lidz = robeza_utc.astimezone(ET).date().isoformat(), tagad.astimezone(ET).date().isoformat()
        print(f"Režīms: spēles, kas beigušās pēdējo {PEDEJAS_STUNDAS:g} h laikā (sākums pēc {robeza_utc:%Y-%m-%d %H:%M} UTC); datumi {no} – {lidz}")
    elif not args:
        no, lidz = noklusejuma_intervals()
    elif len(args) == 1:
        no = lidz = args[0]
    else:
        no, lidz = args[0], args[1]

    sagatavot_failus()
    gatavas = ielasit_id("speles")
    ar_tiesnesiem = ielasit_id("tiesnesi")
    pievienotas = 0

    for datums in datumu_saraksts(no, lidz):
        print(f"\n=== {datums} ===")
        dati = get_json(f"{API_WEB}/score/{datums}")
        if dati is None:
            print("Neizdevās iegūt spēļu sarakstu.")
            kludu_skaits += 1
            continue
        speles = dati.get("games") or []
        if not speles:
            print("Šajā dienā spēļu nav.")
            continue

        krajums = {nos: [] for nos in TABULAS}
        apstradatie = set()
        for spele in speles:
            gid = spele.get("id")
            print(f"{teksts((spele.get('awayTeam') or {}).get('abbrev'))} @ "
                  f"{teksts((spele.get('homeTeam') or {}).get('abbrev'))} (ID: {gid})")
            if robeza_utc is not None:                     # režīms "pēdējās N stundas": tikai nesen beigušās spēles, tās vienmēr pārlasa
                try:
                    sak = datetime.fromisoformat(str(spele.get("startTimeUTC")).replace("Z", "+00:00"))
                except ValueError:
                    sak = None
                if sak is None or sak < robeza_utc:
                    print("  Ārpus izvēlētajām pēdējām stundām, izlaižu.")
                    continue
            parrakstit = ATJAUNOT or robeza_utc is not None
            if str(gid) in gatavas and str(gid) in ar_tiesnesiem and not parrakstit:
                print("  Jau ir datubāzē, izlaižu.")
                continue
            if str(gid) in gatavas and parrakstit:
                print("  Spēle jau ir - pārrakstu (--atjaunot).")
            elif str(gid) in gatavas:
                print("  Spēle jau ir, bet trūkst tiesnešu - ielasu atkārtoti.")
            if spele.get("gameType") not in SPELU_TIPI:
                print(f"  Spēles tips {spele.get('gameType')} nav izvēlēts, izlaižu.")
                continue
            if spele.get("gameState") not in ("OFF", "FINAL"):
                print(f"  Spēle nav pabeigta (stāvoklis: {spele.get('gameState')}), izlaižu.")
                continue
            rez = apstradat_spele(spele, datums)
            if rez is None:
                kludu_skaits += 1
                continue
            apstradatie.add(str(gid))
            for nos, rindas in rez.items():
                krajums[nos].extend(rindas)
            time.sleep(KAVESANAS)

        # "speles" tiek rakstīta pēdējā, lai pārtraukta darbība neatstātu "pusgatavu" spēli
        for nos in [n for n in TABULAS if n != "speles"] + ["speles"]:
            if VIEGLAIS and nos in LIELAS_TABULAS:
                continue
            if ATJAUNOT or robeza_utc is not None:
                dzest_spelu_rindas(nos, apstradatie)      # vecās rindas tiek aizstātas ar jaunajām
            n = pievienot(nos, krajums[nos])
            if nos == "speles":
                pievienotas += n
                gatavas = ielasit_id("speles")

    print(f"\nGatavs. Jaunas spēles: {pievienotas}. Kļūdas: {kludu_skaits}. Mape: {DATU_MAPE}")
    if kludu_skaits:
        sys.exit(1)
    # veiksmīgas atjaunināšanas laiks (lietotne to rāda kā "Pēdējā atjaunošana"; neveiksmīga palaišana to nemaina)
    try:
        with open(os.path.join(DATU_MAPE, "pedeja_atjaunosana.json"), "w", encoding="utf-8") as f:
            json.dump({"utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "jaunas_speles": pievienotas,
                       "rezims": (f"pedejas {PEDEJAS_STUNDAS:g}h" if PEDEJAS_STUNDAS else ("atjaunot" if ATJAUNOT else "parasts"))}, f)
    except OSError as ex:
        print("Neizdevās saglabāt atjaunināšanas laiku:", ex)


if __name__ == "__main__":
    main()
