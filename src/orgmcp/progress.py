"""Progress for the human: one plain line per root task, then what needs the human.

Read-only and derived from the files, like everything else (nothing is stored). It is what an assistant reads back
to a user who asks "status?": for every task root gave, its state, who is busy, what it cost and when anything last
happened; then one line per item in root's inbox that waits for a decision.

States of a task: ``working`` (someone below is running or has unread work), ``waiting on <agent>`` (the work sits
with an agent that is not running; a paused one says why), ``stalled`` (the assignee itself holds the task and
nothing is happening), ``blocked: <reason>``, ``done``, ``failed``.

``wait_seconds`` turns the call into a wait: it polls the same files (read-only: no locks, nothing written) until a
task changes state (done, failed, blocked, stalled), something new needs the human, or the time is up.

A task counts as in progress (so a wait really waits) when its state is ``working`` or ``waiting``, or when it is
``blocked``/``stalled`` but some agent in its subtree is running, or could run now: unread mail that wakes it, budget
left, not paused (a root task is ``blocked`` while its lead is about to work on the budget root just granted). Only
when nothing in the org can run does a wait return at once, and a wait that began with such work also ends as soon as
the last of it stops, instead of running out the clock.

Runs per task: every run of any agent in the task's subtree from the task's creation to its final result
(``done``/``failed``; ``blocked`` is not final) or now, against everything root sent into that subtree for the task
(the task's budget plus later grants).
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from .core import ROOT, Message, Org, OrgError, latest_results, utcnow
from .health import _aware, _duration, _stamp

RECENT = timedelta(hours=24)  # without a task id, finished tasks are listed for this long after they finished
SHORT = 110  # characters of a reason or a note shown on a line
WAIT_MAX = 900  # longest wait_seconds honored
POLL = 2.0  # seconds between two looks at the files while waiting
FINAL = ("done", "failed", "blocked", "stalled")  # the states a wait returns for


def progress(org: Org, task_id: str | None = None, now: datetime | None = None, *, wait_seconds: int = 0,
             poll: float = POLL, sleep: Callable[[float], None] = time.sleep,
             clock: Callable[[], float] = time.monotonic) -> str:
    """Status of root's tasks (``task_id``: just that one, in any state) and of what waits for the human.

    ``wait_seconds`` > 0 (at most 900): first block until a listed task changes state (done / failed / blocked /
    stalled), something new needs the human, or the time is up; the result then starts with a line saying which.
    """
    wait = max(0, min(int(wait_seconds or 0), WAIT_MAX))
    if wait <= 0:
        return _render(org, task_id, now)
    before = _snapshot(org, task_id)
    if not _in_progress(before[0], before[2]):
        return "Nothing to wait for: no listed task is being worked on right now.\n" + _render(org, task_id, now)
    start = clock()
    suspect: set[str] = set()  # tasks seen stalled once: confirmed on the next look, so a hand-over is not a stall
    idle = 0  # consecutive looks at which nothing in the org could run any more
    while True:
        left = wait - (clock() - start)
        sleep(max(0.0, min(poll, left)))
        after = _snapshot(org, task_id)
        changes, suspect = _changes(before, after, suspect)
        waited = _duration(max(0.0, clock() - start))
        if changes:
            return f"Changed after waiting {waited}: " + "; ".join(changes) + "\n" + _render(org, task_id, now)
        idle = 0 if _in_progress(after[0], after[2]) else idle + 1
        if idle >= 2:  # twice in a row, so the gap between one run ending and the next starting is not mistaken for it
            return (f"Stopped after waiting {waited}: nothing in the org can run any more and no task finished. "
                    "It needs a decision, budget or a restart (see below).\n" + _render(org, task_id, now))
        if clock() - start >= wait:
            return (f"Waited {waited}: no task finished, got blocked or stalled, and nothing new needs you. "
                    "Call progress(wait_seconds=...) again to keep waiting.\n" + _render(org, task_id, now))


def describe_progress(org: Org, task_id: str | None = None, wait_seconds: int = 0) -> str:
    """``progress`` plus the scheduler line (the same text for the MCP tool and the CLI).

    Without a running scheduler nothing moves, so a wait would only burn time: it returns at once and says so. The same
    when every open task waits for the user (budget, a crashing agent, a decision): the line then says so and lists the
    user's options.
    """
    from .scheduler import describe_scheduler, waiting_on_user

    sched = describe_scheduler(org)
    stopped = not sched.startswith("scheduler: running")
    open_work = bool(org.outstanding(ROOT))
    waiting = waiting_on_user(org) if open_work else None
    note = ""
    if waiting is not None and sched.startswith(("scheduler: running", "scheduler: stopped")):
        if stopped:  # the line already says why ("stopped (waiting on you: ...)")
            sched += f" - nothing moves until you act. {waiting.options}"
        else:
            sched += f" - {waiting.text}. {waiting.options} A scheduler started with until_done exits by itself soon."
        if wait_seconds:
            wait_seconds, note = 0, "Not waiting: nothing can progress without you. "
    elif stopped and open_work:
        sched += " - open tasks do not move until it is started (start() or `orgmcp run`)"
        if wait_seconds:
            wait_seconds, note = 0, "Not waiting: no scheduler is running, so nothing will change. "
    elif stopped and wait_seconds and work_in_flight(org, task_id):  # e.g. a blocked task whose lead was just granted runs
        sched += " - agents have work they could do, but nothing moves until it is started (start() or `orgmcp run`)"
        wait_seconds, note = 0, "Not waiting: no scheduler is running, so nothing will change. "
    return f"{note}{progress(org, task_id, wait_seconds=wait_seconds)}\n{sched}"


def _render(org: Org, task_id: str | None, now: datetime | None) -> str:
    now = _aware(now) or utcnow()
    tasks = [m for m in org.sent(ROOT) if m.type == "task"]
    results = latest_results(org.received(ROOT))
    if task_id:
        task = next((t for t in tasks if t.id == task_id), None)
        if task is None:
            known = ", ".join(t.id for t in tasks) or "none"
            raise OrgError(f"no task {task_id} given by root. Tasks: {known}")
        lines = [_task_line(org, task, results.get(task.id), now)]
    else:
        lines = [
            _task_line(org, t, results.get(t.id), now) for t in tasks if _listed(results.get(t.id), now)
        ] or ["No open tasks." + _last_finished(org, tasks, results, now)]
    lines += _needs_human(org)
    return "\n".join(lines)


def _can_run(org: Org, addr: str) -> bool:
    """Is ``addr`` running, or would a scheduler start it now (unread mail that wakes it, budget left, not paused)?"""
    if org.running(addr):
        return True
    return bool(org.unread(addr)) and (org.budget(addr) or 0) > 0 and org.paused(addr) in (None, "budget")


def _alive(org: Org, team: list[str]) -> bool:
    return any(_can_run(org, a) for a in team)


def _in_progress(states: dict[str, tuple[str, str, str]], alive: set[str]) -> bool:
    """Does any listed task still move? working/waiting always; blocked/stalled while someone below can run."""
    return any(c in ("working", "waiting") or (c in ("blocked", "stalled") and tid in alive) for tid, (c, _, _) in states.items())


def work_in_flight(org: Org, task_id: str | None = None) -> bool:
    """Could anything move for the listed root tasks right now (see :func:`_in_progress`)? Read-only."""
    states, _, alive = _snapshot(org, task_id)
    return _in_progress(states, alive)


def _snapshot(org: Org, task_id: str | None) -> tuple[dict[str, tuple[str, str, str]], dict[str, str], set[str]]:
    """(task id -> (state class, title, state text), message id -> line of what needs the human, ids of the tasks that
    have an agent below them that is running or can run now). Read-only."""
    tasks = [m for m in org.sent(ROOT) if m.type == "task"]
    results = latest_results(org.received(ROOT))
    now = utcnow()
    states: dict[str, tuple[str, str, str]] = {}
    alive: set[str] = set()
    for t in tasks:
        if (task_id and t.id != task_id) or (not task_id and not _listed(results.get(t.id), now)):
            continue
        team = [a for a in org.subtree(t.to) if a != ROOT] if org.exists(t.to) else []
        state = _state(org, t, results.get(t.id), team)[0]
        states[t.id] = (re.split(r"[ :(]", state, 1)[0], t.title, state)
        if _alive(org, team):
            alive.add(t.id)
    return states, dict(_human_items(org)), alive


def _changes(before, after, suspect: set[str]) -> tuple[list[str], set[str]]:
    """What differs between two snapshots, as short phrases, and the tasks to confirm as stalled on the next look."""
    out: list[str] = []
    seen: set[str] = set()
    for tid, (cls, title, state) in after[0].items():
        old = before[0].get(tid)
        if old is None or cls == old[0] or cls not in FINAL:
            continue
        if cls == "stalled" and tid not in suspect:
            seen.add(tid)
            continue
        out.append(f'"{title}": {old[0]} -> {state}')
    out += [f"new item for you: {line}" for mid, line in after[1].items() if mid not in before[1]]
    return out, seen


def _listed(result: Message | None, now: datetime) -> bool:
    """Open and blocked tasks always; finished ones while they are recent."""
    if result is None or result.status == "blocked":
        return True
    finished = _stamp(result.id)
    return finished is None or now - finished <= RECENT


def _last_finished(org: Org, tasks: list[Message], results: dict[str, Message], now: datetime) -> str:
    done = [t for t in tasks if (r := results.get(t.id)) and r.status != "blocked"]
    return "\n" + _task_line(org, done[-1], results[done[-1].id], now) if done else ""


def _task_line(org: Org, task: Message, result: Message | None, now: datetime) -> str:
    team = [a for a in org.subtree(task.to) if a != ROOT] if org.exists(task.to) else []
    state, who = _state(org, task, result, team)
    tag = f" [service {task.service} v{task.playbook or 0}]" if task.service else ""
    parts = [f'"{task.title}"{tag}: {state}']
    if who:
        parts.append(who)
    parts.append(_runs(org, task, result, team))
    last = _last_activity(org, team)
    if last is not None:
        parts.append(f"last activity {_duration(max(0.0, (now - last).total_seconds()))} ago")
    if result is not None and result.status in ("done", "failed"):
        arts = _artifacts(result)
        parts.append("artifacts: " + ", ".join(arts) if arts else "no artifacts")
        if task.service and _no_feedback(org, task):
            parts.append("no feedback yet")
    return ". ".join(parts) + f". (task {task.id})"


def _no_feedback(org: Org, task: Message) -> bool:
    """A finished service request that the client has not rated yet (feedback on any task of its case counts)."""
    from . import services

    case = next((c for c in services.cases(org, task.to, task.service) if task.id in {t.id for t in c.tasks}), None)
    return case is None or case.feedback is None


def _state(org: Org, task: Message, result: Message | None, team: list[str]) -> tuple[str, str]:
    """(state, who is busy) of a root task."""
    if result is not None and result.status in ("done", "failed"):
        return result.status, ""
    if result is not None:  # blocked
        return f"blocked: {_short(_summary(result)) or 'no reason given'}", ""
    if not team:
        return f"failed: {task.to} no longer exists", ""
    running = [a for a in team if org.running(a)]
    unread = [a for a in team if org.unread(a) and not org.paused(a) and a not in running]
    who = "; ".join(
        x for x in (
            "running: " + ", ".join(running) if running else "",
            "unread work: " + ", ".join(unread) if unread else "",
        ) if x
    )
    if running or unread:
        return "working", who
    holders = [a for a in team if org.open_tasks(a) and not org.outstanding(a)]
    if holders == [task.to]:
        why = org.paused(task.to)
        return f"stalled ({task.to} {'is paused: ' + why if why else 'has not reported and nothing is running'})", ""
    names = ", ".join(a + (f" (paused: {org.paused(a)})" if org.paused(a) else "") for a in holders)
    return f"waiting on {names or task.to}", ""


def _runs(org: Org, task: Message, result: Message | None, team: list[str]) -> str:
    """Runs the team made for this task, against everything root put into the team for it.

    Runs: every run log of every agent in the subtree from the task's creation to its *final* result (``done`` or
    ``failed``; a ``blocked`` one is not final: the team may be given more budget and go on) or now. It ends early
    only where root's next task to the same assignee begins, so overlapping tasks do not count a run twice. Run logs
    are files, so scheduler restarts and extra grants change nothing. Budget: the task's own plus every later grant
    (a note from root carrying budget to an agent of the team) in the same window.
    """
    start = task.id[:21]
    end = result.id[:21] if result is not None and result.status in ("done", "failed") else None
    later = [t.id[:21] for t in org.sent(ROOT) if t.type == "task" and t.to == task.to and t.id > task.id]
    if later and (end is None or later[0] < end):
        end = later[0]

    def inside(name: str) -> bool:
        return name[:21] >= start and (end is None or name[:21] <= end)

    used = 0
    for a in team:
        d = org.dir(a) / "runs"
        used += sum(1 for n in (os.listdir(d) if d.is_dir() else []) if n.endswith(".log") and not n.startswith(".") and inside(n))
    members = set(team)
    given = task.budget + sum(
        m.budget for m in org.sent(ROOT) if m.type == "note" and m.to in members and inside(m.id)
    )
    text = f"runs {used} of {given}"
    if result is not None and result.budget:
        text += f" ({result.budget} returned)"
    return text


def _last_activity(org: Org, team: list[str]) -> datetime | None:
    """The newest message or run in the team's mailboxes and run logs (from file names and mtimes: no parsing)."""
    newest: datetime | None = None
    for a in team:
        d = org.dir(a)
        for box in ("inbox", "inflight", "read", "sent"):
            try:
                names = os.listdir(d / box)
            except OSError:
                continue
            for n in names:
                t = None if n.startswith(".") else _stamp(n)
                if t and (newest is None or t > newest):
                    newest = t
        try:
            for n in os.listdir(d / "runs"):
                if n.endswith(".log") and not n.startswith("."):
                    t = datetime.fromtimestamp(os.stat(d / "runs" / n).st_mtime, timezone.utc)
                    if newest is None or t > newest:
                        newest = t
        except OSError:
            continue
    return newest


