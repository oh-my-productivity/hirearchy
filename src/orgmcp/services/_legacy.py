"""The old module-level names of ``orgmcp.services`` (every function takes the :class:`~orgmcp.core.Org` first and the acting agent second).

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). Two kinds of code are here:

* thin adapters of the part that moved (step C-services): contracts, playbooks, requests, feedback and their hints call the ports of
  ``org.runtime``; they only keep the old spelling (the ``Org`` is duck-typed, because no feature may import the facade);
* THE SEAM FOR ``reflection`` (step C-reflection, ARCHITECTURE.md 5.8): the cases of a service (``Case``, ``Verdict``, ``Stats``,
  ``playbook_timeline``, ``cases``, ``case_of``, ``version_at``, ``lessons_of``, ``summarize``, ``stats_by_version``), the reflection digest, the
  ``services`` listing, ``case_total`` and the sections of the run prompt are DERIVED from the message files and the run logs. They stay here
  verbatim, reading contracts and playbooks through ``org.runtime.service_catalog`` and the history of the playbook through
  ``org.runtime.service_store``, until C-reflection moves them into ``reflection`` (and then this module has only the adapters).

Standing services: the contract ``<owner>/services/<name>/SERVICE.md`` is written by the client (the owner's parent) with :func:`define_service`;
the playbook ``PLAYBOOK.md`` by the owner with :func:`revise_playbook`; a request is a task built from the contract (:func:`request`). All raise
:class:`~orgmcp.core.OrgError` with a message written for an LLM.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import cast

from ..kernel import RENDER_BODY_CHARS, TITLE_MAX, JsonObject, Message, clip_line, latest_results, msg_time
from ._cap import playbook_word_cap
from ._hints import client_words
from ._host import ServicesOrg
from ._normalizer import TextContractNormalizer
from ._parse import as_int, as_time
from .api import (
    DELIVERABLE_KEYS,
    DESCRIPTION_MAX,
    FEEDBACK_HEADER,
    FEEDBACK_MAX,
    INPUT_RE,
    REASON_MAX,
    VERDICTS,
    Contract,
    Playbook,
)

DIGEST_CASES = 6  # cases with new evidence shown in the digest
DIGEST_CHARS = 3000  # soft limit of the whole digest
CLIP_LESSON = 220
CLIP_NOTE = 160
MAX_VERDICTS = 4  # verdicts of one case shown in a digest line

__all__ = [
    "CLIP_LESSON", "CLIP_NOTE", "DELIVERABLE_KEYS", "DESCRIPTION_MAX", "DIGEST_CASES", "DIGEST_CHARS", "FEEDBACK_HEADER", "FEEDBACK_MAX",
    "INPUT_RE", "MAX_VERDICTS", "REASON_MAX", "TITLE_MAX", "VERDICTS", "Case", "Contract", "Playbook", "Stats", "Verdict", "case_of",
    "case_total", "cases", "define_service", "feedback", "feedback_text", "lessons_of", "owned_services", "parse_input_spec",
    "playbook_timeline", "prompt_sections", "read_contract", "read_playbook", "reflection_digest", "report_hint", "request",
    "requestable_services", "retire_service", "revise_playbook", "rework_fields", "service_dir", "services_text", "stats_by_version",
    "summarize", "version_at",
]


# ----------------------------------------------------------------------------------- names kept for the callers that still reach for them

_clip = clip_line  # the private copy of ``kernel.clip_line`` that ``kernel/tests/test_text.py`` still compares with the others


# ----------------------------------------------------------------------------------- the adapters of the part that moved


def service_dir(org: ServicesOrg, owner: str, name: str) -> Path:
    return org.dir(owner) / "services" / name


def _rel(org: ServicesOrg, path: Path | None) -> str:
    return str(path.relative_to(org.root)) if path is not None else ""


def read_contract(org: ServicesOrg, owner: str, name: str) -> Contract | None:
    """The contract of ``owner``'s service ``name``; None when there is no such (non-retired) service."""
    return org.runtime.service_catalog.read_contract(owner, name)


