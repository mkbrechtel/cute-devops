---
status: draft
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# Authelia

## Goal

An `authelia` role deploying Authelia as a **local** gate fulfilling [forward-auth.pattern.md](forward-auth.pattern.md), so that a host with no identity provider can still publish [ttyd](ttyd.feature.md) and [code-server](code-server.feature.md).
Passkeys as the primary factor, password as the fallback, credential enrolment by emailed link — out of one Go binary with a file-backed user store and no database server.

Adopted rather than written: this is the shape we would have built, already built and maintained.
Forward-auth is its native mode, it does WebAuthn including passwordless passkeys, enrolment is email-verified, the user store can be a file, it is a single Apache-2.0 binary, and it is OpenID Certified.
An auth server is the worst place in a stack to own bespoke code.

## Scope

### Install

- Authelia is **not in Debian**, in bookworm or trixie. Upstream maintains a signed APT repository at `apt.authelia.com` and also attaches signed `.deb` artifacts to each release.
- Install from the upstream repository, pinned to its `stable` suite, keyring at `/usr/share/keyrings/authelia-security.gpg`, the source written in deb822 form to match `debian_apt_sources`.
- This is the collection's **first third-party apt source**. Whatever it settles on — keyring path, deb822 layout, how the suite is pinned — should read as a reusable convention rather than something Authelia-shaped, because the next such role will copy it.

### Shape on the host

- **One instance per host.** The gate is local, per the trust boundary in [forward-auth.pattern.md](forward-auth.pattern.md); hosts do not point at each other's.
- Authelia serves two things: the authz endpoint the reverse proxy calls, and the login portal the user is redirected to. The portal needs a vhost of its own — `auth.<host>` — publishing on `/run/https/auth.<host>/http.sock` per [reverse-proxy.pattern.md](reverse-proxy.pattern.md).
- **Caddy-fragment auto-deploy** (`authelia_configure_caddy`, default true), the same option the ttyd and code-server roles carry, plus the gated-vhost snippet those roles need in order to consult it.

### Users, storage, secrets

- **File user backend.** No LDAP, no external provider. The user list is rendered from the collection's existing `users` variable, so a host's accounts and its gate cannot drift apart.
- **Local SQLite storage** for what has to persist across restarts: registered WebAuthn credentials, TOTP secrets, user preferences. No postgres and no Redis — a single instance needs no shared session store, which is most of why one instance per host is a comfortable rule rather than a limiting one.
- Secrets — JWT signing key, session secret, storage encryption key, SMTP password if used — belong to the [secrets](secrets.feature.md) role. **That role does not exist yet.** It is reviewed but unbuilt, so this is a hard dependency and not a detail: until it lands there is no correct place for this role to read a key from.

### Enrolment and notification

- Registering an authenticator is email-verified: Authelia sends a link, the user opens it, and only then is the key touched and enrolled. The notifier is therefore on the critical path for onboarding, not a convenience.
- Two ways to satisfy it: SMTP through the host's postfix, or Authelia's filesystem notifier, which writes the link to a file for the administrator to read.
- For a single-user devbox the filesystem notifier removes the mail dependency entirely, which is worth more than the ergonomics it costs.

## Security

- **The fallback must not quietly become the front door.** A resource that accepts a passkey *or* a password is worth exactly its password, because an attacker will never attempt the passkey. Authelia's per-resource policy (`two_factor` against `one_factor`) is the right lever, so the role should default every gated resource to `two_factor` and make anything weaker a deliberate, per-resource opt-out.
- **The enrolment link is a credential.** Whoever holds it can enrol an authenticator. Short expiry, single use, and — with the filesystem notifier — a file readable only by root.
- **The trust boundary holds unmodified.** The gate is local, so the identity headers stay unspoofable for the structural reason [forward-auth.pattern.md](forward-auth.pattern.md) relies on rather than by configuration.
- **Bus factor, stated rather than discovered.** Authelia is community-maintained with no company behind it: Apache 2.0, OpenID Certified, and a small team with one very active lead. A reasonable bet for gating our own machines, and one to re-examine before it fronts anything expensive to migrate off.

## Design notes

### Why this replaces two roles rather than adding one

The [oauth2-proxy](oauth2-proxy.feature.md) scheme needs a provider behind it, which the collection does not have and would otherwise deploy separately — Keycloak or Authentik, each a heavier thing than the gate it feeds.
Authelia is gate and identity source in one binary, so the no-provider host needs one role instead of two.

It also does not close the door it appears to.
If several hosts later want a single login, the same binary can be the shared OIDC provider with per-host gates in front of it — exactly the shape [forward-auth.pattern.md](forward-auth.pattern.md) recommends for that case — so growing into the distributed shape means adding a provider, not replacing the gates.

## Open questions

- **Notifier default: filesystem or SMTP?** Filesystem drops the mail dependency for a one-user box; SMTP is what a host with real users wants. Recommendation: filesystem by default, SMTP opt-in.
- **Does the role wait for the secrets role**, or carry an interim way to place keys so it can ship before that one lands? Waiting is cleaner and blocks this on unrelated work.
- **`auth.<host>` per host, or one `auth.<zone>`?** Per-host follows the local-gate rule and is the recommendation; per-zone only starts making sense once there is a shared provider to name.
- **Two hosts, two enrolments.** A WebAuthn credential is bound to a relying-party ID, so per-host gates mean registering the same authenticator once per host — twice for orb and rod. Tolerable at two; the moment it stops being tolerable is the signal to move to a shared provider, and it would be good to say that out loud in the docs rather than let it be discovered at host five.
