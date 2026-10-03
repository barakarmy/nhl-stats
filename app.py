import hashlib
import hmac
import html as _html
import re
import time
from datetime import timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import datu_apstrade as da
import modelis  # Puasona prognožu modelis

# Neobligātie moduļi: ja fails nav augšupielādēts repozitorijā, lietotne darbojas bez attiecīgās funkcijas (nevis apstājas ar kļūdu)
try:
    import cats          # čata sadaļa
except ImportError:
    cats = None
try:
    import lokacijas     # ceļojuma un atpūtas faktori
except ImportError:
    lokacijas = None
try:
    from fons import FONS_DATA_URI      # lapas fona attēls (ledus ar NHL logo)
except ImportError:
    FONS_DATA_URI = None
try:
    import rulli                        # komandu izvēle ar rullīšiem (salīdzināšanas lapā); bez tā tiek rādītas parastas izvēlnes
except ImportError:
    rulli = None

st.set_page_config(page_title="NHL analītika", page_icon=":material/sports_hockey:", layout="wide",
                   initial_sidebar_state="collapsed")


# ============================================================================
# PAROLE (ieteicams: Streamlit Cloud → Settings → Secrets → APP_PASSWORD = "...")
# ============================================================================
def _parole():
    """Parole tiek ņemta tikai no Streamlit Secrets (kodā tās nav). Atgriež None, ja nav iestatīta."""
    try:
        v = str(st.secrets["APP_PASSWORD"])
        return v or None
    except Exception:
        return None


# Saites uz citām cilnēm: katra jauna cilne ir jauna sesija un prasītu paroli. Tāpēc saitēs, ko lietotne pati izveido (piem., burbuļos), tiek pievienots
# īslaicīgs paraksts t=... (HMAC no derīguma laika ar paroli kā atslēgu; pati parole tajā nav). Jaunā cilne to pārbauda un paraksts tiek noņemts no adreses.
SAITES_ZETONA_STUNDAS = 8


def _auth_zetons(parole, lidz):
    return f"{lidz}.{hmac.new(parole.encode(), f'nhl-saite:{lidz}'.encode(), hashlib.sha256).hexdigest()}"


def _auth_zetons_derigs(zetons, parole):
    try:
        lidz, paraksts = str(zetons).split(".", 1)
        if int(lidz) < time.time():
            return False
        return hmac.compare_digest(paraksts, _auth_zetons(parole, int(lidz)).split(".", 1)[1])
    except Exception:
        return False


