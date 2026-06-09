/* Shared knowledge-object (envelope) card renderer.
 *
 * One renderer for every page that shows an anonymized KnowledgeObject
 * envelope (knowledge.html drafts, search.html drafts, future federation
 * surfaces), so provenance badges, integrity hashes, and the JSON body
 * read identically everywhere. Built with createElement + textContent
 * only -- no innerHTML on dynamic content.
 *
 * API:
 *   window.dcEnvelopeCard.render(env, opts) -> HTMLElement
 *     opts.className  card class (default "wb-card dc-envelope-card")
 *     opts.title      optional bold first line (search-style cards)
 *     opts.subtitle   optional muted second line
 *     opts.statusId / opts.statusText   optional status span in the header
 *     opts.actions    [{label, id, title, primary, style, onClick}]
 *   window.dcEnvelopeCard.badges(env) -> DocumentFragment of provenance pills
 */
(function () {
  'use strict';

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function pill(stateClass, text, title) {
    var span = el('span', 'dc-gemma-mark ' + stateClass, text);
    if (title) span.title = title;
    return span;
  }

  function badges(env) {
    var ext = (env && env.extensions) || {};
    var prov = (env && env.provenance) || {};
    var frag = document.createDocumentFragment();
    var gemmaError = ext.gemma_error ? String(ext.gemma_error) : '';
    var usedGemma = (ext.gemma_drafted === true || ext.model_call_requested === true)
      && ext.model_call_available === true
      && !ext.fallback && !gemmaError;
    if (gemmaError) {
      frag.appendChild(pill('is-unavailable', 'Deterministic (Gemma 4 errored)',
        'Gemma 4 was attempted but errored; the deterministic template is shown instead.'));
    } else if (usedGemma) {
      frag.appendChild(pill('is-done', 'Gemma 4 refined',
        'Gemma 4 actually refined this draft (server confirmed model_call_available + no fallback + no error).'));
    } else {
      frag.appendChild(pill('is-optional', 'Deterministic',
        'Server returned the deterministic template for this draft.'));
    }
    if (ext.noise_scrubbed_before_gemma === true) {
      frag.appendChild(pill('is-done', 'Noise scrubbed',
        'Source text was scrubbed of kernel run IDs, /kaggle/working/... paths, ZIP/JSONL filenames, and synthetic case folder names before this draft was generated, so the saved fact reads as anonymized prose instead of build-log fragments.'));
    }
    if (ext.standardized_shape === true) {
      frag.appendChild(pill('is-done', 'Standard shape',
        'Envelope content was normalized to the canonical fact schema: same field names, field order, ILO indicator vocabulary, corridor format across every page.'));
    }
    if (ext.polished_by_gemma === true) {
      frag.appendChild(pill('is-done', 'Polished x' + (ext.polish_passes || 1),
        'Iterative Gemma 4 polish ran: critique pass then rewrite pass, followed by re-standardization.'));
    }
    if (prov.content_sha256) {
      frag.appendChild(pill('is-done', 'sha256 ' + String(prov.content_sha256).slice(0, 8),
        'Integrity hash stamped at promote/serve time: sha256 over sorted-key compact JSON of `content`. Any recipient (or peer node) can recompute it to verify the envelope was not modified in transit. Full hash: ' + prov.content_sha256));
    }
    if (prov.vetted === true) {
      frag.appendChild(pill('is-done', 'Hub vetted',
        'A human curator on the public hub approved this entry before it was served.'));
    }
    return frag;
  }

  function errorBanner(ext) {
    var msg = ext.gemma_error ? String(ext.gemma_error).slice(0, 280) : '';
    if (!msg) return null;
    var box = el('div');
    box.style.cssText = 'margin: 8px 0; padding: 9px 12px; background: oklch(0.97 0.025 25); border: 1px solid oklch(0.78 0.10 45); border-left: 4px solid oklch(0.55 0.18 25); border-radius: 6px; font-size: 12px; line-height: 1.5; color: oklch(0.32 0.10 25);';
    var head = el('b', null, 'Gemma 4 did not refine this envelope.');
    head.style.cssText = 'display:block; margin-bottom:3px;';
    box.appendChild(head);
    box.appendChild(document.createTextNode('Reason: ' + msg));
    var hint = el('div');
    hint.style.cssText = 'margin-top:6px; opacity:0.85;';
    var low = msg.toLowerCase();
    hint.textContent = (low.indexOf('cuda out of memory') >= 0 || low.indexOf('oom') >= 0)
      ? 'Recovery: load a smaller Gemma 4 variant (E4B / E2B) via the Model picker, OR Shutdown + reload the kernel to clear GPU state. The deterministic template below is still usable for promotion.'
      : 'The deterministic template below is still usable for promotion; check the activity log for kernel state.';
    box.appendChild(hint);
    return box;
  }

  function render(env, opts) {
    env = env || {};
    opts = opts || {};
    var ext = env.extensions || {};
    var card = el(opts.tag || 'section', opts.className || 'wb-card dc-envelope-card');
    if (!opts.className) {
      card.style.cssText = 'background:#FAF9F4; margin:8px 0; padding:12px;';
    }
    if (opts.title) {
      var t = el('div', null, opts.title);
      t.style.cssText = 'font-size: 13px; font-weight: 600;';
      card.appendChild(t);
    }
    if (opts.subtitle) {
      card.appendChild(el('div', 'wb-muted', opts.subtitle));
    }
    var head = el('div');
    head.style.cssText = 'display:flex; justify-content:space-between; gap:8px; flex-wrap:wrap; align-items:center; margin-top:' + (opts.title ? '6px' : '0') + ';';
    var left = el('div');
    left.appendChild(el('b', null, env.knowledge_object_type || 'knowledge_object'));
    left.appendChild(document.createTextNode(' '));
    left.appendChild(el('span', 'wb-muted', env.id || ''));
    left.appendChild(document.createTextNode(' '));
    left.appendChild(badges(env));
    head.appendChild(left);
    var right = el('div');
    right.style.cssText = 'display:flex; gap:8px; align-items:center; flex-wrap:wrap;';
    if (opts.statusId) {
      var status = el('span', 'wb-muted', opts.statusText || '');
      status.id = opts.statusId;
      right.appendChild(status);
    }
    (opts.actions || []).forEach(function (action) {
      var btn = el('button', action.primary ? 'wb-btn-primary' : 'wb-btn-secondary', action.label);
      btn.type = 'button';
      if (action.id) btn.id = action.id;
      if (action.title) btn.title = action.title;
      if (action.style) btn.style.cssText = action.style;
      if (typeof action.onClick === 'function') btn.addEventListener('click', action.onClick);
      right.appendChild(btn);
    });
    head.appendChild(right);
    card.appendChild(head);
    var banner = errorBanner(ext);
    if (banner) card.appendChild(banner);
    var pre = el('pre', null, JSON.stringify(env, null, 2));
    pre.style.cssText = 'background:#FFF; border:1px solid #DDD8C9; padding:10px; border-radius:6px; font-size:11.5px; overflow:auto; max-height:240px;';
    card.appendChild(pre);
    return card;
  }

  window.dcEnvelopeCard = { render: render, badges: badges };
})();
