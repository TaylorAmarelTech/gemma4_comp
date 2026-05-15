"""Shared layer composer for every harness.

Each safety layer (GREP / RAG / Tools / Online) is a callable wired into
``app.state``. ``compose_layers(app, text, *, layers)`` fans out to the
requested layers, captures their output in a trace, and assembles a
Gemma-readable grounding block. Wired layers run; missing or failing
layers degrade to "skipped"/"error" entries -- never raise.
"""
from __future__ import annotations

from typing import Any


LAYER_NAMES: tuple[str, ...] = ("grep", "rag", "tools", "online")


def compose_layers(
    app: Any,
    text: str,
    *,
    layers: list[str] | tuple[str, ...] = LAYER_NAMES,
    rag_top_k: int = 5,
    online_top_n: int = 5,
) -> dict[str, Any]:
    """Run the requested safety layers against ``text``."""
    trace: dict[str, dict[str, Any]] = {}
    grounding_chunks: list[str] = []

    if "grep" in layers:
        gc = getattr(app.state, "grep_call", None)
        if gc is None:
            trace["grep"] = {"fired": False, "skipped": "not wired"}
        else:
            try:
                try:
                    out = gc(text) or {}
                except TypeError:
                    out = gc(text, extra_rules=None) or {}
                hits = (out.get("hits") or [])[:10]
                rule_ids = [
                    rid for rid in (h.get("rule_id") or h.get("id") for h in hits)
                    if rid
                ]
                trace["grep"] = {
                    "fired": bool(hits),
                    "n_hits": len(hits),
                    "rule_ids": rule_ids,
                }
                if hits:
                    grounding_chunks.append(
                        "[GREP layer fired]\n"
                        + "\n".join(
                            f"- {h.get('rule_id') or h.get('id') or 'unnamed_rule'} "
                            f"({h.get('severity', 'medium')}): "
                            f"{(h.get('match_text') or h.get('match') or '')[:120]}"
                            for h in hits
                        )
                    )
            except Exception as e:
                trace["grep"] = {"fired": False, "error": str(e)[:200]}

    if "rag" in layers:
        rc = getattr(app.state, "rag_call", None)
        if rc is None:
            trace["rag"] = {"fired": False, "skipped": "not wired"}
        else:
            try:
                try:
                    out = rc(text, top_k=rag_top_k) or {}
                except TypeError:
                    out = rc(text) or {}
                docs = (out.get("docs") or [])[:rag_top_k]
                trace["rag"] = {
                    "fired": bool(docs),
                    "n_docs": len(docs),
                    "doc_ids": [d.get("id") for d in docs],
                }
                if docs:
                    grounding_chunks.append(
                        "[RAG layer surfaced these citations]\n"
                        + "\n".join(
                            f"- {d.get('title') or d.get('id')}: "
                            f"{(d.get('snippet') or '')[:200]}"
                            for d in docs
                        )
                    )
            except Exception as e:
                trace["rag"] = {"fired": False, "error": str(e)[:200]}

    if "tools" in layers:
        tc = getattr(app.state, "tools_call", None)
        if tc is None:
            trace["tools"] = {"fired": False, "skipped": "not wired"}
        else:
            try:
                msgs = [{"role": "user", "content": [{"type": "text", "text": text}]}]
                out = tc(msgs) or {}
                calls = (out.get("tool_calls") or [])[:8]
                trace["tools"] = {
                    "fired": bool(calls),
                    "n_calls": len(calls),
                    "tool_names": [c.get("name") for c in calls],
                }
                if calls:
                    grounding_chunks.append(
                        "[Tools layer returned]\n"
                        + "\n".join(
                            f"- {c.get('name')}({c.get('args')}): "
                            f"{str(c.get('result'))[:200]}"
                            for c in calls
                        )
                    )
            except Exception as e:
                trace["tools"] = {"fired": False, "error": str(e)[:200]}

    if "online" in layers:
        oc = getattr(app.state, "online_search_call", None)
        if oc is None:
            trace["online"] = {"fired": False, "skipped": "not wired"}
        else:
            try:
                out = oc(text, top_n=online_top_n) or {}
                results = (out.get("results") or [])[:online_top_n]
                trace["online"] = {
                    "fired": bool(results),
                    "n_results": len(results),
                    "source": out.get("source"),
                }
                if results:
                    grounding_chunks.append(
                        "[Online search candidates]\n"
                        + "\n".join(
                            f"- {r.get('title')}: {r.get('url')} "
                            f"-- {(r.get('snippet') or '')[:160]}"
                            for r in results
                        )
                    )
            except Exception as e:
                trace["online"] = {"fired": False, "error": str(e)[:200]}

    grounding = "\n\n".join(grounding_chunks)
    return {"trace": trace, "grounding": grounding}
