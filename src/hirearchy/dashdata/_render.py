"""``TextSnapshotRenderer``: the plain text of ``hirearchy dash --once``."""

from __future__ import annotations

from ..kernel import ROOT, clip_line, fmt_dur
from .api import RequestQuery, ServiceQuery, SnapshotQuery, SnapshotRenderer


class TextSnapshotRenderer(SnapshotRenderer):
    def __init__(self, snapshots: SnapshotQuery, requests: RequestQuery, services: ServiceQuery) -> None:
        self._snapshots = snapshots
        self._requests = requests
        self._services = services

    def render_once(self, width: int = 110) -> str:
        """The ``hirearchy dash --once`` output: header, the agent tree with states, requests, services."""
        snap = self._snapshots.snapshot()
        out = [f"hirearchy dash - {snap.org_name} ({snap.root})  {snap.at:%Y-%m-%d %H:%M:%S}Z",
               f"{snap.scheduler.text} | {snap.counts_text}", ""]
        out.append("AGENTS")
        for addr in snap.order:
            r = snap.agents[addr]
            indent = "  " * r.depth
            if addr == ROOT:
                out.append(f"{r.glyph} root (you)" + (f"  needs you: {len(snap.needs_you)}" if snap.needs_you else ""))
                continue
            budget = "" if r.budget is None else f"  budget {r.budget}"
            out.append(f"{indent}{r.glyph} {r.name} [{r.role}]  {r.word}{budget}  {r.model}")
        if snap.needs_you:
            out += ["", "NEEDS YOU"] + [f"  {line}" for _, line in snap.needs_you]
        out += ["", "REQUESTS"]
        reqs = self._requests.requests(snap)
        if reqs:
            for q in reqs[:20]:
                last = f", last activity {fmt_dur(q.last_activity_s * 1000)} ago" if q.last_activity_s is not None else ""
                out.append(f'  "{clip_line(q.title, 40)}" -> {q.assignee}: {q.state}{" (" + q.who + ")" if q.who else ""}; {q.runs_text}{last}')
        else:
            out.append("  none")
        out += ["", "SERVICES"]
        svc = self._services.services(snap)
        if svc:
            for s in svc:
                out.append(f"  {s.owner}/{s.name}  contract v{s.contract_version} playbook v{s.playbook_version}  {s.stats.line()}")
        else:
            out.append("  none")
        if snap.bad_files:
            out += ["", f"UNREADABLE FILES ({len(snap.bad_files)})"] + [f"  {p}: {w}" for p, w in list(snap.bad_files.items())[:5]]
        return "\n".join(out)  # whole lines: this output is read by people and scripts, never cut
