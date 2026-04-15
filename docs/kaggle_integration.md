# Kaggle Integration Plan

> How we use Kaggle's API, Notebooks, Datasets, and free GPU compute as
> primary infrastructure for the Gemma 4 Good Hackathon project.
>
> Motivation: the author's local machine is not strong enough for Phase 1
> baseline runs (21K × 2 models) or Phase 3 fine-tuning (Unsloth + Gemma 4
> E4B on a single GPU). Kaggle provides the needed compute for free, and
> aligns naturally with the hackathon's delivery channel.
>
> Last updated: 2026-04-11.

## TL;DR

**Kaggle is our primary compute for Phases 1-3 and our primary submission
channel for the final writeup.** Phase 4 deployment (the live demo) still
goes to HuggingFace Spaces because Kaggle Notebooks aren't meant for
long-running web servers.

| Phase | Compute | Artifact | Hosted on |
|---|---|---|---|
| **Phase 1** Exploration (21K × 2 models) | Kaggle GPU (T4) | `reports/phase1/*.md` + `data/phase1/baselines.sqlite` | Kaggle Dataset |
| **Phase 2** Comparison (10 models) | Kaggle GPU + APIs | `reports/phase2/*.md` + `data/phase2/comparison.sqlite` | **public Kaggle Dataset** |
| **Phase 3** Enhancement (Unsloth fine-tune) | **Kaggle GPU (T4)** | LoRA adapters + merged fp16 + GGUF quantizations | HF Hub + Kaggle Model |
| **Phase 4** Implementation (live demo) | HF Spaces free tier (CPU) | FastAPI + web UI | HF Spaces (primary), Kaggle Notebook (reference) |
| **Submission** | — | Kaggle Writeup | **kaggle.com/competitions/gemma-4-good-hackathon** |

---

## 1. Kaggle resources we'll use

### 1.1 Free GPU quota (corrected 2026-04-11 after direct research)

**IMPORTANT CORRECTION** — an earlier version of this doc claimed 30h T4
+ 9h P100 + 20h TPU = 59 weekly GPU-hours. That was wrong. The real
numbers (verified via the Kaggle docs and Community Hackathon FAQ):

- **GPU: 30 hours / week TOTAL**, split between P100 and T4 × 2 as you
  choose per-session. You pick the accelerator when you create a
  notebook; the same 30h pool covers both.
- **TPU v3-8: 20 hours / week** (separate pool)
- **Per-session limit: 12 hours** of wall-clock for GPU/CPU sessions,
  **9 hours** for TPU sessions
- **Per-session auto-saved disk: 20 GB**

**What fits where (realistic):**
- Gemma 4 E2B (~2B params, 4-bit) — fits on T4 × 2 or P100
- Gemma 4 E4B (~4B params, 4-bit) — fits on T4 × 2 or P100 (~3-5 GB VRAM)
- Gemma 4 E4B full fine-tune with Unsloth + LoRA (r=16) — ~12 GB VRAM,
  comfortable on T4 × 2 or P100
- Qwen 2.5 32B (4-bit) — tight but doable on T4 × 2 (~18 GB); better on P100
- GPT-OSS 20B (4-bit) — fits on T4 × 2 or P100
- Anything 70B+ — out of reach on Kaggle free tier; use API for DeepSeek V3

**Weekly budget (revised):** **30 GPU-hours/week total** + 20 TPU-hours.
That's tighter than the old estimate:
- Phase 1 (Gemma E2B + E4B baseline across 4 tasks on 1-2K samples) — ~5-6 h GPU
- Phase 2 (cross-model on 6 locally-runnable models) — ~12-18 h GPU
- Phase 3 (Unsloth fine-tune on E4B, 2 epochs) — ~5-6 h GPU

**Total: 22-30 GPU-hours.** Fits in one weekly quota ONLY if every run
lands first-try. Realistic plan: stretch Phases 1 + 2 across week 1, run
Phase 3 at the start of week 2 after the GPU quota resets. Leave room
for one re-run.

