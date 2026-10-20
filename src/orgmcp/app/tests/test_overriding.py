"""The one seam for the process: ``wiring.overriding`` replaces ports of every runtime opened inside the block (ARCHITECTURE.md 6.4/7.4).

It is what the module-attribute patch points were (``core.utcnow``, ``core.atomic_write``, ``core.secrets``, ``telemetry.datetime``), made explicit: a
test that runs code which opens its own ``Org(root)`` / runtime (a CLI command, an MCP tool, the scheduler) gives it a fake clock or counting ids
through the composition root. ``open_runtime(root, overrides)`` stays the way to give one runtime its own fake; those win over the process ones.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orgmcp.app import Org, wiring
from orgmcp.eventlog import EVENTS_REL
from orgmcp.kernel import AtomicWriter, Clock, IdGenerator, Message, TokenSource
from orgmcp.kernel._system import FsAtomicWriter, SecretsTokens, SystemClock
from orgmcp.kernel.testing import CounterTokens, FakeClock, MemoryAtomicWriter

pytestmark = pytest.mark.xfail(strict=True, reason="red: E2-compat")

FIXED = datetime(2031, 5, 6, 7, 8, 9, tzinfo=timezone.utc)


class Fixed(SystemClock):
    def now(self) -> datetime:
        return FIXED


def test_a_runtime_opened_inside_the_block_gets_the_override(tmp_path: Path) -> None:
    clock = Fixed()
    with wiring.overriding({Clock: clock}):
        assert wiring.open_runtime(tmp_path).clock is clock
    assert wiring.open_runtime(tmp_path).clock is not clock


def test_the_override_is_gone_after_the_block_even_when_it_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError), wiring.overriding({Clock: Fixed()}):
        raise RuntimeError("boom")
    assert type(wiring.open_runtime(tmp_path).clock) is SystemClock


def test_an_explicit_override_wins_over_the_process_one(tmp_path: Path) -> None:
    mine = FakeClock()
    with wiring.overriding({Clock: Fixed()}):
        assert wiring.open_runtime(tmp_path, {Clock: mine}).clock is mine


def test_blocks_nest_and_the_inner_one_wins(tmp_path: Path) -> None:
    outer, inner = Fixed(), FakeClock()
    with wiring.overriding({Clock: outer, TokenSource: CounterTokens()}):
        with wiring.overriding({Clock: inner}):
            runtime = wiring.open_runtime(tmp_path)
            assert runtime.clock is inner and runtime.ids.message_id("a").endswith("-0000")  # the outer block's tokens stay
        assert wiring.open_runtime(tmp_path).clock is outer


def test_code_that_opens_its_own_org_sees_the_override(tmp_path: Path) -> None:
    with wiring.overriding({Clock: Fixed(), TokenSource: CounterTokens(per_length=True)}):
        org = Org.init(tmp_path / "org", "mission")
        assert org.new_id("ceo") == "20310506T070809000000-ceo-0000"
        assert org.new_id("ceo") == "20310506T070809000000-ceo-0001"


def test_message_ids_come_from_the_token_source(tmp_path: Path) -> None:
    with wiring.overriding({TokenSource: CounterTokens(per_length=True)}):
        ids = wiring.open_runtime(tmp_path).ids
        assert [ids.message_id("a")[-4:], ids.message_id("a")[-4:]] == ["0000", "0001"]


def test_the_atomic_writer_names_its_temp_files_with_the_token_source(tmp_path: Path) -> None:
    tokens = CounterTokens(per_length=True)
    with wiring.overriding({TokenSource: tokens}):
        wiring.open_runtime(tmp_path).atomic_writer.write(tmp_path / "a.txt", "one")
    assert tokens.counts == {4: 1}  # one temp name of four bytes


def test_the_events_are_stamped_by_the_clock_port(tmp_path: Path) -> None:
    with wiring.overriding({Clock: Fixed()}):
        org = Org.init(tmp_path / "org", "mission")
        org.emit("custom.kind")
    stamps = [json.loads(line)["ts"] for f in (org.root / EVENTS_REL).glob("*/*.jsonl") for line in f.read_text(encoding="utf-8").splitlines()]
    assert "2031-05-06T07:08:09.000000+00:00" in stamps


def test_a_plain_runtime_wires_the_system_adapters(tmp_path: Path) -> None:
    runtime = wiring.open_runtime(tmp_path)
    assert type(runtime.clock) is SystemClock and type(runtime.atomic_writer) is FsAtomicWriter
    assert isinstance(runtime.ids, IdGenerator) and isinstance(runtime.atomic_writer, AtomicWriter)
    assert type(wiring.open_runtime(tmp_path, {AtomicWriter: MemoryAtomicWriter()}).atomic_writer) is MemoryAtomicWriter


def test_one_shared_counter_serves_ids_and_temp_names_in_order(tmp_path: Path) -> None:
    tokens = CounterTokens()
    with wiring.overriding({TokenSource: tokens}):
        runtime = wiring.open_runtime(tmp_path)
        runtime.atomic_writer.write(tmp_path / "a.txt", "one")
        assert runtime.ids.message_id("a").endswith("-0001")  # the temp name took 0000: that is how the scenarios number their ids


def test_the_real_token_source_is_secrets() -> None:
    assert len(SecretsTokens().token_hex(4)) == 8


def test_the_patch_point_layer_is_gone() -> None:
    assert importlib.util.find_spec("orgmcp.app._compat") is None
    assert "load" not in vars(Message)
