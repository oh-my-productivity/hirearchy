"""Runtime fields of ``dispatch`` (ARCHITECTURE.md 3.20): one field per port that ``wire_dispatch.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..dispatch import ArtifactNormalizer, GuardedSender, HopCounter, MessageSender, ReworkContext, RoutePolicy, TaskAssigner, TaskReporter

STEP: str | None = "B-dispatch"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    message_sender: MessageSender
    facade_sender: GuardedSender  # the sender behind ``Org.send``: the message sender, but root sends no service task or rework through it
    task_assigner: TaskAssigner
    task_reporter: TaskReporter
    rework_context: ReworkContext
    route_policy: RoutePolicy
    hop_counter: HopCounter
    artifact_normalizer: ArtifactNormalizer
