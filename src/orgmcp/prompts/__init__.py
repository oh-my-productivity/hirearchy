"""orgmcp.prompts: the texts an agent is shown - whoami, the state summary, the run prompt (see :mod:`orgmcp.prompts.api`)."""

from . import api
from .api import *  # noqa: F403

__all__ = api.__all__
