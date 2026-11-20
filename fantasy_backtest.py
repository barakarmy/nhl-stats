"""
fantasy_backtest.py – fantasy pickup / drop loģikas pārbaude uz jau aizvadītām nedēļām: modeļu salīdzinājums.
Modeļi (shorts.py FANTASY_MODELI): vecs (līdz 20.11.2026), sezona (20.11. 1. versija – forma ar sezonu visur),
jauns (pēc 70 nedēļu backtest – forma ar sezonu, pretinieki top/bottom 10, DROP aizsardzība).

Katrai aizvadītai fantasy nedēļai (pirmdiena–svētdiena):
  1) "ieteikums" tieši tā, kā shorts.py to būtu izrēķinājis svētdienas vakarā (dati līdz svētdienai, tā paša koda funkcijas);
  2) ko šie spēlētāji nedēļā patiešām izdarīja (punkti no speletaji.csv).
Rostered %: ESPN vēsture glabājas tikai 15 dienas, tāpēc pagātnei – aizvietotājs pēc sezonas punktiem līdz tam brīdim:
  pickup grupa = ārpus top 150 laukuma spēlētājiem (≈ < 40 % rostered), drop grupa = 61.–150. vieta (≈ 50–90 % rostered).
  Abiem modeļiem grupas ir vienādas, tāpēc salīdzinājums ir godīgs (lai gan ne 1:1 ar ESPN).

Rādītāji katram modelim:
  ADD top 3   – vidējie punkti nedēļā; HIT % (punkti virs grupas mediānas – tāpat kā atskata video); TOP25 % (grupas top 25 %)
  ADD top 10  – tas pats 10 izvēlēm (mazāk nejaušības nekā 3 izvēlēm)
  ρ           – rangu korelācija starp pickup score un nedēļas punktiem VISAI pickup grupai (augstāka = labāk sakārto)
  pret vecs   – cik nedēļās ADD10 / ρ bija labāks : sliktāks nekā vecajam modelim (stabilitāte – ne tikai vidējais)
  DROP        – cik ieteikts, vidējie punkti (mazāk = labāk), GOOD CALL % (zem drop grupas mediānas), KĻŪDA % (drop grupas top 25 %)

Palaišana:
  python fantasy_backtest.py                        šī sezona, visas aizvadītās nedēļas
  python fantasy_backtest.py --visas                šī sezona + vēstures sezonas (sezonas/vesture/<sezona>/, ja tur ir faili)
  python fantasy_backtest.py --sezona 20252026      tikai viena vēstures sezona
  python fantasy_backtest.py --streameri            streameri: trešdiena–svētdiena (dati līdz otrdienai), bez drop
  python fantasy_backtest.py --ablacija             + "jauns" ar vienu izmaiņu katrā variantā (logs80, logs40, P30, -veiksme,
                                                    -toi, +pret, +b2b, +viegl, +visi3) – vai kāda vēl uzlabo pašu augšu (ADD10)
Rezultāts: konsolē + video/fantasy_backtest.csv (katra izvēle ar punktiem un verdiktu; mape video – .gitignore, netiek augšupielādēta).
"""
import argparse
import os
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import shorts as S  # noqa: E402

POOL_BRIVI = 150            # ārpus top 150 pēc sezonas punktiem ≈ < 40 % rostered
POOL_DROP = (60, 150)       # 61.–150. vieta ≈ 50–90 % rostered


def ablacijas():
    """"jauns" + viena izmaiņa katrā variantā: vai kāda vēl uzlabo pašu augšu (ADD10). Tie paši svari ir arī DROP
    vērtējumā, tāpēc katra izmaiņa var mainīt arī DROP kolonnas."""
    j = S.FANTASY_MODELI["jauns"]

    def v(**kw):
        return dict(j, **kw)
    return {
        "logs80": v(logs=0.80),                       # 80 % 14 dienas + 20 % sezona
        "logs40": v(logs=0.40),                       # 40 % + 60 % (vairāk sezonas)
        "P30": v(P=0.30),                             # punktiem kā agrāk
        "-veiksme": v(veiksme=0.0),                   # bez soda par vārtiem virs ixG
        "-toi": v(TOI=0.0),                           # bez laika uz ledus līmeņa
        "+pret": v(pret=0.15),                        # pretinieki nepārtraukti (xGA + ielaistie)
        "+b2b": v(b2b=0.10),                          # pretinieks 2. vakaru pēc kārtas
        "+viegl": v(viegl=0.05),                      # vieglās dienas arī nedēļai
        "+visi3": v(pret=0.15, b2b=0.10, viegl=0.05),  # = "sezona" pickups
    }


