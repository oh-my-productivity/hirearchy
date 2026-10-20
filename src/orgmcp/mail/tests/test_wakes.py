"""``wakes``: whether the message in a file wakes its recipient (the function behind ``FsMailbox.unread`` and the static ``Org._wakes`` of the facade)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.mail._parser import CachingMessageParser
from orgmcp.mail._wakes import wakes

HEAD = "---\nfrom: root\nto: ceo\ntype: note\n"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (HEAD + "---\nx\n", True),  # no `wake` key: it wakes
        (HEAD + "wake: false\n---\nx\n", False),  # held back until the next real run
        (HEAD + "wake: true\n---\nx\n", True),
        ("---\nfrom: [oops\n---\nx\n", True),  # unparsable: still mail, a run should look at it
        ("", True),
    ],
)
def test_a_message_wakes_unless_it_says_otherwise(tmp_path: Path, text: str, expected: bool) -> None:
    path = tmp_path / "m.md"
    path.write_text(text, encoding="utf-8")
    assert wakes(CachingMessageParser(), path) is expected


def test_a_file_that_is_not_there_counts_as_mail(tmp_path: Path) -> None:
    assert wakes(CachingMessageParser(), tmp_path / "absent.md") is True
