"""Offline Drive enumerator + prioritization.

Walks the Google Drive tree for the configured root folders, capturing
METADATA ONLY (no file bytes downloaded). Scores every folder and
every file by likelihood of producing good network-graph entities,
then writes:

    data/drive_manifest.json         -- full (id, name, path, mime, size, scores)
    data/drive_manifest_summary.md   -- human-readable report
    data/drive_curated_file_ids.json -- top-N file IDs to download on Kaggle

Usage:
    # Set GOOGLE_DRIVE_API_KEY first (or edit the fallback below).
    python scripts/_enumerate_drive_folders.py

    # Custom folders + smaller budget:
    python scripts/_enumerate_drive_folders.py \\
        --folders 1p0D6tMznPos...,1iL7HJODAt... \\
        --max-folders 200 --max-files-per-bundle 30 \\
        --curate-top 400
"""
from __future__ import annotations

import argparse
import heapq
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = REPO_ROOT / "data" / "drive_manifest.json"
OUT_SUMMARY = REPO_ROOT / "data" / "drive_manifest_summary.md"
OUT_CURATED = REPO_ROOT / "data" / "drive_curated_file_ids.json"

# -----------------------------------------------------------------------------
#  Scoring (mirrors the logic in gemma4_multimodal_with_rag_grep_v1.py)
# -----------------------------------------------------------------------------
FOLDER_POS = {
    "recruitment": 30, "agency": 30, "manpower": 25,
    "employment": 20, "contractor": 20, "placement": 20,
    "passport": 25, "visa": 25, "contract": 22,
    "receipt": 18, "remittance": 18, "fee": 16,
    "id ": 18, "license": 15, "certificate": 15,
    "affidavit": 20, "witness": 22, "case": 20,
    "complaint": 22, "sworn": 18, "statement": 16,
    "letter": 14, "poea": 25, "pcg": 20, "polo": 20,
    "dole": 20, "nbi": 20,
    "whatsapp": 15, "screenshot": 14, "chat": 14,
    "message": 12, "sms": 12,
    "philippines": 12, "saudi": 12, "uae": 12, "dubai": 12,
    "kuwait": 12, "qatar": 12, "bahrain": 12, "oman": 12,
    "nepal": 12, "bangladesh": 12, "indonesia": 12,
}
FOLDER_NEG = {
    "trash": -30, "deleted": -25, "old": -10, "backup": -10,
    "archive": -5, "draft": -5, "temp": -10, "test": -10,
    "misc": -10, "duplicate": -15, "copy": -5,
}
FILE_POS = {
    "contract": 40, "agreement": 35, "letter": 30,
    "complaint": 40, "affidavit": 40, "sworn": 35,
    "statement": 30, "witness": 45, "information": 25,
    "receipt": 25, "remittance": 25, "invoice": 20,
    "passport": 30, "visa": 25, "id_card": 20,
    "certificate": 25, "license": 20,
    "poea": 30, "pcg": 25, "polo": 25, "dole": 25, "nbi": 25,
    "report": 25, "application": 20, "manifest": 18,
    "form": 18, "intake": 25, "disclosure": 25,
    "chat": 22, "whatsapp": 22, "messenger": 20, "sms": 18,
}
FILE_NEG = {
    "thumbnail": -25, "thumb": -15, "preview": -10, "cover": -5,
    "avatar": -20, "profile": -15, "selfie": -20, "icon": -20,
    "logo": -10, "blank": -10, "untitled": -15,
    "img_": -5, "dscn": -5, "dsc_": -5,
}
MIME_WEIGHTS = {
    "application/pdf":       35,
    "application/msword":    30,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 30,
    "text/plain":            25,
    "application/vnd.google-apps.document": 30,
    "image/png":             15,
    "image/jpeg":            15,
    "image/webp":            15,
    "image/tiff":            18,
    "image/gif":              8,
    "video/mp4":             -10,
    "video/quicktime":       -10,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": -5,
    "application/vnd.google-apps.spreadsheet": -5,
}

FOLDER_MIME = "application/vnd.google-apps.folder"


