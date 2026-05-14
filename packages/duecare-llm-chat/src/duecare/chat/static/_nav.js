/*
 * DueCare Exploration Workbench: shared nav + status loader.
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
        if (el) el.textContent = value == null ? 'pending' : String(value);
    }

    function setDot(state) {
        const el = document.getElementById('dc-wb-status-dot');
        if (!el) return;
        el.className = 'dc-wb-status-dot dc-wb-status-dot-' + state;
    }

    function fmtBytes(n) {
        if (n == null || isNaN(n)) return 'pending';
        if (n < 1024) return n + 'B';
        if (n < 1024 * 1024) return (n / 1024).toFixed(0) + 'KB';
        if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(0) + 'MB';
        return (n / 1024 / 1024 / 1024).toFixed(1) + 'GB';
    }

    const MODEL_FALLBACK_VARIANTS = {
        'e2b-it':         {display: 'Gemma 4 E2B-it', size_gb: 2.0, category: 'on-device', load_eta: '~20-30 sec'},
        'e4b-it':         {display: 'Gemma 4 E4B-it', size_gb: 4.0, category: 'on-device', load_eta: '~30-60 sec'},
        '26b-a4b-it':     {display: 'Gemma 4 26B-A4B-it', size_gb: 14.0, category: 'on-device', load_eta: '~6-15 min first run'},
        '31b-it':         {display: 'Gemma 4 31B-it', size_gb: 18.0, category: 'on-device', load_eta: '~15-25 min first run'},
        'jailbroken-31b': {display: 'Gemma 4 31B abliterated', size_gb: 18.0, category: 'jailbroken', load_eta: '~15-25 min first run'},
        'jailbroken-e4b': {display: 'Gemma 4 E4B abliterated', size_gb: 4.0, category: 'jailbroken', load_eta: '~30-60 sec'},
        'cloud-gemini':   {display: 'Gemini API (cloud)', size_gb: 0.0, category: 'cloud', load_eta: 'instant'},
        'cloud-openai':   {display: 'OpenAI-compatible (cloud)', size_gb: 0.0, category: 'cloud', load_eta: 'instant'},
        'cloud-ollama':   {display: 'Ollama (cloud/local)', size_gb: 0.0, category: 'cloud', load_eta: 'instant'}
    };
    let modelPollTimer = null;
    let modelLastStatus = {loaded: false};

    function modelSelectEl() {
        return document.getElementById('dc-wb-model-select');
    }

    function renderModelOptions(variants, activeVariant) {
        const sel = modelSelectEl();
        if (!sel) return;
        const prior = sel.value;
        const map = (variants && Object.keys(variants).length)
            ? variants : MODEL_FALLBACK_VARIANTS;
        sel.innerHTML = '';
        Object.keys(map).forEach(function (key) {
            const info = map[key] || {};
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = (info.display || key)
                + (info.load_eta ? ' | ' + info.load_eta : '');
            sel.appendChild(opt);
        });
        const keys = Object.keys(map);
        if (activeVariant && keys.indexOf(activeVariant) >= 0) sel.value = activeVariant;
        else if (prior && keys.indexOf(prior) >= 0) sel.value = prior;
        else if (keys.indexOf('e4b-it') >= 0) sel.value = 'e4b-it';
    }

    function renderModelLogs(logs) {
        const el = document.getElementById('dc-wb-model-log');
        if (!el) return;
        if (!logs || !logs.length) {
            el.textContent = 'No loader events yet.';
            return;
        }
        el.classList.add('show');
        el.textContent = logs.slice(-80).map(function (e) {
            const elapsed = e.elapsed_s == null ? '' : '+' + Number(e.elapsed_s).toFixed(0) + 's ';
            const phase = e.phase ? '[' + e.phase + '] ' : '';
            const level = e.level && e.level !== 'info' ? e.level.toUpperCase() + ' ' : '';
            return (e.ts || '') + ' ' + elapsed + level + phase + (e.message || '');
        }).join('\n');
        el.scrollTop = el.scrollHeight;
    }

    function setModelPopoverStatus(text) {
        const el = document.getElementById('dc-wb-model-popover-status');
        if (el) el.textContent = text || '';
    }

    async function refreshModelLoaderStatus() {
        let info = {};
        let load = {};
        try {
            const r = await fetch('/api/model-info', {cache: 'no-store'});
            if (r.ok) info = await r.json();
        } catch (_) { /* quiet */ }
        try {
            const r = await fetch('/api/load-model/status', {cache: 'no-store'});
            if (r.ok) load = await r.json();
        } catch (_) { /* kernels without the loader endpoint still use model-info */ }

        const loaded = !!info.loaded;
        const loading = load.status === 'loading';
        modelLastStatus = {...info, loaded};
        renderModelOptions(load.variants, load.variant || info.variant || info.name);
        renderModelLogs(load.logs || []);

        const name = loaded
            ? (info.display || info.name || load.variant || 'model loaded')
            : (loading ? 'Loading ' + (load.variant || 'model') : 'no model loaded');
        setText('dc-wb-status-model', name);
        setDot(loading ? 'loading' : (loaded ? 'loaded' : (load.status === 'error' ? 'error' : 'idle')));

        const loadBtn = document.getElementById('dc-wb-model-load');
        if (loadBtn) {
            loadBtn.disabled = loading;
            loadBtn.textContent = loading ? 'Loading...' : (loaded ? 'Switch/load selected' : 'Load selected');
        }

        const parts = [];
        if (loaded && (info.device || info.quantization)) {
            parts.push([info.device, info.quantization].filter(Boolean).join(' | '));
        }
        if (loading) {
            parts.push('phase: ' + (load.phase || 'loading'));
            if (load.elapsed_s != null) parts.push(Math.round(load.elapsed_s) + 's elapsed');
        }
        if (load.status === 'error' && load.error) parts.push('error: ' + load.error);
        setModelPopoverStatus(parts.join(' | ') || 'Select a model, then load it for all pages.');

        if (loading) {
            if (modelPollTimer) clearTimeout(modelPollTimer);
            modelPollTimer = setTimeout(refreshModelLoaderStatus, 1500);
        }
        return {info, load};
    }

    async function loadSelectedModel() {
        const sel = modelSelectEl();
        const variant = sel && sel.value;
        if (!variant) return;
        setModelPopoverStatus('Starting model load: ' + variant);
        try {
            const r = await fetch('/api/load-model', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({variant: variant})
            });
            const payload = await r.json().catch(function () { return {}; });
            if (!r.ok || payload.status === 'error') {
                setDot('error');
                setModelPopoverStatus('Model load failed: '
                    + (payload.error || payload.message || ('HTTP ' + r.status)));
                return;
            }
            await refreshModelLoaderStatus();
        } catch (e) {
            setDot('error');
            setModelPopoverStatus('Model load request failed: ' + ((e && e.message) || e));
        }
    }

    function openModelPopover() {
        const pop = document.getElementById('dc-wb-model-popover');
        const btn = document.getElementById('dc-wb-model-open');
        if (!pop) return;
        pop.hidden = false;
        if (btn) btn.setAttribute('aria-expanded', 'true');
        refreshModelLoaderStatus();
    }

    function closeModelPopover() {
        const pop = document.getElementById('dc-wb-model-popover');
        const btn = document.getElementById('dc-wb-model-open');
        if (pop) pop.hidden = true;
        if (btn) btn.setAttribute('aria-expanded', 'false');
    }

    async function refreshStatus() {
        // Version + brand counts (always succeeds when chat package is wired).
        try {
            const r = await fetch('/api/version', {cache: 'no-store'});
            if (r.ok) {
                const d = await r.json();
                const v = d.chat_package || d.version || d.duecare_llm_chat || '';
                setText('dc-wb-status-version', v ? 'v' + v : 'pending');
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

    function wireClearChat() {
        const btn = document.getElementById('dc-wb-clearchat-btn');
        if (!btn) return;
        const onChat = (document.body.getAttribute('data-nav') || '') === 'chat';
        if (!onChat) {
            btn.hidden = true;
            return;
        }
        btn.hidden = false;
        btn.addEventListener('click', function () {
            if (typeof window.resetChat === 'function') {
                window.resetChat();
                return;
            }
            const chat = document.getElementById('chat');
            if (chat) {
                const empty = chat.querySelector('.empty');
                Array.from(chat.children).forEach(function (n) {
                    if (n !== empty) n.remove();
                });
                if (empty) empty.style.display = '';
            }
        });
    }

    function wireModelPopover() {
        const openBtn = document.getElementById('dc-wb-model-open');
        const closeBtn = document.getElementById('dc-wb-model-close');
        const loadBtn = document.getElementById('dc-wb-model-load');
        const refreshBtn = document.getElementById('dc-wb-model-refresh');
        if (openBtn) {
            openBtn.addEventListener('click', function (event) {
                event.stopPropagation();
                const pop = document.getElementById('dc-wb-model-popover');
                if (pop && !pop.hidden) closeModelPopover();
                else openModelPopover();
            });
        }
        if (closeBtn) closeBtn.addEventListener('click', closeModelPopover);
        if (loadBtn) loadBtn.addEventListener('click', loadSelectedModel);
        if (refreshBtn) refreshBtn.addEventListener('click', refreshModelLoaderStatus);
        document.addEventListener('click', function (event) {
            const pop = document.getElementById('dc-wb-model-popover');
            const btn = document.getElementById('dc-wb-model-open');
            if (!pop || pop.hidden) return;
            if (pop.contains(event.target) || (btn && btn.contains(event.target))) return;
            closeModelPopover();
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') closeModelPopover();
        });
        window.dcWbOpenModelSelector = openModelPopover;
        window.dcWbRefreshModelStatus = refreshModelLoaderStatus;
        window.dcWbLoadSelectedModel = loadSelectedModel;
        window.dcWbEnsureModelReady = isModelReadyForPage;
        window.dcWbModelStatus = function () { return modelLastStatus; };
        renderModelOptions(null, null);
    }

    async function isModelReadyForPage() {
        const state = await refreshModelLoaderStatus();
        if (state.info && state.info.loaded) return true;
        openModelPopover();
        return false;
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
        // twice), don't duplicate it. That produced the "two nav
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
        if (!document.getElementById('dc-components-js')) {
            var s = document.createElement('script');
            s.id = 'dc-components-js';
            s.src = '/static/_components.js';
            s.defer = true;
            document.body.appendChild(s);
        }
        const key = document.body.getAttribute('data-nav') || '';
        activate(nav, key);
        wireModelPopover();
        wireShutdown();
        wireClearChat();
        refreshStatus();
        refreshModelLoaderStatus();
        // Light polling so the status strip stays current without blowing up
        // a phone battery: every 8 seconds.
        setInterval(function () {
            refreshStatus();
            refreshModelLoaderStatus();
        }, 8000);
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