### 1.2 Kaggle Datasets
- Public Datasets are indexable and citable
- Each Dataset can be up to **100 GB** (current limit; much bigger than
  we need)
- Versioned — new pushes create new versions
- Attachable to Notebooks and Writeups
- **Strategy:** publish our Phase 2 comparison results as a public Kaggle
  Dataset (`trafficking-llm-safety-benchmark-results`) so it's citable by
  other researchers

### 1.3 Kaggle Notebooks (Kernels)
- Interactive Jupyter-like environment
- GPU-enabled with a single config flag
- Can be attached to competitions as submission
- Can import Datasets directly via the side panel
- Version-controlled (every save = new version)
- Can be **published as private** and become **automatically public after
  the competition deadline** (per the rules) — useful if we want to keep
  WIP private until submission
- **Strategy:** at least two notebooks
  - `phase3_finetune` — the training run (proves the work is real)
  - `submission` — the final hackathon writeup + code walkthrough,
    attached to the Kaggle Writeup

### 1.4 Kaggle Models (model hosting)

**Confirmed via direct CLI inspection** (`kaggle models --help`). The
model hosting surface has three tiers:

```
Model            (e.g., "gemma-4-e4b-safetyjudge")
└── Variation    (e.g., "q5_k_m")
    └── Version  (e.g., "v1", "v2", ...)
```

CLI commands for the full lifecycle:

```bash
# create the model (one-time)
kaggle models init -p kaggle/models/safetyjudge/
kaggle models create -p kaggle/models/safetyjudge/

# create a variation per quantization
kaggle models instances init -p kaggle/models/safetyjudge/q5_k_m/
kaggle models instances create -p kaggle/models/safetyjudge/q5_k_m/

# push a new version whenever weights change
kaggle models instances versions create \
    taylorsamarel/gemma-4-e4b-safetyjudge/GgufQuant/q5_k_m \
    -p kaggle/models/safetyjudge/q5_k_m/ \
    -n "v1.0.0: first release"
```

**Strategy:** cross-publish the Phase 3 weights to both HF Hub AND
Kaggle Models. HF Hub is primary (model card, community). Kaggle Models
lets judges load our model inside their Kaggle Notebook with one click —
critical for verification since they can reproduce the submission
notebook's output without leaving the Kaggle platform.

### 1.5 Kaggle Writeups (submission format — **corrected**)

**IMPORTANT CORRECTION** — an earlier version of this doc implied that
`kaggle competitions submit` could submit a Writeup. That's false. The
`competitions submit` command is for prediction competitions only (it
takes a CSV of predictions). Hackathons use the Writeup format, which is
**submitted exclusively via the web UI.**

What we actually do:

1. Publish the submission notebook via `kaggle kernels push`
2. Publish the dataset(s) via `kaggle datasets create` / `version`
3. Publish the model via `kaggle models instances versions create`
4. Go to the hackathon page in a browser → "New Writeup" → attach the
   notebook, model, dataset, YouTube URL, live demo URL, cover image
5. Click **Submit** in the browser

The Kaggle CLI covers steps 1-3 but **not step 4-5**. Budget time in
Week 5 for manual web-UI submission.

### 1.6 Kaggle `files upload` (new; low-level convenience)

The CLI also has a top-level `kaggle files upload` command for direct
file uploads outside the datasets/models system. We don't need it for
the primary workflow but it's available as a fallback for one-off file
shipping.

---

## 2. Setup: one-time bootstrapping

### 2.1 API token (required, blocking)

The Kaggle CLI is already installed (v2.0.1, verified in the earlier
session). **What's missing is the API token.**

```bash
# 1. Go to https://www.kaggle.com/settings
# 2. Click "Create New Token" — this downloads kaggle.json
# 3. Move it to the expected location:
mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
chmod 600 ~/.kaggle/kaggle.json       # unix only; Windows can skip

# 4. Verify:
kaggle competitions list | head -5
```

**On Windows (bash / Git Bash):**
```bash
mkdir -p "/c/Users/amare/.kaggle"
mv "/c/Users/amare/Downloads/kaggle.json" "/c/Users/amare/.kaggle/kaggle.json"
kaggle competitions list | head -5
```

