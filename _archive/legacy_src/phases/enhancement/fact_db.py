"""Build the Phase 3 RAG fact database.

Ingests all 176 scraper seed modules from _reference/framework/src/scraper/seeds/
plus ILO / IOM / Palermo Protocol / Kafala / POEA documentation, emits a
SQLite fact database with stable ids and source attribution.

Schema:
  facts(id PK, text, fact_type, source_module, jurisdiction, metadata JSON)

TODO: implement. See docs/project_phases.md Phase 3.2a.
"""
