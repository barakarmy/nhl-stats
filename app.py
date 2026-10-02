import hmac
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import datu_apstrade as da
import lokacijas
import modelis  # Puasona prognožu modelis

st.set_page_config(page_title="NHL analītika", page_icon=":material/sports_hockey:", layout="wide",
                   initial_sidebar_state="collapsed")


# ============================================================================
# PAROLE (ieteicams: Streamlit Cloud → Settings → Secrets → APP_PASSWORD = "...")
# ============================================================================
def _parole():
    try:
        return str(st.secrets["APP_PASSWORD"])
    except Exception:
        return "propredict"


def check_password():
    if st.session_state.get("password_correct"):
        return True

    def entered():
        ievade = str(st.session_state.get("password", ""))
        st.session_state["password_correct"] = hmac.compare_digest(ievade.encode(), _parole().encode())
        st.session_state.pop("password", None)

    st.text_input("Ievadi paroli:", type="password", on_change=entered, key="password")
    if st.session_state.get("password_correct") is False:
        st.error("Nepareiza parole")
    return False


if not check_password():
    st.stop()

# ============================================================================
# STILS
# ============================================================================
st.markdown("""<style>
/* ===== Fonti: virsraksti un sadaļu nosaukumi - Plus Jakarta Sans, teksts - Inter (Google Fonts; ja nav pieejams, tiek lietots sistēmas fonts) ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');
.stApp, .stApp p, .stApp li, .stApp label, .stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stCaptionContainer"] { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp [data-testid="stHeading"] *,
.stApp button[data-baseweb="tab"] p, .stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stExpander"] summary p,
.stApp [data-testid="stMetricLabel"] p {
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; letter-spacing: -0.01em; }
.stApp h1 { font-weight: 800; font-size: 2.05rem; letter-spacing: -0.03em; margin: .2rem 0 .8rem 0; }
.stApp h2, .stApp h3 { font-weight: 700; letter-spacing: -0.02em; }
.stApp h5 { font-weight: 700; }
.stApp [data-testid="stWidgetLabel"] p { font-weight: 600; font-size: .8rem; opacity: .85; }
.stApp button[data-baseweb="tab"] p { font-weight: 600; }

/* ===== Vispārējais izskats ===== */
header[data-testid="stHeader"] { display: none; }
.stApp .stMainBlockContainer, .stApp [data-testid="stMainBlockContainer"] { padding-top: 1rem; max-width: 1500px; }
.stApp [data-testid="stMetric"], .stApp [data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
.stApp [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
.stApp [data-testid="stSegmentedControl"] button, .stApp button[kind="secondary"] { border-radius: 10px; }
.stApp [data-testid="stExpander"] { border-radius: 12px; }

/* ===== Augšējā josla ar hover izvēlnēm ===== */
.st-key-topbar { position: sticky; top: .6rem; z-index: 1000; display: flex !important; flex-direction: row !important;
  flex-wrap: wrap; align-items: center; gap: .15rem !important; background: #0f172a; border: 1px solid rgba(255,255,255,.08);
  border-radius: 16px; padding: .3rem .6rem; margin-bottom: 1.1rem; box-shadow: 0 10px 28px rgba(15,23,42,.28); }
.st-key-topbar, .st-key-topbar * { overflow: visible !important; }
.st-key-topbar > div, [class*="st-key-navg-"], [class*="st-key-navs-"], .st-key-brand { width: auto !important; }
.st-key-topbar p, .st-key-topbar a { font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; }
.st-key-brand { margin-right: .9rem; }
.st-key-brand a, .st-key-brand p { color: #ffffff !important; font-weight: 800 !important; font-size: 1.08rem !important;
  letter-spacing: -0.03em; text-decoration: none !important; }
.st-key-brand a { padding-left: .5rem; }
[class*="st-key-navg-"] { position: relative; }
.nav-title { font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; font-weight: 600; font-size: .92rem; color: #cbd5e1;
  padding: .55rem .95rem; border-radius: 10px; cursor: pointer; user-select: none; outline: none; white-space: nowrap; }
.nav-title:after { content: ""; display: inline-block; margin-left: .5rem; border: solid currentColor; border-width: 0 1.6px 1.6px 0;
  padding: 2.2px; transform: rotate(45deg) translateY(-2px); opacity: .7; }
.nav-title.aktivs { color: #ffffff; box-shadow: inset 0 -2px 0 #3b82f6; border-radius: 10px 10px 4px 4px; }
[class*="st-key-navg-"]:hover .nav-title, [class*="st-key-navg-"]:focus-within .nav-title { color: #ffffff; background: rgba(255,255,255,.12); }
[class*="st-key-navi-"] { display: none !important; position: absolute; top: 100%; left: 0; min-width: 260px; flex-direction: column;
  gap: .1rem !important; background: #0f172a; border: 1px solid rgba(255,255,255,.10); border-radius: 14px; padding: .4rem;
  box-shadow: 0 18px 44px rgba(2,6,23,.5); z-index: 1001; }
[class*="st-key-navg-"]:hover [class*="st-key-navi-"], [class*="st-key-navg-"]:focus-within [class*="st-key-navi-"] { display: flex !important; }
.st-key-topbar a[data-testid="stPageLink-NavLink"] { color: #e2e8f0 !important; border-radius: 10px; padding: .5rem .75rem; }
.st-key-topbar a[data-testid="stPageLink-NavLink"] p { color: inherit !important; font-weight: 500; font-size: .92rem; }
.st-key-topbar a[data-testid="stPageLink-NavLink"]:hover { background: rgba(255,255,255,.09); }
.st-key-topbar a[data-testid="stPageLink-NavLink"][aria-current="page"] { background: #2563eb; color: #ffffff !important; }
[class*="st-key-navs-"] a[data-testid="stPageLink-NavLink"] p { font-weight: 600; color: #cbd5e1 !important; }

/* ===== Komandu salīdzināšanas joslas ===== */
.cmp-row{display:flex;align-items:center;gap:12px;margin:8px 0}
.cmp-val{width:78px;font-weight:600;font-size:1.02rem;opacity:.7}
.cmp-val.right{text-align:right}
.cmp-val.win{opacity:1;font-weight:800}
.cmp-val.win.left{color:#3b82f6}
.cmp-val.win.right{color:#f97316}
.cmp-mid{flex:1}
.cmp-label{font-size:.78rem;text-align:center;opacity:.7;margin-bottom:3px}
.cmp-bar{display:flex;height:8px;border-radius:6px;overflow:hidden;background:rgba(128,128,128,.2)}
.cmp-a{background:#3b82f6}
.cmp-b{background:#f97316}
.cmp-group{margin:18px 0 4px 0;font-weight:700;font-size:.9rem;letter-spacing:.04em;opacity:.8}
</style>""", unsafe_allow_html=True)

# ============================================================================
# DATI
# ============================================================================
VERSIJA = da.datu_versija()


@st.cache_data(show_spinner="Ielādēju datus…")
def ielasit_visu(versija):
    raw = da.ielasit_speles()
    return raw, da.sagatavot_vienoto_tabulu(raw), da.ielasit_kalendaru()


@st.cache_data(show_spinner=False)
def ielasit_papildu(nos, versija):
    return da.ielasit_tabulu(nos)


@st.cache_data(show_spinner=False)
def ielasit_tiesnesus(versija):
    cur = da.ielasit_tabulu("tiesnesi")
    prev, info = da.ielasit_pagajuso_tiesnesus()
    return cur, prev, info


@st.cache_data(show_spinner=False)
def ielasit_planotos(versija):
    return da.ielasit_planotos_tiesnesus()


@st.cache_data(show_spinner=False)
def tiesnesu_tabula(versija):
    cur, prev, _ = ielasit_tiesnesus(versija)
    return da.tiesnesu_apkopojums(cur, prev) if (cur is not None or prev is not None) else (None, None)


def speles_tiesnesi(game_id):
    """(tiesnešu vārdi, gaidāmie noraidījumi pēc tiesnešiem vai None, līgas vidējais vai None)."""
    vardi = da.planotie_vardi(ielasit_planotos(VERSIJA), game_id)
    if not vardi:
        return [], None, None
    tab, liga = tiesnesu_tabula(VERSIJA)
    if tab is None:
        return vardi, None, None
    return vardi, da.tiesnesu_prognoze(tab, liga, vardi), liga["blend"]["kopa"]


RAW, DF, KAL = ielasit_visu(VERSIJA)
if RAW is None or DF.empty:
    st.error("Nav atrasts datu fails 'dati/speles.csv' (vai vecais 'nhl_sezona.csv'). "
             "Palaid nhl_dati.py un ieliec CSV failus repozitorijā.")
    st.stop()

SCOPES = ["Visas", "Mājās", "Izbraukumā"]
LOGI = {"Visa sezona": None, "Pēdējās 5": 5, "Pēdējās 10": 10}


# ============================================================================
# PALĪGFUNKCIJAS
# ============================================================================
def izvele(label, opcijas, default=None, key=None):
    vertiba = st.segmented_control(label, opcijas, default=default or opcijas[0], key=key)
    return vertiba if vertiba is not None else (default or opcijas[0])


def fmt(x, formats="{:.2f}"):
    return "–" if x is None or pd.isna(x) else formats.format(x)


def komandas_etikete(kods):
    return f"{da.pilns_nosaukums(kods)} ({kods})"


