"""
Plānotie tiesneši: pirms spēlēm iegūst galvenos tiesnešus un ieraksta dati/tiesnesi_planotie.csv
(viena rinda uz spēli un amatpersonu). Spēļu laiki tiek ņemti no nhl_kalendars.csv (to atjaunina kalendars.py).

Avoti (pēc prioritātes):
  1. Scouting The Refs (scoutingtherefs.com): neatkarīgs hokeja tiesnešu portāls, kas katru dienu apmēram 4 stundas pirms pirmās spēles
     publicē ierakstu "Tonight's NHL Referees and Linespersons" ar visu spēļu tiesnešiem. NHL API (right-rail) pirms spēles tiesnešus parasti
     nesniedz, tāpēc šis ir galvenais avots. Skripts tur izdara tikai 2-3 pieprasījumus un tikai tad, kad tiesnešu vēl trūkst.
  2. NHL right-rail (gameInfo.referees), ja tur tiesneši jau ir.
Faila kolonna `avots` norāda, no kurienes katrs ieraksts.

Darbplūsma (.github/workflows/referees.yml) katras 30 minūtes palaiž ĀTRO pārbaudi:
  python tiesnesi_planotie.py --parbaude
Pārbaude nolasa tikai CSV failus (bez interneta) un izlemj, vai ir vajadzīga ielāde:
  • ielāde vajadzīga, ja kādai spēlei, kas sākas tuvāko 4 stundu laikā, vēl nav paziņoti tiesneši;
  • ja visām šīm spēlēm tiesneši jau ir failā, ielāde netiek palaista.
Ja ielāde vajadzīga, tā pārbauda visas spēles bez tiesnešiem tuvāko 8 stundu laikā (tāpēc agrāka ielāde
bieži jau aizpilda arī nākamās spēles), un nemaina spēles, kurām tiesneši jau ir.

Lietošana:
  python tiesnesi_planotie.py --parbaude       # tikai pārbaude (raksta needed=true/false uz GITHUB_OUTPUT)
  python tiesnesi_planotie.py                  # ielāde: spēles bez tiesnešiem tuvāko 8 h laikā
  python tiesnesi_planotie.py --stundas 30 --visas   # pārbauda arī spēles, kurām tiesneši jau ir (testam)
"""
import csv
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.abspath(__file__))
DATU_MAPE = os.environ.get("NHL_DATU_MAPE") or os.path.join(BASE, "dati")
KALENDARS = os.path.join(BASE, "nhl_kalendars.csv")
FAILS = os.path.join(DATU_MAPE, "tiesnesi_planotie.csv")
KOLONNAS = ["game_id", "sakums_utc", "home_team", "away_team", "loma", "vards", "atjaunots_utc", "avots"]

TRIGERA_STUNDAS = 6    # darbu sāk, ja kādai spēlei tuvāko tik stundu laikā nav tiesnešu (portāls ieraksta publicē ~4 h pirms pirmās spēles)
IEGUVES_STUNDAS = 30   # ielādes laikā tiek pārbaudītas visas spēles bez tiesnešiem tik stundu laikā
MIN_TIESNESI = 2       # spēle ir "aizpildīta", ja failā ir vismaz tik galvenie tiesneši
GLABAT_DIENAS = 2


def _laiks(teksts):
    try:
        return datetime.fromisoformat(str(teksts).replace("Z", "+00:00"))
    except ValueError:
        return None


