"""
metieni.py – metienu dati xG (paredzamo vārtu) modelim.

No NHL play-by-play katrai spēlei tiek saglabāti visi NEBLOĶĒTIE metieni (metiens vārtos, garām, vārti) ar pazīmēm:
attālums un leņķis līdz vārtiem, metiena veids, atlēciens (iepriekšējais metiens ≤ 3 s), ātrais uzbrukums (iepriekšējais
notikums citā zonā ≤ 4 s), sastāvs (5v5 / vairākums / mazākums / cits), tukši vārti, vārtsargs vārtos.

Lietošana:
  - ikdienas atjaunināšana (nhl_dati.py) pievieno jauno spēļu metienus failā sezonas/metieni.csv;
  - lokāli, vienreiz:  python metieni.py 20232024 20242025 20252026   → sezonas/vesture/<sezona>/metieni.csv
                       python metieni.py --aktiva                       → trūkstošās šīs sezonas spēles sezonas/metieni.csv
    (ielādē tikai play-by-play katrai spēlei no speles.csv; var pārtraukt un palaist vēlreiz – gatavās spēles tiek izlaistas).
"""
import csv
import math
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
KOLONNAS = ["datums", "game_id", "period", "period_type", "sek", "komanda", "pretinieks", "majas", "tips", "varti",
            "x", "y", "attalums", "lenkis", "veids", "atleciens", "atrais", "saviem", "pretiniekiem", "tuksi",
            "sastavs", "vartsargs", "metejs"]
NEBLOKETI = {"shot-on-goal": "sog", "missed-shot": "miss", "goal": "goal"}
VARTI_X = 89.0


def _sek(laiks):
    try:
        m, s = str(laiks).split(":")
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return 0


def _sit(kods):
    k = str(kods or "")
    return (int(k[0]), int(k[1]), int(k[2]), int(k[3])) if len(k) == 4 and k.isdigit() else None


def metienu_rindas(pbp, gid, datums):
    """Play-by-play (dict no NHL API) → metienu rindas (list[dict])."""
    home, away = pbp.get("homeTeam") or {}, pbp.get("awayTeam") or {}
    home_id, away_id = home.get("id"), away.get("id")
    ab = {home_id: home.get("abbrev", ""), away_id: away.get("abbrev", "")}
    rindas = []
    ieprieks = None                        # (sek, komanda, tips, zona)
    for p in pbp.get("plays") or []:
        det = p.get("details") or {}
        pd_ = p.get("periodDescriptor") or {}
        per = pd_.get("number") or 0
        ptype = str(pd_.get("periodType") or "")
        sek = (int(per) - 1) * 1200 + _sek(p.get("timeInPeriod"))
        tips = p.get("typeDescKey")
        tid = det.get("eventOwnerTeamId")
        zona = det.get("zoneCode")
        if tips in NEBLOKETI and ptype != "SO" and tid in ab:
            majas = 1 if tid == home_id else 0
            x, y = det.get("xCoord"), det.get("yCoord")
            if x is None or y is None:
                ieprieks = (sek, tid, tips, zona)
                continue
            puse = p.get("homeTeamDefendingSide")
            if puse in ("left", "right"):
                # mājinieki aizsargā kreisos (x<0) vārtus → mājinieki met uz +89; viesi – pretēji
                merkis = VARTI_X if (puse == "left") == bool(majas) else -VARTI_X
            else:
                merkis = VARTI_X if x >= 0 else -VARTI_X
            dx = abs(merkis - x)
            attalums = math.hypot(dx, y)
            lenkis = math.degrees(math.atan2(abs(y), dx)) if dx > 0 else 90.0
            s = _sit(p.get("situationCode"))
            if s:
                aw_g, aw_s, hm_s, hm_g = s
                saviem, pret = (hm_s, aw_s) if majas else (aw_s, hm_s)
                tuksi = int((aw_g if majas else hm_g) == 0)       # pretinieka vārti tukši
            else:
                saviem, pret, tuksi = 5, 5, 0
            sastavs = "5v5" if (saviem, pret) == (5, 5) else ("PP" if saviem > pret else ("SH" if saviem < pret else "EV"))
            atleciens = int(ieprieks is not None and ieprieks[1] == tid and ieprieks[2] in NEBLOKETI and 0 <= sek - ieprieks[0] <= 3)
            atrais = int(ieprieks is not None and ieprieks[3] in ("N", "D") and 0 <= sek - ieprieks[0] <= 4 and ieprieks[2] not in NEBLOKETI)
            rindas.append({
                "datums": datums, "game_id": gid, "period": per, "period_type": ptype, "sek": sek,
                "komanda": ab.get(tid, ""), "pretinieks": ab.get(away_id if majas else home_id, ""), "majas": majas,
                "tips": NEBLOKETI[tips], "varti": int(tips == "goal"), "x": x, "y": y,
                "attalums": round(attalums, 2), "lenkis": round(lenkis, 2), "veids": det.get("shotType") or "",
                "atleciens": atleciens, "atrais": atrais, "saviem": saviem, "pretiniekiem": pret, "tuksi": tuksi,
                "sastavs": sastavs, "vartsargs": det.get("goalieInNetId") or "",
                "metejs": det.get("shootingPlayerId") or det.get("scoringPlayerId") or "",
            })
        if tips not in ("stoppage", "period-start", "period-end", "game-end"):
            ieprieks = (sek, tid, tips, zona)
    return rindas


