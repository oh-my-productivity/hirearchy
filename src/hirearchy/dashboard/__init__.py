"""hirearchy.dashboard: the terminal dashboard of ``hirearchy dash`` (see :mod:`hirearchy.dashboard.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = [*api.__all__]
