"""
Valodas atbalsts (EN / LV) NHL stats lietotnei.

KĀ TAS STRĀDĀ
  Kods paliek latviski: iekšējās vērtības, kolonnu nosaukumi, pogu vērtības un loģika netiek mainīti. Tulkots tiek tikai tas,
  ko redz lietotājs – tieši pirms parādīšanas ekrānā:
    - uzstadit() aizstāj Streamlit teksta funkcijas (st.markdown, st.caption, st.info, st.metric, pogas, cilnes, logrīku
      etiķetes un izvēļu nosaukumi u.c.) ar versijām, kas tekstu pārtulko ar T();
    - HTML tekstā (tabulas, kartītes) tiek tulkoti teksta gabali starp tagiem un atribūti title / aria-label / alt / placeholder;
    - tulkojumi ir failā tulkojumi_en.py: {"latviešu teksts": "English text"}.
  Veidnes: {} aizstāj mainīgu daļu (skaitli, vārdu, komandu), piem. "Vidēji {} spēlē" → "{} per game". Ja angliski secība
  jāmaina, lieto {0}, {1}. {:%d.%m} u.tml. ir datums – angliski tas tiek pārveidots uz "Nov 12" (laiks paliek Rīgas laikā).
  Mainīgā daļa, ja tā ir latviešu vārds (piem., "punkti"), tiek tulkota atsevišķi.

JAUNS TEKSTS LIETOTNĒ
  Pievieno rindu tulkojumi_en.py. Neiztulkotie teksti ir redzami, atverot lapu ar ?i18n=1 (saraksts lapas apakšā).

VALODA
  Noklusējums – angļu. Izvēle: slēdzis EN | LV augšējā joslā; tiek saglabāta sesijā, adresē (?lang=lv) un pārlūkā
  (localStorage "nhl_valoda"), tāpēc nākamajā apmeklējumā atveras izvēlētā valoda. Ārpus Streamlit (skripti) T() neko nemaina.
"""
import datetime as _dt
import functools
import html as _h
import os
import re
import threading

VALODAS = ("en", "lv")
NOKLUSEJUMS = "en"
SESIJAS_ATSLEGA = "valoda"

_tl = threading.local()                  # katrai Streamlit sesijai (skripta pavedienam) sava valoda


def valoda():
    """Aktīvā valoda ("en" / "lv"). Ārpus lietotnes (skripti, testi) – "lv", lai nekas netiktu mainīts."""
    return getattr(_tl, "v", "lv")


def iestatit(v):
    _tl.v = v if v in VALODAS else NOKLUSEJUMS


def en():
    return valoda() == "en"


# ----------------------------------------------------------------------------
# Tulkojumu vārdnīca un veidnes
# ----------------------------------------------------------------------------
_LVC = re.compile(r"[āčēģīķļņšūžĀČĒĢĪĶĻŅŠŪŽ]")
_BURTS = re.compile(r"[A-Za-zÀ-ž]")
_VIETA = re.compile(r"\{(:[^{}]*)?\}")
MENESI = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DIENAS_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

_EXACT = {}            # normalizēts LV teksts → EN
_VEIDNES = {}          # pirmās 2 zīmes → [(regex, EN, veidi, garākā konstantā daļa, garums)]
_PELDOSAS = []         # veidnes, kas sākas ar {}
_TRUKST = set()        # neiztulkotie teksti (redzami ar ?i18n=1)
_IELADETS = [False]
_lock = threading.Lock()


def _n(s):
    return re.sub(r"\s+", " ", s).strip()


def _sadalit(k):
    """Veidni sadala konstantajās daļās un vietās: (["Vidēji ", " spēlē"], [""]); {{ }} – burtiskās iekavas."""
    k = k.replace("{{", "\x00").replace("}}", "\x01")
    dalas, vietas, pos = [], [], 0
    for m in _VIETA.finditer(k):
        dalas.append(k[pos:m.start()])
        vietas.append((m.group(1) or "")[1:])
        pos = m.end()
    dalas.append(k[pos:])
    dalas = [d.replace("\x00", "{").replace("\x01", "}") for d in dalas]
    return dalas, vietas


