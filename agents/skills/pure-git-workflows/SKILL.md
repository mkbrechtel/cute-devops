---
# SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
# SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
#
# SPDX-License-Identifier: EUPL-1.2

name: pure-git-workflows
description: Operate a pure-git project — no forge; branches, commits, and hooks carry the whole lifecycle. Use when starting or concluding work, proposing a merge, integrating open branches, reviewing a merge, filing issues, or cutting a release in a shared-worktree repository.
---

# Pure Git Workflows

You are working in a project that runs entirely on git primitives. There is no
forge: merge requests, reviews, issues, and releases are all git artefacts
following the conventions below. The full patterns live in
`patterns/workflows/` (start with `pure-git-project-workflows.md`); this skill
is the operational summary.

## Ground rules

- Never commit to or push `main` — the maintainer merges; hooks reject
  everything else.
- Every commit on a shared-worktree branch is published the moment it's made.
  Never rebase or rewrite a branch that others may have seen; append instead.
  Rewriting is reserved for the maintainer's explicit instruction.
- All state lives in git. A decision, finding, or request that exists only in
  chat didn't happen — put it in a commit, a file, or a ref.

## Do work: one worktree per task

Work happens at `/work/<project>/<category>/<branch>` on branch
`work/<category>/<branch>`. Create it with the EnterWorktree tool (name
`<category>/<branch>`), or by hand:

```bash
git -C /srv/repos/<project>.git worktree add \
  /work/<project>/<category>/<slug> -b work/<category>/<slug> <base>
```

`<category>` is a grouping folder (`feature`, `fix`, `docs`, …, created on
demand); `<slug>` is lowercase `a-z0-9`, starts with a letter, has at least one
`-`, at most 40 chars. Base is `main` when starting from the work directory;
inside a worktree, new branches stack on the current branch.

## Propose a merge: the `MR(<branch>):` commit

When the branch is ready for merging, add an empty commit. The subject follows
Conventional Commits: `MR` as the type, the source branch (minus the `work/`
prefix) as the scope. The body carries the description — reuse-ready as a merge
commit message; note mechanics like "FF-able onto main":

```bash
git commit --allow-empty -m "MR(<category>/<branch>): <title>

<why and what; reference issues/<slug>.md if one exists>"
```

List open MRs: `git log --branches --not main --grep '^MR[(:]' --oneline`
(the character class also matches the older unscoped `MR:` subjects).
What follows the mark — review, QA, nothing — is the project's convention, not
yours to assume. A superseding `MR(<branch>):` commit updates the request.

## Integrate open branches: `integration/<topic>`

To combine several open work branches into one reviewable, testable basket:
cut `integration/<topic>` from `main`, `git merge --no-ff` each candidate
branch, resolve conflicts in the merge commits, test the combination, and
finish with an `MR(<branch>):` commit listing the contents. Never do feature work on the
integration branch — stack a work branch on it instead. If a branch isn't
ready, rebuild the basket without it; integration branches are disposable
scaffolding.

## Review a merge: `reviews/merge-<sha>`

Reviews target the actual merge commit. Cut a worktree at it
(`work/reviews/merge-<short-sha>`), then on that branch:

- record findings as gitflower `.review` files or as `issues/*.md` (mark
  blocking ones);
- fix what's easier fixed than described, as normal commits;
- close with an empty verdict commit: `APPROVE: merge-<sha>` or
  `REQUEST-CHANGES: merge-<sha>`, findings in the body.

Unresolved non-blocking findings stay as `issues/*.md` and land in-tree when
the review branch merges.

## Continuous review

The alternative to the MR ritual: commits are reviewed as they land, each
getting a `.review` keyed by its SHA on `refs/notes/reviews`
(`gitflower review` scaffolds the delta since the last `[Review]` merge).
Fixes are follow-up commits on the same branch. A branch whose review stream
kept pace merges without any `MR(<branch>):` commit.

## Issues

Issues are markdown files: `issues/<slug>[.<type>].md`. Filing one is a branch
plus an MR adding the file; merging it means the project accepts the issue.
Review findings ride the review branch instead of getting their own.

## Releases

Releases are annotated tags on `main`, with the changelog updated in the same
MR as the change — not in a scramble before tagging. Cut `release/<x.y>` only
when an older version actually needs a fix; backport with `cherry-pick -x`
and tag patch releases from the maintenance branch.
