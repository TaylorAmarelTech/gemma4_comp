"""Parameterised question templates -- the 6 demo-friendly NGO queries.

These are the SAFE, PARAMETERISED queries that NL->SQL falls back to
when Gemma's free-form translation fails or is uncertain. Each template
is a pure function of (params dict) -> (sql, ordered_params_tuple).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QuestionTemplate:
    name: str
    description: str
    natural_language_examples: list[str]
    required_params: list[str]
    optional_params: list[str]
    sql: str
    """SQL with named :param placeholders. The render() method binds
    them in deterministic order."""

    def render(self, params: dict) -> tuple[str, tuple]:
        """Substitute :name placeholders with ? and return ordered tuple."""
        # Validate required params
        missing = [p for p in self.required_params if p not in params]
        if missing:
            raise ValueError(
                f"template {self.name!r} missing required params: {missing}")
        # Order params in the order they appear in the SQL
        ordered: list = []
        sql_out: list[str] = []
        i = 0
        while i < len(self.sql):
            ch = self.sql[i]
            if ch == ":" and i + 1 < len(self.sql) and self.sql[i + 1].isalpha():
                # Read identifier
                j = i + 1
                while j < len(self.sql) and (self.sql[j].isalnum() or self.sql[j] == "_"):
                    j += 1
                name = self.sql[i + 1:j]
                if name in params:
                    ordered.append(params[name])
                else:
                    ordered.append(None)
                sql_out.append("?")
                i = j
            else:
                sql_out.append(ch)
                i += 1
        return "".join(sql_out), tuple(ordered)


QUESTION_TEMPLATES: dict[str, QuestionTemplate] = {

    "avg_fee_by_corridor": QuestionTemplate(
        name="avg_fee_by_corridor",
        description="Average illicit recruitment fee detected, broken "
                    "down by jurisdiction.",
        natural_language_examples=[
            "What is the average illicit fee?",
            "What's the typical recruitment fee charged?",
            "Show me average fees by country",
        ],
        required_params=[],
        optional_params=["min_severity"],
        sql=(
            "SELECT jurisdiction, "
            "COUNT(*) AS finding_count, "
            "AVG(severity) AS avg_severity, "
            "GROUP_CONCAT(DISTINCT fee_value) AS sample_fees "
            "FROM findings "
            "WHERE trigger_name = 'fee_detected' "
            "AND severity >= COALESCE(:min_severity, 0) "
            "GROUP BY jurisdiction "
            "ORDER BY finding_count DESC"
        ),
    ),

    "complaints_by_agency": QuestionTemplate(
        name="complaints_by_agency",
        description="Number of complaint-flagged findings per agency / "
                    "organisation entity.",
        natural_language_examples=[
            "How many complaints does X agency have?",
            "Show me complaints by agency",
            "Which agencies have the most complaints?",
        ],
        required_params=[],
        optional_params=["agency_name", "min_severity"],
        sql=(
            "SELECT e.canonical_name AS agency, "
            "COUNT(DISTINCT f.finding_id) AS complaint_count, "
            "MAX(f.severity) AS max_severity, "
            "COUNT(DISTINCT f.bundle) AS bundle_count "
            "FROM entities e "
            "JOIN entity_documents ed ON ed.entity_id = e.entity_id "
            "JOIN findings f ON f.doc_id = ed.doc_id "
            "WHERE e.etype IN ('person_or_org', 'organization', "
            "'recruitment_agency', 'employer') "
            "AND f.severity >= COALESCE(:min_severity, 0) "
            "AND (:agency_name IS NULL OR LOWER(e.canonical_name) "
            "LIKE LOWER('%' || :agency_name || '%')) "
            "GROUP BY e.canonical_name "
            "HAVING complaint_count > 0 "
            "ORDER BY complaint_count DESC, max_severity DESC "
            "LIMIT 50"
        ),
    ),

    "fee_change_over_time": QuestionTemplate(
        name="fee_change_over_time",
        description="Time-series of detected fee values (by month).",
        natural_language_examples=[
            "Has there been changes in how fees are collected recently?",
            "Show me fee trends over time",
            "How have fees changed?",
        ],
        required_params=[],
        optional_params=["agency_name"],
        sql=(
            "SELECT strftime(f.detected_at, '%Y-%m') AS month, "
            "COUNT(*) AS finding_count, "
            "AVG(f.severity) AS avg_severity, "
            "COUNT(DISTINCT f.bundle) AS bundle_count "
            "FROM findings f "
            "WHERE f.trigger_name = 'fee_detected' "
            "AND (:agency_name IS NULL OR EXISTS (SELECT 1 "
            "FROM entity_documents ed "
            "JOIN entities e ON e.entity_id = ed.entity_id "
            "WHERE ed.doc_id = f.doc_id "
            "AND LOWER(e.canonical_name) LIKE LOWER('%' || :agency_name || '%'))) "
            "GROUP BY month "
            "ORDER BY month"
        ),
    ),

    "top_bad_actors": QuestionTemplate(
        name="top_bad_actors",
        description="Top entities by combined doc count + max severity.",
        natural_language_examples=[
            "Who are the worst bad actors?",
            "Show me the top suspected traffickers",
            "Which entities appear in the most flagged documents?",
        ],
        required_params=[],
        optional_params=["etype", "limit"],
        sql=(
            "SELECT etype, canonical_name, doc_count, "
            "bundle_count, severity_max "
            "FROM entities "
            "WHERE doc_count >= 2 "
            "AND (:etype IS NULL OR etype = :etype) "
            "ORDER BY (doc_count * 2 + severity_max) DESC "
            "LIMIT COALESCE(:limit, 25)"
        ),
    ),

    "scheme_fingerprints": QuestionTemplate(
        name="scheme_fingerprints",
        description="All scheme fingerprints Gemma identified across the "
                    "corpus, grouped by pattern.",
        natural_language_examples=[
            "What worrisome trends are occurring?",
            "Show me trafficking scheme patterns",
            "What MOs are in the data?",
        ],
        required_params=[],
        optional_params=[],
        sql=(
            "SELECT scheme_pattern, "
            "COUNT(*) AS occurrence_count, "
            "COUNT(DISTINCT bundle) AS bundle_count, "
            "AVG(severity) AS avg_severity, "
            "GROUP_CONCAT(DISTINCT bundle) AS affected_bundles "
            "FROM findings "
            "WHERE finding_type = 'scheme_fingerprint' "
            "AND scheme_pattern IS NOT NULL "
            "GROUP BY scheme_pattern "
            "ORDER BY occurrence_count DESC, avg_severity DESC"
        ),
    ),

    "documents_citing_entity": QuestionTemplate(
        name="documents_citing_entity",
        description="All documents that mention a specific entity.",
        natural_language_examples=[
            "Which documents mention Pacific Coast Manpower?",
            "Show me every document that cites X",
            "Find documents related to Y",
        ],
        required_params=["entity_name"],
        optional_params=[],
        sql=(
            "SELECT d.doc_id, d.bundle, d.category, d.image_path, "
            "ed.raw_spelling, ed.confidence "
            "FROM documents d "
            "JOIN entity_documents ed ON ed.doc_id = d.doc_id "
            "JOIN entities e ON e.entity_id = ed.entity_id "
            "WHERE LOWER(e.canonical_name) = LOWER(:entity_name) "
            "OR LOWER(e.canonical_name) LIKE LOWER('%' || :entity_name || '%') "
            "ORDER BY d.parsed_at DESC "
            "LIMIT 100"
        ),
    ),
}
