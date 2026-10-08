"""
prognozes_arhivs.py – modeļa prognožu "momentuzņēmums" katrā koeficientu ielādē → sezonas/prognozes_arhivs.csv

Palaiž darbplūsma "NHL Odds" uzreiz pēc koeficienti.py. Katrai vēl nesāktajai spēlei, kurai ir koeficienti, saglabā:
- modeļa varbūtības TAJĀ BRĪDĪ (tikai no datiem, kas bija pieejami pirms spēles): 1X2 pamatlaikā, uzvarētājs ar OT,
  over pilnai spēlei (ar OT) Pinnacle galvenajai totāla līnijai;
- tā paša brīža Pinnacle koeficientus un labākos koeficientus (1, X, 2, over, under).
Vēlāk (lietotnē) tos salīdzina ar spēles rezultātu un ar pēdējiem zināmajiem koeficientiem pirms spēles (CLV).
Viena rinda = spēle × ielāde; vecās rindas netiek mainītas (godīga pārbaude bez "skatīšanās nākotnē").
"""
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import datu_apstrade as da          # noqa: E402
import modelis                      # noqa: E402

FAILS = os.path.join(BASE, "sezonas", "prognozes_arhivs.csv")


def _et_datums(t):
    """Spēles datums pēc ASV austrumu laika (kā NHL kalendārā) – atpūtas dienu skaitīšanai."""
    return (pd.Timestamp(t).tz_convert("America/New_York")).tz_localize(None).normalize()


def atputas_pazimes(g, kal, tagad):
    """Atpūta un ceļš nākamajām spēlēm: aizvadītās spēles (g) + kalendārā ieplānotās (ieskaitot citas nākotnes spēles)."""
    nak = kal[kal["sakums_utc"] > tagad].copy()
    nak = pd.DataFrame({"game_id": pd.to_numeric(nak["game_id"], errors="coerce").astype("int64"),
                        "datums": nak["sakums_utc"].map(_et_datums), "home": nak["majas_komanda"], "away": nak["viesu_komanda"],
                        "sezona": int(g["sezona"].max()), "po": (nak.get("speles_tips", "RS") == "PO").astype(int) if "speles_tips" in nak else 0,
                        "hg": 0, "ag": 0})
    pag = g[["game_id", "datums", "home", "away", "sezona", "po", "hg", "ag"]]
    viss = pd.concat([pag, nak], ignore_index=True).sort_values(["datums", "game_id"]).reset_index(drop=True)
    viss = modelis.pievienot_atputu(viss.drop(columns=[c for c in ("b2b_h", "b2b_a", "cels_h", "cels_a") if c in viss.columns]))
    return viss[viss["game_id"].isin(set(nak["game_id"]))].set_index("game_id")


def _koef(x, bk, tirgus, izn, lin=None):
    y = x[(x["tirgus"] == tirgus) & (x["iznakums"] == izn)]
    if lin is not None:
        y = y[(y["linija"] - lin).abs() < 1e-9]
    if bk:
        y = y[y["bukmeikers"] == bk]
    if y.empty:
        return np.nan
    return float(y["koef"].iloc[0]) if bk else float(y["koef"].max())


