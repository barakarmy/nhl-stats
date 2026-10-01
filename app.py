import pandas as pd
import streamlit as st
import os
from datetime import datetime
import modelis  # Importējam mūsu prognožu modeli

st.set_page_config(page_title="NHL Analītiskais Terminālis", layout="wide")

CSV_FAILS = "nhl_sezona.csv"
CSV_KALENDARS = "nhl_kalendars.csv"

NHL_KOMANDAS = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes", "CHI": "Chicago Blackhawks",
    "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montreal Canadiens",
    "NSH": "Nashville Predators", "NJD": "New Jersey Devils", "NYI": "New York Islanders",
    "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks", "SEA": "Seattle Kraken",
    "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Hockey Club", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
    "WSH": "Washington Capitals", "WPG": "Winnipeg Jets"
}

def pilns_nosaukums(saisinajums):
    return NHL_KOMANDAS.get(saisinajums.upper(), saisinajums.upper())

@st.cache_data
def ielasit_datus(file_mtime):
    try:
        if not os.path.exists(CSV_FAILS):
            return None
        df = pd.read_csv(CSV_FAILS)
        if 'datums' in df.columns:
            df['datums'] = pd.to_datetime(df['datums']) + pd.Timedelta(days=1)
            df = df.sort_values('datums')
        return df
    except Exception:
        return None

def iegut_datus():
    mtime = os.path.getmtime(CSV_FAILS) if os.path.exists(CSV_FAILS) else 0
    return ielasit_datus(mtime)

def sagatavot_vienoto_tabulu(df):
    if df is None or df.empty:
        return pd.DataFrame()

    h = df[['datums', 'game_id', 'home_team', 'away_team', 
            'home_p1', 'away_p1', 'home_sog_p1', 'home_pim_p1',
            'home_p2', 'away_p2', 'home_sog_p2', 'home_pim_p2',
            'home_p3', 'away_p3', 'home_sog_p3', 'home_pim_p3',
            'home_ppg', 'home_pim_total']].copy()
    
    h.columns = ['datums', 'game_id', 'komanda', 'pretinieks', 
                 'g_p1', 'z_p1', 'sog_p1', 'pim_p1',
                 'g_p2', 'z_p2', 'sog_p2', 'pim_p2',
                 'g_p3', 'z_p3', 'sog_p3', 'pim_p3',
                 'ppg', 'pim_tot']
    h['majas'] = 1

    a = df[['datums', 'game_id', 'away_team', 'home_team', 
            'away_p1', 'home_p1', 'away_sog_p1', 'away_pim_p1',
            'away_p2', 'home_p2', 'away_sog_p2', 'away_pim_p2',
            'away_p3', 'home_p3', 'away_sog_p3', 'away_pim_p3',
            'away_ppg', 'away_pim_total']].copy()
    
    a.columns = ['datums', 'game_id', 'komanda', 'pretinieks', 
                 'g_p1', 'z_p1', 'sog_p1', 'pim_p1',
                 'g_p2', 'z_p2', 'sog_p2', 'pim_p2',
                 'g_p3', 'z_p3', 'sog_p3', 'pim_p3',
                 'ppg', 'pim_tot']
    a['majas'] = 0

    combined = pd.concat([h, a]).sort_values(['komanda', 'datums'])
    
    combined['diff_p1'] = combined['g_p1'] - combined['z_p1']
    combined['diff_p2'] = combined['g_p2'] - combined['z_p2']
    combined['diff_p3'] = combined['g_p3'] - combined['z_p3']
    
    combined['g_reg'] = combined['g_p1'] + combined['g_p2'] + combined['g_p3']
    combined['z_reg'] = combined['z_p1'] + combined['z_p2'] + combined['z_p3']
    combined['tot_reg_goals'] = combined['g_reg'] + combined['z_reg']
    
    combined['sog_reg'] = combined['sog_p1'] + combined['sog_p2'] + combined['sog_p3']
    combined['pim_reg'] = combined['pim_p1'] + combined['pim_p2'] + combined['pim_p3']
    combined['pim_count'] = (combined['pim_tot'] / 2).round().astype(int)

    team_game_ppg = combined[['game_id', 'komanda', 'ppg']].rename(columns={'komanda': 'pretinieks', 'ppg': 'ppg_allowed'})
    combined = pd.merge(combined, team_game_ppg, on=['game_id', 'pretinieks'], how='left')
    combined['pilns_nosaukums'] = combined['komanda'].apply(pilns_nosaukums)

    return combined

