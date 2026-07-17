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
    auto_push: false                # per-repo override of repos_with_auto_push
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
- `repos_with_auto_push: false`

### Remotes

Each entry in `remotes` needs a `name` and a `url`; the role adds the remote
(or updates its URL) in the bare repo. Existing remotes not listed are left
alone.

### Auto-push

With `auto_push: true` the role installs a `reference-transaction` git hook
in the bare repo: whenever a branch or tag changes — a push into the repo, a
commit in a shared worktree, a merge — the update is pushed on to every
configured remote in the background (deletions propagate too). Per remote,
`auto_push: false` opts that remote out (the hook only pushes to remotes
whose `remote.<name>.autopush` git config is true).

Notes:

- The push runs as whichever user updated the ref, so everyone in the repo
  group needs credentials for the remotes (e.g. ssh keys / agent).
- Pushes are non-forced; rejections and other failures are appended to
  `autopush.log` in the bare repo.
- The hook file is Ansible-managed while `auto_push` is true (it overwrites a
  hand-rolled `reference-transaction` hook). With `auto_push` false the role
  never touches the hook.

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

- [Shared Worktrees 🌳](../../patterns/approaches/shared-worktrees.md) — the bare repo half.

## License

EUPL-1.2
