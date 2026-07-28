(function () {
  "use strict";

  var script = document.currentScript;
  var basePath = (script && script.dataset.basePath || "").replace(/\/$/, "");
  var snapshotDate = script && script.dataset.snapshotDate || "unknown";
  var liveUrl = script && script.dataset.liveUrl || "https://duecare-ai.com";
  var originalFetch = window.fetch.bind(window);

  var snapshots = {
    "/api/demo/priority-examples": "/static/demo_priority_examples.json",
    "/api/hub/packs": "/static/snapshots/hub-packs.json",
    "/api/hub/knowledge-packs": "/static/snapshots/hub-knowledge-packs.json",
    "/api/knowledge/packs": "/static/snapshots/runtime-knowledge-packs.json",
    "/api/hub/status": "/static/snapshots/hub-status.json",
    "/api/hub/trends": "/static/snapshots/hub-trends.json"
  };
  var backendOnlyPages = new Set([
    "/contact",
    "/contribute",
    "/email-feedback",
    "/local-kb",
    "/login",
    "/newsletter",
    "/outreach",
    "/partners",
    "/submissions",
    "/submit-information",
    "/volunteer"
  ]);

  function localPath(path) {
    return basePath + path;
  }

  function logicalPath(url) {
    var path = url.pathname;
    if (basePath && (path === basePath || path.indexOf(basePath + "/") === 0)) {
      path = path.slice(basePath.length) || "/";
    }
    return path;
  }

  function blockedResponse(path, method) {
    return Promise.resolve(new Response(JSON.stringify({
      detail: "This continuity site is read-only; the server action is unavailable.",
      method: method,
      path: path,
      snapshot_date: snapshotDate
    }), {
      status: 503,
      headers: {"content-type": "application/json; charset=utf-8"}
    }));
  }

  function filteredPackResponse(response, url) {
    return response.json().then(function (payload) {
      var packs = Array.isArray(payload.packs) ? payload.packs : [];
      var filters = ["kind", "corridor", "jurisdiction", "tag", "status"];
      packs = packs.filter(function (pack) {
        return filters.every(function (key) {
          var wanted = url.searchParams.get(key);
          if (!wanted) return true;
          if (key === "tag") return Array.isArray(pack.tags) && pack.tags.indexOf(wanted) >= 0;
          if (key === "jurisdiction") {
            return Array.isArray(pack.jurisdictions) && pack.jurisdictions.indexOf(wanted) >= 0;
          }
          return String(pack[key] || "") === wanted;
        });
      });
      payload.packs = packs;
      payload.count = packs.length;
      payload.static_snapshot = true;
      payload.snapshot_date = snapshotDate;
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: {"content-type": "application/json; charset=utf-8"}
      });
    });
  }

  window.fetch = function (input, init) {
    var requestUrl = input instanceof Request ? input.url : String(input);
    var url = new URL(requestUrl, window.location.href);
    var method = String(
      init && init.method || input instanceof Request && input.method || "GET"
    ).toUpperCase();
    var path = logicalPath(url);
    if (url.origin !== window.location.origin && path.indexOf("/api") === 0) {
      return blockedResponse(path, method);
    }
    if (url.origin === window.location.origin && path.indexOf("/api") === 0) {
      if (method === "GET" && snapshots[path]) {
        var snapshotUrl = new URL(localPath(snapshots[path]), window.location.origin);
        return originalFetch(snapshotUrl.toString(), {cache: "no-store"}).then(function (response) {
          if (path === "/api/hub/packs") return filteredPackResponse(response, url);
          return response;
        });
      }
      return blockedResponse(path, method);
    }
    if (url.origin === window.location.origin && path.indexOf("/static/") === 0 && basePath) {
      url.pathname = localPath(path);
      return originalFetch(url.toString(), init);
    }
    return originalFetch(input, init);
  };

  function disableServerControls() {
    var pagePath = logicalPath(new URL(window.location.href));
    if (!backendOnlyPages.has(pagePath.replace(/\/$/, ""))) return;

    document.querySelectorAll("form").forEach(function (form) {
      form.addEventListener("submit", function (event) { event.preventDefault(); }, true);
      form.querySelectorAll("input, select, textarea, button").forEach(function (control) {
        control.disabled = true;
        control.setAttribute("aria-disabled", "true");
        control.title = "Unavailable on the read-only continuity site";
      });
      if (!form.querySelector(".dc-static-form-note")) {
        var note = document.createElement("p");
        note.className = "dc-static-form-note";
        note.textContent = "Read-only continuity copy: this form does not collect or transmit data.";
        form.insertBefore(note, form.firstChild);
      }
    });

    document.querySelectorAll("button").forEach(function (button) {
      if (!button.closest("form")) {
        button.disabled = true;
        button.setAttribute("aria-disabled", "true");
        button.title = "Unavailable on the read-only continuity site";
      }
    });
  }

  function disableApiLinks() {
    document.querySelectorAll("a").forEach(function (anchor) {
      var original = anchor.dataset.dcOriginalHref || anchor.getAttribute("href") || "";
      if (!original) return;
      var url;
      try { url = new URL(original, window.location.href); } catch (error) { return; }
      var path = logicalPath(url);
      var serverOnly = (
        anchor.dataset.dcStaticDisabled === "api" ||
        path.indexOf("/api/") === 0 ||
        path === "/api-docs" ||
        path === "/openapi.json" ||
        path === "/redoc"
      );
      if (!serverOnly) return;
      anchor.removeAttribute("href");
      anchor.classList.add("dc-static-disabled-link");
      anchor.setAttribute("aria-disabled", "true");
      anchor.title = "Server endpoint unavailable on the read-only continuity site";
    });
  }

  function addNotice() {
    document.body.classList.add("dc-static-fallback");
    if (document.querySelector(".dc-static-notice")) return;
    var notice = document.createElement("aside");
    notice.className = "dc-static-notice";
    notice.setAttribute("role", "status");
    notice.innerHTML = (
      "<strong>Read-only continuity preview.</strong> " +
      "Snapshot " + snapshotDate + ". Public pages and committed reference data work here; " +
      "submissions, accounts, automation, mutable APIs, and local-KB actions are disabled. " +
      "The current live service remains at <a href=\"" + liveUrl + "\">duecare-ai.com</a>."
    );
    var nav = document.querySelector("nav");
    if (nav && nav.parentNode) nav.parentNode.insertBefore(notice, nav.nextSibling);
    else document.body.insertBefore(notice, document.body.firstChild);
  }

  document.addEventListener("DOMContentLoaded", function () {
    addNotice();
    disableApiLinks();
    disableServerControls();
  });
}());
