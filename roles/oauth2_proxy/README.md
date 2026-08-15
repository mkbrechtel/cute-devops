<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# oauth2_proxy

Deploys [oauth2-proxy](https://oauth2-proxy.github.io/oauth2-proxy/) as a local forward-auth gate for the [forward-auth pattern](../../docs/patterns/forward-auth.md), signing users in against an OpenID Connect provider — by default the zone's [Authelia](../authelia/README.md) at `https://auth.<zone>`. Sessions live in the cookie; no Redis.

Each entry in `oauth2_proxy_instances` is a `oauth2-proxy@<name>.service` listening on `/run/oauth2-proxy/<name>.sock` and a Caddy snippet `(oauth2-proxy-<name>)` in `/etc/caddy/conf.d/`. A gated vhost imports the snippet: `/oauth2/*` (sign-in, callback, sign-out) is served by oauth2-proxy, everything else is checked with `forward_auth` and, on allow, reaches the app with `X-Auth-Request-User`, `X-Auth-Request-Email` and `X-Auth-Request-Preferred-Username`.

Installed from the pinned upstream release tarball (checksum vendored in `files/`), under `/opt/oauth2-proxy/<version>/`, linked as `/usr/local/bin/oauth2-proxy`.

## Requirements

- Debian 13/trixie
- The [caddy](../caddy/README.md) role on the same host (or `oauth2_proxy_configure_caddy: false`)
- An OIDC client registered at the provider with `https://<each gated vhost>/oauth2/callback` as redirect URI

## Role Variables

- `oauth2_proxy_version` (default: `v7.15.3`)
- `oauth2_proxy_zone` (default: `{{ domain }}`), `oauth2_proxy_issuer_url` (default: `https://auth.<zone>`)
- `oauth2_proxy_instances` (default: `{}`) — per instance: `client_id`, `client_secret`, optional `issuer_url`, `cookie_domains` (default `[]` — the cookie is bound to the gated vhost; `[".<zone>"]` gives one login for every subdomain, and every subdomain the session), `email_domains` (`["*"]`), `allowed_groups`, `cookie_expire` (`168h`), `cookie_refresh` (`1h`), `whitelist_domains` (`[".<zone>"]`), `extra` (verbatim options)
- `oauth2_proxy_allow_unverified_email` (default: `false`)
- `oauth2_proxy_configure_caddy` (default: `true`)

The cookie secret is generated on the host on first run under `/etc/secrets/oauth2-proxy/`.

## Gating a vhost

```caddy
terminal.example.com {
    import oauth2-proxy-default
    reverse_proxy unix//run/https/terminal.example.com/http.sock
}
```

Logout link for the app: `/oauth2/sign_out?rd=https://auth.example.com/logout` — clears the oauth2-proxy cookie, then the Authelia session.

## Example Playbook

```yaml
- hosts: devbox
  become: true
  roles:
    - role: osahris.cute_devops.caddy
    - role: osahris.cute_devops.oauth2_proxy
      vars:
        oauth2_proxy_instances:
          default:
            client_id: oauth2-proxy
            client_secret: "{{ vault_oauth2_proxy_client_secret }}"
```

## License

EUPL-1.2
