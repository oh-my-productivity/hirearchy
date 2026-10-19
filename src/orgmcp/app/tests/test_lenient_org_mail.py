"""The dashboard's ``LenientOrg`` reads its mailboxes through the decorator of the mail package (it used to do so itself in ``_box``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.app import Org
from ._lenient_org import LenientOrg
from orgmcp.mail._caching import DirMtimeCachingMailbox


def test_the_lenient_org_skips_and_reports_a_message_it_cannot_read(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    org.send("root", "ceo", "good")
    (org.root / "ceo" / "inbox" / "20260101T000000000000-root-bad0.md").write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    lenient = LenientOrg(org.root)
    assert isinstance(lenient.runtime.mailbox, DirMtimeCachingMailbox)
    assert len(lenient.messages("ceo", "inbox")) == 1 and lenient.unread("ceo") == 2  # the unreadable file still counts as mail
    assert [k for k in lenient.bad] == ["ceo/inbox/20260101T000000000000-root-bad0.md"]
    assert list(lenient.bad.values())[0].startswith("ParserError:")
    with pytest.raises(Exception):  # noqa: B017, PT011 - the plain Org raises on it (yaml error), as it always did
        org.messages("ceo", "inbox")


def test_the_lenient_org_derives_the_task_views_from_the_cached_boxes(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    task = org.delegate("root", "ceo", "T", "g", "a", budget=1)
    (org.root / "ceo" / "inbox" / "20260101T000000000000-root-bad0.md").write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    lenient = LenientOrg(org.root)
    assert [t.id for t in lenient.open_tasks("ceo")] == [task.id] and lenient.outstanding("root")[0].id == task.id


def test_the_lenient_org_has_a_running_agent_when_its_batch_does_not_even_parse(tmp_path: Path) -> None:
    org = Org.init(tmp_path / "org", "mission")
    org.hire("root", "ceo", "Boss", "text")
    inflight = org.root / "ceo" / "inflight"
    inflight.mkdir(exist_ok=True)
    (inflight / "20260101T000000000000-root-bad0.md").write_text("---\nfrom: [oops\n---\nx\n", encoding="utf-8")
    assert LenientOrg(org.root).running("ceo") is True
