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
  - budget = budget received - budget handed down - runs consumed (files in ``runs/``).
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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import yaml

from . import templates

ROOT = "root"
RUNTIME = "runtime"
BOXES = ("inbox", "inflight", "read", "sent")
RUNTIME_NAMES = {*BOXES, "runs", ".paused", ".kiro", ".runtime", ".retired", ".git", ".gitignore"}
RESERVED = RUNTIME_NAMES | {"work", "root", "runtime", "agent", "memory", "org"}
# Always use NAME_RE.fullmatch: a "$" anchor would accept a trailing newline ("ops\n"), so \Z is used as well.
NAME_RE = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")
MESSAGE_TYPES = ("task", "result", "note")
RESULT_STATUSES = ("done", "failed", "blocked")
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
    "default_budget": 10,  # runs given with a task when none is specified
    "memory_max_words": 800,  # cap on an agent's MEMORY.md; writes that exceed it are refused
    "default_model": None,  # kiro model; None = kiro default
    "max_message_chars": 20000,  # longest message body send/delegate/report accept; detail goes in a file
}
RENDER_BODY_CHARS = 8000  # longer bodies are cut when shown to an agent (prompt, inbox tool); the file has the rest


class OrgError(ValueError):
    """A rule of the organization was violated. The message is shown to the agent."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)  # libyaml when available: same result, ~10x faster


def split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            meta = yaml.load(text[4:end], Loader=_YAML_LOADER) or {}
            return (meta if isinstance(meta, dict) else {}), text[end + 5 :]
    return {}, text


def _message_cap(config: dict) -> int:
    """``max_message_chars`` from ORG.md; a malformed value means the default."""
    try:
        cap = int(config["max_message_chars"])
    except (TypeError, ValueError):
        return int(DEFAULT_CONFIG["max_message_chars"])
    return cap if cap > 0 else int(DEFAULT_CONFIG["max_message_chars"])


def join_frontmatter(meta: dict, body: str) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n" + body.rstrip() + "\n"


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


_FENCE_LINE = re.compile(r"\s*(?:`{3,}|~{3,})\S*\s*")
_LINE_MARKER = re.compile(r"\s*(?:>|#{1,6}(?=\s)|[-*+\u2022](?=\s)|\d{1,3}[.)](?=\s)|\[[ xX]\](?=\s))")
_MARKUP_ONLY = re.compile(r"[#*+=_~`>|:\-\u2022]+")


def word_count(text: str) -> int:
    """Words of ``text`` for word limits: markdown markers (``#``, ``-``, ``*``, ``1.``, ``|``, ``---``, fence lines,
    ``>``, checkboxes) are not words; the words next to them are."""
    total = 0
    for line in text.splitlines():
        if _FENCE_LINE.fullmatch(line):
            continue
        if line.lstrip().startswith("|"):  # table row: the pipes are delimiters
            line = line.replace("|", " ")
        while (m := _LINE_MARKER.match(line)) and m.end() > 0:
            line = line[m.end():]
        total += sum(1 for tok in line.split() if not _MARKUP_ONLY.fullmatch(tok))
    return total


def _visible(paths) -> list[Path]:
    return sorted(p for p in paths if not p.name.startswith("."))


_PARSED: OrderedDict[str, tuple[tuple[int, int], dict, str]] = OrderedDict()  # Message.load cache (LRU)
_PARSED_MAX = 50_000


@dataclass
class Message:
    sender: str
    to: str
    type: str
    body: str
    title: str = ""
    reply_to: str | None = None
    status: str | None = None
    budget: int = 0
    hops: int = 0
    revises: str | None = None  # a task sent back for rework: the earlier task it revises
    id: str = ""
    created: str = ""
    path: Path | None = field(default=None, compare=False, repr=False)

    def meta(self) -> dict:
        meta = {
            "id": self.id,
            "from": self.sender,
            "to": self.to,
            "type": self.type,
            "title": self.title,
            "created": self.created,
            "hops": self.hops,
        }
        if self.reply_to:
            meta["reply_to"] = self.reply_to
        if self.status:
            meta["status"] = self.status
        if self.budget:
            meta["budget"] = self.budget
        if self.revises:
            meta["revises"] = self.revises
        return meta

    def to_text(self) -> str:
        return join_frontmatter(self.meta(), self.body)

    @classmethod
    def load(cls, path: Path) -> Message:
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
        return cls(
            sender=str(meta.get("from", "")),
            to=str(meta.get("to", "")),
            type=str(meta.get("type", "note")),
            body=body.strip(),
            title=str(meta.get("title") or ""),
            reply_to=meta.get("reply_to"),
            status=meta.get("status"),
            budget=int(meta.get("budget") or 0),
            hops=int(meta.get("hops") or 0),
            revises=str(meta["revises"]) if meta.get("revises") else None,
            id=str(meta.get("id") or path.stem),
            created=str(meta.get("created") or ""),
            path=path,
        )

    def cut_body(self, limit: int = RENDER_BODY_CHARS, where: str | None = None) -> str:
        """The body, cut to ``limit`` characters with a pointer to the file for the rest.

        ``where`` = path of the file relative to the org root; by default derived from the recipient's box.
        """
        body = self.body
        if limit and len(body) > limit:
            if where is None:
                where = f"{self.to}/" if self.to != ROOT else ""
                where += f"{self.path.parent.name}/{self.path.name}" if self.path else f"<box>/{self.id}.md"
            body = (
                body[:limit].rstrip()
                + f"\n\n[... message cut: {len(self.body) - limit} more of {len(self.body)} characters. "
                f"Read the rest with read(path=\"{where}\") if you need it.]"
            )
        return body

    def render(self, limit: int = RENDER_BODY_CHARS) -> str:
        """The message as shown to an agent. A body over ``limit`` characters is cut, with the path to read the rest."""
        head = [f"from: {self.sender}", f"to: {self.to}"]
        if self.title:
            head.append(f"title: {self.title}")
        if self.reply_to:
            head.append(f"reply_to: {self.reply_to}")
        if self.status:
            head.append(f"status: {self.status}")
        if self.revises:
            head.append(f"revises: {self.revises}")
        if self.budget:
            head.append(f"budget: {self.budget} runs")
        body = self.cut_body(limit)
        return f"### {self.type} {self.id}\n" + " | ".join(head) + f"\n\n{body}\n"


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
        (root / ".gitignore").write_text(".tmp-*\nruns/\n.kiro/\n.runtime/scheduler.pid\n", encoding="utf-8")
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
        a = (addr or "").strip().strip("/")
        return ROOT if a in ("", ROOT) else a

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
        a = cls.norm(addr)
        if a == ROOT:
            return None
        return a.rsplit("/", 1)[0] if "/" in a else ROOT

    @classmethod
    def depth(cls, addr: str) -> int:
        a = cls.norm(addr)
        return 0 if a == ROOT else a.count("/") + 1

    def child_addr(self, parent: str, name: str) -> str:
        return name if self.norm(parent) == ROOT else f"{self.norm(parent)}/{name}"

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
        d = self.dir(addr) / "inbox"
        return len(_visible(d.glob("*.md"))) if d.is_dir() else 0

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

    def deliver(self, msg: Message) -> Message:
        """Low level: assign an id and write the message. Policy is checked by the callers."""
        msg.id = msg.id or self.new_id(msg.sender)
        msg.created = msg.created or utcnow().isoformat(timespec="seconds")
        text = msg.to_text()
        # Sender's copy first: it is what charges a budget grant. A failure between the two writes can then only
        # leave a message charged but undelivered (recover() re-delivers it), never delivered but uncharged.
        if msg.sender != RUNTIME:
            atomic_write(self.dir(msg.sender) / "sent" / f"{msg.id}.md", text)
        atomic_write(self.dir(msg.to) / "inbox" / f"{msg.id}.md", text)
        return msg

    def notify(self, to: str, title: str, body: str) -> Message:
        """A notice from the runtime itself (budget, failures, stalls)."""
        return self.deliver(Message(sender=RUNTIME, to=self.norm(to), type="note", title=title, body=body))

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
        if budget and actor != ROOT and self.parent(to) != actor:
            raise OrgError("budget can only be handed to your direct reports")
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
        return self.send(actor, to, body, type="task", title=title, budget=budget, revises=revises or None)

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
        """Resolve an artifact path and annotate it with facts a manager can check claims against."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = next((b / p for b in (self.root, self.dir(actor)) if (b / p).exists()), self.root / p)
        p = p.resolve()
        if p != self.root and self.root not in p.parents:  # checked before existence: no probing of the host
            raise OrgError(f"artifacts must be inside the organization: {path} (paths are relative to the org root)")
        if not p.exists():
            raise OrgError(f"artifact not found: {path} (paths are relative to the org root)")
        shown = str(p.relative_to(self.root))
        if p.is_dir():
            return f"{shown}/ (directory)"
        modified = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        note = f"{word_count(p.read_text(encoding='utf-8', errors='replace'))} words, modified {modified:%H:%M:%S} UTC"
        if since and modified.isoformat(timespec="seconds") < since:
            note += ", NOT modified since this task was assigned"
        return f"{shown} ({note})"

    def report(self, actor: str, task_id: str, status: str, summary: str, artifacts: list[str] | None = None) -> Message:
        actor = self.require(actor)
        if status not in RESULT_STATUSES:
            raise OrgError(f"status must be one of {RESULT_STATUSES}")
        task = self.find_received(actor, task_id)
        if task is None or task.type != "task":
            open_ids = ", ".join(t.id for t in self.open_tasks(actor)) or "none"
            raise OrgError(f"no task {task_id} assigned to you. Your open tasks: {open_ids}")
        if any(m.type == "result" and m.reply_to == task_id for m in self.sent(actor)):
            raise OrgError(f"task {task_id} was already reported")
        arts = [self._normalize_artifact(actor, a, task.created) for a in (artifacts or [])]
        body = templates.result_body(summary, arts)
        return self.send(
            actor, task.sender, body, type="result", title=task.title,
            reply_to=task.id, status=status, _skip_route_check=True,
        )

    def hire(
        self,
        actor: str,
        name: str,
        role: str,
        charter: str,
        *,
        model: str | None = None,
        tools: list[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
    ) -> str:
        actor = self.require(actor)
        if not NAME_RE.fullmatch(name) or name in RESERVED:
            raise OrgError("name must be lowercase letters, digits and dashes (max 32), and not a reserved word")
        tools = sorted(set(tools or []))
        meta, _ = self.charter(actor)
        if actor != ROOT:
            if not meta.get("can_hire"):
                raise OrgError("your charter does not allow hiring")
            if len(self.children(actor)) >= int(meta.get("max_children", 5)):
                raise OrgError(f"you already have the maximum of {meta.get('max_children', 5)} direct reports")
            self._check_authority(actor, tools, workspace)
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
            "hired_by": actor,
            "created": utcnow().isoformat(timespec="seconds"),
        }
        child_meta = {k: v for k, v in child_meta.items() if v is not None}
        for sub in (*BOXES, "work", "runs"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        atomic_write(d / "MEMORY.md", "")
        atomic_write(d / "AGENT.md", join_frontmatter(child_meta, templates.charter_body(role, charter)))
        return addr

    def _check_authority(self, actor: str, tools: list[str], workspace: str | None) -> None:
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

    def retire(self, actor: str, name: str, reason: str) -> str:
        """Remove a direct report and its team; returns the retired address. See :meth:`retire_team`."""
        return self.retire_team(actor, name, reason).addr

    def retire_team(self, actor: str, name: str, reason: str) -> Retired:
        """Retire a direct report (short name or full address; root: any agent by full address) and its team.

        Open tasks the team owes the outside are closed as failed, and the team's unspent budget is returned to the
        retired agent's parent as a runtime note carrying the budget (nothing when the parent is root, who has no
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
                sender=RUNTIME, to=parent, type="note", budget=refund, title=f"Budget returned from {addr}",
                body=templates.notice_budget_returned(addr, refund, actor, reason),
            ))
        return Retired(addr, refund, parent if refund else None)

    # ------------------------------------------------------------- file access

    def resolve_read(self, path: str) -> Path:
        p = (self.root / path.lstrip("/")).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        if p != self.root and self.root not in p.parents:
            raise OrgError("you can only read inside the organization")
        return p

    def read(self, path: str) -> str:
        p = self.resolve_read(path or ".")
        if p.is_dir():
            entries = [f"{c.name}/" if c.is_dir() else c.name for c in _visible(p.iterdir())]
            return "\n".join(entries) or "(empty directory)"
        if not p.is_file():
            raise OrgError(f"not found: {path} (paths are relative to the org root)")
        text = p.read_text(encoding="utf-8", errors="replace")
        modified = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
        head = f"[{p.relative_to(self.root)}: {word_count(text)} words, {text.count(chr(10))} lines, modified {modified:%H:%M:%S} UTC]\n"
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
        actor = self.require(actor)
        p = self.resolve_write(actor, path)
        if p.name == "AGENT.md" and actor != ROOT:  # a parent editing a report's charter
            meta, _ = split_frontmatter(content)
            if not meta.get("role"):
                raise OrgError("a charter needs YAML frontmatter with at least `role:`")
            self._check_authority(actor, list(meta.get("tools") or []), meta.get("workspace"))
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
        return p

    # ------------------------------------------------------------ run lifecycle

    def begin_run(self, addr: str) -> list[Message]:
        """Move the inbox into inflight/: that batch is what this run handles."""
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

    def pause(self, addr: str, reason: str) -> None:
        (self.dir(addr) / ".paused").write_text(reason, encoding="utf-8")

    def resume(self, addr: str) -> None:
        (self.dir(addr) / ".paused").unlink(missing_ok=True)

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
            lines.append(
                "  " * self.depth(a) + f"{name} [{meta.get('role', '?')}] {self.state(a)}  budget={self.budget(a)} "
                f"open={len(self.open_tasks(a))} delegated={len(self.outstanding(a))} unread={self.unread(a)}"
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
        out = self.outstanding(a)
        lines.append("- Work you delegated that is still outstanding:" + ("" if out else " none"))
        lines += [f"  - {t.id} \"{t.title}\" -> {t.to} ({self.state(t.to) if self.exists(t.to) else 'gone'})" for t in out]
        return "\n".join(lines)

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
        # Which of your own open tasks does it serve? Derivable only if exactly one was already yours at the time.
        mine = [t for t in self.open_tasks(addr) if t.id < task.id]
        if len(mine) == 1:
            out += (
                f"[It was the only task assigned to you before you delegated this, so it probably serves your open task "
                f"{mine[0].id} \"{mine[0].title}\": the result must also satisfy that task's criteria (shown in full in this prompt).]\n"
            )
        return out

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
        return f"""# orgmcp run: you are `{a}`

{self.rules()}

# Your charter ({a}/AGENT.md, owned by your parent)
{charter}

# Your memory ({a}/MEMORY.md)
{memory}

# Your state
{self.state_summary(a, shown)}
- Paths: every path (read, write, artifacts) is relative to the org root. Yours start with `{a}/`.

# New messages for this run ({len(batch)})
{messages}
---
Handle every new message above with the orgmcp tools, following the protocol.
Messages may be redelivered after a crash: if your state shows one was already handled, skip it.
Before you stop, update your memory with write(path="{a}/MEMORY.md", ...). Do not wait for replies; end the run when done.
"""