Once this works, every other Kaggle integration step is unblocked.

### 2.2 Join the competition

```bash
kaggle competitions list -s "Gemma 4 Good"
# then via web UI:
# Click "Join Competition" on the page to accept rules
```

Necessary before any submission-related commands (`kaggle competitions
submit`) will work.

### 2.3 Environment variable pin

Add to `.env` (gitignored):
```
GEMMA4_KAGGLE_USERNAME=<your_kaggle_username>
GEMMA4_KAGGLE_COMPETITION=gemma-4-good-hackathon
```

---

## 3. Data flow: local <-> Kaggle

### 3.1 Sync direction decision

We use **Kaggle as the compute plane** and **local (+ GitHub) as the
source-of-truth plane**. Code lives in local git; Kaggle Notebooks are
generated from local scripts and published.

```
                LOCAL (source of truth)
                        │
                        │ (A) push dataset -> Kaggle Dataset
                        │ (B) push notebook -> Kaggle Kernel
                        │
                        v
                KAGGLE (compute + publish)
                        │
                        │ (C) run GPU job
                        │ (D) pull results
                        │
                        v
                LOCAL (results + reports)
                        │
                        │ commit -> GitHub
                        │
                        v
                    SUBMIT
```

### 3.2 Push: local -> Kaggle

**3.2a Publish a Kaggle Dataset** (e.g., the benchmark test data)

```bash
# one-time: initialize metadata
mkdir -p kaggle/datasets/trafficking-benchmark-21k
cd kaggle/datasets/trafficking-benchmark-21k
kaggle datasets init

# edit dataset-metadata.json:
# {
#   "title": "Trafficking LLM Safety Benchmark (21K tests)",
#   "id": "taylorsamarel/trafficking-llm-safety-benchmark-21k",
#   "licenses": [{"name": "MIT"}]
# }

# copy the files we want to ship
cp _reference/trafficking-llm-benchmark-gitlab/*.json kaggle/datasets/trafficking-benchmark-21k/

# create (first time)
kaggle datasets create -p kaggle/datasets/trafficking-benchmark-21k

# or update (subsequent)
kaggle datasets version -p kaggle/datasets/trafficking-benchmark-21k -m "v2: new splits"
```

**3.2b Push a Kaggle Notebook (Kernel)**

```bash
mkdir -p kaggle/kernels/phase3_finetune
cd kaggle/kernels/phase3_finetune
kaggle kernels init

# edit kernel-metadata.json:
# {
#   "id": "taylorsamarel/phase3-finetune",
#   "title": "Phase 3 - Unsloth Fine-tune of Gemma 4 E4B",
#   "code_file": "phase3_finetune.ipynb",
#   "language": "python",
#   "kernel_type": "notebook",
#   "is_private": true,
#   "enable_gpu": true,
#   "enable_tpu": false,
#   "enable_internet": true,
#   "dataset_sources": [
#     "taylorsamarel/trafficking-llm-safety-benchmark-21k"
#   ],
#   "competition_sources": [],
#   "kernel_sources": []
# }

# create or update
kaggle kernels push -p kaggle/kernels/phase3_finetune
```

### 3.3 Pull: Kaggle -> local

```bash
# wait for the kernel to finish (poll or check the Kaggle UI)
kaggle kernels status taylorsamarel/phase3-finetune

# once "complete", download outputs
kaggle kernels output taylorsamarel/phase3-finetune -p data/phase3_outputs/
```

---

## 4. Per-phase usage

### 4.1 Phase 1 — Exploration on Kaggle

**Notebook:** `kaggle/kernels/phase1_exploration/phase1_exploration.ipynb`

Structure:
1. Install dependencies (`unsloth`, `llama-cpp-python`, `transformers`,
   `bitsandbytes`, `sentence-transformers`)
