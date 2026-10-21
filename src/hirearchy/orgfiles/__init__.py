"""hirearchy.orgfiles: the guard of every file an agent reads or writes (see :mod:`hirearchy.orgfiles.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
