"""Single source of truth for Kaggle public slug overrides.

The default slug for a notebook is the value on the ``slug`` key of its
entry in the ``PHASES`` list inside ``build_index_notebook.py``. The
default matches the canonical ``duecare-NNN-*`` pattern unless the live
Kaggle kernel was first pushed under a different slug and Kaggle will
not let us move the kernel to the canonical slug without losing the
public URL.

When the live Kaggle slug differs from the default, add an override
here and the three builders (``build_index_notebook.py``,
``build_notebook_005_glossary.py``, and
``build_section_conclusion_notebooks.py``) will pick it up through the
``PUBLIC_SLUG_OVERRIDES`` import.

Keep this map short. Only record deviations. Redundant entries where
the override equals the default add noise without adding signal.

The ``UNPUBLISHED_IDS`` set is kept only for historical compatibility
with older builders. Keep it empty whenever the full tracked suite is
live on Kaggle.
"""

from __future__ import annotations


PUBLIC_SLUG_OVERRIDES: dict[str, str] = {
    # 010: the live kernel first shipped under the longer quickstart slug.
    "010": "010-duecare-quickstart-in-5-minutes",
    # 100: first live push landed at the keyword-rich slug; Kaggle
    # will not let us rename without losing the URL.
    "100": "duecare-real-gemma-4-on-50-trafficking-prompts",
    # 105: live kernel at the numeric-first form.
    "105": "105-duecare-prompt-corpus-introduction",
    # 110: live kernel is still the original 00a publish slug.
    "110": "00a-duecare-prompt-prioritizer-data-pipeline",
    # 120: current canonical live slug is the short-form.
    "120": "duecare-prompt-remixer",
    # 140: live slug is numeric-first.
    "140": "140-duecare-evaluation-mechanics",
    # 190: live slug is numeric-first.
    # 245: Gemini API comparison is live under numeric-first slug.
    "245": "245-duecare-gemini-api-comparison",
    # 200: live push landed at the non-prefixed slug; ``duecare-200-*``
    # would 404.
    "200": "duecare-cross-domain-proof",
    # 210: live slug matches the default.
    "210": "duecare-gemma-vs-oss-comparison",
    # 250 / 260 / 300 / 400 / 420 / 500: public kernels landed under
    # explicit live slugs that differ from older local defaults.
    "250": "duecare-250-comparative-grading",
    "260": "duecare-260-rag-comparison",
    # 299: shortened title avoids Kaggle's long-slug create failure.
    "299": "299-duecare-text-evaluation-conclusion",
    "300": "duecare-300-adversarial-resistance",
    # 335: live slug is numeric-first.
    "335": "335-duecare-attack-vector-inspector",
    "400": "duecare-400-function-calling-multimodal",
    "420": "duecare-420-conversation-testing",
    # 430: newer numeric-first slug is the canonical public URL.
    "430": "duecare-430-rubric-evaluation",
    # 460: live slug is numeric-first.
    "460": "460-duecare-citation-verifier",
    "500": "duecare-500-agent-swarm-deep-dive",
    # 525 / 527 / 550: expanded Phase 3 pipeline notebooks are live.
    "525": "525-duecare-uncensored-grade-generator",
    "527": "527-duecare-uncensored-rubric-generator",
    # 540: live slug has ``fine-tune`` with the hyphen (not ``finetune``).
    "540": "540-duecare-fine-tune-delta-visualizer",
    "550": "550-duecare-ngo-partner-survey-pipeline",
    # 600: canonical live slug is numeric-first.
    "600": "600-duecare-results-dashboard",
    # 610: live capstone uses the numeric-first slug.
    "610": "610-duecare-submission-walkthrough",
    # 620: live slug is numeric-first.
    "620": "620-duecare-demo-api-endpoint-tour",
    # 650: live slug is numeric-first.
    "650": "650-duecare-custom-domain-walkthrough",
    # 181-189: Kaggle resolves these to the title-derived numeric-first
    # shape on first push. 181 and 185 are live at those slugs as of
    # 2026-04-19; the remaining entries are mapped pre-emptively so the
    # Index, Glossary, and section-conclusion builders link at the slugs
    # they will land on once the daily GPU batch quota clears.
    "181": "181-duecare-jailbreak-response-viewer",
    "182": "182-duecare-refusal-direction-visualizer",
    # 183 / 186 / 189: the ``NNN-duecare-*`` slug is locked on Kaggle
    # (push returns 409 Conflict; delete returns 403 Forbidden), so
    # these three fall back to the default ``duecare-NNN-*`` shape.
    # The override entries are intentionally absent — the builders
    # compute the default from the PHASES table.
    "184": "184-duecare-frontier-consultation-playground",
    "185": "185-duecare-jailbroken-gemma-comparison",
    "187": "187-duecare-jailbreak-abliterated-e4b",
    "188": "188-duecare-jailbreak-uncensored-community",
    # 699 / 799 / 899: section conclusions fell back to non-prefixed
    # slugs; Kaggle accepted those and the canonical forms 404.
    "699": "duecare-advanced-prompt-test-generation-conclusion",
    "799": "duecare-adversarial-evaluation-conclusion",
    "899": "duecare-solution-surfaces-conclusion",
}


UNPUBLISHED_IDS: set[str] = {
    # 015 / 020: new Section 1 content notebooks, drafted 2026-04-18; not
    # yet pushed to Kaggle. Index renders them as "(pending publication)".
    "015", "020",
}
