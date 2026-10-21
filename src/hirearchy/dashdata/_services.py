"""``CachedServiceQuery``: the services of the organization and the record of each."""

from __future__ import annotations

from ..agents import AgentDirectory
from ..kernel import clip_line
from ..reflection import CaseHistory, Stats, stats_by_version, summarize
from ..services import ServiceCatalog
from ._const import SERVICES_TTL
from ._data import Section, ServiceRow, Snapshot
from ._ports import CaseVerdicts
from .api import DashboardState, ServiceQuery, SnapshotQuery


class CachedServiceQuery(ServiceQuery):
    def __init__(self, state: DashboardState, snapshots: SnapshotQuery, agents: AgentDirectory, catalog: ServiceCatalog, history: CaseHistory,
                 verdicts: CaseVerdicts) -> None:
        self._state = state
        self._snapshots = snapshots
        self._agents = agents
        self._catalog = catalog
        self._history = history
        self._verdicts = verdicts

    def services(self, snap: Snapshot | None = None) -> list[ServiceRow]:
        self._state.refresh()
        snap = snap or self._state.snap or self._snapshots.snapshot()
        return self._state.memoised("services", snap.sig, SERVICES_TTL, self._services)

    def _services(self) -> list[ServiceRow]:
        rows: list[ServiceRow] = []
        for owner in self._agents.agents():
            for name in self._catalog.service_names(owner):
                try:
                    c = self._catalog.read_contract(owner, name)
                    if c is None:
                        continue
                    pb = self._catalog.read_playbook(owner, name)
                    stats = summarize(self._history.cases(owner, name))
                except Exception as exc:  # noqa: BLE001
                    rows.append(ServiceRow(owner, name, 0, 0, False, Stats(), f"unreadable: {type(exc).__name__}", ""))
                    continue
                rows.append(ServiceRow(owner, name, c.version, pb.version, c.locked, stats, pb.reason, c.description))
        return rows

    def service_detail(self, owner: str, name: str) -> list[Section]:
        try:
            c = self._catalog.read_contract(owner, name)
            if c is None:
                return [Section("", [f"{owner}/{name}: no such service (retired?)"])]
            pb = self._catalog.read_playbook(owner, name)
            items = self._history.cases(owner, name)
        except Exception as exc:  # noqa: BLE001
            return [Section("", [f"cannot read the service: {type(exc).__name__}: {exc}"])]
        stats = summarize(items)
        doc = [Section(f"{name} (owner {owner})", [
            c.description or "(no description)",
            f"contract v{c.version}" + (" (locked)" if c.locked else "") + f", budget {c.budget} per request"
            + (f", defined by {c.defined_by}" if c.defined_by else ""),
            f"playbook v{pb.version}" + (f" revised by {pb.by or '?'}: {pb.reason}" if pb.version else " (none yet)"),
        ])]
        doc.append(Section("Record", [stats.line()]))
        by_v = stats_by_version(items)
        if by_v:
            doc.append(Section("By playbook version", [f"v{v}: {s.line()}" for v, s in by_v.items()]))
        lines = []
        for case in reversed(items):
            bits = [f'{case.id}  "{clip_line(case.title, 50)}"  {case.state}', f"playbook v{case.used}",
                    f"{case.runs} of {case.budget} runs"]
            if case.reworks:
                bits.append(f"{case.reworks} rework(s)")
            if case.verdicts:
                bits.append("feedback: " + self._verdicts.chain(case))
            lines.append(", ".join(bits))
        doc.append(Section(f"Cases ({len(items)})", lines or ["none yet"]))
        doc.append(Section("Contract", [
            "inputs: " + (", ".join(f"{i['name']}{'*' if i['required'] else ''}" for i in c.inputs) or "none"),
            *[f"  accept: {a}" for a in c.acceptance],
            "deliverable: " + ", ".join(f"{k}={v}" for k, v in c.deliverable.items()),
        ]))
        doc.append(Section(f"Playbook v{pb.version}" if pb.version else "Playbook", (pb.body or "(none)").splitlines()))
        return doc