def folder_score(name: str) -> int:
    lo = (name or "").lower()
    s = 0
    for k, w in FOLDER_POS.items():
        if k in lo:
            s += w
    for k, w in FOLDER_NEG.items():
        if k in lo:
            s += w
    return s


def file_score(name: str, mime: str, size: int) -> int:
    lo = (name or "").lower()
    s = 0
    for k, w in FILE_POS.items():
        if k in lo:
            s += w
    for k, w in FILE_NEG.items():
        if k in lo:
            s += w
    s += MIME_WEIGHTS.get(mime, 0)
    if size > 0:
        if size < 8_000:
            s -= 20
        elif size < 30_000:
            s -= 5
        elif size > 20_000_000:
            s -= 15
        elif 50_000 <= size <= 3_000_000:
            s += 5
    return s


# -----------------------------------------------------------------------------
#  Drive API walker
# -----------------------------------------------------------------------------

@dataclass
class Node:
    id: str
    name: str
    mime: str
    size: int
    parent_id: str
    root_id: str
    bundle: str
    path: str
    depth: int
    score: int
    is_folder: bool


def extract_fid(raw: str) -> str:
    m = (re.search(r"/folders/([a-zA-Z0-9_-]+)", raw)
         or re.search(r"/file/d/([a-zA-Z0-9_-]+)", raw))
    return m.group(1) if m else raw


