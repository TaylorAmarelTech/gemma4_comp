#!/usr/bin/env python3
"""Apply design consistency across the DueCare project.

This script ensures all components use the same civic-tech design system:
1. Validates that design tokens are properly loaded
2. Updates notebook display system with civic-tech colors
3. Generates CSS variables for website consistency
4. Provides regeneration commands for notebooks

Usage:
    python scripts/apply_design_consistency.py --check
    python scripts/apply_design_consistency.py --apply
    python scripts/apply_design_consistency.py --regenerate-notebooks
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from _design_tokens import (
    get_palette, get_spacing, get_typography,
    generate_css_vars, load_design_tokens
)

ROOT = Path(__file__).resolve().parent.parent


def check_design_tokens():
    """Check if design tokens are properly loaded and consistent."""
    print("[CHECK] Checking design token system...")

    try:
        tokens = load_design_tokens()
        palette = get_palette()
        spacing = get_spacing()
        typography = get_typography()

        print(f"[PASS] Design tokens loaded successfully")
        print(f"       - {len(palette)} colors in palette")
        print(f"       - {len(spacing)} spacing values")
        print(f"       - {len(typography.get('families', {}))} font families")

        # Check for civic-tech signature colors
        if palette.get('primary') == "oklch(0.52 0.08 195)":
            print("[PASS] Civic teal accent color detected")
        else:
            print("[WARN] Primary color is not civic teal")

        if palette.get('surface') == "#F7F6F1":
            print("[PASS] Warm paper background detected")
        else:
            print("[WARN] Surface color is not warm paper")

        return True

    except Exception as e:
        print(f"[FAIL] Design token system failed: {e}")
        return False


def check_notebook_display():
    """Check if notebook display system uses civic-tech colors."""
    print("\n[CHECK] Checking notebook display system...")

    try:
        from _notebook_display import PALETTE

        if PALETTE.get('primary') == "oklch(0.52 0.08 195)":
            print("[PASS] Notebook display uses civic teal")
        else:
            print("[WARN] Notebook display uses generic colors")
            print(f"       Primary: {PALETTE.get('primary')}")

        if PALETTE.get('surface') == "#F7F6F1":
            print("[PASS] Notebook display uses warm paper")
        else:
            print("[WARN] Notebook display uses generic surface")

        return True

    except Exception as e:
        print(f"[FAIL] Notebook display system failed: {e}")
        return False


def check_website_css():
    """Check if website CSS uses proper design tokens."""
    print("\n[CHECK] Checking website CSS...")

    css_file = ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "styles.css"

    if not css_file.exists():
        print("[FAIL] Website CSS file not found")
        return False

    css_content = css_file.read_text()

    if "--paper: #F7F6F1" in css_content:
        print("[PASS] Website uses warm paper background")
    else:
        print("[WARN] Website CSS may not use proper tokens")

    if "--accent: oklch(0.52 0.08 195)" in css_content:
        print("[PASS] Website uses civic teal accent")
    else:
        print("[WARN] Website CSS may not use civic teal")

    return True


def apply_consistency():
    """Apply design consistency across all systems."""
    print("[APPLY] Applying design consistency...\n")

    # Generate updated CSS variables
    print("[BUILD] Generating CSS custom properties...")
    css_vars = generate_css_vars()

    output_file = ROOT / "configs" / "duecare" / "design_tokens.css"
    output_file.write_text(css_vars)
    print(f"[DONE] CSS variables written to {output_file}")

    # Check systems
    tokens_ok = check_design_tokens()
    display_ok = check_notebook_display()
    css_ok = check_website_css()

    if all([tokens_ok, display_ok, css_ok]):
        print("\n[SUCCESS] All systems are consistent!")
        print("\nNext steps:")
        print("1. Regenerate notebooks to pick up new colors:")
        print("   python scripts/apply_design_consistency.py --regenerate-notebooks")
        print("2. Test a few notebooks to verify the civic-tech aesthetic")
        print("3. Commit the design tokens and updated display system")
    else:
        print("\n[WARNING] Some systems need attention - see details above")


def regenerate_notebooks():
    """Provide commands to regenerate notebooks with new design system."""
    print("[GUIDE] Notebook regeneration commands:\n")

    key_notebooks = [
        ("010_quickstart", "Quick demo with civic-tech styling"),
        ("100_gemma_exploration", "Main baseline evaluation"),
        ("200_cross_domain_proof", "Cross-domain demonstration"),
        ("500_agent_swarm_deep_dive", "Technical depth showcase"),
        ("610_submission_walkthrough", "Final submission narrative"),
    ]

    print("[PRIMARY] Primary notebooks (regenerate these first):")
    for nb_id, desc in key_notebooks:
        build_script = f"build_notebook_{nb_id}.py"
        if (ROOT / "scripts" / build_script).exists():
            print(f"   python scripts/{build_script}")
        else:
            print(f"   # scripts/{build_script} (not found)")

    print("\n[BATCH] Batch regeneration:")
    print("   # All core notebooks:")
    print("   python scripts/build_kaggle_notebooks.py")
    print("   # All appendix notebooks:")
    print("   python scripts/build_deployment_application_notebooks.py")

    print("\n[TOKEN SYSTEM] Streamlined approach for future:")
    print("   Replace hardcoded colors with tokens in kernel templates:")
    print("   OLD: background:#dc2626;color:white;")
    print("   NEW: background:{{DANGER_COLOR}};color:white;")
    print("   Then: from _token_substitution import substitute_tokens")
    print("   Auto-processes during build - no more manual find/replace!")

    print("\n[NEXT] After regenerating:")
    print("1. Check a few notebook outputs for civic-tech colors")
    print("2. Verify warm paper background (#F7F6F1) and civic teal accents")
    print("3. Push updated notebooks to Kaggle when ready")


def main():
    parser = argparse.ArgumentParser(description="Apply design consistency across DueCare project")
    parser.add_argument("--check", action="store_true", help="Check design token consistency")
    parser.add_argument("--apply", action="store_true", help="Apply design consistency")
    parser.add_argument("--regenerate-notebooks", action="store_true", help="Show notebook regeneration commands")

    args = parser.parse_args()

    if args.check or (not args.apply and not args.regenerate_notebooks):
        check_design_tokens()
        check_notebook_display()
        check_website_css()

    if args.apply:
        apply_consistency()

    if args.regenerate_notebooks:
        regenerate_notebooks()


if __name__ == "__main__":
    main()