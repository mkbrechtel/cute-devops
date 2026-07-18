<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# Claude Code Role

Deploys Claude Code's worktree hooks **once, machine-wide**: hook scripts in
`/etc/claude/hooks/`, wired up through a [managed settings](https://code.claude.com/docs/en/settings)
drop-in in `/etc/claude-code/managed-settings.d/`. Every repo on the host gets
the same behaviour — no per-repo `.claude/` scaffolding, no sync-on-merge.

- **`worktree-create` / `worktree-remove`** — Claude Code's `WorktreeCreate` /
  `WorktreeRemove` hooks. Where the worktree lands depends on the repo:
  - a repo with a **shared work directory** (the `cute.workdir` git config set
    by the [worktrees role](../worktrees/README.md)): `<workdir>/<category>/<branch>`
    on a branch of the same name — the Shared Worktrees 🌳 layout;
  - **any other checkout** (e.g. a personal clone under `$HOME`):
    `<clone>/work/<name>` on branch `<name>`, where `<name>` is a plain
    `<branch>` slug or `<category>/<branch>`.

  New branches are always cut from `main` (the repo's `HEAD` branch if there is
  no `main`). The remove hook only ever deletes below where the create hook
  creates.
- **`require-clean`** — a `Stop` hook that blocks a session from ending while
  its worktree has uncommitted changes, so work always lands as a commit. It
  only enforces inside *linked* worktrees; a primary checkout (someone's own
  clone with their own WIP) and bare lookup pads are left alone.

Because hooks from all settings scopes run **in addition to** each other, don't
also keep per-repo copies of these hooks in `.claude/settings.json` — they
would fire twice.

## Requirements

- Ansible >= 2.14
- Debian 13 (trixie); `git` and bash on the target.
- Claude Code new enough to read `managed-settings.d/` drop-ins.

## Role Variables

Defaults (see `defaults/main.yml`):

- `claude_code_hooks_dir: /etc/claude/hooks`
- `claude_code_managed_settings_dropin: /etc/claude-code/managed-settings.d/50-cute-devops.json`
- `claude_code_with_require_clean: true`

## Example

```yaml
- hosts: village
  become: true
  roles:
    - role: osahris.cute_devops.claude_code
```

## Implements

- [Shared Worktrees 🌳](../../patterns/approaches/shared-worktrees.md) — the Claude Code integration half.

## License

EUPL-1.2
