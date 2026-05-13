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
 *   - attach(selectorOrEl, opts) -> {info, ok, warn, err, step, channel, clear}
 *       opts.idlePlaceholder  initial muted line; cleared on first event
 *       opts.maxEvents        cap retained events (default 500)
 *   - parseSSE(response, onEvent) helper for /api/chat/send-style streams.
 *   - progressRow(selectorOrEl, steps) decorates a row with progress dots.
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

    function _clearIdle() {
      const first = host.firstChild;
      if (
        first &&
        first.classList &&
        (first.classList.contains('dc-log-idle') ||
          first.classList.contains('wb-muted'))
      ) {
        while (host.firstChild) host.removeChild(host.firstChild);
      }
    }
    function _trim() {
      while (host.childElementCount > maxEvents) {
        host.removeChild(host.firstChild);
      }
    }
    function _emit(tag, msg, detail) {
      _clearIdle();
      const row = document.createElement('div');
      row.className = 'dc-log-event';
      const tsSpan = document.createElement('span');
      tsSpan.className = 'dc-log-ts';
      tsSpan.textContent = '[' + nowTs() + '] ';
      row.appendChild(tsSpan);
      if (activeChannel) {
        const chSpan = document.createElement('span');
        chSpan.className = 'dc-log-channel-' + activeChannel;
        chSpan.textContent = '[' + activeChannel + '] ';
        row.appendChild(chSpan);
      }
      const tagSpan = document.createElement('span');
      tagSpan.className = 'dc-log-tag-' + (tag || 'info');
      tagSpan.textContent = String(msg == null ? '' : msg);
      row.appendChild(tagSpan);
      if (detail) {
        const detSpan = document.createElement('div');
        detSpan.className = 'dc-log-detail';
        detSpan.textContent = String(detail).slice(0, 800);
        row.appendChild(detSpan);
      }
      host.appendChild(row);
      _trim();
      host.scrollTop = host.scrollHeight;
    }
    function clear() {
      while (host.firstChild) host.removeChild(host.firstChild);
      if (opts.idlePlaceholder) {
        const d = document.createElement('div');
        d.className = 'dc-log-idle';
        d.textContent = opts.idlePlaceholder;
        host.appendChild(d);
      }
    }
    if (opts.idlePlaceholder && !host.firstChild) clear();
    return {
      info: function (msg, detail) { _emit('info', msg, detail); },
      ok:   function (msg, detail) { _emit('ok',   msg, detail); },
      warn: function (msg, detail) { _emit('warn', msg, detail); },
      err:  function (msg, detail) { _emit('err',  msg, detail); },
      step: function (msg, detail) { _emit('step', msg, detail); },
      net:  function (msg, detail) { _emit('net',  msg, detail); },
      anon: function (msg, detail) { _emit('anon', msg, detail); },
      channel: function (label) { activeChannel = label || null; },
      clear: clear,
      host: host,
    };
  }
  function _noopLog() {
    const n = function () {};
    return {info: n, ok: n, warn: n, err: n, step: n, net: n, anon: n,
            channel: n, clear: n, host: null};
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
