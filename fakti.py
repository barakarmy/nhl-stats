"""
fakti.py – "Interesanti fakti": nestandarta spēļu gaitas statistika no vārtu notikumiem (goal by goal).

Ievade (tie paši CSV, ko raksta nhl_dati.py):
  - speles  (sezonas/speles.csv):  game_id, datums, home_team, away_team, home_total, away_total,
                                home_p1..p3, away_p1..p3, spele_beidzas (REG / OT / SO)
  - varti   (sezonas/varti.csv):   game_id, period, period_type (REG / OT / SO), laiks "MM:SS", komanda,
                                home_score, away_score (rezultāts pēc šiem vārtiem)

Izvade: Python saraksti/vārdnīcas, kas gatavi JSON (front-end tabulām), un pandas DataFrame lietotnei.

1) Comebacks: katrai spēlei tiek iets cauri vārtiem hronoloģiski; stāvokļa mainīgie atceras rezultātu un katras komandas
   lielāko deficītu (kad un pie kāda rezultāta tas bija). Ja komanda bija iedzinējos ar ≥ 2 vārtiem un spēli uzvarēja
   (pamatlaikā, papildlaikā vai metienu sērijā), tas ir comeback.
2) Trešā perioda karaļi: rezultāts pēc 2. perioda (p1 + p2) un spēles iznākums – cik bieži komanda uzvar, ja 3. periodu
   sāk iedzinējos (kā arī: noturētās vadības, neizšķirts pēc 2. perioda).

Pēcspēles metienu sērijas "vārti" netiek skaitīti rezultāta gaitā (tie nav vārti spēlē); uzvarētājs tiek ņemts no
oficiālā gala rezultāta (home_total / away_total, kur metienu sērijas uzvarētājam pieskaitīti +1 vārti).
"""
import json

import pandas as pd

MIN_DEFICITS = 2                 # comeback = uzvara pēc vismaz šāda vārtu deficīta


def _laiks_sek(laiks):
    """'MM:SS' → sekundes periodā (kārtošanai)."""
    try:
        m, s = str(laiks).split(":")
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return 0


def _iznakums(speles_rinda, komanda):
    """W / L / OTL komandai pēc oficiālā gala rezultāta."""
    maj = speles_rinda["home_team"] == komanda
    savi, pret = (speles_rinda["home_total"], speles_rinda["away_total"]) if maj else (speles_rinda["away_total"], speles_rinda["home_total"])
    if savi > pret:
        return "W"
    return "OTL" if str(speles_rinda.get("spele_beidzas", "REG")).upper() in ("OT", "SO") else "L"


