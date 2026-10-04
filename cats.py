"""
Čats par NHL datiem (CSV failiem).

Kā tas darbojas:
  • Datu slānis (klase Dati) ir drošu, tikai lasāmu "rīku" kopa: komandu statistika, līgas tabula, spēles, spēlētāji, karstie spēlētāji,
    vārtsargi, tiesneši, kalendārs, komandu salīdzinājums. Tie izmanto tās pašas funkcijas, ko lapas, tāpēc skaitļi sakrīt.
  • Ja Streamlit Secrets ir ANTHROPIC_API_KEY, jautājumu saprot Claude: modelis pats izvēlas rīkus, saņem to rezultātus un atbild latviski.
    Modelis nekad neizpilda kodu un neredz CSV failus, tikai rīku atgrieztos rezultātus.
  • Bez atslēgas darbojas vienkāršā meklēšana (atslēgvārdi + komandu/spēlētāju nosaukumi), kas izmanto tos pašus rīkus un parāda tabulas.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import timedelta

import numpy as np
import pandas as pd

import datu_apstrade as da

TOP_MAX = 25
MAX_RINDAS_MODELIM = 25
MAX_KARTAS = 6

# metrikas līgas tabulai: nosaukums → (kolonna kopsavilkumā, apraksts)
METRIKAS = {
    "punkti": ("PTS", "Tabulas punkti"),
    "punkti_pct": ("PTS_pct", "Iegūto punktu daļa no iespējamajiem, %"),
    "varti_sp": ("G_sp", "Gūtie vārti spēlē pamatlaikā"),
    "ielaisti_sp": ("Z_sp", "Ielaistie vārti spēlē pamatlaikā"),
    "starpiba": ("Starpiba", "Vārtu starpība pamatlaikā"),
    "metieni_sp": ("SOG_sp", "Metieni vārtos spēlē pamatlaikā"),
    "pretinieka_metieni_sp": ("SA_sp", "Pretinieka metieni vārtos spēlē pamatlaikā"),
    "metienu_dala": ("SOG_dala", "Metienu daļa %"),
    "pp_pct": ("PP_pct", "Vairākuma efektivitāte %"),
    "pk_pct": ("PK_pct", "Mazākuma efektivitāte %"),
    "noraidijumi_sp": ("PEN_sp", "Saņemtie noraidījumi spēlē pamatlaikā"),
    "izcinitie_noraidijumi_sp": ("DRAW_sp", "Izcīnītie (pretinieka) noraidījumi spēlē"),
    "over_65_pct": ("Over65", "Spēļu daļa, kurās vārtu summa pamatlaikā > 6.5, %"),
    "varti_p1_sp": ("G_p1", "Gūtie vārti 1. periodā spēlē"),
    "varti_p2_sp": ("G_p2", "Gūtie vārti 2. periodā spēlē"),
    "varti_p3_sp": ("G_p3", "Gūtie vārti 3. periodā spēlē"),
    "ielaisti_p1_sp": ("Z_p1", "Ielaistie vārti 1. periodā spēlē"),
    "ielaisti_p2_sp": ("Z_p2", "Ielaistie vārti 2. periodā spēlē"),
    "ielaisti_p3_sp": ("Z_p3", "Ielaistie vārti 3. periodā spēlē"),
}
SPELETAJU_KARTOSANA = ("P", "G", "A", "SOG", "PM", "PIM", "HIT", "BLK", "PPG", "TOI", "P_sp")


# ----------------------------------------------------------------------------
# PALĪGFUNKCIJAS
# ----------------------------------------------------------------------------
def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9\s]", " ", s).strip()


def _skaits(x, noklusejums, mn=1, mx=TOP_MAX):
    try:
        return max(mn, min(mx, int(x)))
    except (TypeError, ValueError):
        return noklusejums


def _noapalot(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if pd.isna(v) else round(float(v), 3)
    if isinstance(v, (pd.Timestamp,)):
        return v.strftime("%Y-%m-%d %H:%M")
    return v


def _tira(obj):
    """Rekursīvi sagatavo objektu JSON: skaitļi noapaļoti, NaN → None (np.float64 ir float apakšklase, tāpēc to json pats neapstrādā)."""
    if isinstance(obj, dict):
        return {str(k): _tira(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_tira(v) for v in obj]
    return _noapalot(obj)


def _json(obj):
    return json.dumps(_tira(obj), ensure_ascii=False)


def _ieraksti(df, max_rindas=MAX_RINDAS_MODELIM):
    return [{k: _noapalot(v) for k, v in r.items()} for r in df.head(max_rindas).to_dict("records")]


class Dati:
    """Visi dati čatam (pandas tabulas, kas jau tiek lietotas lietotnē)."""

    def __init__(self, raw, df, kal=None, sk=None, vg=None, ties_cur=None, ties_prev=None, plan=None, modelis=None):
        self.raw, self.df, self.kal, self.sk, self.vg = raw, df, kal, sk, vg
        self.ties_cur, self.ties_prev, self.plan, self.modelis = ties_cur, ties_prev, plan, modelis

    # ---- komandu atpazīšana ----
    def komandu_atslegas(self):
        out = {}
        for kods, nos in da.KOMANDAS.items():
            n = _norm(nos).split()
            atsl = {kods.lower(), _norm(nos), n[-1]}
            if n[0] not in ("new", "los", "san", "st", "tampa", "salt", "las") and len(n) > 1:
                atsl.add(n[0])
            for a in atsl:
                out.setdefault(a, set()).add(kods)
        return out

    def komandas_tekstaa(self, teksts):
        """Komandu kodi, kas minēti tekstā (pēc parādīšanās secības; nenoteiktie nosaukumi netiek ņemti)."""
        t = " " + _norm(teksts) + " "
        atrasts = []
        for atsl, kodi in self.komandu_atslegas().items():
            if len(kodi) != 1:
                continue
            m = re.search(r"(?<![a-z0-9])" + re.escape(atsl) + r"(?![a-z0-9])", t)
            if m:
                atrasts.append((m.start(), next(iter(kodi))))
        out = []
        for _, k in sorted(atrasts):
            if k not in out:
                out.append(k)
        return out

    def komanda(self, teksts):
        t = _norm(teksts)
        kandidati = self.komandu_atslegas().get(t)
        if kandidati and len(kandidati) == 1:
            return next(iter(kandidati))
        atrasti = self.komandas_tekstaa(teksts)
        if len(atrasti) >= 1:
            return atrasti[0]
        raise ValueError(f"Komanda '{teksts}' nav atpazīta. Lieto 3 burtu kodu (piem. NJD, TOR, NYR) vai pilnu nosaukumu.")

    # ---- datu pārskats (sistēmas ziņojumam) ----
    def apraksts(self):
        d = self.raw["datums_lv"].dt.date
        return {"spelu_skaits": int(len(self.raw)), "no": str(d.min()), "lidz": str(d.max()),
                "komandu_skaits": int(self.df["komanda"].nunique()),
                "ir_speletaju_dati": self.sk is not None, "ir_tiesnesu_dati": self.ties_cur is not None or self.ties_prev is not None}

    # ------------------------------------------------------------------------
    # RĪKI
    # ------------------------------------------------------------------------
    def komandas_statistika(self, komanda, speles="Visas", pedejas=None):
        kods = self.komanda(komanda)
        speles = speles if speles in ("Visas", "Mājās", "Izbraukumā") else "Visas"
        k = da.kopsavilkums(self.df, speles, _skaits(pedejas, None, 1, 82) if pedejas else None)
        if kods not in k.index:
            return {"kluda": f"{kods}: šai izlasei vēl nav datu"}, None
        r = k.loc[kods]
        forma = da.forma(self.df, 5).get(kods, "")
        d = {
            "komanda": f"{da.pilns_nosaukums(kods)} ({kods})", "izlase": speles + (f", pēdējās {int(pedejas)} spēles" if pedejas else ""),
            "speles": int(r.GP), "bilance_U_Z_ZPL": f"{int(r.W)}-{int(r.L)}-{int(r.OTL)}", "punkti": int(r.PTS),
            "punkti_pct": r.PTS_pct, "varti_sp": r.G_sp, "ielaisti_sp": r.Z_sp, "starpiba": int(r.Starpiba),
            "metieni_sp": r.SOG_sp, "pretinieka_metieni_sp": r.SA_sp, "metienu_dala_pct": r.SOG_dala,
            "pp_pct": r.PP_pct, "pk_pct": r.PK_pct, "noraidijumi_sp": r.PEN_sp, "izcinitie_noraidijumi_sp": r.DRAW_sp,
            "over_65_pct": r.Over65, "vid_sodu_minutes_sp": r.PIM_sp,
            "varti_pa_periodiem_sp": {"1": r.G_p1, "2": r.G_p2, "3": r.G_p3},
            "ielaisti_pa_periodiem_sp": {"1": r.Z_p1, "2": r.Z_p2, "3": r.Z_p3},
            "forma_pedejas_5_emoji": forma,
        }
        tab = pd.DataFrame([{k_: v for k_, v in d.items() if not isinstance(v, dict)}])
        return d, tab

    def ligas_tabula(self, metrika="punkti", speles="Visas", pedejas=None, top=10, augosi=False):
        if metrika not in METRIKAS:
            return {"kluda": f"Nezināma metrika. Pieejamās: {', '.join(METRIKAS)}"}, None
        kol, apr = METRIKAS[metrika]
        speles = speles if speles in ("Visas", "Mājās", "Izbraukumā") else "Visas"
        k = da.kopsavilkums(self.df, speles, _skaits(pedejas, None, 1, 82) if pedejas else None)
        k = k.sort_values(kol, ascending=bool(augosi), na_position="last").head(_skaits(top, 10))
        tab = pd.DataFrame({"komanda": [f"{da.pilns_nosaukums(i)} ({i})" for i in k.index], "speles": k.GP.astype(int).values,
                            "punkti": k.PTS.astype(int).values, metrika: k[kol].values})
        d = {"metrika": metrika, "apraksts": apr, "izlase": speles + (f", pēdējās {int(pedejas)} spēles" if pedejas else ""),
             "kartojums": "augošs" if augosi else "dilstošs", "rindas": _ieraksti(tab)}
        return d, tab

    def speles(self, datums=None, komanda=None, pedejas=5):
        x = self.raw
        if komanda:
            kods = self.komanda(komanda)
            x = x[(x["home_team"] == kods) | (x["away_team"] == kods)]
        if datums:
            x = x[x["datums_lv"].dt.strftime("%Y-%m-%d") == str(datums)]
        elif not komanda:                                  # nav ne datuma, ne komandas: pēdējā diena ar spēlēm
            x = x[x["datums_lv"] == x["datums_lv"].max()]
        else:
            x = x.sort_values(["datums_lv", "game_id"]).tail(_skaits(pedejas, 5, 1, 30))
        x = x.sort_values(["datums_lv", "sakums_lv", "game_id"])
        reg = lambda p: x[[f"{p}_p1", f"{p}_p2", f"{p}_p3"]].fillna(0).sum(axis=1).astype(int)  # noqa: E731
        tab = pd.DataFrame({
            "datums_riga": x["datums_lv"].dt.strftime("%Y-%m-%d"), "viesi": x["away_team"], "majas": x["home_team"],
            "rezultats_viesi_majas": x["away_total"].astype(int).astype(str) + "–" + x["home_total"].astype(int).astype(str),
            "beigas": x["spele_beidzas"], "pamatlaika_rezultats": reg("away").astype(str) + "–" + reg("home").astype(str),
            "periodi": [" ".join(f"{int(r[f'away_p{p}'])}:{int(r[f'home_p{p}'])}" for p in (1, 2, 3)) for _, r in x.iterrows()],
        })
        return {"spelu_skaits": int(len(tab)), "rindas": _ieraksti(tab)}, tab

    def _speletaju_tabula(self):
        return da.speletaju_lideri(self.sk) if self.sk is not None else pd.DataFrame()

    def speletaji(self, vards=None, komanda=None, pozicija="Visi", kartot_pec="P", top=10):
        L = self._speletaju_tabula()
        if L.empty:
            return {"kluda": "Spēlētāju dati nav pieejami"}, None
        if vards:
            tokens = _norm(vards).split()
            L = L[[all(t in _norm(n) for t in tokens) for n in L["Speletajs"]]]
        if komanda:
            L = L[L["Komanda"] == self.komanda(komanda)]
        if pozicija == "Uzbrucēji":
            L = L[L["Poz"].isin(["C", "L", "R", "W"])]
        elif pozicija == "Aizsargi":
            L = L[L["Poz"] == "D"]
        kartot_pec = kartot_pec if kartot_pec in SPELETAJU_KARTOSANA else "P"
        L = L.sort_values(kartot_pec, ascending=False).head(_skaits(top, 10))
        tab = L.drop(columns=["playerId"]).rename(columns={"Speletajs": "speletajs", "Komanda": "komanda", "Poz": "poz"})
        return {"kartots_pec": kartot_pec, "rindas": _ieraksti(tab)}, tab

    def karstie_speletaji(self, raditajs="punkti", logs=5, top=10, komanda=None, min_speles=2):
        if self.sk is None:
            return {"kluda": "Spēlētāju dati nav pieejami"}, None
        raditajs = raditajs if raditajs in da.KARSTUMA_METRIKAS else "punkti"
        res = da.karstie_speletaji(self.sk, raditajs, _skaits(logs, 5, 2, 20), _skaits(min_speles, 2, 2, 10))
        res = res[res["z"].notna()] if not res.empty else res
        if komanda and not res.empty:
            res = res[res["Komanda"] == self.komanda(komanda)]
        res = res.head(_skaits(top, 10))
        if res.empty:
            return {"rindas": [], "piezime": "Nav spēlētāju, kas atbilst nosacījumiem (vajag vismaz 2 spēles un rādītāju 2 dažādās spēlēs)."}, None
        tab = pd.DataFrame({"speletajs": res["Speletajs"].values, "komanda": res["Komanda"].values, "poz": res["Poz"].values,
                            "speles_logaa": res["n_w"].astype(int).values, "G": res["G_w"].astype(int).values,
                            "A": res["A_w"].astype(int).values, "P": res["P_w"].astype(int).values,
                            "serija": res["serija"].astype(int).values, "karstuma_indekss": res["z"].values,
                            "kapec": [da.karstuma_teksts(r, raditajs) for _, r in res.iterrows()]})
        return {"raditajs": raditajs, "logs": _skaits(logs, 5, 2, 20),
                "paskaidrojums": "karstuma indekss: 0 = parasts līmenis, 2+ = karsts, 3+ = ļoti karsts", "rindas": _ieraksti(tab)}, tab

    def vartsargi(self, vards=None, komanda=None, min_speles=1, top=10, kartot_pec="SVpct"):
        G = da.vartsargu_lideri(self.vg) if self.vg is not None else pd.DataFrame()
        if G.empty:
            return {"kluda": "Vārtsargu dati nav pieejami"}, None
        if vards:
            tokens = _norm(vards).split()
            G = G[[all(t in _norm(n) for t in tokens) for n in G["Vartsargs"]]]
        if komanda:
            G = G[G["Komanda"] == self.komanda(komanda)]
        G = G[G["GP"] >= _skaits(min_speles, 1, 1, 82)]
        kartot_pec = kartot_pec if kartot_pec in ("SVpct", "GAA", "W", "SV", "GP") else "SVpct"
        G = G.sort_values(kartot_pec, ascending=(kartot_pec == "GAA")).head(_skaits(top, 10))
        tab = G.drop(columns=["playerId"]).rename(columns={"Vartsargs": "vartsargs", "Komanda": "komanda"})
        return {"kartots_pec": kartot_pec, "rindas": _ieraksti(tab)}, tab

    def tiesnesi(self, vards=None, top=10):
        if self.ties_cur is None and self.ties_prev is None:
            return {"kluda": "Tiesnešu dati nav pieejami"}, None
        tab, liga = da.tiesnesu_apkopojums(self.ties_cur, self.ties_prev)
        if tab.empty:
            return {"kluda": "Nav tiesnešu datu"}, None
        if vards:
            tokens = _norm(vards).split()
            tab = tab[[all(t in _norm(n) for t in tokens) for n in tab["vards"].fillna("")]]
        tab = tab.sort_values("kopa", ascending=False).head(_skaits(top, 10))
        out = pd.DataFrame({"tiesnesis": tab["vards"].values, "speles_sosezon": tab["GP_t"].values, "speles_pagajusaja": tab["GP_p"].values,
                            "noraid_sp_sosezon": tab["kopa_t"].values, "noraid_sp_pagajusaja": tab["kopa_p"].values,
                            "kombinets_noraid_sp": tab["kopa"].values, "pret_ligu": tab["kopa_vs_liga"].values, "datu_apjoms": tab["dati"].values})
        d = {"piezime": "minor noraidījumi spēlē (abu komandu kopā, pamatlaikā; bez major, 10 min disciplinārajiem un kautiņiem); kombinēts = 60% pagājušā + 40% šī sezona ar līgas korekciju",
             "ligas_videjais_sosezon": liga["t"]["kopa"], "ligas_videjais_pagajusaja": liga["p"]["kopa"], "rindas": _ieraksti(out)}
        return d, out

    def kalendars(self, dienas=2, komanda=None):
        if self.kal is None or self.kal.empty:
            return {"kluda": "Kalendārs nav pieejams"}, None
        sodien = da.sodien_lv()
        d = self.kal["datums_lv"].dt.date
        x = self.kal[(d >= sodien) & (d <= sodien + timedelta(days=_skaits(dienas, 2, 0, 14)))]
        if komanda:
            kods = self.komanda(komanda)
            x = x[(x["majas_komanda"] == kods) | (x["viesu_komanda"] == kods)]
        x = x.head(40)
        tab = pd.DataFrame({
            "datums_riga": x["datums_lv"].dt.strftime("%Y-%m-%d"), "laiks_riga": x["sakums_lv"].dt.strftime("%H:%M"),
            "viesi": x["viesu_komanda"].values, "majas": x["majas_komanda"].values,
            "galvenie_tiesnesi": [", ".join(da.planotie_vardi(self.plan, g)) or "nav paziņoti" for g in x["game_id"]]})
        return {"sodien_riga": str(sodien), "rindas": _ieraksti(tab, 40)}, tab

    def salidzinat_komandas(self, majas, viesi):
        a, b = self.komanda(majas), self.komanda(viesi)
        ka, kb = da.kopsavilkums(self.df, "Mājās"), da.kopsavilkums(self.df, "Izbraukumā")
        kopa = da.kopsavilkums(self.df, "Visas")

        def rinda(kods, k, nos):
            if kods not in k.index:
                return {"komanda": kods, "izlase": nos, "kluda": "nav datu"}
            r = k.loc[kods]
            return {"komanda": f"{da.pilns_nosaukums(kods)} ({kods})", "izlase": nos, "speles": int(r.GP), "punkti": int(r.PTS),
                    "varti_sp": r.G_sp, "ielaisti_sp": r.Z_sp, "metieni_sp": r.SOG_sp, "pretinieka_metieni_sp": r.SA_sp,
                    "pp_pct": r.PP_pct, "pk_pct": r.PK_pct, "noraidijumi_sp": r.PEN_sp, "over_65_pct": r.Over65}

        tab = pd.DataFrame([rinda(a, ka, "mājas spēles"), rinda(b, kb, "izbraukuma spēles"),
                            rinda(a, kopa, "visas spēles"), rinda(b, kopa, "visas spēles")])
        h2h = self.raw[((self.raw["home_team"] == a) & (self.raw["away_team"] == b)) | ((self.raw["home_team"] == b) & (self.raw["away_team"] == a))]
        d = {"majas": a, "viesi": b, "statistika": _ieraksti(tab),
             "savstarpejas_spheles_sosezon": [f"{r.away_team} @ {r.home_team}: {int(r.away_total)}–{int(r.home_total)} {da.beigu_etikete(r.spele_beidzas)}".strip()
                                              for r in h2h.itertuples()]}
        try:
            import lokacijas
            sak = self.kal[(self.kal["majas_komanda"] == a) & (self.kal["viesu_komanda"] == b)] if self.kal is not None else pd.DataFrame()
            kad = sak["sakums_lv"].iloc[0] if not sak.empty and pd.notna(sak["sakums_lv"].iloc[0]) else pd.Timestamp.now(tz=da.LV_TZ)
            f = lokacijas.speles_faktori(self.df, a, b, kad)
            d["celojums"] = {"attalums_km": f["starp_pilsetam"]["km"], "viesu_back_to_back": f["viesi"]["back_to_back"],
                             "majas_back_to_back": f["majas"]["back_to_back"], "viesu_slodzes_indekss": lokacijas.celojuma_slodze(f["viesi"]),
                             "majas_slodzes_indekss": lokacijas.celojuma_slodze(f["majas"])}
        except Exception:
            pass
        if self.modelis is not None:
            try:
                gatavs = self.modelis.parbaudit_gatavibu(self.df)[0]
                if gatavs:
                    d["modela_prognoze_puasons"] = self.modelis.aprekinat_prognozi_speles(a, b, self.df)
            except Exception:
                pass
        return d, tab

    # ---- izpilde ----
    def izpildit(self, nosaukums, parametri):
        """Izpilda vienu rīku. Atgriež {"teksts": JSON modelim, "tabula": DataFrame vai None}."""
        funkcijas = {"komandas_statistika": self.komandas_statistika, "ligas_tabula": self.ligas_tabula, "speles": self.speles,
                     "speletaji": self.speletaji, "karstie_speletaji": self.karstie_speletaji, "vartsargi": self.vartsargi,
                     "tiesnesi": self.tiesnesi, "kalendars": self.kalendars, "salidzinat_komandas": self.salidzinat_komandas}
        if nosaukums not in funkcijas:
            raise ValueError(f"Nezināms rīks: {nosaukums}")
        d, tab = funkcijas[nosaukums](**(parametri or {}))
        return {"teksts": _json(d), "tabula": tab}


# ----------------------------------------------------------------------------
# RĪKU APRAKSTI MODELIM
# ----------------------------------------------------------------------------
_SPELES = {"type": "string", "enum": ["Visas", "Mājās", "Izbraukumā"], "description": "Which games: all, home only or away only."}
_PEDEJAS = {"type": "integer", "description": "Only the team's last N games (e.g. 5 or 10). Omit for the whole season."}
_KOMANDA = {"type": "string", "description": "Team 3-letter code (e.g. NJD, TOR, NYR) or full name."}
TOOLS = [
    {"name": "komandas_statistika",
     "description": "Season statistics for ONE team: record, points, goals for/against per game, shots, power play %, penalty kill %, penalties, over 6.5 share, goals by period, form. All figures are regulation time only (no overtime).",
     "input_schema": {"type": "object", "properties": {"komanda": _KOMANDA, "speles": _SPELES, "pedejas": _PEDEJAS}, "required": ["komanda"]}},
    {"name": "ligas_tabula",
     "description": "Rank all teams by one metric (top N). Use for questions like 'which team scores most', 'best power play', 'most penalties', 'best form' (use pedejas).",
     "input_schema": {"type": "object", "properties": {
         "metrika": {"type": "string", "enum": list(METRIKAS), "description": "; ".join(f"{k} = {v[1]}" for k, v in METRIKAS.items())},
         "speles": _SPELES, "pedejas": _PEDEJAS, "top": {"type": "integer", "description": "How many teams to return (max 25)."},
         "augosi": {"type": "boolean", "description": "true = ascending order (lowest first)."}}, "required": ["metrika"]}},
    {"name": "speles",
     "description": "Finished game results. Give a date (YYYY-MM-DD, Riga date) and/or a team. With only a team returns its last N games; with nothing returns the latest day.",
     "input_schema": {"type": "object", "properties": {"datums": {"type": "string", "description": "Riga date YYYY-MM-DD."}, "komanda": _KOMANDA,
                                                       "pedejas": {"type": "integer", "description": "Number of last games for a team (default 5)."}}}},
    {"name": "speletaji",
     "description": "Skater season statistics (GP, goals, assists, points, +/-, PIM, shots, hits, blocks, PP goals, avg TOI). Search by player name and/or team, or rank leaders.",
     "input_schema": {"type": "object", "properties": {"vards": {"type": "string", "description": "Player name or surname."}, "komanda": _KOMANDA,
                                                       "pozicija": {"type": "string", "enum": ["Visi", "Uzbrucēji", "Aizsargi"]},
                                                       "kartot_pec": {"type": "string", "enum": list(SPELETAJU_KARTOSANA), "description": "P points, G goals, A assists, SOG shots, PM plus/minus, PIM, HIT, BLK, PPG, TOI, P_sp points per game."},
                                                       "top": {"type": "integer"}}}},
    {"name": "karstie_speletaji",
     "description": "Players on a hot streak: recent form (last N games) versus their expected production, with streak and a short explanation. One game is never enough.",
     "input_schema": {"type": "object", "properties": {"raditajs": {"type": "string", "enum": ["punkti", "vardi", "piespeles"]},
                                                       "logs": {"type": "integer", "description": "Window of last N games (3, 5 or 10)."}, "top": {"type": "integer"},
                                                       "komanda": _KOMANDA, "min_speles": {"type": "integer"}}}},
    {"name": "vartsargi",
     "description": "Goalie season statistics (GP, starts, wins, shots against, saves, goals against, save %, GAA).",
     "input_schema": {"type": "object", "properties": {"vards": {"type": "string"}, "komanda": _KOMANDA, "min_speles": {"type": "integer"}, "top": {"type": "integer"},
                                                       "kartot_pec": {"type": "string", "enum": ["SVpct", "GAA", "W", "SV", "GP"]}}}},
    {"name": "tiesnesi",
     "description": "Referee statistics: penalties per game (both teams, regulation) this season and last season, a combined 60/40 figure and deviation from the league average.",
     "input_schema": {"type": "object", "properties": {"vards": {"type": "string", "description": "Referee name or surname."}, "top": {"type": "integer"}}}},
    {"name": "kalendars",
     "description": "Upcoming games (Riga time) for the next N days, optionally for one team, with the announced main referees.",
     "input_schema": {"type": "object", "properties": {"dienas": {"type": "integer", "description": "Days ahead (0 = today only, max 14)."}, "komanda": _KOMANDA}}},
    {"name": "salidzinat_komandas",
     "description": "Compare the home team and the away team of a game: home/away form, head-to-head this season, travel and rest, and the Poisson model prediction when available.",
     "input_schema": {"type": "object", "properties": {"majas": _KOMANDA, "viesi": _KOMANDA}, "required": ["majas", "viesi"]}},
]


def sistemas_zinojums(dati):
    ap = dati.apraksts()
    return (
        "Tu esi NHL datu palīgs lietotnē ar komandu, spēlētāju, tiesnešu un spēļu statistiku. Atbildi latviešu valodā, īsi un konkrēti.\n"
        "Noteikumi:\n"
        "- Skaitļus ņem TIKAI no rīkiem; neizdomā datus. Ja rīks atbild ar kļūdu vai datu nav, pasaki to.\n"
        "- Ja jautājums nav par šiem datiem (piem., ārpus NHL statistikas), pieklājīgi pasaki, ka vari palīdzēt tikai ar šo datu analīzi.\n"
        "- Statistika (vārti, metieni, noraidījumi, vairākums) ir tikai pamatlaikā, bez papildlaika. Uzvaras, zaudējumi un punkti ir oficiālie.\n"
        "- Spēļu datumi ir pēc Rīgas laika: vakara spēles ASV parādās nākamajā dienā pēc Rīgas laika.\n"
        "- Komandām lieto 3 burtu kodus (NJD, TOR…) vai pilnus nosaukumus. 'Mājas' un 'viesi' ir home un away.\n"
        "- Nesniedz likmju vai finanšu padomus; statistika ir tikai informācijai. Ja sezona ir sākumā, atgādini, ka izlase ir maza.\n"
        f"Dati: {ap['spelu_skaits']} noslēgušās spēles no {ap['no']} līdz {ap['lidz']} (Rīgas datumi), {ap['komandu_skaits']} komandas. "
        f"Šodien (Rīga): {da.sodien_lv()}.")


# ----------------------------------------------------------------------------
# ATBILDE AR CLAUDE (rīku cikls)
# ----------------------------------------------------------------------------
def atbildet_ar_claude(klients, modelis_nos, vesture, dati, max_kartas=MAX_KARTAS, max_tokens=1200):
    """
    vesture: [{"role": "user"/"assistant", "content": "teksts"}, ...] (beidzas ar lietotāja jautājumu).
    Atgriež (atbildes teksts, [(rīks, parametri, DataFrame), ...]).
    """
    messages = [{"role": z["role"], "content": z["content"]} for z in vesture]
    tabulas = []
    for _ in range(max_kartas):
        resp = klients.messages.create(model=modelis_nos, max_tokens=max_tokens, system=sistemas_zinojums(dati), tools=TOOLS, messages=messages)
        if resp.stop_reason != "tool_use":
            teksts = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
            return teksts or "Neizdevās sagatavot atbildi. Mēģini pārformulēt jautājumu.", tabulas
        messages.append({"role": "assistant", "content": resp.content})
        rezultati = []
        for b in resp.content:
            if getattr(b, "type", "") != "tool_use":
                continue
            try:
                out = dati.izpildit(b.name, dict(b.input))
                rezultati.append({"type": "tool_result", "tool_use_id": b.id, "content": out["teksts"]})
                if out["tabula"] is not None:
                    tabulas.append((b.name, dict(b.input), out["tabula"]))
            except Exception as e:      # kļūda tiek nodota modelim, lai tas varētu pārformulēt vai paskaidrot
                rezultati.append({"type": "tool_result", "tool_use_id": b.id, "content": f"Kļūda: {e}", "is_error": True})
        messages.append({"role": "user", "content": rezultati})
    return "Atbildei vajadzēja pārāk daudz soļu. Pamēģini jautāt konkrētāk (piemēram, norādi komandu vai spēlētāju).", tabulas


# ----------------------------------------------------------------------------
# VIENKĀRŠĀ MEKLĒŠANA (bez API atslēgas)
# ----------------------------------------------------------------------------
# bieži jautājuma vārdi, ko nedrīkst uzskatīt par spēlētāja vai tiesneša uzvārdu
VAJADZIGIE_VARDI = {"speles", "spele", "forma", "punkti", "vardi", "karstie", "karstais", "karstakie", "komandas", "komanda", "tabula",
                    "pedejas", "pedejo", "majas", "viesu", "labakie", "labakais", "rezultati", "tiesnesi", "vartsargi", "speletaji"}


def _pedejo_skaits(t):
    m = re.search(r"pedej\w*\s+(\d{1,2})", t) or re.search(r"(\d{1,2})\s+pedej", t)
    return int(m.group(1)) if m else None


def vienkarsa_meklesana(jautajums, dati):
    """Atslēgvārdu meklēšana: izvēlas rīku pēc vārdiem tekstā un komandu/spēlētāju nosaukumiem. Atgriež (teksts, [(rīks, parametri, tabula)])."""
    t = _norm(jautajums)
    komandas = dati.komandas_tekstaa(jautajums)
    n = _pedejo_skaits(t)
    scope = "Mājās" if re.search(r"\bmajas\b|\bmajaa?s?\b|\bmajinieki\b", t) else ("Izbraukumā" if "izbrauk" in t or "viesu" in t else "Visas")
    dienas_rez = None
    if "vakar" in t:
        dienas_rez = str(da.sodien_lv() - timedelta(days=1))
    elif "sodien" in t and not re.search(r"kalendar|nakam|spelees", t):
        dienas_rez = str(da.sodien_lv())

    def sauc(rikas, **p):
        d = dati.izpildit(rikas, p)
        return [(rikas, p, d["tabula"])] if d["tabula"] is not None else []

    def atrast_vardu(tabula_vardi):
        gabali = [w for w in t.split() if len(w) >= 4 and w not in VAJADZIGIE_VARDI]
        for w in gabali:
            tr = [v for v in tabula_vardi if w in _norm(v).split()]
            if tr:
                return w
        return None

    try:
        if re.search(r"tiesnes|referee|tiesnesi", t):
            if dati.ties_cur is not None or dati.ties_prev is not None:
                tab, _ = da.tiesnesu_apkopojums(dati.ties_cur, dati.ties_prev)
                return "Tiesnešu statistika:", sauc("tiesnesi", vards=atrast_vardu(tab["vards"].dropna()), top=10)
        L = dati._speletaju_tabula()
        v = atrast_vardu(L["Speletajs"]) if not L.empty else None
        if v:                                              # minēts konkrēts spēlētājs
            return f"Spēlētāja statistika («{v}»):", sauc("speletaji", vards=v, top=10, **({"komanda": komandas[0]} if komandas else {}))
        if "karst" in t:
            rad = "vardi" if "vard" in t else ("piespeles" if "piesp" in t else "punkti")
            return "Karstākie spēlētāji pēdējās spēlēs:", sauc("karstie_speletaji", raditajs=rad, logs=n or 5, top=10,
                                                                 **({"komanda": komandas[0]} if komandas else {}))
        if "vartsarg" in t:
            G = da.vartsargu_lideri(dati.vg) if dati.vg is not None else pd.DataFrame()
            v = atrast_vardu(G["Vartsargs"]) if not G.empty else None
            return "Vārtsargu statistika:", sauc("vartsargi", vards=v, **({"komanda": komandas[0]} if komandas else {}), top=10)
        if re.search(r"kalendar|nakam\w* spel|rit\b|spelees|nakamaj", t):
            return "Tuvākās spēles:", sauc("kalendars", dienas=1 if "rit" in t or "sodien" in t else 3, **({"komanda": komandas[0]} if komandas else {}))
        if komandas and re.search(r"forma|statistik|bilance|radit", t) or (len(komandas) == 1 and re.search(r"majas|izbrauk|viesu|majinieki", t)):
            return f"Komandas statistika ({komandas[0]}):", sauc("komandas_statistika", komanda=komandas[0], speles=scope, **({"pedejas": n} if n else {}))
        if re.search(r"rezultat|vakar|izspel|uzvarej|zaudej", t) and not re.search(r"speletaj", t):
            p = {"pedejas": n or 5}
            if komandas:
                p["komanda"] = komandas[0]
            if dienas_rez:
                p["datums"] = dienas_rez
            return "Spēļu rezultāti:", sauc("speles", **p)
        if len(komandas) >= 2:
            return f"Komandu salīdzinājums ({komandas[1]} pie {komandas[0]}):", sauc("salidzinat_komandas", majas=komandas[0], viesi=komandas[1])
        if re.search(r"speletaj|punkt|piesp|assist|goals|labakie? uzbruc|aizsarg", t):
            kart = "G" if re.search(r"\bvard", t) and "komand" not in t else ("A" if "piesp" in t or "assist" in t else "P")
            p = {"kartot_pec": kart, "top": 10}
            if v:
                p["vards"] = v
            if komandas:
                p["komanda"] = komandas[0]
            if "aizsarg" in t:
                p["pozicija"] = "Aizsargi"
            return "Spēlētāju statistika:", sauc("speletaji", **p)
        if len(komandas) == 1 and not re.search(r"\btop\b|labak|tabula", t):
            return f"Komandas statistika ({komandas[0]}):", sauc("komandas_statistika", komanda=komandas[0], speles=scope, **({"pedejas": n} if n else {}))
        metrika = "punkti"
        for rx, m in ((r"noraid|sod", "noraidijumi_sp"), (r"powerplay|vairakum|\bpp\b", "pp_pct"), (r"mazakum|\bpk\b", "pk_pct"),
                      (r"over|summa", "over_65_pct"), (r"metien|\bsog\b", "metieni_sp"), (r"ielaist", "ielaisti_sp"), (r"vart|uzbruk", "varti_sp")):
            if re.search(rx, t):
                metrika = m
                break
        if re.search(r"\btop\b|labak|tabula|lidz|visvairak|vislielak|forma|lielak", t) or "komand" in t:
            return "Komandu tabula:", sauc("ligas_tabula", metrika=metrika, speles=scope, top=10, **({"pedejas": n} if n else {}))
    except ValueError as e:
        return str(e), []
    return ("Neatradu atbilstošus datus. Pamēģini, piemēram: «NJD forma pēdējās 5 spēlēs», «kuras komandas vairāk noraidījumu», "
            "«Hughes punkti», «karstākie spēlētāji», «vakardienas rezultāti», «tiesneši» vai «TOR pret MTL»."), []
