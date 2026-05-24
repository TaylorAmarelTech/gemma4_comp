"""Validate the non-archived DueCare Kaggle kernel.py files.

This is a static compatibility gate. It parses the active/public Kaggle
script kernels without executing them, then checks for the boot-path tokens
that make them runnable after copy/paste into Kaggle.

Appendix and archived notebooks are intentionally out of scope.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class KernelContract:
    path: str
    tier: str
    role: str
    kaggle_id: str
    enable_gpu: bool
    required_tokens: tuple[str, ...]


KERNELS: tuple[KernelContract, ...] = (
    KernelContract(
        path="kaggle/01-duecare-exploration-workbench/kernel.py",
        tier="active",
        role="reviewer workbench",
        kaggle_id="taylorsamarel/duecare-app",
        enable_gpu=True,
        required_tokens=(
            "DueCare App",
            "DUECARE_REQUIRED_CHAT_VERSION",
            "TaylorAmarelTech/gemma4_comp",
            "create_app",
            "default_harness",
            "cloudflared",
            "trycloudflare.com",
            "_verify_portable_app_contract",
            "/kaggle/working",
        ),
    ),
    KernelContract(
        path="kaggle/02-live-demo/kernel.py",
        tier="active",
        role="focused live demo",
        kaggle_id="taylorsamarel/duecare-live-demo",
        enable_gpu=True,
        required_tokens=(
            "DueCare Live Demo",
            "DUECARE_VERSION",
            "TaylorAmarelTech/gemma4_comp",
            "create_app",
            "cloudflared",
            "open_tunnel",
            "/kaggle/working",
        ),
    ),
    KernelContract(
        path="kaggle/A-00-omni-experiment-workbench/kernel.py",
        tier="active",
        role="quantitative control plane",
        kaggle_id="taylorsamarel/duecare-fine-tuning-and-evaluation",
        enable_gpu=True,
        required_tokens=(
            "DueCare Fine-tuning and Evaluation",
            "DUECARE_REPO",
            "TaylorAmarelTech/gemma4_comp",
            "DUECARE_PACKAGES",
            "build_minimal_shell",
            "trycloudflare.com",
            "/api/a00/pipeline/run",
            "/kaggle/working",
        ),
    ),
    KernelContract(
        path="kaggle/03-universal-llm-benchmark/kernel.py",
        tier="optional",
        role="universal endpoint benchmark",
        kaggle_id="taylorsamarel/duecare-universal-llm-benchmark",
        enable_gpu=False,
        required_tokens=(
            "DueCare Universal LLM Benchmark",
            "DEFAULT_JUDGE_MODEL",
            "make_app",
            "cloudflared",
            "trycloudflare.com",
            "/kaggle/working/universal-benchmark",
        ),
    ),
    KernelContract(
        path="kaggle/04-kaggle-community-benchmark/kernel.py",
        tier="optional",
        role="Kaggle Community Benchmark",
        kaggle_id="taylorsamarel/duecare-kaggle-community-benchmark",
        enable_gpu=False,
        required_tokens=(
            "DueCare Kaggle Community Benchmark",
            "kaggle_benchmarks",
            "duecare.chat.benchmark",
            "default_fallback_rows",
            "/kaggle/working/duecare-kbench",
        ),
    ),
)


def _line_has_conflict_marker(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("<<<<<<<")
        or stripped.startswith(">>>>>>>")
        or stripped.startswith("|||||||")
    )


def validate_kernel(contract: KernelContract) -> list[str]:
    path = REPO_ROOT / contract.path
    failures: list[str] = []
    if not path.exists():
        return [f"missing kernel file: {contract.path}"]
    if "_archive" in path.parts or path.parts[-2] == "kernels":
        return [f"kernel gate should not target archived/legacy path: {contract.path}"]

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"not UTF-8 readable: {exc}"]

    if not text.strip():
        failures.append("file is empty")

    conflict_lines = [
        i for i, line in enumerate(text.splitlines(), start=1)
        if _line_has_conflict_marker(line)
    ]
    if conflict_lines:
        failures.append(f"merge-conflict marker(s) at line(s): {conflict_lines[:5]}")

    try:
        ast.parse(text, filename=contract.path)
    except SyntaxError as exc:
        failures.append(f"syntax error: line {exc.lineno}: {exc.msg}")

    if "from __future__ import annotations" not in text:
        failures.append("missing future annotations import")

    missing = [token for token in contract.required_tokens if token not in text]
    if missing:
        failures.append("missing required token(s): " + ", ".join(missing))

    metadata_path = path.with_name("kernel-metadata.json")
    if not metadata_path.exists():
        failures.append("missing kernel-metadata.json")
        return failures
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        failures.append(f"kernel-metadata.json is not valid UTF-8 JSON: {exc}")
        return failures

    expected_metadata = {
        "id": contract.kaggle_id,
        "code_file": "kernel.py",
        "language": "python",
        "kernel_type": "script",
        "enable_internet": True,
        "enable_gpu": contract.enable_gpu,
    }
    for key, expected in expected_metadata.items():
        actual = metadata.get(key)
        if actual != expected:
            failures.append(
                f"metadata {key!r} = {actual!r}; expected {expected!r}"
            )

    return failures


def main() -> int:
    total_failures = 0
    print("Main Kaggle kernel compatibility gate")
    print("=" * 72)
    for contract in KERNELS:
        failures = validate_kernel(contract)
        label = f"{contract.tier:8s} {contract.path} ({contract.role})"
        if failures:
            total_failures += len(failures)
            print(f"[FAIL] {label}")
            for failure in failures:
                print(f"  - {failure}")
        else:
            print(f"[OK  ] {label}")
    print("=" * 72)
    if total_failures:
        print(f"FAILED: {total_failures} finding(s)")
        return 1
    print(
        "PASS: all active/optional main Kaggle kernels parse, keep their "
        "boot tokens, and match Kaggle metadata"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