def walk_tree(service, root_ids: list, drill_ids: set,
              max_folders: int, max_depth: int,
              max_files_per_bundle: int,
              verbose: bool = True) -> list:
    """BFS walker over the configured roots. Returns a flat list of Node."""
    nodes: list = []
    visited: set = set()
    # Priority queue: (neg_priority, seq, folder_id, name, path, depth,
    #                   root_id, bundle, parent_id)
    pq: list = []
    seq = 0
    folders_seen = 0

    # Drill expansion: replace drill-listed root IDs with their immediate
    # subfolders so each sub-case gets its own budget in the main walk.
    effective_roots: list = []
    for rid in root_ids:
        if rid in drill_ids:
            try:
                resp = service.files().list(
                    q=(f"'{rid}' in parents and mimeType='{FOLDER_MIME}' "
                       f"and trashed=false"),
                    fields="files(id,name)", pageSize=1000,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                ).execute()
                subs = resp.get("files", [])
                if verbose:
                    print(f"[enum] drill {rid[:10]}... -> "
                          f"{len(subs)} subfolders")
                for s in subs:
                    effective_roots.append((s["id"], s.get("name", rid)))
            except Exception as e:
                if verbose:
                    print(f"[enum] drill {rid[:10]}... FAIL "
                          f"({type(e).__name__}: {e}); keeping parent")
                effective_roots.append((rid, rid))
        else:
            effective_roots.append((rid, rid))

    for rid, rname in effective_roots:
        heapq.heappush(pq, (-9999, seq := seq + 1,
                             rid, rname, rname, 0, rid, rname, ""))
        nodes.append(Node(
            id=rid, name=rname, mime=FOLDER_MIME, size=0,
            parent_id="", root_id=rid, bundle=rname,
            path=rname, depth=0, score=folder_score(rname),
            is_folder=True,
        ))

    while pq and folders_seen < max_folders:
        neg_p, _, fid, fname, fpath, fdepth, rid, bundle, _ = heapq.heappop(pq)
        if fid in visited:
            continue
        visited.add(fid)
        folders_seen += 1

        # List ALL children (folders + files) with pagination
        page = None
        children_folders: list = []
        children_files: list = []
        while True:
            try:
                resp = service.files().list(
                    q=f"'{fid}' in parents and trashed=false",
                    fields=("nextPageToken, files(id, name, mimeType, "
                            "size, modifiedTime)"),
                    pageSize=1000,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageToken=page,
                ).execute()
            except Exception as e:
                if verbose:
                    print(f"[enum] list FAIL {fid[:10]}...: "
                          f"{type(e).__name__}: {e}")
                break
            for f in resp.get("files", []):
                if f.get("mimeType") == FOLDER_MIME:
                    children_folders.append(f)
                else:
                    children_files.append(f)
            page = resp.get("nextPageToken")
            if not page:
                break

        # At depth 0, the folder itself IS the bundle. At deeper levels,
        # the bundle inherits from the parent (first meaningful subfolder).
        if fdepth == 1 and bundle == rid:
            # the first real subfolder under the root becomes the bundle
            bundle = fname

        # Rank + add files
        files_sorted = sorted(
            children_files,
            key=lambda f: -file_score(
                f.get("name", ""), f.get("mimeType", ""),
                int(f.get("size") or 0)),
        )
        for i, f in enumerate(files_sorted):
            if i >= max_files_per_bundle:
                break
            fsize = int(f.get("size") or 0)
            fmime = f.get("mimeType", "")
            fname_c = f.get("name") or f["id"]
            nodes.append(Node(
                id=f["id"], name=fname_c, mime=fmime,
                size=fsize, parent_id=fid, root_id=rid, bundle=bundle,
                path=f"{fpath}/{fname_c}", depth=fdepth + 1,
                score=file_score(fname_c, fmime, fsize),
                is_folder=False,
            ))

        # Queue subfolders (if under depth cap)
        if fdepth < max_depth:
            for sf in children_folders:
                sf_name = sf.get("name") or sf["id"]
                sf_prio = folder_score(sf_name)
                sf_path = f"{fpath}/{sf_name}"
                # Bundle for child: if we're at the root, child becomes
                # the bundle; else inherit.
                sf_bundle = sf_name if fdepth == 0 else bundle
                seq += 1
                heapq.heappush(pq, (-sf_prio, seq, sf["id"], sf_name,
                                     sf_path, fdepth + 1, rid,
                                     sf_bundle, fid))
                nodes.append(Node(
                    id=sf["id"], name=sf_name, mime=FOLDER_MIME,
                    size=0, parent_id=fid, root_id=rid,
                    bundle=sf_bundle, path=sf_path,
                    depth=fdepth + 1, score=sf_prio, is_folder=True,
                ))

        if verbose and folders_seen % 25 == 0:
            n_files = sum(1 for n in nodes if not n.is_folder)
            print(f"[enum] walked {folders_seen:>4} folders, "
                  f"captured {n_files:>5} files, queue={len(pq)}")

    return nodes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders",
                    default=("1p0D6tMznPosAeXk486O7NNMua24nGC_6,"
                             "1JSy_xNvUOItuV2go1A-4TIvG4aAsA4mr,"
                             "1soev7vNpF-ACwWR4NrjD3S89U3GA4TpK,"
                             "1iL7HJODAtDkXKLlW8weZJhPNHKdHM_tV,"
                             "13qz3AFTHLczRw1-wrNoSomWiHvjLCndE"))
    ap.add_argument("--drill",
                    default="1soev7vNpF-ACwWR4NrjD3S89U3GA4TpK",
                    help="Comma-separated folder IDs whose subfolders "
                         "should each be treated as independent roots.")
    ap.add_argument("--max-folders", type=int, default=800,
                    help="Cap on total folders enumerated across all roots")
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--max-files-per-bundle", type=int, default=80,
                    help="Max files captured per leaf folder (bundle)")
    ap.add_argument("--curate-top", type=int, default=500,
                    help="How many top-scored files to write to "
                         "drive_curated_file_ids.json")
    ap.add_argument("--api-key",
                    default=os.environ.get("GOOGLE_DRIVE_API_KEY",
                                            "AIzaSyCJ3BJkAEjHG5XMuWkJtSFwCPHvk3h9RJA"))
    args = ap.parse_args()

    if not args.api_key:
        print("[enum] no API key set; aborting")
        return 1
    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("[enum] pip install google-api-python-client")
        return 1

    svc = build("drive", "v3", developerKey=args.api_key,
                cache_discovery=False)
    root_ids = [extract_fid(r) for r in args.folders.split(",") if r.strip()]
    drill_ids = {extract_fid(d) for d in args.drill.split(",") if d.strip()}

    print(f"[enum] roots   = {len(root_ids)}")
    print(f"[enum] drill   = {len(drill_ids)}")
    print(f"[enum] budgets = <= {args.max_folders} folders, "
          f"depth <= {args.max_depth}, "
          f"<= {args.max_files_per_bundle}/bundle")

    t0 = time.time()
    nodes = walk_tree(svc, root_ids, drill_ids,
                      max_folders=args.max_folders,
                      max_depth=args.max_depth,
                      max_files_per_bundle=args.max_files_per_bundle)
    elapsed = time.time() - t0
    print(f"[enum] done in {elapsed:.1f}s")

    # ---- Write full manifest
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps([asdict(n) for n in nodes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[enum] wrote {OUT_JSON} ({len(nodes)} nodes)")

    files = [n for n in nodes if not n.is_folder]
    folders = [n for n in nodes if n.is_folder]
    bundle_files: dict = defaultdict(list)
    for f in files:
        bundle_files[f.bundle].append(f)

    # ---- Curated top-N: balance by bundle so no single bundle dominates
    per_bundle_cap = max(1, args.curate_top // max(1, len(bundle_files)))
    per_bundle_cap = max(per_bundle_cap, 10)
    curated: list = []
    for b, flist in bundle_files.items():
        flist_sorted = sorted(flist, key=lambda n: -n.score)
        curated.extend(flist_sorted[:per_bundle_cap])
    curated.sort(key=lambda n: -n.score)
    curated = curated[:args.curate_top]
    OUT_CURATED.write_text(
        json.dumps([
            {"id": n.id, "name": n.name, "mime": n.mime, "size": n.size,
             "bundle": n.bundle, "score": n.score, "path": n.path}
            for n in curated
        ], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[enum] wrote {OUT_CURATED} ({len(curated)} curated file IDs)")

    # ---- Human-readable summary
    text_count = sum(1 for n in files
                     if n.mime.startswith("application/pdf")
                     or n.mime.startswith("application/msword")
                     or "wordprocessing" in n.mime
                     or "google-apps.document" in n.mime
                     or n.mime == "text/plain")
    image_count = sum(1 for n in files if n.mime.startswith("image/"))
    total_size_mb = sum(n.size for n in files) / (1024 * 1024)

    top_bundles = sorted(bundle_files.items(),
                         key=lambda kv: (-len(kv[1]), kv[0]))[:20]
    md: list = [
        "# Drive enumeration summary",
        "",
        f"- Enumerated: **{len(folders)} folders**, **{len(files)} files**",
        f"- Elapsed: {elapsed:.1f}s",
        f"- Total size: {total_size_mb:.1f} MB",
        f"- Text-bearing docs (PDF/DOC/TXT): {text_count}",
        f"- Image docs: {image_count}",
        f"- Distinct bundles: {len(bundle_files)}",
        "",
        "## Top bundles by file count",
        "",
        "| files | bundle |",
        "|---:|---|",
    ]
    for b, flist in top_bundles:
        md.append(f"| {len(flist)} | `{b[:80]}` |")
    md.extend([
        "",
        f"## Top 30 curated files (by graph-entity score, bundle-balanced)",
        "",
        "| score | mime | size KB | bundle | name |",
        "|---:|---|---:|---|---|",
    ])
    for n in curated[:30]:
        mime_short = n.mime.split("/")[-1][:10]
        size_kb = f"{n.size/1024:.0f}" if n.size else "?"
        md.append(f"| {n.score} | {mime_short} | {size_kb} | "
                  f"`{n.bundle[:40]}` | `{n.name[:60]}` |")
    OUT_SUMMARY.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[enum] wrote {OUT_SUMMARY}")

    # ---- Console summary
    print("")
    print(f"=== CORPUS SUMMARY ===")
    print(f"  folders enumerated: {len(folders)}")
    print(f"  files captured    : {len(files)}")
    print(f"  distinct bundles  : {len(bundle_files)}")
    print(f"  text-bearing docs : {text_count}")
    print(f"  image docs        : {image_count}")
    print(f"  curated top-N     : {len(curated)}")
    print("")
    print(f"  top 10 bundles:")
    for b, flist in top_bundles[:10]:
        print(f"    {len(flist):>4}  {b[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
