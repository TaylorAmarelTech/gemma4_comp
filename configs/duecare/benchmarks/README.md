# Benchmark prompt corpora — data card

**Read this before reading the corpora.** These files contain thousands of
prompts written from the point of view of people attempting labour
exploitation. That is what they are for. This card states plainly what is in
them, why, and what has deliberately been left out.

## What these are

Adversarial evaluation sets for migrant-worker safety. Each row is a prompt
put to a model to find out how the model responds. A large share are written
in the voice of a recruiter, agency director, or employer trying to get a
model to validate a scheme — debt bondage, recruitment-fee shifting, passport
retention, wage deduction dressed as savings, jurisdiction shopping. Others
are written in the voice of workers asking for help, and a deliberate control
set is entirely benign.

Publishing adversarial prompts is standard practice for safety benchmarks
(HarmBench, AdvBench, and JailbreakBench all do it). Without public prompts,
nobody can reproduce a safety claim.

## Category names are labels, not endorsements

Categories such as `base_harmful`, `override_jailbreak`, `evasion_probe`,
`keyword_mutation`, `punctuated_obfuscation`, and
`prompt_injection_amplification` describe **what the prompt attempts**, so
results can be broken down by attack shape. A category named `base_harmful`
marks a prompt as a harmful request that should be refused. It does not mark
content the project endorses, and no row is advice.

## Inventory

| File | Rows | Role |
|---|---:|---|
| `scheme_prompts.json` | 5,998 | Broad scheme/pretext sweep across 180+ categories |
| `attack_matrix.json` | 2,940 | Attack-shape matrix |
| `harness_lift_prompts_expansion.jsonl` | 2,532 | Paired lift-measurement expansion |
| `harness_lift_prompts_2000.json` | 2,000 | Paired lift measurement |
| `pretext_framing_prompts.jsonl` | 1,848 | Pretext-framing variants |
| `harness_lift_prompts_1000.json` | 1,000 | Paired lift measurement |
| `money_laundering_prompts.jsonl` | 600 | Financial-crime intersection |
| `harness_lift_prompts_500.json` | 500 | Paired lift measurement |
| `benign_control_prompts.json` | 440 | **Benign controls** — over-refusal measurement |
| `harness_lift_prompt_mix_expansion.jsonl` | 418 | Mixed-intent expansion |
| `multipath_prompts.jsonl` | 176 | Multi-leg scheme chains |
| `harness_lift_prompts_100.json` | 100 | Small paired slice |
| `money_laundering_benign_controls.json` | 72 | **Benign controls** — financial-crime lane |

The benign-control sets exist because a safety system that refuses everything
is not safe, it is useless. They measure over-refusal on legitimate worker and
employer questions and are scored separately — never merged into the
under-refusal headline.

## Every entity in these files is invented

Person names, company names, agency names, licence numbers, registration
numbers, phone numbers, and case IDs are **fabricated composites**. Names are
deliberately plausible, because a benchmark built from obviously-fake names
would not test realistic inputs — but no entity refers to a real organisation,
and any resemblance is coincidental. Regulator licence numbers use real-world
*formats* with fabricated *values*.

The single deliberate exception is **statute and convention citations** (ILO
C029/C097/C181/C189, the UN Palermo Protocol, RA 8042/10022, and similar).
Those are public record and are meant to be verifiable — checking whether a
model cites them correctly is part of the measurement.

## What is deliberately not here

**Successful harmful completions.** Where the project retains what a model
actually answered, the response text is withheld from public files; only the
grade, outcome, and model id remain. See
`scripts/redact_seed_prompt_responses.py`, whose `--check` mode gates against
regression. Prompts and grades are what make a claim reproducible. The
completions that succeeded would mostly transfer operational detail, so they
stay out.

**Any registry of safety-stripped models.** DueCare does not distribute,
endorse, or link refusal-ablated Gemma weights anywhere in this repository.

## Handling

Treat these corpora as evaluation inputs. Do not use them as training targets
without the domain pack's grading ladder, do not quote rows as guidance, and
do not treat a fabricated licence number as a real registration. Related terms
and the PII boundary: `configs/duecare/domains/trafficking/README.md` and
`.claude/rules/10_safety_gate.md`.
