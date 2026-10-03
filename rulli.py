"""
Komandu izvēle ar vertikāliem rullīšiem (kā datorspēlē NHL): abās pusēs ritinās komandu logotipi, pa vidu ir uzraksts "VS".
Izvēlēta ir tā komanda, kuras logotips ir izcelts rāmī vidū. Ritina ar peles ritenīti, ar pirkstu vai velkot ar peli; klikšķis uz
blakus logotipa to ieritina vidū; bultiņas augšup/lejup maina izvēli ar tastatūru.

Tas ir Streamlit pielāgots komponents, rakstīts kā vienkāršs HTML/JS (bez būvēšanas). HTML tiek ierakstīts pagaidu mapē izpildes laikā,
tāpēc papildu failu augšupielādēt nav jāpiegādā: pietiek ar šo moduli.
"""
import os
import tempfile

import streamlit.components.v1 as components

_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root { --item: 104px; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: transparent; font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; overflow: hidden; -webkit-user-select: none; user-select: none; }
.stage { display: flex; align-items: flex-start; justify-content: center; gap: clamp(8px, 3vw, 30px); padding: 10px 4px 8px; }
.col { display: flex; flex-direction: column; align-items: center; gap: 10px; width: clamp(124px, 36vw, 200px); }
.reel-box { position: relative; width: 100%; height: calc(var(--item) * 3); border-radius: 22px; overflow: hidden;
  background: linear-gradient(180deg, #08142e, #11285a 50%, #08142e); border: 2px solid #2b4a8f;
  box-shadow: inset 0 0 34px rgba(0,0,0,.65), 0 10px 26px rgba(8,20,50,.45); }
.reel { position: absolute; inset: 0; overflow-y: scroll; scroll-snap-type: y mandatory; scrollbar-width: none; -ms-overflow-style: none;
  overscroll-behavior: contain; touch-action: pan-y; cursor: grab; outline: none; }
.reel::-webkit-scrollbar { display: none; }
.reel.drag { cursor: grabbing; scroll-snap-type: none; }
.sp { height: var(--item); flex: none; }
.it { height: var(--item); display: flex; align-items: center; justify-content: center; scroll-snap-align: center; scroll-snap-stop: always; }
.tile { width: calc(var(--item) * .84); height: calc(var(--item) * .84); border-radius: 20px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(145deg, #fbfdff, #d3e3fa); box-shadow: 0 3px 12px rgba(0,0,0,.4); will-change: transform; }
.tile img { width: 76%; height: 76%; object-fit: contain; pointer-events: none; -webkit-user-drag: none; }
.mask { position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(180deg, rgba(5,14,38,.93) 0, rgba(5,14,38,0) 32%, rgba(5,14,38,0) 68%, rgba(5,14,38,.93) 100%); }
.frame { position: absolute; left: 7px; right: 7px; top: var(--item); height: var(--item); border: 3px solid #38bdf8; border-radius: 22px; pointer-events: none;
  box-shadow: 0 0 18px rgba(56,189,248,.7), inset 0 0 16px rgba(56,189,248,.28); }
.name { min-height: 2.5rem; max-width: 100%; padding: .4rem .8rem; border-radius: 14px; background: #0b1d3f; color: #e8f1ff; font-weight: 700; font-size: .92rem;
  text-align: center; line-height: 1.2; display: flex; align-items: center; justify-content: center; }
.vsbox { height: calc(var(--item) * 3); display: flex; align-items: center; }
.vs { font-family: 'Arial Black', Impact, 'Segoe UI Black', sans-serif; font-weight: 900; font-size: clamp(1.7rem, 6.2vw, 2.7rem); color: #ffffff; letter-spacing: .06em;
  padding: .15em .45em; border-radius: 16px; background: linear-gradient(145deg, #11285a, #08142e); border: 2px solid #2b4a8f;
  text-shadow: 0 0 14px rgba(56,189,248,.95), 0 2px 0 #08142e; box-shadow: 0 8px 20px rgba(8,20,50,.4); }
</style></head>
<body>
<div class="stage">
  <div class="col"><div class="reel-box"><div class="reel" id="ra" tabindex="0"></div><div class="mask"></div><div class="frame"></div></div><div class="name" id="na">&nbsp;</div></div>
  <div class="vsbox"><div class="vs">VS</div></div>
  <div class="col"><div class="reel-box"><div class="reel" id="rb" tabindex="0"></div><div class="mask"></div><div class="frame"></div></div><div class="name" id="nb">&nbsp;</div></div>
</div>
<script>
(function () {
  var ITEM = 104, teams = [], reels = {}, lastSent = '', lastArgs = '', built = false, spinning = 0, timer = null;
  function send(type, data) { window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data), '*'); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function itemSize() { return parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--item')) || 104; }
  var lastH = 0;
  function frame() {
    var h = Math.ceil(document.querySelector('.stage').getBoundingClientRect().height) + 2;
    if (h !== lastH) { lastH = h; send('streamlit:setFrameHeight', { height: h }); }
  }

  function build(el) {
    el.innerHTML = '';
    var sp = function () { var d = document.createElement('div'); d.className = 'sp'; return d; };
    el.appendChild(sp());
    teams.forEach(function (t, i) {
      var it = document.createElement('div'); it.className = 'it'; it.dataset.i = i;
      var tile = document.createElement('div'); tile.className = 'tile';
      var img = document.createElement('img'); img.src = t.logo; img.alt = t.kods; img.draggable = false;
      tile.appendChild(img); it.appendChild(tile); el.appendChild(it);
    });
    el.appendChild(sp());
  }
  function idx(el) { return clamp(Math.round(el.scrollTop / ITEM), 0, teams.length - 1); }
  function paint(el) {
    var c = el.scrollTop / ITEM, items = el.querySelectorAll('.it');
    for (var i = Math.max(0, Math.floor(c) - 3); i < Math.min(items.length, Math.ceil(c) + 4); i++) {
      var d = Math.abs(i - c), tile = items[i].firstChild;
      tile.style.transform = 'scale(' + Math.max(.52, 1 - d * .24).toFixed(3) + ')';
      tile.style.opacity = Math.max(.22, 1 - d * .38).toFixed(3);
    }
  }
  function labels() {
    document.getElementById('na').textContent = teams[idx(reels.a)].nos;
    document.getElementById('nb').textContent = teams[idx(reels.b)].nos;
  }
  function emit() {
    var v = { a: teams[idx(reels.a)].kods, b: teams[idx(reels.b)].kods }, s = JSON.stringify(v);
    if (s !== lastSent) { lastSent = s; send('streamlit:setComponentValue', { value: v, dataType: 'json' }); }
  }
  function onScroll(el) {
    paint(el); labels();
    clearTimeout(timer);
    timer = setTimeout(function () { reels.a._tgt = reels.b._tgt = undefined; if (!spinning) emit(); }, 160);
  }
  function goTo(el, i, smooth) { el.scrollTo({ top: clamp(i, 0, teams.length - 1) * ITEM, behavior: smooth ? 'smooth' : 'auto' }); }

  // "griešanās": rullītis ātri izripo no citas vietas līdz izvēlētajai komandai
  function spin(el, target, ms) {
    var n = teams.length, from = (target + Math.floor(n / 2) + 3) % n, t0 = null, a = from * ITEM, b = target * ITEM;
    el.style.scrollSnapType = 'none'; spinning++;
    el.scrollTop = a;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var k = clamp((ts - t0) / ms, 0, 1), e = 1 - Math.pow(1 - k, 3);
      el.scrollTop = a + (b - a) * e;
      if (k < 1) { requestAnimationFrame(step); } else { el.style.scrollSnapType = ''; spinning--; el.scrollTop = b; onScroll(el); emit(); }
    }
    requestAnimationFrame(step);
  }

  function attach(el) {
    el.addEventListener('scroll', function () { onScroll(el); }, { passive: true });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        var base = el._tgt === undefined ? idx(el) : el._tgt;
        el._tgt = clamp(base + (e.key === 'ArrowDown' ? 1 : -1), 0, teams.length - 1);
        goTo(el, el._tgt, true);
      }
    });
    var y0 = 0, s0 = 0, down = false, moved = 0;
    el.addEventListener('pointerdown', function (e) {
      if (e.pointerType !== 'mouse' || e.button !== 0) return;
      down = true; moved = 0; y0 = e.clientY; s0 = el.scrollTop; el.classList.add('drag'); el.setPointerCapture(e.pointerId);
    });
    el.addEventListener('pointermove', function (e) { if (!down) return; moved = Math.max(moved, Math.abs(e.clientY - y0)); el.scrollTop = s0 - (e.clientY - y0); });
    function up(e) {
      if (!down) return; down = false; el.classList.remove('drag');
      try { el.releasePointerCapture(e.pointerId); } catch (x) {}
      goTo(el, Math.round(el.scrollTop / ITEM), true);
    }
    el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    el.addEventListener('click', function (e) {
      if (moved > 5) return;
      var y = e.clientY - el.getBoundingClientRect().top;               // klikšķa vieta rullīša iekšienē
      goTo(el, Math.round((y + el.scrollTop - ITEM * 1.5) / ITEM), true);   // i-tā logotipa centrs ir y = ITEM*1.5 + i*ITEM - scrollTop
    });
  }

  function onRender(args) {
    ITEM = itemSize();
    var key = JSON.stringify(args.sakuma || []);
    if (!built) {
      teams = args.komandas || [];
      reels.a = document.getElementById('ra'); reels.b = document.getElementById('rb');
      build(reels.a); build(reels.b); attach(reels.a); attach(reels.b);
      built = true; frame();
      var ix = function (k) { var i = teams.findIndex(function (t) { return t.kods === k; }); return i < 0 ? 0 : i; };
      var s = args.sakuma || [];
      setTimeout(function () {
        paint(reels.a); paint(reels.b);
        spin(reels.a, ix(s[0]), 900); spin(reels.b, ix(s[1]), 1150);
      }, 60);
      lastArgs = key;
    } else if (key !== lastArgs) {              // Python nomainīja sākuma izvēli: pārliek bez griešanās
      lastArgs = key;
      var s2 = args.sakuma || [];
      [reels.a, reels.b].forEach(function (r, n) { var i = teams.findIndex(function (t) { return t.kods === s2[n]; }); if (i >= 0) goTo(r, i, false); });
    }
  }

  window.addEventListener('message', function (ev) {
    if (ev.data && ev.data.type === 'streamlit:render') { onRender(ev.data.args || {}); }
  });
  window.addEventListener('resize', frame);
  send('streamlit:componentReady', { apiVersion: 1 });
})();
</script></body></html>
"""

_KOMP = None


def _komponents():
    """Izveido (vienreiz uz procesu) komponentu: HTML tiek ierakstīts pagaidu mapē un deklarēts kā Streamlit komponents."""
    global _KOMP
    if _KOMP is None:
        mape = os.path.join(tempfile.gettempdir(), "nhl_rulli_komponents")
        os.makedirs(mape, exist_ok=True)
        fails = os.path.join(mape, "index.html")
        try:
            vecais = open(fails, encoding="utf-8").read() if os.path.exists(fails) else None
        except OSError:
            vecais = None
        if vecais != _HTML:
            with open(fails, "w", encoding="utf-8") as f:
                f.write(_HTML)
        _KOMP = components.declare_component("nhl_rulli", path=mape)
    return _KOMP


def izvele(komandas, sakuma, key="rulli"):
    """
    Parāda divus rullīšus. komandas: [{"kods", "nos" (nosaukums), "logo" (adrese)}]; sakuma: (kods_kreisais, kods_labais).
    Atgriež (kreisās komandas kods, labās komandas kods): pašreizējā izvēle (pirms lietotājs ko mainījis, tā ir sākuma izvēle).
    """
    val = _komponents()(komandas=list(komandas), sakuma=list(sakuma), key=key, default={"a": sakuma[0], "b": sakuma[1]})
    try:
        return val["a"], val["b"]
    except (TypeError, KeyError):
        return tuple(sakuma)