def spelu_gaita(speles, varti):
    """
    Iet cauri katras spēles vārtiem hronoloģiski un katrai komandai atgriež spēles gaitas kopsavilkumu:
    lielākais deficīts un vadība, kad tie bija, gala iznākums. Spēles ar nepilniem vārtu datiem tiek izlaistas.
    Atgriež sarakstu: [{game_id, datums, komanda, pretinieks, majas, max_deficits, deficita_brīdis, max_vadiba, iznakums, beigas, gala}]
    """
    rezultati = []
    v = varti[varti["period_type"].astype(str).str.upper() != "SO"].copy()
    v["_sek"] = v["laiks"].map(_laiks_sek)
    pec_speles = {gid: g.sort_values(["period", "_sek"]) for gid, g in v.groupby("game_id")}
    for s in speles.itertuples(index=False):
        sr = s._asdict()
        home, away, gid = sr["home_team"], sr["away_team"], sr["game_id"]
        beigas = str(sr.get("spele_beidzas", "REG")).upper()
        g = pec_speles.get(gid, pd.DataFrame(columns=v.columns))
        # pārbaude: vārtu skaits datos = gala rezultāts (bez metienu sērijas uzvaras vārtiem)
        so_h = 1 if beigas == "SO" and sr["home_total"] > sr["away_total"] else 0
        so_a = 1 if beigas == "SO" and sr["away_total"] > sr["home_total"] else 0
        if len(g) != (sr["home_total"] - so_h) + (sr["away_total"] - so_a):
            continue
        # --- stāvoklis (state): rezultāts un katras komandas lielākais deficīts / vadība ---
        rez = {home: 0, away: 0}
        stav = {k: {"max_def": 0, "def_brids": None, "def_rez": None, "max_vad": 0} for k in (home, away)}
        for gol in g.itertuples(index=False):
            k = gol.komanda if gol.komanda in rez else None
            if k is None:
                continue
            rez[k] += 1
            for kom, pret in ((home, away), (away, home)):
                starp = rez[pret] - rez[kom]                     # > 0 = komanda iedzinējos
                if starp > stav[kom]["max_def"]:
                    stav[kom].update(max_def=starp, def_brids=(int(gol.period), str(gol.laiks)),
                                     def_rez=f"{rez[home]}:{rez[away]}")
                stav[kom]["max_vad"] = max(stav[kom]["max_vad"], -starp)
        for kom, pret in ((home, away), (away, home)):
            rezultati.append({
                "game_id": int(gid), "datums": str(sr.get("datums"))[:10], "komanda": kom, "pretinieks": pret,
                "majas": kom == home, "max_deficits": stav[kom]["max_def"], "deficita_brids": stav[kom]["def_brids"],
                "deficita_rezultats": stav[kom]["def_rez"], "max_vadiba": stav[kom]["max_vad"],
                "iznakums": _iznakums(sr, kom), "beigas": beigas,
                "gala": f"{int(sr['home_total'])}:{int(sr['away_total'])}"})
    return rezultati


def comebacks(gaita, min_def=MIN_DEFICITS):
    """Uzvaras pēc ≥ min_def vārtu deficīta (jaunākās/lielākās augšā)."""
    c = [r for r in gaita if r["iznakums"] == "W" and r["max_deficits"] >= min_def]
    c = sorted(c, key=lambda r: r["datums"], reverse=True)              # jaunākās vispirms ...
    return sorted(c, key=lambda r: -r["max_deficits"])                  # ... lielākais deficīts augšā (stabila kārtošana)


def zaudetas_vadibas(gaita, min_vad=MIN_DEFICITS):
    """Pretējais: zaudējumi pēc ≥ min_vad vārtu vadības (izlaistās vadības)."""
    return sorted([r for r in gaita if r["iznakums"] != "W" and r["max_vadiba"] >= min_vad], key=lambda r: -r["max_vadiba"])


def tresa_perioda_stat(speles):
    """
    Rezultāts pēc 2. perioda un iznākums katrai komandai.
    Atgriež DataFrame (index = komanda): iedz_sp, iedz_W, iedz_OTL, iedz_pct, vad_sp, vad_W, vad_pct, neizs_sp, neizs_W, neizs_pct.
    """
    rindas = []
    for s in speles.itertuples(index=False):
        sr = s._asdict()
        h2 = sr["home_p1"] + sr["home_p2"]
        a2 = sr["away_p1"] + sr["away_p2"]
        for kom, savi, pret in ((sr["home_team"], h2, a2), (sr["away_team"], a2, h2)):
            st = "iedz" if savi < pret else ("vad" if savi > pret else "neizs")
            rindas.append({"komanda": kom, "stavoklis": st, "iznakums": _iznakums(sr, kom)})
    df = pd.DataFrame(rindas)
    if df.empty:
        return pd.DataFrame()
    out = pd.DataFrame(index=sorted(df["komanda"].unique()))
    for st in ("iedz", "vad", "neizs"):
        x = df[df["stavoklis"] == st]
        out[f"{st}_sp"] = x.groupby("komanda").size()
        out[f"{st}_W"] = x[x["iznakums"] == "W"].groupby("komanda").size()
        out[f"{st}_OTL"] = x[x["iznakums"] == "OTL"].groupby("komanda").size()
    out = out.fillna(0).astype(int)
    for st in ("iedz", "vad", "neizs"):
        out[f"{st}_pct"] = (out[f"{st}_W"] / out[f"{st}_sp"] * 100).where(out[f"{st}_sp"] > 0)
    out.index.name = "komanda"
    return out


