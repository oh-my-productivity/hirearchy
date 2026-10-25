"""``DerivedCaseRecords``: the records of the cases for the quality view and for health (design 12.1, 13, 4.3, 10).

The organization is the services world of ``reflection.testing`` (memory or disk); a collaborator that must fail is a small subclass of its port that
raises what the test names. A YAML error is produced through ``kernel.split_frontmatter`` (PyYAML is imported by ``kernel`` and ``blueprint`` only)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import ROOT, JsonObject, Message, OrgError, msg_time, split_frontmatter
from hirearchy.reflection import (
    BarChanges, Case, CaseHistory, CharterMark, DeliverableChecks, DeliverableFinding, ModelMark, ServiceRecord, TopUpMark,
)
from hirearchy.mail import MailboxReader
from hirearchy.reflection._ports import ContractVersions
from hirearchy.reflection._records import DerivedCaseRecords
from hirearchy.reflection.testing import FixedBarHistory, FixedDeliverableChecks, NoBarHistory, ReflectionWorld, fs_world, memory_world
from hirearchy.services import Criterion, Playbook, ServiceCatalog
from hirearchy.services.api import Contract

from ._support import SERVICE, ask, define, deliver, nested, note_on, populated, rate, revise, rework

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
CONTRACT_PATH = f"ceo/services/{SERVICE}/SERVICE.md"
BAD_YAML = "---\nkey: [unclosed\n---\n"


def yaml_error() -> Exception:
    """The exception a frontmatter that does not parse raises (from ``kernel``, the one place that imports PyYAML)."""
    try:
        split_frontmatter(BAD_YAML)
    except Exception as exc:  # noqa: BLE001 - this is how the test obtains the library's exception
        return exc
    raise AssertionError("the frontmatter parsed")


def micros(moment: datetime | None) -> int:
    assert moment is not None
    return (moment - EPOCH) // timedelta(microseconds=1)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


# ------------------------------------------------------------------------------------------------------------------------ collaborators that fail


class BreakingCatalog(ServiceCatalog):
    """A catalog that raises ``raises[method]`` when that method is called, and answers like ``inner`` otherwise."""

    def __init__(self, inner: ServiceCatalog, raises: Mapping[str, BaseException]) -> None:
        self._inner = inner
        self._raises = raises
        self.calls: list[str] = []

    def _go(self, method: str, *args: str) -> object:
        self.calls.append(method)
        if method in self._raises:
            raise self._raises[method]
        return getattr(self._inner, method)(*args)

    def service_names(self, addr: str) -> list[str]:
        return self._go("service_names", addr)  # type: ignore[return-value]

    def read_contract(self, owner: str, name: str) -> Contract | None:
        return self._go("read_contract", owner, name)  # type: ignore[return-value]

    def read_playbook(self, owner: str, name: str) -> Playbook:
        return self._go("read_playbook", owner, name)  # type: ignore[return-value]

    def owned_services(self, owner: str) -> list[Contract]:
        return self._go("owned_services", owner)  # type: ignore[return-value]

    def requestable_services(self, actor: str) -> list[Contract]:
        return self._go("requestable_services", actor)  # type: ignore[return-value]

    def criteria(self, owner: str, name: str) -> list[Criterion]:
        return self._go("criteria", owner, name)  # type: ignore[return-value]

    def playbook_versions(self, owner: str, name: str) -> list[Playbook]:
        return self._go("playbook_versions", owner, name)  # type: ignore[return-value]


class BreakingHistory(CaseHistory):
    """A case history that raises ``raises[method]`` and otherwise answers like ``inner``; ``calls`` keep what it was asked, with the keywords."""

    def __init__(self, inner: CaseHistory, raises: Mapping[str, BaseException] | None = None, chains: list[Case] | None = None) -> None:
        self._inner = inner
        self._raises = raises or {}
        self._chains = chains  # the chains to answer instead of the inner history's
        self.calls: list[tuple[str, dict[str, object]]] = []

    def cases(self, owner: str, service: str) -> list[Case]:
        return self._inner.cases(owner, service)

    def chains(self, owner: str, service: str, *, since: datetime | None, runs: bool) -> list[Case]:
        self.calls.append(("chains", {"since": since, "runs": runs}))
        if "chains" in self._raises:
            raise self._raises["chains"]
        return self._inner.chains(owner, service, since=since, runs=runs) if self._chains is None else self._chains

    def one_off_cases(self, *, runs: bool = True) -> list[Case]:
        self.calls.append(("one_off_cases", {"runs": runs}))
        if "one_off_cases" in self._raises:
            raise self._raises["one_off_cases"]
        return self._inner.one_off_cases(runs=runs)

    def case_of(self, task: Message) -> Case | None:
        return self._inner.case_of(task)

    def playbook_timeline(self, owner: str, service: str) -> list[tuple[int, datetime]]:
        return self._inner.playbook_timeline(owner, service)


class BreakingVersions(ContractVersions):
    def __init__(self, inner: ContractVersions, raises: BaseException | None = None) -> None:
        self._inner = inner
        self._raises = raises

    def versions(self, owner: str, name: str, kind: str) -> list[tuple[int, JsonObject, str]]:
        if self._raises is not None:
            raise self._raises
        return self._inner.versions(owner, name, kind)


class UnreadableMail(MailboxReader):
    """A mailbox reader whose received boxes cannot be read."""

    def __init__(self, inner: MailboxReader) -> None:
        self._inner = inner

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        return self._inner.messages(addr, *boxes)

    def received(self, addr: str) -> list[Message]:
        raise OSError(5, "I/O error")

    def sent(self, addr: str) -> list[Message]:
        return self._inner.sent(addr)

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        return self._inner.find_received(addr, msg_id)

    def find_anywhere(self, addr: str, msg_id: str) -> Message | None:
        return self._inner.find_anywhere(addr, msg_id)

    def unread(self, addr: str) -> int:
        return self._inner.unread(addr)

    def has_inflight(self, addr: str) -> bool:
        return self._inner.has_inflight(addr)


class CountingChecks(DeliverableChecks):
    """Fixed findings, with the calls it was asked and an exception it can raise instead."""

    def __init__(self, findings: Sequence[DeliverableFinding] = (), raises: BaseException | None = None) -> None:
        self._fixed = FixedDeliverableChecks({ROOT: list(findings)})
        self._raises = raises
        self.calls: list[tuple[str, str | None, bool]] = []

    def findings(self, actor: str, service: str | None = None, *, settled: bool = False) -> list[DeliverableFinding]:
        self.calls.append((actor, service, settled))
        if self._raises is not None:
            raise self._raises
        return self._fixed.findings(actor, service, settled=settled)


def records_of(
    w: ReflectionWorld, *, catalog: ServiceCatalog | None = None, history: CaseHistory | None = None, versions: ContractVersions | None = None,
    bars: FixedBarHistory | NoBarHistory | None = None, checks: DeliverableChecks | None = None,
) -> DerivedCaseRecords:
    return DerivedCaseRecords(
        history or w.history, catalog or w.s.catalog, w.s.d.agents, w.s.d.mail, versions or w.s.store, bars or NoBarHistory(), checks or CountingChecks(),
    )


def only(found: list[ServiceRecord], service: str = SERVICE) -> ServiceRecord:
    (record,) = [r for r in found if r.service == service]
    return record


def one_off(found: list[ServiceRecord]) -> ServiceRecord:
    return only(found, "")


# ------------------------------------------------------------------------------------------------------------------------ the read helper (DR3-4)


def test_a_yaml_error_reads_does_not_parse_with_its_type(w: ReflectionWorld) -> None:
    define(w)
    exc = yaml_error()
    catalog = BreakingCatalog(w.s.catalog, {"read_contract": exc})
    record = only(records_of(w, catalog=catalog).records())
    assert record.error == f"SERVICE.md: does not parse ({type(exc).__name__})"


def test_a_unicode_decode_error_reads_is_not_utf8(w: ReflectionWorld) -> None:
    define(w)
    catalog = BreakingCatalog(w.s.catalog, {"read_contract": UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")})
    assert only(records_of(w, catalog=catalog).records()).error == "SERVICE.md: is not UTF-8"


def test_any_other_exception_reads_cannot_be_read_with_its_type_and_words(w: ReflectionWorld) -> None:
    define(w)
    catalog = BreakingCatalog(w.s.catalog, {"read_contract": RuntimeError("boom\n  inside")})
    assert only(records_of(w, catalog=catalog).records()).error == "SERVICE.md: cannot be read (RuntimeError: boom inside)"


def test_an_org_error_or_os_error_reads_its_own_words(w: ReflectionWorld) -> None:
    define(w)
    org = BreakingCatalog(w.s.catalog, {"read_contract": OrgError("the contract is locked")})
    assert only(records_of(w, catalog=org).records()).error == "SERVICE.md: the contract is locked"
    long = BreakingCatalog(w.s.catalog, {"read_contract": PermissionError(13, "Permission denied " + "x" * 300)})
    error = only(records_of(w, catalog=long).records()).error
    assert error.startswith("SERVICE.md: [Errno 13] Permission denied xxx") and len(error) <= len("SERVICE.md: ") + 200  # the words are clipped


# ------------------------------------------------------------------------------------------------------------------------ what a read that fails does (DR3-5, 13)


def test_a_service_md_read_that_does_not_parse_sets_the_record_error(w: ReflectionWorld) -> None:
    define(w)
    define(w, "ops", "other-brief")
    w.s.put(CONTRACT_PATH, BAD_YAML)  # a real file whose frontmatter does not parse
    found = records_of(w).records()
    assert only(found).error.startswith("SERVICE.md: does not parse (")
    assert only(found, "other-brief").error == "" and only(found, "other-brief").contract == 1  # the other records build


def test_a_stored_version_that_does_not_parse_sets_the_record_error(w: ReflectionWorld) -> None:
    define(w)
    exc = yaml_error()
    record = only(records_of(w, versions=BreakingVersions(w.s.store, exc)).records())
    assert record.error == f"the stored contract versions: does not parse ({type(exc).__name__})"
    assert (record.cases, record.deliveries, record.timeline, record.contract) == ((), (), (), 0)  # the heading only


def test_a_criteria_read_that_raises_sets_the_record_error_labelled_the_criteria(w: ReflectionWorld) -> None:
    define(w)
    catalog = BreakingCatalog(w.s.catalog, {"criteria": RuntimeError("bad")})
    assert only(records_of(w, catalog=catalog).records()).error == "the criteria: cannot be read (RuntimeError: bad)"


def test_a_playbook_versions_read_that_raises_sets_the_record_error(w: ReflectionWorld) -> None:
    define(w)
    catalog = BreakingCatalog(w.s.catalog, {"playbook_versions": yaml_error()})
    assert only(records_of(w, catalog=catalog).records()).error.startswith("the playbook versions: does not parse (")


def test_a_cases_read_that_raises_sets_the_record_error_labelled_the_cases(w: ReflectionWorld) -> None:
    define(w)
    history = BreakingHistory(w.history, {"chains": OSError(5, "I/O error")})
    found = records_of(w, history=history).records()
    assert only(found).error == "the cases: [Errno 5] I/O error"
    assert one_off(found).error == ""  # the one-off record has its own read


def test_a_one_off_cases_read_that_raises_sets_the_one_off_record_error(w: ReflectionWorld) -> None:
    define(w)
    history = BreakingHistory(w.history, {"one_off_cases": RuntimeError("bad")})
    found = records_of(w, history=history).records()
    assert one_off(found).error == "the cases: cannot be read (RuntimeError: bad)"
    assert (one_off(found).service, one_off(found).owner, one_off(found).client, one_off(found).client_kind) == ("", "", ROOT, "human")
    assert only(found).error == ""


def test_records_list_services_by_name_without_parsing_a_contract(w: ReflectionWorld) -> None:
    define(w)
    define(w, "ops", "other-brief")
    catalog = BreakingCatalog(w.s.catalog, {"read_contract": yaml_error()})
    found = records_of(w, catalog=catalog).records()
    assert sorted(r.service for r in found) == ["", "other-brief", SERVICE]  # listed by name; both then fail to be read, and both are records
    assert all(r.error for r in found if r.service)
    assert "service_names" in catalog.calls and "owned_services" not in catalog.calls


def test_a_mailbox_that_cannot_be_read_sets_the_record_error_and_makes_deliveries_raise(w: ReflectionWorld) -> None:
    define(w)
    deliver(w, ask(w))
    assert only(records_of(w).records()).error == ""  # the control: with a readable mailbox the record builds
    records = DerivedCaseRecords(w.history, w.s.catalog, w.s.d.agents, UnreadableMail(w.s.d.mail), w.s.store, NoBarHistory(), CountingChecks())
    assert only(records.records()).error == "the mailboxes: [Errno 5] I/O error"
    with pytest.raises(OSError):
        records.deliveries("ceo")  # health's rule: a mailbox that cannot be read raises


def test_an_unknown_service_is_an_org_error(w: ReflectionWorld) -> None:
    define(w)
    define(w, "ops", "alpha")
    nested(w)
    with pytest.raises(OrgError) as raised:
        records_of(w).records("nothing")
    assert str(raised.value) == "no service named `nothing`: the services are weekly-brief, alpha, inner. Call quality() without a service for everything."


def test_records_order_top_level_then_nested_by_owner_and_name(w: ReflectionWorld) -> None:
    define(w, "ops", "alpha")
    define(w, "ceo", "weekly-brief")
    define(w, "ceo", "annual")
    define(w, "ceo/qa", "beta", actor="ceo")
    define(w, "ceo/eng", "zeta", actor="ceo")
    define(w, "ceo/eng", "alpha", actor="ceo")
    found = records_of(w).records()
    assert [(r.owner, r.service) for r in found] == [
        ("ceo", "annual"), ("ceo", "weekly-brief"), ("ops", "alpha"), ("ceo/eng", "alpha"), ("ceo/eng", "zeta"), ("ceo/qa", "beta"), ("", ""),
    ]
    assert [(r.client, r.client_kind) for r in found] == [("root", "human")] * 3 + [("ceo", "agent")] * 3 + [("root", "human")]
    assert [(r.owner, r.service) for r in records_of(w).records("alpha")] == [("ops", "alpha"), ("ceo/eng", "alpha")]  # a name two agents offer; no one-off record


# ------------------------------------------------------------------------------------------------------------------------ the record


def story(w: ReflectionWorld, *, lessons: str = "") -> tuple[Message, Message]:
    """One request, delivered, rejected by the user (human tier) with a note, and the rejection linked to the contract's first criterion."""
    define(w)
    task = ask(w)
    deliver(w, task, runs=2, lessons=lessons)
    w.s.d.clock.advance(1)
    verdict = rate(w, task, "reject", "That is not what I asked for.")
    note_on(w, task, reply_to=verdict.id, criterion="C1", source="human", body="link")
    return task, verdict


