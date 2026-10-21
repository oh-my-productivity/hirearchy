"""The pure rules of ``access``: no collaborator, no file."""

from __future__ import annotations

from collections.abc import Mapping

from ..kernel import OrgError

CHILDREN_LIMIT_ERROR = "max_children must be a whole number >= 0"


def unconfined_read(meta: Mapping[str, object]) -> bool:
    """Legacy charter: no workspace and no ``inputs`` key. Its built-in ``read`` is not confined (as before)."""
    return not meta.get("workspace") and "inputs" not in meta


def children_limit(value: object) -> int:
    """``value`` as a report's ``max_children``: an ``int`` (not a ``bool``) >= 0, else ``OrgError``. Numeric strings are refused:
    YAML, the MCP schema and the CLI's argparse all give ints."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OrgError(CHILDREN_LIMIT_ERROR)
    return value