def komandu_kopsavilkums(gaita, tresais):
    """Viena rinda katrai komandai: comeback skaits, lielākais comeback, izlaistās vadības + 3. perioda statistika."""
    cb, zv = comebacks(gaita), zaudetas_vadibas(gaita)
    kom = sorted({r["komanda"] for r in gaita} | set(tresais.index))
    df = pd.DataFrame(index=kom)
    df["comebacks"] = pd.Series({k: sum(1 for r in cb if r["komanda"] == k) for k in kom})
    df["lielakais_cb"] = pd.Series({k: max([r["max_deficits"] for r in cb if r["komanda"] == k] or [0]) for k in kom})
    df["izlaistas_vadibas"] = pd.Series({k: sum(1 for r in zv if r["komanda"] == k) for k in kom})
    df = df.join(tresais, how="left")
    df.index.name = "komanda"
    return df


def fakti_json(speles, varti, indent=None):
    """Viss kopā JSON virknē priekš front-end: {comebacks: [...], zaudetas_vadibas: [...], komandas: [...]}."""
    gaita = spelu_gaita(speles, varti)
    kops = komandu_kopsavilkums(gaita, tresa_perioda_stat(speles)).reset_index()
    dati = {
        "comebacks": comebacks(gaita),
        "zaudetas_vadibas": zaudetas_vadibas(gaita),
        "komandas": json.loads(kops.to_json(orient="records", force_ascii=False)),
    }
    return json.dumps(dati, ensure_ascii=False, indent=indent, default=str)


# ============================================================================
# SITUĀCIJAS: pirmie vārti, rezultāts pēc 1. / 2. perioda, izlīdzinājumi beigās, izcēlumi
# ============================================================================
VELU_IZL_NO_SEK = 18 * 60        # izlīdzinājums "beigās" = 3. perioda pēdējās 2 minūtes (laiks ≥ 18:00)
IZCELUMA_MIN_SP = 3              # izcēlumam vajag vismaz tik spēļu šajā situācijā
IZCELUMA_MIN_STARP = 0.30        # ... un vismaz 30 procentpunktu atšķirību no līgas vidējā


def spelu_ieraksti(speles, varti):
    """
    Viens ieraksts katrai komandai katrā spēlē: iznākums, vārtu starpība pēc 1. un 2. perioda (no periodu rezultātiem),
    kurš guva pirmos vārtus, un izlīdzinājumi 3. perioda pēdējās 2 minūtēs (no vārtu notikumiem).
    Vārtu notikumu lauki ir None spēlēm ar nepilniem vārtu datiem.
    """
    v = varti[varti["period_type"].astype(str).str.upper() != "SO"].copy()
    v["sek"] = v["laiks"].map(_laiks_sek)
    pec_speles = {gid: g.sort_values(["period", "sek"]) for gid, g in v.groupby("game_id")}
    out = []
    for s in speles.itertuples(index=False):
        sr = s._asdict()
        home, away, gid = sr["home_team"], sr["away_team"], sr["game_id"]
        beigas = str(sr.get("spele_beidzas", "REG")).upper()
        g = pec_speles.get(gid, pd.DataFrame(columns=v.columns))
        so_h = 1 if beigas == "SO" and sr["home_total"] > sr["away_total"] else 0
        so_a = 1 if beigas == "SO" and sr["away_total"] > sr["home_total"] else 0
        pilns = len(g) == (sr["home_total"] - so_h) + (sr["away_total"] - so_a)
        pirmie, izl = None, []                            # izl: [(komanda, laiks)] – izlīdzinājumi beigās
        if pilns and len(g):
            pirmie = g.iloc[0]["komanda"]
            rez = {home: 0, away: 0}
            for gol in g.itertuples(index=False):
                if gol.komanda not in rez:
                    continue
                rez[gol.komanda] += 1
                if int(gol.period) == 3 and gol.sek >= VELU_IZL_NO_SEK and rez[home] == rez[away]:
                    izl.append((gol.komanda, str(gol.laiks)))
        h1, a1 = sr["home_p1"], sr["away_p1"]
        h2, a2 = h1 + sr["home_p2"], a1 + sr["away_p2"]
        for kom, pret, d1, d2 in ((home, away, h1 - a1, h2 - a2), (away, home, a1 - h1, a2 - h2)):
            out.append({
                "game_id": int(gid), "datums": str(sr.get("datums"))[:10], "komanda": kom, "pretinieks": pret, "majas": kom == home,
                "iznakums": _iznakums(sr, kom), "beigas": beigas, "gala": f"{int(sr['home_total'])}:{int(sr['away_total'])}",
                "d1": int(d1), "d2": int(d2),
                "pirmie": (None if not pilns or pirmie is None else ("savi" if pirmie == kom else "pret")),
                "izl_savi": [t for k_, t in izl if k_ == kom] if pilns else None,
                "izl_pret": [t for k_, t in izl if k_ != kom] if pilns else None,
            })
    return out


