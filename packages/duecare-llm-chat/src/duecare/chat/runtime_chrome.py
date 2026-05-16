from __future__ import annotations


def runtime_model_topbar_html(
    *,
    title: str,
    model_text: str = "Model: not loaded",
    note: str = "Gemma 4 required for real exports",
    custom_href: str = "/custom",
    shutdown_function: str = "shutdownA00",
) -> str:
    """Shared notebook runtime banner.

    The notebooks can style this with their page CSS, but the DOM contract is
    shared: model text, model note, KPI slot, custom-controls link, and shutdown
    button keep the same ids/classes across 01-derived pages, 02, and A-00.
    """
    return f"""
<div id="_dc-runtime-topbar" role="banner" aria-label="{title} runtime controls">
  <div class="runtime-brand">{title}</div>
  <div class="runtime-model">
    <b id="runtime-model-name">{model_text}</b>
    <span id="runtime-model-note">{note}</span>
  </div>
  <div class="runtime-actions">
    <div class="runtime-metrics" id="kpis" aria-label="Runtime status"></div>
    <button class="runtime-button" type="button" onclick="openModelSelector()">Model</button>
    <button class="runtime-button" type="button" onclick="location.href='{custom_href}'">Custom controls</button>
    <button class="runtime-button" id="_dc-shutdown-btn" type="button" onclick="{shutdown_function}()">Shutdown</button>
  </div>
</div>
<div class="runtime-model-overlay" id="runtime-model-overlay" hidden></div>
<div class="runtime-model-modal" id="runtime-model-modal" role="dialog" aria-modal="true" aria-label="Model selector" hidden>
  <div class="runtime-model-modal-head">
    <div>
      <b>Load Gemma 4 model</b>
      <p id="runtime-model-selector-status">Select a model variant. Loaded models are shared by this notebook runtime.</p>
    </div>
    <button class="runtime-button" type="button" onclick="closeModelSelector()">Close</button>
  </div>
  <div class="runtime-model-modal-controls">
    <select id="runtime-model-select" aria-label="Gemma 4 model variant"></select>
    <button class="runtime-button" type="button" onclick="loadSelectedRuntimeModel()">Load selected</button>
  </div>
  <pre id="runtime-model-loader-log">No loader events yet.</pre>
</div>
""".strip()
