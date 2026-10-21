"""hirearchy.eventlog: the on-disk event log and the readers of its format (see :mod:`hirearchy.eventlog.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
