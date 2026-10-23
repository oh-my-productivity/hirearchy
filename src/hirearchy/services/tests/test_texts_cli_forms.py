"""The refusals that name an argument give its terminal form too (DR-46): the texts are raised in ``services``, the one layer the MCP tools and the
command line share, so one text serves both; a flag-less text would send a terminal user to an argument they cannot type."""

from __future__ import annotations

import pytest

from hirearchy.services import _define, _feedback, _retire

P2_TEXTS = [
    (_define, "NOT_AN_AMENDMENT"),
    (_define, "PAIR"),
    (_define, "WORDS_LONG"),
    (_define, "NOT_A_REJECTION"),
    (_define, "ANSWERED"),
    (_define, "ABOUT"),
    (_define, "WORDS_ARE_THE_REJECTION"),
    (_define, "LINK_FAILED"),
    (_define, "UNRATED"),
    (_define, "NEEDS_WORDS"),
    (_define, "OPEN_REJECTION"),
    (_feedback, "CONFIRMS_ANSWERED"),
    (_feedback, "CONFIRMS_RECOVERY"),
    (_retire, "RETIRE_UNRATED"),
    (_retire, "RETIRE_OPEN"),
    (_define, "CONTINUES"),
]


@pytest.mark.parametrize(("module", "name"), P2_TEXTS, ids=[name for _, name in P2_TEXTS])
def test_every_p2_text_that_names_an_argument_gives_its_cli_form(module: object, name: str) -> None:
    text: str = getattr(module, name)
    assert "CLI: " in text, f"{name} names an argument and has no terminal form"


@pytest.mark.parametrize(("module", "name"), [p for p in P2_TEXTS if p[1] != "LINK_FAILED"], ids=[n for _, n in P2_TEXTS if n != "LINK_FAILED"])
def test_a_refusal_starts_with_refused_and_says_what_was_not_done(module: object, name: str) -> None:
    text: str = getattr(module, name)
    assert text.startswith("refused: ") and text.rstrip(".").split(". ")[-1] in ("Nothing was written", "Nothing was recorded", "Nothing was retired")
