"""Organization health, measured from the files alone.

Everything here is read-only and derived from message files and run logs (nothing is persisted):

* a run starts at the timestamp in its log file name and ends at the log's mtime;
* an *empty* run is one during which the agent sent no message. Runs that failed (crash, timeout, kiro missing)
  and runs woken only by runtime notes (stall reminders, reviews, refunds) are not the agent's doing and are left
  out of the waste and cost statistics (``expensive``); ``runs_used`` itself still counts every run (it is the budget);
* a task counts once, by its *latest* result: a ``blocked`` that was superseded by ``done`` is a ``done``;
* *rework* is a received task that carries ``revises`` (a manager sent earlier work back). Rework that comes from
  the client of a service case - a rework request after a delivery that was reported ``done``, and the re-checks
  the owner sends its team while it handles such a request - is counted apart (``client_rework``) and is not held
  against the agent: the client's rejection says nothing about the reviewer's or the writer's own quality.

Thresholds come from ``HEALTH_DEFAULTS`` overridden by the ``health:`` mapping in ORG.md frontmatter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .core import ROOT, Message, Org, OrgError, latest_results, utcnow
from .kernel import aware, fmt_duration, msg_time, parse_time, stamp_of
from .settings import config_number  # noqa: F401 - re-export (legacy name health.config_number)
from .settings import finite_number as _number

HEALTH_DEFAULTS: dict[str, float] = {
    "stuck_after_seconds": 1800,  # open task older than this, with nothing in progress -> stuck
    "max_runs_per_task": 5,  # runs used per result sent -> expensive
    "max_runs_without_result": 6,  # runs since the last result while holding an open task -> expensive
    "max_problem_ratio": 0.5,  # (failed + blocked + rework) / tasks received -> low_quality
    "min_tasks_for_quality": 3,  # tasks received before low_quality can fire
    "max_empty_run_ratio": 0.5,  # empty runs / runs used -> wasteful
    "min_runs_for_waste": 4,  # runs used before wasteful can fire
    "idle_after_seconds": 86400,  # no work and no activity for this long -> idle (candidate to retire)
    "stranded_after_seconds": 1800,  # budget left, no work and no activity for this long -> stranded_budget
}

FLAGS = ("stuck", "out_of_budget", "paused", "low_quality", "expensive", "wasteful", "stranded_budget", "idle")  # worst first


@dataclass
class AgentHealth:
    addr: str
    depth: int
    state: str
    budget_left: int | None
    budget_received: int
    runs_used: int
    tasks_received: int
    open_tasks: int
    oldest_open_age: float | None  # seconds
    done: int
    failed: int
    blocked: int
    runs_per_task: float | None  # runs used / results sent; None without results
    rework: int  # received tasks that revise an earlier one (client-driven ones excluded: see client_rework)
    empty_runs: int  # runs that sent no message (failed runs and runs that only handled runtime notes excluded)
    last_activity: datetime | None
    since_activity: float | None  # seconds
    flags: dict[str, str] = field(default_factory=dict)  # flag -> human reason
    failed_runs: int = 0  # runs that crashed, failed to start, timed out or were interrupted (not the agent's fault)
    runtime_runs: int = 0  # runs woken only by runtime notes (budget, stall, review): sending nothing is fine
    client_rework: int = 0  # received reworks that stem from the client of a service case (not counted in ``rework``)

    @property
    def worst_flag(self) -> str | None:
        return next((f for f in FLAGS if f in self.flags), None)


@dataclass
class BranchHealth:
    addr: str  # the branch root ("root" = the whole organization)
    agents: int
    runs_used: int
    open_tasks: int
    done: int
    failed: int
    blocked: int
    rework: int
    worst_flag: str | None


@dataclass
class OrgHealth:
    root: str
    now: datetime
    agents: list[AgentHealth]  # parents before children
    branches: dict[str, BranchHealth]  # branch root address -> totals over it and its subtree

    @property
    def flagged(self) -> list[AgentHealth]:
        return [a for a in self.agents if a.flags]

    def to_dict(self) -> dict:
        """Plain JSON-able structure (datetimes as ISO strings)."""
        return _plain(asdict(self) | {"flagged": [a.addr for a in self.flagged]})


def thresholds(org: Org) -> dict:
    """HEALTH_DEFAULTS merged with the ``health:`` mapping of ORG.md.

    A value that is not a finite number falls back to its default (a typo in ORG.md must not break health).
    """
    custom = org.config.get("health")
    merged = {**HEALTH_DEFAULTS, **(custom if isinstance(custom, dict) else {})}
    for key, default in HEALTH_DEFAULTS.items():
        number = _number(merged[key])
        merged[key] = default if number is None else number
    return merged


def _client_rework(
    org: Org, addr: str, tasks: list[Message], results: dict[str, Message], _depth: int = 0,
) -> set[str]:
    """Ids of the received reworks (tasks with ``revises``) that stem from the client of a service case.

    * a rework *request* of a service (``service`` set) whose revised task had already been reported ``done``: the
      client looked at a delivery and sent it back;
    * a rework the sender sent its team (e.g. "check the memo again") while it held such a client rework as an open
      task: a consequence of the client's rejection, not of the receiver's own work.

    A rework sent in answer to a failed, blocked or still open task is the manager's own quality control and counts.
    """
    out: set[str] = set()
    for t in tasks:
        if not t.revises:
            continue
        prior = results.get(t.revises)
        if t.service and prior is not None and prior.status == "done" and prior.id < t.id:
            out.add(t.id)
        elif _depth < 8 and t.sender != ROOT and org.exists(t.sender) and _holds_client_rework(org, t, _depth):
            out.add(t.id)
    return out


def _holds_client_rework(org: Org, task: Message, depth: int) -> bool:
    """Did ``task``'s sender hold a client-driven rework as an open task when it sent ``task``?"""
    sender = task.sender
    mine = [m for m in org.received(sender) if m.type == "task"]
    answers = latest_results(org.sent(sender))
    driven = _client_rework(org, sender, mine, answers, depth + 1)
    return any(
        m.id in driven and m.id < task.id and (m.id not in answers or answers[m.id].id > task.id) for m in mine
    )


