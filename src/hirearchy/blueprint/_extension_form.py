"""The form of an extension blueprint (design 5.1, 5.2 ``extend-form``, ``extend-placeholder``, ``extend-keeps``): pure rules over the mapping, no
organization read. An extension is ``{reason, needs: {elicitation, budget_runs}, extend: {<section>: [entry, ...]}}``."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping

from ._view import AGENT_KEYS, SERVICE_KEYS, s
from .api import Issue

SECTIONS = ("add_agents", "add_services", "add_charter_lines", "remove_charter_lines", "limits", "budgets", "schedules", "retire_services", "retire")
TOP_KEYS = ("reason", "needs", "extend")
EXTENSION_NEEDS_KEYS = ("elicitation", "budget_runs")
ENTRY_KEYS: Mapping[str, tuple[str, ...]] = {
    "add_agents": (*sorted(AGENT_KEYS), "parent", "charter_extra"),
    "add_services": tuple(sorted(SERVICE_KEYS)),
    "add_charter_lines": ("agent", "line"),
    "remove_charter_lines": ("agent", "line"),
    "limits": ("agent", "org", "can_hire", "max_children", "value"),
    "budgets": ("owner", "service", "budget"),
    "retire_services": ("owner", "service", "reason"),
    "retire": ("agent", "reason"),
    "schedules": (),
}
ENTRIES_MAX = 20
REASON_MAX = 300
PLACEHOLDER = re.compile(r"<[A-Za-z][^<>\n]*>")

NOT_A_MAPPING = "an extension is a mapping with reason, needs and extend; extend is a mapping of sections ({sections}), each a list of entries."
NOT_EXTENDING = "an extension has the top-level keys reason, needs and extend only; '{key}' is not one of them (a full blueprint builds a new team: leave extend out)."
BAD_REASON = "reason is one line of 1 to " + str(REASON_MAX) + " characters: the brief's item (B3.1) or the user's own words."
BAD_NEEDS = "needs of an extension may hold only elicitation and budget_runs, not '{key}'."
EMPTY_EXTEND = "extend holds no entry: give at least one entry in one of " + ", ".join(SECTIONS) + "."
UNKNOWN_SECTION = "extend has the unknown section '{key}' (known: {sections})."
NOT_A_LIST = "extend.{section} is a list of entries."
NOT_AN_ENTRY = "extend.{section}[{i}] is a mapping."
TOO_MANY = "extend.{section} has {n} entries; at most " + str(ENTRIES_MAX) + " per change: split it into two changes."
UNKNOWN_KEY = "{path} has the unknown key '{key}' (known: {known})."
NO_SCHEDULES = "schedules are not part of this version of hirearchy: leave the section out."
HOLDS_PLACEHOLDER = "{path} still holds a placeholder ({text}): replace it with what the user said, or ask them."
KEEPS = "an extension cannot change {what}: {why}. {how}"

CRITERIA = ("the criteria of {service}", "they change only with the user's words", "Use define_service(owner, name, add_acceptance=..., words=<their words>)")
PLAYBOOK = ("the playbook of {service}", "the owner keeps it and revises it from the client's evidence", "The owner changes it with revise_playbook")
CHARTER = (
    "the charter of {agent}", "an existing charter changes only through its added section",
    "Use add_charter_lines or remove_charter_lines, or edit the charter at the terminal",
)
OWN_BUDGET = (
    "the budget of {agent}", "spend is handed down with send(budget=N) under today's rules",
    "Hand runs down with send(to, ..., budget=N); budgets changes the per-request budget of a service",
)
SETTING = (
    "the ORG.md setting {key}", "ORG.md's rules and settings are the user's, except max_depth",
    "Change it at the terminal; limits: [{{org: max_depth, value: N}}] changes the depth",
)
ACCESS_VERBS = {"tools": "are", "inputs": "are", "model": "is", "workspace": "is"}
ACCESS_WHY = "an existing agent's {key} {verb} the plan it was approved with"
ACCESS_HOW = "Add a new agent with those {key}, or change them at the terminal"
KEEPS_BY_KEY: Mapping[str, tuple[str, str, str]] = {
    "acceptance": CRITERIA, "add_acceptance": CRITERIA, "remove_acceptance": CRITERIA, "criteria": CRITERIA, "playbook": PLAYBOOK,
    "charter": CHARTER, "body": CHARTER, "role": CHARTER, "budget": OWN_BUDGET, "mission": SETTING, "rules": SETTING,
}


def keeps_message(section: str, entry: Mapping[str, object], key: str) -> str | None:
    """The ``extend-keeps`` text for the key ``key`` of an entry of ``section``, or None when the key is not a forbidden change. The entries that
    add something new (``add_agents``, ``add_services``) may name any of these keys: they are the new thing's own."""
    if section in ("add_agents", "add_services"):
        return None
    agent, service = s(entry.get("agent")) or s(entry.get("owner")), s(entry.get("service")) or s(entry.get("name"))
    if key in ACCESS_VERBS:
        return KEEPS.format(
            what=f"the {key} of {agent or 'an agent'}", why=ACCESS_WHY.format(key=key, verb=ACCESS_VERBS[key]), how=ACCESS_HOW.format(key=key),
        )
    if key == "budget" and section != "limits" or key == "agent" and section != "budgets":
        return None
    triple = OWN_BUDGET if key == "agent" else KEEPS_BY_KEY.get(key)
    if triple is None:
        return None
    what, why, how = triple
    return KEEPS.format(what=what.format(service=service or "a service", agent=agent or "an agent", key=key), why=why, how=how.format())


