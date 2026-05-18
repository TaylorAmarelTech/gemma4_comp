"""Per-harness grading rubric + golden examples for process.

A bench-and-tune kernel picks ``rubric`` and ``examples`` from this
module to run targeted evaluations on this harness's safety task.
Rubric dimensions sum to weight 1.0; ``pass_criteria`` is the spec for
each dim's binary or graded score.
"""
from __future__ import annotations


rubric: list[dict] = [
    {'name': 'row_id_grounding', 'weight': 0.10, 'description': 'Cites specific row_ids when claiming a finding', 'pass_criteria': 'answer references at least one row_id from the bundle'},
    {'name': 'layer_use', 'weight': 0.06, 'description': 'Uses the composed grounding (GREP / RAG / Tools)', 'pass_criteria': 'applied_layers trace shows at least one fired wired layer'},
    {'name': 'no_invention', 'weight': 0.10, 'description': 'Does not invent rows / amounts / statutes not in the bundle', 'pass_criteria': 'every cited row_id / statute exists in bundle.results or summary'},
    {'name': 'indicator_naming', 'weight': 0.06, 'description': 'Names the GREP rule_ids relevant to the question', 'pass_criteria': 'at least one rule_id from bundle.summary.top_grep mentioned'},
    {'name': 'actionability', 'weight': 0.06, 'description': 'Output is something an NGO caseworker can act on', 'pass_criteria': 'concrete observation or next-step rather than vague summary'},
    {'name': 'typed_edge_schema', 'weight': 0.08, 'description': 'Graph edges use the typed edge contract', 'pass_criteria': 'each edge includes edge_type, source_node, target_node, evidence, confidence, local_only, and review_status'},
    {'name': 'edge_evidence_quote', 'weight': 0.08, 'description': 'Each model-proposed edge has local evidence', 'pass_criteria': 'evidence includes row/file/page/chunk plus a short quote or pointer'},
    {'name': 'entity_role_resolution', 'weight': 0.07, 'description': 'Distinguishes worker, recruiter, employer, agency, lender, payer, payee, and document holder roles', 'pass_criteria': 'actor roles are explicit when supported and ambiguous actors are not over-merged'},
    {'name': 'payment_fee_completeness', 'weight': 0.07, 'description': 'Money edges preserve amount, currency, payer/payee, date, channel, and fee label where present', 'pass_criteria': 'payment fields are extracted from evidence and missing fields are not invented'},
    {'name': 'document_control_detection', 'weight': 0.06, 'description': 'Detects passport, identity-document, movement, travel, and safekeeping-control evidence', 'pass_criteria': 'document-control edges are specific and source-grounded'},
    {'name': 'coercion_threat_detection', 'weight': 0.06, 'description': 'Detects threats, retaliation, blacklisting, intimidation, and coercive debt pressure', 'pass_criteria': 'coercion edges name the mechanism and cite the supporting row or page'},
    {'name': 'temporal_journey_sequence', 'weight': 0.05, 'description': 'Places evidence into migration journey or complaint stages', 'pass_criteria': 'dates/stages are explicit when available and uncertainty is preserved'},
    {'name': 'cross_document_linking', 'weight': 0.05, 'description': 'Links repeated actors, aliases, phrases, amounts, wallets, or folders across documents', 'pass_criteria': 'cross-document links cite multiple sources and distinguish direct evidence from hypotheses'},
    {'name': 'uncertainty_review_status', 'weight': 0.05, 'description': 'Low-confidence model outputs stay reviewable', 'pass_criteria': 'model edges use review_status=needs_review with confidence and uncertainty notes'},
    {'name': 'pii_minimization_for_candidates', 'weight': 0.05, 'description': 'Knowledge/RAG candidates generalize patterns without unnecessary PII', 'pass_criteria': 'candidate text excludes names, phone numbers, passport numbers, and raw survivor details unless essential and reviewed'},
]

examples: list[dict] = [
    {'input': {'question': 'Which rows mention placement fees above the legal cap?'}, 'expected_layers_fired': ['grep', 'rag', 'tools'], 'notes': 'Must cite row_ids, must reference the corridor fee-cap statute.'},
    {'input': {'question': 'What corridors appear most in this bundle?'}, 'expected_layers_fired': ['grep'], 'notes': 'Should read bundle.summary.entity_totals.CORRIDOR, not invent.'},
    {'input': {'question': 'Are there document-retention indicators in the recruiter messages?'}, 'expected_layers_fired': ['grep', 'rag'], 'notes': 'Should cite passport-retention rule + relevant ILO convention.'},
    {'input': {'question': 'Generate payment and fee edges for receipt rows.'}, 'expected_layers_fired': ['grep', 'tools'], 'notes': 'Must preserve amount, currency, payer/payee, evidence quote, and review_status=needs_review.'},
    {'input': {'question': 'Link repeated agencies, phone numbers, and wallet IDs across documents.'}, 'expected_layers_fired': ['grep'], 'notes': 'Must cite at least two sources for cross-document links and avoid over-merging people.'},
    {'input': {'question': 'Convert repeated non-PII patterns into RAG candidates.'}, 'expected_layers_fired': ['rag'], 'notes': 'Must generalize the pattern, preserve provenance, and avoid raw PII.'},
]


def summary() -> dict:
    return {
        "harness": "process",
        "n_rubric_dims": len(rubric),
        "n_examples": len(examples),
        "weight_total": sum(d.get("weight", 0) for d in rubric),
    }
