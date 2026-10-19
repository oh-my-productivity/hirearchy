"""A parent rewriting a report's charter does not strip its frontmatter.

Every key of the old frontmatter that the new text does not set is kept (a key the new text sets, even to an empty value, wins); the
authority checks run on the MERGED frontmatter; and the writer gets a note saying which keys were kept, changed or added. Root edits a
charter as it is. Runs over both implementations."""

from __future__ import annotations

from pathlib import Path

import json

import pytest

from orgmcp.kernel import JsonObject, OrgError, join_frontmatter, split_frontmatter
from orgmcp.orgfiles import OrgFileWriter
from orgmcp.orgfiles.testing import IMPLEMENTATIONS, OrgFilesHarness

from ._support import make, refusal, written


REPORT = "lead/rev"
APPEND_NOTE = "A key you leave out is kept; to remove one, set it explicitly (e.g. `tools: []`)."


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    """root -> lead (a manager: read and shell, inputs ``notes``) -> rev (read, ``notes``, a model, and the bookkeeping keys)."""
    made = make(request, tmp_path)
    assert isinstance(made.writer, OrgFileWriter)
    notes = str(made.outside / "notes")
    made.add_agent("lead", {"role": "Lead", "tools": ["read", "shell"], "inputs": [notes], "can_hire": True})
    made.add_agent(
        REPORT,
        {"role": "Reviewer", "tools": ["read"], "model": "m-1", "inputs": [notes], "can_hire": False, "max_children": 5,
         "hired_by": "lead", "created": "2026-01-01"},
    )
    return made


def text(role: str, body: str = "New body.", **extra: object) -> str:
    meta: JsonObject = {"role": role, **extra}
    return join_frontmatter(meta, body)


def charter(h: OrgFilesHarness, addr: str = REPORT) -> JsonObject:
    meta, _ = split_frontmatter(written(h, *addr.split("/"), "AGENT.md") or "")
    return meta


# ------------------------------------------------------------------------------ the merge


def test_a_rewrite_with_only_a_role_keeps_every_other_key(h: OrgFilesHarness) -> None:
    before = charter(h)
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: Sharper reviewer\n---\n# Role\nNew body.\n")
    after = charter(h)
    assert after["role"] == "Sharper reviewer"
    assert {k: v for k, v in after.items() if k != "role"} == {k: v for k, v in before.items() if k != "role"}


def test_the_merged_charter_is_the_new_keys_first_then_the_kept_ones_and_the_new_body(h: OrgFilesHarness) -> None:
    old = charter(h)
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: Sharper\nmax_children: 2\n---\n# Role\nNew body.\n\n\n")
    expected = join_frontmatter({"role": "Sharper", "max_children": 2, **{k: v for k, v in old.items() if k not in ("role", "max_children")}}, "# Role\nNew body.")
    assert written(h, "lead", "rev", "AGENT.md") == expected


def test_a_key_set_explicitly_wins_even_when_empty(h: OrgFilesHarness) -> None:
    h.writer.write("lead", f"{REPORT}/AGENT.md", text("Reviewer", tools=[], model="m-2"))
    after = charter(h)
    assert after["tools"] == [] and after["model"] == "m-2"
    assert after["inputs"] == [str(h.outside / "notes")]  # not in the new text: kept


def test_a_null_or_blank_value_wins_too(h: OrgFilesHarness) -> None:
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: Reviewer\nmodel:\nhired_by: ''\n---\nbody\n")
    after = charter(h)
    assert after["model"] is None and after["hired_by"] == "" and after["tools"] == ["read"]


def test_a_text_that_sets_every_key_is_written_as_it_is(h: OrgFilesHarness) -> None:
    keys = charter(h)
    given = "---\n" + json.dumps({**keys, "role": "Everything"}) + "\n---\nBody   \n\n\n"  # JSON is YAML in flow style
    h.writer.write("lead", f"{REPORT}/AGENT.md", given)
    assert written(h, "lead", "rev", "AGENT.md") == given


