"""The contract and the playbook of a service as values, parsed from the frontmatter and the body of their files."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import SupportsInt, cast

from ..kernel import JsonObject, parse_time
from .api import Contract, Playbook


VERSIONED_KINDS = ("SERVICE", "PLAYBOOK")  # the files that keep a history


def as_int(value: object, default: int = 0) -> int:
    """``value`` as a whole number; ``default`` for what is none (absent, a bool, text that is no number)."""
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(cast("SupportsInt | str", value))
    except (TypeError, ValueError):
        return default


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
    """The playbook a ``PLAYBOOK.md`` describes."""
    return Playbook(
        version=as_int(meta.get("version")), revised=as_time(meta.get("revised")), by=str(meta.get("by") or ""),
        reason=str(meta.get("reason") or ""), body=body.strip(), path=path, evidence=_ids(meta.get("evidence")),
        admitted=str(meta.get("admitted") or ""),
    )


def _ids(value: object) -> list[str]:
    """The ids of an ``evidence`` list as text, without blanks; anything else (a damaged file) is no evidence."""
    return [text for x in value if (text := str(x).strip())] if isinstance(value, list) else []
