"""The pure rules of ``access``: no collaborator, no file."""

from __future__ import annotations

from collections.abc import Mapping


def unconfined_read(meta: Mapping[str, object]) -> bool:
    """Legacy charter: no workspace and no ``inputs`` key. Its built-in ``read`` is not confined (as before)."""
    return not meta.get("workspace") and "inputs" not in meta
