"""``KiroConfinementPolicy``: which paths kiro's built-in ``read``/``write`` may use."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .api import ConfinementPolicy


class KiroConfinementPolicy(ConfinementPolicy):
    def file_confinement(
        self, org_root: Path, tools: Sequence[str], workspace: Path | None, inputs: Sequence[Path]
    ) -> tuple[list[str], dict[str, object]]:
        raise NotImplementedError