def _section(body: str, heading: str) -> list[str]:
    out, inside = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower() == heading
        elif inside and line.strip():
            out.append(line.strip())
    return out


def _summary(result: Message) -> str:
    lines = _section(result.body, "summary")
    return lines[0] if lines else (result.body.splitlines() or [""])[0]


def _artifacts(result: Message) -> list[str]:
    """Paths listed under ``## Artifacts`` (the runtime's word-count notes after the path are dropped)."""
    return [line.lstrip("-* ").split(" (", 1)[0] for line in _section(result.body, "artifacts")]


def _short(text: str, limit: int = SHORT) -> str:
    text = " ".join(text.split())
    text = text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
    return text.rstrip(".")


def _human_items(org: Org) -> list[tuple[str, str]]:
    """(message id, line) for each unread root message that asks for a decision: blocked or failed results and every
    note or runtime notice (budget requests, questions, escalations), oldest first, each as one line with its id.
    Not listed: a ``done`` result (the task line already summarises it) and quiet notices (``wake: false``: budget
    returned or reclaimed, refunds), which only carry runs."""
    out = []
    for m in org.messages(ROOT, "inbox"):
        if not m.wake or (m.type == "result" and m.status == "done"):
            continue
        if m.type == "result":
            what, text = f"{m.status} result from {m.sender}", _summary(m)
        else:
            what = "runtime notice" if m.sender == "runtime" else f"note from {m.sender}"
            text = next((line.strip() for line in m.body.splitlines() if line.strip()), "")
        title = f' "{m.title}"' if m.title else ""
        out.append((m.id, f"Needs you: {what}{title}" + (f": {_short(text)}" if text else "") + f" (message {m.id})"))
    return out


def _needs_human(org: Org) -> list[str]:
    """One line per item that waits for the human."""
    return [line for _, line in _human_items(org)]
