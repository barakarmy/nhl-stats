"""
shorts.py – vertikāls YouTube Shorts video (1080×1920, MP4) no lietotnes datiem: "xG LUCK REPORT".

Saturs: 3 spēlētāji, kuri gūst vārtus krietni VAIRĀK nekā paredz xG ("lucky – expect cooldown"),
un 3, kuri gūst krietni MAZĀK ("unlucky – due for goals"). Dati: sezonas/metieni.csv + xG modelis (xg.py),
vārdi no sezonas/speletaji.csv. Tukšo vārtu metieni un metienu sērija netiek skaitīti.

Palaišana (repozitorija mapē):
    pip install pandas numpy pillow            (+ ffmpeg sistēmā: https://ffmpeg.org, Windows: winget install ffmpeg)
    pip install edge-tts                       (neobligāti: angļu AI balss; bez tā video būs bez skaņas)
    python shorts.py                           → video/xg_luck_<datums>.mp4 + video/xg_luck_<datums>.txt
    python shorts.py --dienas 14               → tikai pēdējās 14 dienas (citādi visa sezona)
    python shorts.py --top 3 --min-metieni 15 --balss en-US-AndrewNeural --kanals @tavskanals
    python shorts.py --bez-balss               → bez skaņas pat ja edge-tts ir uzinstalēts

.txt failā: virsraksts, apraksts ar tēmturiem un runas teksts (ja balsi gribi ierunāt pats vai pievienot CapCut).
"""
import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import xg as xgm  # noqa: E402

W, H, FPS = 1080, 1920, 30
BG_TOP, BG_BOT = (10, 15, 28), (22, 32, 58)
BALTS, PELEKS, TUMSS = (245, 247, 250), (148, 163, 184), (30, 41, 59)
ZALS, SARKANS, ZILS, DZELTENS = (34, 197, 94), (239, 68, 68), (56, 189, 248), (250, 204, 21)

KOMANDU_KRASAS = {
    "ANA": (252, 76, 2), "BOS": (252, 181, 20), "BUF": (0, 48, 135), "CGY": (200, 16, 46), "CAR": (206, 17, 38),
    "CHI": (207, 10, 44), "COL": (111, 38, 61), "CBJ": (0, 38, 84), "DAL": (0, 104, 71), "DET": (206, 17, 38),
    "EDM": (252, 76, 0), "FLA": (200, 16, 46), "LAK": (162, 170, 173), "MIN": (21, 71, 52), "MTL": (175, 30, 45),
    "NSH": (255, 184, 28), "NJD": (206, 17, 38), "NYI": (0, 83, 155), "NYR": (0, 56, 168), "OTT": (218, 26, 50),
    "PHI": (247, 73, 2), "PIT": (252, 181, 20), "SJS": (0, 109, 117), "SEA": (153, 217, 217), "STL": (0, 47, 135),
    "TBL": (0, 40, 104), "TOR": (0, 32, 91), "UTA": (113, 175, 229), "VAN": (0, 32, 91), "VGK": (185, 151, 91),
    "WSH": (200, 16, 46), "WPG": (4, 30, 66),
}

FONTU_MAPES = ["/usr/share/fonts/opentype/inter", "C:/Windows/Fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental",
               "/usr/share/fonts/truetype/dejavu"]