def agent_health(org: Org, addr: str, now: datetime | None = None, limits: dict | None = None) -> AgentHealth:
    """Metrics and flags for one agent. ``now`` defaults to the current time; ``limits`` to ``thresholds(org)``."""
    a = org.require(addr)
    if a == ROOT:
        raise OrgError("root is the human; only agents have health data")
    now, cfg = _aware(now) or utcnow(), limits or thresholds(org)

    received, sent = org.received(a), org.sent(a)
    tasks = [m for m in received if m.type == "task"]
    results = latest_results(sent)  # task id -> its latest result: each task counts once, by its latest status
    answered = set(results)
    open_tasks = [t for t in tasks if t.id not in answered]
    answered_out = {m.reply_to for m in received if m.type == "result"}
    waiting = any(m.type == "task" and m.id not in answered_out for m in sent)
    by_status = {s: sum(1 for r in results.values() if r.status == s) for s in ("done", "failed", "blocked")}
    client_driven = _client_rework(org, a, tasks, results)
    rework = sum(1 for t in tasks if t.revises and t.id not in client_driven)
    unread, running, paused = org.unread(a), org.running(a), org.paused(a)
    budget_left, runs_used = org.budget(a), org.runs_used(a)

    log_reader = org.runtime.run_log_reader
    windows = log_reader.windows(a)
    sent_at = [t for t in map(_msg_time, sent) if t]
    outcomes = log_reader.outcomes(a)
    failed, runtime_only = outcomes.failed, outcomes.runtime_only
    excluded = failed | runtime_only  # run starts that say nothing about the agent's own efficiency
    judged = sum(1 for start, _ in windows if start not in excluded)
    candidates = windows[:-1] if running else windows  # a run in progress is not (yet) empty
    empty = sum(
        1 for start, end in candidates
        if start not in excluded and not any(start <= t <= end for t in sent_at)
    )
    activity = [end for _, end in windows] + sent_at
    last = max(activity, default=None)
    since = max(0.0, (now - last).total_seconds()) if last else None

    ages = [max(0.0, (now - c).total_seconds()) for t in open_tasks if (c := _parse_time(t.created))]
    oldest = max(ages, default=None)
    result_times = [t for t in map(_msg_time, (m for m in sent if m.type == "result")) if t]
    last_result = max(result_times, default=None)
    # Runs that say nothing about the agent's own efficiency (failed, or woken only by runtime notes) are not charged.
    since_result = sum(
        1 for start, _ in windows if start not in excluded and (last_result is None or start > last_result)
    )
    runs_per_task = (runs_used - len(excluded)) / len(results) if results else None
    problems = by_status["failed"] + by_status["blocked"] + rework

    flags: dict[str, str] = {}
    if oldest is not None and oldest > cfg["stuck_after_seconds"] and not (waiting or running or unread):
        flags["stuck"] = f"open task is {_duration(oldest)} old and nothing is in progress"
    if budget_left is not None and budget_left <= 0 and (unread or open_tasks):
        flags["out_of_budget"] = "no budget left but has unread mail or open tasks"
    if paused:
        flags["paused"] = f"paused: {paused}"
    if len(tasks) >= cfg["min_tasks_for_quality"] and problems / max(1, len(tasks)) > cfg["max_problem_ratio"]:
        flags["low_quality"] = f"{problems} of {len(tasks)} tasks failed, blocked or were sent back"
    reasons = []
    if runs_per_task is not None and runs_per_task > cfg["max_runs_per_task"]:
        reasons.append(f"{runs_per_task:.1f} runs per completed task (max {cfg['max_runs_per_task']})")
    if open_tasks and since_result > cfg["max_runs_without_result"]:
        reasons.append(f"{since_result} runs without a result on an open task (max {cfg['max_runs_without_result']})")
    if reasons:
        flags["expensive"] = "; ".join(reasons)
    if judged and judged >= cfg["min_runs_for_waste"] and empty / judged > cfg["max_empty_run_ratio"]:
        flags["wasteful"] = f"{empty} of {judged} runs sent no message"
    quiet = (since if last else _since_hired(org, a, now)) or 0.0
    if (
        budget_left is not None and budget_left > 0 and org.parent(a) != ROOT and quiet > cfg["stranded_after_seconds"]
        and not (open_tasks or waiting or running or unread)
    ):  # root has no limit, so budget parked in its direct reports starves nobody
        flags["stranded_budget"] = (
            f"{budget_left} unused run(s) and no work or activity for {_duration(quiet)}; "
            "they belong with its parent"
        )
    if not (open_tasks or waiting or running or unread) and quiet > cfg["idle_after_seconds"]:
        flags["idle"] = f"no open tasks and no activity for {_duration(quiet)}; candidate to retire"

    return AgentHealth(
        addr=a, depth=org.depth(a), state=org.state(a), budget_left=budget_left,
        budget_received=sum(m.budget for m in received), runs_used=runs_used, tasks_received=len(tasks),
        open_tasks=len(open_tasks), oldest_open_age=oldest, rework=rework, client_rework=len(client_driven), empty_runs=empty,
        runs_per_task=runs_per_task, last_activity=last, since_activity=since, flags=flags, **by_status,
        failed_runs=len(failed), runtime_runs=len(runtime_only - failed),
    )


