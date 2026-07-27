#!/usr/bin/env python3
"""Verify that every primary-router HTTP attempt has an enclosing reservation."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts" / "llm_generate.py"
EXPECTED_FUNCTIONS = {
    "ollama_chat",
    "nvidia_chat",
    "openai_compatible_chat",
    "anthropic_chat",
}


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
    def __init__(self) -> None:
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
        guarded = any(_call_name(item.context_expr) == "_budget_attempt" for item in node.items)
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
        if _call_name(node) == "_http_post_json":
            function = self.function_stack[-1] if self.function_stack else "<module>"
            self.calls.append(
                TransportCall(function, node.lineno, self.reservation_depth > 0)
            )
        self.generic_visit(node)


def validate(path: Path = ROUTER) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [f"router cannot be parsed: {type(exc).__name__}"]
    visitor = CoverageVisitor()
    visitor.visit(tree)
    findings = [
        f"line {call.line}: {call.function} transport is outside _budget_attempt"
        for call in visitor.calls
        if not call.reserved
    ]
    observed_functions = {call.function for call in visitor.calls}
    missing = sorted(EXPECTED_FUNCTIONS - observed_functions)
    extra = sorted(observed_functions - EXPECTED_FUNCTIONS)
    if missing:
        findings.append("missing primary transport functions: " + ", ".join(missing))
    if extra:
        findings.append("unexpected primary transport functions: " + ", ".join(extra))
    if len(visitor.calls) != len(EXPECTED_FUNCTIONS):
        findings.append(
            f"expected {len(EXPECTED_FUNCTIONS)} transports, observed {len(visitor.calls)}"
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--router", type=Path, default=ROUTER)
    args = parser.parse_args(argv)
    findings = validate(args.router)
    if findings:
        for finding in findings:
            print(f"[provider-budget-coverage] FAIL: {finding}")
        return 1
    print(
        "[provider-budget-coverage] PASS: four primary transports are "
        "reservation-wrapped"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
