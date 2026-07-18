<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# git_hooks

Deploys a machine-wide git hooks directory (`/etc/git/hooks`, set via `git config --system core.hooksPath`) with an extensible `.d` layout:

- **Dispatcher** — the same script installed under every managed hook name. It runs every executable in `<hook>.d/`, then chains to the repository's own `hooks/<hook>` — so per-repo hooks (like pod's `post-receive` deploy trigger) keep firing even though `core.hooksPath` shadows them.
- **`reference-transaction.d/50-autopush`** — a static script (no templating): whenever a branch or tag changes, it pushes the update to every remote whose `remote.<name>.autopush` git config is `true`. All configuration is per remote; repos without autopush-enabled remotes make it a no-op.
- **`check-tree` + `check-tree.d/`** — pluggable tree validation. `check-tree <tree-ish>` exports the tree and runs every check against it; `check-tree.d/50-reuse` validates REUSE compliance. `pre-receive.d/50-check-tree` gates incoming pushes with it.

Pairs with the [`repos`](../repos/README.md) role, which declares the per-remote `autopush` config from `repos[].remotes[].auto_push`.

## Requirements

- Ansible >= 2.14
- Debian 13 (trixie) on the target; `reuse` installed if the REUSE check should be active.

## Role Variables

- `git_hooks_dir` (default: `/etc/git/hooks`) — the global hooks directory.
- `git_hooks_hooks` — hook names that get the dispatcher. Defaults to every common client- and server-side hook; hooks whose mere existence changes git's behaviour (`proc-receive`, `push-to-checkout`, `fsmonitor-watchman`) are deliberately excluded.
- `git_hooks_dotd` — `.d` directories created up front; any `<hook>.d` directory works once created.
- `git_hooks_with_check_tree` (default: `true`) — install the check-tree driver, the REUSE check, and the pre-receive gate.

## Example

```yaml
- hosts: village
  become: true
  roles:
    - role: osahris.cute_devops.git_hooks
```

## License

EUPL-1.2
