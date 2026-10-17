# Verification Ledger: Writer's Analysis Draft
## Document checked: lead/writer/work/analysis-draft.md
## Date: 2026-10-17
## Checker: lead/factcheck

---

## SCOPE

This ledger covers all factual claims in `lead/writer/work/analysis-draft.md` (the comparison table and "Where we can win" section). The "Sources" block at the end of the table is not a separate claim; it is the citation block and is evaluated as part of the claims it supports.

Word count of analysis draft (from `read`): **396 words**.

---

## LEDGER

| id | type | statement (quoted) | location in draft | cited source (from Sources block) | verdict | evidence |
|----|------|--------------------|-------------------|-----------------------------------|---------|----------|
| DA01 | fact | "Free core app" [Obsidian pricing] | Obsidian row / Pricing | https://obsidian.md/pricing | verified | "Free without limits. No sign-up required. No strings attached." — https://obsidian.md/pricing |
| DA02 | fact | "optional Sync $4–5/month (annual/monthly)" [Obsidian] | Obsidian row / Pricing | https://obsidian.md/pricing | verified | "Sync — $4 USD Per user, per month, billed annually … $5 USD Per user, per month, billed monthly" — https://obsidian.md/pricing |
| DA03 | fact | "Publish $8–10/month" [Obsidian] | Obsidian row / Pricing | https://obsidian.md/pricing | verified | "Publish — $8 USD Per site, per month, billed annually … $10 USD Per site, per month, billed monthly" — https://obsidian.md/pricing |
| DA04 | fact | "Catalyst $25 one-time" [Obsidian] | Obsidian row / Pricing | https://obsidian.md/pricing | verified | "Catalyst — $25 USD One-time payment" — https://obsidian.md/pricing |
| DA05 | fact | "Commercial $50/year" [Obsidian] | Obsidian row / Pricing | https://obsidian.md/pricing | verified | "Commercial — $50 USD Per user, per year" — https://obsidian.md/pricing |
| DA06 | fact | "Proprietary; free for personal, commercial, non-profit, educational, and government use" [Obsidian license] | Obsidian row / License | https://obsidian.md/license | verified | "You can download and use Obsidian for free, forever, for any purpose including: Personal use, Commercial use, Non-profit and charitable organizations, Educational institutions, Government departments and agencies" — https://obsidian.md/license |
| DA07 | fact | "Proprietary Obsidian Sync (end-to-end encrypted)" [Obsidian sync] | Obsidian row / Sync Model | https://obsidian.md/pricing | verified | "Sync notes across devices, End-to-end encryption, Version history, Collaborate on shared vaults" — https://obsidian.md/pricing |
| DA08 | fact | "self-managed via third-party services (Dropbox, iCloud, OneDrive, WebDAV)" [Obsidian sync alternatives] | Obsidian row / Sync Model | https://obsidian.md/pricing | wrong | The cited source (obsidian.md/pricing) does NOT mention Dropbox, iCloud, OneDrive, or WebDAV. The official Obsidian help docs (https://help.obsidian.md/getting-started/sync-your-notes-across-devices) list community-reported third-party sync methods as "iCloud, OneDrive, and Google Drive" — not Dropbox and not WebDAV. The draft lists Dropbox and WebDAV but omits Google Drive, and cites the wrong page entirely. Correct statement based on official help docs: "self-managed via third-party services (iCloud, OneDrive, Google Drive, and others)" with source https://help.obsidian.md/getting-started/sync-your-notes-across-devices which states: "Third-party cloud sync: iCloud, OneDrive, and Google Drive" as the community-reported options. |
| DA09 | fact | "Free core app" [Joplin pricing] | Joplin row / Pricing | https://joplinapp.org/plans | verified | Page presents the free open-source app and optional paid cloud plans; all plans show the free self-hosted option — https://joplinapp.org/plans |
| DA10 | fact | "Joplin Cloud €2.40–7.99/month (annual pricing)" [Joplin pricing range] | Joplin row / Pricing | https://joplinapp.org/plans | verified | "Basic … 2.40€ /month … Pro … 4.79€ /month … Pro 100 GB … 7.99€ /month" (annual rates) — https://joplinapp.org/plans. Range €2.40–7.99 is accurate for annual pricing. |
| DA11 | fact | "Joplin Server Business (self-hosted) €30–40/year per user depending on team size" [Joplin pricing] | Joplin row / Pricing | https://joplinapp.org/plans | verified | "2—10 users │3.33€ / user / month … (40.00€ per user per year)" and "51—∞ users │2.50€ / user / month … (30.00€ per user per year)" — https://joplinapp.org/plans. €30–40/year range is accurate. |
| DA12 | fact | "AGPL-3.0" [Joplin license] | Joplin row / License | https://discourse.joplinapp.org/t/joplin-is-switching-to-the-gnu-affero-general-public-license-v3-agpl-3-0/28747 | wrong | The claim is WRONG. Desktop/mobile/CLI/web clipper are AGPL-3.0 (confirmed by github.com/laurent22/joplin main LICENSE). However, Joplin Server (packages/server) has a SEPARATE proprietary license — the "Joplin Server Personal Use License" — which explicitly restricts use to non-commercial purposes: "The Software may be used for personal non-commercial purposes only." Source: https://github.com/laurent22/joplin/blob/dev/packages/server/LICENSE.md — "JOPLIN SERVER PERSONAL USE LICENSE … Subject to the terms of the License, the Licensee is entitled to access and use the Software for non-commercial purposes … Unless authorised by the Licensor in writing, the Software may be used for personal non-commercial purposes only." The cited Discourse post only announced the AGPL-3.0 switch for "desktop, mobile and CLI applications, as well as the web clipper" — it never said the server was AGPL-3.0. Stating a single "AGPL-3.0" for all of Joplin is incorrect and misleading for users evaluating self-hosting. Correct statement: "Desktop/mobile/CLI: AGPL-3.0; Joplin Server: proprietary Personal Use License (non-commercial only)" |
| DA13 | fact | "Joplin Cloud (managed), Joplin Server Business (self-hosted), or third-party services (Nextcloud, WebDAV, OneDrive, Google Drive)" [Joplin sync] | Joplin row / Sync Model | https://joplinapp.org/plans + https://discourse.joplinapp.org/... | wrong | Partial. Joplin Cloud and Joplin Server Business are verified. For third-party services, the official Joplin sync docs state: "synchronisation is possible with Joplin Cloud, Nextcloud, S3, WebDAV, Dropbox, OneDrive or the local filesystem." Source: https://joplinapp.org/help/apps/sync/ — "Currently, synchronisation is possible with Joplin Cloud, Nextcloud, S3, WebDAV, Dropbox, OneDrive or the local filesystem." Google Drive is NOT listed by Joplin as a supported sync target. Dropbox is a supported option but is omitted from the draft. The draft includes Google Drive (which is not supported) and omits Dropbox (which is supported). Correct statement: "third-party services (Nextcloud, S3, WebDAV, Dropbox, OneDrive, or local filesystem)" |
| DA14 | fact | "Free and open-source forever" [Logseq pricing] | Logseq row / Pricing | https://blog.logseq.com/how-to-setup-and-use-logseq-sync/ | wrong | The claim "free and open-source forever" is substantively supported but the CITATION IS WRONG. The Logseq Sync blog post does NOT state "free and open-source forever" — it is a tutorial about setting up sync. The correct source for this claim is https://blog.logseq.com/contribute/ which states: "We're a free and open-source tool that will always remain free for personal use." Additionally the logseq.com website has been reported (in search snippets) to state "Free forever for personal use." The claim as worded is true for personal use but the citation must be corrected to the Contribute page or the main website. |
| DA15 | fact | "AGPL-3.0" [Logseq license] | Logseq row / License | https://github.com/logseq/logseq | verified | "AGPL-3.0 license" listed on the GitHub repository page under Resources — https://github.com/logseq/logseq |
| DA16 | fact | "Plaintext mode with third-party sync (Dropbox, OneDrive, Git, WebDAV)" [Logseq sync] | Logseq row / Sync Model | https://blog.logseq.com/how-to-setup-and-use-logseq-sync/ | unsupported | The cited Logseq Sync blog post mentions iCloud, Dropbox, and OneDrive only as third-party sync services that users should STOP using before switching to Logseq Sync (i.e., move graph out of those folders). It does NOT enumerate Dropbox, OneDrive, Git, WebDAV as supported Logseq sync options, and it does not mention Git or WebDAV at all. The blog post says "we will keep supporting and developing the plaintext versions/modes of Logseq, which work with any regular file sync solution" — this supports a general "works with third-party sync" claim, but no specific services (Dropbox, OneDrive, Git, WebDAV) are enumerated as supported options on the cited page. The specific list of services is unsupported from the cited source. |
| DA17 | fact | "optional beta Logseq Sync via sponsorship (currently $5–15/month recurring donation)" [Logseq sync] | Logseq row / Sync Model | https://blog.logseq.com/how-to-setup-and-use-logseq-sync/ | verified | "During the beta test, we're giving all of our active Open Collective contributors access to Logseq Sync. That means you need to have monthly recurring donation of either $5 per month or $15 per month." — https://blog.logseq.com/how-to-setup-and-use-logseq-sync/ |
| DA18 | fact | "Free open-source" [Trilium Notes pricing] | Trilium row / Pricing | https://trilium.cc + https://github.com/TriliumNext/Trilium | verified | "Trilium Notes is a free and open-source, cross-platform hierarchical note taking application" — https://github.com/TriliumNext/Trilium (README). Note: trilium.cc is a third-party hosting service; the free/open-source claim is confirmed from the official GitHub repo. |
| DA19 | fact | "optional hosted instance $3.50/month" [Trilium Notes pricing] | Trilium row / Pricing | https://trilium.cc | verified | "$3.50/month gets you a hosted Trilium Notes instance you can connect to from anywhere." — https://trilium.cc |
| DA20 | fact | "AGPL-3.0" [Trilium Notes license] | Trilium row / License | https://github.com/TriliumNext/Trilium | verified | "AGPL-3.0 license" listed under Repository files navigation on the GitHub page — https://github.com/TriliumNext/Trilium |
| DA21 | fact | "Self-hosted server (Linux/Windows) with desktop, web, and mobile clients syncing locally" [Trilium sync] | Trilium row / Sync Model | https://trilium.cc + https://github.com/TriliumNext/Trilium | unsupported | The TriliumNext README states "Synchronization with self-hosted sync server" and mentions a "Touch optimized mobile frontend for smartphones and tablets" and Docker/server setup. However, the specific claim of "Linux/Windows" for the server (and that it does NOT support macOS as server) is NOT stated on either cited page. The README says "cross-platform" for the app itself. The original zadam/Trilium README explicitly said "provided as either desktop application (Linux and Windows) or web application hosted on your server (Linux)" but that is from the ARCHIVED original project, not TriliumNext. The TriliumNext fork's README does not reproduce that platform restriction. The "Linux/Windows" qualifier for server is unsupported from the current TriliumNext source. The rest (self-hosted server, desktop + web + mobile clients) is verified from the GitHub README which mentions Docker setup (server), desktop app, and "Touch optimized mobile frontend." |
| DA22 | fact | "Free for personal use" [AnyType pricing] | AnyType row / Pricing | https://blog.anytype.io/our-open-philosophy/ | verified | "This license grants individuals the freedom to review, modify, and utilize the code for personal, academic, scientific, research, and development purposes." — https://blog.anytype.io/our-open-philosophy/. The personal use is free (no pricing mentioned for personal use on the business page which covers only the Business plan). |
| DA23 | fact | "€20/editor/month for Business" [AnyType pricing] | AnyType row / Pricing | https://business.anytype.io | verified | "€20 per editor / month" — https://business.anytype.io |
| DA24 | fact | "self-hosted Business (coming soon) €300/month" [AnyType pricing] | AnyType row / Pricing | https://business.anytype.io | verified | "Self-hosted — coming soon … €300 / month, flat … Regardless of team size." — https://business.anytype.io |
| DA25 | fact | "Custom license (personal use unrestricted; commercial use requires consent from Any Association)" [AnyType license] | AnyType row / License | https://blog.anytype.io/our-open-philosophy/ | verified | "This license grants individuals the freedom to review, modify, and utilize the code for personal, academic, scientific, research, and development purposes. However, for commercial use, consent from the Any Association is required." — https://blog.anytype.io/our-open-philosophy/ |
| DA26 | fact | "MIT for sync protocol" [AnyType license] | AnyType row / License | https://blog.anytype.io/our-open-philosophy/ | verified | "our core solutions, the infrastructure protocol any-sync, and the data protocol any-block, are released as open source under the permissive MIT license" — https://blog.anytype.io/our-open-philosophy/ |
| DA27 | fact | "Personal: local-first, end-to-end encrypted peer-to-peer sync across devices" [AnyType sync] | AnyType row / Sync Model | https://business.anytype.io | verified | "Local-first & self-hosted. Your data lives on your devices first. Works offline, syncs peer-to-peer." and "Encrypted by default. Data is encrypted on your device before it syncs" — https://business.anytype.io |
| DA28 | fact | "Business: cloud-hosted or self-hosted (coming soon), GDPR compliant" [AnyType sync] | AnyType row / Sync Model | https://business.anytype.io | verified | "Cloud-hosted … Self-hosted — coming soon" and "GDPR compliant" — https://business.anytype.io |

