# Goal: standardized titles, index notebook live, all 28 published

You are working in `C:\Users\amare\OneDrive\Documents\gemma4_comp\`.

## Definition of done

The pass is complete when ALL of these are true:

1. Every notebook title matches the canonical format (defined below).
2. The index notebook (000) is live at a resolvable Kaggle URL and
   contains a clickable table of all 28 notebooks with their live
   URLs.
3. All 28 notebooks are live on Kaggle, HTTP 200, no 404.
4. Every `kernel-metadata.json` `id` matches the live Kaggle slug.
5. Every notebook has `keywords`, `is_private: false`, and
   `competition_sources: ["gemma-4-good-hackathon"]`.
6. `README.md`, `docs/notebook_guide.md`, and
   `docs/current_kaggle_notebook_state.md` link only to live URLs.
7. `scripts/verify_kaggle_urls.py` reports 28 of 28 at HTTP 200.

## The canonical title format (THE STANDARD)

Every notebook title must match this format exactly:

```
<number>: DueCare <Descriptive Title in Title Case>
```

Where `<number>` is the three-digit zero-padded curriculum ID for
that specific notebook (for example, `000`, `010`, `100`, `300`).
The number is not a placeholder in the published title; it is the
actual number. Real examples:

```
000: DueCare Index and Reading Guide
100: DueCare Gemma 4 Exploration (Phase 1 Baseline)
300: DueCare Adversarial Resistance Against 15 Attack Vectors
```

### Why the three-digit number

- First digit is the section. `0xx` orientation, `1xx` exploration,
  `2xx` comparison, `3xx` adversarial, `4xx` tools and evaluation,
  `5xx` pipeline and fine-tuning, `6xx` results.
- Third digit is the sibling position. Stepping by 10 (010, 020,
  030) leaves 9 insertion slots between adjacent notebooks so new
  ones can be added later without renumbering.
- Three digits zero-padded so `030` sorts before `100` in every
  filesystem, Kaggle search, and doc index. Two digits would break
  sort order.

### Title rules

- Colon plus single space after the number.
- The word `DueCare` appears in every title (capital D, capital C).
- Never `Duecare`, never `duecare`, never `DUECARE`.
- Descriptive portion uses Title Case.
- No em dashes. Use hyphens, colons, parentheses, or commas.
- No emojis.
- No "vs" mixed with "versus"; standardize on `vs` for all
  comparison notebooks.
- Maximum 90 characters total.

### The canonical 28 titles (already applied to metadata)

These are the authoritative titles for every kernel. If a title
differs from this list, update it:

```
000: DueCare Index and Reading Guide
010: DueCare Quickstart in 5 Minutes
100: DueCare Gemma 4 Exploration (Phase 1 Baseline)
110: DueCare Prompt Prioritizer
120: DueCare Prompt Remixer
200: DueCare Cross-Domain Proof
210: DueCare Gemma 4 vs OSS Models
220: DueCare Gemma 4 vs 6 OSS Models via Ollama Cloud
230: DueCare Gemma 4 vs Mistral Family
240: DueCare Gemma 4 vs Frontier Cloud Models
250: DueCare Anchored Grading vs Reference Responses
260: DueCare Plain vs Retrieval-Augmented vs System-Guided
270: DueCare Gemma 2 vs 3 vs 4 Safety Gap
300: DueCare Adversarial Resistance Against 15 Attack Vectors
310: DueCare Adversarial Prompt Factory
320: DueCare Red-Team Safety Gap
400: DueCare Gemma 4 Native Tool Calls and Multimodal
410: DueCare Six-Dimension LLM Judge Grading
420: DueCare Multi-Turn Conversation Escalation
430: DueCare 54-Criterion Pass/Fail Rubric Evaluation
440: DueCare Per-Prompt Rubric Generator
450: DueCare Contextual Worst-Response Judge
500: DueCare 12-Agent Gemma 4 Safety Swarm
510: DueCare Phase 2 Model Comparison
520: DueCare Phase 3 Curriculum Builder
530: DueCare Phase 3 Unsloth Fine-Tune
600: DueCare Results Dashboard
610: DueCare End-to-End Submission Walkthrough
```

## Step 1. Authenticate Kaggle

Credentials must be on disk before anything else:

a. Visit https://www.kaggle.com/settings/account.
b. Click "Create New Token". A `kaggle.json` downloads.
c. Move it to `C:\Users\amare\.kaggle\kaggle.json`.
d. Run:

```
python scripts/publish_kaggle.py auth-check
```

Must exit 0. Do not proceed otherwise.

## Step 2. Verify titles match the canonical list

```
python -c "
import json
from pathlib import Path
CANONICAL = {
    'duecare_000_index': '000: DueCare Index and Reading Guide',
    'duecare_010_quickstart': '010: DueCare Quickstart in 5 Minutes',
    'duecare_100_gemma_exploration': '100: DueCare Gemma 4 Exploration (Phase 1 Baseline)',
    'duecare_110_prompt_prioritizer': '110: DueCare Prompt Prioritizer',
    'duecare_120_prompt_remixer': '120: DueCare Prompt Remixer',
    'duecare_200_cross_domain_proof': '200: DueCare Cross-Domain Proof',
    'duecare_210_oss_model_comparison': '210: DueCare Gemma 4 vs OSS Models',
    'duecare_220_ollama_cloud_comparison': '220: DueCare Gemma 4 vs 6 OSS Models via Ollama Cloud',
    'duecare_230_mistral_family_comparison': '230: DueCare Gemma 4 vs Mistral Family',
    'duecare_240_openrouter_frontier_comparison': '240: DueCare Gemma 4 vs Frontier Cloud Models',
    'duecare_250_comparative_grading': '250: DueCare Anchored Grading vs Reference Responses',
    'duecare_260_rag_comparison': '260: DueCare Plain vs Retrieval-Augmented vs System-Guided',
    'duecare_270_gemma_generations': '270: DueCare Gemma 2 vs 3 vs 4 Safety Gap',
    'duecare_300_adversarial_resistance': '300: DueCare Adversarial Resistance Against 15 Attack Vectors',
    'duecare_310_prompt_factory': '310: DueCare Adversarial Prompt Factory',
    'duecare_320_supergemma_safety_gap': '320: DueCare Red-Team Safety Gap',
    'duecare_400_function_calling_multimodal': '400: DueCare Gemma 4 Native Tool Calls and Multimodal',
    'duecare_410_llm_judge_grading': '410: DueCare Six-Dimension LLM Judge Grading',
    'duecare_420_conversation_testing': '420: DueCare Multi-Turn Conversation Escalation',
    'duecare_430_rubric_evaluation': '430: DueCare 54-Criterion Pass/Fail Rubric Evaluation',
    'duecare_440_per_prompt_rubric_generator': '440: DueCare Per-Prompt Rubric Generator',
    'duecare_450_contextual_worst_response_judge': '450: DueCare Contextual Worst-Response Judge',
    'duecare_500_agent_swarm_deep_dive': '500: DueCare 12-Agent Gemma 4 Safety Swarm',
    'duecare_510_phase2_model_comparison': '510: DueCare Phase 2 Model Comparison',
    'duecare_520_phase3_curriculum_builder': '520: DueCare Phase 3 Curriculum Builder',
    'duecare_530_phase3_unsloth_finetune': '530: DueCare Phase 3 Unsloth Fine-Tune',
    'duecare_600_results_dashboard': '600: DueCare Results Dashboard',
    'duecare_610_submission_walkthrough': '610: DueCare End-to-End Submission Walkthrough',
}
for d, want in CANONICAL.items():
    meta = json.loads((Path('kaggle/kernels')/d/'kernel-metadata.json').read_text('utf-8'))
    if meta['title'] != want:
        print(f'MISMATCH {d}: {meta[\"title\"]} != {want}')
        meta['title'] = want
        (Path('kaggle/kernels')/d/'kernel-metadata.json').write_text(json.dumps(meta, indent=2)+'\n', 'utf-8')
        print(f'  fixed')
    else:
        print(f'OK {d}')
