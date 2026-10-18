"""Services and reflection: a standing task an agent offers, and the loop that improves how it is done.

A *service* is a standing offer by one agent (the owner, usually a team lead) to do one kind of task on request:

* the **contract** ``<owner>/services/<name>/SERVICE.md`` is written by the client (the owner's parent) with
  :func:`define_service`: what may be asked, the acceptance criteria, the budget of a request;
* the **playbook** ``PLAYBOOK.md`` (how the team does it) is written by the owner with :func:`revise_playbook`, and
  versioned by the runtime. The owner cannot change the contract, so improving the playbook can never lower the bar;
* a **request** is a task built from the contract (:func:`request`), so every rule of tasks applies unchanged;
* **cases** (the history of requests), their **stats** and the **reflection digest** are never stored: they are
  derived from the message files and run logs, like all state in orgmcp.

Every function takes the :class:`~orgmcp.core.Org` first and the acting agent second. ``Org`` has thin wrappers with
the same names (without the ``org`` argument) for define_service, retire_service, request, revise_playbook and
feedback. All raise :class:`~orgmcp.core.OrgError` with a message written for an LLM.

Files::

    <owner>/services/<name>/SERVICE.md, PLAYBOOK.md, history/SERVICE.v<n>.md, history/PLAYBOOK.v<n>.md
    <owner>/services/.retired/<name>-<timestamp>/   (retired services)
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .core import (
    RENDER_BODY_CHARS, ROOT, Message, Org, OrgError, NAME_RE, atomic_write, join_frontmatter, latest_results,
    split_frontmatter, utcnow,
)
from .health import _msg_time, _parse_time

INPUT_RE = re.compile(r"[a-z][a-z0-9_]{0,31}\Z")
VERDICTS = ("accept", "reject")
DESCRIPTION_MAX = 300
REASON_MAX = 400
FEEDBACK_MAX = 1000
TITLE_MAX = 80
DELIVERABLE_KEYS = ("description", "format", "max_words", "path")
DIGEST_CASES = 6  # cases with new evidence shown in the digest
DIGEST_CHARS = 3000  # soft limit of the whole digest
FEEDBACK_HEADER = (
    "Client feedback for reflection only: it does not change this task's acceptance criteria or outcome; "
    "report `done` only if every criterion is met."
)
CLIP_LESSON = 220
CLIP_NOTE = 160
MAX_VERDICTS = 4  # verdicts of one case shown in a digest line


# ------------------------------------------------------------------------------------------------ files


@dataclass
class Contract:
    """A parsed ``SERVICE.md``."""

    name: str
    owner: str
    description: str = ""
    inputs: list[dict] = field(default_factory=list)  # {"name", "description", "required"}
    acceptance: list[str] = field(default_factory=list)
    deliverable: dict = field(default_factory=dict)
    budget: int = 1
    locked: bool = False
    version: int = 1
    defined_by: str = ""
    defined: datetime | None = None
    created: datetime | None = None  # when the service was first defined (requests before it belong to an older service)
    notes: str = ""  # free text body: notes from the client
    path: Path | None = None


@dataclass
class Playbook:
    """A parsed ``PLAYBOOK.md``; ``version`` 0 = there is none."""

    version: int = 0
    revised: datetime | None = None
    by: str = ""
    reason: str = ""
    body: str = ""
    path: Path | None = None


def service_dir(org: Org, owner: str, name: str) -> Path:
    return org.dir(owner) / "services" / name


def _rel(org: Org, path: Path) -> str:
    return str(path.relative_to(org.root))


def _int(value, default: int = 0) -> int:
    try:
        return default if value is None or isinstance(value, bool) else int(value)
    except (TypeError, ValueError):
        return default


def _when(value) -> datetime | None:
    return _parse_time(value) if value else None


def read_contract(org: Org, owner: str, name: str) -> Contract | None:
    """The contract of ``owner``'s service ``name``; None when there is no such (non-retired) service."""
    path = service_dir(org, owner, name) / "SERVICE.md"
    if not path.is_file():
        return None
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    inputs = [
        {"name": str(i.get("name", "")), "description": str(i.get("description") or ""),
         "required": i.get("required", True) is not False}
        for i in (meta.get("inputs") or []) if isinstance(i, dict) and i.get("name")
    ]
    accept = [str(a) for a in (meta.get("acceptance") or [])]
    deliverable = meta.get("deliverable")
    return Contract(
        name=name, owner=owner, description=str(meta.get("description") or ""), inputs=inputs, acceptance=accept,
        deliverable=dict(deliverable) if isinstance(deliverable, dict) else {},
        budget=max(1, _int(meta.get("budget"), 1)), locked=meta.get("locked") is True,
        version=max(1, _int(meta.get("version"), 1)), defined_by=str(meta.get("defined_by") or ""),
        defined=_when(meta.get("defined")), created=_when(meta.get("created") or meta.get("defined")),
        notes=body.strip(), path=path,
    )


