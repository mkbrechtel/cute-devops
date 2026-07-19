---
status: draft
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# logind

## Goal

A `logind` role that configures `systemd-logind` so a user's session infrastructure — the `user@<uid>.service` manager and `/run/user/<uid>` — outlives their last logout by a useful margin instead of the stock ten seconds. Long enough that a process started on Friday afternoon is still there on Monday morning; short enough that a genuinely abandoned session is reclaimed on a shared machine.

## Scope

**Retention window.** The role writes a drop-in under `/etc/systemd/logind.conf.d/` setting `UserStopDelaySec=` from `logind_user_stop_delay`, default `72h`. logind keeps the user record and `user@<uid>.service` — and with them the user's runtime directory and any `systemctl --user` services — for that long after the user's last session ends. Reconnecting inside the window rejoins the existing environment; rootless podman containers, `tmux`, and long-running jobs are simply still running.

**Cleanup preserved.** After the window expires the normal teardown runs. This is a multi-user system: a user who has not looked at their session for three days can be cleaned up, and anything worth keeping is worth restarting.

**Session-process survival.** The role asserts `KillUserProcesses=no` explicitly rather than relying on the Debian default, so a distribution change or a stray local edit cannot quietly undermine the retention window.

The drop-in carries the managed-file header from [coding conventions](../improve/coding.md), and configuration changes notify a handler that applies them to the running `systemd-logind`.

## Design notes

This is the host-wide alternative to per-user `loginctl enable-linger`. Both keep a user's systemd instance alive independently of their sessions, but linger is per-user state that something has to maintain as users come and go, while `UserStopDelaySec=` is one file that covers everybody who ever logs in.

That matters for [ttyd](ttyd.feature.md): a browser terminal is exactly the kind of session a user closes and reopens all day, and rootless podman inside it needs the user manager and runtime directory to persist across those gaps. With this role deployed, ttyd needs no per-user session management of its own.

## Open questions

- Confirm that `/run/user/<uid>` survives the delay window, not just `user@<uid>.service`. `logind.conf(5)` documents the user record and per-user service being kept; the runtime directory's lifetime is tied to that record but not spelled out. Verify in the VM test: open a session, end it, check the directory is still present after the last session exits.
- Whether `systemd-logind` accepts a reload for this setting or needs a restart, and what a restart costs on a host with live sessions.
- Whether `RemoveIPC=` needs to be aligned with the retention window, or whether its cleanup already follows the same user-record lifecycle.

# Considerations

## Not per-user lingering

`loginctl enable-linger` achieves a similar effect but introduces per-user state in `/var/lib/systemd/linger/` that must be granted, revoked, and kept in sync with whoever currently has access. It also never expires: a lingering user's processes survive indefinitely, which on a shared box accumulates. Retention as a global time window needs no per-user bookkeeping and reclaims resources on its own.

## Not `UserStopDelaySec=infinity`

`infinity` is a supported value and would keep every user's manager alive until shutdown. On a single-purpose host that would be reasonable, but on a shared multi-user system the cleanup is a feature — it is the only thing that ever reclaims an abandoned session's resources.

## `KillUserProcesses=no` is not sufficient on its own

It looks like the obvious knob and it is not enough. With it set, a logging-out user's processes are spared, but `$XDG_RUNTIME_DIR` is still removed on their final logout — `pam_systemd(8)` is explicit about this. Rootless podman keeps its network namespace, conmon sockets and pause process there, so the containers survive with their runtime state deleted underneath them. The retention window is what actually preserves a working environment.

## Why 72 hours

The window has to span a weekend for the "start something Friday, come back Monday" case, which rules out anything shorter than about two days. Beyond that the returns fade: a session untouched for longer than three days is one whose owner has moved on.
