"""Provenance - full traceability for any record in a Duecare run."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    """Full traceability for any record produced in a Duecare run.

    Every record in the pipeline carries one of these. The pipeline refuses
    to write a record without a populated Provenance.
    """

    source_id: str = ""                 # which Source connector produced this
    source_row_id: str = ""             # primary key inside that source
    run_id: str
    git_sha: str
    workflow_id: str
    agent_id: str | None = None
    target_model_id: str | None = None
    domain_id: str | None = None
    ingested_at: datetime | None = None
    created_at: datetime
    ingestion_script_version: str = ""
    classifier_versions: dict[str, str] = Field(default_factory=dict)
    anonymizer_version: str | None = None
    anonymizer_actions: list[str] = Field(default_factory=list)
    parent_record_id: str | None = None
    split: str | None = None            # train / val / test / holdout
    checksum: str
