"""
NHL analītika – Streamlit lietotne (nhl-stats-lv.streamlit.app, repozitorijs barakarmy/nhl-stats).

KĀ DATI NONĀK LIETOTNĒ
----------------------
Lietotne pati NHL datus nevāc: tā tikai nolasa CSV failus no repozitorija mapes sezonas/ (aktīvā sezona; iepriekšējās – sezonas/vesture/<sezona>/).
Šos failus atjaunina divas GitHub Actions darbplūsmas (.github/workflows/), un katru no tām palaiž divi grafiki:

1) NHL Daily Update (.github/workflows/daily.yml → python kalendars.py, pēc tam python nhl_dati.py --vieglais)
   - Avots: NHL oficiālā statistika (api-web.nhle.com: score, landing, boxscore, play-by-play, right-rail).
   - Raksta: sezonas/speles.csv (spēles, periodi, metieni, minor sodi, vairākums), sezonas/speletaji.csv, sezonas/vartsargi.csv,
     sezonas/varti.csv, sezonas/tiesnesi.csv (faktiskie tiesneši) un sezonas/nhl_kalendars.csv (nākamās RS un PO spēles 60 dienas uz priekšu).
   - Palaišana:
       a) cron-job.org katru dienu 08:40 pēc Rīgas laika (workflow_dispatch caur GitHub API) – galvenais, precīzs grafiks;
       b) GitHub paša grafiks '15 8 * * *' (UTC) = 11:15 Rīgā vasaras laikā / 10:15 ziemas laikā – rezerve (var kavēties).
   - Ar roku (Actions → Run workflow): datumu intervāls, "atjaunot" (pārrakstīt) vai "pēdējās 8h / 4h / 2h".
   - Veiksmīgas palaišanas laiku raksta sezonas/pedeja_atjaunosana.json (lietotnē: "Pēdējā atjaunošana").
   - Statistika lietotnē = tikai pamatlaiks; papildlaiks un metienu sērijas tiek krāti atsevišķi (sadaļa OT / SO).

2) NHL Referees (.github/workflows/referees.yml → python tiesnesi_planotie.py)
   - Avots: Scouting The Refs (dienas ieraksts "Tonight's NHL Referees and Linespersons"), rezerve: NHL right-rail.
   - Raksta: sezonas/tiesnesi_planotie.csv (pirms spēlēm paziņotie tiesneši).
   - Palaišana:
       a) cron-job.org ik 30 minūtes 14:00–23:30 pēc Rīgas laika (workflow_dispatch) – galvenais;
       b) GitHub grafiks '7,22,37,52 12-23 * * *' (UTC) – rezerve.
   - Katra palaišana vispirms ātri pārbauda (~10 s), vai kādai spēlei tuvāko 6 stundu laikā trūkst tiesnešu;
     pilna ielāde notiek tikai tad (taupa GitHub Actions minūtes). Piespiedu ielāde: Run workflow → "Ielādēt tiesnešus vienmēr".
   - Lietotne papildus pati (tiešsaistē, ik 10 min, ar 8 s laika limitu) pārbauda Scouting The Refs spēlēm, kurām failā tiesnešu vēl nav.

!!! cron-job.org darbi izmanto GitHub "fine-grained" žetonu (tikai Actions: Read and write repozitorijam nhl-stats),
!!! kura derīgums beidzas 2027-07-30. Līdz tam jāizveido jauns žetons (github.com/settings/personal-access-tokens/new)
!!! un jānomaina abu cron-job.org darbu galvenē "Authorization: Bearer ...". Citādi automātiskā atjaunināšana apstāsies.

CITI SVARĪGI FAKTI
------------------
- Parole: Streamlit Secrets → APP_PASSWORD. Pieteikšanās tiek atcerēta pārlūkā 3 dienas (localStorage paraksts, termiņš netiek pagarināts);
  saitēm uz jaunām cilnēm tiek pievienots īslaicīgs paraksts ?t=...
- Motīvs vienmēr gaišs (.streamlit/config.toml: base = "light").
- Noraidījumi = tikai minor sodi (dubultais minor = 2); bez major, 10 min disciplinārajiem un kautiņiem.
- Regulārā sezona (RS) un play-off (PO) vienmēr tiek skaitīti atsevišķi (speles.csv: speles_tips 2 = RS, 3 = PO; sezona, piem., 20262027).
  Statistikas lapās pārslēdzējs "Regulārā sezona · Play-off" parādās tikai tad, kad datos ir PO spēles; Līgas pārskats vienmēr RS;
  Rezultāti, Kalendārs, Prognozes, Karstākie spēlētāji un Tiesneši izmanto visas šīs sezonas spēles. Play-off zaudējums papildlaikā = loss.
- Koeficienti: koeficienti.py (.github/workflows/odds.yml, 3× dienā; The Odds API, atslēga – GitHub noslēpums ODDS_API_KEY)
  → sezonas/koeficienti.csv; salīdzinājumā zem komandām, Prognozēs – modelis pret tirgu.
- Modelis: modelis.py (Puasona regresija ar DB kā sākuma pieņēmumu); parametrus kalibrē lokāli ar
  python modelis.py --kalibret → sezonas/vesture/modelis_parametri.json (Prognožu lapa to nolasa).
- Vēsture: vesture.py (palaiž lokāli) lejupielādē iepriekšējās sezonas uz sezonas/vesture/<sezona>/; --arhivet pārvieto aktīvo sezonu uz arhīvu.
- Moduļi: datu_apstrade.py (aprēķini), lokacijas.py (attālumi, laika joslas), modelis.py (Puasona prognozes),
  rulli.py (komandu izvēle ar rullīšiem), fons.py (fona attēls), tiesnesi_planotie.py (tiesneši), nhl_dati.py (datu vākšana).
- APP_VERSIJA (zemāk) redzama katras lapas apakšā – palielini to pēc katras izmaiņas, lai pārbaudītu, vai Streamlit rāda jauno failu.
"""
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
    import fakti         # "Interesanti fakti": comebacks un 3. perioda statistika (fakti.py)
except ImportError:
    fakti = None
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

