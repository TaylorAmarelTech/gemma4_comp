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

    if (window.__dcWbNavBooting) return;
    window.__dcWbNavBooting = true;

    function activate(root, key) {
        if (!key || !root) return;
        const navAliases = {
            layers: 'harness',
            tools: 'harness',
            hotlines: 'share',
            anonymize: 'share',
            import: 'process',
            grade: 'compare',
            logs: 'status',
            models: 'status',
            settings: 'status',
        };
        let link = root.querySelector('a[data-nav-key="' + key + '"]');
        const exact = !!link;
        if (!link && navAliases[key]) {
            link = root.querySelector('a[data-nav-key="' + navAliases[key] + '"]');
        }
        if (link) {
            if (exact) link.setAttribute('aria-current', 'page');
            link.classList.add('on');
            const group = link.closest('.dc-wb-nav-group');
            if (group) {
                group.classList.add('on');
                const summary = group.querySelector('summary');
                if (summary) summary.classList.add('on');
            }
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
        'jailbroken-e4b': {display: 'Gemma 4 E4B abliterated', size_gb: 4.0, category: 'jailbroken', load_eta: '~30-60 sec'}
    };
    let modelPollTimer = null;
    let modelLastStatus = {loaded: false};
    let modelSelectorRequired = false;
    let modelVariantMap = MODEL_FALLBACK_VARIANTS;
    let modelActiveVariant = '';
    let modelUserSelectedVariant = '';
    const modelRequiredNavKeys = new Set([
        'chat',
        'compare',
        'process',
        'knowledge',
        'search',
    ]);

    function modelSelectEl() {
        return document.getElementById('dc-wb-model-select');
    }

    function normalizeVariantMap(variants) {
        if (!variants) return MODEL_FALLBACK_VARIANTS;
        if (Array.isArray(variants)) {
            const out = {};
            variants.forEach(function (item) {
                if (!item) return;
                const key = item.key || item.variant || item.id || item.name;
                if (!key) return;
                out[key] = {
                    display: item.display || item.label || item.name || key,
                    size_gb: item.size_gb,
                    fits: item.fits,
                    category: item.category || item.runtime_class,
                    load_eta: item.load_eta || item.eta,
                };
            });
            return Object.keys(out).length ? out : MODEL_FALLBACK_VARIANTS;
        }
        if (typeof variants === 'object' && Object.keys(variants).length) {
            return variants;
        }
        return MODEL_FALLBACK_VARIANTS;
    }

    function normalizeActiveModel(active, load) {
        if (active && typeof active === 'object' && !Array.isArray(active)) {
            return active;
        }
        if (typeof active === 'string' && active) {
            return {
                loaded: true,
                name: active,
                display: active,
                variant: load && load.variant,
            };
        }
        return {};
    }

    function escText(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
        });
    }

    function renderSelectedModelDetail() {
        const host = document.getElementById('dc-wb-model-detail');
        const sel = modelSelectEl();
        if (!host || !sel) return;
        const key = sel.value || modelActiveVariant || '';
        const info = modelVariantMap[key] || {};
        if (!key) {
            host.textContent = 'Select a model to see size, runtime class, and estimated load time.';
            return;
        }
        const active = modelLastStatus.loaded
            && (key === modelActiveVariant
                || key === modelLastStatus.variant
                || key === modelLastStatus.name);
        const bits = [];
        if (info.category) bits.push('class: ' + info.category);
        if (info.size_gb != null) bits.push('runtime size: ' + info.size_gb);
        if (info.load_eta) bits.push('load: ' + info.load_eta);
        host.innerHTML =
            '<b>' + escText(info.display || key) + '</b>' +
            (active ? ' <span class="dc-wb-status-dot dc-wb-status-dot-loaded" aria-hidden="true" style="display:inline-block; vertical-align:-1px; margin:0 4px;"></span><b>loaded</b>' : '') +
            '<br>' + escText(bits.join(' | ') || 'Loader metadata is not available for this model.') +
            '<br><span class="dc-wb-model-popover-sub">Loaded models are shared across all workbench pages.</span>';
    }

    function renderModelOptions(variants, activeVariant) {
        const sel = modelSelectEl();
        if (!sel) return;
        const prior = sel.value;
        const map = normalizeVariantMap(variants);
        modelVariantMap = map;
        modelActiveVariant = activeVariant || '';
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
        if (modelUserSelectedVariant && keys.indexOf(modelUserSelectedVariant) >= 0) sel.value = modelUserSelectedVariant;
        else if (activeVariant && keys.indexOf(activeVariant) >= 0) sel.value = activeVariant;
        else if (prior && keys.indexOf(prior) >= 0) sel.value = prior;
        // Default the chat picker to 31b-it. Steady-state inference
        // latency is comparable to smaller variants once loaded, and
        // using 31b-it for both chat AND judge (via "Use chat model
        // as judge") avoids loading a second model.
        else if (keys.indexOf('31b-it') >= 0) sel.value = '31b-it';
        else if (keys.indexOf('e4b-it') >= 0) sel.value = 'e4b-it';
        renderSelectedModelDetail();
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
            const rawLevel = e.level || e.severity || '';
            const level = rawLevel && rawLevel !== 'info' ? rawLevel.toUpperCase() + ' ' : '';
            return (e.ts || '') + ' ' + elapsed + level + phase + (e.message || '');
        }).join('\n');
        el.scrollTop = el.scrollHeight;
    }

    function setModelPopoverStatus(text) {
        const el = document.getElementById('dc-wb-model-popover-status');
        if (el) el.textContent = text || '';
    }

    function modelPhaseProgress(load, loaded, loading) {
        if (loaded) return 100;
        if (!load || load.status === 'idle' || !loading) return 0;
        if (load.status === 'error') return 100;
        const phase = String(load.phase || load.status || '').toLowerCase();
        const phaseMap = {
            queued: 6,
            starting: 12,
            importing: 22,
            imported: 30,
            unload: 36,
            'gpu-check': 42,
            'resolve-repo': 48,
            from_pretrained: 64,
            tokenizer: 72,
            warmup: 84,
            ready: 100,
        };
        if (phaseMap[phase] != null) return phaseMap[phase];
        if (phase.indexOf('pretrained') >= 0 || phase.indexOf('download') >= 0) return 64;
        if (phase.indexOf('import') >= 0) return 24;
        if (phase.indexOf('gpu') >= 0) return 42;
        return 35;
    }

    function updateModelProgress(load, loaded, loading) {
        const bar = document.getElementById('dc-wb-model-progress');
        const fill = document.getElementById('dc-wb-model-progress-fill');
        const meta = document.getElementById('dc-wb-model-progress-meta');
        if (!bar || !fill || !meta) return;
        const pct = Math.max(0, Math.min(100, modelPhaseProgress(load, loaded, loading)));
        const state = loaded ? 'loaded' : (load && load.status === 'error' ? 'error' : (loading ? 'loading' : 'idle'));
        bar.setAttribute('data-state', state);
        bar.setAttribute('aria-valuenow', String(Math.round(pct)));
        fill.style.width = pct + '%';
        const bits = [];
        if (loaded) bits.push('Ready for all workbench pages.');
        else if (load && load.status === 'error') bits.push('Load failed.');
        else if (loading) bits.push('Loading: ' + (load.phase || 'starting'));
        else bits.push('Idle.');
        if (load && load.variant) bits.push('variant=' + load.variant);
        if (load && load.elapsed_s != null) bits.push(Math.round(load.elapsed_s) + 's elapsed');
        if (load && load.eta) bits.push('ETA ' + load.eta);
        if (load && load.error) bits.push('error=' + load.error);
        meta.textContent = bits.join(' | ');
        // Show the Unload button when a model is currently loaded. The
        // Load button stays visible (the user might want to swap to a
        // new variant after unload), but the new Unload action is only
        // useful when there's something to unload.
        const unloadBtn = document.getElementById('dc-wb-model-unload');
        if (unloadBtn) unloadBtn.hidden = !loaded;
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

        if (!info.loaded && load.ready && load.active_model) {
            info = {...normalizeActiveModel(load.active_model, load), loaded: true};
        }
        const loaded = !!(info.loaded || load.ready || load.status === 'ready');
        const loading = load.status === 'loading' || load.status === 'queued';
        modelLastStatus = {...info, loaded, variant: info.variant || load.variant || info.name};
        renderModelOptions(load.variants, load.variant || info.variant || info.name);
        renderModelLogs(load.logs || []);
        updateModelProgress(load, loaded, loading);

        const name = loaded
            ? (info.display || info.name || load.variant || 'model loaded')
            : (loading ? 'Loading ' + (load.variant || 'model') : 'no model loaded');
        setText('dc-wb-status-model', name);
        setDot(loading ? 'loading' : (loaded ? 'loaded' : (load.status === 'error' ? 'error' : 'idle')));
        const openBtn = document.getElementById('dc-wb-model-open');
        if (openBtn) {
            openBtn.title = [
                'Universal model service',
                loaded ? 'ready' : (loading ? 'loading' : (load.status || 'idle')),
                load.phase ? 'phase: ' + load.phase : '',
                load.error ? 'error: ' + load.error : '',
            ].filter(Boolean).join(' | ');
        }

        const loadBtn = document.getElementById('dc-wb-model-load');
        if (loadBtn) {
            const sel = modelSelectEl();
            const selected = sel && sel.value;
            const selectedActive = loaded && selected
                && (selected === modelActiveVariant
                    || selected === modelLastStatus.variant
                    || selected === modelLastStatus.name);
            loadBtn.disabled = loading;
            loadBtn.textContent = loading
                ? 'Loading...'
                : (selectedActive ? 'Loaded' : (loaded ? 'Load selected' : 'Load selected'));
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

        if (loaded && modelSelectorRequired) {
            modelUserSelectedVariant = '';
            closeModelPopover(true);
        }

        if (loading) {
            if (modelPollTimer) clearTimeout(modelPollTimer);
            modelPollTimer = setTimeout(refreshModelLoaderStatus, 1500);
        }
        return {info, load};
    }

    // ============== Chat-model preflight (disk + GPU gate) ==============
    //
    // Mirror of the judge-model preflight in compare.html. The kernel
    // exposes /api/load-model/preflight?variant=... so the UI can show
    // disk + GPU headroom BEFORE the user clicks Load. Older kernels
    // (without the endpoint) return 404; in that case the picker hides
    // the panel and operates as it did before -- the load endpoint
    // itself is the only gate.
    var modelLastPreflight = null;
    async function refreshModelPreflight() {
        const sel = modelSelectEl();
        const variant = sel && sel.value;
        const panel = document.getElementById('dc-wb-model-preflight');
        const badge = document.getElementById('dc-wb-model-preflight-badge');
        const detail = document.getElementById('dc-wb-model-preflight-detail');
        const reasons = document.getElementById('dc-wb-model-preflight-reasons');
        const forceLbl = document.getElementById('dc-wb-model-force-label');
        const loadBtn = document.getElementById('dc-wb-model-load');
        if (!panel || !badge || !detail) return null;
        if (!variant) {
            panel.hidden = true;
            return null;
        }
        badge.textContent = 'checking…';
        badge.style.background = '#EFEDE4';
        badge.style.color = '#5B5F68';
        try {
            const r = await fetch(
                '/api/load-model/preflight?variant=' + encodeURIComponent(variant),
                {cache: 'no-store'}
            );
            if (r.status === 404) {
                // Older kernel without preflight: hide panel and let
                // the picker behave exactly as before.
                panel.hidden = true;
                modelLastPreflight = null;
                return null;
            }
            if (!r.ok) {
                panel.hidden = false;
                badge.textContent = 'check failed';
                badge.style.background = 'oklch(0.94 0.04 25)';
                badge.style.color = 'oklch(0.32 0.10 25)';
                detail.textContent = 'HTTP ' + r.status;
                if (reasons) reasons.style.display = 'none';
                if (forceLbl) forceLbl.style.display = 'none';
                modelLastPreflight = null;
                return null;
            }
            const data = await r.json();
            modelLastPreflight = data;
            panel.hidden = false;
            const needD = (data.needs_disk_gb != null) ? data.needs_disk_gb.toFixed(1) : '?';
            const needG = (data.needs_gpu_gb != null) ? data.needs_gpu_gb.toFixed(1) : '?';
            const haveD = (data.disk_free_gb != null) ? data.disk_free_gb.toFixed(1) : '?';
            const haveG = (data.gpu_free_gb != null) ? data.gpu_free_gb.toFixed(1) : '?';
            detail.textContent =
                'needs ' + needD + ' GB disk + ' + needG + ' GB GPU · ' +
                'have ' + haveD + ' GB disk + ' + haveG + ' GB GPU' +
                (Array.isArray(data.notes) && data.notes.length
                    ? ' · ' + data.notes.join('; ')
                    : '');
            if (data.ok) {
                badge.textContent = 'ready';
                badge.style.background = 'oklch(0.92 0.06 155)';
                badge.style.color = 'oklch(0.32 0.07 155)';
                if (reasons) { reasons.style.display = 'none'; reasons.textContent = ''; }
                if (forceLbl) forceLbl.style.display = 'none';
                if (loadBtn) loadBtn.disabled = false;
            } else {
                badge.textContent = 'blocked';
                badge.style.background = 'oklch(0.94 0.04 25)';
                badge.style.color = 'oklch(0.32 0.10 25)';
                if (reasons) {
                    reasons.style.display = '';
                    reasons.textContent = 'Reasons: ' + (data.reasons || []).join(' · ');
                }
                if (forceLbl) forceLbl.style.display = 'inline-flex';
                const forceChk = document.getElementById('dc-wb-model-force');
                if (loadBtn) loadBtn.disabled = !(forceChk && forceChk.checked);
            }
            return data;
        } catch (e) {
            panel.hidden = false;
            badge.textContent = 'check failed';
            badge.style.background = 'oklch(0.94 0.04 25)';
            badge.style.color = 'oklch(0.32 0.10 25)';
            detail.textContent = 'preflight error: ' + e;
            return null;
        }
    }

    async function unloadCurrentModel(opts) {
        opts = opts || {};
        const force = !!opts.force;
        const purgeChk = document.getElementById('dc-wb-model-purge');
        const purge = !purgeChk || purgeChk.checked;  // default true
        setModelPopoverStatus(
            'Unloading current model' +
            (purge ? ' (purging disk cache)' : '') +
            (force ? ' (forced)' : '') +
            '…'
        );
        try {
            const r = await fetch('/api/unload-model', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({purge_cache: purge, force: force})
            });
            if (r.status === 404) {
                setModelPopoverStatus(
                    'Unload requires kernel v0.18+ (POST /api/unload-model missing). '
                    + 'Restart the Kaggle cell with the latest kernel.py.'
                );
                return;
            }
            // Queue-busy gate: kernel refuses to free the model while
            // other users have in-flight requests. Offer a confirm-
            // dialog escape hatch so an operator can interrupt others
            // when truly needed (recording session, stuck call, etc.).
            if (r.status === 409) {
                const data = await r.json().catch(function () { return {}; });
                if (data && data.status === 'queue_busy') {
                    const drain = (data.drain || {});
                    const msg =
                        'Cannot unload while ' + (drain.active_at_close || 0) +
                        ' inference call(s) are running and ' +
                        (drain.waiting_at_close || 0) + ' waiting on the chat slot.';
                    setModelPopoverStatus(msg + ' Click again to force-interrupt.');
                    // Second click within ~10s triggers force unload.
                    const shouldForce = window.confirm(
                        msg + '\n\nForce-unload now? This will interrupt anyone ' +
                        'currently using the model.'
                    );
                    if (shouldForce) {
                        await unloadCurrentModel({force: true});
                    }
                    return;
                }
                setModelPopoverStatus((data && data.message) || 'Unload conflict (HTTP 409).');
                return;
            }
            const data = await r.json().catch(function () { return {}; });
            if (data.purged && data.purged.ok) {
                const gb = data.purged.gb_freed != null ? data.purged.gb_freed.toFixed(2) : '?';
                setModelPopoverStatus('Unloaded · freed ' + gb + ' GB from disk');
            } else {
                setModelPopoverStatus(data.message || 'Unloaded.');
            }
            // Refresh status so the picker UI matches the freed state.
            await refreshModelLoaderStatus();
            await refreshModelPreflight();
        } catch (e) {
            setModelPopoverStatus('Unload failed: ' + ((e && e.message) || e));
        }
    }

    async function loadSelectedModel() {
        const sel = modelSelectEl();
        const variant = sel && sel.value;
        if (!variant) return;
        modelUserSelectedVariant = variant;
        // Re-run preflight at click time so a stale check can't sneak
        // through: the user might have downloaded another model since
        // the last refresh and eaten the headroom.
        const pre = await refreshModelPreflight();
        const forceChk = document.getElementById('dc-wb-model-force');
        const override = !!(forceChk && forceChk.checked);
        if (pre && !pre.ok && !override) {
            setModelPopoverStatus(
                'Preflight blocked: ' + (pre.reasons || []).join('; ') +
                '. Free disk / GPU or tick "Force load".'
            );
            return;
        }
        setModelPopoverStatus('Starting model load: ' + variant);
        renderModelLogs([{ts: new Date().toLocaleTimeString(), phase: 'request', message: 'POST /api/load-model variant=' + variant + (override ? ' (force)' : '')}]);
        try {
            const r = await fetch('/api/load-model', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({variant: variant, override: override})
            });
            if (r.status === 503) {
                const data = await r.json().catch(function () { return {}; });
                setDot('error');
                setModelPopoverStatus('Preflight blocked: ' + (data.message || ''));
                refreshModelPreflight();
                return;
            }
            const payload = await r.json().catch(function () { return {}; });
            if (payload.status === 'already_loaded') {
                setDot('loaded');
                setModelPopoverStatus(
                    (payload.message || 'A model is already loaded.')
                    + ' Selected: ' + variant + '. Active: ' + (payload.variant || modelActiveVariant || 'current model') + '.'
                );
                await refreshModelLoaderStatus();
                return;
            }
            if (payload.status === 'busy') {
                setDot('loading');
                setModelPopoverStatus(payload.message || 'A model is already loading; wait for completion before selecting another variant.');
                await refreshModelLoaderStatus();
                return;
            }
            if (!r.ok || payload.status === 'error') {
                setDot('error');
                setModelPopoverStatus('Model load failed: '
                    + (payload.error || payload.message || ('HTTP ' + r.status)));
                updateModelProgress({status: 'error', variant: variant, error: payload.error || payload.message || ('HTTP ' + r.status)}, false, false);
                await refreshModelLoaderStatus();
                return;
            }
            await refreshModelLoaderStatus();
        } catch (e) {
            setDot('error');
            setModelPopoverStatus('Model load request failed: ' + ((e && e.message) || e));
            updateModelProgress({status: 'error', variant: variant, error: ((e && e.message) || e)}, false, false);
        }
    }

    async function loadModelVariant(variant, options) {
        const opts = options || {};
        const sel = modelSelectEl();
        if (sel && variant) {
            sel.value = variant;
            modelUserSelectedVariant = variant;
            renderSelectedModelDetail();
        }
        if (opts.open !== false) {
            openModelPopover({required: !!opts.required});
        }
        return loadSelectedModel();
    }

    function openModelPopover(options) {
        const opts = options || {};
        const layer = document.getElementById('dc-wb-model-layer');
        const pop = document.getElementById('dc-wb-model-popover');
        const btn = document.getElementById('dc-wb-model-open');
        if (!pop) return;
        modelSelectorRequired = !!opts.required;
        if (layer) layer.hidden = false;
        pop.hidden = false;
        pop.setAttribute('aria-modal', modelSelectorRequired ? 'true' : 'false');
        pop.setAttribute('data-required', modelSelectorRequired ? 'true' : 'false');
        document.body.classList.toggle('dc-wb-model-required', modelSelectorRequired);
        if (btn) btn.setAttribute('aria-expanded', 'true');
        if (modelSelectorRequired) {
            setModelPopoverStatus(
                'Load a Gemma 4 model to continue. The top bar can switch models after one is loaded.'
            );
        }
        setTimeout(function () {
            const sel = modelSelectEl();
            if (sel) sel.focus();
        }, 0);
        refreshModelLoaderStatus();
        // Surface disk + GPU headroom the moment the popover opens.
        // Hidden gracefully when the kernel doesn't expose the
        // /api/load-model/preflight endpoint.
        refreshModelPreflight();
    }

    function closeModelPopover(force) {
        const layer = document.getElementById('dc-wb-model-layer');
        const pop = document.getElementById('dc-wb-model-popover');
        const btn = document.getElementById('dc-wb-model-open');
        if (modelSelectorRequired && !force && !modelLastStatus.loaded) return;
        modelSelectorRequired = false;
        if (layer) layer.hidden = true;
        if (pop) pop.hidden = true;
        if (pop) {
            pop.setAttribute('aria-modal', 'false');
            pop.removeAttribute('data-required');
        }
        document.body.classList.remove('dc-wb-model-required');
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

        // Inference queue. Polled at the same cadence as model-info
        // so any page that shares the chrome can see how busy the
        // kernel is. Older kernels without /api/queue/status return
        // 404; we fail closed to "idle" and stay quiet so the new UI
        // does not break the legacy backend.
        try {
            const r = await fetch('/api/queue/status', {cache: 'no-store'});
            if (r.ok) {
                const q = await r.json();
                setText('dc-wb-status-queue', _renderQueueStatus(q));
            }
        } catch (_) { /* quiet */ }
    }

    /**
     * Compose the queue status label from a /api/queue/status snapshot.
     * Sums chat + judge slots so the strip shows one honest number.
     * @param {{slots?: Record<string, {n_active?: number, n_waiting?: number}>}} snapshot
     * @returns {string}
     */
    function _renderQueueStatus(snapshot) {
        const slots = (snapshot && snapshot.slots) || {};
        let active = 0;
        let waiting = 0;
        Object.keys(slots).forEach(name => {
            const s = slots[name] || {};
            active += Number(s.n_active || 0);
            waiting += Number(s.n_waiting || 0);
        });
        if (!active && !waiting) return 'idle';
        if (!waiting) return active === 1 ? '1 running' : active + ' running';
        return active + ' running, ' + waiting + ' waiting';
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

    const DC_REPLAY_BODY_LIMIT = 800000;
    const DC_REPLAY_TEXT_LIMIT = 2500000;

    function replayEntries() {
        if (!window.__dcWbReplayEntries) window.__dcWbReplayEntries = [];
        return window.__dcWbReplayEntries;
    }

    function replayUrlParts(input) {
        try {
            const rawUrl = typeof input === 'string'
                ? input
                : (input && input.url) || '';
            const url = new URL(rawUrl, window.location.origin);
            return {url: url.href, path: url.pathname, query: url.search || ''};
        } catch (_) {
            return {url: '', path: '', query: ''};
        }
    }

    function serializeReplayBody(body) {
        if (body == null) return null;
        if (typeof FormData !== 'undefined' && body instanceof FormData) {
            const fields = [];
            body.forEach(function (value, key) {
                if (value && typeof value === 'object'
                    && typeof value.name === 'string'
                    && typeof value.size === 'number') {
                    fields.push({
                        key: key,
                        kind: 'file',
                        name: value.name,
                        size: value.size,
                        type: value.type || '',
                        last_modified: value.lastModified || null,
                    });
                } else {
                    fields.push({key: key, kind: 'field', value: String(value)});
                }
            });
            return {kind: 'form_data', fields: fields};
        }
        if (typeof URLSearchParams !== 'undefined' && body instanceof URLSearchParams) {
            return {kind: 'url_search_params', value: String(body)};
        }
        if (typeof body === 'string') {
            const truncated = body.length > DC_REPLAY_BODY_LIMIT;
            const text = truncated ? body.slice(0, DC_REPLAY_BODY_LIMIT) : body;
            let parsed = null;
            try { parsed = JSON.parse(text); } catch (_) {}
            return {
                kind: parsed ? 'json' : 'text',
                value: parsed || text,
                chars: body.length,
                truncated: truncated,
            };
        }
        if (body && typeof body === 'object'
            && typeof body.size === 'number'
            && typeof body.type === 'string') {
            return {kind: 'blob', size: body.size, type: body.type};
        }
        return {kind: 'unknown', detail: Object.prototype.toString.call(body)};
    }

    function shouldRecordReplay(path) {
        if (!path || path.indexOf('/api/') !== 0) return false;
        const quiet = new Set([
            '/api/version',
            '/api/model-info',
            '/api/load-model/status',
            '/api/brand',
        ]);
        return !quiet.has(path);
    }

    function installReplayRecorder() {
        if (!window.fetch || window.__dcWbReplayFetchWrapped) return;
        const nativeFetch = window.fetch.bind(window);
        window.__dcWbReplayFetchWrapped = true;
        window.fetch = function (input, init) {
            let method = (init && init.method) || 'GET';
            if ((!init || !init.method) && input && input.method) method = input.method;
            method = String(method || 'GET').toUpperCase();
            const parts = replayUrlParts(input);
            const record = shouldRecordReplay(parts.path);
            const t0 = performance.now();
            let entry = null;
            if (record) {
                entry = {
                    ts: new Date().toISOString(),
                    page: window.location.pathname,
                    nav_key: document.body.getAttribute('data-nav') || '',
                    method: method,
                    path: parts.path,
                    query: parts.query,
                    url: parts.url,
                    request: serializeReplayBody(init && init.body),
                    status: 'pending',
                };
                replayEntries().push(entry);
            }
            return nativeFetch(input, init).then(function (resp) {
                if (entry) {
                    const dt = Math.round(performance.now() - t0);
                    entry.status = resp.status;
                    entry.ok = resp.ok;
                    entry.elapsed_ms = dt;
                    entry.response_content_type = resp.headers.get('content-type') || '';
                    try {
                        resp.clone().text().then(function (text) {
                            const truncated = text.length > DC_REPLAY_TEXT_LIMIT;
                            const kept = truncated ? text.slice(0, DC_REPLAY_TEXT_LIMIT) : text;
                            entry.response_chars = text.length;
                            entry.response_truncated = truncated;
                            entry.response_text = kept;
                            if (!truncated && /json/i.test(entry.response_content_type || '')) {
                                try { entry.response_json = JSON.parse(kept); } catch (_) {}
                            }
                        }).catch(function (err) {
                            entry.response_read_error = String((err && err.message) || err);
                        });
                    } catch (err) {
                        entry.response_read_error = String((err && err.message) || err);
                    }
                }
                return resp;
            }).catch(function (err) {
                if (entry) {
                    entry.status = 'fetch_error';
                    entry.ok = false;
                    entry.elapsed_ms = Math.round(performance.now() - t0);
                    entry.error = String((err && err.message) || err);
                }
                throw err;
            });
        };
    }

    function downloadReplayJson() {
        const navKey = document.body.getAttribute('data-nav') || 'page';
        const payload = {
            schema_version: 'duecare.browser_replay_log.v1',
            captured_at: new Date().toISOString(),
            origin: window.location.origin,
            page: window.location.pathname,
            nav_key: navKey,
            entry_count: replayEntries().length,
            entries: replayEntries(),
            note: (
                'This local browser replay log is intended for synthetic demo '
                + 'recording and debugging. Review before sharing if real case '
                + 'material was used.'
            ),
        };
        const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const stamp = new Date().toISOString().replace(/[:.]/g, '-');
        const a = document.createElement('a');
        a.href = url;
        a.download = 'duecare-' + navKey + '-replay-' + stamp + '.json';
        a.click();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        if (window.dcWbPageLog && window.dcWbPageLog.ok) {
            window.dcWbPageLog.ok('Downloaded replay JSON', payload.entry_count + ' API event(s)');
        }
    }

    function wireReplayDownload() {
        const btn = document.getElementById('dc-wb-replay-btn');
        if (!btn) return;
        btn.addEventListener('click', downloadReplayJson);
        window.dcWbReplayEntries = replayEntries;
        window.dcWbDownloadReplayJson = downloadReplayJson;
    }

    function ensureActivityLogScript(cb) {
        if (window.dcActivityLog) {
            cb();
            return;
        }
        const existing = document.getElementById('dc-activity-log-js');
        if (existing) {
            existing.addEventListener('load', cb, {once: true});
            return;
        }
        const script = document.createElement('script');
        script.id = 'dc-activity-log-js';
        script.src = '/static/_activity_log.js';
        script.defer = true;
        script.addEventListener('load', cb, {once: true});
        document.body.appendChild(script);
    }

    function shouldAutoLogFetch(path) {
        if (!path || path.indexOf('/api/') !== 0) return false;
        const quiet = new Set([
            '/api/version',
            '/api/model-info',
            '/api/load-model/status',
            '/api/brand',
        ]);
        if (quiet.has(path)) return false;
        return true;
    }

    function instrumentFetchForAutoLog(log) {
        if (!log || !window.fetch || window.__dcWbAutoLogFetchWrapped) return;
        const nativeFetch = window.fetch.bind(window);
        window.__dcWbAutoLogFetchWrapped = true;
        window.fetch = function (input, init) {
            let method = (init && init.method) || 'GET';
            let path = '';
            try {
                const rawUrl = typeof input === 'string'
                    ? input
                    : (input && input.url) || '';
                const url = new URL(rawUrl, window.location.origin);
                path = url.pathname;
                if ((!init || !init.method) && input && input.method) {
                    method = input.method;
                }
            } catch (_) {
                path = '';
            }
            method = String(method || 'GET').toUpperCase();
            const shouldLog = shouldAutoLogFetch(path);
            const t0 = performance.now();
            if (shouldLog) log.net(method + ' ' + path);
            return nativeFetch(input, init).then(function (resp) {
                if (shouldLog) {
                    const dt = Math.round(performance.now() - t0);
                    const fn = resp.ok ? log.ok : log.err;
                    fn('HTTP ' + resp.status + ' (' + dt + 'ms)', method + ' ' + path);
                }
                return resp;
            }).catch(function (err) {
                if (shouldLog) {
                    log.err('Fetch failed', method + ' ' + path + ' | ' + ((err && err.message) || err));
                }
                throw err;
            });
        };
    }

    function ensureDefaultActivityLog() {
        if (document.querySelector('.dc-activity-log')
            || document.querySelector('.dc-wb-auto-log-card')) {
            return;
        }
        const navKey = document.body.getAttribute('data-nav') || 'page';
        const card = document.createElement('section');
        card.className = 'dc-wb-auto-log-card';
        card.setAttribute('aria-label', 'Activity log');

        const title = document.createElement('h2');
        title.textContent = 'Activity log';
        const sub = document.createElement('span');
        sub.textContent = ' page activity and API calls';
        title.appendChild(sub);
        card.appendChild(title);

        const logHost = document.createElement('div');
        logHost.className = 'dc-activity-log';
        logHost.id = 'dc-wb-auto-log';
        logHost.setAttribute('role', 'log');
        logHost.setAttribute('aria-label', 'Activity log');
        logHost.setAttribute('aria-live', 'polite');
        const idle = document.createElement('div');
        idle.className = 'dc-log-idle';
        idle.textContent = 'No page activity yet.';
        logHost.appendChild(idle);
        card.appendChild(logHost);

        const target = document.querySelector('main') || document.body;
        target.appendChild(card);

        ensureActivityLogScript(function () {
            if (!window.dcActivityLog) return;
            const log = window.dcActivityLog.attach(logHost, {
                idlePlaceholder: 'No page activity yet.',
            });
            window.dcWbPageLog = log;
            log.info('Page loaded', navKey + ' | ' + window.location.pathname);
            instrumentFetchForAutoLog(log);
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
                else openModelPopover({required: false});
            });
        }
        if (closeBtn) closeBtn.addEventListener('click', closeModelPopover);
        if (loadBtn) loadBtn.addEventListener('click', loadSelectedModel);
        if (refreshBtn) refreshBtn.addEventListener('click', refreshModelLoaderStatus);
        const unloadBtn = document.getElementById('dc-wb-model-unload');
        if (unloadBtn) unloadBtn.addEventListener('click', unloadCurrentModel);
        const preflightRefresh = document.getElementById('dc-wb-model-preflight-refresh');
        if (preflightRefresh) preflightRefresh.addEventListener('click', refreshModelPreflight);
        const forceChk = document.getElementById('dc-wb-model-force');
        if (forceChk) forceChk.addEventListener('change', function () {
            // When preflight is blocking, the Load button is gated to
            // the Force toggle. Keep it in sync without re-fetching.
            if (modelLastPreflight && !modelLastPreflight.ok) {
                const lb = document.getElementById('dc-wb-model-load');
                if (lb) lb.disabled = !forceChk.checked;
            }
        });
        const sel = modelSelectEl();
        if (sel) sel.addEventListener('change', function () {
            modelUserSelectedVariant = sel.value || '';
            renderSelectedModelDetail();
            // New variant has different disk + GPU footprint -- refresh.
            refreshModelPreflight();
        });
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
        window.dcWbLoadModelVariant = loadModelVariant;
        window.dcWbEnsureModelReady = isModelReadyForPage;
        window.dcWbModelStatus = function () { return modelLastStatus; };
        window.dcWbModelService = {
            open: openModelPopover,
            close: closeModelPopover,
            refresh: refreshModelLoaderStatus,
            loadSelected: loadSelectedModel,
            loadVariant: loadModelVariant,
            unload: unloadCurrentModel,
            preflight: refreshModelPreflight,
            lastPreflight: function () { return modelLastPreflight; },
            ensureReady: isModelReadyForPage,
            status: function () { return modelLastStatus; },
            variants: function () { return modelVariantMap; },
        };
        renderModelOptions(null, null);
    }

    function wireNavToggle() {
        const btn = document.getElementById('dc-wb-nav-toggle');
        const links = document.getElementById('dc-wb-nav-links');
        if (!btn || !links) return;
        btn.addEventListener('click', function () {
            const open = !document.body.classList.contains('dc-wb-nav-open');
            document.body.classList.toggle('dc-wb-nav-open', open);
            btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        links.addEventListener('click', function (event) {
            const target = event.target;
            if (target && target.tagName === 'A') {
                document.body.classList.remove('dc-wb-nav-open');
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    }

    async function isModelReadyForPage() {
        const state = await refreshModelLoaderStatus();
        if (state.info && state.info.loaded) return true;
        openModelPopover({required: true});
        return false;
    }

    function pageRequiresModelOnLoad() {
        const mode = document.body.getAttribute('data-model-gate') || '';
        if (mode === 'required') return true;
        if (mode === 'optional' || mode === 'disabled') return false;
        return modelRequiredNavKeys.has(document.body.getAttribute('data-nav') || '');
    }

    function wireShutdown() {
        const btn = document.getElementById('dc-wb-shutdown-btn');
        if (!btn) return;
        btn.addEventListener('click', function () {
            const ok = window.confirm(
                'Shut down the Kaggle kernel?\n\n' +
                'This will:\n' +
                '  - release GPU memory\n' +
                '  - close the cloudflared tunnel\n' +
                '  - make this URL unreachable until the kernel is restarted\n\n' +
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

    function dedupeWorkbenchChrome() {
        const shells = Array.from(document.querySelectorAll('.dc-wb-shell'));
        shells.slice(1).forEach(function (node) { node.remove(); });
        const shell = document.querySelector('.dc-wb-shell');
        if (shell) {
            shell.querySelectorAll('.dc-wb-model-overlay, .dc-wb-model-popover').forEach(function (node) {
                node.remove();
            });
        }
        const layers = Array.from(document.querySelectorAll('#dc-wb-model-layer, .dc-wb-model-layer'));
        layers.slice(1).forEach(function (node) { node.remove(); });
        return {
            shell: shell,
            layer: document.getElementById('dc-wb-model-layer'),
        };
    }

    function setupChrome(nav) {
        if (!nav || nav.getAttribute('data-dc-wb-wired') === 'true') return;
        nav.setAttribute('data-dc-wb-wired', 'true');
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
        installReplayRecorder();
        wireNavToggle();
        wireModelPopover();
        wireShutdown();
        wireClearChat();
        wireReplayDownload();
        ensureDefaultActivityLog();
        refreshStatus();
        refreshModelLoaderStatus().then(function (state) {
            const onModelsPage = (document.body.getAttribute('data-nav') || '') === 'models';
            if (!onModelsPage && pageRequiresModelOnLoad() && state.info && !state.info.loaded) {
                openModelPopover({required: true});
            }
        });
        // Light polling so the status strip stays current without blowing up
        // a phone battery: every 8 seconds.
        setInterval(function () {
            refreshStatus();
            refreshModelLoaderStatus();
        }, 8000);
    }

    function inject(html) {
        const tpl = document.createElement('div');
        tpl.innerHTML = html.trim();
        const templateShell = Array.from(tpl.children).find(function (node) {
            return node.classList && node.classList.contains('dc-wb-shell');
        });
        const templateLayer = Array.from(tpl.children).find(function (node) {
            return node.classList && node.classList.contains('dc-wb-model-layer');
        });

        let mounted = dedupeWorkbenchChrome();
        let nav = mounted.shell;
        if (!nav && templateShell) {
            nav = templateShell;
            document.body.insertBefore(nav, document.body.firstChild);
        }
        if (!document.getElementById('dc-wb-model-layer') && templateLayer) {
            if (nav && nav.nextSibling) document.body.insertBefore(templateLayer, nav.nextSibling);
            else if (nav) document.body.appendChild(templateLayer);
            else document.body.insertBefore(templateLayer, document.body.firstChild);
        }
        mounted = dedupeWorkbenchChrome();
        setupChrome(mounted.shell);
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
