"""``CaseJudgedVersions``: the delivery the client judged, and what relayed reworks changed after it, derived from the cases and the team's checked versions."""

from __future__ import annotations

from ..kernel import ROOT, Message, artifact_paths, latest_results
from ..mail import MailboxReader
from ..services import JUDGED_BYTES, JudgedBase, JudgedVersions
from ._deliverable_checks import PATHS_PER_RESULT, _in_the_organization
from ._ports import CheckedVersions
from .api import Case, CaseHistory


class CaseJudgedVersions(JudgedVersions):
    """The judged delivery ``J`` of a case is the latest result, before the client's latest human verdict, of the task that verdict is on; with no
    human verdict, the latest ``done`` result of a task that was not a relayed rework. The relayed reworks sent after ``J`` changed an artifact of
    ``J`` when the file now differs from the version git holds for ``J``, or, where git does not know it, when a result of a relayed rework lists it."""

    def __init__(self, history: CaseHistory, mail: MailboxReader, versions: CheckedVersions) -> None:
        self._history = history
        self._mail = mail
        self._versions = versions

    def base(self, owner: str, service: str, revises: str) -> JudgedBase | None:
        case = next((c for c in self._history.cases(owner, service) if revises in {t.id for t in c.tasks}), None)
        if case is None:
            return None
        results = [m for m in self._mail.received(ROOT) if m.type == "result"]
        judged = self._judged(case, results)
        if judged is None:
            return None
        relayed = tuple(t.id for t in case.tasks if t.source == "relayed" and t.id > judged.id)
        if not relayed:
            return None
        paths = [p for p in dict.fromkeys(artifact_paths(judged.body)[:PATHS_PER_RESULT]) if _in_the_organization(p)]
        commits: dict[str, str] = {}
        changed = tuple(p for p in paths if self._changed(judged, p, relayed, results, commits))
        if not changed:
            return None
        commit = next((commits[p] for p in changed if p in commits), "")
        return JudgedBase(judged.reply_to or "", judged.id, commit, relayed, changed, self._texts(changed, commits))

    def _judged(self, case: Case, results: list[Message]) -> Message | None:
        human = [v for v in case.verdicts if v.tier == "human"]
        if human:
            verdict = max(human, key=lambda v: v.message.id)
            before = [r for r in results if r.reply_to == verdict.task_id and r.id < verdict.message.id]
            return max(before, key=lambda r: r.id, default=None)
        plain = {t.id for t in case.tasks if t.source != "relayed"}
        latest = latest_results(r for r in results if r.reply_to in plain)
        done = [r for r in latest.values() if r.status == "done"]
        return max(done, key=lambda r: r.id, default=None)

    def _changed(self, judged: Message, path: str, relayed: tuple[str, ...], results: list[Message], commits: dict[str, str]) -> bool:
        checked = self._versions.at_result(judged, path)
        if checked is None:  # git does not know the judged version: only what the relayed results themselves list
            return any(r.reply_to in relayed and path in artifact_paths(r.body) for r in results)
        commits[path] = checked[0]
        return self._versions.current(path, len(checked[1])) != checked[1]

    def _texts(self, changed: tuple[str, ...], commits: dict[str, str]) -> tuple[tuple[str, str], ...]:
        texts: list[tuple[str, str]] = []
        used = 0
        for path in changed:
            commit = commits.get(path)
            data = None if commit is None else self._versions.text(commit, path, JUDGED_BYTES)
            if data is not None and used + len(data) <= JUDGED_BYTES:
                used += len(data)
                texts.append((path, data.decode("utf-8", errors="replace")))
        return tuple(texts)