def org_health(org: Org, root: str = ROOT, now: datetime | None = None) -> OrgHealth:
    """Health of ``root`` and everything below it (``root`` = the whole organization, human excluded)."""
    top = org.require(root)
    now, cfg = _aware(now) or utcnow(), thresholds(org)
    addrs = org.agents() if top == ROOT else org.subtree(top)
    agents = [agent_health(org, a, now, cfg) for a in addrs]
    by_addr = {h.addr: h for h in agents}
    branches = {}
    for b in dict.fromkeys([top, *addrs]):
        members = [by_addr[a] for a in addrs if a == b or b == ROOT or a.startswith(b + "/")]
        branches[b] = BranchHealth(
            addr=b, agents=len(members), runs_used=sum(h.runs_used for h in members),
            open_tasks=sum(h.open_tasks for h in members), done=sum(h.done for h in members),
            failed=sum(h.failed for h in members), blocked=sum(h.blocked for h in members),
            rework=sum(h.rework for h in members),
            worst_flag=min((f for h in members for f in h.flags), key=FLAGS.index, default=None),
        )
    return OrgHealth(root=top, now=now, agents=agents, branches=branches)


def render_text(health: OrgHealth) -> str:
    """Human report: a summary line, then one line per agent (indented by depth) with flags and reasons."""
    n, bad = len(health.agents), len(health.flagged)
    lines = [f"{n} agent{'s' * (n != 1)}, {bad} flagged"]
    base = min((h.depth for h in health.agents), default=0)
    for h in health.agents:
        left = "unlimited" if h.budget_left is None else h.budget_left
        parts = [
            f"{h.addr.rsplit('/', 1)[-1]} {h.state}",
            f"budget {left}/{h.budget_received}",
            f"runs {h.runs_used}",
            f"open {h.open_tasks}" + (f" (oldest {_duration(h.oldest_open_age)})" if h.oldest_open_age is not None else ""),
            f"done {h.done} failed {h.failed} blocked {h.blocked} rework {h.rework}"
            + (f" (+{h.client_rework} by the client)" if h.client_rework else ""),
            "runs/task " + ("-" if h.runs_per_task is None else f"{h.runs_per_task:.1f}"),
            f"empty {h.empty_runs}" + (f" (+{h.failed_runs} failed)" if h.failed_runs else ""),
            "last activity " + ("never" if h.since_activity is None else f"{_duration(h.since_activity)} ago"),
        ]
        line = "  " * (h.depth - base) + ", ".join(parts)
        branch = health.branches[h.addr]
        if branch.agents > 1:
            line += (
                f" | branch: runs {branch.runs_used}, open {branch.open_tasks}, done {branch.done}, "
                f"failed {branch.failed}, blocked {branch.blocked}, rework {branch.rework}, "
                f"worst {branch.worst_flag or 'none'}"
            )
        if h.flags:
            line += " | " + "; ".join(f"!{flag}: {why}" for flag, why in h.flags.items())
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------- helpers


# The time helpers live in the kernel; other modules still import these private names from here.
_aware = aware
_parse_time = parse_time
_stamp = stamp_of
_msg_time = msg_time


def _since_hired(org: Org, addr: str, now: datetime) -> float:
    """Seconds since the agent was hired, for agents that never did anything."""
    hired = _parse_time(org.charter(addr)[0].get("created"))
    if hired is None:
        hired = datetime.fromtimestamp((org.dir(addr) / "AGENT.md").stat().st_mtime, timezone.utc)
    return max(0.0, (now - hired).total_seconds())


_duration = fmt_duration


def _plain(value):
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value.isoformat() if isinstance(value, datetime) else value
