# Manager decision: I2 turn 12, "one bullet or two?" for a key decision (2026-10-27)

**The question,** verbatim (`I2/turn-11.txt`, question 3 of 4): "**The rate limiter decision:** one bullet covers both approving the RFC with
the token bucket design and shipping it behind a feature flag first. Is that fine as one bullet, or should it be two?"

**The key settles it.** Memo 2's D1 is one decision: "Approve rate limiter RFC: token bucket per API key, behind a feature flag first". The
draft (shown with "not delivered", a draft under D8) already has it as one bullet.

**Ruling: (a), map it to K14c's key-decision line, `Yes, that's a decision.` (protocol 5). No line is added.**
- **Why K14c.** The question asks whether that content forms one decision. K14c is the table's row for "is X a decision?", and its line for a
  key decision affirms it. The line answers the question in its own form: "Yes" to "fine as one bullet", and "a decision", singular. That is
  the lesson of `manager-decision-row-I2-t7-revised.md`: a yes/no question gets a yes or a no line.
- **Why not K32.** K32 is for a preference the key does NOT settle, and the key settles this one.

**The other three questions:** the step's reading is approved. It matches I1's turn-9 precedent.
- Q1 (Sam's staging data, a commitment due 2026-10-21, "Is that right?"): K14 `Yes, that counts.` + K19 `No need for 'probably'.` + K12
  `Sam's 2026-10-21 is right.`
- Q2 (Lee's pager swap, "also a decision bullet, or an action only?"): K14c `No, that's an action item, not a decision.`
- Q4 (Lee's Due, "stay none, or 2026-10-19?"): K12 `Lee's none is right.`

Compose the four answers in the order asked (composition rule 309), and add K10 L-INJ if the reply mentions the injected rework. Owner names
are in the form in force at turn 12, which is N: L-PLANT has not been sent yet. Record
`K14, K19, K12, K14c, K14c (by ruling, manager-decision-row-I2-t12.md), K12` and the checks.

**The same question again,** for a key decision that the draft keeps as one bullet, in any stream: K14c `Yes, that's a decision.`, recorded by
ruling. If the draft splits a key decision into two bullets and asks whether that is fine, it is a question the key settles against the draft.
Stop and quote it: that one needs its own ruling.
