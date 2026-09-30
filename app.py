import pandas as pd
import streamlit as st
import os
from datetime import datetime

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
def ielasit_datus():
    try:
        if not os.path.exists(CSV_FAILS):
            return None
        df = pd.read_csv(CSV_FAILS)
        if 'datums' in df.columns:
            df['datums'] = pd.to_datetime(df['datums'])
            df = df.sort_values('datums')
        return df
    except Exception:
        return None

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

st.set_page_config(page_title="NHL Analītiskais Terminālis", layout="wide")

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

raw_df = ielasit_datus()
if raw_df is None:
    st.error("CSV fails ('nhl_sezona.csv') nav atrasts!")
    st.stop()

df = sagatavot_vienoto_tabulu(raw_df)

if 'rezims' not in st.session_state:
    st.session_state.rezims = "1. Periods"

st.sidebar.markdown("### Sadaļas")
if st.sidebar.button("1. Periods", use_container_width=True): st.session_state.rezims = "1. Periods"
if st.sidebar.button("2. Periods", use_container_width=True): st.session_state.rezims = "2. Periods"
if st.sidebar.button("3. Periods", use_container_width=True): st.session_state.rezims = "3. Periods"
if st.sidebar.button("Forma un Vārti", use_container_width=True): st.session_state.rezims = "Forma un Vārti"
if st.sidebar.button("Over / Under", use_container_width=True): st.session_state.rezims = "Over / Under"
if st.sidebar.button("Powerplay", use_container_width=True): st.session_state.rezims = "Powerplay"
if st.sidebar.button("Noraidījumi", use_container_width=True): st.session_state.rezims = "Noraidījumi"
st.sidebar.markdown("---")
if st.sidebar.button("Komandas Statistika", use_container_width=True): st.session_state.rezims = "Komandas Statistika"
if st.sidebar.button("Kalendārs", use_container_width=True): st.session_state.rezims = "Kalendārs"

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

