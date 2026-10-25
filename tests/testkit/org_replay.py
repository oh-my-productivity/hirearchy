"""The kit of the exit-check replays of phase 0b (design 19.1): it builds, from the files a study kept, an organization directory that the product's own
code reads (no scheduler, no LLM, no network, no git).

``materialize(corpus, root, variant=None)`` follows ``org_replay_manifest.MANIFESTS[corpus]`` (E, E2, A5, E3, E4-s1r, E4-s2r, E4-s3) and builds, below the
directory ``root`` (created), the organization ``root/org`` and returns it; ``Org(materialize(...))`` opens it. A deliverable folder is ``root/deliverables``
when the corpus kept deliverables (E4), else ``root/no-deliverables``, which is never created, so the deliverable checks find nothing.

* Messages are parsed with ``kernel.split_frontmatter`` and written byte for byte, each in the box it was kept in. A corpus that kept sent boxes only
  (``received_from_sent``: E, E2, A5) also gets the recipient's copy in its ``read/``. A message of the ``runtime`` is written only to its recipient (the
  runtime has no sent box). The same id kept twice must be byte-identical, else the test fails.
* Contract and playbook versions go to ``<owner>/services/<service>/history/`` and the current file. **The contract's ``deliverable.path`` line is
  rewritten to the replay's deliverable folder: that edit of the materialized copy is the only change to a kept record.**
* Times are UTC microseconds (``utc_us``): message ids are UTC already; ``memos/versions/INDEX.txt`` is ``+01:00`` and the deliverables log is ``Z``.
  A delivered file's modification time is the manifest's pin; the manifest pins the start time of the last logged command that wrote the file.
* Run logs are empty files named like the kept ones (the case counts read the names only).
* A charter the corpus kept is copied; every other address the messages name (and its ancestors), except ``root`` and ``runtime``, gets a minimal
  charter (``name`` only).
* ``variant`` (E3 only): ``"r2-links-r1"`` adds one human-tier link on a rejection; ``"r3-overspend-<N>"`` adds ``N`` empty run logs of ``lead`` inside
  case ``...-root-ab46``'s window. **``r3-overspend-<N>`` is a constructed variant, not an observation** (design 19.3 E3-9): no study corpus fires the
  cost alarm under D-E5-6's rule, so this is the only replay in which it fires.

The kit reads the corpora read-only. A listed file or folder that is missing, a message that does not parse, or two different copies of one id FAILS the
test (``pytest.fail``), never skips it: a replay that quietly did not run proves nothing.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping
from typing import Any
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.kernel import RESERVED, ROOT, split_frontmatter

from . import org_replay_manifest

RUNTIME = "runtime"
INDEX_LINE = re.compile(r"^(?P<path>\S+) v(?P<k>\d+) (?P<hash>[0-9a-f]+) (?P<time>\S+) md5 (?P<md5>[0-9a-f]{32})$")
LOG_HEADER = re.compile(r"^\[(?P<time>[^\]]+)\] call #(?P<call>\d+) ")
CONTRACT_PATH = re.compile(r"^  path: .*$", re.MULTILINE)
R2_LINKS_R1_ID = "20261021T154600000000-root-0b01"
R2_LINK_SOURCE = "20261021T154557001479-root-8ca0"  # the human-tier link on ab46's rejection that the variant copies
OVERSPEND = re.compile(r"r3-overspend-(\d{1,2})")
OVERSPEND_STAMP = "20261021T1543000000{n:02d}"  # 21 characters, inside case ...-root-ab46's window (15:38:09.201054 to 15:43:42.518435)


def utc_us(text: str) -> int:
    """Microseconds since the epoch, UTC, of an ISO time with an offset or ``Z`` (``2026-10-22T19:12:45.031Z``, ``2026-10-22T19:36:41+01:00``)."""
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        pytest.fail(f"{text!r} has no offset or Z: a time of the evidence must say its zone")
    delta = moment.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def deliverable_folder(root: Path, corpus: str, manifest: Mapping[str, Any] | None = None) -> Path:
    """Where the replay's deliverables are: ``root/deliverables`` when the corpus kept some, else a folder that is never created."""
    entry = manifest if manifest is not None else org_replay_manifest.MANIFESTS[corpus]
    return root / ("deliverables" if entry["deliverables"] else "no-deliverables")


def _file(path: Path) -> Path:
    if not path.is_file():
        pytest.fail(f"no evidence file {path}")
    return path


def _dir(path: Path) -> Path:
    if not path.is_dir():
        pytest.fail(f"no evidence directory {path}")
    return path


def _write(path: Path, data: bytes, written: dict[Path, bytes]) -> None:
    """Write ``data`` at ``path``; the same path written twice must get the same bytes."""
    if path in written:
        if written[path] != data:
            pytest.fail(f"{path} would be written twice with different bytes")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    written[path] = data


def _box(org: Path, address: str, box: str) -> Path:
    return (org if address == ROOT else org / address) / box


