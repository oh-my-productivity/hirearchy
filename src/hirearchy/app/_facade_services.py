"""Standing services: thin wrappers over the ports of the runtime (services).

The bodies call the ports of ``self.runtime`` (step C-services; ARCHITECTURE.md 5.3 and 6.4): ``service_names`` is the catalog's, the five commands are
``ServiceCommands``'."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..kernel import Message
from .runtime import OrgRuntime


class ServicesMixin:
    """Standing services: thin wrappers over the ports of the runtime (services)."""

    runtime: OrgRuntime

    def service_names(self, addr: str) -> list[str]:
        """Names of the (non-retired) services ``addr`` offers: the directories of ``<addr>/services`` with a SERVICE.md."""
        return self.runtime.service_catalog.service_names(addr)

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs: object = None, acceptance: object = None,
        deliverable: Mapping[str, object] | None = None, budget: int | None = None, playbook: str | None = None,
        locked: bool | None = None, notes: str | None = None, add_acceptance: object = None, remove_acceptance: object = None,
        answers: str | None = None, about: str | None = None, words: str | None = None,
    ) -> str:
        """Define a service of a direct report, or amend it (omitted fields keep their value). See
        :meth:`hirearchy.services.ServiceCommands.define_service`."""
        return self.runtime.service_commands.define_service(
            actor, owner, name, description=description, inputs=inputs, acceptance=acceptance, deliverable=deliverable, budget=budget,
            playbook=playbook, locked=locked, notes=notes, add_acceptance=add_acceptance, remove_acceptance=remove_acceptance,
            answers=answers, about=about, words=words,
        )

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        """Take a service out of use (its files are kept). See :meth:`hirearchy.services.ServiceCommands.retire_service`."""
        return self.runtime.service_commands.retire_service(actor, owner, name, reason)

    def request(
        self, actor: str, service: str, inputs: Mapping[str, object] | None, *, title: str = "", note: str = "",
        extra_acceptance: Sequence[str] | None = None, budget: int | None = None, revises: str | None = None,
        source: str | None = None, base: str | None = None,
    ) -> Message:
        """Ask a direct report for one of its services. See :meth:`hirearchy.services.ServiceCommands.request`."""
        return self.runtime.service_commands.request(
            actor, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance, budget=budget, revises=revises, source=source,
            base=base,
        )

    def revise_playbook(self, actor: str, service: str, content: str, reason: str, evidence: Sequence[str]) -> int:
        """Write the next version of the playbook of a service you own; returns the version. ``evidence`` is required (``[]`` for the first
        version, or to restore one the client wrote). See :meth:`hirearchy.services.ServiceCommands.revise_playbook`."""
        return self.runtime.service_commands.revise_playbook(actor, service, content, reason, evidence)

    def feedback(
        self, actor: str, task_id: str, verdict: str, note: str = "", *, source: str | None = None, criterion: Sequence[str] | None = None,
        confirms: str | None = None,
    ) -> Message:
        """Tell the owner whether a delivered service request was accepted or rejected. See :meth:`hirearchy.services.ServiceCommands.feedback`."""
        return self.runtime.service_commands.feedback(actor, task_id, verdict, note, source=source, criterion=criterion, confirms=confirms)
