#!/usr/bin/env python3
"""rederive_quality.py: the study's independent re-derivation of ``hirearchy quality --json`` (design org-growth-phase-0b 20.2, 21).

It reads ONLY the copied raw files of one stream evidence dir (E7's layout: ``msgs/``, ``run-logs/``, ``service/``, ``playbook/``, ``org-files/``,
``memos/`` with ``memos/versions/INDEX.txt``, ``org-git-log.txt``) and writes a JSON in the shape of design 9.4's ``quality_data``, for every key it
can derive. Standard library only (Python 3.11); it never imports hirearchy product code. ``final-services-progress-status-health.txt`` is never an
input: the self-check reads it only as a published cross-check.

Usage:
  python3 -B rederive_quality.py <streamdir> --out <dir> [--compare <quality.json>]
  python3 -B rederive_quality.py --selfcheck <E7EV> --out <harness-selfcheck dir>

``--out`` writes ``<dir>/rederived.json``; ``--compare`` also writes ``<dir>/mismatches.txt`` (``MISMATCH <path>: product=<v> rederived=<v>``, one
``NOT DERIVED <path>`` per key the re-derivation does not derive, then ``compared <k> keys, <m> mismatches``) and exits 0; an unreadable input
exits 2. ``--selfcheck`` re-derives E7's s1-s3 into ``<dir>/e7-<sN>/rederived.json``, compares every entry of
``selfcheck/e7-expected-rederive.json`` (transcribed from design 19.3's E7 block, never from this script's output), writes
``<dir>/e7-<sN>/rederive-selfcheck.txt``, prints ``OK``/``MISMATCH`` lines, ``CROSSCHECK`` lines (report only) and ``selfcheck rederive: <k> of <n>
OK``, and exits 0 iff all are OK.

Rules and where they come from. The design text (sections 3, 4, 5, 6, 7, 9.4 of org-growth-phase-0b.md; 0a 5.5; 0a.1 moved_past; 0a.2 P1-P4;
0a.3/0a.5 A2) names every rule, but for the exact arithmetic several are only precise in the product source, which was READ (never imported) to
learn the rule and then re-implemented here. Rule learned from:
  - src/hirearchy/reflection/_cases.py: the chain (``head``), the window and ``cut``, ``_spend`` (relayed runs, relayed_returned/to_user/overlap,
    user grants, ``user_ceiling`` with 0a.5 A2's ``unapproved_reworks``), ``_top_ups``, ``_runs_unknown``, ``_verdict`` (links, links_tier, confirmed).
  - src/hirearchy/reflection/api.py: ``Delivery.counted/voided/decisive/outcome``, ``case_spend``, ``user_spend``, ``user_cost``,
    ``user_approved``, ``confirmed_criteria``, ``regressions``, the mark dataclasses' fields.
  - src/hirearchy/reflection/_quality_rules.py: ``signer_of``, ``deliveries_of`` (``superseded``), ``unjudged_cases``, ``not_on_a_delivery``,
    ``judged_cases``, ``repeat_alarm`` (``_reading``, ``not_counted``), ``cost_alarm``, ``quality_thresholds``.
  - src/hirearchy/reflection/_causes.py: ``cause_of`` (rules 1-6, ``_judged_result``, ``_before_verdict``, ``_link_note``), ``attribution``,
    ``failure_class``.
  - src/hirearchy/reflection/_records.py: ``_carried``, ``_answering``, ``_attributed`` (edited_at = min write time of the differs findings), the
    timeline sort (time, then contract < playbook < top-up < charter < model).
  - src/hirearchy/reflection/_marks.py: contract marks (``answers`` parts), playbook marks (cited criteria through link notes, own words,
    tagged), top-up marks.
  - src/hirearchy/reflection/_deliverable_checks.py: P3's folder rule (pairs newest first, the walk past relayed reworks, ``differs`` names the
    newest pair, ``relayed`` names the equal earlier pair), the floor (files written before the contract's ``created``), ``_in_the_organization``.
    ``at_result`` (app/_checked_versions.py's port doc: the version at the first commit holding the result) is read from
    ``memos/versions/INDEX.txt`` as the brief says: the latest committed version at or before the result's time; ``current`` is INDEX's
    ``working tree`` md5. The checked artifact is named by the result's ``## Artifacts`` section only (``kernel.artifact_paths``).
  - src/hirearchy/services/api.py and services/_criteria.py: ``number_criteria``, ``amendment_ids``, ``version_in_force``, ``line_key``,
    ``changed_lines``, ``criterion_words``; services/_hints.py: ``client_words`` (the verdict's own words).
  - src/hirearchy/kernel/_message.py, _text.py, _timeutil.py: ``latest_results``, ``verdict_tier``, ``link_ids``, run credits,
    ``artifact_paths``, ``strip_markers``, ``clip_line``, ``msg_time``.
  - src/hirearchy/mail/api.py (``moved_past``), mail/_tasks.py (``blocked_tasks``), progress/_quality.py (``held_tasks``, ``left_blocked``),
    budget/_query.py (held = budget received - handed down - run logs).
  - src/hirearchy/health/_escapes.py and health/_rework.py: the verifier's ``rechecks`` and ``rework_runs`` (MailEscapeCounter, ClientRework).
  - src/hirearchy/progress/_quality_facts.py and progress/_quality_render.py: the JSON keys and their null rules (9.4), ``two_decimals``.

Not derived (listed as ``NOT DERIVED`` by ``--compare``): ``stalled`` of an ``open`` case (needs the live task state, not in the files); the
timeline's charter and model marks when org-git-log.txt shows a later commit of an AGENT.md or ORG.md (the copy keeps no file contents of past
commits). ``history`` is derived from org-git-log.txt (``known`` = the log has commits). ``nested`` is derived from the copied service folder only
(the copy keeps one service).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path, PurePosixPath

ROOT = "root"
RUNTIME = "runtime"
SOURCES = ("human", "relayed")
BOXES = ("inbox", "inflight", "read", "sent")
RECEIVED_BOXES = ("inbox", "inflight", "read")
FEEDBACK_HEADER = (
    "Client feedback for reflection only: it does not change this task's acceptance criteria or outcome; "
    "report `done` only if every criterion is met."
)
BASE_DELIVERED_HEADING = "## Base: the version the client judged"
RUN_CREDIT_TITLE = "run credit"
LASTING_WORDS = ("always", "never", "from now on")
CAUSES = ("relayed-error", "relayed-carry-over", "contract-gap", "reviewer-miss", "untyped")
COUNTED_CAUSES = ("reviewer-miss", "untyped")
NOT_ITS_CAUSES = ("contract-gap", "relayed-error", "relayed-carry-over")
STAMP_FORMAT = "%Y%m%dT%H%M%S%f"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
EARLIEST = datetime.min.replace(tzinfo=timezone.utc)
KIND_RANK = {"contract": 0, "playbook": 1, "top-up": 2, "charter": 3, "model": 4}
RESULTS_PER_SOURCE = 20
PATHS_PER_RESULT = 10
LINES_LISTED = 10
LINE_CLIP = 600
HISTORY_LIMIT = 40
DEFAULTS = {"min_judged": 3, "repeat_window": 3, "repeat_failures": 2, "cost_ratio": "1.25"}
_EVIDENCE_ID = re.compile(r"C\d+|R\d+|\d{8}T\d{12}-[a-z0-9./-]+")
_CRITERION = re.compile(r"C\d+")
_TAG = re.compile(r"(?<![A-Za-z0-9])[CR]\d+(?![0-9])")
_LINE_MARKER = re.compile(r"\s*(?:>|#{1,6}(?=\s)|[-*+\u2022](?=\s)|\d{1,3}[.)](?=\s)|\[[ xX]\](?=\s))")

# The self-check's amended expectations and the declared product deviation F-G0-1 are recorded in selfcheck/e7-expected-rederive.json (each
# amended entry carries its published value and the ruling it rests on: manager-decision-selfcheck.md, 2026-10-25) and in
# harness-selfcheck/SELFCHECK.md. The code was never fitted to a published number.


class Unreadable(Exception):
    """An input that cannot be read: exit 2."""


# ------------------------------------------------------------------------------------------------------------------------ a small YAML subset


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _blank(line: str) -> bool:
    s = line.strip()
    return not s or s.startswith("#")


_KEY = re.compile(r"""^(?:'(?P<sq>(?:[^']|'')*)'|"(?P<dq>(?:[^"\\]|\\.)*)"|(?P<pl>[^\s'"#\-?:][^:]*?|-[^\s:][^:]*?))\s*:(?:\s+(?P<rest>.*)|$)""")


def _convert(text: str) -> object:
    s = text.strip()
    if s in ("", "~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"):
        return True
    if s in ("false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF"):
        return False
    if re.fullmatch(r"[-+]?[0-9]+", s):
        return int(s)
    if s == "[]":
        return []
    if s == "{}":
        return {}
    if s.startswith("[") and s.endswith("]"):
        return [_convert(x) for x in s[1:-1].split(",") if x.strip()]
    return s


