"""Bundled sample data accessor."""
from __future__ import annotations

from pathlib import Path


def path() -> Path:
    """Return the path to the bundled sample data directory."""
    return Path(__file__).parent


def copy_to(dest: str | Path) -> Path:
    """Copy sample_data/<bundle>/<file> tree to dest. Returns dest."""
    import shutil
    src = path()
    dst = Path(dest)
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in ("__init__.py", "README.md", "__pycache__"):
            continue
        target = dst / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    return dst