def read_playbook(org: Org, owner: str, name: str) -> Playbook:
    """The current playbook of a service (version 0 when it has none yet)."""
    path = service_dir(org, owner, name) / "PLAYBOOK.md"
    if not path.is_file():
        return Playbook()
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    return Playbook(
        version=_int(meta.get("version")), revised=_when(meta.get("revised")),
        by=str(meta.get("by") or ""), reason=str(meta.get("reason") or ""), body=body.strip(), path=path,
    )


def owned_services(org: Org, owner: str) -> list[Contract]:
    """The services ``owner`` offers (not the retired ones), by name."""
    return [c for n in org.service_names(owner) if (c := read_contract(org, owner, n)) is not None]


def requestable_services(org: Org, actor: str) -> list[Contract]:
    """The services ``actor`` can request: those of its direct reports (root: of its top-level agents)."""
    return [c for kid in org.children(actor) for c in owned_services(org, kid)]


def _owner_addr(org: Org, actor: str, owner: str) -> str:
    """``owner`` as a full address; a manager may give the short name of a direct report."""
    short = org.norm(owner)
    if "/" in short or org.norm(actor) == ROOT or org.exists(short):
        return short
    return org.child_addr(actor, short)


def _word_cap(org: Org) -> int:
    try:
        cap = int(org.config["playbook_max_words"])
    except (TypeError, ValueError):
        return 1000
    return cap if cap > 0 else 1000


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _stamp_now() -> str:
    return utcnow().isoformat(timespec="microseconds")


# ------------------------------------------------------------------------------------- validation helpers


def _lines(value, what: str, *, required: bool) -> list[str]:
    """A list of criteria from a list or a newline-separated string: stripped, without a leading "- "."""
    if value is None:
        items: list = []
    elif isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise OrgError(f"{what} must be a list of strings (or one newline-separated string)")
    out = []
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


def parse_input_spec(spec: str) -> dict:
    """``'topic*:what it is about'`` -> ``{"name": "topic", "description": "what it is about", "required": True}``.

    A trailing ``*`` on the name marks it required; without it the input is optional. Used by the CLI.
    """
    name, _, desc = spec.partition(":")
    name = name.strip()
    required = name.endswith("*")
    return {"name": name.rstrip("*").strip(), "description": desc.strip(), "required": required}


def _inputs(value) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise OrgError("inputs must be a list of {name, description, required} (or may be empty)")
    out, seen = [], set()
    for raw in value:
        item = parse_input_spec(raw) if isinstance(raw, str) else raw
        if not isinstance(item, dict):
            raise OrgError(f"each input must be {{name, description, required}} (got {raw!r})")
        extra = set(item) - {"name", "description", "required"}
        if extra:
            raise OrgError(f"unknown key(s) in input {item.get('name')!r}: {', '.join(sorted(extra))}. Use name, description, required")
        name = str(item.get("name") or "")
        if not INPUT_RE.fullmatch(name):
            raise OrgError(f"input name must be lowercase letters, digits and underscores, starting with a letter (max 32): {name!r}")
        if name in seen:
            raise OrgError(f"input name used twice: {name}")
        seen.add(name)
        required = item.get("required", True)
        if not isinstance(required, bool):
            raise OrgError(f"input {name}: required must be true or false")
        out.append({"name": name, "description": str(item.get("description") or "").strip(), "required": required})
    return out


def _deliverable(value) -> dict:
    if not isinstance(value, dict):
        raise OrgError("deliverable must be {description, format?, max_words?, path?}")
    extra = set(value) - set(DELIVERABLE_KEYS)
    if extra:
        raise OrgError(f"unknown key(s) in deliverable: {', '.join(sorted(extra))}. Use {', '.join(DELIVERABLE_KEYS)}")
    desc = str(value.get("description") or "").strip()
    if not desc:
        raise OrgError("deliverable needs a description: what the owner hands back (e.g. one markdown file)")
    out: dict = {"description": desc}
    if value.get("format"):
        out["format"] = str(value["format"]).strip()
    if value.get("max_words") not in (None, ""):
        mw = value["max_words"]
        if isinstance(mw, bool) or not isinstance(mw, int) or mw < 1:
            raise OrgError("deliverable.max_words must be a whole number of at least 1")
        out["max_words"] = mw
    if value.get("path"):
        path = str(value["path"]).strip()
        if not Path(path).expanduser().is_absolute():
            raise OrgError(f"deliverable.path must be an absolute path (got {path!r})")
        out["path"] = path
    return out


