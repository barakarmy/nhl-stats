"""
Komandu izvēle ar vertikāliem rullīšiem (kā datorspēlē NHL): abās pusēs ritinās komandu logotipi, pa vidu ir uzraksts "VS".
Izvēlēta ir tā komanda, kuras logotips ir vidū (lielākais, bez rāmjiem). Ritina ar peles ritenīti, ar pirkstu vai velkot ar peli; klikšķis uz
blakus logotipa to ieritina vidū; bultiņas augšup/lejup maina izvēli ar tastatūru.

Tas ir Streamlit pielāgots komponents, rakstīts kā vienkāršs HTML/JS (bez būvēšanas). HTML tiek ierakstīts pagaidu mapē izpildes laikā,
tāpēc papildu failu augšupielādēt nav jāpiegādā: pietiek ar šo moduli.
"""
import hashlib
import os
import tempfile

import streamlit.components.v1 as components

_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root { --item: 120px; --pulse: 5.2s; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: transparent; font-family: Inter, system-ui, -apple-system, 'Segoe UI', sans-serif; overflow: hidden; color: #31333f; -webkit-user-select: none; user-select: none; }
.stage { display: flex; align-items: flex-start; justify-content: center; gap: clamp(8px, 3%, 30px); padding: 6px 4px 8px; }
.col { display: flex; flex-direction: column; align-items: center; gap: 8px; width: clamp(110px, 36%, 200px); }       /* platums kā agrākajai kastei (max 200 px) */
/* rullītis: bez rāmjiem un kastēm, tikai logotipi; izvēlētā logo platums = kolonnas platums */
.reel-box { position: relative; width: 100%; height: calc(var(--item) * 3); overflow: hidden; }
.reel { position: absolute; inset: 0; overflow-y: scroll; overflow-x: hidden; scroll-snap-type: y mandatory; scrollbar-width: none; -ms-overflow-style: none;
  overscroll-behavior: contain; touch-action: pan-y; cursor: grab; outline: none; }
.reel::-webkit-scrollbar { display: none; }
.reel.drag { cursor: grabbing; scroll-snap-type: none; }
.sp { height: var(--item); flex: none; }
.it { position: relative; height: var(--item); scroll-snap-align: center; scroll-snap-stop: always; }
/* .lg tiek mērogots ritināšanas laikā; img iekšpusē saņem blur un pulsāciju tikai tad, kad rullītis ir apstājies (.settled) */
.lg { position: absolute; left: 0; top: 50%; width: 100%; height: var(--logo); margin-top: calc(var(--logo) / -2); will-change: transform; transform-origin: 50% 50%; pointer-events: none; }
.lg img { width: 100%; height: 100%; object-fit: contain; display: block; -webkit-user-drag: none; transition: filter .25s ease; }
.reel.settled .it.nb img { filter: blur(var(--b, 2px)); }
.reel.settled .it.sel img { animation: pulss var(--pulse) ease-in-out infinite; }
@keyframes pulss { 0%, 100% { transform: scale(1); } 50% { transform: scale(.93); } }       /* minimāla pulsēšana, nepārsniedzot kolonnas platumu */
@media (prefers-reduced-motion: reduce) { .reel.settled .it.sel img { animation: none; } }
.name { min-height: 2.4rem; max-width: 100%; text-align: center; font-weight: 700; font-size: .95rem; line-height: 1.2; display: flex; align-items: center; justify-content: center; }
.vsbox { height: calc(var(--item) * 3); display: flex; align-items: center; }
.vs { font-family: 'Plus Jakarta Sans', Inter, system-ui, sans-serif; font-weight: 800; font-size: clamp(1.5rem, 6vw, 2.2rem); letter-spacing: .04em; opacity: .55; }
</style></head>
<body>
<div class="stage">
  <div class="col"><div class="reel-box"><div class="reel" id="ra" tabindex="0"></div></div><div class="name" id="na">&nbsp;</div></div>
  <div class="vsbox"><div class="vs">VS</div></div>
  <div class="col"><div class="reel-box"><div class="reel" id="rb" tabindex="0"></div></div><div class="name" id="nb">&nbsp;</div></div>
</div>
<script>
(function () {
  var COPIES = 7, MID = 3, SETTLE_MS = 700, ITEM = 120, LOGO = 120, teams = [], N = 0, reels = {}, lastSent = '', lastArgs = '', built = false, spinning = 0, lastH = 0;
  function send(type, data) { window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data), '*'); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function frame() {
    var h = Math.ceil(document.querySelector('.stage').getBoundingClientRect().height) + 2;
    if (h !== lastH) { lastH = h; send('streamlit:setFrameHeight', { height: h }); }
  }
  function sizes() {                       // izvēlētā logo platums = kolonnas platums; rindas solis mazāks, lai kaimiņi (mazāki) neaizsegtu
    var w = reels.a.parentNode.getBoundingClientRect().width || 140;
    LOGO = Math.round(w); ITEM = Math.round(w * 0.78);
    document.documentElement.style.setProperty('--logo', LOGO + 'px');
    document.documentElement.style.setProperty('--item', ITEM + 'px');
  }
  function build(el) {
    el.innerHTML = '';
    var sp = function () { var d = document.createElement('div'); d.className = 'sp'; return d; };
    el.appendChild(sp());
    for (var c = 0; c < COPIES; c++) {
      teams.forEach(function (t, i) {
        var it = document.createElement('div'); it.className = 'it'; it.dataset.g = c * N + i;
        var lg = document.createElement('div'); lg.className = 'lg';
        var img = document.createElement('img'); img.src = t.logo; img.alt = t.kods; img.draggable = false;
        lg.appendChild(img); it.appendChild(lg); el.appendChild(it);
      });
    }
    el.appendChild(sp());
  }
  function gidx(el) { return clamp(Math.round(el.scrollTop / ITEM), 0, COPIES * N - 1); }
  function team(el) { return teams[gidx(el) % N]; }
  function paint(el) {                     // mērogs un caurspīdīgums pēc attāluma līdz centram (ritināšanas laikā; bez blur un pulsācijas)
    var c = el.scrollTop / ITEM, items = el.querySelectorAll('.it');
    for (var i = Math.max(0, Math.floor(c) - 3); i < Math.min(items.length, Math.ceil(c) + 4); i++) {
      var d = Math.abs(i - c), lg = items[i].firstChild;
      lg.style.transform = 'scale(' + Math.max(.5, 1 - d * .32).toFixed(3) + ')';
      lg.style.opacity = Math.max(.35, 1 - d * .42).toFixed(3);
    }
  }
  function labels() { document.getElementById('na').textContent = team(reels.a).nos; document.getElementById('nb').textContent = team(reels.b).nos; }
  function emit() {
    var v = { a: team(reels.a).kods, b: team(reels.b).kods }, s = JSON.stringify(v);
    if (s !== lastSent) { lastSent = s; send('streamlit:setComponentValue', { value: v, dataType: 'json' }); }
  }
  function unsettle(el) { el.classList.remove('settled'); }
  function settle(el) {                    // rullītis apstājies: pārliek uz vidējo kopiju (nebeidzama ritināšana), uzliek blur kaimiņiem un pulsāciju izvēlētajam
    var g = gidx(el), ti = g % N, mid = MID * N + ti;
    if (g < N * 1.5 || g > N * (COPIES - 1.5)) { el.style.scrollSnapType = 'none'; el.scrollTop = mid * ITEM; el.style.scrollSnapType = ''; g = mid; }
    var items = el.querySelectorAll('.it');
    for (var i = Math.max(0, g - 6); i < Math.min(items.length, g + 7); i++) {
      var d = Math.abs(i - g), it = items[i];
      it.classList.toggle('sel', d === 0); it.classList.toggle('nb', d !== 0);
      it.style.setProperty('--b', (0.8 + 2.7 * Math.max(0, 1 - (d - 1) / 6)).toFixed(2) + 'px');     // jo tuvāk izvēlētajam, jo stiprāks blur
    }
    paint(el); labels();
    if (!spinning) { el.classList.add('settled'); emit(); }
  }
  function onScroll(el) {
    paint(el); labels(); unsettle(el);
    clearTimeout(el._t); el._t = setTimeout(function () { settle(el); }, SETTLE_MS);
  }
  function goTo(el, g, smooth) { el.scrollTo({ top: clamp(g, 0, COPIES * N - 1) * ITEM, behavior: smooth ? 'smooth' : 'auto' }); }

  // sākuma "griešanās": rullītis izripo pilnu apli līdz izvēlētajai komandai
  function spin(el, ti, ms) {
    var b = (MID * N + ti) * ITEM, a = b - (N + 9) * ITEM, t0 = null;
    el.style.scrollSnapType = 'none'; spinning++; unsettle(el); el.scrollTop = a;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var k = clamp((ts - t0) / ms, 0, 1), e = 1 - Math.pow(1 - k, 3);
      el.scrollTop = a + (b - a) * e;
      if (k < 1) { requestAnimationFrame(step); }
      else { el.style.scrollSnapType = ''; el.scrollTop = b; spinning--; clearTimeout(el._t); el._t = setTimeout(function () { settle(el); }, SETTLE_MS); }
    }
    requestAnimationFrame(step);
  }

  function attach(el) {
    el.addEventListener('scroll', function () { onScroll(el); }, { passive: true });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        var base = el._tgt === undefined ? gidx(el) : el._tgt;
        el._tgt = clamp(base + (e.key === 'ArrowDown' ? 1 : -1), 0, COPIES * N - 1);
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
      var y = e.clientY - el.getBoundingClientRect().top;
      goTo(el, Math.round((y + el.scrollTop - ITEM * 1.5) / ITEM), true);
    });
  }

  function onRender(args, theme) {
    if (theme && theme.textColor) document.body.style.color = theme.textColor;
    var key = JSON.stringify(args.sakuma || []);
    if (!built) {
      teams = args.komandas || []; N = teams.length;
      reels.a = document.getElementById('ra'); reels.b = document.getElementById('rb');
      sizes(); build(reels.a); build(reels.b); attach(reels.a); attach(reels.b);
      built = true; frame();
      var ix = function (k) { var i = teams.findIndex(function (t) { return t.kods === k; }); return i < 0 ? 0 : i; };
      var s = args.sakuma || [];
      setTimeout(function () { sizes(); frame(); spin(reels.a, ix(s[0]), 1000); spin(reels.b, ix(s[1]), 1250); }, 60);
      lastArgs = key;
    } else if (key !== lastArgs) {              // Python nomainīja sākuma izvēli: pārliek bez griešanās
      lastArgs = key;
      var s2 = args.sakuma || [];
      [reels.a, reels.b].forEach(function (r, n) { var i = teams.findIndex(function (t) { return t.kods === s2[n]; }); if (i >= 0) goTo(r, MID * N + i, false); });
    }
  }

  window.addEventListener('message', function (ev) {
    if (ev.data && ev.data.type === 'streamlit:render') { onRender(ev.data.args || {}, ev.data.theme); }
  });
  window.addEventListener('resize', function () {
    if (!built) return;
    var ga = gidx(reels.a), gb = gidx(reels.b); sizes(); reels.a.scrollTop = ga * ITEM; reels.b.scrollTop = gb * ITEM; frame();
  });
  send('streamlit:componentReady', { apiVersion: 1 });
})();
</script></body></html>
"""

_KOMP = None


def _komponents():
    """
    Izveido (vienreiz uz procesu) komponentu. Nosaukums un mape satur HTML satura jaucējkodu: mainoties dizainam, mainās arī adrese,
    tāpēc pārlūks (arī telefonā) nekad nerāda veco kešoto versiju.
    """
    global _KOMP
    if _KOMP is None:
        h = hashlib.md5(_HTML.encode("utf-8")).hexdigest()[:10]
        mape = os.path.join(tempfile.gettempdir(), f"nhl_rulli_{h}")
        os.makedirs(mape, exist_ok=True)
        fails = os.path.join(mape, "index.html")
        if not os.path.exists(fails):
            with open(fails, "w", encoding="utf-8") as f:
                f.write(_HTML)
        _KOMP = components.declare_component(f"nhl_rulli_{h}", path=mape)
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
