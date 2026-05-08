"""Default dense embedding loader for hybrid retrieval + caching.

Loads `sentence-transformers/all-MiniLM-L6-v2` on CPU (~80 MB,
~3 ms / sentence) for the chat package's `embed_call` hook. Wired
into the v0.8.0 hybrid retrieval mode (`retrieval_mode=hybrid_rrf`):
the BM25 first stage produces ~50 lexical candidates; the dense
embedder produces ~20 semantic candidates; the two lists are fused
via Reciprocal Rank Fusion before any rerank stage.

Why this model:
  - 80 MB, CPU-friendly. Loads in ~2 s on a Kaggle session, no GPU
    contention with the chat model.
  - 384-dim output — small enough that an in-memory FAISS index over
    ~1 K chunks fits in <2 MB.
  - Trained on a billion sentence pairs; strong on general semantic
    similarity. Specialized legal embeddings would help marginally
    on a 35-doc corpus but aren't worth the wheel weight.

Why not OpenAI / Cohere embeddings:
  - Network-bound + BYOK + per-call cost. The default should run
    offline. A kernel that wants paid embeddings can swap the hook
    by passing its own `embed_call` to `create_app`.

Implementation notes:
  - Uses `transformers` directly with mean-pooling — avoids adding
    `sentence-transformers` as a dep when the kernel already has
    `transformers` installed for Gemma.
  - Exposes the same `embed_call(texts)` signature regardless of
    backend so kernels can swap implementations transparently.
"""
from __future__ import annotations

import hashlib
import os
import sys
import threading
from collections import OrderedDict
from typing import Callable, Optional

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# v0.8.1: per-process embedding cache. The chat package re-embeds the
# RAG corpus + Import chunks on every chat send under hybrid_rrf
# retrieval mode — wasteful when the corpus is stable. Caching by
# content hash gives ~10x speed-up on repeat queries with no quality
# cost. LRU-bounded so a runaway upload can't blow process memory.
class EmbeddingCache:
    """Thread-safe LRU cache of (text_hash → embedding vector).

    Used by `wrap_embed_with_cache()` to memoize embed_call results.
    Invalidation is content-hash-keyed: any change to the underlying
    corpus that produces new text strings naturally misses the cache
    on the next call. The Import store calls `invalidate_corpus()` on
    add/evict so stale entries are scrubbed eagerly rather than lazily.
    """

    def __init__(self, max_entries: int = 50_000):
        self._max = int(max_entries)
        self._d: OrderedDict[str, list] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[list]:
        h = self.hash_text(text)
        with self._lock:
            v = self._d.get(h)
            if v is not None:
                # LRU bump
                self._d.move_to_end(h)
                self._stats["hits"] += 1
                return list(v)
            self._stats["misses"] += 1
            return None

    def put(self, text: str, vector: list) -> None:
        h = self.hash_text(text)
        with self._lock:
            self._d[h] = list(vector)
            self._d.move_to_end(h)
            while len(self._d) > self._max:
                self._d.popitem(last=False)
                self._stats["evictions"] += 1

    def invalidate_text(self, text: str) -> None:
        h = self.hash_text(text)
        with self._lock:
            self._d.pop(h, None)

    def invalidate_corpus(self, texts: list) -> int:
        """Drop all cache entries whose text hash matches anything in
        `texts`. Returns the number of evictions for diagnostics."""
        if not texts:
            return 0
        hashes = {self.hash_text(t) for t in texts}
        with self._lock:
            n = 0
            for h in list(self._d.keys()):
                if h in hashes:
                    self._d.pop(h, None)
                    n += 1
            return n

    def stats(self) -> dict:
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            return {
                **self._stats,
                "size":     len(self._d),
                "hit_rate": round(self._stats["hits"] / max(1, total) * 100, 1),
            }

    def clear(self) -> None:
        with self._lock:
            self._d.clear()
            self._stats = {k: 0 for k in self._stats}


def wrap_embed_with_cache(embed_call: Callable,
                              cache: Optional[EmbeddingCache] = None,
                              ) -> Callable:
    """Wrap an `embed_call(texts) -> vectors` with LRU caching.

    The wrapped callable preserves the original signature: still accepts
    a list of texts, still returns a list of vectors in the same order.
    Misses are batched into a single underlying embed_call so a request
    that's 90% cache-hits doesn't fragment into N tiny inference calls.
    """
    if cache is None:
        cache = EmbeddingCache()

    def _cached_embed(texts: list) -> list:
        if not texts:
            return []
        # Layer 1: collect hits + miss indices.
        results: list = [None] * len(texts)
        miss_idxs: list = []
        miss_texts: list = []
        for i, t in enumerate(texts):
            v = cache.get(t)
            if v is not None:
                results[i] = v
            else:
                miss_idxs.append(i)
                miss_texts.append(t)
        # Layer 2: single batched embed call for all misses.
        if miss_texts:
            try:
                fresh = embed_call(miss_texts)
            except Exception:  # noqa: BLE001
                # Fail open: return zeros for misses, hits stand. Caller's
                # downstream BM25 / RRF will degrade gracefully.
                fresh = [[0.0] * 384] * len(miss_texts)
            for j, idx in enumerate(miss_idxs):
                v = fresh[j] if j < len(fresh) else [0.0] * 384
                results[idx] = v
                cache.put(miss_texts[j], v)
        return results

    _cached_embed.__name__ = "embed_call_cached"   # type: ignore[attr-defined]
    _cached_embed.cache = cache                     # type: ignore[attr-defined]
    # Pass through the underlying model_name + dim if present so callers
    # introspecting attributes still work.
    for attr in ("model_name", "dim", "device"):
        if hasattr(embed_call, attr):
            setattr(_cached_embed, attr, getattr(embed_call, attr))
    return _cached_embed