def _playbook_text(org: Org, content: str) -> str:
    """The playbook body: frontmatter (if the caller wrote one) stripped, non-empty, within the word cap."""
    text = (content or "").replace("\r\n", "\n")
    body = (split_frontmatter(text)[1] if text.startswith("---\n") else text).strip()
    if not body:
        raise OrgError("the playbook is empty: write the workflow (steps: who does what, in which order, which check)")
    cap, words = _word_cap(org), len(body.split())
    if words > cap:
        raise OrgError(
            f"the playbook is {words} words; the limit is {cap} (playbook_max_words). Condense it to the steps that "
            "matter and move detail into a file under your work/ directory."
        )
    return body


def _check_actor_owns(org: Org, actor: str, name: str) -> Contract:
    """The contract of ``name`` among the services ``actor`` owns, or an error listing the ones it owns."""
    contract = read_contract(org, actor, name) if NAME_RE.fullmatch(name or "") else None
    if contract is None:
        mine = ", ".join(org.service_names(actor)) or "none"
        raise OrgError(
            f"you do not own a service called `{name}`. Services you own: {mine}. Only the owner revises a "
            "playbook, and services are defined for you by your parent (define_service)."
        )
    return contract


# ------------------------------------------------------------------------------------------ define / retire


def define_service(
    org: Org, actor: str, owner: str, name: str, *, description: str | None = None, inputs=None, acceptance=None,
    deliverable: dict | None = None, budget: int | None = None, playbook: str | None = None, locked: bool | None = None,
    notes: str | None = None, add_acceptance=None, remove_acceptance=None,
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
    actor = org.require(actor)
    owner = _owner_addr(org, actor, owner)
    if owner == ROOT or not org.exists(owner):
        raise OrgError(f"no such agent: {owner}. A service is offered by one of your direct reports (root: a top-level agent).")
    client = org.parent(owner)
    if actor != client:
        raise OrgError(
            f"only {client}, the parent of {owner}, can define its services (you are {actor}): the contract belongs "
            f"to the client. Ask {client}, or define services for your own direct reports."
        )
    if not NAME_RE.fullmatch(name or ""):
        raise OrgError("a service name is lowercase letters, digits and dashes, starting with a letter (max 32), e.g. weekly-brief")
    for sibling in org.children(client):
        if sibling != owner and name in org.service_names(sibling):
            raise OrgError(
                f"a service called `{name}` already exists at {sibling}. Requests name the service only, so names "
                f"must be unique among the agents that report to {client}: pick another name."
            )
    old = read_contract(org, owner, name)
    if old is not None and playbook is not None:
        raise OrgError(
            f"the playbook belongs to {owner}, which revises it with revise_playbook: do not pass `playbook` when "
            "you redefine the contract. Leave it out; the existing playbook stays."
        )
    if acceptance is not None and (add_acceptance is not None or remove_acceptance is not None):
        raise OrgError(
            "`acceptance` replaces all criteria; do not combine it with add_acceptance / remove_acceptance. Use "
            "add_acceptance / remove_acceptance alone to change single criteria."
        )
    if old is None:
        if add_acceptance is not None or remove_acceptance is not None:
            raise OrgError(
                f"service `{name}` does not exist yet: add_acceptance / remove_acceptance amend an existing contract. "
                "Give the full `acceptance` list for a first definition."
            )
        missing = [k for k, v in (("description", description), ("acceptance", acceptance), ("deliverable", deliverable),
                                  ("budget", budget)) if v is None]
        if missing:
            raise OrgError(f"a first definition of `{name}` needs {', '.join(missing)} (it does not exist yet, so there is nothing to keep)")

    if description is not None:
        description = description.strip() if isinstance(description, str) else ""
        if not description or len(description) > DESCRIPTION_MAX or "\n" in description:
            raise OrgError(f"description is one line of at most {DESCRIPTION_MAX} characters saying what the service delivers")
    if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int) or budget < 1):
        raise OrgError("budget is the number of runs handed down with each request: a whole number, at least 1")
    if locked is not None and not isinstance(locked, bool):
        raise OrgError("locked must be true or false")
    inputs_n = _inputs(inputs) if inputs is not None or old is None else old.inputs
    deliverable_n = _deliverable(deliverable) if deliverable is not None else (old.deliverable if old else {})
    if acceptance is not None:
        accept_n = _lines(acceptance, "acceptance", required=True)
    elif old is None:
        accept_n = []
    else:
        accept_n = _amended_criteria(name, old.acceptance, add_acceptance, remove_acceptance)
    playbook_body = _playbook_text(org, playbook) if playbook is not None else None

    sdir = service_dir(org, owner, name)
    now = _stamp_now()
    notes_n = (notes if notes is not None else (old.notes if old else "") or "").strip()
    meta = {
        "name": name, "description": description if description is not None else (old.description if old else ""),
        "inputs": inputs_n, "acceptance": accept_n, "deliverable": deliverable_n,
        "budget": budget if budget is not None else (old.budget if old else 1),
        "locked": locked if locked is not None else (old.locked if old else False),
        "version": 1 if old is None else old.version + 1, "defined_by": actor, "defined": now,
        "created": now if old is None or old.created is None else old.created.isoformat(timespec="microseconds"),
    }
    where = _rel(org, sdir / "SERVICE.md")
    if old is not None:
        changes = _contract_changes(old, meta, notes_n)
        if not changes:
            raise OrgError(
                f"no change: the amendment leaves the contract of `{name}` exactly as it is (v{old.version}). "
                f"Current criteria:\n{_numbered(old.acceptance)}"
            )
        atomic_write(sdir / "history" / f"SERVICE.v{old.version}.md", (sdir / "SERVICE.md").read_text(encoding="utf-8"))
    atomic_write(sdir / "SERVICE.md", join_frontmatter(meta, notes_n))
    if old is None:
        text = f"defined service `{name}` (contract v1) for {owner}: {where}"
        if playbook_body is not None:
            _write_playbook(org, owner, name, 1, playbook_body, actor, "initial playbook")
            text += f"; playbook v1: {_rel(org, sdir / 'PLAYBOOK.md')}"
        else:
            text += f". It has no playbook yet: {owner} writes v1 with revise_playbook after its first request."
        return text
    org.notify(
        owner, f"contract of service {name} changed to v{meta['version']}",
        _contract_diff(old, meta, changes, where), wake=False,
    )
    return (
        f"redefined service `{name}` of {owner}: contract v{old.version} -> v{meta['version']} ({where}); the old one "
        f"is kept at {_rel(org, sdir / 'history' / f'SERVICE.v{old.version}.md')}. {owner} was told (without waking it).\n"
        "Changed:\n" + "\n".join(changes) + f"\nAcceptance criteria now ({len(accept_n)}):\n{_numbered(accept_n)}"
    )


