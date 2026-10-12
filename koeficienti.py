"""
koeficienti.py – NHL koeficienti no The Odds API (the-odds-api.com) → sezonas/koeficienti.csv

Palaiž darbplūsma "NHL Odds" 3 reizes dienā (~09:00, ~16:30, ~23:00 Rīgā). API atslēga – GitHub noslēpums ODDS_API_KEY
(vide: ODDS_API_KEY); kodā un žurnālos tā netiek rādīta.

Viena ielāde = 1 pieprasījums: ES reģions, tirgi h2h + spreads + totals = 3 kredīti (bezmaksas plānā 500 mēnesī).
ES bukmeikeriem hokeja h2h parasti ir pamatlaika 1X2 (ar neizšķirtu); ja bukmeikers dod tikai 2 iznākumus, tas ir
uzvarētājs ar papildlaiku (saglabāts kā tirgus "ml"). ±1.5 un totāli bukmeikeriem parasti ietver papildlaiku.

Faili:
- sezonas/koeficienti.csv – pašreizējie koeficienti spēlēm, kas kalendārā ir tuvāko 3 dienu laikā (pārrakstīts katrā ielādē);
  katram koeficientam ir arī iepriekšējās ielādes vērtība (koef_iepr), lai redzētu izmaiņas.
- sezonas/koeficienti_meta.json – ielādes laiks, atlikušie kredīti, spēļu skaits.
- sezonas/koeficienti_arhivs.csv – viena rinda katrai spēlei: Pinnacle pirmie un pēdējie zināmie 1X2 un totāla koeficienti
  (vēlāk – modeļa salīdzināšanai ar tirgu; lietotnē netiek rādīts).
Ja ielāde neizdodas, esošie faili netiek mainīti.

Papildu ielāde pēc vārtsargu paziņošanas (darbplūsma "NHL Starting Goalies", ik 30 min vakaros):
    python koeficienti.py --ja-vajag
Koeficienti tiek ielādēti tikai tad, ja kādai spēlei, kas sākas tuvāko VARTSARGU_LOGS_H stundu laikā, abi sākuma vārtsargi ir
paziņoti (Confirmed / Expected) PĒC pēdējās koeficientu ielādes – tad tirgus jau ir ievērtējis vārtsargu ziņas, un Picks var
atlasīt likmes ar pareizajiem vārtsargiem. Kredītu sargs: ne vairāk par MAX_PAPILDU_DIENA papildu ielādēm dienā un tikai, ja
atlikums pietiek parastajām ielādēm līdz mēneša beigām (+ rezerve).
"""
import calendar
import csv
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
MAPE = os.path.join(BASE, "sezonas")
KALENDARS = os.path.join(MAPE, "nhl_kalendars.csv")
FAILS = os.path.join(MAPE, "koeficienti.csv")
META = os.path.join(MAPE, "koeficienti_meta.json")
ARHIVS = os.path.join(MAPE, "koeficienti_arhivs.csv")
VARTSARGI = os.path.join(MAPE, "vartsargi_sakuma.csv")
VARTSARGU_LOGS_H = 4             # papildu ielāde tikai spēlēm, kas sākas tuvāko 4 h laikā
MAX_PAPILDU_DIENA = 2            # papildu ielādes dienā (katra = 3 kredīti)
KREDITI_IELADE = 3
PARASTAS_DIENA = 3               # parastās ielādes dienā (odds.yml)
KREDITU_REZERVE = 15
VARTSARGI_ZINAMI = ("Confirmed", "Expected")
URL = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds"
DIENAS = 3
KOLONNAS = ["game_id", "sakums_utc", "majas", "viesi", "bukmeikers", "tirgus", "iznakums", "linija", "koef",
            "koef_iepr", "atjaunots", "ielade"]
ARH_KOLONNAS = ["game_id", "sakums_utc", "majas", "viesi", "pirmo_reizi", "pedejo_reizi",
                "p1_pirmais", "pX_pirmais", "p2_pirmais", "p1_pedejais", "pX_pedejais", "p2_pedejais",
                "tot_linija", "over_pirmais", "under_pirmais", "over_pedejais", "under_pedejais"]
