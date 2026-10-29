"""``FileBriefSources``: the facts of one brief, read from the files through the existing read ports (design 4.1, 4.3).

The one place that reads the cases, the contracts, the agents, the event log and health, and hands the brief its narrow views (``_views``). It reads human-tier evidence, runtime facts
and root's own tasks; it keeps no lesson, memory, note or report of a team. A record that cannot be read becomes a line of ``Facts.unreadable``."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone

from ..agents import AgentDirectory, CharterReader, RetiredArchive
from ..blueprint import RoleLibrary, is_verifier
from ..eventlog import EventReader
from ..health import HealthAnalyzer
from ..kernel import ROOT, Clock, JsonObject, OrgError, fmt_duration, msg_time, parent, parse_time, stamp_of, verdict_tier
from ..mail import MailboxReader
from ..reflection import (
    Case, CaseRecords, ContractMark, Delivery, ServiceRecord, cost_alarm, judged_cases, lineage_class, quality_thresholds, repeat_alarm, user_approved, user_cost,
)
from ..runs import RunLogReader
from ..services import (
    ServiceCatalog, ServiceEvidence, ServiceHints, ServiceStore, added_words, criterion_sources, line_key, number_criteria, text_tokens,
)
from ..settings import OrgSettings
from ._changes import PLAN_HEADING, ChangeFacts
from ._facts import Facts, proposals_of, writes_of
from ._ports import CharterHistory, ORG, BriefSources, ServiceRetirements
from ._shapes import criteria_key
from ._thresholds import retro_thresholds
from ._texts import day
from ._views import (
    Answering, AgentFact, EffectFacts, EventFacts, FailedCase, HealthFlag, OneOffCase, Occasion, OwnerFacts, Passed, PlaybookFacts, RetiredFact, Said, ServiceAlarms,
    ServiceFact, ServiceFailures, Sourced, SpendFacts, Tracked, WatchState,
)

_STAMP = re.compile(r"-(\d{8}T\d{6})$")
_HEADING = re.compile(r"^## ")
_TAG = re.compile(r" \[change [^\]]+\]$")
ADDED_HEADING = "## Added by your changes"


def criteria_lines(body: str) -> tuple[str, ...]:
    """The non-empty lines of the ``## Acceptance criteria`` section of a task body, up to the next ``## `` heading."""
    lines = body.splitlines()
    start = next((n for n, line in enumerate(lines) if line.strip() == "## Acceptance criteria"), None)
    if start is None:
        return ()
    end = next((n for n in range(start + 1, len(lines)) if _HEADING.match(lines[n])), len(lines))
    return tuple(line.strip() for line in lines[start + 1 : end] if line.strip())


def goal_line(body: str) -> str:
    """The first non-empty line of the ``## Goal`` section of a task body; ``""`` when there is none."""
    lines = body.splitlines()
    start = next((n for n, line in enumerate(lines) if line.strip() == "## Goal"), None)
    return next((line.strip() for line in lines[start + 1 :] if line.strip()), "") if start is not None else ""


def _human(case: Case) -> bool:
    return any(v.tier == "human" for v in case.verdicts)