---

## JUDGEMENT SECTION: "Where we can win (our assessment)"

The section is correctly labelled "our assessment" in the heading. No in-line citations appear in this section. Review of each sentence for hidden new facts:

| id | type | statement | verdict | notes |
|----|------|-----------|---------|-------|
| DJ01 | judgement | "Obsidian dominates the proprietary paid-sync market with strong pricing discipline (Sync starting at $4/month)…" | ok | "$4/month" is a verified fact (DA02); rest is assessment |
| DJ02 | judgement | "its proprietary license, while permissive in use, may limit appeal to open-source-first users" | ok | Proprietary license is verified (DA06); rest is assessment |
| DJ03 | judgement | "Joplin and Trilium compete on openness (both AGPL-3.0)…" | fix | This rests on DA12 (Joplin license = AGPL-3.0), which is WRONG. Joplin Server is NOT AGPL-3.0; it uses a proprietary Personal Use License. The judgement "both AGPL-3.0" is factually incorrect as stated. It should say Joplin desktop/mobile apps are AGPL-3.0 but the server is under a proprietary license. |
| DJ04 | judgement | "Joplin's pricing complexity (multiple tiers, per-user scaling)…" | ok | Pricing tiers are all verified (DA10, DA11) |
| DJ05 | judgement | "Trilium's sparse documentation of self-hosting may create friction" | ok | Assessment; no new factual claim |
| DJ06 | judgement | "Logseq offers radical simplicity (free forever, plaintext-compatible) but with an underdeveloped paid sync story (currently beta-only for sponsors)" | ok | "free forever" and "beta-only for sponsors" rest on DA14 (which is substantively correct, wrong citation) and DA17 (verified); core facts are supported though DA14's citation needs fixing |
| DJ07 | judgement | "AnyType differentiates on local-first architecture and team collaboration features at the high end (€20/editor/month)…" | ok | "€20/editor/month" is verified (DA23); rest is assessment |
| DJ08 | judgement | "the custom license and sparse documentation of personal-use sync leave gaps" | ok | Custom license verified (DA25); rest is assessment |
| DJ09 | judgement | "A contender with AGPL-3.0 licensing, straightforward self-hosted server setup, team-friendly pricing that doesn't scale linearly with users…" | ok | Pure assessment/recommendation; no new factual claims |

