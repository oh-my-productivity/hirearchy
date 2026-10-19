"""The commands of the blueprints: ``plan`` (read-only) and ``apply``."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..blueprint import BlueprintApplier, BlueprintLoader, BlueprintValidator, PlanRenderer, errors
from ..kernel import Provider
from ._ports import Arguments, Command, OrgSession, Output


class PlanCommand(Command):
    """Validates a blueprint and prints the plan for approval: against the organization if there is one, else against the defaults of a new one."""

    def __init__(
        self, session: OrgSession, loader: Provider[BlueprintLoader], validator: Provider[BlueprintValidator], renderer: Provider[PlanRenderer],
        out: Output,
    ) -> None:
        self._session = session
        self._loader = loader
        self._validator = validator
        self._renderer = renderer
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError


class ApplyCommand(Command):
    def __init__(self, session: OrgSession, loader: Provider[BlueprintLoader], applier: Provider[BlueprintApplier], out: Output) -> None:
        self._session = session
        self._loader = loader
        self._applier = applier
        self._out = out

    def add_arguments(self, sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
        raise NotImplementedError

    def run(self, args: Arguments) -> None:
        raise NotImplementedError
