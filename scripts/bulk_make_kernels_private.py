"""Bulk-make Kaggle kernels private. Keeps a small whitelist public.

For each kernel: pull to a temp dir, flip is_private=True in
kernel-metadata.json, push back. Slow (~20-30s per kernel) but
required because the Kaggle API has no direct "set visibility"
endpoint -- everything is via metadata + push.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault(
    "KAGGLE_API_TOKEN",
    "KGAT_60334d61220fab3203911577dc47b268",
)

from kaggle.api.kaggle_api_extended import KaggleApi

KEEP_PUBLIC = {
    "taylorsamarel/duecare-live-demo",
}

api = KaggleApi()
api.authenticate()

# Find all DueCare kernels via search
res = api.kernels_list(search="duecare", page_size=50)
all_dc = [k for k in res]
to_priv = [k for k in all_dc if k.ref not in KEEP_PUBLIC]

print(f"Found {len(all_dc)} DueCare kernels")
print(f"KEEP public ({len(KEEP_PUBLIC)}): {sorted(KEEP_PUBLIC)}")
print(f"Will MAKE PRIVATE: {len(to_priv)}")
print()

tmp_root = Path("/tmp/kaggle_priv_tmp")
tmp_root.mkdir(parents=True, exist_ok=True)

ok, fail, skip = 0, 0, 0
for i, k in enumerate(to_priv, 1):
    slug = k.ref.split("/", 1)[1]
    tmp = tmp_root / slug
    print(f"[{i}/{len(to_priv)}] {k.ref}")
    try:
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        api.kernels_pull(k.ref, path=str(tmp), metadata=True)
        meta_path = tmp / "kernel-metadata.json"
        if not meta_path.exists():
            print(f"  SKIP -- no kernel-metadata.json after pull")
            skip += 1
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("is_private") is True:
            print(f"  ALREADY private -- skipping push")
            skip += 1
            continue
        meta["is_private"] = True
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        api.kernels_push(folder=str(tmp))
        print(f"  OK -- pushed as private")
        ok += 1
        # Throttle to avoid 429s
        time.sleep(2.0)
    except Exception as e:
        msg = str(e)[:300]
        print(f"  FAIL -- {type(e).__name__}: {msg}")
        fail += 1
        time.sleep(3.0)

print()
print(f"=== DONE: ok={ok}, fail={fail}, skipped={skip} ===")