st.set_page_config(page_title="NHL stats", page_icon=":material/sports_hockey:", layout="wide",
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
ATCERETIES_DIENAS = 3          # pēc paroles ievades pārlūks to atceras 3 dienas (termiņš netiek pagarināts, lietojot lapu)
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
        st.session_state["password_correct"] = True          # saite uz jaunu cilni: saglabāto pieteikšanos nepagarina
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
        st.session_state["password_correct"] = True          # termiņš netiek pagarināts: parole jāievada vismaz reizi 3 dienās
        return True

    def entered():
        ievade = str(st.session_state.get("password", ""))
        st.session_state["password_correct"] = hmac.compare_digest(ievade.encode(), parole.encode())
        if st.session_state["password_correct"]:
            st.session_state["_auth_zetons"] = _auth_zetons(parole, int(time.time()) + ATCERETIES_DIENAS * 86400)
        st.session_state.pop("password", None)

    if saglabats is None and st.query_params.get("ievade") != "1":
        # Pārlūks vēl nav atbildējis, vai pieteikšanās ir saglabāta: paroles lauks netiek veidots vispār
        # (citādi pēc atbildes tas uz mirkli paliek redzams, kamēr lapa pārzīmējas).
        # Rezerve vienā elementā (pats sevi slēpj): ja atbilde nepienāk 4 s laikā, parādās saite uz paroles ievadi.
        st.markdown('<div style="visibility:hidden;animation:login-rezerve 0s linear 4s forwards;text-align:center;margin-top:35vh;font-size:.9rem">'
                    '<style>@keyframes login-rezerve { to { visibility: visible; } }</style>'
                    '<a href="?ievade=1" target="_top">Ievadīt paroli</a></div>', unsafe_allow_html=True)
        return False
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed", on_change=entered, key="password")
    if st.session_state.get("password_correct") is False:
        st.markdown('<div class="login-err">Incorrect password</div>', unsafe_allow_html=True)
    return False


APP_VERSIJA = "v1.1.35"   # formāts v1.1.N: N palielina par 1 ar katru izmaiņu      # palielini, kad augšupielādē jaunu app.py; redzama lapas apakšā
NAV_REZIMS = "pielagots"   # "pielagots" = augšējā josla ar hover izvēlnēm; "standarta" = Streamlit iebūvētā augšējā navigācija

NAV = [
    # zīmols "NHL stats" ved uz Fakti (atsevišķas pogas joslā tiem nav); sākumlapa vienmēr ir Karstākie spēlētāji
    {"zimols": ("lapa_fakti", "Fakti", "facts", "lightbulb")},
    # atsevišķas pogas joslā (bez izvēlnes); pirmā no tām (Karstākie spēlētāji) ir sākumlapa
    {"lapa": ("lapa_karstie", "Karstākie spēlētāji", "hot-players", "local_fire_department")},
    {"lapa": ("lapa_prognozes", "Prognozes", "predictions", "insights")},
    # grupas ar izvēlni (funkcija, nosaukums, url, Material ikona)
    {"grupa": "Komandas", "lapas": [
        ("lapa_parskats", "Līgas pārskats", "standings", "leaderboard"),
        ("lapa_salidzinat", "Salīdzināt komandas", "compare", "compare_arrows"),
        ("lapa_komanda", "Komandas statistika", "team", "groups"),
    ]},
    {"grupa": "Statistika", "lapas": [
        ("lapa_periodi", "Periodi", "periods", "view_timeline"),
        ("lapa_forma", "Forma un vārti", "form", "trending_up"),
        ("lapa_over_under", "Vairāk / Mazāk", "over-under", "swap_vert"),
        ("lapa_powerplay", "Vairākums", "powerplay", "bolt"),
        ("lapa_mazakums", "Mazākums", "penalty-kill", "shield"),
        ("lapa_otso", "OT / SO", "ot-so", "timer"),
        ("lapa_noraidijumi", "Noraidījumi", "penalties", "gavel"),
    ]},
    {"grupa": "Spēlētāji un tiesneši", "lapas": [
        ("lapa_speletaji", "Spēlētāji", "players", "person"),
        ("lapa_tiesnesi", "Tiesneši", "referees", "sports"),
    ]},
    # beigās atsevišķas sadaļas: Kalendārs (priekšpēdējais), Rezultāti (pēdējais)
    {"lapa": ("lapa_kalendars", "Kalendārs", "schedule", "calendar_month")},
    {"lapa": ("lapa_rezultati", "Rezultāti", "results", "sports_score")},
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
ZIMOLA_LAPA = None
for _ier in NAV:
    if "zimols" in _ier:                                  # lapa zem zīmola (nav sākumlapa)
        ZIMOLA_LAPA = _lapa(_ier["zimols"], False)
        continue
    _recs = _ier["lapas"] if "grupa" in _ier else [_ier["lapa"]]
    _lapas = []
    for _rec in _recs:
        _lapas.append((_rec, _lapa(_rec, _pirma)))
        _pirma = False
    STRUKTURA.append(("grupa", _ier["grupa"], _lapas) if "grupa" in _ier else ("lapa", _recs[0][1], _lapas))
VISAS_LAPAS = [p for _, _, saraksts in STRUKTURA for _, p in saraksts] + ([ZIMOLA_LAPA] if ZIMOLA_LAPA else [])   # [0] = sākumlapa



# Navigācija tiek reģistrēta PIRMS paroles pārbaudes: tad adrese (piem., /rezultati?spele=...) tiek saglabāta arī tad, ja vispirms jāievada parole
if NAV_REZIMS == "pielagots":
    lapas = st.navigation(VISAS_LAPAS, position="hidden")
else:
    lapas = st.navigation({**({"NHL stats": [ZIMOLA_LAPA]} if ZIMOLA_LAPA else {}), **{n: [p for _, p in s] for t, n, s in STRUKTURA}}, position="top")

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
  border-radius: 16px; padding: .35rem .7rem; padding-right: 4.2rem !important; margin-bottom: 1.1rem; box-shadow: 0 10px 28px rgba(0,0,0,.35); }   /* labajā pusē vieta motīva slēdzim */
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
  background: linear-gradient(135deg, #18233d 0%, #0a0f1c 100%) !important; border: 1px solid rgba(255,255,255,.12) !important; border-radius: 999px !important;
  color: #ffffff; box-shadow: 0 4px 12px rgba(10,15,28,.22); transition: border-color .15s ease; cursor: pointer; }
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

/* ===== Filtru rinda: pogu grupas blakus pa kreisi (bez lielām starpām), pārnesas nākamajā rindā, ja neietilpst ===== */
[class*="st-key-frinda_"] { display: flex !important; flex-direction: row !important; flex-wrap: wrap; align-items: flex-end; gap: .55rem 1.8rem !important; }
[class*="st-key-frinda_"] > div { width: auto !important; flex: 0 0 auto; min-width: 0; }

/* ===== Tabulas: kārtošanas izvēlne (⇅ Kārtot), pielīpošais virsraksts un pirmā kolonna ===== */
[class*="st-key-tbs_"] { display: flex !important; flex-direction: row !important; justify-content: flex-end; margin-bottom: -.35rem; }
[class*="st-key-tbs_"] > div { width: auto !important; flex: 0 0 auto; }
[class*="st-key-tbs_"] button { background: linear-gradient(135deg, #18233d 0%, #0a0f1c 100%) !important; border: 1px solid rgba(255,255,255,.12) !important;
  border-radius: 999px !important; min-height: 2rem; padding: .2rem .95rem !important; box-shadow: 0 4px 12px rgba(10,15,28,.22); }
[class*="st-key-tbs_"] button p { color: #e2e8f0 !important; font-weight: 600 !important; font-size: .84rem; white-space: nowrap;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif !important; }
/* izvēlnes bultiņa (Material ikona) paslēpta: ar citu fontu tā parādās kā teksts "expand_more" */
[class*="st-key-tbs_"] button [data-testid="stIconMaterial"], [class*="st-key-tbs_"] button span[translate="no"], [class*="st-key-tbs_"] button svg,
[class*="st-key-tbs_"] button > span:not(:has(p)), [class*="st-key-tbs_"] button > div > span:not(:has(p)) { display: none !important; }
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
.kt-logo { width: 3.4rem !important; height: 3.4rem !important; max-width: none !important; object-fit: contain; display: block; margin: 0 auto;
  pointer-events: none; -webkit-user-drag: none; }          /* palielinātais logo nedrīkst nosegt blakus esošo komandu pogas */
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

/* rezultātu kartīte: iznākuma poga (Pamatlaiks / OT / SO) atver detaļas; tad statistikas rindas pazūd */
.mc-box { position: relative; }
.mc-tg { position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }
.mc-btn { cursor: pointer; position: relative; z-index: 5; user-select: none; transition: background .15s ease, color .15s ease, border-color .15s ease; }
.mc-btn:hover { border-color: #3b82f6 !important; color: #1d4ed8; }
.mc-tg:checked ~ .mc .mc-btn { background: linear-gradient(135deg, #18233d 0%, #0a0f1c 100%); color: #ffffff; border-color: transparent !important; }
.mc-det { display: none; margin-top: .4rem; }
.mc-tg:checked ~ .mc-det { display: block; }
.mc-tg:checked ~ .mc-lines { display: none; }
.mc-det p { margin: .45rem 0; }
.mc-det .mc-dh { font-weight: 700; margin: .9rem 0 .3rem; }
@media (hover: hover) {
  .mc-btn::after { content: attr(data-tip); position: absolute; left: 50%; bottom: calc(100% + 6px); top: auto; transform: translateX(-50%); padding: .25rem .6rem;
    border-radius: .45rem; background: #262730; color: #fff; font-size: .75rem; font-weight: 600; letter-spacing: 0; text-transform: none; white-space: nowrap;
    opacity: 0; pointer-events: none; transition: opacity .12s ease; z-index: 30; box-shadow: 0 4px 12px rgba(0,0,0,.25); }
  .mc-btn:hover::after { opacity: 1; }
  .mc-tg:checked ~ .mc .mc-btn::after { content: "Aizvērt detaļas"; }
}
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
/* (GP. N) atsevišķā rindā zem nosaukuma; logo ir saite uz komandas lapu */
.cmp-gp { font-size: .82rem; font-weight: 700; line-height: 1.2; margin-top: -.25rem; }
.cmp-logo-a { display: block; line-height: 0; border-radius: 50%; transition: transform .15s ease; }
.cmp-logo-a:hover { transform: scale(1.05); }
/* taimeris kopš iepriekšējās spēles (back-to-back): lēni un minimāli pulsē */
.cel-taim { margin-top: .45rem; font-size: .78rem; font-weight: 600; color: #b91c1c; }          /* tāda pati krāsa kā "Kritiski" */
.cel-pared { margin-top: .45rem; font-size: .78rem; font-weight: 700; color: #b91c1c; }
.cel-taim .tk { display: inline-block; font-variant-numeric: tabular-nums; font-size: .95rem; margin-left: .2rem; }
/* rezultātu kartīte: sākuma laiks un vieta zem iznākuma pogas */
.mc-info { text-align: center; font-size: .82rem; opacity: .75; margin: .15rem 0 .1rem; }
/* komandas lapa: galvenie rādītāji, forma, informācija, aizvadītās spēles */
.kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .7rem; margin: .4rem 0 .8rem; align-items: start; }
.kpi, .kn { border: 1px solid rgba(128,128,128,.22); border-radius: 14px; padding: .75rem .9rem; background: rgba(255,255,255,.6); }
.kpi-l { font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; opacity: .6; }
.kpi-v { font-size: 1.65rem; font-weight: 800; line-height: 1.2; margin-top: .15rem; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif; }
.kpi-s { font-size: .8rem; opacity: .72; }
.kpi-r { display: inline-block; margin-top: .35rem; font-size: .72rem; font-weight: 700; padding: .1rem .45rem; border-radius: .35rem; background: rgba(128,128,128,.12); }
.kpi-r.ok { background: rgba(22,163,74,.14); color: #15803d; }
.kpi-r.slikti { background: rgba(220,38,38,.12); color: #b91c1c; }
.kpi-row { display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; }
.fm { display: flex; gap: .35rem; margin-top: .45rem; flex-wrap: wrap; }
.fm-b { display: inline-flex; flex-direction: column; align-items: center; min-width: 2.6rem; padding: .25rem .4rem; border-radius: .5rem; font-weight: 800;
  font-size: .85rem; text-decoration: none !important; line-height: 1.15; }
.kn-r { display: flex; align-items: center; gap: .6rem; margin-top: .4rem; }
.kn-r img { width: 2.4rem; height: 2.4rem; object-fit: contain; }
.ki { border: 1px solid rgba(128,128,128,.22); border-radius: 14px; background: rgba(255,255,255,.6); padding: .3rem .9rem; max-width: 640px; }
.ki-r { display: flex; justify-content: space-between; gap: 1rem; padding: .5rem 0; border-bottom: 1px solid rgba(128,128,128,.15); font-size: .92rem; }
.ki-r:last-child { border-bottom: 0; }
.ki-r span { opacity: .65; }
.ks { max-width: 760px; }
.ks-r { display: flex; align-items: center; gap: .7rem; padding: .5rem 0; border-bottom: 1px solid rgba(128,128,128,.18); font-size: .92rem; }
.ks-d { min-width: 3.4rem; font-size: .82rem; opacity: .7; line-height: 1.15; }
.ks-o { flex: 1; min-width: 0; display: inline-flex; align-items: center; gap: .35rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ks-o img { width: 1.6rem; height: 1.6rem; object-fit: contain; flex: none; }
.ks-v { display: inline-block; width: 1.5rem; text-align: center; flex: none; opacity: .8; }
.ks-s { font-weight: 800; color: inherit !important; text-decoration: underline; text-underline-offset: 3px; white-space: nowrap; min-width: 4.4rem; text-align: right; }
.ks-m { font-size: .78rem; opacity: .6; white-space: nowrap; min-width: 5.6rem; text-align: right; }
.ks-c { font-size: .78rem; opacity: .6; margin: .5rem 0 .2rem; }
@media (max-width: 640px) {
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; }
  .kpi, .kn { padding: .6rem .7rem; }
  .kpi-v { font-size: 1.35rem; }
  .kpi-row { grid-template-columns: 1fr; }
  .ks-r { gap: .45rem; font-size: .82rem; }
  .ks-m { display: none; }
}
/* datums ar laiku: datorā 02.10(05:00), telefonā laiks centrēts zem datuma */
.dt { display: inline-flex; align-items: baseline; white-space: nowrap; }
@media (max-width: 640px) { .dt { flex-direction: column; align-items: center; line-height: 1.1; } .dt-t { font-size: .9em; } }
/* U / Z / ZPL paskaidrojumi */
.l5u, .fm-b { position: relative; cursor: help; }
@media (hover: hover) {
  .l5u[data-tip]:hover::after, .fm-b[data-tip]:hover::after, .kn-r a.kn-a[data-tip]:hover::after {
    content: attr(data-tip); position: absolute; left: 50%; bottom: calc(100% + 6px); transform: translateX(-50%); padding: .25rem .6rem;
    border-radius: .45rem; background: #262730; color: #fff; font-size: .74rem; font-weight: 600; white-space: nowrap; z-index: 30;
    box-shadow: 0 4px 12px rgba(0,0,0,.25); pointer-events: none; text-transform: none; letter-spacing: 0; }
}
.l5u:focus::after { content: attr(data-tip); position: absolute; left: 50%; bottom: calc(100% + 6px); transform: translateX(-50%); padding: .25rem .6rem;
  border-radius: .45rem; background: #262730; color: #fff; font-size: .72rem; font-weight: 600; white-space: nowrap; z-index: 30; }
.kn-a { color: inherit !important; text-decoration: none; }
.kn-r a.kn-a { position: relative; line-height: 0; }
.kn-r b a.kn-a { text-decoration: underline; text-underline-offset: 3px; line-height: inherit; }
.ks-o.kn-a { text-decoration: none; }
.ks-o.kn-a:hover { text-decoration: underline; }
.tb a.tb-logo-a { display: inline-block; line-height: 0; border-radius: 50%; transition: transform .15s ease; }
.tb a.tb-logo-a:hover { transform: scale(1.12); }
/* komandas līderi: spēlētāja foto kartītes augšējā labajā stūrī (datorā lielāks) */
.kpi.ld-k { position: relative; }
.ld-top { position: relative; min-height: 5.9rem; padding-right: 6.2rem; }           /* vieta foto: nākamās rindas sākas zem tā */
.ld-foto { position: absolute; top: 0; right: 0; width: 5.6rem; height: 5.6rem; border-radius: 50%; background-color: #e8eef6;
  background-size: 150% auto; background-position: 50% 12%; background-repeat: no-repeat; box-shadow: 0 2px 8px rgba(0,0,0,.12); }
@media (max-width: 640px) {
  .ld-top { min-height: 0; padding-right: 0; }
  .ld-foto { width: 2.5rem; height: 2.5rem; top: -.1rem; right: -.1rem; }
  .ld-top .kpi-l { padding-right: 2.6rem; }
}
/* komandas līderi */
.ld-foto.ld-logo { display: flex; align-items: center; justify-content: center; background-image: none; background-color: #ffffff; }
.ld-logo-img { width: 72%; height: 72%; object-fit: contain; }
.ld-h { font-weight: 800; font-size: 1.05rem; margin: 1rem 0 .4rem; }
.ld-x { margin-top: .35rem; }
.ld-x summary { list-style: none; cursor: pointer; font-size: .76rem; font-weight: 700; color: #1d4ed8; padding-top: .3rem; user-select: none; }
.ld-x summary::-webkit-details-marker { display: none; }
.ld-x .ld-z { display: none; }
.ld-x[open] .ld-a { display: none; }
.ld-x[open] .ld-z { display: inline; }
.ld-v { font-weight: 700; font-size: .9rem; margin-top: .1rem; }
.ld-v span { font-weight: 400; opacity: .6; font-size: .78rem; }
.ld-c { display: flex; justify-content: space-between; gap: .5rem; font-size: .8rem; opacity: .75; margin-top: .3rem; padding-top: .3rem;
  border-top: 1px solid rgba(128,128,128,.15); }
.ld-c span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* forma kā bumbiņas */
.fb { display: inline-flex; gap: 5px; align-items: center; }
.fb i { position: relative; display: inline-block; width: 14px; height: 14px; border-radius: 50%; cursor: help; outline: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.10); }
/* Flashscore formas krāsas: uzvara #00a83f, zaudējums #dc0000, papildlaiks/metieni #f3a000 (30 % oranžs, 70 % iznākuma krāsa) */
.fb i.u { background: #00a83f; }
.fb i.z { background: #dc0000; }
.fb i.uo { background: linear-gradient(90deg, #f3a000 0 30%, #00a83f 30% 100%); }
.fb i.zo { background: linear-gradient(90deg, #f3a000 0 30%, #dc0000 30% 100%); }
.fb i:hover::after, .fb i:focus::after { content: attr(data-tip); position: absolute; right: 50%; bottom: calc(100% + 7px); transform: translateX(50%);
  padding: .3rem .6rem; border-radius: .45rem; background: #262730; color: #fff; font-size: .75rem; font-weight: 600; font-style: normal;
  white-space: nowrap; z-index: 40; box-shadow: 0 4px 12px rgba(0,0,0,.25); pointer-events: none; }
.fb i:last-child:hover::after, .fb i:last-child:focus::after { right: 0; transform: none; }
/* aizvadīto spēļu rezultāts un zīme fiksētās kolonnās; nākamo spēļu vieta */
.ks-z { width: 2.9rem; display: inline-flex; justify-content: center; flex: none; }
.ks-vieta { font-size: .8rem; opacity: .65; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 45%; }
/* padziļinātā statistika: tēmu kartītes */
.dz-leg { font-size: .8rem; opacity: .75; margin: .4rem 0 .6rem; }
.dz-g { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; }
.dz-k { border: 1px solid rgba(128,128,128,.22); border-radius: 14px; background: rgba(255,255,255,.6); padding: .6rem .9rem .4rem; }
.dz-h { font-weight: 800; font-size: .82rem; letter-spacing: .06em; text-transform: uppercase; opacity: .7; margin-bottom: .3rem; }
.dz-r { display: grid; grid-template-columns: minmax(0, 1fr) 4.2rem 5.6rem 3rem; align-items: center; gap: .4rem; padding: .38rem 0;
  border-top: 1px solid rgba(128,128,128,.13); font-size: .9rem; }
.dz-l { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dz-v { text-align: right; font-size: 1rem; }
.dz-a { text-align: right; font-size: .78rem; opacity: .6; }
.dz-p { text-align: right; }
.dz-p .kpi-r { margin-top: 0; }
@media (max-width: 900px) { .dz-g { grid-template-columns: 1fr; } }
@media (max-width: 640px) {
  .dz-r { grid-template-columns: minmax(0, 1fr) 3.4rem 4.4rem 2.4rem; font-size: .82rem; gap: .3rem; }
  .ks-s { min-width: 3.6rem; }
  .ks-z { width: 2.4rem; }
  .ks-r { flex-wrap: wrap; row-gap: .1rem; }
  .ks-vieta { flex-basis: 100%; max-width: none; text-align: left; padding-left: 4.1rem; font-size: .74rem; }
}
/* rezultātu kvadrāti (W / L) visur vienādi: krāsas kā formas bumbiņām; OT/SO = kreisie 30 % oranži */
.l5u.rw, .l5u.rwo, .l5u.rl, .l5u.rlo, .fm-b.rw, .fm-b.rwo, .fm-b.rl, .fm-b.rlo {
  display: inline-flex; align-items: center; justify-content: center; width: 1.6rem; height: 1.6rem; min-width: 1.6rem; padding: 0 !important;
  border-radius: .3rem; color: #ffffff !important; font-weight: 800; font-size: .8rem; line-height: 1; text-decoration: none !important;
  text-shadow: 0 1px 1px rgba(0,0,0,.25); box-shadow: inset 0 0 0 1px rgba(0,0,0,.08); }
.l5u.rw, .fm-b.rw { background: #00a83f; }
.l5u.rl, .fm-b.rl { background: #dc0000; }
.l5u.rwo, .fm-b.rwo { background: linear-gradient(90deg, #f3a000 0 30%, #00a83f 30% 100%); }
.l5u.rlo, .fm-b.rlo { background: linear-gradient(90deg, #f3a000 0 30%, #dc0000 30% 100%); }
/* topu vērtības ar paskaidrojumu (uzvedot / pieskaroties) */
.ld-tip { position: relative; cursor: help; text-decoration: underline dotted rgba(128,128,128,.7); text-underline-offset: 3px; outline: none; }
.ld-tip:hover::after, .ld-tip:focus::after { content: attr(data-tip); position: absolute; right: 0; bottom: calc(100% + 6px); padding: .28rem .6rem;
  border-radius: .45rem; background: #262730; color: #fff; font-size: .74rem; font-weight: 600; white-space: nowrap; z-index: 40;
  box-shadow: 0 4px 12px rgba(0,0,0,.25); pointer-events: none; }
/* logo kājenē */
.st-key-kaj_logo { display: flex !important; justify-content: center; align-items: center; margin-top: 3.2rem; margin-bottom: -1.7rem; }   /* kopējā atstarpe no teksta līdz versijai saglabāta, logo tuvāk versijai */
.st-key-kaj_logo [data-testid="stMarkdownContainer"] { text-align: center; margin-bottom: 0 !important; }
.st-key-kaj_logo [data-testid="stIconMaterial"], .st-key-kaj_logo span[translate="no"] { font-size: 2.8rem !important; opacity: .55; line-height: 1; }
/* interesanti fakti: comeback saraksts */
.fk-liga { font-size: .85rem; opacity: .8; margin: .2rem 0 .5rem; }
.fk-izl { color: #b45309; background: rgba(245,158,11,.14); }
.fk-izc { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .6rem; }
.fk-iz { display: flex; gap: .6rem; align-items: center; border: 1px solid rgba(128,128,128,.22); border-left: 4px solid #00a83f; border-radius: 12px;
  padding: .55rem .8rem; background: rgba(255,255,255,.6); font-size: .86rem; }
.fk-iz.zem { border-left-color: #dc0000; }
.fk-iz img { width: 2rem; height: 2rem; object-fit: contain; flex: none; }
.fk-iz span { display: block; opacity: .8; }
@media (max-width: 640px) { .fk-izc { grid-template-columns: 1fr; } }
.fk-r { display: flex; align-items: center; gap: .7rem; padding: .5rem 0; border-bottom: 1px solid rgba(128,128,128,.18); font-size: .92rem; max-width: 760px; }
.fk-r .ks-o img { width: 1.6rem; height: 1.6rem; object-fit: contain; }
.fk-def { min-width: 2.6rem; text-align: center; font-weight: 800; color: #b91c1c; background: rgba(220,38,38,.10); border-radius: .35rem; padding: .1rem .35rem; cursor: help; }
@media (max-width: 640px) { .fk-r { gap: .4rem; font-size: .8rem; } }
.fm-dir { display: flex; justify-content: space-between; max-width: calc(5 * 1.6rem + 4 * .35rem); font-size: .68rem; opacity: .6; margin-top: .3rem; }
/* fakti: sausās sērijas */
.fk-foto { position: static !important; width: 1.9rem; height: 1.9rem; border-radius: 50%; flex: none; background-color: #e8eef6;
  background-size: 150% auto; background-position: 50% 12%; background-repeat: no-repeat; }
.fk-pie { font-size: .78rem; opacity: .7; white-space: nowrap; }
.fk-ser { min-width: 5.4rem; text-align: center; font-weight: 800; border-radius: .35rem; padding: .12rem .4rem; background: rgba(128,128,128,.14); }
.fk-ser.akt { background: rgba(0,168,63,.14); color: #15803d; }
@media (max-width: 640px) { .fk-pie { display: none; } .fk-ser { min-width: 4.4rem; } }
/* savstarpējās spēles (H2H) salīdzinājumā */
.st-key-pgr_h2hv, .st-key-pgr_h2hsez { justify-content: center; margin: -.1rem 0 .4rem; }
.h2h-sez { font-size: .76rem; font-weight: 800; letter-spacing: .05em; opacity: .6; margin: .7rem 0 .1rem; padding-bottom: .2rem;
  border-bottom: 1px solid rgba(128,128,128,.25); }
.h2h-nak { font-size: .85rem; opacity: .8; }
.st-key-sl_per button:disabled { opacity: .45; cursor: not-allowed; }
.h2h-nav { text-align: center; font-size: .8rem; opacity: .65; margin: -.2rem 0 .4rem; }
.h2h-sum { text-align: center; margin: .2rem auto .9rem; max-width: 760px; }
.h2h-ser { font-size: .95rem; }
.h2h-piez { font-size: .76rem; opacity: .65; margin-top: .25rem; }
.h2h-l { margin-top: 1.2rem; }
.h2h-l .ks { max-width: none; }
.h2h-k img { width: 1.5rem; height: 1.5rem; object-fit: contain; }
/* regulārā sezona / play-off */
.st-key-pgr_sez_dala { justify-content: center; margin: -.4rem 0 .6rem; }
.sez-piez { text-align: center; font-size: .78rem; opacity: .65; margin: -.4rem 0 .5rem; }
/* prognožu kartītes */
.pk { border: 1px solid rgba(128,128,128,.22); border-radius: 14px; background: rgba(255,255,255,.6); padding: .8rem 1rem; margin: 0 0 .9rem; }
.pk-g { display: flex; justify-content: space-between; align-items: center; gap: .6rem; flex-wrap: wrap; }
.pk-kom { display: flex; align-items: center; gap: .4rem; font-size: .98rem; }
.pk-kom img { width: 1.7rem; height: 1.7rem; object-fit: contain; }
.pk-at { opacity: .6; margin: 0 .2rem; }
.pk-laiks { font-size: .82rem; opacity: .85; }
.pk-s { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr; gap: .6rem .9rem; margin-top: .7rem; }
.pk-s > div { display: flex; flex-direction: column; gap: .2rem; }
.pk-l { font-size: .7rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; opacity: .6; }
.pk-v { display: flex; gap: .3rem .8rem; flex-wrap: wrap; align-items: flex-end; font-size: .95rem; }
.pk-x { display: inline-flex; flex-direction: column; white-space: nowrap; line-height: 1.15; }
.pk-x b { font-size: 1.05rem; }
.pk-u { font-size: .68rem; opacity: .6; font-weight: 700; }
.pk-k { font-size: .74rem; opacity: .6; }
.pk-t .pk-x { flex-direction: row; gap: .3rem; align-items: baseline; }
.pk-t .pk-x b { font-size: .86rem; }
.pk-f { font-size: .78rem; opacity: .8; margin-top: .55rem; }
.pk-d { margin-top: .5rem; }
.pk-d summary { list-style: none; cursor: pointer; font-size: .8rem; font-weight: 700; color: #1d4ed8; }
.pk-d summary::-webkit-details-marker { display: none; }
.pk-d .ld-z { display: none; }
.pk-d[open] .ld-a { display: none; }
.pk-d[open] .ld-z { display: inline; }
.pk-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .9rem; margin-top: .5rem; }
.pk-h { font-size: .72rem; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; opacity: .65; margin-bottom: .3rem; }
.pk-t { width: 100%; border-collapse: collapse; font-size: .84rem; margin-bottom: .4rem; }
.pk-t th { text-align: left; font-size: .72rem; opacity: .6; font-weight: 700; padding: .15rem .3rem; }
.pk-t td { padding: .22rem .3rem; border-top: 1px solid rgba(128,128,128,.15); white-space: nowrap; }
.pk-piez { font-size: .8rem; opacity: .85; margin: .2rem 0 .4rem; }
.pk-top { display: inline-flex; gap: .25rem; align-items: baseline; padding: .1rem .45rem; border-radius: .4rem; background: rgba(128,128,128,.12); font-weight: 700; margin-right: .25rem; }
.pk-top small { font-weight: 500; opacity: .7; }
@media (max-width: 900px) { .pk-s { grid-template-columns: repeat(2, minmax(0, 1fr)); } .pk-1x2 { grid-column: 1 / -1; } .pk-grid { grid-template-columns: 1fr; } }
html.tumss .pk { background: var(--t-karte); border-color: var(--t-mala); }
html.tumss .pk-d summary { color: var(--t-zils); }
/* koeficienti */
.kf { max-width: 760px; margin: .2rem auto .8rem; text-align: center; }
.kf-g { font-size: .72rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; opacity: .6; margin-bottom: .3rem; }
.kf-r { display: flex; justify-content: center; gap: .6rem; flex-wrap: wrap; }
.kf-s { display: inline-flex; align-items: baseline; gap: .35rem; padding: .35rem .8rem; border-radius: 999px;
  border: 1px solid rgba(128,128,128,.25); background: rgba(255,255,255,.55); }
.kf-n { font-size: .78rem; font-weight: 700; opacity: .7; }
.kf-s b { font-size: 1.05rem; }
.kf-p { font-size: .74rem; opacity: .6; }
.kf-b { font-size: .7rem; } .kf-b.aug { color: #16a34a; } .kf-b.kr { color: #dc2626; }
.kf-nav { font-size: .8rem; opacity: .6; }
.kf-d { margin-top: .4rem; text-align: left; }
.kf-d summary { list-style: none; cursor: pointer; font-size: .8rem; font-weight: 700; color: #1d4ed8; text-align: center; }
.kf-d summary::-webkit-details-marker { display: none; }
.kf-d .ld-z { display: none; } .kf-d[open] .ld-a { display: none; } .kf-d[open] .ld-z { display: inline; }
.pk-m { font-size: .8rem; margin-top: .55rem; padding: .35rem .6rem; border-radius: .5rem; background: rgba(128,128,128,.08); }
.pk-pl { color: #15803d; font-weight: 700; } .pk-mn { color: #b91c1c; font-weight: 700; }
@media (max-width: 640px) { .kf-r { gap: .35rem; flex-wrap: nowrap; } .kf-s { padding: .3rem .5rem; gap: .25rem; } .kf-s b { font-size: .95rem; } .kf-p { display: none; } }
html.tumss .kf-s { background: var(--t-karte); border-color: var(--t-mala); }
html.tumss .kf-d summary { color: var(--t-zils); }
html.tumss .kf-b.aug, html.tumss .pk-pl { color: #4ade80; } html.tumss .kf-b.kr, html.tumss .pk-mn { color: #f87171; }
/* kājene: paskaidrojums par lapu */
.kaj { max-width: 900px; margin: 3rem auto 0; padding-top: 1rem; border-top: 1px solid rgba(128,128,128,.25); font-size: .8rem; line-height: 1.55; opacity: .75; }
.kaj p { margin: 0 0 .7rem; }
.kaj-pied { font-style: italic; opacity: .85; }
/* ceļojuma faktors salīdzinājumā */
.cel { margin: 1.7rem 0 .2rem; }
.cel-h { text-align: center; font-weight: 800; font-size: .88rem; letter-spacing: .07em; opacity: .9; margin-bottom: .2rem; }
.cel-sub { text-align: center; font-size: .82rem; opacity: .65; margin-bottom: .6rem; }
.cel-row { display: flex; gap: .8rem; }
.cel-c, .cel-one { flex: 1 1 0; min-width: 0; border: 1px solid rgba(128,128,128,.25); border-radius: 12px; padding: .6rem .85rem; background: rgba(255,255,255,.5); }
.cel-c.l { border-top: 3px solid #dc2626; }
.cel-c.r { border-top: 3px solid #111827; text-align: right; }
.cel-one { text-align: center; }
.cel-k { font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; opacity: .6; }
.cel-km { font-size: 1.35rem; font-weight: 800; line-height: 1.25; }
.cel-t { font-size: .85rem; opacity: .8; }
.cel-piez { font-size: .75rem; opacity: .55; margin-top: .25rem; }
.cel-b { display: inline-block; margin-top: .45rem; font-size: .75rem; font-weight: 700; padding: .15rem .5rem; border-radius: .4rem; }
.cel-c.krit { border-color: rgba(220,38,38,.6); box-shadow: inset 0 0 0 1px rgba(220,38,38,.25); background: rgba(254,226,226,.45); }
.cel-b.krit { background: rgba(220,38,38,.12); color: #b91c1c; }
.cel-b.brid { background: rgba(245,158,11,.16); color: #b45309; }
@media (max-width: 640px) { .cel-row { gap: .45rem; } .cel-c { padding: .5rem .55rem; } .cel-km { font-size: 1.1rem; } .cel-t { font-size: .76rem; } .cel-b { font-size: .68rem; } }
/* pēdējās 5 spēles abām komandām */
.cmp-l5 { display: flex; justify-content: space-between; gap: 1.2rem; margin: 1.8rem 0 .5rem; }
.l5c { flex: 1 1 0; min-width: 0; max-width: 26rem; }
.l5h { font-weight: 800; font-size: .9rem; margin-bottom: .35rem; }
.l5c.r .l5h { text-align: right; }
.l5r { display: grid; grid-template-columns: 5.4rem 1.5rem 1.8rem 4rem 2.8rem; align-items: center; justify-items: center; column-gap: .4rem;
  padding: .38rem 0; border-bottom: 1px solid rgba(128,128,128,.2); font-size: .9rem; justify-content: start; }
.l5c.r .l5r { direction: rtl; justify-content: start; }
.l5c.r .l5r > * { direction: ltr; }
.l5r .l5d { justify-self: start; }
.l5c.r .l5r .l5d { justify-self: end; }
.l5v { font-weight: 600; opacity: .75; }
.l5d { opacity: .65; font-size: .8rem; white-space: nowrap; }
.l5lg { width: 1.7rem !important; height: 1.7rem !important; max-width: none !important; object-fit: contain; }
.l5s { font-weight: 800; color: inherit !important; text-decoration: underline; text-underline-offset: 3px; }
.l5u { font-size: .68rem; font-weight: 800; padding: .08rem .38rem; border-radius: .3rem; }
@media (max-width: 640px) {
  .st-key-cmp_head { gap: .3rem !important; }
  .st-key-cmp_ch, .st-key-cmp_ca { width: 9.3rem !important; }
  .st-key-cmp_cm { width: 2.8rem !important; }
  .st-key-cmp_vh, .st-key-cmp_va { gap: .25rem !important; flex-wrap: nowrap; }
  .st-key-cmp_vh button, .st-key-cmp_va button { padding: .1rem .45rem !important; min-height: 1.8rem; }
  .st-key-cmp_vh button p, .st-key-cmp_va button p { font-size: .7rem; }
  .cmp-l5 { gap: .6rem; }
  .l5r { font-size: .76rem; grid-template-columns: 2.4rem 1rem 1.4rem 2.7rem 2.3rem; column-gap: .22rem; }
  .l5d { font-size: .68rem; }
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
.st-key-sl_per { display: flex !important; flex-direction: row !important; flex-wrap: wrap; justify-content: center; gap: .5rem !important; margin-bottom: .4rem; }
.st-key-sl_per > div { width: auto !important; flex: 0 0 auto; }
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

# Lapas fons: ledus ar NHL logo, caurspīdīgs, lai netraucētu lasīt tekstu (tumšā motīva caurspīdīgums – sadaļā TUMŠAIS MOTĪVS).
# Pielāgošana: FONA_CAURSPIDIBA_GAISS (0 = nav redzams, 1 = pilna redzamība).
FONA_CAURSPIDIBA_GAISS = 0.30
if FONS_DATA_URI:
    st.markdown(f"""<style>
.stApp {{ isolation: isolate; }}
.stApp::before {{ content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background: url("{FONS_DATA_URI}") center / cover no-repeat; opacity: {FONA_CAURSPIDIBA_GAISS}; }}
.stApp [data-testid="stAppViewContainer"], .stApp [data-testid="stMain"], .stApp section.stMain {{ background: transparent !important; }}
</style>""", unsafe_allow_html=True)

st.markdown(r"""<style>
/* ============================================================================
   TUMŠAIS MOTĪVS: automātiski pēc ierīces laika 23:01–07:59 (08:00–23:00 gaišais); slēdzis saule/mēness augšējās joslas
   labajā stūrī to maina līdz nākamajai automātiskajai maiņai
   Krāsas: tumši zili pelēks fons (nevis melns), gaišs teksts, kartītes nedaudz gaišākas par fonu.
   ============================================================================ */
html.tumss { --t-fons: #1a2433; --t-karte: rgba(37,49,68,.92); --t-karte2: #22304a; --t-mala: rgba(255,255,255,.12);
  --t-teksts: #e6ebf2; --t-blavs: #aab6c8; --t-zils: #93c5fd; --t-zals: #4ade80; --t-sarkans: #f87171; --t-oranzs: #fbbf24; --t-viesi: #cbd5e1; }
html.tumss, html.tumss body, html.tumss .stApp { background-color: var(--t-fons) !important; color: var(--t-teksts); color-scheme: dark; }
html.tumss .stApp::before { opacity: .07 !important; }
html.tumss .stApp :is(h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label,
  [data-testid="stCaptionContainer"], [data-testid="stText"], [data-testid="stMetricLabel"], [data-testid="stMetricValue"], .stMarkdown) { color: var(--t-teksts); }
html.tumss .stApp [data-testid="stCaptionContainer"], html.tumss .stApp .kpi-s, html.tumss .stApp .kpi-l { color: var(--t-blavs); }
html.tumss .stApp a { color: var(--t-zils); }
/* kartītes un bloki */
html.tumss :is(.kpi, .kn, .ki, .dz-k, .fk-iz, .cel-c, .cel-one, .cf-c) { background: var(--t-karte) !important; border-color: var(--t-mala) !important; }
html.tumss :is(.ki-r, .ks-r, .fk-r, .l5r, .dz-r, .ld-c, .kaj) { border-color: rgba(255,255,255,.10) !important; }
html.tumss .kpi-r { background: rgba(255,255,255,.10); color: var(--t-teksts); }
html.tumss .kpi-r.ok { background: rgba(74,222,128,.16); color: var(--t-zals); }
html.tumss .kpi-r.slikti { background: rgba(248,113,113,.16); color: var(--t-sarkans); }
html.tumss :is(.cel-taim, .cel-pared, .fk-def, .cel-b.krit) { color: var(--t-sarkans) !important; }
html.tumss .cel-b.krit, html.tumss .fk-def { background: rgba(248,113,113,.14) !important; }
html.tumss .cel-b.brid, html.tumss .fk-izl { color: var(--t-oranzs) !important; background: rgba(251,191,36,.14) !important; }
html.tumss .fk-ser.akt { color: var(--t-zals); background: rgba(74,222,128,.15); }
html.tumss .ld-x summary { color: var(--t-zils); }
html.tumss :is(.fm-b, .l5u) { box-shadow: inset 0 0 0 1px rgba(255,255,255,.12); }
/* viesu komandas krāsa (bija gandrīz melna) */
html.tumss :is(.cf-c i.b, .cmp-krasa.b, .cmp-bar i.b) { background: var(--t-viesi) !important; }
html.tumss .cel-c.r { border-top-color: var(--t-viesi) !important; }
/* tabulas */
html.tumss .tb, html.tumss .tb :is(th, td) { color: var(--t-teksts); border-color: rgba(255,255,255,.09) !important; }
html.tumss .tb thead th, html.tumss .tb :is(td.c0, th.c0, td.c1, th.c1) { background: #1f2b3e !important; }
html.tumss .tb tbody tr:hover, html.tumss .tb tbody tr:hover td { background: rgba(147,197,253,.08) !important; }
html.tumss .tb .bubble a, html.tumss .mc-det a { color: var(--t-zils) !important; }
/* paskaidrojumi */
html.tumss :is(.ld-tip, .fb i, .l5u, .fm-b, .kn-r a.kn-a)[data-tip]:hover::after,
html.tumss :is(.ld-tip, .fb i):focus::after { background: #0e1626 !important; border: 1px solid rgba(255,255,255,.14); }
html.tumss :is(.tip .bubble, .tb .bubble) { background: #0e1626 !important; color: var(--t-teksts) !important; border-color: rgba(255,255,255,.14) !important; }
/* rezultātu kartītes */
html.tumss .mc-btn { color: var(--t-zils); border-color: rgba(147,197,253,.45) !important; }
html.tumss :is(.mc-lines, .mc-info, .mc-det) { color: var(--t-teksts); }
/* Streamlit logrīki */
html.tumss [data-baseweb="select"] > div, html.tumss [data-baseweb="input"], html.tumss [data-baseweb="base-input"],
html.tumss [data-baseweb="textarea"], html.tumss .stDateInput [data-baseweb="input"] { background-color: var(--t-karte2) !important; border-color: var(--t-mala) !important; }
html.tumss [data-baseweb="select"] *, html.tumss [data-baseweb="input"] input, html.tumss [data-baseweb="base-input"] input { color: var(--t-teksts) !important; }
html.tumss [data-baseweb="popover"] :is(ul, [role="listbox"], [data-baseweb="menu"], [data-baseweb="calendar"]),
html.tumss [data-testid="stPopoverBody"] { background-color: var(--t-karte2) !important; color: var(--t-teksts) !important; }
html.tumss [data-baseweb="popover"] [role="option"] { color: var(--t-teksts) !important; }
html.tumss [data-baseweb="popover"] [role="option"]:hover, html.tumss [data-baseweb="popover"] [aria-selected="true"] { background-color: #2e3f5c !important; }
html.tumss [data-baseweb="calendar"] * { color: var(--t-teksts); }
html.tumss [data-testid="stExpander"] details { background: rgba(37,49,68,.55); border-color: var(--t-mala) !important; }
html.tumss [data-testid="stExpander"] summary, html.tumss [data-testid="stExpander"] summary * { color: var(--t-teksts) !important; }
html.tumss [data-baseweb="tab-list"] { border-color: rgba(255,255,255,.12) !important; }
html.tumss [data-baseweb="tab"] p { color: var(--t-blavs) !important; }
html.tumss [data-baseweb="tab"][aria-selected="true"] p { color: var(--t-zils) !important; }
html.tumss [data-testid="stAlertContainer"] { background-color: rgba(147,197,253,.12) !important; color: var(--t-teksts) !important; }
html.tumss [data-testid="stAlertContainer"] * { color: var(--t-teksts) !important; }
html.tumss :is([data-testid="stVerticalBlockBorderWrapper"], [data-testid="stVerticalBlock"][style*="border"], [data-testid="stMetric"]) { border-color: var(--t-mala) !important; }
html.tumss [data-testid="stMetric"] { background: rgba(37,49,68,.55); }
html.tumss :is([data-testid="stTickBar"] *, [data-testid="stThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"]) { color: var(--t-blavs) !important; }
html.tumss :is(.stDownloadButton, .stButton) button:not([kind="primary"]) { background: #22304a; color: var(--t-teksts); border-color: var(--t-mala); }
html.tumss .kaj { color: var(--t-blavs); }
/* izvēlnes (selectbox): lauks, izvēlētā vērtība un nolaižamais saraksts tumšajā motīvā */
html.tumss [data-baseweb="select"] > div { background-color: var(--t-karte2) !important; border-color: var(--t-mala) !important; }
html.tumss [data-baseweb="select"] :is(div, span, input) { color: var(--t-teksts) !important; -webkit-text-fill-color: var(--t-teksts) !important; opacity: 1 !important; }
html.tumss [data-baseweb="select"] svg { color: var(--t-zils) !important; }
html.tumss [data-baseweb="popover"] > div, html.tumss [data-baseweb="popover"] :is([data-baseweb="menu"], [role="listbox"], ul),
html.tumss [data-testid="stSelectboxVirtualDropdown"] { background-color: var(--t-karte2) !important; }
html.tumss [data-baseweb="popover"] :is(li, [role="option"]) { background-color: transparent !important; color: var(--t-teksts) !important; }
html.tumss [data-baseweb="popover"] :is(li, [role="option"]) * { color: var(--t-teksts) !important; -webkit-text-fill-color: var(--t-teksts) !important; }
html.tumss [data-baseweb="popover"] :is(li, [role="option"]):hover, html.tumss [data-baseweb="popover"] :is(li, [role="option"])[aria-selected="true"] { background-color: #2e3f5c !important; }
/* izvēršamie bloki (Comebacks, SHUTOUT): virsraksta josla tumša, teksts labi salasāms */
html.tumss [data-testid="stExpander"] details > summary { background-color: rgba(37,49,68,.95) !important; }
html.tumss [data-testid="stExpander"] details > summary:hover { background-color: #2e3f5c !important; }
html.tumss [data-testid="stExpander"] summary :is(p, span, div) { color: var(--t-teksts) !important; -webkit-text-fill-color: var(--t-teksts) !important; opacity: 1 !important; }
html.tumss [data-testid="stExpander"] summary svg { color: var(--t-zils) !important; }
html.tumss :is([class*="st-key-rmb_"], .st-key-rez_fokuss_kartite) { border: 1px solid rgba(255,255,255,.16) !important; }   /* rezultātu, kalendāra, prognožu rāmji */
html.tumss .stTabs *:has(> [data-baseweb="tab-list"]) > :not([data-baseweb="tab-list"]) {     /* cilņu ritināšanas bultiņas: tumši zilas, nevis baltas */
  background: #22304a !important; background-image: none !important; color: var(--t-zils) !important; border-color: var(--t-mala) !important; }
html.tumss .stTabs *:has(> [data-baseweb="tab-list"]) > :not([data-baseweb="tab-list"]) :is(button, span) { background: transparent !important; color: var(--t-zils) !important; }
html.tumss .stTabs *:has(> [data-baseweb="tab-list"]) > :not([data-baseweb="tab-list"]) svg { color: var(--t-zils) !important; }
html.tumss :is(.ld-foto, .fk-foto) { background-color: #2c3c57 !important; }   /* spēlētāju foto un komandu logo aplis tumšajā motīvā */
html.tumss :is(.tb-logo, .ks-o img, .l5lg, .cmp-logo, .cf-c img, .kn-r img, .fk-iz img, .mc img, .ld-logo-img) { filter: drop-shadow(0 0 1px rgba(255,255,255,.55)) drop-shadow(0 0 3px rgba(255,255,255,.18)); }   /* tumšas krāsas logo (melni elementi) ir saskatāmi uz tumšā fona */
/* slēdzis saule / mēness (ievieto skripts augšējā joslā) */
.tema-sw { position: absolute; top: 50%; right: .7rem; transform: translateY(-50%); width: 3.1rem; height: 1.65rem; border-radius: 999px; border: 1px solid rgba(255,255,255,.18);
  background: #1e293b; cursor: pointer; padding: 0; z-index: 20; }
.tema-sw svg { position: absolute; top: 50%; width: .95rem; height: .95rem; transform: translateY(-50%); pointer-events: none; }
.tema-sw .s { left: .4rem; color: #fbbf24; } .tema-sw .m { right: .4rem; color: #c7d2fe; }
.tema-sw::after { content: ""; position: absolute; top: 2px; left: 2px; width: calc(1.65rem - 6px); height: calc(1.65rem - 6px); border-radius: 50%;
  background: #f8fafc; box-shadow: 0 1px 3px rgba(0,0,0,.4); transition: transform .2s ease; }
html.tumss .tema-sw::after { transform: translateX(1.45rem); background: #e0e7ff; }
.tema-sw:focus-visible { outline: 2px solid #60a5fa; outline-offset: 2px; }
@media (max-width: 640px) { .tema-sw { top: .55rem; transform: none; right: .55rem; } }
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
def ielasit_koef(versija):
    return da.ielasit_koeficientus()


BUKMEIKERU_NOS = {"pinnacle": "Pinnacle", "betfair_ex_eu": "Betfair", "betsson": "Betsson", "nordicbet": "NordicBet", "unibet_eu": "Unibet",
                  "unibet_se": "Unibet", "unibet_nl": "Unibet", "unibet_fr": "Unibet", "williamhill": "William Hill", "sport888": "888sport",
                  "coolbet": "Coolbet", "onexbet": "1xBet", "matchbook": "Matchbook", "marathonbet": "Marathonbet", "leovegas_se": "LeoVegas",
                  "winamax_fr": "Winamax", "winamax_de": "Winamax", "tipico_de": "Tipico", "pmu_fr": "PMU", "everygame": "Everygame",
                  "gtbets": "GTbets", "betonlineag": "BetOnline", "betanysports": "BetAnything"}


def speles_koeficienti(a_kom, b_kom):
    """Tuvākās vēl nesāktās spēles koeficienti starp abām komandām (jebkurā mājas/viesu secībā): DataFrame vai None."""
    k, _ = ielasit_koef(VERSIJA)
    if k is None:
        return None
    x = k[(((k["majas"] == a_kom) & (k["viesi"] == b_kom)) | ((k["majas"] == b_kom) & (k["viesi"] == a_kom)))
          & (k["sakums_lv"] > pd.Timestamp.now(tz=da.LV_TZ))]
    if x.empty:
        return None
    gid = x.sort_values("sakums_lv")["game_id"].iloc[0]
    return x[x["game_id"] == gid]


def _pinnacle_vai_vid(x, tirgus, izn, linija=None):
    """Pinnacle koeficients (vai vidējais, ja Pinnacle nav) un iepriekšējā vērtība: (koef, iepr, avots)."""
    y = x[(x["tirgus"] == tirgus) & (x["iznakums"] == izn)]
    if linija is not None:
        y = y[(y["linija"] - linija).abs() < 1e-9]
    if y.empty:
        return None, None, None
    p = y[y["bukmeikers"] == "pinnacle"]
    if not p.empty:
        r = p.iloc[0]
        return float(r["koef"]), (float(r["koef_iepr"]) if pd.notna(r["koef_iepr"]) and str(r["koef_iepr"]) != "" else None), "Pinnacle"
    return float(y["koef"].mean()), None, f"vidējais ({y['bukmeikers'].nunique()})"


def _labakais(x, tirgus, izn, linija=None):
    y = x[(x["tirgus"] == tirgus) & (x["iznakums"] == izn)]
    if linija is not None:
        y = y[(y["linija"] - linija).abs() < 1e-9]
    if y.empty:
        return None, None
    r = y.loc[y["koef"].idxmax()]
    return float(r["koef"]), BUKMEIKERU_NOS.get(r["bukmeikers"], str(r["bukmeikers"]))


def _bulta(k, iepr):
    if iepr is None or k is None or abs(k - iepr) < 1e-9:
        return ""
    return (f'<span class="kf-b {"aug" if k > iepr else "kr"}" title="Iepriekšējā ielādē: {iepr:.2f}">{"▲" if k > iepr else "▼"}</span>')


def koef_bloks_html(x, meta):
    """Salīdzinājumā: 1 · X · 2 (pamatlaiks) ar izmaiņu bultiņām un varbūtībām; izvēršot – vairāk līniju un labākie koeficienti."""
    e = _html.escape
    h, v = x["majas"].iloc[0], x["viesi"].iloc[0]
    k1, i1, avots = _pinnacle_vai_vid(x, "1x2", "1")
    kx, ix, _ = _pinnacle_vai_vid(x, "1x2", "X")
    k2, i2, _ = _pinnacle_vai_vid(x, "1x2", "2")
    laiks = ""
    if meta and meta.get("ielade"):
        laiks = f'{pd.Timestamp(meta["ielade"]).tz_convert(da.LV_TZ):%d.%m. %H:%M}'
    galva = f'<div class="kf-g">Koeficienti · {e(avots or "–")} · pamatlaiks{f" · atjaunoti {laiks}" if laiks else ""}</div>'
    if k1 and kx and k2:
        tv = modelis.tirgus_varbutibas({"1": k1, "X": kx, "2": k2}) or {}
        sk = lambda nos, k, i, izn: (f'<div class="kf-s"><span class="kf-n">{e(nos)}</span><b>{k:.2f}</b>{_bulta(k, i)}'   # noqa: E731
                                     f'<span class="kf-p">{tv.get(izn, 0) * 100:.0f}%</span></div>')
        rinda = f'<div class="kf-r">{sk(h, k1, i1, "1")}{sk("X", kx, ix, "X")}{sk(v, k2, i2, "2")}</div>'
    else:
        rinda = '<div class="kf-r kf-nav">Pamatlaika 1X2 koeficientu vēl nav</div>'
    # vairāk līniju
    rind = []

    def r_(nos, tirgus, izn, lin=None):
        kp, ip, av = _pinnacle_vai_vid(x, tirgus, izn, lin)
        kb, bn = _labakais(x, tirgus, izn, lin)
        if kp is None:
            return
        avz = "" if av == "Pinnacle" else ' <small title="Pinnacle šai līnijai nav – vidējais no bukmeikeriem">vid.</small>'
        rind.append(f'<tr><td>{e(nos)}</td><td><b>{kp:.2f}</b>{_bulta(kp, ip)}{avz}</td>'
                    f'<td>{f"{kb:.2f} <small>{e(bn)}</small>" if kb else "–"}</td></tr>')
    for izn, nos in (("1", f"{h} pamatlaikā"), ("X", "Neizšķirts"), ("2", f"{v} pamatlaikā")):
        r_(nos, "1x2", izn)
    for izn, nos in (("1", f"{h} ar OT"), ("2", f"{v} ar OT")):
        r_(nos, "ml", izn)
    for lin_h in sorted(x[(x["tirgus"] == "pm") & (x["iznakums"] == "1")]["linija"].dropna().unique()):
        r_(f"{h} {lin_h:+.1f}", "pm", "1", lin_h)
        r_(f"{v} {-lin_h:+.1f}", "pm", "2", -lin_h)
    for lin in sorted(x[x["tirgus"] == "tot"]["linija"].dropna().unique()):
        r_(f"Over {lin:g}", "tot", "over", lin)
        r_(f"Under {lin:g}", "tot", "under", lin)
    sikak = ""
    if rind:
        sikak = (f'<details class="kf-d"><summary><span class="ld-a">Vairāk līniju ▾</span><span class="ld-z">Paslēpt ▴</span></summary>'
                 f'<table class="pk-t"><tr><th></th><th>Pinnacle</th><th>Labākais</th></tr>{"".join(rind)}</table>'
                 f'<div class="pk-piez">±1.5 un totāli parasti ietver papildlaiku. Taisnīgās varbūtības – bez bukmeikera uzcenojuma.</div></details>')
    return f'<div class="kf">{galva}{rinda}{sikak}</div>'


@st.cache_data(show_spinner=False)
def ielasit_db_visu(versija):
    """DB: iepriekšējās sezonas (sezonas/vesture) – spēles un komandu rindas. Lapās netiek rādīts; izmanto modelis un H2H."""
    return da.ielasit_db()


@st.cache_data(show_spinner=False)
def _ielasit_papildu_visu(nos, versija):
    return da.ielasit_tabulu(nos)


def ielasit_papildu(nos, versija):
    """Spēlētāji / vārtsargi / vārti / tiesneši: tikai spēles, kas ietilpst pašreizējā atlasē (šī sezona un RS vai PO)."""
    t = _ielasit_papildu_visu(nos, versija)
    if t is None or t.empty or SPELU_ID is None or "game_id" not in t.columns:
        return t
    return t[t["game_id"].isin(SPELU_ID)]


@st.cache_data(show_spinner=False)
def ielasit_tiesnesus(versija):
    cur = da.ielasit_tabulu("tiesnesi")
    prev, info = da.ielasit_pagajuso_tiesnesus()
    return cur, prev, info


TIESSAISTES_LIMITS_S = 8          # tiešsaistes tiesnešu pārbaude nekad nebloķē lapu ilgāk


def ielasit_planotos(versija):
    return _planotie_ar_statusu(versija)[0]


@st.cache_data(show_spinner=False, ttl=600)
def _planotie_ar_statusu(versija):
    """
    Paziņotie tiesneši: fails sezonas/tiesnesi_planotie.csv (to papildina GitHub Actions) + spēlēm, kurām tur tiesnešu vēl nav, tiešā ielāde no Scouting The Refs.
    GitHub plānotie darbi bieži kavējas vai tiek izlaisti, tāpēc lietotne tiesnešus meklē arī pati (rezultāts tiek turēts 10 minūtes, lai neslogotu portālu).
    """
    plan = da.ielasit_planotos_tiesnesus()
    kal = ielasit_visu(versija)[2]
    n_fails = int(plan.loc[plan["loma"] == "referee", "game_id"].nunique()) if plan is not None and not plan.empty else 0
    tagad = datetime.datetime.now(datetime.timezone.utc)
    lv = lambda t: t.astimezone(da.LV_TZ)                                                        # noqa: E731
    # pārbaudītais logs: spēles, kas sākušās pēdējo 4 h laikā (vēl notiek), un nākamās 30 h
    statuss = {"fails": n_fails, "tiessaiste": 0, "kluda": None, "laiks": lv(tagad).strftime("%H:%M"),
               "no": lv(tagad - timedelta(hours=4)), "lidz": lv(tagad + timedelta(hours=30)), "nakama": lv(tagad + timedelta(minutes=10)).strftime("%H:%M")}
    if kal is None or kal.empty:
        return plan, statuss
    kludas = []
    try:
        import tiesnesi_planotie as tp
        if not hasattr(tp, "dzivie_tiesnesi") or not hasattr(tp, "_lejupieladet"):
            statuss["kluda"] = "repozitorijā ir vecs tiesnesi_planotie.py (augšupielādē jauno), tiešsaistes pārbaude nedarbojas"
            return plan, statuss

        def lej(url, meginajumi=2):
            """Lejupielāde statusam: 404 (dienas ieraksts vēl nav publicēts) nav kļūda; kļūda ir tikai, ja vietne neatbild vai atsaka."""
            import requests
            for _ in range(meginajumi):
                try:
                    r = requests.get(url, headers={"User-Agent": getattr(tp, "STR_UA", "Mozilla/5.0"), "Accept-Language": "en"}, timeout=(3, 5))
                    if r.status_code == 200:
                        return r.text
                    if r.status_code == 404:
                        return None
                except requests.RequestException:
                    pass
            kludas.append(url)
            return None
        esosie = set(plan.loc[plan["loma"] == "referee", "game_id"].astype(int)) if plan is not None and not plan.empty else set()
        # dzivie_tiesnesi pārbauda [tagad − 1 h, tagad + stundas]; pārbīdot "tagad" 3 h atpakaļ, logs ir [−4 h, +30 h].
        # Darbojas atsevišķā pavedienā ar laika limitu: ja vietne atbild lēni, lapa neiestrēgst (izmanto failā esošos tiesnešus).
        import threading
        rez_ = {}

        def darbs():
            try:
                rez_["j"] = tp.dzivie_tiesnesi(kal, esosie, stundas=33, tagad=tagad - timedelta(hours=3), lejupieladet=lej)
            except Exception as ex_:
                rez_["ex"] = ex_
        pav = threading.Thread(target=darbs, daemon=True)
        pav.start()
        pav.join(TIESSAISTES_LIMITS_S)
        if pav.is_alive():
            statuss["kluda"] = "Scouting The Refs neatbildēja laikā, rādīti tiesneši no datu faila"
            return plan, statuss
        if "ex" in rez_:
            raise rez_["ex"]
        jaunas = rez_.get("j") or []
    except Exception as ex:               # bez interneta vai ja portāls nav pieejams: paliek tikai tas, kas ir failā
        statuss["kluda"] = f"{type(ex).__name__}: {str(ex)[:80]}"
        return plan, statuss
    if kludas:
        statuss["kluda"] = f"Scouting The Refs nav sasniedzams ({len(kludas)} pieprasījumi neizdevās)"
    if not jaunas:
        return plan, statuss
    jauns = pd.DataFrame(jaunas)
    statuss["tiessaiste"] = int(jauns.loc[jauns["loma"] == "referee", "game_id"].nunique())
    return (jauns if plan is None or plan.empty else pd.concat([plan, jauns], ignore_index=True)), statuss


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
SPELU_ID = None            # spēļu atlase (sezona + RS/PO); tiek iestatīta pirms lapas palaišanas (sk. "SEZONA UN RS / PO")
SEZ_DALA = da.TIPS_RS
if RAW is None or DF.empty:
    st.error("Nav atrasts datu fails 'sezonas/speles.csv' (vai vecais 'nhl_sezona.csv'). "
             "Palaid nhl_dati.py un ieliec CSV failus repozitorijā.")
    st.stop()

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
    "Z": "loss (pamatlaikā)",
    "OTL": "OT loss vai SO loss (komanda saņem 1 punktu)",
    "L": "loss (pamatlaikā)",
    "Punkti": "Tabulas punkti: win 2, OT loss / SO loss 1, loss 0",
    "Punkti %": "Iegūto punktu daļa no iespējamajiem: punkti / (2 × spēles)",
    "Vārti/sp": "Vidēji gūtie vārti spēlē pamatlaikā (bez papildlaika un pēcspēles metieniem)",
    "Ielaisti/sp": "Vidēji ielaistie vārti spēlē pamatlaikā",
    "Starpība": "Gūto un ielaisto vārtu starpība pamatlaikā",
    "Metieni/sp": "Vidēji metieni vārtos (SOG) spēlē pamatlaikā (bez papildlaika)",
    "Metienu daļa %": "Komandas metienu daļa pamatlaikā: SOG par / (SOG par + SOG pret), bez papildlaika",
    "PP %": "Vairākuma (Power Play) efektivitāte pamatlaikā: vārti vairākumā / vairākuma iespējas, bez papildlaika",
    "PK %": "Mazākuma (Penalty Kill) efektivitāte pamatlaikā: neielaisto vārtu daļa, kad komanda spēlē mazākumā, bez papildlaika",
    "Noraid./sp": "Vidēji noraidījumu skaits spēlē (tikai minor sodi pamatlaikā; dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem)",
    "Forma (5)": "Pēdējās 5 spēles (vecākā → jaunākā): zaļa = win, sarkana = loss, ar oranžu daļu = OT win / SO win vai OT loss / SO loss. Uzved uz bumbiņas, lai redzētu rezultātu un pretinieku",
    "Forma": "Pēdējās spēles (vecākā → jaunākā): zaļa = win, sarkana = loss, ar oranžu daļu = OT win / SO win vai OT loss / SO loss. Uzved uz bumbiņas, lai redzētu rezultātu un pretinieku",
    "Gūti vārti": "Pēdējās izvēlētajās spēlēs gūtie vārti pamatlaikā (kopā)",
    "Ielaisti vārti": "Pēdējās izvēlētajās spēlēs ielaistie vārti pamatlaikā (kopā)",
    # periodi
    "Gūti": "Šajā periodā gūtie vārti (kopā)",
    "Ielaisti": "Šajā periodā ielaistie vārti (kopā)",
    # over / under, vairākums, noraidījumi
    "Over %": "Spēļu daļa (%), kurās abu komandu vārtu summa pamatlaikā pārsniedza izvēlēto līniju",
    "Under %": "Spēļu daļa (%), kurās abu komandu vārtu summa pamatlaikā bija zemāka par izvēlēto līniju",
    "Vid. vārti spēlē": "Vidējā abu komandu vārtu summa spēlē pamatlaikā",
    "PP vārti": "Vairākumā pamatlaikā gūtie vārti (bez papildlaika)",
    "PP iespējas": "Vairākuma iespējas pamatlaikā (reizes, kad komanda spēlēja vairākumā), bez papildlaika",
    "PP metieni": "Metieni vārtos vairākumā pamatlaikā (bez papildlaika)",
    "Ielaisti PP": "Pretinieka vairākumā pamatlaikā gūtie vārti pret šo komandu",
    "Izcīnīti − saņemti": "Izcīnīto un saņemto noraidījumu starpība spēlē; pozitīvs skaitlis = komanda izcīna vairāk, nekā saņem",
    # komandas lapa
    "Metieni": "Metieni vārtos visā spēlē (arī papildlaikā, tikai informācijai): komanda–pretinieks",
    "Noraidījumi": "Komandas noraidījumu skaits spēlē (tikai minor sodi pamatlaikā; dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem)",
    "PIM min": "Minor sodu minūtes spēlē (pamatlaikā; bez major, 10 min disciplinārajiem un kautiņiem)",
    "Mājās": "Vārtu starpība šajā periodā mājas spēlēs",
    "Viesos": "Vārtu starpība šajā periodā viesu spēlēs",
    "Pēdējās 10": "Vārtu starpība šajā periodā pēdējās 10 spēlēs",
    # ceļojums un atpūta
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
    "Kombinētais": "Kombinētais rādītājs: 60% pagājušā + 40% šī sezona (svarus var mainīt iestatījumos); katra daļa tiek pievilkta pie līgas vidējā, ja spēļu ir maz",
    "Pret līgu": "Kombinētā rādītāja starpība pret kombinēto līgas vidējo; pozitīvs = tiesnesis soda vairāk par vidējo",
    "Mājas komanda": "Kombinētie noraidījumi mājas komandai spēlē",
    "Viesu komanda": "Kombinētie noraidījumi viesu komandai spēlē",
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
    "Iznākums": "W = win, L = loss, O = OT loss / SO loss",
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
    "W": "win (arī OT win un SO win)",
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


def rtabula_html(df, column_config=None, paskaidr=None):
    """Tabula kā HTML virkne (bez kārtošanas), ievietošanai citā HTML (piem., spēles detaļās)."""
    return df_html(df, config=cfg_ar_help(list(df.columns), column_config, paskaidr), kartot=False, atgriezt=True)


def rtabula_bez_kartosanas(df, column_config=None, paskaidr=None, **kw):
    """Tabula bez kārtošanas izvēlnes (spēļu protokoli Rezultātos)."""
    kw["kartot"] = False
    rtabula(df, column_config=column_config, paskaidr=paskaidr, **kw)


def rtabula(df, column_config=None, paskaidr=None, **kw):
    """Tabula (caurspīdīga HTML) ar paskaidrojumiem kolonnu virsrakstos. Citi Streamlit st.dataframe parametri (width, height) netiek lietoti."""
    df_html(df, config=cfg_ar_help(list(df.columns), column_config, paskaidr),
            indekss=(kw.get("hide_index") is False and not isinstance(df.index, pd.RangeIndex)), kartot=kw.get("kartot", True))


def tabula(res, kolonnas, sort_col, ascending=False, config=None, grafiks=False, paskaidr=None, burbuli=None, formati=None, prog=None, numurs_no=1):
    """Komandu rangu tabula ar logotipiem. res: DataFrame ar indeksu 'komanda'; kolonnas: {iekšējais: virsraksts}.
    burbuli: {komanda: HTML} spēļu saraksts burbulī uz kolonnas "Sp."; formati/prog: {iekšējais: formāts / (min, max)}. (Grafiki lietotnē vairs netiek rādīti.)"""
    if res is None or res.empty:
        st.info("Nav datu šim skatam.")
        return
    t = res.sort_values(sort_col, ascending=ascending, kind="stable").reset_index()
    bur = [burbuli.get(k) for k in t["komanda"]] if burbuli else None
    saites = [iekseja_saite("team", kom=k) for k in t["komanda"]]           # logo atver komandas statistiku
    t.insert(0, "Logo", t["komanda"].map(da.logo_url))
    t.insert(1, "Komanda", t["komanda"].map(da.pilns_nosaukums))
    t.insert(0, "#", range(numurs_no, numurs_no + len(t)))
    t = t[["#", "Logo", "Komanda"] + list(kolonnas)].rename(columns=kolonnas)
    cfg = {"Logo": st.column_config.ImageColumn("", width="small"), "#": st.column_config.NumberColumn("#", width="small")}
    cfg.update(config or {})
    fm = {kolonnas[k]: v for k, v in (formati or {}).items() if k in kolonnas}
    pg = {kolonnas[k]: v for k, v in (prog or {}).items() if k in kolonnas}
    df_html(t, config=cfg_ar_help(list(t.columns), cfg, paskaidr), formati=fm, prog=pg, burbuli=bur, bur_kol=kolonnas.get("GP"), logo_saites=saites,
            numurs_no=numurs_no)


# ============================================================================
# LAPA: PROGNOZES
# ============================================================================
@st.cache_data(show_spinner=False)
def modela_dati(versija):
    """Modeļa spēļu tabula (DB + šī sezona), parametri un reitingi uz šodienu (kešots pēc datu versijas)."""
    raw_db, df_db = ielasit_db_visu(versija)
    raw_t, df_t, _ = ielasit_visu(versija)
    dalas = [x for x in (raw_db, raw_t) if x is not None and not x.empty]
    if not dalas:
        return None, None, None, None
    g = modelis.spelu_tabula(pd.concat(dalas, ignore_index=True))
    p, meta = modelis.ielasit_parametrus()
    sez = int(raw_t["sezona"].max()) if raw_t is not None and not raw_t.empty else int(g["sezona"].max())
    mod = modelis.aprekinat_reitingus(g, uz_datumu=pd.Timestamp.now(tz=da.LV_TZ).tz_localize(None).normalize(), sezona_tagad=sez, p=p)
    rindas = pd.concat([x for x in (df_db, df_t) if x is not None and not x.empty], ignore_index=True).sort_values(["datums", "game_id"])
    return g, mod, (p, meta), rindas


def _speles_faktori(home, away, sakums):
    """Atpūta un ceļš katrai komandai pirms šīs spēles (aizvadītās + kalendārā ieplānotās spēles)."""
    out = {}
    for puse, kods in (("h", home), ("a", away)):
        pirms = komandas_speles_pirms(kods, pd.Timestamp(sakums))
        b2b = cels = 0
        if pirms:
            iepr = pirms[-1]
            dienas = (_et_datums(sakums) - _et_datums(iepr[0])).days
            b2b = int(dienas == 1)
            if dienas <= 2 and lokacijas is not None and lokacijas.attalums_km(iepr[1], home) >= modelis.GARS_CELS_KM:
                cels = 1
        out[f"b2b_{puse}"], out[f"cels_{puse}"] = b2b, cels
    return out


def _pk(x, uzr=""):
    """Procenti un taisnīgais koeficients vienā nedalāmā vienībā (uzr – īss apzīmējums virs, piem., 1 / X / 2)."""
    u = f'<small class="pk-u">{_html.escape(uzr)}</small>' if uzr else ""
    return f'<span class="pk-x">{u}<b>{x * 100:.0f}%</b><span class="pk-k">{modelis.koeficients(x):.2f}</span></span>'


def prognozes_karte_html(home, away, sakums, tiesn_txt, pr, nor, mod):
    e = _html.escape
    f = pr["faktori"]
    cipi = []
    if f["b2b_h"]: cipi.append(f"{home}: otrā spēle pēc kārtas")
    if f["b2b_a"]: cipi.append(f"{away}: otrā spēle pēc kārtas")
    if f["cels_h"]: cipi.append(f"{home}: garš ceļš")
    if f["cels_a"]: cipi.append(f"{away}: garš ceļš")
    if f["po"]: cipi.append("play-off")
    kh, ka, n_h2h = f["h2h"]
    if n_h2h and (abs(kh - 1) > 0.005 or abs(ka - 1) > 0.005):
        cipi.append(f"H2H ({n_h2h} sp.): {home} {kh - 1:+.0%}, {away} {ka - 1:+.0%}")
    if nor and abs(nor["tiesnesu_koef"] - 1) > 0.005:
        cipi.append(f"tiesneši: noraidījumi {nor['tiesnesu_koef'] - 1:+.0%}")
    tic_kl = {"Augsta": "ok", "Vidēja": "", "Zema": "slikti"}[pr["ticamiba"]]
    x = pr["1x2"]; o = pr["ar_ot"]; t55 = pr["totali"][5.5]
    galva = (f'<div class="pk-g"><div class="pk-kom"><img src="{e(da.logo_url(away))}" alt=""><b>{e(da.pilns_nosaukums(away))}</b>'
             f'<span class="pk-at">@</span><img src="{e(da.logo_url(home))}" alt=""><b>{e(da.pilns_nosaukums(home))}</b></div>'
             f'<div class="pk-laiks">{pd.Timestamp(sakums):%d.%m(%H:%M)} · <span class="kpi-r {tic_kl}" title="Mazākais šīs sezonas spēļu skaits abām komandām: {pr["n_min"]}">'
             f'ticamība: {e(pr["ticamiba"])}</span></div></div>')
    kops = (f'<div class="pk-s"><div class="pk-1x2"><span class="pk-l">Pamatlaikā</span><span class="pk-v">{_pk(x["1"], home)} {_pk(x["X"], "X")} {_pk(x["2"], away)}</span></div>'
            f'<div><span class="pk-l">Uzvarētājs ar OT</span><span class="pk-v">{_pk(o["1"], home)} {_pk(o["2"], away)}</span></div>'
            f'<div><span class="pk-l">Gaidāmie vārti</span><span class="pk-v"><span class="pk-x"><small class="pk-u">{e(home)} : {e(away)}</small>'
            f'<b>{pr["lh"]:.2f} : {pr["la"]:.2f}</b><span class="pk-k">kopā {pr["lh"] + pr["la"]:.2f}</span></span></span></div>'
            f'<div><span class="pk-l">Totāls 5.5</span><span class="pk-v">{_pk(t55["over"], "Over")} {_pk(t55["under"], "Under")}</span></div></div>')
    rinda = lambda nos, *v: f'<tr><td>{e(nos)}</td>' + "".join(f"<td>{_pk(z)}</td>" for z in v) + "</tr>"   # noqa: E731
    tot = "".join(rinda(f"Totāls {lin}", pr["totali"][lin]["over"], pr["totali"][lin]["under"]) for lin in (4.5, 5.5, 6.5))
    pm = pr["plus_minus"]
    pml = (rinda(f"{home} −1.5 / {away} +1.5", pm["1 −1.5"], pm["2 +1.5"]) + rinda(f"{away} −1.5 / {home} +1.5", pm["2 −1.5"], pm["1 +1.5"]))
    top = " ".join(f'<span class="pk-top">{s_}<small>{pv * 100:.0f}%</small></span>' for pv, s_ in pr["top"])
    per = "".join(f'<tr><td>{nr}. periods <small>({v["gaidami"]:.2f})</small></td>'
                  + "".join(f'<td>{_pk(v[lin]["over"])}</td>' for lin in (0.5, 1.5, 2.5)) + "</tr>" for nr, v in pr["periodi"].items())
    nor_html = ""
    if nor:
        nor_html = (f'<div class="pk-sek"><div class="pk-h">Noraidījumi (minor, pamatlaiks)</div>'
                    f'<div class="pk-piez">Gaidāmie: <b>{nor["kopa"]:.1f}</b> ({home} {nor["majas"]:.1f} · {away} {nor["viesi"]:.1f})'
                    f'{" · " + e(tiesn_txt) if tiesn_txt else ""}</div>'
                    f'<table class="pk-t"><tr><th></th><th>Over</th><th>Under</th></tr>'
                    + "".join(rinda(f"Noraidījumi {lin}", v["over"], v["under"]) for lin, v in nor["totali"].items())
                    + "</table></div>")
    sikak = (f'<details class="pk-d"><summary><span class="ld-a">Visi tirgi ▾</span><span class="ld-z">Paslēpt ▴</span></summary>'
             f'<div class="pk-grid"><div class="pk-sek"><div class="pk-h">Vārti (pamatlaiks)</div>'
             f'<table class="pk-t"><tr><th></th><th>Over</th><th>Under</th></tr>{tot}</table>'
             f'<table class="pk-t"><tr><th>±1.5</th><th></th><th></th></tr>{pml}</table>'
             f'<div class="pk-piez">Ticamākie rezultāti: {top}</div></div>'
             f'<div class="pk-sek"><div class="pk-h">Periodi: over (gaidāmie vārti)</div>'
             f'<table class="pk-t"><tr><th></th><th>0.5</th><th>1.5</th><th>2.5</th></tr>{per}</table></div>{nor_html}</div></details>')
    fakt = f'<div class="pk-f">{" · ".join(e(c) for c in cipi)}</div>' if cipi else ""
    return f'<div class="pk">{galva}{kops}{tirgus_html(home, away, pr)}{fakt}{sikak}</div>'


def tirgus_html(home, away, pr):
    """Modelis pret tirgu: Pinnacle (bez uzcenojuma) 1X2 pamatlaikā un galvenais totāls (ar OT), starpība procentpunktos."""
    x = speles_koeficienti(home, away)
    if x is None:
        return ""
    e = _html.escape
    if x["majas"].iloc[0] != home:                        # kalendārā mājinieki ir pirmā komanda; drošībai pārbaude
        return ""
    k = {izn: _pinnacle_vai_vid(x, "1x2", izn)[0] for izn in ("1", "X", "2")}
    dalas = []
    tv = modelis.tirgus_varbutibas(k) if all(k.values()) else None
    if tv:
        def st_(izn, nos):
            d = (pr["1x2"][izn] - tv[izn]) * 100
            kl = "pk-pl" if d >= 5 else ("pk-mn" if d <= -5 else "")
            return f'{e(nos)} {tv[izn] * 100:.0f}% <span class="{kl}">({d:+.0f})</span>'
        dalas.append("Tirgus pamatlaikā: " + " · ".join(st_(i, n) for i, n in (("1", home), ("X", "X"), ("2", away))))
    tot = x[(x["tirgus"] == "tot") & (x["bukmeikers"] == "pinnacle")]
    if tot.empty:
        tot = x[x["tirgus"] == "tot"]
    if not tot.empty:
        lin = tot["linija"].mode().iloc[0]
        ko = {i: _pinnacle_vai_vid(x, "tot", i, lin)[0] for i in ("over", "under")}
        tvo = modelis.tirgus_varbutibas(ko) if all(ko.values()) else None
        mo = modelis.pilnas_speles_over(pr, float(lin))
        if tvo and mo is not None:
            d = (mo - tvo["over"]) * 100
            kl = "pk-pl" if d >= 5 else ("pk-mn" if d <= -5 else "")
            dalas.append(f"Over {lin:g} (ar OT): tirgus {tvo['over'] * 100:.0f}%, modelis {mo * 100:.0f}% <span class=\"{kl}\">({d:+.0f})</span>")
    if not dalas:
        return ""
    return (f'<div class="pk-m" title="Tirgus varbūtības no Pinnacle koeficientiem bez uzcenojuma; iekavās – modelis mīnus tirgus, procentpunktos">'
            + "<br>".join(dalas) + "</div>")


def modelis_pret_tirgu_bloks():
    """Pārbaude uz aizvadītām spēlēm: prognozes un koeficienti, kas saglabāti PIRMS spēles (prognozes_arhivs.csv)."""
    prog = da.ielasit_prognozu_arhivu()
    if prog is None:
        st.caption("Arhīvs vēl ir tukšs. Tas sāks krāties pēc koeficientu ielādēm (3× dienā): katrā ielādē tiek saglabātas modeļa "
                   "prognozes un tā brīža koeficienti, lai vēlāk godīgi salīdzinātu ar rezultātiem.")
        return
    r = RAW_VISS if globals().get("RAW_VISS") is not None else RAW
    rez = pd.DataFrame({"game_id": r["game_id"].astype("int64"),
                        "hg": r[["home_p1", "home_p2", "home_p3"]].fillna(0).sum(axis=1), "ag": r[["away_p1", "away_p2", "away_p3"]].fillna(0).sum(axis=1),
                        "h_tot": r["home_total"], "a_tot": r["away_total"]})
    v = modelis.vertet_pret_tirgu(prog, rez)
    n = v.get("speles", 0)
    st.caption(f"Arhīvā: {prog['game_id'].nunique()} spēles ar prognozēm, no tām aizvadītas un novērtējamas: {n}.")
    if n == 0:
        return
    if n < 200:
        st.warning(f"Tikai {n} spēles – rezultāti vēl ir ļoti nejauši. Ticamus secinājumus var izdarīt pēc ~200–300 spēlēm.")
    lg = v["logloss"]
    st.markdown(
        f"**Precizitāte 1X2 pamatlaikā** (log loss, mazāk = labāk): modelis **{lg['modelis']:.4f}** · tirgus rītā (Pinnacle) "
        f"**{lg['tirgus_rits']:.4f}** · tirgus pirms spēles **{lg['tirgus_nosl']:.4f}** · modelis un tirgus uz pusēm **{lg['apvienots']:.4f}**.")
    rindas = [x for x in v["likmes"] if x.get("likmes")]
    if rindas:
        rtabula(pd.DataFrame({
            "Tirgus": [x["tirgus"] for x in rindas], "Starpība ≥": [f"{x['slieksnis'] * 100:.0f}%" for x in rindas],
            "Likmes": [x["likmes"] for x in rindas], "Uzvaras %": [x["uzvaras"] / x["likmes"] * 100 for x in rindas],
            "ROI Pinnacle %": [x["roi_pin"] * 100 for x in rindas], "ROI labākais %": [x["roi_lab"] * 100 for x in rindas],
            "CLV %": [x["clv"] * 100 for x in rindas], "Pārspēj noslēgumu %": [x["parspeja_noslegumu"] * 100 for x in rindas]}),
            hide_index=True, kartot=False,
            column_config={k: st.column_config.NumberColumn(format="%.1f") for k in ("Uzvaras %", "ROI Pinnacle %", "ROI labākais %", "CLV %", "Pārspēj noslēgumu %")},
            paskaidr={"Starpība ≥": "Simulētā likme tiek “likta”, ja modeļa varbūtība × rīta koeficients − 1 ir vismaz tik liela",
                      "ROI Pinnacle %": "Peļņa uz likmi (vienādas likmes) ar Pinnacle rīta koeficientiem",
                      "ROI labākais %": "Tas pats ar labāko rīta koeficientu starp ES bukmeikeriem",
                      "CLV %": "Cik rīta koeficients bija labāks par pēdējo zināmo pirms spēles: + nozīmē, ka tirgus pēc tam pagājās modeļa virzienā",
                      "Pārspēj noslēgumu %": "Cik % likmju rīta koeficients bija augstāks par pēdējo pirms spēles"})
    st.caption("Svarīgākais rādītājs ir CLV: ja tas ilgtermiņā ir pozitīvs, modelis atrod informāciju, ko tirgus vēl nav ievērtējis. "
               "ROI uz maziem paraugiem ir ļoti nejaušs. Tā ir simulācija, nevis ieteikums likt likmes.")


def lapa_prognozes():
    st.title("Prognozes")
    md = modela_dati(VERSIJA)
    if md[1] is None:
        st.info("Modelim vēl nav datu (ne šīs sezonas, ne DB).")
        return
    g, mod, (p, meta), rindas = md
    with st.expander("Kā modelis strādā un cik tas precīzs", expanded=False):
        st.markdown(
            "- **Komandu stiprums:** uzbrukums un aizsardzība no visām spēlēm, ņemot vērā pretinieku (svērta Puasona regresija). "
            "Šīs sezonas spēles sver vairāk, iepriekšējās sezonas (DB) – mazāk; sezonas sākumā prognoze balstās galvenokārt uz DB.\n"
            "- **Korekcijas:** mājas priekšrocība, otrā spēle pēc kārtas, garš ceļš, play-off, H2H (ja pārbaude rāda, ka tā uzlabo), "
            "tiesneši – noraidījumiem.\n"
            "- **Visi tirgi** ir no vienas pamatlaika rezultātu matricas (ar neizšķirtu korekciju; gaidāmo vārtu kopsumma piesardzīgi pievilkta "
            "pie līgas vidējā, ja pārbaude to rāda); “ar OT” – neizšķirta gadījumā pēc vēstures. "
            "Koeficients = 1 / varbūtība (taisnīgais, bez bukmeikera uzcenojuma).")
        if meta:
            mt, bz = meta.get("parbaude", {}), meta.get("baze", {})
            st.markdown(
                f"**Pārbaude pret vēsturi** ({str(meta.get('parbaudes_sezona'))[:4]}/{str(meta.get('parbaudes_sezona'))[6:]}, "
                f"{mt.get('speles', 0)} spēles, katra prognozēta tikai no datiem pirms tās): log loss 1X2 **{mt.get('logloss_1x2', float('nan')):.4f}** "
                f"(bāze no iepriekšējo sezonu biežumiem {bz.get('logloss_1x2', float('nan')):.4f}; mazāk = labāk), totāls 5.5 "
                f"**{mt.get('logloss_o55', float('nan')):.4f}** (bāze {bz.get('logloss_o55', float('nan')):.4f}); neizšķirti pamatlaikā "
                f"{mt.get('neizskirti_prog', 0):.1%} prognoze / {mt.get('neizskirti_fakt', 0):.1%} fakts; vidēji vārti "
                f"{mt.get('videji_varti_prog', 0):.2f} / {mt.get('videji_varti_fakt', 0):.2f}. "
                f"H2H korekcija: {'tiek lietota' if p.get('h2h_lietot') else 'netiek lietota (neuzlaboja prognozes)'}. Kalibrēts: {meta.get('izveidots', '')}.")
            kal = meta.get("kalibracija_1") or []
            if kal:
                rtabula(pd.DataFrame({"Mājinieku uzvara (prognoze)": [f"{k['no'] * 100:.0f}–{k['lidz'] * 100:.0f}%" for k in kal],
                                      "Spēles": [k["speles"] for k in kal], "Vidēji prognoze": [k["prognoze"] * 100 for k in kal],
                                      "Notika": [k["fakts"] * 100 for k in kal]}), hide_index=True, kartot=False,
                        column_config={"Vidēji prognoze": st.column_config.NumberColumn(format="%.0f"), "Notika": st.column_config.NumberColumn(format="%.0f")},
                        paskaidr={"Notika": "Cik % no šīm spēlēm mājinieki tiešām uzvarēja pamatlaikā – jo tuvāk prognozei, jo labāk kalibrēts modelis"})
        else:
            st.caption("Modelis vēl nav kalibrēts pret vēsturi (python modelis.py --kalibret), tiek lietoti noklusējuma iestatījumi.")
    with st.expander("Modelis pret tirgu (reālās spēles)", expanded=False):
        modelis_pret_tirgu_bloks()
    if KAL is None or KAL.empty:
        st.warning("Nav atrasts kalendārs (sezonas/nhl_kalendars.csv).")
        return
    skaits = st.slider("Cik tuvākās spēles rādīt", 3, 15, 7)
    nak = KAL[KAL["sakums_lv"] > pd.Timestamp.now(tz=da.LV_TZ)].sort_values("sakums_lv").head(skaits)
    if nak.empty:
        st.info("Kalendārā šobrīd nav nākamo spēļu.")
        return
    for _, r in nak.iterrows():
        home, away, sak = r["majas_komanda"], r["viesu_komanda"], r["sakums_lv"]
        if home not in modelis.NHL_KOMANDAS_SARAKSTS or away not in modelis.NHL_KOMANDAS_SARAKSTS:
            continue
        po = int(str(r.get("speles_tips", "RS")) == "PO")
        fk = _speles_faktori(home, away, sak)
        pr = modelis.prognoze(mod, g, home, away, p, po=po, **fk)
        vardi, ref_pr, liga_kopa = speles_tiesnesi(r["game_id"])
        tk = (ref_pr["kopa"] / liga_kopa) if (vardi and ref_pr is not None and liga_kopa and pd.notna(ref_pr["kopa"])) else 1.0
        nor = modelis.noraidijumi(rindas, home, away, p=p, tiesnesu_koef=tk)
        tiesn_txt = ("Tiesneši: " + ", ".join(vardi)) if vardi else "tiesneši vēl nav paziņoti"
        st.markdown(prognozes_karte_html(home, away, sak, tiesn_txt, pr, nor, mod), unsafe_allow_html=True)
    st.caption("Prognozes ir matemātisks novērtējums no pieejamajiem datiem (pamatlaiks), nevis garantija.")


# ============================================================================
# LAPA: LĪGAS PĀRSKATS
# ============================================================================
def lapa_parskats():
    with st.container(key="frinda_pk"):                   # filtru grupas blakus pa kreisi
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="pk_scope")
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="pk_logs")
    res = da.kopsavilkums(DF, scope, LOGI[logs])
    res["Forma"] = forma_bumbas(DF, 5)
    tabula(res, {
        "GP": "Sp.", "W": "W", "L": "L", "OTL": "OTL", "PTS": "Punkti", "PTS_pct": "Punkti %",
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
    st.caption("W = win (arī OT win un SO win), L = loss, OTL = OT loss vai SO loss. "
               "Visi statistikas rādītāji (vārti, metieni, noraidījumi, vairākums) ir pamatlaika, bez papildlaika un pēcspēles metieniem. "
               "Win, loss un punkti ir oficiālie rezultāti. Tabulu var kārtot, klikšķinot uz kolonnas virsraksta.")


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
SL_H2H = "Savstarpējās"                                # tajā pašā pogu grupā: tikai šīs sezonas savstarpējās spēles
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
    sk = tip_html(f"(GP. {gp_kopa})", f"Nospēlētās spēles kopā: {gp_kopa}" + (f" · šajā skatā: {gp_skata}" if gp_skata is not None and gp_skata != gp_kopa else ""))
    nos = _html.escape(da.pilns_nosaukums(kods))
    href = _html.escape(iekseja_saite("team", kom=kods))
    return (f'<div class="cmp-col"><a class="cmp-logo-a" href="{href}" target="_blank" rel="noopener" title="Atvērt komandas statistiku">'
            f'<img class="cmp-logo" src="{_html.escape(da.logo_url(kods))}" alt="{_html.escape(kods)}"></a>'
            f'<div class="cmp-krasa {kl}"></div><div class="cmp-nos">{nos}</div><div class="cmp-gp">{sk}</div></div>')


SAKUMI = {}           # game_id -> sākuma laiks (Rīga), aizpildās pirmajā izsaukumā
REZ_NOZIME = {"W": "win", "L": "loss", "OTW": "OT win", "SOW": "SO win", "OTL": "OT loss", "SOL": "SO loss"}
REZ_KRASA = {"W": "rw", "OTW": "rwo", "SOW": "rwo", "L": "rl", "OTL": "rlo", "SOL": "rlo"}   # CSS: zaļš, sarkans, 30 % oranžs + zaļš/sarkans
REZ_BURTS = {"W": "W", "OTW": "W", "SOW": "W", "L": "L", "OTL": "L", "SOL": "L"}          # kvadrātā tikai W vai L


def rez_kods(rez, beigas):
    """Spēles iznākums: W, L, OTW, SOW, OTL, SOL (pēc oficiālā rezultāta un tā, kā spēle beidzās)."""
    b = str(beigas).upper()
    if rez == "W":
        return {"OT": "OTW", "SO": "SOW"}.get(b, "W")
    if rez == "OTL":
        return "SOL" if b == "SO" else "OTL"
    return "L" if rez == "L" else ""


def dt_html(ts, datums=None):
    """Datums ar laiku: datorā 02.10(05:00), telefonā laiks precīzi centrēts zem datuma."""
    if ts is not None and pd.notna(ts):
        return f'<span class="dt"><span class="dt-d">{ts:%d.%m}</span><span class="dt-t">({ts:%H:%M})</span></span>'
    return f'<span class="dt"><span class="dt-d">{pd.Timestamp(datums):%d.%m}</span></span>' if datums is not None else ""


def rez_zime(u, kl="l5u"):
    """W / L / OTW / SOW / OTL / SOL zīme ar paskaidrojumu (uzvedot peli vai pieskaroties)."""
    if not u:
        return ""
    return f'<span class="{kl} {REZ_KRASA.get(u, "")}" data-tip="{REZ_NOZIME.get(u, "")}" title="{REZ_NOZIME.get(u, "")}" tabindex="0">{REZ_BURTS.get(u, "")}</span>'


def sl_h2h_speles(kreisa, laba, df=None):
    """Savstarpējās spēles (kreisās komandas rindas pret labo), jaunākā augšā. Pēc noklusējuma – šī sezona (pašreizējā RS/PO atlase)."""
    df = DF if df is None else df
    if df is None or df.empty:
        return pd.DataFrame(columns=DF.columns)
    return df[(df["komanda"] == kreisa) & (df["pretinieks"] == laba)].sort_values(["datums", "game_id"], ascending=False)


def sl_db_rindas():
    """DB (iepriekšējo sezonu) komandu rindas ar to pašu RS/PO atlasi kā pašreizējā skatā; None, ja vēstures nav."""
    _, df_db = ielasit_db_visu(VERSIJA)
    if df_db is None or df_db.empty:
        return None
    return df_db if SEZ_DALA is None else df_db[df_db["tips"] == SEZ_DALA]


def sez_nos(s):
    s = str(int(s))
    return f"{s[:4]}/{s[6:]}"


SL_H2H_APJOMI = {"sezona": "Šī sezona", "visas": "Visas sezonas"}


def sl_kopsavilkums_no(sub_df):
    """Kopsavilkums tikai no dotajām spēlēm (abām komandām), ar Over 5.5, tāpat kā sl_kopsavilkums."""
    k = da.kopsavilkums(sub_df, "Visas", None)
    if not k.empty and "Over55" not in k.columns:
        k["Over55"] = (sub_df["tot_reg_goals"] > 5.5).groupby(sub_df["komanda"]).mean() * 100
    return k


def sl_nakama_savstarpeja(kreisa, laba):
    """Nākamā savstarpējā spēle no kalendāra: (sākums, mājinieki) vai None."""
    if KAL is None or KAL.empty:
        return None
    x = KAL[(((KAL["majas_komanda"] == kreisa) & (KAL["viesu_komanda"] == laba)) | ((KAL["majas_komanda"] == laba) & (KAL["viesu_komanda"] == kreisa)))
            & (KAL["sakums_lv"] > pd.Timestamp.now(tz=da.LV_TZ))].sort_values("sakums_lv")
    return (x.iloc[0]["sakums_lv"], x.iloc[0]["majas_komanda"]) if not x.empty else None


def _nakama_txt(nak):
    if not nak:
        return ""
    pils = lokacijas.LOKACIJAS.get(nak[1], {}).get("pilseta", nak[1]) if lokacijas is not None else nak[1]
    return f"nākamā spēle {nak[0]:%d.%m(%H:%M)} · {pils}"


def _serijas_txt(kreisa, laba, x):
    w = int((x["rez"] == "W").sum())
    ot = int(x["beigas"].astype(str).str.upper().isin(["OT", "SO"]).sum())
    return (f'<b>{_html.escape(kreisa)} {w}–{len(x) - w} {_html.escape(laba)}</b>{f" ({ot} OT/SO)" if ot else ""} · '
            f'vārti {int(x["g_tot"].sum())}:{int(x["z_tot"].sum())}')


def sl_h2h_kopsavilkums_html(kreisa, laba, sezona_r, visas_r, filtretas, apjoms):
    """
    Sērija (oficiālais rezultāts ar OT/SO) šajā sezonā un, ja izvēlētas visas sezonas, arī kopā; nākamā savstarpējā spēle;
    brīdinājums par mazo izlasi (un par sastāvu maiņu starp sezonām).
    """
    e = _html.escape
    nak = _nakama_txt(sl_nakama_savstarpeja(kreisa, laba))
    rindas = [f"Šī sezona: {_serijas_txt(kreisa, laba, sezona_r)}" if not sezona_r.empty else "Šī sezona: vēl nav spēlējušas"]
    if apjoms == "visas" and not visas_r.empty:
        sez = sorted(visas_r["sezona"].dropna().astype(int).unique())
        diap = sez_nos(sez[0]) if sez[0] == sez[-1] else f"{sez_nos(sez[0])}–{sez_nos(sez[-1])}"
        rindas.append(f"Visas sezonas ({diap}): {_serijas_txt(kreisa, laba, visas_r)}")
    n = len(filtretas)
    if not n:
        piez = "Ar šo vietas izvēli savstarpējo spēļu nav – izvēlies otru komandu mājās vai noņem izvēli."
    else:
        piez = (f"Statistika pēc {n} savstarpēj{'ās spēles' if n == 1 else 'ām spēlēm'} – izlase ir maza, procenti un vidējie ir mazāk droši nekā sezonas dati."
                + (" Iepriekšējās sezonās komandu sastāvi bija citādi." if apjoms == "visas" else ""))
    return ('<div class="h2h-sum">' + "".join(f'<div class="h2h-ser">{r}</div>' for r in rindas)
            + (f'<div class="h2h-ser h2h-nak">{e(nak)}</div>' if nak else "")
            + f'<div class="h2h-piez">{e(piez)}</div></div>')


def sl_h2h_saraksts_html(kreisa, rindas):
    """Viens kopīgs savstarpējo spēļu saraksts: datums, mājinieki – viesi, rezultāts (saite uz protokolu), W/L no kreisās komandas skatpunkta."""
    e = _html.escape
    global SAKUMI
    if not SAKUMI and "sakums_lv" in RAW.columns:
        SAKUMI = dict(zip(RAW["game_id"], RAW["sakums_lv"]))
    raw_db, _ = ielasit_db_visu(VERSIJA)
    sak_db = dict(zip(raw_db["game_id"], raw_db["sakums_lv"])) if raw_db is not None and "sakums_lv" in raw_db.columns else {}
    sez_tagad = globals().get("SEZONA")
    rn, pedeja_sez = "", None
    for r in rindas.itertuples():
        sez = int(r.sezona) if pd.notna(getattr(r, "sezona", None)) else sez_tagad
        if sez != pedeja_sez:                              # sezonas atdalītājs
            rn += f'<div class="h2h-sez">{sez_nos(sez)}{" · šī sezona" if sez == sez_tagad else ""}</div>'
            pedeja_sez = sez
        maj, vie = (kreisa, r.pretinieks) if r.majas == 1 else (r.pretinieks, kreisa)
        gm, gv = (int(r.g_tot), int(r.z_tot)) if r.majas == 1 else (int(r.z_tot), int(r.g_tot))
        bg = da.beigu_etikete(r.beigas)
        tagad = sez == sez_tagad
        saite = speles_saite(r.game_id) if tagad else f"https://www.nhl.com/gamecenter/{int(r.game_id)}"   # vēsturei – NHL protokols
        rn += (f'<div class="ks-r h2h-r"><span class="ks-d">{dt_html(SAKUMI.get(r.game_id) if tagad else sak_db.get(r.game_id), r.datums)}</span>'
               f'<span class="ks-o h2h-k"><img src="{e(da.logo_url(maj))}" alt="">{e(maj)}<span class="ks-v">–</span>'
               f'<img src="{e(da.logo_url(vie))}" alt="">{e(vie)}</span>'
               f'<a class="ks-s" href="{e(saite)}" target="_blank" rel="noopener">{gm}:{gv}{(" " + bg) if bg else ""}</a>'
               f'<span class="ks-z">{rez_zime(rez_kods(r.rez, r.beigas))}</span></div>')
    virsr = "Savstarpējās spēles" + (" (play-off)" if SEZ_DALA == da.TIPS_PO else "")
    return (f'<div class="h2h-l"><div class="l5h">{virsr}</div>'
            f'<div class="ks">{rn or "<div class=ks-r>Ar šādu atlasi spēļu nav</div>"}</div></div>')


def sl_pedejas5_html(kods, puse):
    """Komandas pēdējās 5 spēles (jaunākā augšā). Rezultāts ir saite uz spēles protokolu sadaļā Rezultāti (jaunā cilnē)."""
    g = DF[DF["komanda"] == kods].sort_values(["datums", "game_id"]).tail(5).iloc[::-1]
    global SAKUMI
    if not SAKUMI and "sakums_lv" in RAW.columns:
        SAKUMI = dict(zip(RAW["game_id"], RAW["sakums_lv"]))
    rindas = ""
    for r in g.itertuples():
        bg = da.beigu_etikete(r.beigas)
        rez = f"{int(r.g_tot)}:{int(r.z_tot)}" + (f" {bg}" if bg else "")
        u = rez_kods(r.rez, r.beigas)
        rindas += (f'<div class="l5r"><span class="l5d">{dt_html(SAKUMI.get(r.game_id), r.datums)}</span>'
                   f'<span class="l5v">{"vs" if r.majas == 1 else "@"}</span>'
                   f'<img class="l5lg" src="{_html.escape(da.logo_url(r.pretinieks))}" alt="{_html.escape(r.pretinieks)}" title="{_html.escape(da.pilns_nosaukums(r.pretinieks))}">'
                   f'<a class="l5s" href="{_html.escape(speles_saite(r.game_id))}" target="_blank" rel="noopener noreferrer">{rez}</a>'
                   f'<span class="l5z">{rez_zime(u)}</span></div>')
    return f'<div class="l5c {puse}"><div class="l5h">Pēdējās 5 spēles</div>{rindas or "<div class=l5r>Nav spēļu</div>"}</div>'


def _sl_salidzinat(a, b):
    # noklusējums jaunam salīdzinājumam: mājiniekiem mājas spēles, viesiem izbraukuma spēles, visa sezona
    st.session_state.update(sl_a=a, sl_b=b, sl_rezims="salidzinajums", sl_vh="Mājās", sl_va="Izbraukumā", sl_logs=None, sl_h2h_vieta=None,
                            sl_h2h_apjoms=None)


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
  function tikski() {                       // taimeri "kopš iepriekšējās spēles": skaitās uz priekšu līdz spēles sākumam
    d.querySelectorAll('.tk[data-no]').forEach(function (el) {
      var rinda = el.closest('.cel-taim');
      if (Date.now() < +el.dataset.no) { if (rinda) rinda.style.display = 'none'; return; }
      if (rinda && rinda.style.display === 'none') rinda.style.display = '';
      var s = Math.max(0, Math.floor((Math.min(Date.now(), +el.dataset.lidz) - (+el.dataset.no)) / 1000));
      el.classList.toggle('stop', Date.now() >= +el.dataset.lidz);          // spēle sākusies: taimeris apstājas un vairs nepulsē
      var p = function (n) { return (n < 10 ? '0' : '') + n; };
      el.textContent = p(Math.floor(s / 3600)) + ':' + p(Math.floor(s % 3600 / 60)) + ':' + p(s % 60);
    });
  }
  var tid = w.setInterval(tikski, 1000); tikski();
  d.addEventListener('scroll', plan, true);
  w.addEventListener('resize', plan);
  var mo = new w.MutationObserver(plan); mo.observe(d.body, { childList: true, subtree: true });
  w.__cmpPeld = { stop: function () { w.clearInterval(tid); d.removeEventListener('scroll', plan, true); w.removeEventListener('resize', plan); mo.disconnect();
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


SPELES_ILGUMS_APTUVENI_H = 2.5   # taimerim: iepriekšējās spēles aptuvenās beigas = sākums + 2,5 h
MAJAS_PEC_DIENAM = 3      # ja kopš pēdējās spēles pagājušas tik dienas vai vairāk, ceļš tiek skaitīts no komandas mājām


def _cel_laiks(h):
    """Ceļojuma laiks tekstā: ~1 h 50 min / ~45 min."""
    if not h or h <= 0:
        return ""
    m = int(round(h * 60 / 5.0)) * 5
    return f"~{m // 60} h {m % 60:02d} min" if m >= 60 else f"~{m} min"


def _cel_pilseta(k):
    return lokacijas.LOKACIJAS.get(k, {}).get("pilseta", k) if lokacijas is not None else k


def komandas_speles_pirms(kods, lidz):
    """Komandas spēles pirms brīža `lidz`: aizvadītās (dati) un kalendārā plānotās. Atgriež [(sākums, mājinieki, game_id)] laika secībā."""
    rindas = {}
    raw_ = globals().get("RAW_VISS")                       # ceļojumam vienmēr visas spēles (RS un PO), neatkarīgi no atlases
    raw_ = RAW if raw_ is None else raw_
    if raw_ is not None and not raw_.empty and "sakums_lv" in raw_.columns:
        x = raw_[((raw_["home_team"] == kods) | (raw_["away_team"] == kods)) & (raw_["sakums_lv"] < lidz)]
        for r in x.itertuples():
            rindas[r.game_id] = (r.sakums_lv, r.home_team, r.game_id)
    if KAL is not None and not KAL.empty:
        x = KAL[((KAL["majas_komanda"] == kods) | (KAL["viesu_komanda"] == kods)) & (KAL["sakums_lv"] < lidz)]
        for r in x.itertuples():
            rindas.setdefault(r.game_id, (r.sakums_lv, r.majas_komanda, r.game_id))
    return sorted((v for v in rindas.values() if pd.notna(v[0])), key=lambda v: v[0])


def _et_datums(ts):
    return pd.Timestamp(ts).tz_convert("America/New_York").date()


def sl_celojums_html(kreisa, laba):
    """
    Ceļojuma faktors salīdzinājumā (virs pēdējām 5 spēlēm).
    - Ja šīs komandas savā starpā spēlē tuvāko 2 dienu laikā: katrai komandai, cik jāceļo no pēdējās spēles vietas uz spēles vietu,
      ar kādu transportu un cik ilgi, atpūta un laika joslas; kritiski apstākļi tiek izcelti.
    - Citādi: attālums starp pilsētām, iespējamais pārvietošanās veids un laiks.
    """
    if lokacijas is None or kreisa not in lokacijas.LOKACIJAS or laba not in lokacijas.LOKACIJAS:
        return ""
    e = _html.escape
    sod = da.sodien_lv()
    spele = None
    if KAL is not None and not KAL.empty:
        d = KAL["datums_lv"].dt.date
        x = KAL[(d >= sod - timedelta(days=1)) & (d <= sod + timedelta(days=2)) & (KAL["sakums_lv"] > pd.Timestamp.now(tz=da.LV_TZ) - pd.Timedelta(hours=2))
                & (((KAL["majas_komanda"] == kreisa) & (KAL["viesu_komanda"] == laba)) | ((KAL["majas_komanda"] == laba) & (KAL["viesu_komanda"] == kreisa)))]
        if not x.empty:
            spele = x.sort_values("sakums_lv").iloc[0]
    if spele is None:                                      # nav savstarpējas spēles tuvākajās 2 dienās: tikai attālums starp pilsētām
        c = lokacijas.celojums(kreisa, laba)
        ikona = "🚌 autobuss" if c["veids"] == "autobuss" else "✈️ lidojums"
        tz = c["laika_joslu_starpiba_h"]
        tz_t = f" · laika joslu starpība {abs(tz):g} h" if tz else ""
        return (f'<div class="cel"><div class="cel-h">CEĻOJUMS</div>'
                f'<div class="cel-one"><div class="cel-km">{int(c["km"]):,} km</div>'.replace(",", " ")
                + f'<div class="cel-t">{e(_cel_pilseta(kreisa))} ↔ {e(_cel_pilseta(laba))} · {ikona} {_cel_laiks(c["laiks_h"])}{tz_t}</div>'
                f'<div class="cel-piez">Savstarpējas spēles tuvāko 2 dienu kalendārā nav</div></div></div>')
    majas, viesi = spele["majas_komanda"], spele["viesu_komanda"]
    sak = spele["sakums_lv"] if pd.notna(spele["sakums_lv"]) else pd.Timestamp(spele["datums_lv"]).tz_localize(da.LV_TZ) + pd.Timedelta(hours=2)
    f = lokacijas.speles_faktori(DF, majas, viesi, sak)

    def kolonna(kods, puse):
        # iepriekšējā spēle: aizvadītā vai jau kalendārā ieplānotā (piem., spēle iepriekšējā vakarā, kas vēl nav notikusi)
        sak_ts = pd.Timestamp(sak)
        pirms = komandas_speles_pirms(kods, sak_ts)
        iepr = pirms[-1] if pirms else None
        iepr_vieta = iepr[1] if iepr else None
        dienas = (_et_datums(sak_ts) - _et_datums(iepr[0])).days if iepr else None
        b2b = dienas == 1
        st_h = (sak_ts - pd.Timestamp(iepr[0])).total_seconds() / 3600 if iepr else None
        sp7 = sum(1 for s_ in pirms if (sak_ts - pd.Timestamp(s_[0])).total_seconds() <= 7 * 86400)
        fk = {"iepriekspeja_vieta": iepr_vieta}
        # sākumpunkts: pēdējās spēles pilsēta; ja kopš tās pagājušas 3+ dienas (vai spēles nav), komanda ceļo no mājām
        no_majam = not iepr_vieta or (dienas is not None and dienas >= MAJAS_PEC_DIENAM)
        no = kods if no_majam else iepr_vieta
        km = int(round(lokacijas.attalums_km(no, majas)))
        laiks = lokacijas.celojuma_laiks_h(km)
        tz = lokacijas.laika_joslu_starpiba_h(no, majas, pd.Timestamp(sak).to_pydatetime())
        krit, brid = [], []
        if b2b and km > 0:
            krit.append(f"otrā spēle pēc kārtas un ceļš {km:,} km".replace(",", " "))
        elif b2b:
            brid.append("otrā spēle pēc kārtas")
        if km >= 1500 and st_h is not None and st_h < 48 and not b2b:
            krit.append("garš ceļš īsā laikā")
        if tz and abs(tz) >= 2:
            brid.append(f"laika joslu maiņa {abs(tz):g} h")
        if sp7 >= 3:
            brid.append(f"{sp7 + 1}. spēle 7 dienās")
        if km == 0:
            galv, apaksa = "Nav jāceļo", ("mājās" if no_majam else "pēdējā spēle šeit pat")
        else:
            ikona = "🚌" if km <= lokacijas.AUTOBUSA_LIMITS_KM else "✈️"
            galv, apaksa = f"{km:,} km".replace(",", " "), (f"{ikona} {_cel_laiks(laiks)} · {e(_cel_pilseta(no))} → {e(_cel_pilseta(majas))}"
                                                             + (" (no mājām)" if no_majam and fk.get("iepriekspeja_vieta") else ""))
        atp = ("spēle otro dienu pēc kārtas" if b2b else (f"atpūta {dienas - 1} d." if dienas else "pirmā spēle"))
        tz_t = f" · laika josla {'+' if tz > 0 else '−'}{abs(tz):g} h" if tz else ""
        cls = "krit" if krit else ("brid" if brid else "")
        pared = ""
        if iepr and b2b and pd.Timestamp(iepr[0]) > pd.Timestamp.now(tz=da.LV_TZ):    # iepriekšējā spēle vēl tikai paredzēta
            gm, gv = iepr[1], None
            if KAL is not None and not KAL.empty:
                rr_ = KAL[KAL["game_id"] == iepr[2]]
                if not rr_.empty:
                    gv = rr_.iloc[0]["viesu_komanda"]
            pret_ = gv if gm == kods else gm
            pared = (f'<div class="cel-pared">Paredzēta spēle {pd.Timestamp(iepr[0]).tz_convert(da.LV_TZ):%d.%m(%H:%M)} · '
                     f'{"vs" if gm == kods else "@"} {e(da.pilns_nosaukums(pret_)) if pret_ else ""} ({e(_cel_pilseta(gm))})</div>')
        nozime = pared + (f'<div class="cel-b krit">Kritiski: {e("; ".join(krit))}</div>' if krit else
                  (f'<div class="cel-b brid">Jāņem vērā: {e("; ".join(brid))}</div>' if brid else ""))
        loma = "mājās" if kods == majas else "viesos"
        taim = ""
        if b2b and iepr:                                   # otrā spēle pēc kārtas: dzīvs laiks kopš iepriekšējās spēles aptuvenām beigām līdz šīs spēles sākumam
            if True:
                beigas_ = pd.Timestamp(iepr[0]) + pd.Timedelta(hours=SPELES_ILGUMS_APTUVENI_H)       # aptuvenas beigas = sākums + 2,5 h
                no_ms, lidz_ms = int(beigas_.timestamp() * 1000), int(pd.Timestamp(sak).timestamp() * 1000)
                pag = max(0, min(int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000), lidz_ms) - no_ms) // 1000
                apst = " stop" if int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000) >= lidz_ms else ""
                tagad_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
                slept = ' style="display:none"' if tagad_ms < no_ms else ""          # taimeris parādās tikai tad, kad iepriekšējā spēle (aptuveni) beigusies
                taim = (f'<div class="cel-taim"{slept}>Kopš iepriekšējās spēles beigām (~) <b class="tk{apst}" data-no="{no_ms}" data-lidz="{lidz_ms}">'
                        f'{pag // 3600:02d}:{pag % 3600 // 60:02d}:{pag % 60:02d}</b></div>')
        return (f'<div class="cel-c {puse} {cls}"><div class="cel-k">{e(kods)} · {loma}</div><div class="cel-km">{galv}</div>'
                f'<div class="cel-t">{apaksa}</div><div class="cel-t">{atp}{tz_t}</div>{nozime}{taim}</div>')

    sak_t = pd.Timestamp(sak).tz_convert(da.LV_TZ) if pd.Timestamp(sak).tzinfo else pd.Timestamp(sak)
    return (f'<div class="cel"><div class="cel-h">CEĻOJUMS</div>'
            f'<div class="cel-sub">Spēle {sak_t:%d.%m.} plkst. {sak_t:%H:%M} · {e(_cel_pilseta(majas))} ({e(majas)} mājās)</div>'
            f'<div class="cel-row">{kolonna(kreisa, "l")}{kolonna(laba, "r")}</div></div>')


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
    qa, qb = st.query_params.get("a"), st.query_params.get("b")    # saite no kalendāra: /salidzinat?a=DET&b=WPG
    if qa in da.KOMANDAS and qb in da.KOMANDAS and qa != qb and st.session_state.get("sl_qp_apstradats") != (qa, qb):
        st.session_state["sl_qp_apstradats"] = (qa, qb)
        _sl_salidzinat(qa, qb)
    kodi = sorted(da.KOMANDAS, key=lambda k: da.KOMANDAS[k])
    if "sl_a" not in st.session_state:                       # noklusējums: pirmā kalendāra spēle, kas vēl nav sākusies (mājinieki kreisajā pusē)
        nak = None
        if KAL is not None and not KAL.empty:
            nak = KAL[KAL["sakums_lv"] > pd.Timestamp.now(tz=da.LV_TZ)].sort_values("sakums_lv").head(1)
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
    h2h_visas = sl_h2h_speles(home, away)                 # šīs sezonas savstarpējās spēles (kreisās komandas skatpunktā)
    df_db = sl_db_rindas()                                # iepriekšējās sezonas (tā pati RS/PO atlase)
    h2h_db = sl_h2h_speles(home, away, df_db) if df_db is not None else h2h_visas.iloc[0:0]
    n_t, n_db = len(h2h_visas), len(h2h_db)
    if logs == SL_H2H and n_t + n_db == 0:                # citam pārim varēja palikt ieslēgts
        st.session_state["sl_logs"] = logs = None
    h2h = logs == SL_H2H
    n = SL_LOGI.get(logs)
    kopa = da.kopsavilkums(DF, "Visas", None)
    apjoms = "sezona"
    if h2h:                                               # statistika tikai no savstarpējām spēlēm; vieta – viena kopīga izvēle
        hv = st.session_state.get("sl_h2h_vieta")
        if hv not in (home, away):
            hv = st.session_state["sl_h2h_vieta"] = None
        apjoms = st.session_state.get("sl_h2h_apjoms")
        if apjoms not in SL_H2H_APJOMI or (apjoms == "sezona" and n_t == 0) or (apjoms == "visas" and n_db == 0):
            apjoms = st.session_state["sl_h2h_apjoms"] = "sezona" if n_t else "visas"
        h2h_kopa = pd.concat([h2h_visas, h2h_db], ignore_index=True) if apjoms == "visas" else h2h_visas
        h2h_kopa = h2h_kopa.sort_values(["datums", "game_id"], ascending=False)
        h2h_rindas = h2h_kopa if hv is None else h2h_kopa[h2h_kopa["majas"] == (1 if hv == home else 0)]
        avots = pd.concat([x for x in (DF, df_db if apjoms == "visas" else None) if x is not None], ignore_index=True)
        kh = ka = sl_kopsavilkums_no(avots[avots["game_id"].isin(set(h2h_rindas["game_id"]))])
    else:
        kh, ka = sl_kopsavilkums(vh or "Visas", n), sl_kopsavilkums(va or "Visas", n)
    a = kh.loc[home] if home in kh.index else None
    b = ka.loc[away] if away in ka.index else None
    gp = lambda k: int(kopa.loc[k, "GP"]) if k in kopa.index else 0                    # noqa: E731

    with st.container(key="cmp_head"):
        with st.container(key="cmp_ch"):
            st.markdown(sl_komanda_html(home, "a", gp(home), int(a["GP"]) if a is not None else 0, True), unsafe_allow_html=True)
            if not h2h:                                   # savstarpējās spēlēs vieta ir viena kopīga izvēle (zemāk)
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
            if not h2h:
                with st.container(key="cmp_va"):
                    for v in ("Mājās", "Izbraukumā"):
                        st.button(ETIKETES.get(v, v), key=f"slva_{v}", type="primary" if v == va else "secondary", on_click=_sl_tog, args=("sl_va", v))
    kx_ = speles_koeficienti(home, away)                  # koeficienti nākamajai spēlei starp šīm komandām (ja ir)
    if kx_ is not None:
        st.markdown(koef_bloks_html(kx_, ielasit_koef(VERSIJA)[1]), unsafe_allow_html=True)
    with st.container(key="sl_per"):                       # pēdējās 5 / 10 / savstarpējās: vienlaikus ieslēgta viena; neviena = visa sezona
        for p in SL_LOGI:
            st.button(p, key=f"slp_{p}", type="primary" if p == logs else "secondary", on_click=_sl_tog, args=("sl_logs", p))
        nak_txt = _nakama_txt(sl_nakama_savstarpeja(home, away)) if n_t == 0 else ""
        nav_nevienas = n_t + n_db == 0
        st.button(f"{SL_H2H} ({n_t})" if not n_db else f"{SL_H2H} ({n_t} · kopā {n_t + n_db})", key="slp_h2h",
                  type="primary" if h2h else "secondary", disabled=nav_nevienas,
                  help=("Nav spēlējušas ne šosezon, ne iepriekšējās sezonās" + (f" · {nak_txt}" if nak_txt else "")) if nav_nevienas else
                       (f"Šosezon {n_t}, iepriekšējās sezonās {n_db} savstarpējās spēles" if n_db else None),
                  on_click=_sl_tog, args=("sl_logs", SL_H2H))
    if n_t == 0:
        st.markdown(f'<div class="h2h-nav">Savstarpējās: šosezon vēl nav spēlējušas{f" · {_html.escape(nak_txt)}" if nak_txt else ""}'
                    f'{f" · iepriekšējās sezonās {n_db} spēles" if n_db else ""}</div>', unsafe_allow_html=True)
    if h2h:
        with st.container(key="pgr_h2hv"):                # viena kopīga vietas izvēle: neviena = visas savstarpējās spēles
            for kods in (home, away):
                st.button(f"{kods} mājās", key=f"slh2h_{kods}", type="primary" if hv == kods else "secondary",
                          on_click=_sl_tog, args=("sl_h2h_vieta", kods))
        if n_db:
            with st.container(key="pgr_h2hsez"):          # šī sezona / visas sezonas (DB)
                for k_, nos_ in SL_H2H_APJOMI.items():
                    st.button(nos_, key=f"slh2hs_{k_}", type="primary" if apjoms == k_ else "secondary",
                              disabled=(k_ == "sezona" and n_t == 0),
                              on_click=lambda v_=k_: st.session_state.__setitem__("sl_h2h_apjoms", v_))

    rindas = sl_peldosie_html(home, away)
    if h2h:
        rindas += sl_h2h_kopsavilkums_html(home, away, h2h_visas, pd.concat([h2h_visas, h2h_db], ignore_index=True), h2h_rindas, apjoms)
    for grupa, metrikas in SALIDZ_METRIKAS:
        rindas += f'<div class="cmp-group">{_html.escape(grupa.upper())}</div>'
        for nos, pask, k, labak, dec in metrikas:
            rindas += sl_rinda_html(nos, pask, a.get(k) if a is not None else None, b.get(k) if b is not None else None, labak, dec)
    try:
        rindas += sl_celojums_html(home, away)              # ceļojuma faktors (virs pēdējām 5 spēlēm)
    except Exception:
        pass
    if h2h:                                               # savstarpējās: viens kopīgs saraksts (abām komandām tās ir tās pašas spēles)
        rindas += sl_h2h_saraksts_html(home, h2h_rindas)
    else:
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
def iekseja_saite(cels, **param):
    """Saite uz citu lietotnes sadaļu ar parametriem un īslaicīgu parakstu (jaunā cilnē nav jāievada parole)."""
    from urllib.parse import urlencode
    zet = saites_zetons()
    if zet:
        param["t"] = zet
    return f"/{cels}" + (f"?{urlencode(param)}" if param else "")


class HtmlSuna(str):
    """Gatavs HTML tabulas šūnai (df_html to neaizvieto ar escape)."""


HTML_ZIME = '<span class="fb">'      # pandas 3 pārvērš str apakšklases par parastu str, tāpēc HTML šūnas atpazīst arī pēc sākuma


def ir_html_suna(v):
    return isinstance(v, HtmlSuna) or (isinstance(v, str) and v.startswith(HTML_ZIME))


def forma_bumbas(df, n=5):
    """
    Pēdējo n spēļu forma kā bumbiņas (vecākā → jaunākā): zaļa = win, sarkana = loss,
    oranža daļa + zaļa = OT win / SO win, oranža daļa + sarkana = OT loss / SO loss.
    Uzvedot (vai pieskaroties) bumbiņai: datums, pretinieks un rezultāts.
    """
    e = _html.escape
    sak = dict(zip(RAW["game_id"], RAW["sakums_lv"])) if "sakums_lv" in RAW.columns else {}
    out = {}
    for kom, g in df.sort_values(["datums", "game_id"]).groupby("komanda"):
        bumbas = ""
        for r in g.tail(n).itertuples():
            ot = str(r.beigas).upper() in ("OT", "SO")
            kl = ("uo" if ot else "u") if r.rez == "W" else ("zo" if r.rez == "OTL" or ot else "z")
            bg = da.beigu_etikete(r.beigas)
            s_ = sak.get(r.game_id)
            dat = f"{s_:%d.%m}" if s_ is not None and pd.notna(s_) else f"{pd.Timestamp(r.datums):%d.%m}"
            iz = REZ_NOZIME.get(rez_kods(r.rez, r.beigas), "")
            tip = f"{dat} · {'vs' if r.majas == 1 else '@'} {da.pilns_nosaukums(r.pretinieks)} {int(r.g_tot)}:{int(r.z_tot)}{(' ' + bg) if bg else ''} · {iz}"
            bumbas += f'<i class="{kl}" data-tip="{e(tip)}" title="{e(tip)}" tabindex="0"></i>'
        out[kom] = HtmlSuna(f'<span class="fb">{bumbas}</span>')
    return pd.Series(out)


def speles_saite(game_id):
    """Saite uz šīs spēles protokolu lietotnes sadaļā Rezultāti (atveras jaunā cilnē; saitē ir īslaicīgs paraksts, lai nebūtu jāievada parole)."""
    zet = saites_zetons()
    return f"/results?spele={int(game_id)}" + (f"&t={zet}" if zet else "")


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


def df_html(df, config=None, formati=None, prog=None, paskaidr=None, logo_kol=(), burbuli=None, bur_kol=None, platas=(), indekss=False, kartot=True,
            atgriezt=False, logo_saites=None, numurs_no=1):
    """
    Visas lietotnes tabulas: DataFrame kā caurspīdīga HTML tabula ar paskaidrojumiem virsrakstos (uzvedot peli).
    config: Streamlit column_config (None = kolonna paslēpta; image = logotips; progress = josla; format = skaitļa formāts; width='large' = plata teksta kolonna);
    formati/prog/logo_kol/platas: tas pats tieši; burbuli: saraksts (pa vienam katrai rindai) ar HTML burbuli kolonnai bur_kol (spēļu saraksts uz "Sp.").
    """
    if df is None or df.empty:
        if atgriezt:
            return ""
        st.info("Nav datu šim skatam.")
        return
    e = _html.escape
    config, formati, prog, paskaidr = config or {}, formati or {}, prog or {}, paskaidr or {}
    if atgriezt:
        kartot = False
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
        opcijas = {c["k"]: str(c["label"]) for c in kol if not c["logo"] and str(c["label"]) not in ("#", "") and not c["wide"]
                   and not (len(df) and ir_html_suna(df[c["k"]].iloc[0]))}
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
            if logo_saites is not None:
                logo_saites = [logo_saites[i] for i in seciba]
            if "#" in df.columns:
                df["#"] = range(numurs_no, numurs_no + len(df))
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
                img_ = f'<img class="tb-logo" width="38" height="38" src="{e(str(v))}" alt="">' if isinstance(v, str) and v else ""
                if img_ and logo_saites is not None and logo_saites[i]:
                    img_ = f'<a class="tb-logo-a" href="{e(logo_saites[i])}" target="_blank" rel="noopener" title="Atvērt komandas statistiku">{img_}</a>'
                rinda += f'<td class="lg">{img_}</td>'
            elif k == bur_kol and burbuli is not None and burbuli[i]:
                rinda += f'<td class="tbsp" tabindex="0"><span class="spw">{_fmt_v(v, "{:.0f}")}<span class="bubble">{burbuli[i]}</span></span></td>'
            elif c["prog"] is not None:
                lo, hi = c["prog"]
                platums = 0 if pd.isna(v) else max(0, min(100, (v - lo) / (hi - lo) * 100))
                rinda += f'<td><div class="pb"><i style="width:{platums:.0f}%"></i><b>{_fmt_v(v, c["fmt"])}</b></div></td>'
            elif ir_html_suna(v):
                rinda += f'<td class="l">{v}</td>'
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
    html_ = f'<div class="tb-wrap{garsa}"><table class="tb"><thead><tr>{galva}</tr></thead><tbody>{rindas}</tbody></table></div>'
    if atgriezt:
        return html_
    st.markdown(html_, unsafe_allow_html=True)


def lapa_periodi():
    st.title("Periodi")
    augsa = st.container()
    with st.container(key="frinda_per"):
        p = int(izvele("Hokeja periods", ["1. periods", "2. periods", "3. periods"], key="per_p")[0])
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="per_scope")
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="per_logs")
    kolonna = "Starpiba"                                   # noklusējuma secība; citu secību izvēlas tabulas izvēlnē "Kārtot"
    kartes_p = []
    for pp in (1, 2, 3):                                   # labākās komandas katrā periodā pēc vidēji gūtajiem vārtiem
        tp_ = da.periodu_tabula(DF, pp, scope, LOGI[logs])
        kartes_p.append(kom_kartes(tp_, "G_sp", f"{pp}. periods – vidēji gūti", lambda v: _sk(v, 2)))
    kp_ = da.kopsavilkums(DF, scope, LOGI[logs])
    kartes_p.append(kom_kartes(kp_, "G_sp", "Pamatlaikā kopā – vidēji gūti", lambda v: _sk(v, 2)))
    with augsa:
        st.markdown('<p class="ld-h">Topi</p>' + top_kartes_html(kartes_p), unsafe_allow_html=True)
    res = da.periodu_tabula(DF, p, scope, LOGI[logs])
    pask = {
        "Gūti": f"{p}. periodā gūtie vārti (kopā izvēlētajās spēlēs)",
        "Ielaisti": f"{p}. periodā ielaistie vārti (kopā izvēlētajās spēlēs)",
        "Starpība": f"Gūto un ielaisto vārtu starpība {p}. periodā (kopā izvēlētajās spēlēs)",
        "Gūti/v.": f"Vidēji gūtie vārti {p}. periodā vienā spēlē",
        "Ielaisti/v.": f"Vidēji ielaistie vārti {p}. periodā vienā spēlē",
        "Metieni/v.": f"Vidēji metieni vārtos {p}. periodā vienā spēlē",
        "Metieni pret/v.": f"Pretinieka vidējie metieni vārtos pret šo komandu {p}. periodā vienā spēlē",
    }
    n_ = LOGI[logs]
    burbuli = None
    if n_ in (5, 10) and not res.empty:        # "Visa sezona": spēļu saraksta burbuļus nerāda
        burbuli = spelu_burbuli(scope, n_, lambda r: (getattr(r, f"g_p{p}"), getattr(r, f"z_p{p}")),
                                f"{p}. periods · pēdējās {n_} spēles{vietas_teksts(scope)} (komanda:pretinieks)", set(res.index))
    tabula(res, {"G": "Gūti", "Z": "Ielaisti", "Starpiba": "Starpība",
                 "G_sp": "Gūti/v.", "Z_sp": "Ielaisti/v.", "SOG_sp": "Metieni/v.", "SA_sp": "Metieni pret/v."},
           sort_col=kolonna, paskaidr=pask, burbuli=burbuli,
           formati={"G_sp": "{:.2f}", "Z_sp": "{:.2f}", "SOG_sp": "{:.1f}", "SA_sp": "{:.1f}"},
           config={"Gūti/v.": st.column_config.NumberColumn(format="%.2f"),
                   "Ielaisti/v.": st.column_config.NumberColumn(format="%.2f"),
                   "Metieni/v.": st.column_config.NumberColumn(format="%.1f"),
                   "Metieni pret/v.": st.column_config.NumberColumn(format="%.1f")})


# ============================================================================
# LAPA: FORMA UN VĀRTI
# ============================================================================
def lapa_forma():
    st.title("Forma un vārti")
    with st.container(key="frinda_fm"):
        n = int(izvele("Pēdējās spēles", ["5", "10"], key="fm_n"))

    res = da.kopsavilkums(DF, "Visas", n)
    res["Forma"] = forma_bumbas(DF, n)
    kol, asc = "G", False                                  # noklusējums: visvairāk gūto vārtu; citu secību - tabulas izvēlnē "Kārtot"
    burbuli = spelu_burbuli("Visas", n, lambda r: (r.g_reg, r.z_reg), f"Pēdējās {n} spēles · pamatlaika vārti (komanda:pretinieks)", set(res.index))
    tabula(res, {"W": "W", "L": "L", "OTL": "OTL", "PTS": "Punkti",
                 "G": "Gūti vārti", "Z": "Ielaisti vārti", "Starpiba": "Starpība", "Forma": "Forma"},
           sort_col=kol, ascending=asc, burbuli=burbuli)


# ============================================================================
# LAPA: OVER / UNDER
# ============================================================================
def lapa_over_under():
    st.title("Vairāk / Mazāk")
    with st.container(key="frinda_ou"):
        linija = float(izvele("Līnija", ["5.5", "6.5", "7.5"], default="6.5", key="ou_l"))
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="ou_s")
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", default="Pēdējās 10", key="ou_n")
    res = da.over_under(DF, linija, scope, LOGI[logs])
    kol = "Over"                                           # noklusējums; Under u.c. secība - tabulas izvēlnē "Kārtot"
    n_ = LOGI[logs]
    burbuli = None
    if n_ in (5, 10) and not res.empty:
        burbuli = spelu_burbuli(scope, n_, lambda r: (r.g_reg, r.z_reg),
                                f"Pēdējās {n_} spēles{vietas_teksts(scope)} · pamatlaika vārti (komanda:pretinieks)", set(res.index))
    tabula(res, {"Over": f"Over {linija}", "Over_pct": "Over %",
                 "Under": f"Under {linija}", "Under_pct": "Under %", "Vid_kopa": "Vid. vārti spēlē"},
           sort_col=kol, burbuli=burbuli, formati={"Vid_kopa": "{:.2f}"}, prog={"Over_pct": (0, 100), "Under_pct": (0, 100)},
           config={"Over %": st.column_config.ProgressColumn("Over %", min_value=0, max_value=100, format="%.0f"),
                   "Under %": st.column_config.ProgressColumn("Under %", min_value=0, max_value=100, format="%.0f"),
                   "Vid. vārti spēlē": st.column_config.NumberColumn(format="%.2f")})


# ============================================================================
# LAPA: POWERPLAY
# ============================================================================
def lapa_powerplay():
    st.title("Vairākums")
    augsa = st.container()
    with st.container(key="frinda_pp"):
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="pp_s")
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="pp_n")
    kol = "PPG"                                            # noklusējums; citu secību izvēlas tabulas izvēlnē "Kārtot"
    n_ = LOGI[logs]
    res = da.kopsavilkums(DF, scope, n_)
    if res.empty:
        st.info("Šim skatam datu nav.")
        return
    pari, _ = _apakskopa_pari(scope, n_)
    tp = spelētaju_situacijas_topi("pp", pari)
    kartes = [spel_kartes(tp, "P", "Punkti vairākumā", lambda r: f" · {int(r.G)} v. + {int(r.A)} p."),
              spel_kartes(tp, "G", "Vārti vairākumā"), spel_kartes(tp, "A", "Piespēles vairākumā"),
              kom_kartes(res, "PP_pct", "PP % (komandas)", lambda v: f"{v:.1f}%", lambda k: f" · {int(res.loc[k, 'PPG'])}/{int(res.loc[k, 'PP_opp'])}",
                         filtrs=lambda x: x["PP_opp"] > 0,
                         tip_f=lambda k: f"{int(res.loc[k, 'PPG'])} vārti no {int(res.loc[k, 'PP_opp'])} vairākumiem"),
              kom_kartes(res, "PPG", "PP vārti (komandas)", lambda v: f"{int(v)}")]
    with augsa:
        st.markdown('<p class="ld-h">Topi</p>' + top_kartes_html(kartes), unsafe_allow_html=True)
    burbuli = None
    if n_ in (5, 10):
        burbuli = spelu_burbuli(scope, n_, lambda r: (r.ppg, r.ppg_allowed),
                                f"Pēdējās {n_} spēles{vietas_teksts(scope)} · vairākuma vārti (par:pret)", set(res.index))
    tabula(res, {"PPG": "PP vārti", "PP_opp": "PP iespējas", "PP_pct": "PP %",
                 "PP_sog": "PP metieni", "PPG_pret": "Ielaisti PP"},
           sort_col=kol, burbuli=burbuli, formati={"PP_pct": "{:.1f}"},
           config={"PP %": st.column_config.NumberColumn(format="%.1f")})


# ============================================================================
# LAPA: NORAIDĪJUMI
# ============================================================================
def noraidijumu_topi_html(scope, n):
    """Noraidījumu topi: komandas (vidēji spēlē un pa periodiem) un spēlētāji (vidēji spēlē, kopā, sodu minūtes)."""
    t = da.noraidijumu_tabula(DF, scope, n, "skaits", True)
    kartes = []
    if t is not None and not t.empty:
        f2 = lambda v: _sk(v, 2)                                                                  # noqa: E731
        kartes += [kom_kartes(t, "s_kopa", "Noraidījumi spēlē (komandas)", f2),
                   kom_kartes(t, "s_1", "1. periodā (komandas, vidēji)", f2),
                   kom_kartes(t, "s_2", "2. periodā (komandas, vidēji)", f2),
                   kom_kartes(t, "s_3", "3. periodā (komandas, vidēji)", f2)]
    sk_ = ielasit_papildu("speletaji", VERSIJA)
    if sk_ is not None and not sk_.empty:
        pari, _ = _apakskopa_pari(scope, n)
        x = sk_[pd.Series([(gi, kk) in pari for gi, kk in zip(sk_["game_id"], sk_["team"])], index=sk_.index)]
        if not x.empty:
            agg = {"vards": ("vards", "last"), "GP": ("game_id", "nunique"), "PIM": ("pim", "sum")}
            if "noraid" in x.columns and x["noraid"].notna().any():
                agg["N"] = ("noraid", "sum")
            g = x.groupby(["playerId", "team"]).agg(**agg).reset_index()
            def spl(kol, nos, fmt, filtrs=None, tip=None):
                y = g if filtrs is None else g[filtrs(g)]
                y = y[y[kol] > 0].sort_values([kol, "GP"], ascending=[False, True]).head(10)
                return (nos, [(f"{r.vards} ({r.team})", fmt(getattr(r, kol)), f" · {int(r.GP)} sp.", spel_foto_html(r.playerId, r.team, r.vards) if i_ == 0 else "",
                               tip(r) if tip else "") for i_, r in enumerate(y.itertuples())])
            if "N" in g.columns:
                g["N_sp"] = g["N"] / g["GP"]
                min_gp = 3 if g["GP"].max() >= 5 else 1
                kartes += [spl("N_sp", "Noraidījumi vidēji spēlē (spēlētājs)", lambda v: _sk(v, 2), filtrs=lambda y: y["GP"] >= min_gp,
                               tip=lambda r: f"{int(r.N)} noraidījumi {int(r.GP)} spēlēs"),
                           spl("N", "Visvairāk noraidījumu (spēlētājs)", lambda v: f"{int(v)}")]
            kartes.append(spl("PIM", "Visvairāk sodu minūšu (spēlētājs)", lambda v: f"{int(v)}"))
    return top_kartes_html(kartes)


def lapa_noraidijumi():
    st.title("Noraidījumi")
    augsa = st.container()
    with st.container(key="frinda_nr"):
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="nr_s")
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="nr_n")
        perioda = sledzis("Hokeja periods", ["1. periods", "2. periods", "3. periods"], "Visi periodi", key="nr_p")
        metrika = izvele("Rādītājs", ["Noraidījumu skaits", "Sodu minūtes"], key="nr_m")
        vertiba = sledzis("Vērtība", ["Vidēji spēlē"], "Kopā", default="Vidēji spēlē", key="nr_v")
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
        kolonnas, pask = {}, {}
        for nos, p in [("1. periods", 1), ("2. periods", 2), ("3. periods", 3), ("Kopā", "kopa")]:      # Kopā – pēdējā kolonna
            kolonnas[f"{vkods}_{p}"] = nos
            pask[nos] = apraksts(vkods, p)
        tabula(res, kolonnas, sort_col=f"{vkods}_kopa", paskaidr=pask,
               config={nos: st.column_config.NumberColumn(format=fm) for nos in pkarte})
    else:
        p = pkarte[perioda]
        kolonnas = {f"s_{p}": "Saņemtie", f"i_{p}": "Izcīnītie", f"r_{p}": "Izcīnīti − saņemti"}
        pask = {"Saņemtie": apraksts("s", p), "Izcīnītie": apraksts("i", p),
                "Izcīnīti − saņemti": f"Izcīnīto un saņemto starpība ({ptxt[p]}, {mtxt}, {vtxt}); "
                                      "pozitīvs skaitlis = komanda izcīna vairāk, nekā saņem"}
        tabula(res, kolonnas, sort_col=f"{vkods}_{p}", paskaidr=pask,
               config={"Saņemtie": st.column_config.NumberColumn(format=fm),
                       "Izcīnītie": st.column_config.NumberColumn(format=fm),
                       "Izcīnīti − saņemti": st.column_config.NumberColumn(format=fm.replace("%", "%+"))})
    with augsa:
        st.markdown('<p class="ld-h">Topi</p>' + noraidijumu_topi_html(scope, LOGI[logs]), unsafe_allow_html=True)


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


def spel_foto_html(player_id, komanda, vards=""):
    """Spēlētāja oficiālais NHL foto (assets.nhle.com), pietuvināts sejai. Ja foto nav, paliek tukšs gaišs aplis."""
    try:
        pid = int(player_id)
    except (TypeError, ValueError):
        return ""
    sod = da.sodien_lv()
    sez = sod.year if sod.month >= 9 else sod.year - 1
    url = f"https://assets.nhle.com/mugs/nhl/{sez}{sez + 1}/{komanda}/{pid}.png"
    return (f'<div class="ld-foto" role="img" aria-label="{_html.escape(vards)}" '
            f'style="background-image:url(\'{url}\')"></div>')


KOMANDU_DIVIZIJAS = {**{k: ("Austrumu", "Atlantijas") for k in ("BOS", "BUF", "DET", "FLA", "MTL", "OTT", "TBL", "TOR")},
                     **{k: ("Austrumu", "Metropolitēna") for k in ("CAR", "CBJ", "NJD", "NYI", "NYR", "PHI", "PIT", "WSH")},
                     **{k: ("Rietumu", "Centrālā") for k in ("CHI", "COL", "DAL", "MIN", "NSH", "STL", "UTA", "WPG")},
                     **{k: ("Rietumu", "Klusā okeāna") for k in ("ANA", "CGY", "EDM", "LAK", "SJS", "SEA", "VAN", "VGK")}}
KOMANDAS_DZ_GRUPAS = [   # padziļinātā statistika pa tēmām: (nosaukums, kolonna, zīmes aiz komata, vai labāk augsts (None = bez vietas))
    ("Rezultāti", [("Spēles", "GP", 0, None), ("Win", "W", 0, True), ("Loss", "L", 0, False), ("OT loss / SO loss", "OTL", 0, None),
                   ("Punkti", "PTS", 0, True), ("Punkti %", "PTS_pct", 1, True)]),
    ("Vārti", [("Gūtie vārti", "G", 0, True), ("Ielaistie vārti", "Z", 0, False), ("Vārtu starpība", "Starpiba", 0, True),
               ("Vārti spēlē", "G_sp", 2, True), ("Ielaisti spēlē", "Z_sp", 2, False), ("Over 6.5 %", "Over65", 0, None), ("Over 5.5 %", "Over55", 0, None)]),
    ("Vārti pa periodiem (vidēji spēlē)", [("Gūti 1. periodā", "G_p1", 2, True), ("Gūti 2. periodā", "G_p2", 2, True), ("Gūti 3. periodā", "G_p3", 2, True),
                                           ("Ielaisti 1. periodā", "Z_p1", 2, False), ("Ielaisti 2. periodā", "Z_p2", 2, False), ("Ielaisti 3. periodā", "Z_p3", 2, False)]),
    ("Metieni", [("Metieni spēlē", "SOG_sp", 1, True), ("Pretinieka metieni spēlē", "SA_sp", 1, False), ("Metienu daļa %", "SOG_dala", 1, True)]),
    ("Vairākums un mazākums", [("Vairākums PP %", "PP_pct", 1, True), ("Vairākuma vārti", "PPG", 0, True), ("Vairākuma iespējas", "PP_opp", 0, None),
                               ("Vairākuma metieni", "PP_sog", 0, True), ("Mazākums PK %", "PK_pct", 1, True), ("Ielaisti mazākumā", "PPG_pret", 0, False),
                               ("Mazākuma reizes", "PP_opp_pret", 0, None)]),
    ("Noraidījumi", [("Noraidījumi spēlē", "PEN_sp", 1, False), ("Sodu minūtes spēlē", "PIM_sp", 1, False),
                     ("Izcīnītie noraidījumi spēlē", "DRAW_sp", 1, True), ("Noraidījumu starpība spēlē", "PEN_starpiba", 2, False)]),
    ("Spēles stils (vidēji spēlē)", [("Sitieni", "hits", 1, None), ("Bloķētie metieni", "blocked", 1, None), ("Ripas zaudējumi", "giveaways", 1, False),
                                    ("Ripas atņemšanas", "takeaways", 1, True), ("Iemetieni %", "fo_pct", 1, True)]),
]


def lapa_komanda():
    qk = st.query_params.get("kom")                               # saite no salīdzinājuma: /komanda?kom=BUF
    if qk in da.KOMANDAS and st.session_state.get("kom_qp_apstradats") != qk:
        st.session_state["kom_qp_apstradats"] = qk
        st.session_state["kom_izv"] = qk
    kom = komandu_registis()
    tdf = DF[DF["komanda"] == kom]
    if tdf.empty:
        st.warning("Šai komandai vēl nav datu.")
        return
    st.markdown(f'<div class="kom-nos">{_html.escape(da.pilns_nosaukums(kom))}</div>', unsafe_allow_html=True)

    t_gal, t_lid, t_sp, t_nak, t_dz, t_par = st.tabs(["Statistika", "Spēlētāju statistika", "Aizvadītās spēles", "Nākamās spēles",
                                                      "Padziļināta statistika", "Par komandu"])
    e = _html.escape
    liga = da.kopsavilkums(DF, "Visas", None)
    kop = liga.loc[kom] if kom in liga.index else da.kopsavilkums(tdf).iloc[0]

    def vieta(k, augsts=True, tab=liga):
        """Komandas vieta līgā pēc rādītāja (1 = labākā)."""
        if tab is None or k not in tab.columns or kom not in tab.index or pd.isna(tab.loc[kom, k]):
            return None
        return int(tab[k].rank(ascending=not augsts, method="min").loc[kom])

    def vieta_html(v, n=None):
        if v is None:
            return ""
        n = n or len(liga)
        kl = "ok" if v <= n // 4 else ("slikti" if v > n - n // 4 else "")
        return f'<span class="kpi-r {kl}">{v}. vieta līgā</span>'

    with t_gal:                                           # svarīgākie rādītāji
        kartes = [
            ("Bilance (W-L-OTL)", f"{int(kop['W'])}-{int(kop['L'])}-{int(kop['OTL'])}", f"{int(kop['PTS'])} punkti · {kop['PTS_pct']:.0f}%", vieta("PTS_pct")),
            ("Vārti spēlē", _sk(kop["G_sp"], 2), f"kopā {int(kop['G'])}", vieta("G_sp")),
            ("Ielaisti spēlē", _sk(kop["Z_sp"], 2), f"kopā {int(kop['Z'])}", vieta("Z_sp", False)),
            ("Vārtu starpība", f"{int(kop['Starpiba']):+d}", f"{int(kop['GP'])} spēlēs", vieta("Starpiba")),
            ("Metieni spēlē", _sk(kop["SOG_sp"], 1), f"pretinieki {_sk(kop['SA_sp'], 1)}", vieta("SOG_sp")),
            ("Vairākums PP %", _sk(kop["PP_pct"], 1) if pd.notna(kop["PP_pct"]) else "–", f"{int(kop['PPG'])}/{int(kop['PP_opp'])} vārti", vieta("PP_pct")),
            ("Mazākums PK %", _sk(kop["PK_pct"], 1) if pd.notna(kop["PK_pct"]) else "–", f"ielaisti {int(kop['PPG_pret'])}", vieta("PK_pct")),
            ("Noraidījumi spēlē", _sk(kop["PEN_sp"], 1), f"izcīnīti {_sk(kop['DRAW_sp'], 1)}", vieta("PEN_sp", False)),
        ]
        try:                                              # papildlaika un metienu sēriju bilances (no sadaļas OT / SO)
            go = otso_kopsavilkums("Visas", None)
            if kom in go.index:
                o = go.loc[kom]
                rot = lambda kol, aug=True: int(go[kol].rank(ascending=not aug, method="min").loc[kom])     # noqa: E731
                kartes += [("OT win – OT loss", o["OT_bil"], f"{int(o['OT_W'] + o['OT_L'])} spēles izšķīrās papildlaikā", rot("OT_W")),
                           ("SO win – SO loss", o["SO_bil"], f"{int(o['SO_W'] + o['SO_L'])} metienu sērijas", rot("SO_W"))]
        except Exception:
            pass
        st.markdown('<div class="kpi-grid">' + "".join(
            f'<div class="kpi"><div class="kpi-l">{e(l)}</div><div class="kpi-v">{e(v)}</div><div class="kpi-s">{e(s)}</div>{vieta_html(r)}</div>'
            for l, v, s, r in kartes) + "</div>", unsafe_allow_html=True)
        # forma: pēdējās 5 spēles
        l5 = tdf.sort_values(["datums", "game_id"]).tail(5)
        forma = "".join(f'<a class="fm-b {REZ_KRASA.get(rez_kods(r.rez, r.beigas), "")}" href="{e(speles_saite(r.game_id))}" target="_blank" rel="noopener" '
                        f'data-tip="{e(REZ_NOZIME.get(rez_kods(r.rez, r.beigas), ""))} {int(r.g_tot)}:{int(r.z_tot)} · {"vs" if r.majas == 1 else "@"} {e(da.pilns_nosaukums(r.pretinieks))}" '
                        f'title="{e(REZ_NOZIME.get(rez_kods(r.rez, r.beigas), ""))} {int(r.g_tot)}:{int(r.z_tot)} · {e(da.pilns_nosaukums(r.pretinieks))}">{REZ_BURTS.get(rez_kods(r.rez, r.beigas), "")}</a>'
                        for r in l5.itertuples())
        nak = da.nakamas_speles(KAL, 1, komanda=kom) if KAL is not None else None
        nak_html = ""
        if nak is not None and not nak.empty:
            n0 = nak.iloc[0]
            pret = n0["viesu_komanda"] if n0["majas_komanda"] == kom else n0["majas_komanda"]
            href_ = e(iekseja_saite("compare", a=n0["majas_komanda"], b=n0["viesu_komanda"]))
            nak_html = (f'<div class="kn"><div class="kpi-l">Nākamā spēle</div><div class="kn-r">'
                        f'<a class="kn-a" href="{href_}" target="_blank" rel="noopener" data-tip="Salīdzināt komandas" title="Salīdzināt komandas">'
                        f'<img src="{e(da.logo_url(pret))}" alt=""></a>'
                        f'<div><b>{"vs" if n0["majas_komanda"] == kom else "@"} <a class="kn-a" href="{href_}" target="_blank" rel="noopener" '
                        f'title="Salīdzināt komandas">{e(da.pilns_nosaukums(pret))}</a></b>'
                        f'<div class="kpi-s">{n0["sakums_lv"]:%d.%m(%H:%M)} · {"mājās" if n0["majas_komanda"] == kom else "viesos"} · uzspied, lai salīdzinātu</div></div></div></div>')
        st.markdown(f'<div class="kpi-row"><div class="kn"><div class="kpi-l">Forma (pēdējās 5)</div><div class="fm">{forma}</div>'
                    f'<div class="fm-dir"><span>← vecākā</span><span>jaunākā →</span></div></div>{nak_html}</div>',
                    unsafe_allow_html=True)

    with t_lid:                                           # komandas līderi (kā kartītes cilnē Statistika)
        sk_k = ielasit_papildu("speletaji", VERSIJA)
        vg_k = ielasit_papildu("vartsargi", VERSIJA)
        sk_k = sk_k[sk_k["team"] == kom] if sk_k is not None and not sk_k.empty else None
        vg_k = vg_k[vg_k["team"] == kom] if vg_k is not None and not vg_k.empty else None
        Lp = da.speletaju_lideri(sk_k) if sk_k is not None and not sk_k.empty else pd.DataFrame()
        Lg = da.vartsargu_lideri(vg_k) if vg_k is not None and not vg_k.empty else pd.DataFrame()
        if Lp.empty and Lg.empty:
            st.info("Šai komandai spēlētāju datu vēl nav.")
        else:
            def toi_t(m):
                return f"{int(m)}:{int(round((m - int(m)) * 60)):02d}" if pd.notna(m) else "–"

            def lideru_karte(nos, tab, kol, vards_kol, fmt_f, augsts=True, min_gp=1, piez=""):
                if tab.empty or kol not in tab.columns:
                    return ""
                t_ = tab[(tab["GP"] >= min_gp) & tab[kol].notna()]
                if t_.empty:
                    return ""
                t_ = t_.sort_values([kol, "GP"], ascending=[not augsts, False]).head(7)
                r0 = t_.iloc[0]
                rinda_ = lambda n, r: f'<div class="ld-c"><span>{n}. {e(str(r[vards_kol]))}</span><b>{e(fmt_f(r[kol]))}</b></div>'   # noqa: E731
                citi = "".join(rinda_(n + 2, r) for n, (_, r) in enumerate(t_.iloc[1:3].iterrows()))
                vel = "".join(rinda_(n + 4, r) for n, (_, r) in enumerate(t_.iloc[3:7].iterrows()))
                izvers = (f'<details class="ld-x"><summary><span class="ld-a">Rādīt top 7 ▾</span><span class="ld-z">Paslēpt ▴</span></summary>{vel}</details>'
                          if vel else "")
                foto = spel_foto_html(r0.get("playerId"), kom, str(r0[vards_kol]))
                return (f'<div class="kpi ld-k"><div class="ld-top">{foto}<div class="kpi-l">{e(nos)}</div><div class="kpi-v">{e(fmt_f(r0[kol]))}</div>'
                        f'<div class="ld-v">{e(str(r0[vards_kol]))}<span> · {int(r0["GP"])} sp.{piez}</span></div></div>{citi}{izvers}</div>')
            vesels = lambda v: f"{int(v)}"                                                    # noqa: E731
            ar_zimi = lambda v: f"{int(v):+d}"                                                # noqa: E731
            kartes_p = [lideru_karte("Punkti", Lp, "P", "Speletajs", vesels), lideru_karte("Vārti", Lp, "G", "Speletajs", vesels),
                        lideru_karte("Piespēles", Lp, "A", "Speletajs", vesels), lideru_karte("+/-", Lp, "PM", "Speletajs", ar_zimi),
                        lideru_karte("Metieni vārtos", Lp, "SOG", "Speletajs", vesels), lideru_karte("Vairākuma vārti", Lp, "PPG", "Speletajs", vesels),
                        lideru_karte("Sitieni", Lp, "HIT", "Speletajs", vesels), lideru_karte("Bloķētie metieni", Lp, "BLK", "Speletajs", vesels),
                        lideru_karte("Laiks laukumā (vidēji)", Lp, "TOI", "Speletajs", toi_t), lideru_karte("Sodu minūtes", Lp, "PIM", "Speletajs", vesels)]
            st.markdown('<p class="ld-h">Laukuma spēlētāji</p><div class="kpi-grid">' + "".join(x for x in kartes_p if x) + "</div>", unsafe_allow_html=True)
            if not Lg.empty:
                min_v = 1 if Lg["GP"].max() < 3 else 2                         # atvairīto % un GAA: vārtsargi ar vismaz 2 spēlēm (sezonas sākumā 1)
                kartes_g = [lideru_karte("Atvairīto metienu %", Lg, "SVpct", "Vartsargs", lambda v: f"{v:.1f}%", True, min_v),
                            lideru_karte("Ielaisti vidēji (GAA)", Lg, "GAA", "Vartsargs", lambda v: f"{v:.2f}", False, min_v),
                            lideru_karte("Win", Lg, "W", "Vartsargs", vesels),
                            lideru_karte("Atvairītie metieni", Lg, "SV", "Vartsargs", vesels)]
                st.markdown('<p class="ld-h">Vārtsargi</p><div class="kpi-grid">' + "".join(x for x in kartes_g if x) + "</div>", unsafe_allow_html=True)

    with t_par:                                           # komandas informācija
        lok = (lokacijas.LOKACIJAS.get(kom, {}) if lokacijas is not None else {})
        konf, div = KOMANDU_DIVIZIJAS.get(kom, ("", ""))
        tz_t = ""
        if lok.get("tz"):
            try:
                from zoneinfo import ZoneInfo
                tagad_ = datetime.datetime.now(datetime.timezone.utc)
                st_ = (tagad_.astimezone(ZoneInfo(lok["tz"])).utcoffset() - tagad_.astimezone(da.LV_TZ).utcoffset()).total_seconds() / 3600
                tz_t = f"{st_:+g} h pret Rīgu"
            except Exception:
                pass
        km = da.kopsavilkums(tdf, "Mājās").iloc[0] if not tdf[tdf["majas"] == 1].empty else None
        kv = da.kopsavilkums(tdf, "Izbraukumā").iloc[0] if not tdf[tdf["majas"] == 0].empty else None
        bil = lambda k: f"{int(k['W'])}-{int(k['L'])}-{int(k['OTL'])}" if k is not None else "–"     # noqa: E731
        info = [("Nosaukums", da.pilns_nosaukums(kom)), ("Saīsinājums", kom), ("Konference", konf), ("Divīzija", div),
                ("Pilsēta", ", ".join(x for x in (lok.get("pilseta"), lok.get("valsts")) if x)), ("Arēna", lok.get("arena", "")),
                ("Laika josla", tz_t), ("Sezonā aizvadītas", f"{int(kop['GP'])} spēles"),
                ("Bilance mājās", bil(km)), ("Bilance viesos", bil(kv))]
        st.markdown('<div class="ki">' + "".join(f'<div class="ki-r"><span>{e(l)}</span><b>{e(str(v))}</b></div>' for l, v in info if v) + "</div>",
                    unsafe_allow_html=True)


    with t_sp:                                            # aizvadītās spēles: 5 → "Ielādēt vēl" (+5) → "Visas"
        with st.container(key="frinda_kom_sp"):
            vieta_sp = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="kom_sp_vieta")
        sk_key = f"kom_sp_n_{kom}_{vieta_sp}"
        n_rad = st.session_state.get(sk_key, 10)
        visas = tdf.sort_values(["datums", "game_id"]).iloc[::-1]
        if vieta_sp == "Mājās":
            visas = visas[visas["majas"] == 1]
        elif vieta_sp == "Izbraukumā":
            visas = visas[visas["majas"] == 0]
        sak = dict(zip(RAW["game_id"], RAW["sakums_lv"])) if "sakums_lv" in RAW.columns else {}
        rindas = ""
        for r in visas.head(n_rad).itertuples():
            bg = da.beigu_etikete(r.beigas)
            u = rez_kods(r.rez, r.beigas)
            s_ = sak.get(r.game_id)
            dat = dt_html(s_, r.datums)
            rindas += (f'<div class="ks-r"><span class="ks-d">{dat}</span>'
                       f'<span class="ks-o"><span class="ks-v">{"vs" if r.majas == 1 else "@"}</span><img src="{e(da.logo_url(r.pretinieks))}" alt="">{e(da.pilns_nosaukums(r.pretinieks))}</span>'
                       f'<a class="ks-s" href="{e(speles_saite(r.game_id))}" target="_blank" rel="noopener" title="Atvērt spēles protokolu">{int(r.g_tot)}:{int(r.z_tot)}{(" " + bg) if bg else ""}</a>'
                       f'<span class="ks-z">{rez_zime(u)}</span>'
                       f'<span class="ks-m">metieni {int(r.sog_tot) if pd.notna(r.sog_tot) else "–"}:{int(r.sog_pret) if pd.notna(r.sog_pret) else "–"}</span></div>')
        st.markdown(f'<div class="ks">{rindas}</div><div class="ks-c">Parādītas {min(n_rad, len(visas))} no {len(visas)} spēlēm</div>', unsafe_allow_html=True)
        if n_rad < len(visas):
            with st.container(key="pgr_kom_sp"):
                st.button("Ielādēt vēl", key=f"kom_sp_vel_{kom}", on_click=lambda: st.session_state.__setitem__(sk_key, n_rad + 10))
                if n_rad > 10:
                    st.button("Visas", key=f"kom_sp_visas_{kom}", on_click=lambda: st.session_state.__setitem__(sk_key, len(visas)))

    with t_nak:                                           # nākamās spēles: tīrs saraksts (pretinieks = saite uz salīdzinājumu)
        nak = da.nakamas_speles(KAL, 10, komanda=kom) if KAL is not None else None
        if nak is not None and not nak.empty:
            rn = ""
            for s_ in nak.itertuples():
                maj = s_.majas_komanda == kom
                pret = s_.viesu_komanda if maj else s_.majas_komanda
                href_ = e(iekseja_saite("compare", a=s_.majas_komanda, b=s_.viesu_komanda))
                lok_ = lokacijas.LOKACIJAS.get(s_.majas_komanda, {}) if lokacijas is not None else {}      # spēles vieta = mājinieku arēna
                rn += (f'<div class="ks-r"><span class="ks-d">{dt_html(s_.sakums_lv, s_.datums_lv)}</span>'
                       f'<a class="ks-o kn-a" href="{href_}" target="_blank" rel="noopener" title="Salīdzināt komandas"><span class="ks-v">{"vs" if maj else "@"}</span>'
                       f'<img src="{e(da.logo_url(pret))}" alt="">{e(da.pilns_nosaukums(pret))}</a>'
                       f'<span class="ks-vieta">{e(", ".join(x for x in (lok_.get("arena"), lok_.get("pilseta")) if x))}</span></div>')
            st.markdown(f'<div class="ks">{rn}</div>', unsafe_allow_html=True)
        else:
            st.info("Kalendārā nav atrastu nākamo spēļu.")

    with t_dz:                                            # padziļinātā statistika: visa pieejamā informācija tabulā ar atlasēm
        with st.container(key="frinda_kdz"):
            scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="kdz_s")
            logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="kdz_n")
        n = LOGI[logs]
        L = da.kopsavilkums(DF, scope, n)
        sub_ = da.filtret(DF, scope, n)
        extra = sub_.groupby("komanda")[["hits", "blocked", "giveaways", "takeaways", "fo_pct"]].mean() if not sub_.empty else pd.DataFrame()
        L = L.join(extra, how="left") if not L.empty else L
        if L.empty or kom not in L.index:
            st.info("Šim skatam datu nav.")
        else:
            nL = len(L)
            st.markdown(f'<div class="dz-leg">Komandas vērtība · līgas vidējais · vieta starp {nL} komandām '
                        f'(<span class="kpi-r ok">zaļa</span> = labākā ceturtdaļa, <span class="kpi-r slikti">sarkana</span> = sliktākā)</div>',
                        unsafe_allow_html=True)
            kartes_dz = ""
            for grupa, metr in KOMANDAS_DZ_GRUPAS:
                rr = ""
                for lbl, k, dec, augsts in metr:
                    if k not in L.columns:
                        continue
                    v = L.loc[kom, k]
                    vid = L[k].mean()
                    r_ = vieta(k, augsts, L) if augsts is not None else None
                    kl = "" if r_ is None else ("ok" if r_ <= nL // 4 else ("slikti" if r_ > nL - nL // 4 else ""))
                    rr += (f'<div class="dz-r"><span class="dz-l">{e(lbl)}</span><b class="dz-v">{"–" if pd.isna(v) else _sk(v, dec)}</b>'
                           f'<span class="dz-a">{"" if pd.isna(vid) else "līgā " + _sk(vid, max(dec, 1))}</span>'
                           f'<span class="dz-p">{("<span class=" + chr(34) + "kpi-r " + kl + chr(34) + ">" + str(r_) + ".</span>") if r_ else ""}</span></div>')
                if rr:
                    kartes_dz += f'<div class="dz-k"><div class="dz-h">{e(grupa)}</div>{rr}</div>'
            st.markdown(f'<div class="dz-g">{kartes_dz}</div>', unsafe_allow_html=True)



# ============================================================================
# LAPA: INTERESANTI FAKTI (comebacks, 3. perioda karaļi) – loģika failā fakti.py
# ============================================================================
@st.cache_data(show_spinner=False)
def fakti_dati(versija, dala=None):
    v = ielasit_papildu("varti", versija)
    if fakti is None or v is None or v.empty:
        return None, None, None, None
    sp = RAW[["game_id", "datums", "home_team", "away_team", "home_total", "away_total", "spele_beidzas",
              "home_p1", "home_p2", "home_p3", "away_p1", "away_p2", "away_p3"]].dropna(subset=["home_total", "away_total"])
    gaita = fakti.spelu_gaita(sp, v)
    kops = fakti.komandu_kopsavilkums(gaita, fakti.tresa_perioda_stat(sp))
    ier = fakti.spelu_ieraksti(sp, v)
    return gaita, kops, fakti.fakti_json(sp, v, indent=2), ier


@st.cache_data(show_spinner=False)
def sausas_serijas_dati(versija, dala=None):
    v = ielasit_papildu("varti", versija)
    vg = ielasit_papildu("vartsargi", versija)
    if fakti is None or v is None or vg is None or v.empty or vg.empty:
        return []
    return fakti.sausas_serijas(vg, v)


def lapa_fakti():
    gaita, kops, js, ier = fakti_dati(VERSIJA, SEZ_DALA)
    if gaita is None:
        st.info("Šai sadaļai vajag failu fakti.py un vārtu datus (sezonas/varti.csv).")
        return
    e = _html.escape
    cb = fakti.comebacks(gaita)
    k = kops.copy()
    pv, lpv = fakti.situaciju_tabula(ier, "pirmie", "vad")
    pi, lpi = fakti.situaciju_tabula(ier, "pirmie", "iedz")
    vel_notik, vel = fakti.velie_izlidzinajumi(ier)
    min_sp = 2 if k["iedz_sp"].max() >= 3 else 1

    def pct_karte(t, nos, kontekts, min_n):
        return kom_kartes(t, "win_pct", nos, lambda v: f"{v:.0f}%", filtrs=lambda x: x["sp"] >= min_n,
                          piez_f=lambda kk: f" · {int(t.loc[kk, 'W'])} no {int(t.loc[kk, 'sp'])}",
                          tip_f=lambda kk: f"{int(t.loc[kk, 'W'])} win, {int(t.loc[kk, 'OTL'])} OT/SO loss, {int(t.loc[kk, 'L'])} loss {kontekts}")
    # --- topi: tikai dominējošās komandas katrā rādītājā ---
    kartes = [
        ("Lielākie comebacks", [(f"{da.pilns_nosaukums(r['komanda'])} pret {r['pretinieks']}", f"−{r['max_deficits']}",
                                f" · {pd.Timestamp(r['datums']):%d.%m.} · {r['gala'].replace(':', '–')}{' ' + r['beigas'] if r['beigas'] != 'REG' else ''}",
                                komandas_logo_foto(r["komanda"]) if i_ == 0 else "",
                                f"Uzvara pēc {r['max_deficits']} vārtu deficīta ({r['deficita_brids'][0]}. periodā {r['deficita_brids'][1]})")
                               for i_, r in enumerate(cb[:10])]),
        pct_karte(pv, "Iemet pirmie → win %", "spēlēs, kurās guva pirmos vārtus", min_sp),
        pct_karte(pi, "Ielaiž pirmie → win %", "spēlēs, kurās ielaida pirmos vārtus", min_sp),
        kom_kartes(k, "iedz_pct", "3. perioda karaļi (win %)", lambda v: f"{v:.0f}%", filtrs=lambda x: x["iedz_sp"] >= min_sp,
                   piez_f=lambda kk: f" · {int(k.loc[kk, 'iedz_W'])} no {int(k.loc[kk, 'iedz_sp'])}",
                   tip_f=lambda kk: f"{int(k.loc[kk, 'iedz_W'])} win no {int(k.loc[kk, 'iedz_sp'])} spēlēm, kurās pēc 2. perioda bija iedzinējos"),
        kom_kartes(k, "vad_pct", "Noturīgākie līderi (win %)", lambda v: f"{v:.0f}%", filtrs=lambda x: x["vad_sp"] >= min_sp,
                   piez_f=lambda kk: f" · {int(k.loc[kk, 'vad_W'])} no {int(k.loc[kk, 'vad_sp'])}",
                   tip_f=lambda kk: f"{int(k.loc[kk, 'vad_W'])} win no {int(k.loc[kk, 'vad_sp'])} spēlēm, kurās pēc 2. perioda vadīja"),
        kom_kartes(vel, "izlidzinaja", "Izlīdzinājumi beigās", lambda v: f"{int(v)}", filtrs=lambda x: x["izlidzinaja"] > 0,
                   piez_f=lambda kk: f" · {int(vel.loc[kk, 'izl_W'])} no tām win"),
        kom_kartes(k, "comebacks", "Visvairāk comebacks", lambda v: f"{int(v)}", filtrs=lambda x: x["comebacks"] > 0,
                   piez_f=lambda kk: f" · lielākais −{int(k.loc[kk, 'lielakais_cb'])}"),
        kom_kartes(k, "izlaistas_vadibas", "Izlaistas 2+ vārtu vadības", lambda v: f"{int(v)}", filtrs=lambda x: x["izlaistas_vadibas"] > 0),
    ]
    st.markdown('<p class="ld-h">Topi</p>' + top_kartes_html(kartes), unsafe_allow_html=True)

    # --- situāciju pārlūks: izvēlies, ko tieši skatīties ---
    st.markdown('<p class="ld-h">Situācijas</p>', unsafe_allow_html=True)
    with st.container(key="frinda_fk"):
        brids = izvele("Brīdis", ["Pirmie vārti", "Pēc 1. perioda", "Pēc 2. perioda", "Izlīdzinājumi beigās"], key="fk_br")
        stav, starp = None, None
        if brids == "Pirmie vārti":
            stav = {"Iemet pirmie": "vad", "Ielaiž pirmie": "iedz"}[izvele("Kurš guva pirmos", ["Iemet pirmie", "Ielaiž pirmie"], key="fk_pv")]
        elif brids in ("Pēc 1. perioda", "Pēc 2. perioda"):
            stav = {"Vadībā": "vad", "Iedzinējos": "iedz", "Neizšķirts": "neizs"}[izvele("Stāvoklis", ["Vadībā", "Iedzinējos", "Neizšķirts"], key="fk_st")]
            if stav != "neizs":
                starp = {"1 vārts": 1, "2 vārti": 2, "3+ vārti": 3}.get(
                    sledzis("Starpība", ["1 vārts", "2 vārti", "3+ vārti"], "Jebkura", key="fk_sp"))
    if brids == "Izlīdzinājumi beigās":
        t = vel[vel["izlidzinaja"] + vel["pret_izlidzinaja"] > 0]
        st.markdown(f'<div class="fk-liga">Izlīdzinājumi 3. perioda pēdējās 2 minūtēs: kopā {len(vel_notik)} '
                    f'(no tām {sum(1 for r in vel_notik if r["iznakums"] == "W")} beidzās ar win)</div>', unsafe_allow_html=True)
        if not t.empty:
            tabula(t, {"izlidzinaja": "Izlīdzināja", "izl_W": "No tām win", "pret_izlidzinaja": "Pret to izlīdzināja"}, sort_col="izlidzinaja",
                   paskaidr={"Izlīdzināja": "Vārti 3. perioda pēdējās 2 minūtēs, kas izlīdzināja rezultātu",
                             "No tām win": "Spēles, kuras pēc izlīdzinājuma komanda arī uzvarēja (OT/SO)",
                             "Pret to izlīdzināja": "Reizes, kad pretinieks izlīdzināja pēdējās 2 minūtēs"})
        rn = "".join(
            f'<div class="fk-r"><span class="ks-d">{dt_html(SAKUMI.get(r["game_id"]) if SAKUMI else None, r["datums"])}</span>'
            f'<span class="ks-o"><img src="{e(da.logo_url(r["komanda"]))}" alt="">{e(da.pilns_nosaukums(r["komanda"]))}'
            f'<span class="ks-v">{"vs" if r["majas"] else "@"}</span><img src="{e(da.logo_url(r["pretinieks"]))}" alt=""></span>'
            f'<span class="fk-def fk-izl" title="Izlīdzinājums 3. periodā">{e(r["laiks"])}</span>'
            f'<a class="ks-s" href="{e(speles_saite(r["game_id"]))}" target="_blank" rel="noopener">{e(r["gala"])}{(" " + r["beigas"]) if r["beigas"] != "REG" else ""}</a>'
            f'<span class="ks-z">{rez_zime(rez_kods(r["iznakums"], r["beigas"]))}</span></div>'
            for r in vel_notik)
        if rn:
            st.markdown(f'<div class="ks">{rn}</div>', unsafe_allow_html=True)
    else:
        br_kods = {"Pirmie vārti": "pirmie", "Pēc 1. perioda": "p1", "Pēc 2. perioda": "p2"}[brids]
        t, liga = fakti.situaciju_tabula(ier, br_kods, stav, starp)
        t = t[t["sp"] > 0]
        starp_t = ""
        if starp:
            starp_t = " ar " + str(starp) + ("+" if starp == 3 else "") + " vārtu"
        if br_kods == "pirmie":
            apr = {"vad": "guva pirmos vārtus", "iedz": "ielaida pirmos vārtus"}
        else:
            apr = {"vad": brids.lower() + " vadīja" + (starp_t + " pārsvaru" if starp_t else ""),
                   "iedz": brids.lower() + " bija iedzinējos" + (starp_t + " deficītu" if starp_t else ""),
                   "neizs": brids.lower() + " bija neizšķirts"}
        apraksts = apr[stav]
        if t.empty:
            st.info("Šādā situācijā vēl nav nevienas spēles.")
        else:
            st.markdown(f'<div class="fk-liga">Spēles, kurās komanda {e(apraksts)}: kopā {int(t["sp"].sum())} · '
                        f'līgā vidēji <b>{liga:.0f}%</b> win</div>', unsafe_allow_html=True)
            tabula(t, {"sp": "Sp.", "W": "W", "L": "L", "OTL": "OTL", "win_pct": "Win %", "pts_pct": "Punkti %"}, sort_col="win_pct",
                   prog={"win_pct": (0, 100), "pts_pct": (0, 100)}, formati={"win_pct": "{:.0f}", "pts_pct": "{:.0f}"},
                   paskaidr={"Sp.": f"Spēles, kurās komanda {apraksts}", "W": "win (arī OT win un SO win)", "L": "loss",
                             "OTL": "OT loss vai SO loss", "Win %": "Uzvaru daļa šajās spēlēs", "Punkti %": "Izcīnīto punktu daļa (win 2, OT/SO loss 1)"})

    # --- comebacks: atverams saraksts ar visām spēlēm un atlasi pēc komandas ---
    if cb:
        with st.expander(f"Comebacks · {len(cb)} {'spēle' if len(cb) == 1 else 'spēles'} (uzvara pēc ≥ {fakti.MIN_DEFICITS} vārtu deficīta)"):
            skaits = pd.Series([r["komanda"] for r in cb]).value_counts()
            opc = ["Visas komandas"] + sorted(skaits.index, key=lambda kk: da.pilns_nosaukums(kk))
            izv_kom = st.selectbox("Komanda", opc, key="fk_cb_kom",
                                   format_func=lambda kk: kk if kk == "Visas komandas" else f"{da.pilns_nosaukums(kk)} ({int(skaits[kk])})")
            rindas_cb = cb if izv_kom == "Visas komandas" else [r for r in cb if r["komanda"] == izv_kom]
            rindas_cb = sorted(rindas_cb, key=lambda r: (r["datums"], r["game_id"]), reverse=True)    # secīgi pēc notikuma laika (jaunākās vispirms)
            # lapošana pa 10 spēlēm; mainot komandu, sāk no 1. lapas
            if st.session_state.get("fk_cb_pedeja_kom") != izv_kom:
                st.session_state["fk_cb_pedeja_kom"] = izv_kom
                st.session_state["fk_cb_lapa"] = 1
            lapas_n = max(1, -(-len(rindas_cb) // CB_LAPA))
            lapa = min(max(1, st.session_state.get("fk_cb_lapa", 1)), lapas_n)
            rn = ""
            for r in rindas_cb[(lapa - 1) * CB_LAPA: lapa * CB_LAPA]:
                kom, pret = r["komanda"], r["pretinieks"]
                h_, a_ = r["gala"].split(":")
                savi, pretv = (h_, a_) if r["majas"] else (a_, h_)
                db = r["deficita_rezultats"].split(":") if r["deficita_rezultats"] else ["", ""]
                d_savi, d_pret = (db[0], db[1]) if r["majas"] else (db[1], db[0])
                rn += (f'<div class="fk-r"><span class="ks-d">{dt_html(SAKUMI.get(r["game_id"]) if SAKUMI else None, r["datums"])}</span>'
                       f'<span class="ks-o"><img src="{e(da.logo_url(kom))}" alt="">{e(da.pilns_nosaukums(kom))}'
                       f'<span class="ks-v">{"vs" if r["majas"] else "@"}</span><img src="{e(da.logo_url(pret))}" alt="" title="{e(da.pilns_nosaukums(pret))}"></span>'
                       f'<span class="fk-def" title="Lielākais deficīts: {d_savi}:{d_pret}, {r["deficita_brids"][0]}. periodā {r["deficita_brids"][1]}">−{r["max_deficits"]}</span>'
                       f'<a class="ks-s" href="{e(speles_saite(r["game_id"]))}" target="_blank" rel="noopener">{savi}:{pretv}{(" " + r["beigas"]) if r["beigas"] != "REG" else ""}</a>'
                       f'<span class="ks-z">{rez_zime(fakti_rez_kods(r))}</span></div>')
            st.markdown(f'<div class="ks">{rn}</div>', unsafe_allow_html=True)
            if lapas_n > 1:
                st.markdown(f'<div class="fk-liga">Lapa {lapa} no {lapas_n} · spēles {(lapa - 1) * CB_LAPA + 1}–{min(lapa * CB_LAPA, len(rindas_cb))} no {len(rindas_cb)}</div>',
                            unsafe_allow_html=True)
                with st.container(key="pgr_fk_cb"):
                    for nr in range(1, lapas_n + 1):
                        st.button(str(nr), key=f"fk_cb_l{nr}", type="primary" if nr == lapa else "secondary",
                                  on_click=lambda n_=nr: st.session_state.__setitem__("fk_cb_lapa", n_))

    # --- SHUTOUT: vārtsargu sausās sērijas ≥ 120 min (aktīvās; pārtrauktā paliek līdz vārtsarga nākamajai spēlei) ---
    ser = sausas_serijas_dati(VERSIJA, SEZ_DALA)
    akt_n = sum(1 for x in ser if x["aktiva"])
    with st.expander(f"SHUTOUT · {akt_n} {'aktīva sērija' if akt_n == 1 else 'aktīvas sērijas'} (vārtsargs bez ielaistiem vārtiem ≥ 120 min)"):
        if not ser:
            st.markdown('<div class="fk-liga">Pašlaik nevienam vārtsargam nav sausās sērijas, kas ilgāka par 120 minūtēm.</div>', unsafe_allow_html=True)
        else:
            rn = ""
            for x in ser:
                mm = f"{x['sek'] // 60}:{x['sek'] % 60:02d}"
                if x["aktiva"]:
                    stat = f'<span class="fk-ser akt" title="Sērija turpinās kopš {pd.Timestamp(x["sakums"]):%d.%m.}">{mm} min</span>'
                    pie = f"aktīva · kopš {pd.Timestamp(x['sakums']):%d.%m.}" if x.get("sakums") else "aktīva"
                else:
                    stat = f'<span class="fk-ser" title="Sērija pārtraukta">{mm} min</span>'
                    pie = f"pārtraukta {pd.Timestamp(x['partraukta']):%d.%m.} · {x['partraukta_brids']}"
                rn += (f'<div class="fk-r"><span class="ks-d">{dt_html(None, x["pedeja_spele"])}</span>'
                       f'<span class="ks-o">{spel_foto_html(x["playerId"], x["komanda"], x["vards"]).replace("ld-foto", "fk-foto")}'
                       f'{e(x["vards"])}<img src="{e(da.logo_url(x["komanda"]))}" alt="" title="{e(da.pilns_nosaukums(x["komanda"]))}"></span>'
                       f'<span class="fk-pie">{e(pie)}</span>{stat}</div>')
            st.markdown(f'<div class="ks">{rn}</div>', unsafe_allow_html=True)

    # --- izcēlumi: komandas, kas kādā rādītājā ļoti atšķiras no līgas ---
    izc = fakti.izcelumi(ier)
    st.markdown('<p class="ld-h">Izcēlumi</p>', unsafe_allow_html=True)
    if izc:
        st.markdown('<div class="fk-izc">' + "".join(
            f'<div class="fk-iz {"aug" if x["augstak"] else "zem"}"><img src="{e(da.logo_url(x["komanda"]))}" alt="">'
            f'<div><b>{e(da.pilns_nosaukums(x["komanda"]))}</b><span>{e(x["teksts"])}</span></div></div>' for x in izc) + "</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fk-liga">Pagaidām neviena komanda būtiski neizceļas. Izcēlumam vajag vismaz {fakti.IZCELUMA_MIN_SP} spēles situācijā '
                    f'un vismaz {int(fakti.IZCELUMA_MIN_STARP * 100)} procentpunktu atšķirību no līgas vidējā.</div>', unsafe_allow_html=True)
    st.download_button("Lejupielādēt datus (JSON)", data=js, file_name="nhl_fakti.json", mime="application/json", key="fakti_json")


CB_LAPA = 10        # comebacks sarakstā spēles vienā lapā


def fakti_rez_kods(r):
    return {"REG": "W", "OT": "OTW", "SO": "SOW"}.get(r["beigas"], "W")


# ============================================================================
# LAPAS: MAZĀKUMS UN OT / SO
# ============================================================================
def _apakskopa_pari(scope, n):
    """(game_id, komanda) pāri, kas ietilpst izvēlētajā atlasē (mājās/viesos, pēdējās N)."""
    sub_ = da.filtret(DF, scope, n)
    return set(zip(sub_["game_id"], sub_["komanda"])), sub_


def _varti_df():
    v = ielasit_papildu("varti", VERSIJA)
    return v if v is not None and not v.empty else None


def top_kartes_html(kartes, top=10):
    """
    Topu kartītes (kā Spēlētāju statistikā): līderis ar foto/logo, 2.–3. vieta un “Rādīt top 10”.
    kartes: [(nosaukums, [(vārds, vērtība_teksts, piezīme, foto_html)])] – foto_html līderim (var būt "").
    """
    e = _html.escape
    out = ""
    for nos, saraksts in kartes:
        if not saraksts:
            continue
        v0 = saraksts[0]
        def tip_(r):                                     # papildinformācija, uzvedot uz vērtības (piem., 12/13 izturēti)
            return f' class="ld-tip" data-tip="{e(r[4])}" title="{e(r[4])}" tabindex="0"' if len(r) > 4 and r[4] else ""
        rinda_ = lambda n, r: f'<div class="ld-c"><span>{n}. {e(r[0])}</span><b{tip_(r)}>{e(r[1])}</b></div>'   # noqa: E731
        citi = "".join(rinda_(i + 2, r) for i, r in enumerate(saraksts[1:3]))
        vel = "".join(rinda_(i + 4, r) for i, r in enumerate(saraksts[3:top]))
        izv = (f'<details class="ld-x"><summary><span class="ld-a">Rādīt top {top} ▾</span><span class="ld-z">Paslēpt ▴</span></summary>{vel}</details>'
               if vel else "")
        foto = v0[3] if len(v0) > 3 else ""
        out += (f'<div class="kpi ld-k"><div class="ld-top">{foto}<div class="kpi-l">{e(nos)}</div><div class="kpi-v">{e(v0[1])}</div>'
                f'<div class="ld-v">{e(v0[0])}<span>{e(v0[2])}</span></div></div>{citi}{izv}</div>')
    return f'<div class="kpi-grid">{out}</div>' if out else ""


def komandas_logo_foto(kods):
    """Komandas logo apaļajā līdera vietā (komandu topiem)."""
    return (f'<div class="ld-foto ld-logo" role="img" aria-label="{_html.escape(kods)}">'
            f'<img class="ld-logo-img" src="{_html.escape(da.logo_url(kods))}" alt=""></div>')


def spelētaju_situacijas_topi(stiprums, pari, perioda_tips="REG", top=10):
    """
    Spēlētāju topi no vārtu datiem (vārti, piespēles, punkti) noteiktā situācijā: "pp" vairākums, "sh" mazākums, None = jebkura.
    perioda_tips "REG" (pamatlaiks) vai "OT". Atgriež DataFrame: playerId, vards, komanda, G, A, P.
    """
    v = _varti_df()
    if v is None:
        return pd.DataFrame()
    m = (v["period_type"].astype(str).str.upper() == perioda_tips)
    if stiprums:
        m &= v["strength"].astype(str).str.lower() == stiprums
    m &= pd.Series([(gi, kk) in pari for gi, kk in zip(v["game_id"], v["komanda"])], index=v.index)
    x = v[m]
    if x.empty:
        return pd.DataFrame()
    ier = pd.concat([x[["scorer_id", "scorer", "komanda"]].set_axis(["pid", "vards", "komanda"], axis=1).assign(G=1, A=0),
                     x[["assist1_id", "assist1", "komanda"]].set_axis(["pid", "vards", "komanda"], axis=1).assign(G=0, A=1),
                     x[["assist2_id", "assist2", "komanda"]].set_axis(["pid", "vards", "komanda"], axis=1).assign(G=0, A=1)])
    ier = ier[ier["pid"].notna() & (ier["vards"].astype(str) != "")]
    if ier.empty:
        return pd.DataFrame()
    t = ier.groupby(["pid", "komanda"]).agg(vards=("vards", "last"), G=("G", "sum"), A=("A", "sum")).reset_index()
    t["P"] = t["G"] + t["A"]
    sk_ = ielasit_papildu("speletaji", VERSIJA)              # pilni vārdi no spēlētāju datiem
    if sk_ is not None and not sk_.empty:
        pilni = sk_.drop_duplicates("playerId", keep="last").set_index("playerId")["vards"]
        t["vards"] = [pilni.get(int(pid), v_) if pd.notna(pid) else v_ for pid, v_ in zip(t["pid"], t["vards"])]
    return t


def spel_kartes(t, kol, nos, piez_f=lambda r: "", top=10):
    """Viena topa kartīte no spēlētāju tabulas: [(vārds (komanda), vērtība, piezīme, foto)]."""
    if t is None or t.empty or kol not in t.columns:
        return (nos, [])
    t = t[t[kol] > 0].sort_values([kol, "P"], ascending=False).head(top)
    rindas = []
    for n, r in enumerate(t.itertuples()):
        rindas.append((f"{r.vards} ({r.komanda})", f"{int(getattr(r, kol))}", piez_f(r), spel_foto_html(r.pid, r.komanda, r.vards) if n == 0 else ""))
    return (nos, rindas)


def kom_kartes(g, kol, nos, fmt, piez_f=lambda k: "", aug=True, top=10, filtrs=None, tip_f=None):
    """Viena topa kartīte no komandu tabulas (līderim logo). tip_f(k): paskaidrojums uz vērtības visām vietām (piem., procentiem)."""
    if g is None or g.empty or kol not in g.columns:
        return (nos, [])
    x = g if filtrs is None else g[filtrs(g)]
    x = x[x[kol].notna()].sort_values(kol, ascending=not aug).head(top)
    return (nos, [(da.pilns_nosaukums(k), fmt(v), piez_f(k), komandas_logo_foto(k) if n == 0 else "", tip_f(k) if tip_f else "")
                  for n, (k, v) in enumerate(x[kol].items())])


def otso_kopsavilkums(scope="Visas", n=None):
    """Papildlaika (OT) un pēcspēles metienu (SO) statistika katrai komandai izvēlētajā atlasē."""
    pari, sub_ = _apakskopa_pari(scope, n)
    if sub_.empty:
        return pd.DataFrame()
    r = RAW.set_index("game_id")
    def no_raw(row, kol):
        if row.game_id not in r.index:
            return np.nan
        g = r.loc[row.game_id]
        if isinstance(g, pd.DataFrame):
            g = g.iloc[0]
        puse, pret = ("home", "away") if row.majas == 1 else ("away", "home")
        return g.get(f"{puse}_{kol}"), g.get(f"{pret}_{kol}")
    x = sub_.copy()
    vals = [no_raw(row, "ot") for row in x.itertuples()]
    x["g_ot"] = [v[0] if isinstance(v, tuple) else np.nan for v in vals]
    x["z_ot"] = [v[1] if isinstance(v, tuple) else np.nan for v in vals]
    vals = [no_raw(row, "sog_ot") for row in x.itertuples()]
    x["s_ot"] = [v[0] if isinstance(v, tuple) else np.nan for v in vals]
    x["sa_ot"] = [v[1] if isinstance(v, tuple) else np.nan for v in vals]
    b = x["beigas"].astype(str).str.upper()
    x = x.assign(otg=b.isin(["OT", "SO"]).astype(int), ot_w=((x["rez"] == "W") & (b == "OT")).astype(int),
                 ot_l=((x["rez"] != "W") & (b == "OT")).astype(int), so_w=((x["rez"] == "W") & (b == "SO")).astype(int),
                 so_l=((x["rez"] != "W") & (b == "SO")).astype(int))
    ot = x[b.isin(["OT", "SO"])]
    g = x.groupby("komanda").agg(GP=("game_id", "count"), OTG=("otg", "sum"), OT_W=("ot_w", "sum"), OT_L=("ot_l", "sum"),
                                 SO_W=("so_w", "sum"), SO_L=("so_l", "sum"))
    g2 = ot.groupby("komanda").agg(G_OT=("g_ot", "sum"), Z_OT=("z_ot", "sum"), S_OT=("s_ot", "sum"), SA_OT=("sa_ot", "sum"))
    g = g.join(g2, how="left").fillna({"G_OT": 0, "Z_OT": 0, "S_OT": 0, "SA_OT": 0})
    g["W_kopa"] = g["OT_W"] + g["SO_W"]
    g["L_kopa"] = g["OT_L"] + g["SO_L"]
    g["OT_pct"] = g["OTG"] / g["GP"] * 100
    g["W_pct"] = (g["W_kopa"] / g["OTG"] * 100).where(g["OTG"] > 0)
    g["OT_bil"] = g["OT_W"].astype(int).astype(str) + "-" + g["OT_L"].astype(int).astype(str)
    g["SO_bil"] = g["SO_W"].astype(int).astype(str) + "-" + g["SO_L"].astype(int).astype(str)
    g["Kopa_bil"] = g["W_kopa"].astype(int).astype(str) + "-" + g["L_kopa"].astype(int).astype(str)
    return g


def lapa_otso():
    st.title("OT / SO")
    augsa = st.container()                                 # topi (aizpildās pēc filtru nolasīšanas, bet tiek rādīti virs tiem)
    with st.container(key="frinda_otso"):
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="otso_s")
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="otso_n")
    n = LOGI[logs]
    g = otso_kopsavilkums(scope, n)
    if g.empty:
        st.info("Šim skatam datu nav.")
        return
    # topi (komandas ar logo, spēlētāji ar foto)
    kartes = [kom_kartes(g, "W_kopa", "OT win + SO win", lambda v: f"{int(v)}", lambda k: f" · bilance {g.loc[k, 'Kopa_bil']}"),
              kom_kartes(g, "OTG", "Visbiežāk līdz papildlaikam", lambda v: f"{int(v)}", lambda k: f" · {g.loc[k, 'OT_pct']:.0f}% spēļu"),
              kom_kartes(g, "W_pct", "Win % OT/SO", lambda v: f"{v:.0f}%", lambda k: f" · {int(g.loc[k, 'OTG'])} sp.", filtrs=lambda x: x["OTG"] > 0,
                         tip_f=lambda k: f"{int(g.loc[k, 'W_kopa'])} win no {int(g.loc[k, 'OTG'])} spēlēm līdz papildlaikam")]
    pari, _ = _apakskopa_pari(scope, n)
    to = spelētaju_situacijas_topi(None, pari, "OT")
    kartes += [spel_kartes(to, "G", "Vārti papildlaikā"), spel_kartes(to, "P", "Punkti papildlaikā")]
    with augsa:
        st.markdown('<p class="ld-h">Topi</p>' + top_kartes_html(kartes), unsafe_allow_html=True)
    tabula(g, {"GP": "Sp.", "OTG": "Līdz papildl.", "OT_pct": "Papildl. %", "OT_bil": "OT W-L", "SO_bil": "SO W-L", "Kopa_bil": "Kopā W-L",
               "W_pct": "Win %", "G_OT": "Gūti OT", "Z_OT": "Ielaisti OT", "S_OT": "Metieni OT", "SA_OT": "Pret. metieni OT"},
           sort_col="W_kopa",
           config={"Papildl. %": st.column_config.NumberColumn(format="%.0f"), "Win %": st.column_config.NumberColumn(format="%.0f")},
           paskaidr={"Līdz papildl.": "Spēles, kas pēc pamatlaika bija neizšķirtas (papildlaiks un/vai metienu sērija)",
                     "Papildl. %": "Cik % spēļu aizgāja līdz papildlaikam", "OT W-L": "OT win – OT loss (spēles, kas izšķīrās papildlaikā)",
                     "SO W-L": "SO win – SO loss (pēcspēles metienu sērijas)", "Kopā W-L": "(OT win + SO win) – (OT loss + SO loss)",
                     "Win %": "OT win un SO win daļa spēlēs, kas aizgāja līdz papildlaikam", "Gūti OT": "Papildlaikā gūtie vārti",
                     "Ielaisti OT": "Papildlaikā ielaistie vārti", "Metieni OT": "Metieni vārtos papildlaikā", "Pret. metieni OT": "Pretinieka metieni papildlaikā"})


def lapa_mazakums():
    st.title("Mazākums")
    augsa = st.container()
    with st.container(key="frinda_mz"):
        scope = sledzis("Spēles", ["Mājās", "Izbraukumā"], "Visas", key="mz_s")
        logs = sledzis("Laika posms", ["Pēdējās 5", "Pēdējās 10"], "Visa sezona", key="mz_n")
    n = LOGI[logs]
    res = da.kopsavilkums(DF, scope, n)
    if res.empty:
        st.info("Šim skatam datu nav.")
        return
    pari, _ = _apakskopa_pari(scope, n)
    v = _varti_df()
    sh = pd.DataFrame()
    if v is not None:
        sh = v[(v["strength"].astype(str).str.lower() == "sh") & (v["period_type"].astype(str).str.upper() == "REG")
               & pd.Series([(gi, kk) in pari for gi, kk in zip(v["game_id"], v["komanda"])], index=v.index)]
    res["SHG"] = sh.groupby("komanda").size() if not sh.empty else 0
    res["SHG"] = res["SHG"].fillna(0)
    res["PK_nosargati"] = res["PP_opp_pret"] - res["PPG_pret"]
    kol = {"PP_opp_pret": "Mazākuma reizes", "PK_nosargati": "Nosargāti", "PPG_pret": "Ielaisti",
           "SHG": "Gūti mazākumā", "PEN_sp": "Noraid/v.", "PK_pct": "PK %"}
    cfg = {"PK %": st.column_config.NumberColumn(format="%.1f"), "Noraid/v.": st.column_config.NumberColumn(format="%.1f")}
    pask = {"PK %": "Nosargāto mazākumu daļa (pamatlaikā)", "Mazākuma reizes": "Cik reizes komanda spēlēja mazākumā (pamatlaikā)",
            "Nosargāti": "Mazākumi bez ielaistiem vārtiem", "Ielaisti": "Mazākumā ielaistie vārti", "Gūti mazākumā": "Mazākumā gūtie vārti (pamatlaikā)",
            "Noraid/v.": "Vidēji saņemtie noraidījumi spēlē (pamatlaikā)"}
    tsh = spelētaju_situacijas_topi("sh", pari)
    kartes = [kom_kartes(res, "PK_pct", "PK % (komandas)", lambda v: f"{v:.1f}%", lambda k: f" · {int(res.loc[k, 'PK_nosargati'])}/{int(res.loc[k, 'PP_opp_pret'])}",
                         filtrs=lambda x: x["PP_opp_pret"] > 0,
                         tip_f=lambda k: f"{int(res.loc[k, 'PK_nosargati'])} no {int(res.loc[k, 'PP_opp_pret'])} mazākumiem izturēti"),
              kom_kartes(res, "SHG", "Gūti mazākumā (komandas)", lambda v: f"{int(v)}", filtrs=lambda x: x["SHG"] > 0),
              spel_kartes(tsh, "P", "Punkti mazākumā", lambda r: f" · {int(r.G)} v. + {int(r.A)} p."),
              spel_kartes(tsh, "G", "Vārti mazākumā")]
    with augsa:
        st.markdown('<p class="ld-h">Topi</p>' + top_kartes_html(kartes), unsafe_allow_html=True)
    tabula(res, kol, sort_col="PK_pct", config=cfg, paskaidr=pask)


# ============================================================================
# LAPA: KALENDĀRS
# ============================================================================
def lapa_kalendars():
    st.title("Spēļu kalendārs")
    if KAL is None:
        st.warning("Kalendāra fails 'sezonas/nhl_kalendars.csv' nav atrasts (palaid kalendars.py).")
        return
    try:
        _ts = _planotie_ar_statusu(VERSIJA)[1]
        _parb = _ts["lidz"] - timedelta(hours=30)                                                # pārbaudes brīdis
        st.caption(f"Tiesneši pārbaudīti {_parb:%d.%m. %H:%M}"
                   + (f" · ⚠️ {_ts['kluda']}" if _ts.get("kluda") else "")
                   + f". Nākamā pārbaude: {_ts['nakama']}.")
    except Exception:
        pass
    c1, _ = st.columns([1, 2])
    dienas = c1.slider("Cik dienas uz priekšu", 1, 14, 5)
    sodien = da.sodien_lv()
    d = KAL["datums_lv"].dt.date
    x = KAL[(d >= sodien) & (d <= sodien + timedelta(days=dienas))]
    x = x[x["sakums_lv"] > pd.Timestamp.now(tz=da.LV_TZ) - pd.Timedelta(hours=2, minutes=30)]      # 2 h 30 min pēc sākuma spēle pazūd
    if x.empty:
        st.info("Šajā periodā spēļu nav.")
        return
    for n_dienas, (dat, grupa) in enumerate(x.groupby(x["datums_lv"].dt.date)):
        with st.container(border=True, key=f"rmb_kal_{dat:%Y%m%d}"):
            st.markdown(f"**{da.DIENAS[dat.weekday()]}, {dat:%d.%m.%Y}** · {len(grupa)} spēles")
            plan = ielasit_planotos(VERSIJA)
            ties_txt = []
            for gid in grupa["game_id"]:
                vardi = da.planotie_vardi(plan, gid)
                ties_txt.append(", ".join(vardi) if vardi else "Tiesneši nav paziņoti")
            tab = pd.DataFrame({
                "Laiks (Rīga)": grupa["sakums_lv"].dt.strftime("%H:%M"),
                "Viesi": grupa["viesu_komanda"].map(komandas_etikete),
                "Mājinieki": grupa["majas_komanda"].map(komandas_etikete),
                "Galvenie tiesneši": ties_txt})
            if n_dienas < 2:                                   # pirmās divas redzamās dienas: pogas uz komandu salīdzinājumu virs tabulas (mājinieki pa kreisi)
                salid = None
                with st.container(key=f"pg_kal_salid{n_dienas}"):
                    st.markdown('<div class="pg-lab">⇄ Salīdzināt komandas</div>', unsafe_allow_html=True)
                    with st.container(key=f"pgr_kal_salid{n_dienas}"):
                        for h, v, g_ in zip(grupa["majas_komanda"], grupa["viesu_komanda"], grupa["game_id"]):
                            if st.button(f"⇄ {v} @ {h}", key=f"kals_{g_}", help=None if mobila_ierice() else f"Salīdzināt komandas: {da.pilns_nosaukums(v)} @ {da.pilns_nosaukums(h)}"):
                                salid = (h, v)
                if salid and _lapa_pec_nosaukuma("Salīdzināt komandas") is not None:
                    _sl_salidzinat(*salid)
                    st.switch_page(_lapa_pec_nosaukuma("Salīdzināt komandas"))
            rtabula_bez_kartosanas(tab, hide_index=True, width="stretch")


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


def rez_kartite_html(away, home, at, ht, ra, rh, iznakums, linijas, uid="g", detalas_html=None, atverts=False, info=None):
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
    sakums = (f'<div class="mc-box"><input type="checkbox" class="mc-tg" id="det_{uid}"{" checked" if atverts else ""}>' if detalas_html is not None else "")
    beigas = (f'<div class="mc-det">{detalas_html}</div></div>' if detalas_html is not None else "")
    return (
        sakums
        + '<div class="mc">'
        f'<div class="mc-team mc-away"><span class="mc-name{" uzv-nos" if at > ht else ""}">{e(da.pilns_nosaukums(away))}</span>'
        f'<img class="mc-logo" src="{e(da.logo_url(away))}" alt="{e(away)}"></div>'
        '<div class="mc-mid">'
        f'<div class="mc-score">{_rezultata_svg(at, ht, kl_a, kl_h, "g" + str(uid))}</div>'
        + (f'<label class="mc-outcome mc-btn" for="det_{uid}" data-tip="Detaļas">{e(iznakums)}</label></div>' if detalas_html is not None
           else f'<div class="mc-outcome">{e(iznakums)}</div></div>')
        + ''
        f'<div class="mc-team mc-home"><img class="mc-logo" src="{e(da.logo_url(home))}" alt="{e(home)}">'
        f'<span class="mc-name{" uzv-nos" if ht > at else ""}">{e(da.pilns_nosaukums(home))}</span></div>'
        '</div>'
        + (f'<div class="mc-info">{e(info)}</div>' if info else "")
        + '<div class="mc-lines">' + "".join(f"<div>{e(x)}</div>" for x in linijas if x) + '</div>'
        + beigas)


# Ikdienas datu atjaunināšana (NHL Daily Update): cron-job.org 08:40 pēc Rīgas laika un GitHub rezerve 08:15 UTC (11:15 Rīgā vasaras laikā)
DATU_ATJAUNINASANA_LV = [(8, 40)]                 # cron-job.org (darba laika josla Europe/Riga)
DATU_ATJAUNINASANA_UTC = [(8, 15)]                # GitHub grafiks daily.yml: '15 8 * * *' (UTC)


def rezultatu_statuss():
    """Rinda Rezultātu lapā: kad dati atjaunināti, kuras spēles tajos ir, cik pabeigtu spēļu vēl gaida rezultātu un kad nākamā atjaunināšana."""
    lv = lambda t: t.astimezone(da.LV_TZ)                                                       # noqa: E731
    f = lambda t: t.strftime("%d.%m. %H:%M")                                                     # noqa: E731
    tagad = datetime.datetime.now(datetime.timezone.utc)
    atjaun = None                                       # tikai no veiksmīgas NHL Daily Update palaišanas (nhl_dati.py raksta šo failu)
    c = da.DATU_MAPE / "pedeja_atjaunosana.json"
    if c.exists():
        try:
            import json as _json
            atjaun = lv(pd.Timestamp(_json.loads(c.read_text(encoding="utf-8"))["utc"]).to_pydatetime())
        except Exception:
            atjaun = None
    sak = RAW["datums_lv"].dt.date
    teksts = (f"Pēdējā atjaunošana: {f(atjaun)} · " if atjaun else "") + f"Rezultāti līdz {sak.max():%d.%m.} ({len(RAW)} spēles)"
    kandidati = []                                     # nākamie ieplānotie laiki šodien un rīt (abi grafiki), agrākais pēc tagad
    for d_ in (0, 1):
        for h, m in DATU_ATJAUNINASANA_LV:
            kandidati.append((lv(tagad) + timedelta(days=d_)).replace(hour=h, minute=m, second=0, microsecond=0))
        for h, m in DATU_ATJAUNINASANA_UTC:
            kandidati.append(lv((tagad + timedelta(days=d_)).replace(hour=h, minute=m, second=0, microsecond=0)))
    nak = min(k for k in kandidati if k > lv(tagad))
    return teksts + f" · Nākošā atjaunošana: {f(nak)}."


def lapa_rezultati():
    st.title("Spēļu rezultāti")
    try:
        st.caption(rezultatu_statuss())
    except Exception:
        pass
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
    st.markdown(f"<style>.st-key-datums_lauks::after {{ content: '{dat:%d.%m.%Y}'; }}</style>", unsafe_allow_html=True)
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
        with (st.container(border=True, key="rez_fokuss_kartite") if ir_fokuss else st.container(border=True, key=f"rmb_rez_{r['game_id']}")):
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
            # detaļas: atveras, nospiežot iznākuma pogu (Pamatlaiks / OT / SO) zem rezultāta
            gid = r["game_id"]
            det = []
            zv = [r.get(f"star{i}") for i in (1, 2, 3)]
            if any(isinstance(z, str) and z for z in zv):
                det.append("<p><b>Spēles zvaigznes:</b> " + " · ".join(f"{i}. {_html.escape(z)}" for i, z in enumerate(zv, 1) if isinstance(z, str) and z) + "</p>")
            if ties is not None:
                tv = ties[(ties["game_id"] == gid) & (ties["loma"] == "referee")]["vards"].tolist()
                if tv:
                    det.append("<p><b>Tiesneši:</b> " + _html.escape(", ".join(tv)) + "</p>")
            if varti is not None:
                v = varti[varti["game_id"] == gid]
                if not v.empty:
                    det.append('<p class="mc-dh">Vārti</p>' + rtabula_html(pd.DataFrame({
                        "Per.": v["period"].astype(str) + v["period_type"].map(lambda x: "" if x == "REG" else f" {x}"),
                        "Laiks": v["laiks"], "Komanda": v["komanda"], "Autors": v["scorer"],
                        "Piespēles": (v["assist1"].fillna("") + ", " + v["assist2"].fillna("")).str.strip(", "),
                        "Situācija": v["strength"].str.upper(),
                        "Rez. pēc vārtiem": v["away_score"].astype("Int64").astype(str) + "–" + v["home_score"].astype("Int64").astype(str)})))
            if sk is not None:
                s = sk[sk["game_id"] == gid].sort_values(["points", "goals", "sog"], ascending=False).head(6)
                if not s.empty:
                    det.append('<p class="mc-dh">Labākie spēlētāji</p>' + rtabula_html(s[["vards", "team", "goals", "assists", "points", "sog", "toi"]].rename(columns={
                        "vards": "Spēlētājs", "team": "Komanda", "goals": "G", "assists": "A",
                        "points": "P", "sog": "Metieni", "toi": "TOI spēlē"})))
            if vg is not None:
                g = vg[(vg["game_id"] == gid) & (vg["shotsAgainst"].fillna(0) > 0)].copy()
                if not g.empty:
                    g["SV %"] = (g["saves"] / g["shotsAgainst"] * 100).round(1)
                    det.append('<p class="mc-dh">Vārtsargi</p>' + rtabula_html(g[["vards", "team", "saves", "shotsAgainst", "SV %", "decision"]].rename(columns={
                        "vards": "Vārtsargs", "team": "Komanda", "saves": "Atvairīti",
                        "shotsAgainst": "Metieni pret", "decision": "Iznākums"})))
            info = None
            if pd.notna(r.get("sakums_lv")):
                vieta = ", ".join(x for x in (r.get("arena") if isinstance(r.get("arena"), str) else "",
                                               lokacijas.LOKACIJAS.get(home, {}).get("pilseta", "") if lokacijas is not None else "") if x)
                info = f"Sākums {r['sakums_lv']:%d.%m. %H:%M}" + (f" · {vieta}" if vieta else "")
            st.markdown(rez_kartite_html(away, home, at, ht, ra, rh, et or "Pamatlaiks", linijas, uid=gid,
                                         detalas_html="".join(det) or "<p>Detaļu vēl nav.</p>", atverts=ir_fokuss, info=info), unsafe_allow_html=True)


# ============================================================================
# LAPA: SPĒLĒTĀJI
# ============================================================================
def lapa_speletaji():  # noqa: C901
    st.title("Spēlētāji")
    sk = ielasit_papildu("speletaji", VERSIJA)
    vg = ielasit_papildu("vartsargi", VERSIJA)
    if sk is None and vg is None:
        st.info("Spēlētāju dati (sezonas/speletaji.csv un sezonas/vartsargi.csv) vēl nav pieejami.")
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
            L = L[[c for c in ["playerId", "Speletajs", "Komanda", "Poz", "GP", "G", "A", "P", "P_sp", "PM", "PIM", "SOG", "HIT", "BLK", "PPG", "TOI"]
                   if c in L.columns]]
            rtabula(L, hide_index=True, width="stretch", kartot=False,
                         column_config={"playerId": None, "Komanda": st.column_config.ImageColumn("TEAM", width="small"),
                                        "Poz": st.column_config.TextColumn("POS"),
                                        "TOI": st.column_config.NumberColumn("TOI AVG", format="%.1f"),
                                        "P_sp": st.column_config.NumberColumn("P AVG", format="%.2f")})
    with t_vart:
        G = da.vartsargu_lideri(vg)
        if G.empty:
            st.info("Nav datu.")
        else:
            c1, c2 = st.columns(2)
            kom = c1.selectbox("Komanda", komandas, key="vg_kom",
                               format_func=lambda x: x if x == "Visas komandas" else komandas_etikete(x))
            kart_opc = {"SV %": ("SVpct", False), "GAA": ("GAA", True), "W": ("W", False), "SHUTOUT": ("SHUT", False), "GP": ("GP", False),
                        "SA": ("SA", False), "SV": ("SV", False), "GA": ("GA", True), "TOI": ("TOI", False)}
            kart_v = c2.selectbox("Kārtot pēc", list(kart_opc), key="vg_kart")
            if kom != "Visas komandas":
                G = G[G["Komanda"] == kom]
            G = G.copy()
            G["SHUT"] = G["playerId"].map(fakti.shutouts(vg)).fillna(0).astype(int) if fakti is not None else 0
            kol_, aug_ = kart_opc[kart_v]
            G = G.sort_values([kol_, "GP"], ascending=[aug_, False]).rename(columns={"TOI": "TOI_kopa"})
            G["Komanda"] = G["Komanda"].map(da.logo_url)
            G = G[[c for c in ["playerId", "Vartsargs", "Komanda", "GP", "GS", "W", "SA", "SV", "GA", "GAA", "SVpct", "SHUT", "TOI_kopa"] if c in G.columns]]
            rtabula(G, hide_index=True, width="stretch", kartot=False,
                         paskaidr={"SHUTOUT": "Sausās spēles: uzvaras bez ielaistiem vārtiem, nostāvot visu spēli vienam"},
                         column_config={"playerId": None, "Komanda": st.column_config.ImageColumn("TEAM", width="small"),
                                        "SVpct": st.column_config.NumberColumn("SV %", format="%.1f"),
                                        "GAA": st.column_config.NumberColumn("GAA", format="%.2f"),
                                        "SHUT": st.column_config.NumberColumn("SHUTOUT", format="%d"),
                                        "TOI_kopa": st.column_config.NumberColumn("TOI", format="%.0f")})



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
                "(sezonas/tiesnesi.csv); iepriekšējo sezonu dati – sezonas/vesture/<sezona>/tiesnesi.csv.")
        return
    db_sez = da.vestures_sezonas()
    db_txt = ", ".join(f"{s_[:4]}/{s_[6:]}" for s_ in db_sez) if db_sez else "nav"

    with st.expander("Aprēķina iestatījumi", expanded=False):
        c1, c2 = st.columns(2)
        w_prev = c1.slider("DB svars (%)", 0, 100, 60, 5, key="ti_w",
                           help=f"DB = iepriekšējās sezonas kopā ({db_txt})") / 100
        k = c2.slider("Līgas vidējā korekcija K (spēles)", 0, 30, 10, key="ti_k")
        st.caption(f"Kombinētais rādītājs = {w_prev:.0%} × DB ({db_txt}) + {1 - w_prev:.0%} × šī sezona. "
                   f"Katra sezonas komponente tiek pievilkta pie līgas vidējā, kas vienāds ar {k} spēlēm: "
                   "jaunam tiesnesim vai ar maz spēlēm rādītājs ir tuvu līgas vidējam.")

    tab, liga = da.tiesnesu_apkopojums(cur, prev, w_prev=w_prev, k=k)
    if tab.empty:
        st.info("Nav tiesnešu datu.")
        return
    if prev is None:
        st.caption("Iepriekšējo sezonu dati (sezonas/vesture/<sezona>/tiesnesi.csv) nav atrasti, tāpēc tiek lietota tikai šī sezona.")

    m = st.columns(4)
    m[0].metric("Līgas vidējais šosezon", fmt(liga["t"]["kopa"]), border=True)
    m[1].metric("Līgas vidējais DB", f"{liga['p']['kopa']:.2f}" if pd.notna(liga["p"]["kopa"]) else "–", border=True,
                help=f"Iepriekšējās sezonas kopā: {db_txt}")
    m[2].metric("Tiesneši datubāzē", len(tab), border=True)
    m[3].metric("Spēles ar tiesnešiem šosezon",
                0 if cur is None else int(cur.loc[cur["loma"] == "referee", "game_id"].nunique()), border=True)

    t_tab, t_rez, t_spele = st.tabs(["Tiesnešu tabula", "Gaidāmie noraidījumi spēlei", "Tiesneša spēles"])
    with t_tab:
        min_sp = st.slider("Rādīt tiesnešus ar vismaz tik spēlēm (šī sezona + DB kopā)", 0, 150, 0, key="ti_min")
        t = tab[(tab["GP_t"] + tab["GP_p"]) >= min_sp].sort_values("kopa", ascending=False).reset_index(drop=True)
        vis = pd.DataFrame({
            "Tiesnesis": t["vards"], "Spēles šosezon": t["GP_t"], "Spēles DB": t["GP_p"],
            "Noraid. vid. šosezon": t["kopa_t"], "Noraid. vid. DB": t["kopa_p"],
            "Kombinētais": t["kopa"], "Pret līgu": t["kopa_vs_liga"],
            "Mājas komanda": t["majas"], "Viesu komanda": t["viesi"], "Dati": t["dati"]})
        fm = st.column_config.NumberColumn(format="%.2f")
        rtabula(vis, hide_index=True, width="stretch",
                     height=min(900, 35 * (len(vis) + 1) + 3),
                     column_config={"Noraid. vid. šosezon": fm, "Noraid. vid. DB": fm, "Kombinētais": fm,
                                    "Mājas komanda": fm, "Viesu komanda": fm,
                                    "Pret līgu": st.column_config.NumberColumn(format="%+.2f")},
                     paskaidr={"Spēles DB": f"Spēles iepriekšējās sezonās kopā ({db_txt})",
                               "Noraid. vid. šosezon": "Vidēji noraidījumi spēlē šosezon (abām komandām kopā)",
                               "Noraid. vid. DB": f"Vidēji noraidījumi spēlē iepriekšējās sezonās kopā ({db_txt})",
                               "Kombinētais": "Šīs sezonas un DB vidējais, pievilkts pie līgas vidējā (sk. Aprēķina iestatījumi)",
                               "Pret līgu": "Kombinētais mīnus līgas vidējais: + = vairāk noraidījumu nekā vidēji",
                               "Mājas komanda": "Kombinētie noraidījumi mājas komandai spēlē",
                               "Viesu komanda": "Kombinētie noraidījumi viesu komandai spēlē",
                               "Dati": "Spēļu skaits (šī sezona + DB): Maz < 8 spēles, Vidēji 8–19, OK 20+"})
        st.caption("Noraidījumi = abu komandu minor sodu skaits spēles pamatlaikā (dubultais minor = 2; bez major, 10 min disciplinārajiem un kautiņiem), "
                   f"ko pieskaita katram spēles tiesnesim. DB = iepriekšējās sezonas kopā ({db_txt}).")

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
        st.info("Spēlētāju dati (sezonas/speletaji.csv) vēl nav pieejami.")
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
        min_sp = st.slider("Minimālais spēļu skaits logā", 2, 5, max(2, min(3, max_gp)), key="ks_min",
                               help="Viena spēle nekad netiek ņemta vērā; agrā sezonā logā var būt mazāk spēļu")
    logs_t = "Pēdējās 5"                                   # logs vienmēr pēdējās 5 spēles
    with st.container(key="frinda_ks"):                   # Rādītājs un Pozīcija blakus pa kreisi
        metrika = izvele("Rādītājs", ["Punkti", "Vārti", "Piespēles"], key="ks_m")
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
# NAVIGĀCIJA
# Struktūra ir šeit, vienā vietā: lapas var pārvietot starp grupām, grupas pārsaukt vai lapu izvilkt kā atsevišķu pogu
# ({"lapa": (...)} ieraksts bez grupas). Ikonas ir Material Symbols (fonts.google.com/icons).
# ============================================================================
def augseja_josla(aktiva):
    """Viena josla augšā: zīmols + atsevišķas pogas + grupas, kuru lapas parādās, uzvedot peli virsū (vai pieskaroties)."""
    pedejais = len(STRUKTURA) - 1
    with st.container(key="topbar"):
        with st.container(key="brand"):
            st.page_link(ZIMOLA_LAPA or VISAS_LAPAS[0], label="NHL stats", icon=":material/sports_hockey:")
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
  // ---- tumšais motīvs: slēdzis saule/mēness joslas labajā stūrī; izvēle glabājas pārlūkā (localStorage "nhl_tema") ----
  // Automātiski pēc ierīces vietējā laika: 08:00–23:00 gaišais, 23:01–07:59 tumšais.
  // Ar slēdzi izvēlētais motīvs ir spēkā līdz nākamajai automātiskajai maiņai (08:00 vai 23:01).
  function autoTumss(dt) { var m = dt.getHours() * 60 + dt.getMinutes(); return m >= 23 * 60 + 1 || m < 8 * 60; }
  function nakamaMaina(dt) {
    var n = new Date(dt.getTime()); n.setSeconds(0, 0);
    var m = dt.getHours() * 60 + dt.getMinutes();
    if (m < 8 * 60) { n.setHours(8, 0); } else if (m < 23 * 60 + 1) { n.setHours(23, 1); } else { n.setDate(n.getDate() + 1); n.setHours(8, 0); }
    return n.getTime();
  }
  function tumss() {
    try {
      var v = w.localStorage.getItem('nhl_tema'), lidz = +(w.localStorage.getItem('nhl_tema_lidz') || 0);
      if ((v === 'tumss' || v === 'gaiss') && Date.now() < lidz) return v === 'tumss';
    } catch (e) {}
    return autoTumss(new Date());
  }
  var IFR_CSS = 'html.tumss body{color:#e6ebf2!important;background:transparent!important}html.tumss .lbl,html.tumss .nos,html.tumss span,html.tumss div{color:#e6ebf2}';
  function iframes(t) {                    // tās pašas izcelsmes komponenti (piem., rullīši): tāda pati klase un gaišs teksts
    d.querySelectorAll('iframe').forEach(function (f) {
      try { var dd = f.contentDocument; if (!dd || !dd.documentElement) return;
        dd.documentElement.classList.toggle('tumss', t);
        if (!dd.getElementById('nhl-tumss')) { var s = dd.createElement('style'); s.id = 'nhl-tumss'; s.textContent = IFR_CSS; (dd.head || dd.documentElement).appendChild(s); }
      } catch (e) {}
    });
  }
  function gaissFons(el) {
    var cs = w.getComputedStyle(el), bg = cs.backgroundColor || '', bi = cs.backgroundImage || '';
    return /rgba?\\((25[0-5]|24\\d), *(25[0-5]|24\\d), *(25[0-5]|24\\d)(, *(1|0?\\.[5-9]\\d*))?\\)/.test(bg) || /gradient/.test(bi) && /(255, 255, 255|white)/.test(bi);
  }
  function krasa(s) {                      // "rgb(a)(...)" → {g: gaisums 0–255, a: alfa, pel: vai pelēcīga (nav krāsaina)}
    var m = (s || '').match(/rgba?\\(([\\d.]+),\\s*([\\d.]+),\\s*([\\d.]+)(?:,\\s*([\\d.]+))?\\)/);
    if (!m) return null;
    var r = +m[1], g = +m[2], b = +m[3];
    return { g: 0.299 * r + 0.587 * g + 0.114 * b, a: m[4] === undefined ? 1 : +m[4], pel: Math.max(r, g, b) - Math.min(r, g, b) < 40 };
  }
  var LAUKU_ZONAS = '.stSelectbox, .stMultiSelect, [data-baseweb="popover"], [data-testid="stSelectboxVirtualDropdown"], [role="listbox"]';
  function tumsieLauki(t) {                 // izvēlnes un to saraksti: Streamlit krāsas nāk no iekšējām klasēm, tāpēc pārkrāso pēc aprēķinātās krāsas
    d.querySelectorAll(LAUKU_ZONAS).forEach(function (z) {
      [z].concat(Array.prototype.slice.call(z.querySelectorAll('*'))).forEach(function (el) {
        if (el instanceof w.SVGElement) return;
        if (t) {
          var cs = w.getComputedStyle(el), bg = krasa(cs.backgroundColor), tx = krasa(cs.color), mainits = false;
          if (el.dataset.nhlLauks !== '1') el.dataset.nhlOrigL = el.getAttribute('style') || '';
          if (bg && bg.a > 0.3 && bg.g > 185) {                    // gaišs fons → tumši zils (izceltā rinda nedaudz gaišāka)
            el.style.setProperty('background-color', bg.g > 238 ? '#22304a' : '#2e3f5c', 'important'); mainits = true;
          }
          if (tx && tx.g < 140 && tx.pel) {                        // tumšs pelēks teksts → gaišs (krāsainu tekstu neaiztiek)
            el.style.setProperty('color', '#e6ebf2', 'important'); el.style.setProperty('-webkit-text-fill-color', '#e6ebf2', 'important'); mainits = true;
          }
          if (mainits) el.dataset.nhlLauks = '1'; else if (el.dataset.nhlLauks !== '1') delete el.dataset.nhlOrigL;
        } else if (el.dataset.nhlLauks === '1') {
          el.setAttribute('style', el.dataset.nhlOrigL || ''); delete el.dataset.nhlOrigL; delete el.dataset.nhlLauks;
        }
      });
    });
  }
  function tabuBultas(t) {                  // cilņu ritināšanas bultiņas tumšajā motīvā – tumši zilas
    d.querySelectorAll('.stTabs').forEach(function (tb) {
      var kandidati = [], tw = d.createTreeWalker(tb, 1, { acceptNode: function (n) {      // cilņu saturu un pašas cilnes izlaiž ar visu apakškoku
        if (n.matches('[data-baseweb="tab-panel"], [role="tab"]')) return 2;             // FILTER_REJECT
        return n.matches('[data-baseweb="tab-list"], [data-baseweb="tab-highlight"], [data-baseweb="tab-border"]') ? 3 : 1;   // SKIP / ACCEPT
      } });
      while (tw.nextNode()) kandidati.push(tw.currentNode);
      kandidati.forEach(function (el) {
        if (t) {
          if (el.dataset.nhlBulta === '1' || (el.getBoundingClientRect().width < 90 && gaissFons(el))) {
            if (el.dataset.nhlBulta !== '1') el.dataset.nhlOrig = el.getAttribute('style') || '';     // oriģinālais stils atjaunošanai
            el.dataset.nhlBulta = '1';
            el.style.setProperty('background', '#22304a', 'important'); el.style.setProperty('background-image', 'none', 'important');
            el.style.setProperty('color', '#93c5fd', 'important');
            // krāsa tikai pašam svg (ceļi to manto); ceļus neaiztiek, jo ikonām ir caurspīdīgs fona kvadrāts (fill="none")
            el.querySelectorAll('svg').forEach(function (s) { s.style.setProperty('color', '#93c5fd', 'important'); s.style.setProperty('fill', 'currentColor', 'important'); });
          }
        } else if (el.dataset.nhlBulta === '1') {
          el.setAttribute('style', el.dataset.nhlOrig || ''); delete el.dataset.nhlOrig;
          el.querySelectorAll('svg').forEach(function (s) { s.style.removeProperty('fill'); s.style.removeProperty('color'); });
          delete el.dataset.nhlBulta;
        }
      });
    });
  }
  function piemerot() { var t = tumss(); d.documentElement.classList.toggle('tumss', t); iframes(t); tabuBultas(t); tumsieLauki(t);
    var sw = d.querySelector('.tema-sw'); if (sw) { sw.setAttribute('aria-pressed', t ? 'true' : 'false'); sw.title = t ? 'Gaišais motīvs' : 'Tumšais motīvs'; } }
  function sledzis(atjaunot) {
    var b = josla(); if (!b) return;
    var vecais_sw = b.querySelector('.tema-sw');
    if (vecais_sw) { if (!atjaunot) return; vecais_sw.remove(); }       // jauns skripta kadrs: slēdzis ar dzīvu klikšķa apstrādi
    var sw = d.createElement('button'); sw.type = 'button'; sw.className = 'tema-sw'; sw.setAttribute('aria-label', 'Gaišais / tumšais motīvs');
    sw.innerHTML = '<svg class="s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/>'
      + '<path d="M12 2v2.2M12 19.8V22M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2 12h2.2M19.8 12H22M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6"/></svg>'
      + '<svg class="m" viewBox="0 0 24 24" fill="currentColor"><path d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5a8.5 8.5 0 1 0 11.1 11.1z"/></svg>';
    sw.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation();
      try { w.localStorage.setItem('nhl_tema', tumss() ? 'gaiss' : 'tumss'); w.localStorage.setItem('nhl_tema_lidz', String(nakamaMaina(new Date()))); } catch (e2) {}
      piemerot(); });
    b.appendChild(sw); piemerot();
  }
  piemerot(); sledzis(true);
  if (w.__nhlTemaMO) { try { w.__nhlTemaMO.disconnect(); } catch (e) {} }   // vecā kadra novērotāju aizstāj ar šī kadra
  var __nhlTemaT = null;
  w.__nhlTemaMO = new w.MutationObserver(function () {                 // apvienots: ne biežāk kā reizi 150 ms
    if (__nhlTemaT) return;
    __nhlTemaT = w.setTimeout(function () {
      __nhlTemaT = null;
      if (josla() && !d.querySelector('.tema-sw')) sledzis(false);
      if (tumss()) { iframes(true); tabuBultas(true); tumsieLauki(true); }
    }, 150);
  });
  if (w.__nhlTemaInt) w.clearInterval(w.__nhlTemaInt);    // automātiskā maiņa (08:00 / 23:01) arī tad, ja lapa ir atvērta
  w.__nhlTemaInt = w.setInterval(function () { if (d.documentElement.classList.contains('tumss') !== tumss()) piemerot(); }, 60000);
  w.__nhlTemaMO.observe(d.body, { childList: true, subtree: true });
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
# ============================================================================
# SEZONA UN RS / PO: statistika vienmēr tiek skaitīta atsevišķi regulārajai sezonai un play-off.
# Pārslēdzējs "Regulārā sezona · Play-off" parādās tikai tad, kad datos ir play-off spēles.
# Rezultāti, Kalendārs, Prognozes, Karstākie spēlētāji un Tiesneši izmanto visas šīs sezonas spēles; Līgas pārskats – tikai RS.
# ============================================================================
SEZ_DALAS = {da.TIPS_RS: "Regulārā sezona", da.TIPS_PO: "Play-off"}
LAPAS_VISAS_SPELES = {"Rezultāti", "Kalendārs", "Prognozes", "Karstākie spēlētāji", "Tiesneši"}
RAW_VISS, DF_VISS = RAW, DF
if RAW_VISS is not None and not RAW_VISS.empty:
    SEZONA = int(RAW_VISS["sezona"].max())
    RAW_VISS = RAW_VISS[RAW_VISS["sezona"] == SEZONA]
    DF_VISS = DF_VISS[DF_VISS["sezona"].fillna(SEZONA) == SEZONA] if DF_VISS is not None and not DF_VISS.empty else DF_VISS
    PO_IR = bool((RAW_VISS["tips"] == da.TIPS_PO).any())
else:
    SEZONA, PO_IR = None, False
_lapa_nos = getattr(lapas, "title", "")
if _lapa_nos in LAPAS_VISAS_SPELES:
    SEZ_DALA = None
elif _lapa_nos == "Līgas pārskats" or not PO_IR:
    SEZ_DALA = da.TIPS_RS
else:
    SEZ_DALA = st.session_state.get("sez_dala", da.TIPS_RS) if st.session_state.get("sez_dala") in SEZ_DALAS else da.TIPS_RS
if RAW_VISS is not None and not RAW_VISS.empty:
    RAW = RAW_VISS if SEZ_DALA is None else RAW_VISS[RAW_VISS["tips"] == SEZ_DALA]
    DF = DF_VISS if SEZ_DALA is None else DF_VISS[DF_VISS["tips"] == SEZ_DALA]
    SPELU_ID = set(RAW["game_id"])
if PO_IR and _lapa_nos not in LAPAS_VISAS_SPELES:
    if _lapa_nos == "Līgas pārskats":
        st.markdown('<div class="sez-piez">Līgas tabula: tikai regulārā sezona</div>', unsafe_allow_html=True)
    else:
        with st.container(key="pgr_sez_dala"):
            for _k, _nos in SEZ_DALAS.items():
                st.button(_nos, key=f"sezd_{_k}", type="primary" if SEZ_DALA == _k else "secondary",
                          on_click=lambda k_=_k: st.session_state.__setitem__("sez_dala", k_))

lapas.run()


def kajene_html():
    """Lapas apakšā: kā tiek rēķināts, kādi dati pieejami, no kurienes tie nāk un ka tie ir tikai informatīvi."""
    try:
        d_ = RAW["datums_lv"].dt.date
        periods = f"šīs sezonas spēles no {d_.min():%d.%m.%Y} līdz {d_.max():%d.%m.%Y} ({len(RAW)} spēles)"
    except Exception:
        periods = "šīs sezonas aizvadītās spēles"
    db_sez = da.vestures_sezonas()
    if db_sez:
        periods += ("; datubāzē arī iepriekšējās sezonas (" + ", ".join(f"{s[:4]}/{s[6:]}" for s in db_sez) +
                    "), kas lapās netiek rādītas, bet tiek izmantotas tiesnešu statistikā")
    return f'''<div class="kaj">
<p><b>Kā tiek rēķināts.</b> Visi rādītāji (vārti, metieni, noraidījumi, vairākums, periodi) ir tikai par pamatlaiku – papildlaiks
un pēcspēles metienu sērijas netiek ieskaitīti; tās ir apkopotas atsevišķi sadaļā OT / SO. Vidējie ir kopsumma, dalīta ar
izvēlēto spēļu skaitu (visa sezona, pēdējās 5 vai pēdējās 10, visas vai tikai mājās / viesos). Noraidījumi ir minor sodi
(dubultais minor = 2), bez lielajiem un disciplinārajiem sodiem. Bilance (win, loss, OT loss) un punkti ir oficiālie rezultāti.</p>
<p><b>Pieejamie dati.</b> {periods}; nākamo spēļu kalendārs uz priekšu.</p>
<p><b>Datu avoti.</b> NHL oficiālā statistika (rezultāti, spēlētāji, vārtsargi, notikumi, kalendārs, tiesneši pēc spēles)
un Scouting The Refs (pirms spēlēm paziņotie tiesneši). Dati tiek atjaunināti automātiski katru dienu.</p>
<p class="kaj-pied">Visa informācija ir tikai informatīva un balstīta uz matemātiskiem aprēķiniem no pieejamajiem datiem.
Tā nav garantija un nav ieteikums.</p>
</div>'''


st.markdown(kajene_html(), unsafe_allow_html=True)
with st.container(key="kaj_logo"):                         # logo (tas pats, kas cilnē) virs versijas
    st.markdown(":material/sports_hockey:")
st.markdown(f'<div style="text-align:center;font-size:.7rem;opacity:.35;margin-top:.2rem">versija {APP_VERSIJA}</div>', unsafe_allow_html=True)

# ===== app.py beigas (ja šī rinda redzama GitHub failā, fails ir augšupielādēts pilnīgi) =====
