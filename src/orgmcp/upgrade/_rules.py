"""The parts of an ORG.md that an upgrade tells apart: the frontmatter as written, the body, and the mission inside the body."""

from __future__ import annotations

from ..kernel import OrgError

MISSION_HEADING = "## Mission\n"
RULES_HEADING = "\n## How this organization works"


def split_raw(text: str) -> tuple[str, str]:
    """(frontmatter exactly as written including the closing line, body)."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[: end + 5], text[end + 5 :]
    return "", text


def extract_mission(body: str) -> str:
    """The mission text of an ORG.md body made from the rules template."""
    start = body.find(MISSION_HEADING)
    if start == -1:
        raise OrgError("ORG.md has no '## Mission' section, so the rules cannot be upgraded automatically; "
                       "edit ORG.md by hand")
    start += len(MISSION_HEADING)
    end = body.find(RULES_HEADING, start)
    if end == -1:  # the rules heading was edited away: stop at the next level-2 heading instead
        end = body.find("\n## ", start)
    return (body[start:] if end == -1 else body[start:end]).strip()
