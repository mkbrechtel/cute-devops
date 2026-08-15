<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# php_fpm

Installs Debian's `php-fpm` and starts it. PHP apps served through the [caddy](../caddy/README.md) role point `php_fastcgi` at `php_fpm_socket` (default `/run/php/php-fpm.sock`, `www-data`, which Caddy is a member of).

## Role Variables

- `php_fpm_socket` (default: `/run/php/php-fpm.sock`)

## Dependencies

None. Consumers: [postfixadmin](../postfixadmin/README.md).

## License

EUPL-1.2
