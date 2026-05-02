# Individual researcher — using Duecare for analysis

> **Persona.** Academic, NGO research lead, investigative journalist,
> grad student. You don't deploy software for a living. You want to
> use Duecare as a tool: feed it data, get back structured analysis
> you can cite or build on.
>
> **Use cases.** Code a labor-trafficking dataset. Compare Gemma 4
> against alternatives on a domain rubric. Map fee-camouflage
> patterns across 10k posts on Facebook job groups. Analyze a year
> of court filings for ILO-indicator coverage. Reproduce someone
> else's published numbers to verify them.
>
> **What this doc gives you.** Three concrete workflows + the
> citations + the reproducibility pattern researchers need to
> defend their results.

## TL;DR

| You want to... | Use |
|---|---|
| Try the harness without installing anything | The 6 published Kaggle notebooks |
| Run on your own dataset (≤ 1000 prompts) | Local CLI: `examples/deployment/local-cli/duecare_cli.py` |
| Run a batch (1000+ prompts) | A short Python script using `duecare-llm-chat` |
| Compare Gemma 4 vs other models | The `bench-and-tune` Kaggle notebook |
| Add your domain (medical / fraud / etc.) | Extension pack format + a custom domain pack |
| Cite specific findings | The `(git_sha, dataset_version, model_revision)` provenance pattern |

## Three concrete workflows

### Workflow 1: Reproduce a published number

Suppose you read in the writeup: *"+56.5 pp mean lift on the
207-prompt rubric"* and you want to verify it.

```bash
# 1. Install
pip install duecare-llm-chat duecare-llm-tasks duecare-llm-domains

# 2. Get the dataset (the 207 prompts + their hand-grade rubrics)
git clone https://github.com/TaylorAmarelTech/gemma4_comp.git
cd gemma4_comp

# 3. Pull the model (Apache 2.0, ungated)
ollama pull gemma4:e2b

# 4. Reproduce
python scripts/run_local_gemma.py --graded-only --output reproduce.jsonl

# 5. Compare your output to the published harness_lift_report.md numbers
python scripts/compare_to_published.py reproduce.jsonl docs/harness_lift_report.md
```

The reproduction tolerates ±2% per category (model nondeterminism)
and prints any rows that diverge by more than that.

### Workflow 2: Run on your own dataset

Suppose you have 500 job postings scraped from a regional Facebook
group. You want to know: how many show recruitment-fraud patterns?

```python
from duecare.chat.harness import apply_grep_rules, retrieve_rag_docs
import json

with open("my_postings.jsonl") as f:
    postings = [json.loads(line) for line in f]

results = []
for posting in postings:
    text = posting["body"]
    grep_hits = apply_grep_rules(text)
    if grep_hits:
        results.append({
            "post_id": posting["id"],
            "rules_fired": [h["rule"] for h in grep_hits],
            "indicators": list({h["indicator"] for h in grep_hits}),
            "snippet": text[:200],
        })

# Quick triage: the highest-severity hits
critical = [r for r in results
            if any(rule.endswith("critical") for rule in r["rules_fired"])]
print(f"{len(critical)} of {len(postings)} show critical patterns.")

# Save for downstream analysis
with open("flagged.jsonl", "w") as f:
    for r in results:
        f.write(json.dumps(r) + "\n")
```

That's it. No model needed. The GREP layer alone gives you a
deterministic first pass — fast (10k posts/sec on CPU), reproducible,
defensible.

For a richer analysis with Gemma 4 reasoning per posting:

```python
import requests

OLLAMA = "http://localhost:11434"
for r in results[:50]:   # sample of 50
    text = next(p["body"] for p in postings if p["id"] == r["post_id"])
    prompt = f"""Analyze this job posting for trafficking indicators:

{text}

Cite specific ILO C029 indicators (1-11) by number, the controlling
statute if known, and what evidence in the post supports your
finding."""
    resp = requests.post(f"{OLLAMA}/api/generate", json={
        "model": "gemma4:e2b",
        "prompt": prompt,
        "stream": False,
    })
    r["gemma_analysis"] = resp.json().get("response", "")
```

### Workflow 3: Compare Gemma 4 against alternatives

For "Gemma 4 vs GPT-4 vs Claude vs Mistral on the trafficking-rubric"
papers:

```bash
# Use the comparison notebooks directly
# Open in Kaggle: https://www.kaggle.com/code/taylorsamarel/duecare-bench-and-tune
# (this is one of the 5 appendix notebooks)
#
# OR locally:
python scripts/run_comparison.py \
  --models gemma4:e2b gemma4:e4b claude-sonnet-4 gpt-4o \
  --rubric trafficking_legal_citation_quality \
  --n-prompts 207 \
  --output comparison.jsonl
```

Caveats:
- Cloud models need API keys in env vars (`ANTHROPIC_API_KEY`,
  `OPENAI_API_KEY`, etc.) — those rows in the output get redacted
  to model names only, no prompt/response content
- Comparison is fair only if all models see the same prompt; the
  harness layers can be on or off independently per model
- Cite the exact `(git_sha, dataset_version, model_revision)` for
  each row so others can reproduce

## Reproducibility — the citation contract

Every metric Duecare publishes is anchored to three IDs:

```
(git_sha, dataset_version, model_revision)
```

