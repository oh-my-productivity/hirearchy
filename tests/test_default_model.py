"""Every agent runs on claude-sonnet-5.5 unless its charter or the org config names another model."""

from orgmcp.core import DEFAULT_MODEL


def test_create_org_without_a_model_uses_the_default(tmp_path, monkeypatch):
    from orgmcp.server import resolve_binding

    monkeypatch.setenv("ORG_ROOT", str(tmp_path / "new"))
    binding, _ = resolve_binding()
    org = binding.create("A mission")
    assert org.config["default_model"] == DEFAULT_MODEL