2. Load the 21K benchmark Dataset (attached via Kaggle UI)
3. Load Gemma 4 E2B in 4-bit via Unsloth or transformers
4. Run the 4 capability tests (from `src/phases/categories.py`)
5. Save results to `/kaggle/working/baselines_e2b.sqlite`
6. Repeat for E4B
7. Cluster failures, produce `failure_taxonomy.md`
8. Zip outputs

**GPU budget:** T4 single for ~2-3 hours per model = ~5 hours total
**Commit back:** pull the SQLite files and reports locally for the
repository

### 4.2 Phase 2 — Comparison on Kaggle + APIs

**Notebook:** `kaggle/kernels/phase2_comparison/phase2_comparison.ipynb`

Structure:
1. Install dependencies
2. Attach both the benchmark Dataset and the Phase 1 baseline results
3. Iterate over `COMPARISON_FIELD` from `src/phases/comparison/model_list.py`
4. For each local-inference model, load via Unsloth / transformers
5. For each API model, call out through secrets (Kaggle Notebook supports
   "Secrets" for API keys — more secure than env vars)
6. Run the 4 capability tests
7. Aggregate, compute head-to-head tables
8. Save `data/phase2/comparison.sqlite` to `/kaggle/working/`
9. Push to public Kaggle Dataset `trafficking-llm-safety-comparison`

**GPU budget:** mix of T4 single (small models) and P100 / dual T4
(Qwen 32B, GPT-OSS 20B) = ~15-20 hours
**API budget:** ~$50-100 total for Claude / GPT-4o-mini / DeepSeek V3
**Kaggle Secrets setup:**
- In the Kaggle Notebook UI → "Add-ons" → "Secrets"
- Add `GEMMA4_ANTHROPIC_KEY`, `GEMMA4_OPENAI_KEY`, `GEMMA4_MISTRAL_KEY`,
  `GEMMA4_DEEPSEEK_KEY`
- Loaded in the notebook via `from kaggle_secrets import UserSecretsClient`

### 4.3 Phase 3 — Fine-tune on Kaggle (**primary use case**)

**Notebook:** `kaggle/kernels/phase3_finetune/phase3_finetune.ipynb`

This is the notebook that matters most. It runs the Unsloth + LoRA
fine-tune and produces the deployable artifacts.

Structure:
1. Install Unsloth (+ matching `torch` / `bitsandbytes` / `xformers`)
2. Attach the cleaned training dataset (published as
   `trafficking-llm-safety-training-data`)
3. Load base model: `unsloth/gemma-4-e4b-bnb-4bit`
4. Apply LoRA config (r=16, alpha=32, target_modules=attn+mlp)
5. Load the dataset, format as Unsloth chat JSONL
6. Run `SFTTrainer` for 2 epochs
7. Save LoRA adapters to `/kaggle/working/lora_adapters/`
8. Merge LoRA -> fp16
9. Convert to GGUF via `llama.cpp` (installed in-notebook)
10. Quantize to q4_k_m / q5_k_m / q8_0
11. Upload to HF Hub (using `HF_TOKEN` secret)
12. Also publish as a Kaggle Model (using the Kaggle API)
13. Zip the notebook's outputs for download

**GPU budget:** T4 single for ~6 hours = 6 hours. Well within the weekly
30h T4 quota, with room for 2-3 re-runs if the first pass needs tweaking.

**Sync pattern:** after the run, pull the GGUF files locally via
`kaggle kernels output` and commit to a release branch in GitHub.

### 4.4 Phase 4 — Deployment stays on HF Spaces

Kaggle Notebooks are not designed for long-running HTTP servers. Deploy
the demo to HuggingFace Spaces (free tier, FastAPI + Docker).

**However, publish a "read-only" notebook** in Kaggle that:
1. Loads the Phase 3 GGUF from Kaggle Models
2. Runs a handful of example inputs through the judge
3. Links to the live HF Spaces demo
4. This notebook is a **reference implementation** that judges can run to
   reproduce the live demo's output without visiting the external URL

### 4.5 Submission notebook

**Notebook:** `kaggle/kernels/submission/submission.ipynb`

