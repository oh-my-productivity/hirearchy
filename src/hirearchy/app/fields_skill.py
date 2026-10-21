"""Runtime fields of ``skill`` (ARCHITECTURE.md 3.33): one field per port that ``wire_skill.py`` builds."""

from __future__ import annotations

from dataclasses import dataclass

from ..skill import SkillInstaller, SkillSource, SkillStore

STEP: str | None = "A-skill"  # the step that filled this part (see test_runtime_fields)
NOT_A_FIELD: dict[str, str] = {}  # port -> why it is not a runtime field (a value, a factory, ...)


@dataclass(frozen=True)
class Fields:
    skill_source: SkillSource
    skill_store: SkillStore
    skill_installer: SkillInstaller
