"""
onice.py – "on-ice" statistika no NHL maiņu datiem (shift charts): kas notika, kamēr spēlētājs bija laukumā.

Katrai spēlei un katram laukuma spēlētājam (bez vārtsargiem) → sezonas/onice.csv, divas rindas (sit = all / 5v5):
  toi   – laiks laukumā (minūtes; 5v5 = abās komandās 5 laukuma spēlētāji + vārtsargs)
  CF/CA – visi metienu mēģinājumi par / pret (Corsi: pa vārtiem + garām + bloķētie)
  FF/FA – neblokētie mēģinājumi (Fenwick)
  SF/SA – metieni pa vārtiem;  GF/GA – vārti
  xGF/xGA – paredzamie vārti (mūsu xG modelis);  HDCF/HDCA – bīstamie metieni (xG ≥ 0.20)
Metieni tukšos vārtos netiek skaitīti. "5v5" – pēc metiena situācijas NHL datos (sastavs = 5v5).
Spēlētājs ir laukumā metiena brīdī t, ja maiņa sākās PIRMS t un beidzās t vai vēlāk (tikko nomainītais skaitās,
tikko uzbraukušais – nē).

Avoti: https://api.nhle.com/stats/rest/en/shiftcharts (maiņas), sezonas/metieni.csv, sezonas/bloketi.csv,
sezonas/vartsargi.csv (vārtsargu ID), xG modelis (sezonas/vesture/xg_modelis.json).
NHL dažām spēlēm maiņu datus nepublicē (vai publicē ar nokavēšanos) – tās tiek mēģinātas katru dienu,
un pēc 5 dienām atzīmētas kā "bez datiem" (onice_gatavs.txt).

Palaišana:
  python onice.py --aktiva [--max 300]          → sezonas/onice.csv (ikdienas darbplūsmā, pēc bloķētajiem metieniem)
  python onice.py 20232024 20242025 [--max N]   → sezonas/vesture/<sezona>/onice.csv (vajag arī bloketi.csv)
  python onice.py --aktiva --no-jauna           → pārrēķināt visu (piem. pēc xG modeļa pārapmācības)
"""
import csv
import os
import sys
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import xg as xgm  # noqa: E402

URL = "https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={}"
KOL = ["datums", "game_id", "playerId", "team", "sit", "toi", "CF", "CA", "FF", "FA", "SF", "SA", "GF", "GA",
       "xGF", "xGA", "HDCF", "HDCA"]
BISTAMS = 0.20
GAIDIT_DIENAS = 5


def _sek(t):
    try:
        m, s = str(t).split(":")
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return None


def mainas_no_api(dati):
    """shiftcharts JSON → [(playerId, team, sākums_s, beigas_s)] spēles sekundēs (tikai īstas maiņas, typeCode 517)."""
    out = []
    for s in (dati or {}).get("data") or []:
        if s.get("typeCode") not in (None, 517):
            continue
        p, a, b = s.get("period"), _sek(s.get("startTime")), _sek(s.get("endTime"))
        if not p or a is None or b is None or b <= a:
            continue
        off = (int(p) - 1) * 1200
        out.append((int(s["playerId"]), str(s.get("teamAbbrev") or ""), off + a, off + b))
    return out


