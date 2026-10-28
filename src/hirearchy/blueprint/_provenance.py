"""Criteria provenance (design 10.1, F-P1-3): where each acceptance criterion comes from, and the refusals that bind the form of the citation.

A criterion is a string (as always) or a mapping ``{text, from, asked}`` (the user's exact words it rests on, with the question they answered),
``{text, default: true}`` (root's proposal, accepted with the plan) or, in an extension only, ``{text, from_tasks: [...]}``. ``needs.elicitation``
holds the user's answers, verbatim. Whether a criterion says what the user meant is their judgement at the gate; these rules check only the form."""

from __future__ import annotations

from collections.abc import Mapping

from ..services import added_words
from ._view import mapping_or_empty, needs_of, s, services_of
from .api import Issue

CRITERION_KEYS = ("text", "from", "asked", "default", "from_tasks")
SOURCE_KEYS = ("from", "default", "from_tasks")
TEXT_MAX = 1000
FROM_MAX = 1000
ASKED_MAX = 300
ELICITATION_MAX = 4000
FROM_TASKS_MAX = 20

BAD_TEXT = "criterion {i} has no text of 1 to " + str(TEXT_MAX) + " characters: a criterion is a string or {{text: <the criterion>, from: <the user's exact words> | default: true}}."
UNKNOWN_KEY = "criterion {i} has the unknown key '{key}' (known: " + ", ".join(CRITERION_KEYS) + ")."
TWO_SOURCES = "criterion {i} gives more than one source ({given}): give exactly one of from, default or from_tasks."
BAD_FROM = "criterion {i}: from is the user's exact words, 1 to " + str(FROM_MAX) + " characters."
BAD_DEFAULT = "criterion {i}: default is true, or left out."
OUTSIDE_EXTENSION = "criterion {i}: from_tasks copies criteria of earlier one-off tasks, which only an extension of the current organization can do."
BAD_FROM_TASKS = "criterion {i}: from_tasks is a list of 1 to " + str(FROM_TASKS_MAX) + " case-head ids."
BAD_ASKED = "criterion {i}: asked is the question the quote answered, at most " + str(ASKED_MAX) + " characters, and only with from."
NOT_IN_WORDS = 'criterion {i} quotes words that are not in needs.elicitation: "{quote}". Quote the user\'s own words exactly, or mark it default: true.'
NO_WORDS = "criterion {i} quotes the user, but needs.elicitation is missing: put their answers there, verbatim."
NO_SOURCE = "criterion {i} does not say where it comes from: give from: <the user's exact words in needs.elicitation> or default: true."
NO_RECORD = (
    "this plan records none of the user's words, so no criterion can show where it comes from. Put their answers, verbatim, in needs.elicitation "
    "(for a plan with only defaults: their request in their words), and give each criterion from: or default: true."
)
FROM_LINE = 'from your words "{quote}"{asked}; words I added: {added}'
ASKED_LINE = ' (my question: "{asked}")'
DEFAULT_LINE = "my default: you did not say this"
UNRECORDED_LINE = "my wording: your words for it were not recorded"
SHOWN_ADDED = 8  # the words a source line lists before it says how many more
BAD_ELICITATION = "needs.elicitation is the user's answers, verbatim: a text of 1 to " + str(ELICITATION_MAX) + " characters."


def _fold(text: str) -> str:
    """Whitespace collapsed and case folded: the form in which a quote is compared with the recorded words."""
    return " ".join(text.split()).casefold()


def _form_problem(c: Mapping[str, object], i: int, extension: bool) -> str | None:
    """What is wrong with the form of the mapping criterion number ``i`` (1-based), or None."""
    text = c.get("text")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= TEXT_MAX:
        return BAD_TEXT.format(i=i)
    for key in c:
        if key not in CRITERION_KEYS:
            return UNKNOWN_KEY.format(i=i, key=key)
    given = [k for k in SOURCE_KEYS if k in c]
    if len(given) > 1:
        return TWO_SOURCES.format(i=i, given=", ".join(given))
    if "from" in c and (not isinstance(c["from"], str) or not 1 <= len(c["from"].strip()) <= FROM_MAX):
        return BAD_FROM.format(i=i)
    if "default" in c and c["default"] is not True:
        return BAD_DEFAULT.format(i=i)
    if "from_tasks" in c:
        if not extension:
            return OUTSIDE_EXTENSION.format(i=i)
        ids = c["from_tasks"]
        if not isinstance(ids, list) or not 1 <= len(ids) <= FROM_TASKS_MAX or not all(isinstance(x, str) and x.strip() for x in ids):
            return BAD_FROM_TASKS.format(i=i)
    if "asked" in c and ("from" not in c or not isinstance(c["asked"], str) or len(c["asked"].strip()) > ASKED_MAX):
        return BAD_ASKED.format(i=i)
    return None


