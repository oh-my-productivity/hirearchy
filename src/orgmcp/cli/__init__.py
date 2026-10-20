"""orgmcp.cli: the command line of the human and of the runtime (see :mod:`orgmcp.cli.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = [*api.__all__]