# CSS stils sānjoslas pogām
st.markdown("""
    <style>
    div[data-testid="stSidebar"] button {
        border: none !important;
        background-color: transparent !important;
        text-align: left !important;
        padding: 5px 15px !important;
        font-size: 16px !important;
        font-weight: 500 !important;
        color: inherit !important;
        justify-content: flex-start !important;
    }
    div[data-testid="stSidebar"] button:hover {
        background-color: rgba(150, 150, 150, 0.1) !important;
        color: #ff4b4b !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏒 NHL Analītiskais Panelis")

raw_df = iegut_datus()
if raw_df is None:
    st.error("CSV fails ('nhl_sezona.csv') nav atrasts!")
    st.stop()

df = sagatavot_vienoto_tabulu(raw_df)

if 'rezims' not in st.session_state:
    st.session_state.rezims = "Prognozes"

# --- SĀNJOSLAS NAVIGĀCIJA ---
st.sidebar.markdown("### 🏠 Sākumlapa")
if st.sidebar.button("🎯 Prognozes", width='stretch'): st.session_state.rezims = "Prognozes"

st.sidebar.markdown("---")
st.sidebar.markdown("### Datu Filtri")
if st.sidebar.button("1. Periods", width='stretch'): st.session_state.rezims = "1. Periods"
if st.sidebar.button("2. Periods", width='stretch'): st.session_state.rezims = "2. Periods"
if st.sidebar.button("3. Periods", width='stretch'): st.session_state.rezims = "3. Periods"
if st.sidebar.button("Forma un Vārti", width='stretch'): st.session_state.rezims = "Forma un Vārti"
if st.sidebar.button("Over / Under", width='stretch'): st.session_state.rezims = "Over / Under"
if st.sidebar.button("Powerplay", width='stretch'): st.session_state.rezims = "Powerplay"
if st.sidebar.button("Noraidījumi", width='stretch'): st.session_state.rezims = "Noraidījumi"

st.sidebar.markdown("---")
st.sidebar.markdown("### Komandas un Spēles")
if st.sidebar.button("Komandas Statistika", width='stretch'): st.session_state.rezims = "Komandas Statistika"
if st.sidebar.button("Kalendārs", width='stretch'): st.session_state.rezims = "Kalendārs"
if st.sidebar.button("Rezultāti", width='stretch'): st.session_state.rezims = "Rezultāti"

rezims = st.session_state.rezims

def sagatavot_tabulu_izvadei(res_df):
    res_df = res_df.copy()
    if 'komanda' in res_df.columns:
        res_df['Komanda'] = res_df['komanda'].apply(pilns_nosaukums)
        res_df = res_df.drop(columns=['komanda'])
    
    res_df = res_df.reset_index(drop=True)
    res_df.insert(0, 'Vieta', range(1, len(res_df) + 1))
    
    cols = ['Vieta', 'Komanda'] + [c for c in res_df.columns if c not in ['Vieta', 'Komanda']]
    return res_df[cols]

# === LAPU SATURS ===

if rezims == "Prognozes":
    st.subheader("🎯 Spēļu Prognozes")
    st.caption("ℹ️ Dati tiek atjaunināti automātiski katru rītu plkst. 10:00, bet prognožu modelis tiek izsaukts plkst. 11:00.")
    
    # Pārbaudām gatavību (vai visas komandas ir sasniegušas 5 spēļu slieksni)
    gatavs, gatavas_sk, kopa_sk = modelis.parbaudit_gatavibu(df)
    
    if not gatavs:
        st.warning(f"⏳ Sezonas ievads: Visas komandas vēl nav aizvadījušas vismaz 5 spēles.")
        st.progress(gatavas_sk / kopa_sk)
        st.info(f"Pašreizējais statuss: {gatavas_sk} no {kopa_sk} komandām ir sasniegušas 5 spēļu slieksni.")
    else:
        st.success("✅ Modelis ir pilnībā aktīvs! Tiek rēķinātas Puasona prognozes tuvākajām spēlēm.")
        
        # Šeit mēs vēlāk pieslēgsim kalendāru, kas ņem šodienas/tuvākās dienas spēles 
        # un katrai spēlei izsauc modelis.aprekinat_prognozi_speles(home, away, df)
        if os.path.exists(CSV_KALENDARS):
            df_k = pd.read_csv(CSV_KALENDARS)
            df_k['datums_dt'] = pd.to_datetime(df_k['datums']) + pd.Timedelta(days=1)
            sodiena_str = datetime.now().strftime('%Y-%m-%d')
            
            # Paņemam tuvākās dienas spēles
            tuvakas_speles = df_k[df_k['datums_dt'].dt.strftime('%Y-%m-%d') >= sodiena_str].head(5)
            
            if not tuvakas_speles.empty:
                st.markdown("#### 📅 Tuvākās dienas prognozes:")
                for _, r in tuvakas_speles.iterrows():
                    home = r['majas_komanda']
                    away = r['viesu_komanda']
                    
                    # Izsaucam Puasona modeli no modelis.py
                    prognoze = modelis.aprekinat_prognozi_speles(home, away, df)
                    
                    st.markdown(f"**{pilns_nosaukums(away)} ({away}) @ {pilns_nosaukums(home)} ({home})**")
                    if prognoze:
                        st.markdown(f"""
                        <div class='prognozes-bloks'>
                            • Rezultāts: <b>{prognoze['rezultats']}</b><br>
                            • Over/Under: <b>{prognoze['over_under']}</b><br>
                            • Noraidījumi: <b>{prognoze['noraidījumi']}</b><br>
                            • 1. periods: <b>{prognoze['p1']}</b><br>
                            • 2. periods: <b>{prognoze['p2']}</b><br>
                            • 3. periods: <b>{prognoze['p3']}</b>
                        </div>
                        """, unsafe_allow_html=True)
                    st.divider()
            else:
                st.info("Kalendārā nav atrastu nākamo spēļu.")
        else:
            st.warning("Nav atrasts 'nhl_kalendars.csv' fails.")

# (Pārējās lapas: 1. Periods, 2. Periods, 3. Periods, Forma un Vārti, Powerplay, Over / Under, Noraidījumi, Komandas Statistika, Kalendārs, Rezultāti paliek nemainīgas, bet bez vecā simulācijas bloka Rezultātu sadaļā)

elif rezims == "1. Periods":
    # ... (saglabājas viss iepriekšējais kods)
