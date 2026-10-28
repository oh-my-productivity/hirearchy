#!/usr/bin/env python3
"""F2 only: a renamed VIEW of F2's evidence for the frozen score_memos.py (the scorer's reading for an arm-F reported measure).

    python3 -B f2_renamed_view.py <EV>

Why. F2's team named its deliverable `<date>-memo.md` (SERVICE.md v1 `deliverable`, K3 "The file name each time is fine."), while the frozen
score_memos.py finds memos only as `memo-<date>.md` (its _VERSION_FILE, _INDEX_LINE, _COPY_SOURCE and final_files patterns). The frozen
scorer therefore reads 0 versions and 0 final memos in F2 (F2/measures/score_memos.txt). This is the same class of harness assumption as the
memo input's name (manager-decision-memo-input-name.md), which has no ruling for the deliverable's file name. No regression is a reported
measure in arm F (protocol 12.3; the manager's decision on M7), so this view decides no pass rule.

What. A copy of F2's evidence under scoring/F2/renamed-view/ in which `<date>-memo.md` and `<date>-memo.v<n>.<sha>.md` are renamed to
`memo-<date>.md` and `memo-<date>.v<n>.<sha>.md`, in file names (memos/, memos/versions/) and in the text of memos/versions/INDEX.txt,
deliverables-log.txt, org-git-log.txt and msgs/*/*.md. Nothing else changes; F2's own files are not touched. score_memos.py (frozen) then
runs on the view."""
import re
import shutil
import sys
from pathlib import Path

EV = Path(sys.argv[1]).resolve()
SRC, DST = EV / "F2", EV / "scoring" / "F2" / "renamed-view"
NAME = re.compile(r"(\d{4}-\d{2}-\d{2})-memo(\.v\d+\.[0-9a-f]+)?\.md")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("org-kiro-sessions", "ambient", "run-logs", "events"))
n_names = n_text = 0
for p in sorted(list((DST / "memos").rglob("*.md"))):
    new = NAME.sub(lambda m: f"memo-{m.group(1)}{m.group(2) or ''}.md", p.name)
    if new != p.name:
        p.rename(p.with_name(new))
        n_names += 1
for p in [DST / "memos" / "versions" / "INDEX.txt", DST / "deliverables-log.txt", DST / "org-git-log.txt", *(DST / "msgs").glob("*/*.md")]:
    t = p.read_text(errors="replace")
    u = NAME.sub(lambda m: f"memo-{m.group(1)}{m.group(2) or ''}.md", t)
    if u != t:
        p.write_text(u)
        n_text += 1
(DST.parent / "renamed-view-note.txt").write_text(
    f"F2 renamed view: {n_names} file names and {n_text} text files rewritten (<date>-memo -> memo-<date>); source {SRC}; nothing else changed. "
    "Used only for the arm-F reported no-regression reading (scoring/F2/measures-renamed/).\n")
print(f"renamed {n_names} files, rewrote {n_text} text files")