def _numbered(items: list[str], indent: str = "") -> str:
    return "\n".join(f"{indent}{i}. {x}" for i, x in enumerate(items, 1))


def _amended_criteria(name: str, current: list[str], add, remove) -> list[str]:
    """``current`` without the ``remove`` criteria (exact text) and with the ``add`` ones appended; errors say why."""
    if add is None and remove is None:
        return list(current)
    add_n, remove_n = _lines(add, "add_acceptance", required=False), _lines(remove, "remove_acceptance", required=False)
    listing = f"Current criteria of `{name}`:\n{_numbered(current)}"
    unknown = [x for x in remove_n if x not in current]
    if unknown:
        raise OrgError(
            "remove_acceptance must be the exact text of existing criteria; not found: "
            + "; ".join(f'"{x}"' for x in unknown) + f".\n{listing}"
        )
    dup = [x for x in add_n if x in current]
    if dup:
        raise OrgError(
            "add_acceptance: already a criterion: " + "; ".join(f'"{x}"' for x in dup)
            + f". Add only new criteria (to reword one, remove it and add the new text in two calls).\n{listing}"
        )
    twice = sorted({x for x in add_n if add_n.count(x) > 1})
    if twice:
        raise OrgError("add_acceptance lists the same criterion twice: " + "; ".join(f'"{x}"' for x in twice))
    result = [x for x in current if x not in remove_n] + add_n
    if not result:
        raise OrgError(f"that would leave `{name}` without acceptance criteria: a service needs at least one.\n{listing}")
    return result


def _fmt_deliverable(d: dict) -> str:
    extra = [f"{k}: {d[k]}" for k in ("format", "max_words", "path") if d.get(k)]
    return f'"{d.get("description", "")}"' + (f" ({'; '.join(extra)})" if extra else "")