def read_playbook(org: ServicesOrg, owner: str, name: str) -> Playbook:
    """The current playbook of a service (version 0 when it has none yet)."""
    return org.runtime.service_catalog.read_playbook(owner, name)


def owned_services(org: ServicesOrg, owner: str) -> list[Contract]:
    """The services ``owner`` offers (not the retired ones), by name."""
    return org.runtime.service_catalog.owned_services(owner)


def requestable_services(org: ServicesOrg, actor: str) -> list[Contract]:
    """The services ``actor`` can request: those of its direct reports (root: of its top-level agents)."""
    return org.runtime.service_catalog.requestable_services(actor)


def parse_input_spec(spec: str) -> JsonObject:
    """``'topic*:what it is about'`` -> ``{"name": "topic", "description": "what it is about", "required": True}``.

    A trailing ``*`` on the name marks it required; without it the input is optional. Used by the CLI.
    """
    return TextContractNormalizer().parse_input_spec(spec)


def _inputs(value: object) -> list[JsonObject]:
    return TextContractNormalizer().inputs(value)


def _deliverable(value: object) -> JsonObject:
    return TextContractNormalizer().deliverable(value)


def define_service(
    org: ServicesOrg, actor: str, owner: str, name: str, *, description: str | None = None, inputs: object = None,
    acceptance: object = None, deliverable: Mapping[str, object] | None = None, budget: int | None = None, playbook: str | None = None,
    locked: bool | None = None, notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None,
) -> str:
    """Define a service for ``owner`` (first definition), or amend its contract (the service exists). Returns a confirmation.

    Only ``owner``'s parent (root for a top-level agent) may call it: the contract is the client's. ``name`` is unique
    among the services of the owner's siblings. A first definition needs ``description``, ``acceptance``,
    ``deliverable`` and ``budget`` (``inputs`` default to none, ``locked`` to false) and writes ``SERVICE.md`` v1 (and
    ``PLAYBOOK.md`` v1 when ``playbook`` is given). On an existing service every field but ``owner`` and ``name`` is
    optional and an omitted (None) one keeps its value: ``add_acceptance`` appends criteria, ``remove_acceptance``
    drops criteria (exact text), ``acceptance`` replaces them all (not with add/remove). The old contract is archived
    to ``history/SERVICE.v<n>.md``, ``n+1`` written, and the owner gets a non-waking note saying exactly what changed.
    A change that changes nothing is refused; ``playbook`` is refused (the owner's).
    """
    return org.runtime.service_commands.define_service(
        actor, owner, name, description=description, inputs=inputs, acceptance=acceptance, deliverable=deliverable, budget=budget,
        playbook=playbook, locked=locked, notes=notes, add_acceptance=add_acceptance, remove_acceptance=remove_acceptance,
    )


def retire_service(org: ServicesOrg, actor: str, owner: str, name: str, reason: str) -> str:
    """Take a service out of use: it moves to ``<owner>/services/.retired/<name>-<timestamp>/``. Returns a confirmation.

    Same authority as :func:`define_service` (the owner's parent). Afterwards the service is not listed and cannot be
    requested; its past cases no longer count for a service of the same name defined later. The owner is told in a
    non-waking note.
    """
    return org.runtime.service_commands.retire_service(actor, owner, name, reason)


def revise_playbook(org: ServicesOrg, actor: str, service: str, content: str, reason: str) -> int:
    """Write the next version of the playbook of a service ``actor`` owns; returns the new version.

    Refused when the contract is locked, when ``content`` is empty, over ``playbook_max_words`` or identical to the
    current playbook. A frontmatter in ``content`` is stripped (the runtime writes it). The old version is archived to
    ``history/PLAYBOOK.v<n>.md`` and the client gets a quiet (non-waking) note with the reason.
    """
    return org.runtime.service_commands.revise_playbook(actor, service, content, reason)


