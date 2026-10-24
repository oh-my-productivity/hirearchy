# Review: memo for meeting 2026-10-05

Files opened (hirearchy org_read):
- lead/writer/work/memo-2026-10-05.md (201 words, 24 lines)
- /private/tmp/hirearchy-e6-s3-1792861552/notes/2026-10-05.md (362 words, 19 lines)
Not opened: nothing else (none needed).

## My own enumeration from the notes (before comparing)

Firm decisions (notes wording "we decided"):
- D1: "we decided to push the gateway migration to the week of 26 October and use the extra time for the failing services"
- D2: "we decided to adopt Renovate with a weekly Monday batch of dependency PRs, starting with the three core repos and widening later if the noise is acceptable"

Discussed, not decided: flaky CI ("Nobody objected and we moved on"); rate limiter (only an RFC to be drafted). "We agreed Lee would ping the vendor" is an agreement but a commitment (see A5), not a separate policy decision. Listed as ambiguous below (X1).

Commitments (5):
- A1 Priya: "ACTION: Priya to draft the RFC for the new per-key rate limiter by Oct 9, so the team can review it at the following meeting."
- A2 Dev: "ACTION: Dev to enable Renovate on the three core repos by Oct 8."
- A3 Sam (informal): "Sam said he'd look into the flaky CI before Friday, since he suspects the shared build cache."
- A4 Marta: "ACTION: Marta to book the on-call training room for Oct 14."
- A5 Lee (informal): "We agreed Lee would ping the vendor about it this week and report back, no hard date attached."

Not commitments: Dev's staging walkthrough (status); Dev "which he can do himself" (covered by A2); Marta's reminder (covered by A4).

## Criteria

- C1 met. Memo content (present list, 2 decisions, 5 rows, next meeting) all comes from the single notes file; nothing refers to other meetings.
- C2 met. read shows 201 words (limit 400).
- C3 met. Heading "## Decisions" present; lists exactly D1 and D2. The open item (flaky CI) is in a separate "## Open, not decided" section, not under Decisions. Ambiguous only via X1.
- C4 met. Heading "## Action items"; header row "| Owner | Action | Due |" exactly three columns in that order.
- C5 met. 5 rows (Priya, Dev, Sam, Marta, Lee) = A1..A5 one-to-one, including informal A3 and A5. No missing, no extra.
- C6 AMBIGUOUS (not decided by me). All Due values are ISO dates or "none" in form. Which value is right is readable two ways for three rows:
  - Sam: memo 2026-10-09. Notes "before Friday"; the meeting is Mon 2026-10-05 so Friday = 2026-10-09. Read strictly, "before Friday" = by 2026-10-08; read loosely, by Friday 2026-10-09 (the memo's choice).
  - Marta: memo none. Notes "for Oct 14" is the training date, not a deadline for booking. Alternative reading: due 2026-10-14.
  - Lee: memo none. Notes "this week ... no hard date attached". Alternative reading: end of week 2026-10-09; the notes explicitly say no hard date, which supports none.
  Verified fine: Priya 2026-10-09 ("by Oct 9"), Dev 2026-10-08 ("by Oct 8").
- C7 met. Every claim checked (13 of 13 verified), see table below.
- C8 not verifiable by me yet. It depends on this review's outcome (criteria met n = m) and on the writer applying changes; with C6 ambiguous, n = m cannot be stated.

Criteria met: 6 of 8 (C1, C2, C3, C4, C5, C7). C6 ambiguous, C8 pending. Overall verdict: not pass yet; blocked on C6 ruling.

## Claim-by-claim (13 of 13 verified)

1. "Present: Priya, Sam, Lee, Marta, Dev." = notes "Present: Priya, Sam, Lee, Marta, Dev."
2. Title date Monday 2026-10-05 = "Monday 5 October 2026"
3. D1 push to week of 26 October, extra time for failing services = "we decided to push the gateway migration to the week of 26 October and use the extra time for the failing services"
4. D1 reason: two of five fail contract tests, mostly header casing; nobody comfortable in week of 12 October = "two of the five services still fail the contract tests, mostly because of header casing. Nobody was comfortable cutting over in the week of 12 October"
5. D2 Renovate weekly Monday batch, three core repos, widen later if noise acceptable = D2 sentence above
6. D2 reason: three incidents this quarter from stale libraries = "three incidents this quarter that traced back to stale libraries"
7. Priya row: RFC per-key rate limiter, review at following meeting, 2026-10-09 = A1
8. Dev row: enable Renovate three core repos, 2026-10-08 = A2
9. Sam row: flaky CI, main pipeline ~1 in 8 runs fail, suspects shared build cache, before Friday = "fail roughly one run in eight", "suspects the shared build cache", "before Friday"; Due 2026-10-09 see C6
10. Marta row: book on-call training room, fits eight with screen, 14 October = A4 + "fits eight people with a screen"; Due none see C6
11. Lee row: ping identity vendor about SSO certificate renewal (expires end of month), this week, report back = "expires at the end of the month", A5; Due none see C6
12. Open item: "No decision was recorded on the flaky CI itself" = true ("Nobody objected and we moved on"). "Sam is investigating" is a mild paraphrase of "Sam said he'd look into" (see optional change)
13. "Next meeting: Monday 2026-10-12" = "Next meeting Monday 12 October" (year taken from the meeting header)

## Ambiguous items (for the lead to decide)

- C6 / Sam: Due 2026-10-08 or 2026-10-09 for "before Friday".
- C6 / Marta: none or 2026-10-14 (training date vs. booking deadline).
- C6 / Lee: none or 2026-10-09 ("this week, no hard date").
- C3 / X1: whether "We agreed Lee would ping the vendor" should also count as a decision. I read it as a commitment only.

## REQUIRED CHANGES

None found, apart from whatever the lead rules on the ambiguous C6 items above (the author would then change the Due cell of the affected row).

## OPTIONAL CHANGES

- Under "Open, not decided": replace "Sam is investigating." with "Sam said he would look into it before Friday." (closer to the notes; "is investigating" implies progress the notes do not state).

## Scope note
The reviewer checks traceability to the notes only; I did not check the notes' facts against any outside source (e.g. that 2026-10-05 is a Monday; I computed it as a Monday, but that is outside the notes).
