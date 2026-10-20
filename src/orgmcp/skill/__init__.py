"""orgmcp.skill: the assistant skill that ships with orgmcp and its installation (see :mod:`orgmcp.skill.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
