"""
ShortsB.py – STILS "STORY" (spilgts, kā Instagram/TikTok stāsti, ar "uzmini pats" sajūtu)

Izmanto shorts.py (tam jābūt tajā pašā mapē) – visi dati, teksti un komandas paliek tieši tādi paši,
mainās tikai izskats un kustība:
  • krāsains "ziemeļblāzmas" fons – lēni peldoši zili / violeti / dzelteni mirdzumi
  • ainas "uzlec" no apakšas ar nelielu atsitienu
  • saraksti atklājas no apakšas uz augšu (#5 → #1), #1 beigās izgaismojas
  • lielie skaitļi skaitās augšā
  • āķa ainā uzlīme "GUESS BEFORE THE REVEAL", beigās – aicinājums komentēt
  • komandu krāsas kartītēs un datu joslās (primārā + sekundārā krāsa)
  • fons – izpludināts hokeja video (B-roll) no mapes shorts_fons\\ (ja tur ir video)
  • audio: klusa fona mūzika no mapes shorts_muzika\\ + skaņu efekti (swoosh, boom, tick)

Mapes (izveido pats nhl-stats saknē; ja mapes nav vai tā tukša – attiecīgā daļa vienkārši izpaliek):
  shorts_fons\\     1–5 īsi hokeja video (.mp4/.mov) no Pexels / Pixabay (bezmaksas, komerciāli drīkst).
                    Skripts katram video izvēlas vienu, izpludina, aptumšo un atkārto cilpā.
  shorts_muzika\\   1+ fona mūzikas faili (.mp3) no YouTube Audio Library / Pixabay Music.
                    Skaļums ~15 %, kamēr runā balss – vēl klusāk; beigās izbalē.
  shorts_sfx\\      (nav obligāti) swoosh.mp3 / boom.mp3 / tick.mp3 – aizstāj skripta ģenerētos efektus.
Papildu parametri: --bez-fona-video  --bez-muzikas  --bez-sfx

Lietošana – tieši tāpat kā shorts.py, tikai cits faila nosaukums:
    python ShortsB.py --veids tiesnesi --kanals @tavskanals
Video, INFO.txt un vēsture (fakti, tiesneši, fantasy rezultāti, atskati) – parastajā mapē video\\, tāpat kā shorts.py.
Failu var saukt kā grib (piem. ShortsB.py), bet shorts.py jāatrodas tajā pašā mapē.
"""
import colorsys
import math
import os
import random
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

import shorts as S

STILS = "B"
VIOLETS = (139, 92, 246)

MAPE_FONS = os.path.join(S.BASE, "shorts_fons")
MAPE_MUZIKA = os.path.join(S.BASE, "shorts_muzika")
MAPE_SFX = os.path.join(S.BASE, "shorts_sfx")
MUZIKAS_SKALUMS = 0.15          # fona mūzika (0–1); kamēr runā balss, automātiski vēl klusāk
SFX_SKALUMS = 0.55              # skaņu efekti
FONA_TUMSUMS = 0.55             # cik stipri fona video aptumšots (0 = neaptumšots, 1 = melns)
SR = 44100
VIDEO_PAPL = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
AUDIO_PAPL = (".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac")
OPC = {"fons": True, "muzika": True, "sfx": True}

# komandu sekundārās krāsas (primārās – shorts.KOMANDAS)
SEKUNDARAS = {
    "ANA": (185, 151, 91), "BOS": (230, 230, 235), "BUF": (252, 181, 20), "CGY": (241, 190, 72), "CAR": (162, 170, 173),
    "CHI": (255, 209, 0), "COL": (35, 97, 146), "CBJ": (206, 17, 38), "DAL": (162, 170, 173), "DET": (230, 230, 235),
    "EDM": (4, 30, 66), "FLA": (185, 151, 91), "LAK": (230, 230, 235), "MIN": (166, 25, 46), "MTL": (25, 33, 104),
    "NSH": (4, 30, 66), "NJD": (230, 230, 235), "NYI": (244, 125, 48), "NYR": (206, 17, 38), "OTT": (183, 146, 87),
    "PHI": (230, 230, 235), "PIT": (230, 230, 235), "SJS": (234, 114, 0), "SEA": (232, 24, 40), "STL": (252, 181, 20),
    "TBL": (230, 230, 235), "TOR": (230, 230, 235), "UTA": (230, 230, 235), "VAN": (0, 132, 61), "VGK": (51, 63, 72),
    "WSH": (4, 30, 66), "WPG": (172, 22, 44),
}


