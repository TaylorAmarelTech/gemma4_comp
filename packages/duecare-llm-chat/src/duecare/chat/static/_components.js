/* DueCare shared widgets -- toast, loading, confirm, Cmd+K. */
(function () {
  'use strict';
  if (window.dcToast) return;

  function _ensureHost() {
    var host = document.getElementById('dc-toast-host');
    if (!host) {
      host = document.createElement('div');
      host.id = 'dc-toast-host';
      host.className = 'dc-toast-host';
      host.setAttribute('role', 'status');
      host.setAttribute('aria-live', 'polite');
      document.body.appendChild(host);
    }
    return host;
  }
  window.dcToast = function (msg, kind, ttl_ms) {
    kind = kind || 'info';
    ttl_ms = ttl_ms || 3500;
    var el = document.createElement('div');
    el.className = 'dc-toast dc-toast-' + kind;
    el.textContent = String(msg);
    _ensureHost().appendChild(el);
    setTimeout(function () {
      el.classList.add('dc-toast-out');
      setTimeout(function () { el.remove(); }, 200);
    }, ttl_ms);
    return el;
  };

  window.dcLoading = function (parentEl) {
    if (!parentEl) parentEl = document.body;
    var sk = document.createElement('div');
    sk.className = 'dc-skeleton-container';
    sk.innerHTML =
      '<span class="dc-skeleton dc-skeleton-line"></span>' +
      '<span class="dc-skeleton dc-skeleton-line"></span>' +
      '<span class="dc-skeleton dc-skeleton-line"></span>';
    parentEl.appendChild(sk);
    return { stop: function () { sk.remove(); } };
  };

  window.dcConfirm = function (msg) {
    return Promise.resolve(window.confirm(String(msg)));
  };

  window.dcCmdK = function () {
    var existing = document.getElementById('dc-cmdk-overlay');
    if (existing) {
      existing.classList.remove('dc-show');
      setTimeout(function () { existing.remove(); }, 140);
      return;
    }
    var overlay = document.createElement('div');
    overlay.id = 'dc-cmdk-overlay';
    overlay.className = 'dc-cmdk-overlay dc-show';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Tab switcher');

    var panel = document.createElement('div');
    panel.className = 'dc-cmdk-panel';
    var input = document.createElement('input');
    input.className = 'dc-cmdk-input';
    input.type = 'text';
    input.placeholder = 'Jump to a tab...';
    input.setAttribute('aria-label', 'Tab search');
    var list = document.createElement('ul');
    list.className = 'dc-cmdk-list';

    var links = Array.prototype.slice.call(
      document.querySelectorAll('.dc-wb-nav-links a[data-nav-key]')
    );
    function render(filter) {
      filter = (filter || '').toLowerCase();
      list.innerHTML = '';
      var matches = links.filter(function (a) {
        return (a.textContent + ' ' + (a.title || '')).toLowerCase().includes(filter);
      });
      if (!matches.length) {
        var none = document.createElement('li');
        none.className = 'dc-cmdk-item';
        none.style.color = 'var(--ink-4)';
        none.textContent = 'no matches';
        list.appendChild(none);
        return;
      }
      matches.forEach(function (a, i) {
        var li = document.createElement('li');
        li.className = 'dc-cmdk-item' + (i === 0 ? ' dc-cmdk-active' : '');
        li.setAttribute('role', 'option');
        var label = document.createElement('span');
        label.textContent = a.textContent.trim();
        var key = document.createElement('span');
        key.className = 'dc-cmdk-key';
        key.textContent = (a.getAttribute('data-nav-key') || '');
        li.appendChild(label);
        li.appendChild(key);
        li.onclick = function () { window.location.href = a.href; };
        list.appendChild(li);
      });
    }
    render('');
    input.addEventListener('input', function () { render(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.preventDefault(); window.dcCmdK(); return; }
      if (e.key === 'Enter') {
        e.preventDefault();
        var active = list.querySelector('.dc-cmdk-active') || list.querySelector('.dc-cmdk-item');
        if (active && active.onclick) active.click();
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        var items = Array.prototype.slice.call(list.querySelectorAll('.dc-cmdk-item'));
        var cur = list.querySelector('.dc-cmdk-active');
        var idx = items.indexOf(cur);
        if (idx < 0) idx = 0;
        var next = e.key === 'ArrowDown'
          ? Math.min(idx + 1, items.length - 1)
          : Math.max(idx - 1, 0);
        if (cur) cur.classList.remove('dc-cmdk-active');
        if (items[next]) items[next].classList.add('dc-cmdk-active');
      }
    });
    panel.appendChild(input);
    panel.appendChild(list);
    overlay.appendChild(panel);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) window.dcCmdK();
    });
    document.body.appendChild(overlay);
    setTimeout(function () { input.focus(); }, 0);
  };

  document.addEventListener('keydown', function (e) {
    var isMod = e.metaKey || e.ctrlKey;
    if (isMod && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      window.dcCmdK();
    }
  });
})();
