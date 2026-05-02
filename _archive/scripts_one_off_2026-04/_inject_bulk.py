"""Bulk inject at-a-glance (stat cards + pipeline) into every direct build
script that's missing it.

The stat card / step content is derived from the notebook title and
intro (best-effort generic labels). Each build script gets a consistent
visual treatment; notebook-specific polish can follow in a later session.
"""
import pathlib
import re

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


# Per-notebook content. Each entry: (stat_cards, pipeline_steps, intro_body, pipeline_title)
CONTENT = {
    '130': {
        'cards': [('5','grade levels','worst -> best','primary'),
                  ('categories','axes shown','sector / corridor / difficulty','info'),
                  ('1','example per grade','real graded prompt','warning'),
                  ('< 1 min','runtime','CPU, no model','success')],
        'steps': [('Load corpus','from pack','primary'),('Group','by category','info'),('Sample','one per grade','warning'),('Render','5-band cards','success')],
        'body':'Walk through the corpus by category, sector, corridor, and difficulty; render the 5-grade rubric.',
        'title':'Corpus walkthrough',
    },
    '150': {
        'cards': [('Gemma 4 E4B','model','4-bit on T4','primary'),('text-in / text-out','interface','single turn','info'),('ipywidgets','UI','live Kaggle widget','warning'),('T4','GPU','on-device','success')],
        'steps': [('Load E4B','4-bit','primary'),('Widget','textarea','info'),('Generate','single turn','warning'),('Render','response','success')],
        'body':'Type any prompt and see stock Gemma 4 respond live on a Kaggle T4 GPU.',
        'title':'Playground flow',
    },
    '152': {
        'cards': [('Gemma 4 E4B','model','on-device','primary'),('3','personas','neutral / judge / citation','info'),('live','safety score','per response','warning'),('stateful','chat','history + presets','success')],
        'steps': [('Load E4B','4-bit','primary'),('Preset','persona','info'),('Chat','with history','warning'),('Score','live rubric','success')],
        'body':'Stateful chat with Gemma 4 E4B with a live safety-score overlay and three persona presets.',
        'title':'Interactive chat',
    },
    '155': {
        'cards': [('native','function calling','Gemma 4 feature','primary'),('9','sample tools','hotline / statute / ...','info'),('live','tool picker','watch model decide','warning'),('T4','GPU','single model load','success')],
        'steps': [('Load E4B','with tools','primary'),('Describe tools','JSON schema','info'),('User prompt','any scenario','warning'),('Render','tool call + args','success')],
        'body':'Gemma 4 picks a tool and arguments for any scenario you type.',
        'title':'Tool-calling demo',
    },
    '160': {
        'cards': [('Gemma 4','multimodal','image + text','primary'),('upload','image','any format','info'),('question','text prompt','user-typed','warning'),('live','inference','single GPU call','success')],
        'steps': [('Load multimodal','4-bit','primary'),('Upload image','widget','info'),('Ask','text prompt','warning'),('Render','response','success')],
        'body':'Upload an image, ask a question, see the multimodal response live.',
        'title':'Image playground',
    },
    '170': {
        'cards': [('3','modes compared','plain / RAG / guided','primary'),('same','model','stock Gemma 4','info'),('live','inference','user prompt','warning'),('T4','GPU','single load','success')],
        'steps': [('Load E4B','4-bit','primary'),('User prompt','any','info'),('Run 3 modes','parallel','warning'),('Compare','side-by-side','success')],
        'body':'Type any prompt and see plain vs RAG vs guided side-by-side on a T4 GPU.',
        'title':'Context lift demo',
    },
    '180': {
        'cards': [('Gemma 4','multimodal','image + text','primary'),('7','extracted fields','employer / fees / ...','info'),('12','trafficking rules','ILO / TIP / Saudi labor','warning'),('severity','0-100','triage score','success')],
        'steps': [('Load multimodal','4-bit','primary'),('Upload contract','image','info'),('Extract fields','JSON','warning'),('Flag indicators','12 rules','danger'),('Score','severity 0-100','success')],
        'body':'Upload a recruitment-contract image; Gemma 4 multimodal extracts key fields and flags trafficking indicators.',
        'title':'Document inspection',
    },
    '181': {
        'cards': [('6','slot columns','stock / DAN / abliterated / ...','primary'),('top-12','most-informative','sorted by disagreement','info'),('inline','highlight','refusal + harmful phrases','warning'),('CPU','kernel','reads artifacts','success')],
        'steps': [('Load artifacts','from 186-189','primary'),('Join','on prompt_id','info'),('Rank','by disagreement','warning'),('Render','full-width cards','success')],
        'body':'Visual side-by-side viewer across stock / abliterated / uncensored / cracked slots.',
        'title':'Response viewer',
    },
    '182': {
        'cards': [('40','calibration prompts','20 harmful + 20 benign','primary'),('every','layer','per-layer PCA','info'),('silhouette','metric','separability score','warning'),('T4','GPU','one fp16 load','success')],
        'steps': [('Load stock','fp16','primary'),('Forward','40 prompts','info'),('Residuals','every layer','warning'),('PCA','per layer','warning'),('Best layer','silhouette peak','success')],
        'body':'Where does refusal become linearly separable in the residual stream?',
        'title':'Refusal direction',
    },
    '184': {
        'cards': [('3','gating modes','prompt / entropy / always','primary'),('1','tool','consult_frontier','info'),('native','function calling','load-bearing Gemma 4 feature','warning'),('T4','GPU','one Gemma load','success')],
        'steps': [('Load Gemma','4-bit','primary'),('Prompt','with tool','info'),('Decide','local vs escalate','warning'),('Frontier','consult','danger'),('Score','3 modes','success')],
        'body':'Gemma 4 calls a frontier model when uncertain via native function calling.',
        'title':'Escalation flow',
    },
    '185': {
        'cards': [('4','slots compared','stock / abliterated / community / 31B','primary'),('CPU','comparator','no model load','info'),('6','expected slots','186-189 + 3 conditions','warning'),('graceful','missing slots','"not yet run" row','success')],
        'steps': [('Find artifacts','root dir','primary'),('Load slots','meta+responses','info'),('Score','same rubric','warning'),('Render','tables + plots','success')],
        'body':'CPU comparator that joins the 186-189 per-model artifact bundles.',
        'title':'Comparator pipeline',
    },
    '186': {
        'cards': [('3','conditions','baseline / DAN / roleplay','primary'),('stock','Gemma 4 E4B','unmodified','info'),('15','benchmark prompts','graded slice','warning'),('T4','GPU','one model load','success')],
        'steps': [('Load stock','4-bit','primary'),('Baseline','no prefix','info'),('DAN','preamble','warning'),('Roleplay','framing','warning'),('Save','3 slots','success')],
        'body':'Stock Gemma 4 E4B under three prompt-level jailbreak conditions.',
        'title':'Stock baseline',
    },
    '187': {
        'cards': [('30+30','calibration','harmful + benign prompts','primary'),('mid-band','layer picked','largest diff-mean norm','info'),('o_proj + down_proj','edited','residual-stream writes','warning'),('T4 x 2','GPU','bf16 abliteration','success')],
        'steps': [('Load bf16','stock','primary'),('Calibrate','30+30','info'),('Refusal dir','per-layer','warning'),('Ablate','subtract','danger'),('Probe','validate','success')],
        'body':'In-kernel abliteration: calibrate, pick layer, subtract refusal direction.',
        'title':'Abliteration recipe',
    },
    '188': {
        'cards': [('ranked','probe list','huihui / AEON-7 / mlabonne','primary'),('first','that loads','fallback chain','info'),('NVFP4','excluded','Blackwell-only','warning'),('T4','GPU','4-bit load','success')],
        'steps': [('Probe candidates','HF hub','primary'),('Load first','4-bit','info'),('Run benchmark','15 prompts','warning'),('Gen red-team','10 prompts','success')],
        'body':'Load the first resolvable community uncensored Gemma variant.',
        'title':'Community probe',
    },
    '189': {
        'cards': [('31B','model','dealignai/JANG_4M-CRACK','primary'),('22 GB','VRAM required','gated','warning'),('4-bit','nf4','device_map auto','info'),('L4x4 / A100','GPU','skip on T4','danger')],
        'steps': [('VRAM gate','>= 22 GB','warning'),('Load 31B','4-bit','primary'),('Run benchmark','15 prompts','info'),('Gen red-team','10 prompts','success')],
        'body':'4-bit 31B cracked Gemma; skips gracefully on single T4.',
        'title':'31B gated run',
    },
    '500': {
        'cards': [('12','agents','autonomous','primary'),('1','supervisor','AgentSupervisor','info'),('function-call','orchestration','native Gemma 4','warning'),('CPU','walkthrough','no inference','success')],
        'steps': [('Supervisor','AgentSupervisor','primary'),('Dispatch','to agents','info'),('Judge / curator','score + collect','warning'),('Historian','summarize','success')],
        'body':'Walk through the agent swarm: 12 specialized agents + a supervisor.',
        'title':'Swarm architecture',
    },
    '530': {
        'cards': [('Unsloth','framework','efficient LoRA','primary'),('4-bit','quant','nf4','info'),('LoRA','adapter','parameter-efficient','warning'),('T4','GPU','single-run','success')],
        'steps': [('Load stock','4-bit','primary'),('Attach LoRA','r=16','info'),('Train','curriculum','warning'),('Merge + export','GGUF + LiteRT','success')],
        'body':'Fine-tune Gemma 4 with Unsloth + LoRA, export to GGUF and LiteRT.',
        'title':'Fine-tune pipeline',
    },
    '620': {
        'cards': [('17','endpoints','FastAPI tour','primary'),('curl','examples','per endpoint','info'),('live','catalog','vs app drift audit','warning'),('upload','case intake','multimodal','success')],
        'steps': [('Load catalog','17 endpoints','primary'),('Show curl','examples','info'),('Response shapes','documented','warning'),('Drift audit','catalog vs app','success')],
        'body':'Walk all 17 FastAPI endpoints with curl examples and live drift audit.',
        'title':'API endpoint tour',
    },
}