def spilgta(kr, v_min=0.84):
    """Tumšas komandu krāsas padara gaišākas (tas pats tonis), lai tās labi redz uz tumša fona."""
    h, s_, v = colorsys.rgb_to_hsv(*(x / 255 for x in kr[:3]))
    v = max(v, v_min)
    if s_ < 0.15:
        v = max(v, 0.88)
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s_, v))


def kom_krasas(kom):
    """(primārā, sekundārā) – abas gaišas pietiekami, un savā starpā atšķirīgas."""
    p = spilgta(S.kkrasa(kom))
    s_ = spilgta(SEKUNDARAS.get(str(kom), (230, 230, 235)))
    if sum(abs(a - b) for a, b in zip(p, s_)) < 90:
        s_ = (235, 238, 245) if sum(p) < 600 else (120, 140, 170)
    return p, s_


# ---------------------------------------------------------------- palīgfunkcijas
def ease_back(t, s=1.6):
    t = min(1.0, max(0.0, t)) - 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def skaitit(txt, k):
    txt = str(txt)
    m = re.search(r"\d+(?:\.\d+)?", txt)
    if not m or k >= 1:
        return txt
    s = m.group(0)
    dec = len(s.split(".")[1]) if "." in s else 0
    return txt[:m.start()] + f"{float(s) * max(0.0, k):.{dec}f}" + txt[m.end():]


