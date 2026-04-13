"""Evolution loop -- select, mutate, evaluate, archive.

A simple generational GA over a population of attack probes.  Each call
to ``step()`` runs one generation:

    1. **Select** -- fitness-proportionate sampling with exploration bonus
    2. **Mutate** -- apply one mutation per selected parent
    3. **Evaluate** -- score offspring fitness from benchmark results
    4. **Archive** -- keep elite population, archive the rest

The loop is deliberately synchronous and side-effect-free so it can be
driven from any outer harness (Coordinator agent, Kaggle notebook,
CLI script).

Ported from the orchestrator iteration loop in
trafficking_llm_benchmark/src/harness/orchestrator.py, distilled to the
genetic-algorithm core without the full orchestrator machinery.
"""

from __future__ import annotations

import random
from typing import Any

from pydantic import BaseModel, Field

from .fitness_evaluator import FitnessEvaluator, FitnessScores
from .mutation_engine import MutationEngine, MutationType


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class EvolutionConfig(BaseModel):
    """Tunable knobs for one evolution run."""

    population_cap: int = 400
    offspring_per_step: int = 10
    elite_ratio: float = 0.15
    tournament_size: int = 3
    exploration_decay: float = 0.1


# ---------------------------------------------------------------------------
# Snapshot (what comes out of each generation)
# ---------------------------------------------------------------------------

class EvolutionSnapshot(BaseModel):
    """Summary of one generation."""

    generation: int
    population_size: int
    offspring_created: int
    archive_size: int
    top_fitness: float = 0.0
    mean_fitness: float = 0.0
    top_attacks: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------

class EvolutionLoop:
    """Maintains and evolves a population of attack probes.

    Parameters
    ----------
    mutator:
        A ``MutationEngine`` instance (provides the 13 operators).
    evaluator:
        A ``FitnessEvaluator`` instance (scores on 5 dimensions).
    config:
        Tunable knobs.
    seed_population:
        Initial attack dicts.  Each must have at least ``id`` and
        ``prompt`` keys.
    """

    def __init__(
        self,
        *,
        mutator: MutationEngine,
        evaluator: FitnessEvaluator,
        config: EvolutionConfig | None = None,
        seed_population: list[dict[str, Any]] | None = None,
    ) -> None:
        self._mutator = mutator
        self._evaluator = evaluator
        self._cfg = config or EvolutionConfig()
        self._population: list[dict[str, Any]] = list(seed_population or [])
        self._archive: list[dict[str, Any]] = []
        self._generation = 0

    # -- read-only accessors ------------------------------------------------

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def population(self) -> list[dict[str, Any]]:
        return list(self._population)

    @property
    def archive(self) -> list[dict[str, Any]]:
        return list(self._archive)

    # -- core loop ----------------------------------------------------------

    def step(
        self,
        results_map: dict[str, list[dict[str, Any]]],
    ) -> EvolutionSnapshot:
        """Run one generation.

        Parameters
        ----------
        results_map:
            ``{attack_id: [result_dict, ...]}`` from the most recent
            benchmark run.  Used to update fitness scores.

        Returns
        -------
        EvolutionSnapshot
            Summary of the generation.
        """
        self._generation += 1

        # 1. Score current population
        self._score_population(results_map)

        # 2. Select parents via tournament
        parents = self._select(self._cfg.offspring_per_step)

        # 3. Mutate to produce offspring
        offspring = self._breed(parents)

        # 4. Score offspring (with whatever results we have for parents)
        for child in offspring:
            parent_id = child.get("parent_id", "")
            child_results = results_map.get(parent_id, [])
            scores = self._evaluator.evaluate(child, child_results)
            child["fitness"] = scores.overall
            child["fitness_scores"] = scores.model_dump()
            self._evaluator.add_to_archive(child)

        # 5. Merge offspring into population
        self._population.extend(offspring)

        # 6. Prune to cap
        self._prune()

        # 7. Adapt mutation weights from fitness deltas
        self._adapt_weights(offspring)

        return self._snapshot(offspring_created=len(offspring))

    # -- selection ----------------------------------------------------------

    def _select(self, n: int) -> list[dict[str, Any]]:
        """Tournament selection with exploration bonus."""
        if not self._population:
            return []

        selected: list[dict[str, Any]] = []
        for _ in range(n):
            candidates = random.sample(
                self._population,
                k=min(self._cfg.tournament_size, len(self._population)),
            )
            winner = max(candidates, key=lambda a: self._selection_score(a))
            selected.append(winner)
        return selected

    def _selection_score(self, attack: dict[str, Any]) -> float:
        fitness = attack.get("fitness", 0.5)
        test_count = len(attack.get("result_ids", []))
        exploration = 1.0 / (1.0 + test_count * self._cfg.exploration_decay)
        return fitness + exploration

    # -- breeding -----------------------------------------------------------

    def _breed(self, parents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        offspring: list[dict[str, Any]] = []
        for parent in parents:
            child = self._mutator.mutate(parent)
            child["generation"] = self._generation
            # Start slightly below parent fitness to earn its keep
            child["fitness"] = parent.get("fitness", 0.5) * 0.9
            offspring.append(child)
        return offspring

    # -- scoring ------------------------------------------------------------

    def _score_population(
        self,
        results_map: dict[str, list[dict[str, Any]]],
    ) -> None:
        for attack in self._population:
            aid = attack.get("id", "")
            results = results_map.get(aid, [])
            if not results:
                continue
            scores = self._evaluator.evaluate(attack, results)
            attack["fitness"] = scores.overall
            attack["fitness_scores"] = scores.model_dump()

    # -- pruning ------------------------------------------------------------

    def _prune(self) -> None:
        """Keep population at cap; archive overflow."""
        if len(self._population) <= self._cfg.population_cap:
            return

        self._population.sort(key=lambda a: a.get("fitness", 0.0), reverse=True)

        # Preserve elite slice unconditionally
        elite_n = max(1, int(self._cfg.population_cap * self._cfg.elite_ratio))
        keep_n = self._cfg.population_cap

        survivors = self._population[:keep_n]
        overflow = self._population[keep_n:]

        self._archive.extend(overflow)
        self._population = survivors

    # -- weight adaptation --------------------------------------------------

    def _adapt_weights(self, offspring: list[dict[str, Any]]) -> None:
        """Tell the mutation engine which operators produced fitness gains."""
        for child in offspring:
            mutations = child.get("mutations", [])
            if not mutations:
                continue
            last_mutation = mutations[-1]
            parent_fitness = child.get("fitness", 0.5) / 0.9  # undo the 0.9 discount
            child_fitness = child.get("fitness", 0.5)
            delta = child_fitness - parent_fitness

            try:
                mtype = MutationType(last_mutation)
            except ValueError:
                continue
            self._mutator.record_fitness_delta(mtype, delta)

    # -- snapshot -----------------------------------------------------------

    def _snapshot(self, *, offspring_created: int) -> EvolutionSnapshot:
        fitnesses = [a.get("fitness", 0.0) for a in self._population]
        top_n = sorted(self._population, key=lambda a: a.get("fitness", 0.0), reverse=True)[:5]
        return EvolutionSnapshot(
            generation=self._generation,
            population_size=len(self._population),
            offspring_created=offspring_created,
            archive_size=len(self._archive),
            top_fitness=max(fitnesses) if fitnesses else 0.0,
            mean_fitness=sum(fitnesses) / len(fitnesses) if fitnesses else 0.0,
            top_attacks=[
                {"id": a.get("id"), "fitness": a.get("fitness", 0.0), "category": a.get("category")}
                for a in top_n
            ],
        )
