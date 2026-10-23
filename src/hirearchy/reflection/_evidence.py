"""The evidence gate and the ids a verdict may name, judged from the cases of a service (``services``' ``ServiceEvidence`` port, implemented here).

``services`` cannot import ``reflection``, which derives the cases, so the gate behind ``revise_playbook`` lives here and ``app`` wires it into
``services`` (the pattern of ``dispatch.ReworkContext``, which ``services`` implements). A revision is admitted by rule (b), the same criterion or
regression assertion failed in two different cases the human client rejected, or by rule (c), it cites a criterion the human client added to the
contract by an amendment and confirmed (a human ``confirms`` link names it: the user's recorded yes). Lessons, relayed verdicts and an agent
client's verdicts weigh nothing.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence

from ..kernel import ROOT, OrgError, clip_line, link_ids, parent, verdict_tier
from ..services import (
    Admission, AmendmentBasis, Criterion, Rejection, ServiceCatalog, ServiceEvidence, confirmed_amendments, line_key, normalize_evidence,
    normalize_links,
)
from .api import Assertion, CaseHistory, Verdict, confirmed_criteria, delivered_unrated, regressions

REASON_CLIP = 200  # characters of the reason in the question of a refusal
WORDS_CLIP = 300  # characters of the client's words in the question of a refusal
EXEMPTION = "no evidence needed"
LINES_LISTED = 10  # offending lines a refusal quotes
LINE_CLIP = 600  # characters of one quoted line
RULE_TEXT_CLIP = 300  # characters of a criterion's text in "Write it as ..."
QUESTION_LINE_CLIP = 160  # characters of the first offending line in the question
LINES_REFUSED = (
    "refused: every line a revision adds or changes must rest on the evidence it cites, and {n} line(s) do not:\n"
    "{listing}\n"
    "{c_part}{b_part}A change of punctuation, spacing, list numbering or markdown alone needs nothing. Nothing was written: revise again "
    "without these lines, or send {client} (`send`) this question once: "
    '"We would add to how we deliver {service}: {first}. Is that what you want from now on? If yes, please add it to the contract as a criterion."'
)


class CaseServiceEvidence(ServiceEvidence):
    """Reads the cases of a service (``CaseHistory``) and its contract history (``ServiceCatalog``) to say what they prove."""

    def __init__(self, history: CaseHistory, catalog: ServiceCatalog) -> None:
        self._history = history
        self._catalog = catalog

    def links(self, owner: str, service: str, ids: Sequence[str], *, verdict: str | None = None) -> tuple[str, ...]:
        wanted = normalize_links(list(ids))
        criteria = [c.id for c in self._catalog.criteria(owner, service)]
        found = regressions(self._history.cases(owner, service))
        named = [a.id for a in found]
        unknown = [x for x in wanted if x != "none" and x not in criteria and x not in named]
        if unknown:
            raise OrgError(
                f"unknown criterion or assertion for `{service}`: {', '.join(unknown)}. Its criteria: {', '.join(criteria) or 'none'}; "
                f"its regression assertions: {', '.join(named) or 'none yet'} (see `services`)."
            )
        itself = next((a.id for a in found if a.verdict.message.id == verdict), None) if verdict else None
        if itself in wanted:
            raise OrgError(f"{itself} is this rejection itself: name the criterion it is about, or the earlier rejection it repeats.")
        return wanted

    def confirmed(self, owner: str, service: str) -> frozenset[str]:
        return confirmed_criteria(self._history.cases(owner, service), self._catalog.criteria(owner, service))

    def amendment_basis(self, owner: str, service: str) -> AmendmentBasis:
        cases = self._history.cases(owner, service)
        found = regressions(cases)
        titles = {t.id: t.title for c in cases for t in c.tasks}
        rejections = tuple(
            Rejection(
                note=a.verdict.message.id, assertion=a.id, task=a.verdict.task_id, title=titles.get(a.verdict.task_id, ""),
                earlier=tuple(x.id for x in found[:k]), words=a.verdict.note,
                answered=next((m.id for m in a.verdict.link_notes if verdict_tier(m) == "human"), ""),
            )
            for k, a in enumerate(found)
        )
        return AmendmentBasis(rejections, delivered_unrated(cases))

    def admit(
        self, owner: str, service: str, evidence: Sequence[str], reason: str, *, exempt: str | None = None, lines: Sequence[str] = (),
    ) -> Admission:
        ids = normalize_evidence(list(evidence))
        crit = {c.id: c for c in self._catalog.criteria(owner, service)}
        cases = self._history.cases(owner, service)
        found = regressions(cases)
        confirmed = confirmed_criteria(cases, list(crit.values()))
        eligible = confirmed_amendments(list(crit.values()), confirmed)
        client = parent(owner) or ROOT
        subjects: set[str] = set()  # what the revision rests on, once the human client's own evidence is picked out
        cited_cases: set[str] = set()  # the cases of the assertions it cites
        notes: list[str] = []  # why a cited id weighs nothing
        unknown: list[str] = []

        by_assertion = {a.id: a for a in found}
        by_verdict = {v.message.id: (v, c) for c in cases for v in c.verdicts}
        by_task = {t.id: c for c in cases for t in c.tasks}
        by_result = {r: c for c in cases for r in [*c.lesson_ids, *([c.result.id] if c.result is not None else [])]}
        by_link = {m.id: (m, v) for c in cases for v in c.verdicts for m in v.link_notes}
        assertion_of = {a.verdict.message.id: a for a in found}

        def count(a: Assertion) -> None:
            subjects.add(a.id)
            subjects.update(x for x in a.about if x in crit and crit[x].current)
            cited_cases.add(a.case)

        for x in ids:
            if x in crit:
                c = crit[x]
                if not c.current:
                    notes.append(f"{x} is no longer in the contract: cite a current criterion (see `services`)")
                    continue
                subjects.add(x)
                if not c.amended:
                    notes.append(f"{x} is in the contract since v{c.since}, not added by an amendment, and failed in no case the client rejected")
                elif x not in confirmed:
                    notes.append(f"{x} was added to the contract by an amendment (v{c.since}), but the client's yes to it is not recorded (not confirmed)")
            elif x in by_assertion:
                count(by_assertion[x])
            elif x in by_verdict:
                v, _ = by_verdict[x]
                if x in assertion_of:
                    count(assertion_of[x])
                else:
                    notes.append(_verdict_note(v))
            elif x in by_task:
                case = by_task[x]
                mine = [a for a in found if a.case == case.id]
                for a in mine:
                    count(a)
                if not mine:
                    relayed = f"; {case.relayed_reworks} of its reworks were relayed (the assistant's own reading)" if case.relayed_reworks else ""
                    notes.append(f"case {case.id} has no rejection by the client{relayed}")
            elif x in by_result:
                notes.append(f"{x} is a result: its lessons are your team's view")
            elif x in by_link:
                link, v = by_link[x]
                if verdict_tier(link) == "human":  # the user's recorded yes: it stands for the rejection and the criteria it names
                    if v.message.id in assertion_of:
                        count(assertion_of[v.message.id])
                    subjects.update(k for k in link_ids(link) if k in crit and crit[k].current)
                elif verdict_tier(link) == "agent":
                    notes.append(f"link {x} is an agent client's (a hypothesis)")
                else:
                    notes.append(f"link {x} is relayed (the assistant's own reading)")
            else:
                unknown.append(x)

        if unknown:
            raise OrgError(
                f"unknown evidence for `{service}`: {', '.join(unknown)}. Evidence is a criterion ({', '.join(crit) or 'none'}), a regression "
                f"assertion ({', '.join(by_assertion) or 'none yet'}), or the id of a verdict or a case of this service: see the regression list "
                "and the digest in your prompt. Nothing was written."
            )
        if exempt:
            return Admission(exempt, ids, EXEMPTION)
        if client != ROOT:
            raise OrgError(
                f"refused: the client of `{service}` is {client}, an agent, so its verdicts are hypotheses and nothing in this service's history "
                "can admit a revision (rules (b) and (c) need the human client). Nothing was written. Follow the playbook and the contract; if "
                f"you think the playbook must change, send {client} (`send`) what you would change and why."
            )

        added = [c for c in eligible if c.id in subjects]
        order = {c.id: i for i, c in enumerate(cases)}

        def cases_of(x: str) -> list[str]:
            return sorted({a.case for a in found if x == a.id or x in a.about}, key=order.__getitem__)

        qualifying = [x for x in sorted(subjects) if len(cases_of(x)) >= 2]  # the subjects that failed in 2 different cases the client rejected
        if added or qualifying:
            return self._admitted(service, client, ids, added, qualifying, by_assertion, lines, cases_of)

        single = [
            a for a in found
            if a.case in cited_cases or any(x in subjects and len(cases_of(x)) == 1 for x in (a.id, *a.about))
        ]
        where = ", ".join(c.id for c in eligible) or "none yet"
        if single:
            raise OrgError(_one_case(service, client, where, crit, max(single, key=lambda a: a.verdict.message.id)))
        raise OrgError(_no_client_evidence(service, client, where, notes, reason))


    @staticmethod
    def _admitted(
        service: str, client: str, ids: tuple[str, ...], added: Sequence[Criterion], qualifying: Sequence[str], assertions: Mapping[str, Assertion],
        lines: Sequence[str], cases_of: Callable[[str], list[str]],
    ) -> Admission:
        """The evidence stage found a rule; now every line the revision adds or changes must rest on it (4.1): under rule (c) it is the cited
        criterion's own words with its id, under rule (b) it carries a qualifying id. Any other line refuses the whole revision."""
        tags = [*qualifying, *(x for x in ids if x in assertions and not set(assertions[x].about).isdisjoint(qualifying) and x not in qualifying)]
        admitted: list[tuple[str, str]] = []
        offending: list[str] = []
        tagged = False  # some admitted line rests on rule (b)
        for line in lines:
            words, tag = _words_of(line, added), _tag_of(line, tags)
            if words or tag:
                admitted.append((words or tag or "", line))
                tagged = tagged or not words
            else:
                offending.append(line)
        if offending:
            raise OrgError(_lines_refused(service, client, offending, added, tags))
        if added and not tagged:
            since = ", ".join(f"v{n}" for n in sorted({c.since for c in added}))
            detail = f"cites {', '.join(c.id for c in added)}, which {client} added to the contract ({since}) and the client confirmed"
            return Admission("c", ids, detail, lines=tuple(admitted))
        failed = cases_of(qualifying[0])
        return Admission("b", ids, f"{qualifying[0]} failed in {len(failed)} cases the client rejected: {', '.join(failed)}", lines=tuple(admitted))


