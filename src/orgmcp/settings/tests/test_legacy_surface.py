"""The legacy names of the slice are the settings package's objects (``core``, ``health``): one definition, many names."""

from __future__ import annotations

import orgmcp.settings as settings
from orgmcp.settings.tests._legacy import legacy


def test_core_exports_the_settings_constants_and_functions_of_the_package() -> None:
    core = legacy("core")
    assert core.DEFAULT_CONFIG is settings.DEFAULT_CONFIG
    assert core.DEFAULT_MODEL == settings.DEFAULT_MODEL
    assert core.config_default_model is settings.config_default_model
    assert core._message_cap is settings.config_message_cap


def test_health_re_exports_the_numeric_readers_of_the_package() -> None:
    health = legacy("health")
    assert health.config_number is settings.config_number
    assert health._number is settings.finite_number
