#!/usr/bin/env python3
"""Build the 015 Background Literature notebook.

Section 1 (Background and Package Setup) explainer notebook. Gives a
reader the academic and legal grounding that every later evaluation
claim depends on: the ILO forced-labor indicators, the Palermo
Protocol, the US TIP Report framework, the migrant-worker regulatory
corridors (RA 10022, Saudi Labor Law Article 40, Kafala system), and
the AI-safety literature (red-teaming, jailbreak research, LLM-as-judge)
that shapes DueCare's evaluation rubric.

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

FILENAME = "015_background_literature.ipynb"
KERNEL_DIR_NAME = "duecare_015_background_literature"
KERNEL_ID = "taylorsamarel/015-duecare-background-literature"
KERNEL_TITLE = "015: DueCare Background Literature"
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"
KEYWORDS = ["gemma", "safety", "llm", "trafficking", "literature"]


URL_000 = "https://www.kaggle.com/code/taylorsamarel/duecare-000-index"
URL_005 = "https://www.kaggle.com/code/taylorsamarel/duecare-005-glossary"
URL_010 = "https://www.kaggle.com/code/taylorsamarel/010-duecare-quickstart-in-5-minutes"
URL_020 = "https://www.kaggle.com/code/taylorsamarel/020-duecare-current-events"
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
        "The academic, legal, and AI-safety foundations every later evaluation "
        "in the suite assumes a reader knows: ILO forced-labor indicators, the "
        "Palermo Protocol, migrant-worker regulatory corridors, and the LLM-"
        "safety literature that shapes the rubric."
    ),
)


HEADER_TABLE = canonical_header_table(
    inputs_html="Published research and legal citations only. No model loading, no runtime data.",
    outputs_html="Grouped reading list linking each cited source back to the notebook that operationalizes it in the DueCare suite.",
    prerequisites_html=(
        f"Kaggle CPU kernel with internet enabled and the <code>{WHEELS_DATASET}</code> "
        "wheel dataset attached. No GPU, no API keys, no model sources."
    ),
    runtime_html="Under 30 seconds end-to-end. Pure static reading material.",
    pipeline_html=(
        f'Background and Package Setup section, explainer slot. Previous: '
        f'<a href="{URL_010}">010 Quickstart</a>. Next: '
        f'<a href="{URL_020}">020 Current Events</a>. Section close: '
        f'<a href="{URL_099}">099 Conclusion</a>.'
    ),
)


HEADER = f"""# 015: DueCare Background Literature

**Before any model score in the suite is interpretable, a reader needs the academic and legal grounding that defines what the model is being scored against.** This notebook is the reading list: the ILO forced-labor indicators, the Palermo Protocol's trafficking definition, the US TIP Report framework, the migrant-worker regulatory corridors that govern Saudi and Gulf placements, and the AI-safety literature on red-teaming, jailbreak research, and LLM-as-judge evaluation that every later rubric in the DueCare suite quietly imports.

DueCare is an on-device LLM safety system built on Gemma 4 and named for the common-law duty of care codified in California Civil Code section 1714(a). The duty-of-care framing is the legal bridge between the trafficking literature below and the engineering work the rest of the suite does.

{HEADER_TABLE}

### What a reader gets from this page

Five grouped reading lists. Each row names one cited source, a one-line summary, and the DueCare notebook where the claim becomes an operational evaluation. The groups are:

1. **International frameworks** — ILO C029, C105, C181, Palermo Protocol, US TVPA, TIP Report indicators.
2. **Regional regulatory regimes** — RA 8042 (PH), RA 10022 (PH), Saudi Labor Law Article 40, UAE Federal Law No. 6 of 2008, Kuwait Domestic Workers Law, Qatar Law No. 21 of 2015, Kafala system.
3. **AI safety and evaluation** — Red-teaming LLMs, jailbreak literature, LLM-as-judge, constitutional AI, multi-turn escalation detection.
4. **On-device and open-source models** — Gemma 4 technical report, Unsloth fine-tuning, llama.cpp / LiteRT runtimes, GGUF quantization.
5. **NGO and operational context** — Polaris Project reporting, IJM casework, ECPAT reports, POEA / BP2MI hotline operations.

### Reading order

- **Previous step:** [010 Quickstart]({URL_010}) proves the install works.
- **Companion:** [020 Current Events]({URL_020}) grounds the literature in recent public incidents.
- **Section close:** [099 Conclusion]({URL_099}).
- **Back to navigation:** [000 Index]({URL_000}).
- **Vocabulary surface:** [005 Glossary]({URL_005}).
"""


GROUP_1_MD = """---

## 1. International frameworks

