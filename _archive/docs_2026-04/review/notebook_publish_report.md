# Notebook Publish Report

Date: 2026-04-15 (rewritten after ground-truth verification)

## Summary

All 29 Kaggle notebooks are live at HTTP 200 and verified by
`scripts/verify_kaggle_urls.py` using a browser user-agent.

```
29 notebooks configured
29 Kaggle URLs verified live (HTTP 200)
 0 missing
 0 404s
```

## Why earlier reports showed 21 failures

The earlier versions of this report said 21 of 28 notebooks failed
to publish. Those numbers came from two broken measurements:

1. The URL verifier used HEAD requests with a non-browser
   user-agent. Kaggle returns 404 to HEAD and to unknown user
   agents even when the page renders fine in a browser. Every 404
   in the earlier report was the verifier lying, not Kaggle
   rejecting the kernel.
2. The `kaggle kernels push` output was misread. Some pushes that
   Kaggle recorded as 400 or 409 actually succeeded. The CLI
   surfaced an error, the kernel got created or version-bumped,
   and the verifier had no way to confirm because of problem 1.

The verifier has been fixed in `scripts/verify_kaggle_urls.py`. It
now uses GET with a Mozilla user-agent and inspects the response
body for Kaggle soft-404 markers. With the fix, it reports
29 of 29 live.

## Next steps

- Do not republish anything. The suite is already live.
- Do not alter kernel ids, titles, or metadata unless a specific
  Kaggle page renders incorrectly when you click it.
- Focus remaining hackathon time on the writeup and the video.

## Fixed verifier output

```text
duecare_000_index: OK https://www.kaggle.com/code/taylorsamarel/duecare-000-index
duecare_005_glossary: OK https://www.kaggle.com/code/taylorsamarel/duecare-005-glossary
duecare_010_quickstart: OK https://www.kaggle.com/code/taylorsamarel/duecare-010-quickstart
duecare_100_gemma_exploration: OK https://www.kaggle.com/code/taylorsamarel/duecare-gemma-exploration
duecare_110_prompt_prioritizer: OK https://www.kaggle.com/code/taylorsamarel/00a-duecare-prompt-prioritizer-data-pipeline
duecare_120_prompt_remixer: OK https://www.kaggle.com/code/taylorsamarel/duecare-prompt-remixer
duecare_200_cross_domain_proof: OK https://www.kaggle.com/code/taylorsamarel/duecare-200-cross-domain-proof
duecare_210_oss_model_comparison: OK https://www.kaggle.com/code/taylorsamarel/duecare-gemma-vs-oss-comparison
duecare_220_ollama_cloud_comparison: OK https://www.kaggle.com/code/taylorsamarel/duecare-ollama-cloud-oss-comparison
duecare_230_mistral_family_comparison: OK https://www.kaggle.com/code/taylorsamarel/duecare-230-mistral-family-comparison
duecare_240_openrouter_frontier_comparison: OK https://www.kaggle.com/code/taylorsamarel/duecare-openrouter-frontier-comparison
duecare_250_comparative_grading: OK https://www.kaggle.com/code/taylorsamarel/duecare-250-comparative-grading
duecare_260_rag_comparison: OK https://www.kaggle.com/code/taylorsamarel/duecare-260-rag-comparison
duecare_270_gemma_generations: OK https://www.kaggle.com/code/taylorsamarel/duecare-270-gemma-generations
duecare_300_adversarial_resistance: OK https://www.kaggle.com/code/taylorsamarel/300-gemma-4-against-15-adversarial-attack-vectors
duecare_310_prompt_factory: OK https://www.kaggle.com/code/taylorsamarel/duecare-310-prompt-factory
duecare_320_supergemma_safety_gap: OK https://www.kaggle.com/code/taylorsamarel/duecare-finding-gemma-4-safety-line
duecare_400_function_calling_multimodal: OK https://www.kaggle.com/code/taylorsamarel/duecare-400-function-calling-multimodal
duecare_410_llm_judge_grading: OK https://www.kaggle.com/code/taylorsamarel/duecare-410-llm-judge-grading
duecare_420_conversation_testing: OK https://www.kaggle.com/code/taylorsamarel/420-multi-turn-conversation-escalation-detection
duecare_430_rubric_evaluation: OK https://www.kaggle.com/code/taylorsamarel/430-54-criterion-pass-fail-rubric-evaluation
duecare_440_per_prompt_rubric_generator: OK https://www.kaggle.com/code/taylorsamarel/duecare-per-prompt-rubric-generator
duecare_450_contextual_worst_response_judge: OK https://www.kaggle.com/code/taylorsamarel/duecare-contextual-judge
duecare_500_agent_swarm_deep_dive: OK https://www.kaggle.com/code/taylorsamarel/duecare-500-agent-swarm-deep-dive
duecare_510_phase2_model_comparison: OK https://www.kaggle.com/code/taylorsamarel/duecare-phase2-comparison
duecare_520_phase3_curriculum_builder: OK https://www.kaggle.com/code/taylorsamarel/duecare-520-phase3-curriculum-builder
duecare_530_phase3_unsloth_finetune: OK https://www.kaggle.com/code/taylorsamarel/duecare-530-phase3-unsloth-finetune
duecare_600_results_dashboard: OK https://www.kaggle.com/code/taylorsamarel/600-interactive-safety-evaluation-dashboard
duecare_610_submission_walkthrough: OK https://www.kaggle.com/code/taylorsamarel/duecare-610-submission-walkthrough

All 29 notebooks resolve.
```

## Per-kernel status

See `docs/notebook_guide.md` for the full table with live URLs.
That file is regenerated from `scripts/verify_kaggle_urls.py`
output and is the authoritative list.