def _en_formats(v, n):
    """EN veidne: {} secīgi vai {0}, {1} – pārveido uz numurētām vietām."""
    v = v.replace("{{", "\x00").replace("}}", "\x01")
    i = [0]

    def f(m):
        if m.group(1) is not None and m.group(1) != "":
            return "{" + m.group(1) + "}"
        r = "{" + str(i[0]) + "}"
        i[0] += 1
        return r
    v = re.sub(r"\{(\d*)(?::[^{}]*)?\}", f, v)              # formāta norādes ({:.1%}) EN pusē neder – vietās jau ir teksts
    return v.replace("\x00", "{{").replace("\x01", "}}")


def _pievienot(lv, en_):
    k = _n(lv)
    if not k or en_ is None:
        return
    if _VIETA.search(k.replace("{{", "").replace("}}", "")):
        dalas, vietas = _sadalit(k)
        rx = ""
        for i, d in enumerate(dalas):
            # Atstarpe starp tekstu un vietu drīkst trūkt tikai teksta malā (HTML gabals beidzas / sākas ar vietu, piem.
            # "Ticamākie rezultāti:" no "Ticamākie rezultāti: {}"); vārda vidū (pret → pretinieks) tā nekad neatbilst.
            if d.strip():
                pirms = i > 0 and d[:1] == " "
                pec = i < len(vietas) and d[-1:] == " "
                d_ = d.strip(" ") if (pirms and pec) else (d[1:] if pirms else (d[:-1] if pec else d))
                rx += (r"(?:^|\s)" if pirms else "") + re.escape(d_) + (r"(?:\s|$)" if pec else "")
            else:
                rx += re.escape(d)
            if i < len(vietas):                                   # datuma vietā – tikai cipari un atdalītāji
                rx += r"(\d[\d.:() ]*?)" if re.search(r"%[dmYHM]", vietas[i]) else "(.*?)"
        rx = rx.replace(r"\ ", " ")
        try:
            rxc = re.compile(rx, re.S)
        except re.error:
            return
        gar = max((d.strip() for d in dalas), key=len)
        lit = sum(len(d) for d in dalas)
        ier = (rxc, _en_formats(en_, len(vietas)), tuple(vietas), gar, lit)
        if dalas[0] and len(dalas[0]) >= 2:
            _VEIDNES.setdefault(dalas[0][:2], []).append(ier)
        else:
            _PELDOSAS.append(ier)
    else:
        _EXACT[k] = en_


_VARDNICAS_FAILS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tulkojumi_en.py")
_VARDNICAS_MTIME = [None]


def _lasit_vardnicu():
    """tulkojumi_en.py saturs (katru reizi no faila, lai pēc augšupielādes nav vajadzīgs Reboot app)."""
    try:
        ns = {}
        with open(_VARDNICAS_FAILS, encoding="utf-8") as f:
            exec(compile(f.read(), _VARDNICAS_FAILS, "exec"), ns)
        return ns.get("EN", {})
    except Exception:
        return {}


def ieladet(vardnica=None):
    """Ielādē tulkojumus. Bez argumenta – no tulkojumi_en.py, ja tas ir mainījies kopš pēdējās ielādes."""
    with _lock:
        if vardnica is None:
            try:
                mt = os.path.getmtime(_VARDNICAS_FAILS)
            except OSError:
                mt = None
            if _IELADETS[0] and mt == _VARDNICAS_MTIME[0]:
                return
            _VARDNICAS_MTIME[0] = mt
            vardnica = _lasit_vardnicu()
        _EXACT.clear()
        _VEIDNES.clear()
        _PELDOSAS.clear()
        _TRUKST.clear()
        try:
            _tr.cache_clear()
            _tr_html.cache_clear()
        except NameError:
            pass
        for lv, en_ in vardnica.items():
            _pievienot(lv, en_)
        for v in _VEIDNES.values():
            v.sort(key=lambda x: -x[4])
        _PELDOSAS.sort(key=lambda x: -x[4])
        _IELADETS[0] = True


def _datums_en(s, spec):
    """'12.11' (spec %d.%m) → 'Nov 12'; '12.11.2026' → 'Nov 12, 2026'; ar laiku – 'Nov 12 19:00'."""
    try:
        d = _dt.datetime.strptime(s.strip(), spec.strip())
    except Exception:
        return s
    ir_d, ir_t = "%d" in spec, "%H" in spec
    out = f"{MENESI[d.month - 1]} {d.day}" if ir_d else ""
    if ir_d and "%Y" in spec:
        out += f", {d.year}"
    if ir_t:
        t = f"{d:%H:%M}"
        out = f"{out} ({t})" if "(%H" in spec else (f"{out} {t}" if out else t)
    return out


