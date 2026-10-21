"""``RecordingNotices`` (``templates.testing``): what a consumer's unit test may rely on."""

from __future__ import annotations

import pytest

from hirearchy.templates import Notices
from hirearchy.templates.testing import RecordingNotices

def test_it_is_a_notices() -> None:
    assert isinstance(RecordingNotices(), Notices)


def test_it_records_every_call_with_its_defaults_filled_in() -> None:
    notices = RecordingNotices()
    notices.failures("a", 3, "log")
    notices.review_item("a", "idle", "why")
    notices.review_root("s", ["- i"], {"ceo": "paused"})
    assert notices.calls == [
        ("failures", ("a", 3, "log", True)),
        ("review_item", ("a", "idle", "why", True, None)),
        ("review_root", ("s", ("- i",), {"ceo": "paused"})),
    ]


def test_the_text_it_returns_names_the_method_and_the_arguments() -> None:
    notices = RecordingNotices()
    assert notices.budget("ceo/eng", 3) == "budget: ceo/eng | 3"
    assert notices.nudge("T-1", "Build") == "nudge: T-1 | Build"
    assert notices.stalled("ceo", "T-1", "Build", ["ceo", "root"]) == "stalled: ceo | T-1 | Build | ['ceo', 'root']"


def test_two_recorders_do_not_share_their_calls() -> None:
    first, second = RecordingNotices(), RecordingNotices()
    first.nudge("T-1", "t")
    assert second.calls == []
