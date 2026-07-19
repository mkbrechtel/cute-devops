---
status: in-progress
---

<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# test-in-containers — role testing in podman system containers

## Goal

Test the collection's roles in rootless podman **system containers** — `systemd` as PID 1, full Debian userspace, real `.service` units — instead of full incus VMs. Faster to boot, cheaper to run, quick to iterate. This is now the **default** test path for the collection; `test-in-vms` stays, narrowed to the OS-level roles that genuinely need a kernel, and is to be used sparingly.

## Scope

One base image (`test/Containerfile`) drives every instance. A templated quadlet (`cute-devops-test@<instance>`) starts named instances on a shared podman network in the invoking user's account, backed by linger. Ansible reaches them over the `containers.podman.podman` connection, where `test-in-vms` used the incus connection. Multi-instance topologies (the mail stack's `mo`/`mx`/`mb`/`ml` split) come from starting several instances on the one network and resolving peers by name.

Three topologies exist: `roles` (general role coverage — the former VM suite), and the mail stack's `single` and `multi`. The mail stack is the first and heaviest consumer — postfix, dovecot, and sympa are all real systemd services with cross-service coupling — so it proves the pattern. The lighter roles (`common`, deploy, monitoring, shells) follow, each as instances of the same base image.

A run assertion convention comes with it: the `test_mail_stack` role checks units are active and ports listen, and drives an end-to-end probe. The same shape generalises to other roles' service-up checks.

## Design notes

**System container, not dockerized.** One container, one init, one journald — the same service topology as a VM or bare metal. This is distinct from the compose-style, one-process-per-container decomposition that [`dockerize-mail-servers`](dockerize-mail-servers.feature.md) warns against.

**Prototype for `deploy_quadlet`.** The rootless-quadlet-with-linger provisioning here is the working prototype of the `deploy_quadlet` role proposed in [`container-apps.feature.md`](container-apps.feature.md); the two should converge.

**Where VMs stay.** `test-in-vms` is kept, but narrowed to what a container cannot answer because it owns no kernel: boot/init config, kernel and sysctl behaviour, firewall/netfilter rules, storage and partitioning, firmware/microcode, and true multi-host networking a shared podman network can't model. It now runs `common` plus `sysctl_tweaks`, `resolvconf`, `storage`, `firmware` and `microcode`.

Everything else it used to cover — `setup_deploy` + the `test_deploy_*` probes, `ttyd`, `knot_nameserver` — moved to the `test-in-containers-roles` topology. The VM path is the expensive one (it needs an incus daemon, absent on the current dev host), so both the playbook and its inventory carry an explicit "use sparingly" remark: adding a play there commits whoever runs the suite to keeping a VM alive.

`sysctl_tweaks` is the concrete case for keeping it. The flag is off by default, and a rootless container silently keeps the host's `fs.inotify.max_user_watches` — only a VM run actually exercises it.

## Open questions

- One base image for all roles, or per-family images once the set grows?
- CI: run the container harness in pipelines (needs cgroups v2 + rootless in the runner), and which topologies gate a merge?
- How far to push multi-instance realism (separate networks, injected latency) before it's cheaper to use VMs?
