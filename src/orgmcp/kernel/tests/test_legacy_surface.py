"""What the legacy modules keep exposing now that the vocabulary lives in the kernel.

``orgmcp.core`` and ``orgmcp.health`` are reached by name (``_legacy.legacy``): the kernel's tests do not import upward."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import orgmcp.kernel as kernel
from orgmcp.kernel.tests._legacy import legacy

MOVED_FROM_CORE = [
    "OrgError", "Message", "split_frontmatter", "join_frontmatter", "word_count", "latest_results",
    "BOXES", "RUNTIME_NAMES", "RESERVED", "MESSAGE_TYPES", "RESULT_STATUSES", "RENDER_BODY_CHARS",
]


@pytest.mark.parametrize("name", ["ROOT", "RUNTIME", "NAME_RE"])
def test_core_constants_that_were_always_shared_stay_so(name: str) -> None:
    assert getattr(legacy("core"), name) is getattr(kernel, name)  # interned string / cached pattern: true before and after the move


@pytest.mark.xfail(strict=True, reason="red: K1")
@pytest.mark.parametrize("name", MOVED_FROM_CORE)
def test_core_exposes_the_kernel_objects_themselves(name: str) -> None:
    assert getattr(legacy("core"), name) is getattr(kernel, name)


@pytest.mark.xfail(strict=True, reason="red: K1")
def test_core_private_helpers_are_the_kernel_functions() -> None:
    core = legacy("core")
    assert core._inside is kernel.inside and core._visible is kernel.visible


@pytest.mark.xfail(strict=True, reason="red: K1")
@pytest.mark.parametrize(("old", "new"), [
    ("_aware", "aware"), ("_parse_time", "parse_time"), ("_stamp", "stamp_of"), ("_msg_time", "msg_time"), ("_duration", "fmt_duration"),
])
def test_health_private_helpers_are_the_kernel_functions(old: str, new: str) -> None:
    assert getattr(legacy("health"), old) is getattr(kernel, new)


@pytest.mark.xfail(strict=True, reason="red: K1")
def test_the_patch_points_stay_in_core() -> None:
    core = legacy("core")
    assert core.utcnow.__module__ == "orgmcp.core" and core.atomic_write.__module__ == "orgmcp.core"
    assert "load" in vars(kernel.Message) and kernel.Message.load.__func__.__module__ == "orgmcp.core"  # type: ignore[attr-defined]


def test_org_address_helpers_agree_with_the_kernel(org: Any) -> None:
    for raw in (None, "", "root", " /ceo/ ", "ceo/eng", "ceo\n"):
        assert type(org).norm(raw) == org.norm(raw) == kernel.norm(raw)
        assert type(org).parent(raw) == org.parent(raw) == kernel.parent(raw)
        assert type(org).depth(raw) == org.depth(raw) == kernel.depth(raw)
    assert org.child_addr("ceo", "eng") == kernel.child_addr("ceo", "eng") and org.child_addr("root", "ceo") == "ceo"


@pytest.mark.xfail(strict=True, reason="red: K1")
def test_loading_a_message_gives_a_kernel_message(org: Any) -> None:
    msg = org.send("root", "ceo", "hello")
    loaded = legacy("core").Message.load(org.dir("ceo") / "inbox" / f"{msg.id}.md")
    assert type(loaded) is kernel.Message and loaded == msg and loaded.path is not None


def test_a_message_file_is_parsed_once_however_often_it_is_read(org: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """The parse cache keeps its hit rate: N files read R times cost N parses, not N * R."""
    core = legacy("core")
    sent = [org.send("root", "ceo", f"note {i}") for i in range(40)]
    paths: list[Path] = [org.dir("ceo") / "inbox" / f"{m.id}.md" for m in sent]
    core._PARSED.clear()
    parses: list[int] = []
    real = core.split_frontmatter

    def counting(text: str) -> Any:
        parses.append(1)
        return real(text)

    monkeypatch.setattr(core, "split_frontmatter", counting)
    for _ in range(5):
        for p in paths:
            core.Message.load(p)
    assert len(parses) == 40
    for _ in range(3):
        assert len(org.messages("ceo", "inbox")) == 40
    assert len(parses) == 40
    paths[0].write_text(paths[0].read_text(encoding="utf-8") + "\nmore", encoding="utf-8")  # one file changes: one reparse
    org.messages("ceo", "inbox")
    assert len(parses) == 41
