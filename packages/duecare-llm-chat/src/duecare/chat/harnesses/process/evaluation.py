"""Per-harness grading rubric + golden examples for process.

A bench-and-tune kernel picks ``rubric`` and ``examples`` from this
module to run targeted evaluations on this harness's safety task.
Rubric dimensions sum to weight 1.0; ``pass_criteria`` is the spec for
each dim's binary or graded score.
"""
from __future__ import annotations


rubric: list[dict] = [{'name': 'row_id_grounding', 'weight': 0.25, 'description': 'Cites specific row_ids when claiming a finding', 'pass_criteria': 'answer references at least one row_id from the bundle'}, {'name': 'layer_use', 'weight': 0.2, 'description': 'Uses the composed grounding (GREP / RAG / Tools)', 'pass_criteria': 'applied_layers trace shows at least one fired wired layer'}, {'name': 'no_invention', 'weight': 0.25, 'description': 'Does not invent rows / amounts / statutes not in the bundle', 'pass_criteria': 'every cited row_id / statute exists in bundle.results or summary'}, {'name': 'indicator_naming', 'weight': 0.15, 'description': 'Names the GREP rule_ids relevant to the question', 'pass_criteria': 'at least one rule_id from bundle.summary.top_grep mentioned'}, {'name': 'actionability', 'weight': 0.15, 'description': 'Output is something an NGO caseworker can act on', 'pass_criteria': 'concrete observation or next-step rather than vague summary'}]

examples: list[dict] = [{'input': {'question': 'Which rows mention placement fees above the legal cap?'}, 'expected_layers_fired': ['grep', 'rag', 'tools'], 'notes': 'Must cite row_ids, must reference the corridor fee-cap statute.'}, {'input': {'question': 'What corridors appear most in this bundle?'}, 'expected_layers_fired': ['grep'], 'notes': 'Should read bundle.summary.entity_totals.CORRIDOR, not invent.'}, {'input': {'question': 'Are there document-retention indicators in the recruiter messages?'}, 'expected_layers_fired': ['grep', 'rag'], 'notes': 'Should cite passport-retention rule + relevant ILO convention.'}]


def summary() -> dict:
    return {
        "harness": "process",
        "n_rubric_dims": len(rubric),
        "n_examples": len(examples),
        "weight_total": sum(d.get("weight", 0) for d in rubric),
    }
