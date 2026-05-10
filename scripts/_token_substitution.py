"""Simple token substitution for design consistency across notebooks.

Usage in build scripts:
    from _token_substitution import substitute_tokens
    kernel_source = substitute_tokens(kernel_source)

Replaces {{TOKEN_NAME}} with actual values from design tokens.
"""

from __future__ import annotations

try:
    from _design_tokens import PALETTE
except (ImportError, FileNotFoundError):
    # Fallback palette if design tokens not available
    PALETTE = {
        "danger": "oklch(0.58 0.14 45)",
        "danger_dark": "oklch(0.50 0.16 45)",
        "success": "oklch(0.55 0.10 155)",
        "primary": "oklch(0.52 0.08 195)",
        "surface": "#F7F6F1",
    }

# Simple token map for common patterns
TOKENS = {
    "DANGER_COLOR": PALETTE["danger"],
    "DANGER_HOVER_COLOR": PALETTE.get("danger_dark", "oklch(0.50 0.16 45)"),
    "SUCCESS_COLOR": PALETTE["success"],
    "PRIMARY_COLOR": PALETTE["primary"],
    "SURFACE_COLOR": PALETTE["surface"],
}


def substitute_tokens(content: str) -> str:
    """Replace {{TOKEN_NAME}} placeholders with actual values."""
    for token, value in TOKENS.items():
        content = content.replace(f"{{{{{token}}}}}", value)
    return content


def validate_tokens_used(content: str) -> list[str]:
    """Return list of any unsubstituted {{TOKEN}} patterns."""
    import re
    return re.findall(r'\{\{[A-Z_]+\}\}', content)