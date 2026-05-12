#!/usr/bin/env python3
"""Install and validate a local DueCare consumer setup.

The script is intentionally conservative:

- ``--dry-run`` prints every action without installing packages or writing files.
- ``--source auto`` uses editable local packages when run from this repository,
  and PyPI package names when copied outside the repository.
- Model setup writes a local manifest only; it does not download model weights or
  send any prompt data to a remote service.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal, cast

Mode = Literal["desktop", "mobile", "browser"]
Source = Literal["auto", "local", "pypi"]

MIN_PYTHON = (3, 11)
MIN_RAM_GB = 8
MIN_DISK_GB = 10
DEFAULT_HOME = Path.home() / ".duecare"

LOCAL_PACKAGE_ORDER = [
    "duecare-llm-core",
    "duecare-llm-models",
    "duecare-llm-domains",
    "duecare-llm-tasks",
    "duecare-llm-evidence-db",
    "duecare-llm-engine",
    "duecare-llm-nl2sql",
    "duecare-llm-research-tools",
    "duecare-llm-benchmark",
    "duecare-llm-server",
    "duecare-llm-cli",
]

PYPI_PACKAGES_BY_MODE: dict[Mode, list[str]] = {
    "desktop": [
        "duecare-llm-cli",
        "duecare-llm-models",
        "duecare-llm-domains",
        "duecare-llm-tasks",
    ],
    "mobile": ["duecare-llm-core", "duecare-llm-models", "duecare-llm-tasks"],
    "browser": ["duecare-llm-core", "duecare-llm-models", "duecare-llm-tasks"],
}

MODEL_EXTRA_PACKAGES_BY_MODE: dict[Mode, list[str]] = {
    "desktop": ["ollama>=0.4.0"],
    "mobile": ["llama-cpp-python>=0.3.0"],
    "browser": ["llama-cpp-python>=0.3.0"],
}

MODEL_CONFIGS: dict[Mode, dict[str, str | None]] = {
    "desktop": {"primary": "gemma4:e2b", "fallback": "gemma4:e4b"},
    "mobile": {"primary": "gemma-4-e2b-q4", "fallback": None},
    "browser": {"primary": "gemma-4-e2b-q8", "fallback": None},
}

REQUIRED_MODULES_BY_MODE: dict[Mode, list[str]] = {
    "desktop": ["duecare.server", "duecare.engine", "duecare.evidence"],
    "mobile": ["duecare.core", "duecare.models", "duecare.tasks"],
    "browser": ["duecare.core", "duecare.models", "duecare.tasks"],
}


class ConsumerSetup:
    """Handle local installation of the DueCare safety harness."""

    def __init__(
        self,
        *,
        mode: Mode = "desktop",
        source: Source = "auto",
        home: Path = DEFAULT_HOME,
        dry_run: bool = False,
        skip_install: bool = False,
        with_model_extras: bool = False,
        verbose: bool = False,
    ) -> None:
        self.mode = mode
        self.source = source
        self.home = home
        self.dry_run = dry_run
        self.skip_install = skip_install
        self.with_model_extras = with_model_extras
        self.verbose = verbose
        self.platform = platform.system().lower()

    def check_requirements(self) -> bool:
        """Return whether the current machine meets minimum requirements."""
        print("Checking system requirements...")

        python_version = sys.version_info[:2]
        if python_version < MIN_PYTHON:
            print(
                f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required; "
                f"found {python_version[0]}.{python_version[1]}."
            )
            return False
        print(f"Python {python_version[0]}.{python_version[1]} OK")

        self._print_ram_check()
        return self._print_disk_check()

    def install_dependencies(self) -> bool:
        """Install packages for the selected mode."""
        if self.skip_install:
            print("Skipping package installation (--skip-install).")
            return True

        resolved_source = self._resolve_source()
        print(
            "Installing DueCare packages for "
            f"{self.mode} mode from {resolved_source}..."
        )

        if resolved_source == "local":
            package_args = self._local_editable_package_args()
        else:
            package_args = PYPI_PACKAGES_BY_MODE[self.mode].copy()

        if self.with_model_extras:
            package_args.extend(MODEL_EXTRA_PACKAGES_BY_MODE[self.mode])

        if not package_args:
            print("No package arguments resolved for installation.")
            return False

        command = [sys.executable, "-m", "pip", "install", *package_args]
        return self._run_command(command, timeout=900)

    def setup_models(self) -> bool:
        """Write a local model manifest without downloading weights."""
        config = MODEL_CONFIGS[self.mode]
        models_dir = self.home / "models"
        config_file = models_dir / "config.json"
        config_data = {
            "mode": self.mode,
            "primary_model": config["primary"],
            "fallback_model": config["fallback"],
            "models_path": str(models_dir),
            "raw_data_policy": (
                "Raw worker chats and case documents stay on this device unless "
                "the user explicitly creates a sanitized submission."
            ),
            "weights_downloaded_by_setup": False,
        }

        if self.dry_run:
            print(f"Would write model config to {config_file}")
            return True

        try:
            models_dir.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                json.dumps(config_data, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"Model configuration failed: {exc}")
            return False

        print(f"Model configuration saved: {config_file}")
        return True

    def create_desktop_shortcuts(self) -> bool:
        """Create a tiny launch script for the existing ``duecare serve`` CLI."""
        if self.mode != "desktop":
            return True

        scripts_dir = self.home / "scripts"
        suffix = "bat" if self.platform == "windows" else "sh"
        startup_script = scripts_dir / f"start_duecare.{suffix}"
        script_content = self._desktop_script_content()

        if self.dry_run:
            print(f"Would write startup script to {startup_script}")
            return True

        try:
            scripts_dir.mkdir(parents=True, exist_ok=True)
            startup_script.write_text(script_content, encoding="utf-8")
            if self.platform != "windows":
                startup_script.chmod(0o755)
        except OSError as exc:
            print(f"Startup script creation failed: {exc}")
            return False

        print(f"Startup script created: {startup_script}")
        return True

    def validate_installation(self) -> bool:
        """Return whether required imports and the console entry point work."""
        print("Validating installation...")

        missing_modules = [
            module
            for module in REQUIRED_MODULES_BY_MODE[self.mode]
            if not self._module_importable(module)
        ]
        if missing_modules:
            print(f"Missing modules: {', '.join(missing_modules)}")
            return False

        if self.mode == "desktop" and not self._validate_cli():
            return False

        print("Installation validation passed.")
        return True

    def run_setup(self) -> bool:
        """Execute the full setup flow."""
        print(f"DueCare consumer setup ({self.mode} mode)")
        print("=" * 50)

        steps = [
            ("System requirements", self.check_requirements),
            ("Package installation", self.install_dependencies),
            ("Model manifest", self.setup_models),
            ("Desktop launcher", self.create_desktop_shortcuts),
        ]
        if not self.dry_run:
            steps.append(("Installation validation", self.validate_installation))

        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                print(f"Setup failed at: {step_name}")
                return False

        print("\nSetup complete.")
        if self.mode == "desktop":
            print("Next steps:")
            print("1. Run: duecare init")
            print("2. Run: duecare demo-stage")
            print("3. Run: duecare serve --port 8080")
            print("4. Open: http://127.0.0.1:8080")
        return True

    def _print_ram_check(self) -> None:
        """Print a best-effort RAM check without making psutil mandatory."""
        try:
            import psutil  # type: ignore[import-not-found]
        except ImportError:
            print("RAM check skipped; psutil is not installed.")
            return

        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < MIN_RAM_GB:
            print(f"Only {ram_gb:.1f} GB RAM detected; {MIN_RAM_GB} GB is recommended.")
            return
        print(f"{ram_gb:.1f} GB RAM OK")

    def _print_disk_check(self) -> bool:
        """Print and return the free-space check for the current working directory."""
        try:
            disk_free = shutil.disk_usage(Path.cwd()).free / (1024**3)
        except OSError as exc:
            print(f"Disk check skipped: {exc}")
            return True

        if disk_free < MIN_DISK_GB:
            print(f"Only {disk_free:.1f} GB free; {MIN_DISK_GB} GB is required.")
            return False
        print(f"{disk_free:.1f} GB free disk space OK")
        return True

    def _resolve_source(self) -> Literal["local", "pypi"]:
        """Resolve installation source based on ``--source`` and repository layout."""
        if self.source == "pypi":
            return "pypi"
        if self.source == "local" or self._has_local_packages():
            return "local"
        return "pypi"

    def _has_local_packages(self) -> bool:
        """Return whether this script is running from the monorepo checkout."""
        packages_dir = self._repo_root() / "packages"
        return all(
            (packages_dir / package / "pyproject.toml").exists()
            for package in LOCAL_PACKAGE_ORDER
        )

    def _local_editable_package_args(self) -> list[str]:
        """Return editable-install arguments for local packages in dependency order."""
        packages_dir = self._repo_root() / "packages"
        args: list[str] = []
        for package in LOCAL_PACKAGE_ORDER:
            package_dir = packages_dir / package
            if not package_dir.exists():
                continue
            args.extend(["-e", str(package_dir)])
        return args

    def _repo_root(self) -> Path:
        """Return the repository root inferred from this script path."""
        return Path(__file__).resolve().parents[1]

    def _run_command(self, command: list[str], *, timeout: int) -> bool:
        """Run a subprocess command with consistent output and dry-run support."""
        printable = " ".join(command)
        if self.dry_run:
            print(f"Would run: {printable}")
            return True
        if self.verbose:
            print(f"Running: {printable}")

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"Command timed out after {timeout} seconds: {printable}")
            return False
        except OSError as exc:
            print(f"Command failed to start: {exc}")
            return False

        if result.returncode != 0:
            print(result.stderr.strip() or result.stdout.strip())
            return False
        if self.verbose and result.stdout:
            print(result.stdout.strip())
        return True

    def _desktop_script_content(self) -> str:
        """Return platform-specific launcher content."""
        if self.platform == "windows":
            return (
                "@echo off\n"
                "echo Starting DueCare Safety Harness...\n"
                "duecare serve --host 127.0.0.1 --port 8080\n"
                "pause\n"
            )
        return (
            "#!/usr/bin/env sh\n"
            "set -eu\n"
            "echo 'Starting DueCare Safety Harness...'\n"
            "duecare serve --host 127.0.0.1 --port 8080\n"
        )

    def _module_importable(self, module: str) -> bool:
        """Return whether a module imports without raising ImportError."""
        try:
            importlib.import_module(module)
        except ImportError as exc:
            print(f"Import failed for {module}: {exc}")
            return False
        return True

    def _validate_cli(self) -> bool:
        """Return whether the installed ``duecare`` console command responds."""
        duecare_command = shutil.which("duecare")
        if not duecare_command:
            print("Missing `duecare` console command; install duecare-llm-cli.")
            return False
        return self._run_command([duecare_command, "--version"], timeout=20)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description="DueCare consumer setup")
    parser.add_argument(
        "--mode",
        choices=["desktop", "mobile", "browser"],
        default="desktop",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "local", "pypi"],
        default="auto",
    )
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate an existing installation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without changing files",
    )
    parser.add_argument("--skip-install", action="store_true", help="Do not run pip install")
    parser.add_argument(
        "--with-model-extras",
        action="store_true",
        help="Install optional runtime client packages such as ollama or llama-cpp-python",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    setup = ConsumerSetup(
        mode=cast(Mode, args.mode),
        source=cast(Source, args.source),
        home=args.home,
        dry_run=args.dry_run,
        skip_install=args.skip_install,
        with_model_extras=args.with_model_extras,
        verbose=args.verbose,
    )

    if args.check:
        return 0 if setup.validate_installation() else 1
    return 0 if setup.run_setup() else 1


if __name__ == "__main__":
    sys.exit(main())