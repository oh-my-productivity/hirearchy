"""The org-agent floor: the models an org agent may run on, the effort levels, and the one wording of every refusal.

Owner decision D-E4-9 (docs/design/org-agent-model-floor.md): claude-sonnet-5.5 is the minimum, at ``high`` effort or above. Every refusal
point (hire, blueprint, charter rewrite, org creation, ORG.md writes, the run command) calls the functions here, so the allowed ids, the
levels and the messages are written once. The set can only be widened by the user, with the ORG.md key ``extra_allowed_models``.
"""

from __future__ import annotations

from collections.abc import Mapping

from ._config import DEFAULT_EFFORT, config_default_model

DEFAULT_ALLOWED_MODELS = ("claude-sonnet-5.5", "claude-opus-5.5")  # the models org agents may run on, before the user widens the set
EFFORT_LEVELS = ("high", "xhigh", "max")  # the kiro efforts an org-agent run may use


def config_effort(config: Mapping[str, object] | None) -> str:
    """The ``effort`` of a config mapping, stripped as written (``null``, empty or missing = DEFAULT_EFFORT)."""
    return str((config or {}).get("effort") or "").strip() or DEFAULT_EFFORT


def config_allowed_models(config: Mapping[str, object] | None) -> tuple[str, ...]:
    """DEFAULT_ALLOWED_MODELS followed by the ids of ``extra_allowed_models`` (a list, or one id); blanks and non-text entries are ignored."""
    extra = (config or {}).get("extra_allowed_models")
    items = [extra] if isinstance(extra, str) else list(extra) if isinstance(extra, (list, tuple)) else []
    allowed = list(DEFAULT_ALLOWED_MODELS)
    for item in items:
        model = item.strip() if isinstance(item, str) else ""
        if model and model not in allowed:
            allowed.append(model)
    return tuple(allowed)


def model_floor_problem(config: Mapping[str, object] | None, model: str) -> str | None:
    """None when ``model`` is allowed by ``config``, else the refusal that names the allowed set."""
    allowed = config_allowed_models(config)
    if model in allowed:
        return None
    return f'model "{model}" is not allowed for org agents; allowed: {", ".join(allowed)} (only the user can widen this set)'


def effort_floor_problem(effort: str) -> str | None:
    """None when ``effort`` is one of EFFORT_LEVELS, else the refusal that names them."""
    if effort in EFFORT_LEVELS:
        return None
    return f'effort "{effort}" is not allowed for org agents; allowed: {", ".join(EFFORT_LEVELS)}'


def config_floor_problem(config: Mapping[str, object] | None, before: Mapping[str, object] | None = None) -> str | None:
    """The first refusal of a settings block: a widened set (only with ``before``), then the effort, then the default model.

    With ``before``, a value equal to the one ``before`` had is tolerated: an organization made before the floor keeps what it had.
    """
    if before is not None:
        added = [m for m in config_allowed_models(config) if m not in config_allowed_models(before)]
        if added:
            return f'only the user can widen the allowed models, by editing ORG.md themselves (not allowed now: {", ".join(added)})'
    effort = config_effort(config)
    if effort != (config_effort(before) if before is not None else None):
        problem = effort_floor_problem(effort)
        if problem:
            return problem
    default = config_default_model(config)
    if default != (config_default_model(before) if before is not None else None):
        problem = model_floor_problem(config, default)
        if problem:
            return f"default_model: {problem}"
    return None