def speles_onice(gid, datums, mainas, metieni, bloketi, vartsargi_ids):
    """Vienas spēles on-ice rindas. metieni – ar kolonnu xg (NaN tukšajiem vārtiem); bloketi – bloķētie."""
    if not mainas:
        return []
    sp = sorted({(p, t) for p, t, _, _ in mainas if p not in vartsargi_ids})
    if not sp:
        return []
    idx = {p: i for i, (p, _) in enumerate(sp)}
    T = max(b for _, _, _, b in mainas) + 1
    on = np.zeros((len(sp), T + 1), dtype=bool)              # on[i, k]: spēlētājs laukumā sekundē (k-1, k]
    for p, _, a, b in mainas:
        if p in idx:
            on[idx[p], a + 1:b + 1] = True
    komanda = np.array([t for _, t in sp])
    # notikumi: (sekunde, metēja komanda, sit5v5, tips, xg)
    ev = []
    for r in metieni.itertuples(index=False):
        if int(r.tuksi) == 1:
            continue
        ev.append((int(r.sek), r.komanda, r.sastavs == "5v5", r.tips, float(r.xg) if np.isfinite(r.xg) else 0.0))
    for r in bloketi.itertuples(index=False):
        if int(r.tuksi) == 1:
            continue
        ev.append((int(r.sek), r.komanda, r.sastavs == "5v5", "blocked", 0.0))
    # 5v5 laiks: abās komandās tieši 5 laukuma spēlētāji un abi vārtsargi laukumā
    komandas = sorted(set(komanda))
    gk = np.zeros((len(komandas), T + 1), dtype=int)
    for p, t, a, b in mainas:
        if p in vartsargi_ids and t in komandas:
            gk[komandas.index(t), a + 1:b + 1] = 1
    sk = np.vstack([on[komanda == t].sum(axis=0) for t in komandas])
    pieci = np.all(sk == 5, axis=0) & np.all(gk == 1, axis=0) if len(komandas) == 2 else np.zeros(T + 1, dtype=bool)
    rez = {(p, s_): {k: 0.0 for k in KOL[5:]} for p, _ in sp for s_ in ("all", "5v5")}
    for i, (p, _) in enumerate(sp):
        rez[(p, "all")]["toi"] = on[i].sum() / 60
        rez[(p, "5v5")]["toi"] = (on[i] & pieci).sum() / 60
    for k, kom, ir5, tips, x in ev:
        if k <= 0 or k > T:
            continue
        laukuma = np.where(on[:, k])[0]
        for i in laukuma:
            p = sp[i][0]
            par = komanda[i] == kom
            for s_ in (("all", "5v5") if ir5 else ("all",)):
                d = rez[(p, s_)]
                if par:
                    d["CF"] += 1
                    if tips != "blocked":
                        d["FF"] += 1
                        d["xGF"] += x
                        d["HDCF"] += x >= BISTAMS
                    if tips in ("sog", "goal"):
                        d["SF"] += 1
                    d["GF"] += tips == "goal"
                else:
                    d["CA"] += 1
                    if tips != "blocked":
                        d["FA"] += 1
                        d["xGA"] += x
                        d["HDCA"] += x >= BISTAMS
                    if tips in ("sog", "goal"):
                        d["SA"] += 1
                    d["GA"] += tips == "goal"
    out = []
    for (p, s_), d in rez.items():
        if d["toi"] <= 0:
            continue
        row = {"datums": datums, "game_id": gid, "playerId": p, "team": komanda[idx[p]], "sit": s_}
        row.update({k: (round(v, 4) if k in ("toi", "xGF", "xGA") else int(v)) for k, v in d.items()})
        out.append(row)
    return out


def _gatavas(mape):
    g = set()
    f = os.path.join(mape, "onice.csv")
    if os.path.exists(f):
        g |= set(pd.read_csv(f, usecols=["game_id"], encoding="utf-8-sig")["game_id"].astype(str))
    f2 = os.path.join(mape, "onice_gatavs.txt")
    if os.path.exists(f2):
        with open(f2, encoding="utf-8") as fh:
            g |= {x.strip().split(",")[0] for x in fh if x.strip()}
    return g


