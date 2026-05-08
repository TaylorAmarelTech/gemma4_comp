# Licenses & attributions

This file indexes the licenses of every third-party asset, model, and
dataset bundled with the Duecare hackathon submission. It complements
the project's MIT `LICENSE` file (which covers our own source code).

Last refreshed: 2026-05-08 (v0.14.0 inventory below; chat-package v0.13.0).

## Project-authored code

**License:** MIT (see `LICENSE` at repo root).
**Scope:** all `.py` source under `packages/`, `src/`, `scripts/`,
`tests/`, plus the `kaggle/*/kernel.py` orchestration files. The
`docs/`, `_archive/`, and the writeups are MIT unless otherwise noted.

## Project-authored synthetic evidence images

**Path:** `packages/duecare-llm-chat/src/duecare/chat/static/synthetic/`
(bundled into the wheel; ships at `static/synthetic/` in the deployed
chat package).

**License:** **CC0 1.0 Universal** (Public Domain Dedication) — see
<https://creativecommons.org/publicdomain/zero/1.0/>.

**Why CC0:** Creative Commons explicitly recommends CC0 for
algorithmic-template-generated content where copyright authorship is
ambiguous (per the U.S. Copyright Office's 2023 guidance — purely
AI/algorithmically generated content is not copyrightable). CC0
maximises downstream NGO and researcher reuse with no friction.

**Synthetic disclaimer (load-bearing legal notice — preserve in
downstream reuse):**

> All persons, agencies, account numbers, phone numbers, passport
> numbers, signatures, employer names, and case identifiers in these
> images are FICTIONAL. Composite character names ("Maria Composite",
> "Ramesh Composite", "Aisha Placeholder", etc.) and reserved-for-
> fictional-use phone-number prefixes (555/900) make the synthetic
> nature visually unambiguous. Each image carries:
>
>   - A visible "SYNTHETIC — TRAINING USE ONLY" watermark.
>   - PNG `tEXt` chunks with `License`, `Source`, `Comment`, and
>     `ImageKind` fields.
>   - A JSON sidecar (`<image>.json`) with full provenance.
>
> These images are TRAINING / DEMONSTRATION assets for AI
> trafficking-detection research. **They MUST NOT be used as
> evidence in legal, journalistic, or investigative proceedings.**
> Synthetic ID-style images deliberately fail forensic checks
> (incorrect MRZ, broken security features) — using them to bypass
> KYC, customs, or border controls is criminal in most jurisdictions.

**Generator:** `scripts/generate_synthetic_evidence.py` — Pillow-based
templating, deterministic seeds, no neural model or scraped imagery.

## Third-party assets and references

The chat package itself does NOT bundle third-party trafficking-
awareness imagery. The references below are linked / cited only,
either in the prompt text or in `docs/` writeups.

