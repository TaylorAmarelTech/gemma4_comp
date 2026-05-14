/* DueCare workbench - shared examples-picker primitive.
 *
 * Tier 4 #15 from the Compare audit: extract the example-prompts
 * lightbox so Chat + Compare (and future pages) share one
 * implementation instead of duplicating modals.
 *
 * Status: introductory release. Compare consumes this; Chat keeps
 * its own deeply-integrated modal for now (it also handles model
 * picker + layer config, which makes a wholesale swap risky). Chat
 * can adopt this incrementally by:
 *   1. Loading <script src="/static/_examples_picker.js" defer>
 *   2. Replacing its openExamplesModal() body with:
 *        window.dcExamplesPicker.open({onPick: useExample});
 *
 * Public API:
 *   window.dcExamplesPicker.fetchAll() -> Promise<Example[]>
 *      Cached fetch of /api/examples. Returns [] on failure.
 *
 *   window.dcExamplesPicker.renderInto(host, opts)
 *      Replaces `host`'s children with a categorized, filterable
 *      list of examples. `opts.onPick(example)` fires when a row
 *      is clicked. `opts.filter` is an initial filter string.
 *      `opts.examples` overrides the fetch (used for live filtering).
 *
 *   window.dcExamplesPicker.open(opts)
 *      Spawns a self-contained modal (creates DOM if not present)
 *      and calls renderInto on its body. opts.onPick is invoked
 *      with the chosen example AND the modal closes automatically.
 *      Returns a {close} handle.
 */
