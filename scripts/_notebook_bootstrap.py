"""
DueCare Notebook Bootstrap - Multi-tier Installation Strategy

Self-contained installation for DueCare packages in Kaggle notebooks.
No dataset linking required - installs directly from GitHub.

🚀 SETUP REQUIRED (in Kaggle notebook settings):
  1. Set Accelerator → GPU T4 x2 (or equivalent)
  2. Set Internet → ON
  3. Run the notebook - installation is automatic!

📋 For detailed setup across all environments: docs/SETUP_REQUIREMENTS.md

Installation Tiers (automatic fallback):
1. GitHub Release Assets (fastest, most reliable)
2. GitHub Repository Install (pinned commit, development)
3. Local wheel fallback (for repository-adjacent notebooks)

Usage in notebook:
    exec(open('scripts/_notebook_bootstrap.py').read())
    # OR copy-paste the install_duecare() function
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Literal

# Version and commit pinning for reproducibility
DUECARE_VERSION = "0.1.0"
GITHUB_REPO = "TaylorAmarelTech/gemma4_comp"
PINNED_COMMIT = "6da0e04bae38bcd75abd3d8c178cc80c183f4f41"  # Pinned for reproducibility

# Package installation order (dependencies first)
PACKAGE_INSTALL_ORDER = [
    "duecare-llm-core",
    "duecare-llm-models",
    "duecare-llm-domains",
    "duecare-llm-tasks",
    "duecare-llm-evidence-db",
    "duecare-llm-engine",
    "duecare-llm-server",
    "duecare-llm-cli",
]

# Mode-specific package subsets
PACKAGES_BY_MODE = {
    "minimal": ["duecare-llm-core", "duecare-llm-models", "duecare-llm-tasks"],
    "demo": ["duecare-llm-core", "duecare-llm-models", "duecare-llm-domains",
             "duecare-llm-tasks", "duecare-llm-server"],
    "full": PACKAGE_INSTALL_ORDER,
}


def log_step(message: str, level: str = "INFO") -> None:
    """Log installation steps with clear formatting."""
    prefix = {
        "INFO": "📦",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "DEBUG": "🔍"
    }.get(level, "ℹ️")
    print(f"{prefix} {message}")


def run_pip_command(args: list[str], timeout: int = 300) -> tuple[bool, str, str]:
    """Run pip command with logging and error handling."""
    cmd = [sys.executable, "-m", "pip"] + args
    log_step(f"Running: {' '.join(cmd)}", "DEBUG")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return False, "", str(e)


def try_github_release_install(package: str) -> bool:
    """Try installing from GitHub release assets."""
    wheel_name = package.replace("-", "_") + f"-{DUECARE_VERSION}-py3-none-any.whl"
    release_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{DUECARE_VERSION}/{wheel_name}"

    log_step(f"Trying GitHub release for {package}...")
    success, stdout, stderr = run_pip_command(["install", release_url])

    if success:
        log_step(f"Installed {package} from GitHub release", "SUCCESS")
        return True
    else:
        log_step(f"GitHub release failed for {package}: {stderr[:100]}...", "WARNING")
        return False


def try_github_repo_install(package: str) -> bool:
    """Try installing from GitHub repository (pinned commit)."""
    repo_url = f"git+https://github.com/{GITHUB_REPO}.git@{PINNED_COMMIT}#subdirectory=packages/{package}"

    log_step(f"Trying GitHub repository for {package}...")
    success, stdout, stderr = run_pip_command(["install", repo_url])

    if success:
        log_step(f"Installed {package} from GitHub repo", "SUCCESS")
        return True
    else:
        log_step(f"GitHub repo failed for {package}: {stderr[:100]}...", "WARNING")
        return False


def try_local_wheel_install(package: str) -> bool:
    """Try installing from local wheel (if running in repository)."""
    # Look for wheel in dist directory
    possible_paths = [
        Path(f"packages/{package}/dist"),
        Path(f"dist"),
        Path(f"wheels/{package}"),
    ]

    for wheel_dir in possible_paths:
        if wheel_dir.exists():
            wheel_files = list(wheel_dir.glob(f"{package.replace('-', '_')}-*.whl"))
            if wheel_files:
                wheel_path = wheel_files[0]  # Use newest
                log_step(f"Trying local wheel for {package}: {wheel_path}")
                success, stdout, stderr = run_pip_command(["install", str(wheel_path)])

                if success:
                    log_step(f"Installed {package} from local wheel", "SUCCESS")
                    return True
                else:
                    log_step(f"Local wheel failed for {package}: {stderr[:100]}...", "WARNING")

    return False


def install_package_with_fallback(package: str) -> bool:
    """Install a single package using multi-tier strategy."""
    log_step(f"Installing {package}...")

    # Tier 1: GitHub Release Assets
    if try_github_release_install(package):
        return True

    # Tier 2: GitHub Repository Install
    if try_github_repo_install(package):
        return True

    # Tier 3: Local Wheel (for development)
    if try_local_wheel_install(package):
        return True

    log_step(f"All installation methods failed for {package}", "ERROR")
    return False


def check_package_installed(package: str) -> bool:
    """Check if package is already installed."""
    try:
        import_name = package.replace("-", ".").replace("llm.", "")
        if import_name.startswith("duecare."):
            module_name = import_name
        else:
            module_name = f"duecare.{import_name.split('.')[-1]}"

        __import__(module_name)
        log_step(f"{package} already installed", "SUCCESS")
        return True
    except ImportError:
        return False


def install_system_dependencies() -> None:
    """Install system dependencies that DueCare needs."""
    dependencies = [
        "requests>=2.31.0",
        "pydantic>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "python-multipart>=0.0.6",
        "jinja2>=3.1.0",
        "aiofiles>=23.0.0",
    ]

    log_step("Installing system dependencies...")
    for dep in dependencies:
        success, _, stderr = run_pip_command(["install", dep])
        if not success:
            log_step(f"Warning: Failed to install {dep}: {stderr[:50]}...", "WARNING")


def install_duecare(
    mode: Literal["minimal", "demo", "full"] = "demo",
    force_reinstall: bool = False,
    skip_deps: bool = False
) -> bool:
    """
    Install DueCare packages using multi-tier strategy.

    Args:
        mode: Package set to install ("minimal", "demo", "full")
        force_reinstall: Reinstall even if packages exist
        skip_deps: Skip system dependency installation

    Returns:
        True if all packages installed successfully
    """
    log_step(f"🚀 DueCare Bootstrap - {mode} mode", "INFO")
    log_step(f"Repository: {GITHUB_REPO}", "INFO")
    log_step(f"Version: {DUECARE_VERSION}", "INFO")
    log_step(f"Commit: {PINNED_COMMIT}", "INFO")

    # Install system dependencies first
    if not skip_deps:
        install_system_dependencies()

    # Get package list for mode
    packages = PACKAGES_BY_MODE.get(mode, PACKAGES_BY_MODE["demo"])

    successful_installs = 0
    failed_packages = []

    for package in packages:
        # Skip if already installed (unless forced)
        if not force_reinstall and check_package_installed(package):
            successful_installs += 1
            continue

        # Try multi-tier installation
        if install_package_with_fallback(package):
            successful_installs += 1
        else:
            failed_packages.append(package)

    # Summary
    total_packages = len(packages)
    log_step(f"Installation complete: {successful_installs}/{total_packages} packages",
             "SUCCESS" if successful_installs == total_packages else "WARNING")

    if failed_packages:
        log_step(f"Failed packages: {', '.join(failed_packages)}", "ERROR")
        log_step("Some packages failed - notebook may have limited functionality", "WARNING")
        return False
    else:
        log_step("All packages installed successfully! 🎉", "SUCCESS")
        return True


def validate_installation(mode: Literal["minimal", "demo", "full"] = "demo") -> bool:
    """Validate that installed packages can be imported."""
    log_step("Validating installation...")

    # Test core imports based on mode
    test_imports = {
        "minimal": ["duecare.core", "duecare.models"],
        "demo": ["duecare.core", "duecare.models", "duecare.server"],
        "full": ["duecare.core", "duecare.models", "duecare.server", "duecare.cli"]
    }

    imports_to_test = test_imports.get(mode, test_imports["demo"])
    failed_imports = []

    for module in imports_to_test:
        try:
            __import__(module)
            log_step(f"✓ {module}", "SUCCESS")
        except ImportError as e:
            log_step(f"✗ {module}: {e}", "ERROR")
            failed_imports.append(module)

    if failed_imports:
        log_step(f"Validation failed for: {', '.join(failed_imports)}", "ERROR")
        return False
    else:
        log_step("Installation validation passed!", "SUCCESS")
        return True


# Auto-execution when script is run directly
if __name__ == "__main__":
    # Default auto-install in demo mode
    success = install_duecare(mode="demo", force_reinstall=False)
    if success:
        validate_installation(mode="demo")
    else:
        log_step("Installation completed with errors - check logs above", "WARNING")


# For copy-paste into notebooks, provide a simple one-liner:
def quick_install(mode: str = "demo") -> None:
    """One-line installer for notebook cells."""
    install_duecare(mode=mode)
    validate_installation(mode=mode)