#!/usr/bin/env python3
"""Build the .ipynb, version the wheels dataset, push the kernel.

Uses Kaggle's REST API directly via stdlib urllib so no working pip is
required. Authenticates with the KAGGLE_API_TOKEN env var (Bearer
token).
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import mimetypes
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
# Convert kaggle/<notebook>/kernel.py -> .ipynb (single huge cell)
# ---------------------------------------------------------------------------
def build_ipynb(py_path: Path, out_path: Path,
                  markdown_intro: str | None = None) -> Path:
    """Build the .ipynb. CRITICAL: Kaggle's /kernels/push silently
    discards `source` if it's a list of lines (the standard nbformat).
    Source must be a single string."""
    src = py_path.read_text(encoding="utf-8")
    md = markdown_intro or (
        "# Duecare notebook\n\n"
        "Single cell that installs the wheels, loads Gemma 4, and "
        "launches the application.\n\n"
        "**Requires:** GPU T4 (or better), Internet ON, `HF_TOKEN` "
        "Kaggle Secret, and the wheels dataset declared in "
        "kernel-metadata.json attached."
    )
    nb = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": md,
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {"trusted": True},
                "outputs": [],
                "source": src,
            },
        ],
        "metadata": {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
                "language": "python",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    return out_path


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
# Kernel push (multipart-shaped: metadata + ipynb in one POST)
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
    """Push a kernel directory containing kernel-metadata.json + .ipynb.

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
    # from the title. The notebook body MUST be in the `text` field;
    # `kernelBody` is silently discarded.
    payload = {
        "id": existing_id,
        "newTitle": meta.get("title"),
        "language": meta.get("language", "python"),
        "kernelType": meta.get("kernel_type", "notebook"),
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
        "notebook_dir": "kaggle/live-demo",
        "kernel_py": "kernel.py",
        "ipynb_name": "notebook.ipynb",
        "slug": "duecare-live-demo",
        "title": "Duecare Live Demo",
        "wheels_dataset_slug": "duecare-llm-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "gemma-chat": {
        "notebook_dir": "kaggle/gemma-chat",
        "kernel_py": "kernel.py",
        "ipynb_name": "notebook.ipynb",
        "slug": "duecare-gemma-chat",
        "title": "Duecare Gemma Chat",
        "wheels_dataset_slug": "duecare-gemma-chat-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
    },
    "bench-and-tune": {
        "notebook_dir": "kaggle/bench-and-tune",
        "kernel_py": "kernel.py",
        "ipynb_name": "notebook.ipynb",
        "slug": "duecare-bench-and-tune",
        "title": "Duecare Bench & Tune",
        "wheels_dataset_slug": "duecare-bench-and-tune-wheels",
        "wheels_dir": "wheels",
        "model_sources": _DEFAULT_GEMMA4_MODELS,
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
                          "(demo|gemma-chat|bench-and-tune)")
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

    # 1. Build the .ipynb from the python kernel source.
    py_path = notebook_dir / preset["kernel_py"]
    nb_path = notebook_dir / preset["ipynb_name"]
    if not py_path.exists():
        print(f"[1] kernel source not found: {py_path.relative_to(root)}")
        return 1
    print(f"[1] building notebook -> {nb_path.relative_to(root)}")
    md_intro = (
        f"# {preset['title']}\n\n"
        f"Single cell that installs the wheels, loads Gemma 4, and "
        f"launches the application.\n\n"
        f"**Requires:** GPU T4 (or better), Internet ON, `HF_TOKEN` "
        f"Kaggle Secret, the `{USERNAME}/{wheels_slug}` dataset "
        f"attached."
    )
    build_ipynb(py_path, nb_path, markdown_intro=md_intro)

    # 2. Write kernel-metadata.json (in the same dir as the .ipynb).
    kernel_dir = nb_path.parent
    kernel_meta = {
        "id": f"{USERNAME}/{slug}",
        "title": preset["title"],
        "code_file": nb_path.name,
        "language": "python",
        "kernel_type": "notebook",
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

    # 3. Version the wheels dataset (or skip). Each notebook bundles
    # its own subset of wheels under kaggle/<notebook>/wheels/, so the
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
