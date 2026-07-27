#!/usr/bin/env python3
"""Atomic provider-attempt, token, and cost budget ledger.

The ledger uses SQLite ``BEGIN IMMEDIATE`` transactions so concurrent threads
and processes cannot reserve the same remaining allowance. It stores provider
labels plus model/prompt SHA-256 values, never prompts, model text, keys, URLs,
or error messages. Reservations are conservative and are not refunded when a
provider attempt fails or is cancelled; retries therefore consume new call,
token, and cost allowance.

The environment integration is opt-in when any ``DUECARE_*BUDGET*`` or
``DUECARE_MAX_PLANNED_MODEL_CALLS`` setting is present. Setting the existing
planned-call ceiling to zero activates the ledger and blocks transport before a
request. Positive budgets require a stable run id and finite input/output/cash
limits. Pricing comes from an operator-reviewed JSON file; unknown pricing is
blocked unless an explicit override is recorded in the run policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "reports" / "provider_budget" / "provider_budget.sqlite3"
DEFAULT_RECEIPT = ROOT / "reports" / "provider_budget" / "provider_budget_receipt.json"
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
SCHEMA = "duecare.provider-budget.v1"


class BudgetError(RuntimeError):
    """Base class for provider budget failures."""


class BudgetConfigurationError(BudgetError):
    """The run budget is incomplete or internally inconsistent."""


class BudgetExceededError(BudgetError):
    """A provider attempt cannot fit inside the frozen run budget."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(f"provider budget exhausted: {category}")