class _Yaml:
    """Block mappings and sequences, plain and quoted scalars that may wrap onto more-indented lines: the frontmatter the product writes."""

    def __init__(self, text: str):
        self.lines = text.split("\n")
        self.i = 0

    def _skip(self) -> None:
        while self.i < len(self.lines) and _blank(self.lines[self.i]):
            self.i += 1

    def parse(self) -> object:
        self._skip()
        if self.i >= len(self.lines):
            return None
        return self._block(_indent(self.lines[self.i]))

    def _block(self, ind: int) -> object:
        self._skip()
        line = self.lines[self.i]
        if line.strip() == "-" or line.lstrip().startswith("- "):
            return self._seq(ind)
        return self._map(ind)

    def _nested(self, ind: int, allow_seq_same: bool) -> object:
        self._skip()
        if self.i < len(self.lines):
            nxt = self.lines[self.i]
            n = _indent(nxt)
            if n > ind or (allow_seq_same and n == ind and (nxt.strip() == "-" or nxt.lstrip().startswith("- "))):
                return self._block(n)
        return None

    def _map(self, ind: int) -> dict:
        out: dict = {}
        while True:
            self._skip()
            if self.i >= len(self.lines):
                break
            line = self.lines[self.i]
            if _indent(line) != ind or line.lstrip().startswith("- "):
                break
            m = _KEY.match(line.strip())
            if not m:
                raise ValueError(f"not a mapping line: {line!r}")
            key = m.group("sq").replace("''", "'") if m.group("sq") is not None else (
                m.group("dq") if m.group("dq") is not None else m.group("pl").strip())
            rest = (m.group("rest") or "").strip()
            self.i += 1
            if not rest or rest.startswith("#"):
                out[key] = self._nested(ind, True)
            else:
                out[key] = self._scalar(rest, ind)
        return out

    def _seq(self, ind: int) -> list:
        out: list = []
        while True:
            self._skip()
            if self.i >= len(self.lines):
                break
            line = self.lines[self.i]
            s = line.strip()
            if _indent(line) != ind or not (s == "-" or s.startswith("- ")):
                break
            body = s[1:].strip()
            if not body:
                self.i += 1
                out.append(self._nested(ind, False))
            elif body[0] not in "'\"[{" and _KEY.match(body):
                self.lines[self.i] = " " * (ind + 2) + body
                out.append(self._map(ind + 2))
            else:
                self.i += 1
                out.append(self._scalar(body, ind))
        return out

    def _more(self, ind: int) -> list[str]:
        """The continuation lines of a scalar: the following lines indented deeper than ``ind`` (blank lines kept as '')."""
        extra: list[str] = []
        j = self.i
        while j < len(self.lines):
            ln = self.lines[j]
            if ln.strip() == "":
                extra.append("")
                j += 1
                continue
            if _indent(ln) <= ind:
                break
            extra.append(ln.strip())
            j += 1
        while extra and extra[-1] == "":
            extra.pop()
        self.i += len(extra)
        return extra

    @staticmethod
    def _fold(parts: list[str]) -> str:
        out = ""
        pending_break = False
        for k, p in enumerate(parts):
            if p == "":
                out += "\n"
                pending_break = True
                continue
            if k and not pending_break:
                out += " "
            out += p
            pending_break = False
        return out

    def _scalar(self, first: str, ind: int) -> object:
        if first[0] in "'\"":
            q = first[0]
            raw = first
            while not self._closed(raw, q):
                if self.i >= len(self.lines):
                    raise ValueError("unterminated quoted scalar")
                ln = self.lines[self.i]
                self.i += 1
                raw += "\n" + ln.strip()
            inner = raw[1:self._close_at(raw, q)]
            folded = self._fold(inner.split("\n"))
            if q == "'":
                return folded.replace("''", "'")
            return bytes(folded, "utf-8").decode("unicode_escape") if "\\" in folded else folded
        parts = [first.split(" #", 1)[0].rstrip()] + self._more(ind)
        return _convert(self._fold(parts))

    @staticmethod
    def _close_at(raw: str, q: str) -> int:
        k = 1
        while k < len(raw):
            c = raw[k]
            if q == "'" and c == "'":
                if k + 1 < len(raw) and raw[k + 1] == "'":
                    k += 2
                    continue
                return k
            if q == '"' and c == "\\":
                k += 2
                continue
            if q == '"' and c == '"':
                return k
            k += 1
        return -1

    def _closed(self, raw: str, q: str) -> bool:
        return self._close_at(raw, q) != -1


def parse_yaml(text: str) -> object:
    return _Yaml(text).parse()


