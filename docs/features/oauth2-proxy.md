---
status: implemented
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# oauth2-proxy — the local gate in front of a provider

The [`oauth2_proxy`](../../roles/oauth2_proxy/README.md) role deploys oauth2-proxy in **forward-auth mode** with **cookie-only sessions**, gating vhosts on a host by signing users in against an OpenID Connect provider — by default the zone's [Authelia](authelia.md) at `https://auth.<zone>`. It is the [forward-auth pattern](../patterns/forward-auth.md)'s answer for several hosts that want one login: the cross-network exchange happens at login, every later check is a local sub-request.

## What it deploys

**Install.** The pinned upstream release tarball (`oauth2_proxy_version`, checksum vendored under `files/`), unpacked to `/opt/oauth2-proxy/<version>/`, linked as `/usr/local/bin/oauth2-proxy`.

**Instances.** `oauth2_proxy_instances` is a dict; each entry is a `oauth2-proxy@<name>.service` from one template unit, listening on `/run/oauth2-proxy/<name>.sock` (directory `2750 oauth2-proxy:https-socket-access`, socket `0660` from the unit's `UMask`). Its TOML config lives at `/etc/oauth2-proxy/<name>.toml` (`0640 root:oauth2-proxy`); the cookie secret is generated on the host on first run under `/etc/secrets/oauth2-proxy/`.

**Provider settings.** `provider = oidc`, issuer discovery at start, PKCE `S256`, scope `openid profile email groups`, `oidc_groups_claim = groups`, `skip_provider_button` so `/oauth2/sign_in` goes straight to the provider. Login can be restricted with `email_domains` and `allowed_groups`; the group check happens at login and only identity lands in the cookie.

**Sessions in the cookie.** `session_store_type = cookie`, secure, http-only, `SameSite=Lax`, seven-day expiry with hourly refresh. No Redis.

**The Caddy snippet.** Per instance the role writes `(oauth2-proxy-<name>)` into `/etc/caddy/conf.d/`. A gated vhost imports it: `/oauth2/*` (sign-in, callback, sign-out) is proxied to the instance socket, and every other request is checked with `forward_auth … /oauth2/auth` — 200 lets it through with `X-Auth-Request-User`, `X-Auth-Request-Email` and `X-Auth-Request-Preferred-Username` copied onto it, 401 is turned into a redirect to `/oauth2/sign_in?rd=<the request>`. Because the callback is served on the gated vhost itself, `redirect_url` is derived per request and the provider needs `https://<vhost>/oauth2/callback` registered for each gated vhost.

**Cookie scope.** The default cookie is bound to the gated vhost. `cookie_domains: [".<zone>"]` opts an instance into one login for every subdomain — and every subdomain into that session, which is why it is not the default; see below.

## Verified

In the container harness (`./test-in-containers-roles.yaml --tags auth`) an instance against the local Authelia comes up, discovers the issuer through Caddy, answers an anonymous request on the gated vhost with a redirect to `/oauth2/sign_in`, and its authorization request is accepted by Authelia. `/oauth2/sign_out?rd=https://auth.<zone>/logout` chains into Authelia's logout.

## Open

- **Wildcard cookie.** One login per zone means the session cookie is presented to every service under the zone, trusted or not. The default is per-vhost until there is a stated trust model for a zone; the wildcard remains one line of inventory.
- **`--trusted-proxy-ip`.** oauth2-proxy warns that all connecting IPs may supply `X-Forwarded-*`. The only client is Caddy over a group-restricted unix socket, which is the structural answer; a CIDR list would be cosmetic here.
- **Verdict caching** at the reverse proxy for asset-heavy vhosts is not configured; websocket applications pay the check once at upgrade anyway.
