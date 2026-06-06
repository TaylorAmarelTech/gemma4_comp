"""Harvest document URLs from the sitemap/robots seed queue to expand the
acquisition frontier toward the 10k-doc goal.

Reads the research_spider sitemap probe queue (sitemap-index / sitemap /
robots.txt URLs for known-good gov/NGO domains), walks each via the sitemap
harvester, and writes candidate rows (the schema run_acquisition.py consumes)
to reports/acquisition/ (gitignored). Per-seed cap keeps domain coverage
balanced; a denylist drops obvious non-content (tags, feeds, assets).

Env knobs:
  HARVEST_SEEDS    seeds .jsonl (default: research_spider/sitemap_probe_queue.jsonl)
  HARVEST_OUT      candidates out (default: reports/acquisition/harvested_candidates.jsonl)
  HARVEST_PER_SEED max docs per seed domain (default 80)
  HARVEST_TOTAL    total cap across all seeds (default 4000)
  HARVEST_TIMEOUT  per-fetch timeout seconds (default 20)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in sorted((ROOT / "packages").glob("*/src")):
    sys.path.insert(0, str(_p))

from duecare.research_tools.monitor import default_fetch  # noqa: E402
from duecare.research_tools.sitemap import harvest  # noqa: E402

SEEDS = Path(os.environ.get(
    "HARVEST_SEEDS",
    ROOT / "configs/duecare/benchmarks/research_spider/sitemap_probe_queue.jsonl"))
OUT = Path(os.environ.get("HARVEST_OUT", ROOT / "reports/acquisition/harvested_candidates.jsonl"))
PER_SEED = int(os.environ.get("HARVEST_PER_SEED", "80"))
TOTAL = int(os.environ.get("HARVEST_TOTAL", "4000"))
TIMEOUT = float(os.environ.get("HARVEST_TIMEOUT", "20"))

_DENY = ("/tag/", "/tags/", "/category/", "/categories/", "/author/", "/wp-json",
         "/feed", "/comments", "/login", "/search", "/privacy", "/cookie", "/terms",
         "/sitemap", "/rss", "/contact", "javascript:", "mailto:", ".css", ".js",
         ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".zip", ".mp4", ".mp3")


def _keep(u: str) -> bool:
    ul = (u or "").lower()
    return ul.startswith("http") and not any(d in ul for d in _DENY)


def _load_jsonl(p: Path) -> list[dict]:
    out: list[dict] = []
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seeds = _load_jsonl(SEEDS)
    seeds.sort(key=lambda d: d.get("priority", 0), reverse=True)
    print(f"[harvest] seeds={len(seeds)} per_seed={PER_SEED} total_cap={TOTAL}", flush=True)

    def fetch(url: str):
        return default_fetch(url, timeout=TIMEOUT)

    seen_urls: set[str] = set()
    candidates: list[dict] = []
    for i, s in enumerate(seeds):
        seed_url = s.get("url")
        if not seed_url:
            continue
        docs, stats = harvest([seed_url], fetch=fetch, max_depth=2,
                              max_docs=PER_SEED, max_fetches=40, url_filter=_keep)
        tier = (s.get("source_families") or ["harvested"])[0]
        jur = s.get("jurisdictions") or []
        sig = s.get("top_signals") or []
        for u in docs:
            if u in seen_urls:
                continue
            seen_urls.add(u)
            candidates.append({
                "id": "HARV-" + hashlib.sha1(u.encode("utf-8")).hexdigest()[:12].upper(),
                "url": u, "title": None, "source_tier": tier,
                "jurisdictions": jur, "signals": sig, "harvested_from": seed_url,
            })
        if (i + 1) % 20 == 0 or len(candidates) >= TOTAL:
            print(f"[harvest] seed {i + 1}/{len(seeds)} domain={s.get('domain')} "
                  f"+{stats['docs']} docs (total candidates={len(candidates)})", flush=True)
        if len(candidates) >= TOTAL:
            print(f"[harvest] reached total cap {TOTAL}; stopping seed walk.", flush=True)
            break

    with open(OUT, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"[harvest] DONE wrote {len(candidates)} candidates -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
