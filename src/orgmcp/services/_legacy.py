"""The old module-level names of ``orgmcp.services`` (every function takes the :class:`~orgmcp.core.Org` first and the acting agent second).

Exported by ``__init__`` until step E3 (``LEGACY_EXPORTS``). Thin adapters of the classes of the package (step C-services): contracts, playbooks,
requests, feedback and their hints call the ports of ``org.runtime``; they only keep the old spelling (the ``Org`` is duck-typed, because no feature may
import the facade). The names of the cases, statistics, digest, listing and prompt sections moved to ``reflection`` (step C-reflection); ``__init__``
answers to them too, until E3.

Standing services: the contract ``<owner>/services/<name>/SERVICE.md`` is written by the client (the owner's parent) with :func:`define_service`;
the playbook ``PLAYBOOK.md`` by the owner with :func:`revise_playbook`; a request is a task built from the contract (:func:`request`). All raise
:class:`~orgmcp.core.OrgError` with a message written for an LLM.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from ..kernel import TITLE_MAX, JsonObject, Message, clip_line
from ._hints import client_words
from ._host import ServicesOrg
from ._normalizer import TextContractNormalizer
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

__all__ = [
    "DELIVERABLE_KEYS", "DESCRIPTION_MAX", "FEEDBACK_HEADER", "FEEDBACK_MAX", "INPUT_RE", "REASON_MAX", "TITLE_MAX", "VERDICTS", "Contract",
    "Playbook", "define_service", "feedback", "feedback_text", "owned_services", "parse_input_spec", "read_contract", "read_playbook",
    "report_hint", "request", "requestable_services", "retire_service", "revise_playbook", "rework_fields", "service_dir",
]


# ----------------------------------------------------------------------------------- names kept for the callers that still reach for them

_clip = clip_line  # the private copy of ``kernel.clip_line`` that ``kernel/tests/test_text.py`` still compares with the others


# ----------------------------------------------------------------------------------- the adapters of the part that moved


def service_dir(org: ServicesOrg, owner: str, name: str) -> Path:
    return org.dir(owner) / "services" / name


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
