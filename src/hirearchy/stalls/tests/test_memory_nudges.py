"""The fake ledger, and the calls the ladder makes of the ledger through the ports (not through the file)."""

from __future__ import annotations

from hirearchy.mail.testing import MemoryMailbox
from hirearchy.stalls import NudgeLedger
from hirearchy.stalls._ports import NudgeRecorder
from hirearchy.stalls.testing import MemoryNudges



def test_the_fake_is_both_ports() -> None:
    fake = MemoryNudges(MemoryMailbox().agents)
    assert isinstance(fake, NudgeLedger) and isinstance(fake, NudgeRecorder)


def test_the_fake_keeps_the_text_the_file_would_hold() -> None:
    fake = MemoryNudges(MemoryMailbox().agents)
    assert fake.text is None
    fake.save({"T-1": {"step": 0, "at": 1.5}})
    assert fake.text == '{\n  "T-1": {\n    "step": 0,\n    "at": 1.5\n  }\n}\n'
