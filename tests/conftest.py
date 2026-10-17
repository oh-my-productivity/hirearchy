import pytest

from orgmcp.core import ROOT, Org


@pytest.fixture
def org(tmp_path):
    """root -> ceo (manager, can hire) -> eng (worker)."""
    o = Org.init(tmp_path / "org", "Test mission", {"poll_seconds": 0.05})
    o.hire(ROOT, "ceo", "Chief executive", "Run the company.", can_hire=True, max_children=2)
    o.hire("ceo", "eng", "Engineer", "Build things.")
    return o
