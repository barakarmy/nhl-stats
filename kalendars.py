import requests
import csv
import os
from datetime import datetime, timedelta

CSV_KALENDARS = "nhl_kalendars.csv"

def atjaunot_kalendaru():
    sodiena = datetime.now()
    beigu_datums = sodiena + timedelta(days=60) # Skatāmies 2 mēnešus uz priekšu
    
    print(f"Iegūstu NHL spēļu kalendāru no {sodiena.strftime('%Y-%m-%d')} līdz {beigu_datums.strftime('%Y-%m-%d')}...")
    
    # NHL API kalendārs pēc noklusējuma dod datus pa nedēļām, sākot no šodienas /v1/schedule/now
    # Bet lai paņemtu precīzi nākamos 2 mēnešus, mēs varam iet cauri vairākām secīgām nedēļām vai izmantot /v1/schedule/{date}
    
    visas_speles = []
    prakstijamais_datums = sodiena
    
    # Ejam cauri pa 7 dienām (nedēļām), kamēr sasniedzam 2 mēnešu robežu
    while prakstijamais_datums <= beigu_datums:
        datums_str = prakstijamais_datums.strftime('%Y-%m-%d')
        url = f"https://api-web.nhle.com/v1/schedule/{datums_str}"
        
        response = requests.get(url)
        if response.status_code == 200:
            dati = response.json()
            game_weeks = dati.get("gameWeek", [])
            
            for nedela in game_weeks:
                g_datums = nedela.get("date")
                # Pārliecināmies, ka datums nav pagātnē un nepārsniedz mūsu 2 mēnešu limitu
                g_dt = datetime.strptime(g_datums, '%Y-%m-%d')
                if sodiena.date() <= g_dt.date() <= beigu_datums.date():
                    for spele in nedela.get("games", []):
                        game_id = spele.get("id")
                        game_state = spele.get("gameState")  # FUT, LIVE, FINAL utt.
                        home_team = spele.get("homeTeam", {}).get("abbrev", "N/A")
                        away_team = spele.get("awayTeam", {}).get("abbrev", "N/A")
                        start_time = spele.get("startTimeUTC", "N/A")

                        # Pievienojam sarakstam, ja vēl nav pievienots (lai izvairītos no dublikātiem)
                        speles_ieraksts = {
                            "datums": g_datums,
                            "game_id": game_id,
                            "statuss": game_state,
                            "majas_komanda": home_team,
                            "viesu_komanda": away_team,
                            "sakuma_laiks_utc": start_time
                        }
                        if speles_ieraksts not in visas_speles:
                            visas_speles.append(speles_ieraksts)
                            
        prakstijamais_datums += timedelta(days=7)

    if not visas_speles:
        print("Netika atrastas nevienas spēles kalendārā.")
        return

    # Sakārtojam hronoloģiski pēc datuma
    visas_speles = sorted(visas_speles, key=lambda x: x['datums'])

    # Saglabājam CSV failā (pārrakstām, lai vecās/pagājušās spēles automātiski pazustu)
    kolonnas = ["datums", "game_id", "statuss", "majas_komanda", "viesu_komanda", "sakuma_laiks_utc"]
    
    with open(CSV_KALENDARS, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=kolonnas)
        writer.writeheader()
        for spress in visas_speles:
            writer.writerow(spress)
            
    print(f"Kalendārs veiksmīgi atjaunināts! Saglabātas {len(visas_speles)} nākotnes spēles failā {CSV_KALENDARS}.")

if __name__ == "__main__":
    atjaunot_kalendaru()
