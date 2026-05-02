"""Two-tier NL->SQL translator: template-match first, Gemma fallback."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from duecare.evidence.queries import QUESTION_TEMPLATES
from duecare.nl2sql.safety import validate_readonly, SQLSafetyError


_SCHEMA_DESCRIPTION = """
Tables (DuckDB / SQLite / Postgres compatible SELECTs only):

  runs(run_id, started_at, completed_at, pipeline_version, input_root,
       n_documents, n_entities, n_edges, n_findings)

  documents(doc_id, run_id, image_path, source_pdf, bundle, category,
            language, parsed_at, page_count, triage_score)

  entities(entity_id, run_id, etype, canonical_name, raw_spellings_json,
           doc_count, bundle_count, severity_max)
    -- etype IN ('person_or_org', 'organization', 'recruitment_agency',
                  'employer', 'phone', 'email', 'financial_account',
                  'address', 'passport_number', 'id_number', 'money',
                  'case_bundle', 'date', 'location')

  entity_documents(entity_id, doc_id, raw_spelling, page, confidence, source)

  edges(edge_id, run_id, a_entity_id, b_entity_id, relation_type,
        confidence, doc_count, source, evidence_text, gemma_confirmed,
        gemma_confidence)

  findings(finding_id, run_id, doc_id, bundle, trigger_name,
           finding_type, severity, statute_violated, jurisdiction,
           fee_value, scheme_pattern, detected_at)
    -- trigger_name IN ('fee_detected', 'passport_held_by_employer',
                         'phone_shared_cross_bundle',
                         'agency_repeated_cross_doc',
                         'suspicious_chat_pattern')

  pairwise_links(link_id, run_id, doc_a_id, doc_b_id, relationship_type,
                 confidence, explanation, visual_similarities_json,
                 shared_entities_json)

  bundle_summaries(bundle, run_id, n_documents, n_entities, n_findings,
                   severity_max, brief_text, top_actors_json)

  tool_call_cache(call_id, tool_name, args_hash, args_json, result_json,
                  fetched_at, ttl_seconds, hit_count)
