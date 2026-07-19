<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# test-in-containers

A fast, VM-free harness for the collection's roles, and **the default**
test path — `test-in-vms` is now reserved for OS-level work that needs a
real kernel (see below). It boots Debian-trixie
**system containers** — `systemd` as PID 1, full userspace, real
`.service` units — as rootless podman quadlets in your user account and
deploys the roles into them over the `containers.podman.podman`
connection.

This is a system container, **not** a dockerized, one-process-per-
container decomposition. It does not contradict
[`anti-patterns/dockerize-mail-servers.md`](../anti-patterns/dockerize-mail-servers.md);
see the "What This Is Not About" section there.

## Topologies

- **roles** — the general role coverage: `deploy` (setup_deploy + the
  `test_deploy_*` probes), `devbox` (ttyd), `ns` (knot_nameserver), each
  on `common`. Run: `./test-in-containers-roles.yaml`
- **single** — one `mail` instance runs postfix + dovecot + sympa
  co-located. Run: `./test-in-containers-single.yaml`
- **multi** — the stack split across `mx` (inbound MX), `mo` (submission),
  `mb` (mailboxes/dovecot), `ml` (mailing lists) on a shared network.
  Run: `./test-in-containers-multi.yaml`

All three build the one `test/Containerfile` image and start instances
from the templated `test/quadlets/cute-devops-test@.container` unit. The
two mail topologies additionally issue a throwaway test CA (`test/ca/`)
and assert with the `test_mail_stack` role; **roles** sets no
`test_ca_domain`, so CA issuance is skipped.

### The VM harness — use it sparingly

`test-in-vms.yaml` still exists, now scoped to **only** what a container
cannot answer, because a container owns no kernel of its own: boot/init
config, kernel and sysctl behaviour, firewall/netfilter rules, storage and
partitioning, firmware and microcode, and true multi-host networking. It
runs `common` plus `sysctl_tweaks`, `resolvconf`, `storage`, `firmware`
and `microcode` on one incus VM.

Everything the VM suite used to cover beyond that — `setup_deploy` and the
`test_deploy_*` probes, `ttyd`, `knot_nameserver` — moved to the **roles**
topology above, where it costs seconds instead of minutes.

Reach for the VM path only when the container path genuinely can't answer
the question: it needs an incus daemon on the machine running it (not
installed on the current dev host), and every play added there is one
someone has to keep a VM alive for. `sysctl_tweaks` is the clearest
example of why it's kept — a rootless container silently keeps the host's
`fs.inotify.max_user_watches`, so only the VM run actually tests it.

## Prerequisites

- Rootless podman on a **cgroups v2** host (Debian trixie default) with
  `crun`. The mail packages are installed by the roles at run time.
- The collections in `../requirements.yml`:
  `ansible-galaxy collection install -r ../requirements.yml`
- User **linger** (the provision play enables it via `loginctl
  enable-linger`) so `systemctl --user` works non-interactively.

## Iteration loop

- Re-apply one role on one instance (seconds; instances stay up):
  `./test-in-containers-single.yaml --tags postfix`
  `./test-in-containers-multi.yaml --tags dovecot --limit mb`
  `./test-in-containers-roles.yaml --tags knot`
- Re-run just the assertions: `--tags test`
- Rebuild the base image: `-e test_rebuild_image=true`
- Teardown: `systemctl --user stop 'cute-devops-test@*'` then
  `podman rm -f <instance>...`; remove the quadlets from
  `~/.config/containers/systemd/` and `systemctl --user daemon-reload`.
- Logs: `podman exec <instance> journalctl -u postfix -u dovecot`

## Status / notes

**roles** deploys green on all three instances: knot answers its
`test.example` SOA, ttyd 1.7.7 installs and symlinks, and the deploy
units template out. `deploy` and `devbox` are fully idempotent.

Both mail topologies deploy green and pass the end-to-end mail-flow probe
(SMTP submission → LMTP delivery → IMAPS retrieval):

- **single** — postfix + dovecot + sympa co-located; a message to
  `test@mail.test` is delivered and retrieved over IMAPS.
- **multi** — a message injected at `mx` is delivered to `mb` over LMTP
  inet and retrieved over IMAPS on `mb`.

Known limits / follow-ups:

- **`knot_nameserver` is not idempotent** — the role sets `/var/lib/knot`
  to `0750` and notifies a restart; knot puts it back to `0755` on start,
  so every run reports 2 changes and restarts knot. Pre-existing and
  container-independent (a VM behaves the same); a role fix, not a
  harness fix.
- **Milters (opendkim/opendmarc) are disabled in the tests.** On trixie
  the opendkim service can't bind its socket in postfix's spool dir under
  systemd sandboxing, and DKIM/DMARC need published DNS to be meaningful.
  A production milter fix (inet socket or a systemd `ReadWritePaths`
  override) is a separate task.
- **`mo`→`mb` submission SASL over the network is not exercised** by the
  flow probe (which tests `mx`→`mb` delivery). mo deploys and listens on
  587, but cross-host SASL auth needs a dedicated check.
- If inner systemd fails to boot rootless, add `AddCapability=SYS_ADMIN`
  + `SecurityLabelDisable=true` to the `@` quadlet, or run rootful.