FONTI = {"black": ["Inter-Black.otf", "ariblk.ttf", "Arial Black.ttf", "DejaVuSans-Bold.ttf"],
         "bold": ["Inter-ExtraBold.otf", "Inter-Bold.otf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
         "semi": ["Inter-SemiBold.otf", "seguisb.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"],
         "reg": ["Inter-Medium.otf", "Inter-Regular.otf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]}
_fcache = {}


def fonts(veids, izm):
    k = (veids, izm)
    if k not in _fcache:
        for nos in FONTI[veids]:
            for mape in FONTU_MAPES:
                p = os.path.join(mape, nos)
                if os.path.exists(p):
                    _fcache[k] = ImageFont.truetype(p, izm)
                    break
            if k in _fcache:
                break
        else:
            _fcache[k] = ImageFont.load_default(izm)
    return _fcache[k]


# ---------------------------------------------------------------- dati

def dati(dienas=None, min_metieni=15, top=3):
    m = pd.read_csv(os.path.join(BASE, "sezonas", "metieni.csv"), low_memory=False)
    mod = xgm.ielasit_modeli()
    if mod is None:
        raise SystemExit("Nav xG modeļa (sezonas/vesture/xg_modelis.json).")
    if dienas:
        no = (pd.Timestamp(m["datums"].max()) - timedelta(days=dienas - 1)).strftime("%Y-%m-%d")
        m = m[m["datums"] >= no]
    m = m.copy()
    m["xg"] = xgm.xg_varbutibas(m, mod)
    m = m[m["xg"].notna()]                                          # bez tukšajiem vārtiem un metienu sērijas
    m["varti"] = pd.to_numeric(m["varti"], errors="coerce").fillna(0)
    m["metejs"] = pd.to_numeric(m["metejs"], errors="coerce")
    m["uz_v"] = m["tips"].astype(str).isin(["sog", "goal"]).astype(int)
    g = m.groupby("metejs").agg(G=("varti", "sum"), xG=("xg", "sum"), met=("xg", "size"), sog=("uz_v", "sum"),
                                sp=("game_id", "nunique")).reset_index()
    g = g[g["met"] >= min_metieni]
    g["d"] = g["G"] - g["xG"]
    sp = pd.read_csv(os.path.join(BASE, "sezonas", "speletaji.csv"), encoding="utf-8-sig", low_memory=False)
    sp = sp.sort_values("datums").drop_duplicates("playerId", keep="last")
    sp["playerId"] = pd.to_numeric(sp["playerId"], errors="coerce")
    g = g.merge(sp[["playerId", "vards", "team", "pozicija", "numurs"]], left_on="metejs", right_on="playerId", how="left")
    g = g[g["vards"].notna()]
    laimigie = g.sort_values(["d", "G"], ascending=[False, False]).head(top)
    nelaimigie = g[g["xG"] >= 1.5].sort_values(["d", "xG"], ascending=[True, False]).head(top)
    periods = (m["datums"].min(), m["datums"].max())
    return laimigie, nelaimigie, periods, len(m)


# ---------------------------------------------------------------- zīmēšana

def ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def fons():
    a = np.linspace(0, 1, H)[:, None, None]
    img = (np.array(BG_TOP) * (1 - a) + np.array(BG_BOT) * a).repeat(W, axis=1).astype(np.uint8)
    im = Image.fromarray(img, "RGB")
    d = ImageDraw.Draw(im, "RGBA")
    # ledus laukuma līnijas (vāji)
    d.line([(0, 1250), (W, 1250)], fill=(220, 38, 38, 40), width=6)
    d.ellipse([W / 2 - 330, 1250 - 330, W / 2 + 330, 1250 + 330], outline=(56, 189, 248, 28), width=6)
    for y in (420, 1700):
        d.line([(0, y), (W, y)], fill=(56, 189, 248, 30), width=8)
    return im


def teksts_c(d, y, txt, f, krasa=BALTS, x=None):
    b = d.textbbox((0, 0), txt, font=f)
    w = b[2] - b[0]
    d.text(((W - w) / 2 if x is None else x, y), txt, font=f, fill=krasa)
    return b[3] - b[1]


def ietilpinat(d, txt, veids, izm, max_w):
    while izm > 30:
        f = fonts(veids, izm)
        b = d.textbbox((0, 0), txt, font=f)
        if b[2] - b[0] <= max_w:
            return f
        izm -= 4
    return fonts(veids, izm)


def pill(d, x, y, txt, f, bg, fg=BALTS, pad=(26, 12), center=False):
    b = d.textbbox((0, 0), txt, font=f)
    w, h = b[2] - b[0] + 2 * pad[0], b[3] - b[1] + 2 * pad[1]
    if center:
        x = (W - w) / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2, fill=bg)
    d.text((x + pad[0] - b[0], y + pad[1] - b[1]), txt, font=f, fill=fg)
    return w, h


def slide(t, ilgums, t_in=0.28, t_out=0.22):
    """Pārbīde (x nobīde) un necaurspīdīgums ainas sākumā/beigās."""
    if t < t_in:
        k = ease(t / t_in)
        return (1 - k) * 140, k
    if t > ilgums - t_out:
        k = ease((t - (ilgums - t_out)) / t_out)
        return -k * 140, 1 - k
    return 0, 1


def aina_intro(t, ilg, info):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = ease(t / 0.5)
    pill(d, 0, 300, "NHL  ·  xG LUCK REPORT", fonts("semi", 40), (56, 189, 248, 255), (8, 15, 30), center=True)
    y = 470
    for i, (rinda, kr) in enumerate([("WHO'S", BALTS), ("RUNNING", BALTS), ("ON LUCK?", DZELTENS)]):
        kk = ease((t - 0.12 * i) / 0.45)
        f = fonts("black", 150)
        b = d.textbbox((0, 0), rinda, font=f)
        d.text(((W - (b[2] - b[0])) / 2 + (1 - kk) * 200, y), rinda, font=f, fill=kr + (int(255 * kk),))
        y += 175
    f = fonts("reg", 46)
    for i, r in enumerate(["Goals vs expected goals (xG)", info]):
        teksts_c(d, 1080 + i * 66, r, f, PELEKS + (int(255 * k),))
    # mini legenda
    kk = ease((t - 0.6) / 0.4)
    a = int(255 * kk)
    pill(d, 0, 1300, "LUCKY  →  cooldown", fonts("semi", 40), ZALS + (a,), (8, 15, 30, a), center=True)
    pill(d, 0, 1400, "UNLUCKY  →  due for goals", fonts("semi", 40), SARKANS + (a,), BALTS + (a,), center=True)
    return im


def aina_speletajs(t, ilg, r, nr, lucky):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    akc = ZALS if lucky else SARKANS
    kom = str(r["team"])
    kkr = KOMANDU_KRASAS.get(kom, (100, 116, 139))
    # augšā: kategorija
    pill(d, 0, 250, ("LUCKY  ·  EXPECT A COOLDOWN" if lucky else "UNLUCKY  ·  DUE FOR GOALS"), fonts("semi", 40), akc,
         (8, 15, 30) if lucky else BALTS, center=True)
    # karte
    x0, y0, x1, y1 = 70, 380, W - 70, 1640
    d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=(15, 23, 42, 235), outline=(255, 255, 255, 30), width=3)
    d.rounded_rectangle([x0, y0, x1, y0 + 22], radius=11, fill=kkr)
    # numurs
    d.text((x0 + 50, y0 + 60), f"#{nr}", font=fonts("black", 92), fill=akc)
    pill(d, x1 - 230, y0 + 80, kom, fonts("bold", 48), kkr, BALTS, pad=(34, 14))
    # vārds
    vards = str(r["vards"])
    dalas = vards.split(" ", 1)
    f1 = fonts("semi", 54)
    d.text((x0 + 50, y0 + 210), dalas[0].upper() if len(dalas) > 1 else "", font=f1, fill=PELEKS)
    f2 = ietilpinat(d, (dalas[-1]).upper(), "black", 120, x1 - x0 - 100)
    d.text((x0 + 50, y0 + 275), dalas[-1].upper(), font=f2, fill=BALTS)
    poz = {"C": "Center", "L": "Left wing", "R": "Right wing", "D": "Defense"}.get(str(r["pozicija"]), str(r["pozicija"]))
    num = "" if pd.isna(r["numurs"]) else f"#{int(r['numurs'])}  ·  "
    d.text((x0 + 50, y0 + 425), f"{num}{poz}  ·  {int(r['sp'])} GP", font=fonts("reg", 44), fill=PELEKS)
    # stabiņi
    mx = max(r["G"], r["xG"], 1) * 1.08
    k = ease((t - 0.35) / 0.9)
    yb = y0 + 560
    for i, (nos, v, kr, fmt) in enumerate([("GOALS", r["G"], BALTS, "{:.0f}"), ("EXPECTED (xG)", r["xG"], ZILS, "{:.1f}")]):
        y = yb + i * 190
        d.text((x0 + 50, y), nos, font=fonts("semi", 40), fill=PELEKS)
        bx0, bx1 = x0 + 50, x1 - 50
        d.rounded_rectangle([bx0, y + 62, bx1, y + 142], radius=40, fill=TUMSS)
        w = (bx1 - bx0) * (v / mx) * k
        if w > 80:
            d.rounded_rectangle([bx0, y + 62, bx0 + w, y + 142], radius=40, fill=kr)
        val = fmt.format(v * k) if fmt == "{:.1f}" else str(int(round(v * k)))
        fv = fonts("black", 64)
        b = d.textbbox((0, 0), val, font=fv)
        tx = bx0 + w + 20 if w + (b[2] - b[0]) + 60 < bx1 - bx0 else bx0 + w - (b[2] - b[0]) - 30
        d.text((tx, y + 64), val, font=fv, fill=(8, 15, 30) if tx < bx0 + w else BALTS)
    # starpība
    k2 = ease((t - 1.2) / 0.45)
    if k2 > 0:
        delta = r["G"] - r["xG"]
        txt = f"{delta:+.1f}".replace("-", "−")
        f = fonts("black", int(200 * (0.7 + 0.3 * k2)))
        b = d.textbbox((0, 0), txt, font=f)
        d.text(((W - (b[2] - b[0])) / 2, yb + 400), txt, font=f, fill=akc + (int(255 * k2),))
        sh = r["G"] / r["sog"] * 100 if r["sog"] else 0
        apak = f"goals vs expected  ·  {sh:.0f}% shooting on {int(r['sog'])} SOG"
        teksts_c(d, yb + 640, apak, ietilpinat(d, apak, "reg", 42, x1 - x0 - 80), PELEKS + (int(255 * k2),))
    return im


def aina_outro(t, ilg, kanals, n_met):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = ease(t / 0.4)
    a = int(255 * k)
    teksts_c(d, 560, "LUCK RUNS OUT.", fonts("black", 104), BALTS + (a,))
    teksts_c(d, 700, "xG DOESN'T.", fonts("black", 104), DZELTENS + (a,))
    f = fonts("reg", 44)
    for i, r in enumerate([f"Own xG model · {n_met:,} unblocked shots this season".replace(",", " "),
                           "Empty-net goals excluded"]):
        teksts_c(d, 900 + i * 64, r, f, PELEKS + (a,))
    k2 = ease((t - 0.5) / 0.4)
    pill(d, 0, 1180, "FOLLOW FOR WEEKLY NHL STATS", fonts("bold", 50), ZILS + (int(255 * k2),), (8, 15, 30, int(255 * k2)),
         pad=(44, 24), center=True)
    if kanals:
        teksts_c(d, 1330, kanals, fonts("semi", 52), BALTS + (int(255 * k2),))
    return im


def progress(d, t, kopa):
    d.rectangle([0, 0, W, 10], fill=(255, 255, 255, 30))
    d.rectangle([0, 0, W * min(1, t / kopa), 10], fill=DZELTENS)


# ---------------------------------------------------------------- balss

def runas_teksti(laim, nelaim, periods_txt):
    def vards(r):
        return str(r["vards"])
    t = ["Which NHL scorers are running on luck? Here's goals versus expected goals " + periods_txt + "."]
    for i, (_, r) in enumerate(laim.iterrows(), 1):
        t.append(f"{vards(r)} has {int(r['G'])} goals on just {r['xG']:.1f} expected. "
                 + ("Expect a cooldown." if i == 1 else "That pace won't last." if i == 2 else "Regression is coming."))
    for i, (_, r) in enumerate(nelaim.iterrows(), 1):
        t.append(f"{vards(r)}: {int(r['G'])} goal{'' if int(r['G']) == 1 else 's'}, but {r['xG']:.1f} expected. "
                 + ("He's due." if i == 1 else "The goals will come." if i == 2 else "Buy low."))
    t.append("Luck runs out. Expected goals don't. Follow for weekly NHL stats.")
    return t


def ierunat(teksti, balss, mape):
    """edge-tts → mp3 katrai ainai; atgriež [(fails, ilgums_s)] vai None."""
    try:
        import edge_tts
    except ImportError:
        return None

    async def viens(txt, fails):
        await edge_tts.Communicate(txt, balss, rate="+8%").save(fails)
    out = []
    for i, txt in enumerate(teksti):
        f = os.path.join(mape, f"a{i}.mp3")
        try:
            asyncio.run(viens(txt, f))
        except Exception as ex:                                       # noqa: BLE001
            print(f"Balss neizdevās ({type(ex).__name__}) – video bez skaņas.")
            return None
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                             capture_output=True, text=True).stdout.strip()
        out.append((f, float(dur or 0)))
    return out