# 1. PERIODS
if rezims == "1. Periods":
    st.subheader("⏱️ 1. Perioda Statistika")
    filtrs = st.selectbox("Izvēlies skatu:", [
        "1. perioda vārtu starpība (Visas spēles)", 
        "1. perioda vārtu starpība (Mājas spēles)", 
        "1. perioda vārtu starpība (Izbraukuma spēles)",
        "1. perioda vārtu starpība pēdējajās 10 spēlēs (Visas)",
        "1. perioda vārtu starpība pēdējajās 10 spēlēs (Mājās)",
        "1. perioda vārtu starpība pēdējajās 10 spēlēs (Izbraukumā)",
        "1. perioda vidējie metieni (SOG)"
    ])
    
    if "pēdējajās 10 spēlēs" in filtrs:
        sub = df
        if "Mājās" in filtrs: sub = sub[sub['majas'] == 1]
        elif "Izbraukumā" in filtrs: sub = sub[sub['majas'] == 0]
        res = sub.groupby('komanda').tail(10).groupby('komanda')['diff_p1'].sum().reset_index()
        res.columns = ['komanda', '1.P Vārtu Starpība (pēd. 10)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='1.P Vārtu Starpība (pēd. 10)', ascending=False)), use_container_width=True, hide_index=True)
    elif "Visas" in filtrs:
        res = df.groupby('komanda')['diff_p1'].sum().reset_index()
        res.columns = ['komanda', '1. perioda vārtu starpība']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='1. perioda vārtu starpība', ascending=False)), use_container_width=True, hide_index=True)
    elif "Mājas" in filtrs:
        sub = df[df['majas'] == 1]
        res = sub.groupby('komanda')['diff_p1'].sum().reset_index()
        res.columns = ['komanda', '1. perioda vārtu starpība (Mājās)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='1. perioda vārtu starpība (Mājās)', ascending=False)), use_container_width=True, hide_index=True)
    elif "Izbraukuma" in filtrs:
        sub = df[df['majas'] == 0]
        res = sub.groupby('komanda')['diff_p1'].sum().reset_index()
        res.columns = ['komanda', '1. perioda vārtu starpība (Izbraukumā)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='1. perioda vārtu starpība (Izbraukumā)', ascending=False)), use_container_width=True, hide_index=True)
    else:
        res = df.groupby('komanda')['sog_p1'].mean().reset_index()
        res.columns = ['komanda', '1. perioda vidējie metieni (SOG)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='1. perioda vidējie metieni (SOG)', ascending=False)), use_container_width=True, hide_index=True)

# 2. PERIODS
elif rezims == "2. Periods":
    st.subheader("⏱️ 2. Perioda Statistika")
    filtrs = st.selectbox("Izvēlies skatu:", [
        "2. perioda vārtu starpība (Visas spēles)",
        "2. perioda vārtu starpība (Mājas spēles)",
        "2. perioda vārtu starpība (Izbraukuma spēles)",
        "2. perioda vārtu starpība pēdējajās 10 spēlēs (Visas)",
        "2. perioda vārtu starpība pēdējajās 10 spēlēs (Mājās)",
        "2. perioda vārtu starpība pēdējajās 10 spēlēs (Izbraukumā)",
        "2. perioda vidējie metieni (SOG)"
    ])
    if "pēdējajās 10 spēlēs" in filtrs:
        sub = df
        if "Mājās" in filtrs: sub = sub[sub['majas'] == 1]
        elif "Izbraukumā" in filtrs: sub = sub[sub['majas'] == 0]
        res = sub.groupby('komanda').tail(10).groupby('komanda')['diff_p2'].sum().reset_index()
        res.columns = ['komanda', '2.P Vārtu Starpība (pēd. 10)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='2.P Vārtu Starpība (pēd. 10)', ascending=False)), use_container_width=True, hide_index=True)
    elif "Visas" in filtrs:
        res = df.groupby('komanda')['diff_p2'].sum().reset_index()
        res.columns = ['komanda', '2. perioda vārtu starpība']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='2. perioda vārtu starpība', ascending=False)), use_container_width=True, hide_index=True)
    elif "Mājas" in filtrs:
        sub = df[df['majas'] == 1]
        res = sub.groupby('komanda')['diff_p2'].sum().reset_index()
        res.columns = ['komanda', '2. perioda vārtu starpība (Mājās)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='2. perioda vārtu starpība (Mājās)', ascending=False)), use_container_width=True, hide_index=True)
    elif "Izbraukuma" in filtrs:
        sub = df[df['majas'] == 0]
        res = sub.groupby('komanda')['diff_p2'].sum().reset_index()
        res.columns = ['komanda', '2. perioda vārtu starpība (Izbraukumā)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='2. perioda vārtu starpība (Izbraukumā)', ascending=False)), use_container_width=True, hide_index=True)
    else:
        res = df.groupby('komanda')['sog_p2'].mean().reset_index()
        res.columns = ['komanda', '2. perioda vidējie metieni (SOG)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='2. perioda vidējie metieni (SOG)', ascending=False)), use_container_width=True, hide_index=True)

# 3. PERIODS
elif rezims == "3. Periods":
    st.subheader("⏱️️ 3. Perioda Statistika")
    filtrs = st.selectbox("Izvēlies skatu:", [
        "3. perioda vārtu starpība (Visas spēles)",
        "3. perioda vārtu starpība (Mājas spēles)",
        "3. perioda vārtu starpība (Izbraukuma spēles)",
        "3. perioda vārtu starpība pēdējajās 10 spēlēs (Visas)",
        "3. perioda vārtu starpība pēdējajās 10 spēlēs (Mājās)",
        "3. perioda vārtu starpība pēdējajās 10 spēlēs (Izbraukumā)",
        "3. perioda vidējie metieni (SOG)"
    ])
    if "pēdējajās 10 spēlēs" in filtrs:
        sub = df
        if "Mājās" in filtrs: sub = sub[sub['majas'] == 1]
        elif "Izbraukumā" in filtrs: sub = sub[sub['majas'] == 0]
        res = sub.groupby('komanda').tail(10).groupby('komanda')['diff_p3'].sum().reset_index()
        res.columns = ['komanda', '3.P Vārtu Starpība (pēd. 10)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='3.P Vārtu Starpība (pēd. 10)', ascending=False)), use_container_width=True, hide_index=True)
    elif "Visas" in filtrs:
        res = df.groupby('komanda')['diff_p3'].sum().reset_index()
        res.columns = ['komanda', '3. perioda vārtu starpība']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='3. perioda vārtu starpība', ascending=False)), use_container_width=True, hide_index=True)
    elif "Mājas" in filtrs:
        sub = df[df['majas'] == 1]
        res = sub.groupby('komanda')['diff_p3'].sum().reset_index()
        res.columns = ['komanda', '3. perioda vārtu starpība (Mājās)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='3. perioda vārtu starpība (Mājās)', ascending=False)), use_container_width=True, hide_index=True)
    elif "Izbraukuma" in filtrs:
        sub = df[df['majas'] == 0]
        res = sub.groupby('komanda')['diff_p3'].sum().reset_index()
        res.columns = ['komanda', '3. perioda vārtu starpība (Izbraukumā)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='3. perioda vārtu starpība (Izbraukumā)', ascending=False)), use_container_width=True, hide_index=True)
    else:
        res = df.groupby('komanda')['sog_p3'].mean().reset_index()
        res.columns = ['komanda', '3. perioda vidējie metieni (SOG)']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='3. perioda vidējie metieni (SOG)', ascending=False)), use_container_width=True, hide_index=True)

# FORMA UN VĀRTI
elif rezims == "Forma un Vārti":
    st.subheader("🔥 Komandu Forma un Vārtu Guvumi")
    filtrs = st.selectbox("Izvēlies skatu:", [
        "Karstākās komandas (pēd. 5 spēlēs)",
        "Karstākās komandas (pēd. 10 spēlēs)",
        "Aukstākās komandas (pēd. 5 spēlēs)",
        "Aukstākās komandas (pēd. 10 spēlēs)",
        "Visvairāk iemet (pēd. 5 spēlēs)",
        "Visvairāk ielaiž (pēd. 5 spēlēs)"
    ])
    
    if "Karstākās" in filtrs:
        n = 10 if "10" in filtrs else 5
        res = df.groupby('komanda').tail(n).groupby('komanda')['g_reg'].sum().reset_index()
        res.columns = ['komanda', f'Gūtie vārti pēd. {n} spēlēs']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by=res.columns[1], ascending=False)), use_container_width=True, hide_index=True)
    elif "Aukstākās" in filtrs:
        n = 10 if "10" in filtrs else 5
        res = df.groupby('komanda').tail(n).groupby('komanda')['g_reg'].sum().reset_index()
        res.columns = ['komanda', f'Gūtie vārti pēd. {n} spēlēs']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by=res.columns[1], ascending=True)), use_container_width=True, hide_index=True)
    elif "Visvairāk iemet" in filtrs:
        res = df.groupby('komanda').apply(lambda g: g.tail(5)['g_reg'].sum()).reset_index(name='Vārtu skaits')
        res.columns = ['komanda', 'Gūtie vārti pēd. 5 spēlēs']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='Gūtie vārti pēd. 5 spēlēs', ascending=False)), use_container_width=True, hide_index=True)
    elif "Visvairāk ielaiž" in filtrs:
        res = df.groupby('komanda').apply(lambda g: g.tail(5)['z_reg'].sum()).reset_index(name='Vārtu skaits')
        res.columns = ['komanda', 'Ielaistie vārti pēd. 5 spēlēs']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='Ielaistie vārti pēd. 5 spēlēs', ascending=False)), use_container_width=True, hide_index=True)

