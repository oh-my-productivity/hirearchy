"""Providers of the ``skill`` ports (ARCHITECTURE.md 6.1)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from ..kernel import Environment
from ..skill import SkillCheck, SkillInstaller, SkillSource, SkillStore
from ..skill._fs import FsSkillStore
from ..skill._install import CopySkillInstaller
from ..skill._source import PackagedSkillSource
from ._builder import Builder


def package_dir() -> Path:
    """The directory of the ``hirearchy`` package, from the import system: where the wheel's ``_skill/`` or the checkout's tree is found from."""
    spec = importlib.util.find_spec("hirearchy")
    assert spec is not None and spec.origin is not None  # hirearchy is imported: this module is part of it
    return Path(spec.origin).resolve().parent


def skill_check(environment: Environment) -> SkillCheck:
    """The check of the installed skill against the packaged one, for callers that have an environment but no organization."""
    return CopySkillInstaller(PackagedSkillSource(package_dir()), FsSkillStore(environment.home))


def register(b: Builder) -> None:
    b.provide(SkillSource, lambda b: PackagedSkillSource(package_dir()))
    b.provide(SkillStore, lambda b: FsSkillStore(b.get(Environment).home))
    b.provide(SkillInstaller, lambda b: CopySkillInstaller(b.get(SkillSource), b.get(SkillStore)))
    b.provide(SkillCheck, lambda b: CopySkillInstaller(b.get(SkillSource), b.get(SkillStore)))
