#!/usr/bin/env python3
"""Build the 020 Current Events notebook.

Section 1 (Background and Package Setup) grounding notebook that links
the academic framing in 015 to recent public trafficking cases and AI-
safety incidents. Establishes why DueCare matters right now, not just
in principle.

CPU-only, no model inference, no API calls. Pure reading material with
cited links.
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_notebook import canonical_header_table, canonical_hero_code
from notebook_hardening_utils import harden_notebook


ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
KAGGLE_KERNELS = ROOT / "kaggle" / "kernels"

FILENAME = "020_current_events.ipynb"
KERNEL_DIR_NAME = "duecare_020_current_events"
KERNEL_ID = "taylorsamarel/020-duecare-current-events"
KERNEL_TITLE = "020: DueCare Current Events"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "safety", "llm", "trafficking", "current-events"]


URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_005 = "https://www.kaggle.com/code/taylorsamarel/duecare-005-glossary"
URL_010 = "https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes"
URL_015 = "https://www.kaggle.com/code/taylorsamarel/015-duecare-background-literature"
URL_099 = "https://www.kaggle.com/code/taylorsamarel/099-duecare-orientation-setup-conclusion"


def md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


def code(s: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": s.splitlines(keepends=True),
    }


NB_METADATA = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
    "kaggle": {"accelerator": "none", "isInternetEnabled": True},
}


HERO_CODE = canonical_hero_code(
    title=KERNEL_TITLE,
    kicker="DueCare - Background and Package Setup",
    tagline=(
        "Recent public trafficking cases and AI-safety incidents that ground "
        "the abstract rubric in today's news. Each item links to reporting "
        "and names the DueCare notebook that would detect or mitigate it."
    ),
)


HEADER_TABLE = canonical_header_table(
    inputs_html="Public news reporting and public court filings only. No PII. No proprietary sources.",
    outputs_html="Three grouped tables: trafficking cases, AI-safety incidents, and regulatory / policy changes; each row linked to the DueCare notebook that operationalizes a response.",
    prerequisites_html=(
        f"Kaggle CPU kernel with internet enabled and the <code>{WHEELS_DATASET}</code> "
        "wheel dataset attached. No GPU, no API keys, no model sources."
    ),
    runtime_html="Under 30 seconds end-to-end. Pure static reading material.",
    pipeline_html=(
        f'Background and Package Setup section, grounding slot. Previous: '
        f'<a href="{URL_015}">015 Background Literature</a>. Next: '
        f'<a href="{URL_099}">099 Conclusion</a>.'
    ),
)


HEADER = f"""# 020: DueCare Current Events

**Abstract rubrics are easy to ignore. Recent cases are harder.** This notebook grounds the [015 Background Literature]({URL_015}) reading list in public incidents from the last 24 months: specific trafficking cases, specific AI-safety failures, and specific regulatory actions. Every row names the DueCare notebook that would measure, detect, or mitigate the corresponding class of harm if that model were asked about the same scenario.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). This page exists because a judge or adopter reading the suite should see the connection between the rubric we score responses against and the real-world events that rubric was designed for.

{HEADER_TABLE}

### What a reader gets from this page

Three grouped tables:

1. **Trafficking cases in public reporting** — recent exploitation and recruitment-fee abuse cases where LLM-based safety guidance would have mattered.
2. **AI-safety incidents** — public jailbreaks, hallucinated legal citations, and moderation failures that map directly to DueCare's evaluation dimensions.
3. **Regulatory and policy changes** — recent laws and enforcement actions across the migrant-worker corridors the suite targets.

Each row is cited to a public source. No PII appears anywhere on this page; composite descriptions are labeled as such.

### Reading order

- **Previous step:** [015 Background Literature]({URL_015}) gives the academic framing this page grounds in reality.
- **Section close:** [099 Orientation and Setup Conclusion]({URL_099}).
- **Back to navigation:** [000 Index]({URL_000}).
- **Vocabulary surface:** [005 Glossary]({URL_005}).
"""


GROUP_1_MD = """---

## 1. Trafficking cases in public reporting

