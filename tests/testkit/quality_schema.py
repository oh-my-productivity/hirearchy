"""The schema of ``hirearchy quality --json`` (design 9.4) as data: the keys of every object, their types and their null rules.

``problems(data)`` lists everything in ``data`` that does not fit it (a missing key, a key the schema does not know, a wrong type or value), one
line per problem with the path to it; it is empty for a conforming document. The tests of the JSON and the replay of the E3 corpus use it, so the
table of the design is written once. The rules that tie one key to another (a count equal to a figure of the text) are the tests' own."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

Check = Callable[[Any, str], list[str]]

_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_RATIO = re.compile(r"\d+\.\d{2}")


def _type(name: str, ok: Callable[[Any], bool]) -> Check:
    def check(value: Any, path: str) -> list[str]:
        return [] if ok(value) else [f"{path}: expected {name}, got {value!r}"]
    return check


INT = _type("int", lambda v: isinstance(v, int) and not isinstance(v, bool))
STR = _type("str", lambda v: isinstance(v, str))
BOOL = _type("bool", lambda v: isinstance(v, bool))
TIME = _type("a UTC time (YYYY-MM-DDTHH:MM:SSZ)", lambda v: isinstance(v, str) and _TIME.fullmatch(v) is not None)
RATIO = _type("a two-decimal ratio string", lambda v: isinstance(v, str) and _RATIO.fullmatch(v) is not None)
TRUE = _type("true", lambda v: v is True)


def choice(*values: str) -> Check:
    return _type("one of " + ", ".join(values), lambda v: v in values)


def null(check: Check) -> Check:
    """``check``, or ``null``."""
    return lambda value, path: [] if value is None else check(value, path)


def items(check: Check) -> Check:
    """A list of values that each fit ``check``."""
    def run(value: Any, path: str) -> list[str]:
        if not isinstance(value, list):
            return [f"{path}: expected a list, got {value!r}"]
        return [p for i, x in enumerate(value) for p in check(x, f"{path}[{i}]")]
    return run


def counts(check: Check) -> Check:
    """An object whose keys are free and whose values fit ``check``."""
    def run(value: Any, path: str) -> list[str]:
        if not isinstance(value, dict):
            return [f"{path}: expected an object, got {value!r}"]
        return [p for k, x in value.items() for p in check(x, f"{path}.{k}")]
    return run


def pair(first: Check, second: Check) -> Check:
    def run(value: Any, path: str) -> list[str]:
        if not isinstance(value, list) or len(value) != 2:
            return [f"{path}: expected a list of two, got {value!r}"]
        return first(value[0], f"{path}[0]") + second(value[1], f"{path}[1]")
    return run


def shape(**fields: Check) -> Check:
    """An object with exactly these keys, each fitting its check."""
    def run(value: Any, path: str) -> list[str]:
        if not isinstance(value, dict):
            return [f"{path}: expected an object, got {value!r}"]
        out = [f"{path}.{k}: missing" for k in fields if k not in value]
        out += [f"{path}.{k}: not in the schema" for k in value if k not in fields]
        return out + [p for k, check in fields.items() if k in value for p in check(value[k], f"{path}.{k}")]
    return run


def tagged(by: str, kinds: Mapping[str, Check]) -> Check:
    """An object that names its own shape in the key ``by``."""
    def run(value: Any, path: str) -> list[str]:
        if not isinstance(value, dict) or value.get(by) not in kinds:
            return [f"{path}.{by}: expected one of {', '.join(kinds)}, got {value.get(by) if isinstance(value, dict) else value!r}"]
        return kinds[value[by]](value, path)
    return run


IDS = items(STR)
CASE_TASK = shape(case=STR, task=STR)

CONTRACT_MARK = shape(
    kind=choice("contract"), when=null(TIME), version=INT, by=STR, adds=IDS, removes=IDS, basis=choice("first", "answers", "user", "legacy", "agent"),
    answers=null(STR), confirmed=items(shape(id=STR, link=STR)), not_confirmed=IDS,
)
PLAYBOOK_MARK = shape(
    kind=choice("playbook"), when=null(TIME), version=INT, by=STR,
    basis=choice("c", "b", "first", "restore", "migrate", "exempt", "watch", "client", "legacy"),
    op=choice("", "first", "migrate", "add", "edit", "retire", "restore", "move", "watch"), item=STR, item_kind=choice("", "step", "rule"), restores=null(INT),
    evidence=IDS, evidence_other=INT, changed=INT, removed=INT, own_words=null(INT), beyond=null(INT), tagged=null(INT), untagged=null(INT),
    cited=items(shape(id=STR, text=STR)), lines=items(shape(text=STR, own_words=BOOL)), lines_more=INT, agent_written=TRUE,
)
CHARTER_MARK = shape(kind=choice("charter"), when=TIME, addr=STR, commit=STR)
MODEL_MARK = shape(kind=choice("model"), when=TIME, addr=STR, key=choice("model", "default_model", "effort"), before=STR, after=STR, commit=STR)
TOP_UP_MARK = shape(kind=choice("top-up"), when=null(TIME), case=STR, id=STR, source=choice("human", "relayed", "unrecorded", "granted"), amount=INT)
MARK = tagged("kind", {"contract": CONTRACT_MARK, "playbook": PLAYBOOK_MARK, "charter": CHARTER_MARK, "model": MODEL_MARK, "top-up": TOP_UP_MARK})

FIRST = shape(
    task=STR, outcome=choice("accepted", "rejected", "neither", "none"), superseded_by=null(STR), superseded_source=null(choice("human", "relayed", "unrecorded")),
)
CASE = shape(
    id=STR, title=STR, assignee=STR, state=choice("done", "failed", "blocked", "open"), stalled=null(BOOL), tasks=INT, budget=INT, user_approved=INT,
    runs=null(INT), credited=null(INT), relayed_runs=null(INT), spend=null(INT), user_cost=null(INT), ratio=null(RATIO), cut=BOOL, runs_unknown=STR,
    top_ups=items(shape(id=STR, source=choice("human", "relayed", "unrecorded", "granted"), amount=INT)), first=null(FIRST),
)
ESCAPE = shape(
    assertion=null(STR), case=STR, task=STR, verdict=STR, signer=STR, cause=choice("relayed-error", "relayed-carry-over", "contract-gap", "reviewer-miss", "untyped"),
    rule=STR, rules=IDS, detail=IDS, also=IDS, before_verdict=STR, attribution=choice("counted", "not its"), **{"class": null(choice("off_spec"))},
)
VERIFIER = shape(
    addr=STR, judged=INT, escapes=shape(counted=counts(INT), not_its=counts(INT)), pass_precision=pair(INT, INT), rechecks=null(INT), rework_runs=null(INT),
    fails_error=STR,
)
REPEAT = shape(
    state=choice("fires", "no", "n/a", "does not apply"), judged=INT, window=IDS, subjects=counts(INT), fired=IDS, not_counted=counts(IDS),
)
COST = shape(
    state=choice("fires", "no", "n/a"), judged=INT, compared=INT,
    cases=items(shape(case=STR, user_cost=INT, user_approved=INT, ratio=RATIO, relayed_runs=INT, total=INT)),
    skipped=items(shape(case=STR, reason=choice("budget 0", "runs not counted"))),
)
DELIVERIES = shape(
    total=INT, judged=INT, unjudged_cases=IDS, relayed_only=IDS, unseen_relayed=IDS, not_as_delivered=items(CASE_TASK), neither=items(CASE_TASK),
    legacy_verdicts=INT, not_on_a_delivery=IDS,
)
RECORD = shape(
    owner=STR, service=STR, client=STR, client_kind=STR, unit=STR, error=STR, files_error=STR, stalled_error=STR, contract=INT, playbook=INT, budget=null(INT),
    cases=items(CASE), first_deliveries=shape(accepted=INT, rejected=INT, no_verdict=INT, superseded=INT, neither=INT, never_delivered=INT),
    deliveries=DELIVERIES, escapes=items(ESCAPE), verifiers=items(VERIFIER),
    alarms=lambda value, path: [] if value == {} else shape(repeat=REPEAT, cost=COST)(value, path),  # an error record has {}
    timeline=items(MARK), history=null(shape(known=BOOL, truncated=BOOL, skipped=INT)),
    watch=items(shape(
        item=STR, kind=choice("step", "rule"), state=choice("new", "warning", "retired", "restored", "kept"), k=INT, r=pair(INT, INT), clean=INT, waiting=INT,
        related=IDS, pending=IDS, since=null(TIME), carried=STR,
    )),
)
HELD_TASK = shape(id=STR, sender=STR, title=null(STR), blocked=TIME, left_blocked=BOOL, sent_since=INT)
DOCUMENT = shape(
    schema=_type("1", lambda v: v == 1 and not isinstance(v, bool)),
    thresholds=shape(min_judged=INT, repeat_window=INT, repeat_failures=INT, cost_ratio=STR, source=choice("defaults", "ORG.md")), notes=items(STR),
    services=items(RECORD), one_off=null(RECORD),
    nested=items(shape(owner=STR, service=STR, client=STR, cases=INT, delivered=INT, agent_verdicts=INT, error=STR)),
    moved_past=items(shape(addr=STR, held=null(INT), held_error=STR, error=STR, tasks=items(HELD_TASK))),
)


def problems(data: object) -> list[str]:
    """Everything in ``data`` that is not what 9.4 says, one line per problem; empty for a conforming document."""
    return DOCUMENT(data, "$")
