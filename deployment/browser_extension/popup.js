// Popup controller. Sends the textarea to the configured DueCare endpoint
// and renders the grade/indicators/resources.

const DEFAULT_ENDPOINT = "http://localhost:8080";

async function loadConfig() {
  const { endpoint = DEFAULT_ENDPOINT } = await chrome.storage.sync.get(["endpoint"]);
  return { endpoint };
}

async function analyze() {
  const text = document.getElementById("text").value.trim();
  const jurisdiction = document.getElementById("jurisdiction").value;
  const language = document.getElementById("language").value;
  if (!text) return;

  const result = document.getElementById("result");
  result.textContent = "Analyzing...";
  result.classList.add("visible");

  const { endpoint } = await loadConfig();
  try {
    const resp = await fetch(`${endpoint}/api/v1/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, jurisdiction, language, context: "other" }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    render(await resp.json());
  } catch (err) {
    result.innerHTML =
      `<div style="color: var(--danger); font-size: 12px;">` +
      `Could not reach ${endpoint}.<br>` +
      `Start the DueCare demo server: <code>uvicorn src.demo.app:app --port 8080</code>` +
      `</div>`;
  }
}

function render(data) {
  const grade = data.grade || "neutral";
  const action = (data.action || "review").toUpperCase();
  const score = Math.round((data.score || 0) * 100);
  let html = `<div>`;
  html += `<span class="badge grade-${grade}">${grade.toUpperCase()}</span>`;
  html += `<span style="margin-left: 8px; font-weight: 600;">${action} &middot; ${score}%</span>`;
  html += `</div>`;

  if (data.warning_text) {
    html += `<div style="margin-top: 8px; font-size: 12px; line-height: 1.5;">${esc(data.warning_text)}</div>`;
  }

  if (data.indicators && data.indicators.length) {
    html += `<div style="margin-top: 8px;">`;
    for (const i of data.indicators) {
      html += `<span class="indicator">${esc(i.replaceAll("_", " "))}</span>`;
    }
    html += `</div>`;
  }

  if (data.resources && data.resources.length) {
    html += `<div class="resources"><strong>Help:</strong><br>`;
    for (const r of data.resources.slice(0, 4)) {
      html += `<div>`;
      html += `<strong>${esc(r.name)}</strong>`;
      if (r.number) html += ` &middot; <span style="color: var(--primary);">${esc(r.number)}</span>`;
      if (r.url) html += ` &middot; <a href="${esc(r.url)}" target="_blank">website</a>`;
      html += `</div>`;
    }
    html += `</div>`;
  }

  document.getElementById("result").innerHTML = html;
}

function esc(s) {
  return String(s || "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

document.getElementById("analyze").addEventListener("click", analyze);
document.getElementById("options").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});