def _contract_changes(old: Contract, new: dict, notes: str) -> list[str]:
    """What differs between the old contract and the new one, one line each (criteria verbatim, others old -> new)."""
    out: list[str] = []

    def listing(label: str, before: list[str], after: list[str]) -> None:
        out.extend(f"- {label} removed: {x}" for x in before if x not in after)
        out.extend(f"+ {label} added: {x}" for x in after if x not in before)

    listing("acceptance", old.acceptance, new["acceptance"])
    fmt = lambda items: [f"{i['name']}{'*' if i['required'] else ''}: {i['description']}" for i in items]  # noqa: E731
    listing("input", fmt(old.inputs), fmt(new["inputs"]))
    if old.budget != new["budget"]:
        out.append(f"budget per request: {old.budget} -> {new['budget']} runs")
    if old.locked != new["locked"]:
        out.append(f"locked: {str(old.locked).lower()} -> {str(new['locked']).lower()}"
                   + (" (you may no longer revise the playbook)" if new["locked"] else ""))
    if old.description != new["description"]:
        out.append(f'description: "{old.description}" -> "{new["description"]}"')
    if old.deliverable != new["deliverable"]:
        out.append(f"deliverable: {_fmt_deliverable(old.deliverable)} -> {_fmt_deliverable(new['deliverable'])}")
    if old.notes != notes:
        out.append(f'notes: "{old.notes}" -> "{notes}"')
    if not out and old.acceptance != new["acceptance"]:
        out.append("acceptance: order changed")
    return out


def _contract_diff(old: Contract, new: dict, changes: list[str], where: str) -> str:
    """The note to the owner: who changed the contract, exactly what, and where to read it."""
    head = (f"{old.defined_by or 'your parent'} changed the contract of service `{old.name}` (v{old.version} -> v{new['version']}). "
            "Read it, and follow the new criteria from the next request on:")
    return "\n".join([head, *changes, f"Contract: {where}"])


def retire_service(org: Org, actor: str, owner: str, name: str, reason: str) -> str:
    """Take a service out of use: it moves to ``<owner>/services/.retired/<name>-<timestamp>/``. Returns a confirmation.

    Same authority as :func:`define_service` (the owner's parent). Afterwards the service is not listed and cannot be
    requested; its past cases no longer count for a service of the same name defined later. The owner is told in a
    non-waking note.
    """
    actor = org.require(actor)
    owner = _owner_addr(org, actor, owner)
    if owner == ROOT or not org.exists(owner) or org.parent(owner) != actor:
        raise OrgError(f"you can only retire services of your direct reports (root: top-level agents); {owner!r} is not one")
    if read_contract(org, owner, name) is None:
        known = ", ".join(org.service_names(owner)) or "none"
        raise OrgError(f"{owner} offers no service called `{name}`. Its services: {known}")
    if not (reason or "").strip():
        raise OrgError("say why the service is retired (reason)")
    dest = service_dir(org, owner, ".retired") / f"{name}-{utcnow():%Y%m%dT%H%M%S%f}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(service_dir(org, owner, name)), dest)
    org.notify(
        owner, f"service {name} retired",
        f"{actor} retired the service `{name}`: {reason.strip()}. It cannot be requested any more; its files are kept at "
        f"{_rel(org, dest)}.", wake=False,
    )
    return f"retired service `{name}` of {owner}; files kept at {_rel(org, dest)}"


# ------------------------------------------------------------------------------------------------ playbook


def _write_playbook(org: Org, owner: str, name: str, version: int, body: str, by: str, reason: str) -> Path:
    path = service_dir(org, owner, name) / "PLAYBOOK.md"
    meta = {"service": name, "version": version, "revised": _stamp_now(), "by": by, "reason": reason}
    atomic_write(path, join_frontmatter(meta, body))
    return path


