#!/usr/bin/env python3
"""
copy_reference.py - Copy reference material for the Gemma 4 hackathon project.

Copies selected items from the trafficking benchmark source folder into a
_reference folder inside the gemma4_comp project, then writes REFERENCE_INDEX.md
documenting URLs and context from the planning session.

Non-destructive by default: does not delete anything from the source folder.
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

SOURCE = Path(r"C:\Users\amare\OneDrive\Documents\Migrant_Worker_LLM_Test_Benchmark_Trafficking_Bondage_Etc")
DEST   = Path(r"C:\Users\amare\OneDrive\Documents\gemma4_comp\_reference")

# "light"  : top-level files only (~200 KB)
# "medium" : top-level files + most subfolders, EXCLUDES 5.1 GB framework (~300 MB total)
# "full"   : everything except junk (5.3 GB+, slow)
SCOPE = "medium"

# Also delete the 8.45 GB 'nul' file from source after copying? Default False.
DELETE_NUL_AFTER_COPY = False

# ============================================================================
# IMPLEMENTATION
# ============================================================================

TOP_LEVEL_EXCLUDE = {"nul", ".git"}
HEAVY_FOLDERS = {"llm-safety-framework-public"}
NESTED_EXCLUDE = {".git", "__pycache__", "nul", ".pytest_cache", ".mypy_cache"}


def ignore_nested(src, names):
    return [n for n in names if n in NESTED_EXCLUDE]


def should_copy_top_level(name: str, is_dir: bool) -> bool:
    if name in TOP_LEVEL_EXCLUDE:
        return False
    if SCOPE == "light" and is_dir:
        return False
    if SCOPE == "medium" and is_dir and name in HEAVY_FOLDERS:
        return False
    return True


def copy_one(src_path: Path, dest_path: Path) -> None:
    if src_path.is_dir():
        shutil.copytree(
            src_path,
            dest_path,
            dirs_exist_ok=True,
            symlinks=False,
            ignore=ignore_nested,
            ignore_dangling_symlinks=True,
        )
    else:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: Source does not exist: {SOURCE}", file=sys.stderr)
        return 1

    DEST.mkdir(parents=True, exist_ok=True)

    print(f"Source : {SOURCE}")
    print(f"Dest   : {DEST}")
    print(f"Scope  : {SCOPE}")
    print(f"Started: {datetime.now().isoformat(timespec='seconds')}")
    print("-" * 60)

    copied, skipped, errors = [], [], []

    for item in sorted(SOURCE.iterdir()):
        is_dir = item.is_dir()
        label = item.name + ("/" if is_dir else "")
        if not should_copy_top_level(item.name, is_dir):
            skipped.append(label)
            continue

        print(f"COPY  {label}", flush=True)
        try:
            copy_one(item, DEST / item.name)
            copied.append(label)
        except Exception as e:
            print(f"  FAIL: {e}", flush=True)
            errors.append((label, str(e)))

    print("-" * 60)
    print(f"Copied : {len(copied)}")
    print(f"Skipped: {len(skipped)}  ->  {', '.join(skipped) if skipped else '(none)'}")
    if errors:
        print(f"Errors : {len(errors)}")
        for name, err in errors:
            print(f"  - {name}: {err}")

    write_reference_index(copied, skipped, errors)

    if DELETE_NUL_AFTER_COPY:
        nul_path = SOURCE / "nul"
        if nul_path.exists():
            try:
                nul_path.unlink()
                print(f"Deleted junk file: {nul_path}")
            except Exception as e:
                print(f"Failed to delete {nul_path}: {e}", file=sys.stderr)

    print(f"Done   : {datetime.now().isoformat(timespec='seconds')}")
    return 0 if not errors else 2


def write_reference_index(copied, skipped, errors):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    copied_lines  = "\n".join(f"- `{x}`" for x in copied)  or "- (none)"
    skipped_lines = "\n".join(f"- `{x}`" for x in skipped) or "- (none)"
    error_lines   = "\n".join(f"- `{n}`: {e}" for n, e in errors) or "- (none)"

    content = f"""# Reference Index - Gemma 4 Good Hackathon

Generated: {now}
Source: `{SOURCE}`
Scope:  `{SCOPE}`

## Purpose
Reference material gathered for the **Gemma 4 Good Hackathon** submission on
anti-trafficking / platform-facilitated abuse. Supports scoping, benchmark
design, and writeup drafting.

## Copied items
{copied_lines}

## Skipped at top level
{skipped_lines}

## Errors
{error_lines}

## Key URLs (from prior planning session)

