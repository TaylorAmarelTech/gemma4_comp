"""Generate HF Hub-compatible model cards."""

from __future__ import annotations

from pathlib import Path
from typing import Any


CARD_TEMPLATE = """---
language: en
license: mit
tags:
  - safety
  - duecare
  - gemma
  - llm-evaluation
datasets:
  - {dataset_id}
model-index:
  - name: {model_name}
    results:
      - task:
          type: safety-evaluation
        dataset:
          name: {dataset_id}
          type: trafficking-safety
        metrics:
          - type: grade_exact_match
            value: {grade_exact_match:.3f}
---

# {model_name}

> {description}

## Model details

- **Base model:** `{base_model}`
- **Fine-tuning:** Unsloth + LoRA (r={lora_r}, alpha={lora_alpha})
- **Training epochs:** {num_epochs}
- **Training data:** {n_train_samples} samples from the Duecare trafficking / tax-evasion / financial-crime domain packs

## Intended use

This model is a **safety judge** for migrant-worker trafficking and labor
exploitation scenarios. It takes a (prompt, candidate_response) pair and
returns a grade (worst / bad / neutral / good / best) with missed safety
indicators and citations to ILO Conventions / national labor law.

**Target users:** frontline NGOs, recruitment regulators, labor
ministries - organizations where sensitive case data cannot be sent to
frontier APIs.

## Out-of-scope use

- General-purpose conversation
- Legal advice for specific cases
- Autonomous enforcement (always keep a human in the loop)

## Evaluation

| Metric | Value |
|---|---|
| Grade exact match | {grade_exact_match:.3f} |
| Grade within 1 | {grade_within_1:.3f} |
| ILO indicator recall | {ilo_indicator_recall:.3f} |
| Refusal rate | {refusal_rate:.3f} |

## Limitations

- English-only in the v0.1 release; cross-lingual support pending
- Corridor coverage is strongest for PH-SA, NP-QA, ID-SA
- Not a replacement for human expert review

## Citation

```bibtex
@misc{{amarel2026duecare,
  title={{Duecare: An Agentic Safety Harness for LLMs}},
  author={{Amarel, Taylor}},
  year={{2026}},
}}
```

## License

MIT
"""


class ModelCardGenerator:
    """Generate HF Hub-compatible model cards from run metrics."""

    def render(
        self,
        *,
        model_name: str,
        base_model: str,
        dataset_id: str,
        description: str,
        grade_exact_match: float = 0.0,
        grade_within_1: float = 0.0,
        ilo_indicator_recall: float = 0.0,
        refusal_rate: float = 0.0,
        lora_r: int = 16,
        lora_alpha: int = 32,
        num_epochs: int = 2,
        n_train_samples: int = 0,
        **extra: Any,
    ) -> str:
        return CARD_TEMPLATE.format(
            model_name=model_name,
            base_model=base_model,
            dataset_id=dataset_id,
            description=description,
            grade_exact_match=grade_exact_match,
            grade_within_1=grade_within_1,
            ilo_indicator_recall=ilo_indicator_recall,
            refusal_rate=refusal_rate,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            num_epochs=num_epochs,
            n_train_samples=n_train_samples,
        )

    def write(self, path: Path | str, **kwargs: Any) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(**kwargs), encoding="utf-8")
        return path
