"""
ShortsB.py – Ice Math (@IceMathHockey) Shorts ģenerators, stils "STORY" (palaid ŠO failu)

Izmanto shorts.py (tam jābūt tajā pašā mapē) – visi dati, teksti un komandas paliek tieši tādi paši,
mainās tikai izskats un kustība:
  • krāsains "ziemeļblāzmas" fons – lēni peldoši zili / violeti / dzelteni mirdzumi
  • ainas "uzlec" no apakšas ar nelielu atsitienu
  • saraksti atklājas no apakšas uz augšu (#5 → #1), #1 beigās izgaismojas
  • lielie skaitļi skaitās augšā
  • āķa ainā uzlīme "GUESS BEFORE THE REVEAL", beigās – aicinājums komentēt
  • komandu krāsas kartītēs un datu joslās (primārā + sekundārā krāsa)
  • fons – izpludināts hokeja video (B-roll) no mapes shorts_fons\\ (ja tur ir video)
  • āķis pirmajās ~2,4 s (konkrēts skaitlis + izpludināts #1), secība #3 → #1, cilpa beigās ("…remember:")
  • pirmajā ainā "brand header" (ripa + balts @IceMathHockey); ainu maiņā teksts izbalē un tā pati ripa
    kļūst 70 % necaurspīdīga (watermark), augšā pa kreisi; krāsains ICE MATH logo beigu kadrā
  • tiesnešu video fons automātiski palēnināts tā, lai klips izstieptos pa visu video (FONA_ATRUMS_VEIDAM)
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
  shorts_logo.png      kanāla ikona (caurspīdīga) – pirmajā ainā ar @rokturi (galvene), tad tā pati ripa (watermark).
  shorts_wordmark.png  logo ar nosaukumu (caurspīdīgs) – beigu kadrā. Ja failu nav, rāda tikai @rokturi.
  Rokturis pēc noklusējuma: KANALS_NOKL (zemāk); --kanals @cits to aizstāj.
Papildu parametri: --bez-fona-video  --bez-muzikas  --bez-sfx  --bez-logo

Lietošana (nhl-stats mapē datorā; pirms tam git pull – dati atjaunojas ~08:40 pēc Rīgas laika):
    python ShortsB.py --veids speletaji --dienas 21      (visi veidi un parametri – SHORTS_KOMANDAS.txt)
Video, INFO.txt un vēsture (fakti, tiesneši, fantasy rezultāti, atskati) – mapē video\\.
shorts.py jāatrodas tajā pašā mapē. Abi faili glabājas TIKAI datorā (.gitignore – nav publiskajā repozitorijā).
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
FONA_ATRUMS = 0.25              # fona video ātrums: 1 = normāls, 0.5 = 2× lēnāk, 0.25 = 4× lēnāk (plūstoši, ar kustības interpolāciju)
# atsevišķs ātrums konkrētam video veidam: skaitlis (piem. 0.2 = 5× lēnāk) vai "auto" = tik lēni, lai fona klips
# vienreiz izstieptos pa visu video (8 s klips → 65 s video ≈ 8× lēnāk, bez atkārtošanās). Ļoti lēnam – kustības interpolācija.
FONA_ATRUMS_VEIDAM = {"tiesnesi": "auto"}
FONA_ATRUMS_MIN = 0.08          # "auto" ne lēnāk par ~12×
SR = 44100
VIDEO_PAPL = (".mp4", ".mov", ".m4v", ".webm", ".mkv")
AUDIO_PAPL = (".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac")
OPC = {"fons": True, "muzika": True, "sfx": True, "logo": True}
KANALS_NOKL = "@IceMathHockey"            # rokturis, ja --kanals nav norādīts
LOGO_FAILS = os.path.join(S.BASE, "shorts_logo.png")           # ikona ūdenszīmei (caurspīdīgs PNG)
WORDMARK_FAILS = os.path.join(S.BASE, "shorts_wordmark.png")   # logo ar nosaukumu beigu kadram
# Pirmajā ainā – "brand header": ripa + balts @rokturis (pilnā redzamībā). Ainu maiņas brīdī (kopā ar swoosh)
# teksts izbalē un ripa plūstoši kļūst caurspīdīga (LOGO_ALFA) – tālāk paliek tikai ripa (watermark).
GALVENE = True                            # False = uzreiz tikai watermark ripa
LOGO_AUGSTUMS = 50                        # ripas augstums pikseļos (galvenē un watermark vienāds)
LOGO_ALFA = 0.70                          # watermark necaurspīdīgums (0.65–0.75 = watermark efekts)
LOGO_MELNBALTS = False                    # True = pelēka ripa
LOGO_MALA = 46                            # atstarpe no kreisās un augšējās malas (augšējais kreisais stūris –
                                          #  Shorts pogas ir labajā pusē un apakšā)

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
    """Verdikts kā slīpa krāsaina josla (THE FINAL VERDICT stilā) + paskaidrojums zem tās (ietilpst kartītē)."""
    k = S.ease((t - t0) / 0.35)
    if k <= 0:
        return
    kb = ease_back((t - t0) / 0.45)
    f = S.fonts("black", int(66 * (0.85 + 0.15 * kb)))
    bb = d.textbbox((0, 0), teksts, font=f)
    h, sl = 92, 30
    w = bb[2] - bb[0] + 2 * sl + 70
    px = (S.W - w) / 2
    d.polygon([(px + sl, y), (px + w, y), (px + w - sl, y + h), (px, y + h)], fill=S.ar_alfa(kr, 255 * k))
    for i_ in range(2):                                               # "//" svītras abās pusēs
        for xx in (px - 38 - i_ * 24, px + w + 12 + i_ * 24):
            d.polygon([(xx + 18, y + 14), (xx + 28, y + 14), (xx + 10, y + h - 14), (xx, y + h - 14)],
                      fill=S.ar_alfa(kr, 200 * k))
    d.text((px + sl + 35 - bb[0], y + (h - (bb[3] - bb[1])) / 2 - bb[1]), teksts, font=f, fill=S.ar_alfa(S.uz_fona(kr), 255 * k))
    k2 = S.ease((t - t0 - 0.25) / 0.35)
    if k2 > 0 and apaksa:
        fa, rr = S.rindas_ietilpinat(d, apaksa, "semi", 36, x1 - x0 - 100, 2)
        yy = y + h + 20
        for r in rr:
            S.teksts_c(d, yy, r, fa, S.ar_alfa(S.BALTS, 225 * k2))
            yy += int(fa.size * 1.22)


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


_logo_kesa = {}


def _logo(fails, augstums):
    """Ielādē caurspīdīgu PNG, apgriež tukšās malas un samazina līdz augstumam (kešā)."""
    k = (fails, augstums)
    if k not in _logo_kesa:
        try:
            im = Image.open(fails).convert("RGBA")
            im = im.crop(im.getbbox())
            _logo_kesa[k] = im.resize((max(1, int(im.width * augstums / im.height)), augstums), Image.LANCZOS)
        except Exception:                                             # noqa: BLE001
            _logo_kesa[k] = None
    return _logo_kesa[k]


def _ar_alfu(im, k):
    """Kopija ar reizinātu caurspīdīgumu (0..1)."""
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * k)))
    return out


def logo_slani(kanals):
    """(ripa pilnā redzamībā, @rokturis teksts) – katrs var būt None."""
    if not OPC["logo"]:
        return None, None
    ik = _logo(LOGO_FAILS, LOGO_AUGSTUMS)
    if ik is not None and LOGO_MELNBALTS:
        g = ik.convert("L").point(lambda v: int(150 + v * 0.42)).convert("RGBA")
        g.putalpha(ik.getchannel("A"))
        ik = g
    txt = (kanals or "").strip()
    tx = None
    if txt and (GALVENE or ik is None):
        f = S.fonts("bold", 32)
        d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tx = Image.new("RGBA", (int(d0.textlength(txt, font=f)) + 6, LOGO_AUGSTUMS + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(tx)
        bb = d.textbbox((0, 0), txt, font=f)
        y = (LOGO_AUGSTUMS - (bb[3] - bb[1])) // 2 - bb[1]
        d.text((2, y + 2), txt, font=f, fill=(0, 0, 0, 120))          # ēna – lasāms arī uz gaiša fona
        d.text((0, y), txt, font=f, fill=(255, 255, 255, 255))
    return ik, tx


def logo_alfas(T, T1, ir_ripa):
    """Ripas un teksta redzamība laikā T. T1 = pirmās ainas beigas (ainu maiņa ar swoosh).
    Sākumā fade-in 0,3 s; maiņas brīdī (T1 − 0,22 … T1 + 0,18) teksts 1 → 0, ripa 1 → LOGO_ALFA; tālāk nekustīgs."""
    k_in = min(1.0, T / 0.3)
    if not GALVENE:
        return k_in * LOGO_ALFA, 0.0
    p = S.ease(min(1.0, max(0.0, (T - (T1 - 0.22)) / 0.4)))
    a_txt = k_in * (1 - p)
    if not ir_ripa:                                                   # nav logo faila – teksts paliek kā watermark
        a_txt = k_in * (1 - p * (1 - LOGO_ALFA))
    return k_in * (1 - p * (1 - LOGO_ALFA)), a_txt


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
        return float(min(0.5, max(FONA_ATRUMS_MIN, d / video_ilgums)))          # "auto" (tiesneši) – neatkarīgi no FONA_ATRUMS
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
    """Hokeja "slap shot": nūjas sitiens pa ripu (ass klikšķis + koka rezonanse) + ripa atsitas pret bortu (atbalss).
    (Nosaukums paliek "boom" – shorts_sfx\\boom.mp3 joprojām to aizstāj.)"""
    rng = S.np.random.default_rng(7)
    n = int(SR * 0.6)
    t = S.np.arange(n) / SR
    y = S.np.zeros(n)
    # 1) sitiens: īss augstfrekvences troksnis (nūja + ripa)
    m = int(SR * 0.03)
    tr = rng.standard_normal(m)
    tr = S.np.diff(S.np.concatenate([[0], tr]))                      # "augstfrekvenču" troksnis (ass)
    y[:m] += tr * S.np.exp(-S.np.arange(m) / SR * 160) * 0.9
    # 2) nūjas / ripas rezonanse: dažas slāpētas frekvences
    for fr_, dec, amp in ((1350, 70, 0.55), (2650, 110, 0.3), (520, 45, 0.35), (190, 28, 0.25)):
        y += amp * S.np.sin(2 * S.np.pi * fr_ * t) * S.np.exp(-t * dec)
    # 3) ripa ietriecas bortā pēc ~0,12 s – dobjš, klusāks "thud" ar nelielu atbalsi
    o = int(SR * 0.12)
    tt = t[: n - o]
    th = (0.45 * S.np.sin(2 * S.np.pi * 140 * tt) + 0.25 * S.np.sin(2 * S.np.pi * 310 * tt)) * S.np.exp(-tt * 22)
    k = int(SR * 0.008)
    th[:k] += rng.standard_normal(k) * 0.25 * S.np.linspace(1, 0, k)
    y[o:] += th * 0.6
    y[o + int(SR * 0.09):] += th[: n - o - int(SR * 0.09)] * 0.18     # atbalss arēnā
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
    """Efektu paraugi: no shorts_sfx\\ (ja ir swoosh/boom/tick fails), citādi ģenerēti (boom = hokeja slap shot)."""
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
        if veids == "outro" and c and c.get("verdikts"):               # THE FINAL VERDICT: boom + tick katrai kartītei
            ev.append((t0 + 0.05, "boom", 0.7))
            ev += [(t0 + 0.5 + 0.45 * j, "tick", 0.8) for j in range(min(3, len(c["verdikts"])))]
        if veids == "outro" and c and c.get("fakti_tiles"):            # faktu beigas: boom + tick katrai flīzei
            ev.append((t0 + 0.05, "boom", 0.7))
            ev += [(t0 + 0.45 + 0.22 * j, "tick", 0.7) for j in range(len(c["fakti_tiles"]))]
            if c.get("streak"):
                ev.append((t0 + 0.6 + 0.22 * len(c["fakti_tiles"]), "boom", 0.5))
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
        tiles = [{"skaitlis": c_.get("skaitlis", ""), "apaksa": c_.get("skaitlis_apaksa", ""),
                  "vards": (f"{c_.get('vards', '')}" + (f" ({c_['badge']})" if c_.get("badge") and c_["badge"] not in str(c_.get("vards", "")) else "")),
                  "retums": c_.get("retums", 0)} for c_ in izv]
        # STREAK WATCH – tikai, ja aktīva sērija ir kādam NO PĀRĒJIEM faktiem (galvenā fakta "NEXT UP" jau bija stāstā)
        sr = next((c_ for c_ in citi if c_.get("aktiva") and c_.get("nakamais")), None)
        streak = None
        if sr is not None:
            streak = {"vards": str(sr.get("vards", "")).upper(), "garums": sr.get("garums", 0), "nakamais": sr["nakamais"],
                      "konteksts": (sr.get("konteksts") or [""])[0]}
        outro = {"rindas": [("WHICH ONE", S.BALTS), ("SURPRISED YOU?", S.DZELTENS)],
                 "info": [f"Stats through {S.dat(lidz, True)}", "History: our database since 2023-24"],
                 "follow": "FOLLOW FOR WEEKLY NHL FACTS", "komentars": f"COMMENT 1–{n}",
                 "komentars2": "Which fact surprised you most?", "fakti_tiles": tiles, "streak": streak}
        # beigās īsi – viss jau pateikts; sērija redzama ekrānā
        runa.append("Which one surprised you? Comment the number." + (f" And watch the {sr.get('vards', '')} streak." if streak else "")
                    + " Follow, and remember:")
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
                r_ = min(40, w / 2)
                d.rounded_rectangle([xa, y + 62, xb, y + 142], radius=r_, fill=kr)
                # pie centra līnijas – taisna mala, ārējais gals paliek noapaļots
                d.rectangle([xa, y + 62, xa + r_, y + 142] if vv >= 0 else [xb - r_, y + 62, xb, y + 142], fill=kr)
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
    # krāsu skaidrojums blakus virsrakstam
    virs_w = d.textlength(c.get("grafika_virs", "NEXT WEEK"), font=S.fonts("semi", 36))
    leg = ([("POINT", S.ZALS), ("NO POINT", S.NEITRALS)] if c.get("grafika_virs") == "GAMES THAT WEEK"
           else [("SOFT D", S.ZALS), ("AVERAGE", S.NEITRALS), ("TOUGH D", S.SARKANS)])
    fl = S.fonts("semi", 26)
    lx = x0 + 50 + virs_w + 34
    for txt_, kr_ in leg:
        d.ellipse([lx, yg + 12, lx + 20, yg + 32], fill=kr_)
        d.text((lx + 28, yg + 7), txt_, font=fl, fill=S.PELEKS)
        lx += 28 + d.textlength(txt_, font=fl) + 26
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
    verdikts(d, t, 1.3, str(c["liels"]), akc, c.get("apaksa", ""), y0 + 1050, x0, x1)
    return im


# ---------------------------------------------------------------- THE FINAL VERDICT
VERDIKTS_ILGUMS = 7.0          # sekundes (ar balsi – ne īsāks par runu)


def _mini_laukums(d, x0, y0, w, h, punkti, varti_kr, k):
    """Uzbrukuma zona (x 0..100, y −42.5..42.5) ar metieniem: vārti – krāsaini, pārējie – pelēki punkti."""
    lin = S.ar_alfa((148, 163, 184), 120 * k)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(h * 0.28), fill=S.ar_alfa((10, 14, 30), 255 * k), outline=lin, width=3)
    X = lambda v: x0 + (v / 100) * w                                  # noqa: E731
    Y = lambda v: y0 + (v + 42.5) / 85 * h                            # noqa: E731
    d.line([(X(25), y0 + 4), (X(25), y0 + h - 4)], fill=S.ar_alfa((56, 189, 248), 150 * k), width=4)   # zilā līnija
    d.line([(X(89), y0 + 8), (X(89), y0 + h - 8)], fill=S.ar_alfa((239, 68, 68), 150 * k), width=2)   # vārtu līnija
    d.pieslice([X(89) - h * 0.09, Y(0) - h * 0.09, X(89) + h * 0.09, Y(0) + h * 0.09], 90, 270,
               fill=S.ar_alfa((56, 189, 248), 70 * k))                                                   # vārtu laukums
    for yc in (-22, 22):
        r_ = h * 0.18
        d.ellipse([X(69) - r_, Y(yc) - r_, X(69) + r_, Y(yc) + r_], outline=S.ar_alfa((239, 68, 68), 110 * k), width=2)
    gk = varti_kr or S.ZALS
    for (px, py, g) in sorted(punkti, key=lambda q: q[2]):            # vārti virsū
        if not (0 <= px <= 100):
            continue
        r_ = 9 if g else 5
        c_ = S.ar_alfa(gk, 255 * k) if g else S.ar_alfa((203, 213, 225), 120 * k)
        d.ellipse([X(px) - r_, Y(py) - r_, X(px) + r_, Y(py) + r_], fill=c_)


def _slips(d, x0, y0, h, teksts, fonts_, k, fill=None, txt=None, max_w=None):
    """Dzeltena slīpa birka ar melnu tekstu; atgriež platumu."""
    fill = fill or S.DZELTENS
    f = S.ietilpinat(d, teksts, "black", fonts_, max_w) if max_w else S.fonts("black", fonts_)
    tw = d.textlength(teksts, font=f)
    sl = h * 0.35
    w = tw + 2 * sl + 30
    d.polygon([(x0 + sl, y0), (x0 + w, y0), (x0 + w - sl, y0 + h), (x0, y0 + h)], fill=S.ar_alfa(fill, 255 * k))
    bb = d.textbbox((0, 0), teksts, font=f)
    d.text((x0 + sl + 15, y0 + (h - (bb[3] - bb[1])) / 2 - bb[1]), teksts, font=f, fill=S.ar_alfa(txt or S.MELNS, 255 * k))
    return w


def aina_verdikts(t, s, kanals):
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # virsraksts – slīpa dzeltena josla ar "THE FINAL VERDICT"
    k = S.ease(t / 0.35)
    f = S.fonts("black", 74)
    tw = d.textlength("THE FINAL VERDICT", font=f)
    h_, sl = 112, 40
    w_ = tw + 2 * sl + 60
    x0 = (S.W - w_) / 2 - (1 - k) * 700
    y0 = 226
    d.polygon([(x0 + sl, y0), (x0 + w_, y0), (x0 + w_ - sl, y0 + h_), (x0, y0 + h_)], fill=S.ar_alfa(S.DZELTENS, 255 * k))
    for i_ in range(2):                                               # mazas svītras abās pusēs
        xx = x0 - 44 - i_ * 26
        d.polygon([(xx + 22, y0 + 18), (xx + 34, y0 + 18), (xx + 12, y0 + h_ - 18), (xx, y0 + h_ - 18)], fill=S.ar_alfa(S.DZELTENS, 200 * k))
        xx = x0 + w_ + 12 + i_ * 26
        d.polygon([(xx + 22, y0 + 18), (xx + 34, y0 + 18), (xx + 12, y0 + h_ - 18), (xx, y0 + h_ - 18)], fill=S.ar_alfa(S.DZELTENS, 200 * k))
    bb = d.textbbox((0, 0), "THE FINAL VERDICT", font=f)
    d.text((x0 + sl + 30, y0 + (h_ - (bb[3] - bb[1])) / 2 - bb[1]), "THE FINAL VERDICT", font=f, fill=S.MELNS)
    k2 = S.ease((t - 0.25) / 0.4)
    S.teksts_c(d, 364, "NUMBERS TELL A STORY. HERE'S WHAT IT MEANS.", S.fonts("semi", 34), S.ar_alfa((147, 197, 253), 255 * k2))

    # 3 kartītes
    kartites = s["verdikts"][:3]
    X0, X1, Y0, KH, GAP = 70, S.W - 70, 430, 318, 22
    for i, c in enumerate(kartites):
        kc = S.ease((t - 0.45 - 0.45 * i) / 0.4)
        if kc <= 0:
            continue
        y = Y0 + i * (KH + GAP) + (1 - kc) * 60
        akc = c.get("kr") or S.ZILS
        d.rounded_rectangle([X0, y, X1, y + KH], radius=30, fill=S.ar_alfa(KARTE_KR, 255 * kc),
                            outline=S.ar_alfa(akc, 200 * kc), width=3)
        # kreisā vizualizācija (300 × 196)
        vx, vy, vw, vh = X0 + 24, y + 24, 300, 196
        viz = c.get("vizu")
        if viz == "rink":
            _mini_laukums(d, vx, vy, vw, vh, c.get("punkti", []), c.get("varti_kr"), kc)
            if c.get("badge"):
                bk = tuple(c.get("bkr") or S.NEITRALS)
                fb = S.fonts("bold", 26)
                bw = d.textlength(c["badge"], font=fb) + 26
                d.rounded_rectangle([vx + 10, vy + 10, vx + 10 + bw, vy + 48], radius=19, fill=S.ar_alfa(bk, 255 * kc))
                d.text((vx + 23, vy + 14), c["badge"], font=fb, fill=S.ar_alfa(S.uz_fona(bk), 255 * kc))
        elif viz == "badge":
            bk = tuple(c.get("bkr") or S.NEITRALS)
            r_ = 86
            cx, cy = vx + vw / 2, vy + vh / 2
            d.ellipse([cx - r_, cy - r_, cx + r_, cy + r_], fill=S.ar_alfa(bk, 255 * kc), outline=S.ar_alfa(akc, 255 * kc), width=6)
            fb = S.ietilpinat(d, c.get("badge", ""), "black", 64, 150)
            bb = d.textbbox((0, 0), c.get("badge", ""), font=fb)
            d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), c.get("badge", ""), font=fb,
                   fill=S.ar_alfa(S.uz_fona(bk), 255 * kc))
        elif viz == "skaitlis":
            fb = S.ietilpinat(d, c.get("liels", ""), "black", 130, vw - 20)
            bb = d.textbbox((0, 0), c.get("liels", ""), font=fb)
            d.text((vx + (vw - (bb[2] - bb[0])) / 2 - bb[0], vy + (vh - (bb[3] - bb[1])) / 2 - bb[1]), c.get("liels", ""),
                   font=fb, fill=S.ar_alfa(akc, 255 * kc))
        else:                                                         # logo
            lg = _logo(LOGO_FAILS, 130) if OPC["logo"] else None
            if lg is not None:
                im.alpha_composite(_ar_alfu(lg, kc), (int(vx + (vw - lg.width) / 2), int(vy + (vh - lg.height) / 2)))
            else:
                S.teksts_c(d, vy + 50, "xG", S.fonts("black", 96), S.ar_alfa(S.DZELTENS, 255 * kc))
        # labā puse
        rx, rw = vx + vw + 26, X1 - 24 - (vx + vw + 26)
        d.text((rx, y + 22), c.get("virs", ""), font=S.fonts("semi", 26), fill=S.ar_alfa(akc, 255 * kc))
        fv = S.ietilpinat(d, c.get("vards", ""), "black", 38, rw)
        d.text((rx, y + 54), c.get("vards", ""), font=fv, fill=S.ar_alfa(S.BALTS, 255 * kc))
        tw_ = (rw - 14) / 2
        for j, (lab, val) in enumerate(c.get("flizes", [])[:2]):
            tx = rx + j * (tw_ + 14)
            d.rounded_rectangle([tx, y + 104, tx + tw_, y + 196], radius=16, fill=S.ar_alfa((24, 32, 64), 255 * kc))
            d.text((tx + 16, y + 112), str(lab), font=S.ietilpinat(d, str(lab), "semi", 22, tw_ - 28), fill=S.ar_alfa(S.PELEKS, 255 * kc))
            fvv = S.ietilpinat(d, str(val), "black", 48, tw_ - 28)
            d.text((tx + 16, y + 138), str(val), font=fvv, fill=S.ar_alfa(S.BALTS if j else akc, 255 * kc))
        d.text((rx, y + 206), c.get("sal", ""), font=S.ietilpinat(d, c.get("sal", ""), "reg", 26, rw),
               fill=S.ar_alfa(S.PELEKS, 255 * kc))
        if c.get("birka"):
            kb = S.ease((t - 0.75 - 0.45 * i) / 0.3)
            if kb > 0:
                _slips(d, X0 + 16, y + KH - 70, 52, str(c["birka"]).upper().rstrip("."), 30, kb, max_w=X1 - X0 - 140)

    # jautājums skatītājam (fantasy – Google Sheets piedāvājums)
    kq = ease_back((t - 0.6 - 0.45 * len(kartites)) / 0.5)
    cta = s.get("cta")
    if kq > 0 and cta:
        x0, y0, x1, y1 = 100, 1452, S.W - 100, 1652
        dy = (1 - kq) * 80
        d.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=30, fill=(15, 23, 42, 245), outline=S.DZELTENS, width=4)
        S.teksts_c(d, y0 + 24 + dy, cta[0], S.ietilpinat(d, cta[0], "black", 50, x1 - x0 - 60), S.DZELTENS)
        for i_, rinda in enumerate(cta[1:]):
            S.teksts_c(d, y0 + 96 + i_ * 48 + dy, rinda, S.ietilpinat(d, rinda, "semi", 36, x1 - x0 - 60), S.BALTS)
    elif kq > 0:
        x0, y0, x1, y1 = 120, 1462, S.W - 120, 1602
        dy = (1 - kq) * 80
        d.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=34, fill=(245, 247, 250))
        q = s.get("komentars") or "WHAT DO YOU THINK?"
        S.teksts_c(d, y0 + 22 + dy, q, S.ietilpinat(d, q, "black", 50, x1 - x0 - 60), S.MELNS)
        S.teksts_c(d, y0 + 88 + dy, f"Comment below  ·  follow {kanals}".strip(" ·"), S.fonts("semi", 32), (71, 85, 105))
    return im


def pill_slips(d, x, y, txt, f, bg, fg=None, pad=(26, 12), center=False):
    """Augšējā zīmīte (y ≈ 250–300, centrā) – slīpa josla "THE FINAL VERDICT" stilā; citas zīmītes – parastais ovāls."""
    if not (center and 230 <= y <= 310):
        return _orig["pill"](d, x, y, txt, f, bg, S.BALTS if fg is None else fg, pad, center)
    izm = getattr(f, "size", 40)
    fb = S.fonts("black", izm)
    while d.textlength(txt, font=fb) > S.W - 330 and izm > 24:
        izm -= 2
        fb = S.fonts("black", izm)
    bb = d.textbbox((0, 0), txt, font=fb)
    h, sl = 76, 26
    w = (bb[2] - bb[0]) + 2 * sl + 52
    x0, y0 = (S.W - w) / 2, y - 6
    a = bg[3] if len(bg) > 3 else 255
    kr = tuple(bg[:3])
    d.polygon([(x0 + sl, y0), (x0 + w, y0), (x0 + w - sl, y0 + h), (x0, y0 + h)], fill=kr + (int(a),))
    for i in range(2):                                                # "//" svītras abās pusēs
        for xx in (x0 - 36 - i * 22, x0 + w + 10 + i * 22):
            d.polygon([(xx + 16, y0 + 12), (xx + 26, y0 + 12), (xx + 10, y0 + h - 12), (xx, y0 + h - 12)], fill=kr + (int(a * 0.8),))
    d.text((x0 + sl + 26 - bb[0], y0 + (h - (bb[3] - bb[1])) / 2 - bb[1]), txt, font=fb, fill=S.MELNS if fg is None else fg)
    return w, h


VIEGLA_DIENA = 7                 # ≤ 7 NHL spēles dienā = "light day"


def aina_grafiks(t, c):
    """Nākamās nedēļas grafiks kā kalendārs: TARGET (4 spēles) un AVOID (2 spēles) kartītes ar spēļu dienām,
    izgaismotām vieglajām dienām un back-to-back savienojumiem + flīzes LIGHT DAYS / BEST SCHEDULE."""
    if not c.get("dienas_idx"):
        return S.aina_grafiks(t, c)
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S.pill(d, 0, 250, "NEXT WEEK'S SCHEDULE", S.fonts("semi", 40), S.ZILS, S.MELNS, center=True)
    k0 = S.ease(t / 0.4)
    S.teksts_c(d, 350, c["nedela"], S.fonts("black", 88), S.ar_alfa(S.BALTS, 255 * k0))
    S.teksts_c(d, 458, "EVERYONE ELSE PLAYS 3", S.fonts("semi", 30), S.ar_alfa(S.PELEKS, 255 * k0))
    dn = c["dienu_n"]
    viegla = [n_ <= VIEGLA_DIENA and n_ > 0 for n_ in dn]
    idx = c["dienas_idx"]
    grupas = [(g, kr, virs, birka) for g, kr, virs, birka in
              ((c["cetri"], S.ZALS, "TARGET", "4 GAMES · TARGET THEIR PLAYERS"),
               (c["divi"], S.SARKANS, "AVOID", "ONLY 2 GAMES · BENCH OR DROP")) if g]
    X0, X1, Y = 70, S.W - 70, 520
    rindas_kopa = sum(len(g[0]) for g in grupas)
    rh = int(min(66, (1440 - Y - len(grupas) * 186) / max(1, rindas_kopa)))
    kol0 = X0 + 214
    kw = (X1 - 28 - kol0) / 7
    for gi, (komandas, kr, virs, birka) in enumerate(grupas):
        kc = S.ease((t - 0.3 - 0.5 * gi) / 0.4)
        h = 106 + len(komandas) * rh + 80
        if kc > 0:
            y = Y + (1 - kc) * 50
            d.rounded_rectangle([X0, y, X1, y + h], radius=30, fill=S.ar_alfa(KARTE_KR, 255 * kc), outline=S.ar_alfa(kr, 220 * kc), width=3)
            d.text((X0 + 26, y + 18), virs, font=S.fonts("black", 40), fill=S.ar_alfa(kr, 255 * kc))
            # vieglo dienu kolonnas
            for j in range(7):
                cx = kol0 + j * kw + kw / 2
                if viegla[j]:
                    d.rounded_rectangle([cx - kw / 2 + 4, y + 66, cx + kw / 2 - 4, y + 106 + len(komandas) * rh],
                                        radius=14, fill=S.ar_alfa((34, 197, 94), 40 * kc))
                lt = "MTWTFSS"[j]
                fl = S.fonts("bold", 30)
                d.text((cx - d.textlength(lt, font=fl) / 2, y + 70), lt, font=fl,
                       fill=S.ar_alfa(S.ZALS if viegla[j] else S.PELEKS, 255 * kc))
            for ri, kom in enumerate(komandas):
                yr = y + 106 + ri * rh
                bk = tuple(S.kkrasa(kom))
                fb = S.fonts("bold", int(rh * 0.5))
                bw = 150
                d.rounded_rectangle([X0 + 26, yr + rh * 0.12, X0 + 26 + bw, yr + rh * 0.88], radius=rh * 0.38,
                                    fill=S.ar_alfa(bk, 255 * kc))
                tb = d.textbbox((0, 0), kom, font=fb)
                d.text((X0 + 26 + (bw - (tb[2] - tb[0])) / 2 - tb[0], yr + (rh - (tb[3] - tb[1])) / 2 - tb[1]), kom, font=fb,
                       fill=S.ar_alfa(S.uz_fona(bk), 255 * kc))
                if ri < len(komandas) - 1:
                    d.line([(kol0, yr + rh), (X1 - 28, yr + rh)], fill=S.ar_alfa((255, 255, 255), 18 * kc), width=1)
                dienas = idx.get(kom, [])
                r_ = rh * 0.26
                for a_, b_ in zip(dienas, dienas[1:]):                # back-to-back – savienojums
                    if b_ - a_ == 1:
                        kb = S.ease((t - 0.6 - 0.5 * gi - 0.07 * b_) / 0.25)
                        if kb > 0:
                            xa, xb = kol0 + a_ * kw + kw / 2, kol0 + b_ * kw + kw / 2
                            d.rounded_rectangle([xa, yr + rh / 2 - r_ * 0.45, xb, yr + rh / 2 + r_ * 0.45], radius=r_ * 0.45,
                                                fill=S.ar_alfa(kr, 150 * kb))
                for j in dienas:
                    kd = S.ease((t - 0.6 - 0.5 * gi - 0.07 * j) / 0.25)
                    if kd > 0 and 0 <= j < 7:
                        cx, cy = kol0 + j * kw + kw / 2, yr + rh / 2
                        rr = r_ * (0.6 + 0.4 * kd)
                        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=S.ar_alfa(kr, 255 * kd))
            kb2 = S.ease((t - 1.0 - 0.5 * gi) / 0.3)
            if kb2 > 0:
                _slips(d, X0 + 16, y + h - 66, 50, birka, 28, kb2, fill=kr, txt=S.uz_fona(kr))
        Y += h + 20
    # flīzes: LIGHT DAYS / BEST SCHEDULE
    kf = S.ease((t - 1.4 - 0.5 * (len(grupas) - 1)) / 0.4)
    if kf > 0:
        dnos = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        vd = [dnos[j] for j in range(7) if viegla[j]]
        lab = " · ".join(vd) if vd else "NONE"
        lab2 = "≤ %d NHL games" % VIEGLA_DIENA
        best = max(c["cetri"] or [""], key=lambda k_: sum(1 for j in idx.get(k_, []) if 0 <= j < 7 and viegla[j]))
        bn = sum(1 for j in idx.get(best, []) if 0 <= j < 7 and viegla[j]) if best else 0
        fl_ = [("LIGHT DAYS", lab, lab2), ("BEST SCHEDULE", f"{best}" if best else "–", f"{bn} game{'s' if bn != 1 else ''} on light days" if best else "")]
        yt = min(Y, 1480) + (1 - kf) * 40
        tw = (X1 - X0 - 20) / 2
        for i, (l1, v_, l2) in enumerate(fl_):
            tx = X0 + i * (tw + 20)
            d.rounded_rectangle([tx, yt, tx + tw, yt + 140], radius=24, fill=S.ar_alfa(KARTE_KR, 255 * kf),
                                outline=S.ar_alfa((52, 58, 84), 255 * kf), width=3)
            d.text((tx + 22, yt + 14), l1, font=S.fonts("semi", 26), fill=S.ar_alfa(S.PELEKS, 255 * kf))
            d.text((tx + 22, yt + 46), v_, font=S.ietilpinat(d, v_, "black", 50, tw - 44), fill=S.ar_alfa(S.ZALS if i == 0 else S.BALTS, 255 * kf))
            d.text((tx + 22, yt + 104), l2, font=S.ietilpinat(d, l2, "reg", 24, tw - 44), fill=S.ar_alfa(S.PELEKS, 255 * kf))
    return im


def _jauna_beigu_aina(o):
    return bool(o.get("verdikts") or o.get("fakti_tiles"))


RETUMS_TXT = ((0.85, "EXTREMELY RARE"), (0.7, "VERY RARE"), (0.55, "RARE"), (0.0, "UNCOMMON"))


def aina_fakti_beigas(t, s, kanals):
    """Faktu video beigas: "YOUR PICK" – visi fakti numurētās flīzēs ar retumu + "STREAK WATCH" aktīvai sērijai."""
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # virsraksts
    k = S.ease(t / 0.35)
    f = S.fonts("black", 74)
    txt = "YOUR PICK"
    bb = d.textbbox((0, 0), txt, font=f)
    h_, sl = 112, 40
    w_ = (bb[2] - bb[0]) + 2 * sl + 60
    x0 = (S.W - w_) / 2 - (1 - k) * 700
    y0 = 226
    d.polygon([(x0 + sl, y0), (x0 + w_, y0), (x0 + w_ - sl, y0 + h_), (x0, y0 + h_)], fill=S.ar_alfa(S.DZELTENS, 255 * k))
    for i_ in range(2):
        for xx in (x0 - 44 - i_ * 26, x0 + w_ + 12 + i_ * 26):
            d.polygon([(xx + 22, y0 + 18), (xx + 34, y0 + 18), (xx + 12, y0 + h_ - 18), (xx, y0 + h_ - 18)],
                      fill=S.ar_alfa(S.DZELTENS, 200 * k))
    d.text((x0 + sl + 30 - bb[0], y0 + (h_ - (bb[3] - bb[1])) / 2 - bb[1]), txt, font=f, fill=S.MELNS)
    S.teksts_c(d, 364, "WHICH ONE SURPRISED YOU MOST?", S.fonts("semi", 36),
               S.ar_alfa((147, 197, 253), 255 * S.ease((t - 0.25) / 0.4)))

    flizes = s["fakti_tiles"]
    st = s.get("streak")
    n = len(flizes)
    X0, X1, Y = 70, S.W - 70, 430
    RH = int(min(190, (1430 - Y - (400 if st else 0)) / max(1, n) - 14))
    if not st:                                                        # bez sērijas – flīzes vertikāli centrā
        Y += max(0, (1430 - Y - n * (RH + 14)) // 2 - 20)
    for i, c in enumerate(flizes):
        kc = S.ease((t - 0.45 - 0.22 * i) / 0.35)
        if kc <= 0:
            continue
        y = Y + i * (RH + 14) + (1 - kc) * 40
        d.rounded_rectangle([X0, y, X1, y + RH], radius=26, fill=S.ar_alfa(KARTE_KR, 255 * kc),
                            outline=S.ar_alfa(S.DZELTENS if i == 0 else (52, 58, 84), 255 * kc), width=3)
        # numurs
        r_ = RH * 0.32
        cx, cy = X0 + 26 + r_, y + RH / 2
        d.ellipse([cx - r_, cy - r_, cx + r_, cy + r_], fill=S.ar_alfa(S.DZELTENS, 255 * kc))
        fn = S.fonts("black", int(r_ * 1.0))
        nb = d.textbbox((0, 0), f"#{i + 1}", font=fn)
        d.text((cx - (nb[2] - nb[0]) / 2 - nb[0], cy - (nb[3] - nb[1]) / 2 - nb[1]), f"#{i + 1}", font=fn, fill=S.MELNS)
        # lielais skaitlis + apraksts
        tx = cx + r_ + 26
        sk_ = str(c.get("skaitlis", ""))
        fs = S.ietilpinat(d, sk_, "black", int(min(84, RH * 0.40)), 360)
        d.text((tx, y + RH * 0.12), sk_, font=fs, fill=S.ar_alfa(S.BALTS, 255 * kc))
        apr = f"{c.get('vards', '')}  ·  {c.get('apaksa', '')}".strip(" ·")
        d.text((tx, y + RH * 0.12 + fs.size * 1.08), apr,
               font=S.ietilpinat(d, apr, "semi", int(min(32, RH * 0.19)), X1 - 30 - 5 * 34 - tx - 24),
               fill=S.ar_alfa(S.PELEKS, 255 * kc))
        # retums: punkti + teksts (labajā pusē)
        ret = float(c.get("retums") or 0)
        pk = max(1, min(5, round(ret * 5)))
        lab = next(tx_ for lim, tx_ in RETUMS_TXT if ret >= lim)
        rx = X1 - 30 - 5 * 34
        for j in range(5):
            xx = rx + j * 34
            d.ellipse([xx, cy - 30, xx + 22, cy - 8], fill=S.ar_alfa(S.DZELTENS if j < pk else (52, 58, 84), 255 * kc))
        fl = S.fonts("bold", 24)
        d.text((X1 - 30 - d.textlength(lab, font=fl), cy + 6), lab, font=fl, fill=S.ar_alfa(S.DZELTENS if pk >= 4 else S.PELEKS, 255 * kc))

    # STREAK WATCH
    yk = Y + n * (RH + 14) + 10
    if st:
        ks = S.ease((t - 0.6 - 0.22 * n) / 0.4)
        if ks > 0:
            hh = min(1430 - yk, 400)
            yy = yk + (1430 - yk - hh) / 2 + (1 - ks) * 60
            d.rounded_rectangle([X0, yy, X1, yy + hh], radius=30, fill=S.ar_alfa(KARTE_KR, 255 * ks), outline=S.ar_alfa(S.ZALS, 255 * ks), width=3)
            _slips(d, X0 + 20, yy + 20, 50, "STREAK WATCH", 30, ks, fill=S.ZALS)
            nos = f"{st['vards']}  ·  {st['garums']} STRAIGHT"
            d.text((X0 + 30, yy + 88), nos, font=S.ietilpinat(d, nos, "black", 46, X1 - X0 - 60), fill=S.ar_alfa(S.BALTS, 255 * ks))
            # sērijas mērītājs: katra spēle – aizpildīts kvadrātiņš, nākamā – "?"
            g_ = int(st["garums"])
            n_kv = min(g_, 18)
            kv = min(44, (X1 - X0 - 60 - 60) / (n_kv + 1) - 8)
            for j in range(n_kv + 1):
                xx = X0 + 30 + j * (kv + 8)
                kj = S.ease((t - 0.9 - 0.22 * n - 0.03 * j) / 0.2)
                if j < n_kv:
                    d.rounded_rectangle([xx, yy + 156, xx + kv, yy + 156 + kv], radius=8, fill=S.ar_alfa(S.DZELTENS, 255 * ks * kj))
                else:
                    d.rounded_rectangle([xx, yy + 156, xx + kv, yy + 156 + kv], radius=8, outline=S.ar_alfa(S.BALTS, 255 * ks),
                                        width=3)
                    fq = S.fonts("black", int(kv * 0.7))
                    qb = d.textbbox((0, 0), "?", font=fq)
                    d.text((xx + (kv - (qb[2] - qb[0])) / 2 - qb[0], yy + 156 + (kv - (qb[3] - qb[1])) / 2 - qb[1]), "?", font=fq,
                           fill=S.ar_alfa(S.BALTS, 255 * ks))
            if g_ > n_kv:
                d.text((X0 + 30 + (n_kv + 1) * (kv + 8) + 6, yy + 160), f"+{g_ - n_kv}", font=S.fonts("bold", 30),
                       fill=S.ar_alfa(S.PELEKS, 255 * ks))
            nk = st.get("nakamais") or ("", "", "")
            nxt = f"NEXT: {nk[0]}  {nk[1]}".strip()
            d.text((X0 + 30, yy + 156 + kv + 22), nxt, font=S.ietilpinat(d, nxt, "bold", 34, X1 - X0 - 60),
                   fill=S.ar_alfa(S.PELEKS, 255 * ks))
            if st.get("konteksts") and hh >= 380:
                kt = str(st["konteksts"]).upper()
                d.text((X0 + 30, yy + 156 + kv + 68), kt, font=S.ietilpinat(d, kt, "semi", 28, X1 - X0 - 60),
                       fill=S.ar_alfa(S.DZELTENS, 255 * ks))
            if nk[2]:
                fq = S.ietilpinat(d, nk[2], "black", 54, X1 - X0 - 60)
                d.text((X0 + 30, yy + hh - fq.size - 26), nk[2], font=fq, fill=S.ar_alfa(S.ZALS, 255 * ks))

    # komentārs
    kq = ease_back((t - 0.9 - 0.22 * n - (0.4 if st else 0)) / 0.5)
    if kq > 0:
        x0, y0, x1, y1 = 120, 1462, S.W - 120, 1602
        dy = (1 - kq) * 80
        d.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=34, fill=(245, 247, 250))
        S.teksts_c(d, y0 + 22 + dy, s.get("komentars", "COMMENT BELOW"), S.fonts("black", 50), S.MELNS)
        S.teksts_c(d, y0 + 88 + dy, f"Comment the number  ·  follow {kanals}".strip(" ·"), S.fonts("semi", 32), (71, 85, 105))
    return im


def aina_outro(t, s, kanals):
    if s.get("fakti_tiles"):
        return aina_fakti_beigas(t, s, kanals)
    if s.get("verdikts"):
        return aina_verdikts(t, s, kanals)
    im = _orig["outro"](t, s, kanals)
    wm = _logo(WORDMARK_FAILS, 200) if OPC["logo"] else None
    if wm is not None and t > 0.05:                                   # logo ar nosaukumu beigu kadra augšā
        k = S.ease(t / 0.45)
        w2 = wm.copy()
        w2.putalpha(w2.getchannel("A").point(lambda v: int(v * k)))
        im.alpha_composite(w2, ((S.W - wm.width) // 2, int(300 + (1 - k) * 40)))
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
        + [("outro", s["outro"] if _jauna_beigu_aina(s["outro"]) else None,
            VERDIKTS_ILGUMS if _jauna_beigu_aina(s["outro"]) else (4.5 if s["outro"].get("cta") else 3.6))]
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
    ripa, rtekst = logo_slani(kanals)
    T1 = ainas[0][2]                                                  # pirmās ainas beigas – galvene pārvēršas watermark
    fn_map = {"fantasy": aina_fantasy, "grafiks": aina_grafiks, "fakts_hook": aina_fakts_hook,
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
            if (veids != "outro" or c) and (ripa is not None or rtekst is not None):   # galvene → watermark (beigās – lielais logo)
                a_r, a_t = logo_alfas(t0 + t, T1, ripa is not None)
                x_ = LOGO_MALA
                if ripa is not None:
                    l2 = ripa if a_r >= 1 else _ar_alfu(ripa, a_r)
                    kadrs.paste(l2, (x_, LOGO_MALA), l2)
                    x_ += ripa.width + 14
                if rtekst is not None and a_t > 0.01:
                    l2 = rtekst if a_t >= 1 else _ar_alfu(rtekst, a_t)
                    kadrs.paste(l2, (x_, LOGO_MALA), l2)
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
    _orig["pill"] = S.pill
    S.pill = pill_slips                                               # augšējās zīmītes – slīpas joslas
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
    if "--kanals" not in sys.argv:
        sys.argv += ["--kanals", KANALS_NOKL]
    for arg, k in (("--bez-fona-video", "fons"), ("--bez-muzikas", "muzika"), ("--bez-sfx", "sfx"), ("--bez-logo", "logo")):
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
