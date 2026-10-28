"""Contract of ``Notices``: every registered implementation renders the notices byte for byte as before the move."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest

from hirearchy.templates import Notices
from hirearchy.templates.testing import IMPLEMENTATIONS

from ._cases import FLAGS, NOTICE_CASES, Case
from ._golden import expected, render


@pytest.fixture(params=IMPLEMENTATIONS[Notices], ids=lambda factory: factory.__name__)
def notices(request: pytest.FixtureRequest) -> Notices:
    made = cast(Callable[[], Notices], request.param)()
    assert isinstance(made, Notices)
    return made


@pytest.mark.parametrize("case", NOTICE_CASES, ids=lambda case: case.name)
def test_the_text_is_byte_identical_to_the_text_before_the_move(notices: Notices, case: Case) -> None:
    assert render(notices, case) == expected(case.name)


@pytest.mark.parametrize("flag", FLAGS)
def test_a_review_item_carries_the_action_of_its_flag_unless_told_not_to(notices: Notices, flag: str) -> None:
    with_action = notices.review_item("ceo/eng", flag, "why")
    assert with_action.startswith(f"- `ceo/eng` {flag}: why\n  -> ") and "{a}" not in with_action and "ceo/eng" in with_action.split("\n  -> ")[1]
    assert notices.review_item("ceo/eng", flag, "why", act=False) == f"- `ceo/eng` {flag}: why"


def test_a_branch_item_points_at_the_report_not_at_a_flag_action(notices: Notices) -> None:
    assert notices.review_item("ceo/eng", "idle", "why", branch="ceo") == (
        "- `ceo` team: `ceo/eng` is idle: why\n  -> ask `ceo` to deal with it, or step in via its charter"
    )


def test_an_unknown_flag_that_asks_for_an_action_is_refused(notices: Notices) -> None:
    with pytest.raises(KeyError):
        notices.review_item("ceo/eng", "no_such_flag", "why")
    assert notices.review_item("ceo/eng", "no_such_flag", "why", act=False) == "- `ceo/eng` no_such_flag: why"


def test_the_failure_notice_differs_by_audience_only_after_the_first_line(notices: Notices) -> None:
    human, parent = notices.failures("a", 2, "log"), notices.failures("a", 2, "log", to_human=False)
    head = "`a` failed 2 runs in a row and is paused. Last run log: log\n"
    assert human == head + "A human must inspect it and run `hirearchy resume a`."
    assert parent.startswith(head) and "`delegate`" in parent and "hirearchy resume" not in parent


def test_the_root_summary_names_the_managers_that_were_not_told_only_when_there_are_some(notices: Notices) -> None:
    assert "not notified" not in notices.review_root("s", ["- i"], {})
    assert notices.review_root("s", ["- i"], {"ceo": "paused"}).endswith("Managers not notified: `ceo` (paused).")


def test_a_manager_note_counts_its_items(notices: Notices) -> None:
    assert notices.review_manager("ceo", ["- a", "- b"]).startswith("Health review: 2 new problem(s) among your direct reports.\n- a\n- b\n\n")


def test_the_low_quality_action_names_escapes_and_the_regression_list(notices: Notices) -> None:
    text = notices.review_item("ceo/eng", "low_quality", "why").split("\n  -> ")[1]
    assert text == (
        "compare `ceo/eng`'s last checks with the client's rejections it let through (escapes, and its re-checks after a FAIL): if you own a "
        "service, make sure its review tasks carry the regression list. Its charter is the plan's: the retro brief shows the user these escapes."
    )
