"""The listing of the services of an agent, with their record, and the totals of a case."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from ..agents import AgentDirectory
from ..kernel import Message, clip_line
from ..services import Contract, Criterion, ServiceCatalog, confirmed_amendments, criteria_of
from ._ports import ServicePaths
from .api import (
    Assertion, CaseHistory, ServiceReports, case_spend, confirmed_criteria, regressions, summarize, user_approved, user_cost,
)

CLIP_ASSERTION = 160  # characters of the client's words shown for an assertion in the listing

# The texts of ``case_total`` (design 4.4). ``{s}``, ``{has}``, ``{it}``, ``{its}`` and ``{Its}`` are the singular or plural of the relayed reworks' ids.
HEAD = "case total: {runs} runs used of {budget} handed down (contract: {B} per request)"
HEAD_SPLIT = (
    "case total: {runs} runs used: {user} by the user's requests, {relayed} by your relayed rework{s} {ids}; {budget} handed down "
    "(contract: {B} per request)"
)
OVER_CONTRACT = "This case now exceeds the per-request budget of {B}: tell the user."
OVER_APPROVED = (  # DR-0a3-11: ``topped`` is ", plus {A - B} approved beyond it" when the approval is above the contract's budget
    "The user's requests now cost {U} runs, more than the {A} the user approved for this case (contract: {B} per request{topped}): tell the user."
)
RELAYED_SPEND = (
    "The runs of your relayed rework{s} are your own spend, not the user's: report them to the user as yours, and never ask the user to fund them."
)
RELAYED_NONE_YET = (
    "Your relayed rework{s} {ids} {has} used no run yet; {its} runs will be your own spend, not the user's: report them to the user as yours, "
    "and never ask the user to fund them."
)
RELAYED_UNSPLIT = (  # DR-0a3-1, P-2: the relayed rework's runs fell in the interval of a later request of the user's
    "Your relayed rework{s} {ids} {has} no run counted apart: a request of the user's followed before {it} finished, so {its} runs could not be "
    "split from the user's interval, which holds {n} run(s) since then, all counted with the user's requests. {Its} runs are your own spend, not "
    "the user's: report them to the user as yours, and never ask the user to fund them."
)


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

    @staticmethod
    def _mark(x: Criterion, eligible: Collection[str]) -> str:
        """What the listing says of a criterion that is an amendment: the user's own request never admits a revision; the others wait for the yes."""
        if not x.amended:
            return ""
        if x.user:
            return " (amendment, user-initiated: never admits a playbook revision)"
        return "" if x.id in eligible else " (amendment, not confirmed)"

    def _block(self, c: Contract, *, offered: bool) -> list[str]:
        pb = self._catalog.read_playbook(c.owner, c.name)
        items = self._history.cases(c.owner, c.name)
        criteria = self._catalog.criteria(c.owner, c.name)
        current = {x.id for x in criteria if x.current}
        assertions = regressions(items)
        eligible = {x.id for x in confirmed_amendments(criteria, confirmed_criteria(items, criteria))}  # the amendments rule (c) admits
        inputs = ", ".join(f"{i['name']}{'*' if i['required'] else ''}" + (f" ({i['description']})" if i["description"] else "")
                           for i in c.inputs) or "none"
        head = f"- {c.name} (offered by {c.owner}; contract v{c.version}, playbook v{pb.version})" if not offered else \
            f"- {c.name} (contract v{c.version}, playbook v{pb.version}{', locked' if c.locked else ''})"
        lines = [
            f"{head}: {c.description}",
            f"  inputs: {inputs}   (* required)",
            f"  each request: {c.budget} runs; acceptance criteria ({self._paths.rel(c.path)}):" if c.path else "",
            *(f"    {x.id}: {x.text}{self._mark(x, eligible)}" for x in criteria_of(criteria, c.acceptance)),
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
        budget = contract.budget
        if c.client_kind == "agent":  # an agent client's case reads as before 0a.3, whatever its relayed reworks (I6)
            text = HEAD.format(runs=c.runs, budget=c.budget, B=budget)
            return f"{text}. {OVER_CONTRACT.format(B=budget)}" if case_spend(c) > budget else text
        relayed = [t.id for t in c.tasks if t.source == "relayed"]
        approved, cost = user_approved(c, budget), user_cost(c)
        several = len(relayed) > 1
        words = {
            "s": "s" if several else "", "has": "have" if several else "has", "it": "they" if several else "it",
            "its": "their" if several else "its", "Its": "Their" if several else "Its", "ids": ", ".join(relayed),
        }
        if c.relayed_runs >= 1:
            head = HEAD_SPLIT.format(runs=c.runs, user=c.runs - c.relayed_runs, relayed=c.relayed_runs, budget=c.budget, B=budget, **words)
        else:
            head = HEAD.format(runs=c.runs, budget=c.budget, B=budget)
        sentences: list[str] = []
        if cost > approved:
            if approved == budget and not relayed:
                sentences.append(OVER_CONTRACT.format(B=budget))  # today's sentence, today's bytes
            else:
                topped = f", plus {approved - budget} approved beyond it" if approved > budget else ""
                sentences.append(OVER_APPROVED.format(U=cost, A=approved, B=budget, topped=topped))
        if relayed:
            if c.relayed_runs >= 1:
                sentences.append(RELAYED_SPEND.format(**words))
            elif c.relayed_overlap > 0:
                sentences.append(RELAYED_UNSPLIT.format(n=c.unsplit_runs, **words))
            else:
                sentences.append(RELAYED_NONE_YET.format(**words))
        return head + "".join(". " + x if i == 0 else " " + x for i, x in enumerate(sentences))