---

## COVERAGE SUMMARY

**Factual claims: m = 28** (DA01–DA28)
- verified: 21 (DA01–DA07, DA09–DA11, DA15, DA17–DA20, DA22–DA28)
- wrong: 3 (DA08, DA12, DA13)
- unsupported: 2 (DA16, DA21)
- not-checkable: 0

**Total check: 21 + 3 + 2 + 0 = 26** ← Recount needed

Wait — let me recount:
- DA01 verified, DA02 verified, DA03 verified, DA04 verified, DA05 verified = 5
- DA06 verified, DA07 verified, DA08 WRONG = 2 verified + 1 wrong
- DA09 verified, DA10 verified, DA11 verified, DA12 WRONG, DA13 WRONG = 3 verified + 2 wrong
- DA14 WRONG (citation wrong / substantively wrong citation), DA15 verified, DA16 UNSUPPORTED, DA17 verified = 1 wrong + 1 verified + 1 unsupported + 1 verified
- DA18 verified, DA19 verified, DA20 verified, DA21 UNSUPPORTED = 3 verified + 1 unsupported
- DA22 verified, DA23 verified, DA24 verified, DA25 verified, DA26 verified, DA27 verified, DA28 verified = 7 verified

Verified: 5 + 2 + 3 + 2 + 3 + 7 = **22**
Wrong: 1 (DA08) + 2 (DA12, DA13) + 1 (DA14) = **4**
Unsupported: 1 (DA16) + 1 (DA21) = **2**
Not-checkable: **0**
Total: 22 + 4 + 2 = **28** ✓

