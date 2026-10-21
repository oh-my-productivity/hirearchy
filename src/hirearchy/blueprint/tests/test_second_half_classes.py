"""The classes of the second half subclass the interface they implement (rule D: every class with behaviour is a Protocol's)."""

from __future__ import annotations

from hirearchy.blueprint import EXAMPLE_KINDS, api
from hirearchy.blueprint._accesswords import PlainAccessWords
from hirearchy.blueprint._applier import HiringBlueprintApplier
from hirearchy.blueprint._basis import ValidatedPlanBasis
from hirearchy.blueprint._charters import CharterWriter
from hirearchy.blueprint._details import TextPlanDetails
from hirearchy.blueprint._examples import TemplateBlueprintExamples
from hirearchy.blueprint._firsttask import FirstTaskGiver
from hirearchy.blueprint._identity import HashPlanIdentity
from hirearchy.blueprint._playbooks import StepsPlaybookWriter
from hirearchy.blueprint._protocols import (
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
from hirearchy.blueprint._provision import FsWorkspaceProvisioner
from hirearchy.blueprint._render import TextPlanRenderer
from hirearchy.blueprint._servicedef import PlaybookServiceDefiner
from hirearchy.blueprint._team import CharterTeamBuilder
from hirearchy.blueprint._undo import RetiringRollback
from hirearchy.blueprint._userplan import TextUserPlan
from hirearchy.blueprint._words import ServiceWords

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
