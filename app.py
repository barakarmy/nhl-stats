    var a = e.target.closest && e.target.closest('.st-key-topbar a');
    var b = josla();
    if (!a || !b) return;
    b.classList.add('nav-aizvert');
    if (d.activeElement && d.activeElement.blur) d.activeElement.blur();
  }
  function atvert(e) {                    // atkal ļauj atvērt, kad lietotājs uzved peli vai pieskaras grupas nosaukumam
    var t = e.target.closest && e.target.closest('.nav-title');
    var b = josla();
    if (t && b) b.classList.remove('nav-aizvert');
  }
  var reg = [['click', klik], ['pointerover', atvert], ['touchstart', atvert], ['focusin', atvert]];
  reg.forEach(function (n) { d.addEventListener(n[0], n[1], true); });
  w.__nhlIzv = { reg: reg };
  var b0 = josla(); if (b0) b0.classList.remove('nav-aizvert');          // jauns kadrs = tīrs sākums
  function tirit() {                       // kadrs tiek likvidēts: noņem savus klausītājus un iestrēgušo stāvokli
    try { reg.forEach(function (n) { d.removeEventListener(n[0], n[1], true); }); if (w.__nhlIzv && w.__nhlIzv.reg === reg) w.__nhlIzv = null; var b = josla(); if (b) b.classList.remove('nav-aizvert'); } catch (e) {}
  }
  window.addEventListener('pagehide', tirit);
  window.addEventListener('unload', tirit);
})();
</script>
"""

if NAV_REZIMS == "pielagots":
    augseja_josla(lapas)
    with st.container(key="nav_skripts"):       # stabila pozīcija: skripta kadrs netiek pārbūvēts, mainoties citiem elementiem
        try:
            import streamlit.components.v1 as components
            components.html(IZVELNES_SKRIPTS, height=0)
        except Exception:       # skripts ir tikai uzlabojums: bez tā izvēlne aizveras, nospiežot jebkur citur
            pass
lapas.run()

# ===== app.py beigas (ja šī rinda redzama GitHub failā, fails ir augšupielādēts pilnīgi) =====