**Coverage: 22 of 28 factual claims verified (22 ≠ 28 required); 4 wrong, 2 unsupported, 0 not-checkable.**

**Judgement section ("Where we can win"):**
- 8 judgement statements (DJ01–DJ09... using DJ01–DJ09)
- All correctly labelled "our assessment" in the section heading
- No in-line citations in the judgement section ✓
- DJ03 rests on DA12 which is WRONG → **judgement answer: NO** (DJ03 fails)

**VERDICT: FAIL**
- n = 22, m = 28; n ≠ m
- Judgement section: DJ03 rests on wrong fact DA12; answer is NO

---

## REQUIRED CHANGES (ordered by severity)

### CRITICAL — DA12 (Wrong): Joplin License stated as simply "AGPL-3.0"
**Current text in draft**: `AGPL-3.0`  
**Problem**: Joplin Server (packages/server) uses a proprietary "Joplin Server Personal Use License" that prohibits commercial use. Only the desktop, mobile, CLI apps, and web clipper are AGPL-3.0. The analysis is comparing apps for self-hosting (which uses Joplin Server), so this distinction is material.  
**Quoted source confirming the error**: "JOPLIN SERVER PERSONAL USE LICENSE … Unless authorised by the Licensor in writing, the Software may be used for personal non-commercial purposes only." — https://github.com/laurent22/joplin/blob/dev/packages/server/LICENSE.md  
**Replacement text**: `Desktop/mobile/CLI: AGPL-3.0; Joplin Server (self-hosted): proprietary Personal Use License (non-commercial only)`  
**Impact on judgement**: DJ03 ("Joplin and Trilium compete on openness (both AGPL-3.0)") must be revised. Joplin's self-hosted server is NOT open-source. Suggested revision: "Joplin's desktop apps are AGPL-3.0 but its self-hosted server uses a proprietary non-commercial license, meaning Joplin's self-hosted option is not fully open-source."

