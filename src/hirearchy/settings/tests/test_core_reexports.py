"""The names ``hirearchy.core`` keeps for the slice are the settings package's objects: one definition, many names."""

from __future__ import annotations

import hirearchy.settings as settings
from hirearchy.settings.tests._reach import reach


def test_core_exports_the_settings_constants_and_functions_of_the_package() -> None:
    core = reach("core")
    assert core.DEFAULT_CONFIG is settings.DEFAULT_CONFIG
    assert core.DEFAULT_MODEL == settings.DEFAULT_MODEL
    assert core.config_default_model is settings.config_default_model
    assert core._message_cap is settings.config_message_cap
