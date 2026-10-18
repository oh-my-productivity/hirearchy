"""The pure rules of ``access``: no collaborator, no file."""

from __future__ import annotations

from collections.abc import Mapping


def unconfined_read(meta: Mapping[str, object]) -> bool:
    raise NotImplementedError
