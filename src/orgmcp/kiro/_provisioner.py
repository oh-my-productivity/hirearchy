"""``OrgProfileProvisioner``: the kiro profile of one organization."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

from ..kernel import OrgLayout
from ._profile_document import kiro_profile
from .api import ConfinementPolicy, McpServerLocator, ProfileProvisioner, ProfileStore


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


class OrgProfileProvisioner(ProfileProvisioner):
    def __init__(self, layout: OrgLayout, store: ProfileStore, confinement: ConfinementPolicy, locator: McpServerLocator) -> None:
        self._layout = layout
        self._store = store
        self._confinement = confinement
        self._locator = locator

    def profile_name(self, tools: Sequence[str]) -> str:
        """``orgmcp-<org-slug>-<6-char hash of the org root path>[-<tools>]``, lowercase ``[a-z0-9-]``.

        The hash makes the name unique per organization (two ``.../org`` dirs never share a profile); the slug only
        makes it recognizable. Profiles of different orgs therefore never overwrite each other.
        """
        root = Path(self._layout.root).expanduser().resolve()
        base = root.name
        if base.lower() == "org" and root.parent.name:  # "org" alone says nothing: use "<parent>-org"
            base = f"{root.parent.name}-org"
        slug = _slug(base)[:24].strip("-") or "org"
        digest = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:6]
        return "-".join(["orgmcp", slug, digest, *(_slug(t) for t in sorted(set(tools)) if _slug(t))])

    def ensure_profile(
        self, tools: Sequence[str], *, workspace: Path | None = None, inputs: Sequence[Path] | None = None, confine: bool = False
    ) -> str:
        """Write the scheduler's profile for the organization into ``~/.kiro/agents``: only the orgmcp server plus the granted tools.

        The profile is internal to this organization: its MCP server entry carries ``ORG_ROOT`` (this org) and
        ``ORG_REQUIRE_AGENT=1``, so used outside the scheduler (no ``ORG_AGENT``) the server refuses to start instead of
        acting as ``root``. ``ORG_AGENT`` itself is NOT baked in: it comes from the scheduler's process environment
        (assumption: kiro starts MCP servers with its own environment plus the profile's ``env``; if it did not, the
        server would fail closed and the run would fail visibly rather than act as root).

        ``confine=False``: the shared profile of the org for this tool set; every granted tool runs unprompted.
        ``confine=True``: the profile of an agent with built-in ``read``/``write``: they are limited to ``workspace`` (write)
        and ``workspace`` + ``inputs`` + the org itself (read), see ``ConfinementPolicy.file_confinement``. Its name carries a
        hash of that access, so agents with the same tools and access share a profile and different access never does.

        Profiles of other orgs, and the legacy global ``orgmcp[-tools].json`` files, are never touched.
        """
        root = self._layout.root
        tools = sorted(set(tools))
        name = self.profile_name(tools)
        settings: dict[str, object]
        allowed, settings = ["@orgmcp", *tools], {}
        if confine:
            allowed, settings = self._confinement.file_confinement(root, tools, workspace, list(inputs or []))
            allowed = ["@orgmcp", *allowed]
            name += "-x" + hashlib.sha1(json.dumps(settings, sort_keys=True).encode("utf-8")).hexdigest()[:8]
        server = {**self._locator.command(), "env": {"ORG_ROOT": str(root), "ORG_REQUIRE_AGENT": "1"}}
        data = kiro_profile(
            name,
            f"internal: used by the orgmcp scheduler for {root}; not a general-purpose agent"
            + (f" (built-in tools: {', '.join(tools)})" if tools else ""),
            ["@orgmcp", *tools],
            server,
            allowed_tools=allowed,
            tools_settings=settings,
        )
        if self._store.read(name) != data:  # missing or corrupt: rewrite it
            self._store.write(name, data)
        return name
