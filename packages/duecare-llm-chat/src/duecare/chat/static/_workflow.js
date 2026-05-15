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
        const state = _stateEl(el, idx);
        if (state) {
          state.textContent = complete
            ? labels.done
            : (open ? labels.active : labels.waiting);
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
