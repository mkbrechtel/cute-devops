---
title: Release Flow 🎁
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

## Overview 📋

Releasing stays trunk-based until reality demands more: a release is an
**annotated tag on `main`** plus a changelog entry. Only when an older version
actually needs support does a `release/<x.y>` maintenance branch appear — the
escalation path, not standing structure. The shape borrows gitflow's release
and hotfix ideas but pays their cost strictly on demand; there is no `develop`
branch, ever.

## Goals 🎯

- Make the common case — release the tip of `main` — one tag and one
  changelog line.
- Support old versions when (and only when) users actually run them.
- Keep every release artefact in git: the tag names the commit, the tag
  message and changelog carry the notes.
- Avoid gitflow's standing ceremony for projects that don't need it yet,
  without blocking the projects that eventually do.

## Pattern Structure 📑

### Default: tags on main

```bash
git tag -a v1.4.0 -m "v1.4.0 — knot role, mail-stack hardening"
```

The changelog is a file in-tree, updated through the normal MR lifecycle
before tagging. Release notes for the website or a package index are built
from the tag and the changelog — the repo already holds everything.

### Escalation: a maintenance branch when needed

The trigger is concrete: a user is on `v1.4` and can't take `v1.5`, and a fix
must reach them. Then — and not before — cut the maintenance branch at the
release being maintained:

```bash
git branch release/1.4 v1.4.0
```

Fix on `main` first (the usual work branch + MR lifecycle), then backport:

```bash
git worktree add /work/foo/release/1.4 release/1.4
cd /work/foo/release/1.4
git cherry-pick <fix-commits>
git tag -a v1.4.1 -m "v1.4.1 — backport TLS default fix"
```

A fix that only applies to the old version is developed as a work branch cut
from `release/<x.y>` (stacked branching makes this natural) and merged into
the maintenance branch through the same MR convention as any other change.

### Retirement

A maintenance branch lives exactly as long as its version is supported. When
support ends, tag the last state if it isn't tagged already and archive the
branch — the tags carry the history.

```
main      ─●───●───●───●───●───●──►
            \        tag v1.5.0
    tag v1.4.0
              \
release/1.4    ●───●──► (only exists because someone needed it)
              cherry-picks, tag v1.4.1
```

## Security Considerations 🔐

- Sign release tags (`git tag -s`) — the tag is the artefact consumers verify.
- Backports are re-authored commits; the cherry-pick's `-x` marker keeps the
  traceable link to the reviewed original on `main`.
- Gate `release/*` branches like `main` — they are mainlines for their
  version, fed by MRs, not pushed to directly.

## Anti-Patterns ⚠️

- ❌ Standing gitflow: a permanent `develop`, release branches for every
  version regardless of whether anyone runs it. Structure without a user is
  pure carrying cost.
- ❌ Fixing on the maintenance branch first and forward-porting to `main`.
  `main` is where review and CI live; fix there, backport the accepted fix.
  (The exception is a fix that only applies to the old version.)
- ❌ Releasing from an untagged commit — "the deploy from last Tuesday" is not
  an addressable version.

## Best Practices 💡

- Keep versions boring: semver-ish `v<major>.<minor>.<patch>`, maintenance
  branches `release/<major>.<minor>`.
- Update the changelog in the same MR as the change, not in a scramble before
  the tag.
- Write the escalation trigger into the project docs ("we cut release
  branches when …") so nobody cuts one defensively.
- The `release` category in the work directory gives maintenance branches
  worktrees like any other work.

## Implementation Checklist ✅

- [ ] Changelog file in-tree, maintained through MRs.
- [ ] Annotated (ideally signed) tag per release on `main`.
- [ ] Documented trigger for cutting `release/<x.y>`.
- [ ] Backport flow: fix on `main`, cherry-pick with `-x`, patch tag on the
  maintenance branch.
- [ ] Archive maintenance branches when support ends.

## Related Patterns 🔗

- [Pure Git Project Workflows 🌻](./pure-git-project-workflows.md) — the
  umbrella.
- [MR Commits 💌](./mr-commits.md) — how changes reach `main` and
  `release/<x.y>` alike.
- [Shared Worktrees 🌳](./shared-worktrees.md) — stacked branching from a
  maintenance branch; the `release` category.

## References 📚

- gitflow — the ancestry of the release/hotfix branch shapes, adopted here
  only on demand.
