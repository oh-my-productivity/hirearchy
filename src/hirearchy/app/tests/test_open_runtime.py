"""``open_runtime``: the runtime of one organization root, built from the ``wire_*`` modules, without touching the disk."""

from __future__ import annotations

import dataclasses
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hirearchy.app import wiring
from hirearchy.app.runtime import OrgRuntime
from hirearchy.kernel import Clock, OrgPaths
from hirearchy.kernel.testing import FakeClock


def test_the_wire_modules_are_discovered_and_sorted() -> None:
    names = wiring.wire_modules()
    assert "hirearchy.app.wire_kernel" in names and names == sorted(names)
    assert len(wiring.registrars()) == len(names)


def test_open_runtime_fills_every_field(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert runtime.root == tmp_path and runtime.paths == OrgPaths(tmp_path)
    assert all(getattr(runtime, f.name) is not None for f in dataclasses.fields(OrgRuntime))


def test_open_runtime_touches_nothing(tmp_path: Path) -> None:
    missing, empty = tmp_path / "nowhere", tmp_path / "empty"
    empty.mkdir()
    wiring.open_runtime(missing)
    wiring.open_runtime(empty)
    assert not missing.exists() and list(empty.iterdir()) == []


def test_the_runtime_is_frozen(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        runtime.root = tmp_path / "other"  # type: ignore[misc]


def test_two_runtimes_of_one_root_are_independent_objects_that_share_the_process_resources(tmp_path: Path) -> None:
    one, two = wiring.open_runtime(tmp_path), wiring.open_runtime(tmp_path)
    assert one.clock is not two.clock and one.ledgers is not two.ledgers and one.resources is two.resources


def test_an_override_replaces_a_port_for_everyone_who_needs_it(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    runtime = wiring.open_runtime(tmp_path, {Clock: clock})
    assert runtime.clock is clock
    assert runtime.ids.message_id("ceo/eng").startswith("20300102T030405") and "-ceo.eng-" in runtime.ids.message_id("ceo/eng")


def test_the_kernel_ports_read_and_write_the_files_the_org_methods_do(tmp_path: Path) -> None:
    from hirearchy.app import Org

    org = Org.init(tmp_path / "org", "mission")
    runtime = wiring.open_runtime(org.root)
    org.save_ledger("probe", {"a": 1})
    assert runtime.ledgers.read("probe") == {"a": 1} == org.ledger("probe")
    runtime.ledgers.write("probe", {"b": 2})
    assert org.ledger("probe") == {"b": 2}
    runtime.atomic_writer.write(org.root / "x" / "note.txt", "hi")
    assert (org.root / "x" / "note.txt").read_text(encoding="utf-8") == "hi"


def test_the_ids_have_the_format_of_org_new_id(tmp_path: Path) -> None:
    from hirearchy.app import Org

    org = Org.init(tmp_path / "org", "mission")
    pattern = r"\d{8}T\d{12}-ceo\.eng-[0-9a-f]{4}"
    assert re.fullmatch(pattern, wiring.open_runtime(org.root).ids.message_id("ceo/eng")) and re.fullmatch(pattern, org.new_id("ceo/eng"))
