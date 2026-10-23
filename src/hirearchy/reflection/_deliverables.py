"""The only code that touches a contract's deliverable folder (design 6.3, DR-43, DR-45).

A contract names a place outside the organization (``deliverable.path``), so what is read there is bounded and contained: ``locate`` makes the path
absolute and resolves it as it is now; ``walk`` then opens it again component by component with ``O_NOFOLLOW``, so a component that became a link after
the resolve is reported (``link``) and never followed; a parent that can be passed through but not listed (mode ``--x``) is walked through; only the
place itself that cannot be opened is ``unreadable``. The entries of a folder are opened by name relative to its descriptor with ``O_NOFOLLOW |
O_NONBLOCK`` (a FIFO swapped in cannot block), at most 4 MiB a file, 200 entries a folder and the budget of the call in all. The bytes of a file are
returned to the caller, who keeps their blob id and drops them; a file name reaches root only through :func:`shown_name`.

Declared residual: a traverse-only parent swapped for a link and swapped back between its two ``stat`` calls is not detected; as for a link that was
there before the path was resolved (the user's own layout, ``/tmp`` on macOS), only the names and hashes of the direct files of the place reached
are used, never their contents beyond the hash.
"""

from __future__ import annotations

import errno
import json
import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kernel import clip_line
from ._ports import DeliverableFolder, FolderFile, FolderRead, Located

FILE_LIMIT = 4 * 1024 * 1024  # bytes of one file that are read; a larger file is `large`
READ_TOTAL = 32 * 1024 * 1024  # bytes of file content one call reads in all
ENTRY_LIMIT = 200  # entries of one folder that are read
CHUNK = 65536
NAME_SHOWN = 120  # characters of a file name that root sees
FOLDER_SHOWN = 200  # characters of a folder path that root sees

_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
_STATES = {"dir": "folder", "file": "file", "link": "link", "unreadable": "unreadable", "missing": "missing"}


def shown_name(text: str, limit: int) -> str:
    """``text`` (a file name, a folder path) as one quoted line root can read without being led by it (pure): ``json.dumps`` (quotes, backslashes and
    control characters escaped), every character that is still not printable (U+2028, DEL, ...) as ``\\uXXXX``, at most ``limit`` characters."""
    quoted = json.dumps(text, ensure_ascii=False)
    return clip_line("".join(ch if ch.isprintable() else f"\\u{ord(ch):04x}" for ch in quoted), limit)


def _words(error: OSError) -> str:
    """The operating system's words for ``error`` (never the name of the file it is about)."""
    return os.strerror(error.errno) if error.errno else "cannot be read"


def _lstat(name: str, dfd: int) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=dfd, follow_symlinks=False)
    except OSError:
        return None


@dataclass
class Opened:
    """What the walk reached: ``dir`` (``fd`` is the folder), ``file`` (``fd`` is the folder it is in, ``name`` the file relative to it), or why nothing
    was opened (``link``, ``unreadable``, ``missing``). The caller closes the descriptor."""

    kind: str
    fd: int = -1
    name: str = ""
    error: str = ""


def release(opened: Opened) -> None:
    """Close the descriptor a walk handed over (once)."""
    if opened.fd >= 0:
        os.close(opened.fd)
        opened.fd = -1


def carried_unchanged(fd: int, carried: Sequence[tuple[str, int, int]]) -> bool:
    """Is every traverse-only component the walk passed through (``(name relative to fd, st_dev, st_ino)``) still the same directory, and not a link?"""
    for name, dev, ino in carried:
        found = _lstat(name, fd)
        if found is None or not stat.S_ISDIR(found.st_mode) or (found.st_dev, found.st_ino) != (dev, ino):
            return False
    return True


def _refused(error: OSError, fd: int, name: str, last: bool, carried: list[tuple[str, int, int]]) -> Opened | None:
    """What a refused open of ``name`` (relative to ``fd``) means: the Opened that ends the walk, or None to go on (a traverse-only parent, now carried)."""
    if error.errno == errno.ENOENT:
        return Opened("missing")
    if error.errno in (errno.ENOTDIR, errno.ELOOP):  # a link (which of the two a system reports for one differs), a file, or something else
        found = _lstat(name, fd)
        if found is None:
            return Opened("missing")
        if stat.S_ISLNK(found.st_mode):
            return Opened("link")
        if stat.S_ISREG(found.st_mode) and last:
            return Opened("file", name=name) if carried_unchanged(fd, carried) else Opened("link")
        return Opened("missing")
    if error.errno in (errno.EACCES, errno.EPERM):
        if last:
            return Opened("unreadable", error=_words(error))  # the folder itself cannot be opened
        found = _lstat(name, fd)
        if found is None:
            return Opened("missing")
        if stat.S_ISLNK(found.st_mode):
            return Opened("link")
        if not stat.S_ISDIR(found.st_mode):
            return Opened("missing")
        carried.append((name, found.st_dev, found.st_ino))  # passed through, not listed: not a finding
        return None
    return Opened("unreadable", error=_words(error))


