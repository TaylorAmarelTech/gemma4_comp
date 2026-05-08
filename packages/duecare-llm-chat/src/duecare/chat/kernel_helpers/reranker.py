"""Default cross-encoder reranker loader.

Loads `mixedbread-ai/mxbai-rerank-xsmall-v1` on CPU (~70 MB, ~50 ms
for 20 candidates) so the chat package's `rerank_call` hook can be
wired without each kernel.py reinventing the transformers boilerplate.

Why this model:
  - 70 MB on disk, fits in process memory next to a 6 GB Gemma without
    GPU contention.
  - Cross-encoder architecture: scores `(query, candidate)` pairs jointly,
    which beats two-tower dense retrieval on legal/statutory text per the
    public benchmarks.
  - Pure CPU forward pass — no contention with the chat model on the GPU.
  - MIT-licensed; no API key required.

Why not BGE-rerank-v2-m3:
  - 568 MB on disk, peaks ~2 GB during inference. On a Kaggle T4 with
    Gemma 4 E4B already loaded (~6 GB), risks OOM.

Why not Cohere rerank-3.5:
  - Best accuracy on legal text per Cohere's public benchmarks but
    requires a BYOK + a network call (~100 ms RTT). Out-of-scope for
    the default; can be wired as `rerank_call=cohere_rerank` by a
    kernel that needs it.
"""
from __future__ import annotations

import os
import sys
from typing import Callable, Optional

DEFAULT_MODEL_NAME = "mixedbread-ai/mxbai-rerank-xsmall-v1"


def load_default_reranker(
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    device: str = "cpu",
    max_length: int = 512,
    quiet: bool = False,
) -> Optional[Callable]:
    """Return a `rerank_call(query, candidates) -> list[dict]` callable
    or None when the load fails (missing transformers / torch / network).

    The returned callable is safe to call concurrently — each request
    runs the model with `torch.inference_mode()` and a CPU-side forward
    pass.
    """
    if os.environ.get("DUECARE_DISABLE_RERANKER", "").strip() in ("1", "true", "yes"):
        if not quiet:
            print("[reranker] disabled via DUECARE_DISABLE_RERANKER env",
                  file=sys.stderr)
        return None
    try:
        import torch  # type: ignore
        from transformers import AutoModelForSequenceClassification, AutoTokenizer  # type: ignore
    except ImportError as e:
        if not quiet:
            print(f"[reranker] transformers/torch unavailable; rerank disabled: {e}",
                  file=sys.stderr)
        return None
    try:
        if not quiet:
            print(f"[reranker] loading {model_name} on {device} …",
                  file=sys.stderr)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model = model.to(device)
        model.eval()
    except Exception as e:  # noqa: BLE001
        if not quiet:
            print(f"[reranker] load failed; rerank disabled: {e}", file=sys.stderr)
        return None
    if not quiet:
        print(f"[reranker] ready ({model_name}); ~70 MB RAM, ~50 ms / 20 candidates",
              file=sys.stderr)

    def _rerank_call(query: str, candidates: list, top_k: Optional[int] = None) -> list:
        """Score (query, candidate) pairs and return candidates sorted
        by descending rerank_score. Each returned dict has a
        `rerank_score` field added (or overwritten). Candidates with
        no `text` AND no `snippet` are passed through unscored.
        """
        if not candidates:
            return candidates
        # Extract candidate texts. Both `text` and `snippet` are normalized
        # at the chat-package call site (v0.7.1) so either should be set;
        # we accept both for robustness against external callers.
        pairs = []
        idxs = []
        for i, c in enumerate(candidates):
            txt = (c.get("text") or c.get("snippet") or "").strip()
            if not txt:
                continue
            pairs.append((query, txt))
            idxs.append(i)
        if not pairs:
            return candidates
        try:
            with torch.inference_mode():
                inputs = tokenizer(
                    [q for q, _ in pairs],
                    [t for _, t in pairs],
                    padding=True, truncation=True,
                    max_length=max_length,
                    return_tensors="pt",
                ).to(device)
                logits = model(**inputs).logits.view(-1).cpu().tolist()
        except Exception as e:  # noqa: BLE001
            # Run-time failure (OOM mid-batch, tokenizer issue, etc.) —
            # don't tank the whole retrieval; preserve BM25 order.
            if not quiet:
                print(f"[reranker] inference failed, BM25 order preserved: {e}",
                      file=sys.stderr)
            return candidates
        # Apply scores back to candidate indices.
        score_by_idx = {idx: float(s) for idx, s in zip(idxs, logits)}
        out = []
        for i, c in enumerate(candidates):
            c2 = dict(c)
            c2["rerank_score"] = score_by_idx.get(i, 0.0)
            out.append(c2)
        out.sort(key=lambda c: -c.get("rerank_score", 0.0))
        if top_k is not None:
            out = out[:max(1, int(top_k))]
        return out

    _rerank_call.__name__ = "rerank_call"
    _rerank_call.model_name = model_name  # type: ignore[attr-defined]
    _rerank_call.device = device          # type: ignore[attr-defined]
    return _rerank_call
