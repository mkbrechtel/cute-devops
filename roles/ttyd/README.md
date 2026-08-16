<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# ttyd

Publishes a browser terminal per user behind one vhost. [ttyd](https://github.com/tsl0922/ttyd) is installed from the pinned GitHub release (checksum vendored in `files/`); each user in `ttyd_users` gets a `ttyd@<user>.service` running as that user, in their home, on `/run/ttyd/<user>/http.sock`. The vhost `terminal.<zone>` imports the [forward-auth](../../docs/patterns/forward-auth.md) snippet and proxies to the socket named by `X-Auth-Request-User` — one vhost, N users, no ttyd auth of its own.

Each instance is a real logind session (`PAMName=ttyd`, `/etc/pam.d/ttyd`), so `XDG_RUNTIME_DIR`, the user manager and rootless podman work as after an ssh login; lingering is enabled for the users so their services survive the terminal.

## Requirements

- Debian 13/trixie
- The users exist (the [users](../users/README.md) role); a gate in front ([oauth2_proxy](../oauth2_proxy/README.md) or [authelia](../authelia/README.md)) and [caddy](../caddy/README.md), or `ttyd_configure_caddy: false`

## Role Variables

- `ttyd_version` (default: `1.7.7`), `ttyd_install_dir` (default: `/opt/ttyd`), `ttyd_with_usr_local_bin_symlink` (default: `false`)
- `ttyd_users` (default: the keys of `users`)
- `ttyd_shell` (default: `/bin/bash`), `ttyd_cwd` (default: `~`)
- `ttyd_enable_linger` (default: `true`)
- `ttyd_zone` (default: `{{ domain }}`), `ttyd_vhost` (default: `terminal.<zone>`)
- `ttyd_caddy_auth_snippet` (default: `oauth2-proxy-default`; `authelia` for the direct gate)
- `ttyd_configure_caddy` (default: `true`), `ttyd_caddy_conf_dir` / `_group` / `_mode` / `_reload_command`

## Example Playbook

```yaml
- hosts: devbox
  become: true
  roles:
    - role: osahris.cute_devops.users
    - role: osahris.cute_devops.caddy
    - role: osahris.cute_devops.oauth2_proxy
    - role: osahris.cute_devops.ttyd
      vars:
        ttyd_shell: /usr/bin/fish
```

## License

EUPL-1.2
