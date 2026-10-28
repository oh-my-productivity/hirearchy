"""``ExtensionResolver``: an extension blueprint read against the organization it extends (design 5.2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..kernel import ROOT, norm
from ._extension_agents import added_agents
from ._extension_changes import limits_of, retires_of
from ._extension_form import form_issues
from ._extension_org import Reads, as_int, read_held, retargeted
from ._extension_services import added_services, cap_issue, charter_lines, checkers_of, rebudgeted, retired_services, team_of, team_owners
from ._protocols import ExtensionResolution
from ._provenance import criterion_issues, task_copy_issues
from ._shapes import Extension
from ._view import needs_of, s
from .api import Issue

EXTEND_NONE = (
    "refused: there is no organization yet, so there is nothing to extend: create_org(mission=...) and a full blueprint come first."
)
LOWERS = "this removes the last check of {service}: its requests are then checked only by {lead}"
NAMING_SECTIONS = {
    "add_agents": "parent", "add_services": "owner", "budgets": "owner", "retire_services": "owner", "add_charter_lines": "agent",
    "remove_charter_lines": "agent", "limits": "agent",
}


class ExtensionResolver(ExtensionResolution):
    def __init__(self, reads: Reads) -> None:
        self._reads = reads

    def resolve(self, bp: Mapping[str, object], *, allowed_roots: Sequence[str | Path] | None = None, require_sources: bool = False) -> Extension:
        ext = Extension(form_issues(bp))
        if any(i.level == "error" for i in ext.issues):
            return ext
        reads = self._reads
        if reads.org.root() is None:
            ext.issues.append(Issue("error", "extend", EXTEND_NONE, "extend-none"))
            return ext
        extend = bp["extend"]
        assert isinstance(extend, Mapping)
        ext.reason = s(bp.get("reason"))
        cfg = reads.org.config()
        needs = needs_of(bp)
        sections = {name: [(i, e) for i, e in enumerate(extend.get(name) or []) if isinstance(e, Mapping)] for name in (*NAMING_SECTIONS, "retire")}
        ext.cap = cap_issue(needs, ext.issues)
        roots = reads.roots.roots(allowed_roots)
        ext.limits, ext.depth = limits_of(reads, sections["limits"], ext.issues)
        max_depth = ext.depth.value if ext.depth is not None else as_int(cfg.get("max_depth"), 4)
        ext.agents, ext.extras = added_agents(
            reads, sections["add_agents"], {c.agent: c for c in ext.limits}, max_depth, cfg, allowed_roots, ext.issues,
        )
        named = {
            norm(s(e.get(key))): f"extend.{section}[{i}]" for section, key in NAMING_SECTIONS.items() for i, e in sections[section] if norm(s(e.get(key))) != ROOT
        }
        ext.retires = retires_of(reads, sections["retire"], named, ext.issues)
        gone = {a for r in ext.retires for a in r.team}
        view: dict[str, object] = {"needs": needs, "services": [dict(e) for _, e in sections["add_services"]]}
        owners = [o for o in team_owners(ext.agents, gone, []) + [norm(s(e.get("owner"))) for _, e in sections["add_services"] + sections["budgets"]]
                  if o != ROOT and "/" not in o and reads.agents.exists(o)]
        ext.teams = {o: team_of(reads, o, gone, ext.agents) for o in dict.fromkeys(owners)}
        ext.services = added_services(reads, sections["add_services"], ext.teams, ext.cap, roots, ext.issues)
        ext.service_retires = retired_services(reads, sections["retire_services"], ext.issues)
        ext.budgets = rebudgeted(reads, sections["budgets"], ext.teams, ext.cap, {(r.owner, r.service) for r in ext.service_retires}, ext.issues)
        ext.lines, ext.removals = charter_lines(reads, sections["add_charter_lines"], sections["remove_charter_lines"], ext.issues)
        ext.checkers = checkers_of(reads, ext.agents, {o: [sv.name for sv in ext.services if sv.owner == o] for o in ext.teams})
        ext.issues += self._provenance(view, sections["add_services"], require_sources)
        self._lowers(ext, sections["retire"])
        return ext

    def _provenance(self, view: Mapping[str, object], entries: Sequence[tuple[int, Mapping[str, object]]], require_sources: bool) -> list[Issue]:
        """The provenance rules of 10.1 for the criteria of the added services, at the paths of their entries."""
        where = {s(e.get("name")): f"extend.add_services[{i}]" for i, e in entries}
        found = criterion_issues(view, extension=True, require_sources=require_sources) + task_copy_issues(view, self._reads.tasks)
        return retargeted(found, where)

    def _lowers(self, ext: Extension, entries: Sequence[tuple[int, Mapping[str, object]]]) -> None:
        """``extend-lowers`` (warning): a retire takes away the last verifier of a team that keeps a service."""
        reads = self._reads
        gone = {a for r in ext.retires for a in r.team}
        for r in ext.retires:
            where = next((f"extend.retire[{i}]" for i, e in entries if norm(s(e.get("agent"))) == r.agent), "extend.retire")
            for owner in dict.fromkeys(a.split("/")[0] for a in r.team if read_held(reads.agents, reads.charters, reads.roles, a).verifier):
                if owner in gone:
                    continue
                kept = [a for a in reads.agents.subtree(owner)[1:] if a not in gone and read_held(reads.agents, reads.charters, reads.roles, a).verifier]
                added = [a for a in ext.agents if a.addr.split("/")[0] == owner and a.kind == "verifier"]
                if kept or added:
                    continue
                for service in reads.services.service_names(owner):
                    ext.issues.append(Issue("warning", where, LOWERS.format(service=service, lead=owner), "extend-lowers"))
