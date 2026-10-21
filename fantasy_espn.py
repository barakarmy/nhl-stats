"""
fantasy_espn.py – ESPN Fantasy Hockey "% rostered" (cik % ESPN līgu spēlētājs ir paņemts) → sezonas/fantasy_espn.csv

Vajadzīgs trešdienas "Fantasy pickups" video (shorts.py --veids fantasy): pickup ieteikumiem jābūt spēlētājiem,
kuri lielākajā daļā līgu vēl ir brīvi. Avots: ESPN publiskais fantasy API (bez pieteikšanās; neoficiāls – ja ESPN to
maina, skripts izdrukā brīdinājumu un vecie faili paliek).

Palaiž darbplūsma "NHL Daily Update" katru rītu (pēc spēļu datiem). Ar roku: python fantasy_espn.py
Raksta:
  sezonas/fantasy_espn.csv          – pēdējais stāvoklis: espn_id, playerId (NHL), vards, komanda, poz, rostered,
                                      trauma (ACTIVE / DAY_TO_DAY / OUT / INJURY_RESERVE), datums
  sezonas/fantasy_espn_vesture.csv  – rostered % pa dienām (pēdējās 15 dienas) – izmaiņām "▲ +3% šonedēļ"
NHL playerId tiek atrasts pēc vārda (+ komandas, ja vārdi sakrīt) no sezonas/speletaji.csv.
"""
import csv
import json
import os
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
MAPE = os.path.join(BASE, "sezonas")
FAILS = os.path.join(MAPE, "fantasy_espn.csv")
VESTURE = os.path.join(MAPE, "fantasy_espn_vesture.csv")
URL = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fhl/seasons/{}/segments/0/leaguedefaults/1?view=kona_player_info"
URL_REZERVE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fhl/seasons/{}/players?view=players_wl"   # bez traumu statusa
VESTURES_DIENAS = 15
MIN_VESTUREI = 0.1          # vēsturē glabā tikai spēlētājus ar ≥ 0,1 % (pārējie ir praktiski neizmantoti)

# ESPN proTeamId → NHL saīsinājums (0 = brīvais aģents)
ESPN_KOMANDAS = {1: "BOS", 2: "BUF", 3: "CGY", 4: "CHI", 5: "DET", 6: "EDM", 7: "CAR", 8: "LAK", 9: "DAL", 10: "MTL",
                 11: "NJD", 12: "NYI", 13: "NYR", 14: "OTT", 15: "PHI", 16: "PIT", 17: "COL", 18: "SJS", 19: "STL",
                 20: "TBL", 21: "TOR", 22: "VAN", 23: "WSH", 25: "ANA", 26: "FLA", 27: "NSH", 28: "WPG", 29: "CBJ",
                 30: "MIN", 37: "VGK", 124292: "SEA", 129764: "UTA"}
POZICIJAS = {1: "C", 2: "LW", 3: "RW", 4: "D", 5: "G"}


def norm(v):
    """Vārds salīdzināšanai: bez diakritikas, mazie burti, bez punktiem un viena burta iniciāļiem."""
    v = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode().lower()
    v = "".join(c if c.isalpha() or c == " " else " " for c in v)
    return " ".join(t for t in v.split() if len(t) > 1)


def espn_sezona(d=None):
    d = d or date.today()
    return d.year + 1 if d.month >= 7 else d.year


def ielasit_espn(sezona):
    """Galvenais avots: 2000 spēlētāji ar lielāko % rostered (+ traumu statuss, ~3 MB). Rezerve: visi aktīvie bez traumām."""
    import requests
    galvenes = {"User-Agent": "Mozilla/5.0"}
    try:
        filtrs = {"players": {"limit": 2000, "sortPercOwned": {"sortPriority": 1, "sortAsc": False},
                              "filterStatsForTopScoringPeriodIds": {"value": 1, "additionalValue": [f"00{sezona}"]}}}
        r = requests.get(URL.format(sezona), headers={**galvenes, "X-Fantasy-Filter": json.dumps(filtrs)}, timeout=60)
        r.raise_for_status()
        dati = [x.get("player") or {} for x in r.json().get("players", [])]
        if len(dati) >= 300:
            return dati
        print(f"::warning::ESPN galvenais avots atgrieza {len(dati)} spēlētājus – izmantoju rezervi (bez traumām)")
    except Exception as ex:                                            # noqa: BLE001
        print(f"::warning::ESPN galvenais avots neatbild ({type(ex).__name__}) – izmantoju rezervi (bez traumām)")
    filtrs = {"players": {"filterActive": {"value": True}}}
    r = requests.get(URL_REZERVE.format(sezona), headers={**galvenes, "X-Fantasy-Filter": json.dumps(filtrs)}, timeout=60)
    r.raise_for_status()
    return r.json()


