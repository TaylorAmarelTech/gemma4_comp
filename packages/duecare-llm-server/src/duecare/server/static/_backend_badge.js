// Global "Backend: <model>" floating pill. Loaded on every page; hits
// /api/model-info on first load, then every 30s in case the kernel
// switches model.
(function () {
  if (window.__dcBackendBadgeInit) return;
  window.__dcBackendBadgeInit = true;

  const el = document.createElement('div');
  el.className = 'dc-backend-badge';
  el.title = 'Click for details';
  el.innerHTML =
    '<span class="dot"></span>' +
    '<span class="label">Backend:</span>' +
    '<span class="name" id="dc-backend-name">checking…</span>';
  document.body.appendChild(el);

  function format(info) {
    if (!info || !info.loaded) return 'Heuristic-only · Built on Gemma 4';
    const display = info.display || info.name || 'unknown';
    // Hint at upstream attribution; the closing slide carries the
    // full Apache 2.0 + HF link.
    return display + ' · Built on Google\'s Gemma 4';
  }

  async function refresh() {
    try {
      const r = await fetch('/api/model-info', {cache: 'no-store'});
      if (!r.ok) throw new Error('http ' + r.status);
      const info = await r.json();
      document.getElementById('dc-backend-name').innerText = format(info);
      el.classList.toggle('loaded', !!info.loaded);
      el.style.pointerEvents = 'auto';
      el.title = info.device
        ? `model=${info.name} · device=${info.device} · quant=${info.quantization || '-'}`
        : `model=${info.name || 'none'}`;
    } catch (e) {
      document.getElementById('dc-backend-name').innerText = 'offline';
      el.classList.remove('loaded');
    }
  }

  refresh();
  setInterval(refresh, 30000);
})();
