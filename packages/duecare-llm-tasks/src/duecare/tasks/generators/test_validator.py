"""Prompt/test validation module.

Validates that generated prompts meet quality criteria before
they enter the evaluation pipeline. Catches:
  - Too short/long prompts
  - Missing required fields
  - Duplicate or near-duplicate content
  - Invalid categories
  - Prompts that don't test exploitation scenarios
  - Prompts with PII that should have been anonymized

Usage:
    from duecare.tasks.generators.test_validator import PromptValidator

    validator = PromptValidator()
    report = validator.validate_batch(prompts)
    valid_prompts = report.valid_prompts
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Result of validating a single prompt."""

    prompt_id: str
    valid: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Summary of batch validation."""

    total: int
    valid_count: int
    invalid_count: int
    warning_count: int
    issues_by_type: dict[str, int] = Field(default_factory=dict)
    valid_prompts: list[dict] = Field(default_factory=list)
    invalid_prompts: list[dict] = Field(default_factory=list)
    results: list[ValidationResult] = Field(default_factory=list)


VALID_CATEGORIES = {
    "business_framed_exploitation",
    "jurisdictional_hierarchy_exploitation",
    "financial_crime_blindness",
    "prompt_injection_amplification",
    "victim_revictimization",
    "labor_trafficking",
    "adversarial",
    "corridor_specific",
    "unknown",
}

PII_PATTERNS = [
    re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),  # Phone numbers
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
    re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),  # Passport numbers
    re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),  # Credit cards
]

EXPLOITATION_KEYWORDS = [
    "fee", "recruitment", "placement", "salary", "deduction", "passport",
    "contract", "worker", "domestic", "agency", "employer", "wage",
    "trafficking", "exploitation", "forced", "labor", "bondage", "debt",
    "migrant", "overseas", "kafala", "poea", "ilo",
]


class PromptValidator:
    """Validate prompt quality before evaluation."""

    def __init__(
        self,
        *,
        min_length: int = 20,
        max_length: int = 10000,
        require_exploitation_keywords: bool = True,
        check_pii: bool = True,
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        self.require_exploitation_keywords = require_exploitation_keywords
        self.check_pii = check_pii

    def validate_prompt(self, prompt: dict[str, Any]) -> ValidationResult:
        """Validate a single prompt."""
        issues: list[str] = []
        warnings: list[str] = []
        pid = prompt.get("id", "unknown")
        text = prompt.get("text", "")

        # Required fields
        if not text:
            issues.append("missing_text")
        if not prompt.get("id"):
            warnings.append("missing_id")
        if not prompt.get("category"):
            warnings.append("missing_category")

        # Length checks
        if text and len(text) < self.min_length:
            issues.append(f"too_short ({len(text)} chars, min={self.min_length})")
        if text and len(text) > self.max_length:
            issues.append(f"too_long ({len(text)} chars, max={self.max_length})")

        # Category validation
        category = prompt.get("category", "")
        if category and category not in VALID_CATEGORIES:
            warnings.append(f"unknown_category: {category}")

        # Exploitation keyword check
        if self.require_exploitation_keywords and text:
            text_lower = text.lower()
            has_keyword = any(kw in text_lower for kw in EXPLOITATION_KEYWORDS)
            if not has_keyword:
                warnings.append("no_exploitation_keywords")

        # PII check
        if self.check_pii and text:
            for pattern in PII_PATTERNS:
                if pattern.search(text):
                    issues.append("contains_pii")
                    break

        # Graded response validation
        graded = prompt.get("graded_responses")
        if graded:
            if "best" not in graded and "good" not in graded:
                warnings.append("graded_responses_missing_best_or_good")

        return ValidationResult(
            prompt_id=pid,
            valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )

    def validate_batch(self, prompts: list[dict[str, Any]]) -> ValidationReport:
        """Validate a batch of prompts and return a report."""
        results = []
        valid_prompts = []
        invalid_prompts = []
        issues_counter: dict[str, int] = {}

        # Dedup check
        seen_hashes: set[str] = set()

        for prompt in prompts:
            result = self.validate_prompt(prompt)

            # Check for duplicates
            text = prompt.get("text", "")
            text_hash = hashlib.md5(text[:200].lower().encode()).hexdigest()
            if text_hash in seen_hashes:
                result.issues.append("duplicate")
                result.valid = False
            seen_hashes.add(text_hash)

            results.append(result)

            if result.valid:
                valid_prompts.append(prompt)
            else:
                invalid_prompts.append(prompt)

            for issue in result.issues:
                issue_type = issue.split("(")[0].strip()
                issues_counter[issue_type] = issues_counter.get(issue_type, 0) + 1

        warning_count = sum(len(r.warnings) for r in results)

        return ValidationReport(
            total=len(prompts),
            valid_count=len(valid_prompts),
            invalid_count=len(invalid_prompts),
            warning_count=warning_count,
            issues_by_type=issues_counter,
            valid_prompts=valid_prompts,
            invalid_prompts=invalid_prompts,
            results=results,
        )
