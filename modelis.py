"""
modelis.py – Puasona prognožu modelis (NHL, pamatlaika vārti).

PROCESS PIRMS PROGNOZES
1) Dati: šīs sezonas spēles + DB (sezonas/vesture/<sezona>/), tikai pamatlaika vārti (1.–3. periods).
2) Komandu stiprums: katrai komandai uzbrukums (att) un aizsardzība (def), plus līgas līmenis (mu) un mājas priekšrocība.
   Svērta Puasona regresija:  log λ_mājinieki = mu + mājas + att[mājinieki] − def[viesi] + korekcijas,  viesiem līdzīgi.
   Svari: šīs sezonas spēles izgaist ar pusperiodu (dienās); iepriekšējās sezonas – ar mazāku, nemainīgu svaru (vēsture kā
   sākuma pieņēmums: sezonas sākumā tā dominē, vēlāk šīs sezonas spēles to aizstāj). L2 regularizācija tur reitingus pie 0.
3) Korekcijas (aprēķinātas no datiem tajā pašā regresijā): otrā spēle pēc kārtas (back-to-back), garš ceļš (≥ 1500 km
   ≤ 2 dienu laikā), play-off. H2H: neliela, stipri "pievilkta" korekcija pēc savstarpējo spēļu atlikumiem (ar griestiem).
4) Rezultātu matrica (neatkarīgi Puasoni) + neizšķirtu korekcija (hokejā pamatlaikā neizšķirtu ir vairāk) → 1X2 pamatlaikā,
   totāli, ±1.5, ticamākie rezultāti. Uzvarētājs ar OT: neizšķirta gadījumā mājinieku uzvaras iespēja papildlaikā/metienos
   (no vēstures) ar nelielu stipruma ietekmi. Periodi: λ × perioda daļa (no datiem). Noraidījumi: komandu minor sodu biežums
   × pretinieka izcīnītie × tiesnešu koeficients.
5) Parametrus (pusperiods, vēstures svars, neizšķirtu korekcija, OT, vai lietot H2H) nosaka pārbaude pret vēsturi:
       python modelis.py --kalibret
   → sezonas/vesture/modelis_parametri.json (lietotne to nolasa; bez faila izmanto noklusējumus).
"""
import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import nbinom, poisson

NHL_KOMANDAS_SARAKSTS = [
    "ANA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET",
    "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT",
    "PHI", "PIT", "SJS", "SEA", "STL", "TBL", "TOR", "UTA", "VAN", "VGK",
    "WSH", "WPG",
]
NOKLUSETIE = {
    "pusperiods_dienas": 60,          # šīs sezonas spēļu svars uz pusi ik pēc N dienām
    "vesture_svari": [0.5, 0.25],      # pagājušā, aizpagājušā sezona (relatīvi pret svaigu šīs sezonas spēli)
    "regularizacija": 3.0,            # L2 sods komandu reitingiem
    "neizskirts_rho": 1.15,           # diagonāles (neizšķirtu) reizinātājs rezultātu matricā
    "ot_majas": 0.52,                 # P(mājinieki uzvar OT/SO | neizšķirts pamatlaikā), līgas līmenis
    "ot_stiprums": 0.35,              # cik λ attiecība ietekmē OT uzvaru
    "h2h_lietot": True,               # vai H2H korekcija uzlabo prognozes (nosaka kalibrēšana)
    "h2h_k": 12.0,                    # H2H atlikumu "pievilkšana" (gaidāmo vārtu ekvivalents)
    "h2h_max": 0.08,                  # H2H korekcijas griesti (±8%)
    "periodu_dalas": [0.31, 0.34, 0.35],
    "totali_kappa": 1.0,              # gaidāmo vārtu kopsummas "pievilkšana" pie līgas vidējā (1 = bez, 0.5 = uz pusi)
    "nb_r": 0.0,                      # vārtu izkliede: 0 = Puasons, >0 = negatīvais binomiālais (mazāks = lielāka izkliede)
    "totali_kal": {},                 # totālu kalibrācija pēc vēstures: {"5.5": [a, b]} → over = σ(a + b·logit(over_modelis))
    "noraid_k": 10.0,                 # komandas noraidījumu biežuma pievilkšana pie līgas (spēles)
    "vartsargu_beta": 0.0,            # sākuma vārtsarga ietekmes stiprums (0 = neietekmē; nosaka kalibrēšana: 0 … 2)
    "vartsargu_k": 1500,              # vārtsarga vērtējuma pievilkšana pie līgas (sv: metieni; xg: paredzamie vārti; nosaka kalibrēšana)
    "vartsargu_metode": "sv",         # "sv" = glābšanas % vienādos sastāvos; "xg" = ielaistie pret paredzamajiem vārtiem (GSAx)
    "xg_svars": 0.0,                  # komandu stiprums: 0 = tikai vārti, 1 = tikai xG (nosaka kalibrēšana)
    "neiz_k": 0.0,                    # neizšķirtu līmeņa pielāgošana šai sezonai: 0 = nav; >0 = ilgtermiņa līmeņa svars spēlēs
    "neiz_c": 0.0,                    # neizšķirtu korekcijas atkarība no gaidāmo vārtu kopsummas (<0: mazāk vārtu → vairāk neizšķirtu)
}
GARS_CELS_KM = 1500
KOMANDU_PECTECI = {"ARI": "UTA"}      # Arizona Coyotes (līdz 2023/24) → Utah: sastāvs pārcēlās, modelim tā ir viena komanda
PARAMETRU_FAILS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sezonas", "vesture", "modelis_parametri.json")
MAX_V = 13
VG_K = 1500                           # vārtsarga glābšanas % "pievilkšana" pie līgas (metienu ekvivalents)
VG_SEZONAS_SVARS = 0.5                # iepriekšējo sezonu metieni vārtsargu vērtējumā sver uz pusi


# ----------------------------------------------------------------------------
# DATI
# ----------------------------------------------------------------------------
def ielasit_parametrus(fails=PARAMETRU_FAILS):
    """(parametri, kalibrēšanas rezultāts vai None). Bez faila – noklusējumi."""
    p = dict(NOKLUSETIE)
    meta = None
    if os.path.exists(fails):
        try:
            with open(fails, encoding="utf-8") as f:
                d = json.load(f)
            p.update(d.get("parametri", {}))
            meta = d
        except (OSError, ValueError):
            pass
    return p, meta


def pievienot_vartsargus(g, vr, k=VG_K, metode="sv", w=0.0):
    """Faktisko sākuma vārtsargu attiecības katrai spēlei (vg_h / vg_a) ar doto pievilkšanu k un metodi."""
    g = g.copy()
    g["vg_h"] = g["vg_a"] = 1.0
    if vr is None or vr.empty:
        return g
    f = vartsargu_faktori_vesturei(vr, k, metode, w)
    if not f.empty:
        kk = dict(zip(zip(f["game_id"], f["team"]), f["vg"]))
        g["vg_h"] = [kk.get((gid, h), 1.0) for gid, h in zip(g["game_id"], g["home"])]
        g["vg_a"] = [kk.get((gid, a), 1.0) for gid, a in zip(g["game_id"], g["away"])]
    return g


def pievienot_xg(g, xgk):
    """Komandu xG (normalizēts) + vārti tukšos vārtos katrai spēlei: xh / xa (NaN, ja metienu datu nav)."""
    g = g.copy()
    g["xh"] = g["xa"] = np.nan
    if xgk is None or xgk.empty:
        return g
    k = {(int(a), b): float(x) + float(e) for a, b, x, e in zip(xgk["game_id"], xgk["komanda"], xgk["xg"], xgk["en"])}
    g["xh"] = [k.get((gid, h), np.nan) for gid, h in zip(g["game_id"], g["home"])]
    g["xa"] = [k.get((gid, a), np.nan) for gid, a in zip(g["game_id"], g["away"])]
    return g


NEIZ_ILGTERMINA = 0.21                # neizšķirtu īpatsvars pamatlaikā, ja vēstures nav


def pievienot_neizskirtus(g):
    """Katrai spēlei: šīs sezonas spēles un neizšķirti LĪDZ šai dienai (nz_n, nz_k) un ilgtermiņa īpatsvars no iepriekšējām sezonām (nz_L)."""
    g = g.copy()
    nz = (g["hg"] == g["ag"]).astype(int)
    n_out, k_out, l_out = np.zeros(len(g)), np.zeros(len(g)), np.full(len(g), NEIZ_ILGTERMINA)
    iepr_n = iepr_k = 0.0
    for sez in sorted(g["sezona"].unique()):
        m = (g["sezona"] == sez).to_numpy()
        L = iepr_k / iepr_n if iepr_n >= 300 else NEIZ_ILGTERMINA
        idx = np.where(m)[0]
        d = g["datums"].to_numpy()[idx]
        z = nz.to_numpy()[idx]
        sec = np.argsort(d, kind="stable")
        dd, zz = d[sec], z[sec]
        # kumulatīvi līdz iepriekšējai dienai (vienas dienas spēles savā starpā neredz)
        uniq, pirmais = np.unique(dd, return_index=True)
        cz = np.concatenate([[0], np.cumsum(zz)])
        n_d = {u: pirmais[i] for i, u in enumerate(uniq)}
        for j, pos in enumerate(sec):
            n_before = n_d[dd[j]]
            n_out[idx[pos]], k_out[idx[pos]], l_out[idx[pos]] = n_before, cz[n_before], L
        iepr_n += m.sum()
        iepr_k += z.sum()
    g["nz_n"], g["nz_k"], g["nz_L"] = n_out, k_out, l_out
    return g


