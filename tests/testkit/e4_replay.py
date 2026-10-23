"""The kit of the deterministic replays of E4's and E3's recorded sessions (plan commits 13-14; design 10): it reads the raw evidence and drives a real
organization (real git, no scheduler, no LLM, no network) with the calls the recorded assistant and lead made.

* ``evidence(path)`` reads a file of the evidence (``EV`` for E4, ``EV3`` for E3) and splits its frontmatter;
* ``tool_call(stream_dir, n)`` reads the arguments of call ``#n`` in either recorded format (E4's ``contract-loop.txt``, E3's
  ``assistant-tool-calls.txt``);
* ``lena_line(stream_dir, turn)`` is what the user said in that turn;
* ``ReplayIds`` maps the literal message ids of the evidence to the ids of the replay's own organization, which differ (DR-42);
* ``scripted_report(w, task_id, result_file, artifact_texts)`` makes the owner of a task report it the way the recorded result did.

Every lookup that finds nothing, or finds it twice, FAILS the test that asked (``pytest.fail``), never skips it: a replay that quietly did not run
proves nothing.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest

from hirearchy.kernel import ROOT, JsonObject, Message, split_frontmatter

from . import REPO

EV = REPO / "studies" / "E4-org-growth-0a1-recheck" / "evidence"
EV3 = REPO / "studies" / "E3-org-growth-0a-live" / "evidence"
LENA_MARKER = "######## LENA (prompt sent verbatim):"  # E3's turn files: the line after it is what the user said
E4_CALL = re.compile(r"^\[[^\]]+\] call #(\d+) turn \d+ ")  # E4's contract loop: this line, then `ARGS: {...}`
E3_CALL = re.compile(r"^\[[^\]]+\] CALL #(\d+) .*? args=(\{.*\})\s*$")  # E3's tool-call log: one line, the JSON after `args=`


def evidence(path: str | Path) -> tuple[JsonObject, str]:
    """``(frontmatter, body)`` of a file of the evidence: a path relative to ``EV`` or, failing that, to ``EV3`` (or an absolute one). A file that is
    not there fails the test."""
    candidates = [Path(path)] if Path(path).is_absolute() else [EV / path, EV3 / path]
    found = next((c for c in candidates if c.is_file()), None)
    if found is None:
        pytest.fail(f"no evidence file {path}: looked in {', '.join(str(c) for c in candidates)}")
    return split_frontmatter(found.read_text(encoding="utf-8"))


def tool_call(stream_dir: Path, n: int) -> dict[str, object]:
    """The ``arguments`` of tool call ``#n`` of a recorded stream, in E4's format (``contract-loop.txt``) or E3's (``assistant-tool-calls.txt``). A
    call number that is absent, or present twice, fails the test."""
    loop, one_line = stream_dir / "contract-loop.txt", stream_dir / "assistant-tool-calls.txt"
    if loop.is_file():
        lines = loop.read_text(encoding="utf-8").splitlines()
        found = [i for i, line in enumerate(lines) if (m := E4_CALL.match(line)) and int(m.group(1)) == n]
        found_args = [lines[i + 1].removeprefix("ARGS: ") for i in found if i + 1 < len(lines) and lines[i + 1].startswith("ARGS: ")]
    elif one_line.is_file():
        matches = [E3_CALL.match(line) for line in one_line.read_text(encoding="utf-8").splitlines()]
        found_args = [m.group(2) for m in matches if m and int(m.group(1)) == n]
        found = found_args
    else:
        pytest.fail(f"no tool-call record (contract-loop.txt or assistant-tool-calls.txt) in {stream_dir}")
    if len(found) == 0:
        pytest.fail(f"call #{n} is not in the tool-call record of {stream_dir}")
    if len(found) > 1 or len(found_args) != 1:
        pytest.fail(f"call #{n} is in the tool-call record of {stream_dir} more than once (twice): the evidence cannot say which it was")
    arguments = json.loads(found_args[0])["arguments"]
    assert isinstance(arguments, dict)
    return arguments


def lena_line(stream_dir: Path, turn: int) -> str:
    """What the user said in turn ``turn``: ``turn-<NN>.prompt.txt`` when it exists (E4), else the line after ``LENA_MARKER`` in ``turn-<NN>.txt``
    (E3). A turn that is not there fails the test."""
    prompt = stream_dir / f"turn-{turn:02d}.prompt.txt"
    if prompt.is_file():
        return prompt.read_text(encoding="utf-8").strip()
    recorded = stream_dir / f"turn-{turn:02d}.txt"
    if not recorded.is_file():
        pytest.fail(f"no turn {turn} in {stream_dir}")
    lines = recorded.read_text(encoding="utf-8").splitlines()
    if LENA_MARKER not in lines:
        pytest.fail(f"turn {turn} of {stream_dir} has no line of the user ({LENA_MARKER})")
    return lines[lines.index(LENA_MARKER) + 1].strip()


class ReplayIds:
    """The ids of the evidence, in the ids of the replay (DR-42). A message id of E4 (``20261022T182945409755-root-ed94``) names a message of the
    recorded organization; the replay's own organization numbers its messages differently, so each is bound to the replay's id once it exists. The
    ids of criteria and assertions (``C<k>``, ``R<k>``) are numbered the same way in both and pass through. An id that is not bound fails the test."""

    def __init__(self) -> None:
        self._bound: dict[str, str] = {}

    def bind(self, e4_id: str, replay_id: str) -> None:
        if e4_id in self._bound:
            pytest.fail(f"{e4_id} is already bound to {self._bound[e4_id]}")
        self._bound[e4_id] = replay_id

    def of(self, e4_id: str) -> str:
        if re.fullmatch(r"[CR]\d+", e4_id):
            return e4_id
        if e4_id not in self._bound:
            pytest.fail(f"{e4_id} is not bound to an id of the replay: bind it where the replay creates that message")
        return self._bound[e4_id]

    def map(self, ids: Iterable[str]) -> list[str]:
        return [self.of(x) for x in ids]


def _sections(body: str) -> dict[str, str]:
    """The ``## `` sections of a result body, by lower-cased heading."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = found.setdefault(line[3:].strip().lower(), [])
        elif current is not None:
            current.append(line)
    return {name: "\n".join(lines).strip() for name, lines in found.items()}


