---
title: Shared Worktrees 🌳
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

## Overview 📋

A bare git repository lives on one host. Next to it sits a shared **work
directory** — a plain directory whose `.git` file points back at the bare repo.
From the work directory you can `git log` and `git branch` the live project to
**look things up**, and from it everyone spawns their own **worktrees**: private
checkouts built on the same tree everyone else is building on.

A worktree is light, spawnable, easy to dismantle — cut a branch, do your work,
remove it. Filesystem permissions decide who can write where, and `git worktree`
itself guarantees that no two worktrees share a branch. Every worktree name is
`<category>/<branch>`, and new branches stack: from the work directory they cut
from `main`, from inside a worktree they cut from the branch you're already on.

Two small Ansible roles set this up, and they're independent: one makes the bare
repo, the other adds the work directory on top.

## Goals 🎯

- Give every contributor an isolated working tree without the cost of managing a full clone per person.
- Let teammates read each other's in-progress work without races or permission gymnastics.
- Push access control down to the kernel and git hooks — no bespoke "who can touch this branch" service.
- Keep CI / linting / agent config inside the repo, so a fresh worktree works the moment it exists.
- One primitive (`git worktree`) for everyone; no bespoke way to set up a development environment.
- Make branching *stack* by default, so work-in-review doesn't block the work that builds on it.
- Get transparency on what happens in the project by just looking at the files — make `ls /work/<project>` the honest answer to "what's everyone working on right now?"

## Pattern Structure 📑

### The bare repo and the work directory

The bare repo is the project's canonical store; the work directory is where
people live while they work. They're separate paths:

```
/srv/repos/foo.git/                   ← the project; bare repo
├── HEAD, refs/, objects/, info/      ← standard bare-repo internals
├── worktrees/                        ← git's per-worktree metadata
├── config                            ← holds cute.workdir = /work/foo
└── hooks/
    ├── pre-receive                   ← CI gate
    └── reference-transaction         ← main-line policy + config sync

/work/foo/                            ← the shared work directory; 3775 (rwxrwsr-t)
├── .git                              ← file: "gitdir: /srv/repos/foo.git" (lookup pad)
├── CLAUDE.md                         ← how to look things up + spawn a worktree
├── feature/                          ← category folder; 3775, same as work dir
│   └── cute-thing/                   ← worktree, branch feature/cute-thing
└── fix/                              ← category folder
    └── login-redirect/               ← worktree, branch fix/login-redirect

/etc/claude/hooks/                    ← machine-wide Claude Code hooks (see below)
├── worktree-create                   ← creates a worktree for Claude
├── worktree-remove
└── require-clean                     ← Stop gate: no ending on a dirty worktree
```

The bare repo stands on its own — it's a complete git repository and works with
no work directory at all. The work directory is a convenience layer bolted on
top: delete it and the repo is untouched.

### The `.git` file is a read-only lookup pad

