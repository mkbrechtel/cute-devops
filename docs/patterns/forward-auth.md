---
status: implemented
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# Forward auth

> **Pattern.** Implemented by the [Authelia](../features/authelia.md) and [oauth2-proxy](../features/oauth2-proxy.md) roles on top of [Caddy](../features/caddy.md); any service role that wants a gate in front follows this document.

## Goal

One convention for putting authentication in front of a web service, written so that **the service role never learns which scheme authenticated the user**.
The pattern fixes the contract — a verdict, plus identity headers on the way in — and leaves the scheme pluggable: OIDC through [oauth2-proxy](../features/oauth2-proxy.md) on a host that has an identity provider, something cheaper on a host that does not.
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
- **Identity headers.** On allow, the request reaching the app carries `X-Auth-Request-User`, `X-Auth-Request-Email` and `X-Auth-Request-Preferred-Username`. `X-Auth-Request-User` is the stable local identifier, and the one the per-user routers in [ttyd](../features/ttyd.md) and [code-server](../features/code-server.md) key on. The spelling is oauth2-proxy's; a gate that answers in another one — Authelia emits `Remote-User`, `Remote-Email`, `Remote-Name` — is renamed to it in the rpx snippet (Caddy: `copy_headers Remote-User>X-Auth-Request-User`), so the contract holds at the app regardless of the gate.
- **Identity only.** Group and role lists never flow through as headers. A scheme may *gate* on them, but what reaches the app is who the user is, not what they may do.
- **Trust.** App sockets are unbound from the network ([reverse-proxy.pattern.md](reverse-proxy.md)), so within the trust boundary below the rpx chain is the only producer of `X-Auth-Request-*`. Spoofing is structurally impossible rather than filtered against, and apps may trust the headers as they arrive. This bullet is the one that fails first if the boundary is stretched, which is why the boundary is part of the contract and not advice.
- **Endpoint.** The rpx addresses the gate by URL, so a gate that is its own process may be local or on a neighbouring machine — but only within one trust boundary, as below. A local one publishes on a unix socket like any other service in the collection, which is the default.

A service role that speaks this contract works under every scheme below, and gains nothing from knowing which one is deployed.

## Schemes

The two defaults answer the two different questions from the design note above.

- **[Authelia](../features/authelia.md)** — a local gate carrying its own user store, passkeys with a password fallback. The default for a host that stands alone: the vhost imports the `(authelia)` Caddy snippet and the rpx calls Authelia's authz endpoint directly.
- **[oauth2-proxy](../features/oauth2-proxy.md)** — a local gate in front of an OIDC provider. The default once several hosts want the same login; the vhost imports the `(oauth2-proxy-<instance>)` snippet, and the provider is the zone's one Authelia, which is a provider as well as a gate.

Cheaper alternates, where a gate process is more than the service warrants:

- **Basic auth at the rpx.** The rpx checks an htpasswd file and injects the matched username as `X-Auth-Request-User`. No gate process, no provider, no session; the browser re-sends credentials on every request. One shared secret per user, so revocation means editing a file.
- **Client certificates (mTLS).** The rpx requires a client certificate and maps its CN or SAN onto the identity headers. No passwords and no provider, at the cost of issuing and distributing certificates.

Not a scheme, but the honest alternative worth naming: **do not publish it.**
A service reachable only over wireguard, or over an ssh tunnel to a loopback socket, has no public surface to gate.
For a single-user devbox that is frequently the right answer and costs nothing to run.

## Design notes

### Why the contract is the pattern

The valuable, stable thing here is not any one gate — it is that [ttyd](../features/ttyd.md) and [code-server](../features/code-server.md) route per user off a header without caring where the header came from.
Fixing the contract first means the cheap scheme and the full SSO scheme are the same shape to everything downstream, and swapping them is a reverse-proxy edit rather than a service-role change.
It also keeps the collection honest about the gap between "authenticated" and "authorized": the gate answers the first, the app is still responsible for the second.

### Where the gate may run

**The gate and the reverse proxy have to share a trust boundary** — the same host, or the same tightly integrated cluster: one administrative domain, a private network, latency of the same order as a local call.
Inside that, whether the endpoint is a unix socket or a URL on a neighbouring machine is an implementation detail.
Across the open internet it is not a detail, and the pattern does not stretch that far.

