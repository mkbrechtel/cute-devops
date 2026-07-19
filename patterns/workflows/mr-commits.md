---
title: MR Commits 💌
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

## Overview 📋

A merge request is an **empty commit on the work branch itself**, subject
`MR: <title>` — optionally scoped as `MR(<topic>): <title>` — body carrying the
description. It marks the branch **ready for merging** — everything before it
is work in flight; the MR commit is the boundary. What happens *after* the mark
is deliberately open: the project's own convention decides whether a review,
testing, QA, or nothing at all stands between the mark and the merge. The
coupling is loose by design.

## Goals 🎯

- Express "please merge this" as a git artefact — no forge, no ticket, no
  message that lives outside the repo.
- Keep the MR description versioned, greppable, and attached to exactly the
  commit range it describes; `git fetch` carries it everywhere the branch goes.
- Let any tool (or agent, or `git log`) list open merge requests from the refs
  alone.
- Prescribe only the ready-for-merging signal; leave review and QA process to
  each project.

## Pattern Structure 📑

### The commit

```bash
git commit --allow-empty -m "MR(feature/shared-worktrees): Shared worktrees layout

Replace the treehouse scaffold with a dedicated worktrees role that
manages the shared work directory.

FF-able onto main — this empty commit marks the merge request."
```

- **Subject**: `MR: <title>` — the `MR` prefix is the grammar; the title reads
  like a merge commit subject.
- **Scope** *(optional)*: `MR(<topic>): <title>`, the
  [Conventional Commits](https://www.conventionalcommits.org/) shape with `MR`
  as the type. The topic says what the request is *about*, so the subject stays
  self-describing when it is read away from its branch — in a merge log, in an
  integration basket listing, in the open-MR list. The **source branch name is
  the natural topic** and the one to reach for by default (`feature/new-api`
  for a branch stored as `work/feature/new-api` — drop whatever prefix the
  project namespaces its work branches with), but nothing binds the scope to a
  ref: any short topic that names the change honestly is valid.
- **Body**: the merge request description — motivation, summary of changes,
  anything a reviewer or maintainer needs.
- **Empty**: `--allow-empty`, no tree change. The commit is pure metadata, so
  it never conflicts and never alters what merges.

The author of the MR commit is the requester; sign the commit where
attribution matters.

### Discovery

Open MRs are branches whose history contains an `MR:` commit not yet
reachable from `main`:

```bash
git log --branches --not main --grep '^MR[(:]' --oneline
```

The `[(:]` character class matches both subject forms — scoped and unscoped —
since the scope is optional.

That one-liner is the MR list. gitflower reads the same convention and renders
it as a CLI and web view; nothing more than the refs is needed.

### Conclusion

The maintainer's merge into `main` (or into an integration branch — see
[Optimistic Integration 🧺](./optimistic-integration.md)) concludes the MR:
the `MR:` commit becomes reachable from the mainline and drops out of the open
list. The merge commit is the natural place to echo the MR title. A branch
that is abandoned instead is concluded by archiving it — the `MR:` commit
stays in its history as the record of what was asked.

### Loose coupling

The pattern ends at "this branch is ready for merging". Projects layer their
own follow-ups on that signal:

- a solo maintainer merges directly;
- a team runs a [Merge Review 🔍](./merge-reviews.md) first;
- several MRs are batched via
  [Optimistic Integration 🧺](./optimistic-integration.md);
- CI gates the merge in the bare repo's hooks.

None of those change the MR grammar, and the grammar doesn't require any of
them. The ritual as a whole is also optional: a branch under
[Continuous Review 🫧](./continuous-review.md) — commits reviewed as they
land — merges without any `MR:` commit, because there's no pent-up review the
mark would trigger.

## Security Considerations 🔐

- The MR commit's author claims the request — require signed commits if "who
  asked for this merge" must be non-forgeable.
- An empty commit is still a commit: pushing one is gated by the same ref
  permissions as any other push, so only people who can write the branch can
  mark it ready.

## Anti-Patterns ⚠️

- ❌ Describing the MR somewhere else (chat, email, a forge) and leaving the
  `MR:` body empty — the description belongs to the branch.
- ❌ Putting the ready-marker in a file instead of an empty commit. A file
  change can conflict, alters the merged tree, and needs cleanup after merge;
  the empty commit does none of that.
- ❌ Tooling that stores MR state (open/closed/assignee) outside the repo.
  Reachability from `main` *is* the state.

## Best Practices 💡

- Write the body like the merge commit message you'd want — the maintainer can
  reuse it directly.
- State the intended merge mechanics when it matters (e.g. *"FF-able onto
  main"*).
- Reference the issue the branch fulfils (`issues/<slug>.md`) in the body, so
  the request links intent to implementation.

## Implementation Checklist ✅

- [ ] Document the `MR:` grammar in the project's contribution docs /
  `CLAUDE.md`.
- [ ] Provide the discovery one-liner (or gitflower) so open MRs are visible.
- [ ] Decide and document what your project's convention between mark and
  merge is — even if it's "nothing".

## Related Patterns 🔗

- [Pure Git Project Workflows 🌻](./pure-git-project-workflows.md) — the
  umbrella.
- [Shared Worktrees 🌳](./shared-worktrees.md) — where the branch carrying the
  MR commit lives; committing there already publishes it.
- [Merge Reviews 🔍](./merge-reviews.md) and
  [Optimistic Integration 🧺](./optimistic-integration.md) — conventions
  projects commonly attach to the ready signal.
- [Continuous Review 🫧](./continuous-review.md) — the alternative track that
  skips the ready signal entirely: review follows the commits as they land.

## References 📚

- `git log --grep '^MR[(:]'` in this repository — the collection's own merge
  requests, e.g. *"MR(feature/shared-worktrees): Shared worktrees layout"*.