"""


@dataclass
class TranslationResult:
    question: str
    method: str                  # "template" | "gemma" | "fallback"
    template_name: Optional[str] = None
    sql: str = ""
    params: dict = field(default_factory=dict)
    rows: list = field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None
    raw_gemma_output: str = ""


class Translator:
    """Translate natural-language questions into SELECTs against the
    evidence store."""

    def __init__(self, store, gemma_call: Optional[Callable] = None) -> None:
        """Args:
          store      -- a duecare.evidence.EvidenceStore
          gemma_call -- callable(prompt: str, max_new_tokens: int) -> str.
                        Used for free-form translation when no template
                        matches. Pass None to disable Gemma fallback.
        """
        self.store = store
        self.gemma_call = gemma_call

    # -- public API -----------------------------------------------------------
    def answer(self, question: str,
                 prefer_template: bool = True) -> TranslationResult:
        """Run the two-tier translator and return the result."""
        result = TranslationResult(question=question, method="template")
        if prefer_template:
            tmpl_match = self._match_template(question)
            if tmpl_match:
                tmpl_name, params = tmpl_match
                try:
                    payload = self.store.run_template(tmpl_name, params)
                    result.template_name = tmpl_name
                    result.sql = payload["sql"]
                    result.params = params
                    result.rows = payload["rows"]
                    result.row_count = payload["row_count"]
                    return result
                except Exception as e:
                    result.error = f"template execution FAIL: {e}"
        # Gemma free-form fallback
        if self.gemma_call is None:
            result.method = "fallback"
            result.error = (result.error or "no template matched and "
                            "no Gemma backend supplied")
            return result
        result.method = "gemma"
        gemma_sql, raw = self._gemma_translate(question)
        result.raw_gemma_output = raw
        if not gemma_sql:
            result.error = "Gemma did not return parseable SQL"
            return result
        try:
            cleaned_sql = validate_readonly(gemma_sql)
        except SQLSafetyError as e:
            result.error = f"safety check failed: {e}"
            result.sql = gemma_sql
            return result
        result.sql = cleaned_sql
        try:
            result.rows = self.store.fetchall(cleaned_sql)
            result.row_count = len(result.rows)
        except Exception as e:
            result.error = f"SQL execution FAIL: {e}"
        return result

    # -- template matching ----------------------------------------------------
    def _match_template(self, question: str) -> Optional[tuple[str, dict]]:
        """Cheap keyword-driven matcher. Returns (template_name, params)
        or None. Designed so the demo's 6 question types always hit a
        template even when Gemma is unavailable."""
        q = question.lower().strip()

        # avg_fee_by_corridor
        if (("average" in q or "avg" in q or "typical" in q
             or "common" in q or "what" in q)
                and "fee" in q):
            return ("avg_fee_by_corridor", {"min_severity": 0})

        # fee_change_over_time
        if "fee" in q and any(k in q for k in (
                "change", "trend", "over time", "recent", "lately",
                "month", "year")):
            return ("fee_change_over_time", {"agency_name": None})

        # complaints_by_agency
        if "complaint" in q or ("how many" in q and any(
                k in q for k in ("agency", "company", "agencies",
                                  "recruiter"))):
            agency = self._extract_quoted_or_capitalised(question)
            return ("complaints_by_agency",
                    {"agency_name": agency, "min_severity": 0})

        # documents_citing_entity
        if any(k in q for k in ("documents", "docs", "files", "show me")
               ) and any(k in q for k in (
                   "mentioning", "mention", "about", "related to",
                   "cite", "citing", "with")):
            ent = self._extract_quoted_or_capitalised(question)
            if ent:
                return ("documents_citing_entity",
                        {"entity_name": ent})

        # scheme_fingerprints
        if (("worrisome" in q or "trend" in q or "scheme" in q
             or "pattern" in q or "mo" in q or "modus" in q)
                and not "fee" in q):
            return ("scheme_fingerprints", {})

        # top_bad_actors
        if any(k in q for k in (
                "bad actor", "bad actors", "trafficker", "worst",
                "most flagged", "top suspect", "top actor")):
            return ("top_bad_actors", {"etype": None, "limit": 25})

        return None

    def _extract_quoted_or_capitalised(self, q: str) -> Optional[str]:
        """Pull a quoted name from the question, or fall back to the
        longest capitalised run."""
        m = re.search(r"['\"]([^'\"]+)['\"]", q)
        if m:
            return m.group(1).strip()
        # Find longest sequence of Capitalised words
        cap_runs = re.findall(r"(?:[A-Z][\w&-]*(?:\s+[A-Z][\w&-]*)+)", q)
        cap_runs.sort(key=len, reverse=True)
        return cap_runs[0] if cap_runs else None

    # -- Gemma free-form ------------------------------------------------------
    def _gemma_translate(self, question: str) -> tuple[Optional[str], str]:
        prompt = (
            "You write SAFE READ-ONLY SQL for a SQLite-compatible "
            "evidence database. Schema:\n"
            f"{_SCHEMA_DESCRIPTION}\n"
            "RULES:\n"
            "1. Output ONE SELECT (or WITH ... SELECT) statement and "
            "NOTHING ELSE.\n"
            "2. NEVER use INSERT/UPDATE/DELETE/DROP/CREATE/ALTER.\n"
            "3. Always LIMIT results to <= 100 rows.\n"
            "4. Use simple column names that exist in the schema "
            "above.\n"
            "5. Wrap your final answer in a fenced sql code block.\n\n"
            f"QUESTION:\n{question}\n\n"
            "SQL:"
        )
        try:
            raw = self.gemma_call(prompt, max_new_tokens=400) or ""
        except Exception as e:
            return None, f"gemma call FAILED: {type(e).__name__}: {e}"
        # Pull SQL out of the response. Prefer fenced ```sql ... ```
        m = re.search(r"```(?:sql)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip(), raw
        # Fallback: grab the longest line starting with SELECT / WITH
        for line in raw.splitlines():
            ls = line.strip()
            if ls.upper().startswith(("SELECT", "WITH ")):
                return ls.rstrip(";"), raw
        # Last resort: assume the whole reply is SQL
        return raw.strip().rstrip(";") if raw else None, raw
