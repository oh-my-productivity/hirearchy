"""orgmcp.dashboard: the terminal dashboard of ``orgmcp dash`` (see :mod:`orgmcp.dashboard.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = [*api.__all__]
