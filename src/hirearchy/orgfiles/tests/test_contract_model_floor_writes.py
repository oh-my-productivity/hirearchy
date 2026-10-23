"""Contract of ``OrgFileWriter`` and the model floor (docs/design/org-agent-model-floor.md 3): a charter rewrite cannot move an agent below the
allowed models, and root's write of ORG.md cannot widen the set or lower the effort and the default model. What an agent already runs on is
never refused: a rewrite that leaves the model as it was goes through."""

from __future__ import annotations

from pathlib import Path

import pytest

from hirearchy.kernel import JsonObject, join_frontmatter, split_frontmatter
from hirearchy.orgfiles import OrgFileWriter
from hirearchy.orgfiles.testing import IMPLEMENTATIONS, OrgFilesHarness

from ._support import make, refusal, team, written

PAIR = "claude-sonnet-5.5, claude-opus-5.5"
MODELS_OUT = ["claude-haiku-4.5", "claude-sonnet-4.6"]
MODELS_IN = ["claude-sonnet-5.5", "claude-opus-5.5"]


def m1(model: str, allowed: str = PAIR) -> str:
    return f'model "{model}" is not allowed for org agents; allowed: {allowed} (only the user can widen this set)'


@pytest.fixture(params=IMPLEMENTATIONS[OrgFileWriter], ids=lambda factory: factory.__name__)
def h(request: pytest.FixtureRequest, tmp_path: Path) -> OrgFilesHarness:
    return team(make(request, tmp_path))


def org_md(meta: JsonObject) -> str:
    return join_frontmatter(meta, "# Organization\n\nRules.")


def charter(model: str | None, role: str = "Engineer") -> str:
    meta: JsonObject = {"role": role}
    if model is not None:
        meta["model"] = model
    return join_frontmatter(meta, "# Role\n\nNew body.")


def pin(h: OrgFilesHarness, addr: str, model: str) -> None:
    """The agent's charter says ``model`` (written behind ``hire`` and ``write``: a charter from before the floor)."""
    old, _ = split_frontmatter(written(h, addr, "AGENT.md") or "")
    h.put(h.root / addr / "AGENT.md", join_frontmatter({**old, "model": model}, "# Role\n\nDo the work."))


WRITERS = [("ceo", "ceo/eng"), ("root", "ceo")]  # (who rewrites, whose charter): a manager and its report, root and its direct report


@pytest.mark.parametrize("who, addr", WRITERS)
@pytest.mark.parametrize("model", MODELS_OUT)
def test_a_charter_rewrite_to_a_model_outside_the_set_is_refused(h: OrgFilesHarness, who: str, addr: str, model: str) -> None:
    before = written(h, addr, "AGENT.md")
    assert refusal(lambda: h.writer.write(who, f"{addr}/AGENT.md", charter(model))) == f"charter of {addr}: {m1(model)}"
    assert written(h, addr, "AGENT.md") == before


@pytest.mark.parametrize("who, addr", WRITERS)
@pytest.mark.parametrize("model", MODELS_IN)
def test_a_charter_rewrite_to_a_floor_model_is_admitted(h: OrgFilesHarness, who: str, addr: str, model: str) -> None:
    h.writer.write(who, f"{addr}/AGENT.md", charter(model))
    text = written(h, addr, "AGENT.md")
    assert text is not None and f"model: {model}" in text


@pytest.mark.parametrize("who, addr", WRITERS)
def test_a_rewrite_that_keeps_a_model_below_the_floor_is_admitted(h: OrgFilesHarness, who: str, addr: str) -> None:
    """An agent that existed before the floor can still get a new body, or the same model written again."""
    pin(h, addr, "claude-haiku-4.5")
    h.writer.write(who, f"{addr}/AGENT.md", charter("claude-haiku-4.5", role="Sharper"))
    text = written(h, addr, "AGENT.md")
    assert text is not None and "model: claude-haiku-4.5" in text and "Sharper" in text


def test_a_manager_s_body_only_rewrite_keeps_the_model_below_the_floor(h: OrgFilesHarness) -> None:
    pin(h, "ceo/eng", "claude-haiku-4.5")
    h.writer.write("ceo", "ceo/eng/AGENT.md", charter(None, role="Sharper"))  # the merge keeps the model the old charter had
    text = written(h, "ceo/eng", "AGENT.md")
    assert text is not None and "model: claude-haiku-4.5" in text and "Sharper" in text


def test_an_append_to_a_charter_below_the_floor_is_admitted(h: OrgFilesHarness) -> None:
    pin(h, "ceo", "claude-haiku-4.5")
    h.writer.write("root", "ceo/AGENT.md", "\nOne more rule.\n", append=True)
    text = written(h, "ceo", "AGENT.md")
    assert text is not None and "model: claude-haiku-4.5" in text and text.endswith("One more rule.\n")


