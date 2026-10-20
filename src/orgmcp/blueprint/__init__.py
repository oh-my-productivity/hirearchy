"""orgmcp.blueprint: a whole organization for one goal as a reviewable document (see :mod:`orgmcp.blueprint.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
