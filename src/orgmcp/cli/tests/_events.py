"""The events a real organization has on disk: ``.runtime/events/<day>/<process>-<pid>-<start>.jsonl``, one JSON object per line."""

from __future__ import annotations

import json
from pathlib import Path


def read_events(root: Path, kind: str | None = None) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for path in sorted((root / ".runtime" / "events").glob("*/*.jsonl")):
        out.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    out.sort(key=lambda e: (str(e["ts"]), int(str(e["seq"]))))
    return [e for e in out if kind is None or e["kind"] == kind]
