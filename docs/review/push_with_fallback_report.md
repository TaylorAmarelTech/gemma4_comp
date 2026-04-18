# Kaggle Push With Fallback Report

Ran `scripts/push_all_with_fallback.py` against all 29 kernels.

## Summary

- Pushed cleanly (version bumped on existing slug): 19
- Pushed to fallback `-v2` slug (original push failed): 0
- Completely failed: 10

## Details

| Dir | Original id | Status | Title |
|---|---|---|---|
| `duecare_000_index` | `taylorsamarel/duecare-000-index` | OK | DueCare 000 Index |
| `duecare_005_glossary` | `taylorsamarel/duecare-005-glossary` | OK | DueCare 005 Glossary |
| `duecare_010_quickstart` | `taylorsamarel/duecare-010-quickstart` | OK | DueCare 010 Quickstart |
| `duecare_100_gemma_exploration` | `taylorsamarel/duecare-gemma-exploration` | OK | DueCare Gemma Exploration |
| `duecare_110_prompt_prioritizer` | `taylorsamarel/00a-duecare-prompt-prioritizer-data-pipeline` | OK | DueCare Prompt Prioritizer |
| `duecare_120_prompt_remixer` | `taylorsamarel/duecare-prompt-remixer` | OK | DueCare Prompt Remixer |
| `duecare_200_cross_domain_proof` | `taylorsamarel/duecare-200-cross-domain-proof` | OK | DueCare 200 Cross Domain Proof |
| `duecare_210_oss_model_comparison` | `taylorsamarel/duecare-gemma-vs-oss-comparison` | OK | DueCare Gemma vs OSS Comparison |
| `duecare_220_ollama_cloud_comparison` | `taylorsamarel/duecare-ollama-cloud-oss-comparison` | OK | DueCare Ollama Cloud OSS Comparison |
| `duecare_230_mistral_family_comparison` | `taylorsamarel/duecare-230-mistral-family-comparison` | OK | DueCare 230 Mistral Family Comparison |
| `duecare_240_openrouter_frontier_comparison` | `taylorsamarel/duecare-openrouter-frontier-comparison` | OK | DueCare OpenRouter Frontier Comparison |
| `duecare_250_comparative_grading` | `taylorsamarel/duecare-250-comparative-grading` | OK | DueCare 250 Comparative Grading |
| `duecare_260_rag_comparison` | `taylorsamarel/duecare-260-rag-comparison` | FALLBACK_FAIL | DueCare 260 RAG Comparison |
| `duecare_270_gemma_generations` | `taylorsamarel/duecare-270-gemma-generations` | FALLBACK_FAIL | DueCare 270 Gemma Generations |
| `duecare_300_adversarial_resistance` | `taylorsamarel/300-gemma-4-against-15-adversarial-attack-vectors` | OK | DueCare 300 Adversarial Resistance |
| `duecare_310_prompt_factory` | `taylorsamarel/duecare-310-prompt-factory` | FALLBACK_FAIL | DueCare 310 Prompt Factory |
| `duecare_320_supergemma_safety_gap` | `taylorsamarel/duecare-finding-gemma-4-safety-line` | FALLBACK_FAIL | DueCare Finding Gemma 4 Safety Line |
| `duecare_400_function_calling_multimodal` | `taylorsamarel/duecare-400-function-calling-multimodal` | FALLBACK_FAIL | DueCare 400 Function Calling Multimodal |
| `duecare_410_llm_judge_grading` | `taylorsamarel/duecare-410-llm-judge-grading` | FALLBACK_FAIL | DueCare 410 LLM Judge Grading |
| `duecare_420_conversation_testing` | `taylorsamarel/420-multi-turn-conversation-escalation-detection` | OK | DueCare 420 Conversation Testing |
| `duecare_430_rubric_evaluation` | `taylorsamarel/430-54-criterion-pass-fail-rubric-evaluation` | OK | DueCare 430 Rubric Evaluation |
| `duecare_440_per_prompt_rubric_generator` | `taylorsamarel/duecare-per-prompt-rubric-generator` | OK | DueCare Per Prompt Rubric Generator |
| `duecare_450_contextual_worst_response_judge` | `taylorsamarel/duecare-contextual-judge` | OK | DueCare Contextual Judge |
| `duecare_500_agent_swarm_deep_dive` | `taylorsamarel/duecare-500-agent-swarm-deep-dive` | FALLBACK_FAIL | DueCare 500 Agent Swarm Deep Dive |
| `duecare_510_phase2_model_comparison` | `taylorsamarel/duecare-phase2-comparison` | OK | DueCare Phase2 Comparison |
| `duecare_520_phase3_curriculum_builder` | `taylorsamarel/duecare-520-phase3-curriculum-builder` | FALLBACK_FAIL | DueCare 520 Phase3 Curriculum Builder |
| `duecare_530_phase3_unsloth_finetune` | `taylorsamarel/duecare-530-phase3-unsloth-finetune` | FALLBACK_FAIL | DueCare 530 Phase3 Unsloth Finetune |
| `duecare_600_results_dashboard` | `taylorsamarel/600-interactive-safety-evaluation-dashboard` | OK | 600: DueCare Results Dashboard |
| `duecare_610_submission_walkthrough` | `taylorsamarel/duecare-610-submission-walkthrough` | FALLBACK_FAIL | DueCare 610 Submission Walkthrough |

## Complete failures

### duecare_260_rag_comparison
```
id=taylorsamarel/duecare-260-rag-comparison-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_270_gemma_generations
```
id=taylorsamarel/duecare-270-gemma-generations-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_310_prompt_factory
```
id=taylorsamarel/duecare-310-prompt-factory-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_320_supergemma_safety_gap
```
id=taylorsamarel/duecare-finding-gemma-4-safety-line-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
'charmap' codec can't decode byte 0x8f in position 558: character maps to <undefined>
```

### duecare_400_function_calling_multimodal
```
id=taylorsamarel/duecare-400-function-calling-multimodal-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_410_llm_judge_grading
```
id=taylorsamarel/duecare-410-llm-judge-grading-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_500_agent_swarm_deep_dive
```
id=taylorsamarel/duecare-500-agent-swarm-deep-dive-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_520_phase3_curriculum_builder
```
id=taylorsamarel/duecare-520-phase3-curriculum-builder-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_530_phase3_unsloth_finetune
```
id=taylorsamarel/duecare-530-phase3-unsloth-finetune-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```

### duecare_610_submission_walkthrough
```
id=taylorsamarel/duecare-610-submission-walkthrough-v2
Your kernel title does not resolve to the specified id. This may result in surprising behavior. We suggest making your title something that resolves to the specified id. See https://en.wikipedia.org/wiki/Clean_URL#Slug for more information on how slugs are determined.
429 Client Error: Too Many Requests for url: https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel
```
