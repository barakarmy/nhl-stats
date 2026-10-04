import datetime
import hashlib
import hmac
import html as _html
import os
import re
import tempfile
import time
import zlib
from datetime import timedelta

import numpy as np
import pandas as pd
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


# Pieteikšanās atcerēšanās pēc lapas atsvaidzināšanas: pēc paroles ievades pārlūka localStorage tiek saglabāts paraksts (HMAC no derīguma
# laika ar paroli kā atslēgu; pati parole tajā nav). Jaunā sesijā (refresh, jauna cilne) mazs komponents to nolasa un nodod Python, kas to pārbauda.
# localStorage nav atkarīgs no sīkdatnēm un Streamlit Cloud starpniekservera; paraksts nav redzams adresē. Paroles maiņa visus parakstus anulē.
ATCERETIES_DIENAS = 30
_AUTH_HTML = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0"><script>
(function () {
  var NOS = 'nhl_auth', atbildets = false;
  function send(t, d) { window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: t }, d), '*'); }
  window.addEventListener('message', function (ev) {
    if (!ev.data || ev.data.type !== 'streamlit:render') return;
    var a = ev.data.args || {};
    try { if (a.rakstit) localStorage.setItem(NOS, a.rakstit); } catch (e) {}
    if (a.lasit && !atbildets) {
      atbildets = true;
      var v = '';
      try { v = localStorage.getItem(NOS) || ''; } catch (e) {}
      send('streamlit:setComponentValue', { value: v, dataType: 'json' });
    }
    send('streamlit:setFrameHeight', { height: 0 });
  });
  send('streamlit:componentReady', { apiVersion: 1 });
})();
</script></body></html>"""


@st.cache_resource(show_spinner=False)
def _auth_komponents():
    """Komponents deklarēts vienreiz uz procesu; mapes nosaukums satur satura jaucējkodu (pārlūks neizmanto veco versiju)."""
    import streamlit.components.v1 as components
    h = hashlib.md5(_AUTH_HTML.encode("utf-8")).hexdigest()[:10]
    mape = os.path.join(tempfile.gettempdir(), f"nhl_auth_{h}")
    os.makedirs(mape, exist_ok=True)
    fails = os.path.join(mape, "index.html")
    if not os.path.exists(fails):
        with open(fails, "w", encoding="utf-8") as f:
            f.write(_AUTH_HTML)
    return components.declare_component(f"nhl_auth_{h}", path=mape)


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
.st-key-auth_lasit, .st-key-auth_krat { position: absolute !important; width: 0; height: 0; overflow: hidden; margin: 0 !important; }
/* kamēr pārlūks vēl nav atbildējis par saglabāto pieteikšanos, paroles lauks parādās ar nelielu aizkavi (lai pēc refresh tas nemirgo) */
.login-gaida [data-testid="stTextInput"], .stApp:has(.login-gaida) [data-testid="stTextInput"] { animation: login-paradit .25s ease 1.3s both; }
@keyframes login-paradit { from { opacity: 0; } to { opacity: 1; } }
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
        st.session_state["_auth_zetons"] = _auth_zetons(parole, int(time.time()) + ATCERETIES_DIENAS * 86400)
        try:
            del st.query_params["t"]                     # paraksts nepaliek adreses joslā
        except Exception:
            pass
        return True

    saglabats = None                                     # atcerētā pieteikšanās no pārlūka (localStorage); None = pārlūks vēl nav atbildējis
    try:
        with st.container(key="auth_lasit"):
            saglabats = _auth_komponents()(lasit=True, key="nhl_auth_lasit", default=None)
    except Exception:
        saglabats = ""
    if isinstance(saglabats, str) and saglabats and _auth_zetons_derigs(saglabats, parole):
        st.session_state["password_correct"] = True
        st.session_state["_auth_zetons"] = _auth_zetons(parole, int(time.time()) + ATCERETIES_DIENAS * 86400)     # termiņš tiek atjaunots
        return True

    def entered():
        ievade = str(st.session_state.get("password", ""))
        st.session_state["password_correct"] = hmac.compare_digest(ievade.encode(), parole.encode())
        if st.session_state["password_correct"]:
            st.session_state["_auth_zetons"] = _auth_zetons(parole, int(time.time()) + ATCERETIES_DIENAS * 86400)
        st.session_state.pop("password", None)

    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    if saglabats is None:
        st.markdown('<div class="login-gaida"></div>', unsafe_allow_html=True)
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
        globals()["_TABULU_SKAITS"][0] = 0                # tabulu numerācija katrā lapas izpildē sākas no jauna (stabilas kārtošanas atslēgas)
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

if st.session_state.get("_auth_zetons"):
    try:
        with st.container(key="auth_krat"):
            _auth_komponents()(rakstit=st.session_state["_auth_zetons"], key="nhl_auth_rakstit", default=None)
    except Exception:
        pass


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
.st-key-auth_krat { position: absolute !important; width: 0; height: 0; overflow: hidden; margin: 0 !important; padding: 0 !important; }
.st-key-nav_skripts { position: absolute !important; width: 0; height: 0; overflow: hidden; margin: 0 !important; padding: 0 !important; }

/* ===== HTML tabula ar uznirstošajiem burbuļiem (spēļu saraksts, uzvedot peli uz "Sp.") ===== */
.tb-wrap { width: 100%; }
.tb { width: 100%; border-collapse: collapse; font-size: .9rem; }
.tb th, .tb td { padding: .45rem .65rem; border-bottom: 1px solid rgba(128,128,128,.22); text-align: right; white-space: nowrap; vertical-align: middle; }
.tb th { font-weight: 600; background: transparent; border-bottom: 2px solid rgba(128,128,128,.4); font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; font-size: .82rem; }
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
  .tb .bubble, .tb th:nth-last-child(-n+3) .bubble { position: fixed; left: .5rem; right: .5rem; top: auto; bottom: calc(4rem + env(safe-area-inset-bottom, 0px)); transform: none; width: auto; max-width: none;
    max-height: 55vh; overflow-y: auto; margin: 0; z-index: 2000; box-shadow: 0 -.25rem 1.5rem rgba(0,0,0,.28); }
  .tb .bubble::before { display: none; }
}

/* ===== Tabulas: kārtošanas izvēlne (⇅ Kārtot), pielīpošais virsraksts un pirmā kolonna ===== */
[class*="st-key-tbs_"] { display: flex !important; flex-direction: row !important; justify-content: flex-end; margin-bottom: -.35rem; }
[class*="st-key-tbs_"] > div { width: auto !important; flex: 0 0 auto; }
[class*="st-key-tbs_"] button { background: linear-gradient(135deg, #18233d 0%, #0a0f1c 100%) !important; border: 1px solid rgba(255,255,255,.12) !important;
  border-radius: 999px !important; min-height: 2rem; padding: .2rem .95rem !important; box-shadow: 0 4px 12px rgba(10,15,28,.22); }
[class*="st-key-tbs_"] button p, [class*="st-key-tbs_"] button span { color: #e2e8f0 !important; font-weight: 600 !important; font-size: .84rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; }
[class*="st-key-tbs_"] button svg, [class*="st-key-tbs_"] button [data-testid="stIconMaterial"] { color: #e2e8f0 !important; fill: #e2e8f0 !important; }
.tbm-lab { font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; opacity: .6; margin: .1rem 0 -.2rem .1rem; }
[class*="st-key-tbm_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[class*="st-key-tbmk_"], [class*="st-key-tbmd_"] { display: flex !important; flex-direction: row !important; flex-wrap: wrap; gap: .35rem !important; max-width: 22rem; }
[class*="st-key-tbmk_"] > div, [class*="st-key-tbmd_"] > div { width: auto !important; flex: 0 0 auto; }
[class*="st-key-tbmk_"] button, [class*="st-key-tbmd_"] button { border-radius: 999px !important; min-height: 1.9rem; padding: .1rem .75rem !important;
  border: 1px solid rgba(128,128,128,.3) !important; background: transparent !important; }
[class*="st-key-tbmk_"] button p, [class*="st-key-tbmd_"] button p { font-size: .8rem; font-weight: 600 !important; }
[class*="st-key-tbmk_"] button[data-testid="stBaseButton-primary"], [class*="st-key-tbmk_"] button[kind="primary"],
[class*="st-key-tbmd_"] button[data-testid="stBaseButton-primary"], [class*="st-key-tbmd_"] button[kind="primary"] {
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%) !important; border-color: rgba(147,197,253,.5) !important; }
[class*="st-key-tbmk_"] button[data-testid="stBaseButton-primary"] p, [class*="st-key-tbmk_"] button[kind="primary"] p,
[class*="st-key-tbmd_"] button[data-testid="stBaseButton-primary"] p, [class*="st-key-tbmd_"] button[kind="primary"] p { color: #fff !important; }
/* virsraksta rinda pielīp: datorā lapas augšā (zem pielipušās joslas), garām tabulām telefonā - tabulas lodziņa augšā */
.tb thead th { position: sticky; top: var(--tb-top, 0px); z-index: 3; background: #eef3f9; }          /* necaurspīdīgs, lai zem tā ritinātais saturs neparādās */
.tb td.c0, .tb th.c0, .tb td.c1, .tb th.c1 { position: sticky; z-index: 2; background: #eef3f9; }
.tb th.c0, .tb th.c1 { z-index: 4; }
.tb td.c0, .tb th.c0 { left: 0; }
.tb td.c0:has(+ td.c1), .tb th.c0:has(+ th.c1) { width: 2.3rem; min-width: 2.3rem; max-width: 2.3rem; box-sizing: border-box; padding-left: .3rem; padding-right: .3rem; }
.tb td.c1, .tb th.c1 { left: 2.3rem; box-shadow: 1px 0 0 rgba(128,128,128,.25); }
.tb td.c0:not(:has(+ td.c1)), .tb th.c0:not(:has(+ th.c1)) { box-shadow: 1px 0 0 rgba(128,128,128,.25); }
@media (max-width: 900px), (hover: none) {
  .tb-wrap.garsa { max-height: 72vh; overflow: auto; overscroll-behavior: contain; border-bottom: 1px solid rgba(128,128,128,.25); }
  .tb thead th { top: 0; }
  .tb td.c0:not(:has(+ td.c1)), .tb th.c0:not(:has(+ th.c1)) { max-width: 8.5rem; white-space: normal; }
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

/* ===== Visas filtru / kārtošanas pogas: tumšas noapaļotas pogas (kā "Salīdzināt"), aktīvā zilā ===== */
[class*="st-key-pg_"] { gap: .35rem !important; }
[class*="st-key-pg_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }      /* Streamlit noklusējums -1rem lika uzrakstam uzbraukt pogām */
.pg-lab { font-size: .78rem; font-weight: 600; opacity: .7; margin: 0 0 .05rem .15rem; }
[class*="st-key-pgr_"], .st-key-sl_per, .st-key-cmp_vh, .st-key-cmp_va { display: flex !important; flex-direction: row !important; flex-wrap: wrap; gap: .4rem !important; }
[class*="st-key-pgr_"] > div, .st-key-sl_per > div, .st-key-cmp_vh > div, .st-key-cmp_va > div { width: auto !important; flex: 0 0 auto; }
[class*="st-key-pgr_"] button, .st-key-datums_josla button, .st-key-sl_per button, .st-key-cmp_vh button, .st-key-cmp_va button {
  background: linear-gradient(135deg, #18233d 0%, #0a0f1c 100%) !important; border: 1px solid rgba(255,255,255,.12) !important; border-radius: 999px !important;
  min-height: 2.1rem; padding: .25rem .9rem !important; box-shadow: 0 4px 12px rgba(10,15,28,.22); transition: transform .15s ease, box-shadow .15s ease; }
[class*="st-key-pgr_"] button p, .st-key-datums_josla button p, .st-key-sl_per button p, .st-key-cmp_vh button p, .st-key-cmp_va button p {
  color: #cbd5e1 !important; font-weight: 600 !important; font-size: .88rem; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; }
[class*="st-key-pgr_"] button:hover, .st-key-datums_josla button:hover, .st-key-sl_per button:hover, .st-key-cmp_vh button:hover, .st-key-cmp_va button:hover {
  transform: translateY(-1px); box-shadow: 0 8px 18px rgba(10,15,28,.32); }
[class*="st-key-pgr_"] button:hover p, .st-key-sl_per button:hover p, .st-key-cmp_vh button:hover p, .st-key-cmp_va button:hover p, .st-key-datums_josla button:hover p { color: #ffffff !important; }
[class*="st-key-pgr_"] button[data-testid="stBaseButton-primary"], [class*="st-key-pgr_"] button[kind="primary"],
.st-key-sl_per button[data-testid="stBaseButton-primary"], .st-key-sl_per button[kind="primary"],
.st-key-cmp_vh button[data-testid="stBaseButton-primary"], .st-key-cmp_vh button[kind="primary"],
.st-key-cmp_va button[data-testid="stBaseButton-primary"], .st-key-cmp_va button[kind="primary"] {
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%) !important; border-color: rgba(147,197,253,.5) !important;
  box-shadow: 0 0 0 2px rgba(59,130,246,.3), 0 6px 16px rgba(37,99,235,.32); }
[class*="st-key-pgr_"] button[data-testid="stBaseButton-primary"] p, [class*="st-key-pgr_"] button[kind="primary"] p,
.st-key-sl_per button[data-testid="stBaseButton-primary"] p, .st-key-sl_per button[kind="primary"] p,
.st-key-cmp_vh button[data-testid="stBaseButton-primary"] p, .st-key-cmp_vh button[kind="primary"] p,
.st-key-cmp_va button[data-testid="stBaseButton-primary"] p, .st-key-cmp_va button[kind="primary"] p { color: #ffffff !important; }
.st-key-datums_lauks { background: linear-gradient(135deg, #18233d 0%, #0a0f1c 100%) !important; border-color: rgba(255,255,255,.12) !important;
  border-radius: 999px !important; color: #ffffff; box-shadow: 0 4px 12px rgba(10,15,28,.22); }

/* ===== Salīdzinājuma virsraksts: [mājinieki] [VS + maiņas poga] [viesi], zem nosaukumiem katras komandas Mājās/Izbraukumā ===== */
.st-key-cmp_head { display: flex !important; flex-direction: row !important; flex-wrap: nowrap; justify-content: center; align-items: flex-start;
  gap: 1.1rem !important; max-width: 900px; margin: .3rem auto .2rem; }
.st-key-cmp_head > div { width: auto !important; flex: 0 0 auto; min-width: 0; }
.st-key-cmp_ch, .st-key-cmp_ca { width: 15rem !important; align-items: center; gap: .6rem !important; }
.st-key-cmp_head [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }      /* Streamlit noklusējums -1rem lika pogām uzbraukt nosaukumam */
.st-key-cmp_head .cmp-nos { margin-bottom: .15rem; }
.st-key-cmp_cm { width: 4.5rem !important; align-items: center; gap: .55rem !important; }
.st-key-cmp_vh, .st-key-cmp_va { justify-content: center; gap: .35rem !important; }
.st-key-cmp_vh button, .st-key-cmp_va button { min-height: 1.95rem; padding: .15rem .8rem !important; }
.st-key-cmp_vh button p, .st-key-cmp_va button p { font-size: .8rem; }
.st-key-sl_per { justify-content: center; margin: .5rem 0 .3rem; }
.cmp-nos .tip { font-weight: 800; }
.st-key-cmp_ch .cmp-col, .st-key-cmp_ca .cmp-col { width: 100%; }
/* maiņas poga (ikona) ar paskaidrojumu, uzejot ar peli */
.st-key-sl_maina { position: relative !important; width: 2.7rem !important; height: 2.7rem; cursor: pointer; flex: 0 0 auto; }
.st-key-sl_maina > div:first-child { width: 100% !important; line-height: 0; }
.st-key-sl_maina p { margin: 0 !important; }
.maina-ik { width: 2.7rem !important; height: 2.7rem !important; max-width: none !important; display: block; pointer-events: none; transition: transform .35s ease; }
.st-key-sl_maina > div:last-child { position: absolute !important; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important; opacity: 0; }
.st-key-sl_maina > div:last-child * { width: 100% !important; height: 100% !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important; display: block !important; }
.st-key-sl_maina::after { content: "Salīdzināt citas komandas"; position: absolute; top: 100%; left: 50%; transform: translate(-50%, 6px); z-index: 30;
  padding: .3rem .65rem; border-radius: .45rem; background: #262730; color: #fff; font-size: .78rem; font-weight: 600; white-space: nowrap;
  opacity: 0; pointer-events: none; transition: opacity .12s ease; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; }
@media (hover: hover) { .st-key-sl_maina:hover::after { opacity: 1; } .st-key-sl_maina:hover .maina-ik { transform: rotate(180deg); } }
/* paskaidrojums, uzejot ar peli (vai pieskaroties) uz pasvītrota teksta */
.tip { position: relative; display: inline-block; cursor: help; text-decoration: underline dotted rgba(128,128,128,.8); text-underline-offset: 3px; outline: none; }
.tip .bubble { display: none; position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: 6px; z-index: 40; width: max-content; max-width: 17rem;
  padding: .45rem .7rem; background: #ffffff; color: #31333f; border: 1px solid rgba(49,51,63,.12); border-radius: .5rem; box-shadow: 0 .25rem 1rem rgba(0,0,0,.18);
  font-size: .8rem; font-weight: 400; line-height: 1.45; text-align: left; white-space: normal; letter-spacing: 0; text-transform: none; }
.tip:hover .bubble, .tip:focus .bubble, .tip:focus-within .bubble { display: block; }
@media (max-width: 900px), (hover: none) {
  .tip .bubble { position: fixed; left: .5rem; right: .5rem; top: auto; bottom: calc(4rem + env(safe-area-inset-bottom, 0px)); transform: none; margin: 0;
    width: auto; max-width: none; max-height: 50vh; overflow-y: auto; z-index: 2000; font-size: .9rem; box-shadow: 0 -.25rem 1.5rem rgba(0,0,0,.28); }
}
/* peldošie logo: kad virsraksta logo vairs nav redzami, mazi logo "brauc līdzi" ekrāna augšā virs attiecīgās puses (ieslēdz skripts) */
.cmp-float { position: fixed; left: 50%; top: var(--cf-top, .5rem); width: min(900px, calc(100vw - 2rem)); display: flex; z-index: 900; pointer-events: none;
  opacity: 0; transform: translate(-50%, -16px); transition: opacity .22s ease, transform .22s ease; }
.cmp-float.on { opacity: 1; transform: translate(-50%, 0); }
.cf-k { width: 50%; display: flex; justify-content: center; }
.cf-c { display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 5px 8px 5px; border-radius: 14px; background: rgba(255,255,255,.66);
  -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); box-shadow: 0 4px 14px rgba(0,0,0,.12); }
.cf-c img { width: 2.6rem !important; height: 2.6rem !important; max-width: none !important; object-fit: contain; display: block; }
.cf-c i { display: block; width: 2.2rem; height: 3px; border-radius: 2px; }
.cf-c i.a { background: #dc2626; }
.cf-c i.b { background: #111827; }
.st-key-cmp_skripts { position: absolute !important; width: 0; height: 0; overflow: hidden; margin: 0 !important; padding: 0 !important; }
@media (max-width: 640px) { .cf-c { padding: 4px 6px; } .cf-c img { width: 2.1rem !important; height: 2.1rem !important; } .cf-c i { width: 1.8rem; } }
/* pēdējās 5 spēles abām komandām */
.cmp-l5 { display: flex; justify-content: space-between; gap: 1.2rem; margin: 1.8rem 0 .5rem; }
.l5c { flex: 1 1 0; min-width: 0; max-width: 26rem; }
.l5h { font-weight: 800; font-size: .9rem; margin-bottom: .35rem; }
.l5c.r .l5h { text-align: right; }
.l5r { display: flex; align-items: center; gap: .55rem; padding: .38rem 0; border-bottom: 1px solid rgba(128,128,128,.2); font-size: .9rem; }
.l5c.r .l5r { flex-direction: row-reverse; }
.l5d { opacity: .65; font-size: .8rem; min-width: 2.6rem; }
.l5o { font-weight: 600; display: inline-flex; align-items: center; gap: .3rem; }
.l5lg { width: 1.7rem !important; height: 1.7rem !important; max-width: none !important; object-fit: contain; }
.l5s { font-weight: 800; color: inherit !important; text-decoration: underline; text-underline-offset: 3px; }
.l5u { font-size: .68rem; font-weight: 800; padding: .08rem .38rem; border-radius: .3rem; }
.l5u.U { background: rgba(22,163,74,.14); color: #15803d; }
.l5u.Z { background: rgba(220,38,38,.12); color: #b91c1c; }
.l5u.ZPL { background: rgba(245,158,11,.16); color: #b45309; }
@media (max-width: 640px) {
  .st-key-cmp_head { gap: .3rem !important; }
  .st-key-cmp_ch, .st-key-cmp_ca { width: 9.3rem !important; }
  .st-key-cmp_cm { width: 2.8rem !important; }
  .st-key-cmp_vh, .st-key-cmp_va { gap: .25rem !important; flex-wrap: nowrap; }
  .st-key-cmp_vh button, .st-key-cmp_va button { padding: .1rem .45rem !important; min-height: 1.8rem; }
  .st-key-cmp_vh button p, .st-key-cmp_va button p { font-size: .7rem; }
  .cmp-l5 { gap: .6rem; }
  .l5r { font-size: .78rem; gap: .35rem; }
  .l5d { min-width: 2.2rem; font-size: .72rem; }
}

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
}

/* ===== Komandu salīdzināšana: virsraksts (logo VS logo vienā rindā), krāsas sarkana/melna pie logo, rādītāju rindas ===== */
.cmp-wrap { width: 100%; max-width: 900px; margin: 0 auto; }
.cmp-head { display: flex; align-items: flex-start; justify-content: center; gap: 1.4rem; margin: .4rem 0 1rem; }
.cmp-col { width: 10.5rem; display: flex; flex-direction: column; align-items: center; text-align: center; gap: .5rem; }
.cmp-logo { width: 7rem !important; height: 7rem !important; max-width: none !important; object-fit: contain; display: block; }
.cmp-krasa { width: 7rem; height: .4rem; border-radius: .25rem; }
.cmp-krasa.a, .cmp-bar i.a { background: #dc2626; }
.cmp-krasa.b, .cmp-bar i.b { background: #111827; }
.cmp-nos { font-weight: 700; font-size: 1rem; line-height: 1.2; }
.cmp-vs { height: 7rem; display: flex; align-items: center; font-weight: 800; font-size: 2rem; opacity: .55; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; }
.cmp-group { margin: 1.5rem 0 .2rem; font-weight: 800; font-size: .88rem; letter-spacing: .07em; opacity: .9; text-align: center; }
.cmp-row { margin: .8rem 0; }
.cmp-top { display: flex; align-items: baseline; justify-content: space-between; gap: .6rem; }
.cmp-v { font-weight: 600; font-size: 1.15rem; min-width: 3.2rem; opacity: .7; }
.cmp-v.r { text-align: right; }
.cmp-v.win { opacity: 1; font-weight: 800; }
.cmp-lab { flex: 1; text-align: center; font-size: .88rem; opacity: .85; }
.cmp-bar { display: flex; gap: .25rem; height: .5rem; margin-top: .35rem; }
.cmp-bar i { display: block; height: 100%; }
.cmp-bar i.a { border-radius: .3rem 0 0 .3rem; }
.cmp-bar i.b { border-radius: 0 .3rem .3rem 0; }
/* filtru pogas: augšējie (laika posms) un apakšējie (mājās / izbraukumā), centrēti */
.st-key-sl_per, .st-key-sl_viet { display: flex !important; flex-direction: row !important; flex-wrap: wrap; justify-content: center; gap: .5rem !important; margin-bottom: .4rem; }
.st-key-sl_per > div, .st-key-sl_viet > div { width: auto !important; flex: 0 0 auto; }
.st-key-sl_viet button { min-height: 2rem; padding: .1rem .9rem; font-size: .85rem; }
.st-key-sl_poga_josla { display: flex !important; flex-direction: row !important; justify-content: center; margin: .3rem 0 .8rem; }
.st-key-sl_poga_josla > div { width: auto !important; flex: 0 0 auto; }
.st-key-sl_poga_josla button { background: linear-gradient(135deg, #18233d 0%, #0a0f1c 100%) !important; border: 1px solid rgba(255,255,255,.14) !important;
  border-radius: 999px !important; min-height: 3rem; padding: .55rem 2.6rem !important; box-shadow: 0 10px 24px rgba(10,15,28,.35);
  transition: transform .15s ease, box-shadow .15s ease, background .15s ease; }
.st-key-sl_poga_josla button p { color: #ffffff !important; font-weight: 700 !important; letter-spacing: .06em; font-size: 1rem;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; }
.st-key-sl_poga_josla button:hover:not(:disabled) { transform: translateY(-1px) scale(1.03); box-shadow: 0 14px 30px rgba(10,15,28,.45);
  background: linear-gradient(135deg, #22304f 0%, #0d1424 100%) !important; }
.st-key-sl_poga_josla button:disabled { opacity: .45; box-shadow: none; }
.st-key-sl_citas { display: flex !important; flex-direction: row !important; justify-content: center; margin: .2rem 0 .6rem; }
.st-key-sl_citas > div { width: auto !important; flex: 0 0 auto; }
@media (max-width: 640px) {
  .cmp-head { gap: .5rem; }
  .cmp-col { width: 7.4rem; }
  .cmp-logo { width: 4.9rem !important; height: 4.9rem !important; }
  .cmp-krasa { width: 4.9rem; }
  .cmp-vs { height: 4.9rem; font-size: 1.5rem; }
  .cmp-nos { font-size: .85rem; }
  .cmp-v { font-size: 1.05rem; min-width: 2.6rem; }
  .cmp-lab { font-size: .8rem; }
}
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


_tumss_tab = tema_css(".tb thead th, .tb td.c0, .tb th.c0, .tb td.c1, .tb th.c1 { background: #11151d; } .cf-c { background: rgba(14,17,23,.62); } .cf-c i.b { background: #d1d5db; } .tb .bubble, .tip .bubble { background: #262730; color: #fafafa; border-color: rgba(250,250,250,.15); } .tb .bubble a { color: #60a5fa; } .maina-ik { filter: invert(1); }")
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


@st.cache_data(show_spinner=False, ttl=600)
def ielasit_planotos(versija):
    """
    Paziņotie tiesneši: fails dati/tiesnesi_planotie.csv (to papildina GitHub Actions) + spēlēm, kurām tur tiesnešu vēl nav, tiešā ielāde no Scouting The Refs.
    GitHub plānotie darbi bieži kavējas vai tiek izlaisti, tāpēc lietotne tiesnešus meklē arī pati (rezultāts tiek turēts 10 minūtes, lai neslogotu portālu).
    """
    plan = da.ielasit_planotos_tiesnesus()
    kal = ielasit_visu(versija)[2]
    if kal is None or kal.empty:
        return plan
    try:
        import tiesnesi_planotie as tp
        esosie = set(plan.loc[plan["loma"] == "referee", "game_id"].astype(int)) if plan is not None and not plan.empty else set()
        jaunas = tp.dzivie_tiesnesi(kal, esosie)
    except Exception:                     # bez interneta vai ja portāls nav pieejams: paliek tikai tas, kas ir failā
        return plan
    if not jaunas:
        return plan
    jauns = pd.DataFrame(jaunas)
    return jauns if plan is None or plan.empty else pd.concat([plan, jauns], ignore_index=True)


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
def _izv_vertiba(key, opcijas, noklusejums):
    v = st.session_state.get(key)
    return v if v in opcijas else noklusejums


def _izv_set(key, v):
    st.session_state[key] = v


ETIKETES = {"Izbraukumā": "Viesos"}          # redzamie nosaukumi pogām (iekšējā vērtība paliek nemainīta)


def sledzis(label, opcijas, neitrala, default=None, key=None):
    """
    Pārslēdzēju pogas (kā komandu salīdzinājumā): klikšķis ieslēdz opciju, atkārtots klikšķis uz tās pašas to izslēdz.
    Ja nekas nav ieslēgts, tiek rādīts neitrālais skats (neitrala, piem., "Visas" vai "Visa sezona"), un tam pogas nav.
    """
    opcijas = list(opcijas)
    key = key or "sl_" + "".join(ch if ch.isalnum() else "_" for ch in label)
    if key not in st.session_state or (st.session_state[key] is not None and st.session_state[key] not in opcijas):
        st.session_state[key] = default if default in opcijas else None
    cur = _izv_vertiba(key, opcijas, st.session_state.get(key))
    with st.container(key=f"pg_{key}"):
        if label:
            st.markdown(f'<div class="pg-lab">{_html.escape(label)}</div>', unsafe_allow_html=True)
        with st.container(key=f"pgr_{key}"):
            for o in opcijas:
                st.button(ETIKETES.get(o, str(o)), key=f"{key}__{o}", type="primary" if o == cur else "secondary", on_click=_sl_tog, args=(key, o))
    return cur if cur in opcijas else neitrala


def izvele(label, opcijas, default=None, key=None):
    """Filtru / kārtošanas pogu grupa: tumšas noapaļotas pogas (kā "Salīdzināt"), aktīvā izcelta zilā krāsā. Atgriež izvēlēto vērtību."""
    opcijas = list(opcijas)
    key = key or "izv_" + "".join(ch if ch.isalnum() else "_" for ch in label)
    d = default if default in opcijas else opcijas[0]
    cur = _izv_vertiba(key, opcijas, d)
    with st.container(key=f"pg_{key}"):
        if label:
            st.markdown(f'<div class="pg-lab">{_html.escape(label)}</div>', unsafe_allow_html=True)
        with st.container(key=f"pgr_{key}"):
            for o in opcijas:
                st.button(ETIKETES.get(o, str(o)), key=f"{key}__{o}", type="primary" if o == cur else "secondary", on_click=_izv_set, args=(key, o))
    return cur


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
    "Noraid./sp": "Vidēji noraidījumu skaits spēlē (tikai minor sodi pamatlaikā; dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem)",
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
    "PIM min/sp": "Vidēji minor sodu minūtes spēlē (pamatlaikā; bez major, 10 min disciplinārajiem un kautiņiem)",
    "Izcīnīti/sp": "Vidēji pretinieka noraidījumi pret šo komandu spēlē pamatlaikā (bez papildlaika)",
    "Izcīnīti − saņemti": "Izcīnīto un saņemto noraidījumu starpība spēlē; pozitīvs skaitlis = komanda izcīna vairāk, nekā saņem",
    # komandas lapa
    "Skats": "Spēļu izlase, kurai parādīta statistika",
    "Pretinieks": "vs = spēle mājās, @ = spēle viesos",
    "Rez.": "🟩 uzvara, 🟨 zaudējums papildlaikā/pēcspēles metienos, 🟥 zaudējums pamatlaikā",
    "Rezultāts": "Spēles rezultāts: komandas vārti–pretinieka vārti (OT/SO = papildlaiks/pēcspēles metieni)",
    "Metieni": "Metieni vārtos visā spēlē (arī papildlaikā, tikai informācijai): komanda–pretinieks",
    "Noraid.": "Komandas noraidījumu skaits spēlē (tikai minor sodi pamatlaikā; dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem)",
    "Noraidījumi": "Komandas noraidījumu skaits spēlē (tikai minor sodi pamatlaikā; dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem)",
    "PIM min": "Minor sodu minūtes spēlē (pamatlaikā; bez major, 10 min disciplinārajiem un kautiņiem)",
    "PIM 1. per.": "Sodu minūtes 1. periodā",
    "PIM 2. per.": "Sodu minūtes 2. periodā",
    "PIM 3. per.": "Sodu minūtes 3. periodā",
    "Starpība (visas)": "Vārtu starpība šajā periodā visās sezonas spēlēs",
    "Mājās": "Vārtu starpība šajā periodā mājas spēlēs",
    "Viesos": "Vārtu starpība šajā periodā viesu spēlēs",
    "Pēdējās 10": "Vārtu starpība šajā periodā pēdējās 10 spēlēs",
    "Vieta": "Spēles vieta: mājās vai viesos",
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
    """Tabula (caurspīdīga HTML) ar paskaidrojumiem kolonnu virsrakstos. Citi Streamlit st.dataframe parametri (width, height) netiek lietoti."""
    df_html(df, config=cfg_ar_help(list(df.columns), column_config, paskaidr),
            indekss=(kw.get("hide_index") is False and not isinstance(df.index, pd.RangeIndex)), kartot=kw.get("kartot", True))


def tabula(res, kolonnas, sort_col, ascending=False, config=None, grafiks=False, paskaidr=None, burbuli=None, formati=None, prog=None):
    """Komandu rangu tabula ar logotipiem. res: DataFrame ar indeksu 'komanda'; kolonnas: {iekšējais: virsraksts}.
    burbuli: {komanda: HTML} spēļu saraksts burbulī uz kolonnas "Sp."; formati/prog: {iekšējais: formāts / (min, max)}. (Grafiki lietotnē vairs netiek rādīti.)"""
    if res is None or res.empty:
        st.info("Nav datu šim skatam.")
        return
    t = res.sort_values(sort_col, ascending=ascending, kind="stable").reset_index()
    bur = [burbuli.get(k) for k in t["komanda"]] if burbuli else None
    t.insert(0, "Logo", t["komanda"].map(da.logo_url))
    t.insert(1, "Komanda", t["komanda"].map(da.pilns_nosaukums))
    t.insert(0, "#", range(1, len(t) + 1))
    t = t[["#", "Logo", "Komanda"] + list(kolonnas)].rename(columns=kolonnas)
    cfg = {"Logo": st.column_config.ImageColumn("", width="small"), "#": st.column_config.NumberColumn("#", width="small")}
    cfg.update(config or {})
    fm = {kolonnas[k]: v for k, v in (formati or {}).items() if k in kolonnas}
    pg = {kolonnas[k]: v for k, v in (prog or {}).items() if k in kolonnas}
    df_html(t, config=cfg_ar_help(list(t.columns), cfg, paskaidr), formati=fm, prog=pg, burbuli=bur, bur_kol=kolonnas.get("GP"))


def prognozes_bloks(pr):
    m1, m2, m3 = st.columns(3)
    m1.metric("Rezultāts (mājas–viesi)", pr["rezultats"], border=True)
    m2.metric("Vārti: Over / Under", pr["over_under"], border=True)
    m3.metric("Noraidījumi", pr["noraidījumi"], border=True)
    st.caption(f"1. periods: {pr['p1']}  ·  2. periods: {pr['p2']}  ·  3. periods: {pr['p3']}")


def rezultata_teksts(h, a, beigas):
    et = da.beigu_etikete(beigas)
    return f"{int(a)}–{int(h)}" + (f" {et}" if et else "")


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
    c1, c2 = st.columns(2)
    with c1:
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="pk_scope")
    with c2:
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="pk_logs")
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
SALIDZ_METRIKAS = [      # (nosaukums, paskaidrojums uzejot ar peli, kolonna, kam labāk ("augsts"/"zems"/"neitrals"), zīmes aiz komata)
    ("Rezultativitāte", [
        ("Vārti spēlē", "Vidēji spēlē (pamatlaikā)", "G_sp", "augsts", 2),
        ("Ielaisti spēlē", "Vidēji spēlē (pamatlaikā)", "Z_sp", "zems", 2),
        ("Over 6.5", "% – spēļu daļa, kurās abu komandu vārtu summa pamatlaikā ir lielāka par 6.5", "Over65", "neitrals", 0),
        ("Over 5.5", "% – spēļu daļa, kurās abu komandu vārtu summa pamatlaikā ir lielāka par 5.5", "Over55", "neitrals", 0),
    ]),
    ("Metieni", [
        ("Metieni vārtos spēlē", "Vidēji spēlē (pamatlaikā)", "SOG_sp", "augsts", 1),
        ("Pretinieka metieni spēlē", "Vidēji spēlē (pamatlaikā)", "SA_sp", "zems", 1),
    ]),
    ("Vairākums un noraidījumi", [
        ("Vairākums PP", "% – kopā izvēlētajās spēlēs: vairākumā gūtie vārti / vairākuma iespējas", "PP_pct", "augsts", 1),
        ("Mazākums PK", "% – kopā izvēlētajās spēlēs: mazākumā nosargātās reizes", "PK_pct", "augsts", 1),
        ("Noraidījumi spēlē", "Vidēji spēlē (saņemtie, pamatlaikā)", "PEN_sp", "zems", 1),
        ("Izcīnītie noraidījumi spēlē", "Vidēji spēlē (pretinieka noraidījumi)", "DRAW_sp", "augsts", 1),
    ]),
    ("Gūtie vārti pa periodiem", [
        ("1. periods", "Vidēji spēlē", "G_p1", "augsts", 2),
        ("2. periods", "Vidēji spēlē", "G_p2", "augsts", 2),
        ("3. periods", "Vidēji spēlē", "G_p3", "augsts", 2),
    ]),
    ("Ielaistie vārti pa periodiem", [
        ("1. periods", "Vidēji spēlē", "Z_p1", "zems", 2),
        ("2. periods", "Vidēji spēlē", "Z_p2", "zems", 2),
        ("3. periods", "Vidēji spēlē", "Z_p3", "zems", 2),
    ]),
]
SL_LOGI = {"Pēdējās 5": 5, "Pēdējās 10": 10}          # ja neviens nav izvēlēts: visas sezonas spēles
MAINA_IKONA = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAARZElEQVR42u1dW2wUR9b+TvWMPcYGzGJMsCFczIYFRjKEQEJEFEiUzUMIQshZEoGQolir/TdE0YpEechDnshKBK0REBI2InlA5AaBsNhAohUBJEIQIIPt/bmYcBEbLuYWj+fel7MPdPX29MzYY5ieHlhKank8Hk9XfV+dc6rOOXWa4G0jAML8qWX4ezWAMUKIR4QQY3VdH8XMNQDKAfzG8dmbACJEdElRlIuGYZwzDOM0gPMAujJ8tw8AAzDMn54B4NV9lQyg/xbATABPENE0AGMBVMl+MueGE5E1LAZwHcA5AEeZ+ScABwF0ZiBD94KIQhMgZ7tue+8JIpoH4PcA6gH4MgDtnKXZ+s0ZpMtJjAbgOIDvmfkfAH6yfUSxScV91YQ5ONlqhRDLiOgwETERsTlwNgFSTZIM2/t3ehnmd6nmdzMAlvclosNCiGUAah1EiPsBeHIAP5WI1hPRLRvoRp4B7w8hho2MW0S0HsBUBxF0r4Lvs72eQkRfEJFmA0K16V0vL0mGlAyNiL4AMCXLWO4JdSPFt4aI1hJRwjbjtQLN9DuRDM0mEQkiWgugJsO4irbZ1c0fieiqA3i+Ry47EVcB/DHLGItK10sxHUdEu23Aq0U643ORCNVGxG4A42wqiYoJfNmZPxDR9Xsc+N6IuA7gDxnG7am+BwBBRH+7R9XNnailv9nH7rW+H2JTOdp9Mut7NdQ2lTTEK7sgb/gwER03O5e8j4F3XklTGo4DeLjQJMgbTSKiTpu+5/+xS9qFTgCTCkWCvMHviKjrfxh8JwldAH7nNgnCpnbOeAW+EIIVRXH6j4qBhDM2dSTcAJ8AVBJRu1crHSfoRUSCXCG1A6jM5InNxyZLENH3Xsx8O9CzZ8/mxYsXc1VVVbGRICXhexP8vG3WfKYvvckcbLLQ4AshGACvWrWKdV1nZuYTJ07wpEmTLLVULKsjc4nalC8nnjQoDSb4qlfgr1mzhpmZo9Eod3d3MzPz+vXrGQArilJUhtnEquFujbIAQIFA4GEiulVAf31W8Ht6ejgajXI4HGZd13nr1q3FJgFWvIGIbgUCgYfvxh4opur5Z6GNrh381atXMzNzOBzmWCzGsViMw+EwMzNv2bKFiajYVkV2o/zPO5UCBQCEEI2FVj2ZZr4dfDsBmzdvzrpMFUJ4TYpqjqWxvyTIwEM1Ed0opOrJBXw7Ac3NzTxixAgePXo0V1ZWZlRFkgwPVdEN3E6vyRjQoSyzXyeidcz8f6Y4uR6Sk6kkzIzVq1fjjTfeQCQSgaIoWT+fSCTQ09MDIQR6enpw7do1XLx4EceOHcO+fftw4sQJdHd3W58nIhhGQRMeNAA+IvqImf8sse3T8Pr9/slElCjU7JczXwjBa9eutQyuc+Y7r3g8zqqqsqqq1vJUtlgsxqdPn+aVK1fy9OnTU1RUAVWTlIKE3++fnItBloZ3cyE3XFJFvPfeezmDL69oNMrRaJQjkQhHIhEOh8PW/0tSYrEYb9++nWfPnp2imgq8QducyRaQA3zD9HIeZ+a8bqd7Uz3MjGHDhuHw4cOora1FMpmEEHd/a8MwYBgGfD4fAoEANE3Dxo0b8e677+Ly5ctQFAW6rhdCFRlExMxcD+D/TVz1TE4jJqK/MLMkozAxTVOfh0IhKIqScwqitBlZ9akQ8Plum69IJAJVVfHqq6/i4MGDmDt3LnRdhxDCnsroGgHMrBDRX+BIf1RskmAAGE5Efwfgtzng3I9rCoF4PI4bN26goaHBmrm5AKMoCgzDADNbP6XBdd6DiBCPx1FVVYWFCxdC13Xs378/L9KWgz8NRPQIgE8B9Mj3FJvPwhBC/AnAXFM8ChbhYWYIIdDR0YFffvkF8+bNs1RINhLkiiaRSCAQCKC0tBQlJSUoKSkBM0PTtJTVlZ0IVVVhGAaef/55DB06FDt37nSbBDKNcUAIcYWZD0rMJchsfuhDZn7I/L2gwWZmhqIoOHr0KC5cuID58+dnJcEwDJSVleHAgQNoaGjAl19+iW+//Rbnz59HOBxGVVUVKisr4fP5kEwm0yRCvk4mk5g1axYqKyuxe/furEvefA1R7q8A/N2uiuRdp5vLM0+D6j6fjwHw4sWLOZFIcCKR4EgkknEjtmPHjozfMX78eH7zzTe5vb2dmZmTyWTGDZ30KzEzL1u2rBCrI8PEeLode785K/7qhcezNxIWLVrEiUSC4/F4CgkStJaWFhZCsM/nY0VR0nxCFRUV/NZbb/H169ezLm+j0ai1p3j22Wfddu6pprv6ryYBfivBiIiOFVNOjyThpZde4ng8niIJdldEJsCkP0j+HgwGef/+/VldG5FIhHVd559//pmHDRvGGVLm8+2kO+ZM7KojIpnJ5ooKkl5L5+veLvmZhoYGjsVilirp6elhTdP4u+++63XGEpFF5IABA3jTpk1ZSejp6WFm5rVr17opBYaphlQAdXYDscSWWOVqSLG/A5MALliwgCORiBWUYWZuamrKSW/LvwsheiVBXjNmzHCTBM3EY4l9VfCRW64HCf6IESN4xYoV/MMPP/DOnTv5tddeyzm4Lkl48cUX+eTJk3zlyhVubm7m4cOH56wupA9owIABfODAgV7d3F999ZWbBEjXxEc2/Okw/ntYIa/gExHX1tZyR0cHO1tTU5PlhMvVX1RRUcGjRo26o/5ISQgGg3zjxg1OJBKWEbY7+EKhEAeDQbdI0E1sDksbUGXLaM6r/pcD/uCDD5iZ+ddff7UcZlKdPPXUUzkv/+xg3KmhlPd55513MkqBtAXvv/++W8tSeSzqOm6fAMUMIsq721mCM2jQIO7s7GRVVdOWkoZh8Ntvv92vgd7tCkX+/+DBg/nUqVOsaVpKv+SKqKOjg8vLy91KfTFMzGcIABPMHVpez8jK3WYwGMTIkSOhaVradp+IkEwm+71j7o+zLpvbo7u7G5988kma80/2ady4cZg4cWJGd0Yed8UThM/nG2t7M+8EPPPMM5Yr2OlESyaTOHToUJ9eTTfcHgDQ3NyMUCgEv99vvUdE0DQNZWVlePrpp90kAD6fb6zQdX2kG4OXob/6+vq0QRiGgdLSUrS1teH48eMFJ0D6lzo7O3HkyBGUlJSkhCplX6dOnepa35gZuq6PFMw83K0gi9/vx5gxY9IIkC7jtrY2xGKxfscA8uUC13UdHR0dWaV39OjRrsaRmXm4ADDIrUEOGTIEw4YNg67rGcX4yJEj8Lpl64NhGBg+fDgGDx7slhoCgEFCLoXyGXyRna2oqEBZWVnaDJJ/P3XqlOcEXLx4MQ1gOesrKiowcOBA1wI0AKqEm6HHQYMGZSVA13VrBVRo9WO/p6qq0DQt4wwnImvl5pIEGO6GgXrp9N0uJ/PZx1zAdauvrh6/D4VCiMfjaet/Gf2SEagCBMWzTg6/3591ESDjzK6uBXC7oFFe9wFyMOFwGLFYLCMBRISamhrPJWDChAlpM1xOkFAohFAo5FZ4EgCuCwAhtwZ38+ZNXLt2LesMe/zxxz0n4LHHHssqIV1dXRYBLqmgkDCLUeTdwBERVFXF+fPnsw4gGAxCCFHofE1rEVBaWopgMGj11ynB586ds1wXLvXjqlAU5d9u6GDZ6ba2tjQChBBIJpOYNm0a6urqXB1kb/q/vr4eU6ZMQSKRSLm/7Gtra6trNoqIoCjKv4WmaefyvQ+wD2LPnj2Ix+NWhpq8uaqqGDJkCF544YWCG2J5r5kzZ6K0tDQlPVHu4KPRKPbu3euW+rldvE7TzgkAp8y9gCsEtLe349KlSykOL/tmp7GxEeXl5Tlnwt3tctLeysvL08BlZvh8Ppw5cwanT592kwADwCkB4CyAW+abeV0JKYqC7u5u7NixIy0RVgiBWCyGyZMno7Gx8Y7VkARe7iv68x0//vijRZqu6zAMA6qqQlEUbN26FdFo1A0/lUyCu2Vi715IUkawZsyYkTW1PJlM8tWrV3n8+PF3FQIcOXIkDxw4MOfvkKkr69atSwuVtre380MPPeRWekpaSNLVoLwMhu/YsaPXQPiePXs4EAikHFNCDpGtoUOH8jfffMNXrlzhzs5OXrBgQUogH31E7IQQvHTpUt63bx8fOnSIm5qauLa21s1D4GlBecDFtBQZapwzZw6rqpoWBLeT8Omnn+Z8gEL+ffny5SmpKolEgl9++eWcSHAS4vf7C1EGIT0tBS4nZskZ/dlnn2VNEZQkbNiwgUtKSiwAswEhv3Pbtm2saRr39PRwOBy2UhlfeeWVnCXBTrbLR14zJma5npoo1dCIESP4woULaYFwJwm7du2ybAKynHSUv2/evDlFtUUiESupd+HChf2ShAKcHcuYmliQ5FwJ2Ny5c60MiUzqSKaFXLp0iZcuXcplZWVps1VRFPb5fCyE4C1btqTZlkgkYuWTLlq0qN/qyMUrY3JuwdLTpaj3dRgvHA6zqqrMzNza2spLly7lurq6jN/59ddfZzTudkm4E5uAAqan29VQK1zMkLaXFfjwww8t4DJJgj13n5m5q6uLW1paePny5Txv3jyeNWsWT548mXfv3s3MnFGlSUlIJpOWOvKwsIdUP63IUPLSZ26Olrl9RsC+tpYkyGOmmaRBZtIlk8mUtbqqqtzd3c3hcJjj8XjWRFtJgt0we3RyXpYuWGbH3H5ECcx8loj+BKDUDf+Qc/fa0tICZsacOXPg9/vTnGL2sKBhGEgmk1YI0TAMlJSUQAjR605VujwURcH8+fPR1taGkydP9vl/Lvj/BRFFmLkRQERibj8UpQDoIaI6AI+aOzbXXJQS2L1796K1tRWzZs1CdXW1dYAuGxHytGN/0kXsyVaTJk3Cpk2brLNjBWo6AIWINgL4Av89k50GMDFzk5m36Kp/WIb7FEVBc3MzZs6ciQ0bNsDv96O8vBymt7BXkPsDoN0DGwgECh2PFkSkM3OTU6sIB0sCwL8AbDNfa65PDV2Hoii4fPkyGhsb8dxzz2H79u1gZlRUVCAQCFhkSIeZdLz1B0TDMOD3+7Fx40Zcu3atkCpIM7HcZmJrnZLPFqQveLEOOErVAOBp06bxypUrubOzk+PxeIoB1jSNk8mktevtq56E3Ft8/PHHha4l1GexjqIpV2N3U9tn9+DBgxEMBjFnzhzU19dj9OjRqK6uRllZGfx+P0pLS3t1Geu6jvLycqxbtw6vv/56SlmcAs3+fpWrkVLgScEm9HLSEbbjStXV1VxXV8cTJ07kvXv3smEYvRZ2sh+886BUTa8Fm7I1z0qWZVNN2Zxkfbm516xZk5eDHXex7u93ybIUErwo2pfLRk76glpaWlIIsO+gV69e7cXMz0vRPssge1W2Mlfn3q5du1jXdculUQTg561spZ25hmIpY+Ak4PPPP2dm5u7ubisos2rVKq/Az2vh1hQ/kVeli/si4NFHH+WzZ89aRTlWrFjhJfh5L10sl6qeFu/uK4BSU1PDS5Ys4SeffNIrg+tq8W7LHsDj8vW5RLE88nS6Wr7e6bbw9AEOvcUZvHIzowAPcHAa5QePMPHgESZOEh48xMeDh/g4SXjwGCsPHmPlJOHBg9w8fMDng0cZFsEjbh88zLMI2oPH2RZJe/BA5yJoDx5pXiTN7oiaQkRfEJHmWEfrRQC8bt/HEJFGRF8AmJJlLPdUI4fITiWi9UR0yyYRho0Mo0AzXbfbJnPG3yKi9QCmOtQN4T5owkFErZkGeTiD51LLMyF2wDVnZI2IDpvpgrUO4EWhZmihiSBHZsATRDQPwO8B1APwZchYkET01W/nZ1JTQG5nRGgAjgP4npn/AeAnB/CSNNyPBDhVkzPx67cAZpqkTAMwFrfrGRGQeyqJLWOOcbsWxjlmPmqCfRBAZwZ7pSPPdfOKmQDnLCVkzsKrBjBGCPGIEGKsruujmLkGQDmA3zg+exNAhIguKYpy0TCMc4ZhnAZwHkBXlkUCZ5Cugrb/ACpG4ME7R0cnAAAAAElFTkSuQmCC"


def _sk(v, dec):
    """Skaitlis bez liekiem punktiem un nullēm: 3.00 → 3, 5.50 → 5.5, 26.0 → 26."""
    s = f"{v:.{dec}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def tip_html(teksts, paskaidrojums):
    """Teksts ar paskaidrojumu, kas parādās, uzejot ar peli (vai pieskaroties)."""
    e = _html.escape
    return f'<span class="tip" tabindex="0">{e(str(teksts))}<span class="bubble">{e(paskaidrojums)}</span></span>'


def sl_rinda_html(nos, paskaidr, a, b, labak, dec):
    """Viena rinda: vērtība | nosaukums (paskaidrojums uzejot ar peli) | vērtība, un sarkani-melna josla. Labākais cipars treknrakstā."""
    if a is None or b is None or pd.isna(a) or pd.isna(b):
        fa = "–" if a is None or pd.isna(a) else _sk(a, dec)
        fb = "–" if b is None or pd.isna(b) else _sk(b, dec)
        sa, wa, wb = 50.0, False, False
    else:
        fa, fb = _sk(a, dec), _sk(b, dec)
        kopa = abs(a) + abs(b)
        sa = 50.0 if kopa == 0 else abs(a) / kopa * 100
        wa, wb = ((a > b, b > a) if labak == "augsts" else (a < b, b < a) if labak == "zems" else (False, False))
    return (f'<div class="cmp-row"><div class="cmp-top"><span class="cmp-v l{" win" if wa else ""}">{fa}</span>'
            f'<span class="cmp-lab">{tip_html(nos, paskaidr)}</span><span class="cmp-v r{" win" if wb else ""}">{fb}</span></div>'
            f'<div class="cmp-bar"><i class="a" style="width:{sa:.1f}%"></i><i class="b" style="width:{100 - sa:.1f}%"></i></div></div>')


def sl_komanda_html(kods, kl, gp_kopa, gp_skata, majas_puse):
    """Logo, komandas krāsa (zem logo, tā platumā) un nosaukums; nospēlēto spēļu skaits mājiniekiem pirms nosaukuma, viesiem aiz tā."""
    sk = tip_html(gp_kopa, f"Nospēlētās spēles kopā: {gp_kopa}" + (f" · šajā skatā: {gp_skata}" if gp_skata is not None and gp_skata != gp_kopa else ""))
    nos = _html.escape(da.pilns_nosaukums(kods))
    rinda = f"{sk} {nos}" if majas_puse else f"{nos} {sk}"
    return (f'<div class="cmp-col"><img class="cmp-logo" src="{_html.escape(da.logo_url(kods))}" alt="{_html.escape(kods)}">'
            f'<div class="cmp-krasa {kl}"></div><div class="cmp-nos">{rinda}</div></div>')


def sl_pedejas5_html(kods, puse):
    """Komandas pēdējās 5 spēles (jaunākā augšā). Rezultāts ir saite uz spēles protokolu sadaļā Rezultāti (jaunā cilnē)."""
    g = DF[DF["komanda"] == kods].sort_values(["datums", "game_id"]).tail(5).iloc[::-1]
    iznak = {"W": "U", "L": "Z", "OTL": "ZPL"}
    rindas = ""
    for r in g.itertuples():
        bg = da.beigu_etikete(r.beigas)
        rez = f"{int(r.g_tot)}:{int(r.z_tot)}" + (f" {bg}" if bg else "")
        u = iznak.get(r.rez, "")
        rindas += (f'<div class="l5r"><span class="l5d">{pd.Timestamp(r.datums):%d.%m}</span>'
                   f'<span class="l5o" title="{_html.escape(da.pilns_nosaukums(r.pretinieks))}">{"vs" if r.majas == 1 else "@"} '
                   f'<img class="l5lg" src="{_html.escape(da.logo_url(r.pretinieks))}" alt="{_html.escape(r.pretinieks)}"></span>'
                   f'<a class="l5s" href="{_html.escape(speles_saite(r.game_id))}" target="_blank" rel="noopener noreferrer">{rez}</a>'
                   + (f'<span class="l5u {u}">{u}</span>' if u else "") + "</div>")
    return f'<div class="l5c {puse}"><div class="l5h">Pēdējās 5 spēles</div>{rindas or "<div class=l5r>Nav spēļu</div>"}</div>'


def _sl_salidzinat(a, b):
    # noklusējums jaunam salīdzinājumam: mājiniekiem mājas spēles, viesiem izbraukuma spēles, visa sezona
    st.session_state.update(sl_a=a, sl_b=b, sl_rezims="salidzinajums", sl_vh="Mājās", sl_va="Izbraukumā", sl_logs=None)


def _sl_citas():
    st.session_state["sl_rezims"] = "izvele"


CMP_PELD_SKRIPTS = """
<script>
(function () {
  var w = window.parent, d = w.document;
  var vecais = w.__cmpPeld; if (vecais) { try { vecais.stop(); } catch (e) {} }      // iepriekšējā kadra klausītāji tiek noņemti
  var raf = 0;
  function noteikt() {
    raf = 0;
    var fl = d.querySelectorAll('.cmp-float'); if (!fl.length) return;
    var logo = d.querySelector('.st-key-cmp_head .cmp-logo') || d.querySelector('.cmp-head .cmp-logo');
    var josla = d.querySelector('.st-key-topbar'), augsa = 8;
    if (josla) {                                   // ja augšējā josla ir "pielipusi" ekrāna augšā, logo novieto zem tās
      var jr = josla.getBoundingClientRect();
      if (getComputedStyle(josla).position === 'sticky' && jr.top >= -1 && jr.top < 40 && jr.bottom > 0) augsa = Math.max(augsa, jr.bottom + 8);
    }
    var redzams = true;
    if (logo) { var r = logo.getBoundingClientRect(); redzams = r.bottom > augsa + 2; }   // redzama kaut daļa no virsraksta logo
    fl.forEach(function (f) { f.style.setProperty('--cf-top', augsa + 'px'); f.classList.toggle('on', !redzams); });
  }
  function plan() { if (!raf) raf = w.requestAnimationFrame(noteikt); }
  d.addEventListener('scroll', plan, true);
  w.addEventListener('resize', plan);
  var mo = new w.MutationObserver(plan); mo.observe(d.body, { childList: true, subtree: true });
  w.__cmpPeld = { stop: function () { d.removeEventListener('scroll', plan, true); w.removeEventListener('resize', plan); mo.disconnect();
    d.querySelectorAll('.cmp-float.on').forEach(function (f) { f.classList.remove('on'); }); } };
  window.addEventListener('pagehide', function () { try { if (w.__cmpPeld) w.__cmpPeld.stop(); } catch (e) {} });
  plan();
})();
</script>
"""


def sl_peldosie_html(home, away):
    """Mazie logo, kas parādās ekrāna augšā virs attiecīgās puses, kad virsraksta logo ir aizritināti prom (ar komandas krāsu zem logo)."""
    e = _html.escape
    k = lambda kods, kl: (f'<div class="cf-k"><span class="cf-c"><img src="{e(da.logo_url(kods))}" alt="{e(kods)}" title="{e(da.pilns_nosaukums(kods))}">'   # noqa: E731
                          f'<i class="{kl}"></i></span></div>')
    return f'<div class="cmp-float" aria-hidden="true">{k(home, "a")}{k(away, "b")}</div>'


def sl_kopsavilkums(scope, n):
    """Komandu kopsavilkums salīdzinājumam. Over 5.5 tiek aprēķināts šeit, ja datu_apstrade.py vēl ir vecā versija bez tā."""
    k = da.kopsavilkums(DF, scope, n)
    if not k.empty and "Over55" not in k.columns:
        sub_ = da.filtret(DF, scope, n)
        k["Over55"] = (sub_["tot_reg_goals"] > 5.5).groupby(sub_["komanda"]).mean() * 100
    return k


def _sl_tog(atslega, v):          # pārslēdzējs: klikšķis ieslēdz, atkārtots klikšķis uz tā paša izslēdz (tad - visas spēles)
    st.session_state[atslega] = None if st.session_state.get(atslega) == v else v


def lapa_salidzinat():
    kodi = sorted(da.KOMANDAS, key=lambda k: da.KOMANDAS[k])
    if "sl_a" not in st.session_state:                       # noklusējums: nākamā tuvākā spēle no kalendāra (mājinieki kreisajā pusē)
        nak = da.nakamas_speles(KAL, 1)
        if nak is not None and not nak.empty:
            st.session_state["sl_a"], st.session_state["sl_b"] = nak.iloc[0]["majas_komanda"], nak.iloc[0]["viesu_komanda"]
        else:
            st.session_state["sl_a"], st.session_state["sl_b"] = kodi[0], kodi[1]

    # 1) komandu izvēle: rullīši, "VS" un poga "Salīdzināt"
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
        with st.container(key="sl_poga_josla"):          # moderna tumša poga lapas vidū (nevis pa visu platumu)
            st.button("Salīdzināt", disabled=(kom_a == kom_b), on_click=_sl_salidzinat, args=(kom_a, kom_b), key="sl_poga")
        return

    # 2) salīdzinājums: rullīši pazūd; virsraksts [mājinieki] [VS + maiņas poga] [viesi], zem nosaukumiem katrai komandai Mājās/Izbraukumā
    home, away = st.session_state["sl_a"], st.session_state["sl_b"]
    vh = st.session_state.setdefault("sl_vh", "Mājās")
    va = st.session_state.setdefault("sl_va", "Izbraukumā")
    logs = st.session_state.get("sl_logs")
    n = SL_LOGI.get(logs)
    kopa = da.kopsavilkums(DF, "Visas", None)
    kh, ka = sl_kopsavilkums(vh or "Visas", n), sl_kopsavilkums(va or "Visas", n)
    a = kh.loc[home] if home in kh.index else None
    b = ka.loc[away] if away in ka.index else None
    gp = lambda k: int(kopa.loc[k, "GP"]) if k in kopa.index else 0                    # noqa: E731

    with st.container(key="cmp_head"):
        with st.container(key="cmp_ch"):
            st.markdown(sl_komanda_html(home, "a", gp(home), int(a["GP"]) if a is not None else 0, True), unsafe_allow_html=True)
            with st.container(key="cmp_vh"):
                for v in ("Mājās", "Izbraukumā"):
                    st.button(ETIKETES.get(v, v), key=f"slvh_{v}", type="primary" if v == vh else "secondary", on_click=_sl_tog, args=("sl_vh", v))
        with st.container(key="cmp_cm"):
            st.markdown('<div class="cmp-vs">VS</div>', unsafe_allow_html=True)
            with st.container(key="sl_maina"):
                st.markdown(f'<img class="maina-ik" src="{MAINA_IKONA}" alt="Salīdzināt citas komandas">', unsafe_allow_html=True)
                st.button("Salīdzināt citas komandas", key="sl_maina_poga", on_click=_sl_citas)
        with st.container(key="cmp_ca"):
            st.markdown(sl_komanda_html(away, "b", gp(away), int(b["GP"]) if b is not None else 0, False), unsafe_allow_html=True)
            with st.container(key="cmp_va"):
                for v in ("Mājās", "Izbraukumā"):
                    st.button(ETIKETES.get(v, v), key=f"slva_{v}", type="primary" if v == va else "secondary", on_click=_sl_tog, args=("sl_va", v))
    with st.container(key="sl_per"):                       # pēdējās 5 / 10: ieslēdz ar klikšķi, izslēdz ar atkārtotu klikšķi (tad - visa sezona)
        for p in SL_LOGI:
            st.button(p, key=f"slp_{p}", type="primary" if p == logs else "secondary", on_click=_sl_tog, args=("sl_logs", p))

    rindas = sl_peldosie_html(home, away)
    for grupa, metrikas in SALIDZ_METRIKAS:
        rindas += f'<div class="cmp-group">{_html.escape(grupa.upper())}</div>'
        for nos, pask, k, labak, dec in metrikas:
            rindas += sl_rinda_html(nos, pask, a.get(k) if a is not None else None, b.get(k) if b is not None else None, labak, dec)
    rindas += f'<div class="cmp-l5">{sl_pedejas5_html(home, "l")}{sl_pedejas5_html(away, "r")}</div>'
    st.markdown(f'<div class="cmp-wrap">{rindas}</div>', unsafe_allow_html=True)
    with st.container(key="cmp_skripts"):                 # peldošo logo skripts (neredzams; stabila vieta)
        try:
            import streamlit.components.v1 as components
            components.html(CMP_PELD_SKRIPTS, height=0)
        except Exception:
            pass


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
    return {"Mājās": " · mājās", "Izbraukumā": " · viesos"}.get(scope, "")


def _tips(spec):
    """(vārdnīca, type_config, tips) no Streamlit column_config objekta (der gan jaunajam, gan vecajam formātam): 'image', 'progress', 'number', 'text'..."""
    d = spec if isinstance(spec, dict) else {}
    tc = d.get("type_config") or {}
    return d, tc, str(tc.get("type") or d.get("type") or "").lower().replace("column", "")


def _fmt_v(v, f=None):
    """Vērtība tekstā. f: '{:.2f}' vai printf stils '%.2f' (kā Streamlit column_config). Bez formāta: veseli skaitļi bez komata, citādi līdz 2 zīmēm bez liekām nullēm."""
    if v is None or (not isinstance(v, (str, bool)) and pd.isna(v)):
        return "–"
    if f:
        try:
            return f.format(v) if "{" in f else (f % v)
        except Exception:
            pass
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


_TABULU_SKAITS = [0]          # tabulu numurs šajā izpildē (stabila atslēga katras tabulas kārtošanas izvēlei)


def _tk_set(key, k, dilst):
    st.session_state[key] = None if k is None else (k, dilst)


def _kartosanas_izvele(key, opcijas, izv):
    """Moderna kārtošanas izvēlne virs tabulas: neliela tumša poga "⇅ Kārtot: Kolonna ↓", kas atver izvēlni ar kolonnām un virzienu."""
    k0, d0 = izv if izv else (None, True)
    etik = f"⇅  {opcijas[k0]}  {'↓' if d0 else '↑'}" if k0 in opcijas else "⇅  Kārtot"
    with st.container(key=f"tbs_{key}"):
        try:
            pop = st.popover(etik)
        except Exception:
            return
        with pop:
            with st.container(key=f"tbm_{key}"):
                st.markdown('<div class="tbm-lab">Kārtot pēc</div>', unsafe_allow_html=True)
                with st.container(key=f"tbmk_{key}"):
                    for i, (k, lbl) in enumerate(opcijas.items()):
                        st.button(lbl, key=f"{key}__k{i}", type="primary" if k == k0 else "secondary", on_click=_tk_set, args=(key, k, d0))
                st.markdown('<div class="tbm-lab">Secība</div>', unsafe_allow_html=True)
                with st.container(key=f"tbmd_{key}"):
                    st.button("↓ No lielākā", key=f"{key}__dl", type="primary" if (k0 and d0) else "secondary", on_click=_tk_set, args=(key, k0 or next(iter(opcijas)), True))
                    st.button("↑ No mazākā", key=f"{key}__dm", type="primary" if (k0 and not d0) else "secondary", on_click=_tk_set, args=(key, k0 or next(iter(opcijas)), False))
                    if k0:
                        st.button("Noklusējums", key=f"{key}__dr", on_click=_tk_set, args=(key, None, True))


def df_html(df, config=None, formati=None, prog=None, paskaidr=None, logo_kol=(), burbuli=None, bur_kol=None, platas=(), indekss=False, kartot=True):
    """
    Visas lietotnes tabulas: DataFrame kā caurspīdīga HTML tabula ar paskaidrojumiem virsrakstos (uzvedot peli).
    config: Streamlit column_config (None = kolonna paslēpta; image = logotips; progress = josla; format = skaitļa formāts; width='large' = plata teksta kolonna);
    formati/prog/logo_kol/platas: tas pats tieši; burbuli: saraksts (pa vienam katrai rindai) ar HTML burbuli kolonnai bur_kol (spēļu saraksts uz "Sp.").
    """
    if df is None or df.empty:
        st.info("Nav datu šim skatam.")
        return
    e = _html.escape
    config, formati, prog, paskaidr = config or {}, formati or {}, prog or {}, paskaidr or {}
    if indekss:
        df = df.reset_index()
    df = df.reset_index(drop=True)
    kol = []
    for k in df.columns:
        spec = config.get(k, False)
        if spec is None:                                   # paslēpta kolonna
            continue
        d, tc, t = _tips(None if spec is False else spec)
        label = k if d.get("label") is None else d.get("label")
        nonnull = df[k].dropna()
        teksts = (not nonnull.empty) and isinstance(nonnull.iloc[0], str)
        kol.append({"k": k, "label": label, "logo": k in logo_kol or t == "image", "prog": prog.get(k) or ((tc.get("min_value", d.get("min_value", 0)), tc.get("max_value", d.get("max_value", 100))) if t == "progress" else None),
                    "fmt": formati.get(k) or tc.get("format") or d.get("format"), "wide": k in platas or d.get("width") == "large",
                    "help": d.get("help") or paskaidr.get(k) or palidziba(k), "teksts": teksts})
    # kārtošanas izvēlne (tabulām ar vismaz 4 rindām); izvēle tiek saglabāta sesijā katrai tabulai atsevišķi
    if kartot and len(df) >= 4:
        _TABULU_SKAITS[0] += 1
        key = f"tbk{_TABULU_SKAITS[0]}_{zlib.crc32('|'.join(map(str, df.columns)).encode()) % 100000}"
        opcijas = {c["k"]: str(c["label"]) for c in kol if not c["logo"] and str(c["label"]) not in ("#", "") and not c["wide"]}
        izv = st.session_state.get(key)
        if izv and izv[0] not in opcijas:
            izv = None
        if len(opcijas) >= 2:
            _kartosanas_izvele(key, opcijas, izv)
        if izv:
            k, dilst = izv
            s = df[k]
            atsl = s.astype(str).str.lower() if s.dtype == object else pd.to_numeric(s, errors="coerce")
            seciba = atsl.sort_values(ascending=not dilst, na_position="last", kind="stable").index
            df = df.loc[seciba].reset_index(drop=True)
            if burbuli is not None:
                burbuli = [burbuli[i] for i in seciba]
            if "#" in df.columns:
                df["#"] = range(1, len(df) + 1)
    # pielīpošās pirmās kolonnas (redzams, kurai komandai / spēlētājam pieder cipari, ritinot pa labi): "#" + logo vai pirmā kolonna
    pielip = 2 if (len(kol) > 1 and str(kol[0]["label"]) == "#" and kol[1]["logo"]) else 1
    for n_, c in enumerate(kol):
        c["pl"] = f" c{n_}" if n_ < pielip else ""
    galva = ""
    for c in kol:
        sad = f'<span class="tbh" tabindex="0">{e(str(c["label"]))}<span class="bubble">{e(c["help"])}</span></span>' if c["help"] and c["label"] != "" else e(str(c["label"]))
        galva += f'<th class="{("l" if (c["teksts"] and not c["logo"]) else "") + c["pl"]}">{sad}</th>'
    rindas = ""
    for i, (_, r) in enumerate(df.iterrows()):
        rinda = ""
        for c in kol:
            v, k = r[c["k"]], c["k"]
            ns = len(rinda)
            if c["logo"]:
                rinda += f'<td class="lg"><img class="tb-logo" width="38" height="38" src="{e(str(v))}" alt=""></td>' if isinstance(v, str) and v else '<td class="lg"></td>'
            elif k == bur_kol and burbuli is not None and burbuli[i]:
                rinda += f'<td class="tbsp" tabindex="0"><span class="spw">{_fmt_v(v, "{:.0f}")}<span class="bubble">{burbuli[i]}</span></span></td>'
            elif c["prog"] is not None:
                lo, hi = c["prog"]
                platums = 0 if pd.isna(v) else max(0, min(100, (v - lo) / (hi - lo) * 100))
                rinda += f'<td><div class="pb"><i style="width:{platums:.0f}%"></i><b>{_fmt_v(v, c["fmt"])}</b></div></td>'
            elif isinstance(v, bool):
                rinda += f'<td class="l">{"✓" if v else ""}</td>'
            elif isinstance(v, (pd.Timestamp, datetime.date)):
                rinda += f'<td class="l">{v:%d.%m.%Y}</td>'
            elif isinstance(v, str):
                rinda += f'<td class="{"w" if c["wide"] else "l"}">{e(v)}</td>'
            elif isinstance(v, (int, float, np.integer, np.floating)) or v is None:
                rinda += f'<td>{_fmt_v(v, c["fmt"])}</td>'
            else:
                rinda += f'<td class="l">{e(str(v))}</td>'
            if c["pl"]:                                       # pielīpošā kolonna: klase pirmajā <td>
                sun = rinda[ns:]
                sun = sun.replace('<td class="', f'<td class="{c["pl"].strip()} ', 1) if sun.startswith('<td class="') else sun.replace("<td", f'<td class="{c["pl"].strip()}"', 1)
                rinda = rinda[:ns] + sun
        rindas += f"<tr>{rinda}</tr>"
    garsa = " garsa" if len(df) > 12 else ""
    st.markdown(f'<div class="tb-wrap{garsa}"><table class="tb"><thead><tr>{galva}</tr></thead><tbody>{rindas}</tbody></table></div>', unsafe_allow_html=True)


def lapa_periodi():
    c0, c1, c2 = st.columns([1.1, .7, .9])
    with c0:
        p = int(izvele("Hokeja periods", ["1. periods", "2. periods", "3. periods"], key="per_p")[0])
    with c1:
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="per_scope")
    with c2:
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="per_logs")
    kolonna = "Starpiba"                                   # noklusējuma secība; citu secību izvēlas tabulas izvēlnē "Kārtot"
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
    c1, c2 = st.columns(2)
    with c1:
        n = int(izvele("Pēdējās spēles", ["5", "10"], key="fm_n"))

    res = da.kopsavilkums(DF, "Visas", n)
    res["Forma"] = da.forma(DF, n)
    kol, asc = "G", False                                  # noklusējums: visvairāk gūto vārtu; citu secību - tabulas izvēlnē "Kārtot"
    burbuli = spelu_burbuli("Visas", n, lambda r: (r.g_reg, r.z_reg), f"Pēdējās {n} spēles · pamatlaika vārti (komanda:pretinieks)", set(res.index))
    tabula(res, {"GP": "Sp.", "W": "U", "L": "Z", "OTL": "ZPL", "PTS": "Punkti",
                 "G": "Gūti vārti", "Z": "Ielaisti vārti", "Starpiba": "Starpība", "Forma": "Forma"},
           sort_col=kol, ascending=asc, burbuli=burbuli)


# ============================================================================
# LAPA: OVER / UNDER
# ============================================================================
def lapa_over_under():
    c1, c3, c4 = st.columns(3)
    with c1:
        linija = float(izvele("Līnija", ["5.5", "6.5", "7.5"], default="6.5", key="ou_l"))
    with c3:
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="ou_s")
    with c4:
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", default="Pēdējās 10", key="ou_n")
    res = da.over_under(DF, linija, scope, LOGI[logs])
    kol = "Over"                                           # noklusējums; Under u.c. secība - tabulas izvēlnē "Kārtot"
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
    c1, c2 = st.columns(2)
    with c1:
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="pp_s")
    with c2:
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="pp_n")
    kol = "PPG"                                            # noklusējums; citu secību izvēlas tabulas izvēlnē "Kārtot"
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
    c1, c2, c3 = st.columns(3)
    with c1:
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="nr_s")
    with c2:
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="nr_n")
    with c3:
        perioda = sledzis("Hokeja periods", ["1. periods", "2. periods", "3. periods"], "Visi periodi", key="nr_p")
    d1, d2, d3 = st.columns(3)
    with d1:
        metrika = izvele("Rādītājs", ["Noraidījumu skaits", "Sodu minūtes"], key="nr_m")
    with d2:
        vertiba = sledzis("Vērtība", ["Vidēji spēlē"], "Kopā", default="Vidēji spēlē", key="nr_v")
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
        kolonnas, pask = {"GP": "Sp."}, {}
        for nos, p in pkarte.items():
            kolonnas[f"{vkods}_{p}"] = nos
            pask[nos] = apraksts(vkods, p)
        tabula(res, kolonnas, sort_col=f"{vkods}_kopa", paskaidr=pask,
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
               "Noraidījumi = tikai minor sodi (dubultais minor = 2); major, 10 min disciplinārie sodi un kautiņi netiek skaitīti. Kopā = 1.–3. periods kopā, papildlaiks netiek ieskaitīts. "
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
        ["Pārskats", "Mājās / viesos", "Pēdējās spēles", "Periodi", "Noraidījumi un PP", "Nākamās spēles"])
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
        x[2].metric("Viesos", fmt(away10["g_reg"].mean()), border=True)
        y = st.columns(3)
        for i, p in enumerate((1, 2, 3)):
            y[i].metric(f"{p}. periods", fmt(last10[f"g_p{p}"].mean()), border=True)

    with t_mi:
        rindas = {}
        for nos, sc, n in [("Visas", "Visas", None), ("Mājās", "Mājās", None), ("Viesos", "Izbraukumā", None),
                           ("Pēdējās 5", "Visas", 5), ("Pēdējās 5 mājās", "Mājās", 5),
                           ("Pēdējās 5 viesos", "Izbraukumā", 5), ("Pēdējās 10", "Visas", 10)]:
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
                           "Mājās": int(mh[f"diff_p{p}"].sum()), "Viesos": int(ma[f"diff_p{p}"].sum()),
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
                "Vieta": ["Mājās" if m == kom else "Viesos" for m in nak["majas_komanda"]]}),
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
            L = L.sort_values(kartot, ascending=False).head(60).copy()
            L["Komanda"] = L["Komanda"].map(da.logo_url)                       # komandas saīsinājuma vietā logotips
            rtabula(L, hide_index=True, width="stretch", kartot=False,
                         column_config={"playerId": None, "Komanda": st.column_config.ImageColumn("Komanda", width="small"),
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
            G = G.sort_values("SVpct", ascending=False).rename(columns={"TOI": "TOI_kopa"}).copy()
            G["Komanda"] = G["Komanda"].map(da.logo_url)
            rtabula(G, hide_index=True, width="stretch", kartot=False,
                         column_config={"playerId": None, "Komanda": st.column_config.ImageColumn("Komanda", width="small"),
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
        st.caption("Noraidījumi = abu komandu minor sodu skaits spēles pamatlaikā (dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem), ko pieskaita katram spēles tiesnesim. "
                   "Datu apjoms: Maz datu < 8 spēles, Vidēji 8–19, Pietiekami 20+ (abas sezonas kopā).")

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
            f"- **Sērija pēc vietas.** Sarakstā tiek iekļauti arī spēlētāji, kas negūst rādītāju katrā spēlē, bet gūst to {da.VIETAS_SERIJAS_SLIEKSNIS} un vairāk "
            "mājas (🏠) vai viesu (✈️) spēlēs pēc kārtas (skaitot tikai attiecīgās vietas spēles).\n"
            "- **Sp. logā:** uzvedot peli uz spēļu skaita, redzams, vai spēle bija mājās vai viesos un ko spēlētājs tajā guva (jaunākā spēle augšā).\n"
            "- **Gaidāmais nākamajā spēlē** = 75% sezonas vidējais + 25% pēdējo spēļu vidējais (abi pievilkti pie līgas vidējā). "
            "Hokejā karstumam ir neliela noturība: lielu daļu uzliesmojumu veido veiksme, tāpēc prognoze ir piesardzīga.\n"
            "- Punkti = vārti + piespēles (G+A), tāpēc atsevišķa G+A kolonna nav vajadzīga.")

    max_gp = int(sk.groupby("playerId").size().max())
    s1, _ = st.columns([1, 2])                              # minimālais spēļu skaits: uzreiz zem skaidrojuma
    with s1:
        min_sp = st.slider("Minimālais spēļu skaits logā", 2, 10, max(2, min(3, max_gp)), key="ks_min",
                               help="Viena spēle nekad netiek ņemta vērā; agrā sezonā logā var būt mazāk spēļu")
    c1, c2, c3 = st.columns([1, 1.2, .75])                  # Rādītājs, Logs, Pozīcija vienā rindā
    with c1:
        metrika = izvele("Rādītājs", ["Punkti", "Vārti", "Piespēles"], key="ks_m")
    with c2:
        logs_t = izvele("Logs", ["Pēdējās 3", "Pēdējās 5", "Pēdējās 10"], default="Pēdējās 5", key="ks_l")
    with c3:
        poz = sledzis("Pozīcija", ["Uzbrucēji", "Aizsargi"], "Visi", key="ks_poz")

    mkods = {"Punkti": "punkti", "Vārti": "vardi", "Piespēles": "piespeles"}[metrika]
    nos = {"punkti": "punkti", "vardi": "vārti", "piespeles": "piespēles"}[mkods]
    logs = int(logs_t.split()[-1])
    res = da.karstie_speletaji(sk, mkods, logs, min_sp)
    res = res[(res["z"].notna()) | res["tr_serija"]] if not res.empty else res      # indekss vai sērija mājās/izbraukumā
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
        "Spēlētājs": res["Speletajs"].values, "Komanda": [da.logo_url(k) for k in res["Komanda"]], "Poz": res["Poz"].values,
        "Statuss": [(" ".join(x for x in (("🔥🔥" if z >= 3 else "🔥" if z >= 2 else ""),
                                          (f"🏠{int(m)}" if m >= da.VIETAS_SERIJAS_SLIEKSNIS else ""),
                                          (f"✈️{int(v)}" if v >= da.VIETAS_SERIJAS_SLIEKSNIS else "")) if x)) or "–"
                    for z, m, v in zip(res["z"].fillna(0), res["ser_majas"], res["ser_viesos"])],
        "Sp. logā": res["n_w"].astype(int).values,
        "G": res["G_w"].astype(int).values, "A": res["A_w"].astype(int).values, "P": res["P_w"].astype(int).values,
        vid_w: res["vid_w"].values, vid_s: res["vid_sez"].values,
        "Sērija": res["serija"].astype(int).values,
        ind: res["z"].values, gaid: res["gaidamie_nakamaja"].values,
        "Sezona īsumā": [f"{int(r.GP)} sp · {int(r.G_sez)}G {int(r.A_sez)}A {int(r.P_sez)}P · {int(r.SOG_sez)} metieni"
                         for r in res.itertuples()],
        "Kāpēc karsts": [da.karstuma_teksts(r, mkods) for _, r in res.iterrows()],
    })
    # burbulis kolonnai "Sp. logā": spēlētāja pēdējās spēles (jaunākā augšā), mājās vai izbraukumā, un ko viņš tajā guva
    speles_df = da.speletaju_speles(sk[sk["playerId"].isin(res.index)], RAW, logs)
    burbuli = []
    for pid in res.index:
        g = speles_df[speles_df["playerId"] == pid]
        ier = [{"teksts": f"{r.datums:%d.%m.} · {ETIKETES.get(r.vieta, r.vieta)} vs {r.pretinieks}", "piez": f"{int(r.goals)}G {int(r.assists)}A ({int(r.points)}P)"}
               for r in g.itertuples()]
        burbuli.append(burbula_html(f"Pēdējās {logs} spēles (jaunākā augšā)", ier))
    pask = {
        "Sp. logā": "Spēles izvēlētajā logā. Uzvedot peli, redzams, vai spēle bija mājās vai viesos un ko spēlētājs tajā guva (jaunākā augšā)",
        "Statuss": f"🔥 karsts (indekss 2+), 🔥🔥 ļoti karsts (3+); 🏠/✈️ ar skaitli = rādītājs tik mājas/viesu spēlēs pēc kārtas (no {da.VIETAS_SERIJAS_SLIEKSNIS})",
        "G": "Vārti izvēlētajā logā", "A": "Piespēles izvēlētajā logā", "P": "Punkti (vārti + piespēles) izvēlētajā logā",
        vid_w: f"Vidēji {nos} spēlē izvēlētajā logā", vid_s: f"Vidēji {nos} spēlē visā sezonā",
        ind: f"Faktiskie {nos} logā pret gaidāmajiem (z-vērtība): 0 = parasts līmenis, 2+ = karsts, 3+ = ļoti karsts. "
             "Netiek rēķināts, ja logā ir pārāk maz spēļu vai rādītājs bijis tikai vienā spēlē",
        gaid: f"Piesardzīgs novērtējums: 75% sezonas vidējais + 25% pēdējo spēļu vidējais ({nos} spēlē), pievilkti pie līgas vidējā",
    }
    df_html(vis, formati={vid_w: "{:.2f}", vid_s: "{:.2f}", ind: "{:.1f}", gaid: "{:.2f}"}, prog={ind: (0, 5)}, paskaidr=pask,
            logo_kol=("Komanda",), burbuli=burbuli, bur_kol="Sp. logā", platas=("Kāpēc karsts",))
    st.caption(f"Logs: {logs_t.lower()} (ja spēlētājs nospēlējis mazāk, tiek ņemtas visas viņa spēles). "
               "Sezonas sākumā izlase ir maza, tāpēc rangs var strauji mainīties. Tā ir statistikas indikācija, nevis garantija.")


# ============================================================================
# LAPA: ČATS
# ============================================================================
CATA_PIEMERI = ["Kuras komandas saņem visvairāk noraidījumu?", "Kā klājas NJD pēdējās 5 spēlēs?", "Kuri spēlētāji šobrīd ir karsti?",
                "Vakardienas rezultāti", "Salīdzini TOR un MTL", "Kuri tiesneši soda visvairāk?"]
CATA_RIKU_NOS = {"komandas_statistika": "Komandas statistika", "ligas_tabula": "Komandu tabula", "speles": "Spēles", "speletaji": "Spēlētāji",
                 "karstie_speletaji": "Karstie spēlētāji", "vartsargi": "Vārtsargi", "tiesnesi": "Tiesneši", "kalendars": "Kalendārs",
                 "salidzinat_komandas": "Komandu salīdzinājums"}
MAX_CATA_JAUTAJUMI = 40       # jautājumu skaits vienā sesijā (ierobežo izmaksas, ja ieslēgts Claude)


def _secret(nos, noklusejums=None):
    try:
        return st.secrets[nos]
    except Exception:
        return noklusejums


def _cata_dati():
    cur, prev, _ = ielasit_tiesnesus(VERSIJA)
    return cats.Dati(RAW, DF, KAL, ielasit_papildu("speletaji", VERSIJA), ielasit_papildu("vartsargi", VERSIJA),
                     cur, prev, ielasit_planotos(VERSIJA), modelis)


def _cata_zina(z):
    with st.chat_message(z["loma"]):
        st.markdown(z["teksts"])
        for nos, _, tab in z.get("tabulas", []):
            with st.expander(f"Dati: {CATA_RIKU_NOS.get(nos, nos)}"):
                rtabula(tab, hide_index=True, width="stretch")


def lapa_cats():
    st.title("Čats")
    atslega = _secret("ANTHROPIC_API_KEY")
    klients, kluda = None, None
    if atslega:
        try:
            import anthropic
            klients = anthropic.Anthropic(api_key=atslega)
        except Exception as e:
            kluda = f"Claude nav pieejams ({type(e).__name__}); pārbaudi, vai requirements.txt ir 'anthropic'."
    modelis_nos = _secret("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    if klients:
        st.caption("Jautā brīvā formā par komandām, spēlētājiem, tiesnešiem un spēlēm. Atbildes balstās tikai uz šīs lietotnes datiem; "
                   "jautājumi un datu fragmenti tiek nosūtīti Anthropic API apstrādei.")
    else:
        st.info("Darbojas vienkāršā meklēšana pēc atslēgvārdiem un komandu/spēlētāju nosaukumiem. Lai čats saprastu brīvas frāzes, "
                "Streamlit Secrets pievieno ANTHROPIC_API_KEY.")
        if kluda:
            st.warning(kluda)

    vesture = st.session_state.setdefault("cats_vesture", [])
    for z in vesture:
        _cata_zina(z)

    jaut = None
    if not vesture:
        st.markdown("**Piemēri**")
        for i, piemers in enumerate(CATA_PIEMERI):
            if st.button(piemers, key=f"cp{i}", width="stretch"):
                jaut = piemers
    iev = st.chat_input("Pajautā par komandām, spēlētājiem, tiesnešiem, rezultātiem…")
    jaut = iev or jaut
    if vesture:
        st.button("Notīrīt sarunu", on_click=lambda: st.session_state.update(cats_vesture=[]), key="cats_clear")

    if not jaut:
        return
    if sum(1 for z in vesture if z["loma"] == "user") >= MAX_CATA_JAUTAJUMI:
        st.warning("Sasniegts jautājumu limits šajā sesijā. Nospied «Notīrīt sarunu», lai sāktu no jauna.")
        return
    vesture.append({"loma": "user", "teksts": jaut})
    _cata_zina(vesture[-1])
    with st.chat_message("assistant"):
        with st.spinner("Meklēju datos…"):
            dati = _cata_dati()
            try:
                if klients:
                    api = [{"role": z["loma"], "content": z["teksts"]} for z in vesture[-9:]]
                    while api and api[0]["role"] != "user":
                        api.pop(0)
                    atb, tabulas = cats.atbildet_ar_claude(klients, modelis_nos, api, dati)
                else:
                    atb, tabulas = cats.vienkarsa_meklesana(jaut, dati)
            except Exception as e:
                try:
                    teksts, tabulas = cats.vienkarsa_meklesana(jaut, dati)
                except Exception:
                    teksts, tabulas = "Neizdevās atrast datus.", []
                atb = f"Neizdevās sazināties ar Claude ({type(e).__name__}). Vienkāršās meklēšanas rezultāts: {teksts}"
        st.markdown(atb)
        for nos, _, tab in tabulas:
            with st.expander(f"Dati: {CATA_RIKU_NOS.get(nos, nos)}"):
                rtabula(tab, hide_index=True, width="stretch")
    vesture.append({"loma": "assistant", "teksts": atb, "tabulas": tabulas})
    del vesture[:-30]            # saglabā tikai pēdējās 30 ziņas


# ============================================================================
# NAVIGĀCIJA
# Struktūra ir šeit, vienā vietā: lapas var pārvietot starp grupām, grupas pārsaukt vai lapu izvilkt kā atsevišķu pogu
# ({"lapa": (...)} ieraksts bez grupas). Ikonas ir Material Symbols (fonts.google.com/icons).
# ============================================================================
def augseja_josla(aktiva):
    """Viena josla augšā: zīmols + atsevišķas pogas + grupas, kuru lapas parādās, uzvedot peli virsū (vai pieskaroties)."""
    pedejais = len(STRUKTURA) - 1
    with st.container(key="topbar"):
        with st.container(key="brand"):
            st.page_link(VISAS_LAPAS[0], label="NHL analītika")
        for i, (tips, nosaukums, saraksts) in enumerate(STRUKTURA):
            if tips == "lapa":
                akt = saraksts[0][1].title == aktiva.title
                with st.container(key=f"navs-{i}" + ("-akt" if akt else "")):
                    st.page_link(saraksts[0][1], label=nosaukums)
                continue
            aktivs = any(p.title == aktiva.title for _, p in saraksts)
            with st.container(key=f"navg-{i}" + ("-rr" if i == pedejais else "")):      # -rr: izvēlne līdzināta pie labās malas
                st.markdown(f'<div class="nav-title{" aktivs" if aktivs else ""}" tabindex="0">{nosaukums}</div>',
                            unsafe_allow_html=True)
                with st.container(key=f"navi-{i}"):
                    for j, (rec, p) in enumerate(saraksts):
                        with st.container(key=f"navp-{i}-{j}" + ("-akt" if p.title == aktiva.title else "")):
                            st.page_link(p, label=rec[1], icon=f":material/{rec[3]}:")


IZVELNES_SKRIPTS = """
<script>
(function () {
  var w = window.parent, d = w.document;
  function josla() { return d.querySelector('.st-key-topbar'); }
  // Streamlit var pārbūvēt šo kadru (piem., mainoties elementu secībai lapā). Iepriekšējā kadra klausītāji tiek noņemti, un katrs jauns kadrs
  // reģistrē savus; tāpēc izvēlnes nepaliek "iestrēgušas" (agrāk vecais kadrs bija likvidēts, bet tā iestatītais stāvoklis palika).
  var vecais = w.__nhlIzv;
  if (vecais) { try { vecais.reg.forEach(function (n) { d.removeEventListener(n[0], n[1], true); }); } catch (e) {} }
  function klik(e) {                      // nospiežot saiti joslā: aizver izvēlni un noņem fokusu
    var a = e.target.closest && e.target.closest('.st-key-topbar a');
    var b = josla();
    if (!a || !b) return;
    b.classList.add('nav-aizvert');
    if (d.activeElement && d.activeElement.blur) d.activeElement.blur();
  }
  function atvert(e) {                    // atkal ļauj atvērt, kad lietotājs uzved peli vai pieskaras grupas nosaukumam
    var t = e.target.closest && e.target.closest('.nav-title');
    var b = josla();
    if (t && b) b.classList.remove('nav-aizvert');
  }
  var raf = 0;
  function tbTop() {                      // tabulu virsraksti pielīp zem augšējās joslas, ja tā ir pielipusi ekrāna augšā
    raf = 0; var b = josla(), v = 0;
    if (b) { var r = b.getBoundingClientRect(); if (w.getComputedStyle(b).position === 'sticky' && r.top >= -1 && r.top < 40 && r.bottom > 0) v = Math.round(r.bottom + 6); }
    d.documentElement.style.setProperty('--tb-top', v + 'px');
  }
  function plan() { if (!raf) raf = w.requestAnimationFrame(tbTop); }
  var reg = [['click', klik], ['pointerover', atvert], ['touchstart', atvert], ['focusin', atvert], ['scroll', plan]];
  reg.forEach(function (n) { d.addEventListener(n[0], n[1], true); });
  plan();
  w.__nhlIzv = { reg: reg };
  var b0 = josla(); if (b0) b0.classList.remove('nav-aizvert');          // jauns kadrs = tīrs sākums
  function tirit() {                       // kadrs tiek likvidēts: noņem savus klausītājus un iestrēgušo stāvokli
    try { reg.forEach(function (n) { d.removeEventListener(n[0], n[1], true); }); if (w.__nhlIzv && w.__nhlIzv.reg === reg) w.__nhlIzv = null; var b = josla(); if (b) b.classList.remove('nav-aizvert'); } catch (e) {}
  }
  window.addEventListener('pagehide', tirit);
  window.addEventListener('unload', tirit);
})();
</script>
"""

if NAV_REZIMS == "pielagots":
    augseja_josla(lapas)
    with st.container(key="nav_skripts"):       # stabila pozīcija: skripta kadrs netiek pārbūvēts, mainoties citiem elementiem
        try:
            import streamlit.components.v1 as components
            components.html(IZVELNES_SKRIPTS, height=0)
        except Exception:       # skripts ir tikai uzlabojums: bez tā izvēlne aizveras, nospiežot jebkur citur
            pass
lapas.run()

# ===== app.py beigas (ja šī rinda redzama GitHub failā, fails ir augšupielādēts pilnīgi) =====
