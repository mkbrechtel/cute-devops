---
status: draft
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# Retire the apache role

## Goal

Remove `roles/apache` once the [Caddy](reverse-proxy-caddy.feature.md) role exists, so the collection ships one reverse proxy and it is the one every pattern is written against.

## Scope

- `roles/apache` is a bare install plus a default vhost, with no consumer in the collection. The only reference is postfix's `certbot --apache`, already scheduled to go in [certificate-role-rework](certificate-role-rework.feature.md).
- Apache cannot be the reverse proxy for [forward-auth.pattern.md](forward-auth.pattern.md): it has no `forward_auth`-style sub-request, and Authelia lists Caddy, nginx, Traefik, HAProxy and Envoy as supported proxies, not Apache. Every socket-publishing role in the pipeline — [ttyd](ttyd.feature.md), [code-server](code-server.feature.md), [authelia](authelia.feature.md), [oauth2-proxy](oauth2-proxy.feature.md) — assumes Caddy fragments.
- Order: land the Caddy role, move the postfix certbot flow off `--apache`, delete the role, note the removal in the changelog.
