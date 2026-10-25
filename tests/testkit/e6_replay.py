"""The kit of the deterministic replays of E6's recorded streams (0a.4 design 17.1): E5's kit (``testkit.e5_replay``) pointed at ``EV6`` and E6's
service, ``weekly-memo``. ``materialize(stream, cut, dest, inflight=None)`` writes the organization ``EV6/<stream>`` had at the 21-character stamp
``cut`` (inclusive), with the contract ``service/history--SERVICE.v1.md`` at ``lead/services/weekly-memo/SERVICE.md``; see ``e5_replay`` for the rest.
A missing evidence file fails the test (``pytest.fail``), never skips it."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from . import REPO, e5_replay

EV6 = REPO / "studies" / "E6-org-growth-0a3-recheck" / "evidence"
SERVICE_NAME = "weekly-memo"  # the service of every E6 stream, offered by ``lead``


def materialize(stream: str, cut: str, dest: Path, inflight: Mapping[str, Sequence[str]] | None = None) -> Path:
    """Write the organization ``EV6/<stream>`` had at ``cut`` at ``dest`` (created) and return ``dest``."""
    return e5_replay.materialize(stream, cut, dest, inflight, evidence=EV6, service=SERVICE_NAME)
