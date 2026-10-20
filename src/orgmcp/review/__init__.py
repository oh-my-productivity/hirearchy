"""orgmcp.review: turns the health of the organization into notes for the managers who can act on it (see :mod:`orgmcp.review.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = [*api.__all__]
