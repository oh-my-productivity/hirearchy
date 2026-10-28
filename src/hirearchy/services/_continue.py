"""The retired copy of a service that a root definition continues (design 5.10): which copy, and whether a request of it has a result to keep."""

from __future__ import annotations

import re
from pathlib import Path

from ..agents import RetiredArchive
from ..kernel import ROOT, latest_results, msg_time, parent, split_frontmatter
from ..mail import MailboxReader
from ._parse import FILE_SHAPE, as_int, contract_of, merged_versions
from ._places import RETIRED_DIR
from ._protocols import ContinuedServices, RetiredService, ServiceFiles, ServicePlaces
from .api import Contract

STAMP = r"\d{8}T\d{12}"  # ``%Y%m%dT%H%M%S%f``: the stamp ``RuleServiceRetirement`` gives a retired service
HISTORY = "history"


def copy_contracts(owner: str, name: str, retired: RetiredService) -> list[Contract]:
    """The versions of the copy's contract, oldest first and the current one last, read as ``FsServiceStore.versions`` reads them."""
    files = [split_frontmatter(text) for rel, text in retired.files if rel == "SERVICE.md" or re.fullmatch(r"history/SERVICE\.v\d+\.md", rel)]
    return [contract_of(owner, name, meta, body, None) for _, meta, body in merged_versions("SERVICE", files)]


def copy_playbook_version(retired: RetiredService) -> int:
    """The version of the copy's playbook; 0 when it has none."""
    for rel, text in retired.files:
        if rel == "PLAYBOOK.md":
            return as_int(split_frontmatter(text)[0].get("version"))
    return 0


class RecordedContinuations(ContinuedServices):
    """The newest retired copy of ``owner``'s service ``name``, when a request of it has a result of any status.

    A copy is a directory with a regular ``SERVICE.md`` in ``<owner>/services/.retired/<name>-<stamp>/``, or in a retired tree of the owner
    (``.retired/<owner>-<stamp>/services/<name>/`` and ``.../services/.retired/<name>-<stamp>/``). Every candidate path is built from the layout
    and the archive, never from a name read in a file; the newest copy is the one with the greatest ``defined`` (none sorts first), ties to the
    greater path."""

    def __init__(self, places: ServicePlaces, archive: RetiredArchive, mail: MailboxReader, files: ServiceFiles) -> None:
        self._places = places
        self._archive = archive
        self._mail = mail
        self._files = files

    def continued(self, owner: str, name: str) -> RetiredService | None:
        newest: tuple[tuple[bool, float, str], Path, Contract] | None = None
        for path in self._candidates(owner, name):
            if "SERVICE.md" not in self._files.listdir(path):
                continue  # no directory (a link is none) with a SERVICE.md: no copy
            text = self._files.read_text(path / "SERVICE.md")
            if text is None:
                continue  # not a regular file
            contract = contract_of(owner, name, *split_frontmatter(text), None)
            key = (contract.defined is not None, contract.defined.timestamp() if contract.defined is not None else 0.0, self._places.rel(path))
            if newest is None or key > newest[0]:
                newest = (key, path, contract)
        if newest is None:
            return None
        _, path, contract = newest
        recorded = self._recorded(owner, name, contract)
        if not recorded:
            return None
        return RetiredService(self._places.rel(path), self._read(path), recorded)

    def _candidates(self, owner: str, name: str) -> list[Path]:
        """The directories that may be a retired copy, from the layout (the owner's own ``.retired``) and the archive (its retired trees)."""
        stamped = re.compile(re.escape(name) + "-" + STAMP)
        services = [self._places.services_dir(owner)]
        found: list[Path] = []
        for tree in self._archive.trees():
            if tree.top_level and tree.addr == owner:
                here = tree.path / services[0].name
                services.append(here)
                found.append(here / name)
        for directory in services:
            retired = directory / RETIRED_DIR
            found += [retired / entry for entry in sorted(self._files.listdir(retired)) if stamped.fullmatch(entry)]
        return found

    def _recorded(self, owner: str, name: str, contract: Contract) -> int:
        """The requests of the service since the copy's ``created`` (all of them without one) whose latest result has any status."""
        client = parent(owner) or ROOT
        since = contract.created
        results = latest_results(self._mail.received(client))
        return sum(
            1 for m in self._mail.sent(client)
            if m.type == "task" and m.to == owner and m.service == name and m.id in results
            and (since is None or (msg_time(m) or since) >= since)
        )

    def _read(self, path: Path) -> tuple[tuple[str, str], ...]:
        """The files of the shapes the copy holds, the kept versions first and ``SERVICE.md`` last."""
        names = [f"{HISTORY}/{entry}" for entry in sorted(self._files.listdir(path / HISTORY))] + ["PLAYBOOK.md", "RETIRED.md", "SERVICE.md"]
        found = [(rel, self._files.read_text(path / rel)) for rel in names if FILE_SHAPE.fullmatch(rel)]
        return tuple((rel, text) for rel, text in found if text is not None)