def message_files(source: Path, pattern: str) -> list[Path]:
    """The messages of one listed folder (every file of the directory) or glob (``msgs/sent__*.md``); none at all fails the test."""
    if "*" in pattern:
        found = sorted(source.glob(pattern))
        if not found:
            pytest.fail(f"no evidence file matches {source / pattern}")
        return found
    return sorted(_dir(source / pattern).iterdir())


def read_message(path: Path) -> tuple[dict[str, object], bytes]:
    """``(frontmatter, bytes)`` of a kept message. It must parse and carry an ``id``, a ``from`` and a ``to`` that are text, and its file must be named
    after its id (``<id>.md``, or ``<prefix>__<id>.md``)."""
    data = _file(path).read_bytes()
    try:
        meta, _ = split_frontmatter(data.decode("utf-8"))
    except Exception as error:  # noqa: BLE001  (a YAML error is yaml's own type; PyYAML is not imported here)
        pytest.fail(f"the message {path} does not parse: {type(error).__name__}")
    for key in ("id", "from", "to"):
        if not isinstance(meta.get(key), str) or not meta[key]:
            pytest.fail(f"the message {path} has no {key} in its frontmatter: it does not parse as a message")
    if not path.name.endswith(f"{meta['id']}.md"):
        pytest.fail(f"the message {path} is not named after its id {meta['id']}")
    return meta, data


def _versions(entry: Mapping[str, Any], kind: str) -> list[tuple[str, int | None]]:
    listed = entry[kind]
    assert isinstance(listed, tuple)
    return list(listed)


def _contract_text(path: Path, deliverables: Path) -> bytes:
    """The kept contract with the one edit of the kit: its ``deliverable.path`` line names the replay's deliverable folder."""
    text = _file(path).read_text(encoding="utf-8")
    meta, _ = split_frontmatter(text)
    head = text.split("\n---", 1)[0]
    if len(CONTRACT_PATH.findall(head)) != 1 or not isinstance(meta.get("deliverable"), dict):
        pytest.fail(f"{path} has no single `  path:` line under `deliverable:` to rewrite")
    return (CONTRACT_PATH.sub(f"  path: {deliverables}", head, count=1) + text[len(head):]).encode("utf-8")


def index_entries(index: Path) -> dict[str, list[dict[str, object]]]:
    """``memos/versions/INDEX.txt`` as ``{path: [{k, hash, time (UTC microseconds), md5}, ...]}``, in the file's order; the lines of the working tree
    are not versions. A line that is neither fails the test."""
    found: dict[str, list[dict[str, object]]] = {}
    for line in _file(index).read_text(encoding="utf-8").splitlines():
        if not line.strip() or " working tree md5 " in line:
            continue
        m = INDEX_LINE.match(line)
        if m is None:
            pytest.fail(f"{index}: the line {line!r} is not a version of a file")
        found.setdefault(m["path"], []).append({"k": int(m["k"]), "hash": m["hash"], "time": utc_us(m["time"]), "md5": m["md5"]})
    return found


def newest_version(index: Path, path: str) -> tuple[Path, str]:
    """The kept version file of ``path`` that INDEX.txt lists with the latest UTC time (the highest version on a tie), and its listed md5."""
    versions = index_entries(index).get(path)
    if not versions:
        pytest.fail(f"{index} lists no version of {path}")
    best = max(versions, key=lambda v: (int(str(v["time"])), int(str(v["k"]))))
    name = f"{Path(path).stem}.v{best['k']}.{best['hash']}.md"
    return _file(index.parent / name), str(best["md5"])


def log_block(log: Path, line: int) -> tuple[str, str]:
    """``(time, text)`` of the logged command that starts at ``line`` (1-based) of the deliverables log: the header line ``[<time>] call #<n> ...`` and
    everything up to the next header. A line that is not a header fails the test."""
    lines = _file(log).read_text(encoding="utf-8").splitlines()
    if not 1 <= line <= len(lines):
        pytest.fail(f"{log} has no line {line}")
    m = LOG_HEADER.match(lines[line - 1])
    if m is None:
        pytest.fail(f"line {line} of {log} is not the start of a logged command: {lines[line - 1]!r}")
    end = next((i for i in range(line, len(lines)) if LOG_HEADER.match(lines[i])), len(lines))
    return m["time"], "\n".join(lines[line - 1 : end])


def _charter(leaf: str) -> bytes:
    return f"---\nname: {leaf}\n---\n".encode()


def _address_parts(address: str) -> list[str]:
    return ["/".join(address.split("/")[: i + 1]) for i in range(len(address.split("/")))]


def _agent_address(address: str) -> bool:
    return address not in (ROOT, RUNTIME) and all(part not in RESERVED for part in address.split("/"))


