"""Contract of ``BatchStore``: the mailboxes on disk and the in-memory ones pass the same tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.mail import BatchStore
from orgmcp.mail.testing import IMPLEMENTATIONS, MailHarness

from ._support import BAD_YAML, agents, make, message_text, mid, put, still_red, where




@pytest.fixture(params=still_red(IMPLEMENTATIONS[BatchStore]), ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> MailHarness:
    made = make(request, tmp_path)
    assert isinstance(made.batches, BatchStore)
    agents(made, "ceo", "ceo/eng", "cto")
    return made


def ids(h: MailHarness, addr: str, box: str) -> list[str]:
    return [m.id for m in h.reader.messages(addr, box)]


# ------------------------------------------------------------------------------ begin


def test_begin_moves_the_inbox_into_inflight_and_returns_the_batch(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 2)
    put(h, "ceo", "inbox", 1)
    batch = h.batches.begin("ceo")
    assert [m.id for m in batch] == [mid(1), mid(2)]
    assert ids(h, "ceo", "inbox") == [] and ids(h, "ceo", "inflight") == [mid(1), mid(2)]


def test_begin_takes_the_held_messages_too(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "ceo", "inbox", 2, wake=False, kind="note")
    assert [m.id for m in h.batches.begin("ceo")] == [mid(1), mid(2)]


def test_the_batch_is_the_whole_inflight_box_including_what_was_there(h: MailHarness) -> None:
    put(h, "ceo", "inflight", 1)
    put(h, "ceo", "inbox", 2)
    assert [m.id for m in h.batches.begin("ceo")] == [mid(1), mid(2)]


def test_begin_of_an_empty_inbox_is_an_empty_batch_and_makes_the_inflight_box(h: MailHarness) -> None:
    assert h.batches.begin("ceo") == []
    assert h.listing("ceo/inflight") == []


def test_begin_moves_the_file_unchanged(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    text = h.read(where("ceo", "inbox", mid(1)))
    h.batches.begin("ceo")
    assert h.read(where("ceo", "inflight", mid(1))) == text and h.read(where("ceo", "inbox", mid(1))) is None


def test_begin_leaves_hidden_files_and_other_agents_alone(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    put(h, "cto", "inbox", 2, to="cto")
    h.put("ceo/inbox/.tmp-1-x.md", "half written")
    h.batches.begin("ceo")
    assert h.read("ceo/inbox/.tmp-1-x.md") == "half written" and ids(h, "cto", "inbox") == [mid(2)]


def test_begin_of_the_root_uses_the_boxes_of_the_organization(h: MailHarness) -> None:
    put(h, "root", "inbox", 1, sender="ceo")
    assert [m.id for m in h.batches.begin("root")] == [mid(1, "ceo")]
    assert h.read(f"inflight/{mid(1, 'ceo')}.md") is not None


# ------------------------------------------------------------------------------ end


def test_a_successful_run_moves_the_batch_to_read(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    h.batches.begin("ceo")
    h.batches.end("ceo", ok=True)
    assert ids(h, "ceo", "inflight") == [] and ids(h, "ceo", "read") == [mid(1)] and ids(h, "ceo", "inbox") == []
    assert h.reader.has_inflight("ceo") is False


def test_a_failed_run_puts_the_batch_back_in_the_inbox(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    h.batches.begin("ceo")
    h.batches.end("ceo", ok=False)
    assert ids(h, "ceo", "inflight") == [] and ids(h, "ceo", "inbox") == [mid(1)] and h.reader.unread("ceo") == 1


def test_a_retried_batch_is_the_same_batch(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    first = h.batches.begin("ceo")
    h.batches.end("ceo", ok=False)
    assert [m.id for m in h.batches.begin("ceo")] == [m.id for m in first]


def test_end_makes_the_target_box_when_it_is_not_there(h: MailHarness) -> None:
    put(h, "cto", "inflight", 1, to="cto")
    assert h.listing("cto/read") is None
    h.batches.end("cto", ok=True)
    assert ids(h, "cto", "read") == [mid(1)]


def test_end_without_a_batch_changes_nothing(h: MailHarness) -> None:
    put(h, "ceo", "inbox", 1)
    h.batches.end("ceo", ok=True)
    h.batches.end("ceo", ok=False)
    assert ids(h, "ceo", "inbox") == [mid(1)] and ids(h, "ceo", "read") == []


def test_end_leaves_the_other_agents_batches(h: MailHarness) -> None:
    put(h, "ceo", "inflight", 1)
    put(h, "cto", "inflight", 2, to="cto")
    h.batches.end("ceo", ok=True)
    assert ids(h, "cto", "inflight") == [mid(2)]


def test_end_for_an_agent_that_no_longer_exists_does_nothing(h: MailHarness) -> None:
    """Retired while its run was in flight: its directory is gone, and creating the mailbox again would leave a ghost directory behind."""
    h.batches.end("ghost", ok=False)
    assert h.listing("ghost") is None
    h.batches.end("ghost", ok=True)
    assert h.listing("ghost") is None


# ------------------------------------------------------------------------------ recover


def test_recover_returns_every_inflight_batch_to_its_inbox(h: MailHarness) -> None:
    put(h, "ceo", "inflight", 1)
    put(h, "ceo/eng", "inflight", 2, to="ceo/eng")
    put(h, "cto", "inbox", 3, to="cto")
    assert h.batches.recover() == ["ceo", "ceo/eng"]
    assert ids(h, "ceo", "inbox") == [mid(1)] and ids(h, "ceo/eng", "inbox") == [mid(2)] and ids(h, "cto", "inbox") == [mid(3)]
    assert not ids(h, "ceo", "inflight") and not ids(h, "ceo/eng", "inflight")


def test_recover_is_idempotent(h: MailHarness) -> None:
    put(h, "ceo", "inflight", 1)
    assert h.batches.recover() == ["ceo"]
    assert h.batches.recover() == [] and ids(h, "ceo", "inbox") == [mid(1)]


def test_recover_in_a_quiet_organization_does_nothing(h: MailHarness) -> None:
    assert h.batches.recover() == []


def test_recover_finishes_the_interrupted_deliveries_too(h: MailHarness) -> None:
    put(h, "ceo", "sent", 1, sender="ceo", to="ceo/eng")  # the sender's copy was written, the recipient's was not
    assert h.batches.recover() == []
    assert ids(h, "ceo/eng", "inbox") == [mid(1, "ceo")]


# ------------------------------------------------------------------------------ redeliver_orphans


def orphan(h: MailHarness, n: int, to: str = "ceo/eng", sender: str = "ceo") -> str:
    return put(h, sender, "sent", n, sender=sender, to=to)


def test_a_sent_message_without_a_copy_at_the_recipient_is_delivered(h: MailHarness) -> None:
    msg_id = orphan(h, 1)
    assert h.batches.redeliver_orphans() == [msg_id]
    assert h.read(where("ceo/eng", "inbox", msg_id)) == h.read(where("ceo", "sent", msg_id))


@pytest.mark.parametrize("box", ["inbox", "inflight", "read"])
def test_a_message_the_recipient_has_in_any_box_is_not_delivered_again(h: MailHarness, box: str) -> None:
    msg_id = orphan(h, 1)
    h.put(where("ceo/eng", box, msg_id), h.read(where("ceo", "sent", msg_id)) or "")
    assert h.batches.redeliver_orphans() == []
    for other in {"inbox", "inflight", "read"} - {box}:
        assert h.read(where("ceo/eng", other, msg_id)) is None


def test_a_copy_anywhere_in_the_organization_counts_as_handled(h: MailHarness) -> None:
    """Ids are unique across the organization, so the file names of all received boxes are enough to tell."""
    msg_id = orphan(h, 1)
    h.put(where("cto", "read", msg_id), "elsewhere")
    assert h.batches.redeliver_orphans() == []


def test_a_message_to_an_agent_that_no_longer_exists_is_left_alone(h: MailHarness) -> None:
    orphan(h, 1, to="gone")
    assert h.batches.redeliver_orphans() == []
    assert h.listing("gone") is None


def test_a_sent_file_that_does_not_parse_is_left_alone(h: MailHarness) -> None:
    h.put(where("ceo", "sent", mid(1, "ceo")), BAD_YAML)
    good = orphan(h, 2)
    assert h.batches.redeliver_orphans() == [good]


def test_the_orphans_of_every_agent_are_delivered_root_first_each_in_file_name_order(h: MailHarness) -> None:
    c2, c1 = orphan(h, 2, to="cto"), orphan(h, 1, to="cto")
    r = put(h, "root", "sent", 3, sender="root", to="ceo")
    t = put(h, "cto", "sent", 4, sender="cto", to="root")
    assert h.batches.redeliver_orphans() == [r, c1, c2, t]
    assert ids(h, "ceo", "inbox") == [r] and ids(h, "cto", "inbox") == [c1, c2] and ids(h, "root", "inbox") == [t]


def test_redelivery_is_idempotent(h: MailHarness) -> None:
    msg_id = orphan(h, 1)
    assert h.batches.redeliver_orphans() == [msg_id]
    assert h.batches.redeliver_orphans() == []


def test_the_recipient_is_the_one_in_the_file_normalized(h: MailHarness) -> None:
    h.put(where("ceo", "sent", mid(1, "ceo")), message_text(mid(1, "ceo"), sender="ceo", to=" /ceo/eng/ "))
    assert h.batches.redeliver_orphans() == [mid(1, "ceo")]
    assert ids(h, "ceo/eng", "inbox") == [mid(1, "ceo")]
