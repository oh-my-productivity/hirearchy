"""MCP server: the organization's system calls.

Identity is assigned, not claimed: the scheduler starts each run with ORG_AGENT=<address>.
Without ORG_AGENT (e.g. registered in your own kiro mcp.json) you act as `root`, the human.

A root server may start before any organization exists (setup mode): it then offers `create_org` and every other
tool answers "no organization yet". The server is bound to exactly one root path for its lifetime and never
falls back to another organization. Agent servers (ORG_AGENT set) still fail fast without an organization.
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .core import ROOT, Org, OrgError
from .health import org_health, render_text
from .scheduler import describe_scheduler, start_scheduler, stop_scheduler

INSTRUCTIONS = """\
You are a member of a file-based organization of agents. Your identity is fixed by the runtime.
Work flows down as tasks (delegate), results flow up (report), everything else is a note (send).
Call whoami first if you do not know your role, reports, budget and open tasks.
"""

ROOT_INSTRUCTIONS = """\
You are connected to ONE orgmcp organization as `root`, the human's seat. {where}
- Use only this organization. Never look for, create or modify any other one (no other paths, no shell or CLI
  workarounds, no changing ORG_ROOT).
- Never claim the organization did work unless orgmcp tools show it (status, inbox, read, health).
- If an orgmcp tool fails, tell the user what failed instead of substituting another mechanism (for example a
  generic subagent tool).
- Work flows down as tasks (delegate), results flow up (report), everything else is a note (send). `whoami` and
  `status` show the current state; `start` and `stop` control the scheduler that wakes the agents.
