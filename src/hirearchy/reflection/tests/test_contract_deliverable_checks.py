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
from hirearchy.reflection.testing import IMPLEMENTATIONS, DeliverableHarness, FixedCheckedVersions, HashBlobIds, blob, fs_world

from ._support import SERVICE, ask, define, populated, rework


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
