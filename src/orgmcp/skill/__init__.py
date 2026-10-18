"""orgmcp.skill: the assistant skill that ships with orgmcp and its installation (see :mod:`orgmcp.skill.api`).

The module ``skill.py`` became this package in place (ARCHITECTURE.md 1.3 decision 2): ``api`` is the public surface; the old
function and constant names are still exported (``LEGACY_EXPORTS`` in ``tests/architecture/legacy_exports.py``) by the private
``_legacy`` module until step E3 removes them.
"""

from . import api
from .api import *  # noqa: F403
from ._legacy import SKILL_NAME, install_skill, skill_source

__all__ = [*api.__all__, "SKILL_NAME", "install_skill", "skill_source"]
