# Post-Search Verification Harness

Search results are candidate evidence, not trusted facts. This harness gates
sanitized search result cards before they can be injected into a prompt, drafted
as knowledge objects, or used by extraction workflows.

## Purpose

- Score source quality from URL, title, and snippet signals.
- Score relevance against the sanitized query.
- Flag basic contradiction patterns across candidate snippets.
- Block results that reintroduce direct identifiers such as emails, phone
  numbers, passport-like IDs, or precise addresses.
- Emit accepted, review, and blocked result envelopes with enough metadata for
  an audit trail.

## Model Role

The default path is deterministic and local. Local Gemma can later be added for
contradiction summarization over sanitized snippets. External models should only
receive sanitized snippets and public URLs, never the raw private prompt.

## Routes

- `POST /api/search/verify-results`
- `GET /api/search/verification-info`

## Contract

The harness consumes candidate `context_snippet`, `citation_edge`, and `rag_doc`
objects. It emits only accepted or review-gated snippets/citation edges plus an
`audit_template` row. Blocked results must not become model context.