def saites_zetons():
    """Derīgs 8-9 stundas (laiks noapaļots uz stundu, lai HTML nemainās katrā izpildē). None, ja parole nav iestatīta."""
    p = _parole()
    return _auth_zetons(p, (int(time.time()) // 3600 + SAITES_ZETONA_STUNDAS + 1) * 3600) if p else None


LOGIN_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600&display=swap');
/* Pieteikšanās ekrāns: fons ir #000066, #000039 un #000024 sajaukums; lauks ir tieši lapas centrā (fiksēts pozicionējums, neatkarīgs no Streamlit izkārtojuma);
   lauks ir tumši pelēks, nedaudz caurspīdīgs; uzraksts "Password" pazūd, uzvedot peli virsū */
.stApp { background: radial-gradient(circle at 50% 45%, rgba(255,255,255,.035), transparent 55%),
                     linear-gradient(135deg, #000066 0%, #000039 50%, #000024 100%) !important; }
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer { display: none !important; }
.stApp .stMainBlockContainer, .stApp [data-testid="stMainBlockContainer"] { padding: 0 !important; max-width: none !important; }

/* lauks: vidū pa horizontāli un vertikāli */
.stApp [data-testid="stTextInput"] { position: fixed !important; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: min(340px, 86vw) !important; z-index: 1000; margin: 0 !important;
  background: rgba(56, 56, 62, .62); border: 1px solid rgba(255,255,255,.16); border-radius: 14px; overflow: hidden;
  -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); box-shadow: 0 12px 34px rgba(0,0,20,.38);
  transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease, background .22s ease; }
/* uz lauka uzvedot peli: lauks mazliet palielinās un kļūst tumšāks (bez gaismas apspīdējuma) */
.stApp [data-testid="stTextInput"]:hover, .stApp [data-testid="stTextInput"]:focus-within {
  transform: translate(-50%, -50%) scale(1.035); border-color: rgba(255,255,255,.22); background: rgba(44, 44, 50, .82);
  box-shadow: 0 18px 42px rgba(0,0,14,.6); }
/* visi iekšējie slāņi caurspīdīgi un bez apmalēm, lai redzams tikai mūsu tumši pelēkais lauks */
.stApp [data-testid="stTextInput"] div, .stApp [data-testid="stTextInput"] input {
  background: transparent !important; background-color: transparent !important; border: none !important; box-shadow: none !important; outline: none !important; }
.stApp [data-testid="stTextInput"] input { height: 3.2rem; text-align: center; color: #ffffff !important; caret-color: #ffffff;
  -webkit-text-fill-color: #ffffff; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; font-size: 1.05rem; letter-spacing: .16em; }
.stApp [data-testid="stTextInput"] input::placeholder { color: rgba(255,255,255,.85) !important; -webkit-text-fill-color: rgba(255,255,255,.85);
  opacity: 1; letter-spacing: .1em; font-weight: 500; transition: color .15s ease, opacity .15s ease; }
/* uz lauka uzvedot peli (vai ieklikšķinot) uzraksts pazūd */
.stApp [data-testid="stTextInput"]:hover input::placeholder, .stApp [data-testid="stTextInput"]:focus-within input::placeholder {
  color: transparent !important; -webkit-text-fill-color: transparent; opacity: 0; }
.stApp [data-testid="stTextInput"] button, .stApp [data-testid="InputInstructions"] { display: none !important; }
.login-err { position: fixed; top: calc(50% + 2.9rem); left: 50%; transform: translateX(-50%); z-index: 1000; white-space: nowrap;
  color: #ffb4b4; font-family: 'Plus Jakarta Sans', system-ui, sans-serif; font-size: .85rem; letter-spacing: .04em; }
</style>"""


def check_password():
    if st.session_state.get("password_correct"):
        return True
    parole = _parole()
    if parole is None:
        st.error("Parole nav iestatīta. Streamlit Cloud → App settings → Secrets pievieno rindu: APP_PASSWORD = \"tava_parole\" "
                 "un spied Save changes (izmaiņas stājas spēkā aptuveni minūtes laikā).")
        return False

    zet = st.query_params.get("t")                       # saite no citas cilnes (burbulis u.c.): derīgs paraksts aizstāj paroles ievadi
    if zet and _auth_zetons_derigs(zet, parole):
        st.session_state["password_correct"] = True
        try:
            del st.query_params["t"]                     # paraksts nepaliek adreses joslā
        except Exception:
            pass
        return True

    def entered():
        ievade = str(st.session_state.get("password", ""))
        st.session_state["password_correct"] = hmac.compare_digest(ievade.encode(), parole.encode())
        st.session_state.pop("password", None)

    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed", on_change=entered, key="password")
    if st.session_state.get("password_correct") is False:
        st.markdown('<div class="login-err">Incorrect password</div>', unsafe_allow_html=True)
    return False


NAV_REZIMS = "pielagots"   # "pielagots" = augšējā josla ar hover izvēlnēm; "standarta" = Streamlit iebūvētā augšējā navigācija

NAV = [
    # atsevišķas pogas joslā (bez izvēlnes)
    {"lapa": ("lapa_karstie", "Karstākie spēlētāji", "karstie", "local_fire_department")},
    {"lapa": ("lapa_prognozes", "Prognozes", "prognozes", "insights")},
    # grupas ar izvēlni (funkcija, nosaukums, url, Material ikona)
    {"grupa": "Komandas", "lapas": [
        ("lapa_parskats", "Līgas pārskats", "parskats", "leaderboard"),
        ("lapa_salidzinat", "Salīdzināt komandas", "salidzinat", "compare_arrows"),
        ("lapa_komanda", "Komandas statistika", "komanda", "groups"),
    ]},
    {"grupa": "Statistika", "lapas": [
        ("lapa_periodi", "Periodi", "periodi", "view_timeline"),
        ("lapa_forma", "Forma un vārti", "forma", "trending_up"),
        ("lapa_over_under", "Over / Under", "over-under", "swap_vert"),
        ("lapa_powerplay", "Powerplay", "powerplay", "bolt"),
        ("lapa_noraidijumi", "Noraidījumi", "noraidijumi", "gavel"),
    ]},
    {"grupa": "Spēlētāji un tiesneši", "lapas": [
        ("lapa_speletaji", "Spēlētāji", "speletaji", "person"),
        ("lapa_tiesnesi", "Tiesneši", "tiesnesi", "sports"),
    ]},
    # beigās atsevišķas sadaļas: Čats, Kalendārs (priekšpēdējais), Rezultāti (pēdējais)
    *([{"lapa": ("lapa_cats", "Čats", "cats", "chat")}] if cats is not None else []),   # tikai, ja ir cats.py
    {"lapa": ("lapa_kalendars", "Kalendārs", "kalendars", "calendar_month")},
    {"lapa": ("lapa_rezultati", "Rezultāti", "rezultati", "sports_score")},
]


def _lazy(funkcijas_nosaukums):
    """Lapas funkcija tiek atrasta pēc nosaukuma izpildes brīdī (funkcijas ir definētas zemāk failā; izpildās tikai pēc pieteikšanās)."""
    def _izsaukt():
        globals()[funkcijas_nosaukums]()
    _izsaukt.__name__ = funkcijas_nosaukums
    return _izsaukt


def _lapa(rec, noklusejuma):
    f, nos, url, ikona = rec
    return st.Page(_lazy(f), title=nos, icon=f":material/{ikona}:", url_path=url, default=noklusejuma)


STRUKTURA, _pirma = [], True            # [(tips, nosaukums, [(ieraksts, st.Page), ...]), ...]
for _ier in NAV:
    _recs = _ier["lapas"] if "grupa" in _ier else [_ier["lapa"]]
    _lapas = []
    for _rec in _recs:
        _lapas.append((_rec, _lapa(_rec, _pirma)))
        _pirma = False
    STRUKTURA.append(("grupa", _ier["grupa"], _lapas) if "grupa" in _ier else ("lapa", _recs[0][1], _lapas))
VISAS_LAPAS = [p for _, _, saraksts in STRUKTURA for _, p in saraksts]



# Navigācija tiek reģistrēta PIRMS paroles pārbaudes: tad adrese (piem., /rezultati?spele=...) tiek saglabāta arī tad, ja vispirms jāievada parole
if NAV_REZIMS == "pielagots":
    lapas = st.navigation(VISAS_LAPAS, position="hidden")
else:
    lapas = st.navigation({n: [p for _, p in s] for t, n, s in STRUKTURA}, position="top")

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

/* ===== Augšējā josla ar hover izvēlnēm (melns fons, gaiši teksti) ===== */
.st-key-topbar { position: sticky; top: .6rem; z-index: 1000; display: flex !important; flex-direction: row !important;
  flex-wrap: wrap; align-items: center; gap: .2rem !important; background: #0a0f1c; border: 1px solid rgba(255,255,255,.10);
  border-radius: 16px; padding: .35rem .7rem; margin-bottom: 1.1rem; box-shadow: 0 10px 28px rgba(0,0,0,.35); }
.st-key-topbar, .st-key-topbar * { overflow: visible !important; }
.st-key-topbar > div, [class*="st-key-navg-"], [class*="st-key-navs-"], .st-key-brand { width: auto !important; }
.st-key-topbar p, .st-key-topbar a, .st-key-topbar .nav-title { font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; }

/* Teksti un ikonas joslā vienmēr skaidri gaiši (netiek mantoti no Streamlit motīva) */
.st-key-topbar a[data-testid="stPageLink-NavLink"], .st-key-topbar a[data-testid="stPageLink-NavLink"] p,
.st-key-topbar a[data-testid="stPageLink-NavLink"] div { color: #e5e7eb !important; opacity: 1 !important; }
.st-key-topbar [data-testid="stIconMaterial"] { color: #cbd5e1 !important; }
.st-key-topbar a[data-testid="stPageLink-NavLink"]:hover, .st-key-topbar a[data-testid="stPageLink-NavLink"]:hover p,
.st-key-topbar a[data-testid="stPageLink-NavLink"]:hover [data-testid="stIconMaterial"] { color: #ffffff !important; }

/* Zīmols */
.st-key-brand { margin-right: .8rem; }
.st-key-brand a[data-testid="stPageLink-NavLink"], .st-key-brand a[data-testid="stPageLink-NavLink"] p { color: #ffffff !important;
  font-weight: 800 !important; font-size: 1.1rem !important; letter-spacing: -0.01em !important; text-decoration: none !important; }
.st-key-brand a[data-testid="stPageLink-NavLink"] { padding: .35rem .6rem !important; background: transparent !important; }

/* Grupu nosaukumi (atver izvēlni uz hover) */
[class*="st-key-navg-"] { position: relative; }
.nav-title { font-weight: 600; font-size: .95rem; color: #e2e8f0; padding: .55rem .95rem; border-radius: 10px; cursor: pointer;
  user-select: none; outline: none; white-space: nowrap; transition: transform .15s ease, background .15s ease, box-shadow .15s ease; }
.nav-title:after { content: ""; display: inline-block; margin-left: .5rem; border: solid currentColor; border-width: 0 1.6px 1.6px 0;
  padding: 2.2px; transform: rotate(45deg) translateY(-2px); opacity: .8; }
.nav-title.aktivs { color: #ffffff; box-shadow: inset 0 -2px 0 #3b82f6; }
[class*="st-key-navg-"]:hover .nav-title, [class*="st-key-navg-"]:focus-within .nav-title { color: #ffffff; background: rgba(255,255,255,.14);
  transform: translateY(-1px) scale(1.06); box-shadow: 0 8px 18px rgba(0,0,0,.5), inset 0 -2px 0 #3b82f6; }

/* Atsevišķās pogas joslā */
[class*="st-key-navs-"] a[data-testid="stPageLink-NavLink"] { padding: .55rem .95rem !important; border-radius: 10px !important;
  transition: transform .15s ease, background .15s ease, box-shadow .15s ease; }
[class*="st-key-navs-"] a[data-testid="stPageLink-NavLink"] p { font-weight: 600 !important; font-size: .95rem !important; color: #e2e8f0 !important; }
[class*="st-key-navs-"] a[data-testid="stPageLink-NavLink"]:hover { background: rgba(255,255,255,.14) !important;
  transform: translateY(-1px) scale(1.06); box-shadow: 0 8px 18px rgba(0,0,0,.5); }
[class*="st-key-navs-"][class*="-akt"] a[data-testid="stPageLink-NavLink"] { background: transparent !important; box-shadow: inset 0 -2px 0 #3b82f6; }
[class*="st-key-navs-"][class*="-akt"] a[data-testid="stPageLink-NavLink"] p { color: #ffffff !important; }

/* Izkrītošā izvēlne */
[class*="st-key-navi-"] { display: none !important; position: absolute; top: 100%; left: 0; min-width: 270px; flex-direction: column;
  gap: .15rem !important; background: #0a0f1c; border: 1px solid rgba(255,255,255,.12); border-radius: 14px; padding: .45rem;
  box-shadow: 0 20px 48px rgba(0,0,0,.6); z-index: 1001; }
[class*="st-key-navg-"][class*="-rr"] [class*="st-key-navi-"] { left: auto; right: 0; }
@media (hover: hover) { [class*="st-key-navg-"]:hover [class*="st-key-navi-"] { display: flex !important; } }
@media (hover: none) { [class*="st-key-navg-"]:focus-within [class*="st-key-navi-"] { display: flex !important; } }
/* pēc saites nospiešanas izvēlne tiek aizvērta (klasi uzliek mazs skripts, kad nospiež saiti joslā) */
.st-key-topbar.nav-aizvert [class*="st-key-navg-"] [class*="st-key-navi-"] { display: none !important; }
/* tukšais konteiners ar skriptu netraucē izkārtojumam */
div[data-testid="stElementContainer"]:has(iframe[height="0"]) { position: absolute; width: 0; height: 0; margin: 0; overflow: hidden; }
[class*="st-key-navi-"] a[data-testid="stPageLink-NavLink"] { padding: .55rem .8rem !important; border-radius: 10px !important;
  transform-origin: left center; transition: transform .15s ease, background .15s ease, box-shadow .15s ease; }
[class*="st-key-navi-"] a[data-testid="stPageLink-NavLink"] p { font-weight: 500 !important; font-size: .95rem !important; color: #e5e7eb !important; }
[class*="st-key-navi-"] a[data-testid="stPageLink-NavLink"]:hover { background: rgba(255,255,255,.14) !important;
  transform: translateX(3px) scale(1.04); box-shadow: 0 6px 16px rgba(0,0,0,.5); }
[class*="st-key-navp-"][class*="-akt"] a[data-testid="stPageLink-NavLink"] { background: #2563eb !important; }
[class*="st-key-navp-"][class*="-akt"] a[data-testid="stPageLink-NavLink"] p,
[class*="st-key-navp-"][class*="-akt"] a[data-testid="stPageLink-NavLink"] [data-testid="stIconMaterial"] { color: #ffffff !important; font-weight: 700 !important; }

/* ===== Spēles kartīte (Rezultāti) ===== */
.mc { display: grid; grid-template-columns: minmax(0,1fr) auto minmax(0,1fr); align-items: center; gap: .9rem; padding: .5rem .2rem 0; }
.mc-team { display: flex; align-items: center; gap: .8rem; min-width: 0; }
.mc-away { justify-content: flex-end; text-align: right; }
.mc-home { justify-content: flex-start; text-align: left; }
.mc-logo { width: 4.6rem; height: 4.6rem; object-fit: contain; flex: 0 0 auto; }
.mc-name { font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; font-size: 1.15rem; font-weight: 500; line-height: 1.2; }
.mc-name.uzv-nos { font-weight: 800; }
.mc-mid { display: flex; flex-direction: column; align-items: center; gap: .45rem; }
.mc-score { display: flex; align-items: center; justify-content: center; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  font-weight: 800; font-size: 3.5rem; line-height: 0; padding: .45rem 0; }
/* rezultāta cipari ir SVG teksts: pamatlīnija un krāsu pāreja nav atkarīgas no fonta metrikas, tāpēc apakšas netiek nogrieztas.
   Pamatlaikā izšķirta spēle - zaļš (uzvarētājs) / sarkans (zaudētājs) pa visu ciparu; spēle ar papildlaiku - apakšā līdz vidum oranžs, augšā līdz vidum zaļš/sarkans */
.mc-score svg { display: block; height: 1em; overflow: visible; }
.mc-score text { font-family: inherit; font-weight: inherit; }
.mc-outcome { font-size: .72rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; padding: .15rem .7rem;
  border-radius: 999px; border: 1px solid rgba(127,127,127,.45); opacity: .85; }
.mc-lines { margin-top: .45rem; text-align: center; font-size: .88rem; opacity: .72; line-height: 1.75; }

/* ===== Rezultāti: datuma josla (iepriekšējā diena / datums / nākamā diena): vienādi, treknraksts, centrēts teksts ===== */
.st-key-datums_josla { display: flex !important; flex-direction: row !important; flex-wrap: wrap; justify-content: center;
  align-items: center; gap: .6rem !important; margin-bottom: .4rem; }
.st-key-datums_josla > div { width: auto !important; flex: 0 0 auto; }
.st-key-datums_josla button { justify-content: center; padding-left: 1.1rem; padding-right: 1.1rem; }
.st-key-datums_josla button, .st-key-datums_josla button p { font-weight: 700 !important; text-align: center; }
.st-key-datums_josla button p { font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; }
/* Datuma lauks: pats Streamlit lauks ir neredzams (opacity 0), bet aizpilda visu rāmīti un saņem klikšķus, tāpēc kalendārs atveras uzreiz;
   redzamo izskatu (balts fons, apmale, centrēts treknraksts) zīmējam mēs, tāpēc tas izskatās kā blakus pogas un nav atkarīgs no Streamlit iekšējās struktūras.
   Datuma tekstu ieliek ::after satura vērtībā (to uzstāda Python katrā izpildē). */
.st-key-datums_lauks { position: relative !important; width: 10rem !important; height: 2.5rem; flex: 0 0 auto; overflow: hidden; box-sizing: border-box;
  background: #ffffff; border: 1px solid rgba(49,51,63,.2); border-radius: 10px; transition: border-color .15s ease; cursor: pointer; }
.st-key-datums_lauks > * { position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important; opacity: 0; }
.st-key-datums_lauks::after { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; pointer-events: none;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; font-size: 1rem; font-weight: 700; letter-spacing: .01em; }
.st-key-datums_lauks:hover, .st-key-datums_lauks:focus-within { border-color: #3b82f6; }
.st-key-nav_skripts { position: absolute !important; width: 0; height: 0; overflow: hidden; margin: 0 !important; padding: 0 !important; }

/* ===== HTML tabula ar uznirstošajiem burbuļiem (spēļu saraksts, uzvedot peli uz "Sp.") ===== */
.tb-wrap { width: 100%; }
.tb { width: 100%; border-collapse: collapse; font-size: .9rem; }
.tb th, .tb td { padding: .45rem .65rem; border-bottom: 1px solid rgba(128,128,128,.22); text-align: right; white-space: nowrap; vertical-align: middle; }
.tb th { font-weight: 600; background: rgba(128,128,128,.08); font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; font-size: .82rem; }
.tb th.l, .tb td.l { text-align: left; }
.tb td.w { white-space: normal; min-width: 20rem; text-align: left; font-size: .85rem; }
.tb tbody tr:hover { background: rgba(59,130,246,.07); }
.tb td.lg { text-align: center; padding: .3rem .5rem; }
.tb img.tb-logo { display: block; margin: 0 auto; width: 38px !important; height: 38px !important; max-width: none !important; object-fit: contain; }
.tb .pb { position: relative; min-width: 88px; height: 1.15rem; border-radius: 6px; overflow: hidden; background: rgba(128,128,128,.2); text-align: center; }
.tb .pb i { position: absolute; inset: 0 auto 0 0; background: rgba(59,130,246,.55); }
.tb .pb b { position: relative; font-size: .78rem; font-weight: 600; line-height: 1.15rem; }
/* burbuļi: izskats un uzvedība kā Streamlit paskaidrojumiem virsrakstos */
.tb .spw, .tb .tbh { position: relative; display: inline-block; }
.tb .spw { cursor: help; border-bottom: 1px dotted rgba(128,128,128,.8); }
.tb .tbh { cursor: help; }
.tb .bubble { display: none; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); margin-top: 6px; z-index: 1500;
  width: max-content; max-width: 21rem; padding: .5rem .75rem; background: #ffffff; color: #31333f; border: 1px solid rgba(49,51,63,.12);
  border-radius: .5rem; box-shadow: 0 .25rem 1rem rgba(0,0,0,.18); font-size: .85rem; font-weight: 400; line-height: 1.55;
  text-align: left; white-space: normal; font-family: 'Inter', system-ui, sans-serif; letter-spacing: 0; text-transform: none; }
.tb .bubble::before { content: ""; position: absolute; left: 0; right: 0; top: -9px; height: 9px; }
.tb th:nth-last-child(-n+3) .bubble { left: auto; right: 0; transform: none; }
.tb .spw:hover .bubble, .tb .tbh:hover .bubble { display: block; }
.tb .bt { display: block; font-weight: 700; margin-bottom: .2rem; }
.tb .bl { display: block; white-space: nowrap; }
.tb .bubble a { color: #2563eb; text-decoration: underline; font-weight: 600; }
.tb .bubble .bpiez { opacity: .75; }
/* šaurs ekrāns vai ierīce bez peles: tabula ritinās horizontāli, burbulis atveras kā apakšējā lapa (fiksēts, tāpēc netiek nogriezts) un paliek atvērts, kamēr lietotājs tajā klikšķina */
@media (max-width: 900px), (hover: none) {
  .tb-wrap { overflow-x: auto; }
  .tb td.tbsp { cursor: pointer; }
  .tb td.tbsp:focus-within .bubble, .tb th:focus-within .bubble { display: block; }      /* pieskāriens atver, kamēr fokuss ir burbulī */
  .tb .bubble, .tb th:nth-last-child(-n+3) .bubble { position: fixed; left: .5rem; right: .5rem; top: auto; bottom: .5rem; transform: none; width: auto; max-width: none;
    max-height: 55vh; overflow-y: auto; margin: 0; z-index: 2000; box-shadow: 0 -.25rem 1.5rem rgba(0,0,0,.28); }
  .tb .bubble::before { display: none; }
}

/* ===== Komandu logo režģis (Komandu statistika): bez rāmjiem, logo centrēti; katrs logo ir klikšķināms pa visu savu laukumu (neredzama poga virsū) ===== */
.st-key-kom_registis { display: grid !important; grid-template-columns: repeat(8, 4.9rem); justify-content: center; justify-items: center; align-items: center;
  gap: .45rem !important; margin: 0 auto 1rem; width: 100%; }
.st-key-kom_registis > div { width: 4.9rem !important; min-width: 0; }
[class*="st-key-kt_"] { position: relative !important; width: 4.9rem; height: 4.9rem; display: flex !important; align-items: center; justify-content: center;
  padding: 0 !important; border: none !important; background: none !important; box-shadow: none !important; cursor: pointer; }
[class*="st-key-kt_"] .kt-logo { opacity: .8; transition: filter .2s ease, transform .2s ease, opacity .2s ease; }       /* blur katram logo uzstādās no Python (attālums līdz izvēlētajam) */
@media (hover: hover) {      /* hover efekti tikai ierīcēs ar peli (uz telefona hover "pielīp" un iOS prasa dubultu pieskārienu) */
  [class*="st-key-kt_"]:hover { z-index: 5; }
  [class*="st-key-kt_"]:hover .kt-logo { filter: none !important; transform: scale(1.15); opacity: 1; }
}
.kt-logo { pointer-events: none; -webkit-user-drag: none; }          /* palielinātais logo nedrīkst nosegt blakus esošo komandu pogas */
[class*="st-key-kt_"] button { touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
[class*="st-key-kt_"][class*="_akt"] { z-index: 4; }
[class*="st-key-kt_"][class*="_akt"] .kt-logo, [class*="st-key-kt_"][class*="_akt"]:hover .kt-logo { transform: scale(1.7); opacity: 1; filter: drop-shadow(0 6px 10px rgba(0,0,0,.32)) !important;
  animation: kt-pulss 5.2s ease-in-out infinite; }
@keyframes kt-pulss { 0%, 100% { transform: scale(1.64); } 50% { transform: scale(1.78); } }          /* minimāla pulsēšana ap 1.7x */
@media (prefers-reduced-motion: reduce) { [class*="st-key-kt_"][class*="_akt"] .kt-logo { animation: none; } }
[class*="st-key-kt_"] > div:first-child { width: 100% !important; line-height: 0; display: flex; justify-content: center; }
[class*="st-key-kt_"] p { margin: 0 !important; }
.st-key-komreg_stils { position: absolute !important; width: 0; height: 0; overflow: hidden; margin: 0 !important; padding: 0 !important; }
/* neredzamā poga aizpilda visu laukumu: visi tās ietinumi (jebkura tipa elementi) tiek izstiepti 100% */
[class*="st-key-kt_"] > div:last-child { position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important; opacity: 0; }
[class*="st-key-kt_"] > div:last-child * { width: 100% !important; height: 100% !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important;
  display: block !important; box-sizing: border-box; }
.kt-logo { width: 3.4rem !important; height: 3.4rem !important; max-width: none !important; object-fit: contain; display: block; margin: 0 auto; }
@media (max-width: 640px) {
  .st-key-kom_registis { grid-template-columns: repeat(4, 4.4rem); }
  .st-key-kom_registis > div, [class*="st-key-kt_"] { width: 4.4rem !important; height: 4.4rem; }
  .kt-logo { width: 3rem !important; height: 3rem !important; }
}
/* izvēlētās komandas nosaukums virs statistikas: centrēts, liels */
.kom-nos { text-align: center; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; font-weight: 800; font-size: 2.7rem; line-height: 1.15;
  letter-spacing: -.01em; margin: 1.1rem 0 1.2rem; }
@media (max-width: 640px) { .kom-nos { font-size: 1.9rem; margin-top: .9rem; } }
/* pēdējā spēle: rezultāts kā saite uz Rezultātu sadaļu */
.st-key-pedeja_spele_josla { display: flex !important; flex-direction: row !important; flex-wrap: wrap; align-items: center; gap: .4rem !important; margin-bottom: .6rem; }
.st-key-pedeja_spele_josla > div { width: auto !important; flex: 0 0 auto; }
.st-key-pedeja_spele_josla button { background: none !important; border: none !important; padding: 0 .2rem !important; min-height: 0 !important;
  color: #2563eb !important; text-decoration: underline; font-weight: 700; }

.st-key-rez_fokuss_kartite { border: 2px solid #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,.18); }

/* ===== Mobilā versija ===== */
@media (max-width: 768px) {
  .stApp .stMainBlockContainer, .stApp [data-testid="stMainBlockContainer"] { padding: .6rem .8rem 3rem .8rem; }
  .stApp h1 { font-size: 1.55rem; margin-bottom: .5rem; }
  .st-key-topbar { top: .3rem; padding: .25rem .35rem; border-radius: 14px; gap: .05rem !important; }
  .st-key-brand { margin-right: .3rem; }
  .st-key-brand a[data-testid="stPageLink-NavLink"], .st-key-brand a[data-testid="stPageLink-NavLink"] p { font-size: 1rem !important; }
  .nav-title { padding: .45rem .6rem; font-size: .85rem; }
  [class*="st-key-navs-"] a[data-testid="stPageLink-NavLink"] { padding: .45rem .6rem !important; }
  [class*="st-key-navs-"] a[data-testid="stPageLink-NavLink"] p { font-size: .85rem !important; }
  /* izvēlne atveras zem joslas pa visu platumu, tāpēc nekad neiet ārpus ekrāna */
  [class*="st-key-navg-"] { position: static !important; }
  [class*="st-key-navi-"], [class*="st-key-navg-"][class*="-rr"] [class*="st-key-navi-"] { left: .35rem; right: .35rem; top: 100%; min-width: 0; width: auto; max-height: 70vh; overflow-y: auto !important; }
  .mc { gap: .4rem; }
  .mc-team { flex-direction: column; gap: .3rem; justify-content: center; text-align: center !important; }
  .mc-away { flex-direction: column-reverse; }
  .mc-logo { width: 3.4rem; height: 3.4rem; }
  .mc-name { font-size: .8rem; }
  .mc-score { font-size: 2.6rem; gap: .35rem; }
  .mc-lines { font-size: .78rem; }
  .cmp-val { width: 56px; font-size: .9rem; }
}

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

def tema():
    """Streamlit lietotnes patiesais motīvs: 'light' / 'dark' (st.context.theme), vai None, ja to nevar noteikt."""
    try:
        t = st.context.theme.type
    except Exception:
        return None
    return t if t in ("light", "dark") else None


def tema_css(tumss_css):
    """CSS, kas jāpiemēro tikai tumšajā motīvā. Ja motīvu var noteikt, izvēlas pēc tā (nevis pēc ierīces iestatījuma); citādi pēc ierīces."""
    t = tema()
    if t == "dark":
        return tumss_css
    if t == "light":
        return ""
    return "@media (prefers-color-scheme: dark) { " + tumss_css + " }"


_tumss_tab = tema_css(".tb .bubble { background: #262730; color: #fafafa; border-color: rgba(250,250,250,.15); } .tb .bubble a { color: #60a5fa; }")
if _tumss_tab:
    st.markdown(f"<style>{_tumss_tab}</style>", unsafe_allow_html=True)

# Lapas fons: ledus ar NHL logo, caurspīdīgs, lai netraucētu lasīt tekstu (gaišajā motīvā 30%, tumšajā 16%).
# Pielāgošana: FONA_CAURSPIDIBA_GAISS / FONA_CAURSPIDIBA_TUMSS (0 = nav redzams, 1 = pilna redzamība).
FONA_CAURSPIDIBA_GAISS, FONA_CAURSPIDIBA_TUMSS = 0.30, 0.16
if FONS_DATA_URI:
    _tumss_fons = tema_css(".stApp::before { opacity: " + str(FONA_CAURSPIDIBA_TUMSS) + "; }")
    st.markdown(f"""<style>
.stApp {{ isolation: isolate; }}
.stApp::before {{ content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background: url("{FONS_DATA_URI}") center / cover no-repeat; opacity: {FONA_CAURSPIDIBA_GAISS}; }}
{_tumss_fons}
.stApp [data-testid="stAppViewContainer"], .stApp [data-testid="stMain"], .stApp section.stMain {{ background: transparent !important; }}
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


def tabula(res, kolonnas, sort_col, ascending=False, config=None, grafiks=True, paskaidr=None, burbuli=None, formati=None, prog=None):
    """Rangu tabula ar logotipiem. res: DataFrame ar indeksu 'komanda'; kolonnas: {iekšējais: virsraksts}.
    Ja norādīti burbuļi (pēdējo 5/10 spēļu saraksti), tabula tiek zīmēta kā HTML ar burbuļiem uz kolonnas "Sp." (formati/prog apraksta izskatu)."""
    if res is None or res.empty:
        st.info("Nav datu šim skatam.")
        return
    if burbuli:
        return tabula_html(res, kolonnas, sort_col, ascending, formati=formati, prog=prog, paskaidr=paskaidr, burbuli=burbuli, grafiks=grafiks)
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
    if lokacijas is None:
        st.info("Ceļojuma modulis nav pieejams: repozitorijā trūkst faila lokacijas.py.")
        return
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


SL_PAMATI = {"Visa sezona": None, "Pēdējās 10": 10, "Pēdējās 5": 5}


def _sl_salidzinat(a, b):
    st.session_state.update(sl_a=a, sl_b=b, sl_rezims="salidzinajums")


def _sl_citas():
    st.session_state["sl_rezims"] = "izvele"


def lapa_salidzinat():
    st.title("Komandu salīdzināšana")
    kodi = sorted(da.KOMANDAS, key=lambda k: da.KOMANDAS[k])
    if "sl_a" not in st.session_state:                       # sākuma izvēle: tuvākā kalendāra spēle (mājinieki kreisajā pusē)
        nak = da.nakamas_speles(KAL, 1)
        if nak is not None and not nak.empty:
            st.session_state["sl_a"], st.session_state["sl_b"] = nak.iloc[0]["majas_komanda"], nak.iloc[0]["viesu_komanda"]
        else:
            st.session_state["sl_a"], st.session_state["sl_b"] = kodi[0], kodi[1]

    # 1) komandu izvēle: rullīši "VS" un poga "Salīdzināt"
    if st.session_state.get("sl_rezims", "izvele") == "izvele":
        a0, b0 = st.session_state["sl_a"], st.session_state["sl_b"]
        if rulli is not None:
            komandas = [{"kods": k, "nos": da.pilns_nosaukums(k), "logo": da.logo_url(k)} for k in kodi]
            kom_a, kom_b = rulli.izvele(komandas, (a0, b0), key="sl_rulli")
        else:                                                # rezerves variants, ja rulli.py nav augšupielādēts
            c1, c2 = st.columns(2)
            kom_a = c1.selectbox("Pirmā komanda", kodi, index=kodi.index(a0), format_func=komandas_etikete, key="sl_sel_a")
            kom_b = c2.selectbox("Otrā komanda", kodi, index=kodi.index(b0), format_func=komandas_etikete, key="sl_sel_b")
        if kom_a == kom_b:
            st.caption("Izvēlies divas dažādas komandas.")
        st.button("Salīdzināt", type="primary", width="stretch", disabled=(kom_a == kom_b), on_click=_sl_salidzinat, args=(kom_a, kom_b), key="sl_poga")
        return

    # 2) salīdzinājums: komandu izvēle ir paslēpta, ir poga "Salīdzināt citas komandas" un laika posma pogas
    home, away = st.session_state["sl_a"], st.session_state["sl_b"]
    st.button("Salīdzināt citas komandas", on_click=_sl_citas, key="sl_citas")
    pamats = izvele("Laika posms", list(SL_PAMATI), default="Visa sezona", key="sl_pamats")
    n = SL_PAMATI[pamats]
    liga = da.kopsavilkums(DF, "Visas", n)
    if home not in liga.index or away not in liga.index:
        st.warning("Vienai no komandām šim skatam vēl nav datu.")
        return
    a, b = liga.loc[home], liga.loc[away]

    h1, h2, h3 = st.columns([4, 1, 4], vertical_alignment="center")
    with h1:
        st.image(da.logo_url(home), width=72)
        st.subheader(f":blue[{da.pilns_nosaukums(home)}]")
        st.caption(f"{int(a['GP'])} spēles · {da.forma(DF[DF['komanda'] == home], 5).iloc[0]}")
    with h2:
        st.markdown("<h3 style='text-align:center;opacity:.5'>VS</h3>", unsafe_allow_html=True)
    with h3:
        st.image(da.logo_url(away), width=72)
        st.subheader(f":orange[{da.pilns_nosaukums(away)}]")
        st.caption(f"{int(b['GP'])} spēles · {da.forma(DF[DF['komanda'] == away], 5).iloc[0]}")

    kol_l, kol_r = st.columns([3, 2])
    with kol_l:
        for grupa, metrikas in SALIDZ_METRIKAS:
            st.markdown(f"<div class='cmp-group'>{grupa.upper()}</div>", unsafe_allow_html=True)
            for nos, k, labak, formats in metrikas:
                salidzinajuma_rinda(nos, a[k], b[k], labak, formats)
    with kol_r:
        nos = [x[0] for x in RADARA_ASIS]
        va, vb = percentiles(liga, home), percentiles(liga, away)
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=va + va[:1], theta=nos + nos[:1], fill="toself", name=home,
                                      line_color="#3b82f6", fillcolor="rgba(59,130,246,0.25)"))
        fig.add_trace(go.Scatterpolar(r=vb + vb[:1], theta=nos + nos[:1], fill="toself", name=away,
                                      line_color="#f97316", fillcolor="rgba(249,115,22,0.25)"))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False)),
                          height=400, margin=dict(l=40, r=40, t=20, b=20), legend=dict(orientation="h"))
        st.plotly_chart(fig)
        st.caption("Reitings pret visām komandām (100 = līgas labākais).")