def split_frontmatter(text: str) -> tuple[dict, str]:
    """``(meta, body)`` of a file's text; ``({}, text)`` without a frontmatter block (the product's ``kernel.split_frontmatter``)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end == -1 and text.endswith("\n---"):
            end = len(text) - 4
        if end != -1:
            meta = parse_yaml(text[4:end]) or {}
            return (meta if isinstance(meta, dict) else {}), text[end + 5:]
    return {}, text


# ------------------------------------------------------------------------------------------------------------------------ messages and time


def _int(v: object, default: int = 0) -> int:
    if v is None or isinstance(v, bool):
        return default
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _opt_int(v: object) -> int | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _text(v: object) -> str | None:
    return str(v) if v else None


@dataclass(frozen=True)
class Msg:
    id: str
    sender: str
    to: str
    type: str
    title: str = ""
    created: str = ""
    body: str = ""
    budget: int = 0
    reply_to: str | None = None
    status: str | None = None
    revises: str | None = None
    supersedes: str | None = None
    service: str | None = None
    contract: int | None = None
    playbook: int | None = None
    feedback: str | None = None
    source: str | None = None
    criterion: str | None = None


def message_of(meta: dict, body: str, stem: str = "") -> Msg:
    return Msg(
        id=str(meta.get("id") or stem), sender=str(meta.get("from", "")), to=str(meta.get("to", "")), type=str(meta.get("type", "note")),
        title=str(meta.get("title") or ""), created=str(meta.get("created") or ""), body=body.strip(), budget=_int(meta.get("budget") or 0),
        reply_to=_text(meta.get("reply_to")), status=_text(meta.get("status")), revises=_text(meta.get("revises")),
        supersedes=_text(meta.get("supersedes")), service=_text(meta.get("service")), contract=_opt_int(meta.get("contract")),
        playbook=_opt_int(meta.get("playbook")), feedback=_text(meta.get("feedback")), source=_text(meta.get("source")),
        criterion=_text(meta.get("criterion")),
    )


def stamp_of(name: str) -> datetime | None:
    try:
        return datetime.strptime(name[:21], STAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_time(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def msg_time(m: Msg) -> datetime | None:
    return stamp_of(m.id) or parse_time(m.created)


def micros(when: datetime) -> int:
    return (when - EPOCH) // timedelta(microseconds=1)


def utc(when: datetime | None) -> str | None:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if when is not None else None


def parent(addr: str) -> str | None:
    if addr == ROOT:
        return None
    return addr.rsplit("/", 1)[0] if "/" in addr else ROOT


def latest_results(msgs) -> dict[str, Msg]:
    out: dict[str, Msg] = {}
    for m in msgs:
        if m.type == "result" and m.reply_to and (m.reply_to not in out or m.id > out[m.reply_to].id):
            out[m.reply_to] = m
    return out


def verdict_tier(note: Msg) -> str:
    if note.sender != ROOT:
        return "agent"
    if note.source is None:
        return "human"
    return note.source if note.source in SOURCES else "relayed"


def link_ids(note: Msg) -> tuple[str, ...]:
    return tuple(p for p in (x.strip() for x in (note.criterion or "").split(",")) if p)


def credited_stems(received) -> set[str]:
    out = set()
    for n in received:
        prefix = f"{RUN_CREDIT_TITLE} {n.to}@"
        if n.sender == RUNTIME and n.type == "note" and n.budget > 0 and n.title.startswith(prefix):
            out.add(n.title[len(prefix):])
    return out


def artifact_paths(body: str) -> list[str]:
    paths: list[str] = []
    inside = False
    for line in body.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower() == "artifacts"
        elif inside and line.strip():
            paths.append(line.strip().lstrip("-* ").split(" (", 1)[0])
    return paths


def client_words(m: Msg) -> str:
    body = m.body.removeprefix(FEEDBACK_HEADER).strip()
    return "" if body == "accepted" else body


def clip_line(text: object, limit: int) -> str:
    t = " ".join(str(text).split())
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "\u2026"


def strip_markers(line: str) -> str:
    while (m := _LINE_MARKER.match(line)) and m.end() > 0:
        line = line[m.end():]
    return line.lstrip()


def line_key(line: str) -> str:
    return "".join(ch for ch in strip_markers(line).casefold() if ch.isalnum())


def changed_lines(current: str, new: str) -> list[str]:
    have = Counter(k for line in current.splitlines() if (k := line_key(line)))
    out: list[str] = []
    for line in new.splitlines():
        k = line_key(line)
        if not k:
            continue
        if have[k] > 0:
            have[k] -= 1
        else:
            out.append(line.strip())
    return out


def two_decimals(value: Fraction) -> str:
    h = (value.numerator * 200 + value.denominator) // (2 * value.denominator)
    return f"{h // 100}.{h % 100:02d}"


# ------------------------------------------------------------------------------------------------------------------------ the stream's files


@dataclass
class Contract:
    version: int
    defined_by: str
    acceptance: list[str]
    budget: int
    defined: datetime | None
    created: datetime | None
    answers: str
    initiated: str
    deliverable: dict
    name: str


@dataclass
class Playbook:
    version: int
    revised: datetime | None
    by: str
    body: str
    evidence: list[str]
    admitted: str


@dataclass
class Criterion:
    id: str
    text: str
    since: int
    by: str
    current: bool
    answers: str = ""
    user: bool = False


@dataclass
class Stream:
    root: Path
    read: set[str] = field(default_factory=set)
    received: dict[str, list[Msg]] = field(default_factory=dict)
    sent: dict[str, list[Msg]] = field(default_factory=dict)
    agents: list[str] = field(default_factory=list)
    charters: dict[str, dict] = field(default_factory=dict)
    logs: dict[str, list[str]] = field(default_factory=dict)
    service: str = ""
    owner: str = ""
    contracts: list[Contract] = field(default_factory=list)
    playbooks: list[Playbook] = field(default_factory=list)
    files: list[tuple[str, str, int]] = field(default_factory=list)  # deliverable folder: (name, md5, mtime_us)
    versions: dict[str, list[tuple[int, str, datetime, str]]] = field(default_factory=dict)  # path -> (n, sha, time, md5)
    working: dict[str, str] = field(default_factory=dict)  # path -> working tree md5
    git: list[tuple[str, datetime | None, list[str]]] | None = None
    sent_pos: dict[str, int] = field(default_factory=dict)  # message id -> position in ``git`` (newest first) of the first commit holding its sent copy
    org_config: dict | None = None
    org_error: str = ""

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def text(self, p: Path) -> str:
        try:
            data = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise Unreadable(f"{p}: {exc}") from exc
        self.read.add(self.rel(p))
        return data

    def recv(self, addr: str) -> list[Msg]:
        return self.received.get(addr, [])

    def snt(self, addr: str) -> list[Msg]:
        return self.sent.get(addr, [])

    def exists(self, addr: str) -> bool:
        return addr in self.agents

    def children(self, addr: str) -> list[str]:
        return [a for a in self.agents if parent(a) == addr]

    def subtree(self, addr: str) -> list[str]:
        return [a for a in self.agents if a == addr or a.startswith(addr + "/")]


def _resolve(dashed: str, known: dict[str, str], agents: set[str]) -> str:
    if dashed in known:
        return known[dashed]
    for k in range(len(dashed) - 1, 0, -1):  # longest known prefix that is an agent: the rest is one name
        if dashed[k] == "-" and known.get(dashed[:k]) in agents:
            return known[dashed[:k]] + "/" + dashed[k + 1:]
    return dashed.replace("-", "/")


def load_stream(root: Path) -> Stream:
    root = Path(root)
    if not (root / "msgs").is_dir():
        raise Unreadable(f"{root}: no msgs/ folder (not a stream evidence dir)")
    s = Stream(root)
    raw: list[tuple[str, str, Msg]] = []
    addrs: set[str] = set()
    for d in sorted(p for p in (root / "msgs").iterdir() if p.is_dir()):
        if d.name in BOXES:
            dashed, box = ROOT, d.name
        else:
            dashed, _, box = d.name.rpartition("-")
            if box not in BOXES or not dashed:
                continue
        for f in sorted(d.glob("*.md")):
            try:
                meta, body = split_frontmatter(s.text(f))
            except ValueError as exc:
                raise Unreadable(f"{f}: frontmatter does not parse ({exc})") from exc
            m = message_of(meta, body, f.stem)
            raw.append((dashed, box, m))
            addrs |= {m.sender, m.to}
    charter_files = sorted((root / "org-files").glob("*-AGENT.md")) if (root / "org-files").is_dir() else []
    known = {a.replace("/", "-"): a for a in addrs if a and a not in (ROOT, RUNTIME)}
    known[ROOT] = ROOT
    agents = {a for a in known.values() if a not in (ROOT, RUNTIME)}
    for f in charter_files:
        addr = _resolve(f.name[: -len("-AGENT.md")], known, agents)
        try:
            meta, _ = split_frontmatter(s.text(f))
        except ValueError:
            meta = {}
        s.charters[addr] = meta
        agents.add(addr)
    if charter_files:
        s.agents = sorted(s.charters)
    else:
        s.agents = sorted(agents)
    for dashed, box, m in raw:
        addr = ROOT if dashed == ROOT else _resolve(dashed, known, set(s.agents))
        target = s.sent if box == "sent" else s.received
        target.setdefault(addr, []).append(m)
    for box in (s.sent, s.received):
        for addr in box:
            box[addr] = sorted({m.id: m for m in box[addr]}.values(), key=lambda m: m.id)
    if (root / "run-logs").is_dir():
        for d in sorted(p for p in (root / "run-logs").iterdir() if p.is_dir()):
            addr = _resolve(d.name, known, set(s.agents))
            s.logs[addr] = sorted(p.stem for p in d.glob("*.log") if not p.name.startswith("."))
            s.read.add(s.rel(d) + "/*.log (names)")
    _load_service(s)
    _load_memos(s)
    _load_git(s)
    org = root / "org-files" / "ORG.md"
    if org.is_file():
        try:
            s.org_config, _ = split_frontmatter(s.text(org))
        except ValueError:
            s.org_config, s.org_error = None, "unparseable"
    return s


def _contract_of(meta: dict) -> Contract:
    deliverable = meta.get("deliverable")
    return Contract(
        version=max(1, _int(meta.get("version"), 1)), defined_by=str(meta.get("defined_by") or ""),
        acceptance=[str(a) for a in (meta.get("acceptance") or [])], budget=max(1, _int(meta.get("budget"), 1)),
        defined=parse_time(meta.get("defined")), created=parse_time(meta.get("created") or meta.get("defined")),
        answers=str(meta.get("answers") or ""), initiated=str(meta.get("initiated") or ""),
        deliverable=dict(deliverable) if isinstance(deliverable, dict) else {}, name=str(meta.get("name") or ""),
    )


def _merged(s: Stream, folder: Path, kind: str) -> list[tuple[dict, str]]:
    """The kept versions (``history--{kind}.v<n>.md``) then the current one, by the version they state; the current one wins a tie."""
    files = sorted(folder.glob(f"history--{kind}.v*.md"), key=lambda p: _int(re.sub(r"\D", "", p.name.split(".v")[-1]), 0))
    current = folder / f"current-{kind}.md"
    if current.is_file():
        files.append(current)
    by_version: dict[int, tuple[dict, str]] = {}
    for f in files:
        try:
            meta, body = split_frontmatter(s.text(f))
        except ValueError as exc:
            raise Unreadable(f"{f}: frontmatter does not parse ({exc})") from exc
        by_version[_int(meta.get("version"))] = (meta, body)
    return [by_version[v] for v in sorted(by_version)]


def _load_service(s: Stream) -> None:
    folder = s.root / "service"
    if not (folder / "current-SERVICE.md").is_file():
        return
    s.contracts = [_contract_of(meta) for meta, _ in _merged(s, folder, "SERVICE")]
    s.service = s.contracts[-1].name if s.contracts else ""
    owners = sorted({m.to for msgs in s.sent.values() for m in msgs if m.type == "task" and m.service == s.service})
    if not owners and (s.root / "org-files").is_dir():
        for f in (s.root / "org-files").glob(f"current-*-services-{s.service}-SERVICE.md"):
            owners.append(_resolve(f.name[len("current-"): -len(f"-services-{s.service}-SERVICE.md")], {a.replace('/', '-'): a for a in s.agents}, set(s.agents)))
    s.owner = owners[0] if owners else ""
    pfolder = s.root / "playbook"
    if (pfolder / "current-PLAYBOOK.md").is_file():
        for meta, body in _merged(s, pfolder, "PLAYBOOK"):
            ev = meta.get("evidence")
            s.playbooks.append(Playbook(
                version=_int(meta.get("version")), revised=parse_time(meta.get("revised")), by=str(meta.get("by") or ""), body=body.strip(),
                evidence=[t for x in ev if (t := str(x).strip())] if isinstance(ev, list) else [], admitted=str(meta.get("admitted") or ""),
            ))


def _load_memos(s: Stream) -> None:
    folder = s.root / "memos"
    if not folder.is_dir():
        return
    for f in sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")):
        data = f.read_bytes()
        s.read.add(s.rel(f))
        s.files.append((f.name, hashlib.md5(data).hexdigest(), f.stat().st_mtime_ns // 1000))
    index = folder / "versions" / "INDEX.txt"
    if index.is_file():
        for line in s.text(index).splitlines():
            m = re.match(r"^(\S+) v(\d+) (\S+) (\S+) md5 ([0-9a-f]{32})$", line.strip())
            if m:
                when = parse_time(m.group(4))
                s.versions.setdefault(m.group(1), []).append((int(m.group(2)), m.group(3), when, m.group(5)))  # type: ignore[arg-type]
                continue
            w = re.match(r"^(\S+) working tree md5 ([0-9a-f]{32})", line.strip())
            if w:
                s.working[w.group(1)] = w.group(2)


def _load_git(s: Stream) -> None:
    log = s.root / "org-git-log.txt"
    if not log.is_file():
        return
    commits: list[tuple[str, datetime | None, list[str]]] = []
    for line in s.text(log).splitlines():
        if line.startswith("commit "):
            commits.append((line.split()[1], None, []))
        elif line.startswith("Date:") and commits:
            sha, _, paths = commits[-1]
            commits[-1] = (sha, parse_time(line[5:].strip().replace(" +0000", "+00:00").replace(" ", "T", 1)), paths)
        elif " | " in line and commits and line.startswith(" "):
            commits[-1][2].append(line.split(" | ")[0].strip())
    s.git = commits
    for pos in range(len(commits) - 1, -1, -1):  # oldest first: the first commit that holds each sent copy
        for path in commits[pos][2]:
            m = _SENT_COPY.search(path)
            if m:
                s.sent_pos.setdefault(m.group(1), pos)


_SENT_COPY = re.compile(r"(?:^|/)sent/([^/{}=> ]+)\.md$")  # ``lead/sent/<id>.md``, ``sent/<id>.md`` and git's ``.../sent/<id>.md``


def _commit_pos(s: Stream, short: str) -> int | None:
    """Position in ``s.git`` (newest first) of the commit whose sha starts with ``short``; None when the log does not hold it."""
    return next((i for i, c in enumerate(s.git or []) if c[0].startswith(short)), None)


# ------------------------------------------------------------------------------------------------------------------------ cases (4.1, 4.2)


@dataclass(frozen=True)
class Verdict:
    verdict: str
    note: str
    created: datetime | None
    task_id: str
    step: int
    message: Msg
    tier: str
    links: tuple[str, ...]
    links_tier: str
    confirmed: tuple[str, ...]
    link_notes: tuple[Msg, ...]


@dataclass
class Case:
    id: str
    service: str
    owner: str
    tasks: list[Msg]
    result: Msg | None
    state: str
    runs: int
    relayed_runs: int
    credited: int
    budget: int
    returned: int
    relayed_returned: int
    relayed_to_user: int
    relayed_overlap: int
    user_granted: int
    user_ceiling: int
    unapproved: tuple[str, ...]
    top_ups: tuple[tuple[str, str, int], ...]
    cut: bool
    runs_unknown: str
    verdicts: list[Verdict]
    client_kind: str

    @property
    def title(self) -> str:
        return self.tasks[0].title


def _within(stamp: str, bounds: tuple[str, str | None]) -> bool:
    return bounds[0] <= stamp and (bounds[1] is None or stamp < bounds[1])


def _handed_down(sent, team, start: str, end: str | None) -> list[Msg]:
    return [m for m in sent if m.type == "note" and m.budget > 0 and m.to in team and m.id[:21] >= start and (end is None or m.id[:21] <= end)]


def stamps(s: Stream, team, start: str, end: str | None) -> list[tuple[str, bool]]:
    found = []
    for addr in team:
        logs = s.logs.get(addr, [])
        credited = credited_stems(s.recv(addr)) if logs else set()
        for st in logs:
            name = f"{st}.log"[:21]
            if name >= start and (end is None or name <= end):
                found.append((name, st in credited))
    return sorted(found)


def _spend(tasks, results, sent, team, human, start, end, charged, per_request):
    """design 4.2 / 0a.3 / 0a.5 A2 (rule learned from reflection/_cases.py ``_spend``)."""
    bounds = [(t.id[:21], tasks[k + 1].id[:21] if k + 1 < len(tasks) else None) for k, t in enumerate(tasks)]
    relayed = [b for t, b in zip(tasks, bounds) if t.source == "relayed"]

    def in_relayed(x: str) -> bool:
        return any(_within(x, b) for b in relayed)

    handed = _handed_down(sent, team, start, end)
    grants = sorted((m for m in handed if human and not in_relayed(m.id[:21])), key=lambda m: m.id)

    def back_to_user(k: int, t: Msg) -> int:
        r = results.get(t.id)
        if not human or t.source != "relayed" or r is None or (k + 1 < len(tasks) and r.id >= tasks[k + 1].id):
            return 0
        funds = t.budget + sum(n.budget for n in handed if _within(n.id[:21], bounds[k]))
        ran = sum(1 for x in charged if _within(x, bounds[k]))
        return max(0, r.budget - max(0, funds - ran))

    to_user = {t.id: back_to_user(k, t) for k, t in enumerate(tasks)}
    users = [t for t in tasks if t.source != "relayed"]
    ceiling = 0
    unapproved: list[str] = []
    for h in (sorted([*users, *grants], key=lambda m: m.id) if human else []):
        runs = sum(1 for x in charged if x < h.id[:21] and not in_relayed(x))
        given = sum(t.budget for t in users if t.id < h.id) + sum(g.budget for g in grants if g.id < h.id)
        back = sum(min(r.budget, t.budget) for t in users if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
        back += sum(to_user[t.id] for t in tasks if t.id < h.id and (r := results.get(t.id)) is not None and r.id < h.id)
        committed = runs + max(0, given - runs - back)
        if h.type == "task" and h.source == "human" and h.revises and h.budget == 1 and max(per_request, ceiling) - committed <= 0:
            unapproved.append(h.id)
            continue
        out = sum(1 for d in unapproved if not ((r := results.get(d)) is not None and r.id < h.id and r.budget >= 1))
        ceiling = max(ceiling, max(0, committed - out) + h.budget)
    overlap = 0
    for k, t in enumerate(tasks[:-1]):
        r = results.get(t.id)
        if t.source != "relayed" or not any(u.source != "relayed" for u in tasks[k + 1:]) or (r is not None and r.id < tasks[k + 1].id):
            continue
        funds = t.budget + sum(n.budget for n in handed if _within(n.id[:21], bounds[k]))
        ran = sum(1 for x in charged if _within(x, bounds[k]))
        overlap += max(0, funds - (min(r.budget, t.budget) if r is not None else 0) - ran)
    return dict(
        relayed_runs=sum(1 for x in charged if in_relayed(x)),
        relayed_returned=sum(min(r.budget, t.budget) for t in tasks if t.source == "relayed" and (r := results.get(t.id)) is not None),
        relayed_to_user=sum(to_user.values()), relayed_overlap=overlap, user_granted=sum(g.budget for g in grants), user_ceiling=ceiling,
        unapproved=tuple(unapproved),
    )


def _verdict(note: Msg, step: int, links: list[Msg]) -> Verdict:
    candidates = sorted((m for m in (note, *links) if link_ids(m)), key=lambda m: m.id)

    def tier(m: Msg) -> str:
        return "relayed" if m is note else verdict_tier(m)

    winning = [m for m in candidates if tier(m) == "human"] or candidates
    confirmed = dict.fromkeys(x for m in candidates if m is not note and tier(m) == "human" for x in link_ids(m) if x.startswith("C"))
    return Verdict(
        note.feedback or "", client_words(note), msg_time(note), note.reply_to or "", step, note, verdict_tier(note),
        link_ids(winning[-1]) if winning else (), tier(winning[-1]) if winning else "", tuple(confirmed), tuple(sorted(links, key=lambda m: m.id)),
    )


def build_cases(s: Stream, client: str, mine: list[Msg], service: str, per_request: int) -> list[Case]:
    sent = s.snt(client)
    by_id = {m.id: m for m in mine}

    def head(m: Msg) -> str:
        seen = {m.id}
        while m.revises in by_id and m.revises not in seen and by_id[m.revises].to == m.to:  # type: ignore[index]
            m = by_id[m.revises]  # type: ignore[index]
            seen.add(m.id)
        return m.id

    chains: dict[str, list[Msg]] = {}
    for m in mine:
        chains.setdefault(head(m), []).append(m)
    results = latest_results(s.recv(client))
    notes = sorted((m for m in sent if m.type == "note" and m.feedback and m.reply_to in by_id), key=lambda m: m.id)
    by_note = {n.id: n for n in notes}
    link_notes = sorted((m for m in sent if m.type == "note" and not m.feedback and link_ids(m) and m.reply_to in by_note), key=lambda m: m.id)
    kind = "human" if client == ROOT else "agent"
    out = []
    for first, tasks in chains.items():
        owner = tasks[0].to
        others = sorted(m.id for m in sent if m.type == "task" and m.to == owner)
        team = s.subtree(owner)
        ids = {t.id for t in tasks}
        last = tasks[-1]
        res = results.get(last.id)
        state = res.status if res is not None and res.status in ("done", "failed", "blocked") else "open"
        final = res is not None and res.status in ("done", "failed")
        end = res.id[:21] if res is not None and final else None
        later = next((i for i in others if i > last.id and i not in ids), None)
        cut = later is not None and (end is None or later[:21] < end)
        if later is not None and cut:
            end = later[:21]
        start = tasks[0].id[:21]
        st = stamps(s, team, start, end)
        charged = [x for x, credited in st if not credited]
        sp = _spend(tasks, results, sent, team, kind == "human", start, end, charged, per_request)
        step = {t.id: i for i, t in enumerate(tasks)}
        verdicts = [_verdict(n, step[n.reply_to], [m for m in link_notes if m.reply_to == n.id]) for n in notes if n.reply_to in ids]  # type: ignore[index]
        tops = [(t.id, t.source or "unrecorded", t.budget) for t in tasks[1:]] + [(n.id, "granted", n.budget) for n in _handed_down(sent, team, start, end)]
        out.append(Case(
            id=first, service=service, owner=owner, tasks=tasks, result=res, state=state, runs=len(charged), relayed_runs=sp["relayed_runs"],
            credited=sum(1 for _, c in st if c), budget=sum(t.budget for t in tasks),
            returned=sum(min(r.budget, t.budget) for t in tasks if (r := results.get(t.id)) is not None),
            relayed_returned=sp["relayed_returned"], relayed_to_user=sp["relayed_to_user"], relayed_overlap=sp["relayed_overlap"],
            user_granted=sp["user_granted"], user_ceiling=sp["user_ceiling"], unapproved=sp["unapproved"], top_ups=tuple(sorted(tops)),
            cut=cut, runs_unknown=_runs_unknown(s, owner, service, tasks[0], state, cut, st), verdicts=verdicts, client_kind=kind,
        ))
    return out


def _runs_unknown(s: Stream, owner: str, service: str, head: Msg, state: str, cut: bool, st) -> str:
    if not service and not s.exists(owner):
        return "assignee retired"
    hired = parse_time((s.charters.get(owner) or {}).get("created"))
    sent = msg_time(head)
    if hired is not None and sent is not None and sent < hired:
        return f"sent before {owner} was hired again: the retired team's run logs are not read"
    if state in ("done", "failed") and not cut and not st:
        return "no run log in its window"
    return ""


def case_spend(c: Case) -> int:
    still = 0 if c.state in ("done", "failed") else max(0, c.budget - c.runs - c.returned)
    return c.runs + still


def user_spend(c: Case) -> int:
    runs = c.runs - c.relayed_runs
    if c.state in ("done", "failed"):
        return runs
    budget = sum(t.budget for t in c.tasks if t.source != "relayed")
    return runs + max(0, budget - runs - (c.returned - c.relayed_returned + c.relayed_to_user))


def user_cost(c: Case) -> int:
    return max(0, user_spend(c) - c.relayed_overlap)


def user_approved(c: Case, budget: int) -> int:
    return max(budget, c.user_ceiling)


# ------------------------------------------------------------------------------------------------------------------------ deliveries (4.3, 4.4)


@dataclass(frozen=True)
class Delivery:
    case: str
    task: Msg
    result: Msg
    step: int
    signer: str
    verdicts: tuple[Verdict, ...]
    superseded: str
    edited_at: int = 0
    edited: bool = False
    given: bool = False

    @property
    def counted(self) -> tuple[Verdict, ...]:
        human = tuple(v for v in self.verdicts if v.tier == "human")
        if self.edited_at <= 0:
            return human
        return tuple(v for v in human if v.created is None or micros(v.created) < self.edited_at)

    @property
    def voided(self) -> tuple[Verdict, ...]:
        if self.edited_at <= 0:
            return ()
        return tuple(v for v in self.verdicts if v.tier == "human" and v.created is not None and micros(v.created) >= self.edited_at)

    @property
    def judged(self) -> bool:
        return bool(self.counted)

    @property
    def escape(self) -> bool:
        return any(v.verdict == "reject" for v in self.counted)

    @property
    def decisive(self) -> Verdict | None:
        rejects = [v for v in self.counted if v.verdict == "reject"]
        return rejects[-1] if rejects else self.counted[-1] if self.counted else None

    @property
    def outcome(self) -> str:
        if self.escape:
            return "rejected"
        return "accepted" if self.judged else "neither" if self.voided else "none"


def signer_of(owner: str, task_id: str, done_id: str, owner_sent, owner_received, reports) -> str:
    later = {m.id for m in owner_sent if m.type == "task" and m.id > task_id}
    signed = [r for r in owner_received if r.type == "result" and r.status == "done" and r.sender in reports and r.reply_to in later and r.id < done_id]
    return max(signed, key=lambda r: r.id).sender if signed else owner


def deliveries_of(s: Stream, case: Case, results) -> list[Delivery]:
    out = []
    reports = set(s.children(case.owner))
    for step, t in enumerate(case.tasks):
        done = results.get(t.id)
        if done is None or done.status != "done":
            continue
        verdicts = tuple(v for v in case.verdicts if v.task_id == t.id and v.message.id > done.id)
        later = next((x.id for x in case.tasks if x.id > done.id), "")
        superseded = "" if any(v.tier == "human" for v in verdicts) else later
        signer = signer_of(case.owner, t.id, done.id, s.snt(case.owner), s.recv(case.owner), reports)
        out.append(Delivery(case.id, t, done, step, signer, verdicts, superseded))
    return out


@dataclass(frozen=True)
class Assertion:
    id: str
    case: str
    verdict: Verdict
    about: tuple[str, ...]
    link: str


def regressions(cases) -> list[Assertion]:
    found = sorted(((v, c.id) for c in cases for v in c.verdicts if v.verdict == "reject" and v.tier == "human"), key=lambda x: x[0].message.id)
    ids = [f"R{k}" for k in range(1, len(found) + 1)]

    def human(v: Verdict) -> tuple[str, ...]:
        return v.links if v.links_tier == "human" else ()

    def about(k: int, seen: frozenset) -> tuple[str, ...]:
        out: list[str] = []
        for x in human(found[k][0]):
            if x == "none":
                continue
            if x.startswith("C"):
                out.append(x)
            elif x[1:].isdigit() and 1 <= int(x[1:]) <= len(found) and x != ids[k] and x not in seen:
                inner = about(int(x[1:]) - 1, seen | {ids[k]})
                out.extend(inner or (x,))
        return tuple(dict.fromkeys(out))

    def link(v: Verdict) -> str:
        if human(v) == ("none",):
            return "none"
        return "confirmed" if human(v) else "unconfirmed" if v.links else ""

    return [Assertion(ids[k], case, v, about(k, frozenset()), link(v)) for k, (v, case) in enumerate(found)]


# ------------------------------------------------------------------------------------------------------------------------ criteria (0a.2)


def number_criteria(versions, basis=None) -> list[Criterion]:
    seen: dict[str, tuple[int, str]] = {}
    added: dict[str, tuple[str, bool]] = {}
    before: set[str] = set()
    for version, defined_by, acceptance in versions:
        for text in acceptance:
            seen.setdefault(text, (version, defined_by))
            if version > 1 and text not in before:
                added[text] = (basis or {}).get(version, ("", False))
        before = set(acceptance)
    latest = set(versions[-1][2]) if versions else set()
    return [Criterion(f"C{k}", text, since, by, text in latest, *added.get(text, ("", False))) for k, (text, (since, by)) in enumerate(seen.items(), start=1)]


def amendment_ids(versions, version: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ids = {c.text: c.id for c in number_criteria(versions)}
    texts = {v: list(a) for v, _, a in versions}
    earlier = [v for v in texts if v < version]
    if version not in texts or not earlier:
        return (), ()
    before, now = texts[max(earlier)], texts[version]
    return tuple(ids[t] for t in now if t not in before), tuple(ids[t] for t in before if t not in now)


def criterion_words(line: str, criteria) -> str | None:
    key = line_key(line)
    for c in criteria:
        text = line_key(c.text)
        if text and key in (line_key(c.id) + text, text + line_key(c.id)):
            return c.id
    return None


def version_in_force(contracts, when):
    if not contracts:
        return None
    dated = [c for c in contracts if when is not None and c.defined is not None and c.defined <= when]
    return max(dated, key=lambda c: c.version) if dated else contracts[0]


# ------------------------------------------------------------------------------------------------------------------------ causes (5)


@dataclass(frozen=True)
class Cause:
    type: str
    rule: str
    detail: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()
    also: tuple[str, ...] = ()
    before_verdict: str = ""


def _named(v: Verdict | None, a: Assertion) -> tuple[str, ...]:
    ids = list(v.confirmed) if v is not None else []
    if a.link == "confirmed":
        ids += [x for x in a.about if x.startswith("C")]
    return tuple(dict.fromkeys(ids))


def _link_note(v: Verdict | None, first: str) -> str:
    if v is None:
        return ""
    human = [m for m in v.link_notes if verdict_tier(m) == "human"]
    naming = [m for m in human if first in link_ids(m)]
    chosen = naming or human
    return chosen[-1].id if chosen else v.message.id


def _judged_result(case: Case, results, before: str) -> str:
    found = case.tasks[0].id
    for t in case.tasks:
        r = results.get(t.id)
        if r is None or r.status != "done":
            continue
        first = min((v.message.id for v in case.verdicts if v.task_id == t.id and v.tier == "human" and v.message.id > r.id), default=None)
        if first is not None and first < before:
            found = max(found, r.id)
    return found


def _carry_over(d: Delivery, case: Case, results):
    task = d.task
    if task.source == "relayed" or BASE_DELIVERED_HEADING in task.body:
        return None
    judged = _judged_result(case, results, task.id)
    shared = set(artifact_paths(d.result.body))
    for r in case.tasks:
        res = results.get(r.id)
        if r.source != "relayed" or not judged < r.id < task.id or res is None or res.status != "done":
            continue
        path = next((p for p in artifact_paths(res.body) if p in shared), None)
        if path is not None:
            return r.id, path
    return None


def _before_verdict(d: Delivery, case: Case, results, v: Verdict | None) -> str:
    if v is None:
        return ""
    found = [
        r.id for r in case.tasks
        if r.source == "relayed" and r.id != d.task.id and (x := results.get(r.id)) is not None and x.status == "done"
        and d.result.id < x.id < v.message.id
    ]
    return found[-1] if found else ""


def cause_of(d: Delivery, case: Case, a: Assertion, carried, answer_removes, results, lasting=LASTING_WORDS, version: int = 0) -> Cause:
    v = d.decisive
    named = _named(v, a)
    matched: list[tuple[str, str, tuple[str, ...]]] = []
    if d.task.source == "relayed":
        matched.append(("relayed task", "relayed-error", (d.task.id,)))
    if (carry := _carry_over(d, case, results)) is not None:
        matched.append(("carry-over", "relayed-carry-over", carry))
    unreadable = bool(named) and carried is None
    if named and carried is not None:
        kept = [c for c in named if c in carried and c not in answer_removes]
        gap = [c for c in named if c not in carried or c in answer_removes]
        if kept:
            matched.append(("link", "reviewer-miss", (_link_note(v, kept[0]), *kept)))
        if gap:
            matched.append(("answer", "contract-gap", (_link_note(v, gap[0]), *gap)))
    if not unreadable and v is not None:
        word = next((w for w in lasting if re.search(rf"\b{re.escape(w)}\b", v.note, re.IGNORECASE)), None)
        if word is not None:
            matched.append(("words", "contract-gap", (word,)))
    before = _before_verdict(d, case, results, v)
    if not matched:
        if unreadable:
            return Cause("untyped", "unreadable", (f"contract v{version} is not stored",), before_verdict=before)
        return Cause("untyped", "none", ("the user said it is no lasting rule",) if a.link == "none" else (), before_verdict=before)
    rule, kind, detail = matched[0]
    also = tuple(dict.fromkeys(k for _, k, _ in matched[1:] if k != kind))
    return Cause(kind, rule, detail, tuple(r for r, _, _ in matched), also, before)


def attribution(c: Cause) -> str:
    return "counted" if c.type in COUNTED_CAUSES else "not its"


# ------------------------------------------------------------------------------------------------------------------------ P3: files not as delivered


def _in_org(path: str) -> bool:
    return bool(path) and "\0" not in path and not path.startswith("/") and all(p not in ("", ".", "..") for p in path.split("/"))


def _checked(s: Stream, result: Msg, path: str) -> str | None:
    """The md5 of the team's version of ``path`` at ``result``. Design 0a.2 (P3's checked version, ``CheckedVersions.at_result``): the blob of
    ``path`` at the first org-git commit that holds the result's sent copy (``org-git-log.txt``), i.e. the newest version (INDEX.txt) committed
    by that commit or before it. When the log does not give it: the latest committed version at or before the result's time (INDEX.txt), else
    the working tree's (the organization's file now); None when neither is known."""
    pos = s.sent_pos.get(result.id)
    if pos is not None:
        at = [(vp, v) for v in s.versions.get(path, []) if (vp := _commit_pos(s, v[1])) is not None and vp >= pos]
        if at:
            return min(at, key=lambda x: x[0])[1][3]
    when = parse_time(result.created) or msg_time(result)
    found = [v for v in s.versions.get(path, []) if when is not None and v[2] is not None and v[2] <= when]
    if found:
        return max(found, key=lambda v: (v[2], v[0]))[3]
    return s.working.get(path)


def findings(s: Stream, cases: list[Case], one_off: list[Case]) -> list[tuple[str, str, int, str, tuple[tuple[str, str], ...]]]:
    """``(kind, task id, written_us, file name, equal)`` per file of the deliverable folder: ``kind`` is what P3's folder rule reports
    (``differs`` or ``relayed``, with the task it names), or ``same`` when the file equals the newest pair's checked version (no finding);
    ``equal`` lists every ``(task id, result id)`` pair of the same file name whose checked version equals the file, newest first (the
    candidates of OQ-2's given delivery, ``_attributed``)."""
    if not s.contracts or not s.files:
        return []
    latest = latest_results(s.recv(ROOT))
    done: dict[str, tuple[Msg, Msg]] = {}
    cands = [(r, t) for c in cases for t in c.tasks if (r := latest.get(t.id)) is not None and r.status == "done"]
    for r, t in sorted(cands, key=lambda x: x[0].id, reverse=True)[:RESULTS_PER_SOURCE]:
        done[r.id] = (r, t)
    offs = [(r, t) for t in s.snt(ROOT) if t.type == "task" and not t.service and (r := latest.get(t.id)) is not None and r.status == "done"]
    for r, t in sorted(offs, key=lambda x: x[0].id, reverse=True)[:RESULTS_PER_SOURCE]:
        done[r.id] = (r, t)
    pairs: list[tuple[Msg, str, Msg]] = []
    for r, t in sorted(done.values(), key=lambda x: x[0].id, reverse=True):
        paths = [p for p in artifact_paths(r.body) if _in_org(p)]
        pairs += [(r, p, t) for p in dict.fromkeys(paths[:PATHS_PER_RESULT])]
    created = [micros(c.created) for c in s.contracts[-1:] if c.created is not None]
    floor = min(created) if created else None
    out = []
    for name, md5, mtime_us in s.files:
        if floor is not None and mtime_us < floor:
            continue
        newest: Msg | None = None
        kind, named = "", ""
        same_name = [p for p in pairs if PurePosixPath(p[1]).name == name]
        equal = tuple(dict.fromkeys((t.id, r.id) for r, path, t in same_name if _checked(s, r, path) == md5))
        for r, path, t in same_name:  # newest first
            checked = _checked(s, r, path)
            if checked is None:  # unknown on both sides: dropped
                continue
            if checked == md5:  # equal to this delivery: fine when it is the newest, else the user's file is that earlier delivery
                kind, named = ("relayed" if newest is not None else "same"), t.id
                break
            newest = newest or t
            if t.source != "relayed":  # a task that is not a relayed rework ends the walk
                kind, named = "differs", newest.id
                break
        else:
            if newest is not None:
                kind, named = "differs", newest.id
        # with no pair of the same name the file is a renamed copy or ``unknown``: neither names a delivery (not counted)
        if kind:
            out.append((kind, named, mtime_us, name, equal))
    return out


# ------------------------------------------------------------------------------------------------------------------------ verifiers' FAILs (0a 5.5)


def _driven(s: Stream, tasks, results, depth: int) -> set[str]:
    out: set[str] = set()
    for t in tasks:
        if not t.revises:
            continue
        prior = results.get(t.revises)
        if t.service and prior is not None and prior.status == "done" and prior.id < t.id:
            out.add(t.id)
        elif depth < 8 and t.sender != ROOT and s.exists(t.sender) and _holds_client_rework(s, t, depth):
            out.add(t.id)
    return out


def _holds_client_rework(s: Stream, task: Msg, depth: int) -> bool:
    mine = [m for m in s.recv(task.sender) if m.type == "task"]
    answers = latest_results(s.snt(task.sender))
    driven = _driven(s, mine, answers, depth + 1)
    return any(m.id in driven and m.id < task.id and (m.id not in answers or answers[m.id].id > task.id) for m in mine)


def rechecks(s: Stream, addr: str) -> tuple[int, int]:
    boss = parent(addr)
    if boss is None or boss == ROOT:
        return 0, 0
    tasks = [m for m in s.recv(addr) if m.type == "task"]
    by_id = {t.id: t for t in tasks}
    results = latest_results(s.snt(addr))
    driven = _driven(s, tasks, results, 0)
    siblings = set(s.children(boss)) - {addr}
    author_reworks = [m for m in s.snt(boss) if m.type == "task" and m.revises and m.to in siblings]
    count, runs = 0, set()
    for r in tasks:
        checked = by_id.get(r.revises or "")
        fail = results.get(checked.id) if checked else None
        if fail is None or fail.status != "done" or r.id in driven:
            continue
        window = [m for m in author_reworks if fail.id < m.id < r.id]
        if not window:
            continue
        count += 1
        start, end = msg_time(fail), msg_time(r)
        if start is None or end is None:
            continue
        for author in {m.to for m in window}:
            runs |= {(author, w) for x in s.logs.get(author, []) if (w := stamp_of(x)) is not None and start <= w < end}
    return count, len(runs)


# ------------------------------------------------------------------------------------------------------------------------ held tasks (4.5)


def moved_past(task: Msg, blocked: Msg, received) -> bool:
    mine = [t for t in received if t.type == "task" and t.sender == task.sender]
    chain = _chain(task, received)
    later = any(t.id > task.id and (t.revises == task.id or (task.revises is not None and t.revises == task.revises)) for t in mine)
    verdict = any(m.type == "note" and m.feedback and m.sender == task.sender and m.reply_to in chain and m.id > blocked.id for m in received)
    return later or verdict


def _chain(task: Msg, received) -> set[str]:
    mine = [t for t in received if t.type == "task" and t.sender == task.sender]
    chain = {task.id}
    grown = True
    while grown:
        more = {t.id for t in mine if t.revises in chain} | {t.revises for t in mine if t.id in chain and t.revises}
        grown = not more <= chain
        chain |= more  # type: ignore[arg-type]
    return chain


def moved_past_section(s: Stream) -> list[dict]:
    out = []
    for addr in s.agents:
        latest = latest_results(s.snt(addr))
        received = s.recv(addr)
        blocked = [t for t in received if t.type == "task" and (r := latest.get(t.id)) is not None and r.status == "blocked"]
        if not blocked:
            continue
        held = [t for t in blocked if not moved_past(t, latest[t.id], received)]
        rows = []
        for t in sorted(held, key=lambda t: latest[t.id].id):
            b = latest[t.id]
            chain = _chain(t, received)
            since = sum(1 for x in received if x.type == "task" and x.sender == t.sender and x.id > b.id and x.id not in chain)
            rows.append({
                "id": t.id, "sender": t.sender, "title": t.title if t.sender == ROOT else None, "blocked": utc(msg_time(b)),
                "left_blocked": since > 0, "sent_since": since,
            })
        if not any(r["left_blocked"] for r in rows):
            continue
        budget = sum(m.budget for m in received) - sum(m.budget for m in s.snt(addr)) - len(s.logs.get(addr, []))
        out.append({"addr": addr, "held": budget, "held_error": "", "error": "", "tasks": rows})
    return out


# ------------------------------------------------------------------------------------------------------------------------ thresholds (6)


def thresholds(s: Stream) -> tuple[dict, list[str]]:
    t = dict(DEFAULTS)
    t["source"] = "defaults"
    if s.org_error:
        return t, ["ORG.md cannot be read (its settings block does not parse): the default thresholds are used."]
    config = s.org_config or {}
    if "quality" not in config:
        return t, []
    raw = config["quality"]
    if not isinstance(raw, dict):
        return t, ["quality in ORG.md is not a mapping: the defaults are used."]
    notes: list[str] = []
    applied = False

    def count(v):
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            n = v
        elif isinstance(v, float):
            n = int(v) if v.is_integer() else None
        elif isinstance(v, str) and re.fullmatch(r"[0-9]+", v):
            n = int(v)
        else:
            n = None
        return n if n is not None and n >= 1 else None

    def counted(key, default, what, ceiling=None):
        nonlocal applied
        if key not in raw:
            return default
        v = count(raw[key])
        if v is None or (ceiling is not None and v > ceiling):
            notes.append(f"quality.{key} in ORG.md is not {what}: the default {default} is used.")
            return default
        applied = True
        return v

    t["min_judged"] = counted("min_judged", 3, "a whole number of at least 1")
    w = counted("repeat_window", 3, "a whole number of at least 1")
    t["repeat_window"] = w
    df = min(2, w)
    if "repeat_failures" not in raw and w < 2:
        notes.append(f"quality.repeat_failures: the default 2 is above repeat_window {w}, so {df} is used.")
    t["repeat_failures"] = counted("repeat_failures", df, f"a whole number from 1 to {w}", ceiling=w)
    if "cost_ratio" in raw:
        v = raw["cost_ratio"]
        text = None
        if not isinstance(v, bool) and isinstance(v, (int, float)):
            text = str(v)
        elif isinstance(v, str) and re.fullmatch(r"[0-9]+(\.[0-9]+)?", v):
            text = v
        if text is None or Fraction(text) <= 0:
            notes.append("quality.cost_ratio in ORG.md is not a number above 0: the default 1.25 is used.")
        else:
            t["cost_ratio"], applied = text, True
    keys = ("min_judged", "repeat_window", "repeat_failures", "cost_ratio")
    notes += [f"quality.{k} in ORG.md is not a threshold: ignored (the thresholds are {', '.join(keys)})." for k in raw if str(k) not in keys]
    t["source"] = "ORG.md" if applied else "defaults"
    return t, notes


# ------------------------------------------------------------------------------------------------------------------------ the record (9.4)


@dataclass
class Rec:
    owner: str
    service: str
    client: str
    client_kind: str
    budget: int | None
    cases: list[Case]
    deliveries: list[Delivery]
    assertions: list[Assertion]
    escapes: list[tuple[Delivery, Cause]]
    timeline: list[dict]
    given: list[dict] = field(default_factory=list)  # OQ-2's given-delivery choices (``_attributed``), outside 9.4's schema


def _attributed(deliveries: list[Delivery], found) -> tuple[list[Delivery], list[dict]]:
    """The deliveries with P3's findings applied (``differs``: not as delivered, edited at the file's write time) and OQ-2's given delivery
    marked, and the record of every given-delivery choice.

    OQ-2's given delivery (design 3 and 4.3, as the manager ruled it on 2026-10-25, ``manager-decision-selfcheck.md`` item 2): the delivery
    whose checked artifact equals the user's file; when several deliveries of the case qualify, the one that carries a human-tier verdict
    (the newest result among them); when none carries one, the latest: the one P3's ``relayed`` finding names, or, with no finding, the case's
    latest delivery. The product takes P3's newest-first pair alone; each choice records what P3 names, so a difference (F-G0-1) is shown."""
    writes: dict[str, list[int]] = {}
    given: set[str] = set()
    record: list[dict] = []
    by_task = {d.task.id: d for d in deliveries}
    for kind, task, written, name, equal in found:
        if kind == "differs":
            writes.setdefault(task, []).append(written)
            continue
        named = by_task.get(task)
        if named is None:
            continue
        mine = [d for d in deliveries if d.case == named.case]
        cands = [by_task[t] for t, _ in equal if t in by_task and by_task[t].case == named.case]
        human = [d for d in cands if any(v.tier == "human" for v in d.verdicts)]
        if human:
            chosen, by = max(human, key=lambda d: d.result.id), "human verdict"
        elif kind == "relayed":
            chosen, by = named, "P3's relayed finding"
        else:
            chosen, by = mine[-1], "the case's latest delivery"
        p3 = named if kind == "relayed" else mine[-1]
        given.add(chosen.task.id)
        record.append({"case": named.case, "file": name, "kind": kind, "candidates": [d.task.id for d in cands],
                       "results": [d.result.id for d in cands], "given": chosen.task.id, "by": by, "p3_names": p3.task.id,
                       "differs": chosen.task.id != p3.task.id})
    out = []
    for d in deliveries:
        if d.task.id in writes:
            d = replace(d, edited=True, edited_at=min((w for w in writes[d.task.id] if w > 0), default=0))
        if d.task.id in given:
            d = replace(d, given=True)
        out.append(d)
    return out, record


def judged_cases(r: Rec) -> list[Case]:
    latest: dict[str, str] = {}
    for d in r.deliveries:
        if d.judged:
            latest[d.case] = max(latest.get(d.case, ""), *(v.message.id for v in d.counted))
    by_id = {c.id: c for c in r.cases}
    return [by_id[c] for c in sorted(latest, key=latest.__getitem__) if c in by_id]


def _num(x: str) -> tuple[int, int, str]:
    return (0 if x.startswith("R") else 1, int(x[1:]) if x[1:].isdigit() else 0, x)


def _rejections(r: Rec, cases) -> list:
    wanted = {c.id for c in cases}
    by_v = {a.verdict.message.id: a for a in r.assertions}
    found = [(d.case, v, a.id, a.about) for d in r.deliveries if d.case in wanted for v in d.counted
             if v.verdict == "reject" and (a := by_v.get(v.message.id)) is not None]
    return sorted(found, key=lambda x: x[1].message.id)


def _reading(v: Verdict) -> tuple[str, ...]:
    if v.links_tier == "human":
        confirmed = set(v.links)
        return tuple(x for x in link_ids(v.message) if x != "none" and x not in confirmed)
    return tuple(x for x in v.links if x != "none")


def _not_counted(r: Rec, cases) -> dict:
    found: dict[str, tuple[str, ...]] = {}
    for _, v, a, _ in _rejections(r, cases):
        reading = _reading(v)
        if reading:
            found.setdefault(a, reading)
    return {k: list(v) for k, v in sorted(found.items(), key=lambda x: _num(x[0]))}


def repeat_alarm(r: Rec, t: dict) -> dict:
    judged = judged_cases(r)
    base = {"state": "", "judged": len(judged), "window": [], "subjects": {}, "fired": [], "not_counted": {}}
    if not r.service:
        return {**base, "state": "does not apply"}
    if len(judged) < t["min_judged"]:
        return {**base, "state": "n/a", "not_counted": _not_counted(r, judged)}
    window = judged[-t["repeat_window"]:]
    in_case: dict[str, set[str]] = {c.id: set() for c in window}
    for case, v, a, about in _rejections(r, window):
        in_case[case] |= {a, *v.confirmed, *about}
        if v.links_tier == "human":
            in_case[case] |= {x for x in v.links if x[:1] == "R" and x[1:].isdigit()}
    count = Counter(x for xs in in_case.values() for x in xs)
    subjects = sorted(count.items(), key=lambda x: _num(x[0]))
    fired = [x for x, n in subjects if n >= t["repeat_failures"]]
    return {**base, "state": "fires" if fired else "no", "window": list(in_case), "subjects": dict(subjects), "fired": fired,
            "not_counted": _not_counted(r, window)}


def approved_of(r: Rec, c: Case) -> int:
    return user_approved(c, r.budget if r.service else c.tasks[0].budget)  # type: ignore[arg-type]


def cost_alarm(r: Rec, t: dict) -> dict:
    judged = len(judged_cases(r))
    compared, skipped = [], []
    for c in r.cases:
        a = approved_of(r, c)
        if c.runs_unknown:
            skipped.append({"case": c.id, "reason": "runs not counted"})
        elif a <= 0:
            skipped.append({"case": c.id, "reason": "budget 0"})
        else:
            compared.append((c, a))
    if judged < t["min_judged"] or not compared:
        return {"state": "n/a", "judged": judged, "compared": len(compared), "cases": [], "skipped": skipped}
    ratio = Fraction(t["cost_ratio"])
    fired = [
        {"case": c.id, "user_cost": user_cost(c), "user_approved": a, "ratio": two_decimals(Fraction(user_cost(c), a)), "relayed_runs": c.relayed_runs,
         "total": case_spend(c)}
        for c, a in compared if Fraction(user_cost(c)) > ratio * a
    ]
    return {"state": "fires" if fired else "no", "judged": judged, "compared": len(compared), "cases": fired, "skipped": skipped}


def _criteria_basis(s: Stream):
    stored = [(c.version, c.defined_by, c.acceptance) for c in s.contracts]
    basis = {c.version: (c.answers, c.initiated == "user") for c in s.contracts}
    return stored, number_criteria(stored, basis)


def confirmed_criteria(cases, criteria) -> set[str]:
    by = {c.id: c for c in criteria}

    def counts(v: Verdict, x: str) -> bool:
        c = by.get(x)
        return c is None or not (c.user or (c.answers and c.answers != v.message.id))

    return {x for c in cases for v in c.verdicts for x in v.confirmed if counts(v, x)}


def contract_marks(s: Stream, cases) -> list[dict]:
    stored, numbered = _criteria_basis(s)
    ids = {c.text: c.id for c in numbered}
    confirmed = confirmed_criteria(cases, numbered)
    rejections = {a.verdict.message.id: a.id for a in regressions(cases)}
    links: dict[str, list[tuple[str, str]]] = {}
    for case in cases:
        for v in case.verdicts:
            for note in v.link_notes:
                if verdict_tier(note) == "human":
                    for x in link_ids(note):
                        links.setdefault(x, []).append((v.message.id, note.id))
    for f in links.values():
        f.sort(key=lambda p: p[1])
    out = []
    for pos, c in enumerate(s.contracts):
        mark = {"kind": "contract", "when": utc(c.defined), "_when": c.defined, "version": c.version, "by": c.defined_by}
        if pos == 0:
            out.append({**mark, "adds": [ids[t] for t in c.acceptance], "removes": [], "basis": "first", "answers": None, "confirmed": [], "not_confirmed": []})
            continue
        added, removed = amendment_ids(stored, c.version)
        if c.answers:
            basis, named = "answers", added or removed
            parts = [(x, next((ln for rej, ln in links.get(x, []) if rej == c.answers), "")) for x in named]
        elif c.initiated == "user":
            basis, parts = "user", []
        elif c.defined_by in ("", ROOT):
            basis = "legacy"
            parts = [(x, links[x][0][1] if x in confirmed and links.get(x) else "") for x in added]
        else:
            basis, parts = "agent", []
        out.append({
            **mark, "adds": list(added), "removes": list(removed), "basis": basis,
            "answers": rejections.get(c.answers, c.answers) if basis == "answers" else None,
            "confirmed": [{"id": i, "link": ln} for i, ln in parts if ln], "not_confirmed": [i for i, ln in parts if not ln],
        })
    return out


def playbook_marks(s: Stream, owner: str, cases) -> list[dict]:
    _, numbered = _criteria_basis(s)
    by_id = {c.id: c for c in numbered}
    notes = {n.id: n for c in cases for v in c.verdicts for n in v.link_notes}
    client = parent(owner) or ROOT
    out = []
    for pos, p in enumerate(s.playbooks):
        before = s.playbooks[pos - 1].body if pos else ""
        changed, removed = changed_lines(before, p.body), changed_lines(p.body, before)
        shown = [x for x in p.evidence if _EVIDENCE_ID.fullmatch(x)]
        cited: dict[str, Criterion] = {}
        for x in p.evidence:
            note = notes.get(x)
            if _CRITERION.fullmatch(x) and x in by_id:
                cited.setdefault(x, by_id[x])
            elif note is not None and verdict_tier(note) == "human":
                cited.update({k: by_id[k] for k in link_ids(note) if k in by_id})
        own = [criterion_words(line, list(cited.values())) is not None for line in changed]
        tagged = [_TAG.search(line) is not None for line in changed]
        basis = p.admitted if p.admitted in ("c", "b", "first", "restore") else "client" if p.by == client else "legacy"
        out.append({
            "kind": "playbook", "when": utc(p.revised), "_when": p.revised, "version": p.version, "by": p.by, "basis": basis,
            "restores": next((q.version for q in reversed(s.playbooks[:pos]) if q.body == p.body), None) if basis == "restore" else None,
            "evidence": shown, "evidence_other": len(p.evidence) - len(shown), "changed": len(changed), "removed": len(removed),
            "own_words": sum(own) if basis == "c" else None, "beyond": len(own) - sum(own) if basis == "c" else None,
            "tagged": sum(tagged) if basis == "b" else None, "untagged": len(tagged) - sum(tagged) if basis == "b" else None,
            "cited": [{"id": c.id, "text": c.text} for c in cited.values()],
            "lines": [{"text": clip_line(line, LINE_CLIP), "own_words": o} for line, o in zip(changed[:LINES_LISTED], own)],
            "lines_more": max(0, len(changed) - LINES_LISTED), "agent_written": True,
        })
    return out


def top_up_marks(cases) -> list[dict]:
    return [{"kind": "top-up", "when": utc(stamp_of(i)), "_when": stamp_of(i), "case": c.id, "id": i, "source": k, "amount": a}
            for c in cases for i, k, a in c.top_ups]


def history_of(s: Stream, team: set[str]) -> tuple[dict, bool]:
    """``(history, marks_known)`` from org-git-log.txt: ``known`` when the log has commits; ``truncated`` when the AGENT.md/ORG.md paths changed in
    40 or more commits (the product's list is full); the charter and model marks are derivable only when no path changed after its first commit."""
    if not s.git:
        return {"known": False, "truncated": False, "skipped": 0}, True
    watched = {f"{a}/AGENT.md" for a in s.agents} | {"ORG.md"}
    touching = [(sha, [p for p in paths if p in watched or (p.startswith("...") and (p.endswith("/AGENT.md") or p.endswith("ORG.md")))])
                for sha, _, paths in s.git]
    touching = [(sha, ps) for sha, ps in touching if ps]
    per_path = Counter(p for _, ps in touching for p in ps)
    marks_known = all(n <= 1 for p, n in per_path.items() if not p.startswith("...")) and not any(p.startswith("...") for p in per_path)
    return {"known": True, "truncated": len(touching) >= HISTORY_LIMIT, "skipped": 0}, marks_known


def build_record(s: Stream, client: str, cases: list[Case], service: str, owner: str, found) -> Rec:
    results = latest_results(s.recv(client))
    deliveries, given = _attributed([d for c in cases for d in deliveries_of(s, c, results)], found)
    assertions = regressions(cases) if service else []
    by_case = {c.id: c for c in cases}
    by_v = {a.verdict.message.id: a for a in assertions}
    if service:
        stored, numbered = _criteria_basis(s)
        ids = {c.text: c.id for c in numbered}
    escapes = []
    for d in deliveries:
        v = d.decisive
        if not d.escape or v is None:
            continue
        a = by_v.get(v.message.id) or Assertion("", d.case, v, (), "")
        case = by_case[d.case]
        if not service:
            cause = cause_of(d, case, a, frozenset(), (), results)
        else:
            if d.task.contract is not None:
                number = d.task.contract
            else:
                chosen = version_in_force(s.contracts, msg_time(d.task))
                number = chosen.version if chosen is not None else 0
            c = next((x for x in s.contracts if x.version == number), None)
            carried = None if c is None else frozenset(ids[t] for t in c.acceptance)
            ans = next((x for x in s.contracts if x.answers == v.message.id), None)
            removes = () if ans is None else amendment_ids(stored, ans.version)[1]
            cause = cause_of(d, case, a, carried, removes, results, version=number)
        escapes.append((d, cause))
    escapes.sort(key=lambda p: p[0].decisive.message.id if p[0].decisive else "")
    marks = (contract_marks(s, cases) + playbook_marks(s, owner, cases) if service else []) + top_up_marks(cases)
    marks.sort(key=lambda m: (m["_when"] or EARLIEST, KIND_RANK[m["kind"]]))
    return Rec(owner, service, client, "human" if client == ROOT else "agent", s.contracts[-1].budget if service else None, cases, deliveries,
               assertions, escapes, marks, given)


def _first(r: Rec, case: Case) -> dict | None:
    mine = [d for d in r.deliveries if d.case == case.id]
    if not mine:
        return None
    first = min(mine, key=lambda d: d.step)
    later = next((t for t in case.tasks if t.id == first.superseded), None) if first.superseded else None
    return {"task": first.task.id, "outcome": first.outcome, "superseded_by": later.id if later else None,
            "superseded_source": None if later is None else (later.source or "unrecorded")}


def _given(case: Case, ds) -> Delivery | None:
    mine = [d for d in ds if d.case == case.id]
    return next((d for d in mine if d.given), mine[-1] if mine else None)


def _unjudged(cases, ds, relayed_only=False) -> list[str]:
    out = []
    for c in cases:
        d = _given(c, ds) if c.state == "done" else None
        if d is None or any(v.tier == "human" for v in d.verdicts):
            continue
        if not relayed_only or d.verdicts:
            out.append(c.id)
    return out


def record_data(s: Stream, r: Rec, t: dict, not_derived: list[str], path: str, marks_known: bool, history: dict) -> dict:
    ds = r.deliveries
    cases_out = []
    firsts = []
    for k, c in enumerate(r.cases):
        f = _first(r, c)
        firsts.append((c, f, next((d for d in ds if d.case == c.id and f and d.task.id == f["task"]), None)))
        counted = not c.runs_unknown
        a = approved_of(r, c)
        if c.state == "open":
            not_derived.append(f"{path}.cases.{k}.stalled")
        cases_out.append({
            "id": c.id, "title": c.title, "assignee": c.owner, "state": c.state, "stalled": None if c.state == "open" else False,
            "tasks": len(c.tasks), "budget": r.budget if r.service else c.tasks[0].budget, "user_approved": a,
            "runs": c.runs if counted else None, "credited": c.credited if counted else None, "relayed_runs": c.relayed_runs if counted else None,
            "spend": case_spend(c) if counted else None, "user_cost": user_cost(c) if counted else None,
            "ratio": two_decimals(Fraction(user_cost(c), a)) if counted and a > 0 else None, "cut": c.cut, "runs_unknown": c.runs_unknown,
            "top_ups": [{"id": i, "source": kd, "amount": am} for i, kd, am in c.top_ups], "first": f,
        })
    outcomes = Counter(f["outcome"] if f else "never" for _, f, _ in firsts)
    unseen = []
    for c in r.cases:
        g = next((d for d in ds if d.case == c.id and d.given), None)
        if g is not None and any(d.case == c.id and d.step > g.step and d.task.source == "relayed" for d in ds):
            unseen.append(c.id)
    on_one = {v.message.id for d in ds for v in d.verdicts}
    by_v = {a.verdict.message.id: a.id for a in r.assertions}
    owner_of = {c.id: c.owner for c in r.cases}
    signers = sorted({d.signer for d in ds if d.signer != owner_of.get(d.case)})
    verifiers = []
    for addr in signers:
        causes = [cause for d, cause in r.escapes if d.signer == addr]
        counted_c = [c.type for c in causes if attribution(c) == "counted"]
        not_its = [c.type for c in causes if attribution(c) == "not its"]
        judged = sum(1 for d in ds if d.signer == addr and d.judged)
        rc, rw = rechecks(s, addr)
        verifiers.append({
            "addr": addr, "judged": judged,
            "escapes": {"counted": {k: counted_c.count(k) for k in COUNTED_CAUSES if k in counted_c},
                        "not_its": {k: not_its.count(k) for k in NOT_ITS_CAUSES if k in not_its}},
            "pass_precision": [judged - len(counted_c), judged], "rechecks": rc, "rework_runs": rw, "fails_error": "",
        })
    timeline = [{k: v for k, v in m.items() if k != "_when"} for m in r.timeline]
    if not marks_known:
        not_derived.append(f"{path}.timeline")
    return {
        "owner": r.owner, "service": r.service, "client": r.client, "client_kind": r.client_kind, "unit": "case", "error": "", "files_error": "",
        "stalled_error": "", "contract": s.contracts[-1].version if r.service else 0,
        "playbook": (s.playbooks[-1].version if s.playbooks else 0) if r.service else 0, "budget": r.budget, "cases": cases_out,
        "first_deliveries": {
            "accepted": outcomes["accepted"], "rejected": outcomes["rejected"], "no_verdict": outcomes["none"],
            "superseded": sum(1 for _, f, _ in firsts if f and f["outcome"] == "none" and f["superseded_by"] is not None),
            "neither": outcomes["neither"], "never_delivered": outcomes["never"],
        },
        "deliveries": {
            "total": len(ds), "judged": sum(1 for d in ds if d.judged), "unjudged_cases": _unjudged(r.cases, ds),
            "relayed_only": _unjudged(r.cases, ds, relayed_only=True), "unseen_relayed": unseen,
            "not_as_delivered": [{"case": d.case, "task": d.task.id} for d in ds if d.edited],
            "neither": [{"case": d.case, "task": d.task.id} for d in ds if d.outcome == "neither"],
            "legacy_verdicts": sum(1 for c in r.cases for v in c.verdicts if v.tier == "human" and v.message.source is None),
            "not_on_a_delivery": [v.message.id for c in r.cases for v in c.verdicts if v.tier == "human" and v.message.id not in on_one],
        },
        "escapes": [{
            "assertion": by_v.get(d.decisive.message.id) if d.decisive else None, "case": d.case, "task": d.task.id,
            "verdict": d.decisive.message.id if d.decisive else "", "signer": d.signer, "cause": c.type, "rule": c.rule, "rules": list(c.rules),
            "detail": list(c.detail), "also": list(c.also), "before_verdict": c.before_verdict, "attribution": attribution(c),
            "class": "off_spec" if c.type == "reviewer-miss" else None,
        } for d, c in r.escapes],
        "verifiers": verifiers, "alarms": {"repeat": repeat_alarm(r, t), "cost": cost_alarm(r, t)}, "timeline": timeline, "history": history,
    }


def _script() -> dict:
    p = Path(__file__).resolve()
    return {"name": p.name, "md5": hashlib.md5(p.read_bytes()).hexdigest()}


def rederive(streamdir) -> dict:
    """The re-derived ``quality_data`` of one stream evidence dir, plus ``source_files``, ``script`` and ``not_derived`` (paths)."""
    s = load_stream(Path(streamdir))
    t, notes = thresholds(s)
    not_derived: list[str] = []
    services = []
    cases: list[Case] = []
    if s.contracts and s.owner:
        client = parent(s.owner) or ROOT
        since = s.contracts[-1].created
        mine = sorted((m for m in s.snt(client) if m.type == "task" and m.to == s.owner and m.service == s.service
                       and (since is None or (msg_time(m) or since) >= since)), key=lambda m: m.id)
        cases = build_cases(s, client, mine, s.service, s.contracts[-1].budget)
    off_tasks = sorted((m for m in s.snt(ROOT) if m.type == "task" and not m.service), key=lambda m: m.id)
    off_cases = build_cases(s, ROOT, off_tasks, "", 0)
    found = findings(s, cases, off_cases)
    nested = []
    given: list[dict] = []
    if s.contracts and s.owner:
        team = set(s.subtree(s.owner))
        history, marks_known = history_of(s, team)
        rec = build_record(s, parent(s.owner) or ROOT, cases, s.service, s.owner, found)
        given += rec.given
        if rec.client_kind == "human":
            services.append(record_data(s, rec, t, not_derived, f"services.{len(services)}", marks_known, history))
        else:
            nested.append({"owner": rec.owner, "service": rec.service, "client": rec.client, "cases": len(rec.cases), "delivered": len(rec.deliveries),
                           "agent_verdicts": sum(len(c.verdicts) for c in rec.cases), "error": ""})
    one_off = None
    if off_cases:
        team = {a for c in off_cases for a in s.subtree(c.owner)}
        history, marks_known = history_of(s, team)
        rec = build_record(s, ROOT, off_cases, "", "", found)
        given += [g for g in rec.given if g not in given]
        one_off = record_data(s, rec, t, not_derived, "one_off", marks_known, history)
    out = {
        "schema": 1, "thresholds": t, "notes": notes, "services": services, "one_off": one_off, "nested": nested,
        "moved_past": moved_past_section(s),
    }
    out["source_files"] = sorted(s.read)
    out["script"] = _script()
    out["not_derived"] = sorted(set(not_derived))
    out["given_deliveries"] = given  # outside 9.4's schema: OQ-2's choices, with what P3's newest-first pair names (F-G0-1)
    return out


EXTRA_KEYS = ("source_files", "script", "not_derived", "given_deliveries")  # the re-derivation's own keys, never compared


def f_g0_1_lines(rederived: dict) -> list[str]:
    """One line per case whose given delivery (OQ-2, the manager's rule) is not the one P3's newest-first pair names: F-G0-1 (a product
    deviation, manager-decision-selfcheck.md item 2), with the files that show it."""
    out = []
    for g in rederived.get("given_deliveries", []):
        if g.get("differs"):
            files = ", ".join([f"msgs/read|inbox/{r}.md" for r in g["results"]] + ["memos/versions/INDEX.txt", f"memos/{g['file']}", "org-git-log.txt"])
            out.append(f"F-G0-1 case {g['case']}: {g['file']} equals the checked artifact of the deliveries {', '.join(g['candidates'])}; the "
                       f"design's given delivery is {g['given']} ({g['by']}), P3's newest-first pair names {g['p3_names']}: the product's "
                       f"unjudged_cases, relayed_only and unseen_relayed of this case follow P3's pair (files: {files})")
    return out


# ------------------------------------------------------------------------------------------------------------------------ compare and self-check


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True, indent=2) + "\n"


