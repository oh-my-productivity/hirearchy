"""Whether a command line is the scheduler of an organization."""

from __future__ import annotations

from pathlib import Path

from ._ports import SchedulerRecognizer


def _root_arguments(tokens: list[str]) -> list[str]:
    """The values given to ``--root`` in a command line."""
    return [tokens[i + 1] for i, t in enumerate(tokens[:-1]) if t == "--root"] + [t[7:] for t in tokens if t.startswith("--root=")]


def _same_dir(path: str, root: Path) -> bool:
    """Is ``path`` the directory ``root`` under another spelling (a symlink such as macOS /tmp -> /private/tmp, ``~``)?"""
    if not path.startswith(("/", "~")):
        return False  # relative to the other process's working directory: cannot be compared
    try:
        return Path(path).expanduser().resolve() == root.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


class SchedulerIdentity(SchedulerRecognizer):
    def recognises(self, command: str, root: Path) -> bool:
        """Does this command line plausibly start the scheduler of the organization at ``root``?

        Needs the ``run`` subcommand and either the org's root path or an ``orgmcp`` program. A ``--root`` that is not
        this org (or cannot be compared, being relative) is a no.
        """
        tokens = command.split()
        names_root = str(root) in command or any(_same_dir(t, root) for t in _root_arguments(tokens))
        has_root_flag = any(t == "--root" or t.startswith("--root=") for t in tokens)
        has_orgmcp = any(Path(t).name == "orgmcp" for t in tokens)
        return "run" in tokens and (names_root or (has_orgmcp and not has_root_flag))