def rho_spelei(p, lh, la, nz=None):
    """Neizšķirtu korekcija konkrētai spēlei: bāzes rho × šīs sezonas līmenis (izredžu attiecība pret ilgtermiņa, pievilkta ar neiz_k)
    × atkarība no gaidāmo vārtu kopsummas (neiz_c). Robežas 0.8–2.5."""
    rho = float(p["neizskirts_rho"])
    K = float(p.get("neiz_k", 0.0))
    if K > 0 and nz is not None:
        n, k, L = nz
        if np.isfinite(n) and np.isfinite(k) and 0 < L < 1:
            r_s = (k + K * L) / (n + K)
            rho *= (r_s / (1 - r_s)) / (L / (1 - L))
    c = float(p.get("neiz_c", 0.0))
    if c:
        rho *= math.exp(c * (lh + la - 6.0))
    return float(min(2.5, max(0.8, rho)))


def spelu_tabula(raw, vg=None, k=VG_K, xgk=None):
    """Spēļu līmeņa tabula modelim: datums, sezona, po, home, away, hg, ag (pamatlaika vārti) + atpūtas/ceļa pazīmes
    + faktisko sākuma vārtsargu attiecības vg_h / vg_a (ja doti vārtsargu dati; citādi 1)."""
    if raw is None or raw.empty:
        return pd.DataFrame()
    r = raw.copy()
    g = pd.DataFrame({
        "game_id": pd.to_numeric(r["game_id"], errors="coerce").astype("int64"),
        "datums": pd.to_datetime(r["datums"]).dt.normalize(),
        "sezona": pd.to_numeric(r["sezona"], errors="coerce").fillna(0).astype(int),
        "po": (r["tips"] == "PO").astype(int) if "tips" in r.columns else 0,
        "home": r["home_team"].replace(KOMANDU_PECTECI), "away": r["away_team"].replace(KOMANDU_PECTECI),
        "hg": r[["home_p1", "home_p2", "home_p3"]].fillna(0).sum(axis=1).astype(int),
        "ag": r[["away_p1", "away_p2", "away_p3"]].fillna(0).sum(axis=1).astype(int),
        "beigas": r["spele_beidzas"].astype(str).str.upper() if "spele_beidzas" in r.columns else "REG",
        "uzv_majas": (r["home_total"] > r["away_total"]).astype(int),
    })
    for p_ in (1, 2, 3):
        g[f"g_p{p_}"] = r[f"home_p{p_}"].fillna(0) + r[f"away_p{p_}"].fillna(0)
    g = g[g["home"].isin(NHL_KOMANDAS_SARAKSTS) & g["away"].isin(NHL_KOMANDAS_SARAKSTS)]
    g = g.drop_duplicates("game_id").sort_values(["datums", "game_id"]).reset_index(drop=True)
    g = pievienot_vartsargus(g, vartsargu_rindas(vg) if vg is not None and not vg.empty else None, k)
    g = pievienot_xg(g, xgk)
    g = pievienot_neizskirtus(g)
    return pievienot_atputu(g)


def _attalums(a, b):
    try:
        import lokacijas
        return float(lokacijas.attalums_km(a, b))
    except Exception:
        return 0.0


def pievienot_atputu(g):
    """Katrai komandai katrā spēlē: back-to-back (iepriekšējā spēle vakar) un garš ceļš (≥ 1500 km, ≤ 2 dienas kopš iepr. spēles)."""
    g = g.copy()
    n = len(g)
    b2b = {"h": np.zeros(n, int), "a": np.zeros(n, int)}
    cels = {"h": np.zeros(n, int), "a": np.zeros(n, int)}
    pedeja, cache = {}, {}                         # komanda → (datums, spēles vieta = mājinieki)
    for i, (d, home, away) in enumerate(zip(g["datums"], g["home"], g["away"])):
        for puse, kom in (("h", home), ("a", away)):
            if kom in pedeja:
                d0, vieta0 = pedeja[kom]
                dienas = (d - d0).days
                if dienas == 1:
                    b2b[puse][i] = 1
                if dienas <= 2:
                    k = (vieta0, home)
                    if k not in cache:
                        cache[k] = _attalums(vieta0, home)
                    if cache[k] >= GARS_CELS_KM:
                        cels[puse][i] = 1
            pedeja[kom] = (d, home)
    for puse in ("h", "a"):
        g[f"b2b_{puse}"] = b2b[puse]
        g[f"cels_{puse}"] = cels[puse]
    return g


# ----------------------------------------------------------------------------
# VĀRTSARGI: kvalitāte (pievilkts glābšanas % vienādos sastāvos) un sākuma vārtsarga ietekme
# ----------------------------------------------------------------------------
def _dala(v, idx):
    try:
        a, b = str(v).split("/")
        return float((a, b)[idx])
    except (ValueError, IndexError):
        return np.nan


def vartsargu_rindas(vg):
    """Vārtsargs × spēle: game_id, datums, team, playerId, vards, starter, sa, ga (vienādos sastāvos; ja nav – visi metieni)."""
    if vg is None or vg.empty:
        return pd.DataFrame()
    v = vg.copy()
    sa = v["evenStrengthShotsAgainst"].map(lambda x: _dala(x, 1)) if "evenStrengthShotsAgainst" in v else pd.Series(np.nan, index=v.index)
    ga = pd.to_numeric(v.get("evenStrengthGoalsAgainst"), errors="coerce") if "evenStrengthGoalsAgainst" in v else pd.Series(np.nan, index=v.index)
    sa = sa.fillna(pd.to_numeric(v.get("shotsAgainst"), errors="coerce"))
    ga = ga.fillna(pd.to_numeric(v.get("goalsAgainst"), errors="coerce"))
    out = pd.DataFrame({"game_id": pd.to_numeric(v["game_id"], errors="coerce").astype("int64"), "datums": pd.to_datetime(v["datums"]).dt.normalize(),
                        "team": v["team"].replace(KOMANDU_PECTECI), "playerId": pd.to_numeric(v["playerId"], errors="coerce").astype("int64"),
                        "vards": v.get("vards", ""), "starter": v["starter"].astype(str).str.lower().isin(["true", "1"]),
                        "sa": sa.fillna(0), "ga": ga.fillna(0)})
    return out.sort_values(["datums", "game_id"]).reset_index(drop=True)


def _sezona_no_datuma(d):
    return d.year * 10000 + d.year + 1 if d.month >= 7 else (d.year - 1) * 10000 + d.year


class VartsarguUzskaite:
    """Kumulatīvā uzskaite pa datumiem: vārtsargu metieni/vārti (iepriekšējās sezonas ar svaru) un komandu vārtsargu sajaukums."""

    def __init__(self, k=VG_K):
        self.k = float(k)
        self.gk = {}                 # playerId → [metieni, vārti]
        self.kom = {}                # komanda → [metieni, vārti] (šī + iepriekšējā sezona ar svaru)
        self.sezona = None
        self.lg = [0.0, 0.0]

    def jauna_sezona(self, sez):
        if self.sezona is not None and sez != self.sezona:
            for d in (self.gk, self.kom):
                for k in d:
                    d[k] = [d[k][0] * VG_SEZONAS_SVARS, d[k][1] * VG_SEZONAS_SVARS]
        self.sezona = sez

    def liga_sv(self):
        return 1 - self.lg[1] / self.lg[0] if self.lg[0] > 500 else 0.915

    def sv(self, pid):
        s, g = self.gk.get(pid, (0.0, 0.0))
        lsv = self.liga_sv()
        return ((s - g) + self.k * lsv) / (s + self.k)

    def kom_sv(self, team):
        s, g = self.kom.get(team, (0.0, 0.0))
        lsv = self.liga_sv()
        return ((s - g) + self.k * lsv) / (s + self.k)

    def attieciba(self, pid, team):
        """Vārti pret šo vārtsargu attiecībā pret komandas parasto vārtsargu sajaukumu (>1 = sliktāks par parasto)."""
        return (1 - self.sv(pid)) / max(1e-6, 1 - self.kom_sv(team))

    def pievienot(self, rindas):
        for r in rindas.itertuples(index=False):
            if r.sa <= 0:
                continue
            a = self.gk.setdefault(r.playerId, [0.0, 0.0]); a[0] += r.sa; a[1] += r.ga
            b = self.kom.setdefault(r.team, [0.0, 0.0]); b[0] += r.sa; b[1] += r.ga
            self.lg[0] += r.sa; self.lg[1] += r.ga


class VartsarguUzskaiteXG(VartsarguUzskaite):
    """Vārtsargs pēc ielaistajiem pret paredzamajiem vārtiem (rindās sa = xG pret vārtsargu, ga = ielaistie).
    r = (ielaistie + k) / (xG + k); komandas stiprums ar xG svaru w jau neietver vārtsargu, tāpēc
    attiecība = r_vārtsargs / r_komandas^(1 − w) (w = 0: salīdzinājums ar komandas parasto; w = 1: absolūti)."""

    def __init__(self, k=50.0, w=0.0):
        super().__init__(k)
        self.w = float(w)

    def r(self, s, g):
        return (g + self.k) / (s + self.k)

    def attieciba(self, pid, team):
        s, g = self.gk.get(pid, (0.0, 0.0))
        ks, kg = self.kom.get(team, (0.0, 0.0))
        return self.r(s, g) / max(1e-6, self.r(ks, kg)) ** (1 - self.w)


def _uzskaite(k, metode="sv", w=0.0):
    return VartsarguUzskaiteXG(k, w) if metode == "xg" else VartsarguUzskaite(k)


