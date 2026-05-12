"""One-shot patcher: upgrade kaggle/03-duecare-video-pitch/kernel.py with:
  - In-app tabbed nav (Slides / Presentation / Setup) instead of ?mode=
  - Floating presenter remote (NEXT / PREV) for live recording
  - Real in-browser setup editor (edit/save/load DEMO_SCRIPT without
    restarting the kernel)
  - New FastAPI routes /api/get-script /api/save-script /api/load-script

Query-string navigation (?mode=slides etc) looks amateur on a live
screen recording. The setup mode as shipped was inspect-and-copy,
not a real authoring surface. This patcher fixes both by replacing
the INDEX_HTML_TPL constant in place and injecting the new routes
inside the build_minimal_shell try block.
"""
from __future__ import annotations

from pathlib import Path
import sys

KERNEL = Path("kaggle/03-duecare-video-pitch/kernel.py")
text = KERNEL.read_text(encoding="utf-8")


# ---- New INDEX_HTML_TPL with in-app tabs + presenter remote + setup
# editor.

NEW_INDEX = r'''INDEX_HTML_TPL = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare 03 . Video Pitch</title>
<link rel="stylesheet" href="/static/_chrome.css">
<style>
  :root{
    --paper:#F7F6F1; --paper-2:#EFEDE4; --ink:#0E1116; --ink-2:#2A2D34;
    --ink-3:#5B5F68; --line:#DDD8C9; --good:#3E8C65; --warn:#A97935;
    --danger:#9E3F3F;
  }
  body{background:var(--paper);color:var(--ink);
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",
                    system-ui,sans-serif;
       margin:0;padding:0;line-height:1.55}
  .topbar{position:sticky;top:0;z-index:50;background:var(--paper);
          border-bottom:1px solid var(--line);
          display:flex;align-items:center;gap:14px;padding:12px 28px}
  .topbar .brand{font-weight:700;font-size:15px;letter-spacing:-0.01em}
  .topbar .tabs{display:flex;gap:6px;margin-left:24px}
  .topbar .tab{padding:7px 14px;background:transparent;
               border:1px solid var(--line);border-radius:999px;
               font-size:13px;cursor:pointer;color:var(--ink);
               font-weight:600}
  .topbar .tab:hover{background:var(--paper-2)}
  .topbar .tab.active{background:var(--ink);color:var(--paper);
                       border-color:var(--ink)}
  .topbar .lane-pick{margin-left:auto;display:none;gap:6px}
  .topbar .lane-pick.show{display:flex}
  .topbar .lane{padding:5px 11px;background:transparent;
                border:1px solid var(--line);border-radius:999px;
                font-size:12.5px;cursor:pointer;color:var(--ink-3);
                font-weight:600}
  .topbar .lane.active{background:var(--paper-2);color:var(--ink);
                        border-color:var(--ink-3)}
  .page{max-width:980px;margin:0 auto;padding:24px 28px 120px}

  #slides-view{display:none}
  .slide-card{background:#FFF;border:1px solid var(--line);
              border-radius:14px;padding:56px 64px;min-height:480px;
              margin-top:8px}
  .slide-sub{font-size:11px;text-transform:uppercase;
              letter-spacing:.12em;color:var(--ink-3);
              margin-bottom:14px;
              font-family:"JetBrains Mono",ui-monospace,monospace}
  .slide-title{font-size:38px;line-height:1.12;margin:0 0 28px;
                letter-spacing:-.02em;font-weight:700}
  .slide-body{font-size:19px;line-height:1.65;color:var(--ink-2);
               white-space:pre-wrap}
  .slide-meta{margin-top:28px;font-size:12px;color:var(--ink-3);
               font-family:"JetBrains Mono",ui-monospace,monospace}

  #presentation-view{display:none}
  .scene-bar{display:flex;gap:8px;margin:14px 0;flex-wrap:wrap}
  .scene-bar .pill{padding:5px 11px;background:var(--paper-2);
                    border:1px solid var(--line);border-radius:999px;
                    font-size:12px;font-weight:600;cursor:pointer;
                    color:var(--ink-3)}
  .scene-bar .pill.active{background:var(--ink);color:var(--paper);
                            border-color:var(--ink)}
  .chat{display:flex;flex-direction:column;gap:14px;background:#FFF;
        border:1px solid var(--line);border-radius:14px;
        padding:22px 24px;min-height:440px}
  .msg{padding:14px 18px;border-radius:12px;line-height:1.6}
  .msg.user{background:#F0EBE0;border:1px solid var(--line);
             align-self:flex-end;max-width:78%;font-size:15px}
  .msg.assistant{background:#FFF;border:1px solid var(--paper-2);
                  align-self:flex-start;max-width:96%;font-size:15px;
                  white-space:pre-wrap}
  .thinking{align-self:flex-start;background:var(--paper-2);
             border:1px solid var(--line);padding:10px 16px;
             border-radius:12px;font-size:13px;color:var(--ink-3);
             font-family:"JetBrains Mono",ui-monospace,monospace}
  .citations{margin-top:8px;font-size:12px;color:var(--ink-3)}
  .cite{display:inline-block;padding:2px 8px;border-radius:999px;
         background:#EAF2EC;color:#1F4F33;font-size:11px;
         margin:1px 4px 1px 0;font-weight:600}
  .trace{margin-top:8px;font-family:"JetBrains Mono",ui-monospace,monospace;
          font-size:11px;color:#8A8E97}

  #setup-view{display:none}
  .setup-grid{display:grid;grid-template-columns:280px 1fr;
              gap:20px;margin-top:14px}
  .setup-list{background:var(--paper-2);border:1px solid var(--line);
              border-radius:12px;padding:14px 16px;max-height:580px;
              overflow:auto}
  .setup-list h3{margin:0 0 8px;font-size:13px;
                   text-transform:uppercase;letter-spacing:.06em;
                   color:var(--ink-3)}
  .setup-list select{width:100%;padding:8px 10px;
                       border:1px solid var(--line);border-radius:6px;
                       background:#FFF;font:inherit;margin-bottom:10px}
  .setup-list .scene-row{padding:8px 10px;background:#FFF;
                          border:1px solid var(--line);
                          border-radius:8px;margin-bottom:6px;
                          cursor:pointer;font-size:13px}
  .setup-list .scene-row.active{border-color:var(--ink);
                                  background:var(--paper)}
  .setup-list .scene-row .pid{font-family:"JetBrains Mono",monospace;
                                color:var(--ink-3);font-size:11px}
  .setup-list .actions{margin-top:12px;display:flex;flex-direction:column;
                         gap:6px}
  .setup-list .actions button{padding:7px 12px;
        border:1px solid var(--line);border-radius:6px;
        background:#FFF;cursor:pointer;font-size:12.5px;color:var(--ink)}
  .setup-list .actions button:hover{background:var(--paper)}
  .setup-editor{background:#FFF;border:1px solid var(--line);
                 border-radius:12px;padding:18px 20px}
  .setup-editor label{display:block;font-size:11px;
                        text-transform:uppercase;letter-spacing:.06em;
                        color:var(--ink-3);margin:12px 0 4px}
  .setup-editor input[type=text],
  .setup-editor input[type=number],
  .setup-editor textarea{width:100%;padding:10px 12px;
                            border:1px solid var(--line);
                            border-radius:8px;background:var(--paper);
                            font:inherit;font-size:13.5px}
  .setup-editor textarea{min-height:140px;
                            font-family:"JetBrains Mono",monospace;
                            font-size:12.5px;line-height:1.5}
  .setup-editor .edit-actions{margin-top:14px;display:flex;gap:8px}
  .setup-editor .edit-actions button{padding:8px 14px;
        border:none;border-radius:999px;font-weight:600;
        font-size:12.5px;cursor:pointer}
  .setup-editor .btn-primary{background:var(--ink);color:var(--paper)}
  .setup-editor .btn-ghost{background:transparent;color:var(--ink);
                             border:1px solid var(--line)!important}
  .setup-status{margin-top:10px;font-size:12px;color:var(--ink-3);
                 font-family:"JetBrains Mono",monospace}

  .remote{position:fixed;bottom:18px;right:20px;z-index:60;
          background:var(--ink);color:var(--paper);
          border-radius:14px;padding:10px 14px;
          box-shadow:0 8px 24px rgba(0,0,0,.18);
          display:none;align-items:center;gap:10px;
          font-family:"JetBrains Mono",monospace;font-size:12px}
  .remote.show{display:flex}
  .remote button{background:transparent;color:var(--paper);
                  border:1px solid rgba(255,255,255,.3);
                  border-radius:999px;padding:6px 14px;cursor:pointer;
                  font-size:13px;font-weight:600}
  .remote button:hover{background:rgba(255,255,255,.12)}
  .remote .pos{opacity:.65}
</style></head><body>

<div class="topbar">
  <div class="brand">DueCare . 03 Video Pitch</div>
  <div class="tabs">
    <button class="tab" data-mode="slides">Slides</button>
    <button class="tab active" data-mode="presentation">Presentation</button>
    <button class="tab" data-mode="setup">Setup</button>
  </div>
  <div class="lane-pick" id="lane-pick"></div>
</div>

<div class="page">
  <div id="slides-view"><div id="slides-root"></div></div>

  <div id="presentation-view">
    <h2 id="lane-label" style="margin:8px 0 4px;font-size:22px"></h2>
    <p id="lane-intro" style="color:var(--ink-3);margin:0 0 12px;
                                font-size:14px"></p>
    <div class="scene-bar" id="scene-bar"></div>
    <div class="chat" id="chat"></div>
  </div>

  <div id="setup-view">
    <p style="color:var(--ink-3);max-width:740px;margin:8px 0 0;
                font-size:14px">
      Edit prompts and responses in-browser. Save writes
      <code>/kaggle/working/demo_script_authored.json</code>; Load
      reads a previously saved JSON. Changes apply immediately to
      the Presentation tab without restarting the kernel.</p>
    <div class="setup-grid">
      <div class="setup-list">
        <h3>Lane</h3>
        <select id="setup-lane"></select>
        <h3>Scenes</h3>
        <div id="setup-scene-list"></div>
        <div class="actions">
          <button onclick="setupAddScene()">+ Add scene</button>
          <button onclick="setupDuplicate()">Duplicate selected</button>
          <button onclick="setupDelete()" style="color:#9E3F3F">
            Delete selected</button>
          <button onclick="setupSave()"
                  style="background:var(--ink);color:var(--paper)">
            Save to /kaggle/working</button>
          <label style="margin-top:8px;font-size:11px;
                          color:var(--ink-3);text-transform:uppercase;
                          letter-spacing:.06em">Load JSON</label>
          <input type="file" id="setup-load" accept=".json"
                  onchange="setupLoad(this.files[0])">
        </div>
        <div class="setup-status" id="setup-status"></div>
      </div>
      <div class="setup-editor" id="setup-editor">
        <p style="color:var(--ink-3);font-size:13px">
          Select a scene on the left to edit.</p>
      </div>
    </div>
  </div>
</div>

<div class="remote" id="remote">
  <span class="pos" id="remote-pos">.</span>
  <button onclick="remotePrev()">&lt; Prev</button>
  <button onclick="remoteNext()">Next &gt;</button>
</div>

<script>
const SCRIPT_INIT = __SCRIPT_JSON__;
const SLIDES_DATA = __SLIDES_JSON__;
let SCRIPT = JSON.parse(JSON.stringify(SCRIPT_INIT));

let currentMode = "presentation";
let currentLane = "worker";
let currentScene = 0;
let currentSlide = 0;
let setupSelected = 0;
let abortToken = 0;

function _el(tag, cls, txt){
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (txt != null) e.textContent = String(txt);
  return e;
}

function setMode(m){
  if (!["slides","presentation","setup"].includes(m)) return;
  abortToken++;
  currentMode = m;
  document.querySelectorAll(".topbar .tab").forEach(t=>{
    t.classList.toggle("active", t.dataset.mode === m);
  });
  document.getElementById("slides-view").style.display =
    (m==="slides") ? "block" : "none";
  document.getElementById("presentation-view").style.display =
    (m==="presentation") ? "block" : "none";
  document.getElementById("setup-view").style.display =
    (m==="setup") ? "block" : "none";
  document.getElementById("lane-pick").classList.toggle(
    "show", m==="presentation");
  const remote = document.getElementById("remote");
  remote.classList.toggle("show", m==="slides" || m==="presentation");
  if (m==="slides") showSlide(currentSlide);
  else if (m==="presentation"){
    renderLaneBar(); renderLaneHead(); playScene();
  } else if (m==="setup") renderSetup();
}

document.querySelectorAll(".topbar .tab").forEach(t=>{
  t.onclick = ()=> setMode(t.dataset.mode);
});

function showSlide(i){
  const root = document.getElementById("slides-root");
  root.replaceChildren();
  const s = SLIDES_DATA.slides[i];
  if (!s) return;
  const card = _el("div","slide-card");
  card.appendChild(_el("div","slide-sub", s.subtitle));
  card.appendChild(_el("h1","slide-title", s.title));
  const body = _el("div","slide-body");
  body.textContent = s.body;
  card.appendChild(body);
  card.appendChild(_el("div","slide-meta",
    "Slide " + (i+1) + " / " + SLIDES_DATA.slides.length +
    " . id: " + s.id));
  root.appendChild(card);
  updateRemote();
}

function renderLaneBar(){
  const wrap = document.getElementById("lane-pick");
  wrap.replaceChildren();
  for (const k of Object.keys(SCRIPT.lanes)){
    const b = document.createElement("button");
    b.className = "lane" + (k===currentLane ? " active" : "");
    b.textContent = SCRIPT.lanes[k].label.split("--")[0].trim();
    b.onclick = ()=>{
      currentLane = k; currentScene = 0;
      renderLaneBar(); renderLaneHead(); playScene();
    };
    wrap.appendChild(b);
  }
}

function renderLaneHead(){
  const lane = SCRIPT.lanes[currentLane];
  document.getElementById("lane-label").textContent = lane.label;
  document.getElementById("lane-intro").textContent = lane.intro;
  renderSceneBar();
}

function renderSceneBar(){
  const bar = document.getElementById("scene-bar");
  bar.replaceChildren();
  const scenes = SCRIPT.lanes[currentLane].scenes;
  for (let i=0; i<scenes.length; i++){
    const p = _el("span", "pill" + (i===currentScene ? " active" : ""),
                   (i+1) + ". " + scenes[i].scene_id);
    p.onclick = ()=>{ currentScene = i; playScene(); };
    bar.appendChild(p);
  }
}

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

async function typewrite(el, text, cps){
  const myToken = ++abortToken;
  const delay = Math.max(8, Math.round(1000/cps));
  for (let i=0; i<text.length; i++){
    if (myToken !== abortToken) return;
    el.textContent = text.slice(0, i+1);
    await sleep(delay);
  }
}

async function playScene(){
  abortToken++;
  const chat = document.getElementById("chat");
  chat.replaceChildren();
  renderSceneBar();
  const s = SCRIPT.lanes[currentLane].scenes[currentScene];
  if (!s) return;
  updateRemote();
  const user = _el("div","msg user");
  chat.appendChild(user);
  await typewrite(user, s.prompt, 28);
  const t = _el("div","thinking","thinking ...");
  chat.appendChild(t);
  await sleep(s.latency_simulation_ms || 1500);
  if (t.parentNode) chat.removeChild(t);
  const a = _el("div","msg assistant");
  chat.appendChild(a);
  await typewrite(a, s.response, 65);
  if ((s.citations||[]).length){
    const c = _el("div","citations");
    for (const ct of s.citations) c.appendChild(_el("span","cite",ct));
    chat.appendChild(c);
  }
  const tr = s.harness_trace || {};
  const grepN = (tr.grep && tr.grep.rules_fired ?
                  tr.grep.rules_fired.length : 0);
  const ragN  = (tr.rag  && tr.rag.docs_retrieved ?
                  tr.rag.docs_retrieved.length  : 0);
  const tooN  = (tr.tools && tr.tools.tools_called ?
                  tr.tools.tools_called.length  : 0);
  const trParts = [];
  if (tr.persona && tr.persona.enabled) trParts.push("persona");
  if (grepN) trParts.push("grep:" + grepN + " rules");
  if (ragN)  trParts.push("rag:"  + ragN  + " docs");
  if (tooN)  trParts.push("tools:" + tooN);
  if (trParts.length){
    chat.appendChild(_el("div","trace",
      "harness trace: " + trParts.join(" . ")));
  }
}

function skip(){
  abortToken++;
  const chat = document.getElementById("chat");
  chat.replaceChildren();
  const s = SCRIPT.lanes[currentLane].scenes[currentScene];
  if (!s) return;
  const u = _el("div","msg user"); u.textContent = s.prompt;
  chat.appendChild(u);
  const a = _el("div","msg assistant"); a.textContent = s.response;
  chat.appendChild(a);
  if ((s.citations||[]).length){
    const c = _el("div","citations");
    for (const ct of s.citations) c.appendChild(_el("span","cite",ct));
    chat.appendChild(c);
  }
}

function updateRemote(){
  const pos = document.getElementById("remote-pos");
  if (currentMode === "slides"){
    pos.textContent = "Slide " + (currentSlide+1) + " / " +
                       SLIDES_DATA.slides.length;
  } else if (currentMode === "presentation"){
    const ns = SCRIPT.lanes[currentLane].scenes.length;
    pos.textContent = currentLane + " . Scene " +
                       (currentScene+1) + " / " + ns;
  }
}

function remoteNext(){
  if (currentMode === "slides"){
    if (currentSlide < SLIDES_DATA.slides.length - 1){
      currentSlide++; showSlide(currentSlide);
    }
  } else if (currentMode === "presentation"){
    const ns = SCRIPT.lanes[currentLane].scenes.length;
    if (currentScene < ns - 1){ currentScene++; playScene(); }
  }
}

function remotePrev(){
  if (currentMode === "slides"){
    if (currentSlide > 0){ currentSlide--; showSlide(currentSlide); }
  } else if (currentMode === "presentation"){
    if (currentScene > 0){ currentScene--; playScene(); }
  }
}

document.addEventListener("keydown", (e)=>{
  if (e.key === " " || e.key === "ArrowRight"){
    e.preventDefault(); remoteNext();
  } else if (e.key === "ArrowLeft"){
    e.preventDefault(); remotePrev();
  } else if (e.key === "r" || e.key === "R"){
    if (currentMode === "slides"){ currentSlide=0; showSlide(0); }
    else if (currentMode === "presentation"){
      currentScene=0; playScene();
    }
  } else if (e.key === "s" || e.key === "S"){
    if (currentMode === "presentation") skip();
  } else if (e.key >= "1" && e.key <= "9"){
    const n = parseInt(e.key, 10) - 1;
    if (currentMode === "slides" && n < SLIDES_DATA.slides.length){
      currentSlide = n; showSlide(n);
    } else if (currentMode === "presentation"){
      const ns = SCRIPT.lanes[currentLane].scenes.length;
      if (n < ns){ currentScene = n; playScene(); }
    }
  }
});

function renderSetup(){
  const laneSel = document.getElementById("setup-lane");
  laneSel.replaceChildren();
  for (const k of Object.keys(SCRIPT.lanes)){
    const o = document.createElement("option");
    o.value = k; o.textContent = SCRIPT.lanes[k].label;
    laneSel.appendChild(o);
  }
  laneSel.value = currentLane;
  laneSel.onchange = ()=>{
    currentLane = laneSel.value;
    setupSelected = 0;
    renderSetupSceneList();
    renderSetupEditor();
  };
  renderSetupSceneList();
  renderSetupEditor();
}

function renderSetupSceneList(){
  const wrap = document.getElementById("setup-scene-list");
  wrap.replaceChildren();
  const scenes = SCRIPT.lanes[currentLane].scenes;
  for (let i=0; i<scenes.length; i++){
    const row = _el("div",
      "scene-row" + (i===setupSelected ? " active" : ""));
    row.appendChild(_el("div", "pid", "[" + (i+1) + "] " +
                          scenes[i].scene_id));
    const preview = scenes[i].prompt.slice(0, 60) +
                      (scenes[i].prompt.length > 60 ? "..." : "");
    row.appendChild(_el("div", null, preview));
    row.onclick = ()=>{
      setupSelected = i;
      renderSetupSceneList();
      renderSetupEditor();
    };
    wrap.appendChild(row);
  }
}

function renderSetupEditor(){
  const wrap = document.getElementById("setup-editor");
  wrap.replaceChildren();
  const scenes = SCRIPT.lanes[currentLane].scenes;
  const s = scenes[setupSelected];
  if (!s){
    wrap.appendChild(_el("p", null,
      "No scene selected. Use + Add scene on the left."));
    return;
  }
  function field(label, key, isArea){
    wrap.appendChild(_el("label", null, label));
    const inp = document.createElement(isArea ? "textarea" : "input");
    if (!isArea) inp.type = "text";
    inp.value = s[key] != null ? s[key] : "";
    inp.oninput = ()=>{ s[key] = inp.value; };
    wrap.appendChild(inp);
    return inp;
  }
  field("Scene ID", "scene_id", false);
  field("Prompt (user message)", "prompt", true);
  field("Response (assistant message)", "response", true);
  wrap.appendChild(_el("label", null, "Latency simulation (ms)"));
  const lat = document.createElement("input");
  lat.type = "number";
  lat.value = s.latency_simulation_ms != null ?
    s.latency_simulation_ms : 1500;
  lat.oninput = ()=>{
    s.latency_simulation_ms = parseInt(lat.value, 10) || 1500;
  };
  wrap.appendChild(lat);
  wrap.appendChild(_el("label", null,
    "Citations (comma-separated)"));
  const cit = document.createElement("input");
  cit.type = "text";
  cit.value = (s.citations || []).join(", ");
  cit.oninput = ()=>{
    s.citations = cit.value.split(",").map(x=>x.trim())
                              .filter(Boolean);
  };
  wrap.appendChild(cit);
  const acts = _el("div", "edit-actions");
  const tb = document.createElement("button");
  tb.className = "btn-primary";
  tb.textContent = "Preview in Presentation tab";
  tb.onclick = ()=>{
    currentScene = setupSelected;
    setMode("presentation");
  };
  acts.appendChild(tb);
  const gb = document.createElement("button");
  gb.className = "btn-ghost";
  gb.textContent = "Discard changes (reload from server)";
  gb.onclick = ()=>{ setupReloadFromServer(); };
  acts.appendChild(gb);
  wrap.appendChild(acts);
}

function setupAddScene(){
  const scenes = SCRIPT.lanes[currentLane].scenes;
  const idx = scenes.length;
  scenes.push({
    scene_id: "new_scene_" + (idx+1).toString().padStart(2, "0"),
    prompt: "Type your prompt here ...",
    response: "Type the response Gemma should give back ...",
    harness_trace: {},
    citations: [],
    latency_simulation_ms: 1500,
  });
  setupSelected = idx;
  renderSetupSceneList();
  renderSetupEditor();
}

function setupDuplicate(){
  const scenes = SCRIPT.lanes[currentLane].scenes;
  const s = scenes[setupSelected];
  if (!s) return;
  const copy = JSON.parse(JSON.stringify(s));
  copy.scene_id = (s.scene_id || "scene") + "_copy";
  scenes.splice(setupSelected + 1, 0, copy);
  setupSelected = setupSelected + 1;
  renderSetupSceneList();
  renderSetupEditor();
}

function setupDelete(){
  const scenes = SCRIPT.lanes[currentLane].scenes;
  if (scenes.length <= 1){
    setupStatus("Cannot delete the last scene in a lane.", true);
    return;
  }
  scenes.splice(setupSelected, 1);
  setupSelected = Math.max(0, setupSelected - 1);
  renderSetupSceneList();
  renderSetupEditor();
}

function setupStatus(msg, isErr){
  const el = document.getElementById("setup-status");
  el.textContent = msg;
  el.style.color = isErr ? "#9E3F3F" : "var(--ink-3)";
}

async function setupSave(){
  setupStatus("saving ...");
  try {
    const r = await fetch("/api/save-script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({script: SCRIPT}),
    }).then(r=>r.json());
    if (r.ok){
      setupStatus("saved to " + r.path + " (" + r.size_bytes + " B)");
    } else {
      setupStatus("save failed: " + (r.error || "unknown"), true);
    }
  } catch (e){ setupStatus("save error: " + e, true); }
}

async function setupLoad(file){
  if (!file) return;
  setupStatus("loading " + file.name + " ...");
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    if (!parsed.lanes){
      setupStatus("JSON missing 'lanes' key", true);
      return;
    }
    const r = await fetch("/api/load-script", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({script: parsed}),
    }).then(r=>r.json());
    if (r.ok){
      SCRIPT = parsed;
      currentLane = Object.keys(SCRIPT.lanes)[0];
      setupSelected = 0;
      renderSetup();
      setupStatus("loaded " + file.name);
    } else {
      setupStatus("load failed: " + (r.error || "unknown"), true);
    }
  } catch (e){ setupStatus("load error: " + e, true); }
}

async function setupReloadFromServer(){
  try {
    const r = await fetch("/api/get-script").then(r=>r.json());
    if (r.ok && r.script){
      SCRIPT = r.script;
      renderSetup();
      setupStatus("reloaded from server");
    }
  } catch (e){ setupStatus("reload error: " + e, true); }
}

setMode("presentation");
</script>
</body></html>
"""
'''