def metieni(cels):
    """Kā shorts.ielasit(), bet no norādīta faila (vēstures sezonām)."""
    m = pd.read_csv(cels, low_memory=False)
    mod = S.xgm.ielasit_modeli()
    if mod is None:
        raise SystemExit("Nav xG modeļa (sezonas/vesture/xg_modelis.json).")
    m["xg"] = S.xgm.xg_varbutibas(m, mod)
    m = m[m["xg"].notna()].copy()
    m["varti"] = pd.to_numeric(m["varti"], errors="coerce").fillna(0)
    m["metejs"] = pd.to_numeric(m["metejs"], errors="coerce")
    m["vartsargs"] = pd.to_numeric(m["vartsargs"], errors="coerce")
    m["uz_v"] = m["tips"].astype(str).isin(["sog", "goal"]).astype(int)
    return m


def sezonas_dati(mape, pasreizeja):
    """→ (sp, m, v_pp, sg) vai None, ja trūkst failu."""
    vaj = ["speletaji.csv", "metieni.csv", "speles.csv", "varti.csv"]
    trukst = [f for f in vaj if not os.path.exists(os.path.join(mape, f))]
    if trukst:
        print(f"  {mape}: trūkst {', '.join(trukst)} – izlaižu")
        return None
    sp = pd.read_csv(os.path.join(mape, "speletaji.csv"), encoding="utf-8-sig", low_memory=False)
    sp["playerId"] = pd.to_numeric(sp["playerId"], errors="coerce")
    sp = sp[sp["playerId"].notna()]
    for k, nokl in (("hits", 0), ("blockedShots", 0), ("numurs", ""), ("sog", 0)):
        if k not in sp:
            sp[k] = nokl
    sp["toi_m"] = sp["toi"].map(S._toi_min)
    m = S.ielasit() if pasreizeja else metieni(os.path.join(mape, "metieni.csv"))
    v = pd.read_csv(os.path.join(mape, "varti.csv"), encoding="utf-8-sig", low_memory=False)
    v_pp = v[v["strength"].astype(str).str.lower() == "pp"]
    sg = pd.read_csv(os.path.join(mape, "speles.csv"), encoding="utf-8-sig", low_memory=False)
    if "speles_tips" in sg:
        sg = sg[sg["speles_tips"].astype(str).isin(["2", "2.0"])]   # tikai regulārā sezona (fantasy)
    sp = sp[sp["game_id"].isin(sg["game_id"])] if "game_id" in sp and "game_id" in sg else sp
    return sp, m, v_pp, sg


def verdikts(P, GP, med, labi_ja_virs):
    if GP > 0 and P == med:
        return None
    return bool(P > med) if labi_ja_virs else bool(P < med)


