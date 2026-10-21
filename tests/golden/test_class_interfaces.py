"""Class-interface check: every class with behaviour defined in ``src/hirearchy`` must subclass a ``typing.Protocol``.

Principle (docs/refactor-principles.md, "D"): ``class FsMessageStore(MessageStore): ...``. Today almost no class does, so the
classes that do not are listed in ``interface_allowlist.txt`` (one ``module.Qualname`` per line). Each refactor step
removes entries; the end state is an EMPTY list.

* ``test_no_new_class_without_an_interface`` (active): fails only for a class that is NOT on the allow-list.
* ``test_every_class_has_an_interface`` (report): xfails while the allow-list is not empty, and passes (as a hard
  assertion) once it is empty. ``pytest -rx tests/golden/test_class_interfaces.py`` shows the count; set
  ``HIREARCHY_INTERFACE_REPORT=1`` (with ``-s``) to print every offender and every stale allow-list entry.
* Stale entries (on the list but gone, exempt or compliant now) are reported, not failed; prune them with
  ``HIREARCHY_INTERFACE_ALLOWLIST=rewrite uv run pytest tests/golden/test_class_interfaces.py`` (rewrites the list from
  the current offenders: a diff that ADDS a line is a review failure; the list may only shrink).

This is THE class-interface check (rule R6); the classifier it uses (the exemption rules: Protocols, exceptions, Textual
subclasses, pure data) lives in ``tests/architecture/class_interfaces.py`` so the architecture tests can prove on a seeded
violation that it flags a class without a Protocol. Permanent exemptions: ``tests/architecture/exempt_classes.py`` (empty).
"""

from __future__ import annotations

import dataclasses
import enum
import os
import typing
from pathlib import Path

import pytest
from architecture.class_interfaces import exemption, subclasses_a_protocol, survey as survey_package

import hirearchy

ALLOWLIST = Path(__file__).with_name("interface_allowlist.txt")
REPORT = os.environ.get("HIREARCHY_INTERFACE_REPORT", "").strip() not in ("", "0")
REWRITE = os.environ.get("HIREARCHY_INTERFACE_ALLOWLIST", "") == "rewrite"


def survey() -> tuple[dict[str, str], dict[str, int]]:
    return survey_package(hirearchy)


def allowed() -> set[str]:
    if not ALLOWLIST.is_file():
        return set()
    lines = (line.split("#", 1)[0].strip() for line in ALLOWLIST.read_text(encoding="utf-8").splitlines())
    return {line for line in lines if line}


def write_allowlist(offenders: set[str]) -> None:
    head = (
        "# Classes with behaviour that do not yet subclass a typing.Protocol (see test_class_interfaces.py).\n"
        "# One module.Qualname per line. Refactor steps REMOVE entries; the end state is an empty list.\n"
    )
    ALLOWLIST.write_text(head + "".join(f"{name}\n" for name in sorted(offenders)), encoding="utf-8")


# ----------------------------------------------------------------------------------------------------- tests


@pytest.fixture(scope="module")
def surveyed():
    offenders, counts = survey()
    if REWRITE:
        write_allowlist(set(offenders))
    return offenders, counts


def test_no_new_class_without_an_interface(surveyed):
    offenders, counts = surveyed
    listed = allowed()
    new = sorted(set(offenders) - listed)
    stale = sorted(listed - set(offenders))
    if REPORT:
        print(f"\n{len(offenders)} class(es) without a Protocol base ({len(listed)} allow-listed); exempt/compliant: {counts}")
        print("\n".join(f"  no interface: {n}" for n in sorted(offenders)))
        print("\n".join(f"  stale allow-list entry (remove it): {n}" for n in stale))
    assert not new, (
        "these classes have behaviour but subclass no typing.Protocol (add the interface, or exempt them only if they are "
        "data/exceptions/framework classes; do NOT add them to interface_allowlist.txt):\n  " + "\n  ".join(new)
    )


def test_stale_allowlist_entries_are_listed_for_pruning(surveyed):
    """Not a failure (the list may only shrink, and a rename shows up above first); a warning with the names to remove."""
    offenders, _ = surveyed
    stale = sorted(allowed() - set(offenders))
    if stale:
        import warnings

        warnings.warn(f"interface_allowlist.txt has {len(stale)} stale entr(ies) to remove: {', '.join(stale)}", stacklevel=1)


def test_every_class_has_an_interface(surveyed):
    """The end-state assertion. Reported as xfail until the allow-list is empty, then a hard check."""
    offenders, counts = surveyed
    if offenders:
        pytest.xfail(f"{len(offenders)} class(es) with behaviour still lack a Protocol base "
                     f"(allow-list: {len(allowed())}; exempt/compliant: {counts}); HIREARCHY_INTERFACE_REPORT=1 lists them")
    assert not allowed(), "all classes have interfaces: empty interface_allowlist.txt"


def test_the_exemption_rules_on_examples():
    """The classifier itself, on small classes (so a change of the rules is a visible change)."""

    class Port(typing.Protocol):
        def run(self) -> None: ...

    class Impl(Port):
        def run(self) -> None:
            return None

    @dataclasses.dataclass
    class Plain:
        x: int = 0

        def __post_init__(self) -> None: ...

        @property
        def double(self) -> int:
            return self.x * 2

    @dataclasses.dataclass
    class Smart:
        x: int = 0

        def compute(self) -> int:
            return self.x

    class Named(typing.NamedTuple):
        a: int

    class Color(enum.Enum):
        RED = 1

    class Boom(ValueError): ...

    class Service:
        def run(self) -> None: ...

    assert [exemption(c) for c in (Port, Impl, Plain, Smart, Named, Color, Boom, Service)] == [
        "protocol", None, "data", None, "data", "data", "exception", None]
    assert subclasses_a_protocol(Impl) and not subclasses_a_protocol(Service) and not subclasses_a_protocol(Port)
