#!/usr/bin/env python3
"""
Duecare local CLI — single-file, no Docker.

Bundles Gemma 4 (via Ollama HTTP) + GREP + RAG + tools + internet search
in one terminal-friendly script. Run it on a laptop and chat with the
full harness without any service containers.

Usage:
    python duecare_cli.py                       # interactive REPL
    python duecare_cli.py --once "Is X legal?"  # one-shot
    python duecare_cli.py --pipeline "..."      # show GREP/RAG/tool hits

Prerequisites (one-time):
    1. Install Ollama (https://ollama.com/download).
    2. Pull a model:    ollama pull gemma4:e2b
    3. Install Duecare: pip install duecare-llm-chat \\
                                     duecare-llm-research-tools

Environment variables (all optional):
    OLLAMA_HOST         — default http://localhost:11434
    OLLAMA_MODEL        — default gemma4:e2b
    TAVILY_API_KEY      — enable Tavily search
    BRAVE_SEARCH_API_KEY — enable Brave search
    SERPER_API_KEY      — enable Serper search
    DUECARE_DATA_DIR    — chat + journal storage. Default: ~/.duecare/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterator

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e2b")
DATA_DIR = Path(os.environ.get("DUECARE_DATA_DIR", str(Path.home() / ".duecare")))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _import_harness():
    """Lazy import so missing deps surface a useful error message."""
    try:
        from duecare.chat.harness import (  # type: ignore
            apply_grep_rules, retrieve_rag_docs, lookup_tools,
        )
        return apply_grep_rules, retrieve_rag_docs, lookup_tools
    except ImportError:
        sys.stderr.write(
            "Missing dependency: duecare-llm-chat.\n"
            "Install: pip install duecare-llm-chat duecare-llm-research-tools\n"
        )
        sys.exit(2)


def _import_research():
    try:
        from duecare.research_tools import (  # type: ignore
            FastWebSearchTool, WikipediaTool,
        )
        return FastWebSearchTool, WikipediaTool
    except ImportError:
        return None, None  # internet search disabled


def assemble_prompt(question: str, corridor: str | None = None) -> dict:
    """Build the journey-aware prompt and return the structured pipeline."""
    apply_grep, retrieve_rag, lookup = _import_harness()
    grep_hits = apply_grep(question)
    rag_docs = retrieve_rag(question, k=3)
    tool_results = lookup(question, corridor=corridor) if corridor else []

    persona = (
        "You are a 40-year migrant-worker safety expert deeply versed "
        "in ILO conventions C029/C181/C189/C095, the Palermo Protocol, "
        "ICRMW, and the recruitment statutes of the Philippines, "
        "Indonesia, Nepal, Bangladesh, Hong Kong, and Saudi Arabia."
    )
    parts = [persona, ""]
    if grep_hits:
        parts.append("## Detected indicators (Duecare GREP)")
        for hit in grep_hits:
            parts.append(f" - {hit['rule']} [{hit['severity']}] — {hit['citation']}")
        parts.append("")
    if rag_docs:
        parts.append("## Reference law (Duecare RAG)")
        for doc in rag_docs:
            parts.append(f" - {doc['title']} ({doc['source']})")
            parts.append(f"   {doc['snippet']}")
        parts.append("")
    if tool_results:
        parts.append("## Corridor lookups")
        for r in tool_results:
            parts.append(f" - {r}")
        parts.append("")
    parts.append("## User's question")
    parts.append(question)
    return {
        "prompt": "\n".join(parts),
        "grep_hits": grep_hits,
        "rag_docs": rag_docs,
        "tool_results": tool_results,
    }


def stream_ollama(prompt: str) -> Iterator[str]:
    """Stream tokens from Ollama as they arrive."""
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": True},
        stream=True, timeout=300,
    )
    resp.raise_for_status()
    for line in resp.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        if "response" in chunk:
            yield chunk["response"]
        if chunk.get("done"):
            break


def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Optional internet research. Returns [] if no provider is configured."""
    FastWebSearchTool, _ = _import_research()
    if FastWebSearchTool is None:
        return []
    tool = FastWebSearchTool()  # picks Tavily/Brave/Serper/DuckDuckGo by env
    return tool.search(query, num_results=num_results)


def chat_once(question: str, corridor: str | None = None,
              show_pipeline: bool = False) -> None:
    """Run one question end-to-end and stream the answer."""
    pipe = assemble_prompt(question, corridor=corridor)
    if show_pipeline:
        print("\n=== Pipeline ===", file=sys.stderr)
        print(f"GREP hits ({len(pipe['grep_hits'])}):", file=sys.stderr)
        for h in pipe["grep_hits"]:
            print(f"  - {h['rule']} [{h['severity']}]", file=sys.stderr)
        print(f"RAG docs ({len(pipe['rag_docs'])}):", file=sys.stderr)
        for d in pipe["rag_docs"]:
            print(f"  - {d['title']}", file=sys.stderr)
        print(f"Tool results ({len(pipe['tool_results'])}):", file=sys.stderr)
        for t in pipe["tool_results"]:
            print(f"  - {t[:80]}...", file=sys.stderr)
        print("=== Streaming response ===\n", file=sys.stderr)
    for token in stream_ollama(pipe["prompt"]):
        sys.stdout.write(token)
        sys.stdout.flush()
    sys.stdout.write("\n")


def repl(corridor: str | None = None) -> None:
    """Interactive REPL — type a question, get a streamed answer."""
    print(f"Duecare local CLI · model={OLLAMA_MODEL} · "
          f"data={DATA_DIR} · corridor={corridor or '(none)'}")
    print("Commands: /search <query>  /pipeline <question>  /quit\n")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line in ("/quit", "/exit"):
            return
        if line.startswith("/search "):
            query = line[len("/search "):]
            results = web_search(query)
            if not results:
                print("(no internet-search provider configured — set "
                      "TAVILY_API_KEY, BRAVE_SEARCH_API_KEY, or SERPER_API_KEY)")
                continue
            for r in results:
                print(f"  - {r.get('title', '')}\n    {r.get('url', '')}")
            continue
        if line.startswith("/pipeline "):
            question = line[len("/pipeline "):]
            chat_once(question, corridor=corridor, show_pipeline=True)
            continue
        # Plain chat
        try:
            print("duecare> ", end="", flush=True)
            chat_once(line, corridor=corridor)
        except requests.RequestException as e:
            print(f"\n[error talking to ollama at {OLLAMA_HOST}: {e}]\n"
                  "Is `ollama serve` running? Try: ollama list")


def main() -> int:
    p = argparse.ArgumentParser(prog="duecare-cli")
    p.add_argument("--once", help="run one question and exit")
    p.add_argument("--pipeline", help="show GREP/RAG/tool hits for a question")
    p.add_argument("--search", help="run an internet search and exit")
    p.add_argument("--corridor", default=None,
                   help="migration corridor code, e.g. PH-HK / ID-SG / NP-SA")
    args = p.parse_args()

    if args.search:
        results = web_search(args.search)
        if not results:
            sys.stderr.write("No internet-search provider configured. "
                             "Set TAVILY_API_KEY / BRAVE_SEARCH_API_KEY / "
                             "SERPER_API_KEY.\n")
            return 1
        for r in results:
            print(f"{r.get('title', '')}\n  {r.get('url', '')}\n")
        return 0
    if args.pipeline:
        chat_once(args.pipeline, corridor=args.corridor, show_pipeline=True)
        return 0
    if args.once:
        chat_once(args.once, corridor=args.corridor)
        return 0
    repl(corridor=args.corridor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
