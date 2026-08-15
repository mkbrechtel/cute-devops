<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# postfixadmin

Installs Debian's `postfixadmin` against a MySQL/MariaDB database and serves it at `https://<postfixadmin_server_name>/postfixadmin` through [caddy](../caddy/README.md) and [php_fpm](../php_fpm/README.md), both pulled in as dependencies. `postfixadmin-cli` is linked into `/usr/local/bin`.

## Role Variables

- `postfixadmin_mysql_host` / `_database` / `_username` / `_password`
- `postfixadmin_server_name` (default: `{{ inventory_hostname }}`) — the vhost
- `postfixadmin_web_root` (default: `/var/www/postfixadmin`) — holds the `postfixadmin` link to the package's `public/`
- `postfixadmin_php_fpm_socket` (default: `php_fpm_socket`)
- `postfixadmin_configure_caddy` (default: `true`) — write `/etc/caddy/conf.d/<server_name>`

## Dependencies

`caddy`, `php_fpm`.

## License

Apache-2.0 OR EUPL-1.2 (see file headers)