def source_line(entry: object) -> str:
    """The line the gate shows under a criterion (design 10.1 step 4): the user's words it rests on and the words root added, root's default, or
    that its source was not recorded. ``entry`` is the criterion as written (a string or a mapping)."""
    if isinstance(entry, dict):
        quote = entry.get("from")
        if isinstance(quote, str) and quote.strip():
            asked = entry.get("asked")
            question = " ".join(asked.split()) if isinstance(asked, str) else ""
            added = added_words(s(entry.get("text")), quote, question)
            listed = ", ".join(added[:SHOWN_ADDED]) + (f", +{len(added) - SHOWN_ADDED} more" if len(added) > SHOWN_ADDED else "") if added else "none"
            return FROM_LINE.format(quote=" ".join(quote.split()), asked=ASKED_LINE.format(asked=question) if question else "", added=listed)
        if entry.get("default") is True:
            return DEFAULT_LINE
    return UNRECORDED_LINE


def criterion_issues(bp: Mapping[str, object], *, extension: bool, require_sources: bool) -> list[Issue]:
    """The provenance issues of a blueprint's criteria (``task.acceptance`` and each service's ``acceptance``): ``criterion-form`` and
    ``criterion-from`` (errors everywhere), a bad ``needs.elicitation``, and the two a plan without sources earns: ``criterion-source`` (a
    criterion that says nothing of where it comes from) and ``criterion-words`` (no recorded words at all). ``extension``: the blueprint extends
    the current organization (``from_tasks`` is allowed). ``require_sources``: over MCP, where those two are errors; at the terminal, warnings."""
    level = "error" if require_sources else "warning"
    issues: list[Issue] = []
    sourced = False  # some criterion rests on the user's words or on root's default, or has no source: the plan needs the words
    elicitation = needs_of(bp).get("elicitation")
    words: str | None = ""
    if elicitation is not None:
        if isinstance(elicitation, str) and len(elicitation.strip()) <= ELICITATION_MAX:
            words = _fold(elicitation)
        else:
            words = None  # reported once here; no quote is judged against words that are not usable
            issues.append(Issue("error", "needs.elicitation", BAD_ELICITATION, "criterion-words"))
    lists: list[tuple[str, list[object]]] = []
    task = mapping_or_empty(bp.get("task"))
    if isinstance(task.get("acceptance"), list):
        lists.append(("task.acceptance", task["acceptance"]))
    for n, sv in enumerate(services_of(bp)):
        if isinstance(sv.get("acceptance"), list):
            lists.append((f"services[{s(sv.get('name')) or n}].acceptance", sv["acceptance"]))
    for where, criteria in lists:
        for i, c in enumerate(criteria, 1):
            if not isinstance(c, dict):
                if s(c):
                    sourced = True
                    issues.append(Issue(level, f"{where}[{i}]", NO_SOURCE.format(i=i), "criterion-source"))
                continue
            problem = _form_problem(c, i, extension)
            if problem is not None:
                issues.append(Issue("error", f"{where}[{i}]", problem, "criterion-form"))
                continue
            if "from_tasks" not in c:
                sourced = True
            if "from" in c and words is not None:
                if not words:
                    issues.append(Issue("error", f"{where}[{i}]", NO_WORDS.format(i=i), "criterion-from"))
                elif _fold(c["from"]) not in words:
                    issues.append(Issue("error", f"{where}[{i}]", NOT_IN_WORDS.format(i=i, quote=c["from"].strip()), "criterion-from"))
            elif not any(k in c for k in SOURCE_KEYS):
                issues.append(Issue(level, f"{where}[{i}]", NO_SOURCE.format(i=i), "criterion-source"))
    if sourced and words == "":
        issues.append(Issue(level, "needs.elicitation", NO_RECORD, "criterion-words"))
    return issues