def main():
    koef, meta = da.ielasit_koeficientus()
    if koef is None:
        print("Nav koeficientu – prognožu arhīvs netiek papildināts.")
        return 0
    tagad = pd.Timestamp.now(tz="UTC")
    koef["sakums_utc"] = pd.to_datetime(koef["sakums_utc"], utc=True)
    koef = koef[koef["sakums_utc"] > tagad]
    if koef.empty:
        print("Nav nesāktu spēļu ar koeficientiem.")
        return 0
    raw_db, _ = da.ielasit_db()
    raw_t = da.ielasit_speles()
    vg_d = [x for x in (da.ielasit_db_tabulu("vartsargi"), da.ielasit_tabulu("vartsargi")) if x is not None and not x.empty]
    vg = pd.concat(vg_d, ignore_index=True) if vg_d else None
    p, _ = modelis.ielasit_parametrus()
    metieni, xmod = None, None
    if modelis.vajag_metienus(p):
        import xg as xgm
        m_d = [x for x in (da.ielasit_db_tabulu("metieni"), da.ielasit_tabulu("metieni")) if x is not None and not x.empty]
        metieni = pd.concat(m_d, ignore_index=True) if m_d else None
        xmod = xgm.ielasit_modeli()
    raw_all = pd.concat([x for x in (raw_db, raw_t) if x is not None and not x.empty], ignore_index=True)
    sez = int(raw_t["sezona"].max()) if raw_t is not None and not raw_t.empty else int(raw_all["sezona"].max())
    sodiena = tagad.tz_convert(da.LV_TZ).tz_localize(None).normalize()
    g, mod, vr, vu, p = modelis.sagatavot(raw_all, vg, metieni, p, sodiena, sez, xmod)
    svs = da.ielasit_sakuma_vartsargus()
    kal = da.ielasit_kalendaru()
    kal["sakums_utc"] = pd.to_datetime(kal["sakuma_laiks_utc"], utc=True)
    pazimes = atputas_pazimes(g, kal, tagad)
    ielade = (meta or {}).get("ielade") or tagad.strftime("%Y-%m-%dT%H:%M:%SZ")
    rindas = []
    for gid, x in koef.groupby("game_id"):
        home, away = x["majas"].iloc[0], x["viesi"].iloc[0]
        f = pazimes.loc[int(gid)] if int(gid) in pazimes.index else None
        fk = {k: int(f[k]) for k in ("b2b_h", "b2b_a", "cels_h", "cels_a")} if f is not None else {}
        po = int(f["po"]) if f is not None else 0
        vs_h = modelis.ticamie_vartsargi(vr, home, fk.get("b2b_h", 0), vu) if vr is not None else []
        vs_a = modelis.ticamie_vartsargi(vr, away, fk.get("b2b_a", 0), vu) if vr is not None else []
        sak = x["sakums_utc"].iloc[0]
        vs_h, st_h = modelis.apstiprinatie_vartsargi(vs_h, vr, home, *da.sakuma_vartsargs(svs, home, away, home, sak), vu)
        vs_a, st_a = modelis.apstiprinatie_vartsargi(vs_a, vr, away, *da.sakuma_vartsargs(svs, home, away, away, sak), vu)
        pr = modelis.prognoze(mod, g, home, away, p, po=po, vg_h=modelis.sagaidama_attieciba(vs_h),
                              vg_a=modelis.sagaidama_attieciba(vs_a), **fk)
        tot = x[(x["tirgus"] == "tot") & (x["bukmeikers"] == "pinnacle")]
        lin = float(tot["linija"].mode().iloc[0]) if not tot.empty else np.nan
        over_m = modelis.pilnas_speles_over(pr, lin) if not np.isnan(lin) else None
        rindas.append({
            "game_id": int(gid), "ielade": ielade, "sakums_utc": x["sakums_utc"].iloc[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
            "majas": home, "viesi": away, "lh": round(pr["lh"], 4), "la": round(pr["la"], 4),
            "m_1": round(pr["1x2"]["1"], 5), "m_X": round(pr["1x2"]["X"], 5), "m_2": round(pr["1x2"]["2"], 5),
            "m_ml1": round(pr["ar_ot"]["1"], 5), "m_ml2": round(pr["ar_ot"]["2"], 5),
            "tot_linija": lin, "m_over": round(over_m, 5) if over_m is not None else np.nan,
            **{f"pin_{i}": _koef(x, "pinnacle", "1x2", i) for i in ("1", "X", "2")},
            **{f"lab_{i}": _koef(x, None, "1x2", i) for i in ("1", "X", "2")},
            "pin_over": _koef(x, "pinnacle", "tot", "over", lin) if not np.isnan(lin) else np.nan,
            "pin_under": _koef(x, "pinnacle", "tot", "under", lin) if not np.isnan(lin) else np.nan,
            "lab_over": _koef(x, None, "tot", "over", lin) if not np.isnan(lin) else np.nan,
            "lab_under": _koef(x, None, "tot", "under", lin) if not np.isnan(lin) else np.nan,
            "ticamiba": pr["ticamiba"],
            "vartsargs_h": max(vs_h, key=lambda z: z[2])[1] if vs_h else "", "vartsargs_a": max(vs_a, key=lambda z: z[2])[1] if vs_a else "",
            "vg_h": round(pr["vg_h"], 4), "vg_a": round(pr["vg_a"], 4), "vartsargs_h_statuss": st_h or "", "vartsargs_a_statuss": st_a or "",
        })
    jaunas = pd.DataFrame(rindas)
    if os.path.exists(FAILS):
        vecas = pd.read_csv(FAILS)
        jaunas = pd.concat([vecas, jaunas], ignore_index=True).drop_duplicates(["game_id", "ielade"], keep="first")
    jaunas.sort_values(["sakums_utc", "game_id", "ielade"]).to_csv(FAILS, index=False)
    print(f"Prognožu arhīvs: +{len(rindas)} prognozes (kopā {len(jaunas)} rindas, {jaunas['game_id'].nunique()} spēles).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