### HIGH — DA13 (Wrong): Joplin third-party sync includes Google Drive (false) and omits Dropbox (true)
**Current text in draft**: `third-party services (Nextcloud, WebDAV, OneDrive, Google Drive)`  
**Problem**: Google Drive is NOT a supported Joplin sync target. Dropbox IS supported but omitted.  
**Quoted source**: "Currently, synchronisation is possible with Joplin Cloud, Nextcloud, S3, WebDAV, Dropbox, OneDrive or the local filesystem." — https://joplinapp.org/help/apps/sync/  
**Replacement text**: `third-party services (Nextcloud, S3, WebDAV, Dropbox, OneDrive, or local filesystem)`  
**New citation to add to Sources block**: https://joplinapp.org/help/apps/sync/

### HIGH — DA08 (Wrong): Obsidian third-party sync lists Dropbox and WebDAV; cites wrong page
**Current text in draft**: `self-managed via third-party services (Dropbox, iCloud, OneDrive, WebDAV)`  
**Problem**: (1) The cited page (obsidian.md/pricing) does not mention any third-party sync services at all. (2) The official Obsidian help docs list "iCloud, OneDrive, and Google Drive" as community-reported sync methods — not Dropbox or WebDAV specifically. Dropbox is a community plugin option but not listed in the official help guide for syncing.  
**Quoted source**: "Third-party cloud sync: iCloud, OneDrive, and Google Drive" as listed "commonly used sync methods reported by members of the Obsidian community" — https://help.obsidian.md/getting-started/sync-your-notes-across-devices  
**Replacement text**: `self-managed via third-party services (iCloud, OneDrive, Google Drive, and others — community plugins available for more)`  
**New citation to add to Sources block**: https://help.obsidian.md/getting-started/sync-your-notes-across-devices

