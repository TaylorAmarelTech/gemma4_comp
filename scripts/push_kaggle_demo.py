#!/usr/bin/env python3
"""Version the wheels dataset, then push the script kernel.

Uses Kaggle's REST API directly via stdlib urllib so no working pip is
required. Authenticates with the KAGGLE_API_TOKEN env var (Bearer
token).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path


KAGGLE_BASE = "https://www.kaggle.com/api/v1"
USERNAME = "taylorsamarel"


def _auth_headers() -> dict:
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("KAGGLE_API_TOKEN env var not set")
    return {"Authorization": f"Bearer {token}"}


def _api(method: str, path: str, *, body=None, headers=None,
          timeout: float = 60.0):
    url = f"{KAGGLE_BASE}{path}"
    h = dict(_auth_headers())
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            h.setdefault("Content-Type", "application/json")
        else:
            data = body
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ---------------------------------------------------------------------------
# Dataset upload (multipart-style: request token, PUT bytes, finalize)
# ---------------------------------------------------------------------------
def _start_upload(file_name: str, content_length: int) -> dict:
    """Step 1: ask Kaggle for an upload URL + token.
    Uses the NEW /blobs/upload endpoint with type=DATASET. The legacy
    /datasets/upload/file/... endpoint returns a token that lacks the
    path metadata create/version needs ('Path must be non-null')."""
    body = {
        "type": "DATASET",
        "name": file_name,
        "contentLength": content_length,
        "lastModifiedEpochSeconds": int(time.time()),
        "contentType": "application/octet-stream",
    }
    code, resp = _api("POST", "/blobs/upload", body=body)
    if code >= 300:
        raise RuntimeError(f"start_upload failed {code}: {resp[:500]!r}")
    return json.loads(resp)


def _put_bytes(upload_url: str, data: bytes) -> None:
    """Step 2: PUT the actual bytes to the URL Kaggle returned."""
    req = urllib.request.Request(
        upload_url, data=data, method="PUT",
        headers={"Content-Type": "application/octet-stream",
                  "Content-Length": str(len(data))})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            if r.status >= 300:
                raise RuntimeError(f"put_bytes failed {r.status}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"put_bytes HTTP {e.code}: {e.read()[:500]!r}")


def upload_files(file_paths: list[Path]) -> list[dict]:
    """Upload a batch of files. Returns file entries with path + token."""
    tokens = []
    for p in file_paths:
        size = p.stat().st_size
        print(f"  upload  {p.name}  ({size} bytes)")
        info = _start_upload(p.name, size)
        upload_url = info.get("createUrl") or info.get("uploadUrl")
        token = info.get("token")
        if not upload_url:
            raise RuntimeError(f"no upload URL in response: {info}")
        with p.open("rb") as f:
            _put_bytes(upload_url, f.read())
        tokens.append({
            "path": p.name,
            "token": token,
            "description": f"Wheel {p.name}",
        })
    return tokens


def version_dataset(owner: str, slug: str, file_paths: list[Path],
                      version_notes: str) -> dict:
    """Create a new version of an existing dataset.
    Tries new + old endpoints + body shapes."""
    tokens = upload_files(file_paths)
    body = {
        "versionNotes": version_notes,
        "deleteOldVersions": False,
        "subtitle": "",
        "description": "",
        "categoryIds": [],
        "files": [{"token": t["token"]} for t in tokens],
    }
    code, resp = _api(
        "POST", f"/datasets/create/version/{owner}/{slug}",
        body=body, timeout=300)
    if code >= 300:
        raise RuntimeError(
            f"version_dataset failed {code}: {resp[:1000]!r}")
    return json.loads(resp)


# ---------------------------------------------------------------------------
# Kernel push (metadata + kernel.py source in one POST)
# ---------------------------------------------------------------------------
def _normalize_data_source_slugs(values: list, key: str) -> list[str]:
    """Kaggle's /kernels/pull returns dataset/model sources as objects
    with a `ref` or `slug` field; /kernels/push wants flat strings of
    the form 'owner/slug' (datasets/competitions/kernels) or
    'owner/group/framework/variation/version' (models). Normalise
    whatever shape pull returned into the flat string form push needs."""
    out: list[str] = []
    if not values:
        return out
    for v in values:
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            for field in ("ref", "url", "slug", "kernelDataSourceUrl"):
                if v.get(field):
                    out.append(v[field])
                    break
    return out


def push_kernel(kernel_dir: Path,
                  preserve_attached: bool = True) -> dict:
    """Push a kernel directory containing kernel-metadata.json + kernel.py.

    When `preserve_attached` is True, fetch the existing kernel's
    attached datasets/models/competitions/kernels via /kernels/pull
    and MERGE them with whatever's listed in kernel-metadata.json
    (metadata wins for explicit additions; pull-side wins for any
    user-attached items not in metadata). This stops every push from
    wiping the user's manually attached Gemma 4 model in the UI."""
    meta_path = kernel_dir / "kernel-metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"missing kernel-metadata.json in "
                                  f"{kernel_dir}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    code_file = kernel_dir / meta["code_file"]
    if not code_file.exists():
        raise FileNotFoundError(f"code_file not found: {code_file}")

    # Resolve existing numeric kernel id so this becomes an UPDATE
    # rather than a CREATE (avoids 409 title-already-in-use). Also
    # capture the existing attached data sources so a push doesn't
    # wipe the user's manual UI attachments.
    owner, slug = meta["id"].split("/", 1)
    existing_id = None
    existing_meta: dict = {}
    code, body = _api(
        "GET",
        f"/kernels/pull?user_name={owner}&kernel_slug={slug}")
    if code == 200:
        try:
            parsed = json.loads(body)
            existing_meta = parsed.get("metadata") or {}
            existing_id = int(existing_meta["id"])
            print(f"    found existing kernel id={existing_id} -- "
                  f"will UPDATE in place")
        except Exception:
            existing_id = None

    # Merge attached sources: union of metadata-supplied list +
    # whatever pull returned (preserves UI-attached items).
    def _merge(meta_key: str, pull_key: str) -> list[str]:
        from_meta = meta.get(meta_key, []) or []
        from_pull = (_normalize_data_source_slugs(
            existing_meta.get(pull_key) or [], pull_key)
                     if preserve_attached else [])
        seen = set()
        merged = []
        for s in [*from_meta, *from_pull]:
            if s and s not in seen:
                merged.append(s); seen.add(s)
        return merged

    dataset_sources = _merge("dataset_sources", "datasetDataSources")
    competition_sources = _merge("competition_sources",
                                   "competitionDataSources")
    kernel_sources = _merge("kernel_sources", "kernelDataSources")
    model_sources = _merge("model_sources", "modelDataSources")
    if preserve_attached and existing_meta:
        print(f"    preserving attached sources: "
              f"{len(model_sources)} model(s), "
              f"{len(dataset_sources)} dataset(s), "
              f"{len(competition_sources)} competition(s), "
              f"{len(kernel_sources)} kernel(s)")
        if model_sources:
            for m in model_sources:
                print(f"      model: {m}")

    # `id` is a numeric kernel id (for updates); for first push pass null
    # and Kaggle assigns one. DO NOT pass `slug` -- Kaggle derives it
    # from the title. The script body MUST be in the `text` field;
    # `kernelBody` is silently discarded.
    payload = {
        "id": existing_id,
        "newTitle": meta.get("title"),
        "language": meta.get("language", "python"),
        "kernelType": meta.get("kernel_type", "script"),
        "isPrivate": str(meta.get("is_private", "true")).lower() == "true",
        "enableGpu": str(meta.get("enable_gpu", "false")).lower() == "true",
        "enableTpu": False,
        "enableInternet":
            str(meta.get("enable_internet", "true")).lower() == "true",
        "datasetDataSources": dataset_sources,
        "competitionDataSources": competition_sources,
        "kernelDataSources": kernel_sources,
        "modelDataSources": model_sources,
        "categoryIds": meta.get("keywords", []),
        "dockerImagePinningType":
            meta.get("docker_image_pinning_type", "original"),
        "text": code_file.read_text(encoding="utf-8"),
    }
    code, resp = _api("POST", "/kernels/push", body=payload, timeout=180)
    if code >= 300:
        raise RuntimeError(f"kernel push failed {code}: {resp[:1000]!r}")
    return json.loads(resp)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
