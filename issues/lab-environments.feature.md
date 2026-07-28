---
status: draft
---

<!--
SPDX-FileCopyrightText: 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science
SPDX-FileCopyrightText: 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>

SPDX-License-Identifier: EUPL-1.2
-->

# Lab environments

## Goal

A `lab` role that gives a project its own sandboxed environment, in which a developer or an agent can run experiments freely while reaching nothing else on the host. Each lab owns a systemd user manager, a rootless podman, a workspace, and nothing further: no other project's files, no services on the machine, no network.

The environment is defined by the project repository, so cloning a repo and starting its lab is the whole setup.

## Scope

A system-scope template unit `lab@<name>.service` whose `ExecStart` is `/usr/lib/systemd/systemd --user`, modelled on systemd's own `user@.service`. It runs as a dedicated per-lab Unix user, carries the sandbox directives, and manages everything else in the lab as ordinary user units.

The role provisions per lab:

- a Unix user with a subuid range, in no administrative group
- a workspace, bound in from the project's working tree
- rootless podman with its own graph root
- unit and quadlet definitions read from `devenv/` inside the project repository
- vendored images, as OCI archives from a read-only directory
- git remotes, as a read-only bind of `/srv/repos`

`PrivateNetwork=yes` completes the isolation. Containers still reach each other over an internal bridge, so multi-service workloads develop normally offline.

The same unit shape serves two purposes. Started on its default target it is a development lab a person or an agent attaches to; started on a CI target by `lab-factory-runner@<id>.service` it is a build.

## CI runs

A continuous-integration run is the same lab with a different initial target. `lab-factory-runner@<id>.service` takes a slot number, runs as that slot's service user, and starts the manager on the repository's CI target rather than its default one:

```ini
ExecStart=/usr/lib/systemd/systemd --user --unit=ci.target
```

`ci.target` and the units it pulls in are ordinary user units from the project's `devenv/`, so a CI run is described the same way a development environment is, and the two share definitions instead of duplicating them. Ordering, readiness and dependency semantics come from systemd rather than a pipeline language.

The run ends when the manager exits. A job unit hands its status back on the way out:

```ini
ExecStopPost=/bin/sh -c 'systemctl --user exit $EXIT_STATUS'
```

which becomes the exit status of `lab-factory-runner@<id>.service` itself — a job exiting 3 produced a runner exiting 3, and a successful job produced 0. Whatever supervises the runner therefore learns the result without parsing anything. Job output goes to the journal, since the units are children of the manager rather than of the runner.

Each slot has its own service user. Two labs sharing one account are not isolated from each other: one lab read the other's container storage, because `ProtectSystem=strict` stops writes but nothing stops reads between processes of the same UID. A per-slot user with `StateDirectoryMode=0700` refuses that read. Slots are recycled by wiping the slot's state directory between runs, which is also what makes a run reproducible.

## Design notes

The arrangement is constrained in ways that are not obvious, each established by measurement on a Debian 13 host with podman 5.4 and systemd 257.

**System scope is required.** An unprivileged user manager cannot create a mount namespace directly, so it builds one out of a user namespace, and that namespace consumes the single UID mapping rootless podman needs. Every sandboxing directive that makes a lab a lab — `ProtectHome=`, `PrivateTmp=`, `ProtectSystem=` — reproduces this independently. Units started by PID 1 are unaffected.

**The lab user is dedicated and unprivileged.** Rootless podman reaches its subuid range through the setuid helper `newuidmap`, so the unit runs with `NoNewPrivileges=no`, which leaves every setuid binary live. A lab running as an account with `sudo` would therefore be one command from root.

**`DynamicUser=` cannot host a lab that needs several UIDs.** It enables `NoNewPrivileges=` implicitly and non-disableably, because its UIDs are recycled; the setuid helper is inert as a result and containers are confined to a single UID. Allocating subuid ranges does not help and actively hurts, since podman then attempts a mapping it cannot install rather than falling back. Labs that need multi-UID images take an ordinary user from a recycled pool.

**Images are vendored as archives, not as a shared store.** `additionalimagestores` serves only a store belonging to the same user: a store written by root and opened for reading yields containers with an empty root filesystem, because rootful and rootless overlay keep their metadata in different xattr namespaces and layer ownership follows the writing user's subuid range. A published OCI archive loads and runs cleanly.

**The runtime directory name is fixed per lab.** Podman records its run root in the graph root's metadata, and a run root that moves between restarts fails the next start.

## Relation to existing roles

The lab is where [container-apps](container-apps.feature.md) workloads are developed before they are deployed, and it gives [claude-code](claude-code.feature.md) a blast radius bounded by the kernel rather than by tool permissions. A [devbox](devbox.feature.md) host would offer one lab per project, with [code-server](code-server.feature.md) and [ttyd](ttyd.feature.md) sessions attached to a lab rather than to the host. [test-in-containers](test-in-containers.feature.md) describes the same shape for role tests and is the natural first consumer.

Repositories reach labs as bare repos under `/srv/repos`, which is how [push-to-deploy](push-to-deploy.pattern.md) and [Shared Worktrees](../patterns/workflows/shared-worktrees.md) already move work.

## Open questions

**Slot allocation.** How a run claims a free slot and how many slots a host offers, given that each is a standing service user rather than something created on demand.

**Disposal.** Whether a slot's storage lives in `StateDirectory=`, wiped by the runner on stop, or in `RuntimeDirectory=`, which systemd removes automatically at the cost of holding image layers in memory.

**The vendor service.** How a lab requests an artefact it does not have, and what publishes archives into the read-only vendor directory.

**Global units.** A host-wide unit directory bound at one of the manager's lower-precedence search paths, so a repository tracks only what is specific to it. The search order already supports this; the layering is untested.

**Credentials.** How a lab receives the secrets it legitimately needs, given that the point of the design is that it can reach nothing by default.

**Name resolution.** Containers resolve each other through `aardvark-dns` once the lab's own manager is running. Whether labs should resolve anything beyond themselves is undecided.

# Considerations

## Not a podman socket from the host

Binding the host's `podman.sock` into a lab is worse than granting no sandbox at all, because it looks contained and is not: the host podman resolves bind mounts in the host's namespace, so a container asking for `/` receives the machine's root filesystem. The same reasoning rules out one podman instance serving several labs.

## Not a container per lab

Running each lab inside a container with nested podman also contains bind mounts correctly, and it works: `_CONTAINERS_USERNS_CONFIGURED=done` to stop the inner podman re-execing into a new namespace, plus `--cap-add=SYS_ADMIN`, with `--privileged` not required. It costs more than it returns here — an extra capability, nested containers sharing one uid space, and a base image per lab — where a systemd unit already provides the same boundary.

## Not quadlets served by the host manager

Quadlet is a systemd generator rather than part of the podman API, so a lab's quadlet files are read by the lab's own manager. Arranging for the host manager to read them would let a repository author units that the host executes outside the sandbox.
