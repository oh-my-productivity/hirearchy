"""hirearchy.progress: what the user reads back when they ask "status?" (see :mod:`hirearchy.progress.api`).

``progress(org, task_id=None)`` is part of the permanent compatibility surface (README): ``_function`` keeps its signature and its text.
"""

from . import api
from .api import *  # noqa: F403
from ._function import progress

__all__ = [*api.__all__, "progress"]