POMOC = {
    # līgas / komandu tabulas
    "Sp.": "Nospēlētās spēles",
    "U": "Uzvaras (arī papildlaikā un pēcspēles metienos)",
    "Z": "Zaudējumi pamatlaikā",
    "ZPL": "Zaudējumi papildlaikā vai pēcspēles metienos (komanda saņem 1 punktu)",
    "Punkti": "Tabulas punkti: uzvara 2, zaudējums papildlaikā/pēcspēles metienos 1, zaudējums pamatlaikā 0",
    "Punkti %": "Iegūto punktu daļa no iespējamajiem: punkti / (2 × spēles)",
    "Vārti/sp": "Vidēji gūtie vārti spēlē pamatlaikā (bez papildlaika un pēcspēles metieniem)",
    "Ielaisti/sp": "Vidēji ielaistie vārti spēlē pamatlaikā",
    "Starpība": "Gūto un ielaisto vārtu starpība pamatlaikā",
    "Metieni/sp": "Vidēji metieni vārtos (SOG) spēlē pamatlaikā (bez papildlaika)",
    "Pretin. metieni/sp": "Pretinieka metieni vārtos pret šo komandu vidēji spēlē pamatlaikā (bez papildlaika)",
    "Metienu daļa %": "Komandas metienu daļa pamatlaikā: SOG par / (SOG par + SOG pret), bez papildlaika",
    "PP %": "Vairākuma (Power Play) efektivitāte pamatlaikā: vārti vairākumā / vairākuma iespējas, bez papildlaika",
    "PK %": "Mazākuma (Penalty Kill) efektivitāte pamatlaikā: neielaisto vārtu daļa, kad komanda spēlē mazākumā, bez papildlaika",
    "Noraid./sp": "Vidēji noraidījumu (sodu) skaits spēlē pamatlaikā (bez papildlaika un kautiņiem)",
    "Forma (5)": "Pēdējo 5 spēļu rezultāti (vecākā → jaunākā): 🟩 uzvara, 🟨 zaudējums papildlaikā/pēcspēles metienos, 🟥 zaudējums pamatlaikā",
    "Forma": "Pēdējo spēļu rezultāti (vecākā → jaunākā): 🟩 uzvara, 🟨 zaudējums papildlaikā/pēcspēles metienos, 🟥 zaudējums pamatlaikā",
    "Gūti vārti": "Pēdējās izvēlētajās spēlēs gūtie vārti pamatlaikā (kopā)",
    "Ielaisti vārti": "Pēdējās izvēlētajās spēlēs ielaistie vārti pamatlaikā (kopā)",
    # periodi
    "Gūti": "Šajā periodā gūtie vārti (kopā)",
    "Ielaisti": "Šajā periodā ielaistie vārti (kopā)",
    "Gūti/sp": "Vidēji gūtie vārti šajā periodā spēlē",
    # over / under, vairākums, noraidījumi
    "Over %": "Spēļu daļa (%), kurās abu komandu vārtu summa pamatlaikā pārsniedza izvēlēto līniju",
    "Under %": "Spēļu daļa (%), kurās abu komandu vārtu summa pamatlaikā bija zemāka par izvēlēto līniju",
    "Vid. vārti spēlē": "Vidējā abu komandu vārtu summa spēlē pamatlaikā",
    "PP vārti": "Vairākumā pamatlaikā gūtie vārti (bez papildlaika)",
    "PP iespējas": "Vairākuma iespējas pamatlaikā (reizes, kad komanda spēlēja vairākumā), bez papildlaika",
    "PP metieni": "Metieni vārtos vairākumā pamatlaikā (bez papildlaika)",
    "Ielaisti PP": "Pretinieka vairākumā pamatlaikā gūtie vārti pret šo komandu",
    "PIM min/sp": "Vidēji sodu minūtes spēlē pamatlaikā (bez papildlaika un kautiņiem)",
    "Izcīnīti/sp": "Vidēji pretinieka noraidījumi pret šo komandu spēlē pamatlaikā (bez papildlaika)",
    "Izcīnīti − saņemti": "Izcīnīto un saņemto noraidījumu starpība spēlē; pozitīvs skaitlis = komanda izcīna vairāk, nekā saņem",
    # komandas lapa
    "Skats": "Spēļu izlase, kurai parādīta statistika",
    "Pretinieks": "vs = spēle mājās, @ = spēle izbraukumā",
    "Rez.": "🟩 uzvara, 🟨 zaudējums papildlaikā/pēcspēles metienos, 🟥 zaudējums pamatlaikā",
    "Rezultāts": "Spēles rezultāts: komandas vārti–pretinieka vārti (OT/SO = papildlaiks/pēcspēles metieni)",
    "Metieni": "Metieni vārtos visā spēlē (arī papildlaikā, tikai informācijai): komanda–pretinieks",
    "Noraid.": "Komandas noraidījumu (sodu) skaits spēlē pamatlaikā (bez papildlaika un kautiņiem)",
    "Noraidījumi": "Komandas noraidījumu (sodu) skaits spēlē pamatlaikā (bez papildlaika un kautiņiem)",
    "PIM min": "Sodu minūtes spēlē pamatlaikā (bez papildlaika un kautiņiem)",
    "PIM 1. per.": "Sodu minūtes 1. periodā",
    "PIM 2. per.": "Sodu minūtes 2. periodā",
    "PIM 3. per.": "Sodu minūtes 3. periodā",
    "Starpība (visas)": "Vārtu starpība šajā periodā visās sezonas spēlēs",
    "Mājās": "Vārtu starpība šajā periodā mājas spēlēs",
    "Izbraukumā": "Vārtu starpība šajā periodā izbraukuma spēlēs",
    "Pēdējās 10": "Vārtu starpība šajā periodā pēdējās 10 spēlēs",
    "Vieta": "Spēles vieta: mājās vai izbraukumā",
    # ceļojums un atpūta
    "Iepriekšējā spēle pie": "Komandas pēdējā spēle pirms šīs: kuras komandas mājās tā notika",
    "Ceļojums (km)": "Attālums no iepriekšējās spēles vietas līdz šīs spēles vietai (lielais aplis, aptuveni)",
    "Ceļojuma laiks (h)": "Aptuvenais ceļojuma laiks: autobuss līdz ~400 km, citādi čartera lidojums (~800 km/h + 45 min); bez gaidīšanas un viesnīcas",
    "Laika joslu maiņa (h)": "Laika joslu starpība starp iepriekšējās spēles vietu un šo spēli (+ uz austrumiem, − uz rietumiem)",
    "Stundas kopš pēdējās spēles": "Stundas no iepriekšējās spēles sākuma līdz šīs spēles sākumam",
    "Back-to-back": "Jā = spēle nākamajā kalendārajā dienā (pēc ASV austrumu laika) pēc iepriekšējās spēles",
    "Spēles 7 dienās": "Komandas spēļu skaits pēdējās 7 dienās pirms šīs spēles",
    "Slodzes indekss": "Vienkārša heiristika: back-to-back, ceļojuma garums, laika joslu maiņa un daudz spēļu nedēļā. Jo lielāks, jo vairāk noguruma. Svarus var mainīt failā lokacijas.py",
    # karstie spēlētāji
    "Statuss": "🔥🔥 = ļoti karsts (indekss ≥ 3), 🔥 = karsts (indekss ≥ 2)",
    "Sp. logā": "Spēļu skaits izvēlētajā logā (pēdējās N spēles; ja spēlētājs nospēlējis mazāk, visas viņa spēles)",
    "Sērija": "Spēles pēc kārtas (skaitot no jaunākās), kurās spēlētājs guvis vismaz vienu izvēlēto rādītāju",
    "Sezona īsumā": "Sezonas kopsavilkums: spēles, vārti (G), piespēles (A), punkti (P), metieni vārtos",
    "Kāpēc karsts": "Automātisks īss paskaidrojums: rezultāts logā, sērija, metieni un šaušanas %, laiks laukumā",
    # kalendārs
    "Laiks (Rīga)": "Spēles sākuma laiks pēc Rīgas laika",
    "Galvenie tiesneši": "Spēlei piešķirtie galvenie tiesneši (NHL tos paziņo dažas stundas pirms spēles)",
    # tiesneši
    "Spēles šosezon": "Spēles, kurās tiesnesis šosezon ir strādājis",
    "Spēles pagājušajā": "Spēles, kurās tiesnesis strādāja pagājušajā sezonā",
    "Noraid./sp šosezon": "Vidēji noraidījumi spēlē (abu komandu kopā), kad šosezon strādāja šis tiesnesis",
    "Noraid./sp pagājušajā": "Vidēji noraidījumi spēlē (abu komandu kopā), kad pagājušajā sezonā strādāja šis tiesnesis",
    "Kombinētais": "Kombinētais rādītājs: 60% pagājušā + 40% šī sezona (svarus var mainīt iestatījumos); katra daļa tiek pievilkta pie līgas vidējā, ja spēļu ir maz",
    "Pret līgu": "Kombinētā rādītāja starpība pret kombinēto līgas vidējo; pozitīvs = tiesnesis soda vairāk par vidējo",
    "Mājas komanda": "Kombinētie noraidījumi mājas komandai spēlē",
    "Viesu komanda": "Kombinētie noraidījumi viesu komandai spēlē",
    "Noraid. 1. per.": "Kombinētie noraidījumi (abu komandu kopā) 1. periodā",
    "Noraid. 2. per.": "Kombinētie noraidījumi (abu komandu kopā) 2. periodā",
    "Noraid. 3. per.": "Kombinētie noraidījumi (abu komandu kopā) 3. periodā",
    "Datu apjoms": "Cik drošs rādītājs ir: Maz datu < 8 spēles, Vidēji 8–19, Pietiekami 20+ (abas sezonas kopā)",
    "Noraid. mājas": "Mājas komandas noraidījumi spēlē",
    "Noraid. viesi": "Viesu komandas noraidījumi spēlē",
    "Kopā": "Abu komandu noraidījumi kopā spēles pamatlaikā",
    # spēles detaļas
    "Per.": "Periods (OT = papildlaiks, SO = pēcspēles metieni)",
    "Laiks": "Laiks periodā, kad gūti vārti",
    "Piespēles": "Piespēļu autori",
    "Situācija": "EV = vienāds sastāvs, PP = vairākums, SH = mazākums",
    "Rez. pēc vārtiem": "Rezultāts pēc šiem vārtiem (viesi–mājinieki)",
    "G": "Vārti",
    "A": "Piespēles",
    "P": "Punkti (vārti + piespēles)",
    "TOI spēlē": "Laiks laukumā šajā spēlē (mm:ss)",
    "Atvairīti": "Atvairītie metieni",
    "Metieni pret": "Metieni pret vārtsargu šajā spēlē",
    "SV %": "Atvairīto metienu procents: atvairītie / metieni pret",
    "Iznākums": "W = uzvara, L = zaudējums pamatlaikā, O = zaudējums papildlaikā/pēcspēles metienos",
    # spēlētāju tabulas (kolonnu nosaukumi no datu moduļa)
    "Poz": "Pozīcija: C centrs, L/R spārni, D aizsargs",
    "GP": "Nospēlētās spēles",
    "PM": "Plus/mīnus: komandas gūtie mīnus ielaistie vārti, kamēr spēlētājs bija laukumā vienāda sastāva spēlē",
    "PIM": "Sodu minūtes",
    "SOG": "Metieni vārtos",
    "HIT": "Sitieni pretiniekam (hits)",
    "BLK": "Bloķētie pretinieka metieni",
    "PPG": "Vārti vairākumā",
    "TOI": "Vidējais laiks laukumā spēlē (minūtes)",
    "TOI_kopa": "Kopējais laiks laukumā (minūtes)",
    "P_sp": "Punkti spēlē",
    "GS": "Spēles sākuma sastāvā",
    "W": "Uzvaras",
    "SA": "Metieni pret vārtsargu",
    "SV": "Atvairītie metieni",
    "GA": "Ielaistie vārti",
    "SVpct": "Atvairīto metienu procents: atvairītie / metieni pret",
    "GAA": "Ielaisto vārtu vidējais skaits 60 minūtēs",
}


def palidziba(label):
    """Paskaidrojums kolonnas virsrakstam (parādās, uzbraucot ar peli)."""
    if label in POMOC:
        return POMOC[label]
    for tips, apraksts in (("Over", "lielāka"), ("Under", "mazāka")):
        if str(label).startswith(tips + " "):
            return f"Spēles, kurās abu komandu vārtu summa pamatlaikā bija {apraksts} par {str(label)[len(tips) + 1:]}"
    return None


