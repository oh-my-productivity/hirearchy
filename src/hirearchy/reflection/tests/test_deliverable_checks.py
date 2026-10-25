"""``FolderDeliverableChecks``: the files of a contract's deliverable folder (or the one file) that differ from the team's last checked version, that the
team never wrote, or that could not be read (design 6.3). The folder, the checked versions (git) and the clock are fakes; the cases are derived from the
mail of the services world, as they are for real."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import ROOT, Clock, Message
from hirearchy.reflection import DeliverableChecks, DeliverableFinding
from hirearchy.reflection._deliverable_checks import FolderDeliverableChecks
from hirearchy.reflection._ports import FolderFile, FolderRead
from hirearchy.reflection.testing import FixedCheckedVersions, HashBlobIds, MemoryDeliverableFolder, ReflectionWorld, blob, fs_world, memory_world
from hirearchy.services import Contract

from ._support import SERVICE, ask, define, populated, rate, rework

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
FOLDER = "/deliverables/memos"
MEMO = "lead/work/memo.md"


def us(moment: datetime) -> int:
    """Microseconds since the epoch, as the files' mtimes are counted."""
    return (moment - EPOCH) // timedelta(microseconds=1)


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@dataclass
class Rig:
    w: ReflectionWorld
    folder: MemoryDeliverableFolder
    versions: FixedCheckedVersions
    checks: FolderDeliverableChecks

    def later(self, seconds: float = 1.0) -> int:
        """Time moves; the microsecond timestamp of the new moment (an edit made now has this mtime)."""
        self.w.s.d.clock.advance(seconds)
        return us(self.w.s.d.clock.now())

    def findings(self, service: str | None = None) -> list[DeliverableFinding]:
        """The findings with their write time left out: these tests compare whole findings, and the time is tested apart (the contract suite)."""
        return [replace(found, written=0) for found in self.checks.findings(ROOT, service)]


def rig(w: ReflectionWorld, clock: Clock | None = None, versions: FixedCheckedVersions | None = None) -> Rig:
    folder, fixed = MemoryDeliverableFolder(), versions or FixedCheckedVersions()
    checks = FolderDeliverableChecks(w.s.catalog, w.history, w.s.d.mail, folder, fixed, HashBlobIds(), clock or w.s.d.clock)
    return Rig(w, folder, fixed, checks)


def service(w: ReflectionWorld, path: str | None = FOLDER, owner: str = "ceo", name: str = SERVICE) -> None:
    """``owner`` offers ``name``; its contract names ``path`` as the deliverable place (none: no ``path`` at all)."""
    define(w, owner, name, deliverable={"description": "one markdown file", **({"path": path} if path else {})})


def done(w: ReflectionWorld, task: Message, *artifacts: str, status: str = "done", questions: Sequence[str] = ()) -> Message:
    """The owner of ``task`` answers it with a result listing ``artifacts`` (and the client's questions, if any)."""
    asked = "Questions for the client:\n" + "\n".join(f"- {q}" for q in questions) + "\n\n" if questions else ""
    listed = "\n".join(f"- {a} (3 words)" for a in artifacts)
    body = f"{asked}## Summary\nok\n\n## Artifacts\n{listed}\n"
    return w.s.d.post(Message(sender=task.to, to=task.sender, type="result", status=status, reply_to=task.id, body=body, title="Result"))


def checked(r: Rig, result: Message, path: str, data: bytes, commit: str = "c1") -> None:
    """The team's file ``path`` as ``result`` reported it held ``data`` (git has it at ``commit``)."""
    r.versions.at[(result.id, path)] = (commit, blob(data))


def put(r: Rig, files: dict[str, bytes], *, folder: str = FOLDER, mtime: int | None = None) -> None:
    """The user's folder holds these files; unless said otherwise they were last written a second after the contract was made."""
    stamp = r.later() if mtime is None else mtime
    r.folder.folder(folder, {name: (data, stamp) for name, data in files.items()})


def finding(name: str, kind: str, services: tuple[str, ...] = (SERVICE,), **over: object) -> DeliverableFinding:
    base: dict[str, object] = dict(folder=FOLDER, services=services, name=name, kind=kind, artifact="", task="", relayed=(), withheld=False, error="", file=False)
    return DeliverableFinding(**{**base, **over})  # type: ignore[arg-type]


