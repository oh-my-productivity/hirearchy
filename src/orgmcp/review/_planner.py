"""``HealthReviewPlanner``: who is told what in a review (moved from ``review.review`` and ``review._pairs``)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ..agents import AgentDirectory
from ..health import AgentHealth, HealthAnalyzer, OrgHealth
from ..kernel import ROOT, parent
from ..templates import Notices
from ._ports import ReserveCheck, ReviewPlanner, RunTotal
from .api import Note, Review


class HealthReviewPlanner(ReviewPlanner):
    def __init__(self, agents: AgentDirectory, health: HealthAnalyzer, reserve: ReserveCheck, notices: Notices, runs: RunTotal) -> None:
        self._agents = agents
        self._health = health
        self._reserve = reserve
        self._notices = notices
        self._runs = runs

    def plan(self, now: datetime, previous: Mapping[str, list[str]]) -> Review:
        health = self._health.org_health(ROOT, now)
        by_addr = {h.addr: h for h in health.agents}
        result = Review(at=now, runs=self._runs.total(), flagged=len(health.flagged))

        for manager in (a for a in by_addr if self._agents.children(a)):
            pairs = self._pairs(health, by_addr, manager)
            if not pairs:
                continue
            known = [k for k in pairs if k in previous.get(manager, [])]
            new = [k for k in pairs if k not in known]
            why = self._reserve.why_not(manager)
            if why:
                result.skipped[manager] = why
                result.notified[manager] = known  # what it already knew and is still true
            elif new:
                result.notified[manager] = known + new
                result.notes.append(Note(
                    manager, f"health review: {len(new)} new problem(s)",
                    self._notices.review_manager(manager, [pairs[k] for k in new]),
                ))
            else:
                result.notified[manager] = known
        if health.flagged:
            keys, items = [], []
            for h in health.flagged:
                for flag, why in h.flags.items():
                    keys.append(f"{h.addr}:{flag}")
                    items.append(self._notices.review_item(h.addr, flag, why, act=parent(h.addr) == ROOT))
            summary = f"{len(health.agents)} agents, {len(health.flagged)} flagged."
            result.notified[ROOT] = keys
            result.notes.append(Note(
                ROOT, f"health review: {len(health.flagged)} of {len(health.agents)} agents flagged",
                self._notices.review_root(summary, items, result.skipped),
            ))
        result.notified = {k: v for k, v in result.notified.items() if v}
        return result

    def _pairs(self, health: OrgHealth, by_addr: dict[str, AgentHealth], manager: str) -> dict[str, str]:
        """Problems of a manager's direct reports: "agent:flag" -> rendered item. Teams add their worst flag."""
        out: dict[str, str] = {}
        for report in self._agents.children(manager):
            h = by_addr[report]
            for flag, why in h.flags.items():
                out[f"{report}:{flag}"] = self._notices.review_item(report, flag, why)
            worst = health.branches[report].worst_flag
            if worst and worst not in h.flags:  # raised by someone further down the team
                member = next(m for m in health.agents if m.addr.startswith(report + "/") and worst in m.flags)
                out[f"{report}:branch:{worst}"] = self._notices.review_item(member.addr, worst, member.flags[worst], branch=report)
        return out