def cfg_ar_help(kolonnas, config=None, paskaidr=None):
    """column_config visām kolonnām ar paskaidrojumiem (help), saglabājot jau norādīto formatējumu.
    paskaidr: konkrētas tabulas paskaidrojumi, kas aizstāj vispārīgos (piem., periodu lapām)."""
    config = config or {}
    paskaidr = paskaidr or {}
    out = {}
    for k in kolonnas:
        h = paskaidr.get(k) or palidziba(k)
        spec = config.get(k)
        if spec is None:
            if h and k not in config:
                out[k] = st.column_config.Column(k, help=h)
        elif h:
            out[k] = {**spec, "help": h}
        else:
            out[k] = spec
    for k, v in config.items():        # arī kolonnas, kas paslēptas (None) vai nav tabulā
        out.setdefault(k, v)
    return out


def rtabula(df, column_config=None, paskaidr=None, **kw):
    """st.dataframe ar paskaidrojumiem kolonnu virsrakstos."""
    st.dataframe(df, column_config=cfg_ar_help(list(df.columns), column_config, paskaidr), **kw)


def tabula(res, kolonnas, sort_col, ascending=False, config=None, grafiks=True, paskaidr=None):
    """Rangu tabula ar logotipiem. res: DataFrame ar indeksu 'komanda'; kolonnas: {iekšējais: virsraksts}."""
    if res is None or res.empty:
        st.info("Nav datu šim skatam.")
        return
    t = res.sort_values(sort_col, ascending=ascending, kind="stable").reset_index()
    t.insert(0, "Logo", t["komanda"].map(da.logo_url))
    t.insert(1, "Komanda", t["komanda"].map(da.pilns_nosaukums))
    t.insert(0, "#", range(1, len(t) + 1))
    t = t[["#", "Logo", "Komanda"] + list(kolonnas)].rename(columns=kolonnas)
    cfg = {"Logo": st.column_config.ImageColumn("", width="small"),
           "#": st.column_config.NumberColumn("#", width="small")}
    cfg.update(config or {})
    rtabula(t, hide_index=True, width="stretch", column_config=cfg, paskaidr=paskaidr,
                 height=min(1250, 35 * (len(t) + 1) + 3))
    if grafiks:
        with st.expander("Grafiks"):
            s = res[sort_col].dropna().sort_values()
            fig = go.Figure(go.Bar(x=s.values, y=list(s.index), orientation="h", marker_color="#3b82f6"))
            fig.update_layout(height=max(320, 22 * len(s)), margin=dict(l=10, r=10, t=10, b=10),
                              xaxis_title=kolonnas.get(sort_col, sort_col))
            st.plotly_chart(fig)


def prognozes_bloks(pr):
    m1, m2, m3 = st.columns(3)
    m1.metric("Rezultāts (mājas–viesi)", pr["rezultats"], border=True)
    m2.metric("Vārti: Over / Under", pr["over_under"], border=True)
    m3.metric("Noraidījumi", pr["noraidījumi"], border=True)
    st.caption(f"1. periods: {pr['p1']}  ·  2. periods: {pr['p2']}  ·  3. periods: {pr['p3']}")


def rezultata_teksts(h, a, beigas):
    et = da.beigu_etikete(beigas)
    return f"{int(a)}–{int(h)}" + (f" {et}" if et else "")


def salidzinajuma_rinda(nosaukums, a, b, labak="augsts", formats="{:.2f}"):
    if pd.isna(a) or pd.isna(b):
        fa, fb, sa, a_win, b_win = fmt(a, formats), fmt(b, formats), 50.0, False, False
    else:
        fa, fb = formats.format(a), formats.format(b)
        kopa = abs(a) + abs(b)
        sa = 50.0 if kopa == 0 else abs(a) / kopa * 100
        if labak == "augsts":
            a_win, b_win = a > b, b > a
        elif labak == "zems":
            a_win, b_win = a < b, b < a
        else:
            a_win = b_win = False
    st.markdown(
        f'<div class="cmp-row"><div class="cmp-val left{" win" if a_win else ""}">{fa}</div>'
        f'<div class="cmp-mid"><div class="cmp-label">{nosaukums}</div>'
        f'<div class="cmp-bar"><span class="cmp-a" style="width:{sa:.1f}%"></span>'
        f'<span class="cmp-b" style="width:{100 - sa:.1f}%"></span></div></div>'
        f'<div class="cmp-val right{" win" if b_win else ""}">{fb}</div></div>',
        unsafe_allow_html=True)


# ============================================================================
# LAPA: PROGNOZES
# ============================================================================
def lapa_prognozes():
    st.title("Prognozes")
    gatavs, gatavas_sk, kopa_sk = modelis.parbaudit_gatavibu(DF)
    if not gatavs:
        st.warning("⏳ Sezonas sākums: modelis šobrīd krāj datus.")
        st.progress(gatavas_sk / kopa_sk)
        st.caption(f"{gatavas_sk} no {kopa_sk} komandām ir sasniegušas vismaz 5 aizvadītas spēles.")
        return
    st.success("Modelis ir aktīvs. Prognozes tiek aprēķinātas pēc Puasona sadalījuma.")
    if KAL is None:
        st.warning("Nav atrasts 'nhl_kalendars.csv' (palaid kalendars.py).")
        return
    skaits = st.slider("Cik tuvākās spēles rādīt", 3, 15, 7)
    nak = da.nakamas_speles(KAL, skaits)
    if nak.empty:
        st.info("Kalendārā šobrīd nav nākamo spēļu.")
        return
    for _, r in nak.iterrows():
        home, away = r["majas_komanda"], r["viesu_komanda"]
        laiks = r["sakums_lv"].strftime("%H:%M") if pd.notna(r["sakums_lv"]) else ""
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{komandas_etikete(away)}** @ **{komandas_etikete(home)}**")
            c2.caption(f"{r['datums_lv']:%d.%m.%Y} {laiks} (Rīga)")
            vardi, ref_pr, liga_kopa = speles_tiesnesi(r["game_id"])
            if vardi:
                teksts_ = f"Tiesneši: {', '.join(vardi)}"
                if ref_pr is not None and pd.notna(ref_pr["kopa"]):
                    teksts_ += f" · gaidāmie noraidījumi pēc tiesnešiem: {ref_pr['kopa']:.1f} (līgas vidējais {liga_kopa:.1f})"
                st.caption(teksts_)
            else:
                st.caption("Tiesneši vēl nav paziņoti")
            pr = modelis.aprekinat_prognozi_speles(home, away, DF)
            if pr:
                prognozes_bloks(pr)


# ============================================================================
# LAPA: LĪGAS PĀRSKATS
# ============================================================================
def lapa_parskats():
    st.title("Līgas pārskats")
    c1, c2 = st.columns(2)
    with c1:
        scope = izvele("Spēles", SCOPES, key="pk_scope")
    with c2:
        logs = izvele("Laika posms", list(LOGI), key="pk_logs")
    res = da.kopsavilkums(DF, scope, LOGI[logs])
    res["Forma"] = da.forma(DF, 5)
    tabula(res, {
        "GP": "Sp.", "W": "U", "L": "Z", "OTL": "ZPL", "PTS": "Punkti", "PTS_pct": "Punkti %",
        "G_sp": "Vārti/sp", "Z_sp": "Ielaisti/sp", "Starpiba": "Starpība",
        "SOG_sp": "Metieni/sp", "SOG_dala": "Metienu daļa %", "PP_pct": "PP %", "PK_pct": "PK %",
        "PEN_sp": "Noraid./sp", "Forma": "Forma (5)"},
        sort_col="PTS",
        config={"Punkti %": st.column_config.ProgressColumn("Punkti %", min_value=0, max_value=100, format="%.0f"),
                "Vārti/sp": st.column_config.NumberColumn(format="%.2f"),
                "Ielaisti/sp": st.column_config.NumberColumn(format="%.2f"),
                "Metieni/sp": st.column_config.NumberColumn(format="%.1f"),
                "Metienu daļa %": st.column_config.NumberColumn(format="%.1f"),
                "PP %": st.column_config.NumberColumn(format="%.1f"),
                "PK %": st.column_config.NumberColumn(format="%.1f"),
                "Noraid./sp": st.column_config.NumberColumn(format="%.1f")})
    st.caption("U = uzvaras, Z = zaudējumi pamatlaikā, ZPL = zaudējumi papildlaikā/pēcspēles metienos. "
               "Visi statistikas rādītāji (vārti, metieni, noraidījumi, vairākums) ir pamatlaika, bez papildlaika un pēcspēles metieniem. "
               "Uzvaras, zaudējumi un punkti ir oficiālie rezultāti. Tabulu var kārtot, klikšķinot uz kolonnas virsraksta.")


# ============================================================================
# LAPA: SALĪDZINĀT KOMANDAS
# ============================================================================
RADARA_ASIS = [("Uzbrukums", "G_sp", True), ("Aizsardzība", "Z_sp", False), ("Metieni", "SOG_sp", True),
               ("Vairākums", "PP_pct", True), ("Mazākums", "PK_pct", True), ("Disciplīna", "PEN_sp", False)]

SALIDZ_METRIKAS = [
    ("Rezultativitāte", [
        ("Punkti %", "PTS_pct", "augsts", "{:.0f}"),
        ("Vārti spēlē", "G_sp", "augsts", "{:.2f}"),
        ("Ielaisti spēlē", "Z_sp", "zems", "{:.2f}"),
        ("Over 6.5 spēļu daļa %", "Over65", "neitrals", "{:.0f}"),
    ]),
    ("Metieni", [
        ("Metieni vārtos / spēle", "SOG_sp", "augsts", "{:.1f}"),
        ("Pretinieka metieni / spēle", "SA_sp", "zems", "{:.1f}"),
        ("Metienu daļa %", "SOG_dala", "augsts", "{:.1f}"),
    ]),
    ("Vairākums un noraidījumi", [
        ("Vairākums PP %", "PP_pct", "augsts", "{:.1f}"),
        ("Mazākums PK %", "PK_pct", "augsts", "{:.1f}"),
        ("Noraidījumi / spēle", "PEN_sp", "zems", "{:.1f}"),
        ("Izcīnītie noraidījumi / spēle", "DRAW_sp", "augsts", "{:.1f}"),
    ]),
    ("Vārti pa periodiem (gūti)", [
        ("1. periods", "G_p1", "augsts", "{:.2f}"),
        ("2. periods", "G_p2", "augsts", "{:.2f}"),
        ("3. periods", "G_p3", "augsts", "{:.2f}"),
    ]),
    ("Vārti pa periodiem (ielaisti)", [
        ("1. periods", "Z_p1", "zems", "{:.2f}"),
        ("2. periods", "Z_p2", "zems", "{:.2f}"),
        ("3. periods", "Z_p3", "zems", "{:.2f}"),
    ]),
]


def percentiles(liga, komanda):
    vert = []
    for _, k, augsts in RADARA_ASIS:
        v = liga[k].rank(pct=True, ascending=augsts).get(komanda, np.nan) * 100
        vert.append(50.0 if pd.isna(v) else float(v))
    return vert


