"""Sīktēlu (thumbnail) izkārtojumi – lai kanāla tīklā blakus esošie sīktēli neatkārtotos.

Izkārtojumi (burti – kā paraugu attēlos):
  A – sērijas krāsa: siluets ar "?" sērijas krāsā (xG zils, fantasy zaļš, streameri violets, fakti oranžs, atskati rozā)
  B – komandas krāsas: īsts krekls komandas krāsās ar "?" numura vietā + komandas krāsas gaisma
  D – laukuma metienu karte: puse laukuma ar metieniem / vārtiem (xG spēlētāji, vārtsargi, fakti)
  E – divas puses: fakts pret gaidīto (GOALS 9 vs EXPECTED 4); atskatiem – CALLED IT pret MISSED
  F – mini grafiks: stabiņi pa spēlēm (fakti, streameri) vai nākamās nedēļas spēļu dienas (fantasy)
  J – tikai teksts uz pilna sērijas krāsas fona (akcents – ne biežāk kā reizi J_PEC video)
  K – čeks: atskatu rezultāti kā veikala čeks ar ✓ / ✗ un TOTAL

Izvēle: katram video veidam sava secība (SECIBA); ņem to izkārtojumu, kas šim veidam izmantots visilgāk atpakaļ,
un nekad to pašu, kas bija iepriekšējam video (ja var – arī ne kā aizpriekšējam; kanāla tīklā tie stāv blakus). Vēsture – video\\video_info.json
(lauki "sikts" un "sikts_veids"). Ar roku:  --sikts D   (0 = vecais dzeltenais noslēpuma sīktēls).
Tiesnešu video – bez izmaiņām (vecais sīktēls).
"""
import json
import math
import os
import re

from PIL import Image, ImageDraw, ImageFilter

TUMSS = (8, 12, 26)
ZALS_T, SARK_T = (21, 94, 52), (140, 28, 28)                         # E pušu krāsas (tumšas)
SERIJAS = {                                                           # veids: (sērijas krāsa, apraksts)
    "xg_sp": ((56, 189, 248), "xG spēlētāji"),
    "xg_va": ((56, 189, 248), "xG vārtsargi"),
    "xg_kom": ((56, 189, 248), "xG komandas"),
    "xg_atsk": ((244, 114, 182), "xG atskats"),
    "fantasy": ((74, 222, 128), "fantasy"),
    "streameri": ((167, 139, 250), "streameri"),
    "fan_atsk": ((244, 114, 182), "fantasy atskats"),
    "fakti": ((251, 146, 60), "fakti"),
}
SECIBA = {"xg_sp": "BDEA", "xg_va": "BEDA", "xg_kom": "EA", "fantasy": "BFA", "streameri": "BFA",
          "fakti": "FDBA", "xg_atsk": "KEA", "fan_atsk": "KEA"}
NOSAUKUMI = {"0": "vecais", "A": "serijas_krasa", "B": "komandas_krekls", "D": "laukums", "E": "divas_puses",
             "F": "grafiks", "J": "teksts", "K": "ceks"}
J_PEC = 6                                                             # J – ne biežāk kā reizi 6 video (kanālā kopā)
MONO_FONTI = ["consolab.ttf", "consola.ttf", "courbd.ttf", "lucon.ttf", "DejaVuSansMono-Bold.ttf",
              "LiberationMono-Bold.ttf", "DejaVuSansMono.ttf"]
MONO_MAPES = ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
              "/Library/Fonts", "/System/Library/Fonts/Supplemental"]

B = None                                                              # ShortsB modulis (iedod izveidot())
S = None                                                              # shorts modulis
_KESA = {}


# ---------------------------------------------------------------- palīgi
def _veids(tag):
    t = str(tag).upper()
    for atsl, v in (("FOLLOW-UP", "xg_atsk"), ("GOALIE", "xg_va"), ("TEAM LUCK", "xg_kom"), ("LUCK REPORT", "xg_sp"),
                    ("RECAP", "fan_atsk"), ("STREAMER", "streameri"), ("WAIVER", "fantasy"), ("FANTASY", "fantasy"),
                    ("WEEK IN NUMBERS", "fakti")):
        if atsl in t:
            return v
    return None                                                       # tiesneši u.c. – vecais sīktēls


def _gaisaks(kr, k=0.35):
    return tuple(int(x + (255 - x) * k) for x in kr)


def _tumsaks(kr, k=0.5):
    return tuple(int(x * (1 - k)) for x in kr)


def _mono(izm):
    k = ("mono", izm)
    if k not in _KESA:
        f = None
        for nos in MONO_FONTI:
            for m in MONO_MAPES + list(getattr(S, "FONTU_MAPES", [])):
                p = os.path.join(m, nos)
                if os.path.exists(p):
                    from PIL import ImageFont
                    f = ImageFont.truetype(p, izm)
                    break
            if f:
                break
        _KESA[k] = f or S.fonts("bold", izm)
    return _KESA[k]


def _fonts_lidz(txt, veids, izm, max_w, min_izm=28):
    f = S.fonts(veids, izm)
    while f.getlength(txt) > max_w and izm > min_izm:
        izm -= 2
        f = S.fonts(veids, izm)
    return f


