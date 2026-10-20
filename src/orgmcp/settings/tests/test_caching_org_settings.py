"""``CachingOrgSettings``: the settings parsed once per change of ORG.md; a broken ORG.md means the defaults, reported."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from orgmcp.kernel import JsonObject, OrgPaths
from orgmcp.kernel.testing import fs_atomic_writer
from orgmcp.settings import DEFAULT_CONFIG, OrgSettings
from orgmcp.settings._caching import CachingOrgSettings
from orgmcp.settings._fs import FsOrgSettings
from orgmcp.settings._stamp import FsOrgDocumentStamp, OrgDocumentStamp
from orgmcp.settings.tests._reach import reach
from orgmcp.settings.tests._oracle import LenientConfig


class ScriptedStamp(OrgDocumentStamp):
    def __init__(self) -> None:
        self.value: tuple[int, int] | OSError = (1, 10)

    def stamp(self) -> tuple[int, int]:
        if isinstance(self.value, OSError):
            raise self.value
        return self.value


class ScriptedSettings(OrgSettings):
    """Answers with whatever is scripted and counts the reads."""

    def __init__(self) -> None:
        self.answer: JsonObject | Exception = {**DEFAULT_CONFIG, "max_depth": 2}
        self.reads = 0
        self.rules_text: str | Exception = "the rules"

    def config(self) -> JsonObject:
        self.reads += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer

    def rules(self) -> str:
        if isinstance(self.rules_text, Exception):
            raise self.rules_text
        return self.rules_text

    def default_model(self) -> str:
        raise AssertionError("derived from the cached config")

    def number(self, key: str, kind: type[float] | type[int] = float) -> float:
        raise AssertionError("derived from the cached config")

    def message_cap(self) -> int:
        raise AssertionError("derived from the cached config")


def make() -> tuple[CachingOrgSettings, ScriptedSettings, ScriptedStamp, dict[str, str]]:
    inner, stamp, problems = ScriptedSettings(), ScriptedStamp(), dict[str, str]()
    return CachingOrgSettings(inner, stamp, problems), inner, stamp, problems


def test_it_is_org_settings() -> None:
    assert isinstance(make()[0], OrgSettings)


def test_building_it_reads_nothing() -> None:
    _, inner, _, problems = make()
    assert inner.reads == 0 and problems == {}


def test_the_config_is_read_once_per_stamp_and_the_cached_mapping_is_handed_out() -> None:
    caching, inner, stamp, _ = make()
    first = caching.config()
    assert first["max_depth"] == 2 and caching.config() is first and caching.config() is first
    assert inner.reads == 1
    stamp.value = (2, 10)
    inner.answer = {**DEFAULT_CONFIG, "max_depth": 3}
    assert caching.config()["max_depth"] == 3 and inner.reads == 2


def test_a_failing_read_means_the_defaults_and_is_reported_by_the_name_of_the_error() -> None:
    caching, inner, stamp, problems = make()
    inner.answer = ValueError("mapping values are not allowed here")
    stamp.value = (3, 10)
    got = caching.config()
    assert got == DEFAULT_CONFIG and got is not DEFAULT_CONFIG
    assert problems == {"ORG.md": "ValueError"}


def test_a_missing_document_means_the_defaults_and_is_reported() -> None:
    caching, inner, stamp, problems = make()
    stamp.value = FileNotFoundError("ORG.md")
    assert caching.config() == DEFAULT_CONFIG
    assert problems == {"ORG.md": "FileNotFoundError"}
    assert inner.reads == 0


def test_a_document_that_recovers_is_no_longer_reported() -> None:
    caching, inner, stamp, problems = make()
    stamp.value = PermissionError("ORG.md")
    caching.config()
    assert problems == {"ORG.md": "PermissionError"}
    stamp.value = (4, 10)
    assert caching.config()["max_depth"] == 2
    assert problems == {}


def test_other_problems_in_the_mapping_are_left_alone() -> None:
    caching, _, stamp, problems = make()
    problems["x/AGENT.md"] = "ScannerError"
    caching.config()
    stamp.value = OSError("gone")
    caching.config()
    stamp.value = (5, 10)
    caching.config()
    assert problems == {"x/AGENT.md": "ScannerError"}


def test_a_failure_is_read_again_at_the_next_stamp_and_not_cached_as_a_success() -> None:
    caching, inner, stamp, problems = make()
    inner.answer = RuntimeError("boom")
    stamp.value = (6, 10)
    caching.config()
    caching.config()
    assert inner.reads == 2 and problems == {"ORG.md": "RuntimeError"}  # nothing was cached: it tries again


def test_the_rest_is_derived_from_the_cached_config() -> None:
    caching, inner, _, _ = make()
    inner.answer = {**DEFAULT_CONFIG, "default_model": " m9 ", "max_message_chars": "77", "poll_seconds": "0.25"}
    assert caching.default_model() == "m9"
    assert caching.message_cap() == 77
    assert caching.number("poll_seconds") == 0.25
    assert caching.number("max_parallel", int) == 3
    assert inner.reads == 1


def test_the_rules_are_not_cached_and_not_lenient() -> None:
    caching, inner, _, _ = make()
    assert caching.rules() == "the rules"
    inner.rules_text = "new rules"
    assert caching.rules() == "new rules"
    inner.rules_text = FileNotFoundError("ORG.md")
    with pytest.raises(FileNotFoundError):
        caching.rules()


def test_it_does_what_the_lenient_org_of_the_dashboard_did(tmp_path: Path) -> None:
    """Characterization: the same document gives the same config and the same ``bad`` entry as ``LenientOrg.config`` (frozen in ``_oracle.LenientConfig``)."""
    org = reach("core").Org.init(tmp_path / "org", "mission", {"max_depth": 3})
    lenient = LenientConfig(org.root)
    paths = OrgPaths(org.root)
    problems: dict[str, str] = {}
    caching = CachingOrgSettings(FsOrgSettings(paths, fs_atomic_writer(tmp_path).writer), FsOrgDocumentStamp(paths), problems)
    documents = [
        (org.root / "ORG.md").read_text(encoding="utf-8"),
        "---\nmax_depth: 9\nevents: false\n---\nbody\n",
        "---\nkey: [unclosed\n---\nbody\n",
        "no frontmatter at all\n",
        "---\n- just\n- a list\n---\nbody\n",
        "---\nmax_depth: 5\n---\nbody ok again\n",
    ]
    for n, text in enumerate(documents):
        (org.root / "ORG.md").write_text(text, encoding="utf-8")
        os.utime(org.root / "ORG.md", ns=(n + 1, 1_700_000_000_000_000_000 + n * 1_000_000))
        assert caching.config() == lenient.config, text
        assert {k: v for k, v in problems.items()} == {k: v for k, v in lenient.bad.items() if k == "ORG.md"}, text
    (org.root / "ORG.md").unlink()
    assert caching.config() == lenient.config == DEFAULT_CONFIG
    assert problems == {"ORG.md": "FileNotFoundError"} == {k: v for k, v in lenient.bad.items() if k == "ORG.md"}