`/work/foo/.git` is not a directory — it's a one-line file, `gitdir:
/srv/repos/foo.git`. That makes `/work/foo` a git working area pointed straight
at the bare repo, so `git log`, `git branch`, `git show main:path` all answer
against the live project without a checkout. Because the bare repo has
`core.bare = true`, git reports the pad as bare and refuses to treat it as an
editable tree — you can read the project from here, but you can't accidentally
start editing files at the top level. Look things up here; do work in a worktree.

### Every worktree is a public branch

A worktree shares its bare repo's objects and refs database. A commit in
`/work/foo/feature/cute-thing/` lands immediately in
`foo.git/refs/heads/feature/cute-thing` — no `git push` step, because
there's nowhere separate to push to. As soon as you commit, your work is part of
the bare repo's history.

The flip side is delightful: **use the bare repo as a git remote and `git fetch`
pulls every worktree's live state**. From any other machine:

```bash
git remote add foo ssh://host/srv/repos/foo.git
git fetch foo
git log foo/feature/cute-thing     # alice's in-progress work
git log foo/fix/login-redirect      # whatever Claude is doing
```

No "publish my branch" ritual. Active work is *already published* the moment
it's committed. (`main` of course stays gated by the maintainer's merge ritual;
we're talking about the in-flight `<category>/<branch>` worktree branches.)

### Names: `<category>/<branch>`

Every worktree is named `<category>/<branch>`, and that shape is both the
directory layout and a soft taxonomy:

- `<category>` is simply a **folder** under the work directory that groups
  related work — no allowlist. Each category folder carries the same `3775`
  permissions as the work directory, and a new one is created on demand. A fresh
  project starts with `feature`, `fix`, `hotfix`, `refactor`, `test`, `ci`,
  `chore`, `docs`, `update`, `experiment`, `release`.
- `<branch>` is a URL slug: lowercase `a-z`/`0-9`, starts with a letter,
  contains at least one `-`, at most 40 characters.

So `feature/add-dns-role`, `fix/login-redirect`, `experiment/new-router`. The
worktree lives at `/work/foo/<category>/<branch>`; the git branch carries the
very same name, `<category>/<branch>` — creating one by hand with a plain
`git worktree add` and going through the hooks give identical results. Grouping
worktrees under category folders keeps `ls
/work/foo` self-organising instead of a flat wall of names, with nothing to
configure — the folders are the taxonomy.

### Stacked branching

The base of a new branch depends on **where you create it**:

- **From the work directory** (or anywhere not inside a worktree) the pad's
  `HEAD` is `main`, so the new branch cuts from `main`.
- **From inside an existing worktree** the new branch cuts from *that worktree's
  current branch*.

That second case is the point: when you've opened `feature/big-thing` and it's
sitting in review, you can open `fix/follow-up` *from inside it* and keep
building on top instead of waiting for the merge. Each branch is still a flat
git ref; the "stack" is just the commit each one was cut from.

### One branch ⇄ one worktree

Git already refuses to check out the same branch in two worktrees. Lean on that:
the branch *is* the worktree, and the existence of the directory is the lock. No
external coordination needed.

```
$ git -C /srv/repos/foo.git worktree add /work/foo/feature/cute-thing -b feature/cute-thing main
fatal: 'feature/cute-thing' is already checked out at
       '/work/foo/feature/cute-thing'
