"""The process-global state that ``orgmcp.core`` and ``orgmcp.app`` keep and that tests are allowed to patch for the length of one test.

``ProcessState.capture()`` records it; ``leaks_since`` names what differs from an earlier capture; ``restore`` puts it back. The autouse fixture
``process_state_guard`` (tests/testkit/fixtures.py) uses all three after every test, so a test that leaves one of these replaced fails
*itself*, by name, instead of making an unrelated test of ``orgmcp.app`` fail later (and only sometimes, depending on what ran before it).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# core attributes that no test may leave replaced: the helpers that used to be patch points (utcnow, atomic_write, secrets: nothing reads them at call
# time any more, a test gives a runtime its fakes through ``wiring.overriding``, captured below as ``wiring.overrides``) and the aliases of the parse cache
CORE_NAMES = ("Message", "utcnow", "atomic_write", "secrets", "split_frontmatter", "_PARSED", "_PARSED_MAX")


@dataclass(frozen=True)
class ProcessState:
    """What was where at one moment: the objects themselves (compared by identity, except the plain values)."""

    values: dict[str, Any]

    @staticmethod
    def capture() -> ProcessState:
        from orgmcp import core
        from orgmcp.app import wiring
        from orgmcp.kernel import Message

        resources = wiring.process_resources()
        values: dict[str, Any] = {f"core.{name}": getattr(core, name) for name in CORE_NAMES}
        values.update({
            "kernel.Message": Message,
            "wiring._process": wiring._process,
            "wiring.overrides": wiring._overrides,
            "resources.message_parser": resources.message_parser,
            "message_parser.cache": resources.message_parser.cache,
        })
        return ProcessState(values)

    def leaks_since(self, earlier: ProcessState) -> list[str]:
        """Names of the entries whose object (or value) is not the one in ``earlier``."""
        return [name for name, value in earlier.values.items() if not _same(self.values.get(name), value)]


def _same(a: Any, b: Any) -> bool:
    return a == b if isinstance(a, (bool, int, str)) and type(a) is type(b) else a is b


def restore(earlier: ProcessState) -> None:
    """Put back the patchable entries of ``earlier`` (the aliases that cannot be patched are only reported)."""
    from orgmcp import core
    from orgmcp.app import wiring

    for name in CORE_NAMES:
        setattr(core, name, earlier.values[f"core.{name}"])
    wiring._process = earlier.values["wiring._process"]
    wiring._overrides = earlier.values["wiring.overrides"]


def verify(before: ProcessState, nodeid: str) -> None:
    """Fail ``nodeid`` if it left the state different from ``before``; the state is put back first, so nothing after it is affected."""
    import pytest

    leaked = ProcessState.capture().leaks_since(before)
    if leaked:
        restore(before)
        pytest.fail(f"{nodeid} left process-global state replaced: {', '.join(leaked)}", pytrace=False)