# komandu nosaukumi (bez diakritikas un pieturzīmēm, mazie burti) → NHL kods
KOMANDAS = {
    "anaheim ducks": "ANA", "boston bruins": "BOS", "buffalo sabres": "BUF", "calgary flames": "CGY",
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


def _lasit_csv(c):
    if not os.path.exists(c):
        return []
    with open(c, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _rakstit_csv(c, kolonnas, rindas):
    tmp = c + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolonnas)
        w.writeheader()
        w.writerows(rindas)
    os.replace(tmp, c)


def _laiks(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def kalendara_speles(tagad):
    """Kalendāra spēles tuvāko DIENAS dienu laikā: [(game_id, mājinieki, viesi, sākums_utc)]."""
    out = []
    for r in _lasit_csv(KALENDARS):
        t = _laiks(r.get("sakuma_laiks_utc"))
        if t and tagad - timedelta(hours=1) <= t <= tagad + timedelta(days=DIENAS):
            out.append((r["game_id"], r["majas_komanda"], r["viesu_komanda"], t))
    return out


def ielasit(api_atslega):
    """(spēles, galvenes) no The Odds API; None, ja neizdodas."""
    params = {"apiKey": api_atslega, "regions": "eu", "markets": "h2h,spreads,totals", "oddsFormat": "decimal", "dateFormat": "iso"}
    for m in range(3):
        try:
            r = requests.get(URL, params=params, timeout=30)
            if r.status_code == 200:
                return r.json(), r.headers
            print(f"The Odds API: HTTP {r.status_code} ({r.text[:120]})")      # atslēga atbildē netiek atkārtota
            if r.status_code in (401, 403, 422, 429):
                return None
        except requests.RequestException as ex:
            print(f"The Odds API: {type(ex).__name__}")
        time.sleep(5 * (m + 1))
    return None


def parset(notikumi, speles, tagad_txt):
    """Koeficientu rindas spēlēm, kas sakrīt ar kalendāru (komandas un sākums ±12 h)."""
    rindas = []
    for ev in notikumi:
        h, a = kods(ev.get("home_team")), kods(ev.get("away_team"))
        t = _laiks(ev.get("commence_time"))
        if not h or not a or not t:
            continue
        sp = next((s for s in speles if s[1] == h and s[2] == a and abs((s[3] - t).total_seconds()) <= 12 * 3600), None)
        if sp is None:
            continue
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                outs = mk.get("outcomes", [])
                if mk.get("key") == "h2h":
                    ir_neizskirts = any(_norm(o.get("name")) == "draw" for o in outs)
                    tirgus = "1x2" if ir_neizskirts else "ml"
                    for o in outs:
                        nm = _norm(o.get("name"))
                        izn = "X" if nm == "draw" else ("1" if kods(o.get("name")) == h else ("2" if kods(o.get("name")) == a else None))
                        if izn:
                            rindas.append(_rinda(sp, h, a, bk, tirgus, izn, "", o.get("price"), mk, tagad_txt))
                elif mk.get("key") == "spreads":
                    for o in outs:
                        izn = "1" if kods(o.get("name")) == h else ("2" if kods(o.get("name")) == a else None)
                        if izn:
                            rindas.append(_rinda(sp, h, a, bk, "pm", izn, o.get("point", ""), o.get("price"), mk, tagad_txt))
                elif mk.get("key") == "totals":
                    for o in outs:
                        izn = {"over": "over", "under": "under"}.get(_norm(o.get("name")))
                        if izn:
                            rindas.append(_rinda(sp, h, a, bk, "tot", izn, o.get("point", ""), o.get("price"), mk, tagad_txt))
    return rindas


def _rinda(sp, h, a, bk, tirgus, izn, linija, koef, mk, tagad_txt):
    return {"game_id": sp[0], "sakums_utc": sp[3].strftime("%Y-%m-%dT%H:%M:%SZ"), "majas": h, "viesi": a,
            "bukmeikers": bk.get("key", ""), "tirgus": tirgus, "iznakums": izn, "linija": linija,
            "koef": koef, "koef_iepr": "", "atjaunots": mk.get("last_update") or bk.get("last_update", ""), "ielade": tagad_txt}


def _atslega(r):
    return (str(r["game_id"]), r["bukmeikers"], r["tirgus"], r["iznakums"], str(r["linija"]))


def papildinat_iepriekseja(jaunas, vecas):
    """Katram koeficientam – iepriekšējās ielādes vērtība (ja tā atšķiras, var parādīt izmaiņu)."""
    vec = {_atslega(r): r for r in vecas}
    for r in jaunas:
        v = vec.get(_atslega(r))
        if v is not None:
            r["koef_iepr"] = v["koef"] if str(v["koef"]) != str(r["koef"]) else v.get("koef_iepr", "")
    return jaunas


def atjaunot_arhivu(rindas, tagad_txt):
    """Pinnacle pirmie un pēdējie 1X2 un galvenā totāla koeficienti katrai spēlei (pārējo spēļu rindas paliek)."""
    arh = {r["game_id"]: r for r in _lasit_csv(ARHIVS)}
    pa_spelem = {}
    for r in rindas:
        if r["bukmeikers"] == "pinnacle":
            pa_spelem.setdefault(str(r["game_id"]), []).append(r)
    for gid, rr in pa_spelem.items():
        x2 = {r["iznakums"]: r["koef"] for r in rr if r["tirgus"] == "1x2"}
        tot = [r for r in rr if r["tirgus"] == "tot"]
        a = arh.get(gid) or {k: "" for k in ARH_KOLONNAS}
        a.update(game_id=gid, sakums_utc=rr[0]["sakums_utc"], majas=rr[0]["majas"], viesi=rr[0]["viesi"], pedejo_reizi=tagad_txt)
        if not a.get("pirmo_reizi"):
            a["pirmo_reizi"] = tagad_txt
        if len(x2) == 3:
            if not a.get("p1_pirmais"):
                a.update(p1_pirmais=x2["1"], pX_pirmais=x2["X"], p2_pirmais=x2["2"])
            a.update(p1_pedejais=x2["1"], pX_pedejais=x2["X"], p2_pedejais=x2["2"])
        if tot:
            lin = str(a.get("tot_linija") or tot[0]["linija"])
            ou = {r["iznakums"]: r["koef"] for r in tot if str(r["linija"]) == lin}
            if len(ou) == 2:
                a["tot_linija"] = lin
                if not a.get("over_pirmais"):
                    a.update(over_pirmais=ou["over"], under_pirmais=ou["under"])
                a.update(over_pedejais=ou["over"], under_pedejais=ou["under"])
        arh[gid] = a
    _rakstit_csv(ARHIVS, ARH_KOLONNAS, sorted(arh.values(), key=lambda r: (r["sakums_utc"], r["game_id"])))


def tirit_atslegu(v):
    """Atslēga no noslēpuma vērtības: der arī, ja ielīmēta visa saite vai 'apiKey=...', ar pēdiņām vai atstarpēm."""
    v = (v or "").strip().strip('"').strip("'").strip()
    m = re.search(r"(?<![0-9a-fA-F])[0-9a-fA-F]{32}(?![0-9a-fA-F])", v)
    return m.group(0) if m else v


def _gh_output(ieladets):
    """GitHub Actions: steps.<id>.outputs.ieladets = true/false (lai nākamie soļi zinātu, vai koeficienti tika ielādēti)."""
    c = os.environ.get("GITHUB_OUTPUT")
    if c:
        with open(c, "a", encoding="utf-8") as f:
            f.write(f"ieladets={'true' if ieladets else 'false'}\n")


def _meta():
    try:
        with open(META, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def vajag_papildu(tagad):
    """(True/False, iemesls): vai pēc vārtsargu paziņošanas vajag papildu koeficientu ielādi."""
    meta = _meta()
    pedeja = _laiks(meta.get("ielade")) if meta.get("ielade") else None
    sodien = tagad.strftime("%Y-%m-%d")
    pap = (meta.get("papildu") or {}).get(sodien, 0)
    if pap >= MAX_PAPILDU_DIENA:
        return False, f"šodien jau {pap} papildu ielādes (max {MAX_PAPILDU_DIENA})"
    try:
        atl = int(float(meta.get("kreditu_atlikums")))
    except (TypeError, ValueError):
        atl = None
    dienas_atl = calendar.monthrange(tagad.year, tagad.month)[1] - tagad.day + 1
    vajag_parastajam = dienas_atl * PARASTAS_DIENA * KREDITI_IELADE + KREDITU_REZERVE
    if atl is not None and atl - KREDITI_IELADE < vajag_parastajam:
        return False, f"kredītu atlikums {atl} – jāpietiek parastajām ielādēm līdz mēneša beigām ({vajag_parastajam})"
    vs = _lasit_csv(VARTSARGI)
    pedejie = {}                                                   # (mājinieki, viesi, komanda) → jaunākais ieraksts
    for r in vs:
        k = (r.get("majas"), r.get("viesi"), r.get("komanda"))
        if k not in pedejie or str(r.get("ielade", "")) >= str(pedejie[k].get("ielade", "")):
            pedejie[k] = r
    for gid, h, a, t in kalendara_speles(tagad):
        if not (tagad < t <= tagad + timedelta(hours=VARTSARGU_LOGS_H)):
            continue
        rr = [pedejie.get((h, a, kom)) for kom in (h, a)]
        if not all(r and r.get("statuss") in VARTSARGI_ZINAMI for r in rr):
            continue
        laiki = [_laiks(r.get("statusa_laiks")) or _laiks(r.get("ielade")) for r in rr]
        jaunakais = max((x for x in laiki if x), default=None)
        if pedeja is None or (jaunakais and jaunakais > pedeja):
            return True, f"{a} @ {h}: abi vārtsargi paziņoti pēc pēdējās koeficientu ielādes"
    return False, "nav spēļu ar jauniem paziņotiem vārtsargiem tuvāko stundu laikā"


def main():
    papildu = "--ja-vajag" in sys.argv
    if papildu:
        ok, iemesls = vajag_papildu(datetime.now(timezone.utc))
        print(f"Papildu ielāde: {'jā' if ok else 'nē'} – {iemesls}")
        if not ok:
            _gh_output(False)
            return 0
    sakotneja = os.environ.get("ODDS_API_KEY", "")
    atslega = tirit_atslegu(sakotneja)
    if not atslega:
        print("Nav ODDS_API_KEY (GitHub: Settings → Secrets and variables → Actions → Repository secrets).")
        return 1
    # diagnostika bez atslēgas atklāšanas: garums un vai izskatās pēc The Odds API atslēgas (32 simboli 0-9, a-f)
    print(f"Atslēga: {len(atslega)} simboli, formāts {'derīgs' if re.fullmatch(r'[0-9a-fA-F]{32}', atslega) else 'NEDERĪGS (gaidīti 32 simboli 0-9, a-f)'}"
          f"{' (no noslēpuma izvilkta tikai atslēga)' if atslega != sakotneja.strip() else ''}")
    tagad = datetime.now(timezone.utc)
    tagad_txt = tagad.strftime("%Y-%m-%dT%H:%M:%SZ")
    speles = kalendara_speles(tagad)
    if not speles:
        print("Kalendārā tuvāko dienu laikā nav spēļu – ielāde netiek veikta (kredīti netiek tērēti).")
        return 0
    res = ielasit(atslega)
    if res is None:
        print("Koeficientus ielādēt neizdevās – esošie faili netiek mainīti.")
        return 1
    notikumi, galvenes = res
    rindas = papildinat_iepriekseja(parset(notikumi, speles, tagad_txt), _lasit_csv(FAILS))
    os.makedirs(MAPE, exist_ok=True)
    _rakstit_csv(FAILS, KOLONNAS, sorted(rindas, key=lambda r: (r["sakums_utc"], r["game_id"], r["bukmeikers"], r["tirgus"], r["iznakums"])))
    atjaunot_arhivu(rindas, tagad_txt)
    sodien = tagad.strftime("%Y-%m-%d")
    pap = {sodien: (_meta().get("papildu") or {}).get(sodien, 0) + (1 if papildu else 0)}     # tikai šodienas skaitītājs
    meta = {"ielade": tagad_txt, "speles": len({r["game_id"] for r in rindas}), "kalendara_speles": len(speles),
            "rindas": len(rindas), "kreditu_atlikums": galvenes.get("x-requests-remaining"), "kreditu_izlietots": galvenes.get("x-requests-used"),
            "papildu": pap}
    with open(META, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"Koeficienti: {meta['speles']} no {meta['kalendara_speles']} kalendāra spēlēm, {meta['rindas']} rindas; "
          f"kredīti: izlietoti {meta['kreditu_izlietots']}, atlikuši {meta['kreditu_atlikums']}.")
    _gh_output(True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
