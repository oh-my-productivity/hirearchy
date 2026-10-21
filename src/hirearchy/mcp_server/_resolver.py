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
        self._environment = environment
        self._locator = locator
        self._opener = opener
        self._bindings = bindings

    def resolve(self) -> tuple[OrgBindingPort, str]:
        agent = (self._environment.get("ORG_AGENT") or "").strip()
        if (self._environment.get("ORG_REQUIRE_AGENT") or "").strip().lower() not in ("", "0", "false", "no"):
            if not agent or norm(agent) == ROOT:
                raise OrgError(
                    "ORG_REQUIRE_AGENT is set but ORG_AGENT does not name an agent: this is an internal profile of the "
                    "hirearchy scheduler and only works when the scheduler starts it. Refusing to act as root. "
                    "To manage an organization yourself, register `hirearchy mcp` without ORG_REQUIRE_AGENT")
        if agent:
            ports = self._opener.open(self._locator.find_root())  # an agent: no organization means fail fast
            return self._bindings.bind(ports.root, ports, pinned=True), agent
        pinned = bool(self._environment.get("ORG_ROOT"))
        root: Path | None
        try:
            root = self._locator.find_root()
        except OrgError:
            root = None
        return self._bindings.bind(root, pinned=pinned), ROOT
