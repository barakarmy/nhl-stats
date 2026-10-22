"""
shorts_B.py – TESTA STILS "STORY" (spilgts, kā Instagram/TikTok stāsti, ar "uzmini pats" sajūtu)

Izmanto shorts.py (tam jābūt tajā pašā mapē) – visi dati, teksti un komandas paliek tieši tādi paši,
mainās tikai izskats un kustība:
  • krāsains "ziemeļblāzmas" fons – lēni peldoši zili / violeti / dzelteni mirdzumi
  • augšā stāstu stila progresa josla – katrai ainai savs posms (redzams, cik vēl palicis)
  • ainas "uzlec" no apakšas ar nelielu atsitienu
  • saraksti atklājas no apakšas uz augšu (#5 → #1), #1 beigās izgaismojas
  • lielie skaitļi skaitās augšā
  • āķa ainā uzlīme "GUESS BEFORE THE REVEAL", beigās – aicinājums komentēt

Lietošana – tieši tāpat kā shorts.py, tikai cits faila nosaukums:
    python shorts_B.py --veids tiesnesi --kanals @tests
Video tiek saglabāti mapē video_test\\ (lai testi neietekmē īsto faktu / tiesnešu vēsturi).
"""
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFilter

import shorts as S

STILS = "B"
VIOLETS = (139, 92, 246)


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
    c2 = dict(c)
    c2["liels"] = skaitit(c["liels"], S.ease((t - 1.2) / 0.9))
    im = _orig["karte"](t, c2)
    return im


def aina_fantasy(t, c):
    c2 = dict(c)
    c2["liels"] = skaitit(c["liels"], S.ease((t - 1.3) / 0.9))
    return _orig["fantasy"](t, c2)


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
    import shutil, subprocess, tempfile
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
    fons = Fons()
    video_tmp = os.path.join(tmp, "v.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S.W}x{S.H}",
                          "-r", str(S.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          video_tmp], stdin=subprocess.PIPE)
    fn_map = {"fantasy": aina_fantasy, "grafiks": S.aina_grafiks, "fakts_hook": aina_fakts_hook,
              "fakts_saraksts": aina_fakts_saraksts, "fakts_konteksts": aina_fakts_konteksts,
              "fakts_nakamais": S.aina_fakts_nakamais}
    n = len(ainas)
    seg_w = (S.W - 80 - (n - 1) * 10) / n
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
            # stāstu progresa josla: posms katrai ainai
            for i in range(n):
                x = 40 + i * (seg_w + 10)
                dd.rounded_rectangle([x, 44, x + seg_w, 54], radius=5, fill=(255, 255, 255, 60))
                pild = 1 if i < nr else (min(1, t / ilg) if i == nr else 0)
                if pild > 0:
                    dd.rounded_rectangle([x, 44, x + seg_w * pild, 54], radius=5, fill=(255, 255, 255, 240))
            p.stdin.write(kadrs.tobytes())
        t0 += ilg
    p.stdin.close()
    p.wait()
    if audio:
        ievades, filtri, sak = [], [], 0.0
        for i, ((f, _), a) in enumerate(zip(audio, ainas)):
            ievades += ["-i", f]
            ms = int((sak + 0.15) * 1000)
            filtri.append(f"[{i + 1}:a]adelay={ms}|{ms}[a{i}]")
            sak += a[2]
        filtri.append("".join(f"[a{i}]" for i in range(len(audio))) + f"amix=inputs={len(audio)}:normalize=0[aout]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video_tmp, *ievades, "-filter_complex", ";".join(filtri),
                        "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", izvade], check=True)
    else:
        shutil.move(video_tmp, izvade)
    shutil.rmtree(tmp, ignore_errors=True)
    return kopa, bool(audio)


def ieslegt():
    for k in ("fakts_konteksts", "karte", "fantasy", "fakts_hook", "outro", "intro"):
        _orig[k] = getattr(S, "aina_" + k)
    S.renderet = renderet
    if "--mape" not in sys.argv:
        mape = os.path.join(S.BASE, "video_test")
        sys.argv += ["--mape", mape]
        for f in (S.FAKTU_VESTURE, "tiesnesi_vesture.json"):          # testos vēsturi neņem vērā (salīdzināmi video)
            if os.path.exists(os.path.join(mape, f)):
                os.remove(os.path.join(mape, f))


if __name__ == "__main__":
    ieslegt()
    print(f"STILS {STILS}: STORY – video tiek saglabāts mapē video_test\\")
    sys.exit(S.main())
