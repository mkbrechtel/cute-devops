---
title: Continuous Review 🫧
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

## Overview 📋

The alternative to marking a branch ready and reviewing at merge time: **review
commits as they land**. In a [shared-worktree 🌳](./shared-worktrees.md) world
every commit is published the moment it's made, so a reviewer can follow along
delta by delta instead of facing one lump at the end. Each reviewed commit gets
a `.review` keyed by its SHA on a notes ref; findings are fixed as follow-up
commits on the same branch; and because review keeps pace with the work,
merging needs no [MR 💌](./mr-commits.md) ritual at all — by the time the
branch is complete, there is nothing left to review.

## Goals 🎯

- Deliver findings while the author's context is fresh — minutes after the
  commit, not days after the branch.
- Spread review effort across the work instead of a big-bang session at merge
  time.
- Make review coverage queryable: which commits carry a `.review`, which don't.
- Let a continuously-reviewed branch merge without ceremony.

## Pattern Structure 📑

### The review stream

Reviews live on a git notes ref — `refs/notes/reviews` by default — keyed by
the reviewed commit's SHA, one `.review` file per commit (the dot-review
format's one-object scope). The stream is plain git:

```bash
git notes --ref reviews show <sha>        # read a commit's review
git fetch origin 'refs/notes/reviews:refs/notes/reviews'
```

gitflower's `gitflower review` is the comfortable front-end: it scaffolds a
review covering **everything that changed since the last review** — the base is
the most recent `[Review]` merge on the branch, falling back to `main` — and
persists to the same notes ref. Re-running is non-destructive; the next session
picks up the next delta.

### Marking the high-water line

`gitflower review merge` attaches a finished review session to the branch
history as a merge commit whose subject is prefixed `[Review]`, carrying the
verdict summary and a recipe pointing at the notes content. That merge is the
visible high-water line: everyone sees in `git log` how far review has
followed, and the next review scaffolds from exactly there.

### Fixes are follow-up commits

A finding worth acting on becomes a commit on the same branch — pushed by the
reviewer or the author, whoever gets there first. Review and work interleave on
one shared branch rather than alternating turns. Findings not worth a commit
right now become [in-tree issues 🗂️](./in-tree-issues.md), same as in a
[Merge Review 🔍](./merge-reviews.md).

### Merging without ceremony

When the branch is complete and the review stream has kept pace, the
maintainer merges — no `MR:` commit, no at-merge review. The reviews travel
with the notes ref, so the judgment trail survives the merge exactly like the
commits do.

The coupling stays loose: continuous review and the
[MR Commits 💌](./mr-commits.md) ritual coexist in one project. A long-running
branch with an engaged reviewer runs continuously; a drive-by fix still gets
marked with an `MR:` commit and reviewed at merge time. The grammar of each
convention tells everyone which track a branch is on.

## Security Considerations 🔐

- The notes ref is a ref like any other: whoever can write
  `refs/notes/reviews` can write reviews. Gate it with the same ref
  permissions as branches, and require signed notes commits where reviewer
  attribution must be non-forgeable.
- A `[Review]` merge's verdict summary is only as trustworthy as its author —
  a `pre-receive` check can verify that merges into `main` are covered by
  verdicts from authorised reviewers, same as in at-merge review.

## Anti-Patterns ⚠️

- ❌ A stream that silently lags. Continuous review that stopped three weeks
  ago looks like coverage but isn't — if the reviewer can't keep pace, fall
  back honestly to a [Merge Review 🔍](./merge-reviews.md) at the end.
- ❌ Findings delivered in chat while following along. The notes ref is the
  record; a finding that never reached a `.review` or an issue file didn't
  happen.
- ❌ Rewriting reviewed commits. Rebasing a published branch orphans every
  per-SHA review behind it — the branch is shared state
  (see [Shared Worktrees 🌳](./shared-worktrees.md)); append, don't rewrite.

## Best Practices 💡

- Configure remotes to fetch and push `refs/notes/reviews` alongside branches,
  so reviews mirror wherever the code does.
- Land `[Review]` merges regularly — small deltas review better, and the
  high-water line keeps the next session's scaffold small.
- Fix small findings yourself as you review; reserve issue files for what
  genuinely needs the author or a later decision.

## Implementation Checklist ✅

- [ ] Notes ref agreed (default `refs/notes/reviews`) and included in
  fetch/mirror configuration.
- [ ] Reviewer follows landing commits — `gitflower review`, or hand-written
  `.review` content on the notes ref.
- [ ] Findings: fix commits on the branch, or `issues/*.md` for the rest.
- [ ] `[Review]` merges mark how far review has followed.
- [ ] Maintainer merges a kept-pace branch without further ritual.

## Related Patterns 🔗

- [Pure Git Project Workflows 🌻](./pure-git-project-workflows.md) — the
  umbrella.
- [MR Commits 💌](./mr-commits.md) — the ready-then-merge ritual this pattern
  replaces on branches where review keeps pace; both tracks coexist.
- [Merge Reviews 🔍](./merge-reviews.md) — the at-merge alternative; same
  `.review` format, per-merge instead of per-commit.
- [Shared Worktrees 🌳](./shared-worktrees.md) — publish-on-commit is what
  makes following along possible.
- [In-Tree Issues 🗂️](./in-tree-issues.md) — where unresolved findings go,
  whichever review mode found them.

## References 📚

- gitflower's `gitflower review` specification
  (`docs/spec/gitflower-review.md` in the gitflower repository) — scaffolding
  since the last `[Review]` merge, the TUI, and `refs/notes/reviews`
  persistence.
- gitflower's dot-review format specification
  (`docs/spec/dot-review-format.md`) — the `.review` file format shared with
  [Merge Reviews 🔍](./merge-reviews.md).