# ---------------------------------------------------------------- ziemeļblāzmas fons
class Fons:
    def __init__(self):
        a = S.np.linspace(0, 1, S.H)[:, None, None]
        img = (S.np.array((12, 10, 30)) * (1 - a) + S.np.array((18, 28, 60)) * a).repeat(S.W, axis=1).astype(S.np.uint8)
        self.base = Image.fromarray(img, "RGB")
        self.blobi = []
        for kr, izm in ((S.ZILS, 900), (VIOLETS, 1000), (S.DZELTENS, 700)):
            m = Image.new("L", (izm, izm), 0)
            ImageDraw.Draw(m).ellipse([izm * 0.2, izm * 0.2, izm * 0.8, izm * 0.8], fill=95 if kr != S.DZELTENS else 45)
            self.blobi.append((Image.new("RGB", (izm, izm), kr), m.filter(ImageFilter.GaussianBlur(izm // 7)), izm))

    def kadrs(self, T):
        im = self.base.copy()
        cel = ((0.20, 0.25, 0.13, 0.21), (0.75, 0.55, 0.11, 0.17), (0.40, 0.85, 0.17, 0.09))
        for (kr, m, izm), (fx, fy, sx, sy) in zip(self.blobi, cel):
            x = S.W * fx + 260 * math.sin(T * sx * 2.2) - izm / 2
            y = S.H * fy + 300 * math.cos(T * sy * 2.2) - izm / 2
            im.paste(kr, (int(x), int(y)), m)
        d = ImageDraw.Draw(im, "RGBA")
        d.line([(0, 1250), (S.W, 1250)], fill=(220, 38, 38, 30), width=6)
        d.ellipse([S.W / 2 - 330, 920, S.W / 2 + 330, 1580], outline=(255, 255, 255, 18), width=5)
        return im


class VideoFons:
    """Izpludināts hokeja video (B-roll) no shorts_fons\\, cilpā, aptumšots; virsū – vieglas krāsu blāzmas."""
    def __init__(self, fails):
        self.w, self.h = 360, 640
        vf = (f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h},"
              f"gblur=sigma=9,eq=saturation=0.8,fps={S.FPS}")
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", fails, "-an", "-vf", vf,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.n = self.w * self.h * 3
        self.pedejais = None
        a = S.np.linspace(0, 1, S.H)[:, None, None]
        tint = (S.np.array((10, 12, 32)) * (1 - a) + S.np.array((16, 26, 58)) * a).repeat(S.W, axis=1).astype(S.np.uint8)
        self.tint = Image.fromarray(tint, "RGB")
        self.blazma = Fons()

    def kadrs(self, T):
        b = self.p.stdout.read(self.n)
        if len(b) == self.n:
            self.pedejais = Image.frombytes("RGB", (self.w, self.h), b).resize((S.W, S.H), Image.BILINEAR)
        im = self.pedejais if self.pedejais is not None else self.tint.copy()
        im = Image.blend(im, self.tint, FONA_TUMSUMS)
        bl = self.blazma.kadrs(T)                                     # krāsu blāzmas pāri video (vieglāk)
        return Image.blend(im, bl, 0.35)

    def aizvert(self):
        try:
            self.p.kill()
        except Exception:                                             # noqa: BLE001
            pass


def izveleties_fonu():
    if not OPC["fons"] or not os.path.isdir(MAPE_FONS):
        return None
    faili = sorted(f for f in os.listdir(MAPE_FONS) if f.lower().endswith(VIDEO_PAPL))
    return os.path.join(MAPE_FONS, random.choice(faili)) if faili else None


# ---------------------------------------------------------------- audio: skaņu efekti un mūzika
def _swoosh():
    d = 0.42
    n = int(SR * d)
    t = S.np.arange(n) / SR
    troks = S.np.random.default_rng(3).standard_normal(n)
    cut = 250 + 5200 * S.np.sin(S.np.pi * t / d) ** 1.5
    alfa = 1 - S.np.exp(-2 * S.np.pi * cut / SR)
    y = S.np.zeros(n)
    v = 0.0
    for i in range(n):
        v += alfa[i] * (troks[i] - v)
        y[i] = v
    y *= S.np.sin(S.np.pi * t / d) ** 2
    return 0.7 * y / max(1e-6, abs(y).max())


def _boom():
    d = 1.0
    n = int(SR * d)
    t = S.np.arange(n) / SR
    f = 42 + 95 * S.np.exp(-t * 7)
    y = S.np.sin(2 * S.np.pi * S.np.cumsum(f) / SR) * S.np.exp(-t * 4.2)
    y[:int(SR * 0.012)] += S.np.random.default_rng(5).standard_normal(int(SR * 0.012)) * 0.35 * S.np.linspace(1, 0, int(SR * 0.012))
    return 0.95 * y / max(1e-6, abs(y).max())


def _tick():
    d = 0.05
    t = S.np.arange(int(SR * d)) / SR
    return 0.35 * S.np.sin(2 * S.np.pi * 1900 * t) * S.np.exp(-t * 110)


def _ielasit_audio(fails):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", fails, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True)
    y = S.np.frombuffer(r.stdout, dtype=S.np.int16).astype(float) / 32768
    return y if len(y) else None


def skanas():
    """Efektu paraugi: no shorts_sfx\\ (ja ir swoosh/boom/tick fails), citādi ģenerēti."""
    out = {"swoosh": _swoosh(), "boom": _boom(), "tick": _tick()}
    if os.path.isdir(MAPE_SFX):
        for f in os.listdir(MAPE_SFX):
            nos, ext = os.path.splitext(f.lower())
            if nos in out and ext in AUDIO_PAPL:
                y = _ielasit_audio(os.path.join(MAPE_SFX, f))
                if y is not None:
                    out[nos] = y
    return out


def sfx_notikumi(ainas):
    """[(laiks_s, efekts, skaļums)] – pēc tā, kas notiek katrā ainā."""
    ev, t0 = [], 0.0
    for nr, (veids, c, ilg) in enumerate(ainas):
        if nr > 0:
            ev.append((max(0, t0 - 0.12), "swoosh", 0.8))
        tips = c.get("tips") if c else veids
        if nr == 0:
            ev.append((t0 + 0.12, "boom", 0.7))
        if tips == "fakts_hook":
            ev.append((t0 + 1.0, "tick", 0.9))
        elif tips == "intro":
            ev.append((t0 + 1.0, "tick", 0.9))
        elif tips == "fakts_konteksts":
            ev.append((t0 + 0.9, "boom", 1.0))
        elif tips == "fantasy":
            ev += [(t0 + 0.3 + 0.08 * i, "tick", 0.6) for i in range(len(c.get("flizes", [])))]
            ev.append((t0 + 1.45, "boom", 0.8))
        elif tips == "fakts_saraksts":
            rindas = c["rindas"][-9:]
            n = len(rindas)
            reit = _ir_reitings(rindas)
            solis = 0.2 if reit else 0.16
            ev += [(t0 + 0.2 + solis * j, "tick", 0.7) for j in range(n)]
            if reit and n > 1:
                ev.append((t0 + 0.2 + solis * (n - 1) + 0.05, "boom", 0.55))
        elif veids == "karte" and tips not in ("grafiks", "fakts_nakamais"):
            ev += [(t0 + 0.4, "tick", 0.6), (t0 + 0.6, "tick", 0.6)]
            ev.append((t0 + 2.05, "boom", 0.9))
        t0 += ilg
    return ev


def sfx_celins(ainas, kopa, fails):
    sk = skanas()
    y = S.np.zeros(int(SR * (kopa + 1.5)))
    for laiks, efekts, sk_ in sfx_notikumi(ainas):
        a = sk[efekts] * sk_
        i = int(laiks * SR)
        j = min(len(y), i + len(a))
        y[i:j] += a[:j - i]
    y = S.np.clip(y * SFX_SKALUMS, -1, 1)
    import wave
    with wave.open(fails, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype(S.np.int16).tobytes())
    return fails


def izveleties_muziku():
    if not OPC["muzika"] or not os.path.isdir(MAPE_MUZIKA):
        return None
    faili = sorted(f for f in os.listdir(MAPE_MUZIKA) if f.lower().endswith(AUDIO_PAPL))
    return os.path.join(MAPE_MUZIKA, random.choice(faili)) if faili else None


def miksets(video_tmp, izvade, balss, ainas, kopa, tmp):
    """Balss + skaņu efekti + fona mūzika (mūzika automātiski klusāka, kamēr runā balss)."""
    sfx = sfx_celins(ainas, kopa, os.path.join(tmp, "sfx.wav")) if OPC["sfx"] else None
    muz = izveleties_muziku()
    if not balss and not sfx and not muz:
        import shutil
        shutil.move(video_tmp, izvade)
        return
    ievades, filtri, celini, idx = [], [], [], 1
    if balss:
        sak, b_ = 0.0, []
        for i, ((f, _), a) in enumerate(zip(balss, ainas)):
            ievades += ["-i", f]
            ms = int((sak + 0.15) * 1000)
            filtri.append(f"[{idx}:a]adelay={ms}|{ms}[b{i}]")
            b_.append(f"[b{i}]")
            sak += a[2]
            idx += 1
        filtri.append("".join(b_) + f"amix=inputs={len(b_)}:normalize=0,aformat=channel_layouts=stereo[balss]")
    if sfx:
        ievades += ["-i", sfx]
        filtri.append(f"[{idx}:a]aformat=channel_layouts=stereo[sfx]")
        celini.append("[sfx]")
        idx += 1
    if muz:
        ievades += ["-stream_loop", "-1", "-i", muz]
        beigas = max(0.0, kopa - 1.8)
        filtri.append(f"[{idx}:a]atrim=0:{kopa:.2f},asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,"
                      f"volume={MUZIKAS_SKALUMS},afade=t=in:d=0.8,afade=t=out:st={beigas:.2f}:d=1.8[muz0]")
        if balss:
            filtri.append("[balss]asplit=2[balss1][balss2]")
            filtri.append("[muz0][balss2]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=350[muz]")
            celini = ["[balss1]"] + celini + ["[muz]"]
        else:
            celini.append("[muz0]")
        idx += 1
    elif balss:
        celini = ["[balss]"] + celini
    filtri.append("".join(celini) + f"amix=inputs={len(celini)}:normalize=0,alimiter=limit=0.95[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_tmp, *ievades, "-filter_complex", ";".join(filtri),
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{kopa:.2f}",
                    izvade], check=True)
    dalas = (["balss"] if balss else []) + (["efekti"] if sfx else []) + ([f"mūzika: {os.path.basename(muz)}"] if muz else [])
    print("AUDIO: " + " + ".join(dalas))


# ---------------------------------------------------------------- ainas
def uzlime(im, txt, y, lenkis=-6, kr=S.DZELTENS):
    """Mazliet sašķiebta "uzlīme" (sticker)."""
    f = S.fonts("black", 46)
    tmp = Image.new("RGBA", (S.W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    S.pill(d, 0, 50, txt, f, kr, S.MELNS, pad=(40, 20), center=True)
    tmp = tmp.rotate(lenkis, resample=Image.BICUBIC, expand=False)
    im.alpha_composite(tmp, (0, int(y)))


def aina_fakts_hook(t, c):
    im = _orig["fakts_hook"](t, c)
    k = ease_back((t - 1.0) / 0.45)
    if k > 0.02:
        sc = max(0.05, k)
        st = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
        uzlime(st, "GUESS BEFORE THE REVEAL", 1380)
        if sc < 0.999:
            w, h = int(S.W * sc), int(S.H * sc)
            st = st.resize((w, h), Image.BILINEAR)
            big = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
            big.alpha_composite(st, ((S.W - w) // 2, int(1460 - 1460 * sc)))
            st = big
        im.alpha_composite(st)
    return im


def aina_intro(t, s):
    im = _orig["intro"](t, s)
    if t > 1.0:
        tag = str(s.get("tag", "")).upper()
        if "FOLLOW" in tag or "RECAP" in tag:
            txt = "DID WE GET IT RIGHT?"
        elif "FANTASY" in tag:
            txt = "WHO'S #1? WATCH TILL THE END"
        elif "GOALIE" in tag:
            txt = "HOT HAND OR LUCKY?"
        else:
            txt = "WHO'S LUCKY? WHO'S DUE?"
        uzlime(im, txt, 1580, 5, S.ZILS)
    return im


def _skaitlis(v):
    m = re.search(r"-?\d+(?:\.\d+)?", str(v))
    return float(m.group(0)) if m and re.fullmatch(r"[+\-−]?\d+(?:\.\d+)?%?", str(v).strip()) else None


def _ir_reitings(rindas):
    """Vai saraksts ir reitings (#1 augšā)? – visas vērtības skaitļi un sakārtoti augošā vai dilstošā secībā."""
    v = [_skaitlis(r[2]) for r in rindas]
    if len(v) < 2 or any(x is None for x in v):
        return False
    return all(a >= b for a, b in zip(v, v[1:])) or all(a <= b for a, b in zip(v, v[1:]))


def aina_fakts_saraksts(t, c):
    """Saraksts atklājas no apakšas (#5 → #1); vērtības skaitās; #1 beigās izgaismojas."""
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S.pill(d, 0, 250, c["saraksts_virs"], S.ietilpinat(d, c["saraksts_virs"], "semi", 40, S.W - 160), c.get("pill_kr", S.ZILS), S.MELNS, center=True)
    x0, x1 = 70, S.W - 70
    rindas = c["rindas"][-9:]
    n = len(rindas)
    rh, y0 = 112, 400
    d.rounded_rectangle([x0, y0, x1, y0 + 40 + rh * max(1, n)], radius=40, fill=(15, 18, 42, 225), outline=(255, 255, 255, 40), width=3)
    solis = 0.2
    reit = _ir_reitings(rindas)                                       # reitings → atklāj no apakšas, #1 izgaismo
    if not reit:
        solis = 0.16
    for i, (a_, b_, c_) in enumerate(rindas):
        sec = n - 1 - i if reit else i
        k = S.ease((t - 0.2 - solis * sec) / 0.3)
        if k <= 0:
            continue
        y = y0 + 30 + i * rh + (1 - k) * 30
        if reit and i == 0 and n > 1:
            kg = S.ease((t - 0.2 - solis * sec - 0.1) / 0.35)
            d.rounded_rectangle([x0 + 14, y - 6, x1 - 14, y + rh - 14], radius=28, fill=S.ar_alfa(S.DZELTENS, 40 * kg),
                                outline=S.ar_alfa(S.DZELTENS, 220 * kg), width=4)
        vw = c.get("vards_w", 300)
        d.text((x0 + 44, y + 22), str(a_), font=S.ietilpinat(d, str(a_), "semi", 40, vw - 20), fill=S.ar_alfa(c.get("vards_kr", S.PELEKS), 255 * k))
        d.text((x0 + 30 + vw, y + 18), str(b_), font=S.ietilpinat(d, str(b_), "bold", 46, 300), fill=S.ar_alfa(S.BALTS, 255 * k))
        v = skaitit(c_, S.ease((t - 0.2 - solis * sec) / 0.5))
        fv = S.ietilpinat(d, str(c_), "black", 50, 330)
        d.text((x1 - 44 - S.platums(d, str(c_), fv), y + 16), v, font=fv, fill=S.ar_alfa(S.DZELTENS, 255 * k))
        if i < n - 1:
            d.line([(x0 + 40, y + rh - 6), (x1 - 40, y + rh - 6)], fill=S.ar_alfa((255, 255, 255), 25 * k), width=2)
    k2 = S.ease((t - 0.35 - solis * n) / 0.4)
    if k2 > 0:
        yk = y0 + 80 + rh * max(1, n)
        S.teksts_c(d, yk, c["kopsavilkums"], S.ietilpinat(d, c["kopsavilkums"], "black", 64, S.W - 140), S.ar_alfa(S.BALTS, 255 * k2))
    return im


def aina_fakts_konteksts(t, c):
    c2 = dict(c)
    c2["k_skaitlis"] = skaitit(c["k_skaitlis"], S.ease(t / 0.9))
    im = _orig["fakts_konteksts"](t, c2)
    return im


def aina_karte(t, c):
    """xG / atskata kartīte: rāmis, akcenti un datu joslas komandas krāsās; skaitļi skaitās augšā."""
    W, d_ = S.W, None
    im = Image.new("RGBA", (W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    prim, sek = kom_krasas(c.get("badge"))
    akc = c["akc"]
    S.pill(d, 0, 250, c["augsa"], S.fonts("semi", 40), akc, S.MELNS if akc == S.ZALS else S.BALTS, center=True)
    x0, y0, x1, y1 = 70, 380, W - 70, 1640
    d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=(15, 18, 40, 235), outline=S.ar_alfa(prim, 170), width=4)
    d.rounded_rectangle([x0, y0, x1, y0 + 22], radius=11, fill=c["bkr"])
    d.rectangle([x0 + 40, y0 + 22, x1 - 40, y0 + 28], fill=sek)
    d.text((x0 + 50, y0 + 60), f"#{c['nr']}", font=S.fonts("black", 92), fill=akc)
    fb = S.fonts("bold", 48)
    S.pill(d, x1 - 50 - S.platums(d, c["badge"], fb) - 68, y0 + 80, c["badge"], fb, c["bkr"], S.uz_fona(c["bkr"]), pad=(34, 14))
    d.text((x0 + 50, y0 + 210), c["v1"].upper(), font=S.fonts("semi", 54), fill=prim)
    f2 = S.ietilpinat(d, c["v2"].upper(), "black", 120, x1 - x0 - 100)
    d.text((x0 + 50, y0 + 275), c["v2"].upper(), font=f2, fill=S.BALTS)
    d.text((x0 + 50, y0 + 425), c["info"], font=S.ietilpinat(d, c["info"], "reg", 44, x1 - x0 - 100), fill=S.PELEKS)
    k = S.ease((t - 0.35) / 0.9)
    yb = y0 + 560
    bx0, bx1 = x0 + 50, x1 - 50
    div = c.get("diverg", False)
    mx = max([abs(b[1]) for b in c["bars"]] + [1]) * (1.25 if div else 1.08)
    for i, bar in enumerate(c["bars"]):
        nos, v, kr, fmt = bar[:4]
        kr = prim if kr == S.BALTS else (sek if kr == S.ZILS else kr)
        baze = bar[4] if len(bar) > 4 else 0
        y = yb + i * 190
        d.text((bx0, y), nos, font=S.fonts("semi", 40), fill=S.PELEKS)
        d.rounded_rectangle([bx0, y + 62, bx1, y + 142], radius=40, fill=S.TUMSS)
        vv = v * k
        txt = fmt.format(baze + vv)
        txt = S.minus(txt) if "+" in fmt or baze + vv < 0 else txt
        if div and c.get("nulle") and i == 0:
            fz = S.fonts("semi", 32)
            d.text(((bx0 + bx1) / 2 - S.platums(d, c["nulle"], fz) / 2, y + 8), c["nulle"], font=fz, fill=S.PELEKS)
        fv = S.fonts("black", 64)
        tw = S.platums(d, txt, fv)
        if div:
            cx = (bx0 + bx1) / 2
            d.line([(cx, y + 50), (cx, y + 154)], fill=(255, 255, 255, 90), width=4)
            w = (bx1 - bx0) / 2 * (abs(vv) / mx)
            if w > 6:
                xa, xb = (cx, cx + w) if vv >= 0 else (cx - w, cx)
                d.rounded_rectangle([xa, y + 62, xb, y + 142], radius=min(40, w / 2), fill=kr)
            arpus = (cx + w + 20 + tw <= bx1 - 10) if vv >= 0 else (cx - w - 20 - tw >= bx0 + 10)
            if arpus:
                tx, krt = (cx + w + 20 if vv >= 0 else cx - w - 20 - tw), S.BALTS
            else:
                tx, krt = (cx + w - tw - 28 if vv >= 0 else cx - w + 28), S.uz_fona(kr)
            d.text((tx, y + 64), txt, font=fv, fill=krt)
        else:
            w = (bx1 - bx0) * (max(vv, 0) / mx)
            if w > 80:
                d.rounded_rectangle([bx0, y + 62, bx0 + w, y + 142], radius=40, fill=kr)
            ieksa = w + tw + 60 >= bx1 - bx0
            tx = bx0 + w - tw - 30 if ieksa else bx0 + max(w, 0) + 20
            d.text((tx, y + 64), txt, font=fv, fill=S.uz_fona(kr) if ieksa else S.BALTS)
    k2 = S.ease((t - 1.2) / 0.45)
    if k2 > 0:
        liels = skaitit(c["liels"], S.ease((t - 1.2) / 0.9))
        f = S.ietilpinat(d, c["liels"], "black", int(c.get("liels_izm", 200) * (0.7 + 0.3 * k2)), x1 - x0 - 80)
        S.teksts_c(d, yb + 410, liels, f, S.ar_alfa(akc, 255 * k2))
        S.teksts_c(d, yb + 640, c["apaksa"], S.ietilpinat(d, c["apaksa"], "reg", 42, x1 - x0 - 80), S.ar_alfa(S.PELEKS, 255 * k2))
    return im


def aina_fantasy(t, c):
    """Fantasy kartīte: flīžu vērtības un lielais verdikts skaitās; rāmis komandas krāsā."""
    c2 = dict(c)
    c2["liels"] = skaitit(c["liels"], S.ease((t - 1.3) / 0.9))
    c2["flizes"] = [(lab, val if ":" in str(val) else skaitit(val, S.ease((t - 0.3 - 0.08 * i) / 0.55)), sub)
                    for i, (lab, val, sub) in enumerate(c["flizes"])]
    im = _orig["fantasy"](t, c2)
    prim, sek = kom_krasas(c.get("badge"))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 70, 380, S.W - 70, 1640
    d.rounded_rectangle([x0, y0, x1, y1], radius=48, outline=S.ar_alfa(prim, 170), width=4)
    d.rectangle([x0 + 40, y0 + 22, x1 - 40, y0 + 28], fill=sek)
    return im


def aina_outro(t, s, kanals):
    im = _orig["outro"](t, s, kanals)
    if not s.get("cta") and t > 0.9:
        k = ease_back((t - 0.9) / 0.5)
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = 120, 1440, S.W - 120, 1600
        dy = (1 - k) * 80
        d.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=36, fill=(255, 255, 255, 235))
        S.teksts_c(d, y0 + 30 + dy, "COMMENT BELOW", S.fonts("black", 54), S.MELNS)
        S.teksts_c(d, y0 + 98 + dy, "What should we cover next?", S.fonts("semi", 36), (71, 85, 105))
    return im


_orig = {}


def renderet(s, izvade, kanals="", balss=None):
    import shutil, tempfile
    if not shutil.which("ffmpeg"):
        raise SystemExit("Nav ffmpeg (Windows: winget install ffmpeg, tad jauns terminālis).")
    ainas = ([("intro", None, 3.2)] if s.get("intro") else []) + [("karte", c, c.get("ilgums", 3.6)) for c in s["kartes"]] \
        + [("outro", None, 4.5 if s["outro"].get("cta") else 3.6)]
    tmp = tempfile.mkdtemp(prefix="shorts_")
    audio = S.ierunat(s["runa"], balss, tmp) if balss else None
    if audio and len(audio) == len(ainas) and all(dur > 0 for _, dur in audio):
        ainas = [(v, c, max(ilg, dur + 0.45)) for (v, c, ilg), (_, dur) in zip(ainas, audio)]
    else:
        if audio:
            print("BALSS: audio faili tukši vai nepilnīgi – video bez skaņas.")
        audio = None
    kopa = sum(a[2] for a in ainas)
    fona_fails = izveleties_fonu()
    fons = VideoFons(fona_fails) if fona_fails else Fons()
    if fona_fails:
        print(f"FONS: {os.path.basename(fona_fails)}")
    video_tmp = os.path.join(tmp, "v.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S.W}x{S.H}",
                          "-r", str(S.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          video_tmp], stdin=subprocess.PIPE)
    fn_map = {"fantasy": aina_fantasy, "grafiks": S.aina_grafiks, "fakts_hook": aina_fakts_hook,
              "fakts_saraksts": aina_fakts_saraksts, "fakts_konteksts": aina_fakts_konteksts,
              "fakts_nakamais": S.aina_fakts_nakamais}
    t0 = 0.0
    for nr, (veids, c, ilg) in enumerate(ainas):
        for fr in range(int(round(ilg * S.FPS))):
            t = fr / S.FPS
            if veids == "intro":
                sl = aina_intro(t, s["intro"])
            elif veids == "outro":
                sl = aina_outro(t, s["outro"], kanals)
            else:
                sl = fn_map.get(c.get("tips"), aina_karte)(t, c)
            # pāreja: uzlec no apakšas ar atsitienu; iziet – izbalē un paceļas
            if t < 0.4:
                k = ease_back(t / 0.4)
                alfa, dy = min(1, t / 0.2), (1 - k) * 260
            elif t > ilg - 0.22 and veids != "outro":
                k = S.ease((t - (ilg - 0.22)) / 0.22)
                alfa, dy = 1 - k, -k * 120
            else:
                alfa, dy = 1, 0
            kadrs = fons.kadrs(t0 + t)
            if alfa < 1:
                sl.putalpha(sl.getchannel("A").point(lambda v: int(v * alfa)))
            kadrs.paste(sl, (0, int(dy)), sl)
            dd = ImageDraw.Draw(kadrs, "RGBA")
            fz = S.ietilpinat(dd, s["zimogs"], "semi", 34, S.W - 100)
            S.teksts_c(dd, 170, s["zimogs"], fz, S.ar_alfa(S.PELEKS, 235))
            # progresa josla: dzeltena līnija augšā (kā shorts.py)
            dd.rectangle([0, 0, S.W, 10], fill=(255, 255, 255, 30))
            dd.rectangle([0, 0, S.W * min(1, (t0 + t) / kopa), 10], fill=S.DZELTENS)
            p.stdin.write(kadrs.tobytes())
        t0 += ilg
    p.stdin.close()
    p.wait()
    if fona_fails:
        fons.aizvert()
    miksets(video_tmp, izvade, audio, ainas, kopa, tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    return kopa, bool(audio)


def ieslegt():
    for k in ("fakts_konteksts", "karte", "fantasy", "fakts_hook", "outro", "intro"):
        _orig[k] = getattr(S, "aina_" + k)
    S.renderet = renderet
    for arg, k in (("--bez-fona-video", "fons"), ("--bez-muzikas", "muzika"), ("--bez-sfx", "sfx")):
        if arg in sys.argv:
            OPC[k] = False
            sys.argv.remove(arg)


if __name__ == "__main__":
    ieslegt()
    print(f"STILS {STILS}: STORY")
    sys.exit(S.main())
