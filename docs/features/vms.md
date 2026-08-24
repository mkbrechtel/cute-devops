<!--
SPDX-FileCopyrightText: 2016 - 2026 Mirian Brechtel <markus.katharina.brechtel@thengo.net>
SPDX-FileCopyrightText: 2020 - 2025 Uniklinik Köln
SPDX-FileCopyrightText: 2025 - 2026 Goethe-University Frankfurt – Institute for Digital Medicine and Clinical Data Science

SPDX-License-Identifier: EUPL-1.2
-->

# vms

Really simple virtual machines: one instanced `vm@.service` template
unit that starts qemu directly. systemd *is* the hypervisor manager —
no libvirt, no XML, no extra daemon. A VM is a unit instance
(`vm@webtest.service`) plus one qemu config file; everything you
already know about units (enable, restart, journal, resource limits)
applies to VMs unchanged.

Implemented by the [`vms` role](../../roles/vms/README.md).

## How it works

**The unit is policy, the config file is the VM.** The template unit
runs

```
qemu-system-x86_64 -nodefaults -display none -cpu host -name %i \
    -readconfig /etc/vms/%i.cfg
```

and `/etc/vms/<name>.cfg` is qemu's native `-readconfig` format:
`[machine]`, `[memory]`, `[smp-opts]`, `[drive]`, `[netdev]`,
`[device]`, `[chardev]`. The role templates it from the
`vms_instances` inventory dict — but a hand-written file works
identically, and `systemctl start vm@<name>` just runs it.

**Per-VM run dir.** `RuntimeDirectory=vms/%i` gives every VM
`/run/vms/<name>/`, created and cleaned up with the unit. It holds
the QMP socket (`qmp`) and serial console socket (`console`), so
every VM is reachable without graphics:

```bash
socat - UNIX-CONNECT:/run/vms/webtest/console
```

**Graceful shutdown.** `ExecStop` sends ACPI `system_powerdown` over
QMP; qemu exits when the guest halts. `TimeoutStopSec=120` is the
backstop for guests that ignore ACPI.

**The systemd toolbox is the VM toolbox.** `systemctl status
vm@webtest`, `journalctl -u vm@webtest`, `MemoryMax=`/`CPUQuota=` via
a `vm@webtest.service.d/` drop-in instead of hypervisor tunables.
qemu merges `-readconfig` with further CLI args, so a drop-in
appending arguments also covers anything the config format can't
express — no wrapper scripts, no invented formats.

## Access model

Two principals:

- **`vm-run`** — system user qemu runs as, member of `kvm` (a system
  user has no logind seat, so the desktop uaccess ACL on `/dev/kvm`
  does not apply; group membership is the mechanism).
- **`vm-admin`** — group for humans operating VMs: read/write on the
  console and QMP sockets (run dir is `0750 vm-run:vm-admin`), and a
  polkit rule allowing start/stop/restart of `vm@*.service` — matched
  on the unit name — without sudo.

QMP access is powerful (device hotplug etc.), but `vm-admin` members
can restart units anyway, so the trust boundary is consistent:
`vm-admin` administers VMs, full stop.

## Networking

Default is qemu's built-in user-mode networking: zero host
configuration, outbound-only. `vms_with_bridge: true` enables bridged
NICs via `qemu-bridge-helper`:

- Debian ships the helper inert (`0755 root:root`, no ACL file). The
  role activates it scoped: `dpkg-statoverride` to `4750
  root:vm-run` — setuid, but executable only by the qemu user.
- `/etc/qemu/bridge.conf` is written from `vms_bridge_allow`, default
  `allow all`. Restrictive sites list specific bridges; the ACL is
  default-deny with deny-overriding-allow. Bridges themselves are
  host network config and assumed to exist.
- A VM on multiple networks is just multiple `[netdev]`/`[device]`
  pairs naming different bridges.
- NIC MACs are stable, derived from the VM name (qemu's default MAC
  is identical for every VM), overridable per VM.

**Multi-host VM networks** need no new machinery: enslave a kernel
VXLAN device into the same bridge on each host (over WireGuard when
the underlay is untrusted) and the L2 spans machines. Full SDN (OVN)
is the scale-up path beyond this feature — at that point use incus.

## Web console

`vms_with_web_console: true` adds browser access to each VM's
graphical console — unix sockets only, no TCP ports anywhere:

- Each VM's config gains `[vnc]` on `/run/vms/<name>/vnc`.
- A `websockify@` instance per VM (`PartOf=vm@%i.service`) bridges it
  to `/run/vms/<name>/websock`, owned
  `vm-run:https-socket-access 0660` so the reverse proxy can connect;
  the run dir stays `vm-admin`-only apart from a traverse-only ACL.
- A single Caddy vhost (`vms.<host>`) serves the noVNC client and
  proxies `/<name>/websock` per VM — put oauth2-proxy's
  `forward_auth` in front via `vms_caddy_extra`. Open a console at
  `/vnc.html?path=<name>/websock&autoconnect=true`.

Same ingredients as Debian's `qemu-web-desktop` (qemu + websockify +
noVNC), composed our way: declarative long-lived service VMs behind
the collection's reverse-proxy pattern instead of a session-oriented
web app with its own stack.

## Design rationale

### Why `-readconfig`

Candidates for feeding qemu its configuration: an env-file schema
interpolated in the unit (invents a role-owned format, fragile
escaping), a wrapper script reading an args file (glue between
systemd and qemu), or qemu's own config file. `-readconfig` wins: two
native formats, zero glue, and the per-VM file is the whole truth
about the VM.

Config-file sections only exist for options backed by a registered
`QemuOpts` group. Verified against qemu 10.0.11 (trixie): `[cpu]`,
`[display]`, `[nographic]`, `[nodefaults]` are rejected — which is
fine, because those are exactly the *policy* options that belong in
the unit. Upstream's own example configs
(`/usr/share/doc/qemu-system-common/config/`) use the same split.
QAPI-only options (`-blockdev`, JSON `-object`) have no config-file
form; the drop-in escape hatch covers them.

### The bridge helper, precisely

A small setuid C binary qemu execs per bridged NIC: it checks the
bridge against the ACL, creates a tap (kernel-named `tap%d`),
attaches it with `SIOCBRADDIF`, passes the fd back, and exits.
Accepted limits for this feature's trusted-guest scope: tap names are
never reported, so per-port policy (MAC locking, ARP filters,
per-port VLANs) cannot be attached, and only kernel bridges work, not
OVS. A future port-security variant would switch to role-created
named taps (`ip tuntap add … user vm-run vnet_hdr` in
`ExecStartPre=+`, qemu opens by `ifname=`), which also covers OVN
attachment — same `[netdev]` mechanism, different tap provenance.

### Rejected alternatives

qemu's `socket`/`dgram`/`stream`/`hubport` backends (hub semantics,
no uplink, slow path) and vde (dormant, still needs a privileged
uplink) for networking; libvirt and incus as a whole — right for
fleets, migration, snapshot features, wrong for the host that needs
two or three long-lived VMs and no new mental model.

## Decisions

- **Firmware:** SeaBIOS. UEFI/OVMF would add a per-VM nvram file;
  can become a flag when needed.
- **User-mode backend:** qemu's built-in slirp. passt is the modern
  replacement (unprivileged per-VM process, already in trixie) and a
  candidate future flag.
- **OS installation:** not this feature's job — boot an installer ISO
  via `extra_config`, or provision images externally (see the
  os-bootstrap ticket).
- **Console:** on the socket only, not mirrored to the journal.
- **polkit scope:** start/stop/restart (`manage-units`) only;
  enable/disable stays with root.