def _block(cards, steps, body, title):
    card_lines = ',\n    '.join(f"_stat_card({v!r}, {l!r}, {s!r}, {k!r})" for v, l, s, k in cards)
    step_lines = ',\n    '.join(f"_step({l!r}, {s!r}, {k!r})" for l, s, k in steps)
    return (f'''

AT_A_GLANCE_INTRO = """---

## At a glance

{body}
"""


AT_A_GLANCE_CODE = \'\'\'{STAT_HELPERS}
cards = [
    {card_lines}
]
display(HTML('<div style="margin:8px 0">' + ''.join(cards) + '</div>'))

steps = [
    {step_lines}
]
display(HTML(
    '<div style="margin:10px 0 4px 0;font-family:system-ui,-apple-system,sans-serif;'
    'font-weight:600;color:#1f2937">{title}</div>'
    '<div style="margin:6px 0">' + _arrow.join(steps) + '</div>'
))
\'\'\'


''')


SCRIPTS = {
    '130': 'build_notebook_130_prompt_corpus_exploration.py',
    '150': 'build_notebook_150_free_form_gemma_playground.py',
    '152': 'build_notebook_152_interactive_gemma_chat.py',
    '155': 'build_notebook_155_tool_calling_playground.py',
    '160': 'build_notebook_160_image_processing_playground.py',
    '170': 'build_notebook_170_live_context_injection_playground.py',
    '180': 'build_notebook_180_multimodal_document_inspector.py',
    '181': 'build_notebook_181_jailbreak_response_viewer.py',
    '182': 'build_notebook_182_refusal_direction_visualizer.py',
    '184': 'build_notebook_184_frontier_consultation_playground.py',
    '185': 'build_notebook_185_jailbroken_gemma_comparison.py',
    '186': 'build_notebook_186_jailbreak_stock_gemma.py',
    '187': 'build_notebook_187_jailbreak_abliterated_e4b.py',
    '188': 'build_notebook_188_jailbreak_uncensored_community.py',
    '189': 'build_notebook_189_jailbreak_cracked_31b.py',
    '500': 'build_notebook_500_agent_swarm_deep_dive.py',
    '530': 'build_notebook_530_phase3_unsloth_finetune.py',
    '620': 'build_notebook_620_demo_api_endpoint_tour.py',
}