def _words_of(line: str, added: Sequence[Criterion]) -> str | None:
    """The id of the cited confirmed criterion whose own words ``line`` is (``- C9: <its text>``, ``2. C9: <its text>`` or ``<its text> (C9)``), else
    None. A criterion whose text has no letter or digit has an empty key and admits no line: a bare id would otherwise be its "words"."""
    key = line_key(line)
    for c in added:
        text = line_key(c.text)
        if text and key in (line_key(c.id) + text, text + line_key(c.id)):
            return c.id
    return None


def _tag_of(line: str, tags: Sequence[str]) -> str | None:
    """The first of ``tags`` that ``line`` carries as a standalone token (``[C6]``; not ``C60`` or ``XC6``), else None."""
    return next((x for x in tags if re.search(rf"(?<![A-Za-z0-9]){re.escape(x)}(?![0-9])", line, re.IGNORECASE)), None)


def _lines_refused(service: str, client: str, offending: Sequence[str], added: Sequence[Criterion], tags: Sequence[str]) -> str:
    """P1-REFUSED: the lines that rest on nothing, at most ``LINES_LISTED`` of them, and what each rule would have admitted."""
    listing = [f'- "{clip_line(line, LINE_CLIP)}"' for line in offending[:LINES_LISTED]]
    if len(offending) > LINES_LISTED:
        listing.append(f"- and {len(offending) - LINES_LISTED} more")
    c_part = b_part = ""
    if added:
        names = [f"{c.id}'s" for c in added]
        whose = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} or {names[-1]}"
        c_part = (
            "Rule (c) admits only the cited confirmed criterion's own words, one line each with its id: "
            f"these lines are not {whose} words. "
        ) + "".join(f'Write it as "- {c.id}: {clip_line(c.text, RULE_TEXT_CLIP)}". ' for c in added if line_key(c.text))
    if tags:
        shown = ", ".join(f'"[{x}]"' for x in tags)
        b_part = f"Rule (b) admits a line that carries the id it rests on ({shown}): these lines carry none. "
    return LINES_REFUSED.format(
        n=len(offending), listing="\n".join(listing), c_part=c_part, b_part=b_part, client=client, service=service,
        first=clip_line(offending[0], QUESTION_LINE_CLIP),
    )


