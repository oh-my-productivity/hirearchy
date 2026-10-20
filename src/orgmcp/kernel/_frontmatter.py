"""Markdown files with a YAML frontmatter block."""

from __future__ import annotations

import yaml

from ._ports import JsonObject

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)  # libyaml when available: same result, ~10x faster


def split_frontmatter(text: str) -> tuple[JsonObject, str]:
    """``(meta, body)`` of a file's text; ``({}, text)`` without a (dict) frontmatter block."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            meta = yaml.load(text[4:end], Loader=_YAML_LOADER) or {}
            return (meta if isinstance(meta, dict) else {}), text[end + 5 :]
    return {}, text


def join_frontmatter(meta: JsonObject, body: str) -> str:
    """The text of a file with ``meta`` as frontmatter and ``body`` (one trailing newline)."""
    dumped: str = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return "---\n" + dumped + "---\n" + body.rstrip() + "\n"


def flow_text(value: object) -> str:
    """``value`` as YAML in flow style on one line (``[read, write]``, ``{a: 1}``): blanks collapsed, never wrapped, without the document-end marker."""
    text: str = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=10_000).strip()
    if text.endswith("\n..."):
        text = text[:-4].strip()
    return " ".join(text.split())
