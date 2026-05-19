/* DueCare workbench - shared activity-log helper.
 *
 * Standardizes the dark-themed real-time event log that appears on
 * Chat / Compare / Process Files / Knowledge / Search / Sync.
 * Without this, each page hand-rolled its own `wbLog()` with slightly
 * different markup, color rules, and DOM construction, and several
 * versions used innerHTML with un-escaped strings.
 *
 * Usage:
 *
 *   <link rel="stylesheet" href="/static/_chrome.css">   <!-- provides .dc-activity-log styles -->
 *   <div id="my-log" class="dc-activity-log">
 *     <div class="dc-log-idle">Waiting...</div>
 *   </div>
 *   <script src="/static/_activity_log.js" defer></script>
 *   ...
 *   const log = window.dcActivityLog.attach('#my-log', {idlePlaceholder: 'Waiting...'});
 *   log.info('POST /api/...');
 *   log.step('grep starting');
 *   log.ok('grep fired (12ms)', 'hits=3');
 *   log.err('HTTP 500', 'short error detail');
 *
 * API:
 *   - attach(selectorOrEl, opts) -> {info, ok, warn, err, step, channel,
 *                                     clear, toJSON, copy, host}
 *       opts.idlePlaceholder  initial muted line; cleared on first event
 *       opts.maxEvents        cap retained events (default 500)
 *       opts.toolbar          "copy-json" injects a small toolbar with a
 *                              "Copy JSON" link as the host's first child.
 *                              Equivalent to setting data-toolbar="copy-json"
 *                              on the host element.
 *   - parseSSE(response, onEvent) helper for /api/chat/send-style streams.
 *   - progressRow(selectorOrEl, steps) decorates a row with progress dots.
 *
 *   The returned object also exposes:
 *   - toJSON()  -> shallow copy of the in-memory event array
 *                  (each row: {ts, level, channel, msg, detail?})
 *   - copy()    -> writes JSON.stringify(events, null, 2) to the clipboard
 *                  via navigator.clipboard. Returns a Promise that
 *                  resolves to true on success, false on failure.
 *
 * All text content is set via textContent (never innerHTML), so no
 * markup ever flows through unescaped.
 */
