"""DueCare adapter for the Kaggle Community Benchmarks SDK.

Public surface used by ``kaggle/04-kaggle-community-benchmark/kernel.py``
and by Kernel 01 / A-00 when they want to display "what the public
benchmark would say" alongside their own grading UI.

The subpackage is organised so each concern is one small file:

  * :mod:`.criteria` -- versioned natural-language criteria + the
    domain -> criterion-set mapping.
  * :mod:`.scoring` -- :class:`BenchmarkScoringPolicy` (Pydantic frozen)
    plus the default + alternative policies.
  * :mod:`.judge_schema` -- structured judge dataclass + custom
    ``prompt_fn`` for ``kbench.assertions.assess_response_with_judge``.
  * :mod:`.kbench_adapter` -- :func:`score_row`, :func:`build_assertions`
    and the fallback row corpus the kernel falls back to when the repo
    isn't attached as a Kaggle dataset.

Nothing here imports :mod:`kaggle_benchmarks` -- the SDK is only
referenced inside the kernel itself, so the subpackage stays
unit-testable in a plain Python environment.
"""

from __future__ import annotations

from .criteria import (
    BenchmarkCriterion,
    CORE_CRITERIA,
    CRITERIA_VERSION,
    criteria_statements,
    domain_criteria,
    get_criterion,
    known_domains,
)
from .judge_schema import (
    CriterionResult,
    DueCareJudgeReport,
    GRADE_ADEQUATE,
    GRADE_BEST,
    GRADE_GOOD,
    GRADE_HARMFUL,
    GRADE_INCOMPLETE,
    VALID_GRADES,
    build_judge_prompt,
)
from .kbench_adapter import (
    BenchmarkAssertion,
    BenchmarkRow,
    BenchmarkRowScore,
    DEFAULT_FALLBACK_ROWS,
    PROMPT_TEMPLATE,
    build_assertions,
    build_prompt,
    coerce_row,
    default_fallback_rows,
    score_row,
    select_judge_model,
)
from .scoring import (
    BenchmarkScoringPolicy,
    CombinedScore,
    DEFAULT_POLICY,
    DETERMINISTIC_ONLY_POLICY,
    JUDGE_HEAVY_POLICY,
)


__all__ = [
    "BenchmarkAssertion",
    "BenchmarkCriterion",
    "BenchmarkRow",
    "BenchmarkRowScore",
    "BenchmarkScoringPolicy",
    "CORE_CRITERIA",
    "CombinedScore",
    "CRITERIA_VERSION",
    "CriterionResult",
    "DEFAULT_FALLBACK_ROWS",
    "DEFAULT_POLICY",
    "DETERMINISTIC_ONLY_POLICY",
    "DueCareJudgeReport",
    "GRADE_ADEQUATE",
    "GRADE_BEST",
    "GRADE_GOOD",
    "GRADE_HARMFUL",
    "GRADE_INCOMPLETE",
    "JUDGE_HEAVY_POLICY",
    "PROMPT_TEMPLATE",
    "VALID_GRADES",
    "build_assertions",
    "build_judge_prompt",
    "build_prompt",
    "coerce_row",
    "criteria_statements",
    "default_fallback_rows",
    "domain_criteria",
    "get_criterion",
    "known_domains",
    "score_row",
    "select_judge_model",
]