# ---- Replace the existing INDEX_HTML_TPL block

start_marker = 'INDEX_HTML_TPL = r"""<!doctype html>'
end_marker_block = '</body></html>\n"""\n'

start = text.find(start_marker)
if start < 0:
    sys.exit("could not find INDEX_HTML_TPL start anchor")
end_search_start = start + len(start_marker)
end = text.find(end_marker_block, end_search_start)
if end < 0:
    sys.exit("could not find INDEX_HTML_TPL end anchor")
end += len(end_marker_block)
old_block = text[start:end]
text = text[:start] + NEW_INDEX + text[end:]
print(f"  + INDEX_HTML_TPL replaced "
      f"({len(old_block)} -> {len(NEW_INDEX)} bytes)")


# ---- Inject /api/get-script, /api/save-script, /api/load-script

ROUTES_INSERT = r'''
    # Setup-mode endpoints: get / save / load the in-memory DEMO_SCRIPT
    # so the operator can author scenes through the browser without
    # restarting the kernel. Authored scripts persist as
    # /kaggle/working/demo_script_authored.json.
    _SCRIPT_RUNTIME = {"script": DEMO_SCRIPT}
    _AUTHORED_PATH = OUTPUT_DIR / "demo_script_authored.json"

    from fastapi import Request as _Request

    @app.get("/api/get-script")
    def _get_script():
        return {"ok": True, "script": _SCRIPT_RUNTIME["script"]}

    @app.post("/api/save-script")
    async def _save_script(req: _Request):
        body = await req.json()
        script = body.get("script")
        if not isinstance(script, dict) or "lanes" not in script:
            return {"ok": False, "error":
                    "expected {script: {lanes: ...}}"}
        _SCRIPT_RUNTIME["script"] = script
        try:
            _AUTHORED_PATH.write_text(
                json.dumps(script, indent=2, ensure_ascii=False),
                encoding="utf-8")
            size = _AUTHORED_PATH.stat().st_size
        except Exception as _e:
            return {"ok": False,
                    "error": f"write failed: {type(_e).__name__}: "
                              f"{str(_e)[:200]}"}
        return {"ok": True, "path": str(_AUTHORED_PATH),
                "size_bytes": size}

    @app.post("/api/load-script")
    async def _load_script(req: _Request):
        body = await req.json()
        script = body.get("script")
        if not isinstance(script, dict) or "lanes" not in script:
            return {"ok": False, "error":
                    "expected {script: {lanes: ...}}"}
        _SCRIPT_RUNTIME["script"] = script
        try:
            _AUTHORED_PATH.write_text(
                json.dumps(script, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            pass
        return {"ok": True}
'''

