"""Golden (characterization) tests: byte-for-byte snapshots of everything the refactor's behaviour freeze covers.

Expected files live in ``tests/golden/expected/``; each test builds a deterministic fixture (fixed clock, counter-based
ids, tmp paths replaced by placeholders), renders some output and compares it with ``check(name, text)``.

Regenerate deliberately, review the diff in git, and commit it with the change that caused it::

    HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden            # rewrite every expected file that differs
    HIREARCHY_UPDATE_GOLDEN=1 uv run pytest tests/golden -k prompts # only some

A refactor step must leave ``expected/`` untouched: a diff there means observable behaviour changed.
Without the variable, a missing or different file fails the test and prints a unified diff.

Normalisation happens here, in the tests, never in production code:

* real clock -> ``FixedClock`` as the ``Clock`` of every runtime (``wiring.overriding``, see ``conftest.clock``); a test moves it with ``clock.tick()``;
* the random part of message ids -> a counter (``CounterTokens(per_length=True)``: one per byte length), so message ids are stable;
* the tmp paths, ``$HOME``, the venv ``bin`` dir and the project dir -> ``<ORG>``, ``<TMP>``, ``<HOME>``, ``<VENV_BIN>``, ``<PROJECT>``.
"""

from __future__ import annotations

import difflib
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

EXPECTED = Path(__file__).resolve().parent / "expected"
UPDATE = os.environ.get("HIREARCHY_UPDATE_GOLDEN", "").strip().lower() not in ("", "0", "false", "no")
START = datetime(2026, 1, 15, 9, 0, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------------------------------------ comparing


def check(name: str, actual: str) -> None:
    """Compare ``actual`` with ``expected/<name>`` byte for byte (or rewrite it when ``HIREARCHY_UPDATE_GOLDEN`` is set)."""
    path = EXPECTED / name
    data = actual.encode("utf-8")
    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
        return
    if not path.is_file():
        pytest.fail(f"no golden file {path.relative_to(EXPECTED.parent)}: create it with HIREARCHY_UPDATE_GOLDEN=1 "
                    f"uv run pytest tests/golden, then review it")
    expected = path.read_bytes()
    if expected != data:
        diff = "".join(difflib.unified_diff(
            expected.decode("utf-8", "replace").splitlines(keepends=True),
            actual.splitlines(keepends=True), "expected/" + name, "actual", n=2,
        ))
        pytest.fail(f"golden file {name} differs (behaviour changed? regenerate deliberately with "
                    f"HIREARCHY_UPDATE_GOLDEN=1):\n{diff[:6000]}")


# ------------------------------------------------------------------------------------------------ determinism


class FixedClock:
    """The one clock of a golden test. Starts at ``START``; only ``tick`` moves it."""

    def __init__(self) -> None:
        self.now = START

    def tick(self, seconds: float = 60) -> datetime:
        self.now += timedelta(seconds=seconds)
        return self.now


class Normalizer:
    """Replace the machine-specific parts of a text with placeholders (longest first)."""

    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []

    def add(self, real: object, placeholder: str) -> None:
        for form in {str(real), str(Path(str(real)).resolve())}:
            if form and form not in ("/", "."):
                self.pairs.append((form, placeholder))

    def __call__(self, text: str) -> str:
        for real, placeholder in sorted(self.pairs, key=lambda p: -len(p[0])):
            text = text.replace(real, placeholder)
        # this process's pid (events written in-process by the test carry it)
        return re.sub(rf'("pid": ){os.getpid()}\b', r'\1"<PID>"', text)


def make_normalizer(tmp_path: Path, home: Path | None) -> Normalizer:
    from hirearchy.app import wire_kiro

    n = Normalizer()
    n.add(wire_kiro.project_dir(), "<PROJECT>")
    n.add(Path(sys.executable).parent, "<VENV_BIN>")
    if home is not None:
        n.add(home, "<HOME>")
    n.add(tmp_path, "<TMP>")
    return n
