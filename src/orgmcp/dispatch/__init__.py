"""orgmcp.dispatch: the protocol rules for every message an agent sends (see :mod:`orgmcp.dispatch.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
