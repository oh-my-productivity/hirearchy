"""Criteria as the callers write them: a list of strings, or one newline-separated string."""

from __future__ import annotations

from ..kernel import JsonObject, OrgError


def criteria_lines(value: object, what: str, *, required: bool) -> list[str]:
    """A list of criteria from a list or a newline-separated string: stripped, without a leading "- "."""
    if value is None:
        items: list[object] = []
    elif isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise OrgError(f"{what} must be a list of strings (or one newline-separated string)")
    out: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise OrgError(f"{what} must contain only strings (got {item!r})")
        for line in item.splitlines():
            line = line.strip()
            if line.startswith(("- ", "* ")):
                line = line[2:].strip()
            if line and line not in ("-", "*"):
                out.append(line)
    if required and not out:
        raise OrgError(
            f"{what} needs at least one non-empty criterion: concrete, checkable conditions the delivery must meet"
        )
    return out


SOURCE_KEYS = ("from", "asked", "default", "from_tasks")
ASKED_MAX = 300
ELICITATION_MAX = 4000
FROM_TASKS_MAX = 20
SOURCES_SHAPE = (
    "refused: sources has one entry for each criterion of acceptance ({count}), in order: {{from: <the user's words>, asked: <the question>}}, "
    "{{default: true}}, {{from_tasks: [<case heads>]}} or {{}}. Not understood: {why}. Nothing was written."
)
ELICITATION_SHAPE = "refused: elicitation is the user's answers, verbatim: a text of 1 to {max} characters. Nothing was written."


def source_entries(value: object, count: int) -> list[JsonObject]:
    """The ``sources`` of a first definition (design 10.1 step 5), one entry for each of its ``count`` criteria: ``{from, asked}``, ``{default: true}``,
    ``{from_tasks: [...]}`` or ``{}``, as stored in SERVICE.md; a ``OrgError`` for anything else."""

    def refuse(why: str) -> OrgError:
        return OrgError(SOURCES_SHAPE.format(count=count, why=why))

    if not isinstance(value, (list, tuple)) or len(value) != count:
        raise refuse(f"{len(value) if isinstance(value, (list, tuple)) else 'not a list'} entries")
    out: list[JsonObject] = []
    for number, entry in enumerate(value, 1):
        if not isinstance(entry, dict) or any(key not in SOURCE_KEYS for key in entry):
            raise refuse(f"entry {number} is not a mapping of from, asked, default and from_tasks")
        given = [key for key in ("from", "default", "from_tasks") if key in entry]
        quote, asked, tasks = entry.get("from"), entry.get("asked", ""), entry.get("from_tasks")
        if len(given) > 1 or ("asked" in entry and "from" not in entry):
            raise refuse(f"entry {number} has more than one source, or asked without from")
        if "from" in entry and (not isinstance(quote, str) or not quote.strip()):
            raise refuse(f"entry {number}: from is the user's words")
        if "default" in entry and entry["default"] is not True:
            raise refuse(f"entry {number}: default is true")
        if "from_tasks" in entry and (not isinstance(tasks, list) or not 1 <= len(tasks) <= FROM_TASKS_MAX or not all(isinstance(x, str) and x.strip() for x in tasks)):
            raise refuse(f"entry {number}: from_tasks is a list of 1 to {FROM_TASKS_MAX} case heads")
        if not isinstance(asked, str) or len(asked.strip()) > ASKED_MAX:
            raise refuse(f"entry {number}: asked is a question of at most {ASKED_MAX} characters")
        stored: JsonObject = {}
        if isinstance(quote, str):
            stored["from"] = quote.strip()
            if asked.strip():
                stored["asked"] = asked.strip()
        elif "default" in entry:
            stored["default"] = True
        elif isinstance(tasks, list):
            stored["from_tasks"] = [str(x).strip() for x in tasks]
        out.append(stored)
    return out


def elicitation_text(value: object) -> str:
    """The user's recorded words (design 10.1 step 5): a text of 1 to 4000 characters, stripped; an ``OrgError`` for anything else."""
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= ELICITATION_MAX:
        raise OrgError(ELICITATION_SHAPE.format(max=ELICITATION_MAX))
    return value.strip()
