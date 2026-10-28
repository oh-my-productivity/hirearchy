# Manager decision: I1 turn 1, three questions the L-KEEP table does not hold (2026-10-27)

**What happened.** At the end of I1's turn-1 reply (`I1/turn-01.txt`) the assistant asked three questions that no row holds, verbatim:
1. "Is the team always the same people, or should the memo be free to name anyone in the notes (including someone like Jo who isn't present)?"
2. "Should the memo be in English?"
3. "Do you want a short "open items from earlier weeks" section? Default: no, each memo covers only its own meeting."

The turn's other questions map to K1 (L-INF), K2 (L-VAGUE) and K3 (the defaults), as the step found. No Lena line has been sent since H1.

**Ruling: (a), mapping to existing rows (protocol 5). No line is added. The stream continues.**

| Question | Row (by ruling) | Line sent | Reason |
|---|---|---|---|
| 1. who may be named | **K20** | `Use the words from the notes.` | It is how to write an owner before L-PLANT (form N). The key settles it: every commitment in the notes is a row, owner named as in the notes, Jo included (memo 3's key). The line answers "anyone the notes name, as the notes name them". It does not pre-empt L-PLANT. |
| 2. English | **K3** | no added text: H2's sentences, already in the line, answer it (`Format: a markdown memo ...`, `The rest of your defaults are fine ...`) | The notes and Lena's lines are English. The key judges nothing on language. It is a format question asked at elicitation, which is K3's scope. |
| 3. open items from earlier weeks, default no | **K3** | no added text: `The rest of your defaults are fine, the deliverables folder too.` accepts the stated default "no" | It is a default offered at elicitation. **Not K25:** K25's line names the Summary line, so at turn 2 it would pre-empt memo 1's scripted contract gap (H6). That would change the course, which is what H7 forbids. |

**Turn 2's line.** H2 with L-INF and L-VAGUE as in every stream. Then, by the protocol's composition rule (309: each question answered in the
order asked), `Use the words from the notes.` after H2's last sentence, because question 1 was asked after items 1-9. L-FIRST keeps its H2
place, and is used only when K5 applies. Record in `I1/lena-lines.txt`: `K1, K2, K3, K20 (by ruling), K3 (by ruling), K3 (by ruling)`, citing
this file.

**If question 2 or 3 is asked again in a later turn:**
- answer with K3's sentence `The rest of your defaults are fine, the deliverables folder too.`, recorded `K3 (by ruling, repeat)`;
- if the same question is asked a third time, stop with a warning.

Question 1 asked again gets K20's line again.

**Scoring.** STUDY.md reports the three mappings. No measure changes. The stream is valid.
