/*
 * Shared "knowledge network" flow diagram.
 *
 * Renders the end-to-end submit -> curate -> publish -> sync loop so a
 * reviewer can see, at a glance, how anonymized facts/patterns leave a
 * kernel, get human-vetted on the hub, and come back as downloadable
 * knowledge packs. One source of truth used by share.html (submit half lit)
 * and sync.html (retrieve half lit); drop in:
 *
 *   <div class="dc-kflow" data-active="submit"></div>      // or "retrieve"
 *   <script src="/static/_knowledge_flow.js" defer></script>
 *
 * No dependencies. All text set via textContent (never innerHTML). Uses the
 * workbench palette tokens from _chrome.css with hex fallbacks; ember is the
 * privacy-boundary marker (anonymize stage) per the design rules.
 */
(function () {
  'use strict';

  // 6 stages of the loop. `phase` groups them: local (on the worker/NGO
  // device), boundary (the PII gate), hub (the shared server), back (return
  // to any kernel). `active` is the data-active token(s) each stage belongs to.
  var STAGES = [
    { n: 1, label: 'Extract', sub: 'Find patterns in case files, locally', phase: 'local', active: ['submit'] },
    { n: 2, label: 'Anonymize', sub: 'PII stripped before anything leaves', phase: 'boundary', active: ['submit'] },
    { n: 3, label: 'Submit', sub: 'Anonymized envelope sent to the hub', phase: 'hub', active: ['submit'] },
    { n: 4, label: 'Curate', sub: 'A human curator vets the submission', phase: 'hub', active: ['submit', 'retrieve'] },
    { n: 5, label: 'Publish', sub: 'Vetted pack added to the registry', phase: 'hub', active: ['retrieve'] },
    { n: 6, label: 'Sync + download', sub: 'Any kernel pulls the updated pack', phase: 'back', active: ['retrieve'] }
  ];

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function render(host) {
    var active = (host.getAttribute('data-active') || '').trim() || 'submit';
    while (host.firstChild) host.removeChild(host.firstChild);

    var title = el('div', 'dc-kflow-title',
      'How shared knowledge flows ' +
      (active === 'retrieve' ? '— you are pulling vetted packs back'
                             : '— you are contributing anonymized facts'));
    host.appendChild(title);

    var row = el('div', 'dc-kflow-row');
    STAGES.forEach(function (s, i) {
      var on = s.active.indexOf(active) !== -1;
      var node = el('div', 'dc-kflow-node' + (on ? ' is-active' : '') +
        (s.phase === 'boundary' ? ' is-boundary' : ''));
      node.appendChild(el('span', 'dc-kflow-num', String(s.n)));
      node.appendChild(el('span', 'dc-kflow-label', s.label));
      node.appendChild(el('span', 'dc-kflow-sub', s.sub));
      if (s.phase === 'boundary') {
        node.appendChild(el('span', 'dc-kflow-tag', 'privacy boundary'));
      }
      row.appendChild(node);
      if (i < STAGES.length - 1) {
        var arr = el('span', 'dc-kflow-arrow', '→');
        arr.setAttribute('aria-hidden', 'true');
        row.appendChild(arr);
      }
    });
    host.appendChild(row);

    var loop = el('div', 'dc-kflow-loop',
      '↺  The loop is the point: every vetted contribution makes the ' +
      'packs that every other kernel syncs better. Raw worker data never ' +
      'leaves the device — only anonymized, human-vetted knowledge does.');
    host.appendChild(loop);
  }

  function injectStyle() {
    if (document.getElementById('dc-kflow-style')) return;
    var css =
      '.dc-kflow{margin:0 0 14px;padding:14px 16px;background:var(--paper-2,#EFEDE4);' +
        'border:1px solid var(--line,#DDD8C9);border-radius:12px;}' +
      '.dc-kflow-title{font-size:12.5px;font-weight:700;color:var(--ink,#0E1116);margin:0 0 10px;}' +
      '.dc-kflow-row{display:flex;align-items:stretch;gap:6px;flex-wrap:wrap;}' +
      '.dc-kflow-node{flex:1 1 130px;min-width:120px;background:var(--paper,#F7F6F1);' +
        'border:1px solid var(--line,#DDD8C9);border-radius:10px;padding:9px 11px;' +
        'display:flex;flex-direction:column;gap:2px;opacity:0.55;transition:opacity 150ms;}' +
      '.dc-kflow-node.is-active{opacity:1;border-color:var(--accent,oklch(0.52 0.08 195));' +
        'box-shadow:0 1px 4px rgba(14,17,22,0.06);}' +
      '.dc-kflow-node.is-boundary.is-active{border-color:var(--ember,oklch(0.58 0.14 45));}' +
      '.dc-kflow-num{font-family:var(--mono,monospace);font-size:10px;font-weight:700;' +
        'color:var(--ink-3,#5B5F68);}' +
      '.dc-kflow-label{font-size:13px;font-weight:700;color:var(--ink,#0E1116);}' +
      '.dc-kflow-sub{font-size:10.5px;color:var(--ink-3,#5B5F68);line-height:1.35;}' +
      '.dc-kflow-tag{margin-top:3px;align-self:flex-start;font-family:var(--mono,monospace);' +
        'font-size:8.5px;text-transform:uppercase;letter-spacing:0.06em;padding:1px 5px;' +
        'border-radius:4px;background:var(--ember-soft,oklch(0.94 0.04 45));' +
        'color:var(--ember,oklch(0.58 0.14 45));}' +
      '.dc-kflow-arrow{align-self:center;color:var(--ink-4,#8A8E97);font-size:14px;flex:0 0 auto;}' +
      '@media(max-width:720px){.dc-kflow-arrow{display:none;}}' +
      '.dc-kflow-loop{margin-top:10px;font-size:11px;color:var(--ink-3,#5B5F68);line-height:1.5;}';
    var style = el('style');
    style.id = 'dc-kflow-style';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function init() {
    injectStyle();
    var hosts = document.querySelectorAll('.dc-kflow');
    Array.prototype.forEach.call(hosts, render);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  window.dcKnowledgeFlow = { render: render };
})();
