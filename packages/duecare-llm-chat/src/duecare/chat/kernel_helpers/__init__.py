"""Reusable kernel-side helpers for Duecare chat notebooks.

Every kernel that runs the chat package faces the same boilerplate:
load Gemma, optionally load a reranker, optionally load an embedder,
wire search, run the FastAPI server. Without this module each
kernel.py copy-pastes ~50 lines of model-loading code; with it,
adoption is three import lines.

Design rules:

  - **Lazy imports.** Heavy deps (`transformers`, `torch`,
    `sentence_transformers`) are imported INSIDE each loader, not at
    module load time. A kernel that doesn't need a reranker doesn't
    pay the import cost.
  - **Graceful skip.** When a dep is missing or the model fails to
    load (typical on a Kaggle session that pinned an older torch),
    each loader logs a one-line warning and returns `None`. The
    create_app hook then sees `None` and uses BM25 fallbacks.
  - **Match the create_app contract.** `load_default_reranker()`
    returns a callable matching `rerank_call(query, candidates) -> list[dict]`.
    `load_default_embedder()` returns a callable matching
    `embed_call(texts: list[str]) -> list[list[float]]`.

Usage in a kernel.py:

    from duecare.chat import create_app
    from duecare.chat.kernel_helpers import (
        load_default_reranker, load_default_embedder,
    )

    rerank = load_default_reranker()    # None if transformers absent
    embed  = load_default_embedder()    # None if dep missing

    app = create_app(
        gemma_call=loaded.backend,
        rerank_call=rerank,
        embed_call=embed,
        ...,
    )
"""
from __future__ import annotations

from .reranker  import load_default_reranker
from .embedding import (
    load_default_embedder,
    reciprocal_rank_fusion,
    EmbeddingCache,
    wrap_embed_with_cache,
)

import os as _os
import sys as _sys


def default_optional_hooks(*,
                              rerank: Optional[bool] = None,  # type: ignore[name-defined]
                              embed:  Optional[bool] = None,  # type: ignore[name-defined]
                              quiet: bool = False,
                              cache_size: Optional[int] = None,
                              ) -> dict:
    """One-call wiring of the optional `rerank_call` + `embed_call`
    hooks that `create_app` accepts.

    Returns a dict ready to spread into create_app kwargs:

        from duecare.chat import create_app
        from duecare.chat.kernel_helpers import default_optional_hooks
        app = create_app(gemma_call=..., **default_optional_hooks(),
                         **default_harness())

    Each hook is opt-in via env var (defaults match the primary
    01-duecare-harness-chat kernel — reranker ON, embedder OFF since
    embed adds 80 MB and most kernels stay on pure BM25 retrieval).

    Args:
        rerank: explicit override for ENABLE_RERANKER. None = read env.
        embed:  explicit override for ENABLE_EMBEDDER.  None = read env.
        quiet:  suppress per-loader status prints to stderr.
        cache_size: override DUECARE_EMBED_CACHE_SIZE (default 50_000).

    Env vars:
        ENABLE_RERANKER=1|0          (default: 1)
        ENABLE_EMBEDDER=1|0          (default: 0)
        DUECARE_DISABLE_RERANKER=1   (hard kill switch)
        DUECARE_DISABLE_EMBEDDER=1   (hard kill switch)
        DUECARE_EMBED_CACHE_SIZE=N   (default: 50000)

    Returns:
        {"rerank_call": <callable or None>,
         "embed_call":  <callable or None>}
        Keys with None values are still included so the caller can
        distinguish "intentionally unwired" from "missing key".
    """
    out: dict = {"rerank_call": None, "embed_call": None}

    enable_rerank = (_os.environ.get("ENABLE_RERANKER", "1") == "1"
                       if rerank is None else bool(rerank))
    if enable_rerank:
        try:
            rr = load_default_reranker(quiet=quiet)
            if rr is not None:
                out["rerank_call"] = rr
                if not quiet:
                    print(f"[kernel_helpers] reranker wired ({rr.model_name})",
                          file=_sys.stderr)
        except Exception as e:  # noqa: BLE001
            if not quiet:
                print(f"[kernel_helpers] reranker unavailable: {e}",
                      file=_sys.stderr)

    enable_embed = (_os.environ.get("ENABLE_EMBEDDER", "0") == "1"
                      if embed is None else bool(embed))
    if enable_embed:
        try:
            em_raw = load_default_embedder(quiet=quiet)
            if em_raw is not None:
                size = (cache_size if cache_size is not None
                        else int(_os.environ.get("DUECARE_EMBED_CACHE_SIZE", "50000")))
                em = wrap_embed_with_cache(em_raw, EmbeddingCache(max_entries=size))
                out["embed_call"] = em
                if not quiet:
                    print(f"[kernel_helpers] embedder wired ({em.model_name}, "
                          f"{em.dim}-dim, cache={size})", file=_sys.stderr)
        except Exception as e:  # noqa: BLE001
            if not quiet:
                print(f"[kernel_helpers] embedder unavailable: {e}",
                      file=_sys.stderr)

    return out


from typing import Optional  # placed late to avoid circular at runtime

__all__ = [
    "load_default_reranker",
    "load_default_embedder",
    "reciprocal_rank_fusion",
    "EmbeddingCache",
    "wrap_embed_with_cache",
    "default_optional_hooks",
]
