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
  • āķis pirmajās ~3 s – NOSLĒPUMA ĀĶIS (kopš 04.11.2026): krekla siluets ar "?", 2 jautājumi, glitch ar komandas
    mājienu; vecais āķis (skaitlis + izpludināts #1) – --bez-noslepuma. Secība #3 → #1, cilpa beigās ("…remember the name.")
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
    (ja atskatam savu nav – tie paši faili, ko parastajam šī veida video: speletaji_ / xg_, fantasy_),
    visi_1.mp4 (vai jebkurš cits nosaukums) – der jebkuram veidam, kam nav savu failu.
  Ja veidam ir vairāki faili, tie tiek ņemti pēc kārtas (1, 2, 3, 1 ...); kārta saglabājas
  video\\shorts_mediji.json. Ja nav ne sava, ne visi_ faila – fons paliek krāsainais / bez mūzikas.
  shorts_sfx\\      (nav obligāti) swoosh.mp3 / boom.mp3 / tick.mp3 – aizstāj skripta ģenerētos efektus.
  shorts_logo.png      kanāla ikona (caurspīdīga) – pirmajā ainā ar @rokturi (galvene), tad tā pati ripa (watermark).
  shorts_wordmark.png  logo ar nosaukumu (caurspīdīgs) – beigu kadrā. Ja failu nav, rāda tikai @rokturi.
  Rokturis pēc noklusējuma: KANALS_NOKL (zemāk); --kanals @cits to aizstāj.
Papildu parametri: --bez-fona-video  --bez-muzikas  --bez-sfx  --bez-logo
  --tests    video un vēstures – mapē video_test\\ (īstā vēsture video\\ netiek aiztikta)
  --vecais   vecais izskats (līdz 04.11.) – rezerve, ja jaunajā izskatā kāda kļūda

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

from PIL import Image, ImageChops, ImageDraw, ImageFilter

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


VEIDI_PREFIKSI = ("speletaji", "komandas", "vartsargi", "fantasy", "streameri", "fakts", "tiesnesi", "atskats", "visi", "serijas",
                  "xg", "fakti")
MEDIJU_VESTURE = "shorts_mediji.json"
MEDIJI_JSON = "video_info.json"   # video\ mapē – visu ģenerēto video saraksts: datums, nosaukums, fons, mūzika (Content ID claim gadījumam)
_IZMANTOTS = {"muzika": None}
SIKTS = {"kods": None}            # --sikts A/B/D/E/F/J/K (0 = vecais) – sīktēla izkārtojums ar roku; citādi sikteli.py izvēlas pats
XG_VEIDI = ("speletaji", "komandas", "vartsargi")      # xG video – izmanto speletaji_ failus (ja nav savu komandas_ / vartsargi_)


def _arg(nos, nokl=None):
    return sys.argv[sys.argv.index(nos) + 1] if nos in sys.argv and sys.argv.index(nos) + 1 < len(sys.argv) else nokl


def _parastas_atslegas(veids):
    """Failu nosaukumu sākumi parastajam (ne atskata) video, svarīgākais pirmais."""
    if veids in XG_VEIDI:                                             # komandas / vartsargi → kā spēlētājiem, tad xg_
        return ([veids] if veids != "speletaji" else []) + ["speletaji", "xg", "visi"]
    if veids == "streameri":                                          # streameri → tie paši faili kā fantasy
        return [veids, "fantasy", "visi"]
    if veids == "fakts":                                              # fakti_ (kā mūzikai) vai vecais fakts_
        return ["fakti", "fakts", "visi"]
    if veids == "serijas":                                            # Streak watch – savi serijas_, citādi kā faktiem
        return ["serijas", "fakti", "fakts", "visi"]
    return [veids, "visi"]


def veida_atslegas():
    """Kuri failu nosaukumu sākumi der šim video, svarīgākais pirmais.
    Atskats: vispirms savi (atskats_<veids>_, atskats_), tad – TIEŠI tie paši, ko parastajam šī veida video.
    Piem. xG atskats par vārtsargiem: ['atskats_vartsargi', 'atskats_speletaji', 'atskats',
                                        'vartsargi', 'speletaji', 'xg', 'visi']."""
    ats = _arg("--atskats")
    if not ats:
        return _parastas_atslegas(_arg("--veids", "speletaji"))
    veids = ""
    try:
        import json
        js = ats
        if os.path.isdir(ats):
            js = os.path.join(ats, sorted(f for f in os.listdir(ats) if f.endswith(".json") and f != MEDIJI_JSON)[0])
        veids = json.load(open(js, encoding="utf-8")).get("veids", "")
    except Exception:                                                 # noqa: BLE001
        pass
    a_ = [f"atskats_{veids}"] if veids else []
    if veids in XG_VEIDI and veids != "speletaji":
        a_.append("atskats_speletaji")
    a_.append("atskats")
    for x in (_parastas_atslegas(veids) if veids else ["visi"]):     # līdz 04.11.: xG atskatam trūka speletaji_ → fona nebija
        if x not in a_:
            a_.append(x)
    return a_


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
    if _NS_SFX.get("ev"):                                             # noslēpuma āķim
        out.update({"riser": _sfx_riser(), "glitch": _sfx_glitch(0.3), "glitch_mazs": _sfx_glitch(0.09, 3),
                    "trieciens": _sfx_trieciens(), "sirds": _sfx_sirds(), "klik": _sfx_klik()})
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
        if nr > 0 and not (nr == 1 and _NS_SFX.get("ev")) and not (veids == "outro" and c and c.get("iss")):   # pēc āķa – swoosh jau ir
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
        if nr == 0 and veids == "intro" and _NS_SFX.get("ev"):          # noslēpuma āķis: savi efekti pēc balss
            ev += [(t0 + a_, e_, g_) for a_, e_, g_ in _NS_SFX["ev"]]
            t0 += ilg
            continue
        if nr == 0:
            ev.append((t0, "boom", 0.9))
            if veids == "intro":
                ev.append((t0 + 0.5, "tick", 0.9))
        if tips == "fakts_hook":
            ev.append((t0 + 1.0, "tick", 0.9))
        elif tips in ("intro", "fantasy_intro"):
            ev.append((t0 + 1.0, "tick", 0.9))
        elif tips == "fakts_tablo" and c.get("izk") == "A" and len(c.get("fakti") or []) > 1:   # rinda izplešas / saplok
            _to, _tc = _fja_laiki(c)
            ev.append((t0 + _to, "tick", 0.8))
            if _tc is not None:
                ev.append((t0 + _tc + 0.4, "boom", 0.45))
        elif tips == "fakts_tablo":                                  # kartīte ielido (tick), nolaižas tablo (boom)
            ev.append((t0 + 0.15, "tick", 0.8))
            ev.append((t0 + max(0.8, ilg - 0.8 + 0.4), "boom", 0.45))
        elif tips == "fakts_ripa":                                   # tick katrai ripai
            n_ = len(c["ripa"]["punkti"]); dt_ = _fj_ripa_dt(ilg, n_)
            ev += [(t0 + 0.9 + i * dt_ + 0.35, "tick", 0.55) for i in range(min(n_, 40))]
        elif tips == "fakts_hist":
            nb = len(c["hist"]["bins"])
            ev += [(t0 + 0.9 + i * 0.14, "tick", 0.5) for i in range(nb)]
            ev.append((t0 + 0.9 + nb * 0.14 + 1.0, "boom", 0.7))
        elif tips == "fakts_hc":                                     # tick katrai rindai + sērija bez vārtiem
            n_ = max([len(k_.get("rindas") or []) for k_ in c.get("kol") or []] + [1])
            ev += [(t0 + 0.6 + i * 0.22, "tick", 0.5) for i in range(n_)]
            if c.get("sausums"):
                ev.append((t0 + 0.6 + 0.22 * n_ + 0.25, "tick", 0.7))
        elif tips == "fakts_ga_serijas":                             # tick katrai rindai (garākā kolonna)
            n_ = max([len(k_.get("rindas") or []) for k_ in c.get("kol") or []] + [0])
            ev += [(t0 + 0.6 + i * 0.2, "tick", 0.5) for i in range(n_)]
        elif tips == "fakts_serijas":                                # tick katrai rindai
            n_ = min(8, len(c.get("rindas") or []))
            ev += [(t0 + 0.6 + i * (0.22 if n_ <= 5 else 0.15), "tick", 0.5) for i in range(n_)]
        elif tips == "fakts_reti":                                   # kartīte (tick), skaitlis (tick), zīmogs (boom)
            ev += [(t0 + 0.4, "tick", 0.5), (t0 + 0.8, "tick", 0.6)]
            if len(c.get("konteksts") or []) > 1:
                ev.append((t0 + 1.75, "boom", 0.7))
        elif tips == "fakts_nak_j":
            ev.append((t0 + 1.3, "boom", 0.6))
        elif tips == "xg_karte":                                     # līgas karte: tick katram izceltajam
            ev += [(t0 + 1.95 + 0.22 * j, "tick", 0.7) for j in range(len(c.get("izcelti", [])))]
        elif tips == "fantasy_divi":                                  # īsā versija: 2 DROP kartītes – ielido (swoosh), zīmogs (boom)
            _ti, _ts = _nv_divi_laiki(c)
            ev += [(t0 + x_, "swoosh", 0.4) for x_ in _ti] + [(t0 + x_ + 0.24, "boom", 0.6) for x_ in _ts]
        elif tips == "fantasy_ats_saraksts":                          # fantasy atskats, 2. aina: ✓/✗ rūtiņas, rindas, zīmogi
            _tt, _ti, _ts = _fa_s2_laiki(c)
            _rk = c.get("rek") or (0, 0)
            ev += [(t0 + _tt + 0.2 + 0.13 * j_ + 0.05, "tick", 0.5) for j_ in range(min(6, _rk[1]))]
            if _ti:
                ev.append((t0 + _ti[0], "swoosh", 0.45))
            ev += [(t0 + x_ + 0.05, "tick", 0.6) for x_ in _ts]
        elif tips in ("fantasy_saraksts", "fantasy_kalendars"):     # īsā versija, 2. aina: rindas, poga / dienas, zaļās
            _ti, _tk, _tz = _iss_s2_laiki(c)
            if _ti:
                ev.append((t0 + _ti[0], "swoosh", 0.45))
            if tips == "fantasy_saraksts":
                _sp = c.get("speletaji") or []
                _d0 = next((x_ for x_, p_ in zip(_ti, _sp) if p_["drop"]), None)
                if _d0 is not None:
                    ev.append((t0 + _d0, "swoosh", 0.35))
                ev += [(t0 + x_ + 0.3, "tick", 0.55) for x_ in _ti]
            else:
                ev += [(t0 + _tk + 0.1 * j_ + 0.05, "tick", 0.4) for j_ in range(7)]
            ev.append((t0 + _tz, "tick", 0.7))
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
                 "fakts": "fakti", "tiesnesi": "tiesnesi", "serijas": "fakti"}
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
            js = os.path.join(ats, sorted(f for f in os.listdir(ats) if f.endswith(".json") and f != MEDIJI_JSON)[0])
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
        _IZMANTOTS["muzika"] = f_
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
    _IZMANTOTS["muzika"] = os.path.join(MAPE_MUZIKA, izv)
    return _IZMANTOTS["muzika"]


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
                    "On the season: " + ", ".join(f"{r_[0]} has " + re.sub(r"\b1 (goal|assist)s\b", r"1 \1",
                                                                       r_[2].replace("G ", " goals and ").replace("A", " assists"))
                                                  for r_ in rindas) + ".")
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
    manuali = arg.endswith("!")                                       # "--fakts 8,1,2!" – secība tieši tāda (pirmais = #1)
    arg = arg.rstrip("!")
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
    if arg.startswith("top"):                                         # topN: katrs faktu veids TIKAI VIENREIZ (kopš 11.11.2026 –
        izv, kat = [], set()                                          # ne divi vārtsargi; ja veidu mazāk – mazāk faktu)
        for solis in (1, 2):           # 1) ne-ikdienišķie  2) arī ikdienišķie (ja dažādu veidu vēl trūkst)
            for c in kand:
                if len(izv) >= len(idx) or c in izv:
                    continue
                k_ = _kategorija(c)
                if k_ in kat or (solis == 1 and c.get("biezi")):
                    continue
                kat.add(k_)
                izv.append(c)
        if len(izv) < len(idx):
            print(f"TOP {len(idx)}: tikai {len(izv)} dažādi faktu veidi – video ar {len(izv)} faktiem (katrs veids – vienreiz)")
    else:
        izv = [kand[i] for i in idx if i < len(kand)]
    if manuali:
        return izv
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


FAKTI_BEZ_SERIJAM = True         # kopš 11.11.2026: faktos nav sēriju (punktu, vārtu, piespēļu, komandu uzvaru / zaudējumu)
                                 # – tās ir sestdienas Streak watch video; faktos – tikai nedēļas notikumi


def _fakts_ir_serija(c):
    k_ = str(c.get("atsl", "")).split(":")[0]
    return k_.endswith("_serija") or k_ in ("kom_uzv", "kom_zaud")


FAKTI_TOPN_IEVADS = ["The NHL week in numbers: {n} stats that stood out.", "{N} numbers from this NHL week.",
                     "This week's {n} wildest NHL stats.", "The NHL week, in {n} numbers."]


def veids_fakti_b(m, a):
    D = S.fakti_dati(a.lidz)
    kand = S.fakti_kandidati(D, a.mape)
    if not kand:
        print("Šonedēļ nav atrasts neviens fakts.")
        return None
    if a.fakts is None:
        S.fakti_saraksts(kand)
        print("\n(--fakts nav norādīts → izmantoju #1. Vairāki: --fakts 1,3,5 vai --fakts top5)")
    izv = _fakti_izvele(a.fakts, kand)                                # top5 → 5, top3 → 3, 1,3,5 → 3, "8,1,2!" – tava secība
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
    runa.append((S.reta_frase(FAKTI_TOPN_IEVADS, veids="fakts", n=2).format(n=skaits_v, N=skaits_v.capitalize())
                  + f" Number one: {hook_runa}. {jaut}" if n > 1 else f"{hook_runa}. {jaut}"))
    # #n → #2: viena aina katram
    mini_runa = []
    for nr, c in zip(range(n, 1, -1), citi[::-1]):
        st = fakta_statistika(D, c)
        kartes.append({"tips": "fakts_mini", "ilgums": 5.0, **c, "nr": nr, "stat_virs": st[0] if st else None,
                       "stat_rindas": [r_ for r_ in (st[1] if st else c["rindas"]) if r_[0]][:3]})
        runa.append(f"Number {nr}. {c['runa'][0]} {c['runa'][2]}".replace("  ", " "))
        mini_runa.append(runa[-1])
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
    st_hero = fakta_statistika(D, hero)
    return fakti_jauns({
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
    }, D, m, izv, st_hero, mini_runa)


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
            d.text((tx + 16, y + 138), str(val), font=fvv,
                   fill=S.ar_alfa(akc if j == c.get("izcelt_fl", 0) else S.BALTS, 255 * kc))   # atskatā – SINCE (2.)
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
    if veids == "intro" and (s.get("intro") or {}).get("noslepums"):
        return noslepums_thumbnail(s["intro"]["noslepums"])           # silueti ar "?" + 2. jautājums
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
        alt = _THUMB.get("alt") or {}
        if len(alt) > 1:                                              # visi varianti → sikteli\\ (ja gribas citu – augšupielādē to)
            try:
                import sikteli
                m_ = os.path.join(os.path.dirname(fails), "sikteli")
                os.makedirs(m_, exist_ok=True)
                for k_, im_ in alt.items():
                    piez = "_IZVELETS" if k_ == _THUMB.get("kods") else ""
                    im_.save(os.path.join(m_, f"{k_}_{sikteli.NOSAUKUMI.get(k_, k_)}{piez}.png"))
            except Exception as ex:                                   # noqa: BLE001
                print(f"  (sikteli\\: {type(ex).__name__}: {ex})")
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
    iss_o = bool(s["outro"].get("iss") and s["kartes"])               # īsā versija: beigās – cilpas aina
    if iss_o:
        s["kartes"][-1]["_bez_izejas"] = True
    ainas = ([("intro", None, s["intro"].get("ilgums", 3.2))] if s.get("intro") else []) + [("karte", c, c.get("ilgums", 3.6)) for c in s["kartes"]] \
        + ([("outro", s["outro"], ISS_CILPA_ILG)] if iss_o else
           [("outro", s["outro"] if _jauna_beigu_aina(s["outro"]) else None,
             VERDIKTS_ILGUMS if _jauna_beigu_aina(s["outro"]) else (4.5 if s["outro"].get("cta") else 3.6))])
    tmp = tempfile.mkdtemp(prefix="shorts_")
    audio = S.ierunat(s["runa"], balss, tmp) if balss else None
    if audio and len(audio) == len(ainas) and all(dur > 0 for _, dur in audio):
        ainas = [(v, c, max(ilg, dur + 0.45)) for (v, c, ilg), (_, dur) in zip(ainas, audio)]
        if JAUNS_FANTASY and len(S.VARDI_AINAS) == len(ainas):       # jaunā kartīte: zīmogs kopā ar verdikta frāzi
            ainas_ = []
            for i_, ((v, c, ilg), vl) in enumerate(zip(ainas, S.VARDI_AINAS)):
                if isinstance(c, dict) and c.get("tips") == "fantasy" and c.get("viz"):
                    tz_ = _nv_frazes_laiks(vl, s["runa"][i_] if i_ < len(s["runa"]) else "", c.get("_zim_frase"))
                    if tz_ is not None:
                        c["_zim_t"] = tz_ + 0.15                      # balss sākas 0,15 s pēc ainas
                        ilg = max(ilg, _nv_zimoga_laiks(c) + 1.6)
                ainas_.append((v, c, ilg))
            ainas = ainas_
    else:
        if audio:
            print("BALSS: audio faili tukši vai nepilnīgi – video bez skaņas.")
        audio = None
    nsl = (s.get("intro") or {}).get("noslepums") if (ainas and ainas[0][0] == "intro") else None
    _NS_SFX["ev"] = None
    if nsl:                                                           # noslēpuma āķis: notikumi pēc balss vārdiem
        try:
            vl0 = ([(a_ + 0.15, b_ + 0.15, x_) for a_, b_, x_ in S.VARDI_AINAS[0]]
                   if (audio and len(S.VARDI_AINAS) == len(ainas)) else None)
            nsl["_laiki"] = _ns_laiki(nsl, vl0, ainas[0][2])
            ainas[0] = ("intro", None, nsl["_laiki"]["beigas"])
            _NS_SFX["ev"] = _ns_sfx_ev(nsl["_laiki"])
            _ns_krekli(nsl)                                           # krekli – vienreiz, pirms kadriem
        except Exception as ex:                                       # noqa: BLE001
            print(f"  (noslēpuma āķis: {type(ex).__name__}: {ex} – parastais āķis)")
            nsl = None
            s["intro"].pop("noslepums", None)
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
        for i_s, ((_, _, ilg_), vl) in enumerate(zip(ainas, S.VARDI_AINAS)):
            if not (nsl and i_s == 0):                                # noslēpuma āķī subtitru nav – jautājums jau ir uz ekrāna
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
              "fantasy_intro": lambda t_, c_: aina_intro(t_, c_["intro"]), "fantasy_kartis": aina_kartis, "xg_karte": aina_xg_karte,
              "fakts_tablo": aina_fakts_tablo, "fakts_ripa": aina_fakts_ripa, "fakts_hist": aina_fakts_hist,
              "fakts_reti": aina_fakts_reti, "fakts_serijas": aina_fakts_serijas, "fakts_ga_serijas": aina_fakts_ga_serijas, "fakts_hc": aina_fakts_hc,
              "fakts_nak_j": aina_fakts_nak_j, "fantasy_divi": aina_fantasy_divi,
              "fantasy_saraksts": aina_fantasy_saraksts, "fantasy_kalendars": aina_fantasy_kalendars,
              "fantasy_ats_saraksts": aina_fantasy_ats_saraksts}
    _DAL["fons"] = bool(JAUNS_FANTASY and s.get("_bez_zimoga"))       # jaunais izskats: burbuļi fonā (ne āķī)
    # cilpai: āķa (1. ainas) sākuma kadrs – beigās video pāriet atpakaļ uz to
    v0, c0, _ = ainas[0]
    if v0 == "intro" and nsl:
        cilpa_sl = None                                               # noslēpuma āķis – pilns kadrs (sk. cilpa_kadrs)
    elif v0 == "intro":
        cilpa_sl = aina_intro(0.0 if s["intro"].get("aki") else 1.1, s["intro"])
    elif v0 == "karte":
        cilpa_sl = fn_map.get(c0.get("tips"), aina_karte)(1.1, c0)
    else:
        cilpa_sl = None
    cilpa_sl = _zona(cilpa_sl) if cilpa_sl is not None else None
    cilpa_kadrs = aina_noslepums(0.0, nsl, ainas[0][2]) if nsl else None
    t0 = 0.0
    for nr, (veids, c, ilg) in enumerate(ainas):
        for fr in range(int(round(ilg * S.FPS))):
            t = fr / S.FPS
            if nsl and veids == "intro":                              # noslēpuma āķis: pilns kadrs ar savu fonu
                kadrs = aina_noslepums(t, nsl, ilg)
            else:
                iss_c = veids == "outro" and isinstance(c, dict) and c.get("iss") and nr > 0
                if iss_c:                                             # īsā versija: iepriekšējā kartīte turpinās
                    _pv, pc_, pilg_ = ainas[nr - 1]
                    sl = fn_map.get(pc_.get("tips"), aina_karte)(pilg_ + t, pc_)
                elif veids == "intro":
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
                elif t < 0.4 and not (isinstance(c, dict) and c.get("_bez_ieejas")):
                    k = ease_back(t / 0.4)
                    alfa, dy = min(1, t / 0.2), (1 - k) * 260
                elif t > ilg - 0.22 and veids != "outro" and not (isinstance(c, dict) and c.get("_bez_izejas")):
                    k = S.ease((t - (ilg - 0.22)) / 0.22)
                    alfa, dy = 1 - k, -k * 120
                else:
                    alfa, dy = 1, 0
                zm_ = 0.0 if (isinstance(c, dict) and c.get("_bez_tuv")) else (0.04 if nr == 0 else TUVINAJUMS)   # TOP N tablo – bez lēcieniem
                if iss_c:                                             # tuvinājums – kā iepriekšējās ainas beigās
                    sl = _zona(sl, 0.0 if pc_.get("_bez_tuv") else TUVINAJUMS)
                else:
                    sl = _zona(sl, zm_ * S.ease(t / ilg))                 # drošā zona + lēna tuvināšana
                if veids == "outro" and cilpa_sl is not None and t > ilg - CILPA:      # cilpa: atpakaļ uz āķi
                    sl = Image.blend(sl, cilpa_sl, S.ease((t - (ilg - CILPA)) / CILPA))
                kadrs = fons.kadrs(t0 + t)
                if _DAL["fons"] and veids != "intro":
                    _nv_dalinas_fons(kadrs, t0 + t)
                if alfa < 1:
                    sl.putalpha(sl.getchannel("A").point(lambda v: int(v * alfa)))
                kadrs.paste(sl, (0, int(dy)), sl)
            if cilpa_kadrs is not None and veids == "outro" and t > ilg - CILPA:     # cilpa: atpakaļ uz noslēpuma āķi
                kadrs = Image.blend(kadrs, cilpa_kadrs, S.ease((t - (ilg - CILPA)) / CILPA))
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
    _DAL["fons"] = False
    if fona_fails:
        fons.aizvert()
    try:                                                              # sīktēls = āķa kadrs ar to pašu fonu
        _THUMB["im"] = thumbnail_kadrs(ainas[0], s, fona_fails, atr, fn_map)
    except Exception as ex:                                           # noqa: BLE001
        print(f"SĪKTĒLS: neizdevās no āķa ({type(ex).__name__}: {ex}) – vecais variants")
        _THUMB["im"] = None
    _THUMB.update(alt={}, kods=None, veids=None)
    if _THUMB["im"] is not None and SIKTS["kods"] != "0":            # sīktēlu dažādošana (sikteli.py) – A/B/D/E/F/J/K pēc kārtas
        try:
            import sikteli
            vp_ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(izvade))), MEDIJI_JSON)
            r_ = sikteli.izveidot(sys.modules[__name__], s, vp_, SIKTS["kods"])
            if r_:
                kods_, im_, alt_, veids_ = r_
                _THUMB.update(alt=dict(alt_, **{"0": _THUMB["im"]}), im=im_, kods=kods_, veids=veids_)
        except Exception as ex:                                       # noqa: BLE001
            print(f"SĪKTĒLS: sikteli.py kļūda ({type(ex).__name__}: {ex}) – vecais variants")
    _IZMANTOTS["muzika"] = None
    miksets(video_tmp, izvade, audio, ainas, kopa, tmp)
    shutil.rmtree(tmp, ignore_errors=True)
    try:                                                              # video_info.json – kas izmantots šajā video
        import json, datetime
        info = {"izveidots": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "video": os.path.basename(izvade),
                "virsraksts": S.yt_virsraksts(s.get("virsraksts", "")) if hasattr(S, "yt_virsraksts") else s.get("virsraksts", ""),
                "komanda": "python ShortsB.py " + " ".join(sys.argv[1:]),
                "fons": os.path.basename(fona_fails) if fona_fails else None, "fona_cels": fona_fails,
                "muzika": os.path.basename(_IZMANTOTS["muzika"]) if _IZMANTOTS["muzika"] else None,
                "muzikas_cels": _IZMANTOTS["muzika"], "balss": balss if audio else None, "garums_s": round(kopa, 1),
                "sikts": _THUMB.get("kods") or "0", "sikts_veids": _THUMB.get("veids"),   # sīktēla izkārtojums (rotācijai)
                "iss": bool(s.get("_iss"))}
        mape_v = os.path.dirname(os.path.abspath(izvade))
        info["mape"] = os.path.basename(mape_v)
        vp = os.path.join(os.path.dirname(mape_v), MEDIJI_JSON)      # kopējais saraksts video\ mapē (paliek, ja video mapi izdzēš)
        try:
            vis_ = json.load(open(vp, encoding="utf-8")) if os.path.exists(vp) else []
            vis_ = vis_ if isinstance(vis_, list) else []
        except Exception:                                             # noqa: BLE001
            vis_ = []
        vis_.append(info)
        with open(vp, "w", encoding="utf-8") as f_:
            json.dump(vis_, f_, ensure_ascii=False, indent=1)
    except Exception as ex:                                           # noqa: BLE001
        print(f"  ({MEDIJI_JSON}: {type(ex).__name__}: {ex})")
    return kopa, bool(audio)


TESTA_MAPE = "video_test"
VESTURES_FAILI = ("fakti_vesture.json", "frazes_vesture.json", "tiesnesi_vesture.json", "fantasy_rezultati.json",
                  "shorts_mediji.json", MEDIJI_JSON)                  # video_info.json – arī sīktēlu kārtai


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


def _argv_vertiba(nos):
    """Argumenta vērtība no sys.argv ("--veids fantasy" vai "--veids=fantasy"); None, ja nav."""
    for i_, x_ in enumerate(sys.argv):
        if x_ == nos:
            return sys.argv[i_ + 1] if i_ + 1 < len(sys.argv) else ""
        if x_.startswith(nos + "="):
            return x_.split("=", 1)[1]
    return None


def ieslegt():
    global JAUNS_FANTASY, NOSL_AKIS, FJ_ANIM
    if "--bez-noslepuma" in sys.argv:                                 # vecais āķis (ar skaitli), noslēpuma vietā
        sys.argv.remove("--bez-noslepuma")
        NOSL_AKIS = False
        print("ĀĶIS: bez noslēpuma (--bez-noslepuma)")
    rez_ = None                                                       # garums: xG (3 veidi), fantasy, streameri, fakti – īsā versija
    if "--iss" in sys.argv:                                           # pēc noklusējuma (kopš 10.11.2026); --long – garā;
        sys.argv.remove("--iss")                                      # --iss – īsā arī faktiem un atskatiem
        rez_ = "iss"
    if "--long" in sys.argv:
        sys.argv.remove("--long")
        rez_ = "long"
    v_ = _argv_vertiba("--veids") or "speletaji"
    ats_ = _argv_vertiba("--atskats") is not None
    ISS["on"] = rez_ == "iss" or (rez_ is None and not ats_ and v_ in ISS_NOKLUSETS)
    S.ISS = ISS["on"]
    if ISS["on"]:
        print("ĪSĀ VERSIJA" + (" (--iss)" if rez_ == "iss" else " (noklusējums; garā – --long)")
              + ": bez jautājuma 1, verdikta un CTA balsī; beigās cilpa uz āķi")
    elif rez_ == "long" and not ats_ and v_ in ISS_NOKLUSETS:
        print("GARĀ VERSIJA: --long")
    if "--sikts" in sys.argv:                                         # sīktēla izkārtojums ar roku: --sikts D  (0 = vecais)
        i_ = sys.argv.index("--sikts")
        if i_ + 1 < len(sys.argv) and sys.argv[i_ + 1].upper() in ("0", "A", "B", "D", "E", "F", "J", "K"):
            SIKTS["kods"] = sys.argv[i_ + 1].upper()
            print(f"SĪKTĒLS: ar roku – {SIKTS['kods']}")
            del sys.argv[i_:i_ + 2]
        else:
            print("SĪKTĒLS: --sikts vajag burtu A/B/D/E/F/J/K vai 0 – izvēlos pats")
            del sys.argv[i_]
    if "--anim" in sys.argv:                                          # faktu TOP N animācija testam: --anim B (A–E)
        i_ = sys.argv.index("--anim")
        if i_ + 1 < len(sys.argv) and sys.argv[i_ + 1].upper() in ("A", "B", "C", "D", "E", "1", "2", "3", "4", "5"):
            FJ_ANIM = sys.argv[i_ + 1].upper()
            print(f"FAKTU ANIMĀCIJA: {FJ_ANIM}")
            del sys.argv[i_:i_ + 2]
        else:
            del sys.argv[i_]
    if "--vecais" in sys.argv:                                        # vecais izskats (rezerve, ja jaunajā kāda kļūda)
        sys.argv.remove("--vecais")
        JAUNS_FANTASY = False
        S.JAUNI_TEKSTI = False
        print("IZSKATS: vecais (--vecais)")
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
        if s_ and "RECAP" in str(s_.get("intro", {}).get("tag", "")):     # fantasy atskats – jaunais izskats
            s_ = fantasy_atskats_jauns(s_)
        return s_
    S.atskats = atskats_ar_aki
    S.VEIDI["fakts"] = veids_fakti_b
    if FAKTI_BEZ_SERIJAM and not getattr(S.fakti_kandidati, "_bez_serijam", False):   # sērijas – Streak watch video
        _orig_kand = S.fakti_kandidati

        def _kand_bez_serijam(D, mape_video):
            return [c for c in _orig_kand(D, mape_video) if not _fakts_ir_serija(c)]
        _kand_bez_serijam._bez_serijam = True
        S.fakti_kandidati = _kand_bez_serijam                         # arī --fakti sarakstam (shorts.py main)
    S.VEIDI["serijas"] = veids_serijas_b                              # Streak watch (kopš 10.11.2026)
    for v_ in ("fantasy", "streameri"):                               # jaunais āķis fantasy / streameru video
        if v_ in S.VEIDI:
            S.VEIDI[v_] = (lambda f_: (lambda m, a: fantasy_aki(f_(m, a))))(S.VEIDI[v_])
    if ISS["on"]:                                                     # īsā versija – pēc visiem pārveidojumiem
        for v_ in ("speletaji", "komandas", "vartsargi", "fantasy", "streameri", "fakts"):
            if v_ in S.VEIDI:
                S.VEIDI[v_] = (lambda f_, vv: (lambda m, a: iss_parveidot(f_(m, _iss_args(a, vv)), vv)))(S.VEIDI[v_], v_)
        orig_ats_iss = S.atskats
        S.atskats = lambda fails, m, a: iss_parveidot(orig_ats_iss(fails, m, a), "atskats")
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
# Kopš 04.11. – noklusējums ShortsB.py (vecais izskats: --vecais).
JAUNS_FANTASY = True             # jaunais izskats (kopš 04.11.); ārkārtas gadījumā vecais:  python ShortsB.py ... --vecais
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


_DAL = {"fons": False}   # True – burbuļi tiek zīmēti fonā (renderet), ne katrā ainā atsevišķi


def _nv_dalinas(L, t):
    if _DAL["fons"]:                                                  # jaunajā izskatā – fonā (visās ainās, izņemot āķi)
        return
    _nv_dalinas_zim(ImageDraw.Draw(L), t)


def _nv_dalinas_fons(kadrs, T):
    """Burbuļi, kas lido uz augšu – uz video fona (RGB), vienmērīgi visu video (laiks no video sākuma). Kopš 05.11.2026:
    nepazūd grafika / verdikta ainās, zīmoga brīdī un ainu maiņās."""
    _nv_dalinas_zim(ImageDraw.Draw(kadrs, "RGBA"), T)


def _nv_dalinas_zim(d, t):
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
    out.paste(L, (int(rnd.uniform(-a, a)), int(rnd.uniform(-a, a))))   # bez maskas: ar masku caurspīdīgie slāņi
    return out                                                        # (komandas burti fonā, burbuļi) uz brīdi pazuda


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
    return _ns_fantasy(s)                                             # noslēpuma āķis (ja ieslēgts)


XG_VIRSR_PAPILDU = {"speletaji": [[("LUCKY", S.BALTS), ("OR", S.BALTS), ("DUE?", S.DZELTENS)]]}   # pamīšus ar XG_VIRSR
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
        virsr_ = S.reta_frase([XG_VIRSR[veids]] + XG_VIRSR_PAPILDU.get(veids, []), veids=veids, n=1)
        ha = dict(hero["viz"]["aki"])
        ha.update({"vards": str(hero.get("v2", "")).upper(), "kom": hero.get("badge"), "tag": s["intro"].get("tag", ""), "kart_txt": "#1"})
        orig = sorted(kar, key=lambda c: (0 if c["viz"]["grupa"] == "laim" else 1, c.get("nr", 0)))
        kartis = [{"kom": str(c.get("badge", "")), "poz": c["viz"].get("poz", ""), "akc": tuple(c["akc"]),
                   "liels": c["viz"]["kart"]["liels"], "maz": c["viz"]["kart"]["maz"], "lab": c["viz"]["zimogs"]} for c in orig]
        k2 = {"tips": "fantasy_kartis", "ilgums": 6.0, "tag": s["intro"].get("tag", ""), "_tv": tv, "virsr": virsr_,
              "apaksa": "  ·  ".join(x for x in (per, XG_APAKSA[veids]) if x), "kartis": kartis,
              "n_pick": sum(1 for c in orig if c["viz"]["grupa"] == "laim"), "rek": None}
        if s.get("xg_karte") and all(c["viz"].get("xy") for c in orig):          # līgas karte (neko nepasaka priekšā)
            k2 = {"tips": "xg_karte", "ilgums": 5.5, "_tv": tv, "virsr": virsr_, "karte": s["xg_karte"],
                  "apaksa": "  ·  ".join(x for x in (per, XG_APAKSA[veids]) if x),
                  "izcelti": [(float(c["viz"]["xy"][0]), float(c["viz"]["xy"][1]), tuple(c["akc"]), f"#{c.get('nr', '')}") for c in orig]}
        jaunas = [k2]
        for i, c in enumerate(kar):
            c = dict(c)
            c["tips"], c["liels"] = "fantasy", c["viz"]["zimogs"]
            c["_tablo"] = {"lab": c["viz"]["tablo_lab"], "liels": f"#{c.get('nr', '')}", "kr": kr_rad, "idx": i}
            c["_datums"] = c["viz"].get("tablo_txt", "")
            jaunas.append(c)
        s["intro"] = {"aki": True, "fantasy_aki": ha, "tag": ha["tag"], "ilgums": 2.6, "_tv": tv}
        # + viens papildu teikums pie katras kartītes – pārmaiņus fakts / fantasy (komandām – uzvaras), lai video nav par garu
        r_k = [(r_ + " " + ((c["viz"].get("runa_fant") if i % 2 == 1 and c["viz"].get("runa_fant") else c["viz"].get("runa_fakts"))
                            or c["viz"].get("runa_pap", ""))).strip() for i, (r_, c) in enumerate(zip(s["runa"][1:-1], kar))]
        s["runa"] = [s["runa"][0], s.get("_intro_runa", "")] + r_k + [s["runa"][-1]]
        s["kartes"] = jaunas
        s["_bez_zimoga"] = True
        _ns_xg(s, veids, hero)                                        # noslēpuma āķis (ja ieslēgts)
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
        kom_ = liels_ == "TEAMS"                                      # noslēpuma āķis: visi atzīmētie – silueti rindā
        noslepuma_aki(s, [(c.get("badge"), "" if kom_ else c.get("v2")) for c in kar], NOSL_Q1["atskats_xg"],
                      NOSL_Q2["atskats_xg"], "atskats_" + ("vartsargi" if liels_ == "GOALIES" else ("komandas" if kom_ else "speletaji")),
                      x_vards={"GOALIES": "goalies", "TEAMS": "teams"}.get(liels_, "players"), runa_pec=s["aki_runa"])
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
              "virsr": S.reta_frase([[("LAST", S.BALTS), ("WEEK'S", S.BALTS), ("CALLS", S.DZELTENS)],
                                     [("CHECKING", S.BALTS), ("OUR", S.BALTS), ("CALLS", S.DZELTENS)]], veids="atskats_fantasy", n=1),
              "apaksa": f"{ned}  ·  VS A TYPICAL PLAYER IN THE SAME POOL",
              "kartis": kartis, "n_pick": n_add, "rek": tuple(s["atskats_rek"]) if s.get("atskats_rek") else None}
        try:                                                          # 2. aina – rezultātu saraksts ar vārdiem (kopš 10.11.2026)
            k2 = _fa_s2_aina(k2, kar, s) or k2
        except Exception as ex_:                                      # noqa: BLE001
            print(f"  (atskata saraksts: {type(ex_).__name__}: {ex_} – kārtis)")
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
        noslepuma_aki(s, [(c.get("badge"), c.get("v2")) for c in kar], NOSL_Q1["atskats_f"], NOSL_Q2["atskats_f"],
                      "atskats_fantasy", runa_pec=s["aki_runa"])      # noslēpuma āķis: visi ieteiktie – silueti rindā
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
    _nv_put(L, _nv_timg(a_["zem"], S.ietilpinat(d, a_["zem"], "black", 66, S.W - 140), (203, 213, 225)), 540, 835 + dy0, 1,
            S.ease((t - 0.45) / 0.25))
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
    """Zīmogs: kad balss SĀK verdikta frāzi ("Worth a pickup.", "The chances are there." …) – zīmogs un frāze kopā;
    ne agrāk kā 2,4 s (kartīte izrullēta). Bez balss – 1,9 s pirms ainas beigām."""
    if c.get("_zim_t") is not None:
        return max(2.4, float(c["_zim_t"]) - 0.1)
    return max(3.2, c.get("_ilg", 6.5) - 1.9)


def _nv_frazes_laiks(vardi, teksts, frase):
    """Verdikta frāzes sākuma laiks (s) ainas balsī: vārdu skaits pirms frāzes → tuvākais atbilstošais vārds vārdu laikos."""
    if not vardi or not teksts:
        return None
    teksts = str(teksts)
    if frase and str(frase) in teksts:
        pirms, fr_ = teksts[:teksts.rfind(str(frase))], str(frase)
    else:                                                             # rezerve – pēdējais teikums
        tk = re.split(r"(?<=[.!?])\s+", teksts.strip())
        if len(tk) < 2:
            return None
        pirms, fr_ = " ".join(tk[:-1]), tk[-1]
    n = len(S.balsij(pirms).split())
    tirs = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())        # noqa: E731
    pirmais = tirs((S.balsij(fr_).split() or [""])[0])
    kand = [i for i in range(max(0, n - 4), min(len(vardi), n + 5)) if tirs(vardi[i][2]) == pirmais]
    i = min(kand, key=lambda j: abs(j - n)) if kand else min(n, len(vardi) - 1)
    return float(vardi[i][0])


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
    pk = sorted([c for c in kar if c.get("liels") not in ("DROP", "BENCH")], key=lambda c: c.get("nr", 0))   # kārtis #1, #2, #3
    dr = [c for c in kar if c.get("liels") in ("DROP", "BENCH")]                                              # (streameru kartītes – #3 → #1)
    kartis = []
    for grupa in (pk, dr):
        for j, c in enumerate(grupa, 1):
            v = c["viz"]
            ir_r = v.get("rost") is not None
            kartis.append({"kom": str(c.get("badge", "")), "poz": str(v.get("poz", "")), "akc": tuple(c["akc"]),
                           "liels": (f"{v['rost']:.0f}%" if v["rost"] >= 1 else f"{v['rost']:.1f}%") if ir_r else str(v.get("pts", "")),
                           "maz": "ROSTERED" if ir_r else "POINTS", "lab": f"{c.get('liels', 'ADD')} #{c.get('nr') or j}"})
    ap = [str(x) for x in (vecais or {}).get("apaksa", [])]
    ned = re.sub(r"^Week of\s+", "", ap[0]) if ap else ""
    ned = re.sub(r",\s*\d{4}$", "", ned).upper()
    ned = re.sub(r"\b([A-Z]{3}) (\d+) – \1 (\d+)\b", r"\1 \2 – \3", ned)
    mr = re.search(r"under (\d+)%", " ".join(ap))
    rr = re.search(r"Last week: (\d+)/(\d+)", " ".join(ap))
    stream = "STREAM" in str((vecais or {}).get("tag", "")).upper()
    return {"tips": "fantasy_kartis", "ilgums": 6.0, "tag": (vecais or {}).get("tag", "NHL  ·  FANTASY WAIVER WIRE"),
            "virsr": [("THIS", S.BALTS), ("WEEK'S", S.BALTS), ("STREAMS", S.DZELTENS)] if stream else
                     S.reta_frase([[("NEXT", S.BALTS), ("WEEK'S", S.BALTS), ("MOVES", S.DZELTENS)],
                                   [("WAIVER", S.BALTS), ("WIRE", S.BALTS), ("PICKS", S.DZELTENS)]], veids="fantasy", n=1),
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


def aina_xg_karte(t, c):
    """xG video 2. aina – "līgas karte": visi spēlētāji / vārtsargi / komandas kā punkti (xG pret vārtiem, xGA pret
    ielaistajiem, SV% pret SH%), "godīgā" līnija (vārti = xG / PDO = 100), zonas LUCKY / UNLUCKY un mūsu 6 izceltie
    (#1–#3, bez vārdiem). Neko nepasaka priekšā – parāda, ko nozīmē "luck"."""
    from PIL import ImageChops
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    if c.get("_tv"):
        _nv_tablo_virs(L, N, t, c["_tv"])
    F, WH, LAB = S.fonts, S.BALTS, _NV_LAB
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
        S.teksts_c(d, 488, c["apaksa"], S.ietilpinat(d, c["apaksa"], "semi", 34, 900), LAB + (int(255 * a),))
    K = c["karte"]
    # panelis
    ku = S.ease(min(1.0, max(0.0, (t - 0.45) / 0.5)))
    if ku <= 0:
        L.alpha_composite(N); return L
    B0, B1 = 560, 560 + (1440 - 560) * ku
    d.rounded_rectangle([70, B0, 1010, B1], radius=36, fill=(10, 14, 32, 235))
    for pad, al_ in ((10, 22), (5, 50)):
        d.rounded_rectangle([70 - pad, B0 - pad, 1010 + pad, B1 + pad], radius=36 + pad, outline=S.ZILS + (al_,), width=pad + 2)
    d.rounded_rectangle([70, B0, 1010, B1], radius=36, outline=S.ZILS + (220,), width=4)
    C = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dc = ImageDraw.Draw(C)
    PX0, PX1, PY0, PY1 = 170, 960, 640, 1330                           # zīmēšanas laukums
    pk = K.get("punkti") or []
    izc = c.get("izcelti") or []
    xs = [p[0] for p in pk] + [p[0] for p in izc]
    ys = [p[1] for p in pk] + [p[1] for p in izc]
    if K.get("veids") == "pdo":
        xa, xb = min(xs) - 0.4, max(xs) + 0.4
        ya, yb = min(ys) - 0.6, max(ys) + 0.6
    else:
        m_ = max(max(xs), max(ys)) * 1.06 if xs else 1
        xa, xb, ya, yb = 0.0, m_, 0.0, m_

    def X(v):
        return PX0 + (v - xa) / (xb - xa) * (PX1 - PX0)

    def Y(v):
        return PY1 - (v - ya) / (yb - ya) * (PY1 - PY0)
    # zonas (puse virs / zem līnijas), līnija
    if K.get("veids") == "pdo":
        p1, p2 = (X(xa), Y(100 - xa)), (X(xb), Y(100 - xb))
    else:
        p1, p2 = (X(xa), Y(xa)), (X(xb), Y(xb))
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    ln = math.hypot(dx, dy) or 1
    ux, uy = dx / ln, dy / ln
    t0_, t1_ = 0.0, 1.0                                               # līnija – tikai laukuma iekšpusē (Liang–Barsky)
    for pp, qq in ((-dx, p1[0] - PX0), (dx, PX1 - p1[0]), (-dy, p1[1] - PY0), (dy, PY1 - p1[1])):
        if pp == 0:
            continue
        rr_ = qq / pp
        if pp < 0:
            t0_ = max(t0_, rr_)
        else:
            t1_ = min(t1_, rr_)
    q1_, q2_ = (p1[0] + dx * t0_, p1[1] + dy * t0_), (p1[0] + dx * t1_, p1[1] + dy * t1_)
    nx, ny = uy, -ux                                                  # normāle uz "augšu" (mazāks y)
    if ny > 0:
        nx, ny = -nx, -ny
    FAR = 3000
    kz = S.ease(min(1.0, max(0.0, (t - 1.2) / 0.5)))
    if kz > 0:
        rect = Image.new("L", (S.W, S.H), 0); ImageDraw.Draw(rect).rectangle([PX0, PY0, PX1, PY1], fill=255)
        for sign, (txt_, kr_) in ((1, K["augsa"]), (-1, K["apaksa"])):
            z = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
            a1 = (p1[0] - ux * FAR, p1[1] - uy * FAR); a2 = (p2[0] + ux * FAR, p2[1] + uy * FAR)
            ImageDraw.Draw(z).polygon([a1, a2, (a2[0] + sign * nx * FAR, a2[1] + sign * ny * FAR),
                                       (a1[0] + sign * nx * FAR, a1[1] + sign * ny * FAR)], fill=tuple(kr_) + (int(30 * kz),))
            z.putalpha(ImageChops.multiply(z.getchannel("A"), rect))
            C.alpha_composite(z)
        # zonu nosaukumi – stūrī savā pusē, kur vismazāk punktu
        visi_ = [(X(px), Y(py), 1) for px, py in pk] + [(X(px), Y(py), 8) for px, py, _, _ in izc]   # izceltie "sver" vairāk
        sturi = [((PX0 + 16, PY0 + 14), "la", (PX0 + 110, PY0 + 34)), ((PX1 - 16, PY0 + 14), "ra", (PX1 - 110, PY0 + 34)),
                 ((PX0 + 16, PY1 - 14), "ld", (PX0 + 110, PY1 - 34)), ((PX1 - 16, PY1 - 14), "rd", (PX1 - 110, PY1 - 34)),
                 (((PX0 + PX1) / 2, PY1 - 14), "md", ((PX0 + PX1) / 2, PY1 - 34)), (((PX0 + PX1) / 2, PY0 + 14), "ma", ((PX0 + PX1) / 2, PY0 + 34)),
                 ((PX0 + 16, (PY0 + PY1) / 2), "lm", (PX0 + 110, (PY0 + PY1) / 2)), ((PX1 - 16, (PY0 + PY1) / 2), "rm", (PX1 - 110, (PY0 + PY1) / 2))]
        for sign, (txt_, kr_) in ((1, K["augsa"]), (-1, K["apaksa"])):
            der = [s_ for s_ in sturi if sign * ((s_[2][0] - p1[0]) * nx + (s_[2][1] - p1[1]) * ny) > 0] or sturi
            best = min(der, key=lambda s_: (sum(q[2] for q in visi_ if abs(q[0] - s_[2][0]) < 140 and abs(q[1] - s_[2][1]) < 50),
                                            sturi.index(s_) >= 4))       # vienādi – priekšroka stūrim
            dc.text(best[0], txt_, font=F("black", 40), fill=tuple(kr_) + (int(230 * kz),), anchor=best[1])
    # asis
    dc.line([(PX0, PY1), (PX1, PY1)], fill=(255, 255, 255, 90), width=3)
    dc.line([(PX0, PY0), (PX0, PY1)], fill=(255, 255, 255, 90), width=3)
    dc.text((PX1, PY1 + 22), K["x_lab"] + "  →", font=F("semi", 28), fill=LAB, anchor="ra")
    ylab = _nv_timg("↑  " + K["y_lab"], F("semi", 28), LAB).rotate(90, expand=True)
    C.alpha_composite(ylab, (int(PX0 - 30 - ylab.width), int(PY0)))
    # "godīgā" līnija – zīmējas
    kl = S.ease(min(1.0, max(0.0, (t - 1.0) / 0.6)))
    ln2 = math.hypot(q2_[0] - q1_[0], q2_[1] - q1_[1])
    if kl > 0 and ln2 > 1:
        n_ = int(ln2 * kl / 26)
        for j in range(n_):
            a0 = (q1_[0] + ux * j * 26, q1_[1] + uy * j * 26); a1 = (q1_[0] + ux * (j * 26 + 15), q1_[1] + uy * (j * 26 + 15))
            dc.line([a0, a1], fill=(255, 255, 255, 200), width=4)
        if kl >= 1:
            lt = _nv_timg(K["linija"], F("black", 26), WH)
            ang = -math.degrees(math.atan2(dy, dx))
            lt = lt.rotate(ang, expand=True, resample=Image.BICUBIC)
            mx_, my_ = q1_[0] + (q2_[0] - q1_[0]) * 0.7, q1_[1] + (q2_[1] - q1_[1]) * 0.7
            C.alpha_composite(lt, (int(mx_ - lt.width / 2 + nx * 24), int(my_ - lt.height / 2 + ny * 24)))
    # visi punkti (pelēki) – parādās pakāpeniski
    for i, (px, py) in enumerate(pk):
        kk = (t - 0.6 - (i % 40) * 0.025) / 0.3
        if kk <= 0:
            continue
        r = 6
        dc.ellipse([X(px) - r, Y(py) - r, X(px) + r, Y(py) + r], fill=(203, 213, 225, int(120 * min(1.0, kk))))
    # izceltie – mūsu 6
    vietas = []
    for i, (px, py, kr, lab) in enumerate(izc):
        kk = (t - 1.9 - i * 0.22) / 0.3
        if kk <= 0:
            continue
        r = 17 * ease_back(min(1.0, kk))
        cx_, cy_ = X(px), Y(py)
        dn.ellipse([cx_ - r - 10, cy_ - r - 10, cx_ + r + 10, cy_ + r + 10], fill=tuple(kr) + (60,))
        dn.ellipse([cx_ - r, cy_ - r, cx_ + r, cy_ + r], fill=tuple(kr) + (255,), outline=WH + (255,), width=3)
        if kk > 0.6:
            for ox, oy, anc in ((24, -22, "lm"), (24, 24, "lm"), (-24, -22, "rm"), (-24, 24, "rm")):
                lx, ly = cx_ + ox, cy_ + oy
                if all(abs(lx - qx) > 56 or abs(ly - qy) > 30 for qx, qy in vietas):
                    break
            vietas.append((lx, ly))
            dn.text((lx, ly), lab, font=F("black", 30), fill=WH, anchor=anc)
    m = Image.new("L", (S.W, S.H), 0)
    ImageDraw.Draw(m).rounded_rectangle([74, B0 + 4, 1006, max(B0 + 10, B1 - 4)], radius=32, fill=255)
    C.putalpha(ImageChops.multiply(C.getchannel("A"), m))
    L.alpha_composite(C)
    L.alpha_composite(N)
    return L


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
            mm_ = max(abs(float(r_[1])) for r_ in rind)
            m_ = (max(0.5, mm_) if mm_ >= 1 else max(0.05, mm_)) * 1.15
            cx_ = bx0 + bw_ / 2
            dc.line([(cx_, y0 + 56), (cx_, y1 - 12)], fill=(255, 255, 255, int(70 * a)), width=2)
            xr = cx_ + bw_ / 2 * max(-1.0, min(1.0, float(f["robeza"]) / m_)) if f.get("robeza") is not None else None
        else:
            skala = max(4.0, math.ceil(max(float(r_[1]) for r_ in rind)) + 1)
        uzraksti = []                                                  # vērtības – virs pusceļa līnijas (nepārsvītrotas)
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
                r_j = min(18, max(14, L_) / 2)                       # pie centra – taisna mala, ārējais gals noapaļots
                if val >= 0:
                    xa, xb = cx_, cx_ + max(14, L_)
                    dc.rounded_rectangle([xa, yy, xb, yy + 36], radius=r_j, fill=kr_(kr) + (int(255 * a),))
                    dc.rectangle([xa, yy, xa + r_j, yy + 36], fill=kr_(kr) + (int(255 * a),))
                    uzraksti.append(((xb + 12, yy + 18), txt, "lm"))
                else:
                    xa, xb = cx_ - max(14, L_), cx_
                    dc.rounded_rectangle([xa, yy, xb, yy + 36], radius=r_j, fill=kr_(kr) + (int(255 * a),))
                    dc.rectangle([xb - r_j, yy, xb, yy + 36], fill=kr_(kr) + (int(255 * a),))
                    uzraksti.append(((xa - 12, yy + 18), txt, "rm"))
            else:
                bx1 = bx0 + bw_ * max(0.0, val) / skala * kk
                dc.rounded_rectangle([bx0, yy, max(bx0 + 36, bx1), yy + 36], radius=18, fill=kr_(kr) + (int(255 * a),))
                uzraksti.append(((max(bx0 + 36, bx1) + 14, yy + 18), txt, "lm"))
        if f.get("diverg") and xr is not None and gk(T1 + 0.4, 0.4) > 0:   # pusceļa līnija – virs joslām (raustīta, dzeltena)
            ar_ = int(255 * a * eo(gk(T1 + 0.4, 0.4)))
            yy_ = y0 + 54
            while yy_ < y1 - 8:
                dc.line([(xr, yy_), (xr, min(yy_ + 10, y1 - 8))], fill=S.MELNS + (ar_,), width=8)
                dc.line([(xr, yy_), (xr, min(yy_ + 10, y1 - 8))], fill=Y + (ar_,), width=4)
                yy_ += 16
        for (px_, py_), txt, anc in uzraksti:
            dc.text((px_, py_), txt, font=F("black", 32), fill=WH + (int(255 * a),), anchor=anc, stroke_width=4, stroke_fill=_NV_TILE + (int(255 * a),))
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
    if U0 < u < U1:                                                   # skenera līnija pie izrullēšanās malas
        _skeneris(N, 70, 1010, yb_)
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
        bw, gap, base, mx = 30, 12, y1 - 38, 60                      # ≤ 60 px – cipars virs stabiņa nepārklāj virsrakstu
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


# ================================================================ FAKTU VIDEO – JAUNAIS IZSKATS
# Āķis (jaunais stils) → TOP N tablo: fakti #N → #2 ielido kā lielas kartītes un "nolaižas" tablo rindā, #1 pulsē līdz
# beigām → #1 atklājas → "katrs vārts uz ripas" (īstās metienu vietas) + sezonas skaitļi → "HOW RARE IS IT?" histogramma
# (visas sezonas sērijas / spēles) → NEXT UP. Ja kādam fakta veidam datu nav – tā vietā vecā aina (saraksts / konteksts).

def _fj_tablo(L, N, t, c, anim=True):
    tv = c.get("_tv") or {}
    _nv_tablo_zim(L, N, t, S.ZILS, tv.get("lab", "NHL · THE WEEK"), tv.get("liels", "IN NUMBERS"), tv.get("kr") or [],
                  c.get("_tv_idx", len(tv.get("kr") or []) - 1), tv.get("labaja", ""), anim)


def _fj_virsr(L, t, dalas, y, izm=120, staticks=False):
    d = ImageDraw.Draw(L)
    f = S.ietilpinat(d, "  ".join(x for x, _ in dalas), "black", izm, 940)
    plat = [d.textlength(x, font=f) for x, _ in dalas]
    spr = d.textlength("  ", font=f)
    x = 540 - (sum(plat) + spr * (len(dalas) - 1)) / 2
    for i, ((txt, kr), w_) in enumerate(zip(dalas, plat)):
        k = 1.0 if staticks else (t - 0.05 - i * 0.15) / 0.3
        if k > 0:
            _nv_put(L, _nv_timg(txt, f, tuple(kr)), x + w_ / 2, y, 1 + 0.6 * (1 - ease_back(min(1.0, k), 2.0)), min(1.0, k * 2.5))
        x += w_ + spr


def _fj_ripa(d, cx, cy, r, kom, a=255):
    """Komandas apzīmējums: balts kods + divkrāsu pasvītra 60/40 ar "/" (kā spēlētāja vārdam). Aizņem ≤ 2,2r × 2r
    (tikpat, cik agrākais aplis), centrs (cx, cy). Tumšas komandu krāsas – gaišākas (_nv_gaisas_kr), lai redzamas."""
    kom = str(kom or "")[:3]
    if not kom or a <= 0 or r < 4:
        return
    prim, sek = kom_krasas(kom)
    f = S.ietilpinat(d, kom, "black", max(10, int(r * 0.95)), 2.2 * r)
    tw = d.textlength(kom, font=f)
    d.text((cx, cy - r * 0.12), kom, font=f, fill=S.BALTS + (int(a),), anchor="mm")
    y, h = cy + r * 0.52, max(3.0, r * 0.16)
    x0, x1 = cx - tw / 2, cx + tw / 2
    xs = x0 + (x1 - x0) * 0.6
    d.polygon([(x0, y), (xs + h * 0.5, y), (xs - h * 0.5, y + h), (x0, y + h)], fill=_nv_gaisas_kr(prim) + (int(a),))
    d.polygon([(xs + h * 1.2, y), (x1, y), (x1, y + h), (xs + h * 0.2, y + h)], fill=_nv_gaisas_kr(sek) + (int(a),))


def _fj_karte(f_, kr):
    """Lielā fakta kartīte (760×440): #nr, komandas aplis, galvenais skaitlis, apraksts, vārds."""
    F = S.fonts
    cw, ch = 760, 440
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); di = ImageDraw.Draw(im)
    di.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=36, fill=(12, 18, 40, 245), outline=tuple(kr) + (255,), width=6)
    di.text((40, 40), f"#{f_['nr']}", font=F("black", 64), fill=tuple(kr))
    if f_.get("badge"):
        _fj_ripa(di, cw - 90, 80, 52, f_["badge"])
    h = list(f_.get("hook") or [""])
    di.text((cw / 2, 205), h[0], font=S.ietilpinat(di, h[0], "black", 110, cw - 80), fill=S.BALTS, anchor="mm")
    if len(h) > 1:
        r_ = " ".join(h[1:])
        di.text((cw / 2, 290), r_, font=S.ietilpinat(di, r_, "black", 46, cw - 80), fill=S.DZELTENS, anchor="mm")
    v = str(f_.get("vards_pilns") or "").upper()
    di.text((cw / 2, 375), v, font=S.ietilpinat(di, v, "semi", 40, cw - 80), fill=_NV_LAB, anchor="mm")
    return im


def _fj_karte_plus(f_, kr):
    """Paplašinātā kartīte (#N → #2, kamēr runā balss): augšā – parastā kartīte, zem tās spēle pa spēlei / "kā tas notika"
    flīzes, sezonas skaitļi un vieta konteksta joslai. → (attēls bez rāmja, konteksta joslas y, augstums)."""
    F = S.fonts
    pl = f_["plus"]
    cw = 760
    rind = [r_ for r_ in (pl.get("rindas") or []) if any(str(x).strip() for x in r_)]
    vis = rind[-8:]
    n = len(vis)
    rindu = 1 if n <= 4 else 2
    per = n if rindu == 1 else math.ceil(n / 2)
    TH, GAP = 112, 12
    y = 452
    st = pl.get("stats") or []
    H = y + (36 + rindu * (TH + GAP) if n else 0) + (36 + 104 + GAP if st else 0) + (86 if pl.get("kont") else 0) + 24
    im = Image.new("RGBA", (cw, H), (0, 0, 0, 0)); di = ImageDraw.Draw(im)
    di.rounded_rectangle([0, 0, cw - 1, H - 1], radius=36, fill=(12, 18, 40, 245))
    bazes = _fj_karte(f_, kr)
    im.alpha_composite(bazes)
    di.rounded_rectangle([3, 3, cw - 4, 440], radius=33, outline=(12, 18, 40, 255), width=6)   # bāzes rāmi nosedz
    di.line([(40, 446), (cw - 40, 446)], fill=(255, 255, 255, 30), width=2)
    if n:
        virs = str(pl.get("virs") or "").upper() + (f"  ·  LAST {n} OF {len(rind)}" if len(rind) > n else "")
        izc_t = str(pl.get("izcelt_txt") or "").upper()               # piem. "4 GOALS IN 2:06" – dzeltens, labajā pusē
        if izc_t:
            fz_ = S.ietilpinat(di, izc_t, "black", 26, 300)
            di.text((cw - 40, y + 4), izc_t, font=fz_, fill=S.DZELTENS, anchor="ra")
            virs_w = cw - 80 - di.textlength(izc_t, font=fz_) - 24
        else:
            virs_w = cw - 80
        di.text((40, y + 4), virs, font=S.ietilpinat(di, virs, "semi", 26, virs_w), fill=_NV_LAB)
        y += 36
        tw = (cw - 80 - GAP * (per - 1)) / per
        izc_k = {(str(p_), str(l_)) for p_, l_ in (pl.get("izcelt") or [])}
        for i, r_ in enumerate(vis):
            row, col = divmod(i, per)
            x = 40 + col * (tw + GAP); yy = y + row * (TH + GAP)
            a_, b_, c_ = (list(r_) + ["", "", ""])[:3]
            izc = (str(a_), str(b_)) in izc_k
            di.rounded_rectangle([x, yy, x + tw, yy + TH], radius=18, fill=_NV_TILE + (255,))
            di.text((x + tw / 2, yy + 22), str(a_).upper(), font=S.ietilpinat(di, str(a_).upper(), "black", 24, tw - 14), fill=S.BALTS, anchor="mm")
            if str(b_).strip():
                di.text((x + tw / 2, yy + 52), str(b_).upper(), font=S.ietilpinat(di, str(b_).upper(), "semi", 22, tw - 14), fill=_NV_LAB, anchor="mm")
            cc_ = str(c_).upper().strip()
            kr_c = S.ZALS if re.match(r"^W\b", cc_) else (S.SARKANS if re.match(r"^(L|OTL)\b", cc_) else S.DZELTENS)   # W / L spēlēm
            if izc:                                                   # izceltā sērija (piem. atspēlēšanās vārti) – dzeltens rāmis
                di.rounded_rectangle([x, yy, x + tw, yy + TH], radius=18, outline=S.DZELTENS + (255,), width=4)
            f_c = S.ietilpinat(di, cc_, "black", 30, tw - 14)
            if di.textlength(cc_, font=f_c) > tw - 14 and " · " in cc_:    # nesatilpst (2 spēlētāji) – divās rindās, vārtu guvējs pirmais
                dal = sorted(cc_.split(" · "), key=lambda x_: 0 if x_.endswith(" G") else 1)
                l1, l2 = dal[0], " · ".join(dal[1:])
                fl = S.ietilpinat(di, max(l1, l2, key=len), "black", 24, tw - 14)
                di.text((x + tw / 2, yy + 77), l1, font=fl, fill=S.DZELTENS if l1.endswith(" G") else kr_c, anchor="mm")
                di.text((x + tw / 2, yy + 99), l2, font=fl, fill=(203, 213, 225) if l2.endswith(" A") else kr_c, anchor="mm")
            else:
                di.text((x + tw / 2, yy + 86), cc_, font=f_c, fill=kr_c, anchor="mm")
        y += rindu * (TH + GAP)
    if st:
        di.text((40, y + 4), str(pl.get("stats_virs") or "SEASON SO FAR").upper(), font=F("semi", 26), fill=_NV_LAB)
        y += 36
        tw = (cw - 80 - GAP * (len(st) - 1)) / len(st)
        for i, (lab_, _, val) in enumerate(st):
            x = 40 + i * (tw + GAP)
            di.rounded_rectangle([x, y, x + tw, y + 104], radius=18, fill=_NV_TILE + (255,))
            di.text((x + tw / 2, y + 42), str(val), font=S.ietilpinat(di, str(val), "black", 48, tw - 16), fill=S.BALTS, anchor="mm")
            di.text((x + tw / 2, y + 84), str(lab_).upper(), font=S.ietilpinat(di, str(lab_).upper(), "semi", 22, tw - 16), fill=_NV_LAB, anchor="mm")
        y += 104 + GAP
    return im, y + 8, H


def aina_fakts_tablo(t, c):
    """TOP N tablo: rindas #1…#N, pašreizējais fakts ielido kā liela kartīte un beigās nolaižas savā rindā."""
    if c.get("izk") == "A" and not c.get("bez_tablo") and len(c.get("fakti") or []) > 1:
        return aina_fakts_tablo_a(t, c)                               # īsā versija – rinda izplešas tabulā (kopš 11.11.2026)
    F = S.fonts
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c, anim=c.get("pirmais", False))
    fakti, nr, n = c["fakti"], c["nr"], len(c["fakti"])
    _fj_virsr(L, t, c["virsr"], 400, 120, staticks=not c.get("pirmais"))
    ilg = c.get("_ilg", c.get("ilgums", 4.0))
    t_dock = ilg - 0.8
    bez_tablo = c.get("bez_tablo") or n < 2
    docked = set(c.get("docked") or [])
    f_ = next(x for x in fakti if x["nr"] == nr)
    plus = bool(f_.get("plus")) and not bez_tablo and nr != 1 and not c.get("bez_plus")   # bez_plus – īsā versija
    k_exp = 0.0
    if plus:                                                          # izvēršas, kamēr runā balss; pirms nolaišanās – sakļaujas
        k_exp = S.ease(min(1.0, max(0.0, (t - 0.8) / 0.6))) * (1 - S.ease(min(1.0, max(0.0, (t - (t_dock - 0.55)) / 0.45))))
    L0, d0 = L, d
    if plus:
        L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    if not bez_tablo:
        kp = 1.0 if not c.get("pirmais") else S.ease(min(1.0, max(0.0, (t - 0.3) / 0.4)))
        y0, y1 = 1010, 1010 + n * 76 + 40
        if kp > 0:
            yb = y0 + (y1 - y0) * kp
            d.rounded_rectangle([90, y0, 990, yb], radius=36, fill=(10, 14, 32, 235))
            dn.rounded_rectangle([90, y0, 990, yb], radius=36, outline=S.ZILS + (220,), width=4)
            if kp < 1:
                _skeneris(N, 90, 990, yb)
        if kp >= 1:
            for rw in fakti:                                          # (ne f_ – tas ir pašreizējais fakts)
                y = y0 + 20 + (rw["nr"] - 1) * 76
                atv = rw["nr"] in docked or (rw["nr"] == nr and t >= t_dock + (FJ_NOL - 0.05 if FJ_ANIM in FJ_EFEKTI else 0.45))
                kr = tuple(rw["kr"])
                d.rounded_rectangle([110, y, 970, y + 64], radius=18, fill=(255, 255, 255, 26 if atv else 14))
                d.text((140, y + 32), f"#{rw['nr']}", font=F("black", 40), fill=(kr if atv else _NV_LAB), anchor="lm")
                if atv:
                    ka = 1.0 if rw["nr"] in docked else min(1.0, (t - t_dock - (FJ_NOL - 0.05 if FJ_ANIM in FJ_EFEKTI else 0.45)) / 0.25)
                    if rw.get("badge"):
                        _fj_ripa(d, 250, y + 32, 24, rw["badge"], int(255 * ka))
                    vv = str(rw.get("vards") or "").upper()
                    d.text((290, y + 32), vv, font=S.ietilpinat(d, vv, "black", 34, 330), fill=S.BALTS + (int(255 * ka),), anchor="lm")
                    ds_ = " ".join(rw.get("hook") or [])
                    d.text((950, y + 32), ds_, font=S.ietilpinat(d, ds_, "semi", 26, 300), fill=_NV_LAB + (int(255 * ka),), anchor="rm")
                else:                                                 # arī #1 – LOCKED (bez "? ? ?", kopš 11.11.2026)
                    d.text((540, y + 32), "LOCKED", font=F("semi", 28), fill=_NV_LAB + (120,), anchor="mm")
    if plus:                                                          # tablo slānis – pritumšināts, kamēr kartīte izvērsta
        fb = 1 - 0.85 * k_exp
        for lay in (L, N):
            if fb < 1:
                lay.putalpha(lay.getchannel("A").point(lambda v: int(v * fb)))
        L0.alpha_composite(_nv_glow(N, 12, 1.2)); L0.alpha_composite(L)
        L, d, N, dn = L0, d0, Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)), None
        dn = ImageDraw.Draw(N)
    # lielā kartīte
    if "_kesa" not in c:
        c["_kesa"] = _fj_karte(f_, f_["kr"])
    im = c["_kesa"]
    k = t - 0.1
    if plus and k_exp > 0.001:                                        # izvērstā kartīte (atritinās uz leju)
        if "_kesa_p" not in c:
            c["_kesa_p"] = _fj_karte_plus(f_, f_["kr"])
        imp, y_k, H = c["_kesa_p"]
        hv = int(440 + (H - 440) * k_exp)
        cr = imp.crop((0, 0, 760, hv))
        from PIL import ImageChops
        m_ = Image.new("L", cr.size, 0); ImageDraw.Draw(m_).rounded_rectangle([0, 0, 759, hv - 1], radius=36, fill=255)
        cr.putalpha(ImageChops.multiply(cr.getchannel("A"), m_))
        L.alpha_composite(cr, (160, 510))
        kr_ = tuple(f_["kr"])
        dn.rounded_rectangle([160, 510, 919, 510 + hv - 1], radius=36, outline=kr_ + (255,), width=6)
        # konteksta josla – kad balss to saka
        kont = (f_.get("plus") or {}).get("kont")
        if kont and k_exp > 0.95:
            vardi = c.get("_vardi") or []
            n_pre = len(str((f_.get("plus") or {}).get("runa_pre", "")).split())
            t_k = vardi[n_pre][0] if 0 < n_pre < len(vardi) else 0.5 * ilg
            kk = (t - t_k) / 0.3
            if kk > 0:
                ch = Image.new("RGBA", (680, 70), (0, 0, 0, 0)); dch = ImageDraw.Draw(ch)
                dch.rounded_rectangle([0, 0, 679, 69], radius=22, fill=S.DZELTENS)
                dch.text((340, 35), str(kont).upper(), font=S.ietilpinat(dch, str(kont).upper(), "black", 32, 640), fill=S.MELNS, anchor="mm")
                _nv_put(L, ch, 540, 510 + y_k + 35, 1 + 0.35 * (1 - ease_back(min(1.0, kk))), min(1.0, kk * 2.5))
    elif k > 0:
        sy_ = 1010 + 20 + (nr - 1) * 76 + 32                          # savas rindas centrs tablo
        if FJ_ANIM in FJ_EFEKTI:                                      # jaunie efekti (1–5) – zīmē paši
            FJ_EFEKTI[FJ_ANIM](L, N, im, k, t, t_dock, bez_tablo, sy_, tuple(f_["kr"]), nr)
            L.alpha_composite(_nv_glow(N, 12, 1.2))
            return L
        cx, cy, sx, sy, a = _fj_anim(FJ_ANIM, k, t, t_dock, bez_tablo, sy_, im)
        if a > 0.01 and sx > 0.01 and sy > 0.01:
            im2 = im if (sx, sy) == (1.0, 1.0) else im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.BICUBIC)
            _nv_put(L, im2, cx, cy, 1.0, a)
        if FJ_ANIM in ("D", "E") and not bez_tablo and t >= t_dock:  # rinda iemirdzas, kad kartīte tajā "ielec"
            g_ = 1 - min(1.0, max(0.0, (t - t_dock - 0.4) / 0.5))
            if g_ > 0 and t >= t_dock + 0.3:
                dn.rounded_rectangle([110, sy_ - 32, 970, sy_ + 32], radius=18, outline=tuple(f_["kr"]) + (int(255 * g_),), width=5)
    L.alpha_composite(_nv_glow(N, 12, 1.2))
    if FJ_ANIM == "E" and not bez_tablo and not plus:
        L = _nv_kratit(L, t, t_dock + 0.38, amp=10, dur=0.2)
    return L


# ---------------------------------------------------------------- TOP N tablo – variants A (kopš 11.11.2026, īsā versija)
# Nav loga virs tabulas: tabula aizpilda ekrānu (centrēta), pašreizējā fakta rinda izplešas lielā kartītē turpat tabulā
# (pārējās rindas pabīdās), kamēr balss runā; beigās saplok atpakaļ kompaktā rindā (vārds + fakts). #1 – LOCKED līdz
# savai kārtai un paliek izvērsts līdz ainas beigām. Garajā versijā (--long) – iepriekšējais izkārtojums.
FJA_Y0, FJA_Y1 = 500, 1690       # tabulas laukums ainas koordinātās (drošā zona ×0,82 → video ~455–1430, virs subtitriem)
FJA_X0, FJA_X1 = 50, 1030
FJA_G = 14


def _fja_izm(n):
    """(kompaktās rindas augstums, izvērstās rindas augstums) – lai tabula aizpilda laukumu arī ar 2–3 faktiem."""
    rh = {2: 200, 3: 180, 4: 148}.get(n, 128)
    eh = min(820, (FJA_Y1 - FJA_Y0) - (n - 1) * (rh + FJA_G))
    return rh, eh


def _fja_laiki(c):
    """(izvēršanās sākums, sakļaušanās sākums | None) – #1 paliek izvērsts līdz ainas beigām."""
    ilg = c.get("_ilg", c.get("ilgums", 4.0))
    t_open = 0.95 if c.get("pirmais") else 0.15
    t_close = None if c.get("nr") == 1 else max(t_open + 1.0, ilg - 0.75)
    return t_open, t_close


def _fja_saturs(f_, W, H):
    """Izvērstās rindas saturs (bez fona): #nr, komanda, galvenais skaitlis, apraksts, vārds."""
    F = S.fonts
    kr = tuple(f_["kr"])
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((42, 30), f"#{f_['nr']}", font=F("black", int(min(110, H * 0.15))), fill=kr)
    r = int(min(66, H * 0.09))
    if f_.get("badge"):
        _fj_ripa(d, W - 44 - r, 34 + r, r, f_["badge"])
    h = [str(x) for x in (f_.get("hook") or [""])]
    d.text((W / 2, H * 0.47), h[0], font=S.ietilpinat(d, h[0], "black", int(min(200, H * 0.27)), W - 100), fill=S.BALTS, anchor="mm")
    if len(h) > 1:
        r_ = " ".join(h[1:])
        d.text((W / 2, H * 0.665), r_, font=S.ietilpinat(d, r_, "black", int(min(74, H * 0.1)), W - 100), fill=S.DZELTENS, anchor="mm")
    v = str(f_.get("vards_pilns") or f_.get("vards") or "").upper()
    d.text((W / 2, H * 0.835), v, font=S.ietilpinat(d, v, "semi", int(min(54, H * 0.075)), W - 100), fill=_NV_LAB, anchor="mm")
    return im


def _fja_rinda(d, dn, y, h, rw, atv, t, a=1.0):
    """Kompaktā rinda: atvērta – #nr, komanda, vārds + fakts; vēl neatklāta (arī #1) – LOCKED."""
    F = S.fonts
    x0, x1 = FJA_X0, FJA_X1
    kr = tuple(rw["kr"])
    A = lambda v: int(v * a)
    d.rounded_rectangle([x0, y, x1, y + h], radius=22, fill=(12, 18, 40, A(235)) if atv else (255, 255, 255, A(16)))
    fnr = F("black", int(h * 0.34))
    d.text((x0 + 30, y + h / 2), f"#{rw['nr']}", font=fnr, fill=(kr if atv else _NV_LAB) + (A(255),), anchor="lm")
    if atv:
        dn.rounded_rectangle([x0, y, x1, y + h], radius=22, outline=kr + (A(110),), width=3)
        r = int(h * 0.21)
        cx = x0 + 30 + d.textlength("#5", font=fnr) + 26 + r
        if rw.get("badge"):
            _fj_ripa(d, cx, y + h / 2, r, rw["badge"], A(255))
        xt = cx + r + 24
        vv = str(rw.get("vards") or "").upper()
        d.text((xt, y + h * 0.37), vv, font=S.ietilpinat(d, vv, "black", int(h * 0.29), x1 - 30 - xt), fill=S.BALTS + (A(255),), anchor="lm")
        ds_ = " ".join(str(x) for x in (rw.get("hook") or []))
        d.text((xt, y + h * 0.72), ds_, font=S.ietilpinat(d, ds_, "semi", int(h * 0.2), x1 - 30 - xt), fill=(203, 213, 225, A(255)), anchor="lm")
    else:                                                             # neatklāta (arī #1) – LOCKED
        d.text(((x0 + x1) / 2, y + h / 2), "LOCKED", font=F("semi", int(h * 0.2)), fill=_NV_LAB + (A(130),), anchor="mm")


def aina_fakts_tablo_a(t, c):
    """TOP N (variants A): tabula pa visu laukumu, pašreizējā rinda izplešas lielā kartītē un beigās saplok."""
    from PIL import ImageChops
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c, anim=c.get("pirmais", False))
    _fj_virsr(L, t, c["virsr"], 400, 120, staticks=not c.get("pirmais"))
    fakti, nr = c["fakti"], c["nr"]
    n = len(fakti)
    docked = set(c.get("docked") or [])
    rh, eh = _fja_izm(n)
    t_open, t_close = _fja_laiki(c)
    k_o = S.ease(min(1.0, max(0.0, (t - t_open) / 0.5)))
    k_c = S.ease(min(1.0, max(0.0, (t - t_close) / 0.45))) if t_close is not None else 0.0
    k = k_o * (1 - k_c)
    aug = {rw["nr"]: (rh + (eh - rh) * k if rw["nr"] == nr else rh) for rw in fakti}
    kopa = sum(aug.values()) + (n - 1) * FJA_G
    y = (FJA_Y0 + FJA_Y1) / 2 - kopa / 2                              # centrēta – izvēršoties rindas pabīdās uz augšu / leju
    W = FJA_X1 - FJA_X0
    for i, rw in enumerate(sorted(fakti, key=lambda r_: r_["nr"])):
        h = aug[rw["nr"]]
        a = 1.0
        if c.get("pirmais"):                                          # pirmā aina – rindas uzrodas pa vienai
            a = S.ease(min(1.0, max(0.0, (t - 0.3 - 0.09 * i) / 0.3)))
        if a <= 0:
            y += h + FJA_G
            continue
        yy = y + (1 - a) * 40
        if rw["nr"] == nr and k > 0.001:                              # izvērstā rinda
            kr = tuple(rw["kr"])
            hi = int(round(h))
            d.rounded_rectangle([FJA_X0, yy, FJA_X1, yy + hi], radius=30, fill=(12, 18, 40, 250))
            dn.rounded_rectangle([FJA_X0, yy, FJA_X1, yy + hi], radius=30, outline=kr + (255,), width=6)
            if "_kesa_a" not in c:
                c["_kesa_a"] = _fja_saturs(rw, W, eh)
            sat = c["_kesa_a"]
            ca = min(1.0, k_o * 1.4) * (1 - min(1.0, k_c * 1.8))      # saturs – atritinās ar augstumu, sakļaujoties izgaist
            if ca > 0.01 and hi > 8:
                cr = sat.crop((0, 0, W, min(eh, hi)))
                if ca < 1:
                    cr.putalpha(cr.getchannel("A").point(lambda v: int(v * ca)))
                L.alpha_composite(cr, (FJA_X0, int(yy)))
            if k_c > 0.4:                                             # sakļaujoties – parādās kompaktais saturs
                _fja_rinda(d, dn, yy, hi, rw, True, t, min(1.0, (k_c - 0.4) / 0.4))
            if k_o < 1:                                               # skeneris pa apakšējo malu, kamēr izplešas
                _skeneris(N, FJA_X0 + 10, FJA_X1 - 10, yy + hi - 4, 1 - k_o)
        else:
            atv = rw["nr"] in docked or (rw["nr"] == nr and k_c >= 1)
            _fja_rinda(d, dn, yy, h, rw, atv, t, a)
            if rw["nr"] == nr and t_close is not None and k_c >= 1:  # nolaižoties – rinda iemirdzas
                g_ = 1 - min(1.0, max(0.0, (t - t_close - 0.45) / 0.5))
                if g_ > 0:
                    dn.rounded_rectangle([FJA_X0, yy, FJA_X1, yy + h], radius=22, outline=tuple(rw["kr"]) + (int(255 * g_),), width=6)
        y += h + FJA_G
    L.alpha_composite(_nv_glow(N, 12, 1.2))                          # neona rāmji – virs rindām (kā iepriekš)
    return L


# ---- TOP N kartītes efekti 1–5 (kopš 09.11.2026): katrs – sava uzrašanās un iekrišana atpakaļ sarakstā
#   1 – MOZAĪKA:  kartīte salido no 40 flīzēm; atpakaļ – flīzes pa vienai "ieber" savā rindā
#   2 – SKENERIS: dzeltena skenera līnija "uzzīmē" kartīti no augšas; atpakaļ – saplok gaismas strīpā, kas ielido rindā
#   3 – RIPA:     ripa ielido, trieciens ar zibsni un dzirkstelēm, kartīte izlec griežoties; atpakaļ – griežas kā metiens rindā
#   4 – PRINTERIS: rinda atveras, kartīte izslīd no tās uz augšu kā čeks; atpakaļ – ieslīd rindā un tā aizveras
#   5 – GLITCH:   kartīte "teleportējas" sagriezta joslās ar RGB nobīdi; atpakaļ – izjūk joslās un sabrūk rindā
FJ_IEN, FJ_NOL = 0.6, 0.6        # s – uzrašanās / iekrišana


def _skeneris(N, x0, x1, y, a=1.0):
    """Dzeltena skenera līnija ar mirdzumu (lietota visur, kur logs / saraksts atklājas no augšas)."""
    if a <= 0.01:
        return
    dn = ImageDraw.Draw(N)
    for g_, al in ((14, 50), (8, 90)):
        dn.rectangle([x0 - 20, y - g_, x1 + 20, y + g_], fill=S.DZELTENS + (int(al * a),))
    dn.rectangle([x0 - 20, y - 3, x1 + 20, y + 3], fill=S.DZELTENS + (int(255 * a),))


def _fj_lim(x):
    return min(1.0, max(0.0, x))


def _fj_rinda_zib(N, sy_, kr, t, t_dock):
    """Rinda iemirdzas, kad kartīte tajā "ielec"."""
    g = 1 - _fj_lim((t - t_dock - FJ_NOL + 0.05) / 0.5)
    if t >= t_dock + FJ_NOL - 0.1 and g > 0:
        ImageDraw.Draw(N).rounded_rectangle([110, sy_ - 32, 970, sy_ + 32], radius=18, outline=kr + (int(255 * g),), width=5)


def _fj_ef_mozaika(L, N, im, k, t, t_dock, bez_tablo, sy_, kr, nr):
    C, R = 8, 5
    tw, th = im.width / C, im.height / R
    x0, y0 = 540 - im.width / 2, 730 - im.height / 2
    nol = not bez_tablo and t >= t_dock
    for j in range(R):
        for i in range(C):
            rnd = random.Random(nr * 1000 + j * C + i)
            box = (int(i * tw), int(j * th), int((i + 1) * tw), int((j + 1) * th))
            tile = im.crop(box)
            tx, ty = x0 + box[0] + tw / 2, y0 + box[1] + th / 2
            d_ = (i + j) * 0.022
            if nol:
                q = S.ease(_fj_lim((t - t_dock - d_ * 0.8) / 0.32))
                gx, gy = 120 + (i + 0.5) / C * 840, sy_
                cx, cy = tx + (gx - tx) * q, ty + (gy - ty) * q - math.sin(math.pi * q) * 120
                sc, rot, a = 1 - 0.85 * q, 0, 1 - _fj_lim((q - 0.7) / 0.3)
            else:
                p = _fj_lim((k - d_) / 0.38)
                if p <= 0:
                    continue
                e = ease_back(p, 1.2)
                ox, oy, orot = rnd.uniform(-700, 700), rnd.uniform(-900, 900), rnd.uniform(-160, 160)
                cx, cy = tx + ox * (1 - e), ty + oy * (1 - e)
                sc, rot, a = 0.4 + 0.6 * e, orot * (1 - p), _fj_lim(p * 2.5)
            if a > 0.01:
                _nv_put(L, tile, cx, cy, sc, a, rot)
    if nol:
        _fj_rinda_zib(N, sy_, kr, t, t_dock)


def _fj_ef_skeneris(L, N, im, k, t, t_dock, bez_tablo, sy_, kr, nr):
    W, H = im.width, im.height
    x0, y0 = int(540 - W / 2), int(730 - H / 2)
    dn = ImageDraw.Draw(N)
    if not bez_tablo and t >= t_dock:
        q = _fj_lim((t - t_dock) / FJ_NOL)
        if q < 0.45:                                                  # saplok strīpā
            sy = max(0.02, 1 - S.ease(q / 0.45))
            sm = im.resize((W, max(2, int(H * sy))), Image.BICUBIC)
            _nv_put(L, sm, 540, 730, 1, 1)
            dn.rounded_rectangle([x0, 730 - 4, x0 + W, 730 + 4], radius=4, fill=S.DZELTENS + (int(255 * S.ease(q / 0.45)),))
        else:                                                         # strīpa ielido rindā un izplešas
            qq = S.ease((q - 0.45) / 0.55)
            yy = 730 + (sy_ - 730) * qq
            hw = W / 2 + (430 - W / 2) * qq
            a = 1 - _fj_lim((qq - 0.75) / 0.25)
            dn.rounded_rectangle([540 - hw, yy - 4 - 28 * qq, 540 + hw, yy + 4 + 28 * qq], radius=14,
                                 outline=S.DZELTENS + (int(255 * a),), width=6)
        _fj_rinda_zib(N, sy_, kr, t, t_dock)
        return
    p = _fj_lim(k / FJ_IEN)
    h = int(H * S.ease(p))
    if h > 2:
        fl = 0.85 + 0.15 * math.sin(t * 60) if p < 1 else 1.0
        L.alpha_composite(_ar_alfu(im.crop((0, 0, W, h)), fl) if fl < 1 else im.crop((0, 0, W, h)), (x0, y0))
        if p < 1:
            yl = y0 + h
            dn.rectangle([x0 - 30, yl - 3, x0 + W + 30, yl + 3], fill=S.DZELTENS + (255,))
            for g_, al in ((14, 50), (8, 90)):
                dn.rectangle([x0 - 30, yl - g_, x0 + W + 30, yl + g_], fill=S.DZELTENS + (al,))


def _fj_ef_ripa(L, N, im, k, t, t_dock, bez_tablo, sy_, kr, nr):
    dn = ImageDraw.Draw(N)
    if not bez_tablo and t >= t_dock:
        q = _fj_lim((t - t_dock) / FJ_NOL)
        for g_ in (0.12, 0.06, 0.0):                                  # pēdas (motion trail)
            qq = S.ease(_fj_lim(q - g_))
            cx, cy = 540 + math.sin(qq * math.pi) * 220, 730 + (sy_ - 730) * qq
            _nv_put(L, im, cx, cy, max(0.02, 1 - 0.9 * qq), (1 - qq) * (0.35 if g_ else 1), 540 * qq)
        _fj_rinda_zib(N, sy_, kr, t, t_dock)
        return
    if k < 0.18:                                                      # ripa lido
        p = k / 0.18
        x = -80 + (540 + 80) * p
        for i in range(6):
            dn.line([(x - 40 - i * 30, 730), (x - 60 - i * 30, 730)], fill=(255, 255, 255, 120 - i * 18), width=10 - i)
        ImageDraw.Draw(L).ellipse([x - 26, 714, x + 26, 746], fill=(20, 20, 24, 255), outline=(90, 90, 100, 255), width=3)
        return
    p = _fj_lim((k - 0.18) / 0.42)
    if p < 0.35:                                                      # trieciens: zibsnis + dzirksteles
        z = 1 - p / 0.35
        dn.ellipse([540 - 300 * (1 - z) - 40, 730 - 300 * (1 - z) - 40, 540 + 300 * (1 - z) + 40, 730 + 300 * (1 - z) + 40],
                   outline=(255, 255, 255, int(220 * z)), width=8)
        rnd = random.Random(nr)
        for i in range(14):
            an = rnd.uniform(0, 2 * math.pi); r0, r1 = 60 + 500 * (1 - z), 120 + 620 * (1 - z)
            dn.line([(540 + math.cos(an) * r0, 730 + math.sin(an) * r0), (540 + math.cos(an) * r1, 730 + math.sin(an) * r1)],
                    fill=S.DZELTENS + (int(255 * z),), width=5)
    e = ease_back(p, 1.8)
    _nv_put(L, im, 540, 730, max(0.05, e), _fj_lim(p * 3), 25 * (1 - p))


def _fj_ef_printeris(L, N, im, k, t, t_dock, bez_tablo, sy_, kr, nr):
    W, H = im.width, im.height
    dn = ImageDraw.Draw(N)
    sl = sy_ - 32 if not bez_tablo else 730 + H / 2                   # "sprauga" – rindas augšmala
    nol = not bez_tablo and t >= t_dock
    q = S.ease(_fj_lim((t - t_dock) / FJ_NOL)) if nol else 1 - S.ease(_fj_lim(k / FJ_IEN))
    cy = 730 + (sl + H / 2 - 730) * q                                 # q=0 – augšā, q=1 – pilnībā spraugā
    top = int(cy - H / 2)
    vis = int(min(H, sl - top))
    if vis > 2:
        L.alpha_composite(im.crop((0, 0, W, vis)), (int(540 - W / 2), top))
    if 0 < q < 1 or (nol and q < 1):                                  # sprauga mirdz, kamēr kartīte iet cauri
        dn.rounded_rectangle([540 - W / 2 - 20, sl - 5, 540 + W / 2 + 20, sl + 5], radius=5, fill=kr + (230,))
    if nol:
        _fj_rinda_zib(N, sy_, kr, t, t_dock)


def _fj_ef_glitch(L, N, im, k, t, t_dock, bez_tablo, sy_, kr, nr):
    W, H = im.width, im.height
    nol = not bez_tablo and t >= t_dock
    if nol:
        q = _fj_lim((t - t_dock) / FJ_NOL)
        sila, cy, sx, sy = q, 730 + (sy_ - 730) * S.ease(q), 1 + (860 / W - 1) * S.ease(q), 1 + (64 / H - 1) * S.ease(q)
        a = 1 - _fj_lim((q - 0.8) / 0.2)
    else:
        p = _fj_lim(k / FJ_IEN)
        sila, cy, sx, sy, a = 1 - p, 730, 1.0, 1.0, _fj_lim(p * 3)
    if a <= 0.01:
        if nol:
            _fj_rinda_zib(N, sy_, kr, t, t_dock)
        return
    src = im if (sx, sy) == (1.0, 1.0) else im.resize((max(1, int(W * sx)), max(1, int(H * sy))), Image.BICUBIC)
    w2, h2 = src.size
    rnd = random.Random(int(t * 30))
    n_ = 10
    for i in range(n_):
        y1, y2 = int(i * h2 / n_), int((i + 1) * h2 / n_)
        if y2 <= y1:
            continue
        sl_ = src.crop((0, y1, w2, y2))
        dx = rnd.uniform(-1, 1) * 260 * sila ** 1.5
        x = 540 - w2 / 2 + dx
        y = cy - h2 / 2 + y1
        if sila > 0.05:                                               # RGB nobīde
            r_, g_, b_, a_ = sl_.split()
            sar = Image.merge("RGBA", (r_, Image.new("L", sl_.size, 0), Image.new("L", sl_.size, 0), a_.point(lambda v: int(v * 0.6 * a))))
            zil = Image.merge("RGBA", (Image.new("L", sl_.size, 0), g_, b_, a_.point(lambda v: int(v * 0.6 * a))))
            L.alpha_composite(sar, (int(x - 18 * sila), int(y)))
            L.alpha_composite(zil, (int(x + 18 * sila), int(y)))
        L.alpha_composite(_ar_alfu(sl_, a * (0.55 + 0.45 * (1 - sila))), (int(x), int(y)))
    if nol:
        _fj_rinda_zib(N, sy_, kr, t, t_dock)


FJ_EFEKTI = {"1": _fj_ef_mozaika, "2": _fj_ef_skeneris, "3": _fj_ef_ripa, "4": _fj_ef_printeris, "5": _fj_ef_glitch}


# TOP N faktu kartītes animācija (kopš 09.11.2026 – 5 varianti; izvēle FJ_ANIM):
#   A – "punch": ielido no lielāka (kā līdz 09.11.), nolaižas – sarūk savā rindā
#   B – "slide": ieslīd no labās, nolaižas – pārvēršas rindā (saplacinās līdz rindas augstumam)
#   C – "flip": apgriežas kā kārts (no šauras), nolaižas – apgriežas atpakaļ rindā
#   D – "no rindas": izaug no savas rindas tablo un atgriežas tajā (rinda iemirdzas)
#   E – "drop": iekrīt no augšas ar atsitienu, nolaižas – strauji iekrīt rindā (rinda iemirdzas, kadrs nodreb)
FJ_ANIM = "2"                    # standarts kopš 09.11.2026 – SKENERIS (A = vecā "punch")


def _fj_anim(v, k, t, t_dock, bez_tablo, sy_, im):
    """→ (cx, cy, x mērogs, y mērogs, caurspīdīgums) lielajai kartītei (ielidošana / stāvēšana / nolaišanās)."""
    ease, eb = S.ease, ease_back
    W0, H0 = im.width, im.height
    rx, ry = 860 / W0, 64 / H0                                        # rindas izmērs pret kartīti
    ien = 0.45 if v in ("B", "D", "E") else 0.32
    if k < ien:                                                       # --- ielidošana
        p = min(1.0, k / ien)
        if v == "B":
            return 540 + (1 - eb(p)) * 900, 730, 1.0, 1.0, min(1.0, p * 3)
        if v == "C":
            return 540, 730, max(0.02, ease(p)), 1.0, min(1.0, p * 4)
        if v == "D" and not bez_tablo:
            q = eb(p, 1.4)
            return 540, sy_ + (730 - sy_) * q, rx + (1 - rx) * q, ry + (1 - ry) * q, min(1.0, p * 4)
        if v == "E":
            return 540, -300 + (730 + 300) * eb(p, 2.4), 1.0, 1.0, 1.0
        sc = 1.4 - 0.4 * eb(p)
        return 540, 730, sc, sc, min(1.0, k / 0.15)
    if bez_tablo or t < t_dock:
        return 540, 730, 1.0, 1.0, 1.0
    q = ease(min(1.0, (t - t_dock) / 0.45))                           # --- nolaišanās savā rindā
    if v in ("B", "D"):
        return 540, 730 + (sy_ - 730) * q, 1 + (rx - 1) * q, 1 + (ry - 1) * q, 1 - max(0.0, (q - 0.75) / 0.25)
    if v == "C":
        return 540, 730 + (sy_ - 730) * q, 1 + (rx - 1) * q, max(0.02, 1 - q), 1.0 if q < 0.9 else (1 - q) * 10
    if v == "E":
        qq = min(1.0, (t - t_dock) / 0.38) ** 2
        return 540, 730 + (sy_ - 730) * qq, 1 + (rx - 1) * qq, 1 + (ry - 1) * qq, 1.0 if qq < 1 else 0.0
    return 540, 730 + (sy_ - 730) * q, 1 - 0.85 * q, 1 - 0.85 * q, 1 - q


def _fj_laukums(d, x0, y0, w, h):
    """Uzbrukuma zona (no zilās līnijas līdz galam); → (X, Y) koordinātu funkcijas."""
    X = lambda v: x0 + (v - 25) / 75 * w                              # noqa: E731
    Yf = lambda v: y0 + (v + 42.5) / 85 * h                          # noqa: E731
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(h * 0.3), fill=(14, 22, 48, 255), outline=(148, 163, 184, 160), width=4)
    d.line([(X(25) + 3, y0 + 4), (X(25) + 3, y0 + h - 4)], fill=S.ZILS + (200,), width=8)
    d.line([(X(89), y0 + 14), (X(89), y0 + h - 14)], fill=S.SARKANS + (180,), width=4)
    d.pieslice([X(89) - h * 0.1, Yf(0) - h * 0.1, X(89) + h * 0.1, Yf(0) + h * 0.1], 90, 270, fill=S.ZILS + (90,))
    for yc in (-22, 22):
        r_ = h * 0.18
        d.ellipse([X(69) - r_, Yf(yc) - r_, X(69) + r_, Yf(yc) + r_], outline=S.SARKANS + (130,), width=3)
        d.ellipse([X(69) - 6, Yf(yc) - 6, X(69) + 6, Yf(yc) + 6], fill=S.SARKANS + (160,))
    d.rectangle([X(89), Yf(-3), X(92), Yf(3)], outline=S.BALTS + (200,), width=3)
    return X, Yf


_FJ_KR = {"G": S.DZELTENS, "A": S.ZILS, "GA": S.SARKANS, "S": (203, 213, 225)}


FJ_RIPA_PAUZE = 2.8              # s – pēc pēdējās ripas aina vēl stāv (var apskatīt visus vārtus kopā)


def _fj_ripa_dt(ilg, n):
    """Laiks starp ripām: visas nokrīt FJ_RIPA_PAUZE s pirms ainas beigām (0,9 s sākums, 0,35 s lidojums)."""
    return min(0.5, max(0.06, (ilg - 0.9 - 0.35 - FJ_RIPA_PAUZE) / max(1, n)))


def aina_fakts_ripa(t, c):
    """Katrs sērijas / spēles vārts (vai atvairītais metiens) uz ripas: ripa pa vienai lido vārtos, skaitītājs aug."""
    F = S.fonts
    R = c["ripa"]
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c)
    _fj_virsr(L, t, R["virsr"], 390, 100)
    a0 = S.ease(min(1.0, max(0.0, (t - 0.4) / 0.3)))
    if R.get("apaksa") and a0 > 0:
        S.teksts_c(d, 470, R["apaksa"], S.ietilpinat(d, R["apaksa"], "semi", 34, 900), _NV_LAB + (int(255 * a0),))
    x0, y0, w, h = 90, 540, 900, 700
    k0 = S.ease(min(1.0, max(0.0, (t - 0.3) / 0.4)))
    if k0 <= 0:
        return L
    Lr = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    X, Yf = _fj_laukums(ImageDraw.Draw(Lr), x0, y0, w, h)
    if k0 < 1:
        Lr.putalpha(Lr.getchannel("A").point(lambda v: int(v * k0)))
    L.alpha_composite(Lr)
    pk = R["punkti"]
    ilg = c.get("_ilg", c.get("ilgums", 5.5))
    T0 = 0.9
    DT = _fj_ripa_dt(ilg, len(pk))
    tx, ty = X(89), Yf(0)
    nv, ped = 0, None
    for i, p_ in enumerate(pk):
        k = (t - T0 - i * DT) / 0.35
        if k <= 0:
            continue
        kr = _FJ_KR.get(p_["k"], S.DZELTENS)
        sx, sy = X(p_["x"]), Yf(p_["y"])
        glaba = p_["k"] == "S"
        q = S.ease(min(1.0, k)) * (0.86 if glaba else 1.0)
        d.ellipse([sx - 11, sy - 11, sx + 11, sy + 11], fill=kr + (255,), outline=S.MELNS + (255,), width=3)
        if k < 1:
            for j in range(9):
                qq = max(0.0, q - j * 0.04)
                qx, qy = sx + (tx - sx) * qq, sy + (ty - sy) * qq
                rr = 7 - j * 0.6
                dn.ellipse([qx - rr, qy - rr, qx + rr, qy + rr], fill=S.BALTS + (int(220 * (1 - j / 9)),))
        else:
            d.line([(sx, sy), (sx + (tx - sx) * q, sy + (ty - sy) * q)], fill=kr + (60,), width=3)
            nv += 1 if p_["k"] in R.get("skaita", ("G", "A", "GA", "S")) else 0
            ped = p_
        kf = (t - T0 - i * DT - 0.35) / 0.3
        if 0 < kf < 1:
            rr = 18 + 50 * kf
            if glaba:                                                 # atvairīts – balts "vairogs"
                ex, ey = sx + (tx - sx) * 0.86, sy + (ty - sy) * 0.86
                dn.arc([ex - rr, ey - rr, ex + rr, ey + rr], 120, 240, fill=S.BALTS + (int(255 * (1 - kf)),), width=6)
            else:
                dn.ellipse([tx - rr, ty - rr, tx + rr, ty + rr], outline=kr + (int(255 * (1 - kf)),), width=6)
    if ped and ped.get("lab"):
        d.rounded_rectangle([x0 + 30, y0 + h - 86, x0 + 520, y0 + h - 22], radius=22, fill=(0, 0, 0, 160))
        d.text((x0 + 50, y0 + h - 54), ped["lab"], font=S.ietilpinat(d, ped["lab"], "black", 34, 450), fill=S.BALTS, anchor="lm")
    if R.get("legenda"):                                               # leģenda – augšmalas vidū (stūri ir noapaļoti)
        fl_ = F("black", 26)
        plat_ = sum(d.textlength(lab_, font=fl_) + 34 for lab_, _ in R["legenda"]) + 26 * (len(R["legenda"]) - 1)
        xx = 540 - plat_ / 2
        for lab_, k_ in R["legenda"]:
            d.ellipse([xx, y0 + 26, xx + 20, y0 + 46], fill=_FJ_KR[k_])
            d.text((xx + 30, y0 + 36), lab_, font=fl_, fill=S.BALTS, anchor="lm")
            xx += d.textlength(lab_, font=fl_) + 34 + 26
    beigas_ = t > T0 + len(pk) * DT + 0.4
    if beigas_ and R.get("kopa"):                                      # beigās – īstais kopskaits (arī bez metiena vietas)
        nv = int(R["kopa"])
    d.text((300, 1320), str(nv), font=F("black", 130), fill=_FJ_KR.get(R.get("kr_sk", "G"), S.DZELTENS), anchor="mm")
    if beigas_ and R.get("piezime"):
        d.text((400, 1392), R["piezime"], font=S.ietilpinat(d, R["piezime"], "semi", 24, 580), fill=_NV_LAB, anchor="lm")
    d.text((400, 1300), R["skaititajs"], font=S.ietilpinat(d, R["skaititajs"], "black", 48, 560), fill=S.BALTS, anchor="lm")   # (kopa)
    if R.get("skaititajs2"):
        d.text((400, 1352), R["skaititajs2"], font=S.ietilpinat(d, R["skaititajs2"], "semi", 32, 560), fill=_NV_LAB, anchor="lm")
    st = R.get("stats") or []
    ks = (t - T0 - len(pk) * DT - 0.2) / 0.4
    if st and ks > 0:
        S.teksts_c(d, 1430, R.get("stats_virs", "SEASON SO FAR"), F("semi", 28), _NV_LAB + (int(255 * min(1, ks)),))
        n_ = len(st)
        tw_ = (900 - (n_ - 1) * 16) / n_
        for j, (lab_, val) in enumerate(st):
            kk = ease_back(min(1.0, max(0.0, ks - j * 0.12)))
            if kk <= 0:
                continue
            xx = 90 + j * (tw_ + 16)
            d.rounded_rectangle([xx, 1460, xx + tw_, 1590], radius=22, fill=_NV_TILE + (int(255 * min(1, kk)),))
            d.text((xx + tw_ / 2, 1505), str(val), font=S.ietilpinat(d, str(val), "black", 56, tw_ - 20), fill=S.BALTS, anchor="mm")
            d.text((xx + tw_ / 2, 1562), str(lab_).upper(), font=S.ietilpinat(d, str(lab_).upper(), "semi", 24, tw_ - 20), fill=_NV_LAB, anchor="mm")
    L.alpha_composite(_nv_glow(N, 10, 1.3))
    return L


def aina_fakts_hist(t, c):
    """HOW RARE IS IT? – visas sezonas sērijas / spēles kā stabiņi, varoņa stabiņš dzeltens, beigās zīmogs."""
    F = S.fonts
    H = c["hist"]
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c)
    _fj_virsr(L, t, [("HOW", S.BALTS), ("RARE", S.BALTS), ("IS IT?", S.DZELTENS)], 390, 120)
    a0 = S.ease(min(1.0, max(0.0, (t - 0.4) / 0.3)))
    S.teksts_c(d, 480, H["apaksa"], S.ietilpinat(d, H["apaksa"], "semi", 34, 900), _NV_LAB + (int(255 * a0),))
    kp = S.ease(min(1.0, max(0.0, (t - 0.5) / 0.4)))
    if kp > 0:
        yb = 560 + (1330 - 560) * kp
        d.rounded_rectangle([80, 560, 1000, yb], radius=36, fill=(10, 14, 32, 235))
        dn.rounded_rectangle([80, 560, 1000, yb], radius=36, outline=S.ZILS + (220,), width=4)
        if kp < 1:
            _skeneris(N, 80, 1000, yb)
    if kp >= 1:
        bins = H["bins"]
        PX0, PX1, PY1, HMAX = 140, 940, 1210, 500
        nb = len(bins)
        gap = 20
        bw = (PX1 - PX0 - gap * (nb - 1)) / nb
        mx = max(math.log10(cn + 1) for _, cn in bins) or 1
        for i, (lab, cn) in enumerate(bins):
            k = S.ease(min(1.0, max(0.0, (t - 0.9 - i * 0.14) / 0.5)))
            hh = HMAX * math.log10(cn + 1) / mx * k
            x = PX0 + i * (bw + gap)
            hero = i == H["hero"]
            kr = S.DZELTENS if hero else (90, 104, 130)
            (dn if hero else d).rounded_rectangle([x, PY1 - max(hh, 6), x + bw, PY1], radius=14, fill=kr + (255,))
            if k > 0.6:
                tx_ = f"{cn:,}".replace(",", " ")
                d.text((x + bw / 2, PY1 - hh - 28), tx_, font=S.ietilpinat(d, tx_, "black", 38, bw + 10), fill=(S.DZELTENS if hero else S.BALTS), anchor="mm")
            d.text((x + bw / 2, PY1 + 32), str(lab), font=S.ietilpinat(d, str(lab), "black", 36, bw + 14), fill=(S.DZELTENS if hero else _NV_LAB), anchor="mm")
        d.text((540, PY1 + 80), H["x_lab"], font=S.ietilpinat(d, H["x_lab"], "semi", 28, 860), fill=_NV_LAB, anchor="mm")
        ka = (t - 0.9 - nb * 0.14 - 0.4) / 0.4
        if ka > 0 and H.get("hero_lab"):
            i = H["hero"]
            x = PX0 + i * (bw + gap) + bw / 2
            cn = bins[i][1]
            y = PY1 - HMAX * math.log10(cn + 1) / mx - 104 - 12 * abs(math.sin(t * 4))
            d.polygon([(x - 16, y + 36), (x + 16, y + 36), (x, y + 60)], fill=S.DZELTENS)
            anc = "rm" if x > 760 else ("lm" if x < 320 else "mm")
            d.text((x + (16 if anc == "rm" else (-16 if anc == "lm" else 0)), y + 10), H["hero_lab"], font=F("black", 34),
                   fill=S.DZELTENS, anchor=anc)
        kb = (t - 0.9 - nb * 0.14 - 1.0) / 0.35
        if kb > 0:
            ch = Image.new("RGBA", (880, 150), (0, 0, 0, 0)); dc = ImageDraw.Draw(ch)
            dc.rounded_rectangle([0, 0, 879, 149], radius=40, fill=S.DZELTENS)
            dc.text((440, 52), H["z1"], font=S.ietilpinat(dc, H["z1"], "black", 64, 820), fill=S.MELNS, anchor="mm")
            dc.text((440, 112), H["z2"], font=S.ietilpinat(dc, H["z2"], "black", 34, 820), fill=S.MELNS, anchor="mm")
            _nv_put(L, ch, 540, 1440, 1 + 0.4 * (1 - ease_back(min(1.0, kb))), min(1.0, kb * 2), -3)
    L.alpha_composite(_nv_glow(N, 14, 1.3))
    return L


def aina_fakts_reti(t, c):
    """HOW RARE IS IT? jaunajā izskatā faktiem bez histogrammas (piem. 2–3 biedri vienā spēlē): tablo, liels skaitlis
    kartītē, paskaidrojums, dzeltens zīmogs (konteksts[1]). Līdz 04.11. te rādījās vecā izskata aina."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c)
    _fj_virsr(L, t, [("HOW", S.BALTS), ("RARE", S.BALTS), ("IS IT?", S.DZELTENS)], 390, 120)
    kont = [str(x) for x in (c.get("konteksts") or []) if str(x).strip()]
    kp = S.ease(min(1.0, max(0.0, (t - 0.35) / 0.4)))
    if kp > 0:
        yb = 540 + (1250 - 540) * kp
        d.rounded_rectangle([80, 540, 1000, yb], radius=36, fill=(10, 14, 32, 235))
        ImageDraw.Draw(N).rounded_rectangle([80, 540, 1000, yb], radius=36, outline=S.ZILS + (220,), width=4)
        if kp < 1:
            _skeneris(N, 80, 1000, yb)
    if kp >= 1:
        ks = str(c.get("k_skaitlis") or "")
        k1 = min(1.0, max(0.0, (t - 0.75) / 0.25))
        if ks and k1 > 0:
            sk = skaitit(ks, S.ease(min(1.0, (t - 0.75) / 0.8)))
            f = S.ietilpinat(d, ks, "black", 280, 820)
            _nv_put(N, _nv_timg(sk, f, S.DZELTENS), 540, 760, 1 + 0.35 * (1 - ease_back(k1)), min(1.0, k1 * 2))
        k2 = min(1.0, max(0.0, (t - 1.1) / 0.35))
        if kont and k2 > 0:
            f2, rr = S.rindas_ietilpinat(d, kont[0].upper(), "black", 64, 820, 3)
            y = 1010 - (len(rr) - 1) * f2.size * 0.6
            for r_ in rr:
                S.teksts_c(d, int(y), r_, f2, S.BALTS + (int(255 * k2),))
                y += f2.size * 1.2
    kb = (t - 1.7) / 0.35
    if kb > 0 and len(kont) > 1:
        z = kont[1].upper()
        ch = Image.new("RGBA", (880, 130), (0, 0, 0, 0)); dc = ImageDraw.Draw(ch)
        dc.rounded_rectangle([0, 0, 879, 129], radius=40, fill=S.DZELTENS)
        dc.text((440, 65), z, font=S.ietilpinat(dc, z, "black", 46, 820), fill=S.MELNS, anchor="mm")
        _nv_put(L, ch, 540, 1420, 1 + 0.4 * (1 - ease_back(min(1.0, kb))), min(1.0, kb * 2), -3)
    L.alpha_composite(_nv_glow(N, 14, 1.3))
    return L


def aina_fakts_serijas(t, c):
    """Kopsavilkums pirms verdikta: aktīvās punktu sērijas 10+ (kopā / mājās / izbraukumā) vai nedēļas vārtsargu sērijas
    bez ielaistiem vārtiem (≥ 120 min, arī pārtrauktās). Rindas ielido pa vienai; video jau pieminētā – dzeltenā rāmī."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c)
    _fj_virsr(L, t, c["virsr"], 390, 112)
    a0 = S.ease(min(1.0, max(0.0, (t - 0.35) / 0.3)))
    S.teksts_c(d, 478, c["apaksa"], S.ietilpinat(d, c["apaksa"], "semi", 34, 900), _NV_LAB + (int(255 * a0),))
    rr = c["rindas"][:8]
    if "_izc_t" not in c:                                             # Streak watch: rinda izceļas, kad balss nosauc vārdu
        vardi_, izc_t = c.get("_vardi") or [], {}
        for i_, nm_ in c.get("izc") or []:
            tok = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in str(nm_).split()]
            tt_ = _nv_vards_laiks(vardi_, *tok) if tok and all(tok) else None
            if tt_ is None and tok and tok[-1]:
                tt_ = _nv_vards_laiks(vardi_, tok[-1])
            if tt_ is not None and i_ not in izc_t:
                izc_t[i_] = tt_
        c["_izc_t"] = izc_t
    if len(rr) <= 5:                                                  # rindas – līdz subtitriem (drošā zona ×0,82 → y ≤ 1690)
        RH, GAP, Y0 = int(min(176, (1690 - 560) / max(4, len(rr)) - 16)), 16, 560
    else:
        RH, GAP, Y0 = int(min(132, (1690 - 540) / len(rr) - 12)), 12, 540
    dt_ = 0.22 if len(rr) <= 5 else 0.15
    Y_end = Y0 + len(rr) * (RH + GAP)
    sk_p = min(1.0, max(0.0, (t - 0.6) / (dt_ * len(rr) + 0.3)))      # skeneris iet pa sarakstu uz leju
    y_sk = Y0 + (Y_end - Y0) * S.ease(sk_p)
    if 0 < sk_p < 1:
        _skeneris(N, 80, 1000, y_sk)
    for i, r in enumerate(rr):
        y_r = Y0 + i * (RH + GAP)
        k = min(1.0, max(0.0, (y_sk - y_r) / RH)) if sk_p < 1 else 1.0
        if k <= 0:
            continue
        y = y_r
        al = int(235 * k)
        mans = bool(r.get("video") or r.get("izcelt"))                # dzeltens rāmis: 10+ sērijas / sausās sērijas / video fakts
        d.rounded_rectangle([80, y, 1000, y + RH], radius=30, fill=(10, 14, 32, al))
        (dn if mans else d).rounded_rectangle([80, y, 1000, y + RH], radius=30, outline=(S.DZELTENS if mans else S.ZILS) + (int(220 * k),),
                                              width=4 if mans else 3)
        if i in c["_izc_t"]:                                          # balss nosauc – mirdzošs rāmis ~1,6 s
            dtt = t - c["_izc_t"][i] + 0.1
            g_ = min(1.0, max(0.0, dtt / 0.2)) * (1 - min(1.0, max(0.0, (dtt - 1.1) / 0.5)))
            if g_ > 0:
                d.rounded_rectangle([80, y, 1000, y + RH], radius=30, fill=(255, 255, 255, int(28 * g_)))
                dn.rounded_rectangle([76, y - 4, 1004, y + RH + 4], radius=32, outline=S.DZELTENS + (int(255 * g_),), width=7)
        sk_ = RH / 132
        _fj_ripa(d, 160, y + RH / 2, int(42 * sk_), r.get("team"), int(255 * k))
        nm = str(r["vards"]).upper()
        d.text((230, y + 42 * sk_), nm, font=S.ietilpinat(d, nm, "black", int(46 * sk_), 470), fill=S.BALTS + (int(255 * k),), anchor="lm")
        pw_ = _ser_pill(d, 230, y + 94 * sk_, r.get("kur"), int(20 * sk_), int(255 * k))   # HOME / ROAD zīmīte
        xa_ = 230 + (pw_ + 12 if pw_ else 0)
        d.text((xa_, y + 94 * sk_), r["apaksa"], font=S.ietilpinat(d, r["apaksa"], "semi", int(30 * sk_), 470 - (xa_ - 230)),
               fill=tuple(r.get("apaksa_kr") or _NV_LAB) + (int(255 * k),), anchor="lm")
        kr_l = S.DZELTENS if r.get("izcelt", bool(r.get("video")) or i == 0) else S.BALTS
        d.text((960, y + 50 * sk_), r["liels"], font=S.ietilpinat(d, r["liels"], "black", int(64 * sk_), 260), fill=kr_l + (int(255 * k),), anchor="rm")
        d.text((960, y + 100 * sk_), r["maz"], font=S.ietilpinat(d, r["maz"], "semi", int(26 * sk_), 260), fill=r.get("maz_kr", _NV_LAB) + (int(255 * k),), anchor="rm")
    L.alpha_composite(_nv_glow(N, 12, 1.3))
    return L


# Kopsavilkuma ainu balss – vispārīgi (vārdi un skaitļi redzami sarakstā), nejaušs variants (kopš 09.11.2026)
PS_RUNA_10 = ["Here are the other active point streaks right now.",
              "The longest point streaks still alive this week. Anything in yellow has reached ten games.",
              "Point streaks that are still going.",
              "Who else keeps finding the scoresheet? The longest active point streaks.",
              "Still rolling: the longest active point streaks in the league right now."]
PS_RUNA_NAV = ["Nobody else has reached ten straight games yet. These are the closest.",
               "The longest point streaks still alive right now. Who reaches ten next?",
               "No one is at ten games yet. Here's who's getting close.",
               "Still building: the longest active point streaks right now."]
SS_RUNA = ["All shutout streaks this week, active or ended, and below them, the best save percentages.",
           "This week's longest shutout streaks, still going or already over. Then, the hottest goalies of the week.",
           "The goalies who shut the door this week: every streak of two hours or more, plus the best save percentages.",
           "Brick walls of the week. Shutout streaks on top, the hottest goalies below.",
           "Minutes without a goal: this week's longest shutout streaks, plus the goalies who were hardest to beat."]
SS_RUNA_NAV = ["No two-hour shutout streak this week. These goalies were still the hottest.",
               "Nobody went two hours without allowing a goal this week. Here's who stopped the most.",
               "No shutout streaks this week, but these goalies were hard to beat.",
               "The goalies of the week, ranked by save percentage."]


SS_SOLO = ["Now, the goalies of the week.", "In net this week:", "The brick walls of the week.", "And the goalies of the week."]
SS_SOLO_NAV = ["No two-hour shutout streak this week, but these goalies were hard to beat.",
               "Nobody went two hours without allowing a goal this week. The hottest goalies instead."]
_SER_KUR = {"HOME": " at home", "AWAY": " on the road", "ALL": ""}


def _ps_stasts(ps):
    """Streak watch – punktu sērijas balsī: līderis, otrais, nākamā grupa ar vienādu skaitu, mājas / izbraukuma sērija,
    cik ir 10+. → (teksts, [(rindas nr, vārds)] – rinda izceļas, kad balss nosauc vārdu)."""
    if not ps:
        return "", []
    out, izc = [], []
    vis = {"G": ", with a goal in every one", "A": ", with an assist in every one"}
    a = ps[0]
    out.append(f"{a['vards']} leads with {a['n']} straight games{_SER_KUR.get(a['veids'], '')}{vis.get(a.get('visi'), '')}.")
    izc.append((0, a["vards"]))
    if len(ps) > 1:
        b = ps[1]
        out.append((f"{b['vards']} also has {b['n']}" if b["n"] == a["n"] else f"{b['vards']} is next with {b['n']}")
                   + f"{_SER_KUR.get(b['veids'], '')}{vis.get(b.get('visi'), '')}.")
        izc.append((1, b["vards"]))
    gr = [i for i in range(2, len(ps)) if ps[i]["veids"] == "ALL"]
    if gr:
        n3 = ps[gr[0]]["n"]
        gr = [i for i in gr if ps[i]["n"] == n3][:3]
        if len(gr) == 1:
            out.append(f"{ps[gr[0]]['vards']} has {n3}.")
        else:
            out.append(f"{_vardu_saraksts([ps[i]['vards'].split()[-1] for i in gr])} are all at {n3}.")
        izc += [(i, ps[i]["vards"]) for i in gr]
    mj = next((i for i in range(2, len(ps)) if ps[i]["veids"] != "ALL" and i not in [x for x, _ in izc]), None)
    if mj is not None:
        x = ps[mj]
        verb_ = {"G": "has scored in", "A": "has an assist in"}.get(x.get("visi"), "has a point in")
        out.append(f"{x['vards']} {verb_} {x['n']} straight {'home' if x['veids'] == 'HOME' else 'road'} games.")
        izc.append((mj, x["vards"]))
    k10 = sum(1 for x in ps if x["n"] >= S.PUNKTU_SERIJA_MIN)
    if k10 >= 3:
        out.append(f"{_VARDIEM.get(k10, str(k10)).capitalize()} streaks are at ten games or more.")
    return " ".join(out), izc


def _ss_stasts(ss, labakie):
    """Streak watch – vārtsargi balsī: 1–2 garākās sausās sērijas (minūtes, vai turpinās) un labākais atvairīto %."""
    out, izc = [], []
    for j, x in enumerate(ss[:2]):
        mins = int(x["sek"]) // 60
        if j == 0:
            out.append(f"{x['vards']} hasn't allowed a goal in {mins} minutes, and counting." if x["aktiva"]
                       else f"{x['vards']} went {mins} minutes without allowing a goal.")
        else:
            out.append(f"{x['vards']} is at {mins} minutes, still going." if x["aktiva"] else f"{x['vards']} went {mins} minutes.")
        izc.append((j, x["vards"]))
    if labakie:
        _, r_ = labakie[0]
        out.append(f"{r_['vards']} leads the week with a {r_['pct']:.3f} save percentage".replace(" 0.", " .")
                   + f", {int(r_['sv'])} saves in {int(r_['gs'])} starts.")
        izc.append((len(ss), r_["vards"]))
    return " ".join(out), izc


# ---------------------------------------------------------------- Streak watch: vārtu un piespēļu sērijas (kopš 11.11.2026)
GA_SOLO = ["Goal and assist streaks still alive.", "Now, the goal and assist streaks.",
           "Who keeps scoring, and who keeps setting them up?", "Goals on the left, assists on the right."]
GA_MIN = 3                       # sērija – no 3 spēlēm pēc kārtas
GA_RINDAS = 6                    # rindas katrā tabulā
SER_KUR_PILL = {"HOME": ("HOME", S.ZALS), "AWAY": ("ROAD", S.ZILS)}


def _ga_serijas(D, kol, min_n=GA_MIN):
    """Aktīvās sērijas pēc kolonnas (goals / assists): kopējā, mājās, izbraukumā (mājas / izbraukuma – tikai, ja garāka
    par kopējo); spēlētājs pēdējās 7 dienās ir spēlējis. → [{pid, vards, team, veids, n}] garākās pirmās."""
    out = []
    sp = D["sp"].sort_values(["datums", "game_id"])
    robeza = (S.pd.Timestamp(D["lidz"]) - S.timedelta(days=7)).strftime("%Y-%m-%d")
    for pid, g in sp.groupby("playerId"):
        if g["datums"].max() < robeza:
            continue

        def gar(x):
            n = 0
            for v in (S.pd.to_numeric(x[kol], errors="coerce").fillna(0).to_numpy() > 0)[::-1]:
                if not v:
                    break
                n += 1
            return n
        vards, kom = str(g["vards"].iloc[-1]), str(g["team"].iloc[-1])
        lab = {"pid": int(pid), "vards": vards, "team": kom, "veids": "ALL", "n": gar(g)}
        for v_, k_ in (("home", "HOME"), ("away", "AWAY")):           # katram spēlētājam – tikai garākā (kopā / mājās / izbr.)
            n_ = gar(g[g["home_away"] == v_])
            if n_ > lab["n"]:
                lab = dict(lab, veids=k_, n=n_)
        if lab["n"] >= min_n:
            out.append(lab)
    return sorted(out, key=lambda x: (-x["n"], x["veids"] != "ALL"))


def _ga_stasts(gs, asl):
    """Balss: vārtu sērijas līderis, piespēļu sērijas līderis, viena mājas / izbraukuma sērija (ja līderi nav tādi).
    → (teksts, [(kolonna, rindas nr, vārds)])."""
    kur = {"HOME": " home", "AWAY": " road", "ALL": ""}
    out, izc = [], []
    for kol_, rr, verbs in ((0, gs, "has scored in"), (1, asl, "has an assist in")):   # katras tabulas līderis
        if not rr:
            continue
        a = rr[0]
        out.append(f"{a['vards']} {verbs} {a['n']} straight{kur[a['veids']]} games.")
        izc.append((kol_, 0, a["vards"]))
    for kol_, rr, verbs in ((0, gs, "has scored in"), (1, asl, "has an assist in")):   # viena mājas / izbraukuma sērija
        j = next((i for i, x in enumerate(rr[:GA_RINDAS]) if x["veids"] != "ALL" and (kol_, i) not in [(k, i_) for k, i_, _ in izc]), None)
        if j is not None:
            x = rr[j]
            out.append(f"{x['vards']} {verbs} {x['n']} straight{kur[x['veids']]} games.")
            izc.append((kol_, j, x["vards"]))
            break
    return " ".join(out), izc


def ga_serijas_aina(D, tv, idx, gs=None, asl=None):
    """Ainas dati + balss: divas tabulas blakus – GOALS (kreisā) un ASSISTS (labā). gs / asl – jau atfiltrētie saraksti
    (bez tiem, kuru sērija ir tā pati, kas punktu tabulā)."""
    gs = (_ga_serijas(D, "goals") if gs is None else gs)[:GA_RINDAS]
    asl = (_ga_serijas(D, "assists") if asl is None else asl)[:GA_RINDAS]
    if not gs and not asl:
        return None
    st_, izc = _ga_stasts(gs, asl)
    runa = (S.reta_frase(GA_SOLO, veids="serijas", n=2) + " " + st_).strip()
    kol = [{"virs": "GOALS", "kr": S.DZELTENS, "rindas": gs}, {"virs": "ASSISTS", "kr": S.ZILS, "rindas": asl}]
    return ({"tips": "fakts_ga_serijas", "ilgums": 5.0, "virsr": [("GOAL", S.BALTS), ("+", S.BALTS), ("ASSIST", S.BALTS), ("STREAKS", S.DZELTENS)],
             "apaksa": "ACTIVE  ·  3+ GAMES IN A ROW  ·  HOME / ROAD MARKED", "kol": kol, "_tv": tv, "_tv_idx": idx, "izc": izc}, runa)


def _ser_pill(d, x, y, veids, izm=20, a=255):
    """HOME / ROAD zīmīte (mājas – zaļa, izbraukums – zila). → platums (0, ja kopējā sērija)."""
    if veids not in SER_KUR_PILL:
        return 0
    txt, kr = SER_KUR_PILL[veids]
    f = S.fonts("black", izm)
    w = d.textlength(txt, font=f) + izm * 1.1
    h = izm * 1.55
    d.rounded_rectangle([x, y - h / 2, x + w, y + h / 2], radius=h / 2, fill=tuple(kr) + (a,))
    d.text((x + w / 2, y + 1), txt, font=f, fill=S.MELNS + (a,), anchor="mm")
    return w


def aina_fakts_ga_serijas(t, c):
    """Divas tabulas blakus: vārtu un piespēļu sērijas (aktīvās; mājas / izbraukuma – ar zīmīti). Rindas atklājas
    ar skeneri; kad balss nosauc vārdu – rinda iemirdzas."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c)
    _fj_virsr(L, t, c["virsr"], 390, 112)
    a0 = S.ease(min(1.0, max(0.0, (t - 0.35) / 0.3)))
    S.teksts_c(d, 478, c["apaksa"], S.ietilpinat(d, c["apaksa"], "semi", 32, 900), _NV_LAB + (int(255 * a0),))
    if "_izc_t" not in c:
        vardi_, izc_t = c.get("_vardi") or [], {}
        for k_, i_, nm_ in c.get("izc") or []:
            tok = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in str(nm_).split()]
            tt_ = _nv_vards_laiks(vardi_, *tok) if tok and all(tok) else None
            if tt_ is None and tok and tok[-1]:
                tt_ = _nv_vards_laiks(vardi_, tok[-1])
            if tt_ is not None and (k_, i_) not in izc_t:
                izc_t[(k_, i_)] = tt_
        c["_izc_t"] = izc_t
    W, GX, X0 = 470, 20, 60
    nmax_ = max([len(k_["rindas"]) for k_ in c["kol"]] + [1])
    RH, GAP, Y0 = int(min(205, (1690 - 590) / max(4, nmax_) - 12)), 12, 590   # līdz subtitriem (drošā zona)
    sc = RH / 122
    nmax = max(len(k_["rindas"]) for k_ in c["kol"])
    Y_end = Y0 + max(1, nmax) * (RH + GAP)
    sk_p = min(1.0, max(0.0, (t - 0.6) / (0.2 * max(1, nmax) + 0.3)))
    y_sk = Y0 + (Y_end - Y0) * S.ease(sk_p)
    if 0 < sk_p < 1:
        _skeneris(N, X0, X0 + 2 * W + GX, y_sk)
    for ci, kol in enumerate(c["kol"]):
        x = X0 + ci * (W + GX)
        kr = tuple(kol["kr"])
        d.text((x + 8, Y0 - 34), kol["virs"], font=S.fonts("black", 36), fill=kr + (int(255 * a0),), anchor="lm")
        d.text((x + W - 8, Y0 - 34), "GAMES", font=S.fonts("semi", 22), fill=_NV_LAB + (int(255 * a0),), anchor="rm")
        if not kol["rindas"]:
            d.text((x + W / 2, Y0 + 60), "NONE ACTIVE", font=S.fonts("semi", 28), fill=_NV_LAB + (int(160 * a0),), anchor="mm")
        for i, r in enumerate(kol["rindas"]):
            y = Y0 + i * (RH + GAP)
            k = min(1.0, max(0.0, (y_sk - y) / RH)) if sk_p < 1 else 1.0
            if k <= 0:
                continue
            A = lambda v: int(v * k)
            d.rounded_rectangle([x, y, x + W, y + RH], radius=24, fill=(10, 14, 32, A(235)))
            pirmais = i == 0
            (dn if pirmais else d).rounded_rectangle([x, y, x + W, y + RH], radius=24, outline=(kr if pirmais else S.ZILS) + (A(220),),
                                                     width=4 if pirmais else 3)
            if (ci, i) in c["_izc_t"]:                               # balss nosauc – mirdzošs rāmis
                dtt = t - c["_izc_t"][(ci, i)] + 0.1
                g_ = min(1.0, max(0.0, dtt / 0.2)) * (1 - min(1.0, max(0.0, (dtt - 1.1) / 0.5)))
                if g_ > 0:
                    d.rounded_rectangle([x, y, x + W, y + RH], radius=24, fill=(255, 255, 255, int(28 * g_)))
                    dn.rounded_rectangle([x - 4, y - 4, x + W + 4, y + RH + 4], radius=26, outline=S.DZELTENS + (int(255 * g_),), width=7)
            _fj_ripa(d, x + 46, y + RH / 2, int(26 * min(sc, 1.25)), r.get("team"), A(255))
            vv = str(r["vards"]).split(" ", 1)
            xn_ = x + 86 + int(8 * (sc - 1))
            d.text((xn_, y + RH * 0.25), vv[0] if len(vv) > 1 else "", font=S.fonts("semi", int(22 * sc)), fill=_NV_LAB + (A(255),), anchor="lm")
            uz = (vv[-1]).upper()
            d.text((xn_, y + RH * 0.52), uz, font=S.ietilpinat(d, uz, "black", int(36 * sc), W - (xn_ - x) - int(104 * sc)), fill=S.BALTS + (A(255),), anchor="lm")
            _ser_pill(d, xn_, y + RH * 0.8, r.get("veids"), int(18 * sc), A(255))
            d.text((x + W - 22, y + RH * 0.46), str(r["n"]), font=S.fonts("black", int(66 * sc)), fill=(kr if pirmais else S.BALTS) + (A(255),), anchor="rm")
    L.alpha_composite(_nv_glow(N, 12, 1.3))
    return L


# ---------------------------------------------------------------- Streak watch: HOT & COLD (kopš 11.11.2026)
# Divas tabulas blakus – komandu uzvaru sērijas (HOT) un sērijas bez uzvaras (COLD), apakšā – zvaigznes garākā sērija
# bez vārtiem (SCORING DROUGHT). Mājas / izbraukuma sērijas – ar HOME / ROAD zīmīti (tikai, ja garākas par kopējo).
HC_SOLO = ["Hot and cold.", "Who's hot, and who's not?", "The hottest and coldest streaks right now."]   # ne tikai komandas –
HC_SAUSUMS = ["And the coldest star: {v} hasn't scored in {n} games.",                  # beigās arī spēlētājs
              "One star in a slump: {v} hasn't scored in {n} games.",
              "And a star in a slump: {v}, {n} games without a goal."]
HC_MIN = 3                       # komandu sērija – no 3 spēlēm
HC_RINDAS = 4
HC_SAUSUMS_MIN = 5               # sērija bez vārtiem – no 5 spēlēm
HC_ZVAIGZNE = 80                 # "zvaigzne" – ESPN rostered ≥ 80 % (ja ESPN nav – sezonas 60 rezultatīvākie uzbrucēji)


def _hc_serijas(D):
    """→ (karstās, aukstās): [{kom, veids, n, rek}] garākās pirmās; katrai komandai – garākā (kopā / mājās / izbr.)."""
    sg = D["sg"].sort_values(["datums", "game_id"])
    karst, auk = [], []
    for kom in sorted(set(sg["home_team"]) | set(sg["away_team"])):
        g = sg[(sg["home_team"] == kom) | (sg["away_team"] == kom)]

        def gar(x, uzv):
            n, rek = 0, [0, 0, 0]                                     # W, L, OTL
            for r in x[::-1].itertuples(index=False):
                w = r.uzvaretajs == kom
                if w != uzv:
                    break
                n += 1
                if w:
                    rek[0] += 1
                elif str(r.spele_beidzas) != "REG":
                    rek[2] += 1
                else:
                    rek[1] += 1
            return n, rek
        for uzv, sar in ((True, karst), (False, auk)):
            lab = None
            for veids, x in (("ALL", g), ("HOME", g[g["home_team"] == kom]), ("AWAY", g[g["away_team"] == kom])):
                n, rek = gar(x, uzv)
                if n >= HC_MIN and (lab is None or n > lab["n"]):
                    lab = {"kom": kom, "veids": veids, "n": n, "rek": rek}
            if lab:
                sar.append(lab)
    k_ = lambda x: (-x["n"], x["veids"] != "ALL")
    return sorted(karst, key=k_), sorted(auk, key=k_)


def _hc_sausums(D):
    """Zvaigznes (uzbrucēja) garākā aktīvā sērija bez vārtiem. → {pid, vards, team, n, pedejie} vai None."""
    sp = D["sp"].sort_values(["datums", "game_id"])
    robeza = (S.pd.Timestamp(D["lidz"]) - S.timedelta(days=7)).strftime("%Y-%m-%d")
    sp = sp[~sp["pozicija"].astype(str).str.upper().isin(["D", "G"])] if "pozicija" in sp else sp
    ros = D.get("espn")
    if ros is not None and len(ros):
        pool = {int(p) for p, v in ros.items() if S.pd.notna(v) and float(v) >= HC_ZVAIGZNE}
    else:
        gl = sp.assign(goals=S.pd.to_numeric(sp["goals"], errors="coerce").fillna(0)).groupby("playerId")["goals"].sum()
        pool = {int(p) for p in gl.sort_values(ascending=False).index[:60]}
    lab = None
    for pid, g in sp.groupby("playerId"):
        if S.pd.isna(pid) or int(pid) not in pool or g["datums"].max() < robeza:
            continue
        v = S.pd.to_numeric(g["goals"], errors="coerce").fillna(0).to_numpy()
        n = 0
        for x in v[::-1]:
            if x > 0:
                break
            n += 1
        if n >= HC_SAUSUMS_MIN and (lab is None or n > lab["n"]):
            ar_v = g[S.pd.to_numeric(g["goals"], errors="coerce").fillna(0) > 0]
            lab = {"pid": int(pid), "vards": str(g["vards"].iloc[-1]), "team": str(g["team"].iloc[-1]), "n": n,
                   "pedejie": str(ar_v["datums"].max()) if len(ar_v) else None}
    return lab


def _hc_stasts(karst, auk, sausums):
    kur = {"HOME": " at home", "AWAY": " on the road", "ALL": ""}
    out, izc = [], []
    if karst:
        a = karst[0]
        out.append(f"The {S.kom_nos(a['kom'])} have won {a['n']} straight{kur[a['veids']]}.")
        izc.append((0, 0, S.kom_nos(a["kom"])))
    if auk:
        a = auk[0]
        out.append(f"The {S.kom_nos(a['kom'])} haven't won in {a['n']} games{kur[a['veids']]}.")
        izc.append((1, 0, S.kom_nos(a["kom"])))
    if sausums:                                                       # pāreja no komandām uz spēlētāju
        out.append(S.reta_frase(HC_SAUSUMS, veids="serijas", n=1).format(v=sausums["vards"], n=sausums["n"]))
        izc.append(("s", 0, sausums["vards"]))
    return " ".join(out), izc


def hc_aina(D, tv, idx):
    """Ainas dati + balss: HOT (uzvaru sērijas) | COLD (bez uzvaras) + SCORING DROUGHT (ja ir)."""
    karst, auk = _hc_serijas(D)
    karst, auk = karst[:HC_RINDAS], auk[:HC_RINDAS]
    try:
        sausums = _hc_sausums(D)
    except Exception as ex_:                                          # noqa: BLE001
        print(f"  (sērija bez vārtiem: {type(ex_).__name__}: {ex_})")
        sausums = None
    if not karst and not auk:
        return None
    st_, izc = _hc_stasts(karst, auk, sausums)
    runa = (S.reta_frase(HC_SOLO, veids="serijas", n=2) + " " + st_).strip()
    kol = [{"virs": "HOT", "kr": S.ZALS, "rindas": karst}, {"virs": "COLD", "kr": S.SARKANS, "rindas": auk}]
    return ({"tips": "fakts_hc", "ilgums": 5.0, "virsr": [("HOT", S.ZALS), ("&", S.BALTS), ("COLD", (96, 165, 250))],
             "apaksa": "TEAM STREAKS  ·  WINS  ·  GAMES WITHOUT A WIN", "kol": kol, "sausums": sausums,
             "_tv": tv, "_tv_idx": idx, "izc": izc}, runa)


def aina_fakts_hc(t, c):
    """HOT & COLD: divas komandu tabulas blakus + apakšā zvaigznes sērija bez vārtiem. Kad balss nosauc – iemirdzas."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c)
    _fj_virsr(L, t, c["virsr"], 390, 112)
    a0 = S.ease(min(1.0, max(0.0, (t - 0.35) / 0.3)))
    S.teksts_c(d, 478, c["apaksa"], S.ietilpinat(d, c["apaksa"], "semi", 32, 900), _NV_LAB + (int(255 * a0),))
    if "_izc_t" not in c:
        vardi_, izc_t = c.get("_vardi") or [], {}
        for k_, i_, nm_ in c.get("izc") or []:
            tok = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in str(nm_).split()]
            tt_ = _nv_vards_laiks(vardi_, *tok) if tok and all(tok) else None
            if tt_ is None and tok and tok[-1]:
                tt_ = _nv_vards_laiks(vardi_, tok[-1])
            if tt_ is not None and (k_, i_) not in izc_t:
                izc_t[(k_, i_)] = tt_
        c["_izc_t"] = izc_t

    def mirdz(key, box, r_=24):
        if key not in c["_izc_t"]:
            return
        dtt = t - c["_izc_t"][key] + 0.1
        g_ = min(1.0, max(0.0, dtt / 0.2)) * (1 - min(1.0, max(0.0, (dtt - 1.1) / 0.5)))
        if g_ > 0:
            d.rounded_rectangle(box, radius=r_, fill=(255, 255, 255, int(28 * g_)))
            dn.rounded_rectangle([box[0] - 4, box[1] - 4, box[2] + 4, box[3] + 4], radius=r_ + 2, outline=S.DZELTENS + (int(255 * g_),), width=7)
    sausums = c.get("sausums")
    W, GX, X0, Y0, GAP = 470, 20, 60, 590, 12
    nmax = max([len(k_["rindas"]) for k_ in c["kol"]] + [1])
    lauks = (1690 - 260 - 30 if sausums else 1690) - Y0                # apakšā vieta SCORING DROUGHT kartītei
    RH = int(min(220, lauks / max(3, nmax) - GAP))
    sc = RH / 122
    Y_end = Y0 + max(1, nmax) * (RH + GAP)
    sk_p = min(1.0, max(0.0, (t - 0.6) / (0.22 * max(1, nmax) + 0.3)))
    y_sk = Y0 + (Y_end - Y0) * S.ease(sk_p)
    if 0 < sk_p < 1:
        _skeneris(N, X0, X0 + 2 * W + GX, y_sk)
    for ci, kol in enumerate(c["kol"]):
        x = X0 + ci * (W + GX)
        kr = tuple(kol["kr"])
        d.text((x + 8, Y0 - 34), kol["virs"], font=S.fonts("black", 38), fill=kr + (int(255 * a0),), anchor="lm")
        d.text((x + W - 8, Y0 - 34), "GAMES", font=S.fonts("semi", 22), fill=_NV_LAB + (int(255 * a0),), anchor="rm")
        if not kol["rindas"]:
            d.text((x + W / 2, Y0 + 60), "NONE RIGHT NOW", font=S.fonts("semi", 28), fill=_NV_LAB + (int(160 * a0),), anchor="mm")
        for i, r in enumerate(kol["rindas"]):
            y = Y0 + i * (RH + GAP)
            k = min(1.0, max(0.0, (y_sk - y) / RH)) if sk_p < 1 else 1.0
            if k <= 0:
                continue
            A = lambda v: int(v * k)
            d.rounded_rectangle([x, y, x + W, y + RH], radius=24, fill=(10, 14, 32, A(235)))
            pirm = i == 0
            (dn if pirm else d).rounded_rectangle([x, y, x + W, y + RH], radius=24, outline=(kr if pirm else S.ZILS) + (A(220),),
                                                  width=4 if pirm else 3)
            mirdz((ci, i), [x, y, x + W, y + RH])
            _fj_ripa(d, x + 46, y + RH / 2, int(26 * min(sc, 1.25)), r["kom"], A(255))
            pils, nos = S.KOMANDAS.get(str(r["kom"]), ("", str(r["kom"])))[:2]
            xn_ = x + 86 + int(8 * (sc - 1))
            d.text((xn_, y + RH * 0.25), str(pils), font=S.fonts("semi", int(22 * sc)), fill=_NV_LAB + (A(255),), anchor="lm")
            nm = str(nos).upper()
            d.text((xn_, y + RH * 0.52), nm, font=S.ietilpinat(d, nm, "black", int(34 * sc), W - (xn_ - x) - int(100 * sc)), fill=S.BALTS + (A(255),), anchor="lm")
            pw_ = _ser_pill(d, xn_, y + RH * 0.8, r.get("veids"), int(18 * sc), A(255))
            W_, L_, O_ = r["rek"]
            rek = f"{W_}-0" if ci == 0 else f"0-{L_}-{O_}"
            d.text((xn_ + (pw_ + 10 if pw_ else 0), y + RH * 0.8), rek, font=S.fonts("semi", int(20 * sc)), fill=_NV_LAB + (A(255),), anchor="lm")
            d.text((x + W - 22, y + RH * 0.46), str(r["n"]), font=S.fonts("black", int(66 * sc)), fill=(kr if pirm else S.BALTS) + (A(255),), anchor="rm")
    if sausums:                                                       # SCORING DROUGHT – visā platumā tieši zem tabulām
        yk = Y_end + 18
        ka = S.ease(min(1.0, max(0.0, (t - 0.6 - 0.22 * max(1, nmax) - 0.2) / 0.4)))
        if ka > 0:
            A = lambda v: int(v * ka)
            box = [X0, yk, X0 + 2 * W + GX, yk + 260]
            d.rounded_rectangle(box, radius=30, fill=(10, 14, 32, A(240)))
            dn.rounded_rectangle(box, radius=30, outline=(96, 165, 250) + (A(230),), width=5)
            mirdz(("s", 0), box, 30)
            d.text((X0 + 34, yk + 40), "SCORING DROUGHT", font=S.fonts("black", 34), fill=(96, 165, 250) + (A(255),), anchor="lm")
            _fj_ripa(d, X0 + 80, yk + 150, 44, sausums["team"], A(255))
            vv = str(sausums["vards"]).split(" ", 1)
            d.text((X0 + 150, yk + 112), vv[0] if len(vv) > 1 else "", font=S.fonts("semi", 30), fill=_NV_LAB + (A(255),), anchor="lm")
            uz = vv[-1].upper()
            d.text((X0 + 150, yk + 158), uz, font=S.ietilpinat(d, uz, "black", 60, 470), fill=S.BALTS + (A(255),), anchor="lm")
            ped = f"LAST GOAL: {S.dat(sausums['pedejie']).upper()}" if sausums.get("pedejie") else "NO GOAL THIS SEASON"
            d.text((X0 + 150, yk + 212), ped, font=S.fonts("semi", 26), fill=_NV_LAB + (A(255),), anchor="lm")
            xr = X0 + 2 * W + GX - 34
            d.text((xr, yk + 128), str(sausums["n"]), font=S.fonts("black", 110), fill=(96, 165, 250) + (A(255),), anchor="rm")
            d.text((xr, yk + 212), "GAMES WITHOUT A GOAL", font=S.fonts("semi", 24), fill=_NV_LAB + (A(255),), anchor="rm")
    L.alpha_composite(_nv_glow(N, 12, 1.3))
    return L


def fakti_serijas_ainas(D, m, izv, tv, idx, solo=False):
    """Divas kopsavilkuma ainas pirms verdikta (ja ir dati): punktu sērijas 10+ un nedēļas sausās sērijas.
    → [(kartīte, balss teksts)]. Video jau atsevišķi pieminētās sērijas rāda, bet balsī nesauc vārdā."""
    out = []
    try:
        mans = {str(c.get("atsl", "")) for c in izv}
        ps_, redz_ = [], set()                                        # katram spēlētājam – tikai garākā sērija (kopā / mājās / izbr.)
        for x_ in S.punktu_serijas_kopsavilkums(D, min_n=3):
            if x_["pid"] not in redz_:
                redz_.add(x_["pid"])
                ps_.append(x_)
        ps = ps_[:8]                                                  # garākās aktīvās (ekrāns pilns); 10+ – dzeltenas
        gs_all, as_all, skip_g, skip_a = [], [], set(), set()
        if solo:                                                      # Streak watch: ja punktu sērija = vārtu (piespēļu) sērija
            try:                                                      # (tas pats veids un garums) – tā ir VIENA sērija: paliek
                gs_all, as_all = _ga_serijas(D, "goals"), _ga_serijas(D, "assists")   # punktu tabulā ar piezīmi "goal in
            except Exception as ex_:                                  # every game", vārtu tabulā to vairs nerāda
                print(f"  (vārtu / piespēļu sērijas: {type(ex_).__name__}: {ex_})")
            gmap, amap = {x["pid"]: x for x in gs_all}, {x["pid"]: x for x in as_all}
            for x in ps:
                g_, a_ = gmap.get(x["pid"]), amap.get(x["pid"])
                if g_ and g_["veids"] == x["veids"] and g_["n"] >= x["n"]:
                    x["visi"] = "G"
                    skip_g.add(x["pid"])
                elif a_ and a_["veids"] == x["veids"] and a_["n"] >= x["n"]:
                    x["visi"] = "A"
                    skip_a.add(x["pid"])
        if ps:
            piez = {"G": ("goal in every game", S.DZELTENS), "A": ("assist in every game", S.ZILS)}
            rindas = [{"vards": x["vards"], "team": x["team"], "liels": str(x["n"]), "maz": "STRAIGHT GAMES", "kur": x["veids"],
                       "apaksa": piez[x["visi"]][0] if x.get("visi") else "point streak",   # mājas / izbr. – zīmīte zem vārda
                       "apaksa_kr": piez[x["visi"]][1] if x.get("visi") else None,
                       "video": x["veids"] == "ALL" and f"points_serija:{x['pid']}" in mans,
                       "izcelt": x["n"] >= S.PUNKTU_SERIJA_MIN} for x in ps]
            desmit = [x for x in ps if x["n"] >= S.PUNKTU_SERIJA_MIN]
            runa = (S.reta_frase(PS_SOLO if desmit else PS_SOLO_NAV, veids="serijas", n=2) if solo else
                    S.reta_frase(PS_RUNA_10 if desmit else PS_RUNA_NAV, veids="fakts", n=3))   # vispārīgi – vārdi redzami sarakstā
            izc = []
            if solo:                                                  # Streak watch – balss izstāsta redzamo (kopš 11.11.2026)
                st_, izc = _ps_stasts(ps)
                runa = (runa + " " + st_).strip()
            out.append(({"tips": "fakts_serijas", "ilgums": 4.8, "virsr": [("POINT", S.BALTS), ("STREAKS", S.DZELTENS)],
                         "apaksa": "LONGEST ACTIVE  ·  ALL / HOME / ROAD  ·  10+ IN YELLOW", "rindas": rindas, "_tv": tv, "_tv_idx": idx,
                         "izc": izc}, runa))
        if solo:                                                      # Streak watch: vārtu + piespēļu sērijas (kopš 11.11.2026)
            try:
                ga_ = ga_serijas_aina(D, tv, idx, [x for x in gs_all if x["pid"] not in skip_g],
                                      [x for x in as_all if x["pid"] not in skip_a])
                if ga_:
                    out.append(ga_)
            except Exception as ex_:                                  # noqa: BLE001
                print(f"  (vārtu / piespēļu sērijas: {type(ex_).__name__}: {ex_} – izlaists)")
        # GOALIES OF THE WEEK (kopš 09.11.2026): augšā sausās sērijas ≥ 120 min (dzeltenas), tālāk – nedēļas labākie pēc
        # atvairīto % (≥ 2 starti), lai ekrāns vienmēr pilns; aina ir vienmēr (arī, ja sēriju nav)
        ss = S.sausas_serijas_nedela(D, m)[:3]
        rindas = [{"vards": x["vards"], "team": x["team"], "liels": f"{x['sek'] // 60}:{x['sek'] % 60:02d}",
                   "maz": "STILL GOING" if x["aktiva"] else "ENDED", "maz_kr": S.ZALS if x["aktiva"] else _NV_LAB,
                   "apaksa": f"shutout streak · {x['atvairiti']} saves", "izcelt": True} for x in ss]
        no_ = (S.pd.Timestamp(D["lidz"]) - S.timedelta(days=6)).strftime("%Y-%m-%d")
        vg = D["vg"][(D["vg"]["datums"] >= no_) & (D["vg"]["starter"].astype(str) == "True")].copy()
        for c_ in ("saves", "shotsAgainst", "goalsAgainst"):
            vg[c_] = S.pd.to_numeric(vg[c_], errors="coerce").fillna(0)
        gw = vg.groupby("playerId").agg(vards=("vards", "last"), team=("team", "last"), gs=("game_id", "nunique"),
                                        sv=("saves", "sum"), sa=("shotsAgainst", "sum"), ga=("goalsAgainst", "sum"))
        gw = gw[(gw["gs"] >= 2) & (gw["sa"] > 0)]
        gw["pct"] = gw["sv"] / gw["sa"]
        gw = gw.sort_values(["pct", "sv"], ascending=False)
        jau = {x["pid"] for x in ss}
        labakie = [(int(p_), r_) for p_, r_ in gw.iterrows() if int(p_) not in jau][:max(0, 8 - len(rindas))]
        for p_, r_ in labakie:
            rindas.append({"vards": r_["vards"], "team": r_["team"], "liels": f"{r_['pct']:.3f}".lstrip("0"),
                           "maz": "SAVE %", "apaksa": f"{int(r_['gs'])} starts · {int(r_['sv'])} saves, {int(r_['ga'])} goals allowed",
                           "izcelt": False})
        if rindas:
            runa = S.reta_frase(SS_RUNA if ss else SS_RUNA_NAV, veids="serijas" if solo else "fakts", n=3)   # vārdi – sarakstā
            izc = []
            if solo:                                                  # Streak watch – īss ievads + kas redzams ekrānā
                st_, izc = _ss_stasts(ss, labakie)
                runa = (S.reta_frase(SS_SOLO if ss else SS_SOLO_NAV, veids="serijas", n=2) + " " + st_).strip()
            out.append(({"tips": "fakts_serijas", "ilgums": 4.8, "virsr": [("GOALIES", S.BALTS), ("OF THE WEEK", S.DZELTENS)],
                         "apaksa": "SHUTOUT STREAKS 120+ MIN IN YELLOW  ·  SAVE %  ·  2+ STARTS", "rindas": rindas,
                         "_tv": tv, "_tv_idx": idx, "izc": izc}, runa))
        if solo:                                                      # Streak watch: HOT & COLD – pēdējā aina (kopš 11.11.2026)
            try:
                hc_ = hc_aina(D, tv, idx)
                if hc_:
                    out.append(hc_)
            except Exception as ex_:                                  # noqa: BLE001
                print(f"  (HOT & COLD: {type(ex_).__name__}: {ex_} – izlaists)")
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (sēriju kopsavilkums: {type(ex).__name__}: {ex} – izlaists)")
    return out


def aina_fakts_nak_j(t, c):
    """NEXT UP – nākamā spēle aktīvai sērijai (bez aicinājuma komentēt)."""
    F = S.fonts
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); dn = ImageDraw.Draw(N)
    _nv_dalinas(L, t)
    _fj_tablo(L, N, t, c)
    _fj_virsr(L, t, [("NEXT", S.BALTS), ("UP", S.DZELTENS)], 400, 130)
    nk = list(c.get("nakamais") or ["", "", ""])
    kp = S.ease(min(1.0, max(0.0, (t - 0.35) / 0.4)))
    if kp > 0:
        yb = 560 + (1060 - 560) * kp
        d.rounded_rectangle([90, 560, 990, yb], radius=36, fill=(10, 14, 32, 235))
        dn.rounded_rectangle([90, 560, 990, yb], radius=36, outline=S.DZELTENS + (220,), width=4)
        if kp < 1:
            _skeneris(N, 90, 990, yb)
    if kp >= 1:
        k = min(1.0, (t - 0.75) / 0.3)
        if k > 0:
            if c.get("badge"):
                _fj_ripa(d, 240, 800, int(100 * ease_back(k)), c["badge"])      # ≤ 350 px – atstarpe līdz tekstam (400)
            d.text((400, 740), str(nk[0]).upper(), font=S.ietilpinat(d, str(nk[0]).upper(), "black", 76, 560), fill=S.BALTS + (int(255 * k),), anchor="lm")
            d.text((400, 840), str(nk[1]).upper(), font=S.ietilpinat(d, str(nk[1]).upper(), "black", 56, 560), fill=_NV_LAB + (int(255 * k),), anchor="lm")
            if c.get("serija"):
                d.text((400, 920), c["serija"], font=S.ietilpinat(d, c["serija"], "semi", 34, 560), fill=S.DZELTENS + (int(255 * k),), anchor="lm")
    kq = (t - 1.3) / 0.35
    if kq > 0 and len(nk) > 2 and nk[2]:                              # jautājums – parasts teksts (bez spīduma / pulsēšanas)
        jt = str(nk[2]).upper()
        S.teksts_c(d, 1150, jt, S.ietilpinat(d, jt, "black", 64, 900), S.BALTS + (int(255 * min(1.0, kq)),))
    L.alpha_composite(_nv_glow(N, 12, 1.3))
    return L


# ---------------------------------------------------------------- dati (ripa / histogramma) pēc fakta veida
def _fj_spelu_lab(D, gid, kom):
    i = (D.get("info") or {}).get((gid, kom), {})
    o = i.get("o", "")
    return o


def fakts_ripa_dati(D, m, c):
    """→ {"punkti": [{x, y, k, lab}], "virsr", "apaksa", "skaititajs", ...} vai None (tad vecā saraksta aina)."""
    np, pd = S.np, S.pd
    veids, _, rest = str(c.get("atsl", "")).partition(":")
    dal = rest.split(":")
    sp, sg, va = D["sp"], D["sg"], D["va"]

    def koord(rows, k, lab_fn):
        out = []
        for r in rows.itertuples(index=False):
            x, y = float(r.x) if r.x == r.x else None, float(r.y) if r.y == r.y else None
            if x is None or y is None:
                continue
            sgn = -1 if x < 0 else 1
            out.append({"x": min(99.0, max(26.0, x * sgn)), "y": max(-41.0, min(41.0, y * sgn)), "k": k, "lab": lab_fn(r), "_s": (r.datums, r.sek)})
        return out

    def dat_lab(r):
        return f"{S.dat(r.datums).upper()}  ·  vs {r.pretinieks}"

    def per_lab(r):
        p_ = int(r.period)
        mm_, ss_ = divmod(int(r.sek) - (p_ - 1) * 1200, 60)
        return f"{'OT' if p_ > 3 else 'P' + str(p_)}  ·  {mm_}:{ss_:02d}"

    def piespeles(pids, gids, lab_fn):
        """Piespēles: va (vārtu tabula) → tie paši vārti metienu tabulā (spēle, komanda, laiks ±3 s)."""
        out = []
        v = va[va["game_id"].isin(gids)].copy()
        v = v[(pd.to_numeric(v["assist1_id"], errors="coerce").isin(pids)) | (pd.to_numeric(v["assist2_id"], errors="coerce").isin(pids))]
        v = v[~pd.to_numeric(v["scorer_id"], errors="coerce").isin(pids)]
        g_ = m[(m["game_id"].isin(gids)) & (m["varti"] == 1)]
        for r in v.itertuples(index=False):
            s_ = (int(r.period) - 1) * 1200 + S._sek(r.laiks)
            x = g_[(g_["game_id"] == r.game_id) & (g_["komanda"] == r.komanda) & ((g_["sek"] - s_).abs() <= 3)]
            if len(x):
                out += koord(x.head(1), "A", lab_fn)
        return out

    if veids in ("goals_serija", "points_serija"):
        pid = float(dal[0])
        x = sp[(sp["playerId"] == pid) & (sp["datums"] <= str(c.get("datums")))].sort_values("datums").tail(int(c.get("garums", 0)))
        gids = list(x["game_id"])
        p = koord(m[(m["game_id"].isin(gids)) & (m["metejs"] == pid) & (m["varti"] == 1)], "G", dat_lab)
        if veids == "points_serija":
            p += piespeles([pid], gids, dat_lab)
        G_, A_ = int(pd.to_numeric(x["goals"], errors="coerce").fillna(0).sum()), int(pd.to_numeric(x["assists"], errors="coerce").fillna(0).sum())
        kopa = G_ + A_ if veids == "points_serija" else G_
        sk_ = (f"POINTS  ·  {len(gids)} GAMES" if veids == "points_serija" else f"GOALS  ·  {len(gids)} GAMES")
        rez = {"kopa": kopa, "virsr": [("EVERY", S.BALTS), ("GOAL", S.BALTS), ("OF THE", S.BALTS), ("STREAK", S.DZELTENS)],
               "apaksa": f"{str(c.get('v1') or '')} {c.get('vards')}".strip().upper() + "  ·  WHERE THEY CAME FROM",
               "skaititajs": sk_, "skaititajs2": (_fj_ga(G_, A_) if veids == "points_serija" else ""),
               "legenda": ([("GOAL", "G"), ("ASSIST", "A")] if veids == "points_serija" else None)}
    elif veids in ("liela", "liela_duo"):
        pids = [float(x_) for x_ in dal[0].split("-")]
        gid = int(dal[1])
        p = koord(m[(m["game_id"] == gid) & (m["metejs"].isin(pids)) & (m["varti"] == 1)], "G", per_lab)
        p += piespeles(pids, [gid], per_lab)
        x_ = sp[(sp["playerId"].isin(pids)) & (sp["game_id"] == gid)]
        G_, A_ = int(pd.to_numeric(x_["goals"], errors="coerce").fillna(0).sum()), int(pd.to_numeric(x_["assists"], errors="coerce").fillna(0).sum())
        rez = {"kopa": G_ + A_, "virsr": [("EVERY", S.BALTS), ("POINT", S.BALTS), ("OF THE", S.BALTS), ("NIGHT", S.DZELTENS)],
               "apaksa": "GOALS AND ASSISTS  ·  WHERE THEY CAME FROM",
               "skaititajs": "POINTS", "skaititajs2": _fj_ga(G_, A_),
               "legenda": [("GOAL", "G"), ("ASSIST", "A")] if A_ else None}
    elif veids == "vartsargs":
        pid, gid = float(dal[0]), int(dal[1])
        x = m[(m["game_id"] == gid) & (m["vartsargs"] == pid) & (m["uz_v"] == 1)]
        p = koord(x[x["varti"] == 0], "S", per_lab) + koord(x[x["varti"] == 1], "GA", per_lab)
        rez = {"kopa": int(c.get("garums", 0)) or None, "virsr": [("EVERY", S.BALTS), ("SAVE", S.DZELTENS)], "apaksa": "SHOTS ON GOAL HE FACED",
               "skaititajs": "SAVES", "kr_sk": "S", "skaita": ("S",)}
    elif veids in ("periods", "comeback", "atri"):
        gid = int(dal[0])
        kom = dal[1] if veids == "periods" else c.get("badge")
        x = m[(m["game_id"] == gid) & (m["komanda"] == kom) & (m["varti"] == 1)]
        if veids == "periods":
            x = x[x["period"] == int(dal[2])]
        if veids == "atri":
            x = x.sort_values("sek")
            dd = x["sek"].diff()
            if dd.notna().any():
                j = int(np.nanargmin(dd.to_numpy()))
                x = x.iloc[max(0, j - 1):j + 1]
        p = koord(x, "G", per_lab)
        rez = {"kopa": (int(c.get("garums", 0)) if veids == "periods" else (2 if veids == "atri" else None)),
               "virsr": [("EVERY", S.BALTS), ("GOAL", S.DZELTENS)], "apaksa": f"{S.kom_nos(kom).upper()}  ·  WHERE THEY CAME FROM",
               "skaititajs": "GOALS"}
    elif veids == "metieni":
        gid, kom = int(dal[0]), c.get("badge")
        x = m[(m["game_id"] == gid) & (m["pretinieks"] == kom) & (m["uz_v"] == 1)]
        p = koord(x[x["varti"] == 0], "S", per_lab) + koord(x[x["varti"] == 1], "GA", per_lab)
        rez = {"virsr": [("EVERY", S.BALTS), ("SHOT", S.BALTS), ("THEY", S.BALTS), ("SURVIVED", S.DZELTENS)],
               "apaksa": "SHOTS ON GOAL AGAINST THEM", "skaititajs": "SHOTS FACED", "kr_sk": "S"}
    elif veids in ("kom_uzv", "kom_zaud"):
        kom = dal[0]
        g = sg[((sg["home_team"] == kom) | (sg["away_team"] == kom)) & (sg["datums"] <= str(c.get("datums")))].sort_values("datums")
        gids = list(g["game_id"].tail(int(c.get("garums", 0))))
        if veids == "kom_uzv":
            p = koord(m[(m["game_id"].isin(gids)) & (m["komanda"] == kom) & (m["varti"] == 1)], "G", dat_lab)
            gg = g[g["game_id"].isin(gids)]
            rez = {"kopa": int(sum(r_.home_total if r_.home_team == kom else r_.away_total for r_ in gg.itertuples(index=False))), "virsr": [("EVERY", S.BALTS), ("GOAL", S.BALTS), ("OF THE", S.BALTS), ("STREAK", S.DZELTENS)],
                   "apaksa": f"{S.kom_nos(kom).upper()}  ·  GOALS IN THE WINS", "skaititajs": f"GOALS  ·  {len(gids)} WINS"}
        else:
            x = m[(m["game_id"].isin(gids)) & (m["pretinieks"] == kom) & (m["varti"] == 1)]
            p = koord(x, "GA", lambda r: f"{S.dat(r.datums).upper()}  ·  by {r.komanda}")
            gg = g[g["game_id"].isin(gids)]
            rez = {"kopa": int(sum(r_.away_total if r_.home_team == kom else r_.home_total for r_ in gg.itertuples(index=False))), "virsr": [("EVERY", S.BALTS), ("GOAL", S.BALTS), ("AGAINST", S.SARKANS)],
                   "apaksa": f"{S.kom_nos(kom).upper()}  ·  {len(gids)} GAMES WITHOUT A WIN", "skaititajs": f"GOALS AGAINST  ·  {len(gids)} GAMES",
                   "kr_sk": "GA"}
    else:
        return None
    if not p:
        return None
    p.sort(key=lambda q: q.pop("_s"))
    rez["punkti"] = p[:60]
    kopa = rez.get("kopa")
    if kopa and kopa > len(rez["punkti"]):                            # tukši vārti / bez metiena vietas – nav uz ripas
        d_ = kopa - len(rez["punkti"])
        rez["piezime"] = f"{d_} not shown (empty net / no shot location)"
    return rez


def _fj_ga(G_, A_):
    return f"{G_} goal{'' if G_ == 1 else 's'}  ·  {A_} assist{'' if A_ == 1 else 's'}"


def _fj_serijas(vert):
    """Sēriju garumi no bool virknes."""
    out, r = [], 0
    for v in vert:
        if v:
            r += 1
        else:
            if r:
                out.append(r)
            r = 0
    if r:
        out.append(r)
    return out


def _fj_bins_garumi(garumi, L):
    """Sēriju garumi → stabiņi (≤ 8): 1, 2, 3 … ; vidējie apvienoti, varoņa garums atsevišķi, garāki – "L+1+"."""
    import collections
    cnt = collections.Counter(garumi)
    mx = max(cnt) if cnt else L
    vals = list(range(1, max(mx, L) + 1))
    if len(vals) <= 8:
        bins = [(str(v), cnt.get(v, 0)) for v in vals]
        return bins, L - 1
    bins = [(str(v), cnt.get(v, 0)) for v in range(1, 5)]
    if L - 1 >= 5:
        bins.append((f"5–{L - 1}" if L - 1 > 5 else "5", sum(cnt.get(v, 0) for v in range(5, L))))
    hero = len(bins)
    bins.append((str(L), cnt.get(L, 0)))
    gar = sum(c_ for v, c_ in cnt.items() if v > L)
    if gar:
        bins.append((f"{L + 1}+", gar))
    return bins, hero


def _fj_proc(k, n):
    p = k / max(1, n) * 100
    return f"{p:.1f}%" if p < 1 else f"{p:.0f}%"


def fakts_hist_dati(D, c):
    """→ {"bins", "hero", "x_lab", "apaksa", "z1", "z2", "hero_lab", "runa"} vai None (tad vecā konteksta aina)."""
    np, pd = S.np, S.pd
    veids, _, rest = str(c.get("atsl", "")).partition(":")
    dal = rest.split(":")
    sp, sg = D["sp"], D["sg"]
    vards_ = str(c.get("vards") or "").upper()
    if veids in ("goals_serija", "points_serija"):
        kol = "goals" if veids == "goals_serija" else "points"
        L = int(c.get("garums", 0))
        gar = []
        for _, g in sp.sort_values("datums").groupby("playerId"):
            gar += _fj_serijas((pd.to_numeric(g[kol], errors="coerce").fillna(0) > 0).tolist())
        bins, hero = _fj_bins_garumi(gar, L)
        k, n = sum(1 for v in gar if v >= L), len(gar)
        vv = "goal" if kol == "goals" else "point"
        rez = {"bins": bins, "hero": hero, "x_lab": f"GAMES IN A ROW WITH A {vv.upper()}",
               "apaksa": f"ALL {n} {vv.upper()} RUNS THIS SEASON (1+ GAMES)", "hero_lab": vards_,
               "z1": f"ONLY {k} OF {n}" if k / max(1, n) <= 0.3 else f"{k} OF {n}", "z2": f"REACHED {L} GAMES  ·  TOP {_fj_proc(k, n)}",
               "runa": f"Only {k} of {n} {vv} runs this season {'has' if k == 1 else 'have'} reached {L} games." if k / max(1, n) <= 0.3 else ""}
    elif veids in ("kom_uzv", "kom_zaud"):
        L = int(c.get("garums", 0))
        s_ = sg[sg["home_total"].notna()].sort_values("datums")
        gar = []
        for kom in sorted(set(s_["home_team"]) | set(s_["away_team"])):
            g = s_[(s_["home_team"] == kom) | (s_["away_team"] == kom)]
            uzv = (g["uzvaretajs"] == kom).tolist()
            gar += _fj_serijas(uzv if veids == "kom_uzv" else [not u for u in uzv])
        bins, hero = _fj_bins_garumi(gar, L)
        k, n = sum(1 for v in gar if v >= L), len(gar)
        ko = "WINS IN A ROW" if veids == "kom_uzv" else "GAMES IN A ROW WITHOUT A WIN"
        rez = {"bins": bins, "hero": hero, "x_lab": ko, "apaksa": f"ALL {n} TEAM RUNS THIS SEASON (1+ GAMES)",
               "hero_lab": str(c.get("badge") or ""), "z1": f"ONLY {k} OF {n}" if k / max(1, n) <= 0.3 else f"{k} OF {n}",
               "z2": f"REACHED {L} GAMES  ·  TOP {_fj_proc(k, n)}",
               "runa": (f"Only {k} of {n} team runs this season {'has' if k == 1 else 'have'} reached {L} games." if k / max(1, n) <= 0.3 else "")}
    elif veids == "liela":
        pid, gid = float(dal[0]), int(dal[1])
        x = sp[(sp["playerId"] == pid) & (sp["game_id"] == gid)]
        if x.empty:
            return None
        G, P = int(x["goals"].iloc[0]), int(x["points"].iloc[0])
        kol, v_ = ("goals", G) if G >= 3 else ("points", P)
        vals = pd.to_numeric(sp[kol], errors="coerce").fillna(0).astype(int)
        top = max(v_ + 1, 5)
        bins = [(str(i) if i < top else f"{top}+", int((vals == i).sum()) if i < top else int((vals >= top).sum())) for i in range(0, top + 1)]
        hero = v_ if v_ < top else top
        k, n = int((vals >= v_).sum()), len(vals)
        vv = "goals" if kol == "goals" else "points"
        rez = {"bins": bins, "hero": hero, "x_lab": f"{vv.upper()} IN ONE GAME", "apaksa": f"ALL {n:,} PLAYER GAMES THIS SEASON".replace(",", " "),
               "hero_lab": vards_, "z1": f"ONLY {k} OF {n:,}".replace(",", " "), "z2": f"PLAYER GAMES WITH {v_}+ {vv.upper()}  ·  TOP {_fj_proc(k, n)}",
               "runa": f"Only {k} of {n:,} player games this season had {v_} or more {vv}.".replace(",", "")}
    elif veids == "vartsargs" and not (str(c.get("skaitlis_apaksa", "")).lower() == "shutout"
                                       or "SHUTOUT" in " ".join(str(x) for x in (c.get("hook") or [])).upper()):
        # 45+ atvairīti BEZ sausās spēles (līdz 04.11. te kļūdaini rādīja sauso spēļu histogrammu)
        sv_ = int(c.get("garums", 0))
        vg = pd.concat([D.get("h_vg"), D["vg"]], ignore_index=True)
        svs = pd.to_numeric(vg["saves"], errors="coerce")
        so = svs[(vg["starter"].astype(str) == "True") & svs.notna()].astype(int)
        if len(so) < 20:
            return None
        edges = [0, 25, 30, 35, 40, 45, 50, 999]
        labs = ["<25", "25–29", "30–34", "35–39", "40–44", "45–49", "50+"]
        bins = [(labs[i], int(((so >= edges[i]) & (so < edges[i + 1])).sum())) for i in range(len(labs))]
        hero = next(i for i in range(len(labs)) if edges[i] <= sv_ < edges[i + 1])
        k, n = int((so >= sv_).sum()), len(so)
        rez = {"bins": bins, "hero": hero, "x_lab": "SAVES IN ONE GAME", "apaksa": f"ALL {n:,} STARTS SINCE 2023".replace(",", " "),
               "hero_lab": vards_, "z1": f"ONLY {k} OF {n:,}".replace(",", " "), "z2": f"STARTS WITH {sv_}+ SAVES  ·  TOP {_fj_proc(k, n)}",
               "runa": f"Since 2023, only {k} of {n} starts had {sv_} or more saves."}
    elif veids == "comeback":                                         # cik vārtus uzvarētājs bija iedzīts – visas sezonas uzvaras
        d_ = int(c.get("garums", 0))
        vg_ = D["va"].groupby("game_id")
        vals = []
        for r in sg[sg["uzvaretajs"].notna()].itertuples(index=False):
            if r.game_id not in vg_.groups:
                continue
            m_ = 0
            for _, _, _, h_, a_ in S._gaita(vg_.get_group(r.game_id)):
                m_ = max(m_, (a_ - h_) if r.uzvaretajs == r.home_team else (h_ - a_))
            vals.append(m_)
        if len(vals) < 20 or d_ < 1:
            return None
        top = max(4, d_)
        bins = [(str(i), sum(1 for v in vals if v == i)) for i in range(top)] + [(f"{top}+", sum(1 for v in vals if v >= top))]
        k, n = sum(1 for v in vals if v >= d_), len(vals)
        rez = {"bins": bins, "hero": min(d_, top), "x_lab": "GOALS DOWN – AND STILL WON", "apaksa": f"ALL {n:,} WINS THIS SEASON".replace(",", " "),
               "hero_lab": str(c.get("badge") or ""), "z1": f"ONLY {k} OF {n:,}".replace(",", " "),
               "z2": f"WINS FROM {d_}+ GOALS DOWN  ·  TOP {_fj_proc(k, n)}",
               "runa": f"Only {k} of {n:,} wins this season came from {d_} or more goals down.".replace(",", "")}
    elif veids == "atri":                                             # ātrākie 2 vienas komandas vārti katrā spēlē
        sek = abs(int(c.get("garums", 0)))
        x = D["va"].copy()
        if x.empty or sek <= 0:
            return None
        x["s"] = x["laiks"].map(S._sek) + (x["period"] - 1) * 1200
        x = x.sort_values(["game_id", "s"])
        x["d"] = x.groupby(["game_id", "komanda"])["s"].diff()
        vals = [int(v) for v in x.dropna(subset=["d"]).groupby("game_id")["d"].min().tolist()]
        if len(vals) < 20:
            return None
        edges = [0, 11, 21, 31, 61, 121, 10 ** 6]
        labs = ["≤10", "11–20", "21–30", "31–60", "61–120", "120+"]
        bins = [(labs[i], sum(1 for v in vals if edges[i] <= v < edges[i + 1])) for i in range(len(labs))]
        hero = next(i for i in range(len(labs)) if edges[i] <= sek < edges[i + 1])
        k, n = sum(1 for v in vals if v <= sek), len(vals)
        rez = {"bins": bins, "hero": hero, "x_lab": "FASTEST 2 GOALS BY ONE TEAM IN A GAME (SECONDS)",
               "apaksa": f"ALL {n:,} GAMES WITH 2+ GOALS BY ONE TEAM".replace(",", " "), "hero_lab": str(c.get("badge") or ""),
               "z1": f"ONLY {k} OF {n:,}".replace(",", " "), "z2": f"GAMES WITH 2 GOALS IN {sek} SEC OR LESS  ·  TOP {_fj_proc(k, n)}",
               "runa": f"Only {k} of {n:,} games this season had two goals by one team that fast.".replace(",", "")}
    elif veids == "metieni":                                          # par cik metieniem uzvarētājs bija pārspēts
        starp = int(c.get("garums", 0))
        vals = []
        for r in sg[sg["uzvaretajs"].notna()].itertuples(index=False):
            try:
                hm, am = int(r.home_sog_total), int(r.away_sog_total)
            except (TypeError, ValueError):
                continue
            vals.append((am - hm) if r.uzvaretajs == r.home_team else (hm - am))
        if len(vals) < 20 or starp < 1:
            return None
        edges = [-999, 1, 10, 15, 20, 25, 999]
        labs = ["≤0", "1–9", "10–14", "15–19", "20–24", "25+"]
        bins = [(labs[i], sum(1 for v in vals if edges[i] <= v < edges[i + 1])) for i in range(len(labs))]
        hero = next(i for i in range(len(labs)) if edges[i] <= starp < edges[i + 1])
        k, n = sum(1 for v in vals if v >= starp), len(vals)
        rez = {"bins": bins, "hero": hero, "x_lab": "SHOTS THE WINNER WAS OUTSHOT BY", "apaksa": f"ALL {n:,} WINS THIS SEASON".replace(",", " "),
               "hero_lab": str(c.get("badge") or ""), "z1": f"ONLY {k} OF {n:,}".replace(",", " "),
               "z2": f"WINS WHILE OUTSHOT BY {starp}+  ·  TOP {_fj_proc(k, n)}", "runa": ""}   # balss jau saka "99 percent"
    elif veids == "vartsargs":
        sv_ = int(c.get("garums", 0))
        vg = pd.concat([D.get("h_vg"), D["vg"]], ignore_index=True)
        ga = pd.to_numeric(vg["goalsAgainst"], errors="coerce")
        svs = pd.to_numeric(vg["saves"], errors="coerce")
        so = svs[(ga == 0) & (svs >= 10) & (vg["starter"].astype(str) == "True")].astype(int)
        if len(so) < 5:
            return None
        edges = [0, 20, 25, 30, 35, 40, 999]
        labs = ["<20", "20–24", "25–29", "30–34", "35–39", "40+"]
        bins = [(labs[i], int(((so >= edges[i]) & (so < edges[i + 1])).sum())) for i in range(len(labs))]
        hero = next(i for i in range(len(labs)) if edges[i] <= sv_ < edges[i + 1])
        k, n = int((so >= sv_).sum()), len(so)
        rez = {"bins": bins, "hero": hero, "x_lab": "SAVES IN A SHUTOUT", "apaksa": f"ALL {n} SHUTOUTS SINCE 2023",
               "hero_lab": vards_, "z1": f"ONLY {k} OF {n}" if k / n <= 0.3 else f"{k} OF {n}",
               "z2": f"SHUTOUTS WITH {sv_}+ SAVES", "runa": (f"Since 2023, only {k} of {n} shutouts had {sv_} or more saves." if k / n <= 0.3 else "")}
    elif veids == "periods":
        g_ = int(c.get("garums", 0))
        vals = pd.concat([pd.to_numeric(sg[f"{h}_p{p}"], errors="coerce") for h in ("home", "away") for p in (1, 2, 3)]).dropna().astype(int)
        top = max(g_, 5)
        bins = [(str(i) if i < top else f"{top}+", int((vals == i).sum()) if i < top else int((vals >= top).sum())) for i in range(0, top + 1)]
        k, n = int((vals >= g_).sum()), len(vals)
        rez = {"bins": bins, "hero": min(g_, top), "x_lab": "GOALS BY ONE TEAM IN ONE PERIOD", "apaksa": f"ALL {n:,} TEAM PERIODS THIS SEASON".replace(",", " "),
               "hero_lab": str(c.get("badge") or ""), "z1": f"ONLY {k} OF {n:,}".replace(",", " "), "z2": f"PERIODS WITH {g_}+ GOALS  ·  TOP {_fj_proc(k, n)}",
               "runa": f"Only {k} of {n:,} team periods this season had {g_} or more goals.".replace(",", "")}
    else:
        return None
    if not rez["bins"] or rez["hero"] >= len(rez["bins"]):
        return None
    return rez


def fakti_jauns(rez, D, m, izv, st, mini_runa):
    """Faktu scenārijs → jaunais izskats. Jebkura kļūda → vecais izskats (video netiek salauzts)."""
    if not JAUNS_FANTASY or not rez:
        return rez
    try:
        n = len(izv)
        hero = izv[0]
        tv = {"lab": "NHL · THE WEEK", "liels": "IN NUMBERS", "kr": [S.ZILS] * (n - 1) + [S.DZELTENS],
              "labaja": f"STATS THRU {S.dat(rez['lidz']).upper()}"}
        rows = [{"nr": i + 1, "vards": c.get("vards"), "vards_pilns": f"{c.get('v1') or ''} {c.get('vards') or ''}".strip(),
                 "badge": c.get("badge"), "hook": c.get("hook"), "kr": S.DZELTENS if i == 0 else S.ZILS} for i, c in enumerate(izv)]
        st_nr = {c_.get("nr"): c_.get("stat_rindas") for c_ in rez["kartes"] if c_.get("tips") == "fakts_mini"}
        sv_nr = {c_.get("nr"): c_.get("stat_virs") for c_ in rez["kartes"] if c_.get("tips") == "fakts_mini"}
        for i, c in enumerate(izv[1:], 2):                            # #N → #2: paplašinātā informācija, kamēr runā balss
            sr = st_nr.get(i) or []
            if sr == [r_ for r_ in (c.get("rindas") or []) if r_[0]][:3]:   # nav sezonas datu (tās pašas rindas) – neatkārto
                sr = []
            rows[i - 1]["plus"] = {"virs": c.get("saraksts_virs"), "rindas": c.get("rindas"), "stats": sr[:3],
                                   "stats_virs": sv_nr.get(i) or "SEASON SO FAR",
                                   "kont": (c.get("konteksts") or [""])[0], "runa_pre": f"Number {i}. {c['runa'][0]}",
                                   "izcelt": c.get("izcelt_rindas"), "izcelt_txt": c.get("izcelt_txt")}
        virsr = [(f"TOP {n}", S.BALTS), ("THIS WEEK", S.DZELTENS)] if n > 1 else [("STAT OF", S.BALTS), ("THE WEEK", S.DZELTENS)]
        kartes, runa = [], [rez["runa"][0]]
        docked = []
        for pos, nr in enumerate(range(n, 1, -1)):
            kartes.append({"tips": "fakts_tablo", "ilgums": 6.0, "fakti": rows, "nr": nr, "docked": list(docked), "virsr": virsr,
                           "pirmais": pos == 0, "_tv": tv, "_tv_idx": pos, "_bez_ieejas": pos > 0, "_bez_izejas": True, "_bez_tuv": True})
            runa.append(mini_runa[pos])
            docked.append(nr)
        kartes.append({"tips": "fakts_tablo", "ilgums": 4.4, "fakti": rows, "nr": 1, "docked": list(docked), "virsr": virsr,
                       "pirmais": n == 1, "bez_tablo": n == 1, "_tv": tv, "_tv_idx": n - 1, "_bez_ieejas": n > 1, "_bez_tuv": True})
        runa.append(("Number one. " if n > 1 else "") + hero["runa"][0])
        ripa = fakts_ripa_dati(D, m, hero)
        if ripa:
            if st:
                ripa["stats"] = [(r_[0].replace("Games played", "GP").replace("Shots on goal", "SOG"), r_[2]) for r_ in st[1][:4]]
                ripa["stats_virs"] = st[0]
            kartes.append({"tips": "fakts_ripa", "ilgums": max(6.0, 1.25 + 0.1 * len(ripa["punkti"]) + FJ_RIPA_PAUZE),
                           "ripa": ripa, "_tv": tv, "_tv_idx": n - 1})
            sk1, sk2 = set(re.findall(r"\d+", hero["runa"][1])), set(re.findall(r"\d+", st[3])) if st else set()
            papild = (" " + st[3]) if st and not sk2 <= sk1 else ""          # sezona = sērija → neatkārto tos pašus skaitļus
            runa.append((hero["runa"][1] + papild).strip())
        else:
            kartes.append({"tips": "fakts_saraksts", "ilgums": 2.6 + 0.22 * min(9, len(hero["rindas"])), **hero})
            runa.append(hero["runa"][1])
            if st:
                kartes.append({"tips": "fakts_saraksts", "ilgums": 3.6, **hero, "saraksts_virs": st[0], "rindas": st[1],
                               "kopsavilkums": st[2], "pill_kr": S.ZILS, "vards_w": 420 if st[0] != "BOX SCORE" else 330, "vards_kr": S.BALTS})
                runa.append(st[3])
        hist = fakts_hist_dati(D, hero)
        if hist:
            kartes.append({"tips": "fakts_hist", "ilgums": 5.0, "hist": hist, "_tv": tv, "_tv_idx": n - 1})
            # "That's the 14th hat trick…" jau saka skaitu → "Only 14 of …" nepiebilst (citādi skan pretrunīgi / atkārtojas)
            kart_ = re.search(r"\d+(st|nd|rd|th)\b", hero["runa"][2])
            runa.append((hero["runa"][2] + ("" if kart_ else " " + hist.get("runa", ""))).strip())
        else:                                                         # bez histogrammas – tā pati aina jaunajā izskatā
            kartes.append({"tips": "fakts_reti", "ilgums": 4.4, **hero, "_tv": tv, "_tv_idx": n - 1})
            runa.append(hero["runa"][2])
        if hero.get("nakamais") and len(hero["runa"]) > 3 and hero["runa"][3]:
            th = hero.get("th_hook") or []
            kartes.append({"tips": "fakts_nak_j", "ilgums": 3.6, "nakamais": hero["nakamais"], "badge": hero.get("badge"),
                           "serija": " ".join(th).upper() if th else "", "_tv": tv, "_tv_idx": n - 1})
            runa.append(hero["runa"][3])
        # (līdz 11.11.2026 te bija POINT STREAKS / GOALIES OF THE WEEK – tagad tās ir tikai Streak watch video)
        runa.append(rez["runa"][-1])
        # āķis – jaunajā stilā
        ap = []
        if str(hero.get("atsl", "")).startswith(("goals_serija", "points_serija")):
            for r_ in hero.get("rindas") or []:
                nums = [int(x) for x in re.findall(r"(\d+)\s*[GA]", str(r_[2]))]
                ap.append(sum(nums))
            ap = ap[-6:]
        uzl = str(rez["intro"].get("uzlime") or "").upper()
        h = list(hero.get("hook") or [""])
        aki = {"liels": h[0], "apli": [f"+{v}" for v in ap], "izcelt": [int(S.np.argmax(ap))] if ap else [],
               "zem": " ".join(h[1:]), "josla": ("..." + uzl) if uzl else "", "vards": str(hero.get("vards") or "").upper(),
               "kom": hero.get("badge"), "tag": "NHL  ·  THE WEEK IN NUMBERS", "kart_txt": "#1"}
        rez["intro"] = {"aki": True, "fantasy_aki": aki, "tag": aki["tag"], "ilgums": 2.6, "_tv": tv}
        rez["kartes"], rez["runa"] = kartes, runa
        rez["_bez_zimoga"] = True
        _ns_fakti(rez, hero)                                          # noslēpuma āķis (ja ieslēgts) – arī TOP N
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (faktu jaunais izskats: {type(ex).__name__}: {ex} – vecais)")
    return rez


# ================================================================ NOSLĒPUMA ĀĶIS (kopš 04.11.2026)
# Āķis bez skaitļiem un sīka teksta: melns krekla siluets (mala – komandas krāsā) ar spīdošu "?" prožektora gaismā,
# jautājums 1 ("WHO IS THIS?") → glitch (uz mirkli uzzibsnī īstais krekls – vārds izpludināts, numura vietā "?")
# → jautājums 2 ("WHY IS HE STILL FREE?"), sirdspuksti, kamera ielido "?" iekšā → nākamā aina. Balss nolasa abus
# jautājumus; subtitru āķī nav (jautājums jau ir uz ekrāna). Frāzes neatkārtojas pēdējos video (frazes_vesture.json).
# Vecais āķis (ar skaitli):  python ShortsB.py ... --bez-noslepuma
NOSL_AKIS = True
NOSL_VIRSRAKSTS = True           # YouTube virsrakstā vārda vietā "guess who's …" / "guess which team …" (vārds – aprakstā)
_NS_SFX = {"ev": None}

NOSL_Q1 = {
    "speletajs": [(("WHO IS", "THIS?"), "Who is this?"), (("GUESS", "WHO?"), "Guess who."),
                  (("KNOW", "THIS GUY?"), "Do you know this guy?"), (("CAN YOU", "NAME HIM?"), "Can you name him?"),
                  (("RECOGNIZE", "THIS JERSEY?"), "Recognize this jersey?"), (("ANY", "GUESSES?"), "Any guesses?")],
    "vartsargs": [(("WHO IS", "THIS?"), "Who is this?"), (("GUESS THE", "GOALIE"), "Guess the goalie."),
                  (("KNOW THIS", "GOALIE?"), "Do you know this goalie?"), (("NAME", "THIS GOALIE"), "Name this goalie."),
                  (("RECOGNIZE", "THIS JERSEY?"), "Recognize this jersey?"), (("ANY", "GUESSES?"), "Any guesses?")],
    "komanda": [(("WHICH TEAM", "IS THIS?"), "Which team is this?"), (("GUESS THE", "TEAM"), "Guess the team."),
                (("NAME THIS", "TEAM"), "Can you name this team?"), (("RECOGNIZE", "THESE COLORS?"), "Recognize these colors?"),
                (("WHO", "WEARS THIS?"), "Who wears this?"), (("ANY", "GUESSES?"), "Any guesses?")],
    "duo": [(("WHO ARE", "THESE TWO?"), "Who are these two?"), (("GUESS", "THE DUO"), "Guess the duo."),
            (("KNOW", "THESE TWO?"), "Do you know these two?"), (("NAME", "THE PAIR"), "Name the pair."),
            (("RECOGNIZE", "THESE TWO?"), "Recognize these two?"), (("ANY", "GUESSES?"), "Any guesses?")],
    "atskats_f": [(("OUR PICKS", "LAST WEEK"), "Our picks from last week."), (("REMEMBER", "THESE GUYS?"), "Remember these guys?"),
                  (("LAST WEEK", "WE SAID…"), "Last week, we said…"), (("REMEMBER", "OUR PICKS?"), "Remember our picks?"),
                  (("LAST WEEK'S", "CALLS"), "Last week's calls."), (("THE PICKS", "WE MADE"), "The picks we made.")],
    "atskats_xg": [(("WE FLAGGED", "THESE {X}"), "We flagged these {x}."), (("REMEMBER", "THESE {X}?"), "Remember these {x}?"),
                   (("xG FLAGGED", "THESE {X}"), "The numbers flagged these {x}."), (("REMEMBER", "OUR LIST?"), "Remember our list?"),
                   (("THE {X}", "WE FLAGGED"), "The {x} we flagged."), (("BACK TO", "OUR LIST"), "Back to our list.")],
}
NOSL_ATKL = {     # kad noslēpuma spēlētāja / komandas kartīte parādās – balss sākumā (atklāšana)
    "speletajs": ["Mystery solved.", "Remember the jersey?", "Did you guess right?", "Time for the reveal.", "Here's our mystery man."],
    "vartsargs": ["Mystery solved.", "Remember the jersey?", "Did you guess right?", "Time for the reveal.", "Here's our mystery goalie."],
    "komanda": ["Mystery solved.", "Remember the jersey?", "Did you guess the team?", "Time for the reveal."],
    "duo": ["Mystery solved.", "Did you guess them?", "Time for the reveal.", "Remember the jerseys?"],
}
NOSL_Q2 = {
    "fantasy": [(("WHY IS HE", "STILL", "FREE?"), "Why is he still free?"),
                (("NOBODY", "WANTS", "HIM?"), "Nobody wants him?"),
                (("WHY IS NOBODY", "ADDING", "HIM?"), "Why is nobody adding him?"),
                (("HOW IS HE", "STILL ON", "WAIVERS?"), "How is he still on waivers?"),
                (("THE STEAL", "OF THE", "WEEK?"), "The steal of the week?"),
                (("DID YOUR", "LEAGUE", "FORGET HIM?"), "Did your league forget him?")],
    "streameri": [(("YOUR", "NEXT", "STREAMER?"), "Your next streamer?"),
                  (("STREAM HIM", "THIS", "WEEK?"), "Stream him this week?"),
                  (("FREE POINTS", "THIS", "WEEK?"), "Free points this week?"),
                  (("WHY IS NOBODY", "STREAMING", "HIM?"), "Why is nobody streaming him?"),
                  (("THE STREAMER", "NOBODY", "TALKS ABOUT"), "The streamer nobody talks about.")],
    "sp_laim": [(("HOT STREAK", "OR JUST", "LUCK?"), "Hot streak, or just luck?"),
                (("IS IT", "JUST", "LUCK?"), "Is it just luck?"),
                (("TOO HOT", "TO", "LAST?"), "Too hot to last?"),
                (("REAL", "OR", "LUCKY?"), "Real, or lucky?"),
                (("TIME TO", "SELL", "HIGH?"), "Time to sell high?")],
    "sp_nelaim": [(("WHERE ARE", "THE", "GOALS?"), "Where are the goals?"),
                  (("DUE FOR A", "BIG", "BREAKOUT?"), "Due for a big breakout?"),
                  (("BAD LUCK", "OR", "BAD PLAYER?"), "Bad luck, or bad player?"),
                  (("TIME TO", "BUY", "LOW?"), "Time to buy low?"),
                  (("ABOUT TO", "FINALLY", "SCORE?"), "Is he about to finally score?")],
    "va_labs": [(("IS HE", "STEALING", "GAMES?"), "Is he stealing games?"),
                (("IS THIS", "FOR", "REAL?"), "Is this for real?"),
                (("A BRICK WALL", "OR JUST", "LUCK?"), "A brick wall, or just luck?"),
                (("CAN HE", "KEEP THIS", "UP?"), "Can he keep this up?"),
                (("THE BEST", "GOALIE", "RIGHT NOW?"), "The best goalie right now?")],
    "va_slikts": [(("IS HE", "COSTING", "GAMES?"), "Is he costing his team games?"),
                  (("WHAT IS", "GOING", "WRONG?"), "What is going wrong?"),
                  (("BAD LUCK", "OR", "BAD GOALIE?"), "Bad luck, or bad goalie?"),
                  (("TIME FOR", "A", "CHANGE?"), "Time for a change?"),
                  (("CAN HE", "TURN IT", "AROUND?"), "Can he turn it around?")],
    "kom_laim": [(("WINNING", "OR JUST", "LUCKY?"), "Winning, or just lucky?"),
                 (("GOOD", "OR", "LUCKY?"), "Good, or lucky?"),
                 (("CAN THIS", "REALLY", "LAST?"), "Can this really last?"),
                 (("RIDING", "THE", "LUCK?"), "Riding the luck?"),
                 (("ABOUT", "TO", "CRASH?"), "About to crash?")],
    "kom_nelaim": [(("BETTER", "THAN THEIR", "RECORD?"), "Better than their record?"),
                   (("THE UNLUCKIEST", "TEAM", "RIGHT NOW?"), "The unluckiest team right now?"),
                   (("ABOUT TO", "TURN IT", "AROUND?"), "About to turn it around?"),
                   (("BAD TEAM", "OR", "BAD LUCK?"), "Bad team, or bad luck?"),
                   (("DON'T", "WRITE THEM", "OFF"), "Don't write them off.")],
    "fakti_sp": [(("CAN ANYONE", "STOP", "HIM?"), "Can anyone stop him?"),
                 (("HOW IS THIS", "EVEN", "POSSIBLE?"), "How is this even possible?"),
                 (("THE STAT", "OF THE", "WEEK?"), "The stat of the week?"),
                 (("NOBODY SAW", "THIS", "COMING"), "Nobody saw this coming."),
                 (("THE HOTTEST", "PLAYER", "RIGHT NOW?"), "The hottest player right now?")],
    "fakti_va": [(("CAN ANYONE", "BEAT", "HIM?"), "Can anyone beat him?"),
                 (("HOW IS THIS", "EVEN", "POSSIBLE?"), "How is this even possible?"),
                 (("THE WALL", "OF THE", "WEEK?"), "The wall of the week?"),
                 (("NOBODY SAW", "THIS", "COMING"), "Nobody saw this coming."),
                 (("THE HOTTEST", "GOALIE", "RIGHT NOW?"), "The hottest goalie right now?")],
    "fakti_duo": [(("CAN ANYONE", "STOP", "THEM?"), "Can anyone stop them?"),
                  (("THE BEST DUO", "IN THE", "NHL?"), "The best duo in the NHL?"),
                  (("HOW IS THIS", "EVEN", "POSSIBLE?"), "How is this even possible?"),
                  (("THE STAT", "OF THE", "WEEK?"), "The stat of the week?"),
                  (("NOBODY SAW", "THIS", "COMING"), "Nobody saw this coming.")],
    "fakti_kom": [(("CAN ANYONE", "STOP", "THEM?"), "Can anyone stop them?"),
                  (("HOW IS THIS", "EVEN", "POSSIBLE?"), "How is this even possible?"),
                  (("THE TEAM", "OF THE", "WEEK?"), "The team of the week?"),
                  (("NOBODY SAW", "THIS", "COMING"), "Nobody saw this coming."),
                  (("THE HOTTEST", "TEAM", "RIGHT NOW?"), "The hottest team right now?")],
    "fakti_kom_zaud": [(("WHEN WILL", "THEY", "WIN?"), "When will they win again?"),
                       (("WHAT IS", "GOING", "WRONG?"), "What is going wrong?"),
                       (("IS THIS", "ROCK", "BOTTOM?"), "Is this rock bottom?"),
                       (("CAN THEY", "TURN IT", "AROUND?"), "Can they turn it around?"),
                       (("HOW DID IT", "GET THIS", "BAD?"), "How did it get this bad?")],
    "atskats_f": [(("DID THEY", "DELIVER?"), "Did they deliver?"),
                  (("WERE WE", "RIGHT?"), "Were we right?"),
                  (("HIT", "OR", "MISS?"), "Hit, or miss?"),
                  (("DID WE", "NAIL IT?"), "Did we nail it?"),
                  (("TIME TO", "CHECK THE", "RECEIPTS"), "Time to check the receipts."),
                  (("DID THEY", "PAY", "OFF?"), "Did they pay off?"),
                  (("GOOD ADDS", "OR", "BAD ADDS?"), "Good adds, or bad adds?"),
                  (("WORTH", "THE", "PICKUP?"), "Were they worth the pickup?"),
                  (("DID WE", "HELP YOUR", "TEAM?"), "Did we help your team?")],
    "atskats_xg": [(("WAS xG", "RIGHT?"), "Were the numbers right?"),
                   (("CALLED IT", "OR", "BLEW IT?"), "Called it, or blew it?"),
                   (("HIT", "OR", "MISS?"), "Hit, or miss?"),
                   (("WERE WE", "RIGHT?"), "Were we right?"),
                   (("LET'S CHECK", "THE", "RECEIPTS"), "Let's check the receipts."),
                   (("DID THE", "NUMBERS", "HOLD?"), "Did the numbers hold?"),
                   (("LUCK", "OR", "SKILL?"), "Luck, or skill?"),
                   (("DID xG", "SEE IT", "COMING?"), "Did the numbers see it coming?"),
                   (("RIGHT", "OR", "WRONG?"), "Right, or wrong?")],
}


# ---------------------------------------------------------------- reālistisks krekls (mugurpuse, bez logo)
_KR_WH, _KR_BK = (245, 247, 250), (10, 12, 18)
KREKLI = {    # mājas krekli: ķermenis, svītras [(krāsa, platums)…], apkakle, numurs + kontūras, vārds (+ kontūra)
    "BUF": dict(body=(0, 48, 135), stripes=[(_KR_WH, 12), ((252, 181, 20), 50), (_KR_WH, 12)], collar=(252, 181, 20),
                num=_KR_WH, o1=(252, 181, 20), o2=None, name=_KR_WH, name_o=None),
    "EDM": dict(body=(4, 30, 66), stripes=[((252, 76, 0), 16), (_KR_WH, 10), ((252, 76, 0), 46)], collar=(252, 76, 0),
                num=(252, 76, 0), o1=_KR_WH, o2=None, name=(252, 76, 0), name_o=_KR_WH),
    "DAL": dict(body=(0, 104, 71), stripes=[(_KR_BK, 10), (_KR_WH, 48), (_KR_BK, 10)], collar=_KR_WH,
                num=_KR_WH, o1=_KR_BK, o2=(162, 170, 173), name=_KR_WH, name_o=_KR_BK),
    "TBL": dict(body=(0, 40, 104), stripes=[(_KR_WH, 50)], collar=_KR_WH, num=_KR_WH, o1=None, o2=None, name=_KR_WH, name_o=None),
    "BOS": dict(body=(17, 17, 17), stripes=[((252, 181, 20), 14), (_KR_WH, 8), ((252, 181, 20), 40)], collar=(252, 181, 20),
                num=(252, 181, 20), o1=_KR_WH, o2=None, name=(252, 181, 20), name_o=None),
    "TOR": dict(body=(0, 32, 91), stripes=[(_KR_WH, 46)], collar=_KR_WH, num=_KR_WH, o1=None, o2=None, name=_KR_WH, name_o=None),
    "DET": dict(body=(206, 17, 38), stripes=[(_KR_WH, 54)], collar=_KR_WH, num=_KR_WH, o1=None, o2=None, name=_KR_WH, name_o=None),
    "CHI": dict(body=(207, 10, 44), stripes=[(_KR_WH, 10), (_KR_BK, 40), (_KR_WH, 10)], collar=_KR_WH,
                num=_KR_WH, o1=_KR_BK, o2=None, name=_KR_WH, name_o=_KR_BK),
    "NYR": dict(body=(0, 56, 168), stripes=[((206, 17, 38), 14), (_KR_WH, 10), ((206, 17, 38), 14)], collar=_KR_WH,
                num=(206, 17, 38), o1=_KR_WH, o2=None, name=_KR_WH, name_o=None),
    "NYI": dict(body=(0, 83, 155), stripes=[(_KR_WH, 10), ((244, 125, 48), 40), (_KR_WH, 10)], collar=(244, 125, 48),
                num=(244, 125, 48), o1=_KR_WH, o2=None, name=_KR_WH, name_o=None),
    "NSH": dict(body=(255, 184, 28), stripes=[((4, 30, 66), 16), (_KR_WH, 8), ((4, 30, 66), 16)], collar=(4, 30, 66),
                num=(4, 30, 66), o1=_KR_WH, o2=None, name=(4, 30, 66), name_o=None),
    "PIT": dict(body=(17, 17, 17), stripes=[((252, 181, 20), 14), (_KR_WH, 10), ((252, 181, 20), 14)], collar=(252, 181, 20),
                num=_KR_WH, o1=(252, 181, 20), o2=None, name=_KR_WH, name_o=None),
    "MTL": dict(body=(175, 30, 45), stripes=[(_KR_WH, 10), ((25, 33, 104), 40), (_KR_WH, 10)], collar=(25, 33, 104),
                num=_KR_WH, o1=(25, 33, 104), o2=None, name=_KR_WH, name_o=None),
    "PHI": dict(body=(247, 73, 2), stripes=[(_KR_WH, 10), (_KR_BK, 36), (_KR_WH, 10)], collar=_KR_BK,
                num=_KR_WH, o1=_KR_BK, o2=None, name=_KR_WH, name_o=_KR_BK),
    "COL": dict(body=(111, 38, 61), stripes=[(_KR_WH, 10), ((35, 97, 146), 40), (_KR_WH, 10)], collar=(35, 97, 146),
                num=_KR_WH, o1=(35, 97, 146), o2=None, name=_KR_WH, name_o=None),
    "VAN": dict(body=(0, 32, 91), stripes=[(_KR_WH, 10), ((0, 132, 61), 40), (_KR_WH, 10)], collar=(0, 132, 61),
                num=_KR_WH, o1=(0, 132, 61), o2=None, name=_KR_WH, name_o=None),
}


def _kr_dizains(kom):
    if kom in KREKLI:
        return KREKLI[kom]
    b = tuple(S.kkrasa(kom) or (40, 60, 120))
    s_ = tuple(SEKUNDARAS.get(str(kom), _KR_WH))
    tumss_s = sum(s_) < 300
    return dict(body=b, stripes=[(_KR_WH, 12), (s_, 48), (_KR_WH, 12)], collar=s_, num=_KR_WH if tumss_s else s_,
                o1=s_ if tumss_s else _KR_WH, o2=None, name=_KR_WH, name_o=None)


def _kr_blur(a, s):
    """~Gausa izpludināšana (3 kastes filtri ar cumsum) – tikai numpy."""
    np = S.np
    if s <= 0:
        return a
    r = max(1, int(round(s * 0.87)))
    out = a.astype(np.float32)
    for ax in (0, 1):
        for _ in range(3):
            p = np.pad(out, [(r + 1, r) if i == ax else (0, 0) for i in range(2)], mode="edge")
            c = np.cumsum(p, axis=ax, dtype=np.float64)
            out = (((c[2 * r + 1:] - c[:-2 * r - 1]) if ax == 0 else (c[:, 2 * r + 1:] - c[:, :-2 * r - 1])) / (2 * r + 1)).astype(np.float32)
    return out


def _kr_chaikin(pts, n=2):
    for _ in range(n):
        q = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        pts = q
    return pts


def _kr_maska(pts, Wd, Hd, sc):
    m = Image.new("L", (Wd, Hd), 0)
    ImageDraw.Draw(m).polygon([(x * sc, y * sc) for x, y in pts], fill=255)
    return S.np.asarray(m, S.np.float32) / 255


_KR_KREISA = [(500, 92), (455, 88), (420, 76), (400, 62), (350, 74), (290, 92), (235, 118), (190, 170), (140, 260), (95, 370),
              (58, 480), (30, 590), (14, 660), (60, 688), (115, 710), (160, 722), (175, 650), (195, 560), (215, 470), (232, 400),
              (242, 350), (238, 450), (232, 600), (228, 760), (224, 900), (220, 1005), (260, 1012), (380, 1018), (500, 1020)]
_KR_PIED = [(270, 98), (235, 118), (190, 170), (140, 260), (95, 370), (58, 480), (30, 590), (14, 660), (60, 688), (115, 710),
            (160, 722), (175, 650), (195, 560), (215, 470), (232, 400), (242, 350), (252, 270), (262, 180)]
_KR_ASS = ((250, 150), (88, 700))                                      # piedurknes ass: plecs → aproce


def _kr_mir(pts):
    return [(1000 - x, y) for x, y in pts]


def _kr_kroka(H_, X, Y, p0, p1, w, amp, sc):
    np = S.np
    x0, y0, x1, y1 = p0[0] * sc, p0[1] * sc, p1[0] * sc, p1[1] * sc
    m_ = 4 * w * sc
    xa, xb = int(max(0, min(x0, x1) - m_)), int(min(H_.shape[1], max(x0, x1) + m_))
    ya, yb = int(max(0, min(y0, y1) - m_)), int(min(H_.shape[0], max(y0, y1) + m_))
    if xb <= xa or yb <= ya:
        return
    Xs, Ys = X[ya:yb, xa:xb], Y[ya:yb, xa:xb]
    dx, dy = x1 - x0, y1 - y0
    t = np.clip(((Xs - x0) * dx + (Ys - y0) * dy) / (dx * dx + dy * dy), 0, 1)
    d2 = (Xs - x0 - t * dx) ** 2 + (Ys - y0 - t * dy) ** 2
    H_[ya:yb, xa:xb] += amp * np.exp(-d2 / (2 * (w * sc) ** 2)) * np.clip(np.sin(np.pi * t), 0, 1) ** 0.6


def _kr_burti(txt, h_px, squeeze=0.8, track=0.04):
    """Bloka burti (krekla numurs / vārds): Inter Black, saspiesti, ar atstarpēm → L attēls."""
    f0 = S.fonts("black", max(8, int(h_px * 1.38)))
    bb = f0.getbbox("H")
    f = S.fonts("black", max(8, int(h_px * 1.38 * h_px / max(1, bb[3] - bb[1]))))
    ws = [f.getlength(ch) for ch in txt]
    tr = track * h_px
    im = Image.new("L", (int(sum(ws) + tr * (len(txt) - 1) + 40), int(h_px * 1.8)), 0)
    d = ImageDraw.Draw(im)
    x = 20
    for ch, w in zip(txt, ws):
        d.text((x, h_px * 1.35), ch, font=f, fill=255, anchor="ls")
        x += w + tr
    im = im.crop(im.getbbox())
    return im.resize((max(1, int(im.width * squeeze)), im.height), Image.LANCZOS)


def _kr_uzlikt(arr, im, cx, cy, rot=0.0):
    np = S.np
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    a = np.asarray(im, np.float32) / 255
    h, w = a.shape
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs0, ys0, xs1, ys1 = max(0, x0), max(0, y0), min(arr.shape[1], x0 + w), min(arr.shape[0], y0 + h)
    if xs1 > xs0 and ys1 > ys0:
        arr[ys0:ys1, xs0:xs1] = np.maximum(arr[ys0:ys1, xs0:xs1], a[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0])


def _kr_paplest(m, px):
    im = Image.fromarray((S.np.clip(m, 0, 1) * 255).astype(S.np.uint8))
    k = int(px) * 2 + 1
    while k > 1:
        kk = min(k, 31) | 1
        im = im.filter(ImageFilter.MaxFilter(kk))
        k -= kk - 1
    return S.np.asarray(im.filter(ImageFilter.GaussianBlur(0.8)), S.np.float32) / 255


def krekls_reals(kom, vards, numurs, izm=820, vards_izpl=0.0):
    """Reālistisks hokeja krekls no mugurpuses → RGBA (izm × 1,08·izm): forma ar krokām, auduma tekstūra, gaisma
    (normāļu karte), uzšūts vārds un numurs ar kontūrām, svītras, numuri uz piedurknēm. Bez komandu logo."""
    np = S.np
    K = _kr_dizains(kom)
    ss = 2
    sc = izm * ss / 1000
    Wd, Hd = int(1000 * sc), int(1080 * sc)
    Y, X = np.mgrid[0:Hd, 0:Wd].astype(np.float32)
    M = _kr_maska(_kr_chaikin(_KR_KREISA + _kr_mir(_KR_KREISA[1:-1])[::-1]), Wd, Hd, sc)
    SL = np.maximum(_kr_maska(_kr_chaikin(_KR_PIED), Wd, Hd, sc), _kr_maska(_kr_chaikin(_kr_mir(_KR_PIED)), Wd, Hd, sc)) * M
    A = np.zeros((Hd, Wd, 3), np.float32)
    A[:] = np.array(K["body"], np.float32)

    def krasot(m, kr):
        A[:] = A * (1 - m[..., None]) + np.array(kr, np.float32) * m[..., None]

    (ax_a, ax_b) = _KR_ASS
    for side in (0, 1):
        a_ = ax_a if side == 0 else (1000 - ax_a[0], ax_a[1])
        b_ = ax_b if side == 0 else (1000 - ax_b[0], ax_b[1])
        dx, dy = b_[0] - a_[0], b_[1] - a_[1]
        Ln = math.hypot(dx, dy)
        s_ = (X / sc - a_[0]) * dx / Ln + (Y / sc - a_[1]) * dy / Ln
        smask = SL * ((X < Wd / 2) if side == 0 else (X >= Wd / 2))
        pos = Ln * 0.60
        for kr, w in K["stripes"]:
            krasot(_kr_blur(((s_ >= pos) & (s_ < pos + w)).astype(np.float32), 0.7 * ss) * smask, kr)
            pos += w + 6
        krasot(_kr_blur((s_ >= Ln * 0.94).astype(np.float32), 0.7 * ss) * smask, K["stripes"][len(K["stripes"]) // 2][0])
    y = 845
    for kr, w in K["stripes"]:
        krasot(_kr_blur(((Y / sc >= y) & (Y / sc < y + w)).astype(np.float32), 0.7 * ss) * M * (1 - SL), kr)
        y += w + 6
    col = [(402, 62), (420, 76), (455, 88), (500, 92), (545, 88), (580, 76), (598, 62), (606, 82), (583, 100), (548, 114),
           (500, 119), (452, 114), (417, 100), (394, 82)]
    krasot(_kr_maska(_kr_chaikin(col), Wd, Hd, sc) * M, K["collar"])
    NUMm, NUMo1, NUMo2, NAMm = (np.zeros((Hd, Wd), np.float32) for _ in range(4))
    if vards:
        nm = _kr_burti(str(vards).upper(), 50 * sc, 0.86, 0.06)
        if nm.width > 390 * sc:
            nm = nm.resize((int(390 * sc), nm.height), Image.LANCZOS)
        na = np.asarray(nm, np.float32) / 255
        h_, w_ = na.shape
        pad = int(h_ * 0.6)
        arc = np.zeros((h_ + pad, w_), np.float32)
        for xi in range(w_):                                          # vārds nedaudz arkā
            off = int(((xi - w_ / 2) ** 2) / (2 * 1500 * sc))
            arc[off:off + h_, xi] = na[:, xi]
        _kr_uzlikt(NAMm, Image.fromarray((arc * 255).astype(np.uint8)), 500 * sc, 226 * sc + pad / 2)
        if vards_izpl:
            NAMm = _kr_blur(NAMm, vards_izpl * ss)
    _kr_uzlikt(NUMm, _kr_burti(str(numurs), 290 * sc, 0.80, 0.03), 500 * sc, 520 * sc)
    ang = math.degrees(math.atan2(ax_b[0] - ax_a[0], ax_b[1] - ax_a[1]))
    for side in (0, 1):
        px, py = ax_a[0] + (ax_b[0] - ax_a[0]) * 0.33, ax_a[1] + (ax_b[1] - ax_a[1]) * 0.33
        _kr_uzlikt(NUMm, _kr_burti(str(numurs), 66 * sc, 0.80, 0.03), (1000 - px if side else px) * sc, py * sc,
                   ang if side else -ang)
    if K["o1"]:
        NUMo1 = _kr_paplest(NUMm, 9 * sc)
        if K["o2"]:
            NUMo2 = _kr_paplest(NUMm, 16 * sc)
            krasot(NUMo2 * M, K["o2"])
        krasot(NUMo1 * M, K["o1"])
    krasot(NUMm * M, K["num"])
    if K.get("name_o") and vards:
        krasot(_kr_paplest(NAMm, 4 * sc) * M, K["name_o"])
    krasot(NAMm * M, K["name"])
    # augstuma karte: apjoms + krokas + audums + uzšuves
    Hh = _kr_blur(M, 38 * ss) * 26 + _kr_blur(M, 10 * ss) * 6
    for side in (0, 1):
        f_ = (lambda p: p) if side == 0 else (lambda p: (1000 - p[0], p[1]))
        for p0, p1, w, amp in (((244, 362), (365, 545), 16, -9), ((250, 392), (335, 650), 22, -6), ((362, 132), (340, 470), 28, 5),
                               ((262, 878), (470, 926), 22, 5), ((240, 938), (292, 1008), 14, -5), ((222, 200), (112, 520), 18, 6),
                               ((244, 300), (168, 640), 14, -6), ((66, 498), (210, 522), 12, -8), ((44, 560), (192, 588), 10, -6),
                               ((170, 230), (90, 420), 10, -4)):
            _kr_kroka(Hh, X, Y, f_(p0), f_(p1), w, amp, sc)
        _kr_kroka(Hh, X, Y, f_((270, 98)), f_((256, 230)), 2.2, -3, sc)    # piedurknes šuve
        _kr_kroka(Hh, X, Y, f_((256, 230)), f_((242, 352)), 2.2, -3, sc)
    _kr_kroka(Hh, X, Y, (500, 300), (500, 960), 40, -4, sc)
    rng = np.random.default_rng(3)
    Hh += _kr_blur(rng.standard_normal((Hd, Wd)).astype(np.float32), 1.0 * ss) * 0.9
    Hh += np.sin((X + Y) * 2 * np.pi / (7 * ss)) * np.sin((X - Y) * 2 * np.pi / (7 * ss)) * 0.18
    Hh += _kr_blur(np.clip(NUMm + NUMo1 + NUMo2 + NAMm, 0, 1), 1.2 * ss) * 2.2
    Hh *= M
    gy, gx = np.gradient(Hh / ss)
    nl = np.sqrt(gx * gx + gy * gy + 1)
    nx, ny, nz = -gx / nl, -gy / nl, 1 / nl
    lx, ly, lz = -0.38, -0.62, 0.68
    ll = math.sqrt(lx * lx + ly * ly + lz * lz); lx, ly, lz = lx / ll, ly / ll, lz / ll
    dif = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
    hl = math.sqrt(lx * lx + ly * ly + (lz + 1) ** 2)
    spec = np.clip((nx * lx + ny * ly + nz * (lz + 1)) / hl, 0, 1) ** 46
    ao = np.clip(1 - 0.07 * (_kr_blur(Hh, 14 * ss) - Hh), 0.55, 1.0)
    rgb = A * ((0.36 + 0.78 * dif) * ao * (1.05 - 0.22 * (Y / Hd)))[..., None] + (spec * 70 * M)[..., None]
    edge = np.clip(_kr_paplest(NUMm, 2.5 * sc) - NUMm, 0, 1)                 # diega šuve gar numuru
    dots = (np.sin(X * 2 * np.pi / (9 * ss)) * np.sin(Y * 2 * np.pi / (9 * ss)) > 0.2).astype(np.float32)
    rgb = np.clip(rgb * (1 - 0.25 * edge * dots)[..., None], 0, 255)
    im = Image.fromarray(np.dstack([rgb, M * 255]).astype(np.uint8), "RGBA")
    return im.resize((izm, int(izm * 1.08)), Image.LANCZOS)


# ---------------------------------------------------------------- aina
_NS_KESA = {}


def _ns_fons(inten):
    """Tumšs fons + prožektora konuss no augšas + vinjete (kešā pēc spožuma)."""
    k = ("fons", round(inten, 2))
    if k not in _NS_KESA:
        np = S.np
        a = np.linspace(0, 1, S.H)[:, None]
        img = (np.array((5, 7, 15)) * (1 - a) + np.array((11, 13, 26)) * a)[:, None, :].repeat(S.W, 1).reshape(S.H, S.W, 3)
        im = Image.fromarray(img.astype(np.uint8), "RGB").convert("RGBA")
        m = Image.new("L", (S.W // 4, S.H // 4), 0)
        d = ImageDraw.Draw(m)
        d.polygon([(480 / 4, -5), (600 / 4, -5), (1140 / 4, 1500 / 4), (-60 / 4, 1500 / 4)], fill=70)
        d.ellipse([110 / 4, 1150 / 4, 970 / 4, 1290 / 4], fill=95)
        m = m.filter(ImageFilter.GaussianBlur(14))
        ma = (np.asarray(m, np.float32) * np.linspace(1.0, 0.45, S.H // 4)[:, None] * inten).clip(0, 255).astype(np.uint8)
        kon = Image.new("RGBA", (S.W, S.H), (255, 240, 215, 0))
        kon.putalpha(Image.fromarray(ma).resize((S.W, S.H), Image.BILINEAR))
        im.alpha_composite(kon)
        _NS_KESA[k] = im
    return _NS_KESA[k].copy()


def _ns_vinjete():
    if "vin" not in _NS_KESA:
        v = Image.new("L", (S.W // 8, S.H // 8), 0)
        ImageDraw.Draw(v).ellipse([-S.W // 14, -S.H // 30, S.W // 8 + S.W // 14, S.H // 8 + S.H // 30], fill=255)
        v = v.filter(ImageFilter.GaussianBlur(12)).resize((S.W, S.H), Image.BILINEAR)
        dark = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
        dark.putalpha(ImageChops.invert(v).point(lambda x: int(x * 0.8)))
        _NS_KESA["vin"] = dark
    return _NS_KESA["vin"]


_NS_PUT = [tuple(x) for x in S.np.random.default_rng(5).uniform(0, 1, (110, 5))]


def _ns_puteklis(im, t, inten):
    L = Image.new("RGBA", (S.W // 2, S.H // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for (u, v, r, ph, sp) in _NS_PUT:
        r, ph, sp = 0.75 + 1.5 * r, ph * 6.28, 10 + 20 * sp
        y = (v * 1500 - t * sp) % 1500
        x = 540 + (u - 0.5) * 2 * (60 + 540 * y / 1500) + 12 * math.sin(t * 0.8 + ph)
        a = int(150 * inten * (0.5 + 0.5 * math.sin(t * 2.3 + ph)) * (1 - y / 1700))
        d.ellipse([x / 2 - r, y / 2 - r, x / 2 + r, y / 2 + r], fill=(255, 245, 225, max(0, a)))
    im.alpha_composite(L.resize((S.W, S.H), Image.BILINEAR))


def _ns_gaismot(img, inten):
    np = S.np
    a = np.asarray(img, np.float32)
    g = (1.08 - 0.30 * np.linspace(0, 1, a.shape[0]))[:, None, None] * (0.18 + 0.82 * inten)
    return Image.fromarray(np.dstack([(a[..., :3] * g).clip(0, 255), a[..., 3:]]).astype(np.uint8), "RGBA")


def _ns_siluets(img, rim):
    a = img.getchannel("A")
    s_ = Image.new("RGBA", img.size, (6, 8, 14, 255)); s_.putalpha(a)
    rm = Image.new("RGBA", img.size, tuple(rim) + (0,))
    rm.putalpha(ImageChops.subtract(a.filter(ImageFilter.MaxFilter(7)), a.filter(ImageFilter.MinFilter(5))))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(rm.filter(ImageFilter.GaussianBlur(6)))
    out.alpha_composite(rm.filter(ImageFilter.GaussianBlur(2)))
    out.alpha_composite(s_)
    return out


def _ns_mala(kom):
    """Silueta mala – komandas krāsā (mājiens); tumšām krāsām – apkakles/sekundārā krāsa."""
    K = _kr_dizains(kom)
    b = K["body"]
    if 0.299 * b[0] + 0.587 * b[1] + 0.114 * b[2] < 60:
        b = K["collar"]
    return tuple(int(x + (255 - x) * 0.15) for x in b)


def _ns_txt(s_, sz, fill, box=None, maxw=880):
    k = ("txt", s_, sz, fill, box, maxw)
    if k not in _NS_KESA:
        f = S.fonts("black", sz)
        while f.getlength(s_) > maxw and sz > 40:
            sz -= 4
            f = S.fonts("black", sz)
        bb = f.getbbox(s_)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        im = Image.new("RGBA", (int(tw + 2 * (40 if box else 24) + 60), int(th + 2 * (40 if box else 24) + 30)), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        cx, cy = im.width / 2, im.height / 2
        if box:
            bw, bh = tw + 70, th + 56
            d.polygon([(cx - bw / 2 + 22, cy - bh / 2), (cx + bw / 2 + 4, cy - bh / 2), (cx + bw / 2 - 22, cy + bh / 2),
                       (cx - bw / 2 - 4, cy + bh / 2)], fill=tuple(box) + (255,))
            d.text((cx, cy), s_, font=f, fill=fill, anchor="mm")
        else:
            sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((cx + 5, cy + 8), s_, font=f, fill=(0, 0, 0, 200), anchor="mm")
            im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
            d.text((cx, cy), s_, font=f, fill=fill, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 255))
        _NS_KESA[k] = im
    return _NS_KESA[k]


def _ns_jzime(izm):
    k = ("jz", izm)
    if k not in _NS_KESA:
        q = _ns_txt("?", int(420 * izm / 820), S.DZELTENS)
        _NS_KESA[k] = (q, q.filter(ImageFilter.GaussianBlur(18 * izm / 820)))
    return _NS_KESA[k]


def _ns_put(L, im, cx, cy, sc=1.0, a=1.0, rot=0.0):
    if a <= 0.01 or sc <= 0.01:
        return
    if sc != 1.0:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if a < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    L.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def _ns_punch(t, t0, amp=0.07, dur=0.25):
    k = (t - t0) / dur
    return 1 + amp * math.sin(math.pi * k) if 0 <= k <= 1 else 1.0


def _ns_trice(t, t0, amp=16, dur=0.3):
    k = t - t0
    if not 0 <= k <= dur:
        return 0, 0
    a = amp * (1 - k / dur) ** 2
    return a * math.sin(k * 97), a * math.cos(k * 73)


def _ns_glitch(im, sila, seed):
    np = S.np
    r = np.random.default_rng(seed)
    a = np.asarray(im.convert("RGB")).copy()
    dx = int(14 * sila)
    a[..., 0] = np.roll(a[..., 0], dx, 1)
    a[..., 2] = np.roll(a[..., 2], -dx, 1)
    for _ in range(int(9 * sila)):
        y0, hh = int(r.uniform(0, S.H - 80)), int(r.uniform(12, 90))
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], int(r.uniform(-90, 90) * sila), 1)
    return Image.fromarray(a, "RGB").convert("RGBA")


def _ns_kamera(im, sc, dx=0.0, dy=0.0, cy=820, cx=540):
    if sc == 1 and not dx and not dy:
        return im
    return im.transform((S.W, S.H), Image.AFFINE, (1 / sc, 0, cx - cx / sc - dx / sc, 0, 1 / sc, cy - cy / sc - dy / sc),
                        resample=Image.BILINEAR)


def _ns_izkartojums(n, thumb=False):
    """[(cx, augša, izmērs)] krekliem: 1 – liels; 2–3 – rindā; 4+ – divās rindās."""
    y0, y1 = (95, 900) if thumb else (150, 1090)
    if n == 1:
        return [(540, y0, 740 if thumb else 820)]
    rindas = 1 if n <= 3 else 2
    per = math.ceil(n / rindas)
    izm = int(min(980 / per - 20, ((y1 - y0) / rindas - 40) / 1.08, 470))
    h = izm * 1.08
    top0 = y0 + max(0, ((y1 - y0) - (rindas * h + (rindas - 1) * 40)) / 2)
    out = []
    for r in range(rindas):
        cnt = per if r < rindas - 1 else n - per * (rindas - 1)
        w = cnt * izm + (cnt - 1) * 20
        out += [(540 - w / 2 + izm / 2 + c * (izm + 20), top0 + r * (h + 40), izm) for c in range(cnt)]
    return out


def _ns_krekli(nsl, thumb=False):
    k = ("kr", id(nsl), thumb)
    if k not in _NS_KESA:
        out = []
        for (kom, v), (cx, top, izm) in zip(nsl["krekli"], _ns_izkartojums(len(nsl["krekli"]), thumb)):
            kb = ("mist", kom, v, izm)
            if kb not in _NS_KESA:
                _NS_KESA[kb] = krekls_reals(kom, v, "?", izm, vards_izpl=11 * izm / 820)
            mist = _NS_KESA[kb]
            out.append({"cx": cx, "top": top, "izm": izm, "mist": mist, "sil": _ns_siluets(mist, _ns_mala(kom)),
                        "cy": top + mist.height / 2, "hint": _ns_gaismot(mist, 0.9)})
        _NS_KESA[k] = out
    return _NS_KESA[k]


def _ns_laiki(nsl, vardi=None, ilg=None):
    """Notikumu laiki āķa ainā (s): rindu parādīšanās pēc balss vārdiem (vardi – jau ar +0,15 s nobīdi), glitch,
    sirdspuksti, izeja. Bez balss – noklusējums."""
    q1, q2 = nsl["q1"][0], nsl["q2"][0]
    if not q1:                                                        # īsā versija: jautājums 2 jau pirmajā kadrā
        ok = bool(vardi)
        a2, b2 = (vardi[0][0], vardi[-1][1]) if ok else (0.15, 1.0)
        vv, t2, c = [len(r.split()) for r in q2], [], 0
        for x in vv:
            t2.append(vardi[min(int(round(c * len(vardi) / max(1, sum(vv)))), len(vardi) - 1)][0] if ok
                      else a2 + (b2 - a2) * c / max(1, sum(vv)))
            c += x
        t2[0] = 0.0
        beigas = max(float(ilg or 0), b2 + 1.0)
        return {"q1": [], "q2": t2, "q2_beigas": b2, "glitch": [min(b2 + 0.4, beigas - 0.7)], "glitch_liels": (-1.0, -1.0),
                "sirds": b2 + 0.2, "izeja": beigas - 0.45, "beigas": beigas}
    a1, b1, a2, b2 = 0.15, 0.85, 1.30, 2.10
    n1 = len(S.balsij(nsl["q1"][1]).split())
    ok = bool(vardi) and len(vardi) > n1
    if ok:
        a1, b1, a2, b2 = vardi[0][0], vardi[n1 - 1][1], vardi[n1][0], vardi[-1][1]

    def rindu(rindas, a, b, sak):
        vv = [len(r.split()) for r in rindas]
        out, c = [], 0
        for x in vv:
            if ok:
                kopa_v = len(vardi) - sak if sak else n1
                j = sak + int(round(c * kopa_v / max(1, sum(vv))))
                out.append(vardi[min(j, len(vardi) - 1)][0])
            else:
                out.append(a + (b - a) * c / max(1, sum(vv)))
            c += x
        return out
    t1 = rindu(q1, a1, b1, 0)
    t1[0] = 0.0                                                       # pirmā rinda – jau pirmajā kadrā
    t2 = rindu(q2, a2, b2, n1)
    lg = (max(t1[-1] + 0.15, a2 - 0.25), a2)
    mazi = [t1[-1] + 0.13]
    if lg[0] - t1[-1] > 0.6:
        mazi.append((t1[-1] + lg[0]) / 2 + 0.05)
    beigas = max(float(ilg or 0), b2 + 1.25)
    mazi.append(min(b2 + 0.45, beigas - 0.7))
    return {"q1": t1, "q2": t2, "q2_beigas": b2, "glitch": mazi, "glitch_liels": lg, "sirds": b2 + 0.25,
            "izeja": beigas - 0.45, "beigas": beigas}


def _ns_sfx_ev(L_):
    """Āķa skaņu efekti (laiks no ainas sākuma)."""
    ev = [(0.0, "riser", 0.5)] + ([(L_["q1"][-1], "klik", 0.6)] if L_["q1"] else [])
    ev += [(x, "glitch_mazs", 0.45) for x in L_["glitch"]]
    ev += [(L_["glitch_liels"][0], "glitch", 0.8)] if L_["glitch_liels"][0] >= 0 else []
    ev += [(x, "klik", 0.6) for x in L_["q2"][1:-1]]
    ev += [(L_["q2"][0], "trieciens", 0.5), (L_["q2"][-1], "trieciens", 0.95), (L_["sirds"], "sirds", 0.9),
           (L_["izeja"] - 0.05, "swoosh", 0.8)]
    return ev


def _ns_jautajums(L, t, rindas, t0s, thumb=False):
    if len(rindas) == 2:
        y0, dy, izm = (1010, 170, (170, 200)) if thumb else (1170, 175, (160, 190))
    else:
        y0, dy, izm = (975, 142, (128, 148, 172)) if thumb else (1135, 146, (128, 148, 172))
    for i, (r, t_) in enumerate(zip(rindas, t0s)):
        k = (t - t_) / 0.16
        if t_ > 0 and k <= 0:
            continue
        sc = (1 + 0.7 * (1 - S.ease(k))) if (t_ > 0 and k < 1) else 1.0
        last = i == len(rindas) - 1
        im = _ns_txt(r, izm[min(i, len(izm) - 1)], (8, 12, 26) if last else S.BALTS, S.DZELTENS if last else None)
        _ns_put(L, im, 540, y0 + i * dy + (12 if last else 0), sc, min(1.0, (t - t_) / 0.08) if t_ > 0 else 1.0, 2 if last else 0)


def aina_noslepums(t, nsl, ilg=None, thumb=False):
    """Noslēpuma āķis – pilns kadrs (RGB, ar savu fonu; drošā zona jau ievērota)."""
    L_ = nsl.get("_laiki") or _ns_laiki(nsl, None, ilg)
    js = _ns_krekli(nsl, thumb)
    q2 = thumb or t >= L_["q2"][0]
    im = _ns_fons(0.9 if q2 else 0.75)
    gl, hint = 0.0, False
    if not thumb:
        for x in L_["glitch"]:
            if 0 <= t - x < 0.09:
                gl, hint = 0.5, True
        a_, b_ = L_["glitch_liels"]
        if a_ <= t < b_:
            gl, hint = 1.0, int(t * S.FPS) % 2 == 0
    sirds = L_["sirds"]
    for i, j in enumerate(js):
        rot = 0.0 if thumb else 0.6 * math.sin(t * 2.0 + i * 1.3)
        sc_k = j["izm"] / 820
        d = ImageDraw.Draw(im)                                        # pakaramais
        cx, yt = j["cx"], j["top"] + 30 * sc_k
        d.line([(cx, yt + 30 * sc_k), (cx, yt - 12 * sc_k)], fill=(190, 196, 208, 255), width=max(3, int(9 * sc_k)))
        d.arc([cx - 30 * sc_k, yt - 72 * sc_k, cx + 30 * sc_k, yt - 12 * sc_k], 140, 400, fill=(190, 196, 208, 255), width=max(3, int(9 * sc_k)))
        if hint:
            _ns_put(im, j["hint"], j["cx"], j["cy"], 1, 1, rot)
            continue
        _ns_put(im, j["sil"], j["cx"], j["cy"], 1.0 if thumb else _ns_punch(t, L_["q2"][0], 0.03), 1, rot)
        q, qg = _ns_jzime(j["izm"])
        tau = 0.0 if thumb else max(0.0, t - (L_["q2"][-1] + 0.2))
        rq = 6 * math.sin(2 * math.pi * tau / 2.0 + i * 0.9) * min(1.0, tau / 0.4)
        p = 1.0 if thumb else ((1 + 0.04 * math.sin(t * 6 + i * 0.9)) * _ns_punch(t, L_["q2"][0], 0.12, 0.3)
                               * _ns_punch(t, sirds, 0.06, 0.2) * _ns_punch(t, sirds + 0.17, 0.05, 0.2))
        _ns_put(im, qg, j["cx"], j["cy"] + 20 * sc_k, p, 0.95, rq)
        _ns_put(im, q, j["cx"], j["cy"] + 20 * sc_k, p, 1, rq)
    if not thumb:
        _ns_puteklis(im, t, 0.7)
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    if q2:
        _ns_jautajums(L, 9.0 if thumb else t, nsl["q2"][0], [0.0] * 3 if thumb else L_["q2"], thumb)
    else:
        _ns_jautajums(L, t, nsl["q1"][0], L_["q1"])
    im.alpha_composite(L)
    im.alpha_composite(_ns_vinjete())
    if thumb:
        return im.convert("RGB")
    kf = (t - L_["q2"][-1]) / 0.16                                    # zibsnis pēdējai rindai
    if 0 <= kf <= 1:
        im.alpha_composite(Image.new("RGBA", (S.W, S.H), (255, 255, 255, int(64 * (1 - kf) ** 1.5))))
    if gl:
        im = _ns_glitch(im, gl, int(t * S.FPS))
    dx, dy = _ns_trice(t, L_["q2"][-1], 16)
    sc = 1 + 0.04 * S.ease(t / max(0.1, L_["izeja"]))
    if t > L_["izeja"]:                                               # izeja: kamera ielido "?" iekšā (centrālākajam kreklam)
        k = S.ease((t - L_["izeja"]) / max(0.05, L_["beigas"] - L_["izeja"]))
        j0 = min(js, key=lambda j: abs(j["cx"] - 540) + 0.5 * abs(j["cy"] - 620))
        fx, fy = j0["cx"] + (540 - j0["cx"]) * (1 - k), j0["cy"] + 20 * j0["izm"] / 820
        im = _ns_kamera(im, sc * (1 + 4.0 * 820 / j0["izm"] * k ** 1.6), dx, dy, cy=fy, cx=fx)
        im.alpha_composite(Image.new("RGBA", (S.W, S.H), (0, 0, 0, int(235 * k * k))))
    else:
        im = _ns_kamera(im, sc, dx, dy)
    return im.convert("RGB")


def noslepums_thumbnail(nsl):
    """Sīktēls: silueti ar "?" + 2. jautājums (augstāk – lai YouTube nosaukums apakšā to neaizsedz)."""
    return aina_noslepums(0.0, nsl, None, thumb=True)


# ---------------------------------------------------------------- skaņas efekti āķim (ģenerēti; aizstāj shorts_sfx\\<nosaukums>.mp3)
def _sfx_lp(x, fc):
    np = S.np
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    v = 0.0
    for i in range(len(x)):
        v += a[i] * (x[i] - v)
        y[i] = v
    return y


def _sfx_norm(x, p):
    m = abs(x).max()
    return x * (p / m) if m > 0 else x


def _sfx_riser(d=1.3):
    np = S.np
    t = np.arange(int(SR * d)) / SR
    n = _sfx_lp(np.random.default_rng(4).standard_normal(len(t)), 400 + 7000 * (t / d) ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(180 + 900 * (t / d) ** 2) / SR) * 0.35
    return _sfx_norm((n + tone) * (t / d) ** 2.2, 0.7)


def _sfx_glitch(d=0.3, seed=9):
    np = S.np
    rng = np.random.default_rng(seed)
    t = np.arange(int(SR * d)) / SR
    y = np.zeros_like(t)
    i = 0
    while i < len(t):
        L = int(SR * rng.uniform(0.012, 0.045))
        f = rng.choice([180, 340, 620, 1250, 2400, 3900])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * (0.35 if rng.random() < 0.7 else 0)
        if rng.random() < 0.35:
            seg = np.round(rng.standard_normal(L) * 3) / 6
        y[i:i + L] = seg[:len(y[i:i + L])]
        i += L
    return _sfx_norm(y * np.exp(-t * 3), 0.6)


def _sfx_trieciens():
    """Kino trieciens: zemas frekvences kritiens + trokšņa sitiens + neliela atbalss."""
    np = S.np
    t = np.arange(int(SR * 1.2)) / SR
    y = np.sin(2 * np.pi * np.cumsum(95 * np.exp(-t * 2.2) + 38) / SR) * np.exp(-t * 3.2)
    y += _sfx_lp(np.random.default_rng(6).standard_normal(len(t)) * np.exp(-t * 18), 900) * 1.6
    out = np.zeros(len(y) + int(SR * 0.4))
    out[:len(y)] += y
    for k, dl in enumerate((0.031, 0.047, 0.071, 0.093)):
        o = int(SR * dl)
        out[o:o + len(y)] += y * 0.35 * 0.55 ** (k + 1)
    return _sfx_norm(out, 0.95)


def _sfx_sirds():
    np = S.np
    t = np.arange(int(SR * 0.7)) / SR
    y = np.zeros_like(t)
    for o, g in ((0.0, 1.0), (0.17, 0.7)):
        k = int(SR * o)
        tt = t[:len(t) - k]
        y[k:] += g * np.sin(2 * np.pi * (48 + 20 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 16)
    return _sfx_norm(_sfx_lp(y, 400), 0.95)


def _sfx_klik():
    np = S.np
    t = np.arange(int(SR * 0.06)) / SR
    return 0.6 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 120) + 0.3 * np.random.default_rng(2).standard_normal(len(t)) * np.exp(-t * 400)


# ---------------------------------------------------------------- dati katram video veidam
def noslepuma_aki(s, krekli, q1, q2, veids_v, x_vards=None, runa_pec=None, atcere=None, atkl=None, bez_q1=False):
    """Ieliek āķī noslēpumu: krekli [(komanda, uzvārds)], jautājums 1 / 2 (neatkārtojas pēdējos video), balss.
    runa_pec – vecā āķa teikums (atskatiem – rezultāts) → 2. ainas balss sākumā."""
    if not (NOSL_AKIS and JAUNS_FANTASY) or not s or not s.get("intro") or not krekli or len(s.get("runa") or []) < 2:
        return s
    try:                                                              # viss vispirms uz kopijas – kļūdas gadījumā video
        bez_q1 = bez_q1 or ISS["on"]                                  # īsā versija: tikai jautājums 2
        a = ((), "") if bez_q1 else S.reta_frase(q1, veids=veids_v, n=3)   # paliek pilnībā ar parasto āķi
        q2_ = [x for x in q2 if repr(x) not in S.Frazes.vesture] or q2  # ne tas pats, kas citā video tikko (atskati u.c.)
        b = S.reta_frase(q2_, veids=veids_v, n=4)
        if x_vards and a[0]:
            a = (tuple(r.replace("{X}", x_vards.upper()) for r in a[0]), a[1].replace("{x}", x_vards.lower()))
        nsl = {"krekli": [(str(k or ""), str(v or "").upper()) for k, v in krekli][:8], "q1": a, "q2": b}
        runa = [str(r) for r in s["runa"]]
        if runa_pec:
            runa[1] = (str(runa_pec).strip() + " " + runa[1]).strip()
        runa[0] = f"{a[1]} {b[1]}".strip()
        if atkl and 0 < atkl[0] < len(runa) - 1:                      # varoņa kartīte: "Mystery solved. Olen Zellweger, …"
            fr_ = S.reta_frase(NOSL_ATKL[atkl[1]], veids=veids_v, n=3)
            nsl["atkl_fr"] = fr_                                      # īsajai versijai
            t_ = runa[atkl[0]]
            runa[atkl[0]] = ("Number one. " + fr_ + " " + t_[len("Number one. "):]) if t_.startswith("Number one. ") \
                else (fr_ + " " + t_)
        if atcere:                                                    # cilpa: "…and remember: 7 goals." → "…and remember the name."
            runa[-1] = re.sub(r"and remember:\s*[^.?!]*\d[^.?!]*[.?!]?\s*$", f"and remember {atcere}.", runa[-1])
            runa[-1] = _ns_beigas(runa[-1], veids_v, atcere)            # beigu teikuma varianti (NOSL_BEIGAS)
        s["runa"][:] = runa
        s["intro"]["noslepums"] = nsl
        s["intro"]["ilgums"] = 3.3
        print(f"ĀĶIS: noslēpums – \"{' '.join(a[0])}\" → \"{' '.join(b[0])}\"")
    except Exception as ex:                                           # noqa: BLE001
        print(f"  (noslēpuma āķis: {type(ex).__name__}: {ex} – parastais āķis)")
        (s.get("intro") or {}).pop("noslepums", None)
    return s


# beigu teikums noslēpuma video (pēdējais "Follow…" teikums; pirmais variants – līdzšinējais teksts)
NOSL_BEIGAS = {
    "speletajs": ["Follow, and remember {atcere}.", "Follow, and keep an eye on him.", "Follow, and remember this jersey.",
                  "Follow, and we'll see who was right."],
    "vartsargs_labs": ["Follow, and remember: this goalie is stealing games.", "Follow, and keep an eye on this goalie.",
                       "Follow, and remember this jersey.", "Follow, and we'll see if the wall holds."],
    "vartsargs_slikts": ["Follow, and remember: this goalie is costing games.", "Follow, and keep an eye on this goalie.",
                         "Follow, and remember this jersey.", "Follow, and we'll see if he turns it around."],
    "komanda_laim": ["Follow, and remember: this team is winning on luck.", "Follow, and keep an eye on this team.",
                     "Follow, and remember these colors.", "Follow, and we'll see who was right."],
    "komanda_nelaim": ["Follow, and remember: this team is better than its record.", "Follow, and keep an eye on this team.",
                       "Follow, and remember these colors.", "Follow, and we'll see who was right."],
    "fakti": ["Follow for the NHL week in numbers, and remember {atcere}.", "New numbers every Friday. Follow, and remember {atcere}.",
              "That's the week in numbers. Follow, and remember {atcere}.", "Follow for next week's numbers, and remember {atcere}."],
}


def _ns_beigas(teik, veids_v, atcere):
    """Pēdējā "Follow…, and remember…" teikuma vietā – variants no NOSL_BEIGAS (šī veida pēdējos 2 video neatkārtojas)."""
    try:
        i = teik.rfind("Follow")
        if i < 0 or "remember" not in teik[i:]:
            return teik
        aste = teik[i:]
        if veids_v == "fakts":
            k = "fakti"
        elif veids_v == "vartsargi":
            k = "vartsargs_slikts" if "costing" in aste else "vartsargs_labs"
        elif veids_v == "komandas":
            k = "komanda_nelaim" if "better than" in aste else "komanda_laim"
        elif veids_v == "speletaji":
            k = "speletajs"
        else:
            return teik
        return teik[:i] + S.reta_frase(NOSL_BEIGAS[k], veids=veids_v, n=2).format(atcere=atcere)
    except Exception:                                                 # noqa: BLE001
        return teik


def _virsr_izvele(saraksts, veids, lauki):
    """YouTube virsraksts no saraksta: tikai tie, kuriem ir visi dati; šī veida pēdējos 4 video neatkārtojas."""
    lauki = {k: v for k, v in lauki.items() if v not in (None, "")}
    der = []
    for x in saraksts:
        try:
            x.format(**lauki)
            der.append(x)
        except (KeyError, IndexError, ValueError):
            pass
    x = S.reta_frase(der or saraksts[:1], veids=veids, n=4 if len(der) > 4 else max(1, len(der) - 1))
    try:
        return x.format(**lauki)
    except (KeyError, IndexError, ValueError):
        return None


def _ns_virsraksts(s, vards, komanda=False):
    """YouTube virsrakstā spēlētāja / komandas vārda vietā "guess who's …" / "guess which team is …"; vārds – aprakstā."""
    if not (NOSL_VIRSRAKSTS and s and vards and (s.get("intro") or {}).get("noslepums")):
        return
    try:
        v = str(s.get("virsraksts") or "")
        pat = (r"(?:The\s+)?" if komanda else r"(?:[A-ZÀ-Ž][\w'’.\-]*\s+)?") + re.escape(str(vards)) + r"(\s+(?:is|are|has|have)\b)?"
        m = re.search(pat, v, flags=re.I)
        if not m:
            return
        verb = (m.group(1) or "").strip().lower()
        if komanda:
            rep = "guess which team" + {"is": " is", "are": " is", "has": " has", "have": " has"}.get(verb, "")
        else:
            rep = "guess who" + {"is": "'s", "are": "'s", "has": " has", "have": " has"}.get(verb, "")
        nos = v[m.start():m.end() - len(m.group(1) or "")].strip()
        jauns = v[:m.start()] + rep + v[m.end():]
        if m.start() == 0:
            jauns = jauns[0].upper() + jauns[1:]
        s["virsraksts"] = jauns
        _ns_vards_apraksta(s, re.sub(r"^The ", "", nos))
    except Exception:                                                 # noqa: BLE001
        pass


def _ns_vards_apraksta(s, nos):
    """Noslēpuma vārds aprakstā – saraksta beigās ("#1: Leon Draisaitl"), lai meklēšana atrod; ja vārds jau ir
    apraksta tekstā (faktu stāsts) – nedublē."""
    nos = str(nos or "").strip()
    if not nos or nos.lower() in str(s.get("apraksts") or "").lower():
        return
    if isinstance(s.get("saraksts"), list):
        s["saraksts"].append(f"#1: {nos}")
    else:
        s["apraksts"] = (str(s.get("apraksts") or "").rstrip() + f"\n#1: {nos}").strip()


# xG virsraksts noslēpuma video – pēc VAROŅA (kartīte, par kuru āķis), ne pēc saraksta #1:
# līdz 04.11. nelaimīga varoņa video virsrakstā palika laimīgākā vārds ("Alexis Lafrenière is running HOT…").
# (kopš 10.11.2026 – saraksti; pirmais – līdzšinējais). {G} "9 goals", {xG} "3.6", {gs} "10.0", {pdo} "107.9"
NOSL_XG_VIRSR = {
    ("speletaji", True): ["Guess who's running HOT… but xG says it won't last 🏒",
                          "Guess who's scoring way above his chances – can it last?",
                          "{G} on {xG} expected – guess who's living on luck",
                          "Guess who's the luckiest scorer in the NHL right now",
                          "Hot streak or pure luck? Guess who xG is worried about",
                          "Guess who's finishing everything – xG says it's luck"],
    ("speletaji", False): ["Guess who's due for goals – xG says they're coming 🏒",
                           "{G} on {xG} expected – guess who's due",
                           "Guess who's the unluckiest scorer in the NHL right now",
                           "Guess who xG says is about to break out",
                           "Bad luck, not bad play – guess who's due for goals",
                           "Guess who's a buy-low – the numbers behind the slump"],
    ("vartsargi", True): ["Guess who's STEALING games – the numbers 🥅",
                          "Guess which goalie is saving {gs} goals above expected",
                          "Guess the hottest goalie in the NHL – by the numbers",
                          "Brick wall or luck? Guess which goalie the numbers love",
                          "Guess which goalie is carrying his team right now"],
    ("vartsargi", False): ["Guess which goalie is COSTING games – the numbers 🥅",
                           "Guess which goalie is {gs} goals worse than expected",
                           "Bad luck or bad goalie? Guess who the numbers say",
                           "Guess which goalie needs a turnaround – fast"],
    ("komandas", True): ["Guess which team is winning on LUCK – here's the proof 🏒",
                         "Guess which team's record is too good to be true",
                         "PDO {pdo}: guess which team is riding the bounces",
                         "Good or lucky? Guess which team the numbers doubt"],
    ("komandas", False): ["Guess which team is better than its record – here's the proof 🏒",
                          "Guess which team the bounces keep beating",
                          "PDO {pdo}: guess which team is due for a turnaround",
                          "Guess the unluckiest team in the NHL right now"],
}


def _xg_lauki(hero):
    """Skaitļi virsrakstam no varoņa kartītes."""
    out = {}
    try:
        kl = str(((hero.get("viz") or {}).get("kart") or {}).get("liels") or "")
        j = next((x for it in (hero.get("viz") or {}).get("spec") or [] for x in it[1:]
                  if isinstance(x, dict) and x.get("tips") == "joslas"), None)
        if j and len(j.get("rind") or []) >= 2 and str(j["rind"][0][0]).upper() == "GOALS":
            G = int(round(float(j["rind"][0][1])))
            out["G"], out["xG"] = f"{G} goal{'' if G == 1 else 's'}", str(j["rind"][1][2])
        v = _parsk(kl)
        if v is not None:
            out["gs"], out["pdo"] = f"{abs(v):.1f}", f"{v:.1f}"
    except Exception:                                                 # noqa: BLE001
        pass
    return out


def _ns_xg_virsraksts(s, veids, laim, vards, hero=None):
    if not (NOSL_VIRSRAKSTS and s and vards and (s.get("intro") or {}).get("noslepums")):
        return
    v_ = veids if veids in ("vartsargi", "komandas") else "speletaji"
    sar = NOSL_XG_VIRSR[(v_, bool(laim))]
    s["virsraksts"] = _virsr_izvele(sar, v_, _xg_lauki(hero or {})) or sar[0]
    _ns_vards_apraksta(s, vards)


def _ns_fantasy(s):
    af = s.get("aki_f") or {}
    stream = "STREAMER" in str((s.get("intro") or {}).get("tag", "")).upper()
    kk = s.get("kartes") or []                                        # #1 kartīte (streameriem – pēdējā, secība #3 → #1)
    k1 = next((j for j, c in enumerate(kk) if c.get("tips") == "fantasy" and c.get("nr") == 1 and c.get("liels") in ("ADD", "STREAM")),
              next((j for j, c in enumerate(kk) if c.get("tips") == "fantasy"), None))
    if stream:                                                        # streameri (kopš 11.11.2026): #1 netiek slēpts – āķī tikai
        noslepuma_aki(s, [(af.get("kom"), af.get("vards"))], NOSL_Q1["speletajs"], NOSL_Q2["streameri"], "streameri",
                      bez_q1=True)                                    # jautājums 2, bez "Mystery solved", vārds virsrakstā
        _ns_stream_virsraksts(s, kk[k1] if k1 is not None else {})
        return s
    noslepuma_aki(s, [(af.get("kom"), af.get("vards"))], NOSL_Q1["speletajs"], NOSL_Q2["fantasy"],
                  "fantasy", atkl=(k1 + 1, "speletajs") if k1 is not None else None)
    v0 = str(s.get("virsraksts") or "")
    _ns_virsraksts(s, af.get("vards"))
    if str(s.get("virsraksts") or "") != v0:                          # "guess who" izdevās → viens no variantiem
        try:
            m_ = re.match(r"(\d+) fantasy hockey (?:pickups?|streamers)(?: & (\d+) drops?)?", v0)
            mg = re.search(r"has (\d+) games? left", v0)
            viz = (kk[k1].get("viz") or {}) if k1 is not None else {}
            rost = viz.get("rost")
            n_, d_ = (int(m_.group(1)), int(m_.group(2) or 0)) if m_ else (None, 0)
            g_ = int(mg.group(1)) if mg else viz.get("sp_nak")
            lauki = {"n": n_, "pickups": "pickup" if n_ == 1 else "pickups", "adds": "add" if n_ == 1 else "adds",
                     "D_amp": f" & {d_} drop{'' if d_ == 1 else 's'} " if d_ else " ",
                     "D_comma": f", {d_} drop{'' if d_ == 1 else 's'} " if d_ else " ",
                     "r": (f"{rost:.0f}" if rost >= 1 else "under 1") if isinstance(rost, (int, float)) else None,
                     "g": g_}
            jauns = _virsr_izvele(NOSL_FANTASY_VIRSR["streameri" if stream else "fantasy"],
                                  "streameri" if stream else "fantasy", lauki)
            if jauns:
                s["virsraksts"] = re.sub(r"\s+", " ", jauns).strip()
        except Exception:                                             # noqa: BLE001
            pass
    return s


# streameri (kopš 11.11.2026) – #1 netiek slēpts: vārds virsrakstā (palīdz meklēšanā); pirmais – shorts.py virsraksts
VIRSR_STREAM = ["{n} fantasy hockey streamers for the rest of the week – {vards} has {gs} left 🏒",
                "Stream {vards}? {n} fantasy hockey streamers before Sunday",
                "{vards} is just {r}% rostered with {gs} left – fantasy hockey streamers",
                "Need games before Sunday? {n} fantasy hockey streamers, led by {vards}",
                "{gs} left: why {vards} is our top fantasy hockey streamer"]   # {gs} – "4 games" / "1 game"


def _ns_stream_virsraksts(s, c1):
    """Streameru virsraksts ar #1 vārdu (bez "guess who") – viens no VIRSR_STREAM; ja kaut kā trūkst – shorts.py virsraksts."""
    try:
        v0 = str(s.get("virsraksts") or "")
        m_ = re.match(r"(\d+) fantasy hockey streamers", v0)
        mg = re.search(r"– (.+?) has (\d+) games? left", v0)
        viz = c1.get("viz") or {}
        vards = f"{c1.get('v1', '')} {c1.get('v2', '')}".strip() or (mg.group(1) if mg else None)
        rost = viz.get("rost")
        g = viz.get("sp_nak") if viz.get("sp_nak") is not None else (int(mg.group(2)) if mg else None)
        gs = f"{int(g)} game{'' if int(g) == 1 else 's'}" if g is not None else None
        lauki = {"n": int(m_.group(1)) if m_ else None, "vards": vards, "gs": gs,
                 "r": (f"{rost:.0f}" if rost >= 1 else "under 1") if isinstance(rost, (int, float)) else None}
        jauns = _virsr_izvele(VIRSR_STREAM, "streameri", lauki)
        if jauns:
            s["virsraksts"] = re.sub(r"\s+", " ", jauns).strip()
    except Exception:                                                 # noqa: BLE001
        pass


NOSL_FANTASY_VIRSR = {   # {D_amp} " & 2 drops" / " ", {D_comma} ", 2 drops" / " "; pirmais – līdzšinējais
    "fantasy": ["{n} fantasy hockey {pickups}{D_amp}for next week – guess who's a must-add 🏒",
                "Guess who's still on waivers – {n} fantasy {pickups} for next week",
                "Fantasy hockey waiver wire: {n} {adds}{D_comma}– guess the steal of the week",
                "Guess who's rostered in just {r}% of leagues – next week's fantasy pickups",
                "{n} fantasy hockey {adds} before your league wakes up – guess who's #1",
                "Next week's fantasy hockey moves: {n} {adds}{D_comma}– guess who"],
    "streameri": ["{n} fantasy hockey streamers for the rest of the week – guess who has {g} games left 🏒",
                  "Guess the best stream before Sunday – {n} fantasy hockey streamers",
                  "{n} quick fantasy hockey adds for the rest of the week – guess who's #1",
                  "Need games before Sunday? Guess our top fantasy streamer",
                  "Guess who's just {r}% rostered with {g} games left – fantasy streamers"],
}


def _ns_xg(s, veids, hero):
    laim = hero["viz"].get("grupa") == "laim"
    if veids == "komandas":
        noslepuma_aki(s, [(hero.get("badge"), "")], NOSL_Q1["komanda"], NOSL_Q2["kom_laim" if laim else "kom_nelaim"], veids,
                      atcere="this team", atkl=(len(s["runa"]) - 2, "komanda"))
        k_ = S.KOMANDAS.get(str(hero.get("badge") or ""))
        _ns_xg_virsraksts(s, veids, laim, f"{k_[0]} {k_[1]}" if k_ else hero.get("v2"), hero)
    else:
        q1 = NOSL_Q1["vartsargs" if veids == "vartsargi" else "speletajs"]
        q2 = NOSL_Q2[("va_labs" if laim else "va_slikts") if veids == "vartsargi" else ("sp_laim" if laim else "sp_nelaim")]
        noslepuma_aki(s, [(hero.get("badge"), hero.get("v2"))], q1, q2, veids, atcere="the name",
                      atkl=(len(s["runa"]) - 2, "vartsargs" if veids == "vartsargi" else "speletajs"))
        _ns_xg_virsraksts(s, veids, laim, " ".join(str(x) for x in (hero.get("v1"), hero.get("v2")) if x), hero)
    return s


def _ns_fakti(rez, hero):
    atsl = str(hero.get("atsl", ""))
    kom, v = hero.get("badge"), hero.get("vards")
    if not kom or atsl.startswith("tiesnesis"):
        return rez
    if atsl.startswith(("points_serija", "goals_serija", "liela:")):
        kr, q1, q2, kom_v = [(kom, v)], NOSL_Q1["speletajs"], NOSL_Q2["fakti_sp"], None
    elif atsl.startswith("vartsargs"):
        kr, q1, q2, kom_v = [(kom, v)], NOSL_Q1["vartsargs"], NOSL_Q2["fakti_va"], None
    elif atsl.startswith("liela_duo"):
        kr, q1, q2, kom_v = [(kom, x.strip()) for x in str(v).split("&")][:3], NOSL_Q1["duo"], NOSL_Q2["fakti_duo"], None
    else:
        kr, q1, kom_v = [(kom, "")], NOSL_Q1["komanda"], v
        q2 = NOSL_Q2["fakti_kom_zaud" if atsl.startswith("kom_zaud") else "fakti_kom"]
    vecais = str(rez["runa"][0])
    noslepuma_aki(rez, kr, q1, q2, "fakts", atcere="this team" if kom_v else ("these names" if len(kr) > 1 else "the name"))
    # (kopš 11.11.2026 – bez atklāšanas frāzes "Mystery solved." pie #1; āķis – kā līdz šim)
    if (rez.get("intro") or {}).get("noslepums"):
        m = re.match(r"(The NHL week in numbers[^.]*\.)", vecais)       # ievada teikums → 2. ainā
        if m and not rez["runa"][1].startswith("The NHL week"):
            rez["runa"][1] = m.group(1) + " " + rez["runa"][1]
        if kom_v:
            _ns_virsraksts(rez, kom_v, komanda=True)
        elif not atsl.startswith("liela_duo"):
            _ns_virsraksts(rez, v)
    return rez


# ================================================================ ĪSĀ VERSIJA (--iss, kopš 10.11.2026)
# Āķis tikai ar jautājumu 2 → saīsinātas ainas → beigās varoņa kartīte paliek, balss saka cilpas teikumu ("So… why is he
# still free?") un video pāriet atpakaļ uz āķi. Bez THE FINAL VERDICT un bez SHEET piedāvājuma balsī (aprakstā – paliek).
# Fantasy ~45 s, streameri ~35 s, xG ~40 s, fakti ~30 s, atskati ~30 s.  Palaišana:  python ShortsB.py --veids fantasy --iss
ISS = {"on": False}
ISS_NOKLUSETS = ("speletaji", "vartsargi", "komandas", "fantasy", "streameri", "fakts")   # īsā pēc noklusējuma (--long – garā)
ISS_CILPA_ILG = 1.6              # beigu ainas minimums (ar balsi – cilpas teikuma garums + 0,45 s)
ISS_CILPA_Q = ["So… {q}", "Your call: {q}", "{Q}", "One more time: {q}"]          # jautājums 2 – jautājums
ISS_CILPA_APG = ["{Q}", "Like we said: {q}"]                                        # jautājums 2 – apgalvojums
ISS_FAKTI_BEIGAS = ["Which one surprised you most? Follow for the NHL week in numbers.",
                    "Which number would you put first? Follow for more.",
                    "Did we miss one? Tell us, and follow for next week's numbers."]
_VARDIEM = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

ISS_FAN_IEVADS = {
    False: ["{N} pickups for next week, all {rost}. Green games mean soft defenses.",
            "{N} adds for next week, all {rost}. Green means an easy matchup.",
            "Next week's waiver wire: {n} adds, all {rost}. Green games are the soft ones."],
    True: ["{N} streamers for the rest of the week, all {rost}. Green games mean soft defenses.",
           "{N} quick adds before Sunday, all {rost}. Green means an easy matchup.",
           "Need games before Sunday? {N} streamers, all {rost}. Green games are the soft ones."]}
ISS_FAN_ROST = ["Only {r} percent of leagues have him.", "Just {r} percent rostered.", "{a} percent of leagues still don't have him."]
ISS_DROP_VIRSR = [[("WHO", S.BALTS), ("TO", S.BALTS), ("CUT", S.DZELTENS)],
                  [("TIME", S.BALTS), ("TO", S.BALTS), ("CUT", S.DZELTENS)]]
ISS_DROP_VIENS = ["Cut {a}.", "Time to cut {a}.", "Drop {a}."]
ISS_DROP_DIVI = ["Cut {a} and {b}.", "Time to move on from {a} and {b}.", "On the way out: {a} and {b}."]

ISS_XG_KARTE = {   # (līgas karte, ja kartes nav – kārtis)
    "speletaji": (["Goals versus expected goals since {no}. Above the line: lucky. Below it: due.",
                   "Every NHL scorer since {no}. Above the line is luck. Below it, goals are coming.",
                   "Goals against the chances, since {no}. The further from the line, the bigger the luck."],
                  ["Goals versus expected goals since {no}: three lucky, three due.",
                   "Since {no}: three scorers riding luck, three still waiting."]),
    "vartsargi": (["Goals allowed versus expected since {no}. Below the line: stealing games. Above it: costing them.",
                   "Every NHL goalie since {no}. Below the line, he's stealing games.",
                   "Goals allowed against the chances, since {no}. The further from the line, the bigger the story."],
                  ["Goals saved above expected since {no}: three stealing games, three costing them."]),
    "komandas": (["Every NHL team's PDO since {no}. Above the line: lucky. Below it: unlucky.",
                  "PDO since {no}: shooting plus save percentage. Above the line, the bounces go their way.",
                  "Shooting and save percentage since {no}. One hundred is normal. Above it is luck."],
                 ["PDO since {no}: three lucky teams, three unlucky."]),
}
ISS_XG_GRUPA = {   # (virsraksts kāršu ainā, balss sākums)
    ("speletaji", "laim"): ([("RUNNING", S.BALTS), ("HOT", S.DZELTENS)],
                            ["Running hot: {names}.", "Riding the luck: {names}.", "Scoring above their chances: {names}."]),
    ("speletaji", "nelaim"): ([("DUE", S.BALTS), ("FOR", S.BALTS), ("GOALS", S.DZELTENS)],
                              ["Due for goals: {names}.", "Still waiting on goals: {names}.", "Getting robbed: {names}."]),
    ("vartsargi", "laim"): ([("STEALING", S.BALTS), ("GAMES", S.DZELTENS)],
                            ["Stealing games: {names}.", "Hard to beat right now: {names}."]),
    ("vartsargi", "nelaim"): ([("COSTING", S.BALTS), ("GAMES", S.DZELTENS)],
                              ["Costing games: {names}.", "Struggling in net: {names}."]),
    ("komandas", "laim"): ([("LIVING", S.BALTS), ("ON", S.BALTS), ("LUCK", S.DZELTENS)],
                           ["Living on luck: {names}.", "Riding the bounces: {names}."]),
    ("komandas", "nelaim"): ([("OWED", S.BALTS), ("BOUNCES", S.DZELTENS)],
                             ["Better than their record: {names}.", "Still waiting on the bounces: {names}."]),
}
ISS_XGATS_IEVADS = ["On {d}, we flagged {n} {X}.", "Our list from {d}: {n} {X}.", "{N} {X}, flagged on {d}."]
ISS_FANATS_IEVADS = ["Our picks for the week of {no} to {lidz}.", "Last week's calls, {no} to {lidz}.",
                     "Here's how last week's picks did."]
ISS_ATS_PIRMS = ["Every call, on the record.", "No edits, no excuses.", "Hits and misses, all on the record."]


def _iss_args(a, veids):
    """Īsās versijas argumenti. Fakti (kopš 11.11.2026): faktu skaits – kā --fakts (top5 → 5, top3 → 3, 1,3,5 → 3,
    viens numurs / auto → viens fakts); īsajā versijā #N…#2 – viens teikums, #1 – pilnais stāsts."""
    return a


def _vardu_saraksts(v):
    v = [x for x in v if x]
    return v[0] if len(v) == 1 else (", ".join(v[:-1]) + " and " + v[-1] if v else "")


def _iss_cilpa(s, veids_v, pirms=""):
    """Cilpas teikums: (pirms) + jautājums 2 – video beigas ved atpakaļ uz āķi."""
    nsl = (s.get("intro") or {}).get("noslepums") or {}
    q = str((nsl.get("q2") or (None, ""))[1] or "").strip()
    if not q:
        return (str(pirms) + " Follow for more.").strip()
    x = S.reta_frase(ISS_CILPA_Q if q.endswith("?") else ISS_CILPA_APG, veids=veids_v, n=2)
    ql = q if q.startswith(("I ", "xG")) else q[0].lower() + q[1:]
    return (str(pirms) + " " + x.format(q=ql, Q=q)).strip()


def _iss_outro(s):
    s["outro"] = {"iss": True, "_bez_ieejas": True, "rindas": [], "info": []}


def _gp(c):
    m_ = re.search(r"(\d+) GP", str(c.get("info", "")))
    return int(m_.group(1)) if m_ else None


def _iss_fan_teik(c, stream):
    v = c.get("viz") or {}
    P, gp, sp = v.get("pts"), _gp(c), v.get("sp_nak")
    t_ = [f"{c.get('v1', '')} {c.get('v2', '')}".strip() + f", {S.kom_nos(c.get('badge'))}."]
    if P is not None and gp:
        t_.append(f"{P} point{'' if P == 1 else 's'} in {gp} games"
                  + (f", and {sp} game{'' if sp == 1 else 's'} {'left this week' if stream else 'next week'}." if sp else "."))
    if c.get("_zim_frase"):
        t_.append(str(c["_zim_frase"]))
    return " ".join(t_)


def _iss_drop(drops, k2):
    kartis, P, GP = [], 0, 0
    for c in drops:
        v = c.get("viz") or {}
        p_, g_ = int(v.get("pts") or 0), _gp(c)
        P, GP = P + p_, GP + (g_ or 0)
        kartis.append({"kom": str(c.get("badge", "")), "poz": v.get("poz", ""), "akc": tuple(c["akc"]),
                       "liels": f"{p_} PT{'' if p_ == 1 else 'S'}", "maz": f"IN {g_} GP" if g_ else "LAST 14 DAYS",
                       "lab": str(c.get("liels", "DROP"))})
    aina = {"tips": "fantasy_divi", "ilgums": 3.6, "tag": k2.get("tag", ""), "_tv": k2.get("_tv"),
            "virsr": S.reta_frase(ISS_DROP_VIRSR, veids="fantasy", n=1), "kartites": list(drops)}
    vardi = [f"{c.get('v1', '')} {c.get('v2', '')}".strip() for c in drops]
    if len(vardi) == 1:
        t_ = S.reta_frase(ISS_DROP_VIENS, veids="fantasy", n=1).format(a=vardi[0])
    else:
        t_ = S.reta_frase(ISS_DROP_DIVI, veids="fantasy", n=1).format(a=", ".join(vardi[:-1]), b=vardi[-1])
    pt = "No points" if P == 0 else ("One point" if P == 1 else f"{P} points")
    if GP and P / GP < 0.5:
        t_ += f" {pt} between them in their last {GP} games." if len(drops) > 1 else f" {pt} in his last {GP} games."
    else:
        t_ += " Their schedules turn next week." if len(drops) > 1 else " His schedule turns next week."
    return aina, t_


# ---------------------------------------------------------------- īsā versija: divi DROP spēlētāji vienā ainā (mazākas kartītes)
def _nv_divi_laiki(c):
    """(parādīšanās[], zīmogs[]) – kartīte parādās, kad balss nosauc uzvārdu (bez balss – pēc kārtas)."""
    K = c.get("kartites") or []
    ilg, vardi = c.get("_ilg", c.get("ilgums", 3.6)), c.get("_vardi") or []
    def laiks(txt):
        w_ = [re.sub(r"[^a-z0-9]", "", w.lower()) for w in str(txt or "").split()]
        w_ = [x for x in w_ if x]
        return (_nv_vards_laiks(vardi, *w_) or _nv_vards_laiks(vardi, w_[-1])) if w_ else None
    t_in, t_st = [], []
    for i, k in enumerate(K):
        tv1, tv2 = laiks(k.get("v1")), laiks(k.get("v2"))
        if i == 0:
            a_ = 0.35                                                 # pirmā – uzreiz
        else:
            a_ = max(t_in[-1] + 0.45, ((tv1 or tv2) - 0.3) if (tv1 or tv2) else 1.0)
        t_in.append(a_)
        t_st.append(max(a_ + 0.5, ((tv2 or tv1) + 0.35) if (tv2 or tv1) else a_ + 0.6))
    lim = max(1.2, ilg - 0.6)
    return [min(x, lim - 0.6) for x in t_in], [min(x, lim) for x in t_st]


def _spec_x(k, lab):
    for it in (k.get("viz") or {}).get("spec") or []:
        for x in it[1:]:
            if isinstance(x, dict) and str(x.get("lab", "")).upper() == lab:
                return x
    return None


def _mk_flizes(k, veids):
    """3 flīzes mazajai kartītei: [(virsraksts, vērtība, apakšā)]."""
    v = k.get("viz") or {}
    gp = _gp(k)
    if veids in XG_VEIDI:
        b = k.get("bars") or []
        A = float(b[0][1]) if len(b) > 0 else None
        B_ = float(b[1][1]) if len(b) > 1 else None
        liels = str((v.get("kart") or {}).get("liels") or "–")
        if veids == "speletaji":
            sh = _spec_x(k, "SHOOTING %") or {}
            return [("GOALS", f"{int(A)}" if A is not None else "–", f"IN {gp} GP" if gp else ""),
                    ("EXPECTED", f"{B_:.1f}" if B_ is not None else "–", "xG"),
                    ("SHOOTING %", str(sh.get("val") or "–"), str(sh.get("sub") or "").upper())]
        if veids == "vartsargi":
            sv = _spec_x(k, "SAVE %") or {}
            return [("GSAx", liels, "VS EXPECTED"),
                    ("ALLOWED", f"{int(A)}" if A is not None else "–", f"ON {B_:.1f} EXPECTED" if B_ is not None else ""),
                    ("SAVE %", str(sv.get("val") or "–"), str(sv.get("sub") or "").upper())]
        j = next((x for it in v.get("spec") or [] for x in it[1:] if isinstance(x, dict) and x.get("tips") == "joslas"), None)
        rind = (j or {}).get("rind") or []
        rec = _spec_x(k, "RECORD") or {}
        return [("PDO", liels, "AVERAGE 100"),
                ("GOAL DIFF", str(rind[0][2]) if rind else "–", f"xGD {rind[1][2]}" if len(rind) > 1 else ""),
                ("RECORD", str(rec.get("val") or v.get("poz") or "–"), str(rec.get("sub") or "").upper())]
    rost = v.get("rost")
    ned = v.get("ned") or []
    gr = sum(1 for n_ in ned if n_.get("o") and tuple(n_.get("kr") or ()) == tuple(S.SARKANS))
    return [("PTS", str(v.get("pts", "–")), f"IN {gp} GP" if gp else "LAST 14 DAYS"),
            ("ROSTERED", f"{rost:.0f}%" if isinstance(rost, (int, float)) else "–", "ESPN"),
            ("NEXT WEEK", f"{v.get('sp_nak', '–')} GP", f"{gr} TOUGH" if gr else "GAMES")]


def _nv_divi_karte(k, W, H, veids="fantasy"):
    """Viena mazākā kartīte (tas pats stils, kas lielajai): vārds, 3 flīzes, (ja vieta) iemesls. H < 400 – kompakta."""
    v = k.get("viz") or {}
    prim, sek = kom_krasas(k.get("badge"))
    F = S.fonts
    liela = H >= 400
    pad = 26
    im = Image.new("RGBA", (W + 2 * pad, H + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    box = (pad, pad, pad + W, pad + H)
    for p_, al_ in ((12, 22), (7, 45), (3, 80)):                       # mīksts spīdums ap rāmi (kā lielajai kartītei)
        d.rounded_rectangle((box[0] - p_, box[1] - p_, box[2] + p_, box[3] + p_), radius=34 + p_, outline=prim + (al_,), width=p_ + 2)
    d.rounded_rectangle(box, radius=34, fill=(10, 14, 32, 240))
    wm = _nv_timg(str(k.get("badge", "")), F("black", 230 if liela else 170), prim + (55,))
    im.alpha_composite(wm, (int(box[2] - wm.width - 10), int(box[1] + 4)))
    x0, y0 = box[0] + 34, box[1]
    v1 = str(k.get("v1") or "").upper()
    f1 = F("semi", 40 if liela else 32)
    ya = 30 if liela else 18
    if v1:
        d.text((x0, y0 + ya), v1, font=f1, fill=(255, 255, 255, 225))
    lab_ = str(k.get("badge", "")) if veids == "komandas" else f"{v.get('poz', '')}  ·  {k.get('badge', '')}"
    d.text((x0 + (d.textlength(v1, font=f1) + 22 if v1 else 0), y0 + ya + (6 if liela else 4)), lab_,
           font=F("black", 30 if liela else 26), fill=_NV_LAB)
    vards = str(k.get("v2", "")).upper()
    fv = S.ietilpinat(d, vards, "black", 112 if liela else 84, W - 450)   # labajā pusē – vieta zīmogam
    yv = 168 if liela else 124
    d.text((x0, y0 + yv), vards, font=fv, fill=S.BALTS, anchor="ls")
    yp, xe = y0 + yv + 18, box[2] - 34
    xs = x0 + (xe - x0) * 0.6
    d.polygon([(x0, yp), (xs + 8, yp), (xs - 4, yp + 11), (x0, yp + 11)], fill=prim)
    d.polygon([(xs + 20, yp), (xe, yp), (xe, yp + 11), (xs + 8, yp + 11)], fill=sek)
    fl = _mk_flizes(k, veids)
    gap = 16
    tw = (W - 68 - 2 * gap) / 3
    ty0 = y0 + (214 if liela else 158)
    ty1 = ty0 + (132 if liela else 108)
    for i, (lab, val, sub) in enumerate(fl):
        tx = x0 + i * (tw + gap)
        d.rounded_rectangle([tx, ty0, tx + tw, ty1], radius=22, fill=_NV_TILE + (255,))
        d.text((tx + 18, ty0 + (12 if liela else 8)), lab, font=F("semi", 26 if liela else 22), fill=_NV_LAB)
        d.text((tx + 18, ty0 + (42 if liela else 34)), val, font=S.ietilpinat(d, val, "black", 54 if liela else 46, tw - 36), fill=S.BALTS)
        if sub:
            d.text((tx + 18, ty1 - (12 if liela else 9)), sub, font=S.ietilpinat(d, sub, "semi", 22 if liela else 19, tw - 36),
                   fill=_NV_LAB, anchor="ls")
    ie = str(k.get("apaksa") or "")
    if ie and liela:
        d.text((x0, ty1 + 52), ie, font=S.ietilpinat(d, ie, "semi", 32, W - 68), fill=(203, 213, 225, 255), anchor="ls")
    d.rounded_rectangle(box, radius=34, outline=prim + (230,), width=5)
    return im


def aina_fantasy_divi(t, c):
    """Īsā versija: 1–3 mazākas kartītes ar vārdiem vienā ainā (fantasy DROP; xG – otra grupa un varoņa grupas #3, #2);
    katra ieslīd, kad balss nosauc uzvārdu, pēc mirkļa – zīmogs (DROP / LUCKY / UNLUCKY / STEALING / COSTING)."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    _nv_dalinas(L, t)
    if c.get("_tv"):
        _nv_tablo_virs(L, N, t, c["_tv"])
    _fj_virsr(L, t, c["virsr"], 400, 120)
    K = c.get("kartites") or []
    n = len(K)
    veids_k = c.get("veids_k", "fantasy")
    W = 940
    if n >= 3:                                                        # trīs – kompaktas (bez iemesla rindas)
        H, gap_k = 290, 22
    else:
        H, gap_k = (430 if n == 2 else 470), 34
    ys = [500 + i * (H + gap_k) for i in range(n)] if n > 1 else [600]
    t_in, t_st = _nv_divi_laiki(c)
    kesa = c.setdefault("_kesa_divi", {})
    flash = None
    for i, k in enumerate(K):
        e = S.ease(min(1.0, max(0.0, (t - t_in[i]) / 0.38)))
        if e <= 0:
            continue
        if i not in kesa:
            kesa[i] = _nv_divi_karte(k, W, H, veids_k)
        im = kesa[i]
        x = 540 - im.width / 2 + (1 - e) * 260
        _nv_put(L, im, x, ys[i] + H / 2, 1.0, e, 0, "l")
        ks = (t - t_st[i]) / 0.24
        if ks > 0:                                                    # DROP / BENCH zīmogs (kā lielajai kartītei, mazāks)
            akc = tuple(k.get("akc") or S.SARKANS)
            txt = str(k.get("liels", "DROP"))
            st = Image.new("RGBA", (360, 120), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
            ds.rounded_rectangle([6, 6, 354, 114], radius=20, fill=(10, 14, 32, 215), outline=akc, width=9)
            ds.text((180, 60), txt, font=S.ietilpinat(ds, txt, "black", 74, 320), fill=akc, anchor="mm")
            _nv_put(N, st, 850, ys[i] + (118 if H >= 400 else 84), (0.88 if H >= 400 else 0.78) * (1 + 1.4 * (1 - S.ease(min(1.0, ks)))),
                    min(1.0, ks * 3), 8)
            if 1.0 <= ks < 2.0:
                flash = t_st[i]
    out = _nv_glow(N, 18, 1.0)
    out.alpha_composite(L)
    out.alpha_composite(N)
    if flash is not None:
        _nv_zibsnis(out, t, flash + 0.24, 0.08)
        out = _nv_kratit(out, t, flash + 0.24, 8)
    return out


# ---------------------------------------------------------------- īsā versija: 2. aina – waiver saraksts (fantasy) / nedēļas kalendārs (streameri)
ISS_DIENAS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
ISS_S2_DROP_LAB = "DROP CANDIDATES"
ISS_S2_LEGENDA = [(S.ZALS, "SOFT"), ((100, 116, 139), "AVERAGE"), (S.SARKANS, "TOUGH")]


def _iss_spel(c, hero=False):
    """Kartīte → viena rinda 2. ainai (saraksts / kalendārs)."""
    v = c.get("viz") or {}
    return {"kom": str(c.get("badge", "")), "poz": str(v.get("poz", "")), "rost": v.get("rost"), "v1": str(c.get("v1", "")),
            "v2": str(c.get("v2", "")), "nr": c.get("nr"), "gp": v.get("sp_nak"), "ned": list(v.get("ned") or [])[:7],
            "akc": tuple(c.get("akc") or S.ZALS), "drop": c.get("liels") in ("DROP", "BENCH"), "hero": hero}


def _iss_s2_aina(k2, pl, dl, hero, stream):
    """2. aina īsajai versijai: fantasy – saraksts kā lietotnē (+ / −), streameri – nedēļas kalendārs (MON–SUN)."""
    if not pl or not all((c.get("viz") or {}).get("ned") for c in pl + dl):
        return None
    sp = [_iss_spel(c, c is hero and not stream) for c in sorted(pl, key=lambda c: c.get("nr") or 9)] + \
         [_iss_spel(c) for c in sorted(dl, key=lambda c: c.get("nr") or 9)]
    nl = str((hero.get("viz") or {}).get("ned_lab", "")).split("·")[0].strip() or ("THIS WEEK" if stream else "NEXT WEEK")
    return {"tips": "fantasy_kalendars" if stream else "fantasy_saraksts", "ilgums": 3.5, "tag": k2.get("tag", ""),
            "_tv": k2.get("_tv"), "virsr": k2["virsr"], "apaksa": k2.get("apaksa", ""), "speletaji": sp, "ned_lab": nl}


def _iss_s2_laiki(c):
    """(rindu ieslīdēšana[], krāsu sākums, zaļo izcēlums) – rindas pēc kārtas (drop – ar pauzi), krāsas aizpildās
    pa dienām, zaļās spēles izceļas, kad balss saka "green" (bez balss – pēc krāsām). Viss paspēj līdz ainas beigām."""
    sp = c.get("speletaji") or []
    ilg, vardi = c.get("_ilg", c.get("ilgums", 3.5)), c.get("_vardi") or []
    t_in = [0.45 + 0.2 * i + (0.25 if p["drop"] else 0.0) for i, p in enumerate(sp)]
    t_kr = (t_in[-1] if t_in else 0.45) + 0.4
    lim = max(1.8, ilg - 0.55)
    if t_kr + 0.75 > lim:                                             # saspiest (īss audio / bez balss)
        k = max(0.3, (lim - 0.75 - 0.45) / max(0.01, t_kr - 0.45))
        t_in = [0.45 + (x - 0.45) * k for x in t_in]
        t_kr = 0.45 + (t_kr - 0.45) * k
    tg = _nv_vards_laiks(vardi, "green")
    t_zal = tg if tg is not None else t_kr + 1.0
    t_zal = min(max(t_zal, t_kr + 0.7), lim - 0.2)
    return t_in, t_kr, t_zal


def _iss_s2_augsa(L, N, t, c):
    _nv_dalinas(L, t)
    if c.get("_tv"):
        _nv_tablo_virs(L, N, t, c["_tv"])
    _fj_virsr(L, t, c["virsr"], 400, 130)
    a = S.ease(min(1.0, max(0.0, (t - 0.5) / 0.3)))
    if c.get("apaksa") and a > 0:
        d = ImageDraw.Draw(L)
        S.teksts_c(d, 488, c["apaksa"], S.ietilpinat(d, c["apaksa"], "semi", 34, 900), _NV_LAB + (int(255 * a),))


def _iss_pct(x):
    return "–" if not isinstance(x, (int, float)) else (f"{x:.0f}%" if x >= 1 else "<1%")


def _iss_tm(kr):
    return S.MELNS if tuple(kr) in (S.ZALS, S.DZELTENS) else S.BALTS


def _iss_zal_puls(t, t_zal):
    """0…1…0 – zaļo spēļu izcēlums (0,8 s)."""
    k = (t - t_zal) / 0.8
    return math.sin(math.pi * k) if 0 < k < 1 else 0.0


def _iss_punkts(d, x, y, s, n_, a=255):
    """Viena diena: zaļš / pelēks / sarkans kvadrātiņš ar spēli, tukšs – kontūra, pagājusi – blāvs."""
    if n_.get("o"):
        kr = tuple(n_.get("kr") or (100, 116, 139))
        d.rounded_rectangle([x, y, x + s, y + s], radius=s // 4, fill=kr + (int(a * (0.4 if n_.get("pag") else 1.0)),))
    elif n_.get("pag"):
        d.rounded_rectangle([x, y, x + s, y + s], radius=s // 4, fill=(32, 40, 62, a))
    else:
        d.rounded_rectangle([x, y, x + s, y + s], radius=s // 4, outline=(70, 80, 108, a), width=2)


# --- B: waiver saraksts (fantasy)
def _iss_s2_izkartojums(c):
    sp = c.get("speletaji") or []
    dr = any(p["drop"] for p in sp)
    k, h, g, y = (1.0, 142, 12, 560) if dr else (1.18, 176, 22, 600)
    ys, yl = [], None
    y += 46
    for i, p in enumerate(sp):
        if p["drop"] and yl is None:
            yl = y + 12 - g
            y += 58 - g
        ys.append(y)
        y += h + g
    return k, h, ys, yl


def _iss_rinda_pamats(p, h, k):
    """Saraksta rindas nemainīgā daļa (fons, komandas svītra, vārds, pozīcija, tukšas dienas) → (attēls, punktu x, y, izm.)."""
    W = 960
    im = Image.new("RGBA", (W, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    prim, _ = kom_krasas(p["kom"])
    d.rounded_rectangle([0, 0, W - 1, h - 1], radius=26, fill=(14, 19, 42, 245))
    d.rounded_rectangle([0, 0, 16, h - 1], radius=8, fill=prim)
    r = int(40 * k)
    xn = 36 + 2 * r + 30
    fn = int(54 * k)
    nm = (p["v1"][:1] + ". " if p["v1"] else "") + p["v2"].upper()
    if p["hero"]:                                                     # noslēpuma #1 – vārds izpludināts
        ti = _nv_timg(nm, S.fonts("black", fn), S.BALTS)
        b = Image.new("RGBA", (ti.width + 60, ti.height + 60), (0, 0, 0, 0)); b.alpha_composite(ti, (30, 30))
        im.alpha_composite(b.filter(ImageFilter.GaussianBlur(12)), (xn - 30, int(14 * k) - 30))
    else:
        d.text((xn, 16 * k), nm, font=S.ietilpinat(d, nm, "black", fn, W - 230 - xn), fill=S.BALTS)
    yl = h - 22 * k
    d.text((xn, yl), f"{p['poz']} · {p['kom']}", font=S.fonts("semi", int(28 * k)), fill=_NV_LAB, anchor="ls")
    s_, g_ = int(26 * k), int(7 * k)
    xd, yd = int(xn + 160 * k), int(yl - s_ + 2)
    for i in range(7):
        _iss_punkts(d, xd + i * (s_ + g_), yd, s_, {})
    d.text((xd + 7 * (s_ + g_) + 10, yl), f"{p['gp']} GP" if p.get("gp") is not None else "", font=S.fonts("black", int(28 * k)),
           fill=S.BALTS, anchor="ls")
    d.text((W - 28, yl), "ROSTERED", font=S.fonts("semi", int(20 * k)), fill=_NV_LAB, anchor="rs")
    return im, (xd, yd, s_, g_, xn, r)


def aina_fantasy_saraksts(t, c):
    """Īsā fantasy 2. aina: brīvo spēlētāju saraksts kā lietotnē – rindas ieslīd, "+" (drop – "−") nospiežas,
    rostered % saskaitās, nedēļas dienas iekrāsojas, zaļās spēles izceļas, kad balss saka "green"."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    _iss_s2_augsa(L, N, t, c)
    sp = c.get("speletaji") or []
    k, h, ys, yl = _iss_s2_izkartojums(c)
    t_in, t_kr, t_zal = _iss_s2_laiki(c)
    d = ImageDraw.Draw(L); dn = ImageDraw.Draw(N)
    a0 = S.ease(min(1.0, max(0.0, (t - 0.4) / 0.3)))
    if a0 > 0:
        akc = sp[0]["akc"] if sp else S.ZALS
        d.text((60, ys[0] - 46 if ys else 606), "FREE AGENTS  ·  ESPN", font=S.fonts("black", 30), fill=akc + (int(255 * a0),))
        d.text((1020, ys[0] - 44 if ys else 606), c.get("ned_lab", "NEXT WEEK"), font=S.fonts("black", 26), fill=_NV_LAB + (int(255 * a0),), anchor="ra")
    if yl is not None:
        ad_ = S.ease(min(1.0, max(0.0, (t - (min(t_in[i] for i, p in enumerate(sp) if p["drop"]) - 0.15)) / 0.3)))
        if ad_ > 0:
            d.text((60, yl), ISS_S2_DROP_LAB, font=S.fonts("black", 30), fill=S.SARKANS + (int(255 * ad_),))
    kesa = c.setdefault("_kesa_s2", {})
    puls = _iss_zal_puls(t, t_zal)
    for i, p in enumerate(sp):
        e = S.ease(min(1.0, max(0.0, (t - t_in[i]) / 0.4)))
        if e <= 0:
            continue
        if i not in kesa:
            kesa[i] = _iss_rinda_pamats(p, h, k)
        base, (xd, yd, s_, g_, xn, r) = kesa[i]
        im = base.copy(); di = ImageDraw.Draw(im)
        kr = S.SARKANS if p["drop"] else p["akc"]
        # poga: "+" / "−" – nospiežas 0,3 s pēc ieslīdēšanas
        kp = (t - t_in[i] - 0.3) / 0.22
        sc = 1 - 0.16 * math.sin(math.pi * kp) if 0 < kp < 1 else 1.0
        cx, cy, rr = 36 + r, h / 2, r * sc
        di.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=kr)
        di.line([cx - rr * 0.45, cy, cx + rr * 0.45, cy], fill=_iss_tm(kr), width=max(3, int(9 * k * sc)))
        if not p["drop"]:
            di.line([cx, cy - rr * 0.45, cx, cy + rr * 0.45], fill=_iss_tm(kr), width=max(3, int(9 * k * sc)))
        # rostered % – saskaitās
        kc = S.ease(min(1.0, max(0.0, (t - t_in[i]) / 0.6)))
        txt = _iss_pct(p["rost"])
        di.text((960 - 28, 18 * k), skaitit(txt, kc) if txt not in ("–", "<1%") else txt, font=S.fonts("black", int(58 * k)),
                fill=S.BALTS if not p["drop"] else (252, 165, 165), anchor="ra")
        # nedēļas dienas – iekrāsojas pa vienai
        for j, n_ in enumerate(p["ned"]):
            kd = (t - t_kr - 0.06 * j - 0.03 * i) / 0.2
            if kd <= 0:
                continue
            x = xd + j * (s_ + g_)
            zal = bool(n_.get("o")) and tuple(n_.get("kr") or ()) == tuple(S.ZALS) and not n_.get("pag")
            ps = (1 + 0.35 * (1 - ease_back(min(1.0, kd), 2.0))) * (1 + 0.35 * puls * zal)
            if ps != 1:
                q = Image.new("RGBA", (s_ * 2, s_ * 2), (0, 0, 0, 0))
                _iss_punkts(ImageDraw.Draw(q), s_ // 2, s_ // 2, s_, n_)
                q = q.resize((max(2, int(q.width * ps)), max(2, int(q.height * ps))), Image.BICUBIC)
                im.alpha_composite(q, (int(x + s_ / 2 - q.width / 2), int(yd + s_ / 2 - q.height / 2)))
            else:
                _iss_punkts(di, x, yd, s_, n_)
        xo = (1 - e) * 300
        X0 = 60 + xo
        _nv_put(L, im, X0, ys[i] + h / 2, 1.0, e, 0, "l")
        if kp > 0:                                                    # pogas spīdums nospiešanas brīdī
            ag = max(0.25, 1 - max(0.0, kp - 1) / 2.5)
            dn.ellipse([X0 + cx - r - 6, ys[i] + cy - r - 6, X0 + cx + r + 6, ys[i] + cy + r + 6], outline=kr + (int(220 * ag),), width=7)
        if puls > 0:                                                  # zaļās spēles – spīdums
            for j, n_ in enumerate(p["ned"]):
                if n_.get("o") and tuple(n_.get("kr") or ()) == tuple(S.ZALS) and not n_.get("pag"):
                    x = X0 + xd + j * (s_ + g_)
                    dn.rounded_rectangle([x - 8, ys[i] + yd - 8, x + s_ + 8, ys[i] + yd + s_ + 8], radius=10, fill=S.ZALS + (int(240 * puls),))
    out = _nv_glow(N, 18, 1.1)
    out.alpha_composite(L)
    return out


# --- D: nedēļas kalendārs (streameri)
def _iss_kal_izkartojums(c):
    sp = c.get("speletaji") or []
    dr = any(p["drop"] for p in sp)
    XL, LW = 50, 258
    XC, cg = XL + LW + 8, 8
    cw = (1030 - XC - 6 * cg) / 7
    rh, rg, y = (124, 12, 562) if dr else (160, 18, 670)
    yh = y
    y += 44
    ys, yl = [], None
    for p in sp:
        if p["drop"] and yl is None:
            yl = y + 8 - rg
            y += 52 - rg
        ys.append(y)
        y += rh + rg
    return XL, LW, XC, cg, cw, rh, yh, ys, yl, y + 16 - rg


def _iss_kal_etikete(p, LW, rh):
    """Kalendāra rindas kreisā daļa: komanda, pozīcija, vārds (noslēpuma #1 – ???)."""
    im = Image.new("RGBA", (LW, rh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    prim, _ = kom_krasas(p["kom"])
    ak = S.SARKANS if p["drop"] else p["akc"]
    d.rounded_rectangle([0, 0, LW - 1, rh - 1], radius=20, fill=(14, 19, 42, 245), outline=ak, width=4)
    f1 = S.fonts("black", 30)
    tw = d.textlength(p["kom"], font=f1) + 24
    d.rounded_rectangle([14, 14, 14 + tw, 58], radius=12, fill=prim)
    d.text((14 + tw / 2, 36), p["kom"], font=f1, fill=S.MELNS if sum(prim) > 450 else S.BALTS, anchor="mm")
    d.text((26 + tw, 36), p["poz"], font=f1, fill=S.BALTS, anchor="lm")
    nm = "???" if p["hero"] else p["v2"].upper()
    pre = f"#{p['nr']} " if (p.get("nr") and not p["drop"]) else ""    # vieta sarakstā (#1 – augšā)
    f_ = S.ietilpinat(d, pre + nm, "black", 30, LW - 32)
    x_ = 16
    if pre:
        d.text((x_, rh - 18), pre, font=f_, fill=S.DZELTENS, anchor="ls")
        x_ += d.textlength(pre, font=f_)
    d.text((x_, rh - 18), nm, font=f_, fill=S.DZELTENS if p["hero"] else (226, 232, 240), anchor="ls")
    return im


def _iss_kal_suna(n_, cw, rh):
    """Viena kalendāra diena: pretinieks krāsā (zaļš – vāja aizsardzība, pelēks – vidēja, sarkans – stipra)."""
    im = Image.new("RGBA", (int(cw), rh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    box = [0, 0, int(cw) - 1, rh - 1]
    if n_.get("o"):
        kr = tuple(n_.get("kr") or (100, 116, 139))
        pag = bool(n_.get("pag"))
        d.rounded_rectangle(box, radius=18, fill=kr + ((95 if pag else 255),))
        o = str(n_["o"]); at = o.startswith("@")
        fc = (_iss_tm(kr) if kr != (100, 116, 139) else S.BALTS) if not pag else (190, 198, 212)
        d.text((cw / 2, rh / 2 - (12 if at else 0)), o.lstrip("@"), font=S.ietilpinat(d, o.lstrip("@"), "black", 32, cw - 12), fill=fc, anchor="mm")
        if at:
            d.text((cw / 2, rh / 2 + 26), "AWAY", font=S.fonts("semi", 17), fill=fc, anchor="mm")
    elif n_.get("pag"):
        d.rounded_rectangle(box, radius=18, fill=(22, 28, 50, 230))
        d.line([cw / 2 - 18, rh / 2, cw / 2 + 18, rh / 2], fill=(70, 80, 105), width=4)
    else:
        d.rounded_rectangle(box, radius=18, outline=(48, 58, 85), width=3)
    return im


def aina_fantasy_kalendars(t, c):
    """Īsā streameru 2. aina: nedēļas kalendārs – rindas (komanda, pozīcija, vārds) ieslīd, dienas iekrāsojas
    no pirmdienas līdz svētdienai (GP skaitās), zaļās spēles izceļas, kad balss saka "green"; apakšā – leģenda."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    _iss_s2_augsa(L, N, t, c)
    sp = c.get("speletaji") or []
    XL, LW, XC, cg, cw, rh, yh, ys, yl, yleg = _iss_kal_izkartojums(c)
    t_in, t_kr, t_zal = _iss_s2_laiki(c)
    d = ImageDraw.Draw(L); dn = ImageDraw.Draw(N)
    a0 = S.ease(min(1.0, max(0.0, (t - 0.4) / 0.3)))
    if a0 > 0:
        for j, dn_ in enumerate(ISS_DIENAS):
            d.text((XC + j * (cw + cg) + cw / 2, yh), dn_, font=S.fonts("black", 26), fill=_NV_LAB + (int(255 * a0),), anchor="ma")
    if yl is not None:
        ad_ = S.ease(min(1.0, max(0.0, (t - (min(t_in[i] for i, p in enumerate(sp) if p["drop"]) - 0.15)) / 0.3)))
        if ad_ > 0:
            d.text((XL, yl), ISS_S2_DROP_LAB, font=S.fonts("black", 30), fill=S.SARKANS + (int(255 * ad_),))
    kesa = c.setdefault("_kesa_kal", {})
    puls = _iss_zal_puls(t, t_zal)
    if ys:                                                            # skeneris – gaiša kolonna, kas iet pāri dienām
        for j in range(7):
            ah = max(0.0, 1 - abs(t - (t_kr + 0.1 * j + 0.08)) / 0.16)
            if ah > 0:
                x = XC + j * (cw + cg)
                d.rounded_rectangle([x - 4, ys[0] - 8, x + cw + 4, ys[-1] + rh + 8], radius=22, fill=(255, 255, 255, int(38 * ah)))
    for i, p in enumerate(sp):
        e = S.ease(min(1.0, max(0.0, (t - t_in[i]) / 0.4)))
        if e <= 0:
            continue
        y = ys[i]
        if ("et", i) not in kesa:
            kesa[("et", i)] = _iss_kal_etikete(p, LW, rh)
        X = XL - (1 - e) * 220
        _nv_put(L, kesa[("et", i)], X, y + rh / 2, 1.0, e, 0, "l")
        gp_n = 0
        for j, n_ in enumerate(p["ned"]):
            x = XC + j * (cw + cg)
            kd = (t - t_kr - 0.1 * j - 0.025 * i) / 0.25
            if kd <= 0:                                               # vēl neatklāta – tukša kontūra
                d.rounded_rectangle([x, y, x + cw, y + rh], radius=18, outline=(48, 58, 85, int(255 * e)), width=3)
                continue
            if n_.get("o") and not n_.get("pag"):
                gp_n += 1
            zal = bool(n_.get("o")) and tuple(n_.get("kr") or ()) == tuple(S.ZALS) and not n_.get("pag")
            if ("su", i, j) not in kesa:
                kesa[("su", i, j)] = _iss_kal_suna(n_, cw, rh)
            sc = (0.7 + 0.3 * ease_back(min(1.0, kd), 2.2)) * (1 + 0.07 * puls * zal)
            _nv_put(L, kesa[("su", i, j)], x + cw / 2, y + rh / 2, sc, min(1.0, kd * 2.5))
            if zal and (puls > 0 or 0 < kd < 1.6):
                ag = max(puls, 0.55 * max(0.0, 1 - kd / 1.6))
                dn.rounded_rectangle([x - 2, y - 2, x + cw + 2, y + rh + 2], radius=20, fill=S.ZALS + (int(200 * ag),))
        if t > t_kr:                                                  # GP skaitās līdzi dienām
            gpv = p.get("gp") if (t > t_kr + 0.85 and p.get("gp") is not None) else gp_n
            ak = S.SARKANS if p["drop"] else p["akc"]
            d.text((X + LW - 16, y + 36), f"{gpv} GP", font=S.fonts("black", 28), fill=ak + (int(255 * e),), anchor="rm")
    al = S.ease(min(1.0, max(0.0, (t - t_kr - 0.75) / 0.35)))
    if al > 0:                                                        # leģenda
        f = S.fonts("black", 28)
        tot = sum(44 + d.textlength(t_, font=f) for _, t_ in ISS_S2_LEGENDA) + 56 * (len(ISS_S2_LEGENDA) - 1)
        x = 540 - tot / 2
        for kr, t_ in ISS_S2_LEGENDA:
            d.rounded_rectangle([x, yleg, x + 32, yleg + 32], radius=8, fill=tuple(kr) + (int(255 * al),))
            d.text((x + 44, yleg + 16), t_, font=f, fill=S.BALTS + (int(255 * al),), anchor="lm")
            x += 44 + d.textlength(t_, font=f) + 56
    out = _nv_glow(N, 18, 1.1)
    out.alpha_composite(L)
    return out


# ---------------------------------------------------------------- fantasy atskats: 2. aina – rezultātu saraksts (kopš 10.11.2026)
FA_S2_IKONA = {"HIT": "v", "GOOD CALL": "v", "MISS": "x", "BAD CALL": "x", "DIDN'T PLAY": "x", "EVEN": "="}


def _fa_s2_aina(k2, kar, s):
    """Fantasy atskata 2. aina: augšā LAST WEEK (✓/✗) un SEASON (trāpīts / kopā, %), zem tam visi ieteiktie ar vārdiem –
    punkti katrā nedēļas dienā, punkti pret tipisko spēlētāju un rezultāts (HIT / MISS / EVEN / GOOD CALL / BAD CALL)."""
    if not kar or not all((c.get("viz") or {}).get("ned") for c in kar):
        return None
    m_ = re.search(r"SEASON:\s*(\d+)\s*/\s*(\d+)", " ".join(str(x[0]) for x in ((s.get("outro") or {}).get("rindas") or [])))
    rind = []
    for c in kar:
        v = c["viz"]
        rind.append({"kom": str(c.get("badge", "")), "poz": str(v.get("poz", "")), "v1": str(c.get("v1", "")),
                     "v2": str(c.get("v2", "")), "grupa": v.get("grupa", "add"), "pts": int(v.get("pts") or 0),
                     "med": float(v.get("med") or 0), "verd": str(c.get("liels") or v.get("verd") or ""),
                     "akc": tuple(c.get("akc") or (100, 116, 139)), "ned": list(v.get("ned") or [])[:7]})
    return {"tips": "fantasy_ats_saraksts", "ilgums": k2.get("ilgums", 6.0), "tag": k2.get("tag", ""), "_tv": k2.get("_tv"),
            "virsr": k2["virsr"], "apaksa": k2.get("apaksa", ""), "rindas": rind,
            "rek": tuple(s["atskats_rek"]) if s.get("atskats_rek") else None,
            "sezona": (int(m_.group(1)), int(m_.group(2))) if m_ else None,
            "_ievads_no": len(str(s.get("aki_runa") or "").split())}


def _fa_s2_izk(c):
    R = c.get("rindas") or []
    n = max(1, len(R))
    ir_t = bool(c.get("rek") or c.get("sezona"))
    yt = 548
    y = yt + 142 if ir_t else 556
    y0 = y + 46
    dr = any(r["grupa"] == "drop" for r in R)
    g = 10
    h = int(min(140, (1432 - y0 - (54 if dr else 0) - g * (n - 1)) / n))
    ys, yl, yy = [], None, y0
    for r in R:
        if r["grupa"] == "drop" and yl is None:
            yl = yy + 6
            yy += 54
        ys.append(yy)
        yy += h + g
    return ir_t, yt, y, h, ys, yl


def _fa_s2_laiki(c):
    """(tablo sākums, rindu ieslīdēšana[], zīmogi[]) – rezultāts uzreiz (balss: "0 for 4 last week"), rindas – kad balss
    sāk ievadu ("Time to check last week's calls"), katrai rindai pēc mirkļa – rezultāta zīmogs. Viss paspēj līdz beigām."""
    R = c.get("rindas") or []
    ilg, vardi = c.get("_ilg", c.get("ilgums", 6.0)), c.get("_vardi") or []
    t_t = 0.45
    i0 = int(c.get("_ievads_no") or 0)
    t_r = vardi[i0][0] - 0.15 if (i0 and len(vardi) > i0) else 1.4
    lim = max(2.0, ilg - 0.5)
    t_r = min(max(1.2, t_r), lim - 0.95 - 0.24 * max(0, len(R) - 1))
    t_r = max(0.8, t_r)
    t_in, p_ = [], False
    for i, r in enumerate(R):
        if r["grupa"] == "drop" and not p_:
            p_ = True
        t_in.append(t_r + 0.24 * i + (0.2 if p_ else 0.0))
    if t_in and t_in[-1] + 0.95 > lim:                                # saspiest
        k = max(0.3, (lim - 0.95 - t_in[0]) / max(0.01, t_in[-1] - t_in[0]))
        t_in = [t_in[0] + (x - t_in[0]) * k for x in t_in]
    return t_t, t_in, [x + 0.6 for x in t_in]


def _fa_ikona(d, cx, cy, r, ik, kr):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=kr)
    w = max(4, int(r * 0.22))
    if ik == "v":
        d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.36), (cx + r * 0.48, cy - r * 0.34)], fill=S.BALTS, width=w, joint="curve")
    elif ik == "x":
        d.line([(cx - r * 0.38, cy - r * 0.38), (cx + r * 0.38, cy + r * 0.38)], fill=S.BALTS, width=w)
        d.line([(cx + r * 0.38, cy - r * 0.38), (cx - r * 0.38, cy + r * 0.38)], fill=S.BALTS, width=w)
    else:
        d.line([(cx - r * 0.4, cy - r * 0.18), (cx + r * 0.4, cy - r * 0.18)], fill=S.BALTS, width=w)
        d.line([(cx - r * 0.4, cy + r * 0.18), (cx + r * 0.4, cy + r * 0.18)], fill=S.BALTS, width=w)


def _fa_diena(d, x, y, s_, n_, a=255):
    """Viena nedēļas diena: punkti tajā spēlē (zaļš – ≥1, pelēks – 0), bez spēles – kontūra."""
    p = n_.get("p")
    if n_.get("o") and p is not None:
        kr = S.ZALS if p > 0 else (100, 116, 139)
        d.rounded_rectangle([x, y, x + s_, y + s_], radius=max(4, s_ // 4), fill=kr + (a,))
        d.text((x + s_ / 2, y + s_ / 2 + 1), str(p), font=S.fonts("black", int(s_ * 0.62)), fill=(S.MELNS if p > 0 else S.BALTS) + (a,), anchor="mm")
    else:
        d.rounded_rectangle([x, y, x + s_, y + s_], radius=max(4, s_ // 4), outline=(70, 80, 108, a), width=2)


def _fa_rinda_pamats(r, h):
    W = 960
    im = Image.new("RGBA", (W, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    prim, _ = kom_krasas(r["kom"])
    d.rounded_rectangle([0, 0, W - 1, h - 1], radius=24, fill=(14, 19, 42, 245))
    d.rounded_rectangle([0, 0, 16, h - 1], radius=8, fill=prim)
    rr = int(min(36, h * 0.3))
    xn = 36 + 2 * rr + 24
    nm = (r["v1"][:1] + ". " if r["v1"] else "") + r["v2"].upper()
    d.text((xn, h * 0.12), nm, font=S.ietilpinat(d, nm, "black", int(min(50, h * 0.4)), W - 220 - xn), fill=S.BALTS)
    yl = h - h * 0.15
    f2 = S.fonts("semi", int(min(26, h * 0.22)))
    d.text((xn, yl), f"{r['poz']} · {r['kom']}", font=f2, fill=_NV_LAB, anchor="ls")
    s_ = int(min(30, h * 0.25)); g_ = max(4, s_ // 5)
    xd, yd = int(xn + 140), int(yl - s_ + 3)
    for j in range(7):
        _fa_diena(d, xd + j * (s_ + g_), yd, s_, {})
    d.text((W - 28, yl), f"TYPICAL {r['med']:.0f}", font=S.fonts("semi", int(min(22, h * 0.19))), fill=_NV_LAB, anchor="rs")
    return im, (rr, xn, xd, yd, s_, g_, yl)


def _fa_tablo(t, c, yt, kesa):
    """Augšas flīzes: LAST WEEK (✓/✗ rūtiņas + 1/4) un SEASON (H/T, % josla)."""
    t_t = _fa_s2_laiki(c)[0]
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    F = S.fonts
    for i_, (x0, x1) in enumerate(((60, 530), (550, 1020))):
        e = S.ease(min(1.0, max(0.0, (t - t_t - 0.2 * i_) / 0.35)))
        if e <= 0:
            continue
        a = int(255 * e)
        dy = (1 - e) * 40
        y0, y1 = yt + dy, yt + 120 + dy
        if i_ == 0 and c.get("rek"):
            tr, n = c["rek"]
            kr = S.ZALS if n and tr / n >= 0.5 else S.SARKANS
            d.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(245 * e),), outline=kr + (a,), width=4)
            d.text((x0 + 24, y0 + 16), "LAST WEEK", font=F("black", 26), fill=_NV_LAB + (a,))
            d.text((x1 - 24, y0 + 60), f"{tr}/{n}", font=F("black", 70), fill=S.BALTS + (a,), anchor="rm")
            n_ = min(n, 6)
            for j in range(n_):
                kj = (t - t_t - 0.2 - 0.13 * j) / 0.2
                if kj <= 0:
                    continue
                sc = 1 + 0.4 * (1 - ease_back(min(1.0, kj), 2.0))
                q = 40 * sc
                cx, cy = x0 + 44 + j * 50, y0 + 84
                ok = j < tr
                d.rounded_rectangle([cx - q / 2, cy - q / 2, cx + q / 2, cy + q / 2], radius=10, fill=(S.ZALS if ok else S.SARKANS) + (a,))
                if ok:
                    d.line([(cx - q * 0.25, cy), (cx - q * 0.05, cy + q * 0.2), (cx + q * 0.28, cy - q * 0.22)], fill=S.BALTS + (a,), width=5)
                else:
                    d.line([(cx - q * 0.2, cy - q * 0.2), (cx + q * 0.2, cy + q * 0.2)], fill=S.BALTS + (a,), width=5)
                    d.line([(cx + q * 0.2, cy - q * 0.2), (cx - q * 0.2, cy + q * 0.2)], fill=S.BALTS + (a,), width=5)
        elif i_ == 1 and c.get("sezona"):
            H, T = c["sezona"]
            pr = H / T if T else 0.0
            kr = S.ZALS if pr >= 0.5 else S.SARKANS
            d.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=_NV_TILE + (int(245 * e),), outline=(255, 255, 255, int(70 * e)), width=3)
            fl_ = F("black", 26)
            d.text((x0 + 24, y0 + 16), "SEASON", font=fl_, fill=_NV_LAB + (a,))
            kb = S.ease(min(1.0, max(0.0, (t - t_t - 0.45) / 0.7)))
            d.text((x0 + 24 + d.textlength("SEASON", font=fl_) + 14, y0 + 16), f"{pr * 100 * kb:.0f}%", font=fl_, fill=kr + (a,))
            d.text((x1 - 24, y0 + 60), f"{H}/{T}", font=F("black", 70), fill=S.BALTS + (a,), anchor="rm")
            bx0, bx1, by = x0 + 24, x0 + 200, y0 + 78
            d.rounded_rectangle([bx0, by, bx1, by + 14], radius=7, fill=(255, 255, 255, int(40 * e)))
            if pr > 0 and kb > 0:
                d.rounded_rectangle([bx0, by, bx0 + max(14, (bx1 - bx0) * pr * kb), by + 14], radius=7, fill=kr + (a,))
    return L


def aina_fantasy_ats_saraksts(t, c):
    """Fantasy atskata 2. aina: LAST WEEK + SEASON augšā, zem tam visi ieteiktie (WE SAID ADD / WE SAID DROP) ar vārdiem –
    rindas ieslīd, nedēļas dienas iekrāsojas (punkti spēlē), punkti saskaitās, rezultāta zīmogs + ✓/✗."""
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    N = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    _iss_s2_augsa(L, N, t, c)
    R = c.get("rindas") or []
    ir_t, yt, ylab, h, ys, yl = _fa_s2_izk(c)
    t_t, t_in, t_st = _fa_s2_laiki(c)
    kesa = c.setdefault("_kesa_fa", {})
    if ir_t:
        L.alpha_composite(_fa_tablo(t, c, yt, kesa))
    d = ImageDraw.Draw(L); dn = ImageDraw.Draw(N)
    if t_in:
        a0 = S.ease(min(1.0, max(0.0, (t - t_in[0] + 0.15) / 0.3)))
        if a0 > 0 and any(r["grupa"] != "drop" for r in R):
            d.text((60, ylab), "WE SAID ADD", font=S.fonts("black", 30), fill=S.ZALS + (int(255 * a0),))
            d.text((1020, ylab + 2), "PTS THAT WEEK", font=S.fonts("black", 26), fill=_NV_LAB + (int(255 * a0),), anchor="ra")
        if yl is not None:
            i_d = next(i for i, r in enumerate(R) if r["grupa"] == "drop")
            ad_ = S.ease(min(1.0, max(0.0, (t - t_in[i_d] + 0.15) / 0.3)))
            if ad_ > 0:
                d.text((60, yl), "WE SAID DROP", font=S.fonts("black", 30), fill=S.SARKANS + (int(255 * ad_),))
    for i, r in enumerate(R):
        e = S.ease(min(1.0, max(0.0, (t - t_in[i]) / 0.4)))
        if e <= 0:
            continue
        if i not in kesa:
            kesa[i] = _fa_rinda_pamats(r, h)
        base, (rr, xn, xd, yd, s_, g_, yl_) = kesa[i]
        im = base.copy(); di = ImageDraw.Draw(im)
        ik = FA_S2_IKONA.get(r["verd"], "=")
        kr = r["akc"]
        ks = (t - t_st[i]) / 0.25                                     # zīmogs: ✓/✗ + rezultāts
        if ks > 0:
            sc = 1 + 0.5 * (1 - ease_back(min(1.0, ks), 2.0))
            _fa_ikona(di, 36 + rr, h / 2, rr * sc, ik, kr)
        else:
            di.ellipse([36, h / 2 - rr, 36 + 2 * rr, h / 2 + rr], outline=(70, 80, 108), width=3)
        for j, n_ in enumerate(r["ned"]):                             # dienas – punkti katrā spēlē
            kd = (t - t_in[i] - 0.2 - 0.05 * j) / 0.18
            if kd > 0 and n_.get("o"):
                _fa_diena(di, xd + j * (s_ + g_), yd, s_, n_, int(255 * min(1.0, kd)))
        kc = S.ease(min(1.0, max(0.0, (t - t_in[i] - 0.15) / 0.5)))
        p_ = round(r["pts"] * kc)
        di.text((960 - 28, h * 0.1), f"{p_} PT{'' if p_ == 1 else 'S'}", font=S.fonts("black", int(min(50, h * 0.4))),
                fill=S.BALTS, anchor="ra")
        if ks > 0:
            txt = r["verd"]
            f = S.fonts("black", int(min(24, h * 0.2)))
            tw = di.textlength(txt, font=f) + 26
            px = xd + 7 * (s_ + g_) + 14
            ph = int(min(38, h * 0.3))
            st = Image.new("RGBA", (int(tw) + 8, ph + 8), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
            ds.rounded_rectangle([4, 4, 4 + tw, 4 + ph], radius=ph // 2, fill=kr)
            ds.text((4 + tw / 2, 4 + ph / 2), txt, font=f, fill=S.MELNS if kr == tuple(S.ZALS) else S.BALTS, anchor="mm")
            sc = 1 + 0.6 * (1 - ease_back(min(1.0, ks), 2.0))
            _nv_put(im, st, px + st.width / 2, yd + s_ / 2, sc, min(1.0, ks * 3))
        X0 = 60 + (1 - e) * 300
        _nv_put(L, im, X0, ys[i] + h / 2, 1.0, e, 0, "l")
        if 0 < ks < 3:                                                # zīmoga spīdums
            ag = max(0.0, 1 - ks / 3)
            dn.ellipse([X0 + 36 - 6, ys[i] + h / 2 - rr - 6, X0 + 36 + 2 * rr + 6, ys[i] + h / 2 + rr + 6], fill=kr + (int(200 * ag),))
    out = _nv_glow(N, 18, 1.1)
    out.alpha_composite(L)
    return out


def _iss_fantasy(s, veids):
    kk, rr = s["kartes"], s["runa"]
    if len(rr) != len(kk) + 2:
        return None
    stream = veids == "streameri"
    k2 = next((c for c in kk if c.get("tips") == "fantasy_kartis"), None)
    adds = [c for c in kk if c.get("tips") == "fantasy" and c.get("liels") in ("ADD", "STREAM")]
    drops = [c for c in kk if c.get("tips") == "fantasy" and c.get("liels") in ("DROP", "BENCH")]
    if not k2 or not adds:
        return None
    hero = next((c for c in adds if c.get("nr") == 1), adds[-1])
    citi = [c for c in adds if c is not hero]
    nsl = (s.get("intro") or {}).get("noslepums") or {}
    mr = re.search(r"UNDER (\d+)%", str(k2.get("apaksa", "")))
    rost = f"under {mr.group(1)}% rostered" if mr else "barely rostered"
    n_ = _VARDIEM.get(len(adds), str(len(adds)))
    a2 = _iss_s2_aina(k2, adds, [] if stream else drops, hero, stream)   # fantasy – saraksts, streameri – kalendārs
    kartes = [a2 or dict(k2, ilgums=3.5)]
    runa = [rr[0], S.reta_frase(ISS_FAN_IEVADS[stream], veids=veids, n=2).format(N=n_.capitalize(), n=n_, rost=rost)]
    for c in citi:
        kartes.append(c)
        runa.append(_iss_fan_teik(c, stream))
    if drops and not stream:
        d_aina, d_teik = _iss_drop(drops, k2)
        kartes.append(d_aina)
        runa.append(d_teik)
    kartes.append(hero)
    runa.append((str(nsl.get("atkl_fr") or "") + " " + _iss_fan_teik(hero, stream)).strip())
    r_ = (hero.get("viz") or {}).get("rost")
    pirms = ""
    if isinstance(r_, (int, float)):
        pirms = (S.reta_frase(ISS_FAN_ROST, veids=veids, n=1).format(r=f"{r_:.0f}", a=f"{100 - r_:.0f}") if r_ >= 1
                 else "Almost nobody has him.")
    runa.append(_iss_cilpa(s, veids, pirms))
    return kartes, runa


def _xg_skaitli(c):
    b = c.get("bars") or []
    return (float(b[0][1]), float(b[1][1])) if len(b) >= 2 else (None, None)


def _iss_xg_grupa(cards, veids, k2, virsr, apaksa):
    kartis = [{"kom": str(c.get("badge", "")), "poz": (c.get("viz") or {}).get("poz", ""), "akc": tuple(c["akc"]),
               "liels": c["viz"]["kart"]["liels"], "maz": c["viz"]["kart"]["maz"], "lab": c["viz"]["zimogs"]} for c in cards]
    return {"tips": "fantasy_kartis", "ilgums": 3.2, "tag": k2.get("tag", ""), "_tv": k2.get("_tv"), "virsr": virsr,
            "apaksa": apaksa, "kartis": kartis, "n_pick": len(kartis), "rek": None}


def _iss_xg(s, veids):
    kk, rr = s["kartes"], s["runa"]
    if len(rr) != len(kk) + 2 or len(kk) < 3 or kk[0].get("tips") not in ("xg_karte", "fantasy_kartis"):
        return None
    k2, cards = kk[0], kk[1:]
    hero = cards[-1]
    hg = hero["viz"]["grupa"]
    other = [c for c in cards if c["viz"]["grupa"] != hg]
    mine = [c for c in cards[:-1] if c["viz"]["grupa"] == hg]
    m_ = re.search(r"([A-Z][a-z]{2} \d+)", str(s.get("periods", "")))
    karte_l, kartis_l = ISS_XG_KARTE[veids]
    runa = [rr[0], S.reta_frase(karte_l if k2.get("tips") == "xg_karte" else kartis_l, veids=veids, n=2)
            .format(no=m_.group(1) if m_ else "the start of the season")]
    kartes = [dict(k2, ilgums=3.5)]
    if other:
        og = other[0]["viz"]["grupa"]
        virsr, sak = ISS_XG_GRUPA[(veids, og)]
        vardi = [("the " if veids == "komandas" else "") * (i == 0) + str(c.get("v2", "")) for i, c in enumerate(other)]
        teik = S.reta_frase(sak, veids=veids, n=1).format(names=_vardu_saraksts(vardi))
        apaksa = "PDO  ·  AVERAGE 100"
        if veids in ("speletaji", "vartsargi"):
            G = sum(_xg_skaitli(c)[0] or 0 for c in other)
            X = sum(_xg_skaitli(c)[1] or 0 for c in other)
            if veids == "speletaji":
                teik += f" {int(G)} goal{'' if int(G) == 1 else 's'} on {S.xgv(X)} expected, combined."
                apaksa = f"{int(G)} GOALS ON {X:.1f} xG  ·  COMBINED"
            else:
                teik += f" {int(G)} allowed on {S.xgv(X)} expected, combined."
                apaksa = f"{int(G)} ALLOWED ON {X:.1f} EXPECTED  ·  COMBINED"
        kartes.append({"tips": "fantasy_divi", "veids_k": veids, "ilgums": 3.6, "_tv": k2.get("_tv"), "virsr": virsr,
                       "kartites": list(other)})
        runa.append(teik)
    if mine:
        virsr, _ = ISS_XG_GRUPA[(veids, hg)]
        dalas = []
        for i, c in enumerate(mine):
            if veids == "speletaji":
                G, X = _xg_skaitli(c)
                dalas.append(f"{c.get('v2', '')}: {int(G)} goal{'' if int(G) == 1 else 's'} on {S.xgv(X)} expected." if i == 0
                             else f"{c.get('v2', '')}: {int(G)} on {S.xgv(X)}.")
            elif veids == "vartsargi":
                gs = abs(_parsk(c["viz"]["kart"]["liels"]) or 0)
                dalas.append(f"{c.get('v2', '')}: {S.xgv(gs)} {'saved above' if hg == 'laim' else 'worse than'} expected." if i == 0
                             else f"{c.get('v2', '')}: {S.xgv(gs)}.")
            else:
                dalas.append(f"The {c.get('v2', '')}: PDO {c['viz']['kart']['liels']}.")
        kartes.append({"tips": "fantasy_divi", "veids_k": veids, "ilgums": 3.6, "_tv": k2.get("_tv"), "virsr": virsr,
                       "kartites": list(mine)})
        runa.append(" ".join(dalas))
    kartes.append(hero)
    runa.append(rr[-2])
    runa.append(_iss_cilpa(s, veids, S.atskata_teksts()))
    return kartes, runa


def _iss_fakti(s):
    kk, rr = s["kartes"], s["runa"]
    if len(rr) != len(kk) + 2:
        return None
    keep = [i for i, c in enumerate(kk) if c.get("tips") != "fakts_serijas"]
    kartes = [kk[i] for i in keep]
    runa = [rr[0]] + [rr[i + 1] for i in keep]
    for j, c in enumerate(kartes):                                    # TOP 3: #3 un #2 – tikai galvenais teikums
        if c.get("tips") != "fakts_tablo" or (c.get("nr") or 1) <= 1:
            continue
        row = next((x for x in c.get("fakti") or [] if x.get("nr") == c["nr"]), {})
        pre = str((row.get("plus") or {}).get("runa_pre") or "").strip()
        if pre:                                                       # "Number 3. Connor McDavid has …" (bez konteksta teikuma)
            m_ = re.match(r"(The NHL week in numbers[^.]*\.)\s*", runa[j + 1])
            runa[j + 1] = ((m_.group(1) + " ") if m_ else "") + pre
        kartes[j] = dict(c, ilgums=3.4, bez_plus=True)                # kartīte bez izvēršanās – parādās un nolaižas rindā
    for j, c in enumerate(kartes):                                    # TOP N izkārtojums A – rinda izplešas tabulā (11.11.)
        if c.get("tips") == "fakts_tablo" and len(c.get("fakti") or []) > 1 and not c.get("bez_tablo"):
            kartes[j] = dict(c, izk="A")
    for c in kartes:
        if c.get("tips") == "fakts_ripa":                             # īsāka pauze ripu ainas beigās
            c["ilgums"] = max(4.5, 1.25 + 0.1 * len(c["ripa"]["punkti"]) + 1.0)
    if (s.get("intro") or {}).get("noslepums"):
        runa.append(_iss_cilpa(s, "fakts"))
    else:                                                             # TOP N bez noslēpuma – jautājums komentāriem
        runa.append(S.reta_frase(ISS_FAKTI_BEIGAS, veids="fakts", n=2))
    return kartes, runa


def _akc_tips(c):
    a = tuple(c.get("akc") or (0, 0, 0))
    return "v" if a[1] > a[0] + 40 else ("x" if a[0] > a[1] + 40 else "-")


def _iss_atskats(s):
    kk, rr = s["kartes"], s["runa"]
    if len(rr) != len(kk) + 2 or len(kk) < 2 or kk[0].get("tips") not in ("fantasy_kartis", "fantasy_ats_saraksts"):
        return None
    tag = str((s.get("intro") or {}).get("tag", "")).upper()
    xg = "FOLLOW-UP" in tag
    k2, cards = kk[0], kk[1:]
    zal = [c for c in cards if _akc_tips(c) == "v"]
    sar = [c for c in cards if _akc_tips(c) == "x"]
    pel = [c for c in cards if _akc_tips(c) == "-"]
    izv = ([zal[0]] if zal else pel[:1]) + (sar[:1] if sar else zal[1:2])
    if not izv:
        izv = cards[:1]
    veids_v = "atskats_fantasy"
    if xg:
        veids_j = "vartsargi" if "GOALIE" in tag else ("komandas" if "TEAM" in tag else "speletaji")
        veids_v = f"atskats_{veids_j}"
        ap = (s.get("_intro_vecais") or {}).get("apaksa") or [""]
        m_ = re.search(r"([A-Z][a-z]{2} \d+)", str(ap[0]))
        X = {"speletaji": "scorers", "vartsargi": "goalies", "komandas": "teams"}[veids_j]
        n_ = _VARDIEM.get(len(cards), str(len(cards)))
        ievads = S.reta_frase(ISS_XGATS_IEVADS, veids=veids_v, n=2).format(d=m_.group(1) if m_ else "our last list", n=n_,
                                                                           N=n_.capitalize(), X=X)
    else:
        d_ = re.findall(r"([A-Z][a-z]{2} \d+)", str(s.get("periods", "")))
        ievads = S.reta_frase(ISS_FANATS_IEVADS[:2] if len(d_) >= 2 else ISS_FANATS_IEVADS[2:], veids=veids_v, n=1).format(
            no=d_[0] if d_ else "", lidz=d_[1] if len(d_) > 1 else "")
    kartes = [dict(k2, ilgums=3.5)] + izv
    runa = [rr[0], (str(s.get("aki_runa") or "") + " " + ievads).strip()] + [rr[1 + kk.index(c)] for c in izv]
    runa.append(_iss_cilpa(s, veids_v, S.reta_frase(ISS_ATS_PIRMS, veids=veids_v, n=1)))
    return kartes, runa


def iss_parveidot(s, veids):
    """Īsā versija no gatava (jaunā izskata) scenārija; kļūdas gadījumā – parastā versija."""
    if not s or not ISS["on"] or not s.get("kartes"):
        return s
    try:
        if veids in ("fantasy", "streameri"):
            r_ = _iss_fantasy(s, veids)
        elif veids in XG_VEIDI:
            r_ = _iss_xg(s, veids)
        elif veids == "fakts":
            r_ = _iss_fakti(s)
        elif veids == "atskats":
            r_ = _iss_atskats(s)
        else:
            r_ = None
        if not r_:
            print(f"ĪSĀ VERSIJA: {veids} – nav piemērota scenārija, parastā versija")
            return s
        s["_kartes_pilnas"] = s["kartes"]
        s["kartes"], s["runa"] = r_
        _iss_outro(s)
        s["_iss"] = True
        s["nosaukums"] = (s.get("nosaukums") or f"xg_{veids}_{s.get('lidz', '')}") + "_iss"
        print(f"ĪSĀ VERSIJA: {len(s['kartes'])} ainas + āķis + cilpa, ~{sum(len(str(x).split()) for x in s['runa'])} vārdi")
    except Exception as ex:                                           # noqa: BLE001
        print(f"ĪSĀ VERSIJA: {type(ex).__name__}: {ex} – parastā versija")
    return s


# ================================================================ STREAK WATCH (--veids serijas, kopš 10.11.2026)
# Atsevišķs ~25 s video: noslēpuma āķis (garākās aktīvās punktu sērijas līderis) → POINT STREAKS → GOALIES OF THE WEEK
# → cilpa. Ainas – tās pašas, kas faktu video beigās (fakti_serijas_ainas).   python ShortsB.py --veids serijas
PS_SOLO = ["The longest active point streaks in the NHL right now. Anything in yellow has reached ten games.",
           "The longest point streaks still alive.",
           "Still rolling: the longest active point streaks in the league.",
           "Who keeps finding the scoresheet? The longest active point streaks."]
PS_SOLO_NAV = ["No one has reached ten straight games yet. These are the longest active point streaks.",
               "The longest point streaks still alive. Who reaches ten first?"]
NOSL_Q2["serijas"] = [(("WHO'S", "STILL", "ROLLING?"), "Who's still rolling?"),
                      (("THE LONGEST", "STREAK", "RIGHT NOW?"), "The longest streak right now?"),
                      (("CAN ANYONE", "CATCH", "HIM?"), "Can anyone catch him?"),
                      (("WHO CAN'T", "STOP", "SCORING?"), "Who can't stop scoring?"),
                      (("STREAK", "WATCH:", "WHO'S #1?"), "Streak watch: who's number one?")]
ST_BEIGAS = ["Can {v} make it {n1}? Follow for next week's streak watch.",
             "Which streak ends first? Follow for next week's streak watch.",
             "Who keeps it rolling? Follow for next week's streak watch."]
ST_BEIGAS_VA = ["Which streak ends first? Follow for next week's streak watch.",
                "Who shuts the door next? Follow for next week's streak watch."]
NOSL_Q2["serijas_va"] = [(("WHO", "SHUT THE", "DOOR?"), "Who shut the door?"),
                         (("THE HOTTEST", "GOALIE", "THIS WEEK?"), "The hottest goalie this week?"),
                         (("CAN ANYONE", "BEAT", "HIM?"), "Can anyone beat him?")]
VIRSR_SERIJAS = ["NHL streak watch: guess who has a point in {n} straight games",
                 "Guess who has the longest active point streak in the NHL",
                 "Streak watch: who's still rolling? Guess the leader",
                 "The longest NHL point streaks right now – guess who's #1"]
VIRSR_SERIJAS_VA = ["NHL streak watch: guess the hottest goalie of the week",
                    "Goalies of the week – guess who shut the door"]


def veids_serijas_b(m, a):
    D = S.fakti_dati(a.lidz)
    lidz = D["lidz"]
    tv = {"lab": "NHL · STREAK", "liels": "WATCH", "kr": [S.DZELTENS, S.ZILS], "labaja": f"STATS THRU {S.dat(lidz).upper()}"}
    ainas = fakti_serijas_ainas(D, m, [], tv, 0, solo=True)
    if not ainas:
        print("Streak watch: nav ne punktu sēriju, ne vārtsargu datu.")
        return None
    kartes = [k_ for k_, _ in ainas]
    tv["kr"] = [S.DZELTENS] + [S.ZILS] * (len(kartes) - 1)            # tablo punkti – cik ainu (2–3)
    for i, k_ in enumerate(kartes):
        k_["_tv_idx"] = i
    k0 = next((k_ for k_ in kartes if k_.get("rindas")), None)       # āķim – punktu sēriju (vai vārtsargu) līderis
    if k0 is None:
        print("Streak watch: nav ne punktu sēriju, ne vārtsargu datu.")
        return None
    r0 = k0["rindas"][0]
    ps = k0["virsr"][0][0] == "POINT"
    vards, team = str(r0["vards"]), str(r0["team"])
    runa = [""] + [r_ for _, r_ in ainas] + [""]                      # stāsts par redzamo – fakti_serijas_ainas(solo=True)
    saraksts = []
    kur_t = {"HOME": " (home)", "AWAY": " (road)"}
    for k_ in kartes:
        if k_.get("tips") == "fakts_hc":                              # HOT & COLD
            kur_k = {"HOME": " at home", "AWAY": " on the road"}
            for kol_, nos_ in zip(k_["kol"], ("Win streaks:", "Without a win:")):
                if kol_["rindas"]:
                    saraksts.append(nos_)
                    saraksts += [f"{S.KOMANDAS.get(r_['kom'], ('', r_['kom']))[0]} {S.kom_nos(r_['kom'])}: {r_['n']} games{kur_k.get(r_['veids'], '')}".strip()
                                 for r_ in kol_["rindas"]]
            if k_.get("sausums"):
                x_ = k_["sausums"]
                saraksts.append(f"Scoring drought: {x_['vards']} ({x_['team']}) – {x_['n']} games without a goal")
            continue
        if k_.get("kol"):                                             # vārtu + piespēļu sērijas
            for kol_, nos_ in zip(k_["kol"], ("Goal streaks:", "Assist streaks:")):
                if kol_["rindas"]:
                    saraksts.append(nos_)
                    saraksts += [f"{r_['vards']} ({r_['team']}): {r_['n']} straight games{kur_t.get(r_['veids'], '')}" for r_ in kol_["rindas"]]
            continue
        saraksts.append(("Longest active point streaks:" if k_["virsr"][0][0] == "POINT" else "Goalies of the week:"))
        saraksts += [f"{r_['vards']} ({r_['team']}): {r_['liels']} {str(r_['maz']).lower()}" for r_ in k_["rindas"]]
    n_ = r0["liels"] if ps else ""
    s = {"intro": {"aki": True, "tag": "NHL  ·  STREAK WATCH", "ilgums": 2.6, "_tv": tv}, "kartes": kartes,
         "outro": {"rindas": [], "info": []}, "runa": runa, "lidz": lidz, "zimogs": f"STATS THROUGH {S.dat(lidz, True).upper()}",
         "periods": f"through {S.dat(lidz, True)}", "_bez_zimoga": True, "nosaukums": f"serijas_{lidz}",
         "virsraksts": f"NHL streak watch: {vards} has a point in {n_} straight games" if ps else f"NHL goalies of the week: {vards}",
         "apraksts": "The longest active NHL point streaks and the goalies of the week.", "saraksts": saraksts,
         "piezime": "Point, goal and assist streaks: active, 3+ games (all / home / road). Goalies: shutout streaks of 120+ minutes this week, "
                    "then the best save % (2+ starts).",
         "tagi": "#NHL #hockey #NHLstats #StreakWatch #Shorts",
         "thumb": {"tag": "NHL  ·  STREAK WATCH", "hook": ["STREAK", "WATCH"], "vards": vards.split()[-1].upper(), "badge": team,
                   "skaitlis": f"{n_} GAMES" if ps else str(r0["liels"]), "kr": S.DZELTENS,
                   "apaksa": "in a row with a point · longest active" if ps else "goalie of the week", "datums": lidz}}
    noslepuma_aki(s, [(team, vards.split()[-1])], NOSL_Q1["speletajs" if ps else "vartsargs"],
                  NOSL_Q2["serijas" if ps else "serijas_va"], "serijas", bez_q1=True)   # bez "Mystery solved"
    nsl = (s.get("intro") or {}).get("noslepums")
    if nsl:
        if NOSL_VIRSRAKSTS:
            s["virsraksts"] = _virsr_izvele(VIRSR_SERIJAS if ps else VIRSR_SERIJAS_VA, "serijas", {"n": n_}) or s["virsraksts"]
            _ns_vards_apraksta(s, vards)
        s["thumb"]["hook"] = list(nsl["q2"][0])
    else:                                                             # bez noslēpuma (--bez-noslepuma) – sākas ar sarakstu
        s["intro"] = None
        s["runa"] = s["runa"][1:]
        s["runa"][0] = f"Streak watch. {s['runa'][0]}"
    # beigas (kopš 11.11.2026): nevis āķa jautājums atkārtoti (atbilde jau bija), bet jautājums par nākamo spēli
    s["runa"][-1] = S.reta_frase(ST_BEIGAS if ps else ST_BEIGAS_VA, veids="serijas", n=2).format(
        v=vards, n1=(int(r0["liels"]) + 1) if ps and str(r0.get("liels", "")).isdigit() else "")
    _iss_outro(s)
    s["_iss"] = True
    return s


if __name__ == "__main__":
    ieslegt()
    print(f"STILS {STILS}: STORY")
    rc = S.main()
    if FAKTI_PAPILDU.get("fakti"):
        pierakstit_papildu_faktus(_arg("--mape", os.path.join(S.BASE, "video")))
    sys.exit(rc)