def load_default_embedder(
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    device: str = "cpu",
    max_length: int = 256,
    batch_size: int = 16,
    quiet: bool = False,
) -> Optional[Callable]:
    """Return an `embed_call(texts: list[str]) -> list[list[float]]`
    callable or None on load failure.

    Output is a list of L2-normalized 384-dim float lists, suitable
    for cosine-similarity by dot product (ranked-list scoring used
    by the wheel's RRF fusion path).
    """
    if os.environ.get("DUECARE_DISABLE_EMBEDDER", "").strip() in ("1", "true", "yes"):
        if not quiet:
            print("[embedder] disabled via DUECARE_DISABLE_EMBEDDER env",
                  file=sys.stderr)
        return None
    try:
        import torch  # type: ignore
        from transformers import AutoModel, AutoTokenizer  # type: ignore
    except ImportError as e:
        if not quiet:
            print(f"[embedder] transformers/torch unavailable; embedder disabled: {e}",
                  file=sys.stderr)
        return None
    try:
        if not quiet:
            print(f"[embedder] loading {model_name} on {device} …",
                  file=sys.stderr)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        model = model.to(device)
        model.eval()
    except Exception as e:  # noqa: BLE001
        if not quiet:
            print(f"[embedder] load failed; embedder disabled: {e}", file=sys.stderr)
        return None
    if not quiet:
        print(f"[embedder] ready ({model_name}); ~80 MB RAM, ~3 ms / sentence",
              file=sys.stderr)

    def _mean_pool(last_hidden_state, attention_mask):
        # Standard mean-pooling: weight by attention mask, sum, divide
        # by mask sum. Matches the sentence-transformers default for
        # all-MiniLM-L6-v2.
        mask = attention_mask.unsqueeze(-1).float()
        summed = (last_hidden_state * mask).sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1e-9)
        return summed / counts

    def _embed_call(texts: list) -> list:
        """Encode a list of strings to L2-normalized 384-dim vectors."""
        if not texts:
            return []
        out: list = []
        try:
            with torch.inference_mode():
                for start in range(0, len(texts), batch_size):
                    batch = [str(t)[:max_length * 4] for t in texts[start:start + batch_size]]
                    inputs = tokenizer(
                        batch, padding=True, truncation=True,
                        max_length=max_length, return_tensors="pt",
                    ).to(device)
                    last_hidden = model(**inputs).last_hidden_state
                    pooled = _mean_pool(last_hidden, inputs["attention_mask"])
                    # L2-normalize so cosine similarity == dot product.
                    pooled = pooled / pooled.norm(dim=1, keepdim=True).clamp(min=1e-9)
                    out.extend(pooled.cpu().tolist())
        except Exception as e:  # noqa: BLE001
            if not quiet:
                print(f"[embedder] inference failed: {e}", file=sys.stderr)
            return [[0.0] * 384] * len(texts)
        return out

    _embed_call.__name__ = "embed_call"
    _embed_call.model_name = model_name      # type: ignore[attr-defined]
    _embed_call.dim = 384                     # type: ignore[attr-defined]
    _embed_call.device = device               # type: ignore[attr-defined]
    return _embed_call


def reciprocal_rank_fusion(ranked_lists: list, *, k: int = 60) -> list:
    """RRF fusion of multiple ranked lists. Each list is a list of
    items where each item has an `id` field (or a stable identifier
    callable extractor). Items in higher-ranked positions across
    multiple input lists score highest.

    Standard RRF formula: score(d) = sum over lists of 1 / (k + rank_in_list).
    k=60 is the canonical default from the original RRF paper.

    Returns the input items deduplicated by id, sorted by RRF score
    descending, with `rrf_score` annotated.
    """
    accum: dict[str, float] = {}
    seen: dict[str, dict] = {}
    for lst in ranked_lists:
        if not lst:
            continue
        for rank, item in enumerate(lst, start=1):
            key = item.get("id")
            if not key:
                continue
            accum[key] = accum.get(key, 0.0) + 1.0 / (k + rank)
            seen.setdefault(key, item)
    fused = []
    for key, score in sorted(accum.items(), key=lambda kv: -kv[1]):
        item = dict(seen[key])
        item["rrf_score"] = round(float(score), 6)
        fused.append(item)
    return fused
