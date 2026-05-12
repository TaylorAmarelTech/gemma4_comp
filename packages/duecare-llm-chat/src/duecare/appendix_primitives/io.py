"""Write / read the v1.0 four-file bundle.

A bundle is the unit consumed by Add Data when crossing kernels.
Layout (4 files per RunID):

* ``<RUN_ID>_results.json`` -- the full BundleEnvelope as JSON
* ``<RUN_ID>_run.jsonl`` -- streaming variant, one PerRow per line
* ``<RUN_ID>_metadata.json`` -- BundleEnvelope minus ``results[]``
* ``<RUN_ID>_bundle.zip`` -- zip of the above + ``manifest.json``

See docs/data_primitives.md section 1.7.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from duecare.appendix_primitives.envelopes import BundleEnvelope


def _sha256_file(p: Path) -> str:
    """Return the SHA-256 hex digest of file p."""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def write_v1_bundle(
    envelope: BundleEnvelope,
    output_dir: Path,
) -> dict[str, Any]:
    """Write the 4-file v1.0 bundle to output_dir.

    Args:
        envelope: a validated BundleEnvelope.
        output_dir: existing directory (typically ``/kaggle/working/``).

    Returns:
        Dict with absolute Paths for ``results_json``, ``run_jsonl``,
        ``metadata_json``, ``bundle_zip``, plus the ``manifest`` dict.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = envelope.run_id

    results_path = output_dir / f"{run_id}_results.json"
    jsonl_path = output_dir / f"{run_id}_run.jsonl"
    metadata_path = output_dir / f"{run_id}_metadata.json"
    bundle_path = output_dir / f"{run_id}_bundle.zip"

    full = envelope.model_dump(mode="json")
    results_path.write_text(
        json.dumps(full, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    metadata_only = {k: v for k, v in full.items() if k != "results"}
    metadata_path.write_text(
        json.dumps(metadata_only, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for row in full["results"]:
            line = {
                "schema_version": "1.0",
                "run_id": run_id,
                "kernel_id": envelope.kernel_id,
                **row,
            }
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "run_id": run_id,
        "kernel_id": envelope.kernel_id,
        "files": ["results.json", "run.jsonl", "metadata.json"],
        "checksums": {
            "results.json": _sha256_file(results_path),
            "run.jsonl": _sha256_file(jsonl_path),
            "metadata.json": _sha256_file(metadata_path),
        },
    }
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.write(results_path, "results.json")
        zf.write(jsonl_path, "run.jsonl")
        zf.write(metadata_path, "metadata.json")

    return {
        "results_json": results_path,
        "run_jsonl": jsonl_path,
        "metadata_json": metadata_path,
        "bundle_zip": bundle_path,
        "manifest": manifest,
    }


def read_v1_bundle(bundle_zip: Path) -> BundleEnvelope:
    """Read a bundle.zip and return a validated BundleEnvelope.

    Args:
        bundle_zip: path to a v1.0 bundle ``.zip``.

    Raises:
        ValueError: when the manifest's schema_version is not '1.0'.
    """
    bundle_zip = Path(bundle_zip)
    with zipfile.ZipFile(bundle_zip, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        if manifest.get("schema_version") != "1.0":
            raise ValueError(
                "unsupported bundle schema_version: "
                f"{manifest.get('schema_version')!r}"
            )
        payload = json.loads(zf.read("results.json").decode("utf-8"))
    return BundleEnvelope.model_validate(payload)
