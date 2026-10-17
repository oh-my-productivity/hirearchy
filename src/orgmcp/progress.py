"""Progress for the human: one plain line per root task, then what needs the human.

Read-only and derived from the files, like everything else (nothing is stored). It is what an assistant reads back
to a user who asks "status?": for every task root gave, its state, who is busy, what it cost and when anything last
happened; then one line per item in root's inbox that waits for a decision.

States of a task: ``working`` (someone below is running or has unread work), ``waiting on <agent>`` (the work sits
with an agent that is not running; a paused one says why), ``stalled`` (the assignee itself holds the task and
nothing is happening), ``blocked: <reason>``, ``done``, ``failed``.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from .core import ROOT, Message, Org, OrgError, latest_results, utcnow
from .health import _aware, _duration, _stamp

RECENT = timedelta(hours=24)  # without a task id, finished tasks are listed for this long after they finished
SHORT = 110  # characters of a reason or a note shown on a line


def progress(org: Org, task_id: str | None = None, now: datetime | None = None) -> str:
    """Status of root's tasks (``task_id``: just that one, in any state) and of what waits for the human."""
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
    parts = [f'"{task.title}": {state}']
    if who:
        parts.append(who)
    parts.append(_runs(org, task, result, team))
    last = _last_activity(org, team)
    if last is not None:
        parts.append(f"last activity {_duration(max(0.0, (now - last).total_seconds()))} ago")
    if result is not None and result.status in ("done", "failed"):
        arts = _artifacts(result)
        parts.append("artifacts: " + ", ".join(arts) if arts else "no artifacts")
    return ". ".join(parts) + f". (task {task.id})"


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
    """Runs the team started while this task was open, against the budget root gave for it (task + later grants)."""
    start, end = _stamp(task.id), (_stamp(result.id) if result is not None else None)

    def inside(t: datetime | None) -> bool:
        return t is not None and (start is None or t >= start) and (end is None or t <= end)

    used = 0
    for a in team:
        d = org.dir(a) / "runs"
        used += sum(
            1 for n in (os.listdir(d) if d.is_dir() else [])
            if n.endswith(".log") and not n.startswith(".") and inside(_stamp(n))
        )
    given = task.budget + sum(
        m.budget for m in org.sent(ROOT) if m.to == task.to and m.type == "note" and inside(_stamp(m.id))
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


def _needs_human(org: Org) -> list[str]:
    """One line per unread root message that asks for a decision: blocked or failed results, notes, runtime notices."""
    out = []
    for m in org.messages(ROOT, "inbox"):
        if not m.wake or (m.type == "result" and m.status == "done"):
            continue
        if m.type == "result":
            what, text = f"{m.status} result from {m.sender}", _summary(m)
        else:
            what = "runtime notice" if m.sender == "runtime" else f"note from {m.sender}"
            text = (m.body.splitlines() or [""])[0]
        title = f' "{m.title}"' if m.title else ""
        out.append(f"Needs you: {what}{title}" + (f": {_short(text)}" if text else "") + f" (message {m.id})")
    return out
