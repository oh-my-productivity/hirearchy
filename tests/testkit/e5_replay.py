"""The kit of the deterministic replays of E5's recorded streams (0a.3 design 4.7): it rebuilds, from the raw evidence, the organization a stream had at
one moment, and the product's own code reads it (no scheduler, no LLM, no network, no assistant calls).

``materialize(stream, cut, dest)`` writes an organization at ``dest`` holding what ``EV5/<stream>`` had at the 21-character stamp ``cut`` (inclusive):

* ``org-files/ORG.md`` as ``ORG.md``;
* each ``org-files/<a-b>-AGENT.md`` as ``<a>/<b>/AGENT.md`` (the evidence names an address by joining its parts with ``-``);
* ``service/history--SERVICE.v1.md`` as ``lead/services/weekly-meeting-memo/SERVICE.md`` (the contract of every E5 stream);
* every file of ``msgs/<box>`` (root's) and ``msgs/<a-b>-<box>`` (the agent ``a/b``'s) whose id starts with a stamp ``<= cut``, in that box;
* an empty ``<a>/<b>/runs/<stamp>.log`` for every file of ``run-logs/<a-b>/`` with ``stamp <= cut``: the case counts read the names of the logs only;
* with ``inflight={"lead": [<message id>, ...]}``, those messages of the agent are in its ``inflight/`` box instead of ``inbox``/``read``: the batch its
  run was handling at ``cut`` (the evidence keeps only the boxes after the run). A message that is not in the organization at ``cut`` fails the test.

``Org(dest)`` opens it as it stands: ``ORG.md`` and the agents' directories are all the product reads here (the organization's git repository,
``.runtime/`` and the settings file ``Org.init`` writes are created lazily or not needed by the readers the replays call). The kit reads the evidence only and
never writes into it. A missing evidence file fails the test (``pytest.fail``), never skips it: a replay that quietly did not run proves nothing.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from . import REPO

EV5 = REPO / "studies" / "E5-org-growth-0a2-recheck" / "evidence"
SERVICE_NAME = "weekly-meeting-memo"  # the service of every E5 stream, offered by ``lead``
BOXES = ("inbox", "read", "sent")


def _stamp(name: str) -> str:
    """The 21-character moment a message or a run log is named after (``20261024T031704521000``)."""
    return name[:21]


def _addr(parts: str) -> str:
    """An address as the evidence names it: ``lead-writer`` is ``lead/writer``."""
    return parts.replace("-", "/")


def _file(path: Path) -> Path:
    if not path.is_file():
        pytest.fail(f"no evidence file {path}")
    return path


def _dir(path: Path) -> Path:
    if not path.is_dir():
        pytest.fail(f"no evidence directory {path}")
    return path


def materialize(stream: str, cut: str, dest: Path, inflight: Mapping[str, Sequence[str]] | None = None) -> Path:
    """Write the organization ``EV5/<stream>`` had at ``cut`` at ``dest`` (created) and return ``dest``; see the module docstring."""
    source = _dir(EV5 / stream)
    if len(cut) != 21:
        pytest.fail(f"cut must be a 21-character stamp, got {cut!r}")
    dest.mkdir(parents=True, exist_ok=True)
    files = _dir(source / "org-files")
    shutil.copyfile(_file(files / "ORG.md"), dest / "ORG.md")
    for agent in sorted(files.glob("*-AGENT.md")):
        target = dest / _addr(agent.name.removesuffix("-AGENT.md")) / "AGENT.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(agent, target)
    contract = dest / "lead" / "services" / SERVICE_NAME / "SERVICE.md"
    contract.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_file(source / "service" / "history--SERVICE.v1.md"), contract)
    for box_dir in sorted(_dir(source / "msgs").iterdir()):
        who, _, box = box_dir.name.rpartition("-")
        if box_dir.name in BOXES:
            who, box = "", box_dir.name
        if box not in BOXES:
            pytest.fail(f"{box_dir} is not a mailbox of the evidence (inbox, read, sent)")
        for message in sorted(box_dir.glob("*.md")):
            if _stamp(message.name) <= cut:
                target = (dest / _addr(who) / box / message.name) if who else (dest / box / message.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(message, target)
    for logs in sorted(p for p in _dir(source / "run-logs").iterdir() if p.is_dir()):
        for log in sorted(logs.glob("*.log")):
            if _stamp(log.name) <= cut:
                target = dest / _addr(logs.name) / "runs" / log.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("", encoding="utf-8")
    for agent, ids in (inflight or {}).items():
        for msg_id in ids:
            held = [dest / agent / box / f"{msg_id}.md" for box in ("inbox", "read") if (dest / agent / box / f"{msg_id}.md").is_file()]
            if not held:
                pytest.fail(f"inflight message {msg_id} is not in the organization of {agent} at the cut {cut}")
            (dest / agent / "inflight").mkdir(exist_ok=True)
            shutil.move(held[0], dest / agent / "inflight" / held[0].name)
    return dest