def revise_playbook(org: Org, actor: str, service: str, content: str, reason: str) -> int:
    """Write the next version of the playbook of a service ``actor`` owns; returns the new version.

    Refused when the contract is locked, when ``content`` is empty, over ``playbook_max_words`` or identical to the
    current playbook. A frontmatter in ``content`` is stripped (the runtime writes it). The old version is archived to
    ``history/PLAYBOOK.v<n>.md`` and the client gets a quiet (non-waking) note with the reason.
    """
    actor = org.require(actor)
    contract = _check_actor_owns(org, actor, service)
    client = org.parent(actor) or ROOT
    if contract.locked:
        raise OrgError(
            f"the contract of `{service}` is locked by {client}: you may not revise its playbook. Follow the current "
            f"one, and if you think it must change, tell {client} (`send`)."
        )
    reason = (reason or "").strip()
    if not reason or len(reason) > REASON_MAX:
        raise OrgError(
            f"reason is 1-{REASON_MAX} characters: say what changed and which cases it rests on (case ids from the "
            "evidence), so the next revision can judge it"
        )
    body = _playbook_text(org, content)
    current = read_playbook(org, actor, service)
    if current.version and body == current.body.strip():
        raise OrgError(
            f"no change: this is identical to playbook v{current.version}. Revise only when the evidence calls for a "
            "different way of working."
        )
    sdir = service_dir(org, actor, service)
    if current.version:
        atomic_write(sdir / "history" / f"PLAYBOOK.v{current.version}.md", (sdir / "PLAYBOOK.md").read_text(encoding="utf-8"))
    version = current.version + 1
    path = _write_playbook(org, actor, service, version, body, actor, reason)
    org.notify(
        client, f"playbook of {service} revised to v{version}",
        f"{actor} revised the playbook of service `{service}` to v{version}.\nReason: {reason}\nFile: {_rel(org, path)}",
        wake=False,
    )
    return version


def report_hint(org: Org, actor: str, task: Message, status: str) -> str:
    """What the `report` tool adds to its reply for a final result on a service request (empty otherwise)."""
    if not task.service or status not in ("done", "failed"):
        return ""
    contract = read_contract(org, actor, task.service)
    if contract is None or contract.locked:
        return ""
    if read_playbook(org, actor, task.service).version == 0:
        return (
            "This service has no playbook yet: write v1 now with revise_playbook - the steps your team followed and "
            "what you would change."
        )
    return (
        "Lessons recorded. If they call for a playbook change now, use revise_playbook; otherwise they are reviewed "
        "before the next request."
    )


# ------------------------------------------------------------------------------------------------ requests


def request(
    org: Org, actor: str, service: str, inputs: dict | None, *, title: str = "", note: str = "",
    extra_acceptance: list[str] | None = None, budget: int | None = None, revises: str | None = None,
) -> Message:
    """Ask one of ``actor``'s direct reports for its service ``service``: a task built from the contract.

    The task goes through ``Org.send`` like a delegation (same route, hops and budget rules, the reserve included).
    ``budget`` defaults to the contract's. ``extra_acceptance`` adds criteria after the contract's, which always
    travel unchanged. ``revises``: the id of an earlier request of this service to the same owner, to send it back.
    The task carries ``service``, ``contract`` and ``playbook`` (versions at this moment) in its frontmatter.
    """
    actor = org.require(actor)
    available = requestable_services(org, actor)
    contract = next((c for c in available if c.name == service), None)
    if contract is None:
        listing = ", ".join(f"{c.name} (offered by {c.owner})" for c in available) or "none"
        raise OrgError(
            f"no service `{service}` among your direct reports. Services you can request: {listing}. "
            "A parent defines one with define_service."
        )
    given = {str(k).strip(): ("" if v is None else str(v).strip()) for k, v in (inputs or {}).items()}
    known = {i["name"]: i for i in contract.inputs}
    unknown = [k for k in given if k not in known]
    if unknown:
        raise OrgError(
            f"unknown input(s) for `{service}`: {', '.join(unknown)}. Its inputs: {', '.join(known) or 'none'}."
        )
    missing = [n for n, i in known.items() if i["required"] and not given.get(n)]
    if missing:
        raise OrgError(f"missing required input(s) for `{service}`: {', '.join(missing)}. Pass them in `inputs`.")
    given = {k: v for k, v in given.items() if v}
    if budget is None:
        budget = contract.budget
    if isinstance(budget, bool) or int(budget) < 1:
        raise OrgError("a request needs a budget of at least 1 run")
    if revises and not any(
        m.id == revises and m.type == "task" and m.to == contract.owner and m.service == service for m in org.sent(actor)
    ):
        raise OrgError(
            f"revises must be the id of an earlier request for `{service}` that you sent to {contract.owner}: {revises}"
        )
    extra = _lines(extra_acceptance, "extra_acceptance", required=False)
    body = _request_body(contract, given, extra, note)
    if not title.strip():
        first = next((given[n] for n, i in known.items() if i["required"] and n in given), "")
        title = _clip(f"{service}: {first}" if first else service, TITLE_MAX)
    return org.send(
        actor, contract.owner, body, type="task", title=title.strip(), budget=int(budget), revises=revises or None,
        service=service, contract=contract.version, playbook=read_playbook(org, contract.owner, service).version,
    )


