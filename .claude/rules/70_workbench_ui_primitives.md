# Workbench UI primitives -- recurring rules for every kernel page

> Auto-loaded by Claude Code at the project memory level. Applies to
> every `.html` file under
> `packages/duecare-llm-chat/src/duecare/chat/static/` and any new
> workbench page added later.

These rules capture conventions Taylor has confirmed multiple times
across the workbench surface. They are not negotiable per-page --
breaking one creates an inconsistency a reviewer will catch within
seconds of clicking around the kernel.

## 1. Every interactive page MUST have an Activity Log

If a page makes any HTTP call, drafts anything via Gemma, runs the
GREP / RAG / tools / online layers, processes a file, or persists
anything, it MUST render a live activity log so the reviewer can see
what is happening in real time.

### How

- Use the shared primitive from
  `packages/duecare-llm-chat/src/duecare/chat/static/_chrome.css`
  (`.dc-activity-log`, `.dc-log-event`, `.dc-log-ts`,
  `.dc-log-tag-{info,ok,warn,err,step,net,anon}`,
  `.dc-log-channel-{A,B}`, `.dc-log-detail`, `.dc-log-idle`).
- Use the shared JS helper from
  `packages/duecare-llm-chat/src/duecare/chat/static/_activity_log.js`
  via `window.dcActivityLog.attach(selector, {idlePlaceholder: '...'})`
  and the returned `{info, ok, warn, err, step, channel, clear}` API.
- Load `<script src="/static/_activity_log.js" defer></script>` in
  the page's `<head>`.

### Why

- One pattern across pages means a reviewer does not have to relearn
  the kernel five times.
- The activity log is also the kernel's transparency story for the
  rubric -- "real, not faked for demo" requires the reviewer can see
  exactly what each call did.

### What NOT to do

- Do not hand-roll a bespoke `wbLog()` in a new page. It will diverge.
- Do not use `innerHTML` to write log lines, even with escaping. Use
  `document.createElement` + `textContent` (the shared helper enforces
  this).
- Do not omit the activity log because "this page is simple". Even a
  one-click page should show the log so the reviewer can confirm the
  click actually did something.

## 2. Every multi-step or stateful page MUST emit per-step events

If the page invokes Gemma, the harness, or a multi-stage pipeline,
each step gets its own log event:

- `log.step('grep starting')`        -- step kicked off
- `log.ok('grep fired (12ms)', 'hits=3')`   -- step finished, fired
- `log.info('rag not fired')`        -- step finished, no-op
- `log.err('HTTP 500', body)`         -- step failed

For SSE streams (e.g., `/api/chat/send`), use
`window.dcActivityLog.parseSSE(response, onEvent)` to consume
`{type: "step_start"|"step_done"|"complete"|"error"}` frames and
fan them into the log. Do not poll, do not await `r.json()` on a
stream endpoint.

## 3. Every page that mutates global kernel state MUST be discoverable on Status

The Status page at `/static/status.html` is the canonical
"what does this kernel know right now" surface. When a page changes
runtime knowledge state (sync, import, promote, train, swap model,
etc.), the change MUST be reflected on Status either:

- via a hot-reload that bumps `/api/knowledge/list`'s output, OR
- via a `localStorage` counter that Status reads
  (current counters: `duecare:syncs-count`,
  `duecare:syncs-last-at`, `duecare:imports-count`,
  `duecare:imports-last-at`).

When adding a new mutation page, also:

1. Add a `localStorage` bump on the success path of the mutating call.
2. Add a stat card to `status.html` reading that counter.
3. If the mutation changes harness consumption/emission, update the
   harness consumption + emission table on `status.html` too.

## 4. Every page that produces or accepts artifacts MUST ship a sample

If a page accepts an upload, or produces a downloadable file (ZIP,
JSON, envelope, bundle), it MUST ship a **judge-safe sample artifact**
served under `/static/samples/` so a first-time reviewer can
round-trip the flow without hunting down a file.

### How

- Add the sample to `scripts/build_static_samples.py` (so it is
  regeneratable + deterministic -- fixed ZIP timestamps).
- Serve it at `/static/samples/<name>`.
- The page MUST surface BOTH a `Download sample` button (for review)
  AND a `Use sample` / `Try sample import` button (for one-click
  round-trip).
- The page must accept the same shape it produces (round-tripability
  is a hard requirement).
- All sample content must be composite/synthetic -- no real names,
  no real case numbers, no real PII (the `10_safety_gate.md` rule
  applies).

