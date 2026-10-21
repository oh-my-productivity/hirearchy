"""Contract of ``ArgumentSummarizer`` (a pure function of the arguments: one implementation): which argument becomes what, and never a body.

Every rule of the table is today's ``summarize_args``: ids, addresses, titles (clipped), statuses, budgets, paths, service names, verdicts,
booleans and numbers as they are; any other text only as its length; dicts as their keys; other lists as their length."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from hirearchy.kernel import JsonObject
from hirearchy.telemetry import ArgumentSummarizer
from hirearchy.telemetry.testing import IMPLEMENTATIONS



@pytest.fixture(params=IMPLEMENTATIONS[ArgumentSummarizer], ids=lambda factory: factory.__name__)
def summarize(request: pytest.FixtureRequest, tmp_path: Path) -> Callable[[dict[str, object]], JsonObject]:
    made = cast(Callable[[Path], ArgumentSummarizer], request.param)(tmp_path)
    assert isinstance(made, ArgumentSummarizer)
    return made.summarize


# name -> the longest text kept as it is (the clip of ``_KEEP_STR``)
KEEP_STR = {
    "to": 200, "task_id": 200, "status": 40, "name": 80, "owner": 200, "service": 80, "verdict": 20, "report": 200,
    "agent": 200, "path": 300, "reply_to": 200, "revises": 200, "view": 40, "target": 200, "since": 80, "until": 80,
    "by": 40, "model": 80, "workspace": 300, "kind": 40, "plan_id": 80, "role": 80, "title": 80,
}
KEEP_LIST = ("inputs", "artifacts", "tools")


@pytest.mark.parametrize("name,limit", sorted(KEEP_STR.items()))
def test_a_short_identifier_is_kept_and_a_long_one_is_clipped(summarize: Callable[[dict[str, object]], JsonObject], name: str, limit: int) -> None:
    assert summarize({name: "x" * limit}) == {name: "x" * limit}
    cut = summarize({name: "x" * (limit + 50)})[name]
    assert isinstance(cut, str) and len(cut) == limit and cut.endswith("…")


@pytest.mark.parametrize("name", ["body", "goal", "acceptance", "text", "summary", "playbook", "reason", "description"])
def test_any_other_text_is_only_its_length(summarize: Callable[[dict[str, object]], JsonObject], name: str) -> None:
    assert summarize({name: "secret " * 10}) == {f"{name}_chars": 70}


def test_numbers_and_booleans_are_kept_as_they_are(summarize: Callable[[dict[str, object]], JsonObject]) -> None:
    assert summarize({"budget": 5, "ratio": 0.5, "force": False, "wake": True, "n": 0}) == {"budget": 5, "ratio": 0.5, "force": False, "wake": True, "n": 0}


def test_an_argument_left_at_its_default_says_nothing(summarize: Callable[[dict[str, object]], JsonObject]) -> None:
    assert summarize({"to": None, "budget": None}) == {}
    assert summarize({}) == {}


def test_a_dict_is_its_keys_at_most_twenty_clipped_to_sixty(summarize: Callable[[dict[str, object]], JsonObject]) -> None:
    got = summarize({"inputs_dict": {f"k{i}": "v" for i in range(30)}, "d": {"k" * 100: 1}})
    keys = got["inputs_dict_keys"]
    assert keys == [f"k{i}" for i in range(20)] and got["d_keys"] == ["k" * 59 + "…"]


@pytest.mark.parametrize("name", KEEP_LIST)
def test_a_list_of_paths_or_names_is_kept_clipped_to_twenty_items(summarize: Callable[[dict[str, object]], JsonObject], name: str) -> None:
    assert summarize({name: ["a", "b"]}) == {name: ["a", "b"]}
    got = summarize({name: [f"p{i}" for i in range(25)]})
    assert got[name] == [f"p{i}" for i in range(20)] + ["…"]
    long = summarize({name: ["z" * 500]})[name]
    assert isinstance(long, list) and len(long[0]) == 200


def test_a_kept_list_that_holds_other_things_is_only_counted(summarize: Callable[[dict[str, object]], JsonObject]) -> None:
    assert summarize({"inputs": ["a", 1]}) == {"inputs_n": 2, "inputs_chars": 1}


def test_any_other_list_is_its_length_and_the_characters_of_its_strings(summarize: Callable[[dict[str, object]], JsonObject]) -> None:
    assert summarize({"acceptance": ["abc", "de"], "tags": (1, 2, 3)}) == {"acceptance_n": 2, "acceptance_chars": 5, "tags_n": 3}
    assert summarize({"acceptance": []}) == {"acceptance_n": 0}


def test_anything_else_is_only_its_type(summarize: Callable[[dict[str, object]], JsonObject]) -> None:
    assert summarize({"blob": b"bytes", "when": Path("/x")}) == {"blob_type": "bytes", "when_type": "PosixPath"}


def test_no_value_of_an_unlisted_argument_ever_appears(summarize: Callable[[dict[str, object]], JsonObject]) -> None:
    got = str(summarize({"body": "TOP-SECRET", "goal": "TOP-SECRET", "acceptance": ["TOP-SECRET"], "x": {"TOP-SECRET": "TOP-SECRET"}}))
    assert got.count("TOP-SECRET") == 1  # only the key of the dict