def vartsargu_rindas_xg(vr, vxg):
    """Vārtsargu rindas xG metodei: starter un datums no vr, sa = xG pret vārtsargu, ga = ielaistie (bez tukšajiem vārtiem)."""
    if vr is None or vr.empty or vxg is None or vxg.empty:
        return pd.DataFrame()
    x = vxg.copy()
    x["playerId"] = pd.to_numeric(x["playerId"], errors="coerce")
    x = x.dropna(subset=["playerId"])
    x["playerId"] = x["playerId"].astype("int64")
    out = vr[["game_id", "datums", "team", "playerId", "vards", "starter"]].merge(
        x[["game_id", "playerId", "xga", "ga"]], on=["game_id", "playerId"], how="left")
    out["sa"] = out["xga"].fillna(0.0)
    out["ga"] = out["ga"].fillna(0.0)
    return out.drop(columns=["xga"]).sort_values(["datums", "game_id"]).reset_index(drop=True)


def vartsargu_faktori_vesturei(vr, k=VG_K, metode="sv", w=0.0):
    """Katrai aizvadītajai spēlei: faktiskā sākuma vārtsarga attiecība (no datiem pirms šīs dienas) → game_id, team, vg."""
    if vr is None or vr.empty:
        return pd.DataFrame(columns=["game_id", "team", "vg"])
    u = _uzskaite(k, metode, w)
    out = []
    for d, diena in vr.groupby("datums", sort=True):
        u.jauna_sezona(_sezona_no_datuma(d))
        for r in diena[diena["starter"]].itertuples(index=False):
            out.append((r.game_id, r.team, u.attieciba(r.playerId, r.team)))
        u.pievienot(diena)
    return pd.DataFrame(out, columns=["game_id", "team", "vg"])


def ticamie_vartsargi(vr, team, b2b=0, u=None):
    """
    Nākamās spēles ticamie sākuma vārtsargi pēc rotācijas: [(playerId, vārds, varbūtība, attiecība)].
    Nr. 1 = visvairāk sākumu komandas pēdējās 10 spēlēs. Otrajā spēlē pēc kārtas, ja vakar sāka Nr. 1, biežāk sāk otrs vārtsargs.
    """
    x = vr[(vr["team"] == team) & vr["starter"]].sort_values(["datums", "game_id"])
    if x.empty:
        return []
    # šīs sezonas sākumi, ja tādu ir vismaz 3 (citādi pēdējie 10 kopā ar iepriekšējo sezonu)
    sez_tag = _sezona_no_datuma(x["datums"].iloc[-1])
    xs = x[x["datums"].map(_sezona_no_datuma) == sez_tag]
    ped = (xs if len(xs) >= 3 else x).tail(10)
    sk = ped["playerId"].value_counts()
    vardi = dict(zip(x["playerId"], x["vards"]))
    ids = list(sk.index[:2])
    if len(ids) == 1:
        # tikai viens vārtsargs nesen sācis: bez apstiprinājuma nekad 100% – 15% komandas otrajam vārtsargam (no vēstures)
        otrie = [i for i in x["playerId"].iloc[::-1].unique() if i != ids[0]][:1]
        ids += otrie if otrie else [-1]
        p = {ids[0]: 0.85, ids[1]: 0.15}
    else:
        p1 = min(0.85, max(0.5, sk.iloc[0] / sk.sum()))
        if b2b and x["playerId"].iloc[-1] == ids[0]:
            p1 = 0.3
        p = {ids[0]: p1, ids[1]: 1 - p1}
    return [(pid, vardi.get(pid, ""), pr, (u.attieciba(pid, team) if u is not None else 1.0)) for pid, pr in p.items()]


APSTIPRINAJUMA_VARBUTIBA = {"Confirmed": 1.0, "Expected": 0.9, "Likely": 0.75}


def _vards_norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


def apstiprinatie_vartsargi(rotacija, vr, team, vards, statuss, u=None):
    """
    Ja ir ziņa par sākuma vārtsargu (Confirmed / Expected / Likely), tas aizstāj rotācijas varbūtības:
    šim vārtsargam – 100% / 90% / 75%, atlikums – pārējiem pēc rotācijas. Unconfirmed vai nav ziņu – paliek rotācija.
    Atgriež (saraksts [(playerId, vārds, varbūtība, attiecība)], statuss vai None).
    """
    pv = APSTIPRINAJUMA_VARBUTIBA.get(str(statuss))
    if not pv or not vards:
        return rotacija, None
    nv = _vards_norm(vards)
    pid = None
    if vr is not None and not vr.empty:
        kand = vr[vr["vards"].map(_vards_norm) == nv]
        if not kand.empty:
            kom = kand[kand["team"] == team]
            pid = int((kom if not kom.empty else kand)["playerId"].iloc[-1])
    pid = pid if pid is not None else -abs(hash(nv)) % 10 ** 9      # jauns vārtsargs bez NHL spēlēm DB → līgas vidējais
    citi = [(i, n, p_, r_) for i, n, p_, r_ in rotacija if i != pid]
    s_citi = sum(p_ for _, _, p_, _ in citi)
    out = [(pid, vards, pv, (u.attieciba(pid, team) if u is not None else 1.0))]
    if pv < 1 and citi:
        out += [(i, n, (1 - pv) * (p_ / s_citi if s_citi > 0 else 1 / len(citi)), r_) for i, n, p_, r_ in citi]
    elif pv < 1:
        out = [(pid, vards, 1.0, out[0][3])]
    return out, str(statuss)


def sagaidama_attieciba(saraksts):
    """Ticamo vārtsargu attiecību vidējais pēc varbūtībām (1, ja nav datu)."""
    return float(sum(p_ * r_ for _, _, p_, r_ in saraksts)) if saraksts else 1.0


def uzskaite_lidz(vr, datums, k=VG_K, metode="sv", w=0.0):
    """Vārtsargu uzskaite ar visām spēlēm pirms datuma (nākamo spēļu prognozēm). vr – rindas atbilstoši metodei."""
    u = _uzskaite(k, metode, w)
    for d, diena in vr[vr["datums"] < pd.Timestamp(datums)].groupby("datums", sort=True):
        u.jauna_sezona(_sezona_no_datuma(d))
        u.pievienot(diena)
    return u


# ----------------------------------------------------------------------------
# REITINGI (svērta Puasona regresija)
# ----------------------------------------------------------------------------
def _svari(g, uz_datumu, sezona_tagad, p):
    vecums = (uz_datumu - g["datums"]).dt.days.clip(lower=0).to_numpy(float)
    w = np.power(0.5, vecums / max(1.0, float(p["pusperiods_dienas"])))
    vsv = list(p["vesture_svari"]) + [0.0] * 5
    sez = g["sezona"].to_numpy()
    for k in range(1, 6):                         # iepriekšējās sezonas: nemainīgs (mazāks) svars
        w = np.where(sez == sezona_tagad - k * 10001, vsv[k - 1], w)
    return np.where(sez > sezona_tagad, 0.0, w)


def aprekinat_reitingus(g, uz_datumu=None, sezona_tagad=None, p=None):
    """Modelis no spēlēm pirms uz_datumu: {'mu', 'majas', 'att', 'def', korekcijas, 'n_sez', ...} vai None."""
    p = p or NOKLUSETIE
    if g is None or g.empty:
        return None
    uz_datumu = pd.Timestamp(uz_datumu).normalize() if uz_datumu is not None else g["datums"].max() + pd.Timedelta(days=1)
    g = g[g["datums"] < uz_datumu]
    if g.empty:
        return None
    sezona_tagad = int(sezona_tagad or g["sezona"].max())
    w = _svari(g, uz_datumu, sezona_tagad, p)
    m = w > 1e-6
    g, w = g[m], w[m]
    if g.empty:
        return None
    komandas = NHL_KOMANDAS_SARAKSTS
    ix = {k: i for i, k in enumerate(komandas)}
    H, A = g["home"].map(ix).to_numpy(), g["away"].map(ix).to_numpy()
    yh, ya = g["hg"].to_numpy(float), g["ag"].to_numpy(float)
    w_xg = float(p.get("xg_svars", 0.0))
    if w_xg > 0 and "xh" in g.columns:                # komandu stiprums no vārtu un paredzamo vārtu sajaukuma
        xh, xa = g["xh"].to_numpy(float), g["xa"].to_numpy(float)
        yh = np.where(np.isfinite(xh), (1 - w_xg) * yh + w_xg * xh, yh)
        ya = np.where(np.isfinite(xa), (1 - w_xg) * ya + w_xg * xa, ya)
    bh, ba = g["b2b_h"].to_numpy(float), g["b2b_a"].to_numpy(float)
    ch, ca = g["cels_h"].to_numpy(float), g["cels_a"].to_numpy(float)
    po = g["po"].to_numpy(float)
    n, reg = len(komandas), float(p["regularizacija"])

    # x = [mu, majas, b2b_att, b2b_def, cels_att, cels_def, po, att(n), def(n)]
    def nll(x):
        att, de = x[7:7 + n], x[7 + n:]
        eh = x[0] + x[1] + att[H] - de[A] + x[2] * bh + x[3] * ba + x[4] * ch + x[5] * ca + x[6] * po
        ea = x[0] + att[A] - de[H] + x[2] * ba + x[3] * bh + x[4] * ca + x[5] * ch + x[6] * po
        lh, la = np.exp(eh), np.exp(ea)
        f = np.sum(w * (lh - yh * eh)) + np.sum(w * (la - ya * ea))
        f += reg * (np.sum(att ** 2) + np.sum(de ** 2)) + 5.0 * np.sum(x[2:7] ** 2)
        rh, ra = w * (lh - yh), w * (la - ya)
        gr = np.zeros_like(x)
        gr[0] = rh.sum() + ra.sum()
        gr[1] = rh.sum()
        gr[2] = (rh * bh).sum() + (ra * ba).sum()
        gr[3] = (rh * ba).sum() + (ra * bh).sum()
        gr[4] = (rh * ch).sum() + (ra * ca).sum()
        gr[5] = (rh * ca).sum() + (ra * ch).sum()
        gr[6] = (rh * po).sum() + (ra * po).sum()
        gr[2:7] += 10.0 * x[2:7]
        gr[7:7 + n] = np.bincount(H, rh, n) + np.bincount(A, ra, n) + 2 * reg * att
        gr[7 + n:] = -np.bincount(A, rh, n) - np.bincount(H, ra, n) + 2 * reg * de
        return f, gr

    sv = float(np.sum(w * (yh + ya)) / max(1e-9, 2 * np.sum(w)))
    x0 = np.zeros(7 + 2 * n)
    x0[0] = math.log(max(0.5, sv))
    x = minimize(nll, x0, jac=True, method="L-BFGS-B", options={"maxiter": 500}).x
    sez_mask = (g["sezona"] == sezona_tagad).to_numpy()
    hs, as_ = g["home"].to_numpy()[sez_mask], g["away"].to_numpy()[sez_mask]
    n_sez = {k: int((hs == k).sum() + (as_ == k).sum()) for k in komandas}
    gs = g[g["sezona"] == sezona_tagad]
    gp = g[g["sezona"] < sezona_tagad]
    L = float((gp["hg"] == gp["ag"]).mean()) if len(gp) >= 300 else NEIZ_ILGTERMINA
    nz_mod = (float(len(gs)), float((gs["hg"] == gs["ag"]).sum()), L)
    return {"nz": nz_mod, "liga_kopa": 2 * sv, "mu": x[0], "majas": x[1], "b2b_att": x[2], "b2b_def": x[3], "cels_att": x[4], "cels_def": x[5], "po": x[6],
            "att": dict(zip(komandas, x[7:7 + n])), "def": dict(zip(komandas, x[7 + n:])),
            "n_sez": n_sez, "sezona": sezona_tagad, "uz_datumu": uz_datumu}