Each row names a publicly reported case pattern, its canonical source, and the DueCare notebook that would score a model's response to a similar scenario.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:22%">Case pattern</th>
      <th style="padding:6px 10px;text-align:left;width:52%">Summary</th>
      <th style="padding:6px 10px;text-align:left;width:26%">DueCare analog</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px">Recruitment-fee abuse (PH-GCC corridor)</td><td style="padding:6px 10px">Multiple <a href="https://www.poea.gov.ph/news/recruitment_violations.html">POEA enforcement actions</a> against agencies charging prohibited placement fees to domestic workers bound for the Gulf. The zero-fee policy from RA 10022 is the legal benchmark.</td><td style="padding:6px 10px">100, 400, 410, 460</td></tr>
    <tr><td style="padding:6px 10px">Kafala-system passport retention</td><td style="padding:6px 10px">ILO and Human Rights Watch have <a href="https://www.hrw.org/topic/womens-rights/kafala-system">repeatedly documented</a> employer-tied visa regimes under which passports are held as deposits; forced-labor indicator under ILO C029.</td><td style="padding:6px 10px">180, 200, 460</td></tr>
    <tr><td style="padding:6px 10px">Sea-based fishing exploitation (Thailand, Indonesia)</td><td style="padding:6px 10px"><a href="https://ejfoundation.org/reports">EJF Foundation reports</a> on coercive confinement at sea, including TH-to-OCN corridor cases from the Trafficking in the Thai Fishing Industry series.</td><td style="padding:6px 10px">100, 270, 460</td></tr>
    <tr><td style="padding:6px 10px">Platform-facilitated recruitment fraud</td><td style="padding:6px 10px">Recruitment-scam reports on social platforms; UNODC <a href="https://www.unodc.org/roseap/en/what-we-do/toip/trafficking-in-persons-online.html">Trafficking in Persons Online</a> identifies the pattern as rising year over year.</td><td style="padding:6px 10px">300, 310, 335</td></tr>
    <tr><td style="padding:6px 10px">Domestic-worker abuse (GCC, PH-HK)</td><td style="padding:6px 10px"><a href="https://www.hrw.org/report/2010/07/14/slow-reform/protection-migrant-domestic-workers-asia-and-middle-east">Human Rights Watch</a> multi-country study on protection gaps for migrant domestic workers.</td><td style="padding:6px 10px">180, 400, 410</td></tr>
  </tbody>
</table>
"""


GROUP_2_MD = """---

## 2. AI-safety incidents

Public incidents where LLM safety failures mapped to the specific rubric dimensions DueCare scores.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:22%">Incident pattern</th>
      <th style="padding:6px 10px;text-align:left;width:52%">Summary</th>
      <th style="padding:6px 10px;text-align:left;width:26%">DueCare rubric dimension</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px">Hallucinated legal citations</td><td style="padding:6px 10px">Multiple <a href="https://www.courtlistener.com/opinion/9555906/mata-v-avianca-inc/">Mata v. Avianca-style sanctions</a> against lawyers who submitted LLM-hallucinated case citations. Direct analog to the fabricated ILO convention and statute problem DueCare's 460 Citation Verifier measures.</td><td style="padding:6px 10px">legal_accuracy (140, 410, 460)</td></tr>
    <tr><td style="padding:6px 10px">Jailbreak research (GCG, adversarial suffixes)</td><td style="padding:6px 10px">Systematic <a href="https://arxiv.org/abs/2307.15043">GCG</a> and <a href="https://arxiv.org/abs/2404.01318">LLM-Attacks-style</a> research showing aligned models bypassed by optimized suffixes; DueCare's 181-189 band is the defensive-research parallel.</td><td style="padding:6px 10px">refusal_quality (181-189)</td></tr>
    <tr><td style="padding:6px 10px">Refusal brittleness (single-direction)</td><td style="padding:6px 10px">Arditi et al. (2024) showed refusal collapses to a single residual-stream direction; ablation bypasses it. The 182 Refusal Direction Visualizer reproduces the finding.</td><td style="padding:6px 10px">refusal_quality (182, 187)</td></tr>
    <tr><td style="padding:6px 10px">Over-refusal on safety prompts</td><td style="padding:6px 10px">Well-intentioned refusals that leave the victim with no next step are measured by the actionability dimension; a refusal without a hotline number is a failure mode, not a success.</td><td style="padding:6px 10px">actionability (100, 410)</td></tr>
    <tr><td style="padding:6px 10px">Multi-turn escalation</td><td style="padding:6px 10px">Policy drift across long conversations; the 420 Conversation Testing notebook measures this specifically for trafficking scenarios.</td><td style="padding:6px 10px">completeness (420)</td></tr>
  </tbody>
</table>
"""


GROUP_3_MD = """---

## 3. Regulatory and policy changes

