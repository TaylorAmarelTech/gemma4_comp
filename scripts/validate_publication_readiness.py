#!/usr/bin/env python3
"""Run DueCare's deterministic, model-free publication and handoff gates.

The core scope is the portable reviewer/release check. The handoff scope checks
succession documents plus live pickup consistency. The training scope is
stricter and may intentionally fail while a dataset curation queue is open. No
gate in this file calls Ollama, a hosted model, or the network.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Gate:
    name: str
    args: tuple[str, ...]
    purpose: str


@dataclass(frozen=True)
class GateResult:
    gate: Gate
    returncode: int
    output: str
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.returncode == 0 and self.error is None


CORE_GATES: tuple[Gate, ...] = (
    Gate("public surface", ("scripts/validate_public_surface.py",),
         "documentation, links, routes, lane order, and generated public metadata"),
    Gate("public messaging", ("scripts/validate_public_messaging.py",),
         "canonical claims and active-surface wording"),
    Gate("source harness smoke", ("scripts/verify.py",),
         "checked-out harness imports and published count floors"),
    Gate("published dataset claims", ("scripts/verify_training_dataset_claims.py",),
         "manifest-backed public dataset counts"),
    Gate("model fallback registry", ("scripts/validate_model_fallback_registry.py",),
         "declared fallback IDs and registry structure"),
    Gate(
        "provider budget coverage",
        ("scripts/validate_provider_budget_coverage.py",),
        "all five registered model transports reserve against one run budget",
    ),
    Gate("active Kaggle kernels", ("scripts/validate_main_kaggle_kernels.py",),
         "active kernel syntax, metadata, and static contracts"),
    Gate("Kaggle page sources", ("scripts/validate_kaggle_page_sources.py",),
         "generated static-page source consistency"),
    Gate(
        "deferred work register",
        ("scripts/validate_deferred_work.py",),
        "outstanding work has explicit owners, boundaries, actions, and acceptance gates",
    ),
    Gate("package release surface", ("scripts/validate_package_release.py",),
         "18-package inventory, build order, install truth, and sole publisher ownership"),
    Gate("package test collection", ("-m", "pytest", "packages", "--collect-only", "-q"),
         "all package tests remain discoverable"),
)

TRAINING_GATES: tuple[Gate, ...] = (
    Gate(
        "corridor curation completion",
        ("scripts/validate_corridor_curation.py", "--require-complete"),
        "75 source-bound rows, lineage isolation, privacy, and two-person adjudication",
    ),
    Gate("strict training-data quality", ("scripts/audit_training_quality.py", "--require-clean"),
         "privacy, leakage, citation, and corridor-shortcut checks"),
    Gate("corridor expansion plan", ("scripts/build_corridor_expansion_plan.py", "--validate"),
         "the latest audit yields a safe metadata-only curation plan"),
    Gate("training provenance", ("scripts/validate_training_provenance.py",),
         "registry fingerprints, model-card evidence, and trainer inputs"),
)

HANDOFF_GATES: tuple[Gate, ...] = (
    Gate(
        "maintainer handoff",
        ("scripts/validate_maintainer_handoff.py",),
        "succession structure, discovery links, local links, and privacy-safe content",
    ),
    Gate(
        "live pickup consistency",
        ("scripts/validate_project_bible_pickup.py",),
        "live paused state and generated handoff consistency",
    ),
)


def gates_for_scope(scope: str) -> tuple[Gate, ...]:
    if scope == "core":
        return CORE_GATES
    if scope == "handoff":
        return HANDOFF_GATES
    if scope == "training":
        return TRAINING_GATES
    if scope == "all":
        return CORE_GATES + HANDOFF_GATES + TRAINING_GATES
    raise ValueError(f"unknown publication scope: {scope}")


def offline_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    """Return a child environment that fails closed for model/network helpers."""
    env = dict(os.environ if source is None else source)
    env.update({
        "DUECARE_MAX_PLANNED_MODEL_CALLS": "0",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "WANDB_MODE": "disabled",
        "PYTHONUTF8": "1",
    })
    return env


def run_gate(gate: Gate, *, timeout: float = 900.0) -> GateResult:
    command = [sys.executable, *gate.args]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=offline_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(part for part in (exc.stdout or "", exc.stderr or "") if part)
        return GateResult(gate, 124, output, f"timed out after {timeout:g}s")
    except OSError as exc:
        return GateResult(gate, 126, "", str(exc))
    output = "\n".join(
        part.rstrip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    return GateResult(gate, completed.returncode, output)


def _output_tail(output: str, limit: int = 30) -> str:
    lines = output.splitlines()
    return "\n".join(lines[-limit:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope",
        choices=("core", "handoff", "training", "all"),
        default="core",
        help=(
            "core is portable; handoff adds succession/live pickup checks; "
            "training adds strict data/provenance gates"
        ),
    )
    parser.add_argument("--fail-fast", action="store_true", help="stop after the first failed gate")
    parser.add_argument(
        "--show-output", action="store_true", help="show successful child output too"
    )
    parser.add_argument("--timeout", type=float, default=900.0, help="per-gate timeout in seconds")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    gates = gates_for_scope(args.scope)
    print(f"DueCare publication readiness: scope={args.scope} (offline, no model calls)")
    failures: list[GateResult] = []
    for index, gate in enumerate(gates, 1):
        print(f"[{index}/{len(gates)}] {gate.name}: {gate.purpose}", flush=True)
        result = run_gate(gate, timeout=args.timeout)
        status = "PASS" if result.passed else "FAIL"
        print(f"        {status} (exit {result.returncode})", flush=True)
        if args.show_output or not result.passed:
            if result.error:
                print(f"        {result.error}")
            if result.output:
                print(_output_tail(result.output))
        if not result.passed:
            failures.append(result)
            if args.fail_fast:
                break

    print()
    if failures:
        names = ", ".join(result.gate.name for result in failures)
        print(f"NOT READY: {len(failures)} gate(s) failed: {names}")
        return 1
    print(f"READY: all {len(gates)} {args.scope} gate(s) passed without model or network calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