This is the notebook attached to the Kaggle Writeup itself. It should be
a narrative walkthrough:

1. Introduction + problem statement (first ~200 words of the writeup)
2. Architecture overview (inline diagram, reference to GitHub)
3. Phase 1 baseline numbers (loaded from the baseline Dataset)
4. Phase 2 comparison table (loaded from the comparison Dataset)
5. Phase 3 ablation table (loaded from the training-data Dataset)
6. Live example: load the q5_k_m model from Kaggle Models and evaluate a
   real prompt
7. Link to the live demo, GitHub repo, HF Hub model, video
8. Closing: call to action, contact info

The notebook **should run end-to-end** so judges can rerun any section
themselves. That's the strongest proof of "not faked for demo."

---

## 5. Repository structure additions

Add to the existing gemma4_comp/ tree:

```
gemma4_comp/
├── kaggle/                        # NEW - all Kaggle-bound artifacts
│   ├── README.md                  # how to use this directory
│   ├── datasets/
│   │   ├── trafficking-benchmark-21k/
│   │   │   ├── dataset-metadata.json
│   │   │   └── (files to ship)
│   │   ├── trafficking-llm-safety-comparison/
│   │   │   └── dataset-metadata.json
│   │   └── trafficking-llm-safety-training-data/
│   │       └── dataset-metadata.json
│   │
│   ├── kernels/
│   │   ├── phase1_exploration/
│   │   │   ├── kernel-metadata.json
│   │   │   └── phase1_exploration.ipynb
│   │   ├── phase2_comparison/
│   │   │   ├── kernel-metadata.json
│   │   │   └── phase2_comparison.ipynb
│   │   ├── phase3_finetune/
│   │   │   ├── kernel-metadata.json
│   │   │   └── phase3_finetune.ipynb
│   │   └── submission/
│   │       ├── kernel-metadata.json
│   │       └── submission.ipynb
│   │
│   └── sync.py                    # orchestration: pushes + pulls
│
└── scripts/
    └── kaggle/
        ├── push_dataset.sh        # thin wrappers for convenience
        ├── push_kernel.sh
        └── pull_kernel_output.sh
```

I'll add these to a new `scaffold_kaggle.py` scaffold script (analogous
to `scaffold_phases.py`) on the next pass.

---

## 6. Notebook generation from the Python codebase

**Problem:** We want to write the real code in `src/` (modular, testable,
imports clean) but deliver it to Kaggle as Jupyter notebooks. Writing the
notebooks by hand means divergence.

**Solution:** Use `jupytext` to keep each notebook as a **paired
`.py` + `.ipynb`** file. The `.py` is the source of truth (versioned in
git, lintable, testable); jupytext regenerates the `.ipynb` from it
automatically.

```bash
pip install jupytext

# create a paired notebook from a .py file
jupytext --set-formats py:percent,ipynb kaggle/kernels/phase3_finetune/phase3_finetune.py

# sync .py -> .ipynb (or vice versa)
jupytext --sync kaggle/kernels/phase3_finetune/phase3_finetune.py
```

In the `.py` file, use `# %%` cell markers:
```python
# %% [markdown]
# # Phase 3 - Unsloth Fine-tune of Gemma 4 E4B
# ...

# %%
import unsloth
from unsloth import FastLanguageModel
# ...
```

This gives us:
- Unit tests in CI (since the notebook is a real `.py`)
- Clean git diffs (notebooks are terrible for git; .py files are fine)
- One-command push to Kaggle (`jupytext --sync && kaggle kernels push`)

Add `jupytext>=1.16` to requirements.txt.

---

## 7. Secrets management

### 7.1 Local (dev + CI)
`.env` (gitignored) + `src/config/loader.py` Pydantic Settings — already
set up.

### 7.2 Kaggle (notebooks)
Kaggle Notebooks have a built-in Secrets UI:
- Sidebar → "Add-ons" → "Secrets"
- Add key/value pairs
- Access in the notebook:
  ```python
  from kaggle_secrets import UserSecretsClient
  secrets = UserSecretsClient()
  anthropic_key = secrets.get_secret("GEMMA4_ANTHROPIC_KEY")
  ```

