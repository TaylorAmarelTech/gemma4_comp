"""Classifier protocol. See docs/architecture.md section 6.2."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.items import ClassifiedItem, StagingItem


@runtime_checkable
class Classifier(Protocol):
    """Assigns labels to a StagingItem, producing a ClassifiedItem.

    Classifiers must populate `classifier_confidence` with a per-label
    confidence score. If the classifier abstains on a label, it should
    leave the field as None (or empty list) and record a zero confidence.
    A classifier must never silently drop an item.
    """

    name: str
    version: str

    def classify(self, item: StagingItem) -> ClassifiedItem:
        ...
