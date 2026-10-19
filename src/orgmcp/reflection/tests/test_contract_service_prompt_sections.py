"""Contract of ``ServicePromptSections``: what an owner's run prompt says about its services, text for text as ``services.py`` printed it."""

from __future__ import annotations

from pathlib import Path

import pytest

from orgmcp.kernel import RENDER_BODY_CHARS, Message
from orgmcp.reflection import ServicePromptSections
from orgmcp.reflection.testing import IMPLEMENTATIONS, ReflectionWorld, fs_world, memory_world

from . import _stories
from ._golden import expected
from ._support import SERVICE, STEPS, ask, define, deliver, implementations, populated, rate, revise

pytestmark = pytest.mark.xfail(strict=True, reason="red: C-reflection")


@pytest.fixture(params=[fs_world, memory_world], ids=lambda f: f.__name__)
def w(request: pytest.FixtureRequest, tmp_path: Path) -> ReflectionWorld:
    return populated(request.param(tmp_path))


@pytest.fixture(params=implementations(IMPLEMENTATIONS[ServicePromptSections]))
def sections(request: pytest.FixtureRequest, tmp_path: Path) -> ServicePromptSections:
    made = request.param(tmp_path)
    assert isinstance(made, ServicePromptSections)
    return made


def batch(w: ReflectionWorld, addr: str = "ceo") -> list[Message]:
    """What the agent finds in its inbox: its next batch."""
    return w.s.d.inbox(addr)


# ------------------------------------------------------------------------------ the text of every situation


@pytest.mark.parametrize("name", list(_stories.SECTIONS))
def test_the_sections_are_the_ones_services_py_printed(w: ReflectionWorld, name: str) -> None:
    story = _stories.SECTIONS[name](w)
    assert w.sections.prompt_sections("ceo", batch(w)) == expected(f"sections_{name}.txt", story)


# ------------------------------------------------------------------------------ who gets what


def test_an_agent_that_owns_no_service_gets_nothing(w: ReflectionWorld) -> None:
    define(w)
    assert w.sections.prompt_sections("ops", []) == "" == w.sections.prompt_sections("ceo/eng", [])


def test_every_section_starts_and_ends_with_a_newline(w: ReflectionWorld) -> None:
    _stories.rejection_and_rework(w)
    text = w.sections.prompt_sections("ceo", batch(w))
    assert text.startswith("\n# Your services\n") and text.endswith("\n") and "\n\n# Playbook: " in text and "\n\n# Reflect before" in text


def test_the_playbook_is_shown_only_for_a_service_with_an_open_request(w: ReflectionWorld) -> None:
    define(w, playbook=STEPS)
    assert "# Playbook:" not in w.sections.prompt_sections("ceo", [])
    ask(w)
    assert "# Playbook: weekly-brief (v1, yours to improve)\n> ## Steps" in w.sections.prompt_sections("ceo", [])


def test_a_first_request_with_no_evidence_asks_for_no_reflection(w: ReflectionWorld) -> None:
    define(w)
    ask(w)
    assert "# Reflect before you start" not in w.sections.prompt_sections("ceo", batch(w))


def test_a_rework_in_the_batch_is_not_a_new_request(w: ReflectionWorld) -> None:
    _stories.rejection_and_rework(w)
    text = w.sections.prompt_sections("ceo", batch(w))
    assert "then handle the rework." in text and "Then handle the rework following the playbook." in text and "new playbook" in text


def test_a_rejection_of_another_owners_service_is_not_ours(w: ReflectionWorld) -> None:
    define(w)
    define(w, owner="ops", name="ops-brief")
    task = w.s.commands.request("root", "ops-brief", {"topic": "x"})
    deliver(w, task, lessons="L.")
    rate(w, task, "reject", "No.")
    assert "# Reflect before you start" not in w.sections.prompt_sections("ceo", batch(w))
    assert "# Reflect before you start: ops-brief" in w.sections.prompt_sections("ops", batch(w, "ops"))


# ------------------------------------------------------------------------------ the playbook in the prompt


def test_a_playbook_over_the_limit_is_cut_and_says_where_the_rest_is(w: ReflectionWorld) -> None:
    define(w)
    w.s.d.configure("---\nmission: test\nplaybook_max_words: 5000\n---\nrules\n")
    revise(w, "## Steps\n" + "z" * (RENDER_BODY_CHARS + 100 - len("## Steps\n")), "long")
    ask(w)
    text = w.sections.prompt_sections("ceo", batch(w))
    assert text.rstrip().endswith(
        '> [... playbook cut: 100 more characters. Read the rest with read(path="ceo/services/weekly-brief/PLAYBOOK.md").]'
    )


def test_the_headings_of_a_playbook_do_not_mix_with_those_of_the_prompt(w: ReflectionWorld) -> None:
    define(w)
    revise(w, "# Title\n\n## Steps\n1. Go.\n", "headings")
    ask(w)
    assert "\n> # Title\n>\n> ## Steps\n> 1. Go.\n" in w.sections.prompt_sections("ceo", batch(w))


def test_the_longest_playbook_is_read_from_the_settings(w: ReflectionWorld) -> None:
    _stories.history_then_new_request(w)
    assert "(at most 1000 words)" in w.sections.prompt_sections("ceo", batch(w))
    w.s.d.configure("---\nmission: test\nplaybook_max_words: 250\n---\nrules\n")
    assert "(at most 250 words)" in w.sections.prompt_sections("ceo", batch(w))


def test_the_implementations_agree_that_nobody_owns_anything(sections: ServicePromptSections) -> None:
    assert sections.prompt_sections("ceo", []) == ""