def vajag_metienus(p):
    return float(p.get("xg_svars", 0.0)) > 0 or p.get("vartsargu_metode", "sv") == "xg"


def sagatavot(raw, vg, metieni, p, uz_datumu, sezona_tagad, xg_modelis=None):
    """
    Viss prognozēm vajadzīgais vienā vietā (lietotne un prognožu arhīvs):
    spēļu tabula (ar vārtsargiem un, ja parametri to prasa, xG), reitingi uz datumu, vārtsargu rotācijas rindas un uzskaite.
    Ja parametri prasa xG, bet metienu datu vai xG modeļa nav, tiek izmantoti vārti un glābšanas % (ar noklusējuma pievilkšanu).
    """
    metode, w = p.get("vartsargu_metode", "sv"), float(p.get("xg_svars", 0.0))
    k = float(p.get("vartsargu_k", VG_K))
    vr = vartsargu_rindas(vg) if vg is not None and not vg.empty else None
    ir_xg = vajag_metienus(p) and metieni is not None and not metieni.empty and bool(xg_modelis)
    g = spelu_tabula(raw, vg, k if metode == "sv" else VG_K)
    vr_u, k_u, metode_u = vr, (k if metode == "sv" else VG_K), "sv"
    if ir_xg:
        import xg as xgm
        xgk, vxg = xgm.modela_xg(metieni, xg_modelis, g)
        g = pievienot_xg(g, xgk)
        if metode == "xg" and vr is not None:
            vr_u, k_u, metode_u = vartsargu_rindas_xg(vr, vxg), k, "xg"
            g = pievienot_vartsargus(g, vr_u, k, "xg", w)
    p_eff = p if ir_xg or not vajag_metienus(p) else dict(p, xg_svars=0.0, vartsargu_metode="sv", vartsargu_k=VG_K)
    mod = aprekinat_reitingus(g, uz_datumu=uz_datumu, sezona_tagad=sezona_tagad, p=p_eff)
    u = uzskaite_lidz(vr_u, uz_datumu, k_u, metode_u, w) if vr_u is not None and not vr_u.empty else None
    return g, mod, vr, u, p_eff


def lambdas(mod, home, away, b2b_h=0, b2b_a=0, cels_h=0, cels_a=0, po=0):
    """Sagaidāmie pamatlaika vārti (mājinieki, viesi)."""
    eh = (mod["mu"] + mod["majas"] + mod["att"].get(home, 0) - mod["def"].get(away, 0) + mod["b2b_att"] * b2b_h
          + mod["b2b_def"] * b2b_a + mod["cels_att"] * cels_h + mod["cels_def"] * cels_a + mod["po"] * po)
    ea = (mod["mu"] + mod["att"].get(away, 0) - mod["def"].get(home, 0) + mod["b2b_att"] * b2b_a
          + mod["b2b_def"] * b2b_h + mod["cels_att"] * cels_a + mod["cels_def"] * cels_h + mod["po"] * po)
    return math.exp(eh), math.exp(ea)


def h2h_koeficienti(mod, g, home, away, p):
    """Savstarpējās spēles (šī sezona + DB): faktiskie pret gaidāmajiem vārtiem katrai komandai, stipri pievilkti, ar griestiem."""
    if g is None or g.empty:
        return 1.0, 1.0, 0
    x = g[(((g["home"] == home) & (g["away"] == away)) | ((g["home"] == away) & (g["away"] == home))) & (g["datums"] < mod["uz_datumu"])]
    if x.empty:
        return 1.0, 1.0, 0
    fakt, gaid = {home: 0.0, away: 0.0}, {home: 0.0, away: 0.0}
    for r in x.itertuples(index=False):
        lh, la = lambdas(mod, r.home, r.away, r.b2b_h, r.b2b_a, r.cels_h, r.cels_a, r.po)
        fakt[r.home] += r.hg
        fakt[r.away] += r.ag
        gaid[r.home] += lh
        gaid[r.away] += la
    k, mx = float(p["h2h_k"]), float(p["h2h_max"])

    def koef(kom):
        return float(min(1 + mx, max(1 - mx, (fakt[kom] + k) / (gaid[kom] + k))))
    return koef(home), koef(away), len(x)


# ----------------------------------------------------------------------------
# VARBŪTĪBAS
# ----------------------------------------------------------------------------
def _sadalijums(lam, r):
    i = np.arange(MAX_V)
    if r and r > 0:                                # negatīvais binomiālais ar vidējo lam un izkliedi r
        return nbinom.pmf(i, r, r / (r + lam))
    return poisson.pmf(i, lam)


def saspiest(lh, la, p, liga_kopa):
    """Gaidāmo vārtu kopsummu pievelk pie līgas vidējā (totali_kappa), saglabājot komandu attiecību."""
    k = float(p.get("totali_kappa", 1.0))
    if k >= 0.999 or not liga_kopa:
        return lh, la
    tot = lh + la
    s = (liga_kopa + k * (tot - liga_kopa)) / tot
    return lh * s, la * s


def rezultatu_matrica(lh, la, rho, r=0.0):
    m = np.outer(_sadalijums(lh, r), _sadalijums(la, r))
    m[np.diag_indices(MAX_V)] *= rho
    return m / m.sum()


def ot_majas_iespeja(lh, la, p):
    z = math.log(p["ot_majas"] / (1 - p["ot_majas"])) + p["ot_stiprums"] * math.log(max(1e-6, lh) / max(1e-6, la))
    return 1 / (1 + math.exp(-z))


def _kal_over(over, p, lin):
    """Totāla over/under; ja ir kalibrācija pēc vēstures, Puasona varbūtība tiek pielāgota reālajam vārtu sadalījumam."""
    ab = (p.get("totali_kal") or {}).get(str(lin))
    if ab:
        o = min(1 - 1e-6, max(1e-6, over))
        over = 1 / (1 + math.exp(-(ab[0] + ab[1] * math.log(o / (1 - o)))))
    return {"over": float(over), "under": float(1 - over)}


def tirgi(lh, la, p):
    """Visas varbūtības no λ: 1X2 (pamatlaiks), uzvarētājs ar OT, totāli, ±1.5, top rezultāti, periodi."""
    m = rezultatu_matrica(lh, la, float(p["neizskirts_rho"]), float(p.get("nb_r", 0.0)))
    h, d, a = float(np.tril(m, -1).sum()), float(np.trace(m)), float(np.triu(m, 1).sum())
    pot = ot_majas_iespeja(lh, la, p)
    ii, jj = np.indices(m.shape)
    tot = np.bincount((ii + jj).ravel(), m.ravel())
    starp = (ii - jj)

    def p_starp(cond):
        return float(m[cond(starp)].sum())
    per = {}
    for nr, dala in enumerate(p["periodu_dalas"], 1):
        lam = (lh + la) * dala
        per[nr] = {"gaidami": lam, **{lin: {"over": float(1 - poisson.cdf(int(lin), lam)), "under": float(poisson.cdf(int(lin), lam))}
                                      for lin in (0.5, 1.5, 2.5)}}
    return {
        "lh": lh, "la": la,
        "1x2": {"1": h, "X": d, "2": a},
        "papildlaiks": {"ja": d, "ne": 1 - d},
        "ar_ot": {"1": h + d * pot, "2": a + d * (1 - pot)},
        "totali": {lin: _kal_over(float(tot[int(lin) + 1:].sum()), p, lin) for lin in (4.5, 5.5, 6.5)},
        "plus_minus": {"1 −1.5": p_starp(lambda s: s >= 2), "2 +1.5": p_starp(lambda s: s <= 1),
                       "2 −1.5": p_starp(lambda s: s <= -2), "1 +1.5": p_starp(lambda s: s >= -1)},
        "top": sorted(((float(m[i, j]), f"{i}:{j}") for i in range(MAX_V) for j in range(MAX_V)), reverse=True)[:3],
        "neizskirts_pa_kopsummam": {int(2 * i): float(m[i, i]) for i in range(MAX_V)},
        "periodi": per,
    }


