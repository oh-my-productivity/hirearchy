"""The expected texts of ``expected/``: captured from the code that lived in ``services.py`` (before the package existed) on the stories of ``_stories``.

A text names the messages of its story as ``{ask0}``, ``{res0}``, ``{note0}`` (the n-th request, result or note the story made); ``expected`` puts their ids in.
"""

from __future__ import annotations

from pathlib import Path

from ._stories import Story

EXPECTED = Path(__file__).with_name("expected")


def placeholders(story: Story) -> dict[str, str]:
    """``{"ask0": id of the first request, ...}``."""
    return {
        **{f"ask{n}": m.id for n, m in enumerate(story.asks)},
        **{f"res{n}": m.id for n, m in enumerate(story.results)},
        **{f"note{n}": m.id for n, m in enumerate(story.notes)},
    }


def expected(name: str, story: Story) -> str:
    text = (EXPECTED / name).read_text(encoding="utf-8")
    for key, value in placeholders(story).items():
        text = text.replace("{" + key + "}", value)
    return text
