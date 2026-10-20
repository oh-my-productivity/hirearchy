# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from testkit.legacy.orgmcp.core import DEFAULT_MODEL


def test_create_org_without_a_model_uses_the_default(tmp_path, monkeypatch):
    from testkit.legacy.orgmcp.server import resolve_binding

    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "new"))
    binding, _ = resolve_binding()
    org = binding.create("A mission")
    assert org.config["default_model"] == DEFAULT_MODEL
