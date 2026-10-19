"""``KiroRunCommandBuilder``: the command line, directory and environment of one agent run."""

from __future__ import annotations

from ..access import AccessScopes, ModelResolver
from ..agents import CharterReader
from ..kernel import Environment, OrgLayout
from .api import ProfileProvisioner, RunCommand, RunCommandBuilder


class KiroRunCommandBuilder(RunCommandBuilder):
    def __init__(
        self, kiro_bin: str, layout: OrgLayout, charters: CharterReader, scopes: AccessScopes, models: ModelResolver,
        provisioner: ProfileProvisioner, environment: Environment,
    ) -> None:
        self._kiro_bin = kiro_bin
        self._layout = layout
        self._charters = charters
        self._scopes = scopes
        self._models = models
        self._provisioner = provisioner
        self._environment = environment

    def build(self, addr: str, prompt: str) -> RunCommand:
        raise NotImplementedError