### 7.3 Never commit
- `kaggle.json`
- API keys
- `.env`
- Kaggle Secret contents

Add to `.gitignore` if not already:
```
.kaggle/
kaggle.json
.env
.env.*
!.env.template
```

(`.env.template` stays committed as the reference.)

---

## 8. CI integration

For the public GitHub repo, add a GitHub Actions job that:
1. On push to `main`, runs `jupytext --sync` on every `.py` notebook
2. Verifies the `.ipynb` is up-to-date with the `.py`
3. Runs `kaggle kernels push` for the submission notebook (with a
   `KAGGLE_USERNAME` + `KAGGLE_KEY` secret)
4. Optionally runs `kaggle datasets version` to bump a versioned dataset

This means the GitHub repo and the Kaggle Notebooks stay in sync
automatically. Judges can use either one.

---

## 9. Decision: where each artifact lives

| Artifact | Primary | Mirror | Notes |
|---|---|---|---|
| Source code | GitHub (`TaylorAmarelTech/gemma4_comp`) | Kaggle Notebooks | git = authoritative |
| Training data splits | Kaggle Dataset | (private) | too big for git |
| Phase 1 baseline results | Kaggle Dataset | local `data/phase1/` | 1-2 GB |
| Phase 2 comparison results | Kaggle Dataset (public) | — | citable |
| Phase 3 LoRA adapters | HF Hub | Kaggle Model | both |
| Phase 3 merged fp16 weights | HF Hub | Kaggle Model | both |
| Phase 3 GGUF quantizations | HF Hub | Kaggle Model | both |
| Live demo | HF Spaces | — | free tier, public |
| Submission notebook | Kaggle | GitHub (as .py) | attached to writeup |
| Final Writeup | Kaggle | GitHub (as markdown) | attached at submission |
| Video | YouTube | (archive copy) | public link in writeup |

---

## 10. Week-by-week Kaggle touchpoints

Integrated into the existing 5-week timeline:

### Week 1 (Apr 14-20)
- **Mon AM**: Create Kaggle API token, verify CLI works (blocking setup)
- **Mon AM**: Join the competition via the Kaggle UI
- **Mon PM**: Publish `trafficking-benchmark-21k` as a private Kaggle
  Dataset (from `_reference/trafficking-llm-benchmark-gitlab/`)
- **Tue**: Scaffold `kaggle/kernels/phase1_exploration/` with jupytext
- **Wed-Thu**: Port the Phase 1 runner to the notebook, test on a 100-
  sample slice locally
- **Fri**: Push to Kaggle, run full 21K × Gemma E2B (~2-3h T4)
- **Sat**: Same for E4B
- **Sun**: Pull results, generate failure taxonomy, commit reports

### Week 2 (Apr 21-27)
- **Mon**: Add Kaggle Secrets for API keys (Anthropic / OpenAI / Mistral
  / DeepSeek)
- **Mon**: Scaffold `kaggle/kernels/phase2_comparison/`
- **Tue-Wed**: Run comparison notebook against all 10 models (split into
  local-GPU and API-only batches)
- **Thu**: Aggregate results, generate tables and plots
- **Fri**: Publish `trafficking-llm-safety-comparison` as **public**
  Kaggle Dataset
- **Sat-Sun**: Phase 2 report written, Kaggle Dataset linked in writeup
  draft

### Week 3 (Apr 28 - May 4)
- **Mon**: Publish `trafficking-llm-safety-training-data` as private
  Kaggle Dataset (the JSONL splits)
- **Tue**: Scaffold `kaggle/kernels/phase3_finetune/`
- **Wed**: Dry-run the fine-tune notebook on 1K samples
- **Thu**: Full fine-tune run on the 21K training data (~6h T4)
- **Fri**: Merge LoRA, convert to GGUF, quantize
- **Fri**: Push to HF Hub + Kaggle Models
- **Sat-Sun**: Run Phase 3 ablation (A/B/C/D configs), write report

