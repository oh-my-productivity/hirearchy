"""orgmcp.stalls: the escalation ladder for tasks whose assignee has gone quiet (see :mod:`orgmcp.stalls.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
