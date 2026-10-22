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
  shorts_fons\\     īsi hokeja video (.mp4/.mov) no Pexels / Pixabay (bezmaksas, komerciāli drīkst).
                    Skripts katru pārvērš melnbaltu, palēnina (slow motion), izpludina, aptumšo un atkārto cilpā.
                    Iestatījumi faila augšā: FONA_MELNBALTS, FONA_ATRUMS (0.5 = 2× lēnāk), FONA_TUMSUMS.
  shorts_muzika\\   fona mūzika (.mp3) no YouTube Audio Library / Pixabay Music.
                    Skaļums ~15 %, kamēr runā balss – vēl klusāk; beigās izbalē.
  NOSAUKUMI – faila sākums nosaka, kuram video tas der (abās mapēs vienādi):
    speletaji_1.mp4, speletaji_2.mp4 (der arī komandas un vartsargi video), fantasy_1.mp4,
    fakts_1.mp4, tiesnesi_1.mp4,
    atskats_1.mp4 (visi atskati) vai precīzāk atskats_speletaji_1.mp4, atskats_fantasy_1.mp4 ...,
    visi_1.mp4 (vai jebkurš cits nosaukums) – der jebkuram veidam, kam nav savu failu.
  Ja veidam ir vairāki faili, tie tiek ņemti pēc kārtas (1, 2, 3, 1 ...); kārta saglabājas
  video\\shorts_mediji.json. Ja nav ne sava, ne visi_ faila – fons paliek krāsainais / bez mūzikas.
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
FONA_MELNBALTS = True           # fona video melnbalts (False = krāsains)
FONA_ATRUMS = 0.5               # fona video ātrums: 1 = normāls, 0.5 = 2× lēnāk (slow motion), 0.35 = ~3× lēnāk
# atsevišķs ātrums konkrētam video veidam: skaitlis (piem. 0.2 = 5× lēnāk) vai "auto" = tik lēni, lai fona klips
# vienreiz izstieptos pa visu video (8 s klips → 65 s video ≈ 8× lēnāk, bez atkārtošanās). Ļoti lēnam – kustības interpolācija.
FONA_ATRUMS_VEIDAM = {"tiesnesi": "auto"}
FONA_ATRUMS_MIN = 0.08          # "auto" ne lēnāk par ~12×
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


KARTE_KR = (15, 18, 40)          # kartīšu fons – PILNĪGI necaurspīdīgs: caurspīdīgā kartītē kustīgais fons
                                 # spīdēja cauri un video saspiešana to rādīja kā mirgojošus krāsainus kvadrātiņus


def jaukt(a, b, k):
    """Krāsa a un b sajaukumā (k = a daļa) – necaurspīdīga kontūra caurspīdīgas vietā."""
    return tuple(int(round(x * k + y * (1 - k))) for x, y in zip(a[:3], b[:3]))


def komandas_josla(d, x0, y0, x1, kom, h=22):
    """Viena josla kartītes augšā: kreisā puse – komandas primārā krāsa, labā – sekundārā (50/50)."""
    p = S.kkrasa(kom)
    s_ = SEKUNDARAS.get(str(kom), (230, 230, 235))
    if sum(abs(a - b) for a, b in zip(p, s_)) < 90:                   # pārāk līdzīgas → sekundārā = balta
        s_ = (230, 230, 235)
    mid = (x0 + x1) / 2
    d.rounded_rectangle([x0, y0, x1, y0 + h], radius=h / 2, fill=s_)
    d.rounded_rectangle([x0, y0, mid, y0 + h], radius=h / 2, fill=p)
    d.rectangle([mid - h / 2, y0, mid, y0 + h], fill=p)


def verdikts(d, t, t0, teksts, kr, apaksa, y, x0, x1):
    """Verdikts kā krāsaina "pill" poga + paskaidrojums zem tās (nepārklājas, ietilpst kartītē)."""
    k = S.ease((t - t0) / 0.35)
    if k <= 0:
        return
    kb = ease_back((t - t0) / 0.45)
    f = S.fonts("black", int(78 * (0.85 + 0.15 * kb)))
    bb = d.textbbox((0, 0), teksts, font=f)
    w, h = bb[2] - bb[0] + 110, 112
    px = (S.W - w) / 2
    d.rounded_rectangle([px, y, px + w, y + h], radius=h / 2, fill=S.ar_alfa(kr, 255 * k))
    d.text((px + 55 - bb[0], y + (h - (bb[3] - bb[1])) / 2 - bb[1]), teksts, font=f, fill=S.ar_alfa(S.uz_fona(kr), 255 * k))
    k2 = S.ease((t - t0 - 0.25) / 0.35)
    if k2 > 0 and apaksa:
        fa, rr = S.rindas_ietilpinat(d, apaksa, "semi", 40, x1 - x0 - 100, 2)
        yy = y + h + 22
        for r in rr:
            S.teksts_c(d, yy, r, fa, S.ar_alfa(S.BALTS, 225 * k2))
            yy += int(fa.size * 1.25)


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


def _ilgums(fails):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", fails],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return float(out)
    except Exception:                                                 # noqa: BLE001
        return None


def fona_atrums(fails, video_ilgums):
    """Fona ātrums šim video veidam (FONA_ATRUMS_VEIDAM), citādi FONA_ATRUMS."""
    v = FONA_ATRUMS_VEIDAM.get(_arg("--veids", "speletaji")) if not _arg("--atskats") else None
    if v is None:
        return FONA_ATRUMS
    if v == "auto":
        d = _ilgums(fails)
        if not d or not video_ilgums:
            return FONA_ATRUMS
        return float(min(FONA_ATRUMS, max(FONA_ATRUMS_MIN, d / video_ilgums)))
    return float(v)


class VideoFons:
    """Izpludināts hokeja video (B-roll) no shorts_fons\\, cilpā, aptumšots; virsū – vieglas krāsu blāzmas."""
    def __init__(self, fails, atrums=None):
        self.w, self.h = 360, 640
        atrums = FONA_ATRUMS if atrums is None else atrums
        if atrums < 0.3:                                              # super slow motion: kustības interpolācija (gludāk)
            lenam = (f"setpts=PTS/{atrums:.4f},minterpolate=fps={S.FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,")
        elif atrums < 0.99:                                           # slow motion ar kadru sapludināšanu
            lenam = f"setpts=PTS/{atrums:.4f},framerate=fps={S.FPS},"
        else:
            lenam = ""
        krasa = "hue=s=0," if FONA_MELNBALTS else "eq=saturation=0.8,"
        vf = (f"fps={S.FPS},scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h},"
              f"{lenam}{krasa}gblur=sigma=9,fps={S.FPS}")
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
        return Image.blend(im, bl, 0.25 if FONA_MELNBALTS else 0.35)

    def aizvert(self):
        try:
            self.p.kill()
        except Exception:                                             # noqa: BLE001
            pass