@pytest.mark.parametrize("who, addr", WRITERS)
def test_unsetting_the_model_is_refused_when_the_default_is_outside_the_set(h: OrgFilesHarness, who: str, addr: str) -> None:
    h.put_org_md(org_md({"max_depth": 4, "default_model": "claude-haiku-4.5"}))
    pin(h, addr, "claude-opus-5.5")
    unset = join_frontmatter({"role": "Engineer", "model": None}, "# Role\n\nBody.")
    assert refusal(lambda: h.writer.write(who, f"{addr}/AGENT.md", unset)) == f"charter of {addr}: {m1('claude-haiku-4.5')}"
    text = written(h, addr, "AGENT.md")
    assert text is not None and "model: claude-opus-5.5" in text


@pytest.mark.parametrize("who, addr", WRITERS)
def test_a_widened_set_admits_its_extra_model_in_a_rewrite(h: OrgFilesHarness, who: str, addr: str) -> None:
    h.put_org_md(org_md({"max_depth": 4, "extra_allowed_models": ["claude-sonnet-4.6"]}))
    h.writer.write(who, f"{addr}/AGENT.md", charter("claude-sonnet-4.6"))
    text = written(h, addr, "AGENT.md")
    assert text is not None and "model: claude-sonnet-4.6" in text
    assert refusal(lambda: h.writer.write(who, f"{addr}/AGENT.md", charter("claude-haiku-4.5"))) == (
        f"charter of {addr}: {m1('claude-haiku-4.5', PAIR + ', claude-sonnet-4.6')}"
    )


# ------------------------------------------------------------------------------ root's write of ORG.md


def test_root_may_not_widen_the_allowed_models_in_ORG_md(h: OrgFilesHarness) -> None:
    before = written(h, "ORG.md")
    widened = org_md({"max_depth": 4, "extra_allowed_models": ["claude-sonnet-4.6"]})
    assert refusal(lambda: h.writer.write("root", "ORG.md", widened)) == (
        "ORG.md: only the user can widen the allowed models, by editing ORG.md themselves (not allowed now: claude-sonnet-4.6)"
    )
    assert written(h, "ORG.md") == before


@pytest.mark.parametrize(
    "meta, message",
    [
        ({"effort": "medium"}, 'effort "medium" is not allowed for org agents; allowed: high, xhigh, max'),
        ({"effort": "low"}, 'effort "low" is not allowed for org agents; allowed: high, xhigh, max'),
        ({"default_model": "claude-haiku-4.5"}, "default_model: " + m1("claude-haiku-4.5")),
        ({"default_model": "claude-sonnet-4.6"}, "default_model: " + m1("claude-sonnet-4.6")),
    ],
    ids=lambda v: repr(v)[:30],
)
def test_root_may_not_set_an_effort_or_a_default_model_below_the_floor_in_ORG_md(h: OrgFilesHarness, meta: JsonObject, message: str) -> None:
    before = written(h, "ORG.md")
    assert refusal(lambda: h.writer.write("root", "ORG.md", org_md({"max_depth": 4, **meta}))) == f"ORG.md: {message}"
    assert written(h, "ORG.md") == before


def test_root_may_raise_the_effort_and_choose_a_floor_model_in_ORG_md(h: OrgFilesHarness) -> None:
    text = org_md({"max_depth": 4, "effort": "xhigh", "default_model": "claude-opus-5.5"})
    h.writer.write("root", "ORG.md", text)
    assert written(h, "ORG.md") == text


def test_root_may_keep_what_ORG_md_already_had(h: OrgFilesHarness) -> None:
    """An organization made before the floor: root can still rewrite its rules while the old default model and effort stay."""
    h.put_org_md(org_md({"max_depth": 4, "default_model": "claude-haiku-4.5", "effort": "low"}))
    rewritten = join_frontmatter({"max_depth": 3, "default_model": "claude-haiku-4.5", "effort": "low"}, "# Organization\n\nNew rules.")
    h.writer.write("root", "ORG.md", rewritten)
    assert written(h, "ORG.md") == rewritten


def test_root_may_keep_the_extra_models_the_user_listed(h: OrgFilesHarness) -> None:
    h.put_org_md(org_md({"max_depth": 4, "extra_allowed_models": ["claude-sonnet-4.6"], "default_model": "claude-sonnet-4.6"}))
    rewritten = join_frontmatter(
        {"max_depth": 3, "extra_allowed_models": ["claude-sonnet-4.6"], "default_model": "claude-sonnet-4.6"}, "# Organization\n\nNew rules."
    )
    h.writer.write("root", "ORG.md", rewritten)
    assert written(h, "ORG.md") == rewritten


def test_an_ORG_md_whose_frontmatter_cannot_be_read_is_written_as_before(h: OrgFilesHarness) -> None:
    broken = "---\nmax_depth: [unclosed\n---\n# Organization\n"
    h.writer.write("root", "ORG.md", broken)
    assert written(h, "ORG.md") == broken


def test_other_files_are_not_looked_at(h: OrgFilesHarness) -> None:
    h.writer.write("root", "MEMORY.md", "---\neffort: low\nmodel: claude-haiku-4.5\n---\nnotes\n")
    h.writer.write("ceo", "ceo/notes.md", "---\nextra_allowed_models: [x]\n---\nnotes\n")
    assert written(h, "ceo", "notes.md") == "---\nextra_allowed_models: [x]\n---\nnotes\n"
