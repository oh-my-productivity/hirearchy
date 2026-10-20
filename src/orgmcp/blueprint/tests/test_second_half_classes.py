"""The classes of the second half subclass the interface they implement (rule D: every class with behaviour is a Protocol's)."""

from __future__ import annotations

from orgmcp.blueprint import EXAMPLE_KINDS, api
from orgmcp.blueprint._accesswords import PlainAccessWords
from orgmcp.blueprint._applier import HiringBlueprintApplier
from orgmcp.blueprint._basis import ValidatedPlanBasis
from orgmcp.blueprint._charters import CharterWriter
from orgmcp.blueprint._details import TextPlanDetails
from orgmcp.blueprint._examples import TemplateBlueprintExamples
from orgmcp.blueprint._firsttask import FirstTaskGiver
from orgmcp.blueprint._identity import HashPlanIdentity
from orgmcp.blueprint._playbooks import StepsPlaybookWriter
from orgmcp.blueprint._protocols import (
    AccessWording,
    BuildUndoing,
    Charters,
    FirstTasking,
    PlanBasis,
    PlanDetailing,
    PlanWords,
    PlaybookWriting,
    ServiceDefining,
    TeamBuilding,
    UserPlanning,
)
from orgmcp.blueprint._provision import FsWorkspaceProvisioner
from orgmcp.blueprint._render import TextPlanRenderer
from orgmcp.blueprint._servicedef import PlaybookServiceDefiner
from orgmcp.blueprint._team import CharterTeamBuilder
from orgmcp.blueprint._undo import RetiringRollback
from orgmcp.blueprint._userplan import TextUserPlan
from orgmcp.blueprint._words import ServiceWords

CLASSES: list[tuple[type, type]] = [
    (PlainAccessWords, AccessWording), (HiringBlueprintApplier, api.BlueprintApplier), (ValidatedPlanBasis, PlanBasis), (CharterWriter, Charters),
    (TextPlanDetails, PlanDetailing), (TemplateBlueprintExamples, api.BlueprintExamples), (FirstTaskGiver, FirstTasking),
    (HashPlanIdentity, api.PlanIdentity), (StepsPlaybookWriter, PlaybookWriting), (FsWorkspaceProvisioner, api.WorkspaceProvisioner),
    (TextPlanRenderer, api.PlanRenderer), (PlaybookServiceDefiner, ServiceDefining), (CharterTeamBuilder, TeamBuilding),
    (RetiringRollback, BuildUndoing), (TextUserPlan, UserPlanning), (ServiceWords, PlanWords),
]


def test_every_class_of_the_second_half_subclasses_the_interface_it_implements() -> None:
    assert [cls.__name__ for cls, port in CLASSES if port not in cls.__mro__] == []


def test_the_kinds_of_example_are_the_four_the_templates_come_in() -> None:
    assert EXAMPLE_KINDS == ("research", "documents", "code", "analysis")
