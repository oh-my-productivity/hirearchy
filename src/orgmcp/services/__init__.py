"""orgmcp.services: standing services, with their contract, playbook, requests and feedback (see :mod:`orgmcp.services.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