def walk(target: Path) -> Opened:
    """Open ``target`` (absolute) one component at a time from ``/``, never through a link (DR-43)."""
    parts = target.parts[1:]
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    pending = ""  # the traverse-only components carried so far, each followed by "/"
    carried: list[tuple[str, int, int]] = []
    keep = False  # the descriptor goes to the caller
    try:
        for index, part in enumerate(parts):
            name = pending + part
            try:
                opened = os.open(name, _DIRECTORY, dir_fd=fd)
            except OSError as error:
                stop = _refused(error, fd, name, index == len(parts) - 1, carried)
                if stop is None:
                    pending = name + "/"
                    continue
                if stop.kind == "file":
                    stop.fd, keep = fd, True
                return stop
            if not carried_unchanged(fd, carried):  # a traverse-only parent was swapped while the walk went on
                os.close(opened)
                return Opened("link")
            os.close(fd)
            fd, pending, carried = opened, "", []
        keep = True
        return Opened("dir", fd=fd)
    finally:
        if not keep:
            os.close(fd)


def read_one(dfd: int, name: str, left: int) -> FolderFile | None:
    """The file ``name`` (relative to the folder descriptor ``dfd``), opened without following a link and without blocking; None when what is there
    is not a regular file (a FIFO swapped in for the entry that was listed). ``left`` is what the call may still read."""
    shown = name.rsplit("/", 1)[-1]
    try:
        fd = os.open(name, _FILE, dir_fd=dfd)
    except OSError as error:
        return FolderFile(shown, "link") if error.errno == errno.ELOOP else FolderFile(shown, "unreadable", error=_words(error))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None
        mtime = info.st_mtime_ns // 1000
        if info.st_size > FILE_LIMIT:
            return FolderFile(shown, "large", mtime_us=mtime)
        if info.st_size > left:
            return FolderFile(shown, "limit", mtime_us=mtime)
        data = bytearray()
        while len(data) <= FILE_LIMIT:  # at most FILE_LIMIT + 1 bytes: a file that grew while it was read is `large`
            chunk = os.read(fd, min(CHUNK, FILE_LIMIT + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > FILE_LIMIT:
            return FolderFile(shown, "large", mtime_us=mtime)
        return FolderFile(shown, "file", bytes(data), mtime)
    except OSError as error:
        return FolderFile(shown, "unreadable", error=_words(error))
    finally:
        os.close(fd)


class FsDeliverableFolder(DeliverableFolder):
    """The deliverable places on disk (see the module)."""

    def locate(self, raw: object) -> Located | None:
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            given = Path(raw).expanduser()
            if not given.is_absolute():
                return None
            named = Path(os.path.normpath(given))
            link = _is_link(named)
            return Located(given.resolve(strict=False), named, link)
        except (OSError, RuntimeError):  # no home directory, a loop of links
            return None

    def kind(self, place: Located) -> str:
        if place.link:
            return "link"
        opened = walk(place.target)
        try:
            return _STATES[opened.kind]
        finally:
            release(opened)

    def read(self, place: Located, budget: int) -> FolderRead:
        if place.link:
            return FolderRead("link", str(place.named))
        opened = walk(place.target)
        try:
            if opened.kind == "dir":
                return self._folder(opened.fd, place, budget)
            if opened.kind == "file":
                return self._file(opened, place, budget)
            return FolderRead(_STATES[opened.kind], str(place.target), error=opened.error)
        finally:
            release(opened)

    @staticmethod
    def _folder(dfd: int, place: Located, budget: int) -> FolderRead:
        folder = str(place.target)
        rows: list[tuple[str, bool, bool]] = []
        try:
            with os.scandir(dfd) as entries:
                for entry in entries:
                    if not entry.name.startswith("."):  # `.DS_Store` and the like
                        rows.append((entry.name, entry.is_symlink(), entry.is_file(follow_symlinks=False)))
        except OSError as error:
            return FolderRead("unreadable", folder, error=_words(error))
        left, files = budget, []
        for name, is_link, is_file in sorted(rows)[:ENTRY_LIMIT]:
            if is_link:
                files.append(FolderFile(name, "link"))  # reported, never followed
            elif is_file:  # a folder, a FIFO, a socket, a device: never opened
                one = read_one(dfd, name, left)
                if one is not None:
                    left -= len(one.data)
                    files.append(one)
        return FolderRead("folder", folder, tuple(files), used=budget - left)

    @staticmethod
    def _file(opened: Opened, place: Located, budget: int) -> FolderRead:
        one = read_one(opened.fd, opened.name, budget)
        if one is None:
            return FolderRead("missing", str(place.target.parent))
        if one.kind == "link":
            return FolderRead("link", str(place.target))
        return FolderRead("file", str(place.target.parent), (one,), used=len(one.data))


def _is_link(path: Path) -> bool:
    try:
        return stat.S_ISLNK(os.lstat(path).st_mode)
    except OSError:
        return False
