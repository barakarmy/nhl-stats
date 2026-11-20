"""
speletaji_vesture.py – trūkstošais speletaji.csv vēstures sezonām (sezonas/vesture/<sezona>/), tikai no NHL boxscore.

Kāpēc: fantasy_backtest.py --visas vajag spēlētāju statistiku pa spēlēm arī iepriekšējām sezonām, bet vēstures mapēs
ir tikai speles.csv / varti.csv / metieni.csv. vesture.py (nhl_dati.py) šīs spēles izlaiž, jo tās jau ir speles.csv.
Šis skripts ielasa TIKAI boxscore (1 pieprasījums uz spēli, ~10–15 min sezonai) un raksta speletaji.csv ar tām pašām
kolonnām kā nhl_dati.py (noraid – tukšs: to var iegūt tikai no play-by-play; fantasy to neizmanto). Citi faili netiek mainīti.

Palaišana (nhl-stats mapē, kur ir nhl_dati.py):
  python speletaji_vesture.py                  visas vēstures sezonas, kurām nav speletaji.csv (vai tas nav pilns)
  python speletaji_vesture.py 20252026         tikai šī sezona
Var pārtraukt (Ctrl+C) un palaist vēlreiz – jau ielasītās spēles tiek izlaistas, darbs turpinās.
Pēc tam:  python fantasy_backtest.py --visas --ablacija --bez-nedelam
Nepieciešams: pip install requests
"""
import csv
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from nhl_dati import API_WEB, SKATER_STAT, SPELETAJA_PAMATS, get_json, teksts  # noqa: E402

VESTURE = os.path.join(BASE, "sezonas", "vesture")
KOLONNAS = SPELETAJA_PAMATS + SKATER_STAT + ["noraid"]
KAVESANAS = 0.25           # pauze starp pieprasījumiem (sekundes) – kā nhl_dati.py
SAGLABAT_IK = 50           # spēles starp ierakstiem failā (pārtraukums nezaudē daudz)


def lasit(cels):
    if not os.path.exists(cels):
        return []
    with open(cels, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def boxscore_rindas(box, gid, datums, vardi):
    """boxscore → laukuma spēlētāju rindas (tāpat kā nhl_dati.apstradat_spele)."""
    rindas = []
    pbgs = box.get("playerByGameStats") or {}
    for puse in ("home", "away"):
        ab = teksts((box.get(f"{puse}Team") or {}).get("abbrev"))
        t = pbgs.get(f"{puse}Team") or {}
        for grupa in ("forwards", "defense"):
            for pl in t.get(grupa) or []:
                pid = pl.get("playerId")
                r = {"datums": datums, "game_id": gid, "team": ab, "home_away": puse, "playerId": pid,
                     "vards": vardi.get(str(pid)) or teksts(pl.get("name")), "numurs": pl.get("sweaterNumber"),
                     "pozicija": pl.get("position")}
                for k in SKATER_STAT:
                    r[k] = pl.get(k)
                r["noraid"] = ""
                rindas.append(r)
    return rindas


def pierakstit(cels, rindas, jauns_fails):
    with open(cels, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=KOLONNAS, extrasaction="ignore")
        if jauns_fails:
            w.writeheader()
        w.writerows(rindas)


def sezona(mape):
    nos = os.path.basename(mape)
    speles = lasit(os.path.join(mape, "speles.csv"))
    if not speles:
        print(f"{nos}: nav speles.csv – izlaižu")
        return 0
    cels = os.path.join(mape, "speletaji.csv")
    esosie = {r.get("game_id") for r in lasit(cels)}
    if os.path.exists(cels):
        with open(cels, newline="", encoding="utf-8-sig") as f:
            galvene = next(csv.reader(f), [])
        if galvene != KOLONNAS:
            print(f"{nos}: speletaji.csv galvene atšķiras no nhl_dati.py – nepārrakstu. Pārdēvē failu un palaid vēlreiz.")
            return 1
    # pilni vārdi no sastavi.csv (ja ir), citādi boxscore "C. McDavid"
    vardi = {r.get("playerId"): r.get("vards") for r in lasit(os.path.join(mape, "sastavi.csv")) if r.get("vards")}
    darams = [(r["game_id"], r["datums"]) for r in speles if r.get("game_id") and r["game_id"] not in esosie]
    print(f"\n=== {nos}: {len(speles)} spēles, jau ir {len(speles) - len(darams)}, jāielasa {len(darams)} "
          f"(~{len(darams) * (KAVESANAS + 0.35) / 60:.0f} min) ===")
    if not darams:
        return 0
    krajums, kludas, jauns_fails = [], 0, not os.path.exists(cels)
    t0 = time.time()
    for i, (gid, datums) in enumerate(darams, 1):
        box = get_json(f"{API_WEB}/gamecenter/{gid}/boxscore")
        if not box:
            kludas += 1
        else:
            krajums += boxscore_rindas(box, gid, datums, vardi)
        if i % SAGLABAT_IK == 0 or i == len(darams):
            if krajums:
                pierakstit(cels, krajums, jauns_fails)
                jauns_fails, krajums = False, []
            print(f"  {i}/{len(darams)}  ({(time.time() - t0) / 60:.1f} min)" + (f", neizdevās: {kludas}" if kludas else ""))
        time.sleep(KAVESANAS)
    if kludas:
        print(f"{nos}: {kludas} spēles neizdevās – palaid vēlreiz (ielasītās tiks izlaistas).")
    return 1 if kludas else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__)
        return 0
    if not os.path.isdir(VESTURE):
        print(f"Nav mapes {VESTURE}")
        return 1
    sezonas = args or sorted(s for s in os.listdir(VESTURE) if s.isdigit() and len(s) == 8)
    kods = 0
    for s in sezonas:
        mape = os.path.join(VESTURE, s)
        if not os.path.isdir(mape):
            print(f"Nav mapes {mape}")
            kods = 1
            continue
        kods = sezona(mape) or kods
    print("\nGatavs. Tagad:  python fantasy_backtest.py --visas --ablacija --bez-nedelam")
    return kods


if __name__ == "__main__":
    sys.exit(main())
