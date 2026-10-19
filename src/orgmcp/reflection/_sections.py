"""The sections of an owner's run prompt that come from its services: the list, the playbooks, and what to reflect on first."""

from __future__ import annotations

from collections.abc import Sequence

from ..kernel import RENDER_BODY_CHARS, Message
from ..mail import MailboxReader, TaskQuery
from ..services import Contract, ServiceCatalog, playbook_word_cap
from ._ports import ConfigSource, PlaybookSection, RejectedServices, ReflectSection, ServicePaths
from .api import CaseHistory, ReflectionDigest, ServicePromptSections


def _quoted(text: str, where: str) -> str:
    """A playbook shown in the prompt: quoted, so its headings do not mix with the prompt's, cut like messages."""
    raise NotImplementedError  # red: C-reflection


class MailRejectedServices(RejectedServices):
    """A rejection is a ``feedback: reject`` note in the batch, a reply to a request the owner received."""

    def __init__(self, mail: MailboxReader) -> None:
        self._mail = mail

    def among(self, addr: str, batch: Sequence[Message]) -> set[str]:
        raise NotImplementedError  # red: C-reflection


class QuotedPlaybookSection(PlaybookSection):
    """The playbook of a service with an open request, quoted; or what to do while there is none."""

    def __init__(self, catalog: ServiceCatalog, paths: ServicePaths) -> None:
        self._catalog = catalog
        self._paths = paths

    def section(self, addr: str, contract: Contract, *, reflecting: bool = False) -> str:
        raise NotImplementedError  # red: C-reflection


class EvidenceReflectSection(ReflectSection):
    """The steps the owner takes before the work: read the evidence, revise the playbook if it would prevent the problem (unless it is locked)."""

    def __init__(self, catalog: ServiceCatalog, config: ConfigSource, paths: ServicePaths) -> None:
        self._catalog = catalog
        self._config = config
        self._paths = paths

    def section(self, addr: str, contract: Contract, digest: str, *, rejected: bool = False, new_request: bool = True) -> str:
        raise NotImplementedError  # red: C-reflection


class OwnerPromptSections(ServicePromptSections):
    """The services an agent owns, the playbook of each it is working on, and the reflection a new request or a rejection calls for."""

    def __init__(
        self, catalog: ServiceCatalog, history: CaseHistory, digest: ReflectionDigest, tasks: TaskQuery, rejections: RejectedServices,
        playbooks: PlaybookSection, reflections: ReflectSection, paths: ServicePaths,
    ) -> None:
        self._catalog = catalog
        self._history = history
        self._digest = digest
        self._tasks = tasks
        self._rejections = rejections
        self._playbooks = playbooks
        self._reflections = reflections
        self._paths = paths

    def prompt_sections(self, addr: str, batch: Sequence[Message]) -> str:
        raise NotImplementedError  # red: C-reflection
