"""orgmcp.agents: the on-disk registry of agents (see :mod:`orgmcp.agents.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