def _fons(kr, inten=1.0, konuss=True):
    """Tumšs fons + konuss / gaismas aplis sērijas (vai komandas) krāsā."""
    k = ("fons", tuple(kr), round(inten, 2), konuss)
    if k not in _KESA:
        np = S.np
        a = np.linspace(0, 1, S.H)[:, None]
        img = (np.array((5, 7, 15)) * (1 - a) + np.array((11, 13, 26)) * a)[:, None, :].repeat(S.W, 1).reshape(S.H, S.W, 3)
        im = Image.fromarray(img.astype(np.uint8), "RGB").convert("RGBA")
        m = Image.new("L", (S.W // 4, S.H // 4), 0)
        d = ImageDraw.Draw(m)
        if konuss:
            d.polygon([(480 / 4, -5), (600 / 4, -5), (1140 / 4, 1500 / 4), (-60 / 4, 1500 / 4)], fill=80)
            d.ellipse([110 / 4, 1150 / 4, 970 / 4, 1290 / 4], fill=90)
        d.ellipse([90 / 4, 140 / 4, 990 / 4, 1040 / 4], fill=120)
        m = m.filter(ImageFilter.GaussianBlur(26))
        ma = (np.asarray(m, np.float32) * np.linspace(1.0, 0.35, S.H // 4)[:, None] * inten).clip(0, 255).astype(np.uint8)
        kon = Image.new("RGBA", (S.W, S.H), tuple(_gaisaks(kr, 0.15)) + (0,))
        kon.putalpha(Image.fromarray(ma).resize((S.W, S.H), Image.BILINEAR))
        im.alpha_composite(kon)
        _KESA[k] = im
    return _KESA[k].copy()


def _tag(im, txt, kr, y=118, tumss=False):
    """Sērijas zīmīte augšā: krāsaina ar tumšu tekstu (J – tumša ar krāsainu tekstu)."""
    d = ImageDraw.Draw(im)
    f = _fonts_lidz(txt, "black", 34, 900)
    tw = d.textlength(txt, font=f)
    w, h = tw + 56, 66
    x0 = S.W / 2 - w / 2
    d.rounded_rectangle([x0, y - h / 2, x0 + w, y + h / 2], radius=14, fill=(TUMSS if tumss else tuple(kr)) + (255,))
    d.text((S.W / 2, y + 1), txt, font=f, fill=(tuple(kr) if tumss else TUMSS) + (255,), anchor="mm")


def _jautajums(im, rindas, kr, yc):
    """Āķa jautājums (kā video): baltas rindas, pēdējā – slīpā kastē sērijas krāsā. yc – bloka vidus."""
    rindas = [str(r) for r in rindas if str(r).strip()][:3]
    if not rindas:
        return
    if len(rindas) <= 2:
        izm, dy = (170, 200), 170
    else:
        izm, dy = (128, 148, 172), 142
    y0 = yc - (len(rindas) - 1) * dy / 2
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    for i, r in enumerate(rindas):
        last = i == len(rindas) - 1
        t_ = B._ns_txt(r, izm[min(i, len(izm) - 1)], TUMSS if last else S.BALTS, tuple(kr) if last else None)
        B._ns_put(L, t_, 540, y0 + i * dy + (12 if last else 0), 1.0, 1.0, 2 if last else 0)
    im.alpha_composite(L)


def _izk(n, y0, y1, maks=700):
    """[(cx, augša, izmērs)] n krekliem laukumā y0..y1."""
    if n <= 1:
        izm = int(min(maks, (y1 - y0) / 1.08))
        return [(540, y0 + ((y1 - y0) - izm * 1.08) / 2, izm)]
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


def _mist(kom, v, izm):
    """Krekls komandas krāsās ar "?" numura vietā (vārds izpludināts) – tas pats, ko rāda video."""
    kb = ("mist", kom, v, izm)
    if kb not in B._NS_KESA:
        B._NS_KESA[kb] = B.krekls_reals(kom, v, "?", izm, vards_izpl=11 * izm / 820)
    return B._NS_KESA[kb]


def _pakaramais(im, cx, top, izm):
    sc_k = izm / 820
    d = ImageDraw.Draw(im)
    yt = top + 30 * sc_k
    w_ = max(3, int(9 * sc_k))
    d.line([(cx, yt + 30 * sc_k), (cx, yt - 12 * sc_k)], fill=(190, 196, 208, 255), width=w_)
    d.arc([cx - 30 * sc_k, yt - 72 * sc_k, cx + 30 * sc_k, yt - 12 * sc_k], 140, 400, fill=(190, 196, 208, 255), width=w_)


def _ena(img, r=18, a=0.75, nob=(0, 14)):
    """Mīksta ēna zem attēla (RGBA, mazliet lielāka)."""
    pad = r * 3
    e = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    m = Image.new("L", e.size, 0)
    m.paste(img.getchannel("A").point(lambda v: int(v * a)), (pad + nob[0], pad + nob[1]))
    e.putalpha(m.filter(ImageFilter.GaussianBlur(r)))
    return e, pad


def _likt_ar_enu(im, img, x, y, r=18, a=0.75):
    e, pad = _ena(img, r, a)
    im.alpha_composite(e, (int(x - pad), int(y - pad)))
    im.alpha_composite(img, (int(x), int(y)))


def _mazs_krekls(kom, v, izm, kr_mala=None):
    """Mazs krekls bez vārda: komandas krāsās (spēlētājiem) vai siluets (komandām – lai neatklātu atbildi)."""
    k = ("mazs", kom, bool(v), izm, kr_mala)
    if k not in _KESA:
        kr = B.krekls_reals(kom, "", "?", izm)
        _KESA[k] = kr if v else B._ns_siluets(kr, kr_mala or (200, 200, 210))
    return _KESA[k]


def _varonis(s, krekli):
    """Galvenā kartīte (tā, kura ir āķī)."""
    if not krekli:
        return None
    kom, v = krekli[0]
    kart = [c for c in s.get("kartes", []) if c.get("tips") == "fantasy" and c.get("badge")]
    for c in kart:
        if c.get("badge") == kom and v and str(c.get("v2", "")).upper() == str(v).upper():
            return c
    for c in kart:
        if c.get("badge") == kom and (not v or str(v).upper() in str(c.get("v2", "")).upper()):
            return c
    return next((c for c in kart if c.get("badge") == kom), None)


def _spec(c, tips):
    for it in ((c or {}).get("viz") or {}).get("spec") or []:
        for x in it[1:]:
            if isinstance(x, dict) and x.get("tips") == tips:
                return x
    return None


def _kartes_tips(s, tips):
    return next((c for c in s.get("kartes", []) if c.get("tips") == tips), None)


def _atskata_kartes(s):
    return [c for c in s.get("kartes", []) if c.get("tips") == "fantasy" and c.get("badge")]


def _zime(d, x, y, r, veids, kr, w=None):
    """Zīmēts ✓ / ✗ / – (fontos šie simboli bieži nav)."""
    w = w or max(4, int(r * 0.32))
    if veids == "v":
        d.line([(x - r, y), (x - r * 0.3, y + r * 0.7), (x + r, y - r * 0.8)], fill=kr, width=w, joint="curve")
    elif veids == "x":
        d.line([(x - r * 0.8, y - r * 0.8), (x + r * 0.8, y + r * 0.8)], fill=kr, width=w)
        d.line([(x - r * 0.8, y + r * 0.8), (x + r * 0.8, y - r * 0.8)], fill=kr, width=w)
    else:
        d.line([(x - r * 0.7, y), (x + r * 0.7, y)], fill=kr, width=w)


def _akc_zime(akc):
    akc = tuple(akc or (100, 116, 139))
    if akc[1] > akc[0] + 40:
        return "v", (22, 163, 74)
    if akc[0] > akc[1] + 40:
        return "x", (220, 38, 38)
    return "-", (100, 116, 139)


def _apaksas_teksts(c):
    th, s = c["th"], c["s"]
    if c["veids"] in ("xg_atsk", "fan_atsk") and s.get("aki_f"):
        a = s["aki_f"]
        return f"{a.get('liels', '')} {a.get('zem', '')}".strip().upper()
    sk, ap = str(th.get("skaitlis") or ""), str(th.get("apaksa") or "")
    sep = "  ·  " if re.match(r"^[A-Za-z]", sk) else " "
    return (sk + sep + ap).strip(" ·").upper()


# ---------------------------------------------------------------- A · sērijas krāsa
def sikts_A(c):
    kr = c["kr"]
    im = _fons(kr, 0.95)
    rim = _gaisaks(kr, 0.15)
    for (kom, v), (cx, top, izm) in zip(c["krekli"], _izk(len(c["krekli"]), 215, 925, 660)):
        mist = _mist(kom, v, izm)
        _pakaramais(im, cx, top, izm)
        sil = B._ns_siluets(mist, rim)
        cy = top + mist.height / 2
        B._ns_put(im, sil, cx, cy)
        q = B._ns_txt("?", int(420 * izm / 820), tuple(kr))
        B._ns_put(im, q.filter(ImageFilter.GaussianBlur(18 * izm / 820)), cx, cy + 20 * izm / 820, 1, 0.95)
        B._ns_put(im, q, cx, cy + 20 * izm / 820)
    _jautajums(im, c["rindas"], kr, 1185 if len(c["rindas"]) > 2 else 1150)
    im.alpha_composite(B._ns_vinjete())
    _tag(im, c["tag"], kr)
    return im.convert("RGB")


# ---------------------------------------------------------------- B · komandas krāsas
def sikts_B(c):
    kr = c["kr"]
    kom0 = c["krekli"][0][0]
    gl = B._ns_mala(kom0)
    im = _fons(gl, 1.0)
    for (kom, v), (cx, top, izm) in zip(c["krekli"], _izk(len(c["krekli"]), 215, 925, 660)):
        mist = _mist(kom, v, izm)
        _pakaramais(im, cx, top, izm)
        aura = Image.new("RGBA", mist.size, tuple(B._ns_mala(kom)) + (0,))
        aura.putalpha(mist.getchannel("A").point(lambda x: int(x * 0.55)))
        aura = aura.filter(ImageFilter.GaussianBlur(28 * izm / 660))
        cy = top + mist.height / 2
        B._ns_put(im, aura, cx, cy, 1.06)
        _likt_ar_enu(im, mist, cx - mist.width / 2, top, 22, 0.8)
    _jautajums(im, c["rindas"], kr, 1185 if len(c["rindas"]) > 2 else 1150)
    im.alpha_composite(B._ns_vinjete())
    _tag(im, c["tag"], kr)
    return im.convert("RGB")


# ---------------------------------------------------------------- D · laukuma metienu karte
def _d_dati(c):
    """(punkti [(x, y, g)], leģenda [(krāsa, teksts)]) – g: 2 = vārti, 1 = piespēle, 0 = metiens."""
    s = c["s"]
    if c["veids"] == "fakti":
        k = _kartes_tips(s, "fakts_ripa")
        if not k or not c["krekli"][0][1]:
            return None
        r = k.get("ripa") or {}
        p = [(float(q["x"]), float(q["y"]), 2 if q.get("k") == "G" else 1) for q in r.get("punkti") or [] if "x" in q]
        if len(p) < 4:
            return None
        ng, na = sum(1 for q in p if q[2] == 2), sum(1 for q in p if q[2] == 1)
        m = re.match(r"\s*(\d+)\s*goals?\s*·\s*(\d+)\s*assists?", str(r.get("skaititajs2", "")), re.I)
        if m:
            ng, na = int(m.group(1)), int(m.group(2))
        leg = [((239, 68, 68), f"{ng} GOALS"), ((37, 99, 235), f"{na} ASSISTS")] if na else [((239, 68, 68), f"{ng} GOALS")]
        return p, leg, "ripa"
    sp = _spec(c["varonis"], "ripa")
    if not sp or len(sp.get("punkti") or []) < 5:
        return None
    p = [(float(x), float(y), 2 if g else 0) for (x, y, g) in sp["punkti"]]
    txt = [str(t) for t in sp.get("txt") or []]
    ng = sum(1 for q in p if q[2])
    sh = next((t for t in txt if "shot" in t.lower()), f"{len(p)} shots")
    gl = "GOALS AGAINST" if "AGAINST" in str(sp.get("lab", "")).upper() else "GOALS"
    return p, [((239, 68, 68), f"{ng} {gl}"), ((100, 116, 139), sh.upper())], "xg"


def _laukums(punkti, w=760, RS=2):
    """Puse laukuma vertikāli (vārti augšā, zilā līnija apakšā) ar punktiem; RGBA (w+2pad) × (h+2pad)."""
    s_ = w / 85 * RS
    pad = 24 * RS
    W_, H_ = int(85 * s_ + 2 * pad), int(75 * s_ + 2 * pad)
    L = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    X = lambda yy: pad + (yy + 42.5) * s_                             # noqa: E731
    Y = lambda v: pad + (100 - v) * s_                                # noqa: E731
    r = 28 * s_
    led, mala = (236, 241, 247, 255), (148, 163, 184, 255)
    d.rounded_rectangle([X(-42.5), Y(100), X(42.5), Y(25)], radius=int(r), fill=led, outline=mala, width=5 * RS)
    d.rectangle([X(-42.5), Y(60), X(42.5), Y(25)], fill=led)
    d.line([(X(-42.5), Y(60)), (X(-42.5), Y(25))], fill=mala, width=5 * RS)
    d.line([(X(42.5), Y(60)), (X(42.5), Y(25))], fill=mala, width=5 * RS)
    sarkans, zils = (220, 38, 38, 255), (37, 99, 235, 255)
    for yc in (-22, 22):                                              # iemetiena apļi
        d.ellipse([X(yc - 15), Y(69 + 15), X(yc + 15), Y(69 - 15)], outline=(220, 38, 38, 170), width=3 * RS)
        d.ellipse([X(yc - 1), Y(69 + 1), X(yc + 1), Y(69 - 1)], fill=sarkans)
    for yc in (-22, 22):                                              # neitrālās zonas punkti
        d.ellipse([X(yc - 1), Y(31), X(yc + 1), Y(29)], fill=sarkans)
    inset = 28 - math.sqrt(28 ** 2 - (89 - 72) ** 2)
    d.line([(X(-42.5 + inset), Y(89)), (X(42.5 - inset), Y(89))], fill=sarkans, width=3 * RS)
    d.pieslice([X(-6), Y(89 + 6), X(6), Y(89 - 6)], 0, 180, fill=(147, 197, 253, 255), outline=sarkans, width=2 * RS)
    d.rectangle([X(-3), Y(91.5), X(3), Y(89)], fill=(248, 250, 252, 255), outline=(100, 116, 139, 255), width=2 * RS)
    d.rectangle([X(-42.5) + 3 * RS, Y(26.2), X(42.5) - 3 * RS, Y(25)], fill=zils)
    for (px, py, g) in sorted(punkti, key=lambda q: q[2]):            # vārti virsū
        if not (26 <= px <= 100) or abs(py) > 42.5:
            continue
        if g == 2:
            rr, kr, ol = 1.75, (239, 68, 68, 255), (255, 255, 255, 255)
        elif g == 1:
            rr, kr, ol = 1.25, (37, 99, 235, 235), (255, 255, 255, 255)
        else:
            rr, kr, ol = 0.95, (100, 116, 139, 170), None
        x_, y_ = X(py), Y(px)
        d.ellipse([x_ - rr * s_, y_ - rr * s_, x_ + rr * s_, y_ + rr * s_], fill=kr, outline=ol, width=(3 * RS) if ol else 0)
    return L.resize((W_ // RS, H_ // RS), Image.LANCZOS), pad // RS


def sikts_D(c):
    kr = c["kr"]
    punkti, leg, _ = c["_D"]
    im = _fons(kr, 0.8, konuss=False)
    lauk, pad = _laukums(punkti, 760)
    x0, y0 = 540 - lauk.width / 2, 200
    _likt_ar_enu(im, lauk, x0, y0, 26, 0.85)
    apa = y0 + lauk.height - pad
    kom, v = c["krekli"][0]
    mk = _mazs_krekls(kom, v, 250, _gaisaks(kr, 0.15)).rotate(-8, resample=Image.BICUBIC, expand=True)
    _likt_ar_enu(im, mk, x0 + lauk.width - mk.width + 30, apa - mk.height + 70, 16, 0.8)
    d = ImageDraw.Draw(im)                                            # leģenda zem laukuma
    f = S.fonts("bold", 38)
    gab = [(k_, t_, d.textlength(t_, font=f)) for k_, t_ in leg]
    kop = sum(28 + 14 + w_ for _, _, w_ in gab) + 44 * (len(gab) - 1)
    x = 540 - kop / 2
    y = apa + 62
    for k_, t_, w_ in gab:
        d.ellipse([x, y - 14, x + 28, y + 14], fill=tuple(k_) + (255,), outline=(255, 255, 255, 255), width=3)
        d.text((x + 42, y), t_, font=f, fill=(226, 232, 240, 255), anchor="lm")
        x += 28 + 14 + w_ + 44
    _jautajums(im, c["rindas"], kr, 1225 if len(c["rindas"]) > 2 else 1200)
    im.alpha_composite(B._ns_vinjete())
    _tag(im, c["tag"], kr)
    return im.convert("RGB")


# ---------------------------------------------------------------- E · divas puses
def _e_dati(c):
    """(kreisā etiķete, skaitlis, labā etiķete, skaitlis, kreisā ir "laba")."""
    if c["veids"] in ("xg_atsk", "fan_atsk"):
        kar = _atskata_kartes(c["s"])
        z = [_akc_zime(k.get("akc"))[0] for k in kar]
        if not kar:
            return None
        return "CALLED IT", str(z.count("v")), "MISSED", str(z.count("x")), True
    j = _spec(c["varonis"], "joslas")
    if not j or len(j.get("rind") or []) < 2:
        return None
    (l1, _, t1, _), (l2, _, t2, _) = j["rind"][:2]
    l1 = {"GOALS": "SCORED"}.get(str(l1).upper(), str(l1).upper())
    labs = tuple((j.get("chip") or (None, (34, 197, 94)))[1])
    return l1, str(t1), str(l2).upper(), str(t2), labs[1] > labs[0]


def sikts_E(c):
    kr = c["kr"]
    l1, v1, l2, v2, laba = c["_E"]
    np = S.np
    k1, k2 = (ZALS_T, SARK_T) if laba else (SARK_T, ZALS_T)
    a = np.linspace(0, 1, S.H)[:, None, None]
    def puse(kr_):                                                    # noqa: E306
        g = (np.array(_gaisaks(kr_, 0.06)) * (1 - a * 0.55) + np.array(TUMSS) * a * 0.55)
        return Image.fromarray(g.repeat(S.W, 1).astype(np.uint8), "RGB").convert("RGBA")
    im = puse(k2)
    m = Image.new("L", (S.W, S.H), 0)
    ImageDraw.Draw(m).polygon([(0, 0), (585, 0), (495, S.H), (0, S.H)], fill=255)
    im.paste(puse(k1), (0, 0), m)
    tm = Image.new("RGBA", (S.W, S.H), TUMSS + (0,))                  # apakšā tumšāks – lai jautājums labi lasāms
    tm.putalpha(Image.fromarray((np.clip((np.linspace(0, 1, S.H) - 0.42) / 0.3, 0, 1) * 165).astype(np.uint8)[:, None]
                                .repeat(S.W, 1), "L"))
    im.alpha_composite(tm)
    d = ImageDraw.Draw(im)
    yc = 520
    for (lab, val, cx) in ((l1, v1, 262), (l2, v2, 818)):
        fl = _fonts_lidz(lab, "bold", 44, 400)
        d.text((cx, yc - 225), lab, font=fl, fill=(255, 255, 255, 215), anchor="mm")
        fv = _fonts_lidz(val, "black", 330, 330, 120)
        sh = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((cx + 6, yc + 14), val, font=fv, fill=(0, 0, 0, 150), anchor="mm")
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        d.text((cx, yc), val, font=fv, fill=(255, 255, 255, 255), anchor="mm")
    xc = 540
    d.ellipse([xc - 84, yc - 84, xc + 84, yc + 84], fill=TUMSS + (255,), outline=(255, 255, 255, 255), width=8)
    d.text((xc, yc + 2), "VS", font=S.fonts("black", 62), fill=(255, 255, 255, 255), anchor="mm")
    apa = _apaksas_teksts(c)
    if apa:
        fa = _fonts_lidz(apa, "black", 48, 900)
        sh = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((543, yc + 259), apa, font=fa, fill=(0, 0, 0, 200), anchor="mm")
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
        d.text((540, yc + 255), apa, font=fa, fill=(255, 255, 255, 255), anchor="mm")
    _jautajums(im, c["rindas"], kr, 1205 if len(c["rindas"]) > 2 else 1170)
    _tag(im, c["tag"], kr)
    return im.convert("RGB")


# ---------------------------------------------------------------- F · mini grafiks
def _f_dati(c):
    """{"stabi": [(vērtība, etiķete, izcelts)], "liels", "vien", "apr"} vai {"dienas": [...]}."""
    s, th = c["s"], c["th"]
    if c["veids"] == "fakti":
        k = _kartes_tips(s, "fakts_ripa")
        sk = str(th.get("skaitlis") or "")
        m = re.match(r"^\s*([+\-−]?[\d.,/%]+)\s*(.*)$", sk)
        liels, vien = (m.group(1), m.group(2).upper()) if m else (sk, "")
        apr = str(th.get("apaksa") or "").split("·")[0].strip().upper()
        if k:
            sec, sk_ = [], {}
            for q in (k.get("ripa") or {}).get("punkti") or []:
                lab = str(q.get("lab", "")).split("·")[0].strip()
                if lab not in sk_:
                    sec.append(lab)
                    sk_[lab] = 0
                sk_[lab] += 1
            if len(sec) >= 4:
                return {"stabi": [(sk_[l_], "", False) for l_ in sec], "liels": liels, "vien": vien, "apr": apr,
                        "vertibas": True}
        h = _kartes_tips(s, "fakts_hist")
        if h and len((h.get("hist") or {}).get("bins") or []) >= 4:
            hh = h["hist"]
            st = [(math.log10(1 + n), str(lab), i == hh.get("hero")) for i, (lab, n) in enumerate(hh["bins"])]
            return {"stabi": st, "liels": liels, "vien": vien, "apr": str(hh.get("z1") or apr).upper(), "vertibas": False}
        return None
    a = s.get("aki_f") or {}
    ap = a.get("apli") or []
    liels_ = str(a.get("liels") or "")
    m = re.match(r"^\s*([+\-−]?[\d.,/%]+)\s*(.*)$", liels_)
    liels, vien = (m.group(1), m.group(2).upper()) if m else (liels_, "")
    if ap and all(re.match(r"^\d+$", str(x)) for x in ap):
        iz = set(a.get("izcelt") or [])
        return {"stabi": [(int(x), "", i in iz) for i, x in enumerate(ap)], "liels": liels, "vien": vien,
                "apr": str(a.get("zem") or "").upper(), "vertibas": True}
    viz = (c["varonis"] or {}).get("viz") or {}
    ned = viz.get("ned") or []
    if len(ned) == 7 and any(n_.get("o") for n_ in ned):
        rost = viz.get("rost")
        apr = str(a.get("zem") or "NEXT WEEK").upper() + (f"  ·  {rost:.0f}% ROSTERED" if isinstance(rost, (int, float)) else "")
        return {"dienas": ned, "liels": liels, "vien": vien, "apr": apr}
    return None


def _f_stabi(im, st, kr, x0, x1, ybot, hmax, vertibas):
    n = len(st)
    gap = max(10, int((x1 - x0) / n * 0.22))
    bw = ((x1 - x0) - gap * (n - 1)) / n
    mx = max(1e-9, max(v for v, _, _ in st))
    L = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    f = S.fonts("bold", int(min(44, max(26, bw * 0.45))))
    kr_g = _gaisaks(kr, 0.3)
    for i, (v, lab, iz) in enumerate(st):
        x = x0 + i * (bw + gap)
        h = max(14, hmax * v / mx)
        k_ = (tuple(kr) if iz else (71, 85, 105)) if any(z for _, _, z in st) else kr_g
        d.rounded_rectangle([x, ybot - h, x + bw, ybot], radius=int(min(14, bw / 3)), fill=tuple(k_) + (255,))
        d.rectangle([x, ybot - min(h, 16), x + bw, ybot], fill=tuple(k_) + (255,))
        if vertibas:
            d.text((x + bw / 2, ybot - h - 14), str(int(v)), font=f, fill=(226, 232, 240, 255), anchor="md")
        if lab:
            d.text((x + bw / 2, ybot + 16), lab, font=S.fonts("bold", 30), fill=(148, 163, 184, 255), anchor="ma")
    gl = L.filter(ImageFilter.GaussianBlur(26))
    gl.putalpha(gl.getchannel("A").point(lambda a: int(a * 0.55)))
    im.alpha_composite(gl)
    im.alpha_composite(L)
    ImageDraw.Draw(im).line([(x0 - 10, ybot + 2), (x1 + 10, ybot + 2)], fill=(148, 163, 184, 160), width=3)


def _f_dienas(im, ned, kr, x0, x1, ybot, h):
    d = ImageDraw.Draw(im)
    n = 7
    gap = 16
    bw = ((x1 - x0) - gap * (n - 1)) / n
    f_o = S.fonts("black", 34)
    for i, (dn, n_) in enumerate(zip(("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"), ned)):
        x = x0 + i * (bw + gap)
        if n_.get("o"):
            k_ = tuple(n_.get("kr") or kr)
            gl = Image.new("RGBA", (S.W, S.H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle([x, ybot - h, x + bw, ybot], radius=18, fill=k_ + (200,))
            im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(22)))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([x, ybot - h, x + bw, ybot], radius=18, fill=k_ + (255,))
            t_ = Image.new("RGBA", (int(h), int(bw)), (0, 0, 0, 0))
            ImageDraw.Draw(t_).text((h / 2, bw / 2), str(n_["o"]), font=f_o, fill=TUMSS + (255,), anchor="mm")
            t_ = t_.rotate(90, expand=True)
            im.alpha_composite(t_, (int(x), int(ybot - h)))
            d = ImageDraw.Draw(im)
        else:
            d.rounded_rectangle([x, ybot - h * 0.18, x + bw, ybot], radius=14, fill=(30, 41, 59, 255))
        d.text((x + bw / 2, ybot + 18), dn, font=S.fonts("bold", 30), fill=(148, 163, 184, 255), anchor="ma")


def sikts_F(c):
    kr = c["kr"]
    D_ = c["_F"]
    im = _fons(kr, 0.75, konuss=False)
    if "dienas" in D_:
        _f_dienas(im, D_["dienas"], kr, 110, 970, 690, 430)
    else:
        _f_stabi(im, D_["stabi"], kr, 120, 960, 700, 420, D_.get("vertibas"))
    d = ImageDraw.Draw(im)
    kom, v = c["krekli"][0]
    yc = 870
    mk = _mazs_krekls(kom, v, 190, _gaisaks(kr, 0.15)) if kom else None
    x = 90
    if mk is not None:
        _likt_ar_enu(im, mk, x, yc - mk.height / 2 + 6, 12, 0.8)
        x += mk.width + 26
    fl = _fonts_lidz(D_["liels"], "black", 200, 330, 100)
    d = ImageDraw.Draw(im)
    d.text((x, yc), D_["liels"], font=fl, fill=tuple(_gaisaks(kr, 0.2)) + (255,), anchor="lm")
    x2 = x + d.textlength(D_["liels"], font=fl) + 26
    mw = 1000 - x2
    if D_.get("vien"):
        fv = _fonts_lidz(D_["vien"], "black", 62, mw, 30)
        d.text((x2, yc - 8), D_["vien"], font=fv, fill=(255, 255, 255, 255), anchor="ls")
    if D_.get("apr"):
        fa = _fonts_lidz(D_["apr"], "bold", 34, mw, 22)
        d.text((x2, yc + 20), D_["apr"], font=fa, fill=(203, 213, 225, 255), anchor="lt")
    _jautajums(im, c["rindas"], kr, 1245 if len(c["rindas"]) > 2 else 1215)
    im.alpha_composite(B._ns_vinjete())
    _tag(im, c["tag"], kr)
    return im.convert("RGB")


# ---------------------------------------------------------------- K · čeks
def _k_dati(c):
    s, th = c["s"], c["th"]
    kar = _atskata_kartes(s)
    if len(kar) < 2:
        return None
    rind = []
    for k in kar:
        viz = k.get("viz") or {}
        if c["veids"] == "fan_atsk":
            lab = "ADD" if viz.get("grupa") == "add" else "DROP"
            lab_r = f"{k.get('_pts', '')}P" if k.get("_pts") is not None else ""
        else:
            ws = str(k.get("augsa", "")).upper()
            lab = "HOT" if "COOLDOWN" in ws else ("DUE" if "DUE" in ws else (ws.replace("WE SAID:", "").split() or ["PICK"])[0])
            lab_r = str((viz.get("kart") or {}).get("liels") or "").replace(" ", "")
        z, zk = _akc_zime(k.get("akc"))
        rind.append((f"{lab} #{k.get('nr', '')} {k.get('badge', '')}", z, zk, lab_r))
    if c["veids"] == "fan_atsk":
        apa = str(th.get("nedela") or "").upper()
    else:
        apa = str(th.get("apaksa") or "").split("·")[0].strip().upper()
    total = str((s.get("aki_f") or {}).get("liels") or th.get("skaitlis") or "")
    return {"rind": rind[:8], "apa": apa, "total": total}


def sikts_K(c):
    kr = c["kr"]
    D_ = c["_K"]
    im = _fons(kr, 0.85)
    n = len(D_["rind"])
    pw = 820
    rh = min(74, int(480 / max(1, n)))
    fm = _mono(min(46, int(rh * 0.66)))
    fh = _mono(52)
    fs = _mono(34)
    ph = 40 + 70 + 50 + 40 + n * rh + 30 + 80 + 40 + 90 + 50
    P = Image.new("RGBA", (pw, ph + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(P)
    papirs = (248, 246, 240, 255)
    zz = [(0, 0), (pw, 0), (pw, ph)]                                  # apakšā – plēsta mala (zigzags)
    st_ = 26
    for i in range(int(pw / st_), -1, -1):
        zz.append((i * st_, ph + (14 if i % 2 else 0)))
    d.polygon(zz, fill=papirs)
    tk = (30, 32, 40, 255)
    y = 40
    d.text((pw / 2, y + 30), "ICE MATH  ·  RECEIPT", font=fh, fill=tk, anchor="mm")
    y += 70
    if D_["apa"]:
        d.text((pw / 2, y + 20), D_["apa"], font=fs, fill=(90, 94, 104, 255), anchor="mm")
    y += 50
    for x in range(40, pw - 40, 22):
        d.line([(x, y), (x + 11, y)], fill=(150, 154, 164, 255), width=3)
    y += 40
    cw = fm.getlength("M")
    x_l, x_z, x_r = 46, pw - 210, pw - 46
    for (lab, z, zk, lab_r) in D_["rind"]:
        yc = y + rh / 2
        d.text((x_l, yc), lab, font=fm, fill=tk, anchor="lm")
        x_dot0 = x_l + fm.getlength(lab) + cw * 0.6
        nd = max(0, int((x_z - 34 - x_dot0) / cw))
        d.text((x_dot0, yc), "." * nd, font=fm, fill=(150, 154, 164, 255), anchor="lm")
        _zime(d, x_z, yc, rh * 0.26, z, zk + (255,), max(5, int(rh * 0.1)))
        if lab_r:
            d.text((x_r, yc), lab_r, font=fm, fill=zk + (255,), anchor="rm")
        y += rh
    y += 14
    for x in range(40, pw - 40, 22):
        d.line([(x, y), (x + 11, y)], fill=(150, 154, 164, 255), width=3)
    y += 30
    fT = _mono(58)
    d.text((x_l, y + 40), "TOTAL", font=fT, fill=tk, anchor="lm")
    d.text((x_r, y + 40), D_["total"], font=fT, fill=tk, anchor="rm")
    y += 80 + 40
    import random                                                     # svītrkods (dekoratīvs, vienmēr vienāds)
    r_ = random.Random(7)
    x = 120
    while x < pw - 120:
        w_ = r_.choice((3, 3, 5, 7))
        d.rectangle([x, y, x + w_, y + 70], fill=tk)
        x += w_ + r_.choice((4, 5, 7))
    y += 70 + 34
    d.text((pw / 2, y), "*** NO REFUNDS ***", font=fs, fill=(90, 94, 104, 255), anchor="mm")
    P = P.rotate(-2.2, resample=Image.BICUBIC, expand=True)
    sc = min(1.0, 800 / P.height)
    if sc < 1:
        P = P.resize((int(P.width * sc), int(P.height * sc)), Image.LANCZOS)
    _likt_ar_enu(im, P, 540 - P.width / 2, 205 + (790 - P.height) / 2, 26, 0.9)
    _jautajums(im, c["rindas"], kr, 1225 if len(c["rindas"]) > 2 else 1190)
    im.alpha_composite(B._ns_vinjete())
    _tag(im, c["tag"], kr)
    return im.convert("RGB")


# ---------------------------------------------------------------- J · tikai teksts
def _j_rindas(rindas, maks=250, platums=900, augst=1000):
    """Jautājuma vārdus sadala 2–5 rindās tā, lai burti būtu pēc iespējas lielāki."""
    vardi = " ".join(str(r) for r in rindas).split()[:8]
    if not vardi:
        return [], maks
    lab = ([vardi], 90)
    from itertools import combinations
    for k in range(2, min(5, len(vardi)) + 1):
        for gr in combinations(range(1, len(vardi)), k - 1):
            g = (0,) + gr + (len(vardi),)
            rr = [" ".join(vardi[g[i]:g[i + 1]]) for i in range(k)]
            izm = min(maks, int(augst / (1.04 * k)))
            while izm > 90 and max(S.fonts("bold", izm).getlength(r) + (44 if r is rr[-1] else 0) for r in rr) > platums:
                izm -= 4
            if izm > lab[1] or (izm == lab[1] and k > len(lab[0])):
                lab = (rr, izm)
    return lab


def sikts_J(c):
    kr = tuple(c["kr"])
    np = S.np
    a = np.linspace(0, 1, S.H)[:, None, None]
    g = np.array(_gaisaks(kr, 0.08)) * (1 - a) + np.array(_tumsaks(kr, 0.12)) * a
    im = Image.fromarray(g.repeat(S.W, 1).astype(np.uint8), "RGB").convert("RGBA")
    d = ImageDraw.Draw(im)
    _tag(im, c["tag"], kr, tumss=True)
    rindas, izm = _j_rindas(c["rindas"])
    f = S.fonts("bold", izm)
    lh = int(izm * 1.04)
    y = 250 + max(0, (1030 - lh * len(rindas)) / 2)
    for i, r in enumerate(rindas):
        bb = d.textbbox((80, y), r, font=f, anchor="lt")
        if i == len(rindas) - 1:
            d.rectangle([bb[0] - 22, bb[1] - 20, bb[2] + 22, bb[3] + 24], fill=TUMSS + (255,))
            d.text((80, y), r, font=f, fill=kr + (255,), anchor="lt")
        else:
            d.text((80, y), r, font=f, fill=TUMSS + (255,), anchor="lt")
        y += lh
    apa = _apaksas_teksts(c)
    if apa:
        fa = _fonts_lidz(apa, "black", 46, 920)
        d.line([(80, 1338), (200, 1338)], fill=TUMSS + (255,), width=8)
        d.text((80, 1372), apa, font=fa, fill=TUMSS + (255,), anchor="lt")
    return im.convert("RGB")


ZIMETAJI = {"A": sikts_A, "B": sikts_B, "D": sikts_D, "E": sikts_E, "F": sikts_F, "J": sikts_J, "K": sikts_K}


# ---------------------------------------------------------------- konteksts, pieejamība, izvēle
def konteksts(s):
    th = s.get("thumb") or {}
    tag = re.sub(r"\s+", " ", str(th.get("tag", ""))).strip()
    veids = _veids(tag)
    nsl = (s.get("intro") or {}).get("noslepums")
    if not veids or not nsl or not nsl.get("krekli"):
        return None                                                   # bez noslēpuma / tiesneši – vecais sīktēls
    krekli = [(str(k), str(v or "")) for k, v in nsl["krekli"]]
    c = {"s": s, "th": th, "tag": tag, "veids": veids, "kr": SERIJAS[veids][0], "krekli": krekli,
         "rindas": list((nsl.get("q2") or [()])[0]) or list(th.get("hook") or []), "nsl": nsl}
    c["varonis"] = _varonis(s, krekli) if len(krekli) == 1 else None
    return c


def pieejami(c):
    """Izkārtojumi, kuriem šim video ir dati."""
    v = c["veids"]
    out = []
    for k in SECIBA.get(v, "") + "J":
        try:
            if k == "A":
                ok = True
            elif k == "B":
                ok = len(c["krekli"]) <= 3 and all(n for _, n in c["krekli"])   # komandām krāsas atklātu atbildi
            elif k == "D":
                c["_D"] = _d_dati(c) if len(c["krekli"]) == 1 else None
                ok = bool(c["_D"])
            elif k == "E":
                c["_E"] = _e_dati(c)
                ok = bool(c["_E"])
            elif k == "F":
                c["_F"] = _f_dati(c) if len(c["krekli"]) == 1 else None
                ok = bool(c["_F"])
            elif k == "K":
                c["_K"] = _k_dati(c) if v in ("xg_atsk", "fan_atsk") else None
                ok = bool(c["_K"])
            else:
                ok = k == "J"
        except Exception as ex:                                       # noqa: BLE001
            print(f"  (sīktēls {k}: dati – {type(ex).__name__}: {ex})")
            ok = False
        if ok and k not in out:
            out.append(k)
    return out


def ielasit_vesturi(cels):
    try:
        v = json.load(open(cels, encoding="utf-8")) if cels and os.path.exists(cels) else []
        return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []
    except Exception:                                                 # noqa: BLE001
        return []


def izveleties(veids, pieej, vesture, piespiests=None):
    """Kurš izkārtojums šim video. vesture – video_info.json ieraksti (vecākais pirmais)."""
    if piespiests and piespiests in pieej:
        return piespiests
    ar = [x for x in vesture if x.get("sikts")]
    ped = ar[-1]["sikts"] if ar else None
    kops_j = next((i for i, x in enumerate(reversed(ar)) if x["sikts"] == "J"), None)
    if "J" in pieej and ped != "J" and len(ar) >= J_PEC and (kops_j is None or kops_j >= J_PEC):
        return "J"
    seq = [k for k in SECIBA.get(veids, "") if k in pieej]
    if not seq:
        return None
    sv = [x["sikts"] for x in ar if x.get("sikts_veids") == veids]
    pedeja = {k: max((i for i, z in enumerate(sv) if z == k), default=-1) for k in seq}
    kand = sorted(seq, key=lambda k: (pedeja[k], seq.index(k)))
    ped2 = [x["sikts"] for x in ar[-2:]]                              # kanāla tīklā blakus: ne kā 2 iepriekšējiem
    return next((k for k in kand if k not in ped2), None) or next((k for k in kand if k != ped), kand[0])


def izveidot(modulis, s, vestures_cels=None, piespiests=None, visi=True):
    """→ (kods, attēls, {kods: attēls}, veids) vai None (tad paliek vecais sīktēls).
    modulis – ShortsB (palīgfunkcijas, krekli); visi=True – uzzīmē arī pārējos variantus (sikteli\\ mapei)."""
    global B, S
    B, S = modulis, modulis.S
    c = konteksts(s)
    if not c:
        return None
    pieej = pieejami(c)
    if piespiests and piespiests not in pieej:
        print(f"SĪKTĒLS: --sikts {piespiests} šim video nav pieejams (ir: {', '.join(pieej)}) – izvēlos pats")
    kods = izveleties(c["veids"], pieej, ielasit_vesturi(vestures_cels), piespiests)
    if not kods:
        return None
    alt = {}
    for k in ([kods] + [x for x in pieej if x != kods]) if visi else [kods]:
        try:
            alt[k] = ZIMETAJI[k](c)
        except Exception as ex:                                       # noqa: BLE001
            print(f"  (sīktēls {k}: {type(ex).__name__}: {ex})")
    if kods not in alt:
        kods = next(iter(alt), None)
        if not kods:
            return None
    print(f"SĪKTĒLS: {kods} ({NOSAUKUMI.get(kods, kods)}) – {SERIJAS[c['veids']][1]}; varianti: {', '.join(alt)}")
    return kods, alt[kods], alt, c["veids"]
