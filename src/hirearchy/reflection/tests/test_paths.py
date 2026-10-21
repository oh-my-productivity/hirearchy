"""``OrgServicePaths``: where the files of a service are, as the texts name them."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import OrgPaths
from hirearchy.reflection._files import OrgServicePaths
from hirearchy.reflection._ports import ServicePaths

ROOT = Path("/memory/org")


def test_it_is_a_service_paths() -> None:
    assert isinstance(OrgServicePaths(OrgPaths(ROOT)), ServicePaths)


def test_a_path_is_relative_to_the_organization() -> None:
    assert OrgServicePaths(OrgPaths(ROOT)).rel(ROOT / "ceo" / "services" / "brief" / "SERVICE.md") == "ceo/services/brief/SERVICE.md"


def test_no_path_is_no_text() -> None:
    assert OrgServicePaths(OrgPaths(ROOT)).rel(None) == ""


def test_the_directory_of_a_service_is_below_its_owner() -> None:
    assert OrgServicePaths(OrgPaths(ROOT)).service_dir("ceo/eng", "brief") == "ceo/eng/services/brief"


def test_the_playbook_file_is_in_the_directory_of_the_service() -> None:
    assert OrgServicePaths(OrgPaths(ROOT)).playbook_file("ceo", "brief") == "ceo/services/brief/PLAYBOOK.md"
