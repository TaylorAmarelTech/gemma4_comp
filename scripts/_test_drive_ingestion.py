"""Local probe of the 4 default Drive URLs against the currently
installed gdown, using each fallback path. Writes a concise report.
"""
from __future__ import annotations

import inspect
import os
import re
import sys
from pathlib import Path

OUT_ROOT = Path("data/_drive_test")
OUT_ROOT.mkdir(parents=True, exist_ok=True)

URLS = [
    "1p0D6tMznPosAeXk486O7NNMua24nGC_6",
    "1JSy_xNvUOItuV2go1A-4TIvG4aAsA4mr",
    "1soev7vNpF-ACwWR4NrjD3S89U3GA4TpK",
    "https://drive.google.com/file/d/1w6HQjzqVfbAybGr_IdPRZu82rBC4K8sb/view",
]


def _extract_id(raw: str) -> tuple[str, str]:
    if "drive.google.com" in raw:
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", raw)
        if m:
            return "folder", m.group(1)
        m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", raw)
        if m:
            return "file", m.group(1)
    return "folder", raw


def main() -> int:
    try:
        import gdown
    except Exception as e:
        print(f"gdown import failed: {e}")
        return 1
    print(f"gdown {gdown.__version__}")
    try:
        print(f"download_folder sig: {inspect.signature(gdown.download_folder)}")
    except Exception:
        pass
    try:
        print(f"download sig:        {inspect.signature(gdown.download)}")
    except Exception:
        pass

    for idx, raw in enumerate(URLS, 1):
        kind, fid = _extract_id(raw)
        print(f"\n=== {idx}. [{kind}] {fid} ===")
        dest = OUT_ROOT / f"test_{idx:02d}"
        dest.mkdir(exist_ok=True)
        if kind == "folder":
            url = f"https://drive.google.com/drive/folders/{fid}"
            try:
                paths = gdown.download_folder(url=url, output=str(dest), quiet=True)
                if paths:
                    print(f"  download_folder OK: {len(paths)} files")
                else:
                    print(f"  download_folder OK but empty (0 files)")
            except Exception as e:
                print(f"  download_folder FAIL: {type(e).__name__}: {e}")
        else:
            url = f"https://drive.google.com/uc?id={fid}"
            target = dest / "file.bin"
            try:
                got = gdown.download(url=url, output=str(target), quiet=True, fuzzy=True)
                if got and os.path.exists(got):
                    print(f"  download OK: {got} ({os.path.getsize(got)} bytes)")
                else:
                    print(f"  download returned: {got}")
            except Exception as e:
                print(f"  download FAIL: {type(e).__name__}: {e}")

    total = sum(1 for p in OUT_ROOT.rglob("*") if p.is_file())
    print(f"\n--- TOTAL: {total} files ingested locally ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
