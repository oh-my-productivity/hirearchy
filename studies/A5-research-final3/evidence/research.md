# Research: Five Self-Hosted Note-Taking Apps

**Retrieval date:** 2026-10-17

## 1. Obsidian

### Pricing
**Free tier:** Core app is completely free with unlimited vaults and all core features. No sign-up required to download and use.

**Optional paid add-ons:**
- **Obsidian Sync:** $4 USD/user/month (billed annually) or $5 USD/user/month (billed monthly) — syncs notes across devices with end-to-end encryption
- **Obsidian Publish:** $8 USD/site/month (billed annually) or $10 USD/site/month (billed monthly) — publish notes as a website
- **Catalyst license:** $25 USD one-time payment — early access to beta versions and community badges (supports development)
- **Commercial license:** $50 USD/user/year — optional support license for organizations (not required for commercial use)

**Source:** https://obsidian.md/pricing  
**Quoted sentence:** "No. You are not *required* to pay for a commercial license, however if you are using Obsidian for work in an organization we encourage you to purchase a commercial license to keep Obsidian independent and 100% user-supported."

**Source:** https://obsidian.md/license  
**Quoted sentence:** "Obsidian is free for all purposes, including personal, commercial, and non-profit use."

### License
**License type:** Proprietary (free software)

Obsidian itself is free to download and use for all purposes (personal, commercial, non-profit, educational, government). The source code is not open source. Optional commercial licenses and catalyst licenses are available to support development but not required.

**Source:** https://obsidian.md/license  
**Quoted sentence:** "Obsidian is free for all purposes, including personal, commercial, and non-profit use. To support our development and help keep Obsidian 100% user-supported, you can optionally purchase a Catalyst or Commercial license."

### Sync Model
**Sync options:**
- **Local only:** Notes stored locally on device; no sync required
- **Official Obsidian Sync (paid):** $4-5 USD/month; end-to-end encrypted cloud sync across devices
- **Third-party options:** Can sync via iCloud, Dropbox, Google Drive, OneDrive, or other file sync services (free, but not officially supported)
- **Self-hosted:** No official self-hosted server; users can use third-party file sync services

**Source:** https://obsidian.md/sync  
**Quoted sentence:** "Obsidian Sync is a paid service enabling you to sync the desktop application with your mobile devices, all with end-to-end encryption."

---

## 2. Joplin

### Pricing
**Free tier:** Completely free and open source. Notes stored locally offline. Can sync using third-party services at no cost.

**Paid tiers (Joplin Cloud — managed hosting):**
- **Basic:** €2.99/month (pay monthly) or €2.40/month (annual: €28.69/year)
  - 2 GB storage, 10 MB per note/attachment limit
- **Pro:** €5.99/month (pay monthly) or €4.79/month (annual: €57.48/year)
  - 30 GB storage, 200 MB per note/attachment limit
- **Pro 100 GB:** €9.99/month (pay monthly) or €7.99/month (annual: €95.88/year)
  - 100 GB storage, 200 MB per note/attachment limit
- **Teams:** €7.99/month per user minimum 2 users (pay monthly) or €6.69/month (annual: €80.28/year)
  - 50 GB storage, 200 MB per note/attachment limit, multi-user collaboration

**Self-hosted option — Joplin Server Business:**
- €3.33/user/month (2-10 users)
- €2.92/user/month (11-50 users)
- €2.50/user/month (51+ users)
- Billed annually; 14-day free trial available

**Source:** https://joplinapp.org/plans  
**Quoted sentence:** "Basic 2.99€ /month (28.69€ /year )"

### License
**License type:** AGPL-3.0-or-later

Joplin is free and open-source software. The entire codebase is licensed under AGPL-3.0, with the exception of the server component which may have a different license (LICENSE.md file in packages/server).

**Source:** https://github.com/laurent22/joplin/blob/dev/LICENSE  
**Quoted sentence:** "All code in this repository is licensed under the AGPL-3.0-or-later License **unless a directory contains a LICENSE or LICENSE.md file**, in which case that file applies to the code in that sub-directory."

### Sync Model
**Sync options:**
- **Local only:** Notes stored offline on your computer by default
- **Joplin Cloud (paid):** Official managed cloud sync with end-to-end encryption; multiple pricing tiers
- **Joplin Server Business (self-hosted):** Self-hosted server option for organizations; source code available
- **Third-party services:** Can sync via Dropbox, OneDrive, Google Drive, WebDAV, Nextcloud, or S3 (free alternatives without official support)

**Source:** https://joplinapp.org/plans  
**Quoted sentence:** "Joplin Cloud allows you to synchronise your notes across devices. It also lets you publish notes, and collaborate on notebooks with your friends, family or colleagues."

---

## 3. Logseq

### Pricing
**Free tier:** Completely free. No payment required for local-first note-taking and all core features.