def _flat(value, path: str, out: dict) -> None:
    if isinstance(value, dict) and value:
        for k, v in value.items():
            _flat(v, f"{path}.{k}" if path else str(k), out)
    elif isinstance(value, list) and value:
        for k, v in enumerate(value):
            _flat(v, f"{path}.{k}" if path else str(k), out)
    else:
        out[path] = value


def compare(product: dict, rederived: dict) -> list[str]:
    nd = list(rederived.get("not_derived", []))
    mine = {k: v for k, v in rederived.items() if k not in EXTRA_KEYS}
    theirs = {k: v for k, v in product.items() if k not in EXTRA_KEYS}
    a: dict = {}
    b: dict = {}
    _flat(theirs, "", a)
    _flat(mine, "", b)
    lines = [f"NOT DERIVED {p}" for p in nd]

    def skipped(p: str) -> bool:
        return any(p == x or p.startswith(x + ".") for x in nd)

    compared = mism = 0
    for p in sorted(set(a) | set(b)):
        if skipped(p):
            continue
        compared += 1
        va, vb = a.get(p, "<absent>"), b.get(p, "<absent>")
        if json.dumps(va, sort_keys=True) != json.dumps(vb, sort_keys=True):
            mism += 1
            lines.append(f"MISMATCH {p}: product={json.dumps(va)} rederived={json.dumps(vb)}")
    lines += f_g0_1_lines(rederived)
    lines.append(f"compared {compared} keys, {mism} mismatches")
    return lines


