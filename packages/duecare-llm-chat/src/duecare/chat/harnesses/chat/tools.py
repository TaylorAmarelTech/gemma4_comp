"""Function-calling tools contributed by the chat harness.

These are Gemma 4 function-call specs that mirror the dispatch
implementations in ``duecare.chat.harness._TOOL_DISPATCH``. Specs only
live here so the chat orchestrator can advertise them to Gemma; the
actual call resolution stays in the legacy harness module.
"""
from __future__ import annotations


TOOLS: list[dict] = [
    {
        "name": "lookup_corridor_fee_cap",
        "description": (
            "Return the statutory placement-fee cap for a given "
            "migrant-worker corridor (e.g. PH-HK = 0 PHP per POEA "
            "Memorandum Circular 14-2017; ID-HK = zero-cost under "
            "Permenaker 9/2020). Use whenever the user mentions a fee "
            "amount AND a corridor or destination country."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "corridor": {
                    "type": "string",
                    "description": "Two-letter ISO pair (e.g. PH-HK, ID-MY, NP-AE)",
                },
            },
            "required": ["corridor"],
        },
    },
    {
        "name": "lookup_fee_camouflage",
        "description": (
            "Classify a fee label the recruiter is using (e.g. "
            "'training fee', 'medical exam', 'visa processing') as "
            "legitimate vs prohibited under the relevant corridor's "
            "zero-fee statute. Use when the user describes a fee by "
            "NAME rather than by amount."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "label": {"type": "string",
                          "description": "Fee label as the recruiter named it"},
                "corridor": {"type": "string",
                              "description": "Corridor for jurisdictional context"},
            },
            "required": ["label"],
        },
    },
    {
        "name": "lookup_ilo_indicator",
        "description": (
            "Look up one of the 11 ILO indicators of forced labour "
            "(passport retention, deception, restriction of movement, "
            "isolation, physical/sexual violence, intimidation, "
            "retention of identity documents, withholding of wages, "
            "debt bondage, abusive working conditions, excessive "
            "overtime). Use when the user describes employer behavior."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "indicator": {"type": "string",
                              "description": "Indicator name or close paraphrase"},
            },
            "required": ["indicator"],
        },
    },
    {
        "name": "lookup_ngo_intake",
        "description": (
            "Return contact info for the appropriate NGO / regulator "
            "intake channel given a corridor or country (Polaris, IJM, "
            "ECPAT, POEA, BP2MI, Mission for Migrant Workers HK, "
            "HRD Nepal, etc.). Use when the user needs to be "
            "redirected to help."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "corridor": {"type": "string"},
                "country": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "lookup_ilo_convention",
        "description": (
            "Return a brief summary of an ILO convention by number "
            "(C029, C095, C097, C143, C181, C188, C189, C190). Use "
            "when citing a convention in the response."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "number": {
                    "type": "string",
                    "description": "Convention number (e.g. 'C181' or '181')",
                },
            },
            "required": ["number"],
        },
    },
]


def list_tools() -> list[dict]:
    return list(TOOLS)
