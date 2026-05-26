# Project Overview - DueCare Gemma 4 Good Submission

## Competition Context

- **Hackathon:** Gemma 4 Good Hackathon (Kaggle)
- **URL:** https://www.kaggle.com/competitions/gemma-4-good-hackathon
- **Window:** 2026-04-02 through 2026-05-18
- **Primary track:** Impact Track -> Safety & Trust
- **Special Technology evidence:** Unsloth fine-tuning and LiteRT/on-device
  Android work through the sibling `duecare-journey-android` repository.
- **Judging emphasis:** real-world impact, clear video storytelling, and
  technical depth with a working demo and public code.

## Submission Title

**DueCare: A Gemma 4 Safety Ecosystem for Migrant-Worker Protection**

**Subtitle:** A self-hostable multi-faceted Gemma 4 implementation for content moderation,
case analysis, worker support, research, and anonymized knowledge sharing.

## Problem

Migrant-worker exploitation is a high-stakes domain where generic LLMs fail in
predictable ways: wrong law, wrong corridor fee cap, vague referrals, unsafe
privacy handling, or operational advice for fee-shifting schemes. The users
closest to the harm are also the least able to rely on cloud-only AI:
frontline NGOs, labor regulators, platform safety teams, researchers, and
workers using monitored or low-connectivity devices.

## Solution

DueCare wraps Gemma 4 in a local, inspectable safety substrate:

1. **Content moderation** - recruitment ads, listings, and messages are
   classified against trafficking indicators and cited policy rules.
2. **Case analysis** - bounded case bundles become people, payments, dates,
   journey stages, typed graph edges, and reviewable evidence rows.
3. **Worker information access** - short questions receive plain-language
   rights guidance, safe reporting paths, contacts, and evidence-preservation
   steps.
4. **Research and enforcement** - repeated patterns can be queried across
   reviewed graphs and exported reports.
5. **Anonymized knowledge sharing** - reviewed facts can become redacted knowledge
   objects that improve local packs without centralizing raw case data.

Gemma 4 is the engine under those lanes, not a separate product lane. The
system uses deterministic GREP rules, RAG packs, tool calls, graph extraction,
sensitive-data handling, and combined rule + LLM grading around the model.

## Why Gemma 4

- **Local runtime:** E2B/E4B-class models are practical on Kaggle T4 and
  worker/NGO hardware.
- **Native tool use:** the harness can route corridor lookups, contact
  resolution, statute validation, and edge extraction through structured
  calls.
- **Multimodal path:** Bulk File Review queues scans, receipts, images, and
  PDFs for local vision-assisted extraction.
- **Fine-tuning:** A-00 trains and evaluates LoRA adapters through Unsloth.
- **Edge path:** the sibling Android APK carries the harness bundle and
  LiteRT/on-device deployment story.

## Deliverables

1. **Kaggle writeup:** `docs/writeup_draft.md` (1494 / 1500 words).
2. **Video script:** `docs/video_script.md` (current 23-slide deck flow).
3. **Public code repository:** this GitHub repo.
4. **Live demo:** `kaggle/02-live-demo/kernel.py` prints a Cloudflare URL;
   open `/start`, `/slides`, and `/wb-static/process.html`.
5. **Evaluation:** `kaggle/A-00-omni-experiment-workbench/` produces the
   stock / harnessed / fine-tuned / fine-tuned+harness matrix.
6. **Public hub:** `apps/duecare-ai.com/` documents the broader ecosystem,
   pack registry, and anonymized signal path.

## Current Evidence

The 2026-05-18 A-00 smoke matrix (`e2b-full-train-eval`, combined rule +
LLM judge) recorded:

| Arm | Score |
|---|---:|
| Stock Gemma 4 2B | 29.5% |
| Stock + chat-offline harness | 35.6% |
| Fine-tuned | 26.4% |
| Fine-tuned + harness | 41.2% |

The result supports the submission thesis: grounding and reviewable safety
infrastructure matter at least as much as raw model response style.

## Reviewer Path

Start with `docs/FOR_KAGGLE_JUDGES.md`, then run the live-demo kernel and
open `/start`. The recording deck is self-contained, and the Bulk File Review
sample demonstrates document upload -> processing -> Gemma edge creation ->
review gate -> graph chat.