# POWERPLAY
elif rezims == "Powerplay":
    st.subheader("⚡ Vairākuma (Powerplay) Līderi")
    filtrs = st.selectbox("Izvēlies skatu:", [
        "Vairākuma vārtu līderi (Visas spēles)",
        "Vairākuma vārtu līderi (Mājās - pēd. 5)",
        "Vairākuma vārtu līderi (Mājās - pēd. 10)",
        "Vairākuma vārtu līderi (Izbraukumā - pēd. 5)",
        "Vairākuma vārtu līderi (Izbraukumā - pēd. 10)"
    ])
    
    sub = df
    if "Mājās" in filtrs: sub = df[df['majas'] == 1]
    elif "Izbraukumā" in filtrs: sub = df[df['majas'] == 0]
    
    if "5" in filtrs:
        res = sub.groupby('komanda').tail(5).groupby('komanda')['ppg'].sum().reset_index()
    elif "10" in filtrs:
        res = sub.groupby('komanda').tail(10).groupby('komanda')['ppg'].sum().reset_index()
    else:
        res = sub.groupby('komanda')['ppg'].sum().reset_index()
        
    res.columns = ['komanda', 'Vairākumā gūtie vārti']
    st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='Vairākumā gūtie vārti', ascending=False)), use_container_width=True, hide_index=True)

