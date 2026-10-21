"""
metieni.py – metienu dati xG (paredzamo vārtu) modelim.

No NHL play-by-play katrai spēlei tiek saglabāti visi NEBLOĶĒTIE metieni (metiens vārtos, garām, vārti) ar pazīmēm:
attālums un leņķis līdz vārtiem, metiena veids, atlēciens (iepriekšējais metiens ≤ 3 s), ātrais uzbrukums (iepriekšējais
notikums citā zonā ≤ 4 s), sastāvs (5v5 / vairākums / mazākums / cits), tukši vārti, vārtsargs vārtos.

BLOĶĒTIE METIENI (atsevišķs fails sezonas/bloketi.csv – xG modelis un visi xG aprēķini tos NEizmanto):
  katram bloķētajam metienam – metējs, bloķētājs, komandas, sastāvs (5v5 / PP / SH), iemesls ("blocked" vai
  "teammate-blocked" – metiens trāpīja savējam). Vajadzīgi Corsi (iCF/60 = visi metienu mēģinājumi) aprēķinam.

Lietošana:
  - ikdienas atjaunināšana (nhl_dati.py) pievieno jauno spēļu metienus failā sezonas/metieni.csv
    un bloķētos metienus failā sezonas/bloketi.csv;
  - ikdienas darbplūsma arī papildina bloketi.csv vecākām spēlēm (python metieni.py --bloketi --aktiva --max 300);
  - lokāli, vienreiz:  python metieni.py 20232024 20242025 20252026   → sezonas/vesture/<sezona>/metieni.csv
                       python metieni.py --aktiva                       → trūkstošās šīs sezonas spēles sezonas/metieni.csv
    (ielādē tikai play-by-play katrai spēlei no speles.csv; var pārtraukt un palaist vēlreiz – gatavās spēles tiek izlaistas).
  - bloķētie metieni vecākām spēlēm:
                       python metieni.py --bloketi --aktiva               → sezonas/bloketi.csv
                       python metieni.py --bloketi 20232024 20242025      → sezonas/vesture/<sezona>/bloketi.csv
                       (--max N – ne vairāk kā N spēles vienā palaišanā)
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
BLOKETI_KOL = ["datums", "game_id", "period", "period_type", "sek", "komanda", "pretinieks", "majas", "saviem",
               "pretiniekiem", "tuksi", "sastavs", "metejs", "bloketajs", "iemesls"]
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


def bloketo_rindas(pbp, gid, datums):
    """Play-by-play → bloķēto metienu rindas (metēja komandas skatījumā). Metienu sērija netiek iekļauta."""
    home, away = pbp.get("homeTeam") or {}, pbp.get("awayTeam") or {}
    home_id, away_id = home.get("id"), away.get("id")
    ab = {home_id: home.get("abbrev", ""), away_id: away.get("abbrev", "")}
    komanda_pec_sp = {r.get("playerId"): r.get("teamId") for r in pbp.get("rosterSpots") or []}
    rindas = []
    for p in pbp.get("plays") or []:
        if p.get("typeDescKey") != "blocked-shot":
            continue
        det = p.get("details") or {}
        pd_ = p.get("periodDescriptor") or {}
        ptype = str(pd_.get("periodType") or "")
        if ptype == "SO":
            continue
        metejs = det.get("shootingPlayerId")
        # NHL: eventOwnerTeamId = metēja komanda; rezervei – metēja komanda pēc sastāva
        tid = det.get("eventOwnerTeamId") if det.get("eventOwnerTeamId") in ab else komanda_pec_sp.get(metejs)
        if tid not in ab:
            continue
        majas = 1 if tid == home_id else 0
        per = pd_.get("number") or 0
        s = _sit(p.get("situationCode"))
        if s:
            aw_g, aw_s, hm_s, hm_g = s
            saviem, pret = (hm_s, aw_s) if majas else (aw_s, hm_s)
            tuksi = int((aw_g if majas else hm_g) == 0)
        else:
            saviem, pret, tuksi = 5, 5, 0
        sastavs = "5v5" if (saviem, pret) == (5, 5) else ("PP" if saviem > pret else ("SH" if saviem < pret else "EV"))
        rindas.append({
            "datums": datums, "game_id": gid, "period": per, "period_type": ptype,
            "sek": (int(per) - 1) * 1200 + _sek(p.get("timeInPeriod")),
            "komanda": ab[tid], "pretinieks": ab.get(away_id if majas else home_id, ""), "majas": majas,
            "saviem": saviem, "pretiniekiem": pret, "tuksi": tuksi, "sastavs": sastavs,
            "metejs": metejs or "", "bloketajs": det.get("blockingPlayerId") or "", "iemesls": det.get("reason") or "",
        })
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


def papildinat_bloketos(mape, max_speles=None):
    """Bloķētie metieni spēlēm no <mape>/speles.csv, kurām vēl nav ierakstu <mape>/bloketi.csv (+ atzīme bloketi_gatavs.txt)."""
    import requests
    speles = _lasit(os.path.join(mape, "speles.csv"))
    fails = os.path.join(mape, "bloketi.csv")
    gatavs_f = os.path.join(mape, "bloketi_gatavs.txt")          # arī spēles bez neviena bloķēta metiena
    gatavas = {r["game_id"] for r in _lasit(fails)}
    if os.path.exists(gatavs_f):
        with open(gatavs_f, encoding="utf-8") as f:
            gatavas |= {x.strip() for x in f if x.strip()}
    darbs = [(r["game_id"], r.get("datums", "")) for r in speles if r["game_id"] not in gatavas and r.get("home_total") not in ("", None)]
    if max_speles:
        darbs = darbs[:max_speles]
    print(f"{os.path.relpath(mape, BASE)}: bloķētie metieni – jāielādē {len(darbs)} spēles")
    if not darbs:
        return 0
    jauns = not os.path.exists(fails)
    sesija = requests.Session()
    kludas = n_r = 0
    with open(fails, "a", newline="", encoding="utf-8") as f, open(gatavs_f, "a", encoding="utf-8") as g:
        w = csv.DictWriter(f, fieldnames=BLOKETI_KOL)
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
            rindas = bloketo_rindas(dati, gid, datums)
            w.writerows(rindas)
            g.write(f"{gid}\n")
            n_r += len(rindas)
            if n % 50 == 0:
                f.flush()
                g.flush()
                print(f"  {n}/{len(darbs)}")
            time.sleep(0.2)
    print(f"  gatavs: {n_r} bloķēti metieni (neizdevās: {kludas})")
    return kludas


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    bloketi = "--bloketi" in args
    max_speles = None
    if "--max" in args:
        i = args.index("--max")
        max_speles = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    args = [x for x in args if x != "--bloketi"]
    mapes = [os.path.join(BASE, "sezonas")] if args and args[0] == "--aktiva" else [os.path.join(BASE, "sezonas", "vesture", s) for s in args]
    kl = 0
    for m in mapes:
        if not os.path.exists(os.path.join(m, "speles.csv")):
            print(f"Nav {os.path.relpath(m, BASE)}/speles.csv – izlaists.")
            continue
        kl += papildinat_bloketos(m, max_speles) if bloketi else papildinat(m)
    return 1 if kl else 0


if __name__ == "__main__":
    sys.exit(main())