VEIDI_PREFIKSI = ("speletaji", "komandas", "vartsargi", "fantasy", "fakts", "tiesnesi", "atskats", "visi")
MEDIJU_VESTURE = "shorts_mediji.json"
XG_VEIDI = ("speletaji", "komandas", "vartsargi")      # xG video – izmanto speletaji_ failus (ja nav savu komandas_ / vartsargi_)


def _arg(nos, nokl=None):
    return sys.argv[sys.argv.index(nos) + 1] if nos in sys.argv and sys.argv.index(nos) + 1 < len(sys.argv) else nokl


def veida_atslegas():
    """Kuri failu nosaukumu sākumi der šim video, svarīgākais pirmais.
    Piem. xG atskats par spēlētājiem: ['atskats_speletaji', 'atskats', 'visi']."""
    ats = _arg("--atskats")
    if ats:
        veids = ""
        try:
            import json
            js = ats
            if os.path.isdir(ats):
                js = os.path.join(ats, sorted(f for f in os.listdir(ats) if f.endswith(".json"))[0])
            veids = json.load(open(js, encoding="utf-8")).get("veids", "")
        except Exception:                                             # noqa: BLE001
            pass
        a_ = [f"atskats_{veids}"] if veids else []
        if veids in XG_VEIDI and veids != "speletaji":
            a_.append("atskats_speletaji")
        return a_ + ["atskats", "visi"]
    veids = _arg("--veids", "speletaji")
    if veids in XG_VEIDI and veids != "speletaji":                  # komandas / vartsargi → kā spēlētājiem
        return [veids, "speletaji", "visi"]
    return [veids, "visi"]


