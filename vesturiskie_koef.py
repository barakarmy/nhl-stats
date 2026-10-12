"""
vesturiskie_koef.py – iepriekšējo sezonu NHL koeficienti (publisks arhīvs) Picks vēsturiskajai pārbaudei.

Avots: SportsbookReview (sportsbookreview.com) – publiskas koeficientu lapas pa datumiem. Katram datumam 3 lapas:
  uzvarētājs ar OT (moneyline), totāli (full game) un ±1.5 (point spread / puck line, full game).
Katram ASV bukmeikeram (BetMGM, bet365, DraftKings, FanDuel, Caesars u.c.) – atvēršanas (openingLine) un pēdējais
(currentLine; pagājušām spēlēm = noslēguma) koeficients. Amerikāņu koeficienti tiek pārvērsti decimālajos.
1X2 pamatlaikā (ar neizšķirtu) ASV bukmeikeri nedod – to vēsturē pārbaudīt nevar.

Spēles tiek sasaistītas ar DB spēlēm (sezonas/vesture/<sezona>/speles.csv) pēc datuma un komandām.

Palaišana (lokāli, repozitorija mapē; vajag: pip install requests pandas):
    python vesturiskie_koef.py                    → visas DB sezonas (sezonas/vesture/2023…/)
    python vesturiskie_koef.py 20242025 20252026  → tikai norādītās
    python vesturiskie_koef.py --aktiva           → arī aktīvā sezona (sezonas/speles.csv), līdz vakardienai
Rezultāts: sezonas/vesture/<sezona>/koeficienti_vesture.csv (aktīvajai – sezonas/koeficienti_vesture.csv)
  kolonnas: game_id, datums, majas, viesi, tirgus (ml / tot / pm), iznakums (1 / 2 / over / under), linija,
            bukmeikers, koef_atv (atvēršanas), koef (noslēguma)
Darbu var pārtraukt un turpināt: jau ielādētie datumi tiek izlaisti. ~200 datumi sezonā × 3 lapas, ~1,2 s pauze
starp pieprasījumiem → ~15 min sezonai.
Pēc tam: python picks.py --parbaude
"""
import csv
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
MAPE = os.path.join(BASE, "sezonas")
VESTURE = os.path.join(MAPE, "vesture")
URL = "https://www.sportsbookreview.com/betting-odds/nhl-hockey/{}?date={}"
LAPAS = {"ml": "", "tot": "totals/full-game/", "pm": "pointspread/full-game/"}
PAUZE_S = 1.2
KOLONNAS = ["game_id", "datums", "majas", "viesi", "tirgus", "iznakums", "linija", "bukmeikers", "koef_atv", "koef"]
GALVENES = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"}

KOMANDAS = {
    "anaheim ducks": "ANA", "arizona coyotes": "ARI", "boston bruins": "BOS", "buffalo sabres": "BUF", "calgary flames": "CGY",
    "carolina hurricanes": "CAR", "chicago blackhawks": "CHI", "colorado avalanche": "COL", "columbus blue jackets": "CBJ",
    "dallas stars": "DAL", "detroit red wings": "DET", "edmonton oilers": "EDM", "florida panthers": "FLA",
    "los angeles kings": "LAK", "minnesota wild": "MIN", "montreal canadiens": "MTL", "nashville predators": "NSH",
    "new jersey devils": "NJD", "new york islanders": "NYI", "new york rangers": "NYR", "ottawa senators": "OTT",
    "philadelphia flyers": "PHI", "pittsburgh penguins": "PIT", "san jose sharks": "SJS", "seattle kraken": "SEA",
    "st louis blues": "STL", "tampa bay lightning": "TBL", "toronto maple leafs": "TOR", "utah mammoth": "UTA",
    "utah hockey club": "UTA", "utah": "UTA", "vancouver canucks": "VAN", "vegas golden knights": "VGK",
    "washington capitals": "WSH", "winnipeg jets": "WPG",
}


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join("".join(c if c.isalnum() or c == " " else " " for c in s).split())


def kods(nos):
    return KOMANDAS.get(_norm(nos))


def decimal(am):
    """Amerikāņu koeficients → decimālais (+150 → 2.50, −185 → 1.54). None, ja nav derīgs."""
    try:
        a = float(am)
    except (TypeError, ValueError):
        return None
    if a >= 100:
        return round(1 + a / 100, 4)
    if a <= -100:
        return round(1 + 100 / -a, 4)
    return None


def next_data(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1)) if m else None


