"""``encode_line``: one event as one JSON line of fewer than ``LINE_MAX`` bytes; the shrink order is part of the file format."""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path

import pytest

from orgmcp.eventlog import ENVELOPE, LINE_MAX
from orgmcp.kernel import JsonObject
from orgmcp.telemetry._encode import encode_line

from . import _oracle


def record(**fields: object) -> JsonObject:
    return {"v": 1, "ts": "2026-10-18T10:00:00.000001+00:00", "seq": 1, "proc": "cli", "pid": 42, "kind": "custom.kind",
            "actor": "root", "run": None, "trace": None, **fields}


def test_a_small_record_is_one_compact_line_with_the_keys_in_order() -> None:
    data = encode_line(record(thing=1, text="héllo ✓"))
    assert data == ('{"v":1,"ts":"2026-10-18T10:00:00.000001+00:00","seq":1,"proc":"cli","pid":42,"kind":"custom.kind","actor":"root",'
                    '"run":null,"trace":null,"thing":1,"text":"héllo ✓"}\n').encode()


def test_what_json_cannot_hold_is_written_as_its_text() -> None:
    event = json.loads(encode_line(record(path=Path("/x/y"), when=datetime(2026, 1, 1), n=float("inf"))))
    assert event["path"] == "/x/y" and event["when"] == "2026-01-01 00:00:00" and event["n"] == float("inf")


def test_a_lone_surrogate_is_replaced_and_the_line_stays_valid_utf8() -> None:
    event = json.loads(encode_line(record(text="a \ud800 b")).decode("utf-8"))
    assert event["text"].startswith("a ") and event["text"].endswith(" b")


def test_a_failing_serializer_raises_for_the_caller_to_count() -> None:
    class Bad:
        def __str__(self) -> str:
            raise RuntimeError("no string for you")

    with pytest.raises(RuntimeError, match="no string for you"):
        encode_line(record(bad=Bad()))


def test_a_circular_value_raises_for_the_caller_to_count() -> None:
    loop: JsonObject = {}
    loop["self"] = loop
    with pytest.raises(ValueError):
        encode_line(record(loop=loop))


def test_a_line_just_under_the_limit_is_left_alone() -> None:
    base = len(encode_line(record(pad="")))
    data = encode_line(record(pad="x" * (LINE_MAX - base)))
    assert len(data) == LINE_MAX and b"truncated" not in data
    assert b'"truncated":true' in encode_line(record(pad="x" * (LINE_MAX - base + 1)))


def test_the_first_shrink_clips_texts_to_300_and_lists_to_25_items_and_marks_the_line() -> None:
    event = json.loads(encode_line(record(text="x" * 9000, items=[f"item-{i}" for i in range(500)], nested={"a": "y" * 400})))
    assert event["truncated"] is True and len(event["text"]) == 300 and event["text"].endswith("…")
    assert len(event["items"]) == 25 and len(event["nested"]["a"]) == 300


def test_the_second_shrink_clips_texts_to_60_and_lists_to_5_items() -> None:
    event = json.loads(encode_line(record(**{f"field{i}": "z" * 300 for i in range(40)}, items=[f"item-{i}" for i in range(500)])))
    assert event["truncated"] is True and len(event["field0"]) == 60 and len(event["items"]) == 5


def test_the_envelope_is_never_shrunk() -> None:
    event = json.loads(encode_line(record(text="x" * 50_000, trace="T" * 400)))
    assert event["trace"] == "T" * 400 and list(event)[: len(ENVELOPE)] == list(ENVELOPE)


def test_the_third_step_drops_the_biggest_fields_first_until_it_fits() -> None:
    fields = {f"field{i:03d}": 10 ** (100 + i) for i in range(120)}  # numbers: the first two shrinks leave them alone
    data = encode_line(record(**fields))
    event = json.loads(data)
    assert len(data) <= LINE_MAX and event["truncated"] is True
    kept = [k for k in event if k.startswith("field")]
    assert kept and all(k in fields for k in kept) and len(kept) < 120
    assert "field000" in kept and "field119" not in kept  # the longest value goes first


def test_the_last_resort_cuts_the_line_itself() -> None:
    data = encode_line(record(trace="T" * 9000))
    assert len(data) == LINE_MAX and data.endswith(b"\n")


@pytest.mark.parametrize("seed", range(12))
def test_the_bytes_are_those_of_the_legacy_encoder(seed: int) -> None:
    rng = random.Random(seed)
    words = ["alpha", "βeta", "γ" * 80, "x" * 700, "é✓", "", "a b c"]

    def value(depth: int = 0) -> object:
        kind = rng.randrange(7 if depth < 4 else 4)
        if kind == 0:
            return rng.choice(words) * rng.randrange(1, 40)
        if kind == 1:
            return rng.randrange(-5, 10**6)
        if kind == 2:
            return None if rng.random() < 0.5 else rng.random() < 0.5
        if kind == 3:
            return rng.choice(words)
        if kind == 4:
            return [value(depth + 1) for _ in range(rng.randrange(0, 40))]
        if kind == 5:
            return {f"k{rng.randrange(100)}": value(depth + 1) for _ in range(rng.randrange(0, 40))}
        return Path(f"/p/{rng.choice(words)}")

    fields = {f"f{i}": value() for i in range(rng.randrange(1, 30))}
    rec = record(**fields)
    assert encode_line(dict(rec)) == _oracle.encode(dict(rec))
