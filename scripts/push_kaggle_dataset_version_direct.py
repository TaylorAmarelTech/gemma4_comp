"""Push a Kaggle dataset version directly via REST API + Bearer auth.

Bypasses the kaggle CLI entirely — needed because the released CLI
(1.7.4.5) doesn't support the new "API Token" format that the user's
fresh token uses, and CLI 1.8.0+ isn't on PyPI yet (only on GitHub
master, which requires Py3.11+, and Py3.11/12/13/14 all have broken
pip on this machine).

Reads token from ~/.kaggle/access_token. Reads dataset metadata from
the standard kaggle/<notebook>/wheels/dataset-metadata.json. Uploads
each file in the wheels folder as a blob, then creates a new dataset
version referencing those blobs.

Run:
    python scripts/push_kaggle_dataset_version_direct.py kaggle/chat-playground/wheels/ \\
        --notes "42 GREP rules"

Or push all 9 chat-bundling wheels datasets:
    python scripts/push_kaggle_dataset_version_direct.py --all
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.request
import urllib.error


API = "https://www.kaggle.com/api/v1"
TOKEN_PATH = pathlib.Path.home() / ".kaggle" / "access_token"
LEGACY_PATH = pathlib.Path.home() / ".kaggle" / "kaggle.json"


def _bearer() -> str | None:
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    return None


def _basic() -> tuple[str, str] | None:
    if LEGACY_PATH.exists():
        cfg = json.loads(LEGACY_PATH.read_text(encoding="utf-8"))
        return cfg["username"], cfg["key"]
    return None


def _request(
    method: str,
    path: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    if content_type:
        headers["Content-Type"] = content_type
    bearer = _bearer()
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    else:
        creds = _basic()
        if creds:
            import base64
            token = base64.b64encode(f"{creds[0]}:{creds[1]}".encode()).decode()
            headers["Authorization"] = f"Basic {token}"
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def upload_file_as_blob(file_path: pathlib.Path, dataset_owner: str, dataset_slug: str) -> str:
    """Upload a file using the Kaggle blob upload flow.

    Step 1: POST /blobs/upload (returns createUrl + token)
    Step 2: PUT the file bytes to createUrl
    Returns the blob token to reference in createVersion.
    """
    file_size = file_path.stat().st_size
    payload = json.dumps({
        "type": "dataset",
        "name": file_path.name,
        "contentLength": file_size,
        "contentType": "application/octet-stream",
        "lastModifiedEpochSeconds": int(file_path.stat().st_mtime),
        "datasetOwner": dataset_owner,
        "datasetSlug": dataset_slug,
    }).encode("utf-8")

    code, body = _request(
        "POST", "/blobs/upload",
        data=payload, content_type="application/json",
    )
    if code != 200:
        raise RuntimeError(f"blobs/upload init failed [{code}]: {body[:300]!r}")
    info = json.loads(body)
    create_url = info["createUrl"]
    token = info["token"]

    # Step 2: PUT the file bytes
    file_bytes = file_path.read_bytes()
    put_req = urllib.request.Request(
        create_url, data=file_bytes, method="PUT",
        headers={
            "Content-Type": "application/octet-stream",
            "x-goog-content-length-range": f"0,{file_size}",
        },
    )
    try:
        with urllib.request.urlopen(put_req, timeout=300) as resp:
            put_status = resp.status
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"blob PUT failed [{e.code}]: {e.read()[:300]!r}")
    if put_status not in (200, 201):
        raise RuntimeError(f"blob PUT unexpected status {put_status}")
    return token


def push_version(folder: pathlib.Path, notes: str) -> bool:
    meta_path = folder / "dataset-metadata.json"
    if not meta_path.exists():
        print(f"  ! missing dataset-metadata.json in {folder}")
        return False
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    full_id = meta["id"]
    owner, slug = full_id.split("/", 1)
    print(f"\n=== {full_id} ===")

    # Upload every non-metadata file in the folder
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.name != "dataset-metadata.json")
    if not files:
        print("  ! no files to upload")
        return False
    blob_files = []
    for f in files:
        print(f"  uploading {f.name} ({f.stat().st_size:,} bytes)...", end="", flush=True)
        try:
            token = upload_file_as_blob(f, owner, slug)
            blob_files.append({"token": token, "description": ""})
            print(" OK")
        except Exception as e:
            print(f" FAIL: {e}")
            return False

    # Create new dataset version
    payload = json.dumps({
        "versionNotes": notes,
        "subtitle": meta.get("subtitle", ""),
        "description": meta.get("description", ""),
        "files": blob_files,
        "isPrivate": meta.get("isPrivate", False),
        "convertToCsv": False,
        "categoryIds": meta.get("keywords", []),
        "deleteOldVersions": False,
    }).encode("utf-8")
    # Endpoint shape: /datasets/create/version/{owner}/{slug}
    # (Kaggle CLI uses /datasets/createVersion/{owner_slug} with combined
    # path arg; the REST routing accepts the slash-split form which is
    # what the public API consistently routes.)
    code, body = _request(
        "POST", f"/datasets/create/version/{owner}/{slug}",
        data=payload, content_type="application/json",
    )
    if code != 200:
        print(f"  ! createversion failed [{code}]: {body.decode(errors='replace')[:400]}")
        return False
    result = json.loads(body)
    print(f"  OK new version url={result.get('url') or result.get('ref')}")
    return True


# The 10 notebooks that bundle the chat wheel and need a re-push
# (grading-evaluation = A6, added 2026-05-03)
CHAT_BUNDLING = (
    "chat-playground",
    "chat-playground-with-grep-rag-tools",
    "content-classification-playground",
    "content-knowledge-builder-playground",
    "gemma-content-classification-evaluation",
    "prompt-generation",
    "research-graphs",
    "chat-playground-with-agentic-research",
    "chat-playground-jailbroken-models",
    "grading-evaluation",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", help="Path to a kaggle/<notebook>/wheels/ folder")
    parser.add_argument("--all", action="store_true", help="Push all 9 chat-bundling wheels datasets")
    parser.add_argument("--notes", default="42 GREP rules (was 37): kafala-huroob, H-2A/H-2B, fishing-vessel, smuggler-fee, domestic-locked-in")
    args = parser.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent
    if args.all:
        ok = 0
        fail = 0
        for nb in CHAT_BUNDLING:
            folder = repo / "kaggle" / nb / "wheels"
            try:
                if push_version(folder, args.notes):
                    ok += 1
                else:
                    fail += 1
            except Exception as e:
                print(f"  ! exception: {e}")
                fail += 1
        print(f"\nDone: {ok} ok, {fail} failed")
        return 0 if fail == 0 else 1
    elif args.folder:
        folder = pathlib.Path(args.folder).resolve()
        return 0 if push_version(folder, args.notes) else 1
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
