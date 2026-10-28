"""A real temporary organization and the extension resolver over it (no test lives here)."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from testkit.reach.hirearchy.core import ROOT, Org

from hirearchy.blueprint import Issue
from hirearchy.blueprint._extension import ExtensionResolver
from hirearchy.blueprint._extension_org import Reads
from hirearchy.blueprint._org import RuntimeOrgContext
from hirearchy.blueprint._pathcheck import RootedPathChecker
from hirearchy.blueprint._resolver import AgentResolver
from hirearchy.blueprint._roots import EnvironmentWorkspaceRoots


def reads_of(org: Org) -> Reads:
    rt = org.runtime
    context = RuntimeOrgContext(rt.settings, rt.agents, rt.service_catalog, rt.paths)
    return Reads(
        context, rt.agents, rt.charters, rt.role_library, AgentResolver(rt.role_library, RootedPathChecker(rt.environment)),
        EnvironmentWorkspaceRoots(rt.environment, lambda: Path(tempfile.gettempdir())), rt.service_catalog,
    )


@dataclass
class World:
    org: Org
    tmp: Path
    resolver: ExtensionResolver

    def issues(self, bp: dict[str, object], *, level: str | None = None) -> list[Issue]:
        found = self.resolver.resolve(bp, allowed_roots=[self.tmp]).issues
        return [i for i in found if level is None or i.level == level]

    def errors(self, bp: dict[str, object]) -> list[Issue]:
        return self.issues(bp, level="error")


def extension(**sections: object) -> dict[str, object]:
    return {"reason": "B1.1: a change", "extend": dict(sections)}


def world(tmp_path: Path, *, max_depth: int = 4, lead_reports: int = 2) -> World:
    """root -> lead (reads and writes in ws, one input folder, may have 2 reports, has 1: writer) and solo (reads only, no hiring)."""
    org = Org.init(tmp_path / "org", "extension tests", {"poll_seconds": 0.05, "max_depth": max_depth})
    ws, src, solo_ws = tmp_path / "ws", tmp_path / "src", tmp_path / "solo"
    for d in (ws / "w", src, solo_ws):
        d.mkdir(parents=True)
    org.hire(ROOT, "lead", "Lead", "Directs.", tools=["read", "write"], workspace=str(ws), inputs=[str(src)], can_hire=True, max_children=lead_reports)
    org.hire("lead", "writer", "Writer", "Writes.", tools=["read", "write"], workspace=str(ws / "w"))
    org.hire(ROOT, "solo", "Solo", "Works alone.", tools=["read"], inputs=[str(src)], can_hire=False, max_children=0)
    return World(org, tmp_path, ExtensionResolver(reads_of(org)))


def codes(issues: list[Issue]) -> list[str]:
    return [i.code for i in issues]
