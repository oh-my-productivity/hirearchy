"""``JsonArgumentSummarizer`` against the frozen ``summarize_args`` of the first version on a corpus of tool-call arguments."""

from __future__ import annotations

import random
from pathlib import Path
from types import MappingProxyType

import pytest

from orgmcp.telemetry._summarize import JsonArgumentSummarizer

from . import _oracle

NAMES = ["to", "task_id", "status", "name", "title", "path", "inputs", "artifacts", "tools", "body", "goal", "acceptance", "budget",
         "force", "inputs_map", "tags", "blob", "workspace", "kind", "plan_id", "verdict", "since", "view", "reply_to", "report", "x"]


def test_a_read_only_mapping_is_enough() -> None:
    assert JsonArgumentSummarizer().summarize(MappingProxyType({"to": "ceo", "body": "abc"})) == {"to": "ceo", "body_chars": 3}


@pytest.mark.parametrize("seed", range(25))
def test_it_summarizes_like_the_frozen_function(seed: int) -> None:
    rng = random.Random(seed)
    words = ["", "ceo", "ceo/eng", "x" * 90, "y" * 250, "z" * 400, "é✓ text", "line\nbreak"]

    def value() -> object:
        kind = rng.randrange(9)
        if kind == 0:
            return None
        if kind == 1:
            return rng.choice([True, False])
        if kind == 2:
            return rng.randrange(-3, 9999)
        if kind == 3:
            return rng.random()
        if kind == 4:
            return rng.choice(words)
        if kind == 5:
            return [rng.choice(words) for _ in range(rng.randrange(0, 30))]
        if kind == 6:
            return [rng.choice([1, "a", None, 2.5, "bb"]) for _ in range(rng.randrange(0, 6))]
        if kind == 7:
            return {rng.choice(words) or "k": 1 for _ in range(rng.randrange(0, 30))}
        return rng.choice([b"bytes", Path("/p"), (1, 2), object()])

    arguments = {rng.choice(NAMES): value() for _ in range(rng.randrange(0, 12))}
    assert JsonArgumentSummarizer().summarize(arguments) == _oracle.summarize_args(arguments)
