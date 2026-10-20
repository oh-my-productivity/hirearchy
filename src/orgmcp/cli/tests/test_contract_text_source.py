"""Contract of ``TextSource``: text is itself; ``@name`` is the text of the file."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from orgmcp.cli._ports import TextSource
from orgmcp.cli.testing import IMPLEMENTATIONS, TextWorld

@pytest.fixture(params=IMPLEMENTATIONS[TextSource], ids=lambda factory: factory.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> TextWorld:
    made = cast(TextWorld, request.param(tmp_path))
    assert isinstance(made.reader, TextSource)
    return made


def test_text_is_itself(w: TextWorld) -> None:
    assert w.reader.read("Write the code.") == "Write the code." and w.reader.read("") == "" and w.reader.read("a @ b") == "a @ b"


def test_an_at_sign_names_a_file_whose_text_is_returned_as_it_is(w: TextWorld) -> None:
    assert w.reader.read(w.make_file("charter.md", "Line one.\nLine two.\n")) == "Line one.\nLine two.\n"


def test_a_missing_file_is_the_error_of_the_file_system(w: TextWorld, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        w.reader.read(f"@{tmp_path / 'missing.md'}")
