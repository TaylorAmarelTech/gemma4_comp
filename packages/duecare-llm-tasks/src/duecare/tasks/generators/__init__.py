"""DueCare prompt-mutation generators.

Usage::

    from duecare.tasks.generators import (
        EvasionGenerator,
        CoercionGenerator,
        FinancialGenerator,
        RegulatoryGenerator,
        CorridorGenerator,
        ALL_GENERATORS,
    )

    prompts = [{"id": "p1", "text": "...", "category": "fee_evasion"}]
    for gen in ALL_GENERATORS:
        variations = gen.generate(prompts, n_variations=2, seed=42)
"""

from .base import Generator, Prompt, make_variation, variation_id
from .case_challenge import CaseChallengeGenerator
from .coercion import CoercionGenerator
from .corridor import CorridorGenerator
from .creative_attacks import CreativeAttackGenerator
from .document_injection import DocumentInjectionGenerator
from .document_quiz import DocumentQuizGenerator
from .evasion import EvasionGenerator
from .financial import FinancialGenerator
from .importance_ranker import ImportanceRanker, rank_prompts
from .informed_followup import InformedFollowupGenerator
from .interactive import InteractiveGenerator
from .multi_turn import MultiTurnGenerator
from .persona import PersonaGenerator
from .obfuscation import ObfuscationGenerator
from .output_conditioning import OutputConditioningGenerator
from .regulatory import RegulatoryGenerator

ALL_GENERATORS: list[Generator] = [
    EvasionGenerator(),
    CoercionGenerator(),
    FinancialGenerator(),
    RegulatoryGenerator(),
    CorridorGenerator(),
    MultiTurnGenerator(),
    DocumentInjectionGenerator(),
    PersonaGenerator(),
    InteractiveGenerator(),
    CaseChallengeGenerator(),
    InformedFollowupGenerator(),
    CreativeAttackGenerator(),
    ObfuscationGenerator(),
    OutputConditioningGenerator(),
    DocumentQuizGenerator(),
]

__all__ = [
    "Generator",
    "Prompt",
    "make_variation",
    "variation_id",
    "EvasionGenerator",
    "CoercionGenerator",
    "FinancialGenerator",
    "RegulatoryGenerator",
    "CorridorGenerator",
    "MultiTurnGenerator",
    "DocumentInjectionGenerator",
    "PersonaGenerator",
    "InteractiveGenerator",
    "CaseChallengeGenerator",
    "InformedFollowupGenerator",
    "CreativeAttackGenerator",
    "ObfuscationGenerator",
    "OutputConditioningGenerator",
    "DocumentQuizGenerator",
    "ImportanceRanker",
    "rank_prompts",
    "ALL_GENERATORS",
]
