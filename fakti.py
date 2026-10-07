"""
kalendars.py – nākamo NHL spēļu kalendārs → sezonas/nhl_kalendars.csv (to lasa lietotne un tiesnesi_planotie.py).

Palaiž NHL Daily Update darbplūsma (pirms nhl_dati.py; ja kalendārs neizdodas, datu atjaunināšana tik un tā turpinās). Avots: NHL oficiālais kalendārs (api-web.nhle.com/v1/schedule/{datums}),
kas atgriež 7 dienu "gameWeek"; skripts iet pa nedēļām 60 dienas uz priekšu.

- Tiek ņemtas tikai regulārās sezonas (gameType 2) un play-off (gameType 3) spēles – bez pirmssezonas (1) un All-Star (4),
  kurām ir neīstas "komandas".
- Atceltās (CNCL) un atliktās (PPD) spēles netiek saglabātas, jo to laiks vairs nav spēkā.
- Ja kāda nedēļa neielādējas arī pēc atkārtojumiem, esošais fails NETIEK pārrakstīts (lai kalendārā nepazustu spēles);
  skripts beidzas ar kļūdu, un darbplūsmā tas ir redzams.
- Kolonnas: pirmās sešas kā agrāk (lietotne tās izmanto), jaunās pievienotas beigās.
"""
import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

CSV_KALENDARS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sezonas", "nhl_kalendars.csv")
DIENAS_UZ_PRIEKSU = 60
SPELU_TIPI = {2: "RS", 3: "PO"}              # gameType → regulārā sezona / play-off
IZLAIST_STAVOKLI = {"CNCL", "PPD"}            # gameScheduleState: atcelta / atlikta
KOLONNAS = ["datums", "game_id", "statuss", "majas_komanda", "viesu_komanda", "sakuma_laiks_utc",
            "speles_tips", "sezona", "arena", "neitrala_vieta", "grafiks", "ja_vajadzes"]


def ielasit_nedelu(datums_str, meginajumi=3):
    """Viena kalendāra nedēļa (dict) vai None, ja neizdodas arī pēc atkārtojumiem."""
    url = f"https://api-web.nhle.com/v1/schedule/{datums_str}"
    for m in range(meginajumi):
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return r.json()
            print(f"  {datums_str}: HTTP {r.status_code}")
        except requests.RequestException as ex:
            print(f"  {datums_str}: {type(ex).__name__}")
        time.sleep(2 * (m + 1))
    return None


def teksts(v):
    """NHL API teksta lauki dažkārt ir {"default": "..."}."""
    return v.get("default", "") if isinstance(v, dict) else (v or "")


def atjaunot_kalendaru():
    sodiena = datetime.now(timezone.utc).date()
    beigu_datums = sodiena + timedelta(days=DIENAS_UZ_PRIEKSU)
    print(f"Iegūstu NHL spēļu kalendāru no {sodiena} līdz {beigu_datums}...")

    speles = {}                                   # game_id → ieraksts (bez dublikātiem)
    neizdevas = []
    d = sodiena
    while d <= beigu_datums:
        dati = ielasit_nedelu(d.isoformat())
        if dati is None:
            neizdevas.append(d.isoformat())
        else:
            for diena in dati.get("gameWeek", []):
                g_datums = diena.get("date")
                try:
                    g_dt = datetime.strptime(g_datums, "%Y-%m-%d").date()
                except (TypeError, ValueError):
                    continue
                if not (sodiena <= g_dt <= beigu_datums):
                    continue
                for spele in diena.get("games", []):
                    tips = SPELU_TIPI.get(spele.get("gameType"))
                    if tips is None:                                  # pirmssezona, All-Star u.c.
                        continue
                    if spele.get("gameScheduleState") in IZLAIST_STAVOKLI:
                        continue
                    gid = spele.get("id")
                    if gid is None:
                        continue
                    speles[gid] = {
                        "datums": g_datums,
                        "game_id": gid,
                        "statuss": spele.get("gameState", ""),                     # FUT, PRE, LIVE, OFF, FINAL ...
                        "majas_komanda": (spele.get("homeTeam") or {}).get("abbrev", "N/A"),
                        "viesu_komanda": (spele.get("awayTeam") or {}).get("abbrev", "N/A"),
                        "sakuma_laiks_utc": spele.get("startTimeUTC", ""),
                        "speles_tips": tips,
                        "sezona": spele.get("season", ""),
                        "arena": teksts(spele.get("venue")),
                        "neitrala_vieta": 1 if spele.get("neutralSite") else 0,      # piem., spēles Eiropā
                        "grafiks": spele.get("gameScheduleState", ""),
                        "ja_vajadzes": 1 if spele.get("ifNecessary") else 0,         # play-off sērijas spēle "ja vajadzēs"
                    }
        d += timedelta(days=7)

    if neizdevas:
        print(f"KĻŪDA: neizdevās ielādēt nedēļas, kas sākas {', '.join(neizdevas)}. Esošais {CSV_KALENDARS} netiek pārrakstīts.")
        sys.exit(1)
    if not speles:
        print("Kalendārā nav nevienas regulārās sezonas vai play-off spēles (piem., starpsezonā). Esošais fails netiek pārrakstīts.")
        return

    rindas = sorted(speles.values(), key=lambda x: (x["datums"], x["sakuma_laiks_utc"], x["game_id"]))
    os.makedirs(os.path.dirname(CSV_KALENDARS), exist_ok=True)
    tmp = CSV_KALENDARS + ".tmp"                  # vispirms pagaidu fails, tad aizstāj (fails nekad nepaliek pa pusei uzrakstīts)
    with open(tmp, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=KOLONNAS)
        writer.writeheader()
        writer.writerows(rindas)
    os.replace(tmp, CSV_KALENDARS)
    po = sum(1 for r in rindas if r["speles_tips"] == "PO")
    print(f"Kalendārs atjaunināts: {len(rindas)} spēles ({po} play-off) failā {CSV_KALENDARS}.")


if __name__ == "__main__":
    atjaunot_kalendaru()
