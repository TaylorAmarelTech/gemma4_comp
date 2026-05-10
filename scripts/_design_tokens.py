"""Design tokens loader and converter for DueCare design system.

Provides centralized access to design tokens defined in configs/duecare/design_tokens.yaml.
Supports conversion between YAML configuration, Python constants, and CSS custom properties.
Used by notebook display helpers and website CSS generation to ensure consistency.

Usage:
    from _design_tokens import get_palette, get_spacing, generate_css_vars

    # Get notebook-compatible palette
    colors = get_palette()

    # Get spacing scale
    spacing = get_spacing()

    # Generate CSS custom properties
    css_vars = generate_css_vars()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

try:
    import yaml
except ImportError:
    yaml = None


def _get_tokens_path() -> Path:
    """Find the design tokens YAML file relative to this script."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    tokens_path = project_root / "configs" / "duecare" / "design_tokens.yaml"

    if not tokens_path.exists():
        raise FileNotFoundError(f"Design tokens not found at {tokens_path}")

    return tokens_path


def load_design_tokens() -> Dict[str, Any]:
    """Load the complete design tokens configuration."""
    if yaml is None:
        raise ImportError("PyYAML required for design tokens. Install with: pip install PyYAML")

    tokens_path = _get_tokens_path()

    with open(tokens_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_palette() -> Dict[str, str]:
    """Get the notebook-compatible color palette.

    Returns a dictionary compatible with the existing PALETTE in _notebook_display.py,
    but with colors sourced from the design tokens instead of hardcoded values.
    """
    tokens = load_design_tokens()
    return tokens.get('notebook_palette', {})


def get_spacing() -> Dict[str, str]:
    """Get the spacing scale from design tokens."""
    tokens = load_design_tokens()
    return tokens.get('spacing', {})


def get_typography() -> Dict[str, Any]:
    """Get typography definitions from design tokens."""
    tokens = load_design_tokens()
    return tokens.get('typography', {})


def get_colors() -> Dict[str, Any]:
    """Get the complete color system from design tokens."""
    tokens = load_design_tokens()
    return tokens.get('colors', {})


def generate_css_vars() -> str:
    """Generate CSS custom properties from design tokens.

    Returns a CSS string with :root variables that can be injected
    into stylesheets to ensure consistency with the design tokens.
    """
    tokens = load_design_tokens()

    css_lines = [":root {"]

    # Colors
    colors = tokens.get('colors', {})
    for category, group in colors.items():
        if isinstance(group, dict):
            for name, value in group.items():
                var_name = f"--{category}-{name.replace('_', '-')}"
                css_lines.append(f"  {var_name}: {value};")
        else:
            var_name = f"--{category}"
            css_lines.append(f"  {var_name}: {group};")

    # Typography
    typography = tokens.get('typography', {})
    for category, group in typography.items():
        if isinstance(group, dict):
            for name, value in group.items():
                if isinstance(value, (int, float)):
                    var_name = f"--font-{category}-{name.replace('_', '-')}"
                else:
                    var_name = f"--font-{category}-{name.replace('_', '-')}"
                css_lines.append(f"  {var_name}: {value};")
        else:
            var_name = f"--font-{category}"
            css_lines.append(f"  {var_name}: {group};")

    # Spacing
    spacing = tokens.get('spacing', {})
    for name, value in spacing.items():
        css_lines.append(f"  --{name}: {value};")

    # Radii
    radii = tokens.get('radii', {})
    for name, value in radii.items():
        var_name = f"--r-{name.replace('_', '-')}"
        css_lines.append(f"  {var_name}: {value};")

    # Shadows
    shadows = tokens.get('shadows', {})
    for name, value in shadows.items():
        var_name = f"--shadow-{name.replace('_', '-')}"
        css_lines.append(f"  {var_name}: {value};")

    css_lines.append("}")
    return "\n".join(css_lines)


def generate_notebook_palette_py() -> str:
    """Generate Python code for the PALETTE dictionary used in notebooks.

    Returns Python source code that can replace the hardcoded PALETTE
    in _notebook_display.py with values from design tokens.
    """
    palette = get_palette()

    lines = ["PALETTE = {"]
    for key, value in palette.items():
        lines.append(f'    "{key}": "{value}",')
    lines.append("}")

    return "\n".join(lines)


# Backwards compatibility: export the palette directly for immediate use
try:
    _TOKENS = load_design_tokens()
    PALETTE = _TOKENS.get('notebook_palette', {})
    SPACING = _TOKENS.get('spacing', {})
    TYPOGRAPHY = _TOKENS.get('typography', {})
except (ImportError, FileNotFoundError):
    # Fallback to hardcoded values if YAML not available or tokens file missing
    PALETTE = {
        "primary": "#4c78a8",
        "success": "#10b981",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "info": "#3b82f6",
        "muted": "#6b7280",
        "surface": "#fafbfc",
        "surface_2": "#f6f8fa",
        "bg_success": "#ecfdf5",
        "bg_warning": "#fffbeb",
        "bg_danger": "#fef2f2",
        "bg_info": "#eff6ff",
    }
    SPACING = {}
    TYPOGRAPHY = {}


if __name__ == "__main__":
    """Development utility: print design tokens in various formats."""
    print("=== Design Tokens ===")
    print("\nPalette:")
    for k, v in get_palette().items():
        print(f"  {k}: {v}")

    print("\nSpacing:")
    for k, v in get_spacing().items():
        print(f"  {k}: {v}")

    print("\nCSS Variables:")
    print(generate_css_vars())

    print("\nPython PALETTE:")
    print(generate_notebook_palette_py())