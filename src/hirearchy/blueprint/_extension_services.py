"""The services an extension adds, re-budgets and retires, and the charter lines it adds and takes out (design 5.1, 5.2)."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

from ..kernel import NAME_RE, ROOT, OrgError, norm, parent
from ..services import line_key
from ._added import added_lines, holds_line
from ._extension_form import CRITERIA, KEEPS
from ._extension_org import Reads, read_held, retargeted
from ._shapes import AddedChecker, AddedService, BudgetChange, CharterLine, ServiceRetire
from ._view import cap_of, s, svc_criteria
from .api import Agent, Issue, Role

LINE_MAX = 300
REASON_MAX = 300
NOT_TOP_LEVEL = "{owner} is not an agent of this organization that reports to root: a service is offered by a top-level agent that exists (add the agent in one change and its service in the next)."
SERVICE_OF_OWNER = "{owner} offers `{name}` already"
SERVICE_TWICE = "the service {name} is added twice in this change: requests name the service only, so each name is used once."
BAD_NAME = "invalid service name '{name}': use lowercase letters, digits and dashes (max 32, starting with a letter), e.g. weekly-brief"
CONTINUES = (
    "{name} continues the retired service of {owner}, so its criteria are the retired ones: {criteria}. Repeat them (each with its source), or pick another name."
)
UNREADABLE_COPY = "the retired copy of {name} cannot be read ({error}), so it cannot be defined again now: try again; if it persists, tell the user."
NO_SUCH_SERVICE = "{owner} offers no service called `{name}`. Its services: {known}"
BAD_BUDGET = "budget is the number of runs handed down with each request: a whole number >= 1."
BUDGET_LOW = (
    "{service} of {owner} would get {b} runs per request, but its team after this change needs at least {est} (one pass and one rework): raise the budget."
)
BUDGET_CAP = "{service} of {owner} would get {b} runs per request, above the user's cap of {cap} (the cap is for ONE request)."
BUDGET_SAME = "{service} of {owner} already has a budget of {b} runs per request: this entry changes nothing."
BUDGET_TWICE = "the budget of {service} of {owner} appears twice in this change: give it one entry."
BUDGET_TEAM = (
    "{service} of {owner} runs on {b} runs per request, but the team after this change needs at least {est}: add budgets: "
    "[{{owner: {owner}, service: {service}, budget: {est}}}] to this change (the user sees the new budget in the plan)."
)
BAD_CAP = "budget_runs is a whole number of runs >= 1."
RETIRE_REASON = "say why in reason (1 to " + str(REASON_MAX) + " characters)."
RETIRE_OPEN = "{service} still has {open}: settle them first, then propose this change again"
RETIRE_UNREADABLE = "the record of {service} cannot be read ({error}), so it cannot be retired now: try again; if it persists, tell the user."
RETIRE_TWICE = "{service} of {owner} is retired twice in this change: retire it once."
BAD_LINE = "line is one line of 1 to " + str(LINE_MAX) + " characters of plain text."
LINE_HEADING = "a line cannot open a heading or the frontmatter: it cannot start with '#' or be a '---' line."
LINE_TAG = "a line cannot hold ' [change ' - the tag is the applier's."
LINE_AGENT = "{agent} is not an agent of this organization: a line goes into the charter of an agent that exists, not root's."
LINE_HAS = "the charter of {agent} has this line already (under '## Added by your changes'): this entry changes nothing."
LINE_TWICE = "the line is {what} twice for {agent} in this change."
LINE_NOT_ADDED = (
    "the charter of {agent} has no line like this one under '## Added by your changes': only a line an earlier change added can be taken out."
)
LINE_UNREADABLE = "the charter of {agent} cannot be read ({error}): try again."


def template_for(reads: Reads, title: str) -> Role | None:
    for name in reads.roles.role_names():
        role = reads.roles.get_role(name)
        if role is not None and role.title == title:
            return role
    return None


def team_of(reads: Reads, owner: str, gone: Collection[str], added: Sequence[Agent]) -> list[Agent]:
    """The team of the top-level agent ``owner`` after the extension, parents first: the agents that stay (read from their charters), then the added ones."""
    stay = [a for a in reads.agents.subtree(owner) if a not in gone]
    team: list[Agent] = []
    for addr in stay:
        meta = reads.charters.charter(addr)[0]
        held = read_held(reads.agents, reads.charters, reads.roles, addr)
        kids = [k for k in reads.agents.children(addr) if k not in gone]
        title = str(meta.get("role") or addr)
        kind = str(meta.get("kind") or ("verifier" if held.verifier else "manager" if kids else "author"))
        role = template_for(reads, title)
        a = Agent(addr, addr.rsplit("/", 1)[-1], None if addr == owner else parent(addr), addr, role=title, kind=kind)
        a.template = role
        a.tools, a.workspace, a.inputs = list(held.tools), held.workspace, list(held.inputs)
        a.can_hire, a.max_children, a.children = held.can_hire, held.max_children, list(kids)
        team.append(a)
    mine = [a for a in added if a.addr == owner or a.addr.startswith(owner + "/")]
    by = {a.addr: a for a in team}
    for a in mine:
        if a.parent in by and a.addr not in by[a.parent].children:
            by[a.parent].children.append(a.addr)
    return team + mine


def _top(addr: str) -> str:
    return addr.split("/")[0]


def _existing_owner(reads: Reads, owner: str) -> bool:
    return owner != ROOT and "/" not in owner and reads.agents.exists(owner)


def added_services(
    reads: Reads, entries: Sequence[tuple[int, Mapping[str, object]]], teams: Mapping[str, list[Agent]], cap: int | None, roots: Sequence[Path],
    issues: list[Issue],
) -> list[AddedService]:
    """The ``add_services`` entries read against the organization: each is checked with the rules of today's service definitions over the owner's team
    after the extension."""
    by_owner: dict[str, list[tuple[int, Mapping[str, object]]]] = {}
    seen: set[str] = set()
    for i, e in entries:
        where, owner, name = f"extend.add_services[{i}]", norm(s(e.get("owner"))), s(e.get("name"))
        if not _existing_owner(reads, owner):
            issues.append(Issue("error", where, NOT_TOP_LEVEL.format(owner=owner or "(none)"), "extend-owner"))
        elif not NAME_RE.fullmatch(name):
            issues.append(Issue("error", where, BAD_NAME.format(name=name), "extend-owner"))
        elif name in seen:
            issues.append(Issue("error", where, SERVICE_TWICE.format(name=name), "extend-owner"))
        elif name in reads.services.service_names(owner):
            what, why, how = CRITERIA  # the same refusal as the other changes of an existing service's criteria
            issues.append(Issue("error", where, KEEPS.format(what=what.format(service=name), why=why, how=how), "extend-keeps"))
        else:
            seen.add(name)
            try:
                retired = reads.continued.criteria(owner, name)
            except (OrgError, OSError) as error:
                issues.append(Issue("error", where, UNREADABLE_COPY.format(name=name, error=error), "extend-owner"))
                continue
            if retired is not None and ({line_key(t) for t in svc_criteria(e)} != {line_key(t) for t in retired} or e.get("playbook") is not None):
                issues.append(Issue("error", where, CONTINUES.format(name=name, owner=owner, criteria="; ".join(f'"{c}"' for c in retired)), "extend-owner"))
                continue
            by_owner.setdefault(owner, []).append((i, e))
    found: list[AddedService] = []
    for owner, group in by_owner.items():
        team = teams[owner]
        tops = [a for a in team if a.addr == owner]
        sub: dict[str, object] = {"needs": {"budget_runs": cap} if cap else {}, "services": [dict(e) for _, e in group]}
        est = reads.budgets.estimate(team)["total"]
        made: list[Issue] = []
        reads.rules.check(sub, team, tops, cap, est, reads.org, roots, made)
        issues += retargeted(made, {s(e.get("name")): f"extend.add_services[{i}]" for i, e in group})
        budgets = reads.budgets.service_budgets(sub, team)
        for i, e in group:
            name = s(e.get("name"))
            found.append(AddedService(owner, name, dict(e), f"extend.add_services[{i}]", budgets[name], reads.continued.criteria(owner, name)))
    return found


def rebudgeted(
    reads: Reads, entries: Sequence[tuple[int, Mapping[str, object]]], teams: Mapping[str, list[Agent]], cap: int | None, retiring: Collection[tuple[str, str]],
    issues: list[Issue],
) -> list[BudgetChange]:
    """The ``budgets`` entries read against the organization."""
    found: list[BudgetChange] = []
    for i, e in entries:
        where, owner, service = f"extend.budgets[{i}]", norm(s(e.get("owner"))), s(e.get("service"))
        contract = reads.services.read_contract(owner, service) if _existing_owner(reads, owner) else None
        b = e.get("budget")
        if contract is None:
            known = ", ".join(reads.services.service_names(owner)) if _existing_owner(reads, owner) else "none"
            issues.append(Issue("error", where, NO_SUCH_SERVICE.format(owner=owner, name=service, known=known or "none"), "extend-budget"))
        elif not isinstance(b, int) or isinstance(b, bool) or b < 1:
            issues.append(Issue("error", where, BAD_BUDGET, "extend-budget"))
        elif any(c.owner == owner and c.service == service for c in found):
            issues.append(Issue("error", where, BUDGET_TWICE.format(service=service, owner=owner), "extend-budget"))
        elif b == contract.budget:
            issues.append(Issue("error", where, BUDGET_SAME.format(service=service, owner=owner, b=b), "extend-budget"))
        else:
            est = reads.budgets.estimate(teams[owner])["total"]
            if b < est:
                issues.append(Issue("error", where, BUDGET_LOW.format(service=service, owner=owner, b=b, est=est), "extend-budget"))
            elif cap is not None and b > cap:
                issues.append(Issue("error", where, BUDGET_CAP.format(service=service, owner=owner, b=b, cap=cap), "extend-budget"))
            else:
                found.append(BudgetChange(owner, service, b, contract.budget))
    for owner in teams:
        est = reads.budgets.estimate(teams[owner])["total"]
        for name in reads.services.service_names(owner):
            contract = reads.services.read_contract(owner, name)
            if contract is None or (owner, name) in retiring or any(c.owner == owner and c.service == name for c in found):
                continue
            if any(norm(s(e.get("owner"))) == owner and s(e.get("service")) == name for _, e in entries):
                continue  # its own entry says what is wrong with it
            if contract.budget < est:
                issues.append(Issue("error", "extend.add_agents", BUDGET_TEAM.format(service=name, owner=owner, b=contract.budget, est=est), "extend-budget"))
    return found


def retired_services(reads: Reads, entries: Sequence[tuple[int, Mapping[str, object]]], issues: list[Issue]) -> list[ServiceRetire]:
    """The ``retire_services`` entries read against the organization: the service exists and every delivered request of it has its verdict and every
    rejection its answer (the same precondition root's ``retire_service`` refuses on)."""
    found: list[ServiceRetire] = []
    for i, e in entries:
        where, owner, service, reason = f"extend.retire_services[{i}]", norm(s(e.get("owner"))), s(e.get("service")), s(e.get("reason"))
        if not _existing_owner(reads, owner) or reads.services.read_contract(owner, service) is None:
            known = ", ".join(reads.services.service_names(owner)) if _existing_owner(reads, owner) else "none"
            issues.append(Issue("error", where, NO_SUCH_SERVICE.format(owner=owner or "(none)", name=service, known=known or "none"), "extend-retire-service"))
        elif not 1 <= len(reason) <= REASON_MAX:
            issues.append(Issue("error", where, RETIRE_REASON, "extend-retire-service"))
        elif any(r.owner == owner and r.service == service for r in found):
            issues.append(Issue("error", where, RETIRE_TWICE.format(service=service, owner=owner), "extend-retire-service"))
        else:
            try:
                basis = reads.evidence.amendment_basis(owner, service)
            except (OrgError, OSError) as error:
                issues.append(Issue("error", where, RETIRE_UNREADABLE.format(service=service, error=error), "extend-retire-service"))
                continue
            waiting = [r for r in basis.rejections if not r.answered]
            parts = [f"{len(basis.unrated)} delivered request(s) with no verdict yet" if basis.unrated else "",
                     f"{len(waiting)} rejection(s) with no answer yet" if waiting else ""]
            if basis.unrated or waiting:
                issues.append(Issue("error", where, RETIRE_OPEN.format(service=service, open=" and ".join(p for p in parts if p)), "extend-retire-service"))
            else:
                found.append(ServiceRetire(owner, service, reason))
    return found


def _line_problem(line: object) -> str | None:
    if not isinstance(line, str) or not 1 <= len(line.strip()) <= LINE_MAX or "\n" in line.strip():
        return BAD_LINE
    text = line.strip()
    if text.startswith("#") or text.startswith("---"):
        return LINE_HEADING
    return LINE_TAG if " [change " in text else None


def charter_lines(
    reads: Reads, adding: Sequence[tuple[int, Mapping[str, object]]], removing: Sequence[tuple[int, Mapping[str, object]]], issues: list[Issue],
) -> tuple[list[CharterLine], list[CharterLine]]:
    """The ``add_charter_lines`` and ``remove_charter_lines`` entries read against the charters they change."""
    added: list[CharterLine] = []
    removed: list[CharterLine] = []
    for section, entries, done in (("add_charter_lines", adding, added), ("remove_charter_lines", removing, removed)):
        for i, e in entries:
            where, agent, line = f"extend.{section}[{i}]", norm(s(e.get("agent"))), e.get("line")
            if agent == ROOT or not s(e.get("agent")) or not reads.agents.exists(agent):
                issues.append(Issue("error", where, LINE_AGENT.format(agent=agent if s(e.get("agent")) else "(none)"), "extend-line"))
            elif (problem := _line_problem(line)) is not None:
                issues.append(Issue("error", where, problem, "extend-line"))
            else:
                text = " ".join(str(line).split())
                try:
                    body = reads.charters.charter(agent)[1]
                except (OrgError, OSError) as error:
                    issues.append(Issue("error", where, LINE_UNREADABLE.format(agent=agent, error=error), "extend-line"))
                    continue
                if any(c.agent == agent and line_key(c.line) == line_key(text) for c in done):
                    issues.append(Issue("error", where, LINE_TWICE.format(agent=agent, what="added" if section.startswith("add") else "taken out"), "extend-line"))
                elif section == "add_charter_lines" and holds_line(body, text):
                    issues.append(Issue("error", where, LINE_HAS.format(agent=agent), "extend-line"))
                elif section == "remove_charter_lines":
                    kept = next((x for x in added_lines(body) if line_key(x) == line_key(text)), None)
                    if kept is None:
                        issues.append(Issue("error", where, LINE_NOT_ADDED.format(agent=agent), "extend-line"))
                    else:
                        done.append(CharterLine(agent, kept))
                else:
                    done.append(CharterLine(agent, text))
    return added, removed


def checkers_of(reads: Reads, agents: Sequence[Agent], added_service_names: Mapping[str, Sequence[str]]) -> list[AddedChecker]:
    """The verifiers added under an agent that offers services (those it has, and those this extension adds)."""
    found: list[AddedChecker] = []
    for a in agents:
        owner = a.parent
        if a.kind != "verifier" or owner is None or not reads.agents.exists(owner):
            continue
        names = tuple(dict.fromkeys([*reads.services.service_names(owner), *added_service_names.get(owner, ())]))
        if names:
            found.append(AddedChecker(a.addr, owner, names))
    return found


def cap_issue(needs: Mapping[str, object], issues: list[Issue]) -> int | None:
    """``needs.budget_runs`` of an extension: the user's cap per request, or None (an unusable value is reported)."""
    if needs.get("budget_runs") is not None and cap_of(needs) is None:
        issues.append(Issue("error", "needs.budget_runs", BAD_CAP, "extend-form"))
    return cap_of(needs)


def team_owners(agents: Sequence[Agent], gone: Collection[str], services: Sequence[AddedService]) -> list[str]:
    """The top-level agents whose team the extension changes or whose services it adds to, in order."""
    return list(dict.fromkeys([*(_top(a.addr) for a in agents if a.parent is not None), *(_top(g) for g in gone), *(sv.owner for sv in services)]))
