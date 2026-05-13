"""Search prompts (Phase 12 placeholder)."""
from __future__ import annotations


QUERY_REWRITE_PROMPT = (
    "You are DueCare's search assistant. Rewrite the user's question into "
    "a focused web search query that surfaces authoritative migrant-worker "
    "protection sources (ILO, POEA, BP2MI, NGO partners, court filings). "
    "Return JUST the rewritten query, no preamble."
)


RESULT_EVALUATION_PROMPT = (
    "Given the user's question and a list of search results, rank each "
    "result 1-5 on relevance and on source authority. Flag any result that "
    "appears to be recruiter marketing, paywalled, or off-topic."
)


def build_rewrite_messages(question: str) -> list[dict]:
    return [
        {"role": "system", "content": [{"type": "text", "text": QUERY_REWRITE_PROMPT}]},
        {"role": "user", "content": [{"type": "text", "text": question}]},
    ]