def report_hint(org: ServicesOrg, actor: str, task: Message, status: str) -> str:
    """What the `report` tool adds to its reply for a final result on a service request (empty otherwise)."""
    return org.runtime.service_hints.report_hint(actor, task, status)


def request(
    org: ServicesOrg, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
    extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
) -> Message:
    """Ask one of ``actor``'s direct reports for its service ``service``: a task built from the contract.

    The task goes through ``Org.send`` like a delegation (same route, hops and budget rules, the reserve included).
    ``budget`` defaults to the contract's. ``extra_acceptance`` adds criteria after the contract's, which always
    travel unchanged. ``revises``: the id of an earlier request of this service to the same owner, to send it back.
    The task carries ``service``, ``contract`` and ``playbook`` (versions at this moment) in its frontmatter.
    """
    return org.runtime.service_commands.request(
        actor, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance, budget=budget, revises=revises,
    )


def rework_fields(org: ServicesOrg, actor: str, revises: str) -> dict[str, object]:
    """The service fields a rework task inherits from the task it revises (empty for an ordinary task).

    ``service`` and ``contract`` are copied from the revised task; ``playbook`` is the version current now.
    """
    return dict(org.runtime.rework_context.fields_for(actor, revises))


def feedback_text(msg: Message) -> str:
    """The client's own words in a feedback note ("" for a bare accept); the fixed header is not part of them."""
    return client_words(msg)


