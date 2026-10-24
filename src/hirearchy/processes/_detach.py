"""Started as a script by ``PopenProcessSpawner.spawn_detached``: it starts the detached process and exits at once, so that process is
re-parented and is no descendant of the caller."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import NoReturn


def main(args: list[str]) -> NoReturn:
    """``<log> -- <argv...>``: start argv in a new session with stdin /dev/null and its output appended to log, print its pid, and leave
    without waiting for it. Exit 2 on a malformed command line, 1 when argv cannot be started (the reason on stderr)."""
    if len(args) < 3 or args[1] != "--":
        sys.stderr.write("usage: _detach.py <log> -- <argv...>\n")
        sys.stderr.flush()
        os._exit(2)
    log, command = args[0], args[2:]
    try:
        with open(log, "ab") as out:
            child = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True,
            )
    except OSError as error:
        sys.stderr.write(f"{error}\n")
        sys.stderr.flush()
        os._exit(1)
    sys.stdout.write(f"{child.pid}\n")
    sys.stdout.flush()
    os._exit(0)  # no wait and no clean-up of the Popen object: the child's parent is gone at once


if __name__ == "__main__":
    main(sys.argv[1:])
