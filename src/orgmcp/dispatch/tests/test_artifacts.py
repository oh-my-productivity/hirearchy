"""``ArtifactAnnotator``: an artifact of a report is inside the organization or, by absolute path, inside the reporter's own workspace, and is
shown with facts a manager can check a claim against. Over files on disk."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from orgmcp.dispatch._artifacts import ArtifactAnnotator
from orgmcp.dispatch.testing import DispatchWorld, fs_world
from orgmcp.kernel import OrgError, OrgPaths

from ._support import populated


class Place:
    """The organization on disk with a ``ceo`` that has a workspace, an ``eng`` below it that has another, and a ``free`` agent without one."""

    def __init__(self, tmp_path: Path) -> None:
        (tmp_path / "org").mkdir()
        self.world: DispatchWorld = populated(fs_world(tmp_path / "org"))
        self.root = (tmp_path / "org").resolve()
        self.outside = tmp_path / "outside"
        self.proj = tmp_path / "proj"
        self.elsewhere = tmp_path / "elsewhere"
        for directory in (self.outside, self.proj / "out", self.elsewhere):
            directory.mkdir(parents=True)
        self.world.put_agent("ceo", {"role": "Lead", "can_hire": True, "workspace": str(self.proj)})
        self.world.put_agent("ceo/eng", {"role": "Worker", "workspace": str(self.elsewhere)})
        self.annotator = ArtifactAnnotator(OrgPaths(self.root), self.world.scopes)

    def normalize(self, actor: str, path: str, since: str = "") -> str:
        return self.annotator.normalize(actor, path, since)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


@pytest.fixture
def place(tmp_path: Path) -> Place:
    return Place(tmp_path)


# ------------------------------------------------------------------------------ inside the organization


def test_a_file_of_the_organization_is_shown_relative_to_its_root_with_its_words(place: Place) -> None:
    place.write("ceo/work/x.md", "a b c")
    assert re.fullmatch(r"ceo/work/x\.md \(3 words, modified \d\d:\d\d:\d\d UTC\)", place.normalize("ceo", "ceo/work/x.md"))


def test_an_absolute_path_inside_the_organization_is_shown_relative_too(place: Place) -> None:
    path = place.write("ceo/work/x.md", "a b c")
    assert place.normalize("ceo", str(path)).startswith("ceo/work/x.md (3 words")


def test_a_relative_path_is_read_from_the_root_of_the_organization_then_from_the_directory_of_the_reporter(place: Place) -> None:
    place.write("work/x.md", "one")
    place.write("ceo/work/x.md", "one two")
    place.write("ceo/only.md", "one two three")
    assert place.normalize("ceo", "work/x.md").startswith("work/x.md (1 words")  # the organization first
    assert place.normalize("ceo", "only.md").startswith("ceo/only.md (3 words")  # then the reporter's own directory


def test_a_directory_is_shown_with_a_slash(place: Place) -> None:
    place.write("ceo/work/x.md", "x")
    assert place.normalize("ceo", "ceo/work") == "ceo/work/ (directory)"


def test_the_word_count_is_that_of_the_text_without_markup(place: Place) -> None:
    place.write("ceo/work/x.md", "# Title\none two three four five\n")
    assert "(6 words" in place.normalize("ceo", "ceo/work/x.md")


def test_the_organization_itself_is_an_artifact(place: Place) -> None:
    assert place.normalize("ceo", ".") == "./ (directory)"


# ------------------------------------------------------------------------------ not modified since the task


def test_a_file_older_than_the_task_says_so(place: Place) -> None:
    path = place.write("ceo/work/old.md", "old")
    os.utime(path, (1_000_000_000, 1_000_000_000))
    note = place.normalize("ceo", "ceo/work/old.md", "2026-01-01T00:00:00+00:00")
    assert note.endswith(", NOT modified since this task was assigned)")


def test_a_file_newer_than_the_task_does_not(place: Place) -> None:
    path = place.write("ceo/work/new.md", "new")
    os.utime(path, (2_000_000_000, 2_000_000_000))
    assert "NOT modified" not in place.normalize("ceo", "ceo/work/new.md", "2026-01-01T00:00:00+00:00")


def test_without_a_creation_time_of_the_task_nothing_is_compared(place: Place) -> None:
    path = place.write("ceo/work/old.md", "old")
    os.utime(path, (1_000_000_000, 1_000_000_000))
    assert "NOT modified" not in place.normalize("ceo", "ceo/work/old.md")


# ------------------------------------------------------------------------------ the workspace of the reporter


def test_an_absolute_path_in_the_own_workspace_is_shown_as_given(place: Place) -> None:
    f = place.proj / "guide.md"
    f.write_text("# Title\none two three four five\n")
    assert place.normalize("ceo", str(f)).startswith(f"{f} (6 words, modified ")
    assert place.normalize("ceo", str(place.proj)) == f"{place.proj}/ (directory)"


def test_a_file_in_a_subfolder_of_the_workspace_is_accepted(place: Place) -> None:
    f = place.proj / "out" / "w.md"
    f.write_text("x y")
    assert place.normalize("ceo", str(f)).startswith(f"{f} (2 words")


def test_a_workspace_file_older_than_the_task_says_so(place: Place) -> None:
    f = place.proj / "old.md"
    f.write_text("old")
    os.utime(f, (1_000_000_000, 1_000_000_000))
    assert "NOT modified since this task was assigned" in place.normalize("ceo", str(f), "2026-01-01T00:00:00+00:00")


REFUSED = "artifacts must be inside the organization (paths relative to the org root) or, by absolute path, inside your workspace ({ws}): {path}"


def test_everything_else_outside_the_organization_is_refused(place: Place) -> None:
    for target in (place.elsewhere / "f.md", place.outside / "f.md"):  # another agent's workspace, anywhere else
        target.write_text("x")
        with pytest.raises(OrgError) as e:
            place.normalize("ceo", str(target))
        assert str(e.value) == REFUSED.format(ws=place.proj, path=target)


def test_the_workspace_of_a_manager_is_not_the_reporters(place: Place) -> None:
    (place.proj / "m.md").write_text("x")
    with pytest.raises(OrgError, match="artifacts must be inside the organization"):
        place.normalize("ceo/eng", str(place.proj / "m.md"))


def test_the_refusal_does_not_say_whether_the_file_exists(place: Place) -> None:
    for p in ("/etc/passwd", "/etc/nope-xxxxxxxx", str(place.elsewhere / "missing.md")):
        with pytest.raises(OrgError, match="artifacts must be inside the organization"):
            place.normalize("ceo", p)


def test_an_agent_without_a_workspace_is_told_so(place: Place) -> None:
    f = place.proj / "f.md"
    f.write_text("x")
    with pytest.raises(OrgError) as e:
        place.normalize("ceo/qa", str(f))
    assert str(e.value) == f"artifacts must be inside the organization (paths relative to the org root) or, by absolute path, (you have no workspace): {f}"


def test_a_symlink_that_leaves_the_workspace_is_refused(place: Place) -> None:
    secret = place.elsewhere / "secret.md"
    secret.write_text("s")
    (place.proj / "escape.md").symlink_to(secret)
    with pytest.raises(OrgError, match="artifacts must be inside"):
        place.normalize("ceo", str(place.proj / "escape.md"))


# ------------------------------------------------------------------------------ a file that is not there


def test_a_missing_file_inside_the_organization_is_not_found(place: Place) -> None:
    with pytest.raises(OrgError) as e:
        place.normalize("ceo", "ceo/work/nope.md")
    assert str(e.value) == "artifact not found: ceo/work/nope.md (relative paths are relative to the org root)."


def test_a_missing_file_in_the_workspace_is_not_found(place: Place) -> None:
    missing = place.proj / "nope.md"
    with pytest.raises(OrgError) as e:
        place.normalize("ceo", str(missing))
    assert str(e.value) == f"artifact not found: {missing} (relative paths are relative to the org root)."


def test_a_relative_path_that_exists_in_the_workspace_points_at_it(place: Place) -> None:
    (place.proj / "ceo" / "work").mkdir(parents=True)
    (place.proj / "ceo" / "work" / "x.md").write_text("misplaced")
    with pytest.raises(OrgError) as e:
        place.normalize("ceo", "ceo/work/x.md")
    assert str(e.value) == (
        "artifact not found: ceo/work/x.md (relative paths are relative to the org root)."
        f" It exists in your workspace: report it by absolute path ({(place.proj / 'ceo' / 'work' / 'x.md').resolve()})."
    )
