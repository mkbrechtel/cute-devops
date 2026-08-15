---
status: implemented
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# Mail web UIs on Caddy — the Apache role is gone

The mail stack's web interfaces are served through the collection's [Caddy](caddy.md) reverse proxy, and `roles/apache` no longer exists. One web server for the collection.

## What changed

**`postfix`** depends on `caddy` instead of `apache`. `postfix_with_ssl` obtains its certificate with `certbot certonly --webroot -w /var/www/acme`; the role drops an `http://<mailserver_domain_name>` fragment into `/etc/caddy/conf.d/` that serves that webroot, so Caddy answers the HTTP-01 challenge on port 80.

**`postfixadmin`** depends on `caddy` and the new [`php_fpm`](../../roles/php_fpm/README.md) role. It publishes `https://<postfixadmin_server_name>/postfixadmin` from a Caddy fragment: web root `/var/www/postfixadmin` with `postfixadmin` linked to the package's `public/` (the shape the old `Alias` had), `php_fastcgi` to `/run/php/php-fpm.sock`, `/` redirected to `/postfixadmin/`. TLS is Caddy's; the `postfixadmin_certificate_*` variables are gone.

**`sympa`** depends on `caddy` instead of `apache` and installs with recommends off (they pulled in `mod_fcgid` and `apache2-suexec`; `libio-socket-ssl-perl` and `logrotate` are listed explicitly). One Caddy fragment per list domain: `/wws` and `/wws/*` go to `wwsympa`'s FastCGI socket `/run/sympa/wwsympa.socket` with `split /wws` so `SCRIPT_NAME` is `/wws` and the rest is `PATH_INFO`; `/static-sympa`, `/css-sympa`, `/pictures-sympa` are `file_server` roots; `/` redirects to `/wws`. The per-domain `certificate` include is gone — Caddy issues them.

**`php_fpm`** — Debian's `php-fpm`, started, socket `/run/php/php-fpm.sock` (the versionless alternative). Caddy is in `www-data`, which is what both that socket and `wwsympa.socket` are owned by.

**Test**: `./test-in-containers-single.yaml` asserts `caddy` and `wwsympa.socket` are active and 443 is listening next to the mail ports; the mail environments set `caddy_local_certs: true`.

## Not moved

- **rainloop** — the Debian package is not in trixie, and the role never wrote a vhost. The role stays as it is; serving a webmail through Caddy is a new ticket once there is a packaged webmail to serve.
- **`sympasoap`** is not published; only the web UI is.

## Considerations

Postfixadmin's `Depends: apache2 | lighttpd | nginx | httpd` is satisfied by Caddy, which `Provides: httpd`, because the role dependency installs Caddy before apt sees postfixadmin.