# OVER / UNDER
elif rezims == "Over / Under":
    st.subheader("📈 Spēļu Kopējā Vārtu Summa (Over / Under 6.5)")
    filtrs = st.selectbox("Izvēlies skatu:", [
        "Over 6.5 (Visas - pēd. 5)",
        "Over 6.5 (Visas - pēd. 10)",
        "Over 6.5 (Mājās - pēd. 10)",
        "Over 6.5 (Izbraukumā - pēd. 10)",
        "Under 6.5 (Visas - pēd. 5)",
        "Under 6.5 (Visas - pēd. 10)",
        "Under 6.5 (Mājās - pēd. 10)",
        "Under 6.5 (Izbraukumā - pēd. 10)"
    ])
    
    n = 10 if "10" in filtrs else 5
    is_over = "Over" in filtrs
    
    sub = df
    if "Mājās" in filtrs: sub = df[df['majas'] == 1]
    elif "Izbraukumā" in filtrs: sub = df[df['majas'] == 0]
    
    def calc_ou(group):
        tail_group = group.tail(n)
        return (tail_group['tot_reg_goals'] > 6.5).sum() if is_over else (tail_group['tot_reg_goals'] < 6.5).sum()
        
    res = sub.groupby('komanda').apply(calc_ou).reset_index(name='Spēļu skaits')
    res.columns = ['komanda', 'Atbilstošo spēļu skaits']
    st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='Atbilstošo spēļu skaits', ascending=False)), use_container_width=True, hide_index=True)

# NORAIDĪJUMI
elif rezims == "Noraidījumi":
    st.subheader("❌ Noraidījumu (PIM) Līderi")
    filtrs = st.selectbox("Izvēlies skatu:", [
        "Kopējie noraidījumi (Visas spēles)",
        "Vidējie noraidījumi mājās (PIM H)",
        "Vidējie noraidījumi izbraukumā (PIM A)"
    ])
    
    if "Visas" in filtrs:
        res = df.groupby('komanda').agg(Kopā=('pim_count', 'sum'), Vidēji=('pim_count', 'mean')).reset_index()
        res['Rādītājs'] = res.apply(lambda r: f"{int(r['Kopā'])} (vid. {r['Vidēji']:.1f})", axis=1)
        res = res[['komanda', 'Rādītājs', 'Kopā']].sort_values(by='Kopā', ascending=False)
        res.columns = ['komanda', 'Noraidījumi (Kopā un vidēji)', '_sort']
        res = res.drop(columns=['_sort'])
        st.dataframe(sagatavot_tabulu_izvadei(res), use_container_width=True, hide_index=True)
    else:
        is_home = 1 if "mājās" in filtrs else 0
        sub = df[df['majas'] == is_home]
        res = sub.groupby('komanda')['pim_count'].mean().reset_index()
        res.columns = ['komanda', 'Vidējais noraidījumu skaits']
        st.dataframe(sagatavot_tabulu_izvadei(res.sort_values(by='Vidējais noraidījumu skaits', ascending=False)), use_container_width=True, hide_index=True)

