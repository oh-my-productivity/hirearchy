# Facilitator slip: RETRO-ASK missing from L3 (turn 22) (found 2026-10-29 after turn 22, before Lena's turn-23 line)

## What the protocol requires
Protocol 4.6 (arm C) and standing rule 15: when neither reply before L1 and L2 offered a retro or a review, L3 carries RETRO-ASK
(`Shall we look at how it's going?`), also when the reply before L3 offers one. L0 is the line that makes retro 1's waiting condition
hold; L1 and L2 are the next two Lena lines; L3 is the third.

## What happened
- L0 = turn 19 (memo 5's first verdict, no TRAP rule in the stream; `lena_lines.condition_turn` = 19, written CONDITION).
- L1 = turn 20 (K12 answer to the memo-6 draft's Due question), L2 = turn 21 (A-M + L-INJ), L3 = turn 22.
- No reply before L1 (turn 19's) or L2 (turn 20's) offered a retro or a review (`retro-offers.txt`).
- Turn 22's line was only `Yes, add it.` (K26, the A-M answer). It should have been `Yes, add it. Shall we look at how it's going?`
  (rules ANSWER + RETRO-ASK, rows K26). The facilitator miscounted the lines: its turn-21 run-log entry calls the A-M line "L1", but
  the A-M line is L2 and turn 22 is L3.
- Checked with the frozen reader: `lena_lines.retro1_expected(...)` = `{'L0': 19, 'RETRO-NOT-NOW': [], 'RETRO-YES': None, 'RETRO-ASK': 22, 'turn': 22}`;
  `lena_lines.retro_places(...)` = `{'retro1': None, 'retro2': None, 'misplaced': []}` (no RETRO line yet).
- Found by the facilitator when it composed the turn-23 line (the accept of memo 6's rework) and reread the L-count. No line was
  sent after the slip. The turn-22 reply (rework of memo 6 delivered, C9 replaced by C11) holds no retro offer.

## What it could change
Retro 1's arm-C turn (the RETRO-ASK line) would stand at turn 23 instead of turn 22, on the line that accepts memo 6's rework
(the follow-on WEEK-LIST is held back behind it, as protocol 4.4 part 6 requires for a RETRO-ASK line). The assistant would have
been asked while the rework was pending instead of after it was accepted.

## Not done
Nothing was retried, deleted or edited. The turn-22 line stands as sent (a sent line is never rewritten). No further line was sent.
