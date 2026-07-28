#!/usr/bin/env python3
"""Verify the exact provider transports covered by the shared budget ledger."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts" / "llm_generate.py"
DIRECT_CLIENT = ROOT / "scripts" / "adverse_media.py"
MODEL_FAILURE_CLIENT = ROOT / "scripts" / "model_failure_study.py"
MODEL_FAILURE_JUDGE_CLIENT = ROOT / "scripts" / "model_failure_judge.py"
PRIMARY_FUNCTIONS = {
    "ollama_chat",
    "nvidia_chat",
    "openai_compatible_chat",
    "anthropic_chat",
}
DIRECT_FUNCTIONS = {"_adverse_media_model_completion"}
MODEL_FAILURE_FUNCTIONS = {"call_chat"}
MODEL_FAILURE_JUDGE_FUNCTIONS = {"call_judge"}


@dataclass(frozen=True)
class TransportCall:
    function: str
    line: int
    reserved: bool


def _call_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


class CoverageVisitor(ast.NodeVisitor):
    def __init__(
        self,
        *,
        transport_name: str,
        guard_name: str,
        included_functions: set[str] | None = None,
    ) -> None:
        self.transport_name = transport_name
        self.guard_name = guard_name
        self.included_functions = included_functions
        self.function_stack: list[str] = []
        self.reservation_depth = 0
        self.calls: list[TransportCall] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_With(self, node: ast.With) -> None:
        guarded = any(_call_name(item.context_expr) == self.guard_name for item in node.items)
        if guarded:
            self.reservation_depth += 1
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self.visit(item.optional_vars)
        for statement in node.body:
            self.visit(statement)
        if guarded:
            self.reservation_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        function = self.function_stack[-1] if self.function_stack else "<module>"
        included = self.included_functions is None or function in self.included_functions
        if _call_name(node) == self.transport_name and included:
            self.calls.append(TransportCall(function, node.lineno, self.reservation_depth > 0))
        self.generic_visit(node)


def _validate_surface(
    path: Path,
    *,
    label: str,
    transport_name: str,
    guard_name: str,
    expected_functions: set[str],
    included_functions: set[str] | None = None,
) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [f"{label} cannot be parsed: {type(exc).__name__}"]
    visitor = CoverageVisitor(
        transport_name=transport_name,
        guard_name=guard_name,
        included_functions=included_functions,
    )
    visitor.visit(tree)
    findings = [
        f"{label} line {call.line}: {call.function} transport is outside {guard_name}"
        for call in visitor.calls
        if not call.reserved
    ]
    observed_functions = {call.function for call in visitor.calls}
    missing = sorted(expected_functions - observed_functions)
    extra = sorted(observed_functions - expected_functions)
    if missing:
        findings.append(f"{label} missing transport functions: " + ", ".join(missing))
    if extra:
        findings.append(f"{label} unexpected transport functions: " + ", ".join(extra))
    if len(visitor.calls) != len(expected_functions):
        findings.append(
            f"{label} expected {len(expected_functions)} transports, observed {len(visitor.calls)}"
        )
    return findings


def validate(
    path: Path = ROUTER,
    direct_client: Path = DIRECT_CLIENT,
    model_failure_client: Path = MODEL_FAILURE_CLIENT,
    model_failure_judge_client: Path = MODEL_FAILURE_JUDGE_CLIENT,
) -> list[str]:
    findings = _validate_surface(
        path,
        label="primary router",
        transport_name="_http_post_json",
        guard_name="_budget_attempt",
        expected_functions=PRIMARY_FUNCTIONS,
    )
    findings.extend(
        _validate_surface(
            direct_client,
            label="adverse-media direct client",
            transport_name="urlopen",
            guard_name="_provider_budget_attempt",
            expected_functions=DIRECT_FUNCTIONS,
            included_functions=DIRECT_FUNCTIONS,
        )
    )
    findings.extend(
        _validate_surface(
            model_failure_client,
            label="model-failure direct client",
            transport_name="urlopen",
            guard_name="attempt",
            expected_functions=MODEL_FAILURE_FUNCTIONS,
            included_functions=MODEL_FAILURE_FUNCTIONS,
        )
    )
    findings.extend(
        _validate_surface(
            model_failure_judge_client,
            label="model-failure judge direct client",
            transport_name="urlopen",
            guard_name="attempt",
            expected_functions=MODEL_FAILURE_JUDGE_FUNCTIONS,
            included_functions=MODEL_FAILURE_JUDGE_FUNCTIONS,
        )
    )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--router", type=Path, default=ROUTER)
    parser.add_argument("--direct-client", type=Path, default=DIRECT_CLIENT)
    parser.add_argument("--model-failure-client", type=Path, default=MODEL_FAILURE_CLIENT)
    parser.add_argument(
        "--model-failure-judge-client", type=Path, default=MODEL_FAILURE_JUDGE_CLIENT
    )
    args = parser.parse_args(argv)
    findings = validate(
        args.router,
        args.direct_client,
        args.model_failure_client,
        args.model_failure_judge_client,
    )
    if findings:
        for finding in findings:
            print(f"[provider-budget-coverage] FAIL: {finding}")
        return 1
    print(
        "[provider-budget-coverage] PASS: four primary-router transports and "
        "the adverse-media, model-failure candidate, and model-failure judge direct "
        "transports are reservation-wrapped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
