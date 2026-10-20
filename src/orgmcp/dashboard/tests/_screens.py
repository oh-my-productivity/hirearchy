"""Every screen of the dashboard as plain text: what the goldens in ``golden/`` hold, and how they are taken.

A screen is read from the compositor of the app the way the terminal would draw it (one line per row, trailing blanks cut), after the keys of a step were
pressed and the refresh they started has finished (``DashApp.settle``): nothing here waits for a time to pass, so the text does not depend on how
fast the machine is. The app is shown a fixed time (``DEMO_NOW``) and has a fixed size, the demo organization is built under a frozen clock with
ids that are the same every time (``tests/testkit/dash_fixtures.py``), and the only thing that varies - the directory the organization was made in - is
replaced by ``/path/to/acme``.

``capture`` takes a *function that makes the app*, so the same steps are taken over the app of the flat module (the goldens were taken before it
became a package), over the app of the legacy constructor and over an app that was given its queries.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from textual.app import App
from textual.pilot import Pilot

GOLDEN = Path(__file__).resolve().parent / "golden"
SHOWN_AS = "/path/to/acme"

WIDE = (150, 42)  # the size of the screenshots in studies/DASH-screens
NARROW = (80, 24)  # the smallest terminal the tree is made to fit
SMALL = (100, 30)

FOCUS = "@focus "  # a step "@focus #pane-messages" moves the focus there (what a click or a tab would do)

# (name of the golden, what is done before the screen is taken): key names of ``Pilot.press`` or "@focus <selector>"
DEMO_WIDE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wide-1-org-root", ()),
    ("wide-1-org-ceo-overview", ("down", "down")),
    ("wide-1-org-ceo-activity", ("]",)),
    ("wide-1-org-ceo-activity-raw", ("x",)),
    ("wide-1-org-ceo-messages", ("x", "]")),
    ("wide-1-org-ceo-message-open", ("@focus #pane-messages", "enter")),
    ("wide-1-org-ceo-runlog", ("escape", "@focus #agent-tree", "]")),
    ("wide-1-org-ceo-memory", ("]",)),
    ("wide-1-org-ceo-charter", ("]",)),
    ("wide-1-org-deploy-runlog", ("@focus #agent-tree", *("down",) * 5, *("]",) * 4)),
    ("wide-1-org-crawler-overview", ("@focus #agent-tree", "G", "[", "[", "[")),
    ("wide-2-workflows", ("2",)),
    ("wide-2-workflows-trace", ("enter",)),
    ("wide-3-services", ("escape", "3")),
    ("wide-3-services-detail", ("enter",)),
    ("wide-4-events", ("escape", "4")),
    ("wide-4-events-errors", ("e",)),
    ("wide-4-events-raw", ("x",)),
    ("wide-4-events-filter", ("x", "e", "slash", *"research")),
    ("wide-5-health", ("escape", "5")),
    ("wide-5-health-checked", ("c",)),
    ("wide-help", ("question_mark",)),
)

DEMO_NARROW: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("narrow-1-org-root", ()),
    ("narrow-1-org-ceo-overview", ("down", "down")),
    ("narrow-2-workflows", ("2",)),
    ("narrow-3-services", ("3",)),
    ("narrow-4-events", ("4",)),
    ("narrow-5-health", ("5",)),
)

EMPTY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("empty-1-org-root", ()),
    ("empty-2-workflows", ("2",)),
    ("empty-3-services", ("3",)),
    ("empty-4-events", ("4",)),
    ("empty-5-health", ("5",)),
    ("empty-help", ("question_mark",)),
)


def plain(app: App[None]) -> str:
    """The screen the way the terminal shows it: one line per row, without the trailing blanks."""
    rows = app.screen._compositor.render_strips()
    return "\n".join(strip.text.rstrip() for strip in rows) + "\n"


async def settled(app: App[None], pilot: Pilot[None]) -> None:
    settle = getattr(app, "settle")
    await settle(pilot)


async def until(app: App[None], pilot: Pilot[None], done: Callable[[], bool], what: str, tries: int = 1000) -> None:
    """Let the app run until ``done()``; no fixed time is slept, the loop gives up after ``tries`` turns."""
    for _ in range(tries):
        await settled(app, pilot)
        if done():
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"the screen never showed {what}")


def _pane(app: App[None], selector: str) -> str:
    return str(getattr(app.query_one(selector), "text_now", ""))


async def stable(app: App[None], pilot: Pilot[None], tries: int = 200) -> str:
    """The screen once it has stopped changing: a table or a pane is painted a turn after the refresh that filled it, and on a loaded machine that turn can
    come late. No time is waited; the loop ends when two reads, with the app idle in between, are the same."""
    before = plain(app)
    for _ in range(tries):
        await settled(app, pilot)
        await pilot.pause()
        after = plain(app)
        if after == before:
            return after
        before = after
    raise AssertionError("the screen never stopped changing")


async def press(app: App[None], pilot: Pilot[None], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key.startswith(FOCUS):
            app.query_one(key.removeprefix(FOCUS)).focus()
        else:
            await pilot.press(key)
        await settled(app, pilot)


async def arrived(app: App[None], pilot: Pilot[None], name: str) -> None:
    """The slow things a step starts (the trace of a request, the consistency check) are waited for until they are on the screen."""
    if name.endswith("workflows-trace"):
        await until(app, pilot, lambda: bool(_pane(app, "#flows-detail")) and not _pane(app, "#flows-detail").startswith("computing"), "the trace")
    elif name.endswith("health-checked"):
        await until(app, pilot, lambda: "checked at" in _pane(app, "#health-body"), "the result of the check")


def capture(make_app: Callable[[], App[None]], steps: tuple[tuple[str, tuple[str, ...]], ...], size: tuple[int, int], root: Path) -> dict[str, str]:
    """The screens of ``steps`` in order, by name, with the directory of the organization written ``/path/to/acme``."""
    seen: dict[str, str] = {}
    hidden = {str(root), str(root.resolve())}

    async def go() -> None:
        app = make_app()
        app.animation_level = "none"  # (the underline of the tabs slides to the new tab; the screen is taken when it has arrived)
        async with app.run_test(size=size) as pilot:
            await settled(app, pilot)
            for name, keys in steps:
                await press(app, pilot, keys)
                await arrived(app, pilot, name)
                text = await stable(app, pilot)
                failed = getattr(app, "last_error", None)
                assert failed is None, f"{name}: the refresh failed: {failed}\n{text}"
                for path in sorted(hidden, key=len, reverse=True):
                    text = text.replace(path, SHOWN_AS)
                seen[name] = text

    asyncio.run(go())
    return seen


def golden_path(name: str) -> Path:
    return GOLDEN / f"{name}.txt"


def demo_screens(make_app: Callable[[Path], App[None]], root: Path) -> dict[str, str]:
    """The wide and the narrow screens of the demo organization at ``root``: ``make_app(root)`` makes a new app each time."""
    return {
        **capture(lambda: make_app(root), DEMO_WIDE, WIDE, root),
        **capture(lambda: make_app(root), DEMO_NARROW, NARROW, root),
    }


def empty_screens(make_app: Callable[[Path], App[None]], root: Path) -> dict[str, str]:
    """The screens of an organization that has only its root."""
    return capture(lambda: make_app(root), EMPTY, SMALL, root)
