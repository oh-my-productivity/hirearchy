"""Contract of ``IdGenerator``: the real generator and the deterministic one produce ids of the same shape."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from orgmcp.kernel import IdGenerator, stamp_of
from orgmcp.kernel.tests._red import impls

SHAPE = re.compile(r"\d{8}T\d{12}-(?P<sender>[^-]+)-[0-9a-f]{4}")


@pytest.fixture(params=impls(IdGenerator))
def ids(request: pytest.FixtureRequest, tmp_path: Path) -> IdGenerator:
    made = cast(Callable[[Path], IdGenerator], request.param)(tmp_path)
    assert isinstance(made, IdGenerator)
    return made


def test_the_id_is_a_timestamp_the_sender_and_four_hex_digits(ids: IdGenerator) -> None:
    match = SHAPE.fullmatch(ids.message_id("ceo"))
    assert match is not None and match["sender"] == "ceo"


def test_a_slash_in_the_sender_becomes_a_dot(ids: IdGenerator) -> None:
    assert SHAPE.fullmatch(ids.message_id("ceo/eng")) is not None
    assert ids.message_id("ceo/eng").split("-")[1] == "ceo.eng"


def test_the_timestamp_part_is_readable_as_a_time(ids: IdGenerator) -> None:
    assert stamp_of(ids.message_id("ceo")) is not None


def test_timestamps_never_go_backwards(ids: IdGenerator) -> None:
    stamps = [ids.message_id("ceo")[:21] for _ in range(50)]
    assert stamps == sorted(stamps)


def test_ids_are_unique(ids: IdGenerator) -> None:
    made = [ids.message_id("ceo") for _ in range(1000)]
    assert len(set(made)) == len(made)
