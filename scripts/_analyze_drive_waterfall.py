"""Waterfall offline analysis of the full Drive corpus.

Processes every text-bearing file in the manifest (not just the
curated top-N), in batches, with resume support. For each batch:

    1. Download + text-extract (cached in data/drive_text_cache/)
    2. Improved entity extraction + noise filtering
    3. Sentence-transformer embedding (all-MiniLM-L6-v2)

After all batches:
    4. Document similarity clustering -> near-duplicate + topic clusters
    5. Entity co-occurrence graph (with paragraph-proximity weighting)
    6. Hypothesis edges: candidate (entity_a, entity_b, relation_type)
       triples for Gemma to verify in the notebook

Outputs:
    data/drive_text_cache/              (extracted text, per file)
    data/drive_doc_embeddings.npz       (matrix + file-id order)
    data/drive_doc_clusters.json        (cluster id -> [file_ids])
    data/drive_entities_v2.json         (cleaned entity index)
    data/drive_hypothesis_edges.json    (candidates for Gemma verification)
    data/drive_waterfall_report.md      (human-readable summary)
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import zipfile
from collections import defaultdict, Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "data" / "drive_manifest.json"
TEXT_CACHE = REPO / "data" / "drive_text_cache"
EMB_OUT = REPO / "data" / "drive_doc_embeddings.npz"
CLUSTERS_OUT = REPO / "data" / "drive_doc_clusters.json"
ENTITIES_OUT = REPO / "data" / "drive_entities_v2.json"
HYP_OUT = REPO / "data" / "drive_hypothesis_edges.json"
REPORT_OUT = REPO / "data" / "drive_waterfall_report.md"

# -----------------------------------------------------------------------------
#  Entity extraction (improved vs v1: filters geography, FB IDs, noise)
# -----------------------------------------------------------------------------

# Geographic tokens that the LASTNAME, Firstname pattern keeps matching
GEO_TOKENS = {
    "SAR", "UAE", "USA", "UK", "HK", "PH", "PRC", "EU",
    "Taiwan", "Singapore", "Philippines", "HongKong", "Dubai",
    "SaudiArabia", "Qatar", "Bahrain", "Oman", "Kuwait",
}

RX_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
RX_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
RX_AMOUNT = re.compile(
    r"(?:PHP|USD|EUR|HKD|AED|SAR|QAR|MYR|SGD|INR|NPR|BDT|KWD|OMR|HKD|\$)"
    r"\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?",
    re.IGNORECASE,
)
# Stricter phone: 8-14 digits (national-format), no huge 15-digit FB post ids
RX_PHONE_PH = re.compile(r"(?<!\d)(?:\+?63|0)?9\d{9}(?!\d)")
RX_PHONE_HK = re.compile(r"(?<!\d)[2-9]\d{7}(?!\d)")
RX_PHONE_INTL = re.compile(r"\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}")
RX_ACCOUNT_BANK = re.compile(
    r"(?:account|a[/.]c|acct)[:#\s.]{0,5}"
    r"([0-9]{4,6}(?:[\s\-]?[0-9]{2,6}){1,3})",
    re.IGNORECASE,
)
RX_ACCOUNT_PH_BANK = re.compile(
    r"\b(?:BDO|BPI|METROBANK|UCPB|PNB|LANDBANK|DBP|CHINABANK|RCBC|"
    r"UNIONBANK|EASTWEST|SECURITY\s+BANK|PSBANK)\b"
    r"[\s:#.]*([0-9][\-0-9\s]{6,28})",
    re.IGNORECASE,
)
ORG_SUFFIXES = [
    "CORPORATION", "CORP", "INCORPORATED", "INC",
    "LIMITED", "LTD", "LLC", "PTE",
    "AGENCY", "CONSULTANTS", "ENTERPRISES",
    "COMPANY", "CO", "PARTNERS", "GROUP", "HOLDINGS",
    "EMPLOYMENT", "RECRUITMENT", "MANPOWER", "PLACEMENT",
    "LENDING", "CREDIT", "FINANCE", "FOUNDATION", "SOCIETY",
]
RX_ORG = re.compile(
    r"\b((?:[A-Z][A-Z0-9'&\-]{1,20}\s+){1,6}(?:"
    + "|".join(re.escape(s) for s in ORG_SUFFIXES)
    + r"))\.?\b"
)
RX_PERSON_HONORIFIC = re.compile(
    r"\b(?:Mr|Ms|Mrs|Miss|Dr|Engr|Atty|Rev)\.?\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})"
)
RX_PERSON_LASTFIRST = re.compile(
    r"\b([A-Z]{2,}[A-Z'\-]{1,}(?:\s+[A-Z][A-Z'\-]+){0,2}),\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"
)
GOV_TOKENS = [
    "POEA", "POLO", "PCG", "DOLE", "DMW", "OWWA", "NBI", "DFA",
    "SEC", "BSP", "MWO", "BP2MI", "IOM", "ILO", "AMLC", "FATF",
    "NLRC", "HKLD",
]


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _is_geo_token(name: str) -> bool:
    return name.strip().upper() in GEO_TOKENS or name.strip() in GEO_TOKENS


def extract_entities_v2(text: str) -> dict:
    """Improved extraction: tighter patterns + post-filter for noise."""
    ents = defaultdict(set)
    if not text:
        return {k: [] for k in (
            "email", "phone", "financial_account", "amount",
            "org", "person", "gov_ref")}

    for m in RX_EMAIL.finditer(text):
        v = m.group(0).lower()
        # Filter common regex false positives
        if ".." in v or v.count("@") != 1:
            continue
        ents["email"].add(v)

    for m in RX_PHONE_PH.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) == 11 and digits.startswith("09"):
            ents["phone"].add("+63" + digits[1:])
        elif len(digits) == 12 and digits.startswith("639"):
            ents["phone"].add("+" + digits)
    for m in RX_PHONE_HK.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) == 8 and digits[0] in "235689":
            ents["phone"].add("+852" + digits)
    for m in RX_PHONE_INTL.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 9 <= len(digits) <= 14:
            ents["phone"].add("+" + digits)

    for m in RX_IBAN.finditer(text):
        ents["financial_account"].add(m.group(0))
    for m in RX_ACCOUNT_PH_BANK.finditer(text):
        num = re.sub(r"\s", "", m.group(1))
        if len(num) >= 8:
            bank = m.group(0).split()[0].upper()
            ents["financial_account"].add(f"{bank}:{num}")
    for m in RX_ACCOUNT_BANK.finditer(text):
        num = re.sub(r"\s", "", m.group(1))
        if 8 <= len(num) <= 24:
            ents["financial_account"].add(num)

    for m in RX_AMOUNT.finditer(text):
        amt = norm_space(m.group(0))
        # drop single-digit-only pagination noise like "P 1" or "$ 5"
        digits = re.sub(r"\D", "", amt)
        if len(digits) >= 3:
            ents["amount"].add(amt)

    for m in RX_ORG.finditer(text):
        name = norm_space(m.group(1))
        if 6 <= len(name) <= 80 and not _is_geo_token(name):
            # skip all-uppercase single-token noise
            parts = name.split()
            if len(parts) >= 2:
                ents["org"].add(name)

    for m in RX_PERSON_HONORIFIC.finditer(text):
        p = norm_space(m.group(1))
        if not _is_geo_token(p) and len(p) >= 4:
            ents["person"].add(p)
    for m in RX_PERSON_LASTFIRST.finditer(text):
        last = norm_space(m.group(1))
        first = norm_space(m.group(2))
        if _is_geo_token(last) or _is_geo_token(first):
            continue
        # Skip known gov tokens misparsed as last names
        if last.upper() in GOV_TOKENS:
            continue
        if len(last) >= 3 and len(first) >= 2:
            ents["person"].add(f"{last}, {first}")

    for tok in GOV_TOKENS:
        if re.search(r"\b" + tok + r"\b", text):
            ents["gov_ref"].add(tok)

    return {k: sorted(v) for k, v in ents.items()}


# -----------------------------------------------------------------------------
#  Download + extract per-file text
# -----------------------------------------------------------------------------

def download_text(svc, fid: str, mime: str, api_key: str) -> str:
    import requests as _rq
    if "google-apps.document" in mime:
        try:
            raw = svc.files().export(
                fileId=fid, mimeType="text/plain").execute()
            return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        except Exception:
            return ""
    if mime == "application/pdf":
        try:
            r = _rq.get(
                f"https://www.googleapis.com/drive/v3/files/{fid}"
                f"?alt=media&key={api_key}", timeout=60)
            if r.status_code != 200:
                return ""
        except Exception:
            return ""
        try:
            import pypdfium2 as _pdfium
            pdf = _pdfium.PdfDocument(io.BytesIO(r.content))
            parts = []
            for p in range(min(len(pdf), 50)):
                page = pdf[p]
                tp = page.get_textpage()
                parts.append(tp.get_text_range())
                tp.close()
                page.close()
            pdf.close()
            return "\n".join(parts)
        except Exception:
            return ""
    if "wordprocessingml" in mime:
        try:
            r = _rq.get(
                f"https://www.googleapis.com/drive/v3/files/{fid}"
                f"?alt=media&key={api_key}", timeout=60)
            if r.status_code != 200:
                return ""
            z = zipfile.ZipFile(io.BytesIO(r.content))
            with z.open("word/document.xml") as f:
                xml = f.read().decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", xml)
        except Exception:
            return ""
    return ""


# -----------------------------------------------------------------------------
#  Main
# -----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--embed-model",
                    default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--max-files", type=int, default=800)
    ap.add_argument("--cluster-threshold", type=float, default=0.72,
                    help="Cosine similarity threshold for doc clustering")
    ap.add_argument("--min-cross-bundle", type=int, default=2)
    ap.add_argument("--api-key",
                    default=os.environ.get(
                        "GOOGLE_DRIVE_API_KEY",
                        "AIzaSyCJ3BJkAEjHG5XMuWkJtSFwCPHvk3h9RJA"))
    ap.add_argument("--skip-download", action="store_true",
                    help="Use only what's already cached (no Drive calls)")
    args = ap.parse_args()

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("[waterfall] pip install google-api-python-client")
        return 1

    svc = build("drive", "v3", developerKey=args.api_key,
                cache_discovery=False)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    text_bearing_mimes = (
        "application/pdf",
        "application/vnd.google-apps.document",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    candidates = [
        n for n in manifest
        if not n.get("is_folder", False)
        and n.get("mime", "") in text_bearing_mimes
    ]
    candidates = sorted(candidates, key=lambda n: -n.get("score", 0))
    candidates = candidates[:args.max_files]
    print(f"[waterfall] {len(candidates)} text-bearing candidates "
          f"(cap={args.max_files})")

    TEXT_CACHE.mkdir(parents=True, exist_ok=True)

    # ---- PHASE 1: batched text extraction with resume ----
    texts: dict = {}
    t0 = time.time()
    errs = 0
    batch_count = 0
    for batch_start in range(0, len(candidates), args.batch_size):
        batch = candidates[batch_start:batch_start + args.batch_size]
        batch_count += 1
        cached_before = len(texts)
        for c in batch:
            fid = c["id"]
            bundle = c.get("bundle") or "unknown"
            cache_key = f"{bundle[:40].replace('/', '_')}__{fid}.txt"
            cache_path = TEXT_CACHE / cache_key
            if cache_path.exists() and cache_path.stat().st_size > 0:
                try:
                    texts[fid] = cache_path.read_text(
                        encoding="utf-8", errors="replace")
                except Exception:
                    errs += 1
                continue
            if args.skip_download:
                continue
            txt = download_text(svc, fid, c["mime"], args.api_key)
            if not txt:
                errs += 1
                continue
            try:
                cache_path.write_text(txt, encoding="utf-8")
                texts[fid] = txt
            except Exception:
                errs += 1
        elapsed = time.time() - t0
        print(f"[waterfall] batch {batch_count} "
              f"({batch_start+1}-{batch_start+len(batch)}): "
              f"texts={len(texts)} (+{len(texts)-cached_before}), "
              f"errs={errs}, elapsed={elapsed:.0f}s")

    print(f"[waterfall] P1 text done: {len(texts)} texts, {errs} errors, "
          f"{time.time()-t0:.0f}s")

    # ---- PHASE 2: entity extraction ----
    file_entities: dict = {}
    entity_index: dict = defaultdict(lambda: defaultdict(
        lambda: {"file_ids": set(), "bundles": set()}))
    for c in candidates:
        fid = c["id"]
        if fid not in texts:
            continue
        bundle = c.get("bundle") or "unknown"
        ents = extract_entities_v2(texts[fid])
        file_entities[fid] = {
            "bundle": bundle, "name": c.get("name", ""),
            "mime": c.get("mime", ""), "entities": ents,
            "text_chars": len(texts[fid]),
        }
        for etype, vals in ents.items():
            for v in vals:
                entity_index[etype][v]["file_ids"].add(fid)
                entity_index[etype][v]["bundles"].add(bundle)
    print(f"[waterfall] P2 entities extracted: {sum(len(v) for v in entity_index.values())} distinct")

    # ---- PHASE 3: sentence-transformer embeddings ----
    embedding_success = False
    fid_order: list = []
    emb_matrix = None
    try:
        print(f"[waterfall] P3 loading embedder {args.embed_model}")
        from sentence_transformers import SentenceTransformer
        import numpy as np
        model = SentenceTransformer(args.embed_model)
        fid_order = [fid for fid in texts.keys()
                     if len(texts[fid].strip()) >= 50]
        print(f"[waterfall] P3 encoding {len(fid_order)} docs (first 2000 chars each)")
        doc_texts = [texts[fid][:2000] for fid in fid_order]
        emb_matrix = model.encode(doc_texts, batch_size=32,
                                    show_progress_bar=False)
        # L2 normalize for cosine
        norms = (emb_matrix ** 2).sum(axis=1, keepdims=True) ** 0.5
        norms[norms < 1e-9] = 1.0
        emb_matrix = emb_matrix / norms
        np.savez(EMB_OUT, embeddings=emb_matrix,
                  file_ids=np.array(fid_order))
        print(f"[waterfall] P3 wrote {EMB_OUT}: {emb_matrix.shape}")
        embedding_success = True
    except Exception as e:
        print(f"[waterfall] P3 embedding FAILED "
              f"({type(e).__name__}: {e}); skipping clusters")

    # ---- PHASE 4: similarity clustering (greedy, single-link) ----
    clusters: list = []
    if embedding_success and emb_matrix is not None:
        import numpy as np
        sim = emb_matrix @ emb_matrix.T
        N = sim.shape[0]
        assigned: list = [-1] * N
        cid = 0
        for i in range(N):
            if assigned[i] != -1:
                continue
            assigned[i] = cid
            stack = [i]
            while stack:
                x = stack.pop()
                for j in range(N):
                    if assigned[j] == -1 and sim[x, j] >= args.cluster_threshold:
                        assigned[j] = cid
                        stack.append(j)
            cid += 1
        by_cluster = defaultdict(list)
        for i, c in enumerate(assigned):
            by_cluster[c].append(fid_order[i])
        clusters = [
            {"cluster_id": c, "size": len(members), "file_ids": members}
            for c, members in sorted(by_cluster.items(),
                                       key=lambda kv: -len(kv[1]))
        ]
        CLUSTERS_OUT.write_text(
            json.dumps(clusters, indent=2), encoding="utf-8")
        print(f"[waterfall] P4 wrote {CLUSTERS_OUT}: "
              f"{len(clusters)} clusters, largest={max(c['size'] for c in clusters) if clusters else 0}")

    # ---- PHASE 5: entity co-occurrence graph ----
    # For every pair of entities appearing in the same document, tally
    # co-occurrences. Weight by how many bundles they span.
    cooc: dict = defaultdict(lambda: {"n_docs": 0, "bundles": set(),
                                        "file_ids": set()})
    for fid, info in file_entities.items():
        bundle = info["bundle"]
        flat = []
        for etype, vals in info["entities"].items():
            for v in vals:
                flat.append((etype, v))
        for i in range(len(flat)):
            for j in range(i + 1, len(flat)):
                a, b = flat[i], flat[j]
                if a == b:
                    continue
                key = tuple(sorted([a, b]))
                cooc[key]["n_docs"] += 1
                cooc[key]["bundles"].add(bundle)
                cooc[key]["file_ids"].add(fid)

    # ---- PHASE 6: hypothesis edges (cross-bundle only) ----
    hypothesis: list = []
    for (a, b), meta in cooc.items():
        nb = len(meta["bundles"])
        if nb < args.min_cross_bundle:
            continue
        # Heuristic relation-type guess based on entity types
        rel_guess = _guess_relation(a[0], a[1], b[0], b[1])
        hypothesis.append({
            "a_type": a[0], "a_value": a[1],
            "b_type": b[0], "b_value": b[1],
            "relation_guess": rel_guess,
            "n_docs": meta["n_docs"],
            "n_bundles": nb,
            "bundles": sorted(meta["bundles"]),
            "sample_file_ids": sorted(meta["file_ids"])[:5],
        })
    hypothesis.sort(
        key=lambda h: (-h["n_bundles"], -h["n_docs"]))
    HYP_OUT.write_text(
        json.dumps(hypothesis[:2000], ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[waterfall] P6 wrote {HYP_OUT}: "
          f"{len(hypothesis)} hypothesis edges (saved top 2000)")

    # Save entity index too
    ENTITIES_OUT.write_text(
        json.dumps({
            etype: [
                {"value": val, "n_bundles": len(m["bundles"]),
                 "n_files": len(m["file_ids"]),
                 "bundles": sorted(m["bundles"])[:20],
                 "file_ids": sorted(m["file_ids"])[:20]}
                for val, m in sorted(
                    vals.items(),
                    key=lambda kv: (-len(kv[1]["bundles"]),
                                      -len(kv[1]["file_ids"])),
                )
            ]
            for etype, vals in entity_index.items()
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[waterfall] P6 wrote {ENTITIES_OUT}")

    # ---- Report ----
    md: list = [
        "# Drive waterfall analysis report",
        "",
        f"- Candidates: {len(candidates)} text-bearing files",
        f"- Text-extracted: {len(texts)}",
        f"- Errors (download / parse): {errs}",
        f"- Distinct entities: {sum(len(v) for v in entity_index.values())}",
        f"- Hypothesis edges (cross-bundle, >= {args.min_cross_bundle}): "
        f"{len(hypothesis)}",
        f"- Doc embedding clusters: {len(clusters)}",
        "",
    ]
    # Top cross-bundle orgs, persons, emails, accounts
    for etype in ("org", "person", "email", "financial_account",
                   "phone", "gov_ref"):
        vals = entity_index.get(etype, {})
        top = sorted(
            vals.items(),
            key=lambda kv: (-len(kv[1]["bundles"]),
                              -len(kv[1]["file_ids"])),
        )[:20]
        md.append(f"## Top {etype} by cross-bundle reach")
        md.append("")
        md.append("| bundles | files | value |")
        md.append("|---:|---:|---|")
        for val, m in top:
            if len(m["bundles"]) < args.min_cross_bundle:
                continue
            md.append(f"| {len(m['bundles'])} | {len(m['file_ids'])} | "
                      f"`{val[:70]}` |")
        md.append("")

    md.append("## Top 40 hypothesis edges")
    md.append("")
    md.append("| bundles | docs | relation | a | b |")
    md.append("|---:|---:|---|---|---|")
    for h in hypothesis[:40]:
        md.append(
            f"| {h['n_bundles']} | {h['n_docs']} | "
            f"{h['relation_guess']} | "
            f"`{h['a_type']}:{h['a_value'][:28]}` | "
            f"`{h['b_type']}:{h['b_value'][:28]}` |"
        )
    md.append("")

    if clusters:
        md.append("## Top 10 doc clusters (by size)")
        md.append("")
        md.append("| cluster | size |")
        md.append("|---:|---:|")
        for c in clusters[:10]:
            md.append(f"| {c['cluster_id']} | {c['size']} |")

    REPORT_OUT.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[waterfall] wrote {REPORT_OUT}")
    print(f"[waterfall] total elapsed: {time.time()-t0:.0f}s")

    # Console summary
    print("\n=== WATERFALL SUMMARY ===")
    print(f"  text-extracted  : {len(texts)}/{len(candidates)}")
    print(f"  entities        : {sum(len(v) for v in entity_index.values())}")
    print(f"  hypothesis edges: {len(hypothesis)}")
    print(f"  doc clusters    : {len(clusters)}")
    return 0


def _guess_relation(ta: str, va: str, tb: str, vb: str) -> str:
    """Statistical relation-type guess from the entity-type pair.
    Gemma will refine/confirm each of these in the notebook."""
    t = {ta, tb}
    if t == {"person", "org"}:
        return "person_associated_with_org"
    if t == {"person", "financial_account"}:
        return "person_owns_account"
    if t == {"person", "phone"}:
        return "person_uses_phone"
    if t == {"person", "email"}:
        return "person_uses_email"
    if t == {"org", "financial_account"}:
        return "org_owns_account"
    if t == {"org", "phone"}:
        return "org_has_phone"
    if t == {"org", "email"}:
        return "org_has_email"
    if t == {"org", "gov_ref"}:
        return "org_regulated_by_agency"
    if t == {"person", "gov_ref"}:
        return "person_filed_with_agency"
    if t == {"person", "person"}:
        return "persons_co_appear"
    if t == {"org", "org"}:
        return "orgs_co_appear"
    return "co_occurs"


if __name__ == "__main__":
    sys.exit(main())