def test_a_record_holds_the_cases_deliveries_assertions_escapes_and_the_versions(w: ReflectionWorld) -> None:
    task, verdict = story(w)
    revise(w)
    record = only(records_of(w).records())
    assert (record.owner, record.client, record.client_kind, record.unit, record.error, record.files_error) == ("ceo", ROOT, "human", "case", "", "")
    assert (record.contract, record.playbook, record.budget) == (1, 1, 10)
    assert [c.id for c in record.cases] == [task.id]
    assert [d.task.id for d in record.deliveries] == [task.id] and record.deliveries[0].signer == "ceo"
    assert [(a.id, a.verdict.message.id) for a in record.assertions] == [("R1", verdict.id)]
    ((delivery, cause),) = record.escapes
    assert delivery.task.id == task.id and delivery.escape
    assert (cause.type, cause.rule, cause.version) == ("reviewer-miss", "link", 1)  # the task carried C1 and the user says it failed


def test_a_legacy_task_uses_the_version_in_force_when_it_was_sent(w: ReflectionWorld) -> None:
    task, _ = story(w)
    (case,) = w.history.cases("ceo", SERVICE)
    legacy = BreakingHistory(w.history, chains=[replace(case, tasks=[replace(task, contract=None)])])  # a task of before the contract was recorded in tasks
    ((_, cause),) = only(records_of(w, history=legacy).records()).escapes
    assert (cause.type, cause.version) == ("reviewer-miss", 1)


