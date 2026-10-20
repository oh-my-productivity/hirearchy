"""The legacy names of the slice are the settings package's objects (``core``): one definition, many names."""

from __future__ import annotations

import orgmcp.settings as settings
from orgmcp.settings.tests._legacy import legacy


def test_core_exports_the_settings_constants_and_functions_of_the_package() -> None:
    core = legacy("core")
    assert core.DEFAULT_CONFIG is settings.DEFAULT_CONFIG
    assert core.DEFAULT_MODEL == settings.DEFAULT_MODEL
    assert core.config_default_model is settings.config_default_model
    assert core._message_cap is settings.config_message_cap