(function () {
  'use strict';

  let _cache = null;

  async function fetchAll() {
    if (_cache !== null) return _cache;
    try {
      const r = await fetch('/api/examples', {cache: 'no-store'});
      if (!r.ok) { _cache = []; return _cache; }
      const data = await r.json();
      _cache = data.examples || [];
      return _cache;
    } catch (e) {
      _cache = [];
      return _cache;
    }
  }

  function renderInto(host, opts) {
    if (!host) return;
    opts = opts || {};
    const examples = opts.examples || [];
    const q = (opts.filter || '').trim().toLowerCase();
    while (host.firstChild) host.removeChild(host.firstChild);

    const filtered = q ? examples.filter(ex => {
      const hay = ((ex.text || '') + ' ' + (ex.category || '')
                    + ' ' + (ex.label || '')).toLowerCase();
      return hay.indexOf(q) >= 0;
    }) : examples;

    if (!filtered.length) {
      const e = document.createElement('div');
      e.style.cssText = 'color:#8A8E97; font-style:italic; padding:24px 0; font-size:13px;';
      e.textContent = q
        ? 'No examples match "' + q + '".'
        : 'No examples loaded.';
      host.appendChild(e);
      return;
    }

    const byCat = {};
    filtered.forEach(ex => {
      const cat = ex.category || 'other';
      (byCat[cat] = byCat[cat] || []).push(ex);
    });

    Object.keys(byCat).sort().forEach(cat => {
      const h = document.createElement('div');
      h.style.cssText = 'font-size:11px; font-weight:700; color:#5B5F68; ' +
        'text-transform:uppercase; letter-spacing:0.05em; margin:14px 0 6px;';
      h.textContent = cat + ' (' + byCat[cat].length + ')';
      host.appendChild(h);

      byCat[cat].forEach(ex => {
        const row = document.createElement('div');
        row.style.cssText = 'padding:10px 12px; margin-bottom:6px; ' +
          'background:#FAF9F4; border:1px solid #EFEDE4; border-radius:8px; ' +
          'cursor:pointer; font-size:12.5px; line-height:1.5; transition:background 120ms;';
        row.onmouseenter = () => { row.style.background = '#F1EFE7'; };
        row.onmouseleave = () => { row.style.background = '#FAF9F4'; };
        row.tabIndex = 0;
        row.setAttribute('role', 'button');
        row.setAttribute('aria-label', ex.label || (ex.text || '').slice(0, 80));
        const onPick = () => { if (opts.onPick) opts.onPick(ex); };
        row.onclick = onPick;
        row.onkeydown = (e) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(); }
        };

        if (ex.label) {
          const lbl = document.createElement('div');
          lbl.style.cssText = 'font-weight:600; color:#0E1116; margin-bottom:4px;';
          lbl.textContent = ex.label;
          row.appendChild(lbl);
        }
        const txt = document.createElement('div');
        txt.style.cssText = 'color:#2A2D34;';
        txt.textContent = (ex.text || '').slice(0, 260)
          + ((ex.text || '').length > 260 ? '...' : '');
        row.appendChild(txt);
        if (ex.id) {
          const id = document.createElement('div');
          id.style.cssText = 'margin-top:4px; font-family:JetBrains Mono, monospace; ' +
            'font-size:10.5px; color:#8A8E97;';
          id.textContent = ex.id;
          row.appendChild(id);
        }
        host.appendChild(row);
      });
    });
  }

  function open(opts) {
    opts = opts || {};
    const overlayId = '_dc_ex_overlay';
    let overlay = document.getElementById(overlayId);
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = overlayId;
      overlay.style.cssText = 'position:fixed; inset:0; background:rgba(14,17,22,0.55); ' +
        'z-index:9000; display:flex; align-items:center; justify-content:center; padding:24px;';
      overlay.setAttribute('role', 'presentation');
      const modal = document.createElement('div');
      modal.style.cssText = 'background:#FFF; border-radius:12px; max-width:880px; ' +
        'width:100%; max-height:84vh; display:flex; flex-direction:column; ' +
        'overflow:hidden; box-shadow:0 12px 40px rgba(14,17,22,0.32);';
      modal.setAttribute('role', 'dialog');
      modal.setAttribute('aria-modal', 'true');
      modal.setAttribute('aria-label', 'Example prompts');
      modal.onclick = (e) => e.stopPropagation();

      const head = document.createElement('div');
      head.style.cssText = 'display:flex; justify-content:space-between; align-items:center; ' +
        'padding:14px 20px; border-bottom:1px solid #EFEDE4; background:#FAF9F4;';
      const title = document.createElement('div');
      title.style.cssText = 'font-size:16px; font-weight:700; color:#0E1116;';
      title.textContent = opts.title || 'Example prompts';
      head.appendChild(title);
      const close = document.createElement('button');
      close.style.cssText = 'padding:7px 13px; background:#FFF; color:#0E1116; ' +
        'border:1px solid #DDD8C9; border-radius:6px; font-size:12.5px; cursor:pointer;';
      close.textContent = 'Close';
      close.onclick = () => { overlay.remove(); };
      head.appendChild(close);
      modal.appendChild(head);

      const filterRow = document.createElement('div');
      filterRow.style.cssText = 'padding:12px 20px; border-bottom:1px solid #EFEDE4;';
      const filter = document.createElement('input');
      filter.type = 'text';
      filter.placeholder = 'Filter examples by text or category...';
      filter.style.cssText = 'width:100%; padding:8px 10px; border:1px solid #DDD8C9; ' +
        'border-radius:6px; font-size:13px; box-sizing:border-box;';
      filter.id = '_dc_ex_filter';
      filterRow.appendChild(filter);
      modal.appendChild(filterRow);

      const body = document.createElement('div');
      body.style.cssText = 'overflow-y:auto; flex:1; padding:8px 20px 20px;';
      body.id = '_dc_ex_body';
      modal.appendChild(body);

      overlay.appendChild(modal);
      overlay.onclick = (e) => {
        if (e.target === overlay) overlay.remove();
      };
      document.body.appendChild(overlay);

      filter.addEventListener('input', () => {
        fetchAll().then(exs => renderInto(body, {
          examples: exs,
          filter: filter.value,
          onPick: (ex) => { if (opts.onPick) opts.onPick(ex); overlay.remove(); },
        }));
      });
      const onEsc = (e) => {
        if (e.key === 'Escape') {
          overlay.remove();
          document.removeEventListener('keydown', onEsc);
        }
      };
      document.addEventListener('keydown', onEsc);
      setTimeout(() => filter.focus(), 50);
    }
    fetchAll().then(exs => renderInto(
      overlay.querySelector('#_dc_ex_body'),
      {examples: exs, filter: '', onPick: (ex) => {
        if (opts.onPick) opts.onPick(ex);
        overlay.remove();
      }},
    ));
    return {close: () => overlay.remove()};
  }

  window.dcExamplesPicker = {fetchAll, renderInto, open};
})();
