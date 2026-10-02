"""
Plānotie tiesneši: pirms spēlēm ielasa NHL `right-rail` datus un ieraksta dati/tiesnesi_planotie.csv
(viena rinda uz spēli un amatpersonu). Spēļu laiki tiek ņemti no nhl_kalendars.csv (to atjaunina kalendars.py).

Darbplūsma (.github/workflows/referees.yml) katras 30 minūtes palaiž ĀTRO pārbaudi:
  python tiesnesi_planotie.py --parbaude
Pārbaude nolasa tikai CSV failus (bez interneta) un izlemj, vai ir vajadzīga ielāde:
  • ielāde vajadzīga, ja kādai spēlei, kas sākas tuvāko 4 stundu laikā, vēl nav paziņoti tiesneši;
  • ja visām šīm spēlēm tiesneši jau ir failā, ielāde netiek palaista.
Ja ielāde vajadzīga, tā pārbauda visas spēles bez tiesnešiem tuvāko 8 stundu laikā (tāpēc agrāka ielāde
bieži jau aizpilda arī nākamās spēles), un nemaina spēles, kurām tiesneši jau ir.

Lietošana:
  python tiesnesi_planotie.py --parbaude       # tikai pārbaude (raksta needed=true/false uz GITHUB_OUTPUT)
  python tiesnesi_planotie.py                  # ielāde: spēles bez tiesnešiem tuvāko 8 h laikā
  python tiesnesi_planotie.py --stundas 30 --visas   # pārbauda arī spēles, kurām tiesneši jau ir (testam)
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DATU_MAPE = os.environ.get("NHL_DATU_MAPE") or os.path.join(BASE, "dati")
KALENDARS = os.path.join(BASE, "nhl_kalendars.csv")
FAILS = os.path.join(DATU_MAPE, "tiesnesi_planotie.csv")
KOLONNAS = ["game_id", "sakums_utc", "home_team", "away_team", "loma", "vards", "atjaunots_utc"]

TRIGERA_STUNDAS = 4    # darbu sāk, ja kādai spēlei tuvāko tik stundu laikā nav tiesnešu
IEGUVES_STUNDAS = 8    # ielādes laikā tiek pārbaudītas visas spēles bez tiesnešiem tik stundu laikā
MIN_TIESNESI = 2       # spēle ir "aizpildīta", ja failā ir vismaz tik galvenie tiesneši
GLABAT_DIENAS = 2


def _laiks(teksts):
    try:
        return datetime.fromisoformat(str(teksts).replace("Z", "+00:00"))
    except ValueError:
        return None


def ielasit_kalendaru():
    if not os.path.isfile(KALENDARS):
        return []
    with open(KALENDARS, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def ielasit_esoso():
    if not os.path.isfile(FAILS):
        return []
    with open(FAILS, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def saglabat(rindas):
    os.makedirs(DATU_MAPE, exist_ok=True)
    with open(FAILS, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=KOLONNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rindas)


def speles_logaa(kalendars, tagad, stundas):
    """Spēles, kas vēl nav sākušās un sākas tuvāko `stundas` stundu laikā (hronoloģiski)."""
    out = []
    for r in kalendars:
        sak = _laiks(r.get("sakuma_laiks_utc"))
        if sak is not None and tagad <= sak <= tagad + timedelta(hours=stundas):
            out.append(r)
    return sorted(out, key=lambda r: r["sakuma_laiks_utc"])


def trukst_tiesnesu(speles, esosie):
    """Spēles, kurām failā vēl nav MIN_TIESNESI galveno tiesnešu."""
    skaits = {}
    for r in esosie:
        if r.get("loma") == "referee":
            skaits[str(r["game_id"])] = skaits.get(str(r["game_id"]), 0) + 1
    return [sp for sp in speles if skaits.get(str(sp["game_id"]), 0) < MIN_TIESNESI]


def nosaukums(sp):
    return f"{sp.get('viesu_komanda')} @ {sp.get('majas_komanda')} ({sp['game_id']})"


# ----------------------------------------------------------------------------
# ĀTRĀ PĀRBAUDE (tikai standarta bibliotēka, bez interneta)
# ----------------------------------------------------------------------------
def parbaude(tagad=None):
    tagad = tagad or datetime.now(timezone.utc)
    logs = speles_logaa(ielasit_kalendaru(), tagad, TRIGERA_STUNDAS)
    bez = trukst_tiesnesu(logs, ielasit_esoso())
    vajag = bool(bez)
    print(f"Spēles tuvāko {TRIGERA_STUNDAS} h laikā: {len(logs)}, bez paziņotiem tiesnešiem: {len(bez)}")
    for sp in bez:
        print(f"  – {nosaukums(sp)} sākas {sp['sakuma_laiks_utc']}")
    print("Ielāde vajadzīga." if vajag else "Ielāde nav vajadzīga.")
    izvade = os.environ.get("GITHUB_OUTPUT")
    if izvade:
        with open(izvade, "a", encoding="utf-8") as f:
            f.write(f"needed={'true' if vajag else 'false'}\n")
    return vajag


# ----------------------------------------------------------------------------
# IELĀDE
# ----------------------------------------------------------------------------
def _nhl():
    import nhl_dati          # ielādē tikai tad, kad tiešām vajag internetu (requests)
    return nhl_dati


def tiesnesi_no_right_rail(rr):
    """[(loma, vārds), ...] (atslēgas 'referees' un 'linesmen' tiek meklētas jebkurā dziļumā)."""
    nhl = _nhl()
    out = []
    for loma, atsl in (("referee", "referees"), ("linesman", "linesmen")):
        for x in nhl.atrast_sarakstu(rr, atsl) or []:
            v = nhl.amatpersonas_vards(x)
            if v:
                out.append((loma, v))
    return out


def ielasit(stundas=IEGUVES_STUNDAS, visas=False, tagad=None):
    nhl = _nhl()
    tagad = tagad or datetime.now(timezone.utc)
    esosie = ielasit_esoso()
    speles = speles_logaa(ielasit_kalendaru(), tagad, stundas)
    if not visas:
        speles = trukst_tiesnesu(speles, esosie)
    print(f"Pārbaudāmās spēles tuvāko {stundas} h laikā: {len(speles)}")

    atjaunots = tagad.strftime("%Y-%m-%d %H:%M")
    jaunas_rindas, atrasti, paraugs = {}, 0, None
    for sp in speles:
        gid = sp["game_id"]
        rr = nhl.get_json(f"{nhl.API_WEB}/gamecenter/{gid}/right-rail", meginajumi=2)
        time.sleep(nhl.KAVESANAS)
        if rr is None:
            print(f"  ✗ {nosaukums(sp)}: pieprasījums neizdevās")
            continue
        paraugs = paraugs or rr
        ties = tiesnesi_no_right_rail(rr)
        if not any(loma == "referee" for loma, _ in ties):
            print(f"  – {nosaukums(sp)}: tiesneši vēl nav paziņoti")
            continue
        atrasti += 1
        print(f"  ✓ {nosaukums(sp)}: {', '.join(v for l, v in ties if l == 'referee')}")
        jaunas_rindas[gid] = [{"game_id": gid, "sakums_utc": sp["sakuma_laiks_utc"],
                               "home_team": sp.get("majas_komanda"), "away_team": sp.get("viesu_komanda"),
                               "loma": loma, "vards": v, "atjaunots_utc": atjaunots} for loma, v in ties]

    # apvieno ar esošo: nemaina spēles, kurām tiesneši nav mainījušies; izmet vecās spēles
    robeza = tagad - timedelta(days=GLABAT_DIENAS)
    rezultats = []
    for r in esosie:
        sak = _laiks(r.get("sakums_utc"))
        if sak is not None and sak < robeza:
            continue
        if r["game_id"] in jaunas_rindas:
            vecie = {(x["loma"], x["vards"]) for x in esosie if x["game_id"] == r["game_id"]}
            jaunie = {(x["loma"], x["vards"]) for x in jaunas_rindas[r["game_id"]]}
            if vecie != jaunie:
                continue                      # tiks aizstāts ar jauno
            jaunas_rindas.pop(r["game_id"])   # nemainīgs: atstājam veco ierakstu
        rezultats.append(r)
    for rindas in jaunas_rindas.values():
        rezultats.extend(rindas)
    rezultats.sort(key=lambda r: (str(r["sakums_utc"]), str(r["game_id"]), 0 if r["loma"] == "referee" else 1))
    saglabat(rezultats)

    print(f"Tiesneši atrasti {atrasti} no {len(speles)} spēlēm. Failā kopā rindu: {len(rezultats)}.")
    if speles and atrasti == 0 and paraugs is not None:
        print("Piezīme: nevienai spēlei tiesnešu nav. right-rail augšējās atslēgas:", list(paraugs)[:15],
              "| gameInfo:", json.dumps(paraugs.get("gameInfo"), ensure_ascii=False)[:300])


def main():
    if "--parbaude" in sys.argv:
        parbaude()
        return
    stundas = IEGUVES_STUNDAS
    if "--stundas" in sys.argv:
        stundas = int(sys.argv[sys.argv.index("--stundas") + 1])
    ielasit(stundas=stundas, visas="--visas" in sys.argv)


if __name__ == "__main__":
    main()