def test_the_body_is_the_new_text_and_the_old_one_is_gone(h: OrgFilesHarness) -> None:
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: R2\n---\nthe new body only\n")
    assert split_frontmatter(written(h, "lead", "rev", "AGENT.md") or "")[1] == "the new body only\n"


def test_a_charter_needs_a_role(h: OrgFilesHarness) -> None:
    gone = "a charter needs YAML frontmatter with at least `role:`"
    for given in ("no frontmatter at all", "---\ntools: [read]\n---\nbody\n", "---\nrole: ''\n---\nbody\n", "---\nrole:\n---\nbody\n", ""):
        assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", given)) == gone
    assert charter(h)["role"] == "Reviewer"


def test_an_append_to_a_charter_adds_text_and_is_not_merged(h: OrgFilesHarness) -> None:
    old = written(h, "lead", "rev", "AGENT.md")
    chunk = "---\nrole: More\n---\nadded"
    path, note = h.writer.write_noted("lead", f"{REPORT}/AGENT.md", chunk, append=True)
    assert path == h.root / "lead" / "rev" / "AGENT.md" and note == "" and written(h, "lead", "rev", "AGENT.md") == (old or "") + chunk


# ------------------------------------------------------------------------------ the note for the writer


def test_the_note_lists_what_was_kept_changed_and_added(h: OrgFilesHarness) -> None:
    path, note = h.writer.write_noted("lead", f"{REPORT}/AGENT.md", text("Sharper", tools=["read"], max_children=2, extra="x"))
    assert path == h.root / "lead" / "rev" / "AGENT.md"
    assert note == (
        "charter frontmatter of `lead/rev`: kept from the old frontmatter (not in your text): model, inputs, can_hire, hired_by, created. "
        "changed (old -> new): role: Reviewer -> Sharper; max_children: 5 -> 2. added: extra: x. " + APPEND_NOTE
    )


def test_the_note_when_nothing_is_kept_and_nothing_changes(h: OrgFilesHarness) -> None:
    every = {k: v for k, v in charter(h).items() if k != "role"}
    _, note = h.writer.write_noted("lead", f"{REPORT}/AGENT.md", join_frontmatter({"role": "Reviewer", **every}, "New body."))
    assert note == "charter frontmatter of `lead/rev`: nothing kept from the old frontmatter (your text set every key). no key changed. " + APPEND_NOTE


def test_the_note_shows_an_emptied_key_and_clips_long_values(h: OrgFilesHarness) -> None:
    _, note = h.writer.write_noted("lead", f"{REPORT}/AGENT.md", text("Reviewer", tools=[], model="m" * 200))
    assert "tools: [read] -> []" in note
    assert f"model: m-1 -> {'m' * 79}…" in note


def test_the_note_names_the_agent_by_its_path_in_the_organization(h: OrgFilesHarness) -> None:
    h.add_agent("lead/rev/sub", {"role": "Sub"})
    assert h.writer.write_noted("lead/rev", "lead/rev/sub/AGENT.md", text("Sub 2"), append=False)[1].startswith(
        "charter frontmatter of `lead/rev/sub`: "
    )


# ------------------------------------------------------------------------------ authority on the merged frontmatter


def test_inputs_outside_the_managers_own_are_refused_and_nothing_is_written(h: OrgFilesHarness) -> None:
    before = written(h, "lead", "rev", "AGENT.md")
    said = refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", text("Reviewer", inputs=[str(h.outside / "elsewhere")])))
    assert said.startswith("a report's inputs must be inside your inputs or workspace (") and said.endswith(f"): {h.outside / 'elsewhere'}")
    assert written(h, "lead", "rev", "AGENT.md") == before


def test_a_tool_the_manager_lacks_is_refused_when_set_explicitly(h: OrgFilesHarness) -> None:
    before = written(h, "lead", "rev", "AGENT.md")
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", text("Reviewer", tools=["read", "write"]))) == (
        "you cannot grant tools you do not have yourself: write"
    )
    assert written(h, "lead", "rev", "AGENT.md") == before


