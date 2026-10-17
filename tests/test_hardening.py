import re

import pytest

from orgmcp.core import ROOT, OrgError


def h1s(text):
    return re.findall(r"^# .*$", text, flags=re.M)


@pytest.mark.parametrize(
    "charter, heading",
    [
        ("Build things.", "# Role: Builder"),
        ("# Role: Builder\n\nBuild things.", "# Role: Builder"),
        ("\n# Lead builder\n\nBuild things.\n", "# Lead builder"),
        ("## Duties\nBuild things.", "# Role: Builder"),  # a lower-level heading is not an H1
    ],
)
def test_charter_has_exactly_one_h1(org, charter, heading):
    addr = org.hire("ceo", "builder", "Builder", charter)
    _, body = org.charter(addr)
    assert h1s(body) == [heading]
    assert "Build things." in body