def celojuma_bloks(home, away, sakums):
    """Attālums starp pilsētām un abu komandu atpūta/ceļojums pirms spēles (modulis lokacijas.py)."""
    f = lokacijas.speles_faktori(DF, home, away, sakums)
    c = f["starp_pilsetam"]
    m = st.columns(4)
    m[0].metric("Attālums starp pilsētām", f"{c['km']:.0f} km", border=True)
    m[1].metric("Ceļojuma laiks (aptuveni)", f"{c['laiks_h']} h", border=True,
                help="Autobuss līdz ~400 km, citādi čartera lidojums (~800 km/h + 45 min)")
    m[2].metric("Ceļojuma veids", {"autobuss": "Autobuss", "lidojums": "Lidojums", "nav": "—"}[c["veids"]], border=True)
    m[3].metric("Laika joslu starpība", f"{c['laika_joslu_starpiba_h']:+.0f} h", border=True,
                help="Viesu komandas laika josla attiecībā pret mājiniekiem (+ = viesi pārceļas uz austrumiem)")
    rindas = []
    for puse, kods in (("majas", home), ("viesi", away)):
        x = f[puse]
        rindas.append({
            "Komanda": da.pilns_nosaukums(kods) + (" (mājinieki)" if puse == "majas" else " (viesi)"),
            "Iepriekšējā spēle pie": x["iepriekspeja_vieta"] or "–",
            "Ceļojums (km)": x["km"], "Ceļojuma laiks (h)": x["laiks_h"],
            "Laika joslu maiņa (h)": x["laika_joslu_starpiba_h"],
            "Stundas kopš pēdējās spēles": x["stundas_kops_pedejas"],
            "Back-to-back": "Jā" if x["back_to_back"] else "Nē",
            "Spēles 7 dienās": x["speles_pedejas_7_dienas"],
            "Slodzes indekss": lokacijas.celojuma_slodze(x),
        })
    rtabula(pd.DataFrame(rindas), hide_index=True, width="stretch",
            column_config={"Ceļojums (km)": st.column_config.NumberColumn(format="%.0f"),
                           "Laika joslu maiņa (h)": st.column_config.NumberColumn(format="%+.0f"),
                           "Stundas kopš pēdējās spēles": st.column_config.NumberColumn(format="%.0f"),
                           "Slodzes indekss": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Ceļojums = attālums no komandas iepriekšējās spēles vietas līdz šīs spēles vietai. "
               "Attālumi un laiks ir aptuveni (lielais aplis, čartera lidojums). Slodzes indekss ir heiristika, nevis pierādīta ietekme.")


def lapa_salidzinat():
    st.title("Komandu salīdzināšana")
    komandas = sorted(da.KOMANDAS)
    nak = da.nakamas_speles(KAL, 15)
    opc = {}
    for _, r in nak.iterrows():
        opc[f"{r['datums_lv']:%d.%m} · {r['viesu_komanda']} @ {r['majas_komanda']}"] = (
            r["majas_komanda"], r["viesu_komanda"], r["sakums_lv"])
    izv = st.selectbox("Spēle no kalendāra", ["— izvēlēties komandas manuāli —"] + list(opc),
                       index=1 if opc else 0)
    sakums = pd.Timestamp.now(tz=da.LV_TZ)          # manuālai izvēlei: aprēķins uz šo brīdi
    if izv in opc:
        home, away, sak = opc[izv]
        if pd.notna(sak):
            sakums = sak
    else:
        c1, c2 = st.columns(2)
        home = c1.selectbox("Mājinieki (A)", komandas, index=0, format_func=komandas_etikete)
        away = c2.selectbox("Viesi (B)", komandas, index=1, format_func=komandas_etikete)

    pamats = izvele("Salīdzināšanas pamats",
                    ["Mājas (A) pret izbraukumu (B)", "Visa sezona", "Pēdējās 10", "Pēdējās 5"],
                    key="sl_pamats")
    if pamats.startswith("Mājas"):
        sc_a, sc_b, n = "Mājās", "Izbraukumā", None
    else:
        sc_a = sc_b = "Visas"
        n = {"Visa sezona": None, "Pēdējās 10": 10, "Pēdējās 5": 5}[pamats]
    liga_a = da.kopsavilkums(DF, sc_a, n)
    liga_b = liga_a if sc_a == sc_b else da.kopsavilkums(DF, sc_b, n)
    if home not in liga_a.index or away not in liga_b.index:
        st.warning("Vienai no komandām šim skatam vēl nav datu.")
        return
    a, b = liga_a.loc[home], liga_b.loc[away]

    h1, h2, h3 = st.columns([4, 1, 4], vertical_alignment="center")
    with h1:
        st.image(da.logo_url(home), width=72)
        st.subheader(f":blue[{da.pilns_nosaukums(home)}]")
        st.caption(f"A · mājinieki · {int(a['GP'])} spēles · {da.forma(DF[DF['komanda'] == home], 5).iloc[0]}")
    with h2:
        st.markdown("<h3 style='text-align:center;opacity:.5'>VS</h3>", unsafe_allow_html=True)
    with h3:
        st.image(da.logo_url(away), width=72)
        st.subheader(f":orange[{da.pilns_nosaukums(away)}]")
        st.caption(f"B · viesi · {int(b['GP'])} spēles · {da.forma(DF[DF['komanda'] == away], 5).iloc[0]}")

    kol_l, kol_r = st.columns([3, 2])
    with kol_l:
        for grupa, metrikas in SALIDZ_METRIKAS:
            st.markdown(f"<div class='cmp-group'>{grupa.upper()}</div>", unsafe_allow_html=True)
            for nos, k, labak, formats in metrikas:
                salidzinajuma_rinda(nos, a[k], b[k], labak, formats)
    with kol_r:
        nos = [x[0] for x in RADARA_ASIS]
        va, vb = percentiles(liga_a, home), percentiles(liga_b, away)
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=va + va[:1], theta=nos + nos[:1], fill="toself", name=home,
                                      line_color="#3b82f6", fillcolor="rgba(59,130,246,0.25)"))
        fig.add_trace(go.Scatterpolar(r=vb + vb[:1], theta=nos + nos[:1], fill="toself", name=away,
                                      line_color="#f97316", fillcolor="rgba(249,115,22,0.25)"))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False)),
                          height=400, margin=dict(l=40, r=40, t=20, b=20), legend=dict(orientation="h"))
        st.plotly_chart(fig)
        st.caption("Reitings pret visām komandām (100 = līgas labākais).")

    st.divider()
    t1, t2, t3 = st.tabs(["Modeļa prognoze", "Savstarpējās spēles", "Ceļojums un atpūta"])
    with t1:
        gatavs, _, _ = modelis.parbaudit_gatavibu(DF)
        if gatavs:
            pr = modelis.aprekinat_prognozi_speles(home, away, DF)
            if pr:
                prognozes_bloks(pr)
        else:
            st.info("Modelis vēl krāj datus (vajag vismaz 5 spēles katrai komandai).")
    with t2:
        h2h = RAW[((RAW["home_team"] == home) & (RAW["away_team"] == away)) |
                  ((RAW["home_team"] == away) & (RAW["away_team"] == home))]
        if h2h.empty:
            st.info("Šosezon šīs komandas vēl nav tikušās.")
        else:
            t = pd.DataFrame({
                "Datums": h2h["datums_lv"].dt.strftime("%d.%m.%Y"),
                "Spēle": h2h["away_team"] + " @ " + h2h["home_team"],
                "Rezultāts (viesi–mājas)": [rezultata_teksts(r.home_total, r.away_total, r.spele_beidzas)
                                            for r in h2h.itertuples()],
            })
            rtabula(t, hide_index=True, width="stretch")
    with t3:
        celojuma_bloks(home, away, sakums)


# ============================================================================
# LAPAS: PERIODI
# ============================================================================
def lapa_periodi():
    st.title("Periodu statistika")
    c0, c1, c2, c3 = st.columns(4)
    with c0:
        p = int(izvele("Hokeja periods", ["1. periods", "2. periods", "3. periods"], key="per_p")[0])
    with c1:
        scope = izvele("Spēles", SCOPES, key="per_scope")
    with c2:
        logs = izvele("Laika posms", list(LOGI), key="per_logs")
    with c3:
        metrika = izvele("Kārtot pēc", ["Vārtu starpība", "Gūtie", "Ielaistie", "Metieni (SOG)"], key="per_met")
    kolonna = {"Vārtu starpība": "Starpiba", "Gūtie": "G", "Ielaistie": "Z", "Metieni (SOG)": "SOG_sp"}[metrika]
    res = da.periodu_tabula(DF, p, scope, LOGI[logs])
    pask = {
        "Gūti": f"{p}. periodā gūtie vārti (kopā izvēlētajās spēlēs)",
        "Ielaisti": f"{p}. periodā ielaistie vārti (kopā izvēlētajās spēlēs)",
        "Starpība": f"Gūto un ielaisto vārtu starpība {p}. periodā (kopā izvēlētajās spēlēs)",
        "Gūti/sp": f"Vidēji gūtie vārti {p}. periodā vienā spēlē",
        "Ielaisti/sp": f"Vidēji ielaistie vārti {p}. periodā vienā spēlē",
        "Metieni/sp": f"Vidēji metieni vārtos {p}. periodā vienā spēlē",
        "Pretin. metieni/sp": f"Pretinieka vidējie metieni vārtos pret šo komandu {p}. periodā vienā spēlē",
    }
    tabula(res, {"GP": "Sp.", "G": "Gūti", "Z": "Ielaisti", "Starpiba": "Starpība",
                 "G_sp": "Gūti/sp", "Z_sp": "Ielaisti/sp", "SOG_sp": "Metieni/sp", "SA_sp": "Pretin. metieni/sp"},
           sort_col=kolonna, paskaidr=pask,
           config={"Gūti/sp": st.column_config.NumberColumn(format="%.2f"),
                   "Ielaisti/sp": st.column_config.NumberColumn(format="%.2f"),
                   "Metieni/sp": st.column_config.NumberColumn(format="%.1f"),
                   "Pretin. metieni/sp": st.column_config.NumberColumn(format="%.1f")})


# ============================================================================
# LAPA: FORMA UN VĀRTI
# ============================================================================
def lapa_forma():
    st.title("Forma un vārti")
    c1, c2 = st.columns(2)
    with c1:
        n = int(izvele("Pēdējās spēles", ["5", "10"], key="fm_n"))
    with c2:
        kartot = izvele("Kārtot", ["Karstākās (vārti)", "Aukstākās (vārti)", "Visvairāk ielaiž", "Labākā forma (punkti)"],
                        key="fm_kartot")
    res = da.kopsavilkums(DF, "Visas", n)
    res["Forma"] = da.forma(DF, n)
    kol, asc = {"Karstākās (vārti)": ("G", False), "Aukstākās (vārti)": ("G", True),
                "Visvairāk ielaiž": ("Z", False), "Labākā forma (punkti)": ("PTS", False)}[kartot]
    tabula(res, {"GP": "Sp.", "W": "U", "L": "Z", "OTL": "ZPL", "PTS": "Punkti",
                 "G": "Gūti vārti", "Z": "Ielaisti vārti", "Starpiba": "Starpība", "Forma": "Forma"},
           sort_col=kol, ascending=asc)


