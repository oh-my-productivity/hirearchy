"""``OrgRuntime``: the objects of one organization, one field per port (ARCHITECTURE.md 6.2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..kernel import AtomicWriter, Clock, Environment, IdGenerator, LedgerStore, OrgLayout
from ..processes import OrphanJudge, ProcessInspector, ProcessSignaller, ProcessSpawner
from ._resources import ProcessResources


@dataclass(frozen=True)
class OrgRuntime:
    """Data only: the ports of one organization root, built by ``wiring.open_runtime``. A step that gives a package its
    interfaces adds the field(s) here and the providers in its ``wire_<pkg>.py``."""

    root: Path
    resources: ProcessResources
    paths: OrgLayout
    clock: Clock
    ids: IdGenerator
    atomic_writer: AtomicWriter
    ledgers: LedgerStore
    environment: Environment
    process_spawner: ProcessSpawner
    process_inspector: ProcessInspector
    process_signaller: ProcessSignaller
    orphan_judge: OrphanJudge
