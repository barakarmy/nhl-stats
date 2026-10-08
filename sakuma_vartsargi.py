"""
sakuma_vartsargi.py – sākuma vārtsargi līdz spēlei → sezonas/vartsargi_sakuma.csv

Palaiž darbplūsma "NHL Starting Goalies" ik 30 min ~16:00–02:30 Rīgā (kad komandas paziņo vārtsargus).
Avots: Daily Faceoff "Starting Goalies" lapa (dailyfaceoff.com/starting-goalies/<ASV austrumu datums>) – NHL oficiālie dati
apstiprinātos vārtsargus pirms spēles nepublicē. Viens pieprasījums palaišanā (pieklājīgs biežums).
"""
import csv
import html
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from koeficienti import kods          # noqa: E402  (komandu nosaukums → NHL kods)

FAILS = os.path.join(BASE, "sezonas", "vartsargi_sakuma.csv")
URL = "https://www.dailyfaceoff.com/starting-goalies/{datums}"
KOLONNAS = ["datums_et", "sakums_utc", "majas", "viesi", "komanda", "puse", "vartsargs", "statuss", "statusa_laiks", "ielade"]
STATUSI = {"confirmed": "Confirmed", "expected": "Expected", "likely": "Likely", "probable": "Likely", "unconfirmed": "Unconfirmed"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
IZLAIST = {"show more", "line combos", "news", "stats", "schedule", "--", "|", "•"}


def teksta_rindas(saturs):
    """HTML → teksta rindas (bez skriptiem un stiliem)."""
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", "\n", saturs)
    s = re.sub(r"(?s)<[^>]+>", "\n", s)
    return [r for r in (html.unescape(x).strip() for x in s.splitlines()) if r]


def parset(rindas):
    """Spēles no lapas teksta: komandas tagad sadalītas pa 3 rindām (Viesi, 'at', Mājinieki)."""
    speles = []
    i, n = 0, len(rindas)
    
    while i < n - 3:
        # Pārbaudām, vai i+1 rinda ir atdalītājs (at, @, vs)
        atdalitajs = rindas[i + 1].strip().lower()
        if atdalitajs in ("at", "@", "vs", "vs."):
            a = kods(rindas[i].strip())
            h = kods(rindas[i + 2].strip())
            
            # Ja atpazīstam abas komandas un i+3 rindā ir ISO sākuma laiks
            if a and h and ISO.match(rindas[i + 3].strip()):
                sakums = rindas[i + 3].strip()
                j, vartsargi = i + 4, []
                
                # Meklējam vārtsargus līdz atrodam 2 (vai sākas nākamā spēle)
                while j < n and len(vartsargi) < 2:
                    # Drošības pārbaude: nepārlekt uz nākamo spēli
                    if j + 2 < n and rindas[j + 1].strip().lower() in ("at", "@", "vs", "vs.") and kods(rindas[j].strip()):
                        break
                        
                    st = STATUSI.get(rindas[j].strip().lower())
                    if st:
                        # Vārtsarga vārds atrodas tieši virs statusa (ignorējot lieko tekstu)
                        vards = next((rindas[k].strip() for k in range(j - 1, max(i + 3, j - 6), -1)
                                      if rindas[k].strip().lower() not in IZLAIST and not ISO.match(rindas[k].strip()) and not rindas[k].strip().startswith("http")), "")
                        
                        # Apstiprinājuma laiks (ja seko ISO formātā)
                        laiks = rindas[j + 1].strip() if j + 1 < n and ISO.match(rindas[j + 1].strip()) else ""
                        vartsargi.append((vards, st, laiks))
                    j += 1
                    
                if len(vartsargi) == 2:
                    speles.append({"sakums_utc": sakums, "viesi": a, "majas": h, "v_viesi": vartsargi[0], "v_majas": vartsargi[1]})
                
                i = j - 1  # Pārbīdām indeksu uz apstrādātā bloka beigām
        i += 1
        
    return speles


def ielasit(datums_et):
    url = URL.format(datums=datums_et)
    for m in range(2):
        try:
            r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0 (personal NHL stats app; 1 request / 30 min)"})
            if r.status_code == 200:
                return r.text
            print(f"Daily Faceoff: HTTP {r.status_code}")
        except requests.RequestException as ex:
            print(f"Daily Faceoff: {type(ex).__name__}")
        time.sleep(5)
    return None


def _lasit_csv(c):
    if not os.path.exists(c):
        return []
    with open(c, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    tagad = datetime.now(timezone.utc)
    datums_et = (tagad - timedelta(hours=5)).strftime("%Y-%m-%d")       # ASV austrumu datums (pietiekami precīzi spēļu dienai)
    saturs = ielasit(datums_et)
    
    if saturs is None:
        print("Lapu ielādēt neizdevās – fails netiek mainīts.")
        return 1
        
    speles = parset(teksta_rindas(saturs))
    
    if not speles:
        print(f"{datums_et}: lapā nav atrastu spēļu (vai mainījusies lapas uzbūve) – fails netiek mainīts.")
        return 0
        
    tagad_txt = tagad.strftime("%Y-%m-%dT%H:%M:%SZ")
    jaunas = []
    for s in speles:
        for puse, kom, (vards, st, laiks) in (("away", s["viesi"], s["v_viesi"]), ("home", s["majas"], s["v_majas"])):
            jaunas.append({"datums_et": datums_et, "sakums_utc": s["sakums_utc"][:19] + "Z", "majas": s["majas"], "viesi": s["viesi"],
                           "komanda": kom, "puse": puse, "vartsargs": vards, "statuss": st, "statusa_laiks": laiks, "ielade": tagad_txt})
                           
    # iepriekšējās rindas citām spēlēm paliek, kamēr spēle nav sākusies sen (≤ 12 h pēc sākuma)
    atsl = {(r["majas"], r["viesi"], r["sakums_utc"][:13]) for r in jaunas}
    robeza = tagad - timedelta(hours=12)
    vecas = [r for r in _lasit_csv(FAILS) if (r["majas"], r["viesi"], r["sakums_utc"][:13]) not in atsl
             and datetime.fromisoformat(r["sakums_utc"].replace("Z", "+00:00")) > robeza]
    rindas = sorted(vecas + jaunas, key=lambda r: (r["sakums_utc"], r["majas"], r["puse"]))
    
    os.makedirs(os.path.dirname(FAILS), exist_ok=True)
    tmp = FAILS + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOLONNAS)
        w.writeheader()
        w.writerows(rindas)
    os.replace(tmp, FAILS)
    
    apst = sum(1 for r in jaunas if r["statuss"] == "Confirmed")
    print(f"{datums_et}: {len(speles)} spēles, apstiprināti {apst} no {len(jaunas)} vārtsargiem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
