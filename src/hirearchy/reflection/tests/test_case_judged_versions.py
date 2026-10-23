"""``CaseJudgedVersions``: the delivery the client judged and what relayed reworks changed after it, derived from the cases of a service and the checked
versions (git) of the files the team delivered (P4, design 7.2).

The services suite of ``JudgedVersions`` runs against it too (the pattern of ``test_case_service_evidence``), over a world where ``ceo`` offers
``weekly-brief`` and no task is in a case; the behaviour tests follow. The checked versions are a fake (``FixedCheckedVersions``): git knows nothing
here."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from hirearchy.kernel import Message
from hirearchy.reflection._judged import CaseJudgedVersions
from hirearchy.reflection.testing import FixedCheckedVersions, ReflectionWorld, blob, fs_world, memory_world
from hirearchy.services import JUDGED_BYTES, JudgedBase, JudgedVersions

# The suite that every ``JudgedVersions`` passes: the same functions, run against this package's implementation.
from hirearchy.services.tests.test_contract_judged_versions import (  # noqa: F401  (imported to be collected here)
    test_a_task_that_is_in_no_case_needs_no_base,
    test_the_answer_is_none_or_a_well_formed_base,
    test_the_answer_is_the_same_every_time,
    test_the_judged_texts_are_those_of_changed_paths_in_their_order_within_the_limit,
)

from ._support import SERVICE, ask, define, populated, rate, rework

MEMO = "ceo/work/memo.md"
OTHER = "ceo/work/other.md"
V1, V2 = b"| Marta | 2026-10-14 |\n", b"| Marta | none |\n"


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@pytest.fixture
def versions() -> FixedCheckedVersions:
    return FixedCheckedVersions()


@pytest.fixture
def judged(w: ReflectionWorld, versions: FixedCheckedVersions) -> JudgedVersions:
    define(w)
    return CaseJudgedVersions(w.history, w.s.d.mail, versions)


def deliver(w: ReflectionWorld, task: Message, paths: Sequence[str] = (MEMO,), status: str = "done") -> Message:
    """The owner answers ``task``, listing ``paths`` as its artifacts."""
    w.use_run(task.to)
    listed = "".join(f"- {path} (10 words)\n" for path in paths)
    body = "Delivered.\n\n## Artifacts\n" + listed if paths else "Delivered."
    return w.s.d.post(Message(sender=task.to, to=task.sender, type="result", status=status, reply_to=task.id, body=body, title="Result"))


def committed(versions: FixedCheckedVersions, result: Message, path: str = MEMO, data: bytes = V1, commit: str = "c" * 40) -> None:
    """Git knows ``result``'s ``path`` as ``data`` at ``commit``, and its judged text."""
    versions.at[(result.id, path)] = (commit, blob(data))
    versions.texts[(commit, path)] = data


def edited(versions: FixedCheckedVersions, path: str = MEMO, data: bytes = V2) -> None:
    """The file in the organization now is ``data``."""
    versions.now[path] = blob(data)


def the_s2r_flow(w: ReflectionWorld, versions: FixedCheckedVersions) -> tuple[Message, Message, Message, Message]:
    """The request is delivered and rejected by the user; a relayed rework changes the memo; its result. ``(request, result, relayed, its result)``."""
    first = ask(w)
    r1 = deliver(w, first)
    committed(versions, r1)
    rate(w, first, "reject", "Marta's date is wrong.")
    again = rework(w, first, source="relayed")
    r2 = deliver(w, again)
    committed(versions, r2, data=V2, commit="d" * 40)
    edited(versions)
    return first, r1, again, r2


def test_no_case_gives_none(judged: JudgedVersions) -> None:
    assert judged.base("ceo", SERVICE, "20200101T000000000001-root-0000") is None


