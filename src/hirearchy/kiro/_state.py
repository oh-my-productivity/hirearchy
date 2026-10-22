"""``FsKiroState``: the private kiro home, the fresh scratch directory and the audit of the home (docs/design/kiro-runtime-v3.md 8.2, 8.4)."""

from __future__ import annotations

import json
import re
import shutil
import stat
from collections.abc import Sequence
from pathlib import Path

from ..kernel import Clock
from .api import KiroHomeAudit, KiroStateDirs

TMP_GRACE = 60.0  # seconds a temp file of the atomic writer may exist in ``agents/`` before it counts as planted (A8)
_PROFILE = re.compile(r"^hirearchy-[a-z0-9-]+\.json$")  # the only names FsProfileStore writes
_LISTED = (  # entries kiro-cli would load into every agent (doc-derived, unproven by probes except permissions.yaml)
    "AGENTS.md", "cloud-cache", "hooks", "powers", "settings/mcp.json", "settings/permissions.yaml", "settings/permissions.yml",
    "skills", "steering", "workflows", "workspace-roots",
)


def planted_problem(home: Path, entries: Sequence[str]) -> str | None:
    """Why a home with these ``planted`` entries cannot be used (M7 when ``cloud-cache`` is among them, else M6), or ``None``."""
    if not entries:
        return None
    if "cloud-cache" in entries:
        return (
            f"the kiro home {home} holds cloud-cache/, configuration kiro-cli synced for this account whose hooks, steering and powers "
            "would run in every agent: synced cloud configuration cannot be confined; this account cannot run hirearchy agents confined"
        )
    return (
        f"the kiro home {home} holds configuration kiro-cli would load into every agent: {', '.join(entries)}; "
        "remove it (this home belongs to hirearchy)"
    )


def _exists(path: Path) -> bool:
    try:
        path.lstat()
    except OSError:
        return False
    return True


class FsKiroState(KiroStateDirs, KiroHomeAudit):
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    # ------------------------------------------------------------------------------------------------ KiroStateDirs

    def private_dir(self, path: Path) -> None:
        if path.is_symlink():
            raise OSError(f"{path} is a symlink; refusing to use it as a kiro home")
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)

    def fresh(self, path: Path) -> None:
        for parent in path.parents:
            if parent.is_symlink():
                raise OSError(f"{parent} is a symlink; refusing to prepare {path} below it")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            mode = None
        if mode is not None:
            if stat.S_ISDIR(mode):
                if not shutil.rmtree.avoids_symlink_attacks:
                    raise OSError(f"cannot safely remove {path} on this platform")
                shutil.rmtree(path)
            else:
                path.unlink()  # a symlink or a file: removed, never followed
        path.mkdir(mode=0o700)

    # ------------------------------------------------------------------------------------------------- KiroHomeAudit

    def planted(self, home: Path) -> list[str]:
        found = [rel for rel in _LISTED if _exists(home / rel)]
        found += self._planted_agents(home / "agents")
        return sorted(found)

    def _planted_agents(self, agents: Path) -> list[str]:
        try:
            mode = agents.lstat().st_mode
        except OSError:
            return []
        if not stat.S_ISDIR(mode):
            return ["agents"]
        found: list[str] = []
        for entry in sorted(agents.iterdir()):
            if not self._ours(entry):
                found.append(f"agents/{entry.name}")
        return found

    def _ours(self, entry: Path) -> bool:
        """A regular file the atomic writer is writing right now, or a well-formed hirearchy profile."""
        try:
            info = entry.lstat()
        except OSError:
            return False
        if not stat.S_ISREG(info.st_mode):
            return False
        if entry.name.startswith(".tmp-"):
            return self._clock.time() - info.st_mtime < TMP_GRACE
        if not _PROFILE.match(entry.name):
            return False
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return isinstance(data, dict) and data.get("name") == entry.name[: -len(".json")]

