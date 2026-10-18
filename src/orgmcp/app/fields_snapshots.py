"""Runtime fields of ``snapshots`` (ARCHITECTURE.md 3.5): one field per port that ``wire_snapshots.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..snapshots import GitClient, IgnoreList, OrgSnapshotter

STEP: str | None = "A-snapshots"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    git: GitClient
    snapshotter: OrgSnapshotter
    ignore_list: IgnoreList