Recent legal developments across the corridors the suite targets.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:22%">Change</th>
      <th style="padding:6px 10px;text-align:left;width:52%">Summary</th>
      <th style="padding:6px 10px;text-align:left;width:26%">Affects</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px">DMW replaces POEA (Philippines, 2022)</td><td style="padding:6px 10px">The <a href="https://dmw.gov.ph/">Department of Migrant Workers</a> replaced POEA in 2022 as the lead overseas-employment agency; hotline 1348 is now the primary contact alongside legacy POEA 1343.</td><td style="padding:6px 10px">Hotline lookup tables (400, 680)</td></tr>
    <tr><td style="padding:6px 10px">EU AI Act (2024)</td><td style="padding:6px 10px">The <a href="https://artificialintelligenceact.eu/">EU AI Act</a> Article 5 prohibits certain high-risk uses of AI; the transparency and evaluation obligations in Annex III directly shape safety-harness requirements.</td><td style="padding:6px 10px">610 Submission Walkthrough framing</td></tr>
    <tr><td style="padding:6px 10px">California SB 1001 (bot disclosure)</td><td style="padding:6px 10px">California Business and Professions Code section 17940 requires disclosure when bots communicate with consumers; affects worker-facing deployments of the 670 Private Client-Side Checker.</td><td style="padding:6px 10px">670 Private Client-Side Checker</td></tr>
    <tr><td style="padding:6px 10px">FATF Recommendations update</td><td style="padding:6px 10px">FATF <a href="https://www.fatf-gafi.org/en/publications/Fatfrecommendations.html">40 Recommendations</a> govern money-laundering typologies relevant to the financial_crime domain pack; periodic updates change typology codes.</td><td style="padding:6px 10px">200 Cross-Domain Proof, financial_crime pack</td></tr>
    <tr><td style="padding:6px 10px">US TIP Report tier changes</td><td style="padding:6px 10px">Annual tier-ranking changes by the US TIP Report shift enforcement priorities country by country; the corridor priors in the prompt corpus track these changes.</td><td style="padding:6px 10px">105, 110 prompt selection</td></tr>
  </tbody>
</table>
"""


SUMMARY = f"""---

## Why this notebook matters

The suite's rubric and the adversarial test bands (181-189, 300, 460) exist because real cases and real failures kept happening in the period this project was built. Naming the cases in a single notebook makes the motivation auditable: a reader can click each row and read the public source, then open the linked DueCare notebook and see how the evaluation framework responds to the same pattern.

Every case on this page is drawn from public reporting. Wherever a source quoted an individual worker's name, that name has been generalized to a composite pattern; the project's [CLAUDE.md safety gate](https://github.com/TaylorAmarelTech/gemma4_comp/blob/main/CLAUDE.md) bans raw PII in committed files.

## Next

- **Close the section:** [099 Orientation and Setup Conclusion]({URL_099}) recaps the four-notebook setup (Index, Glossary, Quickstart, Background, Current Events) and hands off to the evaluation sections that follow.
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""


FINAL_PRINT = (
    "print(\n"
    "    'Current events handoff >>> Section closes at 099: '\n"
    f"    '{URL_099}'\n"
    ")\n"
)


def build() -> None:
    cells = [
        code(HERO_CODE),
        md(HEADER),
        md(GROUP_1_MD),
        md(GROUP_2_MD),
        md(GROUP_3_MD),
        md(SUMMARY),
        code(FINAL_PRINT),
    ]

    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": NB_METADATA,
        "cells": cells,
    }
    nb = harden_notebook(nb, filename=FILENAME, requires_gpu=False)

    NB_DIR.mkdir(parents=True, exist_ok=True)
    KAGGLE_KERNELS.mkdir(parents=True, exist_ok=True)

    nb_path = NB_DIR / FILENAME
    nb_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")

    kernel_dir = KAGGLE_KERNELS / KERNEL_DIR_NAME
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / FILENAME).write_text(json.dumps(nb, indent=1), encoding="utf-8")

    meta = {
        "id": KERNEL_ID,
        "title": KERNEL_TITLE,
        "code_file": FILENAME,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [WHEELS_DATASET],
        "competition_sources": ["gemma-4-good-hackathon"],
        "kernel_sources": [],
        "keywords": KEYWORDS,
    }
    (kernel_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    code_count = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    md_count = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
    print(f"Wrote {nb_path} ({code_count} code + {md_count} md cells)")


if __name__ == "__main__":
    build()
