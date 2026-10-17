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

import anyio
from mcp.server.fastmcp import FastMCP

from . import blueprint as blueprint_mod
from . import blueprint_examples
from .core import ROOT, Org, OrgError
from .health import org_health, render_text
from .progress import WAIT_MAX, describe_progress
from .scheduler import describe_scheduler, nothing_to_do, scheduler_state, start_scheduler, stop_scheduler

INSTRUCTIONS = """\
You are a member of a file-based organization of agents. Your identity is fixed by the runtime.
Work flows down as tasks (delegate), results flow up (report), everything else is a note (send).
Call whoami first if you do not know your role, reports, budget and open tasks.
"""

ROOT_INSTRUCTIONS = """\
You are connected to ONE orgmcp organization as `root`, the human's seat. {where}
- Use only this organization. Never look for, create or modify any other one (no other paths, no shell or CLI
  workarounds, no changing ORG_ROOT).
- Never claim the organization did work unless orgmcp tools show it (status, progress, inbox, read, health).
- If an orgmcp tool fails, tell the user what failed instead of substituting another mechanism (for example a
  generic subagent tool).
- Work flows down as tasks (delegate), results flow up (report), everything else is a note (send). `whoami` and
  `status` show the current state; `start` and `stop` control the scheduler that wakes the agents.
When the user asks for an org, team or agents for a goal:
1. Ask what you need in ONE message. Propose defaults only where a generic one exists; a list the user did not give
   (scope items, competitors, features, source files) you ASK for, never invent. Default deliverable place: a new
   `deliverables/` folder in the user's current directory, stated plainly. Also ask: format, length, exact checkable
   acceptance criteria, sources/web, workspace and tests (code), budget in runs, models, review, approval.
2. Start the blueprint from `blueprint_example(kind)` (research | documents | code), then call `propose_org`. Show the
   "PLAN FOR YOU" block exactly as returned and wait for the user's explicit approval. Fix errors; revise on feedback.
3. After approval: `create_org` (if none exists), `apply_org(blueprint, approved=True, plan_id=<from propose_org>)`,
   `start`. Spend beyond the plan needs their OK.
4. Answer "status?" with `progress`. Never promise to tell the user later (a turn ends when you reply): if they want
   to be told when it is done, say you will wait now and call `progress(wait_seconds=N)`, repeating as they wish;
   otherwise tell them to ask "status?". Relay escalations with a recommended decision.
5. When it is done: read the deliverable and check it against EVERY acceptance criterion (send it back with
   `delegate(..., revises=...)` if not; never patch it yourself), copy it where the user wants it. `start` ends by
   itself when the work is done (start again after giving it more work); `stop` only if the user cancels.
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
        files that hold the work; they must exist. Files in the organization: path relative to the org root.
        Files in your workspace: the ABSOLUTE path (anything else outside the organization is refused). The runtime
        annotates each with its word count and whether it changed since the task was assigned.
        """
        org = binding.get()
        msg = org.report(me, task_id, status, summary, artifacts or [])
        returned = f"; returned {msg.budget} unspent run(s) of budget to {msg.to}" if msg.budget else ""
        return f"reported {status} on {task_id} to {msg.to}{returned}"

    @mcp.tool()
    def send(to: str, body: str, title: str = "", reply_to: str | None = None, budget: int = 0) -> str:
        """Send a note: a question, information, or an escalation.

        Allowed recipients: your parent, your direct reports, your siblings, or the sender of the message
        you reply to (set reply_to to its id). budget: runs to move along with the note (optional): extra runs
        granted to a direct report, or unneeded runs given back to your PARENT (never to a sibling). Runs you
        have left return to your parent by themselves with your final `done`/`failed` report when nothing else
        is open for you; use this only to give some back earlier.
        """
        org = binding.get()
        msg = org.send(me, to, body, title=title, reply_to=reply_to, budget=budget)
        moved = f" with {msg.budget} run(s) of budget" if msg.budget else ""
        return f"sent {msg.id} to {msg.to}{moved}"

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
        inputs: list[str] | None = None,
    ) -> str:
        """Create a direct report (only if your charter allows hiring).

        name: lowercase-dashed (becomes the address <you>/<name>). role: a short job title.
        charter: markdown with purpose, responsibilities, decision rights, what to escalate, quality bar.
        model: kiro model id (optional). tools: kiro built-in tools to grant, only ones you have yourself
        (e.g. "read", "write", "shell"). can_hire: whether the report may build its own team.
        workspace: directory the report works in (must be inside yours).
        inputs: absolute folders the report may only READ (never change); a manager can give only folders inside its
        own inputs or workspace. A report with `read` and no workspace/inputs reads nothing outside the org.
        A new report has no budget until you delegate a task to it.
        """
        org = binding.get()
        addr = org.hire(me, name, role, charter, model=model, tools=tools or [], can_hire=can_hire,
                        max_children=max_children, workspace=workspace, inputs=inputs)
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
        """Read a file (with word count and modification time) or list a directory in the organization. Paths are
        relative to the org root, e.g. "ceo/writer/work/brief.md". Outside the organization only ABSOLUTE paths work,
        and only inside your workspace, your read-only inputs, or the workspace of an agent in your team (to verify
        what your reports made); anything else is refused."""
        return binding.get().read(path, actor=me)

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
    def start(max_runs: int | None = None, until_done: bool = True) -> str:
        """Start the scheduler for this organization in the background; it wakes agents that have mail.

        max_runs: stop starting agent runs after this many (safety cap; default: no cap). until_done (default True):
        the scheduler exits by itself when you have no open task and nothing is running or can run, so you need not
        stop it (status and progress then say "scheduler: stopped (finished: no open tasks)"); start it again after
        giving the org more work. False keeps it running until stop(). Refused if one is already running. Output goes
        to .runtime/scheduler.log. Returns the scheduler's pid.
        """
        org = binding.get()
        if until_done and scheduler_state(org).state == "stopped" and nothing_to_do(org):
            return ("not started: there is nothing to run (you have no open task and no agent has work). Give the "
                    "organization work first (apply_org or delegate), then call start(); until_done=False would "
                    "keep an idle scheduler running instead")
        pid = start_scheduler(org, max_runs, until_done)
        cap = f", at most {max_runs} run(s)" if max_runs is not None else ""
        end = "; it exits by itself when the work is done" if until_done else "; it runs until stop()"
        return f"scheduler started (pid {pid}{cap}{end}); log: {org.root / '.runtime' / 'scheduler.log'}"

    @mcp.tool()
    def stop() -> str:
        """Stop this organization's scheduler (SIGTERM, then wait briefly). Runs in flight are interrupted and
        redelivered on the next start. Only signals a process verified to be this organization's scheduler."""
        return stop_scheduler(binding.get())



    @mcp.tool()
    def blueprint_example(kind: str = "research") -> str:
        """A ready-to-edit blueprint (YAML with a comment on every field and a one-paragraph schema summary).

        kind: "research" (facts from the web with source URLs, fact-checked), "documents" (write from the user's local
        files, no web; uses `needs.inputs`, read-only folders) or "code" (software in a repo workspace, with tests and
        local commits). Replace every <PLACEHOLDER> with what the user told you (ask for what is missing; do not invent
        lists), delete what does not apply, then call propose_org with the text. Read-only.
        """
        return blueprint_examples.example(kind, _example_base(binding.peek()))

    @mcp.tool()
    def propose_org(blueprint: str) -> str:
        """Validate a blueprint and return the plan the user must approve. Writes nothing; safe to call repeatedly.

        blueprint: YAML or JSON text (never a file path). Start from blueprint_example(kind) for a template with every
        field explained. Schema: `mission` (one paragraph); `needs` {scope, deliverable {description, format,
        max_words, path (absolute)}, quality_bar, sources, inputs (read-only folders), workspace (the one absolute
        folder agents may write in), budget_runs (the user's cap), models {cheap, strong}, model_policy, review
        (true/false), approval, progress, kind (research|writing|code), code {tests, packaging, commits}}; `agents`:
        ONE top-level agent (template manager) with `children`; each agent has name and a template (manager,
        researcher, writer, reviewer, fact-checker, engineer, tester, code-reviewer) or a charter, and optionally
        model, tools, workspace, scale; `task` {to, title, goal, acceptance: list of exact, checkable criteria}.
        Works before the organization exists. Returns (1) a block headed "PLAN FOR YOU": show it to the user exactly
        as written and wait for their explicit approval; (2) Details, the full plan for you; (3) a plan_id that
        apply_org requires. If the plan has errors, fix the blueprint and propose again; never ask the user to approve
        a plan with errors.
        """
        org = binding.peek()
        bp = blueprint_mod.load_text(blueprint)
        return blueprint_mod.propose_text(bp, org, target=_target_line(binding, org))

    @mcp.tool()
    def apply_org(blueprint: str, approved: bool = False, plan_id: str | None = None) -> str:
        """Create the agents of a blueprint and give its first task. Only after the user approved the plan.

        blueprint: the YAML/JSON text the user approved via propose_org (unchanged). approved: pass True only after
        the user explicitly approved that plan in this conversation; otherwise nothing happens. plan_id: the id that
        propose_org returned for exactly this blueprint; a missing or different id is refused (propose again, show the
        PLAN FOR YOU block, get approval). Needs an existing organization (create_org first if there is none).
        Refuses with the issues if the blueprint has errors or a name is taken, and undoes everything if it fails
        midway. Returns what was created; then call start().
        """
        if not approved:
            raise OrgError("not applied: the user must approve the plan first. Call propose_org(blueprint), show the "
                           "PLAN FOR YOU block to the user, and only after their explicit approval call "
                           "apply_org(blueprint, approved=True, plan_id=<the plan_id propose_org returned>)")
        bp = blueprint_mod.load_text(blueprint)
        if not plan_id or plan_id.strip() != blueprint_mod.plan_id(bp):
            raise OrgError(("not applied: plan_id is missing" if not plan_id else "not applied: plan_id does not match this blueprint")
                           + ", so this is not the plan the user approved. Call propose_org(blueprint), show the PLAN FOR YOU "
                           "block to the user, get their explicit approval, then call apply_org(blueprint, approved=True, "
                           "plan_id=<the plan_id from that propose_org>) with the same blueprint")
        org = binding.peek()
        if org is None:
            raise OrgError("not applied: there is no organization yet, so call create_org(mission=...) first, then "
                           "apply_org again with the same blueprint and plan_id")
        summary = blueprint_mod.apply(org, bp)
        running = describe_scheduler(org).startswith("scheduler: running")
        nxt = ("The scheduler is already running and will pick the work up; answer status questions with progress()."
               if running else "Next step: call start() to run the scheduler, then answer status questions with progress().")
        return f"applied the blueprint to {org.root}\n{summary.text()}\n{nxt}"

    @mcp.tool()
    async def progress(task_id: str | None = None, wait_seconds: int = 0) -> str:
        """One plain status line per task you (root) gave, then what needs your decision, then the scheduler. Read-only.

        Per task: working / waiting on <agent> / stalled / blocked: <reason> / done / failed, who is busy, runs used
        of the budget given, time since the last activity, and for finished tasks the artifact paths and the runs
        returned. task_id: only that task, in any state (default: open tasks and those finished in the last day).
        wait_seconds (0-900, default 0): first wait until a task finishes, fails, blocks or stalls, or something new
        needs the user, or the time is up, then answer; the answer starts with what changed. Use it when the user
        wants to be told when the work is done: tell them you will wait now, call progress(wait_seconds=...) and
        repeat as long as they want (a turn cannot notify them later). Without wait_seconds it answers "status?".
        """
        if binding.peek() is None:
            return setup_state(binding)
        org = binding.get()
        wait = max(0, min(int(wait_seconds or 0), WAIT_MAX))
        return await anyio.to_thread.run_sync(describe_progress, org, task_id, wait)


def _example_base(org: Org | None) -> Path:
    """Where the examples put deliverables/ and project folders: the user's current directory, unless that is the
    organization itself or a filesystem root (then the home directory)."""
    cwd = Path.cwd().resolve()
    if cwd == cwd.parent or (org is not None and (cwd == org.root or org.root in cwd.parents)):
        return Path.home()
    return cwd


def _target_line(binding: OrgBinding, org: Org | None) -> str:
    if org is not None:
        agents = len(org.agents())
        return f"Target organization: {org.root} (exists, {agents} agent(s) besides root; apply_org adds to it)"
    where = binding.root if binding.root is not None else "(path given to create_org)"
    return f"Target organization: {where} (none yet: create_org(mission=...) comes first, then apply_org)"


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