# ---------------------------------------------------------------- video

def renderet(laim, nelaim, periods, n_met, izvade, kanals="", balss=None):
    if not shutil.which("ffmpeg"):
        raise SystemExit("Nav ffmpeg (Windows: winget install ffmpeg, tad jauns terminālis).")
    no, lidz = (pd.Timestamp(x) for x in periods)
    info = f"{no:%b %-d} – {lidz:%b %-d}, {lidz:%Y}" if os.name != "nt" else f"{no:%b %#d} – {lidz:%b %#d}, {lidz:%Y}"
    periods_txt = f"from {no:%B} {no.day} to {lidz:%B} {lidz.day}"
    teksti = runas_teksti(laim, nelaim, periods_txt)
    ainas = [("intro", None, None, 3.2)]
    ainas += [("sp", r, i, 3.6) for i, (_, r) in enumerate(laim.iterrows(), 1)]
    ainas += [("sp", r, i, 3.6) for i, (_, r) in enumerate(nelaim.iterrows(), 1)]
    ainas += [("outro", None, None, 3.2)]
    lucky_n = len(laim)
    tmp = tempfile.mkdtemp(prefix="shorts_")
    audio = ierunat(teksti, balss, tmp) if balss else None
    if audio and len(audio) == len(ainas):
        ainas = [(a[0], a[1], a[2], max(a[3], dur + 0.45)) for a, (_, dur) in zip(ainas, audio)]
    kopa = sum(a[3] for a in ainas)
    bg = fons()
    video_tmp = os.path.join(tmp, "v.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          video_tmp], stdin=subprocess.PIPE)
    t0 = 0.0
    for idx, (veids, r, nr, ilg) in enumerate(ainas):
        n = int(round(ilg * FPS))
        for fr in range(n):
            t = fr / FPS
            if veids == "intro":
                sl = aina_intro(t, ilg, info)
            elif veids == "outro":
                sl = aina_outro(t, ilg, kanals, n_met)
            else:
                sl = aina_speletajs(t, ilg, r, nr, idx <= lucky_n)
            dx, alfa = slide(t, ilg) if veids == "sp" else (0, min(1, t / 0.25) if t < 0.25 else 1)
            kadrs = bg.copy()
            if alfa < 1:
                sl.putalpha(sl.getchannel("A").point(lambda v: int(v * alfa)))
            kadrs.paste(sl, (int(dx), 0), sl)
            progress(ImageDraw.Draw(kadrs, "RGBA"), t0 + t, kopa)
            p.stdin.write(kadrs.tobytes())
        t0 += ilg
    p.stdin.close()
    p.wait()
    if audio and len(audio) == len(ainas):
        # katras ainas balss sākas ainas sākumā (+0.15 s)
        ievades, filtri, sak = [], [], 0.0
        for i, ((f, _), a) in enumerate(zip(audio, ainas)):
            ievades += ["-i", f]
            ms = int((sak + 0.15) * 1000)
            filtri.append(f"[{i + 1}:a]adelay={ms}|{ms}[a{i}]")
            sak += a[3]
        filtri.append("".join(f"[a{i}]" for i in range(len(audio))) + f"amix=inputs={len(audio)}:normalize=0[aout]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_tmp, *ievades, "-filter_complex", ";".join(filtri),
                        "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", izvade], check=True)
    else:
        shutil.move(video_tmp, izvade)
    shutil.rmtree(tmp, ignore_errors=True)
    return teksti, kopa, bool(audio)


