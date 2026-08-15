---
status: implemented
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# Authelia — gate and identity provider

The [`authelia`](../../roles/authelia/README.md) role deploys Authelia as the zone's **gate and identity provider** for the [forward-auth pattern](../patterns/forward-auth.md): passkeys as the primary factor, password as the fallback, users from the collection's `users` dict, SQLite storage, one Go binary and no database server.

Authelia is always both things at once. Its `/api/authz/forward-auth` endpoint answers a reverse proxy directly, and its OpenID Connect provider is what [oauth2-proxy](oauth2-proxy.md) on other hosts signs in against. Which one a host's reverse proxy consults is a Caddy-fragment decision, not a mode of this role: a lone host imports the `(authelia)` snippet; once a second host wants the same login it runs oauth2-proxy pointed at `https://auth.<zone>`.

## What it deploys

**Install.** The pinned upstream release tarball (`authelia_version`, checksum vendored under `files/`), unpacked to `/opt/authelia/<version>/` and linked as `/usr/local/bin/authelia`. No third-party apt source.

**One vhost, `auth.<zone>`.** Portal, forward-auth endpoint and OIDC endpoints all publish on `/run/https/auth.<zone>/http.sock` (socket `0660`, directory `2750 authelia:https-socket-access`) per the [web-service socket pattern](../patterns/reverse-proxy.md). The role drops the vhost and a `(authelia)` snippet into `/etc/caddy/conf.d/`; the snippet renames Authelia's `Remote-User` / `Remote-Email` to the pattern's `X-Auth-Request-*` headers on the way through.

**Users from `users`.** Every entry with a `password` crypt hash becomes an Authelia user, with optional `email` (default `<name>@<zone>`), `displayname` and `groups`; `authelia_users` merges on top. Password hashes are static inventory for now.

**Access control.** `default_policy: deny`, then `authelia_access_rules`, then a catch-all `two_factor` for `<zone>` and `*.<zone>`. Anything weaker is a deliberate per-domain rule.

**Storage and secrets.** SQLite in `/var/lib/authelia/`; sessions in memory. JWT secret, session secret, storage encryption key, OIDC HMAC secret and the RSA issuer key are generated on the host on first run under `/etc/secrets/authelia/` (`0640 root:authelia`, the path the future secrets role will own) and reach Authelia through `AUTHELIA_*_FILE` variables and the config `secret` template function — never inline in `configuration.yml`.

**Notifier.** `filesystem` by default: enrolment links land in `/var/lib/authelia/notification.txt` for root to read. `smtp` through the host's postfix is a switch.

**OIDC provider.** Enabled when `authelia_oidc_clients` is non-empty. Each client carries `client_id`, a plaintext `client_secret` (hashed at render time by the role's `authelia_pbkdf2_digest` filter with a per-client deterministic salt, so the config is idempotent and holds only the digest) or a ready `client_secret_digest`, `redirect_uris`, and defaults of `two_factor`, `consent_mode: implicit`, `client_secret_basic`, scopes `openid profile email groups`.

**Configuration** is `configuration.yml` plus a `conf.d/` directory Authelia merges, where `authelia_extra_config` goes; both are validated with `authelia config validate` before the service is touched.

**Logout.** `https://auth.<zone>/logout` ends the Authelia session. Behind oauth2-proxy the link is `/oauth2/sign_out?rd=https://auth.<zone>/logout`, which clears both cookies in one click; Authelia publishes no `end_session_endpoint`, so the chain is the mechanism.

## Verified

Against the pinned binary: the socket comes up `0660` from the `?umask=0117` address; discovery at `/.well-known/openid-configuration` advertises `preferred_username`, `email`, `email_verified` and `groups`; the forward-auth endpoint answers an anonymous request with a 302 to the portal; oauth2-proxy's authorization request (PKCE S256) is accepted and lands on the portal's consent flow. In the container harness (`./test-in-containers-roles.yaml --tags auth`) the stack is deployed and asserted end to end.

## Growth

Adding hosts does not add Authelias. A second host runs oauth2-proxy against the first host's `auth.<zone>`; the login redirect crosses the network once, every later check is local. Authelia implements the OIDC provider role and explicitly not the relying-party role, so it cannot itself sign in against Google, Keycloak or another Authelia; the shared-LDAP and clustered-Authelia shapes exist but are not what this role builds toward.

## Open

- **Wildcard or per-vhost cookie for oauth2-proxy** — see [oauth2-proxy](oauth2-proxy.md); the role ships per-vhost as the default.
- **Password provisioning** beyond static hashes in inventory.
- **Binary versus container** — the binary shipped; a podman route is a possible alternative.
- **Secrets role.** The on-host generation is an interim at the secrets role's path; when that role lands the tasks in `secrets.yaml` collapse into calls to it.
