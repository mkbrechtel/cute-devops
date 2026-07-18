---
title: Pure Git Project Workflows 🌻
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

## Overview 📋

Run the whole project on git primitives — branches, commits, hooks, remotes,
worktrees — with **no forge at all**. Issues, merge requests, reviews, CI,
deployments, decisions: each is expressed as a git artefact following a small
convention, so the repository itself is the complete project platform. Anything
that reads those conventions (a CLI, a web UI, an AI agent) is a *view*; the
repo stays the single source of truth.

This is an umbrella pattern: it names the principle and the shared grammar, and
links the family of workflow patterns that implement each piece. Every piece is
**loosely coupled** — adopt one convention without the others, and let each
project decide how much process follows.

## Goals 🎯

- Give small teams an exit from forge weight (GitLab, GitHub) — self-hosted
  project life with nothing to operate beyond a git server.
- Give mixed human + AI-agent teams one primitive to learn: an agent that can
  run `git` can file issues, open MRs, review, and deploy.
- Give smalltown operators — one or two people running everything — the minimum
  number of moving parts.
- Make the whole project history — code, issues, MRs, reviews, decisions —
  greppable, fetchable, and preserved by `git clone`.
- Keep every convention independently adoptable; the integration surface is
  just commit-subject grammar and branch namespaces.

## Pattern Structure 📑

### The lifecycle, in git

```
 idea ──► issues/<slug>.md          (In-Tree Issues 🗂️)
       │
       ▼
 work branch in a worktree          (Shared Worktrees 🌳)
       │
       ▼
 empty commit "MR: <title>"         (MR Commits 💌) — ready for merging,
       │                             or skipped where review followed the
       ▼                             commits all along (Continuous Review 🫧)
 project convention: review, QA,    (Merge Reviews 🔍,
 testing, integration — or nothing   Optimistic Integration 🧺)
       │
       ▼
 maintainer merges into main
       │
       ▼
 tag — release branch when needed   (Release Flow 🎁)
```

Every arrow is a git operation. Nothing above requires a server-side
application; a bare repo with hooks is enough.

### The family

- [Shared Worktrees 🌳](./shared-worktrees.md) — where work happens: a bare
  repo, a shared work directory, one worktree per `<category>/<branch>`.
- [In-Tree Issues 🗂️](./in-tree-issues.md) — what to do: issues as markdown
  files in the repo, filed and resolved through the same lifecycle as code.
- [MR Commits 💌](./mr-commits.md) — the ready signal: an empty commit
  `MR: <title>` marks a branch ready for merging.
- [Optimistic Integration 🧺](./optimistic-integration.md) — combining
  in-flight work: `integration/<topic>` branches merge open work branches
  together before each has individually landed.
- [Merge Reviews 🔍](./merge-reviews.md) — reviewing what actually lands: a
  `review/merge-<commit>` branch whose subject is the merge commit itself.
- [Continuous Review 🫧](./continuous-review.md) — the alternative review
  track: commits are reviewed as they land, and a kept-pace branch merges
  without any MR ritual.
- [Release Flow 🎁](./release-flow.md) — shipping: tags on `main` by default,
  `release/<x.y>` maintenance branches only when an older version needs
  support.

### CI is a hook

The bare repo's `pre-receive` hook is the CI gate: lint, test, and policy
checks run before a ref moves, and a failing check rejects the push. A
`reference-transaction` hook reacts to refs that did move — syncing policy
files into the work directory, mirroring to remotes. There is no external CI
service to operate; the checks live in the repo and the hooks invoke them.

### Deployment is a push

A deployment target is a git remote with a receive hook. `git push deploy
main` *is* the deployment; rollback is pushing an older commit. See the
[Push-to-Deploy draft](../../issues/push-to-deploy.pattern.md) and the
[GitHub-for-deployments anti-pattern 🚫🐙](../../anti-patterns/github-for-deployments.md)
it replaces.

### Comms and decisions are commits

Changelogs, decisions, announcements, contributor lists — project memory lives
in-tree as files, changed through the same MR lifecycle. A new teammate (or
agent) reconstructs the project's state from `git log` alone; there is no chat
archive or wiki that the repo silently depends on.

### Tooling is a view

Conventions are chosen so that plain git is always sufficient: an MR is
readable with `git log`, a review with `git show`. Tools like
**gitflower** — a git-based development platform — discover the same
conventions and present them as a CLI and web UI (MR lists, review rendering).
Because the conventions carry all the state, tooling can be added, swapped, or
dropped without migrating anything.

## Security Considerations 🔐

- The access model is the git server's access model: Unix groups and
  filesystem permissions decide who writes which refs (see
  [Shared Worktrees 🌳](./shared-worktrees.md) for the split).
- Hooks are the policy surface — keep the bare repo's `hooks/` and `config`
  writable by the maintainer only.
- History is the audit log. Require signed commits or signed tags where
  attribution matters; an empty `MR:` or verdict commit is signable like any
  other commit.

## Anti-Patterns ⚠️

- ❌ Running a forge *and* the pure-git conventions in parallel — two sources
  of truth, one always stale. See
  [Don't introduce GitLab as the central DevOps Hub of your organization! 🔻🦊](../../anti-patterns/gitlab.md).
- ❌ Tooling that keeps state outside the repo (its own database of MRs or
  review verdicts). Views may cache; truth stays in refs and trees.
- ❌ Coupling the conventions tightly — requiring a review before every merge
  in a two-person project, or an integration branch for a one-line fix. Each
  project picks the process each change deserves.

## Best Practices 💡

- Start with one convention (usually MR Commits) and let the others in as the
  project actually needs them.
- Write the project's chosen conventions into `CLAUDE.md` / `README.md` in the
  work directory, so humans and agents discover the same rules.
- Keep the grammar boring and greppable: `MR:`, `integration/`, `review/`,
  `release/` — prefixes that `git log --grep` and `git for-each-ref` can
  answer questions about.

## Implementation Checklist ✅

- [ ] Bare repo with maintainer-owned `hooks/` and `config`
  ([Shared Worktrees 🌳](./shared-worktrees.md) — the `repos` role does this).
- [ ] `pre-receive` runs the project's checks; pushes to `main` restricted to
  the maintainer's merge.
- [ ] The conventions in use are documented in-tree.
- [ ] Optional: gitflower (or any other view) pointed at the repo.

## Related Patterns 🔗

All of [the family](#the-family), plus:

- [Smalltown Infrastructure 🏘️](./smalltown-infrastructure.md) — the
  infrastructure philosophy this workflow philosophy pairs with.
- [Pattern Pattern 🔷²](../meta/pattern.md) — how these documents are shaped.

## References 📚

- This repository runs on these workflows — `git log --grep '^MR:'` shows its
  merge requests; the branch list shows its `integration/` and `work/` traffic.
- gitflower — git-based development platform reading these conventions;
  deployable with the collection's `gitflower` role.
