"""P2 harness library: file formats and the design's pure definitions (no product code; written from the design texts and from the formats
of kept evidence and throwaway orgs; protocol 13; the author did not open src/hirearchy/, harness/CHANGES.md).

Definitions implemented here, each from its design text:
  * text_tokens (Phase 1 design 3, verbatim regular expression and `plain`; continuation lines lose their leading markers: P1 13.4 item 11);
  * line_key (0a.2: the letters and digits after the leading markers, case-folded);
  * added_words and listed_added_words (Phase 2 design 3 and 10.1 item 4);
  * tiers (0a 3.1-3.2; P1 13.4 item 7); message times (a message id's stamp).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

TOKEN = re.compile(r"\d+(?:[.,:/-]\d+)*|[^\W\d_]+|[^\w\s.,;:!?'\"()\[\]*_`]")
MARKER = re.compile(r"^\s*(?:#{1,6}\s+|[-*+•]\s+|\d+[.)]\s+|\[[ xX]\]\s+)+")
STAMP = re.compile(r"^(\d{8})T(\d{6})(\d{6})")
ROOT = "root"
VERIFIER_TITLES = ("Independent Reviewer", "Independent Fact-Checker", "Code Reviewer", "Independent Data Checker", "Tester")


def strip_markers(line: str) -> str:
    return MARKER.sub("", line, count=1)


def plain(line: str) -> str:
    return re.sub(r"^\s*#+", "", line.replace("~~", ""))


def text_tokens(t: str) -> list[str]:
    return [tok for i, line in enumerate(t.splitlines()) for tok in TOKEN.findall(plain(strip_markers(line) if i else line).casefold())]


def line_key(line: str) -> str:
    return "".join(ch for ch in strip_markers(line).casefold() if ch.isalnum())


def added_words(text: str, quote: str, asked: str | None) -> list[str]:
    have = set(text_tokens(quote)) | set(text_tokens(asked or ""))
    out: list[str] = []
    for tok in text_tokens(text):
        if tok not in have and tok not in out:
            out.append(tok)
    return out


def listed_added_words(added: list[str]) -> str:
    if not added:
        return "none"
    parts = added[:8] + ([f"+{len(added) - 8} more"] if len(added) > 8 else [])
    return ", ".join(parts)  # the list joined by ", ", the overflow as its last part (as the throwaway org's PLAN FOR YOU renders it)


def split_fm(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            try:
                meta = yaml.safe_load(text[4:end]) or {}
            except yaml.YAMLError:
                meta = {}
            return (meta if isinstance(meta, dict) else {}), text[end + 4:].lstrip("\n")
    return {}, text


def parse_time(v) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).strip().strip("'\"")
    m = STAMP.match(s)
    if m and "-" not in s[:8]:
        d, t, us = m.groups()
        return datetime(int(d[:4]), int(d[4:6]), int(d[6:]), int(t[:2]), int(t[2:4]), int(t[4:]), int(us), tzinfo=timezone.utc)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def msg_time(mid: str) -> datetime | None:
    return parse_time(mid)


def tier(meta: dict) -> str:
    if meta.get("from") != ROOT:
        return "agent"
    src = meta.get("source")
    if src is None or src == "" or src == "human":
        return "human"
    return "relayed"


class Msg:
    __slots__ = ("id", "meta", "body", "path")

    def __init__(self, path: Path):
        self.path = path
        self.meta, self.body = split_fm(path.read_text(errors="replace"))
        self.id = str(self.meta.get("id") or path.stem)

    def get(self, k, d=None):
        return self.meta.get(k, d)

    @property
    def time(self):
        return msg_time(self.id)

    def section(self, heading: str) -> list[str]:
        out, on = [], False
        for ln in self.body.splitlines():
            if ln.startswith("## "):
                on = ln[3:].strip().lower() == heading.lower()
                continue
            if on and ln.strip():
                out.append(ln)
        return out


def read_msgs(dirs) -> dict[str, Msg]:
    out: dict[str, Msg] = {}
    for d in dirs:
        d = Path(d)
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            m = Msg(p)
            out.setdefault(m.id, m)
    return out


def org_msgs(org: Path) -> dict[str, Msg]:
    """Every message file of an org (root's and every agent's sent, inbox and read folders), by id."""
    dirs = [p for p in org.rglob("*") if p.is_dir() and p.name in ("sent", "inbox", "read") and ".git" not in p.parts
            and ".retired" not in p.parts]
    return read_msgs(sorted(dirs))


def evidence_msgs(stream: Path) -> dict[str, Msg]:
    """The stream evidence copy's messages (copy_org_evidence.sh's msgs/<folder>/)."""
    return read_msgs(sorted(p for p in (stream / "msgs").glob("*") if p.is_dir()))


def jdump(o) -> str:
    return json.dumps(o, indent=1, sort_keys=True, default=str)