def _strings(value: object, path: str) -> Iterator[tuple[str, str]]:
    """Every string of a nested value with its path."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for k, v in value.items():
            yield from _strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _strings(v, f"{path}[{i}]")


def _entries(extend: Mapping[str, object], issues: list[Issue]) -> list[tuple[str, int, Mapping[str, object]]]:
    """The entries of every known section that are mappings, with their section and position; the rest of the form problems go to ``issues``."""
    found: list[tuple[str, int, Mapping[str, object]]] = []
    for section, entries in extend.items():
        if section not in SECTIONS:
            issues.append(Issue("error", "extend", UNKNOWN_SECTION.format(key=section, sections=", ".join(SECTIONS)), "extend-form"))
        elif not isinstance(entries, list):
            issues.append(Issue("error", f"extend.{section}", NOT_A_LIST.format(section=section), "extend-form"))
        else:
            if len(entries) > ENTRIES_MAX:
                issues.append(Issue("error", f"extend.{section}", TOO_MANY.format(section=section, n=len(entries)), "extend-form"))
            for i, entry in enumerate(entries):
                if not isinstance(entry, Mapping):
                    issues.append(Issue("error", f"extend.{section}[{i}]", NOT_AN_ENTRY.format(section=section, i=i), "extend-form"))
                else:
                    found.append((section, i, entry))
    return found


def form_issues(bp: Mapping[str, object]) -> list[Issue]:
    """What is wrong with the form of the extension ``bp`` (design 5.2: ``extend-form``, ``extend-placeholder`` and the ``extend-keeps`` of 5.1)."""
    issues: list[Issue] = []
    for key in bp:
        if key not in TOP_KEYS:
            issues.append(Issue("error", s(key), NOT_EXTENDING.format(key=key), "extend-form"))
    reason = bp.get("reason")
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= REASON_MAX or "\n" in reason.strip():
        issues.append(Issue("error", "reason", BAD_REASON, "extend-form"))
    needs = bp.get("needs")
    if needs is not None:
        if not isinstance(needs, Mapping):
            issues.append(Issue("error", "needs", BAD_NEEDS.format(key=needs), "extend-form"))
        else:
            issues += [Issue("error", f"needs.{k}", BAD_NEEDS.format(key=k), "extend-form") for k in needs if k not in EXTENSION_NEEDS_KEYS]
    extend = bp.get("extend")
    if not isinstance(extend, Mapping):
        issues.append(Issue("error", "extend", NOT_A_MAPPING.format(sections=", ".join(SECTIONS)), "extend-form"))
        return issues
    entries = _entries(extend, issues)
    if not entries and not any(i.path.startswith("extend") for i in issues):
        issues.append(Issue("error", "extend", EMPTY_EXTEND, "extend-form"))
    for section, i, entry in entries:
        where = f"extend.{section}[{i}]"
        if section == "schedules":
            issues.append(Issue("error", where, NO_SCHEDULES, "extend-form"))
            continue
        for key in entry:
            kept = keeps_message(section, entry, str(key))
            if kept is not None:
                issues.append(Issue("error", where, kept, "extend-keeps"))
            elif key not in ENTRY_KEYS[section]:
                issues.append(Issue("error", where, UNKNOWN_KEY.format(path=where, key=key, known=", ".join(ENTRY_KEYS[section])), "extend-form"))
        if section == "limits" and "org" in entry and s(entry.get("org")) != "max_depth":
            what, why, how = SETTING
            issues.append(Issue("error", where, KEEPS.format(what=what.format(key=s(entry.get("org"))), why=why, how=how.format()), "extend-keeps"))
    for path, text in _strings(bp, ""):
        if (found := PLACEHOLDER.search(text)) is not None:
            issues.append(Issue("error", path, HOLDS_PLACEHOLDER.format(path=path, text=found.group(0)), "extend-placeholder"))
    return issues
