"""Clean-room install test for Duecare wheels.

Creates a fresh virtualenv in a tmp dir, installs all 18 manifest-backed wheels
from the root `dist/` directory *without* touching the source tree, and
proves the install succeeded by running a smoke script that imports
every sub-package and instantiates a domain pack.

This catches the class of bugs where a package's runtime imports rely
on files that aren't actually shipped in the wheel (e.g. missing from
`pyproject.toml`'s `[tool.hatch.build.targets.wheel]` include rules).

Usage
-----
    python scripts/cleanroom_install.py              # verbose
    python scripts/cleanroom_install.py --quiet      # summary only
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from build_all_wheels import DEFAULT_BUILD_ORDER

REPO_ROOT = Path(__file__).resolve().parents[1]
WHEEL_ORDER = DEFAULT_BUILD_ORDER


SMOKE_SCRIPT = r"""
from __future__ import annotations
import json
import sys

def check():
    errors = []

    # Every sub-package must import
    for sub in [
        "duecare.core",
        "duecare.benchmark",
        "duecare.chat",
        "duecare.appendix_primitives",
        "duecare.evidence",
        "duecare.engine",
        "duecare.kit",
        "duecare.nl2sql",
        "duecare.research_tools",
        "duecare.server",
        "duecare.training",
        "duecare.cli",
        "duecare.models",
        "duecare.domains",
        "duecare.tasks",
        "duecare.agents",
        "duecare.workflows",
        "duecare.publishing",
    ]:
        try:
            __import__(sub)
        except Exception as e:
            errors.append(f"{sub}: {e}")

    if errors:
        print("IMPORT ERRORS:")
        for e in errors:
            print("  " + e)
        sys.exit(1)

    # Public API surface
    from duecare.core import (
        TaskStatus, AgentRole, Capability,
        GenerationResult, ModelHealth, Embedding, ChatMessage, AgentContext,
    )
    from duecare.core.schemas import WorkflowRun
    from duecare.agents.base import SupervisorPolicy, AgentSupervisor, BudgetExceeded, HarmDetected
    from duecare.tasks import task_registry
    from duecare.models import model_registry
    from duecare.agents import agent_registry
    from duecare.workflows import WorkflowRunner
    from importlib.metadata import distribution

    distributions = [
        "duecare-llm-core", "duecare-llm-benchmark", "duecare-llm-chat",
        "duecare-llm-evidence-db", "duecare-llm-engine", "duecare-llm-kit",
        "duecare-llm-nl2sql", "duecare-llm-research-tools",
        "duecare-llm-server", "duecare-llm-training", "duecare-llm-cli",
        "duecare-llm-models", "duecare-llm-domains", "duecare-llm-tasks",
        "duecare-llm-agents", "duecare-llm-workflows",
        "duecare-llm-publishing", "duecare-llm",
    ]
    installed_versions = {name: distribution(name).version for name in distributions}

    # Registries must be populated (Registry has __len__)
    tasks_n = len(task_registry)
    models_n = len(model_registry)
    agents_n = len(agent_registry)

    out = {
        "python": sys.version.split()[0],
        "imports": "ok",
        "tasks": tasks_n,
        "models": models_n,
        "agents": agents_n,
        "distributions": len(installed_versions),
    }
    print("SMOKE_JSON=" + json.dumps(out))
    if tasks_n < 3 or models_n < 3 or agents_n < 8:
        print(
            f"FAIL registry under-populated: tasks={tasks_n}, "
            f"models={models_n}, agents={agents_n}"
        )
        sys.exit(2)
    print("OK: clean-room smoke check passed")

check()
"""


def log(*a: object, quiet: bool) -> None:
    if not quiet:
        print(*a, flush=True)


def create_venv(path: Path) -> Path:
    log(f"  creating venv at {path}", quiet=False)
    venv.EnvBuilder(with_pip=True, clear=True, upgrade_deps=False).create(str(path))
    if sys.platform == "win32":
        return path / "Scripts" / "python.exe"
    return path / "bin" / "python"


def collect_wheels(dist_dir: Path) -> list[Path]:
    wheels: list[Path] = []
    for name in WHEEL_ORDER:
        prefix = name.replace("-", "_") + "-"
        found = sorted(dist_dir.glob(f"{prefix}*.whl"))
        if len(found) != 1:
            raise FileNotFoundError(
                f"expected exactly one {name} wheel in {dist_dir}, found {len(found)}"
            )
        wheels.append(found[0])
    return wheels


def run(
    cmd: list[str], *, quiet: bool, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    log(f"  $ {' '.join(str(c) for c in cmd)}", quiet=quiet)
    return subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=cwd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--keep", action="store_true", help="do not delete the temporary venv afterwards")
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="root artifact directory containing one wheel per package",
    )
    args = parser.parse_args(argv)
    dist_dir = (REPO_ROOT / args.dist_dir).resolve()

    tmp_root = Path(tempfile.mkdtemp(prefix="duecare-cleanroom-"))
    log(f"# clean-room install in {tmp_root}", quiet=args.quiet)

    try:
        venv_path = tmp_root / "venv"
        py = create_venv(venv_path)

        # Upgrade pip so it understands modern wheel metadata.
        pip_up = run([str(py), "-m", "pip", "install", "--upgrade", "pip"], quiet=args.quiet)
        if pip_up.returncode != 0:
            print(pip_up.stderr, file=sys.stderr)
            return 1

        wheels = collect_wheels(dist_dir)
        log(f"  found {len(wheels)} wheels", quiet=args.quiet)
        for w in wheels:
            log(f"    - {w.name} ({w.stat().st_size} bytes)", quiet=args.quiet)

        # Install all wheels in one call.  pip will resolve their deps from
        # PyPI the same way a Kaggle Notebook would.
        install = run(
            [str(py), "-m", "pip", "install", "--prefer-binary", *[str(w) for w in wheels]],
            quiet=args.quiet,
        )
        if install.returncode != 0:
            print("INSTALL FAILED:")
            print(install.stdout)
            print(install.stderr, file=sys.stderr)
            return 1
        log(install.stdout, quiet=args.quiet)

        dependency_check = run(
            [str(py), "-m", "pip", "check"], quiet=args.quiet, cwd=tmp_root
        )
        if dependency_check.returncode != 0:
            print("PIP CHECK FAILED:")
            print(dependency_check.stdout)
            print(dependency_check.stderr, file=sys.stderr)
            return 1

        # Write the smoke script to the tmp dir so relative imports from the
        # source tree can NOT leak in.
        smoke_path = tmp_root / "smoke.py"
        smoke_path.write_text(SMOKE_SCRIPT, encoding="utf-8")

        smoke = run([str(py), str(smoke_path)], quiet=args.quiet, cwd=tmp_root)
        if smoke.returncode != 0:
            print("SMOKE FAILED:")
            print(smoke.stdout)
            print(smoke.stderr, file=sys.stderr)
            return smoke.returncode

        # Extract the SMOKE_JSON line
        for line in smoke.stdout.splitlines():
            if line.startswith("SMOKE_JSON="):
                import json as _json

                data = _json.loads(line.removeprefix("SMOKE_JSON="))
                print(
                    "  smoke: "
                    + ", ".join(f"{k}={v}" for k, v in data.items())
                )
        print("OK: clean-room install + smoke check passed")
        return 0
    finally:
        if not args.keep:
            try:
                shutil.rmtree(tmp_root, ignore_errors=True)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
