import pandas as pd
import numpy as np

# Visas 32 NHL komandas oficiālie saīsinājumi
NHL_KOMANDAS_SARAKSTS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET", 
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT", 
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", 
    "WSH", "WPG"
]

def parbaudit_gatavibu(df):
    """
    Pārbauda, vai visām 32 komandām datubāzē ir vismaz 5 aizvadītas spēles.
    Atgriež: (gatavs: bool, aizvadījušas_komandas: int, kopā_komandas: int)
    """
    if df is None or df.empty:
        return False, 0, len(NHL_KOMANDAS_SARAKSTS)
    
    # Saskaitām, cik spēles katra komanda ir aizvadījusi vienotajā tabulā
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
    Šeit vēlāk atradīsies Puasona sadalījuma aprēķina kods, 
    kas ģenerēs prognozes rezultātam, over/under, noraidījumiem un periodiem.
    """
    # Pagaidu fiktīvi dati struktūras pārbaudei, kamēr modelis nav pilnībā uzrakstīts
    return {
        "rezultats": "3-2",
        "over_under": "Over 6.5",
        "noraidījumi": 8,
        "p1": "1-1",
        "p2": "1-1",
        "p3": "1-0"
    }
