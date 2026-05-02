"""Active learning queue. Low-confidence labels go in -> human review
comes out. Reviewed items are immediately promoted to high-confidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from duecare.training.schema import ensure_tables


@dataclass
class ReviewItem:
    example_id: str
    target_kind: str
    target_id: str
    input_text: str
    proposed_label: str
    confidence: float
    source_strategy: str
    image_path: Optional[str] = None


class ReviewQueue:
    """CRUD over the labeled_examples table for human-in-the-loop
    review."""

    def __init__(self, store) -> None:
        self.store = store
        ensure_tables(self.store)

    def queue_size(self) -> int:
        r = self.store.fetchone(
            "SELECT COUNT(*) AS n FROM labeled_examples "
            "WHERE review_status = 'pending_review'")
        return int(r["n"]) if r else 0

    def stats(self) -> dict:
        rows = self.store.fetchall(
            "SELECT review_status, COUNT(*) AS n "
            "FROM labeled_examples GROUP BY review_status")
        out = {"auto": 0, "pending_review": 0,
               "human_approved": 0, "human_rejected": 0}
        for r in rows:
            out[r["review_status"]] = int(r["n"])
        out["total"] = sum(out.values())
        return out

    def next_item(self) -> Optional[ReviewItem]:
        """Pop the lowest-confidence pending_review item."""
        r = self.store.fetchone(
            "SELECT example_id, target_kind, target_id, input_text, "
            "label, confidence, source_strategy, input_image_path "
            "FROM labeled_examples "
            "WHERE review_status = 'pending_review' "
            "ORDER BY confidence ASC, created_at ASC LIMIT 1")
        if not r:
            return None
        return ReviewItem(
            example_id=r["example_id"],
            target_kind=r["target_kind"],
            target_id=r["target_id"],
            input_text=r["input_text"],
            proposed_label=r["label"],
            confidence=float(r["confidence"] or 0),
            source_strategy=r["source_strategy"],
            image_path=r.get("input_image_path") or None,
        )

    def approve(self, example_id: str,
                  notes: str = "") -> None:
        """Promote an item: status -> human_approved, confidence -> 1.0."""
        self.store.execute(
            "UPDATE labeled_examples SET review_status = ?, "
            "confidence = ?, review_notes = ?, reviewed_at = ? "
            "WHERE example_id = ?",
            ("human_approved", 1.0, notes, datetime.now(), example_id))

    def reject(self, example_id: str, notes: str = "") -> None:
        self.store.execute(
            "UPDATE labeled_examples SET review_status = ?, "
            "confidence = ?, review_notes = ?, reviewed_at = ? "
            "WHERE example_id = ?",
            ("human_rejected", 0.0, notes, datetime.now(), example_id))

    def relabel(self, example_id: str, new_label: str,
                  notes: str = "") -> None:
        """Human disagrees with the proposed label; assign a new one."""
        self.store.execute(
            "UPDATE labeled_examples SET review_status = ?, "
            "label = ?, confidence = ?, review_notes = ?, "
            "reviewed_at = ? WHERE example_id = ?",
            ("human_approved", new_label, 1.0, notes,
             datetime.now(), example_id))