def noraidijumi(df_rindas, home, away, uz_datumu=None, p=None, tiesnesu_koef=1.0, tips="RS"):
    """
    Gaidāmie minor noraidījumi (pamatlaiks) katrai komandai:
      līgas līmenis šosezon (pievilkts pie iepriekšējo sezonu līmeņa, 300 komandas-spēles)
      × komandas saņemto noraidījumu tendence × pretinieka izcīnīto noraidījumu tendence × tiesnešu koeficients.
    Tendences = komandas pēdējās 40 tā paša tipa spēles (RS vai PO) attiecībā pret līgas vidējo TAJĀ sezonā,
    pievilktas pie 1 (noraid_k spēles). Play-off spēlēs noraidījumu ir būtiski vairāk, tāpēc tās netiek jauktas ar RS.
    """
    p = p or NOKLUSETIE
    if df_rindas is None or df_rindas.empty or "pen_count" not in df_rindas.columns:
        return None
    d = df_rindas
    if "tips" in d.columns:
        d = d[d["tips"] == tips] if (d["tips"] == tips).any() else d
    if uz_datumu is not None:
        d = d[pd.to_datetime(d["datums"]) < pd.Timestamp(uz_datumu)]
    d = d[d["pen_count"].notna()]
    if d.empty:
        return None
    d = d.sort_values(["datums", "game_id"])
    lig_sez = d.groupby("sezona")["pen_count"].mean()
    sez = d["sezona"].max()
    tag, iepr = d[d["sezona"] == sez], d[d["sezona"] < sez]
    liga_iepr = float(iepr["pen_count"].mean()) if len(iepr) >= 200 else float(d["pen_count"].mean())
    K = 300.0
    liga = (float(tag["pen_count"].sum()) + K * liga_iepr) / (len(tag) + K)
    if not (liga > 0):
        return None
    k = float(p["noraid_k"])

    def tendence(kom, kol):
        x = d[d["komanda"] == kom].tail(40)
        if x.empty:
            return 1.0
        rel = (x[kol] / x["sezona"].map(lig_sez)).replace([np.inf, -np.inf], np.nan).dropna()
        return float((rel.sum() + k * 1.0) / (len(rel) + k))
    lh = liga * tendence(home, "pen_count") * tendence(away, "pen_draw") * tiesnesu_koef
    la = liga * tendence(away, "pen_count") * tendence(home, "pen_draw") * tiesnesu_koef
    lam = lh + la
    b = int(round(lam))
    linijas = sorted({max(0.5, b - 1.5), max(1.5, b - 0.5), b + 0.5})        # līnijas ap gaidāmo skaitu
    return {"majas": lh, "viesi": la, "kopa": lam, "tiesnesu_koef": tiesnesu_koef, "liga": liga,
            "totali": {lin: {"over": float(1 - poisson.cdf(int(lin), lam)), "under": float(poisson.cdf(int(lin), lam))}
                       for lin in linijas}}


def ticamiba(mod, home, away):
    n = min(mod["n_sez"].get(home, 0), mod["n_sez"].get(away, 0))
    return ("Augsta" if n >= 15 else ("Vidēja" if n >= 5 else "Zema")), n


def prognoze(mod, g, home, away, p, b2b_h=0, b2b_a=0, cels_h=0, cels_a=0, po=0, h2h=None, vg_h=1.0, vg_a=1.0, nz=None):
    """Pilna prognoze spēlei (vārti, tirgi, ticamība, izmantotie faktori).
    vg_h / vg_a – mājinieku / viesu sākuma vārtsarga attiecība pret komandas parasto (>1 = sliktāks): ietekmē pretinieka vārtus."""
    h2h = p.get("h2h_lietot", True) if h2h is None else h2h
    lh, la = lambdas(mod, home, away, b2b_h, b2b_a, cels_h, cels_a, po)
    kh = ka = 1.0
    n_h2h = 0
    if h2h:
        kh, ka, n_h2h = h2h_koeficienti(mod, g, home, away, p)
        lh, la = lh * kh, la * ka
    lh_bv, la_bv = lh, la
    beta = float(p.get("vartsargu_beta", 0.0))
    fv_h = min(1.4, max(0.7, float(vg_a) ** beta))           # mājinieku vārti atkarīgi no viesu vārtsarga un otrādi
    fv_a = min(1.4, max(0.7, float(vg_h) ** beta))           # (drošības robežas: vārtsargs nemaina vārtus vairāk par −30% / +40%)
    lh, la = lh * fv_h, la * fv_a
    lh0, la0 = lh, la
    lh, la = saspiest(lh, la, p, mod.get("liga_kopa"))
    nz = nz if nz is not None else mod.get("nz")
    rho = rho_spelei(p, lh, la, nz)
    t = tirgi(lh, la, dict(p, neizskirts_rho=rho))
    t["rho"], t["nz"] = rho, nz
    t["lh0"], t["la0"], t["liga_kopa"] = lh0, la0, mod.get("liga_kopa")
    t["ticamiba"], t["n_min"] = ticamiba(mod, home, away)
    t["faktori"] = {"b2b_h": b2b_h, "b2b_a": b2b_a, "cels_h": cels_h, "cels_a": cels_a, "po": po, "h2h": (kh, ka, n_h2h),
                    "vartsargi": (fv_h, fv_a)}
    t["lh_bv"], t["la_bv"], t["vg_h"], t["vg_a"] = lh_bv, la_bv, vg_h, vg_a
    return t


def pilnas_speles_over(t, lin):
    """Over varbūtība pilnai spēlei (ar papildlaiku/metienu sēriju, kā bukmeikeru totāliem): neizšķirts pamatlaikā dod +1 vārtu."""
    if abs(lin - round(lin)) < 1e-9:
        return None                                  # veselas līnijas (6.0) ar naudas atgriešanu netiek salīdzinātas
    k = int(math.floor(lin))                         # pamatlaika kopsumma k (neizšķirts) → pilnā spēlē k + 1 > lin
    if lin in t["totali"]:
        pamat = t["totali"][lin]["over"]
    else:
        lam = t["lh"] + t["la"]
        pamat = float(1 - poisson.cdf(k, lam))
    return float(min(1.0, pamat + t.get("neizskirts_pa_kopsummam", {}).get(k, 0.0)))


def tirgus_varbutibas(koef):
    """Koeficienti → varbūtības bez bukmeikera uzcenojuma (proporcionāli): {iznākums: varbūtība} vai None."""
    try:
        inv = {k: 1 / float(v) for k, v in koef.items() if v and float(v) > 1}
    except (TypeError, ValueError):
        return None
    s = sum(inv.values())
    return {k: v / s for k, v in inv.items()} if inv and s > 0 and len(inv) == len(koef) else None


def vertet_pret_tirgu(prog, rez, sliesni=(0.03, 0.05, 0.10)):
    """
    Modelis pret tirgu uz reālām (aizvadītām) spēlēm, izmantojot tikai pirms spēles saglabātās prognozes un koeficientus.
    prog – prognozes_arhivs.csv (spēle × ielāde); rez – spēļu rezultāti: game_id, hg, ag (pamatlaiks), h_tot, a_tot (gala rezultāts).
    Likmes laiks = pirmā ielāde (rīta līnija); "noslēgums" = pēdējā zināmā ielāde pirms spēles.
    Atgriež: {'speles', 'logloss': {...}, 'likmes': [ {tirgus, slieksnis, likmes, uzvaras, roi_pin, roi_lab, clv, parspeja_noslegumu} ]}.
    """
    if prog is None or prog.empty or rez is None or rez.empty:
        return {"speles": 0}
    pr = prog.sort_values("ielade")
    pirma = pr.groupby("game_id").first()
    ped = pr.groupby("game_id").last()
    r = rez.set_index("game_id")
    ids = [i for i in pirma.index if i in r.index]
    if not ids:
        return {"speles": 0}
    a, z, rr = pirma.loc[ids], ped.loc[ids], r.loc[ids]
    iz = np.where(rr["hg"] > rr["ag"], "1", np.where(rr["hg"] == rr["ag"], "X", "2"))

    def tv(df, i):
        inv = 1 / df[[f"pin_{k}" for k in ("1", "X", "2")]]
        return (inv[f"pin_{i}"] / inv.sum(axis=1)).to_numpy()
    p_m = {i: a[f"m_{i}"].to_numpy() for i in ("1", "X", "2")}
    p_t0 = {i: tv(a, i) for i in ("1", "X", "2")}
    p_t1 = {i: tv(z, i) for i in ("1", "X", "2")}
    ok = np.isfinite(p_t0["1"]) & np.isfinite(p_t1["1"])

    def ll(pp):
        v = np.array([pp[k][n] for n, k in enumerate(iz)])
        return float(np.mean(-np.log(np.clip(v[ok], 1e-12, 1))))
    out = {"speles": int(ok.sum()),
           "logloss": {"modelis": ll(p_m), "tirgus_rits": ll(p_t0), "tirgus_nosl": ll(p_t1),
                       "apvienots": ll({k: 0.5 * p_m[k] + 0.5 * p_t0[k] for k in p_m})}}
    likmes = []
    # 1X2 pamatlaikā
    for i in ("1", "X", "2"):
        o0, o1, ob = a[f"pin_{i}"].to_numpy(), z[f"pin_{i}"].to_numpy(), a[f"lab_{i}"].to_numpy()
        ev = p_m[i] * o0 - 1
        uzv = (iz == i)
        for sl in sliesni:
            m = ok & np.isfinite(o0) & (ev >= sl)
            likmes.append(_likmju_rinda(f"Pamatlaikā {i}", sl, m, uzv, o0, ob, o1))
    # totāls ar OT (Pinnacle galvenā līnija; tikai, ja līnija rītā un noslēgumā ir tā pati)
    lin_ok = np.isfinite(a["tot_linija"].to_numpy()) & (a["tot_linija"].to_numpy() == z["tot_linija"].to_numpy())
    tot = (rr["h_tot"] + rr["a_tot"]).to_numpy()
    for puse, mp, kol in (("Over", a["m_over"].to_numpy(), "over"), ("Under", 1 - a["m_over"].to_numpy(), "under")):
        o0, o1, ob = a[f"pin_{kol}"].to_numpy(), z[f"pin_{kol}"].to_numpy(), a[f"lab_{kol}"].to_numpy()
        ev = mp * o0 - 1
        uzv = (tot > a["tot_linija"].to_numpy()) if puse == "Over" else (tot < a["tot_linija"].to_numpy())
        for sl in sliesni:
            m = lin_ok & np.isfinite(o0) & np.isfinite(mp) & (ev >= sl)
            likmes.append(_likmju_rinda(f"Totāls {puse} (ar OT)", sl, m, uzv, o0, ob, o1))
    out["likmes"] = likmes
    return out


