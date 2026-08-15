---
status: implemented
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# Caddy — the default reverse proxy

The [`caddy`](../../roles/caddy/README.md) role installs Caddy as the host-wide reverse proxy of the [web-service socket pattern](../patterns/reverse-proxy.md): TLS and ACME at the edge, application sockets at `/run/https/<vhost>/http.sock` behind it. It is the default implementation of that pattern; every socket-publishing role in the collection writes Caddy fragments.

## What it deploys

**The Debian package.** `caddy` from trixie, under its stock unit, plus a drop-in that binds the admin API to `/run/caddy/admin.sock` (0700, no TCP), passes `caddy_environment` for provider credentials, and — when DNS modules are requested — swaps `ExecStart` to the upstream binary.

**Global block and drop-ins.** `/etc/caddy/Caddyfile` holds only the global block (admin socket, ACME email, JSON logging to journald, optional `local_certs`, `caddy_global_extra` verbatim) and `import /etc/caddy/conf.d/*`. Every vhost is a file `/etc/caddy/conf.d/<vhost>` — filename is the FQDN, no extension — written by the role that deploys the service or by inventory. Snippet definitions use a leading underscore (`_snippet.authelia`) so they sort before the vhosts that import them. The Caddyfile is validated with `caddy validate` before it lands and applied with `systemctl reload caddy`; connections survive.

**The socket access group.** The role creates `https-socket-access` and adds `caddy` to it. Service roles publish their socket directory as `2750 <service-user>:https-socket-access` — the setgid bit is what makes the socket itself inherit the group — so Caddy can connect and nothing else on the host can.

**Wildcard certificates, opt-in.** `caddy_dns_modules: ["github.com/caddy-dns/rfc2136"]` fetches upstream's CI build with that module from `caddyserver.com/api/download` to `/usr/local/bin/caddy`, checks the module is compiled in, and points the unit at it. `caddy_global_extra` carries the `acme_dns` block, credentials arrive through `caddy_environment`. The download API publishes no checksum, so the binary is fetched once and re-fetched only on `caddy_upstream_refresh: true`.

**Hosts that are not publicly reachable** — test containers, lab boxes — set `caddy_local_certs: true` and get certificates from Caddy's internal CA.

## What it does not do

It writes no vhosts of its own, does not aggregate inventory into `conf.d/`, and knows nothing about authentication: gating is the [forward-auth pattern](../patterns/forward-auth.md), implemented by [Authelia](authelia.md) and [oauth2-proxy](oauth2-proxy.md), each dropping its own snippet next to the vhosts.

## Test

`./test-in-containers-roles.yaml --tags auth` brings Caddy up on the `auth` instance with local certificates and serves the Authelia portal and two gated vhosts through it.
