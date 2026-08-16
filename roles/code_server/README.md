<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# code_server

Publishes a VS Code in the browser per user behind one vhost. [code-server](https://github.com/coder/code-server) is installed from the pinned upstream release `.deb` (checksum vendored in `files/`); each user in `code_server_users` gets a `code-server@<user>.service` running as that user, in their home, on `/run/code-server/<user>/http.sock`. The vhost `code.<zone>` imports the [forward-auth](../../docs/patterns/forward-auth.md) snippet and proxies to the socket named by `X-Auth-Request-User` — one vhost, N users, code-server's own auth off.

Each instance is a real logind session (`PAMName=code-server`, `/etc/pam.d/code-server`), so `XDG_RUNTIME_DIR`, the user manager and rootless podman work as after an ssh login; lingering is enabled for the users so their services survive the editor.

## Requirements

- Debian 13/trixie
- The users exist (the [users](../users/README.md) role); a gate in front ([oauth2_proxy](../oauth2_proxy/README.md) or [authelia](../authelia/README.md)) and [caddy](../caddy/README.md), or `code_server_configure_caddy: false`

## Role Variables

- `code_server_version` (default: `v4.132.0`)
- `code_server_users` (default: the keys of `users`)
- `code_server_auth` (default: `none`), `code_server_extra_args`
- `code_server_enable_linger` (default: `true`)
- `code_server_zone` (default: `{{ domain }}`), `code_server_vhost` (default: `code.<zone>`)
- `code_server_caddy_auth_snippet` (default: `oauth2-proxy-default`; `authelia` for the direct gate)
- `code_server_configure_caddy` (default: `true`), `code_server_caddy_conf_dir` / `_group` / `_mode` / `_reload_command`

## Example Playbook

```yaml
- hosts: devbox
  become: true
  roles:
    - role: osahris.cute_devops.users
    - role: osahris.cute_devops.caddy
    - role: osahris.cute_devops.oauth2_proxy
    - role: osahris.cute_devops.code_server
```

## License

EUPL-1.2
