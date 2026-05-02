# Notebook QA companion — what to test, per notebook

> **Purpose.** A practical checklist for the per-notebook testing
> pass before submission. Read alongside whichever notebook you're
> running. Each entry: **what to verify**, **what success looks
> like**, **common confusion points**, **what to fix if broken**.
>
> **Time budget per notebook.** ~10-15 min for a smoke pass; ~30-45
> min for a thorough one. 11 notebooks × 30 min = 5-6 hours total.
> Spread across 2-3 sessions.

## Universal pre-flight (run for every notebook)

Before opening any notebook, do this once:

- [ ] Kaggle notebook → Settings → Accelerator: **GPU T4 ×2** (for
      notebooks that need GPU; the chat playgrounds + classifier +
      research-graphs run on CPU)
- [ ] Settings → Persistence: **Files only** (don't persist variables
      — judges should be able to restart fresh)
- [ ] Settings → Internet: **On** (for pip install of wheels dataset)
- [ ] Notebook **outputs cleared** before saving (judges shouldn't
      see your old run artifacts mixed with theirs)
- [ ] **Cell run order top-to-bottom verified** by clicking "Run
      All" once with a fresh kernel — fail-fast on any cell that
      depends on out-of-order state
- [ ] **Total runtime < 9 hours** (Kaggle's hard cap on GPU notebooks)
- [ ] **Output size < 20 GB** (Kaggle's hard cap on saved-output)

## Per-notebook checklists

### 1. `chat-playground` (raw Gemma 4 baseline)

**Purpose**: judges see the baseline without any harness. Must
demonstrably under-perform without us cherry-picking.

**Test checklist:**
- [ ] First cell installs `duecare-llm-chat` from the wheels dataset
- [ ] Loads Gemma 4 E2B (or E4B if GPU memory allows) successfully
- [ ] Chat surface renders without JS errors (check browser console)
- [ ] Type "Is a 50,000 PHP training fee legal for a Filipino domestic worker going to Hong Kong?" — get a response that does NOT cite POEA MC 14-2017
- [ ] Type a generic chat ("Tell me about Hong Kong domestic work") — get a generic, unsourced response
- [ ] Confirm there's NO Pipeline modal (this is the no-harness notebook)

**Success looks like:** worker would receive incomplete / un-cited
advice; the gap to notebook #2 is visible.

**Common confusion:** judges may not realize this is the deliberate
baseline. Add a banner cell explicitly: *"This notebook shows raw
Gemma 4. The harness lift starts in notebook #2."*

**If broken:** rebuild via `python scripts/build_notebook_NNN.py`;
re-push.

---

### 2. `chat-playground-with-grep-rag-tools` ⭐ HEADLINE

**Purpose**: judges see the harness in action; this is THE demo
notebook for the video. Must be polished.

**Test checklist:**
- [ ] Same install + load sequence as #1
- [ ] Chat surface renders with the **4 toggle tiles visible**
      (Persona / GREP / RAG / Tools)
- [ ] All 4 toggles ON by default (judges should see the lift, not
      have to enable it)
- [ ] Type the same fee question as #1 — response now cites
      **POEA Memorandum Circular 14-2017** with section number
- [ ] **Pipeline modal opens** when clicking "View pipeline" on a
      response; shows: GREP hits, RAG docs retrieved, tool results,
      merged prompt, raw model output
- [ ] **Persona library** dropdown has multiple personas (worker,
      NGO frontline, regulator, etc.); switching changes the
      response register
- [ ] **Custom rule** add-form works (paste a rule, save, see it
      fire on next prompt)
- [ ] **Examples library** lists 394 prompts; clicking one populates
      the input
- [ ] Toggle GREP off + same prompt → fewer / no rule citations in
      the response (visible regression confirms toggles work)
- [ ] All toggles back on at end of run (judges' default state)

**Success looks like:** a judge can instantly see the before/after
comparison by toggling. The Pipeline modal proves the harness is
real, not a single LLM call dressed up.

**Common confusion:** judges may scroll past the toggle tiles. Make
sure they're visually prominent + labeled.

**If broken:** check that the wheels dataset includes
`duecare-llm-chat` (the harness logic). The chat surface UI lives
in there.

---

### 3. `content-classification-playground` (publish pending)

**Purpose**: hands-on classification sandbox. Pre-live-demo intro.

**Test checklist:**
- [ ] Wheels install succeeds
- [ ] **4 schema modes** visible (single-label / multi-label /
      risk-vector / custom JSON Schema)
- [ ] Pasting test content (use the bundled examples) returns
      **structured JSON** matching the chosen schema
- [ ] **Merged prompt visible** — the user can see what was sent
      to Gemma 4
- [ ] **Raw response visible** alongside the parsed JSON
- [ ] Custom JSON Schema mode accepts a user-provided schema and
      validates the response against it
- [ ] At least one **negative test** (paste benign content, get
      a "low risk" classification) to prove the harness doesn't
      auto-flag everything

**Success looks like:** a judge understands the classification
shape before they see it inside the bigger live-demo notebook.

**Common confusion:** the JSON output may look intimidating. Add
a one-line explanation per field.

**If broken:** schemas live in `duecare-llm-domains`; rebuild
that wheel + the notebook.

---

### 4. `content-knowledge-builder-playground` (publish pending)

**Purpose**: hands-on KB builder. Pre-live-demo intro to extending
the harness.

**Test checklist:**
- [ ] Wheels install succeeds
- [ ] Can **add a new GREP rule** via the form (regex + severity +
      ILO indicator + statute)
- [ ] Added rule **fires on a test prompt** demonstrating the
      detection
- [ ] Can **add a new RAG document** (paste source text + ID)
- [ ] Added doc **appears in retrieval** for a relevant query
- [ ] Can **add a new lookup-table entry** (e.g., a new corridor's
      fee cap)
- [ ] **Export** as a single JSON file; **re-import** restores all
      additions (proves the extension pack format works)

**Success looks like:** a judge understands they can extend the
harness without writing code. Critical for "this isn't a closed
black box" framing.

**Common confusion:** users may try to add rules without testing.
Make sure each "Add" button has an inline "Test against a sample
prompt" affordance.

**If broken:** the KB-builder UI logic lives in
`duecare-llm-chat`'s `kb_builder` submodule.

---

### 5. `gemma-content-classification-evaluation`

**Purpose**: polished NGO/agency dashboard with risk vectors +
threshold-filtered queue.

**Test checklist:**
- [ ] Wheels install succeeds
- [ ] **Form-based input** for content + content type + (optional)
      worker context
- [ ] **Submit** returns a structured JSON envelope:
      classification + overall risk + per-vector magnitudes (ILO
      indicators, fee violations, wage protection, debt bondage)
      + recommended action (`allow` / `log_only` / `review` /
      `escalate_to_ngo` / `escalate_to_regulator` /
      `urgent_safety_referral`)
- [ ] **History queue** persists across submissions in the session
- [ ] **Threshold slider** filters the queue by overall-risk score
- [ ] **16 example items** load with one click each (with at least
      6 having SVG document mockups for visual richness)
- [ ] **Export JSON** of the full queue works

**Success looks like:** a judge sees what an NGO triage workflow
looks like. The queue + threshold + escalation labels show the
operational shape.

**Common confusion:** the JSON envelope can look complex. Surface
the most important fields visually first; let JSON be a
"View raw" link.

**If broken:** classification logic in `duecare-llm-tasks`; UI
in this notebook's kernel.

---

### 6. `live-demo` ⭐ POLISHED PRODUCT

**Purpose**: the user-facing combined product. 22-slide deck +
full pipeline + audit Workbench. **THE notebook judges click for
"the deployed thing."**

**Test checklist:**
- [ ] Wheels install succeeds (this is the biggest install — give
      it 30 sec)
- [ ] **22-slide deck** renders (check each slide loads + has
      readable text + no broken images)
- [ ] **Full safety-harness pipeline** is callable end-to-end (chat
      + classify + research + pipeline + audit)
- [ ] **Audit Workbench** shows per-decision provenance
      (model + prompt hash + response hash + harness score + GREP
      hits + RAG docs + tool results)
- [ ] Notebook combines what notebooks #3 + #4 + #5 do — but in
      one polished surface
- [ ] **No broken cross-cell dependencies** — Run All from a fresh
      kernel must succeed in one pass
- [ ] **Total runtime < 9 hours** (this is the longest notebook;
      verify it actually completes within Kaggle's cap)

**Success looks like:** a judge spends 5 minutes here and
understands the full Duecare value proposition without opening
any other notebook.

**Common confusion:** 1,951 lines is a lot. The Table of Contents
at the top must be navigable.

**If broken:** this is the highest-stakes notebook to fix. Cell
that fails: rerun in isolation; iterate.

---

### A1. `prompt-generation` (publish pending)

**Purpose**: Gemma 4 generates new evaluation prompts + 5 graded
responses each. Output feeds A2.

**Test checklist:**
- [ ] Wheels install succeeds
- [ ] Loads Gemma 4 E4B successfully (or fall back to E2B)
- [ ] Generates a batch of N=10 prompts per category
- [ ] Each generated prompt has 5 graded response examples
      (worst → best)
- [ ] Output saved as JSONL in the smoke_25-compatible row shape
- [ ] At least one **manual sanity check** of a generated prompt
      (does it actually look like a real recruitment-fraud question?)

**Success looks like:** the output JSONL is valid input for A2.

**Common confusion:** judges may not realize this notebook's
output is consumed by A2 (not by them). Add a banner.

---

### A2. `bench-and-tune` (publish pending; T4×2 fine-tune run pending)

**Purpose**: stock benchmark → Unsloth SFT → DPO → re-benchmark →
GGUF Q8_0 export → HF Hub push. **The fine-tune story.**

**Test checklist (CPU-only smoke):**
- [ ] Wheels install succeeds
- [ ] Imports Unsloth without errors (CUDA-required imports
      tolerated as warnings if CPU-only test)
- [ ] Loads the smoke_25 dataset
- [ ] Loads stock Gemma 4 E2B and runs the benchmark on N=5
      prompts (CPU is enough for this scale)
- [ ] Smoke benchmark output matches the row shape A1 produces

**Test checklist (GPU run when quota resets):**
- [ ] Loads Gemma 4 E4B + Unsloth on T4 ×2
- [ ] SFT trains for the configured N steps without OOM
- [ ] DPO step trains successfully on chosen/rejected pairs
- [ ] **Re-benchmark numbers** show a delta vs stock (positive lift
      expected; even 5-10 pp is a real result)
- [ ] **GGUF Q8_0 export** writes to disk, file size as expected
      (~4-6 GB for E4B Q8)
- [ ] **HF Hub push** succeeds (requires HF_TOKEN with write scope)
- [ ] HF Hub model page renders the model card correctly
- [ ] RESULTS.md updated with the post-fine-tune numbers

**Success looks like:** weights at
`taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0` on
HF Hub + benchmark delta documented.

**Common confusion:** Unsloth + transformers + flash-attn version
pinning is fragile. The bundled wheels dataset has the exact
versions; don't `pip install --upgrade` anything.

**If broken at the GPU step:** the fallback is to ship A2 as
"runnable but not yet completed; weights pending Q3 2026". RESULTS.md
should note this honestly.

---

### A3. `research-graphs` (publish pending)

**Purpose**: 6 interactive Plotly charts (entity graph, corridor
Sankey, per-category benchmark bars, fee-camouflage heatmap, ILO
indicator hits, RAG corpus sunburst). CPU-only, ~30 sec.

**Test checklist:**
- [ ] Wheels install succeeds
- [ ] All 6 Plotly charts render (look for "Plotly" loading
      message or actual chart)
- [ ] Each chart is **interactive** (hover labels work, zoom works,
      no broken JS)
- [ ] Sankey + sunburst render at the right size (not collapsed
      to 0 height — Kaggle's HTML rendering can do this)
- [ ] Total runtime ~30 sec on CPU

**Success looks like:** a judge sees the corpus + the analysis at
a glance via visualization.

**Common confusion:** Plotly's JS-injection path needs Internet
permission on Kaggle. Verify enabled.

**If broken:** charts may not render in Kaggle's saved-output
viewer; ensure they at least render in the live notebook.

---

### A4. `chat-playground-with-agentic-research` (publish pending)

**Purpose**: chat surface + 5th toggle for agentic web research
(DuckDuckGo + httpx + Wikipedia). All open-source, no API keys.

**Test checklist:**
- [ ] Wheels install succeeds
- [ ] Chat surface renders with **5 toggles** (the original 4 + new
      "Web Research")
- [ ] Toggling Web Research ON + asking a question that needs
      current info ("What's the latest POEA MC?") triggers a
      multi-step loop: web_search → web_fetch → wikipedia → done
- [ ] **Each step visible** in the Pipeline modal (the loop is
      the demo)
- [ ] PII filter rejects an outbound query containing a name or
      passport number (verify the safety boundary)
- [ ] Audit log records hashes of outbound queries (not plaintext)
- [ ] BYOK panel visible with empty fields for Tavily / Brave /
      Serper (so judges who have keys can swap providers)

**Success looks like:** a judge sees how Gemma 4's function-calling
+ a deterministic tool loop combine to do real-time web research
inside the harness boundary.

**Common confusion:** DuckDuckGo HTML scraping is rate-limited;
on a busy day, judges may see "no results." Note this in a banner.

---

### A5. `chat-playground-jailbroken-models` (publish pending) ⭐ STRONGEST PROOF

**Purpose**: load an abliterated/cracked Gemma 4 variant (default:
`dealignai/Gemma-4-31B-JANG_4M-CRACK`) + run the same harness.
**Strongest "real, not faked" proof** — the harness produces safe
outputs even when the base model has had its refusals ablated.

**Test checklist:**
- [ ] Wheels install succeeds
- [ ] Loads abliterated model successfully (verify it's the
      jailbroken variant, not regular Gemma 4 — the model name
      should match)
- [ ] **Without harness**, the abliterated model answers a
      jailbreak prompt with explicit harmful content (this is the
      controlled comparison; judges need to see the model is
      actually jailbroken)
- [ ] **With harness ON**, the same jailbreak prompt produces a
      response that still cites the controlling statute + still
      refuses the harmful framing
- [ ] Side-by-side comparison visible (toggle on/off, see the
      difference)
- [ ] Notebook explicitly notes: "this is an experiment in
      adversarial robustness; do not redistribute the abliterated
      model weights — Gemma TOU + responsible-disclosure
      considerations apply"

**Success looks like:** the strongest evidence we can produce
that the harness ISN'T just relying on the underlying model's
existing safety training.

**Common confusion:** judges may assume jailbroken = unsafe-by-design.
The notebook's framing must clarify: we're stress-testing OUR
contribution (the harness), not endorsing jailbreaks.

**If the abliterated model is unreachable:** the notebook should
fall back gracefully to `Gemma-4-9b-uncensored` or another
publicly-available variant. Document the fallback in the notebook
header.

---

## After all 11 are tested

Once you've run the smoke pass:

1. **Update `kaggle/_INDEX.md`** with publish status per notebook
2. **Update `docs/FOR_JUDGES.md`** to remove "publish pending" markers
   from notebooks now confirmed live
3. **Push notebooks** in priority order:
   1. #2 (headline demo)
   2. #6 (live-demo)
   3. #5 (NGO dashboard)
   4. #3, #4 (sandbox)
   5. A1, A4, A5 (extension)
   6. A2 (fine-tune; only after the GPU run completes)
   7. A3 (research graphs)
4. **Verify each pushed notebook** by opening its public URL and
   running the first 3 cells from a logged-out browser
5. **Update `RESULTS.md`** with the bench-and-tune numbers once
   A2 has run

## Submission-day checklist

- [ ] All 11 notebooks visible at their canonical URLs
- [ ] All 11 wheels datasets attached to their notebooks
- [ ] HF Hub model card live (if A2 completed)
- [ ] Video uploaded + linked in writeup_draft.md
- [ ] writeup_draft.md final version pinned to a release SHA
- [ ] FOR_JUDGES.md final version pinned to same SHA
- [ ] RESULTS.md final numbers
- [ ] Submit on the Kaggle competition page on or before 2026-05-18
