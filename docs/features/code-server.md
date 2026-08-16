---
status: implemented
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# code-server — VS Code per user behind one vhost

The [`code_server`](../../roles/code_server/README.md) role publishes browser VS Code at **`code.<zone>`** and routes each authenticated user to their own code-server instance. Same shape as [ttyd](ttyd.md); authentication is the [forward-auth pattern](../patterns/forward-auth.md)'s job.

## What it deploys

**Install.** The pinned upstream release `.deb` (`code_server_version`, checksum vendored under `files/`), downloaded to `/opt/code-server/` and installed with apt — no third-party apt repository. The role's `code-server@.service` in `/etc/systemd/system/` overrides the package's TCP-listening one.

**Per-user backends.** `code-server@<user>.service` for every user in `code_server_users` (default: the keys of `users`), running as that user in their home, `--auth none`, telemetry and update check off, on `/run/code-server/<user>/http.sock` (`--socket-mode 0660`, directory `2750 <user>:https-socket-access`, `/run/code-server/` `0711`).

**A real login session.** `PAMName=code-server` against `/etc/pam.d/code-server`, so the integrated terminal has `XDG_RUNTIME_DIR` and a user manager; lingering enabled for the users.

**One vhost.** `/etc/caddy/conf.d/code.<zone>` imports the auth snippet (`code_server_caddy_auth_snippet`) and proxies on `X-Auth-Request-User` to `unix//run/code-server/<that user>/http.sock`, 403 otherwise. code-server's own auth is off by default; `code_server_auth: password` opts back in.

## Verified

In the container harness (`./test-in-containers-roles.yaml --tags auth`): `code-server@alice` is up on its socket and answers 200, and `code.<domain>` sends an anonymous request to sign in.

## Considerations

Installing the release `.deb` rather than adding coder's apt repository keeps the host's apt sources Debian-only; the price is a vendored checksum per version bump.
