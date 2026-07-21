# DueCare Prompt and Response Showcase

Raw **prompt + three model responses** for the DueCare harness-lift benchmark, staged for
NLP / sentiment / keyword analysis. Each row is one synthetic, composite migrant-worker-safety
scenario answered by `gemma4:31b` under three arms:

| column | meaning |
|---|---|
| `prompt_id` | synthetic scenario id (GEN-/SCHEME-/...) |
| `category` | scenario family |
| `corridor` | migration corridor (may be blank) |
| `difficulty` | scenario difficulty (may be blank) |
| `prompt_text` | the raw adversarial prompt |
| `baseline_response` | the bare model's answer |
| `harness_core_response` | the model wrapped in the DueCare harness (persona + GREP indicator rules + retrieval + tools) |
| `harness_full_response` | the harness with online lookups |

**Rows:** 1,087 prompts x 3 responses. **Categories:** 73.
Mean response length -- baseline 2795 chars, harness_core 4300 chars.

## Safety and provenance
- Prompts are **synthetic / composite** scenarios -- no real individual, no real case.
- Responses are **model outputs** to those synthetic prompts.
- Kernel run-metadata (paths, run/job ids, archive names) is scrubbed; response structure is preserved.
- Rows tripping a conservative PII scan (e-mail / long account-number / IBAN patterns) are dropped.
- Composite first names are allowed; public NGO hotline numbers in a harnessed answer are public resources, not personal data.
- LLM/model outputs are illustrative, not ground truth. License: CC0-1.0.

Companion grades (scores only): `taylorsamarel/duecare-harness-benchmark-grades`.
Repo: https://github.com/TaylorAmarelTech/gemma4_comp