**Logseq Sync (beta — requires contribution/sponsorship):**
During public beta, Logseq Sync access requires an active Open Collective contribution (donation) of either $5/month or $15/month. A normal subscription system will be implemented when Sync launches to the general public. Exact pricing for public launch not yet announced.

**Planned future pricing:** Will implement a normal subscription system for Logseq Sync (specific pricing UNVERIFIED).

**Source:** https://blog.logseq.com/how-to-setup-and-use-logseq-sync/  
**Quoted sentence:** "During the beta test, we're giving all of our *active* Open Collective contributors access to Logseq Sync. That means you need to have *monthly recurring *donation of either [$5 per month][21] or [$15 per month][22]. We'll implement a normal subscription system once we launch Sync to the general public."

### License
**License type:** GNU Affero General Public License (AGPL-3.0)

Logseq is free and open-source software. The code is publicly available on GitHub under the AGPL-3.0 license. Both desktop and web apps remain free for all users (personal and commercial) when data is stored locally.

**Source:** https://github.com/logseq/logseq/blob/master/LICENSE.md  
**Quoted sentence:** "The GNU Affero General Public License is a free, copyleft license for software and other kinds of works, specifically designed to ensure cooperation with the community in the case of network server software."

**Source:** https://discuss.logseq.com/t/commercial-use-license/29715  
**Quoted sentence:** "Logseq has a GNU AGPL license (see below)."

### Sync Model
**Sync options:**
- **Local only (default):** Notes stored locally as plaintext files; no sync required
- **Third-party file sync:** Can sync using iCloud, Dropbox, OneDrive, Google Drive, or any folder sync service (free)
- **Logseq Sync (beta/future paid service):** Official cloud sync with end-to-end encryption; currently in public beta requiring Open Collective sponsorship; pricing for general public launch UNVERIFIED
- **Smart Merge (experimental):** Allows editing the same page on multiple devices simultaneously

**Source:** https://blog.logseq.com/how-to-setup-and-use-logseq-sync/  
**Quoted sentence:** "But as I explained above, we will keep supporting and developing the plaintext versions/modes of Logseq, which work with any regular file sync solution."

---

## 4. Trilium Notes

### Pricing
**Free tier:** Completely free and open source. Core application with no paid features required.

**Paid hosting option — Trilium.cc (third-party hosted service):**
- **Monthly:** $3.50 USD/month
- **Annual:** $36 USD/year (15% discount)
- **Annual with custom domain:** $52 USD/year (includes full custom domain of choice)
- No hard storage limit, but soft limit on media/large files

**Self-hosted:** Free when self-hosted on your own server

**Source:** https://trilium.cc/  
**Quoted sentence:** "$3.50/month gets you a hosted Trilium Notes instance you can connect to from anywhere."

**Source:** https://trilium.cc/  
**Quoted sentence:** "In addition, you can pay yearly with a plan that costs **$36/yr **(a 15% discount)."

### License
**License type:** AGPL-3.0 (GNU Affero General Public License)

Trilium Notes is free and open-source software. The entire project is licensed under AGPL-3.0, allowing free use, modification, and distribution under the terms of that license.

**Source:** https://github.com/TriliumNext/Trilium/blob/main/LICENSE  
**Quoted sentence:** "This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version."

### Sync Model
**Sync options:**
- **Local only (desktop/web):** Run on your own machine or server; notes stored locally
- **Self-hosted server:** Synchronization with self-hosted sync server (free, open source)
- **Third-party hosting:** Services like Trilium.cc offer hosted instances ($3.50-52 USD/year)
- **Desktop-to-server sync:** Seamless synchronization between desktop app and self-hosted server
- **Mobile:** Web app available on mobile through browser; native Android and iOS apps available as third-party clients

**Source:** https://github.com/TriliumNext/Trilium/blob/main/README.md  
**Quoted sentence:** "[Synchronization][246] with self-hosted sync server * there are [3rd party services for hosting synchronisation server][247]"

---

## 5. AnyType

### Pricing
**Free tier:** Basic services always free. Unlimited local use.
- Local storage and offline access
- 100 MB storage on the Anytype network (files only)
- 10 shared channels
- Limited to personal use

**Paid tiers (Personal — for individual subscriptions):**
Pricing page exists but exact tiers not fetched. Students/educators get 50% discount. Contributors get 50% discount.

**Anytype for Business (team version):**
- **Cloud-hosted:** €20/editor/month (save 20% with annual billing)
  - 14-day free trial, no credit card required
  - 30-day money-back guarantee
  - Viewers are free (only editors count toward seat count)
- **Self-hosted (coming soon):** €300/month flat regardless of team size
  - Full Business feature set with organization-controlled infrastructure