def parset(dati):
    """ESPN atbilde → [{espn_id, vards, komanda, poz, rostered}] tikai spēlētājiem ar ownership datiem."""
    out = []
    for p in dati or []:
        o = p.get("ownership") or {}
        if o.get("percentOwned") is None:
            continue
        out.append({"espn_id": p.get("id"), "vards": p.get("fullName", ""),
                    "komanda": ESPN_KOMANDAS.get(p.get("proTeamId"), ""), "poz": POZICIJAS.get(p.get("defaultPositionId"), ""),
                    "rostered": round(float(o["percentOwned"]), 2), "trauma": p.get("injuryStatus") or ""})
    return out


def nhl_speletaji():
    """norm(vārds) → [(playerId, komanda)] no sezonas/speletaji.csv un vartsargi.csv (pēdējā zināmā komanda)."""
    pec_id = {}
    for fails in ("speletaji.csv", "vartsargi.csv"):
        p = os.path.join(MAPE, fails)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                pid = r.get("playerId")
                if pid:
                    vecs = pec_id.get(pid)
                    if vecs is None or r["datums"] >= vecs[2]:
                        pec_id[pid] = (r.get("vards", ""), r.get("team", ""), r["datums"])
    out = {}
    for pid, (v, kom, _) in pec_id.items():
        out.setdefault(norm(v), []).append((int(pid), kom))
    return out


def sasaistit(rindas, nhl):
    n = 0
    for r in rindas:
        kand = nhl.get(norm(r["vards"]), [])
        if len(kand) > 1:
            kand = [k for k in kand if k[1] == r["komanda"]] or kand[:0]
        r["playerId"] = kand[0][0] if len(kand) == 1 else ""
        n += bool(r["playerId"])
    return n


def saglabat(rindas, sodien):
    kol = ["espn_id", "playerId", "vards", "komanda", "poz", "rostered", "trauma", "datums"]
    with open(FAILS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kol)
        w.writeheader()
        for r in sorted(rindas, key=lambda x: -x["rostered"]):
            w.writerow({**{k: r.get(k, "") for k in kol}, "datums": sodien})
    # vēsture: šodienas rindas aizstāj iepriekšējās šodienas rindas; vecākas par 15 dienām tiek dzēstas
    robeza = (date.fromisoformat(sodien) - timedelta(days=VESTURES_DIENAS)).isoformat()
    vecas = []
    if os.path.exists(VESTURE):
        with open(VESTURE, encoding="utf-8") as f:
            vecas = [r for r in csv.DictReader(f) if robeza <= r["datums"] < sodien]
    jaunas = [{"datums": sodien, "espn_id": r["espn_id"], "rostered": r["rostered"]} for r in rindas if r["rostered"] >= MIN_VESTUREI]
    with open(VESTURE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["datums", "espn_id", "rostered"])
        w.writeheader()
        w.writerows(vecas + jaunas)


def main():
    sodien = datetime.now(timezone.utc).date().isoformat()
    sez = espn_sezona()
    try:
        dati = ielasit_espn(sez)
    except Exception as ex:                                            # noqa: BLE001
        print(f"::warning::ESPN fantasy dati neielādējās ({type(ex).__name__}: {ex}) – paliek vecais fails.")
        return 0
    rindas = parset(dati)
    if len(rindas) < 300:
        print(f"::warning::ESPN atgrieza tikai {len(rindas)} spēlētājus ar % rostered – iespējams, mainījies API. Fails netiek mainīts.")
        return 0
    n = sasaistit(rindas, nhl_speletaji())
    saglabat(rindas, sodien)
    virs1 = sum(r["rostered"] >= 1 for r in rindas)
    traumas = sum(r["trauma"] in ("OUT", "INJURY_RESERVE", "DAY_TO_DAY") for r in rindas)
    print(f"ESPN {sez}: {len(rindas)} spēlētāji ar % rostered ({virs1} ≥ 1 %), sasaistīti ar NHL: {n}, ar traumu: {traumas}. → {FAILS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
