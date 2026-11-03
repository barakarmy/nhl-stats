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
MUZIKAS_SKALUMS = 0.10          # rezerve: ja skaļumu neizdodas izmērīt (0–1)
MUZIKA_ZEM_BALSS_DB = 20        # fona mūzika par tik dB (LUFS) klusāka nekā balss (lietotāja izvēle 28.10.; lielāks = klusāka);
                                # kamēr runā balss – automātiski vēl klusāka. Strādā vienādi jebkurai dziesmai.
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
OPC = {"fons": True, "muzika": True, "sfx": True, "logo": True, "subtitri": True, "zona": True}

# ---- YouTube Shorts drošā zona: saturs 85 % lielumā (augšējā josla y≈250 paliek vietā) – nekas nepaliek zem
#      YouTube pogām (labajā malā) un nosaukuma (apakšā); apakšā – subtitru josla
ZONA_MERS = 0.82                  # (bija 0.85 – kartītes apakša bija gandrīz pie subtitriem)
ZONA_ENKURS = 250                 # šī y paliek vietā (augšējā slīpā josla)
ZONA_CENTRS = 900                 # ap šo y notiek lēnā tuvināšana (satura vidus)
TUVINAJUMS = 0.02                 # katra aina lēni (gludi, subpikseļos) pietuvinās par 2 % (āķis – 4 %); 0 = izslēgt
SUBT_Y = 1490                     # subtitru rindas augša (josla ~1475–1570, centrēta); kartītes beidzas ≤ ~1435
SUBT_X0, SUBT_X1 = 150, 930          # centrēts ap x=540 (ekrāna vidus); labā mala < YouTube pogām (~985)
SUBT_IZM = 64
SUBT_MAX_VARDI, SUBT_MAX_ZIMES = 4, 24
SUBT_ATTEIKT = {"P-D-O": "PDO"}   # balsij rakstītais → kā rādīt subtitros
CILPA = 0.45                      # pēdējās sekundes daļa: beigu kadrs pāriet atpakaļ uz āķi (Shorts atkārtojas cilpā)
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


def lidzsvarotas_rindas(d, txt, veids, izm, max_w, min_izm=30):
    """Teksts vienā rindā (fontu samazinot līdz min_izm), citādi divās LĪDZSVAROTĀS rindās – dalot pie ", " / "·" / "–",
    ja tas dod līdzīgu garumu, nevis atstājot otrajā rindā vienu vārdu ("…next / week")."""
    f = S.fonts(veids, izm)
    i_ = izm
    while i_ > min_izm and S.platums(d, txt, S.fonts(veids, i_)) > max_w:
        i_ -= 2
    if S.platums(d, txt, S.fonts(veids, i_)) <= max_w:
        return S.fonts(veids, i_), [txt]
    vardi = str(txt).split(" ")
    lab, lab_v = None, None
    for j in range(1, len(vardi)):
        a, b = " ".join(vardi[:j]), " ".join(vardi[j:])
        v = max(S.platums(d, a, f), S.platums(d, b, f))
        if a.endswith((",", "·", "–", ":")) or b.startswith(("·", "–")):
            v *= 0.9                                                  # dalījums pie pieturzīmes – priekšroka
        if lab_v is None or v < lab_v:
            lab, lab_v = (a.rstrip(" ·–"), b.lstrip("·– ").strip()), v
    while izm > min_izm and max(S.platums(d, x, f) for x in lab) > max_w:
        izm -= 2
        f = S.fonts(veids, izm)
    return f, list(lab)


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
        fa, rr = lidzsvarotas_rindas(d, apaksa, "semi", 36, x1 - x0 - 100)
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
    """(ripas redzamība, teksta redzamība, teksta "savākšana" 0..1) laikā T. T1 = pirmās ainas beigas (swoosh).
    Maiņas brīdī (T1 − 0,3 … T1 + 0,25) teksts aizslīd pa kreisi un pazūd ripā; kad teksts savākts,
    ripa plūstoši kļūst caurspīdīga (LOGO_ALFA); tālāk nekustīgs."""
    k_in = min(1.0, T / 0.3)
    if not GALVENE:
        return k_in * LOGO_ALFA, 0.0, 1.0
    if not ir_ripa:                                                   # nav logo faila – teksts paliek kā watermark
        p = S.ease(min(1.0, max(0.0, (T - (T1 - 0.22)) / 0.4)))
        return 0.0, k_in * (1 - p * (1 - LOGO_ALFA)), 0.0
    sav = min(1.0, max(0.0, (T - (T1 - 0.3)) / 0.45))
    sav = sav * sav * (3 - 2 * sav)                                   # gluda paātrināšanās / palēnināšanās
    a_txt = k_in * (1 - max(0.0, (sav - 0.75) / 0.25))                # pēdējā brīdī izdziest
    q = S.ease(min(1.0, max(0.0, (T - (T1 + 0.05)) / 0.35)))          # pēc tam ripa → caurspīdīga
    return k_in * (1 - q * (1 - LOGO_ALFA)), a_txt, sav


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


VEIDI_PREFIKSI = ("speletaji", "komandas", "vartsargi", "fantasy", "streameri", "fakts", "tiesnesi", "atskats", "visi",
                  "xg", "fakti")
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
        grupa = MUZIKAS_GRUPA.get(veids)                              # tad – parastā grupa (xg_ / fantasy_)
        return a_ + ["atskats"] + ([grupa] if grupa else []) + ["visi"]
    veids = _arg("--veids", "speletaji")
    if veids in XG_VEIDI:                                             # komandas / vartsargi → kā spēlētājiem, tad xg_
        return ([veids] if veids != "speletaji" else []) + ["speletaji", "xg", "visi"]
    if veids == "streameri":                                          # streameri → tie paši faili kā fantasy
        return [veids, "fantasy", "visi"]
    if veids == "fakts":                                              # fakti_ (kā mūzikai) vai vecais fakts_
        return ["fakti", "fakts", "visi"]
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
    if not OPC["fons"]:
        return None
    f_ = _izvelets("fons", MAPE_FONS) or izveleties_mediju(MAPE_FONS, VIDEO_PAPL, "fons")
    if not f_:
        print(f"FONS: nav neviena fona video šim veidam (shorts_fons\\ meklēju: "
              + ", ".join(x + "_*" for x in veida_atslegas()) + ") – fons būs tumšs")
    return f_


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
        elif tips in ("intro", "fantasy_intro"):
            ev.append((t0 + 1.0, "tick", 0.9))
        elif tips == "fantasy_kartis":                                # kārtis: izdala → katra apgriežas (tick) → čips
            _dl, _fl, _cp = _nv_kartis_laiki(c)
            ev.append((t0 + _dl[0], "swoosh", 0.45))
            ev += [(t0 + x_ + 0.15, "tick", 0.75) for x_ in _fl]
            if _cp is not None:
                ev.append((t0 + _cp, "boom", 0.45))
        elif tips == "fakts_mini":
            ev += [(t0 + 0.9, "boom", 0.8)] + [(t0 + 1.3 + 0.15 * j, "tick", 0.6) for j in range(len(c.get("stat_rindas", [])))]
        elif tips == "fakts_konteksts":
            ev.append((t0 + 0.9, "boom", 1.0))
        elif tips == "fantasy" and JAUNS_FANTASY and c.get("viz"):
            ev += [(t0 + tt_, "tick", 0.5) for tt_ in (0.75, 1.0, 1.25, 1.5, 1.75)]
            ev.append((t0 + _nv_zimoga_laiks(c) + 0.24, "boom", 0.9))
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


IZVELETS = {"muzika": None, "fons": None}   # --muzika / --fons: konkrēts fails (testam), bez kārtas maiņas


def _izvelets(tips, mape):
    f = IZVELETS.get(tips)
    if not f:
        return None
    for c in (f, os.path.join(mape, f)):
        if os.path.isfile(c):
            return c
    print(f"{tips.upper()}: fails '{f}' nav atrasts (ne {mape}\\, ne kā pilns ceļš) – izmantoju parasto izvēli.")
    return None


# ---- MŪZIKA: faila sākums → video grupa. Katrai grupai parastajam video un atskatam – SAVA nejaušā kārta.
#      xg_       xG spēlētāji / komandas / vārtsargi + to atskati
#      fantasy_  fantasy, fantasy atskats, streameri
#      fakti_    The Week in Numbers
#      tiesnesi_ tiesnešu pārskats
#      visi_ (vai bez priedēkļa) – rezerve, ja grupai nav neviena faila
MUZIKAS_GRUPA = {"speletaji": "xg", "komandas": "xg", "vartsargi": "xg", "fantasy": "fantasy", "streameri": "fantasy",
                 "fakts": "fakti", "tiesnesi": "tiesnesi"}
MUZIKAS_VECIE = {"xg": ("speletaji", "komandas", "vartsargi"), "fakti": ("fakts",)}   # vecie nosaukumi – arī der


def _video_veids():
    """(veids, vai_atskats) – atskatam veids no atskata .json."""
    ats = _arg("--atskats")
    if not ats:
        return _arg("--veids", "speletaji"), False
    try:
        import json
        js = ats
        if os.path.isdir(ats):
            js = os.path.join(ats, sorted(f for f in os.listdir(ats) if f.endswith(".json"))[0])
        return json.load(open(js, encoding="utf-8")).get("veids", "speletaji"), True
    except Exception:                                                 # noqa: BLE001
        return "speletaji", True


def izveleties_muziku():
    """Dziesma pēc "maisa" principa: katrā kārtā katra dziesma tiek izmantota vienreiz, nejaušā secībā
    (piem. xg_4, xg_8, xg_1, xg_12 ...). Kad visas izmantotas – jauna kārta (bez tās pašas dziesmas pēc kārtas).
    Kārtas: parastais video un atskats atsevišķi, streameri atsevišķi no fantasy (bet tie paši fantasy_ faili).
    Failu skaits – no mapes katru reizi (jaunu dziesmu vienkārši ieliec mapē). Nejaušība ir noteikta no vēstures,
    tāpēc --tests izvēlas tieši to pašu dziesmu, ko īstais video. Vēsture: video\\shorts_mediji.json."""
    if not OPC["muzika"]:
        return None
    f_ = _izvelets("muzika", MAPE_MUZIKA)
    if f_:
        return f_
    if not os.path.isdir(MAPE_MUZIKA):
        return None
    veids, ats = _video_veids()
    grupa = MUZIKAS_GRUPA.get(veids, "visi")
    visi = sorted(f for f in os.listdir(MAPE_MUZIKA) if f.lower().endswith(AUDIO_PAPL))
    faili = []
    for pr in (grupa,) + MUZIKAS_VECIE.get(grupa, ()):
        faili += [f for f in visi if f.lower().startswith(pr + "_") and f not in faili]
    if not faili:
        faili = [f for f in visi if f.lower().startswith("visi_") or not f.lower().startswith(VEIDI_PREFIKSI)]
    if not faili:
        return None
    import json, random
    vm = _arg("--mape", os.path.join(S.BASE, "video"))
    vp = os.path.join(vm, MEDIJU_VESTURE)
    try:
        vest = json.load(open(vp, encoding="utf-8")) if os.path.exists(vp) else {}
    except Exception:                                                 # noqa: BLE001
        vest = {}
    k = f"muzika_karta:{veids if veids == 'streameri' else grupa}{'_atskats' if ats else ''}"
    ped = vest.get("muzika_pedeja")                                   # pēdējā dziesma jebkurā video
    izm = [f for f in (vest.get(k) or []) if f in faili] if isinstance(vest.get(k), list) else []
    pieej = [f for f in faili if f not in izm]
    if not pieej:                                                     # kārta beigusies – jauna
        izm, pieej = [], [f for f in faili if f != (vest.get(k + ":pedeja"))] or faili
        vest[k + ":nr"] = int(vest.get(k + ":nr", 1)) + 1                # jaunai kārtai – cita secība
    labak = [f for f in pieej if f != ped] or pieej                   # ne tā pati, kas tikko citā video
    rng = random.Random(f"{k}|{vest.get(k + ':nr', 1)}|{'|'.join(izm)}|{'|'.join(faili)}")
    izv = rng.choice(labak)
    vest[k] = izm + [izv]
    vest[k + ":pedeja"] = izv
    vest["muzika_pedeja"] = izv
    try:
        os.makedirs(vm, exist_ok=True)
        json.dump(vest, open(vp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:                                                 # noqa: BLE001
        pass
    print(f"MŪZIKA: {izv}  (kārta {k.split(':')[1]}: {len(vest[k])}/{len(faili)})")
    return os.path.join(MAPE_MUZIKA, izv)


def _lufs(faili, max_s=None):
    """Integrētais skaļums (LUFS) vienam vai vairākiem failiem pēc kārtas; None, ja neizdodas."""
    import json as _json
    try:
        ievades = []
        for f_ in faili:
            ievades += (["-t", f"{max_s:.0f}"] if max_s else []) + ["-i", f_]
        n = len(faili)
        filtrs = ("".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1," if n > 1 else "") \
            + "loudnorm=print_format=json"
        r = subprocess.run(["ffmpeg", "-hide_banner", *ievades, "-filter_complex" if n > 1 else "-af", filtrs,
                            "-f", "null", "-"], capture_output=True, text=True)
        v = float(_json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])["input_i"])
        return v if v > -70 else None
    except Exception:                                                 # noqa: BLE001
        return None


def muzikas_skalums(muz, balss):
    """Mūzikas pastiprinājums (dB), lai tā būtu MUZIKA_ZEM_BALSS_DB zem balss – neatkarīgi no tā, cik skaļi
    dziesma ierakstīta. Rezerve – MUZIKAS_SKALUMS."""
    import math
    l_m = _lufs([muz], 90)
    l_b = _lufs([f for f, _ in balss]) if balss else -20.0
    if l_m is None or l_b is None:
        return 20 * math.log10(MUZIKAS_SKALUMS), None
    g = max(-45.0, min(0.0, (l_b - MUZIKA_ZEM_BALSS_DB) - l_m))
    return g, f"mūzika {l_m:.0f} LUFS → {l_m + g:.0f} (balss {l_b:.0f}, {MUZIKA_ZEM_BALSS_DB} dB zem)"


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
        g_muz, muz_info = muzikas_skalums(muz, balss)
        filtri.append(f"[{idx}:a]atrim=0:{kopa:.2f},asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,"
                      f"volume={g_muz:.1f}dB,afade=t=in:d=0.8,afade=t=out:st={beigas:.2f}:d=1.8[muz0]")
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
    lufs = skalums_normalizet(izvade, tmp)
    print("AUDIO: " + " + ".join(dalas) + (f"  ·  skaļums {lufs}" if lufs else ""))
    if muz and muz_info:
        print("       " + muz_info)


def skalums_normalizet(izvade, tmp, mērķis=-14.0):
    """Skaļums kā YouTube (≈ −14 LUFS, pīķi ≤ −1,5 dB): izmēra, tad pastiprina un ierobežo pīķus."""
    import json as _json
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", izvade, "-af",
                            f"loudnorm=I={mērķis}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True)
        js = _json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
        # pastiprinājums līdz mērķim + limiteris pīķiem (skaņu efekti – sitiens, swoosh – citādi neļautu pacelt skaļumu)
        gain = max(-20.0, min(20.0, mērķis - float(js["input_i"])))
        filtrs = f"volume={gain:.2f}dB,alimiter=limit=0.75:attack=2:release=60:level=false,aresample=48000"
        jauns = os.path.join(tmp, "norm.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", izvade, "-c:v", "copy", "-af", filtrs, "-c:a", "aac",
                        "-b:a", "192k", "-movflags", "+faststart", jauns], check=True)
        os.replace(jauns, izvade)
        return f"{float(js['input_i']):.1f} → {mērķis:.0f} LUFS"
    except Exception as ex:                                           # noqa: BLE001
        print(f"AUDIO: skaļuma normalizācija izlaista ({type(ex).__name__})")
        return None


