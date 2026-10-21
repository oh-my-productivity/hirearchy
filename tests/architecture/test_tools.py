"""The generators and commands that later steps run: ``gen_importlinter`` and ``lint``, and the mypy discovery."""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

from . import checks, gen_importlinter, graph
from .paths import REPO

pytestmark = pytest.mark.architecture


def package(root: Path, name: str, **files: str) -> None:
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / "__init__.py").write_text("", encoding="utf-8")
    for filename, text in files.items():
        (root / name / filename.replace("__", ".")).write_text(text, encoding="utf-8")


def synthetic_tree(tmp_path: Path) -> checks.Tree:
    root = tmp_path / "hirearchy"
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
    assert "root_package = hirearchy" in text and "include_external_packages = True" in text
    layers = text.split("[importlinter:contract:layers]")[1].split("[importlinter:contract:")[0]
    lines = [line.strip() for line in layers.splitlines() if line.strip().startswith("hirearchy.")]
    assert lines == ["hirearchy.core", "hirearchy.mail", "hirearchy.agents | hirearchy.settings", "hirearchy.kernel"], lines
    assert "hirearchy.telemetry" not in text and "hirearchy.dashboard" not in text  # not on disk


def test_a_layer_order_follows_the_levels_of_the_graph(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    order = [line.strip() for line in text.split("[importlinter:contract:layers]")[1].splitlines() if line.strip().startswith("hirearchy.")]
    assert order.index("hirearchy.mail") < order.index("hirearchy.agents | hirearchy.settings") < order.index("hirearchy.kernel")  # mail imports agents


def test_one_private_modules_contract_per_package_with_private_modules(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    mail = text.split("[importlinter:contract:private-modules-mail]")[1].split("[importlinter:contract:")[0]
    assert "type = protected" in mail and "hirearchy.mail._mailbox" in mail and "hirearchy.mail._parser" in mail
    assert "allowed_importers" in mail and "hirearchy.mail\n" in mail
    assert "private-modules-agents" in text and "private-modules-settings" not in text  # settings has no _ module
    assert "private-modules-kernel" in text


def test_the_kernel_contract_forbids_every_other_module_of_the_root(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    kernel = text.split("[importlinter:contract:kernel-independent]")[1].split("[importlinter:contract:")[0]
    for module in ("hirearchy.core", "hirearchy.agents", "hirearchy.mail", "hirearchy.settings"):
        assert module in kernel
    assert "hirearchy.kernel\n" in kernel.split("forbidden_modules")[0]


def test_testing_modules_are_protected_from_production_code(tmp_path):
    text = gen_importlinter.generate(synthetic_tree(tmp_path))
    section = text.split("[importlinter:contract:no-testing-in-production]")[1].split("[importlinter:contract:")[0]
    assert "hirearchy.agents.testing" in section and "hirearchy.*.tests" in section and "hirearchy.*.testing" in section


def test_framework_contracts_exist_for_the_frameworks_the_code_imports(tmp_path):
    tree = synthetic_tree(tmp_path)
    assert "textual-only-in-dashboard" not in gen_importlinter.generate(tree)  # nothing imports textual: import-linter would reject it
    (tree.directory / "mail" / "_parser.py").write_text("import textual\nimport mcp.server\nimport yaml\n", encoding="utf-8")
    text = gen_importlinter.generate(tree)
    textual = text.split("[importlinter:contract:textual-only-in-dashboard]")[1].split("[importlinter:contract:")[0]
    assert "forbidden_modules =\n    textual\n" in textual and "hirearchy.mail" in textual and "hirearchy.dashboard" not in textual
    assert "[importlinter:contract:mcp-only-in-mcp-server]" in text
    yaml_section = text.split("[importlinter:contract:yaml-only-where-needed]")[1].split("[importlinter:contract:")[0]
    assert "hirearchy.mail" in yaml_section and "hirearchy.kernel" not in yaml_section  # the kernel may use yaml


def test_nothing_is_generated_when_no_package_exists(tmp_path):
    root = tmp_path / "hirearchy"
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


# ------------------------------------------------------------------------------------------------------------ mypy strictness


def test_every_package_directory_is_checked_with_mypy_strict(tmp_path):
    spec = importlib.util.spec_from_file_location("static_checks", REPO / "scripts" / "static_checks.py")
    assert spec and spec.loader
    static_checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(static_checks)
    tree = synthetic_tree(tmp_path)
    (tree.directory / "roles").mkdir()  # packaged data, not a package
    (tree.directory / "roles" / "analyst.md").write_text("", encoding="utf-8")
    assert static_checks.discover_packages(tree.directory) == ["hirearchy.agents", "hirearchy.kernel", "hirearchy.mail", "hirearchy.settings"]


def test_the_public_surface_of_a_package_may_not_use_any():
    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["mypy"]
    api = next(o for o in config["overrides"] if o["module"] == ["hirearchy.*.api"])
    assert api["disallow_any_explicit"] is True and config["strict"] is True