for nb_id, fname in SCRIPTS.items():
    if nb_id not in CONTENT:
        print(f'SKIP {nb_id}: no content defined')
        continue
    path = pathlib.Path('scripts') / fname
    if not path.exists():
        print(f'SKIP {nb_id}: {path} not found')
        continue
    t = path.read_text(encoding='utf-8')
    if 'AT_A_GLANCE_INTRO' in t:
        print(f'SKIP {nb_id}: already has AT_A_GLANCE')
        continue
    c = CONTENT[nb_id]
    block = _block(c['cards'], c['steps'], c['body'], c['title'])

    # Insert before "def build"
    if '\ndef build() -> None:' in t:
        t = t.replace('\ndef build() -> None:', block + '\ndef build() -> None:', 1)
    elif '\ndef build():' in t:
        t = t.replace('\ndef build():', block + '\ndef build():', 1)
    else:
        print(f'FAIL {nb_id}: no def build found')
        continue

    # Insert cells after md(HEADER)
    md_pattern = 'md(HEADER),'
    if md_pattern in t:
        t = t.replace(md_pattern, md_pattern + '\n        md(AT_A_GLANCE_INTRO),\n        code(AT_A_GLANCE_CODE),', 1)
    else:
        print(f'WARN {nb_id}: could not find md(HEADER), in cells')

    path.write_text(t, encoding='utf-8')
    print(f'OK {nb_id}: injected into {fname}')
