---
title: Merge Reviews 🔍
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

## Overview 📋

The review targets **the actual merge commit** — not a branch diff that may
differ from what finally lands. A branch `review/merge-<merge-commit-id>` is
cut at the merge being reviewed, and the review happens *on that branch, in
git*: findings are recorded in-tree, fixes are pushed as commits, and the
verdict is an empty commit in the same grammar as an
[MR commit 💌](./mr-commits.md). Findings that stay unresolved but shouldn't
block the merge survive as in-tree issues, so nothing a reviewer noticed
evaporates when the review closes.

## Goals 🎯

- Review what will actually be merged — including conflict resolutions, which
  a per-branch diff never shows.
- Keep the review itself a git artefact: fetchable, greppable, signable, and
  preserved with the project's history.
- Let fixes land as part of the review instead of bouncing "please change X"
  across a chat tool.
- Give leftover findings a durable home as issues instead of losing them with
  the review.

## Pattern Structure 📑

### The review branch

The name pins the subject: `review/merge-<merge-commit-id>` reviews exactly
that merge commit, independent of any branch labels that may later move.

```bash
git worktree add /work/foo/review/merge-4f551d4 \
  -b review/merge-4f551d4 4f551d4
```

Typical subject: the merge produced by an
[Optimistic Integration 🧺](./optimistic-integration.md) basket, proposed via
its `MR(…)` commit. The same shape reviews any merge commit.

### What lands on the branch

**Findings**, recorded one of two ways:

- **`.review` files** — gitflower's dot-review format: a single-file,
  markdown-ish review of one git object, addressed by its SHA. A merge
  commit's `.review` quotes the merge with one diff subsection per parent, and
  reviewer events (comments, questions, verdicts) anchor to lines of that
  quoted content. Readable without tooling; gitflower renders and appends to
  it.
- **`issues/*.md` files** — findings phrased as plain
  [in-tree issues 🗂️](./in-tree-issues.md). A finding can be marked
  **blocking**: the review isn't approvable while it stands unresolved.

**Fix commits** — a finding that's easier to fix than to describe is fixed
right there on the review branch; the commit resolves the finding.

**A verdict** — an empty commit closing the review in the `MR(…)` grammar's
sibling forms, e.g.:

```
APPROVE: merge-4f551d4

Both roles read well together; the template conflict resolution is
correct. Two non-blocking naming remarks filed as issues.
```

or `REQUEST-CHANGES: merge-4f551d4` with the blocking findings in the body.

### Conclusion

An approved review branch is merged by the maintainer: the fix commits land,
and the unresolved non-blocking findings arrive in the tree as regular
`issues/*.md` entries — open issues whose origin is the review. A
requested-changes verdict sends the work back; a reworked merge is a new merge
commit, and its review is a new `review/merge-<id>` branch, so every review
stays pinned to the exact object it judged.

### Two origins of issues

Issues born in reviews ride the review branch into the tree, as above. Issues
from reporters — a bug report, a feature idea — instead get their own branch
and MR per [In-Tree Issues 🗂️](./in-tree-issues.md). Same files, same
directory, two doors in; `git log --follow` on the issue file tells you which
door it came through.

## Security Considerations 🔐

- The verdict commit's author is the approver — require signed commits where
  approval must be non-forgeable, and gate the merge on a verdict from an
  authorised reviewer if the project needs enforced review (a `pre-receive`
  check can verify this).
- `.review` files carry their own SPDX headers — a review is a copyrightable
  artefact of its reviewer.

## Anti-Patterns ⚠️

- ❌ Reviewing the work branch's diff and then merging something else — the
  merge commit, with its conflict resolutions, is what ships; review that.
- ❌ Verdicts or findings held in an external tool. The review branch is the
  review; tooling only renders it.
- ❌ Silently fixing findings on the branch without recording them — the fix
  commit's message should name the finding so the review reads as a
  conversation.
- ❌ Discarding unresolved findings when the review closes. Non-blocking
  leftovers become issues; that's the pattern's whole tail end.

## Best Practices 💡

- Keep one `.review` per reviewed object (the merge commit), per the
  dot-review format's one-object scope; extra per-file depth gets its own
  anchored sections.
- Distinguish blocking from non-blocking findings explicitly — it decides
  between `APPROVE:` and `REQUEST-CHANGES:`.
- Let the author push fixes onto the review branch too; review is a
  collaboration on the same shared branch, not a turn-based exchange.

## Implementation Checklist ✅

- [ ] `review` category available in the work directory.
- [ ] Cut `review/merge-<id>` at the merge commit under review.
- [ ] Record findings (`.review` and/or `issues/*.md`, blocking marked).
- [ ] Push fixes for what's fixable; file issues for the rest.
- [ ] Close with a verdict commit; maintainer merges an approved review.

## Related Patterns 🔗

- [Pure Git Project Workflows 🌻](./pure-git-project-workflows.md) — the
  umbrella.
- [MR Commits 💌](./mr-commits.md) — the grammar the verdict commits extend.
- [Optimistic Integration 🧺](./optimistic-integration.md) — the usual source
  of merges worth reviewing.
- [In-Tree Issues 🗂️](./in-tree-issues.md) — where unresolved findings live
  on.
- [Continuous Review 🫧](./continuous-review.md) — the review-as-you-go
  alternative: same `.review` format, per landed commit instead of per merge.

## References 📚

- gitflower's dot-review format specification (`docs/spec/dot-review-format.md`
  in the gitflower repository) — the `.review` file format: header block,
  quoted git content, reviewer events, verdict states.
