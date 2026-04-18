"""Align 7 kernel titles to the live Kaggle values so push warnings stop.

Also patches the source build script's KERNEL_TITLE (or title= literal) when
present so future rebuilds don't re-break the alignment.
"""
import json, re, pathlib

FIXES = {
    'duecare_005_glossary': ('DueCare 005 Glossary', 'build_notebook_005_glossary.py'),
    'duecare_110_prompt_prioritizer': ('DueCare Prompt Prioritizer', 'build_notebook_110.py'),
    'duecare_120_prompt_remixer': ('DueCare Prompt Remixer', 'build_notebook_120.py'),
    'duecare_210_oss_model_comparison': ('DueCare Gemma vs OSS Comparison', 'build_notebook_210_oss_model_comparison.py'),
    'duecare_699_advanced_prompt_test_generation_conclusion': (
        'DueCare Advanced Prompt-Test Generation Conclusion', None),
    'duecare_799_adversarial_prompt_test_evaluation_conclusion': (
        'DueCare Adversarial Evaluation Conclusion', None),
    'duecare_899_solution_surfaces_conclusion': (
        'DueCare Solution Surfaces Conclusion', None),
}

for kdir, (new_title, script_name) in FIXES.items():
    meta_path = pathlib.Path(f'kaggle/kernels/{kdir}/kernel-metadata.json')
    meta = json.load(meta_path.open())
    old = meta['title']
    if old == new_title:
        print(f'OK {kdir}: already aligned')
    else:
        meta['title'] = new_title
        json.dump(meta, meta_path.open('w'), indent=2)
        print(f'metadata {kdir}: {old!r} -> {new_title!r}')
    # Patch source build script if available
    if script_name:
        sp = pathlib.Path(f'scripts/{script_name}')
        if sp.exists():
            st = sp.read_text(encoding='utf-8')
            # Replace KERNEL_TITLE assignment
            new_st, n = re.subn(
                r'KERNEL_TITLE\s*=\s*"[^"]*"',
                f'KERNEL_TITLE = {new_title!r}',
                st, count=1
            )
            if n:
                sp.write_text(new_st, encoding='utf-8')
                print(f'  source {script_name} KERNEL_TITLE aligned')
