"""Inject at-a-glance into 110 and 120 at the md(PREVIEW_MD) insertion point."""
import pathlib

STAT_HELPERS = '''from IPython.display import HTML, display

_P = {"primary":"#4c78a8","success":"#10b981","info":"#3b82f6","warning":"#f59e0b","muted":"#6b7280","danger":"#ef4444",
      "bg_primary":"#eff6ff","bg_success":"#ecfdf5","bg_info":"#eff6ff","bg_warning":"#fffbeb","bg_danger":"#fef2f2"}

def _stat_card(value, label, sub, kind="primary"):
    c = _P[kind]; bg = _P.get(f"bg_{kind}", _P["bg_info"])
    return (f'<div style="display:inline-block;vertical-align:top;width:22%;margin:4px 1%;padding:14px 16px;'
            f'background:{bg};border-left:5px solid {c};border-radius:4px;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-size:11px;font-weight:600;color:{c};text-transform:uppercase;letter-spacing:0.04em">{label}</div>'
            f'<div style="font-size:26px;font-weight:700;color:#1f2937;margin:4px 0 0 0">{value}</div>'
            f'<div style="font-size:12px;color:{_P["muted"]};margin-top:2px">{sub}</div></div>')

def _step(label, sub, kind="primary"):
    c = _P[kind]; bg = _P.get(f"bg_{kind}", _P["bg_info"])
    return (f'<div style="display:inline-block;vertical-align:middle;min-width:138px;padding:10px 12px;'
            f'margin:4px 0;background:{bg};border:2px solid {c};border-radius:6px;text-align:center;'
            f'font-family:system-ui,-apple-system,sans-serif">'
            f'<div style="font-weight:600;color:#1f2937;font-size:13px">{label}</div>'
            f'<div style="color:{_P["muted"]};font-size:11px;margin-top:2px">{sub}</div></div>')

_arrow = f'<span style="display:inline-block;vertical-align:middle;margin:0 4px;color:{_P["muted"]};font-size:20px">&rarr;</span>'
'''

# --- 110 Prompt Prioritizer ---
INJECT_110 = '''

AT_A_GLANCE_INTRO = """<a id="at-a-glance"></a>
## At a glance

The selection algorithm in one picture — funnel from raw corpus to shipped slice.
"""


AT_A_GLANCE_CODE = \'\'\'''' + STAT_HELPERS + '''
cards = [
    _stat_card("74,567", "raw prompts",     "full trafficking corpus",      "primary"),
    _stat_card("204",    "graded (Tier 1)", "5 reference responses each",    "success"),
    _stat_card("5",      "primary categories","minimum representation",      "info"),
    _stat_card("~2,000", "curated target",  "downstream evaluation slice",    "warning"),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step("Load corpus",   "74K prompts",       "primary"),
    _step("Length filter", "20-10K chars",      "info"),
    _step("Tier 1 graded", "204 calibration",   "success"),
    _step("Tier 2 fill",   "5 categories >=100","warning"),
    _step("Near-dup drop", "first-100-char match","warning"),
    _step("Curated slice", "~2K prompts",        "success"),
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Selection funnel</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
\'\'\'


'''

# --- 120 Prompt Remixer ---
INJECT_120 = '''

AT_A_GLANCE_INTRO = """<a id="at-a-glance"></a>
## At a glance

Five adversarial mutation strategies, one curated prompt to many robustness tests.
"""


AT_A_GLANCE_CODE = \'\'\'''' + STAT_HELPERS + '''
cards = [
    _stat_card("5",    "mutation strategies",  "academic / roleplay / corporate / urgency / corridor", "primary"),
    _stat_card("1-2",  "variants per prompt",  "random sample per curated prompt",                     "info"),
    _stat_card("fixed","seed",                 "random.seed(42) for reproducibility",                  "warning"),
    _stat_card("< 2 min","runtime",            "CPU kernel, no inference",                             "success"),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step("Load curated", "from 110",         "primary"),
    _step("Pick 1-2",     "random per prompt","info"),
    _step("Mutate",       "five strategies",  "warning"),
    _step("Tag provenance","base_prompt_id",  "warning"),
    _step("Combine",      "originals+variants","success"),
    _step("Save JSONL",   "feeds 100",         "success"),
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Remix pipeline</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
\'\'\'


'''


def apply(path, injected_block, cells_anchor, cells_insert):
    p = pathlib.Path(path)
    t = p.read_text(encoding='utf-8')
    if 'AT_A_GLANCE_INTRO' in t:
        return f'SKIP: already has AT_A_GLANCE in {path}'
    # Insert before "def build"
    t = t.replace('\ndef build() -> None:', injected_block + '\ndef build() -> None:')
    # Insert cells: `md(PREVIEW_MD),` -> add AT_A_GLANCE right after HEADER
    t = t.replace(cells_anchor, cells_insert, 1)
    p.write_text(t, encoding='utf-8')
    return f'OK: injected {path}'


print(apply(
    'scripts/build_notebook_110.py',
    INJECT_110,
    'md(HEADER),\n        md(PREVIEW_MD),',
    'md(HEADER),\n        md(AT_A_GLANCE_INTRO),\n        code(AT_A_GLANCE_CODE),\n        md(PREVIEW_MD),',
))

print(apply(
    'scripts/build_notebook_120.py',
    INJECT_120,
    'md(HEADER),\n        md(PREVIEW_MD),',
    'md(HEADER),\n        md(AT_A_GLANCE_INTRO),\n        code(AT_A_GLANCE_CODE),\n        md(PREVIEW_MD),',
))
