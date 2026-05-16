# Legacy Research Archive - 2026-05-09

This archive contains legacy research notebooks and experimental content that were moved out of the main project to focus on the **Gemma 4 Good Hackathon submission**.

## What's here

- **`legacy_notebooks/`** - 66 research notebooks from the original development phase
- **`skunkworks/`** - 11 experimental notebooks and research files

## Why moved

- **Context reduction**: Focus main project on 13 submission notebooks (2 core + 11 appendix)
- **Submission clarity**: Keep only hackathon-relevant content in main directory
- **Performance**: Reduce project size for better Claude Code session performance

## Submission components (remaining in main project)

- `kaggle/01-duecare-harness-chat/` - Core omni playground
- `kaggle/02-live-demo/` - Core live demo
- `kaggle/A-01-*` through `kaggle/A-11-*` - Appendix notebooks

## How to restore (if needed)

```bash
# From project root
cp -r _archive/legacy-research-2026-05-09/legacy_notebooks/ ./
cp -r _archive/legacy-research-2026-05-09/skunkworks/ ./
```

## Note

The build scripts in `scripts/` that reference `legacy_notebooks/` are preserved but may not be needed for the final submission workflow since the submission notebooks in `kaggle/` are independently maintained.
