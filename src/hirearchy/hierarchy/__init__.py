"""hirearchy.hierarchy: who may join the agent tree and who may leave it (see :mod:`hirearchy.hierarchy.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