def _variant_link(source: bytes) -> bytes:
    """E3 ``r2-links-r1``: ``...-root-8ca0`` with another id, time, title and criterion (design 19.1); its body and every other line are 8ca0's."""
    text = source.decode("utf-8")
    for prefix, new in (
        ("id: ", f"id: {R2_LINKS_R1_ID}"),
        ("title: ", "title: 'criterion link on \"Memo for the meeting of 2026-10-19\": R1'"),
        ("created: ", "created: '2026-10-21T15:46:00+00:00'"),
        ("criterion: ", "criterion: R1"),
    ):
        text, n = re.subn(rf"^{re.escape(prefix)}.*$", new, text, count=1, flags=re.MULTILINE)
        if n != 1:
            pytest.fail(f"the message to copy for r2-links-r1 has no `{prefix}` line")
    return text.encode("utf-8")


def materialize(corpus: str, root: Path, variant: str | None = None, *, manifest: Mapping[str, Any] | None = None) -> Path:
    """Build the organization of ``corpus`` below ``root`` and return its directory (``root/org``); see the module. ``manifest`` is for the tests of the
    kit (default ``org_replay_manifest.MANIFESTS[corpus]``)."""
    entry = manifest if manifest is not None else org_replay_manifest.MANIFESTS[corpus]
    source = _dir(Path(str(entry["evidence"])))
    root = root.resolve()
    org, written = root / "org", {}
    deliverables = deliverable_folder(root, corpus, entry)
    overspend = OVERSPEND.fullmatch(variant) if variant else None
    if variant is not None and corpus != "E3":
        pytest.fail(f"the variant {variant!r} is for E3 only, not {corpus}")
    if variant is not None and variant != "r2-links-r1" and overspend is None:
        pytest.fail(f"unknown variant {variant!r}: r2-links-r1 or r3-overspend-<N>")
    org.mkdir(parents=True, exist_ok=True)
    _write(org / "ORG.md", _file(source / str(entry["org_md"])).read_bytes(), written)

    named: set[str] = set()
    ids: dict[str, bytes] = {}
    for pattern, address, box in entry["boxes"]:
        for path in message_files(source, pattern):
            meta, data = read_message(path)
            msg_id, sender, recipient = str(meta["id"]), str(meta["from"]), str(meta["to"])
            if msg_id in ids and ids[msg_id] != data:
                pytest.fail(f"the message {msg_id} is kept twice with different bytes ({path})")
            ids[msg_id] = data
            named |= {sender, recipient, address}
            if not (box == "sent" and sender == RUNTIME):  # the runtime has no sent box
                _write(_box(org, address, box) / f"{msg_id}.md", data, written)
            if entry["received_from_sent"] and box == "sent":
                _write(_box(org, recipient, "read") / f"{msg_id}.md", data, written)

    service, owner = entry["service"], entry["owner"]
    if service is not None:
        place = org / str(owner) / "services" / str(service)
        for kind, name, history in (("contracts", "SERVICE", "SERVICE"), ("playbooks", "PLAYBOOK", "PLAYBOOK")):
            for file, version in _versions(entry, kind):
                data = _contract_text(source / file, deliverables) if kind == "contracts" else _file(source / file).read_bytes()
                _write(place / (f"{name}.md" if version is None else f"history/{history}.v{version}.md"), data, written)
        named.add(str(owner))

    for folder, address in entry["run_logs"]:
        for log in sorted(_dir(source / folder).glob("*.log")):
            _write(_box(org, address, "runs") / log.name, b"", written)
        named.add(address)
    if overspend is not None:
        count = int(overspend.group(1))
        if not 1 <= count <= 99:
            pytest.fail(f"r3-overspend-{count}: N is 1 to 99")
        for n in range(1, count + 1):
            _write(org / "lead" / "runs" / f"{OVERSPEND_STAMP.format(n=n)}.log", b"", written)  # a constructed variant, not an observation

    if variant == "r2-links-r1":
        link = _variant_link(ids[R2_LINK_SOURCE]) if R2_LINK_SOURCE in ids else pytest.fail(f"{R2_LINK_SOURCE} is not in E3's messages")
        _write(org / "sent" / f"{R2_LINKS_R1_ID}.md", link, written)
        _write(org / "lead" / "read" / f"{R2_LINKS_R1_ID}.md", link, written)

    charters = dict(entry["charters"])
    for address in sorted(a for a in named if _agent_address(a)):
        for part in _address_parts(address):
            charters.setdefault(part, "")
    for address, file in sorted(charters.items()):
        data = _file(source / file).read_bytes() if file else _charter(address.rsplit("/", 1)[-1])
        _write(org / address / "AGENT.md", data, written)

    for item in entry["deliverables"]:
        target = deliverables / Path(str(item["file"])).name
        _write(target, _file(source / str(item["file"])).read_bytes(), written)
        pinned = utc_us(str(item["mtime"])) * 1000
        os.utime(target, ns=(pinned, pinned))
    if entry["team_files"]:
        index = source / str(entry["team_files"])
        for path in index_entries(index):
            version_file, _ = newest_version(index, path)
            _write(org / path, version_file.read_bytes(), written)
    return org


def md5_of(path: Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


__all__ = [
    "deliverable_folder", "index_entries", "log_block", "materialize", "md5_of", "message_files", "newest_version", "read_message",
    "utc_us",
]
