"""``FileRetroDue``: the trigger line of a due retro (design 4.6, D17, Q17): a line in a reply or a listing that tells root to OFFER the retro and to call ``retro()`` only
after the user's yes. It is only text: it sends no message and wakes nobody."""

from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path

from hirearchy.kernel import OrgError
from hirearchy.retro import BriefRecord
from hirearchy.retro._due import FileRetroDue
from hirearchy.retro.testing import FixedSources, MemoryRetroRecords
from hirearchy.settings.testing import MemoryOrgSettings

from ._records import ORIGIN, record
from .test_sources import judged_one_off, sources_of, world

REPLY = (
    "Retro due: {k} verdicts of the user since the last brief ({date}). Once this delivery is settled, offer the user a retro in one line, "
    "and call retro() only after their yes."
)
LISTING = "Retro due: {k} verdicts of the user since the last brief ({date}); offer the user a retro, and call retro() only after their yes."
ORG_MD = "---\nmission: m\n---\nrules\n"


def due_over(new: int, records: MemoryRetroRecords | None = None, org_md: str = ORG_MD) -> tuple[FileRetroDue, FixedSources]:
    sources = FixedSources(new=new)
    return FileRetroDue(sources, records or MemoryRetroRecords(), MemoryOrgSettings(org_md)), sources


def test_due_counts_deliveries_whose_first_counted_human_verdict_came_after_the_last_brief(tmp_path: Path) -> None:
    org = world(tmp_path)
    judged_one_off(org, 2)
    judged_one_off(org, 9)
    time.sleep(0.01)
    held = org.runtime.clock.now()
    time.sleep(0.01)
    for day in (16, 23, 30):
        judged_one_off(org, day)
    records = MemoryRetroRecords()
    records.append(BriefRecord("B1", held, None, "mcp"))
    due = FileRetroDue(sources_of(org), records, org.runtime.settings)
    assert due.due() == REPLY.format(k=3, date=held.strftime("%Y-%m-%d"))  # the 2 before the brief do not count: 3 after it
    assert FileRetroDue(sources_of(org), MemoryRetroRecords(), org.runtime.settings).due() == REPLY.format(k=5, date="none yet")


def test_the_reply_form_and_the_listing_form_word_for_word() -> None:
    records = MemoryRetroRecords()
    records.append(record(1))
    due, sources = due_over(4, records)
    date = (ORIGIN + timedelta(days=1)).strftime("%Y-%m-%d")
    assert due.due() == REPLY.format(k=4, date=date) and due.due(listing=True) == LISTING.format(k=4, date=date)
    assert sources.afters == [ORIGIN + timedelta(days=1), ORIGIN + timedelta(days=1)]  # the count is of the verdicts after the last brief's time


def test_before_the_first_brief_the_date_reads_none_yet() -> None:
    due, sources = due_over(3)
    assert due.due() == REPLY.format(k=3, date="none yet") and due.due(listing=True) == LISTING.format(k=3, date="none yet") and sources.afters == [None, None]


def test_below_after_verdicts_it_is_empty() -> None:
    assert due_over(2)[0].due() == "" and due_over(2)[0].due(listing=True) == "" and due_over(0)[0].due() == ""
    assert due_over(3, org_md="---\nmission: m\nretro:\n  after_verdicts: 5\n---\nrules\n")[0].due() == ""
    assert due_over(5, org_md="---\nmission: m\nretro:\n  after_verdicts: 5\n---\nrules\n")[0].due().startswith("Retro due: 5 verdicts")


def test_an_unreadable_source_gives_empty() -> None:
    records = MemoryRetroRecords()
    records.unreadable = "not a ledger"
    assert due_over(9, records)[0].due() == ""  # the ledger cannot be read
    assert FileRetroDue(FixedSources(new=9), MemoryRetroRecords(), MemoryOrgSettings(None)).due() == ""  # no ORG.md to read the threshold from

    class Failing(FixedSources):
        def new_verdicts(self, after: object) -> int:
            raise OrgError("the cases cannot be read")

    assert FileRetroDue(Failing(), MemoryRetroRecords(), MemoryOrgSettings(ORG_MD)).due() == ""


def test_the_trigger_is_a_reply_line_and_wakes_nobody(tmp_path: Path) -> None:
    org = world(tmp_path)
    for day in (2, 9, 16):
        judged_one_off(org, day)
    boxes = sorted(p.relative_to(org.root).as_posix() for p in org.root.rglob("*") if p.is_file() and ".git/" not in p.as_posix() and ".runtime/events" not in p.as_posix())
    records = MemoryRetroRecords()
    line = FileRetroDue(sources_of(org), records, org.runtime.settings).due()
    assert line.startswith("Retro due: 3 verdicts") and "\n" not in line and records.records() == ()
    assert sorted(p.relative_to(org.root).as_posix() for p in org.root.rglob("*") if p.is_file() and ".git/" not in p.as_posix() and ".runtime/events" not in p.as_posix()) == boxes
