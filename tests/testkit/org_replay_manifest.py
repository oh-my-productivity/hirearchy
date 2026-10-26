"""What each corpus of the exit-check replays kept, as plain data (0b design 19.1): ``MANIFESTS[corpus]`` is read by ``testkit.org_replay.materialize``.

Every path is relative to the entry's ``evidence`` directory. A listed file that is not there fails the test that materializes the corpus; a kept
folder that is not listed fails ``tests/meta/test_org_replay_kit.py``, so nothing is dropped quietly.

The keys of an entry:

* ``evidence``: the evidence directory (``testkit.e4_replay.EV``/``EV3`` for E4 and E3, ``studies/<name>/evidence`` for E, E2 and A5);
* ``service``, ``owner``: the service's name and the agent that offers it (``None`` for A5, which has no service);
* ``boxes``: ``(folder or glob, address, box)``. The files of a folder, or the files a glob matches, are messages kept in that box of that agent;
* ``received_from_sent``: the corpus kept sent boxes only (E, E2, A5); the recipient's copy of each message goes to its ``read/``;
* ``contracts``, ``playbooks``: ``(file, version)`` for a version that is in ``history/``, ``(file, None)`` for the current one;
* ``run_logs``: ``(folder, address)``: the names of the run logs of that agent;
* ``deliverables``: for each delivered file, the file, the UTC time of its last write and the line of ``deliverables-log.txt`` that shows it;
* ``team_files``: the ``memos/versions/INDEX.txt`` whose newest listed version of each path is written at that path of the organization;
* ``charters``: ``{address: file}``; an address that the messages name and that is not here gets a minimal charter;
* ``org_md``: the kept ORG.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import REPO
from .e4_replay import EV, EV3
from .e5_replay import EV5
from .e6_replay import EV6

STUDIES = REPO / "studies"
EV_E = STUDIES / "E-service-reflection" / "evidence"
EV_E2 = STUDIES / "E2-service-reflection-regression" / "evidence"
EV_A5 = STUDIES / "A5-research-final3" / "evidence"

# The folders of E3 and E4 name an agent by a prefix (``lead-reviewer-read``): ``lead-reviewer`` is the address ``lead/reviewer``.
PREFIXES = {
    "": "root",
    "lead": "lead",
    "lead-reviewer": "lead/reviewer",
    "lead-writer": "lead/writer",
    "lead-checker": "lead/checker",
    "lead-reader": "lead/reader",
}

Box = tuple[str, str, str]
ENTRY_KEYS = (
    "evidence", "service", "owner", "boxes", "received_from_sent", "contracts", "playbooks", "run_logs", "deliverables", "team_files",
    "charters", "org_md",
)


def prefixed(*pairs: tuple[str, str]) -> tuple[Box, ...]:
    """``("lead-reviewer", "read")`` is the folder ``msgs/lead-reviewer-read``, which holds the ``read`` box of ``lead/reviewer``; the prefix ``""`` is
    root (``msgs/read``)."""
    return tuple((f"msgs/{prefix}-{box}" if prefix else f"msgs/{box}", PREFIXES[prefix], box) for prefix, box in pairs)


def versions(path: str, last: int, current: str) -> tuple[tuple[str, int | None], ...]:
    """``path`` with ``{k}`` for ``k`` in ``1..last-1``, then the current file ``current``."""
    return (*((path.format(k=k), k) for k in range(1, last)), (current, None))


def delivered(file: str, mtime: str, line: int, call: int) -> dict[str, Any]:
    """A delivered file, its last write (the start of the logged command that wrote it, UTC) and the line of the log that shows it."""
    return {"file": file, "mtime": mtime, "log": "deliverables-log.txt", "line": line, "call": call}


E4_COMMON = {
    "owner": "lead",
    "received_from_sent": False,
    "team_files": "memos/versions/INDEX.txt",
    "org_md": "org-files/ORG.md",
}
E4_REVIEWER_TEAM = {"lead": "org-files/lead-AGENT.md", "lead/reviewer": "org-files/lead-reviewer-AGENT.md", "lead/writer": "org-files/lead-writer-AGENT.md"}
E4_REVIEWER_BOXES = prefixed(
    ("", "read"), ("", "sent"), ("lead", "inbox"), ("lead", "read"), ("lead", "sent"), ("lead-reviewer", "read"), ("lead-reviewer", "sent"),
    ("lead-writer", "read"), ("lead-writer", "sent"),
)
E4_REVIEWER_LOGS = (("run-logs/lead", "lead"), ("run-logs/lead-reviewer", "lead/reviewer"), ("run-logs/lead-writer", "lead/writer"))

E5_COMMON = {**E4_COMMON, "service": "weekly-meeting-memo", "contracts": versions("service/history--SERVICE.v{k}.md", 2, "service/current-SERVICE.md"),
             "playbooks": versions("playbook/history--PLAYBOOK.v{k}.md", 2, "playbook/current-PLAYBOOK.md"), "run_logs": E4_REVIEWER_LOGS,
             "charters": E4_REVIEWER_TEAM}
# E5 kept no `lead-inbox` in s2 and s3, and root's and lead's `inbox` in s1 only.
E5_BOXES = prefixed(
    ("", "read"), ("", "sent"), ("lead", "read"), ("lead", "sent"), ("lead-reviewer", "read"), ("lead-reviewer", "sent"), ("lead-writer", "read"),
    ("lead-writer", "sent"),
)

# E6 keeps E5's layout (service `weekly-memo`); the non-empty message folders are the eight of `E5_BOXES` in every stream.
E6_COMMON = {**E5_COMMON, "service": "weekly-memo"}

MANIFESTS: dict[str, dict[str, Any]] = {
    "E": {
        "evidence": EV_E,
        "service": "weekly-memo",
        "owner": "lead",
        "boxes": (
            ("msgs/root-sent", "root", "sent"), ("msgs/lead-sent", "lead", "sent"),
            ("msgs/writer-sent", "lead/writer", "sent"), ("msgs/reviewer-sent", "lead/reviewer", "sent"),
        ),
        "received_from_sent": True,
        "contracts": versions("service/SERVICE.v{k}.md", 3, "service/SERVICE.v3-current.md"),
        "playbooks": versions("playbook/PLAYBOOK.v{k}.md", 3, "playbook/PLAYBOOK.v3-current.md"),
        "run_logs": (),
        "deliverables": (),
        "team_files": None,
        "charters": {"lead": "org-files/lead-AGENT.md", "lead/reviewer": "org-files/reviewer-AGENT-final.md"},
        "org_md": "org-files/ORG.md",
    },
    "E2": {
        "evidence": EV_E2,
        "service": "meeting-memo",
        "owner": "lead",
        "boxes": (
            ("msgs/root-sent", "root", "sent"), ("msgs/lead-sent", "lead", "sent"),
            ("msgs/writer-sent", "lead/writer", "sent"), ("msgs/reviewer-sent", "lead/reviewer", "sent"),
        ),
        "received_from_sent": True,
        "contracts": versions("service/SERVICE.v{k}.md", 3, "service/SERVICE.v3-current.md"),
        "playbooks": versions("playbook/PLAYBOOK.v{k}.md", 3, "playbook/PLAYBOOK.v3-current.md"),
        "run_logs": (),
        "deliverables": (),
        "team_files": None,
        "charters": {"lead/reviewer": "org-files/reviewer-AGENT-final.md"},
        "org_md": "org-files/ORG.md",
    },
    "A5": {
        "evidence": EV_A5,
        "service": None,
        "owner": None,
        "boxes": (("msgs/sent__*.md", "root", "sent"), ("msgs/lead_sent__*.md", "lead", "sent")),
        "received_from_sent": True,
        "contracts": (),
        "playbooks": (),
        "run_logs": (),
        "deliverables": (),
        "team_files": None,
        "charters": {
            "lead": "charters/lead.md", "lead/researcher": "charters/lead-researcher.md", "lead/writer": "charters/lead-writer.md",
            "lead/factcheck": "charters/lead-factcheck.md",
        },
        "org_md": "ORG.md",
    },
    "E3": {
        "evidence": EV3,
        "service": "weekly-meeting-memo",
        "owner": "lead",
        "boxes": prefixed(
            ("", "inbox"), ("", "read"), ("", "sent"), ("lead", "inbox"), ("lead", "read"), ("lead", "sent"),
            ("lead-reviewer", "read"), ("lead-reviewer", "sent"), ("lead-writer", "read"), ("lead-writer", "sent"),
        ),
        "received_from_sent": False,
        "contracts": versions("service/SERVICE.v{k}.md", 3, "service/SERVICE.current.md"),
        "playbooks": (("playbook/PLAYBOOK.current-v1.md", None),),
        "run_logs": (("run-logs/lead", "lead"), ("run-logs/lead-reviewer", "lead/reviewer"), ("run-logs/lead-writer", "lead/writer")),
        "deliverables": (),
        "team_files": None,
        "charters": {
            "lead": "org-files/AGENT-lead.md", "lead/reviewer": "org-files/AGENT-lead-reviewer.md", "lead/writer": "org-files/AGENT-lead-writer.md",
        },
        "org_md": "org-files/ORG.md",
    },
    "E4-s1r": {
        **E4_COMMON,
        "evidence": EV / "s1r",
        "service": "weekly-memo",
        "boxes": prefixed(
            ("", "read"), ("", "sent"), ("lead", "inbox"), ("lead", "read"), ("lead", "sent"), ("lead-checker", "read"), ("lead-checker", "sent"),
            ("lead-reader", "read"), ("lead-reader", "sent"), ("lead-writer", "read"), ("lead-writer", "sent"),
        ),
        "contracts": versions("service/history--SERVICE.v{k}.md", 5, "service/current-SERVICE.md"),
        "playbooks": versions("playbook/history--PLAYBOOK.v{k}.md", 2, "playbook/current-PLAYBOOK.md"),
        "run_logs": (
            ("run-logs/lead", "lead"), ("run-logs/lead-checker", "lead/checker"), ("run-logs/lead-reader", "lead/reader"),
            ("run-logs/lead-writer", "lead/writer"),
        ),
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-22T19:12:45.031Z", 16, 31),
            delivered("memos/memo-2026-10-12.md", "2026-10-22T19:25:33.820Z", 48, 42),
            delivered("memos/memo-2026-10-19.md", "2026-10-22T19:41:21.761Z", 82, 52),
        ),
        "charters": {
            "lead": "org-files/lead-AGENT.md", "lead/checker": "org-files/lead-checker-AGENT.md", "lead/reader": "org-files/lead-reader-AGENT.md",
            "lead/writer": "org-files/lead-writer-AGENT.md",
        },
    },
    "E4-s2r": {
        **E4_COMMON,
        "evidence": EV / "s2r",
        "service": "weekly-meeting-memo",
        "boxes": E4_REVIEWER_BOXES,
        "contracts": versions("service/history--SERVICE.v{k}.md", 3, "service/current-SERVICE.md"),
        "playbooks": versions("playbook/history--PLAYBOOK.v{k}.md", 2, "playbook/current-PLAYBOOK.md"),
        "run_logs": E4_REVIEWER_LOGS,
        "deliverables": (delivered("memos/2026-10-05-memo.md", "2026-10-22T21:29:46.486Z", 13, 38),),
        "charters": E4_REVIEWER_TEAM,
    },
    "E4-s3": {
        **E4_COMMON,
        "evidence": EV / "s3",
        "service": "weekly-memo",
        "boxes": prefixed(
            ("", "inbox"), ("", "read"), ("", "sent"), ("lead", "inbox"), ("lead", "read"), ("lead", "sent"), ("lead-reviewer", "read"),
            ("lead-reviewer", "sent"), ("lead-writer", "read"), ("lead-writer", "sent"),
        ),
        "contracts": versions("service/history--SERVICE.v{k}.md", 2, "service/current-SERVICE.md"),
        "playbooks": versions("playbook/history--PLAYBOOK.v{k}.md", 2, "playbook/current-PLAYBOOK.md"),
        "run_logs": E4_REVIEWER_LOGS,
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-22T22:03:58.863Z", 17, 54),
            delivered("memos/memo-2026-10-12.md", "2026-10-22T22:15:20.879Z", 28, 72),
            delivered("memos/memo-2026-10-19.md", "2026-10-22T22:33:02.155Z", 39, 87),
        ),
        "charters": E4_REVIEWER_TEAM,
    },
    "E5-s1": {
        **E5_COMMON,
        "evidence": EV5 / "s1",
        "boxes": (*prefixed(("", "inbox"), ("lead", "inbox")), *E5_BOXES),
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-24T03:12:35.854Z", 3, 23),
            delivered("memos/memo-2026-10-12.md", "2026-10-24T03:22:12.233Z", 12, 42),
            delivered("memos/memo-2026-10-19.md", "2026-10-24T03:28:11.906Z", 27, 58),
        ),
    },
    "E5-s2": {
        **E5_COMMON,
        "evidence": EV5 / "s2",
        "boxes": E5_BOXES,
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-24T03:45:21.122Z", 3, 27),
            delivered("memos/memo-2026-10-12.md", "2026-10-24T03:57:34.246Z", 12, 50),
        ),
    },
    "E5-s3": {
        **E5_COMMON,
        "evidence": EV5 / "s3",
        "boxes": E5_BOXES,
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-24T04:18:31.904Z", 3, 39),
            delivered("memos/memo-2026-10-12.md", "2026-10-24T04:33:46.819Z", 14, 65),
        ),
    },
    "E6-s1": {
        **E6_COMMON,
        "evidence": EV6 / "s1",
        "boxes": E5_BOXES,
        # memo 1 was copied twice (call #26, then #45 after the human rework): the pin is the last write
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-24T15:59:09.266Z", 12, 45),
            delivered("memos/memo-2026-10-12.md", "2026-10-24T16:09:25.486Z", 24, 61),
            delivered("memos/memo-2026-10-19.md", "2026-10-24T16:20:53.664Z", 35, 73),
        ),
    },
    "E6-s2": {
        **E6_COMMON,
        "evidence": EV6 / "s2",
        "boxes": E5_BOXES,
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-24T16:45:22.100Z", 3, 31),
            delivered("memos/memo-2026-10-12.md", "2026-10-24T16:59:33.715Z", 13, 53),
        ),
    },
    "E6-s3": {
        **E6_COMMON,
        "evidence": EV6 / "s3",
        "boxes": E5_BOXES,
        # memo 1 was copied twice (call #25, then #44 after the human rework): the pin is the last write
        "deliverables": (
            delivered("memos/memo-2026-10-05.md", "2026-10-24T17:29:19.322Z", 12, 44),
            delivered("memos/memo-2026-10-12.md", "2026-10-24T17:33:53.245Z", 23, 52),
        ),
    },
}


# The variants of ``materialize(corpus, root, variant)``: files the kit ADDS to a corpus so that a replay on real files shows an alarm firing.
# They are constructed, never observations; the tests that use them say so in their names.
VARIANTS: dict[str, dict[str, Any]] = {
    "r2-links-r1": {
        "corpus": "E3",
        "what": "constructed variant (design 19.3 E3-7): one more root note, a copy of ...-root-8ca0 with the id 20261021T154600000000-root-0b01, the time "
                "15:46:00, the criterion R1 and its title: a human-tier link on R2 saying it is the same as R1; written to root's sent/ and lead's read/",
    },
    "r3-overspend-<N>": {
        "corpus": "E3",
        "what": "constructed variant, not an observation (design 19.3 E3-9): N empty run logs of lead named 20261021T1543000000<01..N>.log, inside case "
                "...-root-ab46's window; no study corpus fires the cost alarm under D-E5-6's rule, so this is the only replay in which it fires",
    },
}


def evidence_dir(corpus: str) -> Path:
    """The evidence directory of ``corpus`` (a corpus that is not in ``MANIFESTS`` is a mistake of the test)."""
    return Path(str(MANIFESTS[corpus]["evidence"]))
