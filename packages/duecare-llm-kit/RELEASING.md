# Releasing `duecare-llm-kit` to PyPI

This is the "download and reuse" unlock: after this, anyone can
`pip install duecare-llm-kit` and import the DueCare ILO indicator engine,
the chart helpers, the HTML report generator, the corpus exporter, and the
deterministic `verify()` checker — the exact code embedded in the DueCare
Kaggle notebooks, now importable.

## Verified locally (2026-07-21)

All steps below were run and PASS from the clean uv-managed venv
(`scripts/recover_test_env.ps1`); the wheel installs into a throwaway venv
with no source on the path:

| Check | Result |
|---|---|
| `python -m build` (wheel + sdist) | Successfully built `duecare_llm_kit-0.1.0-py3-none-any.whl` + `.tar.gz` |
| `python -m twine check dist/*` | both **PASSED** |
| cleanroom `pip install dist/*.whl` | installs with numpy/pandas/matplotlib/Jinja2 |
| `import duecare.kit` | version `0.1.0` |
| `duecare.kit.engine.scan(...)` | 12 ILO indicators; 3 hits on the smoke prompt |
| `duecare.kit.verify.verify(...)` | 5/5 criteria on the strong-response smoke |
| `duecare-kit-report --help` / `duecare-kit-corpus --help` | both entry points resolve |

## The one manual step (needs a PyPI token)

`twine upload` is an irreversible public action, so it is left to Taylor —
the same manual-publish boundary as Kaggle. When ready:

```bash
# from packages/duecare-llm-kit/
PY="$LOCALAPPDATA/gemma4-testenv/venv/Scripts/python.exe"   # or any 3.11+ python

# 1. (re)build from a clean tree
"$PY" -m build

# 2. re-validate
"$PY" -m twine check dist/*

# 3. OPTIONAL dry run against TestPyPI first
"$PY" -m twine upload --repository testpypi dist/*
#    then: pip install -i https://test.pypi.org/simple/ duecare-llm-kit

# 4. real upload (uses ~/.pypirc or TWINE_USERNAME=__token__ TWINE_PASSWORD=<pypi-token>)
"$PY" -m twine upload dist/*
```

## After upload

1. Tag the release: `git tag kit-v0.1.0 && git push origin kit-v0.1.0`.
2. Update the notebooks' "run it yourself" cells to prefer the published
   package: `pip install duecare-llm-kit` (they already fall back to the
   embedded copy, so no notebook breaks before or after upload).
3. Update `docs/ROADMAP.md` item 2 and the website `/kernels` + `/data`
   copy to say "`pip install duecare-llm-kit`" as a live instruction.
4. Bump `version` in `pyproject.toml` for the next cycle (semver).

## Notes

- `dist/` and `build/` are gitignored — never commit the wheels.
- Optional extras: `pip install duecare-llm-kit[viz]` (seaborn/plotly/scipy),
  `[nlp]` (scikit-learn/vaderSentiment/textstat), `[all]`. The core helpers
  fall back to matplotlib and stdlib, so the base install stays light.
- The package is PEP 420 namespace (`duecare.kit`) and shares the `duecare`
  import namespace with the workspace packages without colliding.