def test_the_judged_delivery_is_the_task_of_the_latest_human_verdict(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first, r1, again, r2 = the_s2r_flow(w, versions)
    base = judged.base("ceo", SERVICE, first.id)
    assert base == JudgedBase(task=first.id, result=r1.id, commit="c" * 40, relayed=(again.id,), changed=(MEMO,), texts=((MEMO, V1.decode()),))
    rate(w, again, "reject", "No: the date was right before.")  # the user judges the relayed rework's delivery: it is the judged one now
    later = rework(w, again, source="relayed")
    r3 = deliver(w, later)
    committed(versions, r3, data=b"| Marta | tbd |\n", commit="e" * 40)
    edited(versions, data=b"| Marta | tbd |\n")
    base = judged.base("ceo", SERVICE, again.id)
    assert base is not None and (base.task, base.result, base.relayed, base.commit) == (again.id, r2.id, (later.id,), "d" * 40)
    assert base.texts == ((MEMO, V2.decode()),)


def test_a_relayed_verdict_does_not_judge_a_delivery(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first, r1, again, _ = the_s2r_flow(w, versions)
    rate(w, again, "accept", source="relayed")  # root's own reading: the client has not judged it
    base = judged.base("ceo", SERVICE, first.id)
    assert base is not None and (base.task, base.result) == (first.id, r1.id)


def test_without_a_human_verdict_it_is_the_latest_done_non_relayed_result(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    r1 = deliver(w, first)
    committed(versions, r1)
    again = rework(w, first, source="relayed")
    r2 = deliver(w, again)
    committed(versions, r2, data=V2, commit="d" * 40)
    edited(versions)
    base = judged.base("ceo", SERVICE, first.id)
    assert base is not None and (base.task, base.result, base.relayed) == (first.id, r1.id, (again.id,))
    human = rework(w, again, source="human")  # a human rework is a non-relayed task: its delivery is the latest judged-by-default one
    r3 = deliver(w, human)
    committed(versions, r3, data=b"| Marta | tbd |\n", commit="e" * 40)
    base = judged.base("ceo", SERVICE, first.id)
    assert base is None or base.result != r2.id  # never the relayed rework's delivery


def test_a_request_that_was_not_delivered_has_no_judged_delivery(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    r1 = deliver(w, first, status="blocked")
    committed(versions, r1)
    again = rework(w, first, source="relayed")
    r2 = deliver(w, again)
    committed(versions, r2, data=V2, commit="d" * 40)
    edited(versions)
    assert judged.base("ceo", SERVICE, first.id) is None


def test_no_relayed_rework_after_it_gives_none(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    r1 = deliver(w, first)
    committed(versions, r1)
    edited(versions)  # the file differs, but nobody relayed anything
    rate(w, first, "reject", "No.")
    assert judged.base("ceo", SERVICE, first.id) is None
    human = rework(w, first, source="human")
    deliver(w, human)
    assert judged.base("ceo", SERVICE, first.id) is None  # a human rework is not a relayed one


def test_a_relayed_rework_that_did_not_touch_the_file_gives_none(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first, r1, again, r2 = the_s2r_flow(w, versions)
    versions.now[MEMO] = blob(V1)  # the file is as the user judged it
    assert judged.base("ceo", SERVICE, first.id) is None


def test_a_missing_file_differs(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first, r1, again, r2 = the_s2r_flow(w, versions)
    del versions.now[MEMO]
    base = judged.base("ceo", SERVICE, first.id)
    assert base is not None and base.changed == (MEMO,)


def test_without_history_a_relayed_result_listing_the_path_counts(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    r1 = deliver(w, first, paths=[MEMO, OTHER])
    rate(w, first, "reject", "No.")
    again = rework(w, first, source="relayed")
    deliver(w, again, paths=[MEMO])  # git knows nothing: only the relayed result's own listing says what it touched
    base = judged.base("ceo", SERVICE, first.id)
    assert base == JudgedBase(task=first.id, result=r1.id, commit="", relayed=(again.id,), changed=(MEMO,), texts=())


def test_without_history_a_relayed_result_that_lists_nothing_of_it_gives_none(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    deliver(w, first, paths=[MEMO])
    rate(w, first, "reject", "No.")
    again = rework(w, first, source="relayed")
    deliver(w, again, paths=[OTHER])
    assert judged.base("ceo", SERVICE, first.id) is None


def test_paths_that_are_not_in_the_organization_are_not_compared(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    deliver(w, first, paths=["/tmp/abs.md", "../up.md", "a//b.md"])
    rate(w, first, "reject", "No.")
    again = rework(w, first, source="relayed")
    deliver(w, again, paths=["/tmp/abs.md", "../up.md", "a//b.md"])
    assert judged.base("ceo", SERVICE, first.id) is None


def test_texts_stay_within_6000_bytes_in_order(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    r1 = deliver(w, first, paths=[MEMO, OTHER, "ceo/work/third.md", "ceo/work/fourth.md"])
    sizes = {MEMO: b"a" * 4000, OTHER: b"b" * 3000, "ceo/work/third.md": b"c" * (JUDGED_BYTES + 1), "ceo/work/fourth.md": "é".encode() * 900}
    for path, data in sizes.items():
        committed(versions, r1, path, data)
        edited(versions, path, b"changed")
    rate(w, first, "reject", "No.")
    again = rework(w, first, source="relayed")
    deliver(w, again, paths=list(sizes))
    base = judged.base("ceo", SERVICE, first.id)
    assert base is not None and base.changed == tuple(sizes)
    # 4000 bytes fit; 4000 + 3000 do not; the third is over the limit on its own (the port answers None); the fourth (1800 bytes) fits after the first
    assert [path for path, _ in base.texts] == [MEMO, "ceo/work/fourth.md"]
    assert sum(len(text.encode()) for _, text in base.texts) <= JUDGED_BYTES


def test_a_text_that_is_not_utf8_is_decoded_with_replacement(w: ReflectionWorld, versions: FixedCheckedVersions, judged: JudgedVersions) -> None:
    first = ask(w)
    r1 = deliver(w, first)
    committed(versions, r1, data=b"caf\xe9\n")
    edited(versions)
    rate(w, first, "reject", "No.")
    again = rework(w, first, source="relayed")
    deliver(w, again)
    base = judged.base("ceo", SERVICE, first.id)
    assert base is not None and base.texts == ((MEMO, "caf\ufffd\n"),)
