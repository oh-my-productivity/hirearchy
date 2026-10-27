"""Contract of ``ReflectionDigest``: the cases with evidence newer than the playbook, text for text as ``services.py`` printed them."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.reflection import ReflectionDigest
from hirearchy.reflection.testing import IMPLEMENTATIONS, ReflectionWorld, fs_world, memory_world

from . import _stories
from ._golden import expected
from ._support import SERVICE, STEPS, ask, define, deliver, first_playbook, implementations, populated, rate


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ReflectionDigest]))
def digest(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionDigest:
    made = request.param(tmp_path)
    assert isinstance(made, ReflectionDigest)
    return made


# ------------------------------------------------------------------------------ when there is evidence


def test_a_service_without_cases_has_no_digest(w: ReflectionWorld) -> None:
    define(w)
    assert w.digest.reflection_digest("ceo", SERVICE) is None


def test_an_open_case_is_no_evidence_yet(w: ReflectionWorld) -> None:
    define(w)
    ask(w)
    assert w.digest.reflection_digest("ceo", SERVICE) is None


def test_without_a_playbook_any_finished_case_is_evidence(w: ReflectionWorld) -> None:
    define(w)
    deliver(w, ask(w))
    assert w.digest.reflection_digest("ceo", SERVICE) is not None


def test_feedback_alone_is_evidence(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task, status="blocked")
    assert w.digest.reflection_digest("ceo", SERVICE) is None
    rate(w, task, "reject", "No.")
    digest = w.digest.reflection_digest("ceo", SERVICE)
    assert digest is not None and 'client feedback: reject R1 "No."' in digest


def test_a_playbook_newer_than_all_the_evidence_leaves_nothing_to_reflect_on(w: ReflectionWorld) -> None:
    define(w)
    deliver(w, ask(w))
    first_playbook(w)
    assert w.digest.reflection_digest("ceo", SERVICE) is None


def test_a_case_that_finishes_after_the_playbook_is_new_evidence(w: ReflectionWorld) -> None:
    define(w)
    first_playbook(w)
    task = ask(w)
    assert w.digest.reflection_digest("ceo", SERVICE) is None
    deliver(w, task)
    assert w.digest.reflection_digest("ceo", SERVICE) is not None


def test_a_service_nobody_defined_has_no_digest(w: ReflectionWorld) -> None:
    assert w.digest.reflection_digest("ceo", "nope") is None


# ------------------------------------------------------------------------------ the text


@pytest.mark.parametrize("name", list(_stories.LISTINGS))
def test_the_text_is_the_one_services_py_printed(w: ReflectionWorld, name: str) -> None:
    story = _stories.LISTINGS[name](w)
    assert w.digest.reflection_digest("ceo", SERVICE) == expected(f"digest_{name}.txt", story)


def test_the_digest_quotes_the_clients_words_without_the_header(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task)
    rate(w, task, "reject", "Missed two items.")
    digest = w.digest.reflection_digest("ceo", SERVICE)
    assert digest is not None and 'client feedback: reject R1 "Missed two items."' in digest and "reflection only" not in digest


def test_the_latest_lessons_come_first_and_the_earlier_ones_after(w: ReflectionWorld) -> None:
    define(w)
    first = ask(w)
    deliver(w, first, lessons="Ran cleanly; no changes needed.")
    again = w.s.commands.request("root", SERVICE, {"topic": "ai"}, revises=first.id, budget=4, source="human")
    deliver(w, again, lessons="Two items were missed: add a pre-read step.")
    digest = w.digest.reflection_digest("ceo", SERVICE)
    assert digest is not None
    line = next(x for x in digest.splitlines() if x.startswith("- case "))
    assert line.index('owner\'s view: "Two items were missed') < line.index('earlier: "Ran cleanly; no changes needed.')


def test_a_bare_accept_has_no_quotes_and_a_clean_case_has_no_mark(w: ReflectionWorld) -> None:
    define(w)
    task = ask(w)
    deliver(w, task, lessons="Fine.")
    rate(w, task, "accept")
    digest = w.digest.reflection_digest("ceo", SERVICE)
    assert digest is not None and "; client feedback: accept; owner's view: near miss: none recorded" in digest and "written after" not in digest
    assert "feedback 1 accept, 0 reject" in digest and "after a reject" not in digest


def test_the_statistics_are_given_per_playbook_version(w: ReflectionWorld) -> None:
    _stories.three_playbook_versions(w)
    digest = w.digest.reflection_digest("ceo", SERVICE)
    assert digest is not None and [x[:5] for x in digest.splitlines() if x.startswith("- v")] == ["- v0:", "- v1:", "- v2:"]


def test_at_most_six_cases_are_shown_and_the_text_stays_within_its_limit(w: ReflectionWorld) -> None:
    define(w)
    for i in range(8):
        deliver(w, ask(w, f"t{i}"), lessons=f"Lesson {i}.")
        w.s.d.clock.advance(1)
    digest = w.digest.reflection_digest("ceo", SERVICE)
    assert digest is not None and len([x for x in digest.splitlines() if x.startswith("- case ")]) == 6 and len(digest) <= 3000


def test_the_implementations_agree_on_an_empty_service(digest: ReflectionDigest) -> None:
    assert digest.reflection_digest("ceo", SERVICE) is None


def test_with_words_the_digest_drops_the_oldest_cases_then_clips_and_says_more_services(w: ReflectionWorld) -> None:
    define(w)
    for i in range(8):  # eight cases whose lessons are about 60 words each
        deliver(w, ask(w, f"topic {i}"), runs=1, lessons=" ".join(f"w{i}x{k}" for k in range(60)))
        w.s.d.clock.advance(1)
    full = w.digest.reflection_digest("ceo", SERVICE)
    assert full is not None and len(full.split()) > 300
    assert w.digest.reflection_digest("ceo", SERVICE, words=None) == full and w.digest.reflection_digest("ceo", SERVICE, words=10000) == full
    case_lines = [x for x in full.splitlines() if x.startswith("- case ")]
    capped = w.digest.reflection_digest("ceo", SERVICE, words=200)
    assert capped is not None and len(capped.split()) <= 200
    kept = [x for x in capped.splitlines() if x.startswith("- case ")]
    assert 1 <= len(kept) < len(case_lines) and kept == case_lines[: len(kept)]  # the oldest go first; the newest stay, newest first
    assert "By playbook version:" in capped and "(more: services)" not in capped  # dropping whole cases was enough
    tiny = w.digest.reflection_digest("ceo", SERVICE, words=40)
    assert tiny is not None and len(tiny.split()) <= 40
    (line,) = [x for x in tiny.splitlines() if x.startswith("- case ")]
    assert line.endswith("… (more: services)") and line.startswith(case_lines[0][:60]) and "By playbook version:" in tiny


def test_a_digest_with_words_is_none_when_there_is_no_evidence(w: ReflectionWorld) -> None:
    define(w)
    assert w.digest.reflection_digest("ceo", SERVICE, words=200) is None
