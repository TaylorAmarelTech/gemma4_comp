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

BLOCK = '''

AT_A_GLANCE_INTRO = """---

## At a glance

Same harness across three safety domains — the proof that DueCare is a framework, not a trafficking-only tool.
"""


AT_A_GLANCE_CODE = \'\'\'''' + STAT_HELPERS + '''
cards = [
    _stat_card("3",    "domain packs",        "trafficking / tax_evasion / financial_crime", "primary"),
    _stat_card("same", "rubric + harness",    "no per-domain code changes",                   "info"),
    _stat_card("9",    "capability tests",    "run identically in each domain",              "warning"),
    _stat_card("CPU",  "kernel",              "no GPU required for the proof",               "success"),
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    _step("Load packs",   "3 domains",         "primary"),
    _step("Pick 9 tasks", "shared capability", "info"),
    _step("Run same loop","per domain",        "warning"),
    _step("Score same",   "same rubric",       "warning"),
    _step("Compare",      "cross-domain table","success"),
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">Cross-domain proof pipeline</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
\'\'\'


'''


p = pathlib.Path('scripts/build_notebook_200_cross_domain_proof.py')
t = p.read_text(encoding='utf-8')
if 'AT_A_GLANCE_INTRO' in t:
    print('SKIP: 200 already injected')
else:
    t = t.replace('\ndef build() -> None:', BLOCK + '\ndef build() -> None:')
    t = t.replace('md(HEADER),', 'md(HEADER),\n        md(AT_A_GLANCE_INTRO),\n        code(AT_A_GLANCE_CODE),', 1)
    p.write_text(t, encoding='utf-8')
    print('OK: injected 200')
