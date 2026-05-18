# Fine-tuning data strategy

This project should treat fine-tuning as a controlled model-improvement loop, not as a place to pour private case files into a model.

## Short answer

Yes, we need sample data for the demo and real training data for A07. The harness can generate much of that data, but harness-generated rows are **silver data** until they pass validation, deduplication, and sensitive-data handling checks.

Use the harness to produce:

1. **SFT rows**: prompt + the best DueCare harness answer as the target.
2. **DPO rows**: prompt + harness-on answer as `chosen` + raw/weak model answer as `rejected`.
3. **Candidate-mining rows**: prompts where the model fails but the harness corrects it.
4. **Release-gate rows**: holdout prompts that are never trained on.

Do not describe this as reinforcement learning unless a future online RL/PPO/GRPO loop actually exists. For the hackathon, the accurate language is **supervised fine-tuning plus preference optimization**.

## What data is allowed

Train on:

- public-source legal, policy, NGO, regulator, and court text,
- synthetic or composite examples,
- anonymized, consented, provenance-tracked examples after redaction,
- harness-distilled safe answers with citations,
- curator-approved factoid and pack-update examples,
- generated graded responses from the prompt-generation notebooks.

Do not train on:

- raw worker case narratives,
- private documents,
- names, phone numbers, emails, addresses, identity numbers, or passport numbers,
- raw chat transcripts from workers or caseworkers,
- evaluation holdout prompts,
- anything whose provenance cannot be reproduced from dataset version + git SHA.

## Minimum row schemas

### SFT JSONL

```json
{
  "id": "sft_demo_platform_text_post_001",
  "messages": [
    {"role": "system", "content": "You are DueCare, a privacy-preserving migrant-worker safety assistant..."},
    {"role": "user", "content": "Synthetic prompt or structured JSON input..."},
    {"role": "assistant", "content": "Grounded safe answer with citations and next-step limits..."}
  ],
  "source": "harness_distilled",
  "provenance": {
    "git_sha": "<sha>",
    "dataset_version": "<version>",
    "pack_versions": ["phl-kwt-domestic@1.7.2"],
    "rubric_grade": "best"
  },
  "privacy_scan": {"pii_found": false}
}
```

### DPO JSONL

```json
{
  "id": "dpo_demo_platform_text_post_001",
  "prompt": "Synthetic prompt or structured JSON input...",
  "chosen": "DueCare harness answer with GREP + RAG + tool grounding...",
  "rejected": "Raw model answer that missed a risk signal or citation...",
  "reason": "chosen cites fee rule and refuses unsafe optimization; rejected treats the post as ordinary hiring copy",
  "provenance": {
    "git_sha": "<sha>",
    "dataset_version": "<version>",
    "raw_model": "gemma4:e4b",
    "harness_mode": "persona+grep+rag+tools"
  },
  "privacy_scan": {"pii_found": false}
}
```

## Best-practice pipeline

1. Select high-priority prompts across the video surfaces: platform moderation, NGO case analysis, worker mobile chat, research graph extraction, and hub vetting loop.
2. Run each prompt through raw Gemma 4 and through DueCare harness-on mode.
3. Store the full prompt, raw answer, harness answer, GREP hits, RAG citations, tool calls, score, grade, latency, and pack versions.
4. Redact and scan every row. Abort on detector-class PII.
5. Deduplicate by normalized prompt and response hash.
6. Split train/validation/test by scenario family so near-duplicates cannot leak into the holdout.
7. Train LoRA with SFT first.
8. Run DPO/preference optimization on chosen/rejected pairs.
9. Re-run the same release gate: safety, citation faithfulness, refusal coverage, cross-domain proof, and no-PII artifact scan.
10. Publish only if the enhanced model beats stock on the held-out gate without weakening safe refusals.

## Demo-specific recommendation

For the video, create a small “recording cache” first:

- six canonical synthetic examples live at `/api/demo/priority-examples`,
- final-cache rows should preserve those IDs,
- warmed runtime outputs replace the fixture responses before screen capture,
- the no-wait page `/demo-recording` displays the cache so the camera never waits for inference.

This gives the video a fast, honest workflow: real examples, real runtime outputs when available, and a static presentation layer for pacing.
