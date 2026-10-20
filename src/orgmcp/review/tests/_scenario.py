"""One organization with managers, a team, a paused agent and a manager that cannot be written to, built on disk by the legacy ``Org`` with a clock that
only moves when told.

The files in ``expected/`` were captured from the module ``review.py`` (the code before the package existed) on exactly this organization, so the
tests that compare them prove the move changed no text and no byte of the ledger. ``orgmcp.core`` is reached by name: a feature's tests do not import
the facade statically.
"""

from __future__ import annotations

import importlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from testkit.clocks import clock_ports

from orgmcp.kernel import TokenSource
from orgmcp.kernel.testing import CounterTokens

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ROOT = "root"
NOW = T0 + timedelta(hours=5)  # the moment of the reviews: everybody has been idle for hours


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


class ScenarioClock:
    """The clock of the runtimes (``Clock.now``): fixed until told to move, then 1 ms per call so that message ids stay ordered."""

    def __init__(self) -> None:
        self.t = T0

    def __call__(self) -> datetime:
        self.t += timedelta(milliseconds=1)
        return self.t

    def at(self, seconds: float) -> None:
        self.t = at(seconds)


def install(process_overrides: Any) -> ScenarioClock:
    """Give every runtime opened from now on (until the test ends) the clock of the scenario and ids that count (the ``process_overrides`` fixture);
    the returned clock is the one in force."""
    clock = ScenarioClock()
    process_overrides({**clock_ports(clock), TokenSource: CounterTokens(start=1)})
    return clock


def build(tmp_path: Path, clock: ScenarioClock) -> Any:
    """The organization:

    * ``ceo`` (manager, 20 runs): ``ceo/eng`` and ``ceo/qa`` (idle), ``ceo/cto`` (manager, 5 runs) with ``ceo/cto/dev`` (paused: a problem of a team);
    * ``ops`` (manager, 3 runs, one of them reserved for a delegation) with ``ops/dev``: its news cannot be told, root's note lists it;
    * everybody has read their mail and been quiet for hours (``idle_after_seconds`` is tiny).
    """
    core: ModuleType = importlib.import_module("orgmcp.core")
    org = core.Org.init(tmp_path / "org", "Test mission", {"health": {"idle_after_seconds": 3600, "stranded_after_seconds": 10**9}})
    clock.at(0)
    org.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=4)
    org.hire("ceo", "eng", "Engineer", "Build things.")
    org.hire("ceo", "qa", "Tester", "Break things.")
    org.hire("ceo", "cto", "CTO", "Lead tech.", can_hire=True, max_children=2)
    org.hire("ceo/cto", "dev", "Developer", "Code.")
    org.hire(ROOT, "ops", "Operations", "Keep it running.", can_hire=True, max_children=2)
    org.hire("ops", "dev", "Developer", "Fix things.")
    clock.at(10)
    org.send(ROOT, "ceo", "budget", budget=20)
    org.delegate("ceo", "ceo/cto", "Tech", "Lead.", "led", budget=5)
    org.delegate(ROOT, "ops", "Keep up", "Keep it up.", "up", budget=3)
    org.delegate("ops", "ops/dev", "Fix", "Fix it.", "fixed", budget=2)
    for addr in ("ceo", "ceo/eng", "ceo/qa", "ceo/cto", "ceo/cto/dev", "ops", "ops/dev"):
        org.begin_run(addr)
        org.end_run(addr, ok=True)
    org.pause("ceo/cto/dev", "failures")
    return org


def notes_text(org: Any) -> str:
    """The review notes the runtime sent to each address, in the order of the addresses."""
    out = []
    for addr in ("ceo", "ceo/cto", "ops", ROOT):
        for m in org.received(addr):
            if m.sender == "runtime" and m.title.startswith("health review"):
                out.append(f"=== {addr} | wake={m.wake} | {m.title}\n{m.body}\n")
    return "\n".join(out)


def ledger_text(org: Any) -> str:
    text: str = (org.root / ".runtime" / "reviews.json").read_text(encoding="utf-8")
    return text


def observed(org: Any, review: Any) -> dict[str, str]:
    """Everything a review says: the dry run, the real one, the notes it sent and the ledger it kept (as the files would hold them)."""
    dry = review(org, NOW, dry_run=True)
    first = review(org, NOW)
    second = review(org, NOW + timedelta(hours=1))
    return {
        "dry_run.txt": dry.render(dry_run=True) + "\n",
        "first.txt": first.render() + "\n",
        "second.txt": second.render() + "\n",
        "notes.txt": notes_text(org),
        "ledger.json": ledger_text(org),
        "first_summary.json": json.dumps({"runs": first.runs, "flagged": first.flagged, "notified": first.notified, "skipped": first.skipped}, indent=2) + "\n",
    }