def test_deliveries_types_escapes_untyped_with_the_service_in_unknown_when_the_contract_cannot_be_read(w: ReflectionWorld) -> None:
    task, _ = story(w)
    clean = records_of(w).deliveries("ceo")
    assert clean.unknown == "" and [c.type if c else None for c in clean.causes] == ["reviewer-miss"]
    w.s.put(CONTRACT_PATH, BAD_YAML)
    broken = records_of(w).deliveries("ceo")
    assert [d.task.id for d in broken.deliveries] == [task.id]  # the cases come from the mailboxes alone
    (cause,) = broken.causes
    assert cause is not None and (cause.type, cause.rule) == ("untyped", "unreadable") and cause.detail[0].startswith("SERVICE.md: does not parse (")
    assert broken.unknown.startswith(f"{SERVICE}: SERVICE.md: does not parse (")


def test_deliveries_read_no_folder_and_count_no_runs(w: ReflectionWorld) -> None:
    story(w)
    history, checks = BreakingHistory(w.history), CountingChecks()
    records_of(w, history=history, checks=checks).deliveries("ceo")
    assert checks.calls == []
    assert ("chains", {"since": w.s.catalog.read_contract("ceo", SERVICE).created, "runs": False}) in history.calls  # type: ignore[union-attr]
    assert ("one_off_cases", {"runs": False}) in history.calls and all(call[1]["runs"] is False for call in history.calls)


