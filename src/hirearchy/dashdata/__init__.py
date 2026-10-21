"""hirearchy.dashdata: the data of the terminal dashboard, UI-free and cached (see :mod:`hirearchy.dashdata.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
