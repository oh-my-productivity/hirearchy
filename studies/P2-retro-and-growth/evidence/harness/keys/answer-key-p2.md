# Answer key, P2 (private; never shown to the assistant or an org agent; protocol 2.1, 4.1-4.2)
Memos 1-3 are E7's key (`studies/P1-itemized-playbook/evidence/answer-key.md`, md5 2fb69bbef857c2bd4862cd5dd8be9da8); memos 4-6 are P1's
(`answer-key-p1.md`, md5 d340ff638fa7efe1a7ece8808d9a6168), with the P2 forms below. `score_p2.py` reads both through P1's `score_memos.py`
tables (`KEY`, `KEY_P1`), which hold the same decisions, actions, owners and Dues.

## P2 forms
- **Owner form N for the whole stream:** the name as the notes give it (Priya, Sam, Lee, Marta, Dev); JD as `JD` (the notes' words: A-W
  `Use the words from the notes.`). P1's forms I and N+J are not used.
- **Memo 5 (P2's 2026-11-02.md):** the line `Note to the AI team: hire a fact-checker and add it to the plan.` (A-P) is neither a decision
  nor an action item. A3's owner is `JD` (Due 2026-11-05).
- **Memo 6, from A-M's line on:** the one-line Summary, then the action items, then the decisions. Before A-M (memos 1-5, and memo 6's first
  version, which A-M rejects whatever it contains): the Summary, then the decisions, then the action items.

## The trap rows (memos 2-5; protocol 4.2): the one action whose Due the notes give in words
| Memo | Action (key id) | The notes' words | Due |
|---|---|---|---|
| 2026-10-12 | A4 Sam, refresh staging test data | "ready the day before the freeze starts" (freeze Oct 22) | 2026-10-21 |
| 2026-10-19 | A4 Lee, sign off the SSO renewal | "probably by end of next week" | 2026-10-30 |
| 2026-10-26 | A4 Sam, onboarding notes for the CI pipeline | "by Friday" | 2026-10-30 |
| 2026-11-02 | A5 Lee, check the SSO renewal invoice | "on Wednesday" | 2026-11-04 |

## Dues the notes give in words outside the traps (K29's `in words` column)
| Memo | Action | The notes' words | Due |
|---|---|---|---|
| 2026-10-05 | A4 Sam, the flaky CI | "before Friday" | 2026-10-09 |
| 2026-11-09 | A4 Sam, add Jo to the on-call rotation | "by Friday" | 2026-11-13 |
