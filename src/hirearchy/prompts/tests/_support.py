"""Helpers shared by the tests of ``prompts`` (no test lives here)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from _pytest.mark.structures import ParameterSet

from hirearchy.mail import TaskQuery
from hirearchy.mail.testing import MemoryMailbox, memory_mailbox


def implementations(factories: Sequence[Callable[[Path], object]]) -> list[ParameterSet]:
    """The factories of one port as test parameters, named by the factory."""
    return [pytest.param(f, id=f.__name__) for f in factories]


def memory_box(tmp_path: Path) -> tuple[MemoryMailbox, TaskQuery]:
    """The mailboxes of an organization kept in memory (with its agents: ``box.agents``) and the task query over them."""
    harness = memory_mailbox(tmp_path)
    box = harness.reader
    assert isinstance(box, MemoryMailbox)
    return box, harness.tasks
