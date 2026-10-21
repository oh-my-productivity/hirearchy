"""``OrgBinding``: the rules of ``create_org`` and every refusal text, on real directories (the organization itself is an in-memory set of directories)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import OrgError
from hirearchy.mcp_server._binding import OpenerBindings, OrgBinding
from hirearchy.mcp_server.testing import MemoryOrgOpener



def bound(root: Path | None, opener: MemoryOrgOpener | None = None, pinned: bool = False) -> tuple[OrgBinding, MemoryOrgOpener]:
    opener = opener or MemoryOrgOpener()
    return OrgBinding(root, opener, pinned=pinned), opener


def test_the_missing_message_says_what_to_do_for_each_state_of_the_path(tmp_path: Path) -> None:
    assert bound(None)[0].missing_message() == (
        "no organization found (ORG_ROOT is not set and none exists in the working directory): "
        "call create_org(mission=..., path=<absolute path>) first")
    free = tmp_path / "free"
    assert bound(free)[0].missing_message() == f"no organization at {free} yet: call create_org(mission=...) first"
    full = tmp_path / "full"
    full.mkdir()
    (full / "note.txt").write_text("x")
    assert bound(full)[0].missing_message() == (
        f"no organization at {full} yet: the directory exists, is not empty and has no ORG.md, so create_org will refuse to use it. "
        "Point ORG_ROOT at an empty or missing directory")
    (full / "note.txt").unlink()
    assert "call create_org(mission=...) first" in bound(full)[0].missing_message()  # an empty directory is fine


def test_a_file_in_the_way_blocks_the_path(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x")
    assert "is not empty and has no ORG.md" in bound(tmp_path / "f")[0].missing_message()


def test_finder_litter_does_not_make_a_directory_not_empty(tmp_path: Path) -> None:
    (tmp_path / ".DS_Store").write_text("x")
    binding, opener = bound(tmp_path)
    binding.create("A mission")
    assert opener.initialized == [(tmp_path, "A mission", None)]


def test_create_initializes_the_bound_path_with_the_stripped_mission_and_the_model(tmp_path: Path) -> None:
    binding, opener = bound(tmp_path / "org")
    ports = binding.create("  A mission  ", "a-model")
    assert opener.initialized == [(tmp_path / "org", "A mission", {"default_model": "a-model"})]
    assert ports.root == tmp_path / "org" and binding.location() == tmp_path / "org" and binding.root == tmp_path / "org"


def test_create_without_a_model_passes_no_config(tmp_path: Path) -> None:
    binding, opener = bound(tmp_path / "org")
    binding.create("A mission")
    assert opener.initialized[0][2] is None


def test_an_existing_organization_is_not_created_again(tmp_path: Path) -> None:
    binding, opener = bound(tmp_path, MemoryOrgOpener({tmp_path}))
    with pytest.raises(OrgError) as info:
        binding.create("A mission")
    assert str(info.value) == f"an organization already exists at {tmp_path}; nothing was created. It is ready to use: call whoami or status"
    assert opener.initialized == []


def test_the_mission_is_required(tmp_path: Path) -> None:
    for blank in ("", "  \n"):
        with pytest.raises(OrgError) as info:
            bound(tmp_path)[0].create(blank)
        assert str(info.value) == "mission is required: say in a few sentences what the organization is for"


def test_a_relative_path_is_refused(tmp_path: Path) -> None:
    with pytest.raises(OrgError) as info:
        bound(None)[0].create("m", None, "relative/org")
    assert str(info.value) == "path must be absolute (got 'relative/org')"


def test_a_bound_server_cannot_create_elsewhere(tmp_path: Path) -> None:
    other = (tmp_path / "other").resolve()
    binding, opener = bound(tmp_path / "org")
    with pytest.raises(OrgError) as info:
        binding.create("m", None, str(other))
    assert str(info.value) == (f"this server is bound to {tmp_path / 'org'} and cannot create an organization at {other}. "
                               "Omit path, or ask the user to register hirearchy with ORG_ROOT set to that path")
    assert opener.initialized == []
    binding.create("m", None, str((tmp_path / "org").resolve()))  # the same path is fine
    assert opener.initialized


def test_an_unbound_server_needs_a_path_and_binds_it_once(tmp_path: Path) -> None:
    binding, opener = bound(None)
    with pytest.raises(OrgError) as info:
        binding.create("m")
    assert str(info.value) == ("ORG_ROOT is not set and no organization was found here: "
                               "call create_org(mission=..., path=<absolute path>)")
    target = (tmp_path / "chosen").resolve()
    binding.create("m", None, str(target))
    assert binding.root == target and binding.location() == target
    with pytest.raises(OrgError, match="already exists"):
        binding.create("m", None, str(tmp_path / "another"))  # bound for its lifetime


def test_an_unbound_server_never_binds_an_organization_it_was_not_given(tmp_path: Path) -> None:
    target = (tmp_path / "there").resolve()
    target.mkdir()
    (target / "ORG.md").write_text("x")
    binding, opener = bound(None)
    with pytest.raises(OrgError) as info:
        binding.create("m", None, str(target))
    assert str(info.value) == (f"an organization already exists at {target}, but this server is not bound to it, so it will not be used. "
                               f"Ask the user to register hirearchy with ORG_ROOT={target}")
    assert binding.peek() is None and opener.initialized == []


def test_a_file_or_a_non_empty_directory_is_not_overwritten(tmp_path: Path) -> None:
    target = tmp_path / "file"
    target.write_text("x")
    with pytest.raises(OrgError) as info:
        bound(target)[0].create("m")
    assert str(info.value) == f"{target} is a file, not a directory; nothing was created"
    crowded = tmp_path / "crowded"
    crowded.mkdir()
    for name in "abcdefg":
        (crowded / name).write_text("x")
    with pytest.raises(OrgError) as info:
        bound(crowded)[0].create("m")
    assert str(info.value) == (f"{crowded} is not empty (a, b, c, d, e, ...) and is not an organization; nothing was created. "
                               "Use an empty or missing directory")


def test_a_write_failure_is_an_org_error_that_names_the_cause(tmp_path: Path) -> None:
    binding, opener = bound(tmp_path / "org")
    opener.fails = PermissionError("denied")
    with pytest.raises(OrgError) as info:
        binding.create("m")
    assert str(info.value) == f"could not create the organization at {tmp_path / 'org'}: denied"
    assert binding.peek() is None


def test_an_organization_made_by_someone_else_is_found_and_kept(tmp_path: Path) -> None:
    binding, opener = bound(tmp_path / "org")
    assert binding.peek() is None
    opener.organizations.add(tmp_path / "org")
    first = binding.peek()
    assert first is not None and binding.get() is first and opener.opened == 1  # opened once, then kept


def test_the_binding_may_be_given_the_organization_it_is_known_to_have(tmp_path: Path) -> None:
    opener = MemoryOrgOpener({tmp_path})
    ports = opener.open(tmp_path)
    binding = OrgBinding(tmp_path, opener, ports, pinned=True)
    assert binding.get() is ports and binding.pinned and opener.opened == 1


def test_the_bindings_of_a_process_share_their_opener(tmp_path: Path) -> None:
    opener = MemoryOrgOpener({tmp_path})
    binding = OpenerBindings(opener).bind(tmp_path, pinned=True)
    assert binding.pinned and binding.peek() is not None
