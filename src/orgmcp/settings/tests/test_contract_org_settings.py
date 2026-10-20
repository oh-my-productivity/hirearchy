"""Contract of ``OrgSettings``: the file-backed settings, the in-memory fake and the caching decorator pass the same tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.settings import DEFAULT_CONFIG, DEFAULT_MODEL, OrgSettings
from orgmcp.settings.testing import IMPLEMENTATIONS, SettingsHarness
from orgmcp.settings.tests._reach import yaml_error


@pytest.fixture(params=IMPLEMENTATIONS[OrgSettings], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> SettingsHarness:
    made = cast(Callable[[Path], SettingsHarness], request.param)(tmp_path)
    assert isinstance(made.settings, OrgSettings)
    return made


def document(settings: str = "", body: str = "# Mission\n\nStudy octopuses.\n") -> str:
    return f"---\n{settings}---\n{body}"


def test_without_a_frontmatter_block_the_config_is_the_defaults(h: SettingsHarness) -> None:
    h.put("# Mission\n\nStudy octopuses.\n")
    assert h.settings.config() == DEFAULT_CONFIG


def test_the_frontmatter_is_merged_over_the_defaults(h: SettingsHarness) -> None:
    h.put(document("max_depth: 7\npoll_seconds: 0.05\nflavour: mint\n"))
    config = h.settings.config()
    assert config == {**DEFAULT_CONFIG, "max_depth": 7, "poll_seconds": 0.05, "flavour": "mint"}
    assert config["max_hops"] == 40


def test_a_frontmatter_that_is_not_a_mapping_means_the_defaults(h: SettingsHarness) -> None:
    h.put(document("- a\n- b\n", "body\n"))
    assert h.settings.config() == DEFAULT_CONFIG
    assert h.settings.rules() == "body"


def test_the_returned_config_is_not_the_defaults_themselves(h: SettingsHarness) -> None:
    h.put(document("max_depth: 7\n"))
    before = dict(DEFAULT_CONFIG)
    h.settings.config()["max_depth"] = 99
    h.settings.config()["extra"] = 1
    assert DEFAULT_CONFIG == before


def test_a_change_of_the_document_is_seen_by_the_next_call(h: SettingsHarness) -> None:
    h.put(document("max_depth: 7\n"))
    assert h.settings.config()["max_depth"] == 7
    h.put(document("max_depth: 2\n", "# Mission\n\nSomething else entirely.\n"))
    assert h.settings.config()["max_depth"] == 2
    assert "Something else entirely." in h.settings.rules()


def test_the_rules_are_the_body_stripped(h: SettingsHarness) -> None:
    h.put(document("max_depth: 7\n", "\n\n# Mission\n\nStudy octopuses.\n\n1. Be kind.\n  \n\n"))
    assert h.settings.rules() == "# Mission\n\nStudy octopuses.\n\n1. Be kind."


def test_without_a_frontmatter_block_the_whole_text_is_the_rules(h: SettingsHarness) -> None:
    h.put("  # Mission\n\nplain  \n")
    assert h.settings.rules() == "# Mission\n\nplain"


@pytest.mark.parametrize(
    "line, expected",
    [
        ("default_model: claude-haiku-4.5\n", "claude-haiku-4.5"),
        ("default_model: '  m2  '\n", "m2"),
        ("default_model:\n", DEFAULT_MODEL),  # null
        ("default_model: ''\n", DEFAULT_MODEL),
        ("default_model: '   '\n", DEFAULT_MODEL),
        ("", DEFAULT_MODEL),  # missing
    ],
)
def test_the_default_model(h: SettingsHarness, line: str, expected: str) -> None:
    h.put(document(line))
    assert h.settings.default_model() == expected


@pytest.mark.parametrize(
    "line, key, kind, expected",
    [
        ("poll_seconds: 0.05\n", "poll_seconds", float, 0.05),
        ("poll_seconds: '0.5'\n", "poll_seconds", float, 0.5),
        ("poll_seconds: 3\n", "poll_seconds", float, 3.0),
        ("run_timeout: '1800'\n", "run_timeout", float, 1800.0),
        ("run_timeout: ' 90 '\n", "run_timeout", int, 90),
        ("stall_after: 1e3\n", "stall_after", float, 1000.0),  # YAML reads this as the text "1e3"
        ("max_parallel: 4\n", "max_parallel", int, 4),
        ("max_parallel: 2.9\n", "max_parallel", int, 2),
        ("max_parallel: true\n", "max_parallel", int, 3),  # a boolean is not a number
        ("max_parallel: .nan\n", "max_parallel", int, 3),
        ("max_parallel: .inf\n", "max_parallel", int, 3),
        ("max_parallel: abc\n", "max_parallel", int, 3),
        ("max_parallel: [2]\n", "max_parallel", int, 3),
        ("max_parallel:\n", "max_parallel", int, 3),
        ("", "max_parallel", int, 3),
        ("", "heartbeat_seconds", float, 60.0),
    ],
)
def test_a_numeric_setting(h: SettingsHarness, line: str, key: str, kind: type, expected: float) -> None:
    h.put(document(line))
    got = h.settings.number(key, kind)
    assert got == expected and type(got) is kind


def test_a_numeric_setting_is_a_float_unless_asked_otherwise(h: SettingsHarness) -> None:
    h.put(document(""))
    got = h.settings.number("poll_seconds")
    assert got == 2.0 and type(got) is float


def test_a_numeric_setting_that_has_no_default_is_an_error_when_missing(h: SettingsHarness) -> None:
    h.put(document(""))
    with pytest.raises(KeyError):
        h.settings.number("no_such_setting")


@pytest.mark.parametrize(
    "line, expected",
    [
        ("max_message_chars: 500\n", 500),
        ("max_message_chars: '500'\n", 500),
        ("max_message_chars: 12.7\n", 12),
        ("max_message_chars: 0\n", 20000),
        ("max_message_chars: -5\n", 20000),
        ("max_message_chars: abc\n", 20000),
        ("max_message_chars:\n", 20000),
        ("max_message_chars: [5]\n", 20000),
        ("max_message_chars: true\n", 1),  # int(True) == 1: the original rule, kept as it is
        ("", 20000),
    ],
)
def test_the_message_cap(h: SettingsHarness, line: str, expected: int) -> None:
    h.put(document(line))
    assert h.settings.message_cap() == expected


def test_a_missing_document(h: SettingsHarness) -> None:
    h.remove()
    if h.lenient:
        assert h.settings.config() == DEFAULT_CONFIG
        assert h.settings.message_cap() == 20000 and h.settings.default_model() == DEFAULT_MODEL
    else:
        with pytest.raises(FileNotFoundError):
            h.settings.config()
    with pytest.raises(FileNotFoundError):
        h.settings.rules()


def test_a_document_that_is_not_valid_yaml(h: SettingsHarness) -> None:
    h.put("---\nkey: [unclosed\n---\nbody\n")
    if h.lenient:
        assert h.settings.config() == DEFAULT_CONFIG
    else:
        with pytest.raises(yaml_error()):
            h.settings.config()
    with pytest.raises(yaml_error()):
        h.settings.rules()


def test_a_document_that_comes_back_is_read_again(h: SettingsHarness) -> None:
    h.remove()
    h.put(document("max_depth: 6\n"))
    assert h.settings.config()["max_depth"] == 6
