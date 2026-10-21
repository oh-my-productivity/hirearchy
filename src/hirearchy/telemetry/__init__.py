"""hirearchy.telemetry: the event log, emission side (see :mod:`hirearchy.telemetry.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = [*api.__all__]
