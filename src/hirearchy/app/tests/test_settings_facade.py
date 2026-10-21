"""The settings slice of the ``Org`` facade: ``config``, ``rules`` and ``find_root`` behave as they always did, and now go through
the runtime's ports."""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import pytest
import yaml

from hirearchy.app import Org
from hirearchy.kernel import OrgError
from hirearchy.settings import DEFAULT_CONFIG, DEFAULT_MODEL
from hirearchy.settings.testing import MemoryOrgSettings

DOCUMENTS = [
    ("---\nmax_depth: 7\nflavour: mint\n---\n# Mission\n\nStudy octopuses.\n\n", {"max_depth": 7, "flavour": "mint"}, "# Mission\n\nStudy octopuses."),
    ("no frontmatter\n", {}, "no frontmatter"),
    ("---\n- a\n---\nbody\n", {}, "body"),
    ("---\r\nmax_depth: 2\r\n---\r\nbody\r\n", {"max_depth": 2}, "body"),
    ("---\ndefault_model:\nevents: false\n---\n", {"default_model": None, "events": False}, ""),
]


@pytest.fixture
def org(tmp_path: Path) -> Org:
    return Org.init(tmp_path / "org", "mission")


@pytest.mark.parametrize("text, meta, rules", DOCUMENTS, ids=range(len(DOCUMENTS)))
def test_config_and_rules_of_a_document(org: Org, text: str, meta: dict[str, object], rules: str) -> None:
    (org.root / "ORG.md").write_bytes(text.encode("utf-8"))
    assert org.config == {**DEFAULT_CONFIG, **meta}
    assert org.rules() == rules


def test_config_is_a_new_dict_every_time(org: Org) -> None:
    first = org.config
    first["max_depth"] = 99
    assert org.config["max_depth"] == DEFAULT_CONFIG["max_depth"] and org.config is not org.config


def test_a_new_org_has_the_defaults_and_its_rules(org: Org) -> None:
    assert org.config["default_model"] == DEFAULT_MODEL and org.config["max_depth"] == 4
    assert org.rules().startswith("# Organization\n\n## Mission\nmission\n")


def test_a_missing_or_broken_document_is_an_error_like_before(org: Org) -> None:
    (org.root / "ORG.md").write_text("---\nkey: [unclosed\n---\nbody\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        org.config
    (org.root / "ORG.md").unlink()
    with pytest.raises(FileNotFoundError):
        org.config
    with pytest.raises(FileNotFoundError):
        org.rules()


def test_find_root_accepts_text_paths_and_nothing(org: Org, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORG_ROOT", raising=False)
    work = org.root / "ceo" / "work"
    work.mkdir(parents=True)
    assert Org.find_root(work) == org.root and Org.find_root(str(work)) == org.root
    monkeypatch.chdir(work)
    assert Org.find_root() == org.root and Org.find_root("") == org.root and Org.find_root(None) == org.root


def test_find_root_prefers_ORG_ROOT_and_expands_it(org: Org, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("ORG_ROOT", "~/somewhere/else")
    assert Org.find_root(org.root) == (tmp_path / "somewhere" / "else").resolve()


def test_find_root_in_a_directory_that_holds_org(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORG_ROOT", raising=False)
    Org.init(tmp_path / "project" / "org", "m")
    assert Org.find_root(tmp_path / "project") == (tmp_path / "project" / "org").resolve()
    with pytest.raises(OrgError, match="^no organization found: set ORG_ROOT or run inside an org directory$"):
        Org.find_root(tmp_path)


def test_find_root_is_a_static_method() -> None:
    assert isinstance(inspect.getattr_static(Org, "find_root"), staticmethod)


def test_config_and_rules_come_from_the_settings_port_of_the_runtime(org: Org) -> None:
    org.runtime = dataclasses.replace(org.runtime, settings=MemoryOrgSettings("---\nmax_depth: 8\n---\nfrom the fake\n"))
    assert org.config["max_depth"] == 8 and org.rules() == "from the fake"

