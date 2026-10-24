"""Providers of the ``services`` ports (ARCHITECTURE.md 6.1), and of ``ReworkContext``, the port of ``dispatch`` that ``services`` implements.

The collaborators among the rules of the package (where the files are, who the owner is, what a playbook text may be, how a playbook is written,
what an amendment changes, how a request is worded, and the parts the commands are made of) are private to it: they are made here, inside the
providers of the ports that use them."""

from __future__ import annotations

from ..agents import AgentDirectory, RetiredArchive
from ..delivery import MessageDelivery
from ..dispatch import MessageSender, ReworkContext
from ..kernel import AtomicWriter, Clock, EventSink, OrgLayout
from ..mail import MailboxReader
from ..services import CaseAllowance, ContractNormalizer, JudgedVersions, ServiceCatalog, ServiceCommands, ServiceEvidence, ServiceHints, ServiceStore
from ..services._amend import ContractAmender
from ..services._catalog import ContractServiceCatalog
from ..services._commands import RuleServiceCommands
from ..services._continue import RecordedContinuations
from ..services._define import RuleContractDefiner
from ..services._feedback import RuleClientFeedback, SenderLinkNotes
from ..services._hints import ServiceReportHints
from ..services._normalizer import TextContractNormalizer
from ..services._places import OrgServicePlaces
from ..services._playbook import RulePlaybookReviser
from ..services._request import RuleServiceRequester, TextRequestBodies
from ..services._retire import RuleServiceRetirement
from ..services._rework import ServiceReworkContext
from ..services._store import FsServiceStore, OsServiceFiles
from ..services._texts import CappedPlaybookTexts, DirectReportOwners, EventedPlaybookWriter
from ..settings import OrgSettings
from ._builder import Builder


def register(b: Builder) -> None:
    b.provide(ServiceStore, lambda b: FsServiceStore(OrgServicePlaces(b.get(OrgLayout)), b.get(AtomicWriter)))
    b.provide(
        ServiceCatalog,
        lambda b: ContractServiceCatalog(b.get(ServiceStore), b.get(AgentDirectory), OrgServicePlaces(b.get(OrgLayout))),
    )
    b.provide(ContractNormalizer, lambda b: TextContractNormalizer())
    b.provide(ServiceHints, lambda b: ServiceReportHints(b.get(ServiceCatalog)))
    b.provide(
        ReworkContext, lambda b: ServiceReworkContext(b.get(MailboxReader), b.get(AgentDirectory), b.get(ServiceCatalog)),
    )
    b.provide(ServiceCommands, _commands)


def _commands(b: Builder) -> ServiceCommands:
    agents, catalog, store = b.get(AgentDirectory), b.get(ServiceCatalog), b.get(ServiceStore)
    delivery, clock, events = b.get(MessageDelivery), b.get(Clock), b.get(EventSink)
    places, owners = OrgServicePlaces(b.get(OrgLayout)), DirectReportOwners(agents)
    texts, playbooks = CappedPlaybookTexts(b.get(OrgSettings)), EventedPlaybookWriter(store, clock, events)
    sender, mail = b.get(MessageSender), b.get(MailboxReader)
    restorer = FsServiceStore(places, b.get(AtomicWriter))  # the same single writer of <owner>/services/**, as the port that puts a retired copy back
    return RuleServiceCommands(
        RuleContractDefiner(
            agents, catalog, store, places, b.get(ContractNormalizer), ContractAmender(), texts, owners, playbooks, delivery, clock, events,
            b.get(ServiceEvidence), SenderLinkNotes(sender), RecordedContinuations(places, b.get(RetiredArchive), mail, OsServiceFiles()), restorer,
        ),
        RuleServiceRetirement(agents, catalog, store, owners, delivery, clock, events, b.get(ServiceEvidence)),
        RulePlaybookReviser(agents, catalog, texts, playbooks, delivery, b.get(ServiceEvidence)),
        RuleServiceRequester(agents, catalog, mail, TextRequestBodies(), sender, b.get(JudgedVersions), b.get(CaseAllowance)),
        RuleClientFeedback(agents, mail, sender, b.get(ServiceEvidence), store),
    )
