"""``StateDirPlaces``: where hirearchy keeps the kiro homes and working directories (docs/design/kiro-runtime-v3.md 8.1)."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from ..kernel import Environment, OrgLayout
from ._confinement import _path_problem, _shown
from .api import KiroPlaces

_KEY_SLUG = 40  # characters of an address kept in an agent key


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))


class StateDirPlaces(KiroPlaces):
    """``<state>`` is ``$HIREARCHY_STATE_DIR``, else ``~/Library/Application Support/hirearchy`` on macOS, else
    ``$XDG_STATE_HOME/hirearchy`` (when absolute) or ``~/.local/state/hirearchy``."""

    def __init__(self, layout: OrgLayout, environment: Environment, platform: str) -> None:
        self._layout = layout
        self._environment = environment
        self._platform = platform

    def _override(self) -> str | None:
        return self._environment.get("HIREARCHY_STATE_DIR") or None

    def _state(self) -> Path:
        override = self._override()
        if override is not None:
            return _real(self._environment.cwd() / override)  # a relative value is a problem(); it still resolves, deterministically
        home = self._environment.home()
        if self._platform == "darwin":
            return _real(home / "Library" / "Application Support" / "hirearchy")
        xdg = self._environment.get("XDG_STATE_HOME")
        if xdg and os.path.isabs(xdg):
            return _real(Path(xdg) / "hirearchy")
        return _real(home / ".local" / "state" / "hirearchy")

    def _org_id(self) -> str:
        root = _real(Path(self._layout.root).expanduser())
        base = root.name
        if base.lower() == "org" and root.parent.name:  # "org" alone says nothing: use "<parent>-org" (as the profile name does)
            base = f"{root.parent.name}-org"
        slug = _slug(base)[:24].strip("-") or "org"
        return f"{slug}-{hashlib.sha1(str(root).encode('utf-8')).hexdigest()[:16]}"

    def roots(self) -> tuple[Path, Path]:
        state = self._state()
        return state / "kiro-home", state / "kiro-cwd"

    def home(self) -> Path:
        return self.roots()[0] / self._org_id()

    def scratch(self, addr: str) -> Path:
        key = f"{_slug(addr)[:_KEY_SLUG].strip('-') or 'agent'}-{hashlib.sha1(addr.encode('utf-8')).hexdigest()[:8]}"
        return self.roots()[1] / self._org_id() / key

    def problem(self) -> str | None:
        override = self._override()
        if override is not None and not os.path.isabs(override):
            return f"HIREARCHY_STATE_DIR must be an absolute path, not {_shown(override)}"
        state = self._state()
        refused = _path_problem(str(state))
        if refused is not None:
            return refused
        home, user = self.home(), _real(self._environment.home())
        if home == user or home in user.parents:
            return (
                f"the kiro home {home} is the user's home directory {user} or above it: kiro-cli would fall back to ~/.kiro; "
                "set HIREARCHY_STATE_DIR to a folder that is not the home directory or above it"
            )
        return None
