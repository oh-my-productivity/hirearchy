"""The base error of the organization's rules."""

from __future__ import annotations


class OrgError(ValueError):
    """A rule of the organization was violated. The message is shown to the agent."""
