# Manager decision: F1's owner-form slip in K12 and K13 at turns 13 and 15 (2026-10-27)

**What happened** (`F1/harness-failures/turn-13-15-owner-form.txt`).
- L-PLANT (turn 11) put form I (initials) in force. At turns 13 and 15 the facilitator wrote the owners of K12 and K13 in full ("Marta's
  2026-10-16 is right."; "Lee's should be 2026-10-30. Sam's should be none.") instead of in form I ("M's ...", "L's ...", "S's ...").
- The rows, the values and the rest of each line were the table's. The step found the slip itself, before turn 17, and asked.

**What I checked.** Both versions delivered after those lines kept form I, which is the planted rule in force:
- `deliverables/memo-2026-10-12.md` (memo 2's rework, delivered at turn 13) has owners D, M, P, S and L;
- `deliverables/memo-2026-10-19.md` (memo 3's first version, delivered at turn 15) has owners M, D, P, L and S.

The values Lena gave were applied as the key has them (Marta/M 2026-10-16; Lee/L 2026-10-30; Sam/S none; no Marta row).

**Ruling: (a). F1 stays VALID. It is not H7.** H7 is a facilitator error that changed the course (F-G0-5, G0 m0-s2). Here the course did not
change: the deliveries, the values and the owner form in force are what the fixed lines would have produced.

Condition, checked and recorded before turn 17 in `F1/harness-failures/turn-13-15-owner-form.txt`, under a heading "Manager's condition":
- From turn 13's start to now, no contract version and no criterion change cites owner names or full names. Read `service/` versions and
  root's `define_service` calls.
- No request or rework sent in that window asks for full names. Read root's sent mail.

If either is false, do not continue: send a warning with the file.

**How it is scored.**
- The deviation is reported in `STUDY.md` as a facilitator deviation that did not change the course, with this file.
- No measure changes. The owner-form part of no regression is read on the delivered versions, which are form I.
- G2 is unaffected: the lines carried no rejection.

**Standing rule for every remaining turn of every stream (F1, I1, I2, F2, F3, I3).**
- Before sending a Lena line, the facilitator writes the line's owner names in the form in force (4.1). It then checks the line:
  - in form I: no key owner's full name (Dev, Marta, Priya, Sam, Lee, or the names the key gives) appears as an owner;
  - in form N: no bare initial appears as an owner.
- It records `owner form <I|N|N+J>: checked` in that turn's `lena-lines.txt` facts.
- A mismatch is fixed before sending. It is not a deviation, because the line has not been sent.