def nedela(a, dati, start, modeli, stream):
    sp, m, v_pp, sg = dati
    beigas = start + timedelta(days=6)
    if stream:
        start = start + timedelta(days=2)                             # trešdiena
    lidz = (start - timedelta(days=1)).strftime("%Y-%m-%d")
    s_, b_ = start.strftime("%Y-%m-%d"), beigas.strftime("%Y-%m-%d")
    g, _, _, _ = S.fantasy_pazimes(sp, m, lidz, a.dienas, v_pp)
    if g.empty:
        return None
    g["rostered"], g["delta7"], g["trauma"] = np.nan, np.nan, ""
    kal = sg[(sg["datums"] >= s_) & (sg["datums"] <= b_)].rename(columns={"home_team": "majas_komanda", "away_team": "viesu_komanda"})
    if len(kal) < 10:                                                 # pārtraukums (4 Nations, olimpiskās spēles u.c.)
        print(f"   {s_}: nedēļā tikai {len(kal)} spēles (pārtraukums) – izlaižu")
        return None
    grafiks = S.fantasy_grafiks(kal)
    spelu_dienas = {(k_, d_) for d_, h_, v_ in zip(sg["datums"], sg["home_team"], sg["away_team"]) for k_ in (h_, v_)}
    # patiesība: nedēļas punkti; grupas pēc sezonas punktu vietas līdz lidz
    w = sp[(sp["datums"] >= s_) & (sp["datums"] <= b_)].groupby("playerId").agg(P=("points", "sum"), GP=("game_id", "nunique"))
    lauk = sp[(sp["datums"] <= lidz) & (sp["pozicija"] != "G")]
    vieta = lauk.groupby("playerId")["points"].sum().rank(ascending=False, method="first")
    vis = pd.DataFrame({"vieta": vieta}).join(w).fillna({"P": 0, "GP": 0})
    pa = vis[(vis["vieta"] > POOL_BRIVI) & (vis["GP"] >= 2)]["P"]
    pd_ = vis[(vis["vieta"] > POOL_DROP[0]) & (vis["vieta"] <= POOL_DROP[1]) & (vis["GP"] >= 2)]["P"]
    med_a, q75_a = pa.median(), pa.quantile(0.75)
    med_d, q75_d = pd_.median(), pd_.quantile(0.75)
    out, rindas = {}, []
    for mod in modeli:
        cfg = S.FANTASY_MODELI[mod]
        ind, vajas, stipras = S.fantasy_pretinieki(m, lidz, cfg)
        gg, _ = S.fantasy_grafika_pazimes(g, grafiks, kal, ind, vajas, stipras, spelu_dienas)
        gg = gg[gg["sp_nak"] >= 1].copy()
        if gg.empty:
            continue
        gg["forma"] = S.fantasy_forma(gg, cfg)
        vv = gg.index.map(vieta)
        brivi = gg[vv > POOL_BRIVI].copy()
        nom = gg[(vv > POOL_DROP[0]) & (vv <= POOL_DROP[1])].copy()
        if len(brivi) < 10:
            continue
        brivi["score"] = S.fantasy_score(brivi, cfg, stream)
        if stream and cfg.get("stream_min_sp"):                       # izslēgtie – grupas apakšā (ρ – tā pati grupa visiem)
            min_sp = max(2, max((len(x) for x in grafiks.values()), default=0) - 1)
            if (brivi["sp_nak"] >= min_sp).sum() >= a.top:
                brivi.loc[brivi["sp_nak"] < min_sp, "score"] = brivi["score"].min() - 1.0
        cfg_d = S.fantasy_drop_cfg(cfg)                               # "jauns": DROP – forma ar sezonu
        if cfg_d is not cfg:
            nom["forma"] = S.fantasy_forma(gg, cfg_d).reindex(nom.index)
        nom["dscore"] = S.fantasy_dscore(nom, cfg_d)
        aizs = S.fantasy_drop_aizsardziba(nom, cfg_d)
        add10 = S.fantasy_ar_limitu(brivi, "score", 10)
        add3 = add10.head(a.top)
        drop = nom.iloc[0:0] if stream else S.fantasy_ar_limitu(S.fantasy_drop_kandidati(nom, cfg_d, aizs), "dscore", a.drop)
        fakt = brivi[["score"]].join(w).fillna({"P": 0, "GP": 0})
        rho = fakt["score"].rank().corr(fakt["P"].rank())
        r = {"modelis": mod, "rho": rho}
        for nos, izv in (("a3", add3), ("a10", add10)):
            x = izv[[]].join(w).fillna({"P": 0, "GP": 0})
            ver = [verdikts(p, gp_, med_a, True) for p, gp_ in zip(x["P"], x["GP"])]
            r[nos + "_P"], r[nos + "_n"] = float(x["P"].sum()), len(x)
            r[nos + "_hit"], r[nos + "_vert"] = sum(v_ is True for v_ in ver), sum(v_ is not None for v_ in ver)
            r[nos + "_top"] = int((x["P"] >= q75_a).sum())
            if nos == "a3":
                for i_, (pid, xr) in enumerate(x.iterrows(), 1):
                    rindas.append({"nedela": s_, "modelis": mod, "veids": "ADD", "nr": i_, "vards": izv.loc[pid, "vards"],
                                   "team": izv.loc[pid, "team"], "score": round(float(izv.loc[pid, "score"]), 3),
                                   "P": int(xr["P"]), "GP": int(xr["GP"]), "mediana": med_a,
                                   "verdikts": {True: "HIT", False: "MISS", None: "EVEN"}[ver[i_ - 1]]})
        x = drop[[]].join(w).fillna({"P": 0, "GP": 0})
        ver = [verdikts(p, gp_, med_d, False) for p, gp_ in zip(x["P"], x["GP"])]
        r.update({"d_n": len(x), "d_P": float(x["P"].sum()), "d_good": sum(v_ is True for v_ in ver),
                  "d_vert": sum(v_ is not None for v_ in ver), "d_kluda": int((x["P"] >= q75_d).sum()), "d_aizs": len(aizs)})
        for i_, (pid, xr) in enumerate(x.iterrows(), 1):
            rindas.append({"nedela": s_, "modelis": mod, "veids": "DROP", "nr": i_, "vards": drop.loc[pid, "vards"],
                           "team": drop.loc[pid, "team"], "score": round(float(drop.loc[pid, "dscore"]), 3),
                           "P": int(xr["P"]), "GP": int(xr["GP"]), "mediana": med_d,
                           "verdikts": {True: "GOOD CALL", False: "BAD CALL", None: "EVEN"}[ver[i_ - 1]]})
        out[mod] = r
    return out, rindas