def _request_body(contract: Contract, given: dict[str, str], extra: list[str], note: str) -> str:
    d = contract.deliverable
    facts = [f"format: {d['format']}"] if d.get("format") else []
    facts += [f"at most {d['max_words']} words"] if d.get("max_words") else []
    facts += [f"path: {d['path']}"] if d.get("path") else []
    parts = [
        f"## Goal\nDeliver the service `{contract.name}`: {contract.description}",
        "## Request\n" + ("\n".join(f"- {k}: {given[k]}".replace("\n", "\n  ") for k in (i["name"] for i in contract.inputs) if k in given) or "(no inputs)"),
        "## Acceptance criteria\n" + "\n".join(f"- {c}" for c in [*contract.acceptance, *extra]),
        "## Deliverable\n" + d.get("description", "") + (f" ({'; '.join(facts)})" if facts else ""),
    ]
    if note.strip():
        parts.append(f"## Note from the requester\n{note.strip()}")
    return "\n\n".join(parts)


def rework_fields(org: Org, actor: str, revises: str) -> dict:
    """The service fields a rework task inherits from the task it revises (empty for an ordinary task).

    ``service`` and ``contract`` are copied from the revised task; ``playbook`` is the version current now.
    """
    task = next((m for m in org.sent(actor) if m.id == revises and m.type == "task"), None)
    if task is None or not task.service:
        return {}
    version = read_playbook(org, task.to, task.service).version if org.exists(task.to) else 0
    return {"service": task.service, "contract": task.contract, "playbook": version}


def feedback_text(msg: Message) -> str:
    """The client's own words in a feedback note ("" for a bare accept); the fixed header is not part of them."""
    body = msg.body.removeprefix(FEEDBACK_HEADER).strip()
    return "" if body == "accepted" else body


