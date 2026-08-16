---
status: implemented
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# ttyd — a terminal per user behind one vhost

The [`ttyd`](../../roles/ttyd/README.md) role publishes a browser terminal at **`terminal.<zone>`** and routes each authenticated user to their own ttyd instance. Same shape as [code-server](code-server.md), so the two compose on a devbox; authentication is the [forward-auth pattern](../patterns/forward-auth.md)'s job, not the role's.

## What it deploys

**Install.** The pinned GitHub release binary (`ttyd_version`, checksum vendored under `files/`) at `/opt/ttyd/`.

**Per-user backends.** `ttyd@<user>.service` for every user in `ttyd_users` (default: the keys of `users`), running as that user in their home with `ttyd_shell`, writable, on `/run/ttyd/<user>/http.sock`. The per-user directory is `2750 <user>:https-socket-access` (setgid, so the socket inherits the group); `/run/ttyd/` itself is `0711 root:root` — the proxy can reach a socket it knows the name of and cannot enumerate the rest.

**A real login session.** The unit sets `PAMName=ttyd` against a role-shipped `/etc/pam.d/ttyd` (`pam_limits`, `pam_systemd`), so each instance is a logind session with `XDG_RUNTIME_DIR` and a user manager — rootless podman and `systemctl --user` work as after ssh. Lingering is enabled for the users so their services outlive the terminal.

**One vhost.** `/etc/caddy/conf.d/terminal.<zone>` imports the auth snippet (`ttyd_caddy_auth_snippet`, default `oauth2-proxy-default`, or `authelia`), matches `X-Auth-Request-User` against `^[a-z_][a-z0-9_-]{0,31}$` and proxies to `unix//run/ttyd/<that user>/http.sock`; anything else is 403. ttyd's own auth stays off — the gate authenticates, the route binds identity to backend.

## Verified

In the container harness (`./test-in-containers-roles.yaml --tags auth`): `ttyd@alice` is up on its socket, answers on it, and `terminal.<domain>` sends an anonymous request to sign in.

## Considerations

A `UMask=` on the unit to shape the socket mode is wrong here: it also shapes every file the user's shell creates. The directory permissions are what protect the socket.