"""

DS_STORE = ".DS_Store"


class OrgBinding:
    """The one organization root path a server is bound to, and the organization there once it exists.

    ``get()`` is the lazily resolved accessor every tool (and later modules) should use: it returns the
    ``Org`` or raises a clear ``OrgError`` while none exists yet. ``root`` is None only when ORG_ROOT is unset and
    no organization was found from the working directory; ``create_org(path=...)`` then binds it, once.
    """

    def __init__(self, root: Path | None, org: Org | None = None, pinned: bool = False):
        self.root = Path(root) if root is not None else None
        self.pinned = pinned  # bound by ORG_ROOT: create_org may not choose another path
        self._org = org

    def peek(self) -> Org | None:
        """The organization if it exists (now), else None."""
        if self._org is None and self.root is not None:
            try:
                self._org = Org(self.root)
            except OrgError:
                return None
        return self._org

    def get(self) -> Org:
        org = self.peek()
        if org is None:
            raise OrgError(self.missing_message())
        return org

    def missing_message(self) -> str:
        if self.root is None:
            return ("no organization found (ORG_ROOT is not set and none exists in the working directory): "
                    "call create_org(mission=..., path=<absolute path>) first")
        if self._blocked():
            return (f"no organization at {self.root}: the directory exists, is not empty and has no ORG.md, so "
                    "create_org will refuse to use it. Point ORG_ROOT at an empty or missing directory")
        return f"no organization at {self.root} yet: call create_org(mission=...) first"

    def _blocked(self) -> bool:
        return self.root is not None and (self.root.is_file() or bool(_entries(self.root)))

    def create(self, mission: str, default_model: str | None = None, path: str | None = None) -> Org:
        existing = self.peek()
        if existing is not None:
            raise OrgError(f"an organization already exists at {existing.root}; nothing was created. "
                           "It is ready to use: call whoami or status")
        if not (mission or "").strip():
            raise OrgError("mission is required: say in a few sentences what the organization is for")
        wanted = Path(path).expanduser() if path else None
        if wanted is not None and not wanted.is_absolute():
            raise OrgError(f"path must be absolute (got {path!r})")
        wanted = wanted.resolve() if wanted is not None else None
        if self.root is not None:
            if wanted is not None and wanted != self.root:
                raise OrgError(f"this server is bound to {self.root} and cannot create an organization at {wanted}. "
                               "Omit path, or ask the user to register orgmcp with ORG_ROOT set to that path")
            target = self.root
        elif wanted is None:
            raise OrgError("ORG_ROOT is not set and no organization was found here: "
                           "call create_org(mission=..., path=<absolute path>)")
        else:
            target = wanted
            if (target / "ORG.md").is_file():
                raise OrgError(f"an organization already exists at {target}, but this server is not bound to it, "
                               "so it will not be used. Ask the user to register orgmcp with "
                               f"ORG_ROOT={target}")
        if target.is_file():
            raise OrgError(f"{target} is a file, not a directory; nothing was created")
        found = _entries(target)
        if found:
            raise OrgError(f"{target} is not empty ({', '.join(found[:5])}{', ...' if len(found) > 5 else ''}) and is not "
                           "an organization; nothing was created. Use an empty or missing directory")
        try:
            org = Org.init(target, mission.strip(), {"default_model": default_model} if default_model else None)
        except OSError as exc:
            raise OrgError(f"could not create the organization at {target}: {exc}") from exc
        self.root, self._org = target, org
        return org


def _entries(directory: Path) -> list[str]:
    try:
        return sorted(p.name for p in directory.iterdir() if p.name != DS_STORE)
    except OSError:  # missing (or unreadable: create will fail with its own error)
        return []


def root_instructions(binding: OrgBinding) -> str:
    org = binding.peek()
    if org is not None:
        where = f"The organization is at {org.root}."
    elif binding.root is not None:
        where = (f"No organization exists at {binding.root} yet: the first step is create_org(mission=...), "
                 "after which all tools work.")
    else:
        where = ("No organization exists and none is bound: the first step is create_org(mission=..., "
                 "path=<absolute path>), after which all tools work.")
    return ROOT_INSTRUCTIONS.format(where=where)


def build_server(org: Org | OrgBinding, me: str) -> FastMCP:
    """The MCP server for ``me``. ``org``: an ``Org``, or an ``OrgBinding`` (root only: it may not exist yet)."""
    binding = org if isinstance(org, OrgBinding) else OrgBinding(org.root, org)
    if binding.peek() is not None:
        me = binding.get().require(me)
    elif Org.norm(me) == ROOT:
        me = ROOT  # setup mode
    else:
        raise OrgError(binding.missing_message())  # agents never run without their organization
    mcp = FastMCP("orgmcp", instructions=root_instructions(binding) if me == ROOT else INSTRUCTIONS)

    @mcp.tool()
    def whoami() -> str:
        """Your address, role, budget, direct reports, open tasks, outstanding delegations and charter."""
        if me == ROOT and binding.peek() is None:
            return setup_state(binding)
        org = binding.get()
        text = org.whoami(me)
        return f"{text}\n\n{describe_scheduler(org)}" if me == ROOT else text

    @mcp.tool()
    def inbox() -> str:
        """The messages for this run. For root (the human) this lists unread messages and marks them read."""
        org = binding.get()
        if me == ROOT:
            batch = org.begin_run(ROOT)
            org.end_run(ROOT, ok=True)
        else:
            batch = org.messages(me, "inflight") or org.messages(me, "inbox")
        return "\n".join(m.render() for m in batch) or "(no new messages)"

    @mcp.tool()
    def delegate(
        to: str,
        title: str,
        goal: str,
        acceptance: str,
        inputs: list[str] | None = None,
        budget: int | None = None,
        revises: str | None = None,
    ) -> str:
        """Assign a task to one of your direct reports.

        to: the report's address (e.g. "ceo/cto"). title: a few words. goal: what outcome is needed and why.
        acceptance: concrete, checkable criteria for "done". inputs: paths (relative to the org root) the
        report should read. budget: runs handed to the report from your own budget. If you omit it, the default is
        min(default_budget from ORG.md, your budget - reserve), where the reserve keeps one run per outstanding
        delegation plus one for this one; if that is below 1 the call fails and tells you your options.
        An explicit budget must leave that same reserve.
        Copy the relevant acceptance criteria verbatim from the task you are working on; never paraphrase or relax them.
        revises: when sending work back for rework, the id of the earlier task you sent to the same report.
        Returns the task id. Do not wait for the result: end your run, the result will wake you.
        """
        org = binding.get()
        msg = org.delegate(me, to, title, goal, acceptance, inputs or [], budget, revises)
        return f"delegated {msg.id} to {msg.to} with budget {msg.budget}. Your budget is now {org.budget(me)}."

    @mcp.tool()
    def report(task_id: str, status: str, summary: str, artifacts: list[str] | None = None) -> str:
        """Answer a task assigned to you. Goes to whoever assigned it.

        status: "done" (every acceptance criterion verifiably met), "failed", or "blocked" (say what would unblock it).
        `done` and `failed` are final: a second report is refused. `blocked` is not: once the blocker is resolved
        you may report the task again, once per blocked report (any status; the new report supersedes the old one),
        under the same rules. A `send` note never changes a task's outcome and must not claim criteria are met.
        summary: at most ~10 lines; this is all your manager reads by default. artifacts: paths of the
        files that hold the work (relative to the org root); they must exist. The runtime annotates each
        with its word count and whether it changed since the task was assigned.
        """
        org = binding.get()
        msg = org.report(me, task_id, status, summary, artifacts or [])
        return f"reported {status} on {task_id} to {msg.to}"

    @mcp.tool()
    def send(to: str, body: str, title: str = "", reply_to: str | None = None, budget: int = 0) -> str:
        """Send a note: a question, information, or an escalation.

        Allowed recipients: your parent, your direct reports, your siblings, or the sender of the message
        you reply to (set reply_to to its id). budget: extra runs to grant a direct report (optional).
        """
        org = binding.get()
        msg = org.send(me, to, body, title=title, reply_to=reply_to, budget=budget)
        return f"sent {msg.id} to {msg.to}"

    @mcp.tool()
    def hire(
        name: str,
        role: str,
        charter: str,
        model: str | None = None,
        tools: list[str] | None = None,
        can_hire: bool = False,
        max_children: int = 5,
        workspace: str | None = None,
    ) -> str:
        """Create a direct report (only if your charter allows hiring).

        name: lowercase-dashed (becomes the address <you>/<name>). role: a short job title.
        charter: markdown with purpose, responsibilities, decision rights, what to escalate, quality bar.
        model: kiro model id (optional). tools: kiro built-in tools to grant, only ones you have yourself
        (e.g. "read", "write", "shell"). can_hire: whether the report may build its own team.
        workspace: directory the report works in (must be inside yours).
        A new report has no budget until you delegate a task to it.
        """
        org = binding.get()
        addr = org.hire(me, name, role, charter, model=model, tools=tools or [], can_hire=can_hire,
                        max_children=max_children, workspace=workspace)
        return f"hired {addr}"

    @mcp.tool()
    def retire(name: str, reason: str) -> str:
        """Remove a direct report and its team (name: its short name or full address, e.g. "eng" or "ceo/eng").

        Their open tasks are reported to you as failed, and the team's unspent budget is returned to you.
        """
        org = binding.get()
        r = org.retire_team(me, name, reason)
        refund = f"; {r.refunded} unspent run(s) of budget returned to {r.refunded_to}" if r.refunded else ""
        return f"retired {r.addr}{refund}"

    @mcp.tool()
    def read(path: str = ".") -> str:
        """Read a file (with word count and modification time) or list a directory anywhere in the
        organization. Paths are relative to the org root, e.g. "ceo/writer/work/brief.md"."""
        return binding.get().read(path)

    @mcp.tool()
    def write(path: str, content: str, append: bool = False) -> str:
        """Write a file inside your own directory. Paths are relative to the org root, like every path here,
        so they start with your address: e.g. "<you>/MEMORY.md" or "<you>/work/plan.md".

        You may also rewrite a direct report's charter ("<you>/<name>/AGENT.md"). Inboxes, logs and your own
        charter are managed by the runtime; use send/delegate/report to communicate.
        """
        org = binding.get()
        p = org.write(me, path, content, append=append)
        return f"wrote {p.relative_to(org.root)}"

    @mcp.tool()
    def status() -> str:
        """The whole organization as a tree: each agent's role, state, budget and workload."""
        if me == ROOT and binding.peek() is None:
            return setup_state(binding)
        org = binding.get()
        return f"{org.tree()}\n\n{describe_scheduler(org)}" if me == ROOT else org.tree()

    @mcp.tool()
    def health(agent: str | None = None) -> str:
        """Health report (stuck, expensive, low-quality, wasteful, idle, paused) for an agent and its subtree.

        agent: yourself or an agent in your own subtree (root may ask about anyone). Default: your own subtree
        (root: the whole organization). Use it to decide whom to follow up with, rework, re-budget or retire.
        """
        org = binding.get()
        target = org.require(agent or me)
        if me != ROOT and target not in org.subtree(me):
            raise OrgError(f"you can only view health for yourself or agents in your own subtree ({me}/...), not {target}")
        return render_text(org_health(org, target))

    if me == ROOT:
        register_root_tools(mcp, binding)
    return mcp