def _atlase(ier, brids, stav, starp=None):
    """Ieraksti noteiktā situācijā. brids: "pirmie" | "p1" | "p2"; stav: "vad" | "iedz" | "neizs"; starp: 1, 2, 3 (=3+) vai None."""
    rez = []
    for r in ier:
        if brids == "pirmie":
            if r["pirmie"] is None:
                continue
            if (stav == "vad" and r["pirmie"] == "savi") or (stav == "iedz" and r["pirmie"] == "pret"):
                rez.append(r)
            continue
        d = r["d1"] if brids == "p1" else r["d2"]
        if stav == "neizs":
            ok = d == 0
        else:
            dd = d if stav == "vad" else -d
            ok = dd >= 1 and (starp is None or (dd >= 3 if starp == 3 else dd == starp))
        if ok:
            rez.append(r)
    return rez


def situaciju_tabula(ier, brids, stav, starp=None):
    """Komandu bilance izvēlētajā situācijā: sp, W, L, OTL, win_pct, pts_pct (index = komanda) un līgas vidējais win %."""
    x = pd.DataFrame(_atlase(ier, brids, stav, starp))
    kom = sorted({r["komanda"] for r in ier})
    out = pd.DataFrame(index=kom)
    if x.empty:
        out[["sp", "W", "L", "OTL"]] = 0
        out["win_pct"] = out["pts_pct"] = float("nan")
        out.index.name = "komanda"
        return out, float("nan")
    for kods in ("W", "L", "OTL"):
        out[kods] = x[x["iznakums"] == kods].groupby("komanda").size()
    out["sp"] = x.groupby("komanda").size()
    out = out.fillna(0).astype(int)
    out["win_pct"] = (out["W"] / out["sp"] * 100).where(out["sp"] > 0)
    out["pts_pct"] = ((2 * out["W"] + out["OTL"]) / (2 * out["sp"]) * 100).where(out["sp"] > 0)
    out.index.name = "komanda"
    liga = len(x[x["iznakums"] == "W"]) / len(x) * 100
    return out, liga


def velie_izlidzinajumi(ier):
    """Izlīdzinājumi 3. perioda pēdējās 2 minūtēs: notikumi un komandu kopsavilkums (izlīdzināja, pret to izlīdzināja, iznākumi)."""
    notik = [dict(r, laiks=t) for r in ier if r["izl_savi"] for t in r["izl_savi"]]
    kom = sorted({r["komanda"] for r in ier})
    df = pd.DataFrame(index=kom)
    df["izlidzinaja"] = pd.Series({k: sum(len(r["izl_savi"] or []) for r in ier if r["komanda"] == k) for k in kom})
    df["izl_W"] = pd.Series({k: sum(1 for r in ier if r["komanda"] == k and r["izl_savi"] and r["iznakums"] == "W") for k in kom})
    df["pret_izlidzinaja"] = pd.Series({k: sum(len(r["izl_pret"] or []) for r in ier if r["komanda"] == k) for k in kom})
    df.index.name = "komanda"
    return sorted(notik, key=lambda r: r["datums"], reverse=True), df


