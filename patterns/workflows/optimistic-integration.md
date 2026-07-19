---
title: Optimistic Integration 🧺
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

## Overview 📋

An `integration/<topic>` branch **optimistically merges open work branches
together** — before any of them has individually landed on `main`. The
combination is testable as a whole, conflicts between in-flight branches
surface early, and the maintainer can accept a whole basket of work with one
merge. Review — typically a [Merge Review 🔍](./merge-reviews.md) of the
integration merge — happens on the combined result instead of on each piece
separately. How the basket is proposed is the project's own convention:
commonly an [MR commit 💌](./mr-commits.md), but the pattern doesn't require
one — plain feature branches integrate just as well, with the merge commits
themselves as the review surface.

## Goals 🎯

- Stop work-in-review from serialising: branches that build on or touch the
  same areas are combined and exercised together while each is still in
  flight.
- Find inter-branch conflicts when they're written, not when the second branch
  finally merges.
- Give the maintainer one reviewable, testable artefact — the integration
  merge — for a set of related changes.
- Keep integration disposable: an integration branch is cheap to rebuild with
  a different selection of work.

## Pattern Structure 📑

### Building the basket

```bash
git worktree add /work/foo/integration/mail-stack \
  -b integration/mail-stack main
cd /work/foo/integration/mail-stack
git merge work/feature/dovecot-role
git merge work/feature/postfix-role
git merge work/fix/tls-defaults
```

Cut `integration/<topic>` from `main`, then merge the candidate work branches
into it. Conflicts are resolved in the integration branch's merge commits —
that resolution work is itself content the maintainer gets to see. The
underlying work branches are untouched; where they carry their own MRs, those
stay open.

### Proposing the basket

When the combination builds, tests, and reads well, the basket is ready —
signalled however the project signals readiness. Under
[MR Commits 💌](./mr-commits.md), that's an `MR:` commit describing what's
inside:

```
MR(integration/merge-open-branches): Integrate the open work branches

Merges work/feature/dovecot-role, work/feature/postfix-role and
work/fix/tls-defaults; resolves the shared template conflict in the
dovecot/postfix pair.
```

A project without the MR ritual integrates plain feature branches and lets
review target the merge commits themselves — the basket's merges are a
complete review surface (see [Merge Reviews 🔍](./merge-reviews.md)), so
nothing about the pattern changes except the mark.

The maintainer merging `integration/<topic>` into `main` concludes everything
inside the basket at once. Where the branches carry `MR:` commits, each is
concluded along the way — it becomes reachable from `main` through the
integration merge.

### Optimism and its refunds

The integration is *optimistic*: nothing in the basket has been individually
accepted yet. When a branch turns out not to be ready — review findings, a
failing combination, a change of plan — rebuild the basket without it:

```bash
git branch -f integration/mail-stack main   # or a fresh topic name
git merge work/feature/dovecot-role work/fix/tls-defaults
```

The dropped branch is unharmed and can land later on its own. Integration
branches carry no unique work except conflict resolutions, so rebuilding one
is cheap; treat them as scaffolding, not as history to preserve.

### Reviewing the combination

Because the deliverable is a merge commit, review naturally targets that merge
— see [Merge Reviews 🔍](./merge-reviews.md). The review covers exactly what
will land, including the conflict resolutions, rather than N separate diffs
that were never tested together.

## Security Considerations 🔐

- An integration branch aggregates other people's work — the integrator's
  merge commits attest the combination, not the contents. Individual
  attribution stays on the work branches' own commits.
- Gate `main` the same as always: the integration branch is proposed by the
  project's convention and merged by the maintainer, never pushed to `main`
  directly.

## Anti-Patterns ⚠️

- ❌ Doing feature work directly on the integration branch. New work gets its
  own work branch (stacked, if it builds on the basket); the integration
  branch only merges and resolves.
- ❌ A standing, ever-growing `integration` branch that never lands — that's a
  fork of `main` in disguise. Baskets are per-topic and short-lived.
- ❌ Rewriting the underlying work branches to make the integration merge
  cleaner. The work branches are published, shared state (see
  [Shared Worktrees 🌳](./shared-worktrees.md)); resolve in the merge instead.

## Best Practices 💡

- Name the topic after the basket's purpose (`integration/mail-stack`,
  `integration/merge-open-branches`), not after a date or a person.
- List the merged branches when proposing the basket — in the `MR:` body, if
  the project uses one — so the maintainer sees the basket's contents without
  walking the graph.
- Run the full test suite on the integration branch — exercising the
  combination is the point.
- Delete or archive the integration branch after it lands; the merge into
  `main` preserves everything worth keeping.

## Implementation Checklist ✅

- [ ] `integration` category available in the work directory (it's just a
  folder — created on demand).
- [ ] Cut from `main`, merge candidate work branches, resolve conflicts in the
  integration branch.
- [ ] Test the combination.
- [ ] Signal readiness the project's way (typically an `MR:` commit listing
  the contents); maintainer merges to `main`.
- [ ] Clean up the integration branch afterwards.

## Related Patterns 🔗

- [Pure Git Project Workflows 🌻](./pure-git-project-workflows.md) — the
  umbrella.
- [MR Commits 💌](./mr-commits.md) — the usual way the basket is proposed;
  optional, as ever.
- [Merge Reviews 🔍](./merge-reviews.md) — reviewing the integration merge
  itself.
- [Shared Worktrees 🌳](./shared-worktrees.md) — integration branches live in
  worktrees like everything else.

## References 📚

- `integration/merge-open-branches` in this repository —
  *"MR(integration/merge-open-branches): Integrate the open work branches"*,
  merged into `main` as one basket.
