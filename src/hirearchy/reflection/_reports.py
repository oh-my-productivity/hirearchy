"""The listing of the services of an agent, with their record, and the totals of a case."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from ..agents import AgentDirectory
from ..kernel import Message, clip_line
from ..services import Contract, ServiceCatalog, criteria_of
from ._ports import ServicePaths
from .api import Assertion, CaseHistory, ServiceReports, case_spend, confirmed_criteria, regressions, summarize

CLIP_ASSERTION = 160  # characters of the client's words shown for an assertion in the listing


def marked(ids: Sequence[str], current: Collection[str]) -> str:
    """``ids`` joined by commas, each ``C<k>`` that is no longer in the contract (not in ``current``) marked ``(removed)``."""
    return ", ".join(f"{x} (removed)" if x.startswith("C") and x not in current else x for x in ids)


class TextServiceReports(ServiceReports):
    """What a client or an owner reads about the services: contract, playbook and record of each, and how much one case has cost."""

    def __init__(self, agents: AgentDirectory, catalog: ServiceCatalog, history: CaseHistory, paths: ServicePaths) -> None:
        self._agents = agents
        self._catalog = catalog
        self._history = history
        self._paths = paths

    @staticmethod
    def _assertion_line(a: Assertion, current: Collection[str]) -> str:
        if a.link == "confirmed":
            about = f", about {marked(a.about, current)}"
        elif a.link == "none":
            about = ", no lasting rule"
        elif a.link == "unconfirmed":
            about = (
                ", possibly a one-off (not confirmed)" if a.verdict.links == ("none",)
                else f", about {marked(a.verdict.links, current)} (not confirmed)"
            )
        else:
            about = ""
        return f'    {a.id} (case {a.case}{about}): "{clip_line(a.verdict.note, CLIP_ASSERTION)}"'

    def _block(self, c: Contract, *, offered: bool) -> list[str]:
        pb = self._catalog.read_playbook(c.owner, c.name)
        items = self._history.cases(c.owner, c.name)
        criteria = self._catalog.criteria(c.owner, c.name)
        current = {x.id for x in criteria if x.current}
        assertions = regressions(items)
        confirmed = confirmed_criteria(items)
        inputs = ", ".join(f"{i['name']}{'*' if i['required'] else ''}" + (f" ({i['description']})" if i["description"] else "")
                           for i in c.inputs) or "none"
        head = f"- {c.name} (offered by {c.owner}; contract v{c.version}, playbook v{pb.version})" if not offered else \
            f"- {c.name} (contract v{c.version}, playbook v{pb.version}{', locked' if c.locked else ''})"
        lines = [
            f"{head}: {c.description}",
            f"  inputs: {inputs}   (* required)",
            f"  each request: {c.budget} runs; acceptance criteria ({self._paths.rel(c.path)}):" if c.path else "",
            *(f"    {x.id}: {x.text}{' (amendment, not confirmed)' if x.amended and x.id not in confirmed else ''}"
              for x in criteria_of(criteria, c.acceptance)),
            f"  record: {summarize(items).line() if items else 'no requests yet'}",
            *(["  regression list (the client's rejections):"] if assertions else []),
            *(self._assertion_line(a, current) for a in assertions),
        ]
        if pb.version:
            lines.append(f'  playbook v{pb.version} ({pb.revised:%Y-%m-%d}): "{clip_line(pb.reason, 120)}"' if pb.revised else f"  playbook v{pb.version}")
        elif not offered:
            lines.append("  playbook: none yet")
        if offered:
            lines.append(f"  playbook file: {self._paths.playbook_file(c.owner, c.name)}" + ("" if pb.version else " (not written yet)"))
        return [x for x in lines if x]

    def services_text(self, actor: str) -> str:
        actor = self._agents.require(actor)
        asks, offers = self._catalog.requestable_services(actor), self._catalog.owned_services(actor)
        if not asks and not offers:
            return (
                "No services yet. A parent defines a standing service for a direct report with define_service(owner, "
                "name, description, acceptance, deliverable, budget, inputs): the contract. Then request(service, inputs) "
                "asks for it, and feedback(task_id, verdict) tells the owner how it went."
            )
        out: list[str] = []
        if asks:
            out.append("Services you can request (from your direct reports):")
            out += [x for c in asks for x in self._block(c, offered=False)]
        if offers:
            out.append("Services you offer:")
            out += [x for c in offers for x in self._block(c, offered=True)]
        return "\n".join(out)

    def case_total(self, task: Message) -> str:
        known = bool(task.service) and self._agents.exists(task.to)
        c = self._history.case_of(task)
        contract = self._catalog.read_contract(task.to, task.service) if known and task.service else None
        if c is None or contract is None:
            return ""
        text = f"case total: {c.runs} runs used of {c.budget} handed down (contract: {contract.budget} per request)"
        if case_spend(c) > contract.budget:
            text += f". This case now exceeds the per-request budget of {contract.budget}: tell the user."
        return text
