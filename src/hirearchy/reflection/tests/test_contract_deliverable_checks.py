"""Contract of ``DeliverableChecks``: the real checks over the fs world (real files in a deliverable folder) and the fixed findings of a test."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import ROOT, Message
from hirearchy.reflection import DeliverableChecks, DeliverableFinding
from hirearchy.reflection._deliverable_checks import FolderDeliverableChecks
from hirearchy.reflection._deliverables import FsDeliverableFolder
from hirearchy.reflection.testing import (
    IMPLEMENTATIONS, DeliverableHarness, FixedCheckedVersions, FixedDeliverableChecks, HashBlobIds, ReflectionWorld, blob, fs_world,
)

from ._support import SERVICE, ask, define, populated, rate, rework


@pytest.fixture(params=IMPLEMENTATIONS[DeliverableChecks], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> DeliverableHarness:
    made = cast(Callable[[Path], DeliverableHarness], request.param)(tmp_path)
    assert isinstance(made.checks, DeliverableChecks)
    return made


def test_an_actor_without_services_has_no_findings(h: DeliverableHarness) -> None:
    assert h.checks.findings(ROOT) == []  # nothing is there yet
    assert h.checks.findings("ceo/eng") == [] and h.checks.findings("ceo/eng", "weekly-brief") == []
    h.populate()
    assert h.checks.findings("ceo/eng") == []  # an agent that requests no service


def test_findings_are_deliverable_findings(h: DeliverableHarness) -> None:
    h.populate()
    (found,) = h.checks.findings(ROOT)
    assert isinstance(found, DeliverableFinding)
    assert (found.name, found.kind, found.services, found.file, found.relayed) == ("x.md", "unknown", (h.service,), False, ())
    assert h.checks.findings(ROOT, h.service) == [found]  # the folder of that service
    assert h.checks.findings(ROOT, "other-service") == []
    assert h.checks.findings(ROOT) == h.checks.findings(ROOT)  # asking again changes nothing


def test_the_e5_shape_over_real_files_is_a_relayed_finding(tmp_path: Path) -> None:
    """E5 s1: the file is the copy the user saw (aae2, the user's rework); root's own rework 963a changed the team's copy after it."""
    w = populated(fs_world(tmp_path))
    folder, memo, versions = tmp_path / "deliverables", "lead/work/memo.md", FixedCheckedVersions()
    define(w, deliverable={"description": "one markdown file", "path": str(folder)})

    def delivery(task: Message, data: bytes) -> None:
        body = f"## Summary\nok\n\n## Artifacts\n- {memo} (3 words)\n"
        result = w.s.d.post(Message(sender=task.to, to=task.sender, type="result", status="done", reply_to=task.id, body=body, title="Result"))
        versions.at[(result.id, memo)] = ("c1", blob(data))

    first = ask(w)
    delivery(first, b"team v1\n")
    human = rework(w, first)
    delivery(human, b"team v2\n")
    relayed = rework(w, human, source="relayed")
    delivery(relayed, b"team v3\n")
    folder.mkdir()
    written = folder / "memo.md"
    written.write_bytes(b"team v2\n")
    later = w.s.d.clock.now() + timedelta(days=1)
    os.utime(written, ns=(int(later.timestamp() * 1e9),) * 2)
    checks = FolderDeliverableChecks(w.s.catalog, w.history, w.s.d.mail, FsDeliverableFolder(), versions, HashBlobIds(), w.s.d.clock)
    (found,) = checks.findings(ROOT, SERVICE)
    assert (found.name, found.kind, found.task, found.relayed, found.file) == ("memo.md", "relayed", human.id, (relayed.id,), False)


# ------------------------------------------------------------------------------------------------------------------------ written and settled (0b 4.3)

MEMO = "lead/work/memo.md"


def edited_folder(tmp_path: Path) -> tuple[ReflectionWorld, Path, Message, FolderDeliverableChecks]:
    """The fs world with a request delivered (the team's copy held ``team v1``) and an empty deliverable folder, and the real checks over it."""
    w = populated(fs_world(tmp_path))
    folder, versions = tmp_path / "deliverables", FixedCheckedVersions()
    define(w, deliverable={"description": "one markdown file", "path": str(folder)})
    task = ask(w)
    body = f"## Summary\nok\n\n## Artifacts\n- {MEMO} (3 words)\n"
    result = w.s.d.post(Message(sender=task.to, to=task.sender, type="result", status="done", reply_to=task.id, body=body, title="Result"))
    versions.at[(result.id, MEMO)] = ("c1", blob(b"team v1\n"))
    folder.mkdir()
    return w, folder, task, FolderDeliverableChecks(w.s.catalog, w.history, w.s.d.mail, FsDeliverableFolder(), versions, HashBlobIds(), w.s.d.clock)


def write(w: ReflectionWorld, path: Path, data: bytes, days: float) -> int:
    """The user's file, last written ``days`` after the fake clock's now; returns its mtime in microseconds."""
    path.write_bytes(data)
    at = w.s.d.clock.now() + timedelta(days=days)
    os.utime(path, ns=(int(at.timestamp() * 1e9),) * 2)
    return path.stat().st_mtime_ns // 1000


def test_a_differs_finding_carries_the_files_write_time(tmp_path: Path) -> None:
    w, folder, task, checks = edited_folder(tmp_path)
    mtime = write(w, folder / "memo.md", b"edited\n", 1)
    (found,) = checks.findings(ROOT, SERVICE)
    assert (found.kind, found.task, found.written, found.settled) == ("differs", task.id, mtime, False)
    other = write(w, folder / "notes.md", b"mine\n", 1)
    by_name = {f.name: f for f in checks.findings(ROOT, SERVICE)}
    assert (by_name["notes.md"].kind, by_name["notes.md"].written) == ("unknown", other)  # the time is on the other kinds a file gets as well


def test_settled_true_returns_the_settled_findings_marked(tmp_path: Path) -> None:
    w, folder, task, checks = edited_folder(tmp_path)
    before = write(w, folder / "memo.md", b"edited\n", 1)
    w.s.d.clock.advance(3 * 86400)
    rate(w, task, "accept")  # the user's own verdict, after the edit: P3 leaves the finding out
    after = write(w, folder / "notes.md", b"mine, later\n", 1)  # written after the verdict: a new finding
    assert [(f.name, f.settled) for f in checks.findings(ROOT, SERVICE, settled=True)] == [("memo.md", True), ("notes.md", False)]
    memo, notes = checks.findings(ROOT, SERVICE, settled=True)
    assert (memo.kind, memo.task, memo.written, notes.kind, notes.written) == ("differs", task.id, before, "unknown", after)


def test_the_default_leaves_settled_findings_out_as_today(tmp_path: Path) -> None:
    w, folder, task, checks = edited_folder(tmp_path)
    write(w, folder / "memo.md", b"edited\n", 1)
    w.s.d.clock.advance(3 * 86400)
    rate(w, task, "accept")
    assert checks.findings(ROOT, SERVICE) == [] == checks.findings(ROOT, SERVICE, settled=False)  # as before 0b
    write(w, folder / "notes.md", b"mine, later\n", 1)
    assert [f.name for f in checks.findings(ROOT, SERVICE)] == ["notes.md"]
    assert all(f.settled is False for f in checks.findings(ROOT))


def test_the_fixed_checks_keep_the_settled_ones_apart_too() -> None:
    settled = DeliverableFinding(folder="/f", services=(SERVICE,), name="a.md", kind="differs", written=5, settled=True)
    open_one = DeliverableFinding(folder="/f", services=(SERVICE,), name="b.md", kind="unknown")
    fixed = FixedDeliverableChecks({ROOT: [settled, open_one]})
    assert fixed.findings(ROOT) == [open_one] and fixed.findings(ROOT, settled=False) == [open_one]
    assert fixed.findings(ROOT, settled=True) == [settled, open_one]
    assert fixed.findings(ROOT, SERVICE, settled=True) == [settled, open_one] and fixed.findings(ROOT, "other", settled=True) == []