def _parts(key: str) -> list[str]:
    """The parts of a dotted key; ``[k=v&k2=v2]`` (a list element selected by its fields) may hold dots; ``#`` is the length."""
    out, cur, depth = [], "", 0
    for ch in key:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "." and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def get_path(data, key: str):
    cur = data
    for part in _parts(key):
        if part == "#":
            cur = len(cur)
        elif part.startswith("[") and part.endswith("]"):
            want = dict(x.split("=", 1) for x in part[1:-1].split("&"))
            hits = [e for e in cur if isinstance(e, dict) and all(str(e.get(k)) == v for k, v in want.items())]
            if len(hits) != 1:
                raise KeyError(f"{key}: {len(hits)} elements match {part}")
            cur = hits[0]
        elif isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(key)
    return cur


def _crosscheck(stream: Path, data: dict) -> list[str]:
    f = stream / "final-services-progress-status-health.txt"
    if not f.is_file() or not data["services"]:
        return []
    lines = []
    cases = data["services"][0]["cases"]
    seen = set()
    for line in f.read_text(encoding="utf-8").splitlines():
        m = re.search(r"case total: (\d+) runs used.*\(task (\S+)\)", line)
        if not m:
            continue
        task = m.group(2)
        rec = load_stream_cases_index(stream).get(task)
        case = next((c for c in cases if c["id"] == rec), None) if rec else None
        if case is None or case["id"] in seen:
            continue
        seen.add(case["id"])
        ok = case["spend"] == int(m.group(1))
        lines.append(f"CROSSCHECK {'agrees' if ok else 'DIFFERS'}: case {case['id']} recorded case total {m.group(1)} runs used; re-derived spend {case['spend']}")
    return lines


