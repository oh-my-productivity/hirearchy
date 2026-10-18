"""Providers of the ``skill`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from ..kernel import Environment
from ..skill import SkillInstaller, SkillSource, SkillStore
from ..skill._fs import FsSkillStore
from ..skill._install import CopySkillInstaller
from ..skill._source import PackagedSkillSource
from ._builder import Builder


def package_dir() -> Path:
    """The directory of the ``orgmcp`` package, from the import system: where the wheel's ``_skill/`` or the checkout's tree is found from."""
    spec = importlib.util.find_spec("orgmcp")
    assert spec is not None and spec.origin is not None  # orgmcp is imported: this module is part of it
    return Path(spec.origin).resolve().parent


def register(b: Builder) -> None:
    b.provide(SkillSource, lambda b: PackagedSkillSource(package_dir()))
    b.provide(SkillStore, lambda b: FsSkillStore(b.get(Environment).home))
    b.provide(SkillInstaller, lambda b: CopySkillInstaller(b.get(SkillSource), b.get(SkillStore)))
