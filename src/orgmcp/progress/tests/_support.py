"""Helpers shared by the tests of ``progress`` (no test lives here)."""

from __future__ import annotations

import pytest

XFAIL = pytest.mark.xfail(strict=True, reason="red: C-progress", raises=NotImplementedError)