@dataclass(frozen=True)
class BudgetPolicy:
    max_attempts: int
    max_input_tokens: int
    max_output_tokens: int
    max_cost_microusd: int
    allow_unknown_cost: bool = False

    def __post_init__(self) -> None:
        for name in (
            "max_attempts",
            "max_input_tokens",
            "max_output_tokens",
            "max_cost_microusd",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise BudgetConfigurationError(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class Pricing:
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    source_sha256: str

    def __post_init__(self) -> None:
        if (
            not self.input_usd_per_million.is_finite()
            or not self.output_usd_per_million.is_finite()
        ):
            raise BudgetConfigurationError("provider pricing must be finite")
        if self.input_usd_per_million < 0 or self.output_usd_per_million < 0:
            raise BudgetConfigurationError("provider pricing cannot be negative")
        if SHA256_RE.fullmatch(self.source_sha256) is None:
            raise BudgetConfigurationError("pricing source hash must be SHA-256")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Conservative deterministic estimate used only when exact usage is absent."""
    value = str(text or "")
    return max(1, math.ceil(len(value.encode("utf-8")) / 3))


def _microusd(value: str | Decimal | int | float) -> int:
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BudgetConfigurationError("cash budget must be a decimal USD value") from exc
    if not decimal.is_finite():
        raise BudgetConfigurationError("cash budget must be finite")
    if decimal < 0:
        raise BudgetConfigurationError("cash budget must be non-negative")
    return int((decimal * Decimal(1_000_000)).to_integral_value(rounding=ROUND_CEILING))


def _token_cost_microusd(input_tokens: int, output_tokens: int, pricing: Pricing) -> int:
    # USD / million tokens numerically equals micro-USD / token.
    cost = (
        Decimal(input_tokens) * pricing.input_usd_per_million
        + Decimal(output_tokens) * pricing.output_usd_per_million
    )
    return int(cost.to_integral_value(rounding=ROUND_CEILING))


def _safe_provider(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_.-]+", "-", str(value or "").lower()).strip("-")
    return cleaned[:64] or "unknown"


def _parse_limit(env: dict[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise BudgetConfigurationError(f"{name} must be an integer") from exc
    if value < 0:
        raise BudgetConfigurationError(f"{name} must be non-negative")
    return value


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _pricing_file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pricing(path: Path | None, provider: str, model: str) -> Pricing | None:
    """Load an exact or wildcard price from an operator-reviewed JSON file."""
    if path is None:
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BudgetConfigurationError("provider pricing file is unreadable") from exc
    if not isinstance(doc, dict) or doc.get("schema") != "duecare.provider-pricing.v1":
        raise BudgetConfigurationError("provider pricing file schema is invalid")
    prices = doc.get("prices")
    if not isinstance(prices, list):
        raise BudgetConfigurationError("provider pricing entries must be a list")
    provider_key = _safe_provider(provider)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for entry in prices:
        if (
            not isinstance(entry, dict)
            or _safe_provider(str(entry.get("provider"))) != provider_key
        ):
            continue
        entry_model = str(entry.get("model") or "")
        if entry_model == model:
            candidates.append((2, entry))
        elif entry_model == "*":
            candidates.append((1, entry))
    if not candidates:
        return None
    _, selected = max(candidates, key=lambda item: item[0])
    try:
        input_rate = Decimal(str(selected["input_usd_per_million_tokens"]))
        output_rate = Decimal(str(selected["output_usd_per_million_tokens"]))
    except (KeyError, InvalidOperation) as exc:
        raise BudgetConfigurationError("provider pricing entry is incomplete") from exc
    return Pricing(input_rate, output_rate, _pricing_file_sha(path))


def classify_error(exc: BaseException) -> str:
    """Return a sanitized retry/budget outcome class without error text."""
    code = getattr(exc, "code", None)
    if code == 401:
        return "authentication"
    if code == 402:
        return "payment_or_quota"
    if code == 403:
        return "permission"
    if code == 429:
        return "rate_limit"
    if isinstance(code, int) and 500 <= code <= 599:
        return "provider_service"
    if isinstance(code, int) and 400 <= code <= 499:
        return "invalid_request"
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return "transport"
    return "internal"


def usage_from_response(
    response: dict[str, Any] | None,
    *,
    reserved_input_tokens: int,
    output_text: str,
) -> tuple[int, int, str]:
    """Normalize OpenAI/Ollama/Anthropic usage without retaining response data."""
    usage = response.get("usage") if isinstance(response, dict) else None
    if isinstance(usage, dict):
        input_value = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_value = usage.get("completion_tokens", usage.get("output_tokens"))
        if (
            isinstance(input_value, int)
            and not isinstance(input_value, bool)
            and input_value >= 0
            and isinstance(output_value, int)
            and not isinstance(output_value, bool)
            and output_value >= 0
        ):
            return input_value, output_value, "provider"
    if isinstance(response, dict):
        input_value = response.get("prompt_eval_count")
        output_value = response.get("eval_count")
        if (
            isinstance(input_value, int)
            and not isinstance(input_value, bool)
            and input_value >= 0
            and isinstance(output_value, int)
            and not isinstance(output_value, bool)
            and output_value >= 0
        ):
            return input_value, output_value, "provider"
    return reserved_input_tokens, estimate_tokens(output_text), "estimated"


class DisabledBudgetAttempt:
    """No-op context used only when no budget environment is configured."""

    def __enter__(self) -> DisabledBudgetAttempt:
        return self

    def settle(self, **_: Any) -> None:
        return None

    def __exit__(self, *_: Any) -> bool:
        return False


class DisabledProviderBudget:
    enabled = False

    def attempt(self, **_: Any) -> DisabledBudgetAttempt:
        return DisabledBudgetAttempt()

    def receipt(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "enabled": False}


class BudgetAttempt:
    def __init__(
        self,
        ledger: ProviderBudgetLedger,
        attempt_id: str,
        reserved_input_tokens: int,
        reserved_output_tokens: int,
        pricing: Pricing | None,
    ) -> None:
        self.ledger = ledger
        self.attempt_id = attempt_id
        self.reserved_input_tokens = reserved_input_tokens
        self.reserved_output_tokens = reserved_output_tokens
        self.pricing = pricing
        self._finished = False

    def __enter__(self) -> BudgetAttempt:
        return self

    def settle(self, *, response: dict[str, Any] | None, output_text: str) -> None:
        if self._finished:
            raise BudgetError("provider attempt already finished")
        input_tokens, output_tokens, usage_source = usage_from_response(
            response,
            reserved_input_tokens=self.reserved_input_tokens,
            output_text=output_text,
        )
        self.ledger._finish(
            self.attempt_id,
            status="succeeded",
            outcome_class="success",
            actual_input_tokens=input_tokens,
            actual_output_tokens=output_tokens,
            usage_source=usage_source,
            pricing=self.pricing,
        )
        self._finished = True

    def __exit__(self, exc_type: Any, exc: BaseException | None, _: Any) -> bool:
        if self._finished:
            return False
        status = "cancelled" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed"
        self.ledger._finish(
            self.attempt_id,
            status=status,
            outcome_class=classify_error(exc) if exc is not None else "unsettled",
            actual_input_tokens=0,
            actual_output_tokens=0,
            usage_source="none",
            pricing=self.pricing,
        )
        self._finished = True
        return False


class ProviderBudgetLedger:
    enabled = True

    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        policy: BudgetPolicy,
        pricing_path: Path | None = None,
        receipt_path: Path | None = None,
    ) -> None:
        if RUN_ID_RE.fullmatch(run_id) is None:
            raise BudgetConfigurationError("run id must be a short non-sensitive slug")
        self.path = path.resolve()
        self.run_id = run_id
        self.policy = policy
        self.pricing_path = pricing_path.resolve() if pricing_path else None
        self.receipt_path = receipt_path.resolve() if receipt_path else None
        self._receipt_lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @classmethod
    def from_environment(
        cls,
        *,
        root: Path = ROOT,
        source: dict[str, str] | None = None,
    ) -> ProviderBudgetLedger | DisabledProviderBudget:
        env = dict(os.environ if source is None else source)
        watched = {
            "DUECARE_MAX_PLANNED_MODEL_CALLS",
            "DUECARE_MAX_INPUT_TOKENS",
            "DUECARE_MAX_OUTPUT_TOKENS",
            "DUECARE_MAX_PROVIDER_COST_USD",
            "DUECARE_PROVIDER_BUDGET_FILE",
            "DUECARE_PROVIDER_BUDGET_RECEIPT",
            "DUECARE_PROVIDER_RUN_ID",
            "DUECARE_PROVIDER_PRICING_FILE",
            "DUECARE_ALLOW_UNKNOWN_PROVIDER_COST",
        }
        if not any(name in env for name in watched):
            return DisabledProviderBudget()
        max_attempts = _parse_limit(env, "DUECARE_MAX_PLANNED_MODEL_CALLS", 0)
        policy = BudgetPolicy(
            max_attempts=max_attempts,
            max_input_tokens=_parse_limit(env, "DUECARE_MAX_INPUT_TOKENS", 0),
            max_output_tokens=_parse_limit(env, "DUECARE_MAX_OUTPUT_TOKENS", 0),
            max_cost_microusd=_microusd(env.get("DUECARE_MAX_PROVIDER_COST_USD", "0")),
            allow_unknown_cost=_truthy(env.get("DUECARE_ALLOW_UNKNOWN_PROVIDER_COST")),
        )
        run_id = env.get("DUECARE_PROVIDER_RUN_ID", "closeout-zero-call")
        if max_attempts > 0 and "DUECARE_PROVIDER_RUN_ID" not in env:
            raise BudgetConfigurationError("positive call budgets require DUECARE_PROVIDER_RUN_ID")
        if max_attempts > 0:
            required_limits = (
                "DUECARE_MAX_INPUT_TOKENS",
                "DUECARE_MAX_OUTPUT_TOKENS",
                "DUECARE_MAX_PROVIDER_COST_USD",
            )
            missing = [name for name in required_limits if name not in env]
            if missing:
                raise BudgetConfigurationError(
                    "positive call budgets require explicit finite input, output, and cash caps"
                )
        ledger_raw = env.get(
            "DUECARE_PROVIDER_BUDGET_FILE",
            "reports/provider_budget/provider_budget.sqlite3",
        )
        receipt_raw = env.get(
            "DUECARE_PROVIDER_BUDGET_RECEIPT",
            "reports/provider_budget/provider_budget_receipt.json",
        )
        pricing_raw = env.get("DUECARE_PROVIDER_PRICING_FILE")

        def resolve(value: str) -> Path:
            path = Path(value)
            return path if path.is_absolute() else root / path

        return cls(
            resolve(ledger_raw),
            run_id=run_id,
            policy=policy,
            pricing_path=resolve(pricing_raw) if pricing_raw else None,
            receipt_path=resolve(receipt_raw),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        policy_json = json.dumps(asdict(self.policy), sort_keys=True, separators=(",", ":"))
        policy_sha = _sha256_text(policy_json)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    policy_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    reserved_attempts INTEGER NOT NULL DEFAULT 0,
                    denied_attempts INTEGER NOT NULL DEFAULT 0,
                    reserved_input_tokens INTEGER NOT NULL DEFAULT 0,
                    reserved_output_tokens INTEGER NOT NULL DEFAULT 0,
                    reserved_cost_microusd INTEGER NOT NULL DEFAULT 0,
                    actual_input_tokens INTEGER NOT NULL DEFAULT 0,
                    actual_output_tokens INTEGER NOT NULL DEFAULT 0,
                    actual_cost_microusd INTEGER NOT NULL DEFAULT 0,
                    succeeded_attempts INTEGER NOT NULL DEFAULT 0,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    cancelled_attempts INTEGER NOT NULL DEFAULT 0,
                    unknown_cost_attempts INTEGER NOT NULL DEFAULT 0,
                    breached INTEGER NOT NULL DEFAULT 0,
                    last_denial_category TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    provider TEXT NOT NULL,
                    model_sha256 TEXT NOT NULL,
                    prompt_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reserved_input_tokens INTEGER NOT NULL,
                    reserved_output_tokens INTEGER NOT NULL,
                    reserved_cost_microusd INTEGER NOT NULL,
                    actual_input_tokens INTEGER NOT NULL DEFAULT 0,
                    actual_output_tokens INTEGER NOT NULL DEFAULT 0,
                    actual_cost_microusd INTEGER NOT NULL DEFAULT 0,
                    pricing_source_sha256 TEXT,
                    usage_source TEXT,
                    outcome_class TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    UNIQUE(run_id, sequence),
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                )
                """
            )
            row = connection.execute(
                "SELECT policy_sha256 FROM runs WHERE run_id = ?", (self.run_id,)
            ).fetchone()
            now = _utc_now()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO runs (
                        run_id, schema_version, policy_json, policy_sha256, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (self.run_id, SCHEMA, policy_json, policy_sha, now, now),
                )
            elif row["policy_sha256"] != policy_sha:
                connection.rollback()
                raise BudgetConfigurationError(
                    "run id already exists with a different frozen policy"
                )
            connection.commit()
        self._export_receipt_best_effort()

    def _deny(self, connection: sqlite3.Connection, category: str) -> None:
        connection.execute(
            """
            UPDATE runs SET denied_attempts = denied_attempts + 1,
                last_denial_category = ?, updated_at = ? WHERE run_id = ?
            """,
            (category, _utc_now(), self.run_id),
        )
        connection.commit()
        raise BudgetExceededError(category)

    @staticmethod
    def _would_exceed(current: int, requested: int, maximum: int) -> bool:
        return maximum >= 0 and current + requested > maximum

    def attempt(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        system: str | None,
        max_output_tokens: int,
        estimated_input_tokens: int | None = None,
    ) -> BudgetAttempt:
        if not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool):
            raise BudgetConfigurationError("max_output_tokens must be an integer")
        if max_output_tokens <= 0:
            raise BudgetConfigurationError("provider attempts require a finite positive output cap")
        reserved_input = (
            estimate_tokens(f"{system or ''}\n{prompt}")
            if estimated_input_tokens is None
            else estimated_input_tokens
        )
        if (
            not isinstance(reserved_input, int)
            or isinstance(reserved_input, bool)
            or reserved_input <= 0
        ):
            raise BudgetConfigurationError("estimated input tokens must be positive")
        provider_key = _safe_provider(provider)
        pricing = load_pricing(self.pricing_path, provider_key, model)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (self.run_id,)
            ).fetchone()
            if run is None:
                connection.rollback()
                raise BudgetError("provider budget run disappeared")
            if run["breached"]:
                self._deny(connection, "previous_actual_overrun")
            if self._would_exceed(run["reserved_attempts"], 1, self.policy.max_attempts):
                self._deny(connection, "attempts")
            if self._would_exceed(
                run["reserved_input_tokens"], reserved_input, self.policy.max_input_tokens
            ):
                self._deny(connection, "input_tokens")
            if self._would_exceed(
                run["reserved_output_tokens"], max_output_tokens, self.policy.max_output_tokens
            ):
                self._deny(connection, "output_tokens")
            unknown_cost = pricing is None
            if unknown_cost and not self.policy.allow_unknown_cost:
                connection.rollback()
                raise BudgetConfigurationError(
                    "provider/model pricing is unknown; supply a reviewed pricing file "
                    "or explicit override"
                )
            reserved_cost = (
                0
                if pricing is None
                else _token_cost_microusd(reserved_input, max_output_tokens, pricing)
            )
            if self._would_exceed(
                run["reserved_cost_microusd"], reserved_cost, self.policy.max_cost_microusd
            ):
                self._deny(connection, "cost")
            sequence = int(run["reserved_attempts"]) + 1
            attempt_id = f"{self.run_id}:{sequence:08d}"
            started_at = _utc_now()
            prompt_hash = _sha256_text(
                json.dumps({"system": system or "", "prompt": prompt}, sort_keys=True)
            )
            connection.execute(
                """
                INSERT INTO attempts (
                    attempt_id, run_id, sequence, provider, model_sha256, prompt_sha256,
                    status, reserved_input_tokens, reserved_output_tokens,
                    reserved_cost_microusd, pricing_source_sha256, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'reserved', ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    self.run_id,
                    sequence,
                    provider_key,
                    _sha256_text(model),
                    prompt_hash,
                    reserved_input,
                    max_output_tokens,
                    reserved_cost,
                    pricing.source_sha256 if pricing else None,
                    started_at,
                ),
            )
            connection.execute(
                """
                UPDATE runs SET reserved_attempts = reserved_attempts + 1,
                    reserved_input_tokens = reserved_input_tokens + ?,
                    reserved_output_tokens = reserved_output_tokens + ?,
                    reserved_cost_microusd = reserved_cost_microusd + ?,
                    unknown_cost_attempts = unknown_cost_attempts + ?,
                    updated_at = ? WHERE run_id = ?
                """,
                (
                    reserved_input,
                    max_output_tokens,
                    reserved_cost,
                    int(unknown_cost),
                    started_at,
                    self.run_id,
                ),
            )
            connection.commit()
        self._export_receipt_best_effort()
        return BudgetAttempt(self, attempt_id, reserved_input, max_output_tokens, pricing)

    def _finish(
        self,
        attempt_id: str,
        *,
        status: str,
        outcome_class: str,
        actual_input_tokens: int,
        actual_output_tokens: int,
        usage_source: str,
        pricing: Pricing | None,
    ) -> None:
        if status not in {"succeeded", "failed", "cancelled"}:
            raise BudgetError("invalid provider attempt status")
        actual_input_tokens = max(0, int(actual_input_tokens))
        actual_output_tokens = max(0, int(actual_output_tokens))
        actual_cost = (
            0
            if pricing is None
            else _token_cost_microusd(actual_input_tokens, actual_output_tokens, pricing)
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            attempt = connection.execute(
                "SELECT * FROM attempts WHERE attempt_id = ? AND run_id = ?",
                (attempt_id, self.run_id),
            ).fetchone()
            if attempt is None or attempt["status"] != "reserved":
                connection.rollback()
                raise BudgetError("provider attempt is missing or already finished")
            run = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (self.run_id,)
            ).fetchone()
            if run is None:
                connection.rollback()
                raise BudgetError("provider budget run disappeared")
            projected_input = run["actual_input_tokens"] + actual_input_tokens
            projected_output = run["actual_output_tokens"] + actual_output_tokens
            projected_cost = run["actual_cost_microusd"] + actual_cost
            breached = (
                actual_input_tokens > attempt["reserved_input_tokens"]
                or actual_output_tokens > attempt["reserved_output_tokens"]
                or self._would_exceed(0, projected_input, self.policy.max_input_tokens)
                or self._would_exceed(0, projected_output, self.policy.max_output_tokens)
                or self._would_exceed(0, projected_cost, self.policy.max_cost_microusd)
            )
            connection.execute(
                """
                UPDATE attempts SET status = ?, actual_input_tokens = ?,
                    actual_output_tokens = ?, actual_cost_microusd = ?, usage_source = ?,
                    outcome_class = ?, finished_at = ? WHERE attempt_id = ?
                """,
                (
                    status,
                    actual_input_tokens,
                    actual_output_tokens,
                    actual_cost,
                    usage_source,
                    _safe_provider(outcome_class),
                    _utc_now(),
                    attempt_id,
                ),
            )
            counter = {
                "succeeded": "succeeded_attempts",
                "failed": "failed_attempts",
                "cancelled": "cancelled_attempts",
            }[status]
            connection.execute(
                f"""
                UPDATE runs SET {counter} = {counter} + 1,
                    actual_input_tokens = actual_input_tokens + ?,
                    actual_output_tokens = actual_output_tokens + ?,
                    actual_cost_microusd = actual_cost_microusd + ?,
                    breached = MAX(breached, ?), updated_at = ? WHERE run_id = ?
                """,
                (
                    actual_input_tokens,
                    actual_output_tokens,
                    actual_cost,
                    int(breached),
                    _utc_now(),
                    self.run_id,
                ),
            )
            connection.commit()
        self._export_receipt_best_effort()

    def receipt(self, *, recent_limit: int = 100) -> dict[str, Any]:
        with self._connect() as connection:
            run = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?", (self.run_id,)
            ).fetchone()
            if run is None:
                raise BudgetError("provider budget run disappeared")
            attempts = connection.execute(
                """
                SELECT attempt_id, sequence, provider, model_sha256, prompt_sha256, status,
                    reserved_input_tokens, reserved_output_tokens, reserved_cost_microusd,
                    actual_input_tokens, actual_output_tokens, actual_cost_microusd,
                    pricing_source_sha256, usage_source, outcome_class, started_at, finished_at
                FROM attempts WHERE run_id = ? ORDER BY sequence DESC LIMIT ?
                """,
                (self.run_id, recent_limit),
            ).fetchall()
        policy = json.loads(run["policy_json"])
        return {
            "schema": SCHEMA,
            "enabled": True,
            "run_id": self.run_id,
            "ledger_file": self.path.name,
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "policy": policy,
            "totals": {
                key: run[key]
                for key in (
                    "reserved_attempts",
                    "denied_attempts",
                    "reserved_input_tokens",
                    "reserved_output_tokens",
                    "reserved_cost_microusd",
                    "actual_input_tokens",
                    "actual_output_tokens",
                    "actual_cost_microusd",
                    "succeeded_attempts",
                    "failed_attempts",
                    "cancelled_attempts",
                    "unknown_cost_attempts",
                    "breached",
                    "last_denial_category",
                )
            },
            "recent_attempts": [dict(attempt) for attempt in reversed(attempts)],
            "privacy": {
                "contains_prompts": False,
                "contains_responses": False,
                "contains_keys": False,
                "contains_urls": False,
                "model_ids_are_hashed": True,
            },
        }

    def export_receipt(self, path: Path | None = None) -> Path:
        destination = path or self.receipt_path
        if destination is None:
            raise BudgetConfigurationError("no provider budget receipt path configured")
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(self.receipt(), indent=2, sort_keys=True) + "\n"
        with self._receipt_lock:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                delete=False,
            ) as handle:
                handle.write(serialized)
                temporary = Path(handle.name)
            os.replace(temporary, destination)
        return destination

    def _export_receipt_best_effort(self) -> None:
        if self.receipt_path is None:
            return
        try:
            self.export_receipt()
        except (OSError, sqlite3.Error):
            # The SQLite transaction is authoritative. A transient receipt
            # export error must never roll back or duplicate a provider call.
            return


_ENV_LEDGER: ProviderBudgetLedger | DisabledProviderBudget | None = None
_ENV_LEDGER_LOCK = threading.Lock()


def environment_ledger() -> ProviderBudgetLedger | DisabledProviderBudget:
    global _ENV_LEDGER
    if _ENV_LEDGER is None:
        with _ENV_LEDGER_LOCK:
            if _ENV_LEDGER is None:
                _ENV_LEDGER = ProviderBudgetLedger.from_environment()
    return _ENV_LEDGER


def reset_environment_ledger_for_tests() -> None:
    global _ENV_LEDGER
    with _ENV_LEDGER_LOCK:
        _ENV_LEDGER = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the sanitized receipt")
    parser.add_argument("--receipt", type=Path, help="also export a sanitized JSON receipt")
    args = parser.parse_args(argv)
    try:
        ledger = ProviderBudgetLedger.from_environment()
        receipt = ledger.receipt()
        if args.receipt and isinstance(ledger, ProviderBudgetLedger):
            ledger.export_receipt(args.receipt)
    except BudgetError as exc:
        print(f"[provider-budget] FAIL: {exc}")
        return 1
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        totals = receipt.get("totals") or {}
        print(
            "[provider-budget] "
            f"enabled={str(receipt.get('enabled')).lower()} "
            f"attempts={totals.get('reserved_attempts', 0)} "
            f"denied={totals.get('denied_attempts', 0)} "
            f"breached={totals.get('breached', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
