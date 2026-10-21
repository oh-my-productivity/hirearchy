"""Finding the organization root from ``$ORG_ROOT`` and the working directory."""

from __future__ import annotations

from pathlib import Path

from ..kernel import Environment, OrgError
from .api import OrgLocator

NOT_FOUND = "no organization found: set ORG_ROOT or run inside an org directory"


class EnvOrgLocator(OrgLocator):
    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def find_root(self, start: str | Path | None = None) -> Path:
        env = self._environment.get("ORG_ROOT")
        if env:
            return Path(env).expanduser().resolve()
        here = Path(start or self._environment.cwd()).resolve()
        for d in (here, *here.parents):
            if (d / "ORG.md").is_file():
                return d
        if (here / "org" / "ORG.md").is_file():  # e.g. running from the hirearchy project dir
            return here / "org"
        raise OrgError(NOT_FOUND)