"
```

Every line must print `OK`. If any print `MISMATCH`, the script
auto-fixes it. Rerun until every line is `OK`.

## Step 3. Align Kaggle ids with live slugs

```
$env:PYTHONIOENCODING = "utf-8"
kaggle kernels list --user taylorsamarel --page-size 50 --csv > kaggle_live.csv
```

Read the CSV. The `ref` column is the live slug for every kernel
the user already has on Kaggle. For each local kernel directory:

a. If a live slug exists, set `id` in
   `kaggle/kernels/<dir>/kernel-metadata.json` to that exact slug.
b. If no live slug exists (new kernel), compute the title-derived
   slug and set `id` to that. Kaggle derives slugs as:
   `title.lower().replace-nonalnum-with-hyphens.collapse-hyphens.strip-hyphens`.
   For `300: DueCare Adversarial Resistance Against 15 Attack Vectors`
   the derived slug is
   `300-duecare-adversarial-resistance-against-15-attack-vectors`, so
   the full id is
   `taylorsamarel/300-duecare-adversarial-resistance-against-15-attack-vectors`.

Record the decision in `scripts/kaggle_live_slug_map.json`:

```json
{
  "duecare_000_index": {
    "live_slug": null,
    "use_id": "taylorsamarel/000-duecare-index-and-reading-guide"
  },
  "duecare_100_gemma_exploration": {
    "live_slug": "taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts",
    "use_id": "taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts"
  },
  ...
}
```

Apply `use_id` to every `kernel-metadata.json`.

## Step 4. Add keywords, public, competition

For every `kaggle/kernels/<dir>/kernel-metadata.json`:

```python
meta["is_private"] = False
meta["competition_sources"] = ["gemma-4-good-hackathon"]
meta["keywords"] = KEYWORDS_BY_SECTION[section(dir)]
```

Use these keyword sets by section:

```
orientation (000, 010):        ["gemma", "safety", "llm", "trafficking", "tutorial"]
exploration (100, 110, 120):   ["gemma", "safety", "llm", "trafficking", "baseline"]
comparison (200-270):          ["gemma", "llm-comparison", "safety", "evaluation"]
adversarial (300, 310, 320):   ["adversarial", "red-team", "jailbreak", "safety"]
tools (400):                   ["function-calling", "tool-use", "multimodal", "gemma"]
evaluation (410-450):          ["llm-judge", "rubric", "grading", "safety"]
pipeline (500-530):            ["agent", "fine-tuning", "unsloth", "lora"]
results (600, 610):            ["dashboard", "results", "submission"]
```

## Step 5. Build the index notebook (000) with live links

The index is the single most important judge-facing artifact. It
must be live first.

Edit `scripts/build_index_notebook.py` so it generates an index
that contains:

a. A title cell: `# 000: DueCare Index and Reading Guide`.
b. A one-paragraph intro: what DueCare is, who it is for, and the
   one-line mission (on-device Gemma 4 safety judge for migrant-
   worker NGOs).
