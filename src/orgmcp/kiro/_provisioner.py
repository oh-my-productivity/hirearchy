"""``OrgProfileProvisioner``: the kiro profile of one organization."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..kernel import OrgLayout
from .api import ConfinementPolicy, McpServerLocator, ProfileProvisioner, ProfileStore


class OrgProfileProvisioner(ProfileProvisioner):
    def __init__(self, layout: OrgLayout, store: ProfileStore, confinement: ConfinementPolicy, locator: McpServerLocator) -> None:
        self._layout = layout
        self._store = store
        self._confinement = confinement
        self._locator = locator

    def profile_name(self, tools: Sequence[str]) -> str:
        raise NotImplementedError

    def ensure_profile(
        self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None, confine: bool = False
    ) -> str:
        raise NotImplementedError