Every safety-rubric dimension and every legal citation the LLM-judge scores against originates in this list. The right-hand column names the DueCare notebook that operationalizes the citation.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:28%">Source</th>
      <th style="padding:6px 10px;text-align:left;width:46%">What it establishes</th>
      <th style="padding:6px 10px;text-align:left;width:26%">Operationalized in</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px"><a href="https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C029">ILO C029 (Forced Labour, 1930)</a></td><td style="padding:6px 10px">Definitional foundation for forced labor; every downstream rubric treats violations as non-negotiable harm.</td><td style="padding:6px 10px">100, 410, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:12100:0::NO::P12100_ILO_CODE:C181">ILO C181 (Private Employment Agencies, 1997)</a></td><td style="padding:6px 10px">Article 7: agencies shall not charge workers directly or indirectly. Central to the recruitment-fee abuse detection.</td><td style="padding:6px 10px">100, 400, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.unodc.org/unodc/en/treaties/CTOC/">Palermo Protocol (2000)</a></td><td style="padding:6px 10px">UN Protocol to Prevent, Suppress and Punish Trafficking in Persons. The canonical international definition.</td><td style="padding:6px 10px">100, 190, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.state.gov/trafficking-in-persons-report/">US TIP Report</a></td><td style="padding:6px 10px">Annual Trafficking in Persons Report with 11 forced-labor indicators used as rubric signals.</td><td style="padding:6px 10px">100, 180, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.state.gov/international-and-domestic-law/">US TVPA (Trafficking Victims Protection Act)</a></td><td style="padding:6px 10px">US federal anti-trafficking statute; reference for the severity classification bands in the V3 classifier.</td><td style="padding:6px 10px">270, 460</td></tr>
  </tbody>
</table>
"""


GROUP_2_MD = """---

## 2. Regional regulatory regimes

Trafficking is a corridor problem; most cases cross jurisdictions. The regimes below define the legal obligations the DueCare rubric scores responses against.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:28%">Source</th>
      <th style="padding:6px 10px;text-align:left;width:46%">What it establishes</th>
      <th style="padding:6px 10px;text-align:left;width:26%">Operationalized in</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px"><a href="https://www.officialgazette.gov.ph/1995/06/07/republic-act-no-8042/">RA 8042 (PH, Migrant Workers Act 1995)</a></td><td style="padding:6px 10px">Philippine Migrant Workers and Overseas Filipinos Act. Establishes POEA jurisdiction.</td><td style="padding:6px 10px">400, 410, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.officialgazette.gov.ph/2010/03/10/republic-act-no-10022/">RA 10022 (PH, amending RA 8042, 2010)</a></td><td style="padding:6px 10px">Zero placement fee for household workers; overseas Filipino protection and OWWA welfare framework.</td><td style="padding:6px 10px">400, 410, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.ilo.org/dyn/natlex/docs/ELECTRONIC/39327/104862/F-1287706975/SAU39327.pdf">Saudi Labor Law Article 40</a></td><td style="padding:6px 10px">Employer obligations for foreign workers; passport confiscation prohibitions.</td><td style="padding:6px 10px">180, 400, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.ilo.org/dyn/natlex/natlex4.detail?p_lang=en&p_isn=79981">UAE Federal Law No. 6 of 2008</a></td><td style="padding:6px 10px">UAE labour relations statute; domestic-worker contract protections.</td><td style="padding:6px 10px">180, 400, 460</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.ilo.org/beirut/areasofwork/labour-migration/kafala/lang--en/index.htm">Kafala sponsorship system</a></td><td style="padding:6px 10px">Employer-tied visa regime in GCC states; the structural context for every passport-retention and visa-tied-employment prompt.</td><td style="padding:6px 10px">180, 200, 460</td></tr>
  </tbody>
</table>
"""


GROUP_3_MD = """---

## 3. AI safety and evaluation

The rubric machinery, the red-team generators, the LLM-judge, and the V3 6-band classifier all originate in published AI-safety research. The rows below link each method to its source paper.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:28%">Source</th>
      <th style="padding:6px 10px;text-align:left;width:46%">What it establishes</th>
      <th style="padding:6px 10px;text-align:left;width:26%">Operationalized in</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px"><a href="https://arxiv.org/abs/2202.03286">Red Teaming Language Models with Language Models (Perez et al., 2022)</a></td><td style="padding:6px 10px">Canonical generator-discriminator framing for adversarial prompt synthesis.</td><td style="padding:6px 10px">300, 310, 335</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://arxiv.org/abs/2307.15043">Universal and Transferable Adversarial Attacks on Aligned Language Models (Zou et al., 2023)</a></td><td style="padding:6px 10px">GCG attack framework; foundation for the cross-model jailbreak research band.</td><td style="padding:6px 10px">181, 185, 189</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://arxiv.org/abs/2309.00267">LLM as a Judge (Zheng et al., 2023)</a></td><td style="padding:6px 10px">The canonical LLM-as-judge evaluation methodology; basis for the 6-dimension weighted rubric.</td><td style="padding:6px 10px">140, 410, 430</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://arxiv.org/abs/2212.08073">Constitutional AI (Bai et al., 2022)</a></td><td style="padding:6px 10px">Principle-based refusal training; DueCare's rubric dimensions mirror the constitution-style critique format.</td><td style="padding:6px 10px">410, 440</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://arxiv.org/abs/2406.11717">Refusal Direction in Language Models (Arditi et al., 2024)</a></td><td style="padding:6px 10px">Single-direction refusal ablation; basis for notebook 182's residual-stream visualizer.</td><td style="padding:6px 10px">182, 187</td></tr>
  </tbody>
