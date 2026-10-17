"""Core CSV -> Markdown table conversion."""

import csv
from typing import Iterable

ALIGNMENTS = {"left": ":---", "center": ":---:", "right": "---:"}


class EmptyInputError(ValueError):
    """Raised when the input contains no CSV rows."""


def _escape(cell: str) -> str:
    # Escape pipes; collapse newlines inside cells so the row stays on one line.
    return cell.replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def csv_to_markdown(lines: Iterable[str], align: str = "left") -> str:
    """Convert CSV text (an iterable of lines, opened with newline='') to a Markdown table.

    The first row is the header. Shorter rows are padded with empty cells; if a
    row is longer than the header, the header is extended with empty cells so
    no data is lost and every row has the same number of columns.
    """
    if align not in ALIGNMENTS:
        raise ValueError(f"invalid alignment: {align!r} (choose from left, center, right)")
    rows = [r for r in csv.reader(lines) if r]  # skip fully blank lines
    if not rows or all(not any(c.strip() for c in r) for r in rows):
        raise EmptyInputError("input is empty (no CSV rows found)")
    width = max(len(r) for r in rows)
    rows = [[_escape(c) for c in r] + [""] * (width - len(r)) for r in rows]
    header, body = rows[0], rows[1:]
    out = [_row(header), _row([ALIGNMENTS[align]] * width)]
    out.extend(_row(r) for r in body)
    return "\n".join(out) + "\n"