# ---------------------------------------------------------------- ainas
def uzlime(im, txt, y, lenkis=-6, kr=S.DZELTENS):
    """Mazliet sašķiebta "uzlīme" (sticker)."""
    f = S.fonts("black", 46)
    tmp = Image.new("RGBA", (S.W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    S.pill(d, 0, 50, txt, f, kr, S.MELNS, pad=(40, 20), center=True)
    tmp = tmp.rotate(lenkis, resample=Image.BICUBIC, expand=False)
    im.alpha_composite(tmp, (0, int(y)))


_UZL = {}


def _uzlime_mini():
    """Tiesnešu āķa uzlīme – izvēlas vienreiz video (aina tiek zīmēta katram kadram)."""
    if "mini" not in _UZL:
        _UZL["mini"] = S.reta_frase(S.UZLIME_MINI)
    return _UZL["mini"]


def aina_fakts_hook(t, c):
    im = _orig["fakts_hook"](t, c)
    k = ease_back((t - 1.0) / 0.45)
    if k > 0.02 and not c.get("bez_uzlimes"):
        sc = max(0.05, k)
        st = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
        uzlime(st, _uzlime_mini(), 1380)
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


def _uzskaitit(txt, t, ilgums=0.6):
    """Āķa skaitlis "uzskaitās" pirmajā 0,6 s (0 → 12, +0.0 → +6.0, 0/6 → 4/6); teksti ar burtiem (PDO 106.9) – nemainās."""
    txt = str(txt)
    if t >= ilgums or not re.fullmatch(r"[+\-−]?\d+(?:\.\d+)?%?|\d+/\d+", txt.strip()):
        return txt
    return skaitit(txt, S.ease(t / ilgums))


def _pulss(t):
    """Neliels "pulss" (līdz +6 %) tieši pēc uzskaitīšanas."""
    import math as _m
    k = (t - 0.6) / 0.3
    return 1 + 0.06 * _m.sin(_m.pi * k) if 0 < k < 1 else 1.0


def aina_aki(t, s):
    """Pirmais kadrs uzreiz pilns: skaitlis/apgalvojums + noslēpumaina #1 kartīte ar izpludinātu vārdu."""
    if s.get("fantasy_aki"):
        return aina_aki_fantasy(t, s)
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S.pill(d, 0, 250, s["tag"], S.fonts("semi", 40), S.ZILS, S.MELNS, center=True)
    y = 380
    for i, (rinda, kr) in enumerate(s["rindas"]):
        f = S.ietilpinat(d, rinda, "black", 140, S.W - 100)
        S.teksts_c(d, y, rinda, f, kr)
        y += int(f.size * 1.12)
    ar_leg = bool(s.get("legenda")) and s.get("uzlime") is not False and bool(LEGENDA_STILS)
    if s.get("kartite"):
        kt = s["kartite"]
        x0, x1, y0 = 120, S.W - 120, max(y + 40, 760)
        y1 = y0 + (470 if ar_leg else 560)                            # ar leģendu – kompaktāka kartīte
        d.rounded_rectangle([x0, y0, x1, y1], radius=44, fill=KARTE_KR, outline=jaukt(kt["akc"], KARTE_KR, 0.55), width=3)
        nr = kt.get("nr", "#1")                                       # bez komandas krāsām/zīmītes – neko neizpaužam
        S.teksts_c(d, y0 + 26, nr, S.fonts("black", 120), kt["akc"])
        vards = _izpludinats_teksts(kt["vards"], S.ietilpinat(d, kt["vards"], "black", 110, x1 - x0 - 100), S.BALTS)
        im.alpha_composite(vards, (int((S.W - vards.width) / 2), int(y0 + 165)))
        f_sk = S.ietilpinat(d, kt["skaitlis"], "black", 150, x1 - x0 - 80)
        f_sk = S.fonts("black", int(f_sk.size * _pulss(t)))
        S.teksts_c(d, y0 + (312 if ar_leg else 395) - f_sk.size // 2, _uzskaitit(kt["skaitlis"], t), f_sk, kt["akc"])
        if kt.get("apaksa"):
            S.teksts_c(d, y1 - 66, kt["apaksa"], S.ietilpinat(d, kt["apaksa"], "semi", 38, x1 - x0 - 80), S.PELEKS)
        y_st = y1 + (30 if ar_leg else 60)
    else:
        sk_ = s.get("skaitlis", "")
        f_sk = S.ietilpinat(d, sk_, "black", 260, S.W - 120)
        f_p = S.fonts("black", int(f_sk.size * _pulss(t)))
        S.teksts_c(d, y + 40 + (f_sk.size - f_p.size) // 2, _uzskaitit(sk_, t), f_p, s.get("skaitlis_kr", S.DZELTENS))
        y_st = y + 40 + int(f_sk.size * 1.15)
        if s.get("skaitlis_apaksa"):
            S.teksts_c(d, y_st, s["skaitlis_apaksa"], S.ietilpinat(d, s["skaitlis_apaksa"], "semi", 48, S.W - 140), S.PELEKS)
            y_st += 110
    if t > 0.5 and s.get("uzlime") is not False:                     # uzlīme "palieciet līdz beigām"
        kb = ease_back((t - 0.5) / 0.4)
        st = Image.new("RGBA", (S.W, 240), (0, 0, 0, 0))
        uzlime(st, s.get("uzlime", "STAY FOR #1"), 20, -5, S.DZELTENS)
        if kb < 0.999:
            sc = max(0.05, kb)
            st = st.resize((int(S.W * sc), int(240 * sc)), Image.BILINEAR)
        im.alpha_composite(st, (int((S.W - st.width) / 2), int(min(y_st, 1460))))
    if ar_leg:                                                        # xG: leģendas kartītes zem uzlīmes (vākā – nē)
        zimet_legendu(im, t + 0.3, s["legenda"], y=min(y_st, 1460) + 200)
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
    s["_intro_runa"], s["_intro_vecais"] = r[0], dict(s.get("intro") or {})   # jaunajam izskatam (kāršu ainai)
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
            rindas = [(f"{int(G)} {vv}.", S.BALTS), (f"SHOULD HAVE {S.xgv(xG, uz=G)}.", S.DZELTENS)]
            sk_ = hero["liels"]
            ap = "goals above expected" if laim_varonis else "goals below expected"
            runa0 = (S.reta_frase(S.AKIS_SP if laim_varonis else S.AKIS_SP_NE, veids="speletaji", n=2)
                     .format(G=int(G), vv=vv.lower(), x=S.xgv(xG, uz=G)) + " " + S.reta_frase(S.KAS_TAS))
            beigas = (f"{S.beigu_frase('speletaji')} {S.atskata_teksts()} "
                      f"Follow, and remember: {int(G)} {vv.lower()}.")
        elif veids == "vartsargi":
            GA, xGA = hero["bars"][0][1], hero["bars"][1][1]
            gs = abs(_parsk(hero["liels"]) or 0)
            rindas = [("HE'S STEALING" if laim_varonis else "HE'S COSTING", S.BALTS), ("GAMES.", S.DZELTENS)]
            sk_, ap = hero["liels"], f"{int(GA)} goals allowed on {S.xgv(xGA, uz=GA)} expected"
            runa0 = (S.reta_frase(S.AKIS_VA_LABS if laim_varonis else S.AKIS_VA_SLIKTS, veids="vartsargi", n=2)
                     .format(gs=S.varti_v(gs, uz=0)) + " " + S.reta_frase(S.KAS_TAS))
            beigas = (f"{S.beigu_frase('vartsargi')} {S.atskata_teksts()} Follow, and remember: this goalie is "
                      + ("stealing games." if laim_varonis else "costing games."))
        else:
            import re as _re
            m_ = _re.search(r"(\d+)-(\d+)-(\d+)", hero.get("info", ""))
            rek = f"{m_.group(1)}–{m_.group(2)}–{m_.group(3)}" if m_ else ""
            rindas = ([(f"{rek}.", S.BALTS)] if rek else []) + [("AND IT'S LUCK." if laim_varonis else "AND IT'S BAD LUCK.", S.DZELTENS)]
            sk_, ap = hero["liels"], "PDO · league average ≈ 100"
            if laim_varonis:
                runa0 = (S.reta_frase(S.AKIS_KOM_LAIM, veids="komandas", n=2).format(w=m_.group(1), l=m_.group(2)) if m_
                         else "This team is winning on luck.") + " " + S.reta_frase(S.KAS_TAS)
                beig_ = "this team is winning on luck."
            else:
                runa0 = (S.reta_frase(S.AKIS_KOM_NELAIM, veids="komandas", n=2).format(w=m_.group(1), l=m_.group(2)) if m_
                         else "This team is better than its record.") + " " + S.reta_frase(S.KAS_TAS)
                beig_ = "this team is better than its record."
            beigas = f"{S.beigu_frase('komandas')} {S.atskata_teksts()} Follow, and remember: {beig_}"
        vards = (hero.get("v2") or "").upper()
        s["intro"] = {"aki": True, "tag": tag, "rindas": rindas, "ilgums": 2.4,       # xG āķī leģendas nav
                      "kartite": {"nr": "#1", "akc": hero["akc"], "badge": hero.get("badge"), "vards": vards,
                                  "skaitlis": sk_, "apaksa": ap},
                      "uzlime": S.reta_frase(S.UZLIME_NR1)}
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
        s["intro"] = {"aki": True, "tag": s["intro"]["tag"], "ilgums": 2.4, "legenda": s["intro"].get("legenda"),
                      "rindas": [(f"ON {datums.upper()}", S.BALTS), ("WE MADE A CALL.", S.DZELTENS)],
                      "skaitlis": f"{rez}", "skaitlis_kr": S.ZALS if trapi else S.SARKANS,
                      "skaitlis_apaksa": "calls that held up" + (f"  ·  {neskait} not counted (too few games)" if neskait else ""),
                      "uzlime": S.reta_frase(S.UZLIME_ATSKATS)}
        vardi = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
        nesk_runa = ""
        if neskait:
            nesk_runa = (f" {vardi.get(neskait, neskait)} {'call was' if neskait == 1 else 'calls were'} not counted:"
                         f" too few games since.")
        r[0] = (f"On {datums} we made a call. We got {ok} out of {kopa} right.{nesk_runa} Here's every one."
                if rez else r[0])
        r[-1] = r[-1].replace("Follow for weekly NHL stats.", "Follow for the next call, and remember: we always check back.")
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
            kas_ = S.reta_frase(S.KAS_TAS)
            c0["v1"], c0["vards"] = f"{men} REFEREE REPORT", kas_.upper()
            r[0] = f"One NHL referee calls {pct} percent more penalties than average. {kas_} {men.capitalize()} referee report."
            r[-1] = r[-1].rstrip() + f" Remember the name: {stingr['rindas'][0][0]}."
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
        if veids == "liela_duo":                                      # divi komandas biedri – sezona blakus
            rindas, kopa_p = [], 0
            for pid_ in dal[0].split("-"):
                x = D["sp"][D["sp"]["playerId"] == float(pid_)]
                if x.empty:
                    continue
                GP, G, A = x["game_id"].nunique(), int(x["goals"].sum()), int(x["assists"].sum())
                kopa_p += G + A
                rindas.append((str(x["vards"].iloc[-1]).split(" ", 1)[-1], f"{GP} GP", f"{G}G {A}A"))
            if len(rindas) < 2:
                return None
            return ("SEASON SO FAR", rindas, f"{kopa_p} POINTS COMBINED",
                    "On the season: " + ", ".join(f"{r_[0]} has {r_[2].replace('G ', ' goals and ').replace('A', ' assists')}" for r_ in rindas) + ".")
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
    if arg.startswith("top"):                                         # topN: katra kategorija tikai vienreiz (ne divas sausās spēles)
        izv, kat = [], set()
        for solis in (1, 2, 3):        # 1) dažādas kategorijas  2) pārējie ne-ikdienišķie  3) jebkas
            for c in kand:
                if len(izv) >= len(idx) or c in izv:
                    continue
                k_ = _kategorija(c)
                if solis == 1 and (k_ in kat or c.get("biezi")) or solis == 2 and c.get("biezi"):
                    continue
                kat.add(k_)
                izv.append(c)
    else:
        izv = [kand[i] for i in idx if i < len(kand)]
    izv = sorted(izv, key=lambda c: -c["vert"])
    # vienas kategorijas fakti (ja izvēlēti ar numuriem) – lielākais skaitlis augstāk (29 atvairīti pirms 26)
    for k_ in {_kategorija(c) for c in izv}:
        poz = [i for i, c in enumerate(izv) if _kategorija(c) == k_]
        if len(poz) > 1:
            sak = sorted((izv[i] for i in poz), key=lambda c: -abs(float(c.get("garums") or 0)))
            for i, c in zip(poz, sak):
                izv[i] = c
    return izv


def _kategorija(c):
    k_ = str(c["atsl"]).split(":")[0]
    return {"liela_duo": "liela"}.get(k_, k_)


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
    hook_runa = hero.get("aki_runa") or " ".join(hero["hook"]).lower().capitalize()
    jaut = S.reta_frase(S.KAS_VINI if hero.get("aki_jaut") else S.KAS_TAS)
    atcerei = hero.get("aki_runa") or " ".join(hero["hook"]).lower()
    skaits_v = {2: "two", 3: "three", 4: "four", 5: "five"}.get(n, str(n))
    tag = "NHL  ·  THE WEEK IN NUMBERS"
    intro = {"aki": True, "tag": tag, "ilgums": 2.6,
             "rindas": [(r_, S.DZELTENS if i == len(hero["hook"]) - 1 else S.BALTS) for i, r_ in enumerate(hero["hook"])],
             "kartite": {"nr": "#1", "akc": S.DZELTENS, "badge": None, "vards": str(hero["vards"]).upper(),
                         "skaitlis": str(hero.get("aki_skaitlis") or hero.get("k_skaitlis") or hero.get("skaitlis")),
                         "apaksa": hero.get("aki_apaksa") or hero.get("skaitlis_apaksa", "")},
             "uzlime": S.reta_frase(S.UZLIME_NR1) if n > 1 else jaut.upper()}
    runa.append((f"The NHL week in numbers: {skaits_v} stats that stood out. Number one: {hook_runa}. {jaut}" if n > 1
                 else f"{hook_runa}. {jaut}"))
    # #n → #2: viena aina katram
    for nr, c in zip(range(n, 1, -1), citi[::-1]):
        st = fakta_statistika(D, c)
        kartes.append({"tips": "fakts_mini", "ilgums": 5.0, **c, "nr": nr,
                       "stat_rindas": [r_ for r_ in (st[1] if st else c["rindas"]) if r_[0]][:3]})
        runa.append(f"Number {nr}. {c['runa'][0]} {c['runa'][2]}".replace("  ", " "))
    # #1 – pilnais stāsts
    st = fakta_statistika(D, hero)
    kopa = {"pill_hook": "#1  ·  STAT OF THE WEEK" if n > 1 else "NHL  ·  STAT OF THE WEEK", "bez_uzlimes": True}
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
        fb_ = S.reta_frase(S.FAKTI_BEIGAS, veids="fakts", n=4)
        outro = {"rindas": [("WHICH ONE", S.BALTS), ("SURPRISED YOU?", S.DZELTENS)],
                 "info": [f"Stats through {S.dat(lidz, True)}", f"Season {S.sezonas_txt(D['sezona'])}"],
                 "follow": "FOLLOW FOR THE WEEK IN NUMBERS", "komentars": f"COMMENT 1–{n}",
                 "komentars2": "Which fact surprised you most?", "fakti_tiles": tiles, "streak": streak,
                 "fakti_apaksa": fb_[0]}
        # beigās īsi – viss jau pateikts; sērija redzama ekrānā
        runa.append(fb_[1] + (f" And watch the {sr.get('vards', '')} streak." if streak else "")
                    + f" Follow, and remember: {atcerei}.")
    else:
        outro = {"rindas": [("THE NHL WEEK", S.BALTS), ("IN NUMBERS.", S.DZELTENS)],
                 "info": [f"Stats through {S.dat(lidz, True)}", f"Season {S.sezonas_txt(D['sezona'])}"],
                 "follow": "FOLLOW FOR THE WEEK IN NUMBERS"}
        runa.append(f"Follow for the NHL week in numbers, and remember: {atcerei}.")
    FAKTI_PAPILDU["fakti"] = [{"atsl": c["atsl"], "garums": c["garums"], "teksts": c["teksts"]} for c in citi]
    return {
        "intro": intro, "kartes": kartes, "outro": outro,
        "zimogs": f"STATS THROUGH {S.dat(lidz, True).upper()}", "runa": runa, "lidz": lidz,
        "periods": f"through {S.dat(lidz, True)}",
        "virsraksts": hero["yt"] + next((x for x in ((f" + {n - 1} more NHL stats that stood out this week",
                                                       f" + {n - 1} more stats of the week", f" + {n - 1} more")
                                                      if n > 1 else ("",))
                                         if len(hero["yt"] + x) <= S.YT_MAX - 13), ""),
        "saraksts": [f"#{i + 1}  " + re.sub(r"[^\w)!?.'’%]+$", "", c["yt"]) for i, c in enumerate(izv)],   # angliski (teksts – LV)
        "apraksts": " ".join(x for x in hero["runa"] if x),
        "piezime": f"Comparisons: season {S.sezonas_txt(D['sezona'])} only.",
        "tagi": "#NHL #hockey #NHLstats #WeekInNumbers #Shorts",
        "nosaukums": f"fakti_{lidz}" if n > 1 else f"fakts_{lidz}",
        "thumb": {"tag": "NHL  ·  THE WEEK IN NUMBERS",
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


# ---- fantasy / streameru ievada leģenda (ADD / STREAM / DROP) – moderns izskats
LEGENDA_STILS = "A"               # "A" kartītes rindā · "B" panelis ar ikonām · "C" slīpas birkas · "" = vecās ovālās
_LEG_IZST = {"DROP / BENCH": "DROP"}                                   # A/B: īsāks virsraksts kartītē
_LEG_APR = {"DROP / BENCH": "cut or bench him", "STREAM": "use him, then move on"}
_LEG_IKONA = {"ADD": "plus", "STREAM": "loop", "DROP": "minus", "DROP / BENCH": "minus", "BENCH": "minus",
              "GOOD CALL": "check", "BAD CALL": "cross",                 # fantasy atskats
              "LUCKY": "down", "UNLUCKY": "up", "HIGH PDO": "down", "LOW PDO": "up",   # xG (āķa ekrānā)
              "STEALING": "plus", "COSTING": "minus", "CALLED IT": "check", "MISSED": "cross"}


def _ikona(d, veids, cx, cy, r, kr):
    w = max(4, int(r * 0.32))
    if veids in ("up", "down"):                                       # bulta augšup / lejup
        sg = -1 if veids == "up" else 1
        d.rounded_rectangle([cx - w / 2, cy - r * 0.75, cx + w / 2, cy + r * 0.75], radius=w / 2, fill=kr)
        d.polygon([(cx - r * 0.8, cy + sg * r * 0.15), (cx + r * 0.8, cy + sg * r * 0.15), (cx, cy + sg * r * 1.0)], fill=kr)
        return
    if veids == "check":
        d.line([(cx - r * 0.85, cy + r * 0.05), (cx - r * 0.25, cy + r * 0.65), (cx + r * 0.9, cy - r * 0.6)], fill=kr, width=w, joint="curve")
        return
    if veids == "cross":
        d.line([(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)], fill=kr, width=w)
        d.line([(cx - r * 0.7, cy + r * 0.7), (cx + r * 0.7, cy - r * 0.7)], fill=kr, width=w)
        return
    if veids in ("plus", "minus"):
        d.rounded_rectangle([cx - r, cy - w / 2, cx + r, cy + w / 2], radius=w / 2, fill=kr)
        if veids == "plus":
            d.rounded_rectangle([cx - w / 2, cy - r, cx + w / 2, cy + r], radius=w / 2, fill=kr)
    else:                                                             # "loop" – aplis ar bultu (izmanto un lai iet)
        d.arc([cx - r, cy - r, cx + r, cy + r], 40, 330, fill=kr, width=w)
        ax, ay = cx + r * 0.77, cy - r * 0.64
        d.polygon([(ax - r * 0.55, ay - r * 0.1), (ax + r * 0.25, ay - r * 0.55), (ax + r * 0.2, ay + r * 0.35)], fill=kr)


def _leg_dalit(legenda):
    out = []
    for txt, bg, fg in legenda:
        lab, _, apr = str(txt).partition("→") if "→" in str(txt) else str(txt).partition("=")
        out.append((lab.strip(), apr.strip(), tuple(bg[:3]), tuple(fg[:3])))
    return out


def zimet_legendu(im, t, legenda, stils=None, y=None):
    stils = LEGENDA_STILS if stils is None else stils
    L = _leg_dalit(legenda)
    if not L:
        return
    d = ImageDraw.Draw(im)
    W = S.W
    k = S.ease((t - 0.6) / 0.4)
    if k <= 0:
        return
    A = lambda kr, a=1.0: tuple(kr[:3]) + (int(255 * k * a),)
    TUMSA = (15, 23, 42)
    if stils == "A":                                                  # kartītes rindā
        n = len(L)
        cw, gap, ch = (304 if n == 3 else 340), 22, 200
        x = (W - (n * cw + (n - 1) * gap)) / 2
        for i, (lab, apr, kr, _) in enumerate(L):
            ki = S.ease((t - 0.6 - 0.12 * i) / 0.4)
            if ki <= 0:
                continue
            y0 = (1270 if y is None else y) + (1 - ki) * 40
            a = lambda kr_, m=1.0: tuple(kr_[:3]) + (int(255 * ki * m),)
            d.rounded_rectangle([x, y0, x + cw, y0 + ch], radius=26, fill=a(TUMSA, 0.92), outline=a(kr, 0.9), width=3)
            d.rounded_rectangle([x + 22, y0 + 26, x + 76, y0 + 80], radius=14, fill=a(kr))
            _ikona(d, _LEG_IKONA.get(lab, "plus"), x + 49, y0 + 53, 15, a(TUMSA))
            lab_ = _LEG_IZST.get(lab, lab)
            fl = S.ietilpinat(d, lab_, "black", 50, cw - 110)
            d.text((x + 92, y0 + 53), lab_, font=fl, fill=a(kr), anchor="lm")
            fa, rr = S.rindas_ietilpinat(d, _LEG_APR.get(lab, apr), "semi", 38, cw - 44, 2)
            for j, r_ in enumerate(rr):
                d.text((x + 22, y0 + 100 + j * 44), r_, font=fa, fill=a(S.BALTS, 0.92))
            x += cw + gap
    elif stils == "B":                                                # panelis ar ikonām
        rh, pw = 80, 760
        x0, y0 = (W - pw) / 2, (1236 if y is None else y) + (1 - k) * 30
        h = len(L) * rh + 30
        d.rounded_rectangle([x0, y0, x0 + pw, y0 + h], radius=30, fill=A(TUMSA, 0.88), outline=A((255, 255, 255), 0.12), width=2)
        y = y0 + 15
        for i, (lab, apr, kr, _) in enumerate(L):
            if i:
                d.line([x0 + 30, y, x0 + pw - 30, y], fill=A((255, 255, 255), 0.08), width=2)
            cy = y + rh / 2
            d.ellipse([x0 + 34, cy - 30, x0 + 94, cy + 30], fill=A(kr))
            _ikona(d, _LEG_IKONA.get(lab, "plus"), x0 + 64, cy, 15, A(TUMSA))
            fl = S.fonts("black", 46)
            lw = max(d.textlength(_LEG_IZST.get(l_[0], l_[0]), font=fl) for l_ in L)
            d.text((x0 + 118, cy), _LEG_IZST.get(lab, lab), font=fl, fill=A(kr), anchor="lm")
            xa = x0 + 118 + lw + 34
            apr_ = _LEG_APR.get(lab, apr)
            fa = S.ietilpinat(d, apr_, "semi", 42, x0 + pw - 34 - xa)
            d.text((xa, cy), apr_, font=fa, fill=A(S.BALTS, 0.92), anchor="lm")
            y += rh
    else:                                                             # "C" – slīpas birkas (kā augšējā josla)
        y = 1256 if y is None else y
        for i, (lab, apr, kr, fg) in enumerate(L):
            ki = S.ease((t - 0.6 - 0.12 * i) / 0.4)
            if ki <= 0:
                y += 82
                continue
            a = lambda kr_, m=1.0: tuple(kr_[:3]) + (int(255 * ki * m),)
            fl, fa = S.fonts("black", 44), S.fonts("semi", 40)
            wl, wa = d.textlength(lab, font=fl), d.textlength(apr, font=fa)
            sl, h = 22, 68
            tw = wl + 2 * sl + 40 + 26 + wa + 40
            x0 = (W - tw) / 2 + (1 - ki) * -60
            d.polygon([(x0 + sl, y), (x0 + wl + 2 * sl + 40, y), (x0 + wl + sl + 40, y + h), (x0, y + h)], fill=a(kr))
            d.text((x0 + sl + 20, y + h / 2), lab, font=fl, fill=a(fg), anchor="lm")
            xa = x0 + wl + 2 * sl + 40 + 4
            d.polygon([(xa, y), (xa + 26 + wa + 40, y), (xa + wa + 40, y + h), (xa - sl, y + h)], fill=a(TUMSA, 0.9))
            d.text((xa + 14, y + h / 2), apr, font=fa, fill=a(S.BALTS), anchor="lm")
            y += 82


def aina_intro(t, s):
    if s.get("aki"):
        return aina_aki(t, s)
    leg = s.get("legenda") or []
    jauna = LEGENDA_STILS and any(_leg_dalit([x])[0][0] in _LEG_IKONA for x in leg)
    im = _orig["intro"](t, dict(s, legenda=[]) if jauna else s)
    if jauna:
        zimet_legendu(im, t, leg)
    if t > 1.0:
        tag = str(s.get("tag", "")).upper()
        if "FOLLOW" in tag or "RECAP" in tag:
            txt = "DID WE GET IT RIGHT?"
        elif "STREAMER" in tag:                                     # secība #1 → #3, tāpēc ne "WHO'S #1?"
            if "streameri" not in _UZL:                                # izvēlas vienreiz video
                _UZL["streameri"] = S.reta_frase(S.UZLIME_STREAMERI)
            txt = _UZL["streameri"]
        elif "FANTASY" in tag:
            if "fantasy" not in _UZL:
                _UZL["fantasy"] = S.reta_frase(S.UZLIME_FANTASY)
            txt = _UZL["fantasy"]
        elif "GOALIE" in tag:
            txt = "HOT HAND OR LUCKY?"
        else:
            txt = "WHO'S LUCKY? WHO'S DUE?"
        uzlime(im, txt, 1500, 5, S.ZILS)            # zonā beidzas ~1415 – virs subtitriem (1490)
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


def _cap_y(d, f, cy):
    """y teksta zīmēšanai, lai LIELO burtu/ciparu vidus būtu tieši cy (neatkarīgi no fonta izmēra un astēm)."""
    bb = d.textbbox((0, 0), "H0", font=f)
    return cy - (bb[1] + bb[3]) / 2


def _etikete(txt):
    """'Referees: A · B' → ('REFEREES', 'A · B'); bez etiķetes → (None, txt)."""
    a_, sep, b_ = str(txt).partition(":")
    if sep and b_.strip() and 0 < len(a_) <= 22 and not re.search(r"\d", a_):
        return a_.strip().upper(), b_.strip()
    return None, str(txt)


def info_karte(d, y, rindas, k, x0=90, x1=None, akc=None):
    """Mūsdienīga informācijas kartīte: katra rinda – maza pelēka etiķete + balta vērtība (vai viens teksts); atgriež apakšu."""
    x1 = x1 or S.W - 90
    akc = akc or S.DZELTENS
    rr = [_etikete(r) for r in rindas if str(r).strip()]
    if not rr:
        return y
    rh = [104 if lab else 76 for lab, _ in rr]
    h = sum(rh) + 24
    d.rounded_rectangle([x0, y, x1, y + h], radius=26, fill=S.ar_alfa(KARTE_KR, 255 * k), outline=S.ar_alfa((52, 58, 84), 255 * k), width=2)
    d.rounded_rectangle([x0, y + 18, x0 + 8, y + h - 18], radius=4, fill=S.ar_alfa(akc, 255 * k))
    yy = y + 12
    for i, ((lab, val), h_) in enumerate(zip(rr, rh)):
        if lab:
            d.text((x0 + 40, yy + 12), lab, font=S.fonts("semi", 28), fill=S.ar_alfa(akc, 230 * k))
            fv = S.ietilpinat(d, val, "bold", 42, x1 - x0 - 80)
            d.text((x0 + 40, yy + 46), val, font=fv, fill=S.ar_alfa(S.BALTS, 255 * k))
        else:
            fv = S.ietilpinat(d, val, "semi", 36, x1 - x0 - 80)
            d.text((x0 + 40, _cap_y(d, fv, yy + h_ / 2)), val, font=fv, fill=S.ar_alfa(S.BALTS, 255 * k))
        if i < len(rr) - 1:
            d.line([(x0 + 40, yy + h_), (x1 - 30, yy + h_)], fill=S.ar_alfa((255, 255, 255), 22 * k), width=2)
        yy += h_
    return y + h


def kopsavilkuma_cipss(d, y, txt, k):
    """Saraksta kopsavilkums – centrēts "čips": pelēka etiķete + dzeltena vērtība (vai viens teksts)."""
    lab, val = _etikete(txt)
    fl, fv = S.fonts("semi", 30), S.fonts("black", 44)
    if lab:
        val = val.upper()
        wl, wv = d.textlength(lab, font=fl), d.textlength(val, font=fv)
        w = wl + 24 + wv + 72
    else:
        fv = S.ietilpinat(d, txt, "black", 42, S.W - 220)
        w = d.textlength(txt, font=fv) + 72
    x0 = (S.W - w) / 2
    h = 84
    d.rounded_rectangle([x0, y, x0 + w, y + h], radius=h / 2, fill=S.ar_alfa((24, 32, 64), 255 * k), outline=S.ar_alfa(S.DZELTENS, 170 * k), width=3)
    yt = _cap_y(d, fv, y + h / 2)
    if lab:
        d.text((x0 + 36, _cap_y(d, fl, y + h / 2)), lab, font=fl, fill=S.ar_alfa(S.PELEKS, 255 * k))
        d.text((x0 + 36 + wl + 24, yt), val, font=fv, fill=S.ar_alfa(S.DZELTENS, 255 * k))
    else:
        d.text((x0 + 36, yt), txt, font=fv, fill=S.ar_alfa(S.BALTS, 255 * k))


def jautajuma_kaste(d, y0, jaut, kanals, k, pirma="COMMENT BELOW"):
    """Beigu jautājums skatītājam: tumša kartīte ar dzeltenu rāmi, slīpa birka "YOUR TAKE", jautājums un divi čipi."""
    x0, x1 = 90, S.W - 90
    dy = (1 - k) * 80
    y0 = y0 + dy
    a = max(0.0, min(1.0, k))
    d.rounded_rectangle([x0, y0, x1, y0 + 168], radius=30, fill=(12, 18, 36, int(255 * a)), outline=S.ar_alfa(S.DZELTENS, 255 * a), width=3)
    _slips(d, x0 + 30, y0 - 24, 46, "YOUR TAKE", 26, a)
    q = (jaut or "WHAT DO YOU THINK?").upper()
    S.teksts_c(d, y0 + 30, q, S.ietilpinat(d, q, "black", 54, x1 - x0 - 80), S.ar_alfa(S.BALTS, 255 * a))
    c1, c2 = pirma.upper(), (f"FOLLOW {kanals}" if kanals else "FOLLOW FOR MORE").upper()
    fc = S.fonts("bold", 26)
    w1, w2 = d.textlength(c1, font=fc) + 48, d.textlength(c2, font=fc) + 48
    xs = (S.W - (w1 + 16 + w2)) / 2
    yc = y0 + 104
    d.rounded_rectangle([xs, yc, xs + w1, yc + 44], radius=22, fill=S.ar_alfa(S.DZELTENS, 255 * a))
    d.rounded_rectangle([xs + w1 + 16, yc, xs + w1 + 16 + w2, yc + 44], radius=22, outline=S.ar_alfa(S.DZELTENS, 255 * a), width=2)
    ty = _cap_y(d, fc, yc + 22)
    d.text((xs + 24, ty), c1, font=fc, fill=S.ar_alfa(S.MELNS, 255 * a))
    d.text((xs + w1 + 16 + 24, ty), c2, font=fc, fill=S.ar_alfa(S.DZELTENS, 255 * a))


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
        cy = y + (rh - 20) / 2                                         # rindas vidus (lielo burtu augstuma centrs)
        fa = S.ietilpinat(d, str(a_), "semi", 40, vw - 20)
        fb = S.ietilpinat(d, str(b_), "bold", 46, 300)
        fv = S.ietilpinat(d, str(c_), "black", 50, 330)
        d.text((x0 + 44, _cap_y(d, fa, cy)), str(a_), font=fa, fill=S.ar_alfa(c.get("vards_kr", S.PELEKS), 255 * k))
        d.text((x0 + 30 + vw, _cap_y(d, fb, cy)), str(b_), font=fb, fill=S.ar_alfa(S.BALTS, 255 * k))
        v = skaitit(c_, S.ease((t - 0.2 - solis * sec) / 0.5))
        d.text((x1 - 44 - S.platums(d, str(c_), fv), _cap_y(d, fv, cy)), v, font=fv, fill=S.ar_alfa(S.DZELTENS, 255 * k))
        if i < n - 1:
            d.line([(x0 + 40, y + rh - 6), (x1 - 40, y + rh - 6)], fill=S.ar_alfa((255, 255, 255), 25 * k), width=2)
    k2 = S.ease((t - 0.35 - solis * n) / 0.4)
    if k2 > 0 and c.get("kopsavilkums"):
        kopsavilkuma_cipss(d, y0 + 76 + rh * max(1, n) + (1 - k2) * 20, c["kopsavilkums"], k2)
    return im


def aina_fakts_konteksts(t, c):
    """Liels skaitlis + virsraksts + paskaidrojumi informācijas kartītē (etiķete + vērtība)."""
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S.pill(d, 0, 250, c.get("pill_k", "HOW RARE IS IT?"), S.fonts("semi", 40), S.ZILS, S.MELNS, center=True)
    k = S.ease(t / 0.5)
    sk = skaitit(c["k_skaitlis"], S.ease(t / 0.9))
    f = S.ietilpinat(d, c["k_skaitlis"], "black", int(300 * (0.8 + 0.2 * k)), S.W - 120)
    S.teksts_c(d, 470, sk, f, S.ar_alfa(S.DZELTENS, 255 * k))
    k2 = S.ease((t - 0.5) / 0.45)
    f, rindas = S.rindas_ietilpinat(d, c["konteksts"][0], "black", 76, S.W - 140, 3)
    y = 860
    for r in rindas:
        S.teksts_c(d, y, r, f, S.ar_alfa(S.BALTS, 255 * k2))
        y += int(f.size * 1.2)
    k3 = S.ease((t - 0.9) / 0.45)
    if k3 > 0 and len(c["konteksts"]) > 1:
        info_karte(d, y + 50 + (1 - k3) * 30, c["konteksts"][1:], k3)
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
    f_ap, rr_ap = lidzsvarotas_rindas(d, c["apaksa"], "semi", 40, x1 - x0 - 100, min_izm=32)
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
    if JAUNS_FANTASY and c.get("viz"):                                # jaunais izskats (fantasy / streameri; ne atskats)
        return aina_fantasy_jauna(t, c)
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
        sw = S.flizes_sub(d, fx + tw_ - 18, fy + th_ - 44, sub, k, tikai_platums=True) + 14 if sub else 0
        d.text((fx + 22, fy + 52), val, font=S.ietilpinat(d, str(val), "black", 62, tw_ - 40 - sw), fill=S.ar_alfa(S.BALTS, 255 * k))
        if sub:
            S.flizes_sub(d, fx + tw_ - 18, fy + th_ - 44, sub, k)
    yg = y0 + 850
    d.text((x0 + 50, yg), c.get("grafika_virs", "NEXT WEEK"), font=S.fonts("semi", 36), fill=S.PELEKS)
    # krāsu skaidrojums blakus virsrakstam
    virs_w = d.textlength(c.get("grafika_virs", "NEXT WEEK"), font=S.fonts("semi", 36))
    leg = ([("POINT", S.ZALS), ("NO POINT", S.NEITRALS)] if c.get("grafika_virs") == "GAMES THAT WEEK"
           else [("SOFT D", S.ZALS), ("AVERAGE", S.NEITRALS), ("TOUGH D", S.SARKANS)])
    fl = S.fonts("semi", 26)
    vb = d.textbbox((x0 + 50, yg), c.get("grafika_virs", "NEXT WEEK"), font=S.fonts("semi", 36))
    cy = (vb[1] + vb[3]) / 2                                          # virsraksta burtu vertikālais centrs
    lx = x0 + 50 + virs_w + 34
    for txt_, kr_ in leg:
        d.ellipse([lx, cy - 10, lx + 20, cy + 10], fill=kr_)
        tb = d.textbbox((0, 0), txt_, font=fl)
        d.text((lx + 28, cy - (tb[1] + tb[3]) / 2), txt_, font=fl, fill=S.PELEKS)
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


def virsraksta_fonts(d, txt, sl, izm=74):
    """Lielā slīpā virsraksta fonts: josla + "//" svītras abās pusēs (~104 px katrā) ietilpst ekrānā ar 24 px malu
    (dažos datoros fonts ir platāks – tad virsraksts tiek samazināts, nevis iziet ārpus ekrāna)."""
    while izm > 40 and d.textlength(txt, font=S.fonts("black", izm)) + 2 * sl + 60 + 2 * 104 > S.W - 48:
        izm -= 2
    return S.fonts("black", izm)


def aina_verdikts(t, s, kanals):
    im = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # virsraksts – slīpa dzeltena josla ar "THE FINAL VERDICT"
    k = S.ease(t / 0.35)
    h_, sl = 112, 40
    f = virsraksta_fonts(d, "THE FINAL VERDICT", sl)
    tw = d.textlength("THE FINAL VERDICT", font=f)
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
    S.teksts_c(d, 364, s.get("verd_apaksa", "NUMBERS TELL A STORY. HERE'S WHAT IT MEANS."), S.fonts("semi", 34),
               S.ar_alfa((147, 197, 253), 255 * k2))

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
        elif viz == "badge":                                          # komandas kods + komandas krāsu josla
            kom = str(c.get("badge", ""))
            p_ = spilgta(tuple(c.get("bkr") or S.kkrasa(kom) or S.NEITRALS), 0.6)
            s_ = SEKUNDARAS.get(kom, (230, 230, 235))
            if sum(abs(a - b) for a, b in zip(p_, s_)) < 90:
                s_ = (230, 230, 235)
            cx = vx + vw / 2
            fb = S.ietilpinat(d, kom, "black", 120, vw - 40)
            bb = d.textbbox((0, 0), kom, font=fb)
            ty = vy + vh / 2 - 22 - (bb[3] - bb[1]) / 2 - bb[1]
            d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], ty), kom, font=fb, fill=S.ar_alfa(S.BALTS, 255 * kc))
            jb, jy = 170, vy + vh / 2 + (bb[3] - bb[1]) / 2 - 4
            d.rounded_rectangle([cx - jb / 2, jy, cx + jb / 2, jy + 14], radius=7, fill=S.ar_alfa(s_, 255 * kc))
            d.rounded_rectangle([cx - jb / 2, jy, cx + 10, jy + 14], radius=7, fill=S.ar_alfa(p_, 255 * kc))
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
        sal_ = c.get("sal", "")
        iz_s = 26
        while iz_s > 18 and S.platums(d, sal_, S.fonts("reg", iz_s)) > rw:     # ietilpināt kartītē (var būt < 30 px)
            iz_s -= 1
        d.text((rx, y + 206), sal_, font=S.fonts("reg", iz_s), fill=S.ar_alfa(S.PELEKS, 255 * kc))
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
        jautajuma_kaste(d, min(1462, Y0 + len(kartites) * (KH + GAP) + 42),   # mazāk kartīšu – jautājums tuvāk
                        s.get("komentars") or "WHAT DO YOU THINK?", kanals, kq)
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
    if JAUNS_FANTASY and c.get("_tv"):                               # jaunais izskats – tablo josla
        _nv_tablo_virs(im, None, t, c["_tv"])
    else:
        S.pill(d, 0, 250, c.get("pill", "NEXT WEEK'S SCHEDULE"), S.fonts("semi", 40), S.ZILS, S.MELNS, center=True)
    k0 = S.ease(t / 0.4)
    S.teksts_c(d, 350, c["nedela"], S.fonts("black", 88), S.ar_alfa(S.BALTS, 255 * k0))
    S.teksts_c(d, 458, c.get("apaksa_txt", "EVERYONE ELSE PLAYS 3"), S.fonts("semi", 30), S.ar_alfa(S.PELEKS, 255 * k0))
    dn = c["dienu_n"]
    viegla = [n_ <= VIEGLA_DIENA and n_ > 0 for n_ in dn]
    idx = c["dienas_idx"]
    grupas = [(g, kr, virs, birka) for g, kr, virs, birka in
              ((c["cetri"], S.ZALS, c.get("virs1", "TARGET"), c.get("birka1", "4 GAMES · TARGET THEIR PLAYERS")),
               (c["divi"], S.SARKANS, c.get("virs2", "AVOID"), c.get("birka2", "ONLY 2 GAMES · BENCH OR DROP"))) if g]
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
    txt = "YOUR PICK"
    h_, sl = 112, 40
    f = virsraksta_fonts(d, txt, sl)
    bb = d.textbbox((0, 0), txt, font=f)
    w_ = (bb[2] - bb[0]) + 2 * sl + 60
    x0 = (S.W - w_) / 2 - (1 - k) * 700
    y0 = 226
    d.polygon([(x0 + sl, y0), (x0 + w_, y0), (x0 + w_ - sl, y0 + h_), (x0, y0 + h_)], fill=S.ar_alfa(S.DZELTENS, 255 * k))
    for i_ in range(2):
        for xx in (x0 - 44 - i_ * 26, x0 + w_ + 12 + i_ * 26):
            d.polygon([(xx + 22, y0 + 18), (xx + 34, y0 + 18), (xx + 12, y0 + h_ - 18), (xx, y0 + h_ - 18)],
                      fill=S.ar_alfa(S.DZELTENS, 200 * k))
    d.text((x0 + sl + 30 - bb[0], y0 + (h_ - (bb[3] - bb[1])) / 2 - bb[1]), txt, font=f, fill=S.MELNS)
    S.teksts_c(d, 364, s.get("fakti_apaksa", "WHICH ONE SURPRISED YOU MOST?"), S.fonts("semi", 36),
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
        lab_ = next(tx_ for lim, tx_ in RETUMS_TXT if float(c.get("retums") or 0) >= lim)
        max_a = X1 - 30 - max(5 * 34, d.textlength(lab_, font=S.fonts("bold", 24))) - tx - 30
        iz_a = int(min(32, RH * 0.19))
        while iz_a > 20 and d.textlength(apr, font=S.fonts("semi", iz_a)) > max_a:     # var būt mazāks par 30
            iz_a -= 2
        d.text((tx, y + RH * 0.12 + fs.size * 1.08), apr,
               font=S.fonts("semi", iz_a),
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
        jautajuma_kaste(d, 1462, s.get("komentars", "WHICH ONE?"), kanals, kq, pirma="COMMENT THE NUMBER")
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
        jautajuma_kaste(d, 1450, s.get("komentars", "WHAT SHOULD WE COVER NEXT?"), kanals, k)
    return im


_orig = {}
_THUMB = {"im": None}


def thumbnail_kadrs(aina, s, fona_fails, atr, fn_map):
    """Sīktēls: video pirmā aina (āķis) pilnā izskatā, uz tā paša fona – bez uzlīmes, datuma, progresa joslas un logo."""
    veids, c, _ = aina
    if veids == "intro":
        i_ = dict(s["intro"])
        if i_.get("aki"):
            i_["uzlime"] = False                                      # sīktēlā – bez uzlīmes
            sl = aina_aki(3.0, i_)
        else:
            sl = _orig["intro"](3.0, i_)
    else:
        c2 = dict(c or {}, bez_uzlimes=True)
        sl = fn_map.get(c2.get("tips"), aina_karte)(3.0, c2)
    if fona_fails:
        f_ = VideoFons(fona_fails, atr)
        for _ in range(int(0.6 * S.FPS)):                             # mazliet tālāk par pašu pirmo kadru
            kadrs = f_.kadrs(0)
        f_.aizvert()
    else:
        kadrs = Fons().kadrs(0)
    kadrs = kadrs.convert("RGBA")
    kadrs.alpha_composite(sl)
    return kadrs.convert("RGB")


def zimet_thumbnail_b(th, fails):
    if _THUMB.get("im") is not None:
        _THUMB["im"].save(fails)
    else:
        _orig["thumbnail"](th, fails)


def _zona(sl, zm=0.0):
    """Ainas slānis → drošajā zonā (ZONA_MERS, josla y=ZONA_ENKURS paliek vietā) + lēna tuvināšana zm ap satura vidu."""
    m = ZONA_MERS if OPC["zona"] else 1.0
    if m == 1.0 and not zm:
        return sl
    a_ = ZONA_ENKURS - ZONA_ENKURS * m
    # 1) nemainīgs samazinājums (ar antialiasing, izmērs katrā kadrā vienāds);
    # 2) tuvināšana ar subpikseļu affine (float mērogs/nobīde) – agrāk resize uz veselu izmēru + paste veselos
    #    pikseļos katrā kadrā lēca par 1 px, un kartīte izskatījās "drebam".
    w_, h_ = round(S.W * m), round(S.H * m)
    small = sl.resize((w_, h_), Image.BILINEAR) if m != 1.0 else sl
    k = 1 + zm
    x0, y0 = (S.W - w_) / 2, a_                                       # small novietojums bez tuvināšanas
    cx, cy = S.W / 2, ZONA_CENTRS
    # izvades (X, Y) → small koordinātas: ((X - cx) / k + cx - x0, (Y - cy) / k + cy - y0)
    out = small.transform((S.W, S.H), Image.AFFINE, (1 / k, 0, cx - cx / k - x0, 0, 1 / k, cy - cy / k - y0),
                          resample=Image.BILINEAR)
    return out


def _subt_gabali(vardi):
    """[(sākums, beigas, vārds)] (video laikā) → subtitru gabali. Vispirms teikumos (pieturzīme vai pauze > 0,25 s),
    tad katru teikumu – vienmērīgos gabalos pa ≤ SUBT_MAX_VARDI (5 → 3+2, 9 → 3+3+3), lai beigās nepaliek viens vārds.
    → [(rādīt_no, rādīt_līdz, [(sākums, beigas, vārds)])]"""
    import math as _m
    teikumi, cur = [], []
    for a, b, x in vardi:
        x = SUBT_ATTEIKT.get(x, x).strip()
        if not x:
            continue
        if cur and (cur[-1][2][-1:] in ".?!:" or a - cur[-1][1] > 0.25):
            teikumi.append(cur)
            cur = []
        cur.append((a, b, x))
    if cur:
        teikumi.append(cur)
    gabali = []
    for t_ in teikumi:
        k = max(1, _m.ceil(len(t_) / SUBT_MAX_VARDI))
        while k < len(t_) and any(len(" ".join(w[2] for w in t_[round(i_ * len(t_) / k):round((i_ + 1) * len(t_) / k)])) > SUBT_MAX_ZIMES + 6
                                  for i_ in range(k)):
            k += 1                                                    # par garu (gari vārdi) – vairāk gabalu
        for i_ in range(k):
            g = t_[round(i_ * len(t_) / k):round((i_ + 1) * len(t_) / k)]
            if g:
                gabali.append(g)
    out = []
    for j_, g in enumerate(gabali):
        beigas = g[-1][1] + 0.35
        if j_ + 1 < len(gabali):
            beigas = min(beigas + 0.5, gabali[j_ + 1][0][0])
        out.append((g[0][0] - 0.05, beigas, g))
    return out


def zimet_subtitrus(kadrs, gabali, T):
    """Subtitri drošajā joslā: balti ar tumšu kontūru, pašreizējais vārds – dzeltens."""
    g = next((x for x in gabali if x[0] <= T < x[1]), None)
    if g is None:
        return
    vardi = [w[2] for w in g[2]]
    akt = max([i for i, w in enumerate(g[2]) if w[0] <= T] or [0])
    d = ImageDraw.Draw(kadrs)
    teksts = " ".join(vardi)
    izm = SUBT_IZM
    while izm > 36 and d.textlength(teksts, font=S.fonts("black", izm)) > SUBT_X1 - SUBT_X0:
        izm -= 2
    f = S.fonts("black", izm)
    atst = d.textlength(" ", font=f)
    platumi = [d.textlength(v, font=f) for v in vardi]
    x = SUBT_X0 + (SUBT_X1 - SUBT_X0 - (sum(platumi) + atst * (len(vardi) - 1))) / 2
    for i, (v, w) in enumerate(zip(vardi, platumi)):
        d.text((x, SUBT_Y + (SUBT_IZM - izm) / 2), v, font=f, fill=S.DZELTENS if i == akt else S.BALTS,
               stroke_width=max(4, izm // 9), stroke_fill=(8, 10, 22))
        x += w + atst


def renderet(s, izvade, kanals="", balss=None):
    import shutil, tempfile
    if not shutil.which("ffmpeg"):
        raise SystemExit("Nav ffmpeg (Windows: winget install ffmpeg, tad jauns terminālis).")
    if s["outro"].get("verdikts") and "verd_apaksa" not in s["outro"]:
        s["outro"]["verd_apaksa"] = S.reta_frase(S.VERDIKTA_APAKSA)
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
    for _v, _c, _ilg in ainas:                                        # ainas garums (jaunajai kartītei – zīmoga laiks)
        if isinstance(_c, dict):
            _c["_ilg"] = _ilg
    if audio and len(S.VARDI_AINAS) == len(ainas):                    # balss vārdu laiki ainai (kārtis apgriežas pēc balss)
        for (_v, _c, _ilg), _vl in zip(ainas, S.VARDI_AINAS):
            if isinstance(_c, dict):
                _c["_vardi"] = [(a_ + 0.15, b_ + 0.15, x_) for a_, b_, x_ in _vl]
    subt = []
    if audio and OPC["subtitri"] and len(S.VARDI_AINAS) == len(ainas):
        sak_, vv_ = 0.0, []
        for (_, _, ilg_), vl in zip(ainas, S.VARDI_AINAS):
            vv_ += [(sak_ + 0.15 + a, sak_ + 0.15 + b, x) for a, b, x in vl]   # balss sākas 0,15 s pēc ainas (miksets)
            sak_ += ilg_
        subt = _subt_gabali(vv_)
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
              "fakts_nakamais": S.aina_fakts_nakamais, "fakts_mini": aina_fakts_mini,
              "fantasy_intro": lambda t_, c_: aina_intro(t_, c_["intro"]), "fantasy_kartis": aina_kartis}
    # cilpai: āķa (1. ainas) sākuma kadrs – beigās video pāriet atpakaļ uz to
    v0, c0, _ = ainas[0]
    if v0 == "intro":
        cilpa_sl = aina_intro(0.0 if s["intro"].get("aki") else 1.1, s["intro"])
    elif v0 == "karte":
        cilpa_sl = fn_map.get(c0.get("tips"), aina_karte)(1.1, c0)
    else:
        cilpa_sl = None
    cilpa_sl = _zona(cilpa_sl) if cilpa_sl is not None else None
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
            sl = _zona(sl, (0.04 if nr == 0 else TUVINAJUMS) * S.ease(t / ilg))     # drošā zona + lēna tuvināšana
            if veids == "outro" and cilpa_sl is not None and t > ilg - CILPA:      # cilpa: atpakaļ uz āķi
                sl = Image.blend(sl, cilpa_sl, S.ease((t - (ilg - CILPA)) / CILPA))
            kadrs = fons.kadrs(t0 + t)
            if alfa < 1:
                sl.putalpha(sl.getchannel("A").point(lambda v: int(v * alfa)))
            kadrs.paste(sl, (0, int(dy)), sl)
            dd = ImageDraw.Draw(kadrs, "RGBA")
            if not s.get("_bez_zimoga"):                              # jaunajā izskatā datums ir kartītes tablo joslā
                fz = S.ietilpinat(dd, s["zimogs"], "semi", 34, S.W - 100)
                S.teksts_c(dd, 170, s["zimogs"], fz, S.ar_alfa(S.PELEKS, 235))
            # progresa josla: dzeltena līnija augšā (kā shorts.py)
            dd.rectangle([0, 0, S.W, 10], fill=(255, 255, 255, 30))
            dd.rectangle([0, 0, S.W * min(1, (t0 + t) / kopa), 10], fill=S.DZELTENS)
            if (veids != "outro" or c) and (ripa is not None or rtekst is not None):   # galvene → watermark (beigās – lielais logo)
                a_r, a_t, sav = logo_alfas(t0 + t, T1, ripa is not None)
                if rtekst is not None and a_t > 0.01:                 # teksts – zem ripas, slīd ripā un pazūd
                    l2 = rtekst if a_t >= 1 else _ar_alfu(rtekst, a_t)
                    if ripa is not None:
                        cx_r = LOGO_MALA + ripa.width / 2             # ripas centrs – tur teksts "ieiet"
                        x_t = LOGO_MALA + ripa.width + 14 - sav * (rtekst.width + 14 + ripa.width / 2)
                        nogriezt = int(max(0, cx_r - x_t))
                        if nogriezt < l2.width:
                            l2 = l2.crop((nogriezt, 0, l2.width, l2.height))
                            kadrs.paste(l2, (int(x_t) + nogriezt, LOGO_MALA), l2)
                    else:
                        kadrs.paste(l2, (LOGO_MALA, LOGO_MALA), l2)
                if ripa is not None:                                  # ripa virsū
                    l2 = ripa if a_r >= 1 else _ar_alfu(ripa, a_r)
                    kadrs.paste(l2, (LOGO_MALA, LOGO_MALA), l2)
            if subt:
                zimet_subtitrus(kadrs, subt, t0 + t)
            p.stdin.write(kadrs.tobytes())
        t0 += ilg
    p.stdin.close()
    p.wait()
    if fona_fails:
        fons.aizvert()
    try:                                                              # sīktēls = āķa kadrs ar to pašu fonu
        _THUMB["im"] = thumbnail_kadrs(ainas[0], s, fona_fails, atr, fn_map)
    except Exception as ex:                                           # noqa: BLE001
        print(f"SĪKTĒLS: neizdevās no āķa ({type(ex).__name__}: {ex}) – vecais variants")
        _THUMB["im"] = None
    miksets(video_tmp, izvade, audio, ainas, kopa, tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    return kopa, bool(audio)


TESTA_MAPE = "video_test"
VESTURES_FAILI = ("fakti_vesture.json", "frazes_vesture.json", "tiesnesi_vesture.json", "fantasy_rezultati.json",
                  "shorts_mediji.json")


def testa_mape():
    """--tests: video tiek saglabāti video_test\\ (nevis video\\). Pirms katras palaišanas uz turieni nokopē īstās vēstures
    (fakti, frāzes, tiesneši, fantasy rezultāti, fona/mūzikas kārta) – tests izvēlas TIEŠI to pašu, ko izvēlētos īstais video,
    bet īstā vēsture video\\ netiek aiztikta."""
    import shutil
    ista = os.path.join(S.BASE, "video")
    tm = os.path.join(S.BASE, TESTA_MAPE)
    os.makedirs(tm, exist_ok=True)
    for f in VESTURES_FAILI:
        src = os.path.join(ista, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tm, f))
        elif os.path.exists(os.path.join(tm, f)):
            os.remove(os.path.join(tm, f))
    if "--mape" not in sys.argv:
        sys.argv += ["--mape", tm]
    print(f"TESTS: video mapē {TESTA_MAPE}\\ (īstā vēsture video\\ netiek mainīta)")


def ieslegt():
    for k in ("fakts_konteksts", "karte", "fantasy", "fakts_hook", "outro", "intro"):
        _orig[k] = getattr(S, "aina_" + k)
    _orig["pill"] = S.pill
    _orig["thumbnail"] = S.zimet_thumbnail
    S.zimet_thumbnail = zimet_thumbnail_b
    S.pill = pill_slips                                               # augšējās zīmītes – slīpas joslas
    S.renderet = renderet
    for v_ in ("speletaji", "komandas", "vartsargi", "tiesnesi"):
        orig_v = S.VEIDI[v_]
        S.VEIDI[v_] = (lambda f_, vv: (lambda m, a: xg_jauns(pievienot_aki(f_(m, a), vv), vv)))(orig_v, v_)
    orig_ats = S.atskats

    def atskats_ar_aki(fails, m, a):
        s_ = orig_ats(fails, m, a)
        if s_ and "FOLLOW-UP" in str(s_.get("intro", {}).get("tag", "")):
            s_ = xg_atskats_jauns(pievienot_aki(s_, "atskats"))
        if s_ and "RECAP" in str(s_.get("intro", {}).get("tag", "")):     # fantasy atskats – jaunais izskats (ShortsBT)
            s_ = fantasy_atskats_jauns(s_)
        return s_
    S.atskats = atskats_ar_aki
    S.VEIDI["fakts"] = veids_fakti_b
    for v_ in ("fantasy", "streameri"):                               # jaunais āķis fantasy / streameru video
        if v_ in S.VEIDI:
            S.VEIDI[v_] = (lambda f_: (lambda m, a: fantasy_aki(f_(m, a))))(S.VEIDI[v_])
    for arg, k in (("--muzika", "muzika"), ("--fons", "fons")):     # konkrēts fails testam:  --muzika dziesma.mp3
        if arg in sys.argv:
            i_ = sys.argv.index(arg)
            if i_ + 1 < len(sys.argv):
                IZVELETS[k] = sys.argv[i_ + 1]
                del sys.argv[i_:i_ + 2]
    if "--tests" in sys.argv:                                         # testa režīms – atsevišķa mape video_test\\
        sys.argv.remove("--tests")
        testa_mape()
    if "--kanals" not in sys.argv:
        sys.argv += ["--kanals", KANALS_NOKL]
    for arg, k in (("--bez-fona-video", "fons"), ("--bez-muzikas", "muzika"), ("--bez-sfx", "sfx"), ("--bez-logo", "logo"),
                   ("--bez-subtitriem", "subtitri"), ("--pilns-ekrans", "zona")):
        if arg in sys.argv:
            OPC[k] = False
            sys.argv.remove(arg)



# ================================================================ JAUNAIS FANTASY / STREAMERU IZSKATS (kopš 02.11.)
# Āķis: "7 POINTS" + punkti pa spēlēm + "...AND HE'S STILL ON WAIVERS" + noslēpumaina #1 kartīte ar kustīgu "?".
# Kartīte: vārds ar komandas kodu fonā un divkrāsu pasvītru "/", logs ar neona rāmi un vienu gaismiņu, kas
# plūdeni "izrullējas" uz leju, flīzes ar mini grafikiem, ESPN rostered tendence, verdikta zīmogs virsū beigās.
# Pagaidām tikai ShortsBT.py (testa versija, video_bt\\). ShortsB.py – vecais izskats, līdz jaunais būs pabeigts.
JAUNS_FANTASY = False            # ShortsBT.py to ieslēdz (tests); kad gatavs – True arī šeit
_NV_TILE, _NV_SL, _NV_LAB = (30, 41, 59), (100, 116, 139), (148, 163, 184)
_NV_KESA = {}


def _nv_timg(txt, f, fill, stroke=0, sfill=None):
    k = (txt, f.path, f.size, fill, stroke, sfill)
    if k not in _NV_KESA:
        if len(_NV_KESA) > 400:
            _NV_KESA.clear()
        d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        bb = d0.textbbox((0, 0), txt, font=f, stroke_width=stroke)
        im = Image.new("RGBA", (max(1, bb[2] - bb[0] + 8), max(1, bb[3] - bb[1] + 8)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)
        _NV_KESA[k] = im
    return _NV_KESA[k]


def _nv_burts(ch, f, fill):
    """Viens burts vārda "krišanas" animācijai – uz kopējas bāzes līnijas, lai Ä (ar punktiem), apostrofs, J u.c.
    nebūtu nobīdīti (agrāk katrs burts tika centrēts pēc sava augstuma). → (attēls, nobīde no LIELO burtu vidus
    līdz attēla centram)."""
    k = ("burts", ch, f.path, f.size, fill)
    if k not in _NV_KESA:
        if len(_NV_KESA) > 400:
            _NV_KESA.clear()
        asc, desc = f.getmetrics()
        p = 14
        w, h = int(math.ceil(f.getlength(ch))) + 2 * p, asc + desc + 2 * p
        im = Image.new("RGBA", (max(1, w), h), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((p, p + asc), ch, font=f, fill=fill, anchor="ls")
        hb = f.getbbox("H", anchor="ls")
        _NV_KESA[k] = (im, h / 2 - (p + asc + (hb[1] + hb[3]) / 2))
    return _NV_KESA[k]


def _nv_put(layer, im, cx, cy, sc=1.0, a=1.0, rot=0.0, anchor="c"):
    if a <= 0.01 or sc <= 0.01:
        return
    if sc != 1.0:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if a < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    x = cx - im.width / 2 if anchor == "c" else cx
    layer.alpha_composite(im, (int(x), int(cy - im.height / 2)))


def _nv_glow(layer, r=18, s=1.3):
    sm = layer.resize((S.W // 4, S.H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4)).resize((S.W, S.H), Image.BILINEAR)
    sm.putalpha(sm.getchannel("A").point(lambda v: min(255, int(v * s))))
    out = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    out.alpha_composite(sm)
    out.alpha_composite(sm)
    out.alpha_composite(layer)
    return out


def _nv_mirgo(t, t0):
    k = t - t0
    if k < 0:
        return 0.0
    for lim, v in ((0.05, 1), (0.10, 0.1), (0.16, 0.9), (0.20, 0.2), (0.3, 1)):
        if k < lim:
            return v
    return 1.0


def _nv_perim(x0, y0, x1, y1, s, r=36, ins=2.5):
    """Punkts uz noapaļota taisnstūra kontūras (tā pati līnija, ko zīmē rounded_rectangle)."""
    x0, y0, x1, y1 = x0 + ins, y0 + ins, x1 - ins, y1 - ins
    r = max(1.0, min(r - ins, (x1 - x0) / 2, (y1 - y0) / 2))
    w_, h_ = x1 - x0 - 2 * r, y1 - y0 - 2 * r
    loks = math.pi * r / 2
    posmi = [("l", (x0 + r, y0), (1, 0), w_), ("a", (x1 - r, y0 + r), -90, loks), ("l", (x1, y0 + r), (0, 1), h_),
             ("a", (x1 - r, y1 - r), 0, loks), ("l", (x1 - r, y1), (-1, 0), w_), ("a", (x0 + r, y1 - r), 90, loks),
             ("l", (x0, y1 - r), (0, -1), h_), ("a", (x0 + r, y0 + r), 180, loks)]
    s %= sum(p[3] for p in posmi)
    for tips, p0, v, garums in posmi:
        if s <= garums:
            if tips == "l":
                return (p0[0] + v[0] * s, p0[1] + v[1] * s)
            ang = math.radians(v + 90 * s / loks)
            return (p0[0] + r * math.cos(ang), p0[1] + r * math.sin(ang))
        s -= garums
    return (x0 + r, y0)


def _nv_gaisma(dn, box, t, atr=410, kr=(255, 225, 225), garums=16):
    """Viena gaismiņa, kas lēni skrien pa noapaļoto rāmi (ar mīkstu oreolu)."""
    px, py = _nv_perim(*box, t * atr)
    for rr, al in ((34, 25), (24, 45), (16, 70)):
        dn.ellipse([px - rr, py - rr, px + rr, py + rr], fill=kr + (al,))
    for j in range(garums):
        px, py = _nv_perim(*box, t * atr - j * 9)
        rr = 9 - j * 0.45
        dn.ellipse([px - rr, py - rr, px + rr, py + rr], fill=kr + (int(255 * (1 - j / garums)),))


def _nv_perim_garums(box, r=36, ins=2.5):
    x0, y0, x1, y1 = box[0] + ins, box[1] + ins, box[2] - ins, box[3] - ins
    r = max(1.0, min(r - ins, (x1 - x0) / 2, (y1 - y0) / 2))
    return 2 * (x1 - x0 - 2 * r) + 2 * (y1 - y0 - 2 * r) + 2 * math.pi * r


def _nv_gaisas_kr(kr):
    """Komandas krāsa gaismiņai: tumšas (melna, tumši zila) → gaiši pelēka, citas – mazliet gaišākas."""
    kr = tuple(kr[:3])
    if 0.299 * kr[0] + 0.587 * kr[1] + 0.114 * kr[2] < 70:
        return (230, 232, 240)
    return tuple(int(x + (255 - x) * 0.25) for x in kr)


def _nv_komeeta(dn, box, s_, kr, virz, al=1.0, garums=22):
    """Viena maza, maiga gaismiņa ar plānu asti (virz = +1 pulksteņrādītāja virzienā, −1 pretēji)."""
    px, py = _nv_perim(*box, s_)
    for rr, a_ in ((20, 16), (13, 32)):                                # neliels oreols
        dn.ellipse([px - rr, py - rr, px + rr, py + rr], fill=kr + (int(a_ * al),))
    for j in range(garums):
        qx, qy = _nv_perim(*box, s_ - virz * j * 6)
        rr = 5.5 - j * 4.5 / garums
        dn.ellipse([qx - rr, qy - rr, qx + rr, qy + rr], fill=kr + (int(210 * (1 - j / garums) ** 1.5 * al),))
    dn.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(255, 255, 255, int(210 * al)))


def _nv_divas_gaismas(dn, box, u, c, prim, sek):
    """Divas gaismiņas komandas krāsās skrien pa rāmi pretējos virzienos visu kartītes laiku un satiekas nejaušās
    vietās (bez papildu efektiem – tikai pabrauc viena otrai garām). Katrai kartītei cits ātrums un vieta (sēkla –
    spēlētājs + datums), bet viena tikšanās vienmēr ir tieši zīmoga brīdī (vieta – nejauša)."""
    if "_gs" not in c:
        import zlib
        rnd = random.Random(zlib.crc32(f"{c.get('v1', '')} {c.get('v2', '')} {c.get('_datums', '')}".encode()))
        va, vb = 1 / rnd.uniform(14.0, 18.0), 1 / rnd.uniform(14.0, 18.0)   # apļi sekundē (viens aplis 14–18 s – mierīgi)
        c["_gs"] = (rnd.random(), va, vb)
    m, va, vb = c["_gs"]
    tz = _nv_zimoga_laiks(c) + 0.24                                     # zīmogs "nolaižas"
    P = _nv_perim_garums(box)
    al = 0.85 * min(1.0, (u - 0.9) / 0.6)
    _nv_komeeta(dn, box, (m + va * (u - tz)) * P, _nv_gaisas_kr(prim), 1, al)
    _nv_komeeta(dn, box, (m - vb * (u - tz)) * P, _nv_gaisas_kr(sek), -1, al)   # satiekoties – vienkārši pabrauc garām


_NV_DAL = [(random.Random(i).uniform(60, 1020), random.Random(i + 99).uniform(0, 1), random.Random(i + 7).uniform(0.6, 1.4),
            random.Random(i + 3).choice([S.DZELTENS, S.ZILS, (255, 255, 255)])) for i in range(40)]


def _nv_dalinas(L, t):
    d = ImageDraw.Draw(L)
    for x, ph, sp, kr in _NV_DAL:
        p = (ph + t * 0.09 * sp) % 1
        y = 1700 - p * 1500
        a = int(150 * math.sin(math.pi * p))
        r = 3 + 3 * sp
        xx = x + 30 * math.sin(t + ph * 9)
        d.ellipse([xx - r, y - r, xx + r, y + r], fill=kr + (a,))


def _nv_kratit(L, t, t0, amp=14, dur=0.25):
    k = (t - t0) / dur
    if not 0 <= k < 1:
        return L
    a = amp * (1 - k) ** 2
    rnd = random.Random(int(t * 1000))
    out = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    out.paste(L, (int(rnd.uniform(-a, a)), int(rnd.uniform(-a, a))), L)
    return out


def _nv_zibsnis(L, t, t0, s=0.14, dur=0.14):
    k = (t - t0) / dur
    if 0 <= k < 1:
        L.alpha_composite(Image.new("RGBA", (S.W, S.H), (255, 255, 255, int(255 * s * (1 - k)))))


def fantasy_aki(s):
    """Fantasy / streameru scenārijs → āķis sākumā (vecā ievada vietā) + āķa teikums balsī."""
    if not s or not JAUNS_FANTASY or not s.get("aki_f"):
        return s
    vecais = s["intro"]
    s["intro"] = {"aki": True, "fantasy_aki": s["aki_f"], "tag": s["aki_f"]["tag"], "ilgums": 2.6}
    try:                                                              # 2. aina – kārtis (vecā ievada vietā)
        otra = _nv_kartis_dati(s, vecais)
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (kāršu aina: {type(ex).__name__} – vecais ievads)")
        otra = None
    s["kartes"].insert(0, otra or {"tips": "fantasy_intro", "intro": vecais, "ilgums": 3.2})
    s["runa"].insert(0, s["aki_runa"])
    viz = [c for c in s["kartes"] if c.get("tips") == "fantasy" and c.get("viz")]   # tablo josla: punkti + datums
    kr_ = [tuple(x["akc"]) for x in viz]
    dat_ = _nv_datums(s.get("zimogs"))
    for i, c in enumerate(viz):
        c["_tablo"] = {"idx": i, "kr": kr_}
        c["_datums"] = dat_
    try:                                                              # ievada ainām – zila tablo josla (zilās slīpās joslas vietā)
        tag = str(vecais.get("tag", "NHL  ·  FANTASY WAIVER WIRE"))
        dala = tag.split("·")[-1].strip()
        lab, liels = ("NHL · FANTASY", dala[len("FANTASY"):].strip()) if dala.upper().startswith("FANTASY ") else ("NHL", dala)
        tv = {"lab": lab, "liels": liels, "kr": kr_, "labaja": dat_}
        s["intro"]["_tv"] = tv
        for c in s["kartes"]:
            if c.get("tips") == "fantasy_kartis":
                c["_tv"] = tv
            elif c.get("tips") == "grafiks":
                p_ = str(c.get("pill", "NEXT WEEK'S SCHEDULE")).upper()
                lab_g, liels_g = (p_[:-len("SCHEDULE")].strip() or "NEXT WEEK'S", "SCHEDULE") if p_.endswith("SCHEDULE") else ("SCHEDULE", p_)
                n1 = re.search(r"\d+", str(c.get("birka1", ""))); n2 = re.search(r"\d+", str(c.get("birka2", "")))
                lj = (f"{n1[0] if n1 else 4} GAMES = {c.get('virs1', 'TARGET')}" if c.get("cetri") else "") + \
                     (f"  ·  {n2[0] if n2 else 2} = {c.get('virs2', 'AVOID')}" if c.get("divi") else "")
                c["_tv"] = {"lab": lab_g, "liels": liels_g, "kr": kr_, "labaja": lj.strip(" ·")}
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (tablo josla ievadam: {type(ex).__name__} – vecā zīmīte)")
    s["_bez_zimoga"] = True                                           # datums – tablo joslā, ne atsevišķā rindā
    return s


XG_VIRSR = {"speletaji": [("WHO'S", S.BALTS), ("RUNNING", S.BALTS), ("ON LUCK?", S.DZELTENS)],
            "vartsargi": [("WHO'S", S.BALTS), ("STEALING", S.BALTS), ("GAMES?", S.DZELTENS)],
            "komandas": [("WHO'S", S.BALTS), ("LIVING", S.BALTS), ("ON LUCK?", S.DZELTENS)]}
XG_TV = {"speletaji": ("NHL · xG", "LUCK REPORT"), "vartsargi": ("NHL · GOALIES", "GSAx REPORT"), "komandas": ("NHL · TEAMS", "PDO REPORT")}
XG_APAKSA = {"speletaji": "GOALS VS EXPECTED GOALS (xG)", "vartsargi": "GOALS SAVED ABOVE EXPECTED (GSAx)",
             "komandas": "PDO = SHOOTING % + SAVE %  ·  AVERAGE 100"}


def _xg_periods(s):
    m_ = re.findall(r"([A-Z][a-z]{2}) (\d+)", str(s.get("periods", "")))
    if len(m_) >= 2:
        a_, b_ = m_[0], m_[-1]
        return f"{a_[0]} {a_[1]} – {b_[1]}".upper() if a_[0] == b_[0] else f"{a_[0]} {a_[1]} – {b_[0]} {b_[1]}".upper()
    return ""


def xg_jauns(s, veids):
    """xG video (spēlētāji / vārtsargi / komandas) jaunajā izskatā: āķis → kārtis → kartītes → THE FINAL VERDICT.
    Kartītes secība – kā līdz šim (otra grupa #3 → #1, tad varoņa grupa #3 → #1)."""
    if not s or not JAUNS_FANTASY or veids not in XG_VIRSR or not s.get("kartes"):
        return s
    try:
        kar = s["kartes"]
        if not all(c.get("viz") and c["viz"].get("spec") for c in kar) or len(s["runa"]) != len(kar) + 2:
            return s
        hero = kar[-1]
        per = _xg_periods(s)
        kr_rad = [tuple(c["akc"]) for c in kar]
        lab_, liels_ = XG_TV[veids]
        tv = {"lab": lab_, "liels": liels_, "kr": kr_rad, "labaja": per}
        ha = dict(hero["viz"]["aki"])
        ha.update({"vards": str(hero.get("v2", "")).upper(), "kom": hero.get("badge"), "tag": s["intro"].get("tag", ""), "kart_txt": "#1"})
        orig = sorted(kar, key=lambda c: (0 if c["viz"]["grupa"] == "laim" else 1, c.get("nr", 0)))
        kartis = [{"kom": str(c.get("badge", "")), "poz": c["viz"].get("poz", ""), "akc": tuple(c["akc"]),
                   "liels": c["viz"]["kart"]["liels"], "maz": c["viz"]["kart"]["maz"], "lab": c["viz"]["zimogs"]} for c in orig]
        k2 = {"tips": "fantasy_kartis", "ilgums": 6.0, "tag": s["intro"].get("tag", ""), "_tv": tv, "virsr": XG_VIRSR[veids],
              "apaksa": "  ·  ".join(x for x in (per, XG_APAKSA[veids]) if x), "kartis": kartis,
              "n_pick": sum(1 for c in orig if c["viz"]["grupa"] == "laim"), "rek": None}
        jaunas = [k2]
        for i, c in enumerate(kar):
            c = dict(c)
            c["tips"], c["liels"] = "fantasy", c["viz"]["zimogs"]
            c["_tablo"] = {"lab": c["viz"]["tablo_lab"], "liels": f"#{c.get('nr', '')}", "kr": kr_rad, "idx": i}
            c["_datums"] = c["viz"].get("tablo_txt", "")
            jaunas.append(c)
        s["intro"] = {"aki": True, "fantasy_aki": ha, "tag": ha["tag"], "ilgums": 2.6, "_tv": tv}
        s["runa"] = [s["runa"][0], s.get("_intro_runa", "")] + s["runa"][1:]
        s["kartes"] = jaunas
        s["_bez_zimoga"] = True
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (xG jaunais izskats: {type(ex).__name__}: {ex} – vecais)")
    return s


def xg_atskats_jauns(s):
    """xG atskats jaunajā izskatā: rezultāts ("2/3" + ✓/✗) → kārtis "DID xG CALL IT?" → visas kartītes → THE FINAL VERDICT."""
    if not s or not JAUNS_FANTASY or not s.get("aki_f"):
        return s
    try:
        kar = s["kartes"]
        if not all(c.get("viz") and c["viz"].get("spec") for c in kar) or len(s["runa"]) != len(kar) + 2:
            return s
        kr_rad = [tuple(c["akc"]) for c in kar]
        tag = str(s["aki_f"].get("tag", ""))
        liels_ = "GOALIES" if "GOALIE" in tag else ("TEAMS" if "TEAM" in tag else "xG")
        tv = {"lab": "NHL · FOLLOW-UP", "liels": liels_, "kr": kr_rad, "labaja": kar[0]["viz"].get("tablo_txt", "")}
        kartis = [{"kom": str(c.get("badge", "")), "poz": c["viz"].get("poz", ""), "akc": tuple(c["akc"]),
                   "aizm": S.ZALS if c["viz"]["grupa"] == "laim" else S.SARKANS,
                   "liels": c["viz"]["kart"]["liels"], "maz": c["viz"]["kart"]["maz"], "lab": c["viz"]["zimogs"]} for c in kar]
        vecais = s.get("_intro_vecais") or {}
        ap = vecais.get("apaksa") or []
        k2 = {"tips": "fantasy_kartis", "ilgums": 6.0, "tag": tag, "_tv": tv,
              "virsr": [("DID", S.BALTS), ("xG", S.BALTS), ("CALL IT?", S.DZELTENS)],
              "apaksa": "  ·  ".join(str(x).upper() for x in ap[:2]), "kartis": kartis,
              "n_pick": sum(1 for c in kar if c["viz"]["grupa"] == "laim"), "rek": None}
        jaunas = [k2]
        for i, c in enumerate(kar):
            c = dict(c)
            c["tips"], c["liels"] = "fantasy", c["viz"]["zimogs"]
            c["_tablo"] = {"lab": c["viz"]["tablo_lab"], "liels": f"#{c.get('nr', '')}", "kr": kr_rad, "idx": i}
            c["_datums"] = c["viz"].get("tablo_txt", "")
            jaunas.append(c)
        s["intro"] = {"aki": True, "fantasy_aki": s["aki_f"], "tag": tag, "ilgums": 2.6, "_tv": tv}
        s["runa"] = [s["aki_runa"], s.get("_intro_runa", s["runa"][0])] + s["runa"][1:]
        s["kartes"] = jaunas
        s["_bez_zimoga"] = True
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (xG atskata jaunais izskats: {type(ex).__name__}: {ex} – vecais)")
    return s


def fantasy_atskats_jauns(s):
    """Fantasy atskats jaunajā izskatā: nedēļas rezultāts ("1/4" + ✓/✗) → kārtis "LAST WEEK'S CALLS" → visas ieteiktās
    kartītes (WE SAID ADD #1 …) → THE FINAL VERDICT. Balss: rezultāts, ievads, katrs spēlētājs, beigas."""
    if not s or not JAUNS_FANTASY or not s.get("aki_f"):
        return s
    try:
        kar = s["kartes"]
        if not all(c.get("tips") == "fantasy" and c.get("viz") for c in kar) or len(s["runa"]) != len(kar) + 2:
            return s
        vecais = s["intro"]
        ap = [str(x) for x in vecais.get("apaksa", [])]
        no_, lidz_ = s.get("periods", "").replace("week of ", "").split(" – ")[:2] if " – " in s.get("periods", "") else ("", "")
        ned = re.sub(r",\s*\d{4}$", "", f"{no_} – {lidz_}").upper()
        ned = re.sub(r"\b([A-Z]{3}) (\d+) – \1 (\d+)\b", r"\1 \2 – \3", ned)
        n_add = sum(1 for c in kar if c["viz"].get("grupa") == "add")
        kr_rez = [tuple(c["akc"]) for c in kar]
        kartis = []
        for c in kar:
            v = c["viz"]
            kartis.append({"kom": str(c.get("badge", "")), "poz": v.get("poz", ""), "akc": tuple(c["akc"]),
                           "aizm": S.ZALS if v.get("grupa") == "add" else S.SARKANS,
                           "liels": f"{v['pts']} PT{'' if v['pts'] == 1 else 'S'}", "maz": f"TYPICAL {v['med']:.0f}",
                           "lab": str(c.get("liels", ""))})
        tv = {"lab": "NHL · FANTASY", "liels": "RECAP", "kr": kr_rez, "labaja": f"WEEK OF {ned}"}
        k2 = {"tips": "fantasy_kartis", "ilgums": 6.0, "tag": vecais.get("tag", ""), "_tv": tv,
              "virsr": [("LAST", S.BALTS), ("WEEK'S", S.BALTS), ("CALLS", S.DZELTENS)],
              "apaksa": f"{ned}  ·  VS A TYPICAL PLAYER IN THE SAME POOL",
              "kartis": kartis, "n_pick": n_add, "rek": tuple(s["atskats_rek"]) if s.get("atskats_rek") else None}
        jaunas, nr_ = [k2], {}
        for i, c in enumerate(kar):                                   # visas ieteiktās kartītes (secībā kā sestdienas video)
            c = dict(c)
            teica = str(c.get("augsa", "")).split("  ·  ")[0].replace("WE SAID:", "").strip() or \
                ("ADD" if c["viz"].get("grupa") == "add" else "DROP")
            nr_[c["viz"].get("grupa")] = nr_.get(c["viz"].get("grupa"), 0) + 1
            c["_tablo"] = {"lab": f"WE SAID {teica}", "liels": f"#{nr_[c['viz'].get('grupa')]}", "kr": kr_rez, "idx": i}
            c["_datums"] = f"WEEK OF {ned}"
            jaunas.append(c)
        runa_k = s["runa"][1:-1]
        s["intro"] = {"aki": True, "fantasy_aki": s["aki_f"], "tag": s["aki_f"]["tag"], "ilgums": 2.6, "_tv": tv}
        s["runa"] = [s["aki_runa"], s["runa"][0]] + runa_k + [s["runa"][-1]]
        s["kartes"] = jaunas
        s["_bez_zimoga"] = True
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (atskata jaunais izskats: {type(ex).__name__} – vecais)")
    return s


def aina_aki_fantasy(t, s):
    """Fantasy / streameru āķis. Pirmais kadrs jau ar galveno skaitli (Shorts plūsmai un cilpai)."""
    a_ = s["fantasy_aki"]
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    if s.get("_tv"):                                                  # tablo josla (kā kartītēs) – jau pirmajā kadrā
        _nv_tablo_virs(L, N, t, s["_tv"], anim=False)
    else:
        S.pill(d, 0, 250, a_["tag"], S.fonts("semi", 40), S.ZILS, S.MELNS, center=True)
    f_l = S.ietilpinat(d, a_["liels"], "black", 210, S.W - 120)
    dy0 = 190 if a_.get("bez_kartes") else 0                           # atskats: bez kartītes apakšā – saturs vidū
    _nv_put(L, _nv_timg(a_["liels"], f_l, S.BALTS), 540, 480 + dy0, 1 + 0.12 * (1 - S.ease(t / 0.2)))
    apli = a_.get("apli", [])
    n = len(apli)
    for i, txt in enumerate(apli):
        kk = (t - 0.15 - i * 0.08) / 0.22
        if kk <= 0:
            continue
        izc = i in a_.get("izcelt", [])
        cx, cy = 540 + (i - (n - 1) / 2) * 160, 705 + dy0
        r = (72 if izc else 60) * ease_back(kk)
        kr = tuple(a_["apli_kr"][i]) if a_.get("apli_kr") else (S.DZELTENS if izc else S.ZILS)
        dn.ellipse([cx - r, cy - r, cx + r, cy + r], fill=kr + (255,))
        if kk > 0.6:
            if txt == "✓":                                            # atskats: trāpīts / garām – figūras (fontā var nebūt)
                dn.line([(cx - 24, cy + 2), (cx - 7, cy + 20), (cx + 26, cy - 18)], fill=S.BALTS, width=12, joint="curve")
            elif txt == "✗":
                dn.line([(cx - 20, cy - 20), (cx + 20, cy + 20)], fill=S.BALTS, width=12)
                dn.line([(cx + 20, cy - 20), (cx - 20, cy + 20)], fill=S.BALTS, width=12)
            else:
                dn.text((cx, cy), txt, font=S.fonts("black", 58 if izc else 48), fill=S.MELNS, anchor="mm")
    _nv_put(L, _nv_timg(a_["zem"], S.fonts("black", 66), (203, 213, 225)), 540, 835 + dy0, 1, S.ease((t - 0.45) / 0.25))
    k = (t - 0.65) / 0.28
    if k > 0:                                                         # dzeltena josla "izbrauc"
        bar = Image.new("RGBA", (S.W, 170), (0, 0, 0, 0)); db = ImageDraw.Draw(bar)
        f_ = S.ietilpinat(db, a_["josla"], "black", 58, S.W - 220)
        tw = db.textlength(a_["josla"], font=f_) + 110; x0 = (S.W - tw) / 2
        db.polygon([(x0 + 32, 25), (x0 + tw, 25), (x0 + tw - 32, 135), (x0, 135)], fill=S.DZELTENS)
        db.text((S.W / 2, 80), a_["josla"], font=f_, fill=S.MELNS, anchor="mm")
        m = Image.new("L", (S.W, 170), 0); ImageDraw.Draw(m).rectangle([0, 0, S.W * S.ease(min(1, k)), 170], fill=255)
        from PIL import ImageChops
        bar.putalpha(ImageChops.multiply(bar.getchannel("A"), m))
        L.alpha_composite(bar, (0, 900 + dy0))
    k = (t - 0.85) / 0.3
    if k > 0 and not a_.get("bez_kartes"):                            # noslēpumainā kartīte: mirgojošs neona rāmis + kustīga "?"
        prim, _ = kom_krasas(a_.get("kom"))
        box = (190, 1130, 890, 1560)
        al = _nv_mirgo(t, 0.85)
        d.rounded_rectangle(box, radius=36, fill=(10, 14, 32, int(235 * S.ease(min(1, k)))))
        dn.rounded_rectangle(box, radius=36, outline=prim + (int(255 * al),), width=5)
        kt_ = a_.get("kart_txt", "#1")
        _nv_put(N, _nv_timg(kt_, S.ietilpinat(d, kt_, "black", 124, 600), S.DZELTENS), 540, 1230, 1, al)
        nm = Image.new("RGBA", (640, 130), (0, 0, 0, 0))
        ImageDraw.Draw(nm).text((320, 65), a_["vards"], font=S.ietilpinat(d, a_["vards"], "black", 100, 600), fill=S.BALTS, anchor="mm")
        _nv_put(L, nm.filter(ImageFilter.GaussianBlur(18)), 540, 1415, 1, S.ease(min(1, k)))
        if t > 1.15:                                                  # "?" lēni šūpojas kā svārsts (iekārts augšā), pamazām rimstas
            tau = t - 1.15
            th = 11 * math.exp(-0.18 * tau) * math.sin(2 * math.pi * tau / 2.0)          # leņķis grādos, periods 2 s
            _nv_put(N, _nv_timg("?", S.fonts("black", 150), S.DZELTENS), 540 + 2.2 * th, 1410 - 0.06 * th * th,
                    1, S.ease(tau / 0.25), th)
    L.alpha_composite(_nv_glow(N, 20, 1.4))
    return L


def _nv_zimoga_laiks(c):
    return max(3.2, c.get("_ilg", 6.5) - 1.9)


def _nv_datums(z):
    """'STATS THROUGH OCT 24, 2026  ·  ESPN ROSTERED % OCT 25' → 'STATS THRU OCT 24  ·  ESPN OCT 25'."""
    m = re.findall(r"\b([A-Z]{3} \d{1,2})\b", str(z or "").upper())
    if not m:
        return ""
    return f"STATS THRU {m[0]}" + (f"  ·  ESPN {m[1]}" if len(m) > 1 else "")


def _nv_tablo(L, N, t, c):
    """Kartītes augšā: tablo josla "PICKUP / #2" (akcenta krāsā), punkti – visas video kartītes (pašreizējā lielāka
    un pulsē, parādītās – pildītas, nākamās – tukši aplīši) un datums. Aizstāj zaļo zīmīti
    "PICKUP #2 · 6% ROSTERED (ESPN)" un pelēko rindu "STATS THROUGH …" (rostered % jau ir kartītes apakšā)."""
    a_ = str(c.get("augsa", "")).split("  ·  ")[0].strip()
    lab, _, nr = a_.rpartition("#")
    lab, nr = (lab.strip(), "#" + nr.strip()) if lab.strip() else (a_, "")
    tb = c.get("_tablo") or {}
    _nv_tablo_zim(L, N, t, tuple(c["akc"]), tb.get("lab", lab), tb.get("liels", nr), tb.get("kr") or [tuple(c["akc"])],
                  tb.get("idx", 0), c.get("_datums") or "")


def _nv_tablo_virs(L, N, t, tv, anim=True):
    """Ievada ainām (āķis, kārtis, grafiks): zila tablo josla, piem. "NHL · FANTASY / WAIVER WIRE" + tukši aplīši
    (cik kartīšu būs) + datums. tv = {"lab", "liels", "kr", "labaja"} (sagatavo fantasy_aki)."""
    _nv_tablo_zim(L, N, t, S.ZILS, tv["lab"], tv["liels"], tv.get("kr") or [], -1, tv.get("labaja", ""), anim)


def _nv_tablo_zim(L, N, t, akc, lab, liels, krasas, idx, labaja, anim=True):
    """Tablo josla kartītes platumā (ainas y 167–311): krāsains bloks ar mazo uzrakstu + lielo tekstu, labajā pusē
    punkti (idx – pašreizējā, -1 = neviena) un pelēks teksts (datums)."""
    from PIL import ImageChops
    akc = tuple(akc)
    d = ImageDraw.Draw(L)
    dn = ImageDraw.Draw(N) if N is not None else d
    x0, y0, x1, y1 = 70, 167, 1010, 311                                # ainas koordinātās (pēc drošās zonas ~154–926, 182–300)
    fl = S.ietilpinat(d, lab, "black", 37, 420)
    isais = len(liels) <= 4                                           # "#2" – liels; "WAIVER WIRE" – mazāks
    fb = S.fonts("black", 90) if isais else S.ietilpinat(d, liels, "black", 60, 400)
    xb = x0 + max(366, d.textlength(lab, font=fl) + 70, d.textlength(liels, font=fb) + 70)
    for pad, al_ in ((10, 22), (6, 45), (2, 80)):                       # mīksts spīdums (bez izpludināšanas – ātri)
        d.rounded_rectangle((x0 - pad, y0 - pad, x1 + pad, y1 + pad), radius=34 + pad, outline=akc + (al_,), width=pad + 2)
    d.rounded_rectangle((x0, y0, x1, y1), radius=34, fill=(10, 14, 32, 215))
    blk = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    ImageDraw.Draw(blk).polygon([(0, 0), (xb - x0 + 37, 0), (xb - x0 - 12, y1 - y0), (0, y1 - y0)], fill=akc + (255,))
    m = Image.new("L", blk.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, blk.width - 1, blk.height - 1], radius=34, fill=255)
    blk.putalpha(ImageChops.multiply(blk.getchannel("A"), m))
    L.alpha_composite(blk, (x0, y0))
    d.rounded_rectangle((x0, y0, x1, y1), radius=34, outline=akc + (210,), width=4)
    tk = S.MELNS if akc in (S.ZALS, S.DZELTENS, S.ZILS) else S.BALTS
    d.text((x0 + 32, y0 + 49), lab, font=fl, fill=tk, anchor="ls")
    if liels:
        d.text((x0 + (27 if isais else 30), y1 - (17 if isais else 26)), liels, font=fb, fill=tk, anchor="ls")
    sp, cy = 56, y0 + 54
    xs = x1 - 41 - (len(krasas) - 1) * sp
    for i, kr in enumerate(krasas):
        k = (t - 0.15 - i * 0.07) / 0.25 if anim else 1.0
        if k <= 0:
            continue
        cx, kr = xs + i * sp, tuple(kr)
        if i == idx:
            r = (18 + 2.5 * math.sin(t * 5)) * ease_back(min(1.0, k))
            dn.ellipse([cx - r - 9, cy - r - 9, cx + r + 9, cy + r + 9], fill=kr + (55,))
            dn.ellipse([cx - r, cy - r, cx + r, cy + r], fill=kr + (255,))
        else:
            r = 12 * ease_back(min(1.0, k))
            if 0 <= i < idx:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=kr + (150,))
            else:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=kr + (190 if idx < 0 else 170,), width=4)
    if labaja:
        x_min = xb + 60
        fd = S.ietilpinat(d, labaja, "semi", 29, max(120, x1 - 37 - x_min))
        d.text((x1 - 37, y1 - 24 if krasas else (y0 + y1) / 2 + 10), labaja, font=fd, fill=_NV_LAB, anchor="rs")


# ---------------------------------------------------------------- 2. aina: kārtis (vecā ievada vietā)
def _nv_kartis_dati(s, vecais):
    """Kāršu ainas dati no kartītēm un vecā ievada (nedēļa, rostered robeža, pagājušās nedēļas rezultāts)."""
    kar = [c for c in s["kartes"] if c.get("tips") == "fantasy" and c.get("viz")]
    if not kar:
        return None
    pk = [c for c in kar if c.get("liels") not in ("DROP", "BENCH")]
    dr = [c for c in kar if c.get("liels") in ("DROP", "BENCH")]
    kartis = []
    for grupa in (pk, dr):
        for j, c in enumerate(grupa, 1):
            v = c["viz"]
            ir_r = v.get("rost") is not None
            kartis.append({"kom": str(c.get("badge", "")), "poz": str(v.get("poz", "")), "akc": tuple(c["akc"]),
                           "liels": (f"{v['rost']:.0f}%" if v["rost"] >= 1 else f"{v['rost']:.1f}%") if ir_r else str(v.get("pts", "")),
                           "maz": "ROSTERED" if ir_r else "POINTS", "lab": f"{c.get('liels', 'ADD')} #{j}"})
    ap = [str(x) for x in (vecais or {}).get("apaksa", [])]
    ned = re.sub(r"^Week of\s+", "", ap[0]) if ap else ""
    ned = re.sub(r",\s*\d{4}$", "", ned).upper()
    ned = re.sub(r"\b([A-Z]{3}) (\d+) – \1 (\d+)\b", r"\1 \2 – \3", ned)
    mr = re.search(r"under (\d+)%", " ".join(ap))
    rr = re.search(r"Last week: (\d+)/(\d+)", " ".join(ap))
    stream = "STREAM" in str((vecais or {}).get("tag", "")).upper()
    return {"tips": "fantasy_kartis", "ilgums": 6.0, "tag": (vecais or {}).get("tag", "NHL  ·  FANTASY WAIVER WIRE"),
            "virsr": [("THIS", S.BALTS), ("WEEK'S", S.BALTS), ("STREAMS", S.DZELTENS)] if stream else
                     [("NEXT", S.BALTS), ("WEEK'S", S.BALTS), ("MOVES", S.DZELTENS)],
            "apaksa": "  ·  ".join(x for x in (ned, f"PICKUPS UNDER {mr[1]}% ROSTERED" if mr else "") if x),
            "kartis": kartis, "n_pick": len(pk), "rek": (int(rr[1]), int(rr[2])) if rr else None}


def _nv_vards_laiks(vardi, *meklet):
    """Pirmā vārda (vai vārdu virknes) sākuma laiks balsī; None, ja nav."""
    tiri = [re.sub(r"[^a-z0-9]", "", str(x).lower()) for _, _, x in vardi]
    for i in range(len(tiri) - len(meklet) + 1):
        if all(tiri[i + j] == m_ for j, m_ in enumerate(meklet)):
            return vardi[i][0]
    return None


def _nv_kartis_laiki(c):
    """(izdalīšana[], apgriešana[], čips) – pickup kārtis apgriežas uzreiz, drop kārtis – kad balss saka "plus",
    'LAST WEEK' čips – kad balss saka "Last week" (bez balss – pēc kārtas). Viss paspēj līdz ainas beigām."""
    K, npk = c["kartis"], c["n_pick"]
    ilg, vardi = c.get("_ilg", c.get("ilgums", 6.0)), c.get("_vardi") or []
    deal = [0.45 + i * 0.12 for i in range(len(K))]
    flip = [1.3 + i * 0.45 for i in range(npk)]
    if len(K) > npk:
        t_plus = _nv_vards_laiks(vardi, "plus")
        td = max((flip[-1] if flip else 0.85) + 0.55, t_plus or 0)
        flip += [td + j * 0.45 for j in range(len(K) - npk)]
    lim = ilg - 0.75
    if flip and flip[-1] + 0.36 > lim:                                 # saspiest, lai paspēj
        k = max(0.2, (lim - 0.36 - 1.3) / max(0.01, flip[-1] - 1.3))
        flip = [1.3 + (f - 1.3) * k for f in flip]
    cips = None
    if c.get("rek"):
        cips = min(max((flip[-1] if flip else 1.3) + 0.5, _nv_vards_laiks(vardi, "last", "week") or 0), max(lim, (flip[-1] if flip else 1.3) + 0.3))
    return deal, flip, cips


def _nv_karte_aizm(kr, w, h):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=(12, 18, 40, 255))
    for x in range(-h, w, 34):
        d.line([(x, h), (x + h, 0)], fill=kr + (22,), width=10)
    from PIL import ImageChops
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=255)
    im.putalpha(ImageChops.multiply(im.getchannel("A"), m))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28, outline=kr + (255,), width=6)
    d.text((w / 2, h / 2 - 10), "?", font=S.fonts("black", int(h * 0.41)), fill=kr, anchor="mm")
    return im


def _nv_karte_prieksa(p, w, h):
    from PIL import ImageChops
    prim, sek = kom_krasas(p["kom"])
    kr = tuple(p["akc"])
    k_ = h / 410
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=(12, 18, 40, 255))
    top = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dt = ImageDraw.Draw(top)
    for yy in range(int(190 * k_)):
        dt.line([(0, yy), (w, yy)], fill=prim + (int(255 * (1 - yy / (240 * k_))),))
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=28, fill=255)
    top.putalpha(ImageChops.multiply(top.getchannel("A"), m)); im.alpha_composite(top)
    d.text((w / 2, 92 * k_), p["kom"], font=S.ietilpinat(d, p["kom"], "black", int(104 * k_), w - 30), fill=S.BALTS, anchor="mm")
    d.text((w / 2, 166 * k_), p["poz"], font=S.fonts("black", int(38 * k_)), fill=S.BALTS, anchor="mm")
    d.text((w / 2, 252 * k_), p["liels"], font=S.ietilpinat(d, p["liels"], "black", int(88 * k_), w - 30), fill=S.BALTS, anchor="mm")
    d.text((w / 2, 310 * k_), p["maz"], font=S.fonts("semi", int(28 * k_)), fill=_NV_LAB, anchor="mm")
    d.rounded_rectangle([18, h - 72 * k_, w - 18, h - 18 * k_], radius=27 * k_, fill=kr)
    d.text((w / 2, h - 45 * k_), p["lab"], font=S.ietilpinat(d, p["lab"], "black", int(36 * k_), w - 60),
           fill=S.MELNS if kr in (S.ZALS, S.DZELTENS) else S.BALTS, anchor="mm")
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=28, outline=kr + (255,), width=6)
    return im