IZCELUMU_SITUACIJAS = [          # (teksta daļa, brīdis, stāvoklis)
    ("gūstot pirmos vārtus", "pirmie", "vad"), ("ielaižot pirmos vārtus", "pirmie", "iedz"),
    ("vadot pēc 1. perioda", "p1", "vad"), ("esot iedzinējos pēc 1. perioda", "p1", "iedz"),
    ("vadot pēc 2. perioda", "p2", "vad"), ("esot iedzinējos pēc 2. perioda", "p2", "iedz"), ("ar neizšķirtu pēc 2. perioda", "p2", "neizs"),
]


def izcelumi(ier, min_sp=IZCELUMA_MIN_SP, min_starp=IZCELUMA_MIN_STARP, max_skaits=10):
    """
    Komandas, kas kādā situācijā ļoti atšķiras no līgas: vismaz min_sp spēles, win % atšķirība ≥ min_starp
    un statistiski ticama novirze (z ≥ 1.64 pret līgas vidējo). Atgriež [{komanda, teksts, z, augstak}].
    """
    rez = []
    for nos, br, sv in IZCELUMU_SITUACIJAS:
        t, liga = situaciju_tabula(ier, br, sv)
        if t.empty or pd.isna(liga):
            continue
        p0 = liga / 100
        for kom, r in t[t["sp"] >= min_sp].iterrows():
            p = r["W"] / r["sp"]
            if abs(p - p0) < min_starp or p0 <= 0 or p0 >= 1:
                continue
            z = (p - p0) / ((p0 * (1 - p0) / r["sp"]) ** 0.5)
            if abs(z) < 1.64:
                continue
            rez.append({"komanda": kom, "z": float(z), "augstak": p > p0,
                        "teksts": f"{int(r['W'])} win no {int(r['sp'])} spēlēm {nos} ({p * 100:.0f}%; līgā vidēji {liga:.0f}%)"})
    _, vi = velie_izlidzinajumi(ier)
    for kom, r in vi[vi["izlidzinaja"] >= 2].iterrows():
        rez.append({"komanda": kom, "z": 2.0 + r["izlidzinaja"] / 10, "augstak": True,
                    "teksts": f"{int(r['izlidzinaja'])} reizes izlīdzinājusi 3. perioda pēdējās 2 minūtēs"})
    return sorted(rez, key=lambda x: -abs(x["z"]))[:max_skaits]


# ============================================================================
# VĀRTSARGU SAUSĀS SĒRIJAS (shutout streaks): minūtes pēc kārtas bez ielaistiem vārtiem
# ============================================================================
SAUSAS_MIN_SEK = 120 * 60        # sadaļā rāda sērijas, kas sasniegušas vismaz 120 minūtes


def _toi_sek(toi):
    try:
        m, s_ = str(toi).split(":")
        return int(m) * 60 + int(s_)
    except (ValueError, AttributeError):
        return 0


