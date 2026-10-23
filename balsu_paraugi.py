"""
balsu_paraugi.py – noklausies dažādas AI balsis, pirms izvēlies vienu Shorts video.

Izveido mapi video_test\\balsis\\ ar MP3 failu katrai balsij (viens un tas pats teksts),
lai tās var ērti salīdzināt. Pēc tam izvēlēto balsi lieto ar --balss, piem.:
    python ShortsB.py --veids tiesnesi --balss en-US-GuyNeural

Lietošana:
    python balsu_paraugi.py                      ieteiktās balsis (sporta stilam)
    python balsu_paraugi.py --visas              VISAS angļu balsis (ASV, UK, Austrālija u.c., ~50)
    python balsu_paraugi.py --balsis en-US-GuyNeural,en-GB-RyanNeural
    python balsu_paraugi.py --atrums +15%        ātrāk (shorts.py lieto +8%)
    python balsu_paraugi.py --teksts "Your own sentence here."
"""
import argparse
import asyncio
import os

IETEIKTAS = [
    "en-US-AndrewNeural",       # mierīgs, dabisks
    "en-US-GuyNeural",          # enerģisks, "ziņu diktora" stils
    "en-US-ChristopherNeural",  # dziļš, nopietns
    "en-US-EricNeural",         # skaidrs, neitrāls
    "en-US-BrianNeural",        # jauneklīgs, sarunvalodas
    "en-US-RogerNeural",        # dzīvs, sporta komentētāja sajūta
    "en-US-SteffanNeural",      # mierīgs
    "en-GB-RyanNeural",         # britu akcents
    "en-AU-WilliamNeural",      # austrāliešu akcents
    "en-CA-LiamNeural",         # kanādiešu akcents (hokejs!) – ShortsB noklusējums
    "en-US-AriaNeural",         # sieviete, enerģiska
    "en-US-JennyNeural",        # sieviete, mierīga
    "en-US-EmmaNeural",         # sieviete, sarunvalodas
]
TEKSTS = ("October referee report. Who called the most penalties in the NHL this month? "
          "The strictest: Cody Beach, ten point six penalties per game. Is your team's ref on this list?")


async def ierunat(balss, teksts, atrums, fails):
    import edge_tts
    await edge_tts.Communicate(teksts, balss, rate=atrums).save(fails)


async def visas_anglu():
    import edge_tts
    return sorted(v["ShortName"] for v in await edge_tts.list_voices() if v["Locale"].startswith("en-"))


def main():
    ap = argparse.ArgumentParser(description="AI balsu paraugi Shorts video")
    ap.add_argument("--visas", action="store_true", help="visas angļu valodas balsis")
    ap.add_argument("--balsis", default="", help="konkrētas balsis ar komatu")
    ap.add_argument("--atrums", default="+8%", help="runas ātrums, piem. +0%%, +8%%, +15%%")
    ap.add_argument("--teksts", default=TEKSTS)
    a = ap.parse_args()
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("Nav edge-tts → palaid:  python -m pip install edge-tts")
        return 1
    if a.balsis:
        balsis = [b.strip() for b in a.balsis.split(",") if b.strip()]
    elif a.visas:
        balsis = asyncio.run(visas_anglu())
    else:
        balsis = IETEIKTAS
    mape = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_test", "balsis")
    os.makedirs(mape, exist_ok=True)
    ok = 0
    for i, b in enumerate(balsis, 1):
        fails = os.path.join(mape, f"{i:02d}_{b}.mp3")
        try:
            asyncio.run(ierunat(b, a.teksts, a.atrums, fails))
            ok += 1
            print(f"  ✓ {b}")
        except Exception as ex:                                       # noqa: BLE001
            print(f"  ✗ {b}: {type(ex).__name__}: {ex}")
    print(f"\nGatavs: {ok} paraugi mapē {os.path.relpath(mape)}\\ – atver un noklausies.")
    print("Izvēlēto balsi lieto:  python ShortsB.py --veids ... --balss <nosaukums>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
