import requests
import csv
import os
from datetime import datetime, timedelta

CSV_FAILS = "nhl_sezona.csv"
VAKAR = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

def iegut_nakts_speles(datums):
    print(f"Iegūstu spēļu sarakstu par {datums}...")
    url = f"https://api-web.nhle.com/v1/score/{datums}"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Kļūda pieslēdzoties API: {response.status_code}")
        return []
        
    return response.json().get("games", [])

def saglabat_csv(dati_rakstisanai):
    fails_eksiste = os.path.isfile(CSV_FAILS)
    
    kolonnas = [
        "datums", "game_id", 
        "home_team", "away_team", 
        "home_total", "away_total",
        "home_p1", "away_p1", "home_p2", "away_p2", "home_p3", "away_p3", "home_ot", "away_ot",
        "home_pim_total", "away_pim_total",
        "home_pim_p1", "away_pim_p1", "home_pim_p2", "away_pim_p2", "home_pim_p3", "away_pim_p3", "home_pim_ot", "away_pim_ot",
        "home_sog_total", "away_sog_total",
        "home_sog_p1", "away_sog_p1", "home_sog_p2", "away_sog_p2", "home_sog_p3", "away_sog_p3", "home_sog_ot", "away_sog_ot",
        "home_ppg", "away_ppg", 
        "home_pp_sog", "away_pp_sog"
    ]
    
    with open(CSV_FAILS, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=kolonnas)
        if not fails_eksiste:
            writer.writeheader()
        for rinda in dati_rakstisanai:
            writer.writerow(rinda)