# KOMANDAS STATISTIKA
elif rezims == "Komandas Statistika":
    st.subheader("📊 Komandas Analīze")
    
    selected_team = st.selectbox("Izvēlies komandu:", sorted(list(NHL_KOMANDAS.keys())), format_func=lambda x: f"{x} - {NHL_KOMANDAS[x]}")
    
    parametru_opcijas = {
        "Kopējā statistika un nākamās spēles": "stats",
        "Mājas spēļu vidējie rādītāji": "h",
        "Izbraukuma spēļu vidējie rādītāji": "a",
        "Pēdējo 5 spēļu statistika (Visas)": "last5",
        "Pēdējo 5 mājas spēļu statistika": "last5h",
        "Pēdējo 5 izbraukuma spēļu statistika": "last5a",
        "Noraidījumu vēsture pēdējajās 5 spēlēs": "pimlast5"
    }
    
    stat_izvele = st.selectbox("Izvēlies parametru:", list(parametru_opcijas.keys()))
    mode_key = parametru_opcijas[stat_izvele]
    
    team_df = df[df['komanda'] == selected_team]
    pilns_n = pilns_nosaukums(selected_team)
    
    if team_df.empty:
        st.warning("Šai komandai nav datu bāzē.")
    else:
        st.markdown(f"### Komanda: {pilns_n} ({selected_team})")
        
        if mode_key == 'stats':
            total_games = len(team_df)
            home_df = team_df[team_df['majas'] == 1]
            away_df = team_df[team_df['majas'] == 0]
            
            st.metric("Apskatītās spēles", total_games)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Vidēji vārti:** {team_df['g_reg'].mean():.2f}")
                st.write(f"Mājās: {home_df['g_reg'].mean():.2f} | Izbr: {away_df['g_reg'].mean():.2f}")
            with col2:
                st.write(f"**Vairākuma vārti:** {team_df['ppg'].mean():.2f}")
                st.write(f"Mājās: {home_df['ppg'].mean():.2f} | Izbr: {away_df['ppg'].mean():.2f}")
            with col3:
                st.write(f"**Noraidījumi:** {team_df['pim_count'].mean():.1f}")
                st.write(f"Mājās: {home_df['pim_count'].mean():.1f} | Izbr: {away_df['pim_count'].mean():.1f}")
            
            if os.path.exists(CSV_KALENDARS):
                st.markdown("---")
                st.markdown("#### 📅 Turpmākās spēles:")
                df_k = pd.read_csv(CSV_KALENDARS)
                komandas_speles = df_k[(df_k['majas_komanda'] == selected_team) | (df_k['viesu_komanda'] == selected_team)]
                sodiena_str = datetime.now().strftime('%Y-%m-%d')
                nakotnes_speles = komandas_speles[komandas_speles['datums'] >= sodiena_str].head(5)
                
                if not nakotnes_speles.empty:
                    for _, r in nakotnes_speles.iterrows():
                        is_home = r['majas_komanda'] == selected_team
                        H_vai_A = "Mājās" if is_home else "Izbraukumā"
                        pretinieka_kods = r['viesu_komanda'] if is_home else r['majas_komanda']
                        pretinieka_viss = pilns_nosaukums(pretinieka_kods)
                        st.text(f"• {r['datums']} vs {pretinieka_viss} ({pretinieka_kods}) [{H_vai_A}]")
                else:
                    st.info("Kalendārā nav atrastu nākamo spēļu.")

        elif mode_key in ['h', 'a']:
            is_home = 1 if mode_key == 'h' else 0
            sub_df = team_df[team_df['majas'] == is_home]
            st.write(f"**Apskatīto spēļu skaits:** {len(sub_df)}")
            st.write(f"**Vidēji iemestie vārti:** {sub_df['g_reg'].mean():.2f}")
            st.write(f"**Vidēji ielaistie vārti:** {sub_df['z_reg'].mean():.2f}")
            st.write(f"**Vidējās soda minūtes (PIM):** {sub_df['pim_tot'].mean():.2f}")

        elif mode_key == 'last5':
            sub_5 = team_df.tail(5)
            st.write(f"**Vārtu guvumi (vidēji):** {sub_5['g_reg'].mean():.2f}")
            st.write(f"**Ielaistie vārti (vidēji):** {sub_5['z_reg'].mean():.2f}")
            st.write(f"**Vairākumā iemestie vārti (vidēji):** {sub_5['ppg'].mean():.2f}")
            if 'ppg_allowed' in sub_5.columns:
                st.write(f"**Vairākumā ielaistie vārti (vidēji):** {sub_5['ppg_allowed'].mean():.2f}")
            st.write(f"**Noraidījumi (vidēji):** {sub_5['pim_count'].mean():.1f} ({sub_5['pim_tot'].mean():.1f} minūtes)")

        elif mode_key in ['last5h', 'last5a']:
            is_home = 1 if mode_key == 'last5h' else 0
            sub_5 = team_df[team_df['majas'] == is_home].tail(5)
            loc_text = "mājas" if is_home else "izbraukuma"
            
            if sub_5.empty:
                st.info(f"Nav atrastas {loc_text} spēles šai komandai.")
            else:
                st.write(f"**Vārtu guvumi (vidēji):** {sub_5['g_reg'].mean():.2f}")
                st.write(f"**Ielaistie vārti (vidēji):** {sub_5['z_reg'].mean():.2f}")
                st.write(f"**Vairākumā iemestie vārti (vidēji):** {sub_5['ppg'].mean():.2f}")
                if 'ppg_allowed' in sub_5.columns:
                    st.write(f"**Vairākumā ielaistie vārti (vidēji):** {sub_5['ppg_allowed'].mean():.2f}")
                st.write(f"**Noraidījumi (vidēji):** {sub_5['pim_count'].mean():.1f} ({sub_5['pim_tot'].mean():.1f} minūtes)")

        elif mode_key == 'pimlast5':
            sub_df = team_df.tail(5)
            for _, r in sub_df.iterrows():
                viesi_majas = "Mājās" if r['majas'] == 1 else "Izbraukumā"
                d_str = pd.to_datetime(r['datums']).strftime('%Y-%m-%d')
                pret_viss = pilns_nosaukums(r['pretinieks'])
                st.text(f"• {d_str} vs {pret_viss} ({r['pretinieks']}) [{viesi_majas}] — {int(r['pim_count'])} noraidījumi ({int(r['pim_tot'])} min)")

