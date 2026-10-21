"""``OrgServicePlaces``: where the files of a service are (path arithmetic only)."""

from __future__ import annotations

from pathlib import Path

from hirearchy.kernel import OrgPaths
from hirearchy.services._places import OrgServicePlaces

ROOT = Path("/org")
PLACES = OrgServicePlaces(OrgPaths(ROOT))


def test_the_files_of_a_service_are_below_the_directory_of_its_owner() -> None:
    assert PLACES.services_dir("ceo/eng") == ROOT / "ceo/eng/services"
    assert PLACES.service_dir("ceo", "brief") == ROOT / "ceo/services/brief"
    assert PLACES.contract_file("ceo", "brief") == ROOT / "ceo/services/brief/SERVICE.md"
    assert PLACES.playbook_file("ceo", "brief") == ROOT / "ceo/services/brief/PLAYBOOK.md"


def test_the_kept_versions_are_in_history_named_by_kind_and_version() -> None:
    assert PLACES.history_file("ceo", "brief", "SERVICE", 3) == ROOT / "ceo/services/brief/history/SERVICE.v3.md"
    assert PLACES.history_file("ceo", "brief", "PLAYBOOK", 12) == ROOT / "ceo/services/brief/history/PLAYBOOK.v12.md"


def test_a_retired_service_is_under_a_hidden_directory_named_by_name_and_stamp() -> None:
    assert PLACES.retired_dir("ceo", "brief", "20260101T000000000001") == ROOT / "ceo/services/.retired/brief-20260101T000000000001"


def test_an_address_is_normalized_and_root_is_the_organization_itself() -> None:
    assert PLACES.services_dir("/ceo/") == ROOT / "ceo/services"
    assert PLACES.services_dir("root") == ROOT / "services"


def test_a_path_is_relative_to_the_organization() -> None:
    assert PLACES.rel(ROOT / "ceo/services/brief/SERVICE.md") == "ceo/services/brief/SERVICE.md"