_INDEX_CACHE: dict[Path, dict[str, str]] = {}


def load_stream_cases_index(stream: Path) -> dict[str, str]:
    """task id -> case id of the stream's service cases (for the cross-check)."""
    if stream not in _INDEX_CACHE:
        s = load_stream(stream)
        client = parent(s.owner) or ROOT
        mine = sorted((m for m in s.snt(client) if m.type == "task" and m.to == s.owner and m.service == s.service), key=lambda m: m.id)
        idx = {}
        for c in build_cases(s, client, mine, s.service, s.contracts[-1].budget if s.contracts else 0):
            for t in c.tasks:
                idx[t.id] = c.id
        _INDEX_CACHE[stream] = idx
    return _INDEX_CACHE[stream]


def selfcheck(e7ev: Path, out: Path) -> int:
    expected = json.loads((Path(__file__).resolve().parent / "selfcheck" / "e7-expected-rederive.json").read_text())
    k = n = 0
    printed: list[str] = []
    for label in ("s1", "s2", "s3"):
        data = rederive(e7ev / label)
        d = out / f"e7-{label}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "rederived.json").write_text(_dump(data))
        lines = []
        for e in (x for x in expected if x["stream"] == label):
            n += 1
            try:
                got = get_path(data, e["key"])
            except (KeyError, IndexError, ValueError):
                got = "<absent>"
            if json.dumps(got, sort_keys=True) == json.dumps(e["expected"], sort_keys=True):
                k += 1
                lines.append(f"OK {label} {e['key']}")
            else:
                lines.append(f"MISMATCH {label}:{e['key']} expected={json.dumps(e['expected'])} rederived={json.dumps(got)} ({e['source']})")
        lines += [f"NOT DERIVED {label}:{p}" for p in data["not_derived"]]
        lines += [f"DECLARED {label}: {ln}" for ln in f_g0_1_lines(data)]
        lines += _crosscheck(e7ev / label, data)
        (d / "rederive-selfcheck.txt").write_text("\n".join(lines) + "\n")
        printed += lines
    for ln in printed:
        print(ln)
    print(f"selfcheck rederive: {k} of {n} OK")
    return 0 if k == n else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("streamdir", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--compare")
    ap.add_argument("--selfcheck")
    args = ap.parse_args(argv)
    out = Path(args.out)
    try:
        if args.selfcheck:
            return selfcheck(Path(args.selfcheck), out)
        if not args.streamdir:
            ap.error("a stream dir is required")
        data = rederive(Path(args.streamdir))
        product = None
        if args.compare:
            try:
                product = json.loads(Path(args.compare).read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise Unreadable(f"{args.compare}: {exc}") from exc
        out.mkdir(parents=True, exist_ok=True)
        (out / "rederived.json").write_text(_dump(data))
        if product is not None:
            (out / "mismatches.txt").write_text("\n".join(compare(product, data)) + "\n")
        return 0
    except Unreadable as exc:
        print(f"unreadable input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
