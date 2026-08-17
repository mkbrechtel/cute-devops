---
title: Don't trust open-core docs about the open-source package! 🔻🎣
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

## The Pitch 📦

> *The vendor's documentation is the canonical reference for their
> software. If the docs describe versions, snapshots and a REST
> document API, then the package we `npm install` has versions,
> snapshots and a REST document API.*

## Why It's Tempting 🍬

- One domain, one nav, one voice — it reads like a single manual.
- The OSS package and the hosted product carry the same brand, and
  often the same page.
- Reading the source of a dependency to check the docs feels like
  paranoia.

## Why It's Not Cute 🔻

An open-core vendor's documentation is also its sales funnel. The
free package and the paid service get documented side by side,
because that adjacency is the point: every page that shows you what
the product *could* do is a page that might sell a plan.

The worked example that cost us planning time: Tiptap documents
**Hocuspocus** (the OSS `@hocuspocus/server`) next to paid **Tiptap
Collaboration** — document versions and snapshots, a REST document
API, document CRUD — in one continuous set of pages. Verified on
2026-08-12 against a running instance and its SQLite schema: the OSS
server keeps **one overwritten blob per document** and speaks **no
REST at all**. None of those features exist in the package you
install.

What this costs:

- **Planning against features that aren't there.** Colleagues read
  the docs, assumed version snapshots were built into Hocuspocus,
  and designed around them. The assumption survived until somebody
  opened the database.
- **The tier boundary is faint by construction.** Where it's marked
  at all, it's a small badge or a sentence halfway down the page —
  never a structural split in the navigation. Nothing about the
  reading experience tells you which half of the sentence you can
  actually run.
- **Search and AI answers flatten it further.** A search hit or a
  chat answer lands mid-page, stripped of whatever badge was
  carrying the distinction. The cheerful summary you get back is
  the merged feature set of both tiers.
- **Scaffolding as a funnel.** The vendor's OSS wrapper often adds
  little over the primitives it wraps, but it shapes your code
  toward the API of the paid service. By the time you hit the
  missing feature, the migration cost is on your side of the table.

## The Cute Alternative 💙

**Verify against the artifact, not the marketing site.** Read the
installed package's source, list its exported API, start it and look
at what it actually stores and serves. A schema dump and a `curl`
against the running thing settle in ten minutes what a documentation
argument doesn't settle at all.

**Name the tier before recommending.** In evaluations, issues and
architecture notes, state explicitly which features are in the OSS
package and which need a plan. Two lines up front save a design
round later.

**Prefer plain OSS primitives when the wrapper earns nothing.** For
collaborative editing that means yjs, y-websocket and y-protocols
directly, rather than vendor scaffolding that mostly re-exports
them. Small, replaceable parts you understand beat a branded layer
whose job is partly to introduce you to a price list.

**When the feature really is paid-only, decide it deliberately** —
buy it, or build it — as a decision with a name, not as a surprise
discovered mid-implementation.

## Related 🔗

- [Smalltown Infrastructure 🏘️](../patterns/workflows/smalltown-infrastructure.md) —
  *compose, don't adopt*: the principle this anti-pattern violates
  by outsourcing your understanding to a vendor's nav.
- [Don't introduce GitLab as the central DevOps Hub of your organization! 🔻🦊](./gitlab.md) —
  the same lock-in-by-feature-breadth shape, one purchase later.