anchor = "app, public_url = build_minimal_shell("
idx = text.find(anchor)
if idx < 0:
    sys.exit("could not find build_minimal_shell anchor")
close = text.find(")\n", idx)
if close < 0:
    sys.exit("could not find build_minimal_shell close")
inject_at = close + 2
if '@app.get("/api/get-script")' in text:
    print("  - routes already present; skipping inject")
else:
    text = text[:inject_at] + ROUTES_INSERT + text[inject_at:]
    print(f"  + injected setup-mode routes "
          f"({len(ROUTES_INSERT)} bytes)")


# ---- Add OUTPUT_DIR fallback definition so the routes work
if "OUTPUT_DIR = Path(" not in text:
    # Inject a one-line OUTPUT_DIR definition right after the PHASE 1
    # DueCare-from-GitHub install (after the first OUTPUT_DIR usage
    # we expect, near the top-level config).
    output_dir_anchor = 'DUECARE_PACKAGES = ["duecare-llm-chat"]'
    idx2 = text.find(output_dir_anchor)
    if idx2 >= 0:
        end_of_line = text.find("\n", idx2)
        if end_of_line >= 0:
            insertion = ('\n\nOUTPUT_DIR = Path("/kaggle/working")\n'
                          'OUTPUT_DIR.mkdir(parents=True, exist_ok=True)\n')
            if "OUTPUT_DIR = Path(" not in text:
                text = (text[:end_of_line + 1] + insertion
                        + text[end_of_line + 1:])
                print(f"  + injected OUTPUT_DIR config "
                      f"({len(insertion)} bytes)")
    else:
        print("  ! WARN: could not find DUECARE_PACKAGES anchor; "
               "setup-mode save will fail until OUTPUT_DIR is added.")


KERNEL.write_text(text, encoding="utf-8")
print(f"  + wrote {KERNEL} ({len(text)} bytes)")
