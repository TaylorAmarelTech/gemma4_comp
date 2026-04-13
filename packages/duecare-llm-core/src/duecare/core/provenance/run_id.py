"""run_id generation. Format: YYYYMMDDHHMMSSffffff_{short_sha}_{workflow_id}.

Microsecond precision ensures that back-to-back runs (e.g., cross-domain
benchmarks that loop over 3 domains in the same second) get distinct
ids. The timestamp + short SHA combination is still stable, sortable,
and greppable.
"""

from __future__ import annotations

from datetime import datetime

from .git import get_short_sha


def generate_run_id(workflow_id: str) -> str:
    """Stable, sortable, greppable run id with microsecond precision."""
    ts = datetime.now().strftime("%Y%m%d%H%M%S%f")
    sha = get_short_sha()
    safe_workflow = workflow_id.replace("/", "_").replace(" ", "_")
    return f"{ts}_{sha}_{safe_workflow}"
