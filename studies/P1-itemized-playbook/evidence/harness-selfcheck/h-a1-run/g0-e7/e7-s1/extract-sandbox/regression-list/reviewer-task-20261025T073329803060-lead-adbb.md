

Regression list (client rejections, verbatim; check the memo against each):
- R1, case 20261025T070423629042-root-5efc, verdict 20261025T071537817238-root-905b, about C9: "No, not right yet. Always start the memo with a one-line 'Summary:' of the meeting, then the decisions, then the action items."

## Acceptance criteria
- C1: Built only from the requested notes file; the other notes files are not used.
- C3: Decisions lists every decision the notes state, one bullet each, and no item the notes do not present as decided.
- C4: Actions is a markdown table with the columns Owner | Action | Due. It has one row for every commitment in the notes, including informal ones in prose (someone says they will do something, offers to, or agrees to), not only lines labelled ACTION.
- C5: Every Owner is a person named in the notes.
- C6: Every Due value is an ISO date (YYYY-MM-DD) when the notes give a date, or give a relative deadline that points to one clear day counted from the meeting date; otherwise it is the word none. No date is guessed.
- C7: At most 400 words as counted by read.
- C9: The memo has a title line with the meeting date, then a one-line 'Summary:' of the meeting, then a Decisions section, then an Actions section, and nothing else (no attendee list, no discussion recap).
- Client changes: Marta 'Keep the agenda as sent' row removed; Lee Due = 2026-10-30; Sam Due = none; everything else identical to the previous version.
- R1 from the regression list holds.

## Inputs
- lead/writer/work/memo-2026-10-19.md
- /private/tmp/hirearchy-e7-s1-1792911600/notes/2026-10-19.md
