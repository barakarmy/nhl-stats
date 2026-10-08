"""
vesture.py – iepriekšējo sezonu dati (palaiž lokāli savā datorā, nevis GitHub).

1) Vēstures lejupielāde: tie paši CSV faili kā aktīvajai sezonai, katrai sezonai sava mape:
       python vesture.py 20242025 20252026
   → sezonas/vesture/20242025/speles.csv, speletaji.csv, vartsargi.csv, varti.csv, tiesnesi.csv, sastavi.csv
     sezonas/vesture/20252026/...
   Tiek ņemtas regulārās sezonas un play-off spēles (pirmssezona izlaista). Dati nāk no NHL oficiālās statistikas,
   tieši tāpat kā ikdienas atjauninājumā (nhl_dati.py --vieglais). Viena sezona ir ~1400 spēļu un aizņem ~1–2 h.
   Var pārtraukt (Ctrl+C) un palaist vēlreiz: jau saglabātās spēles tiek izlaistas, lejupielāde turpinās.

2) Sezonas maiņa (reizi gadā, pirms jaunās sezonas): aktīvo sezonu pārvieto uz arhīvu un sāk tukšus failus:
       python vesture.py --arhivet
   → sezonas/*.csv (spēles, spēlētāji, vārtsargi, vārti, tiesneši, sastāvi, metieni, plānotie tiesneši, prognožu un
     koeficientu arhīvi) pārvietoti uz
     sezonas/vesture/<sezona>/ (sezonu nosaka pēc sezonas/speles.csv). Kalendārs paliek. Jaunās sezonas datus
     ikdienas atjauninājums sāks vākt tajos pašos failu nosaukumos mapē sezonas/.

3) Pārbaude (pēc lejupielādes vai jebkurā brīdī):
       python vesture.py --parbaudit
   → katrai sezonai: regulārās sezonas spēļu skaits (jābūt 1312), play-off spēles, spēles bez vārtu datiem vai ar nesakrītošu
     vārtu skaitu, spēles bez tiesnešiem un dublikāti. Ja ir problēmas, palaid lejupielādi vēlreiz – trūkstošās spēles tiks ielādētas.

Pēc tam: augšupielādē jaunās mapes/failus GitHub (piem., ar GitHub Desktop: Commit → Push).
Nepieciešams: Python 3.10+ un  pip install requests tzdata
"""
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
AKTIVA = os.path.join(BASE, "sezonas")
VESTURE = os.path.join(AKTIVA, "vesture")
# aktīvās sezonas faili, kas pieder vienai sezonai (kalendārs paliek aktīvajā mapē)
SEZONAS_FAILI = ("speles.csv", "speletaji.csv", "vartsargi.csv", "varti.csv", "tiesnesi.csv", "sastavi.csv", "metieni.csv",
                 "tiesnesi_planotie.csv", "pedeja_atjaunosana.json", "notikumi.csv", "mainas.csv",
                 "prognozes_arhivs.csv", "koeficienti_arhivs.csv", "vartsargi_sakuma.csv")


def sezonas_datumi(sezona):
    """'20242025' → ('2024-09-01', '2025-07-15'): visa sezona ar play-off (pirmssezonas spēles nhl_dati.py izlaiž)."""
    s = str(sezona)
    if len(s) != 8 or not s.isdigit() or int(s[4:]) != int(s[:4]) + 1:
        raise ValueError(f"Sezona jānorāda kā 20242025 (nevis {sezona!r}).")
    return f"{s[:4]}-09-01", f"{s[4:]}-07-15"


def lejupieladet(sezona):
    no, lidz = sezonas_datumi(sezona)
    mape = os.path.join(VESTURE, str(sezona))
    os.makedirs(mape, exist_ok=True)
    print(f"\n=== Sezona {sezona[:4]}/{sezona[4:]}: {no} – {lidz} → {os.path.relpath(mape, BASE)} ===")
    env = dict(os.environ, NHL_DATU_MAPE=mape)
    r = subprocess.run([sys.executable, os.path.join(BASE, "nhl_dati.py"), "--vieglais", no, lidz], env=env, cwd=BASE)
    # pēdējās atjaunošanas laiks vēsturei nav vajadzīgs (lietotne to rāda tikai aktīvajai sezonai)
    lieks = os.path.join(mape, "pedeja_atjaunosana.json")
    if os.path.exists(lieks):
        os.remove(lieks)
    if r.returncode != 0:
        print(f"Sezona {sezona}: dažas spēles neizdevās. Palaid to pašu komandu vēlreiz – saglabātās spēles tiks izlaistas.")
    return r.returncode


def noteikt_sezonu():
    """Aktīvās sezonas kods no sezonas/speles.csv (lielākā vērtība kolonnā 'sezona')."""
    import csv
    fails = os.path.join(AKTIVA, "speles.csv")
    if not os.path.exists(fails):
        return None
    sezonas = set()
    with open(fails, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get("sezona") or "").strip()
            if v.isdigit():
                sezonas.add(int(v))
    return str(max(sezonas)) if sezonas else None


