"""Push all 29 kernels to Kaggle; on error, retry with a versioned fallback slug.

For each kernel directory under kaggle/kernels/:

1. Try a normal `kaggle kernels push`.
2. If it fails, create a fallback kernel with id `<original>-v2` and push that.
3. Record outcome per kernel.

Requires KAGGLE_API_TOKEN env var to be set.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KERNELS = Path("kaggle/kernels")
REPORT = Path("docs/review/push_with_fallback_report.md")


def run_push(kernel_dir: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        ["kaggle", "kernels", "push", "-p", str(kernel_dir)],
        capture_output=True,
        text=True,
        env=env,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode, out.strip()


def push_fallback(kernel_dir: Path, meta: dict) -> tuple[str, str]:
    """Copy kernel to a temp dir with a -v2 id and push that."""
    fallback_id = meta["id"] + "-v2"
    fallback_title = "v2 " + meta["title"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / kernel_dir.name
        shutil.copytree(kernel_dir, tmp_path)
        fb_meta_path = tmp_path / "kernel-metadata.json"
        fb_meta = json.loads(fb_meta_path.read_text("utf-8"))
        fb_meta["id"] = fallback_id
        fb_meta["title"] = fallback_title
        fb_meta_path.write_text(json.dumps(fb_meta, indent=2) + "\n", "utf-8")
        rc, out = run_push(tmp_path)
        return ("FALLBACK_OK" if rc == 0 else "FALLBACK_FAIL"), f"id={fallback_id}\n{out}"


def main() -> int:
    if not os.environ.get("KAGGLE_API_TOKEN"):
        print("ERROR: KAGGLE_API_TOKEN env var must be set", file=sys.stderr)
        return 2

    kernel_dirs = sorted(d for d in KERNELS.iterdir() if d.is_dir())
    print(f"Found {len(kernel_dirs)} kernels\n")

    results = []
    for kd in kernel_dirs:
        meta = json.loads((kd / "kernel-metadata.json").read_text("utf-8"))
        kid = meta["id"]
        title = meta["title"]
        print(f"--- {kd.name}")
        print(f"    id:    {kid}")
        print(f"    title: {title}")
        rc, out = run_push(kd)
        if rc == 0:
            status = "OK"
            detail = out.splitlines()[-3:] if out else []
            detail = "\n".join(detail)
            print(f"    OK")
        else:
            short_err = out.splitlines()[-1] if out else "(no output)"
            print(f"    FAIL: {short_err}")
            print(f"    Attempting -v2 fallback...")
            status, detail = push_fallback(kd, meta)
            short = detail.splitlines()[-1] if detail else "(no output)"
            print(f"    {status}: {short}")
        results.append({
            "dir": kd.name,
            "id": kid,
            "title": title,
            "status": status,
            "detail": detail,
        })

    # Write report
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    ok = [r for r in results if r["status"] == "OK"]
    fb_ok = [r for r in results if r["status"] == "FALLBACK_OK"]
    failed = [r for r in results if r["status"] == "FALLBACK_FAIL"]

    lines = [
        "# Kaggle Push With Fallback Report",
        "",
        "Ran `scripts/push_all_with_fallback.py` against all 29 kernels.",
        "",
        "## Summary",
        "",
        f"- Pushed cleanly (version bumped on existing slug): {len(ok)}",
        f"- Pushed to fallback `-v2` slug (original push failed): {len(fb_ok)}",
        f"- Completely failed: {len(failed)}",
        "",
        "## Details",
        "",
        "| Dir | Original id | Status | Title |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| `{r['dir']}` | `{r['id']}` | {r['status']} | {r['title']} |")

    lines.append("")
    if failed:
        lines.append("## Complete failures")
        lines.append("")
        for r in failed:
            lines.append(f"### {r['dir']}")
            lines.append("```")
            lines.append(r['detail'])
            lines.append("```")
            lines.append("")

    if fb_ok:
        lines.append("## Fallback URLs")
        lines.append("")
        lines.append("These kernels could not update in place; a `-v2` slug was created instead. Delete the old orphans on Kaggle manually, or leave them.")
        lines.append("")
        for r in fb_ok:
            fb_slug = r['id'].split('/', 1)[1] + "-v2"
            lines.append(f"- `{r['dir']}`: https://www.kaggle.com/code/taylorsamarel/{fb_slug}")
        lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print()
    print(f"Clean push: {len(ok)}")
    print(f"Fallback push: {len(fb_ok)}")
    print(f"Failed: {len(failed)}")
    print(f"Report: {REPORT}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