_DAT_RX = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})?(?: (\d{1,2}):(\d{2}))?")


def _datums_viens(k):
    """Viss teksts ir datums ar punktu aiz mēneša vai gadu (12.11.2026, 12.11. 19:00) – nav sajaucams ar decimālskaitli."""
    m = _DAT_RX.fullmatch(k)
    if not m:
        return None
    d, mn = int(m.group(1)), int(m.group(2))
    if not (1 <= d <= 31 and 1 <= mn <= 12):
        return None
    out = f"{MENESI[mn - 1]} {d}" + (f", {m.group(3)}" if m.group(3) else "")
    if m.group(4):
        out += f" {int(m.group(4)):02d}:{m.group(5)}"
    return out


_DAT_SPEC = re.compile(r"%[dmYHM]")


def _arg(c, spec, dzil):
    if _DAT_SPEC.search(spec):
        return _datums_en(c, spec)
    if not c or "<" in c or len(c) > 400 or not _BURTS.search(c):
        return c
    return _tr(c, dzil + 1)


def _veidne(k, dzil, min_dala=0.0):
    """Veidnes tulkojums. min_dala: cik lielai teksta daļai jābūt veidnes konstantajam tekstam (HTML veselumam – lai
    vispārīga veidne, piem. "{} pret {}", nepārtulkotu lielu HTML bloku pa daļai)."""
    labakais = None
    for ier in (*_VEIDNES.get(k[:2], ()), *_PELDOSAS):
        rxc, en_, vietas, gar, lit = ier
        if gar and gar not in k:
            continue
        if min_dala and lit < min_dala * len(k):
            continue
        m = rxc.fullmatch(k)
        if not m:
            continue
        try:
            r = en_.format(*[_arg(g, s, dzil) for g, s in zip(m.groups(), vietas)])
        except (IndexError, KeyError, ValueError):
            continue
        n = len(_LVC.findall(r))
        if n == 0:
            return r
        if labakais is None or n < labakais[0]:               # vairākas veidnes der – paliek tā, pēc kuras paliek vismazāk latviešu
            labakais = (n, r)
    return labakais[1] if labakais else None


@functools.lru_cache(maxsize=40000)
def _tr(s, dzil=0, uzskaitit=True):
    """Viena teksta tulkojums angliski (bez valodas pārbaudes). Netulkotu atgriež nemainītu."""
    if dzil > 8 or not s:
        return s
    if not _BURTS.search(s):
        d = _datums_viens(s.strip()) if "." in s else None
        return s if d is None else s[:len(s) - len(s.lstrip())] + d + s[len(s.rstrip()):]
    if not _IELADETS[0]:
        ieladet()
    k = _n(s)
    r = _EXACT.get(k)
    if r is None:
        r = _veidne(k, dzil)
    if r is None:
        r = _datums_viens(k)
    if r is None:
        if uzskaitit and _LVC.search(k):
            _TRUKST.add(k[:300])
        return s
    lead = s[:len(s) - len(s.lstrip())]
    trail = s[len(s.rstrip()):]
    return lead + r + trail


def T(s, *a, **kw):
    """Teksts lietotāja valodā. T("Vidēji {} spēlē", x) – arī ar formatēšanu."""
    if not isinstance(s, str):
        return s
    r = s if valoda() == "lv" else _tr(s)
    return r.format(*a, **kw) if (a or kw) else r


# ----------------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------------
_TOK = re.compile(r"<!--.*?-->|<[^<>]+>", re.S)
_ATR = re.compile(r'(\b(?:title|aria-label|alt|placeholder|data-tip)\s*=\s*")([^"]*)(")')


def _tr_atr(m):
    v = _h.unescape(m.group(2))
    t = _tr(v)
    return m.group(1) + (_h.escape(t, quote=True) if t != v else m.group(2)) + m.group(3)


