"""``YamlBlueprintLoader`` over a dictionary of files: the one rule that no disk can show (a name of 1024 characters or more is text)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.blueprint import BlueprintError
from orgmcp.blueprint._loader import PATH_NAME_MAX, YamlBlueprintLoader
from orgmcp.blueprint.testing import MemoryTextFiles



TEXT = "mission: a mission\n"


def named(length: int) -> Path:
    return Path("/" + "d" * (length - 1))


def test_a_name_just_under_the_limit_is_read_as_a_file() -> None:
    path = named(PATH_NAME_MAX - 1)
    files = MemoryTextFiles({path: TEXT})
    assert YamlBlueprintLoader(files).load(str(path)) == {"mission": "a mission"}
    assert files.reads == [path]


@pytest.mark.parametrize("length", [PATH_NAME_MAX, PATH_NAME_MAX + 76])
def test_a_name_of_the_limit_or_more_is_text_even_when_a_file_has_that_name(length: int) -> None:
    path = named(length)
    files = MemoryTextFiles({path: TEXT})
    with pytest.raises(BlueprintError, match="a blueprint is a mapping"):
        YamlBlueprintLoader(files).load(str(path))
    assert files.reads == []


def test_a_path_object_is_read_whatever_its_length() -> None:
    path = named(PATH_NAME_MAX + 76)
    files = MemoryTextFiles({path: TEXT})
    assert YamlBlueprintLoader(files).load(path) == {"mission": "a mission"}
    assert files.reads == [path]


def test_the_home_directory_is_expanded_in_a_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    files = MemoryTextFiles({tmp_path / "bp.yaml": TEXT})
    assert YamlBlueprintLoader(files).load(Path("~/bp.yaml")) == {"mission": "a mission"}
    assert YamlBlueprintLoader(files).load("~/bp.yaml") == {"mission": "a mission"}