def izveleties_mediju(mape, paplasinajumi, tips):
    """Fails no mapes pēc video veida: speletaji_1.mp4, speletaji_2.mp4, fantasy_1.mp3 ...
    Ja šim veidam nav neviena faila – visi_*.  Faili tiek ņemti pēc kārtas (1, 2, 3, 1, 2 ...),
    lai blakus video nav vienādi; kārta tiek atcerēta video\\shorts_mediji.json."""
    if not os.path.isdir(mape):
        return None
    visi = sorted(f for f in os.listdir(mape) if f.lower().endswith(paplasinajumi))
    for atsl in veida_atslegas():
        faili = [f for f in visi if f.lower().startswith(atsl + "_") or os.path.splitext(f.lower())[0] == atsl]
        if atsl == "visi":                                            # + faili bez veida priedēkļa
            faili += [f for f in visi if not f.lower().startswith(VEIDI_PREFIKSI)]
        if faili:
            break
    else:
        return None
    import json
    vm = _arg("--mape", os.path.join(S.BASE, "video"))
    vp = os.path.join(vm, MEDIJU_VESTURE)
    try:
        vest = json.load(open(vp, encoding="utf-8")) if os.path.exists(vp) else {}
    except Exception:                                                 # noqa: BLE001
        vest = {}
    k = f"{tips}:{atsl}"
    ped = vest.get(k)
    izv = faili[(faili.index(ped) + 1) % len(faili)] if ped in faili else faili[0]
    vest[k] = izv
    try:
        os.makedirs(vm, exist_ok=True)
        json.dump(vest, open(vp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:                                                 # noqa: BLE001
        pass
    return os.path.join(mape, izv)


def izveleties_fonu():
    return izveleties_mediju(MAPE_FONS, VIDEO_PAPL, "fons") if OPC["fons"] else None


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
            ev.append((t0, "boom", 0.9))
            if veids == "intro":
                ev.append((t0 + 0.5, "tick", 0.9))
        if tips == "fakts_hook":
            ev.append((t0 + 1.0, "tick", 0.9))
        elif tips == "intro":
            ev.append((t0 + 1.0, "tick", 0.9))
        elif tips == "fakts_mini":
            ev += [(t0 + 0.9, "boom", 0.8)] + [(t0 + 1.3 + 0.15 * j, "tick", 0.6) for j in range(len(c.get("stat_rindas", [])))]
        elif tips == "fakts_konteksts":
            ev.append((t0 + 0.9, "boom", 1.0))
        elif tips == "fantasy":
            ev += [(t0 + 0.3 + 0.08 * i, "tick", 0.6) for i in range(len(c.get("flizes", [])))]
            ev.append((t0 + 1.45, "boom", 0.8))
        elif tips == "fakts_saraksts":
            rindas = c["rindas"][-9:]
            n = len(rindas)
            reit = _ir_reitings(rindas) and not c.get("nav_reitings")
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
    return izveleties_mediju(MAPE_MUZIKA, AUDIO_PAPL, "muzika") if OPC["muzika"] else None


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
    if k > 0.02 and not c.get("bez_uzlimes"):
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


# ================================================================ ĀĶIS (cold open) – pirmās 2 sekundes
def _izpludinats_teksts(txt, f, kr, blur=24):
    """Teksts, kas ir pa pusei izlasāms – "kas tas ir?" efekts."""
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    bb = d0.textbbox((0, 0), txt, font=f)
    w, h = bb[2] - bb[0] + 80, bb[3] - bb[1] + 80
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((40 - bb[0], 40 - bb[1]), txt, font=f, fill=kr)
    return im.filter(ImageFilter.GaussianBlur(blur))


def aina_aki(t, s):
    """Pirmais kadrs uzreiz pilns: skaitlis/apgalvojums + noslēpumaina #1 kartīte ar izpludinātu vārdu."""
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S.pill(d, 0, 250, s["tag"], S.fonts("semi", 40), S.ZILS, S.MELNS, center=True)
    y = 380
    for i, (rinda, kr) in enumerate(s["rindas"]):
        f = S.ietilpinat(d, rinda, "black", 140, S.W - 100)
        S.teksts_c(d, y, rinda, f, kr)
        y += int(f.size * 1.12)
    if s.get("kartite"):
        kt = s["kartite"]
        x0, x1, y0 = 120, S.W - 120, max(y + 40, 760)
        y1 = y0 + 560
        d.rounded_rectangle([x0, y0, x1, y1], radius=44, fill=KARTE_KR, outline=jaukt(kt["akc"], KARTE_KR, 0.55), width=3)
        nr = kt.get("nr", "#1")                                       # bez komandas krāsām/zīmītes – neko neizpaužam
        S.teksts_c(d, y0 + 26, nr, S.fonts("black", 120), kt["akc"])
        vards = _izpludinats_teksts(kt["vards"], S.ietilpinat(d, kt["vards"], "black", 110, x1 - x0 - 100), S.BALTS)
        im.alpha_composite(vards, (int((S.W - vards.width) / 2), int(y0 + 165)))
        f_sk = S.ietilpinat(d, kt["skaitlis"], "black", 150, x1 - x0 - 80)
        S.teksts_c(d, y0 + 320, kt["skaitlis"], f_sk, kt["akc"])
        if kt.get("apaksa"):
            S.teksts_c(d, y1 - 66, kt["apaksa"], S.ietilpinat(d, kt["apaksa"], "semi", 38, x1 - x0 - 80), S.PELEKS)
        y_st = y1 + 60
    else:
        sk_ = s.get("skaitlis", "")
        f_sk = S.ietilpinat(d, sk_, "black", 260, S.W - 120)
        S.teksts_c(d, y + 40, sk_, f_sk, s.get("skaitlis_kr", S.DZELTENS))
        y_st = y + 40 + int(f_sk.size * 1.15)
        if s.get("skaitlis_apaksa"):
            S.teksts_c(d, y_st, s["skaitlis_apaksa"], S.ietilpinat(d, s["skaitlis_apaksa"], "semi", 48, S.W - 140), S.PELEKS)
            y_st += 110
    if t > 0.5:                                                       # uzlīme "palieciet līdz beigām"
        kb = ease_back((t - 0.5) / 0.4)
        st = Image.new("RGBA", (S.W, 240), (0, 0, 0, 0))
        uzlime(st, s.get("uzlime", "STAY FOR #1"), 20, -5, S.DZELTENS)
        if kb < 0.999:
            sc = max(0.05, kb)
            st = st.resize((int(S.W * sc), int(240 * sc)), Image.BILINEAR)
        im.alpha_composite(st, (int((S.W - st.width) / 2), int(min(y_st, 1460))))
    return im


def _parsk(v):
    try:
        return float(str(v).replace("−", "-").replace("PDO", "").strip())
    except ValueError:
        return None


def pievienot_aki(s, veids):
    """Pārveido video scenāriju: āķis sākumā, #3 → #1 secība, cilpa beigās. Dati un kartītes – tie paši."""
    if not s or not s.get("kartes"):
        return s
    k, r = s["kartes"], s["runa"]
    if veids in ("speletaji", "komandas", "vartsargi"):
        n = len(k) // 2
        laim_k, nelaim_k = k[:n], k[n:]
        r_l, r_n = r[1:1 + n], r[1 + n:-1]
        # āķa varonis: laimīgais #1 vai nelaimīgais #1 – populārākais (ESPN rostered %) × ekstrēmākais
        mz = s.get("momentuzn", {})
        pid_l = next(iter(mz.get("laim", {})), None)
        pid_n = next(iter(mz.get("nelaim", {})), None)
        e_ = None
        if veids != "komandas":
            try:
                e_, _ = S.espn_dati()
            except Exception:                                         # noqa: BLE001
                e_ = None

        def ekstr(c_, pid):
            if veids == "komandas":
                return abs((_parsk(c_["liels"]) or 100) - 100)
            return abs(_parsk(c_["liels"]) or 0)

        def popul(pid):
            if e_ is None or pid is None:
                return None
            try:
                v_ = float(e_["rostered"].get(int(float(pid))))
                return v_ / 100 if v_ == v_ else 0.0
            except (TypeError, ValueError):
                return 0.0
        ex_l, ex_n = ekstr(laim_k[0], pid_l), ekstr(nelaim_k[0], pid_n)
        mx = max(ex_l, ex_n, 1e-6)
        p_l, p_n = popul(pid_l), popul(pid_n)
        if p_l is None or p_n is None:                                # komandas / nav ESPN datu → ekstrēmākais
            punkti_l, punkti_n = ex_l / mx, ex_n / mx
        else:
            punkti_l, punkti_n = (0.25 + p_l) * ex_l / mx, (0.25 + p_n) * ex_n / mx
        laim_varonis = punkti_l >= punkti_n
        hero = laim_k[0] if laim_varonis else nelaim_k[0]
        print(f"ĀĶIS: {'laimīgais' if laim_varonis else 'nelaimīgais'} #1 – {hero.get('v1', '')} {hero.get('v2', '')}".strip()
              + f"  (punkti {punkti_l:.2f} pret {punkti_n:.2f})")
        # secība: otra grupa #3 → #1, tad varoņa grupa #3 → #1 (noslēptais #1 atklājas pašās beigās)
        if laim_varonis:
            s["kartes"] = nelaim_k[::-1] + laim_k[::-1]
            r_k = r_n[::-1] + r_l[::-1]
        else:
            s["kartes"] = laim_k[::-1] + nelaim_k[::-1]
            r_k = r_l[::-1] + r_n[::-1]
        tag = s["intro"]["tag"]
        if veids == "speletaji":
            G, xG = hero["bars"][0][1], hero["bars"][1][1]
            vv = "GOAL" if int(G) == 1 else "GOALS"
            rindas = [(f"{int(G)} {vv}.", S.BALTS), (f"SHOULD HAVE {xG:.1f}.", S.DZELTENS)]
            sk_ = hero["liels"]
            ap = "goals above expected" if laim_varonis else "goals below expected"
            runa0 = f"{int(G)} {vv.lower()}. He should have {xG:.1f}. Who is it?"
            beigas = (f"Luck runs out. Expected goals don't. {S.atskata_teksts()} "
                      f"Follow, and remember: {int(G)} {vv.lower()}.")
        elif veids == "vartsargi":
            GA, xGA = hero["bars"][0][1], hero["bars"][1][1]
            gs = abs(_parsk(hero["liels"]) or 0)
            rindas = [("HE'S STEALING" if laim_varonis else "HE'S COSTING", S.BALTS), ("GAMES.", S.DZELTENS)]
            sk_, ap = hero["liels"], f"{int(GA)} goals allowed on {xGA:.1f} expected"
            runa0 = (f"This goalie is stealing games: {gs:.1f} goals saved above expected. Who is it?" if laim_varonis
                     else f"This goalie is costing his team: {gs:.1f} goals worse than expected. Who is it?")
            beigas = (f"Hot streaks cool, cold streaks thaw. {S.atskata_teksts()} Follow, and remember: this goalie is "
                      + ("stealing games." if laim_varonis else "costing games."))
        else:
            import re as _re
            m_ = _re.search(r"(\d+)-(\d+)-(\d+)", hero.get("info", ""))
            rek = f"{m_.group(1)}–{m_.group(2)}–{m_.group(3)}" if m_ else ""
            rindas = ([(f"{rek}.", S.BALTS)] if rek else []) + [("AND IT'S LUCK." if laim_varonis else "AND IT'S BAD LUCK.", S.DZELTENS)]
            sk_, ap = hero["liels"], "PDO · league average ≈ 100"
            if laim_varonis:
                runa0 = (f"This team is {m_.group(1)} and {m_.group(2)}. And it's mostly luck. Who is it?" if m_
                         else "This team is winning on luck. Who is it?")
                beig_ = "this team is winning on luck."
            else:
                runa0 = (f"This team is {m_.group(1)} and {m_.group(2)}. But they're better than that. Who is it?" if m_
                         else "This team is better than its record. Who is it?")
                beig_ = "this team is better than its record."
            beigas = f"PDO always comes back to one hundred. {S.atskata_teksts()} Follow, and remember: {beig_}"
        vards = (hero.get("v2") or "").upper()
        s["intro"] = {"aki": True, "tag": tag, "rindas": rindas, "ilgums": 2.4,
                      "kartite": {"nr": "#1", "akc": hero["akc"], "badge": hero.get("badge"), "vards": vards,
                                  "skaitlis": sk_, "apaksa": ap},
                      "uzlime": "STAY FOR #1"}
        s["runa"] = [runa0] + r_k + [beigas]
    elif veids == "atskats":
        rez = ""
        for txt, _ in s["outro"]["rindas"]:
            if txt.startswith("WENT "):
                rez = txt[5:].rstrip(".")
        ok, _, kopa = rez.partition("/")
        datums = s["intro"]["apaksa"][0].replace("Our list from ", "")
        trapi = ok.isdigit() and kopa.isdigit() and int(kopa) and int(ok) / int(kopa) >= 0.5
        neskait = sum(1 for c_ in k if c_.get("akc") == S.NEITRALS)
        s["intro"] = {"aki": True, "tag": s["intro"]["tag"], "ilgums": 2.4,
                      "rindas": [(f"ON {datums.upper()}", S.BALTS), ("WE MADE A CALL.", S.DZELTENS)],
                      "skaitlis": f"{rez}", "skaitlis_kr": S.ZALS if trapi else S.SARKANS,
                      "skaitlis_apaksa": "calls that held up" + (f"  ·  {neskait} not counted (too few games)" if neskait else ""),
                      "uzlime": "SEE EVERY CALL"}
        vardi = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
        nesk_runa = ""
        if neskait:
            nesk_runa = (f" {vardi.get(neskait, neskait)} {'call was' if neskait == 1 else 'calls were'} not counted:"
                         f" too few games since.")
        r[0] = (f"On {datums} we made a call. We got {ok} out of {kopa} right.{nesk_runa} Here's every one."
                if rez else r[0])
        r[-1] = r[-1].replace("Follow for weekly NHL stats.", "Follow for the next call. Remember:")
    elif veids == "tiesnesi":
        c0 = k[0]
        stingr = next((c for c in k if "STRICTEST" in str(c.get("saraksts_virs", ""))), None)
        try:
            top = float(stingr["rindas"][0][2])
            vid = float(str(stingr["kopsavilkums"]).split(":")[1].split()[0])
            pct = round((top / vid - 1) * 100)
        except Exception:                                             # noqa: BLE001
            pct = None
        if pct:
            men = c0["hook"][0]
            c0["hook"] = ["THIS REF CALLS", f"+{pct}% MORE", "PENALTIES"]
            c0["v1"], c0["vards"] = f"{men} REFEREE REPORT", "WHO IS IT?"
            r[0] = f"One NHL referee calls {pct} percent more penalties than average. Who is it? {men.capitalize()} referee report."
            r[-1] = r[-1].rstrip() + " Remember:"
    return s


# ================================================================ NEDĒĻAS FAKTI (1–5 faktu vienā video)
FAKTI_PAPILDU = {}     # papildu fakti vēsturei (pieraksta pēc main(), kad zināma mape)


def _toi_min(x):
    try:
        mm, ss = str(x).split(":")
        return int(mm) + int(ss) / 60
    except ValueError:
        return 0.0


def fakta_statistika(D, c):
    """Papildu statistika par faktu: spēlētāja / vārtsarga / komandas sezona vai spēles protokols.
    → (virsraksts, rindas[(nos, "", vērtība)], kopsavilkums, balss teikums) vai None."""
    np, pd = S.np, S.pd
    atsl = str(c.get("atsl", ""))
    veids, _, rest = atsl.partition(":")
    dal = rest.split(":")
    sg = D["sg"]
    try:
        if veids in ("points_serija", "goals_serija", "liela"):
            pid = float(dal[0])
            x = D["sp"][D["sp"]["playerId"] == pid]
            if x.empty:
                return None
            GP, G, A = x["game_id"].nunique(), int(x["goals"].sum()), int(x["assists"].sum())
            P, SOG = int(x["points"].sum()), int(pd.to_numeric(x["sog"], errors="coerce").fillna(0).sum())
            PPG = int(pd.to_numeric(x["powerPlayGoals"], errors="coerce").fillna(0).sum())
            pm = int(pd.to_numeric(x["plusMinus"], errors="coerce").fillna(0).sum())
            toi = x["toi"].map(_toi_min).mean()
            rindas = [("Games played", "", f"{GP}"), ("Goals", "", f"{G}"), ("Assists", "", f"{A}"), ("Points", "", f"{P}"),
                      ("Shots on goal", "", f"{SOG}"), ("Power-play goals", "", f"{PPG}"),
                      ("Plus / minus", "", f"{pm:+d}".replace("-", "−")), ("Ice time / game", "", f"{int(toi)}:{int(round((toi % 1) * 60)) % 60:02d}")]
            return ("SEASON SO FAR", rindas, f"{P / max(GP, 1):.2f} POINTS PER GAME",
                    f"On the season: {G} goals and {A} assists in {GP} games.")
        if veids == "vartsargs":
            pid = float(dal[0])
            x = D["vg"][pd.to_numeric(D["vg"]["playerId"], errors="coerce") == pid]
            x = x[x["toi"].map(_toi_min) > 0]
            if x.empty:
                return None
            GP = x["game_id"].nunique()
            W = int((x["decision"].astype(str) == "W").sum())
            L = int((x["decision"].astype(str) == "L").sum())
            O = int((x["decision"].astype(str) == "O").sum())
            SA, SV = pd.to_numeric(x["shotsAgainst"]).sum(), pd.to_numeric(x["saves"]).sum()
            GA = pd.to_numeric(x["goalsAgainst"]).sum()
            mins = x["toi"].map(_toi_min).sum()
            SO = int(((pd.to_numeric(x["goalsAgainst"]) == 0) & (x["starter"].astype(str) == "True")).sum())
            svp = SV / SA if SA else 0
            rindas = [("Games played", "", f"{GP}"), ("Record", "", f"{W}-{L}-{O}"), ("Save %", "", f".{round(svp * 1000):03d}"),
                      ("Goals against avg", "", f"{GA / mins * 60:.2f}" if mins else "–"), ("Shutouts", "", f"{SO}"),
                      ("Shots faced", "", f"{int(SA)}")]
            return ("SEASON SO FAR", rindas, f"{int(SV)} SAVES THIS SEASON",
                    f"On the season: {W} win{'' if W == 1 else 's'} and a .{round(svp * 1000):03d} save percentage.")
        if veids in ("kom_uzv", "kom_zaud"):
            kom = dal[0]
            x = sg[(sg["home_team"] == kom) | (sg["away_team"] == kom)].sort_values("datums")
            if x.empty:
                return None
            W = int((x["uzvaretajs"] == kom).sum())
            OT = int(((x["uzvaretajs"] != kom) & (x["spele_beidzas"].astype(str) != "REG")).sum())
            L = len(x) - W - OT
            GF = int(np.where(x["home_team"] == kom, x["home_total"], x["away_total"]).sum())
            GA = int(np.where(x["home_team"] == kom, x["away_total"], x["home_total"]).sum())
            ppg = pd.to_numeric(np.where(x["home_team"] == kom, x["home_ppg"], x["away_ppg"]), errors="coerce")
            ppo = pd.to_numeric(np.where(x["home_team"] == kom, x["home_pp_opp"], x["away_pp_opp"]), errors="coerce")
            pp = f"{np.nansum(ppg) / np.nansum(ppo) * 100:.0f}%" if np.nansum(ppo) else "–"
            pec5 = "".join("W" if u == kom else ("O" if b != "REG" else "L")
                           for u, b in zip(x["uzvaretajs"].tail(5), x["spele_beidzas"].astype(str).tail(5)))
            rindas = [("Record", "", f"{W}-{L}-{OT}"), ("Points", "", f"{2 * W + OT}"), ("Goals for", "", f"{GF}"),
                      ("Goals against", "", f"{GA}"), ("Goal difference", "", f"{GF - GA:+d}".replace("-", "−")),
                      ("Power play", "", pp), ("Last 5", "", " ".join(pec5))]
            return ("SEASON SO FAR", rindas, f"{2 * W + OT} POINTS IN {len(x)} GAMES",
                    f"The {S.kom_nos(kom)} have {W} win{'' if W == 1 else 's'}, {L} regulation loss{'' if L == 1 else 'es'} "
                    f"and {OT} overtime loss{'' if OT == 1 else 'es'} this season.")
        if veids in ("comeback", "periods", "atri", "metieni"):
            gid = dal[0]
            x = sg[sg["game_id"].astype(str) == str(gid)]
            if x.empty:
                return None
            r = x.iloc[0]
            h, a_ = r["home_team"], r["away_team"]

            def pr(kh, ka, fmt="{:.0f}"):
                try:
                    return (fmt.format(float(r[ka])), fmt.format(float(r[kh])))
                except (TypeError, ValueError):
                    return ("–", "–")
            rindas = [("", a_, h)]
            for nos, kh, ka in (("Shots", "home_sog_total", "away_sog_total"), ("Hits", "home_hits", "away_hits"),
                                ("Blocked shots", "home_blocked_shots", "away_blocked_shots"),
                                ("Penalty minutes", "home_pim_total", "away_pim_total"), ("Giveaways", "home_giveaways", "away_giveaways")):
                av, hv = pr(kh, ka)
                rindas.append((nos, av, hv))
            try:
                rindas.insert(2, ("Power play", f"{int(r['away_ppg'])}/{int(r['away_pp_opp'])}", f"{int(r['home_ppg'])}/{int(r['home_pp_opp'])}"))
            except (TypeError, ValueError):
                pass
            gal = f"FINAL: {a_} {int(r['away_total'])} – {int(r['home_total'])} {h}" + ("" if str(r["spele_beidzas"]) == "REG" else f" {r['spele_beidzas']}")
            return ("BOX SCORE", rindas, gal,
                    f"Shots were {int(r['away_sog_total'])} to {int(r['home_sog_total'])}.")
    except Exception:                                                 # noqa: BLE001
        return None
    return None


def aina_fakts_mini(t, c):
    """Viens fakts vienā ainā: virsraksts, vārds + komanda, liels skaitlis, konteksts un 3 statistikas rindas."""
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S.pill(d, 0, 236, f"#{c['nr']}", S.fonts("black", 56), S.DZELTENS, S.MELNS, pad=(40, 10), center=True)
    y = 360
    hook = c["hook"]
    for i, r_ in enumerate(hook):
        k = S.ease((t - 0.06 * i) / 0.35)
        f = S.ietilpinat(d, r_, "black", 104, S.W - 100)
        S.teksts_c(d, y + (1 - k) * 30, r_, f, S.ar_alfa(S.DZELTENS if i == len(hook) - 1 else S.BALTS, 255 * k))
        y += int(f.size * 1.1)
    x0, x1, y0 = 80, S.W - 80, y + 40
    rindas = c.get("stat_rindas", [])[:3]
    y1 = y0 + 520 + 64 * len(rindas)
    prim, _ = kom_krasas(c.get("badge"))
    k0 = S.ease((t - 0.25) / 0.35)
    if k0 > 0:
        d.rounded_rectangle([x0, y0, x1, y1], radius=44, fill=KARTE_KR, outline=jaukt(prim, KARTE_KR, 0.6), width=3)
        if c.get("badge"):
            komandas_josla(d, x0 + 40, y0 + 24, x1 - 40, c["badge"], h=12)
            fb = S.fonts("bold", 44)
            S.pill(d, x1 - 44 - S.platums(d, c["badge"], fb) - 60, y0 + 56, c["badge"], fb, S.kkrasa(c["badge"]),
                   S.uz_fona(S.kkrasa(c["badge"])), pad=(30, 10))
        if c.get("v1"):
            d.text((x0 + 44, y0 + 60), c["v1"].upper(), font=S.fonts("semi", 44), fill=prim)
        vn = c["vards"].upper()
        d.text((x0 + 44, y0 + 112), vn, font=S.ietilpinat(d, vn, "black", 96, x1 - x0 - 90), fill=S.BALTS)
        k1 = S.ease((t - 0.6) / 0.3)
        if k1 > 0:
            sk_ = skaitit(c["k_skaitlis"], S.ease((t - 0.6) / 0.6))
            f = S.ietilpinat(d, c["k_skaitlis"], "black", 150, x1 - x0 - 80)
            S.teksts_c(d, y0 + 225, sk_, f, S.ar_alfa(S.DZELTENS, 255 * k1))
            fk, rr = S.rindas_ietilpinat(d, c["konteksts"][0], "bold", 40, x1 - x0 - 90, 2)
            yy = y0 + 400
            for r_ in rr:
                S.teksts_c(d, yy, r_, fk, S.ar_alfa(S.BALTS, 235 * k1))
                yy += int(fk.size * 1.2)
        for j, (a_, b_, v_) in enumerate(rindas):
            kj = S.ease((t - 1.3 - 0.15 * j) / 0.3)
            if kj <= 0:
                continue
            yy = y0 + 510 + 64 * j
            d.line([(x0 + 40, yy - 8), (x1 - 40, yy - 8)], fill=(40, 46, 70), width=2)
            d.text((x0 + 44, yy), str(a_), font=S.fonts("semi", 38), fill=S.ar_alfa(S.PELEKS, 255 * kj))
            fv = S.fonts("black", 42)
            v_ = f"{b_}  –  {v_}" if b_ else str(v_)                    # protokolam: viesi – mājinieki
            d.text((x1 - 44 - S.platums(d, v_, fv), yy - 4), v_, font=fv, fill=S.ar_alfa(S.BALTS, 255 * kj))
    return im


def _fakti_izvele(arg, kand):
    """--fakts 3 | 1,3,5 | top3 | auto  → kandidātu saraksts (max 5), sakārtots pēc vērtējuma (augstākais pirmais)."""
    arg = str(arg or "auto").strip().lower()
    if arg in ("auto", ""):
        idx = [0]
    elif arg.startswith("top"):
        n = int(arg[3:] or 5)
        idx = list(range(min(max(1, n), 5)))
    else:
        idx = []
        for x in arg.replace(" ", "").split(","):
            if x.isdigit() and 1 <= int(x) <= len(kand) and int(x) - 1 not in idx:
                idx.append(int(x) - 1)
        idx = idx[:5]
    izv = [kand[i] for i in idx if i < len(kand)]
    return sorted(izv, key=lambda c: -c["vert"])


def veids_fakti_b(m, a):
    D = S.fakti_dati(a.lidz)
    kand = S.fakti_kandidati(D, a.mape)
    if not kand:
        print("Šonedēļ nav atrasts neviens fakts.")
        return None
    if a.fakts is None:
        S.fakti_saraksts(kand)
        print("\n(--fakts nav norādīts → izmantoju #1. Vairāki: --fakts 1,3,5 vai --fakts top5)")
    izv = _fakti_izvele(a.fakts, kand)
    if not izv:
        S.fakti_saraksts(kand)
        print(f"\nNav faktu ar numuru {a.fakts}. Piem.: --fakts 3  vai  --fakts 1,4,6  vai  --fakts top5")
        return None
    n = len(izv)
    hero, citi = izv[0], izv[1:]
    lidz = D["lidz"]
    kartes, runa = [], []
    # āķis
    hook_runa = " ".join(hero["hook"]).lower().capitalize()
    tag = f"NHL  ·  {n} FACTS OF THE WEEK" if n > 1 else "NHL  ·  FACT OF THE WEEK"
    intro = {"aki": True, "tag": tag, "ilgums": 2.6,
             "rindas": [(r_, S.DZELTENS if i == len(hero["hook"]) - 1 else S.BALTS) for i, r_ in enumerate(hero["hook"])],
             "kartite": {"nr": "#1", "akc": S.DZELTENS, "badge": None, "vards": str(hero["vards"]).upper(),
                         "skaitlis": str(hero.get("k_skaitlis") or hero.get("skaitlis")), "apaksa": hero.get("skaitlis_apaksa", "")},
             "uzlime": "STAY FOR #1" if n > 1 else "WHO IS IT?"}
    runa.append((f"{n} wild NHL facts from this week. Number one: {hook_runa}. Who is it?" if n > 1
                 else f"{hook_runa}. Who is it?"))
    # #n → #2: viena aina katram
    for nr, c in zip(range(n, 1, -1), citi[::-1]):
        st = fakta_statistika(D, c)
        kartes.append({"tips": "fakts_mini", "ilgums": 5.0, **c, "nr": nr,
                       "stat_rindas": [r_ for r_ in (st[1] if st else c["rindas"]) if r_[0]][:3]})
        runa.append(f"Number {nr}. {c['runa'][0]} {c['runa'][2]}".replace("  ", " "))
    # #1 – pilnais stāsts
    st = fakta_statistika(D, hero)
    kopa = {"pill_hook": "#1  ·  FACT OF THE WEEK" if n > 1 else "NHL  ·  FACT OF THE WEEK", "bez_uzlimes": True}
    kartes.append({"tips": "fakts_hook", "ilgums": 3.2, **hero, **kopa})
    runa.append(("Number one. " if n > 1 else "") + hero["runa"][0])
    kartes.append({"tips": "fakts_saraksts", "ilgums": 2.6 + 0.22 * min(9, len(hero["rindas"])), **hero})
    runa.append(hero["runa"][1])
    if st:
        kartes.append({"tips": "fakts_saraksts", "ilgums": 3.6, **hero, "saraksts_virs": st[0], "rindas": st[1],
                       "kopsavilkums": st[2], "pill_kr": S.ZILS, "vards_w": 420 if st[0] != "BOX SCORE" else 330,
                       "vards_kr": S.BALTS})
        runa.append(st[3])
    kartes.append({"tips": "fakts_konteksts", "ilgums": 4.0, **hero, "pill_k": "HOW RARE IS IT?"})
    runa.append(hero["runa"][2])
    if hero.get("nakamais"):
        kartes.append({"tips": "fakts_nakamais", "ilgums": 3.6, **hero})
        runa.append(hero["runa"][3])
    if n > 1:
        outro = {"rindas": [("WHICH ONE", S.BALTS), ("SURPRISED YOU?", S.DZELTENS)],
                 "info": [f"Stats through {S.dat(lidz, True)}", "History: our database since 2023-24"],
                 "follow": "FOLLOW FOR WEEKLY NHL FACTS", "komentars": f"COMMENT 1–{n}",
                 "komentars2": "Which fact surprised you most?"}
        runa.append("Which one surprised you most? Comment the number. Follow for weekly NHL facts, and remember:")
    else:
        outro = {"rindas": [("NHL FACT", S.BALTS), ("OF THE WEEK.", S.DZELTENS)],
                 "info": [f"Stats through {S.dat(lidz, True)}", "History: our database since 2023-24"],
                 "follow": "FOLLOW FOR WEEKLY NHL FACTS"}
        runa.append("Follow for weekly NHL facts, and remember:")
    FAKTI_PAPILDU["fakti"] = [{"atsl": c["atsl"], "garums": c["garums"], "teksts": c["teksts"]} for c in citi]
    return {
        "intro": intro, "kartes": kartes, "outro": outro,
        "zimogs": f"STATS THROUGH {S.dat(lidz, True).upper()}", "runa": runa, "lidz": lidz,
        "periods": f"through {S.dat(lidz, True)}",
        "virsraksts": hero["yt"] + (f" + {n - 1} more wild NHL facts" if n > 1 else ""),
        "saraksts": [f"#{i + 1}  {c['teksts']}" for i, c in enumerate(izv)],
        "apraksts": " ".join(x for x in hero["runa"] if x),
        "piezime": "History: our database since 2023-24.",
        "tagi": "#NHL #hockey #NHLstats #NHLfacts #Shorts",
        "nosaukums": f"fakti_{lidz}" if n > 1 else f"fakts_{lidz}",
        "thumb": {"tag": "NHL  ·  FACT OF THE WEEK" if n == 1 else f"NHL  ·  {n} FACTS OF THE WEEK",
                  "hook": hero.get("th_hook") or hero["hook"][:2], "vards": hero["vards"], "badge": hero["badge"],
                  "skaitlis": hero["skaitlis"], "kr": S.DZELTENS if hero["aktiva"] else S.ZALS,
                  "apaksa": hero["skaitlis_apaksa"], "datums": lidz},
        "fakts_atsl": {"atsl": hero["atsl"], "garums": hero["garums"],
                       "teksts": hero["teksts"] + (f"  (+ {n - 1} citi: " + "; ".join(c["teksts"] for c in citi) + ")" if citi else "")},
    }


def pierakstit_papildu_faktus(mape_video):
    """main() pieraksta vēsturē tikai galveno faktu – pārējos pievienojam ar to pašu video mapi."""
    citi = FAKTI_PAPILDU.get("fakti")
    if not citi:
        return
    import json
    p_ = os.path.join(mape_video, S.FAKTU_VESTURE)
    if not os.path.exists(p_):
        return
    vest = json.load(open(p_, encoding="utf-8"))
    if not vest:
        return
    ped = vest[-1]
    for c in citi:
        vest.append({**c, "datums": ped.get("datums"), "mape": ped.get("mape")})
    json.dump(vest, open(p_, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def aina_intro(t, s):
    if s.get("aki"):
        return aina_aki(t, s)
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
    d.rounded_rectangle([x0, y0, x1, y0 + 40 + rh * max(1, n)], radius=40, fill=KARTE_KR, outline=(52, 58, 84), width=3)
    solis = 0.2
    reit = _ir_reitings(rindas) and not c.get("nav_reitings")        # reitings → atklāj no apakšas, #1 izgaismo
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
    x0, y0, x1 = 70, 380, W - 70
    # apakšas izkārtojums: lielais skaitlis un paskaidrojums – pozīcijas no reālā teksta izmēra (der jebkuram fontam)
    yb = y0 + 560
    y_sk = yb + 190 * (max(1, len(c["bars"])) - 1) + 142 + 46
    f_sk = S.ietilpinat(d, c["liels"], "black", min(170, c.get("liels_izm", 200)), x1 - x0 - 100)
    bb = d.textbbox((0, 0), c["liels"], font=f_sk)
    f_ap, rr_ap = S.rindas_ietilpinat(d, c["apaksa"], "semi", 40, x1 - x0 - 100, 2)
    y_ap = y_sk + bb[3] + 30
    y1 = max(1640, y_ap + len(rr_ap) * int(f_ap.size * 1.25) + 36)
    d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=KARTE_KR, outline=jaukt(prim, KARTE_KR, 0.6), width=3)
    komandas_josla(d, x0 + 44, y0 + 26, x1 - 44, c.get("badge"), h=12)
    d.text((x0 + 50, y0 + 60), f"#{c['nr']}", font=S.fonts("black", 92), fill=akc)
    fb = S.fonts("bold", 48)
    S.pill(d, x1 - 50 - S.platums(d, c["badge"], fb) - 68, y0 + 80, c["badge"], fb, c["bkr"], S.uz_fona(c["bkr"]), pad=(34, 14))
    d.text((x0 + 50, y0 + 210), c["v1"].upper(), font=S.fonts("semi", 54), fill=prim)
    f2 = S.ietilpinat(d, c["v2"].upper(), "black", 120, x1 - x0 - 100)
    d.text((x0 + 50, y0 + 275), c["v2"].upper(), font=f2, fill=S.BALTS)
    d.text((x0 + 50, y0 + 425), c["info"], font=S.ietilpinat(d, c["info"], "reg", 44, x1 - x0 - 100), fill=S.PELEKS)
    k = S.ease((t - 0.35) / 0.9)
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
    k2 = S.ease((t - 1.2) / 0.2)                                     # ātra parādīšanās (bez ilgas caurspīdības)
    if k2 > 0:
        liels = skaitit(c["liels"], S.ease((t - 1.2) / 0.9))
        S.teksts_c(d, y_sk, liels, f_sk, S.ar_alfa(akc, 255 * k2))
        k3 = S.ease((t - 1.5) / 0.3)
        yy = y_ap
        for r in rr_ap:
            S.teksts_c(d, yy, r, f_ap, S.ar_alfa(S.BALTS, 215 * k3))
            yy += int(f_ap.size * 1.25)
    return im


def aina_fantasy(t, c):
    """Fantasy kartīte: komandas josla augšā (50/50), flīžu skaitļi skaitās, verdikts – krāsaina poga."""
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    akc = c["akc"]
    prim, _ = kom_krasas(c.get("badge"))
    S.pill(d, 0, 250, c["augsa"], S.ietilpinat(d, c["augsa"], "semi", 40, S.W - 160), akc, S.uz_fona(akc), center=True)
    x0, y0, x1, y1 = 70, 380, S.W - 70, 1680
    d.rounded_rectangle([x0, y0, x1, y1], radius=48, fill=KARTE_KR, outline=jaukt(prim, KARTE_KR, 0.45), width=3)
    komandas_josla(d, x0 + 44, y0 + 26, x1 - 44, c.get("badge"), h=12)
    d.text((x0 + 50, y0 + 60), f"#{c['nr']}", font=S.fonts("black", 92), fill=akc)
    fb = S.fonts("bold", 48)
    S.pill(d, x1 - 50 - S.platums(d, c["badge"], fb) - 68, y0 + 80, c["badge"], fb, c["bkr"], S.uz_fona(c["bkr"]), pad=(34, 14))
    d.text((x0 + 50, y0 + 200), c["v1"].upper(), font=S.fonts("semi", 50), fill=prim)
    d.text((x0 + 50, y0 + 258), c["v2"].upper(), font=S.ietilpinat(d, c["v2"].upper(), "black", 112, x1 - x0 - 100), fill=S.BALTS)
    d.text((x0 + 50, y0 + 400), c["info"], font=S.ietilpinat(d, c["info"], "reg", 40, x1 - x0 - 100), fill=S.PELEKS)
    tw_, th_, gap = (x1 - x0 - 100 - 2 * 22) / 3, 150, 22
    for i, (lab, val, sub) in enumerate(c["flizes"]):
        k = S.ease((t - 0.3 - 0.08 * i) / 0.35)
        if k <= 0:
            continue
        val = val if ":" in str(val) else skaitit(val, S.ease((t - 0.3 - 0.08 * i) / 0.55))
        ri, ci = divmod(i, 3)
        fx, fy = x0 + 50 + ci * (tw_ + gap), y0 + 480 + ri * (th_ + gap) + (1 - k) * 24
        d.rounded_rectangle([fx, fy, fx + tw_, fy + th_], radius=24, fill=S.ar_alfa(S.TUMSS, 255 * k))
        d.text((fx + 22, fy + 16), lab, font=S.fonts("semi", 28), fill=S.ar_alfa(S.PELEKS, 255 * k))
        sw = S.platums(d, sub, S.fonts("semi", 26)) + 14 if sub else 0
        d.text((fx + 22, fy + 52), val, font=S.ietilpinat(d, str(val), "black", 62, tw_ - 40 - sw), fill=S.ar_alfa(S.BALTS, 255 * k))
        if sub:
            krs = S.ZALS if sub.startswith("▲") else (S.SARKANS if sub.startswith("▼") else S.PELEKS)
            fs = S.fonts("semi", 26)
            d.text((fx + tw_ - 18 - S.platums(d, sub, fs), fy + th_ - 44), sub, font=fs, fill=S.ar_alfa(krs, 255 * k))
    yg = y0 + 850
    d.text((x0 + 50, yg), c.get("grafika_virs", "NEXT WEEK"), font=S.fonts("semi", 36), fill=S.PELEKS)
    pr = c["pretinieki"]
    if pr:
        n = len(pr)
        pw = min(200, (x1 - x0 - 100 - (n - 1) * 16) / n)
        for i, (dn, o, kr) in enumerate(pr):
            k = S.ease((t - 0.8 - 0.07 * i) / 0.3)
            if k <= 0:
                continue
            px = x0 + 50 + i * (pw + 16)
            d.rounded_rectangle([px, yg + 52, px + pw, yg + 172], radius=22, fill=S.ar_alfa(kr, 200 * k))
            fd, fo = S.fonts("semi", 28), S.ietilpinat(d, o, "black", 44, pw - 20)
            d.text((px + (pw - S.platums(d, dn, fd)) / 2, yg + 64), dn, font=fd, fill=S.ar_alfa(S.BALTS, 230 * k))
            d.text((px + (pw - S.platums(d, o, fo)) / 2, yg + 102), o, font=fo, fill=S.ar_alfa(S.BALTS, 255 * k))
    verdikts(d, t, 1.3, str(c["liels"]), akc, c.get("apaksa", ""), y0 + 1065, x0, x1)
    return im


def aina_outro(t, s, kanals):
    im = _orig["outro"](t, s, kanals)
    if not s.get("cta") and t > 0.9:
        k = ease_back((t - 0.9) / 0.5)
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = 120, 1440, S.W - 120, 1600
        dy = (1 - k) * 80
        d.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=36, fill=(245, 247, 250))
        S.teksts_c(d, y0 + 30 + dy, s.get("komentars", "COMMENT BELOW"), S.fonts("black", 54), S.MELNS)
        S.teksts_c(d, y0 + 98 + dy, s.get("komentars2", "What should we cover next?"), S.fonts("semi", 36), (71, 85, 105))
    return im


_orig = {}


def renderet(s, izvade, kanals="", balss=None):
    import shutil, tempfile
    if not shutil.which("ffmpeg"):
        raise SystemExit("Nav ffmpeg (Windows: winget install ffmpeg, tad jauns terminālis).")
    ainas = ([("intro", None, s["intro"].get("ilgums", 3.2))] if s.get("intro") else []) + [("karte", c, c.get("ilgums", 3.6)) for c in s["kartes"]] \
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
    atr = fona_atrums(fona_fails, kopa) if fona_fails else None
    fons = VideoFons(fona_fails, atr) if fona_fails else Fons()
    if fona_fails:
        print(f"FONS: {os.path.basename(fona_fails)}" + (f"  (ātrums {atr:.2f} = {1 / atr:.1f}× lēnāk)" if atr and atr < 0.99 else ""))
    video_tmp = os.path.join(tmp, "v.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{S.W}x{S.H}",
                          "-r", str(S.FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv",
                          "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.1",
                          "-x264-params", "aq-mode=3:keyint=60:min-keyint=30:bframes=2:ref=3",
                          "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                          "-movflags", "+faststart", "-pix_fmt", "yuv420p",
                          video_tmp], stdin=subprocess.PIPE)
    fn_map = {"fantasy": aina_fantasy, "grafiks": S.aina_grafiks, "fakts_hook": aina_fakts_hook,
              "fakts_saraksts": aina_fakts_saraksts, "fakts_konteksts": aina_fakts_konteksts,
              "fakts_nakamais": S.aina_fakts_nakamais, "fakts_mini": aina_fakts_mini}
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
            if nr == 0:                                               # 1. aina: pilns kadrs uzreiz + "punch-in"
                tt = t + (0 if (veids == "intro" and s["intro"].get("aki")) else 1.1)
                if veids == "intro":
                    sl = aina_intro(tt, s["intro"])
                elif veids != "outro":
                    sl = fn_map.get(c.get("tips"), aina_karte)(tt, c)
                if t < 0.25:
                    sc = 1.08 - 0.08 * S.ease(t / 0.25)
                    w_, h_ = int(S.W * sc), int(S.H * sc)
                    big = sl.resize((w_, h_), Image.BILINEAR)
                    yt = int(250 * sc) - 250                          # augšējā zīmīte paliek vietā (nepārklāj datumu)
                    sl = big.crop(((w_ - S.W) // 2, yt, (w_ - S.W) // 2 + S.W, yt + S.H))
                alfa, dy = 1, 0
                if t > ilg - 0.22:
                    k = S.ease((t - (ilg - 0.22)) / 0.22)
                    alfa, dy = 1 - k, -k * 120
            elif t < 0.4:
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
    for v_ in ("speletaji", "komandas", "vartsargi", "tiesnesi"):
        orig_v = S.VEIDI[v_]
        S.VEIDI[v_] = (lambda f_, vv: (lambda m, a: pievienot_aki(f_(m, a), vv)))(orig_v, v_)
    orig_ats = S.atskats

    def atskats_ar_aki(fails, m, a):
        s_ = orig_ats(fails, m, a)
        if s_ and "FOLLOW-UP" in str(s_.get("intro", {}).get("tag", "")):
            s_ = pievienot_aki(s_, "atskats")
        return s_
    S.atskats = atskats_ar_aki
    S.VEIDI["fakts"] = veids_fakti_b
    for arg, k in (("--bez-fona-video", "fons"), ("--bez-muzikas", "muzika"), ("--bez-sfx", "sfx")):
        if arg in sys.argv:
            OPC[k] = False
            sys.argv.remove(arg)


if __name__ == "__main__":
    ieslegt()
    print(f"STILS {STILS}: STORY")
    rc = S.main()
    if FAKTI_PAPILDU.get("fakti"):
        pierakstit_papildu_faktus(_arg("--mape", os.path.join(S.BASE, "video")))
    sys.exit(rc)