### Pages that currently comply

- `process.html`     -> `samples/case_files_sample.zip`
- `knowledge.html`   -> `samples/knowledge_object_sample.json`
                         and `samples/knowledge_bundle_sample.zip`
- `sync.html`        -> reuses the knowledge bundle sample
- `search.html`      -> drafts envelopes from search results

### Pages that need to comply when added

- Any new upload page
- Any new bundle/export page

## 5. Model loading default: ONE model at a time (opt-in for multi)

Loading a Gemma 4 fine-tune takes time (E4B ~30s, larger variants
1-3 minutes). Loading two simultaneously can OOM on a single T4 or
trigger expensive cold-starts. The kernel's **default behaviour is
single-model**: when a new model is requested, the previously loaded
one is unloaded first.

A user with adequate VRAM (single A100, dual T4, etc.) may want to
keep multiple models hot for instant comparison without the
reload penalty. That option lives on `/static/settings.html` as the
**Model loading mode** setting:

| Mode | Default? | Behaviour |
|---|---|---|
| `single` | yes | Load requested model; unload previous first. Predictable VRAM, single warm model. |
| `multi`  | no  | Keep loaded models resident until explicit unload. Faster comparison but VRAM grows. |

### Rules

- **NEVER** silently load a second model. If the user is in `single`
  mode and requests a new variant, the UI MUST show "Unloading X,
  loading Y..." with progress.
- **NEVER** make `multi` the default. The kernel cannot predict the
  user's VRAM, and an OOM on a judge-facing demo is a worse failure
  than a 30-second reload.
- The Settings page MUST surface the current mode prominently AND
  show a one-line caveat ("Loading/unloading takes 30-90s per
  variant; multi mode keeps models hot but uses more VRAM").
- Models page MUST show which model is currently loaded (and, in
  multi mode, which models are also resident).
- The activity log MUST log every load/unload event with timing.

### Persistence

- The mode is a per-device preference, persisted in
  `localStorage.setItem('duecare:model-load-mode', 'single' | 'multi')`.
- A future kernel-level endpoint (`POST /api/settings/model-load-mode`)
  may server-side this for shared instances, but the localStorage
  preference must remain authoritative for single-user kernels.

## 6. The shared chrome (nav + status row) MUST appear on every page

Every workbench page MUST:

- Link `/static/_chrome.css` in `<head>`
- Load `/static/_nav.js` with `defer`
- Set `<body data-nav="<key>">` matching its nav entry's
  `data-nav-key`
- Reuse `.wb-card`, `.wb-row`, `.wb-btn-primary`, `.wb-btn-secondary`,
  `.wb-pill`, `.wb-muted` from the shared chrome -- do not redefine
  these in a page-local `<style>` block.

A page-local `<style>` block is fine for page-unique decorations but
MUST NOT override the shared classes (the shared chrome is
load-bearing for accessibility and consistency).

## 7. Trust-boundary disclosure is mandatory on user-facing pages

Every page that processes user input, accepts an upload, or makes an
outbound call MUST surface a one-paragraph trust boundary at the
top, in the same `.wb-trust` / muted-green style as the existing
pages. State:

- Where the data goes (local kernel, hub, external API)
- What gets anonymized before it leaves the kernel (if anything)
- What the user can opt out of

Examples currently in place: `process.html` ("uploaded rows
processed locally..."), `knowledge.html` ("extraction runs
locally..."), `sync.html` ("only public pre-anonymized envelopes
downloaded..."), `share.html` (anonymizer pipeline). Do not omit.

## 8. Status snapshots: lightweight, regeneratable, opt-in heavy data

The Status page should query lightweight endpoints (`/api/knowledge/list`,
`/api/version`, `/api/model-info`, `/api/search/backends`) plus
`localStorage` on page load. It MUST NOT trigger any expensive
operation (no Gemma calls, no fine-tune scans, no full-text reindex)
without an explicit user click. Heavy actions belong on dedicated
buttons or other pages, not in the page-load path of Status.

## Enforcement

- These rules are auto-loaded; future edits in this directory should
  be sanity-checked against them.
- When adding a new workbench page, walk through rules 1-7
  explicitly. If a rule does not apply (e.g., a pure read-only page
  with no mutations), state why in a one-line comment near the top
  of the page.
- When introducing a new sample artifact, add it to
  `scripts/build_static_samples.py` first, regenerate, and link
  from the page that consumes it.
