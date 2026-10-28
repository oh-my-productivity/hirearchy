"""The kinds of the evidence gate's refusals (design 4.3 D10): a stored tool error is classified by the gate's fixed phrases, and the phrase survives the 500-character clip."""

from __future__ import annotations

from hirearchy.kernel import Message, clip
from hirearchy.reflection import GATE_REFUSALS, Assertion, Verdict, gate_refusal_kind
from hirearchy.reflection._evidence import RELAYED_LINK, _c_words, _no_client_evidence, _one_case
from hirearchy.services import Criterion

ERROR_MAX = 500  # mcp_server/_recorder.py: the longest error text that goes into an event


def no_client_evidence(notes: tuple[str, ...] = ("verdict 20260101T000100000000-root-0001 is an accept",)) -> str:
    return _no_client_evidence("weekly-brief", "root", "none yet", notes, "Read the whole request before you start, every time, in order.")


def one_case() -> str:
    note = Message(sender="root", to="ceo", type="note", body="No.", id="20260101T000100000000-root-0001", feedback="reject")
    g = Assertion("R1", "case-1", Verdict("reject", "Not right.", None, "t1", 0, note), ("C1",), "confirmed")
    return _one_case("weekly-brief", "root", "none yet", {"C1": Criterion("C1", "a", 1, "root", True)}, g)


def not_the_clients_words() -> str:
    added = [Criterion("C9", "Every row has a date.", 2, "root", True), Criterion("C10", "Owners are named.", 2, "root", True)]
    return _c_words("weekly-brief", "root", added, "Always add a date to every row of the table, and name the owners.")


def test_each_gate_refusal_is_classified_by_its_fixed_phrase() -> None:
    assert gate_refusal_kind(no_client_evidence()) == "no client evidence"
    assert gate_refusal_kind(one_case()) == "one case only"
    assert gate_refusal_kind(not_the_clients_words()) == "not the client's words"
    assert [kind for kind, _ in GATE_REFUSALS] == ["no client evidence", "one case only", "not the client's words"]


def test_the_kind_survives_the_500_character_clip() -> None:
    for error in (no_client_evidence(), one_case(), not_the_clients_words()):
        assert len(error) > ERROR_MAX  # the stored error is cut
        assert gate_refusal_kind(clip(error, ERROR_MAX)) == gate_refusal_kind(error) is not None


def test_a_relayed_link_reads_no_client_evidence() -> None:
    assert gate_refusal_kind(no_client_evidence((RELAYED_LINK.format(id="C3"),))) == "no client evidence"


def test_another_error_has_no_kind() -> None:
    assert gate_refusal_kind("refused: the playbook is at its cap of 1000 words.") is None
    assert gate_refusal_kind("") is None
    assert gate_refusal_kind("not an owner of this service. " * 10 + one_case()) is None  # the phrases are the start of the gate's own words
