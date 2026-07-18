<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# Repos Role

Sets up plain **bare git repositories** on the target host: `git init --bare
--shared=group`, group ownership, a `description`, and group-write stripped off
the policy paths (`hooks`, `config`, `description`). Nothing more — a bare repo
is a complete, self-contained thing.

To add the shared work directory on top (the `/work/<project>` lookup pad,
`CLAUDE.md`, categories, and Claude Code worktree hooks for stacked branching),
apply [`osahris.cute_devops.worktrees`](../worktrees/README.md) afterwards. The
two roles are independent: a bare repo works fine without worktrees, and
worktrees can point at any bare repo however it was created.

## Requirements

- Ansible >= 2.14
- Debian 13 (trixie); `git` and POSIX shell on the target.

## Role Variables

```yaml
repos:
  - name: foo                       # short label (optional; defaults to basename of path)
    path: /srv/repos/foo.git        # required; absolute path on target, ends in .git
    group: devops                   # group that shares the repo (defaults to repos_default_group)
    owner: root                     # who owns policy files (defaults to repos_default_owner)
    description: "A cute project."  # optional; written to the bare repo's `description`
    remotes:                        # optional; git remotes to configure on the bare repo
      - name: github
        url: git@github.com:foo/foo.git
      - name: codeberg
        url: ssh://git@codeberg.org/foo/foo.git
        auto_push: false            # exclude this remote from auto-push (default true)
```

Defaults (see `defaults/main.yml`):

- `repos_default_group: devops`
- `repos_default_owner: root`

### Remotes

Each entry in `remotes` needs a `name` and a `url`; the role adds the remote
(or updates its URL) in the bare repo. Existing remotes not listed are left
alone.

### Auto-push

Auto-push is configured **per remote**: each declared remote gets a
`remote.<name>.autopush` git config (true unless the entry sets
`auto_push: false`). The hook that acts on it is machine-wide — the
[`git_hooks`](../git_hooks/README.md) role's
`reference-transaction.d/50-autopush` — so this role only writes config,
no hook files. Whenever a branch or tag changes — a push into the repo, a
commit in a shared worktree, a merge — the update is pushed on to every
autopush-enabled remote in the background (deletions propagate too).

Notes:

- The push runs as whichever user updated the ref, so everyone in the repo
  group needs credentials for the remotes (e.g. ssh keys / agent).
- Pushes are non-forced; rejections and other failures are appended to
  `autopush.log` in the bare repo.
- The role removes `reference-transaction` hook files it templated into
  bare repos in earlier versions; the global hook replaces them.

## Example

```yaml
- hosts: village
  become: true
  roles:
    - role: osahris.cute_devops.repos
      vars:
        repos:
          - name: foo
            path: /srv/repos/foo.git
            description: "A cute project."
    # optional: add the shared work directory + worktree hooks
    - role: osahris.cute_devops.worktrees
      vars:
        worktrees:
          - name: foo
            repo: /srv/repos/foo.git
```

## What this role does NOT do

- Set up the shared work directory or worktree hooks — that's `osahris.cute_devops.worktrees`.
- Wire up branch policy / sync-on-merge in the `reference-transaction` hook. The optional `auto_push` hook only mirrors refs to remotes; anything beyond that is project-specific — see the pattern.
- Create or manage Unix groups / users. Use `osahris.cute_devops.users` for that.
- Push initial content into `main`. That's the maintainer's first commit.

## Implements

- [Shared Worktrees 🌳](../../patterns/workflows/shared-worktrees.md) — the bare repo half.

## License

EUPL-1.2