class FileBriefSources(BriefSources):
    def __init__(
        self, records: CaseRecords, hints: ServiceHints, catalog: ServiceCatalog, store: ServiceStore, evidence: ServiceEvidence, directory: AgentDirectory, charters: CharterReader,
        archive: RetiredArchive, mail: MailboxReader, events: EventReader, health: HealthAnalyzer, roles: RoleLibrary, runs: RunLogReader, settings: OrgSettings,
        history: CharterHistory, retirements: ServiceRetirements, clock: Clock,
    ) -> None:
        self._records, self._hints, self._catalog, self._store, self._evidence = records, hints, catalog, store, evidence
        self._directory, self._charters, self._archive, self._mail, self._events = directory, charters, archive, mail, events
        self._health, self._roles, self._runs, self._settings, self._history, self._retirements, self._clock = health, roles, runs, settings, history, retirements, clock

    # ------------------------------------------------------------------------------------------------------------------------ the start and the verdict count

    def started(self) -> datetime | None:
        found: list[datetime] = []
        try:
            found += [t for m in (*self._mail.received(ROOT), *self._mail.sent(ROOT)) if (t := msg_time(m)) is not None]
            found += [t for addr in self._directory.agents() if (t := self._created(addr)) is not None]
        except (OrgError, OSError):
            pass
        if (t := self._history.org_started()) is not None:
            found.append(t)
        return min(found) if found else None

    def _created(self, addr: str) -> datetime | None:
        try:
            return parse_time(self._charters.charter(addr)[0].get("created"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _first_verdict(delivery: object) -> datetime | None:
        counted = getattr(delivery, "counted", ())
        times = [v.created for v in counted if v.created is not None]
        return min(times) if times else None

    def new_verdicts(self, after: datetime | None) -> int:
        try:
            records = self._records.records()
        except (OrgError, OSError):
            return 0
        return sum(1 for r in records for d in r.deliveries if (first := self._first_verdict(d)) is not None and (after is None or first > after))

    # ------------------------------------------------------------------------------------------------------------------------ the facts

    def read(self, since: datetime | None, after: datetime | None) -> Facts:
        records = self._records.records()
        unreadable = tuple((r.service, r.error) for r in records if r.error)
        records = [r for r in records if not r.error]
        agents = self._directory.agents()
        quality, _ = quality_thresholds(self._settings.config())
        th, _ = retro_thresholds(self._settings.config())
        service_records = [r for r in records if r.service]
        said = tuple(s for r in records for s in self._said(r) if since is None or (s.when is not None and s.when > since))
        passed = tuple(p for r in service_records for p in self._passed(r) if since is None or (p.when is not None and p.when > since))
        windowed = [(r, d) for r in records for d in r.deliveries if (t := self._first_verdict(d)) is not None and (since is None or t > since)]
        accepts = sum(1 for r in records for c in r.cases for v in c.verdicts if v.verdict == "accept" and v.tier == "human" and (since is None or (v.created and v.created > since)))
        ones = next((r for r in records if not r.service), None)
        one_offs = tuple(self._one_off(c) for c in ones.cases) if ones is not None else ()
        sourced, unknown = self._sourced(service_records)
        events = list(self._events.events(since, None))
        oldest = next(iter(self._events.timed()), (None, None))[0]
        facts_events = EventFacts(writes_of(events), oldest)
        tops = [a for a in agents if "/" not in a]
        return Facts(
            verdicts=len(windowed), cases=len({(r.service, d.case) for r, d in windowed}), said=said, accepts=accepts, passed=passed,
            alarms=tuple(ServiceAlarms(r.service, repeat_alarm(r, quality), cost_alarm(r, quality)) for r in service_records),
            one_offs=one_offs, offers=self._offers(tops), estimates={a: self._estimate(a) for a in tops}, flags=self._flags(), last_checks=self._last_checks(agents),
            owners={a: tuple(names) for a in agents if (names := self._catalog.service_names(a))}, sourced=sourced, unknown_sources=unknown,
            proposals=proposals_of(events), oldest_event=oldest, playbooks=tuple(self._playbook(r) for r in service_records), spend=tuple(self._spend(r, since) for r in service_records),
            changes=self._changes(agents, facts_events), tracked=self._tracked(service_records), failures=tuple(f for r in service_records if (f := self._failures(r, th.window_cases))),
            effects=self._effects(after, service_records, {c.id: k for c in one_offs if (k := criteria_key(c.criteria))}), unreadable=unreadable,
        )

    # ------------------------------------------------------------------------------------------------------------------------ D1 to D4

    def _criteria_state(self, record: ServiceRecord) -> tuple[set[str], set[str]]:
        numbered = number_criteria([(c.version, c.defined_by, c.acceptance) for c in record.contracts])
        return {c.id for c in numbered if c.current}, {c.id for c in numbered if not c.current}

    def _said(self, record: ServiceRecord) -> Iterable[Said]:
        current, gone = self._criteria_state(record)
        questions: dict[str, str] = {}
        if record.service:
            try:
                questions = {x.assertion: x.question for x in self._evidence.amendment_basis(record.owner, record.service).rejections}
            except (OrgError, OSError):
                pass
        answers = {m.answers: m for m in record.timeline if isinstance(m, ContractMark) and m.basis == "answers"}
        for a in record.assertions:
            links = a.verdict.links if a.verdict.links_tier == "human" else ()
            mark = answers.get(a.id)
            yield Said(
                record.service, a.id, a.case, a.verdict.created, self._hints.feedback_text(a.verdict.message), a.link, a.about,
                next((x for x in links if x.startswith("R")), ""), Answering(mark.version, mark.adds, mark.removes) if mark is not None else None,
                tuple(x for x in a.about if x in current), tuple(x for x in a.about if x in gone), record.owner, a.verdict.message.id, a.verdict.task_id, questions.get(a.id, ""),
            )

    def _is_check(self, addr: str) -> bool:
        try:
            return is_verifier(self._charters.charter(addr)[0], self._roles)
        except (OSError, ValueError):
            return False

    def _passed(self, record: ServiceRecord) -> Iterable[Passed]:
        by_verdict = {a.verdict.message.id: a for a in record.assertions}
        for delivery, cause in record.escapes:
            verdict = delivery.decisive
            if verdict is None:
                continue
            a = by_verdict.get(verdict.message.id)
            yield Passed(
                record.service, delivery.case, delivery.task.id, delivery.signer, self._is_check(delivery.signer), (a.id,) if a else (), a.about if a else (), cause.type,
                cause.also, verdict.created, self._hints.feedback_text(verdict.message),
            )

    # ------------------------------------------------------------------------------------------------------------------------ D5, the signals' inputs

    @staticmethod
    def _one_off(case: Case) -> OneOffCase:
        head = case.tasks[0]
        return OneOffCase(case.id, case.owner, case.title, criteria_lines(head.body), goal_line(head.body), msg_time(head), _human(case), case.runs, case.runs_unknown)

    def _offers(self, tops: Sequence[str]) -> dict[str, frozenset[tuple[str, ...]]]:
        out: dict[str, frozenset[tuple[str, ...]]] = {}
        for owner in tops:
            keys = {criteria_key(c.acceptance) for name in self._catalog.service_names(owner) if (c := self._catalog.read_contract(owner, name)) is not None}
            if keys:
                out[owner] = frozenset(keys)
        return out

    def _runs_of(self, addr: str) -> int:
        try:
            title = str(self._charters.charter(addr)[0].get("role") or "")
        except (OSError, ValueError):
            title = ""
        for name in self._roles.role_names():
            role = self._roles.get_role(name)
            if role is not None and role.title == title:
                return role.base_runs
        return 2  # a custom charter counts 2

    def _estimate(self, owner: str) -> int:
        """The runs one pass and one rework cycle of the team of ``owner`` need (the blueprint's rule): a manager 2 + its reports + 2, a worker its template's ``base_runs`` + 1."""
        total = 0
        for addr in self._directory.subtree(owner):
            kids = len(self._directory.children(addr))
            total += 2 + kids + 2 if kids else self._runs_of(addr) + 1
        return total

    def _flags(self) -> tuple[HealthFlag, ...]:
        try:
            health = self._health.org_health()
        except (OrgError, OSError):
            return ()
        return tuple(
            HealthFlag(a.addr, flag, a.flags[flag], a.budget_left, fmt_duration(a.since_activity)) for a in health.agents for flag in ("idle", "stranded_budget") if flag in a.flags
        )

    def _last_checks(self, agents: Sequence[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for owner in agents:
            for name in self._catalog.service_names(owner):
                checks = [a for a in self._directory.subtree(owner) if a != owner and self._is_check(a)]
                if len(checks) == 1:
                    out[checks[0]] = name
        return out

    # ------------------------------------------------------------------------------------------------------------------------ 7.2: concentrated failures

    def _rework_runs(self, case: Case, first: datetime | None) -> int | None:
        """The runs of the owner's subtree after the first rejection of the case, up to its final result (or now); None when the case's runs cannot be read."""
        if case.runs_unknown or first is None:
            return None
        end = case.finished or self._clock.now()
        total = 0
        for addr in self._directory.subtree(case.owner):
            total += sum(1 for f in self._runs.files(addr) if f.start is not None and first < f.start <= end)
        return total

    def _owner_facts(self, record: ServiceRecord) -> OwnerFacts:
        owner = record.owner
        meta, _ = self._charters.charter(owner)
        max_children = meta.get("max_children")
        titles = {r.title: n for n in self._roles.role_names() if (r := self._roles.get_role(n)) is not None and r.kind == "verifier"}
        team = [a for a in self._directory.subtree(owner) if a != owner]
        template = next((titles[str(self._charters.charter(a)[0].get("role"))] for a in team if self._is_check(a) and str(self._charters.charter(a)[0].get("role")) in titles), "")
        runs = tuple((n, r.base_runs) for n in self._roles.role_names() if (r := self._roles.get_role(n)) is not None)
        tools = meta.get("tools")
        others = tuple(
            (name, c.budget) for name in self._catalog.service_names(owner) if name != record.service and (c := self._catalog.read_contract(owner, name)) is not None
        )
        return OwnerFacts(
            owner, len(self._directory.children(owner)), max_children if isinstance(max_children, int) and not isinstance(max_children, bool) else 5, bool(meta.get("can_hire")),
            tuple(str(t) for t in tools) if isinstance(tools, list) else (), self._estimate(owner), record.budget, template, runs, others,
        )

    def _failures(self, record: ServiceRecord, window: int) -> ServiceFailures | None:
        judged = judged_cases(record)[-window:]
        escapes: dict[str, list[Delivery]] = {}
        for delivery, _ in record.escapes:
            escapes.setdefault(delivery.case, []).append(delivery)
        by_verdict = {a.verdict.message.id: a for a in record.assertions}
        failed: list[FailedCase] = []
        for case in judged:
            found = escapes.get(case.id, [])
            if not found:
                continue
            classes: list[frozenset[str]] = []
            for d in found:
                a = by_verdict.get(d.decisive.message.id) if d.decisive is not None else None
                if a is not None and a.link == "confirmed" and a.verdict.created is not None:
                    classes += [lineage_class(record.contracts, cid, a.verdict.created) for cid in a.about]
            first = found[0]
            failed.append(FailedCase(
                case.id, first.decisive.created if first.decisive else None, tuple(classes), first.signer, self._is_check(first.signer), True,
                self._rework_runs(case, first.decisive.created if first.decisive else None),
            ))
        if not failed:
            return None
        criteria = {c.id: c.text for c in self._catalog.criteria(record.owner, record.service)}
        return ServiceFailures(record.service, record.owner, tuple(failed), len(judged), criteria, self._owner_facts(record))

    # ------------------------------------------------------------------------------------------------------------------------ D9, D11, D12

    def _sourced(self, records: Sequence[ServiceRecord]) -> tuple[tuple[Sourced, ...], int]:
        rows: list[Sourced] = []
        unknown = 0
        for r in records:
            try:
                sources = criterion_sources(self._store, r.owner, r.service)
                criteria = [c for c in self._catalog.criteria(r.owner, r.service) if c.current]
            except (OrgError, OSError):
                continue
            judged = [d for d in r.deliveries if d.judged and d.task.contract is not None]
            for c in criteria:
                source = sources.get(c.id)
                if source is None or source.kind == "unknown":
                    unknown += 1
                    continue
                mine = [d for d in judged if (d.task.contract or 0) >= c.since]
                added = added_words(c.text, source.quote, source.asked) if source.kind in ("user", "amendment") else ()
                dates = ", ".join(day(stamp_of(t)) for t in source.tasks) if source.kind == "tasks" else ""
                rows.append(Sourced(r.service, c.id, c.text, source.kind, source.quote, source.asked, dates, added, len(mine), sum(d.outcome == "accepted" for d in mine)))
        return tuple(rows), unknown

    def _playbook(self, record: ServiceRecord) -> PlaybookFacts:
        playbook = self._catalog.read_playbook(record.owner, record.service)
        cap = int(self._settings.number("playbook_max_words", int))
        states: dict[str, int] = {}
        for w in record.watch:
            if w.state != "retired":
                states[w.state] = states.get(w.state, 0) + 1
        current = [c for c in self._catalog.criteria(record.owner, record.service) if c.current]
        keys = {tuple(text_tokens(c.text)) for c in current}
        mirrors = [i for i in (playbook.items or ()) if tuple(text_tokens(i.text)) in keys]
        return PlaybookFacts(record.service, len(playbook.body.split()), cap, tuple(sorted(states.items())), (), tuple(i.id for i in mirrors), sum(len(i.text.split()) for i in mirrors))

    @staticmethod
    def _spend(record: ServiceRecord, since: datetime | None) -> SpendFacts:
        cases = [c for c in record.cases if since is None or (c.started is not None and c.started > since)]
        above = sum(1 for c in cases if user_cost(c) > user_approved(c, record.budget))
        return SpendFacts(record.service, len(cases), sum(c.runs for c in cases), record.budget, above)

    # ------------------------------------------------------------------------------------------------------------------------ D7 and D8

    def _tracked(self, records: Sequence[ServiceRecord]) -> tuple[Tracked, ...]:
        found: list[Tracked] = []
        for r in records:
            for m in r.timeline:
                if isinstance(m, ContractMark) and m.basis != "first" and m.adds and m.when is not None:
                    targets = [lineage_class(r.contracts, cid, m.when) for cid in m.adds]
                    exercised = tuple(Occasion(d.case, "", d.decisive.created if d.decisive else None) for d in r.deliveries if d.judged and (d.task.contract or 0) >= m.version)
                    again = tuple(
                        Occasion(a.case, a.id, a.verdict.created, a.verdict.tier) for a in r.assertions
                        if a.verdict.created and a.verdict.created > m.when and a.link != "none"
                        and any(lineage_class(r.contracts, c, a.verdict.created) & t for c in a.about for t in targets)
                    )
                    found.append(Tracked(f"{r.service} contract v{m.version} adds {', '.join(m.adds)}", "amendment", m.when, True, exercised, again))
            for w in r.watch:
                if w.k:
                    found.append(Tracked(f"{r.service} {w.id} (v{w.text_version})", "playbook", w.watch_start, True, watch=WatchState(w.state, w.k, w.clean, w.related)))
        return tuple(found)

    def _agent_fact(self, addr: str) -> AgentFact | None:
        try:
            meta, body = self._charters.charter(addr)
        except (OSError, ValueError):
            return None
        return AgentFact(
            addr, parse_time(meta.get("created")), str(meta.get("hired_by") or ""), str(meta.get("approved_in") or ""), str(meta.get("kind") or ""), PLAN_HEADING in body,
            is_verifier(meta, self._roles),
        )

    def _changes(self, agents: Sequence[str], events: EventFacts) -> ChangeFacts:
        facts = [f for addr in agents if (f := self._agent_fact(addr)) is not None]
        retired: list[RetiredFact] = []
        for tree in self._archive.trees():
            record = self._archive.record(tree)
            stamp = _STAMP.search(tree.name)
            when = parse_time(record.get("retired")) or (datetime.strptime(stamp.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc) if stamp else None)
            retired.append(RetiredFact(tree.addr, when, record.get("by", ""), record.get("reason", ""), record.get("approved_in", ""), bool(record)))
        services: list[ServiceFact] = []
        for owner in agents:
            for name in self._catalog.service_names(owner):
                versions = self._store.versions(owner, name, "SERVICE")
                meta: JsonObject = versions[0][1] if versions else {}
                services.append(ServiceFact(owner, name, parse_time(meta.get("created")), str(meta.get("defined_by") or ""), str(meta.get("approved_in") or "")))
        versions_read = self._history.versions(agents)
        subjects = {p.commit: s for p in versions_read.pairs if p.path == ORG and (s := self._history.subject(p.commit))}
        return ChangeFacts(tuple(facts), tuple(retired), tuple(services), self._retirements.retired(), versions_read, subjects, events)

    # ------------------------------------------------------------------------------------------------------------------------ the effects of the last brief's items

    def _added_lines(self, body: str) -> list[str]:
        lines = body.splitlines()
        start = next((n for n, line in enumerate(lines) if line.strip() == ADDED_HEADING), None)
        if start is None:
            return []
        end = next((n for n in range(start + 1, len(lines)) if _HEADING.match(lines[n])), len(lines))
        return [x.strip() for x in lines[start + 1 : end] if x.strip()]

    @staticmethod
    def _later(when: datetime | None, after: datetime | None) -> bool:
        return when is not None and (after is None or when > after)

    def _answers(self, records: Sequence[ServiceRecord], after: datetime | None) -> tuple[frozenset[str], frozenset[str]]:
        """The rejections answered after ``after`` (an answering version or a human link of the user), and the criteria settled after it as ``service/C`` (a version that
        removes or replaces one, or a human link that names it). A rejection counts as answered only when no rejection with the same number, of another service, still waits."""
        answered: set[str] = set()
        waiting: set[str] = set()
        clarified: set[str] = set()
        for r in records:
            for a in r.assertions:
                mark = next((m for m in r.timeline if isinstance(m, ContractMark) and m.basis == "answers" and m.answers == a.verdict.message.id), None)
                links = [msg_time(n) for n in a.verdict.link_notes if verdict_tier(n) == "human"]
                if not links and mark is None:
                    waiting.add(a.id)
                elif any(self._later(t, after) for t in (*links, mark.when if mark is not None else None)):
                    answered.add(a.id)
                if any(self._later(t, after) for t in links):
                    clarified |= {f"{r.service}/{c}" for c in a.verdict.confirmed}
            for m in r.timeline:
                if isinstance(m, ContractMark) and m.basis != "first" and self._later(m.when, after):
                    clarified |= {f"{r.service}/{c}" for c in m.removes}
        return frozenset(answered - waiting), frozenset(clarified)

    def _reclaimed(self, addrs: Sequence[str], after: datetime | None) -> frozenset[str]:
        """The agents that gave runs back to their parent after ``after``: a note from the agent to its parent that carries budget (a reclaim writes one on its behalf)."""
        found: set[str] = set()
        for addr in addrs:
            try:
                sent = self._mail.sent(addr)
            except (OrgError, OSError):
                continue
            if any(m.type == "note" and m.budget > 0 and m.to == parent(addr) and self._later(msg_time(m), after) for m in sent):
                found.add(addr)
        return frozenset(found)

    def _effects(self, after: datetime | None, records: Sequence[ServiceRecord] = (), shapes: Mapping[str, tuple[str, ...]] | None = None) -> EffectFacts:
        addrs = self._directory.agents()
        answered, clarified = self._answers(records, after)
        agents = [f for addr in addrs if (f := self._agent_fact(addr)) is not None]
        made = [f for f in agents if f.approved_in.startswith("change ") and (after is None or (f.created is not None and f.created > after))]
        lines: set[str] = set()
        for addr in addrs:
            try:
                lines |= {f"{addr}|{line_key(_untagged(x))}" for x in self._added_lines(self._charters.charter(addr)[1])}
            except (OSError, ValueError):
                continue
        services: set[str] = set()
        defined: list[tuple[str, str, tuple[str, ...]]] = []
        for owner in addrs:
            for name in self._catalog.service_names(owner):
                versions = self._store.versions(owner, name, "SERVICE")
                if versions and str(versions[0][1].get("approved_in") or "").startswith("change "):
                    services.add(f"{owner}/{name}")
                    first = versions[0][1].get("acceptance")
                    defined.append((owner, name, criteria_key([str(x) for x in first] if isinstance(first, list) else [])))
        checkers = frozenset(f.addr.rsplit("/", 1)[0] if "/" in f.addr else ROOT for f in made if f.verifier)
        return EffectFacts(
            services=frozenset(services), defined=tuple(defined), shapes=dict(shapes or {}), checkers=checkers, lines=frozenset(lines), workers=frozenset(f.addr.rsplit("/", 1)[0] for f in made if "/" in f.addr),
            retired=frozenset(t.addr for t in self._archive.trees()), reclaimed=self._reclaimed(addrs, after), clarified=clarified, answered=answered,
        )


def _untagged(line: str) -> str:
    """The text of a line of the added section without its bullet and its ``[change ...]`` tag."""
    text = _TAG.sub("", line.strip())
    return text[2:] if text.startswith("- ") else text