def pct(a_, b_):
    return f"{a_ / b_ * 100:5.0f}%" if b_ else "    –"


def main():
    ap = argparse.ArgumentParser(description="Fantasy pickup / drop backtest: vecais vs jaunais modelis")
    ap.add_argument("--sezona", default=None, help="vēstures sezona (mape sezonas/vesture/<sezona>/), piem. 20252026")
    ap.add_argument("--visas", action="store_true", help="šī sezona + visas vēstures sezonas ar vajadzīgajiem failiem")
    ap.add_argument("--streameri", action="store_true", help="streameri: trešdiena–svētdiena, dati līdz otrdienai, bez drop")
    ap.add_argument("--ablacija", action="store_true", help='arī "jauns" ar vienu pickup izmaiņu katrā variantā')
    ap.add_argument("--no", default=None, help="tikai nedēļas no šī datuma (YYYY-MM-DD)")
    ap.add_argument("--dienas", type=int, default=14)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--drop", type=int, default=2)
    ap.add_argument("--bez-nedelam", action="store_true", help="nerādīt katru nedēļu – tikai kopsavilkumu")
    ap.add_argument("--base", default=BASE, help="projekta mape (kurā ir sezonas\\); noklusējums – skripta mape")
    a = ap.parse_args()
    S.BASE = a.base

    modeli = [m_ for m_ in ("vecs", "sezona", "jauns") if m_ in S.FANTASY_MODELI]
    if a.ablacija:
        for k, v in ablacijas().items():
            S.FANTASY_MODELI[k] = v
            modeli.append(k)
    sez = os.path.join(a.base, "sezonas")
    vd = os.path.join(sez, "vesture")
    avoti = []
    if a.sezona:
        avoti = [(a.sezona, os.path.join(vd, a.sezona), False)]
    else:
        avoti = [("šī sezona", sez, True)]
        if a.visas and os.path.isdir(vd):
            avoti += [(s_, os.path.join(vd, s_), False) for s_ in sorted(os.listdir(vd)) if s_.isdigit()]
    kop = {mod: {} for mod in modeli}
    pa_nedelam = []                                                   # [{modelis: (ADD10 vid., ρ)}] – stabilitātei pret "vecs"
    visas_rindas = []
    print(f"FANTASY BACKTEST – {'streameri (trešd.–svētd.)' if a.streameri else 'nedēļas pickups (pirmd.–svētd.)'}; "
          f"pickup grupa: ārpus top {POOL_BRIVI}, drop grupa: {POOL_DROP[0] + 1}.–{POOL_DROP[1]}. vieta pēc sezonas punktiem\n")
    for nos, mape, pas in avoti:
        dati = sezonas_dati(mape, pas)
        if dati is None:
            continue
        sp = dati[0]
        d0, d1 = pd.Timestamp(sp["datums"].min()), pd.Timestamp(sp["datums"].max())
        pirmd = d0 + timedelta(days=a.dienas)
        pirmd += timedelta(days=(7 - pirmd.weekday()) % 7)
        nedelas = []
        while pirmd + timedelta(days=6) <= d1:
            if not a.no or pirmd >= pd.Timestamp(a.no):
                nedelas.append(pirmd)
            pirmd += timedelta(days=7)
        print(f"== {nos}: {len(nedelas)} aizvadītas nedēļas ({d0:%Y-%m-%d} – {d1:%Y-%m-%d})")
        if not a.bez_nedelam:
            print(f"   {'NEDĒĻA':<11} {'MODELIS':<9} {'ADD3 P':>6} {'HIT':>5} {'ADD10 P̄':>8} {'HIT%':>6} {'TOP25%':>7} {'ρ':>6}"
                  f"   {'DROP n':>6} {'P̄':>5} {'GOOD':>5}")
        for pm in nedelas:
            r = nedela(a, dati, pm, modeli, a.streameri)
            if not r:
                continue
            out, rindas = r
            for x in rindas:
                x["sezona"] = nos
            visas_rindas += rindas
            pa_nedelam.append({mod: (x["a10_P"] / max(1, x["a10_n"]), x["rho"]) for mod, x in out.items()})
            for mod, x in out.items():
                k = kop[mod]
                for kk, vv in x.items():
                    if kk != "modelis":
                        k[kk] = k.get(kk, 0) + (0 if (isinstance(vv, float) and not np.isfinite(vv)) else vv)
                k["ned"] = k.get("ned", 0) + 1
                if not a.bez_nedelam:
                    print(f"   {pm:%Y-%m-%d}  {mod:<9} {x['a3_P']:>6.0f} {x['a3_hit']:>2}/{x['a3_vert']:<2} "
                          f"{x['a10_P'] / max(1, x['a10_n']):>8.2f} {pct(x['a10_hit'], x['a10_vert']):>6} {pct(x['a10_top'], x['a10_n']):>7} "
                          f"{x['rho']:>6.3f}   {x['d_n']:>6} "
                          + (f"{x['d_P'] / x['d_n']:>5.2f} {x['d_good']:>2}/{x['d_vert']:<2}" if x["d_n"] else f"{'–':>5} {'–':>5}"))
        print()
    if not any(k.get("ned") for k in kop.values()):
        print("Nav nevienas pilnas nedēļas ar pietiekamiem datiem (vajag ≥ 14 dienas pirms nedēļas un visu nedēļu pēc).")
        return 1
    print("=" * 96)
    print(f"KOPĀ   {'MODELIS':<9} {'NED':>4} {'ADD3 P̄':>7} {'HIT%':>6} {'TOP25%':>7} {'ADD10 P̄':>8} {'HIT%':>6} {'TOP25%':>7} {'ρ vid.':>7}"
          f"   {'DROP':>5} {'P̄':>5} {'GOOD%':>6} {'KĻŪDA%':>7}   {'pret vecs: ADD10':>16} {'ρ':>7}")

    def pret_veco(mod):
        if mod == "vecs":
            return f"{'':>16} {'':>7}"
        def zime(x_, y_):
            return int(np.sign(round(float(x_) - float(y_), 6)))     # 1 labāk, −1 sliktāk, 0 vienādi
        a_ = [zime(x[mod][0], x["vecs"][0]) for x in pa_nedelam if mod in x and "vecs" in x]
        r_ = [zime(x[mod][1], x["vecs"][1]) for x in pa_nedelam if mod in x and "vecs" in x
              and np.isfinite(x[mod][1]) and np.isfinite(x["vecs"][1])]
        return f"{f'{a_.count(1)}:{a_.count(-1)}':>16} {f'{r_.count(1)}:{r_.count(-1)}':>7}"
    for mod in modeli:
        k = kop[mod]
        if not k.get("ned"):
            continue
        print(f"       {mod:<9} {k['ned']:>4} {k['a3_P'] / max(1, k['a3_n']):>7.2f} {pct(k['a3_hit'], k['a3_vert']):>6} "
              f"{pct(k['a3_top'], k['a3_n']):>7} {k['a10_P'] / max(1, k['a10_n']):>8.2f} {pct(k['a10_hit'], k['a10_vert']):>6} "
              f"{pct(k['a10_top'], k['a10_n']):>7} {k['rho'] / k['ned']:>7.3f}   {k['d_n']:>5} "
              + (f"{k['d_P'] / k['d_n']:>5.2f}" if k["d_n"] else f"{'–':>5}") + f" {pct(k['d_good'], k['d_vert']):>6} {pct(k['d_kluda'], k['d_n']):>7}"
              + f"   {pret_veco(mod)}")
    print("\nKā lasīt: ADD P̄ un HIT/TOP25 – augstāk = labāk; ρ – cik labi score sakārto VISU pickup grupu (augstāk = labāk);"
          "\n           DROP P̄ un KĻŪDA% – zemāk = labāk (KĻŪDA = ieteicām mest ārā, bet viņš nedēļā bija grupas top 25 %)."
          "\n           Ar 3 izvēlēm nedēļā nejaušība ir liela – skaties ADD10 un ρ, un uz vairākām nedēļām."
          "\n           pret vecs 12:5 = 12 nedēļās labāk, 5 sliktāk (pārējās vienādi) – jo vairāk nedēļu, jo ticamāk.")
    if visas_rindas:
        p = os.path.join(a.base, "video", "fantasy_backtest.csv")
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            pd.DataFrame(visas_rindas).to_csv(p, index=False, encoding="utf-8-sig")
            print(f"\nKatra izvēle: {p}")
        except OSError as ex:
            print(f"\n(nevarēju saglabāt {p}: {ex})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
