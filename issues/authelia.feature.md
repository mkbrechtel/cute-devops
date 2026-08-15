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

An `authelia` role deploying Authelia as the collection's **identity provider and local gate** for [forward-auth.pattern.md](forward-auth.pattern.md).
Passkeys as the primary factor, password as the fallback, credential enrolment by emailed link — out of one Go binary with a file-backed user store and no database server.

Authelia is always both things at once: the forward-auth authz endpoint a reverse proxy can call directly, and an OpenID Connect provider that [oauth2-proxy](oauth2-proxy.feature.md) can sign in against. The role deploys both; which one a host's reverse proxy consults is a reverse-proxy decision, not a mode of this role. A lone host lets Caddy call Authelia directly. Once a second host wants the same login, each host runs oauth2-proxy as its local gate pointed at the one Authelia — the growth path in the design notes below, built in from the start rather than bolted on.

Adopted rather than written: forward-auth is its native mode, it does WebAuthn including passwordless passkeys, enrolment is email-verified, the user store can be a file, it is a single Apache-2.0 binary, and it is OpenID Certified.
An auth server is the worst place in a stack to own bespoke code.

## Scope

### Install

- Authelia is **not in Debian**, in bookworm or trixie. Upstream ships signed release binaries and a container image; it also runs an apt repository, which this role does not use — no third-party apt sources on a Debian host.
- Two install routes, either the upstream Go binary at `/usr/local/bin/authelia` under a systemd unit, or the upstream image under [podman](../roles/podman/README.md) with the config directory bind-mounted. Recommendation open, see below.
- **Version pinned** by the role. The OIDC provider's config keys have moved between minor releases; a float would break the client list.

### Shape on the host

- **One instance per host at most.** As a gate it is local, per the trust boundary in [forward-auth.pattern.md](forward-auth.pattern.md). As a provider it is one per zone; the other hosts in the zone run oauth2-proxy and no Authelia.
- Authelia serves the authz endpoint the reverse proxy calls, the login portal, and the OIDC endpoints. All three live on one vhost, **`auth.<zone>`**, publishing on `/run/https/auth.<zone>/http.sock` per [reverse-proxy.pattern.md](reverse-proxy.pattern.md). The issuer URL oauth2-proxy is given is `https://auth.<zone>`.
- **All hosts are assumed reachable over https.** oauth2-proxy on another host reaches the issuer's discovery, JWKS and token endpoints through the public vhost, so `auth.<zone>` — its Caddy and its certificate — is what every login in the zone depends on.
- **Caddy-fragment auto-deploy** (`authelia_configure_caddy`, default true): the portal vhost, plus the gated-vhost snippet a service role needs to consult Authelia directly. Behind oauth2-proxy the service role uses oauth2-proxy's snippet and this one is unused.
- **`/logout` on `auth.<zone>`.** One link that clears the Authelia session and, via redirects, the oauth2-proxy cookie of the vhost the user came from — so a service can offer a logout link without knowing which gate is in front of it.

### OIDC provider

- `authelia_oidc_clients` — one entry per oauth2-proxy instance: `client_id`, hashed `client_secret`, `redirect_uris` (`https://<gated vhost>/oauth2/callback`), scopes `openid profile email groups`, `authorization_policy` (`two_factor` default), `consent_mode: implicit` for first-party clients, `token_endpoint_auth_method: client_secret_basic`.
- The client secret is plaintext on the oauth2-proxy host and hashed on this one; both come from the [secrets](secrets.feature.md) role. Redirect URIs and client ids are declared explicitly in inventory on both sides — the deployer maintains the client list, the role does not derive it from `hostvars`.
- oauth2-proxy consumes only the core authorization-code flow — discovery, token endpoint, JWKS, the `email`, `preferred_username` and `groups` claims. Which claims Authelia actually emits under which scope, and whether `email_verified` is among them or oauth2-proxy needs `insecure_oidc_allow_unverified_email`, is settled by the experiment below rather than by reading docs.

### Users, storage, secrets

- **File user backend.** No LDAP, no external provider. The user list is rendered from the collection's existing `users` variable, so a host's accounts and its gate cannot drift apart. Password hashes are given statically in inventory for now; passkeys are enrolled after the first password login.
- **Local SQLite storage** for what has to persist across restarts: registered WebAuthn credentials, TOTP secrets, user preferences. No postgres and no Redis — a single instance keeps sessions in memory.
- Secrets — JWT signing key, session secret, storage encryption key, OIDC issuer private key, OIDC HMAC secret, client secret hashes, SMTP password if used — belong to the [secrets](secrets.feature.md) role. **That role is a hard dependency**: reviewed but unbuilt, and until it lands there is no correct place for this role to read a key from.