def ielasit_kalendaru():
    if not os.path.isfile(KALENDARS):
        return []
    with open(KALENDARS, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def ielasit_esoso():
    if not os.path.isfile(FAILS):
        return []
    with open(FAILS, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def saglabat(rindas):
    os.makedirs(DATU_MAPE, exist_ok=True)
    with open(FAILS, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=KOLONNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rindas)


def speles_logaa(kalendars, tagad, stundas):
    """Spēles, kas vēl nav sākušās un sākas tuvāko `stundas` stundu laikā (hronoloģiski)."""
    out = []
    for r in kalendars:
        sak = _laiks(r.get("sakuma_laiks_utc"))
        if sak is not None and tagad <= sak <= tagad + timedelta(hours=stundas):
            out.append(r)
    return sorted(out, key=lambda r: r["sakuma_laiks_utc"])


def trukst_tiesnesu(speles, esosie):
    """Spēles, kurām failā vēl nav MIN_TIESNESI galveno tiesnešu."""
    skaits = {}
    for r in esosie:
        if r.get("loma") == "referee":
            skaits[str(r["game_id"])] = skaits.get(str(r["game_id"]), 0) + 1
    return [sp for sp in speles if skaits.get(str(sp["game_id"]), 0) < MIN_TIESNESI]


def nosaukums(sp):
    return f"{sp.get('viesu_komanda')} @ {sp.get('majas_komanda')} ({sp['game_id']})"


# ----------------------------------------------------------------------------
# ĀTRĀ PĀRBAUDE (tikai standarta bibliotēka, bez interneta)
# ----------------------------------------------------------------------------
def parbaude(tagad=None):
    tagad = tagad or datetime.now(timezone.utc)
    logs = speles_logaa(ielasit_kalendaru(), tagad, TRIGERA_STUNDAS)
    bez = trukst_tiesnesu(logs, ielasit_esoso())
    vajag = bool(bez)
    print(f"Spēles tuvāko {TRIGERA_STUNDAS} h laikā: {len(logs)}, bez paziņotiem tiesnešiem: {len(bez)}")
    for sp in bez:
        print(f"  – {nosaukums(sp)} sākas {sp['sakuma_laiks_utc']}")
    print("Ielāde vajadzīga." if vajag else "Ielāde nav vajadzīga.")
    izvade = os.environ.get("GITHUB_OUTPUT")
    if izvade:
        with open(izvade, "a", encoding="utf-8") as f:
            f.write(f"needed={'true' if vajag else 'false'}\n")
    return vajag


# ----------------------------------------------------------------------------
# SCOUTING THE REFS (scoutingtherefs.com)
# ----------------------------------------------------------------------------
STR_KATEGORIJA = "https://scoutingtherefs.com/category/tonights-officials/nhl-tonights-officials/"
STR_RX = re.compile(r"https://scoutingtherefs\.com/\d{4}/\d{2}/\d+/(?:tonights|todays)-nhl-(?:playoff-)?referees-and-linespersons-(\d{1,2})-(\d{1,2})-(\d{2})/?")
STR_UA = "Mozilla/5.0 (compatible; NHLStatsPersonal/1.0; personal non-commercial project)"

# komandu nosaukumi (kā tos raksta portāls); dublē datu_apstrade.KOMANDAS, lai skripts nebūtu atkarīgs no pandas
KOMANDU_NOSAUKUMI = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres", "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes",
    "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers", "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild",
    "MTL": "Montreal Canadiens", "NSH": "Nashville Predators", "NJD": "New Jersey Devils", "NYI": "New York Islanders",
    "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers", "PIT": "Pittsburgh Penguins",
    "SJS": "San Jose Sharks", "SEA": "Seattle Kraken", "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning",
    "TOR": "Toronto Maple Leafs", "UTA": "Utah Mammoth", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
    "WSH": "Washington Capitals", "WPG": "Winnipeg Jets",
}


def _norm(x):
    x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", x)).strip()


_NORM_NOS = {k: _norm(v) for k, v in KOMANDU_NOSAUKUMI.items()}


def komanda_no_teksta(teksts):
    """Komandas kods no nosaukuma (arī ar priedēkli, piem., 'Opening Night Florida Panthers'); None, ja nav atpazīta."""
    t = " " + _norm(teksts) + " "
    atrasti = [(len(n), k) for k, n in _NORM_NOS.items() if " " + n + " " in t]
    return max(atrasti)[1] if atrasti else None


class _TekstaParseris(HTMLParser):
    """Teksta izvilkšana no HTML. Tiek izlaists tikai <script>/<style> saturs; pārējais teksts (arī <head>/<noscript>) netiek izlaists,
    lai nepareizi noslēgti HTML elementi nevarētu "apēst" visu ieraksta tekstu."""
    BLOKI = {"p", "div", "li", "ul", "ol", "tr", "td", "th", "table", "br", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.dalas, self._izlaist = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._izlaist += 1
        if tag in self.BLOKI:
            self.dalas.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._izlaist = max(0, self._izlaist - 1)
        if tag in self.BLOKI:
            self.dalas.append("\n")

    def handle_data(self, data):
        if not self._izlaist:
            self.dalas.append(data)


def html_uz_rindam(html):
    """HTML → teksta rindas (bloka elementi atdala rindas, atstarpes sakārtotas). Darbojas arī ar parastu tekstu."""
    p = _TekstaParseris()
    p.feed(html)
    tekts = "".join(p.dalas).replace("\xa0", " ").replace("\u200b", "")
    return [re.sub(r"\s+", " ", r).strip() for r in tekts.split("\n") if r.strip()]


_VARDS = r"[A-Z][A-Za-z.'’\-]*(?: [A-Za-z.'’\-]+){0,3}"
_NOS_RX = "|".join(sorted((r"\s+".join(map(re.escape, v.split())) for v in KOMANDU_NOSAUKUMI.values()), key=len, reverse=True))
# spēles virsraksts: 'New York Rangers at Detroit Red Wings 6:30 PM ET' (komandu nosaukumi tiek meklēti tieši, tāpēc der arī priedēkļi, piem. 'Opening Night')
_ANTRAUKUMS = re.compile(r"(?P<away>" + _NOS_RX + r")\s+(?:at|@)\s+(?P<home>" + _NOS_RX + r")\s+\d{1,2}:\d{2}\s*[AP]M\s*ET", re.I)


def _bez_akcentiem(x):
    return "".join(c for c in unicodedata.normalize("NFKD", x) if not unicodedata.combining(c))


def _pari(teksts, sakums):
    """Divi vārdi no teikuma 'Referees X and Y are paired up…' / 'Linespersons X and Y are together…'."""
    m = re.search(sakums + r"\s+(" + _VARDS + r")\s+and\s+(" + _VARDS + r")\s+(?:are|have been)\s+(?:paired|together|teamed)", teksts)
    return [m.group(1).strip(), m.group(2).strip()] if m else []


def _vardi_ar_numuriem(teksts, no, lidz):
    """Rezerves variants: vārdi formā 'Vārds Uzvārds #14' starp virsrakstiem REFEREES un LINESPERSONS."""
    i = teksts.find(no)
    if i < 0:
        return []
    j = teksts.find(lidz, i + len(no)) if lidz else -1
    gabals = teksts[i + len(no): j if j > 0 else None]
    out = []
    for m in re.finditer(r"(" + _VARDS + r")\s+#\d+", gabals):
        v = m.group(1).strip()
        if v not in out:
            out.append(v)
    return out[:2]


def parse_str(html):
    """
    Scouting The Refs dienas ieraksta parsētājs. Atgriež {(viesi, majas): {"referees": [...], "linesmen": [...]}} ar komandu kodiem.
    Viss teksts tiek apvienots vienā virknē (rindu dalījums HTML nav svarīgs); katras spēles sadaļa sākas ar virsrakstu
    'Viesu komanda at Mājas komanda 7:00 PM ET', un tās beigās ir teikumi 'Referees X and Y are paired up…' un 'Linespersons X and Y are together…'.
    """
    teksts = _bez_akcentiem(" ".join(html_uz_rindam(html)))
    griezums = teksts.find("Games: PS")                       # lapas kājene (skaidrojumi, citi ieraksti)
    if griezums > 0:
        teksts = teksts[:griezums]
    sakumi = list(_ANTRAUKUMS.finditer(teksts))
    out = {}
    for n, m in enumerate(sakumi):
        a, h = komanda_no_teksta(m.group("away")), komanda_no_teksta(m.group("home"))
        if not a or not h:
            continue
        sekcija = teksts[m.end(): sakumi[n + 1].start() if n + 1 < len(sakumi) else len(teksts)]
        refs = _pari(sekcija, r"Referees") or _vardi_ar_numuriem(sekcija, "REFEREES", "LINESPERSONS")
        lins = _pari(sekcija, r"Linespersons") or _vardi_ar_numuriem(sekcija, "LINESPERSONS", None)
        out[(a, h)] = {"referees": refs, "linesmen": lins}
    return out


def diagnostika(html, n=700):
    """Īss ieraksta apraksts, ja spēles netiek atrastas (palīdz saprast, ko portāls atdod)."""
    rindas = html_uz_rindam(html or "")
    teksts = " ".join(rindas)
    print(f"  Diagnostika: HTML garums {len(html or '')}, teksta rindas {len(rindas)}, 'PM ET' reizes {len(re.findall(r'PM ET|AM ET', teksts))}, "
          f"'paired up' reizes {teksts.count('paired up')}, 'Referees' reizes {teksts.count('Referees')}")
    if re.search(r"just a moment|cf-chl|captcha|access denied|attention required", (html or "")[:6000], re.I):
        print("  Diagnostika: lapa izskatās pēc pretbotu aizsardzības (Cloudflare/captcha), nevis ieraksta.")
    i = teksts.find(" at ")
    print("  Diagnostika: teksta sākums:", teksts[:n // 2].replace("\n", " "))
    if i > 0:
        print("  Diagnostika: apkārt pirmajam ' at ':", teksts[max(0, i - 120): i + 200])


def _lejupieladet(url, meginajumi=2):
    import requests
    for i in range(1, meginajumi + 1):
        try:
            r = requests.get(url, headers={"User-Agent": STR_UA, "Accept-Language": "en"}, timeout=20)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:                      # lapas nav (piem., ieraksts vēl nav publicēts): nav jēgas atkārtot
                return None
            print(f"  Kļūda {r.status_code}: {url} (mēģinājums {i}/{meginajumi})")
        except requests.RequestException as e:
            print(f"  Savienojuma kļūda: {e} (mēģinājums {i}/{meginajumi})")
        time.sleep(2 * i)
    return None


def _str_saites(html):
    """{datums 'YYYY-MM-DD': ieraksta URL} no lapas HTML (datums ir ieraksta adreses beigās: m-d-gg)."""
    out = {}
    for m in STR_RX.finditer(html or ""):
        try:
            d = date(2000 + int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat()
        except ValueError:
            continue
        out.setdefault(d, m.group(0).rstrip("/") + "/")
    return out


def str_dati(datumi, lejupieladet=_lejupieladet):
    """
    Spēļu dienu (ASV datuma) tiesneši no Scouting The Refs. datumi: {'YYYY-MM-DD', ...}.
    Atgriež {datums: parse_str rezultāts}. Atrod ierakstu kategorijas lapā, rezerves variantā dienas arhīvā.
    """
    if not datumi:
        return {}
    saites = _str_saites(lejupieladet(STR_KATEGORIJA))
    try:
        from zoneinfo import ZoneInfo
        sodien_et = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        sodien_et = "9999-12-31"
    rezultats = {}
    for d in sorted(datumi):
        if d > sodien_et:                                  # ieraksts tiek publicēts spēļu dienā, nākamās dienas vēl nav
            print(f"  Scouting The Refs: ieraksts par {d} tiks publicēts šajā dienā (ASV laiks)")
            continue
        url = saites.get(d)
        if not url:                                   # rezerves variants: dienas arhīvs
            arhivs = lejupieladet(f"https://scoutingtherefs.com/date/{d.replace('-', '/')}/")
            url = _str_saites(arhivs).get(d)
        if not url:
            print(f"  Scouting The Refs: ieraksts par {d} vēl nav atrasts")
            continue
        html = lejupieladet(url)
        sp = parse_str(html) if html else {}
        print(f"  Scouting The Refs: {d}: atrastas {len(sp)} spēles ({url})")
        if not sp:
            diagnostika(html)
        rezultats[d] = sp
    return rezultats


# ----------------------------------------------------------------------------
# IELĀDE
# ----------------------------------------------------------------------------
def _nhl():
    import nhl_dati          # ielādē tikai tad, kad tiešām vajag internetu (requests)
    return nhl_dati


def tiesnesi_no_right_rail(rr):
    """[(loma, vārds), ...] (atslēgas 'referees' un 'linesmen' tiek meklētas jebkurā dziļumā)."""
    nhl = _nhl()
    out = []
    for loma, atsl in (("referee", "referees"), ("linesman", "linesmen")):
        for x in nhl.atrast_sarakstu(rr, atsl) or []:
            v = nhl.amatpersonas_vards(x)
            if v:
                out.append((loma, v))
    return out


def dzivie_tiesnesi(kalendars, esosie_id=(), stundas=IEGUVES_STUNDAS, tagad=None, lejupieladet=_lejupieladet):
    """
    Tiesneši spēlēm bez tiesnešiem, ielādēti tieši no Scouting The Refs (lietotnei: nav atkarīgs no GitHub Actions grafika).
    kalendars: DataFrame vai saraksts ar vārdnīcām (game_id, datums [ASV datums], majas_komanda, viesu_komanda, sakuma_laiks_utc).
    Atgriež rindu sarakstu tādā pašā formātā kā dati/tiesnesi_planotie.csv (avots 'ScoutingTheRefs'). Nekā nerakstī failos.
    """
    rindas = kalendars.to_dict("records") if hasattr(kalendars, "to_dict") else list(kalendars or [])
    tagad = tagad or datetime.now(timezone.utc)
    esosie_id = {int(x) for x in esosie_id}
    vajag = []
    for sp in rindas:
        t = _laiks(sp.get("sakuma_laiks_utc"))
        if t is None or int(sp["game_id"]) in esosie_id or not (tagad - timedelta(hours=1) <= t <= tagad + timedelta(hours=stundas)):
            continue
        vajag.append(sp)
    if not vajag:
        return []
    portals = str_dati({str(sp["datums"])[:10] for sp in vajag if sp.get("datums")}, lejupieladet=lejupieladet)
    atjaunots = tagad.strftime("%Y-%m-%d %H:%M")
    out = []
    for sp in vajag:
        s = portals.get(str(sp.get("datums"))[:10], {}).get((sp.get("viesu_komanda"), sp.get("majas_komanda")))
        if not s or not s["referees"]:
            continue
        for loma, vards in [("referee", v) for v in s["referees"]] + [("linesman", v) for v in s["linesmen"]]:
            out.append({"game_id": int(sp["game_id"]), "sakums_utc": sp["sakuma_laiks_utc"], "home_team": sp.get("majas_komanda"),
                        "away_team": sp.get("viesu_komanda"), "loma": loma, "vards": vards, "atjaunots_utc": atjaunots, "avots": "ScoutingTheRefs"})
    return out


def ielasit(stundas=IEGUVES_STUNDAS, visas=False, tagad=None, lejupieladet=_lejupieladet):
    nhl = _nhl()
    tagad = tagad or datetime.now(timezone.utc)
    esosie = ielasit_esoso()
    speles = speles_logaa(ielasit_kalendaru(), tagad, stundas)
    if not visas:
        speles = trukst_tiesnesu(speles, esosie)
    print(f"Pārbaudāmās spēles tuvāko {stundas} h laikā: {len(speles)}")

    atjaunots = tagad.strftime("%Y-%m-%d %H:%M")
    jaunas_rindas, atrasti, paraugs = {}, 0, None
    portals = str_dati({sp.get("datums") for sp in speles if sp.get("datums")}, lejupieladet=lejupieladet) if speles else {}
    for sp in speles:
        gid = sp["game_id"]
        avots, ties = "", []
        s = portals.get(sp.get("datums"), {}).get((sp.get("viesu_komanda"), sp.get("majas_komanda")))
        if s and s["referees"]:
            ties = [("referee", v) for v in s["referees"]] + [("linesman", v) for v in s["linesmen"]]
            avots = "ScoutingTheRefs"
        else:                                          # rezerves variants: NHL right-rail
            rr = nhl.get_json(f"{nhl.API_WEB}/gamecenter/{gid}/right-rail", meginajumi=2)
            time.sleep(nhl.KAVESANAS)
            if rr is None:
                print(f"  ✗ {nosaukums(sp)}: pieprasījums neizdevās")
                continue
            paraugs = paraugs or rr
            ties = tiesnesi_no_right_rail(rr)
            avots = "NHL"
        if not any(loma == "referee" for loma, _ in ties):
            print(f"  – {nosaukums(sp)}: tiesneši vēl nav paziņoti")
            continue
        atrasti += 1
        print(f"  ✓ {nosaukums(sp)}: {', '.join(v for l, v in ties if l == 'referee')} ({avots})")
        jaunas_rindas[gid] = [{"game_id": gid, "sakums_utc": sp["sakuma_laiks_utc"],
                               "home_team": sp.get("majas_komanda"), "away_team": sp.get("viesu_komanda"),
                               "loma": loma, "vards": v, "atjaunots_utc": atjaunots, "avots": avots} for loma, v in ties]

    # apvieno ar esošo: nemaina spēles, kurām tiesneši nav mainījušies; izmet vecās spēles
    robeza = tagad - timedelta(days=GLABAT_DIENAS)
    rezultats = []
    for r in esosie:
        sak = _laiks(r.get("sakums_utc"))
        if sak is not None and sak < robeza:
            continue
        if r["game_id"] in jaunas_rindas:
            vecie = {(x["loma"], x["vards"]) for x in esosie if x["game_id"] == r["game_id"]}
            jaunie = {(x["loma"], x["vards"]) for x in jaunas_rindas[r["game_id"]]}
            if vecie != jaunie:
                continue                      # tiks aizstāts ar jauno
            jaunas_rindas.pop(r["game_id"])   # nemainīgs: atstājam veco ierakstu
        rezultats.append(r)
    for rindas in jaunas_rindas.values():
        rezultats.extend(rindas)
    rezultats.sort(key=lambda r: (str(r["sakums_utc"]), str(r["game_id"]), 0 if r["loma"] == "referee" else 1))
    saglabat(rezultats)

    print(f"Tiesneši atrasti {atrasti} no {len(speles)} spēlēm. Failā kopā rindu: {len(rezultats)}.")
    if speles and atrasti == 0 and paraugs is not None:
        print("Piezīme: nevienai spēlei tiesnešu nav. right-rail augšējās atslēgas:", list(paraugs)[:15],
              "| gameInfo:", json.dumps(paraugs.get("gameInfo"), ensure_ascii=False)[:300])


def main():
    if "--parbaude" in sys.argv:
        parbaude()
        return
    stundas = IEGUVES_STUNDAS
    if "--stundas" in sys.argv:
        stundas = int(sys.argv[sys.argv.index("--stundas") + 1])
    ielasit(stundas=stundas, visas="--visas" in sys.argv)


if __name__ == "__main__":
    main()
