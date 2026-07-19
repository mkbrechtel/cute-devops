<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# logind

Configures `systemd-logind` so a user's session infrastructure — their
`user@<uid>.service` manager and `/run/user/<uid>` — outlives their last
logout by a useful margin instead of the stock ten seconds.

Long enough that a process started on Friday afternoon is still there on
Monday morning; short enough that an abandoned session is reclaimed on a
shared machine. This is the host-wide alternative to per-user
`loginctl enable-linger`: one drop-in covers everybody who logs in, with no
per-user state to maintain.

Rootless podman needs the user manager and runtime directory to persist
across disconnects, so this role is what lets containers survive a closed
browser terminal.

## Requirements

- Debian 12/bookworm or 13/trixie

## Role Variables

See `defaults/main.yaml` for all available variables and their default values.

- `logind_user_stop_delay` (default: `"72h"`) - How long the user manager and
  runtime directory are kept after the user's last session ends
  (`UserStopDelaySec`)
- `logind_kill_user_processes` (default: `false`) - Terminate session
  processes at logout (`KillUserProcesses`). Leave off, or the retention
  window has no effect on anything started from a shell
- `logind_dropin` (default:
  `/etc/systemd/logind.conf.d/10-session-retention.conf`) - Drop-in file
  managed by this role

## Notes

`KillUserProcesses` and `UserStopDelaySec` act on different cgroup trees.
Session processes — `tmux`, a long-running build, anything started from a
shell — live in `session-<n>.scope`, which `KillUserProcesses` terminates at
logout. The user manager and the services under it, including rootless
podman containers, live in `user@<uid>.service`, which `UserStopDelaySec`
governs. Turning `logind_kill_user_processes` on would kill shell jobs
immediately while leaving containers running for the full window.

With the default off, the session scope is abandoned rather than terminated
and its processes keep running. They are reclaimed when the retention window
expires and logind tears down the user's slice.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: devboxes
  become: yes
  roles:
    - role: osahris.cute_devops.logind
      vars:
        logind_user_stop_delay: "96h"
```
