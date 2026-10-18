"""Contract of ``MailFingerprint``: the file names of the received boxes and of ``sent``, whatever the implementation."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.mail import MailFingerprint
from orgmcp.mail.testing import IMPLEMENTATIONS, MailHarness

from ._support import agents, make, mid, put, still_red




@pytest.fixture(params=still_red(IMPLEMENTATIONS[MailFingerprint]), ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    made = make(request, tmp_path)
    assert isinstance(made.fingerprint, MailFingerprint)
    agents(made, "ceo", "cto")
    return made


def test_an_agent_without_mail_has_the_empty_fingerprint(h: MailHarness) -> None:
    assert h.fingerprint.fingerprint("ceo") == (frozenset(), frozenset())
    assert h.fingerprint.fingerprint("nobody") == (frozenset(), frozenset())


def test_it_is_the_file_names_of_the_received_boxes_and_of_sent(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "inflight", 2)
    put(h, "ceo", "read", 3)
    put(h, "ceo", "sent", 4, sender="ceo", to="cto")
    assert h.fingerprint.fingerprint("ceo") == (
        frozenset({f"{mid(1)}.md", f"{mid(2)}.md", f"{mid(3)}.md"}),
        frozenset({f"{mid(4, 'ceo')}.md"}),
    )


def test_a_message_that_moves_between_the_received_boxes_keeps_the_fingerprint(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    before = h.fingerprint.fingerprint("ceo")
    h.batches.begin("ceo")
    assert h.fingerprint.fingerprint("ceo") == before
    h.batches.end("ceo", ok=True)
    assert h.fingerprint.fingerprint("ceo") == before


def test_a_new_message_changes_it(h: MailHarness) -> None:
    before = h.fingerprint.fingerprint("ceo")
    put(h, "ceo", "inbox", 1)
    after_received = h.fingerprint.fingerprint("ceo")
    put(h, "ceo", "sent", 2, sender="ceo", to="cto")
    after_sent = h.fingerprint.fingerprint("ceo")
    assert before != after_received != after_sent and after_received[1] == frozenset() and after_sent[0] == after_received[0]


def test_hidden_and_other_files_are_not_in_it(h: MailHarness) -> None:
    h.put("ceo/inbox/.tmp-1-x.md", "x")
    h.put("ceo/inbox/readme.txt", "x")
    assert h.fingerprint.fingerprint("ceo") == (frozenset(), frozenset())


def test_other_agents_do_not_matter(h: MailHarness) -> None:
    before = h.fingerprint.fingerprint("ceo")
    put(h, "cto", "inbox", 1, to="cto")
    assert h.fingerprint.fingerprint("ceo") == before


def test_the_address_is_normalized(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    assert h.fingerprint.fingerprint(" /ceo/ ") == h.fingerprint.fingerprint("ceo") != (frozenset(), frozenset())
