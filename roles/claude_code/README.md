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
- **`trust-work-dirs`** (opt-in) — a `SessionStart` hook that marks the work
  base directories (default `/work`) as trusted in the user's
  `~/.claude.json`. Trust is inherited from ancestors, so one trusted base
  covers every pad and worktree below it. The fleet view (`claude agents`)
  silently refuses to run worktree hooks from an untrusted directory and
  misreports it as a hook failure — deleting sessions then fails. Claude Code
  has no supported way to pre-trust directories centrally
  ([anthropics/claude-code#23109](https://github.com/anthropics/claude-code/issues/23109));
  re-seeding on every session start stands in for that, and heals the flag
  when an exiting Claude Code process rewrites `~/.claude.json` from a stale
  snapshot ([#36403](https://github.com/anthropics/claude-code/issues/36403)).
  Opt-in because it writes to user configuration.

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
- `claude_code_bg_isolation: none` — managed `worktree.bgIsolation` policy:
  `none` pins background-session worktree isolation off machine-wide,
  `worktree` enforces it (the Shared Worktrees setup), `false` omits the key
  so lower settings scopes decide
- `claude_code_with_trust_work_dirs: false` — deploy the `SessionStart` trust
  seeding hook
- `claude_code_trust_work_bases: [/work]` — work bases the trust hook considers

## Example

```yaml
- hosts: village
  become: true
  roles:
    - role: osahris.cute_devops.claude_code
```

## Implements

- [Shared Worktrees 🌳](../../patterns/workflows/shared-worktrees.md) — the Claude Code integration half.

## License

EUPL-1.2
