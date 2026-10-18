"""``Builder``: providers register factories, ``get`` builds each port once, overrides win, mistakes are loud."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pytest

from orgmcp.app._builder import Builder, BuilderError, DependencyCycle, DuplicateProvider, NotProvided


class Greeter(Protocol):
    def greet(self) -> str: ...


class Shouter(Protocol):
    def shout(self) -> str: ...


class Left(Protocol):
    def left(self) -> str: ...


class Right(Protocol):
    def right(self) -> str: ...


class English(Greeter):
    def greet(self) -> str:
        return "hello"


class French(Greeter):
    def greet(self) -> str:
        return "bonjour"


class Loud(Shouter):
    def __init__(self, greeter: Greeter) -> None:
        self.greeter = greeter

    def shout(self) -> str:
        return self.greeter.greet().upper()


class Counting:
    """A factory that counts its calls."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, b: Builder) -> Greeter:
        self.calls += 1
        return English()


def builder(tmp_path: Path, overrides: dict[type, object] | None = None) -> Builder:
    return Builder(tmp_path, overrides)


def test_get_returns_what_the_provider_built(tmp_path: Path) -> None:
    b = builder(tmp_path)
    b.provide(Greeter, lambda _: English())
    assert b.get(Greeter).greet() == "hello"


def test_the_root_is_the_one_the_builder_was_made_for(tmp_path: Path) -> None:
    assert builder(tmp_path).root == tmp_path


def test_provide_is_lazy_and_get_builds_once(tmp_path: Path) -> None:
    b, factory = builder(tmp_path), Counting()
    b.provide(Greeter, factory)
    assert factory.calls == 0
    first = b.get(Greeter)
    assert b.get(Greeter) is first and factory.calls == 1


def test_a_provider_asks_the_builder_for_its_collaborators(tmp_path: Path) -> None:
    b = builder(tmp_path)
    b.provide(Shouter, lambda b: Loud(b.get(Greeter)))  # registered before the collaborator: order is irrelevant
    b.provide(Greeter, lambda _: English())
    assert b.get(Shouter).shout() == "HELLO"


def test_a_shared_collaborator_is_one_object(tmp_path: Path) -> None:
    b = builder(tmp_path)
    b.provide(Greeter, lambda _: English())
    b.provide(Shouter, lambda b: Loud(b.get(Greeter)))
    assert b.get(Shouter).greeter is b.get(Greeter)  # type: ignore[attr-defined]


def test_two_builders_do_not_share_objects(tmp_path: Path) -> None:
    one, two = builder(tmp_path), builder(tmp_path)
    for b in (one, two):
        b.provide(Greeter, lambda _: English())
    assert one.get(Greeter) is not two.get(Greeter)


def test_an_override_replaces_the_provider_without_running_it(tmp_path: Path) -> None:
    fake, factory = French(), Counting()
    b = builder(tmp_path, {Greeter: fake})
    b.provide(Greeter, factory)  # a wire module does not know it is overridden
    assert b.get(Greeter) is fake and factory.calls == 0


def test_an_override_needs_no_provider_and_reaches_the_collaborators(tmp_path: Path) -> None:
    b = builder(tmp_path, {Greeter: French()})
    b.provide(Shouter, lambda b: Loud(b.get(Greeter)))
    assert b.get(Shouter).shout() == "BONJOUR"


def test_an_unknown_port_is_reported_by_name(tmp_path: Path) -> None:
    with pytest.raises(NotProvided, match="Greeter"):
        builder(tmp_path).get(Greeter)


def test_not_provided_is_a_lookup_error_and_a_builder_error(tmp_path: Path) -> None:
    with pytest.raises(LookupError):
        builder(tmp_path).get(Greeter)
    assert issubclass(NotProvided, BuilderError)


def test_two_providers_for_one_port_are_refused(tmp_path: Path) -> None:
    b = builder(tmp_path)
    b.provide(Greeter, lambda _: English())
    with pytest.raises(DuplicateProvider, match="Greeter"):
        b.provide(Greeter, lambda _: French())


def test_a_cycle_is_reported_with_its_path(tmp_path: Path) -> None:
    b = builder(tmp_path)

    class A(Left):
        def left(self) -> str:
            return "a"

    class B(Right):
        def right(self) -> str:
            return "b"

    b.provide(Left, lambda b: (b.get(Right), A())[1])
    b.provide(Right, lambda b: (b.get(Left), B())[1])
    with pytest.raises(DependencyCycle, match=r"Left.*Right.*Left"):
        b.get(Left)


def test_a_port_that_needs_itself_is_a_cycle(tmp_path: Path) -> None:
    b = builder(tmp_path)
    b.provide(Greeter, lambda b: b.get(Greeter))
    with pytest.raises(DependencyCycle):
        b.get(Greeter)


def test_the_builder_is_usable_after_a_cycle_was_reported(tmp_path: Path) -> None:
    b = builder(tmp_path)
    b.provide(Greeter, lambda b: b.get(Greeter))
    b.provide(Shouter, lambda _: Loud(English()))
    with pytest.raises(DependencyCycle):
        b.get(Greeter)
    assert b.get(Shouter).shout() == "HELLO"


def test_a_failing_provider_is_not_cached(tmp_path: Path) -> None:
    b, attempts = builder(tmp_path), []

    def flaky(_: Builder) -> Greeter:
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("first attempt fails")
        return English()

    b.provide(Greeter, flaky)
    with pytest.raises(RuntimeError):
        b.get(Greeter)
    assert b.get(Greeter).greet() == "hello" and len(attempts) == 2
