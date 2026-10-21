"""Addresses: ``norm parent depth child_addr`` and the name vocabulary."""

from __future__ import annotations

import pytest

from hirearchy.kernel import ROOT, child_addr, depth, norm, parent


@pytest.mark.parametrize("raw", [None, "", " ", "\t", "root", " root ", "/", "//", "/root/", "root/", "\nroot\n"])
def test_every_spelling_of_the_root_is_root(raw: str | None) -> None:
    assert norm(raw) == ROOT


@pytest.mark.parametrize(("raw", "expected"), [
    ("ceo", "ceo"),
    (" ceo ", "ceo"),
    ("/ceo/", "ceo"),
    ("ceo/eng", "ceo/eng"),
    (" /ceo/eng/ ", "ceo/eng"),
    ("ceo\n", "ceo"),  # a trailing newline is blanks, not part of the name
    ("ceo/eng\n", "ceo/eng"),
    ("Ceo", "Ceo"),  # no case folding here
    ("ceo//eng", "ceo//eng"),  # inner slashes are left to the existence check
])
def test_norm_strips_blanks_and_outer_slashes(raw: str, expected: str) -> None:
    assert norm(raw) == expected


def test_norm_is_idempotent() -> None:
    for raw in (None, "", "root", " /a/b/ ", "ceo\n", "x"):
        assert norm(norm(raw)) == norm(raw)


@pytest.mark.parametrize(("addr", "expected"), [
    ("root", None), (None, None), ("", None), ("/", None),
    ("ceo", ROOT), (" ceo ", ROOT), ("ceo\n", ROOT),
    ("ceo/eng", "ceo"), ("/ceo/eng/", "ceo"), ("ceo/eng/qa", "ceo/eng"),
])
def test_parent(addr: str | None, expected: str | None) -> None:
    assert parent(addr) == expected


@pytest.mark.parametrize(("addr", "expected"), [
    ("root", 0), (None, 0), ("", 0), (" root ", 0),
    ("ceo", 1), ("ceo\n", 1), ("ceo/eng", 2), ("/ceo/eng/", 2), ("a/b/c", 3), ("a/b/c/d", 4),
])
def test_depth(addr: str | None, expected: int) -> None:
    assert depth(addr) == expected


@pytest.mark.parametrize(("base", "name", "expected"), [
    ("root", "ceo", "ceo"), ("", "ceo", "ceo"), (None, "ceo", "ceo"), (" /root/ ", "ceo", "ceo"),
    ("ceo", "eng", "ceo/eng"), (" /ceo/ ", "eng", "ceo/eng"), ("ceo/eng", "qa", "ceo/eng/qa"),
    ("ceo", "eng\n", "ceo/eng\n"),  # the child name is not normalised: callers validate it with NAME_RE
])
def test_child_addr(base: str | None, name: str, expected: str) -> None:
    assert child_addr(base, name) == expected


def test_parent_and_child_addr_are_inverse() -> None:
    for addr in ("ceo", "ceo/eng", "a/b/c"):
        up = parent(addr)
        assert up is not None
        assert child_addr(up, addr.rsplit("/", 1)[-1]) == addr
        assert depth(addr) == depth(up) + 1
