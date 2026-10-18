"""The generators and commands that later steps run: ``gen_importlinter``, ``lint``, ``mapping_status``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from . import checks, gen_importlinter, graph, mapping_status
from .conftest import REPO

pytestmark = [pytest.mark.architecture, pytest.mark.xfail(strict=True, reason="red: M0")]

MAPPING = """\
### 5.1 `core.py` — module-level symbols

| Symbol | Target |
|---|---|
| `OrgError` | `kernel.OrgError` |
| `word_count`, `_FENCE_LINE` | `kernel/_text.py::word_count` |
| `messages`, `received` | `mail.MailboxReader` |
| `_wakes` | `mail/_mailbox.py::FsMailbox._wakes` (private helper) |
| `_inside` | `kernel.inside` (**deleted: duplicate of** `blueprint._within`) |
| `Retired` | `hierarchy.Retired` |
| `ROOT RUNTIME BOXES` | `kernel` (public constants) |

### 5.2 `core.Message` methods

| Method | Target |
|---|---|
| `meta` | `kernel.Message` (unchanged, pure) |
"""


def package(root: Path, name: str, **files: str) -> None:
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / "__init__.py").write_text("", encoding="utf-8")
    for filename, text in files.items():
        (root / name / filename.replace("__", ".")).write_text(text, encoding="utf-8")


def synthetic_tree(tmp_path: Path) -> checks.Tree:
    root = tmp_path / "orgmcp"
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    (root / "core.py").write_text("", encoding="utf-8")
    package(root, "kernel", api__py="", _text__py="def word_count(): ...\n")
    package(root, "agents", api__py="", _registry__py="", testing__py="")
    package(root, "mail", api__py="class MailboxReader: ...\n", _mailbox__py="class FsMailbox:\n    def _wakes(self): ...\n",
            _parser__py="")
    package(root, "settings", api__py="")
    return checks.Tree(root)


# ----------------------------------------------------------------------------------------------------- gen_importlinter


def test_the_generated_config_describes_only_the_packages_that_exist(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    assert text is not None
    assert "root_package = orgmcp" in text and "include_external_packages = True" in text
    layers = text.split("[importlinter:contract:layers]")[1].split("[importlinter:contract:")[0]
    lines = [line.strip() for line in layers.splitlines() if line.strip().startswith("orgmcp.")]
    assert lines == ["orgmcp.core", "orgmcp.agents | orgmcp.settings", "orgmcp.mail", "orgmcp.kernel"] or \
        lines == ["orgmcp.core", "orgmcp.mail", "orgmcp.agents | orgmcp.settings", "orgmcp.kernel"], lines
    assert "orgmcp.telemetry" not in text and "orgmcp.dashboard" not in text  # not on disk


def test_a_layer_order_follows_the_levels_of_the_graph(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    order = [line.strip() for line in text.split("[importlinter:contract:layers]")[1].splitlines() if line.strip().startswith("orgmcp.")]
    assert order.index("orgmcp.mail") < order.index("orgmcp.agents | orgmcp.settings") < order.index("orgmcp.kernel")  # mail imports agents


def test_one_private_modules_contract_per_package_with_private_modules(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    mail = text.split("[importlinter:contract:private-modules-mail]")[1].split("[importlinter:contract:")[0]
    assert "type = protected" in mail and "orgmcp.mail._mailbox" in mail and "orgmcp.mail._parser" in mail
    assert "allowed_importers" in mail and "orgmcp.mail\n" in mail
    assert "private-modules-agents" in text and "private-modules-settings" not in text  # settings has no _ module
    assert "private-modules-kernel" in text


def test_the_kernel_contract_forbids_every_other_module_of_the_root(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    kernel = text.split("[importlinter:contract:kernel-independent]")[1].split("[importlinter:contract:")[0]
    for module in ("orgmcp.core", "orgmcp.agents", "orgmcp.mail", "orgmcp.settings"):
        assert module in kernel
    assert "orgmcp.kernel\n" in kernel.split("forbidden_modules")[0]


def test_testing_modules_are_protected_from_production_code(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    section = text.split("[importlinter:contract:no-testing-in-production]")[1].split("[importlinter:contract:")[0]
    assert "orgmcp.agents.testing" in section and "orgmcp.*.tests" in section and "orgmcp.*.testing" in section


def test_framework_contracts_name_the_allowed_package(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    assert "[importlinter:contract:textual-only-in-dashboard]" in text
    assert "[importlinter:contract:mcp-only-in-mcp-server]" in text
    assert "[importlinter:contract:yaml-only-where-needed]" in text


def test_nothing_is_generated_when_no_package_exists(tmp_path):
    root = tmp_path / "orgmcp"
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    (root / "cli.py").write_text("", encoding="utf-8")
    assert gen_importlinter.generate(checks.Tree(root)) is None


def test_every_package_of_the_map_is_known_to_the_generator():
    assert len(graph.PACKAGES) == 41
    assert set(gen_importlinter.GRAPH) == set(graph.PACKAGES)


# ------------------------------------------------------------------------------------------------------------------- lint


def test_lint_writes_the_config_to_a_git_ignored_file():
    assert ".importlinter" in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()


# ------------------------------------------------------------------------------------------------------ mapping_status


def test_mapping_status_lists_the_symbols_that_have_not_moved(tmp_path):
    tree = synthetic_tree(tmp_path)  # mail/api.py defines MailboxReader; mail/_mailbox.py defines FsMailbox._wakes
    result = mapping_status.status("mail", MAPPING, tree)
    assert [r.symbol for r in result.moved] == ["messages", "received", "_wakes"]
    assert result.unmoved == []
    result = mapping_status.status("kernel", MAPPING, tree)
    assert [r.symbol for r in result.moved] == ["word_count", "_FENCE_LINE"]
    assert {r.symbol for r in result.unmoved} == {"OrgError", "_inside", "ROOT", "RUNTIME", "BOXES", "meta"}


def test_mapping_status_attributes_a_row_to_its_first_target_and_skips_deleted_rows(tmp_path):
    tree = synthetic_tree(tmp_path)
    result = mapping_status.status("hierarchy", MAPPING, tree)
    assert [r.symbol for r in result.unmoved] == ["Retired"] and result.moved == []
    result = mapping_status.status("blueprint", MAPPING, tree)  # only mentioned in a "duplicate of" remark of the kernel row
    assert result.unmoved == [] and result.moved == []
    deleted = "| Symbol | Target |\n|---|---|\n| `Runner` (type alias) | deleted: replaced by `kiro.RunCommandBuilder` |\n"
    assert mapping_status.status("kiro", "### 5.4 `scheduler.py`\n\n" + deleted, tree).unmoved == []


def test_mapping_status_command_exits_1_while_symbols_are_unmoved_and_2_for_an_unknown_package():
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "tests.architecture.mapping_status", *args], capture_output=True, text=True,
                              cwd=REPO, env={**os.environ, "PYTHONPATH": str(REPO)}, timeout=120)

    result = run("hierarchy")
    assert result.returncode == 1 and "Retired" in result.stdout and "unmoved" in result.stdout
    assert run("nonsense").returncode == 2