def apraksts(laim, nelaim, teksti, kanals):
    v1 = laim.iloc[0]["vards"] if len(laim) else ""
    nos = f"{v1} is running HOT… but xG says it won't last 🏒 #NHL #Shorts"
    tags = "#NHL #hockey #NHLstats #xG #fantasyhockey #Shorts"
    rindas = [f"{r['vards']} ({r['team']}): {int(r['G'])} G vs {r['xG']:.1f} xG" for _, r in pd.concat([laim, nelaim]).iterrows()]
    return (f"VIRSRAKSTS:\n{nos}\n\nAPRAKSTS:\nGoals vs expected goals (xG) – who's lucky and who's due.\n"
            + "\n".join(rindas) + f"\nxG from our own model (unblocked shots, empty-net goals excluded).\n{tags}\n\n"
            "RUNAS TEKSTS (pa ainām):\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(teksti)) + "\n")


def main():
    ap = argparse.ArgumentParser(description="NHL xG Luck Report → YouTube Shorts MP4")
    ap.add_argument("--dienas", type=int, default=None, help="tikai pēdējās N dienas (noklusējums: visa sezona)")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--min-metieni", type=int, default=15)
    ap.add_argument("--balss", default="en-US-AndrewNeural", help="edge-tts balss (piem. en-US-GuyNeural, en-US-AndrewNeural)")
    ap.add_argument("--bez-balss", action="store_true")
    ap.add_argument("--kanals", default="", help="kanāla nosaukums beigu kadram, piem. @nhlxg")
    ap.add_argument("--mape", default=os.path.join(BASE, "video"))
    a = ap.parse_args()
    laim, nelaim, periods, n_met = dati(a.dienas, a.min_metieni, a.top)
    if laim.empty or nelaim.empty:
        print("Nepietiek datu (samazini --min-metieni vai palielini --dienas).")
        return 1
    os.makedirs(a.mape, exist_ok=True)
    izv = os.path.join(a.mape, f"xg_luck_{periods[1]}.mp4")
    teksti, kopa, ar_balsi = renderet(laim, nelaim, periods, n_met, izv, a.kanals, None if a.bez_balss else a.balss)
    with open(izv[:-4] + ".txt", "w", encoding="utf-8") as f:
        f.write(apraksts(laim, nelaim, teksti, a.kanals))
    print(f"Gatavs: {izv} ({kopa:.0f} s, {'ar balsi' if ar_balsi else 'bez skaņas'})\nTeksti: {izv[:-4]}.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