# ============================================================================
# LAPAS: PERIODI
# ============================================================================
def speles_saite(game_id):
    """Saite uz šīs spēles protokolu lietotnes sadaļā Rezultāti (atveras jaunā cilnē; saitē ir īslaicīgs paraksts, lai nebūtu jāievada parole)."""
    zet = saites_zetons()
    return f"/rezultati?spele={int(game_id)}" + (f"&t={zet}" if zet else "")


def burbula_html(virsraksts, ieraksti):
    """Burbuļa saturs: virsraksts + rindas. ieraksti: [{'teksts', 'saite' (rezultāts), 'url', 'piez'}]."""
    e = _html.escape
    rindas = ""
    for it in ieraksti:
        if it.get("url"):
            saite = f' – <a href="{e(it["url"])}" target="_blank" rel="noopener noreferrer">{e(it["saite"])}</a>'
        else:
            saite = f' – {e(it["saite"])}' if it.get("saite") else ""
        piez = f' <span class="bpiez">{e(it["piez"])}</span>' if it.get("piez") else ""
        rindas += f'<span class="bl">{e(it["teksts"])}{saite}{piez}</span>'
    return f'<span class="bt">{e(virsraksts)}</span>{rindas}'


def spelu_burbuli(scope, n, rez_fn, virsraksts, komandas):
    """
    Katrai komandai burbulis ar pēdējām n spēlēm (jaunākā pirmā): 'vs Pretinieks – (komandas vārti:pretinieka vārti)', rezultāts ir
    pasvītrota saite uz spēles protokolu jaunā cilnē. rez_fn(rinda) atgriež (komandas, pretinieka) skaitļus.
    """
    sub_ = da.filtret(DF, scope, n).sort_values(["komanda", "datums", "game_id"], ascending=[True, False, False])
    out = {}
    for kods, g in sub_.groupby("komanda"):
        if kods not in komandas:
            continue
        ier = []
        for r in g.itertuples():
            x, y = rez_fn(r)
            ier.append({"teksts": f"vs {da.pilns_nosaukums(r.pretinieks)}", "saite": f"({fmt(x, '{:.0f}')}:{fmt(y, '{:.0f}')})",
                        "url": speles_saite(r.game_id)})
        out[kods] = burbula_html(virsraksts, ier)
    return out