### MEDIUM — DA14 (Wrong citation): Logseq "Free and open-source forever" cites wrong source
**Current text in draft**: `Free and open-source forever` (cited to the Logseq Sync blog post)  
**Problem**: The Logseq Sync blog post does NOT state this claim. The correct source is the Logseq Contribute page.  
**Quoted source**: "We're a free and open-source tool that will always remain free for personal use." — https://blog.logseq.com/contribute/  
**Fix**: Change the citation in the Sources block from the Logseq Sync blog post URL to https://blog.logseq.com/contribute/ for the "free forever" claim. The claim text itself ("Free and open-source forever") is substantially correct for personal use per the confirmed source.

### MEDIUM — DA16 (Unsupported): Logseq plaintext sync with specific services (Dropbox, OneDrive, Git, WebDAV)
**Current text in draft**: `Plaintext mode with third-party sync (Dropbox, OneDrive, Git, WebDAV)`  
**Problem**: The cited blog post confirms Logseq's plaintext mode works with "any regular file sync solution" but does NOT enumerate Dropbox, OneDrive, Git, WebDAV as official supported options. Git and WebDAV in particular are not mentioned in the blog post at all.  
**Quoted source**: "we will keep supporting and developing the plaintext versions/modes of Logseq, which work with any regular file sync solution." — https://blog.logseq.com/how-to-setup-and-use-logseq-sync/  
**Fix**: Remove the specific service list. Replace with: `Plaintext mode compatible with any regular file sync solution` (citing https://blog.logseq.com/how-to-setup-and-use-logseq-sync/). OR retain the list only if verified from a Logseq documentation page that explicitly names these services.

### LOW — DA21 (Unsupported): Trilium server platform as "Linux/Windows"
**Current text in draft**: `Self-hosted server (Linux/Windows) with desktop, web, and mobile clients syncing locally`  
**Problem**: The TriliumNext/Trilium GitHub README does not state that the server supports only "Linux/Windows." It says the app is "cross-platform" and discusses Docker for server deployment. The "Linux and Windows" server restriction came from the ORIGINAL (archived) zadam/Trilium project. The TriliumNext fork may support additional platforms. The self-hosted server + desktop/web/mobile sync is confirmed; the specific "Linux/Windows" qualifier for the server is not.  
**Quoted source (what the page actually says)**: "Synchronization with self-hosted sync server" and "Touch optimized mobile frontend for smartphones and tablets" — https://github.com/TriliumNext/Trilium  
**Fix**: Remove "Linux/Windows" platform qualifier OR verify from https://github.com/TriliumNext/Trilium documentation that the server is specifically Linux/Windows only. Suggested replacement: `Self-hosted server with desktop, web, and mobile clients syncing locally`
