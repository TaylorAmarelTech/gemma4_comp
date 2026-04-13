"""Autonomous evolution engine -- genetic algorithm over attack populations.

Ported from the trafficking LLM benchmark's harness/evolution subsystem.
Core loop: select high-fitness attacks -> mutate -> evaluate -> archive.
"""

from .evolution_loop import EvolutionLoop, EvolutionConfig, EvolutionSnapshot
from .fitness_evaluator import FitnessEvaluator, FitnessScores
from .mutation_engine import MutationEngine, MutationType
from .continuous_learner import ContinuousLearner, LearningIteration

__all__ = [
    "ContinuousLearner",
    "EvolutionConfig",
    "EvolutionLoop",
    "EvolutionSnapshot",
    "FitnessEvaluator",
    "FitnessScores",
    "LearningIteration",
    "MutationEngine",
    "MutationType",
]