def scripted_report(w: object, task_id: str, result_file: str | Path, artifact_texts: Mapping[str, str]) -> Message:
    """The owner of ``task_id`` reports it the way the recorded result ``result_file`` did: through the owner's MCP ``report`` tool, with the status,
    the summary, the artifacts and the lessons parsed from that result's ``## `` sections. ``artifact_texts`` (organization path -> text, from the
    evidence's saved versions) are written in the organization first; an artifact the result lists and nothing wrote fails the test. Then the
    organization is committed as ``RunSettlement.settle`` does after a run (real git). Returns the result the client received."""
    from testkit.mcp_server_world import build_server
    from testkit.services_world import call

    org = w
    meta, body = evidence(result_file)
    sections = _sections(body)
    listed = [line.lstrip("-* ").split(" (", 1)[0] for line in sections.get("artifacts", "").splitlines() if line.strip()]
    for rel, text in artifact_texts.items():
        target = org.root / rel  # type: ignore[attr-defined]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for rel in listed:
        if not (org.root / rel).is_file():  # type: ignore[attr-defined]
            pytest.fail(f"the result {result_file} lists {rel}, and the replay wrote no text for it")
    task = next(
        (m for addr in (*org.agents(), ROOT) if (m := org.find_received(addr, task_id)) is not None), None,  # type: ignore[attr-defined]
    )
    if task is None:
        pytest.fail(f"no task {task_id} in any inbox: the replay has not sent it yet")
    owner = task.to
    org.begin_run(owner)  # type: ignore[attr-defined]
    org.start_run_log(owner)  # type: ignore[attr-defined]
    call(
        build_server(org, owner), "report", task_id=task_id, status=str(meta.get("status") or "done"), summary=sections.get("summary", ""),
        artifacts=listed, lessons=sections.get("lessons") or None,
    )
    org.end_run(owner, ok=True)  # type: ignore[attr-defined]
    org.runtime.snapshotter.commit(f"{owner}: run ok, 1 message(s) [scripted report of {task_id}]")  # type: ignore[attr-defined]
    results = [m for m in org.runtime.mailbox.received(task.sender) if m.type == "result" and m.reply_to == task_id]  # type: ignore[attr-defined]
    return max(results, key=lambda m: m.id)
