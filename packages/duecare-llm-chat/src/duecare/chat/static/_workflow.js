/* DueCare workbench - shared guided-workflow helper.
 *
 * Process, Knowledge, Search, Share, and Sync all use the same interaction
 * pattern: a visible sequence of detail panels where one step is emphasized,
 * prior steps are marked complete, and optional state labels read
 * Ready/Active/Waiting/Done. This helper keeps that behavior consistent while
 * allowing each page to keep its own markup and domain-specific controls.
 */
(function () {
  'use strict';

  function _el(value) {
    return typeof value === 'string' ? document.getElementById(value) : value;
  }

  function _resolveElements(opts) {
    if (opts.elements) return Array.from(opts.elements).filter(Boolean);
    return (opts.ids || []).map(_el).filter(Boolean);
  }

  function createStepper(opts) {
    opts = opts || {};
    const completeClass = opts.completeClass || 'complete';
    const labels = Object.assign(
      {done: 'Done', active: 'Active', waiting: 'Waiting'},
      opts.labels || {}
    );
    const elements = _resolveElements(opts);
    const clamp = opts.clamp !== false;

    function _activeIndex(active) {
      let idx = Number(active);
      if (!Number.isFinite(idx)) idx = 0;
      idx = Math.trunc(idx);
      if (clamp) idx = Math.max(0, Math.min(elements.length - 1, idx));
      return idx;
    }

    function _stateEl(el, idx) {
      if (typeof opts.stateIdFor === 'function') {
        return _el(opts.stateIdFor(el.id, idx, el));
      }
      if (opts.stateIds) return _el(opts.stateIds[idx]);
      return el && el.id ? _el(el.id + '-state') : null;
    }

    function _stateKey(complete, open) {
      if (complete) return 'done';
      if (open) return 'active';
      return 'waiting';
    }

    function _writeStatePill(state, key, label) {
      // Backward-compatible writer: if the state element is a .dc-pill with
      // a .dc-pill-label child, preserve the dot + structure and only swap
      // the label text and the is-* modifier class. Otherwise fall back to
      // plain textContent.
      const labelChild = state.querySelector
        ? state.querySelector('.dc-pill-label')
        : null;
      if (labelChild) {
        labelChild.textContent = label;
        state.classList.remove('is-waiting', 'is-active', 'is-running', 'is-done', 'is-ready');
        // Design vocabulary: Active step uses the is-running pill style.
        state.classList.add(key === 'active' ? 'is-running' : ('is-' + key));
      } else {
        state.textContent = label;
      }
    }

    function set(active) {
      const activeIdx = _activeIndex(active);
      elements.forEach((el, idx) => {
        const complete = typeof opts.completeWhen === 'function'
          ? !!opts.completeWhen(idx, activeIdx, el)
          : idx < activeIdx;
        const open = typeof opts.openWhen === 'function'
          ? !!opts.openWhen(idx, activeIdx, el, elements.length)
          : idx === activeIdx;
        el.classList.toggle(completeClass, complete);
        if (opts.removeCompleteClass) {
          el.classList.remove(opts.removeCompleteClass);
        }
        if ('open' in el) el.open = open;
        // Mirror lifecycle to a data-state attribute so CSS selectors like
        // .dc-step[data-state="done"] can react without extra wiring.
        const key = _stateKey(complete, open);
        if (el.dataset) el.dataset.state = key;
        const state = _stateEl(el, idx);
        if (state) {
          const label = complete ? labels.done : (open ? labels.active : labels.waiting);
          _writeStatePill(state, key, label);
        }
      });
      return activeIdx;
    }

    function markComplete(indexOrId, on) {
      const el = typeof indexOrId === 'number'
        ? elements[indexOrId]
        : _el(indexOrId);
      if (el) el.classList.toggle(completeClass, on !== false);
    }

    return {set: set, markComplete: markComplete, elements: elements};
  }

  window.dcWorkflow = {
    createStepper: createStepper,
  };
})();
