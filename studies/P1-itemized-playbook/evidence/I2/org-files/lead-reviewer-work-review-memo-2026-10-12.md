# Review: memo 2026-10-12 (task ...-5116)

Files opened:
- lead/writer/work/memo-2026-10-12.md (147 words, by hirearchy org_read)
- /private/tmp/hirearchy-p1-I2-1793142034/notes/2026-10-12.md (opened, all text read)
Not opened: none.

## My own list from the notes (built before comparing)
Meeting: Monday 12 October 2026 (header). Frozen days: Oct 22, Oct 23. "Last Thursday" = Oct 8.

Decisions (notes use "decided"/"won out"):
- D1 "The team decided to approve the RFC with the token bucket design and to ship it behind a feature flag first." (token bucket per API key)
- D2 "We decided the postmortem will be blameless and will be shared with the whole company, not just engineering"
- D3 "the team decided on a deploy freeze on Oct 22 and Oct 23"

Commitments:
- A1 "ACTION: Dev to write the postmortem for the Oct 8 outage by Oct 14." -> 2026-10-14
- A2 "ACTION: Marta to send the demo agenda to the customer by Oct 16." -> 2026-10-16
- A3 "ACTION: Priya to start implementing the rate limiter behind a feature flag by Oct 20." -> 2026-10-20
- A4 Sam (prose): "the test data is out of date and will probably sort it out himself so that it's ready the day before the freeze starts." Freeze starts Oct 22, so day before = 2026-10-21. AMBIGUOUS (hedged, see below)
- A5 Lee (prose): "he'll swap shifts with Dev" for the demo week. No date given -> none.

Not commitments: Sam's CI update ("needs more than a quick patch", nobody to act); Dev "would rather be free to present" (preference); Priya "ready to start building" (covered by A3); "Nobody had a problem with that" (acceptance); next meeting Monday 19 October (scheduling, status).

## Ledger
| Item | In memo? | Evidence |
|---|---|---|
| D1 | yes | "Approve the rate limiter RFC with the token bucket per API key design, and ship it behind a feature flag first." |
| D2 | yes | "Make the postmortem for the 8 October billing outage blameless and share it with the whole company, not just engineering." |
| D3 | yes | "Hold a deploy freeze on 22 and 23 October for the customer demo." |
| A1 | yes | "Dev \| Write the postmortem for the 8 October outage \| 2026-10-14" matches "by Oct 14" |
| A2 | yes | "Marta \| Send the demo agenda to the customer \| 2026-10-16" matches "by Oct 16" |
| A3 | yes | "Priya \| Start implementing ... feature flag \| 2026-10-20" matches "by Oct 20" |
| A4 | yes | "Sam \| Update the out-of-date staging test data \| 2026-10-21"; freeze Oct 22, day before = Oct 21, correct |
| A5 | yes | "Lee \| Swap pager shifts with Dev for the demo week \| none"; notes give no date |

Due values checked: Dev 2026-10-14 ok; Marta 2026-10-16 ok; Priya 2026-10-20 ok; Sam 2026-10-21 ok (derived, notes make the date clear via the Oct 22 freeze); Lee none ok ("demo week" is a period, not a date; week of 19 October is stated but no deadline).

## Criteria
- C1 met. Memo content traces only to 2026-10-12.md (all dates, names, outage details appear there). No other source used visible.
- C2 met. 147 words by read (limit 400).
- C3 met. Title "# Platform team weekly memo, 2026-10-12" names the date; sections "## Decisions" (3 bullets = D1-D3) and "## Actions"; table header "\| Owner \| Action \| Due \|"; only other element is the Summary line (allowed by C8). No other sections.
- C4 met (on my reading; see ambiguous a). 5 rows = A1-A5; no row for non-commitments listed above.
- C5 met. All Due values are YYYY-MM-DD or "none"; derivations checked above.
- C6 met. Each decision/action traced above; nothing invented. Minor wording: "billing outage" and "8 October" combine "last Thursday's outage ... billing service" with Dev's "Oct 8"; both in notes. "for the customer demo" on D3 is in notes ("customer demo ... deploy freeze").
- C7 satisfied by this report: no required changes, so nothing for the writer to apply; all of C1-C6, C8 met.
- C8 met. Order: title, line "Summary: The rate limiter RFC is approved ..." (single line, directly after title), "## Decisions", "## Actions". Addresses R1 verbatim: Summary first, then decisions, then action items.

criteria met: 8 of 8 (C7 judged as the lead specified).

## Factual claims verified: 13 of 13
Decisions 3 (D1-D3); action rows 5 (A1-A5, owner+action+Due); Summary claims 5: RFC approved (D1); per-API-key token bucket (D1); postmortem blameless and company-wide (D2); deploy freeze 22 and 23 October (D3); "five actions were assigned" (5 rows; note: only 3 are labelled ACTION in the notes, the other 2 are prose commitments, still five commitments).

## Borderline items
(a) Sam staging row: AMBIGUOUS. Fits criterion C4's example "X said he'd do Y" and the notes give a date anchor ("day before the freeze starts"), but "will probably" is hedged. My judgement: include is reasonable and the memo is consistent with C4; if the lead reads "commitment" as requiring no hedge, the row and C4 flip. Criteria do not settle it. The memo gives no hint of the hedge (Due 2026-10-21 shown as firm); not a criterion failure.
(b) Lee pager swap: the row is correct ("he'll swap shifts with Dev" is a commitment). Whether "Nobody had a problem with that" makes it a decision: notes do not use "decided" and state no decision; I judge it not a decision, so no bullet needed. AMBIGUOUS in that C3's "every decision stated" does not define an agreement by silence. Due none is correct either way.
(c) Blameless company-wide postmortem as a decision: NOT ambiguous; the notes say "We decided the postmortem will be blameless and will be shared with the whole company". Correct.
(d) AMBIGUOUS, also: D1 contains two decisions in one sentence (approve RFC with token bucket; ship behind a feature flag first). Memo has one bullet; C3 "one bullet for every decision" could be read as requiring two. I judge one bullet acceptable since the notes state it as one sentence, but the criterion does not settle it.
(e) AMBIGUOUS: Lee Due "none" vs "demo week" (week of 19 October). Notes give no date; "none" follows C5's rule.

## Not a fact-check
I checked the memo against the notes only. Claims in the notes themselves (outage length, dates being weekdays) were not checked externally.

## REQUIRED CHANGES
None.