```

### Permissions & trust

Membership in the project's Unix group (typically `devops`) is the access
primitive: being in the group lets you `git worktree add`, commit, and read
everyone else's worktree. Removal from the group revokes all of it at once. No
application-level user database, no per-branch ACL — the kernel decides.

`git worktree add` writes into the bare repo (it creates `worktrees/<name>/`
metadata) and into the work directory (the checkout itself). So group members
need write access to parts of the bare repo *and* to `/work/foo` (and its
category folders). But both also hold **policy** — the bare repo's `hooks/` and
`config`, and the work directory's `.git` file and `CLAUDE.md` — that must not
be edited in place.

Split write access rather than blanket group-writable:

| Path | Who needs write |
|---|---|
| bare `refs/`, `objects/`, `info/`, `logs/`, `packed-refs`, `worktrees/` | group members (so `git worktree add` works) |
| bare `hooks/`, `config`, `description` | maintainer only — git's own policy surface |
| `/work/foo/` and its category folders (to create worktrees) | group members |
| `/work/foo/.git`, `CLAUDE.md` | maintainer only — our policy surface |
| `/etc/claude/`, managed settings | root only — deployed by configuration management |

Concretely: `git init --bare --shared=group`, `chgrp -R devops foo.git`, strip
group-write off `foo.git/{hooks,config,description}`; create `/work/foo` and each
category folder mode `3775` (setgid + sticky + group write) and strip group-write
off the policy files inside it. The setgid + sticky bits mean new worktrees
inherit the group and nobody can delete a neighbour's — the same permission story
as `/tmp`.

Policy files still need to be *changed* — just not in place. The work
directory's `CLAUDE.md` is **tracked content on `main`**, and a
`reference-transaction` hook syncs the new tree into the work directory after
every successful merge. Edit it the same way you edit any other file: in your
own worktree, via an MR, merged into `main`. The project updates itself. The
Claude Code hooks are deliberately *not* per-project content — they live in
`/etc/claude`, deployed by configuration management (see below).

The hook scripts resolve the work directory from `cute.workdir` in the bare
repo's config (recorded once by the role), so they spawn worktrees at the right
level whether they're invoked from the pad or from inside another worktree.

### Claude Code integration

**Claude Code already has a worktree isolation feature.** From the CLI, `claude
--worktree feature/my-thing` spawns a session in a fresh worktree; from inside an
existing session, asking Claude to call `EnterWorktree` does the same thing. Both
routes go through the `WorktreeCreate` hook, which runs the same `git worktree
add` under the hood.

**The hooks are machine policy, not project content.** Claude Code loads
`.claude/settings.json` only from the session's own project root — it does *not*
inherit settings from parent directories the way `CLAUDE.md` does, and hooks
from *every* settings scope run in addition to each other. Per-project copies
therefore mean one copy per pad plus one tracked in every repo, kept in sync
forever — and any drift or duplication bites. Deploy the hook scripts **once per
host** instead: scripts in `/etc/claude/hooks/`, wired up by a [managed
settings](https://code.claude.com/docs/en/settings) drop-in that applies to every
session on the machine:

```json
// /etc/claude-code/managed-settings.d/50-cute-devops.json
{
  "worktree": { "bgIsolation": "worktree" },
  "hooks": {
    "WorktreeCreate": [{"hooks": [{"type": "command",
      "command": "/etc/claude/hooks/worktree-create"}]}],
    "WorktreeRemove": [{"hooks": [{"type": "command",
      "command": "/etc/claude/hooks/worktree-remove"}]}],
    "Stop": [{"hooks": [{"type": "command",
      "command": "/etc/claude/hooks/require-clean"}]}]
  }
}
```

Because the hooks now fire in every repo on the host, they choose the layout by
where they run:

- a repo with a **shared work directory** (`cute.workdir` set in the bare repo's
  config): worktrees at `<workdir>/<category>/<branch>` on a branch of the same
  name — this pattern's layout;
- **any other checkout** (say, a personal clone under `$HOME`): worktrees
  collect inside the clone at `<clone>/work/<name>` on branch `<name>`.

The create hook does what a human runs by hand, with the untrusted-input jobs a
typed command doesn't need: it validates the name strictly, ensures the parent
folder exists (category folders created with `3775` on demand), cuts the branch
from `main`, and prints the path. The remove hook refuses any path outside where
the create hook creates, then calls `git worktree remove`.

The **`Stop` hook** (`require-clean`) refuses to let a session end while its
worktree has uncommitted changes — so work always lands as a commit, and git's
own `pre-commit` / `pre-push` hooks (lint, tests) get a chance to gate it. It
only enforces inside *linked* worktrees: the bare pad has no work tree, and a
primary checkout (someone's own clone, their own WIP) is not the hook's
business. `bgIsolation: "worktree"` tells background sessions to auto-isolate
into their own worktree.

## Security Considerations 🔐

- **Input validation in the `WorktreeCreate` hook is load-bearing.** The hook pulls a name out of an untrusted JSON payload. Validate strictly (category a lowercase folder slug; branch matching `^[a-z][a-z0-9]*(-[a-z0-9]+)+$`, ≤40 chars) and reject anything else — don't sanitise-and-continue. A typed-in `git worktree add` doesn't have this problem; the hook does.
- **The remove hook must geofence to the work directory.** A typo (or a prompt-injected agent) shouldn't be able to delete arbitrary paths — only a worktree directly inside `/work/<project>/`.
- **The `.git` pad is read-only by construction.** It reports as bare, so nobody edits the project at the top level by accident. Keep the `.git` file itself out of group-write so a member can't repoint it.
- **No network surface added.** The bare repo is reached via local filesystem permissions; there's no extra daemon to harden.
- **Ownership = authorship.** Every commit in a worktree is made by the Unix user who owns it. `git log` and `stat` agree on who did what.
- **Isolation is per worktree, not per process.** Anyone running as user `alice` (whether Alice or a Claude session she started) can read every other worktree on the host. That's a feature for collaboration; pair it with a system-level sandbox if you need stronger separation.
- **The managed settings drop-in is policy.** It controls what an agent may do, machine-wide. It lives in `/etc`, root-owned, deployed by configuration management — review changes like CI config, never edit it in place on the host.

## Anti-Patterns ⚠️

- ❌ **Editing at the top of the work directory.** The pad is for looking things up; it reports as bare so git stops you. Do work in a worktree.
- ❌ **Blanket group-write on the whole bare repo or work directory.** Everyone then has write access to `hooks/` and the policy files. Split permissions and sync policy files from `main`.
- ❌ **A helper script that wraps `git worktree add` for humans.** A line of plain git does the job; validation belongs in the `WorktreeCreate` hook (which has untrusted input), not in a third place.
- ❌ **A clone per user.** Wastes disk, hides in-progress work behind `ssh`, makes "what is everyone doing?" a coordination problem instead of an `ls`.
- ❌ **One shared worktree with branch switching.** Two contributors will collide on `git checkout` within the first hour. Git designed worktrees specifically to make this unnecessary.
- ❌ **Letting an agent share its driver's worktree.** Either you race the agent for the file lock, or you serialise edits by hand. Give the agent its own worktree with `EnterWorktree` or `claude --worktree`.
- ❌ **Tracking who-owns-what in Slack / a wiki / a spreadsheet.** `ls -l /work/<project>` is the truth; anything else drifts.
- ❌ **An allowlist of categories in a config file.** Categories are just folders; the `<category>/<branch>` shape is the discipline. Let a new category folder appear when someone needs it.
- ❌ **Long-lived worktrees.** A branch that lingers past its merge turns `ls /work/<project>` from a current-work view into archaeology.
- ❌ **Two `CLAUDE.md` files.** The work directory's `CLAUDE.md` is the one an agent reads on landing; write one doc and sync it from `main`.

## Best Practices 💡

- **Look things up from the pad, work in a worktree.** `git log` / `git branch` at `/work/<project>`; edit only inside `/work/<project>/<category>/<branch>`.
- **Build on review explicitly.** New branches are always cut from `main`; when follow-up work depends on an open MR, merge that branch in from inside the new worktree (`git merge <category>/<branch>`) so the dependency is visible in the log.
- **Keep the category folders few and honest.** A handful of categories that mean something beats a taxonomy nobody reads.
- **Pair this with [[in-tree-issues]]** so the same merge ritual governs both code and the issues that describe it.
- **Sync policy from `main`, never edit it in place.** The work directory's `CLAUDE.md` is a tracked file; a `reference-transaction` hook updates the live copy after each successful merge. The Claude Code hooks are machine policy in `/etc/claude`, updated only by configuration management.
- **Remove worktrees on merge.** If the branch is gone from `main`, the worktree should be too. A short cron that prunes stale, merged-and-empty worktrees keeps `/work/<project>` tidy.
- **Put CI / lint inside the bare repo's `hooks/`.** A fresh worktree inherits them by being a worktree of the bare repo; there is nothing to install.

## Implementation Checklist ✅

### Set up the bare repo

- [ ] `git init --bare --shared=group /srv/repos/foo.git`, owned by the project Unix group (e.g. `devops`).
- [ ] Strip group-write on policy paths: `chmod -R g-w foo.git/{hooks,config,description}`.
- [ ] Seed `main` with a first commit (the maintainer's initial import).

### Set up the work directory

- [ ] Create `/work/foo` with `chmod 3775` (setgid + sticky + group write), owned by the maintainer, group `devops`.
- [ ] Write `/work/foo/.git` containing `gitdir: /srv/repos/foo.git`; keep it out of group-write.
- [ ] Record the path: `git --git-dir=/srv/repos/foo.git config cute.workdir /work/foo`.
- [ ] Create the starter category folders (`feature/`, `fix/`, …) at `chmod 3775`, same as the work directory.
- [ ] Write `/work/foo/CLAUDE.md` (how to look things up + spawn a worktree).
- [ ] Add `/work/` (or the specific paths) to `.gitignore` on `main` so worktree checkouts don't try to track the work directory.

### Wire the Claude path

- [ ] Install the hook scripts machine-wide in `/etc/claude/hooks/` (root-owned, `0755`) and wire them up in a managed settings drop-in (`/etc/claude-code/managed-settings.d/`), with `"worktree": {"bgIsolation": "worktree"}`. No per-repo `.claude/settings.json` — hooks from every settings scope run *in addition* to each other, so per-repo copies would fire twice.
- [ ] `worktree-create`: read the JSON from stdin, validate the name strictly, resolve the layout (`cute.workdir` set → `<workdir>/<category>/<branch>`; otherwise `<clone>/work/<name>`), ensure the parent folder exists (`3775` in a work directory), cut the branch from `main`, run `git worktree add`, print the path.
- [ ] `worktree-remove`: refuse any path outside where `worktree-create` creates, then call `git worktree remove`.
- [ ] `require-clean` (the `Stop` hook): block the session from ending while `git status` in the worktree is dirty; only enforce in linked worktrees — the bare pad and primary checkouts are left alone.
- [ ] Strip group-write on `/work/foo/.git` and `CLAUDE.md`.

### Protect the mainline

- [ ] In `foo.git/hooks/`, set a `reference-transaction` policy on `main` (fast-forward-only, merge-commit-only) — see [[in-tree-issues]] for the shape.
- [ ] Extend the same hook to sync the work directory's `CLAUDE.md` from the new tree after every successful merge.
- [ ] Optionally, a `pre-receive`/`update` hook that rejects any branch (apart from `main`) whose shape isn't `<category>/<branch>` — see [[worktree-branch-shape]].
- [ ] Add `pre-receive` / `update` hooks for CI and lint that every push must satisfy.
- [ ] Auto-push `main` to your public mirrors from the same hook.

## Possible Implementations 🛠️

- [`osahris.cute_devops.repos`](../../roles/repos/README.md) — sets up the plain bare git repo: `git init --bare --shared=group`, group ownership, `description`, and group-write stripped off the policy paths.
- [`osahris.cute_devops.worktrees`](../../roles/worktrees/README.md) — adds the shared work directory on top of a bare repo: the `/work/<project>` directory at `chmod 3775`, the `.git` lookup pad, the starter category folders, and the `CLAUDE.md` landing doc, and records `cute.workdir` in the bare repo's config.
- [`osahris.cute_devops.claude_code`](../../roles/claude_code/README.md) — deploys the Claude Code hooks machine-wide: `worktree-create` / `worktree-remove` / `require-clean` in `/etc/claude/hooks/`, wired up by a managed settings drop-in.

## Related Patterns 🔗

- [Pure Git Project Workflows 🌻](./pure-git-project-workflows.md) — the umbrella: the whole project lifecycle on git primitives, with this pattern as the "where work happens" piece.
- [Smalltown Infrastructure 🏘️](./smalltown-infrastructure.md) — the bigger picture these repos sit in: small, legible, operable by the team you actually have.
- [In-Tree Issues 🗂️](./in-tree-issues.md) — pair the worktree ritual with the same merge ritual for issues; both flow through `main`.
- [Worktree Branch Shape 🪧](../../issues/worktree-branch-shape.pattern.md) — *(absorbed)* the `<category>/<branch>` discipline, now a core rule of this pattern.
- [Village of Villages 🏘️](../../issues/village-of-villages.pattern.md) — *(draft)* multi-repo extension: a thin org directory wrapping several bare repos, each with its own work directory.
- [Push to Deploy 🚀](../../issues/push-to-deploy.pattern.md) — *(draft)* extends the lifecycle with a `git push` to a deploy remote; same primitive, no extra protocol.
- [Cuteness Pattern 🌸](../meta/cuteness.md) — why a line of plain git and an `ls /work/<project>` are friendlier than a sprawl of clones.

## References 📚

- `git-worktree(1)` — the primitive everything sits on.
- `git-init(1)` — `--bare`, `core.sharedRepository`, and the conventional `.git` suffix.
- `gitrepository-layout(5)` — what a `.git` *file* (`gitdir: …`) means.
- `chmod(1)` — the setgid + sticky combination (`3775`) is the whole permission story for the work directory.
