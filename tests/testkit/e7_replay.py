"""The kit of the deterministic replays of E7's recorded streams (0a.5 plan item 2): E5's kit (``testkit.e5_replay``) pointed at ``EV7`` and E7's
service, ``weekly-meeting-memo``. ``materialize(stream, cut, dest, inflight=None)`` writes the organization ``EV7/<stream>`` had at the 21-character
stamp ``cut`` (inclusive), with the contract ``service/history--SERVICE.v1.md`` at ``lead/services/weekly-meeting-memo/SERVICE.md``; see ``e5_replay``
for the rest. A missing evidence file fails the test (``pytest.fail``), never skips it."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from . import REPO, e5_replay

EV7 = REPO / "studies" / "E7-org-growth-0a4-recheck" / "evidence"
SERVICE_NAME = "weekly-meeting-memo"  # the service of every E7 stream, offered by ``lead``


def materialize(stream: str, cut: str, dest: Path, inflight: Mapping[str, Sequence[str]] | None = None) -> Path:
    """Write the organization ``EV7/<stream>`` had at ``cut`` at ``dest`` (created) and return ``dest``."""
    return e5_replay.materialize(stream, cut, dest, inflight, evidence=EV7, service=SERVICE_NAME)