def test_a_kept_key_is_judged_as_well_as_a_new_one(h: OrgFilesHarness) -> None:
    """Authority is checked on the merged frontmatter: a tool kept from the old charter that the manager does not hold is refused."""
    h.put(h.root / "lead" / "rev" / "AGENT.md", join_frontmatter({"role": "Reviewer", "tools": ["web"], "inputs": []}, "old"))
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: R2\n---\nnew\n")) == (
        "you cannot grant tools you do not have yourself: web"
    )
    assert "R2" not in (written(h, "lead", "rev", "AGENT.md") or "")


def test_a_legacy_charter_cannot_be_rewritten_by_a_confined_manager(h: OrgFilesHarness) -> None:
    """Read, no workspace and no ``inputs`` key merges to an unconfined read, which a manager confined to its inputs cannot hand down."""
    h.put(h.root / "lead" / "rev" / "AGENT.md", join_frontmatter({"role": "R", "tools": ["read"]}, "x"))
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: R2\n---\nnew\n")) == (
        "a charter with `read` and no workspace needs an `inputs:` list (it may be empty), otherwise its built-in read is "
        "not confined to the workspace and inputs you have yourself"
    )
    assert "R2" not in (written(h, "lead", "rev", "AGENT.md") or "")
    h.writer.write("lead", f"{REPORT}/AGENT.md", "---\nrole: R2\ninputs: []\n---\nnew\n")  # an explicit (even empty) list is confined
    assert charter(h)["inputs"] == [] and charter(h)["role"] == "R2"


def test_a_manager_that_is_itself_unconfined_may_hand_down_an_unconfined_read(h: OrgFilesHarness) -> None:
    h.add_agent("old", {"role": "Old", "tools": ["read"]})
    h.add_agent("old/kid", {"role": "Kid", "tools": ["read"]})
    h.writer.write("old", "old/kid/AGENT.md", "---\nrole: Kid 2\n---\nnew\n")
    assert charter(h, "old/kid")["role"] == "Kid 2" and charter(h, "old/kid")["tools"] == ["read"]


def test_a_workspace_outside_the_managers_is_refused(h: OrgFilesHarness) -> None:
    h.add_agent("wm", {"role": "WM", "tools": ["read"], "workspace": str(h.outside / "ws-wm"), "inputs": []})
    h.add_agent("wm/kid", {"role": "Kid"})
    h.writer.write("wm", "wm/kid/AGENT.md", text("Kid", workspace=str(h.outside / "ws-wm" / "kid")))
    assert refusal(lambda: h.writer.write("wm", "wm/kid/AGENT.md", text("Kid", workspace=str(h.outside / "ws-other")))) == (
        f"a report's workspace must be inside yours ({h.outside / 'ws-wm'})"
    )


def test_the_checks_run_after_the_role_check_and_before_anything_is_written(h: OrgFilesHarness) -> None:
    before = written(h, "lead", "rev", "AGENT.md")
    assert refusal(lambda: h.writer.write("lead", f"{REPORT}/AGENT.md", "---\ntools: [shell, write]\n---\nx\n")).startswith("a charter needs YAML")
    assert written(h, "lead", "rev", "AGENT.md") == before


# ------------------------------------------------------------------------------ root


def test_root_edits_the_charter_of_a_top_level_agent_as_it_is(h: OrgFilesHarness) -> None:
    path, note = h.writer.write_noted("root", "lead/AGENT.md", "not even a frontmatter")
    assert path == h.root / "lead" / "AGENT.md" and note == "" and written(h, "lead", "AGENT.md") == "not even a frontmatter"


def test_root_is_not_held_to_the_authority_checks(h: OrgFilesHarness) -> None:
    h.writer.write("root", "lead/AGENT.md", text("Lead", tools=["read", "shell", "web", "write"], workspace=str(h.outside / "anywhere")))
    assert charter(h, "lead")["tools"] == ["read", "shell", "web", "write"]


def test_a_refusal_of_the_guard_comes_before_the_charter_checks(h: OrgFilesHarness) -> None:
    with pytest.raises(OrgError, match="^AGENT.md can only be written for an existing direct report"):
        h.writer.write("lead", "lead/stranger/AGENT.md", text("S", tools=["read", "write", "web"]))