# ============================================================================
# LAPA: OVER / UNDER
# ============================================================================
def lapa_over_under():
    st.title("Over / Under (pamatlaika vārtu summa)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        linija = float(izvele("Līnija", ["5.5", "6.5", "7.5"], default="6.5", key="ou_l"))
    with c2:
        virziens = izvele("Rādīt", ["Over", "Under"], key="ou_v")
    with c3:
        scope = izvele("Spēles", SCOPES, key="ou_s")
    with c4:
        logs = izvele("Laika posms", ["Pēdējās 5", "Pēdējās 10", "Visa sezona"], default="Pēdējās 10", key="ou_n")
    res = da.over_under(DF, linija, scope, LOGI[logs])
    kol = "Over" if virziens == "Over" else "Under"
    tabula(res, {"GP": "Sp.", "Over": f"Over {linija}", "Over_pct": "Over %",
                 "Under": f"Under {linija}", "Under_pct": "Under %", "Vid_kopa": "Vid. vārti spēlē"},
           sort_col=kol,
           config={"Over %": st.column_config.ProgressColumn("Over %", min_value=0, max_value=100, format="%.0f"),
                   "Under %": st.column_config.ProgressColumn("Under %", min_value=0, max_value=100, format="%.0f"),
                   "Vid. vārti spēlē": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Skaita abu komandu vārtus pamatlaikā (bez papildlaika un pēcspēles metieniem).")


# ============================================================================
# LAPA: POWERPLAY
# ============================================================================
def lapa_powerplay():
    st.title("Vairākums (Powerplay)")
    c1, c2, c3 = st.columns(3)
    with c1:
        scope = izvele("Spēles", SCOPES, key="pp_s")
    with c2:
        logs = izvele("Laika posms", list(LOGI), key="pp_n")
    with c3:
        kartot = izvele("Kārtot pēc", ["Vairākuma vārti", "PP %", "Vairākuma metieni", "PK %"], key="pp_k")
    kol = {"Vairākuma vārti": "PPG", "PP %": "PP_pct", "Vairākuma metieni": "PP_sog", "PK %": "PK_pct"}[kartot]
    res = da.kopsavilkums(DF, scope, LOGI[logs])
    tabula(res, {"GP": "Sp.", "PPG": "PP vārti", "PP_opp": "PP iespējas", "PP_pct": "PP %",
                 "PP_sog": "PP metieni", "PPG_pret": "Ielaisti PP", "PK_pct": "PK %"},
           sort_col=kol,
           config={"PP %": st.column_config.NumberColumn(format="%.1f"),
                   "PK %": st.column_config.NumberColumn(format="%.1f")})
    st.caption("PP % = vārti vairākumā / vairākuma iespējas. PK % = mazākumā neielaisto vārtu daļa. "
               "Ielaisti PP = pretinieka vairākuma vārti pret šo komandu.")


# ============================================================================
# LAPA: NORAIDĪJUMI
# ============================================================================
def lapa_noraidijumi():
    st.title("Noraidījumi")
    c1, c2, c3 = st.columns(3)
    with c1:
        scope = izvele("Spēles", SCOPES, key="nr_s")
    with c2:
        logs = izvele("Laika posms", list(LOGI), key="nr_n")
    with c3:
        perioda = izvele("Hokeja periods", ["Visi periodi", "Kopā", "1. periods", "2. periods", "3. periods"], key="nr_p")
    d1, d2, d3 = st.columns(3)
    with d1:
        metrika = izvele("Rādītājs", ["Noraidījumu skaits", "Sodu minūtes"], key="nr_m")
    with d2:
        vertiba = izvele("Vērtība", ["Vidēji spēlē", "Kopā"], key="nr_v")
    with d3:
        veids = izvele("Veids", ["Saņemtie", "Izcīnītie"], key="nr_k")

    mkods = "skaits" if metrika == "Noraidījumu skaits" else "minutes"
    videji = vertiba == "Vidēji spēlē"
    vkods = "s" if veids == "Saņemtie" else "i"
    fm = "%.2f" if videji else "%.0f"
    res = da.noraidijumu_tabula(DF, scope, LOGI[logs], mkods, videji)

    mtxt = "noraidījumu skaits" if mkods == "skaits" else "sodu minūtes"
    vtxt = "vidēji vienā spēlē" if videji else "kopā izvēlētajās spēlēs"
    ptxt = {"kopa": "pamatlaikā (1.–3. periods kopā, bez papildlaika)", 1: "1. periodā", 2: "2. periodā", 3: "3. periodā"}
    pkarte = {"Kopā": "kopa", "1. periods": 1, "2. periods": 2, "3. periods": 3}

    def apraksts(k, p):
        v = "komandas saņemtie (paša sodi)" if k == "s" else "komandas izcīnītie (pretinieka sodi pret šo komandu)"
        return f"{mtxt[0].upper() + mtxt[1:]} {ptxt[p]}: {v}, {vtxt}"

    if perioda == "Visi periodi":
        kartot = izvele("Kārtot pēc", list(pkarte), key="nr_kart")
        kolonnas, pask = {"GP": "Sp."}, {}
        for nos, p in pkarte.items():
            kolonnas[f"{vkods}_{p}"] = nos
            pask[nos] = apraksts(vkods, p)
        tabula(res, kolonnas, sort_col=f"{vkods}_{pkarte[kartot]}", paskaidr=pask,
               config={nos: st.column_config.NumberColumn(format=fm) for nos in pkarte})
    else:
        p = pkarte[perioda]
        kolonnas = {"GP": "Sp.", f"s_{p}": "Saņemtie", f"i_{p}": "Izcīnītie", f"r_{p}": "Izcīnīti − saņemti"}
        pask = {"Saņemtie": apraksts("s", p), "Izcīnītie": apraksts("i", p),
                "Izcīnīti − saņemti": f"Izcīnīto un saņemto starpība ({ptxt[p]}, {mtxt}, {vtxt}); "
                                      "pozitīvs skaitlis = komanda izcīna vairāk, nekā saņem"}
        tabula(res, kolonnas, sort_col=f"{vkods}_{p}", paskaidr=pask,
               config={"Saņemtie": st.column_config.NumberColumn(format=fm),
                       "Izcīnītie": st.column_config.NumberColumn(format=fm),
                       "Izcīnīti − saņemti": st.column_config.NumberColumn(format=fm.replace("%", "%+"))})
    st.caption("Saņemtie = paša komandas noraidījumi, izcīnītie = pretinieka noraidījumi pret šo komandu. "
               "Noraidījumu skaitā kautiņi nav iekļauti. Kopā = 1.–3. periods kopā, papildlaiks netiek ieskaitīts. "
               "Vecākām spēlēm sodu skaits pa periodiem ir aprēķināts kā sodu minūtes / 2, līdz tās tiek atjaunotas.")


# ============================================================================
# LAPA: KOMANDAS STATISTIKA
# ============================================================================
def lapa_komanda():
    st.title("Komandas analīze")
    kom = st.selectbox("Komanda", sorted(da.KOMANDAS), format_func=komandas_etikete)
    tdf = DF[DF["komanda"] == kom]
    if tdf.empty:
        st.warning("Šai komandai vēl nav datu.")
        return
    c1, c2 = st.columns([1, 8], vertical_alignment="center")
    c1.image(da.logo_url(kom), width=64)
    c2.subheader(da.pilns_nosaukums(kom))
    c2.caption(f"Forma (pēdējās 5): {da.forma(tdf, 5).iloc[0]}")

    t_par, t_mi, t_sp, t_per, t_nor, t_nak = st.tabs(
        ["Pārskats", "Mājas / izbraukums", "Pēdējās spēles", "Periodi", "Noraidījumi un PP", "Nākamās spēles"])
    kop = da.kopsavilkums(tdf).iloc[0]

    with t_par:
        m = st.columns(4)
        m[0].metric("Spēles", int(kop["GP"]), border=True)
        m[1].metric("Bilance (U-Z-ZPL)", f"{int(kop['W'])}-{int(kop['L'])}-{int(kop['OTL'])}", border=True)
        m[2].metric("Punkti", f"{int(kop['PTS'])} ({kop['PTS_pct']:.0f}%)", border=True)
        m[3].metric("Vārtu starpība", f"{int(kop['Starpiba']):+d}", border=True)
        m = st.columns(4)
        m[0].metric("Vārti spēlē", fmt(kop["G_sp"]), border=True)
        m[1].metric("Ielaisti spēlē", fmt(kop["Z_sp"]), border=True)
        m[2].metric("Metieni spēlē", fmt(kop["SOG_sp"], "{:.1f}"), border=True)
        m[3].metric("Pretinieka metieni", fmt(kop["SA_sp"], "{:.1f}"), border=True)

        st.markdown("##### Vidējie vārti (pēdējās 10 spēles) — prognožu pamats")
        last10 = tdf.tail(10)
        home10 = tdf[tdf["majas"] == 1].tail(10)
        away10 = tdf[tdf["majas"] == 0].tail(10)
        x = st.columns(3)
        x[0].metric("Kopā", fmt(last10["g_reg"].mean()), border=True)
        x[1].metric("Mājās", fmt(home10["g_reg"].mean()), border=True)
        x[2].metric("Izbraukumā", fmt(away10["g_reg"].mean()), border=True)
        y = st.columns(3)
        for i, p in enumerate((1, 2, 3)):
            y[i].metric(f"{p}. periods", fmt(last10[f"g_p{p}"].mean()), border=True)

    with t_mi:
        rindas = {}
        for nos, sc, n in [("Visas", "Visas", None), ("Mājās", "Mājās", None), ("Izbraukumā", "Izbraukumā", None),
                           ("Pēdējās 5", "Visas", 5), ("Pēdējās 5 mājās", "Mājās", 5),
                           ("Pēdējās 5 izbraukumā", "Izbraukumā", 5), ("Pēdējās 10", "Visas", 10)]:
            k = da.kopsavilkums(tdf, sc, n)
            if not k.empty:
                rindas[nos] = k.iloc[0]
        t = pd.DataFrame(rindas).T[["GP", "G_sp", "Z_sp", "SOG_sp", "SA_sp", "PEN_sp", "PIM_sp", "PP_pct", "PK_pct"]]
        t.columns = ["Sp.", "Vārti/sp", "Ielaisti/sp", "Metieni/sp", "Pretin. metieni/sp",
                     "Noraid./sp", "PIM min/sp", "PP %", "PK %"]
        rtabula(t.reset_index().rename(columns={"index": "Skats"}), hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in t.columns[1:]})

    with t_sp:
        lg = tdf.tail(10).iloc[::-1]
        tab = pd.DataFrame({
            "Datums": lg["datums"].dt.strftime("%d.%m"),
            "Pretinieks": lg["majas"].map({1: "vs ", 0: "@ "}) + lg["pretinieks"],
            "Rez.": lg["rez"].map(da.FORMAS_EMOJI),
            "Rezultāts": [f"{int(a)}–{int(b)}" + (f" {da.beigu_etikete(e)}" if da.beigu_etikete(e) else "")
                          for a, b, e in zip(lg["g_tot"].fillna(0), lg["z_tot"].fillna(0), lg["beigas"])],
            "Metieni": [f"{fmt(a, '{:.0f}')}–{fmt(b, '{:.0f}')}" for a, b in zip(lg["sog_tot"], lg["sog_pret"])],
            "Noraid.": lg["pim_count"],
            "PP vārti": lg["ppg"],
        })
        rtabula(tab, hide_index=True, width="stretch")

    with t_per:
        mh, ma, l10 = tdf[tdf["majas"] == 1], tdf[tdf["majas"] == 0], tdf.tail(10)
        rindas = []
        for p in (1, 2, 3):
            rindas.append({"Periods": f"{p}. periods",
                           "Starpība (visas)": int(tdf[f"diff_p{p}"].sum()),
                           "Mājās": int(mh[f"diff_p{p}"].sum()), "Izbraukumā": int(ma[f"diff_p{p}"].sum()),
                           "Pēdējās 10": int(l10[f"diff_p{p}"].sum()),
                           "Gūti/sp": tdf[f"g_p{p}"].mean(), "Ielaisti/sp": tdf[f"z_p{p}"].mean(),
                           "Metieni/sp": tdf[f"sog_p{p}"].mean()})
        pt = pd.DataFrame(rindas)
        rtabula(pt, hide_index=True, width="stretch",
                paskaidr={"Gūti/sp": "Vidēji gūtie vārti attiecīgajā periodā vienā spēlē",
                          "Ielaisti/sp": "Vidēji ielaistie vārti attiecīgajā periodā vienā spēlē",
                          "Metieni/sp": "Vidēji metieni vārtos attiecīgajā periodā vienā spēlē"},
                     column_config={"Gūti/sp": st.column_config.NumberColumn(format="%.2f"),
                                    "Ielaisti/sp": st.column_config.NumberColumn(format="%.2f"),
                                    "Metieni/sp": st.column_config.NumberColumn(format="%.1f")})
        fig = go.Figure()
        fig.add_bar(name="Gūti/sp", x=pt["Periods"], y=pt["Gūti/sp"], marker_color="#3b82f6")
        fig.add_bar(name="Ielaisti/sp", x=pt["Periods"], y=pt["Ielaisti/sp"], marker_color="#f97316")
        fig.update_layout(barmode="group", height=320, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig)

    with t_nor:
        m = st.columns(4)
        m[0].metric("Noraidījumi/sp", fmt(kop["PEN_sp"], "{:.1f}"), border=True)
        m[1].metric("Izcīnītie/sp", fmt(kop["DRAW_sp"], "{:.1f}"), border=True)
        m[2].metric("PP %", fmt(kop["PP_pct"], "{:.1f}"), border=True)
        m[3].metric("PK %", fmt(kop["PK_pct"], "{:.1f}"), border=True)
        lg = tdf.tail(5).iloc[::-1]
        st.markdown("##### Noraidījumi pēdējās 5 spēlēs")
        rtabula(pd.DataFrame({
            "Datums": lg["datums"].dt.strftime("%d.%m"),
            "Pretinieks": lg["majas"].map({1: "vs ", 0: "@ "}) + lg["pretinieks"],
            "Noraidījumi": lg["pim_count"], "PIM min": lg["pim_reg"],
            "PIM 1. per.": lg["pim_p1"], "PIM 2. per.": lg["pim_p2"], "PIM 3. per.": lg["pim_p3"]}),
            hide_index=True, width="stretch")

    with t_nak:
        nak = da.nakamas_speles(KAL, 8, komanda=kom)
        if nak.empty:
            st.info("Kalendārā nav atrastu nākamo spēļu.")
        else:
            rtabula(pd.DataFrame({
                "Datums": nak["datums_lv"].dt.strftime("%d.%m.%Y"),
                "Laiks (Rīga)": nak["sakums_lv"].dt.strftime("%H:%M"),
                "Pretinieks": [komandas_etikete(v if m == kom else m)
                               for m, v in zip(nak["majas_komanda"], nak["viesu_komanda"])],
                "Vieta": ["Mājās" if m == kom else "Izbraukumā" for m in nak["majas_komanda"]]}),
                hide_index=True, width="stretch")


# ============================================================================
# LAPA: KALENDĀRS
# ============================================================================
def lapa_kalendars():
    st.title("Spēļu kalendārs")
    if KAL is None:
        st.warning("Kalendāra fails 'nhl_kalendars.csv' nav atrasts (palaid kalendars.py).")
        return
    c1, c2 = st.columns([1, 2])
    dienas = c1.slider("Cik dienas uz priekšu", 1, 14, 5)
    komanda = c2.selectbox("Komanda", ["Visas komandas"] + sorted(da.KOMANDAS),
                           format_func=lambda x: x if x == "Visas komandas" else komandas_etikete(x))
    sodien = da.sodien_lv()
    d = KAL["datums_lv"].dt.date
    x = KAL[(d >= sodien) & (d <= sodien + timedelta(days=dienas))]
    if komanda != "Visas komandas":
        x = x[(x["majas_komanda"] == komanda) | (x["viesu_komanda"] == komanda)]
    if x.empty:
        st.info("Šajā periodā spēļu nav.")
        return
    for dat, grupa in x.groupby(x["datums_lv"].dt.date):
        with st.container(border=True):
            st.markdown(f"**{da.DIENAS[dat.weekday()]}, {dat:%d.%m.%Y}** · {len(grupa)} spēles")
            plan = ielasit_planotos(VERSIJA)
            ties_txt = []
            for gid in grupa["game_id"]:
                vardi = da.planotie_vardi(plan, gid)
                ties_txt.append(", ".join(vardi) if vardi else "Tiesneši nav paziņoti")
            rtabula(pd.DataFrame({
                "Laiks (Rīga)": grupa["sakums_lv"].dt.strftime("%H:%M"),
                "Viesi": grupa["viesu_komanda"].map(komandas_etikete),
                "Mājinieki": grupa["majas_komanda"].map(komandas_etikete),
                "Galvenie tiesneši": ties_txt}),
                hide_index=True, width="stretch")


# ============================================================================
# LAPA: REZULTĀTI
# ============================================================================
def lapa_rezultati():
    st.title("Spēļu rezultāti")
    datumi = RAW["datums_lv"].dt.date
    mind, maxd = datumi.min(), max(datumi.max(), da.sodien_lv())
    if "rez_datums" not in st.session_state:
        st.session_state["rez_datums"] = min(da.sodien_lv(), datumi.max())

    def nobide(dienas):
        st.session_state["rez_datums"] = min(max(st.session_state["rez_datums"] + timedelta(days=dienas), mind), maxd)

    c1, c2, c3 = st.columns([1, 2, 1], vertical_alignment="bottom")
    c1.button("❮ Iepriekšējā diena", on_click=nobide, args=(-1,), width="stretch")
    c2.date_input("Datums (Rīgas laiks)", min_value=mind, max_value=maxd, key="rez_datums", format="DD.MM.YYYY")
    c3.button("Nākamā diena ❯", on_click=nobide, args=(1,), width="stretch")

    dat = st.session_state["rez_datums"]
    st.markdown(f"#### {da.DIENAS[dat.weekday()]}, {dat:%d.%m.%Y}")
    dienas_speles = RAW[datumi == dat].sort_values(["sakums_lv", "game_id"])
    if dienas_speles.empty:
        st.info("Šajā datumā nav noslēgušos spēļu.")
        return

    varti = ielasit_papildu("varti", VERSIJA)
    sk = ielasit_papildu("speletaji", VERSIJA)
    vg = ielasit_papildu("vartsargi", VERSIJA)
    ties = ielasit_papildu("tiesnesi", VERSIJA)

    for _, r in dienas_speles.iterrows():
        home, away = r["home_team"], r["away_team"]
        ht, at = int(r["home_total"]), int(r["away_total"])
        et = da.beigu_etikete(r["spele_beidzas"])
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 3, 5], vertical_alignment="center")
            with c1:
                st.image(da.logo_url(away), width=48)
                st.markdown(f"**{da.pilns_nosaukums(away)}**" if at > ht else da.pilns_nosaukums(away))
            with c2:
                st.markdown(f"<h2 style='text-align:center;margin:0'>{at} : {ht}</h2>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;opacity:.7'>{et or 'Pamatlaiks'}</div>",
                            unsafe_allow_html=True)
            with c3:
                st.image(da.logo_url(home), width=48)
                st.markdown(f"**{da.pilns_nosaukums(home)}**" if ht > at else da.pilns_nosaukums(home))

            periodi = " · ".join(f"{p}P {int(r[f'away_p{p}'])}:{int(r[f'home_p{p}'])}" for p in (1, 2, 3))
            if (r.get("home_ot", 0) or 0) + (r.get("away_ot", 0) or 0) > 0:
                periodi += f" · OT/SO {int(r['away_ot'])}:{int(r['home_ot'])}"

            def pari(nos, formats="{:.0f}"):
                a, h = r.get(f"away_{nos}"), r.get(f"home_{nos}")
                return None if pd.isna(a) or pd.isna(h) else f"{formats.format(a)}–{formats.format(h)}"

            pen_a = r.get("away_pen_count")
            pen_h = r.get("home_pen_count")
            if pd.isna(pen_a) or pd.isna(pen_h):
                pen_a, pen_h = round(r["away_pim_total"] / 2), round(r["home_pim_total"] / 2)
            dalas = [f"Metieni {pari('sog_total')}", f"Noraidījumi {int(pen_a)}–{int(pen_h)}",
                     f"PP vārti {pari('ppg')}", f"Hits {pari('hits')}" if pari("hits") else None,
                     f"Iemetieni % {pari('faceoff_pct', '{:.0f}')}" if pari("faceoff_pct", "{:.0f}") else None]
            st.caption(periodi)
            st.caption(" · ".join(d for d in dalas if d) + "  (viesi–mājinieki)")
            if et:      # papildlaiks tiek rādīts tikai informācijai, statistikā netiek ieskaitīts
                ot_d = [x for x in (f"metieni {pari('sog_ot')}" if pari("sog_ot") else None,
                                    f"noraidījumi {pari('pen_ot')}" if pari("pen_ot") else None) if x]
                if ot_d:
                    st.caption(f"Papildlaiks ({et}, tikai informācijai): " + " · ".join(ot_d) + "  (viesi–mājinieki)")

            with st.expander("Detaļas"):
                zv = [r.get(f"star{i}") for i in (1, 2, 3)]
                if any(isinstance(z, str) and z for z in zv):
                    st.markdown("**Spēles zvaigznes:** " + " · ".join(
                        f"{i}. {z}" for i, z in enumerate(zv, 1) if isinstance(z, str) and z))
                gid = r["game_id"]
                if ties is not None:
                    tv = ties[(ties["game_id"] == gid) & (ties["loma"] == "referee")]["vards"].tolist()
                    if tv:
                        st.markdown("**Tiesneši:** " + ", ".join(tv))
                if varti is not None:
                    v = varti[varti["game_id"] == gid]
                    if not v.empty:
                        st.markdown("**Vārti**")
                        rtabula(pd.DataFrame({
                            "Per.": v["period"].astype(str) + v["period_type"].map(lambda x: "" if x == "REG" else f" {x}"),
                            "Laiks": v["laiks"], "Komanda": v["komanda"], "Autors": v["scorer"],
                            "Piespēles": (v["assist1"].fillna("") + ", " + v["assist2"].fillna("")).str.strip(", "),
                            "Situācija": v["strength"].str.upper(),
                            "Rez. pēc vārtiem": v["away_score"].astype("Int64").astype(str) + "–" + v["home_score"].astype("Int64").astype(str)}),
                            hide_index=True, width="stretch")
                if sk is not None:
                    s = sk[sk["game_id"] == gid].sort_values(["points", "goals", "sog"], ascending=False).head(6)
                    if not s.empty:
                        st.markdown("**Labākie spēlētāji**")
                        rtabula(s[["vards", "team", "goals", "assists", "points", "sog", "toi"]].rename(columns={
                            "vards": "Spēlētājs", "team": "Komanda", "goals": "G", "assists": "A",
                            "points": "P", "sog": "Metieni", "toi": "TOI spēlē"}), hide_index=True, width="stretch")
                if vg is not None:
                    g = vg[(vg["game_id"] == gid) & (vg["shotsAgainst"].fillna(0) > 0)].copy()
                    if not g.empty:
                        g["SV %"] = (g["saves"] / g["shotsAgainst"] * 100).round(1)
                        st.markdown("**Vārtsargi**")
                        rtabula(g[["vards", "team", "saves", "shotsAgainst", "SV %", "decision"]].rename(columns={
                            "vards": "Vārtsargs", "team": "Komanda", "saves": "Atvairīti",
                            "shotsAgainst": "Metieni pret", "decision": "Iznākums"}), hide_index=True, width="stretch")


