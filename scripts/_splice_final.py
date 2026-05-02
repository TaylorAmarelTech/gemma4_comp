"""Final splice: embed the latest waterfall outputs into the builder.
Run after waterfall + OCR complete."""
from __future__ import annotations

import base64
import gzip
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def make_blob(data: list) -> tuple[str, int]:
    raw = json.dumps(data, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    gz = gzip.compress(raw, 9)
    b64 = base64.b64encode(gz).decode("ascii")
    chunks = [b64[i:i + 72] for i in range(0, len(b64), 72)]
    return "(\n" + "\n".join(f'    "{c}"' for c in chunks) + "\n)", len(b64)


def main() -> int:
    hyp = json.loads(
        (REPO / "data" / "drive_hypothesis_edges.json").read_text(
            encoding="utf-8"))
    curated = json.loads(
        (REPO / "data" / "drive_curated_file_ids.json").read_text(
            encoding="utf-8"))
    clusters = json.loads(
        (REPO / "data" / "drive_doc_clusters.json").read_text(
            encoding="utf-8"))

    # Build fid -> cluster-size map, deprioritize mega templates
    fid_cluster = {}
    cluster_size = {}
    for c in clusters:
        cluster_size[c["cluster_id"]] = c["size"]
        for fid in c["file_ids"]:
            fid_cluster[fid] = c["cluster_id"]

    final_curated: list = []
    for e in curated:
        clu = fid_cluster.get(e["id"], -1)
        sz = cluster_size.get(clu, 1)
        if sz >= 80:
            penalty = -30
        elif sz >= 20:
            penalty = -8
        elif sz == 1:
            penalty = 0
        else:
            penalty = 8
        final_curated.append({
            "id": e["id"], "name": e["name"], "mime": e["mime"],
            "size": e.get("size", 0),
            "bundle": e["bundle"],
            "score": e.get("score", 0) + penalty,
        })
    final_curated.sort(key=lambda e: -e["score"])
    final_curated = final_curated[:450]
    b_set = {e["bundle"] for e in final_curated}
    print(f"final curated: {len(final_curated)} entries, {len(b_set)} bundles")

    hyp_slim = [{
        "a_type": h["a_type"], "a_value": h["a_value"],
        "b_type": h["b_type"], "b_value": h["b_value"],
        "relation_guess": h["relation_guess"],
        "n_docs": h["n_docs"], "n_bundles": h["n_bundles"],
        "bundles": h["bundles"][:5],
    } for h in hyp[:200]]
    print(f"hypothesis edges: {len(hyp_slim)}")

    builder = REPO / "raw_python" / "_build_multimodal_with_rag_grep.py"
    src = builder.read_text(encoding="utf-8")

    cur_lit, cur_sz = make_blob(final_curated)
    m = re.search(
        r'_CURATED_DRIVE_BLOB = \(\n((?:    "[A-Za-z0-9+/=]+"\n)+)\)',
        src)
    if not m:
        print("ERR: curated blob anchor not found")
        return 1
    src = (src[:m.start()] + "_CURATED_DRIVE_BLOB = " + cur_lit
           + src[m.end():])
    print(f"curated blob: {cur_sz:,} bytes")

    hyp_lit, hyp_sz = make_blob(hyp_slim)
    m = re.search(
        r'_HYPOTHESIS_EDGES_BLOB = \(\n((?:    "[A-Za-z0-9+/=]+"\n)+)\)',
        src)
    if not m:
        print("ERR: hypothesis blob anchor not found")
        return 1
    src = (src[:m.start()] + "_HYPOTHESIS_EDGES_BLOB = " + hyp_lit
           + src[m.end():])
    print(f"hypothesis blob: {hyp_sz:,} bytes")

    builder.write_text(src, encoding="utf-8")
    print("builder patched -- rebuild now")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
