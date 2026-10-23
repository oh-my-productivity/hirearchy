"""Contract of ``JudgedVersions``: for a rework of a request, the delivery the client judged and what relayed reworks changed after it (P4, design 7.2).

Every implementation answers for the service ``weekly-brief`` of ``ceo``. What the callers rely on: ``None`` for a task that is in no case and when nothing
needs a base; otherwise a ``JudgedBase`` that names the judged task and result, the relayed reworks sent after it and the artifacts that differ now, with
the judged text of some of them (in the order of ``changed``, at most ``JUDGED_BYTES`` bytes in all). The real one (``reflection.CaseJudgedVersions``) runs
this suite too, over a world with cases: ``reflection/tests/test_case_judged_versions.py``."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.services import JUDGED_BYTES, JudgedBase, JudgedVersions
from hirearchy.services.testing import IMPLEMENTATIONS, JUDGED_TASK

from ._support import implementations

OWNER, SERVICE = "ceo", "weekly-brief"


@pytest.fixture(params=implementations(IMPLEMENTATIONS[JudgedVersions]))
def judged(request: pytest.FixtureRequest, tmp_path: Path) -> JudgedVersions:
    made = request.param(tmp_path)
    assert isinstance(made, JudgedVersions)
    return made


def test_a_task_that_is_in_no_case_needs_no_base(judged: JudgedVersions) -> None:
    assert judged.base(OWNER, SERVICE, "20200101T000000000001-root-0000") is None


def test_the_answer_is_none_or_a_well_formed_base(judged: JudgedVersions) -> None:
    got = judged.base(OWNER, SERVICE, JUDGED_TASK)
    if got is None:
        return
    assert isinstance(got, JudgedBase)
    assert got.task and got.result and got.relayed and got.changed
    assert all(r > got.result for r in got.relayed)  # relayed reworks were sent after the judged delivery
    assert len(set(got.changed)) == len(got.changed)


def test_the_judged_texts_are_those_of_changed_paths_in_their_order_within_the_limit(judged: JudgedVersions) -> None:
    got = judged.base(OWNER, SERVICE, JUDGED_TASK)
    if got is None:
        return
    paths = [path for path, _ in got.texts]
    assert paths == [p for p in got.changed if p in paths]
    assert sum(len(text.encode("utf-8")) for _, text in got.texts) <= JUDGED_BYTES


def test_the_answer_is_the_same_every_time(judged: JudgedVersions) -> None:
    assert judged.base(OWNER, SERVICE, JUDGED_TASK) == judged.base(OWNER, SERVICE, JUDGED_TASK)
