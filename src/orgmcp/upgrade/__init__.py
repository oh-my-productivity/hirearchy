"""orgmcp.upgrade: bringing an organization's ORG.md rules up to the current template (see :mod:`orgmcp.upgrade.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
