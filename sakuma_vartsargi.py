"""
sakuma_vartsargi.py – sākuma vārtsargi līdz spēlei → sezonas/vartsargi_sakuma.csv

Palaiž darbplūsma "NHL Starting Goalies" ik 30 min ~16:00–02:30 Rīgā (kad komandas paziņo vārtsargus).
Avots: Daily Faceoff "Starting Goalies" lapa (dailyfaceoff.com/starting-goalies/<ASV austrumu datums>) – NHL oficiālie dati
apstiprinātos vārtsargus pirms spēles nepublicē. Viens pieprasījums palaišanā (pieklājīgs biežums).

Katrai šodienas spēlei: abu komandu vārtsargs un statuss:
  Confirmed (apstiprināts) · Expected / Likely (gaidāms) · Unconfirmed (nav apstiprināts – modelis paliek pie rotācijas).
Fails tiek pārrakstīts katrā palaišanā; spēles, kas sākās vairāk nekā pirms 12 h, tiek izmestas (glabājas ~2 dienas).
Ja lapu ielādēt vai nolasīt neizdodas, esošais fails netiek mainīts.
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
ISO = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z")
IZLAIST = {"show more", "line combos", "news", "stats", "schedule", "--", "|", "•"}


def teksta_rindas(saturs):
    """HTML → teksta rindas (bez skriptiem un stiliem)."""
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", "\n", saturs)
    s = re.sub(r"(?s)<[^>]+>", "\n", s)
    return [r for r in (html.unescape(x).strip() for x in s.splitlines()) if r]


def parset(rindas):
    """Spēles no lapas teksta: 'Viesi at/vs/@ Mājinieki', sākuma laiks, tad viesu un mājinieku vārtsargs."""
    speles = []
    i, n = 0, len(rindas)
    while i < n:
        # 1. Elastīga komandu pāra meklēšana (atbalsta at, @, vs)
        m = re.search(r"^\s*(.+?)\s+(?:at|@|vs\.?)\s+(.+?)\s*$", rindas[i], re.IGNORECASE)
        a = kods(m.group(1).strip()) if m else None
        h = kods(m.group(2).strip()) if m else None
        
        if not (a and h):
            i += 1
            continue
            
        # 2. Elastīga ISO laika meklēšana tuvākajās 5 rindās
        sakums = ""
        for k in range(1, 6):
            if i + k < n and ISO.search(rindas[i + k]):
                sakums = ISO.search(rindas[i + k]).group(0)
                break
        
        j = i + 1
        vartsargi = []
        
        # 3. Meklējam vārtsargu statusus līdz atduramies pret nākamo spēli
        while j < n and len(vartsargi) < 2:
            r = rindas[j]
            
            # Pārbaudām, vai nesākas jauna spēle (lai nepārlektu pāri datiem)
            m_next = re.search(r"^\s*(.+?)\s+(?:at|@|vs\.?)\s+(.+?)\s*$", r, re.IGNORECASE)
            if m_next and kods(m_next.group(1).strip()) and kods(m_next.group(2).strip()):
                break
            
            st = STATUSI.get(r.lower().strip())
            if st:
                # Vārtsarga vārds parasti ir 1-5 rindas virs statusa
                vards = next((rindas[k] for k in range(j - 1, max(i, j - 6), -1)
                              if rindas[k].lower() not in IZLAIST and not ISO.search(rindas[k]) and not rindas[k].startswith("http")), "")
                
                # Statusa apstiprināšanas laiks var būt uzreiz pēc statusa
                laiks = rindas[j + 1] if j + 1 < n and ISO.search(rindas[j + 1]) else ""
                vartsargi.append((vards.strip(), st, laiks))
            j += 1
            
        if len(vartsargi) == 2:
            sakums_val = sakums if sakums else "9999-12-31T00:00:00Z" # Drošības fallback, ja laiks nav atrasts
            speles.append({"sakums_utc": sakums_val, "viesi": a, "majas": h, "v_viesi": vartsargi[0], "v_majas": vartsargi[1]})
        
        i = j if j > i else i + 1
        
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
    datums_et = (tagad - timedelta(hours=5)).strftime("%Y-%m-%d")       # ASV austrumu datums
    saturs = ielasit(datums_et)
    if saturs is None:
        print("Lapu ielādēt neizdevās – fails netiek mainīts.")
        return 1
    
    rindas = teksta_rindas(saturs)
    
    # --- DIAGNOSTIKAS BLOKS (Lai saprastu, kas lācītim vēderā) ---
    print(f"Lapas HTML iegūts! Kopā atrastas {len(rindas)} teksta rindas.")
    print("--- Lapas teksta sākums (Pirmās 100 rindas) ---")
    for i, r in enumerate(rindas[:100]):
        print(f"{i}: {r}")
    print("--- Diagnostikas beigas ---")
    # -------------------------------------------------------------

    speles = parset(rindas)
    if not speles:
        print(f"{datums_et}: lapā nav atrastu spēļu (vai mainījusies lapas uzbūve) – fails netiek mainīts.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