def feedback(org: ServicesOrg, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
    """The client's verdict on a delivered service request: a quiet note to the owner (it costs no run).

    ``task_id``: any task of the case (the request or a rework) that ``actor`` sent and that has a result. ``verdict``
    is ``accept`` or ``reject``; a rejection needs a ``note`` saying what was wrong. The owner sees it with its next
    batch and in the reflection digest. Every verdict stays in the case's history: the latest one is the final
    verdict of the statistics, and an earlier ``reject`` is still shown (and counted as "after a reject").
    """
    return org.runtime.service_commands.feedback(actor, task_id, verdict, note)


# ----------------------------------------------------------------------------------- cases, stats, digest


@dataclass
class Case:
    """One request of a service plus its rework chain (derived from the message files)."""

    id: str  # id of the first request
    service: str
    owner: str
    tasks: list[Message]  # the request and its reworks, oldest first
    result: Message | None  # latest result of the latest task
    state: str  # open | done | failed | blocked
    playbook: int  # version of the playbook when the first request was sent
    used: int  # version in force when the case was first answered (now, if still unanswered): what the stats group by
    reworks: int
    budget: int  # sum of the budgets of the tasks
    runs: int  # runs of the owner's subtree from the first request to the final result (or now)
    lessons: list[str]  # from the `## Lessons` sections of the results, oldest first
    verdicts: list[Verdict]  # every client verdict on the case, oldest first (the latest is the final one)
    started: datetime | None
    finished: datetime | None  # when it ended done/failed
    lesson_ids: list[str] = field(default_factory=list)  # id of the result each lesson came from (parallel to lessons)

    @property
    def title(self) -> str:
        return self.tasks[0].title

    @property
    def feedback(self) -> Message | None:
        """The latest feedback note (the final verdict), None when the client has not rated the case."""
        return self.verdicts[-1].message if self.verdicts else None

    @property
    def verdict(self) -> str | None:
        """The final verdict: that of the latest feedback."""
        return self.verdicts[-1].verdict if self.verdicts else None

    @property
    def rejected(self) -> bool:
        """Was the case rejected at least once, whatever came after?"""
        return any(v.verdict == "reject" for v in self.verdicts)

    @property
    def accepted_after_reject(self) -> bool:
        return self.verdict == "accept" and self.rejected

    @property
    def evidence_at(self) -> datetime | None:
        """The latest moment this case produced evidence: its final result or its latest feedback."""
        times = [t for t in (self.finished, msg_time(self.feedback) if self.feedback else None) if t]
        return max(times) if times else None


@dataclass
class Verdict:
    """One client verdict on a case: ``step`` is 0 for the first delivery, n for the n-th rework."""

    verdict: str
    note: str  # the client's own words ("" for a bare accept)
    created: datetime | None
    task_id: str  # the task of the chain the feedback was given on
    step: int
    message: Message


@dataclass
class Stats:
    requests: int = 0
    done: int = 0
    failed: int = 0
    open: int = 0
    reworked: int = 0
    accept: int = 0  # final verdict accept (including the ones that came after a reject)
    reject: int = 0  # final verdict reject
    accept_after_reject: int = 0  # of the accepts: cases the client had rejected at least once before
    finished_runs: int = 0

    @property
    def finished(self) -> int:
        return self.done + self.failed

    @property
    def avg_runs(self) -> float | None:
        return round(self.finished_runs / self.finished, 1) if self.finished else None

    def line(self) -> str:
        text = f"{self.requests} request(s): {self.done} done, {self.failed} failed, {self.open} open; {self.reworked} reworked"
        if self.avg_runs is not None:
            text += f"; avg {self.avg_runs:g} runs"
        if self.accept or self.reject:
            after = f" ({self.accept_after_reject} after a reject)" if self.accept_after_reject else ""
            text += f"; feedback {self.accept} accept{after}, {self.reject} reject"
        else:
            text += "; no feedback"
        return text


def playbook_timeline(org: ServicesOrg, owner: str, service: str) -> list[tuple[int, datetime]]:
    """(version, when it was written) of every playbook version the service has had, oldest first."""
    out: list[tuple[int, datetime]] = []
    for version, meta in org.runtime.service_store.playbook_history(owner, service):
        when = as_time(meta.get("revised"))
        if when is not None and version > 0:
            out.append((version, when))
    return sorted(out)


def version_at(timeline: list[tuple[int, datetime]], when: datetime | None) -> int:
    """The playbook version in force at ``when`` (None = now): the latest written at or before it; 0 if none yet."""
    return max((v for v, t in timeline if when is None or t <= when), default=0)


def lessons_of(result: Message) -> str:
    """The text of the ``## Lessons`` section of a result body ("" if there is none)."""
    out, inside = [], False
    for line in result.body.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower() == "lessons"
        elif inside:
            out.append(line)
    return "\n".join(out).strip()


def _count_runs(org: ServicesOrg, team: list[str], start: str, end: str | None) -> int:
    used = 0
    for a in team:
        d = org.dir(a) / "runs"
        for name in os.listdir(d) if d.is_dir() else []:
            if name.endswith(".log") and not name.startswith(".") and name[:21] >= start and (end is None or name[:21] <= end):
                used += 1
    return used


def cases(org: ServicesOrg, owner: str, service: str) -> list[Case]:
    """Every case of ``owner``'s service, oldest first: requests plus their rework chains, with results and feedback.

    Runs: all run logs of the owner's subtree from the first request to the final result (or now), ending early where
    the client's next task to the same owner begins - the same window rule as ``progress`` - so overlapping cases do
    not count a run twice. Requests from before the service was (last) created from scratch are not part of it.
    """
    contract = read_contract(org, owner, service)
    client = org.parent(owner)
    if contract is None or client is None:
        return []
    sent = org.sent(client)
    since = contract.created
    mine = sorted(
        (m for m in sent if m.type == "task" and m.to == owner and m.service == service
         and (since is None or (msg_time(m) or since) >= since)),
        key=lambda m: m.id,
    )
    by_id = {m.id: m for m in mine}

    def head(m: Message) -> str:
        seen = {m.id}
        while m.revises in by_id and m.revises not in seen:
            m = by_id[m.revises]
            seen.add(m.id)
        return m.id

    chains: dict[str, list[Message]] = {}
    for m in mine:
        chains.setdefault(head(m), []).append(m)
    results = latest_results(org.received(client))
    notes = sorted((m for m in sent if m.type == "note" and m.feedback and m.reply_to in by_id), key=lambda m: m.id)
    others = sorted(m.id for m in sent if m.type == "task" and m.to == owner)
    team = org.subtree(owner)
    timeline = playbook_timeline(org, owner, service)
    out = []
    for first, tasks in chains.items():
        ids = {t.id for t in tasks}
        last = tasks[-1]
        res = results.get(last.id)
        state = res.status if res is not None and res.status in ("done", "failed", "blocked") else "open"
        final = res is not None and res.status in ("done", "failed")
        end = res.id[:21] if res is not None and final else None
        later = next((i for i in others if i > last.id and i not in ids), None)
        if later and (end is None or later[:21] < end):
            end = later[:21]
        step = {t.id: i for i, t in enumerate(tasks)}
        verdicts = [
            Verdict(n.feedback or "", feedback_text(n), msg_time(n), n.reply_to or "", step[n.reply_to], n)
            for n in notes if n.reply_to in ids
        ]
        out.append(Case(
            id=first, service=service, owner=owner, tasks=tasks, result=res, state=state,
            playbook=tasks[0].playbook or 0,
            used=version_at(timeline, msg_time(first_result) if (first_result := results.get(tasks[0].id)) else None),
            reworks=len(tasks) - 1, budget=sum(t.budget for t in tasks),
            runs=_count_runs(org, team, tasks[0].id[:21], end),
            lessons=[x for t in tasks if (r := results.get(t.id)) is not None and (x := lessons_of(r))],
            lesson_ids=[r.id for t in tasks if (r := results.get(t.id)) is not None and lessons_of(r)],
            verdicts=verdicts, started=msg_time(tasks[0]),
            finished=msg_time(res) if res is not None and final else None,
        ))
    return out


def summarize(items: list[Case]) -> Stats:
    """Counts over cases: requests, done, failed, open (incl. blocked), reworked, average runs of finished, verdicts."""
    s = Stats(requests=len(items))
    for c in items:
        s.done += c.state == "done"
        s.failed += c.state == "failed"
        s.open += c.state in ("open", "blocked")
        s.reworked += c.reworks > 0
        s.accept += c.verdict == "accept"
        s.reject += c.verdict == "reject"
        s.accept_after_reject += c.accepted_after_reject
        s.finished_runs += c.runs if c.state in ("done", "failed") else 0
    return s


def stats_by_version(items: list[Case]) -> dict[int, Stats]:
    """:func:`summarize` per playbook version, grouped by the version in force when each case was first answered.

    (Not the version current when the request was sent: the owner typically revises the playbook right after the
    request arrives, and that request is then delivered under the new version.)
    """
    return {v: summarize([c for c in items if c.used == v]) for v in sorted({c.used for c in items})}


def reflection_digest(org: ServicesOrg, owner: str, service: str) -> str | None:
    """Evidence since the current playbook was revised, as a compact markdown block; None when there is none.

    New evidence = a case that finished, or feedback that was given, after the playbook's ``revised`` time (without a
    playbook: any finished case or feedback). The block lists the most recent cases with new evidence (state, runs
    used of the budget given, reworks, the client's verdict and note, lessons - each clipped), then one line of
    statistics per playbook version. About 3000 characters at most.
    """
    pb = read_playbook(org, owner, service)
    items = cases(org, owner, service)
    since = pb.revised if pb.version else None
    fresh = [c for c in items if c.evidence_at and (since is None or c.evidence_at > since)]
    if not fresh:
        return None
    fresh.sort(key=lambda c: cast(datetime, c.evidence_at))  # every case in ``fresh`` has evidence
    shown = fresh[-DIGEST_CASES:][::-1]
    per_version = [f"- v{v}: {s.line()}" for v, s in stats_by_version(items).items()]
    while True:
        lines = [_case_line(c) for c in shown]
        text = "Cases with new evidence (most recent first):\n" + "\n".join(lines) + "\nBy playbook version:\n" + "\n".join(per_version)
        if len(text) <= DIGEST_CHARS or len(shown) == 1:
            return text if len(text) <= DIGEST_CHARS else text[: DIGEST_CHARS - 1].rstrip() + "…"
        shown = shown[:-1]


def _verdict_chain(c: Case) -> str:
    """The client's verdicts in order, each with her words: ``reject "too long" -> accept "this one is right"``."""
    shown = c.verdicts[-MAX_VERDICTS:]
    clip = CLIP_NOTE if len(shown) <= 2 else CLIP_NOTE // 2
    parts = [f"{v.verdict}" + (f' "{clip_line(v.note, clip)}"' if v.note else "") for v in shown]
    if len(c.verdicts) > len(shown):
        parts.insert(0, "…")
    return " -> ".join(parts)


def _case_line(c: Case) -> str:
    bits = [f'case {c.id} "{clip_line(c.title, 40)}": {c.state}', f"playbook v{c.used}", f"{c.runs} of {c.budget} runs"]
    if c.reworks:
        bits.append(f"{c.reworks} rework(s)")
    line = ", ".join(bits)
    if c.verdicts:  # the client's verdicts come before the lessons: her words outrank the owner's own conclusions
        line += f"; client feedback: {_verdict_chain(c)}"
    if c.lessons:
        # The latest result is the final word on the case; earlier lessons only where room remains.
        latest, earlier = c.lessons[-1], " / ".join(c.lessons[:-1])
        first_reject = next((v.message.id for v in c.verdicts if v.verdict == "reject"), None)
        after = first_reject is not None and bool(c.lesson_ids) and c.lesson_ids[-1] > first_reject
        mark = " (written after the reject: check it against her words)" if after else ""
        line += f'; lessons{mark}: "{clip_line(latest, CLIP_LESSON)}"'
        room = CLIP_LESSON - len(latest)
        if earlier and room > 40:
            line += f'; earlier: "{clip_line(earlier, room)}"'
    return "- " + line


def case_of(org: ServicesOrg, task: Message) -> Case | None:
    """The case a service task belongs to (None for a task that is not a service request, or an unknown one)."""
    if not task.service or not org.exists(task.to):
        return None
    return next((c for c in cases(org, task.to, task.service) if task.id in {t.id for t in c.tasks}), None)


def case_total(org: ServicesOrg, task: Message) -> str:
    """The whole case in one sentence: runs used by the chain against the runs handed down, and the contract's budget.

    ``case total: 19 runs used of 27 handed down (contract: 15 per request)``; when the chain was handed down more than
    the contract gives one request, it adds that the case exceeds the budget and that the user must be told. Empty for a
    task that is not a service request.
    """
    c = case_of(org, task)
    contract = read_contract(org, task.to, task.service) if task.service and org.exists(task.to) else None
    if c is None or contract is None:
        return ""
    text = f"case total: {c.runs} runs used of {c.budget} handed down (contract: {contract.budget} per request)"
    if c.budget > contract.budget:
        text += f". This case now exceeds the per-request budget of {contract.budget}: tell the user."
    return text


# --------------------------------------------------------------------------------------------- listings


def _service_block(org: ServicesOrg, c: Contract, *, offered: bool) -> list[str]:
    pb = read_playbook(org, c.owner, c.name)
    items = cases(org, c.owner, c.name)
    inputs = ", ".join(f"{i['name']}{'*' if i['required'] else ''}" + (f" ({i['description']})" if i["description"] else "")
                       for i in c.inputs) or "none"
    head = f"- {c.name} (offered by {c.owner}; contract v{c.version}, playbook v{pb.version})" if not offered else \
        f"- {c.name} (contract v{c.version}, playbook v{pb.version}{', locked' if c.locked else ''})"
    lines = [
        f"{head}: {c.description}",
        f"  inputs: {inputs}   (* required)",
        f"  each request: {c.budget} runs; acceptance criteria ({_rel(org, c.path)}):" if c.path else "",
        *(f"    {i}. {x}" for i, x in enumerate(c.acceptance, 1)),
        f"  record: {summarize(items).line() if items else 'no requests yet'}",
    ]
    if pb.version:
        lines.append(f'  playbook v{pb.version} ({pb.revised:%Y-%m-%d}): "{clip_line(pb.reason, 120)}"' if pb.revised else f"  playbook v{pb.version}")
    elif not offered:
        lines.append("  playbook: none yet")
    if offered:
        lines.append(f"  playbook file: {_rel(org, service_dir(org, c.owner, c.name) / 'PLAYBOOK.md')}"
                     + ("" if pb.version else " (not written yet)"))
    return [x for x in lines if x]


def services_text(org: ServicesOrg, actor: str) -> str:
    """The `services` tool/CLI output: what ``actor`` can request from its direct reports, and what it offers."""
    actor = org.require(actor)
    asks, offers = requestable_services(org, actor), owned_services(org, actor)
    if not asks and not offers:
        return (
            "No services yet. A parent defines a standing service for a direct report with define_service(owner, "
            "name, description, acceptance, deliverable, budget, inputs): the contract. Then request(service, inputs) "
            "asks for it, and feedback(task_id, verdict) tells the owner how it went."
        )
    out: list[str] = []
    if asks:
        out.append("Services you can request (from your direct reports):")
        out += [x for c in asks for x in _service_block(org, c, offered=False)]
    if offers:
        out.append("Services you offer:")
        out += [x for c in offers for x in _service_block(org, c, offered=True)]
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------- prompt


def _quoted(org: ServicesOrg, text: str, where: str) -> str:
    """A playbook shown in the prompt: quoted, so its headings do not mix with the prompt's, cut like messages."""
    if len(text) > RENDER_BODY_CHARS:
        text = (
            text[:RENDER_BODY_CHARS].rstrip()
            + f"\n\n[... playbook cut: {len(text) - RENDER_BODY_CHARS} more characters. Read the rest with read(path=\"{where}\").]"
        )
    return "\n".join(f"> {line}".rstrip() for line in text.splitlines())


def prompt_sections(org: ServicesOrg, addr: str, batch: list[Message]) -> str:
    """The sections of an owner's run prompt: its services, the playbook of each service it has an open request for,
    and (when the batch holds a new request, or the client's rejection of a delivery) what to reflect on first. Empty
    for an agent that owns no service.

    Each section starts and ends with a newline, to be appended after the notice and before "# New messages".
    """
    owned = owned_services(org, addr)
    if not owned:
        return ""
    sections = ["# Your services\nThe contract (SERVICE.md) is your parent's; the playbook (PLAYBOOK.md) is yours."]
    lines = []
    for c in owned:
        pb = read_playbook(org, addr, c.name)
        lines.append(
            f"- {c.name}: contract v{c.version}{' (locked)' if c.locked else ''}, "
            f"{'playbook v' + str(pb.version) if pb.version else 'no playbook yet'}, {len(cases(org, addr, c.name))} request(s) so far; "
            f"contract: {_rel(org, c.path)}; playbook: {_rel(org, service_dir(org, addr, c.name) / 'PLAYBOOK.md')}"
        )
    sections[0] += "\n" + "\n".join(lines)
    working = {t.service for t in org.open_tasks(addr) if t.service}
    new = {m.service for m in batch if m.type == "task" and m.service and not m.revises and m.to == addr}
    rejected = _rejected_services(org, addr, batch)
    digests = {
        c.name: d for c in owned if c.name in new | rejected and (d := reflection_digest(org, addr, c.name)) is not None
    }
    for c in owned:
        if c.name in working:
            sections.append(_playbook_section(org, addr, c, reflecting=c.name in digests))
    for c in owned:
        if c.name in digests:
            sections.append(_reflect_section(
                org, addr, c, digests[c.name], rejected=c.name in rejected, new_request=c.name in new,
            ))
    return "".join(f"\n{s}\n" for s in sections)


def _rejected_services(org: ServicesOrg, addr: str, batch: list[Message]) -> set[str]:
    """The services of ``addr`` for which the batch holds a ``feedback: reject`` note (the client rejected a delivery)."""
    notes = [m for m in batch if m.type == "note" and m.feedback == "reject" and m.to == addr and m.reply_to]
    if not notes:
        return set()
    service_of = {m.id: m.service for m in org.received(addr) if m.type == "task" and m.service}
    return {svc for n in notes if (svc := service_of.get(n.reply_to or ""))}


def _playbook_section(org: ServicesOrg, addr: str, c: Contract, *, reflecting: bool = False) -> str:
    """The playbook of a service with an open request. ``reflecting``: the batch holds a new request and the prompt
    carries a "Reflect before you start" section (evidence to write the first playbook from)."""
    pb = read_playbook(org, addr, c.name)
    who = "locked by your parent" if c.locked else "yours to improve"
    head = f"# Playbook: {c.name} (v{pb.version}, {who})"
    if not pb.version:
        if c.locked:
            return f"{head}\nNo playbook yet, and the contract is locked: plan as usual."
        if reflecting:
            return (
                f"{head}\nNo playbook yet: write v1 now from the evidence below (Reflect before you start), then "
                "follow it."
            )
        return (
            f"{head}\nNo playbook yet: plan as usual; when you report this request, write v1 with revise_playbook "
            "from how it went."
        )
    return f"{head}\n{_quoted(org, pb.body, _rel(org, pb.path))}"


def _reflect_section(org: ServicesOrg, addr: str, c: Contract, digest: str, *, rejected: bool = False, new_request: bool = True) -> str:
    pb = read_playbook(org, addr, c.name)
    cap = playbook_word_cap(org.config)
    since = f"Evidence since v{pb.version}:" if pb.version else "Evidence so far (there is no playbook yet):"
    first = (
        "Look for what repeats, and for anything the client rejected. A rejection or a failure is enough on its own; "
        "a single slow case is not."
    )
    client_wins = (
        "When a lesson of yours conflicts with the client's feedback, the client is right: fix the playbook to match "
        "the feedback (and say so in the reason)."
    )
    raise_bar = (
        "The playbook may raise the bar, never lower it: the acceptance criteria come from the contract and travel "
        "with every request. If the client's feedback is a lasting requirement, also tell your parent (`send`) so it "
        "can add it to the contract."
    )
    what = "rework" if rejected and not new_request else "request"
    if c.locked:
        intro = (
            "Your playbook is how your team delivers this service. The contract is locked by your parent, so you may "
            f"not revise the playbook. {since}"
        )
        steps = [
            first,
            "When a lesson of yours conflicts with the client's feedback, the client is right: follow the feedback.",
            f"You cannot change the playbook, but apply what the evidence shows when you plan this {what}. " + raise_bar,
            f"Then handle the {what} following the playbook.",
        ]
        lead = (
            "The client rejected a delivery. The contract is locked, so you cannot revise the playbook: apply what the "
            f"feedback shows, then handle the {what}."
            if rejected else "Before working on the new request:"
        )
    else:
        intro = f"Your playbook is how your team delivers this service; you own it and improve it. {since}"
        steps = [
            first,
            client_wins,
            "If a change to how the team works would prevent it, call `revise_playbook(service, content, reason)` with "
            f"the whole new playbook (at most {cap} words): concrete steps (who does what, in which order, which "
            f"check), not slogans. Name the cases in the reason. The new version applies to this {what}.",
            raise_bar,
        ]
        if pb.version >= 2:
            steps.append(
                "If the current version did worse than an earlier one, restore that one "
                f"(read {_rel(org, service_dir(org, addr, c.name))}/history/PLAYBOOK.v<k>.md)."
            )
        steps.append(f"If nothing needs to change, do not revise. Then handle the {what} following the playbook.")
        lead = (
            "The client rejected a delivery: decide now whether the playbook must change so this does not happen "
            f"again (revise_playbook), then handle the {what}."
            if rejected else "Before working on the new request:"
        )
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return f"# Reflect before you start: {c.name}\n{intro}\n{digest}\n{lead}\n{numbered}"
