<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# authelia

Deploys [Authelia](https://www.authelia.com) as the zone's gate and identity provider for the [forward-auth pattern](../../docs/patterns/forward-auth.md): passkeys as the primary factor, password as the fallback, users from the collection's `users` dict, SQLite storage, no database server.

One instance serves the login portal at `auth.<zone>`, the forward-auth endpoint a reverse proxy calls directly, and an OpenID Connect provider that [oauth2-proxy](../oauth2_proxy/README.md) on other hosts signs in against. It publishes on `/run/https/auth.<zone>/http.sock` per the [web-service socket pattern](../../docs/patterns/reverse-proxy.md) and drops its vhost and a `(authelia)` snippet into `/etc/caddy/conf.d/`.

Installed from the pinned upstream release tarball (checksum vendored in `files/`), under `/opt/authelia/<version>/` with `/usr/local/bin/authelia` linked to it.

## Requirements

- Debian 13/trixie
- The [caddy](../caddy/README.md) role on the same host (or `authelia_configure_caddy: false` and your own vhost)
- `domain` set (the zone)

## Role Variables

- `authelia_version` (default: `v4.39.20`)
- `authelia_zone` (default: `{{ domain }}`) — cookie domain, issuer `https://auth.<zone>`, access-control catch-all
- `authelia_users_from_users` (default: `true`) — render `users` entries that carry a `password` hash; optional `email` (default `<name>@<zone>`), `displayname`, `groups`
- `authelia_users` (default: `{}`) — Authelia user entries merged on top
- `authelia_default_policy` (default: `two_factor`) — for `<zone>` and `*.<zone>`; `authelia_access_rules` are matched first
- `authelia_notifier` (default: `filesystem`) — `filesystem` writes enrolment links to `authelia_notification_file`; `smtp` uses `authelia_smtp_*`
- `authelia_oidc_clients` (default: `[]`) — relying parties; each `client_id`, `client_secret` (plaintext, hashed at render time to a sha512-crypt digest Authelia validates against — or `client_secret_digest`), `redirect_uris`, optional `scopes`, `authorization_policy`, `consent_mode`. The provider is enabled when non-empty
- `authelia_session_*`, `authelia_webauthn_*`, `authelia_oidc_*_lifespan` — see `defaults/main.yaml`
- `authelia_extra_config` (default: `{}`) — merged by Authelia from `conf.d/50-extra.yml`
- `authelia_listen` (default: the unix socket) — `tcp://127.0.0.1:9091` when the reverse proxy cannot reach host sockets
- `authelia_configure_caddy` (default: `true`), `authelia_caddy_conf_dir` / `_group` / `_mode` / `_reload_command` — where fragments go and how Caddy is reloaded; defaults match the `caddy` role

Secrets (JWT, session, storage encryption, OIDC HMAC, issuer key) are generated on the host on first run under `/etc/secrets/authelia/`, `0640 root:authelia`, and reach Authelia as `AUTHELIA_*_FILE` variables. Enrolment links with the filesystem notifier land in `/var/lib/authelia/notification.txt`.

## Gating a vhost directly

```caddy
terminal.example.com {
    import authelia
    reverse_proxy unix//run/https/terminal.example.com/http.sock
}
```

## Logout

`https://auth.<zone>/logout` ends the Authelia session. Behind oauth2-proxy link to `https://<vhost>/oauth2/sign_out?rd=https://auth.<zone>/logout` so both cookies go.

## Example Playbook

```yaml
- hosts: auth
  become: true
  roles:
    - role: osahris.cute_devops.caddy
    - role: osahris.cute_devops.authelia
      vars:
        authelia_oidc_clients:
          - client_id: oauth2-proxy
            client_secret: "{{ vault_oauth2_proxy_client_secret }}"
            redirect_uris:
              - https://terminal.example.com/oauth2/callback
```

## License

EUPL-1.2
