/*
 * DueCare Exploration Workbench — shared nav + status loader.
 *
 * Each viewer page tags itself with <body data-nav="<key>"> where
 * <key> matches a `data-nav-key` attribute in `_nav.html`. This script
 *   1. Fetches /static/_nav.html and prepends it to <body>
 *   2. Marks the matching nav link as aria-current
 *   3. Polls /api/version + /api/model-info to populate the status strip
 *   4. Wires the Shutdown button to a confirm-then-instructions modal
 *
 * Load early in <head> with `defer`; partial renders as body parses.
 */
(function () {
    'use strict';

    function activate(root, key) {
        if (!key || !root) return;
        const link = root.querySelector('a[data-nav-key="' + key + '"]');
        if (link) {
            link.setAttribute('aria-current', 'page');
            link.classList.add('on');
        }
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value == null ? '—' : String(value);
    }

    function setDot(state) {
        const el = document.getElementById('dc-wb-status-dot');
        if (!el) return;
        el.className = 'dc-wb-status-dot dc-wb-status-dot-' + state;
    }

    function fmtBytes(n) {
        if (n == null || isNaN(n)) return '—';
        if (n < 1024) return n + 'B';
        if (n < 1024 * 1024) return (n / 1024).toFixed(0) + 'KB';
        if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(0) + 'MB';
        return (n / 1024 / 1024 / 1024).toFixed(1) + 'GB';
    }

    async function refreshStatus() {
        // Version + brand counts (always succeeds when chat package is wired).
        try {
            const r = await fetch('/api/version', {cache: 'no-store'});
            if (r.ok) {
                const d = await r.json();
                const v = d.chat_package || d.version || d.duecare_llm_chat || '';
                setText('dc-wb-status-version', v ? 'v' + v : '—');
            }
        } catch (_) { /* quiet */ }

        // Model info: name + load state + GPU memory.
        try {
            const r = await fetch('/api/model-info', {cache: 'no-store'});
            if (r.ok) {
                const d = await r.json();
                const name = d.display || d.name || d.model_id || d.variant || '(no model loaded)';
                setText('dc-wb-status-model', name);
                if (d.loaded === false || /no model/i.test(name)) {
                    setDot('idle');
                } else {
                    setDot('loaded');
                }
                if (d.gpu_memory_bytes != null) {
                    setText('dc-wb-status-gpu', fmtBytes(d.gpu_memory_bytes));
                } else if (d.gpu_memory_mb != null) {
                    setText('dc-wb-status-gpu', d.gpu_memory_mb + 'MB');
                } else if (d.device) {
                    setText('dc-wb-status-gpu', d.device);
                }
            } else {
                setDot('error');
            }
        } catch (_) {
            setDot('error');
        }
    }

    function wireShutdown() {
        const btn = document.getElementById('dc-wb-shutdown-btn');
        if (!btn) return;
        btn.addEventListener('click', function () {
            const ok = window.confirm(
                'Shut down the Kaggle kernel?\n\n' +
                'This will:\n' +
                '  • release GPU memory\n' +
                '  • close the cloudflared tunnel\n' +
                '  • make this URL unreachable until the kernel is restarted\n\n' +
                'You will need to re-run the Kaggle cell to bring it back.'
            );
            if (!ok) return;
            // Try the chat-package shutdown endpoint if it exists.
            fetch('/api/shutdown', {method: 'POST'})
                .catch(function () { /* expected on kernels without the endpoint */ })
                .finally(function () {
                    document.body.innerHTML =
                        '<div style="display:flex; height:100vh; align-items:center; ' +
                        'justify-content:center; font-family:Inter, sans-serif; ' +
                        'background:#F7F6F1; color:#0E1116; flex-direction:column; gap:12px;">' +
                        '<h1 style="margin:0; font-weight:600;">Workbench shutdown requested</h1>' +
                        '<p style="margin:0; color:#5B5F68;">' +
                        'Stop the Kaggle cell to fully release the GPU. ' +
                        'Refresh this URL after re-running the cell.' +
                        '</p></div>';
                });
        });
    }

    function inject(html) {
        // Idempotency guard: if a chrome partial is already mounted
        // (because this script ran once, OR the page re-fetched the
        // partial after a DOM swap, OR the script tag is included
        // twice), don't duplicate it -- that produced the "two nav
        // bars + duplicate Shutdown buttons" bug reported 2026-05-12.
        if (document.querySelector('.dc-wb-shell')
            || document.body.classList.contains('dc-wb-has-nav')) {
            return;
        }
        const tpl = document.createElement('div');
        tpl.innerHTML = html.trim();
        const nav = tpl.firstElementChild;
        if (!nav) return;
        document.body.insertBefore(nav, document.body.firstChild);
        document.body.classList.add('dc-wb-has-nav');
        const key = document.body.getAttribute('data-nav') || '';
        activate(nav, key);
        wireShutdown();
        refreshStatus();
        // Light polling so the status strip stays current without blowing up
        // a phone battery: every 8 seconds.
        setInterval(refreshStatus, 8000);
    }

    function load() {
        fetch('/static/_nav.html', {cache: 'no-store'})
            .then(function (r) {
                if (!r.ok) throw new Error('nav fetch ' + r.status);
                return r.text();
            })
            .then(inject)
            .catch(function (err) {
                if (window.console && console.warn) {
                    console.warn('[duecare nav] load failed:', err);
                }
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
