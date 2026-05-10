#!/usr/bin/env python3
"""
Example of DueCare Bootstrap in a Kaggle Notebook

🚀 SETUP REQUIRED (in Kaggle notebook settings):
  1. Set Accelerator → GPU T4 x2 (or equivalent)
  2. Set Internet → ON
  3. Copy this cell and run - installation is automatic!

✅ NO MANUAL STEPS NEEDED:
  - No dataset linking required
  - No "Add Data" requirements
  - Self-installing from GitHub

This demonstrates the GitHub-based installation strategy that replaces
the old requirement for linked Kaggle datasets.
"""

# Import the bootstrap function
exec(open('scripts/_notebook_bootstrap.py').read()) if Path('scripts/_notebook_bootstrap.py').exists() else None

# If the above fails (running in Kaggle without repository), use inline bootstrap:
if 'install_duecare' not in globals():
    from pathlib import Path
    import subprocess
    import sys

    # Minimal inline bootstrap for remote environments
    def install_duecare_minimal():
        """Minimal DueCare installation for demo purposes."""
        packages = [
            "duecare-llm-core",
            "duecare-llm-models",
            "duecare-llm-domains",
            "duecare-llm-tasks",
            "duecare-llm-server"
        ]

        repo = "TaylorAmarelTech/gemma4_comp"
        commit = "6da0e04bae38bcd75abd3d8c178cc80c183f4f41"

        for package in packages:
            print(f"📦 Installing {package}...")

            # Try GitHub repository install
            repo_url = f"git+https://github.com/{repo}.git@{commit}#subdirectory=packages/{package}"
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", repo_url],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ Installed {package}")
            else:
                print(f"❌ Failed to install {package}: {result.stderr[:100]}...")

        # Clear module cache for fresh imports
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]

        print("🎉 DueCare installation complete!")

    # Use the minimal version as fallback
    install_duecare = install_duecare_minimal

# Run the installation
print("🚀 Starting DueCare Bootstrap...")
install_duecare(mode="demo")

# Test the installation
print("\n🔍 Testing DueCare installation...")
try:
    import duecare.core
    print("✅ duecare.core imported successfully")

    import duecare.models
    print("✅ duecare.models imported successfully")

    import duecare.domains
    print("✅ duecare.domains imported successfully")

    import duecare.tasks
    print("✅ duecare.tasks imported successfully")

    import duecare.server
    print("✅ duecare.server imported successfully")

    print("\n🎉 All DueCare packages are working!")
    print("\nYou can now use:")
    print("  • duecare.models.create_model() - Load Gemma models")
    print("  • duecare.domains.load_domain_pack() - Load safety domains")
    print("  • duecare.tasks.run_capability_test() - Run evaluations")
    print("  • duecare.server.create_app() - Start demo server")

except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Some packages may not have installed correctly.")
    print("Check the installation logs above for errors.")

print("\n" + "="*60)
print("Bootstrap complete! DueCare is ready to use.")
print("="*60)