def sausas_serijas(vartsargi, varti, min_sek=SAUSAS_MIN_SEK):
    """
    Katram vārtsargam iet cauri viņa spēlēm hronoloģiski un skaita laiku laukumā bez ielaistiem vārtiem.
    Vārtsarga laiks spēlē: sākumā stājies vārtos (starter) – no 0 līdz savam TOI; maiņā ienākušais – no sākumsarga TOI beigām.
    Vārti, kas gūti, kamēr vārtsargs nebija laukumā (piem., tukšos vārtos), viņa sēriju nepārtrauc. Metienu sērija netiek skaitīta.
    Atgriež sarakstu: aktīvās sērijas ≥ min_sek un sērijas ≥ min_sek, kas pārtrauktas vārtsarga pēdējā spēlē.
    """
    v = varti[varti["period_type"].astype(str).str.upper() != "SO"].copy()
    v["sek"] = [(int(p_) - 1) * 1200 + _laiks_sek(t) for p_, t in zip(v["period"], v["laiks"])]
    vg = vartsargi.copy()
    vg["toi_s"] = vg["toi"].map(_toi_sek)
    vg = vg[vg["toi_s"] > 0]
    starta = vg[vg["starter"].astype(str).str.lower().isin(["true", "1"])].set_index(["game_id", "team"])["toi_s"].to_dict()
    rez = []
    for pid, g in vg.sort_values(["datums", "game_id"]).groupby("playerId"):
        cur, sakums, pedeja_partr, pedeja_spele = 0, None, None, None
        for r in g.itertuples(index=False):
            is_starter = str(r.starter).lower() in ("true", "1")
            no = 0 if is_starter else starta.get((r.game_id, r.team), 0)
            lidz = no + r.toi_s
            pret = v[(v["game_id"] == r.game_id) & (v["komanda"] != r.team) & (v["sek"] >= no) & (v["sek"] < lidz)]["sek"].sort_values()
            punkts, partr_speles = no, None
            if cur == 0:
                sakums = (str(r.datums)[:10], int(r.game_id))
            for s_ in pret:
                cur += s_ - punkts
                if cur >= min_sek and (partr_speles is None or cur > partr_speles["sek"]):
                    per = min(int(s_ // 1200) + 1, 4)
                    t_ = int(s_ - (per - 1) * 1200)
                    partr_speles = {"sek": cur, "datums": str(r.datums)[:10], "game_id": int(r.game_id),
                                    "brids": f"{per if per <= 3 else 'OT'}{'. periods' if per <= 3 else ''} {t_ // 60:02d}:{t_ % 60:02d}"}
                cur, punkts = 0, s_
                sakums = (str(r.datums)[:10], int(r.game_id))
            cur += lidz - punkts
            pedeja_partr = partr_speles                   # tikai pēdējā spēlē pārtrauktā sērija paliek redzama
            pedeja_spele = r
        if pedeja_spele is None:
            continue
        pamats = {"playerId": int(pid), "vards": pedeja_spele.vards, "komanda": pedeja_spele.team,
                  "pedeja_spele": str(pedeja_spele.datums)[:10], "pedeja_game_id": int(pedeja_spele.game_id)}
        if cur >= min_sek:
            rez.append(dict(pamats, aktiva=True, sek=int(cur), sakums=sakums[0] if sakums else None))
        if pedeja_partr:
            rez.append(dict(pamats, aktiva=False, sek=int(pedeja_partr["sek"]), partraukta=pedeja_partr["datums"],
                            partraukta_game_id=pedeja_partr["game_id"], partraukta_brids=pedeja_partr["brids"]))
    return sorted(rez, key=lambda x: (not x["aktiva"], -x["sek"]))


def shutouts(vartsargi):
    """Shutout (sausā spēle) katram vārtsargam: uzvara bez ielaistiem vārtiem, nostāvot visu spēli vienam (playerId → skaits)."""
    vg = vartsargi.copy()
    vg["toi_s"] = vg["toi"].map(_toi_sek)
    sp = vg[vg["toi_s"] > 0]
    vieni = sp.groupby(["game_id", "team"])["playerId"].transform("count") == 1
    so = sp[vieni & (sp["goalsAgainst"].fillna(1) == 0) & (sp["decision"].astype(str).str.upper() == "W")]
    return so.groupby("playerId").size()


if __name__ == "__main__":                  # python fakti.py → sezonas/fakti.json
    import os
    mape = os.environ.get("NHL_DATU_MAPE", "sezonas")
    sp = pd.read_csv(os.path.join(mape, "speles.csv"))
    va = pd.read_csv(os.path.join(mape, "varti.csv"))
    with open(os.path.join(mape, "fakti.json"), "w", encoding="utf-8") as f:
        f.write(fakti_json(sp, va, indent=2))
    print("Saglabāts", os.path.join(mape, "fakti.json"))
