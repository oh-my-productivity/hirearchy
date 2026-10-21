"""What the tests of the packages below ``reflection`` (dispatch, services) read of a case through it.

Those packages may not import ``reflection`` (it sits above them: its cases are derived from their messages), but a few of their tests assert what
``reflection`` makes of what they wrote: the ``## Lessons`` section of a result, the statistics of a case. They take the two pure functions from here.
(The cases themselves are read from the runtime: ``org.runtime.case_history.cases(owner, service)``.)
"""

from hirearchy.reflection import lessons_of, summarize

__all__ = ["lessons_of", "summarize"]
