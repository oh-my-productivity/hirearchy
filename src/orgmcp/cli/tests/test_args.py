"""``AtFileText`` on the real file system: the home directory is expanded and the text is read as UTF-8."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.cli._args import AtFileText



def test_a_path_with_a_home_directory_is_expanded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "m.md").write_text("Mission — with a dash.\n", encoding="utf-8")
    assert AtFileText().read("@~/m.md") == "Mission — with a dash.\n"
