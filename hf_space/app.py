"""HuggingFace Space entry point for the Duecare harness chat.

Routes Gemma 4 calls to a cloud provider (Gemini API by default, OpenAI-
compatible fallback) so the Space runs CPU-only. Reuses the same chat
package as the Kaggle kernels — same harness, same 21-dim grader, same
12 curator JSON files, same auto-grade chips, same layer ablation.

Environment variables (set via Space → Settings → Variables and Secrets):
  GEMINI_API_KEY  (required for default route — get one at
                    https://aistudio.google.com/app/apikey)
  OPENAI_API_KEY  (optional fallback)
  OPENAI_BASE_URL (e.g. https://openrouter.ai/api/v1)
  OPENAI_MODEL    (e.g. google/gemma-2-9b-it:free)
  BRAVE_API_KEY   (optional — enables Online layer with Brave Search)
  TAVILY_API_KEY  (optional — enables Online layer with Tavily)
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from duecare.chat import create_app
from duecare.chat.harness import default_harness


# ---------------------------------------------------------------------------
# Cloud provider routing — pick the first env var that's set
# ---------------------------------------------------------------------------

def _gemini_call(messages: list[dict], **gen_kwargs: Any) -> str:
    """Route the chat-package's gemma_call signature to Gemini API.

    The chat package sends `messages` in OpenAI-style chat shape:
      [{"role": "user"|"assistant",
        "content": [{"type": "text", "text": ...}]}]

    Gemini wants a flat string (or its native Content list); we
    flatten to text and submit. Multimodal images aren't supported
    on the Gemini free tier; image-content chunks are described
    rather than passed.
    """
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY") or ""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set; configure in Space secrets")
    genai.configure(api_key=api_key)
    # Flatten the message stream to Gemini's contents= format
    contents: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        # Gemini calls them "user" / "model"
        gemini_role = "user" if role == "user" else "model"
        text_parts: list[str] = []
        for chunk in m.get("content") or []:
            if chunk.get("type") == "text":
                text_parts.append(chunk.get("text", ""))
            elif chunk.get("type") == "image":
                text_parts.append("[image attached — describe it]")
        if text_parts:
            contents.append({
                "role": gemini_role,
                "parts": [{"text": "\n\n".join(text_parts)}],
            })
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    cfg = {
        "temperature": float(gen_kwargs.get("temperature", 1.0)),
        "top_p":       float(gen_kwargs.get("top_p", 0.95)),
        "top_k":       int(gen_kwargs.get("top_k", 40)),
        "max_output_tokens": int(gen_kwargs.get("max_new_tokens", 4096)),
    }
    response = model.generate_content(contents, generation_config=cfg)
    try:
        return response.text or ""
    except Exception:
        # Some safety blocks return no .text; fall back to a clear message
        return "[Gemini returned no text — possibly blocked by safety filter]"


def _openai_compat_call(messages: list[dict], **gen_kwargs: Any) -> str:
    """OpenAI-compatible chat completions endpoint (OpenRouter, Groq,
    HF Inference, vLLM, etc.). Set OPENAI_API_KEY + OPENAI_BASE_URL +
    OPENAI_MODEL."""
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY") or "",
        base_url=os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1",
    )
    flat_messages: list[dict] = []
    for m in messages:
        text_parts: list[str] = []
        for chunk in m.get("content") or []:
            if chunk.get("type") == "text":
                text_parts.append(chunk.get("text", ""))
            elif chunk.get("type") == "image":
                text_parts.append("[image attached]")
        if text_parts:
            flat_messages.append({
                "role":    m.get("role", "user"),
                "content": "\n\n".join(text_parts),
            })
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gemini-1.5-flash"),
        messages=flat_messages,
        max_tokens=int(gen_kwargs.get("max_new_tokens", 4096)),
        temperature=float(gen_kwargs.get("temperature", 1.0)),
        top_p=float(gen_kwargs.get("top_p", 0.95)),
    )
    return response.choices[0].message.content or ""


def _resolve_gemma_call():
    """Pick the cloud provider based on which env var is set."""
    if os.getenv("GEMINI_API_KEY"):
        print("[hf_space] using Gemini API",
              f"(model={os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')})")
        return _gemini_call
    if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_BASE_URL"):
        print("[hf_space] using OpenAI-compat",
              f"(model={os.getenv('OPENAI_MODEL', 'unset')},",
              f"base={os.getenv('OPENAI_BASE_URL')})")
        return _openai_compat_call
    print("[hf_space] WARNING: no cloud provider configured; chat will "
          "return placeholder text. Set GEMINI_API_KEY in Space secrets.")
    def _no_provider(messages, **kw):
        return ("⚠ No cloud provider configured. The Space admin needs to "
                "set GEMINI_API_KEY in Settings → Variables and Secrets.\n\n"
                "Get a free key at https://aistudio.google.com/app/apikey "
                "(free tier: 1500 requests/day).")
    return _no_provider


# ---------------------------------------------------------------------------
# Optional online-search providers (BYOK)
# ---------------------------------------------------------------------------

def _maybe_online_search():
    """Return an online-search callable if any provider is configured,
    else None (the Online layer toggle will be hidden)."""
    has_brave = bool(os.getenv("BRAVE_API_KEY"))
    has_tavily = bool(os.getenv("TAVILY_API_KEY"))
    if not (has_brave or has_tavily):
        return None

    def _search(query: str, top_n: int = 5) -> dict:
        import httpx
        results: list[dict] = []
        sources: list[str] = []
        if has_tavily:
            try:
                r = httpx.post(
                    "https://api.tavily.com/search",
                    json={"api_key": os.getenv("TAVILY_API_KEY"),
                          "query": query, "max_results": top_n},
                    timeout=10.0,
                )
                if r.status_code == 200:
                    for i, hit in enumerate(r.json().get("results", [])[:top_n]):
                        results.append({
                            "rank": i + 1,
                            "title": hit.get("title", ""),
                            "url": hit.get("url", ""),
                            "snippet": (hit.get("content") or "")[:300],
                            "source": "tavily",
                        })
                    sources.append("tavily")
            except Exception as e:  # noqa: BLE001
                print(f"[hf_space] tavily error: {e}")
        if has_brave and len(results) < top_n:
            try:
                r = httpx.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": query, "count": top_n - len(results)},
                    headers={"X-Subscription-Token": os.getenv("BRAVE_API_KEY")},
                    timeout=10.0,
                )
                if r.status_code == 200:
                    for i, hit in enumerate(r.json().get("web", {}).get("results", [])):
                        results.append({
                            "rank": len(results) + 1,
                            "title": hit.get("title", ""),
                            "url": hit.get("url", ""),
                            "snippet": (hit.get("description") or "")[:300],
                            "source": "brave",
                        })
                    sources.append("brave")
            except Exception as e:  # noqa: BLE001
                print(f"[hf_space] brave error: {e}")
        return {
            "results": results[:top_n],
            "source": "+".join(sources) or "no-provider",
            "elapsed_ms": 0,
        }
    return _search


# ---------------------------------------------------------------------------
# Build the FastAPI app
# ---------------------------------------------------------------------------

print(f"[hf_space] starting Duecare harness chat at {time.time():.0f}")
print(f"[hf_space] python={sys.version.split()[0]}")

dh = default_harness()
gemma_call = _resolve_gemma_call()
online_search_call = _maybe_online_search()

app = create_app(
    gemma_call=gemma_call,
    model_info={
        "loaded": True,
        "name": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        "size_b": 0.0,
        "quantization": "cloud",
        "device": "cloud",
        "display": (
            f"Cloud · {os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')}"
            if os.getenv("GEMINI_API_KEY")
            else "Cloud (not configured)"
        ),
    },
    grep_call=dh["grep_call"],
    rag_call=dh["rag_call"],
    tools_call=dh["tools_call"],
    grade_call=dh["grade_call"],
    online_search_call=online_search_call,
    grep_catalog=dh["grep_catalog"],
    rag_catalog=dh["rag_catalog"],
    tools_catalog=dh["tools_catalog"],
    example_prompts=dh["example_prompts"],
    layer_docs=dh["layer_docs"],
    rubrics_required_categories=dh["rubrics_required_categories"],
)


@app.get("/api/space-info")
def space_info() -> dict:
    """HF-Space-specific deploy info. Useful for verifying the Space
    is current."""
    return {
        "deployment": "hf_space",
        "provider": (
            "gemini" if os.getenv("GEMINI_API_KEY")
            else "openai-compat" if os.getenv("OPENAI_API_KEY")
            else "none-configured"
        ),
        "model": (
            os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            if os.getenv("GEMINI_API_KEY")
            else os.getenv("OPENAI_MODEL", "unset")
        ),
        "online_search_wired": online_search_call is not None,
        "git_sha": os.getenv("DUECARE_GIT_SHA", "unknown"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
