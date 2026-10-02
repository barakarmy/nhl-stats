"""
NHL komandu lokācijas, attālumi starp pilsētām un aptuvenais ceļojuma laiks.
Paredzēts kā viens no faktoriem prognožu modulim (atpūta, ceļojuma garums, laika joslu maiņa).

Galvenās funkcijas:
  attalums_km(a, b)                      - lielā apļa attālums starp divu komandu pilsētām (km)
  celojuma_laiks_h(km)                   - aptuvenais ceļojuma laiks stundās (autobuss līdz ~400 km, citādi lidojums)
  laika_joslu_starpiba_h(a, b, kad)      - laika joslu starpība stundās (pozitīva = b atrodas austrumos no a)
  celojums(a, b, kad)                    - viss kopā: km, laiks, laika joslu starpība, ceļojuma veids, robežas šķērsošana
  celojuma_faktori(df, komanda, vieta, sakums)  - komandas atpūta un ceļojums pirms konkrētas spēles (no sezonas spēļu tabulas)
  speles_faktori(df, majas, viesi, sakums)      - abu komandu faktori vienai spēlei
  celojuma_slodze(f)                     - vienkāršs slodzes indekss (heiristika, svarus var mainīt)
  attalumu_tabula()                      - 32 × 32 attālumu tabula (pandas DataFrame)

Piezīmes:
  • Koordinātas ir pilsētu/halles aptuvenas (precizitāte ~1-2 km), tāpēc attālumiem ir ~1% kļūda.
  • Ceļojuma laiks ir novērtējums (čartera lidojums ~800 km/h + 45 min pacelšanās/nosēšanās; īsos braucienos autobuss),
    tas neietver gaidīšanu lidostā, viesnīcu u.c.
  • Arēnu nosaukumi ir informatīvi un var mainīties; aprēķiniem tie nav vajadzīgi.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

# ----------------------------------------------------------------------------
# KOMANDU LOKĀCIJAS
# ----------------------------------------------------------------------------
LOKACIJAS = {
    # --- Austrumu konference ---
    "BOS": {"pilseta": "Boston", "arena": "TD Garden", "lat": 42.3662, "lon": -71.0621, "tz": "America/New_York", "valsts": "ASV"},
    "BUF": {"pilseta": "Buffalo", "arena": "KeyBank Center", "lat": 42.8750, "lon": -78.8764, "tz": "America/New_York", "valsts": "ASV"},
    "CAR": {"pilseta": "Raleigh", "arena": "Lenovo Center", "lat": 35.8033, "lon": -78.7219, "tz": "America/New_York", "valsts": "ASV"},
    "CBJ": {"pilseta": "Columbus", "arena": "Nationwide Arena", "lat": 39.9692, "lon": -83.0061, "tz": "America/New_York", "valsts": "ASV"},
    "DET": {"pilseta": "Detroit", "arena": "Little Caesars Arena", "lat": 42.3411, "lon": -83.0553, "tz": "America/Detroit", "valsts": "ASV"},
    "FLA": {"pilseta": "Sunrise (Florida)", "arena": "Amerant Bank Arena", "lat": 26.1584, "lon": -80.3256, "tz": "America/New_York", "valsts": "ASV"},
    "MTL": {"pilseta": "Montréal", "arena": "Bell Centre", "lat": 45.4961, "lon": -73.5693, "tz": "America/Toronto", "valsts": "Kanāda"},
    "NJD": {"pilseta": "Newark", "arena": "Prudential Center", "lat": 40.7336, "lon": -74.1711, "tz": "America/New_York", "valsts": "ASV"},
    "NYI": {"pilseta": "Elmont (Ņujorka)", "arena": "UBS Arena", "lat": 40.7114, "lon": -73.7257, "tz": "America/New_York", "valsts": "ASV"},
    "NYR": {"pilseta": "Ņujorka", "arena": "Madison Square Garden", "lat": 40.7505, "lon": -73.9934, "tz": "America/New_York", "valsts": "ASV"},
    "OTT": {"pilseta": "Ottawa", "arena": "Canadian Tire Centre", "lat": 45.2969, "lon": -75.9272, "tz": "America/Toronto", "valsts": "Kanāda"},
    "PHI": {"pilseta": "Filadelfija", "arena": "Wells Fargo Center", "lat": 39.9012, "lon": -75.1720, "tz": "America/New_York", "valsts": "ASV"},
    "PIT": {"pilseta": "Pitsburga", "arena": "PPG Paints Arena", "lat": 40.4395, "lon": -79.9892, "tz": "America/New_York", "valsts": "ASV"},
    "TBL": {"pilseta": "Tampa", "arena": "Amalie Arena", "lat": 27.9428, "lon": -82.4519, "tz": "America/New_York", "valsts": "ASV"},
    "TOR": {"pilseta": "Toronto", "arena": "Scotiabank Arena", "lat": 43.6435, "lon": -79.3791, "tz": "America/Toronto", "valsts": "Kanāda"},
    "WSH": {"pilseta": "Vašingtona", "arena": "Capital One Arena", "lat": 38.8981, "lon": -77.0209, "tz": "America/New_York", "valsts": "ASV"},
    # --- Rietumu konference ---
    "ANA": {"pilseta": "Anaheim", "arena": "Honda Center", "lat": 33.8078, "lon": -117.8765, "tz": "America/Los_Angeles", "valsts": "ASV"},
    "CGY": {"pilseta": "Calgary", "arena": "Scotiabank Saddledome", "lat": 51.0375, "lon": -114.0519, "tz": "America/Edmonton", "valsts": "Kanāda"},
    "CHI": {"pilseta": "Čikāga", "arena": "United Center", "lat": 41.8807, "lon": -87.6742, "tz": "America/Chicago", "valsts": "ASV"},
    "COL": {"pilseta": "Denvera", "arena": "Ball Arena", "lat": 39.7487, "lon": -105.0077, "tz": "America/Denver", "valsts": "ASV"},
    "DAL": {"pilseta": "Dalasa", "arena": "American Airlines Center", "lat": 32.7905, "lon": -96.8103, "tz": "America/Chicago", "valsts": "ASV"},
    "EDM": {"pilseta": "Edmontona", "arena": "Rogers Place", "lat": 53.5469, "lon": -113.4979, "tz": "America/Edmonton", "valsts": "Kanāda"},
    "LAK": {"pilseta": "Losandželosa", "arena": "Crypto.com Arena", "lat": 34.0430, "lon": -118.2673, "tz": "America/Los_Angeles", "valsts": "ASV"},
    "MIN": {"pilseta": "Sentpola (Minesota)", "arena": "Grand Casino Arena", "lat": 44.9448, "lon": -93.1010, "tz": "America/Chicago", "valsts": "ASV"},
    "NSH": {"pilseta": "Našvila", "arena": "Bridgestone Arena", "lat": 36.1592, "lon": -86.7785, "tz": "America/Chicago", "valsts": "ASV"},
    "SEA": {"pilseta": "Sietla", "arena": "Climate Pledge Arena", "lat": 47.6221, "lon": -122.3540, "tz": "America/Los_Angeles", "valsts": "ASV"},
    "SJS": {"pilseta": "Sanhosē", "arena": "SAP Center", "lat": 37.3328, "lon": -121.9013, "tz": "America/Los_Angeles", "valsts": "ASV"},
    "STL": {"pilseta": "Sentluisa", "arena": "Enterprise Center", "lat": 38.6268, "lon": -90.2026, "tz": "America/Chicago", "valsts": "ASV"},
    "UTA": {"pilseta": "Soltleiksitija", "arena": "Delta Center", "lat": 40.7683, "lon": -111.9011, "tz": "America/Denver", "valsts": "ASV"},
    "VAN": {"pilseta": "Vankūvera", "arena": "Rogers Arena", "lat": 49.2778, "lon": -123.1089, "tz": "America/Vancouver", "valsts": "Kanāda"},
    "VGK": {"pilseta": "Lasvegasa", "arena": "T-Mobile Arena", "lat": 36.1029, "lon": -115.1784, "tz": "America/Los_Angeles", "valsts": "ASV"},
    "WPG": {"pilseta": "Vinipega", "arena": "Canada Life Centre", "lat": 49.8928, "lon": -97.1436, "tz": "America/Winnipeg", "valsts": "Kanāda"},
}

# Ceļojuma laika modelis (aptuvens)
ZEMES_RADIUSS_KM = 6371.0088
AUTOBUSA_LIMITS_KM = 400        # līdz šim attālumam komanda brauc ar autobusu
AUTOBUSA_ATRUMS_KMH = 80
LIDOJUMA_ATRUMS_KMH = 800       # čartera lidojuma kruīza ātrums
LIDOJUMA_PAPILDLAIKS_H = 0.75   # pacelšanās, nosēšanās, rulēšana
SPELES_ILGUMS_H = 2.5           # aptuvens spēles ilgums (atpūtas aprēķinam)


def _kods(x):
    k = str(x).upper()
    if k not in LOKACIJAS:
        raise KeyError(f"Nezināma komanda: {x}")
    return k


# ----------------------------------------------------------------------------
# ATTĀLUMS, LAIKS, LAIKA JOSLAS
# ----------------------------------------------------------------------------
def attalums_km(a, b):
    """Lielā apļa (haversine) attālums starp divu komandu pilsētām kilometros."""
    la, lb = LOKACIJAS[_kods(a)], LOKACIJAS[_kods(b)]
    if _kods(a) == _kods(b):
        return 0.0
    f1, f2 = radians(la["lat"]), radians(lb["lat"])
    dfi, dla = f2 - f1, radians(lb["lon"] - la["lon"])
    h = sin(dfi / 2) ** 2 + cos(f1) * cos(f2) * sin(dla / 2) ** 2
    return 2 * ZEMES_RADIUSS_KM * asin(sqrt(h))


def celojuma_laiks_h(km):
    """Aptuvenais ceļojuma laiks stundās: autobuss līdz ~400 km, citādi čartera lidojums."""
    if km <= 0:
        return 0.0
    if km <= AUTOBUSA_LIMITS_KM:
        return km / AUTOBUSA_ATRUMS_KMH + 0.25
    return LIDOJUMA_PAPILDLAIKS_H + km / LIDOJUMA_ATRUMS_KMH


def laika_joslu_starpiba_h(a, b, kad=None):
    """Laika joslu starpība (b - a) stundās konkrētā brīdī; pozitīva = b atrodas austrumos no a."""
    kad = kad or datetime.now(timezone.utc)
    if kad.tzinfo is None:
        kad = kad.replace(tzinfo=timezone.utc)
    oa = kad.astimezone(ZoneInfo(LOKACIJAS[_kods(a)]["tz"])).utcoffset()
    ob = kad.astimezone(ZoneInfo(LOKACIJAS[_kods(b)]["tz"])).utcoffset()
    return (ob - oa).total_seconds() / 3600


def celojums(a, b, kad=None):
    """Ceļojums no komandas a pilsētas uz komandas b pilsētu."""
    km = attalums_km(a, b)
    return {
        "no": _kods(a), "uz": _kods(b),
        "km": round(km, 0),
        "laiks_h": round(celojuma_laiks_h(km), 1),
        "veids": "nav" if km == 0 else ("autobuss" if km <= AUTOBUSA_LIMITS_KM else "lidojums"),
        "laika_joslu_starpiba_h": laika_joslu_starpiba_h(a, b, kad),
        "sķērso_robežu": LOKACIJAS[_kods(a)]["valsts"] != LOKACIJAS[_kods(b)]["valsts"],
    }


def attalumu_tabula():
    """32 × 32 attālumu tabula kilometros (pandas DataFrame)."""
    import pandas as pd
    kodi = sorted(LOKACIJAS)
    return pd.DataFrame([[round(attalums_km(a, b)) for b in kodi] for a in kodi], index=kodi, columns=kodi)


# ----------------------------------------------------------------------------
# ATPŪTA UN CEĻOJUMS PIRMS SPĒLES (no sezonas spēļu tabulas)
# ----------------------------------------------------------------------------
_ET = ZoneInfo("America/New_York")
_RIGA = ZoneInfo("Europe/Riga")


def _spelu_sakums(x):
    """Spēļu sākuma laiks (tz-aware). Ja tā nav (vecais formāts), tiek lietots datums plkst. 03:00 pēc Rīgas laika."""
    import pandas as pd
    sak = pd.to_datetime(x["sakums"], utc=True, errors="coerce")
    rezerve = pd.to_datetime(x["datums"], errors="coerce").dt.tz_localize(_RIGA, nonexistent="shift_forward",
                                                                          ambiguous="NaT") + pd.Timedelta(hours=3)
    return sak.fillna(rezerve.dt.tz_convert("UTC"))


def celojuma_faktori(df, komanda, majas_komanda, sakums):
    """
    Komandas atpūta un ceļojums pirms spēles, kas notiks pie `majas_komanda` mājām laikā `sakums` (tz-aware datetime).
    df: sezonas spēļu tabula ar kolonnām komanda, pretinieks, majas, sakums, datums (datu_apstrade.sagatavot_vienoto_tabulu).
    """
    import pandas as pd
    komanda, majas_komanda = _kods(komanda), _kods(majas_komanda)
    sakums = pd.Timestamp(sakums)
    sakums = sakums.tz_localize("UTC") if sakums.tzinfo is None else sakums.tz_convert("UTC")
    tuksi = {"iepriekspeja_vieta": None, "km": None, "laiks_h": None, "laika_joslu_starpiba_h": None,
             "stundas_kops_pedejas": None, "dienas_starp_spelem": None, "back_to_back": False,
             "speles_pedejas_7_dienas": 0, "celo": None, "majas_atgriesanas": False}
    x = df[df["komanda"] == komanda].copy()
    if x.empty:
        return tuksi
    x["_sak"] = _spelu_sakums(x)
    agrak = x[x["_sak"] < sakums].sort_values("_sak")
    if agrak.empty:
        return tuksi
    p = agrak.iloc[-1]
    prev_vieta = komanda if int(p["majas"]) == 1 else str(p["pretinieks"]).upper()
    if prev_vieta not in LOKACIJAS:
        return tuksi
    km = attalums_km(prev_vieta, majas_komanda)
    dienas = (sakums.tz_convert(_ET).date() - p["_sak"].tz_convert(_ET).date()).days
    pedejas7 = agrak[agrak["_sak"] >= sakums - pd.Timedelta(days=7)]
    return {
        "iepriekspeja_vieta": prev_vieta,
        "km": round(km, 0),
        "laiks_h": round(celojuma_laiks_h(km), 1),
        "laika_joslu_starpiba_h": laika_joslu_starpiba_h(prev_vieta, majas_komanda, sakums.to_pydatetime()),
        "stundas_kops_pedejas": round((sakums - p["_sak"]).total_seconds() / 3600, 1),
        "dienas_starp_spelem": dienas,
        "back_to_back": dienas == 1,
        "speles_pedejas_7_dienas": int(len(pedejas7)),
        "celo": km > 0,
        "majas_atgriesanas": komanda == majas_komanda and int(p["majas"]) == 0,
    }


def speles_faktori(df, majas, viesi, sakums):
    """Abu komandu atpūtas un ceļojuma faktori vienai spēlei + attālums starp pilsētām."""
    return {"majas": celojuma_faktori(df, majas, majas, sakums),
            "viesi": celojuma_faktori(df, viesi, majas, sakums),
            "starp_pilsetam": celojums(viesi, majas, sakums.to_pydatetime() if hasattr(sakums, "to_pydatetime") else sakums)}


# ----------------------------------------------------------------------------
# VIENKĀRŠS SLODZES INDEKSS (heiristika; svarus var pielāgot)
# ----------------------------------------------------------------------------
SLODZES_SVARI = {
    "back_to_back": 2.0,          # spēle nākamajā dienā pēc iepriekšējās
    "km_uz_1000": 0.5,            # par katriem 1000 km ceļojuma
    "laika_josla_h": 0.4,         # par katru stundu laika joslu maiņas (absolūti)
    "daudz_speles_7_dienas": 1.0, # 4 vai vairāk spēles pēdējās 7 dienās
}


def celojuma_slodze(f, svari=None):
    """
    Slodzes indekss vienas komandas faktoriem (rezultāts no celojuma_faktori): jo lielāks, jo vairāk nogurums.
    Tā ir vienkārša heiristika, nevis pierādīta ietekme - svarus vajadzētu kalibrēt uz vēstures datiem.
    """
    s = {**SLODZES_SVARI, **(svari or {})}
    if f.get("km") is None:
        return 0.0
    punkti = s["back_to_back"] * bool(f["back_to_back"])
    punkti += s["km_uz_1000"] * f["km"] / 1000
    punkti += s["laika_josla_h"] * abs(f["laika_joslu_starpiba_h"] or 0)
    punkti += s["daudz_speles_7_dienas"] * (f["speles_pedejas_7_dienas"] >= 4)
    return round(punkti, 2)


if __name__ == "__main__":
    for a, b in (("NJD", "PHI"), ("NYR", "LAK"), ("VAN", "FLA"), ("EDM", "CGY"), ("TOR", "MTL"), ("SEA", "VAN")):
        c = celojums(a, b)
        print(f"{a} → {b}: {c['km']:.0f} km, ~{c['laiks_h']} h ({c['veids']}), laika joslas: {c['laika_joslu_starpiba_h']:+.0f} h")