def apstradat(mape, max_speles=None, no_jauna=False):
    import requests
    sp_f = os.path.join(mape, "speles.csv")
    sg = pd.read_csv(sp_f, encoding="utf-8-sig", low_memory=False)
    sg = sg[sg["home_total"].notna()]
    m = pd.read_csv(os.path.join(mape, "metieni.csv"), encoding="utf-8-sig", low_memory=False)
    bf = os.path.join(mape, "bloketi.csv")
    if not os.path.exists(bf):
        print(f"{os.path.relpath(mape, BASE)}: nav bloketi.csv – vispirms python metieni.py --bloketi ...")
        return 1
    bl = pd.read_csv(bf, encoding="utf-8-sig", low_memory=False)
    vg = pd.read_csv(os.path.join(mape, "vartsargi.csv"), encoding="utf-8-sig", low_memory=False)
    mod = xgm.ielasit_modeli()
    if mod is None:
        print("Nav xG modeļa (sezonas/vesture/xg_modelis.json).")
        return 1
    m["xg"] = xgm.xg_varbutibas(m, mod)
    izv = os.path.join(mape, "onice.csv")
    gat_f = os.path.join(mape, "onice_gatavs.txt")
    if no_jauna:
        for f in (izv, gat_f):
            if os.path.exists(f):
                os.remove(f)
    gatavas = _gatavas(mape)
    darbs = [(str(r.game_id), r.datums) for r in sg.itertuples(index=False) if str(r.game_id) not in gatavas]
    if max_speles:
        darbs = darbs[:max_speles]
    print(f"{os.path.relpath(mape, BASE)}: on-ice – jāapstrādā {len(darbs)} spēles")
    if not darbs:
        return 0
    m["game_id"] = m["game_id"].astype(str)
    bl["game_id"] = bl["game_id"].astype(str)
    vg["game_id"] = vg["game_id"].astype(str)
    mg, bg, vgg = dict(tuple(m.groupby("game_id"))), dict(tuple(bl.groupby("game_id"))), vg.groupby("game_id")["playerId"]
    tuksa_m = m.iloc[0:0]
    tuksa_b = bl.iloc[0:0]
    sesija = requests.Session()
    jauns = not os.path.exists(izv)
    n_ok = n_bez = 0
    robeza = (date.today() - timedelta(days=GAIDIT_DIENAS)).isoformat()
    with open(izv, "a", newline="", encoding="utf-8") as f, open(gat_f, "a", encoding="utf-8") as g:
        w = csv.DictWriter(f, fieldnames=KOL)
        if jauns:
            w.writeheader()
        for n, (gid, datums) in enumerate(darbs, 1):
            dati = None
            for k in range(3):
                try:
                    r = sesija.get(URL.format(gid), timeout=30)
                    if r.status_code == 200:
                        dati = r.json()
                        break
                except Exception:                                   # noqa: BLE001
                    pass
                time.sleep(2 * (k + 1))
            mainas = mainas_no_api(dati)
            if not mainas:
                if dati is not None and datums < robeza:              # NHL datus tā arī nepublicēja
                    g.write(f"{gid},bez_datiem\n")
                    n_bez += 1
                continue
            vids = set(pd.to_numeric(vgg.get_group(gid), errors="coerce").dropna().astype(int)) if gid in vgg.groups else set()
            rindas = speles_onice(int(gid), datums, mainas, mg.get(gid, tuksa_m), bg.get(gid, tuksa_b), vids)
            w.writerows(rindas)
            if not rindas:
                g.write(f"{gid},tukss\n")
            n_ok += 1
            if n % 50 == 0:
                f.flush()
                g.flush()
                print(f"  {n}/{len(darbs)}")
            time.sleep(0.2)
    print(f"  gatavs: {n_ok} spēles apstrādātas, {n_bez} atzīmētas bez NHL maiņu datiem")
    return 0


def main(args):
    if not args or "-h" in args or "--help" in args:
        print(__doc__)
        return 0
    max_speles = None
    if "--max" in args:
        i = args.index("--max")
        max_speles = int(args[i + 1])
        args = args[:i] + args[i + 2:]
    no_jauna = "--no-jauna" in args
    args = [a for a in args if a != "--no-jauna"]
    mapes = [os.path.join(BASE, "sezonas")] if args and args[0] == "--aktiva" else [os.path.join(BASE, "sezonas", "vesture", s) for s in args]
    kl = 0
    for mp in mapes:
        if not os.path.exists(os.path.join(mp, "speles.csv")):
            print(f"Nav {os.path.relpath(mp, BASE)}/speles.csv – izlaists.")
            continue
        kl += apstradat(mp, max_speles, no_jauna)
    return 1 if kl else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
