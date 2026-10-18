"""Finding the organization root from ``$ORG_ROOT`` and the working directory."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Environment
from .api import OrgLocator

NOT_FOUND = "no organization found: set ORG_ROOT or run inside an org directory"


class EnvOrgLocator(OrgLocator):
    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def find_root(self, start: Path | None = None) -> Path:
        raise NotImplementedError("red: A-settings")