def setup_state(binding: OrgBinding) -> str:
    """What whoami/status say before an organization exists."""
    where = f"at {binding.root}" if binding.root is not None else "(none found: ORG_ROOT is not set)"
    path_arg = "" if binding.root is not None else ", path=<absolute path>"
    return (f"Setup: no organization exists {where} yet.\n"
            f"Next step: call create_org(mission=\"...\"{path_arg}) to create it; then hire a team, delegate "
            "work and start() the scheduler. Until then every other tool returns an error.\n"
            "scheduler: stopped")


def register_root_tools(mcp: FastMCP, binding: OrgBinding) -> None:
    """The tools only the human's (root) server has. Add new root-only tools here, resolving the organization
    with ``binding.get()`` at call time (it may not exist yet when the server starts)."""

    @mcp.tool()
    def create_org(mission: str, default_model: str | None = None, path: str | None = None) -> str:
        """Create the organization this server is bound to (only possible while none exists).

        mission: what the organization is for, in a few sentences. default_model: kiro model for all agents
        (optional). path: absolute directory; only needed (and only accepted) when the server is not bound to
        one by ORG_ROOT. The directory must be missing or empty. Afterwards every tool works, no restart needed.
        """
        org = binding.create(mission, default_model, path)
        return (f"created the organization at {org.root}. Next: hire a team (hire), give it work (delegate), then "
                "start() the scheduler. Use only this organization.")

    @mcp.tool()
    def start(max_runs: int | None = None) -> str:
        """Start the scheduler for this organization in the background; it wakes agents that have mail.

        max_runs: stop starting agent runs after this many (safety cap; default: no cap). Refused if one is
        already running. Output goes to .runtime/scheduler.log. Returns the scheduler's pid.
        """
        org = binding.get()
        pid = start_scheduler(org, max_runs)
        cap = f", at most {max_runs} run(s)" if max_runs is not None else ""
        return f"scheduler started (pid {pid}{cap}); log: {org.root / '.runtime' / 'scheduler.log'}"

    @mcp.tool()
    def stop() -> str:
        """Stop this organization's scheduler (SIGTERM, then wait briefly). Runs in flight are interrupted and
        redelivered on the next start. Only signals a process verified to be this organization's scheduler."""
        return stop_scheduler(binding.get())