c. A pip install cell pinning `duecare-llm-core==0.1.0`.
d. A "How to Read" section explaining the numbering:
   - 000-090 Orientation
   - 100-190 Exploration
   - 200-290 Comparison
   - 300-390 Adversarial
   - 400-490 Tools and evaluation
   - 500-590 Pipeline and fine-tuning
   - 600-690 Results and submission
e. A "Start Here" block pointing at the 3 highest-impact notebooks:
   - 100 for the Gemma baseline
   - 300 for adversarial resistance
   - 500 for the 12-agent swarm
f. A full table with columns: Number, Title, Section, Kaggle URL,
   One-Sentence Purpose. Use the canonical titles from step 2. The
   Kaggle URL comes from the `use_id` in
   `scripts/kaggle_live_slug_map.json` formatted as
   `https://www.kaggle.com/code/taylorsamarel/<slug>`.
g. A link to the GitHub repo, the Kaggle writeup, and the video.

Auto-generate the table from
`scripts/notebook_registry.py` + `scripts/kaggle_live_slug_map.json`
so it never drifts from reality. After editing the builder,
rebuild:

```
python scripts/build_index_notebook.py
```

Validate that the generated `kaggle/kernels/duecare_000_index/000_index.ipynb`
and `notebooks/000_index.ipynb` both contain the full 28-row table
with correct URLs.

## Step 6. Dry-run then publish

```
$env:PYTHONIOENCODING = "utf-8"
python scripts/publish_kaggle.py --dry-run push-notebooks
```

Must exit 0 for all 28.

```
python scripts/publish_kaggle.py push-notebooks 2>&1 | tee publish_log.txt
```

For failures:

- 400 Bad Request: `id` does not match live slug AND title-derived
  slug collides. Re-run step 3. Re-push only that kernel:
  `kaggle kernels push -p kaggle/kernels/<dir>`.
- 409 Conflict: wait 60 seconds, retry once.
- 404 Not Found: `id` is wrong. Re-run step 3 with fresh
  `kaggle kernels list` data.
- charmap decode error: set `$env:PYTHONIOENCODING = "utf-8"`
  again, retry.

