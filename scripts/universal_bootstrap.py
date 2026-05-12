#!/usr/bin/env python3
"""
Universal DueCare installer - works in any Python environment.

Paste this entire cell into any Jupyter notebook (Kaggle, Colab, local) and run.
Automatically detects the best installation method for the current environment.
"""

import subprocess
import sys
import time
import platform
from typing import Dict, List, Optional


def detect_environment() -> str:
    """Detect what platform we're running on."""
    try:
        # Check for Kaggle
        if "/kaggle/" in sys.executable:
            return "kaggle"
        # Check for Colab
        if "google.colab" in sys.modules:
            return "colab"
        # Check for Jupyter
        if "ipykernel" in sys.modules:
            return "jupyter"
        # Default to local Python
        return "local"
    except:
        return "unknown"


def check_internet() -> bool:
    """Quick internet connectivity check."""
    try:
        import urllib.request
        urllib.request.urlopen("https://pypi.org", timeout=5)
        return True
    except:
        return False


class DueCareInstaller:
    """Universal DueCare package installer."""

    def __init__(self, version: str = "0.1.0"):
        self.version = version
        self.environment = detect_environment()
        self.has_internet = check_internet()
        self.packages = ["duecare-llm-core", "duecare-llm-models", "duecare-llm-chat"]

    def install(self) -> Dict[str, any]:
        """Install DueCare packages using the best available method."""
        start_time = time.time()

        print(f"🚀 DueCare Universal Installer")
        print(f"   Environment: {self.environment}")
        print(f"   Internet: {'✓' if self.has_internet else '✗'}")
        print(f"   Target version: {self.version}")
        print("=" * 50)

        if not self.has_internet:
            return self._fail("No internet connection detected")

        # Try installation methods in order of reliability
        methods = [
            ("PyPI", self._install_from_pypi),
            ("GitHub Releases", self._install_from_releases),
            ("GitHub Source", self._install_from_source)
        ]

        for method_name, method_func in methods:
            try:
                print(f"📦 Attempting {method_name} installation...")
                result = method_func()
                if result["success"]:
                    elapsed = time.time() - start_time
                    print(f"✅ Success via {method_name} ({elapsed:.1f}s)")
                    return {
                        "success": True,
                        "method": method_name,
                        "elapsed": elapsed,
                        "packages_installed": len(self.packages)
                    }
                else:
                    print(f"❌ {method_name} failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"❌ {method_name} failed: {str(e)}")

        return self._fail("All installation methods failed")

    def _install_from_pypi(self) -> Dict[str, any]:
        """Try installing from PyPI (most universal)."""
        cmd = [
            sys.executable, "-m", "pip", "install", "--no-input",
            "--disable-pip-version-check"
        ] + [f"{pkg}=={self.version}" for pkg in self.packages]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if proc.returncode == 0:
            return {"success": True}
        else:
            # If packages don't exist on PyPI yet, that's expected
            if "No matching distribution found" in proc.stderr:
                return {"success": False, "error": "Packages not yet published to PyPI"}
            return {"success": False, "error": proc.stderr[-200:]}

    def _install_from_releases(self) -> Dict[str, any]:
        """Try installing from GitHub release assets."""
        base_url = f"https://github.com/TaylorAmarelTech/gemma4_comp/releases/download/v{self.version}"

        wheel_urls = []
        for pkg in self.packages:
            wheel_name = pkg.replace("-", "_") + f"-{self.version}-py3-none-any.whl"
            wheel_urls.append(f"{base_url}/{wheel_name}")

        cmd = [
            sys.executable, "-m", "pip", "install", "--no-input",
            "--disable-pip-version-check"
        ] + wheel_urls

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if proc.returncode == 0:
            return {"success": True}
        else:
            return {"success": False, "error": proc.stderr[-200:]}

    def _install_from_source(self) -> Dict[str, any]:
        """Try installing from GitHub source (slowest but most reliable)."""
        repo_packages = []
        for pkg in self.packages:
            repo_packages.append(
                f"git+https://github.com/TaylorAmarelTech/gemma4_comp.git@main#subdirectory=packages/{pkg}"
            )

        cmd = [
            sys.executable, "-m", "pip", "install", "--no-input",
            "--disable-pip-version-check"
        ] + repo_packages

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if proc.returncode == 0:
            return {"success": True}
        else:
            return {"success": False, "error": proc.stderr[-200:]}

    def _fail(self, message: str) -> Dict[str, any]:
        """Handle installation failure."""
        print(f"\n❌ INSTALLATION FAILED: {message}")
        print("\n🔧 Manual installation commands:")
        print("   Copy and run these individually if automatic installation fails:\n")

        for pkg in self.packages:
            print(f"   !pip install git+https://github.com/TaylorAmarelTech/gemma4_comp.git#subdirectory=packages/{pkg}")

        return {"success": False, "error": message}

    def verify_installation(self) -> bool:
        """Verify packages were installed correctly."""
        try:
            import duecare.core
            import duecare.models
            import duecare.chat
            print("✅ All DueCare packages imported successfully")

            # Print versions
            try:
                from importlib.metadata import version
                for pkg in self.packages:
                    v = version(pkg)
                    print(f"   {pkg}: {v}")
            except:
                pass

            return True
        except ImportError as e:
            print(f"❌ Import verification failed: {e}")
            return False


# Main installation function (call this)
def install_duecare(version: str = "0.1.0") -> Dict[str, any]:
    """Install DueCare packages universally.

    Args:
        version: Package version to install

    Returns:
        Installation result dictionary
    """
    installer = DueCareInstaller(version)
    result = installer.install()

    if result["success"]:
        installer.verify_installation()

    return result


# Auto-run if executed directly
if __name__ == "__main__":
    result = install_duecare()
    if not result["success"]:
        sys.exit(1)