</table>
"""


GROUP_4_MD = """---

## 4. On-device and open-source models

The entire project depends on open models that a small NGO can actually run. The rows below name the specific model and runtime papers.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:28%">Source</th>
      <th style="padding:6px 10px;text-align:left;width:46%">What it establishes</th>
      <th style="padding:6px 10px;text-align:left;width:26%">Operationalized in</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px"><a href="https://blog.google/technology/developers/gemma-2/">Gemma model family (Google)</a></td><td style="padding:6px 10px">Open-weight Gemma 2/3/4 checkpoints; the E2B and E4B variants DueCare ships against.</td><td style="padding:6px 10px">100, 102, 270</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://unsloth.ai/">Unsloth fine-tuning library</a></td><td style="padding:6px 10px">2x faster LoRA fine-tuning for Gemma / Llama / Qwen; the Phase 3 training backbone.</td><td style="padding:6px 10px">530</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://github.com/ggerganov/llama.cpp">llama.cpp + GGUF quantization</a></td><td style="padding:6px 10px">Desktop-scale on-device inference runtime; Q4_K_M / Q5_K_M quantization formats for the exported artifacts.</td><td style="padding:6px 10px">530, 600, 695</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://ai.google.dev/edge/litert">LiteRT (on-device runtime)</a></td><td style="padding:6px 10px">Mobile-scale runtime for tablets and phones; the target for the Worker-Side Tool deployment mode.</td><td style="padding:6px 10px">670</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://arxiv.org/abs/2106.09685">LoRA: Low-Rank Adaptation (Hu et al., 2021)</a></td><td style="padding:6px 10px">The parameter-efficient fine-tuning framework DueCare's Phase 3 uses under Unsloth.</td><td style="padding:6px 10px">530</td></tr>
  </tbody>
</table>
"""


GROUP_5_MD = """---

## 5. NGO and operational context

The named partners in the deployment story are real organizations doing the work. The rows below link each partner to their public reporting.

<table style="width:100%;border-collapse:collapse;margin:4px 0 8px 0">
  <thead>
    <tr style="background:#f6f8fa;border-bottom:2px solid #d1d5da">
      <th style="padding:6px 10px;text-align:left;width:28%">Source</th>
      <th style="padding:6px 10px;text-align:left;width:46%">What it establishes</th>
      <th style="padding:6px 10px;text-align:left;width:26%">Operationalized in</th>
    </tr>
  </thead>
  <tbody>
    <tr><td style="padding:6px 10px"><a href="https://polarisproject.org/reports/">Polaris Project reports</a></td><td style="padding:6px 10px">US-based anti-trafficking NGO; annual report data grounds the domestic-work and hospitality-sector priors.</td><td style="padding:6px 10px">610, 680</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://www.ijm.org/">International Justice Mission</a></td><td style="padding:6px 10px">Field-level casework across Philippines, India, Thailand, Cambodia; source for corridor-specific patterns.</td><td style="padding:6px 10px">610, 650</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://ecpat.org/">ECPAT International</a></td><td style="padding:6px 10px">Child-protection anti-trafficking network; reference for age-fraud detection in recruitment material.</td><td style="padding:6px 10px">610, 670</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://poea.gov.ph/">POEA (now DMW, Philippines)</a></td><td style="padding:6px 10px">Philippine overseas employment administration; hotline 1343 is the canonical next-step for RA 10022 violations.</td><td style="padding:6px 10px">400, 610, 680</td></tr>
    <tr><td style="padding:6px 10px"><a href="https://bp2mi.go.id/">BP2MI (Indonesia)</a></td><td style="padding:6px 10px">Indonesian Migrant Worker Protection Agency; corridor counterpart to POEA.</td><td style="padding:6px 10px">400, 680</td></tr>
  </tbody>
</table>
"""


SUMMARY = f"""---

## Why this notebook matters

A safety rubric is only as credible as the literature it is grounded in. If an evaluation rubric cites "ILO standards" without naming the specific conventions, no reviewer can audit the claims. By listing every source and linking each to the operationalizing notebook, this page makes the DueCare suite reproducible from the legal and research end, not just the software end.

The suite is still unusual in one respect: most AI-safety benchmarks cite one or two legal sources (typically US TVPA). DueCare names the GCC, Philippine, Indonesian, and international labor regimes explicitly because the people the tool is built for live under those regimes every day.

## Next

- **Continue the section:** [020 Current Events]({URL_020}) grounds the literature above in recent trafficking and AI-safety incidents.
- **Close the section:** [099 Orientation and Setup Conclusion]({URL_099}).
- **Back to navigation (optional):** [000 Index]({URL_000}).
"""


FINAL_PRINT = (
    "print(\n"
    "    'Background literature handoff >>> Continue to 020 Current Events: '\n"
    f"    '{URL_020}'\n"
    "    '. Section close at 099: '\n"
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
        md(GROUP_4_MD),
        md(GROUP_5_MD),
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
