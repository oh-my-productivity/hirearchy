"""The structural rules R1, R4, R6-R9, R13 on the real source tree, and a seeded violation for each checker.

On today's code the checks are vacuous for the packages that do not exist yet (a checker only looks at ``src/orgmcp/<pkg>/`` for
packages that are there). The seeded tests prove each checker CAN fail: ``fixtures/bad_pkg`` breaks one rule per module.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from . import checks, class_interfaces, gen_importlinter, graph, legacy_exports, lint
from .conftest import FIXTURES, REPO

pytestmark = [pytest.mark.architecture, pytest.mark.xfail(strict=True, reason="red: M0")]

# What the seeded package is allowed to import: nothing but the kernel.
BAD_GRAPH = {name: graph.Package(name, "feature", (graph.KERNEL,)) for name in ("settings", "mail", "rogue", "wide")}


def report(violations: list[checks.Violation]) -> str:
    return "\n".join(str(v) for v in violations)


# ----------------------------------------------------------------------------------------------------------- real code


def test_protocols_are_small(real_tree):
    assert not (found := checks.protocol_widths(real_tree)), report(found)


def test_no_module_level_singletons(real_tree):
    assert not (found := checks.module_singletons(real_tree)), report(found)


def test_single_writer(real_tree):
    assert not (found := checks.single_writer(real_tree)), report(found)


def test_each_ledger_name_has_one_owner(real_tree):
    assert not (found := checks.ledger_names(real_tree)), report(found)


def test_responsibilities_have_no_and(architecture_text):
    assert not (found := checks.responsibilities(architecture_text)), report(found)
    assert len(checks.responsibility_sentences(architecture_text)) == 42


def test_init_reexports_exactly_api(real_tree):
    assert not (found := checks.init_reexports(real_tree, legacy_exports.exported_names_by_package())), report(found)


def test_package_contents(real_tree):
    assert not (found := checks.package_contents(real_tree)), report(found)


def test_every_protocol_has_a_contract_suite(real_tree):
    assert not (found := checks.contract_suites(real_tree)), report(found)


def test_imports_follow_the_dependency_graph(real_tree):
    assert not (found := checks.imports_against_graph(real_tree)), report(found)


# --------------------------------------------------------------------------------------------- seeded violations: each fails


def test_a_protocol_with_nine_methods_is_flagged(bad_tree):
    found = checks.protocol_widths(bad_tree)
    assert [v.rule for v in found] == ["R7"] and "Wide has 9 public methods" in found[0].message


def test_a_module_level_singleton_and_a_global_cache_are_flagged(bad_tree):
    found = checks.module_singletons(bad_tree)
    assert len(found) == 2 and all("rogue._singleton" in v.where for v in found), report(found)
    assert any("REGISTRY = Registry()" in v.message for v in found) and any("CACHE" in v.message for v in found)


def test_a_second_writer_of_ORG_md_is_flagged_and_the_owner_is_not(bad_tree):
    found = checks.single_writer(bad_tree)
    assert len(found) == 1, report(found)
    assert "rogue._second_writer" in found[0].where and "ORG.md" in found[0].message and "settings" in found[0].message


def test_a_ledger_used_outside_its_owner_is_flagged(bad_tree):
    found = checks.ledger_names(bad_tree)
    assert len(found) == 1 and "failures" in found[0].message and "eligibility" in found[0].message, report(found)


def test_a_responsibility_with_and_is_flagged(architecture_text):
    bad = (FIXTURES / "bad_architecture.md").read_text(encoding="utf-8")
    found = checks.responsibilities(bad)
    assert [v.where for v in found] == ["package mail"], report(found)
    assert not checks.responsibilities(architecture_text)  # and the real document is clean


def test_an_init_that_exports_more_than_api_is_flagged(bad_tree):
    found = checks.init_reexports(bad_tree)
    assert len(found) == 1 and "rogue.__init__" in found[0].where and "Plain" in found[0].message, report(found)


def test_a_public_module_and_a_package_outside_the_map_are_flagged(bad_tree):
    found = checks.package_contents(bad_tree, known=BAD_GRAPH)
    messages = report(found)
    assert "rogue/public_module.py" in messages
    assert "not a package of the architecture map" not in messages
    assert "not a package of the architecture map" in report(checks.package_contents(bad_tree, known=["settings", "mail", "rogue"]))


def test_a_protocol_without_a_contract_suite_is_flagged(bad_tree):
    messages = report(checks.contract_suites(bad_tree))
    assert "mail.api.Mailbox" in messages and "no contract suite" in messages


def test_an_import_the_graph_does_not_allow_is_flagged(bad_tree):
    found = checks.imports_against_graph(bad_tree, BAD_GRAPH)
    assert sorted(v.message.split()[1].rstrip(",") for v in found) == ["mail", "settings"], report(found)
    assert all(v.where == "bad_pkg.rogue._imports_private" for v in found)


def test_a_class_without_a_protocol_is_flagged(bad_tree):
    import bad_pkg

    offenders, counts = class_interfaces.survey(bad_pkg)
    assert sorted(offenders) == ["bad_pkg.rogue._no_protocol.Plain", "bad_pkg.rogue._singleton.Registry"]
    assert counts["compliant"] >= 2  # FsOrgDocuments and MemoryMailbox do implement their Protocol


def test_an_import_of_a_private_module_of_another_package_breaks_the_contract(bad_tree, tmp_path):
    config = tmp_path / "importlinter.ini"
    config.write_text(gen_importlinter.generate(bad_tree, BAD_GRAPH) or "", encoding="utf-8")
    result = lint.run_lint_imports(config, cwd=REPO, pythonpath=FIXTURES)
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "private-modules-mail" in output and "bad_pkg.rogue._imports_private" in output and "bad_pkg.mail._mailbox" in output


# ------------------------------------------------------------------------------------------------------- the commands run


def test_the_lint_command_passes_on_today_s_code():
    result = subprocess.run([sys.executable, "-m", "tests.architecture.lint"], capture_output=True, text=True, cwd=REPO,
                            env={**os.environ, "PYTHONPATH": str(Path(REPO))}, timeout=600)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 broken" in result.stdout
