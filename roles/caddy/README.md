<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# caddy

Installs [Caddy](https://caddyserver.com) as the host-wide reverse proxy for the [web-service socket pattern](../../docs/patterns/reverse-proxy.md): TLS termination and ACME at the edge, application sockets at `/run/https/<vhost>/http.sock` behind it.

The role ships the global block and `import /etc/caddy/conf.d/*`; every vhost is a drop-in file under `/etc/caddy/conf.d/<vhost>` (filename = FQDN, no extension) written by the role that deploys the service, or by inventory. Adding a service is a file write plus `systemctl reload caddy`.

## Requirements

- Debian 13/trixie (`caddy` from the Debian archive)

## Role Variables

- `caddy_acme_email` (default: `""`) — ACME account email
- `caddy_dns_modules` (default: `[]`) — DNS provider modules, e.g. `["github.com/caddy-dns/rfc2136"]`. Non-empty replaces the Debian binary with the upstream build from `caddyserver.com/api/download` at `/usr/local/bin/caddy` so DNS-01 / wildcard certificates work
- `caddy_upstream_refresh` (default: `false`) — re-download the upstream binary
- `caddy_global_extra` (default: `""`) — verbatim lines for the global block, e.g. an `acme_dns` block
- `caddy_environment` / `caddy_environment_files` — environment for the service (DNS credentials)
- `caddy_local_certs` (default: `false`) — Caddy's internal CA instead of ACME, for hosts that are not publicly reachable
- `caddy_log_format` (default: `json`) — access log format, into journald
- `caddy_conf_dir` (default: `/etc/caddy/conf.d`)
- `caddy_socket_group` (default: `https-socket-access`) — created by the role; `caddy` is added to it
- `caddy_remove_apache` (default: `true`) — purge `apache2`, which the collection's retired apache role left on :80/:443

The admin API is bound to `/run/caddy/admin.sock` (0700, `caddy`), never to TCP.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: web
  become: true
  roles:
    - role: osahris.cute_devops.caddy
      vars:
        caddy_acme_email: admin@example.com
```

A vhost fragment for a service publishing on a socket:

```caddy
# /etc/caddy/conf.d/element.example.com
element.example.com {
    reverse_proxy unix//run/https/element.example.com/http.sock
}
```

Wildcard certificates over the collection's own nameserver:

```yaml
caddy_dns_modules: ["github.com/caddy-dns/rfc2136"]
caddy_environment:
  CADDY_ACME_TSIG_KEY: "{{ vault_tsig_key }}"
caddy_global_extra: |
  acme_dns rfc2136 {
      key_name acme-update
      key_alg hmac-sha256
      key {env.CADDY_ACME_TSIG_KEY}
      server 192.0.2.53:53
  }
```

## License

EUPL-1.2
