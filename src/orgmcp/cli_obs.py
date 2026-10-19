"""Shim of the flat module that held the commands of ``orgmcp obs`` and ``orgmcp check`` (they are classes of ``orgmcp.cli`` now).

It keeps one name, ``time``: ``tests/test_observe.py`` replaces ``orgmcp.cli_obs.time.sleep`` (the patch point of ``obs now --watch`` and ``obs events --follow``), and the
sleep of the command line is the clock of the kernel, which calls ``time.sleep``. It goes with that test when it moves into ``cli/tests`` (E1-e).
"""

import time  # noqa: F401 - the patch point