# ============================================================================
# LAPA: SPĒLĒTĀJI
# ============================================================================
def lapa_speletaji():
    st.title("Spēlētāji")
    sk = ielasit_papildu("speletaji", VERSIJA)
    vg = ielasit_papildu("vartsargi", VERSIJA)
    if sk is None and vg is None:
        st.info("Spēlētāju dati (dati/speletaji.csv un dati/vartsargi.csv) vēl nav pieejami.")
        return
    t_lauk, t_vart = st.tabs(["Laukuma spēlētāji", "Vārtsargi"])
    komandas = ["Visas komandas"] + sorted(da.KOMANDAS)
    with t_lauk:
        L = da.speletaju_lideri(sk)
        if L.empty:
            st.info("Nav datu.")
        else:
            c1, c2, c3 = st.columns(3)
            kom = c1.selectbox("Komanda", komandas, key="sp_kom",
                               format_func=lambda x: x if x == "Visas komandas" else komandas_etikete(x))
            kartot = c2.selectbox("Kārtot pēc", ["P", "G", "A", "SOG", "PM", "PIM", "HIT", "BLK", "PPG", "TOI", "P_sp"],
                                  key="sp_kart")
            poz = c3.selectbox("Pozīcija", ["Visas", "Uzbrucēji", "Aizsargi"], key="sp_poz")
            if kom != "Visas komandas":
                L = L[L["Komanda"] == kom]
            if poz == "Uzbrucēji":
                L = L[L["Poz"].isin(["C", "L", "R", "W"])]
            elif poz == "Aizsargi":
                L = L[L["Poz"] == "D"]
            rtabula(L.sort_values(kartot, ascending=False).head(60), hide_index=True, width="stretch",
                         column_config={"playerId": None,
                                        "TOI": st.column_config.NumberColumn("TOI (min)", format="%.1f"),
                                        "P_sp": st.column_config.NumberColumn("P/sp", format="%.2f")})
    with t_vart:
        G = da.vartsargu_lideri(vg)
        if G.empty:
            st.info("Nav datu.")
        else:
            c1, c2 = st.columns(2)
            kom = c1.selectbox("Komanda", komandas, key="vg_kom",
                               format_func=lambda x: x if x == "Visas komandas" else komandas_etikete(x))
            min_sp = c2.slider("Minimālais spēļu skaits", 1, 10, 1, key="vg_min")
            if kom != "Visas komandas":
                G = G[G["Komanda"] == kom]
            G = G[G["GP"] >= min_sp]
            rtabula(G.sort_values("SVpct", ascending=False).rename(columns={"TOI": "TOI_kopa"}),
                         hide_index=True, width="stretch",
                         column_config={"playerId": None,
                                        "SVpct": st.column_config.NumberColumn("SV %", format="%.1f"),
                                        "GAA": st.column_config.NumberColumn("GAA", format="%.2f"),
                                        "TOI_kopa": st.column_config.NumberColumn("TOI kopā (min)", format="%.0f")})