def vietas_teksts(scope):
    return {"Mājās": " · mājās", "Izbraukumā": " · izbraukumā"}.get(scope, "")


def tabula_html(res, kolonnas, sort_col, ascending=False, formati=None, prog=None, paskaidr=None, burbuli=None, bur_kol="GP",
                grafiks=True, platas=()):
    """
    Komandu tabula kā HTML (lai varētu rādīt burbuļus, uzvedot peli uz šūnas). Kolonnu virsrakstiem ir paskaidrojumi (kā Streamlit tabulā),
    kolonnai bur_kol (spēļu skaits) - burbulis ar spēļu sarakstu. formati: {iekšējais: '{:.2f}'}, prog: {iekšējais: (min, max)} joslu kolonnām.
    """
    if res is None or res.empty:
        st.info("Nav datu šim skatam.")
        return
    e = _html.escape
    formati, prog, paskaidr, burbuli = formati or {}, prog or {}, paskaidr or {}, burbuli or {}
    t = res.sort_values(sort_col, ascending=ascending, kind="stable")
    galva = '<th>#</th><th></th><th class="l">Komanda</th>'
    for k, label in kolonnas.items():
        h = paskaidr.get(label) or palidziba(label)
        saturs = f'<span class="tbh">{e(label)}<span class="bubble">{e(h)}</span></span>' if h else e(label)
        galva += f'<th{" class=l" if k in platas else ""}>{saturs}</th>'
    rindas = ""
    for i, (kods, r) in enumerate(t.iterrows(), 1):
        rinda = f'<td>{i}</td><td class="lg"><img class="tb-logo" width="38" height="38" src="{e(da.logo_url(kods))}" alt="{e(kods)}"></td><td class="l">{e(da.pilns_nosaukums(kods))}</td>'
        for k in kolonnas:
            v = r[k]
            if k == bur_kol and kods in burbuli:
                rinda += (f'<td class="tbsp" tabindex="0"><span class="spw">{fmt(v, "{:.0f}")}'
                          f'<span class="bubble">{burbuli[kods]}</span></span></td>')
            elif k in prog:
                lo, hi = prog[k]
                platums = 0 if pd.isna(v) else max(0, min(100, (v - lo) / (hi - lo) * 100))
                rinda += f'<td><div class="pb"><i style="width:{platums:.0f}%"></i><b>{fmt(v, formati.get(k, "{:.0f}"))}</b></div></td>'
            elif isinstance(v, str):
                rinda += f'<td class="{"w" if k in platas else "l"}">{e(v)}</td>'
            else:
                rinda += f'<td>{fmt(v, formati.get(k, "{:.0f}"))}</td>'
        rindas += f"<tr>{rinda}</tr>"
    st.markdown(f'<div class="tb-wrap"><table class="tb"><thead><tr>{galva}</tr></thead><tbody>{rindas}</tbody></table></div>', unsafe_allow_html=True)
    if grafiks:
        with st.expander("Grafiks"):
            s = res[sort_col].dropna().sort_values()
            fig = go.Figure(go.Bar(x=s.values, y=list(s.index), orientation="h", marker_color="#3b82f6"))
            fig.update_layout(height=max(320, 22 * len(s)), margin=dict(l=10, r=10, t=10, b=10), xaxis_title=kolonnas.get(sort_col, sort_col))
            st.plotly_chart(fig)


