"""``readable_config``: the settings of ORG.md, or an ``OrgError`` that names ORG.md when its settings block cannot be read."""

from __future__ import annotations

import pytest

from hirearchy.kernel import OrgError
from hirearchy.settings import readable_config
from hirearchy.settings.testing import MemoryOrgSettings

BROKEN = "---\nmax_depth: 4\nextra_allowed_models: [claude-sonnet-4.6\n---\n# Organization\n"  # a hand edit slipped: the YAML does not parse


def test_the_settings_of_a_readable_ORG_md_are_returned_as_they_are() -> None:
    settings = MemoryOrgSettings("---\nmax_depth: 7\n---\n# Organization\n")
    assert readable_config(settings) == settings.config() and readable_config(settings)["max_depth"] == 7


@pytest.mark.parametrize("text", [BROKEN, None], ids=["yaml-does-not-parse", "no-document"])
def test_an_ORG_md_that_cannot_be_read_is_an_OrgError_that_names_it(text: str | None) -> None:
    with pytest.raises(OrgError) as refused:
        readable_config(MemoryOrgSettings(text))
    message = str(refused.value)
    assert message.startswith("ORG.md cannot be read") and "repair" in message
    assert "\n" not in message and "while parsing" not in message and "<unicode string>" not in message  # not the parser's own text
