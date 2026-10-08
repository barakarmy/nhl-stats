"""
xg.py – paredzamo vārtu (xG) modelis no metienu datiem (metieni.py).

xG = varbūtība, ka neblokēts metiens kļūs par vārtiem, pēc tā, NO KURIENES un KĀ tas izdarīts:
attālums un leņķis, metiena veids, atlēciens, ātrais uzbrukums, sastāvs (5v5 / vairākums / mazākums).
Metieni tukšos vārtos un metienu sērija netiek iekļauti (tie neko nepasaka par komandu vai vārtsargu stiprumu).

Lokāli (reizi sezonā, pēc metienu vēstures lejupielādes):
    python xg.py --apmacit
→ apmāca uz visām DB sezonām, izņemot pēdējo, pārbauda uz pēdējās (log loss un AUC pret vienkāršu bāzi),
  tad apmāca gala modeli uz visām sezonām → sezonas/vesture/xg_modelis.json

Izmantošana: xg_varbutibas(metieni, modelis) un spelu_xg(metieni) – komandu xG un vārtsargu vārti pret paredzamajiem.
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
MODELA_FAILS = os.path.join(BASE, "sezonas", "vesture", "xg_modelis.json")
VEIDI = ["wrist", "snap", "slap", "backhand", "tip-in", "deflected", "wrap-around", "bat", "poke", "between-legs", "cradle"]
SASTAVI = ["PP", "SH", "EV"]                         # 5v5 = bāze


def _skaitlis(s, d=0.0):
    return pd.to_numeric(s, errors="coerce").fillna(d)


def pazimes(m):
    """Metienu tabula → pazīmju matrica (numpy) un nosaukumi."""
    att = _skaitlis(m["attalums"], 35.0).clip(1, 100).to_numpy()
    len_ = _skaitlis(m["lenkis"], 30.0).clip(0, 90).to_numpy()
    kol = {
        "const": np.ones(len(m)),
        "att": att / 10, "att2": (att / 10) ** 2, "log_att": np.log(att),
        "lenkis": len_ / 10, "lenkis2": (len_ / 10) ** 2, "att_x_lenkis": att / 10 * len_ / 10,
        "atleciens": _skaitlis(m["atleciens"]).to_numpy(), "atrais": _skaitlis(m["atrais"]).to_numpy(),
    }
    kol["atleciens_x_lenkis"] = kol["atleciens"] * len_ / 10
    veids = m["veids"].astype(str).str.lower()
    for v in VEIDI:
        kol[f"veids_{v}"] = (veids == v).astype(float).to_numpy()
    sastavs = m["sastavs"].astype(str)
    for s_ in SASTAVI:
        kol[f"sastavs_{s_}"] = (sastavs == s_).astype(float).to_numpy()
    nos = list(kol)
    return np.column_stack([kol[n] for n in nos]), nos


def derigi(m):
    """Metieni, kas izmantojami xG: bez tukšajiem vārtiem, bez metienu sērijas, ar koordinātām."""
    return m[(_skaitlis(m["tuksi"]) == 0) & (m["period_type"].astype(str) != "SO") & m["attalums"].notna()]


def apmacit(m, l2=1.0):
    """Loģistiskā regresija (L2) → {'nosaukumi': [...], 'koef': [...]}."""
    from scipy.optimize import minimize
    m = derigi(m)
    X, nos = pazimes(m)
    y = _skaitlis(m["varti"]).to_numpy()

    def f(w):
        z = X @ w
        p = 1 / (1 + np.exp(-z))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        ll = -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)) + l2 * np.sum(w[1:] ** 2)
        g = X.T @ (p - y)
        g[1:] += 2 * l2 * w[1:]
        return ll, g
    w0 = np.zeros(X.shape[1])
    w0[0] = math.log(max(1e-3, y.mean()) / (1 - max(1e-3, y.mean())))
    w = minimize(f, w0, jac=True, method="L-BFGS-B", options={"maxiter": 1000}).x
    return {"nosaukumi": nos, "koef": [float(v) for v in w]}


def xg_varbutibas(m, modelis):
    """xG katram metienam (tukšie vārti un metienu sērija → NaN)."""
    out = pd.Series(np.nan, index=m.index)
    d = derigi(m)
    if d.empty or not modelis:
        return out
    X, nos = pazimes(d)
    w = np.array([dict(zip(modelis["nosaukumi"], modelis["koef"])).get(n, 0.0) for n in nos])
    out.loc[d.index] = 1 / (1 + np.exp(-(X @ w)))
    return out


def novertet(m, modelis):
    d = derigi(m)
    p = np.clip(xg_varbutibas(d, modelis).to_numpy(), 1e-9, 1 - 1e-9)
    y = _skaitlis(d["varti"]).to_numpy()
    b = y.mean()
    ll = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    ll_b = float(-np.mean(y * np.log(b) + (1 - y) * np.log(1 - b)))
    # AUC (Manna–Vitnija)
    r = pd.Series(p).rank().to_numpy()
    n1, n0 = y.sum(), len(y) - y.sum()
    auc = float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else float("nan")
    return {"metieni": int(len(y)), "varti": int(y.sum()), "xg_kopa": float(p.sum()), "logloss": ll, "logloss_baze": ll_b, "auc": auc}


def ielasit_modeli(fails=MODELA_FAILS):
    if not os.path.exists(fails):
        return None
    try:
        with open(fails, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def spelu_xg(m, modelis, tikai_pamatlaiks=True):
    """
    Spēļu kopsavilkums no metieniem:
      komandas – game_id, komanda, xgf, xga, gf, ga (bez tukšajiem vārtiem; pēc noklusējuma tikai 1.–3. periods);
      vartsargi – game_id, vartsargs, komanda (kuru aizsargā), xga, ga (tikai metieni pret šo vārtsargu).
    """
    if m is None or m.empty or not modelis:
        return None, None
    m = m.copy()
    if tikai_pamatlaiks:
        m = m[_skaitlis(m["period"]) <= 3]
    m["xg"] = xg_varbutibas(m, modelis)
    m = m[m["xg"].notna()]
    m["varti"] = _skaitlis(m["varti"])
    uzbr = m.groupby(["game_id", "komanda"]).agg(xgf=("xg", "sum"), gf=("varti", "sum")).reset_index()
    aizs = m.groupby(["game_id", "pretinieks"]).agg(xga=("xg", "sum"), ga=("varti", "sum")).reset_index().rename(columns={"pretinieks": "komanda"})
    kom = uzbr.merge(aizs, on=["game_id", "komanda"], how="outer").fillna(0)
    vm = m[m["vartsargs"].astype(str).str.len() > 0]
    vart = vm.groupby(["game_id", "vartsargs", "pretinieks"]).agg(xga=("xg", "sum"), ga=("varti", "sum")).reset_index() \
        .rename(columns={"pretinieks": "komanda"})
    vart["vartsargs"] = pd.to_numeric(vart["vartsargs"], errors="coerce").astype("Int64")
    return kom, vart


def modela_xg(metieni, modelis, speles, prieks_svars=400.0):
    """
    xG dati Puasona modelim (pamatlaiks, 1.–3. periods):
      komandas – game_id, komanda, xg (normalizēts), en (vārti tukšos vārtos);
      vartsargi – game_id, playerId, komanda (kuru aizsargā), xga (normalizēts), ga.
    Normalizācija: xG × (līgas vārti / līgas xG) šajā sezonā LĪDZ ŠAI DIENAI (+ iepriekšējās sezonas attiecība kā sākuma
    pieņēmums ar svaru prieks_svars), lai xG būtu tajā pašā mērogā kā vārti un pārbaudē netiktu izmantota nākotne.
    speles – modeļa spēļu tabula (game_id, datums, sezona).
    """
    if metieni is None or metieni.empty or not modelis or speles is None or speles.empty:
        return None, None
    m = metieni.copy()
    m = m[_skaitlis(m["period"]) <= 3]
    m["game_id"] = pd.to_numeric(m["game_id"], errors="coerce").astype("int64")
    m["varti"] = _skaitlis(m["varti"])
    en = m[_skaitlis(m["tuksi"]) == 1].groupby(["game_id", "komanda"])["varti"].sum().rename("en").reset_index()
    kom, vart = spelu_xg(m, modelis, tikai_pamatlaiks=True)
    if kom is None:
        return None, None
    sp = speles[["game_id", "datums", "sezona"]].drop_duplicates("game_id")
    # līgas attiecība (vārti / xG) pa dienām katrā sezonā – tikai no iepriekšējām dienām
    dien = kom.merge(sp, on="game_id").groupby(["sezona", "datums"]).agg(g=("gf", "sum"), x=("xgf", "sum")).reset_index().sort_values(["sezona", "datums"])
    faktori, iepr_attieciba = {}, 1.0
    for sez, d in dien.groupby("sezona", sort=True):
        cg = cx = 0.0
        for r in d.itertuples(index=False):
            faktori[(sez, r.datums)] = (cg + prieks_svars * iepr_attieciba) / (cx + prieks_svars)
            cg += r.g
            cx += r.x
        iepr_attieciba = cg / cx if cx > 0 else 1.0
    kom = kom.merge(sp, on="game_id")
    kom["f"] = [faktori.get((s_, d_), 1.0) for s_, d_ in zip(kom["sezona"], kom["datums"])]
    kom["xg"] = kom["xgf"] * kom["f"]
    kom = kom.merge(en, on=["game_id", "komanda"], how="left").fillna({"en": 0})
    vart = vart.merge(kom[["game_id", "f"]].drop_duplicates("game_id"), on="game_id", how="left").fillna({"f": 1.0})
    vart["xga"] = vart["xga"] * vart["f"]
    return (kom[["game_id", "komanda", "xg", "en"]],
            vart.rename(columns={"vartsargs": "playerId"})[["game_id", "playerId", "komanda", "xga", "ga"]])


def main():
    if "--apmacit" not in sys.argv:
        print(__doc__)
        return 0
    vest = os.path.join(BASE, "sezonas", "vesture")
    sezonas = sorted(d for d in os.listdir(vest) if d.isdigit() and os.path.exists(os.path.join(vest, d, "metieni.csv")))
    if len(sezonas) < 2:
        print("Vajag metienus vismaz 2 sezonām (python metieni.py 20232024 20242025 20252026).")
        return 1
    dati = {s: pd.read_csv(os.path.join(vest, s, "metieni.csv"), low_memory=False) for s in sezonas}
    for s, d in dati.items():
        print(f"{s}: {len(d)} metieni, {int(_skaitlis(d['varti']).sum())} vārti")
    # godīga pārbaude: apmāca bez pēdējās sezonas, pārbauda uz pēdējās
    treni = pd.concat([dati[s] for s in sezonas[:-1]], ignore_index=True)
    mod_p = apmacit(treni)
    p = novertet(dati[sezonas[-1]], mod_p)
    print(f"\nPārbaude uz {sezonas[-1]} ({p['metieni']} metieni): log loss {p['logloss']:.4f} (bāze {p['logloss_baze']:.4f}), "
          f"AUC {p['auc']:.3f}; xG kopā {p['xg_kopa']:.0f} pret {p['varti']} vārtiem")
    gala = apmacit(pd.concat(dati.values(), ignore_index=True))
    gala.update({"sezonas": sezonas, "parbaude": p, "izveidots": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")})
    with open(MODELA_FAILS, "w", encoding="utf-8") as f:
        json.dump(gala, f, ensure_ascii=False, indent=2)
    print(f"Saglabāts: {MODELA_FAILS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