# KALENDĀRS
elif rezims == "Kalendārs":
    st.subheader("📅 Tuvāko 3 dienu spēļu grafiks")
    if not os.path.exists(CSV_KALENDARS):
        st.warning("Kalendāra fails 'nhl_kalendars.csv' nav atrasts.")
    else:
        try:
            df_k = pd.read_csv(CSV_KALENDARS)
            sodiena = datetime.now().date()
            beigu_diena = sodiena + pd.Timedelta(days=3)
            df_k['datums_dt'] = pd.to_datetime(df_k['datums']).dt.date
            tuvakas_speles = df_k[(df_k['datums_dt'] >= sodiena) & (df_k['datums_dt'] < beigu_diena)]
            
            if tuvakas_speles.empty:
                st.info("Tuvākajās 3 dienās nav paredzētu spēļu.")
            else:
                dienu_tulkojums = {'Monday': 'Pirmdiena', 'Tuesday': 'Otrdiena', 'Wednesday': 'Trešdiena', 'Thursday': 'Ceturtdiena', 'Friday': 'Piektdiena', 'Saturday': 'Sestdiena', 'Sunday': 'Svētdiena'}
                for datums, grupa in tuvakas_speles.groupby('datums'):
                    dt_obj = datetime.strptime(datums, '%Y-%m-%d')
                    diena_lv = dienu_tulkojums.get(dt_obj.strftime('%A'), dt_obj.strftime('%A'))
                    st.markdown(f"**📌 Datums: {datums} ({diena_lv})**")
                    for _, r in grupa.iterrows():
                        viesis = pilns_nosaukums(r['viesu_komanda'])
                        majas = pilns_nosaukums(r['majas_komanda'])
                        st.text(f"    • {viesis} ({r['viesu_komanda']}) @ {majas} ({r['majas_komanda']})")
                    st.divider()
        except Exception as e:
            st.error(f"Kļūda nolasot kalendāru: {e}")
