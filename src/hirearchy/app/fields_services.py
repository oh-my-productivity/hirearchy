"""Runtime fields of ``services`` (ARCHITECTURE.md 3.21): one field per port that ``wire_services.py`` builds.

``ReworkContext`` (the field ``rework_context`` of ``fields_dispatch``) is a port of ``dispatch`` that ``services`` implements: ``wire_services`` provides it.
``ServiceEvidence`` (the field ``service_evidence``) is a port of ``services`` that ``reflection`` implements, because ``services`` cannot read the cases:
``wire_reflection`` provides it."""

from __future__ import annotations

from dataclasses import dataclass

from ..services import ContractNormalizer, ServiceCatalog, ServiceCommands, ServiceEvidence, ServiceHints, ServiceStore

STEP: str | None = "C-services"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    service_store: ServiceStore
    service_catalog: ServiceCatalog
    service_commands: ServiceCommands
    service_hints: ServiceHints
    contract_normalizer: ContractNormalizer
    service_evidence: ServiceEvidence  # a port of ``services`` that ``reflection`` implements: ``wire_reflection`` provides it