@functools.lru_cache(maxsize=256)
def _tr_html(s):
    if len(s) <= 12000 and "<style" not in s and "<script" not in s:     # viss teksts kā viena veidne (Markdown ar ikonām u.tml.)
        k = _n(s)
        r = _EXACT.get(k)
        if r is None:
            r = _veidne(k, 0, 0.3)
        if r is not None:
            return s[:len(s) - len(s.lstrip())] + r + s[len(s.rstrip()):]
    out, pos, iekseja = [], 0, None                 # iekseja: style / script saturs netiek tulkots
    for m in _TOK.finditer(s):
        teksts = s[pos:m.start()]
        if teksts:
            out.append(teksts if iekseja else _tr_teksts(teksts))
        tags = m.group(0)
        tl = tags[1:8].lower()
        if tl.startswith(("style", "script")):
            iekseja = "style" if tl.startswith("style") else "script"
        elif iekseja and tl.startswith("/" + iekseja):
            iekseja = None
        out.append(tags if iekseja or tags.startswith("<!--") else _ATR.sub(_tr_atr, tags))
        pos = m.end()
    teksts = s[pos:]
    if teksts:
        out.append(teksts if iekseja else _tr_teksts(teksts))
    return "".join(out)


def _tr_teksts(t):
    if not _BURTS.search(t):
        return t
    v = _h.unescape(t)
    r = _tr(v)
    if r == v:
        return t
    return _h.escape(r, quote=False) if any(c in r for c in "<>&") else r


_HTML_RX = re.compile(r"<(/?[a-zA-Z][a-zA-Z0-9-]*)[\s>/]")


def T_html(s):
    """HTML (vai Markdown ar HTML) teksts lietotāja valodā: tulko tekstu starp tagiem un title / aria-label atribūtus."""
    if not isinstance(s, str) or valoda() == "lv" or not s:
        return s
    return _tr_html(s) if _HTML_RX.search(s) else _tr(s)


def T_jebkas(x):
    if isinstance(x, str):
        return T_html(x)
    return x


def trukstosie():
    return sorted(_TRUKST)


# ----------------------------------------------------------------------------
# Datumi (tekstam ārpus f-string veidnēm)
# ----------------------------------------------------------------------------
def datums(ts, formats="%d.%m.%Y"):
    """Datums lietotāja valodā: LV '12.11.2026', EN 'Nov 12, 2026' (formāts kā strftime ar %d.%m[.%Y] [%H:%M])."""
    if ts is None:
        return ""
    try:
        if valoda() == "lv":
            return ts.strftime(formats)
        return _datums_en(ts.strftime(formats), formats)
    except Exception:
        return str(ts)


# ----------------------------------------------------------------------------
# Streamlit funkciju aizstāšana
# ----------------------------------------------------------------------------
_TEKSTA = {             # metode: (pozicionālie indeksi, nosauktie parametri)
    "markdown": ((0,), ("body", "help")), "caption": ((0,), ("body", "help")), "title": ((0,), ("body", "help")),
    "header": ((0,), ("body", "help")), "subheader": ((0,), ("body", "help")), "text": ((0,), ("body", "help")),
    "info": ((0,), ("body",)), "warning": ((0,), ("body",)), "error": ((0,), ("body",)), "success": ((0,), ("body",)),
    "toast": ((0,), ("body",)), "html": ((0,), ("body",)),
    "metric": ((0, 1, 2), ("label", "value", "delta", "help")),
    "button": ((0,), ("label", "help")), "download_button": ((0,), ("label", "help")), "link_button": ((0,), ("label", "help")),
    "form_submit_button": ((0,), ("label", "help")),
    "page_link": ((1,), ("label", "help")),
    "expander": ((0,), ("label",)), "popover": ((0,), ("label", "help")),
    "slider": ((0,), ("label", "help")), "number_input": ((0,), ("label", "help", "placeholder")),
    "text_input": ((0,), ("label", "help", "placeholder")), "text_area": ((0,), ("label", "help", "placeholder")),
    "date_input": ((0,), ("label", "help")), "time_input": ((0,), ("label", "help")),
    "checkbox": ((0,), ("label", "help")), "toggle": ((0,), ("label", "help")),
    "progress": ((1,), ("text",)), "image": ((), ("caption",)),
}
_IZVELES = ("selectbox", "radio", "multiselect", "pills", "segmented_control", "select_slider")


