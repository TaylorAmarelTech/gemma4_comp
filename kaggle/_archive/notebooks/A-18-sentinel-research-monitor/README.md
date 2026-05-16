# A-18 — Sentinel / research monitor (search + submit flow)

<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher, 05 Developer / integration partner

## What it does

Submit a public URL or paste text. Gemma 4 + harness decides whether
the content yields new corridor information that should be proposed
as a pack diff. The curator approves or rejects the proposal before
any pack mutation. Mirrors `sentinel.html` + `research-monitor.html`
+ `submit-information.html` from the website.

## Pipeline

1. POST `/api/propose` with `{"source_url": str?, "inline_text": str?, "target_pack": str}`
2. Fetch URL via `urllib.request.urlopen` (timeout 30s, 8KB cap)
   OR use inline text
3. GREP rules fire on the text; count fires
4. Gemma 4 produces structured assessment (relevance / extracted
   facts / rationale)
5. Heuristic relevance score combines GREP fires + assessment length
6. Verdict: approve (>=0.6) / review (>=0.3) / reject (<0.3)
7. Curator decides — if approve, run A-16 pack builder with the new
   inline_text as a document to bump pack version

## Inputs

- **GPU:** T4 (e2b-it default for fast iteration)
- **Internet:** ON (GitHub install + public-URL fetches)
- **No Kaggle Datasets required**

## Outputs

To `/kaggle/working/`:

- `<run_id>_proposals.json` — full session payload + summary
- `<run_id>_proposals.jsonl` — streaming per-proposal rows
- `<run_id>_metadata.json` — config + verdict counts
- `<run_id>_bundle.zip` — manifest + above

Run-ID format: `a18_sentinel_{iso_ts}`.

Per-proposal schema: `diff_id, target_pack, source_url,
source_text_len, grep_rules_fired, relevance_score, harness_verdict
(approve|review|reject), assessment, elapsed_ms, created_at`.

## Where this slot lives

- **Canonical role:** A-18 sentinel / research monitor
- **Folder path:** `kaggle/A-18-sentinel-research-monitor/`
- **Sibling kernels:** A-16 knowledge-pack builder (consumes
  approved diffs)

See `docs/appendix_experiment_ladder.md`.

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A18 appendix — Sentinel / research monitor**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#03 core: Video pitch (in-app slides + presenter remote)](../03-duecare-video-pitch/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- [#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)
- [#A12 appendix: PrivacyRedactor LoRA fine-tune + eval](../A-12-pii-fine-tune-eval/README.md)
- [#A13 appendix: Multimodal document analyzer (Gemma 4 vision)](../A-13-multimodal-document-analyzer/README.md)
- [#A14 appendix: On-device export (LoRA merge -> GGUF + LiteRT)](../A-14-on-device-export/README.md)
- [#A15 appendix: UGC batch moderator (Lane 01 platform safety)](../A-15-ugc-batch-moderator/README.md)
- [#A16 appendix: NGO local-KB / case-file ingestion](../A-16-ngo-local-kb/README.md)
- [#A17 appendix: Knowledge-pack builder + verifier](../A-17-knowledge-pack-builder/README.md)
- **[#A18 appendix: Sentinel / research monitor](../A-18-sentinel-research-monitor/README.md)**
- [#A19 appendix: Multilingual demo (5-language playback)](../A-19-multilingual-demo/README.md)
- [#A20 appendix: Privacy boundary visualization](../A-20-privacy-boundary/README.md)
- [#A21 appendix: Long-context demo (Gemma 4 128K)](../A-21-long-context-demo/README.md)
- [#A22 appendix: Token streaming demo (Gemma 4 SSE)](../A-22-streaming-demo/README.md)
- [#A23 appendix: Coordinator demo (Gemma 4 native function calling)](../A-23-coordinator-demo/README.md)
- [#A24 appendix: Demo replay (zero-inference video kernel)](../A-24-demo-replay/README.md)

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