When you cite Duecare in a paper / post / report:

1. **git_sha**: pin the repo to a specific commit SHA — `git checkout <sha>`
2. **dataset_version**: the Kaggle dataset version pinned in the
   notebook's `kernel-metadata.json`, e.g.
   `taylorsamarel/duecare-trafficking-prompts/v3`
3. **model_revision**: the HF Hub revision SHA of the model,
   e.g. `google/gemma-4-e2b-it@a3f9c1d`

All three together let any reader rerun your analysis and get the
same numbers (within the model's nondeterminism tolerance).

Example footnote in a paper:

> Lift figures (+56.5 pp mean) computed against 207 hand-graded
> prompts using the Duecare safety harness at git SHA `c235e14`,
> dataset `taylorsamarel/duecare-trafficking-prompts@v3`, model
> `google/gemma-4-e2b-it@main` as of 2026-05-02. Reproduction
> instructions: `docs/scenarios/researcher-analysis.md`,
> "Workflow 1".

## Datasets you can use

Bundled / public:

| Dataset | Slug | Size | License |
|---|---|---|---|
| Trafficking prompts (public) | `taylorsamarel/duecare-trafficking-prompts` | 21K prompts + 5 rubrics | CC-BY-4.0 |
| 5-grade rubric annotations | (in the same dataset) | 207 hand-graded | CC-BY-4.0 |
| Corridor lookup tables | (bundled in `duecare-llm-domains`) | 6 corridors | MIT |
| Trafficking GREP rule catalog | (bundled in `duecare-llm-chat`) | 37 rules | MIT |
| RAG legal corpus | (bundled in `duecare-llm-chat`) | 26 docs | CC-BY-4.0 (each doc has its own attribution) |

For your own data:

- Hand-grade 50-100 prompts in your domain. That's the rubric you'll
  cite. The published 207-prompt rubric took ~30 hours of focused
  hand-grading; budget similar.
- Save in JSONL: `{"id": "...", "prompt": "...", "expected": ["..."]}`.
- Use `duecare-llm-tasks` to run the rubric against any model.

## What makes a research finding defensible

If you're publishing a result like "Gemma 4 + Duecare improves
legal citation quality by N pp on our domain":

1. **Pre-register the rubric** — write the 12-point rubric BEFORE
   running the model. Otherwise post-hoc rubric design will leak
   the result you want.
2. **Hand-grade > 100 prompts** — fewer and your confidence
   intervals are too wide to publish. The bundled rubric uses 207.
3. **Report nondeterminism** — run each prompt 3+ times with
   `temperature=0.7`; report mean ± std. Or use `temperature=0`
   for a deterministic single run (and note this disables Gemma's
   sampling behaviors that real users would see).
4. **Pin everything** — `(git_sha, dataset_version, model_revision)`.
   Without this, your paper isn't reproducible by anyone, including
   your future self.
5. **Disclose what's BUNDLED vs CUSTOM** — if you used the bundled
   GREP catalog + RAG corpus + tools, say so. If you added a
   domain-specific extension, link to the extension pack.
6. **Publish your prompts + your annotation** — even if you can't
   release the model output (license / cost), publish the inputs.
   That's the minimum for replication.

## How NOT to use Duecare for research

- **Don't grade the model with the model.** "Use Gemma 4 to score
  Gemma 4's responses" produces a self-flattering rubric that
  doesn't generalize. Hand-grade or use a different LLM as judge.
- **Don't conflate harness lift with model improvement.** The
  +56.5 pp number is *the harness's* contribution; it doesn't
  mean Gemma 4 got smarter. Always report harness OFF vs ON
  separately so the contributions are visible.
- **Don't draw causal conclusions from cross-sectional data.**
  "Posts with rule X fire are Y% more likely to be trafficking"
  needs longitudinal validation (do those posts actually correlate
  with confirmed cases?). The bundled rubric doesn't claim to.
- **Don't anonymize by removing only obvious PII.** Quasi-identifiers
  (corridor + recruiter name + date) re-identify a small population.
  Use proper k-anonymity / differential privacy if your data is
  sensitive.

## Citation

If you use Duecare in academic work, please cite:

```bibtex
@software{amarel_duecare_2026,
  author       = {Taylor Amarel},
  title        = {Duecare: a content-safety harness for Gemma 4
                  on migrant-worker trafficking risk},
  year         = 2026,
  publisher    = {GitHub},
  version      = {0.1.0},
  url          = {https://github.com/TaylorAmarelTech/gemma4_comp},
  note         = {Submission to the Gemma 4 Good Hackathon}
}
```

If your work specifically uses the harness-lift methodology in
[`docs/harness_lift_report.md`](../harness_lift_report.md),
also cite the rubric DOI (TBD on rubric publication).

## Adjacent reads

- [`docs/embedding_guide.md`](../embedding_guide.md) — for embedding
  the harness into other research tools / dashboards
- [`docs/scenarios/lawyer-evidence-prep.md`](./lawyer-evidence-prep.md) — adjacent persona; legal-aid clinic
- [`docs/scenarios/regulator-pattern-analysis.md`](./regulator-pattern-analysis.md) — adjacent persona; government regulator
- [`kaggle/_INDEX.md`](../../kaggle/_INDEX.md) — full notebook roster
