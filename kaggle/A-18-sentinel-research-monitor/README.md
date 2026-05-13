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
