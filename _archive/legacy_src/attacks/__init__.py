"""Adversarial harness. See docs/architecture.md section 9."""

from .base import BaseAttackStrategy
from .registry import AttackRegistry

__all__ = ["BaseAttackStrategy", "AttackRegistry"]
