"""The binding and the identity of a server, from the environment."""
from __future__ import annotations
from pathlib import Path
from ..kernel import ROOT, Environment, OrgError, norm
from ..locator import OrgLocator
from ._ports import BindingFactory, OrgOpener
from .api import BindingResolver, OrgBindingPort

class EnvBindingResolver(BindingResolver):
    """* ORG_REQUIRE_AGENT=1 (set in the profiles the scheduler writes): ORG_AGENT must name an agent, otherwise the server refuses to start,
    so a profile used outside the scheduler fails closed instead of acting as root.
    * ORG_AGENT set: an agent; the organization must exist (fail fast, as always).
    * otherwise: root. ORG_ROOT (or the organization found from the working directory) is the bound path, whether or not an organization
      exists there yet."""

    def __init__(self, environment: Environment, locator: OrgLocator, opener: OrgOpener, bindings: BindingFactory) -> None:
        raise NotImplementedError('red: D-mcp')

    def resolve(self) -> tuple[OrgBindingPort, str]:
        raise NotImplementedError('red: D-mcp')