### ILO (International Labour Organization)
**Link:** <https://www.ilo.org/rights-and-permissions>
**License (publications dated 3 May 2023 or later):** **CC BY 4.0** —
free reuse with attribution. Source: ILO open-access policy.
**Attribution format:**
> Source: International Labour Organization (ILO), [title], [year].
> Licensed under CC BY 4.0 (<https://creativecommons.org/licenses/by/4.0/>).

**Photos on Flickr (`flickr.com/photos/ilopictures`):** CC BY-NC-ND
4.0 — non-commercial, no derivatives, attribution required. We do
NOT bundle ILO photos; only cite them.

**Specifically referenced in this project:**
- *ILO 11 Indicators of Forced Labour* (operational manual, 2012).
- *ILO Forced Labour Protocol P029* (2014).
- ILO Conventions C029, C095, C181, C188, C189 (Forced Labour, Wage
  Protection, Private Employment Agencies, Work in Fishing, Domestic
  Workers).

### UNODC (UN Office on Drugs and Crime) — Blue Heart Campaign
**Link:** <https://www.unodc.org/unodc/en/blueheart/tools.html>
**License:** Logo + campaign templates may be used "without
permission" for awareness-raising activities, AS LONG AS uses are
"consistent with the goals, objectives and messages of the campaign."
The branding can only be used as designed (no edits to the logo).
**Attribution required:** "International/UN campaign coordinated by
UNODC" + link to <https://www.unodc.org/blueheart>.
**Bundling:** NOT bundled in this version. Reference-only.

### Polaris Project (US)
**Link:** <https://polarisproject.org/resources/>
**License:** Closed (no public CC license declaration). The project
supports their work via citation, never redistribution.
**Bundling:** NEVER bundle Polaris graphics or the Polaris logo
(registered trademark).

### IJM (International Justice Mission)
**Link:** <https://www.ijm.org/terms-of-use>
**License:** Closed. IJM Terms of Use forbid copying, redistribution,
or derivative works without written authorization.
**Bundling:** NEVER bundle IJM imagery; cite reports only with case
references.
**Specifically referenced:** *IJM "Tied Up" Brief (2023): Domestic
Worker Debt Bondage in Asia* — cited via the RAG corpus by case
identifier; the source PDF lives at the IJM domain.

### ECPAT International
**Link:** <https://www.ecpat.org/>
**License:** Closed campaign assets (gated through `info@dontlookaway.nl`).
The Anti-Trafficking Review (published with GAATW) IS open-access CC.
**Bundling:** Anti-Trafficking Review citations are CC-OK. ECPAT
campaign visuals — link only, do not bundle.

### IOM (International Organization for Migration)
**Link:** <https://medialib.iom.int/en/terms>
**License:** **CC BY-NC-ND 3.0 IGO** — non-commercial, no derivatives,
attribution required. Commercial requests via `publications@iom.int`.
**Bundling:** Not bundled. The chat package wheel is distributed
on PyPI/Kaggle (commercial-adjacent platforms); CC-NC-ND is the wrong
licence shape for that distribution.

### GAATW (Global Alliance Against Traffic in Women)
**Link:** <https://www.gaatw.org/resources/publications>
**License:** Anti-Trafficking Review journal is open-access CC. Other
publications check per-document.
**Bundling:** Not bundled. Cited in writeups.

### Mission for Migrant Workers HK
**Link:** <https://www.migrants.net/>
**License:** No public CC declaration; treat as all-rights-reserved.
**Bundling:** Not bundled. Cited as operational hotline reference.

### HRD Nepal / NHRC Nepal
**Link:** <https://www.nhrcnepal.org/>
**License:** No public CC declaration.
**Bundling:** Not bundled. Cited in corridor-specific guidance.

## Models loaded by the kernel

### `mixedbread-ai/mxbai-rerank-xsmall-v1` (cross-encoder reranker)
**Link:** <https://huggingface.co/mixedbread-ai/mxbai-rerank-xsmall-v1>
**License:** Apache 2.0.
**Bundling:** NOT bundled in the wheel. Lazy-downloaded by
`kernel_helpers/reranker.py` at runtime when `ENABLE_RERANKER=1`.
**Use:** scoring `(query, candidate)` pairs in the chat package's
optional rerank stage.

### `sentence-transformers/all-MiniLM-L6-v2` (dense embedder)
**Link:** <https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2>
**License:** Apache 2.0.
**Bundling:** NOT bundled. Lazy-downloaded by
`kernel_helpers/embedding.py` at runtime when `ENABLE_EMBEDDER=1`.
**Use:** dense embedding for the optional `hybrid_rrf` retrieval mode.

### Gemma 4 family (E2B / E4B / 26B-A4B / 31B variants)
**Link:** <https://huggingface.co/google/gemma-4>
**License:** Gemma Terms of Use (<https://ai.google.dev/gemma/terms>).
**Bundling:** NOT bundled. Loaded by the kernel via `transformers` /
`unsloth` at user choice.
**Use:** primary chat model; multimodal variants (E4B, 31B) handle
the `image_prompts` bucket attachments.

## Python dependencies

The chat package's `pyproject.toml` declares:
- `fastapi>=0.115.0` (MIT)
- `uvicorn>=0.30.0` (BSD-3-Clause)
- `pydantic>=2.9.0` (MIT)

The kernel-side dependencies (loaded transitively via `unsloth`,
`transformers`, `accelerate`, `peft`, etc.) are governed by their
respective licenses; major ones are Apache 2.0 (transformers) and
Apache 2.0 (unsloth).

## Optional Pillow-pulled fonts

The synthetic-evidence generator falls back to system fonts (DejaVu
on Linux, Arial on Windows, Helvetica on macOS). It does NOT bundle
any font files. License of the rendered text falls under the system
font's license (DejaVu: Bitstream/Public-Domain-equivalent; Arial:
Microsoft proprietary; Helvetica: Linotype). For wheel distribution,
no font files are touched — only their glyph rasters are embedded
in the rendered PNG output, which is treated as image data.

## How to add a new third-party asset

1. Verify the license at the source. Get the version, retrieval
   date, and exact attribution string.
2. If the license forbids redistribution: do NOT bundle. Reference
   via URL in `docs/` only.
3. If the license requires attribution: add the asset to
   `static/synthetic/external/` (or similar) with a sidecar JSON
   declaring `license`, `source`, `attribution`, `retrieved_at`.
4. Append a section to this file under "Third-party assets".

## Risks

This project bundles synthetic trafficking-evidence imagery. Specific
risks we have mitigated:

1. **KYC / passport-fraud reuse.** Synthetic ID-style images are
   deliberately broken (incorrect layout, fictional MRZ, watermark).
   Bundled disclaimer warns against use in border / customs contexts.
2. **Trauma.** UI surfaces a `📎 Attach an image` banner with
   image-hint text BEFORE the image renders, so users with lived
   trauma can opt out.
3. **Training-data contamination.** A `robots.txt` / `ai.txt` at repo
   root will exclude `static/synthetic/` from major AI crawlers
   (GPTBot, ClaudeBot, Google-Extended) — see next version.
4. **Hallucinated case-as-real.** The chat package's persona prefix
   includes a SYNTHETIC reminder when the prompt body references
   composite characters; the model is instructed not to assert
   composite cases as real.
5. **Misattribution of NGO branding.** No real NGO logos appear in
   any synthetic asset; agency names use composite "(composite)"
   suffix tags.

## Reporting a license issue

If you find a license violation in this project — either a missing
attribution or a mistakenly bundled all-rights-reserved asset — open
a GitHub issue at <https://github.com/TaylorAmarelTech/gemma4_comp/issues>
or email the project author. We treat license issues as P0 fixes.