### Week 4 (May 5-11)
- Deployment on HF Spaces (not Kaggle)
- **Fri**: Scaffold `kaggle/kernels/submission/` (the notebook attached to
  the writeup)

### Week 5 (May 12-18)
- **Mon**: Cover image designed
- **Tue**: Record video
- **Wed**: Final writeup pass
- **Thu**: Dress rehearsal + submission notebook final commit
- **Fri**: Submit
- **Sat-Sun**: Buffer

---

## 11. Open decisions

1. **Kaggle Notebook for the writeup, or external GitHub?**
   - **Kaggle Notebook**: tightest submission integration, but limited
     markdown rendering (no embeddable widgets)
   - **External GitHub**: full control of formatting, but one extra click
     for judges
   - **Recommendation:** **Kaggle Notebook** (for the submission writeup
     itself) + **GitHub** (for the full code repo linked from the
     writeup). Judges get a one-click runnable notebook inside the
     writeup and a full engineering-grade repo on GitHub when they click
     through.

2. **Team name for Kaggle competition submission**
   - Single submitter: use your personal Kaggle username
   - Team: create a Kaggle Team via the competition UI (up to 5 members)
   - **Recommendation:** start solo; add team members later if needed

3. **Private vs public kernel during development**
   - **Recommendation:** private during weeks 1-4, flip to public for the
     submission kernel on submission day. Kaggle automatically makes
     attached private resources public after the deadline, so either way
     works, but publishing before the deadline is an option if you want
     the community to comment.

4. **Internal vs Internet-enabled Kaggle Notebooks**
   - Notebooks must have `enable_internet: true` in their metadata to
     access HF Hub, download models, call APIs
   - **Recommendation:** `enable_internet: true` for all our notebooks
     since they need HF Hub model downloads

5. **Notebook language: Python or R?**
   - **Python** (no discussion needed)

---

## 12. Risks specific to Kaggle

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Weekly GPU quota exhaustion mid-run | Low | High | Run budget-critical jobs Mon/Tue; leave Sat/Sun for retries |
| Kaggle platform downtime during a training run | Low | Medium | Checkpoint every epoch; fall back to local+cloud if needed |
| Private notebook unexpectedly public | Low | High | Double-check `is_private: true` in `kernel-metadata.json` before `kaggle kernels push` |
| API key leaked via notebook output | Medium | Very High | Never print secrets; use `kaggle_secrets` API; add git-leak pre-commit hook |
| Kaggle Model upload API is flaky | Low | Medium | HF Hub is primary; Kaggle Model is mirror |
| GPU environment updates break Unsloth compatibility | Medium | High | Pin the GPU environment version in `kernel-metadata.json`; test on the exact pinned version week 1 |

---

## 13. Integration with the existing project structure

The Kaggle integration is **additive**, not a rewrite. Everything already
in the project (`src/`, `_reference/`, `docs/architecture.md`,
`docs/project_phases.md`) stays exactly as it is. Kaggle gets a new
top-level directory `kaggle/` that contains the metadata + paired `.py`
notebook sources, and the existing `src/phases/*/runner.py` stubs are
imported *into* the notebooks rather than replaced.

The contract stays: **phase runners live in `src/phases/`, Kaggle
notebooks are thin orchestration wrappers that call them and persist the
results to Kaggle Datasets / Models.**

---

## 14. First three concrete actions

If you approve this plan, the first three things to do (in order):

1. **Create the Kaggle API token** (Kaggle Settings → Create New Token),
   move `kaggle.json` to `C:\Users\amare\.kaggle\`, and confirm with
   `kaggle competitions list | head`. **Blocking — nothing else works
   until this is done.**
2. **Join the Gemma 4 Good Hackathon** via the competition UI so
   `kaggle competitions submit` is authorized.
3. **I scaffold `kaggle/`** with metadata files + jupytext-paired
   starter notebooks (similar to `scaffold_phases.py`), which gives us a
   working skeleton we can push to Kaggle on day 1.

Say go and I'll start with #3.