# ============================================================================
# LAPA: TIESNEŠI
# ============================================================================
def lapa_tiesnesi():
    st.title("Tiesneši")
    cur, prev, info = ielasit_tiesnesus(VERSIJA)
    if info:
        st.warning(info)
    if cur is None and prev is None:
        st.info("Tiesnešu dati vēl nav pieejami. Tie parādīsies pēc nākamās datu atjaunināšanas "
                "(dati/tiesnesi.csv). Pagājušās sezonas datus liec failā dati/referees_lastseason.csv.")
        return

    with st.expander("Aprēķina iestatījumi", expanded=False):
        c1, c2 = st.columns(2)
        w_prev = c1.slider("Pagājušās sezonas svars (%)", 0, 100, 60, 5, key="ti_w") / 100
        k = c2.slider("Līgas vidējā korekcija K (spēles)", 0, 30, 10, key="ti_k")
        st.caption(f"Kombinētais rādītājs = {w_prev:.0%} × pagājušā sezona + {1 - w_prev:.0%} × šī sezona. "
                   f"Katra sezonas komponente tiek pievilkta pie līgas vidējā, kas vienāds ar {k} spēlēm: "
                   "jaunam tiesnesim vai ar maz spēlēm rādītājs ir tuvu līgas vidējam.")

    tab, liga = da.tiesnesu_apkopojums(cur, prev, w_prev=w_prev, k=k)
    if tab.empty:
        st.info("Nav tiesnešu datu.")
        return
    if prev is None:
        st.caption("Pagājušās sezonas fails (dati/referees_lastseason.csv) nav ielādēts, tāpēc tiek lietota tikai šī sezona.")

    m = st.columns(4)
    m[0].metric("Līgas vidējais šosezon", fmt(liga["t"]["kopa"]), border=True)
    m[1].metric("Līgas vidējais pagājušajā", f"{liga['p']['kopa']:.2f}" if pd.notna(liga["p"]["kopa"]) else "–", border=True)
    m[2].metric("Tiesneši datubāzē", len(tab), border=True)
    m[3].metric("Spēles ar tiesnešiem šosezon",
                0 if cur is None else int(cur.loc[cur["loma"] == "referee", "game_id"].nunique()), border=True)

    t_tab, t_rez, t_spele = st.tabs(["Tiesnešu tabula", "Gaidāmie noraidījumi spēlei", "Tiesneša spēles"])
    with t_tab:
        min_sp = st.slider("Rādīt tiesnešus ar vismaz tik spēlēm (abās sezonās kopā)", 0, 60, 0, key="ti_min")
        t = tab[(tab["GP_t"] + tab["GP_p"]) >= min_sp].sort_values("kopa", ascending=False).reset_index(drop=True)
        vis = pd.DataFrame({
            "Tiesnesis": t["vards"], "Spēles šosezon": t["GP_t"], "Spēles pagājušajā": t["GP_p"],
            "Noraid./sp šosezon": t["kopa_t"], "Noraid./sp pagājušajā": t["kopa_p"],
            "Kombinētais": t["kopa"], "Pret līgu": t["kopa_vs_liga"],
            "Mājas komanda": t["majas"], "Viesu komanda": t["viesi"],
            "Noraid. 1. per.": t["p1"], "Noraid. 2. per.": t["p2"], "Noraid. 3. per.": t["p3"], "Datu apjoms": t["dati"]})
        fm = st.column_config.NumberColumn(format="%.2f")
        rtabula(vis, hide_index=True, width="stretch",
                     height=min(900, 35 * (len(vis) + 1) + 3),
                     column_config={"Noraid./sp šosezon": fm, "Noraid./sp pagājušajā": fm, "Kombinētais": fm,
                                    "Mājas komanda": fm, "Viesu komanda": fm,
                                    "Noraid. 1. per.": fm, "Noraid. 2. per.": fm, "Noraid. 3. per.": fm,
                                    "Pret līgu": st.column_config.NumberColumn(format="%+.2f")})
        st.caption("Noraidījumi = abu komandu sodu skaits spēles pamatlaikā (bez papildlaika un kautiņiem), ko pieskaita katram spēles tiesnesim. "
                   "Datu apjoms: Maz datu < 8 spēles, Vidēji 8–19, Pietiekami 20+ (abas sezonas kopā).")
        with st.expander("Grafiks"):
            g = t.set_index("vards")["kopa"].sort_values()
            fig = go.Figure(go.Bar(x=g.values, y=list(g.index), orientation="h", marker_color="#3b82f6"))
            fig.add_vline(x=liga["blend"]["kopa"], line_dash="dash")
            fig.update_layout(height=max(320, 22 * len(g)), margin=dict(l=10, r=10, t=10, b=10),
                              xaxis_title="Kombinētie noraidījumi spēlē")
            st.plotly_chart(fig)

    with t_rez:
        vardi = tab["vards"].dropna().sort_values().tolist()
        izv = st.multiselect("Spēles tiesneši (parasti divi)", vardi, max_selections=3, key="ti_izv")
        pr = da.tiesnesu_prognoze(tab, liga, izv)
        if not izv:
            st.caption("Nav izvēlēts neviens tiesnesis, tāpēc rādīts līgas kombinētais vidējais.")
        c = st.columns(3)
        c[0].metric("Noraidījumi spēlē kopā", f"{pr['kopa']:.2f}", f"{pr['kopa'] - liga['blend']['kopa']:+.2f} pret līgu",
                    border=True)
        c[1].metric("Mājas komandai", f"{pr['majas']:.2f}", border=True)
        c[2].metric("Viesu komandai", f"{pr['viesi']:.2f}", border=True)
        c = st.columns(3)
        for i, per in enumerate(("p1", "p2", "p3")):
            c[i].metric(f"{i + 1}. periodā", f"{pr[per]:.2f}", f"{pr[per] - liga['blend'][per]:+.2f} pret līgu", border=True)
        st.caption("Šo vērtību vēlāk var padot modelim (da.tiesnesu_prognoze), lai koriģētu noraidījumu prognozi.")

    with t_spele:
        if cur is None:
            st.info("Šosezon vēl nav tiesnešu spēļu.")
        else:
            vards = st.selectbox("Tiesnesis", sorted(cur.loc[cur["loma"] == "referee", "vards"].unique()), key="ti_sel")
            sp = da.tiesnesu_speles(cur, vards)
            rtabula(pd.DataFrame({
                "Datums": pd.to_datetime(sp["datums"]).dt.strftime("%d.%m.%Y"),
                "Spēle": sp["away_team"] + " @ " + sp["home_team"],
                "Noraid. mājas": sp["pen_home"], "Noraid. viesi": sp["pen_away"], "Kopā": sp["pen_total"],
                "PIM min": sp["pim_home"] + sp["pim_away"]}), hide_index=True, width="stretch")

