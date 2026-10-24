"""The team's checked versions of the files it delivered: ``CheckedVersions`` over the organization's git history and files, and the blob ids they are
compared with (``reflection`` may not import ``snapshots``, so the composition root joins them; design 6.3)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from ..kernel import Message, OrgLayout
from ..reflection._ports import BlobIds, CheckedVersions
from ..snapshots import OrgHistory, blob_id

FILE_LIMIT = 4 * 1024 * 1024  # bytes of a file in the organization that are read to name its version
_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


class GitBlobIds(BlobIds):
    def of(self, data: bytes, hexlen: int) -> str:
        return blob_id(data, hexlen)


class GitCheckedVersions(CheckedVersions):
    """``at_result``: the file as the team reported it, at the first commit that holds the result's sent copy (the scheduler commits after every run,
    so that commit has the artifact as the team left it). Answers are kept for the life of the runtime: a found one for good (commits are immutable), a
    ``None`` under the ``HEAD`` it was asked at, so a pair that is not committed yet is asked again only after the next commit."""

    def __init__(self, history: OrgHistory, paths: OrgLayout) -> None:
        self._history = history
        self._paths = paths
        self._found: dict[tuple[str, str], tuple[str, str]] = {}
        self._unknown: dict[tuple[str, str], str | None] = {}  # (result id, path) -> the HEAD at which git did not know it
        self._root: Path | None = None

    def at_result(self, result: Message, path: str) -> tuple[str, str] | None:
        key = (result.id, path)
        if key in self._found:
            return self._found[key]
        head = self._history.head()  # read before the question: if a commit lands meanwhile, the next call asks again
        if key in self._unknown and self._unknown[key] == head:
            return None
        sent = f"{self._paths.rel(self._paths.box(result.sender, 'sent'))}/{result.id}.md"
        commit = self._history.first_commit_with(sent)
        blob = None if commit is None else self._history.blob(commit, path)
        if commit is None or blob is None:
            self._unknown[key] = head
            return None
        self._unknown.pop(key, None)
        self._found[key] = (commit, blob)
        return self._found[key]

    def current(self, path: str, hexlen: int) -> str | None:
        data = self._read(path)
        return None if data is None else blob_id(data, hexlen)

    def text(self, commit: str, path: str, limit: int) -> bytes | None:
        return self._history.text(commit, path, limit)

    def _read(self, path: str) -> bytes | None:
        """The bytes of the organization's file ``path``: component by component from the organization's directory, never through a link, only a
        regular file, at most 4 MiB; None otherwise."""
        parts = path.split("/")
        if not path or "\0" in path or any(part in ("", ".", "..") for part in parts):
            return None
        if self._root is None:
            self._root = Path(self._paths.root).resolve()  # the organization directory may itself be reached through a link: the user's layout
        fd = -1
        try:
            fd = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            for part in parts[:-1]:
                nxt = os.open(part, _DIRECTORY, dir_fd=fd)
                os.close(fd)
                fd = nxt
            last = os.open(parts[-1], _FILE, dir_fd=fd)
            os.close(fd)
            fd = last
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return None
            data = bytearray()
            while len(data) <= FILE_LIMIT:
                chunk = os.read(fd, min(65536, FILE_LIMIT + 1 - len(data)))
                if not chunk:
                    break
                data += chunk
            return bytes(data) if len(data) <= FILE_LIMIT else None
        except OSError:
            return None
        finally:
            if fd >= 0:
                os.close(fd)