def _verdict_note(v: Verdict) -> str:
    if v.tier == "relayed":
        return f"verdict {v.message.id} is relayed (the assistant's own reading)"
    if v.tier == "agent":
        return f"verdict {v.message.id} is an agent client's (a hypothesis)"
    return f"verdict {v.message.id} is an accept"


def _no_client_evidence(service: str, client: str, amended: str, notes: Sequence[str], reason: str) -> str:
    """G1: none of the evidence is the client's own."""
    return (
        f"refused: none of this evidence is the client's own: {'; '.join(notes) or 'no evidence given'}. A revision is admitted only when (b) the "
        f"same criterion or regression assertion failed in 2 different cases the client rejected, or (c) it cites a criterion {client} added to "
        f"the contract by an amendment the client confirmed ({amended}). Your team's lessons, relayed verdicts (the assistant's own reading) and an agent client's "
        "verdicts weigh nothing. Nothing was written: follow the playbook and the contract.\n"
        f"If you think the client wants this from now on, send {client} (`send`) this question once, and do not wait for an answer (it reaches "
        f'you as a contract change or a criterion link): "We would change how we deliver {service}: {clip_line(reason, REASON_CLIP)}. Is that '
        'what you want from now on? If yes, please add it to the contract as a criterion."'
    )


def _one_case(service: str, client: str, amended: str, crit: Mapping[str, Criterion], g: Assertion) -> str:
    """G2: the client rejected this in one case only. The criteria offered for clarification are the assertion's current ones (a removed criterion
    is never offered)."""
    current = [x for x in g.about if x in crit and crit[x].current]
    return (
        f"refused: the client rejected this in one case only ({g.case}), and the evidence cites no criterion {client} added to the contract by an "
        f"amendment the client confirmed ({amended}). One case is a reason to ask, not to change how the team works: a lasting requirement goes into the contract "
        "first. Nothing was written: apply the client's words to the work at hand without changing the playbook.\n"
        f"Send {client} (`send`) this question once, and do not wait for an answer (it reaches you as a contract change or a criterion link): "
        f'"In case {g.case} you said: "{clip_line(g.verdict.note, WORDS_CLIP)}". Is that a lasting requirement? If yes, which criterion should '
        f'say it: a new one, or a clarification of {" / ".join(current) or "an existing one"}?" Revise when the answer is in the contract (cite '
        "its new criterion), or when a second case shows the same criterion failing."
    )