Priority order for the publish pass:

1. 000 index (must be live so judges have an entry point).
2. 010 quickstart.
3. 100 baseline (Phase 1 anchor).
4. 300 adversarial.
5. 500 agent swarm.
6. 610 submission walkthrough.
7. Everything else.

## Step 7. Verify every URL resolves

Create `scripts/verify_kaggle_urls.py`:

```python
import json
import sys
import urllib.request
from pathlib import Path

errors = []
for meta_path in sorted(Path("kaggle/kernels").glob("*/kernel-metadata.json")):
    meta = json.loads(meta_path.read_text("utf-8"))
    slug = meta["id"].split("/", 1)[1]
    url = f"https://www.kaggle.com/code/taylorsamarel/{slug}"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = f"ERR {e}"
    ok = "OK" if code == 200 else "FAIL"
    print(f"{ok} {code} {meta_path.parent.name} {url}")
    if code != 200:
        errors.append((meta_path.parent.name, url, code))

if errors:
    print(f"\n{len(errors)} of 28 FAILED")
    sys.exit(1)
print(f"\nAll 28 resolve at HTTP 200")
```

Run it. Must print 28 `OK` lines. Any `FAIL` line is a blocker.

## Step 8. Update docs with live URLs

Regenerate from the registry plus the live-slug map:

```
python scripts/generate_notebook_guide.py
python scripts/generate_kaggle_notebook_inventory.py
```

Audit `README.md` for any Kaggle link. Replace any that return
non-200 with the corresponding `use_id` URL.

Update `docs/review/notebook_publish_report.md` to show 28
published, 0 failed.

## Step 9. Rebuild the index one more time

After every URL is live, rebuild the index so its 28-row table
contains all live URLs (not placeholders). Re-push just the index:

```
kaggle kernels push -p kaggle/kernels/duecare_000_index
```

Verify: https://www.kaggle.com/code/taylorsamarel/000-duecare-index-and-reading-guide
returns HTTP 200 and shows the full table.

## Step 10. Commit

```
git add scripts/kaggle_live_slug_map.json scripts/verify_kaggle_urls.py
git add scripts/build_index_notebook.py scripts/notebook_registry.py
git add kaggle/kernels/*/kernel-metadata.json
git add kaggle/kernels/duecare_000_index/000_index.ipynb
git add notebooks/000_index.ipynb
git add README.md docs/notebook_guide.md
git add docs/current_kaggle_notebook_state.md
git add docs/review/notebook_publish_report.md
git commit -m "Standardize titles, publish 28 notebooks, live index URL

- Canonical title format: 'NNN: DueCare <Descriptive>' on all 28.
- Index notebook (000) live with full 28-row table and live URLs.
- All Kaggle ids aligned to live slugs so push updates existing
  kernels and creates new ones deterministically.
- keywords, public visibility, competition source on every kernel.
- verify_kaggle_urls.py confirms HTTP 200 for all 28."
```

## Acceptance checklist (every row must be YES)

```
[ ] All 28 titles match the canonical list (step 2 script prints all OK)
[ ] kaggle kernels list returns >= 28 rows for taylorsamarel
[ ] Every kernel-metadata.json id appears in the live list, OR the id
    equals the title-derived slug for a new kernel
[ ] Every kernel-metadata.json has keywords set
[ ] Every kernel-metadata.json has is_private: false
[ ] Every kernel-metadata.json has competition_sources with gemma-4-good-hackathon
[ ] publish_kaggle.py --dry-run push-notebooks exits 0 with 28 kernels
[ ] publish_kaggle.py push-notebooks reports 28 published, 0 failed
[ ] verify_kaggle_urls.py reports 28 OK, 0 FAIL
[ ] Index notebook URL returns HTTP 200
[ ] Index notebook shows a 28-row table with live URLs
[ ] README.md has zero 404 Kaggle links
[ ] notebook_guide.md has zero 404 Kaggle links
[ ] current_kaggle_notebook_state.md has zero 404 Kaggle links
[ ] notebook_publish_report.md shows 28 published, 0 failed
```

## Why this is the goal

Judges land on Kaggle, search "DueCare", and find an index. The
index links them to 27 other notebooks that tell the story. Every
title starts with `NNN: DueCare` so the suite is visually coherent
in search results. No 404s because every id matches a live slug.
No title drift because the canonical list is enforced by a script.
