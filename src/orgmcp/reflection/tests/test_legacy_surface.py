"""The names the cases, statistics, digest and prompt sections had in ``orgmcp.services`` are exported by ``orgmcp.reflection`` (until step E3), and
``orgmcp.services`` still answers to them: ``services`` is below ``reflection`` and may not import it, so it looks the names up when they are asked for."""

from __future__ import annotations

import importlib

import pytest

import orgmcp.reflection as reflection
from orgmcp import services

MOVED = """
CLIP_LESSON CLIP_NOTE DIGEST_CASES DIGEST_CHARS MAX_VERDICTS Case Verdict Stats playbook_timeline version_at lessons_of cases summarize
stats_by_version reflection_digest case_of case_total services_text prompt_sections _case_line _verdict_chain
""".split()


def test_every_moved_name_is_exported_by_reflection() -> None:
    assert [n for n in MOVED if not hasattr(reflection, n)] == []


CONSTANTS = [n for n in MOVED if n.isupper()]


@pytest.mark.parametrize("name", CONSTANTS)
def test_services_answers_to_the_old_name_of_a_constant_with_the_same_value(name: str) -> None:
    assert getattr(services, name) == getattr(reflection, name)


@pytest.mark.xfail(strict=True, reason="red: C-reflection (services still holds its own copies until the next commit)")
@pytest.mark.parametrize("name", [n for n in MOVED if not n.isupper()])
def test_services_answers_to_the_old_name_with_the_same_object(name: str) -> None:
    assert getattr(services, name) is getattr(reflection, name)


def test_the_digest_constants_keep_their_values() -> None:
    assert (reflection.DIGEST_CASES, reflection.DIGEST_CHARS, reflection.CLIP_LESSON, reflection.CLIP_NOTE, reflection.MAX_VERDICTS) == (6, 3000, 220, 160, 4)


def test_a_name_services_never_had_is_still_an_attribute_error() -> None:
    with pytest.raises(AttributeError):
        services.no_such_name  # noqa: B018
    assert not hasattr(services, "_no_such_name")


def test_services_does_not_import_reflection_when_it_is_imported() -> None:
    source = importlib.import_module("orgmcp.services").__file__
    assert source is not None
    text = open(source, encoding="utf-8").read()
    assert "from ..reflection" not in text and "import orgmcp.reflection" not in text and "from orgmcp.reflection" not in text