# ----------------------------------------------------------------------------
# VĒSTURES / AKTĪVĀS SEZONAS PAPILDINĀŠANA (lokāli)
# ----------------------------------------------------------------------------
def _lasit(c):
    if not os.path.exists(c):
        return []
    with open(c, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def papildinat(mape):
    """Ielādē play-by-play spēlēm no <mape>/speles.csv, kurām vēl nav metienu <mape>/metieni.csv."""
    import requests
    speles = _lasit(os.path.join(mape, "speles.csv"))
    fails = os.path.join(mape, "metieni.csv")
    gatavas = {r["game_id"] for r in _lasit(fails)}
    darbs = [(r["game_id"], r.get("datums", "")) for r in speles if r["game_id"] not in gatavas]
    print(f"{os.path.relpath(mape, BASE)}: {len(speles)} spēles, jāielādē {len(darbs)}")
    jauns = not os.path.exists(fails)
    sesija = requests.Session()
    kludas = 0
    with open(fails, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOLONNAS)
        if jauns:
            w.writeheader()
        for n, (gid, datums) in enumerate(darbs, 1):
            dati = None
            for m in range(3):
                try:
                    r = sesija.get(f"https://api-web.nhle.com/v1/gamecenter/{gid}/play-by-play", timeout=30)
                    if r.status_code == 200:
                        dati = r.json()
                        break
                except Exception:
                    pass
                time.sleep(2 * (m + 1))
            if dati is None:
                kludas += 1
                continue
            rindas = metienu_rindas(dati, gid, datums)
            if rindas:                     # spēle bez metieniem netiek atzīmēta kā gatava (to mēģinās vēlreiz)
                w.writerows(rindas)
                f.flush()
            if n % 50 == 0:
                print(f"  {n}/{len(darbs)}")
            time.sleep(0.25)
    print(f"  gatavs (neizdevās: {kludas})")
    return kludas


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    mapes = [os.path.join(BASE, "sezonas")] if args[0] == "--aktiva" else [os.path.join(BASE, "sezonas", "vesture", s) for s in args]
    kl = 0
    for m in mapes:
        if not os.path.exists(os.path.join(m, "speles.csv")):
            print(f"Nav {os.path.relpath(m, BASE)}/speles.csv – izlaists.")
            continue
        kl += papildinat(m)
    return 1 if kl else 0


if __name__ == "__main__":
    sys.exit(main())
