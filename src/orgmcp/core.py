"""Filesystem model of an agent organization.

Invariants (everything else is built on these):

* An agent is a directory containing AGENT.md. Its address is its path relative to the org
  root (e.g. ``ceo/cto``). The org root itself is ``root``: the human.
* Messages are immutable markdown files with YAML frontmatter. They are created atomically
  (temp file + rename) in the recipient's ``inbox/`` with a copy in the sender's ``sent/``.
* Received messages move ``inbox/ -> inflight/`` (current run) ``-> read/`` (processed).
* Single writer: an agent writes only inside its own directory. The one exception is a
  direct report's AGENT.md, which the parent owns.
* State is derived, never stored:
  - a task is open until its assignee has sent a result with ``reply_to`` = task id;
  - a task's outcome is its *latest* result: ``blocked`` may be superseded by a later result (``supersedes`` = the
    id of the one it replaces), ``done`` and ``failed`` are final;
  - budget = budget received - budget handed down - runs consumed (files in ``runs/``). Budget flows down with tasks
    and grants; it comes back up only as the ``budget`` of a final result (``done``/``failed`` of an agent with nothing
    else open) or of a note to the parent. Every transfer is one message, charged to the sender and credited to the
    recipient, so the total never changes.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import unicodedata
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import yaml

from . import telemetry, templates

# The shared vocabulary lives in orgmcp.kernel; these names stay importable from here (`core.Message is kernel.Message`).
from .kernel import (  # noqa: F401 - re-exports
    BOXES,
    MESSAGE_TYPES,
    NAME_RE,
    RENDER_BODY_CHARS,
    RESERVED,
    RESULT_STATUSES,
    ROOT,
    RUNTIME,
    RUNTIME_NAMES,
    Message,
    OrgError,
    child_addr as _child_addr,
    depth as _depth,
    inside as _inside,
    join_frontmatter,
    latest_results,
    norm as _norm,
    parent as _parent,
    split_frontmatter,
    visible as _visible,
    word_count,
)

DEFAULT_MODEL = "claude-sonnet-5.5"  # the model every agent runs on unless its charter or the org config names another
DEFAULT_CONFIG = {
    "max_depth": 4,  # deepest allowed agent (ceo = 1)
    "max_hops": 40,  # longest message chain before sends are refused (loop guard)
    "max_parallel": 3,  # concurrent agent runs
    "max_failures": 3,  # consecutive failed runs before an agent is paused
    "run_timeout": 1800,  # seconds per run
    "stall_after": 600,  # seconds of silence on an open task before the next step of the stall ladder
    "review_every_runs": 25,  # org-wide runs between health reviews (or review_every_seconds, whichever first)
    "review_every_seconds": 86400,
    "poll_seconds": 2,
    "until_done_grace_seconds": 300,  # an until-done scheduler that finds nothing can progress without the user exits after this
    "default_budget": 10,  # runs given with a task when none is specified
    "memory_max_words": 800,  # cap on an agent's MEMORY.md; writes that exceed it are refused
    "playbook_max_words": 1000,  # cap on a service playbook (revise_playbook refuses longer ones)
    "default_model": DEFAULT_MODEL,  # kiro model for agents whose charter names none; null/missing = DEFAULT_MODEL
    "max_message_chars": 20000,  # longest message body send/delegate/report accept; detail goes in a file
    "events": True,  # write the structured event log (.runtime/events/); false = no emission at all
    "events_keep_days": 30,  # the scheduler deletes event-log days older than this (at most once a day)
    "heartbeat_seconds": 60,  # the scheduler writes a heartbeat event this often
}
LESSONS_MAX_CHARS = 800  # longest `lessons` text a report on a service request may carry


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _message_cap(config: dict) -> int:
    """``max_message_chars`` from ORG.md; a malformed value means the default."""
    try:
        cap = int(config["max_message_chars"])
    except (TypeError, ValueError):
        return int(DEFAULT_CONFIG["max_message_chars"])
    return cap if cap > 0 else int(DEFAULT_CONFIG["max_message_chars"])


def _short(value: object, limit: int = 80) -> str:
    text = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=10_000).strip()
    if text.endswith("\n..."):
        text = text[:-4].strip()
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def config_default_model(config: dict | None) -> str:
    """The default model of a config mapping (``null``, empty or missing = DEFAULT_MODEL)."""
    return str((config or {}).get("default_model") or "").strip() or DEFAULT_MODEL


def charter_change_note(addr: str, old: dict, written: dict, merged: dict) -> str:
    """What a charter rewrite did to the frontmatter: keys kept from the old one, keys changed (old -> new), added."""
    kept = [k for k in old if k not in written]
    changed = [f"{k}: {_short(old[k])} -> {_short(written[k])}" for k in old if k in written and old[k] != written[k]]
    added = [f"{k}: {_short(written[k])}" for k in written if k not in old]
    parts = [f"charter frontmatter of `{addr}`:"]
    parts.append(f"kept from the old frontmatter (not in your text): {', '.join(kept)}." if kept else "nothing kept from the old frontmatter (your text set every key).")
    if changed:
        parts.append("changed (old -> new): " + "; ".join(changed) + ".")
    if added:
        parts.append("added: " + "; ".join(added) + ".")
    if not changed and not added:
        parts.append("no key changed.")
    parts.append("A key you leave out is kept; to remove one, set it explicitly (e.g. `tools: []`).")
    return " ".join(parts)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".tmp-{secrets.token_hex(4)}-{path.name}"
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _fold(name: str) -> str:
    """Key under which two file names count as the same name on *some* filesystem.

    macOS (APFS/HFS+) and Windows ignore letter case (and Unicode form); Windows also ignores trailing dots and
    spaces. Protected names are compared through this key, so the write guard behaves identically on case-sensitive
    and case-insensitive filesystems: it never has to ask the filesystem which kind it is.
    """
    return unicodedata.normalize("NFKC", name).casefold().rstrip(" .")


_FOLDED_RUNTIME_NAMES = {_fold(n) for n in RUNTIME_NAMES}
# Files an agent may only write under their exact spelling (any other casing is a different name on Linux and the
# same file on macOS, so it is refused outright).
_EXACT_FILES = {_fold(n): n for n in ("AGENT.md", "MEMORY.md", "ORG.md")}


def _case_twin(parent: Path, name: str) -> str | None:
    """The existing entry of ``parent`` that equals ``name`` except for case, if there is one."""
    try:
        names = os.listdir(parent)
    except OSError:
        return None
    if name in names:
        return None
    key = _fold(name)
    return next((n for n in names if _fold(n) == key), None)


_PARSED: OrderedDict[str, tuple[tuple[int, int], dict, str]] = OrderedDict()  # Message.load cache (LRU)
_PARSED_MAX = 50_000


def _load_message(cls: type[Message], path: Path) -> Message:
    """Parse a message file. Messages are immutable, so the parse is cached by path + mtime_ns + size."""
    key = str(path)
    with open(path, "rb") as f:
        st = os.fstat(f.fileno())
        stamp = (st.st_mtime_ns, st.st_size)
        hit = _PARSED.get(key)
        if hit is not None and hit[0] == stamp:
            try:
                _PARSED.move_to_end(key)
            except KeyError:  # evicted by another thread: harmless
                pass
            meta, body = hit[1], hit[2]
        else:
            text = f.read().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")  # like read_text
            meta, body = split_frontmatter(text)
            _PARSED[key] = (stamp, meta, body)
            while len(_PARSED) > _PARSED_MAX:
                try:
                    _PARSED.popitem(last=False)
                except KeyError:
                    break
    return cls.from_parts(meta, body, path)


# The file reader (with its parse cache) is the one piece of Message that touches the filesystem; the kernel's Message is pure
# data, so the legacy classmethod is attached here until the mail package takes it over (patch point `core.Message.load`).
Message.load = classmethod(_load_message)  # type: ignore[attr-defined]


class Retired(NamedTuple):
    addr: str
    refunded: int  # runs of unspent team budget returned to ``refunded_to``
    refunded_to: str | None


class Org:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        if not (self.root / "ORG.md").is_file():
            raise OrgError(f"not an organization (no ORG.md): {self.root}")

    # ------------------------------------------------------------------ setup

    @classmethod
    def init(cls, root: str | Path, mission: str | None = None, config: dict | None = None) -> Org:
        root = Path(root).expanduser().resolve()
        if (root / "ORG.md").exists():
            raise OrgError(f"already an organization: {root}")
        root.mkdir(parents=True, exist_ok=True)
        cfg = {**DEFAULT_CONFIG, **(config or {})}
        atomic_write(root / "ORG.md", join_frontmatter(cfg, templates.org_rules(mission)))
        for box in BOXES:
            (root / box).mkdir(exist_ok=True)
        (root / ".runtime").mkdir(exist_ok=True)
        (root / ".gitignore").write_text(".tmp-*\nruns/\n.kiro/\n.runtime/scheduler.pid\n.runtime/events/\n", encoding="utf-8")
        if shutil.which("git") and not (root / ".git").exists():
            subprocess.run(["git", "init", "-q"], cwd=root, check=False)
        org = cls(root)
        org.commit("init organization")
        return org

    @staticmethod
    def find_root(start: str | Path | None = None) -> Path:
        env = os.environ.get("ORG_ROOT")
        if env:
            return Path(env).expanduser().resolve()
        here = Path(start or Path.cwd()).resolve()
        for d in (here, *here.parents):
            if (d / "ORG.md").is_file():
                return d
        if (here / "org" / "ORG.md").is_file():  # e.g. running from the orgmcp project dir
            return here / "org"
        raise OrgError("no organization found: set ORG_ROOT or run inside an org directory")

    @property
    def config(self) -> dict:
        meta, _ = split_frontmatter((self.root / "ORG.md").read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **meta}

    def rules(self) -> str:
        return split_frontmatter((self.root / "ORG.md").read_text(encoding="utf-8"))[1].strip()

    def commit(self, message: str) -> None:
        """Snapshot the organization in git (if it is a repo). Called by the runtime after each run."""
        if not (self.root / ".git").exists():
            return
        git = ["git", "-c", "user.name=orgmcp", "-c", "user.email=orgmcp@localhost"]
        subprocess.run([*git, "add", "-A"], cwd=self.root, capture_output=True)
        subprocess.run([*git, "commit", "-q", "-m", message], cwd=self.root, capture_output=True)

    # ------------------------------------------------------------- addressing

    @staticmethod
    def norm(addr: str | None) -> str:
        return _norm(addr)

    def dir(self, addr: str) -> Path:
        a = self.norm(addr)
        return self.root if a == ROOT else self.root / a

    def exists(self, addr: str) -> bool:
        a = self.norm(addr)
        if a == ROOT:
            return True
        parts = a.split("/")
        if not all(NAME_RE.fullmatch(p) and p not in RESERVED for p in parts):
            return False
        return (self.dir(a) / "AGENT.md").is_file()

    def require(self, addr: str) -> str:
        a = self.norm(addr)
        if not self.exists(a):
            raise OrgError(f"no such agent: {a}")
        return a

    @classmethod
    def parent(cls, addr: str) -> str | None:
        return _parent(addr)

    @classmethod
    def depth(cls, addr: str) -> int:
        return _depth(addr)

    def child_addr(self, parent: str, name: str) -> str:
        return _child_addr(parent, name)

    def children(self, addr: str) -> list[str]:
        a = self.norm(addr)
        d = self.dir(a)
        if not d.is_dir():
            return []
        return [
            self.child_addr(a, p.name)
            for p in sorted(d.iterdir())
            if p.is_dir() and NAME_RE.fullmatch(p.name) and p.name not in RESERVED and (p / "AGENT.md").is_file()
        ]

    def agents(self) -> list[str]:
        """Every agent except root, parents before children."""
        out, stack = [], list(reversed(self.children(ROOT)))
        while stack:
            a = stack.pop()
            out.append(a)
            stack.extend(reversed(self.children(a)))
        return out

    def subtree(self, addr: str) -> list[str]:
        out, stack = [], [self.norm(addr)]
        while stack:
            a = stack.pop()
            out.append(a)
            stack.extend(self.children(a))
        return out

    def charter(self, addr: str) -> tuple[dict, str]:
        a = self.norm(addr)
        if a == ROOT:
            return {"role": "human (root of the organization)"}, ""
        meta, body = split_frontmatter((self.dir(a) / "AGENT.md").read_text(encoding="utf-8"))
        return meta, body.strip()

    @property
    def default_model(self) -> str:
        """The org-wide model: the config's ``default_model``, else DEFAULT_MODEL (also for ``null`` or a missing key)."""
        return config_default_model(self.config)

    def model_for(self, addr: str) -> str:
        """The model a run of ``addr`` uses: its charter's ``model``, else the org config's ``default_model``, else DEFAULT_MODEL."""
        meta, _ = self.charter(addr)
        return str(meta.get("model") or "").strip() or self.default_model

    def memory(self, addr: str) -> str:
        p = self.dir(addr) / "MEMORY.md"
        return p.read_text(encoding="utf-8") if p.is_file() else ""

    def can_message(self, sender: str, to: str, reply_to: str | None = None) -> bool:
        if sender in (ROOT, RUNTIME):
            return True  # the human and the runtime may address anyone
        if to == sender:
            return False
        if to == self.parent(sender) or self.parent(to) == sender or self.parent(to) == self.parent(sender):
            return True
        if reply_to:  # anyone may answer a message they received
            original = self.find_received(sender, reply_to)
            return original is not None and original.sender == to
        return False

    # --------------------------------------------------------------- messages

    def messages(self, addr: str, *boxes: str) -> list[Message]:
        out = []
        for box in boxes:
            d = self.dir(addr) / box
            if d.is_dir():
                out += [Message.load(p) for p in _visible(d.glob("*.md"))]
        return sorted(out, key=lambda m: m.id)

    def received(self, addr: str) -> list[Message]:
        return self.messages(addr, "inbox", "inflight", "read")

    def sent(self, addr: str) -> list[Message]:
        return self.messages(addr, "sent")

    def unread(self, addr: str) -> int:
        """Messages in the inbox that wake the agent: what makes it runnable and what health calls "unread mail".

        Non-waking messages (``wake: false``) sit in the inbox uncounted and join the batch of its next real run.
        """
        d = self.dir(addr) / "inbox"
        return sum(1 for p in _visible(d.glob("*.md")) if self._wakes(p)) if d.is_dir() else 0

    @staticmethod
    def _wakes(path: Path) -> bool:
        try:
            return Message.load(path).wake
        except Exception:  # noqa: BLE001 - an unreadable file still counts as mail: a run should look at it
            return True

    def find_received(self, addr: str, msg_id: str) -> Message | None:
        return next((m for m in self.received(addr) if m.id == msg_id), None)

    def open_tasks(self, addr: str) -> list[Message]:
        a = self.norm(addr)
        answered = {m.reply_to for m in self.sent(a) if m.type == "result"}
        return [m for m in self.received(a) if m.type == "task" and m.id not in answered]

    def outstanding(self, addr: str) -> list[Message]:
        a = self.norm(addr)
        answered = {m.reply_to for m in self.received(a) if m.type == "result"}
        return [m for m in self.sent(a) if m.type == "task" and m.id not in answered]

    def new_id(self, sender: str) -> str:
        return f"{utcnow():%Y%m%dT%H%M%S%f}-{sender.replace('/', '.')}-{secrets.token_hex(2)}"

    # ------------------------------------------------------------------ traces and events

    def emit(self, kind: str, **fields) -> None:
        """Append an event to the org's event log (see :mod:`orgmcp.telemetry`). Never raises."""
        telemetry.emit(self.root, kind, **fields)

    def trace_of(self, addr: str, msg_id: str | None) -> str | None:
        """The trace stamped on message ``msg_id``, looked up in ``addr``'s own boxes (None: not there or unstamped)."""
        if not msg_id or not re.fullmatch(r"[\w.\-]+", str(msg_id)):
            return None
        d = self.dir(addr)
        for box in ("inbox", "inflight", "read", "sent"):
            p = d / box / f"{msg_id}.md"
            if p.is_file():
                try:
                    return Message.load(p).trace
                except Exception:  # noqa: BLE001
                    return None
        return None

    def open_task_traces(self, addr: str) -> list[str | None]:
        """Traces of the tasks ``addr`` received and has not finished (no result, or only a ``blocked`` one)."""
        a = self.norm(addr)
        if a in (ROOT, RUNTIME) or not self.exists(a):
            return []
        latest = latest_results(self.sent(a))
        return [
            t.trace for t in self.received(a)
            if t.type == "task" and ((r := latest.get(t.id)) is None or r.status == "blocked")
        ]

    def context_trace(self, addr: str) -> tuple[str | None, str, list[str]]:
        """(trace, rule, candidates) from what ``addr`` is working on: rule 3 (its open tasks all share one trace),
        else rule 4 (its current batch has exactly one), else (None, "ambiguous", every trace it could be)."""
        a = self.norm(addr)
        open_traces = self.open_task_traces(a)
        distinct = {t for t in open_traces if t}
        if len(distinct) == 1 and None not in open_traces:
            return next(iter(distinct)), "open-task", []
        batch = {m.trace for m in self.messages(a, "inflight")} if a not in (ROOT, RUNTIME) and self.exists(a) else set()
        batch_distinct = {t for t in batch if t}
        if len(batch_distinct) == 1:
            return next(iter(batch_distinct)), "batch", []
        return None, "ambiguous", sorted(distinct | batch_distinct)

    def stamp_trace(self, msg: Message) -> tuple[str, list[str]]:
        """Set ``msg.trace`` (first matching rule wins) and return (rule, candidates). Rules:

        ``given`` already set (runtime notices about a known task); ``new`` root sends a task without ``revises``: its
        own id; ``link`` it answers (``reply_to``) or reworks (``revises``) a message that has a trace; ``open-task``
        the sender's unfinished tasks share one trace; ``batch`` the sender's current batch has one; else
        ``ambiguous`` (``trace`` stays None; the candidates are returned for the event).
        """
        if msg.trace:
            return "given", []
        sender = self.norm(msg.sender)
        if sender == ROOT and msg.type == "task" and not msg.revises:
            msg.trace = msg.id
            return "new", []
        for ref in (msg.reply_to, msg.revises):
            linked = self.trace_of(sender, ref) if sender != RUNTIME else None
            if linked:
                msg.trace = linked
                return "link", []
        if sender == RUNTIME:
            return "ambiguous", []
        trace, rule, candidates = self.context_trace(sender)
        msg.trace = trace
        return rule, candidates

    def deliver(self, msg: Message) -> Message:
        """Low level: assign an id, stamp the trace and write the message. Policy is checked by the callers."""
        msg.id = msg.id or self.new_id(msg.sender)
        msg.created = msg.created or utcnow().isoformat(timespec="seconds")
        try:
            rule, candidates = self.stamp_trace(msg)
        except Exception:  # noqa: BLE001 - a trace is bookkeeping: never worth failing a message for
            rule, candidates = "error", []
        text = msg.to_text()
        # Sender's copy first: it is what charges a budget grant. A failure between the two writes can then only
        # leave a message charged but undelivered (recover() re-delivers it), never delivered but uncharged.
        if msg.sender != RUNTIME:
            atomic_write(self.dir(msg.sender) / "sent" / f"{msg.id}.md", text)
        atomic_write(self.dir(msg.to) / "inbox" / f"{msg.id}.md", text)
        telemetry.note_trace(msg.trace)
        extra = {"trace_candidates": candidates} if candidates else {}
        self.emit(
            "msg.deliver", actor=msg.sender, trace=msg.trace, id=msg.id, type=msg.type, **{"from": msg.sender},
            to=msg.to, title=telemetry.clip(msg.title), status=msg.status, budget=msg.budget, reply_to=msg.reply_to,
            revises=msg.revises, supersedes=msg.supersedes, service=msg.service, feedback=msg.feedback,
            wake=msg.wake, hops=msg.hops, chars=len(msg.body), trace_rule=rule, **extra,
        )
        return msg

    def notify(self, to: str, title: str, body: str, wake: bool = True, trace: str | None = None) -> Message:
        """A notice from the runtime itself (budget, failures, stalls). ``wake=False``: see :meth:`unread`.
        ``trace``: the request the notice is about, when known."""
        return self.deliver(Message(
            sender=RUNTIME, to=self.norm(to), type="note", title=title, body=body, wake=wake, trace=trace or None,
        ))

    # ----------------------------------------------------------------- budget

    def runs_used(self, addr: str) -> int:
        d = self.dir(addr) / "runs"
        return len(_visible(d.glob("*.log"))) if d.is_dir() else 0

    def budget(self, addr: str) -> int | None:
        """Runs this agent may still use. None = unlimited (root)."""
        a = self.norm(addr)
        if a == ROOT:
            return None
        got = sum(m.budget for m in self.received(a))
        given = sum(m.budget for m in self.sent(a))
        return got - given - self.runs_used(a)

    def delegable(self, addr: str) -> tuple[int, int, int]:
        """(budget, outstanding delegations, the most ``addr`` can hand down with one more delegation).

        The most is ``budget - outstanding - 1`` (one run kept per outstanding delegation to process its result, one
        for the new delegation's own result), never below 0.
        """
        budget = self.budget(addr) or 0
        out = len(self.outstanding(addr))
        return budget, out, max(0, budget - out - 1)

    def grant_hint(self, addr: str) -> str:
        """What a direct report can do with its budget now (shown to whoever just granted it runs); "" if it cannot hire."""
        if not self.exists(addr) or not self.charter(addr)[0].get("can_hire"):
            return ""
        budget, out, most = self.delegable(addr)
        head = f"`{addr}` now has {budget} run(s) and {out} outstanding delegation(s)"
        if most > 0:
            return f"{head}; with one more delegation it can hand down at most {most} run(s)."
        need = out + 2  # budget - out - 1 >= 1
        return (
            f"{head}: with {budget} run(s) and {out} outstanding delegation(s) it cannot delegate anything; it can "
            f"only process results or work itself - grant at least {max(0, need - budget)} more (a budget of {need}) "
            "to allow one delegation of 1 run."
        )

    def _check_allocation(self, actor: str, amount: int, new_delegation: bool) -> None:
        if actor == ROOT or amount == 0:
            return
        remaining = self.budget(actor) or 0
        reserve = len(self.outstanding(actor)) + (1 if new_delegation else 0)
        if remaining - amount < reserve:
            raise OrgError(
                f"not enough budget: you have {remaining} run(s) and must keep {reserve} in reserve "
                f"(one per outstanding delegation, to process its result), so you can hand down at most "
                f"{max(0, remaining - reserve)}. Ask your parent for more budget or do less."
            )

    def _next_hops(self, actor: str) -> int:
        if actor in (ROOT, RUNTIME):
            return 0
        return max((m.hops for m in self.messages(actor, "inflight")), default=0) + 1

    # ------------------------------------------------------- policy operations
    # Each takes the acting agent first. The MCP server binds `actor` to the caller's identity.

    def send(
        self,
        actor: str,
        to: str,
        body: str,
        *,
        type: str = "note",
        title: str = "",
        reply_to: str | None = None,
        status: str | None = None,
        budget: int = 0,
        revises: str | None = None,
        supersedes: str | None = None,
        service: str | None = None,
        contract: int | None = None,
        playbook: int | None = None,
        feedback: str | None = None,
        wake: bool = True,
        _skip_route_check: bool = False,
    ) -> Message:
        cap = _message_cap(self.config)
        if len(body.strip()) > cap and self.norm(actor) != ROOT:  # the cap protects agents' runs; the human may paste
            raise OrgError(
                f"message is {len(body.strip())} characters; the limit is {cap} (max_message_chars). Messages are "
                "read in full by the recipient's next run, so keep them short: write the detail to a file inside "
                "your own directory and send a short message that gives its path."
            )
        actor, to = self.require(actor), self.require(to)
        if type not in MESSAGE_TYPES:
            raise OrgError(f"type must be one of {MESSAGE_TYPES}")
        if not body.strip():
            raise OrgError("message body is empty")
        if not _skip_route_check and not self.can_message(actor, to, reply_to):
            raise OrgError(
                f"{actor} cannot message {to}: you may message your parent, your direct reports, "
                "your siblings, or whoever sent you the message you are replying to (reply_to)."
            )
        budget = int(budget or 0)
        if budget < 0:
            raise OrgError("budget cannot be negative")
        if budget and actor != ROOT and self.parent(to) != actor and to != self.parent(actor):
            raise OrgError("budget can only be handed to your direct reports, or returned to your parent")
        self._check_allocation(actor, budget, new_delegation=type == "task")
        hops = self._next_hops(actor)
        if type != "result" and hops > int(self.config["max_hops"]):  # reports always get through
            raise OrgError(
                f"message chain is {hops} hops long (limit {self.config['max_hops']}); this looks like a loop. "
                "Report blocked to whoever assigned your task instead."
            )
        msg = Message(
            sender=actor, to=to, type=type, body=body.strip(), title=title.strip(),
            reply_to=reply_to, status=status, budget=budget, hops=hops, revises=revises,
            supersedes=supersedes, service=service, contract=contract, playbook=playbook, feedback=feedback,
            wake=wake,
        )
        return self.deliver(msg)

    def delegate(
        self,
        actor: str,
        to: str,
        title: str,
        goal: str,
        acceptance: str,
        inputs: list[str] | None = None,
        budget: int | None = None,
        revises: str | None = None,
    ) -> Message:
        actor, to = self.require(actor), self.require(to)
        if actor != ROOT and self.parent(to) != actor:
            reports = ", ".join(self.children(actor)) or "none (hire one first)"
            raise OrgError(f"you can only delegate to your direct reports: {reports}")
        if not title.strip() or not goal.strip() or not acceptance.strip():
            raise OrgError("a task needs a title, a goal and acceptance criteria")
        if budget is None:
            budget = self._default_budget(actor)
        budget = int(budget)
        if budget < 1:
            raise OrgError("a task needs a budget of at least 1 run")
        if revises and not any(m.id == revises and m.type == "task" and m.to == to for m in self.sent(actor)):
            raise OrgError(f"revises must be the id of an earlier task you sent to {to}: {revises}")
        body = templates.task_body(goal, acceptance, list(inputs or []))
        fields: dict = {}
        if revises:  # rework of a service request is still part of its case
            from . import services

            fields = services.rework_fields(self, actor, revises)
        return self.send(actor, to, body, type="task", title=title, budget=budget, revises=revises or None, **fields)

    def _default_budget(self, actor: str) -> int:
        """Runs a delegation gets when the caller names none: what the actor can afford, capped at default_budget.

        min(default_budget, remaining - reserve), where the reserve keeps one run per outstanding delegation plus
        one for the result of this new one. Root has no limit.
        """
        default = int(self.config["default_budget"])
        if actor == ROOT:
            return default
        remaining = self.budget(actor) or 0
        reserve = len(self.outstanding(actor)) + 1
        affordable = remaining - reserve
        if affordable < 1:
            raise OrgError(
                f"you cannot afford this delegation: you have {remaining} run(s) and must keep {reserve} in reserve "
                "(one per outstanding delegation, plus one to process the result of this one), so nothing is left "
                "to hand down. Options: ask your parent for more budget with `send` and end your run; do the work "
                "yourself; or, if the task cannot be completed without this step, report `blocked` (never `done`) "
                "and say what is missing."
            )
        return min(default, affordable)

    def _normalize_artifact(self, actor: str, path: str, since: str = "") -> str:
        """Resolve an artifact path and annotate it with facts a manager can check claims against.

        Inside the organization (paths relative to the org root, or absolute) or, as an absolute path, inside the
        reporter's own workspace. Anything else is refused before existence is checked: no probing of the host.
        """
        p = Path(path).expanduser()
        ws = self.workspace_of(actor)
        if not p.is_absolute():
            p = next((b / p for b in (self.root, self.dir(actor)) if (b / p).exists()), self.root / p)
        p = p.resolve()
        in_org = p == self.root or self.root in p.parents
        if not in_org and not (ws is not None and _inside(p, ws)):
            where = f"inside your workspace ({ws})" if ws is not None else "(you have no workspace)"
            raise OrgError(
                f"artifacts must be inside the organization (paths relative to the org root) or, by absolute path, "
                f"{where}: {path}"
            )
        if not p.exists():
            hint = ""
            if ws is not None and not Path(path).expanduser().is_absolute() and (ws / path).exists():
                hint = f" It exists in your workspace: report it by absolute path ({(ws / path).resolve()})."
            raise OrgError(f"artifact not found: {path} (relative paths are relative to the org root).{hint}")
        shown = str(p.relative_to(self.root)) if in_org else str(p)
        if p.is_dir():
            return f"{shown}/ (directory)"
        modified = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        note = f"{word_count(p.read_text(encoding='utf-8', errors='replace'))} words, modified {modified:%H:%M:%S} UTC"
        if since and modified.isoformat(timespec="seconds") < since:
            note += ", NOT modified since this task was assigned"
        return f"{shown} ({note})"

    def report(
        self,
        actor: str,
        task_id: str,
        status: str,
        summary: str,
        artifacts: list[str] | None = None,
        lessons: str | None = None,
    ) -> Message:
        actor = self.require(actor)
        if status not in RESULT_STATUSES:
            raise OrgError(f"status must be one of {RESULT_STATUSES}")
        task = self.find_received(actor, task_id)
        if task is None or task.type != "task":
            open_ids = ", ".join(t.id for t in self.open_tasks(actor)) or "none"
            raise OrgError(f"no task {task_id} assigned to you. Your open tasks: {open_ids}")
        prior = latest_results(self.sent(actor)).get(task_id)
        if prior is not None and prior.status != "blocked":
            raise OrgError(
                f"task {task_id} was already reported {prior.status}, and {prior.status} is final (rule 6): it cannot be "
                "reported again or changed by a note. Only a task reported `blocked` can be reported again. If you have "
                "information for whoever assigned it, use `send`, as information only: a note does not change the "
                "task's outcome and must not claim that criteria are met."
            )
        lessons = self._check_lessons(task, status, lessons)
        arts = [self._normalize_artifact(actor, a, task.created) for a in (artifacts or [])]
        body = templates.result_body(summary, arts, lessons)
        return self.send(
            actor, task.sender, body, type="result", title=task.title,
            reply_to=task.id, status=status, supersedes=prior.id if prior else None, _skip_route_check=True,
            budget=self._budget_to_return(actor, task, status),
        )

    @staticmethod
    def _check_lessons(task: Message, status: str, lessons: str | None) -> str:
        """The lessons text for a report: required on a service request (done, failed or blocked), 1..800 characters."""
        text = (lessons or "").strip()
        if task.service and status in ("done", "failed", "blocked") and not text:
            raise OrgError(
                f"task {task.id} is a request for service `{task.service}`: pass `lessons` - 1-3 lines for the next "
                "request: what worked, what to change in the playbook, and the evidence (runs, rework, review "
                "findings). Required for done, failed and blocked alike: a blocker is the most informative case, so "
                "say what went wrong and what would have prevented it"
            )
        if len(text) > LESSONS_MAX_CHARS:
            raise OrgError(
                f"lessons are {len(text)} characters; the limit is {LESSONS_MAX_CHARS}. Keep 1-3 lines: what worked, "
                "what to change in the playbook, and the evidence; put detail in a file under your work/ directory."
            )
        return text

    def _budget_to_return(self, actor: str, task: Message, status: str) -> int:
        """Runs that travel up with the final result of ``task``: everything the reporter has left, or 0.

        Only a final result (``done``/``failed``) returns budget, and only when nothing else needs the reporter's
        runs after it: no other open task, no other task reported ``blocked`` (it may be re-reported), no outstanding
        delegation (their results need the reserve) and no mail waiting for a run. It goes to the assigner, and only
        when that is the reporter's parent (the one route budget may travel up). The amount is read from the files
        at the moment of the report and the transfer is the result message itself, so it is counted exactly once: a
        redelivered run finds the task already final (a second ``report`` is refused) and nothing left to return.
        """
        if status == "blocked" or task.sender != self.parent(actor):
            return 0
        busy = (
            [t for t in self.open_tasks(actor) if t.id != task.id]
            or [t for t in self._blocked_tasks(actor) if t.id != task.id]
            or self.outstanding(actor)
            or self.unread(actor)
        )
        return 0 if busy else max(0, self.budget(actor) or 0)

    def reclaim(self, actor: str, report: str, budget: int | None = None) -> Message:
        """Pull unspent budget back from an idle DIRECT report (short name or full address). Default: all of it.

        Budget is derived from messages, so this is one: a note from the report to ``actor`` carrying the budget,
        written by the runtime on the report's behalf (it lands in the report's ``sent/``, which charges it, and in the
        actor's inbox, which credits it). Nothing is minted or destroyed. It does not wake the actor, who is running
        now. The report receives nothing, so it is not woken either. Root may reclaim from its direct reports (the
        runs go back to root, who has no limit). Never from deeper down: a manager reclaims from its own reports, and
        those reclaim from theirs.

        Refused unless the report is idle: it has no open task, nothing delegated and still outstanding, no run in
        flight and no unread mail that would wake it; its budget has to be above zero.
        """
        actor = self.require(actor)
        short = self.norm(report)
        addr = short if "/" in short else self.child_addr(actor, short)
        if addr == ROOT or not self.exists(addr) or self.parent(addr) != actor:
            reports = ", ".join(self.children(actor)) or "none"
            raise OrgError(
                f"you can only reclaim budget from your direct reports (yours: {reports}); {report!r} is not one. "
                "Ask a manager to reclaim from its own team."
            )
        if budget is not None and int(budget) < 1:
            raise OrgError("budget must be at least 1 run (omit it to reclaim everything the report has left)")
        why = [
            text for text in (
                "it is running now" if self.running(addr) else "",
                f"it has {len(self.open_tasks(addr))} open task(s)" if self.open_tasks(addr) else "",
                f"it has {len(self.outstanding(addr))} delegation(s) still outstanding" if self.outstanding(addr) else "",
                f"it has {self.unread(addr)} unread message(s) that will wake it" if self.unread(addr) else "",
            ) if text
        ]
        if why:
            raise OrgError(
                f"{addr} is busy ({'; '.join(why)}), so its runs are not stranded. Wait until it has reported, or "
                "leave its budget with it."
            )
        available = max(0, self.budget(addr) or 0)
        if available < 1:
            raise OrgError(f"{addr} has no unspent budget to reclaim ({self.budget(addr)} run(s) left)")
        amount = available if budget is None else int(budget)
        if amount > available:
            raise OrgError(f"{addr} has only {available} unspent run(s); you asked for {amount}")
        return self.deliver(Message(
            sender=addr, to=actor, type="note", budget=amount, wake=False, hops=0,
            title=f"budget reclaimed by {actor}",
            body=f"{actor} reclaimed {amount} unspent run(s) from {addr} ({available - amount} left with it). "
                 f"The runtime wrote this note on {addr}'s behalf; {addr} received nothing and was not woken.",
        ))

    # ---------------------------------------------------------------- services
    # Thin wrappers: the rules live in :mod:`orgmcp.services` (imported late: it builds on this module).

    def service_names(self, addr: str) -> list[str]:
        """Names of the (non-retired) services ``addr`` offers: the directories of ``<addr>/services`` with a SERVICE.md."""
        a = self.norm(addr)
        d = self.dir(a) / "services"
        if a == ROOT or not d.is_dir():
            return []
        return [p.name for p in _visible(d.iterdir()) if p.is_dir() and (p / "SERVICE.md").is_file()]

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs=None, acceptance=None,
        deliverable: dict | None = None, budget: int | None = None, playbook: str | None = None,
        locked: bool | None = None, notes: str | None = None, add_acceptance=None, remove_acceptance=None,
    ) -> str:
        """Define a service of a direct report, or amend it (omitted fields keep their value). See
        :func:`orgmcp.services.define_service`."""
        from . import services

        return services.define_service(
            self, actor, owner, name, description=description, inputs=inputs, acceptance=acceptance,
            deliverable=deliverable, budget=budget, playbook=playbook, locked=locked, notes=notes,
            add_acceptance=add_acceptance, remove_acceptance=remove_acceptance,
        )

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        """Take a service out of use (its files are kept). See :func:`orgmcp.services.retire_service`."""
        from . import services

        return services.retire_service(self, actor, owner, name, reason)

    def request(
        self, actor: str, service: str, inputs: dict | None, *, title: str = "", note: str = "",
        extra_acceptance: list[str] | None = None, budget: int | None = None, revises: str | None = None,
    ) -> Message:
        """Ask a direct report for one of its services. See :func:`orgmcp.services.request`."""
        from . import services

        return services.request(
            self, actor, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance,
            budget=budget, revises=revises,
        )

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        """Write the next version of the playbook of a service you own; returns the version."""
        from . import services

        return services.revise_playbook(self, actor, service, content, reason)

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        """Tell the owner whether a delivered service request was accepted or rejected."""
        from . import services

        return services.feedback(self, actor, task_id, verdict, note)

    def hire(
        self,
        actor: str,
        name: str,
        role: str,
        charter: str,
        *,
        model: str | None = None,  # None = the org's default model (DEFAULT_MODEL unless ORG.md sets another)
        tools: list[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
        inputs: list[str] | None = None,
    ) -> str:
        actor = self.require(actor)
        if not NAME_RE.fullmatch(name) or name in RESERVED:
            raise OrgError("name must be lowercase letters, digits and dashes (max 32), and not a reserved word")
        tools = sorted(set(tools or []))
        meta, _ = self.charter(actor)
        if inputs is not None:
            inputs = self._check_inputs(inputs)
        elif actor != ROOT and "read" in tools and not workspace and not self.unconfined_read(meta):
            inputs = []  # a confined hirer never hands down an unconfined `read`: nothing unless it names inputs
        if actor != ROOT:
            if not meta.get("can_hire"):
                raise OrgError("your charter does not allow hiring")
            if len(self.children(actor)) >= int(meta.get("max_children", 5)):
                raise OrgError(f"you already have the maximum of {meta.get('max_children', 5)} direct reports")
            self._check_authority(actor, tools, workspace, inputs)
        addr = self.child_addr(actor, name)
        if self.depth(addr) > int(self.config["max_depth"]):
            raise OrgError(f"the organization is limited to depth {self.config['max_depth']}")
        d = self.dir(addr)
        if d.exists():
            raise OrgError(f"{addr} already exists")
        child_meta = {
            "role": role.strip(),
            "model": model,
            "tools": tools,
            "can_hire": bool(can_hire),
            "max_children": int(max_children),
            "workspace": workspace,
            "inputs": inputs,
            "hired_by": actor,
            "created": utcnow().isoformat(timespec="seconds"),
        }
        child_meta = {k: v for k, v in child_meta.items() if v is not None}
        for sub in (*BOXES, "work", "runs"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        atomic_write(d / "MEMORY.md", "")
        atomic_write(d / "AGENT.md", join_frontmatter(child_meta, templates.charter_body(role, charter)))
        self.emit("agent.hire", actor=actor, agent=addr, by=actor, role=telemetry.clip(role.strip()),
                  model=self.model_for(addr), tools=tools)
        return addr

    def _check_authority(self, actor: str, tools: list[str], workspace: str | None, inputs: list[str] | None = None) -> None:
        """Authority only narrows down the tree: a parent cannot grant what it does not have."""
        meta, _ = self.charter(actor)
        extra = set(tools) - set(meta.get("tools") or [])
        if extra:
            raise OrgError(f"you cannot grant tools you do not have yourself: {', '.join(sorted(extra))}")
        if workspace:
            mine = meta.get("workspace")
            if not mine:
                raise OrgError("you have no workspace, so you cannot assign one")
            ws, base = Path(workspace).expanduser().resolve(), Path(mine).expanduser().resolve()
            if ws != base and base not in ws.parents:
                raise OrgError(f"a report's workspace must be inside yours ({mine})")
        if inputs:
            bases = [b for b in (self.workspace_of(actor), *self.inputs_of(actor)) if b is not None]
            if not bases:
                raise OrgError("you have no workspace or inputs, so you cannot assign inputs")
            for raw in inputs:
                if not any(_inside(Path(raw).expanduser().resolve(), b) for b in bases):
                    raise OrgError(
                        f"a report's inputs must be inside your inputs or workspace ({', '.join(map(str, bases))}): {raw}"
                    )

    # ------------------------------------------------------ workspace and inputs

    def workspace_of(self, addr: str) -> Path | None:
        """The agent's workspace (read-write for its built-in tools) as a resolved path, if its charter has one."""
        a = self.norm(addr)
        if a == ROOT or not self.exists(a):
            return None
        raw = self.charter(a)[0].get("workspace")
        return Path(str(raw)).expanduser().resolve() if raw else None

    def inputs_of(self, addr: str) -> list[Path]:
        """The agent's read-only inputs (charter ``inputs``) as resolved paths."""
        a = self.norm(addr)
        if a == ROOT or not self.exists(a):
            return []
        raw = self.charter(a)[0].get("inputs")
        items = [raw] if isinstance(raw, str) else (raw if isinstance(raw, list) else [])
        return [Path(str(x)).expanduser().resolve() for x in items if str(x).strip()]

    @staticmethod
    def unconfined_read(meta: dict) -> bool:
        """Legacy charter: no workspace and no ``inputs`` key. Its built-in ``read`` is not confined (as before)."""
        return not meta.get("workspace") and "inputs" not in meta

    def _check_inputs(self, inputs) -> list[str]:
        """Inputs are absolute paths outside the organization directory (kiro reads them; the org owns its own)."""
        items = [inputs] if isinstance(inputs, str) else list(inputs or [])
        out = []
        for raw in items:
            text = str(raw).strip()
            if not text:
                continue
            p = Path(text).expanduser()
            if not p.is_absolute():
                raise OrgError(f"an input must be an absolute path (got `{text}`)")
            p = p.resolve()
            if _inside(p, self.root) or _inside(self.root, p):
                raise OrgError(f"an input must not overlap the organization directory ({self.root}): {text}")
            out.append(text)
        return out

    def readable_roots(self, addr: str) -> list[Path]:
        """Directories outside the org that ``read`` shows to ``addr`` by absolute path: its workspace and inputs, and
        the workspace of every agent in its subtree (so a manager can verify what its team made)."""
        a = self.norm(addr)
        roots = [*self.inputs_of(a)]
        roots += [w for s in self.subtree(a) if (w := self.workspace_of(s)) is not None]
        return roots

    def retire(self, actor: str, name: str, reason: str) -> str:
        """Remove a direct report and its team; returns the retired address. See :meth:`retire_team`."""
        return self.retire_team(actor, name, reason).addr

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        """Retire a direct report (short name or full address; root: any agent by full address) and its team.

        Open tasks the team owes the outside are closed as failed, and the team's unspent budget is returned to the
        retired agent's parent as a non-waking runtime note carrying the budget (nothing when the parent is root, who has no
        limit), so budget stays derived from files and is neither destroyed nor minted.
        """
        actor = self.require(actor)
        short = self.norm(name)
        addr = short if "/" in short else self.child_addr(actor, short)
        addr = self.require(addr)
        if addr == ROOT:
            raise OrgError("the root of the organization cannot be retired")
        if actor != ROOT and self.parent(addr) != actor:
            raise OrgError("you can only retire your direct reports")
        team = set(self.subtree(addr))
        for a in team:  # close every task the team owes to the outside world
            for task in self.open_tasks(a):
                if task.sender not in team and self.exists(task.sender):
                    self.deliver(Message(
                        sender=a, to=task.sender, type="result", title=task.title, reply_to=task.id,
                        status="failed", body=f"## Summary\nAgent {a} was retired by {actor}: {reason}",
                    ))
        parent = self.parent(addr)
        # Grants inside the team cancel out, so this is what the parent handed down minus what the team ran.
        refund = max(0, sum(self.budget(a) or 0 for a in team)) if parent != ROOT else 0
        dest = self.root / ".retired" / f"{addr.replace('/', '.')}-{utcnow():%Y%m%dT%H%M%S}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.dir(addr)), dest)
        if refund:  # after the move: a crash in between loses the refund rather than counting it twice
            self.deliver(Message(
                sender=RUNTIME, to=parent, type="note", budget=refund, wake=False, title=f"Budget returned from {addr}",
                body=templates.notice_budget_returned(addr, refund, actor, reason),
            ))
        self.emit("agent.retire", actor=actor, agent=addr, by=actor, reason=telemetry.clip(reason, telemetry.ERROR_MAX),
                  returned_budget=refund, team=sorted(team))
        return Retired(addr, refund, parent if refund else None)

    # ------------------------------------------------------------- file access

    def resolve_read(self, path: str, actor: str | None = None) -> Path:
        """Relative paths are relative to the org root. Absolute paths must be inside the organization or, for an agent,
        inside its workspace or inputs or the workspace of an agent in its subtree. Root reads the organization only."""
        p = (self.root / path.lstrip("/")).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        if _inside(p, self.root):
            return p
        who = self.norm(actor) if actor else ROOT
        if who != ROOT and any(_inside(p, b) for b in self.readable_roots(who)):
            return p
        if who == ROOT:
            raise OrgError("you can only read inside the organization")
        raise OrgError(
            "you can only read inside the organization (paths relative to the org root), or by absolute path inside "
            "your workspace, your read-only inputs, or the workspace of an agent in your team"
        )

    def read(self, path: str, actor: str | None = None) -> str:
        p = self.resolve_read(path or ".", self.require(actor) if actor else None)
        if p.is_dir():
            entries = [f"{c.name}/" if c.is_dir() else c.name for c in _visible(p.iterdir())]
            return "\n".join(entries) or "(empty directory)"
        if not p.is_file():
            raise OrgError(f"not found: {path} (relative paths are relative to the org root)")
        text = p.read_text(encoding="utf-8", errors="replace")
        modified = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        shown = p.relative_to(self.root) if _inside(p, self.root) else p
        head = f"[{shown}: {word_count(text)} words, {text.count(chr(10))} lines, modified {modified:%H:%M:%S} UTC]\n"
        limit = 100_000
        return head + (text if len(text) <= limit else text[:limit] + f"\n... (truncated, {len(text)} chars total)")

    def resolve_write(self, actor: str, path: str) -> Path:
        """Paths are relative to the org root (like every path in the org) and must be inside your directory."""
        actor = self.require(actor)
        base = self.dir(actor).resolve()
        p = Path(path).expanduser()
        p = (p if p.is_absolute() else self.root / p).resolve()
        if p == base or base not in p.parents:
            prefix = "" if actor == ROOT else f"{actor}/"
            raise OrgError(
                f"you may only write inside your own directory. Paths are relative to the org root, so yours "
                f"start with `{prefix}`: e.g. `{prefix}MEMORY.md` or `{prefix}work/notes.md` (got `{path}`)"
            )
        rel = p.relative_to(base).parts
        first = rel[0]
        if _fold(first) == "services":
            raise OrgError(
                "services/ is managed by the runtime: the contract (SERVICE.md) is written by your parent with "
                "define_service, and you change your playbook (PLAYBOOK.md) with revise_playbook"
            )
        if _fold(first) in _FOLDED_RUNTIME_NAMES or first.startswith("."):
            raise OrgError(f"{first} is managed by the runtime; use send/delegate/report to communicate")
        exact = _EXACT_FILES.get(_fold(first))
        if exact and first != exact:
            raise OrgError(f"that name is reserved: it must be spelled exactly `{exact}`")
        cur = base
        for part in rel:  # a spelling that differs only by case from an existing entry would alias it on macOS
            twin = _case_twin(cur, part)
            if twin:
                raise OrgError(f"`{part}` differs only by letter case from the existing `{twin}`; use the exact name `{twin}`")
            cur = cur / part
        if any(_fold(part) == "agent.md" for part in rel):
            if len(rel) == 1:
                raise OrgError("your charter is owned by your parent")
            reports = {c.rsplit("/", 1)[-1] for c in self.children(actor)}
            if rel != (rel[0], "AGENT.md") or rel[0] not in reports:
                raise OrgError(
                    "AGENT.md can only be written for an existing direct report; "
                    "create agents with hire (it enforces hiring rights, limits and authority)"
                )
        if first == "ORG.md" and actor != ROOT:
            raise OrgError("ORG.md is owned by root")
        if (base / first / "AGENT.md").is_file() and p != base / first / "AGENT.md":
            raise OrgError("inside a direct report's directory you may only edit its charter (AGENT.md)")
        return p

    def write(self, actor: str, path: str, content: str, append: bool = False) -> Path:
        return self.write_noted(actor, path, content, append)[0]

    def write_noted(self, actor: str, path: str, content: str, append: bool = False) -> tuple[Path, str]:
        """:meth:`write`, plus a note for the writer (non-empty only for a charter rewrite: what was kept/changed).

        A parent rewriting a report's charter does not strip its frontmatter: every key of the old frontmatter that
        the new text does not set is kept (a key the new text sets, even to an empty value, wins). The authority
        checks run on the merged frontmatter.
        """
        actor = self.require(actor)
        p = self.resolve_write(actor, path)
        note = ""
        if p.name == "AGENT.md" and actor != ROOT:  # a parent editing a report's charter
            meta, body = split_frontmatter(content)
            if not meta.get("role"):
                raise OrgError("a charter needs YAML frontmatter with at least `role:`")
            if not append and p.is_file():
                old, _ = split_frontmatter(p.read_text(encoding="utf-8"))
                merged = {**meta, **{k: v for k, v in old.items() if k not in meta}}
                note = charter_change_note(p.parent.relative_to(self.root).as_posix(), old, meta, merged)
                if len(merged) != len(meta):
                    content = join_frontmatter(merged, body)
                meta = merged
            mine, _ = self.charter(actor)
            if "read" in (meta.get("tools") or []) and self.unconfined_read(meta) and not self.unconfined_read(mine):
                raise OrgError(
                    "a charter with `read` and no workspace needs an `inputs:` list (it may be empty), otherwise its "
                    "built-in read is not confined to the workspace and inputs you have yourself"
                )
            self._check_authority(actor, list(meta.get("tools") or []), meta.get("workspace"), self._check_inputs(meta.get("inputs")))
        if append and p.exists():
            content = p.read_text(encoding="utf-8") + content
        if p == self.dir(actor) / "MEMORY.md":
            cap, words = int(self.config["memory_max_words"]), len(content.split())
            if words > cap:
                raise OrgError(
                    f"MEMORY.md would be {words} words; the limit is {cap}. Do not append: condense it. "
                    "Rewrite the whole file (append=false) keeping only what your next run needs, "
                    "and move detail into files under your work/ directory."
                )
        atomic_write(p, content)
        return p, note

    # ------------------------------------------------------------ run lifecycle

    def begin_run(self, addr: str) -> list[Message]:
        """Move the inbox into inflight/: that batch is what this run handles (held non-waking messages included)."""
        d = self.dir(addr)
        (d / "inflight").mkdir(exist_ok=True)
        for p in _visible((d / "inbox").glob("*.md")):
            os.replace(p, d / "inflight" / p.name)
        return self.messages(addr, "inflight")

    def end_run(self, addr: str, ok: bool) -> None:
        """Success: the batch is processed. Failure: put it back for a retry (at-least-once).

        A no-op for an agent that no longer exists (retired while its run was in flight): its directory is gone,
        and creating the mailbox again would leave a ghost directory behind.
        """
        if not self.exists(addr):
            return
        d = self.dir(addr)
        target = d / ("read" if ok else "inbox")
        target.mkdir(exist_ok=True)
        for p in _visible((d / "inflight").glob("*.md")):
            os.replace(p, target / p.name)

    def start_run_log(self, addr: str) -> Path:
        """Create this run's log file. Its existence is what consumes one run of budget."""
        d = self.dir(addr) / "runs"
        d.mkdir(exist_ok=True)
        p = d / f"{utcnow():%Y%m%dT%H%M%S%f}.log"
        p.touch()
        return p

    def recover(self) -> list[str]:
        """After a crash: return every inflight batch to its inbox, and finish interrupted deliveries.

        Returns the agents whose interrupted run was recovered (see :meth:`redeliver_orphans` for the other part).
        """
        out = []
        for a in self.agents():
            if self.messages(a, "inflight"):
                self.end_run(a, ok=False)
                out.append(a)
        self.redeliver_orphans()
        return out

    def redeliver_orphans(self) -> list[str]:
        """Deliver every sent message whose recipient has no copy (``deliver`` writes ``sent/`` first).

        A message is delivered when its id is in the recipient's inbox, inflight or read; ids are unique across the
        organization, so one scan of the file names finds the orphans without parsing the whole history. Messages
        to agents that no longer exist are left alone. Returns the ids that were re-delivered.
        """
        owners = [ROOT, *self.agents()]
        have = {
            p.stem
            for a in owners
            for box in ("inbox", "inflight", "read")
            if (self.dir(a) / box).is_dir()
            for p in _visible((self.dir(a) / box).glob("*.md"))
        }
        out = []
        for a in owners:
            d = self.dir(a) / "sent"
            for p in _visible(d.glob("*.md")) if d.is_dir() else []:
                if p.stem in have:
                    continue
                try:
                    msg = Message.load(p)
                except Exception:  # noqa: BLE001 - an unreadable file is not ours to fix here
                    continue
                to = self.norm(msg.to)
                if self.exists(to):
                    atomic_write(self.dir(to) / "inbox" / p.name, p.read_text(encoding="utf-8"))
                    out.append(msg.id)
        return out

    def running(self, addr: str) -> bool:
        d = self.dir(addr) / "inflight"
        return d.is_dir() and bool(_visible(d.glob("*.md")))

    def paused(self, addr: str) -> str | None:
        p = self.dir(addr) / ".paused"
        return (p.read_text(encoding="utf-8").strip() or "paused") if p.exists() else None

    def pause(self, addr: str, reason: str, by: str | None = None) -> None:
        """Pause an agent. ``by`` names who did it in the event (default: the acting process)."""
        (self.dir(addr) / ".paused").write_text(reason, encoding="utf-8")
        self.emit("agent.pause", actor=by, agent=addr, reason=telemetry.clip(reason, telemetry.ERROR_MAX))

    def resume(self, addr: str, reason: str = "", by: str | None = None) -> None:
        was = self.paused(addr)
        (self.dir(addr) / ".paused").unlink(missing_ok=True)
        if was is not None:
            self.emit("agent.resume", actor=by, agent=addr, reason=reason or "resumed", previous=telemetry.clip(was, 200))

    def record_failure(self, addr: str) -> int:
        """Count one more consecutive failed run (kept in .runtime/failures.json, so it survives restarts)."""
        counts = self.ledger("failures")
        counts[addr] = int(counts.get(addr, 0)) + 1
        self.save_ledger("failures", counts)
        return counts[addr]

    def clear_failures(self, addr: str) -> None:
        counts = self.ledger("failures")
        if counts.pop(addr, None) is not None:
            self.save_ledger("failures", counts)

    def ledger(self, name: str) -> dict:
        """Runtime-private bookkeeping (``.runtime/<name>.json``): the only state not derived from messages."""
        try:
            return json.loads((self.root / ".runtime" / f"{name}.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return {}

    def save_ledger(self, name: str, data: dict) -> None:
        atomic_write(self.root / ".runtime" / f"{name}.json", json.dumps(data, indent=2) + "\n")

    # ----------------------------------------------------------------- views

    def state(self, addr: str) -> str:
        if self.running(addr):
            return "running"
        reason = self.paused(addr)
        if reason:
            return f"paused({reason})"
        return "pending" if self.unread(addr) else "idle"

    def _agent_line(self, addr: str) -> str:
        meta, _ = self.charter(addr)
        return (
            f"{addr} [{meta.get('role', '?')}] {self.state(addr)}, budget {self.budget(addr)}, "
            f"open tasks {len(self.open_tasks(addr))}, delegated {len(self.outstanding(addr))}, unread {self.unread(addr)}"
        )

    def tree(self) -> str:
        lines = [f"root (human): unread {self.unread(ROOT)}, delegated {len(self.outstanding(ROOT))}"]
        for a in self.agents():
            meta, _ = self.charter(a)
            name = a.rsplit("/", 1)[-1]
            offered = self.service_names(a)
            lines.append(
                "  " * self.depth(a) + f"{name} [{meta.get('role', '?')}] {self.state(a)}  budget={self.budget(a)} "
                f"open={len(self.open_tasks(a))} delegated={len(self.outstanding(a))} unread={self.unread(a)}"
                + (f" services: {', '.join(offered)}" if offered else "")
            )
        return "\n".join(lines)

    @staticmethod
    def _indent(text: str, n: int) -> str:
        return "\n".join(" " * n + line for line in text.splitlines())

    def _quote(self, m: Message) -> str:
        """Quote a task's body verbatim, so its own headings do not mix with the prompt's structure.

        A very long body is cut like ``Message.render`` does, with the real path of the file to read the rest."""
        where = str(m.path.relative_to(self.root)) if m.path and m.path.is_relative_to(self.root) else None
        return "\n".join(f"> {line}".rstrip() for line in m.cut_body(where=where).strip().splitlines())

    def state_summary(self, addr: str, shown: set[str] | None = None) -> str:
        """The agent's situation. ``shown``: ids of tasks whose full text the caller already prints elsewhere."""
        a = self.require(addr)
        meta, _ = self.charter(a)
        lines = [f"- Address: `{a}`; parent: `{self.parent(a) or '-'}`; role: {meta.get('role', '?')}"]
        if a != ROOT:
            hiring = (
                f"allowed ({len(self.children(a))}/{meta.get('max_children', 5)} reports)"
                if meta.get("can_hire") else "not allowed"
            )
            tools = ", ".join(meta.get("tools") or []) or "none"
            lines.append(f"- Budget: {self.budget(a)} run(s) left (this run already counted). Hiring: {hiring}")
            lines.append(f"- Tools beyond orgmcp: {tools}" + (f"; workspace: {meta['workspace']}" if meta.get("workspace") else ""))
            lines += self._files_lines(a, meta)
        kids = self.children(a)
        lines.append("- Direct reports:" + ("" if kids else " none"))
        lines += [f"  - {self._agent_line(k)}" for k in kids]
        siblings = [s for s in self.children(self.parent(a)) if s != a] if a != ROOT else []
        if siblings:
            lines.append("- Siblings: " + ", ".join(siblings))
        tasks = self.open_tasks(a)
        lines.append("- Open tasks assigned to you:" + ("" if tasks else " none"))
        for t in tasks:
            lines.append(f"  - {t.id} \"{t.title}\" from {t.sender}")
            if t.id in (shown or ()):
                lines.append("    (full text: see the new messages below)")
            else:  # the contract you are accountable for, verbatim
                lines.append(self._indent(self._quote(t), 4))
        blocked = self._blocked_tasks(a)
        if blocked:
            lines.append("- Tasks you reported blocked (not final):")
            for t in blocked:
                lines.append(
                    f"  - {t.id} \"{t.title}\" from {t.sender}: reported blocked; "
                    "you may re-report it once the blocker is resolved"
                )
                if t.id in (shown or ()):
                    lines.append("    (full text: see the new messages below)")
                else:
                    lines.append(self._indent(self._quote(t), 4))
        out = self.outstanding(a)
        lines.append("- Work you delegated that is still outstanding:" + ("" if out else " none"))
        lines += [f"  - {t.id} \"{t.title}\" -> {t.to} ({self.state(t.to) if self.exists(t.to) else 'gone'})" for t in out]
        return "\n".join(lines)

    def tool_names(self, addr: str) -> dict[str, str]:
        """The names under which ``addr`` has orgmcp's ``read`` and ``write`` tools.

        kiro exposes MCP tools by their plain names, so a built-in ``read``/``write`` of the same name SHADOWS the orgmcp
        tool (the agent sees only kiro's; studies/F-read-experiment, F2-tool-names). An agent whose charter holds the
        built-in gets orgmcp's tool as ``org_read`` / ``org_write`` instead; everyone else (and root) keeps the plain names.
        """
        tools = set((self.charter(addr)[0].get("tools") or []) if addr != ROOT else [])
        return {t: (f"org_{t}" if t in tools else t) for t in ("read", "write")}

    def _files_lines(self, addr: str, meta: dict) -> list[str]:
        """The "Files" part of an agent's state: where each kind of path points, and which tool reaches it.

        The orgmcp tools show up in kiro as ``@orgmcp/<tool>``; kiro's built-in ``read``/``write``/``shell`` reach the
        workspace (``read`` also the org, by absolute path). A built-in ``read``/``write`` hides the orgmcp tool of the
        same name, which is then called ``org_read``/``org_write`` (see :meth:`tool_names`): the agent is told which
        name it has. Empty for an agent with no workspace, no inputs and no built-in tools.
        """
        ws, inputs = self.workspace_of(addr), self.inputs_of(addr)
        tools = set(meta.get("tools") or [])
        builtin = sorted(tools & {"read", "write", "shell"})
        if ws is None and not inputs and not builtin:
            return []
        names = self.tool_names(addr)
        rn, wn = names["read"], names["write"]
        lines = [
            "- Files:",
            f"  - orgmcp tools (shown as `@orgmcp/{wn}`, `@orgmcp/{rn}`, ...): paths are relative to the org root; your "
            f"notes and memory: `{addr}/MEMORY.md`, `{addr}/work/` (orgmcp `{wn}` only).",
        ]
        if builtin:
            kinds = ", ".join(f"`{t}`" for t in builtin)
            if not tools & {"read", "write"}:  # only `shell`: no name clash
                reach = "they work on the workspace only and never reach the org. "
                how = "`@orgmcp/write` and read with `@orgmcp/read`, never with the built-in `write`/`read`."
                intro = "have the same short names as orgmcp's but are not the same tools"
            else:
                reach = (
                    "they write and run only in the workspace and never change the org. " if "read" in tools
                    else "they work on the workspace only and never reach the org. "
                )
                intro = "are not orgmcp's tools"
                if "write" in tools:
                    how = (
                        f"`@orgmcp/{wn}`, never with the built-in `write`: kiro's built-in `write` has the name `write`; "
                        f"the orgmcp write tool is `@orgmcp/{wn}` for you: use it for MEMORY.md and org files "
                        "(wherever ORG.md says `@orgmcp/write`, use that name)."
                    )
                else:
                    how = "`@orgmcp/write`, never with the built-in `write`."
                if "read" in tools:
                    how += (
                        " Your `read` is kiro's built-in: it reads org files too, but only by ABSOLUTE path, "
                        f"`{self.root}/<path in the org>` (a relative path starts in your working directory); the orgmcp "
                        f"read tool is `@orgmcp/{rn}` for you (relative org paths; wherever ORG.md says `@orgmcp/read`, "
                        "use that name)."
                    )
                else:
                    how += " Read org files with `@orgmcp/read`."
            lines.append(
                f"  - Do not mix up the two kinds of tools: kiro's built-in {kinds} {intro}: {reach}"
                f"Org files (`{addr}/MEMORY.md`, `{addr}/work/`, anything under `{addr}/`) are written with " + how
            )
        if ws is not None:
            lines.append(
                f"  - Workspace (kiro read/write/shell, and the working directory of kiro tools): `{ws}`; relative "
                "paths in kiro tools resolve there."
            )
        else:
            lines.append(f"  - You have no workspace: kiro tools start in your org directory (`{addr}/`) and cannot write.")
        if inputs:
            lines.append(
                f"  - Read-only inputs (kiro `read` or orgmcp `{rn}` by absolute path): "
                + ", ".join(f"`{p}`" for p in inputs) + ". Never modify them."
            )
        lines.append(
            "  - Never create org files (MEMORY.md, `<address>/...`) in the workspace. Report workspace artifacts by "
            "absolute path."
        )
        if tools & {"read", "write"}:
            lines.append("  - kiro `write` is limited to the workspace and kiro `read` to workspace + inputs + the organization (read-only); other paths are refused.")
        if "shell" in tools:
            lines.append(
                "  - You have `shell`, which the runtime cannot confine: use it only inside your workspace; never write "
                "to inputs, to the org directory, or anywhere else."
            )
        return lines

    def stray_notice(self, addr: str) -> str:
        """The one-time notice for an agent whose built-in ``write`` put org files in its workspace (see the
        scheduler's stray detection). Told once per agent: the ledger entry is marked, nothing is moved or deleted."""
        ledger = self.ledger("strays")
        entry = ledger.get(addr)
        if not isinstance(entry, dict) or entry.get("told") or not entry.get("paths"):
            return ""
        entry["told"] = True
        self.save_ledger("strays", ledger)
        paths = ", ".join(f"`{p}`" for p in entry["paths"][:5])
        wn = self.tool_names(addr)["write"]
        return (
            "# Notice from the runtime (shown once)\n"
            f"A previous run of yours used kiro's built-in `write` and created org files in your WORKSPACE: {paths}. "
            "The organization does not see them, so your org memory and notes are not saved. Move that content into "
            f"your org files now: read it, then save it with `@orgmcp/{wn}` (e.g. path=\"{addr}/MEMORY.md\" or "
            f"\"{addr}/work/...\"). Use `@orgmcp/{wn}` for every org file from now on; the built-in `write` is for the "
            "workspace only. The runtime does not move or delete those files; if they are real workspace "
            "deliverables, ignore this."
        )

    def _blocked_tasks(self, addr: str) -> list[Message]:
        """Tasks assigned to ``addr`` whose latest result is ``blocked``: answered, but they may be reported again."""
        latest = latest_results(self.sent(addr))
        return [t for t in self.received(addr) if t.type == "task" and (r := latest.get(t.id)) and r.status == "blocked"]

    def whoami(self, addr: str) -> str:
        a = self.require(addr)
        _, charter = self.charter(a)
        return f"{self.state_summary(a)}\n\n## Charter\n{charter or '(root has no charter)'}"

    def _render_in_context(self, addr: str, m: Message) -> str:
        """A batch message; a result is followed by the task it answers, so it is judged against what was asked."""
        text = m.render()
        if m.type != "result" or not m.reply_to:
            return text
        task = next((t for t in self.sent(addr) if t.type == "task" and t.id == m.reply_to), None)
        if task is None:
            return text
        out = (
            f"{text}\n[The task you delegated to {task.to} that this result answers ({task.id}). "
            f"Judge the result against these criteria, verbatim:]\n{self._quote(task)}\n"
        )
        # Which of your own tasks does it serve? Derivable only if exactly one was already yours at the time.
        up = self._upstream(addr, task)
        if up is not None:
            mine, reported = up
            if reported is None:
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your open task "
                    f"{mine.id} \"{mine.title}\": the result must also satisfy that task's criteria (shown in full in this prompt).]\n"
                )
            elif reported.status == "blocked":
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your task "
                    f"{mine.id} \"{mine.title}\", which you already reported blocked. That is not final: you may `report` "
                    "it again, once, if the blocker is resolved (its criteria are shown in your state). The new report must meet "
                    "rule 6: `done` only if every criterion is met and verified by you, including any required review of "
                    "the FINAL version, not an earlier draft; otherwise report `blocked` or `failed`. Do not claim in a note "
                    "that criteria are met.]\n"
                )
            else:
                out += (
                    f"[It was the only task assigned to you before you delegated this, so it probably serves your task "
                    f"{mine.id} \"{mine.title}\", which you already reported {reported.status}: that is final. Do not claim "
                    "in a note that its criteria are met or try to change its outcome; if you have information for "
                    f"{mine.sender}, send it as information only, saying what was and was not verified.]\n"
                )
        return out

    def _upstream(self, addr: str, delegated: Message) -> tuple[Message, Message | None] | None:
        """The one task of ``addr`` that a delegation probably serves, with its latest result (None = still open).

        A candidate was assigned before the delegation and is open, reported ``blocked`` or was reported only after
        the delegation. None when there is not exactly one candidate.
        """
        latest = latest_results(self.sent(addr))
        found = [
            (t, latest.get(t.id)) for t in self.received(addr)
            if t.type == "task" and t.id < delegated.id
            and ((r := latest.get(t.id)) is None or r.status == "blocked" or r.id > delegated.id)
        ]
        return found[0] if len(found) == 1 else None

    def run_prompt(self, addr: str, batch: list[Message]) -> str:
        a = self.require(addr)
        _, charter = self.charter(a)
        memory = self.memory(a).strip() or "(empty: this may be your first run)"
        cap, words = int(self.config["memory_max_words"]), len(memory.split())
        if words > cap:
            memory += (
                f"\n\n**Your memory is {words} words, over the {cap}-word limit, and writes that keep it over "
                f"the limit are refused. This run, condense it: rewrite {a}/MEMORY.md (not append) with only what "
                "your next run needs; move detail into files under your work/ directory.**"
            )
        messages = "\n".join(self._render_in_context(a, m) for m in batch) or "(none)"
        shown = {m.id for m in batch if m.type == "task"}
        wn = self.tool_names(a)["write"]
        notice = self.stray_notice(a)
        notice = f"\n{notice}\n" if notice else ""
        if self.service_names(a):  # only agents that offer a service get these sections
            from . import services

            notice += services.prompt_sections(self, a, batch)
        return f"""# orgmcp run: you are `{a}`

{self.rules()}

# Your charter ({a}/AGENT.md, owned by your parent)
{charter}

# Your memory ({a}/MEMORY.md)
{memory}

# Your state
{self.state_summary(a, shown)}
- Paths: every path (read, write, artifacts) is relative to the org root. Yours start with `{a}/`.
{notice}
# New messages for this run ({len(batch)})
{messages}
---
Handle every new message above with the orgmcp tools, following the protocol.
Messages may be redelivered after a crash: if your state shows one was already handled, skip it.
Before you stop, update your memory with `@orgmcp/{wn}`(path="{a}/MEMORY.md", ...) (the orgmcp tool, not a built-in `write`). Do not wait for replies; end the run when done.
"""