def parset(dati, tirgus):
    """Viena lapa (__NEXT_DATA__) → [(startDate, majas, viesi, rinda_bez_spēles)] – rindas: tirgus, iznakums, linija, bukmeikers, koef_atv, koef."""
    out = []
    try:
        rindas = dati["props"]["pageProps"]["oddsTables"][0]["oddsTableModel"]["gameRows"]
    except (KeyError, IndexError, TypeError):
        return out
    for g in rindas:
        gv = g.get("gameView") or {}
        h, a = kods((gv.get("homeTeam") or {}).get("fullName")), kods((gv.get("awayTeam") or {}).get("fullName"))
        if not h or not a:
            continue
        for ov in g.get("oddsViews") or []:
            if not ov:
                continue
            bk = ov.get("sportsbook") or ""
            atv, nos = ov.get("openingLine") or {}, ov.get("currentLine") or {}
            if tirgus == "ml":
                pari = [("1", None, "homeOdds"), ("2", None, "awayOdds")]
            elif tirgus == "tot":
                pari = [("over", "total", "overOdds"), ("under", "total", "underOdds")]
            else:
                pari = [("1", "homeSpread", "homeOdds"), ("2", "awaySpread", "awayOdds")]
            for izn, lin_k, k_k in pari:
                k1 = decimal(nos.get(k_k))
                if k1 is None:
                    continue
                lin = nos.get(lin_k) if lin_k else None
                # atvēršanas koeficients der tikai, ja līnija ir tā pati (citādi tas ir cits tirgus)
                k0 = decimal(atv.get(k_k)) if (not lin_k or atv.get(lin_k) == lin) else None
                out.append((gv.get("startDate"), h, a, {"tirgus": tirgus, "iznakums": izn, "linija": "" if lin is None else lin,
                                                        "bukmeikers": bk, "koef_atv": "" if k0 is None else k0, "koef": k1}))
    return out


def ielasit_datumu(sesija, d):
    """Visi 3 tirgi vienam datumam (ASV laika datums, kā NHL kalendārā)."""
    out = []
    for tirgus, cels in LAPAS.items():
        for m in range(3):
            try:
                r = sesija.get(URL.format(cels, d), headers=GALVENES, timeout=30)
                if r.status_code == 200:
                    dati = next_data(r.text)
                    if dati is None:
                        print(f"  {d} {tirgus}: lapā nav datu (__NEXT_DATA__) – iespējams, mainījusies lapas uzbūve")
                    else:
                        out += parset(dati, tirgus)
                    break
                print(f"  {d} {tirgus}: HTTP {r.status_code}")
                if r.status_code in (403, 404):
                    break
            except Exception as ex:                                    # noqa: BLE001
                print(f"  {d} {tirgus}: {type(ex).__name__}")
            time.sleep(5 * (m + 1))
        time.sleep(PAUZE_S)
    return out


def _lasit_speles(fails):
    with open(fails, encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("home_total") not in ("", None)]


def apstradat(speles_fails, izvade):
    speles = _lasit_speles(speles_fails)
    pec_dat = {}
    for s in speles:
        pec_dat.setdefault(s["datums"][:10], []).append(s)
    jau = set()
    if os.path.exists(izvade):
        with open(izvade, encoding="utf-8") as f:
            jau = {r["datums"] for r in csv.DictReader(f)}
    vakar = (date.today() - timedelta(days=1)).isoformat()
    datumi = sorted(d for d in pec_dat if d not in jau and d <= vakar)
    print(f"{speles_fails}: {len(pec_dat)} datumi, jāielādē {len(datumi)} → {izvade}")
    if not datumi:
        return 0
    import requests
    sesija = requests.Session()
    jauns_fails = not os.path.exists(izvade)
    n_sp = n_bez = 0
    with open(izvade, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOLONNAS)
        if jauns_fails:
            w.writeheader()
        for i, d in enumerate(datumi, 1):
            rindas = ielasit_datumu(sesija, d)
            dd = date.fromisoformat(d)
            atrastas = set()
            for start, h, a, r in rindas:
                # sasaiste ar DB spēli: tas pats datums (vai ±1 diena, ja lapā cits datuma formāts) un komandas
                sp = next((s for s in pec_dat.get(d, []) if s["home_team"] == h and s["away_team"] == a), None)
                if sp is None:
                    for dd2 in (dd - timedelta(days=1), dd + timedelta(days=1)):
                        sp = next((s for s in pec_dat.get(dd2.isoformat(), []) if s["home_team"] == h and s["away_team"] == a), None)
                        if sp:
                            break
                if sp is None:
                    continue
                atrastas.add(sp["game_id"])
                w.writerow({"game_id": sp["game_id"], "datums": d, "majas": h, "viesi": a, **r})
            bez = len(pec_dat[d]) - len(atrastas)
            n_sp += len(atrastas)
            n_bez += max(0, bez)
            f.flush()
            print(f"  [{i}/{len(datumi)}] {d}: {len(atrastas)}/{len(pec_dat[d])} spēles, {len(rindas)} koeficienti")
    print(f"Gatavs: {n_sp} spēles ar koeficientiem, {n_bez} bez.")
    return 0


def main(args):
    if "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    sezonas = [a for a in args if a.isdigit() and len(a) == 8]
    if not sezonas:
        sezonas = sorted(d for d in os.listdir(VESTURE) if d.isdigit() and os.path.exists(os.path.join(VESTURE, d, "speles.csv"))) \
            if os.path.isdir(VESTURE) else []
    for s in sezonas:
        fails = os.path.join(VESTURE, s, "speles.csv")
        if not os.path.exists(fails):
            print(f"{s}: nav {fails}")
            continue
        apstradat(fails, os.path.join(VESTURE, s, "koeficienti_vesture.csv"))
    if "--aktiva" in args and os.path.exists(os.path.join(MAPE, "speles.csv")):
        apstradat(os.path.join(MAPE, "speles.csv"), os.path.join(MAPE, "koeficienti_vesture.csv"))
    if not sezonas and "--aktiva" not in args:
        print("Nav atrastu sezonu (sezonas/vesture/<sezona>/speles.csv). Palaid skriptu repozitorija mapē.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
