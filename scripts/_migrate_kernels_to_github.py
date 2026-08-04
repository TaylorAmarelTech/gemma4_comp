"""One-shot migration: convert remaining wheel-loading kernels to GitHub-only.

Targets A-05 (lingering Method 2 fallback), A-06/A-07/A-09/A-10/A-11
(no GitHub install at all). Each kernel gets the canonical install_duecare_from_github()
function (matching kaggle/_archive/notebooks/A-08-research-graphs/kernel.py) and its existing
wheel-walking install function body is replaced with a thin call.

Policy 2026-05-11: NO Kaggle wheel datasets. GitHub Release wheels (Tier 1),
git+https source install at pinned commit (Tier 2).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANONICAL_INSTALL = '''
# ===========================================================================
# DueCare from GitHub (no Kaggle wheel datasets)
# ===========================================================================
# Policy 2026-05-11: all DueCare packages install directly from GitHub.
# No attached `*-wheels` Kaggle dataset is required. Two-tier strategy:
#   1. GitHub Release wheels at /releases/download/v{VERSION}/
#   2. GitHub source install via git+https://...@<sha>#subdirectory=...
# Notebook 01's install_chat_wheels() is the canonical reference.
DUECARE_VERSION    = "0.1.0"
DUECARE_REPO       = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "419ebe0"
DUECARE_PACKAGES   = ["duecare-llm-chat"]   # pulls in core for harness data


def install_duecare_from_github() -> bool:
    """Install DueCare packages from GitHub. Wheels-free, judge-transparent.
    Tier 1: GitHub Release wheels. Tier 2: git+https source-install.
    """
    print("=" * 76)
    print("[install] DueCare packages from GitHub (no Kaggle wheel datasets)")
    print("=" * 76)
    base_url = f"https://github.com/{DUECARE_REPO}/releases/download/v{DUECARE_VERSION}"
    success = 0
    for i, pkg in enumerate(DUECARE_PACKAGES, 1):
        wheel_name = f"{pkg.replace('-', '_')}-{DUECARE_VERSION}-py3-none-any.whl"
        url = f"{base_url}/{wheel_name}"
        print(f"  > [{i}/{len(DUECARE_PACKAGES)}] release wheel: {wheel_name}")
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60", url]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode == 0:
            success += 1
            print(f"  + installed {pkg} from release v{DUECARE_VERSION}")
        else:
            tail = (proc.stderr or "")[-200:]
            if "404" in tail or "Not Found" in tail:
                print(f"  - release wheel not found, falling back to source install")
                break
            print(f"  - {pkg} release wheel failed: {tail}")
    if success == len(DUECARE_PACKAGES):
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        return True
    git_pkgs = [
        f"git+https://github.com/{DUECARE_REPO}.git@{DUECARE_COMMIT_SHA}"
        f"#subdirectory=packages/{p}"
        for p in DUECARE_PACKAGES
    ]
    print(f"  > source install @ {DUECARE_COMMIT_SHA} ({len(git_pkgs)} pkg)")
    cmd = [sys.executable, "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--timeout=300", *git_pkgs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if proc.returncode == 0:
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        print(f"  + source install ok @ {DUECARE_COMMIT_SHA}")
        return True
    raise SystemExit(f"DueCare GitHub install failed: {(proc.stderr or '')[-300:]}")
'''


def fix_a05() -> None:
    """Remove lingering Method 2 wheel fallback from A-05."""
    path = ROOT / 'kaggle/_archive/notebooks/A-05-gemma-content-classification-evaluation/kernel.py'
    text = path.read_text(encoding='utf-8')
    pattern = re.compile(
        r'    # Method 2: Fallback to wheels dataset \(original logic\)\n'
        r'    if not Path\("/kaggle/input"\)\.exists\(\):\n'
        r'        print\("  \(not in Kaggle; skipping wheel install\)"\)\n'
        r'        return 0\n'
        r'\n'
        r'    found = sorted\(p for p in Path\("/kaggle/input"\)\.rglob\("\*\.whl"\)\n'
        r'                    if "duecare" in p\.name\.lower\(\)\)\n'
        r'    if not found:\n'
        r'        raise SystemExit\(\n'
        r'            f"GitHub bootstrap failed AND no wheels found in /kaggle/input\. "\n'
        r'            f"Enable internet OR attach dataset: taylorsamarel/\{DATASET_SLUG\}"\)\n'
        r'\n'
        r'    print\(f"  → found \{len\(found\)\} wheel\(s\), installing\.\.\."\)\n'
        r'    cmd = \[sys\.executable, "-m", "pip", "install", "--quiet", "--no-input",\n'
        r'            "--disable-pip-version-check", \*\[str\(p\) for p in found\]\]\n'
        r'    proc = subprocess\.run\(cmd, capture_output=True, text=True\)\n'
        r'    if proc\.returncode != 0:\n'
        r'        print\(f"  bulk install failed: \{proc\.stderr\[-300:\]\}"\)\n'
        r'    print\(f"  ✓ installed \{len\(found\)\} duecare wheels"\)\n'
        r'    return len\(found\)\n',
        re.MULTILINE,
    )
    new_text = pattern.sub(
        '    # Wheels fallback removed 2026-05-11 (GitHub-only policy).\n'
        '    raise SystemExit("DueCare GitHub install failed - check Internet=ON in Kaggle settings")\n',
        text,
    )
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
        print(f'  + A-05: removed wheels fallback ({len(text) - len(new_text)} bytes)')
    else:
        print('  - A-05: pattern not matched, manual review needed')


def replace_install_function(folder: str, func_name: str) -> bool:
    """Generic: find install_<name>() function, replace body with GitHub-only call.
    Inject CANONICAL_INSTALL above the function.
    """
    path = ROOT / 'kaggle' / folder / 'kernel.py'
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    func_start = None
    for i, line in enumerate(lines):
        if line.startswith(f'def {func_name}('):
            func_start = i
            break
    if func_start is None:
        print(f'  - {folder}: def {func_name}() not found')
        return False
    func_end = func_start + 1
    for i in range(func_start + 1, len(lines)):
        line = lines[i]
        if line and not line.startswith((' ', '\t', '\n')):
            func_end = i
            break
    else:
        func_end = len(lines)

    new_func = (
        f'def {func_name}() -> int:\n'
        f'    """Install DueCare packages from GitHub. No Kaggle wheel datasets."""\n'
        f'    return 1 if install_duecare_from_github() else 0\n'
        f'\n'
        f'\n'
    )
    new_lines = lines[:func_start] + [CANONICAL_INSTALL.lstrip('\n'), '\n', new_func] + lines[func_end:]
    new_text = ''.join(new_lines)
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
        print(f'  + {folder}: replaced {func_name}() body with GitHub-only')
        return True
    return False


def fix_a10() -> None:
    """A-10 has top-level wheel install (not a function). Inject CANONICAL_INSTALL,
    replace the inline install block with a call to install_duecare_from_github()."""
    path = ROOT / 'kaggle/_archive/notebooks/A-10-runtime-vs-weights-safety-study/kernel.py'
    text = path.read_text(encoding='utf-8')
    idx = text.find('found = sorted(p for p in Path("/kaggle/input").rglob("*.whl")')
    if idx == -1:
        print('  - A-10: wheel install block not found')
        return
    end_marker = text.find('\nprint("[2/5]', idx)
    if end_marker == -1:
        end_marker = idx + 800
    start_marker = text.rfind('print(f"[1/5]', 0, idx)
    if start_marker == -1:
        start_marker = idx
    new_text = (
        text[:start_marker]
        + CANONICAL_INSTALL.lstrip('\n')
        + '\n\n'
        + 'print("[1/5] installing duecare from GitHub (no wheel dataset)")\n'
        + 'install_duecare_from_github()\n'
        + text[end_marker + 1:]
    )
    path.write_text(new_text, encoding='utf-8')
    print('  + A-10: replaced inline wheel block with GitHub-only')


def fix_a11() -> None:
    """A-11 uses pip install --no-index --find-links WHEELS_DIR. Replace with
    GitHub install."""
    path = ROOT / 'kaggle/_archive/notebooks/A-11-grading-evaluation/kernel.py'
    text = path.read_text(encoding='utf-8')
    wheels_dir_idx = text.find('WHEELS_DIR = "/kaggle/input/')
    if wheels_dir_idx == -1:
        print('  - A-11: WHEELS_DIR not found')
        return
    install_end_idx = text.find('print("[3/6]', wheels_dir_idx)
    if install_end_idx == -1:
        install_end_idx = text.find('print("[2/6]', wheels_dir_idx)
    if install_end_idx == -1:
        print('  - A-11: install block end marker not found')
        return
    new_text = (
        text[:wheels_dir_idx]
        + CANONICAL_INSTALL.lstrip('\n')
        + '\n\nprint("[1/6] installing duecare from GitHub (no wheel dataset)")\n'
        + 'install_duecare_from_github()\n\n'
        + text[install_end_idx:]
    )
    path.write_text(new_text, encoding='utf-8')
    print('  + A-11: replaced WHEELS_DIR install with GitHub-only')


if __name__ == '__main__':
    fix_a05()
    replace_install_function('A-06-prompt-generation', 'install_duecare_wheels')
    replace_install_function('A-07-bench-and-tune', 'install_duecare_wheels')
    replace_install_function('A-09-chat-playground-with-agentic-research', 'install_duecare_wheels')
    fix_a10()
    fix_a11()
    print('\nMigration script complete.')