def _likmju_rinda(tirgus, sl, m, uzv, o0, ob, o1):
    n = int(m.sum())
    if n == 0:
        return {"tirgus": tirgus, "slieksnis": sl, "likmes": 0}
    w = uzv[m].astype(float)
    return {"tirgus": tirgus, "slieksnis": sl, "likmes": n, "uzvaras": int(w.sum()),
            "roi_pin": float(np.mean(w * o0[m] - 1)), "roi_lab": float(np.nanmean(w * np.where(np.isfinite(ob[m]), ob[m], o0[m]) - 1)),
            "clv": float(np.nanmean(o0[m] / o1[m] - 1)), "parspeja_noslegumu": float(np.nanmean(o0[m] > o1[m]))}


def koeficients(pr):
    """Taisnīgais koeficients = 1 / varbūtība (bez bukmeikera uzcenojuma)."""
    return 1 / pr if pr and pr > 1e-9 else float("inf")


# ----------------------------------------------------------------------------
# PĀRBAUDE PRET VĒSTURI UN KALIBRĒŠANA (lokāli: python modelis.py --kalibret)
# ----------------------------------------------------------------------------
def _ll(p_):
    return -math.log(max(1e-12, min(1.0, p_)))


def atpakal_parbaude(g, p, sezona, solis_dienas=3, h2h=False):
    """Walk-forward: katrai sezonas spēlei prognoze tikai no datiem pirms tās (modelis tiek pārrēķināts ik pēc solis_dienas)."""
    s = g[g["sezona"] == sezona]
    if s.empty:
        return pd.DataFrame()
    rindas, mod, pedeja = [], None, None
    for d in sorted(s["datums"].unique()):
        d = pd.Timestamp(d)
        if mod is None or (d - pedeja).days >= solis_dienas:
            mod = aprekinat_reitingus(g, uz_datumu=d, sezona_tagad=sezona, p=p)
            pedeja = d
        if mod is None:
            continue
        for r in s[s["datums"] == d].itertuples(index=False):
            nz = (getattr(r, "nz_n", np.nan), getattr(r, "nz_k", np.nan), getattr(r, "nz_L", NEIZ_ILGTERMINA))
            t = prognoze(mod, g, r.home, r.away, p, r.b2b_h, r.b2b_a, r.cels_h, r.cels_a, r.po, h2h=h2h,
                         vg_h=getattr(r, "vg_h", 1.0), vg_a=getattr(r, "vg_a", 1.0), nz=nz)
            rindas.append({"game_id": r.game_id, "datums": d, "home": r.home, "away": r.away, "hg": r.hg, "ag": r.ag,
                           "beigas": r.beigas, "uzv_majas": r.uzv_majas, "lh": t["lh"], "la": t["la"],
                           "lh0": t["lh0"], "la0": t["la0"], "liga_kopa": t["liga_kopa"],
                           "lh_bv": t["lh_bv"], "la_bv": t["la_bv"], "vg_h": t["vg_h"], "vg_a": t["vg_a"],
                           "nz_n": nz[0], "nz_k": nz[1], "nz_L": nz[2],
                           "p1": t["1x2"]["1"], "pX": t["1x2"]["X"], "p2": t["1x2"]["2"], "ml1": t["ar_ot"]["1"],
                           "o45": t["totali"][4.5]["over"], "o55": t["totali"][5.5]["over"], "o65": t["totali"][6.5]["over"]})
    return pd.DataFrame(rindas)


def metrikas(bt):
    if bt.empty:
        return {}
    iz = np.where(bt["hg"] > bt["ag"], "1", np.where(bt["hg"] == bt["ag"], "X", "2"))
    p_iz = np.where(iz == "1", bt["p1"], np.where(iz == "X", bt["pX"], bt["p2"]))
    tot = bt["hg"] + bt["ag"]
    return {
        "speles": int(len(bt)),
        "logloss_1x2": float(np.mean([_ll(x) for x in p_iz])),
        "brier_1x2": float(np.mean((bt["p1"] - (iz == "1")) ** 2 + (bt["pX"] - (iz == "X")) ** 2 + (bt["p2"] - (iz == "2")) ** 2)),
        "logloss_ar_ot": float(np.mean([_ll(p_ if y else 1 - p_) for p_, y in zip(bt["ml1"], bt["uzv_majas"])])),
        "logloss_o55": float(np.mean([_ll(p_ if y else 1 - p_) for p_, y in zip(bt["o55"], tot > 5.5)])),
        "neizskirti_fakt": float((iz == "X").mean()), "neizskirti_prog": float(bt["pX"].mean()),
        "videji_varti_fakt": float(tot.mean()), "videji_varti_prog": float((bt["lh"] + bt["la"]).mean()),
    }


def pa_sezonas_dalam(bt, ref, dienas=45):
    """Precizitāte sezonas sākumā (pirmās N dienas) un pārējā sezonā, salīdzinot ar godīgo bāzi."""
    if bt.empty:
        return {}
    sak = bt["datums"].min()
    out = {}
    for nos, m in (("sakums", bt["datums"] < sak + pd.Timedelta(days=dienas)), ("parejais", bt["datums"] >= sak + pd.Timedelta(days=dienas))):
        x = bt[m]
        if len(x) >= 50:
            out[nos] = {"speles": int(len(x)), "logloss_1x2": metrikas(x)["logloss_1x2"], "baze_1x2": bazes_metrikas(x, ref)["logloss_1x2"]}
    return out


def kalibracija(bt, kol, fakts, grupas=(0, .2, .3, .4, .5, .6, .7, 1.01)):
    """Prognozētā varbūtība grupās pret faktisko biežumu (vai 60% prognozes piepildās ~60% gadījumu)."""
    out = []
    for a, b in zip(grupas[:-1], grupas[1:]):
        m = (bt[kol] >= a) & (bt[kol] < b)
        if m.sum() >= 10:
            out.append({"no": a, "lidz": min(b, 1.0), "speles": int(m.sum()),
                        "prognoze": float(bt.loc[m, kol].mean()), "fakts": float(fakts[m].mean())})
    return out


def bazes_metrikas(bt, ref=None):
    """
    Bāze: visām spēlēm vienādas līgas varbūtības. ref – iepriekšējo sezonu spēles (godīga bāze, zināma pirms sezonas);
    bez ref – biežumi no pašas pārbaudes sezonas (bāze, kas "zina nākotni", tikai salīdzināšanai).
    """
    iz = np.where(bt["hg"] > bt["ag"], "1", np.where(bt["hg"] == bt["ag"], "X", "2"))
    avots = bt if ref is None or ref.empty else ref
    iz_r = np.where(avots["hg"] > avots["ag"], "1", np.where(avots["hg"] == avots["ag"], "X", "2"))
    f = {k: float((iz_r == k).mean()) for k in ("1", "X", "2")}
    o = float(((avots["hg"] + avots["ag"]) > 5.5).mean())
    return {"logloss_1x2": float(np.mean([_ll(f[x]) for x in iz])),
            "logloss_o55": float(np.mean([_ll(o if y else 1 - o) for y in (bt["hg"] + bt["ag"]) > 5.5])),
            "biezumi": f, "over55": o}


def parrekinat(bt, p):
    """Varbūtības no saglabātajām λ ar citiem rho / kappa / nb_r (bez modeļa pārrēķināšanas)."""
    rind = []
    beta = float(p.get("vartsargu_beta", 0.0))
    if "lh_bv" in bt.columns:                         # vārtsargu ietekme ar šī p beta (ar tām pašām robežām kā prognozē)
        lh0s = bt["lh_bv"] * (bt["vg_a"] ** beta).clip(0.7, 1.4)
        la0s = bt["la_bv"] * (bt["vg_h"] ** beta).clip(0.7, 1.4)
    else:
        lh0s, la0s = bt["lh0"], bt["la0"]
    nzs = list(zip(bt["nz_n"], bt["nz_k"], bt["nz_L"])) if "nz_n" in bt.columns else [None] * len(bt)
    for lh0, la0, L, nz in zip(lh0s, la0s, bt["liga_kopa"], nzs):
        lh, la = saspiest(lh0, la0, p, L)
        t = tirgi(lh, la, dict(p, neizskirts_rho=rho_spelei(p, lh, la, nz)))
        rind.append((t["1x2"]["1"], t["1x2"]["X"], t["1x2"]["2"], t["ar_ot"]["1"], t["totali"][4.5]["over"], t["totali"][5.5]["over"],
                     t["totali"][6.5]["over"], lh, la))
    out = bt.copy()
    out[["p1", "pX", "p2", "ml1", "o45", "o55", "o65", "lh", "la"]] = pd.DataFrame(rind, index=bt.index)
    return out


