"""The old module-level names of ``orgmcp.services`` are still exported (until step E3)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from orgmcp import services

OLD_NAMES = """
INPUT_RE VERDICTS DESCRIPTION_MAX REASON_MAX FEEDBACK_MAX TITLE_MAX DELIVERABLE_KEYS DIGEST_CASES DIGEST_CHARS FEEDBACK_HEADER CLIP_LESSON
CLIP_NOTE MAX_VERDICTS Contract Playbook service_dir read_contract read_playbook owned_services requestable_services parse_input_spec
define_service retire_service revise_playbook report_hint request rework_fields feedback_text feedback Case Verdict Stats playbook_timeline
version_at lessons_of cases summarize stats_by_version reflection_digest case_of case_total services_text prompt_sections
""".split()


def test_every_old_name_is_still_exported() -> None:
    assert [n for n in OLD_NAMES if not hasattr(services, n)] == []


def test_the_private_names_that_callers_still_use_are_reachable() -> None:
    assert callable(services._inputs) and callable(services._deliverable) and callable(services._verdict_chain) and callable(services._case_line)
    assert callable(services._clip)


def test_the_api_names_are_exported_next_to_the_old_ones() -> None:
    assert {"ServiceStore", "ServiceCatalog", "ServiceCommands", "ServiceHints", "ContractNormalizer"} <= set(services.__all__)


def test_the_title_limit_is_eighty_characters() -> None:
    assert services.TITLE_MAX == 80


def test_the_input_spec_and_the_normalizers_need_no_org() -> None:
    assert services.parse_input_spec("topic*:what") == {"name": "topic", "description": "what", "required": True}
    assert services._inputs(["a"]) == [{"name": "a", "description": "", "required": False}]
    assert services._deliverable({"description": "d"}) == {"description": "d"}


def test_the_service_directory_is_below_the_owner() -> None:
    org = SimpleNamespace(dir=lambda addr: Path("/memory/org") / addr)
    assert services.service_dir(org, "ceo", "brief") == Path("/memory/org/ceo/services/brief")


def test_the_adapter_of_the_feedback_keeps_the_text_the_tool_shows() -> None:
    assert "replaces" not in (services.feedback.__doc__ or "") and "stays in the case" in (services.feedback.__doc__ or "")
