import pandas as pd
import numpy as np
from scipy.stats import poisson

# Visas 32 NHL komandas
NHL_KOMANDAS_SARAKSTS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET", 
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT", 
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", 
    "WSH", "WPG"
]

def parbaudit_gatavibu(df):
    """
    Pārbauda, vai visām 32 komandām datubāzē ir vismaz 5 aizvadītas spēles.
    """
    if df is None or df.empty:
        return False, 0, len(NHL_KOMANDAS_SARAKSTS)
    
    spelu_skaits = df['komanda'].value_counts()
    gatavas_komandas = 0
    for komanda in NHL_KOMANDAS_SARAKSTS:
        if spelu_skaits.get(komanda, 0) >= 5:
            gatavas_komandas += 1
            
    kopā = len(NHL_KOMANDAS_SARAKSTS)
    ir_gatavs = (gatavas_komandas >= kopā)
    
    return ir_gatavs, gatavas_komandas, kopā

def aprekinat_prognozi_speles(home_team, away_team, df):
    """
    Aprēķina prognozi, izmantojot Puasona sadalījumu un sabalansētus rādītājus.
    """
    if df is None or df.empty:
        return None

    # Filtrējam datus attiecīgajām komandām
    home_df = df[df['komanda'] == home_team]
    away_df = df[df['komanda'] == away_team]
    
    # Mājas komandas mājas spēļu statistika (vai kopējā, ja maz spēļu)
    home_home_df = home_df[home_df['majas'] == 1]
    if len(home_home_df) >= 3:
        h_scored = home_home_df['g_reg'].tail(10).mean()
        h_conceded = home_home_df['z_reg'].tail(10).mean()
        h_pim = home_home_df['pim_count'].tail(10).mean()
    else:
        h_scored = home_df['g_reg'].tail(10).mean() if not home_df.empty else 3.0
        h_conceded = home_df['z_reg'].tail(10).mean() if not home_df.empty else 3.0
        h_pim = home_df['pim_count'].tail(10).mean() if not home_df.empty else 4.0

    # Izbraukuma komandas izbraukuma spēļu statistika
    away_away_df = away_df[away_df['majas'] == 0]
    if len(away_away_df) >= 3:
        a_scored = away_away_df['g_reg'].tail(10).mean()
        a_conceded = away_away_df['z_reg'].tail(10).mean()
        a_pim = away_away_df['pim_count'].tail(10).mean()
    else:
        a_scored = away_df['g_reg'].tail(10).mean() if not away_df.empty else 2.8
        a_conceded = away_df['z_reg'].tail(10).mean() if not away_df.empty else 3.1
        a_pim = away_df['pim_count'].tail(10).mean() if not away_df.empty else 4.0

    # Līgas vidējie rādītāji drošības buferim (League Prior)
    league_avg_goals = df['g_reg'].mean() if not df.empty else 3.0
    league_avg_pim = df['pim_count'].mean() if not df.empty else 4.0

    # Sabalansētie sagaidāmie vārti (xG) ar prior koeficientu pret galējībām
    lambda_home = max(1.0, (h_scored + a_conceded) / 2 * 0.7 + league_avg_goals * 0.3)
    lambda_away = max(1.0, (a_scored + h_conceded) / 2 * 0.7 + league_avg_goals * 0.3)

    # Puasona matrica vārtu varbūtībām (līdz 10 vārtiem)
    max_goals = 10
    home_probs = [poisson.pmf(i, lambda_home) for i in range(max_goals)]
    away_probs = [poisson.pmf(j, lambda_away) for j in range(max_goals)]

    best_home_g, best_away_g, max_prob = 0, 0, -1
    for h_g in range(max_goals):
        for a_g in range(max_goals):
            prob = home_probs[h_g] * away_probs[a_g]
            if prob > max_prob:
                max_prob = prob
                best_home_g = h_g
                best_away_g = a_g

    # Kopējais vārtu skaits un Over/Under 6.5
    total_xg = lambda_home + lambda_away
    ou_type = "Over 6.5" if total_xg > 6.5 else "Under 6.5"

    # Noraidījumu prognoze
    expected_pim = max(2.0, (h_pim + a_pim) / 2 * 2)
    pim_type = "Over 5.5" if expected_pim > 5.5 else "Under 5.5"

    # Periodu sadalījums (standarta hokeja proporcijas: 1P ~30%, 2P ~35%, 3P ~35%)
    p1_goals = round(total_xg * 0.3, 1)
    p2_goals = round(total_xg * 0.35, 1)
    p3_goals = round(total_xg * 0.35, 1)

    return {
        "rezultats": f"{best_home_g}-{best_away_g}",
        "over_under": ou_type,
        "noraidījumi": f"{round(expected_pim)} ({pim_type})",
        "p1": f"Vidēji {p1_goals} vārti",
        "p2": f"Vidēji {p2_goals} vārti",
        "p3": f"Vidēji {p3_goals} vārti"
    }