def test_deliveries_include_the_one_off_cases_assigned_to_the_owner(w: ReflectionWorld) -> None:
    populated(w)
    task = w.s.d.post(Message(sender="root", to="ceo", type="task", body="do it", title="a one-off"))
    w.s.d.post(Message(sender="ceo", to="root", type="result", status="done", reply_to=task.id, body="Done.", title="Result"))
    w.s.d.clock.advance(1)
    w.s.d.post(Message(sender="root", to="ceo", type="note", body="No.", title="v", feedback="reject", reply_to=task.id, source="human"))
    found = records_of(w).deliveries("ceo")
    assert [d.task.id for d in found.deliveries] == [task.id]
    (cause,) = found.causes
    assert cause is not None and cause.type == "untyped"  # a one-off verdict names no criterion
    assert records_of(w).deliveries("ops").deliveries == ()


def test_lessons_and_result_bodies_change_no_count(tmp_path: Path) -> None:
    worlds = []
    for name in ("plain", "loud"):
        (tmp_path / name).mkdir()
        worlds.append(populated(memory_world(tmp_path / name)))
    plain, loud = worlds
    story(plain)
    story(loud, lessons="The client wants X always and never Y; from now on do Z. They said yes to C9.")

    def counts(world: ReflectionWorld) -> tuple[object, ...]:
        record = only(records_of(world).records())
        return (
            len(record.cases), len(record.deliveries), [d.judged for d in record.deliveries], [d.escape for d in record.deliveries],
            [(c.type, c.rule) for _, c in record.escapes], [a.id for a in record.assertions], [(a.about, a.link) for a in record.assertions],
        )

    assert counts(plain) == counts(loud)


