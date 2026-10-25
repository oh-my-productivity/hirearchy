"""Words of a domain that the core must not name (design 15, I9): the quality modules are domain-agnostic, so they hold no word of the work they were
first measured on.

``violations(path)`` lists every identifier (split on ``_`` and on case changes) and every string literal of a module that holds one of ``WORDS`` as
a whole word, case-insensitively. Docstrings and comments are documentation, not behaviour, and are not read."""

from __future__ import annotations

import ast
import re
from pathlib import Path

WORDS = ("memo", "meeting", "code", "test", "pull request", "ticket", "research")
_PATTERN = re.compile(r"\b(" + "|".join(re.escape(w) for w in WORDS) + r")\b", re.IGNORECASE)
_PARTS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def _identifier_words(name: str) -> str:
    """``cost_alarmCase`` as ``cost alarm Case``: the parts of an identifier, split on ``_`` and on case changes."""
    return " ".join(_PARTS.findall(name))


def _docstrings(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def _identifiers(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.arg):
        return [node.arg]
    if isinstance(node, ast.keyword) and node.arg:
        return [node.arg]
    if isinstance(node, ast.alias):
        return [node.asname or node.name.split(".")[-1]]
    return []


def violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = _docstrings(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        for name in _identifiers(node):
            if hit := _PATTERN.search(_identifier_words(name)):
                found.append(f"{path.name}:{getattr(node, 'lineno', 0)}: identifier {name!r} holds the word {hit.group(1)!r}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip and (hit := _PATTERN.search(node.value)):
            found.append(f"{path.name}:{node.lineno}: the string {node.value[:60]!r} holds the word {hit.group(1)!r}")
    return found
