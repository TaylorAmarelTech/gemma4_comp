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

The ``UNPUBLISHED_IDS`` set lists notebook IDs whose kernels are not
yet live on Kaggle (either still in private draft or not yet pushed).
The index and glossary renderers use it to emit a ``(pending publication)``
label instead of a link that would 404. Move an ID out of this set as
soon as its kernel is public.
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
    # 110: current canonical live slug is the short-form.
    "110": "duecare-prompt-prioritizer",
    # 120: current canonical live slug is the short-form.
    "120": "duecare-prompt-remixer",
    # 140: live slug is numeric-first.
    "140": "140-duecare-evaluation-mechanics",
    # 190: live slug is numeric-first.
    "190": "190-duecare-rag-retrieval-inspector",
    # 200: live push landed at the non-prefixed slug; ``duecare-200-*``
    # would 404.
    "200": "duecare-cross-domain-proof",
    # 210: live slug matches the default.
    "210": "duecare-gemma-vs-oss-comparison",
    # 250: live slug is numeric-first.
    "250": "250-duecare-comparative-grading",
    # 260: live push landed at the non-prefixed slug.
    "260": "duecare-rag-comparison",
    # 300: live push carried the keyword-rich slug.
    "300": "300-duecare-adversarial-resistance",
    # 335: live slug is numeric-first.
    "335": "335-duecare-attack-vector-inspector",
    # 400: live push landed at the non-prefixed slug.
    "400": "duecare-function-calling-multimodal",
    # 420: first live push carried a keyword-rich slug; then a numeric
    # version was also published. Use the numeric variant as canonical.
    "420": "420-duecare-conversation-testing",
    # 430: newer numeric-first slug is the canonical public URL.
    "430": "duecare-430-rubric-evaluation",
    # 460: live slug is numeric-first.
    "460": "460-duecare-citation-verifier",
    # 500: live kernel uses the descriptive slug.
    "500": "duecare-12-agent-gemma-4-safety-pipeline",
    # 540: live slug has ``fine-tune`` with the hyphen (not ``finetune``).
    "540": "540-duecare-fine-tune-delta-visualizer",
    # 600: canonical live slug is numeric-first.
    "600": "600-duecare-results-dashboard",
    # 610: live capstone uses the numeric-first slug.
    "610": "610-duecare-submission-walkthrough",
    # 620: live slug is numeric-first.
    "620": "620-duecare-demo-api-endpoint-tour",
    # 650: live slug is numeric-first.
    "650": "650-duecare-custom-domain-walkthrough",
    # 699 / 799 / 899: section conclusions fell back to non-prefixed
    # slugs; Kaggle accepted those and the canonical forms 404.
    "699": "duecare-advanced-prompt-test-generation-conclusion",
    "799": "duecare-adversarial-evaluation-conclusion",
    "899": "duecare-solution-surfaces-conclusion",
}


# IDs whose public kernel is not yet live (still private, not yet pushed,
# or blocked on the daily SaveKernel rate limit). The index renders these
# as plain text with a "(pending publication)" label instead of a link.
UNPUBLISHED_IDS: set[str] = {
    # 099: orientation conclusion — not yet pushed.
    "099",
    # 150 / 155 / 160 / 170 / 180: free-form playgrounds not yet pushed
    # under canonical slugs; earlier builds pushed variants but the
    # canonical numeric-first forms have not landed.
    "150", "155", "160", "170", "180",
    # 181-189: jailbreak family built 2026-04 but blocked on the
    # Kaggle daily SaveKernel rate limit at publication time.
    "181", "182", "183", "184", "185", "186", "187", "188", "189",
    # 199: free-form exploration conclusion — not yet pushed.
    "199",
    # 130: prompt corpus exploration — not yet live under any slug.
    "130",
    # 299 / 399 / 499 / 599: baseline-text / advanced-evaluation /
    # model-improvement section conclusions — drafted but not yet live.
    "299", "399", "499", "599",
    # 220 / 230 / 240 / 270: comparison notebooks not yet pushed under
    # canonical slugs.
    "220", "230", "240", "270",
    # 310: prompt factory — not yet live.
    "310",
    # 320: supergemma safety gap — not yet live.
    "320",
    # 410: LLM judge grading — not yet live (a 410 variant exists
    # but under a legacy slug; leave pending until the canonical push).
    "410",
    # 440 / 450: advanced judging notebooks — not yet live.
    "440", "450",
    # 510 / 520 / 530: phase 2 / 3 model-improvement notebooks —
    # not yet live.
    "510", "520", "530",
    # 660-695: deployment-application notebooks are local drafts until
    # the next Kaggle publication window.
    "660", "670", "680", "690", "695",
}