# ------------------------------------------------------------------------------------------------------------------------ the timeline


def test_the_timeline_holds_every_kind_of_mark_oldest_first_and_the_bars_of_the_owners_team(w: ReflectionWorld) -> None:
    story(w)
    revise(w)
    when = datetime(2026, 10, 20, tzinfo=timezone.utc)
    marks: list[CharterMark | ModelMark] = [
        CharterMark("ceo/eng", "a" * 40, when), CharterMark("ops", "b" * 40, when), ModelMark("ORG.md", "effort", "high", "xhigh", "c" * 40, when),
        ModelMark("ceo", "model", "", "claude-opus-5.5", "d" * 40, when),
    ]
    found = records_of(w, bars=FixedBarHistory(marks, truncated=True, skipped=2)).records()
    record = only(found)
    kinds = [type(m).__name__ for m in record.timeline]
    assert kinds[0] == "ContractMark" and kinds.count("PlaybookMark") == 1 and "CharterMark" in kinds
    assert [m.addr for m in record.timeline if isinstance(m, (CharterMark, ModelMark))] == ["ceo/eng", "ORG.md", "ceo"]  # not ops's
    assert record.history == BarChanges(known=True, marks=(marks[0], marks[2], marks[3]), truncated=True, skipped=2)
    assert one_off(found).history.marks == (marks[2],)  # no one-off task, so no team: only ORG.md's mark
    times = [getattr(m, "when") or datetime.min.replace(tzinfo=timezone.utc) for m in record.timeline]
    assert times == sorted(times)


