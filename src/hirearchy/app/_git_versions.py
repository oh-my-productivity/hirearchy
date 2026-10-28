"""One committed version of a file of the organization, as far as it can be compared (shared by ``GitBarHistory`` and ``GitCharterHistory``).

``reflection`` and ``retro`` may not import ``snapshots``, so the composition root joins them: both of its adapters ask ``OrgHistory`` which commits
changed the charters and ORG.md and read each version once."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..kernel import split_frontmatter
from ..snapshots import Change, OrgHistory

COMMITS = 40  # the newest commits that changed one of the files, read at most
VERSION_LIMIT = 64 * 1024  # bytes of one version that are read; a larger one is not compared
TIME_BOUND = 5.0  # seconds of git time one call may take
ORG = "ORG.md"


@dataclass(frozen=True)
class Version:
    """One committed version of a file: its frontmatter and body."""

    meta: Mapping[str, object]
    body: str


def read_version(history: OrgHistory, change: Change) -> Version | None:
    """The version ``change`` names; None when it is above ``VERSION_LIMIT``, cannot be read, is not UTF-8 or its frontmatter does not parse."""
    data = history.text(change.commit, change.path, VERSION_LIMIT)
    if data is None:
        return None
    try:
        meta, body = split_frontmatter(data.decode("utf-8"))
    except Exception:  # noqa: BLE001 - not UTF-8, or YAML that does not parse (PyYAML is imported by kernel and blueprint only)
        return None
    return Version(meta, body)
