"""Markdown files with a YAML frontmatter block."""

from __future__ import annotations

import yaml

from ._ports import JsonObject

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)  # libyaml when available: same result, ~10x faster


def split_frontmatter(text: str) -> tuple[JsonObject, str]:
    """``(meta, body)`` of a file's text; ``({}, text)`` without a (dict) frontmatter block."""
    raise NotImplementedError("red: K1")


def join_frontmatter(meta: JsonObject, body: str) -> str:
    """The text of a file with ``meta`` as frontmatter and ``body`` (one trailing newline)."""
    raise NotImplementedError("red: K1")
