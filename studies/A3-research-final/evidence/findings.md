# Fact-Check Findings: Required Changes
File checked: lead/writer/work/competitors.md (1057 words, verified by `read`)
Fact-checker: lead/factcheck

---

## Verdict: FAIL

Coverage: 24 verified, 6 wrong, 3 unsupported, 27 not-checkable of 60 claims.
(24 + 6 + 3 + 27 = 60)

Not-checkable claims are those where the source was not independently fetched in this run (sources cited only in researcher notes) or where claims are qualitative/subjective with no citation — they are not counted as verified. The PASS threshold requires n = m (all verified); that is not met.

---

## REQUIRED CHANGES (ordered by severity)

---

### CHANGE-1 [HIGH] — C30: Wrong arithmetic in enterprise savings comparison

**Location:** Where We Can Win, §2 ("Self-Hosted Sync Without Per-User Fees"), second bullet list

**Current text:**
> "For a 100-user organization, this costs $0 vs. Joplin's €240-330/month or Obsidian's €400-600/month—a 3-5x price advantage that becomes the default choice for enterprises."

**Why it is wrong:**
- Joplin Server Business for 100 users: 100 users falls in the 51+ tier at €2.50/user/month = €250/month. The stated range "€240-330/month" does not correspond to any actual pricing tier. The upper end (€333/month) would be for 2-10 users only. A 100-user org always pays €250/month.
- Obsidian Sync for 100 users: $4/user/mo (annual) × 100 = $400/mo; $5/user/mo × 100 = $500/mo. The claim states "€400-600/month" mixing currencies (these are USD figures, not euros) and the upper bound $600 is overstated ($5×100=$500 not $600).
- The "3-5x price advantage" figure is also unsupported — comparing $0 to $250-500/month is not a "3-5x" difference (it's infinite or undefined if one side is zero).

**Source evidence:**
- joplinapp.org/plans: "51–∞ users: €2.50 / user / month"
- obsidian.md/pricing: "Sync $4 USD per user per month (annually), $5 USD per month (monthly)"

**Required correction:**
Replace the incorrect figures with accurate ones. For example:
> "For a 100-user organization, Joplin Server Business costs ~€250/month (100 users × €2.50/user/month at the 51+ tier) and Obsidian Sync costs ~$400-500/month (100 × $4-5/user/month). A free self-hosted alternative eliminates recurring per-user fees entirely."

Also remove the unsupported "3-5x price advantage" figure, or replace it with the corrected calculation. The same error propagates to the Summary ("For enterprises, this delivers 3-5x cost savings") — that figure must also be corrected or removed.

---

### CHANGE-2 [HIGH] — C58: Unsupported "3-5x cost savings" in Summary

**Location:** Summary paragraph (last section)

**Current text:**
> "For enterprises, this delivers 3-5x cost savings"

**Why it is wrong:**
No source cited. The arithmetic in §2 that underpins this was itself wrong (see CHANGE-1). The correct comparison shows €250/month vs. $0 (self-hosted free), which is not "3-5x" but rather a full elimination of the per-user fee. The "3-5x" figure is invented.

**Required correction:**
Remove or replace with an accurate statement, e.g.: "For enterprises with 100+ users, eliminating per-user sync fees (Joplin's €250/month, Obsidian's ~$400-500/month) represents a significant total cost of ownership advantage."

---

### CHANGE-3 [HIGH] — C05: Unsupported negative claim ("no self-hosted server available") and wrong AES-256 citation

**Location:** Table / Obsidian row / Sync Model column

**Current text:**
> "Cloud-only via Obsidian Sync; end-to-end encrypted (AES-256); no self-hosted server available (https://obsidian.md/sync)"

**Why it is wrong:**
1. "No self-hosted server available" — this is a negative absolute claim. The cited source (https://obsidian.md/sync) does NOT state this; it only describes cloud sync options. A negative claim requires a source that STATES the absence. The source does not say "no self-hosted server."
2. "AES-256" encryption — this specific algorithm is stated on https://obsidian.md/pricing in the FAQ ("your data is secured with AES‑256 end-to-end encryption"), NOT on https://obsidian.md/sync which is the only citation given. The citation is wrong for this fact.

**Source evidence for AES-256:**
- obsidian.md/pricing FAQ: "If you choose to use Obsidian Sync, your data is secured with AES‑256 end-to-end encryption"
- obsidian.md/sync does NOT mention "AES-256"

**Required correction:**
1. Update the AES-256 citation to https://obsidian.md/pricing (or add it alongside /sync).
2. For "no self-hosted server available": either find a source that states this directly (e.g., Obsidian help docs that explicitly say no self-hosted option exists), or reframe as "Obsidian offers no official self-hosted sync server" with a note that the sync page lists only cloud options.

---

### CHANGE-4 [MEDIUM] — C19: Wrong context for 50% student/educator discount

**Location:** Table / AnyType row / Pricing column

**Current text:**
> "Free basic tier; Paid plans €20/editor/mo for business workspaces; 50% student/educator discount; self-hosters free basic tier (https://business.anytype.io/; https://doc.anytype.io/anytype-docs/memberships/monetization)"

**Why it is wrong:**
The 50% student/educator discount applies to **personal Anytype membership plans**, not to the €20/editor/month Anytype for Business workspace plans. The business.anytype.io page (cited first) makes no mention of this discount. Placing both facts in the same cell under the business pricing implies the discount applies to business plans, which is misleading and wrong.

**Source evidence:**
- doc.anytype.io/memberships: "Students or faculty members are eligible for a 50% discount on all of our membership plans." — this is for personal memberships.
- business.anytype.io: No mention of student discount.

**Required correction:**
Either (a) remove the student/educator discount from the AnyType business row since it doesn't apply there, or (b) clarify that it applies to personal plans only: "50% student/educator discount on personal plans." Also note that the citation to business.anytype.io does not support this fact; the correct citation is https://doc.anytype.io/anytype-docs/memberships/monetization.

---

### CHANGE-5 [MEDIUM] — C20: Wrong claim about AnyType self-hosters getting "free basic tier" in business context

**Location:** Table / AnyType row / Pricing column (same cell as C19)

**Current text:**
> "self-hosters free basic tier"

**Why it is wrong:**
In the context of the AnyType business row (which cites business.anytype.io), self-hosting Anytype for Business is NOT free — it is "coming soon" at €300/month flat. The "self-hosters free basic tier" refers to personal Anytype self-hosting (described on the memberships page), not the business product.

**Source evidence:**
- business.anytype.io: "Self-hosted — coming soon... €300 / month, flat. Regardless of team size."
- doc.anytype.io/memberships: "Self-hosters can manage the limits of Viewers/Editors they invite to their Channels themselves." — this is personal Anytype only.

**Required correction:**
Remove "self-hosters free basic tier" from the business-focused AnyType row, or clearly separate personal Anytype pricing (free tier, self-hosters free) from Anytype for Business pricing (€20/editor/mo, self-hosted €300/mo flat — coming soon). The row currently conflates the two products.

---

### CHANGE-6 [MEDIUM] — C22: Citation error — AnyType privacy source contains Obsidian text

**Location:** Table / AnyType row / Sync Model column (sourced from research.md)

**Current status:** The research.md source (https://doc.anytype.io/anytype-docs/data/privacy-and-encryption) was cited with a quote that reads "Your data is saved locally on your device and is not sent to our server. If you use Obsidian Publish or Obsidian Sync, we handle your data..." — this quote is from the OBSIDIAN license/privacy page, not AnyType. The researcher appears to have copy-pasted a quote from the wrong source.

**Why it is wrong:**
The AnyType sync claim in the deliverable ("Local-first by default; optional encrypted sync via Anytype backup nodes; users can self-host sync infrastructure; all data encrypted end-to-end") may be factually correct, but it is supported by a source that was cross-contaminated with an Obsidian quote. The sync page should be fetched fresh to obtain a proper AnyType quote.

**Required correction:**
The researcher (lead/researcher) should re-verify the AnyType privacy/encryption page and provide a correct quote from that page. The deliverable's sync claim for AnyType should be re-cited with a direct quote from the AnyType source (not an Obsidian quote).

Note to manager: This is a researcher error in research.md that the writer likely carried over. The rework should involve both correcting the source quote in research.md and verifying the deliverable's AnyType sync claim.

---

### CHANGE-7 [MEDIUM] — C42: Misleading claim that Obsidian collaboration is "weak" — Obsidian Sync DOES include shared vaults

**Location:** Where We Can Win, §6 ("Real-Time Collaboration Without Lock-In")

**Current text:**
> "Obsidian: weak collaboration (Publish is for distribution, not co-editing)"

**Why it is wrong/misleading:**
The Obsidian Sync page (https://obsidian.md/sync) explicitly states: "Collaborate with your team — Invite your team to a shared Obsidian vault. Notes are updated in real-time across your team's devices without compromising the privacy of your company data." Obsidian Sync does include shared vault collaboration. The claim that Publish is for distribution (not co-editing) is correct, but implying that collaboration is "weak" or only available via Publish ignores the shared vaults feature in Obsidian Sync.

**Required correction:**
Revise to accurately characterize Obsidian's collaboration: Obsidian Sync includes real-time shared vaults (multiple users editing the same vault), but lacks features like granular permissions or operational transforms for true concurrent editing. E.g.: "Obsidian: collaboration via shared vaults (Sync required, $4-5/user/mo), but no CRDT/OT-based real-time co-editing; Publish is for distribution, not co-editing."

---

### CHANGE-8 [LOW] — C55: Claim that Obsidian data flows are "unclear" contradicted by source

**Location:** Where We Can Win, §10 ("Transparent Data Control")

**Current text:**
> "Obsidian: free app but proprietary cloud services create unclear data flows"

**Why it is unsupported:**
The obsidian.md/license page explicitly describes data handling: "Your data is saved locally on your device and is not sent to our server. If you use Obsidian Publish or Obsidian Sync, we handle your data only as needed for those services." The data flows are in fact documented, not "unclear."

**Required correction:**
Revise to accurately state what the concern is. For example: "Obsidian: free app but closed-source cloud sync means users must trust Obsidian's team without ability to independently audit the sync implementation." This is accurate and not contradicted by the source.

---

## NOT-CHECKABLE CLAIMS (27 of 60)
These claims could not be independently verified in this run because their source URLs were not directly fetched, or the claims are qualitative/subjective with no citation. They are listed here for completeness but do not result in required changes. The manager should decide whether these need a second-pass verification:

C08 (Logseq AGPL-3.0 from GitHub), C09 (Logseq custom sync URL), C12 (Joplin AGPL-3.0), C13 (Joplin Server personal license), C16 (Trilium AGPL-3.0 license file), C21 (AnyType license terms), C24 (AnyType commercial licensing), C25-restriction characterization, C26 (Trilium limited enterprise adoption — qualitative), C27 (Obsidian no self-hosted — negative claim overlap with C05), C31-C36 (qualitative Where We Can Win claims without citations), C42/C43/C44/C45 (collaboration characterizations), C46-C50 (security/extensibility characterizations), C51-C57 (qualitative market claims in Where We Can Win and Summary).

Most not-checkable claims are qualitative assessments in the "Where We Can Win" section, which by nature rely on judgment rather than verifiable facts. The factual/quantitative not-checkable claims (C08, C09, C12, C13, C16, C21, C24) should be confirmed by fetching those source URLs directly.
