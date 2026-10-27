"""The reply ``revise_playbook`` gives its owner (design 5.2), built from the ``PlaybookChange`` alone. Pure: no file is read."""

from __future__ import annotations

from .api import PlaybookChange

TOLD = "{client} was told without being woken."
STARTS_NEW = "It starts new and is watched: a related client rejection warns it, a second retires it."
ACK_IGNORED = " (acknowledged={id} was not needed for this change and is not recorded.)"
WATCH_UNREAD = "Its watch state is in your prompt's playbook section."
NO_ITEMS = ' The playbook has no items now: add one (op="add") when the evidence calls for it.'


def playbook_reply(service: str, change: PlaybookChange) -> str:
    """What the owner reads after a change (5.2): the version, what the op did to which item and how it was admitted, the watch sentence, the
    clause of an ``acknowledged`` the change did not need and who was told. A migration that ran first starts the reply."""
    c = change
    on = ", ".join(c.admission.why or c.admission.evidence)
    old = ", ".join(c.carried_related or c.related)
    carried = f"; it continues the watch of {c.carried}: warning ({old}), one more related rejection retires it" if c.carried else ""
    own = ", ".join(r for r in c.related if r not in c.carried_related)
    if c.op == "first":
        done = f"wrote playbook v1: {c.items} items ({', '.join(c.sections) or 'none'})."
    elif c.op == "add":
        watch = WATCH_UNREAD if c.watch_unread else f"It continues the watch of {c.carried}: warning ({old}); one more related rejection retires it." if c.carried else STARTS_NEW
        done = f"added {c.item} ({c.kind}), admitted ({c.admission.rule}) on {on}. {watch}"
    elif c.op == "edit" and c.formatting:
        done = f"fixed the formatting of {c.item} (no evidence needed; its state is unchanged)."
    elif c.op == "edit":
        stays = f"; its warning stays ({own}): one more related rejection retires it" if own else ""
        watch = WATCH_UNREAD if c.watch_unread else f"Its watch starts again{stays}{carried}."
        done = f"edited {c.item}, admitted ({c.admission.rule}) on {on}. {watch}"
    elif c.op == "restore":
        how = f" (written by {c.client}: no evidence needed)" if c.admission.rule == "restore" else f", admitted ({c.admission.rule}) on {on}"
        done = f"restored {c.item} to the text of v{c.restored_from}{how}{carried}." + (f" {WATCH_UNREAD}" if c.watch_unread else "")
    elif c.op == "move":
        done = f"moved {c.item} after {c.after} (no evidence needed)."
    else:
        done = f"retired {c.item}."
    ack = ACK_IGNORED.format(id=c.ack_ignored) if c.ack_ignored else ""
    end = NO_ITEMS if c.op == "retire" and c.items == 0 else ""
    return f"{c.migration}playbook of {service} is now v{c.version}: {done}{ack} {TOLD.format(client=c.client)}{end}"