def _platt(p_mod, y):
    """Loģistiskā pārkalibrēšana: atrod a, b, lai σ(a + b·logit(p)) vislabāk atbilst faktiem (log loss)."""
    z = np.log(np.clip(p_mod, 1e-6, 1 - 1e-6) / (1 - np.clip(p_mod, 1e-6, 1 - 1e-6)))
    y = np.asarray(y, float)

    def f(ab):
        q = 1 / (1 + np.exp(-(ab[0] + ab[1] * z)))
        q = np.clip(q, 1e-9, 1 - 1e-9)
        return -np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)) + 1e-3 * ((ab[0]) ** 2 + (ab[1] - 1) ** 2)
    ab = minimize(f, np.array([0.0, 1.0]), method="Nelder-Mead").x
    return [float(ab[0]), float(max(0.05, ab[1]))]


def _izveleties_papildu(bt, p):
    """No pārbaudes prognozēm: vārtsargu ietekme (pēc 1X2 log loss), kopsummas pievilkšana un izkliede (pēc O/U 5.5 log loss),
    tad neizšķirtu korekcija, OT un totālu kalibrācija."""
    p = dict(p, totali_kal={})
    if "lh_bv" in bt.columns and (bt["vg_h"] != 1).any() and "vartsargu_beta_fiksets" not in p:
        p["vartsargu_beta"] = min((metrikas(parrekinat(bt, dict(p, vartsargu_beta=b)))["logloss_1x2"], b)
                                  for b in (0.0, 0.5, 1.0, 1.25, 1.5, 2.0))[1]
    labakais = (1e9, p["totali_kappa"], p["nb_r"])
    for kappa in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0):
        for r in (0.0, 60.0, 30.0, 15.0):
            pp = dict(p, totali_kappa=kappa, nb_r=r)
            ll = metrikas(parrekinat(bt, pp))["logloss_o55"]
            labakais = min(labakais, (ll, kappa, r))
    p = dict(p, totali_kappa=labakais[1], nb_r=labakais[2])
    b2 = parrekinat(bt, dict(p, neiz_k=0.0, neiz_c=0.0))
    pred_x, fakt_x = b2["pX"].mean(), (b2["hg"] == b2["ag"]).mean()
    p["neizskirts_rho"] = float(min(1.8, max(0.9, p["neizskirts_rho"] * fakt_x / max(1e-6, pred_x))))
    # neizšķirti: šīs sezonas līmeņa pielāgošana (K) un atkarība no kopsummas (c); robusti – tuvos variantus (≤ 0.0005) atrisina
    # par labu vājākai pielāgošanai un c = 0
    if "nz_n" in bt.columns:
        rez = []
        for K in (0.0, 600.0, 300.0, 150.0):
            for c in (0.0, -0.15, -0.3, 0.15):
                rez.append((metrikas(parrekinat(bt, dict(p, neiz_k=K, neiz_c=c)))["logloss_1x2"], K, c))
        lab = min(rez)[0]
        tuvi = [x for x in rez if x[0] <= lab + 0.0005]
        _, K, c = max(tuvi, key=lambda x: (x[1] == 0, x[1], -abs(x[2])))
        p["neiz_k"], p["neiz_c"] = K, c
        p["_neiz_rezultati"] = sorted(rez)[:4] + [x for x in rez if x[1] == 0 and x[2] == 0]
        b2 = parrekinat(bt, p)
        p["neizskirts_rho"] = float(min(1.8, max(0.9, p["neizskirts_rho"] * fakt_x / max(1e-6, b2["pX"].mean()))))
    b2 = parrekinat(bt, p)
    ot = b2[b2["hg"] == b2["ag"]]
    if len(ot) >= 50:
        p["ot_majas"] = float(min(0.6, max(0.4, (ot["uzv_majas"].sum() + 25 * 0.52) / (len(ot) + 25))))   # pievilkts pie 52%
        p["ot_stiprums"] = min((np.mean([_ll(ot_majas_iespeja(a, b, dict(p, ot_stiprums=k)) if y else 1 - ot_majas_iespeja(a, b, dict(p, ot_stiprums=k)))
                                         for a, b, y in zip(ot["lh"], ot["la"], ot["uzv_majas"])]), k) for k in (0.0, 0.2, 0.35, 0.5, 0.75, 1.0))[1]
    # totālu kalibrācija: Puasona forma neatbilst reālajam vārtu sadalījumam (piem., vārti tukšos vārtos) – pielāgo pēc vēstures
    b2 = parrekinat(bt, p)
    tot = b2["hg"] + b2["ag"]
    p["totali_kal"] = {str(lin): _platt(b2[kol].to_numpy(), (tot > lin).to_numpy()) for lin, kol in ((4.5, "o45"), (5.5, "o55"), (6.5, "o65"))}
    return p


def izveleties_vartsargus(bt, p, vr, k_varianti=(250, 500, 1000, 1500, 2000, 3000), b_varianti=(0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0),
                          vr_xg=None, k_xg=(10, 25, 50, 100, 200)):
    """Vārtsargu metode (glābšanas % vai xG), pievilkšana (k) un stiprums (beta) pēc 1X2 log loss uz izvēles sezonas."""
    if vr is None or vr.empty or "lh_bv" not in bt.columns:
        return p, []
    varianti = [("sv", k, vr) for k in k_varianti]
    if vr_xg is not None and not vr_xg.empty:
        varianti += [("xg", k, vr_xg) for k in k_xg]
    rez = []
    for metode, k, rr in varianti:
        f = vartsargu_faktori_vesturei(rr, k, metode, float(p.get("xg_svars", 0.0)))
        kk = dict(zip(zip(f["game_id"], f["team"]), f["vg"]))
        b2 = bt.copy()
        b2["vg_h"] = [kk.get((gid, h), 1.0) for gid, h in zip(b2["game_id"], b2["home"])]
        b2["vg_a"] = [kk.get((gid, a), 1.0) for gid, a in zip(b2["game_id"], b2["away"])]
        for b in b_varianti:
            rez.append((metrikas(parrekinat(b2, dict(p, vartsargu_beta=b)))["logloss_1x2"], k, b, metode))
    # Robusta izvēle: starp variantiem, kas ir ne vairāk kā 0.001 sliktāki par labāko (atšķirība mazāka par nejaušību),
    # ņem labākās metodes variantu ar stiprāko pievilkšanu (lielāks k) un mazāko stiprumu – tas labāk vispārinās.
    labakais = min(rez)
    tuvi = [x for x in rez if x[0] <= labakais[0] + 0.001 and x[2] > 0 and x[3] == labakais[3]]
    ll, k, b, metode = max(tuvi, key=lambda x: (x[1], -x[2])) if tuvi else labakais
    return dict(p, vartsargu_k=k, vartsargu_beta=b, vartsargu_metode=metode), sorted(rez)


