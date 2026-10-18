"""Contract of ``EventSwitch``: ORG.md decides whether events are written, and is read again only when it changes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.settings import EventSwitch
from orgmcp.settings.testing import IMPLEMENTATIONS, SwitchHarness
from orgmcp.settings.tests._red import impls


@pytest.fixture(params=impls(IMPLEMENTATIONS[EventSwitch]))
def h(request: pytest.FixtureRequest, tmp_path: Path) -> SwitchHarness:
    made = cast(Callable[[Path], SwitchHarness], request.param)(tmp_path)
    assert isinstance(made.switch, EventSwitch)
    return made


def document(events: str) -> str:
    return f"---\nmax_depth: 4\n{events}---\n# Mission\n"


def test_no_document_no_events(h: SwitchHarness) -> None:
    assert h.switch.enabled() is False


def test_a_document_without_the_setting_has_events_on(h: SwitchHarness) -> None:
    h.put("# Mission\n\nplain\n")
    assert h.switch.enabled() is True
    h.put(document(""))
    assert h.switch.enabled() is True


@pytest.mark.parametrize(
    "line, expected",
    [
        ("events: true\n", True),
        ("events: false\n", False),
        ("events: no\n", False),  # YAML: a boolean
        ("events: off\n", False),
        ("events: 'false'\n", False),
        ("events: 'No'\n", False),
        ("events: ' OFF '\n", False),
        ("events: '0'\n", False),
        ("events: 0\n", False),
        ("events: 1\n", True),
        ("events: 2\n", True),
        ("events: 'yes'\n", True),
        ("events: 'on'\n", True),
        ("events: 'maybe'\n", True),
        ("events: ''\n", True),
        ("events:\n", True),  # null
        ("events: []\n", True),
        ("events: [0]\n", True),
    ],
)
def test_the_events_setting(h: SwitchHarness, line: str, expected: bool) -> None:
    h.put(document(line))
    assert h.switch.enabled() is expected


def test_a_document_that_is_not_valid_yaml_leaves_events_on(h: SwitchHarness) -> None:
    h.put("---\nevents: [unclosed\n---\nbody\n")
    assert h.switch.enabled() is True


def test_a_change_of_the_document_is_noticed(h: SwitchHarness) -> None:
    h.put(document("events: false\n"))
    assert h.switch.enabled() is False
    h.put(document("events: true\n"))
    assert h.switch.enabled() is True
    h.put(document("events: false\n"))
    assert h.switch.enabled() is False


def test_the_document_is_read_again_only_when_its_stamp_changes(h: SwitchHarness) -> None:
    h.put(document("events: false\n"))
    assert h.switch.enabled() is False
    h.put_unnoticed(document("events: true \n"))  # same size, same time: nothing shows that the file changed
    assert h.switch.enabled() is False
    h.put(document("events: true \n"))  # now the stamp changes
    assert h.switch.enabled() is True


def test_a_change_of_size_is_noticed_without_a_change_of_time(h: SwitchHarness) -> None:
    h.put(document("events: false\n"))
    assert h.switch.enabled() is False
    h.put_unnoticed(document("events: true\n"))  # one character shorter: the stamp (time, size) changes
    assert h.switch.enabled() is True


def test_a_document_that_goes_away_switches_events_off_and_back_on_again(h: SwitchHarness) -> None:
    h.put(document("events: true\n"))
    assert h.switch.enabled() is True
    h.remove()
    assert h.switch.enabled() is False
    h.put(document("events: true\n"))
    assert h.switch.enabled() is True

