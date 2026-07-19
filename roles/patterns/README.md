<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# Patterns Role

Installs the **Cute DevOps Patterns!** library — `patterns/` and
`anti-patterns/`, plus their index files — onto a managed host at
`/opt/cute-devops`, so people at a shell and agents working in a worktree can
read the project's shared vocabulary locally, without network access.

The content ships inside the collection artifact (`patterns/` and
`anti-patterns/` are not in `galaxy.yml`'s `build_ignore`), so the role works
the same from a git checkout and from
`ansible-galaxy collection install osahris.cute_devops`.

## What lands on the host

```
/opt/cute-devops/
├── README.md           ← generated landing doc, points at both libraries
├── patterns.md         ← Patterns! 🔷 index
├── patterns/           ← about/, workflows/, development/, operation/, meta/
├── anti-patterns.md    ← Anti-Patterns! 🔻 index
└── anti-patterns/
```

Directories are `0755`, files `0644`, owned by `root:root` — documentation, so
world-readable. Nothing on the host is expected to write here.

The mirror is **pruning**: the role walks the source tree with
`community.general.filetree`, so it knows the exact set of paths that should
exist and removes anything else under `patterns/` and `anti-patterns/`. A
renamed or deleted pattern disappears from the host on the next run instead of
lingering as a stale second copy.

## Requirements

- Ansible >= 2.14, `community.general` (already a collection dependency).
- Debian 13 (trixie); nothing beyond a writable `/opt`.

## Role Variables

```yaml
patterns_dest: /opt/cute-devops   # where the library lands
patterns_owner: root
patterns_group: root
patterns_dir_mode: "0755"
patterns_file_mode: "0644"
```

## Example

```yaml
- hosts: devbox
  become: true
  roles:
    - role: osahris.cute_devops.patterns
```

Then, on the host:

```bash
ls /opt/cute-devops/patterns/workflows/
grep -ril worktree /opt/cute-devops/patterns/
```

## Telling agents it's there

The [worktrees role](../worktrees/README.md) scaffolds a work directory's
`CLAUDE.md` with a section pointing at this path, so an agent starting work in a
worktree knows the library exists and where to read it. Its
`worktrees_patterns_dir` should match `patterns_dest` if you move either.

## What this role does NOT do

- Render or serve the patterns as a website. That's `website/`, deployed to
  <https://cute-devops.patterns.how> from CI.
- Install the roles themselves — this is documentation only.
- Register anything as a Claude Code plugin marketplace or skills directory.

## Implements

- [In-Tree Issues 🌲](../../patterns/workflows/in-tree-issues.md) — the same
  instinct, applied to patterns: keep the shared vocabulary next to the work
  that uses it rather than behind a browser tab.

## License

EUPL-1.2