def feedback(org: Org, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
    """The client's verdict on a delivered service request: a quiet note to the owner (it costs no run).

    ``task_id``: any task of the case (the request or a rework) that ``actor`` sent and that has a result. ``verdict``
    is ``accept`` or ``reject``; a rejection needs a ``note`` saying what was wrong. The owner sees it with its next
    batch and in the reflection digest. Every verdict stays in the case's history: the latest one is the final
    verdict of the statistics, and an earlier ``reject`` is still shown (and counted as "after a reject").
    """
    actor = org.require(actor)
    task = next((m for m in org.sent(actor) if m.id == task_id and m.type == "task"), None)
    if task is None or not task.service:
        mine = ", ".join(m.id for m in org.sent(actor) if m.type == "task" and m.service) or "none"
        raise OrgError(
            f"{task_id} is not a service request you sent. Feedback is for requests made with `request`. Yours: {mine}"
        )
    if verdict not in VERDICTS:
        raise OrgError(f"verdict must be one of {VERDICTS}")
    note = (note or "").strip()
    if verdict == "reject" and not note:
        raise OrgError("a rejection needs a note: say what was wrong, so the owner can change its playbook")
    if len(note) > FEEDBACK_MAX:
        raise OrgError(f"the note is {len(note)} characters; the limit is {FEEDBACK_MAX}. Keep it to what was wrong or good.")
    if task.id not in latest_results(org.received(actor)):
        raise OrgError(f"task {task_id} has no result yet: wait for the result, then give feedback.")
    body = FEEDBACK_HEADER + "\n\n" + (note or "accepted")
    return org.send(
        actor, task.to, body, type="note", title=f'feedback on "{task.title}": {verdict}',
        reply_to=task.id, feedback=verdict, wake=False,
    )


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
        times = [t for t in (self.finished, _msg_time(self.feedback) if self.feedback else None) if t]
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


def playbook_timeline(org: Org, owner: str, service: str) -> list[tuple[int, datetime]]:
    """(version, when it was written) of every playbook version the service has had, oldest first."""
    sdir = service_dir(org, owner, service)
    paths = [*sorted((sdir / "history").glob("PLAYBOOK.v*.md")), sdir / "PLAYBOOK.md"]
    out = []
    for p in paths:
        if p.is_file():
            meta = split_frontmatter(p.read_text(encoding="utf-8"))[0]
            when = _when(meta.get("revised"))
            if when is not None and _int(meta.get("version")) > 0:
                out.append((_int(meta.get("version")), when))
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


def _count_runs(org: Org, team: list[str], start: str, end: str | None) -> int:
    used = 0
    for a in team:
        d = org.dir(a) / "runs"
        for name in os.listdir(d) if d.is_dir() else []:
            if name.endswith(".log") and not name.startswith(".") and name[:21] >= start and (end is None or name[:21] <= end):
                used += 1
    return used


def cases(org: Org, owner: str, service: str) -> list[Case]:
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
         and (since is None or (_msg_time(m) or since) >= since)),
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
        end = res.id[:21] if final else None
        later = next((i for i in others if i > last.id and i not in ids), None)
        if later and (end is None or later[:21] < end):
            end = later[:21]
        step = {t.id: i for i, t in enumerate(tasks)}
        verdicts = [
            Verdict(n.feedback or "", feedback_text(n), _msg_time(n), n.reply_to or "", step[n.reply_to], n)
            for n in notes if n.reply_to in ids
        ]
        out.append(Case(
            id=first, service=service, owner=owner, tasks=tasks, result=res, state=state,
            playbook=tasks[0].playbook or 0,
            used=version_at(timeline, _msg_time(first_result) if (first_result := results.get(tasks[0].id)) else None),
            reworks=len(tasks) - 1, budget=sum(t.budget for t in tasks),
            runs=_count_runs(org, team, tasks[0].id[:21], end),
            lessons=[x for t in tasks if (r := results.get(t.id)) is not None and (x := lessons_of(r))],
            lesson_ids=[r.id for t in tasks if (r := results.get(t.id)) is not None and lessons_of(r)],
            verdicts=verdicts, started=_msg_time(tasks[0]),
            finished=_msg_time(res) if final else None,
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


def reflection_digest(org: Org, owner: str, service: str) -> str | None:
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
    fresh.sort(key=lambda c: c.evidence_at)
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
    parts = [f"{v.verdict}" + (f' "{_clip(v.note, clip)}"' if v.note else "") for v in shown]
    if len(c.verdicts) > len(shown):
        parts.insert(0, "…")
    return " -> ".join(parts)


def _case_line(c: Case) -> str:
    bits = [f'case {c.id} "{_clip(c.title, 40)}": {c.state}', f"playbook v{c.used}", f"{c.runs} of {c.budget} runs"]
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
        line += f'; lessons{mark}: "{_clip(latest, CLIP_LESSON)}"'
        room = CLIP_LESSON - len(latest)
        if earlier and room > 40:
            line += f'; earlier: "{_clip(earlier, room)}"'
    return "- " + line


def case_of(org: Org, task: Message) -> Case | None:
    """The case a service task belongs to (None for a task that is not a service request, or an unknown one)."""
    if not task.service or not org.exists(task.to):
        return None
    return next((c for c in cases(org, task.to, task.service) if task.id in {t.id for t in c.tasks}), None)


def case_total(org: Org, task: Message) -> str:
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


def _service_block(org: Org, c: Contract, *, offered: bool) -> list[str]:
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
        lines.append(f'  playbook v{pb.version} ({pb.revised:%Y-%m-%d}): "{_clip(pb.reason, 120)}"' if pb.revised else f"  playbook v{pb.version}")
    elif not offered:
        lines.append("  playbook: none yet")
    if offered:
        lines.append(f"  playbook file: {_rel(org, service_dir(org, c.owner, c.name) / 'PLAYBOOK.md')}"
                     + ("" if pb.version else " (not written yet)"))
    return [x for x in lines if x]


def services_text(org: Org, actor: str) -> str:
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


def _quoted(org: Org, text: str, where: str) -> str:
    """A playbook shown in the prompt: quoted, so its headings do not mix with the prompt's, cut like messages."""
    if len(text) > RENDER_BODY_CHARS:
        text = (
            text[:RENDER_BODY_CHARS].rstrip()
            + f"\n\n[... playbook cut: {len(text) - RENDER_BODY_CHARS} more characters. Read the rest with read(path=\"{where}\").]"
        )
    return "\n".join(f"> {line}".rstrip() for line in text.splitlines())


def prompt_sections(org: Org, addr: str, batch: list[Message]) -> str:
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


def _rejected_services(org: Org, addr: str, batch: list[Message]) -> set[str]:
    """The services of ``addr`` for which the batch holds a ``feedback: reject`` note (the client rejected a delivery)."""
    notes = [m for m in batch if m.type == "note" and m.feedback == "reject" and m.to == addr and m.reply_to]
    if not notes:
        return set()
    service_of = {m.id: m.service for m in org.received(addr) if m.type == "task" and m.service}
    return {svc for n in notes if (svc := service_of.get(n.reply_to or ""))}


def _playbook_section(org: Org, addr: str, c: Contract, *, reflecting: bool = False) -> str:
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


def _reflect_section(org: Org, addr: str, c: Contract, digest: str, *, rejected: bool = False, new_request: bool = True) -> str:
    pb = read_playbook(org, addr, c.name)
    cap = _word_cap(org)
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
