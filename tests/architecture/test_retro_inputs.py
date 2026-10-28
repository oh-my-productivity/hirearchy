"""The signals of ``retro`` read no lessons, memory, notes or reports (design 7.7, 12 G2, owner brief check 2).

A signal's inputs decide what can nominate an item, so ``retro/_signals.py`` takes only the narrow views of ``retro/_views.py`` (human-tier verdicts, runtime facts, root's own
one-off tasks) and thresholds: the types of its parameters are an allow-list, and no name of a text a team writes (a lesson, a memory, a note, a report, a message body)
appears in the module."""

from __future__ import annotations

import ast

import pytest

from .paths import SRC

pytestmark = pytest.mark.architecture

SIGNALS = SRC / "retro" / "_signals.py"
ALLOWED = {
    "Sequence", "Mapping", "ShapeGroup", "RetroThresholds", "ServiceFailures", "FailedCase", "TakenFix", "OneOffCase", "Fraction", "frozenset", "tuple", "str", "int", "None", "bool",
    "OwnerFacts", "HealthFlag", "Flag", "Item", "float", "object",
}
FORBIDDEN_NAMES = {"lessons", "lesson", "memory", "notes", "note", "report", "reports", "body", "Message", "Case", "ServiceRecord", "Verdict", "Delivery", "Assertion", "Playbook"}


def parameter_types() -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(SIGNALS.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            for arg in args:
                if arg.annotation is not None:
                    names |= {n.id for n in ast.walk(arg.annotation) if isinstance(n, ast.Name)}
    return names


def test_the_signals_read_no_lessons_memory_notes_or_reports() -> None:
    assert parameter_types() <= ALLOWED, f"a signal takes a type that is not a narrow view: {sorted(parameter_types() - ALLOWED)}"
    used = {n.id for n in ast.walk(ast.parse(SIGNALS.read_text(encoding="utf-8"))) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(ast.parse(SIGNALS.read_text(encoding="utf-8"))) if isinstance(n, ast.Attribute)
    }
    assert not (used & FORBIDDEN_NAMES), f"a signal names what a team writes: {sorted(used & FORBIDDEN_NAMES)}"


def test_the_check_catches_a_signal_that_takes_a_case() -> None:
    source = "def signal(cases: Sequence[Case], notes: list[str]) -> None:\n    return None\n"
    names = {n.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) for a in node.args.args if a.annotation for n in ast.walk(a.annotation) if isinstance(n, ast.Name)}
    assert "Case" in names and "Case" in FORBIDDEN_NAMES and not names <= ALLOWED