# ============================================================================
# LAPA: KARSTĀKIE SPĒLĒTĀJI
# ============================================================================
def lapa_karstie():
    st.title("Karstākie spēlētāji")
    sk = ielasit_papildu("speletaji", VERSIJA)
    if sk is None:
        st.info("Spēlētāju dati (dati/speletaji.csv) vēl nav pieejami.")
        return

    with st.expander("Kā tiek noteikts, ka spēlētājs ir karsts?"):
        st.markdown(
            "- **Salīdzina ar gaidāmo.** Aprēķina, cik punktu (vārtu / piespēļu) spēlētājam būtu jāiegūst pēdējās N spēlēs, "
            "ņemot vērā viņa iepriekšējo vidējo (pievilktu pie līgas vidējā uzbrucējiem vai aizsargiem, ja spēļu ir maz).\n"
            "- **Karstuma indekss** = (faktiskais − gaidāmais) / √gaidāmais. 0 ir parasts līmenis, 2 un vairāk ir karsts (🔥), 3 un vairāk ir ļoti karsts (🔥🔥). "
            "Indekss ņem vērā izlases lielumu, tāpēc īss uzliesmojums nedod augstu vērtību.\n"
            "- **Vienas spēles nepietiek.** Spēlētājam jābūt vismaz izvēlētajam spēļu skaitam logā un rādītājam jābūt vismaz divās dažādās spēlēs.\n"
            "- **Papildu signāli:** sērija (spēles pēc kārtas ar rādītāju), metienu skaits un šaušanas % (vai rezultāts ir pamatots, vai tā ir veiksme) "
            "un laiks laukumā (vai loma ir augusi).\n"
            "- **Gaidāmais nākamajā spēlē** = 75% sezonas vidējais + 25% pēdējo spēļu vidējais (abi pievilkti pie līgas vidējā). "
            "Hokejā karstumam ir neliela noturība: lielu daļu uzliesmojumu veido veiksme, tāpēc prognoze ir piesardzīga.\n"
            "- Punkti = vārti + piespēles (G+A), tāpēc atsevišķa G+A kolonna nav vajadzīga.")

    max_gp = int(sk.groupby("playerId").size().max())
    c1, c2, c3 = st.columns(3)
    with c1:
        metrika = izvele("Rādītājs", ["Punkti", "Vārti", "Piespēles"], key="ks_m")
    with c2:
        logs_t = izvele("Logs", ["Pēdējās 3", "Pēdējās 5", "Pēdējās 10"], default="Pēdējās 5", key="ks_l")
    with c3:
        min_sp = st.slider("Minimālais spēļu skaits logā", 2, 10, max(2, min(3, max_gp)), key="ks_min",
                           help="Viena spēle nekad netiek ņemta vērā; agrā sezonā logā var būt mazāk spēļu")
    d1, d2 = st.columns(2)
    komandas = ["Visas komandas"] + sorted(da.KOMANDAS)
    kom = d1.selectbox("Komanda", komandas, key="ks_kom",
                       format_func=lambda x: x if x == "Visas komandas" else komandas_etikete(x))
    with d2:
        poz = izvele("Pozīcija", ["Visi", "Uzbrucēji", "Aizsargi"], key="ks_poz")

    mkods = {"Punkti": "punkti", "Vārti": "vardi", "Piespēles": "piespeles"}[metrika]
    nos = {"punkti": "punkti", "vardi": "vārti", "piespeles": "piespēles"}[mkods]
    logs = int(logs_t.split()[-1])
    res = da.karstie_speletaji(sk, mkods, logs, min_sp)
    res = res[res["z"].notna()] if not res.empty else res
    if not res.empty and kom != "Visas komandas":
        res = res[res["Komanda"] == kom]
    if not res.empty and poz != "Visi":
        res = res[res["grupa"] == ("D" if poz == "Aizsargi" else "F")]
    if res.empty:
        st.info("Nav spēlētāju, kas atbilst nosacījumiem (nepietiek spēļu vai rādītājs bijis tikai vienā spēlē). "
                "Pamēģini samazināt minimālo spēļu skaitu vai izvēlēties garāku logu.")
        return
    res = res.head(50)

    ind = f"Karstuma indekss ({nos})"
    vid_w, vid_s = f"{metrika} spēlē logā", f"{metrika} spēlē sezonā"
    gaid = f"Gaidāmie {nos} nākamajā spēlē"
    vis = pd.DataFrame({
        "Spēlētājs": res["Speletajs"].values, "Komanda": res["Komanda"].values, "Poz": res["Poz"].values,
        "Statuss": np.where(res["z"] >= 3, "🔥🔥", np.where(res["z"] >= 2, "🔥", "–")),
        "Sp. logā": res["n_w"].astype(int).values,
        "G": res["G_w"].astype(int).values, "A": res["A_w"].astype(int).values, "P": res["P_w"].astype(int).values,
        vid_w: res["vid_w"].values, vid_s: res["vid_sez"].values,
        "Sērija": res["serija"].astype(int).values,
        ind: res["z"].values, gaid: res["gaidamie_nakamaja"].values,
        "Sezona īsumā": [f"{int(r.GP)} sp · {int(r.G_sez)}G {int(r.A_sez)}A {int(r.P_sez)}P · {int(r.SOG_sez)} metieni"
                         for r in res.itertuples()],
        "Kāpēc karsts": [da.karstuma_teksts(r, mkods) for _, r in res.iterrows()],
    })
    pask = {
        "G": "Vārti izvēlētajā logā", "A": "Piespēles izvēlētajā logā", "P": "Punkti (vārti + piespēles) izvēlētajā logā",
        vid_w: f"Vidēji {nos} spēlē izvēlētajā logā", vid_s: f"Vidēji {nos} spēlē visā sezonā",
        ind: f"Faktiskie {nos} logā pret gaidāmajiem (z-vērtība): 0 = parasts līmenis, 2+ = karsts, 3+ = ļoti karsts. "
             "Netiek rēķināts, ja logā ir pārāk maz spēļu vai rādītājs bijis tikai vienā spēlē",
        gaid: f"Piesardzīgs novērtējums: 75% sezonas vidējais + 25% pēdējo spēļu vidējais ({nos} spēlē), pievilkti pie līgas vidējā",
    }
    rtabula(vis, hide_index=True, width="stretch", height=min(900, 35 * (len(vis) + 1) + 3), paskaidr=pask,
            column_config={vid_w: st.column_config.NumberColumn(format="%.2f"),
                           vid_s: st.column_config.NumberColumn(format="%.2f"),
                           ind: st.column_config.ProgressColumn(ind, min_value=0, max_value=5, format="%.1f"),
                           gaid: st.column_config.NumberColumn(format="%.2f"),
                           "Kāpēc karsts": st.column_config.TextColumn(width="large")})
    st.caption(f"Logs: {logs_t.lower()} (ja spēlētājs nospēlējis mazāk, tiek ņemtas visas viņa spēles). "
               "Sezonas sākumā izlase ir maza, tāpēc rangs var strauji mainīties. Tā ir statistikas indikācija, nevis garantija.")


# ============================================================================
# NAVIGĀCIJA
# Struktūra ir šeit, vienā vietā: lapas var pārvietot starp grupām, grupas pārsaukt vai lapu izvilkt kā atsevišķu pogu
# ({"lapa": (...)} ieraksts bez grupas). Ikonas ir Material Symbols (fonts.google.com/icons).
# ============================================================================
NAV_REZIMS = "pielagots"   # "pielagots" = augšējā josla ar hover izvēlnēm; "standarta" = Streamlit iebūvētā augšējā navigācija

NAV = [
    # atsevišķas pogas joslā (bez izvēlnes)
    {"lapa": (lapa_karstie, "Karstākie spēlētāji", "karstie", "local_fire_department")},
    {"lapa": (lapa_prognozes, "Prognozes", "prognozes", "insights")},
    # grupas ar izvēlni (funkcija, nosaukums, url, Material ikona)
    {"grupa": "Komandas", "lapas": [
        (lapa_parskats, "Līgas pārskats", "parskats", "leaderboard"),
        (lapa_salidzinat, "Salīdzināt komandas", "salidzinat", "compare_arrows"),
        (lapa_komanda, "Komandas statistika", "komanda", "groups"),
    ]},
    {"grupa": "Statistika", "lapas": [
        (lapa_periodi, "Periodi", "periodi", "view_timeline"),
        (lapa_forma, "Forma un vārti", "forma", "trending_up"),
        (lapa_over_under, "Over / Under", "over-under", "swap_vert"),
        (lapa_powerplay, "Powerplay", "powerplay", "bolt"),
        (lapa_noraidijumi, "Noraidījumi", "noraidijumi", "gavel"),
    ]},
    {"grupa": "Spēles", "lapas": [
        (lapa_kalendars, "Kalendārs", "kalendars", "calendar_month"),
        (lapa_rezultati, "Rezultāti", "rezultati", "sports_score"),
    ]},
    {"grupa": "Spēlētāji un tiesneši", "lapas": [
        (lapa_speletaji, "Spēlētāji", "speletaji", "person"),
        (lapa_tiesnesi, "Tiesneši", "tiesnesi", "sports"),
    ]},
]


def _lapa(rec, noklusejuma):
    f, nos, url, ikona = rec
    return st.Page(f, title=nos, icon=f":material/{ikona}:", url_path=url, default=noklusejuma)


STRUKTURA, _pirma = [], True            # [(tips, nosaukums, [(ieraksts, st.Page), ...]), ...]
for _ier in NAV:
    _recs = _ier["lapas"] if "grupa" in _ier else [_ier["lapa"]]
    _lapas = []
    for _rec in _recs:
        _lapas.append((_rec, _lapa(_rec, _pirma)))
        _pirma = False
    STRUKTURA.append(("grupa", _ier["grupa"], _lapas) if "grupa" in _ier else ("lapa", _recs[0][1], _lapas))
VISAS_LAPAS = [p for _, _, saraksts in STRUKTURA for _, p in saraksts]


def augseja_josla(aktiva):
    """Viena josla augšā: zīmols + grupas, kuru lapas parādās, uzvedot peli virsū (vai pieskaroties)."""
    with st.container(key="topbar"):
        with st.container(key="brand"):
            st.page_link(VISAS_LAPAS[0], label="NHL analītika")
        for i, (tips, nosaukums, saraksts) in enumerate(STRUKTURA):
            if tips == "lapa":
                with st.container(key=f"navs-{i}"):
                    st.page_link(saraksts[0][1], label=nosaukums)
                continue
            aktivs = any(p.title == aktiva.title for _, p in saraksts)
            with st.container(key=f"navg-{i}"):
                st.markdown(f'<div class="nav-title{" aktivs" if aktivs else ""}" tabindex="0">{nosaukums}</div>',
                            unsafe_allow_html=True)
                with st.container(key=f"navi-{i}"):
                    for rec, p in saraksts:
                        st.page_link(p, label=rec[1], icon=f":material/{rec[3]}:")


if NAV_REZIMS == "pielagots":
    lapas = st.navigation(VISAS_LAPAS, position="hidden")
    augseja_josla(lapas)
else:
    lapas = st.navigation({n: [p for _, p in s] for t, n, s in STRUKTURA}, position="top")
lapas.run()