### Enrolment and notification

- Registering an authenticator is email-verified: Authelia sends a link, the user opens it, and only then is the key touched and enrolled. The notifier is therefore on the critical path for onboarding, not a convenience.
- Two ways to satisfy it: SMTP through the host's postfix, or Authelia's filesystem notifier, which writes the link to a file for the administrator to read.
- For a single-user devbox the filesystem notifier removes the mail dependency entirely, which is worth more than the ergonomics it costs.

## Security

- **The fallback must not quietly become the front door.** A resource that accepts a passkey *or* a password is worth exactly its password, because an attacker will never attempt the passkey. Authelia's per-resource policy (`two_factor` against `one_factor`) is the right lever, so the role should default every gated resource and every OIDC client to `two_factor` and make anything weaker a deliberate, per-resource opt-out.
- **The enrolment link is a credential.** Whoever holds it can enrol an authenticator. Short expiry, single use, and — with the filesystem notifier — a file readable only by root.
- **The trust boundary holds unmodified.** The gate on each host is local, so the identity headers stay unspoofable for the structural reason [forward-auth.pattern.md](forward-auth.pattern.md) relies on rather than by configuration. The cross-host exchange is the OIDC login redirect, over https, and nothing else.
- **Wildcard cookies are a trust decision, not a default.** oauth2-proxy's one-login-per-zone rests on a cookie bound to `.<zone>`, which the browser sends to *every* subdomain — including services in the zone that are not fully trusted. Bounding the cookie to the gated vhost costs a login per service and removes the exposure. Which one is right depends on whether every service under the zone is trusted with every other service's session; this needs more thought before the role picks a default, and is recorded as an open question rather than resolved here.
- **Bus factor, stated rather than discovered.** Authelia is community-maintained with no company behind it: Apache 2.0, OpenID Certified, and a small team with one very active lead. A reasonable bet for gating our own machines, and one to re-examine before it fronts anything expensive to migrate off.

## Experiments

- **Claims and logout against a real oauth2-proxy.** Stand up the pinned Authelia, one oauth2-proxy client, one gated vhost under a hand-written Caddyfile — before the Caddy role exists if need be. Record which claims arrive under which scope, whether `email_verified` is set, what `/oauth2/sign_out` leaves behind, and what a working `/logout` chain looks like. The result decides the claims section above and the logout design.

## Design notes

### Why one role and not two

The [oauth2-proxy](oauth2-proxy.feature.md) scheme needs a provider behind it, which the collection would otherwise deploy separately — Keycloak or Authentik, each a heavier thing than the gate it feeds.
Authelia is gate and provider in one binary, so the lone host needs one role, and the zone needs that role once plus oauth2-proxy per host.

### It cannot sign in against anything upstream

Authelia reads users from a file or from LDAP, and nothing else — one backend at a time.
It implements the OpenID Connect **provider** role, and explicitly not the **relying party** role, so it cannot itself authenticate against Google, Keycloak, or another Authelia.
Upstream states no intention to add it, so this is a deliberate position rather than a gap that may close.

The consequence for growth: adding hosts does not add Authelias.
A second host runs oauth2-proxy pointed at the first host's `auth.<zone>`; the login redirect crosses the network once, and every subsequent check is local, which is where [forward-auth.pattern.md](forward-auth.pattern.md) says the cost belongs.
The alternatives — a shared LDAP behind per-host Authelias, or a clustered Authelia over shared storage — share accounts or need a tightly integrated cluster respectively, and are not what this role builds toward.

## Open questions

- **Binary or container?** The Go binary is one file and one unit; the container gets upstream's image and its update cadence through podman. Both avoid a third-party apt source. Lean binary for the smaller surface, undecided.
- **Wildcard cookie or per-vhost cookie** for the oauth2-proxy scheme — see Security. Needs a trust model for the zone before a default is set.
- **Notifier default: filesystem or SMTP?** Filesystem drops the mail dependency for a one-user box; SMTP is what a host with real users wants. Recommendation: filesystem by default, SMTP opt-in.
- **Password provisioning.** Static hashes in inventory are the interim; a scheme that does not put hashes in inventory — generated on first deploy and emailed, or enrolment-only accounts — is worth thinking about later.
- **Where does `/logout` live and what does it chain?** Authelia's own logout endpoint plus a redirect back through the oauth2-proxy sign-out URL is the sketch; the experiment says whether it holds.