def kalibret(g, sezonas, izvade=PARAMETRU_FAILS, rezgis=None, vr=None, vr_xg=None):
    """
    1) Godīga pārbaude: parametri izvēlēti uz priekšpēdējās sezonas, pārbaudīti uz pēdējās (katra spēle – tikai no datiem pirms tās).
    2) Gala parametri lietotnei: tie paši iestatījumi, bet neizšķirtu/kopsummas/OT korekcijas no abām sezonām kopā.
    Rezultāts – JSON fails lietotnei.
    """
    if len(sezonas) < 2:
        print("Kalibrēšanai vajag vismaz 2 pilnas sezonas.")
        return 1
    sez_reg, sez_test = sezonas[-2], sezonas[-1]
    ir_vesture_regulesanai = bool((g["sezona"] < sez_reg).any())
    print(f"Parametru izvēle uz {sez_reg}, pārbaude uz {sez_test} ({len(g)} spēles kopā)")
    if not ir_vesture_regulesanai:
        print(f"  Piezīme: pirms {sez_reg} DB nav vēstures, tāpēc vēstures svaru uz šīs sezonas nevar izvēlēties "
              f"(lejupielādē arī {sez_reg // 10000 - 1}{sez_reg // 10000}: python vesture.py {sez_reg // 10000 - 1}{sez_reg // 10000}).")
    vs_varianti = ([0.25, 0.1], [0.5, 0.25], [0.8, 0.4]) if ir_vesture_regulesanai else ([0.5, 0.25],)
    rezgis = rezgis or [(pp, vs) for pp in (60, 120, 240) for vs in vs_varianti]
    labakais, lab_ll, lab_bt = None, 1e9, None
    for pp, vs in rezgis:
        p = dict(NOKLUSETIE, pusperiods_dienas=pp, vesture_svari=vs)
        bt = atpakal_parbaude(g, p, sez_reg, solis_dienas=7)
        met = metrikas(bt)
        print(f"  pusperiods {pp:3d} d, vēstures svari {vs}: log loss 1X2 {met.get('logloss_1x2', float('nan')):.4f}")
        if met and met["logloss_1x2"] < lab_ll:
            labakais, lab_ll, lab_bt = p, met["logloss_1x2"], bt
    # komandu stiprums no vārtiem un xG: sajaukuma svars (ja ir metienu dati)
    if "xh" in g.columns and g["xh"].notna().any():
        print("  komandu stiprums: vārti pret xG (xG svars → log loss 1X2):")
        print(f"    xG svars 0.00: {lab_ll:.4f}")
        for w in (0.25, 0.5, 0.75, 1.0):
            pw = dict(labakais, xg_svars=w)
            bt = atpakal_parbaude(g, pw, sez_reg, solis_dienas=7)
            ll_w = metrikas(bt)["logloss_1x2"]
            print(f"    xG svars {w:.2f}: {ll_w:.4f}")
            if ll_w < lab_ll - 0.0005:                  # xG tiek ņemts tikai, ja tas skaidri uzlabo
                labakais, lab_ll, lab_bt = pw, ll_w, bt
    # vārtsargi: metode, pievilkšana un stiprums (faktiskie sākuma vārtsargi; vērtējums tikai no datiem pirms katras spēles)
    p_v, vrez = izveleties_vartsargus(lab_bt, dict(labakais), vr, vr_xg=vr_xg)
    if vrez:
        print("  vārtsargi (metode, pievilkšana k, stiprums beta → log loss 1X2):")
        for ll, k, b, mt in vrez[:6]:
            print(f"    {mt:2s} k={k:5g}, beta={b:.2f}: {ll:.4f}")
        bez = min(x for x in vrez if x[2] == 0.0)
        print(f"    bez vārtsargu ietekmes: {bez[0]:.4f}")
        rr = vr_xg if p_v["vartsargu_metode"] == "xg" else vr
        g = pievienot_vartsargus(g, rr, p_v["vartsargu_k"], p_v["vartsargu_metode"], float(labakais.get("xg_svars", 0.0)))
        lab_bt = atpakal_parbaude(g, dict(labakais, vartsargu_k=p_v["vartsargu_k"], vartsargu_metode=p_v["vartsargu_metode"]), sez_reg, solis_dienas=7)
    p = _izveleties_papildu(lab_bt, dict(labakais, vartsargu_k=p_v.get("vartsargu_k", VG_K), vartsargu_metode=p_v.get("vartsargu_metode", "sv")))
    if vrez:
        p["vartsargu_beta"] = p_v["vartsargu_beta"]
    tot = g[["g_p1", "g_p2", "g_p3"]].sum()
    p["periodu_dalas"] = [float(x) for x in (tot / tot.sum()).round(4)]
    nzr = p.pop("_neiz_rezultati", None)
    if nzr:
        print("  neizšķirti (sezonas pielāgošana K, kopsummas atkarība c → log loss 1X2):")
        for ll, K, c in nzr:
            print(f"    K={'nav' if not K else int(K):>4}, c={c:+.2f}: {ll:.4f}")
    print(f"  izvēlēts: neizšķirti K={'nav' if not p.get('neiz_k') else int(p['neiz_k'])}, c={p.get('neiz_c', 0):+.2f}; xG svars {p.get('xg_svars', 0)}, vārtsargi {p.get('vartsargu_metode', 'sv')} ietekme {p.get('vartsargu_beta', 0)} (pievilkšana {p.get('vartsargu_k', VG_K)}), kopsummas pievilkšana {p['totali_kappa']}, izkliede {'Puasons' if not p['nb_r'] else p['nb_r']}, "
          f"neizšķirtu korekcija {p['neizskirts_rho']:.2f}, OT mājiniekiem {p['ot_majas']:.3f}, "
          f"totālu kalibrācija 5.5: a={p['totali_kal']['5.5'][0]:+.2f}, b={p['totali_kal']['5.5'][1]:.2f}")
    # godīga pārbaude uz pēdējās sezonas: bez un ar H2H
    bt = atpakal_parbaude(g, p, sez_test, solis_dienas=3, h2h=False)
    bt_h = atpakal_parbaude(g, p, sez_test, solis_dienas=3, h2h=True)
    ref = g[g["sezona"] < sez_test]                       # godīgā bāze: tikai tas, kas bija zināms pirms pārbaudes sezonas
    met, met_h, baze, baze_nak = metrikas(bt), metrikas(bt_h), bazes_metrikas(bt, ref), bazes_metrikas(bt)
    p["h2h_lietot"] = bool(met_h["logloss_1x2"] <= met["logloss_1x2"] + 1e-4)
    gala = bt_h if p["h2h_lietot"] else bt
    # gala parametri lietotnei: korekcijas no abām sezonām kopā (vairāk datu; pārbaudes rezultāts paliek godīgs)
    p_gala = _izveleties_papildu(pd.concat([lab_bt, gala], ignore_index=True), dict(p, neizskirts_rho=NOKLUSETIE["neizskirts_rho"], totali_kal={}))
    p_gala["vartsargu_beta"], p_gala["vartsargu_k"] = p.get("vartsargu_beta", 0.0), p.get("vartsargu_k", VG_K)
    p_gala["vartsargu_metode"], p_gala["xg_svars"] = p.get("vartsargu_metode", "sv"), p.get("xg_svars", 0.0)
    p_gala.pop("_neiz_rezultati", None)
    # neizšķirtu pielāgošana (K, c) gala parametros – no abām sezonām kopā, tāpat kā rho: tikai tā var ietvert sezonu, kurā neizšķirtu
    # līmenis būtiski mainījās (vienā izvēles sezonā tāda maiņa var nebūt, tad pielāgošanas vērtību godīgi pārbaudīt nevar)
    p_gala["h2h_lietot"] = p["h2h_lietot"]
    rez = {
        "parametri": p_gala, "parametri_parbaudei": p, "regulesanas_sezona": sez_reg, "parbaudes_sezona": sez_test,
        "parbaude": metrikas(gala), "parbaude_bez_h2h": met, "parbaude_ar_h2h": met_h, "baze": baze, "baze_zina_nakotni": baze_nak,
        "pa_sezonas_dalam": pa_sezonas_dalam(gala, ref),
        "kalibracija_1": kalibracija(gala, "p1", (gala["hg"] > gala["ag"]).astype(float)),
        "kalibracija_o55": kalibracija(gala, "o55", ((gala["hg"] + gala["ag"]) > 5.5).astype(float)),
        "izveidots": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC"),
    }
    os.makedirs(os.path.dirname(izvade), exist_ok=True)
    with open(izvade, "w", encoding="utf-8") as f:
        json.dump(rez, f, ensure_ascii=False, indent=2, default=float)
    m = rez["parbaude"]
    print(f"\nPārbaude {sez_test} ({m['speles']} spēles), log loss (mazāk = labāk):")
    print(f"  1X2:     modelis {m['logloss_1x2']:.4f} | bāze no iepriekšējām sezonām {baze['logloss_1x2']:.4f} | "
          f"bāze, kas zina šīs sezonas biežumus {baze_nak['logloss_1x2']:.4f}")
    print(f"  O/U 5.5: modelis {m['logloss_o55']:.4f} | bāze no iepriekšējām sezonām {baze['logloss_o55']:.4f} | "
          f"bāze, kas zina šīs sezonas biežumus {baze_nak['logloss_o55']:.4f}")
    for nos, v in rez["pa_sezonas_dalam"].items():
        print(f"  {'Sezonas sākums (45 d)' if nos == 'sakums' else 'Pārējā sezona':22s}: modelis {v['logloss_1x2']:.4f} | bāze {v['baze_1x2']:.4f} ({v['speles']} spēles)")
    print(f"  Neizšķirti pamatlaikā: prognoze {m['neizskirti_prog']:.1%}, fakts {m['neizskirti_fakt']:.1%} "
          f"(iepriekšējās sezonās {baze['biezumi']['X']:.1%}); over 5.5 iepriekš {baze['over55']:.1%}, šosezon "
          f"{baze_nak['over55']:.1%}. H2H {'uzlabo – tiek lietots' if p['h2h_lietot'] else 'neuzlabo – netiek lietots'}.")
    print(f"Gala parametri (no abām sezonām): neizšķirti K={'nav' if not p_gala.get('neiz_k') else int(p_gala['neiz_k'])}, "
          f"c={p_gala.get('neiz_c', 0):+.2f}; neizšķirtu korekcija {p_gala['neizskirts_rho']:.2f}, kopsummas pievilkšana "
          f"{p_gala['totali_kappa']}, izkliede {'Puasons' if not p_gala['nb_r'] else p_gala['nb_r']}.\nSaglabāts: {izvade}")
    return 0


if __name__ == "__main__":
    if "--kalibret" in sys.argv:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import datu_apstrade as da
        raw_db, _ = da.ielasit_db()
        raw_t = da.ielasit_speles()
        dalas = [x for x in (raw_db, raw_t) if x is not None and not x.empty]
        if not dalas:
            print("Nav datu.")
            sys.exit(1)
        vg = pd.concat([x for x in (da.ielasit_db_tabulu("vartsargi"), da.ielasit_tabulu("vartsargi")) if x is not None and not x.empty],
                       ignore_index=True) if any(x is not None for x in (da.ielasit_db_tabulu("vartsargi"), da.ielasit_tabulu("vartsargi"))) else None
        g = spelu_tabula(pd.concat(dalas, ignore_index=True), vg)
        vr = vartsargu_rindas(vg) if vg is not None else None
        vr_xg = None
        try:                                           # xG (ja ir metienu dati un xg_modelis.json)
            import xg as xgm
            met = [x for x in (da.ielasit_db_tabulu("metieni"), da.ielasit_tabulu("metieni")) if x is not None and not x.empty]
            xmod = xgm.ielasit_modeli()
            if met and xmod:
                xgk, vxg = xgm.modela_xg(pd.concat(met, ignore_index=True), xmod, g)
                g = pievienot_xg(g, xgk)
                vr_xg = vartsargu_rindas_xg(vr, vxg)
                print(f"xG: {g['xh'].notna().sum()} no {len(g)} spēlēm ar metienu datiem")
            else:
                print("xG: nav metienu datu vai xg_modelis.json – kalibrēšana bez xG")
        except Exception as ex:
            print(f"xG netiek izmantots ({type(ex).__name__}: {ex})")
        sezonas = sorted(int(s) for s in g["sezona"].unique() if (g["sezona"] == s).sum() > 500)
        sys.exit(kalibret(g, sezonas, vr=vr, vr_xg=vr_xg))
    print(__doc__)