def _nv_rekords(L, rek, t, cy):
    """'LAST WEEK ✓✗✗✗ 1/4' čips (zaļa rūtiņa – trāpīts, sarkana – garām)."""
    k = t / 0.35
    if not rek or k <= 0:
        return
    tr, n = rek
    n_ = min(n, 8)
    fl, fr_ = S.fonts("black", 38), S.fonts("black", 44)
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    lw, rw = d0.textlength("LAST WEEK", font=fl), d0.textlength(f"{tr}/{n}", font=fr_)
    w = int(36 + lw + 24 + n_ * 56 + 14 + rw + 36)
    ch = Image.new("RGBA", (w, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(ch)
    d.rounded_rectangle([0, 0, w - 1, 95], radius=48, fill=(10, 14, 32, 235), outline=(255, 255, 255, 60), width=2)
    d.text((36, 48), "LAST WEEK", font=fl, fill=_NV_LAB, anchor="lm")
    for i in range(n_):
        x = 36 + lw + 24 + i * 56
        hit = i < tr
        d.rounded_rectangle([x, 26, x + 44, 70], radius=11, fill=(S.ZALS if hit else S.SARKANS) + (235,))
        if hit:
            d.line([(x + 11, 49), (x + 19, 58), (x + 34, 38)], fill=S.BALTS, width=6)
        else:
            d.line([(x + 13, 37), (x + 31, 59)], fill=S.BALTS, width=6)
            d.line([(x + 31, 37), (x + 13, 59)], fill=S.BALTS, width=6)
    d.text((w - 36, 48), f"{tr}/{n}", font=fr_, fill=S.BALTS, anchor="rm")
    _nv_put(L, ch, 540, cy, 1 + 0.4 * (1 - ease_back(min(1.0, k))), min(1.0, k * 2))


def aina_kartis(t, c):
    """2. aina jaunajā izskatā: virsraksts "NEXT WEEK'S MOVES", aizvērtas kārtis (zaļas – pickup, sarkanas – drop)
    tiek izdalītas un pa vienai apgriežas (komanda, pozīcija, rostered %, ADD/DROP #n); vārdi – noslēpums līdz kartītēm."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    _nv_dalinas(L, t)
    if c.get("_tv"):
        _nv_tablo_virs(L, N, t, c["_tv"])
    else:
        S.pill(d, 0, 250, c["tag"], S.fonts("semi", 40), S.ZILS, S.MELNS, center=True)
    # virsraksts – vārdi ielido pa vienam
    dalas = c["virsr"]
    f = S.ietilpinat(d, "  ".join(x for x, _ in dalas), "black", 130, 920)
    plat = [d.textlength(x, font=f) for x, _ in dalas]
    spr = d.textlength("  ", font=f)
    x = 540 - (sum(plat) + spr * (len(dalas) - 1)) / 2
    for i, ((txt, kr), w_) in enumerate(zip(dalas, plat)):
        k = (t - 0.05 - i * 0.18) / 0.3
        if k > 0:
            _nv_put(L, _nv_timg(txt, f, kr), x + w_ / 2, 400, 1 + 0.7 * (1 - ease_back(min(1.0, k), 2.0)), min(1.0, k * 2.5))
        x += w_ + spr
    a = S.ease(min(1.0, max(0.0, (t - 0.5) / 0.3)))
    if c.get("apaksa") and a > 0:
        S.teksts_c(d, 488, c["apaksa"], S.ietilpinat(d, c["apaksa"], "semi", 34, 900), _NV_LAB + (int(255 * a),))
    # kārtis: rindās pa 3 (pickup augšā, drop zem tām)
    K, npk = c["kartis"], c["n_pick"]
    rindas = [list(range(i, min(i + 3, npk))) for i in range(0, npk, 3)] + \
             [list(range(i, min(i + 3, len(K)))) for i in range(npk, len(K), 3)]
    nr_ = max(1, len(rindas))
    h = int(min(410, (880 - (nr_ - 1) * 30) / nr_)); w = int(min(296, h * 296 / 410))
    ya = 560 + max(0, 880 - nr_ * h - (nr_ - 1) * 30 - (130 if c.get("rek") else 0)) * 0.3    # viena rinda (streameri) – tuvāk vidum
    poz = {}
    for ri, rinda in enumerate(rindas):
        for j, i in enumerate(rinda):
            poz[i] = (540 + (j - (len(rinda) - 1) / 2) * (w + 28), ya + ri * (h + 30) + h / 2)
    deal, flip, cips = _nv_kartis_laiki(c)
    kesa = c.setdefault("_kesa", {})
    for i, p in enumerate(K):
        kd = (t - deal[i]) / 0.45
        if kd <= 0:
            continue
        cx, cy = poz[i]
        e = S.ease(min(1.0, kd))
        xx, yy = cx + (1 - e) * (i - 2) * 120, cy + (1 - e) * 900
        rot = (1 - ease_back(min(1.0, kd), 1.4)) * (14 if i % 2 else -14)
        kf = min(1.0, max(0.0, (t - flip[i]) / 0.36))
        sx = abs(math.cos(math.pi * kf))
        key = (i, kf >= 0.5, w, h)
        if key not in kesa:
            kesa[key] = _nv_karte_prieksa(p, w, h) if kf >= 0.5 else _nv_karte_aizm(tuple(p.get("aizm", p["akc"])), w, h)
        im = kesa[key].resize((max(2, int(w * sx)), int(h * (1 + 0.08 * math.sin(math.pi * kf)))), Image.BICUBIC)
        if abs(rot) > 0.05:
            im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
        L.alpha_composite(im, (int(xx - im.width / 2), int(yy - im.height / 2)))
        if kf >= 1:                                                     # atvērta – neona spīdums
            ImageDraw.Draw(N).rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=28,
                                                outline=tuple(p["akc"]) + (200,), width=6)
    out = _nv_glow(N, 22, 1.1)
    out.alpha_composite(L)
    if cips is not None:
        _nv_rekords(out, c["rek"], t - cips, max(poz.values(), key=lambda q: q[1])[1] + h / 2 + 90)
    return out


def _nv_flizes_atskats(dc, N, u, c, v, prim, ta, gk, t_at, flize, stabini, X0, X1, CW, GAP):
    """Atskata kartītes flīzes: PTS un SOG pa spēlēm, GAMES / PP PTS, viņš pret tipisko spēlētāju (kāpēc HIT / MISS),
    nedēļas kalendārs ar punktiem katrā spēlē, ESPN rostered kopš mūsu ieteikuma."""
    F, WH, LAB, SL, Y, G = S.fonts, S.BALTS, _NV_LAB, _NV_SL, S.DZELTENS, S.ZALS

    def eo(x):
        return S.ease(min(1.0, max(0.0, x)))
    drop = v.get("grupa") == "drop"
    gp = max(1, v.get("gp") or 0)
    # 1) PTS tajā nedēļā + punkti katrā spēlē
    x0, y0, x1, y1 = X0, 685, X0 + CW, 865; a = ta(y0)
    if a > 0:
        flize(x0, y0, x1, y1, "PTS", str(v["pts"]), a, v["ga"])
        stabini(x1, y1, v.get("p_sp") or [], a, t_at(y0 + 110), "BY GAME")
    # 2) SOG + metieni katrā spēlē
    x0, y0, x1, y1 = X0 + CW + GAP, 685, X1, 865; a = ta(y0)
    if a > 0:
        flize(x0, y0, x1, y1, "SOG", str(v["sog"]), a, f"{v['sog'] / gp:.1f} per game")
        stabini(x1, y1, v.get("s_sp") or [], a, t_at(y0 + 110) + 0.1, "BY GAME")
    # 3) spēles + PP punkti
    x0, y0, x1, y1 = X0, 880, X0 + CW, 1060; a = ta(y0)
    if a > 0:
        flize(x0, y0, x1, y1, "GAMES", str(v.get("gp", 0)), a, f"{v['pts'] / gp:.2f} pts per game")
    x0, y0, x1, y1 = X0 + CW + GAP, 880, X1, 1060; a = ta(y0)
    if a > 0:
        flize(x0, y0, x1, y1, "PP PTS", str(v.get("ppp", 0)), a, "on the power play")
    # 4) VIŅŠ pret tipisko spēlētāju tajā pašā grupā – kāpēc HIT / MISS
    x0, y0, x1, y1 = X0, 1075, X1, 1235; a = ta(y0); T1 = t_at(y0 + 100)
    if a > 0:
        dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
        dc.text((x0 + 22, y0 + 16), "VS TYPICAL " + ("ROSTERED" if drop else "WAIVER") + " PLAYER  ·  POINTS",
                font=F("semi", 28), fill=LAB + (int(255 * a),))
        rind = [("HIM", float(v["pts"]), prim, T1), ("TYPICAL", float(v["med"]), SL, T1 + 0.25)]
        skala = max(4.0, math.ceil(max(x_[1] for x_ in rind)) + 1)
        for jj, (lab, val, kr, t0_) in enumerate(rind):
            yy = y0 + 62 + jj * 48
            kk = eo(gk(t0_, 0.45))
            dc.text((x0 + 22, yy + 18), lab, font=F("semi", 28), fill=(203, 213, 225, int(255 * a)), anchor="lm")
            bx0, bw_ = x0 + 250, 480
            dc.rounded_rectangle([bx0, yy, bx0 + bw_, yy + 36], radius=18, fill=(255, 255, 255, int(18 * a)))
            if kk > 0:
                bx1 = bx0 + bw_ * val / skala * kk
                dc.rounded_rectangle([bx0, yy, max(bx0 + 36, bx1), yy + 36], radius=18, fill=kr + (int(255 * a),))
                dc.text((max(bx0 + 36, bx1) + 14, yy + 18), f"{val:.0f}", font=F("black", 32), fill=WH + (int(255 * a),), anchor="lm")
        dlt = v["pts"] - v["med"]
        kc = (u - T1 - 0.65) / 0.3
        if abs(dlt) >= 0.5 and kc > 0:
            labi = (dlt < 0) if drop else (dlt > 0)
            ch = Image.new("RGBA", (150, 50), (0, 0, 0, 0)); dch = ImageDraw.Draw(ch)
            dch.rounded_rectangle([0, 0, 149, 49], radius=25, fill=G if labi else S.SARKANS)
            dch.text((75, 25), ("+" if dlt > 0 else "−") + f"{abs(dlt):.0f}", font=F("black", 34), fill=S.MELNS if labi else WH, anchor="mm")
            _nv_put(N, ch, x1 - 95, y0 + 30, 1 + 0.6 * (1 - ease_back(min(1, kc))), min(1, kc * 3))
    # 5) NEDĒĻA – pretinieki un punkti katrā spēlē (zaļš – punkti, pelēks – 0)
    x0, y0, x1, y1 = X0, 1250, X1, 1425; a = ta(y0); T1 = t_at(y0 + 90)
    if a > 0:
        dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
        dc.text((x0 + 22, y0 + 16), v.get("ned_lab", "THAT WEEK"), font=F("semi", 28), fill=LAB + (int(255 * a),))
        bw, gap = 112, 10
        for i, dd in enumerate(v.get("ned") or []):
            kk = ease_back(gk(T1 + i * 0.06, 0.3))
            if kk <= 0:
                continue
            xx = x0 + 22 + i * (bw + gap); hh = 104 * kk; yb = y1 - 16
            spel = dd.get("o")
            fill = ((G if dd.get("p") else _NV_SL) + (230,)) if spel else (255, 255, 255, 12)
            dc.rounded_rectangle([xx, yb - hh, xx + bw, yb], radius=16, fill=fill)
            if kk > 0.7:
                tk_ = WH if spel else LAB
                dc.text((xx + bw / 2, yb - hh + 20), ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][i], font=F("black", 22), fill=tk_, anchor="mm")
                if spel:
                    dc.text((xx + bw / 2, yb - hh + 50), spel, font=S.ietilpinat(dc, spel, "semi", 24, bw - 10), fill=tk_, anchor="mm")
                    pt = f"{dd.get('p') or 0}P"
                    dc.text((xx + bw / 2, yb - 22), pt, font=F("black", 30), fill=WH, anchor="mm")
    # 6) ESPN ROSTERED – kopš mūsu ieteikuma
    x0, y0, x1, y1 = X0, 1440, X1, 1600; a = ta(y0); T1 = t_at(y0 + 80)
    rv = v.get("rost_vest") or []
    if a > 0 and v.get("rost") is not None:
        dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
        dc.text((x0 + 22, y0 + 16), "ROSTERED ON ESPN · SINCE OUR CALL", font=F("semi", 28), fill=LAB + (int(255 * a),))
        g_ = gk(T1, 0.9)
        r0 = rv[0][1] if len(rv) >= 2 else v["rost"]
        vv = r0 + (v["rost"] - r0) * eo(g_)
        dc.text((x0 + 22, y0 + 52), f"{vv:.1f}%", font=F("black", 60), fill=WH + (int(255 * a),))
        dlt = v["rost"] - r0
        kc = (u - T1 - 0.9) / 0.3
        if len(rv) >= 2 and abs(dlt) >= 0.1 and kc > 0:
            _nv_put(dc._image, _nv_timg(("▲ " if dlt > 0 else "▼ ") + f"{abs(dlt):.1f}", F("black", 34), G if dlt > 0 else S.SARKANS),
                    x0 + 200 + (20 if vv >= 10 else 0), y0 + 88, 1 + 0.5 * (1 - ease_back(min(1, kc))), min(1, kc * 3), 0, "l")
        if drop:
            txt = "leagues are dropping him too" if dlt <= -0.5 else "still widely rostered"
        else:
            txt = ("leagues followed our call" if dlt >= 2 else "leagues are starting to notice" if dlt >= 0.5
                   else "leagues are dropping him" if dlt <= -0.5 else "still under the radar")
        dc.text((x0 + 22, y1 - 12), txt, font=F("semi", 24), fill=LAB + (int(255 * a * eo(kc if kc > 0 else 0)),), anchor="lb")
        if len(rv) >= 2:
            px0, px1, py0, py1 = x1 - 400, x1 - 34, y0 + 58, y1 - 40
            lo_, hi_ = min(x_ for _, x_ in rv) - 0.15, max(x_ for _, x_ in rv) + 0.1
            pts = [(px0 + i * (px1 - px0) / (len(rv) - 1), py1 - (py1 - py0) * (x_ - lo_) / (hi_ - lo_)) for i, (_, x_) in enumerate(rv)]
            n = g_ * (len(pts) - 1); seg = [pts[0]]
            for i in range(1, len(pts)):
                if n >= i:
                    seg.append(pts[i])
                elif n > i - 1:
                    f_ = n - (i - 1)
                    seg.append((pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f_, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f_))
            if len(seg) > 1:
                dc.line(seg, fill=Y + (int(255 * a),), width=5, joint="curve")
            for i, (p_, (dl, _)) in enumerate(zip(pts, rv)):
                if n >= i - 0.01:
                    r_ = 10 if i == 0 else 8
                    dc.ellipse([p_[0] - r_, p_[1] - r_, p_[0] + r_, p_[1] + r_], fill=(Y if i == 0 else WH) + (int(255 * a),))
                dc.text((p_[0], y1 - 8), dl, font=F("semi", 20), fill=(Y if i == 0 else LAB) + (int(255 * a),), anchor="mb")


def _nv_flizes_spec(dc, N, u, c, v, prim, ta, gk, t_at, stabini, X0, X1, CW, GAP):
    """Vispārīgs flīžu zīmētājs (xG video un atskati): v["spec"] = 5 rindas – ("pair", flīze, flīze) vai ("full", flīze).
    Flīzes: skaitlis (+ stabiņi pa spēlēm / mērierīce), ripa (metienu karte), joslas (salīdzinājums, arī ap nulli),
    speles (spēle pa spēlei), rost (ESPN rostered tendence), teksts."""
    F, WH, LAB, SL, Y, G = S.fonts, S.BALTS, _NV_LAB, _NV_SL, S.DZELTENS, S.ZALS
    RINDAS = [(685, 865), (880, 1060), (1075, 1235), (1250, 1425), (1440, 1600)]

    def eo(x):
        return S.ease(min(1.0, max(0.0, x)))

    def kr_(k):
        return prim if k == "prim" else (SL if k in ("pel", None) else tuple(k))

    def pamats(x0, y0, x1, y1, a, lab):
        dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
        dc.text((x0 + 22, y0 + 16), lab, font=S.ietilpinat(dc, lab, "semi", 28, x1 - x0 - 44), fill=LAB + (int(255 * a),))

    def skaitlis(f, x0, y0, x1, y1, a):
        pamats(x0, y0, x1, y1, a, f["lab"])
        val = str(f.get("val", ""))
        vk_ = tuple(f["val_kr"]) if f.get("val_kr") else WH
        maxw = (x1 - x0) * (0.45 if (f.get("bars") or f.get("gauge")) else 0.85)
        dc.text((x0 + 22, y0 + 52), val, font=S.ietilpinat(dc, val, "black", 64, maxw), fill=vk_ + (int(255 * a),))
        if f.get("sub"):
            dc.text((x0 + 22, y1 - 46), f["sub"], font=S.ietilpinat(dc, f["sub"], "semi", 28, (x1 - x0) * (0.5 if f.get("gauge") else 0.9)),
                    fill=LAB + (int(255 * a),))
        T1 = t_at(y0 + 110)
        if f.get("bars"):
            stabini(x1, y1, f["bars"][-(5 if x1 - x0 < 600 else 9):], a, T1, f.get("bars_lab"))   # mazā flīzē ≤ 5 (nepārklāj skaitli)
        g = f.get("gauge")
        if g:
            cx, cy, r = x1 - 105, y1 - 50, 80
            dc.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=SL + (int(200 * a),), width=14)
            pc = float(g["frac"]) * eo(gk(T1, 0.7))
            if pc > 0.005:
                dc.arc([cx - r, cy - r, cx + r, cy + r], 180, 180 + 180 * pc, fill=Y + (int(255 * a),), width=14)
            if g.get("mark") is not None:                              # līgas vidējais – balta svītriņa
                am = math.radians(180 + 180 * float(g["mark"]))
                dc.line([(cx + (r - 14) * math.cos(am), cy + (r - 14) * math.sin(am)), (cx + (r + 12) * math.cos(am), cy + (r + 12) * math.sin(am))],
                        fill=WH + (int(255 * a),), width=4)
            ang = math.radians(180 + 180 * pc)
            dc.line([(cx, cy), (cx + (r - 24) * math.cos(ang), cy + (r - 24) * math.sin(ang))], fill=WH + (int(255 * a),), width=5)
            dc.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=WH + (int(255 * a),))
            dc.text((cx, cy + 24), g.get("txt", ""), font=F("semi", 20), fill=LAB + (int(255 * a),), anchor="mm")

    def ripa(f, x0, y0, x1, y1, a):
        h = y1 - y0 - 30
        w = h * 1.18
        dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
        dc.text((x0 + 22, y0 + 16), f["lab"], font=S.ietilpinat(dc, f["lab"], "semi", 28, x1 - x0 - w - 60), fill=LAB + (int(255 * a),))
        k = eo(gk(t_at(y0 + 100), 0.6))
        pk = f.get("punkti") or []
        n = int(len(pk) * k)
        _mini_laukums(dc, x1 - 18 - w, y0 + 15, w, h, pk[:n], tuple(f.get("varti_kr") or Y), a)
        for i, tx in enumerate(f.get("txt", [])):
            dc.text((x0 + 22, y0 + 66 + i * 40), tx, font=F("black" if i == 0 else "semi", 34 if i == 0 else 28),
                    fill=(WH if i == 0 else tuple(f.get("varti_kr") or Y)) + (int(255 * a),))

    def joslas(f, x0, y0, x1, y1, a):
        pamats(x0, y0, x1, y1, a, f["lab"])
        T1 = t_at(y0 + 100)
        rind = f["rind"]
        bx0, bw_ = x0 + 250, 480
        if f.get("diverg"):
            m_ = max(0.5, max(abs(float(r_[1])) for r_ in rind)) * 1.15
            cx_ = bx0 + bw_ / 2
            dc.line([(cx_, y0 + 56), (cx_, y1 - 12)], fill=(255, 255, 255, int(70 * a)), width=2)
        else:
            skala = max(4.0, math.ceil(max(float(r_[1]) for r_ in rind)) + 1)
        for jj, (lab, val, txt, kr) in enumerate(rind):
            yy = y0 + 62 + jj * 48
            kk = eo(gk(T1 + jj * 0.25, 0.45))
            dc.text((x0 + 22, yy + 18), lab, font=F("semi", 28), fill=(203, 213, 225, int(255 * a)), anchor="lm")
            dc.rounded_rectangle([bx0, yy, bx0 + bw_, yy + 36], radius=18, fill=(255, 255, 255, int(18 * a)))
            if kk <= 0:
                continue
            val = float(val)
            if f.get("diverg"):
                L_ = bw_ / 2 * min(1.0, abs(val) / m_) * kk
                if val >= 0:
                    xa, xb = cx_, cx_ + max(14, L_)
                    dc.rounded_rectangle([xa, yy, xb, yy + 36], radius=18, fill=kr_(kr) + (int(255 * a),))
                    dc.text((xb + 12, yy + 18), txt, font=F("black", 32), fill=WH + (int(255 * a),), anchor="lm")
                else:
                    xa, xb = cx_ - max(14, L_), cx_
                    dc.rounded_rectangle([xa, yy, xb, yy + 36], radius=18, fill=kr_(kr) + (int(255 * a),))
                    dc.text((xa - 12, yy + 18), txt, font=F("black", 32), fill=WH + (int(255 * a),), anchor="rm")
            else:
                bx1 = bx0 + bw_ * max(0.0, val) / skala * kk
                dc.rounded_rectangle([bx0, yy, max(bx0 + 36, bx1), yy + 36], radius=18, fill=kr_(kr) + (int(255 * a),))
                dc.text((max(bx0 + 36, bx1) + 14, yy + 18), txt, font=F("black", 32), fill=WH + (int(255 * a),), anchor="lm")
        ch_ = f.get("chip")
        kc = (u - T1 - 0.75) / 0.3
        if ch_ and kc > 0:
            krc = tuple(ch_[1])
            ch = Image.new("RGBA", (160, 50), (0, 0, 0, 0)); dch = ImageDraw.Draw(ch)
            dch.rounded_rectangle([0, 0, 159, 49], radius=25, fill=krc)
            dch.text((80, 25), ch_[0], font=S.ietilpinat(dch, ch_[0], "black", 34, 140), fill=S.MELNS if krc in (S.ZALS, S.DZELTENS) else WH, anchor="mm")
            _nv_put(N, ch, x1 - 100, y0 + 30, 1 + 0.6 * (1 - ease_back(min(1, kc))), min(1, kc * 3))

    def speles(f, x0, y0, x1, y1, a):
        pamats(x0, y0, x1, y1, a, f["lab"])
        T1 = t_at(y0 + 90)
        sp = f.get("speles") or []
        n = max(1, len(sp))
        gap = 10
        bw = min(112, (x1 - x0 - 44 - gap * (n - 1)) / n)
        xs0 = x0 + 22
        for i, dd in enumerate(sp):
            kk = ease_back(gk(T1 + i * 0.06, 0.3))
            if kk <= 0:
                continue
            xx = xs0 + i * (bw + gap); hh = 104 * kk; yb = y1 - 16
            fill = (tuple(dd["kr"]) + (230,)) if dd.get("kr") else (_NV_SL + (200,))
            dc.rounded_rectangle([xx, yb - hh, xx + bw, yb], radius=16, fill=fill)
            if kk > 0.7:
                dc.text((xx + bw / 2, yb - hh + 20), dd.get("aug", ""), font=S.ietilpinat(dc, dd.get("aug", ""), "black", 20, bw - 8), fill=WH, anchor="mm")
                dc.text((xx + bw / 2, yb - hh + 54), dd.get("vid", ""), font=S.ietilpinat(dc, dd.get("vid", ""), "black", 34, bw - 8), fill=WH, anchor="mm")
                dc.text((xx + bw / 2, yb - 16), dd.get("apa", ""), font=S.ietilpinat(dc, dd.get("apa", ""), "semi", 20, bw - 8), fill=WH, anchor="mm")

    def rost(f, x0, y0, x1, y1, a):
        rv = f.get("rost_vest") or []
        pamats(x0, y0, x1, y1, a, "ROSTERED ON ESPN" + (f" · LAST {len(rv)} DAYS" if len(rv) >= 2 else ""))
        T1 = t_at(y0 + 80)
        g_ = gk(T1, 0.9)
        r0 = rv[0][1] if len(rv) >= 2 else f["rost"]
        vv = r0 + (f["rost"] - r0) * eo(g_)
        dc.text((x0 + 22, y0 + 52), f"{vv:.1f}%", font=F("black", 60), fill=WH + (int(255 * a),))
        kc = (u - T1 - 0.9) / 0.3
        if f.get("tip") and kc > 0:
            dc.text((x0 + 22, y1 - 12), f["tip"], font=F("black", 26), fill=Y + (int(255 * a * eo(kc)),), anchor="lb")
        if len(rv) >= 2:
            px0, px1, py0, py1 = x1 - 400, x1 - 34, y0 + 58, y1 - 40
            lo_, hi_ = min(x_ for _, x_ in rv) - 0.15, max(x_ for _, x_ in rv) + 0.1
            pts = [(px0 + i * (px1 - px0) / (len(rv) - 1), py1 - (py1 - py0) * (x_ - lo_) / (hi_ - lo_)) for i, (_, x_) in enumerate(rv)]
            n = g_ * (len(pts) - 1); seg = [pts[0]]
            for i in range(1, len(pts)):
                if n >= i:
                    seg.append(pts[i])
                elif n > i - 1:
                    f_ = n - (i - 1)
                    seg.append((pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f_, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f_))
            if len(seg) > 1:
                dc.line(seg, fill=Y + (int(255 * a),), width=5, joint="curve")
            for i, (p_, (dl, _)) in enumerate(zip(pts, rv)):
                if n >= i - 0.01:
                    dc.ellipse([p_[0] - 8, p_[1] - 8, p_[0] + 8, p_[1] + 8], fill=WH + (int(255 * a),))
                dc.text((p_[0], y1 - 8), dl, font=F("semi", 20), fill=LAB + (int(255 * a),), anchor="mb")

    def teksts(f, x0, y0, x1, y1, a):
        pamats(x0, y0, x1, y1, a, f.get("lab", ""))
        val = str(f.get("val", ""))
        dc.text((x0 + 22, y0 + 54), val, font=S.ietilpinat(dc, val, "black", 54, x1 - x0 - 44), fill=Y + (int(255 * a),))
        if f.get("sub"):
            dc.text((x0 + 22, y1 - 40), f["sub"], font=S.ietilpinat(dc, f["sub"], "semi", 28, x1 - x0 - 44), fill=LAB + (int(255 * a),))

    zim = {"skaitlis": skaitlis, "ripa": ripa, "joslas": joslas, "speles": speles, "rost": rost, "teksts": teksts}
    for (y0, y1), rinda in zip(RINDAS, v.get("spec") or []):
        a = ta(y0)
        if a <= 0 or not rinda:
            continue
        if rinda[0] == "pair":
            for (x0, x1), f in zip(((X0, X0 + CW), (X0 + CW + GAP, X1)), rinda[1:3]):
                if f:
                    zim.get(f.get("tips"), teksts)(f, x0, y0, x1, y1, a)
        elif rinda[1]:
            zim.get(rinda[1].get("tips"), teksts)(rinda[1], X0, y0, X1, y1, a)


def aina_fantasy_jauna(t, c):
    v = c["viz"]
    u = t
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _nv_tablo(L, N, t, c)                                             # augšā: tablo josla (bija zaļā zīmīte + pelēkais datums)
    prim, sek = kom_krasas(c.get("badge"))
    F = S.fonts
    WH, LAB, SL, Y, G = S.BALTS, _NV_LAB, _NV_SL, S.DZELTENS, S.ZALS
    ease, eb = S.ease, ease_back

    def eo(x):
        return ease(min(1.0, max(0.0, x)))

    # --- vārds: komandas kods fonā + vārds + divkrāsu pasvītra "/"
    kw_ = eo(u / 0.6)
    _nv_put(L, _nv_timg(str(c.get("badge", "")), F("black", 300), prim + (55,)), 760 + (1 - kw_) * 160 - u * 6, 490, 1, kw_)
    ka = eo((u - 0.05) / 0.25)
    if c.get("v1"):
        _nv_put(L, _nv_timg(c["v1"].upper(), F("semi", 52), (255, 255, 255, 225)), 100 - (1 - ka) * 200, 445, 1, ka, 0, "l")
    vards = c["v2"].upper()
    fn = S.ietilpinat(d, vards, "black", 140, 880)
    x = 96
    for i, ch in enumerate(vards):
        kk = (u - 0.12 - i * 0.045) / 0.3
        im, dy_ = _nv_burts(ch, fn, WH)                               # visi burti uz vienas bāzes līnijas (Ä, ', J)
        if kk > 0:
            _nv_put(L, im, x + fn.getlength(ch) / 2, 540 + dy_ - (1 - eb(min(1, kk), 2.2)) * 140, 1, min(1, kk * 3))
        x += fn.getlength(ch)
    kp = eo((u - 0.3) / 0.45)
    if kp > 0:
        x0p, x1p, yp = 100, 980, 622
        xe = x0p + (x1p - x0p) * kp
        xs = x0p + (x1p - x0p) * 0.6
        d.polygon([(x0p, yp), (min(xe, xs + 8), yp), (min(xe, xs - 4), yp + 12), (x0p, yp + 12)], fill=prim)
        if xe > xs + 20:
            d.polygon([(xs + 20, yp), (xe, yp), (xe, yp + 12), (xs + 8, yp + 12)], fill=sek)
    al = eo((u - 0.4) / 0.3)
    if al > 0:
        d.text((980, 420), f"{v['poz']}  ·  {c.get('badge', '')}", font=F("black", 34), fill=LAB + (int(255 * al),), anchor="ra")
    # --- logs, kas plūdeni izrullējas
    U0, U1, YA, YB = 0.45, 2.0, 700, 1625

    def edge(uu):
        k_ = min(1.0, max(0.0, (uu - U0) / (U1 - U0)))
        return YA + (YB - YA) * k_ * k_ * (3 - 2 * k_)

    def t_at(y):
        lo, hi = U0, U1
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if edge(mid) < y else (lo, mid)
        return hi
    yb_ = edge(u) if u > U0 else 660
    box = (70, 660, 1010, yb_)
    kw = eo((u - 0.45) / 0.25)
    C = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dc = ImageDraw.Draw(C)
    if kw > 0 and yb_ > 690:
        for pad, al_ in ((12, 22), (7, 45), (3, 80)):                   # mīksts spīdums ap rāmi (bez izpludināšanas – ātri)
            d.rounded_rectangle((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad), radius=36 + pad,
                                outline=prim + (int(al_ * kw),), width=pad + 2)
        d.rounded_rectangle(box, radius=36, fill=(10, 14, 32, int(240 * kw)))
        d.rounded_rectangle(box, radius=36, outline=prim + (int(230 * kw),), width=5)
        if u > 0.9:
            _nv_divas_gaismas(dn, box, u, c, prim, sek)
    X0, X1, GAP = 100, 980, 20
    CW = (X1 - X0 - GAP) / 2

    def ta(y0):
        return eo((yb_ - y0 - 10) / 130)

    def gk(t0, dur=0.6):
        return min(1.0, max(0.0, (u - t0) / dur))

    def flize(x0, y0, x1, y1, lab, val, a, sub=None, sub_kr=None):
        dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
        dc.text((x0 + 22, y0 + 16), lab, font=F("semi", 28), fill=LAB + (int(255 * a),))
        dc.text((x0 + 22, y0 + 52), val, font=S.ietilpinat(dc, val, "black", 64, 230), fill=WH + (int(255 * a),))
        if sub:
            dc.text((x0 + 22, y1 - 46), sub, font=F("semi", 28), fill=(sub_kr or LAB) + (int(255 * a),))

    def stabini(x1, y1, vert, a, T1, lab_=None):
        if not vert:
            return
        bw, gap, base, mx = 30, 12, y1 - 38, 84
        bx = x1 - 22 - len(vert) * bw - (len(vert) - 1) * gap
        mxv = max(max(vert), 1)
        for i, p in enumerate(vert):
            kk = eb(gk(T1 + i * 0.08, 0.35))
            hh = max(8, mx * p / max(3, mxv) * kk) if kk > 0 else 0
            if hh:
                dc.rounded_rectangle([bx + i * (bw + gap), base - hh, bx + i * (bw + gap) + bw, base], radius=8,
                                     fill=(Y if p == mxv and p > 0 else SL) + (int(255 * a),))
                if kk > 0.8:
                    dc.text((bx + i * (bw + gap) + bw / 2, base - hh - 16), str(p) if float(p).is_integer() else f"{p:.1f}",
                            font=F("black", 24), fill=WH + (int(255 * a),), anchor="mm")
        dc.text((x1 - 22, y1 - 14), lab_ or f"LAST {len(vert)} GP", font=F("semi", 20), fill=LAB + (int(255 * a),), anchor="rb")

    if v.get("spec"):                                                 # xG video / xG atskats – vispārīgās flīzes
        _nv_flizes_spec(dc, N, u, c, v, prim, ta, gk, t_at, stabini, X0, X1, CW, GAP)
    elif not v.get("atskats"):                                        # fantasy / streameri (ieteikums)
        # 1) PTS
        x0, y0, x1, y1 = X0, 685, X0 + CW, 865; a = ta(y0)
        if a > 0:
            flize(x0, y0, x1, y1, "PTS", str(v["pts"]), a, v["ga"])
            stabini(x1, y1, v["p5"], a, t_at(y0 + 110))
        # 2) SOG / GP
        x0, y0, x1, y1 = X0 + CW + GAP, 685, X1, 865; a = ta(y0)
        if a > 0:
            flize(x0, y0, x1, y1, "SOG / GP", v["sog_gp"], a, v["sog60"])
            stabini(x1, y1, v["s5"], a, t_at(y0 + 110) + 0.1)
        # 3) spēlētāja stiprākais rādītājs (HD iespējas / ixG / metieni) – procentile savā grupā
        x0, y0, x1, y1 = X0, 880, X0 + CW, 1060; a = ta(y0)
        if a > 0:
            h = v["hd"]
            flize(x0, y0, x1, y1, h["lab"], h["val"], a, h["sub"])
            if h.get("pct") is not None:
                cx, cy, r = x1 - 105, y1 - 50, 80
                dc.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=SL + (int(200 * a),), width=14)
                pc = h["pct"] / 100 * eo(gk(t_at(y0 + 110), 0.7))
                if pc > 0.005:
                    dc.arc([cx - r, cy - r, cx + r, cy + r], 180, 180 + 180 * pc, fill=Y + (int(255 * a),), width=14)
                ang = math.radians(180 + 180 * pc)
                dc.line([(cx, cy), (cx + (r - 24) * math.cos(ang), cy + (r - 24) * math.sin(ang))], fill=WH + (int(255 * a),), width=5)
                dc.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=WH + (int(255 * a),))
                dc.text((cx, cy + 24), h["pct_txt"], font=F("semi", 22), fill=LAB + (int(255 * a),), anchor="mm")
        # 4) PP PTS – tikai skaitlis
        x0, y0, x1, y1 = X0 + CW + GAP, 880, X1, 1060; a = ta(y0)
        if a > 0:
            flize(x0, y0, x1, y1, "PP PTS", str(v["ppp"]), a, f"last {v['dienas']} days")
        # 5) ICE TIME – agrāk pret pēdējām N dienām
        x0, y0, x1, y1 = X0, 1075, X1, 1235; a = ta(y0); T1 = t_at(y0 + 100)
        if a > 0:
            dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
            dc.text((x0 + 22, y0 + 16), "ICE TIME PER GAME", font=F("semi", 28), fill=LAB + (int(255 * a),))
            rind = ([("EARLIER", v["toi_vec"], SL, T1)] if v.get("toi_vec") else []) + [(f"LAST {v['dienas']} DAYS", v["toi"], prim, T1 + 0.25)]
            skala = max(22.0, math.ceil(max(x_[1] for x_ in rind)) + 1)
            for jj, (lab, mins, kr, t0_) in enumerate(rind):
                yy = y0 + 62 + jj * 48 + (24 if len(rind) == 1 else 0)
                kk = eo(gk(t0_, 0.45))
                dc.text((x0 + 22, yy + 18), lab, font=F("semi", 28), fill=(203, 213, 225, int(255 * a)), anchor="lm")
                bx0, bw_ = x0 + 250, 480
                dc.rounded_rectangle([bx0, yy, bx0 + bw_, yy + 36], radius=18, fill=(255, 255, 255, int(18 * a)))
                if kk > 0:
                    bx1 = bx0 + bw_ * mins / skala * kk
                    dc.rounded_rectangle([bx0, yy, max(bx0 + 36, bx1), yy + 36], radius=18, fill=kr + (int(255 * a),))
                    dc.text((bx1 + 14, yy + 18), S._mmss(mins), font=F("black", 32), fill=WH + (int(255 * a),), anchor="lm")
            if v.get("toi_vec") and abs(v["toi"] - v["toi_vec"]) >= 0.5:
                dlt = v["toi"] - v["toi_vec"]
                kc = (u - T1 - 0.65) / 0.3
                if kc > 0:
                    ch = Image.new("RGBA", (170, 50), (0, 0, 0, 0)); dch = ImageDraw.Draw(ch)
                    dch.rounded_rectangle([0, 0, 169, 49], radius=25, fill=G if dlt > 0 else S.SARKANS)
                    dch.text((85, 25), ("+" if dlt > 0 else "−") + S._mmss(dlt), font=F("black", 34), fill=S.MELNS if dlt > 0 else WH, anchor="mm")
                    _nv_put(N, ch, x1 - 105, y0 + 30, 1 + 0.6 * (1 - eb(min(1, kc))), min(1, kc * 3))
        # 6) NEDĒĻA – kalendārs ar pretiniekiem (zaļš – vāja aizsardzība, pelēks – vidēja, sarkans – stipra)
        x0, y0, x1, y1 = X0, 1250, X1, 1425; a = ta(y0); T1 = t_at(y0 + 90)
        if a > 0:
            dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
            dc.text((x0 + 22, y0 + 16), v["ned_lab"], font=F("semi", 28), fill=LAB + (int(255 * a),))
            bw, gap = 112, 10
            for i, dd in enumerate(v["ned"]):
                kk = eb(gk(T1 + i * 0.06, 0.3))
                if kk <= 0:
                    continue
                xx = x0 + 22 + i * (bw + gap); hh = 104 * kk; yb = y1 - 16
                if dd["o"]:
                    fill = tuple(dd["kr"]) + (110 if dd["pag"] else 230,)
                else:
                    fill = (255, 255, 255, 8 if dd["pag"] else 16)
                dc.rounded_rectangle([xx, yb - hh, xx + bw, yb], radius=16, fill=fill)
                if kk > 0.7:
                    tk_ = WH if dd["o"] and not dd["pag"] else LAB
                    dc.text((xx + bw / 2, yb - hh + 26), ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][i], font=F("black", 24), fill=tk_, anchor="mm")
                    if dd["o"]:
                        dc.text((xx + bw / 2, yb - 30), dd["o"], font=S.ietilpinat(dc, dd["o"], "black", 28, bw - 10), fill=tk_, anchor="mm")
        # 7) ESPN ROSTERED – tendence pēdējās dienās
        x0, y0, x1, y1 = X0, 1440, X1, 1600; a = ta(y0); T1 = t_at(y0 + 80)
        rv = v.get("rost_vest") or []
        if a > 0 and v.get("rost") is not None:
            dc.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(255 * a),))
            dc.text((x0 + 22, y0 + 16), f"ROSTERED ON ESPN" + (f" · LAST {len(rv)} DAYS" if len(rv) >= 2 else ""),
                    font=F("semi", 28), fill=LAB + (int(255 * a),))
            g_ = gk(T1, 0.9)
            r0 = rv[0][1] if len(rv) >= 2 else v["rost"]
            vv = r0 + (v["rost"] - r0) * eo(g_)
            dc.text((x0 + 22, y0 + 52), f"{vv:.1f}%", font=F("black", 60), fill=WH + (int(255 * a),))
            dlt = v["rost"] - r0
            kc = (u - T1 - 0.9) / 0.3
            if len(rv) >= 2 and abs(dlt) >= 0.1 and kc > 0:
                _nv_put(C, _nv_timg(("▲ " if dlt > 0 else "▼ ") + f"{abs(dlt):.1f}", F("black", 34), G if dlt > 0 else S.SARKANS),
                        x0 + 200 + (20 if vv >= 10 else 0), y0 + 88, 1 + 0.5 * (1 - eb(min(1, kc))), min(1, kc * 3), 0, "l")
            if c.get("liels") in ("DROP", "BENCH"):
                txt = "leagues are dropping him" if dlt <= -0.5 else "still widely rostered"
            else:
                txt = "leagues are starting to notice" if dlt >= 0.5 else ("leagues are dropping him" if dlt <= -0.5 else "still under the radar")
            dc.text((x0 + 22, y1 - 12), txt, font=F("semi", 24), fill=LAB + (int(255 * a * eo(kc if kc > 0 else 0)),), anchor="lb")
            if len(rv) >= 2:
                px0, px1, py0, py1 = x1 - 400, x1 - 34, y0 + 58, y1 - 40          # zem virsraksta rindas
                lo_, hi_ = min(x_ for _, x_ in rv) - 0.15, max(x_ for _, x_ in rv) + 0.1
                pts = [(px0 + i * (px1 - px0) / (len(rv) - 1), py1 - (py1 - py0) * (x_ - lo_) / (hi_ - lo_)) for i, (_, x_) in enumerate(rv)]
                n = g_ * (len(pts) - 1); seg = [pts[0]]
                for i in range(1, len(pts)):
                    if n >= i:
                        seg.append(pts[i])
                    elif n > i - 1:
                        f_ = n - (i - 1)
                        seg.append((pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f_, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f_))
                if len(seg) > 1:
                    dc.line(seg, fill=Y + (int(255 * a),), width=5, joint="curve")
                for i, (p_, (dl, _)) in enumerate(zip(pts, rv)):
                    if n >= i - 0.01:
                        dc.ellipse([p_[0] - 8, p_[1] - 8, p_[0] + 8, p_[1] + 8], fill=WH + (int(255 * a),))
                    dc.text((p_[0], y1 - 8), dl, font=F("semi", 20), fill=LAB + (int(255 * a),), anchor="mb")
    else:                                                             # fantasy atskats: kā viņam gāja tajā nedēļā
        _nv_flizes_atskats(dc, N, u, c, v, prim, ta, gk, t_at, flize, stabini, X0, X1, CW, GAP)
    if yb_ > 690 and yb_ >= YB - 0.5:
        L.alpha_composite(C)                                          # izrullēts – maska nav vajadzīga
    elif yb_ > 690:
        from PIL import ImageChops
        m = Image.new("L", (S.W, S.H), 0)
        ImageDraw.Draw(m).rounded_rectangle([box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 6], radius=min(32, (yb_ - 670) / 2), fill=255)
        C.putalpha(ImageChops.multiply(C.getchannel("A"), m))
        L.alpha_composite(C)
    # --- verdikta zīmogs virsū kartītei
    tz = _nv_zimoga_laiks(c)
    k = (u - tz) / 0.24
    if k > 0:
        akc = tuple(c["akc"])
        st = Image.new("RGBA", (680, 200), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
        ds.rounded_rectangle([8, 8, 672, 192], radius=26, fill=(10, 14, 32, 215), outline=akc, width=12)
        ds.text((340, 100), c["liels"], font=S.ietilpinat(ds, c["liels"], "black", 124, 600), fill=akc, anchor="mm")
        _nv_put(N, st, 540, 1140, 1 + 1.5 * (1 - eo(k)), min(1, k * 3), 8)
    L.alpha_composite(N)
    if k > 0:
        _nv_zibsnis(L, u, tz + 0.24)
        L = _nv_kratit(L, u, tz + 0.24)
    return L


if __name__ == "__main__":
    ieslegt()
    print(f"STILS {STILS}: STORY")
    rc = S.main()
    if FAKTI_PAPILDU.get("fakti"):
        pierakstit_papildu_faktus(_arg("--mape", os.path.join(S.BASE, "video")))
    sys.exit(rc)