def _ietinams_teksts(orig, poz, nos):
    @functools.wraps(orig)
    def f(self, *a, **kw):
        if valoda() != "lv":
            a = list(a)
            for i in poz:
                if i < len(a):
                    a[i] = T_jebkas(a[i])
            for n in nos:
                if n in kw:
                    kw[n] = T_jebkas(kw[n])
        return orig(self, *a, **kw)
    return f


def _ietinams_izvele(orig):
    @functools.wraps(orig)
    def f(self, *a, **kw):
        if valoda() != "lv":
            a = list(a)
            if a:
                a[0] = T_jebkas(a[0])
            for n in ("label", "help", "placeholder"):
                if n in kw:
                    kw[n] = T_jebkas(kw[n])
            ff = kw.get("format_func") or str
            kw["format_func"] = lambda o, _ff=ff: T(_ff(o))
        return orig(self, *a, **kw)
    return f


def _ietinams_tabs(orig):
    @functools.wraps(orig)
    def f(self, tabs, *a, **kw):
        if valoda() != "lv":
            tabs = [T(t) if isinstance(t, str) else t for t in tabs]
        return orig(self, tabs, *a, **kw)
    return f


def _ietinams_df(orig):
    @functools.wraps(orig)
    def f(self, data=None, *a, **kw):
        if valoda() != "lv":
            cc = kw.get("column_config")
            if isinstance(cc, dict):
                kw["column_config"] = {k: ({**v, **{p: T(v[p]) for p in ("label", "help") if isinstance(v.get(p), str)}}
                                           if isinstance(v, dict) else (T(v) if isinstance(v, str) else v)) for k, v in cc.items()}
        return orig(self, data, *a, **kw)
    return f


def uzstadit():
    """Aizstāj Streamlit teksta funkcijas ar tulkojošām (vienreiz procesā; valoda tiek pārbaudīta katrā izsaukumā)."""
    import streamlit as st
    if getattr(st, "_i18n_uzstadits", False):
        return
    try:
        from streamlit.delta_generator import DeltaGenerator as DG
    except Exception:
        return
    galvenais = None
    for nos, (poz, kw) in _TEKSTA.items():
        if hasattr(DG, nos):
            setattr(DG, nos, _ietinams_teksts(getattr(DG, nos), poz, kw))
    for nos in _IZVELES:
        if hasattr(DG, nos):
            setattr(DG, nos, _ietinams_izvele(getattr(DG, nos)))
    if hasattr(DG, "tabs"):
        DG.tabs = _ietinams_tabs(DG.tabs)
    for nos in ("dataframe", "data_editor"):
        if hasattr(DG, nos):
            setattr(DG, nos, _ietinams_df(getattr(DG, nos)))
    # st.markdown u.c. moduļa līmenī ir piesaistītas galvenā konteinera metodes – piesaista no jauna
    for nos in list(_TEKSTA) + list(_IZVELES) + ["tabs", "dataframe", "data_editor"]:
        x = getattr(st, nos, None)
        es = getattr(x, "__self__", None)
        if isinstance(es, DG):
            galvenais = es
            setattr(st, nos, getattr(es, nos))
    sp = getattr(st, "spinner", None)                    # st.spinner – parasta funkcija
    if sp is not None and getattr(sp, "__self__", None) is None:
        @functools.wraps(sp)
        def _spinner(text="", *a, **kw):
            return sp(T(text) if isinstance(text, str) else text, *a, **kw)
        st.spinner = _spinner
    st._i18n_uzstadits = True
    return galvenais


def sakt():
    """Lietotnes sākumā: nosaka valodu (adrese ?lang= → sesija → noklusējums EN) un ieslēdz tulkošanu."""
    import streamlit as st
    ieladet()
    uzstadit()
    v = None
    try:
        q = st.query_params.get("lang")
        if q in VALODAS:
            v = q
    except Exception:
        pass
    if v is None:
        v = st.session_state.get(SESIJAS_ATSLEGA)
    if v not in VALODAS:
        v = NOKLUSEJUMS
    st.session_state[SESIJAS_ATSLEGA] = v
    iestatit(v)
    return v


def mainit(v):
    """Pogas EN / LV klikšķis: valoda sesijā un adresē (saiti var saglabāt)."""
    import streamlit as st
    if v not in VALODAS:
        return
    st.session_state[SESIJAS_ATSLEGA] = v
    try:
        st.query_params["lang"] = v
    except Exception:
        pass
    iestatit(v)