def df_html(df, formati=None, prog=None, paskaidr=None, logo_kol=(), burbuli=None, bur_kol=None, platas=()):
    """
    DataFrame kā HTML tabula ar paskaidrojumiem virsrakstos. logo_kol: kolonnas ar logotipu adresēm; prog: {kolonna: (min, max)} joslām;
    burbuli: HTML saraksts (pa vienam katrai rindai) kolonnai bur_kol (burbulis, uzvedot peli); platas: garo tekstu kolonnas.
    """
    e = _html.escape
    formati, prog, paskaidr = formati or {}, prog or {}, paskaidr or {}
    galva = ""
    for k in df.columns:
        h = paskaidr.get(k) or palidziba(k)
        saturs = f'<span class="tbh">{e(k)}<span class="bubble">{e(h)}</span></span>' if h else e(k)
        galva += f'<th{" class=l" if (isinstance(df[k].iloc[0], str) and k not in logo_kol) else ""}>{saturs}</th>' if len(df) else f"<th>{e(k)}</th>"
    rindas = ""
    for i, (_, r) in enumerate(df.iterrows()):
        rinda = ""
        for k in df.columns:
            v = r[k]
            if k in logo_kol:
                rinda += f'<td class="lg"><img class="tb-logo" width="38" height="38" src="{e(v)}" alt=""></td>'
            elif k == bur_kol and burbuli is not None:
                rinda += f'<td class="tbsp" tabindex="0"><span class="spw">{fmt(v, "{:.0f}")}<span class="bubble">{burbuli[i]}</span></span></td>'
            elif k in prog:
                lo, hi = prog[k]
                platums = 0 if pd.isna(v) else max(0, min(100, (v - lo) / (hi - lo) * 100))
                rinda += f'<td><div class="pb"><i style="width:{platums:.0f}%"></i><b>{fmt(v, formati.get(k, "{:.0f}"))}</b></div></td>'
            elif isinstance(v, str):
                rinda += f'<td class="{"w" if k in platas else "l"}">{e(v)}</td>'
            else:
                rinda += f'<td>{fmt(v, formati.get(k, "{:.0f}"))}</td>'
        rindas += f"<tr>{rinda}</tr>"
    st.markdown(f'<div class="tb-wrap"><table class="tb"><thead><tr>{galva}</tr></thead><tbody>{rindas}</tbody></table></div>', unsafe_allow_html=True)


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
    n_ = LOGI[logs]
    burbuli = None
    if n_ in (5, 10) and not res.empty:        # "Visa sezona": spēļu saraksta burbuļus nerāda
        burbuli = spelu_burbuli(scope, n_, lambda r: (getattr(r, f"g_p{p}"), getattr(r, f"z_p{p}")),
                                f"{p}. periods · pēdējās {n_} spēles{vietas_teksts(scope)} (komanda:pretinieks)", set(res.index))
    tabula(res, {"GP": "Sp.", "G": "Gūti", "Z": "Ielaisti", "Starpiba": "Starpība",
                 "G_sp": "Gūti/sp", "Z_sp": "Ielaisti/sp", "SOG_sp": "Metieni/sp", "SA_sp": "Pretin. metieni/sp"},
           sort_col=kolonna, paskaidr=pask, burbuli=burbuli,
           formati={"G_sp": "{:.2f}", "Z_sp": "{:.2f}", "SOG_sp": "{:.1f}", "SA_sp": "{:.1f}"},
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
    burbuli = spelu_burbuli("Visas", n, lambda r: (r.g_reg, r.z_reg), f"Pēdējās {n} spēles · pamatlaika vārti (komanda:pretinieks)", set(res.index))
    tabula(res, {"GP": "Sp.", "W": "U", "L": "Z", "OTL": "ZPL", "PTS": "Punkti",
                 "G": "Gūti vārti", "Z": "Ielaisti vārti", "Starpiba": "Starpība", "Forma": "Forma"},
           sort_col=kol, ascending=asc, burbuli=burbuli)


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
    n_ = LOGI[logs]
    burbuli = None
    if n_ in (5, 10) and not res.empty:
        burbuli = spelu_burbuli(scope, n_, lambda r: (r.g_reg, r.z_reg),
                                f"Pēdējās {n_} spēles{vietas_teksts(scope)} · pamatlaika vārti (komanda:pretinieks)", set(res.index))
    tabula(res, {"GP": "Sp.", "Over": f"Over {linija}", "Over_pct": "Over %",
                 "Under": f"Under {linija}", "Under_pct": "Under %", "Vid_kopa": "Vid. vārti spēlē"},
           sort_col=kol, burbuli=burbuli, formati={"Vid_kopa": "{:.2f}"}, prog={"Over_pct": (0, 100), "Under_pct": (0, 100)},
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
    n_ = LOGI[logs]
    burbuli = None
    if n_ in (5, 10) and not res.empty:
        burbuli = spelu_burbuli(scope, n_, lambda r: (r.ppg, r.ppg_allowed),
                                f"Pēdējās {n_} spēles{vietas_teksts(scope)} · vairākuma vārti (par:pret)", set(res.index))
    tabula(res, {"GP": "Sp.", "PPG": "PP vārti", "PP_opp": "PP iespējas", "PP_pct": "PP %",
                 "PP_sog": "PP metieni", "PPG_pret": "Ielaisti PP", "PK_pct": "PK %"},
           sort_col=kol, burbuli=burbuli, formati={"PP_pct": "{:.1f}", "PK_pct": "{:.1f}"},
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
def _izvelet_komandu(atslega, kods):
    st.session_state[atslega] = kods


def kom_blur_css(kodi, izv):
    """
    CSS, kas katram neizvēlētajam logo uzliek blur: jo tuvāk izvēlētajam logo (attālums režģī), jo spēcīgāks blur (3.5 px pie blakus esošā,
    pakāpeniski līdz 0.8 px tālu no tā). Atsevišķi aprēķināts 8 kolonnu (dators) un 4 kolonnu (telefons) izkārtojumam.
    """
    i0 = kodi.index(izv)

    def px(i, kol):
        dr, dc = i // kol - i0 // kol, i % kol - i0 % kol
        d = (dr * dr + dc * dc) ** 0.5
        return 0.8 + 2.7 * max(0.0, 1 - (d - 1) / 6)

    def noteikumi(kol):
        return " ".join(f'[class*="st-key-kt_{k}"] .kt-logo {{ filter: blur({px(i, kol):.2f}px); }}' for i, k in enumerate(kodi) if k != izv)
    return f"<style>{noteikumi(8)} @media (max-width: 640px) {{ {noteikumi(4)} }}</style>"


def mobila_ierice():
    """True, ja lietotne atvērta telefonā/planšetē (pēc User-Agent). Tur nav peles, tāpēc 'help' burbuļi pēc pieskāriena paliek redzami un nosedz citus elementus."""
    try:
        ua = st.context.headers.get("User-Agent", "") or ""
    except Exception:
        return False
    return bool(re.search(r"Mobi|Android|iPhone|iPad|iPod", str(ua)))


def komandu_registis(atslega="kom_izv"):
    """Visu NHL komandu logo režģis (8x4): klikšķis uz logo izvēlas komandu. Atgriež izvēlētās komandas kodu."""
    kodi = sorted(da.KOMANDAS, key=lambda k: da.KOMANDAS[k])
    izv = st.session_state.setdefault(atslega, kodi[0])
    mob = mobila_ierice()
    with st.container(key="komreg_stils"):
        st.markdown(kom_blur_css(kodi, izv), unsafe_allow_html=True)
    with st.container(key="kom_registis"):
        for kods in kodi:
            with st.container(key=f"kt_{kods}" + ("_akt" if kods == izv else "")):
                st.markdown(f'<img class="kt-logo" src="{_html.escape(da.logo_url(kods))}" alt="{kods}">', unsafe_allow_html=True)
                st.button(kods, key=f"ktb_{kods}", help=None if mob else da.pilns_nosaukums(kods), on_click=_izvelet_komandu, args=(atslega, kods))
    return st.session_state[atslega]


def _lapa_pec_nosaukuma(nosaukums):
    return next((p for p in VISAS_LAPAS if p.title == nosaukums), None)


def lapa_komanda():
    kom = komandu_registis()
    tdf = DF[DF["komanda"] == kom]
    if tdf.empty:
        st.warning("Šai komandai vēl nav datu.")
        return
    st.markdown(f'<div class="kom-nos">{_html.escape(da.pilns_nosaukums(kom))}</div>', unsafe_allow_html=True)

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
        pedeja = lg.iloc[0]                                              # jaunākā spēle
        gid = int(pedeja["game_id"])
        dat_lv = RAW.set_index("game_id")["datums_lv"].get(gid, pedeja["datums"])
        rez_txt = f"{int(pedeja['g_tot'])}–{int(pedeja['z_tot'])}" + (f" {da.beigu_etikete(pedeja['beigas'])}" if da.beigu_etikete(pedeja["beigas"]) else "")
        with st.container(key="pedeja_spele_josla"):
            st.markdown(f"**Pēdējā spēle** · {pd.Timestamp(dat_lv):%d.%m.%Y} · {'vs' if pedeja['majas'] == 1 else '@'} {da.pilns_nosaukums(pedeja['pretinieks'])} ·")
            try:
                atvert = st.button(rez_txt, key="pedeja_spele_saite", type="tertiary", help="Atvērt šīs dienas spēles sadaļā Rezultāti")
            except TypeError:
                atvert = st.button(rez_txt, key="pedeja_spele_saite", help="Atvērt šīs dienas spēles sadaļā Rezultāti")
        if atvert and _lapa_pec_nosaukuma("Rezultāti") is not None:
            st.session_state["rez_datums_pending"] = pd.Timestamp(dat_lv).date()
            st.session_state["rez_fokuss"] = gid
            st.switch_page(_lapa_pec_nosaukuma("Rezultāti"))
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
    st.caption("Galvenos tiesnešus pirms spēlēm paziņo apmēram 4 stundas pirms dienas pirmās spēles. Dati: Scouting The Refs "
               "(scoutingtherefs.com) un NHL.")
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
def _rezultata_svg(at, ht, kl_a, kl_h, uid):
    """
    Rezultāts 'viesi : mājinieki' kā viens SVG (1 vienība = 1 em). Pamatlīnija ir y=0.84, cipara augša ~y=0.12, vidus ~y=0.48,
    tāpēc krāsu pārejas "no apakšas līdz vidum" un "no augšas līdz vidum" nav atkarīgas no fonta metrikas.
    kl: ("reg", "uzv"/"zaud") = krāsa pa visu ciparu; ("ot", "uzv"/"zaud"/"") = apakšā oranžs, augšā zaļš/sarkans.
    """
    KRASAS = {"uzv": (34, 197, 94), "zaud": (239, 68, 68), "oranzs": (245, 158, 11)}
    PAMATLINIJA, AUGSA, VIDUS = 0.84, 0.12, 0.48
    cipara_platums, kols, sprauga = 0.66, 0.3, 0.12
    wa, wh = cipara_platums * len(str(at)), cipara_platums * len(str(ht))
    W = wa + wh + kols + 2 * sprauga
    xa, xk, xh = wa / 2, wa + sprauga + kols / 2, wa + 2 * sprauga + kols + wh / 2

    def gradients(gid, krasa, rezims):
        r, g, b = KRASAS[krasa]
        c = f"rgb({r},{g},{b})"
        if rezims == "pilns":           # no apakšas (nepārtraukts) uz augšu (38%)
            return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{PAMATLINIJA + .02}" x2="0" y2="{AUGSA}">'
                    f'<stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="1" stop-color="{c}" stop-opacity=".38"/></linearGradient>')
        gala = AUGSA if rezims == "augsa" else PAMATLINIJA + .02          # "augsa": no augšas līdz vidum; "apakssa": no apakšas līdz vidum
        return (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{gala}" x2="0" y2="{VIDUS}">'
                f'<stop offset="0" stop-color="{c}" stop-opacity="1"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient>')

    defs, teksti = "", ""
    for nos, x, vert, (tips, rez) in (("a", xa, at, kl_a), ("h", xh, ht, kl_h)):
        teksti += f'<text x="{x:.3f}" y="{PAMATLINIJA}" text-anchor="middle" font-size="1" fill="currentColor">{vert}</text>'
        if tips == "reg":
            gid = f"{uid}{nos}f"
            defs += gradients(gid, rez, "pilns")
            teksti += f'<text x="{x:.3f}" y="{PAMATLINIJA}" text-anchor="middle" font-size="1" fill="url(#{gid})">{vert}</text>'
        else:
            gb = f"{uid}{nos}b"
            defs += gradients(gb, "oranzs", "apakssa")
            teksti += f'<text x="{x:.3f}" y="{PAMATLINIJA}" text-anchor="middle" font-size="1" fill="url(#{gb})">{vert}</text>'
            if rez:
                gt = f"{uid}{nos}t"
                defs += gradients(gt, rez, "augsa")
                teksti += f'<text x="{x:.3f}" y="{PAMATLINIJA}" text-anchor="middle" font-size="1" fill="url(#{gt})">{vert}</text>'
    kolons = f'<text x="{xk:.3f}" y="{PAMATLINIJA}" text-anchor="middle" font-size="1" fill="currentColor" fill-opacity=".6">:</text>'
    return (f'<svg viewBox="0 0 {W:.3f} 1" style="width:{W:.3f}em" role="img" aria-label="{at} : {ht}" xmlns="http://www.w3.org/2000/svg">'
            f'<defs>{defs}</defs>{teksti}{kolons}</svg>')


def rez_kartite_html(away, home, at, ht, ra, rh, iznakums, linijas, uid="g"):
    """
    Spēles kartītes augša: [viesu nosaukums][logo] [rezultāts + iznākums] [logo][mājinieku nosaukums] un centrētas statistikas rindas.
    Ciparu krāsas: pamatlaikā izšķirta spēle - uzvarētājs zaļš, zaudētājs sarkans (pa visu ciparu);
    spēle ar papildlaiku (pamatlaikā neizšķirts) - cipara apakšējā puse oranža, augšējā puse zaļa/sarkana (galīgais uzvarētājs/zaudētājs).
    """
    if ra != rh:                                              # izšķirta pamatlaikā
        kl_a, kl_h = (("reg", "uzv"), ("reg", "zaud")) if ra > rh else (("reg", "zaud"), ("reg", "uzv"))
    elif at == ht:                                            # neizšķirts arī galarezultātā (nav gaidāms)
        kl_a = kl_h = ("ot", "")
    else:                                                     # papildlaiks / pēcspēles metieni
        kl_a, kl_h = (("ot", "uzv"), ("ot", "zaud")) if at > ht else (("ot", "zaud"), ("ot", "uzv"))
    e = _html.escape
    return (
        '<div class="mc">'
        f'<div class="mc-team mc-away"><span class="mc-name{" uzv-nos" if at > ht else ""}">{e(da.pilns_nosaukums(away))}</span>'
        f'<img class="mc-logo" src="{e(da.logo_url(away))}" alt="{e(away)}"></div>'
        '<div class="mc-mid">'
        f'<div class="mc-score">{_rezultata_svg(at, ht, kl_a, kl_h, "g" + str(uid))}</div>'
        f'<div class="mc-outcome">{e(iznakums)}</div></div>'
        f'<div class="mc-team mc-home"><img class="mc-logo" src="{e(da.logo_url(home))}" alt="{e(home)}">'
        f'<span class="mc-name{" uzv-nos" if ht > at else ""}">{e(da.pilns_nosaukums(home))}</span></div>'
        '</div>'
        '<div class="mc-lines">' + "".join(f"<div>{e(x)}</div>" for x in linijas if x) + '</div>')


def lapa_rezultati():
    st.title("Spēļu rezultāti")
    datumi = RAW["datums_lv"].dt.date
    mind, maxd = datumi.min(), max(datumi.max(), da.sodien_lv())
    if "rez_datums" not in st.session_state:
        st.session_state["rez_datums"] = min(da.sodien_lv(), datumi.max())
    qp = st.query_params.get("spele")                              # saite no burbuļa: /rezultati?spele=ID
    if qp and st.session_state.get("rez_qp_apstradats") != qp:
        st.session_state["rez_qp_apstradats"] = qp
        try:
            rinda_ = RAW[RAW["game_id"] == int(qp)]
            if not rinda_.empty:
                st.session_state["rez_datums_pending"] = rinda_.iloc[0]["datums_lv"].date()
                st.session_state["rez_fokuss"] = int(qp)
        except (TypeError, ValueError):
            pass
    if "rez_datums_pending" in st.session_state:                  # pāreja no citas lapas vai saites (piem., komandas pēdējā spēle)
        st.session_state["rez_datums"] = min(max(st.session_state.pop("rez_datums_pending"), mind), maxd)

    def nobide(dienas):
        st.session_state["rez_datums"] = min(max(st.session_state["rez_datums"] + timedelta(days=dienas), mind), maxd)
        st.session_state.pop("rez_fokuss", None)

    with st.container(key="datums_josla"):       # kompakta josla pa lapas vidu: tikai tik plata, cik vajag tekstam
        st.button("❮ Iepriekšējā diena", on_click=nobide, args=(-1,))
        # datums: redzamo izskatu zīmē CSS (::after), pats Streamlit lauks ir neredzams un aizpilda rāmīti, tāpēc kalendārs atveras uzreiz
        with st.container(key="datums_lauks"):
            st.date_input("Datums", min_value=mind, max_value=maxd, key="rez_datums", format="DD.MM.YYYY",
                          label_visibility="collapsed")
        st.button("Nākamā diena ❯", on_click=nobide, args=(1,))

    dat = st.session_state["rez_datums"]
    _tumss_lauks = tema_css(".st-key-datums_lauks { background: #0e1117; border-color: rgba(250,250,250,.2); }")
    st.markdown(f"<style>.st-key-datums_lauks::after {{ content: '{dat:%d.%m.%Y}'; }} {_tumss_lauks}</style>", unsafe_allow_html=True)
    st.markdown(f"#### {da.DIENAS[dat.weekday()]}, {dat:%d.%m.%Y}")
    dienas_speles = RAW[datumi == dat].sort_values(["sakums_lv", "game_id"])
    if dienas_speles.empty:
        st.info("Šajā datumā nav noslēgušos spēļu.")
        return
    fokuss = st.session_state.get("rez_fokuss")
    if fokuss is not None and (dienas_speles["game_id"] == fokuss).any():        # izvēlētā spēle ir pirmā, izcelta un ar atvērtām detaļām
        dienas_speles = pd.concat([dienas_speles[dienas_speles["game_id"] == fokuss], dienas_speles[dienas_speles["game_id"] != fokuss]])
    else:
        fokuss = None

    varti = ielasit_papildu("varti", VERSIJA)
    sk = ielasit_papildu("speletaji", VERSIJA)
    vg = ielasit_papildu("vartsargi", VERSIJA)
    ties = ielasit_papildu("tiesnesi", VERSIJA)

    for _, r in dienas_speles.iterrows():
        home, away = r["home_team"], r["away_team"]
        ht, at = int(r["home_total"]), int(r["away_total"])
        et = da.beigu_etikete(r["spele_beidzas"])
        ir_fokuss = fokuss is not None and r["game_id"] == fokuss
        with (st.container(border=True, key="rez_fokuss_kartite") if ir_fokuss else st.container(border=True)):
            periodi = " · ".join(f"{p}P {int(r[f'away_p{p}'])}:{int(r[f'home_p{p}'])}" for p in (1, 2, 3))
            if (r.get("home_ot", 0) or 0) + (r.get("away_ot", 0) or 0) > 0:
                periodi += f" · OT/SO {int(r['away_ot'])}:{int(r['home_ot'])}"

            def pari(nos, formats="{:.0f}"):
                a_, h_ = r.get(f"away_{nos}"), r.get(f"home_{nos}")
                return None if pd.isna(a_) or pd.isna(h_) else f"{formats.format(a_)}–{formats.format(h_)}"

            pen_a = r.get("away_pen_count")
            pen_h = r.get("home_pen_count")
            if pd.isna(pen_a) or pd.isna(pen_h):
                pen_a, pen_h = round(r["away_pim_total"] / 2), round(r["home_pim_total"] / 2)
            dalas = [f"Metieni {pari('sog_total')}", f"Noraidījumi {int(pen_a)}–{int(pen_h)}",
                     f"PP vārti {pari('ppg')}", f"Hits {pari('hits')}" if pari("hits") else None,
                     f"Iemetieni % {pari('faceoff_pct', '{:.0f}')}" if pari("faceoff_pct", "{:.0f}") else None]
            linijas = [periodi, " · ".join(d for d in dalas if d) + "  (viesi–mājinieki)"]
            if et:      # papildlaiks tiek rādīts tikai informācijai, statistikā netiek ieskaitīts
                ot_d = [x for x in (f"metieni {pari('sog_ot')}" if pari("sog_ot") else None,
                                    f"noraidījumi {pari('pen_ot')}" if pari("pen_ot") else None) if x]
                if ot_d:
                    linijas.append(f"Papildlaiks ({et}, tikai informācijai): " + " · ".join(ot_d) + "  (viesi–mājinieki)")
            ra = int(sum(r[f"away_p{p}"] for p in (1, 2, 3)))
            rh = int(sum(r[f"home_p{p}"] for p in (1, 2, 3)))
            st.markdown(rez_kartite_html(away, home, at, ht, ra, rh, et or "Pamatlaiks", linijas, uid=r["game_id"]), unsafe_allow_html=True)

            with st.expander("Detaļas", expanded=ir_fokuss):
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
          