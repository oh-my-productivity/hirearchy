"""The split of a result's client items is decided in one place (D-E6-1, A2; design 4.1 and 4.3).

``kernel.client_items`` calls the parser ``kernel.client_questions`` and splits its items by whether they name a criterion id: the questions flag a
result and withhold its path, the notes are listed. A module that called the parser itself would count, flag or repeat items by a rule of its own,
and a criterion-tagged question could be hidden. So no module of ``src/hirearchy`` outside ``kernel`` (and outside ``tests/`` directories and the
in-memory fakes of ``testing.py``) calls ``client_questions(``."""

from __future__ import annotations

from pathlib import Path

from .paths import SRC


def modules() -> list[Path]:
    """The modules of ``SRC`` outside ``kernel``, outside any ``tests`` directory and outside ``testing.py``."""
    return sorted(
        p for p in SRC.rglob("*.py")
        if "tests" not in p.parts and p.name != "testing.py" and p.relative_to(SRC).parts[0] != "kernel"
    )


def test_no_module_outside_kernel_calls_client_questions() -> None:
    found = [
        f"{path.relative_to(SRC)}:{number}"
        for path in modules()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "client_questions(" in line
    ]
    assert found == [], f"only kernel.client_items may call kernel.client_questions (D-E6-1): {found}"


def test_the_scan_sees_the_kernel_parser_and_its_one_caller() -> None:
    """The scan is not vacuous: kernel itself defines and calls ``client_questions(``, and ``modules()`` covers the packages that read items."""
    kernel = (SRC / "kernel" / "_text.py").read_text(encoding="utf-8")
    assert "def client_questions(" in kernel and "client_questions(body)" in kernel
    names = {p.relative_to(SRC).parts[0] for p in modules()}
    assert {"progress", "reflection", "mcp_server"} <= names and "kernel" not in names