def test_without_an_org_history_the_bars_are_unknown(w: ReflectionWorld) -> None:
    story(w)
    record = only(records_of(w).records())
    assert record.history == BarChanges() and not any(isinstance(m, (CharterMark, ModelMark)) for m in record.timeline)


def test_top_ups_are_marks_of_the_timeline(w: ReflectionWorld) -> None:
    task, _ = story(w)
    w.s.d.clock.advance(1)
    again = rework(w, task, budget=6)
    record = only(records_of(w).records())
    ups = [m for m in record.timeline if isinstance(m, TopUpMark)]
    assert [(m.case, m.id, m.source, m.amount) for m in ups] == [(task.id, again.id, "human", 6)]


# ------------------------------------------------------------------------------------------------------------------------ files not as delivered (P3, 4.3)


def finding(kind: str, task: str, *, written: int = 0, settled: bool = False, relayed: tuple[str, ...] = ()) -> DeliverableFinding:
    return DeliverableFinding(
        folder="/deliverables", services=(SERVICE,), name="memo.md", kind=kind, artifact="lead/work/memo.md" if kind == "differs" else "", task=task,
        relayed=relayed, written=written, settled=settled,
    )


def judged(w: ReflectionWorld) -> tuple[Message, Message]:
    """A request delivered and accepted by the user."""
    define(w)
    task = ask(w)
    deliver(w, task)
    w.s.d.clock.advance(1)
    return task, rate(w, task, "accept", "good")


def test_a_differs_finding_is_attributed_to_the_delivery_whose_task_it_names(w: ReflectionWorld) -> None:
    task, verdict = judged(w)
    stamp = micros(msg_time(verdict))
    # the file was written after the verdict: the verdict judged the team's file and stays counted
    after = only(records_of(w, checks=CountingChecks([finding("differs", task.id, written=stamp + 5)])).records())
    (delivery,) = after.deliveries
    assert (delivery.edited, delivery.edited_at, delivery.judged, delivery.outcome, len(delivery.voided)) == (True, stamp + 5, True, "accepted", 0)
    # the file was written before it: the verdict is voided and the delivery is judged by nothing
    before = only(records_of(w, checks=CountingChecks([finding("differs", task.id, written=stamp - 5)])).records())
    (delivery,) = before.deliveries
    assert (delivery.edited, delivery.judged, delivery.outcome, len(delivery.voided)) == (True, False, "neither", 1)
    # a write time that is not known marks the delivery and voids nothing
    unknown = only(records_of(w, checks=CountingChecks([finding("differs", task.id, written=0)])).records())
    assert (unknown.deliveries[0].edited, unknown.deliveries[0].edited_at, unknown.deliveries[0].judged) == (True, 0, True)


def test_two_files_of_one_delivery_count_from_the_earliest_write(w: ReflectionWorld) -> None:
    task, verdict = judged(w)
    stamp = micros(msg_time(verdict))
    checks = CountingChecks([finding("differs", task.id, written=stamp + 9), finding("differs", task.id, written=stamp - 9), finding("differs", task.id)])
    (delivery,) = only(records_of(w, checks=checks).records()).deliveries
    assert delivery.edited_at == stamp - 9 and delivery.outcome == "neither"


