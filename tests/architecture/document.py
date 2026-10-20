"""Parsers of ARCHITECTURE.md: the tables that the machine-readable data (graph, ownership, mapping) must equal.

Only what the architecture tests need: the package map (2.2), the levels (4.1), the ownership table (2.3) and the edges (4.3). Each
function takes the document text and returns plain data. (The mapping tables of section 5 are the historical record of the migration;
nothing parses them any more.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PACKAGE_ROW = re.compile(r"^\|\s*\d+\s*\|")
_IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")


@dataclass(frozen=True)
class PackageRow:
    name: str
    kind: str
    responsibility: str
    deps: tuple[str, ...]


def section_lines(markdown: str, heading: str) -> list[str]:
    """Lines under the heading that starts with ``heading`` (e.g. "### 2.2"), up to the next heading or rule."""
    lines = markdown.splitlines()
    for start, line in enumerate(lines):
        if line.startswith(heading):
            end = next((i for i in range(start + 1, len(lines)) if re.match(r"^(#{1,3} |---$)", lines[i])), len(lines))
            return lines[start + 1:end]
    return []


def cells(line: str) -> list[str]:
    """Cells of a markdown table row; a "|" inside backticks does not split."""
    out, current, in_code = [], [], False
    for char in line.strip().strip("|"):
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            out.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    out.append("".join(current).strip())
    return out


def _tick(text: str) -> list[str]:
    return re.findall(r"`([^`]+)`", text)


# ------------------------------------------------------------------------------------------------------------------- 2.2


def package_rows(markdown: str) -> list[PackageRow]:
    """The rows of the package map (``| <n> | `name` | kind | responsibility | ... | allowed dependencies |``)."""
    lines = section_lines(markdown, "### 2.2") or markdown.splitlines()
    rows = []
    for line in lines:
        if _PACKAGE_ROW.match(line):
            row = cells(line)
            match = re.match(r"`(\w+)`", row[1])
            if match and len(row) >= 4:
                deps = row[-1]
                rows.append(PackageRow(match.group(1), row[2], row[3],
                                       () if deps == "none" or deps.startswith("everything") else tuple(d.strip() for d in deps.split(","))))
    return rows


# ------------------------------------------------------------------------------------------------------------------- 4.3


def edge_rows(markdown: str) -> set[tuple[str, str]]:
    """(importer, imported) pairs of the table "Every edge and the interface it uses"."""
    edges = set()
    for line in section_lines(markdown, "### 4.3"):
        match = re.match(r"^\|\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|", line)
        if match:
            edges.add((match.group(1), match.group(2)))
    return edges


# ------------------------------------------------------------------------------------------------------------------- 4.1


def level_rows(markdown: str) -> dict[str, tuple[str, ...]]:
    """{"L1": names, ..., "E": entry points, "A": ...} of the levels table (names sorted)."""
    levels = {}
    for line in section_lines(markdown, "### 4.1"):
        match = re.match(r"^\|\s*(L\d+|E|A)\s*\|(.*)\|\s*$", line)
        if match:
            levels[match.group(1)] = tuple(sorted(n for n in _tick(match.group(2)) if _IDENTIFIER.match(n) and "." not in n))
    return levels


# ------------------------------------------------------------------------------------------------------------------- 2.3


def ownership_rows(markdown: str) -> list[tuple[str, str]]:
    """(path text without backticks, owning package) for every row of the ownership table."""
    rows = []
    for line in section_lines(markdown, "### 2.3"):
        if line.startswith("|") and not re.match(r"^\|\s*(Path|-)", line):
            row = cells(line)
            owners = _tick(row[1])
            if owners:
                rows.append((row[0].replace("`", ""), owners[0]))
    return rows


def ledger_registry(markdown: str) -> dict[str, str]:
    """{ledger name: owning package} from the paragraph "Ledger names ... are a closed registry"."""
    text = " ".join(section_lines(markdown, "### 2.3"))
    paragraph = text[text.index("Ledger names"):] if "Ledger names" in text else ""
    return dict(re.findall(r"`(\w+)`\s*->\s*`(\w+)`", paragraph))
