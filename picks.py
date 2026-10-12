"""
picks.py – "Picks": likmju atlase pēc vērtības (Expected Value), kā to dara profesionāls spēlētājs.

Algoritms NELIEK likmi uz katru spēli. Katrai nākamajai spēlei tas salīdzina Puasona modeļa varbūtības ar bukmeikeru
koeficientiem un atstāj tikai tās izvēles, kurām ir pietiekami liela ilgtermiņa matemātiskā vērtība un saprātīgs risks.

Ievaddati
  1. Modeļa varbūtības – {(tirgus, iznākums, līnija): varbūtība}; no modelis.prognoze() ar modela_varbutibas().
     Tirgi (tie paši nosaukumi kā sezonas/koeficienti.csv):
       "1x2" 1 / X / 2      – pamatlaikā (3 iznākumi)
       "ml"  1 / 2          – uzvarētājs ar papildlaiku un metienu sēriju
       "tot" over / under   – kopējie vārti pilnā spēlē (ar OT; metienu sērijas uzvara = +1 vārti, kā bukmeikeriem)
       "pm"  1 / 2 ar ±1.5  – handikaps pilnā spēlē (OT/SO uzvara vienmēr ir ar 1 vārtu starpību)
  2. Bukmeikeru koeficienti – sezonas/koeficienti.csv rindas (bukmeikers, tirgus, iznakums, linija, koef).
  3. Papildu (neobligāti) – `papildu` = {(tirgus, iznākums, līnija): ±procentpunkti}, piem., traumu vai noraidījumu ietekme,
     ko modelis vēl nezina. Tiek pieskaitīts modeļa varbūtībai pirms vērtības aprēķina (ar robežām 1–99%).

Lēmuma soļi (katrai izvēlei)
  1. Implied probability = 1 / koeficients (ko "paredz" bukmeikers, ar uzcenojumu).
     Tirgus taisnīgā varbūtība = Pinnacle (asākais tirgus) bez uzcenojuma; ja Pinnacle nav – vidējais bez uzcenojuma.
  2. Koeficients likmei = labākais ES bukmeikeru koeficients ("line shopping"), bet ne augstāks par Pinnacle + 10 %
     (lielāka atšķirība parasti nozīmē novecojušu vai kļūdainu koeficientu, ko nevarēs nolikt).
  3. Lēmuma varbūtība p = svars × modelis + (1 − svars) × tirgus (taisnīgā). Modelis tiek "pievilkts" pie tirgus tur, kur tas
     ir mazāk precīzs par tirgu: uzvarētāja tirgiem (1X2 pamatlaikā, ar OT, ±1.5) svars 0.5 – modelis sistemātiski vērtē
     autsaiderus augstāk par tirgu, un visi trīs tirgi nāk no tā paša vārtu sadalījuma (ja pievilktu tikai 1X2, tā pati
     kļūda pārceltos uz ar OT un ±1.5). Totāliem svars 1.0. Ja tirgus atsauces nav, p = modelis.
     EV = p × (koef − 1) − (1 − p)   (= p × koef − 1).
  4. Filtri:
       EV ≥ min_ev (noklusējums 4 %);
       p ≥ min_p (15 %) – nekādu "brīnumu" ar mazu varbūtību (liela dispersija);
       koef ≤ max_koef (6.0) – tas pats no otras puses;
       |p − tirgus| ≤ max_novirze (12 pp) – ja modelis ļoti nesaskan ar asāko tirgu, visticamāk modelis nezina kaut ko
         (trauma, sastāvs), nevis tirgus kļūdās – šādas "vērtības" profesionāļi neņem;
       p ≥ tirgus – modelim jābūt optimistiskākam par taisnīgo tirgu (citādi EV rodas tikai no "labākā" koeficienta).
  5. Vārtsargi: pick tiek atlasīts tikai, kad abu komandu sākuma vārtsargi ir paziņoti (Confirmed vai Expected) –
     NHL tas ir būtiskākais faktors pirms spēles, un bez tā modelis var rēķināt ar nepareizo vārtsargu.
  6. Korelācija: vienā spēlē tikai max_uz_speli izvēles (noklusējums 1, ar lielāko EV) – 1X2, ML un ±1.5 uz to pašu komandu
     ir viena un tā pati likme dažādos veidos.
  7. Likmes lielums – Kelly kritērijs f* = (p × koef − 1) / (koef − 1), ņemta tikai daļa (¼ Kelly), pareizināta ar modeļa
     ticamību (Augsta 1.0 / Vidēja 0.75 / Zema 0.5), robežās 1–5 % no bankrola. Ja vienas dienas likmju summa pārsniedz
     max_dienas_risks (15 %), visas tās dienas likmes proporcionāli samazina.

Vēsture (sezonas/picks_arhivs.csv)
  Darbplūsma "NHL Odds" pēc katras koeficientu ielādes (python prognozes_arhivs.py) atlasītos picks pievieno arhīvam
  (izvēle tiek saglabāta pirmajā ielādē, kad tā izturēja filtrus, ar tā brīža koeficientu – vēlāk netiek mainīta).
  Kamēr spēle nav sākusies, katrā ielādē tiek atjaunināti tikai "noslēguma" dati: labākais koeficients (koef_nosl) un tirgus
  taisnīgā varbūtība (p_tirgus_nosl). CLV = koef × p_tirgus_nosl − 1: vai mūsu koeficients bija labāks par tirgus taisnīgo
  koeficientu tieši pirms spēles (profesionāļu galvenais rādītājs – ilgtermiņā pozitīvs CLV nozīmē reālu priekšrocību).
  Rezultātu lietotne pieliek no sezonas/speles.csv, tāpēc vēsture pati papildinās līdz ar aizvadītajām spēlēm.

Vēsturiskā pārbaude (lokāli, pēc python vesturiskie_koef.py)
  python picks.py --parbaude
  Katrai iepriekšējo sezonu spēlei modeļa prognoze tikai no datiem pirms tās (walk-forward, kā modelis.py --kalibret),
  salīdzināta ar tā laika ASV bukmeikeru noslēguma koeficientiem (uzvarētājs ar OT, totāli, ±1.5). Katram tirgum tiek
  izvēlēts modeļa svars un min. EV uz vecākajām sezonām un godīgi pārbaudīts uz jaunākās. Tirgi, kas vēsturē nebija pelnoši,
  tiek izslēgti. Rezultāts: sezonas/vesture/picks_parametri.json – to automātiski nolasa lietotne un prognozes_arhivs.py.

Komandrinda (lokāli):
  python picks.py --no-arhiva   → izveido / papildina vēsturi no jau saglabātā prognožu arhīva (1X2 un galvenais totāls)
  python picks.py --parbaude    → vēsturiskā pārbaude un parametru izvēle (skat. augstāk)
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
FAILS = os.path.join(BASE, "sezonas", "picks_arhivs.csv")
PARAMETRU_FAILS = os.path.join(BASE, "sezonas", "vesture", "picks_parametri.json")
VARTSARGI_ZINAMI = ("Confirmed", "Expected")      # Daily Faceoff statusi, ar kuriem vārtsargs uzskatāms par paziņotu

NOKLUSETIE = {
    "min_ev": 0.04,             # vismaz +4 % EV
    "min_p": 0.15,              # modeļa varbūtība vismaz 15 %
    "max_koef": 6.0,            # ne augstāki koeficienti
    "max_novirze": 0.12,        # modelis pret tirgu (bez uzcenojuma) ne vairāk par 12 pp
    "labakais_max": 0.10,       # labākais koeficients ne vairāk kā +10 % virs Pinnacle (citādi – aizdomīgs)
    "max_uz_speli": 1,          # izvēles vienā spēlē (korelācija)
    "kelly_dala": 0.25,         # ¼ Kelly
    "min_likme": 0.01,          # 1 % bankrola
    "max_likme": 0.05,          # 5 % bankrola
    "max_dienas_risks": 0.15,   # vienas dienas likmes kopā ne vairāk par 15 % bankrola
    "ticamibas_k": {"Augsta": 1.0, "Vidēja": 0.75, "Zema": 0.5},
    "tirgi": ("1x2", "ml", "tot", "pm"),
    "modela_svars": {"1x2": 0.5, "ml": 0.5, "tot": 1.0, "pm": 0.5},   # lēmuma p = svars × modelis + (1 − svars) × tirgus
    "prasit_vartsargus": True,  # pick tikai ar paziņotiem abu komandu sākuma vārtsargiem
}
PARBAUDE = None                 # vēsturiskās pārbaudes rezultāts (picks_parametri.json), ja tāds ir


def ielasit_parametrus(fails=PARAMETRU_FAILS):
    """Vēsturiskās pārbaudes izvēlētie parametri (modeļa svars, min. EV pa tirgiem, ieslēgtie tirgi) → NOKLUSETIE."""
    global PARBAUDE
    if not os.path.exists(fails):
        return None
    try:
        with open(fails, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    par = d.get("parametri") or {}
    if isinstance(par.get("modela_svars"), dict):
        NOKLUSETIE["modela_svars"] = {**NOKLUSETIE["modela_svars"], **par["modela_svars"]}
    if isinstance(par.get("min_ev"), (dict, float, int)):
        NOKLUSETIE["min_ev"] = par["min_ev"]
    if isinstance(par.get("tirgi"), list):
        NOKLUSETIE["tirgi"] = tuple(par["tirgi"])
    if isinstance(par.get("max_likme"), (dict, float, int)):
        NOKLUSETIE["max_likme"] = par["max_likme"]
    PARBAUDE = d
    return d


def _min_ev(c, tirgus):
    """min_ev var būt viens skaitlis vai {tirgus: skaitlis}."""
    m = c["min_ev"]
    return float(m.get(tirgus, 0.04)) if isinstance(m, dict) else float(m)

BANKROLLS = 1000.0              # virtuālais sākuma bankrolls vēsturē (vienības)

KOLONNAS = ["game_id", "ielade", "sakums_utc", "majas", "viesi", "tirgus", "iznakums", "linija", "izvele", "koef", "bukmeikers",
            "koef_pin", "p_modelis", "p_lemums", "p_tirgus", "implied", "ev", "kelly", "likme_pct", "ticamiba", "avots", "koef_nosl", "p_tirgus_nosl",
            "nosl_ielade", "vartsargi"]
TIRGU_NOS = {"1x2": "Pamatlaikā", "ml": "Uzvarētājs (ar OT)", "tot": "Totāls (ar OT)", "pm": "±1.5 (ar OT)"}


# ----------------------------------------------------------------------------
# PAMATFORMULAS
# ----------------------------------------------------------------------------
def implied(koef):
    """Bukmeikera paredzētā varbūtība (ar uzcenojumu)."""
    return 1.0 / float(koef) if koef and float(koef) > 1 else float("nan")


def bez_uzcenojuma(koefs):
    """{iznākums: koef} → {iznākums: taisnīgā varbūtība} (proporcionāli noņemts uzcenojums). None, ja kāda trūkst."""
    try:
        inv = {k: 1.0 / float(v) for k, v in koefs.items() if v is not None and np.isfinite(v) and float(v) > 1}
    except (TypeError, ValueError):
        return None
    s = sum(inv.values())
    if len(inv) != len(koefs) or len(inv) < 2 or s <= 0:
        return None
    return {k: v / s for k, v in inv.items()}


def ev(p, koef):
    """Expected Value uz 1 likmes vienību: p × (koef − 1) − (1 − p)."""
    return p * (koef - 1.0) - (1.0 - p)


def kelly(p, koef):
    """Pilnais Kelly: bankrola daļa f* = (p × koef − 1) / (koef − 1); ≤ 0 → nelikt."""
    return (p * koef - 1.0) / (koef - 1.0) if koef > 1 else 0.0


def _max_likme(c, tirgus):
    """max_likme var būt viens skaitlis vai {tirgus: skaitlis} (piem., novērošanas režīmā tirgum mazāka likme)."""
    m = c["max_likme"]
    return float(m.get(tirgus, 0.05)) if isinstance(m, dict) else float(m)


def likmes_dala(p, koef, ticamiba=None, cfg=None, tirgus=None):
    """Ieteicamā bankrola daļa: ¼ Kelly × ticamība, robežās min_likme … max_likme (0, ja Kelly ≤ 0)."""
    c = {**NOKLUSETIE, **(cfg or {})}
    f = kelly(p, koef)
    if f <= 0:
        return 0.0
    f *= c["kelly_dala"] * c["ticamibas_k"].get(ticamiba, 0.75)
    mx = _max_likme(c, tirgus)
    return float(min(mx, max(min(c["min_likme"], mx), f)))


def izveles_nosaukums(tirgus, izn, lin, majas, viesi):
    """Saprotams izvēles teksts, piem., 'BOS uzvara pamatlaikā', 'Over 5.5', 'UTA +1.5'."""
    if tirgus == "1x2":
        return {"1": f"{majas} uzvara pamatlaikā", "X": "Neizšķirts pamatlaikā", "2": f"{viesi} uzvara pamatlaikā"}[str(izn)]
    if tirgus == "ml":
        return f"{majas if str(izn) == '1' else viesi} uzvara (ar OT)"
    if tirgus == "tot":
        return f"{'Over' if izn == 'over' else 'Under'} {lin:g}"
    if tirgus == "pm":
        return f"{majas if str(izn) == '1' else viesi} {lin:+.1f}".replace("-", "−")
    return f"{tirgus} {izn} {lin}"


# ----------------------------------------------------------------------------
# MODEĻA VARBŪTĪBAS NO modelis.prognoze()
# ----------------------------------------------------------------------------
def _lin(v):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), 2)


def modela_varbutibas(pr, koef_rindas):
    """
    Modeļa varbūtības visām izvēlēm, kurām ir koeficienti: {(tirgus, iznākums, līnija): p}.
    pr – modelis.prognoze() rezultāts; koef_rindas – vienas spēles koeficientu rindas.
    """
    import modelis                                                  # tikai šeit (darbplūsmai un lietotnei tas ir pieejams)
    out = {}
    for (tirgus, izn, lin), _ in koef_rindas.groupby(["tirgus", "iznakums", koef_rindas["linija"].map(_lin)], dropna=False):
        izn, lin = str(izn), _lin(lin)
        p = None
        if tirgus == "1x2" and izn in ("1", "X", "2"):
            p = pr["1x2"][izn]
        elif tirgus == "ml" and izn in ("1", "2"):
            p = pr["ar_ot"][izn]
        elif tirgus == "tot" and lin is not None:
            o = modelis.pilnas_speles_over(pr, float(lin))              # veselām līnijām (6.0) – None (naudas atgriešana)
            p = None if o is None else (o if izn == "over" else 1.0 - o)
        elif tirgus == "pm" and lin is not None and abs(abs(lin) - 1.5) < 1e-9:
            atsl = f"{izn} {'−' if lin < 0 else '+'}1.5"
            p = pr.get("plus_minus", {}).get(atsl)
        if p is not None and np.isfinite(p):
            out[(tirgus, izn, lin)] = float(p)
    return out


# ----------------------------------------------------------------------------
# KANDIDĀTI UN ATLASE
# ----------------------------------------------------------------------------
def _pretejie(tirgus, izn, lin):
    """Visi viena tirgus iznākumi (ar līnijām), lai noņemtu uzcenojumu: [(izn, lin), ...]."""
    if tirgus == "1x2":
        return [("1", None), ("X", None), ("2", None)]
    if tirgus == "ml":
        return [("1", None), ("2", None)]
    if tirgus == "tot":
        return [("over", lin), ("under", lin)]
    if tirgus == "pm":                                   # mājinieki −1.5 ↔ viesi +1.5 (un otrādi)
        return [("1", lin), ("2", -lin)] if str(izn) == "1" else [("1", -lin), ("2", lin)]
    return [(izn, lin)]


def kandidati(game, probs, koef_rindas, cfg=None, papildu=None):
    """
    Visas vienas spēles izvēles ar aprēķiniem (arī neizturējušās – ar iemeslu).
    game: {game_id, sakums_utc, majas, viesi, ticamiba}; probs: modela_varbutibas(); koef_rindas: spēles koeficienti.
    """
    c = {**NOKLUSETIE, **(cfg or {})}
    k = koef_rindas.copy()
    k["iznakums"] = k["iznakums"].astype(str)
    k["lin_"] = pd.to_numeric(k["linija"], errors="coerce").round(2)
    k = k[k["koef"].notna() & (k["koef"] > 1)]

    def koefi(tirgus, izn, lin):
        lm = k["lin_"].isna() if lin is None else (k["lin_"] - lin).abs() < 1e-9      # 1X2 / ML – bez līnijas
        return k[(k["tirgus"] == tirgus) & (k["iznakums"] == izn) & lm]

    out = []
    for (tirgus, izn, lin), p in probs.items():
        if tirgus not in c["tirgi"]:
            continue
        y = koefi(tirgus, izn, lin)
        if y.empty:
            continue
        p0 = p
        if papildu and (tirgus, izn, lin) in papildu:                   # papildu informācija (traumas u.c.), procentpunktos
            p = min(0.99, max(0.01, p + float(papildu[(tirgus, izn, lin)]) / 100.0))
        # tirgus taisnīgā varbūtība: Pinnacle bez uzcenojuma, citādi vidējie koeficienti bez uzcenojuma
        visi = _pretejie(tirgus, izn, lin)
        pin = {i: koefi(tirgus, i, l_)[lambda d: d["bukmeikers"] == "pinnacle"]["koef"] for i, l_ in visi}
        if all(len(v) for v in pin.values()):
            tv = bez_uzcenojuma({i: float(v.iloc[0]) for i, v in pin.items()})
            avots_t = "Pinnacle"
        else:
            tv = bez_uzcenojuma({i: float(koefi(tirgus, i, l_)["koef"].mean()) if len(koefi(tirgus, i, l_)) else np.nan for i, l_ in visi})
            avots_t = "vidējais"
        p_t = tv.get(izn) if tv else float("nan")
        k_pin = y[y["bukmeikers"] == "pinnacle"]["koef"]
        k_pin = float(k_pin.iloc[0]) if len(k_pin) else float("nan")
        # koeficients likmei: labākais, bet ne aizdomīgi augsts pret Pinnacle (vai pret tirgus taisnīgo, ja Pinnacle nav)
        robeza = (k_pin if np.isfinite(k_pin) else (1 / p_t if p_t and np.isfinite(p_t) else np.inf)) * (1 + c["labakais_max"])
        derigi = y[y["koef"] <= robeza]
        if derigi.empty:
            derigi = y
        r = derigi.loc[derigi["koef"].idxmax()]
        o = float(r["koef"])
        ir_tirgus = p_t is not None and np.isfinite(p_t)
        w = float(c["modela_svars"].get(tirgus, 1.0))
        pl = w * p + (1 - w) * p_t if ir_tirgus else p              # lēmuma varbūtība (modelis pievilkts pie tirgus)
        e = ev(pl, o)
        iemesls = ""
        if not ir_tirgus:
            iemesls = "nav tirgus atsauces (trūkst pretējā iznākuma koeficienta)"
        elif e < _min_ev(c, tirgus):
            iemesls = f"EV {e * 100:+.1f}% < {_min_ev(c, tirgus) * 100:.0f}%"
        elif pl < c["min_p"]:
            iemesls = f"varbūtība {pl * 100:.0f}% < {c['min_p'] * 100:.0f}%"
        elif o > c["max_koef"]:
            iemesls = f"koeficients {o:.2f} > {c['max_koef']:g}"
        elif abs(p - p_t) > c["max_novirze"]:
            iemesls = f"modelis pret tirgu {(p - p_t) * 100:+.0f} pp – pārāk liela atšķirība"
        elif pl < p_t:
            iemesls = "modelis nav optimistiskāks par tirgu"
        elif c.get("prasit_vartsargus") and game.get("vartsargi") is not None \
                and not all(str(v) in VARTSARGI_ZINAMI for v in game["vartsargi"]):
            iemesls = "der, bet gaida paziņotus sākuma vārtsargus"
        out.append({
            "game_id": int(game["game_id"]), "sakums_utc": game.get("sakums_utc"), "majas": game["majas"], "viesi": game["viesi"],
            "tirgus": tirgus, "iznakums": izn, "linija": lin, "izvele": izveles_nosaukums(tirgus, izn, lin, game["majas"], game["viesi"]),
            "koef": o, "bukmeikers": str(r["bukmeikers"]), "koef_pin": k_pin, "p_modelis": float(p), "p_modelis_bez_papildu": float(p0),
            "p_lemums": float(pl), "modela_svars": w,
            "p_tirgus": float(p_t) if p_t is not None else float("nan"), "tirgus_avots": avots_t, "implied": implied(o), "ev": float(e),
            "kelly": float(kelly(pl, o)), "ticamiba": game.get("ticamiba"), "iemesls": iemesls, "der": iemesls == "",
            "vartsargi": "/".join(str(v or "–") for v in game["vartsargi"]) if game.get("vartsargi") is not None else "",
        })
    return out


def atlasit(kand, cfg=None):
    """
    No visiem kandidātiem atstāj tikai picks: izturējuši filtrus, max_uz_speli katrā spēlē (lielākais EV),
    likmes lielums pēc ¼ Kelly × ticamība (1–5 %), dienas riska robeža. Atgriež DataFrame (lielākais EV augšā).
    """
    c = {**NOKLUSETIE, **(cfg or {})}
    d = pd.DataFrame([x for x in kand if x.get("der")])
    if d.empty:
        return d
    d = d.sort_values("ev", ascending=False).groupby("game_id", sort=False).head(int(c["max_uz_speli"])).copy()
    d["likme_pct"] = [likmes_dala(p, o, t, c, tg) for p, o, t, tg in zip(d["p_lemums"], d["koef"], d["ticamiba"], d["tirgus"])]
    d = d[d["likme_pct"] > 0]
    if d.empty:
        return d
    diena = pd.to_datetime(d["sakums_utc"], utc=True, errors="coerce").dt.tz_convert("America/New_York").dt.date
    kopa = d.groupby(diena)["likme_pct"].transform("sum")
    d["likme_pct"] = np.where(kopa > c["max_dienas_risks"], d["likme_pct"] * c["max_dienas_risks"] / kopa, d["likme_pct"])
    return d.sort_values(["ev"], ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------------
# ARHĪVS (vēsture)
# ----------------------------------------------------------------------------
def ielasit_arhivu(fails=FAILS):
    if not os.path.exists(fails):
        return pd.DataFrame(columns=KOLONNAS)
    d = pd.read_csv(fails)
    d["iznakums"] = d["iznakums"].astype(str)
    return d


def atjaunot_arhivu(picks_df, visi_kandidati, ielade, tagad=None, fails=FAILS, avots="ielāde", cfg=None):
    """
    Pievieno jaunos picks arhīvam un atjaunina noslēguma koeficientus vēl nesāktajām spēlēm.
    picks_df – atlasit() rezultāts šai ielādei; visi_kandidati – visu izvēļu saraksts (noslēguma koeficientiem).
    Izvēle, kas jau ir arhīvā, netiek mainīta (izņemot koef_nosl). Spēlē, kurai jau ir max_uz_speli picks, jauni netiek pievienoti.
    """
    c = {**NOKLUSETIE, **(cfg or {})}
    tagad = tagad or pd.Timestamp.now(tz="UTC")
    a = ielasit_arhivu(fails)
    atsl = lambda r: (int(r["game_id"]), str(r["tirgus"]), str(r["iznakums"]), _lin(r["linija"]))   # noqa: E731
    # 1) noslēguma dati (pēdējā ielāde pirms spēles) jau esošajiem picks: labākais koeficients un tirgus taisnīgā varbūtība
    if not a.empty and visi_kandidati:
        nosl = {atsl(x): (x["koef"], x["p_tirgus"]) for x in visi_kandidati}
        sak = pd.to_datetime(a["sakums_utc"], utc=True, errors="coerce")
        for i in a.index[sak > tagad]:
            v = nosl.get(atsl(a.loc[i]))
            if v is not None:
                a.loc[i, "koef_nosl"] = round(float(v[0]), 3)
                a.loc[i, "p_tirgus_nosl"] = round(float(v[1]), 5) if np.isfinite(v[1]) else np.nan
                a.loc[i, "nosl_ielade"] = ielade
    # 2) jaunie picks
    jaunie = []
    if picks_df is not None and not picks_df.empty:
        esosie = {atsl(r) for _, r in a.iterrows()}
        skaits = a.groupby("game_id").size().to_dict() if not a.empty else {}
        for _, r in picks_df.iterrows():
            if atsl(r) in esosie or skaits.get(int(r["game_id"]), 0) >= int(c["max_uz_speli"]):
                continue
            skaits[int(r["game_id"])] = skaits.get(int(r["game_id"]), 0) + 1
            jaunie.append({**{k: r.get(k) for k in KOLONNAS if k in r}, "ielade": ielade, "avots": avots,
                           "koef_nosl": r.get("koef"), "p_tirgus_nosl": r.get("p_tirgus"), "nosl_ielade": ielade})
    if jaunie:
        a = pd.concat([a, pd.DataFrame(jaunie)], ignore_index=True)
    a = a.reindex(columns=KOLONNAS)
    for kol, dec in (("koef", 3), ("koef_pin", 3), ("p_modelis", 5), ("p_lemums", 5), ("p_tirgus", 5), ("implied", 5), ("ev", 5), ("kelly", 5), ("likme_pct", 5),
                     ("koef_nosl", 3), ("p_tirgus_nosl", 5)):
        a[kol] = pd.to_numeric(a[kol], errors="coerce").round(dec)
    os.makedirs(os.path.dirname(fails), exist_ok=True)
    a.sort_values(["sakums_utc", "game_id", "ielade"]).to_csv(fails, index=False)
    return len(jaunie), len(a)


# ----------------------------------------------------------------------------
# REZULTĀTI (picks pret realitāti)
# ----------------------------------------------------------------------------
def izverte(r, s):
    """
    Viena pick iznākums pēc spēles rezultāta: 'W' (uzvara), 'L' (zaudējums), 'P' (naudas atgriešana) vai None (nav rezultāta).
    s – spēles rinda ar hg, ag (pamatlaiks) un h_tot, a_tot (gala rezultāts ar OT/SO, kā bukmeikeriem).
    """
    if s is None or pd.isna(s.get("h_tot")) or pd.isna(s.get("a_tot")):
        return None
    t, izn, lin = r["tirgus"], str(r["iznakums"]), r["linija"]
    if t == "1x2":
        fakts = "1" if s["hg"] > s["ag"] else ("X" if s["hg"] == s["ag"] else "2")
        return "W" if izn == fakts else "L"
    if t == "ml":
        return "W" if (izn == "1") == (s["h_tot"] > s["a_tot"]) else "L"
    if t == "tot":
        kopa, lin = s["h_tot"] + s["a_tot"], float(lin)
        if kopa == lin:
            return "P"
        return "W" if (kopa > lin) == (izn == "over") else "L"
    if t == "pm":
        starp = (s["h_tot"] - s["a_tot"]) if izn == "1" else (s["a_tot"] - s["h_tot"])
        v = starp + float(lin)
        return "P" if v == 0 else ("W" if v > 0 else "L")
    return None


def rezultati(arhivs, speles):
    """
    Pievieno arhīvam rezultātu: rezultats (W/L/P/None), gala (rezultāts tekstā), pelna_vien (uz 1 vienību),
    pelna_bank (vienībās, likme = likme_pct × BANKROLLS), clv (koef × p_tirgus_nosl − 1: mūsu koeficients pret tirgus taisnīgo pirms spēles).
    speles: game_id, home_total, away_total, home_p1..p3, away_p1..p3, spele_beidzas.
    """
    if arhivs is None or arhivs.empty:
        return pd.DataFrame(columns=KOLONNAS + ["rezultats", "gala", "pelna_vien", "pelna_bank", "clv"])
    a = arhivs.copy()
    sp = {}
    if speles is not None and not speles.empty:
        for r in speles.itertuples(index=False):
            if pd.isna(r.home_total) or pd.isna(r.away_total):
                continue
            hg = sum(float(getattr(r, f"home_p{i}") or 0) for i in (1, 2, 3))
            ag = sum(float(getattr(r, f"away_p{i}") or 0) for i in (1, 2, 3))
            b = str(getattr(r, "spele_beidzas", "REG") or "REG").upper()
            sp[int(r.game_id)] = {"hg": hg, "ag": ag, "h_tot": float(r.home_total), "a_tot": float(r.away_total),
                                  "gala": f"{int(r.home_total)}:{int(r.away_total)}" + ("" if b == "REG" else f" {b}")}
    rez, gala = [], []
    for _, r in a.iterrows():
        s = sp.get(int(r["game_id"]))
        rez.append(izverte(r, s))
        gala.append(s["gala"] if s else "")
    a["rezultats"], a["gala"] = rez, gala
    o = pd.to_numeric(a["koef"], errors="coerce")
    a["pelna_vien"] = np.select([a["rezultats"] == "W", a["rezultats"] == "L", a["rezultats"] == "P"], [o - 1, -1.0, 0.0], default=np.nan)
    a["likme_vien"] = pd.to_numeric(a["likme_pct"], errors="coerce") * BANKROLLS
    a["pelna_bank"] = a["pelna_vien"] * a["likme_vien"]
    a["clv"] = o * pd.to_numeric(a["p_tirgus_nosl"], errors="coerce") - 1
    return a


def kopsavilkums(a):
    """Vēstures kopsavilkums no rezultati(): likmes, uzvaras, ROI (vienādas likmes), bankrola peļņa (Kelly likmes), vidējais EV un CLV."""
    x = a[a["rezultats"].isin(["W", "L", "P"])] if a is not None and not a.empty else pd.DataFrame()
    if x.empty:
        return {"likmes": 0, "gaida": int(a["rezultats"].isna().sum()) if a is not None and not a.empty else 0}
    lik = x["likme_vien"].sum()
    return {
        "likmes": len(x), "uzvaras": int((x["rezultats"] == "W").sum()), "zaud": int((x["rezultats"] == "L").sum()),
        "atgriezti": int((x["rezultats"] == "P").sum()), "gaida": int(a["rezultats"].isna().sum()),
        "roi_vien": float(x["pelna_vien"].mean()), "pelna_vien": float(x["pelna_vien"].sum()),
        "pelna_bank": float(x["pelna_bank"].sum()), "roi_bank": float(x["pelna_bank"].sum() / lik) if lik else float("nan"),
        "vid_koef": float(x["koef"].mean()), "vid_ev": float(x["ev"].mean()),
        "vid_p": float(x["p_lemums"].fillna(x["p_modelis"]).mean() if "p_lemums" in x else x["p_modelis"].mean()),
        "clv": float(x["clv"].mean()) if x["clv"].notna().any() else float("nan"),
        "clv_poz": float((x["clv"] > 0).mean()) if x["clv"].notna().any() else float("nan"),
    }


# ----------------------------------------------------------------------------
# VĒSTURE NO PROGNOŽU ARHĪVA (vienreiz / lokāli): 1X2 un galvenais totāls katrā ielādē
# ----------------------------------------------------------------------------
def no_prognozu_arhiva(prog, cfg=None, fails=FAILS):
    """
    Izveido picks vēsturi no sezonas/prognozes_arhivs.csv (modeļa varbūtības un koeficienti, kas saglabāti PIRMS spēlēm).
    Ielādes tiek apstrādātas hronoloģiski, kā tās būtu notikušas darbplūsmā. Tirgi: 1X2 pamatlaikā un galvenais totāls (ar OT).
    """
    if prog is None or prog.empty:
        return 0, 0
    pievienoti = 0
    for ielade, grupa in prog.sort_values("ielade").groupby("ielade", sort=True):
        visi, kand = [], []
        for _, r in grupa.iterrows():
            rindas = []
            for i in ("1", "X", "2"):
                for bk, kol in (("pinnacle", f"pin_{i}"), ("labakais", f"lab_{i}")):
                    if pd.notna(r.get(kol)):
                        rindas.append({"bukmeikers": bk, "tirgus": "1x2", "iznakums": i, "linija": np.nan, "koef": float(r[kol])})
            lin = r.get("tot_linija")
            if pd.notna(lin) and pd.notna(r.get("m_over")):
                for i in ("over", "under"):
                    for bk, kol in (("pinnacle", f"pin_{i}"), ("labakais", f"lab_{i}")):
                        if pd.notna(r.get(kol)):
                            rindas.append({"bukmeikers": bk, "tirgus": "tot", "iznakums": i, "linija": float(lin), "koef": float(r[kol])})
            if not rindas:
                continue
            probs = {("1x2", i, None): float(r[f"m_{i}"]) for i in ("1", "X", "2") if pd.notna(r.get(f"m_{i}"))}
            if pd.notna(lin) and pd.notna(r.get("m_over")):
                probs[("tot", "over", _lin(lin))] = float(r["m_over"])
                probs[("tot", "under", _lin(lin))] = 1.0 - float(r["m_over"])
            game = {"game_id": r["game_id"], "sakums_utc": r["sakums_utc"], "majas": r["majas"], "viesi": r["viesi"],
                    "ticamiba": r.get("ticamiba")}
            kk = kandidati(game, probs, pd.DataFrame(rindas), cfg)
            visi += kk
            kand += kk
        n, _ = atjaunot_arhivu(atlasit(kand, cfg), visi, ielade, tagad=pd.Timestamp(ielade), fails=fails, avots="prognožu arhīvs", cfg=cfg)
        pievienoti += n
    return pievienoti, len(ielasit_arhivu(fails))



# ----------------------------------------------------------------------------
# VĒSTURISKĀ PĀRBAUDE (backtest) ar iepriekšējo sezonu koeficientiem (vesturiskie_koef.py)
# ----------------------------------------------------------------------------
PARB_SVARI = (0.25, 0.5, 0.75, 1.0)                    # modeļa svars (lēmuma p = svars × modelis + (1 − svars) × tirgus)
PARB_MIN_EV = (0.02, 0.03, 0.04, 0.05, 0.07, 0.10)
PARB_MIN_LIKMES = 100                                   # parametru izvēlei vajag vismaz tik likmju apmācības sezonās
PARB_TIRGI = ("ml", "tot", "pm")
NOKLUSETIE_MAX_LIKME = 0.05
NOVEROSANAS_MAX_LIKME = 0.02                            # tirgus "novērošanas" režīmā: max 2 % bankrola                        # 1X2 pamatlaikā ASV koeficientos nav – tas seko "ml" lēmumam


def _vesturiskie_koeficienti(sezona):
    c = os.path.join(BASE, "sezonas", "vesture", str(sezona), "koeficienti_vesture.csv")
    if not os.path.exists(c):
        return None
    d = pd.read_csv(c)
    d["iznakums"] = d["iznakums"].astype(str)
    d["linija"] = pd.to_numeric(d["linija"], errors="coerce")
    for k in ("koef", "koef_atv"):
        d[k] = pd.to_numeric(d[k], errors="coerce")
    return d


def vesturiskas_prognozes(sezonas, solis_dienas=3, test_sezona=None):
    """
    Walk-forward prognozes (tikai no datiem pirms katras spēles) katrai norādīto sezonu spēlei, ar tiem pašiem datiem kā lietotnē
    (vārti + xG, faktiskie sākuma vārtsargi, atpūta, ceļš). Atgriež ({game_id: prognoze}, info).
    Bez noplūdes no pārbaudes sezonas (test_sezona):
      - modeļa iestatījumi – "parametri_parbaudei" no modelis_parametri.json (kalibrēti BEZ pārbaudes sezonas), ja tā sezona sakrīt;
      - xG modelis tiek apmācīts no jauna tikai uz metieniem pirms pārbaudes sezonas.
    """
    sys.path.insert(0, BASE)
    import datu_apstrade as da
    import modelis
    raw_db, _ = da.ielasit_db()
    raw_t = da.ielasit_speles()
    raw = pd.concat([x for x in (raw_db, raw_t) if x is not None and not x.empty], ignore_index=True)
    vg_d = [x for x in (da.ielasit_db_tabulu("vartsargi"), da.ielasit_tabulu("vartsargi")) if x is not None and not x.empty]
    vg = pd.concat(vg_d, ignore_index=True) if vg_d else None
    p, meta = modelis.ielasit_parametrus()
    info = {"modela_parametri": "lietotnes (kalibrēti arī uz pārbaudes sezonas)", "xg_modelis": "lietotnes", "bez_nopludes": False}
    if test_sezona and meta and meta.get("parametri_parbaudei") and int(meta.get("parbaudes_sezona") or 0) == int(test_sezona):
        p = {**modelis.NOKLUSETIE, **meta["parametri_parbaudei"]}
        info["modela_parametri"] = f"parametri_parbaudei (kalibrēti uz {meta.get('regulesanas_sezona')}, bez {test_sezona})"
        print(f"  Modeļa iestatījumi: kalibrēti bez pārbaudes sezonas {test_sezona} (parametri_parbaudei).")
    elif test_sezona:
        print(f"  UZMANĪBU: modelis_parametri.json nav 'parametri_parbaudei' sezonai {test_sezona} – modeļa iestatījumi var būt "
              "kalibrēti arī uz pārbaudes sezonas (palaid python modelis.py --kalibret).")
    metieni, xmod = None, None
    if modelis.vajag_metienus(p):
        import xg as xgm
        m_d = [x for x in (da.ielasit_db_tabulu("metieni"), da.ielasit_tabulu("metieni")) if x is not None and not x.empty]
        metieni = pd.concat(m_d, ignore_index=True) if m_d else None
        xmod = xgm.ielasit_modeli()
        if test_sezona and metieni is not None and not metieni.empty:
            gads = int(test_sezona) // 10000
            m_apm = metieni[pd.to_numeric(metieni["game_id"], errors="coerce") // 1_000_000 < gads]
            if len(m_apm) > 50000:
                print(f"  xG modelis: apmāca no jauna uz {len(m_apm)} metieniem pirms {test_sezona} (bez pārbaudes sezonas)…")
                xmod = xgm.apmacit(m_apm)
                info["xg_modelis"] = f"apmācīts uz metieniem pirms {test_sezona}"
    info["bez_nopludes"] = info["modela_parametri"].startswith("parametri_parbaudei") and info["xg_modelis"].startswith("apmācīts")
    pirma = pd.Timestamp(raw[raw["sezona"] == min(sezonas)]["datums"].min())
    g, _, _, _, p_eff = modelis.sagatavot(raw, vg, metieni, p, pirma, min(sezonas), xmod)
    out = {}
    for sezona in sezonas:
        s_ = g[g["sezona"] == sezona]
        mod, pedeja = None, None
        datumi = sorted(s_["datums"].unique())
        for i, d in enumerate(datumi):
            d = pd.Timestamp(d)
            if mod is None or (d - pedeja).days >= solis_dienas:
                mod = modelis.aprekinat_reitingus(g, uz_datumu=d, sezona_tagad=sezona, p=p_eff)
                pedeja = d
            if mod is None:
                continue
            for r in s_[s_["datums"] == d].itertuples(index=False):
                nz = (getattr(r, "nz_n", np.nan), getattr(r, "nz_k", np.nan), getattr(r, "nz_L", modelis.NEIZ_ILGTERMINA))
                t = modelis.prognoze(mod, g, r.home, r.away, p_eff, r.b2b_h, r.b2b_a, r.cels_h, r.cels_a, r.po,
                                     vg_h=getattr(r, "vg_h", 1.0), vg_a=getattr(r, "vg_a", 1.0), nz=nz)
                out[int(r.game_id)] = {k: t[k] for k in ("lh", "la", "1x2", "ar_ot", "plus_minus", "totali", "neizskirts_pa_kopsummam", "ticamiba")}
            if (i + 1) % 30 == 0:
                print(f"  {sezona}: {i + 1}/{len(datumi)} dienas")
    return out, info


def _vesturiskie_kandidati(prognozes, koef, speles, cena="koef"):
    """
    Visas vēsturiskās izvēles (bez filtriem): modeļa p, tirgus taisnīgā p (vidējie noslēguma koeficienti bez uzcenojuma),
    labākais koeficients un iznākums. cena – "koef" (noslēgums, ~ pēc vārtsargu paziņošanas) vai "koef_atv" (atvēršana).
    """
    cfg = {"min_ev": -9, "min_p": 0, "max_koef": 99, "max_novirze": 9, "prasit_vartsargus": False, "tirgi": PARB_TIRGI,
           "modela_svars": {t: 1.0 for t in PARB_TIRGI}}
    sp = speles.set_index("game_id")
    rindas = []
    for gid, x in koef.groupby("game_id"):
        t = prognozes.get(int(gid))
        if t is None or int(gid) not in sp.index:
            continue
        s_ = sp.loc[int(gid)]
        x = x[x[cena].notna()].assign(koef=lambda d: d[cena])
        if x.empty:
            continue
        game = {"game_id": int(gid), "sakums_utc": str(s_.get("sakums_utc", "")), "majas": s_["home_team"], "viesi": s_["away_team"],
                "ticamiba": t.get("ticamiba")}
        rez = {"hg": float(s_[["home_p1", "home_p2", "home_p3"]].fillna(0).sum()), "ag": float(s_[["away_p1", "away_p2", "away_p3"]].fillna(0).sum()),
               "h_tot": float(s_["home_total"]), "a_tot": float(s_["away_total"])}
        try:
            probs = modela_varbutibas(t, x)
        except Exception:                                                       # noqa: BLE001
            continue
        for k in kandidati(game, probs, x, cfg):
            if not np.isfinite(k["p_tirgus"]):
                continue
            k["rezultats"] = izverte(k, rez)
            k["datums"] = str(s_.get("datums", ""))[:10]
            k["sezona"] = int(s_.get("sezona", 0))
            rindas.append(k)
    return pd.DataFrame(rindas)


def _simulet(d, w, min_ev, c=None):
    """Vienādas likmes (1 vienība) visām izvēlēm, kas iztur filtrus ar svaru w un min_ev: (likmes, uzvaras, ROI, vid. koef)."""
    c = {**NOKLUSETIE, **(c or {})}
    pl = w * d["p_modelis"] + (1 - w) * d["p_tirgus"]
    ev_ = pl * d["koef"] - 1
    m = (ev_ >= min_ev) & (pl >= c["min_p"]) & (d["koef"] <= c["max_koef"]) & ((d["p_modelis"] - d["p_tirgus"]).abs() <= c["max_novirze"]) \
        & (pl >= d["p_tirgus"]) & d["rezultats"].isin(["W", "L", "P"])
    x = d[m]
    if x.empty:
        return {"likmes": 0}
    pel = np.where(x["rezultats"] == "W", x["koef"] - 1, np.where(x["rezultats"] == "L", -1.0, 0.0))
    n = len(x)
    roi = float(pel.mean())
    return {"likmes": n, "uzvaras": int((x["rezultats"] == "W").sum()), "roi": roi, "se": float(pel.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan"),
            "vid_koef": float(x["koef"].mean()), "vid_ev": float(ev_[m].mean())}


def _bankrola_simulacija(d, cfg):
    """Pilns algoritms (1 pick spēlē, ¼ Kelly × ticamība, dienas robeža) laika secībā: gala bankrols un lielākais kritums."""
    bank, augst, kritums, n = BANKROLLS, BANKROLLS, 0.0, 0
    for dat, x in d.sort_values("datums").groupby("datums", sort=True):
        kand = []
        for r in x.to_dict("records"):
            w = float(cfg["modela_svars"].get(r["tirgus"], 1.0))
            pl = w * r["p_modelis"] + (1 - w) * r["p_tirgus"]
            ok = r["tirgus"] in cfg["tirgi"] and pl * r["koef"] - 1 >= _min_ev(cfg, r["tirgus"]) and pl >= cfg["min_p"] \
                and r["koef"] <= cfg["max_koef"] and abs(r["p_modelis"] - r["p_tirgus"]) <= cfg["max_novirze"] and pl >= r["p_tirgus"]
            if ok and r["rezultats"] in ("W", "L", "P"):
                kand.append({**r, "p_lemums": pl, "ev": pl * r["koef"] - 1, "der": True})
        if not kand:
            continue
        pk = atlasit(kand, cfg)
        for r in pk.to_dict("records"):
            likme = r["likme_pct"] * bank
            bank += likme * ((r["koef"] - 1) if r["rezultats"] == "W" else (-1 if r["rezultats"] == "L" else 0))
            n += 1
        augst = max(augst, bank)
        kritums = max(kritums, (augst - bank) / augst)
    return {"likmes": n, "bankrols": round(bank, 1), "max_kritums": round(kritums, 4)}


def parbaude(sezonas=None, izvade=PARAMETRU_FAILS):
    """Vēsturiskā pārbaude: parametru izvēle uz vecākajām sezonām, godīga pārbaude uz jaunākās → picks_parametri.json."""
    sys.path.insert(0, BASE)
    import datu_apstrade as da
    ves = os.path.join(BASE, "sezonas", "vesture")
    sezonas = sezonas or sorted(int(x) for x in os.listdir(ves) if x.isdigit() and os.path.exists(os.path.join(ves, x, "koeficienti_vesture.csv")))
    if len(sezonas) < 2:
        print("Vajag vēsturiskos koeficientus vismaz 2 sezonām: python vesturiskie_koef.py")
        return 1
    print(f"Sezonas ar koeficientiem: {sezonas}. Modeļa prognozes (walk-forward, var aizņemt 10–30 min)…")
    prog, info = vesturiskas_prognozes(sezonas, test_sezona=sezonas[-1])
    raw_db, _ = da.ielasit_db()
    kand, kand_atv = [], []
    for s in sezonas:
        k = _vesturiskie_koeficienti(s)
        sp = raw_db[raw_db["sezona"] == s]
        kand.append(_vesturiskie_kandidati(prog, k, sp, "koef"))
        kand_atv.append(_vesturiskie_kandidati(prog, k, sp, "koef_atv"))
        print(f"  {s}: {kand[-1]['game_id'].nunique() if not kand[-1].empty else 0} spēles ar koeficientiem un prognozēm")
    d = pd.concat(kand, ignore_index=True)
    d_atv = pd.concat(kand_atv, ignore_index=True)
    apm_s, test_s = sezonas[:-1], sezonas[-1]
    apm, test = d[d["sezona"].isin(apm_s)], d[d["sezona"] == test_s]
    rezgis, tirgi_rez = [], {}
    for t in PARB_TIRGI:
        labakais = None
        for w in PARB_SVARI:
            for mev in PARB_MIN_EV:
                a = _simulet(apm[apm["tirgus"] == t], w, mev)
                b = _simulet(test[test["tirgus"] == t], w, mev)
                rezgis.append({"tirgus": t, "svars": w, "min_ev": mev, "apmaciba": a, "parbaude": b})
                # izvēle pēc piesardzīga novērtējuma (ROI − 1 standartkļūda), lai neizvēlētos nejaušu "veiksmīgu" mazu paraugu
                if a.get("likmes", 0) >= PARB_MIN_LIKMES and (labakais is None or a["roi"] - a["se"] > labakais[2]["roi"] - labakais[2]["se"]):
                    labakais = (w, mev, a, b)
        if labakais is None:
            tirgi_rez[t] = {"iesl": False, "iemesls": "par maz likmju apmācības sezonās"}
            continue
        w, mev, a, b = labakais
        atv = _simulet(d_atv[(d_atv["sezona"] == test_s) & (d_atv["tirgus"] == t)], w, mev)
        kopa = _simulet(d[d["tirgus"] == t], w, mev)                       # visas sezonas kopā (informācijai)
        iesl = a["roi"] > 0 and b.get("likmes", 0) > 0 and b["roi"] > 0
        # "pilns" tikai, ja pārbaudes sezonā (kas parametru izvēlē NETIKA izmantota) ROI ir lielāks par savu standartkļūdu;
        # kopējais ROI šim nav derīgs, jo apmācības daļā parametri izvēlēti tieši tāpēc, ka tur tie bija labākie (optimistisks)
        limenis = ("pilns" if b["roi"] - b["se"] > 0 else "novērošana") if iesl else "izslēgts"
        tirgi_rez[t] = {"iesl": bool(iesl), "limenis": limenis, "svars": w, "min_ev": mev, "apmaciba": a, "parbaude": b,
                        "parbaude_atvershana": atv, "kopa": kopa,
                        "iemesls": ("" if limenis == "pilns" else
                                    "pelnošs abos posmos, bet pārbaudes sezonas ROI nav drošs (± 1 SE) – mazākas likmes, līdz to apstiprina reālā vēsture"
                                    if iesl else ("nav pelnošs apmācības sezonās" if a["roi"] <= 0 else "nav pelnošs pārbaudes sezonā"))}
        print(f"  {TIRGU_NOS[t]}: svars {w}, min EV {mev:.0%} → apmācība ROI {a['roi']:+.1%} ({a['likmes']} likmes), "
              f"pārbaude ROI {b.get('roi', float('nan')):+.1%} ({b.get('likmes', 0)} likmes), kopā {kopa['roi']:+.1%} ± {kopa['se']:.1%} "
              f"→ {limenis.upper()}")
    svars = {t: tirgi_rez[t].get("svars", NOKLUSETIE["modela_svars"].get(t, 1.0)) for t in PARB_TIRGI}
    svars["1x2"] = svars["ml"]                                   # 1X2 nāk no tā paša sadalījuma kā "ar OT"
    min_ev = {t: tirgi_rez[t].get("min_ev", 0.04) for t in PARB_TIRGI}
    min_ev["1x2"] = min_ev["ml"]
    tirgi = [t for t in PARB_TIRGI if tirgi_rez[t]["iesl"]] + (["1x2"] if tirgi_rez["ml"]["iesl"] else [])
    max_likme = {t: (NOVEROSANAS_MAX_LIKME if tirgi_rez[t].get("limenis") == "novērošana" else NOKLUSETIE_MAX_LIKME) for t in PARB_TIRGI}
    max_likme["1x2"] = max_likme["ml"]
    cfg = {**NOKLUSETIE, "modela_svars": svars, "min_ev": min_ev, "tirgi": tuple(tirgi), "max_likme": max_likme}
    bank = _bankrola_simulacija(test, cfg) if tirgi else {"likmes": 0, "bankrols": BANKROLLS, "max_kritums": 0.0}
    rez = {
        "izveidots": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "avots": "SportsbookReview – ASV bukmeikeru noslēguma koeficienti (vidējais bez uzcenojuma = tirgus; labākais = likmei)",
        "apmacibas_sezonas": apm_s, "parbaudes_sezona": test_s,
        "speles": {str(s): int(d[d["sezona"] == s]["game_id"].nunique()) for s in sezonas},
        "parametri": {"modela_svars": svars, "min_ev": min_ev, "tirgi": tirgi, "max_likme": max_likme},
        "bez_nopludes": info.get("bez_nopludes", False), "modela_parametri": info.get("modela_parametri"), "xg_modelis": info.get("xg_modelis"),
        "tirgi": tirgi_rez, "bankrols_parbaudes_sezona": bank, "rezgis": rezgis,
    }
    os.makedirs(os.path.dirname(izvade), exist_ok=True)
    with open(izvade, "w", encoding="utf-8") as f:
        json.dump(rez, f, ensure_ascii=False, indent=1, default=float)
    print(f"Ieslēgtie tirgi: {tirgi or 'neviens'}; pārbaudes sezonā bankrols {BANKROLLS:.0f} → {bank['bankrols']:.0f} "
          f"({bank['likmes']} likmes, lielākais kritums {bank['max_kritums']:.0%}). Saglabāts: {izvade}")
    return 0


ielasit_parametrus()

if __name__ == "__main__":
    if "--no-arhiva" in sys.argv:
        sys.path.insert(0, BASE)
        import datu_apstrade as da
        n, kopa = no_prognozu_arhiva(da.ielasit_prognozu_arhivu())
        print(f"Picks vēsture: +{n} (kopā {kopa}) → {FAILS}")
    elif "--parbaude" in sys.argv:
        sys.exit(parbaude([int(a) for a in sys.argv[2:] if a.isdigit()] or None))
    else:
        print(__doc__)
