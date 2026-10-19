"""Runtime fields of ``observability`` (ARCHITECTURE.md 3.31): none yet - the ports of the second half (``C-obs-2``) come with the rest.

``wire_observability`` provides ``EventQueries``, ``TraceQueries`` and ``MetricQueries`` to a builder already (``Builder.get``) and builds them over the
runtime in force for the functions of ``observe.py`` (``event_queries_of`` ...); they become fields when step C-obs-2 fills this part and sets ``STEP``
(``test_runtime_fields`` takes all of 3.31 as one step)."""

from __future__ import annotations

from dataclasses import dataclass

STEP: str | None = None  # set to the step's name when the step fills this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    """No field yet: the step that gives the package its runtime ports adds them here."""