def test_a_finding_whose_file_equals_another_deliverys_checked_artifact_is_no_hand_edit(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first)
    w.s.d.clock.advance(1)
    rate(w, first, "accept", "good")
    w.s.d.clock.advance(1)
    second = rework(w, first, source="relayed")
    deliver(w, second)
    stamp = micros(w.s.d.clock.now())
    relayed = finding("relayed", first.id, written=stamp, relayed=(second.id,))  # the file is the first delivery as the team checked it
    record = only(records_of(w, checks=CountingChecks([relayed])).records())
    by_task = {d.task.id: d for d in record.deliveries}
    assert (by_task[first.id].given, by_task[first.id].edited, by_task[first.id].judged) == (True, False, True)  # the user was given the first
    assert (by_task[second.id].given, by_task[second.id].edited) == (False, False)
    assert all(not d.voided for d in record.deliveries)


def test_a_finding_of_no_record_is_dropped(w: ReflectionWorld) -> None:
    task, _ = judged(w)
    checks = CountingChecks([finding("differs", "20260101T000000000000-root-0000", written=5), finding("relayed", "20260101T000000000001-root-0001")])
    (delivery,) = only(records_of(w, checks=checks).records()).deliveries
    assert (delivery.task.id, delivery.edited, delivery.given) == (task.id, False, False)


def test_other_finding_kinds_are_not_hand_edits(w: ReflectionWorld) -> None:
    task, _ = judged(w)
    others = [finding(kind, task.id, written=5) for kind in ("unknown", "link", "large", "limit", "unreadable")]
    (delivery,) = only(records_of(w, checks=CountingChecks(others)).records()).deliveries
    assert (delivery.edited, delivery.edited_at, delivery.given, delivery.judged) == (False, 0, False, True)


def test_a_p3_call_that_raises_sets_every_records_hand_edits_and_voids_nothing(w: ReflectionWorld) -> None:
    task, _ = judged(w)
    define(w, "ops", "other-brief")
    checks = CountingChecks([finding("differs", task.id, written=1)], raises=RuntimeError("folder"))
    found = records_of(w, checks=checks).records()
    assert {r.files_error for r in found} == {"the deliverable folders: cannot be read (RuntimeError: folder)"}
    assert only(found).deliveries[0].edited is False and only(found).deliveries[0].judged is True  # nothing is voided or counted as not as delivered
    assert len(checks.calls) == 1


def test_one_p3_call_per_records_call(w: ReflectionWorld) -> None:
    judged(w)
    define(w, "ops", "other-brief")
    nested(w)
    checks = CountingChecks()
    records = records_of(w, checks=checks)
    records.records()
    assert checks.calls == [(ROOT, None, True)]  # one call for every record, with the settled findings
    records.records(SERVICE)
    assert checks.calls == [(ROOT, None, True)] * 2


# ------------------------------------------------------------------------------------------------------------------------ one-off records


def test_a_one_off_record_holds_roots_tasks_without_a_service(w: ReflectionWorld) -> None:
    populated(w)
    task = w.s.d.post(Message(sender="root", to="ceo", type="task", body="do it", title="a one-off"))
    w.s.d.post(Message(sender="ceo", to="root", type="result", status="done", reply_to=task.id, body="Done.", title="Result"))
    w.s.d.clock.advance(1)
    verdict = w.s.d.post(Message(sender="root", to="ceo", type="note", body="Not right.", title="v", feedback="reject", reply_to=task.id, source="human"))
    record = one_off(records_of(w).records())
    assert (record.owner, record.service, record.contract, record.playbook, record.budget, record.assertions) == ("", "", 0, 0, 0, ())
    assert [c.id for c in record.cases] == [task.id] and [d.task.id for d in record.deliveries] == [task.id]
    ((delivery, cause),) = record.escapes
    assert delivery.decisive is not None and delivery.decisive.message.id == verdict.id
    assert (cause.type, cause.rule) == ("untyped", "none")