def resolve_binding() -> tuple[OrgBinding, str]:
    """From the environment: the organization this server is bound to, and who it acts as.

    * ORG_REQUIRE_AGENT=1 (set in the profiles the scheduler writes): ORG_AGENT must name an agent, otherwise the
      server refuses to start, so a profile used outside the scheduler fails closed instead of acting as root.
    * ORG_AGENT set: an agent; the organization must exist (fail fast, as always).
    * otherwise: root. ORG_ROOT (or the organization found from the working directory) is the bound path, whether
      or not an organization exists there yet.
    """
    agent = (os.environ.get("ORG_AGENT") or "").strip()
    if os.environ.get("ORG_REQUIRE_AGENT", "").strip().lower() not in ("", "0", "false", "no"):
        if not agent or Org.norm(agent) == ROOT:
            raise OrgError(
                "ORG_REQUIRE_AGENT is set but ORG_AGENT does not name an agent: this is an internal profile of the "
                "orgmcp scheduler and only works when the scheduler starts it. Refusing to act as root. "
                "To manage an organization yourself, register `orgmcp mcp` without ORG_REQUIRE_AGENT")
    if agent:
        org = Org(Org.find_root())  # an agent: no organization means fail fast
        return OrgBinding(org.root, org, pinned=True), agent
    pinned = bool(os.environ.get("ORG_ROOT"))
    try:
        root: Path | None = Org.find_root()
    except OrgError:
        root = None
    return OrgBinding(root, pinned=pinned), ROOT


def serve() -> None:
    binding, me = resolve_binding()
    build_server(binding, me).run()