(function () {
  'use strict';

  function $(selectorOrEl) {
    return typeof selectorOrEl === 'string'
      ? document.querySelector(selectorOrEl)
      : selectorOrEl;
  }
  function nowTs() {
    return new Date().toISOString().slice(11, 19);
  }

  function attach(selectorOrEl, opts) {
    const host = $(selectorOrEl);
    if (!host) {
      console.warn('[dcActivityLog] host not found:', selectorOrEl);
      return _noopLog();
    }
    opts = opts || {};
    const maxEvents = opts.maxEvents || 500;
    let activeChannel = null;

    // Mirror of every emitted event so the log is copyable as JSON.
    // Capped by maxEvents in lock-step with the DOM trim. Each entry is
    // {ts, level, channel, msg, detail?} -- the shape the design contract
    // expects for the "Copy JSON" panel-header link (§2.3).
    const events = [];

    // Toolbar -- opt-in via opts.toolbar === "copy-json" or
    // host.dataset.toolbar === "copy-json". Mounted lazily so existing
    // pages that do not opt in render identically.
    let toolbarEl = null;
    function _mountToolbar() {
      if (toolbarEl) return;
      const wantsToolbar =
        opts.toolbar === 'copy-json' ||
        (host.dataset && host.dataset.toolbar === 'copy-json');
      if (!wantsToolbar) return;
      toolbarEl = document.createElement('div');
      toolbarEl.className = 'dc-activity-log-toolbar';
      const label = document.createElement('span');
      label.className = 'dc-activity-log-toolbar-label';
      label.textContent = opts.toolbarLabel || 'Activity log';
      toolbarEl.appendChild(label);
      const spacer = document.createElement('span');
      spacer.className = 'dc-activity-log-toolbar-spacer';
      toolbarEl.appendChild(spacer);
      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.className = 'dc-activity-log-copy';
      copyBtn.textContent = 'Copy JSON';
      copyBtn.setAttribute('aria-label', 'Copy activity log as JSON');
      copyBtn.addEventListener('click', function () {
        api.copy().then(function (ok) {
          if (!ok) return;
          const prev = copyBtn.textContent;
          copyBtn.textContent = 'Copied';
          copyBtn.classList.add('is-copied');
          setTimeout(function () {
            copyBtn.textContent = prev;
            copyBtn.classList.remove('is-copied');
          }, 1200);
        });
      });
      toolbarEl.appendChild(copyBtn);
      host.insertBefore(toolbarEl, host.firstChild);
    }

    function _clearIdle() {
      // The first child may be the toolbar (always kept) or the idle
      // placeholder (cleared on first event). Skip the toolbar.
      let first = host.firstElementChild;
      if (first === toolbarEl) first = first.nextElementSibling;
      if (
        first &&
        first.classList &&
        (first.classList.contains('dc-log-idle') ||
          first.classList.contains('wb-muted'))
      ) {
        host.removeChild(first);
      }
    }
    function _trim() {
      // The toolbar is the first child when present; count only event rows.
      const eventCount =
        host.childElementCount - (toolbarEl && toolbarEl.parentNode ? 1 : 0);
      let excess = eventCount - maxEvents;
      while (excess > 0) {
        // First removable event row sits after the toolbar.
        const target = toolbarEl && toolbarEl.parentNode
          ? toolbarEl.nextElementSibling
          : host.firstElementChild;
        if (!target) break;
        host.removeChild(target);
        excess -= 1;
      }
      while (events.length > maxEvents) events.shift();
    }
    function _emit(tag, msg, detail) {
      _clearIdle();
      const ts = nowTs();
      const event = {
        ts: ts,
        level: String(tag || 'info'),
        channel: activeChannel || null,
        msg: String(msg == null ? '' : msg),
      };
      if (detail != null && detail !== '') {
        event.detail = String(detail).slice(0, 800);
      }
      events.push(event);
      const row = document.createElement('div');
      row.className = 'dc-log-event';
      const tsSpan = document.createElement('span');
      tsSpan.className = 'dc-log-ts';
      tsSpan.textContent = '[' + ts + '] ';
      row.appendChild(tsSpan);
      if (activeChannel) {
        const chSpan = document.createElement('span');
        chSpan.className = 'dc-log-channel-' + activeChannel;
        chSpan.textContent = '[' + activeChannel + '] ';
        row.appendChild(chSpan);
      }
      const tagSpan = document.createElement('span');
      tagSpan.className = 'dc-log-tag-' + event.level;
      tagSpan.textContent = event.msg;
      row.appendChild(tagSpan);
      if (event.detail) {
        const detSpan = document.createElement('div');
        detSpan.className = 'dc-log-detail';
        detSpan.textContent = event.detail;
        row.appendChild(detSpan);
      }
      host.appendChild(row);
      _trim();
      host.scrollTop = host.scrollHeight;
    }
    function clear() {
      // Remove every child except the toolbar (which is structural).
      Array.from(host.childNodes).forEach(function (node) {
        if (node === toolbarEl) return;
        host.removeChild(node);
      });
      events.length = 0;
      if (opts.idlePlaceholder) {
        const d = document.createElement('div');
        d.className = 'dc-log-idle';
        d.textContent = opts.idlePlaceholder;
        if (toolbarEl && toolbarEl.parentNode) {
          host.insertBefore(d, toolbarEl.nextSibling);
        } else {
          host.appendChild(d);
        }
      }
    }

    _mountToolbar();
    if (opts.idlePlaceholder && !host.firstChild) clear();
    // If the toolbar is present and there are no events yet, surface
    // the idle placeholder right under the toolbar instead of as the
    // raw first child.
    if (
      opts.idlePlaceholder &&
      toolbarEl &&
      host.childElementCount === 1
    ) {
      const d = document.createElement('div');
      d.className = 'dc-log-idle';
      d.textContent = opts.idlePlaceholder;
      host.appendChild(d);
    }

    const api = {
      info: function (msg, detail) { _emit('info', msg, detail); },
      ok:   function (msg, detail) { _emit('ok',   msg, detail); },
      warn: function (msg, detail) { _emit('warn', msg, detail); },
      err:  function (msg, detail) { _emit('err',  msg, detail); },
      step: function (msg, detail) { _emit('step', msg, detail); },
      net:  function (msg, detail) { _emit('net',  msg, detail); },
      anon: function (msg, detail) { _emit('anon', msg, detail); },
      channel: function (label) { activeChannel = label || null; },
      clear: clear,
      toJSON: function () { return events.slice(); },
      copy: async function () {
        const payload = JSON.stringify(events, null, 2);
        // Bail honestly if the clipboard API is unavailable (insecure
        // origin, sandboxed iframe, ancient browser). Returning false
        // lets the caller show a real failure state instead of a fake
        // "Copied" tick.
        if (
          typeof navigator === 'undefined' ||
          !navigator.clipboard ||
          typeof navigator.clipboard.writeText !== 'function'
        ) {
          console.warn('[dcActivityLog.copy] navigator.clipboard unavailable');
          return false;
        }
        try {
          await navigator.clipboard.writeText(payload);
          return true;
        } catch (err) {
          console.warn('[dcActivityLog.copy] clipboard write failed', err);
          return false;
        }
      },
      host: host,
    };
    return api;
  }
  function _noopLog() {
    const n = function () {};
    const empty = function () { return []; };
    const reject = function () { return Promise.resolve(false); };
    return {info: n, ok: n, warn: n, err: n, step: n, net: n, anon: n,
            channel: n, clear: n, toJSON: empty, copy: reject, host: null};
  }

  /**
   * Parse an SSE-style streaming response (text/event-stream) and call
   * `onEvent(jsonPayload)` for every `data: {...}` line. Returns a
   * promise that resolves when the stream closes.
   *
   * Works for /api/chat/send, /api/grade-deep-stream, and similar.
   */
  async function parseSSE(response, onEvent) {
    if (!response.ok) {
      const body = await response.text();
      throw new Error('HTTP ' + response.status + ': ' + body.slice(0, 200));
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const frames = buffer.split('\n\n');
      buffer = frames.pop() || '';
      for (const frame of frames) {
        const dataLine = frame.split('\n').find(l => l.startsWith('data: '));
        if (!dataLine) continue;
        let evt;
        try { evt = JSON.parse(dataLine.substring(6)); }
        catch (e) { continue; }
        try { onEvent(evt); }
        catch (e) { console.warn('[dcActivityLog.parseSSE] onEvent threw', e); }
      }
    }
  }

  /**
   * Decorate a host element with a row of progress dots paired with
   * the log. Each dot corresponds to a "step" (e.g., a layer name)
   * and lights up as events arrive.
   */
  function progressRow(selectorOrEl, steps) {
    const host = $(selectorOrEl);
    if (!host) return _noopProgress();
    while (host.firstChild) host.removeChild(host.firstChild);
    host.classList.add('dc-progress-row');
    const dots = {};
    steps.forEach((step, i) => {
      const wrap = document.createElement('span');
      wrap.style.cssText = 'display:inline-flex; align-items:center; gap:4px;';
      const dot = document.createElement('span');
      dot.className = 'dc-progress-dot';
      dot.id = (host.id || 'dc-prog') + '-dot-' + step;
      wrap.appendChild(dot);
      const lbl = document.createElement('span');
      lbl.textContent = step;
      wrap.appendChild(lbl);
      host.appendChild(wrap);
      if (i < steps.length - 1) {
        host.appendChild(document.createTextNode(' '));
      }
      dots[step] = dot;
    });
    return {
      run:  function (step) { _setDot(dots[step], 'is-run'); },
      done: function (step) { _setDot(dots[step], 'is-done'); },
      err:  function (step) { _setDot(dots[step], 'is-err'); },
      reset: function () {
        Object.values(dots).forEach(d => {
          d.classList.remove('is-run', 'is-done', 'is-err');
        });
      },
    };
  }
  function _setDot(dot, cls) {
    if (!dot) return;
    dot.classList.remove('is-run', 'is-done', 'is-err');
    if (cls) dot.classList.add(cls);
  }
  function _noopProgress() {
    const n = function () {};
    return {run: n, done: n, err: n, reset: n};
  }

  window.dcActivityLog = {
    attach: attach,
    parseSSE: parseSSE,
    progressRow: progressRow,
  };
})();
