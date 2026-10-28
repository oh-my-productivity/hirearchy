"""The contract and the playbook of a service as values, parsed from the frontmatter and the body of their files."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import SupportsInt, cast

from ..kernel import JsonObject, parse_time, split_frontmatter
from ._items import parse_items, rules_of, why_of
from .api import Contract, Playbook


VERSIONED_KINDS = ("SERVICE", "PLAYBOOK")  # the files that keep a history
FILE_SHAPE = re.compile(r"(SERVICE|PLAYBOOK|RETIRED)\.md|history/(SERVICE|PLAYBOOK|RETIRED)\.v\d+\.md")  # the files of a service directory, as named inside it


def as_int(value: object, default: int = 0) -> int:
    """``value`` as a whole number; ``default`` for what is none (absent, a bool, text that is no number)."""
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(cast("SupportsInt | str", value))
    except (TypeError, ValueError):
        return default


def restore_targets(files: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    """The files of a retired copy that a continuation puts back, as ``(name inside the live service directory, text)``, ``SERVICE.md`` last (until it
    is there, no service exists). The copy's ``RETIRED.md`` is kept as ``history/RETIRED.v<n>.md``, ``n`` the contract version it retired."""
    shapes = [(rel, text) for rel, text in files if FILE_SHAPE.fullmatch(rel)]
    version = next((as_int(split_frontmatter(text)[0].get("version")) for rel, text in shapes if rel == "SERVICE.md"), 0)
    named = [(f"history/RETIRED.v{version}.md" if rel == "RETIRED.md" else rel, text) for rel, text in shapes]
    return sorted(named, key=lambda file: file[0] == "SERVICE.md")


def playbook_version(text: str | None) -> int:
    """The version a ``PLAYBOOK.md``'s frontmatter states; 0 for no file and for a file that states none."""
    return as_int(split_frontmatter(text)[0].get("version")) if text is not None else 0


def as_time(value: object) -> datetime | None:
    """The time a frontmatter field holds; None when it is empty or unreadable."""
    return parse_time(value) if value else None


def _items(value: object) -> list[object]:
    """What a list-valued field holds, as the files have always been read: an empty field has no items, anything else is iterated."""
    return list(cast("Iterable[object]", value or []))


def contract_of(owner: str, name: str, meta: JsonObject, body: str, path: Path | None) -> Contract:
    """The contract a ``SERVICE.md`` describes."""
    inputs: list[JsonObject] = [
        {"name": str(i.get("name", "")), "description": str(i.get("description") or ""), "required": i.get("required", True) is not False}
        for i in _items(meta.get("inputs")) if isinstance(i, dict) and i.get("name")
    ]
    deliverable = meta.get("deliverable")
    return Contract(
        name=name, owner=owner, description=str(meta.get("description") or ""), inputs=inputs,
        acceptance=[str(a) for a in _items(meta.get("acceptance"))],
        deliverable=dict(deliverable) if isinstance(deliverable, dict) else {},
        budget=max(1, as_int(meta.get("budget"), 1)), locked=meta.get("locked") is True,
        version=max(1, as_int(meta.get("version"), 1)), defined_by=str(meta.get("defined_by") or ""),
        defined=as_time(meta.get("defined")), created=as_time(meta.get("created") or meta.get("defined")),
        notes=body.strip(), path=path, answers=_text(meta.get("answers")), about=_text(meta.get("about")), words=_text(meta.get("words")),
        initiated=_text(meta.get("initiated")),
    )


def _text(value: object) -> str:
    """A frontmatter field as text; nothing (absent, false, empty) is ``""``."""
    return str(value) if value else ""


def merged_versions(kind: str, files: Iterable[tuple[JsonObject, str]]) -> list[tuple[int, JsonObject, str]]:
    """The ``(version, frontmatter, body)`` of the files of one kind, given kept ones first and the current one last, sorted by the version
    they state (0 when none); of two files that state one version, the later (the current one) wins."""
    if kind not in VERSIONED_KINDS:
        raise ValueError(f"kind must be one of {VERSIONED_KINDS}: {kind!r}")
    by_version = {as_int(meta.get("version")): (meta, body) for meta, body in files}
    return [(version, *by_version[version]) for version in sorted(by_version)]


def playbook_of(meta: JsonObject, body: str, path: Path | None) -> Playbook:
    """The playbook a ``PLAYBOOK.md`` describes. A frontmatter with ``items_max`` is item format: its body is parsed into items, and one that does
    not parse gives ``parse_error`` instead (never an exception); any other playbook is legacy (``items`` None)."""
    text = body.strip()
    parsed = parse_items(text, meta) if "items_max" in meta else None
    return Playbook(
        version=as_int(meta.get("version")), revised=as_time(meta.get("revised")), by=str(meta.get("by") or ""),
        reason=str(meta.get("reason") or ""), body=text, path=path, evidence=_ids(meta.get("evidence")),
        admitted=str(meta.get("admitted") or ""),
        items=parsed.items if parsed is not None and not parsed.error else None, sections=parsed.sections if parsed is not None else (),
        items_max=as_int(meta.get("items_max")), rules=rules_of(meta), why=why_of(meta), op=_text(meta.get("op")), item=_text(meta.get("item")),
        related=tuple(_ids(meta.get("related"))), restores=as_int(meta.get("restores")), acknowledged=_text(meta.get("acknowledged")), parse_error=parsed.error if parsed is not None else "",
    )


def _ids(value: object) -> list[str]:
    """The ids of an ``evidence`` list as text, without blanks; anything else (a damaged file) is no evidence."""
    return [text for x in value if (text := str(x).strip())] if isinstance(value, list) else []
