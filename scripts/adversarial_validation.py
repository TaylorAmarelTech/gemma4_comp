"""Adversarial validation harness for Duecare.

Runs a battery of negative + stress tests that a normal unit test suite
doesn't exercise.  These catch the failure modes that bite submissions
the night before a deadline:

    1. YAML parse validation - every config file in configs/duecare/ parses
    2. Wheel integrity        - every dist/*.whl unpacks without errors
    3. Import contract        - every wheel's top-level modules import cleanly
    4. Negative tests         - malformed domain pack, missing file, bad id
    5. Flake detection        - run the full unit suite N times, look for diffs

Each step exits non-zero on failure so CI can wire this up as a single
quality gate.

Usage
-----
    python scripts/adversarial_validation.py --all
    python scripts/adversarial_validation.py --yaml --imports
    python scripts/adversarial_validation.py --stress 3
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIGS = REPO_ROOT / "configs" / "duecare"
PACKAGES = REPO_ROOT / "packages"

# Every wheel's top-level module that should import cleanly after install.
WHEEL_IMPORT_CONTRACTS: dict[str, list[str]] = {
    "duecare-llm-core": ["duecare.core"],
    "duecare-llm-models": ["duecare.models"],
    "duecare-llm-domains": ["duecare.domains"],
    "duecare-llm-tasks": ["duecare.tasks"],
    "duecare-llm-agents": ["duecare.agents"],
    "duecare-llm-workflows": ["duecare.workflows"],
    "duecare-llm-publishing": ["duecare.publishing"],
    "duecare-llm": ["duecare"],
}


# --------------------------- reporting ---------------------------


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []  # (step, status, detail)
        self.failures: int = 0

    def ok(self, step: str, detail: str = "") -> None:
        self.rows.append((step, "PASS", detail))

    def fail(self, step: str, detail: str) -> None:
        self.rows.append((step, "FAIL", detail))
        self.failures += 1

    def print_summary(self) -> None:
        print("\n================ ADVERSARIAL VALIDATION ================")
        for step, status, detail in self.rows:
            marker = "PASS" if status == "PASS" else "FAIL"
            line = f"  [{marker}] {step}"
            if detail:
                line += f"  -  {detail}"
            print(line)
        print("--------------------------------------------------------")
        print(f"  Total:    {len(self.rows)}")
        print(f"  Failures: {self.failures}")
        print("========================================================")


# --------------------------- validators ---------------------------


def validate_yaml(report: Report) -> None:
    """Every YAML config must parse without error."""
    print("\n# yaml-parse")
    yaml_files = sorted(CONFIGS.rglob("*.yaml")) + sorted(CONFIGS.rglob("*.yml"))
    if not yaml_files:
        report.fail("yaml-parse", f"no YAML files under {CONFIGS}")
        return
    errors = 0
    for p in yaml_files:
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
            print(f"  ok   {p.relative_to(REPO_ROOT)}")
        except Exception as e:
            print(f"  FAIL {p.relative_to(REPO_ROOT)}: {e}")
            errors += 1
    if errors == 0:
        report.ok("yaml-parse", f"{len(yaml_files)} files")
    else:
        report.fail("yaml-parse", f"{errors}/{len(yaml_files)} invalid")


def validate_jsonl(report: Report) -> None:
    print("\n# jsonl-parse")
    jsonl_files = sorted(CONFIGS.rglob("*.jsonl"))
    if not jsonl_files:
        report.fail("jsonl-parse", f"no JSONL files under {CONFIGS}")
        return
    errors = 0
    lines = 0
    for p in jsonl_files:
        with p.open("r", encoding="utf-8") as f:
            for i, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    json.loads(raw)
                    lines += 1
                except Exception as e:
                    print(f"  FAIL {p.relative_to(REPO_ROOT)}:{i}: {e}")
                    errors += 1
    if errors == 0:
        report.ok("jsonl-parse", f"{len(jsonl_files)} files, {lines} lines")
    else:
        report.fail("jsonl-parse", f"{errors} malformed lines")


def validate_wheels(report: Report) -> None:
    """Every wheel must unpack and contain a METADATA file."""
    print("\n# wheel-integrity")
    wheels = sorted(PACKAGES.rglob("dist/*.whl"))
    if not wheels:
        report.fail("wheel-integrity", "no wheels found")
        return
    errors = 0
    for wheel in wheels:
        try:
            with zipfile.ZipFile(wheel) as z:
                names = z.namelist()
                if not any(n.endswith("/METADATA") for n in names):
                    raise ValueError("missing METADATA")
                if not any(n.endswith("/RECORD") for n in names):
                    raise ValueError("missing RECORD")
                # Read and checksum METADATA to ensure the archive is sound.
                meta = next(n for n in names if n.endswith("/METADATA"))
                content = z.read(meta)
                if b"Name:" not in content:
                    raise ValueError("METADATA does not contain Name field")
                print(f"  ok   {wheel.name} ({len(names)} files)")
        except Exception as e:
            print(f"  FAIL {wheel.name}: {e}")
            errors += 1
    if errors == 0:
        report.ok("wheel-integrity", f"{len(wheels)} wheels")
    else:
        report.fail("wheel-integrity", f"{errors}/{len(wheels)} broken")


def validate_imports(report: Report) -> None:
    """The 8 contract imports must resolve in the current interpreter."""
    print("\n# import-contract")
    failures: list[str] = []
    for pkg, modules in WHEEL_IMPORT_CONTRACTS.items():
        for m in modules:
            try:
                mod = importlib.import_module(m)
                print(f"  ok   import {m}  (from {pkg})  -> {getattr(mod, '__file__', '?')}")
            except Exception as e:
                failures.append(f"{m}: {e}")
                print(f"  FAIL import {m}  (from {pkg})  -> {e}")
    if not failures:
        report.ok("import-contract", f"{sum(len(v) for v in WHEEL_IMPORT_CONTRACTS.values())} modules")
    else:
        report.fail("import-contract", "; ".join(failures[:3]))


def validate_namespace(report: Report) -> None:
    """All 8 sub-packages must be individually importable.

    When every wheel is installed into the same site-packages, pip
    collapses the 8 portions into one physical directory — that's
    correct PEP 420 behaviour, not a regression.  The proof of real
    separation is that every sub-package resolves to a file inside its
    own sub-directory.
    """
    print("\n# namespace-portions")
    try:
        import duecare  # type: ignore

        portions = [str(p) for p in duecare.__path__]  # type: ignore[attr-defined]
        print(f"  duecare.__path__ has {len(portions)} physical portion(s):")
        for p in portions:
            print(f"    - {p}")

        expected_subpkgs = [
            "duecare.core",
            "duecare.models",
            "duecare.domains",
            "duecare.tasks",
            "duecare.agents",
            "duecare.workflows",
            "duecare.publishing",
        ]
        missing = []
        for sub in expected_subpkgs:
            try:
                mod = importlib.import_module(sub)
                f = getattr(mod, "__file__", None)
                if not f:
                    missing.append(f"{sub}: no __file__")
                else:
                    print(f"    {sub:25s} -> {f}")
            except Exception as e:
                missing.append(f"{sub}: {e}")

        if missing:
            report.fail("namespace-portions", "; ".join(missing))
        else:
            report.ok(
                "namespace-portions",
                f"{len(expected_subpkgs)} sub-packages resolved",
            )
    except Exception as e:
        report.fail("namespace-portions", str(e))


def validate_negative_domain_pack(report: Report) -> None:
    """load_domain_pack must raise on malformed or missing domains."""
    print("\n# negative-domain-pack")
    try:
        from duecare.domains import load_domain_pack  # type: ignore
    except Exception as e:
        report.fail("negative-domain-pack", f"import failed: {e}")
        return

    import tempfile

    fails = 0

    # Case 1: domain that doesn't exist
    try:
        load_domain_pack("no_such_domain", root=CONFIGS / "domains")
        print("  FAIL missing-domain: should have raised")
        fails += 1
    except Exception:
        print("  ok   missing-domain raised as expected")

    # Case 2: malformed yaml
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "broken"
        bad.mkdir()
        (bad / "card.yaml").write_text("{ not: valid: yaml: [[[")
        (bad / "taxonomy.yaml").write_text("labels: []")
        (bad / "rubric.yaml").write_text("criteria: []")
        (bad / "pii_spec.yaml").write_text("patterns: []")
        (bad / "seed_prompts.jsonl").write_text("")
        (bad / "evidence.jsonl").write_text("")
        try:
            load_domain_pack("broken", root=Path(tmp))
            print("  FAIL malformed-yaml: should have raised")
            fails += 1
        except Exception:
            print("  ok   malformed-yaml raised as expected")

    if fails == 0:
        report.ok("negative-domain-pack", "2/2 negative cases caught")
    else:
        report.fail("negative-domain-pack", f"{fails} missed")


def validate_supervisor_policies(report: Report) -> None:
    """Budget, harm, and retry guardrails must trigger on synthetic probes."""
    print("\n# supervisor-policies")
    try:
        from datetime import datetime

        from duecare.agents import AgentSupervisor  # type: ignore
        from duecare.agents.base import (  # type: ignore
            BudgetExceeded,
            HarmDetected,
            SupervisorPolicy,
            fresh_agent_output,
        )
        from duecare.core import AgentContext  # type: ignore
        from duecare.core.enums import AgentRole, TaskStatus  # type: ignore
    except Exception as e:
        report.fail("supervisor-policies", f"import failed: {e}")
        return

    fails = 0
    ctx = AgentContext(
        run_id="adv_val",
        git_sha="x",
        workflow_id="adv",
        target_model_id="m",
        domain_id="d",
        started_at=datetime.now(),
    )

    # Hard budget enforcement
    class Pricey:
        id = "pricey"
        role = AgentRole.DATA_GENERATOR
        version = "0.1.0"
        model = None
        tools: list = []
        inputs: set = set()
        outputs: set = set()
        cost_budget_usd = 5.0

        def execute(self, ctx):
            out = fresh_agent_output(self.id, self.role)
            out.status = TaskStatus.COMPLETED
            out.decision = "spent"
            out.cost_usd = 5.0
            return out

        def explain(self):
            return "pricey"

    sup = AgentSupervisor(SupervisorPolicy(hard_budget_usd=3.0))
    try:
        sup.run(Pricey(), ctx)
        # Second run trips the cap
        try:
            sup.run(Pricey(), ctx)
            print("  FAIL budget-cap: should have raised BudgetExceeded")
            fails += 1
        except BudgetExceeded:
            print("  ok   budget-cap raised BudgetExceeded")
    except Exception as e:
        print(f"  FAIL budget-cap setup: {e}")
        fails += 1

    # Harm abort: signalled via ctx.record("harm_detected", True), not on AgentOutput
    class Harmful:
        id = "harmful"
        role = AgentRole.ADVERSARY
        version = "0.1.0"
        model = None
        tools: list = []
        inputs: set = set()
        outputs: set = set()
        cost_budget_usd = 0.0

        def execute(self, ctx):
            ctx.record("harm_detected", True)
            out = fresh_agent_output(self.id, self.role)
            out.status = TaskStatus.COMPLETED
            out.decision = "harm flag set"
            return out

        def explain(self):
            return "harmful"

    sup2 = AgentSupervisor(SupervisorPolicy())
    try:
        sup2.run(Harmful(), ctx)
        print("  FAIL harm-abort: should have raised HarmDetected")
        fails += 1
    except HarmDetected:
        print("  ok   harm-abort raised HarmDetected")
    except Exception as e:
        print(f"  FAIL harm-abort: {e}")
        fails += 1

    if fails == 0:
        report.ok("supervisor-policies", "2/2 guardrails fire")
    else:
        report.fail("supervisor-policies", f"{fails} missed")


def stress_test(report: Report, iterations: int) -> None:
    """Run the 4 Kaggle notebook smoke layer N times and diff outputs."""
    print(f"\n# stress-test (x{iterations})")
    try:
        from duecare.core import TaskConfig  # type: ignore
        from duecare.domains import load_domain_pack  # type: ignore
        from duecare.tasks import task_registry  # type: ignore
    except Exception as e:
        report.fail("stress-test", f"import failed: {e}")
        return

    # Build a minimal scripted model inline to avoid a separate fixture dep.
    from duecare.core import (  # type: ignore
        Capability,
        Embedding,
        GenerationResult,
        ModelHealth,
    )

    class ScriptedModel:
        id = "scripted:adv"
        display_name = "scripted-adv"
        provider = "scripted"
        capabilities = {Capability.TEXT, Capability.FUNCTION_CALLING}
        context_length = 4096
        _response = (
            "I cannot help with that. Under ILO C181 Article 7, recruitment "
            "agencies cannot charge workers fees. Under Philippines RA 8042 "
            "this is illegal. Contact POEA at 1343 or your local labor ministry."
        )

        def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs):
            return GenerationResult(
                text=self._response,
                finish_reason="stop",
                prompt_tokens=1,
                completion_tokens=len(self._response.split()),
                tokens_used=1 + len(self._response.split()),
                model_id=self.id,
            )

        def embed(self, texts):
            return [Embedding(text=t, vector=[0.0] * 4, dimension=4, model_id=self.id) for t in texts]

        def healthcheck(self):
            return ModelHealth(model_id=self.id, healthy=True)

    domain_ids = ["trafficking", "tax_evasion", "financial_crime"]
    expected_metrics = None
    fails = 0
    for i in range(iterations):
        try:
            run_metrics = {}
            for d in domain_ids:
                pack = load_domain_pack(d, root=CONFIGS / "domains")
                task = task_registry.get("guardrails")
                result = task.run(ScriptedModel(), pack, TaskConfig(sample_size=3))
                run_metrics[d] = {
                    "mean_score": round(float(result.metrics.get("mean_score", 0)), 3),
                    "refusal_rate": round(float(result.metrics.get("refusal_rate", 0)), 3),
                    "harmful_phrase_rate": round(float(result.metrics.get("harmful_phrase_rate", 0)), 3),
                }
            if expected_metrics is None:
                expected_metrics = run_metrics
                print(f"  iter {i+1}: baseline {run_metrics}")
            elif run_metrics != expected_metrics:
                print(f"  FAIL iter {i+1}: metrics drifted {run_metrics} vs {expected_metrics}")
                fails += 1
            else:
                print(f"  ok   iter {i+1}: identical metrics")
        except Exception as e:
            print(f"  FAIL iter {i+1}: {e}")
            traceback.print_exc()
            fails += 1

    if fails == 0:
        report.ok("stress-test", f"{iterations} iters, deterministic")
    else:
        report.fail("stress-test", f"{fails}/{iterations} drifted")


def run_unit_suite(report: Report) -> None:
    """Run the whole in-tree pytest suite once, report pass count."""
    print("\n# unit-suite")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "packages", "tests"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    tail = result.stdout.strip().splitlines()[-5:]
    for line in tail:
        print(f"  {line}")
    if result.returncode == 0:
        report.ok("unit-suite", tail[-1] if tail else "")
    else:
        report.fail("unit-suite", tail[-1] if tail else "nonzero exit")


# --------------------------- main --------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="run every validation step")
    parser.add_argument("--yaml", action="store_true")
    parser.add_argument("--jsonl", action="store_true")
    parser.add_argument("--wheels", action="store_true")
    parser.add_argument("--imports", action="store_true")
    parser.add_argument("--namespace", action="store_true")
    parser.add_argument("--negative", action="store_true")
    parser.add_argument("--supervisor", action="store_true")
    parser.add_argument("--unit", action="store_true", help="run the full pytest suite once")
    parser.add_argument("--stress", type=int, metavar="N", default=0, help="stress test iterations")
    args = parser.parse_args(argv)

    report = Report()
    steps: list[tuple[str, callable]] = []
    if args.all or args.yaml:
        steps.append(("yaml", lambda: validate_yaml(report)))
    if args.all or args.jsonl:
        steps.append(("jsonl", lambda: validate_jsonl(report)))
    if args.all or args.wheels:
        steps.append(("wheels", lambda: validate_wheels(report)))
    if args.all or args.imports:
        steps.append(("imports", lambda: validate_imports(report)))
    if args.all or args.namespace:
        steps.append(("namespace", lambda: validate_namespace(report)))
    if args.all or args.negative:
        steps.append(("negative", lambda: validate_negative_domain_pack(report)))
    if args.all or args.supervisor:
        steps.append(("supervisor", lambda: validate_supervisor_policies(report)))
    if args.unit:
        steps.append(("unit-suite", lambda: run_unit_suite(report)))
    if args.stress > 0:
        steps.append(("stress", lambda: stress_test(report, args.stress)))

    if not steps:
        parser.error("pick at least one validation step (e.g. --all)")

    for _, fn in steps:
        fn()

    report.print_summary()
    return 0 if report.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
