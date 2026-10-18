"""The in-memory fakes behave as their own documentation says (the shared behaviour is in the contract suites)."""

from __future__ import annotations

import pytest

from orgmcp.settings import DEFAULT_CONFIG, OrgDocumentStore, OrgSettings
from orgmcp.settings._stamp import OrgDocumentStamp
from orgmcp.settings.testing import MemoryOrgSettings
from orgmcp.settings.tests._red import red


def test_the_fake_is_the_settings_the_store_and_the_stamp() -> None:
    fake = MemoryOrgSettings()
    assert isinstance(fake, OrgSettings) and isinstance(fake, OrgDocumentStore) and isinstance(fake, OrgDocumentStamp)


@red
def test_a_fake_made_with_a_text_has_that_document() -> None:
    fake = MemoryOrgSettings("---\nmax_depth: 8\n---\nrules\n")
    assert fake.exists() and fake.config()["max_depth"] == 8 and fake.rules() == "rules"


@red
def test_a_fake_without_a_text_has_no_document() -> None:
    fake = MemoryOrgSettings()
    assert not fake.exists()
    with pytest.raises(OSError):
        fake.stamp()
    with pytest.raises(FileNotFoundError):
        fake.read_raw()


@red
def test_every_write_changes_the_stamp_unless_it_is_unnoticed() -> None:
    fake = MemoryOrgSettings("aaa")
    first = fake.stamp()
    fake.write_raw("bbb")
    second = fake.stamp()
    assert second != first and second[1] == 3
    fake.set_text("ccc", notice=False)
    assert fake.stamp() == second and fake.read_raw() == "ccc"
    fake.set_text("cc", notice=False)
    assert fake.stamp() != second  # the size is part of the stamp


@red
def test_the_fake_config_is_a_new_mapping_every_time() -> None:
    fake = MemoryOrgSettings("rules only")
    fake.config()["max_depth"] = 1
    assert fake.config() == DEFAULT_CONFIG
