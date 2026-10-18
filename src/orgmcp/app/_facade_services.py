"""Standing services: thin wrappers over orgmcp.services (services).

Moved verbatim from ``core.Org`` in step M2 (ARCHITECTURE.md 5.3 and 6.4); a later step replaces the bodies by calls
to the interfaces of the package named above."""

from __future__ import annotations

from ..kernel import Message, ROOT, visible as _visible


class ServicesMixin:
    """Standing services: thin wrappers over orgmcp.services (services)."""

    def service_names(self, addr: str) -> list[str]:
        """Names of the (non-retired) services ``addr`` offers: the directories of ``<addr>/services`` with a SERVICE.md."""
        a = self.norm(addr)
        d = self.dir(a) / "services"
        if a == ROOT or not d.is_dir():
            return []
        return [p.name for p in _visible(d.iterdir()) if p.is_dir() and (p / "SERVICE.md").is_file()]

    def define_service(
        self, actor: str, owner: str, name: str, *, description: str | None = None, inputs=None, acceptance=None,
        deliverable: dict | None = None, budget: int | None = None, playbook: str | None = None,
        locked: bool | None = None, notes: str | None = None, add_acceptance=None, remove_acceptance=None,
    ) -> str:
        """Define a service of a direct report, or amend it (omitted fields keep their value). See
        :func:`orgmcp.services.define_service`."""
        from .. import services

        return services.define_service(
            self, actor, owner, name, description=description, inputs=inputs, acceptance=acceptance,
            deliverable=deliverable, budget=budget, playbook=playbook, locked=locked, notes=notes,
            add_acceptance=add_acceptance, remove_acceptance=remove_acceptance,
        )

    def retire_service(self, actor: str, owner: str, name: str, reason: str) -> str:
        """Take a service out of use (its files are kept). See :func:`orgmcp.services.retire_service`."""
        from .. import services

        return services.retire_service(self, actor, owner, name, reason)

    def request(
        self, actor: str, service: str, inputs: dict | None, *, title: str = "", note: str = "",
        extra_acceptance: list[str] | None = None, budget: int | None = None, revises: str | None = None,
    ) -> Message:
        """Ask a direct report for one of its services. See :func:`orgmcp.services.request`."""
        from .. import services

        return services.request(
            self, actor, service, inputs, title=title, note=note, extra_acceptance=extra_acceptance,
            budget=budget, revises=revises,
        )

    def revise_playbook(self, actor: str, service: str, content: str, reason: str) -> int:
        """Write the next version of the playbook of a service you own; returns the version."""
        from .. import services

        return services.revise_playbook(self, actor, service, content, reason)

    def feedback(self, actor: str, task_id: str, verdict: str, note: str = "") -> Message:
        """Tell the owner whether a delivered service request was accepted or rejected."""
        from .. import services

        return services.feedback(self, actor, task_id, verdict, note)
