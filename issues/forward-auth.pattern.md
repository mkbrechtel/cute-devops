---
status: draft
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# Forward auth

> **Pattern.** Cross-cutting convention. The deliverable is a consolidated definition that lives in `patterns/` once the ticket is closed; the [oauth2-proxy](oauth2-proxy.feature.md) role, the [reverse-proxy](reverse-proxy.pattern.md) backends, and any service-role that wants a gate in front reference this document.

## Goal

One convention for putting authentication in front of a web service, written so that **the service role never learns which scheme authenticated the user**.
The pattern fixes the contract — a verdict, plus identity headers on the way in — and leaves the scheme pluggable: OIDC through [oauth2-proxy](oauth2-proxy.feature.md) on a host that has an identity provider, something cheaper on a host that does not.
A deployer can start on the cheap scheme and swap in OIDC later without touching anything behind the gate.

## Model

The reverse proxy stays on the data path.
Before proxying a gated request it asks a gate for a verdict, and on approval proxies to the app socket with the gate's identity headers attached.

```
                          ┌──auth-check──> gate
                          │
client → network → reverse proxy ────────> app socket  (with X-Auth-Request-* headers)
```

Per backend the sub-request is `forward_auth` (Caddy), `auth_request` (nginx), or the `forwardAuth` middleware (Traefik).
Where a scheme needs no separate gate process — basic auth, client certificates — the reverse proxy *is* the gate and produces the same headers itself. Everything to the right of the rpx is unchanged either way, which is the point.

## The contract

This is the whole of what a service role may assume.

- **Verdict.** 200 means allow. Any other status is the gate's answer to the client — a 401, or a redirect into a login flow — and the rpx surfaces it rather than proxying.
- **Identity headers.** On allow, the request reaching the app carries `X-Auth-Request-User`, `X-Auth-Request-Email` and `X-Auth-Request-Preferred-Username`. `X-Auth-Request-User` is the stable local identifier, and the one the per-user routers in [ttyd](ttyd.feature.md) and [code-server](code-server.feature.md) key on.
- **Identity only.** Group and role lists never flow through as headers. A scheme may *gate* on them, but what reaches the app is who the user is, not what they may do.
- **Trust.** App sockets are unbound from the network ([reverse-proxy.pattern.md](reverse-proxy.pattern.md)), so the rpx chain is the only producer of `X-Auth-Request-*`. Spoofing is structurally impossible rather than filtered against, and apps may trust the headers as they arrive.
- **Endpoint.** The rpx addresses the gate by URL, so a gate that is its own process may be local or on another machine. A local one publishes on a unix socket like any other service in the collection, which is the default; see the cost note below before pointing one across the network.

A service role that speaks this contract works under every scheme below, and gains nothing from knowing which one is deployed.

## Schemes

Default where an identity provider exists: **[oauth2-proxy](oauth2-proxy.feature.md)** — OIDC, cookie sessions, single sign-on across the zone.

Alternates, for a host with no IdP:

- **Basic auth at the rpx.** The rpx checks an htpasswd file and injects the matched username as `X-Auth-Request-User`. No gate process, no provider, no session; the browser re-sends credentials on every request. One shared secret per user, so revocation means editing a file.
- **Client certificates (mTLS).** The rpx requires a client certificate and maps its CN or SAN onto the identity headers. No passwords and no provider, at the cost of issuing and distributing certificates.

Not a scheme, but the honest alternative worth naming: **do not publish it.**
A service reachable only over wireguard, or over an ssh tunnel to a loopback socket, has no public surface to gate.
For a single-user devbox that is frequently the right answer and costs nothing to run.

## Design notes

### Why the contract is the pattern

The valuable, stable thing here is not any one gate — it is that [ttyd](ttyd.feature.md) and [code-server](code-server.feature.md) route per user off a header without caring where the header came from.
Fixing the contract first means the cheap scheme and the full SSO scheme are the same shape to everything downstream, and swapping them is a reverse-proxy edit rather than a service-role change.
It also keeps the collection honest about the gap between "authenticated" and "authorized": the gate answers the first, the app is still responsible for the second.

### Where the gate runs, and what it costs

The sub-request carries the original request's headers and no body, so the bandwidth is trivial.
What it costs is one round trip plus the gate's own session check, on every gated request.

Over a unix socket on the same host that is a sub-millisecond hop, and not worth thinking about.
Pointed at another machine it becomes a real network round trip per request — a few milliseconds inside a datacentre, tens of them across the internet — paid again on every asset a page pulls.
That is the version worth being careful about, and the reason a local gate is the default here.
What buys the remote one its keep is a single login covering several hosts, which per-host gates cannot give without a shared session store; it is a fair trade, but it should be made knowingly rather than by following the pattern blindly.

Two things soften the cost where this collection actually spends it.
[ttyd](ttyd.feature.md) and [code-server](code-server.feature.md) are websocket applications: the gate is consulted once at the upgrade, and the long-lived connection that follows carries the session without further checks, so the per-request cost lands on the initial page load rather than on use.
An rpx that can cache the auth response against the session cookie for a short TTL (nginx's `proxy_cache` over `auth_request`) collapses the repeat cost for the assets too.

The websocket exemption has a security edge worth stating: a session revoked at the gate does not reach a connection that is already open, so revocation takes effect when the socket drops rather than immediately.
For a terminal or an editor that is usually acceptable; a service where it is not should not be gated this way.

### Why not in-line chaining

An earlier draft of this pattern also described putting the gate *in* the data path, between the rpx and the app socket, as an alternative shape.
That is dropped. [oauth2-proxy.feature.md](oauth2-proxy.feature.md) already scopes itself to forward-auth only, so the second shape had no implementation; and it cannot express the per-path and per-user rpx logic that the two service roles above actually need.
One shape, spelled out once, is worth more than two shapes with one of them unused.

### Authz levers a service role gets

- **At the gate:** allow or deny the login itself — by email, email domain, certificate, htpasswd entry, or OIDC claim, depending on the scheme.
- **At the rpx:** allow or deny by path, IP, or time of day, and route per user off the identity header. Per-path public/private splits live here.
- **At the app:** anything needing the user's full group list or RBAC-shaped state. The app reads identity from the headers and consults its own authz, which is the right place for it.

## Open questions

- **Is "forward auth" the right name?** It describes the mechanism, but two of the three schemes have no separate gate to forward to — the rpx answers its own sub-question. A contract-shaped name (`auth-gate`, `authenticated-identity`) would cover all three honestly. Recommendation: keep `forward-auth`, since it matches the Caddy directive and the rpx-native schemes are legitimately the degenerate case of the same shape.
- **Which alternate scheme gets a feature ticket first?** Basic auth is the smallest thing that unblocks a devbox with no IdP; mTLS is stronger and barely harder for a single user. Only one needs writing now.
- **Do the alternates keep the `X-Auth-Request-*` spelling?** It is oauth2-proxy's, not a standard. Recommendation: yes — it is what the service roles already read, and inventing a neutral spelling would mean a translation shim in the default scheme for no gain.
- **Does the basic-auth scheme need a session at all?** Browsers cache basic credentials for the realm, so probably not; worth confirming against a websocket-heavy client like code-server before it is written up.