def delivered(r: Rig, data: bytes = b"team v1\n", path: str = MEMO, topic: str = "ai") -> tuple[Message, Message]:
    """A request of ``weekly-brief``, answered with ``path`` (the team's copy held ``data`` when it reported)."""
    task = ask(r.w, topic)
    result = done(r.w, task, path)
    checked(r, result, path, data)
    return task, result


def test_it_is_a_deliverable_checks(w: ReflectionWorld) -> None:
    assert isinstance(rig(w).checks, DeliverableChecks)


# ------------------------------------------------------------------------------------------------------------------------ what differs


def test_an_edited_copy_differs_from_the_checked_version(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    task, _ = delivered(r)
    put(r, {"memo.md": b"edited by the assistant\n"})
    assert r.findings() == [finding("memo.md", "differs", artifact=MEMO, task=task.id)]


def test_an_equal_copy_gives_nothing(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    delivered(r, b"team v1\n")
    put(r, {"memo.md": b"team v1\n"})
    assert r.findings() == []


def test_a_file_the_team_never_wrote_is_unknown(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    delivered(r)
    put(r, {"notes.md": b"the user's own notes\n"})  # no artifact is called notes.md, and no checked version equals it
    assert r.findings() == [finding("notes.md", "unknown")]


def test_no_done_result_makes_new_files_unknown_and_compares_nothing(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    ask(w, "ai")  # requested, not delivered
    done(w, ask(w, "blocked one"), MEMO, status="blocked")  # a result that is not done is no candidate
    put(r, {"memo.md": b"something\n"})
    assert r.findings() == [finding("memo.md", "unknown")]
    assert r.versions.asked == [] and r.versions.currents == []  # nothing to compare with, nothing asked of git


def test_two_services_and_a_one_off_result_in_one_folder_give_no_false_unknown(w: ReflectionWorld) -> None:
    """The default ``deliverables/`` folder is shared by every service and every one-off goal: the basis is the union of their results."""
    service(w)
    service(w, owner="ops", name="other-service")
    r = rig(w)
    delivered(r, b"a\n", "ceo/work/a.md")
    second = w.s.commands.request(ROOT, "other-service", {"topic": "x"})
    checked(r, done(w, second, "ops/work/b.md"), "ops/work/b.md", b"b\n")
    goal = w.s.d.post(Message(sender=ROOT, to="ceo", type="task", title="A one-off goal", body="goal", budget=3))
    checked(r, done(w, goal, "ceo/work/c.md"), "ceo/work/c.md", b"c\n")
    put(r, {"a.md": b"a\n", "b.md": b"b\n", "c.md": b"c\n"})
    assert r.findings() == []  # each file equals the checked version of the result that listed it
    put(r, {"a.md": b"a\n", "b.md": b"b EDITED\n", "c.md": b"c\n"})
    (only,) = r.findings()
    assert (only.name, only.kind, only.artifact) == ("b.md", "differs", "ops/work/b.md")
    assert only.services == ("other-service", SERVICE)  # sorted; one block names every service that names this folder


def test_a_basename_pair_unknown_on_both_sides_is_dropped(w: ReflectionWorld) -> None:
    """The team's file moved or was deleted (as after a team retirement): neither git nor the organization knows it. That pair cannot be compared."""
    service(w)
    r = rig(w)
    ask_one, ask_two = ask(w, "one"), ask(w, "two")
    older = done(w, ask_one, MEMO)
    checked(r, older, MEMO, b"older team version\n")
    done(w, ask_two, MEMO)  # the newest result lists the same path; git and the organization know nothing of it
    put(r, {"memo.md": b"older team version\n"})
    assert r.findings() == []  # dropped: compared with the older pair's checked version, which it equals
    put(r, {"memo.md": b"edited\n"})
    (found,) = r.findings()
    assert (found.kind, found.artifact, found.task) == ("differs", MEMO, ask_one.id)
    only_unknown = rig(w)
    put(only_unknown, {"memo.md": b"whatever\n"})
    assert only_unknown.findings()[0].kind == "unknown"  # no pair left with a known version: the file goes to the rename rule, finds no equal


def test_a_renamed_copy_equal_to_a_checked_version_is_not_reported(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    delivered(r, b"team v1\n")
    put(r, {"2026-10-05-memo.md": b"team v1\n"})  # the user's copy, renamed: no basename match, equal to what the team checked
    assert r.findings() == []


def test_a_relayed_accept_after_an_edit_leaves_the_finding(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    task, _ = delivered(r)
    put(r, {"memo.md": b"edited\n"})
    w.s.d.clock.advance(1)
    rate(w, task, "accept", source="relayed")  # the assistant's own feedback right after its own edit
    assert [f.kind for f in r.findings()] == ["differs"]


def test_a_human_verdict_after_the_edit_settles_it(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    task, _ = delivered(r)
    put(r, {"memo.md": b"edited\n", "notes.md": b"mine\n"})
    assert sorted(f.kind for f in r.findings()) == ["differs", "unknown"]
    w.s.d.clock.advance(1)
    rate(w, task, "accept")  # the user's own verdict, after the changes: both are settled (an `unknown` by a verdict of any case of the group)
    assert r.findings() == []
    put(r, {"memo.md": b"edited again\n"})  # a later edit is a new finding: the verdict came before it
    assert [f.kind for f in r.findings()] == ["differs"]


def test_files_older_than_the_earliest_created_are_ignored_and_no_created_means_no_floor(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    delivered(r)
    contract = w.s.catalog.read_contract("ceo", SERVICE)
    assert contract is not None and contract.created is not None
    created = us(contract.created)
    put(r, {"old.md": b"from before the service\n"}, mtime=created - 1)
    assert r.findings() == []  # the user's own older file
    put(r, {"old.md": b"from before the service\n"}, mtime=created)
    assert [f.name for f in r.findings()] == ["old.md"]  # at the moment it was made: not before it
    found = w.s.store.read_contract("ceo", SERVICE)
    assert found is not None
    meta, body = found
    meta.pop("created", None)
    meta.pop("defined", None)  # `created` falls back to `defined`: a contract written before either existed has neither
    w.s.store.write_contract("ceo", SERVICE, meta, body, None)
    contract = w.s.catalog.read_contract("ceo", SERVICE)
    assert isinstance(contract, Contract) and contract.created is None
    put(r, {"old.md": b"from before the service\n"}, mtime=1)  # a legacy contract: no floor at all
    assert [f.name for f in r.findings()] == ["old.md"]


def test_withheld_while_questions_are_open(w: ReflectionWorld) -> None:
    """D-E6-1 (A2): the question names a criterion id (``C1``), the only kind that withholds the path; an item without one is a note (next test)."""
    service(w)
    r = rig(w)
    task = ask(w, "ai")
    checked(r, done(w, task, MEMO, questions=["C1: Keep Marta's row?"]), MEMO, b"team v1\n")
    put(r, {"memo.md": b"edited\n"})
    (found,) = r.findings()
    assert (found.kind, found.withheld, found.task) == ("differs", True, task.id)
    rework(w, task, source="relayed")  # the assistant's own rework does not answer them
    assert r.findings()[0].withheld is True
    rework(w, task)  # the user asked for it
    assert r.findings()[0].withheld is False and r.findings()[0].artifact == MEMO


def test_a_relayed_verdict_alone_keeps_the_path_withheld(w: ReflectionWorld) -> None:
    """D-E7-2 C: the assistant's own (relayed) verdict on the delivery settles no question, so the finding stays withheld ("path withheld: ask first");
    the user's own rework releases it."""
    service(w)
    r = rig(w)
    task = ask(w, "ai")
    checked(r, done(w, task, MEMO, questions=["C1: Keep Marta's row?"]), MEMO, b"team v1\n")
    put(r, {"memo.md": b"edited\n"})
    rate(w, task, "accept", source="relayed")
    (found,) = r.findings()
    assert (found.kind, found.withheld, found.task) == ("differs", True, task.id)
    rework(w, task)  # the user's own rework answers the questions (a human verdict after the edit settles the finding itself)
    assert r.findings()[0].withheld is False and r.findings()[0].artifact == MEMO


def test_notes_only_withhold_nothing_and_a_question_with_the_notes_does(w: ReflectionWorld) -> None:
    """D-E6-1 (A2): a result whose block holds only notes (no criterion id) is not withheld, so the finding carries its path; with a ``C<k>`` question it is."""
    service(w)
    r = rig(w)
    task = ask(w, "ai")
    checked(r, done(w, task, MEMO, questions=["Style: 'himself' (reviewer: harmless)."]), MEMO, b"team v1\n")
    put(r, {"memo.md": b"edited\n"})
    (found,) = r.findings()
    assert (found.kind, found.withheld, found.artifact, found.task) == ("differs", False, MEMO, task.id)
    other = ask(w, "bob")
    checked(r, done(w, other, MEMO, questions=["Style: a note.", "C2: Which Friday?"]), MEMO, b"team v2\n", commit="c2")
    put(r, {"memo.md": b"edited again\n"})
    (again,) = r.findings()
    assert (again.kind, again.withheld, again.task) == ("differs", True, other.id)


# ------------------------------------------------------------------------------------------------------------------------ a relayed rework changed the copy (F-E5-5)


def e5_chain(r: Rig, *relayed_data: bytes) -> tuple[Message, list[Message]]:
    """E5 s1's shape: a request, the user's rework of it delivered with ``team v2`` (the delivery the user saw), then one relayed rework of the
    previous task for each of ``relayed_data``, each delivered with its own copy. Returns the delivery's task and the relayed tasks, oldest first."""
    first, _ = delivered(r, b"team v1\n")
    human = rework(r.w, first)
    checked(r, done(r.w, human, MEMO), MEMO, b"team v2\n", commit="c2")
    previous, relayed = human, []
    for n, data in enumerate(relayed_data, start=3):
        previous = rework(r.w, previous, source="relayed")
        checked(r, done(r.w, previous, MEMO), MEMO, data, commit=f"c{n}")
        relayed.append(previous)
    return human, relayed


def test_a_file_equal_to_the_delivery_a_relayed_rework_changed_is_relayed(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    human, (relayed,) = e5_chain(r, b"team v3\n")
    put(r, {"memo.md": b"team v2\n"})  # the copy the user saw and the team checked, before the assistant's own rework changed the team's
    assert r.findings() == [finding("memo.md", "relayed", task=human.id, relayed=(relayed.id,))]


def test_two_relayed_reworks_give_both_ids_oldest_first(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    human, (first, second) = e5_chain(r, b"team v3\n", b"team v4\n")
    put(r, {"memo.md": b"team v2\n"})
    assert r.findings() == [finding("memo.md", "relayed", task=human.id, relayed=(first.id, second.id))]


def test_a_human_rework_that_differs_in_between_gives_differs_from_the_newest(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    _, (relayed,) = e5_chain(r, b"team v3\n")
    put(r, {"memo.md": b"team v1\n"})  # equal to the first delivery, with the user's own rework (v2) between it and the relayed one
    assert r.findings() == [finding("memo.md", "differs", artifact=MEMO, task=relayed.id)]


def test_a_file_equal_to_the_newest_relayed_pair_gives_nothing(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    e5_chain(r, b"team v3\n")
    put(r, {"memo.md": b"team v3\n"})
    assert r.findings() == []


def test_a_file_that_equals_no_pair_differs_from_the_newest_relayed_one(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    _, (relayed,) = e5_chain(r, b"team v3\n")
    put(r, {"memo.md": b"edited by the assistant\n"})
    assert r.findings() == [finding("memo.md", "differs", artifact=MEMO, task=relayed.id)]


def test_a_human_verdict_after_the_edit_settles_a_relayed_finding(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    human, _ = e5_chain(r, b"team v3\n")
    put(r, {"memo.md": b"team v2\n"})
    assert [f.kind for f in r.findings()] == ["relayed"]
    w.s.d.clock.advance(1)
    rate(w, human, "accept", source="relayed")  # the assistant's own verdict never settles it
    assert [f.kind for f in r.findings()] == ["relayed"]
    rate(w, human, "accept")  # the user's does
    assert r.findings() == []


def test_the_file_rule_names_the_relayed_rework_too(w: ReflectionWorld) -> None:
    service(w, "/deliverables/memo.md")
    r = rig(w)
    human, (relayed,) = e5_chain(r, b"team v3\n")
    r.folder.file("/deliverables/memo.md", b"team v2\n", r.later())
    assert r.findings() == [finding("memo.md", "relayed", folder="/deliverables", task=human.id, relayed=(relayed.id,), file=True)]
    r.folder.file("/deliverables/memo.md", b"team v1\n", r.later())
    assert r.findings() == []  # equal to an older pair with the user's own rework newer than it: no finding, as before
    r.folder.file("/deliverables/memo.md", b"edited\n", r.later())
    assert r.findings() == [finding("memo.md", "differs", folder="/deliverables", artifact=MEMO, task=relayed.id, file=True)]


# ------------------------------------------------------------------------------------------------------------------------ the git bound


def test_the_git_bound_is_40_pairs(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    names = []
    for k in range(20):  # the newest 20 results are the candidates, 5 paths each: 100 pairs, of which 40 may ask git
        paths = [f"lead/work/k{k:02d}-{n}.md" for n in range(5)]
        result = done(w, ask(w, f"topic {k}"), *paths)
        for path in paths:
            checked(r, result, path, b"team\n")
            r.versions.now[path] = blob(b"team\n")
            names.append(path.rsplit("/", 1)[1])
    put(r, {name: b"edited\n" for name in names})
    found = r.findings()
    assert len(found) == 100 and {f.kind for f in found} == {"differs"}  # every file is judged, with git or without it
    assert len(r.versions.asked) == 40 and len(set(r.versions.asked)) == 40  # the 41st pair and the ones after it are read from the organization's files
    assert len(r.versions.currents) == 60


def test_the_git_bound_is_5_seconds_by_the_clock(w: ReflectionWorld) -> None:
    class Stepping(Clock):
        """Every look at the clock takes two seconds."""

        def __init__(self) -> None:
            self.t = 0.0

        def now(self) -> datetime:
            return datetime(2026, 1, 1, tzinfo=timezone.utc)

        def time(self) -> float:
            return self.t

        def monotonic(self) -> float:
            self.t += 2.0
            return self.t

        def sleep(self, seconds: float) -> None:
            self.t += seconds

    service(w)
    r = rig(w, Stepping())
    for n in range(6):
        path = f"lead/work/f{n}.md"
        checked(r, done(w, ask(w, f"topic {n}"), path), path, b"team\n")
        r.versions.now[path] = blob(b"team\n")
    put(r, {f"f{n}.md": b"edited\n" for n in range(6)})
    found = r.findings()
    assert len(found) == 6 and {f.kind for f in found} == {"differs"}
    # the call starts at 2 s on this clock; the first pair is looked at 4 s (2 s spent), the second at 6 s (4 s spent), the third at 8 s (6 s: spent)
    assert len(r.versions.asked) == 2 and len(r.versions.currents) == 4


def test_no_repository_compares_current_blobs_with_sha1(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    task = ask(w, "ai")
    done(w, task, MEMO)  # git knows nothing (no repository): no checked version at a result
    r.versions.now[MEMO] = blob(b"team now\n")
    put(r, {"memo.md": b"team now\n"})
    assert r.findings() == [] and r.versions.currents == [(MEMO, 40)]  # both sides are the product's own sha1 blobs
    put(r, {"memo.md": b"edited\n"})
    assert [f.kind for f in r.findings()] == ["differs"]


def test_a_sha256_repository_is_compared_with_sha256(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    task = ask(w, "ai")
    result = done(w, task, MEMO)
    r.versions.at[(result.id, MEMO)] = ("c1", HashBlobIds().of(b"team v1\n", 64))
    put(r, {"memo.md": b"team v1\n"})
    assert r.findings() == []
    put(r, {"memo.md": b"edited\n"})
    assert [f.kind for f in r.findings()] == ["differs"]


# ------------------------------------------------------------------------------------------------------------------------ a contract that names a file


def test_single_file_contract_edited_differs_equal_nothing_missing_nothing(w: ReflectionWorld) -> None:
    service(w, "/deliverables/memo.md")
    r = rig(w)
    task, _ = delivered(r, b"team v1\n")
    assert r.findings() == []  # nothing is there yet
    r.folder.file("/deliverables/memo.md", b"team v1\n", r.later())
    assert r.findings() == []  # equal
    r.folder.file("/deliverables/memo.md", b"edited\n", r.later())
    assert r.findings() == [finding("memo.md", "differs", folder="/deliverables", artifact=MEMO, task=task.id, file=True)]


def test_single_file_contract_with_no_candidate_is_unknown(w: ReflectionWorld) -> None:
    service(w, "/deliverables/memo.md")
    r = rig(w)
    r.folder.file("/deliverables/memo.md", b"somebody's file\n", r.later())
    assert r.findings() == [finding("memo.md", "unknown", folder="/deliverables", file=True)]


def test_a_single_file_contract_compares_the_newest_result_when_no_name_matches(w: ReflectionWorld) -> None:
    """The contract names `memo.md` while the team writes `2026-10-05-memo.md`."""
    service(w, "/deliverables/memo.md")
    r = rig(w)
    task, _ = delivered(r, b"team v1\n", "lead/work/2026-10-05-memo.md")
    r.folder.file("/deliverables/memo.md", b"edited\n", r.later())
    assert r.findings() == [finding("memo.md", "differs", folder="/deliverables", artifact="lead/work/2026-10-05-memo.md", task=task.id, file=True)]
    r.folder.file("/deliverables/memo.md", b"team v1\n", r.later())
    assert r.findings() == []


# ------------------------------------------------------------------------------------------------------------------------ the kind of a contract (DR-45)


def test_the_kind_is_decided_before_grouping(w: ReflectionWorld) -> None:
    """One service names the folder, the other a file in it: one group, one block that names both."""
    service(w)
    service(w, f"{FOLDER}/summary.md", owner="ops", name="summary")
    r = rig(w)
    put(r, {"notes.md": b"mine\n", "summary.md": b"mine too\n"})  # `summary.md` is a file place of the folder that is there
    found = r.findings()
    assert {f.folder for f in found} == {FOLDER} and {f.services for f in found} == {("summary", SERVICE)}  # not a block per contract
    assert len(r.folder.reads) <= 2 and not any(f.file for f in found)


def test_a_file_contract_inside_a_folder_group_uses_the_file_rule_and_joins_the_basis(w: ReflectionWorld) -> None:
    service(w)  # the folder's service delivered nothing
    service(w, f"{FOLDER}/summary.md", owner="ops", name="summary")
    r = rig(w)
    task = w.s.commands.request(ROOT, "summary", {"topic": "x"})
    result = done(w, task, "ops/work/y.md")  # the team of the file contract wrote `y.md`, not `summary.md`
    checked(r, result, "ops/work/y.md", b"team y\n")
    put(r, {"summary.md": b"edited by the assistant\n", "y.md": b"team y\n"})
    found = r.findings()
    assert found == [finding("summary.md", "differs", services=("summary", SERVICE), artifact="ops/work/y.md", task=task.id)]  # `differs`, never `unknown`
    put(r, {"summary.md": b"team y\n", "y.md": b"team y\n"})
    assert r.findings() == []  # the file contract's results are in the basis of the whole folder: y.md equals the checked version


def test_a_single_file_group_outside_any_folder_group(w: ReflectionWorld) -> None:
    service(w, f"{FOLDER}/summary.md", owner="ops", name="summary")
    service(w, "/elsewhere/memos", name="memos")
    r = rig(w)
    r.folder.file(f"{FOLDER}/summary.md", b"mine\n", r.later())
    put(r, {"other.md": b"mine\n"}, folder="/elsewhere/memos")
    assert sorted((f.folder, f.name, f.file) for f in r.findings()) == [("/deliverables/memos", "summary.md", True), ("/elsewhere/memos", "other.md", False)]


# ------------------------------------------------------------------------------------------------------------------------ what is not compared, what is not read


def test_artifact_paths_with_dotdot_or_absolute_are_not_compared(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    task = ask(w, "ai")
    result = done(w, task, "/Users/me/work/memo.md", "../outside/memo.md", "lead//work/memo.md", "lead/./memo.md", "docs/")
    for path in ("/Users/me/work/memo.md", "../outside/memo.md", "lead//work/memo.md", "lead/./memo.md"):
        checked(r, result, path, b"team\n")
        r.versions.now[path] = blob(b"team\n")
    put(r, {"memo.md": b"team\n"})
    assert r.findings() == [finding("memo.md", "unknown")]  # no org-relative path: no candidate pair, so nothing is compared (and git is not asked)
    assert r.versions.asked == [] and r.versions.currents == []


def test_an_artifact_path_with_a_nul_byte_is_not_compared_and_nothing_raises(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    task = ask(w, "ai")
    done(w, task, "lead/work/a\x00b.md")  # an agent's result summary can list any text as an artifact
    put(r, {"memo.md": b"team\n"})
    assert r.findings() == [finding("memo.md", "unknown")]
    assert r.versions.asked == [] and r.versions.currents == []


def test_only_the_newest_20_results_and_10_paths_are_candidates(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    first = ask(w, "oldest")
    old = done(w, first, "lead/work/oldest.md")
    checked(r, old, "lead/work/oldest.md", b"team\n")
    for n in range(20):
        task = ask(w, f"t{n}")
        done(w, task, *[f"lead/work/n{n:02d}-{k}.md" for k in range(12)])
    put(r, {"oldest.md": b"team\n", "n00-0.md": b"x\n", "n00-11.md": b"x\n"})
    kinds = {f.name: f.kind for f in r.findings()}
    assert kinds == {"oldest.md": "unknown", "n00-0.md": "unknown", "n00-11.md": "unknown"}  # the 21st-newest result and the 11th path are no candidates
    assert "lead/work/oldest.md" not in {path for _, path in r.versions.asked}


def test_findings_never_raise_for_an_unreadable_folder(w: ReflectionWorld) -> None:
    service(w)
    service(w, "/linked", owner="ops", name="linked")
    service(w, "/gone", owner="ops", name="gone")
    r = rig(w)
    r.folder.states[FOLDER] = "unreadable"
    r.folder.states["/linked"] = "link"
    found = r.findings()
    assert sorted((f.folder, f.name, f.kind) for f in found) == [("/deliverables/memos", "", "unreadable"), ("/linked", "", "link")]  # /gone: nothing
    assert [f.error for f in found if f.kind == "unreadable"] == ["Permission denied"]


def test_entries_that_were_not_read_are_shown_as_they_are(w: ReflectionWorld) -> None:
    service(w)
    r = rig(w)
    delivered(r)
    stamp = r.later()
    r.folder.put(FOLDER, FolderRead("folder", FOLDER, (
        FolderFile("a-link.md", "link"), FolderFile("big.bin", "large", mtime_us=stamp), FolderFile("late.md", "limit", mtime_us=stamp),
        FolderFile("locked.md", "unreadable", error="Permission denied"),
    )))
    assert [(f.name, f.kind) for f in r.findings()] == [("a-link.md", "link"), ("big.bin", "large"), ("late.md", "limit"), ("locked.md", "unreadable")]
    assert [f.error for f in r.findings() if f.name == "locked.md"] == ["Permission denied"]


def test_the_budget_of_a_call_is_shared_by_its_folders(w: ReflectionWorld) -> None:
    service(w)
    service(w, "/other", owner="ops", name="other")
    r = rig(w)
    r.folder.folder(FOLDER, {}, used=30 * 1024 * 1024)
    r.folder.folder("/other", {})
    r.findings()
    assert r.folder.budgets == [32 * 1024 * 1024, 2 * 1024 * 1024]  # in group order; what the first used is no longer there for the second


def test_a_service_without_a_path_or_with_a_missing_folder_has_no_findings(w: ReflectionWorld) -> None:
    service(w, None)  # no `path` at all
    service(w, "/never-made", owner="ops", name="nowhere")
    r = rig(w)
    assert r.findings() == [] and r.folder.reads == []


def test_only_the_given_services_group_is_checked(w: ReflectionWorld) -> None:
    service(w)
    service(w, "/other", owner="ops", name="other")
    r = rig(w)
    put(r, {"a.md": b"x\n"})
    put(r, {"b.md": b"y\n"}, folder="/other")
    r.folder.reads.clear()
    assert [f.name for f in r.findings("other")] == ["b.md"] and r.folder.reads == ["/other"]  # the other folder was not even read
    assert [f.name for f in r.findings(SERVICE)] == ["a.md"]
    assert r.findings("no-such-service") == []
    assert sorted(f.name for f in r.findings()) == ["a.md", "b.md"]


def test_the_findings_of_an_actor_without_services_are_none(w: ReflectionWorld) -> None:
    assert rig(w).checks.findings("ceo/eng") == [] and rig(w).findings() == []
