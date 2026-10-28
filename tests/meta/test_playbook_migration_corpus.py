"""The migration of a free-text playbook loses nothing and never needs a fallback on real playbooks (design 4.4, B5, plan PC-6).

The corpus is every kept playbook of the studies (61 files) and every v1 the blueprint writes (the shipped service example and the four
``*-service`` templates). ``migrate_body`` must pass its loss check with the per-block split on each: a body that needs a fallback is a splitter bug."""

from __future__ import annotations

from pathlib import Path

import testkit

from hirearchy.blueprint._budgeting import BudgetPlanner
from hirearchy.blueprint._pathcheck import RootedPathChecker
from hirearchy.blueprint._playbooks import StepsPlaybookWriter
from hirearchy.blueprint._resolver import AgentResolver
from hirearchy.blueprint.testing import StaticOrgContext, role_library_of
from hirearchy.blueprint.tests._plans import LABELS, base_dir, load_text, template_at
from hirearchy.kernel import split_frontmatter
from hirearchy.kernel.testing import DictEnvironment
from hirearchy.services._items import migrate_body, parse_items, render_items, split_check

STUDIES = testkit.REPO / "studies"
KEPT = sorted(STUDIES.glob("**/PLAYBOOK*.md"))
SERVICE_LABELS = [label for label in LABELS if label.endswith("-service")]


def check_migrates_per_block(body: str, name: str) -> None:
    m = migrate_body(body)
    assert m.reason == "", f"{name}: the per-block split did not keep every line ({m.reason})"
    assert split_check(body, m.items, m.sections), name
    assert all(i.kind == "step" and i.why == () for i in m.items), name
    back = parse_items(render_items(m.items, m.sections), {"items_max": len(m.items)})
    assert (back.error, back.items, back.sections) == ("", m.items, m.sections), name
    # a real playbook is a list of steps: the split gives it more than one item (not one giant item), and each item is a few lines at most
    assert len(m.items) >= 2, name
    assert max(len(i.text.splitlines()) for i in m.items) <= 40, name


def test_every_kept_playbook_migrates_with_the_per_block_split_and_no_fallback() -> None:
    assert len(KEPT) == 61, [str(p.relative_to(STUDIES)) for p in KEPT]  # B5: E, E2, E3, E4 s1/s1r/s2/s2r/s3, E5-E7 s1-s3, G0's six (42); P1's 19: F1-F3 one each, I1-I3 five each, scoring/F2/renamed-view one
    for path in KEPT:
        _, body = split_frontmatter(path.read_text(encoding="utf-8"))
        check_migrates_per_block(body.strip(), str(path.relative_to(STUDIES)))


def generated_playbooks(tmp_path: Path) -> dict[str, str]:
    """What ``StepsPlaybookWriter.default_playbook`` writes for the services of the shipped example and of the four ``*-service`` templates."""
    base = base_dir(tmp_path)
    planner = BudgetPlanner()
    texts = {f"template {label}": template_at(label, "filled", base) for label in SERVICE_LABELS}
    texts["examples/blueprint-service.yaml"] = (testkit.REPO / "examples" / "blueprint-service.yaml").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for name, text in texts.items():
        bp = load_text(text)
        agents = AgentResolver(role_library_of(packaged=True), RootedPathChecker(DictEnvironment(home=tmp_path, cwd=tmp_path))).resolve(
            bp, StaticOrgContext(), [base], [],
        )
        budgets = planner.service_budgets(bp, agents)
        for service in bp["services"]:  # type: ignore[attr-defined]
            out[f"{name}/{service['name']}"] = StepsPlaybookWriter(planner).default_playbook(agents[0], agents, service, budgets[service["name"]])
    return out


def test_every_generated_v1_migrates_with_the_per_block_split_and_no_fallback(tmp_path: Path) -> None:
    generated = generated_playbooks(tmp_path)
    assert len(generated) >= 5 and any(k.startswith("examples/") for k in generated)
    for name, body in generated.items():
        check_migrates_per_block(body.strip(), name)