### Hackathon
- Gemma 4 Good Hackathon (Kaggle):
  https://www.kaggle.com/competitions/gemma-4-good-hackathon
  - Runs 2026-04-02 through 2026-05-18
  - Prize pool: $200K
    - Main Track $100K (1st $50K / 2nd $25K / 3rd $15K / 4th $10K)
    - Impact Track $50K ($10K each: Health & Sciences, Global Resilience,
      Education, Digital Equity, Safety & Trust)
    - Special Technology Track $50K ($10K each: Cactus, LiteRT, llama.cpp,
      Ollama, Unsloth)
  - Submission: <=1,500-word writeup, <=3-min public YouTube video, public
    code repo, live public demo
  - Judging: Impact & Vision (40) + Video Pitch & Storytelling (30) +
    Technical Depth & Execution (30)

### Motivation source
- NPR - Meta/YouTube social media trial verdict (2026-03-25):
  https://www.npr.org/2026/03/25/nx-s1-5746125/meta-youtube-social-media-trial-verdict
  (WebFetch timed out during session - verify contents manually)

### Related prior work on Kaggle
- "LLM Complicity in Modern Slavery: Native Blind Spots to Amplified Exploitation"
  (writeup, OpenAI gpt-oss-20b Red-Teaming Challenge):
  https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind
- "LLM Complicity in Modern Slavery: Draft Notebook" (taylorsamarel):
  https://www.kaggle.com/code/taylorsamarel/llm-complicity-in-modern-slavery-draft-ntbk
- "Red Teaming Challenge - STARTER NOTEBOOK" (taylorsamarel):
  https://www.kaggle.com/code/taylorsamarel/red-teaming-challenge-starter-notebook
- "V2 Red Teaming Challenge - STARTER NOTEBOOK" (taylorsamarel):
  https://www.kaggle.com/code/taylorsamarel/v2-red-teaming-challenge-starter-notebook
- Parent competition:
  https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming

### Access notes
Kaggle pages are JS-rendered; WebFetch only returns the HTML `<head>`.
The originally-provided slug `llms-support-human-trafficking` returned 404 and
is likely incorrect - the probable correct reference is
`llm-complicity-in-modern-slavery-draft-ntbk` by the same author.

To retrieve real notebook content, use the Kaggle CLI (already installed,
v2.0.1):

  1. https://www.kaggle.com/settings -> "Create New Token"
  2. Move kaggle.json to: C:\\Users\\amare\\.kaggle\\kaggle.json
  3. Run:
     kaggle kernels list --user taylorsamarel
     kaggle kernels pull taylorsamarel/llm-complicity-in-modern-slavery-draft-ntbk

## Harness / benchmark context
Top-level documents cover these sectors of the migrant-worker / trafficking
LLM benchmark:

- Education sector (seed, examples, manifest, completion report)
- Fishing / maritime (expanded summary)
- Forced begging / trafficking (creation summary)
- Free trade zone exploitation (creation + implementation summaries)
- Whistleblower retaliation (seed module spec + summary)
- Overall `ARCHITECTURE_PLAN.md`
- Source-level `CLAUDE.md`
- `reference_publication.txt`

Subdirectories (presence depends on SCOPE):
- `trafficking_llm_benchmark/` - core benchmark code (analyze_results.py,
  api_server.py, api_server_ml.py, augment_prompts_migrant_worker.py,
  automated_consolidation.py, consolidated results JSON)
- `trafficking-llm-benchmark-gitlab/` - GitLab mirror (~122 MB)
- `llm-safety-framework-public/` - full framework (5.1 GB; **excluded at
  scope=medium**; includes src/, data/, exports/, reports/, Docker)

## Housekeeping note
The source folder contains a file named `nul` of ~8.45 GB consisting entirely
of null bytes - an accidental `> nul` bash redirect artifact (Windows CMD
treats `nul` as the null device; bash creates a real file). Safe to delete.
Set `DELETE_NUL_AFTER_COPY = True` at the top of this script and re-run to
remove it.

## Session memory
`C:\\Users\\amare\\.claude\\projects\\C--Users-amare-OneDrive-Documents-gemma4-comp\\memory\\`
- `MEMORY.md` - index
- `project_gemma4_hackathon.md` - project context, deadline, strategy,
  leading concept, pending questions
"""

    index_path = DEST / "REFERENCE_INDEX.md"
    index_path.write_text(content, encoding="utf-8")
    print(f"Wrote  : {index_path}")


if __name__ == "__main__":
    sys.exit(main())
