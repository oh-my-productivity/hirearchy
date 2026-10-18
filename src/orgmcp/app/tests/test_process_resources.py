"""``ProcessResources``: created once per process, shared by every runtime, emptied by ``reset``."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.app import wiring
from orgmcp.app._resources import CachingMessageParser, ProcessResources
from orgmcp.kernel import Message

pytestmark = pytest.mark.xfail(strict=True, reason="red: M2")


def message_file(directory: Path, name: str = "20260101T000000000000-root-aaaa.md", body: str = "hello") -> Path:
    path = directory / name
    path.write_text(f"---\nid: {path.stem}\nfrom: root\nto: ceo\ntype: note\n---\n{body}\n", encoding="utf-8")
    return path


def test_the_resources_hold_the_parser_they_were_given() -> None:
    parser = CachingMessageParser()
    assert ProcessResources(parser).message_parser is parser


def test_reset_forgets_every_parse_and_keeps_the_objects(tmp_path: Path) -> None:
    parser = CachingMessageParser()
    resources = ProcessResources(parser)
    cache = parser.cache
    parser.parse(message_file(tmp_path))
    assert len(cache) == 1
    resources.reset()
    assert resources.message_parser is parser and parser.cache is cache and len(cache) == 0


def test_reset_of_empty_resources_is_harmless() -> None:
    resources = ProcessResources(CachingMessageParser())
    resources.reset()
    resources.reset()


def test_there_is_one_set_of_resources_per_process() -> None:
    assert wiring.process_resources() is wiring.process_resources()


def test_the_process_parser_is_bounded_like_the_old_module_global() -> None:
    parser = wiring.process_resources().message_parser
    assert parser.cache.__class__.__name__ == "OrderedDict" and parser.max_entries == 50_000


def test_every_runtime_of_the_process_shares_them(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    assert wiring.open_runtime(first).resources is wiring.open_runtime(second).resources is wiring.process_resources()


def test_the_resources_are_usable_without_an_organization(tmp_path: Path) -> None:
    path = message_file(tmp_path)
    assert isinstance(wiring.process_resources().message_parser.parse(path), Message)
