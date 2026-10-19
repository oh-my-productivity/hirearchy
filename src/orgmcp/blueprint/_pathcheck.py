"""``RootedPathChecker``: a user path must be absolute, inside an allowed root, and away from the organization and ``~/.kiro``."""
from __future__ import annotations
import os
from collections.abc import Sequence
from pathlib import Path
from ..kernel import Environment, inside
from ._protocols import OrgContext, PathChecking
from ._view import s
from .api import Issue

class RootedPathChecker(PathChecking):

    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def check(self, raw: object, where: str, issues: list[Issue], org: OrgContext, roots: Sequence[Path], *, what: str, dir_must_exist: bool) -> Path | None:
        raise NotImplementedError('red: C-blueprint-1')