def arhivet():
    sezona = noteikt_sezonu()
    if not sezona:
        print("Nav atrasts sezonas/speles.csv ar sezonas kolonnu – nav ko arhivēt.")
        return 1
    merkis = os.path.join(VESTURE, sezona)
    if os.path.exists(os.path.join(merkis, "speles.csv")):
        print(f"Arhīvā jau ir {os.path.relpath(merkis, BASE)}/speles.csv – nekas netiek pārrakstīts. Pārbaudi mapes un mēģini vēlreiz.")
        return 1
    faili = [f for f in SEZONAS_FAILI if os.path.exists(os.path.join(AKTIVA, f))]
    print(f"Aktīvā sezona: {sezona[:4]}/{sezona[4:]}. Uz {os.path.relpath(merkis, BASE)}/ tiks pārvietoti: {', '.join(faili)}")
    if input("Turpināt? (j/n): ").strip().lower() not in ("j", "jā", "ja", "y", "yes"):
        print("Atcelts.")
        return 1
    os.makedirs(merkis, exist_ok=True)
    for f in faili:
        shutil.move(os.path.join(AKTIVA, f), os.path.join(merkis, f))
    print(f"Gatavs. Sezona {sezona} ir arhīvā; jaunās sezonas dati tiks vākti mapē sezonas/ ar tiem pašiem failu nosaukumiem.")
    return 0


RS_SPELES = 1312        # 32 komandas × 82 spēles / 2


def _lasit(fails):
    import csv
    if not os.path.exists(fails):
        return None
    with open(fails, encoding="utf-8-sig") as f:          # utf-8-sig: NHL skripts raksta failus ar BOM zīmi
        return list(csv.DictReader(f))


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def parbaudit():
    """Vēstures datu pilnības pārbaude (tikai standarta Python, bez pandas)."""
    if not os.path.isdir(VESTURE):
        print("Mape sezonas/vesture nav atrasta.")
        return 1
    sezonas = sorted(d for d in os.listdir(VESTURE) if d.isdigit() and len(d) == 8 and os.path.isdir(os.path.join(VESTURE, d)))
    if not sezonas:
        print("sezonas/vesture nav nevienas sezonas mapes (piem., 20242025).")
        return 1
    problemas = 0
    for sez in sezonas:
        mape = os.path.join(VESTURE, sez)
        speles = _lasit(os.path.join(mape, "speles.csv"))
        print(f"\n=== {sez[:4]}/{sez[4:]} ===")
        if not speles:
            print("  ✗ nav speles.csv"); problemas += 1
            continue
        ids = [_int(r.get("game_id")) for r in speles]
        dubl = len(ids) - len(set(ids))
        rs = [r for r in speles if _int(r.get("speles_tips")) == 2]
        po = [r for r in speles if _int(r.get("speles_tips")) == 3]
        datumi = sorted(r.get("datums", "") for r in speles if r.get("datums"))
        laiks = f"; {datumi[0]} – {datumi[-1]}" if datumi else ""
        print(f"  Spēles: regulārā sezona {len(rs)} (jābūt {RS_SPELES}), play-off {len(po)}{laiks}")
        if len(rs) != RS_SPELES:
            print(f"  ✗ regulārajā sezonā trūkst {RS_SPELES - len(rs)} spēļu" if len(rs) < RS_SPELES else f"  ✗ par daudz RS spēļu ({len(rs)})")
            problemas += 1
        if dubl:
            print(f"  ✗ dublētas spēles: {dubl}"); problemas += 1
        # vārti: vārtu notikumu skaits = gala rezultāts (bez metienu sērijas uzvaras vārtiem)
        varti = _lasit(os.path.join(mape, "varti.csv")) or []
        pa_spelem = {}
        for v in varti:
            if (v.get("period_type") or "").upper() != "SO":
                g = _int(v.get("game_id")); pa_spelem[g] = pa_spelem.get(g, 0) + 1
        nesakrit = []
        for r in speles:
            h, a = _int(r.get("home_total")) or 0, _int(r.get("away_total")) or 0
            so = 1 if (r.get("spele_beidzas") or "").upper() == "SO" else 0
            if pa_spelem.get(_int(r.get("game_id")), 0) != h + a - so:
                nesakrit.append(_int(r.get("game_id")))
        if nesakrit:
            print(f"  ! vārtu notikumi nesakrīt ar rezultātu {len(nesakrit)} spēlēs (piem., {', '.join(map(str, nesakrit[:5]))})")
        else:
            print("  ✓ vārtu notikumi sakrīt ar rezultātu visās spēlēs")
        # tiesneši
        ties = _lasit(os.path.join(mape, "tiesnesi.csv")) or []
        ar_ties = {_int(t.get("game_id")) for t in ties if (t.get("loma") or "") == "referee"}
        bez = [i for i in ids if i not in ar_ties]
        print(f"  {'✓' if not bez else '!'} tiesneši: {len(ids) - len(bez)} spēlēs" + (f", nav {len(bez)} spēlēs" if bez else ""))
        # pārējās tabulas
        for nos in ("speletaji", "vartsargi", "sastavi"):
            t = _lasit(os.path.join(mape, f"{nos}.csv"))
            if t is None:
                print(f"  {nos}.csv: nav")
            else:
                print(f"  {nos}.csv: {len(t)} rindas, {len({_int(x.get('game_id')) for x in t})} spēles")
    print("\n" + ("Viss kārtībā." if not problemas else f"Atrastas {problemas} problēmas – palaid lejupielādi vēlreiz (trūkstošās spēles tiks ielādētas)."))
    return 1 if problemas else 0


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--arhivet":
        return arhivet()
    if args[0] == "--parbaudit":
        return parbaudit()
    kods = 0
    for s in args:
        try:
            sezonas_datumi(s)
        except ValueError as ex:
            print(ex)
            return 2
    for s in args:
        kods = lejupieladet(s) or kods
    print("\nGatavs. Augšupielādē mapi sezonas/vesture GitHub (GitHub Desktop: Commit → Push).")
    return kods


if __name__ == "__main__":
    sys.exit(main())
