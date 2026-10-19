"""Health reviews: turn health flags into short notes for the managers who can act on them.

``review`` is the one code path (scheduler and ``orgmcp review``); the scheduler only decides *when*
(``review_if_due``). Healthy parts of the organization cost nothing: a manager is written to only when
a direct report has a problem it has not been told about, and each note costs that manager one run.

* a manager (an agent with direct reports) hears about each (report, flag) pair once; a pair it was already
  told about in the previous review is not repeated. Paused managers and managers whose budget is no more than
  their outstanding delegations (the reserve for processing results) are skipped and listed in root's note;
* root hears about every flagged agent in one note, every review (it is free), so nothing is hidden;
* the only state is ``.runtime/reviews.json``: when, the org-wide run count, and who was told about what.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .. import templates
from ..health import AgentHealth, OrgHealth, config_number, org_health
from ..kernel import ROOT
from ..kernel import aware as _aware
from ..kernel import parse_time as _parse_time
from .api import Note, Review

Org = Any  # the facade (a feature may not import it): the functions below take whatever has its methods
LEDGER = "reviews"


def read_ledger(org: Org) -> dict[str, Any] | None:
    """The reviews ledger normalised to {"at", "runs", "notified"}; None when there is none or it is malformed."""
    ledger = org.ledger(LEDGER)
    if not isinstance(ledger, dict) or not ledger:
        return None
    notified = ledger.get("notified")
    if isinstance(notified, dict):
        notified = {k: v for k, v in notified.items() if isinstance(k, str) and isinstance(v, list)}
    else:
        notified = {}
    runs = ledger.get("runs")
    return {
        "at": ledger.get("at"),
        "runs": runs if isinstance(runs, int) and not isinstance(runs, bool) else 0,
        "notified": notified,
    }


def total_runs(org: Org) -> int:
    """Runs ever used across the organization, counted from the run logs (so a restart does not reset it).

    Retired agents are included, so retiring never moves the counter backwards (and never postpones a review).
    """
    return int(sum(org.runs_used(a) for a in org.agents()) + org.runtime.retired_archive.run_count())


def review_if_due(org: Org, now: datetime) -> Review | None:
    """Run a review when ``review_every_runs`` runs or ``review_every_seconds`` have passed since the last one.

    With no earlier review the clock starts now (the ledger is created, nothing is reported).
    """
    last = read_ledger(org)
    if not last:  # missing, empty or malformed: the clock starts now
        _save(org, now, total_runs(org), {})
        return None
    cfg, at = org.config, _parse_time(last["at"])
    used = total_runs(org)
    if used < last["runs"]:  # logs vanished some other way (e.g. .retired/ deleted): start counting again from here
        last["runs"] = used
        _save(org, _parse_time(last["at"]) or now, used, last["notified"])
    runs_due = used - last["runs"] >= config_number(cfg, "review_every_runs", int)
    time_due = at is None or (_aware(now) - at).total_seconds() >= config_number(cfg, "review_every_seconds")
    return review(org, now) if runs_due or time_due else None


def review(org: Org, now: datetime | None = None, dry_run: bool = False) -> Review:
    """Review the organization now. With ``dry_run`` nothing is sent and the ledger is left alone."""
    now = _aware(now) or datetime.now(timezone.utc)
    health = org_health(org, ROOT, now)
    by_addr = {h.addr: h for h in health.agents}
    previous = (read_ledger(org) or {}).get("notified", {})
    result = Review(at=now, runs=total_runs(org), flagged=len(health.flagged))

    for manager in (a for a in by_addr if org.children(a)):
        pairs = _pairs(org, health, by_addr, manager)
        if not pairs:
            continue
        known = [k for k in pairs if k in previous.get(manager, [])]
        new = [k for k in pairs if k not in known]
        why = _cannot_afford(org, manager)
        if why:
            result.skipped[manager] = why
            result.notified[manager] = known  # what it already knew and is still true
        elif new:
            result.notified[manager] = known + new
            result.notes.append(Note(
                manager, f"health review: {len(new)} new problem(s)",
                templates.notice_review_manager(manager, [pairs[k] for k in new]),
            ))
        else:
            result.notified[manager] = known
    if health.flagged:
        keys, items = [], []
        for h in health.flagged:
            for flag, why in h.flags.items():
                keys.append(f"{h.addr}:{flag}")
                items.append(templates.review_item(h.addr, flag, why, act=org.parent(h.addr) == ROOT))
        summary = f"{len(health.agents)} agents, {len(health.flagged)} flagged."
        result.notified[ROOT] = keys
        result.notes.append(Note(
            ROOT, f"health review: {len(health.flagged)} of {len(health.agents)} agents flagged",
            templates.notice_review_root(summary, items, result.skipped),
        ))
    result.notified = {k: v for k, v in result.notified.items() if v}

    if not dry_run:
        for n in result.notes:
            org.notify(n.to, n.title, n.body)
        _save(org, now, result.runs, result.notified)
        org.emit("review.run", flagged=result.flagged, notes=[n.to for n in result.notes])
    return result


def _cannot_afford(org: Org, manager: str) -> str:
    """Why a note must not be sent to this manager ("" = it may be). A note costs a run; the runs a manager
    holds in reserve (one per outstanding delegation, to process the result) are not for review notes."""
    if org.paused(manager):
        return "paused"
    budget, owed = org.budget(manager) or 0, len(org.outstanding(manager))
    if budget <= 0:
        return "no budget left"
    if budget <= owed:
        return f"budget {budget} is reserved for {owed} outstanding delegation(s)"
    return ""


def _pairs(org: Org, health: OrgHealth, by_addr: dict[str, AgentHealth], manager: str) -> dict[str, str]:
    """Problems of a manager's direct reports: "agent:flag" -> rendered item. Teams add their worst flag."""
    out: dict[str, str] = {}
    for report in org.children(manager):
        h = by_addr[report]
        for flag, why in h.flags.items():
            out[f"{report}:{flag}"] = templates.review_item(report, flag, why)
        worst = health.branches[report].worst_flag
        if worst and worst not in h.flags:  # raised by someone further down the team
            member = next(m for m in health.agents if m.addr.startswith(report + "/") and worst in m.flags)
            out[f"{report}:branch:{worst}"] = templates.review_item(member.addr, worst, member.flags[worst], branch=report)
    return out


def _save(org: Org, now: datetime, runs: int, notified: dict[str, list[str]]) -> None:
    org.save_ledger(LEDGER, {"at": _aware(now).isoformat(timespec="seconds"), "runs": runs, "notified": notified})
