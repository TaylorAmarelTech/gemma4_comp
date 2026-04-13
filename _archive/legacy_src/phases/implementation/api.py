"""Phase 4 REST API endpoints.

Routes:
  POST /v1/evaluate     - (prompt, candidate_response) -> EvaluationResult
  POST /v1/classify     - text -> {sector, corridor, ilo_indicators, attack_category}
  POST /v1/anonymize    - text -> {redacted_text, spans, actions}
  POST /v1/extract_facts - text -> list[Fact]
  GET  /v1/healthz      - model version, uptime
  GET  /docs            - OpenAPI spec (auto)

TODO: implement. See docs/project_phases.md Phase 4.2a.
"""
