# ruff: noqa: E501
"""DueCare corpus exporter -- bundle dataset files into a reusable, downloadable corpus folder.

``export_corpus`` copies a set of dataset files into an output folder and writes a machine-readable
``MANIFEST.json`` (per file: name, rows, columns, sha256, byte size, license, one-line description) plus
a human-readable ``README.md`` table. The result is a self-describing, versionable corpus bundle anyone
can download and reuse -- the "data corpuses" half of moving DueCare artifacts out of Kaggle cells and
into GitHub.

    >>> from duecare.kit.corpus import export_corpus, describe
    >>> export_corpus("corpus_out", ["reports/rich_lift/panel.jsonl"])

CLI:  python -m duecare.kit.corpus --out corpus_out --sources reports/rich_lift/panel.jsonl

ASCII-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

_TABULAR = {".csv", ".jsonl", ".ndjson", ".json", ".parquet", ".tsv"}
_CHUNK = 1 << 20  # 1 MiB streaming hash chunk


def describe(df: pd.DataFrame) -> dict:
    """Return a compact schema description of a DataFrame.

    Returns ``{"n_rows", "n_columns", "columns" {name: dtype}, "null_rates" {name: fraction}}``.
    """
    n = int(len(df))
    columns = {str(c): str(df[c].dtype) for c in df.columns}
    null_rates = {
        str(c): (round(float(df[c].isna().mean()), 4) if n else 0.0)
        for c in df.columns
    }
    return {"n_rows": n, "n_columns": int(df.shape[1]), "columns": columns, "null_rates": null_rates}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_table(path: Path) -> pd.DataFrame | None:
    """Best-effort load of a tabular file into a DataFrame; None when not tabular/parseable."""
    suffix = path.suffix.lower()
    try:
        if suffix in (".jsonl", ".ndjson"):
            return pd.read_json(path, lines=True)
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return pd.DataFrame(data)
            for key in ("rows", "data", "prompts", "records"):
                if isinstance(data.get(key), list):
                    return pd.DataFrame(data[key])
            return None
        if suffix == ".tsv":
            return pd.read_csv(path, sep="\t")
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix == ".parquet":
            return pd.read_parquet(path)
    except Exception:
        return None
    return None


def _count_lines(path: Path) -> int:
    n = 0
    with path.open("rb") as fh:
        for _ in fh:
            n += 1
    return n


def _profile(path: Path) -> dict:
    """Profile a single source file: rows, columns, schema, and a derived one-line description."""
    df = _read_table(path)
    if df is not None:
        desc = describe(df)
        return {
            "rows": desc["n_rows"],
            "columns": list(desc["columns"].keys()),
            "schema": desc["columns"],
            "null_rates": desc["null_rates"],
            "kind": "tabular",
        }
    # Non-tabular: count lines as rows, no columns.
    return {"rows": _count_lines(path), "columns": [], "schema": {}, "null_rates": {}, "kind": "text"}


def _default_description(name: str, profile: dict) -> str:
    if profile["kind"] == "tabular":
        return f"Tabular dataset with {profile['rows']:,} rows and {len(profile['columns'])} columns."
    return f"Text dataset with {profile['rows']:,} lines."


def export_corpus(out_dir: str | Path, sources: list[str | Path], *,
                  corpus_name: str = "DueCare corpus",
                  licenses: dict[str, str] | None = None,
                  descriptions: dict[str, str] | None = None,
                  default_license: str = "See source repository (DueCare: MIT for code; data licenses vary per source)") -> Path:
    """Copy dataset files into ``out_dir`` and write a MANIFEST.json + README.md corpus bundle.

    Args:
        out_dir: destination folder (created; a ``data/`` subfolder holds the copied files).
        sources: list of dataset file paths to include.
        corpus_name: display name recorded in the manifest and README.
        licenses: optional {filename: license string} overrides (keyed by the file's base name).
        descriptions: optional {filename: one-line description} overrides (keyed by base name).
        default_license: license string used when a file has no explicit override.

    Returns:
        The ``out_dir`` Path.

    Raises:
        FileNotFoundError: if a listed source file does not exist.
    """
    out = Path(out_dir)
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    licenses = licenses or {}
    descriptions = descriptions or {}

    entries: list[dict] = []
    for src in sources:
        src_path = Path(src)
        if not src_path.exists():
            raise FileNotFoundError(f"source not found: {src_path}")
        name = src_path.name
        dest = data_dir / name
        shutil.copy2(src_path, dest)
        profile = _profile(dest)
        entries.append({
            "name": name,
            "rows": profile["rows"],
            "columns": profile["columns"],
            "schema": profile["schema"],
            "null_rates": profile["null_rates"],
            "sha256": _sha256(dest),
            "bytes": dest.stat().st_size,
            "license": licenses.get(name, default_license),
            "description": descriptions.get(name, _default_description(name, profile)),
            "source": str(src_path),
        })

    generated = datetime.now(UTC).isoformat(timespec="seconds")
    manifest = {
        "corpus": corpus_name,
        "generated": generated,
        "n_files": len(entries),
        "total_rows": sum(e["rows"] for e in entries),
        "total_bytes": sum(e["bytes"] for e in entries),
        "files": entries,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / "README.md").write_text(_render_readme(manifest), encoding="utf-8")
    return out


def _render_readme(manifest: dict) -> str:
    lines = [
        f"# {manifest['corpus']}",
        "",
        f"Generated {manifest['generated']} by `duecare.kit.corpus`. "
        f"{manifest['n_files']} file(s), {manifest['total_rows']:,} total rows, "
        f"{manifest['total_bytes']:,} bytes.",
        "",
        "A self-describing, downloadable data corpus bundle. Every file is copied under `data/`, "
        "hashed (sha256), and profiled below. `MANIFEST.json` holds the machine-readable version.",
        "",
        "## Files",
        "",
        "| file | rows | columns | bytes | sha256 (first 12) | license |",
        "|---|---:|---:|---:|---|---|",
    ]
    for e in manifest["files"]:
        lines.append(
            f"| `data/{e['name']}` | {e['rows']:,} | {len(e['columns'])} | {e['bytes']:,} | "
            f"`{e['sha256'][:12]}` | {e['license']} |"
        )
    lines.append("")
    lines.append("## Descriptions")
    lines.append("")
    for e in manifest["files"]:
        lines.append(f"- **`{e['name']}`** -- {e['description']}")
        if e["columns"]:
            lines.append(f"  - columns: {', '.join('`' + c + '`' for c in e['columns'])}")
    lines.append("")
    lines.append("_Bundle produced with the DueCare kit (see its README for the current source install). "
                 "Reproduce with `python -m duecare.kit.corpus --out <dir> --sources <files...>`._")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export dataset files into a self-describing corpus bundle.")
    ap.add_argument("--out", required=True, type=Path, help="output corpus folder")
    ap.add_argument("--sources", required=True, nargs="+", type=Path, help="dataset files to include")
    ap.add_argument("--name", default="DueCare corpus", help="corpus display name")
    args = ap.parse_args(argv)
    out = export_corpus(args.out, args.sources, corpus_name=args.name)
    manifest = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    print(f"wrote corpus {out} -- {manifest['n_files']} file(s), "
          f"{manifest['total_rows']:,} rows, {manifest['total_bytes']:,} bytes")
    return 0


__all__ = ["export_corpus", "describe"]


if __name__ == "__main__":
    raise SystemExit(main())