Three reasons, in descending order of how much they should worry a deployer:

- **The trust assumption breaks.** The contract lets an app believe `X-Auth-Request-*` because the rpx chain is the only thing that can produce those headers, which holds precisely while the chain is local and the sockets are off the network. Move the gate across an untrusted one and a forged 200 with forged identity headers is a forged login. The sub-request then needs mutual TLS and a trust store of its own — the problem has not been removed, it has been moved and given a certificate lifecycle.
- **Every gated service inherits a remote single point of failure.** A gate that is unreachable takes down every gated vhost on every host pointed at it. On one host that is one failure domain; across a WAN it couples machines that were otherwise independent.
- **Every request pays the round trip.** The sub-request carries the original headers and no body, so bandwidth is trivial; the cost is one round trip plus the gate's session check, per gated request. Sub-millisecond over a local socket, a few milliseconds inside a datacentre, tens of them across the internet — and paid again on every asset a page pulls.

Two things soften that last one where this collection actually spends it.
[ttyd](../features/ttyd.md) and [code-server](../features/code-server.md) are websocket applications: the gate is consulted once at the upgrade, and the long-lived connection that follows carries the session without further checks, so the per-request cost lands on the initial page load rather than on use.
An rpx that can cache the verdict against the session cookie for a short TTL (nginx's `proxy_cache` over `auth_request`) collapses the repeat cost for the assets too.

The websocket exemption has a security edge worth stating: a session revoked at the gate does not reach a connection that is already open, so revocation takes effect when the socket drops rather than at once.
For a terminal or an editor that is usually acceptable; a service where it is not should not be gated this way.

### Reaching across hosts anyway

What tempts a deployer toward a remote gate is one login covering several machines.
Forward auth is the wrong instrument for it: it puts a cross-network hop on *every request* in order to buy a login that happens *once*.

The shape that gets the same result is a **local gate on each host, pointed at a shared identity provider** — the [oauth2-proxy](../features/oauth2-proxy.md) scheme.
The cross-network exchange happens during the login redirect and then stops; afterwards every check is local, against a cookie the local gate validates by itself.
The remote dependency is reduced to login time, where an outage means "cannot sign in" rather than "everything is down", and where one round trip is invisible.

So the two schemes are not competing implementations of the same thing.
A local gate with its own user store is the answer for a host that stands alone; a local gate in front of a shared provider is the answer for several hosts that want one login.
Neither of them is a gate on the far side of the internet.

### Why not in-line chaining

An earlier draft of this pattern also described putting the gate *in* the data path, between the rpx and the app socket, as an alternative shape.
That is dropped. [oauth2-proxy.feature.md](../features/oauth2-proxy.md) already scopes itself to forward-auth only, so the second shape had no implementation; and it cannot express the per-path and per-user rpx logic that the two service roles above actually need.
One shape, spelled out once, is worth more than two shapes with one of them unused.

### Authz levers a service role gets

- **At the gate:** allow or deny the login itself — by email, email domain, certificate, htpasswd entry, or OIDC claim, depending on the scheme.
- **At the rpx:** allow or deny by path, IP, or time of day, and route per user off the identity header. Per-path public/private splits live here.
- **At the app:** anything needing the user's full group list or RBAC-shaped state. The app reads identity from the headers and consults its own authz, which is the right place for it.

## Open questions

- **Is "forward auth" the right name?** It describes the mechanism, but two of the three schemes have no separate gate to forward to — the rpx answers its own sub-question. A contract-shaped name (`auth-gate`, `authenticated-identity`) would cover all three honestly. Recommendation: keep `forward-auth`, since it matches the Caddy directive and the rpx-native schemes are legitimately the degenerate case of the same shape.
- **Do the cheap alternates need tickets at all?** [Authelia](../features/authelia.md) now covers the no-provider case properly, which was the gap basic auth and mTLS were being considered for. They may be worth writing up as documented rpx snippets rather than roles — or worth dropping to keep the scheme list short.
- **Do the alternates keep the `X-Auth-Request-*` spelling?** It is oauth2-proxy's, not a standard. Recommendation: yes — it is what the service roles already read, and inventing a neutral spelling would mean a translation shim in the default scheme for no gain.
- **Does the basic-auth scheme need a session at all?** Browsers cache basic credentials for the realm, so probably not; worth confirming against a websocket-heavy client like code-server before it is written up.