def main():
    speles = iegut_nakts_speles(VAKAR)
    
    if not speles:
        print(f"Neviena spēle {VAKAR} netika atrasta.")
        return

    saglabajamie_dati = []

    for spele in speles:
        game_id = spele.get("id")
        game_state = spele.get("gameState")
        
        # PĀRBAUDE: Apstrādājam TIKAI tās spēles, kas ir pilnībā beigušas savu gaitu (OFF vai FINAL)
        if game_state not in ["OFF", "FINAL"]:
            print(f"Spēle {game_id} vēl nav beigusies (Statuss: {game_state}). Izlaižam.")
            continue

        home_team = spele.get("homeTeam", {}).get("abbrev", "N/A")
        away_team = spele.get("awayTeam", {}).get("abbrev", "N/A")
        
        print(f"Apstrādāju beigušos spēli: {away_team} @ {home_team} (ID: {game_id})")
        
        url_land = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/landing"
        url_box = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
        url_pbp = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
        
        d_land = requests.get(url_land).json() if requests.get(url_land).status_code == 200 else {}
        d_box = requests.get(url_box).json() if requests.get(url_box).status_code == 200 else {}
        d_pbp = requests.get(url_pbp).json() if requests.get(url_pbp).status_code == 200 else {}

        home_id = d_land.get("homeTeam", {}).get("id")
        away_id = d_land.get("awayTeam", {}).get("id")

        speles_dati = {
            "datums": VAKAR, "game_id": game_id,
            "home_team": home_team, "away_team": away_team,
            "home_total": d_land.get("homeTeam", {}).get("score", 0),
            "away_total": d_land.get("awayTeam", {}).get("score", 0),
            "home_p1": 0, "away_p1": 0, "home_p2": 0, "away_p2": 0, "home_p3": 0, "away_p3": 0, "home_ot": 0, "away_ot": 0,
            "home_pim_total": 0, "away_pim_total": 0,
            "home_pim_p1": 0, "away_pim_p1": 0, "home_pim_p2": 0, "away_pim_p2": 0, "home_pim_p3": 0, "away_pim_p3": 0, "home_pim_ot": 0, "away_pim_ot": 0,
            "home_sog_total": d_land.get("homeTeam", {}).get("sog", 0),
            "away_sog_total": d_land.get("awayTeam", {}).get("sog", 0),
            "home_sog_p1": 0, "away_sog_p1": 0, "home_sog_p2": 0, "away_sog_p2": 0, "home_sog_p3": 0, "away_sog_p3": 0, "home_sog_ot": 0, "away_sog_ot": 0,
            "home_ppg": 0, "away_ppg": 0, 
            "home_pp_sog": 0, "away_pp_sog": 0
        }

        # 1. VĀRTI & PPG
        scoring_data = d_land.get("summary", {}).get("scoring", [])
        for period_data in scoring_data:
            p_num = period_data.get("periodDescriptor", {}).get("number")
            for goal in period_data.get("goals", []):
                kom_dict = goal.get("teamAbbrev", {})
                kom = kom_dict.get("default") if isinstance(kom_dict, dict) else goal.get("teamAbbrev")
                
                if p_num in [1, 2, 3]:
                    if kom == home_team: speles_dati[f"home_p{p_num}"] += 1
                    elif kom == away_team: speles_dati[f"away_p{p_num}"] += 1
                elif p_num > 3:
                    if kom == home_team: speles_dati["home_ot"] += 1
                    elif kom == away_team: speles_dati["away_ot"] += 1
                    
                if goal.get("strength") == "pp":
                    if kom == home_team: speles_dati["home_ppg"] += 1
                    elif kom == away_team: speles_dati["away_ppg"] += 1

        home_summa = speles_dati["home_p1"] + speles_dati["home_p2"] + speles_dati["home_p3"] + speles_dati["home_ot"]
        if speles_dati["home_total"] > home_summa: speles_dati["home_ot"] += (speles_dati["home_total"] - home_summa)
            
        away_summa = speles_dati["away_p1"] + speles_dati["away_p2"] + speles_dati["away_p3"] + speles_dati["away_ot"]
        if speles_dati["away_total"] > away_summa: speles_dati["away_ot"] += (speles_dati["away_total"] - away_summa)

        # 2. NORAIDĪJUMI
        penalties_data = d_land.get("summary", {}).get("penalties", [])
        for p_data in penalties_data:
            p_num = p_data.get("periodDescriptor", {}).get("number")
            for pen in p_data.get("penalties", []):
                kom_dict = pen.get("teamAbbrev", {})
                kom = kom_dict.get("default") if isinstance(kom_dict, dict) else pen.get("teamAbbrev")
                apraksts = str(pen.get("descKey", "")).lower()
                
                if "fight" in apraksts:
                    continue

                if kom == home_team:
                    speles_dati["home_pim_total"] += 1
                    if p_num in [1, 2, 3]: speles_dati[f"home_pim_p{p_num}"] += 1
                    elif p_num > 3: speles_dati["home_pim_ot"] += 1
                elif kom == away_team:
                    speles_dati["away_pim_total"] += 1
                    if p_num in [1, 2, 3]: speles_dati[f"away_pim_p{p_num}"] += 1
                    elif p_num > 3: speles_dati["away_pim_ot"] += 1

        # 3. METIENI PA PERIODIEM
        plays = d_pbp.get("plays", [])
        for play in plays:
            if play.get("typeDescKey") in ["shot-on-goal", "goal"]:
                p_num = play.get("periodDescriptor", {}).get("number")
                team_id = play.get("details", {}).get("eventOwnerTeamId")
                
                if team_id == home_id:
                    if p_num in [1, 2, 3]: speles_dati[f"home_sog_p{p_num}"] += 1
                    elif p_num > 3: speles_dati["home_sog_ot"] += 1
                elif team_id == away_id:
                    if p_num in [1, 2, 3]: speles_dati[f"away_sog_p{p_num}"] += 1
                    elif p_num > 3: speles_dati["away_sog_ot"] += 1

        # 4. VAIRĀKUMA METIENI PA VĀRTIEM (PP SOG)
        box_stats = d_box.get("playerByGameStats", {})
        
        for g in box_stats.get("homeTeam", {}).get("goalies", []):
            ppa = str(g.get("powerPlayShotsAgainst", "0/0")).split('/')
            if len(ppa) == 2: speles_dati["away_pp_sog"] += int(ppa[1])
            
        for g in box_stats.get("awayTeam", {}).get("goalies", []):
            ppa = str(g.get("powerPlayShotsAgainst", "0/0")).split('/')
            if len(ppa) == 2: speles_dati["home_pp_sog"] += int(ppa[1])

        saglabajamie_dati.append(speles_dati)

    if saglabajamie_dati:
        saglabat_csv(saglabajamie_dati)
        print(f"Veiksmīgi saglabātas {len(saglabajamie_dati)} spēles CSV failā.")

if __name__ == "__main__":
    main()