**Source:** https://doc.anytype.io/anytype-docs/memberships/monetization  
**Quoted sentence:** "Those who would like to purchase a name in the Anytype naming system or access priority support, can purchase a membership at the same price as other beta testers."

**Source:** https://business.anytype.io/  
**Quoted sentence:** "€20per editor / month Save 20% with annual billing"

**Source:** https://doc.anytype.io/anytype-docs/memberships/monetization  
**Quoted sentence:** "Students or faculty members are eligible for a [50% discount][70] on all of our membership plans."

### License
**License type:** Cooperative Open Source / Source Available (not fully open source)

**Core infrastructure (MIT-licensed, open source):**
- `any-sync` (data exchange protocol)
- `any-block` (data protocol)

**Application layer (Any Source Available License — NOT open source):**
- `anytype-js` (TypeScript/JavaScript client)
- `anytype-swift` (iOS app)
- `anytype-kotlin` (Android app)
- `any-heart` (middleware library)

The Any Source Available License grants individuals freedom to review, modify, and utilize code for personal, academic, scientific, research, and development purposes, but requires consent from the Any Association for commercial use.

**Source:** https://blog.anytype.io/our-open-philosophy/  
**Quoted sentence:** "While our core solutions, the infrastructure protocol *any-sync*, and the data protocol *any-block*, are released as open source under the permissive MIT license, we distribute the remaining layers, including the middleware library *any-heart*, and applications like *anytype-js*,* anytype-swift*, and *anytype-kotlin*, under the Any Source Available License. This license grants individuals the freedom to review, modify, and utilize the code for personal, academic, scientific, research, and development purposes. However, for commercial use, consent from the Any Association is required."

### Sync Model
**Sync options:**
- **Local-first by default:** Data stored on your device first; works offline
- **Official Anytype Sync (personal app):** End-to-end encrypted, zero-knowledge cloud backup (included in free tier with 100 MB limit; paid tiers offer more storage)
- **Peer-to-peer sync:** Can sync between multiple devices of same user
- **Shared channels (collaboration):** Invite others to shared spaces; paid tiers unlock unlimited shared channels
- **Self-hosted (Anytype for Business):** Coming soon; €300/month flat; self-hosted deployment option for teams

**Source:** https://business.anytype.io/  
**Quoted sentence:** "Your local data stays on your devices. Anytype is local-first, so the source of truth lives with you, not on our servers."

**Source:** https://business.anytype.io/  
**Quoted sentence:** "€300 / month, flat Regardless of team size. Self-hosting isn't available at launch — it's coming soon."

---

## Summary Table

| App | Pricing | License | Sync Model |
|-----|---------|---------|-----------|
| **Obsidian** | Free core app; Optional Sync ($4-5/mo), Publish ($8-10/mo), Commercial license ($50/yr) | Proprietary (free to use) | Local only; Paid official Sync (E2E encrypted); Third-party file sync (free) |
| **Joplin** | Free core app; Cloud tiers €2.99-9.99/mo or free third-party sync; Self-hosted Server €2.50-3.33/user/mo | AGPL-3.0 (open source) | Local only; Paid Joplin Cloud (E2E encrypted); Third-party sync (free); Self-hosted server |
| **Logseq** | Free core app; Logseq Sync in beta (requires $5-15/mo Open Collective donation) | AGPL-3.0 (open source) | Local only; Third-party file sync (free); Paid Logseq Sync (beta, E2E encrypted) |
| **Trilium Notes** | Free core app; Optional third-party hosting Trilium.cc ($3.50-52/yr) | AGPL-3.0 (open source) | Local only; Free self-hosted server; Paid third-party hosting available |
| **AnyType** | Free tier (100 MB limit); Paid personal tiers (exact pricing UNVERIFIED); Business €20/editor/mo or €300/mo self-hosted | MIT (infrastructure) + Source Available (apps; commercial use requires permission) | Local-first; Cloud backup; Paid business tiers unlock unlimited sharing; Self-hosted (coming soon) |

---

## Data Quality Notes

**Verified (current as of 2026-10-17):**
- Obsidian pricing and license (directly from official pricing and license pages)
- Joplin pricing and license (from official plans page and GitHub LICENSE file)
- Logseq license (from GitHub and community forum; sync pricing in beta)
- Trilium license and pricing (from GitHub and Trilium.cc hosted service)
- AnyType license and business pricing (from blog and business.anytype.io)

**UNVERIFIED:**
- Logseq Sync exact pricing for public launch (currently in beta with Open Collective requirement)
- AnyType personal tier exact pricing structure (page exists but full pricing matrix not fetched)
- Exact storage limits on AnyType free tier (stated as "100 MB for files" but details on other content types unclear)

**Out of scope:**
- Feature comparison beyond sync/pricing/license
- Performance benchmarks
- User reviews or community sentiment
- Desktop vs. mobile app availability details (all support multiple platforms but not comprehensively documented per app)
