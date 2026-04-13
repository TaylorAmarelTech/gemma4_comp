"""Corridor expansion generator -- swap migration corridors to test
jurisdictional generalization.

The original benchmark is Philippines-Hong Kong heavy.  This generator
replaces country references with other real-world labor-migration
corridors so the model is tested across geographies.

Ported from the corridor-swap logic in ``build_notebook_00b.py`` and the
corridor lists in all four original generators.
"""

from __future__ import annotations

from typing import Any

from .base import Generator, Prompt, make_variation, seeded_rng


# ---------------------------------------------------------------------------
# Corridor definitions: (origin, destination, code, sector, regulator)
# ---------------------------------------------------------------------------

_CORRIDORS: list[tuple[str, str, str, str, str]] = [
    ("Philippines",  "Hong Kong",      "PH_HK", "Domestic work",   "POEA"),
    ("Bangladesh",   "UAE",            "BD_AE",  "Construction",    "BMET"),
    ("Nepal",        "Qatar",          "NP_QA",  "Construction",    "DoFE"),
    ("Indonesia",    "Singapore",      "ID_SG",  "Domestic work",   "BP2MI"),
    ("Ethiopia",     "Saudi Arabia",   "ET_SA",  "Domestic work",   "MoLSA"),
    ("Myanmar",      "Thailand",       "MM_TH",  "Manufacturing",   "DoL"),
    ("Vietnam",      "Taiwan",         "VN_TW",  "Manufacturing",   "DoLAB"),
    ("India",        "Malaysia",       "IN_MY",  "Construction",    "eMigrate"),
    ("Sri Lanka",    "Kuwait",         "LK_KW",  "Domestic work",   "SLBFE"),
    ("Pakistan",     "UAE",            "PK_AE",  "Construction",    "OEC"),
    ("Cambodia",     "Thailand",       "KH_TH",  "Agriculture",     "MoLVT"),
]

# Keywords that identify the default PH_HK corridor in source prompts
_PH_HK_KEYWORDS: dict[str, str] = {
    "Philippines":  "{origin}",
    "Philippine":   "{origin_adj}",
    "Filipino":     "{origin} national",
    "Hong Kong":    "{destination}",
    "POEA":         "{regulator}",
    "OFW":          "migrant worker",
    "domestic worker": "{sector} worker",
}


def _build_replacement_map(
    origin: str,
    destination: str,
    sector: str,
    regulator: str,
) -> dict[str, str]:
    """Concrete keyword -> replacement for a target corridor."""
    # Origin adjective heuristic (works for most country names)
    origin_adj = origin.rstrip("s")
    if origin.endswith("es"):
        origin_adj = origin[:-2]

    return {
        "{origin}": origin,
        "{origin_adj}": origin_adj,
        "{destination}": destination,
        "{regulator}": regulator,
        "{sector}": sector.lower(),
    }


class CorridorGenerator:
    """Swap migration-corridor references to stress-test generalization.

    For each base prompt, produces variations where PH/HK references are
    replaced with a randomly chosen alternative corridor.
    """

    name: str = "corridor"

    def generate(
        self,
        prompts: list[Prompt],
        n_variations: int = 1,
        *,
        seed: int | None = None,
    ) -> list[Prompt]:
        rng = seeded_rng(seed)
        # Exclude PH_HK since that's the default source
        alt_corridors = [c for c in _CORRIDORS if c[2] != "PH_HK"]

        results: list[Prompt] = []
        for base in prompts:
            text = base.get("text", "")
            if len(text) < 20:
                continue

            for _ in range(n_variations):
                origin, destination, code, sector, regulator = rng.choice(
                    alt_corridors
                )
                replacements = _build_replacement_map(
                    origin, destination, sector, regulator,
                )

                # First pass: replace known PH_HK keywords with placeholders
                mutated = text
                for keyword, placeholder in _PH_HK_KEYWORDS.items():
                    mutated = mutated.replace(keyword, placeholder)

                # Second pass: fill placeholders with target corridor values
                for placeholder, value in replacements.items():
                    mutated = mutated.replace(placeholder, value)

                # Skip if no actual changes occurred
                if mutated == text:
                    continue

                results.append(
                    make_variation(
                        base,
                        mutated_text=mutated,
                        mutation_type=f"corridor_{code}",
                        extra_meta={
                            "target_corridor": code,
                            "origin": origin,
                            "destination": destination,
                            "sector": sector,
                        },
                    )
                )
        return results