# Default Gemma 4 model attachments (note: "Transformers" capital T --
# this is what kernels/pull returns on the user's other kernels). All
# four IT variants — E4B-IT is the headline model, E2B-IT is the
# on-device backup, 26B-A4B-IT and 31B-IT are larger upgrade paths.
# Kept here so pushes never need the user to re-attach via UI.
_DEFAULT_GEMMA4_MODELS = [
    "google/gemma-4/Transformers/gemma-4-e4b-it/1",
    "google/gemma-4/Transformers/gemma-4-e2b-it/1",
    "google/gemma-4/Transformers/gemma-4-26b-a4b-it/1",
    "google/gemma-4/Transformers/gemma-4-31b-it/1",
]

_KERNEL_PRESETS = {
    "demo": {
        "notebook_dir": "kaggle/02-live-demo",
        "kernel_py": "kernel.py",
        "slug": "duecare-live-demo",
        "title": "DueCare Live Demo",
        "wheels_dataset_slug": "duecare-live-demo-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "chat-playground": {
        "notebook_dir": "kaggle/_archive/notebooks/A-01-chat-playground",
        "kernel_py": "kernel.py",
        "slug": "duecare-chat-playground",
        "title": "DueCare Chat Playground",
        "wheels_dataset_slug": "duecare-chat-playground-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "bench-and-tune": {
        "notebook_dir": "kaggle/_archive/notebooks/A-07-bench-and-tune",
        "kernel_py": "kernel.py",
        "slug": "duecare-bench-and-tune",
        # Title MUST derive to the slug above when lowercased + spaces->hyphens
        # (per feedback_kaggle_slug_derivation memory). "DueCare Bench and Tune"
        # -> "duecare-bench-and-tune". The "&" form would derive to a
        # different slug and break the existence check.
        "title": "DueCare Bench and Tune",
        "wheels_dataset_slug": "duecare-bench-and-tune-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "chat-playground-with-grep-rag-tools": {
        "notebook_dir": "kaggle/_archive/notebooks/A-02-chat-playground-with-grep-rag-tools",
        "kernel_py": "kernel.py",
        "slug": "duecare-chat-playground-with-grep-rag-tools",
        "title": "DueCare Chat Playground with GREP RAG Tools",
        "wheels_dataset_slug": "duecare-chat-playground-with-grep-rag-tools-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "content-classifier": {
        "notebook_dir": "kaggle/_archive/notebooks/A-05-gemma-content-classification-evaluation",
        "kernel_py": "kernel.py",
        "slug": "duecare-gemma-content-classification-evaluation",
        "title": "DueCare Gemma Content Classification Evaluation",
        "wheels_dataset_slug": "duecare-gemma-content-classification-evaluation-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "prompt-generation": {
        "notebook_dir": "kaggle/_archive/notebooks/A-06-prompt-generation",
        "kernel_py": "kernel.py",
        "slug": "duecare-prompt-generation",
        "title": "DueCare Prompt Generation",
        "wheels_dataset_slug": "duecare-prompt-generation-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "research-graphs": {
        "notebook_dir": "kaggle/_archive/notebooks/A-08-research-graphs",
        "kernel_py": "kernel.py",
        "slug": "duecare-research-graphs",
        "title": "DueCare Research Graphs",
        "wheels_dataset_slug": "duecare-research-graphs-wheels",
        "wheels_dir": "wheels",
        "model_sources": [],   # pure visualization, no model attached
    },
    "content-classification-playground": {
        "notebook_dir": "kaggle/_archive/notebooks/A-03-content-classification-playground",
        "kernel_py": "kernel.py",
        "slug": "duecare-content-classification-playground",
        "title": "DueCare Content Classification Playground",
        "wheels_dataset_slug": "duecare-content-classification-playground-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "content-knowledge-builder-playground": {
        "notebook_dir": "kaggle/_archive/notebooks/A-04-content-knowledge-builder-playground",
        "kernel_py": "kernel.py",
        "slug": "duecare-content-knowledge-builder-playground",
        "title": "DueCare Content Knowledge Builder Playground",
        "wheels_dataset_slug": "duecare-content-knowledge-builder-playground-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS[:2],  # only E4B + E2B
    },
    "chat-playground-with-agentic-research": {
        "notebook_dir": "kaggle/_archive/notebooks/A-09-chat-playground-with-agentic-research",
        "kernel_py": "kernel.py",
        "slug": "duecare-chat-playground-with-agentic-research",
        "title": "DueCare Chat Playground with Agentic Research",
        "wheels_dataset_slug": "duecare-chat-playground-with-agentic-research-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "chat-playground-jailbroken-models": {
        "notebook_dir": "kaggle/_archive/notebooks/A-10-chat-playground-jailbroken-models",
        "kernel_py": "kernel.py",
        "slug": "duecare-chat-playground-jailbroken-models",
        "title": "DueCare Chat Playground Jailbroken Models",
        "wheels_dataset_slug": "duecare-chat-playground-jailbroken-models-wheels",
        "wheels_dir": "wheels",
        "model_sources": [],   # HF Hub download per JAILBROKEN_MODEL config
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".", type=Path)
    ap.add_argument("--skip-dataset", action="store_true",
                     help="skip wheel upload (assumes dataset is current)")
    ap.add_argument("--skip-kernel", action="store_true",
                     help="skip kernel push")
    ap.add_argument("--kernel", choices=list(_KERNEL_PRESETS),
                     default="demo",
                     help="which kernel preset to push "
                          "(demo|chat-playground|"
                          "chat-playground-with-grep-rag-tools|"
                          "bench-and-tune)")
    ap.add_argument("--kernel-slug", default=None,
                     help="override the slug for the chosen preset")
    ap.add_argument("--enable-gpu", default="false",
                     choices=("true", "false"),
                     help="enableGpu flag (false bypasses the 2-GPU "
                            "session cap; user toggles in UI)")
    args = ap.parse_args()

    root = args.repo_root.resolve()
    preset = _KERNEL_PRESETS[args.kernel]
    slug = args.kernel_slug or preset["slug"]
    notebook_dir = root / preset["notebook_dir"]
    wheels_dir = notebook_dir / preset["wheels_dir"]
    wheels_slug = preset["wheels_dataset_slug"]

    # 1. Validate the python kernel source.
    py_path = notebook_dir / preset["kernel_py"]
    if not py_path.exists():
        print(f"[1] kernel source not found: {py_path.relative_to(root)}")
        return 1
    print(f"[1] using script kernel -> {py_path.relative_to(root)}")

    # 2. Write kernel-metadata.json (in the same dir as kernel.py).
    kernel_dir = py_path.parent
    kernel_meta = {
        "id": f"{USERNAME}/{slug}",
        "title": preset["title"],
        "code_file": py_path.name,
        "language": "python",
        "kernel_type": "script",
        "is_private": "true",
        "enable_gpu": args.enable_gpu,
        "enable_internet": "true",
        "dataset_sources": [f"{USERNAME}/{wheels_slug}"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": preset.get("model_sources", []),
        "docker_image_pinning_type": "original",
        "keywords": [],
    }
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(kernel_meta, indent=2), encoding="utf-8")
    print(f"[2] wrote kernel-metadata.json "
          f"(id={kernel_meta['id']}, gpu={kernel_meta['enable_gpu']})")

    # 3. Version the wheels dataset (or skip). Each kernel bundles
    # its own subset of wheels under kaggle/<kernel>/wheels/, so the
    # upload pulls from there rather than the shared root /dist.
    if not args.skip_dataset:
        wheels = sorted(wheels_dir.glob("*.whl"))
        if not wheels:
            print(f"[3] no wheels in {wheels_dir.relative_to(root)}; "
                  f"build them first with "
                  f"`python scripts/build_all_wheels.py "
                  f"--no-isolation --clean` and copy the relevant "
                  f"subset into {wheels_dir.relative_to(root)}")
            return 1
        print(f"[3] uploading {len(wheels)} wheel(s) as a new version "
              f"of {USERNAME}/{wheels_slug}")
        try:
            result = version_dataset(
                owner=USERNAME, slug=wheels_slug,
                file_paths=wheels,
                version_notes=(f"duecare-llm-* v0.1.0 wheels "
                                f"({time.strftime('%Y-%m-%d %H:%M')})"))
            print(f"    OK: {result.get('url') or result}")
        except Exception as e:
            print(f"    FAILED: {e}")
            return 2
    else:
        print("[3] --skip-dataset -- not uploading wheels")

    # 4. Push the kernel.
    if not args.skip_kernel:
        print(f"[4] pushing kernel {kernel_meta['id']} (PRIVATE, "
              f"GPU={kernel_meta['enable_gpu']}, Internet=on)")
        try:
            result = push_kernel(kernel_dir)
            print(f"    OK")
            print(f"    url:    {result.get('url')}")
            print(f"    ref:    {result.get('ref')}")
            print(f"    versionNumber: {result.get('versionNumber')}")
        except Exception as e:
            print(f"    FAILED: {e}")
            return 3
    else:
        print("[4] --skip-kernel -- not pushing")

    print("\n  done. Open the kernel URL above, switch GPU to T4 if "
          "needed, hit Run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
